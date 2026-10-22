"""Independent v14 head-shape candidate from frozen character-v9.

CPU only, at most four threads. Writes character-v10 BLEND/FBX and identical
baseline/candidate studio-camera previews. No Unity or GLB writes.
"""
import ast,bpy,hashlib,importlib.util,json,math,os,sys,time
from pathlib import Path
from mathutils import Vector
from math import sin,cos,pi,exp,sqrt
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v9/traveler.blend'
OUT=ROOT/'art/generated/character-v10'
OUT.mkdir(parents=True,exist_ok=True)
ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
FACE_LEVELS=[(.932,.012,.020,-.023),(.940,.038,.036,-.021),(.953,.061,.052,-.017),(.975,.083,.072,-.011),(1.006,.103,.089,-.006),(1.045,.119,.105,-.002),(1.081,.128,.111,.001),(1.119,.127,.103,.008),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]
for filename,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract'}),('build_traveler_v6.py',{'smooth','proportion','unproportion','face_section'}),('build_traveler_v8.py',{'components','retained_geometry','tube_append','complexion','paint'})]:
    tree=ast.parse((ROOT/'art/blender'/filename).read_text(encoding='utf-8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),filename,'exec'))
NEW_LEVELS=[(.932,.019,.025,-.021),(.940,.039,.038,-.018),(.953,.060,.053,-.013),(.975,.083,.073,-.007),(1.006,.108,.090,-.002),(1.045,.121,.102,.0015),(1.081,.127,.108,.002),(1.119,.126,.103,.0085),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]
def slope(index,dim):
    if index==0:return (NEW_LEVELS[1][dim]-NEW_LEVELS[0][dim])/(NEW_LEVELS[1][0]-NEW_LEVELS[0][0])
    if index==len(NEW_LEVELS)-1:return (NEW_LEVELS[-1][dim]-NEW_LEVELS[-2][dim])/(NEW_LEVELS[-1][0]-NEW_LEVELS[-2][0])
    a,b,c=NEW_LEVELS[index-1:index+2];h0=b[0]-a[0];h1=c[0]-b[0];d0=(b[dim]-a[dim])/h0;d1=(c[dim]-b[dim])/h1
    if d0*d1<=0:return 0.
    w0=2*h1+h0;w1=h1+2*h0;return (w0+w1)/(w0/d0+w1/d1)
def section(z):
    k=next((i for i in range(len(NEW_LEVELS)-1) if z<=NEW_LEVELS[i+1][0]),len(NEW_LEVELS)-2)
    a,b=NEW_LEVELS[k],NEW_LEVELS[k+1];h=b[0]-a[0];t=max(0,min(1,(z-a[0])/h));out=[]
    for d in [1,2,3]:out.append((2*t**3-3*t*t+1)*a[d]+(t**3-2*t*t+t)*h*slope(k,d)+(-2*t**3+3*t*t)*b[d]+(t**3-t*t)*h*slope(k+1,d))
    mix=smooth(1.142,1.170,z);return [a*(1-mix)+b*mix for a,b in zip(out,face_section(z))]
def sculpt(x,z):
    pair=lambda cx,sx,cz,sz:(exp(-((x-cx)/sx)**2)+exp(-((x+cx)/sx)**2))*exp(-((z-cz)/sz)**2)
    cheek=.0062*pair(.064,.036,1.048,.028)+.0025*pair(.061,.030,1.069,.017)
    socket=.0028*pair(.049,.033,1.088,.021)
    nose=.0048*exp(-(x/.017)**2-((z-1.068)/.030)**2)+.0102*exp(-(x/.020)**2-((z-1.043)/.0145)**2)+.0030*pair(.016,.010,1.033,.009)
    muzzle=.0026*exp(-(x/.036)**2-((z-1.012)/.020)**2)
    lips=.0020*pair(.008,.011,1.016,.0048)+.0030*exp(-(x/.020)**2-((z-1.006)/.0052)**2)
    philtrum=.0006*exp(-(x/.005)**2-((z-1.026)/.007)**2)
    fold=.00045*exp(-(x/.025)**2-((z-.994)/.007)**2)
    chin=.0025*exp(-(x/.040)**2-((z-.976)/.020)**2)
    brow=.0015*pair(.048,.033,1.118,.017)
    return socket+philtrum+fold-cheek-nose-muzzle-lips-chin-brow
def surface(a,z):
    rx,ry,cy=section(z);x=rx*sin(a);f=cos(a)
    return Vector((x,cy-ry*f+smooth(0,.35,max(0,f))*sculpt(x,z),z))
def surface_normal(a,z):
    # Full theta/z differential, including the back. No hard front-normal switch.
    h=.00002
    tangent=proportion(surface(a+h,z))-proportion(surface(a-h,z))
    vertical=proportion(surface(a,z+h))-proportion(surface(a,z-h))
    return tangent.cross(vertical).normalized()
def face_y(x,z):
    rx,ry,cy=section(z);f=sqrt(max(0,1-(x/rx)**2))
    return cy-ry*f+smooth(0,.35,f)*sculpt(x,z)
def face_normal(x,z):
    h=.00002
    a=proportion(Vector((x+h,face_y(x+h,z),z)))-proportion(Vector((x-h,face_y(x-h,z),z)))
    b=proportion(Vector((x,face_y(x,z+h),z+h)))-proportion(Vector((x,face_y(x,z-h),z-h)))
    return a.cross(b).normalized()
def eye_edge(side,t,upper=True,outer=0.):
    x=side*(.048-.0306-.0085*outer+(.0612+.017*outer)*t)
    bump=max(0,sin(pi*t));z=1.0868+.0018*(t-.5)
    if upper:z+=(.0168*(1+side*.025)+.0086*outer)*bump**.82
    else:z-=(.0103+.007*outer)*bump**.92
    return x,z
def inside_eye(x,z,expand=.0012):
    side=-1 if x<0 else 1;t=(side*x-(.048-.0306))/.0612
    if not 0<t<1:return False
    _,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False)
    return low-expand<z<up+expand
def ocular_depth(side,x,z):
    t=max(0,min(1,(side*x-(.048-.0306))/.0612));center=1.0868+.0018*(t-.5)
    _,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False);height=max(.00001,up-center if z>=center else center-low)
    horizontal=(2*t-1)**2;r2=horizontal+(1-horizontal)*min(1,((z-center)/height)**2)
    return .00065+.00215*(1-r2)
