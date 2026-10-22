"""World-v7 derivative: only lavender and fern geometry; no renderer/runtime edits."""
import bpy, math, json, hashlib, argparse, sys, random, shutil, struct
from pathlib import Path
from collections import Counter, defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/world-v7'
OUT=ROOT/'art/generated/world-v8'; OUT.mkdir(parents=True,exist_ok=True)
TARGETS={'Garden_LavenderAndSeedHeads','Garden_FeatherFerns'}
parser=argparse.ArgumentParser()
parser.add_argument('--inspect-only',action='store_true')
parser.add_argument('--verify-only',action='store_true')
opts=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return Vector((p[0],p[2],-p[1]))
def fingerprint(obj):
    m=obj.data
    payload={'matrix':[list(r) for r in obj.matrix_world],
      'vertices':[list(v.co) for v in m.vertices],'faces':[list(p.vertices) for p in m.polygons],
      'mi':[p.material_index for p in m.polygons],'smooth':[p.use_smooth for p in m.polygons],
      'mats':[x.name for x in m.materials],
      'uv':[[list(d.uv) for d in uv.data] for uv in m.uv_layers],
      'colours':[[a.name,a.domain,a.data_type,[list(c.color) for c in a.data]] for a in m.color_attributes],
      'normals':hashlib.sha256(np.asarray([tuple(n.vector) for n in m.corner_normals],dtype='<f4').tobytes()).hexdigest()}
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()
def components(obj):
    m=obj.data;adj=[[] for _ in m.vertices]
    for e in m.edges:
        a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    groups=[];seen=set();vertex_group={}
    for i in range(len(adj)):
        if i in seen:continue
        ids=[];stack=[i];seen.add(i)
        while stack:
            j=stack.pop();ids.append(j);vertex_group[j]=len(groups)
            for k in adj[j]:
                if k not in seen:seen.add(k);stack.append(k)
        groups.append({'vertices':ids,'faces':[]})
    for p in m.polygons:groups[vertex_group[p.vertices[0]]]['faces'].append(p.index)
    return groups
def stem_axes(obj):
    result=[];groups=components(obj);m=obj.data
    for group in groups:
        faces=[m.polygons[i] for i in group['faces']]
        mats={m.materials[p.material_index].name for p in faces}
        if mats!={'BI_stem'}:continue
        points=[U(obj.matrix_world@m.vertices[i].co) for i in group['vertices']]
        # Frozen triangular/four-sided stems have two tiny polygonal end caps.
        caps=[]
        for p in faces:
            pp=[U(obj.matrix_world@m.vertices[i].co) for i in p.vertices]
            diameter=max((a-b).length for a in pp for b in pp)
            if diameter<(.013 if len(points)==8 else .006):
                caps.append(sum(pp,Vector())/len(pp))
        # BLEND stems are triangulated: merge coincident cap centroids by using
        # axial farthest pair and classify original ring vertices instead.
        center=sum(points,Vector())/len(points)
        arr=np.asarray([tuple(p-center) for p in points]);_,_,vh=np.linalg.svd(arr,full_matrices=False)
        axis=Vector(vh[0]);projections=[(p-center).dot(axis) for p in points]
        low=[p for p,t in zip(points,projections) if t<0]
        high=[p for p,t in zip(points,projections) if t>=0]
        assert len(low)==len(high) and len(low) in (3,4),(obj.name,len(points),len(low))
        a=sum(low,Vector())/len(low);b=sum(high,Vector())/len(high)
        if a.y>b.y:a,b=b,a
        result.append({'a':list(a),'b':list(b),'vertices':len(points),'length':(b-a).length})
    return result,groups
