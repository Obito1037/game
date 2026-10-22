"""Read-only clean-scene BLEND/FBX/GLB tree audit. Never saves input assets."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import traceback

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'world-v10'
TARGETS={'Garden_TreeTrunks','Garden_TreeCanopies','Garden_CanopyLeafEdges'}
spec=importlib.util.spec_from_file_location('frozen_audit',BASE/'verify_world_v10.py')
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
a.TARGETS=TARGETS
report={'revision':'world-v12','game_candidate':'v13','passed':False,'in_progress':True,'checks':[],
 'limits':['This verifies asset preservation and interchange, not visual acceptance or runtime performance.',
           'Low source trunk/root components are kept; upper TreeTrunks collider intentionally changes.',
           'Static triangle intersections are reported for cabin/moondial only; no continuous wind or complete visibility proof.']}


def checkpoint(stage):
    report['stage']=stage
    (OUT/'interchange-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('TREE_AUDIT',stage,flush=True)


def read_targets(manifest):
    a.load(OUT/'island.blend','blend')
    source={}
    for name in sorted(TARGETS):
        obj=bpy.data.objects[name]
        mesh=obj.data
        mesh.calc_loop_triangles()
        points=[obj.matrix_world@v.co for v in mesh.vertices]
        tree=KDTree(len(points))
        for i,p in enumerate(points):tree.insert(p,i)
        tree.balance()
        colours=[None]*len(points)
        normals=[[] for _ in points]
        uv=[[] for _ in points]
        nm=obj.matrix_world.to_3x3().inverted().transposed()
        for loop,normal in zip(mesh.loops,mesh.corner_normals):
            colour=a.colour_at(mesh,loop)
            old=colours[loop.vertex_index]
            a.require(old is None or old==colour,'Corner-dependent source colour '+name)
            colours[loop.vertex_index]=colour
            n=tuple((nm@normal.vector).normalized())
            if n not in normals[loop.vertex_index]:normals[loop.vertex_index].append(n)
            value=tuple(mesh.uv_layers[0].data[loop.index].uv)
            if value not in uv[loop.vertex_index]:uv[loop.vertex_index].append(value)
        a.require(all(c is not None for c in colours),'Unreferenced source vertices '+name)
        vertices_seen=set()
        faces_seen=set()
        classes={}
        for part in manifest['parts'][name]:
            ids=set(range(part['vertex_start'],part['vertex_start']+part['vertex_count']))
            a.require(not vertices_seen.intersection(ids),'Overlapping part vertex ranges')
            a.require(not faces_seen.intersection(part['polygon_indices']),'Overlapping part faces')
            vertices_seen.update(ids)
            faces_seen.update(part['polygon_indices'])
            for fi in part['polygon_indices']:
                a.require(set(mesh.polygons[fi].vertices)<=ids,'Part crosses vertex range')
            classes[part['kind']]=classes.get(part['kind'],0)+1
        a.require(vertices_seen==set(range(len(points))) and faces_seen==set(range(len(mesh.polygons))),'Parts do not cover mesh '+name)
        source[name]={'tree':tree,'colours':colours,'normals':normals,'uv':uv,'vertices':len(points),
                      'triangles':len(mesh.loop_triangles),'materials':[m.name for m in mesh.materials],
                      'parts':len(manifest['parts'][name]),'classes':classes}
    return source


def bvh(name):
    obj=bpy.data.objects[name]
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
      [tuple(p.vertices) for p in obj.data.polygons],all_triangles=False)


def static_intersections():
    names=[o.name for o in bpy.context.scene.objects if o.type=='MESH' and
           (o.name.startswith('Cabin_') and o.name!='Cabin_ClimbingIvy' or o.name=='MoonDial_Sculpture')]
    obstacles={name:bvh(name) for name in names}
    rows=[]
    for target in sorted(TARGETS):
        tree=bvh(target)
        for name,obstacle in obstacles.items():
            pairs=tree.overlap(obstacle)
            rows.append({'tree_mesh':target,'obstacle':name,'overlapping_polygon_pairs':len(pairs),'first_pairs':pairs[:8]})
    return rows


def byte_model(mesh,mapping,reference,raw):
    attr=mesh.color_attributes.active_color
    a.require(attr.data_type=='BYTE_COLOR' and attr.domain in {'CORNER','POINT'},'Unexpected GLB local colour storage')
    domain,dtype=attr.domain,attr.data_type
    if domain=='POINT':source_ids=np.asarray(mapping,dtype=np.int32)
    else:source_ids=np.asarray([mapping[l.vertex_index] for l in mesh.loops],dtype=np.int32)
    actual=np.empty((len(attr.data),4),dtype=np.float32)
    attr.data.foreach_get('color',actual.ravel())
    source_values=np.asarray(reference['colours'],dtype=np.float32)[source_ids]
    raw_values=np.ascontiguousarray(raw[source_ids],dtype=np.float32)
    # Exact local BYTE_COLOR linear->sRGB8->linear storage model, not an
    # arbitrary allowance hiding a gamma mismatch.
    active=mesh.color_attributes.active_color_index
    render=mesh.color_attributes.render_color_index
    temp=mesh.color_attributes.new('__readback_quantization_proof__',dtype,domain)
    try:
        temp.data.foreach_set('color',raw_values.ravel())
        predicted=np.empty_like(raw_values)
        temp.data.foreach_get('color',predicted.ravel())
    finally:
        mesh.color_attributes.remove(temp)
        mesh.color_attributes.active_color_index=active
        mesh.color_attributes.render_color_index=render
    residual=a.error_stats(actual,predicted)
    return {'type':dtype,'domain':domain,'model_residual':residual,
            'source_linear_error':a.error_stats(actual,source_values),'passed':residual['max_rgba']<=1e-7}


def target_check(name,source,kind,raw):
    obj=bpy.data.objects[name]
    mesh=obj.data
    ref=source[name]
    points=[obj.matrix_world@v.co for v in mesh.vertices]
    mapping,pos_error=a.match_positions(points,ref,name)
    nm=obj.matrix_world.to_3x3().inverted().transposed()
    angle_max=colour_max=uv_max=0.
    for loop,normal in zip(mesh.loops,mesh.corner_normals):
        source_id=mapping[loop.vertex_index]
        n=(nm@normal.vector).normalized()
        dot=max(n.dot(Vector(saved)) for saved in ref['normals'][source_id])
        angle_max=max(angle_max,math.degrees(math.acos(max(-1,min(1,dot)))))
        actual=a.colour_at(mesh,loop)
        colour_max=max(colour_max,max(abs(x-y) for x,y in zip(actual,ref['colours'][source_id])))
        uv=mesh.uv_layers[0].data[loop.index].uv
        uv_max=max(uv_max,min((uv-Vector(v)).length for v in ref['uv'][source_id]))
    slots=[m.name for m in mesh.materials]
    model=byte_model(mesh,mapping,ref,raw[name]) if kind=='glb' else None
    passed=(pos_error<=1e-5 and angle_max<=.2 and uv_max<=1e-6 and slots==ref['materials']
            and (model['passed'] if model else colour_max<=1e-6))
    return {'mesh':name,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
            'max_position_error_metres':pos_error,'max_corner_normal_error_degrees':angle_max,
            'max_uv_error':uv_max,'max_colour_error':colour_max,'material_slots_identical':slots==ref['materials'],
            'linear_byte_colour_model':model,'passed':passed}


def verify_format(kind,expected,source,raw):
    a.load(BASE/('island.'+kind),kind)
    frozen={o.name:a.fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    anchors=a.anchors()
    materials=a.used_materials()
    matrices={o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='MESH'}
    a.load(OUT/('island.'+kind),kind)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    errors=[]
    unchanged=[]
    for name,digest in frozen.items():
        actual=a.fingerprint(bpy.data.objects[name])
        unchanged.append({'name':name,'baseline_sha256':digest,'candidate_sha256':actual,'same':digest==actual})
    if len(frozen)!=26 or not all(item['same'] for item in unchanged):errors.append('Non-target fingerprint mismatch')
    new_matrices={o.name:[list(row) for row in o.matrix_world] for o in objects}
    if matrices!=new_matrices:errors.append('Object transform mismatch')
    if anchors!=a.anchors() or len(anchors)!=14:errors.append('Anchor mismatch')
    if materials!=a.used_materials():errors.append('Material/value/image mismatch')
    total=0
    zero=[]
    duplicates=[]
    invalid=[]
    for obj in objects:
        m=obj.data
        m.calc_loop_triangles()
        total+=len(m.loop_triangles)
        count=sum(t.area<=1e-12 for t in m.loop_triangles)
        if count:zero.append([obj.name,count])
        count=len(m.loop_triangles)-len({tuple(sorted(t.vertices)) for t in m.loop_triangles})
        if count:duplicates.append([obj.name,count])
        if any(not math.isfinite(float(x)) for n in m.corner_normals for x in n.vector):invalid.append(obj.name)
    if len(objects)!=29 or total!=expected['triangles']:errors.append('Mesh inventory/triangle total differs')
    if zero or duplicates or invalid:errors.append('Invalid geometry/normals')
    targets=[target_check(name,source,kind,raw) for name in sorted(TARGETS)]
    if not all(t['passed'] for t in targets):errors.append('Target interchange mismatch')
    return {'format':kind,'passed':not errors,'errors':errors,'mesh_count':len(objects),'triangles':total,
            'unchanged_non_targets':unchanged,'anchors_identical':anchors==a.anchors(),
            'all_object_transforms_identical':matrices==new_matrices,'materials_identical':materials==a.used_materials(),
            'zero_area_triangles':zero,'duplicate_triangles':duplicates,'invalid_normal_meshes':invalid,'targets':targets}


def main():
    manifest=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
    baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
    files=['island.blend','island.fbx','island.glb','textures/meadow-watercolor.png','textures/meadow-normal.png']
    before={str(root/name):a.sha(root/name) for root in (BASE,OUT) for name in files+['asset-manifest.json']}
    report['candidate_hashes_match']={name:a.sha(OUT/name)==manifest['sha256'][name] for name in files}
    report['source_hashes_match']={name:a.sha(BASE/name)==baseline['sha256'][name] for name in files}
    a.require(all(report['candidate_hashes_match'].values()) and all(report['source_hashes_match'].values()),'File hash drift')
    source=read_targets(manifest)
    report['source_target_parts']={name:{k:r[k] for k in ('vertices','triangles','parts','classes')} for name,r in source.items()}
    report['static_cabin_moondial_triangle_intersections']=static_intersections()
    report['low_trunk_component_checks']=manifest['low_trunk_component_checks']
    report['new_wood_min_y']=manifest['new_wood_min_y']
    checkpoint('source_targets')
    report['raw_glb_linear_colours'],raw=a.audit_raw_glb(OUT/'island.glb',source)
    checkpoint('raw_glb')
    for kind in ['blend','fbx','glb']:
        checkpoint('readback_'+kind)
        try:record=verify_format(kind,manifest,source,raw)
        except Exception as error:record={'format':kind,'passed':False,'errors':[str(error)],'traceback':traceback.format_exc()}
        report['checks'].append(record)
        checkpoint('completed_'+kind)
    report['input_files_unchanged']={name:a.sha(name)==value for name,value in before.items()}
    report['passed']=(len(report['checks'])==3 and all(r['passed'] for r in report['checks'])
                      and all(r['passed'] for r in report['raw_glb_linear_colours']) and all(report['input_files_unchanged'].values()))
    report['in_progress']=False
    checkpoint('complete')
    a.require(report['passed'],'Readback failed; see report')


if __name__=='__main__':
    try:main()
    except Exception as error:
        report['passed']=False
        report['in_progress']=False
        report['fatal_error']=str(error)
        report['fatal_traceback']=traceback.format_exc()
        checkpoint('failed')
        raise
