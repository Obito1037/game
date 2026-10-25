"""Offline controlled lamp surface study. Never writes v1 or Unity Assets.
Modes: --audit, --build [copper_roadlamp|harbor_lantern], --verify.
"""
import bpy, bmesh, json, math, hashlib, sys, re, struct, html
from pathlib import Path
from collections import Counter
from mathutils import Vector, Matrix, Quaternion
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'art/generated/env-v2/lamp-study'
OUT.mkdir(parents=True, exist_ok=True)
IDS = ('copper_roadlamp', 'harbor_lantern')
CANDIDATE = 'candidate-d'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name, data):
    p=OUT/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def source(asset): return ROOT/f'art/generated/env-v1/props/{asset}/{asset}.blend'
def load(asset):
    bpy.ops.wm.open_mainfile(filepath=str(source(asset)))
    for obj in list(bpy.data.objects):
        if obj.type not in ('MESH','EMPTY'): bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1

def snapshot():
    result={}
    for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if obj.type not in ('MESH','EMPTY'): continue
        a={'type':obj.type,'parent':obj.parent.name if obj.parent else None,
           'matrix_world':[list(row) for row in obj.matrix_world],
           'location':list(obj.location),'scale':list(obj.scale)}
        if obj.type=='MESH':
            mesh=obj.data; mesh.calc_loop_triangles()
            a.update(vertices=[list(v.co) for v in mesh.vertices],
                     faces=[list(p.vertices) for p in mesh.polygons],
                     face_material=[p.material_index for p in mesh.polygons],
                     triangles=len(mesh.loop_triangles),
                     materials=[s.material.name if s.material else None for s in obj.material_slots],
                     uv_layers=[u.name for u in mesh.uv_layers],
                     uv0=[list(v.uv) for v in mesh.uv_layers.active.data] if mesh.uv_layers.active else [],
                     world_bounds=[[min((obj.matrix_world@v.co)[i] for v in mesh.vertices) for i in range(3)],
                                   [max((obj.matrix_world@v.co)[i] for v in mesh.vertices) for i in range(3)]])
        result[obj.name]=a
    return result

def audit():
    reports=[]
    for asset in IDS:
        load(asset); snap=snapshot(); write(f'baseline/{asset}-geometry.json',snap)
        mats={}
        for obj in bpy.context.scene.objects:
            if obj.type!='MESH':continue
            for slot in obj.material_slots:
                m=slot.material
                if not m or m.name in mats: continue
                p=m.node_tree.nodes.get('Principled BSDF')
                mats[m.name]={key:list(p.inputs[key].default_value) if hasattr(p.inputs[key].default_value,'__len__') else p.inputs[key].default_value
                              for key in ('Base Color','Metallic','Roughness','Emission Color','Emission Strength','Transmission Weight','IOR')}
        reports.append({'asset':asset,'source':str(source(asset).relative_to(ROOT)),
                        'source_sha256':sha(source(asset)),
                        'fbx_sha256':sha(source(asset).with_suffix('.fbx')),
                        'triangles':sum(x.get('triangles',0) for x in snap.values()),
                        'objects':{k:{kk:vv for kk,vv in v.items() if kk not in ('vertices','faces','face_material')} for k,v in snap.items()},
                        'materials':mats})
    write('baseline/inventory.json',reports)
    print('LAMP_AUDIT',json.dumps(reports,ensure_ascii=False))

def generated_textures():
    """Original periodic surface maps; no external imagery or game-reference pixels."""
    folder=OUT/CANDIDATE/'textures';folder.mkdir(parents=True,exist_ok=True)
    n=512;y,x=np.mgrid[0:n,0:n].astype(np.float64)/n
    rng=np.random.default_rng(417021)
    def field(freqs):
        a=np.zeros_like(x)
        for f,weight in freqs:
            for _ in range(6):
                kx=int(rng.integers(1,f+1));ky=int(rng.integers(-f,f+1))
                a+=weight*np.sin(math.tau*(kx*x+ky*y)+rng.uniform(0,math.tau))/6
        return a
    low=field([(3,1),(8,.35)]);fine=field([(28,1),(67,.4)])
    tarnish=np.clip((low+.12)*1.8,0,1)
    # Oxidation is a restrained thin film, not the large camouflage patches rejected in A.
    patina=np.clip((low-.47)*.3,0,.025)
    rub=.5+.5*field([(7,.9),(19,.3)])
    scratch=np.maximum(0,np.sin(math.tau*(x*83+y*7))-.96)*np.maximum(0,low+.25)
    copper=np.array([.34,.18,.074]);green=np.array([.13,.265,.21])
    # RGB arrays are linear; Blender PNG save performs the sRGB conversion for albedo.
    color=copper[None,None,:]*(1+.025*low[...,None]+.012*fine[...,None])
    color=color*(1-patina[...,None])+green[None,None,:]*patina[...,None]
    color*=1+scratch[...,None]*.12
    rough=np.clip(.56+.02*low+.01*fine,.53,.59)
    metal=np.clip(.62-.06*patina,.60,.62)
    height=np.clip(.5+.12*fine+.035*low+scratch*.3,0,1)
    def save(name,values,noncolor=False):
        image=bpy.data.images.new(name,width=n,height=n,alpha=True,float_buffer=True)
        if noncolor:image.colorspace_settings.name='Non-Color'
        image.pixels.foreach_set(np.asarray(values,dtype=np.float32).reshape(-1))
        image.filepath_raw=str(folder/name);image.file_format='PNG';image.save();image.pack()
        return image
    alpha=np.ones_like(x)
    images={
        'color':save('Lamp_Copper_Albedo.png',np.dstack((color,alpha))),
        'roughness':save('Lamp_Copper_Roughness.png',np.dstack((rough,rough,rough,alpha)),True),
        'height':save('Lamp_Copper_Height.png',np.dstack((height,height,height,alpha)),True),
        # URP metallic map: R metallic, A smoothness. Linear data, never sRGB.
        'metallic_smoothness':save('Lamp_Copper_MetallicSmoothness.png',np.dstack((metal,np.zeros_like(x),np.zeros_like(x),1-rough)),True)
    }
    return images

