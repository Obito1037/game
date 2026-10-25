"""Read-only v1 sources; isolated night A/B materials, no Unity operations.

Blender --background --factory-startup --python env_v2_vegetation_study.py
Pass -- --audit-only to stop after source/material diagnostics.
"""
import bpy,json,hashlib,math,re,sys
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v2/vegetation-study';OUT.mkdir(parents=True,exist_ok=True)
MANIFEST=ROOT/'art/generated/env-v1/asset-manifest.json'
SPECS={a['id']:a for a in json.loads(MANIFEST.read_text(encoding='utf-8'))['assets'] if a['id'] in ['tree_a','tree_b','tree_c','tree_gold']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def meshes():return [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('Study_')]
def geometry():
    data=[]
    for o in sorted(meshes(),key=lambda o:o.name):
        data.append({'name':o.name,'matrix':[list(r) for r in o.matrix_world],'vertices':[list(v.co) for v in o.data.vertices],
                     'polygons':[[p.material_index,list(p.vertices)] for p in o.data.polygons],
                     'uv':[list(v.uv) for v in o.data.uv_layers.active.data] if o.data.uv_layers.active else None,
                     'materials':[m.name if m else None for m in o.data.materials]})
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
def bounds():
    points=[o.matrix_world@v.co for o in meshes() for v in o.data.vertices]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    return lo,hi
def image_array(image,cache):
    if image.name not in cache:
        w,h=image.size;data=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(data);cache[image.name]=data.reshape(h,w,4)
    return cache[image.name]
def incoming_image(bs,socket):
    item=bs.inputs[socket]
    if not item.is_linked:return None
    node=item.links[0].from_node
    return node.image if node.type=='TEX_IMAGE' else None
def stats(values):
    if not len(values):return None
    a=np.asarray(values,dtype=float)
    return {'mean_rgb':a.mean(axis=0).tolist(),'max_rgb':a.max(axis=0).tolist(),'p95_rgb':np.percentile(a,95,axis=0).tolist(),
            'fraction_max_channel_above_1':float((a.max(axis=1)>1).mean()),'fraction_max_channel_above_0_01':float((a.max(axis=1)>.01).mean())}
def unity_material(name):
    path=ROOT/'GameProject/Assets/JieGuang/Environment/Generated/Materials'/f'{name}.mat'
    if not path.exists():return {'path':str(path.relative_to(ROOT)),'exists':False}
    text=path.read_text(encoding='utf-8');result={'path':str(path.relative_to(ROOT)),'exists':True,'sha256':sha(path)}
    for key in ['_BaseColor','_EmissionColor']:
        match=re.search(r'- '+key+r': \{r: ([\deE.+-]+), g: ([\deE.+-]+), b: ([\deE.+-]+), a: ([\deE.+-]+)\}',text)
        if match:result[key]=[float(v) for v in match.groups()]
    for key in ['_Smoothness','_Cull','_AlphaClip']:
        match=re.search(r'- '+key+r': ([\deE.+-]+)',text)
        if match:result[key]=float(match.group(1))
    result['emission_enabled']='  - _EMISSION\n' in text
    return result

def audit(asset):
    spec=SPECS[asset];source=ROOT/spec['blend'];bpy.ops.wm.open_mainfile(filepath=str(source));cache={};mats={};objects=[]
    for o in meshes():
        o.data.calc_loop_triangles();objects.append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),'material_slots':[m.name for m in o.data.materials]})
        for p in o.data.polygons:
            m=o.data.materials[p.material_index]
            if m.name not in mats:
                bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
                mats[m.name]={'polygons':0,'triangles':0,'surface_area':0.,'centroid_base_rgb':[],'centroid_emission_rgb':[],
                              'principled':{'base_color':list(bs.inputs['Base Color'].default_value),'roughness':bs.inputs['Roughness'].default_value,
                                            'emission_strength':bs.inputs['Emission Strength'].default_value,'emission_default_color':list(bs.inputs['Emission Color'].default_value)},
                              'blender_nodes':[{'name':n.name,'type':n.type} for n in m.node_tree.nodes],
                              'unity_read_only':unity_material(m.name),'images':[]}
                for n in m.node_tree.nodes:
                    if n.type!='TEX_IMAGE' or not n.image:continue
                    im=n.image;arr=image_array(im,cache);path=Path(bpy.path.abspath(im.filepath))
                    mats[m.name]['images'].append({'node':n.name,'name':im.name,'size':list(im.size),'color_space':im.colorspace_settings.name,
                        'path':str(path),'file_exists':path.is_file(),'sha256':sha(path) if path.is_file() else None,
                        'pixel_rgb':stats(arr[:,:,:3].reshape(-1,3))})
            entry=mats[m.name];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            entry['polygons']+=1;entry['triangles']+=len(p.vertices)-2;entry['surface_area']+=p.area
            uv=sum((o.data.uv_layers.active.data[l].uv for l in p.loop_indices),Vector((0,0)))/len(p.loop_indices)
            for socket,key in [('Base Color','centroid_base_rgb'),('Emission Color','centroid_emission_rgb')]:
                im=incoming_image(bs,socket)
                if im:
                    arr=image_array(im,cache);h,w=arr.shape[:2];value=arr[int((uv.y%1)*h)%h,int((uv.x%1)*w)%w,:3]
                else:value=np.array(bs.inputs[socket].default_value[:3])
                if key=='centroid_emission_rgb':value=value*bs.inputs['Emission Strength'].default_value
                entry[key].append(value.tolist())
    area=sum(x['surface_area'] for x in mats.values());tri=sum(x['triangles'] for x in mats.values())
    for m in mats.values():
        m['fraction_total_area']=m['surface_area']/area;m['fraction_total_triangles']=m['triangles']/tri
        for key in ['centroid_base_rgb','centroid_emission_rgb']:m[key]=stats(m[key])
    lo,hi=bounds()
    return {'id':asset,'source_blend':str(source.relative_to(ROOT)),'source_sha256':sha(source),'geometry_and_slots_sha256':geometry(),
            'bounds':{'min':list(lo),'max':list(hi)},'objects':objects,'triangles':tri,'materials':mats,
            'scope_note':'Stats use original material slots and nearest texture sample at polygon UV centroids; not a semantic leaf/back/fruit segmentation proof.'}

