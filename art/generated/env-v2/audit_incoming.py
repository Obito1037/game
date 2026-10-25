"""Read-only local asset audit. Writes only two reports beside this script."""
from pathlib import Path
import hashlib, json, struct, re, datetime

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DOWNLOADS = Path('C:/Users/20665/Downloads')
ENV = ROOT / 'GameProject/Assets/JieGuang/Environment'

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def file_record(p):
    rec = {'path':str(p).replace('\\','/'), 'format':p.suffix.lower().lstrip('.'),
           'bytes':p.stat().st_size, 'sha256':digest(p)}
    if p.suffix.lower()=='.png':
        with p.open('rb') as f: head=f.read(24)
        if head[:8]==b'\x89PNG\r\n\x1a\n': rec['pixel_dimensions']=list(struct.unpack('>II', head[16:24]))
    if p.suffix.lower()=='.glb':
        with p.open('rb') as f:
            magic,version,length=struct.unpack('<4sII',f.read(12))
            size,kind=struct.unpack('<II',f.read(8))
            data=json.loads(f.read(size))
        rec['glb_version']=version
        rec['mesh_count']=len(data.get('meshes',[]))
        rec['material_count']=len(data.get('materials',[]))
        rec['embedded_image_count']=len(data.get('images',[]))
        tris=0
        for mesh in data.get('meshes',[]):
            for prim in mesh.get('primitives',[]):
                if prim.get('mode',4)==4:
                    ix=prim.get('indices',prim['attributes'].get('POSITION'))
                    tris += data['accessors'][ix]['count']//3
        rec['source_triangle_count_from_glb_accessors']=tris
        rec['axis']='glTF Y-up; dimensions not remeasured in Blender in this audit'
    return rec

all_download_files = sorted(p for p in DOWNLOADS.rglob('*') if p.is_file())
v2_files=[p for p in all_download_files if re.search(r'(?:借光岛_v2|v2_[A-Z]\d{2}|(?:^|[ _])[TVSU]\d{2})',str(p),re.I)]
old_glbs=[p for p in DOWNLOADS.glob('*.glb') if re.search('发光树|灯光盆景|岩石|木质小艇',p.name)]
reference_dirs=[p for p in DOWNLOADS.iterdir() if p.is_dir() and '%E5%80%9F' in p.name]
old_references=[p for d in reference_dirs for p in d.rglob('*') if p.is_file()]
source_manifest=load(ROOT/'art/generated/env-v1/asset-manifest.json')
source_by_sha={a['source_sha256']:a['id'] for a in source_manifest['assets']}
source_by_path={}
for a in source_manifest['assets']:
    source_by_path.setdefault(a['source_sha256'],[]).append(a['id'])

source_records=[]
for p in old_glbs:
    r=file_record(p)
    r['role']='v1 source; not a new v2 model'
    r['existing_derived_assets']=source_by_path.get(r['sha256'],[])
    source_records.append(r)

models=[]
for p in sorted((ENV/'Models').rglob('*.fbx')):
    r=file_record(p)
    stem=p.stem
    if '/Props/' in str(p).replace('\\','/'):
        info=ROOT/'art/generated/env-v1/props'/stem/'asset.json'
        if info.exists():
            x=load(info)
            r.update({'asset_id':stem,'authored_triangles':x['triangles'],
                      'dimensions_blender_xyz_metres':x['dimensions_metres'],
                      'authoring_metadata':str(info.relative_to(ROOT)).replace('\\','/')})
    else:
        name=re.sub(r'_LOD\d$','',stem)
        matches=[a for a in source_manifest['assets'] if a['id']==name]
        if matches:
            a=matches[0]
            r.update({'asset_id':name,'dimensions_unity_xyz_metres':a['dimensions_xyz_unity_metres'],
                      'authoring_metadata':'art/generated/env-v1/asset-manifest.json'})
    models.append(r)

