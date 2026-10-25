from pathlib import Path
import json, hashlib
P=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=load(P/'manifest.json');b=load(P/'candidate-b/manifest.json')
for w in a['source_end_gap_witnesses']:
    ends={tuple(round(x,5) for x in p) for p in w['chord']}
    w['samples']=[s for s in w['samples'] if tuple(round(x,5) for x in s['point']) not in ends]
    w['omitted_points']=len(w['samples'])
    w['maximum_height_gap']=max(s['height_above_chord'] for s in w['samples'])
a['variant']='A'
a['executed_script_snapshot']='art/generated/env-v2/terrain/candidate-a-source.py'
a['executed_script_snapshot_sha256']=sha(P/'candidate-a-source.py')
a['visual_review']={'reviewed':True,'result':'A fills the actual opening but preserves an undesirable narrow raised end profile because ground is frozen; use as strict repair evidence, not the preferred silhouette.'}
b['source_end_gap_witnesses']=a['source_end_gap_witnesses']
b['source_end_gap_witness_note']='Reused exact original source witnesses from A; B modified coastline must not be used to measure the original gap.'
b['executed_script_snapshot']='art/generated/env-v2/terrain/candidate-b-source.py'
b['executed_script_snapshot_sha256']=sha(P/'candidate-b-source.py')
b['visual_review']={'reviewed':True,'result':'B removes the narrow column by lowering only protected-mask-approved, nonwalkable end vertices; remaining broad gray slopes still require further terrain art work.'}
save(P/'manifest.json',a);save(P/'candidate-b/manifest.json',b)
changes=b['coastline_vertex_changes']
summary={'preferred_candidate_for_runtime_evaluation':'B','A_checks':[len(a['checks']),sum(c['passed'] for c in a['checks'])],
 'B_checks':[len(b['checks']),sum(c['passed'] for c in b['checks'])],
 'source_ground_unmatched_edges':a['before']['seams']['ground_boundary_edges_without_cliff_partner'],
 'source_wrong_end_chords':a['before']['seams']['cliff_top_chords_not_ground_boundary'],
 'after_exact_ground_cliff_shared_edges':b['after']['seams']['exact_shared_top_edges'],
 'changed_ground_vertices_B':len(changes),'unchanged_ground_vertices_B':b['protection_rules']['core_vertices_unchanged'],
 'minimum_anchor_clearance_B':min(c['nearest_anchor_planar_distance_metres'] for c in changes),
 'minimum_road_clearance_B':min(c['distance_to_path_surface_planar_metres'] for c in changes),
 'minimum_building_clearance_B':min(c['clearance_from_house_bounding_circle_metres'] for c in changes),
 'minimum_outside_boundary_clearance_B':min(-c['signed_distance_to_walkable_boundary_metres'] for c in changes),
 'maximum_height_reduction_B':max(-c['delta_height_metres'] for c in changes),
 'cliff_triangles':b['new_triangles'],'added_cliff_triangles':b['added_triangles'],
 'requires_unity_collision_revalidation':True,
 'known_remaining_art_issue':'The tall, broad gray shore slopes are mostly material index 4 polygons on IslandGround, not CoastalCliff. Correcting a cliff-only skirt cannot reshape all of those slopes.'}
