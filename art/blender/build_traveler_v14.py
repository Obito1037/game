"""Isolated eyelid/ocular-surface candidate from frozen character-v11.

Coordinates/normals only: source topology, UVs, Col, materials and rig stay fixed.
CPU rendering <=4 threads. No Unity writes. No earlier rejected lower-face input.
"""
import ast,bpy,hashlib,json,math,os,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from math import sin,cos,pi,exp,sqrt
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v11/traveler.blend'
OUT=ROOT/'art/generated/character-v14'
EYES=['Ivory','AmberRim','Chestnut','Pupil','Catchlight']
TARGETS={'Head_Face_PorcelainCream','Head_Hair_Indigo'}|{'Head_Eye_'+n for n in EYES}|{'Blink_'+s+'_'+n for s in ['L','R'] for n in ['LidCover','ClosedLash']}
for file,names in [('build_traveler_v7.py',{'digest','matrix','weight_values','material_state','mesh_state','object_contract'}),('build_traveler_v6.py',{'smooth','proportion','unproportion','face_section'}),('build_traveler_v8.py',{'tube_append'}),('build_traveler_v11.py',{'slope','section','sculpt','surface','face_y','face_normal','eye_edge','inside_eye','ocular_depth','clip_eye','export_fbx','preview_conditions'})]:
    tree=ast.parse((ROOT/'art/blender'/file).read_text(encoding='utf-8'));selected=[]
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name in names:selected.append(n)
        if file=='build_traveler_v11.py' and isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'ZMAP','FACE_LEVELS','NEW_LEVELS'} for t in n.targets):selected.append(n)
    exec(compile(ast.Module(body=selected,type_ignores=[]),file,'exec'))
old_eye_edge=eye_edge

def eye_edge(side,t,upper=True,outer=0.):
    x,z=old_eye_edge(side,t,upper,outer)
    if upper:z-=(.0168-.0134)*(1+side*.025)*max(0,sin(pi*t))**.82*(1-outer)
    return x,z

def ocular_depth(side,x,z):
    t=max(0,min(1,(side*x-(.048-.0306))/.0612));center=1.0868+.0018*(t-.5)
    _,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False);height=max(.00001,up-center if z>=center else center-low)
    horizontal=(2*t-1)**2;r2=horizontal+(1-horizontal)*min(1,((z-center)/height)**2)
    return .00010+.00050*max(0,sin(pi*t))**.7+.0028*(1-r2)

def set_positions(obj,points,indices=None,normal_blends=None):
    mesh=obj.data;old_normals=[n.vector.copy() for n in mesh.corner_normals];inv=obj.matrix_world.inverted();basis=obj.matrix_world.to_3x3().transposed()
    if indices is None:indices=list(range(len(mesh.vertices)))
    assert len(indices)==len(points),(obj.name,len(indices),len(points))
    for i,p in zip(indices,points):mesh.vertices[i].co=inv@Vector(p)
    mesh.update();auto={i:mesh.vertices[i].normal.copy() for i in indices};chosen=set(indices)
    if normal_blends:
        for i,(normal,blend) in normal_blends.items():auto[i]=auto[i].lerp((basis@normal).normalized(),blend).normalized()
    mesh.normals_split_custom_set([tuple(auto[loop.vertex_index] if loop.vertex_index in chosen else old_normals[loop.index]) for loop in mesh.loops])

def build_ribbons(obj):
    before=[v.co.copy() for v in obj.data.vertices];points=[];indices=[];blends={};start=758+9600;count=48;bands=7
    assert len(before)==11730
    for s,side in enumerate([-1,1]):
        begin=start+s*2*bands*(count+1)
        for row in range(bands-1):
            r=row/(bands-1)
            for k in range(count+1):
                t=k/count;x,z=eye_edge(side,t,True,r);lift=.00110*max(0,sin(pi*t))**.75*(1-r)**1.35+.00012*(1-r)
                index=begin+row*(count+1)+k;indices.append(index);points.append(proportion(Vector((x,face_y(x,z)-lift-.00006,z))));blends[index]=(face_normal(x,z),smooth(.25,1,r))
    set_positions(obj,points,indices,blends)
    assert all(obj.data.vertices[i].co==before[i] for i in range(start)),'Main head shell / ears / neck changed'
    changed=set(indices);assert all(obj.data.vertices[i].co==before[i] for i in range(len(before)) if i not in changed),'Lower/outer lid changed'
    return {'allowedVertexIndices':indices,'mainShellNeckEarVerticesPreserved':start,'lowerRibbonsAndUpperOuterBoundaryCoordinatesExact':True}

