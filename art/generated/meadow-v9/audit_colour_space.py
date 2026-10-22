"""Read-only PNG colour audit; writes only colour-space-audit.json beside this file.

Run with ordinary Python plus NumPy. No Blender, Unity, GPU, Pillow, or image
editing is used. Frozen candidate PNGs and their original evidence stay intact.
"""
from __future__ import annotations

import ast
import hashlib
import json
import struct
import time
import zlib
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GENERATOR = ROOT / "art/blender/build_meadow_contact_v9.py"
REPORT = HERE / "colour-space-audit.json"
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_png(path: Path) -> tuple[np.ndarray, dict]:
    """Decode non-interlaced 8-bit RGB/RGBA PNG, retaining top-to-bottom rows.

    PNG filtering is reversible byte arithmetic. No gamma conversion is applied
    here; the returned uint8 channels are the actual encoded PNG sample values.
    """
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", path
    at = 8
    data = []
    meta = {}
    while at < len(raw):
        length = struct.unpack_from(">I", raw, at)[0]
        kind = raw[at + 4:at + 8]
        payload = raw[at + 8:at + 8 + length]
        checksum = struct.unpack_from(">I", raw, at + 8 + length)[0]
        assert zlib.crc32(kind + payload) & 0xFFFFFFFF == checksum, (path, kind)
        if kind == b"IHDR":
            width, height, bits, colour, compression, filt, interlace = struct.unpack(">IIBBBBB", payload)
            assert bits == 8 and colour in (2, 6), (bits, colour)
            assert compression == 0 and filt == 0 and interlace == 0
            channels = 4 if colour == 6 else 3
            meta.update(width=width, height=height, bit_depth=bits, colour_type=colour,
                        row_order="PNG top to bottom", channels=channels)
        elif kind == b"IDAT":
            data.append(payload)
        elif kind == b"sRGB":
            meta["sRGB_rendering_intent"] = payload[0]
        elif kind == b"gAMA":
            meta["gAMA"] = struct.unpack(">I", payload)[0] / 100000.0
        elif kind == b"IEND":
            break
        at += length + 12
    stride = width * channels
    packed = zlib.decompress(b"".join(data))
    assert len(packed) == height * (stride + 1)
    decoded = np.empty((height, stride), dtype=np.uint8)
    previous = bytearray(stride)
    filter_counts = {}
    for y in range(height):
        start = y * (stride + 1)
        kind = packed[start]
        row = bytearray(packed[start + 1:start + 1 + stride])
        filter_counts[str(kind)] = filter_counts.get(str(kind), 0) + 1
        if kind == 1:
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 255
        elif kind == 2:
            for i in range(stride):
                row[i] = (row[i] + previous[i]) & 255
        elif kind == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((left + previous[i]) // 2)) & 255
        elif kind == 4:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = previous[i]
                corner = previous[i - channels] if i >= channels else 0
                p = left + up - corner
                a, b, c = abs(p - left), abs(p - up), abs(p - corner)
                predictor = left if a <= b and a <= c else up if b <= c else corner
                row[i] = (row[i] + predictor) & 255
        else:
            assert kind == 0, (path, y, kind)
        decoded[y] = np.frombuffer(row, dtype=np.uint8)
        previous = row
    meta["scanline_filter_counts"] = filter_counts
    return decoded.reshape(height, width, channels), meta


def srgb_decode(samples: np.ndarray) -> np.ndarray:
    return np.where(samples <= 0.04045, samples / 12.92,
                    ((samples + 0.055) / 1.055) ** 2.4)


def relative_darkening(before_luma: np.ndarray, after_luma: np.ndarray) -> np.ndarray:
    assert np.all(before_luma > 0), "Relative darkening requires a nonzero baseline"
    return 1.0 - after_luma / before_luma


def read_routes() -> list:
    """Read the frozen generator's literal route data without executing it."""
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "path_layout" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Frozen generator has no literal path_layout")


def path_distance(width: int, height: int, routes: list) -> np.ndarray:
    # UV v increases upward; PNG row indices increase downward. The frozen mesh
    # has u=(Unity.x+9)/18 and v=(Unity.z+9)/18. All samples use texel centres.
    x = (np.arange(width, dtype=np.float64)[None, :] + 0.5) * 18.0 / width - 9.0
    z = 9.0 - (np.arange(height, dtype=np.float64)[:, None] + 0.5) * 18.0 / height
    distance = np.full((height, width), np.inf, dtype=np.float64)
    for route in routes:
        for (ax, az), (bx, bz) in zip(route[:-1], route[1:]):
            dx, dz = bx - ax, bz - az
            t = np.clip(((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz), 0, 1)
            d = np.sqrt((x - ax - t * dx) ** 2 + (z - az - t * dz) ** 2)
            np.minimum(distance, d, out=distance)
    return distance


def box_mip(image: np.ndarray) -> np.ndarray:
    h, w, channels = image.shape
    assert h % 2 == 0 and w % 2 == 0
    return image.reshape(h // 2, 2, w // 2, 2, channels).mean(axis=(1, 3))


def main() -> None:
    started = time.time()
    archived_manifest = HERE / "asset-manifest.original-encoded.json"
    old_manifest_path = archived_manifest if archived_manifest.exists() else HERE / "asset-manifest.json"
    old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
    frozen = [GENERATOR, old_manifest_path,
              HERE / "meadow-no-contact.png", HERE / "meadow-contact.png",
              HERE / "contact-mask.png", HERE / "root-positions.json"]
    frozen_hashes = {str(p.relative_to(ROOT)): sha(p) for p in frozen}
    for name, expected in old_manifest["sha256"].items():
        assert sha(HERE / name) == expected, f"Frozen evidence differs: {name}"
    base, base_meta = read_png(HERE / "meadow-no-contact.png")
    candidate, candidate_meta = read_png(HERE / "meadow-contact.png")
    assert base.shape == candidate.shape == (2048, 2048, 4)
    assert np.array_equal(base[:, :, 3], candidate[:, :, 3])
    changed = np.any(base[:, :, :3] != candidate[:, :, :3], axis=2)
    assert changed.any()
    encoded_change = relative_darkening(base[:, :, :3] @ LUMA,
                                        candidate[:, :, :3] @ LUMA)
    encoded_statistics = {
        "maximum_encoded_luminance_darkening": float(encoded_change.max()),
        "mean_encoded_luminance_darkening_whole_atlas": float(encoded_change.mean()),
        "mean_encoded_luminance_darkening_changed_pixels": float(encoded_change[changed].mean()),
    }
    lut = srgb_decode(np.arange(256, dtype=np.float64) / 255.0)
    base_linear, candidate_linear = lut[base[:, :, :3]], lut[candidate[:, :, :3]]
    base_luma, candidate_luma = base_linear @ LUMA, candidate_linear @ LUMA
    actual = relative_darkening(base_luma, candidate_luma)
    max_row, max_col = np.unravel_index(np.argmax(actual), actual.shape)
    stats = {
        "maximum_linear_luminance_darkening": float(actual.max()),
        "minimum_linear_luminance_darkening": float(actual.min()),
        "mean_linear_luminance_darkening_whole_atlas": float(actual.mean()),
        "mean_linear_luminance_darkening_changed_pixels": float(actual[changed].mean()),
        "total_linear_luminance_reduction_fraction": float(1 - candidate_luma.sum() / base_luma.sum()),
        "changed_pixels": int(changed.sum()),
        "changed_fraction_atlas": float(changed.mean()),
        "pixels_with_linear_darkening_above_12_percent": int((actual > 0.12).sum()),
        "pixels_with_any_brightened_rgb_channel": int(np.any(candidate[:, :, :3] > base[:, :, :3], axis=2).sum()),
        "linear_darkening_changed_pixel_percentiles_p50_p90_p99": [float(v) for v in np.percentile(actual[changed], [50, 90, 99])],
        "maximum_location": {
            "png_column": int(max_col), "png_row_top_to_bottom": int(max_row),
            "authored_unity_xz": [(float(max_col) + 0.5) * 18 / 2048 - 9,
                                   9 - (float(max_row) + 0.5) * 18 / 2048],
            "baseline_srgb_rgb8": base[max_row, max_col, :3].tolist(),
            "candidate_srgb_rgb8": candidate[max_row, max_col, :3].tolist(),
            "baseline_linear_luminance": float(base_luma[max_row, max_col]),
            "candidate_linear_luminance": float(candidate_luma[max_row, max_col]),
            "encoded_luminance_darkening_at_same_pixel": float(encoded_change[max_row, max_col]),
        },
        "alpha_unchanged": True,
    }
    del actual, encoded_change, base_luma, candidate_luma
    routes = read_routes()
    mip_results = []
    mip_base, mip_candidate = base_linear, candidate_linear
    del base_linear, candidate_linear
    for level in range(5):
        if level:
            mip_base, mip_candidate = box_mip(mip_base), box_mip(mip_candidate)
        height, width, _ = mip_base.shape
        delta = relative_darkening(mip_base @ LUMA, mip_candidate @ LUMA)
        distance = path_distance(width, height, routes)
        item = {"mip": level, "resolution": [width, height]}
        for radius, label in [(0.25, "25cm_path_core"), (0.15, "15cm_path_center")]:
            selected = delta[distance <= radius]
            item[label] = {
                "sample_count": int(selected.size),
                "maximum_linear_luminance_darkening": float(selected.max()),
                "mean_linear_luminance_darkening": float(selected.mean()),
                "affected_samples": int((selected > 1e-12).sum()),
            }
        mip_results.append(item)
    assert mip_results[0]["25cm_path_core"]["affected_samples"] == 0
    assert all(sha(p) == frozen_hashes[str(p.relative_to(ROOT))] for p in frozen)
    legacy = old_manifest["mask_statistics"]
    report = {
        "title": "Frozen meadow-v9 PNG colour-space audit",
        "status": "Audit correction only; original candidate and evidence retained. No asset iteration or adoption.",
        "script": str(Path(__file__).relative_to(ROOT)), "script_sha256": sha(Path(__file__)),
        "runtime": "Ordinary Python + NumPy; no Blender, Unity, GPU, or image editing",
        "numpy_version": np.__version__,
        "inputs_sha256": frozen_hashes, "all_frozen_inputs_unchanged": True,
        "legacy_manifest_source": str(old_manifest_path.relative_to(ROOT)),
        "png_metadata": {"baseline": base_meta, "candidate": candidate_meta},
        "colour_contract": {
            "input": "PNG uint8 RGB are sRGB encoded samples; alpha is not gamma transformed.",
            "decode": "c/12.92 for c<=0.04045; ((c+0.055)/1.055)^2.4 otherwise, where c=channel/255.",
            "linear_luminance": "0.2126*R_linear + 0.7152*G_linear + 0.0722*B_linear",
            "darkening": "1 - candidate_linear_luminance / baseline_linear_luminance",
            "means": "Arithmetic mean of per-pixel relative darkening; whole atlas includes unchanged pixels. Total luminance reduction is reported separately.",
            "coordinates": "PNG top-down row r maps to authored Unity z=9-(r+0.5)*18/height; column c maps to x=(c+0.5)*18/width-9.",
        },
        "actual_linear_statistics": stats,
        "encoded_statistics_for_legacy_comparison": encoded_statistics,
        "legacy_manifest_correction": {
            "finding": "Old manifest fields named linear were computed from sRGB encoded channel values. Its maximum/mean and ideal mip values are encoded-space measurements, not linear-light measurements.",
            "maximum_linear_darkening_before_quantization": "The recorded 0.11 cap bounded encoded RGB multiplication, not linear luminance attenuation.",
            "old_maximum_encoded_linear_luminance_darkening": legacy["maximum_encoded_linear_luminance_darkening"],
            "old_mean_encoded_linear_luminance_darkening_whole_atlas": legacy["mean_encoded_linear_luminance_darkening_whole_atlas"],
            "recomputed_encoded_max_difference_from_old": abs(encoded_statistics["maximum_encoded_luminance_darkening"] - legacy["maximum_encoded_linear_luminance_darkening"]),
            "recomputed_encoded_mean_difference_from_old": abs(encoded_statistics["mean_encoded_luminance_darkening_whole_atlas"] - legacy["mean_encoded_linear_luminance_darkening_whole_atlas"]),
            "scope": "Zero pixel differences, identical PNG hashes, alpha preservation and frozen-input checks in the old evidence remain valid.",
        },
        "path_layout_read_as_literal_from_frozen_generator": routes,
        "ideal_linear_mip_path_checks": mip_results,
        "mip_limit": "Recursive 2x2 box averages of sRGB-decoded linear RGB, sampled at mip texel centres. Does not simulate Unity compression, actual mip filtering, trilinear/bilinear sampling, or GPU output.",
        "seconds": time.time() - started,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(REPORT), "linear_statistics": stats,
                      "ideal_linear_mip_path_checks": mip_results,
                      "all_frozen_inputs_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