def clip_eye(side,ex,ez,dx,dz):
    if inside_eye(ex+dx,ez+dz,-.00016):return 1.
    low,high=0.,1.
    for _ in range(24):
        mid=(low+high)/2
        if inside_eye(ex+dx*mid,ez+dz*mid,-.00016):low=mid
        else:high=mid
    return low
def set_geometry(obj,verts,faces,normals=None):
    old=obj.data;mats=list(old.materials);mesh=bpy.data.meshes.new(obj.name+'_HeadV10');inv=obj.matrix_world.inverted()
    mesh.from_pydata([tuple(inv@Vector(p)) for p in verts],[],faces);mesh.update()
    for m in mats:mesh.materials.append(m)
    for p in mesh.polygons:p.use_smooth=True
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        p=Vector(verts[loop.vertex_index]);uv.data[loop.index].uv=(p.x*3+.5,p.z*2-1.7)
    obj.data=mesh
    if normals:
        basis=obj.matrix_world.to_3x3().transposed();out=[]
        for v,n in zip(mesh.vertices,normals):
            if n is None:out.append(tuple(v.normal));continue
            if isinstance(n,dict):
                target=(basis@Vector(n['target'])).normalized();out.append(tuple((v.normal*(1-n['blend'])+target*n['blend']).normalized()))
            else:out.append(tuple((basis@Vector(n)).normalized()))
        mesh.normals_split_custom_set_from_vertices(out)
    if old.users==0:bpy.data.meshes.remove(old)
