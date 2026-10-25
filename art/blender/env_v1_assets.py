"""Inspect and optimize the nine user-provided Tripo environment assets.

Run with Blender 4.5 --background --factory-startup --python this_file -- inventory|process.
Every input is copied, never edited. Exports are in metres, FBX -Z forward / Y up.
"""
import bpy, bmesh, json, math, hashlib, shutil, sys, os, time
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/generated/env-v1'
ASSETS = OUT / 'assets'
INCOMING = ROOT / 'art/incoming/env-2026-10-22'
DOWNLOADS = Path('C:/Users/20665/Downloads')
SPECS = [
    dict(id='tree_a', source='发光树3d模型.glb', kind='tree', dimension=4.8, budget=12000),
    dict(id='tree_b', source='发光树3d模型 (1).glb', kind='tree', dimension=4.3, budget=12000),
    dict(id='tree_c', source='发光树3d模型 (2).glb', kind='tree', dimension=5.2, budget=12000),
    dict(id='tree_gold', source='灯光盆景树3d模型.glb', kind='tree', dimension=5.0, budget=30000),
    dict(id='rock_mountain', source='岩石山3d模型.glb', kind='rock', dimension=4.5, budget=8000),
    dict(id='rock_mass', source='岩石山体3d模型.glb', kind='rock', dimension=4.0, budget=8000),
    dict(id='rock_arch', source='岩石拱门3d模型.glb', kind='rock', dimension=6.0, budget=8000),
    dict(id='rock_cluster', source='岩石群3d模型.glb', kind='rock', dimension=3.5, budget=8000),
    dict(id='boat', source='木质小艇3d模型.glb', kind='boat', dimension=5.0, budget=30000),
]

def relative(path): return str(Path(path).relative_to(ROOT)).replace('\\','/')
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()
def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def meshes(): return [o for o in bpy.context.scene.objects if o.type=='MESH']
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
def load(spec):
    clear()
    dest=INCOMING/spec['id']/spec['source']
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(DOWNLOADS/spec['source'],dest)
    elif sha(dest)!=sha(DOWNLOADS/spec['source']):raise RuntimeError('Existing source hash mismatch: '+str(dest))
    bpy.ops.import_scene.gltf(filepath=str(dest))
    bpy.context.view_layer.update()
    return dest
def bounds(objects):
    v=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
    lo=Vector(tuple(min(a[i] for a in v) for i in range(3)))
    hi=Vector(tuple(max(a[i] for a in v) for i in range(3)))
    return lo,hi
def tri_count(obj):return sum(len(p.vertices)-2 for p in obj.data.polygons)
def material_info(mat):
    if mat is None:return None
    info=dict(name=mat.name,images=[],nodes=[])
    if mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image:
                info['images'].append(dict(name=n.image.name,size=list(n.image.size),color_space=n.image.colorspace_settings.name))
            if n.type=='BSDF_PRINCIPLED':
                info['base_color']=list(n.inputs['Base Color'].default_value)
                info['emission_color']=list(n.inputs['Emission Color'].default_value)
                info['emission_strength']=n.inputs['Emission Strength'].default_value
    return info

def components(obj, detail=False):
    # glTF duplicates vertices at UV seams; weld *for analysis* by quantized positions.
    n=len(obj.data.vertices)
    co=np.empty(n*3,dtype=np.float32);obj.data.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    quant=np.round(co*100000).astype(np.int64)
    unique, inverse=np.unique(quant,axis=0,return_inverse=True)
    parent=np.arange(len(unique),dtype=np.int32)
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    edges=np.empty(len(obj.data.edges)*2,dtype=np.int32);obj.data.edges.foreach_get('vertices',edges)
    for a,b in inverse[edges].reshape(-1,2):
        a=find(a);b=find(b)
        if a!=b:parent[b]=a
    labels=np.array([find(x) for x in inverse],dtype=np.int32)
    values,counts=np.unique(labels,return_counts=True)
    order=np.argsort(-counts)
    result=[]
    for j in order[:200]:
        pts=co[labels==values[j]]
        entry=dict(vertices=int(counts[j]),min=pts.min(axis=0).tolist(),max=pts.max(axis=0).tolist(),label=int(values[j]))
        result.append(entry)
    return (result,labels) if detail else result

