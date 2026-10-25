"""Fresh-process Blender verification; read-only source and candidate files."""
import bpy,json,hashlib,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'art/blender'))
import env_v2_pier_bench as work
OUT=Path(__file__).parent
def uv_corners():
    result={}
    for obj in work.meshes():
        layer=obj.data.uv_layers.active
        for face in obj.data.polygons:
            for li in face.loop_indices:
                p=obj.matrix_world@obj.data.vertices[obj.data.loops[li].vertex_index].co
                key=tuple(round(x,4) for x in p)+(face.material_index,)
                result.setdefault(key,[]).append(tuple(layer.data[li].uv))
    return result
def diff(a,b):
    if set(a)!=set(b):return None
    return max(math.dist(uv,min(b[k],key=lambda q:math.dist(uv,q))) for k,values in a.items() for uv in values)
reports=[]
for asset in work.IDS:
    dest=OUT/asset;record=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
    source=work.SOURCE/asset/(asset+'.blend');blend=dest/(asset+'_v2_candidate.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source));original=work.geometry();marker=work.markers();bounds=work.bounds(work.meshes())
    bpy.ops.wm.open_mainfile(filepath=str(blend));candidate=work.geometry();candidate_markers=work.markers();uv=uv_corners()
    textures=[n.image for m in bpy.data.materials if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    checks={'original_source_hash_unchanged':work.sha(source)==record['source_sha256'],
            'all_geometry_matrices_indices_slots_smoothing_exact':original==candidate,
            'all_markers_parents_matrices_exact':marker==candidate_markers,
            'bounds_exact':bounds==work.bounds(work.meshes()),
            'single_original_1254_texture_packed':len({i.name for i in textures})==1 and all(i.packed_file and list(i.size)==[1254,1254] for i in textures)}
    candidate['Structure']['triangles']=record['after_triangles'];rt=work.check_fbx(asset,dest,candidate,bounds,marker)
    uv_back=uv_corners();a=diff(uv,uv_back);b=diff(uv_back,uv)
    checks.update(rt['checks']);checks['uv_corner_sets_both_directions_within_1micrometre']=a is not None and b is not None and max(a,b)<1e-6
    reports.append({'asset_id':asset,'checks':checks,'all_pass':all(checks.values()),'uv_maximum_error':max(a,b) if a is not None and b is not None else None,
                    'vertex_maximum_error_m':rt['maximum_vertex_errors_m'],'triangles':rt['triangles'],'fbx_sha256':work.sha(dest/(asset+'_v2_candidate.fbx'))})
report={'all_pass':all(r['all_pass'] for r in reports),'assets':reports}
work.dump(OUT/'fresh-process-verification.json',report)
print('FRESH_PROCESS_VERIFY',report['all_pass'],flush=True)
if not report['all_pass']:raise RuntimeError(json.dumps(report))
