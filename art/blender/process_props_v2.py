"""Clean up the user's Tripo v2 models for Unity.

  blender --background --factory-startup --python art/blender/process_props_v2.py -- [id,id,...]

Input : art/incoming/tripo-v2-2026-10-22/tripo_convert_<uuid>.glb (mapping below, identified from
        rendered thumbnails against art/design/v2/借光岛_第二版_生图与Tripo提示词.md)
Output: art/generated/props-v2/<id>/<id>.fbx + <id>_albedo.jpg (+ _normal.png), preview.png,
        and manifest.json; FBX + textures are copied to GameProject/Assets/JieGuang/Props/<id>/.

Each model is decimated to its triangle budget, scaled to real size (metres), its pivot put
at the bottom centre, and its textures limited to 2048 px.
"""
import bpy, sys, os, json, shutil, hashlib
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'art', 'incoming', 'tripo-v2-2026-10-22')
OUT = os.path.join(ROOT, 'art', 'generated', 'props-v2')
UNITY = os.path.join(ROOT, 'GameProject', 'Assets', 'JieGuang', 'Props')

# id: (source uuid prefix, size metres, 'h' = height | 'max' = largest dimension, triangle budget, texture px)
ASSETS = {
    'A01_grandma_house':  ('299ef313', 5.5, 'h', 16000, 2048),
    'A02_desk_set':       ('dfebad59', 1.2, 'max', 5000, 1024),
    'A03_golden_tree':    ('c7000543', 7.0, 'h', 30000, 2048),
    'A04_first_flower':   ('40cb8edc', 0.28, 'max', 3000, 1024),
    'A05_lamp_post':      ('2866ae60', 3.4, 'h', 3000, 1024),
    'A06_lamp_head':      ('b205d846', 0.6, 'max', 4000, 1024),
    'A07_shade_wide':     ('319c76b9', 0.36, 'max', 1500, 512),
    'A07_shade_narrow':   ('127acfc2', 0.45, 'max', 1500, 512),
    'A08_bench':          ('50647509', 1.8, 'max', 4000, 1024),
    'A09_boulder':        ('56ce80d0', 1.8, 'max', 4000, 1024),
    'A10_armillary':      ('7e10203d', 3.0, 'max', 12000, 2048),
    'A11_crescent':       ('e04fa7ff', 2.0, 'h', 4000, 1024),
    'A12_pier_segment':   ('5df8f2a5', 3.0, 'max', 3000, 1024),
    'A13_pier_end':       ('344329a3', 4.0, 'max', 5000, 1024),
    'A14_flagpole':       ('f0bb4ae6', 5.5, 'h', 2500, 1024),
    'A16_harbor_lantern': ('aede95ca', 0.6, 'h', 3000, 1024),
    'B01_lantern':        ('9a552b1b', 0.3, 'h', 3000, 1024),
    'B02_light_fruit':    ('7e61a664', 0.08, 'max', 800, 512),
    'B03_firefly_letter': ('ca73729e', 0.15, 'max', 1500, 512),
    'B04_cane':           ('eec2d603', 1.1, 'max', 1000, 512),
    'C01_light_ship':     ('c72dc2a3', 7.0, 'max', 15000, 2048),
    'C02_rowboat':        ('daaa44a5', 3.2, 'max', 5000, 1024),
    'C03_house_teal':     ('193f5a99', 4.5, 'max', 8000, 1024),
    'C04_house_ochre':    ('1747daa6', 5.0, 'h', 8000, 1024),
    'C05_house_slate':    ('05c45125', 5.0, 'max', 8000, 1024),
    'C06_well':           ('52efb8f7', 2.4, 'h', 4000, 1024),
    'C07_laundry':        ('9bd12163', 4.0, 'max', 3000, 1024),
    'C08_village_tree':   ('48c3ca59', 8.0, 'h', 20000, 2048),
    'D01_tree_tall':      ('63850bf4', 6.0, 'h', 12000, 1024),
    'D02_tree_round':     ('1a44fe4c', 4.5, 'h', 12000, 1024),
    'D03_tree_rock':      ('aecd4846', 5.0, 'h', 14000, 1024),
    'D04_sapling':        ('187654d4', 1.2, 'h', 2500, 1024),
    'D05_rocks_low':      ('7ef47e9e', 3.0, 'max', 5000, 1024),
    'D06_rocks_peak':     ('33498d3f', 3.5, 'h', 5000, 1024),
    'D07_rock_table':     ('ae455962', 4.0, 'max', 4000, 1024),
    'D08_rock_arch':      ('a70fc732', 6.0, 'max', 8000, 1024),
    'D09_rock_pillar':    ('3b7c37e7', 5.0, 'h', 4000, 1024),
    'D10_reef':           ('e03e6421', 2.0, 'max', 2500, 1024),
}