save(P/'comparison-summary.json',summary)
readme=f'''# 海岸缺口诊断与 A/B 离线修复候选

## 结论与证据

历史图里的岬角前缘竖黑缝有明确的几何缺口。旧生成器 `edge_ids` 只取地面两侧纵向边，漏掉两端各23个中间顶点；地面实际边界288条，旧崖壁只精确接上240条，另有2条跨端部弦，**48条真实边没有对应崖壁面**。岬角和北端实际端部剖面分别比错误弦最高抬起2.08m、0.68m。

`before-cape-tip.png` 使用全场同一种灰色诊断材质，仍能看到竖黑洞；这项拓扑缺失不可能靠换颜色或重算法线补好。修复从实际地面网格提取完整闭环，而非用附加石块或不透明贴片遮洞。A/B 的288条顶沿全部与地面逐边精确相接。此证据解释了这一处黑缝，不推断历史截图里的所有暗像素都来自同一原因。

## 两个候选

| 项目 | A：严格保持全部地面 | B：修正非行走海岸端部 |
|---|---|---|
| 目录 | 当前目录 | `candidate-b/` |
| 检查 | {summary['A_checks'][1]}/{summary['A_checks'][0]}通过 | {summary['B_checks'][1]}/{summary['B_checks'][0]}通过 |
| 改动地面顶点 | 0 | {summary['changed_ground_vertices_B']}，完整清单在manifest |
| 保持地面顶点 | 全部3025 | {summary['unchanged_ground_vertices_B']} |
| 石板路 | 顶点/拓扑/位姿SHA完全不变 | 同左 |
| FBX内容 | 仅CoastalCliff | CoastalCliff + IslandGround |
| 视觉结果 | 洞已封闭，但原尖锐端剖面留下支撑片状折痕 | 窄细柱消失，端部平滑下落到海岸 |

A保留为严格修洞证据。**建议根代理优先在Unity测试B**，不是直接宣称可以替换所有碰撞。所有原图、A图、B图、blend/FBX均分别保留。两版崖壁均4,608三角面，比旧968面新增3,640面，小于8,000新增预算。水下底圈约-1.8m，删掉原来延伸至约-3.4m的隐面。

## B 的保护区与实际距离

B仅调整两端附近、Walkable_Boundary之外的顶点高度，不移动XZ、不改拓扑。边界外距离至少{summary['minimum_outside_boundary_clearance_B']:.3f}m；所有改动点离最近锚点至少{summary['minimum_anchor_clearance_B']:.3f}m，离完整石板路表面投影至少{summary['minimum_road_clearance_B']:.3f}m，位于房屋保守包围圆外至少{summary['minimum_building_clearance_B']:.3f}m。房屋包围圆按旧模型XY尺寸、实例缩放并额外加0.30m计算。

变更最大降低{summary['maximum_height_reduction_B']:.3f}m，发生在原0.16m宽尖端高剖面处。`candidate-b/manifest.json` 的 `coastline_vertex_changes` 逐个列出186个索引、前后坐标、高度差、相对边界距离，以及最近锚点/道路/房基距离。核心区和所有受保护对象附近顶点逐值保留。

## 拓扑检查的含义

单独的CoastalCliff仍有顶圈和底圈边界。与地面按位置焊接后，A/B仅剩288条水下底圈开放边；没有岸顶未匹配边、分支非流形边、游离边和零面积面。它是用于游戏的开放底部地形，不是可打印的封闭实体。判断“无洞”针对可见海岸接缝，不虚称整个网格水密。

## 仍需继续做的事

- 画面高大的连续灰色裙边多数是 `IslandGround` 的外侧坡面。旧生成器对横向外16%附近多边形使用 `Cliff_SoftSlate`；`CoastalCliff`主要从地面最外沿向海下延伸。因而这轮虽完成真缺口修复和端头轮廓改善，**没有把整片外坡改造成最终层状岩壁**。进一步岩壁造型应按同样保护规则审查外坡区域，不能靠给CoastalCliff加面掩盖。
- 岩壁PBR细节未制作。新增浅层起伏、柔和裂层仅是几何基础，未声称达到对标游戏美术水平。
- 本离线blend包含原始StonePaths供对照，旧路径存在交叠和局部离地；Unity v1已有独立贴地派生网格，**不要把此处原始StonePaths重新接回去**。FBX已故意不导出它。
- A崖壁平面外鼓最大约{a['max_planar_outward_displacement_metres']:.3f}m，B约{b['max_planar_outward_displacement_metres']:.3f}m。原碰撞若覆盖这部分应检查视觉/碰撞差异。B的海岸地面改形还必须由根代理重新验证MeshCollider、出生点、灯射线和角色可走边界；本任务没有操作Unity。
- 六张每版前后图都是相同机位、1200×900的离线诊断/材质预览，不是实机夜景或FPS证明。

## 文件与复现

`manifest.json`、`candidate-b/manifest.json` 包含文件SHA256与检查。`comparison-summary.json`是两版关键量对照。`candidate-a-source.py`与`candidate-b-source.py`保存各自实际执行的脚本快照；后续主脚本可能继续演进，应以快照和已记录文件SHA查证本次候选。对照页为 `REVIEW.html`。
'''
(P/'DIAGNOSIS-AND-REPAIR.zh-CN.md').write_text(readme,encoding='utf-8')
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>海岸缺口：原版/A/B对照</title><style>body{background:#111b25;color:#e4dbc8;font:16px/1.6 system-ui;margin:24px}h1{font-size:26px}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:25px}figure{margin:0}img{width:100%;display:block}figcaption{padding:10px}a{color:#e5c07e}@media(max-width:900px){.row{grid-template-columns:1fr}}</style><h1>原版 → A 严格修洞 → B 海岸端部轮廓修正</h1><p>1200×900相同机位。首组统一灰色材质，用来区分几何洞和材质问题。B只改186个受保护区域之外的海岸端部顶点；仍需Unity碰撞验证。</p><p><a href="DIAGNOSIS-AND-REPAIR.zh-CN.md">完整诊断与限制</a> · <a href="comparison-summary.json">量化对照</a></p>'''
for view,title in [('cape-tip','岬角端头（同材质）'),('cape-oblique','岬角斜角'),('village-coast','村下海岸')]:
    html+=f'<h2>{title}</h2><div class="row">'
    for path,label in [(f'before-{view}.png','原版'),(f'after-{view}.png','A：顶沿固定，仍有细折痕'),(f'candidate-b/after-{view}.png','B：非行走端部自然下落')]:
        html+=f'<figure><img src="{path}"><figcaption>{label}</figcaption></figure>'
    html+='</div>'
(P/'REVIEW.html').write_text(html+'</html>',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
