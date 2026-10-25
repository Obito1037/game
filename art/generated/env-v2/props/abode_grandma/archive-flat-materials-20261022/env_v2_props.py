"""Non-destructive v2 grandma-house candidate; no Unity project writes.

Blender 4.5 --background --factory-startup --python art/blender/env_v2_props.py
"""
import bpy, bmesh, json, hashlib, math, random
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/env-v1/props/abode_grandma/abode_grandma.blend'
META=ROOT/'art/generated/env-v1/props/abode_grandma/asset.json'
OUT=ROOT/'art/generated/env-v2/props/abode_grandma'
OUT.mkdir(parents=True,exist_ok=True)
RNG=random.Random(6304)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(name,color,rough=.72,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    return m
def mesh(name,verts,faces,m):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(m);return o
def box(name,loc,dim,m,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
    if bevel:
        mod=o.modifiers.new('Hand softened edges','BEVEL');mod.width=bevel;mod.segments=1
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def cylinder(name,loc,rad,depth,m,n=8,rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=rad,depth=depth,location=loc)
    o=bpy.context.object;o.name=name;o.data.materials.append(m)
    if rot:o.rotation_euler=rot
    return o
def beam(name,a,b,width,m,rect=False):
    a,b=Vector(a),Vector(b)
    o=box(name,(a+b)*.5,(width,width,(b-a).length),m,.008) if rect else cylinder(name,(a+b)*.5,width/2,(b-a).length,m)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def bounds():
    pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
    return {'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
def markers():
    return {o.name:{'location':list(o.matrix_world.translation),'quaternion':list(o.matrix_world.to_quaternion())}
            for o in bpy.context.scene.objects if o.type=='EMPTY' and o.name.startswith('Marker_')}
def triangles():
    n=0
    for o in bpy.context.scene.objects:
        if o.type=='MESH':o.data.calc_loop_triangles();n+=len(o.data.loop_triangles)
    return n
def apply_normals_uv():
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':continue
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
        bpy.ops.object.mode_set(mode='OBJECT')

VIEWS={
 'front':{'camera':(7,-10,6),'look':(0,-.1,1.85),'scale':7.5},
 'side':{'camera':(-8,-7,5.0),'look':(0,0,1.8),'scale':7.4},
 'window':{'camera':(3.2,-7.3,3.0),'look':(.45,-1.1,1.9),'scale':5.25},
}
def render_set(prefix):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.render.film_transparent=False
    sc.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Neutral studio audit');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.25,.28,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;sc.world=world
    lights=[]
    for pos,power,size in [((2,-5,8),1350,5),((-5,-2,4),650,4),((1,4,5),800,4)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size
        o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler();lights.append(o)
    bpy.ops.object.camera_add();cam=bpy.context.object;sc.camera=cam;cam.data.type='ORTHO'
    for name,view in VIEWS.items():
        cam.location=view['camera'];cam.rotation_euler=(Vector(view['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']
        sc.render.filepath=str(OUT/f'{prefix}-{name}.png');bpy.ops.render.render(write_still=True)
    for o in lights+[cam]:bpy.data.objects.remove(o,do_unlink=True)

original_sha=sha(BASE);bpy.ops.wm.open_mainfile(filepath=str(BASE))
baseline_bounds=bounds();baseline_markers=markers();baseline_triangles=triangles()
render_set('before')

# The baseline carries all contractual openings, door, desk and seat geometry.
structure=bpy.data.objects['Structure']
roof_mats={i for i,m in enumerate(structure.data.materials) if m and m.name.startswith('Roof_')}
bm=bmesh.new();bm.from_mesh(structure.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in roof_mats],context='FACES')
bm.to_mesh(structure.data);bm.free();structure.data.update()

IVORY=[mat('V2_WhitewashedWood_'+str(i),c) for i,c in enumerate([(.60,.55,.43),(.68,.62,.50),(.73,.67,.55),(.64,.59,.48)])]
TIMBER=[mat('V2_OldTimber_'+str(i),c) for i,c in enumerate([(.24,.14,.075),(.29,.18,.10),(.36,.24,.14)])]
TILES=[mat('V2_TealClay_'+str(i),c,.65) for i,c in enumerate([(.10,.24,.25),(.14,.30,.29),(.17,.33,.31),(.12,.27,.29),(.22,.36,.32)])]
STONES=[mat('V2_FoundationStone_'+str(i),c,.9) for i,c in enumerate([(.38,.37,.31),(.47,.45,.36),(.42,.42,.36)])]
IRON=mat('V2_BlackenedIron',(.10,.12,.12),.43,.66)
COPPER=mat('V2_OldBrass',(.43,.28,.12),.48,.6)
GLASS=mat('V2_AtticUnlitAmberGlass',(.26,.17,.065),.29)

# Individual overlapping timber boards; clipping ranges deliberately leave the original door and round aperture open.
def plank(x0,x1,y,z,depth=.045,height=.174,side=False):
    if x1-x0<.07:return
    if side:
        o=box('WallBoard', (y,(x0+x1)/2,z), (depth,x1-x0-.007,height),RNG.choice(IVORY))
    else:o=box('WallBoard',((x0+x1)/2,y,z),(x1-x0-.007,depth,height),RNG.choice(IVORY),.008 if y<0 else 0)
    # Small shallow nail caps are real geometry, sparse and deliberately kept outside the beam opening.
    if x1-x0>.45 and row%4==0:
        for q in [x0+.10,x1-.10]:
            pos=(y+(.028 if y>0 else -.028),q,z) if side else (q,y-.028,z)
            rot=(0,math.pi/2,0) if side else (math.pi/2,0,0)
            cylinder('SidingNail',pos,.011,.006,IRON,5,rot)
for row in range(13):
    z=.29+row*.180
    plank(-2.0,-1.62,-1.64,z)
    plank(-.63,-.405,-1.64,z)
    if z>2.12:plank(-1.61,-.64,-1.64,z)
    # Largest circle cut across the board interval yields a clear 1.10m aperture with no hidden backing.
    dz=max(0,abs(z-1.62)-.094)
    half=math.sqrt(max(0,.565**2-dz**2)) if dz<.565 else 0
    if half:
        plank(-.397,.82-half,-1.64,z)
        plank(.82+half,1.998,-1.64,z)
    else:plank(-.397,1.998,-1.64,z)
    for side in [-1,1]:plank(-1.56,1.56,side*2.015,z,side=True)
    plank(-1.94,1.94,1.638,z)
box('EaveFrontLintel',(0,-1.685,2.55),(4.06,.11,.14),TIMBER[1],.012)
# Close a pre-existing 3 cm front-wall seam above the left door jamb without changing door clearance.
box('WallBoardDoorJambCap',(-1.585,-1.64,2.205),(.065,.065,.21),IVORY[1])

# Low stone skirt does not cover the door or raise floor collision height.
for side in [-1,1]:
    for j in range(7):
        y=-1.44+j*.47
        box('FieldstoneSide',(side*2.005,y,.135),(.19,.445,.26),RNG.choice(STONES),.035)
for y in [-1.66,1.66]:
    for j in range(9):
        x=-1.8+j*.45
        if y<0 and -1.70<x<-.52:continue
        box('FieldstoneFoot',(x,y,.135),(.43,.20,.26),RNG.choice(STONES),.03)

# Closed curved clay tiles. Grain/roughness texture slots remain for subsequent material work.
def tile(name,side,x0,x1,y0,y1,row):
    verts=[];samples=5
    for bottom in [False,True]:
        for x in [x0,x1]:
            for k in range(samples):
                t=k/(samples-1);y=y0+(y1-y0)*t
                camber=.026*math.sin(t*math.pi)
                z=3.82-abs(x)*1.18/2.29+camber-(.045 if bottom else 0)
                z+=.012*math.sin(row*1.7+y*2.5)
                verts.append((side*x,y,z))
    faces=[]
    for k in range(samples-1):
        faces.extend([(k,k+1,samples+k+1,samples+k),(2*samples+k,3*samples+k,3*samples+k+1,2*samples+k+1)])
    for edge in [0,samples-1]:faces.append((edge,samples+edge,3*samples+edge,2*samples+edge))
    for end in [0,1]:
        off=end*samples
        for k in range(samples-1):faces.append((off+k,off+2*samples+k,off+2*samples+k+1,off+k+1))
    return mesh(name,verts,faces,RNG.choice(TILES))
for side in [-1,1]:
    for row in range(5):
        x0=row*.445;x1=min(2.29,x0+.51)
        for j in range(10):
            y0=-1.895+j*.379
            tile('OverlappingClayTile',side,x0,x1,y0,y0+.383,row)
for j in range(10):
    cylinder('RidgeCap',(0,-1.81+j*.39,3.836),.087,.40,TILES[j%len(TILES)],8,(math.pi/2,0,0))

# Eaves project within the original envelope and give a readable crafted silhouette.
for side in [-1,1]:
    box('EaveBeam',(side*2.20,0,2.58),(.13,3.83,.15),TIMBER[0],.015)
    for y in [-1.47,-.75,0,.75,1.47]:
        beam('ExposedRafterTail',(side*1.93,y,2.52),(side*2.25,y,2.57),.095,TIMBER[1],True)
        beam('EaveKneeBrace',(side*1.97,y,2.11),(side*2.15,y,2.50),.085,TIMBER[2],True)

# Sea-facing attic dormer: exterior recess only, not a navigable upper floor.
box('AtticFront',(-.18,-1.95,3.17),(1.02,.12,.77),IVORY[2],.012)
box('AtticLeft',(-.69,-1.69,3.15),(.10,.57,.70),IVORY[1],.012)
box('AtticRight',(.33,-1.69,3.15),(.10,.57,.70),IVORY[0],.012)
mesh('DormerGable',[(-.74,-2.02,3.51),(.38,-2.02,3.51),(-.18,-2.02,3.83)],[(0,1,2)],IVORY[1])
for side in [-1,1]:
    x0=-.18;x1=-.18+side*.65
    verts=[(x0,-2.16,3.88),(x1,-2.16,3.49),(x1,-1.27,3.49),(x0,-1.27,3.88),
           (x0,-2.16,3.82),(x1,-2.16,3.43),(x1,-1.27,3.43),(x0,-1.27,3.82)]
    mesh('DormerRoof',verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],TILES[2])
    beam('DormerBargeboard',(-.18,-2.18,3.83),(x1,-2.18,3.44),.09,TIMBER[1],True)
    for j in range(4):
        y=-2.11+j*.22
        beam('DormerTileSeam',(-.18,y,3.893),(x1,y,3.503),.025,TILES[3])
box('AtticWindowRecess',(-.18,-2.025,3.20),(.52,.025,.56),TIMBER[0])
box('AtticAmberGlass',(-.18,-2.047,3.20),(.42,.008,.46),GLASS)
for dx,dz,w,h in [(-.27,0,.065,.67),(.27,0,.065,.67),(0,-.31,.60,.065),(0,.31,.60,.065),(0,0,.035,.56),(0,0,.52,.035)]:
    box('AtticWindowFrame',(-.18+dx,-2.065,3.20+dz),(w,.075,h),TIMBER[2],.008)
box('AtticWindowSill',(-.18,-2.12,2.875),(.70,.26,.075),TIMBER[1],.013)

# Low old tin flue clears the roof on its right slope without exceeding baseline ridge height.
cylinder('TinFlue',(.95,.56,3.49),.115,.69,IRON,12)
cylinder('FlueCap',(.95,.56,3.854),.17,.055,IRON,12)
for z in [3.27,3.65]:cylinder('FlueBand',(.95,.56,z),.124,.035,COPPER,12)
box('FlueFlashing',(.95,.56,3.31),(.44,.44,.035),IRON)

# Door and window hardware adds tactile scale; no geometry is added inside the open round window.
for z in [.32,1.62]:box('DoorHinge',(-1.677,-1.86,z),(.035,.20,.085),IRON,.008)
for x in [.23,1.41]:
    cylinder('RoundWindowHinge',(x,-1.71,1.62),.025,.16,COPPER,8)
box('DoorPullPlate',(-1.73,-2.28,1.02),(.035,.11,.14),COPPER,.009)

apply_normals_uv()
# Join by surface family to keep useful submeshes without exporting hundreds of draw objects.
root=bpy.data.objects.get('abode_grandma')
for family in ['WallBoard','SidingNail','Fieldstone','OverlappingClayTile','RidgeCap','Eave','ExposedRafter','Attic','Dormer','TinFlue','Flue','DoorHinge','DoorPull','RoundWindowHinge']:
    objs=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(family)]
    if not objs:continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=bpy.context.object;o.name='V2_'+family
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    o.parent=root;o.matrix_parent_inverse=root.matrix_world.inverted()

bpy.context.view_layer.update()
after_markers=markers();after_bounds=bounds();ntri=triangles()
checks=[]
def check(name,ok,detail=None):checks.append({'name':name,'passed':bool(ok),'detail':detail})
check('triangle_budget_12000',ntri<=12000,ntri)
for name,pose in baseline_markers.items():check('marker_exact_'+name,after_markers.get(name)==pose,after_markers.get(name))
check('original_source_unchanged',sha(BASE)==original_sha,sha(BASE))
for i,axis in enumerate('XYZ'):
    check('bounds_envelope_'+axis,after_bounds['min'][i]>=baseline_bounds['min'][i]-.035 and after_bounds['max'][i]<=baseline_bounds['max'][i]+.035,
          {'before':[baseline_bounds['min'][i],baseline_bounds['max'][i]],'after':[after_bounds['min'][i],after_bounds['max'][i]]})
# Ray checks in Blender coordinates prove front aperture stays open, not the entire Unity gameplay cone.
allv=[];allf=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    off=len(allv);allv.extend(o.matrix_world@v.co for v in o.data.vertices)
    allf.extend(tuple(off+i for i in p.vertices) for p in o.data.polygons)
bvh=BVHTree.FromPolygons(allv,allf)
for name,x,z in [('window_center',.82,1.62),('window_left',.52,1.62),('window_right',1.12,1.62),('window_top',.82,1.95),('entry',-1.13,1.1)]:
    hit=bvh.ray_cast(Vector((x,-3,z)),Vector((0,1,0)),1.9)
    check('aperture_clear_'+name,hit[0] is None,{'origin':[x,-3,z],'length':1.9,'hit':list(hit[0]) if hit[0] else None})
check('all_meshes_have_uv',all(o.data.uv_layers.active is not None for o in bpy.context.scene.objects if o.type=='MESH'))

scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
blend=OUT/'abode_grandma_v2_candidate.blend';fbx=OUT/'abode_grandma_v2_candidate.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,
    mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
render_set('after')
report={'status':'offline-candidate-not-imported','source_blend':str(BASE.relative_to(ROOT)).replace('\\','/'),'source_sha256':original_sha,
 'source_metadata':str(META.relative_to(ROOT)).replace('\\','/'),'script_sha256':sha(Path(__file__)),
 'baseline_triangles':baseline_triangles,'candidate_triangles':ntri,'budget':12000,'baseline_bounds_blender':baseline_bounds,
 'candidate_bounds_blender':after_bounds,'markers_before':baseline_markers,'markers_after':after_markers,'checks':checks,
 'mesh_objects':sum(o.type=='MESH' for o in bpy.context.scene.objects),'material_count':len({m.name for o in bpy.context.scene.objects if o.type=='MESH' for m in o.data.materials if m}),
 'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [blend,fbx]+sorted(OUT.glob('*.png'))],
 'render_views':VIEWS,'render_resolution':[1000,1000],'render_lighting':'Identical neutral studio setup before/after; not night in-game rendering.',
 'changes':['Retained baseline structure, genuine circular opening, open doorway, desk, book and seat.','Replaced old flat roof and narrow raised grid lines with overlapping curved clay tiles.','Added sea-facing attic exterior recess within original height envelope, timber eaves and low tin chimney.','Added staggered whitewashed siding, sparse nail heads, uneven stone foot and restrained metal hardware.','Smart-projected UVs generated for every mesh; no external texture was used.'],
 'limits':['Not imported into Unity; prior FBX axis workaround must be tested before substitution.','Attic is exterior visual geometry only: no walkable upstairs, ladder or new interior navigation.','No wood grain / clay / plaster PBR maps yet; previews use material colors and actual geometry.','5 local aperture rays are only a geometry sanity check, not complete spotlight/camera/capsule validation.','New attic window is unlit; gameplay visibility/emission hookup requires owner integration.','All original Marker transforms remain fixed; future integration must verify actual prefab anchors and colliders.']}
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ENV_V2_GRANDMA_DONE',ntri,'FAILED',sum(not c['passed'] for c in checks),flush=True)
