"""按《参赛作品材料提交规范》第十节目录打包第 6 项参赛打包文件（匿名）。

  python -I tools/make_submission_v3.py <out.zip>
"""
import os, sys, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
P = lambda *a: os.path.join(ROOT, *a)
out = sys.argv[1]
TOP = '借光岛_参赛打包文件'
folders = [
    ('01_作品及成果文件/借光岛_Windows', P('builds/candidates/jieguang-v3-r2/windows')),
    ('01_作品及成果文件/借光岛_WebGL', P('builds/packages/staging-web')),
    ('03_作品介绍文档', P('builds/packages/submission-v3/03_作品介绍文档')),
    ('04_运行或使用说明', P('builds/packages/submission-v3/04_运行或使用说明')),
    ('06_第三方资源说明', P('builds/packages/submission-v3/06_第三方资源说明')),
    ('07_AI工具使用补充说明', P('builds/packages/submission-v3/07_AI工具使用补充说明')),
]
files = [
    ('02_作品展示视频/借光岛_作品展示视频.mp4', P('art/demo-video/借光岛_作品评审视频.mp4')),
    ('04_运行或使用说明/借光岛_运行说明.txt', P('builds/packages/借光岛_运行说明.txt')),
]
n = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for arc, src in folders:
        for base, dirs, fs in os.walk(src):
            dirs[:] = [d for d in dirs if 'DoNotShip' not in d]
            for f in fs:
                full = os.path.join(base, f)
                z.write(full, f'{TOP}/{arc}/' + os.path.relpath(full, src).replace(os.sep, '/'))
                n += 1
    for arc, src in files:
        # video is already compressed: store it
        z.write(src, f'{TOP}/{arc}', compress_type=zipfile.ZIP_STORED if src.endswith('.mp4') else zipfile.ZIP_DEFLATED)
        n += 1
with zipfile.ZipFile(out) as z:
    bad = z.testzip()
print('wrote', out, n, 'files', round(os.path.getsize(out) / 1e6, 1), 'MB', 'bad:', bad)