def build_eyes(objects):
    report={}
    for name in EYES:
        points=[]
        for side in [-1,1]:
            ex=side*.048+.00055;ez=1.0883
            if name=='Ivory':
                ex=side*.048;ez=1.087;points.append(proportion(Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez),ez))))
                for r in [.16,.32,.50,.67,.84,1.]:
                    for k in range(72):
                        a=2*pi*k/72;t=(1+side*cos(a))/2;x,z=eye_edge(side,t,sin(a)>=0);x=ex+(x-ex)*r;z=ez+(z-ez)*r
                        points.append(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z),z))))
            else:
                rx,rz,depth={'AmberRim':(.0136,.0132,.00010),'Chestnut':(.01225,.0120,.00017),'Pupil':(.0053,.0055,.00025),'Catchlight':(.0017,.0018,.00034)}[name]
                if name=='Catchlight':ex-=.0035;ez+=.0043
                points.append(proportion(Vector((ex,face_y(ex,ez)-ocular_depth(side,ex,ez)-depth,ez))))
                for r in [.2,.4,.6,.8,1.]:
                    for k in range(40):
                        a=2*pi*k/40;dx=rx*cos(a);dz=rz*sin(a);clip=clip_eye(side,ex,ez,dx,dz);x=ex+dx*r*clip;z=ez+dz*r*clip
                        points.append(proportion(Vector((x,face_y(x,z)-ocular_depth(side,x,z)-depth,z))))
            report[name]={'canonicalUpperHeight':.0134,'eyeWidthUnchanged':.0612,'coordinatesOnly':True}
        set_positions(objects['Head_Eye_'+name],points)
    return report

def build_lashes(obj):
    manifest=json.loads((ROOT/'art/generated/character-v11/candidate-manifest.json').read_text(encoding='utf-8'));start=640+manifest['hair']['geometry']['vertices'];before=[v.co.copy() for v in obj.data.vertices];indices=[];points=[]
    for s,side in enumerate([-1,1]):
        offset=start+s*(205+198);old=[];unused=[];new=[]
        original=[];modified=[];r0=[];r1=[]
        for k in range(41):
            t=k/40;x,z=old_eye_edge(side,t,True);original.append((x,face_y(x,z)-.00155,z));r0.append(.00012+.00037*sin(pi*t)**.75)
            x,z=eye_edge(side,t,True);modified.append((x,face_y(x,z)-.00134,z));r1.append(.000075+.00023*sin(pi*t)**.75)
        tube_append(old,unused,original,r0,5);tube_append(new,[],modified,r1,5)
        assert len(old)==205
        for i,(p,q) in enumerate(zip(old,new)):
            index=offset+i;assert (obj.matrix_world@before[index]-Vector(p)).length<.000002,'Lash index does not match frozen v11'
            indices.append(index);points.append(q)
    set_positions(obj,points,indices)
    chosen=set(indices);assert all(obj.data.vertices[i].co==before[i] for i in range(len(before)) if i not in chosen),'True hair/scalp/eyebrows changed'
    return {'upperLashVertices':len(indices),'allowedVertexIndices':indices,'allTrueHairScalpEyebrowCoordinatesExact':True,'maximumCanonicalRadius':.000305}

def bvh_objects(objects):
    vertices=[];triangles=[]
    for obj in objects:
        obj.data.calc_loop_triangles();offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);triangles.extend(tuple(offset+i for i in t.vertices) for t in obj.data.loop_triangles)
    return BVHTree.FromPolygons(vertices,triangles,all_triangles=True)

def ray_at(bvh,x,z):
    hit,normal,index,distance=bvh.ray_cast(Vector((x,-1.,z)),Vector((0,1,0)),3.)
    return hit

