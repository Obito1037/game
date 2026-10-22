"""World-v8 derivative: clustered meadow grass and low creeping leaves only."""
import bpy, math, json, hashlib, argparse, sys, random, shutil
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/world-v8';OUT=ROOT/'art/generated/world-v9'
TARGETS={'Garden_GrassTufts','Garden_CreepingMeadowLeaves'}
parser=argparse.ArgumentParser();parser.add_argument('--inspect-only',action='store_true');parser.add_argument('--verify-only',action='store_true')
opts=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return Vector((p[0],p[2],-p[1]))
def fingerprint(obj):
    m=obj.data
    payload={'matrix':[list(r) for r in obj.matrix_world],'vertices':[list(v.co) for v in m.vertices],
      'faces':[list(p.vertices) for p in m.polygons],'mi':[p.material_index for p in m.polygons],
      'smooth':[p.use_smooth for p in m.polygons],'mats':[x.name for x in m.materials],
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
def make_bvh(name):
    ob=bpy.data.objects[name]
    return BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],
      [tuple(p.vertices) for p in ob.data.polygons],all_triangles=False)
def extract_roots():
    ground=make_bvh('Island_Meadow');result={};summary={}
    for name in sorted(TARGETS):
        ob=bpy.data.objects[name];m=ob.data;groups=components(ob);items=[];kinds=Counter();clearances=[]
        for group in groups:
            points=[U(ob.matrix_world@m.vertices[i].co) for i in group['vertices']]
            mat=m.materials[m.polygons[group['faces'][0]].material_index].name
            nv=len(points);kind=(nv,len(group['faces']));kinds[str(kind)]+=1
            order=sorted(range(nv),key=lambda i:points[i].y)
            if name=='Garden_GrassTufts' and nv in (7,9):root=(points[order[0]]+points[order[1]])*.5
            elif name=='Garden_GrassTufts' and nv==13:root=points[order[0]]+Vector((0,.003,0))
            elif name=='Garden_CreepingMeadowLeaves' and nv==9:root=points[order[0]].copy()
            else:raise RuntimeError('Unexpected frozen component '+name+' '+str(kind))
            co=B(root);hit=ground.ray_cast(Vector((co.x,co.y,2)),Vector((0,0,-1)),4)[0]
            clearance=None if hit is None else root.y-hit.z
            if clearance is not None:clearances.append(clearance)
            items.append({'root_unity':list(root),'kind':list(kind),'material':mat,
              'height':max(p.y for p in points)-root.y,'ground_clearance':clearance})
        result[name]=items;summary[name]={'components':len(groups),'kinds':dict(kinds),
          'root_ground_clearance_min':min(clearances),'max':max(clearances),'mean':sum(clearances)/len(clearances),
          'missing_ground_hits':len(items)-len(clearances)}
    (OUT/'frozen-root-cloud.json').write_text(json.dumps({'summary':summary,'roots':result},ensure_ascii=False,indent=2),encoding='utf-8')
    print('FROZEN_ROOTS',json.dumps(summary),flush=True)
    return result

class PlantMesh:
    def __init__(self,name):
        self.name=name;self.materials=[m.name for m in bpy.data.objects[name].data.materials]
        self.vertices=[];self.faces=[];self.mi=[];self.colours=[];self.parts=[]
    def add(self,vs,fs,material,colours,root,kind):
        start=len(self.vertices);face_start=len(self.faces)
        self.vertices.extend([B(p) for p in vs]);self.colours.extend(colours)
        for face in fs:
            f=tuple(face)
            if (vs[f[1]]-vs[f[0]]).cross(vs[f[2]]-vs[f[0]]).y<0:f=tuple(reversed(f))
            self.faces.append(tuple(start+i for i in f));self.mi.append(self.materials.index(material))
        self.parts.append({'root_unity':list(root),'vertex_start':start,'vertex_count':len(vs),
          'face_start':face_start,'face_count':len(fs),'kind':kind})
    def finish(self):
        ob=bpy.data.objects[self.name];old=ob.data;old_name=old.name
        assert all(abs(ob.matrix_world[i][j]-(1 if i==j else 0))<1e-8 for i in range(4) for j in range(4))
        me=bpy.data.meshes.new(self.name+'_candidate');me.from_pydata(self.vertices,[],self.faces)
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

