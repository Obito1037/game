"""Independent lower-face form candidate from frozen character-v11.

Only three existing mesh objects may change coordinates/normals. No new noise,
material, polygons, eye, blink, hair, neck/ear, body or Unity edits. CPU <=4 threads.
"""
import ast,bpy,hashlib,json,math,os,sys
from pathlib import Path
from mathutils import Vector
from math import sin,cos,pi,exp,sqrt
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v11/traveler.blend'
OUT=ROOT/'art/generated/character-v12'
TARGETS={'Head_Face_PorcelainCream','QuietSmile','Head_Face_RoseCheeks'}
# Reuse pure helpers and the frozen v11 parameter surface, never its entrypoint.
for file,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract'}),('build_traveler_v6.py',{'smooth','proportion','unproportion','face_section'}),('build_traveler_v11.py',{'slope','section','sculpt','surface','face_y','export_fbx','preview_conditions'})]:
    tree=ast.parse((ROOT/'art/blender'/file).read_text(encoding='utf-8'));selected=[]
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name in names:selected.append(n)
        if file=='build_traveler_v11.py' and isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'ZMAP','FACE_LEVELS','NEW_LEVELS'} for t in n.targets):selected.append(n)
    exec(compile(ast.Module(body=selected,type_ignores=[]),file,'exec'))

# Authored, low-frequency sagittal control cage. Units are metres. Rows describe
# continuous chin plane -> lip volumes/crease -> philtrum -> alae/nose side planes.
# This is a deformation of the existing surface, not more Gaussian detail or noise.
X=[0,.006,.012,.019,.027,.040,.060,.080,.103,.120]
Z=[.942,.954,.972,.986,.998,1.0065,1.0100,1.0115,1.0147,1.0190,1.0250,1.0330,1.0420,1.0530,1.0650,1.0740]
CAGE=[
 [0,0,0,0,0,0,0,0,0,0],
 [-.0005,-.0005,-.0004,-.0003,-.0002,0,0,0,0,0],
 [-.0017,-.0017,-.0016,-.0014,-.0011,-.0006,0,0,0,0],
 [-.0022,-.0022,-.0020,-.0018,-.0015,-.0008,.0002,.0003,0,0],
 [.0004,.0004,.0005,.0006,.0007,.0008,.0004,.0002,0,0],
 [-.0018,-.0018,-.0015,-.0008,.0006,.0006,.0003,.0002,0,0],
 [-.0005,-.0005,-.0004,.0001,.0012,.0005,.0002,0,0,0],
 [.00115,.00115,.0010,.0013,.0018,.0005,.0001,0,0,0],
 [-.0013,-.0026,-.0020,-.0008,.0014,.0005,.0001,0,0,0],
 [-.0012,-.0015,-.0011,-.0003,.0006,.0002,-.0002,0,0,0],
 [.0009,-.0006,-.0004,0,.0004,.0002,-.0005,-.0001,0,0],
 [-.0012,.0007,.0010,-.0022,.0009,.0005,-.0008,0,0,0],
 [-.0006,-.0006,-.0008,-.0018,.0010,.0006,-.0011,.0002,0,0],
 [-.0011,-.0012,-.0010,.0006,.0010,.0006,-.0013,.0002,0,0],
 [-.0012,-.0010,-.0004,.0005,.0007,.0004,-.0006,0,0,0],
 [0,0,0,0,0,0,0,0,0,0],
]
def slopes(axis,values):
    out=[]
    for i in range(len(axis)):
        if i==0 or i==len(axis)-1:out.append(0.);continue
        h0=axis[i]-axis[i-1];h1=axis[i+1]-axis[i];d0=(values[i]-values[i-1])/h0;d1=(values[i+1]-values[i])/h1
        if d0*d1<=0:out.append(0.)
        else:
            a=2*h1+h0;b=h1+2*h0;out.append((a+b)/(a/d0+b/d1))
    return out
