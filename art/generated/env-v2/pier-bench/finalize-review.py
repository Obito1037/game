"""Create the offline pier/bench review index without touching model assets."""
from pathlib import Path
import json,hashlib,struct,re
OUT=Path(__file__).parent;ROOT=OUT.parents[3]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assets=['pier_module','pier_end','bench'];aggregate=read(OUT/'manifest.json');fresh=read(OUT/'fresh-process-verification.json')
verification={'fresh_process_checks_pass':fresh['all_pass'],'assets':[],'pngs':[],'file_hashes':[]}
for asset in assets:
    record=read(OUT/asset/'manifest.json');source=read(OUT/asset/'source-inventory.json')
    verification['assets'].append({'asset_id':asset,'source_hash_matches':sha(ROOT/source['source'])==source['source_sha256'],
        'geometry_before_after_hash_identical':record['geometry_before_sha256']==record['geometry_after_sha256'],
        'source_and_candidate_triangles':record['after_triangles'],'added_triangles':record['additional_triangles'],
        'checks_all_pass':all(record['checks'].values()),'roundtrip_checks_all_pass':record['fbx_roundtrip']['all_pass']})
    for f in record['files']:
        verification['file_hashes'].append({'path':f['path'],'hash_matches':sha(ROOT/f['path'])==f['sha256']})
    for p in sorted((OUT/asset).glob('*.png')):
        with p.open('rb') as stream:header=stream.read(24)
        size=list(struct.unpack('>II',header[16:24]));verification['pngs'].append({'path':str(p.relative_to(OUT)),'size':size,'size_900x900':size==[900,900]})
verification['original_texture_sha256']=sha(ROOT/'art/generated/env-v2/textures/wood_albedo_v1.png')
verification['texture_hash_matches']=verification['original_texture_sha256']=='2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1'
verification['source_manifest_hash_matches']=sha(ROOT/'art/generated/env-v1/props/manifest.json')==aggregate['source_manifest_sha256']
verification['scene_input_hash_matches']=sha(ROOT/aggregate['scene_input'])==aggregate['scene_input_sha256']
verification['all_pass']=fresh['all_pass'] and verification['texture_hash_matches'] and verification['source_manifest_hash_matches'] and verification['scene_input_hash_matches'] and len(verification['pngs'])==24 and all(x['size_900x900'] for x in verification['pngs']) and all(x['hash_matches'] for x in verification['file_hashes']) and all(x['source_hash_matches'] and x['geometry_before_after_hash_identical'] and x['checks_all_pass'] and x['roundtrip_checks_all_pass'] for x in verification['assets'])
dump(OUT/'final-verification.json',verification)
decision={'status':'offline-visually-recommended-pending-root-unity-review','actual_added_island_triangles':0,
    'instance_counts':{'pier_module':3,'pier_end':0,'bench':1},'assets':assets,
    'accepted_scope':'UV/material surface improvement only; all authored geometry, markers and bounds unchanged.',
    'not_claimed':['Unity imported appearance','three-module repeat/seam runtime test','collision or seat playtest','FPS','new bevels/nails/wear geometry','dedicated annual-ring/normal/roughness textures'],
    'visual_risks':['Wood remains relatively clean; no authored dirt edge mask.','Fine grain can compete with seams; review Unity mipmaps and repeated modules.','End caps reuse planar wood grain rather than dedicated annual rings.'],
    'evidence':['REVIEW.html','REVIEW.zh-CN.md','fresh-process-verification.json','final-verification.json','INTERFACE-AUDIT.zh-CN.md']}
