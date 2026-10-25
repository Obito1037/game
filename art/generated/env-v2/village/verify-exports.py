"""Fresh-process FBX round-trip checks, no Unity or source mutation."""
import bpy,json,hashlib,struct,re
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
IDS=['cottage_teal','cottage_ochre','cottage_slate']
def tris(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def coords(o):return [o.matrix_world@v.co for v in o.data.vertices]
def bounds(objects):
    pts=[v for o in objects for v in coords(o)]
    return {key:[fn(p[i] for p in pts) for i in range(3)] for key,fn in [('min',min),('max',max)]}
def nearest_error(a,b):
    tree=KDTree(len(b))
    for i,p in enumerate(b):tree.insert(Vector(p),i)
    tree.balance();return max(tree.find(Vector(p))[2] for p in a)
rows=[]
for asset in IDS:
    folder=OUT/asset;m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(folder/(asset+'_v2_candidate.blend')))
    authored={o.name:{'vertices':coords(o),'matrix':[list(r) for r in o.matrix_world],'tris':tris(o),'uv_layers':[u.name for u in o.data.uv_layers]} for o in bpy.context.scene.objects if o.type=='MESH'}
    marker_before=[list(r) for r in bpy.data.objects['Marker_Door'].matrix_world]
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(folder/(asset+'_v2_candidate.fbx')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];actual={o.name:o for o in meshes}
    b=bounds(meshes);marker_after=[list(r) for r in bpy.data.objects['Marker_Door'].matrix_world]
    errors={name:{'forward_max_m':nearest_error(authored[name]['vertices'],coords(actual[name])),
                  'reverse_max_m':nearest_error(coords(actual[name]),authored[name]['vertices'])} for name in authored}
    checks={'mesh_names_exact':set(actual)=={'Structure','Window_00','Window_01'},'total_triangles_exact':sum(tris(o) for o in meshes)==m['after_triangles'],
            'per_mesh_triangles_exact':all(tris(actual[n])==authored[n]['tris'] for n in authored),
            'structure_9_material_slots_exact':[x.name for x in actual['Structure'].data.materials]==m['materials'],
            'bounds_within_1micrometre':all(abs(b[k][i]-m['after_bounds'][k][i])<1e-6 for k in ['min','max'] for i in range(3)),
            'marker_matrix_within_1micrometre':all(abs(marker_before[r][c]-marker_after[r][c])<1e-6 for r in range(4) for c in range(4)),
            'bidirectional_vertices_within_1micrometre':all(max(e.values())<1e-6 for e in errors.values()),
            'wood_uv0_exists':'UVMap' in [u.name for u in actual['Structure'].data.uv_layers],
            'root_exists':bpy.data.objects.get(asset) is not None}
    row={'asset_id':asset,'triangles':sum(tris(o) for o in meshes),'checks':checks,'geometry_errors':errors,'bounds':b,
         'window_matrices':{n:[list(r) for r in actual[n].matrix_world] for n in ['Window_00','Window_01']}}
    (folder/'fbx-roundtrip.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');rows.append(row)
out={'assets':rows,'all_pass':all(all(r['checks'].values()) for r in rows),
     'png_dimensions':{str(p.relative_to(OUT)):list(struct.unpack('>II',p.read_bytes()[16:24])) for asset in IDS for p in (OUT/asset).glob('*.png')}}
(OUT/'fbx-roundtrip.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('VILLAGE_FBX_ROUNDTRIP',out['all_pass'],[(r['asset_id'],r['triangles'],r['checks']) for r in rows])
