"""Replace only v6's sleeve ring waves with bone-anchored local elbow folds.

Frozen v6 supplies every object, material, weight, UV and non-sleeve vertex.
The unwrinkled sleeve cage is recovered from frozen v5 using the identical
one-level SIMPLE sampling; it is checked against v6 topology and weights before
coordinates are replaced. Nothing is written to old assets or Unity.
Blender 4.5 LTS --background --python-exit-code 1 --python this.py -- --render
"""
import bpy,json,math,hashlib,sys,array
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v6/traveler.blend'
CAGE_SOURCE=ROOT/'art/generated/character-v5/traveler.blend'
OUT=ROOT/'art/generated/character-v7'
OUT.mkdir(parents=True,exist_ok=True)
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TARGETS=('Sleeve_L','Sleeve_R')

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def file_sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def matrix(m): return [list(row) for row in m]
def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a))); return t*t*(3-2*t)
def tri_count(obj):
    obj.data.calc_loop_triangles(); return len(obj.data.loop_triangles)

def weight_values(obj):
    return [[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in obj.data.vertices]

def material_state(mat):
    nodes=[]
    for node in mat.node_tree.nodes:
        inputs=[]
        for socket in node.inputs:
            if not hasattr(socket,'default_value'): continue
            value=socket.default_value
            if isinstance(value,(str,int,float,bool)): pass
            else:
                try: value=list(value)
                except TypeError: value=str(value)
            inputs.append((socket.name,socket.identifier,value))
        nodes.append({'name':node.name,'type':node.bl_idname,'inputs':inputs,
                      'layer_name':getattr(node,'layer_name',None),
                      'blend_type':getattr(node,'blend_type',None),
                      'image':getattr(getattr(node,'image',None),'name',None)})
    return {'diffuse':list(mat.diffuse_color),'roughness':mat.roughness,'metallic':mat.metallic,
            'nodes':nodes,'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in mat.node_tree.links)}

def mesh_state(obj):
    me=obj.data
    return {'coordinates':[list(v.co) for v in me.vertices],
            'topology':{'polygons':[list(p.vertices) for p in me.polygons],
                        'edges':[list(e.vertices) for e in me.edges],
                        'materials':[p.material_index for p in me.polygons],
                        'smooth':[p.use_smooth for p in me.polygons]},
            'normals':[list(n.vector) for n in me.corner_normals],
            'uv':{a.name:[list(d.uv) for d in a.data] for a in me.uv_layers},
            'colors':{a.name:{'domain':a.domain,'type':a.data_type,'values':[list(d.color) for d in a.data]} for a in me.color_attributes},
            'weights':weight_values(obj),
            'material_names':[m.name for m in me.materials]}

def object_contract(root):
    result={}
    for obj in [root]+list(root.children_recursive):
        result[obj.name]={'type':obj.type,'parent':obj.parent.name if obj.parent else None,
                         'parent_type':obj.parent_type,'parent_bone':obj.parent_bone,
                         'basis':matrix(obj.matrix_basis),'parent_inverse':matrix(obj.matrix_parent_inverse),
                         'modifiers':[(m.name,m.type,getattr(getattr(m,'object',None),'name',None),
                                       getattr(m,'use_deform_preserve_volume',None)) for m in obj.modifiers]}
        if obj.type=='ARMATURE':
            result[obj.name]['bones']={b.name:{'matrix_local':matrix(b.matrix_local),'parent':b.parent.name if b.parent else None,
                                              'pose_basis':matrix(obj.pose.bones[b.name].matrix_basis)} for b in obj.data.bones}
    return result

def recover_sleeve_cages():
    bpy.ops.wm.open_mainfile(filepath=str(CAGE_SOURCE)); result={}
    for name in TARGETS:
        obj=bpy.data.objects[name]; bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Recover exact v6 SIMPLE sleeve sampling','SUBSURF')
        mod.subdivision_type='SIMPLE'; mod.levels=1
        bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        result[name]={'coordinates':[tuple(obj.matrix_world@v.co) for v in obj.data.vertices],
                      'polygons':[list(p.vertices) for p in obj.data.polygons],
                      'weights':weight_values(obj),'matrix_world':matrix(obj.matrix_world)}
    return result

def nearest_on_segment(p,a,b):
    ab=b-a; t=max(0.,min(1.,(p-a).dot(ab)/ab.length_squared))
    return a+ab*t

def elbow_fold(p,h,e,w,side):
    # Coordinates are the final Blender world metres of the real skeleton.
    axis=(h-w).normalized()
    a=nearest_on_segment(p,h,e); b=nearest_on_segment(p,e,w)
    center=a if (p-a).length_squared<(p-b).length_squared else b
    radial=p-center
    if radial.length<.0001: return p.copy(),{'delta':0.,'u':0.,'v':0.,'mask':0.}
    radial.normalize()
    front=Vector((0,-1,0)); front=(front-axis*front.dot(axis)).normalized()
    tangent=axis.cross(front).normalized()
    # An anatomically mirrored lateral coordinate makes the pair of folds
    # similar in construction, with intentionally unequal lengths/amplitudes.
    if side=='L': tangent=-tangent
    u=(p-e).dot(axis); v=(p-center).dot(tangent)
    mask=smooth(.25,.80,radial.dot(front))
    axial_window=1-smooth(.055,.070,abs(u))
    offset=-.004 if side=='L' else 0.
    specs=[(.007+offset,.18,.040,.007,.0011 if side=='L' else .0014),
           (-.019+offset,-.08,.027,.010,.0006 if side=='L' else .0008)]
    delta=0.
    for anchor,slope,half_length,width,amplitude in specs:
        lateral=max(0.,1-(v/half_length)**2)**2 if abs(v)<half_length else 0.
        d=u-(anchor+slope*v)
        profile=math.exp(-(d/width)**2)-.35*math.exp(-((d+1.6*width)/(1.3*width))**2)
        delta+=amplitude*lateral*profile
    delta*=mask*axial_window
    assert abs(delta)<.002
    return p+radial*delta,{'delta':delta,'u':u,'v':v,'mask':mask}

def build():
    source_hash=file_sha(SOURCE); cage_hash=file_sha(CAGE_SOURCE)
    cages=recover_sleeve_cages()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); root=bpy.data.objects['TravelerRoot']
    meshes={o.name:o for o in root.children_recursive if o.type=='MESH'}
    before={name:mesh_state(o) for name,o in meshes.items()}
    contract_before=object_contract(root)
    material_names=sorted({m.name for o in meshes.values() for m in o.data.materials})
    materials_before={name:material_state(bpy.data.materials[name]) for name in material_names}
    changed=[]
    for name in TARGETS:
        obj=meshes[name]; cage=cages[name]
        assert before[name]['topology']['polygons']==cage['polygons'],name+' topology differs from recovered cage'
        assert before[name]['weights']==cage['weights'],name+' weights differ from recovered cage'
        assert matrix(obj.matrix_world)==cage['matrix_world'],name+' transform differs from recovered cage'
        side=name[-1]; rig=bpy.data.objects['Arm_'+side+'_SkinRig']
        upper=rig.data.bones['UpperArm_'+side]; elbow=rig.data.bones['Elbow_'+side]
        h=rig.matrix_world@upper.head_local; e=rig.matrix_world@elbow.head_local; w=rig.matrix_world@elbow.tail_local
        inverse=obj.matrix_world.inverted(); max_vs_cage=0.; max_vs_v6=0.; active=[]
        for vertex,position in zip(obj.data.vertices,cage['coordinates']):
            p=Vector(position); original=obj.matrix_world@vertex.co
            point,detail=elbow_fold(p,h,e,w,side)
            max_vs_cage=max(max_vs_cage,(point-p).length)
            max_vs_v6=max(max_vs_v6,(point-original).length)
            if abs(detail['delta'])>1e-7: active.append(detail)
            vertex.co=inverse@point
        obj.data.update()
        changed.append({'mesh':name,'real_elbow_world':list(e),'vertices':len(obj.data.vertices),
                        'max_new_fold_displacement_from_plain_cage_m':max_vs_cage,
                        'max_displacement_vs_v6_m':max_vs_v6,'active_fold_vertices':len(active),
                        'active_axial_range_m':[min(v['u'] for v in active),max(v['u'] for v in active)],
                        'active_lateral_range_m':[min(v['v'] for v in active),max(v['v'] for v in active)],
                        'min_active_front_mask':min(v['mask'] for v in active)})
    bpy.context.view_layer.update()
    after={name:mesh_state(o) for name,o in meshes.items()}
    unchanged=[]; target_rows=[]
    for name in meshes:
        if name not in TARGETS:
            assert before[name]==after[name],name+' protected mesh changed'
            unchanged.append({'mesh':name,'before_sha256':digest(before[name]),'after_sha256':digest(after[name]),'exact_match':True})
        else:
            keys=['topology','uv','colors','weights','material_names']
            a={k:before[name][k] for k in keys}; b={k:after[name][k] for k in keys}
            assert a==b,name+' sleeve non-position data changed'
            target_rows.append({'mesh':name,'protected_channels':keys,'before_sha256':digest(a),'after_sha256':digest(b),'exact_match':True})
    assert contract_before==object_contract(root),'object/bone/attachment contract changed'
    assert materials_before=={name:material_state(bpy.data.materials[name]) for name in material_names},'material graph changed'
    triangles=sum(tri_count(o) for o in meshes.values())
    skinned=sum(any(m.type=='ARMATURE' for m in o.modifiers) for o in meshes.values())
    assert triangles==75862 and len(meshes)==62 and skinned==28 and len(material_names)==29
    fingerprint={'passed':True,'frozen_source':str(SOURCE.relative_to(ROOT)),'frozen_source_sha256':source_hash,
                 'recovered_plain_cage_source':str(CAGE_SOURCE.relative_to(ROOT)),'plain_cage_source_sha256':cage_hash,
                 'non_target_meshes':unchanged,'sleeve_protected_channels':target_rows,
                 'object_bone_attachment_fingerprint':digest(contract_before),
                 'all_object_bone_attachment_data_exact_match':True,
                 'material_graph_fingerprint':digest(materials_before),'all_material_graphs_exact_match':True,
                 'changed_sleeve_geometry':changed,
                 'scope':'Exact in-memory float/data comparison against loaded frozen v6, including mesh normals/UV/colors/weights and all bone/object transforms. Only Sleeve_L/R coordinates and derived normals may differ.'}
    (OUT/'v6-preservation-verification.json').write_text(json.dumps(fingerprint,indent=2),encoding='utf-8')
    character=[root]+list(root.children_recursive)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in character: obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    saved=[]
    for name in material_names:
        material=bpy.data.materials[name]; bsdf=material.node_tree.nodes.get('Principled BSDF')
        for link in list(bsdf.inputs['Base Color'].links):
            saved.append((material,link.from_socket,bsdf.inputs['Base Color'])); material.node_tree.links.remove(link)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,
        object_types={'MESH','EMPTY','ARMATURE'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
        use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',
        use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,
        primary_bone_axis='Y',secondary_bone_axis='X',colors_type='LINEAR',path_mode='COPY',embed_textures=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'traveler.glb'),export_format='GLB',
        use_selection=True,export_yup=True,export_apply=False,export_materials='EXPORT',
        export_extras=True,export_skins=True,export_animations=False,
        export_vertex_color='ACTIVE',export_all_vertex_colors=True)
    for material,a,b in saved: material.node_tree.links.new(a,b)
    assert materials_before=={name:material_state(bpy.data.materials[name]) for name in material_names}
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))
    manifest={'version':7,'source':str(SOURCE.relative_to(ROOT)),'source_sha256':source_hash,
              'source_script_sha256':file_sha(Path(__file__)),
              'triangles':triangles,'mesh_renderers':62,'skinned_meshes':28,'armatures':4,'bones':12,
              'material_names':material_names,'material_count':29,'target_meshes':list(TARGETS),
              'changes':'Remove v6 whole-circumference periodic sleeve waves; two finite, unequal open elbow folds anchored to actual bind elbow, no sinusoidal displacement.',
              'preservation_evidence':'v6-preservation-verification.json',
              'sha256':{p.name:file_sha(p) for p in [OUT/'traveler.blend',OUT/'traveler.fbx',OUT/'traveler.glb']}}
    (OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    assert file_sha(SOURCE)==source_hash and file_sha(CAGE_SOURCE)==cage_hash
    print('V7_EXPORTED '+json.dumps({'triangles':triangles,'protected_meshes':len(unchanged),'changed':changed}),flush=True)

def render():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.device='CPU'
    scene.render.threads_mode='FIXED'; scene.render.threads=4; scene.cycles.samples=8
    scene.cycles.use_denoising=True; scene.render.resolution_x=512; scene.render.resolution_y=512
    scene.render.resolution_percentage=100
    camera=bpy.data.objects['PREVIEW_Camera']; scene.camera=camera
    for name,location,target,scale in [
        ('render-neutral.png',(1.45,-4.5,1.5),(0,0,.66),1.60),
        ('render-lantern-side.png',(3.8,-2.3,1.35),(0,0,.82),1.18),
        ('render-back.png',(1.45,4.5,1.5),(0,0,.66),1.60)]:
        camera.location=location; camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type='ORTHO'; camera.data.ortho_scale=scale
        scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)

if '--render-only' in ARGS: render()
else:
    build()
    if '--render' in ARGS: render()
