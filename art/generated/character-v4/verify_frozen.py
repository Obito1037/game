"""Independent FBX / GLB validation, run after the authoring process exits."""
import bpy, hashlib, json, math
from pathlib import Path
from mathutils import Vector, Matrix, Euler

OUT=Path(__file__).resolve().parent
manifest=json.loads((OUT/'traveler-manifest.json').read_text(encoding='utf-8'))
rows={o['name']:o for o in manifest['hierarchy'] if o['type']=='EMPTY'}
required={'TravelerRoot','Body','Head','Arm_L','Arm_R','Leg_L','Leg_R','ScarfTail','Lantern','Blink_L','Blink_R'}
assert set(rows)==required, 'Exactly the 11 documented animation pivots are required'
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
    bpy.context.view_layer.update(); errors=[]; pivot_error=0
    for name,source_matrix in expected.items():
        obj=bpy.data.objects.get(name)
        if not obj: errors.append('missing '+name); continue
        deviation=(obj.matrix_world.translation-source_matrix.translation).length
        pivot_error=max(pivot_error,deviation)
        if deviation>.00015: errors.append('wrong pivot '+name)
        if (obj.parent.name if obj.parent else None)!=rows[name]['parent']: errors.append('wrong parent '+name)
    lantern=bpy.data.objects.get('Lantern')
    if not lantern or not lantern.parent or lantern.parent.name!='Arm_R': errors.append('right hand Lantern hierarchy')
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
    bounds={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
    tris=0; nonfinite=0; invalid_normals=0; degenerates=0
    for obj in meshes:
        obj.data.calc_loop_triangles(); tris+=len(obj.data.loop_triangles)
        for vertex in obj.data.vertices:
            if not all(math.isfinite(c) for c in obj.matrix_world@vertex.co): nonfinite+=1
            if not all(math.isfinite(c) for c in vertex.normal) or vertex.normal.length<.99: invalid_normals+=1
        for triangle in obj.data.loop_triangles:
            if triangle.area<1e-16: degenerates+=1
    if tris>55000: errors.append('triangle budget')
    if nonfinite: errors.append('nonfinite vertices')
    if invalid_normals: errors.append('invalid vertex normals')
    if degenerates: errors.append('degenerate triangles')
    if not .001<bounds['min'][2]<.009: errors.append('foot contact')
    if not 1.25<bounds['max'][2]<1.35: errors.append('height')
    # Face outward-facing front normals; authored front is -Y. This also
    # catches flipped contour winding after coordinate conversion.
    head_front=[]
    for obj in meshes:
        if not obj.parent or obj.parent.name!='Head': continue
        if not any(mat and mat.name.startswith('Traveler_Face_PorcelainCream') for mat in obj.data.materials): continue
        normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
        for vertex in obj.data.vertices:
            p=obj.matrix_world@vertex.co
            if abs(p.x)<.06 and 1.08<p.z<1.2 and p.y<-.08:
                head_front.append((normal_matrix@vertex.normal).normalized().y)
    if not head_front or sum(head_front)/len(head_front)>-.3: errors.append('outward face normal / authored forward axis')
    blink_results={}
    for name in ['Blink_L','Blink_R']:
        pivot=bpy.data.objects.get(name)
        if not pivot: continue
        if any(abs(pivot.scale[i]-.001)>.00002 for i in [0,1]) or abs(pivot.scale[2]-1)>.00002: errors.append('open blink scale '+name)
        children=[o for o in pivot.children_recursive if o.type=='MESH']
        points=[o.matrix_world@v.co for o in children for v in o.data.vertices]
        open_width=max(p.x for p in points)-min(p.x for p in points)
        open_height=max(p.z for p in points)-min(p.z for p in points)
        pivot.scale=(1,1,1); bpy.context.view_layer.update()
        points=[o.matrix_world@v.co for o in children for v in o.data.vertices]
        closed_height=max(p.z for p in points)-min(p.z for p in points)
        if max(open_width,open_height)>.0002 or not .040<closed_height<.043: errors.append('blink extent '+name)
        blink_results[name]={'open_width_m':open_width,'open_height_m':open_height,'closed_height_m':closed_height}
        pivot.scale=(.001,.001,1); bpy.context.view_layer.update()
    results[suffix]={'passed':not errors,'errors':errors,'sha256':digest,'triangles':tris,'mesh_renderers':len(meshes),'bounds_blender':bounds,'verified_pivots':sorted(required),'maximum_pivot_error_m':pivot_error,'nonfinite_vertices':nonfinite,'invalid_vertex_normals':invalid_normals,'degenerate_triangles':degenerates,'authored_front_mean_normal_y':sum(head_front)/len(head_front) if head_front else None,'blink_validation':blink_results}
(OUT/'frozen-export-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('FROZEN_TRAVELER_VERIFIED '+json.dumps(results),flush=True)
assert all(row['passed'] for row in results.values()),'Frozen export verification failed'
