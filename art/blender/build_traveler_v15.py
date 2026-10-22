"""Two-stage, constant-width eyelid morph candidate. CPU only, <=4 threads.

Source chain: frozen v11 face/body -> rejected v14's isolated open-eye changes.
Replaces the four Blink meshes; moves only static upper lashes out of Hair.
No Unity writes; all other objects/channels remain frozen source data.
"""
import bpy,hashlib,importlib.util,json,math,os,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from math import sin,cos,pi
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/character-v14/traveler.blend'
OUT=ROOT/'art/generated/character-v15'
spec=importlib.util.spec_from_file_location('frozen_v14_helpers',ROOT/'art/blender/build_traveler_v14.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
proportion=base.proportion;unproportion=base.unproportion;eye_edge=base.eye_edge;face_y=base.face_y;mesh_state=base.mesh_state;object_contract=base.object_contract;material_state=base.material_state;digest=base.digest
KEYS=['Basis','BlinkHalf','BlinkClosed'];SAMPLES=[0,.125,.25,.375,.5,.625,.75,.875,1.];COUNT=64;ROWS=12
TARGETS={'Head_Hair_Indigo'}|{'Blink_'+s+'_'+n for s in ['L','R'] for n in ['LidCover','ClosedLash']}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def weights(c):return [1-2*c,2*c,0] if c<=.5 else [0,2-2*c,2*c-1]
def mix_points(shapes,c):
    w=weights(c);return [sum((Vector(shapes[k][i])*w[j] for j,k in enumerate(KEYS)),Vector()) for i in range(len(shapes['Basis']))]
def bvh_points(points,faces):
    triangles=[]
    for f in faces:
        for i in range(1,len(f)-1):triangles.append((f[0],f[i],f[i+1]))
    return BVHTree.FromPolygons(points,triangles,all_triangles=True),triangles
def bvh_objects(objects,evaluated=False):
    verts=[];faces=[];deps=bpy.context.evaluated_depsgraph_get() if evaluated else None
    for obj in objects:
        other=obj.evaluated_get(deps) if evaluated else obj;mesh=other.to_mesh() if evaluated else obj.data
        mesh.calc_loop_triangles();offset=len(verts);verts.extend(other.matrix_world@v.co for v in mesh.vertices);faces.extend(tuple(offset+i for i in t.vertices) for t in mesh.loop_triangles)
        if evaluated:other.to_mesh_clear()
    return BVHTree.FromPolygons(verts,faces,all_triangles=True)
def ray_at(bvh,x,z):return bvh.ray_cast(Vector((x,-1.,z)),Vector((0,1,0)),3.)[0]
def front_y(eye_bvh,skin_bvh,x,z):
    a=ray_at(eye_bvh,x,z);b,normal,_,_=skin_bvh.ray_cast(Vector((x,-1.,z)),Vector((0,1,0)),3.)
    # The preserved main shell has real eye holes: a ray just beyond the ribbon
    # can hit the BACK of the head. That is not a skin attachment surface.
    if b is not None and normal.y>=0:b=None
    if a is not None and b is not None:return min(a.y,b.y)
    if a is not None:return a.y
    if b is not None:return b.y
    p=unproportion(Vector((x,0,z)));return proportion(Vector((p.x,face_y(p.x,p.z),p.z))).y

def remove_static_lashes(obj):
    old=obj.data;state=mesh_state(obj);start=640+3927;removed=set(range(start,start+205))|set(range(start+403,start+608));kept=[i for i in range(len(old.vertices)) if i not in removed];remap={i:j for j,i in enumerate(kept)}
    assert len(removed)==410 and len(old.vertices)==5373
    # Match the exact v14 record, not an informal component-size heuristic.
    record=json.loads((ROOT/'art/generated/character-v14/candidate-manifest.json').read_text(encoding='utf-8'))['upperLashes']['allowedVertexIndices'];assert removed==set(record)
    polys=[p for p in old.polygons if not any(i in removed for i in p.vertices)];loops=[i for p in polys for i in p.loop_indices]
    assert all(all(i in removed for i in p.vertices) or all(i not in removed for i in p.vertices) for p in old.polygons)
    mesh=bpy.data.meshes.new('Head_Hair_Indigo_V15_NoStaticLashes');mesh.from_pydata([tuple(old.vertices[i].co) for i in kept],[],[tuple(remap[i] for i in p.vertices) for p in polys]);mesh.update()
    for m in old.materials:mesh.materials.append(m)
    for new,p in zip(mesh.polygons,polys):new.material_index=p.material_index;new.use_smooth=p.use_smooth
    for a in old.uv_layers:
        dst=mesh.uv_layers.new(name=a.name)
        for i,j in enumerate(loops):dst.data[i].uv=a.data[j].uv
    for a in old.color_attributes:
        dst=mesh.color_attributes.new(name=a.name,type=a.data_type,domain=a.domain)
        src=loops if a.domain=='CORNER' else kept
        for i,j in enumerate(src):dst.data[i].color=a.data[j].color
    assert all(not w for w in state['weights']),'Unexpected hair skin weights'
    mesh.normals_split_custom_set([tuple(old.corner_normals[i].vector) for i in loops]);obj.data=mesh;after=mesh_state(obj)
    assert after['coordinates']==[state['coordinates'][i] for i in kept]
    assert after['normals']==[state['normals'][i] for i in loops],'Protected true hair/brow corner normals changed'
    for a in old.uv_layers:assert after['uv'][a.name]==[state['uv'][a.name][i] for i in loops]
    for a in old.color_attributes:
        src=loops if a.domain=='CORNER' else kept;assert after['colors'][a.name]['values']==[state['colors'][a.name]['values'][i] for i in src]
    assert after['material_names']==state['material_names']
    return {'removedVertexCount':410,'removedVertexIndices':sorted(removed),'retainedVertices':len(kept),'retainedCoordinatesNormalsUVColoursExact':True,'retainedTopologyRemappedOnly':True,'sourcePreservedChannelsSHA256':digest({'coordinates':[state['coordinates'][i] for i in kept],'normals':[state['normals'][i] for i in loops],'uv':after['uv'],'colours':after['colors'],'topology':after['topology']})}

def build_cover_shapes(side,eye_bvh,skin_bvh):
    shapes={k:[] for k in KEYS};faces=[];grids=[]
    for upper in [True,False]:
        start=len(shapes['Basis']);grid=[]
        for row in range(ROWS+1):
            ids=[]
            for k in range(COUNT+1):
                if row and k in [0,COUNT]:ids.append(grid[0][k]);continue
                t=k/COUNT;x,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False);gap=up-low;meeting=low+.25*gap;bump=max(0,sin(pi*t));outer=(up+.00040*bump**.7) if upper else (low-.00040*bump**.7);r=row/ROWS
                index=len(shapes['Basis']);ids.append(index)
                for name,c in [('Basis',0),('BlinkHalf',.5),('BlinkClosed',1)]:
                    edge=(up-.75*c*gap) if upper else (low+.25*c*gap)
                    # Nonzero open strip under the pre-existing eyelid ribbon.
                    edge+=(-1 if upper else 1)*.00004*bump*(1-c)
                    z=outer*(1-r)+edge*r;p=proportion(Vector((x,0,z)));offset=.00007 if c==0 else .00019
                    p.y=front_y(eye_bvh,skin_bvh,p.x,p.z)-offset;shapes[name].append(p)
            grid.append(ids)
        for row in range(ROWS):
            for k in range(COUNT):
                # Upper advances down; lower advances up. Both face toward -Y.
                f=[grid[row][k],grid[row][k+1],grid[row+1][k+1],grid[row+1][k]]
                f=list(dict.fromkeys(f))
                if not upper:f.reverse()
                if side<0:f.reverse()
                f.reverse()
                assert len(f)>=3
                for j in range(1,len(f)-1):faces.append((f[0],f[j],f[j+1]))
        grids.append(grid)
    # At Closed, both moving boundaries share the same actual 3D seam.
    for a,b in zip(grids[0][-1],grids[1][-1]):
        p=shapes['BlinkClosed'][a];q=shapes['BlinkClosed'][b];assert (p-q).length<.0000001
        q.x=p.x;q.y=p.y;q.z=p.z
    return shapes,faces,grids

