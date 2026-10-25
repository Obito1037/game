"""Extend only submerged pier piles; retain deck, markers and every other prop."""
import sys
sys.dont_write_bytecode=True
import bpy
import json
import hashlib
import shutil
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v1/props'
SCRIPT=Path(__file__)
TARGET_BOTTOM=-3.2
KEEP_ABOVE=-.40

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def coordinates():
    return {o.name:[tuple(o.matrix_world@v.co) for v in o.data.vertices] for o in bpy.context.scene.objects if o.type=='MESH'}
def markers():
    return {o.name:tuple(o.matrix_world.translation) for o in bpy.context.scene.objects if o.type=='EMPTY'}

def preview(path,bmin,bmax):
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.world.color=(.17,.17,.17);scene.view_settings.view_transform='AgX'
    center=Vector(tuple((a+b)*.5 for a,b in zip(bmin,bmax)));span=max(b-a for a,b in zip(bmin,bmax))
    bpy.ops.object.camera_add(location=center+Vector((span*.95,-span*1.65,span*.95)))
    cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=span*1.47;scene.camera=cam
    for pos,power in [((span,-span*2,span*3),220*span*span),((-span,-span*.4,span*1.1),65*span*span)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(pos));o=bpy.context.object
        o.data.energy=power;o.data.shape='DISK';o.data.size=span*2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)

manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
results=[]
for asset_id in ['pier_module','pier_end']:
    folder=OUT/asset_id;blend=folder/(asset_id+'.blend');fbx=folder/(asset_id+'.fbx');metadata=folder/'asset.json'
    before_hash={'blend':sha(blend),'fbx':sha(fbx),'asset_json':sha(metadata)}
    for path in [blend,fbx,metadata]:
        backup=path.with_name(path.stem+'.before-pile-extension'+path.suffix)
        if not backup.exists():shutil.copy2(path,backup)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    bpy.context.view_layer.update()
    before=coordinates();before_markers=markers()
    original_bottom=min(p[2] for vertices in before.values() for p in vertices)
    count=0
    if original_bottom>TARGET_BOTTOM+1e-5:
        ratio=(TARGET_BOTTOM-KEEP_ABOVE)/(original_bottom-KEEP_ABOVE)
        for o in bpy.context.scene.objects:
            if o.type!='MESH':continue
            inverse=o.matrix_world.inverted()
            for vertex in o.data.vertices:
                world=o.matrix_world@vertex.co
                if world.z<KEEP_ABOVE:
                    world.z=KEEP_ABOVE+(world.z-KEEP_ABOVE)*ratio
                    vertex.co=inverse@world
                    count+=1
            o.data.update()
    bpy.context.view_layer.update()
    after=coordinates();after_markers=markers()
    assert before_markers==after_markers,'Markers moved'
    for name,points in before.items():
        assert len(points)==len(after[name]),'Vertex topology changed'
        for index,p in enumerate(points):
            q=after[name][index]
            assert abs(p[0]-q[0])<1e-6 and abs(p[1]-q[1])<1e-6,'Pile width or deck plan changed'
            if p[2]>=KEEP_ABOVE:
                assert max(abs(x-y) for x,y in zip(p,q))<1e-6,'Deck, girder or positive geometry moved'
    points=[p for vertices in after.values() for p in vertices]
    bmin=[min(p[k] for p in points) for k in range(3)];bmax=[max(p[k] for p in points) for k in range(3)]
    assert abs(bmin[2]-TARGET_BOTTOM)<1e-4,'Submerged pile target depth not met'
    meshes=[];total=0
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        o.data.calc_loop_triangles();n=len(o.data.loop_triangles);total+=n
        meshes.append({'name':o.name,'triangles':n,'materials':[s.material.name for s in o.material_slots if s.material]})
    data=json.loads(metadata.read_text(encoding='utf-8'))
    assert total==data['triangles'],'Triangle count changed'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    data['fbx_sha256']=sha(fbx);data['bounds_blender']={'min':bmin,'max':bmax};data['dimensions_metres']=[round(bmax[k]-bmin[k],4) for k in range(3)];data['meshes']=meshes
    data['notes']=[note.replace('Piles extend 1.96m below deck.','Piles extend 3.20m below deck.') for note in data.get('notes',[])]
    extra='Pile extension: all geometry at Z >= -0.40m, X/Y coordinates, topology, markers and deck top retained; only lower pile vertices stretched to Z=-3.20m. At deck Y=2.48m the pile bottom is Y=-0.72m, 0.56m below sea level -0.16m.'
    if extra not in data['notes']:data['notes'].append(extra)
    processing={'step':'extend_submerged_piles_v1','script':rel(SCRIPT),'script_sha256':sha(SCRIPT),'input_sha256':before_hash,'changed_vertices':count,'original_bottom_z':original_bottom,'new_bottom_z':bmin[2],'unchanged_at_or_above_z':KEEP_ABOVE,'deck_and_markers_unchanged':True,'triangles_unchanged':True}
    data.setdefault('postprocessing',[]).append(processing)
    metadata.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for i,old in enumerate(manifest['assets']):
        if old['asset_id']==asset_id:manifest['assets'][i]=data;break
    results.append({'asset_id':asset_id,**processing,'output_fbx_sha256':data['fbx_sha256']})
    preview(folder/'preview.png',bmin,bmax)
manifest['triangles_unique_assets']=sum(a['triangles'] for a in manifest['assets'])
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'pier-extension-verification.json').write_text(json.dumps({'status':'passed','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
print('PIER_EXTENSION_PASSED',json.dumps(results),flush=True)
