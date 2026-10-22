"""Continuous facial study, derived from frozen v7; body/rig are protected.
Blender CPU only. New outputs stay in character-v8, no Unity writes.
-- --render renders identical frontal/three-quarter/profile baseline comparisons.
"""
import bpy,ast,json,hashlib,math,sys
from pathlib import Path
from mathutils import Vector
from math import sin,cos,pi,exp,sqrt
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v7/traveler.blend'
OUT=ROOT/'art/generated/character-v8'; OUT.mkdir(parents=True,exist_ok=True)
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []

# Reuse only pure data/fingerprint helpers, never execute old build entrypoints.
for filename,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract'}),
                       ('build_traveler_v6.py',{'smooth','proportion','unproportion','face_section'})]:
    tree=ast.parse((ROOT/'art/blender'/filename).read_text(encoding='utf-8'))
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=selected,type_ignores=[]),filename,'exec'))
ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
FACE_LEVELS=[(.932,.012,.020,-.023),(.940,.038,.036,-.021),(.953,.061,.052,-.017),(.975,.083,.072,-.011),(1.006,.103,.089,-.006),(1.045,.119,.105,-.002),(1.081,.128,.111,.001),(1.119,.127,.103,.008),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]
NEW_LEVELS=[(.932,.012,.020,-.023),(.940,.033,.032,-.020),(.953,.055,.048,-.015),(.975,.076,.068,-.009),(1.006,.101,.088,-.004),(1.045,.120,.103,0),(1.081,.128,.110,.001),(1.119,.127,.103,.008),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]

def scalar_slope(index,dim):
    levels=NEW_LEVELS
    if index==0: return (levels[1][dim]-levels[0][dim])/(levels[1][0]-levels[0][0])
    if index==len(levels)-1: return (levels[-1][dim]-levels[-2][dim])/(levels[-1][0]-levels[-2][0])
    a,b,c=levels[index-1:index+2]; h0=b[0]-a[0]; h1=c[0]-b[0]
    d0=(b[dim]-a[dim])/h0; d1=(c[dim]-b[dim])/h1
    if d0*d1<=0: return 0.
    w0=2*h1+h0; w1=h1+2*h0
    return (w0+w1)/(w0/d0+w1/d1)

def section(z):
    k=next((i for i in range(len(NEW_LEVELS)-1) if z<=NEW_LEVELS[i+1][0]),len(NEW_LEVELS)-2)
    a,b=NEW_LEVELS[k],NEW_LEVELS[k+1]; h=b[0]-a[0]; t=max(0,min(1,(z-a[0])/h))
    result=[]
    for dim in [1,2,3]:
        value=(2*t**3-3*t*t+1)*a[dim]+(t**3-2*t*t+t)*h*scalar_slope(k,dim)+(-2*t**3+3*t*t)*b[dim]+(t**3-t*t)*h*scalar_slope(k+1,dim)
        result.append(value)
    # Retain the existing scalp fit above the visible forehead.
    mix=smooth(1.142,1.170,z); old=face_section(z)
    return [a*(1-mix)+b*mix for a,b in zip(result,old)]

def sculpt(x,z):
    pair=lambda cx,sx,cz,sz: (exp(-((x-cx)/sx)**2)+exp(-((x+cx)/sx)**2))*exp(-((z-cz)/sz)**2)
    cheeks=.0077*pair(.067,.034,1.043,.026)
    malar=.0032*pair(.064,.028,1.064,.014)
    sockets=.0058*pair(.049,.026,1.087,.016)
    bridge=.0069*exp(-(x/.016)**2-((z-1.069)/.029)**2)
    tip=.0138*exp(-(x/.018)**2-((z-1.043)/.013)**2)
    wings=.0042*pair(.015,.0095,1.033,.009)
    columella=.0021*exp(-(x/.006)**2-((z-1.032)/.006)**2)
    muzzle=.0028*exp(-(x/.033)**2-((z-1.012)/.020)**2)
    upper_lip=.0017*pair(.0075,.010,1.015,.0042)
    lower_lip=.0025*exp(-(x/.018)**2-((z-1.006)/.0044)**2)
    philtrum=.0008*exp(-(x/.0045)**2-((z-1.025)/.007)**2)
    labial_fold=.00065*exp(-(x/.022)**2-((z-.994)/.006)**2)
    chin=.0028*exp(-(x/.032)**2-((z-.976)/.020)**2)
    brow=.0017*pair(.048,.031,1.111,.014)
    return sockets+philtrum+labial_fold-cheeks-malar-bridge-tip-wings-columella-muzzle-upper_lip-lower_lip-chin-brow

