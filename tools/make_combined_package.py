"""One submission archive: Windows build + WebGL build (with its launcher) + run guide.

  python -I tools/make_combined_package.py <out.zip>
"""
import os, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
out = sys.argv[1]
parts = [
    ('借光岛_Windows', os.path.join(ROOT, 'builds/candidates/jieguang-v3-r2/windows')),
    ('借光岛_WebGL', os.path.join(ROOT, 'builds/packages/staging-web')),
]
count = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for arcroot, folder in parts:
        for base, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if 'DoNotShip' not in d]
            for f in files:
                full = os.path.join(base, f)
                z.write(full, arcroot + '/' + os.path.relpath(full, folder).replace(os.sep, '/'))
                count += 1
    z.write(os.path.join(ROOT, 'builds/packages/借光岛_运行说明.txt'), '借光岛_运行说明.txt')
    count += 1
with zipfile.ZipFile(out) as z:
    bad = z.testzip()
print('wrote', out, count, 'files', round(os.path.getsize(out) / 1e6, 1), 'MB', 'bad:', bad)
