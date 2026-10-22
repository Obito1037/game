"""Read-only BLEND/FBX/GLB verification; outputs JSON only, never rewrites assets."""
import bpy,json,math,hashlib,struct,runpy
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
import numpy as np

OUT=Path(__file__).resolve().parent;BASE=OUT.parent/'world-v7'
TARGETS={'Garden_LavenderAndSeedHeads','Garden_FeatherFerns'}
expected=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,kind):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if kind=='blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    elif kind=='fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True,colors_type='LINEAR')
    else:bpy.ops.import_scene.gltf(filepath=str(path))
def fingerprint(obj):
    m=obj.data
    payload={'matrix':[list(r) for r in obj.matrix_world],
      'vertices':[list(v.co) for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],
      'mi':[p.material_index for p in m.polygons],'smooth':[p.use_smooth for p in m.polygons],
      'mats':[x.name for x in m.materials],
      'uv':[[list(d.uv) for d in uv.data] for uv in m.uv_layers],
      'colours':[[a.name,a.domain,a.data_type,[list(c.color) for c in a.data]] for a in m.color_attributes],
      'normals':hashlib.sha256(np.asarray([tuple(n.vector) for n in m.corner_normals],dtype='<f4').tobytes()).hexdigest()}
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
def material_fingerprint(mat):
    # Image content compared separately. Paths intentionally point at the staged
    # texture copy; node types, links and all numeric/string socket values stay.
    nodes=[];links=[]
    if mat.node_tree:
        for n in mat.node_tree.nodes:
            values=[]
            for s in n.inputs:
                if not hasattr(s,'default_value'):continue
                v=s.default_value
                if isinstance(v,(int,float,str,bool)):value=v
                else:
                    try:value=list(v)
                    except TypeError:value=str(v)
                values.append([s.identifier,value])
            image_identity=None
            if n.type=='TEX_IMAGE' and n.image:
                image=n.image
                if image.packed_file:image_hash=hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
                elif image.filepath:image_hash=sha(Path(bpy.path.abspath(image.filepath)))
                else:raise RuntimeError('Image has neither packed data nor readable path: '+image.name)
                image_identity=[image.name,image_hash]
            nodes.append([n.name,n.bl_idname,values,image_identity])
        links=sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in mat.node_tree.links)
    payload=[mat.name,list(mat.diffuse_color),mat.use_nodes,mat.use_backface_culling,mat.surface_render_method,nodes,links]
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

source_hashes={name:sha(BASE/name)==baseline['sha256'][name] for name in ['island.blend','island.fbx','island.glb']}
candidate_hashes={name:sha(OUT/name)==expected['sha256'][name] for name in ['island.blend','island.fbx','island.glb']}
textures={name:sha(OUT/'textures'/name)==sha(BASE/'textures'/name) for name in ['meadow-watercolor.png','meadow-normal.png']}
assert all(source_hashes.values()) and all(candidate_hashes.values()) and all(textures.values())
load(OUT/'island.blend','blend')
source={};source_names={o.name for o in bpy.context.scene.objects if o.type=='MESH'}
for name in TARGETS:
    ob=bpy.data.objects[name];m=ob.data;tree=KDTree(len(m.vertices))
    positions=[ob.matrix_world@v.co for v in m.vertices]
    for i,p in enumerate(positions):tree.insert(p,i)
    tree.balance();normals=[[] for _ in m.vertices];colours=[None]*len(m.vertices)
    nm=ob.matrix_world.to_3x3().inverted().transposed()
    for l,n in zip(m.loops,m.corner_normals):
        normals[l.vertex_index].append((nm@n.vector).normalized())
        colours[l.vertex_index]=tuple(m.color_attributes.active_color.data[l.index].color)
    source[name]={'tree':tree,'normals':normals,'colours':colours,'triangles':len(m.loop_triangles)}

raw=(OUT/'island.glb').read_bytes();jl=struct.unpack_from('<I',raw,12)[0]
gltf=json.loads(raw[20:20+jl]);binary=20+jl+8;raw_colours=[]
for gm in gltf['meshes']:
    lo=1.;hi=0.;types=set()
    for prim in gm['primitives']:
        acc=gltf['accessors'][prim['attributes']['COLOR_0']];view=gltf['bufferViews'][acc['bufferView']]
        typ=acc['componentType'];types.add(typ);dtype=np.dtype({5123:'<u2',5126:'<f4',5121:'u1'}[typ])
        offset=binary+view.get('byteOffset',0)+acc.get('byteOffset',0)
        stride=view.get('byteStride',dtype.itemsize*4)
        a=np.ndarray((acc['count'],4),dtype=dtype,buffer=raw,offset=offset,strides=(stride,dtype.itemsize))[:,:3].astype(float)
        if acc.get('normalized'):a/=65535 if typ==5123 else 255
        lo=min(lo,float(a.min()));hi=max(hi,float(a.max()))
    want=next(c for c in expected['vertex_colors'] if c['mesh']==gm['name'])
    delta=max(abs(lo-want['min_rgb']),abs(hi-want['max_rgb']))
    raw_colours.append({'mesh':gm['name'],'component_types':sorted(types),'range_error':delta,'linear':delta<.00004})

