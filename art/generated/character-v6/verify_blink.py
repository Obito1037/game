"""Check that closed animated lid geometry covers the actual eye surfaces."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
results={}
for suffix in ['blend','fbx','glb']:
    if suffix=='blend': bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'),automatic_bone_orientation=False)
        else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    for side in ['L','R']: bpy.data.objects['Blink_'+side].scale=(1,1,1)
    bpy.context.view_layer.update(); trees={}
    for side in ['L','R']:
        obj=bpy.data.objects['Blink_'+side+'_LidCover']
        vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
        trees[side]=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in obj.data.polygons])
    misses=[]; clearances=[]; samples=0
    for obj in bpy.data.objects['TravelerRoot'].children_recursive:
        if obj.type!='MESH' or not obj.name.startswith('Head_Eye_'): continue
        for vertex in obj.data.vertices:
            p=obj.matrix_world@vertex.co; tree=trees['L' if p.x<0 else 'R']
            hit=tree.ray_cast(Vector((p.x,-2,p.z)),Vector((0,1,0)),4)
            samples+=1
            if hit[0] is None: misses.append({'mesh':obj.name,'vertex':vertex.index,'reason':'outside lid projection'})
            else:
                clearance=p.y-hit[0].y; clearances.append(clearance)
                if clearance<-.00001: misses.append({'mesh':obj.name,'vertex':vertex.index,'reason':'eye in front of closed lid','clearance_m':clearance})
    results[suffix]={'passed':not misses,'eye_vertex_samples':samples,'minimum_eye_recess_behind_closed_lid_m':min(clearances),'failures':misses}
(OUT/'blink-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('BLINK_VERIFICATION '+json.dumps({k:{x:y for x,y in v.items() if x!='failures'} for k,v in results.items()}))
assert all(r['passed'] for r in results.values())