textures=[file_record(p) for p in sorted((ENV/'Textures').rglob('*')) if p.is_file() and p.suffix.lower() in ['.png','.jpg','.jpeg']]
materials=[]
for p in sorted((ENV/'Generated/Materials').glob('*.mat')):
    r=file_record(p)
    txt=p.read_text(encoding='utf-8-sig')
    r['nonzero_texture_guids']=sorted(set(re.findall(r'm_Texture: \{fileID: (?!0[,}])\d+, guid: ([a-f0-9]+)',txt)))
    r['has_any_texture_reference']=bool(r['nonzero_texture_guids'])
    for name in ['_BaseColor','_EmissionColor']:
        m=re.search(re.escape(name)+r': \{([^}]+)\}',txt)
        if m:r[name]=m.group(1)
    for name in ['_Metallic','_Smoothness','_BumpScale']:
        m=re.search(re.escape(name)+r': ([^\r\n]+)',txt)
        if m:r[name]=m.group(1)
    materials.append(r)

# IDs follow the supplied v2 prompt. Descriptive filename stems beyond its explicit examples are not invented contracts.
requirements=[]
def req(id,label,owner,existing,action,filename=None):
    found=[p for p in v2_files if re.search(r'v2_'+re.escape(id)+r'(?:_|\.)',p.name,re.I)]
    requirements.append({'id':id,'label':label,'owner':owner,'provided_v2_files':[str(p).replace('\\','/') for p in found],
        'status':'present-unvalidated' if found else 'new-v2-source-not-found',
        'expected_filename':filename,'existing_fallback':existing,'suggested_action':action})