def build_face(objects):
    obj=objects['Head_Face_PorcelainCream']
    verts,faces=retained_geometry(obj,lambda ids,p:len(ids)<=400 and (max(v.z for v in p)<1.0 or all(abs(v.x)>.10 for v in p)))
    assert len(verts)==758,'Neck and both ears must remain the 758 original vertices'
    normals=[None]*len(verts);start=len(verts);rows=80;around=120
    for j in range(rows):
        z=.932+(1.224-.932)*j/(rows-1)
        for i in range(around):
            a=2*pi*i/around;verts.append(tuple(proportion(surface(a,z))));normals.append(tuple(surface_normal(a,z)))
    faces.extend([tuple(start+i for i in range(around-1,-1,-1)),tuple(start+(rows-1)*around+i for i in range(around))])
    for j in range(rows-1):
        for i in range(around):
            ids=(start+j*around+i,start+j*around+(i+1)%around,start+(j+1)*around+(i+1)%around,start+(j+1)*around+i)
            p=sum((unproportion(Vector(verts[k])) for k in ids),Vector())/4
            if p.y<-.04 and inside_eye(p.x,p.z):continue
            faces.append(ids)
    for side in [-1,1]:
        for upper in [True,False]:
            begin=len(verts);count=48;bands=7
            for row in range(bands):
                r=row/(bands-1)
                for k in range(count+1):
                    t=k/count;x,z=eye_edge(side,t,upper,r)
                    lift=(.0014 if upper else .00065)*sin(pi*t)**.75*(1-r)**1.2
                    verts.append(tuple(proportion(Vector((x,face_y(x,z)-lift-.00006,z)))))
                    normals.append({'target':list(face_normal(x,z)),'blend':smooth(.35,1,r)})
            for row in range(bands-1):
                for k in range(count):
                    a=begin+row*(count+1)+k;f=(a,a+1,a+count+2,a+count+1)
                    faces.append(tuple(reversed(f)) if (side>0)!=upper else f)
    set_geometry(obj,verts,faces,normals)
    for name in ['Ivory','AmberRim','Chestnut','Pupil','Catchlight']:
        verts=[];faces=[]
        for side in [-1,1]:
            start=len(verts);ex=side*.048+.00055;ez=1.0883
            if name=='Ivory':
                ex=side*.048;ez=1.087
                verts.append(tuple(proportion(Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez),ez)))))
                count=72;ring_count=6
                for r in [.16,.32,.50,.67,.84,1.]:
                    for k in range(count):
                        a=2*pi*k/count;t=(1+side*cos(a))/2;x,z=eye_edge(side,t,sin(a)>=0);x=ex+(x-ex)*r;z=ez+(z-ez)*r
                        verts.append(tuple(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z),z)))))
            else:
                rx,rz,depth={'AmberRim':(.0130,.0127,.00010),'Chestnut':(.0117,.0115,.00017),'Pupil':(.0053,.0055,.00025),'Catchlight':(.0017,.0018,.00034)}[name]
                if name=='Catchlight':ex-=.0035;ez+=.0043
                verts.append(tuple(proportion(Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez)-depth,ez)))))
                count=40;ring_count=5
                for r in [.2,.4,.6,.8,1.]:
                    for k in range(count):
                        a=2*pi*k/count;dx=rx*cos(a);dz=rz*sin(a);clip=clip_eye(side,ex,ez,dx,dz);x=ex+dx*r*clip;z=ez+dz*r*clip
                        verts.append(tuple(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z)-depth,z)))))
            for k in range(count):faces.append((start,start+1+k,start+1+(k+1)%count))
            for row in range(ring_count-1):
                for k in range(count):
                    a=start+1+row*count+k;b=start+1+row*count+(k+1)%count;faces.append((a,a+count,b+count,b))
        set_geometry(objects['Head_Eye_'+name],verts,faces)
    # This historical object name now denotes the lower-lid skin margin.
    verts=[];faces=[]
    for side in [-1,1]:
        start=len(verts)
        for row in [0,1]:
            for k in range(49):
                t=k/48;x,z=eye_edge(side,t,False);z-=row*.00065*sin(pi*t)
                verts.append(tuple(proportion(Vector((x,face_y(x,z)-.00072,z)))))
        for k in range(48):
            a=start+k;f=(a,a+1,a+50,a+49);faces.append(tuple(reversed(f)) if side>0 else f)
    set_geometry(objects['Head_Face_NoseCream'],verts,faces)
    verts=[];faces=[]
    for row in [0,1]:
        for k in range(57):
            t=k/56;x=-.028+.056*t;z=1.0108+.0030*abs(x/.028)**1.6+.00065*x/.028
            z+=(row-.5)*(.00014+.0010*sin(pi*t)**.7)
            verts.append(tuple(proportion(Vector((x,face_y(x,z)-.00036,z)))))
    for k in range(56):faces.append((k,k+1,k+58,k+57))
    set_geometry(objects['QuietSmile'],verts,faces)
    obj=objects['Head_Face_RoseCheeks'];verts,faces=retained_geometry(obj,lambda ids,p:all(abs(v.x)>.10 for v in p))
    assert len(verts)==200,'Both original inner-ear components must survive'
    for side in [-1,1]:
        points=[]
        for k in range(11):
            t=k/10;x=side*(.009+.009*t);z=1.032+.0010*sin(pi*t)
            points.append((x,face_y(x,z)-.00024,z))
        tube_append(verts,faces,points,[.00008+.00028*sin(pi*k/10) for k in range(11)],5)
    set_geometry(obj,verts,faces)
