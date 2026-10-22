"""Independently reopen frozen v7 and candidate v8; no mutation of either asset."""
import ast,bpy,json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
builder=ROOT/'art/blender/build_traveler_v7.py'
names={'digest','matrix','weight_values','material_state','mesh_state','object_contract'}
parsed=ast.parse(builder.read_text(encoding='utf-8'))
helpers=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
exec(compile(ast.Module(body=helpers,type_ignores=[]),str(builder),'exec'))
allowed=set(json.loads((OUT/'v7-preservation-verification.json').read_text())['targets'])
material_allowed={'Traveler_Eye_Ivory','Traveler_Eye_AmberRim','Traveler_Eye_Chestnut'}

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path)); root=bpy.data.objects['TravelerRoot']
    meshes={o.name:mesh_state(o) for o in root.children_recursive if o.type=='MESH'}
    materials=sorted({m.name for o in root.children_recursive if o.type=='MESH' for m in o.data.materials})
    return {'meshes':meshes,'objects':object_contract(root),
            'materials':{name:material_state(bpy.data.materials[name]) for name in materials}}

source=ROOT/'art/generated/character-v7/traveler.blend'; candidate=OUT/'traveler.blend'
a=snapshot(source); b=snapshot(candidate); errors=[]; rows=[]
if set(a['meshes'])!=set(b['meshes']): errors.append('mesh names changed')
for name,state in a['meshes'].items():
    other=b['meshes'][name]
    if name in allowed: continue
    same=state==other
    if not same: errors.append('changed protected mesh data: '+name)
    rows.append({'mesh':name,'protected_data_equal':same,'source_sha256':digest(state),'candidate_sha256':digest(other)})
object_equal=a['objects']==b['objects']
if not object_equal: errors.append('changed object/rig/attachment contract')
materials=[]
for name,state in a['materials'].items():
    if name in material_allowed: continue
    same=state==b['materials'][name]
    if not same: errors.append('changed material: '+name)
    materials.append({'material':name,'exact_match':same,'sha256':digest(state)})
result={'passed':not errors,'errors':errors,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'scope':'Independent reload. All channels of 48 non-target meshes; all object/bone/pivot matrices and parent relations; 26 non-target material graphs. Head/eye/blink topology and three eye base colors allowed to change. No body/rig/sole/attachment change.',
        'meshes':rows,'protected_mesh_count':len(rows),'object_contract_equal':object_equal,
        'protected_material_count':len(materials),'materials':materials}
(OUT/'v7-preservation-file-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PRESERVED_RELOADED '+json.dumps({'passed':not errors,'errors':errors,'mesh_count':len(rows),'material_count':len(materials)}))
assert not errors
