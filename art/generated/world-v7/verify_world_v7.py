"""Read-only interchange and frozen-world checks; writes only verification JSON."""
import bpy, json, math, hashlib, struct
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
import numpy as np

OUT=Path(__file__).resolve().parent;BASE=OUT.parent/'world-v6'
expected=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
HERO='Garden_HeroBoulders'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,kind):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if kind=='blend':bpy.ops.wm.open_mainfile(filepath=str(path))
    elif kind=='fbx':bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True,colors_type='LINEAR')
    else:bpy.ops.import_scene.gltf(filepath=str(path))
def fingerprint(obj):
    m=obj.data
    payload={'matrix':[list(r) for r in obj.matrix_world],
        'vertices':[list(v.co) for v in m.vertices],
        'faces':[list(p.vertices) for p in m.polygons],
        'mi':[p.material_index for p in m.polygons],
        'smooth':[p.use_smooth for p in m.polygons],
        'mats':[x.name for x in m.materials],
        'uv':[[list(d.uv) for d in uv.data] for uv in m.uv_layers],
        'colours':[[a.name,a.domain,a.data_type,[list(c.color) for c in a.data]] for a in m.color_attributes],
        'normals':hashlib.sha256(np.asarray([tuple(n.vector) for n in m.corner_normals],dtype='<f4').tobytes()).hexdigest()}
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

assert all(sha(BASE/name)==baseline['sha256'][name] for name in ['island.blend','island.fbx','island.glb'])
textures={name:sha(OUT/'textures'/name)==sha(BASE/'textures'/name) for name in ['meadow-watercolor.png','meadow-normal.png']}
assert all(textures.values())

load(OUT/'island.blend','blend')
source=bpy.data.objects[HERO];m=source.data
source_positions=[source.matrix_world@v.co for v in m.vertices]
tree=KDTree(len(source_positions))
for i,p in enumerate(source_positions):tree.insert(p,i)
tree.balance()
normal_matrix=source.matrix_world.to_3x3().inverted().transposed()
source_normals=[[] for _ in m.vertices];source_colours=[None]*len(m.vertices)
for loop,n in zip(m.loops,m.corner_normals):
    source_normals[loop.vertex_index].append((normal_matrix@n.vector).normalized())
    source_colours[loop.vertex_index]=tuple(m.color_attributes.active_color.data[loop.index].color)
source_names={o.name for o in bpy.context.scene.objects if o.type=='MESH'}

raw=(OUT/'island.glb').read_bytes();jl=struct.unpack_from('<I',raw,12)[0]
gltf=json.loads(raw[20:20+jl]);binary=20+jl+8
raw_colours=[]
for gm in gltf['meshes']:
    lo=1.;hi=0.;types=set()
    for prim in gm['primitives']:
        acc=gltf['accessors'][prim['attributes']['COLOR_0']];view=gltf['bufferViews'][acc['bufferView']]
        typ=acc['componentType'];types.add(typ)
        offset=binary+view.get('byteOffset',0)+acc.get('byteOffset',0)
        a=np.frombuffer(raw,dtype={5123:'<u2',5126:'<f4',5121:'u1'}[typ],count=acc['count']*4,offset=offset).reshape(-1,4)[:,:3].astype(float)
        if acc.get('normalized'):a/=65535 if typ==5123 else 255
        lo=min(lo,float(a.min()));hi=max(hi,float(a.max()))
    want=next(c for c in expected['vertex_colors'] if c['mesh']==gm['name'])
    delta=max(abs(lo-want['min_rgb']),abs(hi-want['max_rgb']))
    assert delta<.00004,'Raw linear COLOR_0 range changed '+gm['name']
    raw_colours.append({'mesh':gm['name'],'component_types':sorted(types),'range_error':delta,'linear':True})