rows=[
('A01','阿婆木屋','abode_grandma','程序化升级或替换；当前无阁楼，圆窗和门必须保持锚点','v2_A01_grandma_house.fbx'),
('A02','书桌组合','abode_grandma 中内置桌椅书本','程序化补纸页、墨水瓶、陶罐、披肩；不挡圆窗','v2_A02_desk_set.fbx'),
('A03','金色光树','tree_gold','现树可用，硬边与重建粘连需美术改进；新高质量单树可替换','v2_A03_golden_tree.fbx'),
('A04','第一朵花','环境目录无独立花模型','可原创程序化；终章启用由 Claude 接口控制','v2_A04_first_flower.fbx'),
('A05','路灯灯柱','copper_roadlamp 内含','程序化倒角、铜锈、手柄，不移动灯轴','v2_A05_lamp_post.fbx'),
('A06','路灯灯头','copper_roadlamp 内含','程序化修边与铜材质，保留 LampHead 转轴和 +Z 光向','v2_A06_lamp_head.fbx'),
('A07','宽罩与窄罩','copper_roadlamp 非两件独立资产','可程序化分件；形态切换需 Claude 协调','v2_A07_shade_wide.fbx / v2_A07_shade_narrow.fbx'),
('A08','长椅','bench','程序化细化木板、磨损并保留坐面','v2_A08_bench.fbx'),
('A09','路口大石头','rock_cluster 复用','现资产可复用，修粗糙度与地面接触','v2_A09_boulder.fbx'),
('A10','浑天仪石台','armillary_platform','程序化倒角、铜环刻度和底座细节','v2_A10_armillary.fbx'),
('A11','月牙雕塑','crescent_sculpture','程序化细化，保持原创轮廓','v2_A11_crescent.fbx'),
('A12','栈桥直段','pier_module','程序化木纹、板缝、桩绳；连续碰撞保持','v2_A12_pier_segment.fbx'),
('A13','栈桥平台','pier_end','同栈桥直段；不得缩窄 NPC 路径','v2_A13_pier_end.fbx'),
('A14','旗杆','flagpole_blue 含旗面','分离旗面与杆，保留铁钩世界坐标','v2_A14_flagpole.fbx'),
('A15','蓝旗图案与旗面','flagpole_blue 几何图案','可原创程序化布面/图案；不是现有 PNG 贴图','v2_A15_flag.png'),
('A16','港灯','harbor_lantern','程序化铜玻璃细化，保留 HarborLight 与熄灯接口','v2_A16_harbor_lantern.fbx'),
('C01','采光船','ReturningBoat 复用 boat','现小艇不具备 7m 采光船轮廓；优先建原创新船或用户 Tripo','v2_C01_light_ship.fbx'),
('C02','码头小艇','boat','可复用现木艇；修中性材质和水线','v2_C02_rowboat.fbx'),
('C03','蓝绿瓦村屋','cottage_teal','可程序化升级三种屋顶和窗木纹','v2_C03_house_teal.fbx'),
('C04','赭红瓦村屋','cottage_ochre','同 C03，轮廓应有差异',None),
('C05','灰瓦村屋','cottage_slate','同 C03，保留独立可控窗',None),
('C06','水井','village_well','可程序化细化井石、木架和绳桶','v2_C06_well.fbx'),
('C07','晾衣绳','laundry_line','可程序化布曲面与微风摆动','v2_C07_laundry.fbx'),
('C08','村口老光树','tree_b 等复用','可先改材质与树簇，独立英雄轮廓缺失','v2_C08_village_tree.fbx'),
('D01','高挑光树','tree_a','现树复用；需修叶簇硬边','v2_D01_tree_tall.fbx'),
('D02','圆冠光树','tree_b','现树复用；需修叶簇硬边',None),
('D03','坡地老树','tree_c','现树复用；根部接地',None),
('D04','光树树苗','tree_a_sapling_01 / 02','现树苗复用；支撑杆可程序化',None),
('D05','低矮岩堆','rock_cluster','现石材复用，不是新模型','v2_D05_rocks_low.fbx'),
('D06','尖峰岩堆','rock_mountain','现石材近似，不是逐参考精确轮廓',None),
('D07','平坦岩台','rock_mass 近似','可程序化重塑轮廓，当前非专用平坦台',None),
('D08','海岸岩拱','rock_arch','现岩拱复用',None),
('D09','陡峭岩柱','无独立专用模型','可程序化不规则柱，不必等用户',None),
('D10','海岸礁石','rock_cluster_reef_01 / 02','现礁石复用',None)]
for id,label,existing,action,fn in rows:req(id,label,'GPT 环境',existing,action,fn)
for id,label,fn in [('B01','手提灯笼','v2_B01_lantern.fbx'),('B02','光果','v2_B02_light_fruit.fbx'),('B03','萤火虫信','v2_B03_firefly_letter.fbx'),('B04','木杖','v2_B04_cane.fbx')]:
    req(id,label,'Claude 道具/剧情','未深入审计 Claude 所有运行时生成对象，不能据 Environment 缺失判定游戏缺失','由 Claude 管理；新源未到货',fn)
for id,label in [('T01','草地'),('T02','石板路'),('T03','泥土路'),('T04','海岸崖壁'),('T05','旧木板'),('T06','三色屋顶陶瓦'),('V01','草叶卡'),('V02','野花卡'),('V03','蕨与灌木卡'),('V04','光树叶簇卡'),('S01','全景夜空'),('S02','细弧地球'),('S03','远海岛影')]:
    req(id,label,'GPT 环境','旧材质/程序化 Shader 可作基础；未找到该 v2 独立图','可原创程序化纹理/网格/Shader，不应阻塞迭代；用户新图到货后再验收')
for i in range(1,14):req(f'U{i:02}','UI 2D 图','Claude UI','不审计 Claude 当前 UI 图形','新图未到货；交由 Claude 接入，不能导入对标截图')
for i in range(1,6):req(f'P{i:02}','可选人物重做','Claude 人物','已有 v1 人物属 Claude 范围','新源未到货；不得覆写 Claude 人物')