def setup_render(objects,size=512):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.resolution_x=size;scene.render.resolution_y=size
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new('PreviewWorld');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.075,0.095,0.13,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    scene.view_settings.view_transform='AgX'
    lo,hi=bounds(objects);center=(lo+hi)/2;span=max(hi-lo)
    for name, offset, power, color in [('Key',(3,-4,5),850,(1,.86,.70)),('Fill',(-3,-2,3),500,(.68,.83,1)),('Rim',(1,4,4),750,(1,.95,.8))]:
        light=bpy.data.lights.new('Preview'+name,'AREA');light.energy=power*span*span/4;light.shape='DISK';light.size=span*2
        o=bpy.data.objects.new(light.name,light);scene.collection.objects.link(o);o.location=center+Vector(offset)*span/2
        o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('PreviewCamera');camera.type='ORTHO';camera.ortho_scale=span*1.24
    co=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(co);scene.camera=co
    return center,span,co

def previews(objects,folder,prefix='source',size=512):
    folder.mkdir(parents=True,exist_ok=True)
    center,span,cam=setup_render(objects,size)
    result={}
    for name,dir in [('front',(0,-1,.08)),('side',(1,0,.08)),('top',(0,-.001,1))]:
        cam.location=center+Vector(dir).normalized()*span*3
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        p=folder/(prefix+'-'+name+'.png');bpy.context.scene.render.filepath=str(p)
        bpy.ops.render.render(write_still=True)
        result[name]=relative(p)
    # Preview cameras/lights should not enter model exports or its next preview.
    for obj in list(bpy.context.scene.objects):
        if obj.type in {'LIGHT','CAMERA'}:bpy.data.objects.remove(obj,do_unlink=True)
    return result

def inventory(only=None):
    inventory_path=OUT/'inventory.json'
    all_items=json.loads(inventory_path.read_text(encoding='utf-8'))['assets'] if inventory_path.exists() else []
    for spec in SPECS:
        if only and spec['id']!=only:continue
        source=load(spec);obs=meshes();lo,hi=bounds(obs)
        item=dict(**spec,source_path=relative(source),sha256=sha(source),source_bytes=source.stat().st_size,
                  coordinate_system='Blender Z-up, glTF imported with official importer; original glTF Y-up',
                  units='Source glTF nominal metres; generated source normalized scale is not trusted',
                  bounds=dict(min=list(lo),max=list(hi),dimensions=list(hi-lo)),
                  object_count=len(bpy.context.scene.objects),mesh_count=len(obs),triangles=sum(tri_count(o) for o in obs),
                  materials=[material_info(m) for m in bpy.data.materials],
                  objects=[dict(name=o.name,vertices=len(o.data.vertices),triangles=tri_count(o),matrix_world=[list(r) for r in o.matrix_world],components=components(o)) for o in obs])
        dump(ASSETS/spec['id']/'source-inventory.json',item)
        item['previews']=previews(obs,ASSETS/spec['id']/'previews')
        item['visual_review']='Pending visual review of the three source previews'
        all_items=[x for x in all_items if x['id']!=spec['id']]+[item]
        dump(inventory_path,dict(schema_version=1,design_basis='art/design/script/07_完整故事与生图提示词（最终版）.md',assets=all_items))
        print('ENV_INVENTORY_COMPLETE',spec['id'],item['triangles'],flush=True)

TREE_GROUPS={
    'tree_a': [('tree_a',[0,3,5],4.8,12000),('tree_a_sapling_01',[1],2.8,6500),('tree_a_sapling_02',[2],3.0,6500)],
    'tree_b': [('tree_b',[0,1,4,5],4.3,12000),('tree_b_sapling_01',[2],2.6,6500),('tree_b_sapling_02',[3],2.7,6500)],
    'tree_c': [('tree_c',[0,5,6,8],5.2,12000),('tree_c_sapling_01',[2,7,9],2.8,6500),('tree_c_sapling_02',[4,10],2.6,6500)],
    'tree_gold': [('tree_gold',[0,4,5,6,7,8,9,11,13],5.0,30000),('tree_gold_sapling_01',[1,14],3.1,6500),('tree_gold_sapling_02',[2,12],3.3,6500)],
}
OTHER_GROUPS={
    'rock_mountain': [('rock_mountain',[0],4.5,8000),('rock_mountain_reef_01',[1],3.1,3000),('rock_mountain_reef_02',[2],3.4,3000)],
    'rock_mass': [('rock_mass',[0],5.5,8000),('rock_mass_reef_01',[1],3.5,3000),('rock_mass_reef_02',[2],3.3,3000)],
    'rock_arch': [('rock_arch',[0],6.0,8000),('rock_arch_reef_01',[1],3.8,3000),('rock_arch_reef_02',[2],3.5,3000)],
    'rock_cluster': [('rock_cluster',[0],3.5,8000),('rock_cluster_reef_01',[1],2.5,3000),('rock_cluster_reef_02',[2],2.6,3000)],
    'boat': [('boat',[0],5.0,30000)],
}

