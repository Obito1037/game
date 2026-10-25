"""Build the environment delivery review from Unity evidence and asset manifests."""
import json, html, os, struct
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v1'
EVIDENCE=ROOT/'art/verification/env-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def e(v):return html.escape(str(v))
def url(p):return quote(Path(os.path.relpath(ROOT/p,OUT)).as_posix(),safe='/')
def fig(p,label):return f'<figure><a href="{e(p)}"><img loading="lazy" src="{e(p)}" alt="{e(label)}"></a><figcaption>{e(label)}</figcaption></figure>'
def png_size(p):
    with p.open('rb') as stream:header=stream.read(24)
    if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError(f'Invalid PNG: {p}')
    return struct.unpack('>II',header[16:24])
validation=read(EVIDENCE/'validation.json')
ground=read(EVIDENCE/'ground-checks.json')
checks=validation['checks']
check_count=len(checks)
checks_passed=sum(bool(c['passed']) for c in checks)
ground_count=len(ground['samples'])
ground_passed=sum(bool(s['passed']) for s in ground['samples'])
verified=(validation['status']=='passed-structural-checks' and check_count>0 and checks_passed==check_count
          and ground['status']=='passed-ground-samples' and ground_count>0 and ground_passed==ground_count)
delivery_status='Unity 环境已交付' if verified else 'Unity 环境验收结果待处理'
parts=['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>借光岛 · Unity 环境交付审阅</title><style>
*{box-sizing:border-box}body{margin:0;background:#101d25;color:#e9e6dc;font:16px/1.6 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1320px;margin:auto;padding:40px 24px}h1{font-weight:600;font-size:32px}h2{margin-top:48px;color:#edbe77}h3{margin:8px 0}a{color:#edbe77}.muted{color:#aab7bb}.tag{display:inline-block;background:#3a3021;color:#f4ce8a;padding:5px 12px;border-radius:8px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px}.wide{grid-template-columns:repeat(2,minmax(0,1fr))}figure{margin:0;background:#172832;padding:10px;border-radius:10px}img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:#14202a}.wide img{aspect-ratio:1.6}figcaption{padding-top:8px;color:#c7d0cc}article{margin:24px 0;padding:22px;border:1px solid #32414a;border-radius:14px}summary{cursor:pointer;color:#edbe77}pre{white-space:pre-wrap;font-size:13px}p{max-width:1000px}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}.stat{padding:18px;background:#172832;border:1px solid #32414a;border-radius:10px}.stat strong{display:block;font-size:26px;color:#f4ce8a}.stat span{color:#c7d0cc;font-size:14px}code{overflow-wrap:anywhere}@media(max-width:700px){main{padding:24px 14px}.wide{grid-template-columns:1fr}h1{font-size:27px}}
</style><main>''']
parts.append(f'<span class="tag">{e(delivery_status)}</span><h1>借光岛 · Unity 环境交付审阅</h1><p>当前交付为可放入场景的 <code>Island.prefab</code>。Unity Build、结构检查、地面采样和四机位截图已完成；人物与章节剧情由 Claude 接入。</p><p><a href="HANDOFF.zh-CN.md">完整交接</a> · <a href="TO_CLAUDE.zh-CN.txt">Claude 接手说明</a> · <a href="manifest.json">总清单</a> · <a href="inventory.json">原始盘点</a></p>')
parts.append('<div class="stats">')
for value,label in [(f'{checks_passed}/{check_count}','Unity 结构检查通过'),(f'{ground_passed}/{ground_count}','地面采样通过'),(f'{validation["activeLod0Triangles"]:,}','最高 LOD 三角面'),(f'{validation["trianglesIncludingBothLods"]:,}','含备用 LOD 三角面')]:
    parts.append(f'<div class="stat"><strong>{e(value)}</strong><span>{e(label)}</span></div>')
parts.append(f'</div><p class="muted">两项三角面统计均含天空与海面（共 {validation["skyAndSeaTriangles"]:,} 面）；备用 LOD 合计是资产统计。{validation["lodGroups"]} 个 LODGroup，{validation["windows"]} 扇独立村窗，{validation["spotlights"]} 盏谜题 Spot。<a href="{url(EVIDENCE/"validation.json")}">结构检查原始报告</a> · <a href="{url(EVIDENCE/"ground-checks.json")}">地面采样原始报告</a></p>')
parts.append('<p class="muted">地面检查包含 3 个高度差不超过 0.03 米的新增贴地锚点。持续 FPS、角色胶囊全路线通行、角色与剧情联调仍待验证；本页没有 draw call 测量结果。</p><h2>Unity 实际场景截图 · 1440×900</h2><p>以下四张来自 EnvTest 场景的实际 Unity 渲染。点击图片可查看完整尺寸。</p><div class="grid wide">')
for filename,label in [('01-title.png','标题 · 全岛俯瞰'),('02-cape.png','岬角'),('03-pier.png','码头'),('04-village.png','村子')]:
    path=EVIDENCE/filename
    width,height=png_size(path)
    if (width,height)!=(1440,900):raise ValueError(f'Unexpected Unity capture size: {path}: {width}x{height}')
    parts.append(fig(url(path),f'{label} · Unity 实际截图 · {width}×{height}'))
parts.append(f'</div><p class="muted"><a href="{url(EVIDENCE/"captures.json")}">截图记录</a> · <a href="{url(ROOT/"GameProject/Assets/JieGuang/Environment/Island.prefab")}">Island.prefab</a> · <a href="{url(ROOT/"GameProject/Assets/JieGuang/Environment/EnvTest.unity")}">EnvTest.unity</a></p>')
parts.append('<h2>历史 Blender 离线预览 · 1200×750</h2><p class="muted">这些图片保留 Unity 导入前的场景布局与美术制作过程，属于历史离线图。最终导入后的场景效果见上方 Unity 实际截图。</p><div class="grid wide">')
for name,label in [('Cam_Title','全岛俯瞰'),('Cam_Puzzle','岬角'),('Cam_Pier','码头'),('Cam_Village','村子')]:
    path=OUT/'preview'/f'{name}.png'
    if path.exists():
        width,height=png_size(path)
        parts.append(fig(url(path),f'{label} · 历史 Blender 离线图 · {width}×{height}'))
parts.append('</div><p class="muted"><a href="preview/status.json">历史预览尺寸与场景哈希</a> · <a href="package-validation.json">离线完整性核验</a></p><h2>下载模型与清理结果</h2>')
processed=read(OUT/'asset-manifest.json')['assets'] if (OUT/'asset-manifest.json').exists() else []
for a in read(OUT/'inventory.json')['assets']:
    parts.append(f'<article><h3>{e(a["source"])}</h3><p class="muted">原始 {a["triangles"]:,} 三角面 · {a["object_count"]} 个物体 · SHA256 <code>{a["sha256"][:16]}…</code></p><details><summary>原始三视图：包含须剔除的展示物</summary><div class="grid">')
    for k,p in a['previews'].items():parts.append(fig(url(p),{'front':'正视','side':'侧视','top':'俯视'}.get(k,k)))
    parts.append('</div></details>')
    for b in [b for b in processed if b['source_id']==a['id']]:
        parts.append(f'<h3>{e(b["id"])}</h3><p>LOD0 {b["lod0"]["triangles"]:,} 面'+(f' · LOD1 {b["lod1"]["triangles"]:,} 面' if b.get('lod1') else '')+f'</p><div class="grid">')
        for k,p in b.get('previews',{}).items():parts.append(fig(url(p),k))
        parts.append(f'</div><p class="muted">{e(b.get("review","尚待目视检查"))}</p>')
    parts.append('</article>')
parts.append('<h2>程序化占位道具</h2><p>16 类道具已通过 Blender 的 FBX 回导检查；需要更精致模型的项目见交接文档。</p><div class="grid">')
for a in read(OUT/'props/manifest.json')['assets']:
    aid=a['asset_id'];parts.append(fig(f'props/{aid}/preview.png',f'{aid} · {a["triangles"]:,} 面'))
parts.append('</div></main></html>')
(OUT/'REVIEW.html').write_text(''.join(parts),encoding='utf-8')
print('Wrote art/generated/env-v1/REVIEW.html')