def build_hair(objects):
    spec=importlib.util.spec_from_file_location('traveler_v10_hair',ROOT/'art/blender/traveler_v10_hair.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    h=module.build_hair_geometry();obj=objects['Head_Hair_Indigo']
    verts,faces=retained_geometry(obj,lambda ids,p:len(ids)==640)
    assert len(verts)==640,'Preserve original fitting scalp cap'
    start=len(verts);verts.extend(tuple(proportion(Vector(v))) for v in h['verts']);faces.extend(tuple(start+i for i in f) for f in h['faces'])
    for side in [-1,1]:
        points=[];radii=[]
        for k in range(41):
            t=k/40;x,z=eye_edge(side,t,True);points.append((x,face_y(x,z)-.00155,z));radii.append(.00012+.00037*sin(pi*t)**.75)
        tube_append(verts,faces,points,radii,5)
        points=[];radii=[]
        for k in range(33):
            t=k/32;x=side*(.048-.029+.058*t)
            # A relaxed attentive arch; mild left/right variation, never raised into a startled pose.
            z=1.123+.0038*sin(pi*t)+.0016*(1-t)+side*.0008*sin(pi*t)
            points.append((x,face_y(x,z)-.00135,z));radii.append(.00012+.00105*sin(pi*t)**.7)
        tube_append(verts,faces,points,radii,6)
    set_geometry(obj,verts,faces)
    set_geometry(objects['Head_Hair_MidnightBlue'],[tuple(proportion(Vector(v))) for v in h['high_verts']],h['high_faces'])
    return h['metadata']
def build_blinks(objects):
    saved={}
    for side,label in [(-1,'L'),(1,'R')]:
        pivot=bpy.data.objects['Blink_'+label];saved[label]=pivot.scale.copy();pivot.scale=(1,1,1);bpy.context.view_layer.update()
        ex=side*.048;ez=1.087;verts=[tuple(proportion(Vector((ex,face_y(ex,ez)-.0088,ez))))];faces=[];normals=[None]
        for r in [.17,.34,.51,.68,.84,1.]:
            for k in range(64):
                a=2*pi*k/64;x=ex+.0405*r*cos(a);z=ez+.0285*r*sin(a)
                y=face_y(x,z)-.00008-.0087*max(0,1-r*r)**1.8
                verts.append(tuple(proportion(Vector((x,y,z)))));normals.append({'target':list(face_normal(x,z)),'blend':smooth(.55,1,r)})
        for k in range(64):faces.append((0,1+k,1+(k+1)%64))
        for row in range(5):
            for k in range(64):
                a=1+row*64+k;b=1+row*64+(k+1)%64;faces.append((a,a+64,b+64,b))
        set_geometry(objects['Blink_'+label+'_LidCover'],verts,faces,normals)
        verts=[];faces=[];points=[];radii=[]
        for k in range(33):
            t=k/32;x=ex-.030+.060*t;z=ez-.0036*sin(pi*t);r=sqrt(((x-ex)/.0405)**2+((z-ez)/.0285)**2)
            y=face_y(x,z)-.00008-.0087*max(0,1-r*r)**1.8-.00038
            points.append((x,y,z));radii.append(.00011+.00042*sin(pi*t)**.7)
        tube_append(verts,faces,points,radii,5);set_geometry(objects['Blink_'+label+'_ClosedLash'],verts,faces)
    for label,scale in saved.items():bpy.data.objects['Blink_'+label].scale=scale
    bpy.context.view_layer.update()
def export_fbx(root,materials):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root]+list(root.children_recursive):obj.select_set(True)
    bpy.context.view_layer.objects.active=root;saved=[]
    for name in materials:
        material=bpy.data.materials[name];bsdf=material.node_tree.nodes.get('Principled BSDF')
        for link in list(bsdf.inputs['Base Color'].links):saved.append((material,link.from_socket,bsdf.inputs['Base Color']));material.node_tree.links.remove(link)
    try:bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,primary_bone_axis='Y',secondary_bone_axis='X',colors_type='LINEAR',path_mode='COPY',embed_textures=True)
    finally:
        for material,a,b in saved:material.node_tree.links.new(a,b)
    bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))