def extract_mesh(src, labels, wanted, name):
    me=src.data
    if any(len(p.vertices)!=3 for p in me.polygons):raise ValueError('Expected triangulated glTF')
    nv=len(me.vertices);nf=len(me.polygons)
    co=np.empty(nv*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    li=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',li);li=li.reshape(-1,3)
    mask=np.isin(labels[li[:,0]],wanted)
    used,inv=np.unique(li[mask].ravel(),return_inverse=True)
    uv=np.empty(len(me.loops)*2,dtype=np.float32);me.uv_layers.active.data.foreach_get('uv',uv)
    uv=uv.reshape(-1,3,2)[mask].reshape(-1,2)
    out=bpy.data.meshes.new(name)
    out.vertices.add(len(used));out.vertices.foreach_set('co',co[used].ravel())
    out.loops.add(len(inv));out.loops.foreach_set('vertex_index',inv)
    out.polygons.add(int(mask.sum()));out.polygons.foreach_set('loop_start',np.arange(0,len(inv),3,dtype=np.int32));out.polygons.foreach_set('loop_total',np.full(int(mask.sum()),3,dtype=np.int32))
    layer=out.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',uv.ravel())
    out.update();ob=bpy.data.objects.new(name,out);bpy.context.collection.objects.link(ob)
    out.materials.append(src.data.materials[0])
    for p in out.polygons:p.use_smooth=True
    return ob

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def decimate(obj,target):
    original=tri_count(obj)
    if original<=target:return
    activate(obj)
    # Weld glTF seam duplication without discarding the per-loop UV coordinates.
    weld=obj.modifiers.new('WeldSourceSeams','WELD');weld.merge_threshold=.00001
    bpy.ops.object.modifier_apply(modifier=weld.name)
    mod=obj.modifiers.new('BudgetCollapse','DECIMATE');mod.decimate_type='COLLAPSE';mod.ratio=max(.00001,(target-24)/tri_count(obj));mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    actual=tri_count(obj)
    if actual>target:
        mod=obj.modifiers.new('BudgetFinish','DECIMATE');mod.ratio=(target-12)/actual;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)

def apply_scale_origin(obj,dimension,kind):
    if kind=='boat':
        coords=np.array([tuple(v.co) for v in obj.data.vertices],dtype=np.float32)
        cov=np.cov(coords[:,:2].T);_,axes=np.linalg.eigh(cov)
        axis=axes[:,-1];obj.rotation_euler.z=-math.pi/2-math.atan2(axis[1],axis[0])
        activate(obj);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    lo,hi=bounds([obj]);d=hi-lo
    measure=d.z if kind=='tree' else max(d)
    scale=dimension/measure
    center=Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z))
    for v in obj.data.vertices:v.co=(v.co-center)*scale
    # The design-sheet assets present their broad side along Blender +X.
    obj.rotation_euler.z=0 if kind=='boat' else -math.pi/2
    activate(obj);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    obj.data.update()
    return scale

def split_base(obj,cut_height):
    # Retain the source base as its own selectable piece, using coincident cut planes.
    base=obj.copy();base.data=obj.data.copy();base.name=obj.name+'_Base';bpy.context.collection.objects.link(base)
    for target,above in [(obj,True),(base,False)]:
        bm=bmesh.new();bm.from_mesh(target.data)
        result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,cut_height),plane_no=(0,0,1),clear_inner=above,clear_outer=not above)
        # Do not fill the internal horizontal cut: both visible halves share the same seam.
        bm.to_mesh(target.data);bm.free();target.data.update()
    return base

