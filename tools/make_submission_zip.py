"""Zips a built game folder for submission, skipping Unity's DoNotShip debug folders.

  python -I tools/make_submission_zip.py <out.zip> <arcroot> <folder> [extra_file ...]
"""
import os, sys, zipfile

out, arcroot, folder = sys.argv[1], sys.argv[2], sys.argv[3]
extras = sys.argv[4:]
os.makedirs(os.path.dirname(out), exist_ok=True)
count = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if 'DoNotShip' not in d]
        for f in files:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, folder).replace(os.sep, '/')
            z.write(full, arcroot + '/' + rel)
            count += 1
    for e in extras:
        z.write(e, os.path.basename(e))
        count += 1
print('wrote', out, count, 'files', round(os.path.getsize(out) / 1e6, 1), 'MB')
