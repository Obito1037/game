"""Repair CoastalCliff from the actual frozen ground boundary, offline only."""
import bpy, bmesh, math, json, hashlib, struct, sys
from collections import defaultdict, Counter
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/generated/env-v1/terrain/island_terrain.blend'
OLD_SCRIPT=ROOT/'art/blender/env_v1_terrain.py'
VARIANT='B' if '--variant-b' in sys.argv else 'A'
OUT=ROOT/'art/generated/env-v2/terrain'
if VARIANT=='B':OUT=OUT/'candidate-b'
OUT.mkdir(parents=True,exist_ok=True)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mesh_signature(o):
    h=hashlib.sha256()
    for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
    vh=h.hexdigest()
    for p in o.data.polygons:
        h.update(struct.pack('<I',len(p.vertices)))
        for i in p.vertices:h.update(struct.pack('<I',i))
    return {'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),
            'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
            'vertex_sha256':vh,'vertex_topology_sha256':h.hexdigest(),
            'world_matrix':[list(row) for row in o.matrix_world]}
def boundary(o):
    counts=Counter();directions={}
    for p in o.data.polygons:
        ids=list(p.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            key=tuple(sorted((a,b)));counts[key]+=1;directions[key]=(a,b)
    edges=[directions[k] for k,n in counts.items() if n==1]
    return edges,counts
def keypoint(v):return tuple(round(float(a),5) for a in v)
def segment_keys(o,edges):
    return {tuple(sorted((keypoint(o.matrix_world@o.data.vertices[a].co),keypoint(o.matrix_world@o.data.vertices[b].co)))) for a,b in edges}
def topology(o):
    edges,counts=boundary(o)
    bm=bmesh.new();bm.from_mesh(o.data)
    stats={'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
      'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges_including_open_rims':sum(not e.is_manifold for e in bm.edges),
      'edges_with_more_than_two_faces':sum(len(e.link_faces)>2 for e in bm.edges),
      'wire_edges':sum(e.is_wire for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-10 for f in bm.faces)}
    bm.free();return stats
def worldpoints(o):return [o.matrix_world@v.co for v in o.data.vertices]
def mean_outward_normals(o):
    # Side normals compared with planar local center-to-face direction. Concave bay makes this only descriptive.
    c=Vector((-7,-1,0));vals=[]
    for p in o.data.polygons:
        xy=Vector((p.center.x-c.x,p.center.y-c.y,0))
        if xy.length:vals.append(p.normal.dot(xy.normalized()))
    return {'min_radial_dot':min(vals),'mean_radial_dot':sum(vals)/len(vals),
            'caveat':'Concave coastline cannot be certified by one radial center; topology seam evidence is independent.'}
def seam_report(ground,cliff):
    ge,gc=boundary(ground);ce,cc=boundary(cliff)
    gkeys=segment_keys(ground,ge);ckeys=segment_keys(cliff,ce)
    shared=gkeys&ckeys
    gp={keypoint(p) for p in worldpoints(ground)}
    rim=[(a,b) for a,b in ce if keypoint(cliff.matrix_world@cliff.data.vertices[a].co) in gp and keypoint(cliff.matrix_world@cliff.data.vertices[b].co) in gp]
    rkeys=segment_keys(cliff,rim)
    unmatched=sorted(gkeys-ckeys)
    return {'ground_boundary_edges':len(gkeys),'cliff_boundary_edges':len(ckeys),
       'exact_shared_top_edges':len(shared),'ground_boundary_edges_without_cliff_partner':len(unmatched),
       'ground_unmatched_segments_blender':unmatched,'cliff_top_chords_not_ground_boundary':len(rkeys-gkeys),
       'cliff_unmatched_top_chords_blender':sorted(rkeys-gkeys),
       'after_weld_combined_open_edges':len(gkeys.symmetric_difference(ckeys)),
       'comparison_tolerance_metres':1e-5}

def create_material(name,col):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*col,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=.88
    return m

VIEWS={
 'cape-tip':{'camera':(14,38,6),'look':(12.9,26.0,.8),'scale':8.5,'clay':True},
 'cape-oblique':{'camera':(25,38,10),'look':(10,24,.6),'scale':18,'clay':False},
 'village-coast':{'camera':(-37,-8,15),'look':(-19,-9,2),'scale':22,'clay':False}}
def renders(prefix):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True
    sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Cliff audit studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.14,.18,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4;sc.world=world
    bpy.ops.mesh.primitive_plane_add(size=400,location=(0,0,-.16));sea=bpy.context.object;sea.name='RENDER_ONLY_SEA'
    sea.data.materials.append(create_material('AuditSea',(.055,.09,.12)))
    lights=[]
    for position,power,size in [((15,25,32),6000,15),((-22,5,23),3200,20)]:
        bpy.ops.object.light_add(type='AREA',location=position);o=bpy.context.object;o.data.energy=power;o.data.size=size
        o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
    clay=create_material('NeutralDiagnosticClay',(.45,.45,.45))
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';sc.camera=cam
    for name,v in VIEWS.items():
        cam.location=v['camera'];cam.rotation_euler=(Vector(v['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale']
        sc.view_layers[0].material_override=clay if v['clay'] else None
        sc.render.filepath=str(OUT/f'{prefix}-{name}.png');bpy.ops.render.render(write_still=True)
    sc.view_layers[0].material_override=None
    for o in lights+[cam,sea]:bpy.data.objects.remove(o,do_unlink=True)

source_hash=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
ground=bpy.data.objects['IslandGround'];paths=bpy.data.objects['StonePaths'];cliff=bpy.data.objects['CoastalCliff']
frozen={'IslandGround':mesh_signature(ground),'StonePaths':mesh_signature(paths)}
ground_before_coords=[tuple(v.co) for v in ground.data.vertices]
ground_before_polygons=[tuple(p.vertices) for p in ground.data.polygons]
before={'topology':topology(cliff),'seams':seam_report(ground,cliff),'normals':mean_outward_normals(cliff)}
renders('before')

changed_ground=[];protection=None
if VARIANT=='B':
    inp=ROOT/'GameProject/Assets/JieGuang/Environment/scene-input.json'
    contract=json.loads(inp.read_text(encoding='utf-8-sig'))
    border=[Vector((q['position'][0],-q['position'][2])) for q in contract['boundary']]
    anchors=[(a['name'],Vector((a['position'][0],-a['position'][2]))) for a in contract['anchors']]
    def segdist(p,a,b):
        ab=b-a;t=max(0,min(1,(p-a).dot(ab)/max(ab.length_squared,1e-12)))
        return (p-(a+ab*t)).length
    def inside(p,poly):
        flag=False
        for a,b in zip(poly,poly[1:]+poly[:1]):
            if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:flag=not flag
        return flag
    def signed_distance(p):
        d=min(segdist(p,a,b) for a,b in zip(border,border[1:]+border[:1]))
        return d if inside(p,border) else -d
    path_polys=[[Vector((paths.data.vertices[i].co.x,paths.data.vertices[i].co.y)) for i in poly.vertices] for poly in paths.data.polygons]
    def path_distance(p):
        if any(inside(p,poly) for poly in path_polys):return 0.0
        return min(segdist(p,a,b) for poly in path_polys for a,b in zip(poly,poly[1:]+poly[:1]))
    houses=[]
    for inst in contract['instances']:
        if inst['asset']=='abode_grandma' or inst['asset'].startswith('cottage_'):
            meta=json.loads((ROOT/'art/generated/env-v1/props'/inst['asset']/'asset.json').read_text(encoding='utf-8-sig'))
            dims=meta['dimensions_metres'];radius=math.hypot(dims[0],dims[1])*.5*inst['scale']+.3
            houses.append((inst['name'],Vector((inst['position'][0],-inst['position'][2])),radius))
    tips=[Vector((13,27)),Vector((14,-24))]
    def smooth01(x):x=max(0,min(1,x));return x*x*(3-2*x)
    for v in ground.data.vertices:
        p=Vector((v.co.x,v.co.y));sd=signed_distance(p)
        tipdist=min((p-c).length for c in tips)
        if sd>=-.10 or tipdist>=2.8:continue
        aname,adist=min(((name,(p-q).length) for name,q in anchors),key=lambda a:a[1])
        pd=path_distance(p)
        hname,hd=min(((name,(p-q).length-radius) for name,q,radius in houses),key=lambda a:a[1])
        if adist<1.0 or pd<1.0 or hd<0:continue
        weight=smooth01((-sd-.1)/.60)*smooth01(1-tipdist/2.8)
        old=v.co.copy();target=.32
        nz=old.z+(target-old.z)*weight
        if abs(nz-old.z)<1e-6:continue
        v.co.z=nz
        changed_ground.append({'vertex_index':v.index,'before_blender_xyz':list(old),'after_blender_xyz':list(v.co),
            'delta_height_metres':v.co.z-old.z,'signed_distance_to_walkable_boundary_metres':sd,
            'nearest_anchor':aname,'nearest_anchor_planar_distance_metres':adist,
            'distance_to_path_surface_planar_metres':pd,'nearest_house':hname,'clearance_from_house_bounding_circle_metres':hd})
    ground.data.update()
    protection={'scene_contract_sha256':sha(inp),'boundary_rule':'negative signed distance means outside; require <-0.10m',
       'anchor_protection_metres':1.0,'road_surface_protection_metres':1.0,
       'building_protection':'World bounding circle of source house XY extents, plus 0.30m',
       'changed_vertices':len(changed_ground),'core_vertices_unchanged':len(ground.data.vertices)-len(changed_ground)}

# The only source of the new top rim is the actual ground's ordered boundary edges.
edges,counts=boundary(ground);adj=defaultdict(list)
for a,b in edges:adj[a].append(b);adj[b].append(a)
if not all(len(v)==2 for v in adj.values()):raise RuntimeError('Ground border not one simple degree-2 cycle')
start=min(adj);loop=[start];prev=None;cur=start
while True:
    choices=[n for n in adj[cur] if n!=prev];nxt=choices[0]
    if nxt==start:break
    if nxt in loop:raise RuntimeError('Ground boundary self-revisited')
    loop.append(nxt);prev,cur=cur,nxt
if len(loop)!=len(edges):raise RuntimeError('Multiple ground boundary loops; refusing to guess')
top=[ground.matrix_world@ground.data.vertices[i].co for i in loop]
area=sum(a.x*b.y-b.x*a.y for a,b in zip(top,top[1:]+top[:1]))*.5
if area<0:loop.reverse();top.reverse()
L=len(top);arc=[0.0]
for i in range(1,L):arc.append(arc[-1]+(top[i]-top[i-1]).length)
perimeter=arc[-1]+(top[0]-top[-1]).length
normals=[]
for i in range(L):
    a,b=top[(i-1)%L],top[(i+1)%L];tan=Vector((b.x-a.x,b.y-a.y,0)).normalized()
    normals.append(Vector((tan.y,-tan.x,0)))

# The original 16 cm tip contains a tall profile. Spread only lower rings into a
# small tapered buttress instead of propagating that tiny cross-section as a razor-thin fin.
cap_fields={}
for chord in before['seams']['cliff_unmatched_top_chords_blender']:
    a,b=map(Vector,chord);center=(a+b)*.5;cross=Vector((b.x-a.x,b.y-a.y,0));width=cross.length
    if width<1e-7:continue
    cross.normalize();members=[]
    for i,p in enumerate(top):
        rel=Vector((p.x-center.x,p.y-center.y,0));r=rel.dot(cross)/(width*.5)
        lateral=(rel-cross*rel.dot(cross)).length
        if abs(r)<=1.0001 and lateral<.0001:members.append((i,max(-1,min(1,r))))
    outward=sum((normals[i] for i,r in members),Vector()).normalized()
    for i,r in members:cap_fields[i]=(cross,outward,r)

# Irregular shallow strata, not a uniform extruded skirt. No random noise changes the shared top edge.
bands=[0,.06,.16,.28,.41,.54,.68,.83,1.0]
offsets=[0,.022,.11,.065,.19,.10,.24,.18,.30]
verts=[];max_displacement=0
for j,t in enumerate(bands):
    for i,p in enumerate(top):
        s=arc[i];phase=2*math.pi*s/perimeter
        coherent=.6*math.sin(phase*9+.6*j)+.28*math.sin(phase*21-1.3*j)+.12*math.cos(phase*37+.9*j)
        amount=offsets[j]*(1+.35*coherent)
        if j==0:verts.append(tuple(p));continue
        toe=-1.8+.07*math.sin(phase*11)
        z=(1-t)*p.z+t*toe+.055*math.sin(math.pi*t)*math.sin(phase*13+j*.8)
        q=p+normals[i]*amount
        if i in cap_fields and VARIANT=='A':
            cross,outward,r=cap_fields[i]
            spread=.46*math.sin(t*math.pi*.5)
            q+=cross*(r*spread)+outward*(math.sqrt(max(0,1-r*r))*spread*.5)
        q.z=z;verts.append(tuple(q));max_displacement=max(max_displacement,math.hypot(q.x-p.x,q.y-p.y))
faces=[];mats=[]
for j in range(len(bands)-1):
    for i in range(L):
        a=j*L+i;b=j*L+(i+1)%L
        # CCW ground edge -> outward facing side normal, no opaque patch across the missing area.
        faces.append((a,a+L,b+L,b))
        phase=2*math.pi*arc[i]/perimeter
        mats.append(4 if math.sin(phase*7+j*1.4)+.35*math.sin(phase*19-j)>.9 else 3)
data=bpy.data.meshes.new('CoastalCliff_v2');data.from_pydata(verts,[],faces);data.update()
for m in cliff.data.materials:data.materials.append(m)
olddata=cliff.data;cliff.data=data
for p,mi in zip(data.polygons,mats):p.material_index=mi;p.use_smooth=True
bpy.context.view_layer.objects.active=cliff;bpy.ops.object.select_all(action='DESELECT');cliff.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.015)
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()

after={'topology':topology(cliff),'seams':seam_report(ground,cliff),'normals':mean_outward_normals(cliff)}
checks=[]
def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
for name,signature in frozen.items():
    if name=='IslandGround' and VARIANT=='B':
        changed_ids={q['vertex_index'] for q in changed_ground}
        check('only_declared_ground_vertices_changed',all(
            (tuple(v.co)!=ground_before_coords[v.index])==(v.index in changed_ids) for v in ground.data.vertices))
        check('ground_topology_exact',ground_before_polygons==[tuple(p.vertices) for p in ground.data.polygons])
        check('changes_outside_boundary',all(q['signed_distance_to_walkable_boundary_metres']<-.10 for q in changed_ground))
        check('anchor_1m_protected',all(q['nearest_anchor_planar_distance_metres']>=1 for q in changed_ground))
        check('paths_1m_protected',all(q['distance_to_path_surface_planar_metres']>=1 for q in changed_ground))
        check('building_foundations_protected',all(q['clearance_from_house_bounding_circle_metres']>=0 for q in changed_ground))
    else:check(name+'_exact_frozen',mesh_signature(bpy.data.objects[name])==signature,mesh_signature(bpy.data.objects[name]))
check('source_blend_unchanged',sha(SOURCE)==source_hash)
check('all_ground_boundary_edges_have_exact_partner',after['seams']['ground_boundary_edges_without_cliff_partner']==0,after['seams']['exact_shared_top_edges'])
check('no_spanning_top_chords',after['seams']['cliff_top_chords_not_ground_boundary']==0)
check('only_submerged_combined_open_rim',after['seams']['after_weld_combined_open_edges']==L,
      {'combined_open_edges':after['seams']['after_weld_combined_open_edges'],'expected_bottom_edges':L})
check('no_nonmanifold_branch_or_wire',after['topology']['edges_with_more_than_two_faces']==0 and after['topology']['wire_edges']==0)
check('no_zero_area_faces',after['topology']['zero_area_faces']==0)
check('added_triangles_at_most_8000',after['topology']['triangles']-before['topology']['triangles']<=8000)
check('top_vertices_exact',all(tuple(data.vertices[i].co)==tuple(p) for i,p in enumerate(top)))
check('bottom_rim_below_water',all(data.vertices[(len(bands)-1)*L+i].co.z<-.16 for i in range(L)))

# Full comparison blend retains frozen ground and paths; FBX intentionally contains only the visual cliff.
blend=OUT/'coastal_cliff_v2_candidate.blend';fbx=OUT/'coastal_cliff_v2_candidate.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.object.select_all(action='DESELECT');cliff.select_set(True)
if VARIANT=='B':ground.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',
    apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='RELATIVE')
renders('after')

# Quantify the source's two incorrectly spanning chords against the true omitted middle vertices.
chords=before['seams']['cliff_unmatched_top_chords_blender'];witnesses=[]
for chord in chords:
    a,b=map(Vector,chord);ab=b-a;d=Vector((ab.x,ab.y,0));den=d.length_squared
    candidates=[]
    for p in top:
        t=Vector((p.x-a.x,p.y-a.y,0)).dot(d)/den if den else 0
        nearest=a+ab*t
        planar=math.hypot(p.x-nearest.x,p.y-nearest.y)
        if .0001<t<.9999 and planar<.0001:candidates.append({'point':list(p),'height_above_chord':p.z-nearest.z})
    if candidates:witnesses.append({'chord':chord,'omitted_points':len(candidates),'maximum_height_gap':max(q['height_above_chord'] for q in candidates),'samples':candidates})

report={'status':'offline-cliff-candidate-not-imported','variant':VARIANT,'source_blend':str(SOURCE.relative_to(ROOT)).replace('\\','/'),
 'source_blend_sha256':source_hash,'source_script_sha256':sha(OLD_SCRIPT),'candidate_script_sha256':sha(Path(__file__)),
 'diagnosis':'Original edge_ids used only both longitudinal sides, skipping 23 interior vertices at each end. Two end chords cannot seal the raised terrain end profiles. Exact topology mismatch persists independently of material and normals.',
 'before':before,'after':after,'source_end_gap_witnesses':witnesses,'frozen_meshes':frozen,'checks':checks,
 'coastline_vertex_changes':changed_ground,'protection_rules':protection,
 'shared_rim_vertex_count':L,'cliff_ring_count':len(bands),'new_triangles':after['topology']['triangles'],
 'added_triangles':after['topology']['triangles']-before['topology']['triangles'],
 'max_planar_outward_displacement_metres':max_displacement,
 'bottom_rim_description':'Open solely below sea level at approximately -1.8m Blender Z / Unity Y; hidden lower skirt from source -3.4m removed. Not a closed printable solid.',
 'render_views':VIEWS,'render_resolution':[1200,900],'render_scope':'Offline exact-camera before/after; cape-tip uses a uniform gray material override as a geometry diagnostic.',
 'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [blend,fbx]+sorted(OUT.glob('*.png'))],
 'limits':[('Only CoastalCliff visual mesh exported; ground is frozen.' if VARIANT=='A' else 'FBX exports CoastalCliff and modified IslandGround; changed nonwalkable coast vertices are explicitly listed. Unity ground collision must be independently rechecked.'),
   'No path, markers, layout, collision or Unity project files altered.',
   'Old ground collision remains exact; visual cliff bulges by up to the reported outward amount. A wall collision following the former cliff could disagree by that amount; do not silently claim collision parity.',
   'Smooth shading and uneven strata improve broad silhouette but do not replace rock PBR detail. Night lighting, Unity import normals, actual gameplay raycasts and FPS remain unverified.',
   'This repairs a demonstrable endpoint gap; it does not prove every black pixel in the historical Unity image had the same cause.']}
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ENV_V2_CLIFF_DONE',report['new_triangles'],'ADDED',report['added_triangles'],'FAILED',sum(not c['passed'] for c in checks),flush=True)
