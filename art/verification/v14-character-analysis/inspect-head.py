"""Read-only CPU inspection. Opens frozen v9; never saves or exports the model."""
import bpy, ast, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'art/generated/character-v9/traveler.blend'
ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
tree=ast.parse((ROOT/'art/blender/build_traveler_v6.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'smooth','unproportion'}],type_ignores=[]),'v6-pure-functions','exec'))
before=(SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
def bounds(points):
    return {'min':[min(p[d] for p in points) for d in range(3)],'max':[max(p[d] for p in points) for d in range(3)],'dimensions':[max(p[d] for p in points)-min(p[d] for p in points) for d in range(3)]} if points else None
def components(obj):
    adj=[[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
    seen=set();out=[]
    for seed in range(len(adj)):
        if seed in seen:continue
        ids=[];pending=[seed];seen.add(seed)
        while pending:
            i=pending.pop();ids.append(i)
            for n in adj[i]:
                if n not in seen:seen.add(n);pending.append(n)
        points=[unproportion(obj.matrix_world@obj.data.vertices[i].co) for i in ids]
        out.append({'firstVertex':min(ids),'vertexCount':len(ids),'canonicalBounds':bounds(points)})
    return out
root=bpy.data.objects['TravelerRoot']
report={'source':str(SOURCE.relative_to(ROOT)),'readOnly':True,'sourceSizeAndMtimeUnchanged':None,'objects':{},'rigs':{}}
report['root']={'matrixWorld':[list(r) for r in root.matrix_world],'meshCount':sum(o.type=='MESH' for o in root.children_recursive)}
for obj in [root]+list(root.children_recursive):
    if obj.type=='ARMATURE':
        report['rigs'][obj.name]={b.name:{'parent':b.parent.name if b.parent else None,'matrixLocal':[list(r) for r in b.matrix_local]} for b in obj.data.bones}
    if not(obj.name.startswith(('Head','Blink')) or obj.name=='QuietSmile'):continue
    row={'type':obj.type,'parent':obj.parent.name if obj.parent else None,'parentType':obj.parent_type,'parentBone':obj.parent_bone,'matrixBasis':[list(r) for r in obj.matrix_basis],'matrixParentInverse':[list(r) for r in obj.matrix_parent_inverse],'matrixWorld':[list(r) for r in obj.matrix_world],'children':[c.name for c in obj.children]}
    if obj.type=='MESH':
        obj.data.calc_loop_triangles()
        row.update(vertices=len(obj.data.vertices),triangles=len(obj.data.loop_triangles),canonicalBounds=bounds([unproportion(obj.matrix_world@v.co) for v in obj.data.vertices]),localBounds=bounds([v.co for v in obj.data.vertices]),components=components(obj),vertexGroups=[g.name for g in obj.vertex_groups],modifiers=[{'name':m.name,'type':m.type,'object':getattr(getattr(m,'object',None),'name',None)} for m in obj.modifiers],materials=[])
        for m in obj.data.materials:
            bsdf=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.use_nodes else None
            row['materials'].append({'name':m.name,'diffuse':list(m.diffuse_color),'roughness':m.roughness,'principledRoughness':bsdf.inputs['Roughness'].default_value if bsdf else None,'metallic':m.metallic,'vertexColors':[{'name':a.name,'type':a.data_type,'domain':a.domain} for a in obj.data.color_attributes]})
    report['objects'][obj.name]=row
report['sourceSizeAndMtimeUnchanged']=before==(SOURCE.stat().st_size,SOURCE.stat().st_mtime_ns)
assert report['sourceSizeAndMtimeUnchanged']
(OUT/'head-structure.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_READ_ONLY_INSPECTION '+json.dumps({'headObjects':len(report['objects']),'armatures':len(report['rigs']),'sourceUnchanged':True}),flush=True)
