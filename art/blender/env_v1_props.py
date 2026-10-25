"""Original low-poly environment props for JieGuang v1.

Run with Blender 4.5 --background --factory-startup --python this-file.
Only writes art/generated/env-v1/props/. No downloaded asset is edited.
All coordinates are metres, Blender Z-up and front -Y. FBX is Y-up/-Z.
"""
import bpy
import bmesh
import math
import json
import hashlib
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'generated' / 'env-v1' / 'props'
OUT.mkdir(parents=True, exist_ok=True)
TAU = math.tau
ASSETS = []


def material(name, rgb, metallic=0.0, roughness=.68, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def assign(o, mat):
    if mat:
        o.data.materials.append(mat)
    return o


def cube(name, loc, dims, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(o, mat)
    if bevel:
        mod = o.modifiers.new('Soft crafted edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
        o.modifiers.new('Weighted corners', 'WEIGHTED_NORMAL')
    return o


def mesh(name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    assign(o, mat)
    return o


def cyl(name, loc, r, depth, mat, n=12, rot=None, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=depth, location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r, radius2=r2, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    if rot:
        o.rotation_euler = rot
    assign(o, mat)
    return o


def beam(name, a, b, radius, mat, n=8):
    a, b = Vector(a), Vector(b)
    o = cyl(name, (a+b)*.5, radius, (b-a).length, mat, n=n)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o


def band(name, center, radius, tube, mat, plane='XZ', n=32, sides=4, start=0, end=TAU):
    verts, faces = [], []
    complete = abs(end-start-TAU)<1e-5
    count = n if complete else n+1
    for i in range(count):
        t = start + (end-start)*i/n
        for j in range(sides):
            q = TAU*j/sides
            u = (radius+tube*math.cos(q))*math.cos(t)
            v = (radius+tube*math.cos(q))*math.sin(t)
            w = tube*math.sin(q)
            xyz = (u,w,v) if plane=='XZ' else ((w,u,v) if plane=='YZ' else (u,v,w))
            verts.append(tuple(center[k]+xyz[k] for k in range(3)))
    for i in range(n):
        ni = (i+1)%count
        for j in range(sides):
            faces.append((i*sides+j, i*sides+(j+1)%sides, ni*sides+(j+1)%sides, ni*sides+j))
    if not complete:
        faces += [tuple(reversed(range(sides))), tuple((count-1)*sides+j for j in range(sides))]
    return mesh(name, verts, faces, mat)


def marker(name, loc, rotation=(0,0,0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rotation
    o.empty_display_type = 'ARROWS'
    o.empty_display_size = .18
    return o


def join_objects(objects, name, pivot=(0,0,0)):
    if not objects:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    bpy.context.scene.cursor.location = pivot
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o


def finish(asset_id, description, notes=None, special_groups=None, keep_prefix=('Window_',), root_pivot=(0,0,0), preview=True):
    special_groups = special_groups or {}
    # Joining meshes otherwise discards non-active objects' Solidify/normal modifiers.
    # Recalculate closed volumes before joining: mirrored roof halves and the ring
    # facade must remain visible with Unity's single-sided material culling.
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    for group_name, prefix in special_groups.items():
        group = [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix)]
        join_objects(group, group_name, root_pivot)
    keep_names = set(special_groups)
    solids = [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith(keep_prefix) and o.name not in keep_names]
    join_objects(solids, 'Structure', root_pivot)
    root = marker(asset_id, root_pivot)
    all_objects = [o for o in bpy.context.scene.objects if o!=root]
    for o in all_objects:
        matrix = o.matrix_world.copy()
        o.parent = root
        o.matrix_world = matrix
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = 0
    meshes = []
    bounds = []
    for o in all_objects:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(depsgraph)
        em = ev.to_mesh()
        em.calc_loop_triangles()
        tris = len(em.loop_triangles)
        total += tris
        verts = [o.matrix_world @ v.co for v in em.vertices]
        bounds += verts
        meshes.append({'name':o.name, 'triangles':tris, 'materials':[s.material.name for s in o.material_slots if s.material]})
        ev.to_mesh_clear()
    bmin = [min(v[i] for v in bounds) for i in range(3)]
    bmax = [max(v[i] for v in bounds) for i in range(3)]
    marks = {}
    for o in all_objects:
        if o.type=='EMPTY':
            p=o.matrix_world.translation
            marks[o.name]={'blender_xyz':[round(v,4) for v in p], 'unity_xyz':[round(p.x,4),round(p.z,4),round(-p.y,4)], 'blender_rotation_degrees':[round(math.degrees(v),3) for v in o.rotation_euler]}
    dest = OUT / asset_id
    dest.mkdir(exist_ok=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(dest/(asset_id+'.fbx')),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/(asset_id+'.blend')))
    m={'asset_id':asset_id, 'description':description,'source':'Original procedural placeholder authored for the final JieGuang script; no legacy game asset reused.', 'source_script':str(Path(__file__).relative_to(ROOT.parent)).replace('\\','/'), 'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'fbx':str((dest/(asset_id+'.fbx')).relative_to(ROOT.parent)).replace('\\','/'), 'fbx_sha256':hashlib.sha256((dest/(asset_id+'.fbx')).read_bytes()).hexdigest(),'triangles':total,'meshes':meshes,'bounds_blender':{'min':bmin,'max':bmax},'dimensions_metres':[round(bmax[i]-bmin[i],4) for i in range(3)],'coordinates':'Blender Z-up, front -Y; FBX Y-up/-Z; intended Unity point mapping (x,z,-y), confirm after import.', 'root_pivot_blender':list(root_pivot),'markers':marks,'notes':notes or []}
    (dest/'asset.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    ASSETS.append(m)
    if preview:
        render_preview(dest/'preview.png', bmin, bmax)
    clear()


def render_preview(path, bmin, bmax):
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.resolution_x=640
    scene.render.resolution_y=640
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.color=(.17,.17,.17)
    scene.view_settings.view_transform='AgX'
    center=Vector(tuple((bmin[i]+bmax[i])*.5 for i in range(3)))
    span=max(bmax[i]-bmin[i] for i in range(3))
    bpy.ops.object.camera_add(location=center+Vector((span*.95,-span*1.65,span*.95)))
    cam=bpy.context.object
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'
    cam.data.ortho_scale=span*1.47
    scene.camera=cam
    for pos,power,size in [((span,-span*2,span*3),220*span*span,span*2),((-span,-span*.4,span*1.1),65*span*span,span*2)]:
        bpy.ops.object.light_add(type='AREA',location=center+Vector(pos))
        light=bpy.context.object
        light.data.energy=power
        light.data.shape='DISK'
        light.data.size=size
        light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.film_transparent=False
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


clear()
WOOD=material('Wood_Honey',(.36,.20,.10))
WOODLIGHT=material('Wood_Endgrain',(.53,.34,.18))
WOODSILVER=material('Wood_Weathered',(.31,.32,.27))
BEAM=material('Wood_DarkBeams',(.19,.13,.09))
WALL=material('Wall_WarmIvory',(.71,.64,.48))
WALL2=material('Wall_LightTimber',(.57,.44,.29))
TEAL=material('Roof_AgedTeal',(.12,.31,.31))
TEAL2=material('Roof_TealHighlight',(.18,.40,.36))
OCHRE=material('Roof_OchreRed',(.46,.20,.13))
OCHRE2=material('Roof_RedHighlight',(.57,.28,.17))
SLATE=material('Roof_WarmSlate',(.27,.32,.35))
SLATE2=material('Roof_SlateHighlight',(.37,.41,.41))
STONE=material('Stone_SoftGrey',(.36,.36,.31))
STONE2=material('Stone_WarmLimestone',(.48,.46,.37))
COPPER=material('Copper_Aged',(.43,.24,.10),metallic=.60,roughness=.42)
GOLD=material('Gold_WornEdges',(.67,.42,.12),metallic=.66,roughness=.36)
IRON=material('Iron_Blackened',(.12,.14,.14),metallic=.62,roughness=.45)
GLOW=material('Window_AmberEmission',(1,.43,.10),roughness=.45,emission=1.5)
GLASS=material('Lantern_AmberCore',(1,.58,.19),roughness=.3,emission=2.2)
BLUE=material('Flag_FadedIndigo',(.16,.28,.45))
FADED=material('Flag_WeatheredEdge',(.58,.61,.59))
SAGE=material('Flag_SilverTree',(.53,.64,.46))
CLOTH=material('Cloth_Unbleached',(.65,.61,.47))


def roof(w,d,h,rise,m1,m2):
    # Two closed pitched slabs, ridgeline runs along Y. Broad tile rows stay readable.
    for side in [-1,1]:
        verts=[(0,-d/2-.26,h+rise),(side*(w/2+.29),-d/2-.26,h-.05),(side*(w/2+.29),d/2+.26,h-.05),(0,d/2+.26,h+rise),
               (0,-d/2-.26,h+rise+.10),(side*(w/2+.29),-d/2-.26,h+.05),(side*(w/2+.29),d/2+.26,h+.05),(0,d/2+.26,h+rise+.10)]
        mesh('RoofPlane',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m1)
        slope=rise/(w/2+.29)
        for row in range(1,5):
            x=side*(w/2+.29)*row/5
            z=h+rise+.115-abs(x)*slope
            beam('TileRow', (x,-d/2-.24,z),(x,d/2+.24,z),.026,m2,6)
        for j in range(7):
            y=-d/2-.21+(d+.42)*j/6
            beam('TileSeam',(side*.08,y,h+rise+.11),(side*(w/2+.28),y,h+.04),.017,m2,5)
    beam('RoofRidge',(0,-d/2-.33,h+rise+.13),(0,d/2+.33,h+rise+.13),.085,m2,8)
    for y in [-d/2-.27,d/2+.27]:
        for side in [-1,1]:
            beam('Fascia',(0,y,h+rise+.04),(side*(w/2+.28),y,h-.04),.077,WOOD,6)


def triangle_gable(w,d,h,rise,mat):
    for y in [-d/2,d/2]:
        o=mesh('Gable', [(-w/2,y,h),(w/2,y,h),(0,y,h+rise)],[(0,1,2)],mat)
        mod=o.modifiers.new('Gable thickness','SOLIDIFY'); mod.thickness=.11
    beam('GableKingPost',(0,-d/2-.02,h),(0,-d/2-.02,h+rise),.065,BEAM,4)


def square_window(x,y,z,w=.70,h=.85,side=False):
    o=cube('Window_%02d'%sum(1 for q in bpy.context.scene.objects if q.name.startswith('Window_')),(x,y,z),(w,.035,h),GLOW)
    o['separate_emissive_window']=True
    for dx,dz,sw,sh in [(-w/2,0,.08,h+.16),(w/2,0,.08,h+.16),(0,-h/2,w+.16,.08),(0,h/2,w+.16,.08),(0,0,.047,h),(0,0,w,.047)]:
        cube('WindowFrame',(x+dx,y-.025,z+dz),(sw,.08,sh),BEAM)
    cube('WindowSill',(x,y-.10,z-h/2-.045),(w+.22,.28,.095),WOODLIGHT)
    return o


def cottage(asset_id,w,d,h,rise,roof_m,wall):
    cube('Plinth',(0,0,.10),(w+.13,d+.13,.20),STONE)
    cube('Walls',(0,0,h/2+.10),(w,d,h),wall)
    for x in [-w/2,w/2]:
        for y in [-d/2,d/2]:
            cube('CornerTimber',(x,y,h/2+.1),(.13,.13,h+.1),BEAM)
    for z in [.28,.69,1.1,1.51,1.92,h-.1]:
        if z<h:
            cube('HorizontalSiding',(0,-d/2-.018,z),(w,.032,.018),WOODLIGHT)
    door_x=-w*.20
    cube('Door',(door_x,-d/2-.05,.99),(.75,.07,1.76),WOOD)
    for x in [door_x-.41,door_x+.41]:
        cube('DoorFrame',(x,-d/2-.11,1.03),(.09,.10,1.95),BEAM)
    cube('DoorLintel',(door_x,-d/2-.11,1.99),(.91,.12,.12),BEAM)
    cyl('DoorHandle',(door_x+.24,-d/2-.125,1.04),.047,.04,COPPER,8,(math.pi/2,0,0))
    cube('Doorstep',(door_x,-d/2-.23,.11),(1.06,.48,.22),STONE2,bevel=.025)
    square_window(w*.24,-d/2-.038,1.4,.67,.83)
    square_window(0,d/2+.038,1.4,.80,.77)
    triangle_gable(w,d,h+.1,rise,wall)
    roof(w,d,h+.1,rise,*roof_m)
    cube('Chimney',(w*.25,d*.22,h+rise*.8),(.34,.40,.86),STONE)
    cube('ChimneyCap',(w*.25,d*.22,h+rise*.8+.44),(.44,.49,.09),STONE2)
    marker('Marker_Door',(door_x,-d/2-.43,.22))
    finish(asset_id,'坡上村子可复用木屋；独立暖琥珀窗，两扇窗可分别亮灭。',notes=['Village window mesh names start Window_; reparent to Village_Windows preserving world transform.','Village cottages are exterior shells; no interior navigation.','Front is Blender -Y; intended Unity +Z.'])


for args in [('cottage_teal',3.1,2.65,2.22,1.10,(TEAL,TEAL2),WALL),('cottage_ochre',3.35,2.8,2.28,1.0,(OCHRE,OCHRE2),WALL2),('cottage_slate',2.75,2.8,2.2,1.15,(SLATE,SLATE2),WALL)]:
    cottage(*args)


def rectangle_with_round_hole(x0,x1,z0,z1,cx,cz,r,y,thick,mat):
    # A hollow wall section, exact rectangle outer border and polygonal circular opening.
    angles=[TAU*i/32 for i in range(32)]
    angles += [math.atan2(z-cz,x-cx)%TAU for x,z in [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
    angles=sorted(set(round(a,9) for a in angles))
    verts=[]
    for yy in [y-thick/2,y+thick/2]:
        for a in angles:
            dx,dz=math.cos(a),math.sin(a)
            ts=[]
            if dx>1e-8:ts.append((x1-cx)/dx)
            if dx<-1e-8:ts.append((x0-cx)/dx)
            if dz>1e-8:ts.append((z1-cz)/dz)
            if dz<-1e-8:ts.append((z0-cz)/dz)
            t=min(ts)
            verts.extend([(cx+r*dx,yy,cz+r*dz),(cx+t*dx,yy,cz+t*dz)])
    n=len(angles); faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [(2*i,2*j,2*j+1,2*i+1),(2*n+2*i+1,2*n+2*j+1,2*n+2*j,2*n+2*i),
                  (2*i,2*n+2*i,2*n+2*j,2*j),(2*i+1,2*j+1,2*n+2*j+1,2*n+2*i+1)]
    return mesh('FrontWall_OpenRoundWindow',verts,faces,mat)


# 阿婆的小屋：圆窗孔径直径1.10m，不用透明面替代开洞；入口净宽.90m。
w,d,h,rise=4.0,3.25,2.55,1.18
cube('Floor',(0,0,.08),(w,d,.16),WOOD)
cube('RearWall',(0,d/2-.08,h/2),(w,.16,h),WALL)
for x in [-w/2+.08,w/2-.08]:
    cube('SideWall',(x,0,h/2),(.16,d,h),WALL)
# Front regions: left pillar, door opening, central pier, round-window wall.
cube('FrontLeft',(-1.78,-d/2+.08,h/2),(.44,.16,h),WALL)
cube('FrontMiddle',(-.53,-d/2+.08,h/2),(.26,.16,h),WALL)
cube('DoorOverhead',(-1.13,-d/2+.08,2.275),(.99,.16,.55),WALL)
rectangle_with_round_hole(-.4,2,.0,h,.82,1.62,.55,-d/2+.08,.16,WALL)
for x in [-1.61,-.64]:
    cube('EntryFrame',(x,-d/2-.035,1.01),(.11,.11,2.04),BEAM)
cube('EntryLintel',(-1.13,-d/2-.055,2.06),(1.10,.17,.12),BEAM)
door=cube('DoorOpen',(-1.62,-d/2-.46,1.0),(.08,.89,1.96),WOOD)
door.rotation_euler.z=-.16
cube('Doorstep',(-1.12,-d/2-.28,.075),(1.2,.6,.15),STONE2)
band('RoundWindowFrame',(.82,-d/2-.015,1.62),.59,.065,WOODLIGHT,'XZ',40,6)
cube('RoundWindowSill',(.82,-d/2-.10,1.035),(1.36,.35,.09),WOODLIGHT)
for x in [-w/2,w/2]:
    for y in [-d/2,d/2]:
        cube('CornerTimber',(x,y,h/2),(.13,.13,h),BEAM)
triangle_gable(w,d,h,rise,WALL)
roof(w,d,h,rise,TEAL,TEAL2)
# Desk inside the real hole: seated character looks forward toward the window.
cube('WritingDesk',(.82,-.98,.79),(1.33,.60,.09),WOODLIGHT,bevel=.02)
for x in [.27,1.37]:
    for y in [-1.19,-.77]:
        cube('DeskLeg',(x,y,.39),(.07,.07,.78),WOOD)
cube('Ledger_Left',(.67,-.97,.847),(.30,.34,.027),CLOTH)
cube('Ledger_Right',(.98,-.97,.849),(.30,.34,.027),CLOTH)
cube('ChairSeat',(.82,-.35,.45),(.46,.44,.07),WOOD)
for x in [.64,1.0]:
    for y in [-.52,-.18]:
        cube('ChairLeg',(x,y,.225),(.06,.06,.45),WOOD)
    cube('ChairBackPost',(x,-.16,.68),(.06,.065,.70),WOOD)
cube('ChairBack',(.82,-.16,.93),(.44,.06,.16),WOODLIGHT)
marker('Marker_Window',(.82,-d/2-.06,1.62))
marker('Marker_ABo_Seat',(.82,-.35,.49))
marker('Marker_Entry',(-1.13,-d/2-.48,.16))
marker('Marker_Desk',(.82,-.98,.84))
finish('abode_grandma','阿婆米白木屋、蓝绿瓦、真实开孔圆窗与敞开的门；室内桌椅和摊开的光树簿。',notes=['Round window has no glass or emissive occluder. Opening diameter 1.10 m.','Seat marker is hip/contact height 0.49m; facing front Blender -Y.','Use detailed MeshCollider for window facade if spotlight raycasts matter, not one solid whole-house box.','Door clear width about .85m; dwelling is a staging interior, no upstairs model.'])


# Lamp root is the swivel anchor, at local zero. Ground is local Z=-3.80.
cyl('LampFoot',(0,0,-3.69),.24,.22,COPPER,12)
cyl('LampBase',(0,0,-3.47),.15,.25,COPPER,12,r2=.092)
cyl('LampPost',(0,0,-1.88),.060,3.12,COPPER,12,r2=.043)
for z in [-3.34,-.61,-.23]:
    cyl('LampCollar',(0,0,z),.079,.075,GOLD,12)
beam('YokeLeft',(-.14,0,-.30),(-.14,0,0),.027,COPPER)
beam('YokeRight',(.14,0,-.30),(.14,0,0),.027,COPPER)
beam('YokeCross',(-.14,0,-.27),(.14,0,-.27),.026,COPPER)
# Front-directed shade, closed top, open front. Pivots around local X.
verts=[]; n=16
for yy,rad in [(.12,.115),(-.32,.245),(-.335,.22),(.10,.093)]:
    for i in range(n):
        a=TAU*i/n;verts.append((rad*math.cos(a),yy,rad*math.sin(a)))
faces=[]
for ring in range(3):
    for i in range(n):
        j=(i+1)%n;faces.append((ring*n+i,ring*n+j,(ring+1)*n+j,(ring+1)*n+i))
faces.append(tuple(reversed(range(n))))
mesh('HEAD_Shade',verts,faces,COPPER)
cyl('HEAD_AmberLens',(0,-.27,0),.163,.022,GLASS,16,(math.pi/2,0,0))
for x in [-.14,.14]:
    cyl('HEAD_SwivelCap',(x,0,0),.059,.032,GOLD,12,(0,math.pi/2,0))
marker('Marker_Bulb',(0,-.285,0))
marker('Marker_Base',(0,0,-3.8))
finish('copper_roadlamp','三盏谜题灯共用铜柱与可旋转遮光灯头；仅在场景实例化三次。',special_groups={'LampHead':'HEAD_'},notes=['Root and LampHead origin exactly at swivel. Root placed 3.80m above ground; Structure descends to -3.80m in Blender Z / Unity Y.','For a 4.0m lamp, scale only Structure along its height by 4/3.8. Leave LampHead at unit scale.','Default light/hood direction Blender -Y, intended Unity +Z. Rotate LampHead, not Structure.','No Blender light exported; Claude creates the gameplay spotlight at Marker_Bulb.','Only 3 lamp instances belong in the island.'])


def pier(asset_id,length,end=False):
    width=2.4
    for i in range(round(length/.245)):
        y=-length/2+(i+.5)*length/round(length/.245)
        cube('DeckBoard',(0,y,-.06),(width-.02,length/round(length/.245)-.013,.12), WOODLIGHT if i%4==0 else WOOD)
    for x in [-.9,.9]:
        cube('SupportGirder',(x,0,-.22),(.15,length+.06,.25),BEAM)
        for y in [-length/2+.22,length/2-.22]:
            cyl('PierPile',(x,y,-.91),.10,2.10,WOODSILVER,10)
            cyl('PileRim',(x,y,.10),.118,.055,IRON,10)
    if end:
        for x in [-1.08,1.08]:
            for y in [-length*.27,length*.27]:
                cube('MooringCleat',(x,y,.085),(.28,.09,.08),BEAM,bevel=.015)
    marker('Marker_Entry',(0,-length/2,0))
    marker('Marker_Exit',(0,length/2,0))
    finish(asset_id,'木栈桥模块，板面顶高为0，桩柱向下延伸。',notes=['Deck width 2.40m, deck top at local Z=0. Boards run X, bridge length along Y.','Add flat deck collision box, avoid tiny gaps catching movement. Piles extend 1.96m below deck.'])

pier('pier_module',3.0)
pier('pier_end',3.6,True)


# Thin mast, aged blue flag. Its old edge is a separate cloth strip, emblem is geometry.
cyl('Mast',(0,0,2.42),.075,4.84,WOOD,12,r2=.038)
cyl('MastFoot',(0,0,.12),.12,.24,IRON,12)
cyl('MastFinial',(0,0,4.9),.06,.14,WOODLIGHT,10,r2=.012)
beam('Halyard',(.08,-.015,.35),(.08,-.015,4.72),.011,CLOTH,5)
nx,nz=12,5
verts=[]
for j in range(nz+1):
    for i in range(nx+1):
        u=i/nx;v=j/nz
        verts.append((.08+1.26*u,.09*math.sin(u*TAU*1.5)+.035*u*math.sin(v*math.pi),4.63-.83*v-.11*u))
faces=[]
for j in range(nz):
    for i in range(nx):
        a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
flag=mesh('FLAG_Fabric',verts,faces,BLUE)
mod=flag.modifiers.new('Cloth has two sides','SOLIDIFY');mod.thickness=.007
for i in range(nx):
    u=(i+.5)/nx;x=.08+1.26*u
    beam('FLAG_FadedHem',(x-.054,.09*math.sin(u*TAU*1.5)-.007,3.8-.11*u),(x+.054,.09*math.sin(u*TAU*1.5)-.007,3.8-.11*u),.018,FADED,4)
def flag_y(x):
    u=(x-.08)/1.26
    return .09*math.sin(u*TAU*1.5)-.013
def emblem_poly(name,points,mat):
    mesh('FLAG_'+name,[(x,flag_y(x),z) for x,z in points],[tuple(range(len(points)))],mat)
emblem_poly('Tree',[(.39,4.12),(.70,4.12),(.62,4.23),(.67,4.23),(.58,4.34),(.62,4.34),(.54,4.47),(.46,4.34),(.50,4.34),(.41,4.23),(.46,4.23)],SAGE)
emblem_poly('Trunk',[(.517,4.02),(.562,4.02),(.562,4.16),(.517,4.16)],SAGE)
for cx,cz,r in [(.90,4.39,.105),(1.12,4.31,.063)]:
    points=[]
    for i in range(10):
        a=math.pi/2+TAU*i/10;rr=r if i%2==0 else r*.42
        points.append((cx+math.cos(a)*rr,cz+math.sin(a)*rr))
    emblem_poly('Star',points,GOLD)
# Hook deliberately at child-reachable height rather than literal half of 4.9m pole.
beam('HookBracket',(0,-.04,1.78),(0,-.25,1.78),.023,IRON)
band('IronHook',(0,-.23,1.68),.102,.024,IRON,'YZ',20,6,start=-math.pi*.5,end=math.pi*.86)
marker('Marker_FlagpoleHook',(0,-.30,1.77))
finish('flagpole_blue','细木旗杆、磨白边蓝旗，小光树与一大一小金星；旗杆下部铁钩可挂灯笼。',special_groups={'FlagFabric':'FLAG_'},notes=['Flagpole height 4.97m. Hook hanging contact at (0,-.30,1.77), reachable by a child standing on tiptoes.','One cloth mesh includes faded hem and tree/two-star emblem. Cloth is static placeholder.','Hook at 1.77m for gameplay accessibility, below exact geometric halfway of mast.'])


# Harbor storm lantern: separate asset, no fixed scene light.
cyl('LanternFoot',(0,0,.07),.17,.14,IRON,12,r2=.13)
cyl('LanternGlass',(0,0,.31),.12,.36,GLASS,12)
cyl('LanternCap',(0,0,.53),.18,.12,COPPER,12,r2=.085)
for x in [-.135,.135]:
    beam('LanternGuard',(x,0,.11),(x,0,.5),.018,IRON)
band('LanternHandle',(0,0,.63),.15,.013,IRON,'XZ',20,6,start=0,end=math.pi)
marker('Marker_HangingPoint',(0,0,.79))
finish('harbor_lantern','旗杆上可挂的大马灯；琥珀光芯单独材质，可由剧情熄灭。',notes=['Base pivot at Z=0, hanging point Z=.79. Light/emission animation handled in Unity.'])


# Bench facing -Y, top of seating 0.45m.
for y in [-.20,0,.20]:
    cube('SeatSlat',(0,y,.41),(1.96,.18,.08),WOODLIGHT,bevel=.013)
for x in [-.76,.76]:
    for y in [-.17,.17]:
        cube('BenchLeg',(x,y,.19),(.095,.10,.38),BEAM)
    cube('BackPost',(x,.22,.66),(.10,.10,.83),WOOD)
    beam('BenchBrace',(x,-.19,.12),(x,.20,.37),.041,WOOD,5)
for z in [.70,.94]:
    cube('BackSlat',(0,.255,z),(1.96,.08,.17),WOODLIGHT,bevel=.016)
marker('Marker_Seat',(0,-.04,.45))
finish('bench','路口双人木长椅，坐高0.45m，朝正前方。',notes=['Seat marker is contact/hip height, not foot height. Facing Blender -Y.'])


cube('CrateCore',(0,0,.26),(.67,.57,.52),WOOD)
for x in [-.28,.28]:
    for y in [-.30,.30]:
        cube('CrateFrame',(x,y,.27),(.085,.075,.54),WOODLIGHT)
for y in [-.30,.30]:
    for z in [.07,.47]:
        cube('CrateRail',(0,y,z),(.68,.06,.08),WOODLIGHT)
    o=cube('CrateDiagonal',(0,y-.015,.27),(.60,.045,.065),WOODLIGHT)
    o.rotation_euler.y=.55
for i in range(4):
    cube('CrateTop',(-.255+.17*i,0,.535),(.16,.59,.05),WOODLIGHT)
marker('Marker_Seat',(0,0,.56))
finish('dock_crate','灯伯旗杆下坐的旧木箱。',notes=['Top contact .56m; use Marker_Seat for seated NPC offset.'])


cyl('KettleBody',(0,0,.17),.15,.27,WOODSILVER,12,r2=.13)
cyl('KettleLid',(0,0,.322),.135,.036,IRON,12,r2=.10)
cyl('KettleKnob',(0,0,.36),.034,.047,WOOD,8)
beam('KettleSpout',(.11,0,.18),(.25,0,.31),.036,WOODSILVER,8)
band('KettleHandle',(0,0,.35),.16,.020,IRON,'XZ',20,6,start=0,end=math.pi)
cyl('WaterBowl',(-.27,-.03,.055),.095,.095,CLOTH,12,r2=.115)
finish('dock_kettle','灯伯脚边铁皮水壶与一碗热水，简化实体占位。')


# Three clear rings rather than an unreadable nest of narrow geometry.
cyl('StonePlatform',(0,0,.105),1.12,.21,STONE2,32)
cyl('StoneStep',(0,0,.035),1.22,.07,STONE,32)
cyl('ArmillaryFoot',(0,0,.27),.37,.12,COPPER,16,r2=.27)
cyl('ArmillaryStem',(0,0,.69),.11,.75,COPPER,12,r2=.07)
cyl('ArmillaryCollar',(0,0,1.01),.20,.07,GOLD,16)
ring_center=(0,0,1.55)
band('Meridian',ring_center,.61,.035,COPPER,'XZ',48,6)
band('Horizon',ring_center,.56,.026,GOLD,'XY',48,6)
o=band('Ecliptic',(0,0,0),.51,.029,COPPER,'XY',48,6)
o.location=ring_center;o.rotation_euler.x=.46
beam('EarthAxis',(0,0,.92),(0,0,2.2),.023,GOLD,8)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.14,location=ring_center)
assign(bpy.context.object,GOLD);bpy.context.object.name='CentralGlobe'
for i in range(12):
    a=TAU*i/12
    beam('MeridianTick',(.60*math.cos(a),-.042,1.55+.60*math.sin(a)),(.55*math.cos(a),-.042,1.55+.55*math.sin(a)),.012,GOLD,4)
finish('armillary_platform','岬角圆形石台上的铜浑天仪：三道清晰铜环、中心小球。',notes=['Stone platform radius 1.22m, height .21m; instrument height 2.2m.','Decorative instrument only; no celestial simulation or interactive mechanics embedded.'])


# Extruded true crescent silhouette with matching inner/outer angular samples.
verts=[];n=40;r=1.02;cx=.42;inner=.89
# Circle intersections: outer x=(R²-r²+d²)/2d.
xx=(r*r-inner*inner+cx*cx)/(2*cx)
zz=math.sqrt(max(0,r*r-xx*xx))
a0=math.atan2(zz,xx)
innera=math.atan2(zz,xx-cx)
profile=[]
for i in range(n+1):
    a=a0+(TAU-2*a0)*i/n
    profile.append((r*math.cos(a),r*math.sin(a)))
for i in range(1,n):
    a=(TAU-innera)-(TAU-2*innera)*i/n
    profile.append((cx+inner*math.cos(a),inner*math.sin(a)))
N=len(profile)
for y in [-.10,.10]:
    for x,z in profile:verts.append((x,y,z+1.30))
faces=[tuple(reversed(range(N))),tuple(N+i for i in range(N))]
for i in range(N):j=(i+1)%N;faces.append((i,j,N+j,N+i))
mesh('Crescent',verts,faces,GOLD)
cyl('CrescentBase',(0,0,.105),.46,.21,STONE2,16)
cube('CrescentStem',(-.14,0,.24),(.14,.14,.28),COPPER)
finish('crescent_sculpture','金色月牙纪念雕塑，真实弯月轮廓；与屋前金色光树相伴。')


# Open well mouth, with twelve wedge stones per course.
for row in range(3):
    for i in range(12):
        a=TAU*(i+row*.5)/12
        vs=[]
        for z in [.05+row*.22,.26+row*.22]:
            for radius,ang in [(.63,a+.015),(.88,a+.015),(.88,a+TAU/12-.015),(.63,a+TAU/12-.015)]:
                vs.append((radius*math.cos(ang),radius*math.sin(ang),z))
        mesh('WellStone',vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],STONE2 if i%3 else STONE)
for x in [-.78,.78]:
    cube('WellPost',(x,0,1.13),(.12,.14,2.26),WOOD)
beam('WellSpindle',(-.9,0,1.36),(.96,0,1.36),.072,WOODLIGHT,10)
beam('WellHandle',(.95,0,1.36),(.95,0,1.12),.032,IRON,8)
beam('WellCrank',(.95,0,1.12),(1.12,0,1.12),.041,WOOD,8)
beam('WellRope',(0,0,.30),(0,0,1.4),.016,CLOTH,5)
roof(1.75,1.30,2.12,.46,TEAL,TEAL2)
cyl('WellDarkInterior',(0,0,-.02),.63,.02,IRON,20)
finish('village_well','坡上村子石井，开口井沿、木摇柄和小蓝绿瓦顶。',notes=['Open well geometry extends .03m below ground, pivot remains ground Z=0.'])


for x in [-1.65,1.65]:
    cyl('LaundryPost',(x,0,1.0),.046,2.0,WOOD,8)
for i in range(12):
    x0=-1.65+3.3*i/12;x1=-1.65+3.3*(i+1)/12
    z0=1.93-.19*(1-(x0/1.65)**2);z1=1.93-.19*(1-(x1/1.65)**2)
    beam('Clothesline',(x0,0,z0),(x1,0,z1),.011,CLOTH,5)
for i,(x,w,h,mat) in enumerate([(-.95,.53,.68,CLOTH),(-.1,.57,.81,BLUE),(.80,.46,.61,CLOTH)]):
    top=1.93-.19*(1-(x/1.65)**2)
    vs=[(x-w/2,0,top),(x+w/2,0,top),(x+w/2+.025,-.07,top-h),(x-w/2+.06,-.10,top-h)]
    o=mesh('HangingCloth',vs,[(0,1,2,3)],mat)
    mo=o.modifiers.new('TwoSidedCloth','SOLIDIFY');mo.thickness=.008
    for dx in [-w*.34,w*.34]:cube('ClothesPeg',(x+dx,-.015,top),(.026,.047,.095),WOODLIGHT)
finish('laundry_line','两户木屋间的晾衣绳，三件旧布与木夹；静态占位。')


manifest={'version':1,'asset_count':len(ASSETS),'triangles_unique_assets':sum(a['triangles'] for a in ASSETS), 'units':'metres','authorship':'Original procedural art created for this project from final design document.','coordinate_convention':'Blender Z-up/front -Y; FBX Y-up; root is bottom centre except roadlamp (swivel), pier (deck top), and well (ground).','materials':[{ 'name':m.name, 'base_color':list(m.diffuse_color),'emission_strength':m.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value,'metallic':m.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value,'roughness':m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value} for m in bpy.data.materials if m.use_nodes and m.node_tree.nodes.get('Principled BSDF')], 'assets':ASSETS}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENV_V1_PROPS_SUCCESS',len(ASSETS),manifest['triangles_unique_assets'],flush=True)