def repair_interpolation(shapes,faces,grids,eye_bvh):
    original={k:[p.copy() for p in shapes[k]] for k in KEYS};triangles=bvh_points(shapes['Basis'],faces)[1];history=[]
    for iteration in range(6):
        proposals={k:[0.]*len(shapes[k]) for k in KEYS};worst=0.;count=0
        for c in SAMPLES:
            points=mix_points(shapes,c);ws=weights(c);key='Basis' if c==0 else ('BlinkHalf' if c<=.5 else 'BlinkClosed');weight=ws[KEYS.index(key)]
            # Actual linear key interpolation, including triangle interiors.
            for tri in triangles:
                for bary in [(1,0,0),(.3333333333333333,)*3,(.5,.5,0),(0,.5,.5),(.5,0,.5)]:
                    p=sum((points[i]*b for i,b in zip(tri,bary)),Vector());hit=ray_at(eye_bvh,p.x,p.z)
                    if hit is None:continue
                    deficit=p.y-hit.y+.00010
                    if deficit<=.0000001:continue
                    worst=max(worst,deficit);count+=1
                    # Moving the three vertices equally moves every barycentric point.
                    for i in tri:proposals[key][i]=max(proposals[key][i],deficit/weight+.000015)
        history.append({'iteration':iteration,'violatingSamples':count,'maximumWorldYDeficit':worst})
        if count==0:break
        for key in KEYS:
            for i,delta in enumerate(proposals[key]):shapes[key][i].y-=delta
        for a,b in zip(grids[0][-1],grids[1][-1]):
            y=min(shapes['BlinkClosed'][a].y,shapes['BlinkClosed'][b].y);shapes['BlinkClosed'][a].y=shapes['BlinkClosed'][b].y=y
        maximum=max(original[k][i].y-p.y for k in KEYS for i,p in enumerate(shapes[k]));assert maximum<.001,('Interpolation needs excessive correction',maximum,history)
    assert history[-1]['violatingSamples']==0,history
    return {'history':history,'maximumAccumulatedWorldYCorrection':max(original[k][i].y-p.y for k in KEYS for i,p in enumerate(shapes[k])),'maximumAllowedCorrection':.001,'checkedClosureValues':SAMPLES,'seamClosedMaximumDistance':max((shapes['BlinkClosed'][a]-shapes['BlinkClosed'][b]).length for a,b in zip(grids[0][-1],grids[1][-1]))}