def face_y(x,z):
    rx,ry,cy=section(z); f=sqrt(max(0,1-(x/rx)**2))
    return cy-ry*f+smooth(0,.35,f)*sculpt(x,z)

def face_normal(x,z):
    h=.00008
    a=proportion(Vector((x+h,face_y(x+h,z),z)))-proportion(Vector((x-h,face_y(x-h,z),z)))
    b=proportion(Vector((x,face_y(x,z+h),z+h)))-proportion(Vector((x,face_y(x,z-h),z-h)))
    return a.cross(b).normalized()

def eye_edge(side,t,upper=True,outer=0.):
    # t runs from inner to outer canthus, a shallow tilt and different lid curves.
    x=side*(.048+(-.0255-.006*outer)+( .051+.012*outer)*t)
    bump=max(0,sin(pi*t))
    z=1.086+.0015*(t-.5)
    z+=(.0122+.0062*outer)*bump**.82 if upper else -(.0075+.0055*outer)*bump**.91
    return x,z

def inside_eye(x,z,expand=.0012):
    side=-1 if x<0 else 1; q=side*x
    t=(q-(.048-.0255))/(.051)
    if not 0<t<1: return False
    _,up=eye_edge(side,t,True); _,down=eye_edge(side,t,False)
    return down-expand<z<up+expand

def ocular_depth(side,x,z):
    """Every ocular layer shares the same shallow cap and rim depth."""
    t=max(0,min(1,(side*x-(.048-.0255))/.051))
    center_z=1.086+.0015*(t-.5)
    _,upper=eye_edge(side,t,True); _,lower=eye_edge(side,t,False)
    height=max(.00001,upper-center_z if z>=center_z else center_z-lower)
    horizontal=(2*t-1)**2
    r2=horizontal+(1-horizontal)*min(1,((z-center_z)/height)**2)
    return .0006+.0018*(1-r2)

def clip_eye_direction(side,ex,ez,dx,dz):
    """Clip the iris's circular arc where it passes under the almond lids."""
    if inside_eye(ex+dx,ez+dz,-.00012): return 1.
    low,high=0.,1.
    for _ in range(24):
        mid=(low+high)/2
        if inside_eye(ex+dx*mid,ez+dz*mid,-.00012): low=mid
        else: high=mid
    return low

def components(obj):
    adjacency=[[] for v in obj.data.vertices]
    for e in obj.data.edges:
        a,b=e.vertices; adjacency[a].append(b); adjacency[b].append(a)
    seen=set(); result=[]
    for seed in range(len(adjacency)):
        if seed in seen: continue
        island=[]; pending=[seed]; seen.add(seed)
        while pending:
            i=pending.pop(); island.append(i)
            for n in adjacency[i]:
                if n not in seen: seen.add(n); pending.append(n)
        result.append(island)
    return result

def retained_geometry(obj,keep):
    retained=set()
    for indices in components(obj):
        points=[unproportion(obj.matrix_world@obj.data.vertices[i].co) for i in indices]
        if keep(indices,points): retained.update(indices)
    indices=sorted(retained); remap={old:new for new,old in enumerate(indices)}
    verts=[tuple(obj.matrix_world@obj.data.vertices[i].co) for i in indices]
    faces=[tuple(remap[i] for i in p.vertices) for p in obj.data.polygons if all(i in retained for i in p.vertices)]
    return verts,faces

