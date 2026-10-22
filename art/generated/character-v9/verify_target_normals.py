"""Exported normals of the seven reshaped meshes; old face is protected separately."""
import bpy,json,math
from pathlib import Path
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent
targets=json.loads((OUT/'v8-preservation-verification.json').read_text())['targets']
def open_asset(suffix):
    if suffix=='blend': bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'),automatic_bone_orientation=False)
        else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    bpy.context.view_layer.update()
def values(obj):
    basis=obj.matrix_world.to_3x3().inverted().transposed()
    return [(obj.matrix_world@obj.data.vertices[l.vertex_index].co,(basis@obj.data.corner_normals[l.index].vector).normalized()) for l in obj.data.loops]
open_asset('blend'); source={}
for name in targets:
    data=values(bpy.data.objects[name]); tree=KDTree(len(data))
    for i,(p,n) in enumerate(data): tree.insert(p,i)
    tree.balance(); source[name]=(tree,data)
result={}
for suffix in ['fbx','glb']:
    open_asset(suffix); rows=[]; errors=[]
    for name in targets:
        tree,expected=source[name]; maximum=0.; unmatched=0
        for p,n in values(bpy.data.objects[name]):
            near=tree.find_range(p,.00001)
            if not near: unmatched+=1; continue
            angle=min(math.degrees(math.acos(max(-1,min(1,n.dot(expected[i][1]))))) for _,i,_ in near)
            maximum=max(maximum,angle)
        rows.append({'mesh':name,'maximum_angle_degrees':maximum,'unmatched':unmatched})
        if maximum>1 or unmatched: errors.append(name)
    result[suffix]={'passed':not errors,'errors':errors,'rows':rows,'max_angle_degrees':max(r['maximum_angle_degrees'] for r in rows)}
(OUT/'target-normal-interchange-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('TARGET_NORMALS '+json.dumps({k:{a:b for a,b in v.items() if a!='rows'} for k,v in result.items()}))
assert all(r['passed'] for r in result.values())
