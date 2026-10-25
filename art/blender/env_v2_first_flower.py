"""Original A04 flower. Offline only; writes first-flower/, never Unity Assets.

blender --background --factory-startup --python-exit-code 1 --python this.py
Add -- --verify to reimport the FBX in a fresh process and audit the round trip.
"""
import bpy, json, math, hashlib, sys
from pathlib import Path
from collections import Counter
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art/generated/env-v2/first-flower/candidate-c'
OUT.mkdir(parents=True, exist_ok=True)
FBX = OUT / 'first_flower_A04.fbx'
BLEND = OUT / 'first_flower_A04.blend'
PHI = [0, .18, .58, math.pi/2, math.pi-.58, math.pi-.18,
       math.pi, math.pi+.18, math.pi+.58, 3*math.pi/2, 2*math.pi-.58, 2*math.pi-.18]
RINGS = [.035, .10, .19, .31, .45, .60, .73, .84, .93, .982]
BLOOM = Vector((.047, .008, .181))
AXIS = Vector((.25, -.17, .953)).normalized()
ROT = Vector((0, 0, 1)).rotation_difference(AXIS)
POSITIONS = [[], [], []]  # closed, half, open
UV, FACES, SLOTS, COMPONENTS = [], [], [], []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def add_vertex(poses, uv=(0, 0)):
    idx = len(UV)
    for k, p in enumerate(poses): POSITIONS[k].append(Vector(p))
    UV.append(tuple(uv))
    return idx


def tri(a, b, c, mat):
    FACES.append((a, b, c)); SLOTS.append(mat)


def quad(a, b, c, d, mat):
    tri(a, b, c, mat); tri(a, c, d, mat)


def finish_component(name, first_vertex, first_face):
    # Orient each closed component outward without touching topology or morph order.
    vol = sum(POSITIONS[2][a].dot(POSITIONS[2][b].cross(POSITIONS[2][c]))
              for a, b, c in FACES[first_face:]) / 6
    if vol < 0:
        FACES[first_face:] = [(c, b, a) for a, b, c in FACES[first_face:]]
    COMPONENTS.append({'name': name, 'vertex_first': first_vertex,
                       'vertex_count': len(UV)-first_vertex,
                       'face_first': first_face, 'face_count': len(FACES)-first_face})


def petal_point(t, phi, index, state):
    # Each petal is a closed lenticular shell, with curved axis and real side thickness.
    variation = [1.0, .975, 1.025, .982, 1.012, .99][index]
    theta = index*math.tau/6 + .16 + [.0, .018, -.022, .012, -.015, .008][index]
    length = .111 * variation
    width = .0445 * (1 + .055*math.sin(index*2.17))
    if state == 0:
        r = .008*(1-t) + .024*math.sin(math.pi*t)
        z = .003 + .111*t
        dr = .024*math.pi*math.cos(math.pi*t) - .008
        dz = .111
        width *= .47
    elif state == 1:
        r = .006 + .073*t - .014*t*t
        z = .004 + .063*t + .006*math.sin(math.pi*t)
        dr = .073 - .028*t
        dz = .063 + .006*math.pi*math.cos(math.pi*t)
        width *= .82
    else:
        r = .005 + length*t
        z = .004 - .009*math.sin(math.pi*t) + .046*t*t
        dr = length
        dz = -.009*math.pi*math.cos(math.pi*t) + .092*t
    # Broad rounded blade; no flat radial triangles or stacked spheres.
    width *= max(0, math.sin(math.pi*t))**.50
    if state == 2:
        width = min(width, r*.53 + .0035*math.sin(math.pi*t))
    elif state == 1:
        width = min(width, r*.60 + .004*math.sin(math.pi*t))
    thick = .0019*max(0, math.sin(math.pi*t))**.45
    side = width*math.cos(phi)
    # Cupped edges, small asymmetry, and a gentle living roll at the lip.
    cup = (.009 if state == 2 else .003)*(math.cos(phi)**2)*math.sin(math.pi*t)
    twist = .0014*math.sin(index*1.9 + t*math.pi)*math.cos(phi)*t
    n = Vector((-dz, 0, dr)).normalized()
    p = Vector((r, side, z + cup + twist)) + n*(thick*math.sin(phi))
    p = Quaternion(Vector((0, 0, 1)), theta) @ p
    return BLOOM + ROT @ p


