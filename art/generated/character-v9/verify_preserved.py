"""Independent reload: exact frozen face/body channels and changed target scope."""
import ast,bpy,json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
builder=ROOT/'art/blender/build_traveler_v7.py'
names={'digest','matrix','weight_values','material_state','mesh_state','object_contract'}
parsed=ast.parse(builder.read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(builder),'exec'))
scope=json.loads((OUT/'v8-preservation-verification.json').read_text()); targets=set(scope['targets'])

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path)); root=bpy.data.objects['TravelerRoot']
    meshes={o.name:mesh_state(o) for o in root.children_recursive if o.type=='MESH'}
    names=sorted({m.name for o in root.children_recursive if o.type=='MESH' for m in o.data.materials})
    hair=bpy.data.objects['Head_Hair_Indigo']; protected=set(scope['protected_hair_vertices'])
    return {'meshes':meshes,'objects':object_contract(root),
            'protected_hair_normals':{loop.index:list(hair.data.corner_normals[loop.index].vector) for loop in hair.data.loops if loop.vertex_index in protected},
            'materials':{name:material_state(bpy.data.materials[name]) for name in names}}

source=ROOT/'art/generated/character-v8/traveler.blend'; candidate=OUT/'traveler.blend'
a=snapshot(source); b=snapshot(candidate); errors=[]; rows=[]
if set(a['meshes'])!=set(b['meshes']): errors.append('mesh names changed')
for name,state in a['meshes'].items():
    other=b['meshes'][name]
    if name in targets:
        state={k:v for k,v in state.items() if k not in ['coordinates','normals']}
        other={k:v for k,v in other.items() if k not in ['coordinates','normals']}
    same=state==other
    if not same: errors.append('changed protected mesh data: '+name)
    rows.append({'mesh':name,'is_target':name in targets,'protected_data_equal':same,
                 'source_sha256':digest(state),'candidate_sha256':digest(other)})
for i in scope['protected_hair_vertices']:
    if a['meshes']['Head_Hair_Indigo']['coordinates'][i]!=b['meshes']['Head_Hair_Indigo']['coordinates'][i]:
        errors.append('protected hair/scalp/brow/lash vertex changed '+str(i))
for key in ['objects','materials','protected_hair_normals']:
    if a[key]!=b[key]: errors.append('changed '+key)
result={'passed':not errors,'errors':errors,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'scope':'All channels of 55 non-target meshes; topology/UV/COLOR_0/weights/material assignment of 7 targets; scalp/brow/lash coordinates and corner normals; all object/bone matrices/parents; all 29 material graphs.',
        'meshes':rows,'object_contract_equal':a['objects']==b['objects'],
        'protected_hair_vertices':len(scope['protected_hair_vertices']),
        'protected_hair_normals_equal':a['protected_hair_normals']==b['protected_hair_normals'],
        'material_graphs_equal':a['materials']==b['materials']}
(OUT/'v8-preservation-file-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PRESERVED_RELOADED '+json.dumps({k:v for k,v in result.items() if k!='meshes'}))
assert not errors
