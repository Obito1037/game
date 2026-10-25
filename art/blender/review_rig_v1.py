"""Review renders and deformation metrics for characters-v1 rigs.

  blender --background --factory-startup --python art/blender/review_rig_v1.py -- <char_id|all> [poses]

Writes art/verification/characters-v1/<char_id>/: rest_front/side with joint markers,
pose_<name>_<view>.png, and metrics.json (edge stretch per pose and region).
"""
import bpy, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GEN = os.path.join(ROOT, 'art', 'generated', 'characters-v1')
VER = os.path.join(ROOT, 'art', 'verification', 'characters-v1')
P = 'mixamorig:'
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# (bone, world axis, degrees); right side is mirrored automatically for Left* entries
POSES = {
    'raise_arms': [('LeftArm', Y, -70), ('LeftForeArm', Y, -25)],
    'arms_down': [('LeftArm', Y, 70), ('LeftForeArm', X, -20)],
    # rotation about +X by a negative angle swings a down-pointing limb forward (-Y)
    'bend_legs': [('LeftUpLeg', X, -75), ('LeftLeg', X, 105), ('LeftFoot', X, -30),
                  ('LeftArm', Z, 60), ('Spine', X, 15)],
    'turn_torso': [('Spine', Z, 22), ('Spine1', Z, 22), ('Spine2', Z, 18), ('Neck', Z, 15),
                   ('LeftArm', Y, 65)],
    'walk_stride': [('LeftUpLeg', X, -35), ('LeftLeg', X, 30), ('RightUpLeg', X, 25), ('RightLeg', X, 45),
                    ('LeftArm', Y, 70), ('LeftArm', X, 20), ('RightArm', X, -20)],
    'sit': [('LeftUpLeg', X, -90), ('LeftLeg', X, 90), ('LeftArm', Y, 70), ('LeftForeArm', X, -40)],
}
MIRROR_AXIS_SIGN = {'X': (1, -1, -1)}  # mirror across X: rotation about Y and Z flips sign


def mirrored(entries):
    out = []
    for b, ax, deg in entries:
        out.append((b, ax, deg))
        if b.startswith('Left'):
            # mirror across YZ plane: axis X keeps angle, axes Y/Z flip angle
            sign = 1 if ax == X else -1
            out.append(('Right' + b[4:], ax, deg * sign))
    return out


def rotate_world(arm, bname, axis, deg):
    pb = arm.pose.bones[P + bname]
    bpy.context.view_layer.update()
    head = arm.matrix_world @ pb.head
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()


def apply_pose(arm, name):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    order = [b.name[len(P):] for b in arm.data.bones]  # parents before children
    ent = mirrored(POSES[name])
    ent.sort(key=lambda e: order.index(e[0]))
    for b, ax, deg in ent:
        rotate_world(arm, b, ax, deg)
    if name in ('bend_legs', 'sit'):
        # keep feet on the floor for the squat
        dg = bpy.context.evaluated_depsgraph_get()
        body = bpy.data.objects['Body']
        ev = body.evaluated_get(dg)
        zmin = min((body.matrix_world @ v.co).z for v in ev.data.vertices)
        arm.pose.bones[P + 'Hips'].location = (0, 0, 0)
        hb = arm.pose.bones[P + 'Hips']
        hb.matrix = Matrix.Translation((0, 0, -zmin)) @ hb.matrix
        bpy.context.view_layer.update()


def edge_stretch(body, rest_len, edges):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    co = np.array([v.co[:] for v in ev.data.vertices])
    l = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
    return l / np.maximum(rest_len, 1e-6), co


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x = 800
    sc.render.resolution_y = 1000
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('w') if not sc.world else sc.world
    sc.world = w
    w.color = (0.75, 0.75, 0.75)


def camera(name, loc, target, ortho):
    cam = bpy.data.cameras.new(name)
    cam.type = 'ORTHO'
    cam.ortho_scale = ortho
    o = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o


def markers(arm):
    mat = bpy.data.materials.new('marker')
    mat.diffuse_color = (1, 0.05, 0.05, 1)
    objs = []
    for b in arm.data.bones:
        h = arm.matrix_world @ b.head_local
        t = arm.matrix_world @ b.tail_local
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.012, location=h, segments=10, ring_count=6)
        s = bpy.context.object
        s.data.materials.append(mat)
        objs.append(s)
        d = t - h
        bpy.ops.mesh.primitive_cylinder_add(radius=0.004, depth=d.length, location=(h + t) / 2, vertices=6)
        c = bpy.context.object
        c.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        c.data.materials.append(mat)
        objs.append(c)
    return objs