def lash_shapes(shapes,grids):
    output={k:[] for k in KEYS};faces=[]
    for key in KEYS:
        points=[];radii=[]
        for i,index in enumerate(grids[0][-1]):
            p=unproportion(shapes[key][index]);t=i/COUNT
            # Basis follows the old upper rim; animated edges sit on the thin skin.
            if key=='Basis':p.y=min(p.y,face_y(p.x,p.z)-.00134)
            p.y-=.00009;points.append(p);radii.append(.000035+.00017*max(0,sin(pi*t))**.85)
        base.tube_append(output[key],faces if key=='Basis' else [],points,radii,5)
        output[key]=[Vector(p) for p in output[key]]
    return output,faces

def source_colour_sampler(obj):
    mesh=obj.data;tree=KDTree(len(mesh.vertices));cols={}
    for a in mesh.color_attributes:
        if a.domain=='CORNER':
            accum=[Vector((0,0,0,0)) for v in mesh.vertices];counts=[0]*len(mesh.vertices)
            for loop in mesh.loops:accum[loop.vertex_index]+=Vector(a.data[loop.index].color);counts[loop.vertex_index]+=1
            cols[a.name]=[tuple(c/max(1,n)) for c,n in zip(accum,counts)]
        else:cols[a.name]=[tuple(d.color) for d in a.data]
    for v in mesh.vertices:
        p=obj.matrix_world@v.co;tree.insert((p.x,0,p.z),v.index)
    tree.balance();return tree,cols