def percentile_report(values):
    a=np.asarray(values,dtype=float)
    return {'count':len(values),'min':float(a.min()),'p05':float(np.percentile(a,5)),
      'median':float(np.median(a)),'p95':float(np.percentile(a,95)),
      'p99':float(np.percentile(a,99)),'max':float(a.max()),'mean':float(a.mean())}
def patch(x,z):
    # Two broad, warped bands plus a restrained secondary scale; no circular
    # flowerbeds, cell boundaries, uniform density or per-leaf white noise.
    return max(0,min(1,.50+.25*math.sin(x*1.13+.62*math.sin(z*1.4))+
      .22*math.sin(z*1.47-x*.56)+.08*math.sin(x*3.8+z*2.6)))

ROUTES=[[(0,-6),(0,-3.6),(-1,-1.7),(-1.7,-.8)],
  [(-1,.9),(-2.4,1.8),(-3.9,2.5),(-4.1,2.9)],
  [(1.6,0),(3.6,-.4),(5.4,-1.8),(6.1,-3.35)],
  [(-1.6,-.3),(-3.7,-.4),(-5.8,.1)]]
SEGMENTS=[(Vector((a[0],0,a[1])),Vector((b[0],0,b[1]))) for route in ROUTES for a,b in zip(route,route[1:])]
def route_distance(p):
    p=Vector((p.x,0,p.z));distance=100.
    for a,b in SEGMENTS:
        d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));distance=min(distance,(p-(a+d*t)).length)
    return distance