def build():
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    root=bpy.data.objects['TravelerRoot'];objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    targets={o.name for o in bpy.data.objects['Head'].children_recursive if o.type=='MESH'}
    before={n:mesh_state(o) for n,o in objects.items() if n not in targets};contract=object_contract(root)
    materials=sorted({m.name for o in objects.values() for m in o.data.materials});material_before={n:material_state(bpy.data.materials[n]) for n in materials}
    build_face(objects);hair=build_hair(objects);build_blinks(objects)
    for name in targets:paint(objects[name])
    protected=[]
    for name,state in before.items():assert state==mesh_state(objects[name]),name+' changed outside the head';protected.append({'mesh':name,'unchanged':True,'sha256':digest(state)})
    assert contract==object_contract(root),'Object/bone/pivot transforms or attachments changed'
    for name in materials:assert material_before[name]==material_state(bpy.data.materials[name]),'Material changed '+name
    triangles=0
    for o in objects.values():o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    assert triangles<120000,triangles
    export_fbx(root,materials)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash,'Frozen v9 changed'
    manifest={'revision':'character-v10','gameCandidate':'v14','source':'art/generated/character-v9/traveler.blend','sourceSHA256':source_hash,'triangles':triangles,'meshRenderers':len(objects),'targets':sorted(targets),'protectedMeshes':protected,'objectBonePivotContractUnchanged':True,'materialGraphsUnchanged':True,'skinWeightsOutsideHeadUnchanged':True,'headHasSkinWeights':False,'headStyle':'Open, gently attentive almond eyes; softer continuous cheek/jaw/nose; asymmetric restrained mouth and brows; layered broad-root hair masses with thin irregular tips. Original dark-brown/teal identity.','eyeChanges':{'openingWidth':.0612,'approxOpeningHeight':.0271,'irisDiameter':.026,'pupilDiameter':.0106,'shallowCapMaxDepth':.0028},'normalMethod':'Continuous full-theta/z derivative over head shell; eyelid transition blended into that surface, no cos-threshold normal switch.','hair':hair,'blinkInterface':'Names, parents, original object transforms and .001..1 XY scale interface preserved; lid covers and closed lashes regenerated to match new opening.','limits':['Candidate only; no normal Unity acceptance or attribution to lighting.','No GLB export or full interchange audit at this stage.','Preview studio lights and fixed cameras compare geometry only; they do not reproduce current Unity gameplay lighting.','Existing blink pivot centers are retained; intermediate/full blink coverage still requires visual runtime checks.'],'files':{},'aestheticObjectiveAchieved':False}
    for file in [OUT/'traveler.blend',OUT/'traveler.fbx']:manifest['files'][file.name]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size}
    (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('HEAD_V10_BUILT '+json.dumps({'triangles':triangles,'protected':len(protected),'targets':len(targets),'pid':os.getpid()}),flush=True)
def preview_conditions(scene,camera):
    return {'cameraMatrix':[list(r) for r in camera.matrix_world],'orthoScale':camera.data.ortho_scale,'engine':scene.render.engine,'samples':scene.cycles.samples,'seed':scene.cycles.seed,'device':scene.cycles.device,'threads':scene.render.threads,'resolution':[scene.render.resolution_x,scene.render.resolution_y], 'lights':{o.name:{'matrix':[list(r) for r in o.matrix_world],'type':o.data.type,'energy':o.data.energy,'color':list(o.data.color),'size':getattr(o.data,'size',None)} for o in bpy.data.objects if o.type=='LIGHT'},'world':scene.world.name if scene.world else None,'exposure':scene.view_settings.look+':'+str(scene.view_settings.exposure),'viewTransform':scene.view_settings.view_transform,'gamma':scene.view_settings.gamma}
def render():
    records=[]
    for version,file in [('baseline',SOURCE),('candidate',OUT/'traveler.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);scene=bpy.context.scene
        scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=17;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
        scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
        camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera
        for name,position in [('three-quarter',(1.8,-3.7,1.45)),('profile',(4,-.12,1.23))]:
            target=proportion(Vector((0,-.002,1.105)));camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.56
            bpy.context.view_layer.update();scene.render.filepath=str(OUT/(version+'-'+name+'.png'));conditions=preview_conditions(scene,camera)
            bpy.ops.render.render(write_still=True);records.append({'version':version,'view':name,'file':version+'-'+name+'.png','conditions':conditions})
            print('HEAD_V10_PREVIEW '+version+' '+name,flush=True)
    for view in ['three-quarter','profile']:
        pair=[r for r in records if r['view']==view];assert pair[0]['conditions']==pair[1]['conditions'],'Preview camera/light settings differ'
    (OUT/'preview-conditions.json').write_text(json.dumps({'sameCameraAndLights':True,'cpuOnly':True,'geometryComparisonOnly':True,'records':records},indent=2),encoding='utf-8')
print('HEAD_V10_PROCESS '+json.dumps({'pid':os.getpid(),'cpuThreadsMax':4,'source':str(SOURCE),'output':str(OUT)}),flush=True)
if '--render-only' not in sys.argv:build()
render()