def add_petal(index):
    v0, f0 = len(UV), len(FACES)
    base = add_vertex([petal_point(0, math.pi/2, index, s) for s in range(3)], (0, .25))
    rings = []
    for t in RINGS:
        rings.append([add_vertex([petal_point(t, a, index, s) for s in range(3)], (t, a/math.tau)) for a in PHI])
    tip = add_vertex([petal_point(1, math.pi/2, index, s) for s in range(3)], (1, .25))
    for j in range(12):
        mat = 1 if j in (0, 5, 6, 11) else 0
        tri(base, rings[0][(j+1)%12], rings[0][j], mat)
        for a, b in zip(rings[:-1], rings[1:]): quad(a[j], a[(j+1)%12], b[(j+1)%12], b[j], mat)
        tri(rings[-1][j], rings[-1][(j+1)%12], tip, mat)
    finish_component('Petal_%02d' % (index+1), v0, f0)


def add_tube(name, points, radii, sides=8, material=3):
    v0, f0 = len(UV), len(FACES)
    points = list(map(Vector, points)); rings = []
    for i, (p, radius) in enumerate(zip(points, radii)):
        tangent = (points[min(i+1,len(points)-1)] - points[max(0,i-1)]).normalized()
        ref = Vector((1, 0, 0)) if abs(tangent.x) < .85 else Vector((0, 1, 0))
        u = tangent.cross(ref).normalized(); v = tangent.cross(u)
        row=[]
        for j in range(sides):
            a=j*math.tau/sides; co=p + radius*(u*math.cos(a)+v*math.sin(a))
            row.append(add_vertex([co]*3,(j/sides,i/max(1,len(points)-1))))
        rings.append(row)
    for a,b in zip(rings[:-1],rings[1:]):
        for j in range(sides):quad(a[j],a[(j+1)%sides],b[(j+1)%sides],b[j],material)
    # A closed branch-root cap at the origin gives an explicit attachment interface.
    ca=add_vertex([points[0]]*3);cb=add_vertex([points[-1]]*3)
    for j in range(sides):
        tri(ca,rings[0][(j+1)%sides],rings[0][j],material)
        tri(cb,rings[-1][j],rings[-1][(j+1)%sides],material)
    finish_component(name,v0,f0)


def add_leaf(name, start, end, width, material=4, edge=True):
    v0,f0=len(UV),len(FACES);start,end=Vector(start),Vector(end)
    tangent=(end-start).normalized()
    lateral=tangent.cross(Vector((0,-.35,1))).normalized()
    normal=lateral.cross(tangent).normalized()
    base=add_vertex([start]*3);rings=[]
    angles=PHI if edge else [i*math.tau/6 for i in range(6)]
    for t in [.13,.37,.65,.88]:
        centre=start.lerp(end,t)+normal*(.006*math.sin(math.pi*t))
        w=width*math.sin(math.pi*t)**.72;thick=.00055+.00035*math.sin(math.pi*t)
        row=[]
        for a in angles:
            co=centre+lateral*w*math.cos(a)+normal*(thick*math.sin(a)+.0013*math.cos(a)**2*math.sin(math.pi*t))
            row.append(add_vertex([co]*3,(t,a/math.tau)))
        rings.append(row)
    tip=add_vertex([end]*3,(1,.25));n=len(angles)
    for j in range(n):
        slot=1 if edge and j in (0,5,6,11) else material
        tri(base,rings[0][(j+1)%n],rings[0][j],slot)
        for a,b in zip(rings[:-1],rings[1:]):quad(a[j],a[(j+1)%n],b[(j+1)%n],b[j],slot)
        tri(rings[-1][j],rings[-1][(j+1)%n],tip,slot)
    finish_component(name,v0,f0)


