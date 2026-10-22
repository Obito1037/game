"""Independent clean-scene readback; this script never writes source assets."""
import bpy, json, math, hashlib, struct
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'GameProject').is_dir())
expected=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
baseline=json.loads((ROOT/'art/generated/world-v4/asset-manifest.json').read_text(encoding='utf-8'))
assert expected['anchors_unity']==baseline['anchors_unity'],'Anchor source contract changed'
expected_names={o['name'] for o in expected['objects']}
expected_colors={x['mesh']:x for x in expected['vertex_colors']}
glb=(OUT/'island.glb').read_bytes();json_length=struct.unpack_from('<I',glb,12)[0]
glb_json=json.loads(glb[20:20+json_length]);binary_start=20+json_length+8
raw_glb_colors=[]
for mesh in glb_json['meshes']:
    values=[]
    for primitive in mesh['primitives']:
        accessor=glb_json['accessors'][primitive['attributes']['COLOR_0']]
        view=glb_json['bufferViews'][accessor['bufferView']]
        dtype={5123:'<u2',5126:'<f4',5121:'u1'}[accessor['componentType']]
        offset=binary_start+view.get('byteOffset',0)+accessor.get('byteOffset',0)
        data=np.frombuffer(glb,dtype=dtype,count=accessor['count']*4,offset=offset).reshape((-1,4))[:,:3].astype(float)
        if accessor.get('normalized'):data/=65535 if accessor['componentType']==5123 else 255
        values.extend([float(data.min()),float(data.max())])
    lo,hi=min(values),max(values);want=expected_colors[mesh['name']]
    assert abs(lo-want['min_rgb'])<.00004 and abs(hi-want['max_rgb'])<.00004,'Raw GLB COLOR_0 is not preserved'
    raw_glb_colors.append({'mesh':mesh['name'],'min_rgb':lo,'max_rgb':hi,'color_space':'linear','encoding':'normalized UINT16 COLOR_0'})
for name in ['meadow-watercolor.png','meadow-normal.png']:
    assert (OUT/'textures'/name).read_bytes()==(ROOT/'art/generated/world-v4/textures'/name).read_bytes(),'Existing ground texture changed'

# Unchanged geometry must keep every surviving vertex at its baseline position;
# zero-area legacy pole cleanup can remove unused vertices but cannot move them.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/generated/world-v4/island.blend'))
baseline_positions={o.name:{tuple(round(float(v),6) for v in p.co) for p in o.data.vertices} for o in bpy.context.scene.objects if o.type=='MESH'}
cleanup_baseline=OUT/'cleanup-baseline.blend'
pre_cleanup_positions={};pre_cleanup_colors={};pre_cleanup_mesh_triangles={}
if cleanup_baseline.exists():
    bpy.ops.wm.open_mainfile(filepath=str(cleanup_baseline))
    for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        mesh=obj.data;pre_cleanup_positions[obj.name]={tuple(round(float(c),6) for c in v.co) for v in mesh.vertices}
        pre_cleanup_mesh_triangles[obj.name]=sum(len(p.vertices)-2 for p in mesh.polygons)
        attr=mesh.color_attributes.active_color
        pre_cleanup_colors[obj.name]={tuple(round(float(c),6) for c in mesh.vertices[loop.vertex_index].co)+tuple(round(float(c),6) for c in attr.data[loop.index].color) for loop in mesh.loops}