def tris(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


def process(aid):
    uuid, size, mode, budget, texpx = ASSETS[aid]
    src = [f for f in os.listdir(SRC) if uuid in f][0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, src))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in bpy.context.scene.objects:
        o.select_set(o.type == 'MESH')
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.context.scene.objects):
        if o != obj:
            bpy.data.objects.remove(o, do_unlink=True)
    before = tris([obj])
    # merge coincident vertices from the reconstruction, then collapse to budget
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    if tris([obj]) > budget:
        m = obj.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = budget / tris([obj])
        m.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    after = tris([obj])
    # scale to real size, pivot at bottom centre
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector([min(v[i] for v in bb) for i in range(3)])
    mx = Vector([max(v[i] for v in bb) for i in range(3)])
    dims = mx - mn
    ref = dims.z if mode == 'h' else max(dims)
    s = size / ref
    obj.data.transform(Matrix.Translation(Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))))
    obj.data.transform(Matrix.Scale(s, 4))
    obj.data.update()
    obj.name = aid
    od = os.path.join(OUT, aid)
    os.makedirs(od, exist_ok=True)
    # textures: keep base colour (+ normal when present) as files beside the FBX
    texinfo = {}
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        mat.name = aid + '_mat'
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is None:
            continue
        for socket, suffix, fmt in (('Base Color', 'albedo', 'JPEG'), ('Normal', 'normal', 'PNG')):
            link = bsdf.inputs[socket].links[0] if bsdf.inputs[socket].links else None
            node = link.from_node if link else None
            while node is not None and node.type != 'TEX_IMAGE':
                ins = [i for i in node.inputs if i.links]
                node = ins[0].links[0].from_node if ins else None
            if node is None or node.image is None:
                continue
            img = node.image
            if max(img.size) > texpx:
                img.scale(texpx, texpx)
            path = os.path.join(od, '%s_%s.%s' % (aid, suffix, 'jpg' if fmt == 'JPEG' else 'png'))
            img.filepath_raw = path
            img.file_format = fmt
            bpy.context.scene.render.image_settings.quality = 90
            img.save()
            texinfo[suffix] = os.path.basename(path)
    fbx = os.path.join(od, aid + '.fbx')
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', path_mode='STRIP', mesh_smooth_type='FACE')
    # preview
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x = sc.render.resolution_y = 360
    sc.world = bpy.data.worlds.new('w')
    sc.world.color = (0.5, 0.5, 0.53)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam)
    d2 = obj.dimensions
    r = max(d2) * 1.1
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = r
    dirv = Vector((1, -1.3, 0.8)).normalized()
    cam.location = Vector((0, 0, d2.z / 2)) + dirv * r * 3
    cam.rotation_euler = (-dirv).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = r * 10
    sc.camera = cam
    sc.render.filepath = os.path.join(od, 'preview.png')
    bpy.ops.render.render(write_still=True)
    dst = os.path.join(UNITY, aid)
    os.makedirs(dst, exist_ok=True)
    shutil.copy2(fbx, dst)
    for t in texinfo.values():
        shutil.copy2(os.path.join(od, t), dst)
    srcpath = os.path.join(SRC, src)
    rec = dict(id=aid, source=os.path.relpath(srcpath, ROOT), source_sha256=hashlib.sha256(open(srcpath, 'rb').read()).hexdigest(),
               tris_before=before, tris_after=after, size_m=[round(v * s, 3) for v in dims], textures=texinfo, materials=len(obj.data.materials))
    json.dump(rec, open(os.path.join(od, 'record.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('PROP', json.dumps(rec, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    args = [a for a in sys.argv[sys.argv.index('--') + 1:] if not a.startswith('--')] if '--' in sys.argv else []
    ids = args[0].split(',') if args else list(ASSETS)
    if '--reverse' in sys.argv:
        ids = ids[::-1]
    for aid in ids:
        if os.path.exists(os.path.join(OUT, aid, 'record.json')) and '--force' not in sys.argv:
            print('SKIP', aid, flush=True)
            continue
        try:
            process(aid)
        except Exception as e:
            print('FAIL', aid, repr(e), flush=True)