scene=load(ENV/'scene-input.json')
anchor_data=scene.get('anchors',[])
report={'schema_version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope':'Read-only filesystem audit; no Blender reimport, no Unity operations, no benchmark asset download.',
    'v2_drop_directory':str(DOWNLOADS/'借光岛_v2模型').replace('\\','/'),
    'v2_drop_directory_exists':(DOWNLOADS/'借光岛_v2模型').exists(),
    'downloads_files_scanned':len(all_download_files),'nearby_v2_candidates':[file_record(p) for p in v2_files],
    'old_source_models':source_records,'old_concept_references':[file_record(p) for p in old_references],
    'existing_environment_models':models,'existing_environment_textures':textures,'existing_environment_materials':materials,
    'required_v2_assets':requirements,'anchor_contract_source':'GameProject/Assets/JieGuang/Environment/scene-input.json',
    'anchor_contract_source_sha256':digest(ENV/'scene-input.json'),'anchors_preserve_exactly':anchor_data,
    'limits':['Missing v2 drop folder is observed now, not proof user has not generated models online.',
              'Existing source dimensions are authoring metadata, not a new Blender measurement.',
              'File bytes / hash verify presence and identity, not visual quality or Unity rendering.',
              'No FPS or gameplay claims are made.']}
(OUT/'incoming-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

md=['# 环境 v2 到货盘点与资产缺口', '',f"盘点时间（UTC）：{report['created_utc']}。只读检查本机 Downloads 与当前 Environment；未进入 Unity，未导入/下载任何对标资产。",'',
'## 结论','',
f"`Downloads/借光岛_v2模型/` **不存在**。递归检查 Downloads 的 {len(all_download_files)} 个文件，没有找到命名为 `v2_*` 或以 T/V/S/U 编号交付的新素材。现阶段不能声称已收到第二版 Tripo 模型或第二版贴图。用户是否已在网页生成未检查。",'',
f"可复用的是 **{len(source_records)} 个旧 GLB 源模型、{len(models)} 个现有导入 FBX、{len(textures)} 张环境 PNG、{len(materials)} 份环境材质**。旧“剩余10项”目录内 {len([p for p in old_references if p.suffix=='.png'])} 张 PNG 是概念图，并不是新 3D 文件。完整大小、格式、SHA256、PNG 尺寸及现有模型元数据见 `incoming-inventory.json`。",'',
'## 当前材质缺口','',
f"{len([m for m in materials if not m['has_any_texture_reference']])}/{len(materials)} 份 `.mat` 没有非零纹理引用。树、岩石、木艇虽有颜色贴图，但并不构成所有道具的木纹、金属磨损、布纹、瓦面细节。仅有图像文件数量不能证明质量已达标。阿婆屋当前作者尺寸约4.63×3.96×4.49m（Unity XYZ），原 v2 提示期望6×5.5×5m；必须围绕不变的窗/门/座点调整几何，不能整体缩放然后移动剧情锚点。",'',
'阿婆屋缺阁楼是已知模型缺项；采光船仍由小艇族复用，缺独立大船轮廓。主金树叶边硬和旧图光照烘入色图的风险需视觉检查后处理。地面、屋顶、木材、织物目前主要依赖纯色与低模形体，优先增加可辨的表面层次。', '',
'## 逐项对照','',
'所有下表 v2 新源均未在 Downloads 找到；“已有”只表示现有可用基础。', '',
'| 编号 | 目标 | 现有基础 | 下一步 |','|---|---|---|---|']
for r in requirements:
    md.append('| '+ ' | '.join([r['id'],r['label'],r['existing_fallback'],r['suggested_action']])+' |')
md+=['','## 无需等待新资产即可推进','',
'1. 草丛、野花、蕨类与灌木：原创低面网格/卡片，按坡度与小路排除区散布；种类、密度、风动和远距衰减做成环境内参数，避免草挡灯/窗/坐点。',
'2. 木板、石面、铜锈和瓦面：可原创程序化纹理或 Shader，控制低频色差、细纹、粗糙度与边角磨损；先在同机位比较，别把噪点堆成脏污。',
'3. 灯柱、浑天仪、长椅、栈桥、旗杆、水井：已有原创程序模型可细化倒角、形变和分材质；维持原碰撞面与玩法空间。',
'4. 云、海面、雾层与星空：可继续原创 Shader/网格；蓝白地球是细弧，夜晚世界观不改，不放太阳。章节参数与 Claude 的剧情天空协调。',
'5. 阿婆屋阁楼、首花、窄/宽灯罩、岩柱：可以原创程序化补齐，保持剧情名称和世界坐标；不能据“无 Tripo 文件”宣称这些工作无法做。','',
'## 用户资产到货后才可完成的特定工作','',
'- **用户生成的指定 v2 资产**的清理、减面、LOD、PBR 贴图校验、切割、轴心和替换，必须先有对应真实文件。不能用现有 v1 重命名假称新模型接入。',
'- 如用户希望最终外形严格采用已生成参考图，需要相应图和模型；目前没有足够文件对某个 v2 Tripo 成品作几何或视觉验收。',
'- 金色主树、阿婆木屋、采光船的美术上限更依赖原创造型质量。新源有帮助，但并非只能等用户；当前可先改善既有资产，并诚实记录仍未达到的细节。',
'- UI 插图与角色由 Claude 管理；这里只登记到货状态，不进入其目录修改。','',
'## 替换模型时不可破坏的接口','',
'- 完整25个输入锚点坐标/方向已从当前 `Environment/scene-input.json` 原样记录在 JSON；`Village_Windows`、散点范围与可走边界还包括组装器生成的对象。最终应校验实际 Prefab 层级，不能只验证输入表。',
'- `Anchor_PlayerSpawn`；三灯 `Anchor_Lamp_WanFeng/YueChuang/GuiHang`；`Target_Path/Bench/Window/Pier`；`Anchor_FlagpoleHook`；五个 NPC 站/坐点；三个主要镜头点全部保持名称与位置。',
'- 追加的 `Anchor_VillageGate`、`Anchor_GoldenTree`、`Anchor_Boat`、`Target_Sea`、`NPC_ABo_Door` 也不移动。船根应继续与 Anchor_Boat 同姿态。',
'- `LampHead` 转轴原点和 +Z 光向保留，实际谜题 Spot 仍只有三盏；更换灯头外观时不能复制第二个 Spot。宽/窄罩外观分件需与 Claude 切换接口对齐。',
'- 圆窗必须真开口，书桌与阿婆座点仍可见；灯到目标的射线不被新增玻璃碰撞、草丛或装饰误挡。门外点保持脚底高度，座点仍为骨盆/接触高度。',
'- `Village_Windows` 下22扇窗独立控制，不随村屋合批吞掉；父中心保持(-13,8.4,10)。',
'- `ReturningBoat` 与 `HarborLantern/HarborLight` 路径/命名延续；亮灭要兼顾 Light 和玻璃发光颜色，不能共享材质连带改掉三灯。',
'- Layer8 为可走地面与栈桥、Layer9 为实体碰撞；陆地 Walkable_Boundary 与 PierBoundary 取并集。原FBX根的反射修正不能再次套在新文件上，先测轴再适配。',
'- 材质升级不能要求改 ProjectSettings/Packages；确需管线设置调整交给根代理写 Claude 请求。','',
'## 验证界限','',
'此次为文件和元数据审计，没有 Blender 新渲染、Unity 运行或性能采样。源 GLB 面数来自 glTF accessor；尺寸沿用带来源的既有作者清单，不假称本轮重新测量。缺少新源不阻止程序化改善，也不证明全部质量目标完成。','']
(OUT/'ASSET-GAPS.zh-CN.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps({'v2_exists':report['v2_drop_directory_exists'],'new_candidates':len(v2_files),'old_glbs':len(source_records),'fbx':len(models),'textures':len(textures),'materials':len(materials),'no_texture_materials':sum(not m['has_any_texture_reference'] for m in materials),'requirements':len(requirements),'anchors':len(anchor_data)},ensure_ascii=False))