dump(OUT/'decision.json',decision)
aggregate['status']=decision['status'];aggregate['decision']='decision.json';aggregate['final_verification']='final-verification.json';dump(OUT/'manifest.json',aggregate)
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>栈桥与长椅：离线表面对照</title><style>body{max-width:1380px;margin:32px auto;padding:0 22px;background:#19232c;color:#e6e4da;font:16px/1.6 system-ui}h1{font-size:27px}label{margin-right:20px}select{padding:8px;background:#33424b;color:#fff;border:1px solid #61717a;border-radius:5px}main{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0}img{width:100%;display:block}figcaption{padding:10px;color:#c6c8c5}a{color:#e1bb78}.note{color:#bdc5cc}code{font-size:14px}@media(max-width:760px){main{grid-template-columns:1fr}}</style><h1>栈桥与长椅 · 只改木纹与材质</h1><p>原几何、尺寸、桥板顶面、座面、Marker 完全冻结；实际岛上 3 段栈桥 + 1 张长椅，新增 0 三角面。末端平台目前未放在岛中。</p><p><label>模型 <select id="asset"><option value="pier_module">栈桥段 · 456 tris</option><option value="pier_end">末端平台 · 668 tris · 未实例化</option><option value="bench">长椅 · 324 tris</option></select></label><label>光线 <select id="light"><option value="neutral">中性</option><option value="night">冷夜 / 暖灯</option></select></label><label>镜头 <select id="view"><option value="surface">表面</option><option value="whole">完整</option></select></label></p><main><figure><img id="before" alt="原模型同机位"><figcaption>原模型</figcaption></figure><figure><img id="after" alt="材质候选同机位"><figcaption>候选：同一几何，原创新木纹沿木材长轴</figcaption></figure></main><p class="note">全部图片为 Blender 真实 900 × 900 渲染，同机位、同照明。未进入 Unity；这里不是运行时画质或性能验证。木色仍偏干净，端面未制作独立年轮图，细纹和重复模块需实景复查。</p><p><a href="REVIEW.zh-CN.md">完整审阅</a> · <a href="final-verification.json">最终验证</a> · <a href="fresh-process-verification.json">独立进程回读</a> · <a href="INTERFACE-AUDIT.zh-CN.md">岛内接口审计</a></p><script>const names=['asset','light','view'];function update(){const[a,l,v]=names.map(n=>document.getElementById(n).value);for(const p of ['before','after'])document.getElementById(p).src=`${a}/${p}-${l}-${v}.png`;}for(const n of names)document.getElementById(n).onchange=update;update();</script></html>'''
(OUT/'REVIEW.html').write_text(html,encoding='utf-8')
lines=['# 栈桥与长椅离线材质候选','',
'结论：三件作为**表面升级候选**推荐给 root 进 Unity 审阅，未自动接入。只改 UV、木纹贴图和木材色/粗糙度；没有新增几何，不能声称已经做了新磨损、沉钉或倒角。现有长椅已有圆角，栈桥的几何没有必要为增加细节而重做。','',
'## 真实基线与保持项','',
'| 模型 | 原 / 候选三角面 | 实际实例数 | 岛内新增 |','|---|---:|---:|---:|',
'| pier_module | 456 / 456 | 3 | 0 |','| pier_end | 668 / 668 | 0 | 0 |','| bench | 324 / 324 | 1 | 0 |','',
'直接读取 env-v1/props 下最新 blend，所有源文件 SHA256 在各自 source-inventory.json。栈桥桩底保留 Blender Z=-3.20 米，没有从旧函数重建短桩。所有顶点、面索引、材质槽/面索引、平滑标记、对象矩阵、Marker 父级与矩阵、整体包围盒逐值一致；只改 UV 和材质节点。桥板 Z=0、长椅座面 Z=.45 的顶点单独列出并逐值核对。','',
'真实 prefab 接口由独立审计记录于 INTERFACE-AUDIT.zh-CN.md：栈桥 3 个独立 WalkableDeck BoxCollider 连续；长椅原 Structure 上 MeshCollider 必须保留旧 sharedMesh 和组件。Marker_Seat 是坐面位置契约，人物朝向以 NPC_Bench 为准，不能误用导入 Marker.forward。此次没有操作 Unity 或测试落座/碰撞。','',
'## 表面实现与局限','',
'复用原创新木纹 env-v2/textures/wood_albedo_v1.png，真实 1254×1254，SHA256 2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1。未改图像像素。每个独立木件按 PCA 长轴定向，V 沿木长，U=1 米、V=4.9 米；使用图内 V 范围避免有问题的纵向平铺边。端面用同图局部平面投影，**没有专用年轮、法线或粗糙度图**。已 pack 原图进候选 blend。FBX 不保证携带 Blender 的乘色节点，Unity 应显式用下表原图×颜色及 roughness 转 smoothness。','',
'| 原槽名 | 建议共享名 | Base tint RGB | Roughness / Unity smoothness |','|---|---|---|---|',
'| Wood_Endgrain | CoastalWood_Light | .62, .57, .46 | .88 / .12 |',
'| Wood_Honey | CoastalWood_Brown | .48, .42, .33 | .87 / .13 |',
'| Wood_DarkBeams | CoastalWood_Dark | .26, .22, .17 | .90 / .10 |',
'| Wood_Weathered | CoastalWood_Silver | .38, .38, .32 | .92 / .08 |','',
'Wood_Endgrain 是历史槽名，实际也包含整块木板，不应按名字给整块木板改年轮。Iron_Blackened 原材质不改。这里四共享名不同于屋子的四木色；既有 HouseSurfaceBuilder 没有 Wood_Weathered，不能假定调用屋材映射就覆盖栈桥。该轮没有新增 C# 或指定未经验证的整合入口。','',
'## 目视判断','',
'实际查看所有三件的中性/夜间、全景/表面前后 PNG：板面与靠背木纹顺长轴，桥桩和腿部顺竖向；暖灯下木材可读性比原纯色块明确，未观察到新黑缝、共面闪黑或轮廓变化。长椅原有圆角、薄靠背和腿部结构保持。末端平台仅离线准备，不能说它已经改善了岛上的码头。','',
'独立环境审阅代理还检查了 pier_module 四张 surface 图，确认方向正确、未见突兀接缝，建议不加面。保留意见：木纹较细且平行，夜图中部深纹会与真实板缝竞争，中性木色偏新；桩顶是平行木纹而非年轮。当前单件镜头不证明三段重复、mipmap 或中远景闪烁已验证。','',
'## 证据与接入前事项','',
'每款 8 张真实 900×900 Cycles 渲染，总计 24 张；同款 before/after 使用相同相机、世界、灯光和曝光。2 个视角不是完整后方/底面全覆盖；无新增几何，源有结构缺陷如需修复应另立变更，不能据此声称无所有缺陷。','',
'fresh-process-verification.json 从新 Blender 进程重开原 blend / 候选 blend，再导入导出 FBX；核对完整几何合同、packed 原图、三角面、原槽、所有根/Marker 矩阵、双向顶点集合与 UV 角点集合。最大误差记在报告中；没有把请求尺寸当实际 PNG 尺寸。final-verification.json 另核对文件 SHA、源文件/纹理未变与 24 张 PNG 尺寸。','',
'root 后续若采用，应只换视觉 MeshFilter 与材料，保留旧长椅 MeshCollider sharedMesh；不要 SetActive(false) 整个带碰撞的 Structure。桥界、3 个 WalkableDeck、NPC_Bench、全岛锚点保持；检查三段板纹重复/过滤、灯下是否过亮、角色坐面和通行。无 Unity/FPS/全岛最终质量结论。','',
'文件路径：`art/generated/env-v2/pier-bench/{pier_module|pier_end|bench}/{asset}_v2_candidate.blend/.fbx`；生成脚本 `art/blender/env_v2_pier_bench.py`。未修改 Assets、旧 v1、Claude 文件、总 HANDOFF 或 CandidateBuilder。','']
(OUT/'REVIEW.zh-CN.md').write_text('\n'.join(lines),encoding='utf-8')
print('PIER_BENCH_FINAL',verification['all_pass'],len(verification['pngs']),len(verification['file_hashes']))
if not verification['all_pass']:raise RuntimeError('Final checks failed')
