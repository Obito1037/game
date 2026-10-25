"""Non-destructive v2 grandma-house candidate; no Unity project writes.

Blender 4.5 --background --factory-startup --python art/blender/env_v2_props.py
"""
import bpy, bmesh, json, hashlib, math, random, sys, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/env-v1/props/abode_grandma/abode_grandma.blend'
META=ROOT/'art/generated/env-v1/props/abode_grandma/asset.json'
OUT=ROOT/'art/generated/env-v2/props/abode_grandma'
OUT.mkdir(parents=True,exist_ok=True)
RNG=random.Random(6304)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(name,color,rough=.72,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    return m
def mesh(name,verts,faces,m):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(m);return o
def box(name,loc,dim,m,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
    if bevel:
        mod=o.modifiers.new('Hand softened edges','BEVEL');mod.width=bevel;mod.segments=1
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def cylinder(name,loc,rad,depth,m,n=8,rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=rad,depth=depth,location=loc)
    o=bpy.context.object;o.name=name;o.data.materials.append(m)
    if rot:o.rotation_euler=rot
    return o
def beam(name,a,b,width,m,rect=False):
    a,b=Vector(a),Vector(b)
    o=box(name,(a+b)*.5,(width,width,(b-a).length),m,.008) if rect else cylinder(name,(a+b)*.5,width/2,(b-a).length,m)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def bounds():
    pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
    return {'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
def markers():
    return {o.name:{'location':list(o.matrix_world.translation),'quaternion':list(o.matrix_world.to_quaternion())}
            for o in bpy.context.scene.objects if o.type=='EMPTY' and o.name.startswith('Marker_')}
def triangles():
    n=0
    for o in bpy.context.scene.objects:
        if o.type=='MESH':o.data.calc_loop_triangles();n+=len(o.data.loop_triangles)
    return n
def apply_normals_uv():
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':continue
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
        bpy.ops.object.mode_set(mode='OBJECT')

VIEWS={
 'front':{'camera':(7,-10,6),'look':(0,-.1,1.85),'scale':7.5},
 'side':{'camera':(-8,-7,5.0),'look':(0,0,1.8),'scale':7.4},
 'window':{'camera':(3.2,-7.3,3.0),'look':(.45,-1.1,1.9),'scale':5.25},
}
def render_set(prefix):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    sc.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Neutral studio audit');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.25,.28,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;sc.world=world
    lights=[]
    for pos,power,size in [((2,-5,8),1350,5),((-5,-2,4),650,4),((1,4,5),800,4)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size
        o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
    bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO'
    for name,view in VIEWS.items():
        cam.location=view['camera'];cam.rotation_euler=(Vector(view['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']
        sc.render.filepath=str(OUT/f'{prefix}-{name}.png');bpy.ops.render.render(write_still=True)
    for o in lights+[cam]:bpy.data.objects.remove(o,do_unlink=True)

# Surface pass is deliberately separate from geometry construction. It always
# starts from the frozen, previously reviewed 11,925-triangle candidate.
SURFACE_PRESETS={
 'Whitewashed':{'tint':[1.0,.96,.86],'roughness':.78},
 'Weathered':{'tint':[.88,.82,.70],'roughness':.82},
 'Honey':{'tint':[.46,.31,.18],'roughness':.72},
 'DarkBeam':{'tint':[.25,.17,.10],'roughness':.80},
}
SURFACE_MAP={
 'V2_WhitewashedWood_0':'Weathered','V2_WhitewashedWood_1':'Whitewashed',
 'V2_WhitewashedWood_2':'Whitewashed','V2_WhitewashedWood_3':'Weathered',
 'V2_OldTimber_0':'DarkBeam','V2_OldTimber_1':'Honey','V2_OldTimber_2':'Honey',
 'Wall_WarmIvory':'Whitewashed','Wall_LightTimber':'Weathered',
 'Wood_Honey':'Honey','Wood_Endgrain':'Honey','Wood_DarkBeams':'DarkBeam',
}
def geometry_hash(exclude=()):
    payload=[]
    for o in sorted((o for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in exclude),key=lambda o:o.name):
        payload.append({'name':o.name,'matrix':[list(r) for r in o.matrix_world],
                        'vertices':[list(v.co) for v in o.data.vertices],
                        'polygons':[list(p.vertices) for p in o.data.polygons]})
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

def metric_wood_uv():
    """Assign UVs on real connected wood pieces, without changing topology.

    The supplied wood image's grain runs along V. Each connected beam/plank
    has a principal long axis; side faces project that axis into their plane.
    A shared 4.9 m V period keeps all pieces inside [0.04,0.96], rather than
    hiding the measured image top/bottom seam behind repeated long boards.
    """
    import numpy as np
    records=[];total_faces=0;aligned_faces=0;worst_alignment=1.;vmin=1.;vmax=0.
    U_METRES=1.;V_METRES=4.9
    for o in sorted((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:o.name):
        d=o.data;uv=d.uv_layers.active or d.uv_layers.new(name='UVMap')
        adjacency=[set() for _ in d.vertices]
        for e in d.edges:
            a,b=e.vertices;adjacency[a].add(b);adjacency[b].add(a)
        pending=set(range(len(d.vertices)));components=[]
        while pending:
            seed=min(pending);pending.remove(seed);stack=[seed];ids=[]
            while stack:
                i=stack.pop();ids.append(i)
                for j in adjacency[i]:
                    if j in pending:pending.remove(j);stack.append(j)
            components.append(ids)
        by_vertex={v:i for i,ids in enumerate(components) for v in ids}
        polys=[[] for _ in components]
        for p in d.polygons:polys[by_vertex[p.vertices[0]]].append(p)
        for ci,ids in enumerate(components):
            faces=[p for p in polys[ci] if d.materials[p.material_index] and d.materials[p.material_index].name in SURFACE_MAP]
            if not faces:continue
            points=np.array([d.vertices[i].co[:] for i in ids],dtype=float)
            center=points.mean(axis=0);extent=np.ptp(points,axis=0)
            eigenvalues,eigenvectors=np.linalg.eigh(np.cov((points-center).T))
            grain=Vector(eigenvectors[:,int(np.argmax(eigenvalues))].tolist()).normalized()
            # Underlying wall shells/gables are panel assemblies: use horizontal
            # boards, even when the entire joined wall is taller than wide.
            names={d.materials[p.material_index].name for p in faces}
            if any(n.startswith('Wall_') for n in names):
                grain=Vector((0,1,0) if extent[0]<extent[1]*.25 else (1,0,0))
            largest=max(range(3),key=lambda a:abs(grain[a]))
            if grain[largest]<0:grain=-grain
            local_rng=random.Random(int(hashlib.sha256((o.name+':'+str(ci)).encode()).hexdigest()[:12],16))
            projections=[grain.dot(d.vertices[i].co) for i in ids]
            span=max(projections)-min(projections)
            if span>4.45:raise RuntimeError('Wood piece exceeds safe V atlas interval: '+o.name)
            offset=.04+local_rng.random()*max(0,.92-span/V_METRES)
            uoffset=local_rng.uniform(.03,.94)
            ring=(o.name=='Structure' and names=={'Wood_Endgrain'} and extent[0]>.9 and extent[2]>.9 and extent[1]<.3)
            before=[list(uv.data[l].uv) for p in faces for l in p.loop_indices]
            for p in faces:
                normal=p.normal.normalized();projected=grain-normal*grain.dot(normal)
                endgrain=projected.length<.18
                if not endgrain:
                    vg=projected.normalized();ug=normal.cross(vg).normalized()
                    # All boards and beam side faces map their physical grain to V.
                    alignment=abs(vg.dot(projected.normalized()));worst_alignment=min(worst_alignment,alignment);aligned_faces+=1
                else:
                    ug=Vector(eigenvectors[:,0].tolist()).normalized();vg=normal.cross(ug).normalized()
                for li in p.loop_indices:
                    q=d.vertices[d.loops[li].vertex_index].co
                    if ring:
                        dx=q.x-float(center[0]);dz=q.z-float(center[2]);angle=math.atan2(dz,dx)
                        # Bent wood frame: grain follows circumference, 0.08..0.92.
                        uu=(math.hypot(dx,dz)-.59)/U_METRES+uoffset
                        vv=.08+(angle+math.pi)/(2*math.pi)*.84
                    elif endgrain:
                        uu=ug.dot(q-Vector(center.tolist()))/U_METRES+uoffset
                        vv=vg.dot(q-Vector(center.tolist()))/V_METRES+.50
                    else:
                        uu=ug.dot(q)/U_METRES+uoffset
                        vv=(grain.dot(q)-min(projections))/V_METRES+offset
                    uv.data[li].uv=(uu,vv);vmin=min(vmin,vv);vmax=max(vmax,vv)
                total_faces+=1
            after=[list(uv.data[l].uv) for p in faces for l in p.loop_indices]
            records.append({'object':o.name,'component':ci,'wood_faces':len(faces),'materials':sorted(names),
                            'grain_local_axis':list(grain),'grain_span_metres':span,'method':'bent_round_frame' if ring else 'metric_component_axis',
                            'before_uv_range':[[min(q[a] for q in before),max(q[a] for q in before)] for a in range(2)],
                            'after_uv_range':[[min(q[a] for q in after),max(q[a] for q in after)] for a in range(2)],
                            'uv_changed':before!=after})
        d.update()
    return {'u_repeat_metres':U_METRES,'v_repeat_metres':V_METRES,'wood_components':len(records),
            'wood_faces':total_faces,'long_side_faces':aligned_faces,'minimum_projected_grain_dot_v':worst_alignment,
            'v_range':[vmin,vmax],'components':records,
            'limitations':['Round frame uses angular V with one intentional lower-frame seam; it is not endgrain texture.',
                          'End caps use the same wood image in a planar projection; dedicated cut-end texture is not supplied.',
                          'The long-axis 4.9m scale deliberately trades some natural grain aspect for avoiding the source V wrap seam.']}

def surface_refinement():
    frozen=OUT/'archive-flat-materials-20261022'
    source=frozen/'abode_grandma_v2_candidate.blend'
    if not source.is_file():raise RuntimeError('Create frozen candidate backup first')
    texture=ROOT/'art/generated/env-v2/textures/wood_albedo_v1.png'
    before_manifest=json.loads((frozen/'manifest.json').read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.view_layer.update()
    before_geo=geometry_hash();before_bounds=bounds();before_markers=markers();before_tris=triangles()
    # These are existing renders of exactly this frozen geometry and VIEWS.
    for view in VIEWS:shutil.copy2(frozen/f'after-{view}.png',OUT/f'material-before-{view}.png')
    uv_report=metric_wood_uv()
    image=bpy.data.images.load(str(texture),check_existing=True);image.colorspace_settings.name='sRGB'
    changed=[]
    for m in bpy.data.materials:
        if m.name not in SURFACE_MAP:continue
        preset=SURFACE_PRESETS[SURFACE_MAP[m.name]];m.use_nodes=True;nodes=m.node_tree.nodes;links=m.node_tree.links
        nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled')
        tex=nodes.new('ShaderNodeTexImage');tex.name='OriginalWoodAlbedo';tex.image=image;tex.extension='REPEAT';tex.interpolation='Linear'
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UVMap';links.new(uv.outputs['UV'],tex.inputs['Vector'])
        multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
        multiply.inputs[2].default_value=(*preset['tint'],1);links.new(tex.outputs['Color'],multiply.inputs[1])
        links.new(multiply.outputs[0],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=preset['roughness']
        links.new(bs.outputs[0],out.inputs[0]);m.diffuse_color=(*preset['tint'],1)
        changed.append({'source_name':m.name,'shared_material':'HouseWood_'+SURFACE_MAP[m.name],**preset})
    after_geo=geometry_hash();after_tris=triangles();after_bounds=bounds();after_markers=markers()
    checks=[{'name':'surface_pass_geometry_exact','passed':after_geo==before_geo,'detail':after_geo},
            {'name':'surface_pass_markers_exact','passed':after_markers==before_markers},
            {'name':'surface_pass_bounds_exact','passed':after_bounds==before_bounds},
            {'name':'surface_pass_triangle_count_exact','passed':after_tris==before_tris and after_tris<=12100,'detail':after_tris},
            {'name':'wood_uv_components_changed','passed':all(c['uv_changed'] for c in uv_report['components'])},
            {'name':'wood_v_does_not_wrap_image_edge','passed':uv_report['v_range'][0]>=.039 and uv_report['v_range'][1]<=.961,'detail':uv_report['v_range']},
            {'name':'texture_sha_unchanged','passed':sha(texture)=='2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1'}]
    if not all(c['passed'] for c in checks):raise RuntimeError(json.dumps(checks))
    # Keep the image absolute while the old archived blend is active; assigning
    # a new relative path here would be remapped from the archive on Save As.
    # Packing also makes the offline author file independently reviewable.
    image.filepath=str(texture);image.pack()
    blend=OUT/'abode_grandma_v2_candidate.blend';fbx=OUT/'abode_grandma_v2_candidate.fbx'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,
        mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    render_set('material-after')
    report={'status':'offline-wood-surface-candidate-not-unity-verified','source_candidate':str(source.relative_to(ROOT)),
            'source_sha256':sha(source),'script_sha256':sha(Path(__file__)),'geometry_sha256_before':before_geo,'geometry_sha256_after':after_geo,
            'candidate_triangles':after_tris,'budget':12100,'bounds_before':before_bounds,'bounds_after':after_bounds,
            'markers_before':before_markers,'markers_after':after_markers,'checks':checks,'uv':uv_report,
            'texture':{'path':str(texture.relative_to(ROOT)),'size':list(image.size),'sha256':sha(texture),'color_space':'sRGB','grain_axis':'V'},
            'material_mapping':changed,'shared_material_count':4,'render_views':VIEWS,'render_resolution':[1000,1000],
            'before_render_provenance':'Copied immutable prior neutral-studio candidate render, identical geometry/cameras/lighting.',
            'render_notes':'No height, normal, or AO map is synthesized. Fixed material roughness matches the planned URP helper.',
            'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [blend,fbx]+sorted(OUT.glob('material-*.png'))]}
    (OUT/'surface-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    before_manifest['status']=report['status'];before_manifest['surface_report']='surface-manifest.json'
    before_manifest['script_sha256']=sha(Path(__file__));before_manifest['files']=report['files']
    before_manifest['changes'][-1]='Wood pieces now use metric, long-axis UVs and one original 1254x1254 wood albedo; four shared Unity wood materials planned.'
    before_manifest['limits']=[x for x in before_manifest['limits'] if not x.startswith('No wood grain')]
    before_manifest['limits'].append('Wood has an albedo only; tile, stone and hardware surfaces remain color materials. Unity integration and nighttime appearance not yet verified.')
    (OUT/'manifest.json').write_text(json.dumps(before_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('HOUSE_SURFACE_DONE',after_tris,'wood_components',uv_report['wood_components'],'checks',len(checks),flush=True)

def seam_refinement():
    frozen=OUT/'archive-wood-surface-20261022';source=frozen/'abode_grandma_v2_candidate.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.view_layer.update()
    affected=('V2_Attic','V2_OverlappingClayTile');unchanged_hash=geometry_hash(affected)
    before_bounds=bounds();before_markers=markers();before_tris=triangles();changed=[]
    def uvhash():
        return hashlib.sha256(json.dumps({o.name:[list(v.uv) for v in o.data.uv_layers.active.data] for o in bpy.context.scene.objects if o.type=='MESH'},sort_keys=True).encode()).hexdigest()
    uv_before=uvhash()
    # Pixel ray picks land on opaque geometry, not a missing-face background.
    # Confirm the selected surface point is covered by more than one triangle.
    from mathutils.geometry import closest_point_on_tri
    pixel_rows=json.loads((OUT/'seam-pixel-rays-before.json').read_text(encoding='utf-8'))
    diagnosed=[]
    for row in pixel_rows:
        if row.get('object') not in affected or row['bbox'][1]>365:continue
        o=bpy.data.objects[row['object']];o.data.calc_loop_triangles();p=Vector(row['location']);hits=[]
        for t in o.data.loop_triangles:
            a,b,c=[o.matrix_world@o.data.vertices[v].co for v in t.vertices]
            if (closest_point_on_tri(p,a,b,c)-p).length<.000015:
                hits.append({'polygon':t.polygon_index,'triangle':list(t.vertices),'normal':list(t.normal)})
        diagnosed.append({**row,'covering_triangles_within_15_micrometres':hits})
    for name in affected:
        o=bpy.data.objects[name];d=o.data;adj=[set() for _ in d.vertices]
        for e in d.edges:
            a,b=e.vertices;adj[a].add(b);adj[b].add(a)
        pending=set(range(len(d.vertices)));ci=0
        while pending:
            seed=min(pending);pending.remove(seed);stack=[seed];ids=[]
            while stack:
                i=stack.pop();ids.append(i)
                for j in adj[i]:
                    if j in pending:pending.remove(j);stack.append(j)
            pts=[d.vertices[i].co.copy() for i in ids]
            lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)])
            size=hi-lo;center=(lo+hi)*.5;delta=0.;reason=''
            if name=='V2_OverlappingClayTile':
                x0=min(abs(lo.x),abs(hi.x));row=int(round(x0/.445));delta=-row*.0015
                reason='Separate coincident front/back caps of overlapping tile rows by 1.5 mm per row.'
            elif abs(size.y-.075)<.0001 and size.x>.45 and size.z<.08:
                delta=-.0015;reason='Horizontal attic frame lap projects 1.5 mm ahead of vertical members.'
            if delta:
                for i,p in zip(ids,pts):
                    d.vertices[i].co.y+=delta
                    changed.append({'object':name,'component':ci,'vertex':i,'before':list(p),'after':list(d.vertices[i].co),'distance_metres':abs(delta),'reason':reason})
            ci+=1
        d.update()
    bpy.context.view_layer.update();after_bounds=bounds();after_markers=markers();after_tris=triangles()
    checks=[{'name':'non_decoration_meshes_exact','passed':geometry_hash(affected)==unchanged_hash,'detail':unchanged_hash},
            {'name':'original_collision_structure_exact','passed':geometry_hash(affected)==unchanged_hash},
            {'name':'marker_transforms_exact','passed':before_markers==after_markers},
            {'name':'bounds_exact','passed':before_bounds==after_bounds},
            {'name':'triangle_count_exact_and_budget','passed':before_tris==after_tris and after_tris<=12100,'detail':after_tris},
            {'name':'uv0_exact','passed':uvhash()==uv_before},
            {'name':'vertex_displacement_at_most_6mm','passed':max(r['distance_metres'] for r in changed)<=.006001}]
    if not all(c['passed'] for c in checks):raise RuntimeError(json.dumps(checks))
    for view in VIEWS:shutil.copy2(frozen/f'material-after-{view}.png',OUT/f'seam-before-{view}.png')
    blend=OUT/'abode_grandma_v2_candidate.blend';fbx=OUT/'abode_grandma_v2_candidate.fbx'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,
        mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    render_set('seam-after')
    report={'status':'offline-coplanar-overlap-corrected-not-unity-verified','source_candidate':str(source.relative_to(ROOT)),
            'source_sha256':sha(source),'script_sha256':sha(Path(__file__)),'candidate_triangles':after_tris,'budget':12100,
            'bounds_before':before_bounds,'bounds_after':after_bounds,'markers_before':before_markers,'markers_after':after_markers,
            'checks':checks,'diagnosis_pixel_rays':diagnosed,'changed_vertices':changed,'changed_vertex_count':len(changed),
            'maximum_vertex_displacement_metres':max(r['distance_metres'] for r in changed),'new_triangles':0,
            'uv_sha256':uv_before,'render_views':VIEWS,'render_resolution':[1000,1000],
            'conclusion':'Black squares hit opaque faces. Coincident intersecting faces are separated only on new decorative meshes; no hole-cover patches or lighting changes.',
            'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [blend,fbx]+sorted(OUT.glob('seam-*.png'))]}
    (OUT/'seam-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    main=json.loads((frozen/'manifest.json').read_text(encoding='utf-8'));main['status']=report['status'];main['surface_report']='archive-wood-surface-20261022/surface-manifest.json';main['seam_report']='seam-manifest.json';main['files']=report['files'];main['script_sha256']=sha(Path(__file__))
    main['changes'].append('Separated coplanar overlapping tile end caps and attic frame laps by 1.5–6 mm on new decoration only; UV0, bounds, baseline Structure and markers preserved.')
    (OUT/'manifest.json').write_text(json.dumps(main,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('HOUSE_SEAM_DONE',after_tris,'changed_vertices',len(changed),'checks',len(checks),flush=True)

if '--seam-pass' in sys.argv:
    seam_refinement()
    raise SystemExit(0)
if '--surface-pass' in sys.argv:
    surface_refinement()
    raise SystemExit(0)

original_sha=sha(BASE);bpy.ops.wm.open_mainfile(filepath=str(BASE))
baseline_bounds=bounds();baseline_markers=markers();baseline_triangles=triangles()
render_set('before')

# The baseline carries all contractual openings, door, desk and seat geometry.
structure=bpy.data.objects['Structure']
roof_mats={i for i,m in enumerate(structure.data.materials) if m and m.name.startswith('Roof_')}
bm=bmesh.new();bm.from_mesh(structure.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in roof_mats],context='FACES')
bm.to_mesh(structure.data);bm.free();structure.data.update()

IVORY=[mat('V2_WhitewashedWood_'+str(i),c) for i,c in enumerate([(.60,.55,.43),(.68,.62,.50),(.73,.67,.55),(.64,.59,.48)])]
TIMBER=[mat('V2_OldTimber_'+str(i),c) for i,c in enumerate([(.24,.14,.075),(.29,.18,.10),(.36,.24,.14)])]
TILES=[mat('V2_TealClay_'+str(i),c,.65) for i,c in enumerate([(.10,.24,.25),(.14,.30,.29),(.17,.33,.31),(.12,.27,.29),(.22,.36,.32)])]
STONES=[mat('V2_FoundationStone_'+str(i),c,.9) for i,c in enumerate([(.38,.37,.31),(.47,.45,.36),(.42,.42,.36)])]
IRON=mat('V2_BlackenedIron',(.10,.12,.12),.43,.66)
COPPER=mat('V2_OldBrass',(.43,.28,.12),.48,.6)
GLASS=mat('V2_AtticUnlitAmberGlass',(.26,.17,.065),.29)

# Individual overlapping timber boards; clipping ranges deliberately leave the original door and round aperture open.
def plank(x0,x1,y,z,depth=.045,height=.174,side=False):
    if x1-x0<.07:return
    if side:
        o=box('WallBoard', (y,(x0+x1)/2,z), (depth,x1-x0-.007,height),RNG.choice(IVORY))
    else:o=box('WallBoard',((x0+x1)/2,y,z),(x1-x0-.007,depth,height),RNG.choice(IVORY),.008 if y<0 else 0)
    # Small shallow nail caps are real geometry, sparse and deliberately kept outside the beam opening.
    if x1-x0>.45 and row%4==0:
        for q in [x0+.10,x1-.10]:
            pos=(y+(.028 if y>0 else -.028),q,z) if side else (q,y-.028,z)
            rot=(0,math.pi/2,0) if side else (math.pi/2,0,0)
            cylinder('SidingNail',pos,.011,.006,IRON,5,rot)
for row in range(13):
    z=.29+row*.180
    plank(-2.0,-1.62,-1.64,z)
    plank(-.63,-.405,-1.64,z)
    if z>2.12:plank(-1.61,-.64,-1.64,z)
    # Largest circle cut across the board interval yields a clear 1.10m aperture with no hidden backing.
    dz=max(0,abs(z-1.62)-.094)
    half=math.sqrt(max(0,.565**2-dz**2)) if dz<.565 else 0
    if half:
        plank(-.397,.82-half,-1.64,z)
        plank(.82+half,1.998,-1.64,z)
    else:plank(-.397,1.998,-1.64,z)
    for side in [-1,1]:plank(-1.56,1.56,side*2.015,z,side=True)
    plank(-1.94,1.94,1.638,z)
box('EaveFrontLintel',(0,-1.685,2.55),(4.06,.11,.14),TIMBER[1],.012)
# Close a pre-existing 3 cm front-wall seam above the left door jamb without changing door clearance.
box('WallBoardDoorJambCap',(-1.585,-1.64,2.205),(.065,.065,.21),IVORY[1])

# Low stone skirt does not cover the door or raise floor collision height.
for side in [-1,1]:
    for j in range(7):
        y=-1.44+j*.47
        box('FieldstoneSide',(side*2.005,y,.135),(.19,.445,.26),RNG.choice(STONES),.035)
for y in [-1.66,1.66]:
    for j in range(9):
        x=-1.8+j*.45
        if y<0 and -1.70<x<-.52:continue
        box('FieldstoneFoot',(x,y,.135),(.43,.20,.26),RNG.choice(STONES),.03)

# Closed curved clay tiles. Grain/roughness texture slots remain for subsequent material work.
def tile(name,side,x0,x1,y0,y1,row):
    verts=[];samples=5
    for bottom in [False,True]:
        for x in [x0,x1]:
            for k in range(samples):
                t=k/(samples-1);y=y0+(y1-y0)*t
                camber=.026*math.sin(t*math.pi)
                z=3.82-abs(x)*1.18/2.29+camber-(.045 if bottom else 0)
                z+=.012*math.sin(row*1.7+y*2.5)
                verts.append((side*x,y,z))
    faces=[]
    for k in range(samples-1):
        faces.extend([(k,k+1,samples+k+1,samples+k),(2*samples+k,3*samples+k,3*samples+k+1,2*samples+k+1)])
    for edge in [0,samples-1]:faces.append((edge,samples+edge,3*samples+edge,2*samples+edge))
    for end in [0,1]:
        off=end*samples
        for k in range(samples-1):faces.append((off+k,off+2*samples+k,off+2*samples+k+1,off+k+1))
    return mesh(name,verts,faces,RNG.choice(TILES))
for side in [-1,1]:
    for row in range(5):
        x0=row*.445;x1=min(2.29,x0+.51)
        for j in range(10):
            y0=-1.895+j*.379
            tile('OverlappingClayTile',side,x0,x1,y0,y0+.383,row)
for j in range(10):
    cylinder('RidgeCap',(0,-1.81+j*.39,3.836),.087,.40,TILES[j%len(TILES)],8,(math.pi/2,0,0))

# Eaves project within the original envelope and give a readable crafted silhouette.
for side in [-1,1]:
    box('EaveBeam',(side*2.20,0,2.58),(.13,3.83,.15),TIMBER[0],.015)
    for y in [-1.47,-.75,0,.75,1.47]:
        beam('ExposedRafterTail',(side*1.93,y,2.52),(side*2.25,y,2.57),.095,TIMBER[1],True)
        beam('EaveKneeBrace',(side*1.97,y,2.11),(side*2.15,y,2.50),.085,TIMBER[2],True)

# Sea-facing attic dormer: exterior recess only, not a navigable upper floor.
box('AtticFront',(-.18,-1.95,3.17),(1.02,.12,.77),IVORY[2],.012)
box('AtticLeft',(-.69,-1.69,3.15),(.10,.57,.70),IVORY[1],.012)
box('AtticRight',(.33,-1.69,3.15),(.10,.57,.70),IVORY[0],.012)
mesh('DormerGable',[(-.74,-2.02,3.51),(.38,-2.02,3.51),(-.18,-2.02,3.83)],[(0,1,2)],IVORY[1])
for side in [-1,1]:
    x0=-.18;x1=-.18+side*.65
    verts=[(x0,-2.16,3.88),(x1,-2.16,3.49),(x1,-1.27,3.49),(x0,-1.27,3.88),
           (x0,-2.16,3.82),(x1,-2.16,3.43),(x1,-1.27,3.43),(x0,-1.27,3.82)]
    mesh('DormerRoof',verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],TILES[2])
    beam('DormerBargeboard',(-.18,-2.18,3.83),(x1,-2.18,3.44),.09,TIMBER[1],True)
    for j in range(4):
        y=-2.11+j*.22
        beam('DormerTileSeam',(-.18,y,3.893),(x1,y,3.503),.025,TILES[3])
box('AtticWindowRecess',(-.18,-2.025,3.20),(.52,.025,.56),TIMBER[0])
box('AtticAmberGlass',(-.18,-2.047,3.20),(.42,.008,.46),GLASS)
for dx,dz,w,h in [(-.27,0,.065,.67),(.27,0,.065,.67),(0,-.31,.60,.065),(0,.31,.60,.065),(0,0,.035,.56),(0,0,.52,.035)]:
    box('AtticWindowFrame',(-.18+dx,-2.065,3.20+dz),(w,.075,h),TIMBER[2],.008)
box('AtticWindowSill',(-.18,-2.12,2.875),(.70,.26,.075),TIMBER[1],.013)

# Low old tin flue clears the roof on its right slope without exceeding baseline ridge height.
cylinder('TinFlue',(.95,.56,3.49),.115,.69,IRON,12)
cylinder('FlueCap',(.95,.56,3.854),.17,.055,IRON,12)
for z in [3.27,3.65]:cylinder('FlueBand',(.95,.56,z),.124,.035,COPPER,12)
box('FlueFlashing',(.95,.56,3.31),(.44,.44,.035),IRON)

# Door and window hardware adds tactile scale; no geometry is added inside the open round window.
for z in [.32,1.62]:box('DoorHinge',(-1.677,-1.86,z),(.035,.20,.085),IRON,.008)
for x in [.23,1.41]:
    cylinder('RoundWindowHinge',(x,-1.71,1.62),.025,.16,COPPER,8)
box('DoorPullPlate',(-1.73,-2.28,1.02),(.035,.11,.14),COPPER,.009)

apply_normals_uv()
# Join by surface family to keep useful submeshes without exporting hundreds of draw objects.
root=bpy.data.objects.get('abode_grandma')
for family in ['WallBoard','SidingNail','Fieldstone','OverlappingClayTile','RidgeCap','Eave','ExposedRafter','Attic','Dormer','TinFlue','Flue','DoorHinge','DoorPull','RoundWindowHinge']:
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(family)]
    if not objs:continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=bpy.context.object;o.name='V2_'+family
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    o.parent=root;o.matrix_parent_inverse=root.matrix_world.inverted()

bpy.context.view_layer.update()
after_markers=markers();after_bounds=bounds();ntri=triangles()
checks=[]
def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
check('triangle_budget_12000',ntri<=12000,ntri)
for name,pose in baseline_markers.items():check('marker_exact_'+name,after_markers.get(name)==pose,after_markers.get(name))
check('original_source_unchanged',sha(BASE)==original_sha,sha(BASE))
for i,axis in enumerate('XYZ'):
    check('bounds_envelope_'+axis,after_bounds['min'][i]>=baseline_bounds['min'][i]-.035 and after_bounds['max'][i]<=baseline_bounds['max'][i]+.035,
          {'before':[baseline_bounds['min'][i],baseline_bounds['max'][i]],'after':[after_bounds['min'][i],after_bounds['max'][i]]})
# Ray checks in Blender coordinates prove front aperture stays open, not the entire Unity gameplay cone.
allv=[];allf=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    off=len(allv);allv.extend(o.matrix_world@v.co for v in o.data.vertices)
    allf.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons)
bvh=BVHTree.FromPolygons(allv,allf)
for name,x,z in [('window_center',.82,1.62),('window_left',.52,1.62),('window_right',1.12,1.62),('window_top',.82,1.95),('entry',-1.13,1.1)]:
    hit=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)),1.9)
    check('aperture_clear_'+name,hit[0] is None,{'origin':[x,-3,z],'length':1.9,'hit':list(hit[0]) if hit[0] else None})
check('all_meshes_have_uv',all(o.data.uv_layers.active is not None for o in bpy.context.scene.objects if o.type=='MESH'))

scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
blend=OUT/'abode_grandma_v2_candidate.blend';fbx=OUT/'abode_grandma_v2_candidate.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,
    mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
render_set('after')
report={'status':'offline-candidate-not-imported','source_blend':str(BASE.relative_to(ROOT)).replace('\\','/'),'source_sha256':original_sha,
 'source_metadata':str(META.relative_to(ROOT)).replace('\\','/'),'script_sha256':sha(Path(__file__)),
 'baseline_triangles':baseline_triangles,'candidate_triangles':ntri,'budget':12000,'baseline_bounds_blender':baseline_bounds,
 'candidate_bounds_blender':after_bounds,'markers_before':baseline_markers,'markers_after':after_markers,'checks':checks,
 'mesh_objects':sum(o.type=='MESH' for o in bpy.context.scene.objects),'material_count':len({m.name for o in bpy.context.scene.objects if o.type=='MESH' for m in o.data.materials if m}),
 'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [blend,fbx]+sorted(OUT.glob('*.png'))],
 'render_views':VIEWS,'render_resolution':[1000,1000],'render_lighting':'Identical neutral studio setup before/after; not night in-game rendering.',
 'changes':['Retained baseline structure, genuine circular opening, open doorway, desk, book and seat.','Replaced old flat roof and narrow raised grid lines with overlapping curved clay tiles.','Added sea-facing attic exterior recess within original height envelope, timber eaves and low tin chimney.','Added staggered whitewashed siding, sparse nail heads, uneven stone foot and restrained metal hardware.','Smart-projected UVs generated for every mesh; no external texture was used.'],
 'limits':['Not imported into Unity; prior FBX axis workaround must be tested before substitution.','Attic is exterior visual geometry only: no walkable upstairs, ladder or new interior navigation.','No wood grain / clay / plaster PBR maps yet; previews use material colors and actual geometry.','5 local aperture rays are only a geometry sanity check, not complete spotlight/camera/capsule validation.','New attic window is unlit; gameplay visibility/emission hookup requires owner integration.','All original Marker transforms remain fixed; future integration must verify actual prefab anchors and colliders.']}
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ENV_V2_GRANDMA_DONE',ntri,'FAILED',sum(not c['passed'] for c in checks),flush=True)
