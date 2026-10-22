"""Independent exported head normals, including fully closed lids; no renders."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent
targets=set(json.loads((OUT/'v7-preservation-verification.json').read_text())['targets'])

def open_asset(suffix):
    if suffix=='blend': bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'),automatic_bone_orientation=False)
        else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    for name in ['Blink_L','Blink_R']: bpy.data.objects[name].scale=(1,1,1)
    bpy.context.view_layer.update()

def normals(obj):
    normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
    return [(obj.matrix_world@obj.data.vertices[loop.vertex_index].co,
             (normal_matrix@obj.data.corner_normals[loop.index].vector).normalized()) for loop in obj.data.loops]

open_asset('blend'); source={}
for name in targets:
    values=normals(bpy.data.objects[name]); tree=KDTree(len(values))
    for i,(p,n) in enumerate(values): tree.insert(p,i)
    tree.balance(); source[name]=(tree,values)
results={}
for suffix in ['fbx','glb']:
    open_asset(suffix); rows=[]; errors=[]
    for name in sorted(targets):
        obj=bpy.data.objects[name]; tree,expected=source[name]
        maximum=0.; visible_maximum=0.; failed=0; mismatch=[]
        loop_poly={i:p for p in obj.data.polygons for i in p.loop_indices}
        for li,(p,n) in enumerate(normals(obj)):
            near=tree.find_range(p,.00001)
            if not near: failed+=1; continue
            difference=min(math.degrees(math.acos(max(-1,min(1,n.dot(expected[index][1]))))) for _,index,_ in near)
            maximum=max(maximum,difference)
            if loop_poly[li].area>1e-12: visible_maximum=max(visible_maximum,difference)
            if difference>1.:
                poly=loop_poly[li]
                mismatch.append({'loop':li,'position':list(p),'normal':list(n),'polygon_area_local':poly.area,
                                 'polygon':list(poly.vertices),'difference_degrees':difference})
        if failed or maximum>1.0: errors.append('export normal mismatch '+name)
        # These are open anterior caps. Their physical polygon winding must
        # agree with the outward (-Y) direction, independently of split normals.
        wrong_facing=0
        if name.startswith('Head_Eye_') or name.endswith('_LidCover'):
            basis=obj.matrix_world.to_3x3().inverted().transposed()
            for poly in obj.data.polygons:
                if poly.area>1e-12 and (basis@poly.normal).normalized().y>.001: wrong_facing+=1
            if wrong_facing: errors.append('inward ocular or closed lid cap '+name)
        rows.append({'mesh':name,'maximum_normal_angle_degrees':maximum,'drawable_maximum_normal_angle_degrees':visible_maximum,
                     'unmatched_loops':failed,'inward_cap_polygons':wrong_facing,'mismatches':mismatch})
    results[suffix]={'passed':not errors,'errors':errors,'rows':rows,
                     'max_normal_angle_degrees':max(row['maximum_normal_angle_degrees'] for row in rows),
                     'drawable_maximum_normal_angle_degrees':max(row['drawable_maximum_normal_angle_degrees'] for row in rows),
                     'limitation':'GLB has six zero-area taper-end triangles whose Blender-import corner normals fall back to +/-Z. Strict all-corner passed remains false; drawable normal error is recorded separately. FBX is the Unity source.'}
(OUT/'face-normal-interchange-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('FACE_NORMALS '+json.dumps({k:{a:b for a,b in v.items() if a!='rows'} for k,v in results.items()}))
assert all(r['passed'] for r in results.values())
