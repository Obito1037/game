"""Read back the frozen v3 FBX / GLB independently of preview rendering."""
import bpy, hashlib, json
from pathlib import Path
from mathutils import Vector, Matrix, Euler

OUT=Path(__file__).resolve().parent
manifest=json.loads((OUT/'traveler-manifest.json').read_text(encoding='utf-8'))
rows={o['name']:o for o in manifest['hierarchy'] if o['type']=='EMPTY'}
expected={}
def world(name):
    if name in expected: return expected[name]
    row=rows[name]
    local=Matrix.LocRotScale(Vector(row['blender_local_position']),Euler(row['blender_local_rotation_euler']).to_quaternion(),Vector(row['blender_local_scale']))
    expected[name]=world(row['parent'])@local if row['parent'] else local
    return expected[name]
for name in rows: world(name)

results={}
for suffix in ['fbx','glb']:
    path=OUT/('traveler.'+suffix)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(path))
    else: bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update(); errors=[]
    for name,source_matrix in expected.items():
        obj=bpy.data.objects.get(name)
        if not obj: errors.append('missing '+name); continue
        if (obj.matrix_world.translation-source_matrix.translation).length>.00015: errors.append('wrong pivot '+name)
        if (obj.parent.name if obj.parent else None)!=rows[name]['parent']: errors.append('wrong parent '+name)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    bounds={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
    tris=0
    for mesh in meshes: mesh.data.calc_loop_triangles(); tris+=len(mesh.data.loop_triangles)
    if tris>32000: errors.append('triangle budget')
    if not .001<bounds['min'][2]<.009: errors.append('foot contact')
    if not 1.245<bounds['max'][2]<1.275: errors.append('height')
    blink_results={}
    for name in ['Blink_L','Blink_R']:
        pivot=bpy.data.objects.get(name)
        if not pivot: continue
        children=[o for o in pivot.children_recursive if o.type=='MESH']
        points=[o.matrix_world@Vector(c) for o in children for c in o.bound_box]
        open_width=max(p.x for p in points)-min(p.x for p in points)
        open_height=max(p.z for p in points)-min(p.z for p in points)
        pivot.scale=(1,1,1); bpy.context.view_layer.update()
        points=[o.matrix_world@Vector(c) for o in children for c in o.bound_box]
        closed_height=max(p.z for p in points)-min(p.z for p in points)
        if max(open_width,open_height)>.0002 or not .046<closed_height<.054: errors.append('blink extent '+name)
        blink_results[name]={'open_width_m':open_width,'open_height_m':open_height,'closed_height_m':closed_height}
        pivot.scale=(.001,.001,1); bpy.context.view_layer.update()
    results[suffix]={'passed':not errors,'errors':errors,'sha256':digest,'triangles':tris,'mesh_renderers':len(meshes),'bounds_blender':bounds,'verified_pivots':list(expected),'blink_validation':blink_results}
(OUT/'frozen-export-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('FROZEN_TRAVELER_VERIFIED '+json.dumps(results),flush=True)
assert all(row['passed'] for row in results.values()),'Frozen export verification failed'