def material(name,color,metal=0,rough=.5):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal
    p.inputs['Roughness'].default_value=rough
    return m,p

def candidate_materials(images):
    m,p=material('V2_Lamp_AgedCopper',(.48,.26,.11),.7,.46)
    nodes=m.node_tree.nodes;links=m.node_tree.links
    for key,socket in [('color','Base Color'),('roughness','Roughness')]:
        n=nodes.new('ShaderNodeTexImage');n.image=images[key];n.extension='REPEAT'
        links.new(n.outputs['Color'],p.inputs[socket])
    h=nodes.new('ShaderNodeTexImage');h.image=images['height'];h.extension='REPEAT'
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.06;bump.inputs['Distance'].default_value=.00015
    links.new(h.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
    packed=nodes.new('ShaderNodeTexImage');packed.image=images['metallic_smoothness']
    split=nodes.new('ShaderNodeSeparateColor');links.new(packed.outputs['Color'],split.inputs['Color'])
    links.new(split.outputs['Red'],p.inputs['Metallic'])
    worn,p=material('V2_Lamp_RubbedCopper',(.48,.29,.12),.58,.62)
    iron,p=material('V2_Lamp_WeatheredIron',(.067,.083,.080),.58,.53)
    glass,p=material('V2_Lamp_AmberGlass_AlwaysVisible',(.98,.965,.94),0,.06)
    p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.04
    p.inputs['Coat Weight'].default_value=.04;p.inputs['Coat Roughness'].default_value=.20
    glass['UnityContract']='Keep Renderer visible when off. Non-emissive; URP transparent/transmission needs explicit mapping.'
    core,p=material('V2_Lamp_LightFruit_Controlled',(.95,.47,.085),0,.34)
    p.inputs['Subsurface Weight'].default_value=.06;p.inputs['Subsurface Scale'].default_value=.02
    p.inputs['Emission Color'].default_value=(1,.43,.085,1);p.inputs['Emission Strength'].default_value=0
    core['UnityContract']='Only this material emission follows lamp power. Default 0; independent from glass.'
    return {'Copper_Aged':m,'Gold_WornEdges':worn,'Iron_Blackened':iron,'Lantern_AmberCore':glass,'core':core}

def apply_candidate(asset):
    images=generated_textures();mapping=candidate_materials(images)
    for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        old_names=[s.material.name for s in obj.material_slots]
        for slot in obj.material_slots:slot.material=mapping.get(slot.material.name,slot.material)
        mesh=obj.data;uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            matname=old_names[poly.material_index]
            if matname in ('Copper_Aged','Gold_WornEdges','Iron_Blackened'):
                # Planar projection per face, tiled every .42 m. Geometry and its transforms do not move.
                axis=max(range(3),key=lambda i:abs(poly.normal[i]));axes=[i for i in range(3) if i!=axis]
                for li in poly.loop_indices:
                    p=mesh.vertices[mesh.loops[li].vertex_index].co
                    uv.data[li].uv=(p[axes[0]]/.42,p[axes[1]]/.42)
        # Smooth only existing cylindrical sidewalls; keep caps, hood rim and frame edges crisp.
        for poly in mesh.polygons:
            if old_names[poly.material_index]=='Lantern_AmberCore':poly.use_smooth=len(poly.vertices)==4
            # A hood's radial wall is smooth; its thick lip and rear cap remain crisp.
            if obj.name=='LampHead' and old_names[poly.material_index]=='Copper_Aged':
                radial=Vector((poly.center.x,0,poly.center.z))
                dot=poly.normal.dot(radial)
                if dot<-.015:
                    poly.material_index=old_names.index('Gold_WornEdges')
                    poly.use_smooth=True
                elif dot>.015 and len(poly.vertices)==4 and abs(poly.normal.y)<.6:poly.use_smooth=True
    if asset=='harbor_lantern':
        # The v1 glass is a solid cylinder. Preserve all outer vertices, replace its
        # two full caps by 2.5 mm annular rims, and add inward-facing inner walls.
        obj=bpy.data.objects['Structure'];old=obj.data
        verts=[tuple(v.co) for v in old.vertices];faces=[];slots=[];smooth=[];uvfaces=[]
        glass_slot=next(i for i,m in enumerate(old.materials) if m.name=='V2_Lamp_AmberGlass_AlwaysVisible')
        bottom=[];top=[]
        for v in old.vertices:
            if abs(math.hypot(v.co.x,v.co.y)-.12)<1e-5:
                if abs(v.co.z-.13)<1e-5:bottom.append(v.index)
                if abs(v.co.z-.49)<1e-5:top.append(v.index)
        if len(bottom)!=12 or len(top)!=12:raise RuntimeError('Unexpected glass cylinder topology')
        bottom.sort(key=lambda i:math.atan2(verts[i][1],verts[i][0]));top.sort(key=lambda i:math.atan2(verts[i][1],verts[i][0]))
        for p in old.polygons:
            if p.material_index==glass_slot and len(p.vertices)>4:continue
            faces.append(tuple(p.vertices));slots.append(p.material_index);smooth.append(p.use_smooth)
            uvfaces.append([tuple(old.uv_layers.active.data[i].uv) for i in p.loop_indices])
        ib=[];it=[]
        for ring,ids in [(ib,bottom),(it,top)]:
            for i in ids:
                p=Vector(verts[i]);p.x*=.1175/.12;p.y*=.1175/.12;ring.append(len(verts));verts.append(tuple(p))
        for i in range(12):
            j=(i+1)%12
            for face,sm in [((ib[i],it[i],it[j],ib[j]),True),((top[i],top[j],it[j],it[i]),False),((bottom[j],bottom[i],ib[i],ib[j]),False)]:
                faces.append(face);slots.append(glass_slot);smooth.append(sm);uvfaces.append([(0,0),(1,0),(1,1),(0,1)])
        mesh=bpy.data.meshes.new('Harbor_ThinGlassAndPreservedFrame');mesh.from_pydata(verts,[],faces);mesh.update()
        for m in old.materials:mesh.materials.append(m)
        uv=mesh.uv_layers.new(name='UVMap')
        for p,slot,sm,puv in zip(mesh.polygons,slots,smooth,uvfaces):
            p.material_index=slot;p.use_smooth=sm
            for li,value in zip(p.loop_indices,puv):uv.data[li].uv=value
        obj.data=mesh
    target=bpy.data.objects['LampHead' if asset=='copper_roadlamp' else 'Structure']
    loc=(0,-.145,0) if asset=='copper_roadlamp' else (0,0,.31)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.073,location=loc)
    fruit=bpy.context.object;fruit.name='LightFruit_Insert'
    # A single seed-shaped fruit; no stack of glowing primitive spheres.
    for v in fruit.data.vertices:
        q=v.co.z/.073
        v.co.x*=1-.10*q;v.co.y*=1-.10*q;v.co.z*=1.08
    for p in fruit.data.polygons:p.use_smooth=True
    fruit.data.materials.append(mapping['core'])
    bpy.ops.object.select_all(action='DESELECT');target.select_set(True);fruit.select_set(True)
    bpy.context.view_layer.objects.active=target;bpy.ops.object.join()
    if asset=='harbor_lantern':
        # Join two narrow handle links into the existing Structure. Hanging marker
        # and all old handle points stay unchanged. The old arch previously floated.
        extra=[]
        for x in (-.15,.15):
            a=Vector((x,0,.63));b=Vector((x*.88,0,.535));v=b-a
            bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=.012,depth=v.length,location=(a+b)*.5)
            link=bpy.context.object;link.name='Handle_Link';link.rotation_euler=v.to_track_quat('Z','Y').to_euler()
            link.data.materials.append(mapping['Iron_Blackened']);extra.append(link)
        # A restrained dark stem identifies the single round light fruit.
        bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.004,depth=.016,location=(0,0,.395))
        stem=bpy.context.object;stem.name='Fruit_Stem';stem.data.materials.append(mapping['Iron_Blackened']);extra.append(stem)
        bpy.ops.object.select_all(action='DESELECT');target.select_set(True)
        for o in extra:o.select_set(True)
        bpy.context.view_layer.objects.active=target;bpy.ops.object.join()
    # Keep the existing source meshes/names/pivots exactly, new fruit is one extra material slot.
    return mapping