def interp(axis,values,x,tangents=None):
    if x<=axis[0]:return values[0]
    if x>=axis[-1]:return values[-1]
    i=next(i for i in range(len(axis)-1) if x<axis[i+1]);h=axis[i+1]-axis[i];t=(x-axis[i])/h;m=tangents if tangents is not None else slopes(axis,values)
    return (2*t**3-3*t*t+1)*values[i]+(t**3-2*t*t+t)*h*m[i]+(-2*t**3+3*t*t)*values[i+1]+(t**3-t*t)*h*m[i+1]
X_SLOPES=[slopes(X,row) for row in CAGE]
def mouth_curve(x):
    q=max(-1.25,min(1.25,x/.0252));return .0022*abs(q)**1.65+.00035*q
def lip_mask(x,z):
    return (1-smooth(.028,.050,abs(x)))*smooth(1.000,1.006,z)*(1-smooth(1.020,1.026,z))
def cage_delta(p):
    x,y,z=p
    if z<=Z[0] or z>=Z[-1] or abs(x)>=X[-1]:return 0.
    z_sample=z-mouth_curve(x)*lip_mask(x,z)
    row_values=[interp(X,row,abs(x),m) for row,m in zip(CAGE,X_SLOPES)]
    return interp(Z,row_values,z_sample)*smooth(.025,.065,-y)

# Redirect existing rings into a closed-lip flow, rather than increasing density.
# The source rings j18..25 remain ordered and end at the same lower/upper bounds.
LIP_RING_OLD=[.932+.292*j/79 for j in range(18,26)]
LIP_RING_NEW=[LIP_RING_OLD[0],1.0035,1.0070,1.0100,1.0115,1.0147,1.0187,LIP_RING_OLD[-1]]
LIP_RING_SLOPES=slopes(LIP_RING_OLD,LIP_RING_NEW)
LIP_RING_SLOPES[0]=LIP_RING_SLOPES[-1]=1.0
def deformed_surface(a,z):
    p=surface(a,z)
    if LIP_RING_OLD[0]<z<LIP_RING_OLD[-1]:
        central=(1-smooth(.028,.055,abs(p.x)))*smooth(.030,.065,-p.y)
        mapped=interp(LIP_RING_OLD,LIP_RING_NEW,z,LIP_RING_SLOPES)
        mapped+=mouth_curve(p.x)*smooth(1.001,1.006,mapped)*(1-smooth(1.019,1.024,mapped))
        p=surface(a,z+(mapped-z)*central)
    dy=cage_delta(p)
    jaw=.0022*smooth(.947,.972,p.z)*(1-smooth(.986,1.008,p.z))*smooth(.028,.080,abs(p.x))*smooth(.005,.060,-p.y)
    return Vector((p.x-math.copysign(jaw,p.x) if p.x else 0.,p.y+dy,p.z))
def deformed_normal(a,z):
    h=.00002
    t=proportion(deformed_surface(a+h,z))-proportion(deformed_surface(a-h,z))
    v=proportion(deformed_surface(a,z+h))-proportion(deformed_surface(a,z-h))
    return t.cross(v).normalized()