def render(path, cam):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def region_of(co, lm):
    """Coarse body region label per rest vertex for reporting."""
    labels = np.full(len(co), 'torso', dtype=object)
    ax = abs(lm['LeftArm'][0])
    labels[np.abs(co[:, 0]) > ax] = 'arm'
    labels[(co[:, 2] < lm['LeftUpLeg'][2]) & (np.abs(co[:, 0]) <= ax)] = 'leg'
    labels[co[:, 2] > lm['Neck'][2]] = 'head'
    return labels


def review(cid, poses):
    blend = os.path.join(GEN, cid, cid + '.blend')
    bpy.ops.wm.open_mainfile(filepath=blend)
    lm = json.load(open(os.path.join(GEN, cid, 'landmarks.json'), encoding='utf-8'))['landmarks_m']
    arm = bpy.data.objects['Armature']
    body = bpy.data.objects['Body']
    od = os.path.join(VER, cid)
    os.makedirs(od, exist_ok=True)
    setup_render()
    h = max((body.matrix_world @ Vector(c)).z for c in body.bound_box)
    span = max((body.matrix_world @ Vector(c)).x for c in body.bound_box) * 2
    o = max(h, span) * 1.08
    cf = camera('front', (0, -6, h / 2), (0, 0, h / 2), o)
    cs = camera('side', (6, 0, h / 2), (0, 0, h / 2), o)
    c34 = camera('q34', (-4.2, -4.2, h * 0.75), (0, 0, h * 0.45), o)
    me = body.data
    edges = np.array([e.vertices[:] for e in me.edges])
    rest = np.array([(body.matrix_world @ v.co)[:] for v in me.vertices])
    rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    regions = region_of(rest, lm)
    metrics = {}
    if 'rest' in poses:
        sh = bpy.context.scene.display.shading
        sh.show_xray, sh.xray_alpha = True, 0.55
        mk = markers(arm)
        render(os.path.join(od, 'rest_front.png'), cf)
        render(os.path.join(od, 'rest_side.png'), cs)
        for m in mk:
            bpy.data.objects.remove(m, do_unlink=True)
        sh.show_xray = False
    for name in poses:
        if name == 'rest':
            continue
        apply_pose(arm, name)
        ratio, co = edge_stretch(body, rest_len, edges)
        vert_r = np.ones(len(rest))
        np.maximum.at(vert_r, edges[:, 0], ratio)
        np.maximum.at(vert_r, edges[:, 1], ratio)
        vmin = np.ones(len(rest))
        np.minimum.at(vmin, edges[:, 0], ratio)
        np.minimum.at(vmin, edges[:, 1], ratio)
        m = {'max_stretch': round(float(ratio.max()), 3), 'p999_stretch': round(float(np.percentile(ratio, 99.9)), 3),
             'min_compress': round(float(ratio.min()), 3), 'regions': {}}
        for r in ('head', 'torso', 'arm', 'leg'):
            sel = regions == r
            m['regions'][r] = {'stretched_gt1.6': int((vert_r[sel] > 1.6).sum()),
                               'compressed_lt0.4': int((vmin[sel] < 0.4).sum()), 'verts': int(sel.sum())}
        worst = np.argsort(-vert_r)[:5]
        m['worst_verts'] = [[int(i), [round(float(c), 3) for c in rest[i]], round(float(vert_r[i]), 2)] for i in worst]
        metrics[name] = m
        render(os.path.join(od, 'pose_%s_front.png' % name), cf)
        render(os.path.join(od, 'pose_%s_q34.png' % name), c34)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    if metrics:
        with open(os.path.join(od, 'metrics.json'), 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=1)
    print('REVIEWED', cid, json.dumps({k: (v['max_stretch'], v['p999_stretch']) for k, v in metrics.items()}))


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    ids = ['xiaodenglong', 'aying', 'postman', 'abo', 'dengbo'] if a[0] == 'all' else a[0].split(',')
    poses = a[1].split(',') if len(a) > 1 else ['rest'] + list(POSES)
    for cid in ids:
        review(cid, poses)
