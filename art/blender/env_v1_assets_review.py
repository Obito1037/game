"""Record source-preview findings after manual inspection; no Unity side effects."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'art/generated/env-v1/inventory.json'
doc=json.loads(path.read_text(encoding='utf-8'))
for asset in doc['assets']:
    tree=asset['kind']=='tree'
    asset['visual_review']={
        'status':'source three-view inspection complete',
        'reviewed_views':['front','side','top'],
        'story_role': ('阿婆屋前坡上的金色光树候选；源树本身仍为银绿叶，金色叶缘需独立发光材质表达' if asset['id']=='tree_gold' else '村子下面缓坡的银绿色光树林' if tree else '采光船/码头小木艇' if asset['kind']=='boat' else '岛岸、山坡和远景礁石的可复用石块组合'),
        'source_orientation':'Broad presentation silhouette is visible from Blender +X (source-side.png); not a physical in-game orientation',
        'problems':[
            '一个 GLB 包含主对象、两个其他角度/尺寸的展示模型和独立局部放大图；不能整体作为单一游戏道具导入。',
            '包围盒被展示板的悬浮对象扩大，源尺度不是可信的米制实物尺寸。',
            '单张 4096x4096 BaseColor 烘焙了材质外观；没有独立发光/法线贴图。',
            '细节几何远高于整岛预算，必须减面并重新检查轮廓。',
        ]+(['部分树冠/果实是合法的独立连通域，不能把所有小连通域当碎片删除。','树根、地面石块及苔草粘连；底座需要独立对象；局部放大果实图应舍弃。'] if tree else ['主岩体内部多块石头相互粘连；拆出的三个展示形体可作为独立石群复用，尚不能声称逐块岩石已人工重拓扑。','局部放大示意图背面为不自然的大平面，应舍弃。'] if asset['kind']=='rock' else ['底部两个小模型与局部船帮剖面属于展示图；只保留主船。','船首/船尾有缆绳，细长边和木板局部可能在极限减面下失真。']),
        'repair_plan':'人工按三视图指定连通域组，删除展示性悬浮剖面，保留可用独立形体。调整轴心/物理尺寸；分级减面后再次检查。',
        'limits':'三张外观图不证明水密性、每个细节的正确性或 Unity 碰撞/运行效果。',
    }
doc['source_totals']={'files':len(doc['assets']),'triangles':sum(a['triangles'] for a in doc['assets']),'bytes':sum(a['source_bytes'] for a in doc['assets'])}
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(doc['source_totals']))