def generate(roots):
    baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
    for name in ['island.blend','island.fbx','island.glb']:assert sha(BASE/name)==baseline['sha256'][name]
    before={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    anchors={o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    ground=make_bvh('Island_Meadow')
    obstacle_names=['Garden_HeroBoulders','Garden_Walkways','Observatory_StoneAndBrass','Cliff_Pier',
      'LampBase_A','LampBase_B','LampBase_C','Cabin_PlasterAndFoundation','Cabin_Timber','Garden_Bench','Garden_TreeTrunks']
    obstacles={name:make_bvh(name) for name in obstacle_names}
    obstacle_bounds={}
    for name in obstacle_names:
        ob=bpy.data.objects[name];coords=[U(ob.matrix_world@v.co) for v in ob.data.vertices]
        obstacle_bounds[name]=(min(p.x for p in coords),max(p.x for p in coords),min(p.z for p in coords),max(p.z for p in coords))
    def ground_y(x,z):
        hit=ground.ray_cast(Vector((x,-z,2)),Vector((0,0,-1)),4)[0]
        return None if hit is None else hit.z
    exclusion=Counter();sample_counts=Counter()
    def blocked(vs,fs):
        # Check vertices and triangle centres. Vertical tests are restricted to
        # the plant-height slab so overhead tree branches do not clear soil.
        max_y=max(p.y for p in vs)+.003;min_y=min(p.y for p in vs)-.025
        points=list(vs)+[sum((vs[i] for i in f),Vector())/3 for f in fs]
        for p in points:
            sample_counts['obstacle_and_route_samples']+=1
            if route_distance(p)<.22:exclusion['route_core']+=1;return True
            for name,bvh in obstacles.items():
                x0,x1,z0,z1=obstacle_bounds[name]
                if not(x0<=p.x<=x1 and z0<=p.z<=z1):continue
                if bvh.ray_cast(Vector((p.x,-p.z,max_y)),Vector((0,0,-1)),max_y-min_y)[0] is not None:
                    exclusion[name]+=1;return True
        return False
    def choose_centers(items,rng,kind):
        order=list(range(len(items)));rng.shuffle(order);grid=defaultdict(list);centers=[];cell=.12
        for index in order:
            item=items[index];p=Vector(item['root_unity']);density=patch(p.x,p.z)
            # Definite gaps at the quiet tail; gradual spacing everywhere else.
            if density<(.23 if kind=='grass' else .18):continue
            if ground_y(p.x,p.z) is None or route_distance(p)<.27:continue
            spacing=(.077+.052*(1-density)) if kind=='grass' else (.14+.045*(1-density))
            gx,gz=math.floor(p.x/cell),math.floor(p.z/cell)
            nearby=[entry for x in range(gx-2,gx+3) for z in range(gz-2,gz+3) for entry in grid[(x,z)]]
            if any((p.x-q.x)**2+(p.z-q.z)**2<((spacing+r)*.5)**2 for q,r in nearby):continue
            p.y=ground_y(p.x,p.z)-.0008;grid[(gx,gz)].append((p,spacing));centers.append((p,density,item,index))
        return centers
    rng=random.Random(12092026);grass=PlantMesh('Garden_GrassTufts');cover=PlantMesh('Garden_CreepingMeadowLeaves')
    grass_centers=choose_centers(roots[grass.name],rng,'grass');cover_centers=choose_centers(roots[cover.name],rng,'cover')
    cluster_records={grass.name:[],cover.name:[]};root_clearances=[];root_edge_clearances=[];cover_surface_clearances=[]
    skipped=Counter();grass_height=[];drooping=0
    for ci,(center,density,source,index) in enumerate(grass_centers):
        orientation=.6+.62*math.sin(center.x*.47+center.z*.29)+rng.uniform(-.9,.9)
        main_dir=Vector((math.cos(orientation),0,math.sin(orientation)));main_side=Vector((-main_dir.z,0,main_dir.x))
        count=3+round(density*3)+rng.randrange(3)
        low=rng.random()<.43;height=rng.uniform(.055,.11) if low else rng.uniform(.11,.21)
        if not low and rng.random()<.13:height=rng.uniform(.20,.285)
        height*=.87+.20*density;spread=rng.uniform(.010,.026)
        material=source['material'];cluster_tint=rng.uniform(.91,1.0);kept=0
        for j in range(count):
            if len(grass.faces)+7>215804:skipped['grass_budget_cap']+=1;continue
            angle=orientation+(j-(count-1)*.5)*rng.uniform(.58,.94)+rng.uniform(-.34,.34)
            bend=Vector((math.cos(angle),0,math.sin(angle)));side=Vector((-bend.z,0,bend.x))
            root=center+main_dir*rng.uniform(-spread,spread)+main_side*rng.uniform(-spread*.54,spread*.54)
            gy=ground_y(root.x,root.z)
            if gy is None:skipped['grass_no_ground']+=1;continue
            root.y=gy-.0008;h=height*rng.uniform(.56,1.18);lean=h*rng.uniform(.48,1.02)
            droop=rng.random()<.33;arc=rng.uniform(1.88,2.12) if droop else rng.uniform(1.35,1.67)
            width=rng.uniform(.0023,.0049)*(.83 if h<.07 else 1.)
            vs=[];colours=[];valid=True
            for t in [0,.25,.53,.79]:
                c=root+Vector((0,h*math.sin(t*arc),0))+bend*(lean*t**1.75)
                c+=side*(h*.055*math.sin(math.pi*t)*math.sin(ci*.7))
                ribbon=side*math.cos(t*.22)+bend*math.sin(t*.22)
                w=width*(.18+.82*math.sin(min(1.,t/.35)*math.pi*.5))*(1-t)**.63
                for sign in [-1,1]:
                    p=c+ribbon*w*sign;ground_height=ground_y(p.x,p.z)
                    if ground_height is None:valid=False;break
                    if t==0:p.y=ground_height-.0008
                    elif p.y<ground_height+.0007:p.y=ground_height+.0007
                    vs.append(p);shade=cluster_tint*(.84+.16*t);colours.append((shade,shade,shade,1))
                if not valid:break
            if not valid:skipped['grass_edge_no_ground']+=1;continue
            tip=root+Vector((0,h*math.sin(arc),0))+bend*lean
            tip_ground=ground_y(tip.x,tip.z)
            if tip_ground is None:skipped['grass_tip_no_ground']+=1;continue
            if tip.y<tip_ground+.001:tip.y=tip_ground+.001
            vs.append(tip);colours.append((cluster_tint,cluster_tint,cluster_tint,1))
            fs=[(0,1,3),(0,3,2),(2,3,5),(2,5,4),(4,5,7),(4,7,6),(6,7,8)]
            if blocked(vs,fs):skipped['grass_obstacle_or_route']+=1;continue
            grass.add(vs,fs,material,colours,root,'curved_grass');grass.parts[-1]['cluster_index']=ci;kept+=1
            root_clearances.append(root.y-gy);root_edge_clearances.extend([vs[k].y-ground_y(vs[k].x,vs[k].z) for k in (0,1)])
            grass_height.append(max(p.y for p in vs)-root.y)
            if tip.y<max(p.y for p in vs)-.002:drooping+=1
        cluster_records[grass.name].append({'center_unity':list(center),'source_root_index':index,'density_field':density,
          'height_class':'low' if low else 'tall','kept_blades':kept})
    for ci,(center,density,source,index) in enumerate(cover_centers):
        orientation=rng.uniform(0,math.tau);count=rng.choice([2,3,3,4]);kept=0
        for j in range(count):
            if len(cover.faces)+8>31984:skipped['cover_budget_cap']+=1;continue
            angle=orientation+j*2.39996+rng.uniform(-.52,.52);direction=Vector((math.cos(angle),0,math.sin(angle)))
            side=Vector((-direction.z,0,direction.x));root=center+direction*rng.uniform(-.006,.009)+side*rng.uniform(-.006,.006)
            gy=ground_y(root.x,root.z)
            if gy is None:skipped['cover_no_ground']+=1;continue
            root.y=gy-.0006;length=rng.uniform(.056,.125);paddle=rng.random()<.24
            width=length*(rng.uniform(.22,.29) if paddle else rng.uniform(.13,.22))
            bend=rng.uniform(-.16,.16)*length;asymmetry=rng.uniform(.73,1.18);vs=[root];valid=True
            for t,ss in [(.18,1),(.49,1),(.81,1),(1,0),(.78,-1),(.46,-1),(.16,-1)]:
                c=root+direction*length*t+side*(bend*math.sin(math.pi*t*.8))
                profile=math.sin(math.pi*t)**(.72 if paddle else .88)
                if t==1:profile=0
                c+=side*width*profile*ss*(asymmetry if ss>0 else 1)
                gyc=ground_y(c.x,c.z)
                if gyc is None:valid=False;break
                c.y=gyc+.0015+.004*math.sin(math.pi*t);vs.append(c)
            if not valid:skipped['cover_edge_no_ground']+=1;continue
            middle=root+direction*length*.47+side*bend*.7;gym=ground_y(middle.x,middle.z)
            if gym is None:skipped['cover_ridge_no_ground']+=1;continue
            middle.y=gym+.008;vs.append(middle);fs=[(k,(k+1)%8,8) for k in range(8)]
            # Soil can change plane inside a leaf. Raise non-root vertices only
            # when face/edge samples require it; omit instead of floating high.
            for attempt in range(3):
                samples=[sum((vs[i] for i in f),Vector())/3 for f in fs]
                samples += [(vs[a]+vs[b])*.5 for a,b in {(min(a,b),max(a,b)) for f in fs for a,b in zip(f,f[1:]+f[:1])}]
                deficits=[]
                for p in samples:
                    gyp=ground_y(p.x,p.z)
                    if gyp is None:valid=False;break
                    deficits.append(gyp-p.y)
                if not valid:break
                deficit=max(deficits)
                if deficit<=.0008:break
                for p in vs[1:]:p.y+=deficit*1.6+.0002
            clearances=[p.y-ground_y(p.x,p.z) for p in vs] if valid else []
            if not valid or max(clearances)>.018 or deficit>.0008:skipped['cover_ground_fit_rejected']+=1;continue
            if blocked(vs,fs):skipped['cover_obstacle_or_route']+=1;continue
            tint=rng.uniform(.91,1.0);colours=[]
            for k,p in enumerate(vs):
                shade=tint*(.86 if k==0 else .96 if k==8 else 1.)
                colours.append((shade,shade,shade,1))
            material=source['material'] if rng.random()<.78 else rng.choice(cover.materials)
            cover.add(vs,fs,material,colours,root,'creeping_leaf');cover.parts[-1]['cluster_index']=ci;kept+=1
            root_clearances.append(root.y-gy);cover_surface_clearances.extend(clearances)
        cluster_records[cover.name].append({'center_unity':list(center),'source_root_index':index,'kept_leaves':kept})
    # The initial slab check alone cannot reject a point already inside a tall
    # closed solid. The final conservative pass projects from above all ground
    # structures, removes whole leaves, and never fills the resulting gap.
    # Tree branches and the seat overhang retain the bounded-height check.
    full_height_names=[name for name in obstacle_names if name not in ['Garden_TreeTrunks','Garden_Bench']]
    cleanup=[]
    for builder in [grass,cover]:
        retained=[];removed=[]
        for part in builder.parts:
            start=part['vertex_start'];stop=start+part['vertex_count'];vs=builder.vertices[start:stop]
            faces=builder.faces[part['face_start']:part['face_start']+part['face_count']]
            samples=vs+[sum((builder.vertices[i] for i in f),Vector())/3 for f in faces]
            obstacle_hit=None;reason='static_full_height';wind_scalar=None
            for p in samples:
                for name in full_height_names:
                    x0,x1,z0,z1=obstacle_bounds[name]
                    if not(x0<=p.x<=x1 and z0<=-p.y<=z1):continue
                    if obstacles[name].ray_cast(Vector((p.x,p.y,6)),Vector((0,0,-1)),9)[0] is not None:
                        obstacle_hit=name;break
                if obstacle_hit:break
            if not obstacle_hit:
                for p in samples:
                    t=max(0,min(1,(p.z-.08)/.40));amplitude=.031*t*t*(3-2*t)
                    if amplitude==0:continue
                    for scalar in [-1,-.5,.5,1]:
                        q=p+Vector((amplitude*scalar,-amplitude*.42*scalar,0))
                        for name in ['Garden_HeroBoulders','LampBase_A','LampBase_B','LampBase_C']:
                            x0,x1,z0,z1=obstacle_bounds[name]
                            if not(x0<=q.x<=x1 and z0<=-q.y<=z1):continue
                            if obstacles[name].ray_cast(Vector((q.x,q.y,6)),Vector((0,0,-1)),9)[0] is not None:
                                obstacle_hit=name;reason='wind_bound_samples';wind_scalar=scalar;break
                        if obstacle_hit:break
                    if obstacle_hit:break
            if obstacle_hit:
                removed.append({'part':part,'obstacle':obstacle_hit,'reason':reason,'wind_scalar':wind_scalar})
                cluster=cluster_records[builder.name][part['cluster_index']]
                cluster['kept_blades' if builder is grass else 'kept_leaves']-=1
            else:retained.append(part)
        # FBX material order follows first polygon use. Keep original slot order
        # by stably sorting whole components, maintaining contiguous part ranges.
        retained.sort(key=lambda p:builder.mi[p['face_start']])
        nv=[];nf=[];nm=[];nc=[];np=[]
        for old_part in retained:
            a=old_part['vertex_start'];b=a+old_part['vertex_count'];fa=old_part['face_start'];fb=fa+old_part['face_count']
            new_part=dict(old_part);new_part['vertex_start']=len(nv);new_part['face_start']=len(nf)
            delta=len(nv)-a;nv.extend(builder.vertices[a:b]);nc.extend(builder.colours[a:b])
            nf.extend([tuple(i+delta for i in f) for f in builder.faces[fa:fb]]);nm.extend(builder.mi[fa:fb]);np.append(new_part)
        builder.vertices,builder.faces,builder.mi,builder.colours,builder.parts=nv,nf,nm,nc,np
        cleanup.append({'mesh':builder.name,'removed_components':len(removed),
          'removed_triangles':sum(e['part']['face_count'] for e in removed),'details':removed})
    root_clearances=[];root_edge_clearances=[];cover_surface_clearances=[];grass_height=[];drooping=0
    for builder in [grass,cover]:
        for part in builder.parts:
            root=Vector(part['root_unity']);root_clearances.append(root.y-ground_y(root.x,root.z))
            vs=[U(p) for p in builder.vertices[part['vertex_start']:part['vertex_start']+part['vertex_count']]]
            if builder is grass:
                root_edge_clearances.extend(vs[k].y-ground_y(vs[k].x,vs[k].z) for k in [0,1])
                peak=max(p.y for p in vs);grass_height.append(peak-root.y)
                if vs[-1].y<peak-.002:drooping+=1
            else:cover_surface_clearances.extend(p.y-ground_y(p.x,p.z) for p in vs)
    grass.finish();cover.finish()
    assert before=={o.name:fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    assert anchors=={o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY'}
    objects=[];total=0;colours=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH':continue
        me=ob.data;me.calc_loop_triangles();nt=len(me.loop_triangles);total+=nt
        assert all(t.area>1e-12 for t in me.loop_triangles),'Degenerate '+ob.name
        assert len({tuple(sorted(t.vertices)) for t in me.loop_triangles})==nt,'Duplicate '+ob.name
        objects.append({'name':ob.name,'vertices':len(me.vertices),'triangles':nt,'materials':[m.name for m in me.materials]})
        a=me.color_attributes.active_color;rgb=[x for c in a.data for x in c.color[:3]]
        colours.append({'mesh':ob.name,'domain':a.domain,'type':a.data_type,'min_rgb':min(rgb),'max_rgb':max(rgb)})
    assert len(objects)==29 and len(anchors)==14 and total<=510293
    texture_names=['meadow-watercolor.png','meadow-normal.png'];(OUT/'textures').mkdir(exist_ok=True)
    for name in texture_names:shutil.copy2(BASE/'textures'/name,OUT/'textures'/name)
    for image in bpy.data.images:
        name=Path(image.filepath).name
        if name in texture_names:image.filepath=str(OUT/'textures'/name)
    bpy.context.scene['meadow_revision']='world-v9 clustered roots and low leaves; only two target meshes'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','EMPTY']:ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',
      apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,
      add_leaf_bones=False,path_mode='COPY',embed_textures=True,colors_type='LINEAR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,
      export_materials='EXPORT',export_cameras=False,export_lights=False,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    files=['island.blend','island.fbx','island.glb']+['textures/'+name for name in texture_names]
    source_contact={name:percentile_report([p['ground_clearance'] for p in items if p['ground_clearance'] is not None]) for name,items in roots.items()}
    report={'revision':'world-v9','game_candidate':'v12','source':'world-v8','triangles':total,'triangle_budget':510293,
      'objects':objects,'anchors_unity':baseline['anchors_unity'],'vertex_colors':colours,'changed_meshes':sorted(TARGETS),
      'unchanged_non_target_fingerprints':before,'anchors_frozen':anchors,'materials_changed':[],'materials_added':[],
      'renderer_count_change':0,'parts':{grass.name:grass.parts,cover.name:cover.parts},
      'candidate_cluster_counts':{grass.name:len(grass_centers),cover.name:len(cover_centers)},
      'active_cluster_counts':{name:sum(p.get('kept_blades',p.get('kept_leaves',0))>0 for p in records) for name,records in cluster_records.items()},
      'live_component_counts':{grass.name:len(grass.parts),cover.name:len(cover.parts)},
      'baseline_component_counts':{name:len(items) for name,items in roots.items()},
      'grass_tips_lower_than_blade_peak_by_2mm':drooping,'grass_heights':percentile_report(grass_height),
      'root_contact_before':source_contact,'root_contact_after':percentile_report(root_clearances),
      'grass_base_edge_contact':percentile_report(root_edge_clearances),'creeping_vertex_surface_clearance':percentile_report(cover_surface_clearances),
      'skipped':dict(skipped),'obstacle_exclusion_counts':dict(exclusion),'sampling_counts':dict(sample_counts),
      'obstacle_names':obstacle_names,'full_height_obstacles':full_height_names,'full_height_cleanup':cleanup,
      'wind_bound_check':{'shader':'FoliageSurface.hlsl','max_world_xz':[.031,.01302],
        'weight':'smoothstep(0.08,0.48,worldY)','scalar_samples':[-1,-.5,0,.5,1],
        'obstacles':['Garden_HeroBoulders','LampBase_A','LampBase_B','LampBase_C'],
        'scope':'Vertex and triangle-centre bound samples; not every continuous time/triangle point.'},
      'route_core_half_width':.22,'route_segments_unity':[[list(a),list(b)] for a,b in SEGMENTS],
      'obstacle_test_scope':'Vertices and triangle centres: route core and all listed ground structures checked by full-height BVH projection. Trees and bench retain plant-height slab exclusion to avoid overhead clearing. Whole leaves omitted, no replacements. Not a continuous intersection proof or animated wind test.',
      'design_changes':['Only grass and creeping mesh rebuilt from spatial support of frozen root cloud; deterministic irregular local clusters, fewer leaves, no added materials.',
        'Narrow rooted bases, wider lower blade belly, upper curvature and some drooping tips. Local low/tall clusters with definite quiet gaps.',
        'Lower, asymmetric creeping leaves in small irregular groups; actual Meadow triangle contact replaces centre-based procedural height.'],
      'textures_byte_identical':{name:sha(OUT/'textures'/name)==sha(BASE/'textures'/name) for name in texture_names},
      'files':files,'sha256':{name:sha(OUT/name) for name in files},'baseline_sha256':baseline['sha256'],
      'verification_pending':True,'visual_review_pending':True}
    (OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'cluster-placement.json').write_text(json.dumps(cluster_records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WORLD_V9_EXPORTED',total,'components',report['live_component_counts'],'clusters',report['active_cluster_counts'],'skipped',dict(skipped),flush=True)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    if opts.verify_only:
        import runpy
        runpy.run_path(str(OUT/'verify_world_v9.py'),run_name='__main__')
    else:
        bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
        roots=extract_roots()
        if not opts.inspect_only:generate(roots)