def add_heart():
    v0,f0=len(UV),len(FACES);c=BLOOM+ROT@Vector((0,0,.009))
    # One small amber seed, not a cluster of plastic spheres.
    bottom=add_vertex([c+ROT@Vector((0,0,-.008))]*3);rings=[]
    for i in range(1,6):
        a=-math.pi/2+math.pi*i/6;row=[]
        for j in range(12):
            th=j*math.tau/12
            co=c+ROT@Vector((.0105*math.cos(a)*math.cos(th),.0105*math.cos(a)*math.sin(th),.008*math.sin(a)))
            row.append(add_vertex([co]*3,(j/12,i/6)))
        rings.append(row)
    top=add_vertex([c+ROT@Vector((0,0,.008))]*3,(.5,1))
    for j in range(12):
        tri(bottom,rings[0][(j+1)%12],rings[0][j],2)
        for a,b in zip(rings[:-1],rings[1:]):quad(a[j],a[(j+1)%12],b[(j+1)%12],b[j],2)
        tri(top,rings[-1][j],rings[-1][(j+1)%12],2)
    finish_component('SingleAmberHeart',v0,f0)


def material(name, color, roughness, metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Roughness'].default_value=roughness;n.inputs['Metallic'].default_value=metal
    return m


def materials():
    petal=material('A04_Petals_CreamGold',(.92,.79,.51),.56)
    bs=petal.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Subsurface Weight'].default_value=.08
    bs.inputs['Subsurface Scale'].default_value=.004
    bs.inputs['Transmission Weight'].default_value=.035
    bs.inputs['Specular IOR Level'].default_value=.28
    image=bpy.data.images.new('A04_OriginalPetalGradient',256,128,alpha=True)
    pixels=[]
    for y in range(128):
        phi=y/127*math.tau
        for x in range(256):
            t=x/255
            # Original low-contrast lamina gradient with fine longitudinal veins.
            mix=min(1,t/.52)
            start=(.86,.63,.27);end=(.96,.875,.67)
            vein=(.5+.5*math.cos(phi*18+.6*math.sin(t*9)))**12*.024*math.sin(math.pi*t)
            noise=.004*math.sin(x*1.31+y*2.17)*math.sin(x*.21-y*.37)
            rgb=[max(0,min(1,start[k]*(1-mix)+end[k]*mix-vein+noise)) for k in range(3)]
            pixels.extend([*rgb,1])
    image.pixels.foreach_set(pixels);image.filepath_raw=str(OUT/'A04_petal_albedo.png');image.file_format='PNG';image.save();image.pack()
    tex=petal.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
    petal.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    edge=material('A04_FineGoldEdges',(.56,.37,.105),.48,.16)
    heart=material('A04_SingleAmberHeart',(.68,.245,.035),.3,.02)
    heart.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.12
    twig=material('A04_Twig_WarmBrown',(.105,.065,.035),.84)
    leaf=material('A04_Leaves_SilverGreen',(.205,.32,.245),.67)
    leaf.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.04
    return [petal,edge,heart,twig,leaf]


def pose(obj,state):
    obj.data.shape_keys.key_blocks['HalfOpen'].value = 1 if state=='half' else 0
    obj.data.shape_keys.key_blocks['Open'].value = 1 if state=='open' else 0
    bpy.context.view_layer.update()


def audit_positions(data,faces):
    edges=Counter(tuple(sorted((a,b))) for f in faces for a,b in zip(f,(f[1],f[2],f[0])))
    degenerate=sum((Vector(data[b])-Vector(data[a])).cross(Vector(data[c])-Vector(data[a])).length < 1e-12 for a,b,c in faces)
    return {'vertices':len(data),'triangles':len(faces),'boundary_edges':sum(n==1 for n in edges.values()),
            'nonmanifold_edges':sum(n!=2 for n in edges.values()),'degenerate_triangles':degenerate,
            'finite':all(math.isfinite(v) for p in data for v in p),
            'bounds_min':[min(p[i] for p in data) for i in range(3)],'bounds_max':[max(p[i] for p in data) for i in range(3)]}


def render(obj):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=40;sc.cycles.use_denoising=True
    sc.render.threads_mode='FIXED';sc.render.threads=8
    sc.render.resolution_x=900;sc.render.resolution_y=900;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast'
    world=bpy.data.worlds.new('A04 Neutral Studio');world.use_nodes=True;sc.world=world
    bg=world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.40,.42,.45,1);bg.inputs['Strength'].default_value=.35
    lights=[]
    for loc,power,size in [((.23,-.35,.5),6,.33),((-.3,-.1,.22),2.4,.36),((.05,.35,.4),5.4,.27)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size
        o.rotation_euler=(BLOOM-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
    bpy.ops.object.camera_add(location=(.36,-.52,.48));cam=bpy.context.object;cam.name='AuditCamera';sc.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=.355
    look=Vector((.035,.003,.147));cam.rotation_euler=(look-cam.location).to_track_quat('-Z','Y').to_euler()
    view={'position':list(cam.location),'rotation_quaternion':list(cam.rotation_euler.to_quaternion()),'target':list(look),'ortho_scale':cam.data.ortho_scale,'resolution':[900,900]}
    for state in ('closed','half','open'):
        pose(obj,state);sc.render.filepath=str(OUT/f'neutral-{state}.png');bpy.ops.render.render(write_still=True)
    # Same camera / exposure / geometry for night; only documented lighting changes.
    bg.inputs['Color'].default_value=(.009,.018,.043,1);bg.inputs['Strength'].default_value=.2
    for o,power,col in zip(lights,[2.4,.7,1.7],[(1,.70,.40),(.28,.46,.75),(1,.64,.3)]):o.data.energy=power;o.data.color=col
    heart=obj.data.materials[2].node_tree.nodes.get('Principled BSDF')
    heart.inputs['Emission Color'].default_value=(1,.39,.065,1);heart.inputs['Emission Strength'].default_value=2.0
    sc.render.filepath=str(OUT/'night-open.png');bpy.ops.render.render(write_still=True)
    heart.inputs['Emission Strength'].default_value=0
    bg.inputs['Color'].default_value=(.40,.42,.45,1);bg.inputs['Strength'].default_value=.35
    for o,power in zip(lights,[6,2.4,5.4]):o.data.energy=power;o.data.color=(1,1,1)
    cam.location=(.37,-.52,.205);cam.rotation_euler=(Vector((.035,.003,.147))-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=str(OUT/'neutral-side-thickness.png');bpy.ops.render.render(write_still=True)
    for o in lights+[cam]:bpy.data.objects.remove(o,do_unlink=True)
    return view


def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    for i in range(6):add_petal(i)
    twig=[(0,0,0),(.006,-.003,.038),(.015,-.003,.078),(.026,.001,.116),(.039,.006,.153),tuple(BLOOM)]
    add_tube('AttachmentTwig',twig,[.0052,.0048,.0041,.0035,.0028,.0022],8,3)
    add_tube('LeafStalk_Left',[(.017,-.002,.085),(-.002,-.003,.095),(-.019,-.005,.104)],[.0017,.0013,.0008],6,3)
    add_tube('LeafStalk_Right',[(.025,.001,.114),(.048,.002,.099),(.063,.008,.098)],[.0016,.0012,.0008],6,3)
    add_leaf('SilverLeaf_Left',(-.019,-.005,.104),(-.082,-.015,.143),.019)
    add_leaf('SilverLeaf_Right',(.063,.008,.098),(.123,.022,.113),.018)
    # A small green receptacle below the petals; no visible star-shaped insert.
    add_tube('FlowerReceptacle',[BLOOM+ROT@Vector((0,0,z)) for z in (-.012,-.004,.001)],[.003,.0095,.0085],8,4)
    add_heart()
    # Normalize corolla projected span to exactly 0.25 m, not total branch height.
    pcount=sum(c['vertex_count'] for c in COMPONENTS if c['name'].startswith('Petal'))
    petals=[ROT.inverted()@(p-BLOOM) for p in POSITIONS[2][:pcount]]
    diameter=max((Vector((a.x,a.y,0))-Vector((b.x,b.y,0))).length for a in petals for b in petals)
    factor=.25/diameter
    for state in POSITIONS:
        for i in range(pcount):state[i]=BLOOM+(state[i]-BLOOM)*factor
    data=bpy.data.meshes.new('FirstFlower_A04_MorphMesh');data.from_pydata(POSITIONS[0],[],FACES);data.update()
    obj=bpy.data.objects.new('FirstFlower_Geometry',data);bpy.context.collection.objects.link(obj)
    for m in materials():data.materials.append(m)
    uv=data.uv_layers.new(name='UVMap')
    for p,slot in zip(data.polygons,SLOTS):
        p.material_index=slot;p.use_smooth=True
        for li in p.loop_indices:uv.data[li].uv=UV[data.loops[li].vertex_index]
    for key,co in zip(['ClosedBud','HalfOpen','Open'],POSITIONS):
        block=obj.shape_key_add(name=key)
        for v,p in zip(block.data,co):v.co=p
    root=bpy.data.objects.new('FirstFlower_A04',None);bpy.context.collection.objects.link(root);obj.parent=root
    marker=bpy.data.objects.new('Marker_AttachRoot',None);bpy.context.collection.objects.link(marker);marker.parent=root
    center=bpy.data.objects.new('Marker_BloomCenter',None);bpy.context.collection.objects.link(center);center.parent=root;center.location=BLOOM;center.rotation_mode='QUATERNION';center.rotation_quaternion=ROT
    report={'source':'original analytic mesh; no imported/reference geometry or textures','story':'07 line 261; v2 art prompt A04','units':'meters; Blender Z up; FBX -Z forward/Y up','root_pivot':[0,0,0],'bloom_center_blender':list(BLOOM),'bloom_axis_blender':list(AXIS),'petal_count':6,'leaf_count':2,'open_corolla_diameter_m':.25,'material_slots':[m.name for m in data.materials],'components':COMPONENTS,'poses':{n:audit_positions(v,FACES) for n,v in zip(['closed','half','open'],POSITIONS)},'shape_keys':['ClosedBud (basis)','HalfOpen','Open'],'unity_verified':False,'scene_attached':False}
    for p in report['poses'].values():assert p['triangles']<=2000 and not p['degenerate_triangles'] and not p['nonmanifold_edges'] and p['finite'],p
    pose(obj,'closed');bpy.ops.object.select_all(action='DESELECT')
    for o in [obj,root,marker,center]:o.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Z',axis_up='Y',use_mesh_modifiers=False,mesh_smooth_type='FACE',use_triangles=True,bake_anim=False,add_leaf_bones=False,path_mode='COPY',embed_textures=False)
    report['camera']=render(obj)
    pose(obj,'closed');bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report['files']={p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.suffix in ['.blend','.fbx','.png']}
    report['lighting']={'neutral':'3 white area lights 6/2.4/5.4W; world strength .35; no emissive asset materials','night':'same camera/exposure; warm/cool/warm area 2.4/.7/1.7W; dark blue world .2; only amber heart emission strength 2.0; no compositor bloom','note':'Blender study, not Unity runtime material verification'}
    (OUT/'asset-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    snapshot={'positions':[[list(p) for p in v] for v in POSITIONS],'faces':FACES,'uv':UV,'materials':report['material_slots'],'markers':{o.name:list(o.location) for o in [marker,center]},'fbx_sha256':sha(FBX)}
    (OUT/'source-geometry.json').write_text(json.dumps(snapshot,separators=(',',':')),encoding='utf-8')
    print('A04 BUILD COMPLETE',len(FACES),'triangles; outputs',OUT)


def verify():
    expected=json.loads((OUT/'source-geometry.json').read_text(encoding='utf-8'))
    assert sha(FBX)==expected['fbx_sha256']
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(FBX),use_custom_normals=True,use_image_search=True)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==1
    obj=meshes[0];obj.data.calc_loop_triangles()
    keys=obj.data.shape_keys.key_blocks if obj.data.shape_keys else None;assert keys and len(keys)==3
    results={};names=['Basis','HalfOpen','Open']
    # Blender FBX importer calls the basis 'Basis'. Compare world positions by vertex order.
    for i,key in enumerate(keys):
        actual=[obj.matrix_world@v.co for v in key.data];want=expected['positions'][i]
        assert len(actual)==len(want)
        err=max((a-Vector(w)).length for a,w in zip(actual,want))
        faces=[tuple(t.vertices) for t in obj.data.loop_triangles]
        stats=audit_positions(actual,faces)
        stats.update({'key_name':key.name,'max_world_vertex_error_m':err})
        results[key.name]=stats
        assert err<1e-6 and stats['triangles']==len(expected['faces']) and not stats['degenerate_triangles']
    uv=obj.data.uv_layers.active;max_uv=0
    for loop in obj.data.loops:max_uv=max(max_uv,(uv.data[loop.index].uv-Vector(expected['uv'][loop.vertex_index])).length)
    assert max_uv<1e-6
    markers={}
    for name,want in expected['markers'].items():
        o=bpy.data.objects.get(name);assert o
        error=(o.matrix_world.translation-Vector(want)).length;assert error<1e-6;markers[name]={'position':list(o.matrix_world.translation),'max_error_m':error}
    material_names=[m.name for m in obj.data.materials];assert material_names==expected['materials']
    report={'fbx_sha256':sha(FBX),'fresh_process':True,'single_mesh':True,'shape_key_count':len(keys),'materials':material_names,'max_uv_error':max_uv,'poses':results,'markers':markers,'object_scale':list(obj.scale),'object_world_matrix':[list(r) for r in obj.matrix_world],'unity_import_verified':False}
    (OUT/'fbx-roundtrip.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    authored=json.loads((OUT/'asset-report.json').read_text(encoding='utf-8'))
    samples=[]
    for step in range(9):
        t=step/8
        a,b,u=(0,1,t*2) if t<=.5 else (1,2,t*2-1)
        coords=[Vector(p).lerp(Vector(q),u) for p,q in zip(expected['positions'][a],expected['positions'][b])]
        stats=audit_positions(coords,expected['faces'])
        volumes={}
        for comp in authored['components']:
            origin=coords[comp['vertex_first']]
            faces=expected['faces'][comp['face_first']:comp['face_first']+comp['face_count']]
            volumes[comp['name']]=sum((coords[x]-origin).dot((coords[y]-origin).cross(coords[z]-origin)) for x,y,z in faces)/6
        assert all(v>0 for v in volumes.values()) and not stats['degenerate_triangles'] and stats['finite']
        samples.append({'bloom_t':t,'half_open_weight_percent':min(t*200,(1-t)*200),
                        'open_weight_percent':max(0,(t-.5)*200),'geometry':stats,'component_signed_volumes_m3':volumes})
    (OUT/'morph-interpolation-audit.json').write_text(json.dumps({'scope':'9 piecewise-linear samples; positive closed component volumes do not prove absence of all self/inter-petal intersections','samples':samples},ensure_ascii=False,indent=2),encoding='utf-8')
    print('A04 FRESH FBX ROUNDTRIP PASSED',json.dumps({'triangles':len(expected['faces']),'keys':[k.name for k in keys],'max_uv_error':max_uv}))


def verify_blend():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    obj=bpy.data.objects['FirstFlower_Geometry'];obj.data.calc_loop_triangles()
    image=bpy.data.images['A04_OriginalPetalGradient']
    keys=obj.data.shape_keys.key_blocks
    assert len(obj.data.loop_triangles)==1968 and len(keys)==3
    assert keys['HalfOpen'].value==0 and keys['Open'].value==0
    assert image.packed_file and tuple(image.size)==(256,128)
    assert list(obj.parent.location)==[0,0,0] and obj.parent.name=='FirstFlower_A04'
    data={'fresh_process':True,'blend_sha256':sha(BLEND),'triangles':len(obj.data.loop_triangles),
          'basis':'ClosedBud','default_weights':{'HalfOpen':0,'Open':0},
          'packed_image':{'name':image.name,'size':list(image.size),'bytes':image.packed_file.size},
          'mesh_objects':len([o for o in bpy.context.scene.objects if o.type=='MESH']),
          'camera_or_light_objects':len([o for o in bpy.context.scene.objects if o.type in ('CAMERA','LIGHT')]),
          'neutral_heart_emission':obj.data.materials[2].node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value}
    (OUT/'blend-reopen.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('A04 FRESH BLEND REOPEN PASSED')


if __name__=='__main__':
    if '--verify-blend' in sys.argv:verify_blend()
    elif '--verify' in sys.argv:verify()
    else:build()