def replace_geometry(obj,verts,faces,custom_normals=None):
    mats=list(obj.data.materials); old=obj.data
    mesh=bpy.data.meshes.new(obj.name+'_ContinuousFaceV8'); inv=obj.matrix_world.inverted()
    mesh.from_pydata([tuple(inv@Vector(p)) for p in verts],[],faces); mesh.update()
    for m in mats: mesh.materials.append(m)
    for p in mesh.polygons: p.use_smooth=True
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        w=Vector(verts[loop.vertex_index]); uv.data[loop.index].uv=(w.x*3+.5,w.z*2-1.7)
    obj.data=mesh
    if custom_normals:
        basis=obj.matrix_world.to_3x3().transposed()
        normals=[tuple((basis@Vector(n)).normalized()) if n else tuple(v.normal) for v,n in zip(mesh.vertices,custom_normals)]
        mesh.normals_split_custom_set_from_vertices(normals)
    if old.users==0: bpy.data.meshes.remove(old)

def tube_append(verts,faces,points,radii,sides=6):
    start=len(verts); pts=list(map(Vector,points)); previous=None
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        a=tangent.cross(Vector((0,1,0))).normalized()
        b=tangent.cross(a).normalized(); radius=radii[i] if isinstance(radii,list) else radii
        for j in range(sides): verts.append(tuple(proportion(p+radius*(a*cos(2*pi*j/sides)+b*sin(2*pi*j/sides)))))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=start+i*sides+j; b=start+i*sides+(j+1)%sides; faces.append((a,b,b+sides,a+sides))

def complexion(p,material):
    x,y,z=p; front=smooth(.015,.065,-y); color=Vector((.982,.973,.962))
    cheeks=(exp(-((x-.064)/.031)**2)+exp(-((x+.064)/.031)**2))*exp(-((z-1.049)/.025)**2)*front
    nose=exp(-(x/.024)**2-((z-1.041)/.018)**2)*front
    lips=exp(-(x/.027)**4-((z-1.011)/.008)**2)*front
    eyelid=(exp(-((x-.048)/.027)**2)+exp(-((x+.048)/.027)**2))*exp(-((z-1.105)/.009)**2)*front
    color-=Vector((.003,.078,.105))*cheeks
    color-=Vector((.002,.035,.052))*nose
    color-=Vector((.010,.046,.044))*lips
    color-=Vector((.012,.022,.026))*eyelid
    if material=='Traveler_Face_NoseCream': color*=.965
    return tuple(max(.72,min(1,c)) for c in color)+(1.,)

def paint(obj):
    material=obj.data.materials[0].name
    attr=obj.data.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='CORNER')
    colors=[]
    for v in obj.data.vertices:
        p=unproportion(obj.matrix_world@v.co)
        colors.append(complexion(p,material) if 'Face_' in material else (1,1,1,1))
    for loop in obj.data.loops: attr.data[loop.index].color=colors[loop.vertex_index]
    obj.data.color_attributes.active_color=attr