def configure_night(asset):
    sc=bpy.context.scene
    for o in list(sc.objects):
        if o.type in {'CAMERA','LIGHT'}:bpy.data.objects.remove(o,do_unlink=True)
    sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
    sc.view_settings.exposure=0;sc.view_settings.gamma=1;sc.render.film_transparent=False
    world=bpy.data.worlds.new('Study_CoolNightAmbient');world.use_nodes=True;sc.world=world
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.055,.085,.16,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
    bpy.ops.object.light_add(type='AREA',location=(3,-4,3.2));light=bpy.context.object;light.name='Study_WarmLamp'
    light.data.energy=240;light.data.size=1.2;light.data.color=(1,.55,.24)
    light.rotation_euler=(Vector((0,0,2.4))-light.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.05));ground=bpy.context.object;ground.name='Study_Ground'
    material=bpy.data.materials.new('Study_GroundMatte');material.use_nodes=True
    bs=material.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.075,.09,.085,1);bs.inputs['Roughness'].default_value=.94;ground.data.materials.append(material)
    lo,hi=bounds();height=hi.z-lo.z;span=max(hi-lo);center=(lo+hi)*.5
    views={'whole':{'position':list(center+Vector((.20,-1,.20)).normalized()*span*3),'look':list(center),'scale':span*1.20},
           'canopy':{'position':list(Vector((0,0,height*.68))+Vector((.30,-1,.10)).normalized()*span*3),'look':[0,0,height*.68],'scale':span*.80}}
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Study_Camera';cam.data.type='ORTHO';sc.camera=cam
    return views,cam