def remove_bottom_faces(obj):
    # Remove only the buried, downward-facing bottom cap; never interior boat surfaces.
    lo,hi=bounds([obj]);threshold=lo.z+(hi.z-lo.z)*.012
    bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
    faces=[f for f in bm.faces if f.normal.z<-.55 and max(v.co.z for v in f.verts)<threshold]
    count=len(faces)
    if faces:bmesh.ops.delete(bm,geom=faces,context='FACES')
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return count

def save_image(img,path):
    img.filepath_raw=str(path);img.file_format='PNG';img.save()
    return dict(path=relative(path),sha256=sha(path),width=img.size[0],height=img.size[1],color_space=img.colorspace_settings.name)

def prepare_materials(spec,folder,source=None,asset_name=None):
    source=source or next(i for i in bpy.data.images if i.size[0]>100)
    asset_name=asset_name or spec['id']
    limit=2048 if spec['id'] in {'tree_gold','boat'} else 1024
    source.scale(limit,limit)
    source.name=asset_name+'_BaseColor'
    texturefolder=folder/'textures';texturefolder.mkdir(parents=True,exist_ok=True)
    textures=[save_image(source,texturefolder/(asset_name+'_BaseColor.png'))]
    pix=np.empty(limit*limit*4,dtype=np.float32);source.pixels.foreach_get(pix);pix=pix.reshape(limit,limit,4)
    r,g,b=pix[:,:,0],pix[:,:,1],pix[:,:,2]
    fruit=(r>.65)&(g>.42)&(b<.20)&(g>b*2.7)&(r>g*.97)&(g>r*.64)
    leaf=(g>r*.88)&(g>b*1.07)&(g>.04)
    materials=[]
    matentries=[]
    for role in (['Bark','LeafVeins','WarmFruit'] if spec['kind']=='tree' else ['Wood' if spec['kind']=='boat' else 'Stone']):
        mat=bpy.data.materials.new(asset_name+'_'+role);mat.use_nodes=True
        bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.86
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=source
        mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        entry=dict(name=mat.name,role=role,base_color_texture=textures[0]['path'],roughness=.86,emission_color=[0,0,0],emission_strength=0)
        if role in {'LeafVeins','WarmFruit'}:
            mask=leaf if role=='LeafVeins' else fruit
            ep=np.zeros_like(pix);ep[:,:,3]=1
            # All actual emitted light is warm amber; underlying leaves remain silver green.
            ep[mask,0]=1;ep[mask,1]=.48;ep[mask,2]=.13
            if role=='LeafVeins':
                # Isolate brighter tips/veins instead of making the entire canopy glow.
                lum=.2126*r+.7152*g+.0722*b
                ep[:,:,:3]*=np.clip((lum-.10)/.35,0,1)[:,:,None]
            emission=bpy.data.images.new(asset_name+'_'+role+'_Emission',width=limit,height=limit,alpha=True)
            emission.colorspace_settings.name='Non-Color';emission.pixels.foreach_set(ep.ravel())
            emission.update();record=save_image(emission,texturefolder/(emission.name+'.png'));textures.append(record)
            et=mat.node_tree.nodes.new('ShaderNodeTexImage');et.image=emission
            mat.node_tree.links.new(et.outputs['Color'],bs.inputs['Emission Color'])
            strength=.22 if role=='LeafVeins' else 1.35;bs.inputs['Emission Strength'].default_value=strength
            entry.update(emission_texture=record['path'],emission_color=[1,.48,.13],emission_strength=strength)
        materials.append(mat);matentries.append(entry)
    return materials,matentries,textures,pix

def bake_color(low,high,size,dimension):
    """Reproject source colour after aggressive reduction instead of stretching its UV atlas."""
    activate(low)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.002,area_weight=.1)
    bpy.ops.object.mode_set(mode='OBJECT')
    target=bpy.data.images.new(low.name+'_RebakedColor',width=size,height=size,alpha=False)
    target.generated_color=(.25,.21,.16,1)
    mat=bpy.data.materials.new(low.name+'_BakeTarget');mat.use_nodes=True
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=target
    mat.node_tree.nodes.active=node;node.select=True
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    low.data.materials.clear();low.data.materials.append(mat)
    for p in low.data.polygons:p.material_index=0
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
    scene.render.bake.use_selected_to_active=True
    scene.render.bake.use_cage=False;scene.render.bake.cage_extrusion=dimension*.009
    scene.render.bake.max_ray_distance=dimension*.045
    scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
    scene.render.bake.margin=5;scene.render.bake.use_clear=False
    high.hide_render=False;high.hide_set(False)
    activate(low);high.select_set(True)
    bpy.ops.object.bake(type='DIFFUSE')
    high.hide_render=True;high.hide_set(True)
    print('ENV_REBAKE_COMPLETE',low.name,size,flush=True)
    return target