def update_head(obj):
    mesh=obj.data;before=[v.co.copy() for v in mesh.vertices];old_normals=[n.vector.copy() for n in mesh.corner_normals];world=obj.matrix_world;inv=world.inverted();basis=world.to_3x3().transposed()
    assert len(mesh.vertices)==11730,('Unexpected v11 head cage',len(mesh.vertices))
    new_normals={};modified=[];max_delta=0.
    for j in range(80):
        z=.932+.292*j/79
        for i in range(120):
            index=758+j*120+i;a=2*pi*i/120;old=unproportion(world@mesh.vertices[index].co)
            reference=surface(a,z);assert (old-reference).length<.000002,'Frozen source head sampling differs'
            p=deformed_surface(a,z);delta=p-reference;d=delta.length
            if d<.000000001:continue
            mesh.vertices[index].co=inv@proportion(old+delta);new_normals[index]=(basis@deformed_normal(a,z)).normalized();modified.append(index);max_delta=max(max_delta,d)
    mesh.update();normals=[tuple(new_normals.get(loop.vertex_index,old_normals[loop.index])) for loop in mesh.loops];mesh.normals_split_custom_set(normals)
    assert all(mesh.vertices[i].co==before[i] for i in range(758)),'Neck/ear geometry changed'
    protected_normals=[(mesh.corner_normals[loop.index].vector-old_normals[loop.index]).length for loop in mesh.loops if loop.vertex_index<758]
    error=max(protected_normals,default=0.);assert error<.0002,error
    return {'changedVertices':len(modified),'maximumCanonicalDisplacementMetres':max_delta,'neckEarVerticesPreserved':758,'neckEarCoordinatesExact':True,'neckEarMaximumNormalVectorRepackingError':error,'eyeLidRibbonsCoordinatesProtected':all(mesh.vertices[i].co==before[i] for i in range(758+9600,len(mesh.vertices))),'ringTopologyUnchanged':True,'newPolygons':0}
def update_mouth(obj):
    assert len(obj.data.vertices)==114,'Unexpected frozen mouth topology'
    inv=obj.matrix_world.inverted()
    for row in [0,1]:
        for k in range(57):
            t=k/56;x=-.0252+.0504*t;z=1.0115+mouth_curve(x)+(row-.5)*(.00015+.00090*sin(pi*t)**.7)
            y=face_y(x,z);y+=cage_delta(Vector((x,y,z)))-.00012
            obj.data.vertices[row*57+k].co=inv@proportion(Vector((x,y,z)))
    obj.data.update();obj.data.normals_split_custom_set_from_vertices([tuple(v.normal) for v in obj.data.vertices])
def update_nostrils(obj):
    before=[v.co.copy() for v in obj.data.vertices];old_normals=[n.vector.copy() for n in obj.data.corner_normals];world=obj.matrix_world;inv=world.inverted();changed=[]
    assert len(before)==310,'Expected 200 inner-ear vertices and 110 groove vertices'
    for v in obj.data.vertices:
        p=unproportion(world@v.co)
        if abs(p.x)>.10:continue
        assert v.index>=200,'Inner ear classification changed'
        p.y+=cage_delta(p);v.co=inv@proportion(p);changed.append(v.index)
    obj.data.update();auto=[v.normal.copy() for v in obj.data.vertices]
    obj.data.normals_split_custom_set([tuple(old_normals[loop.index] if loop.vertex_index<200 else auto[loop.vertex_index]) for loop in obj.data.loops])
    assert all(obj.data.vertices[i].co==before[i] for i in range(200)),'Inner ear geometry changed'
    return {'nostrilGrooveVertices':len(changed),'innerEarVerticesPreserved':200,'innerEarCoordinatesExact':True}