def build_blinks(objects):
    saved={label:bpy.data.objects['Blink_'+label].scale.copy() for label in ['L','R']};reports=[]
    eye_bvh=bvh_objects([objects['Head_Eye_'+n] for n in EYES])
    for side,label in [(-1,'L'),(1,'R')]:
        pivot=bpy.data.objects['Blink_'+label];pivot.scale=(1,1,1);bpy.context.view_layer.update();obj=objects['Blink_'+label+'_LidCover'];before=[obj.matrix_world@v.co for v in obj.data.vertices]
        # Retain the old broad cover and its topology; increase only depth where
        # actual new eye intersections demand it in sampled partial/full states.
        points=[p.copy() for p in before];full_matrix=obj.matrix_world.copy();inv=full_matrix.inverted();adjustments=[]
        for index,p in enumerate(points):
            local=inv@p;maximum=0.
            for scale in [.25,.5005,.75,1.]:
                pivot.scale=(scale,scale,1);bpy.context.view_layer.update();q=obj.matrix_world@local;hit=ray_at(eye_bvh,q.x,q.z)
                if hit is not None:maximum=max(maximum,q.y-hit.y+.00030)
            if maximum>0:p.y-=maximum
            adjustments.append(maximum)
        pivot.scale=(1,1,1);bpy.context.view_layer.update();set_positions(obj,points)
        # Closed lash follows the real updated cover rather than old analytic dome.
        cover=bvh_objects([obj]);lash=objects['Blink_'+label+'_ClosedLash'];new=[]
        for v in lash.data.vertices:
            p=lash.matrix_world@v.co;hit=ray_at(cover,p.x,p.z)
            if hit is not None:p.y=hit.y-.00024
            new.append(p)
        set_positions(lash,new)
        reports.append({'side':label,'maximumWorldYDepthCorrection':max(adjustments),'correctedVertices':sum(d>0 for d in adjustments),'sampledEnvelopeScales':[.25,.5005,.75,1.]})
    for label,scale in saved.items():bpy.data.objects['Blink_'+label].scale=scale
    bpy.context.view_layer.update();return reports

def blink_check(objects):
    saved={label:bpy.data.objects['Blink_'+label].scale.copy() for label in ['L','R']};eye_bvh=bvh_objects([objects['Head_Eye_'+n] for n in EYES]);samples=[]
    for side in [-1,1]:
        for i in range(1,32):
            t=i/32;x,_=eye_edge(side,t,True);_,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False)
            for j in range(1,16):
                p=proportion(Vector((x,0,low+(up-low)*j/16)));eye=ray_at(eye_bvh,p.x,p.z)
                if eye is not None:samples.append(eye)
    records=[]
    for state,s in [('open',.001),('half',.5005),('closed',1.)]:
        for label in ['L','R']:bpy.data.objects['Blink_'+label].scale=(s,s,1)
        bpy.context.view_layer.update();cover=bvh_objects([objects['Blink_'+label+'_LidCover'] for label in ['L','R']]);gaps=[];miss=0;worst=None
        for eye in samples:
            hit=ray_at(cover,eye.x,eye.z)
            if hit is None:miss+=1;continue
            gap=eye.y-hit.y;gaps.append(gap)
            if worst is None or gap<worst['gap']:worst={'gap':gap,'eye':list(eye),'cover':list(hit)}
        records.append({'state':state,'blinkLocalScale':[s,s,1],'actualEyeSampleCount':len(samples),'coverProjectionMisses':miss,'coveredSamples':len(gaps),'minimumWorldYClearance':min(gaps,default=None),'samplesWithCoverBehindEye':sum(g<0 for g in gaps),'worst':worst,'finiteSamplingOnly':True})
    for label,scale in saved.items():bpy.data.objects['Blink_'+label].scale=scale
    bpy.context.view_layer.update();return records

def colour_statistics(obj):
    return {a.name:{'domain':a.domain,'type':a.data_type,'samples':len(a.data),'minimumRGBA':[min(d.color[i] for d in a.data) for i in range(4)],'maximumRGBA':[max(d.color[i] for d in a.data) for i in range(4)],'uniqueRGBA':sorted({tuple(d.color) for d in a.data})} for a in obj.data.color_attributes}