def build():
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); root=bpy.data.objects['TravelerRoot']
    objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    target_names={'Head_Face_PorcelainCream','Head_Face_NoseCream','Head_Face_RoseCheeks','Head_Hair_Indigo','QuietSmile',
                  'Head_Eye_Ivory','Head_Eye_AmberRim','Head_Eye_Chestnut','Head_Eye_Pupil','Head_Eye_Catchlight',
                  'Blink_L_LidCover','Blink_R_LidCover','Blink_L_ClosedLash','Blink_R_ClosedLash'}
    before={n:mesh_state(o) for n,o in objects.items()}; contract=object_contract(root)
    material_names=sorted({m.name for o in objects.values() for m in o.data.materials})
    material_before={n:material_state(bpy.data.materials[n]) for n in material_names}

    # Keep neck and ear geometry; replace the old head shell and disconnected lids.
    obj=objects['Head_Face_PorcelainCream']
    verts,faces=retained_geometry(obj,lambda ids,p: len(ids)<1000 and not all(abs(v.x)<.088 and 1.06<v.z<1.12 and v.y<-.055 for v in p))
    normals=[None]*len(verts); start=len(verts); rows=72; around=112
    for j in range(rows):
        z=.932+(1.224-.932)*j/(rows-1); rx,ry,cy=section(z)
        for i in range(around):
            a=2*pi*i/around; x=rx*sin(a); f=max(0,cos(a)); y=cy-ry*cos(a)+smooth(0,.35,f)*sculpt(x,z)
            verts.append(tuple(proportion(Vector((x,y,z)))))
            normals.append(tuple(face_normal(x,z)) if cos(a)>.08 else None)
    faces.extend([tuple(start+i for i in range(around-1,-1,-1)),tuple(start+(rows-1)*around+i for i in range(around))])
    for j in range(rows-1):
        for i in range(around):
            ids=(start+j*around+i,start+j*around+(i+1)%around,start+(j+1)*around+(i+1)%around,start+(j+1)*around+i)
            p=sum((unproportion(Vector(verts[k])) for k in ids),Vector())/4
            if p.y<-.04 and inside_eye(p.x,p.z): continue
            faces.append(ids)
    for side in [-1,1]:
        for upper in [True,False]:
            start=len(verts); count=40; bands=6
            for row in range(bands):
                r=row/(bands-1)
                for k in range(count+1):
                    t=k/count; x,z=eye_edge(side,t,upper,r)
                    lift=((.00115+.00065*sin(pi*r)) if upper else (.00042+.00025*sin(pi*r)))*sin(pi*t)**.7*(1-r)**1.25
                    verts.append(tuple(proportion(Vector((x,face_y(x,z)-lift-.00004,z)))))
                    normals.append(tuple(face_normal(x,z)) if r>.75 else None)
            for row in range(bands-1):
                for k in range(count):
                    a=start+row*(count+1)+k
                    face=(a,a+1,a+count+2,a+count+1)
                    if (side>0)!=upper: face=tuple(reversed(face))
                    faces.append(face)
    replace_geometry(obj,verts,faces,normals)

    # Eye surfaces are shallow caps following the socket, not stacked spheres.
    for name in ['Ivory','AmberRim','Chestnut','Pupil','Catchlight']:
        verts=[]; faces=[]
        for side in [-1,1]:
            start=len(verts); ex=side*.048; ez=1.087
            if name=='Ivory':
                center=Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez),ez)); verts.append(tuple(proportion(center)))
                for r in [.2,.4,.6,.8,1.]:
                    for k in range(64):
                        a=2*pi*k/64; t=(cos(a)+1)/2; upper=sin(a)>=0
                        x,z=eye_edge(side,t,upper); x=ex+(x-ex)*r; z=ez+(z-ez)*r
                        verts.append(tuple(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z),z)))))
                ring_count=5; count=64
            else:
                rx,rz,depth={'AmberRim':(.0104,.0101,.00010),'Chestnut':(.0092,.0090,.00016),
                             'Pupil':(.0043,.0043,.00023),'Catchlight':(.00135,.0015,.00031)}[name]
                if name=='Catchlight': ex-=.0028; ez+=.0038
                verts.append(tuple(proportion(Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez)-depth,ez)))))
                for r in [.25,.5,.75,1.]:
                    for k in range(32):
                        a=2*pi*k/32; dx=rx*cos(a); dz=rz*sin(a)
                        clip=clip_eye_direction(side,ex,ez,dx,dz)
                        x=ex+dx*r*clip; z=ez+dz*r*clip
                        verts.append(tuple(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z)-depth,z)))))
                ring_count=4; count=32
            reverse=name=='Ivory' and side<0
            for k in range(count):
                face=(start,start+1+k,start+1+(k+1)%count)
                faces.append(tuple(reversed(face)) if reverse else face)
            for j in range(ring_count-1):
                for k in range(count):
                    a=start+1+j*count+k; b=start+1+j*count+(k+1)%count
                    face=(a,a+count,b+count,b)
                    faces.append(tuple(reversed(face)) if reverse else face)
        replace_geometry(objects['Head_Eye_'+name],verts,faces)

    # Lower lid is a restrained skin-colour margin, upper edge a tapered lash.
    verts=[]; faces=[]
    for side in [-1,1]:
        start=len(verts)
        for row in [0,1]:
            for k in range(41):
                t=k/40; x,z=eye_edge(side,t,False)
                z-=row*.00045*sin(pi*t)
                verts.append(tuple(proportion(Vector((x,face_y(x,z)-.00055,z)))))
        for k in range(40):
            a=start+k; face=(a,a+1,a+42,a+41)
            faces.append(tuple(reversed(face)) if side>0 else face)
    replace_geometry(objects['Head_Face_NoseCream'],verts,faces)
    hair=objects['Head_Hair_Indigo']
    verts,faces=retained_geometry(hair,lambda ids,p: not all(abs(v.x)<.09 and 1.065<v.z<1.135 and v.y<-.045 for v in p))
    for side in [-1,1]:
        points=[]; radii=[]
        for k in range(33):
            t=k/32; x,z=eye_edge(side,t,True)
            points.append((x,face_y(x,z)-.00135,z)); radii.append(.00012+.00025*sin(pi*t)**.65)
        tube_append(verts,faces,points,radii,5)
        points=[]; radii=[]
        for k in range(25):
            t=k/24; x=side*(.048-.026+.051*t); z=1.116+.0044*sin(pi*t)+.0014*(1-t)
            points.append((x,face_y(x,z)-.0012,z)); radii.append(.00012+.0010*sin(pi*t)**.7)
        tube_append(verts,faces,points,radii,6)
    replace_geometry(hair,verts,faces)

    # Mouth line follows an actual upper/lower lip volume already in the skin.
    verts=[]; faces=[]
    for row in [0,1]:
        for k in range(49):
            t=k/48; x=-.024+.048*t; z=1.0105+.0027*abs(x/.024)**1.5
            z+=(row-.5)*.00075*sin(pi*t)**.7
            verts.append(tuple(proportion(Vector((x,face_y(x,z)-.00030,z)))))
    for k in range(48): faces.append((k,k+1,k+50,k+49))
    replace_geometry(objects['QuietSmile'],verts,faces)
    obj=objects['Head_Face_RoseCheeks']
    verts,faces=retained_geometry(obj,lambda ids,p: all(abs(v.x)>.10 for v in p))
    for side in [-1,1]:
        points=[]
        for k in range(9):
            t=k/8; x=side*(.008+.009*t); z=1.0318+.0012*sin(pi*t)
            points.append((x,face_y(x,z)-.00025,z))
        tube_append(verts,faces,points,[.00008+.00034*sin(pi*k/8) for k in range(9)],5)
    replace_geometry(obj,verts,faces)

    # Same blink pivots/interface, new covers with edge normals matching new skin.
    scales={}
    for side,label in [(-1,'L'),(1,'R')]:
        pivot=bpy.data.objects['Blink_'+label]; scales[label]=pivot.scale.copy(); pivot.scale=(1,1,1)
        bpy.context.view_layer.update(); ex=side*.048; ez=1.086
        verts=[tuple(proportion(Vector((ex,face_y(ex,ez)-.008,ez))))]; faces=[]; normals=[None]
        for r in [.2,.4,.6,.8,.92,1.]:
            for k in range(48):
                a=2*pi*k/48; x=ex+.034*r*cos(a); z=ez+.023*r*sin(a)
                y=face_y(x,z)-.00008-.0079*max(0,1-r*r)**1.8
                verts.append(tuple(proportion(Vector((x,y,z)))))
                normals.append(tuple(face_normal(x,z)) if r>=.8 else None)
        for k in range(48): faces.append((0,1+k,1+(k+1)%48))
        for row in range(5):
            for k in range(48):
                a=1+row*48+k; b=1+row*48+(k+1)%48; faces.append((a,a+48,b+48,b))
        replace_geometry(objects['Blink_'+label+'_LidCover'],verts,faces,normals)
        verts=[]; faces=[]; points=[]; radii=[]
        for k in range(25):
            t=k/24; x=ex-.024+.048*t; z=ez-.0032*sin(pi*t)
            r=sqrt(((x-ex)/.034)**2+((z-ez)/.023)**2)
            y=face_y(x,z)-.00008-.0079*max(0,1-r*r)**1.8-.00035
            points.append((x,y,z)); radii.append(.00010+.00040*sin(pi*t)**.7)
        tube_append(verts,faces,points,radii,5)
        replace_geometry(objects['Blink_'+label+'_ClosedLash'],verts,faces)
    for name in target_names: paint(objects[name])
    for label,scale in scales.items(): bpy.data.objects['Blink_'+label].scale=scale
    bpy.context.view_layer.update()

    changed_materials={'Traveler_Eye_Ivory':(.70,.695,.63,1),'Traveler_Eye_AmberRim':(.245,.145,.076,1),'Traveler_Eye_Chestnut':(.21,.112,.058,1)}
    for name,color in changed_materials.items():
        material=bpy.data.materials[name]; material.diffuse_color=color
        bsdf=material.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value=color
        # Preserve v7's vertex-colour multiply preview graph, update its base too.
        for link in bsdf.inputs['Base Color'].links:
            if link.from_node.type=='MIX_RGB': link.from_node.inputs[1].default_value=color
    after={n:mesh_state(o) for n,o in objects.items()}
    protected=[]
    for name in objects:
        if name not in target_names:
            assert before[name]==after[name],name+' protected data changed'
            protected.append({'mesh':name,'sha256':digest(before[name]),'exact_match':True})
    assert contract==object_contract(root),'bone/object/pivot contract changed'
    for name in material_names:
        if name not in changed_materials: assert material_before[name]==material_state(bpy.data.materials[name]),name
    triangles=0
    for obj in objects.values(): obj.data.calc_loop_triangles(); triangles+=len(obj.data.loop_triangles)
    assert triangles<82000,triangles
    preservation={'passed':True,'source_sha256':source_hash,'protected_meshes':protected,'protected_count':len(protected),
                  'targets':sorted(target_names),'object_bone_pivot_exact_match':True,'object_contract_sha256':digest(contract),
                  'modified_materials':changed_materials,'triangles':triangles,'mesh_renderers':len(objects),
                  'scope':'Only listed head/eye/blink meshes and 3 eye material bases may change. All non-target mesh channels, skinning/attachments, other material graphs and object/bone/pivot transforms are exact v7 data.'}
    (OUT/'v7-preservation-verification.json').write_text(json.dumps(preservation,indent=2),encoding='utf-8')
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
    manifest={'version':8,'source':str(SOURCE.relative_to(ROOT)),'source_sha256':source_hash,'triangles':triangles,'mesh_renderers':62,
              'skinned_meshes':28,'armatures':4,'bones':12,'material_count':29,'material_names':material_names,
              'changes':'Nonuniform-z C1 facial profile; connected nasal/cheek/lip/chin form; socket openings and asymmetric lids; shallow ocular caps, circular pupil; matching closed covers.',
              'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'traveler.blend',OUT/'traveler.fbx',OUT/'traveler.glb']}}
    (OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
    print('FACE_V8_EXPORTED '+json.dumps({'triangles':triangles,'protected_meshes':len(protected)}),flush=True)

def render():
    for version,path in [('v7',SOURCE),('v8',OUT/'traveler.blend')]:
        if '--candidate-only' in ARGS and version=='v7': continue
        bpy.ops.wm.open_mainfile(filepath=str(path)); scene=bpy.context.scene
        scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=8; scene.cycles.use_denoising=True
        scene.render.threads_mode='FIXED'; scene.render.threads=4
        scene.render.resolution_x=512; scene.render.resolution_y=512; scene.render.resolution_percentage=100
        camera=bpy.data.objects['PREVIEW_Camera']; scene.camera=camera
        for name,location in [('front',(0,-4,1.19)),('three-quarter',(2.1,-4,1.30)),('profile',(4,-.12,1.22))]:
            camera.location=location; camera.rotation_euler=(Vector((0,-.015,1.13))-camera.location).to_track_quat('-Z','Y').to_euler()
            camera.data.type='ORTHO'; camera.data.ortho_scale=.47
            scene.render.filepath=str(OUT/(version+'-'+name+'.png')); bpy.ops.render.render(write_still=True)
        if version=='v8':
            for name in ['Blink_L','Blink_R']: bpy.data.objects[name].scale=(1,1,1)
            camera.location=(2.1,-4,1.30); camera.rotation_euler=(Vector((0,-.015,1.13))-camera.location).to_track_quat('-Z','Y').to_euler()
            scene.render.filepath=str(OUT/'v8-blink.png'); bpy.ops.render.render(write_still=True)

if '--render-only' in ARGS: render()
else:
    build()
    if '--render' in ARGS: render()
