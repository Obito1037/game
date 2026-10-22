import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[2]
out=root/'art'/'generated'
expected=json.loads((out/'asset-manifest.json').read_text(encoding='utf-8'))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(out/'island.fbx'),use_custom_normals=True)
objects=list(bpy.context.scene.objects)
meshes=[o for o in objects if o.type=='MESH']
tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
errors=[]; anchors=[]
for name,xyz in expected['anchors_unity'].items():
    obj=bpy.data.objects.get('Anchor_'+name)
    if obj is None: errors.append('missing anchor '+name); continue
    b=obj.matrix_world.translation
    actual=[b.x,b.z,-b.y]
    delta=(Vector(actual)-Vector(xyz)).length
    anchors.append({'name':name,'expected_unity':xyz,'actual_unity':actual,'error_metres':delta})
    if delta>.0001: errors.append('anchor transform '+name)
expected_names={o['name'] for o in expected['objects']}
actual_names={o.name for o in meshes}
if actual_names!=expected_names: errors.append('named mesh set mismatch')
if tri!=expected['triangles']: errors.append('triangle mismatch')
if tri>220000: errors.append('triangle budget')
uvcount=sum(bool(o.data.uv_layers) for o in meshes)
if uvcount!=len(meshes): errors.append('UV missing')
report={'verified':'FBX exported and reimported into clean Blender scene','passed':not errors,'triangles':tri,'mesh_count':len(meshes),'material_count':len(bpy.data.materials),'uv_mesh_count':uvcount,'anchors':anchors,'errors':errors}
(out/'fbx-roundtrip-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':not errors,'triangles':tri,'mesh_count':len(meshes),'uv_mesh_count':uvcount,'errors':errors}))
assert not errors, str(errors)