def build():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=[SOURCE,ROOT/'art/generated/character-v11/traveler.fbx',ROOT/'art/blender/build_traveler_v11.py',ROOT/'art/blender/traveler_v11_hair.py']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen}
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False);root=bpy.data.objects['TravelerRoot'];objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    before={n:mesh_state(o) for n,o in objects.items()};contract=object_contract(root)
    materials=sorted({m.name for o in objects.values() for m in o.data.materials});material_before={n:material_state(bpy.data.materials[n]) for n in materials}
    main=update_head(objects['Head_Face_PorcelainCream']);update_mouth(objects['QuietSmile']);nostrils=update_nostrils(objects['Head_Face_RoseCheeks'])
    rows=[]
    for name,obj in objects.items():
        after=mesh_state(obj);old=before[name]
        if name in TARGETS:
            for key in old:
                if key not in {'coordinates','normals'}:assert old[key]==after[key],name+' changed '+key
        else:assert old==after,name+' changed outside lower-face scope'
        changed=[i for i,(p,q) in enumerate(zip(old['coordinates'],after['coordinates'])) if p!=q]
        maximum=max(((Vector(old['coordinates'][i])-Vector(after['coordinates'][i])).length for i in changed),default=0.)
        rows.append({'mesh':name,'target':name in TARGETS,'changedVertices':len(changed),'maximumLocalDisplacementMetres':maximum,'unchanged':old==after,'protectedChannelSHA256':digest({k:v for k,v in old.items() if name not in TARGETS or k not in {'coordinates','normals'}})})
    assert contract==object_contract(root),'Object/bone/pivot interface changed'
    for name in materials:assert material_before[name]==material_state(bpy.data.materials[name]),'Material changed '+name
    triangles=0
    for obj in objects.values():obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    assert triangles==81968,triangles
    export_fbx(root,materials)
    unchanged={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p.relative_to(ROOT))] for p in frozen};assert all(unchanged.values())
    manifest={'revision':'character-v12','gameCandidate':'v14','source':str(SOURCE.relative_to(ROOT)),'sourceSHA256':hashes[str(SOURCE.relative_to(ROOT))],'triangles':triangles,'newPolygons':0,'meshRenderers':len(objects),'targets':sorted(TARGETS),'protectedMeshCount':len(objects)-len(TARGETS),'meshDifferences':rows,'mainHead':main,'nostrils':nostrils,'objectBonePivotContractUnchanged':True,'allMaterialGraphsUnchanged':True,'allTopologyUVColourWeightMaterialChannelsUnchanged':True,'frozenInputsUnchanged':unchanged,'shapeMethod':'Authored monotone C1 sagittal control cage; existing mouth rings redirected into lip/closed-crease flow. Broad soft cheek/chin and nose/alar transitions; no added wrinkle, noise, material or polygons.','mouthWidthMetres':.0504,'cage':{'x':X,'z':Z,'dy':CAGE},'limits':['Geometry candidate only; not accepted or imported into Unity.','Source and exported file identities are recorded; source-preservation assertions are not an FBX roundtrip audit.','Eyes, blink, hair and all 59 non-target mesh states remain frozen v11 data.','No new GLB or normal-game/performance acceptance.'],'files':{},'aestheticObjectiveAchieved':False}
    for p in [OUT/'traveler.blend',OUT/'traveler.fbx']:manifest['files'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('HEAD_V12_BUILT '+json.dumps({'pid':os.getpid(),'triangles':triangles,'protectedMeshes':len(objects)-len(TARGETS),'headChangedVertices':main['changedVertices']}),flush=True)
def render():
    records=[]
    for version,file in [('baseline',SOURCE),('candidate',OUT/'traveler.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);scene=bpy.context.scene
        scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=17;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
        scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100;camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera
        for view,position in [('three-quarter',(1.8,-3.7,1.45)),('profile',(4,-.12,1.23))]:
            target=proportion(Vector((0,-.002,1.105)));camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.56
            bpy.context.view_layer.update();conditions=preview_conditions(scene,camera);filename=version+'-'+view+'.png';scene.render.filepath=str(OUT/filename);bpy.ops.render.render(write_still=True)
            records.append({'version':version,'view':view,'file':filename,'conditions':conditions});print('HEAD_V12_PREVIEW '+version+' '+view,flush=True)
    for view in ['three-quarter','profile']:
        pair=[r for r in records if r['view']==view];assert pair[0]['conditions']==pair[1]['conditions'],'Light/camera mismatch'
    (OUT/'preview-conditions.json').write_text(json.dumps({'sameCameraAndLights':True,'cpuOnly':True,'geometryComparisonOnly':True,'baseline':'character-v11','candidate':'character-v12','records':records},indent=2),encoding='utf-8')
if __name__=='__main__':
    print('HEAD_V12_PROCESS '+json.dumps({'pid':os.getpid(),'cpuThreadsMax':4,'source':str(SOURCE),'output':str(OUT)}),flush=True)
    if '--render-only' not in sys.argv:build()
    render()
