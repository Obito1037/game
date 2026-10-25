"""Read-only geometry/FBX roundtrip QA; writes only props/verification.json."""
import bpy
import json
import math
import hashlib
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'generated'/'env-v1'/'props'
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
checks=[]

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

for asset in manifest['assets']:
    clear()
    path=ROOT.parent/asset['fbx']
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    bpy.context.view_layer.update()
    vertices=[]
    triangles=0
    names=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles()
        triangles+=len(o.data.loop_triangles)
        vertices.extend(o.matrix_world@v.co for v in o.data.vertices)
        names.append(o.name)
    bbmin=[min(v[i] for v in vertices) for i in range(3)]
    bbmax=[max(v[i] for v in vertices) for i in range(3)]
    delta=max([abs(bbmin[i]-asset['bounds_blender']['min'][i]) for i in range(3)]+[abs(bbmax[i]-asset['bounds_blender']['max'][i]) for i in range(3)])
    marks=[]
    for name,expected in asset['markers'].items():
        found=bpy.data.objects.get(name)
        # Blender keeps datablocks after deleting scene objects; object get exact should
        # be safe because all marker names except entry/seat vary by asset.
        exists=found is not None and found.name in bpy.context.scene.objects
        err=(found.matrix_world.translation-Vector(expected['blender_xyz'])).length if exists else None
        marks.append({'name':name,'exists':exists,'error_metres':err,'passed':exists and err<.001})
    preserved=all(m['passed'] for m in marks)
    special=True
    if asset['asset_id'].startswith('cottage_'):
        special=len([n for n in names if n.startswith('Window_')])==2
    if asset['asset_id']=='copper_roadlamp':
        o=bpy.data.objects.get('LampHead')
        special=o is not None and o.matrix_world.translation.length<.001
    checks.append({'asset_id':asset['asset_id'],'fbx_triangles':triangles,'expected_triangles':asset['triangles'],'max_bounds_error_metres':delta,'fbx_sha256_matches':hashlib.sha256(path.read_bytes()).hexdigest()==asset['fbx_sha256'],'markers':marks,'special_components_preserved':special,'passed':delta<.001 and triangles==asset['triangles'] and preserved and special})

# Test real openings and wall surface normals in saved authored geometry.
bpy.ops.wm.open_mainfile(filepath=str(OUT/'abode_grandma'/'abode_grandma.blend'))
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
rays=[]
for name,x,z,opening in [('window_center',.82,1.62,True),('entry_center',-1.13,1.20,True),('front_left_solid',-1.85,2.2,False),('front_pier_solid',-.53,2.2,False),('front_below_window',.82,.5,False)]:
    hit,pos,normal,index,obj,matrix=bpy.context.scene.ray_cast(dg,Vector((x,-3,z)),Vector((0,1,0)),distance=6)
    passed=hit and ((pos.y>-.7) if opening else (abs(pos.y+1.625)<.02 and normal.y<-.9))
    rays.append({'name':name,'hit':hit,'position':list(pos) if hit else None,'normal':list(normal) if hit else None,'expected_opening':opening,'passed':passed})
result={'status':'passed' if all(c['passed'] for c in checks) and all(r['passed'] for r in rays) else 'failed','scope':'Blender FBX reimport and authored round-window/door rays. Unity runtime import and gameplay not tested.','assets':checks,'abode_facade_rays':rays,'triangle_budget_passed':manifest['triangles_unique_assets']<=25000,'house_budget_passed':all(a['triangles']<=2500 for a in manifest['assets'] if a['asset_id'].startswith('cottage_') or a['asset_id']=='abode_grandma')}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENV_V1_PROPS_VERIFY',result['status'],flush=True)
if result['status']!='passed':
    raise RuntimeError('Prop verification failed: see props/verification.json')