checks=[]
for kind in ['blend','fbx','glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=OUT/('island.'+kind)
    if kind=='blend':bpy.ops.wm.open_mainfile(filepath=str(source))
    elif kind=='fbx':bpy.ops.import_scene.fbx(filepath=str(source),use_custom_normals=True,colors_type='LINEAR')
    else:bpy.ops.import_scene.gltf(filepath=str(source))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];errors=[]
    if {o.name for o in meshes}!=expected_names:errors.append('Named mesh set differs')
    tri=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)
    if tri!=expected['triangles']:errors.append('Triangle count differs '+str(tri))
    if tri>400000:errors.append('Triangle budget exceeded')
    degenerate=[];colors=[]
    for obj in meshes:
        obj.data.calc_loop_triangles()
        bad=sum(t.area<1e-12 for t in obj.data.loop_triangles)
        if bad:degenerate.append({'mesh':obj.name,'count':bad})
        duplicated=len(obj.data.loop_triangles)-len({tuple(sorted(t.vertices)) for t in obj.data.loop_triangles})
        if duplicated:errors.append('Duplicate triangles remain '+obj.name+': '+str(duplicated))
        if any(not math.isfinite(float(c)) for v in obj.data.vertices for c in v.co):errors.append('Nonfinite vertex '+obj.name)
        if not obj.data.uv_layers:errors.append('Missing UV '+obj.name)
        attr=obj.data.color_attributes.active_color
        if attr is None:errors.append('Missing vertex colors '+obj.name);continue
        values=[float(c) for item in attr.data for c in item.color[:3]]
        lo,hi=min(values),max(values);want=expected_colors[obj.name]
        # The raw GLB UINT16 accessor is checked above at <0.00004 tolerance.
        # Blender 4.5 GLB importer then creates BYTE_COLOR, causing an additional
        # sRGB-byte rounding (~0.0035 here). FBX uses exact linear float colors.
        tolerance=.0045 if kind=='glb' else .00001
        if abs(lo-want['min_rgb'])>tolerance or abs(hi-want['max_rgb'])>tolerance:errors.append('Color range mismatch '+obj.name)
        colors.append({'mesh':obj.name,'attribute':attr.name,'domain':attr.domain,'min_rgb':lo,'max_rgb':hi})
    if degenerate:errors.append('Zero-area triangles remain: '+str(degenerate))
    unchanged=[]
    cleanup_checks=[]
    if kind=='blend':
        for obj in meshes:
            if obj.name in {'Garden_Walkways','Garden_HeroBoulders'}:continue
            missing=sum(tuple(round(float(c),6) for c in v.co) not in baseline_positions[obj.name] for v in obj.data.vertices)
            if missing:errors.append('Unintended vertex movement '+obj.name)
            unchanged.append({'mesh':obj.name,'vertices_not_at_baseline_position':missing})
        if pre_cleanup_positions:
            for obj in meshes:
                mesh=obj.data;attr=mesh.color_attributes.active_color
                moved=sum(tuple(round(float(c),6) for c in v.co) not in pre_cleanup_positions[obj.name] for v in mesh.vertices)
                changed_colors=sum(tuple(round(float(c),6) for c in mesh.vertices[loop.vertex_index].co)+tuple(round(float(c),6) for c in attr.data[loop.index].color) not in pre_cleanup_colors[obj.name] for loop in mesh.loops)
                if moved or changed_colors:errors.append('Cleanup moved/recolored surviving geometry '+obj.name)
                cleanup_checks.append({'mesh':obj.name,'moved_vertices':moved,'recolored_surviving_corners':changed_colors,'removed_triangles':pre_cleanup_mesh_triangles[obj.name]-sum(len(p.vertices)-2 for p in mesh.polygons)})
    anchors=[]
    for name,xyz in expected['anchors_unity'].items():
        obj=bpy.data.objects.get('Anchor_'+name)
        if obj is None:errors.append('Missing anchor '+name);continue
        p=obj.matrix_world.translation;actual=[p.x,p.z,-p.y];delta=(Vector(actual)-Vector(xyz)).length
        if delta>.0001:errors.append('Anchor moved '+name)
        anchors.append({'name':name,'actual_unity':actual,'error_metres':delta})
    path=bpy.data.objects['Garden_Walkways'];ys=[float((path.matrix_world@v.co).z) for v in path.data.vertices]
    nm=path.matrix_world.to_3x3().inverted().transposed()
    tops=[float((nm@p.normal).normalized().z) for p in path.data.polygons if (path.matrix_world@p.center).z>.045 and abs((nm@p.normal).normalized().z)>.75]
    if min(ys)<-.01001 or max(ys)>.10001:errors.append('Walkway outside -1 to +10 cm contract')
    if not tops or any(n<0 for n in tops):errors.append('Walkway top normals incorrect')
    hero=bpy.data.objects['Garden_HeroBoulders'];hero.data.calc_loop_triangles()
    if any('moss' in mat.name.lower() for mat in hero.data.materials):errors.append('Hard moss material remains on HeroBoulders')
    bvh=BVHTree.FromPolygons([hero.matrix_world@v.co for v in hero.data.vertices],[tuple(p.vertices) for p in hero.data.polygons],all_triangles=False)
    remaining_plant_hits=[]
    for entry in expected.get('plant_cleanup',[]):
        obj=bpy.data.objects[entry['mesh']];hits=0
        for vertex in obj.data.vertices:
            co=obj.matrix_world@vertex.co
            if not any(r['bounds_min_unity'][0]-.001<=co.x<=r['bounds_max_unity'][0]+.001 and r['bounds_min_unity'][2]-.001<=-co.y<=r['bounds_max_unity'][2]+.001 for r in expected['hero_boulders']):continue
            hit=bvh.ray_cast(Vector((co.x,co.y,1.5)),Vector((0,0,-1)),2)[0]
            if hit is not None:hits+=1
        remaining_plant_hits.append({'mesh':obj.name,'vertices_projecting_into_boulders':hits})
        if hits:errors.append('Plant still projects into HeroBoulders '+obj.name)
    item={'format':kind,'triangles':tri,'mesh_count':len(meshes),'uv_mesh_count':sum(bool(o.data.uv_layers) for o in meshes),'anchors':anchors,'walkway_height_range_metres':[min(ys),max(ys)],'walkway_top_faces_checked':len(tops),'downward_walkway_top_faces':sum(n<0 for n in tops),'hero_boulder_triangles':len(hero.data.loop_triangles),'hero_materials':[m.name for m in hero.data.materials],'zero_area_triangles':degenerate,'vertex_colors':colors,'unchanged_geometry_checks':unchanged,'cleanup_survivor_checks':cleanup_checks,'remaining_plant_footprint_hits':remaining_plant_hits,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':not errors,'errors':errors}
    checks.append(item);print('READBACK',kind,tri,len(meshes),'PASS' if not errors else errors,flush=True)
report={'scope':'Clean-scene BLEND / FBX / GLB readback. Vertex colors use linear multipliers. All 14 baseline anchors and surviving vertex positions on unchanged meshes checked. Blender previews do not establish Unity appearance.','passed':all(c['passed'] for c in checks),'budget':400000,'baseline_triangles':baseline['triangles'],'ground_textures_identical_to_world_v4':True,'raw_glb_color_0':raw_glb_colors,'checks':checks}
(OUT/'interchange-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['passed'],json.dumps([c['errors'] for c in checks])
print('WORLD_V5_READBACK_PASSED',flush=True)
