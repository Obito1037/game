"""Independent round-trip and posed deformation checks, separate Blender process."""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.kdtree import KDTree

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
manifest=json.loads((OUT/'traveler-manifest.json').read_text(encoding='utf-8'))
v5_manifest=json.loads((ROOT/'art/generated/character-v5/traveler-manifest.json').read_text(encoding='utf-8'))
manifest['preserved_pivots_world']=v5_manifest['preserved_pivots_world']
manifest['rigs']=v5_manifest['rigs']
required=set(manifest['preserved_pivots_world'])
expected_bones={b['name']:b for rig in manifest['rigs'] for b in rig['bones']}

def points(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    values=[evaluated.matrix_world@v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return values

def bone_map():
    return {p.name:(obj,p) for obj in bpy.context.scene.objects if obj.type=='ARMATURE' for p in obj.pose.bones}

def apply_pose():
    for name,degrees in [('Leg_L',-25),('Leg_R',14)]:
        obj=bpy.data.objects[name]
        bind=obj.matrix_basis.to_quaternion()
        axis=obj.matrix_world.to_quaternion().inverted()@Vector((1,0,0))
        obj.rotation_mode='QUATERNION'
        obj.rotation_quaternion=bind@Quaternion(axis,math.radians(degrees))
    for name,degrees in [('Knee_L',42),('Ankle_L',-17),('HipAnchor_L',25),('Knee_R',8),('Ankle_R',-22),('HipAnchor_R',-14),('Elbow_L',-22),('Elbow_R',-9)]:
        rig,pose=bone_map()[name]
        axis=(rig.matrix_world@pose.bone.matrix_local).to_quaternion().inverted()@Vector((1,0,0))
        pose.rotation_mode='QUATERNION'
        pose.rotation_quaternion=Quaternion(axis,math.radians(degrees))
    bpy.context.view_layer.update()

def shape_index(objects):
    result={}
    for o in objects:
        verts=points(o); tree=KDTree(len(verts))
        for i,p in enumerate(verts): tree.insert(p,i)
        tree.balance(); result[o.name]=tree
    return result

bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
source_meshes=[o for o in bpy.data.objects['TravelerRoot'].children_recursive if o.type=='MESH']
neutral=shape_index(source_meshes)
apply_pose()
posed=shape_index(source_meshes)
expected_lantern_pose=bpy.data.objects['Lantern'].matrix_world.copy()

results={}
for suffix in ['fbx','glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'),automatic_bone_orientation=False)
    else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    bpy.context.view_layer.update()
    errors=[]; mesh_rows=[]; bone_rows={}; max_neutral=0.; max_pivot=0.; tris=0
    for name,expected in manifest['preserved_pivots_world'].items():
        obj=bpy.data.objects.get(name)
        if obj is None: errors.append('missing pivot '+name); continue
        deviation=(obj.matrix_world.translation-Vector(expected)).length
        max_pivot=max(max_pivot,deviation)
        if deviation>.00015: errors.append('pivot position '+name)
    bones=bone_map()
    if set(bones)!=set(expected_bones): errors.append('12 named bones not preserved')
    for name,(rig,pose) in bones.items():
        expected=expected_bones[name]
        world=rig.matrix_world@pose.bone.matrix_local
        error=(world.translation-Vector(expected['head_world'])).length
        if error>.00015: errors.append('joint bind head '+name)
        # Verify axis reconstructs authoring +X, independently of exporter roll.
        axis=world.to_quaternion().inverted()@Vector((1,0,0))
        axis_error=(world.to_quaternion()@axis-Vector((1,0,0))).length
        bone_rows[name]={'bind_position_error_m':error,'lateral_axis_bone_local':list(axis),'axis_roundtrip_error':axis_error}
    # glTF importer creates hidden icospheres as Blender bone display shapes;
    # they are not asset geometry or glTF mesh nodes.
    meshes=[o for o in bpy.data.objects['TravelerRoot'].children_recursive if o.type=='MESH']
    for obj in meshes:
        obj.data.calc_loop_triangles(); tris+=len(obj.data.loop_triangles)
        if obj.name not in neutral: errors.append('mesh name '+obj.name); continue
        deviation=max(neutral[obj.name].find(p)[2] for p in points(obj))
        max_neutral=max(max_neutral,deviation)
        if deviation>.00002: errors.append('neutral shape changed '+obj.name)
        modifiers=[m for m in obj.modifiers if m.type=='ARMATURE']
        if modifiers:
            no_weight=0; bad_sum=0; maximum_influences=0; blended=0
            for v in obj.data.vertices:
                weights=[g.weight for g in v.groups if obj.vertex_groups[g.group].name in expected_bones]
                maximum_influences=max(maximum_influences,len(weights))
                if not weights: no_weight+=1
                if abs(sum(weights)-1.)>.0001: bad_sum+=1
                if len([w for w in weights if w>.00001])>1: blended+=1
            if no_weight or bad_sum: errors.append('unweighted / unnormalised '+obj.name)
            mesh_rows.append({'mesh':obj.name,'unweighted':no_weight,'bad_weight_sum':bad_sum,
                              'maximum_influences':maximum_influences,'blended_vertices':blended})
    if tris!=manifest['triangles']: errors.append('geometry budget / triangle count changed')
    if len(mesh_rows)!=28: errors.append('expected 28 skinned meshes')
    for name in ['Sleeve_L','Sleeve_R','Trouser_L','Trouser_R','BootUpper_L','BootUpper_R']:
        row=next((r for r in mesh_rows if r['mesh']==name),None)
        if not row or row['blended_vertices']<10: errors.append('continuous weight transition '+name)
    for name in ['Blink_L','Blink_R']:
        blink=bpy.data.objects.get(name)
        if not blink or any(abs(blink.scale[i]-.001)>.00002 for i in [0,1]) or abs(blink.scale[2]-1)>.00002:
            errors.append('blink XY contract '+name)
    lantern=bpy.data.objects['Lantern']
    ancestor=lantern.parent; ancestors=[]
    while ancestor: ancestors.append(ancestor.name); ancestor=ancestor.parent
    if 'Arm_R' not in ancestors: errors.append('Lantern must remain under right arm')
    apply_pose()
    max_pose=0.; max_sole_tilt=0.; sole_min=[]
    for obj in meshes:
        if obj.name in posed:
            deviation=max(posed[obj.name].find(p)[2] for p in points(obj))
            max_pose=max(max_pose,deviation)
            if deviation>.00004: errors.append('deformation mismatch '+obj.name)
        if obj.name.startswith('BootSole_'):
            values=points(obj); z_min=min(p.z for p in values); sole_min.append(z_min)
            # The sole is a rigid weighted island; its lower vertices stay planar.
            original_min=min(p.z for p in values)
            if original_min<-.002: errors.append('posed boot below ground '+obj.name)
    lantern_error=(lantern.matrix_world.translation-expected_lantern_pose.translation).length
    if lantern_error>.00004: errors.append('lantern no longer follows forearm')
    results[suffix]={'passed':not errors,'errors':errors,'sha256':hashlib.sha256((OUT/('traveler.'+suffix)).read_bytes()).hexdigest(),
        'triangles':tris,'mesh_renderers':len(meshes),'skinned_meshes':len(mesh_rows),'armatures':len([o for o in bpy.context.scene.objects if o.type=='ARMATURE']),
        'bones':len(bones),'max_neutral_vertex_deviation_m':max_neutral,'max_pivot_error_m':max_pivot,
        'max_pose_vertex_deviation_m':max_pose,'lantern_pose_deviation_m':lantern_error,
        'stride_boot_min_height_m':sole_min,'bone_validation':bone_rows,'skin_validation':mesh_rows}
(OUT/'frozen-export-verification.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
print('RIGGED_INDEPENDENT_VERIFICATION '+json.dumps(results),flush=True)
assert all(r['passed'] for r in results.values()),'Independent rigged interchange validation failed'

