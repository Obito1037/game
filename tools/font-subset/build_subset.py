"""Create the game's renamed, outline-preserving OFL font subset.

Run with Blender's Python. Dependencies live beside this script in vendor/.
Only tools/font-subset/ and art/generated/fonts/ are written.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import unicodedata
from datetime import datetime, timezone

TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parents[1]
sys.path.insert(0, str(TOOL_DIR / "vendor"))

import fontTools
from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = ROOT / "GameProject/Assets/BorrowedLight/Resources/Fonts"
SOURCE = FONT_DIR / "StorySerif.otf"
LICENSE = FONT_DIR / "LICENSE.txt"
RUNTIME = ROOT / "GameProject/Assets/BorrowedLight/Runtime"
OUTPUT = ROOT / "art/generated/fonts"
FAMILY = "BorrowedLight Story Serif"
FULL_NAME = FAMILY + " Regular"
POSTSCRIPT_NAME = "BorrowedLightStorySerif-Regular"
EXTRA_TEXT = "，。！？；：、（）【】《》〈〉「」『』“”‘’…—·～　←→↑↓↔⇒"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(codepoints: set[int]) -> list[dict]:
    return [
        {"codepoint": f"U+{cp:04X}", "character": chr(cp),
         "name": unicodedata.name(chr(cp), "CONTROL OR UNNAMED"),
         "category": unicodedata.category(chr(cp))}
        for cp in sorted(codepoints)
    ]


def unique_names(font: TTFont, name_id: int) -> list[str]:
    return sorted({record.toUnicode(errors="replace")
                   for record in font["name"].names if record.nameID == name_id})


def rename_font(font: TTFont) -> None:
    replacements = {
        1: FAMILY, 3: POSTSCRIPT_NAME + "; Borrowed Light current-game subset 1.0",
        4: FULL_NAME, 6: POSTSCRIPT_NAME, 16: FAMILY, 18: FULL_NAME,
        21: FAMILY, 25: "BorrowedLightStorySerif",
    }
    # Keep copyright, author, trademark, license and license URL records verbatim.
    for record in list(font["name"].names):
        if record.nameID in replacements:
            font["name"].setName(replacements[record.nameID], record.nameID,
                                 record.platformID, record.platEncID, record.langID)
    for name_id in (1, 3, 4, 6, 16):
        font["name"].setName(replacements[name_id], name_id, 3, 1, 0x409)
    font["name"].setName("Regular", 2, 3, 1, 0x409)
    font["name"].setName("Regular", 17, 3, 1, 0x409)
    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [POSTSCRIPT_NAME]
        for top in cff.topDictIndex:
            top.FamilyName = FAMILY
            top.FullName = FULL_NAME
            if hasattr(top, "FDArray"):
                for index, font_dict in enumerate(top.FDArray):
                    if hasattr(font_dict, "FontName"):
                        font_dict.FontName = POSTSCRIPT_NAME + f"-FD{index}"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_dir = OUTPUT / "source"
    source_dir.mkdir(exist_ok=True)
    # Keep the original source immutable across future runs, even after the root
    # task replaces Unity's live asset with the much smaller game-text subset.
    canonical_source = source_dir / SOURCE.name
    expected_source_hash = None
    if not canonical_source.exists():
        expected_source_hash = sha256(SOURCE)
        shutil.copy2(SOURCE, canonical_source)
    elif (OUTPUT / "manifest.json").exists():
        previous_manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
        expected_source_hash = previous_manifest.get("sourceSha256")
    canonical_source_hash = sha256(canonical_source)
    if expected_source_hash and canonical_source_hash != expected_source_hash:
        raise RuntimeError("Canonical full source font differs from its previously recorded SHA-256")
    shutil.copy2(LICENSE, source_dir / LICENSE.name)
    shutil.copy2(LICENSE, OUTPUT / LICENSE.name)
    license_text = LICENSE.read_text(encoding="utf-8-sig")

    files = sorted(RUNTIME.rglob("*.cs"))
    if not files:
        raise RuntimeError("No runtime C# source files were found")
    runtime_characters: set[int] = set()
    scanned_files = []
    for path in files:
        content = path.read_bytes().decode("utf-8-sig")
        runtime_characters.update(map(ord, content))
        scanned_files.append({"path": path.relative_to(ROOT).as_posix(),
                              "sha256": sha256(path),
                              "uniqueCharacterCount": len(set(content))})

    ascii_characters = set(range(128))
    extra_characters = set(map(ord, EXTRA_TEXT))
    requested = runtime_characters | ascii_characters | extra_characters
    font = TTFont(canonical_source, recalcTimestamp=False)
    source_cmap = set(font.getBestCmap())
    original_tables = set(font.keys())
    original_glyph_count = len(font.getGlyphOrder())
    source_names = {str(name_id): unique_names(font, name_id)
                    for name_id in (0, 1, 2, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17)}
    missing_from_source = requested - source_cmap
    missing_controls = {cp for cp in missing_from_source
                        if unicodedata.category(chr(cp)).startswith("C")}
    missing_runtime_printable = (runtime_characters - source_cmap) - missing_controls
    retain = requested & source_cmap

    options = subset.Options()
    options.hinting = True
    options.desubroutinize = False
    options.layout_features = ["*"]
    options.layout_scripts = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True
    options.glyph_names = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.recommended_glyphs = True
    options.recalc_average_width = True
    options.recalc_max_context = True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=retain)
    subsetter.subset(font)
    rename_font(font)
    destination = OUTPUT / "StorySerifSubset.otf"
    font.save(destination, reorderTables=True)
    font.close()

    # Reopen the written binary, not the in-memory source, for actual coverage checks.
    verified = TTFont(destination, recalcTimestamp=False)
    output_cmap = set(verified.getBestCmap())
    lost_characters = retain - output_cmap
    lost_runtime = (runtime_characters & source_cmap) - output_cmap
    retained_layout = {table: table in verified for table in ("GSUB", "GPOS")}
    original_layout = {table: table in original_tables for table in ("GSUB", "GPOS")}
    outline_format = "CFF" if "CFF " in verified else "CFF2" if "CFF2" in verified else "UNEXPECTED"
    expected_names = unique_names(verified, 1)
    outline_passed = verified.sfntVersion == "OTTO" and outline_format in ("CFF", "CFF2")
    layout_passed = all(not original_layout[t] or retained_layout[t] for t in original_layout)
    source_copyright = source_names["0"]
    output_copyright = unique_names(verified, 0)
    copyright_passed = source_copyright == output_copyright
    coverage_passed = not lost_characters and not lost_runtime and not missing_runtime_printable
    source_size = canonical_source.stat().st_size
    result_size = destination.stat().st_size

    manifest = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "tool": "fontTools.subset", "fontToolsVersion": fontTools.__version__,
        "sourceStatement": "Derived from the unchanged local StorySerif.otf supplied with this game's font assets. Original authorship and copyright remain with the original font authors. This renamed game-text subset is distributed under SIL OFL 1.1.",
        "sourcePath": SOURCE.relative_to(ROOT).as_posix(),
        "canonicalSourcePath": canonical_source.relative_to(ROOT).as_posix(),
        "sourceBackupPath": (source_dir / SOURCE.name).relative_to(ROOT).as_posix(),
        "sourceBytes": source_size, "sourceSha256": sha256(canonical_source),
        "sourceBackupSha256": sha256(source_dir / SOURCE.name),
        "sourceGlyphCount": original_glyph_count,
        "sourceNameRecords": source_names,
        "outputPath": destination.relative_to(ROOT).as_posix(),
        "outputBytes": result_size, "outputSha256": sha256(destination),
        "sizeReductionPercent": round((1 - result_size / source_size) * 100, 3),
        "outputFamilyNames": expected_names,
        "outputPostScriptNames": unique_names(verified, 6),
        "outputGlyphCount": len(verified.getGlyphOrder()),
        "outlineFormat": outline_format, "outlinePreserved": outline_passed,
        "hintingPreserved": True, "layoutFeaturesRequested": ["*"],
        "sourceLayoutTables": original_layout, "outputLayoutTables": retained_layout,
        "copyrightNameRecordsPreserved": copyright_passed,
        "scannedFiles": scanned_files,
        "runtimeUniqueCodepointCount": len(runtime_characters),
        "asciiRequestedCount": len(ascii_characters),
        "extraPunctuationAndArrows": EXTRA_TEXT,
        "requestedCodepointCount": len(requested),
        "retainedRequestedCodepointCount": len(retain),
        "outputCmapCodepointCount": len(output_cmap),
        "coverageReopenedBinaryPassed": coverage_passed,
        "missingFromSourceControlsIgnored": describe(missing_controls),
        "missingFromSourceNonControl": describe(missing_from_source - missing_controls),
        "missingRuntimePrintableCharacters": describe(missing_runtime_printable),
        "lostAfterSubsetting": describe(lost_characters),
        "requestedCodepoints": [f"U+{cp:04X}" for cp in sorted(requested)],
        "license": {"name": "SIL Open Font License 1.1",
                    "path": "art/generated/fonts/LICENSE.txt",
                    "sha256": sha256(LICENSE), "fullText": license_text},
        "checks": {"belowOneMiB": result_size < 1024 * 1024,
                   "sourceBackupMatches": not expected_source_hash or canonical_source_hash == expected_source_hash,
                   "familyRenamed": expected_names == [FAMILY],
                   "coveragePassed": coverage_passed, "outlinePassed": outline_passed,
                   "layoutPassed": layout_passed, "copyrightPassed": copyright_passed},
    }
    verified.close()
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    retained_text = "".join(chr(cp) for cp in sorted(retain))
    (OUTPUT / "characters.txt").write_text(retained_text + "\n", encoding="utf-8")
    attribution = ("BorrowedLight Story Serif\n\n" + manifest["sourceStatement"] + "\n\n"
                   + "Original font copyright:\n" + "\n".join(source_copyright)
                   + "\n\nSource SHA-256: " + manifest["sourceSha256"]
                   + "\nSubset SHA-256: " + manifest["outputSha256"]
                   + "\n\nFull license: LICENSE.txt\n")
    (OUTPUT / "SOURCE.txt").write_text(attribution, encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in
                      ("outputBytes", "sourceBytes", "sizeReductionPercent", "runtimeUniqueCodepointCount",
                       "requestedCodepointCount", "retainedRequestedCodepointCount", "outputGlyphCount", "checks")},
                     ensure_ascii=False))
    if not all(manifest["checks"].values()):
        raise SystemExit("Font subset verification failed; inspect art/generated/fonts/manifest.json")


if __name__ == "__main__":
    main()