checks=[]
for kind in ['blend','fbx','glb']:
    load(BASE/('island.'+kind),kind)
    frozen={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    old_anchors={o.name:[list(r) for r in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    old_materials={m.name:material_fingerprint(m) for m in bpy.data.materials if m.users}
    load(OUT/('island.'+kind),kind)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];errors=[]
    if {o.name for o in objects}!=source_names:errors.append('Mesh object names changed')
    unchanged=[]
    for name,value in frozen.items():
        actual=fingerprint(bpy.data.objects[name]);same=actual==value
        unchanged.append({'mesh':name,'same':same,'baseline_sha256':value,'candidate_sha256':actual})
        if not same:errors.append('Non-target mesh fingerprint mismatch: '+name)
    new_materials={m.name:material_fingerprint(m) for m in bpy.data.materials if m.users}
    materials_same=old_materials==new_materials
    if not materials_same:errors.append('Material values/nodes/content changed')
    new_anchors={o.name:[list(r) for r in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    anchors_same=old_anchors==new_anchors
    if not anchors_same:errors.append('Anchor matrices changed')
    triangles=0;zero=[];duplicates=[];normal_invalid=[]
    for ob in objects:
        me=ob.data;me.calc_loop_triangles();triangles+=len(me.loop_triangles)
        bad=sum(t.area<1e-12 for t in me.loop_triangles)
        dup=len(me.loop_triangles)-len({tuple(sorted(t.vertices)) for t in me.loop_triangles})
        if bad:zero.append([ob.name,bad])
        if dup:duplicates.append([ob.name,dup])
        if any(not math.isfinite(float(x)) for v in me.vertices for x in v.co):errors.append('Nonfinite positions '+ob.name)
        if any(not math.isfinite(float(x)) for n in me.corner_normals for x in n.vector):normal_invalid.append(ob.name)
    if triangles!=expected['triangles'] or triangles>550000:errors.append('Triangle count/budget mismatch')
    if zero or duplicates or normal_invalid:errors.append('Degenerate/duplicate/invalid normal')
    target_checks=[]
    obstacle_names=['Garden_HeroBoulders','Garden_Walkways','Observatory_StoneAndBrass','Cliff_Pier']
    obstacles={name:BVHTree.FromPolygons([bpy.data.objects[name].matrix_world@v.co for v in bpy.data.objects[name].data.vertices],
      [tuple(p.vertices) for p in bpy.data.objects[name].data.polygons],all_triangles=False) for name in obstacle_names}
    for name in sorted(TARGETS):
        ob=bpy.data.objects[name];m=ob.data;s=source[name];nm=ob.matrix_world.to_3x3().inverted().transposed()
        pos_error=0.;normal_error=0.;colour_error=0.;normal_bad=0;hits=Counter();up_min=1.
        for loop,n in zip(m.loops,m.corner_normals):
            p=ob.matrix_world@m.vertices[loop.vertex_index].co;nearest,vi,dist=s['tree'].find(p);pos_error=max(pos_error,dist)
            actual=(nm@n.vector).normalized();dot=max(float(actual.dot(v)) for v in s['normals'][vi])
            angle=math.degrees(math.acos(max(-1,min(1,dot))));normal_error=max(normal_error,angle)
            if angle>.2:normal_bad+=1
            attr=m.color_attributes.active_color;colour=attr.data[loop.index if attr.domain=='CORNER' else loop.vertex_index].color
            colour_error=max(colour_error,max(abs(float(a)-b) for a,b in zip(colour,s['colours'][vi])))
        for v in m.vertices:
            p=ob.matrix_world@v.co
            for obs,bvh in obstacles.items():
                if bvh.ray_cast(Vector((p.x,p.y,4)),Vector((0,0,-1)),6)[0] is not None:hits[obs]+=1
        # Fern leaf polygons must face up geometrically. Stem tubes excluded.
        if name=='Garden_FeatherFerns':
            up_min=min((nm@p.normal).normalized().z for p in m.polygons if m.materials[p.material_index].name!='BI_stem')
            if up_min<=0:errors.append('Fern leaf face winding reversed')
        if pos_error>1e-5:errors.append('Target positions failed '+name)
        if normal_bad:errors.append('Target corner normals failed '+name)
        if colour_error>(.0045 if kind=='glb' else .00001):errors.append('Target linear colours failed '+name)
        if hits:errors.append('New plant obstacle projection '+name)
        target_checks.append({'mesh':name,'triangles':len(m.loop_triangles),'max_position_error_metres':pos_error,
          'max_corner_normal_error_degrees':normal_error,'normal_corners_over_0_2_degrees':normal_bad,
          'max_linear_colour_error':colour_error,'fern_leaf_up_normal_min':up_min if name=='Garden_FeatherFerns' else None,
          'vertices_projecting_into_obstacles':dict(hits)})
    item={'format':kind,'mesh_count':len(objects),'anchor_count':len(new_anchors),'triangles':triangles,
      'unchanged_non_targets':unchanged,'materials_identical':materials_same,'anchors_identical':anchors_same,
      'zero_area_triangles':zero,'duplicate_triangles':duplicates,'invalid_normal_meshes':normal_invalid,
      'target_checks':target_checks,'sha256':sha(OUT/('island.'+kind)),'errors':errors,'passed':not errors}
    checks.append(item)
    (OUT/'interchange-verification.json').write_text(json.dumps({'passed':False,'in_progress':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    print('WORLD_V8_READBACK',kind,'PASS' if not errors else errors,flush=True)
report={'passed':all(c['passed'] for c in checks) and all(c['linear'] for c in raw_colours),
  'scope':'Clean-scene same-format comparison to world-v7: 27 non-target meshes including normals/UV/colour/material slots, all material numeric/node/content values, 14 anchor matrices. New geometry/normal/linear colour readback plus actual obstacle vertex projection. No runtime aesthetic, collision or performance acceptance.',
  'frozen_source_hashes_unchanged':source_hashes,'candidate_hashes_match':candidate_hashes,'textures_byte_identical':textures,
  'raw_glb_colours':raw_colours,'checks':checks}
(OUT/'interchange-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['passed'],[c['errors'] for c in checks]
expected['verification_pending']=False;expected['verification_file']='interchange-verification.json'
(OUT/'asset-manifest.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORLD_V8_ALL_VERIFIED',flush=True)
