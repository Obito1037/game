"""Read-only model comparison; writes audit JSON beside this script."""
import bpy,json,hashlib,struct,re
from pathlib import Path
p=Path(__file__).resolve().parent
out={};detail={};canonical={}
for label,f in [('before',p/'archive-before-lod1-export-fix/gold_lighttree_geometry_candidate.blend'),('after',p/'gold_lighttree_geometry_candidate.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(f))
    data=[];canonical[label]={}
    for o in sorted([o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.endswith('_LOD0')],key=lambda o:o.name):
        data.append([o.name,[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons],
            [f.material_index for f in o.data.polygons],[[list(x.uv) for x in u.data] for u in o.data.uv_layers],
            [[list(x.color) for x in a.data] for a in o.data.color_attributes]])
        keys=[]
        for face in o.data.polygons:
            corners=[]
            for li in face.loop_indices:
                vi=o.data.loops[li].vertex_index
                corners.append(tuple(o.data.vertices[vi].co)+tuple(x for u in o.data.uv_layers for x in u.data[li].uv))
            keys.append((min(tuple(corners[i:]+corners[:i]) for i in range(len(corners))),face.material_index,face.use_smooth))
        canonical[label][o.name]=hashlib.sha256(json.dumps(sorted(keys)).encode()).hexdigest()
    out[label]=hashlib.sha256(json.dumps(data).encode()).hexdigest()
    detail[label]={d[0]:{key:hashlib.sha256(json.dumps(value).encode()).hexdigest() for key,value in zip(['vertices','polygons','slots','uv','color'],d[1:])} for d in data}
out['lod0_geometry_uv_color_slots_identical']=out['before']==out['after']
out['lod0_changed_components']={name:[key for key in detail['before'][name] if detail['before'][name][key]!=detail['after'][name][key]] for name in detail['before']}
out['lod0_oriented_faces_uv_slots_smoothing_identical']=canonical['before']==canonical['after']
out['lod0_canonical_changed_objects']=[n for n in canonical['before'] if canonical['before'][n]!=canonical['after'][n]]
out['png_dimensions']={f.name:list(struct.unpack('>II',f.read_bytes()[16:24])) for f in p.glob('*.png')}
out['html_missing_local_links']=[url for url in re.findall(r'(?:src|href)="([^"]+)"',(p/'REVIEW.html').read_text(encoding='utf-8')) if not (p/url).exists()]
m=json.loads((p/'geometry-manifest.json').read_text(encoding='utf-8'))
repo=p.parents[3]
out['manifest_hash_matches']={f['path']:hashlib.sha256((repo/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in m['files']}
(p/'final-evidence-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
