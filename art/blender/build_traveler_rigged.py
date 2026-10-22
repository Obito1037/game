"""Add continuous limb skinning to the frozen v4 traveler without remodelling it.

Blender 4.5: --background --factory-startup --python-exit-code 1 --python this.py
Use -- --render after independent validation to create pose presentation images.
The v4 source and Unity Resources are never written by this script.
"""
import bpy, json, hashlib, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'art/generated/character-v4/traveler.blend'
OUT = ROOT/'art/generated/character-v5'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
root = bpy.data.objects['TravelerRoot']
source_objects = [root] + list(root.children_recursive)
source_geometry = {}
for obj in source_objects:
    if obj.type == 'MESH':
        source_geometry[obj.name] = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
source_pivots = {o.name: list(o.matrix_world.translation) for o in source_objects if o.type == 'EMPTY'}

def smoothstep(low, high, value):
    t = max(0., min(1., (value-low)/(high-low)))
    return t*t*(3.-2.*t)

def armature(parent, specs):
    data = bpy.data.armatures.new(parent.name+'_SkinSkeleton')
    obj = bpy.data.objects.new(parent.name+'_SkinRig', data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_world = parent.matrix_world.copy()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    inverse = obj.matrix_world.inverted()
    previous = None
    for name, head, tail in specs:
        bone = data.edit_bones.new(name)
        bone.head = inverse @ Vector(head)
        bone.tail = inverse @ Vector(tail)
        bone.parent = previous
        # The local X is close to the lateral hinge. Runtime derives its exact
        # bind-space axis, avoiding FBX exporter/importer bone-roll assumptions.
        bone.align_roll(Vector((0, -1, 0)))
        bone.use_connect = previous is not None
        previous = bone
    if parent.name.startswith('Leg_'):
        anchor = data.edit_bones.new('HipAnchor_'+parent.name[-1])
        anchor.head = inverse @ Vector(specs[0][1])
        anchor.tail = anchor.head + Vector((0,0,.085))
        anchor.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.show_in_front = True
    obj.select_set(False)
    return obj

rigs = []
weights_manifest = []
for side, sign in [('L', -1), ('R', 1)]:
    for limb in ['Arm', 'Leg']:
        parent = bpy.data.objects[limb+'_'+side]
        meshes = [o for o in parent.children if o.type == 'MESH']
        start = parent.matrix_world.translation.copy()
        if limb == 'Arm':
            joint = Vector((sign*.206, -.004, .806))
            tip = Vector((sign*.231, -.0495, .667))
            names = ['UpperArm_'+side, 'Elbow_'+side]
            specs = [(names[0], start, joint), (names[1], joint, tip)]
        else:
            joint = Vector((start.x, .006, .398))
            ankle = Vector((start.x, .009, .090))
            names = ['Thigh_'+side, 'Knee_'+side, 'Ankle_'+side, 'HipAnchor_'+side]
            specs = [(names[0], start, joint), (names[1], joint, ankle),
                     (names[2], ankle, (start.x, -.101, .040))]
        rig = armature(parent, specs)
        rigs.append(rig)
        for obj in meshes:
            world = obj.matrix_world.copy()
            obj.parent = rig
            obj.matrix_world = world
            groups = {name: obj.vertex_groups.new(name=name) for name in names}
            blended = 0
            for vertex in obj.data.vertices:
                z = (obj.matrix_world @ vertex.co).z
                if limb == 'Arm':
                    # Skin only the continuous sleeve across the elbow. Fingers,
                    # cuff, nails and knit details remain a rigid hand assembly.
                    upper = smoothstep(joint.z-.047, joint.z+.047, z) if obj.name.startswith('Sleeve_') else 0.
                    values = [upper, 1.-upper]
                else:
                    thigh = smoothstep(joint.z-.065, joint.z+.065, z)
                    foot = 1.-smoothstep(.062, .132, z)
                    anchor = smoothstep(.505, .630, z)
                    values = [thigh-anchor, (1.-thigh)*(1.-foot), (1.-thigh)*foot, anchor]
                assert abs(sum(values)-1.) < 1e-7
                if sum(w > .00001 for w in values) > 1: blended += 1
                for name, weight in zip(names, values):
                    if weight > .000001: groups[name].add([vertex.index], weight, 'REPLACE')
            modifier = obj.modifiers.new('Continuous cloth and leather limb skin', 'ARMATURE')
            modifier.object = rig
            modifier.use_deform_preserve_volume = False  # Standard linear skinning in Unity/glTF.
            weights_manifest.append({'mesh': obj.name, 'rig': rig.name, 'bones': names,
                                     'vertices': len(obj.data.vertices), 'blended_vertices': blended})
        if limb == 'Arm' and side == 'R':
            lantern = bpy.data.objects['Lantern']
            world = lantern.matrix_world.copy()
            lantern.parent = rig
            lantern.parent_type = 'BONE'
            lantern.parent_bone = 'Elbow_R'
            bpy.context.view_layer.update()
            lantern.matrix_world = world

bpy.context.view_layer.update()
character = [root]+list(root.children_recursive)
depsgraph = bpy.context.evaluated_depsgraph_get()
rest_error = 0.
triangles = 0
for obj in character:
    if obj.type != 'MESH': continue
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    assert len(mesh.vertices) == len(source_geometry[obj.name]), obj.name
    for v, expected in zip(mesh.vertices, source_geometry[obj.name]):
        rest_error = max(rest_error, (evaluated.matrix_world @ v.co-Vector(expected)).length)
    mesh.calc_loop_triangles()
    triangles += len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
assert rest_error < .000005, 'Rig changed frozen neutral geometry'
assert triangles <= 55000

bpy.ops.object.select_all(action='DESELECT')
for obj in character: obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'), use_selection=True,
    object_types={'MESH','EMPTY','ARMATURE'}, global_scale=1, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
    use_space_transform=True, bake_space_transform=False, mesh_smooth_type='FACE',
    use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
    primary_bone_axis='Y', secondary_bone_axis='X', path_mode='COPY', embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'traveler.glb'), export_format='GLB',
    use_selection=True, export_yup=True, export_apply=False, export_materials='EXPORT',
    export_extras=True, export_skins=True, export_animations=False)

