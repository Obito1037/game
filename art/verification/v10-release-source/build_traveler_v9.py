"""V10 game silhouette candidate from frozen character-v8; CPU-only previews."""
import ast,bpy,json,hashlib,math,sys
from pathlib import Path
from mathutils import Vector
from math import sin,cos,pi,exp,sqrt
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v8/traveler.blend'
OUT=ROOT/'art/generated/character-v9'; OUT.mkdir(parents=True,exist_ok=True)
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for filename,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract','nearest_on_segment'}),
                       ('build_traveler_v6.py',{'smooth','proportion','unproportion'}),
                       ('build_traveler_v8.py',{'components'})]:
    tree=ast.parse((ROOT/'art/blender'/filename).read_text(encoding='utf-8'))
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=selected,type_ignores=[]),filename,'exec'))
ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
TARGETS={'Head_Hair_Indigo','Head_Hair_MidnightBlue','Sleeve_L','Sleeve_R','TailoredTunic','Trouser_L','Trouser_R'}

def inspect():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); result={}
    for name in sorted(TARGETS):
        obj=bpy.data.objects[name]; rows=[]
        for ids in components(obj):
            points=[unproportion(obj.matrix_world@obj.data.vertices[i].co) for i in ids]
            low=[min(p[d] for p in points) for d in range(3)]; high=[max(p[d] for p in points) for d in range(3)]
            rows.append({'count':len(ids),'min':low,'max':high,'first':min(ids)})
        result[name]=rows
    (OUT/'source-components.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)

def nearest_curve(p,centers):
    best=None
    for i in range(len(centers)-1):
        a,b=centers[i:i+2]; delta=b-a
        q=max(0,min(1,(p-a).dot(delta)/max(delta.length_squared,1e-12)))
        center=a+delta*q; distance=(p-center).length_squared
        if best is None or distance<best[0]: best=(distance,i,q,center)
    return best[1:]

def curve_warp(p,old,new,width_scale,depth_scale):
    i,t,center=nearest_curve(p,old); target=new[i].lerp(new[i+1],t)
    tangent=(old[i+1]-old[i]).normalized(); a=tangent.cross(Vector((0,-1,0)))
    if a.length<1e-8: a=tangent.cross(Vector((1,0,0)))
    a.normalize(); b=tangent.cross(a).normalized()
    q=p-center
    return target+a*q.dot(a)*width_scale+b*q.dot(b)*depth_scale+tangent*q.dot(tangent)

def hair_shapes(obj,highlight):
    """Keep scalp and all facial islands; reshape existing tuft groups."""
    islands=components(obj); records=[]; warps=[]
    front=0; temple=0; back=0
    inv=obj.matrix_world.inverted()
    for ids in islands:
        ids=sorted(ids); points=[unproportion(obj.matrix_world@obj.data.vertices[i].co) for i in ids]
        if len(ids) not in [150,130] or max(p.z for p in points)<1.20: continue
        assert len(ids)%10==0
        centers=[sum(points[j:j+10],Vector())/10 for j in range(0,len(points),10)]
        new=[]
        if len(ids)==150:
            group='front'; index=front; front+=1
            width=[.73,.66,.68,1.04,.76,.91,.78,1.0][index]; depth=.66
            tipx=[-.036,-.022,-.010,-.005,.003,.012,.015,.013][index]
            tipz=[.028,.017,.021,-.010,-.005,.008,.012,-.003][index]
            lift=[.019,.025,.009,.017,.010,.018,.008,.014][index]
            for j,c in enumerate(centers):
                t=j/(len(centers)-1); takeoff=smooth(.08,1,t)
                new.append(c+Vector((tipx*takeoff,-.004*sin(pi*t)**2,
                    tipz*takeoff+lift*exp(-((t-.45)/.25)**2)*smooth(0,.20,t))))
        elif max(p.z for p in points)<1.22:
            group='temple'; index=temple; temple+=1
            width=.82 if index%3!=1 else .94; depth=.80
            side=-1 if centers[-1].x<0 else 1
            outward=[.009,.017,.012,.007,.013,.010][index]
            lift=[.006,.010,.003,.003,.008,.005][index]
            for j,c in enumerate(centers):
                t=j/(len(centers)-1); mask=smooth(.25,1,t)
                new.append(c+Vector((side*outward*mask,.004*mask,lift*mask)))
        else:
            group='back'; index=back; back+=1
            width=[.78,.9,.69,.87,.76,.94,.71,.86,.73,.91,.74,.83,.79][index]; depth=.75
            outward=[.008,.016,.012,.021,.009,.018,.013,.022,.010,.016,.024,.011,.017][index]
            lift=[.004,-.004,.010,-.006,.008,-.002,.005,-.005,.009,-.003,.003,.007,-.004][index]
            for j,c in enumerate(centers):
                t=j/(len(centers)-1); mask=smooth(.18,1,t)
                radial=Vector((c.x,c.y-.011,0)).normalized()
                new.append(c+radial*outward*mask+Vector((0,0,lift*mask)))
        for index,p in zip(ids,points):
            transformed=curve_warp(p,centers,new,width,depth)
            obj.data.vertices[index].co=inv@proportion(transformed)
        warps.append((centers,new,width,depth))
        records.append({'group':group,'vertices':ids,'original_centers':[list(c) for c in centers],
                        'new_centers':[list(c) for c in new],'width_scale':width,'depth_scale':depth})
    # The little lighter strand strokes are embedded in the same original locks.
    hi_inv=highlight.matrix_world.inverted(); hi_components=components(highlight)
    assert len(hi_components)==len(warps),(len(hi_components),len(warps))
    for ids,(old,new,width,depth) in zip(hi_components,warps):
        for index in ids:
            p=unproportion(highlight.matrix_world@highlight.data.vertices[index].co)
            highlight.data.vertices[index].co=hi_inv@proportion(curve_warp(p,old,new,width,depth))
    obj.data.update(); highlight.data.update()
    return records

SLEEVE_PATH=[(.112,.002,.908),(.145,.002,.894),(.18,.001,.873),(.202,-.001,.831),(.222,.002,.774),(.237,-.004,.719),(.248,-.018,.660),(.256,-.036,.610),(.262,-.048,.574)]

def sleeve_shape(p,side):
    path=[Vector((side*x,y,z)) for x,y,z in SLEEVE_PATH]
    i,t,c=nearest_curve(p,path); progress=(i+t)/(len(path)-1)
    # Embedded shoulder root and complete cuff remain exact. Upper-arm fullness
    # drops away from the shoulder, instead of a circular tube of constant radius.
    gate=smooth(.04,.16,progress)*(1-smooth(.72,.92,progress))
    if gate==0: return p.copy()
    radial=p-c
    narrow=.20*exp(-((progress-.25)/.23)**2)
    relax=.07*exp(-((progress-.57)/.14)**2)
    scale=1+gate*(relax-narrow)
    q=c+radial*scale
    q.x-=side*.007*gate*exp(-((progress-.28)/.22)**2)
    q.z-=.010*gate*exp(-((progress-.25)/.24)**2)
    # One broad, oblique fabric break at the inner elbow. This keeps v7's
    # localized fold rather than restoring any circular periodic field.
    facing=max(0,-radial.y/max(radial.length,1e-8))
    crease=exp(-((progress-.58-side*.018)/.055)**2)*facing**2
    q.y+=.0038*crease*gate
    return q

def tunic_shape(p):
    x,y,z=p
    # Protect the visible button placket, front stitches, satchel attachment zone,
    # collar and short cape. Only lower side/back cloth has additional ease.
    low=1-smooth(.48,.62,z)
    lateral=smooth(.065,.13,abs(x)); back=smooth(-.075,.02,y)
    mask=low*max(lateral*.9,back)*smooth(-.09,-.055,y)
    if mask==0: return p.copy()
    side=-1 if x<0 else 1
    q=p.copy(); q.x+=side*.019*lateral*mask
    q.y+=.014*back*mask
    # The hem is higher at the side seam and falls again behind the leg.
    edge=1-smooth(.445,.515,z)
    q.z+=(.012*lateral*(1-back*.8)-.006*back)*mask*edge
    # Two long, unequal hanging folds follow side/back fabric, not an annular wave.
    angle=math.atan2(x,max(.005,y))
    first=exp(-((angle-.72)/.22)**2)
    second=exp(-((angle+.85)/.27)**2)
    fold=(.0045*first-.0030*second)*mask
    direction=Vector((x,y,0)).normalized()
    q+=direction*fold
    return q

def trouser_shape(p,side):
    x,y,z=p
    gate=smooth(.228,.266,z)*(1-smooth(.455,.485,z))
    if gate==0: return p.copy()
    center=Vector((side*.082,.007,z)); radial=p-center; radial.z=0
    length=radial.length
    if length<1e-8: return p.copy()
    direction=radial/length
    # Broad knee/calf ease and a single front-diagonal turn below the knee.
    ease=.0135*exp(-((z-.330)/.080)**2)+.0055*exp(-((z-.270)/.035)**2)
    outer=smooth(-.4,.6,direction.x*side)
    ease*=.75+.25*outer
    front=max(0,-direction.y)
    crease_z=.320+.16*(x-side*.082)*side
    fold=-.0042*exp(-((z-crease_z)/.013)**2)*front**2
    angle=math.atan2(direction.x*side,-direction.y)
    diagonal=.57+.7*(z-.34)+side*.06
    hanging=(-.0052*exp(-((angle-diagonal)/.19)**2)+.0025*exp(-((angle-diagonal-.30)/.23)**2))
    hanging*=exp(-((z-(.350+side*.009))/.075)**4)
    q=p+direction*(ease+fold+hanging)*gate
    q.y-=.0035*front*exp(-((z-.36)/.06)**2)*gate
    return q

def write_export(root,material_names):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root]+list(root.children_recursive): obj.select_set(True)
    bpy.context.view_layer.objects.active=root; saved=[]
    for name in material_names:
        material=bpy.data.materials[name]; bsdf=material.node_tree.nodes['Principled BSDF']
        for link in list(bsdf.inputs['Base Color'].links):
            saved.append((material,link.from_socket,bsdf.inputs['Base Color'])); material.node_tree.links.remove(link)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},global_scale=1,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=False,
        mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,primary_bone_axis='Y',secondary_bone_axis='X',colors_type='LINEAR',path_mode='COPY',embed_textures=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'traveler.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,
        export_materials='EXPORT',export_extras=True,export_skins=True,export_animations=False,export_vertex_color='ACTIVE',export_all_vertex_colors=True)
    for material,a,b in saved: material.node_tree.links.new(a,b)
    bpy.ops.object.select_all(action='DESELECT'); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))