def install_shapes(obj,shapes,faces):
    old=obj.data;mats=list(old.materials);sampler,cols=source_colour_sampler(obj);inv=obj.matrix_world.inverted();mesh=bpy.data.meshes.new(obj.name+'_V15_MorphLid');mesh.from_pydata([tuple(inv@p) for p in shapes['Basis']],[],faces);mesh.update()
    for m in mats:mesh.materials.append(m)
    for p in mesh.polygons:p.use_smooth=True
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        p=shapes['Basis'][loop.vertex_index];uv.data[loop.index].uv=(p.x*3+.5,p.z*2-1.7)
    for a in old.color_attributes:
        dst=mesh.color_attributes.new(name=a.name,type=a.data_type,domain=a.domain)
        for i,d in enumerate(dst.data):
            vertex=mesh.loops[i].vertex_index if a.domain=='CORNER' else i;p=shapes['Basis'][vertex];index=sampler.find((p.x,0,p.z))[1];d.color=cols[a.name][index]
    obj.data=mesh;obj.shape_key_add(name='Basis',from_mix=False)
    for key in KEYS[1:]:
        block=obj.shape_key_add(name=key,from_mix=False);block.relative_key=mesh.shape_keys.key_blocks['Basis'];block.value=0
        for v,p in zip(block.data,shapes[key]):v.co=inv@p
    mesh.shape_keys.use_relative=True
    assert [b.name for b in mesh.shape_keys.key_blocks]==KEYS
    return {'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),'shapeKeys':KEYS,'materials':[m.name for m in mats],'colours':'Copied from nearest original cover/lash vertex in XZ; original material graphs unchanged.','uv':'Reconstructed using original v11 world-space UV rule.'}

def set_blink(objects,c):
    w=weights(c)
    for name in TARGETS-{'Head_Hair_Indigo'}:
        obj=objects[name];keys=obj.data.shape_keys.key_blocks;keys['BlinkHalf'].value=w[1];keys['BlinkClosed'].value=w[2]
    bpy.context.view_layer.update()

def validate_actual(objects):
    eye=bvh_objects([objects['Head_Eye_'+n] for n in base.EYES]);samples=[]
    for side in [-1,1]:
        for i in range(1,48):
            t=i/48;x,up=eye_edge(side,t,True);_,low=eye_edge(side,t,False)
            for j in range(1,24):
                p=proportion(Vector((x,0,low+(up-low)*j/24)));hit=ray_at(eye,p.x,p.z)
                if hit is not None:samples.append(hit)
    records=[]
    for c in SAMPLES:
        set_blink(objects,c);cover=bvh_objects([objects['Blink_'+s+'_LidCover'] for s in ['L','R']],evaluated=True);gaps=[];miss=0;worst=None
        for p in samples:
            q=ray_at(cover,p.x,p.z)
            if q is None:miss+=1;continue
            g=p.y-q.y;gaps.append(g)
            if worst is None or g<worst['gap']:worst={'gap':g,'eye':list(p),'cover':list(q)}
        records.append({'closure':c,'weights':weights(c)[1:],'actualEyeSamples':len(samples),'coveredSamples':len(gaps),'projectionMisses':miss,'negativeGaps':sum(g<0 for g in gaps),'minimumWorldYGap':min(gaps,default=None),'worst':worst})
    set_blink(objects,0);assert all(r['negativeGaps']==0 for r in records),records;assert records[-1]['projectionMisses']==0 and len(samples)>0,records[-1]
    return {'passed':True,'records':records,'limits':'Finite frontal world-Y samples at nine closure values; not all viewpoints or continuous animation proof.'}

def export_fbx(root,materials):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root]+list(root.children_recursive):obj.select_set(True)
    bpy.context.view_layer.objects.active=root;saved=[]
    for name in materials:
        material=bpy.data.materials[name];bsdf=material.node_tree.nodes.get('Principled BSDF')
        for link in list(bsdf.inputs['Base Color'].links):saved.append((material,link.from_socket,bsdf.inputs['Base Color']));material.node_tree.links.remove(link)
    try:bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,object_types={'MESH','EMPTY','ARMATURE'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',use_mesh_modifiers=False,add_leaf_bones=False,bake_anim=False,primary_bone_axis='Y',secondary_bone_axis='X',colors_type='LINEAR',path_mode='COPY',embed_textures=True)
    finally:
        for material,a,b in saved:material.node_tree.links.new(a,b)
    bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))

