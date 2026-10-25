"""Export rigged characters-v1 to FBX for Unity (Humanoid, Mixamo bone names).

  blender --background --factory-startup --python art/blender/export_characters_v1.py -- <char_id|all>

Writes art/generated/characters-v1/<id>/<id>.fbx + <id>_albedo.jpg (2048) and copies both to
GameProject/Assets/JieGuang/Characters/<id>/.
"""
import bpy, sys, os, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GEN = os.path.join(ROOT, 'art', 'generated', 'characters-v1')
UNITY = os.path.join(ROOT, 'GameProject', 'Assets', 'JieGuang', 'Characters')
IDS = ['xiaodenglong', 'aying', 'postman', 'abo', 'dengbo']


def export(cid):
    od = os.path.join(GEN, cid)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(od, cid + '.blend'))
    body = bpy.data.objects['Body']
    arm = bpy.data.objects['Armature']
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    tex = os.path.join(od, cid + '_albedo.jpg')
    for img in bpy.data.images:
        if img.source != 'FILE':
            continue
        if max(img.size) > 2048:
            img.scale(2048, 2048)
        img.filepath_raw = tex
        img.file_format = 'JPEG'
        bpy.context.scene.render.image_settings.quality = 92
        img.save()
        img.unpack(method='REMOVE') if img.packed_file else None
        img.filepath = tex
        img.reload()
    mat = body.data.materials[0]
    mat.name = cid + '_mat'
    arm.name = cid
    body.name = cid + '_body'
    fbx = os.path.join(od, cid + '.fbx')
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    body.select_set(True)
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
                             add_leaf_bones=False, bake_anim=False, use_armature_deform_only=True,
                             path_mode='STRIP', mesh_smooth_type='FACE', use_mesh_modifiers=False)
    dst = os.path.join(UNITY, cid)
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(fbx, dst)
    shutil.copy2(tex, dst)
    print('EXPORTED', cid, os.path.getsize(fbx), os.path.getsize(tex))


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
    for cid in (IDS if a == 'all' else a.split(',')):
        export(cid)