checks=[]
for kind in ['blend','fbx','glb']:
    load(BASE/('island.'+kind),kind)
    frozen={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name!=HERO}
    frozen_hero=bpy.data.objects[HERO]
    old_coords=[v.co.copy() for v in frozen_hero.data.vertices]
    old_faces=[tuple(p.vertices) for p in frozen_hero.data.polygons]
    old_matrix=frozen_hero.matrix_world.copy()
    old_bvh=BVHTree.FromPolygons([old_matrix@p for p in old_coords],old_faces,all_triangles=False)
    load(OUT/('island.'+kind),kind)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];errors=[]
    if {o.name for o in objects}!=source_names:errors.append('Mesh names changed')
    unchanged=[]
    for name,value in frozen.items():
        same=fingerprint(bpy.data.objects[name])==value
        unchanged.append({'mesh':name,'geometry_topology_uv_colour_material_fingerprint_equal':same})
        if not same:errors.append('Frozen mesh mismatch '+name)
    triangles=0;zero=[];duplicates=[]
    for ob in objects:
        ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
        bad=sum(t.area<1e-12 for t in ob.data.loop_triangles)
        dup=len(ob.data.loop_triangles)-len({tuple(sorted(t.vertices)) for t in ob.data.loop_triangles})
        if bad:zero.append([ob.name,bad])
        if dup:duplicates.append([ob.name,dup])
        if any(not math.isfinite(float(x)) for v in ob.data.vertices for x in v.co):errors.append('Nonfinite geometry '+ob.name)
    if triangles!=412815:errors.append('Island budget/count changed '+str(triangles))
    if zero or duplicates:errors.append('Degenerate or duplicate triangles')
    anchors=[]
    for name,xyz in expected['anchors_unity'].items():
        p=bpy.data.objects['Anchor_'+name].matrix_world.translation
        delta=(Vector((p.x,p.z,-p.y))-Vector(xyz)).length
        anchors.append({'name':name,'error_metres':delta})
        if delta>.0001:errors.append('Anchor moved '+name)
    hero=bpy.data.objects[HERO];hm=hero.data
    if len(hm.loop_triangles)!=20480:errors.append('Hero triangle count changed')
    if [m.name for m in hm.materials]!=['BI_rock_hero_warm','BI_rock_hero_slate']:errors.append('Hero material names changed')
    nm=hero.matrix_world.to_3x3().inverted().transposed();positions=[];positions_error=0;normal_error=0;colour_error=0;normal_bad=0
    attr=hm.color_attributes.active_color
    for loop,n in zip(hm.loops,hm.corner_normals):
        p=hero.matrix_world@hm.vertices[loop.vertex_index].co;nearest,vi,dist=tree.find(p)
        positions_error=max(positions_error,dist)
        actual=(nm@n.vector).normalized()
        dot=max(float(actual.dot(v)) for v in source_normals[vi]);angle=math.degrees(math.acos(max(-1,min(1,dot))))
        normal_error=max(normal_error,angle)
        if angle>.2:normal_bad+=1
        colour=attr.data[loop.index if attr.domain=='CORNER' else loop.vertex_index].color
        colour_error=max(colour_error,max(abs(float(a)-b) for a,b in zip(colour,source_colours[vi])))
    if positions_error>.00001:errors.append('Hero positions failed readback')
    if normal_bad:errors.append('Hero corner normals failed readback: '+str(normal_bad))
    if colour_error>(.0045 if kind=='glb' else .00001):errors.append('Hero linear colour failed readback')
    same_lower=None
    if kind=='blend':
        same_lower=True
        for vi,old in enumerate(old_coords):
            rock=min(baseline['hero_boulders'],key=lambda r:(old.x-r['center_unity'][0])**2+(-old.y-r['center_unity'][2])**2)
            if old.z<=rock['center_unity'][1]+.08 and hm.vertices[vi].co!=old:same_lower=False
        if not same_lower:errors.append('Frozen lower rim changed')
        if [tuple(p.vertices) for p in hm.polygons]!=old_faces:errors.append('Hero topology changed')
    bvh=BVHTree.FromPolygons([hero.matrix_world@v.co for v in hm.vertices],[tuple(p.vertices) for p in hm.polygons],all_triangles=False)
    plant_checks=[]
    for ent in baseline['plant_cleanup']:
        plant=bpy.data.objects[ent['mesh']];hits=0
        for vertex in plant.data.vertices:
            co=plant.matrix_world@vertex.co
            if not any(r['bounds_min_unity'][0]-.001<=co.x<=r['bounds_max_unity'][0]+.001 and r['bounds_min_unity'][2]-.001<=-co.y<=r['bounds_max_unity'][2]+.001 for r in baseline['hero_boulders']):continue
            if bvh.ray_cast(Vector((co.x,co.y,1.5)),Vector((0,0,-1)),2)[0] is not None:hits+=1
        plant_checks.append({'mesh':plant.name,'vertices_projecting_into_hero':hits})
        if hits:errors.append('Plant footprint intersection '+plant.name)
    item={'format':kind,'mesh_count':len(objects),'triangles':triangles,'hero_triangles':len(hm.loop_triangles),'hero_vertices':len(hm.vertices),'unchanged_meshes':unchanged,'anchors':anchors,'same_lower_rim':same_lower,'zero_area_triangles':zero,'duplicate_triangles':duplicates,'hero_max_position_error_metres':positions_error,'hero_max_normal_error_degrees':normal_error,'hero_normal_corners_outside_0_2_degrees':normal_bad,'hero_max_linear_colour_error':colour_error,'plant_checks':plant_checks,'sha256':sha(OUT/('island.'+kind)),'errors':errors,'passed':not errors}
    checks.append(item);print('WORLD_V7_READBACK',kind,'PASS' if not errors else errors,flush=True)
report={'passed':all(c['passed'] for c in checks),'scope':'Clean-scene BLEND/FBX/GLB readback, each compared to frozen v6 in the same format. 28 non-Hero meshes unchanged. No runtime collision or performance claim.','budget':412815,'ground_textures_byte_identical':textures,'raw_glb_colours':raw_colours,'form_checks':expected['hero_form_checks'],'checks':checks}
(OUT/'interchange-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['passed'],[c['errors'] for c in checks]
print('WORLD_V7_ALL_VERIFIED',flush=True)
