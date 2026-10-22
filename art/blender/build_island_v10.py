"""World-v8 derivative: preserve meadow coverage, refine root and upper leaf shape."""
import bpy, math, json, hashlib, argparse, sys, random, shutil
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/world-v8';OUT=ROOT/'art/generated/world-v10'
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
    full_names=['Garden_HeroBoulders','Garden_Walkways','Observatory_StoneAndBrass','Cliff_Pier',
      'LampBase_A','LampBase_B','LampBase_C','Cabin_PlasterAndFoundation','Cabin_Timber']
    partial_names=['Garden_TreeTrunks','Garden_Bench']
    obstacles={name:make_bvh(name) for name in full_names+partial_names};bounds={}
    for name in obstacles:
        ob=bpy.data.objects[name];v=[ob.matrix_world@p.co for p in ob.data.vertices]
        bounds[name]=(min(p.x for p in v),max(p.x for p in v),min(p.y for p in v),max(p.y for p in v))
    def ground_y(x,z):
        hit=ground.ray_cast(Vector((x,-z,2)),Vector((0,0,-1)),4)[0]
        return None if hit is None else hit.z
    def projected_hit(p,names,start=6.,end=-3.):
        q=B(p)
        for name in names:
            x0,x1,y0,y1=bounds[name]
            if x0<=q.x<=x1 and y0<=q.y<=y1 and obstacles[name].ray_cast(Vector((q.x,q.y,start)),Vector((0,0,-1)),start-end)[0] is not None:return name
        return None
    def exclusion(vs,fs):
        samples=vs+[sum((vs[i] for i in f),Vector())/3 for f in fs]
        ymax=max(p.y for p in vs)+.003;ymin=min(p.y for p in vs)-.30
        for p in samples:
            if route_distance(p)<.22:return 'route_core'
            hit=projected_hit(p,full_names)
            if hit:return hit
            # The deeper lower end catches closed trunk/leg bases while the
            # upper end stays below overhead branches and the bench seat.
            hit=projected_hit(p,partial_names,ymax,ymin)
            if hit:return hit
        for p in samples:
            t=max(0,min(1,(p.y-.08)/.40));a=.031*t*t*(3-2*t)
            if a==0:continue
            for scalar in [-1,-.5,.5,1]:
                q=p+Vector((a*scalar,0,a*.42*scalar))
                hit=projected_hit(q,['Garden_HeroBoulders','LampBase_A','LampBase_B','LampBase_C'])
                if hit:return 'wind_bound:'+hit
        return None
    grass=PlantMesh('Garden_GrassTufts');cover=PlantMesh('Garden_CreepingMeadowLeaves')
    rng=random.Random(12102026);grass_data=bpy.data.objects[grass.name].data
    # Select nearby grouping cues from the existing cloud, without deleting low
    # density regions or replacing the original short/tall population.
    candidate_order=list(range(len(roots[grass.name])));rng.shuffle(candidate_order)
    cells=defaultdict(list);centres=[];cell=.10
    for index in candidate_order:
        p=Vector(roots[grass.name][index]['root_unity']);gx,gz=math.floor(p.x/cell),math.floor(p.z/cell)
        neighbors=[q for x in range(gx-1,gx+2) for z in range(gz-1,gz+2) for q in cells[(x,z)]]
        if any((q.x-p.x)**2+(q.z-p.z)**2<.085**2 for q in neighbors):continue
        p.y=0.;centres.append(p);cells[(gx,gz)].append(p)
    tree=KDTree(len(centres))
    for i,p in enumerate(centres):tree.insert(p,i)
    tree.balance();group_specs=[(rng.uniform(-.30,.30),rng.uniform(.965,1.025)) for _ in centres]
    skipped=Counter();moves=[];cleanup=[];source_classes=Counter();retained_classes=Counter();root_clearances=[];base_clearances=[];cover_clearances=[]
    max_nonroot_soil_correction=0.;drooping=0
    for builder in [grass,cover]:
        ob=bpy.data.objects[builder.name];mesh=ob.data;mesh.calc_loop_triangles();groups=components(ob)
        vertex_group={vi:i for i,g in enumerate(groups) for vi in g['vertices']}
        triangles=[[] for _ in groups]
        for t in mesh.loop_triangles:triangles[vertex_group[t.vertices[0]]].append(tuple(t.vertices))
        vertex_degree=Counter()
        for edge in mesh.edges:
            for vertex_index in edge.vertices:vertex_degree[vertex_index]+=1
        vertex_colours={}
        attr=mesh.color_attributes.active_color
        for loop in mesh.loops:vertex_colours[loop.vertex_index]=tuple(attr.data[loop.index].color)
        for index,group in enumerate(groups):
            ids=sorted(group['vertices']);old={i:U(ob.matrix_world@mesh.vertices[i].co) for i in ids}
            original_root=Vector(roots[builder.name][index]['root_unity']);material=roots[builder.name][index]['material']
            kind='short_grass' if builder is grass and len(ids)==7 else 'long_grass' if builder is grass and len(ids)==9 else 'broad_grass' if builder is grass else 'creeping_leaf'
            source_classes[kind]+=1
            root=original_root.copy();rotation=0.;height_scale=1.;group_index=None
            if builder is grass:
                query=Vector((root.x,0,root.z));nearest,group_index,distance=tree.find(query)
                delta=(nearest-query)*.30
                if delta.length>.02:delta=delta.normalized()*.02
                root.x+=delta.x;root.z+=delta.z;moves.append(delta.length)
                rotation,height_scale=group_specs[group_index]
                rotation+=rng.uniform(-.065,.065)
            gy=ground_y(root.x,root.z)
            if gy is None:skipped[kind+':no_ground']+=1;continue
            root.y=gy-(.0008 if builder is grass else .0006)
            positions={};root_ids=[];shape_data={};cs,sn=math.cos(rotation),math.sin(rotation)
            def rotate(p):return Vector((p.x*cs-p.z*sn,p.y,p.x*sn+p.z*cs))
            if kind in ['short_grass','long_grass']:
                by_height=sorted(ids,key=lambda i:old[i].y);root_ids=by_height[:2]
                pair_count=(len(ids)-1)//2;times=[0,.38,.73] if kind=='short_grass' else [0,.25,.5,.75]
                tip_id=by_height[-1];oldtip=old[tip_id]-original_root
                bend=rotate(Vector((oldtip.x,0,oldtip.z)))
                if bend.length<1e-7:bend=Vector((1,0,0))
                else:bend.normalize()
                h=max(p.y for p in old.values())-original_root.y
                droop=kind=='long_grass' and rng.random()<.31
                for pair,t in enumerate(times):
                    a,b=by_height[pair*2:pair*2+2];mid=(old[a]+old[b])*.5-original_root
                    c=root+rotate(mid);c.y=root.y+mid.y*height_scale
                    c+=bend*(h*.065*math.sin(math.pi*t))
                    if droop:c.y+=h*.075*math.sin(math.pi*t)
                    side=rotate((old[b]-old[a])*.5)
                    side*=.35 if pair==0 else .98 if pair==1 else 1.
                    positions[a]=c-side;positions[b]=c+side
                tip=root+rotate(oldtip);tip.y=root.y+oldtip.y*height_scale
                if droop:tip.y-=h*.22
                positions[tip_id]=tip
                shape_data={'tip_source_id':tip_id,'droop_variant':droop}
            elif kind=='broad_grass':
                # The frozen 84 broad blades have a folded midrib; rotate the
                # width around the axis, preserving 13 vertices and 16 triangles.
                root_ids=[min(ids,key=lambda i:old[i].y)]
                ordered=sorted(ids);dir_vec=old[ordered[-2]]-original_root;dir_vec.y=0
                if dir_vec.length<1e-6:dir_vec=Vector((1,0,0))
                else:dir_vec.normalize()
                direction=rotate(dir_vec);side=Vector((-direction.z,0,direction.x))
                row_ids=[ordered[0:2],ordered[2:5],ordered[5:8],ordered[8:11],ordered[11:13]]
                for row,chunk in enumerate(row_ids):
                    t=row/4;center_id=chunk[1] if len(chunk)==2 else chunk[1]
                    center_old=old[center_id]-Vector((0,.006,0))-original_root
                    center=root+rotate(center_old);center.y=root.y+center_old.y*height_scale
                    width=.018*math.sin(math.pi*t)*.90
                    if len(chunk)==2:
                        positions[chunk[0]]=center-Vector((0,.003,0));positions[chunk[1]]=center+Vector((0,.006,0))
                    else:
                        positions[chunk[0]]=center-side*width-Vector((0,.003,0))
                        positions[chunk[1]]=center+Vector((0,.006,0))
                        positions[chunk[2]]=center+side*width-Vector((0,.003,0))
                # Re-anchor the actual lowest shared base vertex, not a virtual
                # centre three millimetres above that vertex.
                offset=root.y-positions[root_ids[0]].y
                for p in positions.values():p.y+=offset
            else:
                root_ids=[min(ids,key=lambda i:old[i].y)]
                tip_id=max(ids,key=lambda i:(old[i].x-original_root.x)**2+(old[i].z-original_root.z)**2)
                direction=old[tip_id]-original_root;direction.y=0;length=direction.length;direction.normalize()
                side=Vector((-direction.z,0,direction.x));narrow=rng.uniform(.84,1.01);length_scale=rng.uniform(.96,1.03)
                # Keep old individual root locations; avoid assembling every
                # leaf into the same three-arm ground icon.
                ridge=max(ids,key=lambda i:vertex_degree[i]);bend=rng.uniform(-.045,.045)*length
                for i in ids:
                    d=old[i]-original_root;t=max(0,min(1,d.dot(direction)/max(length,1e-8)))
                    transverse=d.dot(side)*narrow*(.95 if d.dot(side)>0 else 1.03)
                    p=root+direction*d.dot(direction)*length_scale+side*(transverse+bend*math.sin(math.pi*t))
                    gyp=ground_y(p.x,p.z)
                    if gyp is None:positions={};break
                    p.y=gyp+(.009 if i==ridge else .002+.004*math.sin(math.pi*t))
                    if i in root_ids:p.y=root.y
                    positions[i]=p
            if not positions:skipped[kind+':edge_no_ground']+=1;continue
            ordered=root_ids+[i for i in ids if i not in root_ids]
            mapping={old_id:i for i,old_id in enumerate(ordered)}
            vs=[positions[i] for i in ordered];fs=[tuple(mapping[i] for i in f) for f in triangles[index]]
            valid=True
            for vi,p in enumerate(vs):
                gyp=ground_y(p.x,p.z)
                if gyp is None:valid=False;break
                if vi<len(root_ids):p.y=gyp-(.0008 if builder is grass else .0006)
                elif p.y<gyp+.0006:
                    max_nonroot_soil_correction=max(max_nonroot_soil_correction,gyp+.0006-p.y);p.y=gyp+.0006
            if not valid:skipped[kind+':edge_no_ground']+=1;continue
            if kind=='creeping_leaf':
                for attempt in range(3):
                    samples=[sum((vs[i] for i in f),Vector())/3 for f in fs]
                    samples += [(vs[a]+vs[b])*.5 for a,b in {(min(a,b),max(a,b)) for f in fs for a,b in zip(f,f[1:]+f[:1])}]
                    deficit=0.
                    for p in samples:
                        gyp=ground_y(p.x,p.z)
                        if gyp is None:valid=False;break
                        deficit=max(deficit,gyp-p.y)
                    if not valid or deficit<=.0008:break
                    for p in vs[len(root_ids):]:p.y+=deficit*1.6+.0002
                if not valid or deficit>.0008 or max(p.y-ground_y(p.x,p.z) for p in vs)>.018:
                    skipped[kind+':ground_fit']+=1;continue
            reason=exclusion(vs,fs)
            if reason:
                skipped[kind+':'+reason]+=1;cleanup.append({'mesh':builder.name,'source_component':index,'reason':reason,'triangles':len(fs)});continue
            colours=[vertex_colours[i] for i in ordered]
            builder.add(vs,fs,material,colours,root,kind)
            part=builder.parts[-1];part['root_vertex_offsets']=list(range(len(root_ids)))
            part['source_component_index']=index;part['original_root_unity']=list(original_root);part['group_index']=group_index
            retained_classes[kind]+=1;root_clearances.append(root.y-gy)
            base_clearances.extend(vs[i].y-ground_y(vs[i].x,vs[i].z) for i in range(len(root_ids)))
            if kind=='creeping_leaf':cover_clearances.extend(p.y-ground_y(p.x,p.z) for p in vs)
            elif 'tip_source_id' in shape_data:
                if positions[shape_data['tip_source_id']].y<max(p.y for p in vs)-.002:drooping+=1
        # First polygon use determines FBX slot order. Sort complete leaves only.
        old_parts=sorted(builder.parts,key=lambda p:builder.mi[p['face_start']]);nv=[];nf=[];nc=[];nm=[];np=[]
        for old_part in old_parts:
            a=old_part['vertex_start'];b=a+old_part['vertex_count'];fa=old_part['face_start'];fb=fa+old_part['face_count']
            part=dict(old_part);part['vertex_start']=len(nv);part['face_start']=len(nf);delta=len(nv)-a
            nv.extend(builder.vertices[a:b]);nc.extend(builder.colours[a:b]);nf.extend(tuple(i+delta for i in f) for f in builder.faces[fa:fb]);nm.extend(builder.mi[fa:fb]);np.append(part)
        builder.vertices,builder.faces,builder.mi,builder.colours,builder.parts=nv,nf,nm,nc,np
        builder.finish()
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
    assert total<=510293 and len(objects)==29 and len(anchors)==14
    texture_names=['meadow-watercolor.png','meadow-normal.png'];(OUT/'textures').mkdir(exist_ok=True)
    for name in texture_names:shutil.copy2(BASE/'textures'/name,OUT/'textures'/name)
    for image in bpy.data.images:
        name=Path(image.filepath).name
        if name in texture_names:image.filepath=str(OUT/'textures'/name)
    bpy.context.scene['meadow_revision']='world-v10 preserve original coverage; roots and local upper curves'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
    for ob in bpy.context.scene.objects:ob.select_set(ob.type in ['MESH','EMPTY'])
    bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',
      apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,
      path_mode='COPY',embed_textures=True,colors_type='LINEAR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,
      export_materials='EXPORT',export_cameras=False,export_lights=False,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    files=['island.blend','island.fbx','island.glb']+['textures/'+n for n in texture_names]
    report={'revision':'world-v10','game_candidate':'v12','source':'world-v8','triangles':total,'triangle_budget':510293,
      'objects':objects,'anchors_unity':baseline['anchors_unity'],'anchors_frozen':anchors,'changed_meshes':sorted(TARGETS),
      'unchanged_non_target_fingerprints':before,'vertex_colors':colours,'materials_added':[],'materials_changed':[],
      'renderer_count_change':0,'parts':{grass.name:grass.parts,cover.name:cover.parts},
      'live_component_counts':{grass.name:len(grass.parts),cover.name:len(cover.parts)},
      'source_classes':dict(source_classes),'retained_classes':dict(retained_classes),'skipped':dict(skipped),'cleanup':cleanup,
      'root_horizontal_move_metres':percentile_report(moves),'root_contact_after':percentile_report(root_clearances),
      'actual_base_contact_after':percentile_report(base_clearances),'creeping_vertex_surface_clearance':percentile_report(cover_clearances),
      'max_nonroot_soil_correction':max_nonroot_soil_correction,'grass_tips_below_peak_by_2mm':drooping,
      'full_height_obstacles':full_names,'plant_height_obstacles':partial_names,'plant_height_lower_margin_metres':.30,
      'route_core_half_width':.22,'route_segments_unity':[[list(a),list(b)] for a,b in SEGMENTS],
      'wind_bound_check':{'shader':'FoliageSurface.hlsl','max_world_xz':[.031,.01302],'scalar_samples':[-1,-.5,0,.5,1],
        'obstacles':['Garden_HeroBoulders','LampBase_A','LampBase_B','LampBase_C'],'scope':'Vertices and triangle centroids; no continuous-time proof.'},
      'design_changes':['Load world-v8; retain original short/tall population and creeping-root distribution, with only spatial collision omissions.',
        'Grass bases narrow to 35%, middle widths retain 98-100%; root grouping moves are capped at 2cm and no macro patch thinning occurs.',
        'Mild upper bow and limited long-blade droop; preserve short 5tri/long 7tri topology and original vertex colours.',
        'Creeping leaves keep their individual source root positions and vary subtly in width/asymmetry while fitting actual soil.'],
      'files':files,'sha256':{name:sha(OUT/name) for name in files},'baseline_sha256':baseline['sha256'],
      'textures_byte_identical':{n:sha(OUT/'textures'/n)==sha(BASE/'textures'/n) for n in texture_names},
      'verification_pending':True,'visual_review_pending':True}
    (OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WORLD_V10_EXPORTED',total,'classes',dict(retained_classes),'skipped',dict(skipped),flush=True)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    if opts.verify_only:
        import runpy
        runpy.run_path(str(OUT/'verify_world_v10.py'),run_name='__main__')
    else:
        bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
        roots=extract_roots()
        if not opts.inspect_only:generate(roots)