def build():
    OUT.mkdir(parents=True,exist_ok=True);frozen=[SOURCE,ROOT/'art/generated/character-v14/traveler.fbx',ROOT/'art/generated/character-v11/traveler.blend',ROOT/'art/blender/build_traveler_v14.py'];hashes={str(p.relative_to(ROOT)):sha(p) for p in frozen};bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False);root=bpy.data.objects['TravelerRoot'];objects={o.name:o for o in root.children_recursive if o.type=='MESH'};before={n:mesh_state(o) for n,o in objects.items()};contract=object_contract(root);materials=sorted({m.name for o in objects.values() for m in o.data.materials});mat_before={n:material_state(bpy.data.materials[n]) for n in materials};pivot_before={s:{'location':list(bpy.data.objects['Blink_'+s].location),'rotation':list(bpy.data.objects['Blink_'+s].rotation_euler),'scale':list(bpy.data.objects['Blink_'+s].scale)} for s in ['L','R']}
    for s in ['L','R']:bpy.data.objects['Blink_'+s].scale=(1,1,1)
    bpy.context.view_layer.update();hair=remove_static_lashes(objects['Head_Hair_Indigo']);eyes=bvh_objects([objects['Head_Eye_'+n] for n in base.EYES]);skin=bvh_objects([objects['Head_Face_PorcelainCream']]);reports={}
    for side,label in [(-1,'L'),(1,'R')]:
        shapes,faces,grids=build_cover_shapes(side,eyes,skin);repair=repair_interpolation(shapes,faces,grids,eyes);report=install_shapes(objects['Blink_'+label+'_LidCover'],shapes,faces);ls,lf=lash_shapes(shapes,grids);lash=install_shapes(objects['Blink_'+label+'_ClosedLash'],ls,lf);reports[label]={'cover':report,'lash':lash,'repair':repair};print('MORPH_V15_SIDE '+json.dumps({'side':label,'repair':repair}),flush=True)
    actual=validate_actual(objects);rows=[]
    for name,obj in objects.items():
        if name not in TARGETS:assert before[name]==mesh_state(obj),name+' changed outside eyelid morph scope'
        rows.append({'mesh':name,'target':name in TARGETS,'unchanged':name not in TARGETS})
    after=object_contract(root)
    for name,data in contract.items():
        if name in ['Blink_L','Blink_R']:
            for key in data:
                if key!='basis':assert data[key]==after[name][key],name+' changed '+key
            label=name[-1];obj=bpy.data.objects[name];assert list(obj.location)==pivot_before[label]['location'] and list(obj.rotation_euler)==pivot_before[label]['rotation'];assert tuple(obj.scale)==(1,1,1)
        else:assert data==after[name],name+' object/bone/pivot contract changed'
    for name in materials:assert mat_before[name]==material_state(bpy.data.materials[name]),'Material graph changed '+name
    triangles=0
    for obj in objects.values():obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    assert triangles<120000;export_fbx(root,materials);unchanged={str(p.relative_to(ROOT)):sha(p)==hashes[str(p.relative_to(ROOT))] for p in frozen};assert all(unchanged.values())
    manifest={'revision':'character-v15','sourceChain':['character-v11 frozen head/body/hair','character-v14 open eyelid/5-eye geometry only','character-v15 animated lid/upper-lash topology'],'source':str(SOURCE.relative_to(ROOT)),'sourceSHA256':hashes[str(SOURCE.relative_to(ROOT))],'triangles':triangles,'targets':sorted(TARGETS),'protectedMeshCount':len(objects)-len(TARGETS),'meshDifferences':rows,'hair':hair,'eyelids':reports,'actualMorphSampling':actual,'blinkInterface':{'objects':['Blink_L','Blink_R'],'defaultScale':[1,1,1],'relativeKeys':['BlinkHalf','BlinkClosed'],'drive':'close<=.5: Half=2*close,Closed=0; close>.5: Half=2-2*close,Closed=2*close-1; values shown as 0..1, Unity uses 0..100.','sameKeyNamesOnFourMeshes':True,'upperClosureFraction':.75,'lowerClosureFraction':.25,'fixedEyeCornersAndWidth':True},'frozenInputsUnchanged':unchanged,'materialGraphsUnchanged':True,'allNonBlinkObjectBonePivotsUnchanged':True,'files':{},'limits':['Unaccepted geometry candidate; no Unity writes.','Uses rejected v14 only for its isolated open-eye geometry; v14 scale-cover failure is replaced entirely.','No normal gameplay, performance or overall visual superiority claim.','Finite sample clearance is not continuous/all-angle animation proof.','FBX exported with modifiers disabled to retain relative blend shapes; readback still required.'],'aestheticObjectiveAchieved':False}
    for p in [OUT/'traveler.blend',OUT/'traveler.fbx']:manifest['files'][p.name]={'sha256':sha(p),'bytes':p.stat().st_size}
    (OUT/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('MORPH_V15_BUILT '+json.dumps({'pid':os.getpid(),'triangles':triangles,'protectedMeshes':len(objects)-len(TARGETS)}),flush=True)

def render():
    records=[]
    for version,file in [('baseline',ROOT/'art/generated/character-v11/traveler.blend'),('candidate',OUT/'traveler.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(file),load_ui=False);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.seed=17;scene.cycles.use_animated_seed=False;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100;camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera;objects={o.name:o for o in bpy.data.objects['TravelerRoot'].children_recursive if o.type=='MESH'}
        views=[('three-quarter-open',(1.8,-3.7,1.45),0),('front-open',(0,-4,1.27),0)]
        if version=='candidate':views.extend([('front-quarter',(0,-4,1.27),.25),('front-half',(0,-4,1.27),.5),('front-threequarter',(0,-4,1.27),.75),('front-closed',(0,-4,1.27),1),('three-quarter-half',(1.8,-3.7,1.45),.5),('profile-half',(4,-.12,1.23),.5)])
        for view,position,c in views:
            if version=='candidate':set_blink(objects,c)
            else:
                for label in ['L','R']:bpy.data.objects['Blink_'+label].scale=(.001,.001,1)
            target=proportion(Vector((0,-.002,1.105)));camera.location=position;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.56;bpy.context.view_layer.update();conditions=base.preview_conditions(scene,camera);name=version+'-'+view+'.png';scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True);records.append({'version':version,'view':view,'closure':c,'file':name,'conditions':conditions});print('MORPH_V15_PREVIEW '+version+' '+view,flush=True)
    for view in ['front-open','three-quarter-open']:
        pair=[r for r in records if r['view']==view];assert pair[0]['conditions']==pair[1]['conditions'],'Preview camera/lights changed'
    (OUT/'preview-conditions.json').write_text(json.dumps({'sameCameraAndLights':True,'cpuOnly':True,'geometryOnly':True,'records':records},indent=2),encoding='utf-8')

if __name__=='__main__':
    print('MORPH_V15_PROCESS '+json.dumps({'pid':os.getpid(),'cpuThreadsMax':4,'source':str(SOURCE),'output':str(OUT)}),flush=True)
    if '--render-only' not in sys.argv:build()
    render()
