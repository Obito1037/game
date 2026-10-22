"""Reopen both serialized .blend files and independently compare fingerprints."""
import ast,bpy,json,hashlib
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
builder=ROOT/'art/blender/build_traveler_v7.py'
names={'digest','matrix','weight_values','material_state','mesh_state','object_contract'}
parsed=ast.parse(builder.read_text(encoding='utf-8'))
helpers=[n for n in parsed.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
exec(compile(ast.Module(body=helpers,type_ignores=[]),str(builder),'exec'))

def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path)); root=bpy.data.objects['TravelerRoot']
    meshes={o.name:mesh_state(o) for o in root.children_recursive if o.type=='MESH'}
    material_names=sorted({m.name for o in root.children_recursive if o.type=='MESH' for m in o.data.materials})
    return {'meshes':meshes,'objects':object_contract(root),
            'materials':{name:material_state(bpy.data.materials[name]) for name in material_names}}

source=ROOT/'art/generated/character-v6/traveler.blend'; candidate=OUT/'traveler.blend'
a=snapshot(source); b=snapshot(candidate); errors=[]; mesh_rows=[]
for name,state in a['meshes'].items():
    other=b['meshes'][name]
    if name in ['Sleeve_L','Sleeve_R']:
        state={k:v for k,v in state.items() if k not in ['coordinates','normals']}
        other={k:v for k,v in other.items() if k not in ['coordinates','normals']}
    same=state==other
    if not same: errors.append('changed protected mesh data: '+name)
    mesh_rows.append({'mesh':name,'protected_data_equal':same,'source_sha256':digest(state),'candidate_sha256':digest(other)})
for key in ['objects','materials']:
    if a[key]!=b[key]: errors.append('changed '+key)
result={'passed':not errors,'errors':errors,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'scope':'Independent reload of both serialized BLEND files. All channels of 60 non-target meshes; topology/UV/COLOR_0/weights/material assignment of 2 sleeves; all object/bone matrices and parents; all material graphs.',
        'meshes':mesh_rows,'object_contract_equal':a['objects']==b['objects'],'material_graphs_equal':a['materials']==b['materials']}
(OUT/'v6-preservation-file-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PRESERVED_RELOADED '+json.dumps({'passed':not errors,'errors':errors,'mesh_count':len(mesh_rows)}))
assert not errors