def build():
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); root=bpy.data.objects['TravelerRoot']
    objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    before={n:mesh_state(o) for n,o in objects.items()}; contract=object_contract(root)
    material_names=sorted({m.name for o in objects.values() for m in o.data.materials})
    materials={n:material_state(bpy.data.materials[n]) for n in material_names}
    hair_records=hair_shapes(objects['Head_Hair_Indigo'],objects['Head_Hair_MidnightBlue'])
    for name in sorted(TARGETS-{'Head_Hair_Indigo','Head_Hair_MidnightBlue'}):
        obj=objects[name]; inv=obj.matrix_world.inverted(); side=-1 if name.endswith('_L') else 1
        for vertex in obj.data.vertices:
            p=unproportion(obj.matrix_world@vertex.co)
            if name.startswith('Sleeve_'): q=sleeve_shape(p,side)
            elif name.startswith('Trouser_'): q=trouser_shape(p,side)
            else: q=tunic_shape(p)
            if (q-p).length_squared>1e-16: vertex.co=inv@proportion(q)
        obj.data.update()
    after={n:mesh_state(o) for n,o in objects.items()}; rows=[]
    for name in objects:
        a,b=before[name],after[name]
        if name in TARGETS:
            for key in a:
                if key not in ['coordinates','normals']: assert a[key]==b[key],name+' changed '+key
        else: assert a==b,name+' changed protected data'
        changed=[i for i,(p,q) in enumerate(zip(a['coordinates'],b['coordinates'])) if p!=q]
        delta=max([(Vector(a['coordinates'][i])-Vector(b['coordinates'][i])).length for i in changed] or [0])
        rows.append({'mesh':name,'is_target':name in TARGETS,'changed_vertices':len(changed),'maximum_local_displacement':delta,
                     'protected_channels_sha256':digest({k:v for k,v in a.items() if name not in TARGETS or k not in ['coordinates','normals']})})
    # Hair mesh also includes brows/lashes. Their exact coordinates, topology,
    # corner colours and UVs are unchanged; target channels already preserve all
    # topology/UV/colour and the protected sub-island coordinates prove the rest.
    hair_ids={i for row in hair_records for i in row['vertices']}
    protected_hair=[i for i in range(len(before['Head_Hair_Indigo']['coordinates'])) if i not in hair_ids]
    for i in protected_hair: assert before['Head_Hair_Indigo']['coordinates'][i]==after['Head_Hair_Indigo']['coordinates'][i]
    assert contract==object_contract(root),'object/bone/pivot/attachment contract changed'
    for name in material_names: assert materials[name]==material_state(bpy.data.materials[name]),name
    triangles=0
    for obj in objects.values(): obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
    assert triangles==77132,triangles
    preservation={'passed':True,'source_sha256':source_hash,'targets':sorted(TARGETS),'rows':rows,
                  'protected_mesh_count':len(objects)-len(TARGETS),'protected_hair_vertices':protected_hair,
                  'object_contract_sha256':digest(contract),'object_bone_pivot_exact_match':True,
                  'all_weights_topology_uv_color_materials_exact':True,'material_count':len(material_names),
                  'scope':'Coordinates/normals only on 7 targets; all other channels exact; protected scalp/brow/lash islands exact.'}
    (OUT/'v8-preservation-verification.json').write_text(json.dumps(preservation,indent=2),encoding='utf-8')
    (OUT/'hair-curve-records.json').write_text(json.dumps(hair_records,indent=2),encoding='utf-8')
    write_export(root,material_names)
    manifest={'version':9,'source':str(SOURCE.relative_to(ROOT)),'source_sha256':source_hash,'triangles':triangles,
              'mesh_renderers':62,'skinned_meshes':28,'armatures':4,'bones':12,'material_count':29,
              'material_names':material_names,'changes':'Irregular lifted flattened hair locks; softer tapered shoulder/sleeve volumes; side/back coat hem ease; loose knee/calf cloth. Face/eyes and all rigs, weights, soles, hands and accessories retained.',
              'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'traveler.blend',OUT/'traveler.fbx',OUT/'traveler.glb']}}
    (OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
    print('SILHOUETTE_V9_EXPORTED '+json.dumps({'triangles':triangles,'protected_meshes':len(objects)-len(TARGETS)}),flush=True)

def render():
    for version,path in [('v8',SOURCE),('v9',OUT/'traveler.blend')]:
        if '--candidate-only' in ARGS and version=='v8': continue
        bpy.ops.wm.open_mainfile(filepath=str(path)); scene=bpy.context.scene
        scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=8; scene.cycles.use_denoising=True
        scene.render.threads_mode='FIXED'; scene.render.threads=4
        scene.render.resolution_x=512; scene.render.resolution_y=640; scene.render.resolution_percentage=100
        camera=bpy.data.objects['PREVIEW_Camera']; scene.camera=camera
        for name,location in [('three-quarter',(2.1,-4,1.50)),('profile',(4,-.12,1.15))]:
            camera.location=location; camera.rotation_euler=(Vector((0,-.015,.71))-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.type='ORTHO'; camera.data.ortho_scale=1.48
            scene.render.filepath=str(OUT/(version+'-'+name+'.png')); bpy.ops.render.render(write_still=True)

if '--inspect' in ARGS: inspect()
elif '--render-only' in ARGS: render()
else:
    build()
    if '--render' in ARGS: render()