def extract_specs():
    lavender,lg=stem_axes(bpy.data.objects['Garden_LavenderAndSeedHeads'])
    fern,fg=stem_axes(bpy.data.objects['Garden_FeatherFerns'])
    stems=[]
    for s in fern:
        stems.append([Vector(s['a']),Vector(s['b'])])
    # Segment endpoints are welded logically, not physically. The original
    # fronds are separate triangular tubes and all four share their root.
    nodes=[];edges=[]
    for a,b in stems:
        ids=[]
        for p in [a,b]:
            nearby=next((i for i,q in enumerate(nodes) if (q-p).length<2e-5),None)
            if nearby is None:nearby=len(nodes);nodes.append(p)
            ids.append(nearby)
        edges.append(tuple(ids))
    adj=defaultdict(list)
    for a,b in edges:adj[a].append(b);adj[b].append(a)
    used=set();fronds=[]
    # Root degree four is authoritative. A partial root after local v5 cleanup
    # can have lower degree; those fragments are recorded, not invented.
    roots=[i for i in adj if len(adj[i])>=3]
    for root in roots:
        for neighbor in adj[root]:
            chain=[root,neighbor];used.add(tuple(sorted((root,neighbor))))
            while len(adj[chain[-1]])==2:
                nxt=next(x for x in adj[chain[-1]] if x!=chain[-2])
                key=tuple(sorted((chain[-1],nxt)))
                if key in used:break
                used.add(key);chain.append(nxt)
            fronds.append({'root':list(nodes[root]),'points':[list(nodes[i]) for i in chain],
              'segments':len(chain)-1,'root_degree':len(adj[root])})
    remnants=[list(e) for e in edges if tuple(sorted(e)) not in used]
    report={'lavender':lavender,'lavender_stems':len(lavender),
      'lavender_component_sizes':dict(Counter(len(g['vertices']) for g in lg)),
      'fern_stem_segments':len(stems),'fern_roots':[list(nodes[i]) for i in roots],
      'fern_fronds':fronds,'fern_frond_segment_counts':dict(Counter(f['segments'] for f in fronds)),
      'fern_component_sizes':dict(Counter(len(g['vertices']) for g in fg)),
      'fern_unassigned_segments':remnants,'fern_node_degrees':dict(Counter(len(v) for v in adj.values()))}
    (OUT/'frozen-plant-specs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FROZEN_PLANTS',json.dumps({k:v for k,v in report.items() if k not in ['lavender','fern_roots','fern_fronds']},ensure_ascii=False),flush=True)
    return report

class PlantMesh:
    def __init__(self,name,materials):
        self.name=name;self.materials=materials;self.vertices=[];self.faces=[];self.mi=[];self.colours=[]
    def add(self,vs,fs,material,tints=None,up=False):
        offset=len(self.vertices)
        self.vertices.extend([B(p) for p in vs])
        self.colours.extend(tints or [(1,1,1,1)]*len(vs))
        for face in fs:
            f=tuple(face)
            if up and (Vector(vs[f[1]])-Vector(vs[f[0]])).cross(Vector(vs[f[2]])-Vector(vs[f[0]])).y<0:f=tuple(reversed(f))
            self.faces.append(tuple(offset+i for i in f));self.mi.append(self.materials.index(material))
    def mark(self):return len(self.vertices),len(self.faces)
    def rewind(self,mark):
        nv,nf=mark;del self.vertices[nv:];del self.colours[nv:];del self.faces[nf:];del self.mi[nf:]
    def tube(self,points,radii,material,segments=5,tint=1.):
        vs=[];fs=[]
        for i,p in enumerate(points):
            tangent=points[min(i+1,len(points)-1)]-points[max(0,i-1)]
            tangent.normalize();ref=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
            u=tangent.cross(ref).normalized();v=tangent.cross(u).normalized()
            for j in range(segments):
                ang=math.tau*j/segments;vs.append(p+(u*math.cos(ang)+v*math.sin(ang))*radii[i])
        for i in range(len(points)-1):
            for j in range(segments):
                a=i*segments+j;b=i*segments+(j+1)%segments;c=b+segments;d=a+segments
                fs.extend([(a,b,c),(a,c,d)])
        # Outward ring winding is (u,v) around the tangent.
        for j in range(1,segments-1):
            fs.append((0,j+1,j));a=(len(points)-1)*segments;fs.append((a,a+j,a+j+1))
        self.add(vs,fs,material,[(tint,tint,tint,1)]*len(vs))
    def finish(self):
        ob=bpy.data.objects[self.name];old=ob.data;old_name=old.name
        assert all(abs(ob.matrix_world[i][j]-(1 if i==j else 0))<1e-8 for i in range(4) for j in range(4))
        me=bpy.data.meshes.new(self.name+'_v8');me.from_pydata(self.vertices,[],self.faces)
        for name in self.materials:me.materials.append(bpy.data.materials[name])
        for p,mi in zip(me.polygons,self.mi):p.material_index=mi;p.use_smooth=True
        uv=me.uv_layers.new(name='WatercolorUV')
        for loop in me.loops:
            co=me.vertices[loop.vertex_index].co;uv.data[loop.index].uv=((co.x+9)/18,(-co.y+9)/18)
        colour=me.color_attributes.new(name='BL_FoliageTint',type='FLOAT_COLOR',domain='CORNER')
        for loop in me.loops:colour.data[loop.index].color=self.colours[loop.vertex_index]
        me.color_attributes.active_color=colour;me.update();ob.data=me
        if old.users==0:bpy.data.meshes.remove(old)
        me.name=old_name
        return ob