def assign_materials(obj,materials,pix,kind):
    obj.data.materials.clear()
    for mat in materials:obj.data.materials.append(mat)
    if kind!='tree':return
    uv=obj.data.uv_layers.active.data;h,w=pix.shape[:2]
    lo,hi=bounds([obj]);height=max(hi.z,.001)
    for p in obj.data.polygons:
        coords=sum((uv[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.loop_indices)
        x=min(w-1,max(0,int(coords.x*w)));y=min(h-1,max(0,int(coords.y*h)))
        r,g,b=pix[y,x,:3]
        z=sum(obj.data.vertices[i].co.z for i in p.vertices)/len(p.vertices)
        if z>height*.18 and r>.65 and g>.42 and b<.20 and g>b*2.7 and r>g*.97 and g>r*.64:p.material_index=2
        elif z>height*.25 and g>r*.88 and g>b*1.07 and g>.04:p.material_index=1
        else:p.material_index=0

def export_fbx(objects,path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE',embed_textures=False)

def process(only=None,main_only=False,variants_only=False,rocks_only=False,fast=False):
    manifest_path=OUT/'asset-manifest.json'
    entries=json.loads(manifest_path.read_text(encoding='utf-8'))['assets'] if manifest_path.exists() else []
    for spec in SPECS:
        if only and spec['id']!=only:continue
        if rocks_only and spec['kind']!='rock':continue
        if main_only and any(e['id']==spec['id'] and any('reprojection' in s for s in e.get('steps',[])) for e in entries):
            print('ENV_MAIN_ALREADY_COMPLETE',spec['id'],flush=True);continue
        source=load(spec);src=meshes()[0];folder=ASSETS/spec['id'];folder.mkdir(parents=True,exist_ok=True)
        comps,labels=components(src,True)
        groups=TREE_GROUPS.get(spec['id'],OTHER_GROUPS.get(spec['id']))
        if groups is None:groups=[(spec['id'],list(range(len(comps))),spec['dimension'],spec['budget'])]
        if main_only:groups=[g for g in groups if g[0]==spec['id']]
        if variants_only:groups=[g for g in groups if g[0]!=spec['id'] and not any(e['id']==g[0] and any('reprojection' in s for s in e.get('steps',[])) for e in entries)]
        # Keep the source hidden and remove it after extracting each group, avoiding repeated imports.
        src.hide_render=True;src.hide_set(True)
        for name,ranks,dimension,budget in groups:
            wanted=[comps[i]['label'] for i in ranks]
            ob=extract_mesh(src,labels,wanted,name)
            before=tri_count(ob);scale=apply_scale_origin(ob,dimension,spec['kind'])
            high=ob.copy();high.data=ob.data.copy();high.name=name+'_BakeSource';bpy.context.collection.objects.link(high)
            high.hide_render=True;high.hide_set(True)
            decimate(ob,budget-160)
            if fast:
                rebaked=next(n.image for n in src.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image).copy()
            else:
                rebaked=bake_color(ob,high,2048 if spec['id'] in {'tree_gold','boat'} else 1024,dimension)
            bpy.data.objects.remove(high,do_unlink=True)
            materials,matentries,textures,pix=prepare_materials(spec,folder,rebaked,name)
            removed=remove_bottom_faces(ob) if spec['kind']!='boat' else 0
            objects=[ob]
            if spec['kind']=='tree':objects.append(split_base(ob,dimension*.047))
            for o in objects:assign_materials(o,materials,pix,spec['kind'])
            # After clipping and base separation, keep the sum within the requested budget.
            current=sum(tri_count(o) for o in objects)
            if current>budget:
                for o in objects:decimate(o,max(32,int(tri_count(o)*((budget-40)/current))))
            targetfolder=folder/name;targetfolder.mkdir(parents=True,exist_ok=True)
            lod0=targetfolder/(name+'_LOD0.fbx');export_fbx(objects,lod0)
            lo,hi=bounds(objects)
            record=dict(id=name,source_id=spec['id'],kind=spec['kind'],source_path=relative(source),source_sha256=sha(source),
                        input_component_ranks=ranks,input_triangles=before,scale_to_metres=scale,
                        dimensions_xyz_blender_metres=list(hi-lo),dimensions_xyz_unity_metres=[hi.x-lo.x,hi.z-lo.z,hi.y-lo.y],
                        pivot='bottom centre of all retained parts; base and trunk share exact world-aligned origin',
                        axis='FBX Y-up, -Z forward; metres; baked space transform',
                        steps=['manual grouping by connected components and three-view source inspection','discard presentation-sheet cutaways and duplicate floating study panels','weld coincident glTF seam vertices while preserving UV loops','uniform physical scale; bottom-centre pivot','QEM collapse decimation','new smart-projected UV atlas; diffuse-colour reprojection from retained high-poly source','separate selectable tree base by horizontal cut; preserve co-located trunk/base seam' if spec['kind']=='tree' else 'preserve all selected visible object geometry','remove only buried downward bottom-cap faces' if spec['kind']!='boat' else 'preserve boat interior and hull bottom','separate bark / leaf veins / amber fruit materials by UV-colour mask' if spec['kind']=='tree' else 'matte source-colour material'],
                        bottom_faces_removed=removed,textures=textures,materials=matentries,
                        lod0=dict(fbx=relative(lod0),sha256=sha(lod0),triangles=sum(tri_count(o) for o in objects),objects=[dict(name=o.name,triangles=tri_count(o)) for o in objects]))
            record['previews']=previews(objects,targetfolder/'previews','processed',640)
            if fast:
                record['steps']=[('retain source UV atlas for low-detail far rock variant' if 'new smart-projected' in step else step) for step in record['steps']]
                record['review']='Far rock variant retains source UVs; inspect its generated previews. Not Unity-import verified.'
            lod1objects=[]
            if spec['kind'] in {'tree','rock'}:
                for o in objects:
                    c=o.copy();c.data=o.data.copy();c.name=o.name+'_LOD1';bpy.context.collection.objects.link(c)
                    decimate(c,max(48,int(tri_count(o)*.4)));lod1objects.append(c)
                lod1=targetfolder/(name+'_LOD1.fbx');export_fbx(lod1objects,lod1)
                record['lod1']=dict(fbx=relative(lod1),sha256=sha(lod1),triangles=sum(tri_count(o) for o in lod1objects),ratio=sum(tri_count(o) for o in lod1objects)/record['lod0']['triangles'])
                for o in lod1objects:o.hide_render=True;o.hide_set(True)
            record['review']='Optimized preview produced; pending human visual review. Not Unity-import verified.'
            entries=[e for e in entries if e['id']!=name]+[record]
            dump(manifest_path,dict(schema_version=1,assets=entries))
            dump(targetfolder/'asset.json',record)
            for o in objects:o.hide_render=True;o.hide_set(True)
            print('ENV_ASSET_COMPLETE',name,record['lod0']['triangles'],flush=True)
        bpy.data.objects.remove(src,do_unlink=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder/(spec['id']+'_processed.blend')))

def verify():
    manifest=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
    checks=[]
    for record in manifest['assets']:
        for level in ['lod0','lod1']:
            if level not in record:continue
            clear();f=ROOT/record[level]['fbx'];bpy.ops.import_scene.fbx(filepath=str(f))
            obs=meshes();lo,hi=bounds(obs);actual=sum(tri_count(o) for o in obs)
            invalid=0;zero_area=0;boundary=0;uv_missing=[];invalid_uv=0
            for o in obs:
                co=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',co)
                invalid+=int((~np.isfinite(co)).sum())
                o.data.calc_loop_triangles();zero_area+=sum(t.area<1e-10 for t in o.data.loop_triangles)
                if not o.data.uv_layers:uv_missing.append(o.name)
                else:
                    uv=np.empty(len(o.data.loops)*2,dtype=np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv)
                    invalid_uv+=int((~np.isfinite(uv)).sum())
                bm=bmesh.new();bm.from_mesh(o.data);boundary+=sum(e.is_boundary for e in bm.edges);bm.free()
            checks.append(dict(id=record['id'],level=level,fbx=relative(f),sha256=sha(f),
                               triangles=actual,expected_triangles=record[level]['triangles'],
                               triangles_match=actual==record[level]['triangles'],
                               materials=sorted(set(m.name for o in obs for m in o.data.materials if m)),
                               bounds_blender=[list(lo),list(hi)],dimensions_blender=list(hi-lo),
                               position_at_bottom_origin=abs(lo.z)<.06,nonfinite_position_components=invalid,
                               nonfinite_uv_components=invalid_uv,meshes_missing_uv=uv_missing,
                               zero_area_triangles_epsilon_1e_10=zero_area,boundary_edges=boundary,
                               boundary_note='Buried bottom caps are intentionally removed; tree/base cut is open at its shared interface. UV seams may be split by FBX. Boundary count is diagnostic, not a closed-manifold claim.'))
    dump(ASSETS/'fbx-roundtrip-verification.json',dict(checks=checks,all_triangle_counts_match=all(c['triangles_match'] for c in checks),all_positions_and_uvs_finite=all(not(c['nonfinite_position_components'] or c['nonfinite_uv_components']) for c in checks),no_missing_uv=all(not c['meshes_missing_uv'] for c in checks),scope='Blender FBX roundtrip only; does not assert every surface repaired, Unity import, collision, or runtime performance'))

def relight(only=None):
    """Tighten gold-fruit classification without repeating geometry reduction or colour baking."""
    path=OUT/'asset-manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    for record in manifest['assets']:
        if record['kind']!='tree' or (only and record['id']!=only):continue
        clear();f=ROOT/record['lod0']['fbx'];bpy.ops.import_scene.fbx(filepath=str(f));obs=meshes()
        for o in obs:o.data.materials.clear()
        for mat in list(bpy.data.materials):bpy.data.materials.remove(mat)
        basepath=ROOT/next(t['path'] for t in record['textures'] if '_BaseColor' in t['path'])
        source=bpy.data.images.load(str(basepath),check_existing=True)
        spec=next(s for s in SPECS if s['id']==record['source_id'])
        mats,entries,textures,pix=prepare_materials(spec,ASSETS/record['source_id'],source,record['id'])
        for o in obs:assign_materials(o,mats,pix,'tree')
        record['material_face_counts']={m.name:sum(1 for o in obs for p in o.data.polygons if o.data.materials[p.material_index]==m) for m in mats}
        export_fbx(obs,f);record['lod0']['sha256']=sha(f)
        record['materials']=entries;record['textures']=textures
        record['previews']=previews(obs,f.parent/'previews','processed',640)
        for o in obs:o.hide_render=True;o.hide_set(True)
        if 'lod1' in record:
            previous=set(meshes());f1=ROOT/record['lod1']['fbx'];bpy.ops.import_scene.fbx(filepath=str(f1));lod1=[o for o in meshes() if o not in previous]
            for o in lod1:assign_materials(o,mats,pix,'tree')
            export_fbx(lod1,f1);record['lod1']['sha256']=sha(f1)
            for o in lod1:o.hide_render=True;o.hide_set(True)
        for o in obs:o.hide_render=False;o.hide_set(False)
        blendpath=f.parent/(record['id']+'_optimized.blend')
        bpy.ops.wm.save_as_mainfile(filepath=str(blendpath))
        record['blend']=relative(blendpath)
        record['steps'].append('tight high-luminance gold mask excludes orange-brown branches from fruit emission')
        dump(f.parent/'asset.json',record)
        dump(path,manifest)
        print('ENV_RELIGHT_COMPLETE',record['id'],record['material_face_counts'],flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['inventory']
    if args[0]=='inventory':inventory(args[1] if len(args)>1 else None)
    elif args[0]=='process':process(args[1] if len(args)>1 else None)
    elif args[0]=='main':process(main_only=True)
    elif args[0]=='variants':process(variants_only=True)
    elif args[0]=='far':process(only=args[1] if len(args)>1 else None,variants_only=True,rocks_only=True,fast=True)
    elif args[0]=='verify':verify()
    elif args[0]=='relight':relight(args[1] if len(args)>1 else None)
    else:raise ValueError(args)