rig_manifest=[]
for rig in rigs:
    rig_manifest.append({'object':rig.name, 'parent':rig.parent.name,
        'bones':[{'name':b.name, 'parent':b.parent.name if b.parent else None,
                  'head_world':list(rig.matrix_world@b.head_local),
                  'tail_world':list(rig.matrix_world@b.tail_local),
                  'lateral_axis_bone_local':list((rig.matrix_world@b.matrix_local).to_quaternion().inverted()@Vector((1,0,0)))}
                 for b in rig.data.bones]})
manifest={'version':5,'source':str(SOURCE.relative_to(ROOT)),
    'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'triangles':triangles,'mesh_renderers':sum(o.type=='MESH' for o in character),
    'armatures':len(rigs),'bones':sum(len(r.data.bones) for r in rigs),
    'frozen_neutral_geometry_max_deviation_m':rest_error,
    'preserved_pivots_world':source_pivots, 'rigs':rig_manifest,'weights':weights_manifest,
    'lantern_parent_contract':'Lantern remains below Arm_R, now bone-parented to Elbow_R; hand and lantern share identical rigid forearm transform.',
    'motor_contract':'Preserve imported bind rotations. Compute joint-local lateral axis from the actor world right vector at Bind; bind * AngleAxis(degrees, axis).',
    'blink_contract':'Unchanged v4: Blink_L/R localScale=(.001,.001,1) open, (1,1,1) closed.',
    'axes':{'authoring_up':'+Z','authoring_forward':'-Y','unity_up':'+Y','unity_forward':'+Z'},
    'sha256':{}}
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))
for name in ['traveler.fbx','traveler.glb','traveler.blend']:
    manifest['sha256'][name]=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
(OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
print('RIGGED_TRAVELER_EXPORTED '+json.dumps({'triangles':triangles,'rest_error':rest_error,'rigs':rig_manifest}),flush=True)

if '--render' in sys.argv:
    scene=bpy.context.scene
    scene.render.resolution_x=800; scene.render.resolution_y=800
    scene.render.resolution_percentage=100; scene.cycles.samples=12
    camera=bpy.data.objects['PREVIEW_Camera']; scene.camera=camera
    def rotate_joint(name,degrees):
        for rig in rigs:
            pose=rig.pose.bones.get(name)
            if pose:
                axis=(rig.matrix_world@pose.bone.matrix_local).to_quaternion().inverted()@Vector((1,0,0))
                pose.rotation_mode='QUATERNION'; pose.rotation_quaternion=Quaternion(axis,math.radians(degrees))
                return
        raise AssertionError(name)
    def render(name,location):
        camera.location=location
        camera.rotation_euler=(Vector((0,0,.66))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type='ORTHO'; camera.data.ortho_scale=1.65
        scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)
    render('render-neutral.png',(1.45,-4.5,1.5))
    # Side stride exposes continuous knee/ankle deformation; relaxed arms expose elbows.
    bpy.data.objects['Leg_L'].rotation_euler.x=math.radians(-25)
    bpy.data.objects['Leg_R'].rotation_euler.x=math.radians(14)
    rotate_joint('Knee_L',42); rotate_joint('Ankle_L',-17)
    rotate_joint('Knee_R',8); rotate_joint('Ankle_R',-22)
    rotate_joint('HipAnchor_L',25); rotate_joint('HipAnchor_R',-14)
    rotate_joint('Elbow_L',-22); rotate_joint('Elbow_R',-9)
    bpy.context.view_layer.update()
    render('render-stride-front.png',(1.45,-4.5,1.5))
    render('render-stride-side.png',(4.5,-.35,1.4))
    print('RIGGED_TRAVELER_PREVIEWS_COMPLETE',flush=True)