def make_bvh(name):
    ob=bpy.data.objects[name]
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],
      [tuple(p.vertices) for p in ob.data.polygons],all_triangles=False)

def generate(specs):
    baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
    for name in ['island.blend','island.fbx','island.glb']:
        assert sha(BASE/name)==baseline['sha256'][name], 'Frozen source changed: '+name
    before={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    anchors={o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    obstacles={name:make_bvh(name) for name in ['Garden_HeroBoulders','Garden_Walkways','Observatory_StoneAndBrass','Cliff_Pier']}
    def blocked(builder,start):
        # Actual frozen geometry projection at generated vertices: prevents a
        # bent stem or leaf entering the walking surface or a Hero rock volume.
        counts=Counter()
        for co in builder.vertices[start:]:
            for name,bvh in obstacles.items():
                if bvh.ray_cast(Vector((co.x,co.y,4.0)),Vector((0,0,-1)),6)[0] is not None:
                    counts[name]+=1;break
        return dict(counts)
    rng=random.Random(11082026);lav=PlantMesh('Garden_LavenderAndSeedHeads',['BI_stem','BI_flower_lilac'])
    lavender_report=[]
    for index,spec in enumerate(specs['lavender']):
        root=Vector(spec['a']);height=spec['b'][1]-root.y
        phase=rng.uniform(0,math.tau);lean=Vector((math.cos(phase),0,math.sin(phase)))*rng.uniform(.018,.048)
        jitter=[rng.uniform(-.07,.07) for _ in range(8)];stage_counts=[4,4,5,4,4,3,2,1]
        scale=rng.uniform(.90,1.08);plant_mark=lav.mark();tries=[]
        for bend_scale in [1.,.65,.25,0.]:
            lav.rewind(plant_mark)
            def axis(t):return root+Vector((0,height*t,0))+lean*bend_scale*(t*t)
            stem=[axis(k/9) for k in range(10)]
            lav.tube(stem,[.0030*(1-.68*k/9) for k in range(10)],'BI_stem',5)
            flowers=0
            for tier,count in enumerate(stage_counts):
                t=.65+.33*tier/7+jitter[tier]*.04
                taper=1.-.53*(tier/7)**1.8
                for j in range(count):
                    ang=phase+tier*2.39996+math.tau*j/count+.13*math.sin(index*3.1+j*5.3)
                    radial=Vector((math.cos(ang),0,math.sin(ang)))
                    flower_axis=(radial*.92+Vector((0,.39+.18*tier/7,0))).normalized()
                    attach=axis(t)+radial*.0012
                    base=attach+flower_axis*(.0065*taper)
                    lav.tube([attach,base],[.0010*taper,.0008*taper],'BI_stem',3)
                    # Five round-ended lips surrounding a shallow throat. Small
                    # scalloped outline, not an elongated faceted ellipsoid.
                    up=Vector((0,1,0));u=flower_axis.cross(up).normalized();v=flower_axis.cross(u).normalized()
                    length=.009*scale*taper;radius=.0077*scale*taper
                    vs=[base-flower_axis*.001]
                    for k in range(5):
                        a=math.tau*k/5;vs.append(base+flower_axis*(length*.22)+(u*math.cos(a)+v*math.sin(a))*(radius*.34))
                    for k in range(10):
                        a=math.tau*k/10;rr=radius*(1 if k%2==0 else .62)
                        vs.append(base+flower_axis*length*(1 if k%2==0 else .78)+(u*math.cos(a)+v*math.sin(a))*rr)
                    vs.append(base+flower_axis*(length*.64))
                    fs=[]
                    for k in range(5):
                        a=1+k;b=1+(k+1)%5;c=6+2*k;d=6+(2*k+1)%10;e=6+(2*k+2)%10
                        fs.extend([(0,b,a),(a,b,d),(a,d,c),(b,e,d)])
                    for k in range(10):fs.append((16,6+k,6+(k+1)%10))
                    lav.add(vs,fs,'BI_flower_lilac');flowers+=1
            hits=blocked(lav,plant_mark[0]);tries.append({'bend_scale':bend_scale,'blocked':hits})
            if not hits:break
        if hits:lav.rewind(plant_mark)
        lavender_report.append({'index':index,'root_unity':list(root),'height':height,'flower_count':flowers if not hits else 0,
          'retained':not hits,'tries':tries})
    lav_obj=lav.finish()
    fern=PlantMesh('Garden_FeatherFerns',['BI_stem','BI_leaf','BI_grass_sage','BI_leaf_light'])
    fern_report=[]
    for index,old in enumerate(specs['fern_fronds']):
        # Incomplete old fronds were already removed around rocks. Do not
        # reconstruct their missing growth or retain floating cut-off segments.
        if old['segments']!=8:
            fern_report.append({'index':index,'retained':False,'reason':'frozen partial frond omitted'});continue
        root=Vector(old['root']);oldtip=Vector(old['points'][-1]);direction=oldtip-root;direction.y=0
        length=direction.length;direction.normalize();side=Vector((-direction.z,0,direction.x))
        frond_mark=fern.mark();base_tint=rng.uniform(.89,.98);phase=rng.uniform(0,math.tau)
        pinna_shapes=[(rng.uniform(.9,1.12),rng.uniform(-.014,.014),rng.choice(['BI_leaf','BI_leaf','BI_leaf_light','BI_grass_sage'])) for _ in range(22)]
        tries=[]
        for extent in [1.,.88,.72,.55]:
            fern.rewind(frond_mark);L=length*extent
            def axis(t):
                return root+direction*(L*t)+side*(math.sin(t*math.pi)*L*.045*math.sin(phase))+Vector((0,math.sin(t*math.pi*.91)*L*.61,0))
            points=[axis(k/12) for k in range(13)]
            fern.tube(points,[.0020*(1-.78*k/12) for k in range(13)],'BI_stem',4,.93)
            for rank in range(11):
                for ss in [-1,1]:
                    variation,offset,material=pinna_shapes[rank*2+(ss==1)]
                    t=.115+rank*.074+(ss==1)*.021+offset
                    p=axis(t);ll=L*.265*(math.sin(math.pi*t)**.72)*variation
                    width=ll*.118
                    sweep=direction*(L*(.025+.050*t))
                    end=p+side*ll*ss+sweep+Vector((0,-ll*(.12+.16*t),0))
                    heading=(end-p).normalized();cross=Vector((-heading.z,0,heading.x)).normalized()
                    vs=[p];tints=[(base_tint*.89,)*3+(1,)]
                    for s in [.23,.51,.77]:
                        c=p.lerp(end,s)+Vector((0,math.sin(s*math.pi)*ll*.115,0))
                        w=width*(math.sin(s*math.pi)**.72)
                        # Three points per cross-section give a mild convex
                        # midrib, smooth within each feather; no giant flat fan.
                        for sign in [-1,0,1]:
                            q=c+cross*(w*sign)+Vector((0,(-.016 if sign else .026)*ll*math.sin(s*math.pi),0))
                            vs.append(q);tint=base_tint*(.90+.10*s);tints.append((tint,tint,tint,1))
                    vs.append(end);tints.append((base_tint,base_tint,base_tint,1))
                    fs=[(0,1,2),(0,2,3)]
                    for k in range(2):
                        a=1+k*3;b=a+3;fs.extend([(a,b,b+1),(a,b+1,a+1),(a+1,b+1,b+2),(a+1,b+2,a+2)])
                    fs.extend([(7,10,8),(8,10,9)])
                    fern.add(vs,fs,material,tints,up=True)
            hits=blocked(fern,frond_mark[0]);tries.append({'extent':extent,'blocked':hits})
            if not hits:break
        if hits:fern.rewind(frond_mark)
        fern_report.append({'index':index,'root_unity':list(root),'original_length':length,'retained':not hits,'tries':tries})
    fern_obj=fern.finish()
    after={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    assert before==after,'Non-target geometry/material/UV/colour/normal changed'
    assert anchors=={o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    objects=[];triangles=0;colours=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        me=ob.data;me.calc_loop_triangles();nt=len(me.loop_triangles);triangles+=nt
        assert all(t.area>1e-12 for t in me.loop_triangles), 'Degenerate '+ob.name
        assert len({tuple(sorted(t.vertices)) for t in me.loop_triangles})==nt,'Duplicate triangle '+ob.name
        objects.append({'name':ob.name,'vertices':len(me.vertices),'triangles':nt,'materials':[m.name for m in me.materials]})
        a=me.color_attributes.active_color;rgb=[x for c in a.data for x in c.color[:3]]
        colours.append({'mesh':ob.name,'domain':a.domain,'type':a.data_type,'min_rgb':min(rgb),'max_rgb':max(rgb)})
    assert len(objects)==29 and len(anchors)==14 and triangles<=550000
    target_checks={name:blocked(builder,0) for name,builder in [('Garden_LavenderAndSeedHeads',lav),('Garden_FeatherFerns',fern)]}
    assert not any(target_checks.values()),target_checks
    texture_names=['meadow-watercolor.png','meadow-normal.png'];(OUT/'textures').mkdir(exist_ok=True)
    for name in texture_names:shutil.copy2(BASE/'textures'/name,OUT/'textures'/name)
    for image in bpy.data.images:
        name=Path(image.filepath).name
        if name in texture_names:image.filepath='//textures/'+name
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','EMPTY']:ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
      axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,
      mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,path_mode='COPY',embed_textures=True,colors_type='LINEAR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,
      export_apply=True,export_materials='EXPORT',export_cameras=False,export_lights=False,
      export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    files=['island.blend','island.fbx','island.glb']+['textures/'+name for name in texture_names]
    report={'revision':'world-v8','game_candidate':'v11','source':'world-v7','triangles':triangles,'triangle_budget':550000,
      'objects':objects,'anchors_unity':baseline['anchors_unity'],'vertex_colors':colours,
      'changed_meshes':sorted(TARGETS),'unchanged_non_target_fingerprints':before,'anchors_frozen':anchors,
      'design_changes':['68 frozen lavender roots: curved fine stem, 27 staggered miniature five-lobed corollas per retained plant, tapering spike.',
        'Fern roots and directions recovered from frozen stem graph: curved rachis, alternate narrow pinnae with convex midrib and downturned ends.',
        'Two target meshes only. No grass density, world lighting, shader, collider, texture or non-target geometry changes.'],
      'lavender':lavender_report,'ferns':fern_report,
      'omitted_old_orphan_fern_segments':len(specs['fern_unassigned_segments']),
      'obstacle_projection_checks':target_checks,'obstacle_test_scope':'Every generated vertex projected against actual frozen Hero, walkways, observatory and pier; conservative whole-plant/frond shrink or omission. No runtime collision claim.',
      'materials_changed':[],'materials_added':[],'renderer_count_change':0,
      'textures_byte_identical':{name:sha(OUT/'textures'/name)==sha(BASE/'textures'/name) for name in texture_names},
      'files':files,'sha256':{name:sha(OUT/name) for name in files},'baseline_sha256':baseline['sha256'],
      'verification_pending':True,'visual_review_pending':'No render or Unity action performed. Root must compare the same FoliageStudy path/roots/lamp cameras.'}
    (OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WORLD_V8_EXPORTED',triangles,'LAVENDER',objects[[o['name'] for o in objects].index(lav.name)],'FERN',objects[[o['name'] for o in objects].index(fern.name)],flush=True)

if __name__=='__main__':
    if opts.verify_only:
        import runpy
        runpy.run_path(str(OUT/'verify_world_v8.py'),run_name='__main__')
    else:
        bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
        specs=extract_specs()
        if not opts.inspect_only:generate(specs)
