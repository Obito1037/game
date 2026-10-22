"""Targeted CPU-only FBX roundtrip and blink views; frozen assets are read-only."""
import bpy,ast,hashlib,json,math,os,re
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'art/generated/character-v9/traveler.fbx'
CAND=ROOT/'art/generated/character-v11/traveler.fbx'
BLEND=ROOT/'art/generated/character-v11/traveler.blend'
for filename,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract'})]:
    tree=ast.parse((ROOT/'art/blender'/filename).read_text(encoding='utf-8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),filename,'exec'))
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
inputs={str(p.relative_to(ROOT)):sha(p) for p in [BASE,CAND,BLEND]}
report={'passed':False,'scope':'Targeted v9/v11 same-format FBX body/rig/pivot protection, BLEND-to-FBX head shape/normal/material checks and actual imported FBX blink views. No GLB or normal-game acceptance.','pid':os.getpid(),'inputs':inputs}
def root_objects():
    root=bpy.data.objects.get('TravelerRoot');assert root is not None,'TravelerRoot absent'
    objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    assert len(objects)==62,('Unexpected mesh count',len(objects))
    return root,objects
def import_fbx(file):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(file),use_custom_normals=True,use_anim=False)
    return root_objects()
def corners(obj):
    basis=obj.matrix_world.to_3x3().inverted().transposed()
    return [(basis@Vector(n.vector)).normalized() for n in obj.data.corner_normals]
def stats(obj):
    obj.data.calc_loop_triangles();normals=corners(obj)
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    low=[min(p[d] for p in points) for d in range(3)];high=[max(p[d] for p in points) for d in range(3)]
    degenerate=sum((points[t.vertices[1]]-points[t.vertices[0]]).cross(points[t.vertices[2]]-points[t.vertices[0]]).length/2<1e-12 for t in obj.data.loop_triangles)
    return {'vertices':len(points),'triangles':len(obj.data.loop_triangles),'min':low,'max':high,'dimensions':[b-a for a,b in zip(low,high)],'cornerNormals':len(normals),'invalidNormals':sum(not all(math.isfinite(c) for c in n) or n.length<.99 for n in normals),'minimumNormalLength':min((n.length for n in normals),default=0),'meanNormalY':sum(n.y for n in normals)/max(1,len(normals)),'zeroAreaTriangles':degenerate,'materials':[m.name for m in obj.data.materials]},points
try:
    bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False);source_root,source_objects=root_objects()
    targets={o.name for o in bpy.data.objects['Head'].children_recursive if o.type=='MESH'};assert len(targets)==15
    source_heads={name:stats(source_objects[name]) for name in targets}
    base_root,base_objects=import_fbx(BASE)
    base_states={n:mesh_state(o) for n,o in base_objects.items() if n not in targets};base_contract=object_contract(base_root)
    base_materials={m.name:material_state(m) for o in base_objects.values() for m in o.data.materials}
    baseline_head_stats={n:stats(base_objects[n])[0] for n in targets}
    cand_root,cand_objects=import_fbx(CAND);checks=[]
    for name,old in base_states.items():
        current=mesh_state(cand_objects[name]);channelChecks={key:old[key]==current[key] for key in old}
        checks.append({'mesh':name,'allChannelsIdentical':all(channelChecks.values()),'channels':channelChecks,'baselineSHA256':digest(old),'candidateSHA256':digest(current)})
    report['protectedMeshes']=checks;report['protectedMeshCount']=len(checks)
    report['sameFormatBodyMeshProtectionPassed']=len(checks)==47 and all(c['allChannelsIdentical'] for c in checks)
    report['sameFormatObjectBonePivotContractIdentical']=base_contract==object_contract(cand_root)
    candidate_materials={m.name:material_state(m) for o in cand_objects.values() for m in o.data.materials}
    report['sameFormatMaterialGraphsIdentical']=base_materials==candidate_materials
    head=[]
    for name in sorted(targets):
        actual,points=stats(cand_objects[name]);expected,original=source_heads[name]
        source_tree=KDTree(len(original))
        for i,p in enumerate(original):source_tree.insert(p,i)
        source_tree.balance();target_tree=KDTree(len(points))
        for i,p in enumerate(points):target_tree.insert(p,i)
        target_tree.balance()
        max_error=max([source_tree.find(p)[2] for p in points]+[target_tree.find(p)[2] for p in original])
        dim_error=max(abs(a-b) for a,b in zip(actual['dimensions'],expected['dimensions']))
        material_names_match=actual['materials']==expected['materials']
        eye_faces_forward=not name.startswith('Head_Eye_') or actual['meanNormalY']<-.20
        row={'mesh':name,'expectedBLEND':expected,'actualFBX':actual,'baselineFBXZeroAreaTriangles':baseline_head_stats[name]['zeroAreaTriangles'],'maxBidirectionalPositionErrorMetres':max_error,'maxDimensionErrorMetres':dim_error,'materialNamesMatch':material_names_match,'eyeFacesForward':eye_faces_forward,'passed':max_error<.00002 and dim_error<.00002 and material_names_match and actual['invalidNormals']==0 and eye_faces_forward}
        head.append(row)
    report['head']=head;report['headPassed']=all(x['passed'] for x in head)
    report['sourceHeadBoundsAndNormalsCheckedAgainstActualFBX']=True
    report['sameFormatImportMeshCount']=len(cand_objects)
    assert report['sameFormatBodyMeshProtectionPassed'],'FBX non-head geometry/weights/channels differ'
    assert report['sameFormatObjectBonePivotContractIdentical'],'FBX object/bone/pivot contract differs'
    assert report['sameFormatMaterialGraphsIdentical'],'FBX material graphs differ'
    assert report['headPassed'],'Head roundtrip shape/normal/material check failed'
    print('HEAD_V11_FBX_CHECKS '+json.dumps({'protectedMeshes':len(checks),'headMeshes':len(head),'maxHeadPositionError':max(x['maxBidirectionalPositionErrorMetres'] for x in head),'pid':os.getpid()}),flush=True)
    # Keep original studio lights/camera and original material style for a shape-only
    # blink view, while every displayed vertex comes from the actual imported FBX.
    bpy.ops.wm.open_mainfile(filepath=str(BLEND),load_ui=False);old_root,old_objects=root_objects();style={m.name:m for m in bpy.data.materials}
    for obj in list(old_root.children_recursive)+[old_root]:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(CAND),use_custom_normals=True,use_anim=False);render_root,render_objects=root_objects()
    for obj in render_objects.values():
        for i,m in enumerate(obj.data.materials):
            name=re.sub(r'\.\d{3}$','',m.name);assert name in style,name
            obj.data.materials[i]=style[name]
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=17;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=512;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera;camera.location=(0,-4,1.27);camera.rotation_euler=(Vector((0,-.002,1.15))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.54
    blink_views=[]
    for state,value in [('open',.001),('closed',1.)]:
        for label in ['L','R']:bpy.data.objects['Blink_'+label].scale=(value,value,1)
        bpy.context.view_layer.update();scene.render.filepath=str(OUT/('fbx-front-'+state+'.png'));bpy.ops.render.render(write_still=True)
        blink_views.append({'state':state,'file':'fbx-front-'+state+'.png','blinkScale':[value,value,1],'actualGeometry':'Imported character-v11 FBX; authoring style materials assigned only for CPU shape visibility.'})
    report['blinkViews']=blink_views
    report['inputFilesUnchanged']={str(p.relative_to(ROOT)):sha(p)==inputs[str(p.relative_to(ROOT))] for p in [BASE,CAND,BLEND]}
    assert all(report['inputFilesUnchanged'].values()),'Frozen asset changed'
    report['passed']=True;report['limits']=['Zero-area endpoint triangles are reported per head object against v9; no GLB acceptance is claimed.','CPU blink originals require visual inspection; two end states do not prove natural intermediate runtime blinking.','CPU images use actual FBX geometry with the known authoring material style; the separately compared imported FBX graphs are recorded above.','This is not Unity import, animation/normal gameplay acceptance, or isolated performance evidence.']
except Exception as e:
    report['failure']=str(e)
    (OUT/'fbx-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise
(OUT/'fbx-readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAD_V11_FBX_COMPLETE '+json.dumps({'passed':report['passed'],'pid':os.getpid()}),flush=True)