SETTINGS={
 'tree_a':{'leaf_tint':[.77,1.04,1.02,1],'leaf_strength':.035,'fruit_strength':.75},
 'tree_gold':{'leaf_tint':[.90,1.02,.88,1],'leaf_strength':.075,'fruit_strength':.90},
}
def candidate_materials(asset):
    settings=SETTINGS[asset];changes=[]
    for m in {m for o in meshes() for m in o.data.materials if m}:
        if not (m.name.endswith('_LeafVeins') or m.name.endswith('_WarmFruit')):continue
        bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');is_leaf=m.name.endswith('_LeafVeins')
        if is_leaf:
            source=bs.inputs['Base Color'].links[0].from_socket
            tint=m.node_tree.nodes.new('ShaderNodeMixRGB');tint.name='Study_SilverGreenMultiply';tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
            tint.inputs[2].default_value=settings['leaf_tint'];m.node_tree.links.new(source,tint.inputs[1]);m.node_tree.links.new(tint.outputs[0],bs.inputs['Base Color'])
        bs.inputs['Emission Strength'].default_value=settings['leaf_strength'] if is_leaf else settings['fruit_strength']
        changes.append({'material':m.name,'base_tint':settings['leaf_tint'] if is_leaf else [1,1,1,1],
                        'emission_strength':bs.inputs['Emission Strength'].default_value,'roughness':bs.inputs['Roughness'].default_value,
                        'emission_map':'Original RGB mask unchanged; no unmasked leaf emission.'})
    return changes

def render(asset,variant,views,cam):
    folder=OUT/asset;folder.mkdir(exist_ok=True)
    for view,cfg in views.items():
        cam.location=cfg['position'];cam.rotation_euler=(Vector(cfg['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cfg['scale']
        bpy.context.scene.render.filepath=str(folder/f'{variant}-{view}.png');bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{asset}_{variant}_study.blend'))

audits=[]
for asset in SPECS:
    audits.append(audit(asset));dump('source-material-audit.json',{'assets':audits,'notes':['Bark is the actual trunk slot name; it is preserved, not renamed to Trunk.','tree_b also has a pre-existing BarkRepair slot, which is preserved.','Existing masks are color-threshold derived; they are not author-painted semantic vein/underside/edge masks.']})
    print('VEGETATION_AUDIT_DONE',asset,flush=True)
if '--audit-only' in sys.argv:raise SystemExit(0)
results=[]
for asset in ['tree_a','tree_gold']:
    source=ROOT/SPECS[asset]['blend'];before_source_sha=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));before_geo=geometry()
    views,cam=configure_night(asset);render(asset,'A-current',views,cam)
    changes=candidate_materials(asset);render(asset,'B-controlled',views,cam)
    after_geo=geometry();folder=OUT/asset
    result={'asset':asset,'source_sha256':before_source_sha,'source_unchanged':sha(source)==before_source_sha,
            'geometry_uv_slots_exact':before_geo==after_geo,'geometry_and_slots_sha256':after_geo,'changes':changes,'views':views,
            'night_rig':{'ambient_color':[.055,.085,.16],'ambient_strength':.45,'warm_lamp_color':[1,.55,.24],'warm_lamp_watts':240,'warm_lamp_position':[3,-4,3.2]},
            'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(folder.iterdir()) if p.suffix in ['.png','.blend']]}
    results.append(result);dump('candidate-manifest.json',{'status':'offline-two-asset-material-study-not-imported','script_sha256':sha(Path(__file__)),'assets':results,
        'limitations':['No geometry or silhouette improvement is claimed.','Original RGB emission masks are retained and weakened; this does not isolate actual leaf backs or gold leaf edges.','This Blender night rig is a controlled comparison, not a reproduction or verification of the Unity night scene.','No PNG pixel edits; no Unity assets, colliders, anchors or gameplay files were modified.']})
    print('VEGETATION_CANDIDATE_DONE',asset,'geometry_exact',before_geo==after_geo,flush=True)
