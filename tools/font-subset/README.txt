Borrowed Light font subset tool

Dependency: fonttools==4.67.0 in the local vendor directory.
Python: tools/blender-4.5.14-windows-x64/4.5/python/bin/python.exe

From the workspace root, run:
tools\blender-4.5.14-windows-x64\4.5\python\bin\python.exe tools\font-subset\build_subset.py

The script scans every character in every Runtime C# file, including comments,
plus all ASCII code points and common Chinese punctuation / arrows. It writes
only art/generated/fonts. It never edits the live Unity font or source code.

Original CFF outlines, hinting and all relevant GSUB/GPOS layout features remain.
The modified font is renamed BorrowedLight Story Serif, retaining original
copyright / license name records and the complete SIL OFL 1.1 license.

The unchanged full source font in art/generated/fonts/source/StorySerif.otf is
created once and used as the canonical source on every later run. It is never
overwritten merely because the live Unity asset has been replaced by a subset.
Keep this original font when extending the game's text in the future.

manifest.json records input C# hashes, Unicode coverage after reopening the
written font, original / output hashes, size, layout tables and full license.
Source-absent ASCII control characters are reported rather than given fake glyphs.

The current final asset is not automatically replaced. The root build task must
copy StorySerifSubset.otf into Unity's existing StorySerif.otf slot deliberately.