def emission(on,candidate):
    for m in bpy.data.materials:
        if not m.use_nodes:continue
        p=m.node_tree.nodes.get('Principled BSDF')
        if p and m.name in ('Lantern_AmberCore','V2_Lamp_LightFruit_Controlled'):
            p.inputs['Emission Strength'].default_value=2.2 if on else 0
        if p and m.name=='V2_Lamp_AmberGlass_AlwaysVisible':p.inputs['Emission Strength'].default_value=0

def render_setup(asset,night=False,full=False):
    for obj in list(bpy.data.objects):
        if obj.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(obj,do_unlink=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40
    scene.cycles.use_denoising=True;scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=8
    scene.render.threads_mode='FIXED';scene.render.threads=8
    scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
    scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value=(*((.045,.075,.13) if night else (.24,.25,.27)),1)
    bg.inputs['Strength'].default_value=.25 if night else .6
    if asset=='copper_roadlamp':
        target=Vector((0,-.07,-.08));pos=Vector((.80,-1.35,.48));size=1.03
        if full:target=Vector((0,0,-1.75));pos=Vector((4.4,-7,.7));size=4.65
    else:target=Vector((0,0,.38));pos=Vector((.90,-1.45,.82));size=1.02
    bpy.ops.object.camera_add(location=pos);cam=bpy.context.object
    cam.rotation_euler=(target-pos).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=size;scene.camera=cam
    lights=[]
    for idx,(offset,power,sz) in enumerate([((.8,-1.4,1.2),125,1.6),((-.9,-.35,.6),55,1.2),((.3,.9,1.0),145,1.3)]):
        if full:offset=tuple(v*4 for v in offset);power*=16;sz*=4
        bpy.ops.object.light_add(type='AREA',location=target+Vector(offset));light=bpy.context.object
        light.data.energy=power*(.20 if idx==0 else .13) if night else power
        light.data.color=((1,.77,.48) if idx==0 else (.55,.69,1)) if night else (1,1,1)
        light.data.shape='DISK';light.data.size=sz;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
        lights.append({'position':list(light.location),'energy':light.data.energy,'size':sz,'color':list(light.data.color)})
    return {'camera_position':list(pos),'camera_target':list(target),'ortho_size':size,'resolution':[900,900],
            'samples':40,'view':'AgX Medium High Contrast','exposure':0,'night':night,'lights':lights,
            'note':'No compositing/bloom. Studio camera, not gameplay. No gameplay Spot or Point added.'}

def render(asset,variant):
    destination=OUT/variant/asset;destination.mkdir(parents=True,exist_ok=True)
    renders=[]
    for state in ('neutral-off','night-on','night-off'):
        night=state.startswith('night');emission(state=='night-on',variant==CANDIDATE)
        conditions=render_setup(asset,night=night)
        path=destination/(state+'.png');bpy.context.scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({'file':str(path.relative_to(OUT)),**conditions,'emission':2.2 if state=='night-on' else 0})
    if asset=='copper_roadlamp':
        emission(False,variant==CANDIDATE);conditions=render_setup(asset,full=True)
        path=destination/'neutral-full.png';bpy.context.scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
        renders.append({'file':str(path.relative_to(OUT)),**conditions,'emission':0})
    write(f'{variant}/{asset}/render-conditions.json',renders)

def build(asset):
    source_hash=sha(source(asset));load(asset);baseline=snapshot()
    if not (OUT/'baseline'/asset/'render-conditions.json').exists():render(asset,'baseline')
    load(asset);apply_candidate(asset)
    candidate=snapshot();destination=OUT/CANDIDATE/asset;destination.mkdir(parents=True,exist_ok=True)
    checks=[]
    for name,old in baseline.items():
        new=candidate[name]
        checks.append({'object':name,'matrix_unchanged':old['matrix_world']==new['matrix_world'],
                       'parent_unchanged':old['parent']==new['parent'],
                       'original_vertices_prefix_identical':old.get('vertices')==new.get('vertices',[])[:len(old.get('vertices',[]))] if old['type']=='MESH' else True,
                       'original_faces_prefix_identical':old.get('faces')==new.get('faces',[])[:len(old.get('faces',[]))] if old['type']=='MESH' else True})
        if asset=='harbor_lantern' and old['type']=='MESH':
            old_non_glass=[f for f,s in zip(old['faces'],old['face_material']) if old['materials'][s]!='Lantern_AmberCore']
            new_faces=set(tuple(f) for f in new['faces'])
            checks[-1]['original_non_glass_faces_preserved']=all(tuple(f) in new_faces for f in old_non_glass)
            checks[-1]['expected_glass_caps_replaced']=not checks[-1].pop('original_faces_prefix_identical')
    if not all(all(v for k,v in c.items() if k!='object') for c in checks):raise RuntimeError('Original contract changed')
    before=sum(x.get('triangles',0) for x in baseline.values());after=sum(x.get('triangles',0) for x in candidate.values())
    if asset=='copper_roadlamp' and (after-before)*3>1000:raise RuntimeError('Three-lamp triangle increment exceeded')
    emission(False,True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type in ('MESH','EMPTY'):obj.select_set(True)
    fbx=destination/(asset+'_v2_candidate.fbx');blend=destination/(asset+'_v2_candidate.blend')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
                            apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,
                            use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    write(f'{CANDIDATE}/{asset}/geometry.json',candidate)
    write(f'{CANDIDATE}/{asset}/validation.json',{'source_sha256':source_hash,'source_unchanged':source_hash==sha(source(asset)),
          'before_triangles':before,'after_triangles':after,'added_triangles':after-before,'checks':checks,
          'fbx_sha256':sha(fbx),'blend_sha256':sha(blend),'default_emission':0,'Unity_tested':False})
    render(asset,CANDIDATE)
    if source_hash!=sha(source(asset)):raise RuntimeError('Source changed')
    print('LAMP_BUILD_COMPLETE',asset,before,after)

def topology(mesh):
    mesh.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(mesh)
    result={'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
            'boundary_edges':sum(e.is_boundary for e in bm.edges),
            'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
            'degenerate_triangles':sum(t.area<1e-12 for t in mesh.loop_triangles),
            'finite':all(math.isfinite(x) for v in mesh.vertices for x in v.co)}
    bm.free();return result

def max_point_error(source_points,target_points):
    kd=KDTree(len(target_points))
    for i,p in enumerate(target_points):kd.insert(Vector(p),i)
    kd.balance()
    return max(kd.find(Vector(p))[2] for p in source_points)

def verify(asset):
    folder=OUT/CANDIDATE/asset;fbx=folder/(asset+'_v2_candidate.fbx')
    expected=json.loads((folder/'geometry.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(folder/(asset+'_v2_candidate.blend')))
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.data.uv_layers.active:
            expected[obj.name]['uv0']=[list(uv.uv) for uv in obj.data.uv_layers.active.data]
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(fbx))
    observed=snapshot();checks=[]
    for name,old in expected.items():
        new=observed.get(name)
        if new is None:raise RuntimeError('Missing object '+name)
        obj=bpy.data.objects[name]
        item={'object':name,'parent_same':old['parent']==new['parent'],
              'matrix_max_delta':max(abs(old['matrix_world'][i][j]-new['matrix_world'][i][j]) for i in range(4) for j in range(4))}
        if obj.type=='MESH':
            old_world=[tuple(sum(old['matrix_world'][row][j]*v[j] for j in range(3))+old['matrix_world'][row][3] for row in range(3)) for v in old['vertices']]
            new_world=[list(obj.matrix_world@v.co) for v in obj.data.vertices]
            item.update(topology(obj.data));item['triangles_same']=old['triangles']==new['triangles']
            item['materials_same']=old['materials']==new['materials']
            item['world_point_error_bidirectional']=max(max_point_error(old_world,new_world),max_point_error(new_world,old_world))
            if 'uv0' in old:
                item['uv0_loop_count_same']=len(old['uv0'])==len(new['uv0'])
                item['uv0_max_delta']=max(abs(a-b) for uv_a,uv_b in zip(old['uv0'],new['uv0']) for a,b in zip(uv_a,uv_b))
                if not item['uv0_loop_count_same'] or item['uv0_max_delta']>1e-6:raise RuntimeError('FBX UV differs '+name)
            if not item['triangles_same'] or not item['materials_same'] or item['world_point_error_bidirectional']>1e-5:raise RuntimeError('FBX geometry differs '+name)
        if item['matrix_max_delta']>1e-5 or not item['parent_same']:raise RuntimeError('FBX transform differs '+name)
        checks.append(item)
    write(f'{CANDIDATE}/{asset}/fbx-roundtrip.json',{'fresh_process':True,'fbx_sha256':sha(fbx),'checks':checks,'passed':True,'Unity_tested':False})
    bpy.ops.wm.open_mainfile(filepath=str(folder/(asset+'_v2_candidate.blend')))
    report={'mesh_count':sum(o.type=='MESH' for o in bpy.context.scene.objects),
            'light_camera_count':sum(o.type in ('LIGHT','CAMERA') for o in bpy.context.scene.objects),
            'emission_defaults':{m.name:m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value for m in bpy.data.materials if m.name in ('V2_Lamp_LightFruit_Controlled','V2_Lamp_AmberGlass_AlwaysVisible')},
            'packed_images':[{'name':im.name,'size':list(im.size),'packed':im.packed_file is not None,'bytes':len(im.packed_file.data) if im.packed_file else 0} for im in bpy.data.images if im.name.startswith('Lamp_Copper_')]}
    if report['light_camera_count'] or any(report['emission_defaults'].values()) or not all(i['packed'] for i in report['packed_images']):raise RuntimeError('Blend delivery defaults invalid')
    write(f'{CANDIDATE}/{asset}/blend-reopen.json',report)
    specs=[]
    for m in bpy.data.materials:
        if not m.name.startswith('V2_Lamp_'):continue
        p=m.node_tree.nodes.get('Principled BSDF')
        values={key:list(p.inputs[key].default_value) if hasattr(p.inputs[key].default_value,'__len__') else p.inputs[key].default_value
                for key in ('Base Color','Metallic','Roughness','Transmission Weight','IOR','Coat Weight','Coat Roughness','Emission Color','Emission Strength','Subsurface Weight','Subsurface Scale')}
        specs.append({'name':m.name,'principled_defaults':values,
                      'linked_inputs':[s.name for s in p.inputs if s.is_linked],
                      'images':[{'name':n.image.name,'colorspace':n.image.colorspace_settings.name} for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image],
                      'bumps':[{'strength':n.inputs['Strength'].default_value,'distance':n.inputs['Distance'].default_value} for n in m.node_tree.nodes if n.type=='BUMP']})
    write(f'{CANDIDATE}/{asset}/material-specs.json',{'blend_sha256':sha(folder/(asset+'_v2_candidate.blend')),'materials':specs,
          'note':'Defaults on linked inputs do not override their image links. These are Blender parameters, not an automatic URP material conversion.'})
    if asset=='copper_roadlamp':shield_rays()
    print('LAMP_VERIFY_COMPLETE',asset)

def shield_rays():
    obj=bpy.data.objects['LampHead'];mesh=obj.data
    faces=[list(p.vertices) for p in mesh.polygons if 'Glass' not in mesh.materials[p.material_index].name and 'LightFruit' not in mesh.materials[p.material_index].name]
    bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],faces)
    origin=Vector((0,-.29,0));samples=[]
    for angle in (0,13,39,60,75,80,90,110,150,180):
        blocked=0;distances=[]
        for i in range(32):
            phi=math.tau*i/32;t=math.radians(angle)
            direction=Vector((math.sin(t)*math.cos(phi),-math.cos(t),math.sin(t)*math.sin(phi)))
            hit,normal,index,distance=bvh.ray_cast(origin,direction,2)
            if hit is not None:blocked+=1;distances.append(distance)
        samples.append({'half_angle_from_forward_degrees':angle,'directions':32,'blocked_by_metal':blocked,'clear':32-blocked,'hit_distance_range':[min(distances),max(distances)] if distances else None})
    write(f'{CANDIDATE}/copper_roadlamp/shield-ray-study.json',{'origin_blender':list(origin),'Unity_Spot_local':[0,0,.29],
          'samples':samples,'scope':'Offline geometric intersection only; not Unity shadows, measured photometry, or gameplay verification.',
          'wide_half_angle':39,'narrow_half_angle':13,'hood_geometry_unchanged':True})

def prefab_contract():
    path=ROOT/'GameProject/Assets/JieGuang/Environment/Island.prefab';raw=path.read_text(encoding='utf-8')
    blocks=re.split(r'(?m)^--- !u!',raw)[1:];objects={};transforms={};lights={}
    def pairs(value):return {k:float(v) for k,v in re.findall(r'(\w+): ([\d.eE+-]+)',value)}
    for block in blocks:
        header,body=block.split('\n',1);typ,num=header.split(' &');ident=num.split()[0]
        if typ=='1':
            m=re.search(r'(?m)^  m_Name: (.*)$',body)
            if m:objects[ident]=m.group(1)
        elif typ=='4' and 'm_LocalPosition:' in body:
            value={key:pairs(re.search(r'  '+key+r': (.*)',body).group(1)) for key in ('m_LocalPosition','m_LocalRotation','m_LocalScale')}
            value['go']=re.search(r'm_GameObject: \{fileID: (\d+)',body).group(1)
            value['parent']=re.search(r'm_Father: \{fileID: (\d+)',body).group(1);transforms[ident]=value
        elif typ=='108':
            go=re.search(r'm_GameObject: \{fileID: (\d+)',body).group(1)
            lights[go]={key:re.search(r'(?m)^  '+key+r': (.*)$',body).group(1) for key in ('m_Type','m_Intensity','m_Range','m_SpotAngle')}
    cache={}
    def world(key):
        if key in cache:return cache[key]
        t=transforms[key];p=t['m_LocalPosition'];q=t['m_LocalRotation'];s=t['m_LocalScale']
        m=Matrix.LocRotScale(Vector(tuple(p[a] for a in 'xyz')),Quaternion(tuple(q[a] for a in 'wxyz')),Vector(tuple(s[a] for a in 'xyz')))
        cache[key]=(world(t['parent'])@m) if t['parent'] in transforms else m
        return cache[key]
    def fullpath(key):
        t=transforms[key];name=objects.get(t['go'],'?')
        return fullpath(t['parent'])+'/'+name if t['parent'] in transforms else name
    picked=[]
    for ident,t in transforms.items():
        name=objects.get(t['go'],'');path_name=fullpath(ident)
        if 'Anchor_Lamp_' in path_name or 'HarborLantern' in path_name or name=='Anchor_FlagpoleHook':
            w=world(ident)
            picked.append({'name':name,'path':path_name,'local_position':t['m_LocalPosition'],'local_rotation':t['m_LocalRotation'],
                           'local_scale':t['m_LocalScale'],'world_position':list(w.translation),'world_forward':list((w.to_3x3()@Vector((0,0,1))).normalized()),'light':lights.get(t['go'])})
    write('prefab-contract.json',{'source':str(path.relative_to(ROOT)),'sha256':sha(path),'observed_offline':True,
          'spot_count':sum(v['m_Type']=='0' for v in lights.values()),'objects':picked,
          'note':'Parsed serialized prefab local matrices; no Unity Editor or runtime query.'})

def finalize():
    comparisons=[];geometry=[];source_checks=[];files=[]
    baseline=json.loads((OUT/'baseline/inventory.json').read_text(encoding='utf-8'))
    for inv in baseline:
        asset=inv['asset'];directory=OUT/CANDIDATE/asset
        old=json.loads((OUT/'candidate-c'/asset/'geometry.json').read_text(encoding='utf-8'))
        new=json.loads((directory/'geometry.json').read_text(encoding='utf-8'))
        rows=[]
        def face_counter(data):
            # Blender may permute the newly created sphere's polygon order across
            # fresh processes. Compare winding-preserving cyclic face + slot keys.
            def canonical(face):return min(tuple(face[i:]+face[:i]) for i in range(len(face)))
            return Counter((canonical(f),m) for f,m in zip(data['faces'],data['face_material']))
        for name,b in old.items():
            c=new[name]
            row={'object':name,'matrix_identical_to_c':b['matrix_world']==c['matrix_world']}
            if b['type']=='MESH':
                row.update(vertices_identical_to_c=b['vertices']==c['vertices'],oriented_face_material_multiset_identical_to_c=face_counter(b)==face_counter(c),
                           bounds_identical_to_c=b['world_bounds']==c['world_bounds'])
            rows.append(row)
        if not all(all(v for k,v in r.items() if k!='object') for r in rows):raise RuntimeError('D unexpectedly changed C geometry')
        geometry.append({'asset':asset,'checks':rows})
        source_checks.append({'asset':asset,'blend_unchanged':sha(source(asset))==inv['source_sha256'],
                              'fbx_unchanged':sha(source(asset).with_suffix('.fbx'))==inv['fbx_sha256']})
        before=json.loads((OUT/'baseline'/asset/'render-conditions.json').read_text(encoding='utf-8'))
        after=json.loads((directory/'render-conditions.json').read_text(encoding='utf-8'))
        if len(before)!=len(after):raise RuntimeError('Missing controlled pair')
        for b,a in zip(before,after):
            equal={k:v for k,v in b.items() if k!='file'}=={k:v for k,v in a.items() if k!='file'}
            sizes=[list(struct.unpack('>II',(OUT/p['file']).read_bytes()[16:24])) for p in (b,a)]
            if not equal or sizes!=[[900,900],[900,900]]:raise RuntimeError('Controlled conditions differ')
            comparisons.append({'asset':asset,'before':b['file'],'after':a['file'],'conditions_identical':equal,'actual_png_dimensions':sizes})
    write('delivery-verification.json',{'source_unchanged':source_checks,'d_geometry_compared_with_c':geometry,'controlled_pairs':comparisons,
                                      'Unity_or_performance_tested':False})
    for p in sorted((OUT/CANDIDATE).rglob('*')):
        if p.is_file() and p.suffix not in ('.blend1','.log'):
            files.append({'path':str(p.relative_to(OUT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)})
    write('manifest.json',{'asset_family':'A05-A07 controlled surface/core study','current_offline_candidate':CANDIDATE,
          'root_review':'Roadlamp D neutral/on/off reviewed; accepted as offline material candidate only. Harbor D pending independent root review.',
          'script':str(Path(__file__).relative_to(ROOT)).replace('\\','/'),'script_sha256':sha(__file__),
          'source_inventory':'baseline/inventory.json','interface_audit':'INTERFACE-AUDIT.zh-CN.md',
          'triangles':{'roadlamp_each':830,'three_roadlamps':2490,'harbor_lantern':788,'three_roads_added':672,'harbor_added':352},
          'default_emission':0,'Unity_imported':False,'gameplay_connected':False,'files':files,
          'history':{'a':'rejected: large patina patches','b':'superseded: thick glass and floating bail','c':'root rejected material: blotches and liquid-like interior reflection; geometry kept in d'}})
    chunks=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>借光岛 · 铜灯离线对照</title>',
      '<style>body{margin:0;background:#101a24;color:#eee8dd;font:16px/1.7 system-ui,sans-serif}main{max-width:1350px;margin:auto;padding:32px}h1,h2{color:#edca91}a{color:#9ccee7}p{max-width:1000px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:24px}figure{margin:0;background:#1a2936;border:1px solid #3b4853;border-radius:12px;overflow:hidden}img{width:100%;height:auto;display:block}figcaption{padding:9px 16px}.note{border-left:4px solid #cd9960;padding:10px 16px;background:#26313c}details{margin-top:32px}code{color:#edca91}@media(max-width:650px){main{padding:14px}.pair{gap:8px}figcaption{padding:8px;font-size:12px}}</style><main>',
      '<h1>铜路灯与港灯 · d 离线材质候选</h1><p class="note">这是 Blender 棚拍对照，不是主场景截图。root 已审 d 路灯三图，认可表面改善；仍为简化光芯，未宣布最终质感达标。港灯采用同材质，待独立审图。没有导入 Unity 或修改剧情。</p>',
      '<p><a href="HANDOFF.zh-CN.md">完整交接</a> · <a href="INTERFACE-AUDIT.zh-CN.md">真实代码/Prefab 接口审计</a> · <a href="manifest.json">文件与 SHA256</a> · <a href="delivery-verification.json">受控条件与几何复核</a></p>',
      '<p>每对图镜头、900×900 分辨率、曝光、棚拍灯光完全相同。无 Bloom。neutral/off 的自发光均为 0；on 旧/新都为 2.2，但发光面积不同，不是等流明测试。旧 off 图人为关闭了材质自发光，不能代表现有游戏代码已修好。</p>']
    labels={'neutral-off':'中性光 · 未点亮','night-on':'夜间 · 点亮','night-off':'夜间 · 熄灭，保留玻璃与框架','neutral-full':'中性光 · 全柱'}
    for asset in IDS:
        chunks.append('<h2>'+('三灯共用铜路灯' if asset=='copper_roadlamp' else '旗杆港灯')+'</h2>')
        for pair in [p for p in comparisons if p['asset']==asset]:
            state=Path(pair['after']).stem
            chunks.append('<h3>'+labels[state]+'</h3><div class="pair">')
            for side,label in [('before','v1 原几何/材质'),('after','d 候选')]:
                path=pair[side].replace('\\','/')
                chunks.append('<figure><a href="'+path+'"><img loading="lazy" src="'+path+'" alt="'+html.escape(label+' '+labels[state])+'"></a><figcaption>'+label+'</figcaption></figure>')
            chunks.append('</div>')
    chunks+=['<h2>接口仍待接入</h2><p>三盏原 Spot、灯头转轴、原碰撞、港灯挂点均不改变。新光果在材质槽 3，默认 emission 0；玻璃在槽 1 始终无自发光。真实 LampPost 只在灰盒绑定 bulb，MaterialKit.SetEmission 只改槽 0，港灯剧情目前只控 Light。Claude 必须按实例、按槽补齐亮灭控制。</p>',
      '<p>路灯每盏 830 tris，三灯增加 672；港灯 788 tris，增加 352。d 与 c 几何逐点一致。弱折射 IOR 1.04 是展示近似；Blender Transmission 不会自动成为 URP 同效果玻璃，需验证透明排序/高光/阴影。没有帧率或主游戏效果通过结论。</p>',
      '<details><summary>历史候选（不推荐接入）</summary><p>a 被代理自审拒绝；c 被 root 因明显花斑和液体般内反射拒绝。保留全过程用于解释取舍。</p>',
      '<div class="pair"><figure><img loading="lazy" src="candidate-c/copper_roadlamp/night-on.png" alt="c 路灯拒绝版本"><figcaption>c：不推荐的反射/斑纹</figcaption></figure><figure><img loading="lazy" src="candidate-a/copper_roadlamp/neutral-off.png" alt="a 路灯拒绝版本"><figcaption>a：过大的铜锈斑块</figcaption></figure></div></details></main></html>']
    page=''.join(chunks)
    for ref in re.findall(r'(?:src|href)="([^"]+)"',page):
        if not (OUT/ref).exists():raise RuntimeError('Broken gallery link '+ref)
    (OUT/'REVIEW.html').write_text(page,encoding='utf-8')
    print('LAMP_DELIVERY_COMPLETE',len(files),'files',len(comparisons),'controlled pairs')

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['--audit']
    if '--audit' in args:audit()
    elif '--build' in args:
        for asset in [a for a in args if a in IDS] or IDS:build(asset)
    elif '--verify' in args:
        for asset in [a for a in args if a in IDS] or IDS:verify(asset)
        prefab_contract()
    elif '--finalize' in args:finalize()