def build():
    OUT.mkdir(parents=True,exist_ok=True);frozen=[SOURCE,ROOT/'art/generated/character-v11/traveler.fbx',ROOT/'art/blender/build_traveler_v11.py'];hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen}
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False);root=bpy.data.objects['TravelerRoot'];objects={o.name:o for o in root.children_recursive if o.type=='MESH'};before={n:mesh_state(o) for n,o in objects.items()};contract=object_contract(root);materials=sorted({m.name for o in objects.values() for m in o.data.materials});material_before={n:material_state(bpy.data.materials[n]) for n in materials}
    ribbons=build_ribbons(objects['Head_Face_PorcelainCream']);eyes=build_eyes(objects);lashes=build_lashes(objects['Head_Hair_Indigo']);blinks=build_blinks(objects);coverage=blink_check(objects);rows=[]
    for name,obj in objects.items():
        after=mesh_state(obj);old=before[name]
        if name in TARGETS:
            for key in old:
                if key not in {'coordinates','normals'}:assert old[key]==after[key],name+' changed '+key
        else:assert old==after,name+' changed outside eyes'
        changed=[i for i,(a,b) in enumerate(zip(old['coordinates'],after['coordinates'])) if a!=b]
        rows.append({'mesh':name,'target':name in TARGETS,'changedVertices':len(changed),'unchanged':old==after})
    assert contract==object_contract(root),'Object/bone/pivot/scale interface changed'
    for name in materials:assert material_before[name]==material_state(bpy.data.materials[name]),'Material changed '+name
    triangles=0
    for obj in objects.values():obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    assert triangles==81968;export_fbx(root,materials);unchanged={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p.relative_to(ROOT))] for p in frozen};assert all(unchanged.values())
    manifest={'revision':'character-v14','gameCandidate':'v14-eye-geometry-study','baseline':'character-v11','source':str(SOURCE.relative_to(ROOT)),'sourceSHA256':hashes[str(SOURCE.relative_to(ROOT))],'triangles':triangles,'newPolygons':0,'targets':sorted(TARGETS),'protectedMeshCount':len(objects)-len(TARGETS),'meshDifferences':rows,'ribbons':ribbons,'eyes':eyes,'upperLashes':lashes,'blinks':blinks,'blinkCoverageFiniteSample':coverage,'sourceEyeColours':{n:colour_statistics(objects['Head_Eye_'+n]) for n in EYES},'allTopologyUVColourWeightsMaterialsUnchanged':True,'materialGraphsUnchanged':True,'objectBonePivotContractUnchanged':True,'frozenInputsUnchanged':unchanged,'files':{},'limits':['Unaccepted geometry candidate, no Unity writes.','CPU studio comparison only; not a normal-game or performance acceptance.','Blink checks are finite frontal world-Y samples, not all angles or all scales.','Export completion and source preservation are not an FBX readback audit.'],'aestheticObjectiveAchieved':False}
    for p in [OUT/'traveler.blend',OUT/'traveler.fbx']:manifest['files'][p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('EYES_V14_BUILT '+json.dumps({'pid':os.getpid(),'triangles':triangles,'protectedMeshes':len(objects)-len(TARGETS),'blinkCoverage':coverage}),flush=True)

def render():
    records=[]
    for version,file in [('baseline',SOURCE),('candidate',OUT/'traveler.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=17;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100;camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera
        views=[('three-quarter',(1.8,-3.7,1.45),.001),('front',(0,-4,1.27),.001)]
        if version=='candidate':views.extend([('profile',(4,-.12,1.23),.001),('front-half',(0,-4,1.27),.5005),('front-closed',(0,-4,1.27),1.)])
        for view,position,s in views:
            for label in ['L','R']:bpy.data.objects['Blink_'+label].scale=(s,s,1)
            target=proportion(Vector((0,-.002,1.105)));camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.56;bpy.context.view_layer.update();conditions=preview_conditions(scene,camera);file=version+'-'+view+'.png';scene.render.filepath=str(OUT/file);bpy.ops.render.render(write_still=True);records.append({'version':version,'view':view,'file':file,'blinkScale':[s,s,1],'conditions':conditions});print('EYES_V14_PREVIEW '+version+' '+view,flush=True)
    for view in ['three-quarter','front']:
        pair=[r for r in records if r['view']==view];assert pair[0]['conditions']==pair[1]['conditions'],'Baseline/candidate lighting/camera changed'
    (OUT/'preview-conditions.json').write_text(json.dumps({'sameCameraAndLights':True,'cpuOnly':True,'geometryOnly':True,'records':records},indent=2),encoding='utf-8')

if __name__=='__main__':
    print('EYES_V14_PROCESS '+json.dumps({'pid':os.getpid(),'cpuThreadsMax':4,'source':str(SOURCE),'output':str(OUT)}),flush=True)
    if '--render-only' not in sys.argv:build()
    render()
