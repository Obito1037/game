"""Rig and skin the five Tripo characters of 借光岛 with a Mixamo-named skeleton.

Run:
  blender --background --factory-startup --python art/blender/rig_characters_v1.py -- <char_id|all>

Input : art/incoming/tripo-2026-10-22/zips/tripo_convert_<uuid>/*.fbx (T-pose, single textured mesh)
Output: art/generated/characters-v1/<char_id>/<char_id>.blend|.fbx|landmarks.json

Joint landmarks are measured from mesh cross-sections (normalised height 1.0),
then corrected by per-character overrides that were checked against front/side
renders. Skin weights come from bone-heat on a watertight voxel proxy, transferred
back to the original mesh, then cleaned per side and per region.
"""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, 'art', 'incoming', 'tripo-2026-10-22', 'zips')
OUT = os.path.join(ROOT, 'art', 'generated', 'characters-v1')

# height in metres, source uuid prefix, landmark overrides (normalised units)
CHARS = {
    'xiaodenglong': dict(uuid='003f3772', height=1.45, name='小灯笼'),
    'aying':        dict(uuid='8f9864d8', height=1.50, name='阿萤'),
    'postman':      dict(uuid='63e35b8e', height=1.66, name='邮差爷爷'),
    'abo':          dict(uuid='3a3078e0', height=1.52, name='阿婆', skirt=True),
    'dengbo':       dict(uuid='eccb5bae', height=1.72, name='灯伯', coat=True),
}
OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), 'rig_characters_v1_overrides.json')

P = 'mixamorig:'


def load_overrides():
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}


def import_character(uuid):
    folder = [d for d in os.listdir(SRC) if uuid in d][0]
    path = os.path.join(SRC, folder, folder + '.fbx')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    mesh = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    # Tripo export faces +X with Z up: turn to Blender's -Y front, feet on the floor.
    mesh.matrix_world = Matrix.Rotation(-math.pi / 2, 4, 'Z') @ mesh.matrix_world
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    V = np.array([v.co[:] for v in mesh.data.vertices])
    off = Vector((-(V[:, 0].max() + V[:, 0].min()) / 2, -(V[:, 1].max() + V[:, 1].min()) / 2, -V[:, 2].min()))
    h = V[:, 2].max() - V[:, 2].min()
    mesh.data.transform(Matrix.Scale(1.0 / h, 4) @ Matrix.Translation(off))
    mesh.data.update()
    mesh.name = 'Body'
    return mesh, path


def slice_pts(V, axis, value, eps, mask=None):
    m = np.abs(V[:, axis] - value) < eps
    if mask is not None:
        m &= mask
    return V[m]


def mid(a):
    return (a.min() + a.max()) / 2


def measure(V, ov):
    """Return dict of joint positions (normalised) for the left side + spine."""
    L = {}
    xm = V[:, 0].max()
    arm = V[V[:, 0] > 0.75 * xm]
    za = float(np.median(arm[:, 2]))
    band = np.abs(V[:, 2] - za) < 0.1

    # armpit: first x (outward) where the slice no longer reaches down into the torso
    armpit = 0.12
    for x in np.arange(0.05, xm * 0.8, 0.005):
        s = slice_pts(V, 0, x, 0.004, band)
        if len(s) and s[:, 2].min() > za - 0.065:
            armpit = x
            break
    sh_x = ov.get('shoulder_x', armpit - 0.025)
    wr_x = ov.get('wrist_x', sh_x + 0.74 * (xm - sh_x))
    el_x = ov.get('elbow_x', (sh_x + wr_x) / 2)

    def arm_center(x):
        s = slice_pts(V, 0, x, 0.006, band)
        return Vector((x, mid(s[:, 1]), mid(s[:, 2])))

    L['LeftArm'] = arm_center(sh_x)
    L['LeftForeArm'] = arm_center(el_x)
    L['LeftForeArm'].y += 0.004  # elbow sits slightly behind the limb centre
    L['LeftHand'] = arm_center(wr_x)
    L['LeftHandEnd'] = arm_center(xm - 0.01)
    L['LeftShoulder'] = Vector((0.025, L['LeftArm'].y, L['LeftArm'].z + 0.005))

    # neck: narrowest torso slice above the shoulder line
    best, nz = 9, za + 0.06
    for z in np.arange(za + 0.02, za + 0.16, 0.005):
        s = slice_pts(V, 2, z, 0.003, np.abs(V[:, 0]) < 0.2)
        if len(s):
            w = s[:, 0].max() - s[:, 0].min()
            if w < best:
                best, nz = w, z
    neck_z = ov.get('neck_z', za + 0.03)
    head_z = ov.get('head_z', nz + 0.01)
    top = V[:, 2].max()

    def torso_y(z, half=0.04):
        s = slice_pts(V, 2, z, 0.006, np.abs(V[:, 0]) < half)
        return mid(s[:, 1]) if len(s) else 0.0

    hip_z = ov.get('hip_z', 0.60 * za)
    # feet
    feet = V[V[:, 2] < 0.035]
    fl = feet[feet[:, 0] > 0]
    foot_x = mid(fl[:, 0])
    toe_y, heel_y = fl[:, 1].min(), fl[:, 1].max()
    ankle_z = ov.get('ankle_z', 0.055)
    knee_z = ov.get('knee_z', ankle_z + 0.47 * (hip_z - ankle_z))
    leg_x_hip = ov.get('hip_x', foot_x * 0.85)

    def leg_center(z, x_guess, depth_only=False):
        s = slice_pts(V, 2, z, 0.006, np.abs(V[:, 0] - x_guess) < 0.045)
        if not len(s):
            return Vector((x_guess, 0.0, z))
        return Vector((x_guess if depth_only else mid(s[:, 0]), mid(s[:, 1]), z))

    L['Hips'] = Vector((0, torso_y(hip_z + 0.03, 0.08), hip_z + 0.03))
    L['LeftUpLeg'] = Vector((leg_x_hip, L['Hips'].y, hip_z))
    k = leg_center(knee_z, (leg_x_hip + foot_x) / 2, depth_only=ov.get('skirt', False))
    k.x = ov.get('knee_x', (leg_x_hip + foot_x) / 2)
    k.y -= 0.004  # knee slightly forward
    L['LeftLeg'] = k
    a = Vector((foot_x, heel_y - 0.30 * (heel_y - toe_y), ankle_z))
    L['LeftFoot'] = a
    L['LeftToeBase'] = Vector((foot_x, toe_y + 0.32 * (heel_y - toe_y), 0.018))
    L['LeftToeEnd'] = Vector((foot_x, toe_y + 0.01, 0.018))

    spine_top = neck_z
    hz = L['Hips'].z
    for name, f in (('Spine', 0.12), ('Spine1', 0.42), ('Spine2', 0.70)):
        z = hz + f * (spine_top - hz)
        L[name] = Vector((0, torso_y(z), z))
    L['Neck'] = Vector((0, torso_y(neck_z, 0.03), neck_z))
    L['Head'] = Vector((0, torso_y(head_z, 0.03), head_z))
    L['HeadTop_End'] = Vector((0, L['Head'].y, top))
    for k2, v in ov.get('offsets', {}).items():
        L[k2] = L[k2] + Vector(v)
    # limb radii for the skin "tubes"
    s = slice_pts(V, 0, el_x, 0.006, band)
    arm_r = max(s[:, 2].max() - s[:, 2].min(), s[:, 1].max() - s[:, 1].min()) / 2
    s = slice_pts(V, 2, L['LeftLeg'].z, 0.006, np.abs(V[:, 0] - L['LeftLeg'].x) < 0.07)
    leg_r = (s[:, 1].max() - s[:, 1].min()) / 2 if len(s) else 0.05
    L['_armpit'] = float(ov.get('armpit_x', armpit))
    L['_arm_r'] = float(ov.get('arm_r', arm_r))
    L['_leg_r'] = float(ov.get('leg_r', leg_r))
    return L, dict(za=za, armpit=armpit, xm=xm, neck_narrow=nz, arm_r=L['_arm_r'], leg_r=L['_leg_r'])


def mirror(v):
    return Vector((-v.x, v.y, v.z))


def build_armature(L):
    arm_data = bpy.data.armatures.new('Armature')
    arm = bpy.data.objects.new('Armature', arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    def bone(name, head, tail, parent=None, roll_up=Vector((0, -1, 0))):
        b = eb.new(P + name)
        b.head, b.tail = head, tail
        b.align_roll(roll_up)
        if parent:
            b.parent = eb[P + parent]
            b.use_connect = (b.parent.tail - head).length < 1e-5
        return b

    up = Vector((0, 0, 1))
    bone('Hips', L['Hips'], L['Spine'], roll_up=Vector((0, -1, 0)))
    bone('Spine', L['Spine'], L['Spine1'], 'Hips')
    bone('Spine1', L['Spine1'], L['Spine2'], 'Spine')
    bone('Spine2', L['Spine2'], L['Neck'], 'Spine1')
    bone('Neck', L['Neck'], L['Head'], 'Spine2')
    bone('Head', L['Head'], L['HeadTop_End'], 'Neck')
    for side, f in (('Left', lambda v: v), ('Right', mirror)):
        bone(side + 'Shoulder', f(L['LeftShoulder']), f(L['LeftArm']), 'Spine2', roll_up=up)
        bone(side + 'Arm', f(L['LeftArm']), f(L['LeftForeArm']), side + 'Shoulder', roll_up=up)
        bone(side + 'ForeArm', f(L['LeftForeArm']), f(L['LeftHand']), side + 'Arm', roll_up=up)
        bone(side + 'Hand', f(L['LeftHand']), f(L['LeftHandEnd']), side + 'ForeArm', roll_up=up)
        bone(side + 'UpLeg', f(L['LeftUpLeg']), f(L['LeftLeg']), 'Hips')
        bone(side + 'Leg', f(L['LeftLeg']), f(L['LeftFoot']), side + 'UpLeg')
        bone(side + 'Foot', f(L['LeftFoot']), f(L['LeftToeBase']), side + 'Leg', roll_up=up)
        bone(side + 'ToeBase', f(L['LeftToeBase']), f(L['LeftToeEnd']), side + 'Foot', roll_up=up)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def make_proxy(mesh, voxel):
    proxy = mesh.copy()
    proxy.data = mesh.data.copy()
    proxy.name = 'Proxy'
    bpy.context.scene.collection.objects.link(proxy)
    proxy.data.materials.clear()
    mod = proxy.modifiers.new('remesh', 'REMESH')
    mod.mode, mod.voxel_size, mod.use_smooth_shade = 'VOXEL', voxel, True
    dec = proxy.modifiers.new('dec', 'DECIMATE')
    dec.ratio = 0.35
    bpy.context.view_layer.objects.active = proxy
    for m in list(proxy.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return proxy


def heat_weights(proxy, arm):
    # Bone heat loses precision on a 1-unit-tall body; solve at 10x and scale back.
    def rescale(f):
        for o in (proxy, arm):
            o.scale = (f, f, f)
        bpy.ops.object.select_all(action='DESELECT')
        proxy.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    rescale(10.0)
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    proxy.parent = None
    proxy.modifiers.clear()
    rescale(0.1)
    return len(proxy.vertex_groups)


def neighbour_table(V, radius, cap=24):
    from mathutils import kdtree
    kd = kdtree.KDTree(len(V))
    for i, c in enumerate(V):
        kd.insert(c, i)
    kd.balance()
    nb = np.full((len(V), cap), -1, dtype=np.int64)
    for i, c in enumerate(V):
        hits = kd.find_range(c, radius)
        hits.sort(key=lambda h: h[2])
        ids = [h[1] for h in hits[:cap]]
        nb[i, :len(ids)] = ids
    return nb


def seg_dist(V, a, b):
    a, b = np.array(a), np.array(b)
    d = b - a
    t = np.clip(((V - a) @ d) / max(d @ d, 1e-12), 0, 1)
    return np.linalg.norm(V - (a + t[:, None] * d), axis=1)


def distance_weights(mesh, arm, L, ov):
    """Bone-segment inverse-distance weights with anatomical gating, then spatial smoothing.

    Used instead of bone heat: Tripo meshes are open, multi-shell surfaces on which
    bone heat finds no solution at all.
    """
    V = np.array([v.co[:] for v in mesh.data.vertices])
    bones = [(b.name, np.array(b.head_local), np.array(b.tail_local)) for b in arm.data.bones]
    names = [b[0] for b in bones]
    D = np.stack([seg_dist(V, h, t) for _, h, t in bones], 1)
    x, z = V[:, 0], V[:, 2]
    za = L['LeftArm'].z
    ax = abs(L['LeftArm'].x)
    armpit = L['_armpit']
    hip_z = L['LeftUpLeg'].z
    col = {n[len(P):]: j for j, n in enumerate(names)}

    def chain_dist(parts):
        return np.min(np.stack([D[:, col[p]] for p in parts], 1), 1)

    # Soft "limb tubes": only geometry within a limb's measured radius follows it.
    tube = {}
    for side, s in (('Left', 1), ('Right', -1)):
        da = chain_dist([side + 'Arm', side + 'ForeArm', side + 'Hand'])
        r = L['_arm_r'] * ov.get('arm_tube', 1.35)
        tube[side + 'arm'] = smoothstep(r + 0.03, r, da)
        dl = chain_dist([side + 'UpLeg', side + 'Leg', side + 'Foot', side + 'ToeBase'])
        r = L['_leg_r'] * ov.get('leg_tube', 1.35)
        tube[side + 'leg'] = smoothstep(r + 0.035, r, dl)
    allow = np.ones_like(D)
    for j, n in enumerate(names):
        p = n[len(P):]
        side = 1 if p.startswith('Left') else -1 if p.startswith('Right') else 0
        sname = 'Left' if side == 1 else 'Right'
        part = p[4:] if side == 1 else p[5:] if side == -1 else p
        if part in ('Arm', 'ForeArm', 'Hand'):
            allow[:, j] = (side * x > ax - 0.03) * tube[sname + 'arm']
        elif part == 'Shoulder':
            allow[:, j] = (side * x > 0.0) & (z > za - 0.09) & (side * x < L['LeftForeArm'].x)
        elif part in ('UpLeg', 'Leg', 'Foot', 'ToeBase'):
            allow[:, j] = (side * x > (-0.02 if part == 'UpLeg' else 0.0)) * (z < hip_z + 0.06) * tube[sname + 'leg']
        elif part in ('Neck', 'Head'):
            allow[:, j] = (z > za - 0.02) & (np.abs(x) < armpit + 0.02)
        elif part == 'Hips':
            # anything hanging below the arms (bags, wide coats, shawls) is torso
            allow[:, j] = (np.abs(x) < armpit + 0.03) | (z < za - 0.12)
        else:  # Spine*
            allow[:, j] = ((np.abs(x) < armpit + 0.03) | (z < za - 0.12)) & (z > hip_z - 0.03)
    eps = ov.get('dist_eps', 0.006)
    k = ov.get('dist_power', 4.0)
    W = allow / (D + eps) ** k
    W /= np.maximum(W.sum(1, keepdims=True), 1e-12)
    nb = neighbour_table(V, ov.get('smooth_radius', 0.018))
    valid = nb >= 0
    for _ in range(ov.get('smooth_iter', 4)):
        acc = np.zeros_like(W)
        for c in range(nb.shape[1]):
            m = valid[:, c]
            acc[m] += W[nb[m, c]]
        W = 0.5 * W + 0.5 * acc / np.maximum(valid.sum(1, keepdims=True), 1)
        W = W * (allow > 0)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-12)
    for n in names:
        mesh.vertex_groups.new(name=n)
    write_weights(mesh, names, W)


def transfer(mesh, proxy):
    for b in proxy.vertex_groups:
        if b.name not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=b.name)
    dt = mesh.modifiers.new('dt', 'DATA_TRANSFER')
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'
    dt.layers_vgroup_select_dst = 'NAME'
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.modifier_apply(modifier='dt')


def weights_array(mesh):
    names = [g.name for g in mesh.vertex_groups]
    W = np.zeros((len(mesh.data.vertices), len(names)))
    for v in mesh.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def write_weights(mesh, names, W):
    for gi, n in enumerate(names):
        g = mesh.vertex_groups[n]
        g.remove(range(len(mesh.data.vertices)))
    for gi, n in enumerate(names):
        g = mesh.vertex_groups[n]
        col = W[:, gi]
        for idx in np.nonzero(col > 1e-4)[0]:
            g.add([int(idx)], float(col[idx]), 'REPLACE')


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def clean_weights(mesh, L, cfg):
    names, W = weights_array(mesh)
    V = np.array([v.co[:] for v in mesh.data.vertices])
    idx = {n: i for i, n in enumerate(names)}
    hip_z = L['LeftUpLeg'].z
    # 1. side separation: a vertex on one side may not follow the other side's limb.
    for side, sign in (('Left', 1), ('Right', -1)):
        wrong = sign * V[:, 0] < 0
        for part in ('UpLeg', 'Leg', 'Foot', 'ToeBase', 'Arm', 'ForeArm', 'Hand', 'Shoulder'):
            n = P + side + part
            if n not in idx:
                continue
            keep = np.ones(len(V))
            if part == 'UpLeg':
                # crotch/hem band blends across the centre line
                keep = np.where(wrong, smoothstep(-0.03, 0.0, sign * V[:, 0]), 1.0)
            else:
                keep = np.where(wrong, 0.0, 1.0)
            W[:, idx[n]] *= keep
    # 2. arms never drive anything below the armpit level on the torso
    za = L['LeftArm'].z
    for side in ('Left', 'Right'):
        for part in ('Arm', 'ForeArm', 'Hand'):
            n = P + side + part
            torso = (np.abs(V[:, 0]) < abs(L['LeftArm'].x) - 0.01) & (V[:, 2] < za - 0.05)
            W[torso, idx[n]] = 0
    # 3. head bones never reach the arms / lower torso
    for n in ('Head', 'Neck'):
        W[V[:, 2] < L['LeftArm'].z - 0.04, idx[P + n]] *= 0
    # 4. long skirt / coat hem: share the hem between hips and both thighs so the
    #    cloth does not tear down the middle when legs move.
    if cfg.get('skirt') or cfg.get('coat'):
        hem_top = hip_z - 0.02
        hem_bottom = cfg.get('hem_z', 0.08 if cfg.get('skirt') else 0.30)
        r_out = cfg.get('hem_r', 0.11)
        cloth = (V[:, 2] < hem_top) & (V[:, 2] > hem_bottom - 0.02)
        # distance from each leg's axis: vertices far from both leg tubes are cloth
        lx = L['LeftLeg'].x
        dl = np.hypot(V[:, 0] - lx, V[:, 1] - L['LeftLeg'].y)
        dr = np.hypot(V[:, 0] + lx, V[:, 1] - L['LeftLeg'].y)
        outer = smoothstep(0.035, 0.075, np.minimum(dl, dr))
        m = cloth & (outer > 0)
        hips_share = np.clip(outer * 0.65 * smoothstep(hem_bottom, hem_top, V[:, 2]) + 0.25 * outer, 0, 0.8)
        for i in np.nonzero(m)[0]:
            s = hips_share[i]
            total = W[i].sum()
            if total <= 0:
                continue
            lw = 0.5 + 0.5 * np.tanh(V[i, 0] / 0.04)  # left/right blend across centre
            W[i] *= (1 - s)
            leg_part = s * 0.55
            W[i, idx[P + 'Hips']] += s - leg_part
            W[i, idx[P + 'LeftUpLeg']] += leg_part * lw
            W[i, idx[P + 'RightUpLeg']] += leg_part * (1 - lw)
    # 5. jacket/coat hem around the hip joint follows the thighs part-way, so a raised
    #    thigh lifts the front hem instead of passing through it (sit, squat, stride).
    hips_y = L['Hips'].y
    band = (V[:, 2] < hip_z + cfg.get('hem_band_top', 0.08)) & (V[:, 2] > hip_z - cfg.get('hem_band_bottom', 0.12))
    band &= np.abs(V[:, 0]) < abs(L['LeftArm'].x) + 0.04
    f_z = smoothstep(hip_z + cfg.get('hem_band_top', 0.08), hip_z - 0.02, V[:, 2])
    front = smoothstep(hips_y + 0.01, hips_y - 0.035, V[:, 1])
    f = f_z * (cfg.get('hem_back', 0.25) + (cfg.get('hem_front', 0.6) - cfg.get('hem_back', 0.25)) * front)
    lw = 0.5 + 0.5 * np.tanh(V[:, 0] / 0.03)
    legs = W[:, [idx[P + n] for n in ('LeftUpLeg', 'RightUpLeg', 'LeftLeg', 'RightLeg')]].sum(1)
    sel = band & (legs < 0.5)
    for i in np.nonzero(sel)[0]:
        fi = f[i] * (1 - legs[i])
        W[i] *= (1 - fi)
        W[i, idx[P + 'LeftUpLeg']] += fi * lw[i]
        W[i, idx[P + 'RightUpLeg']] += fi * (1 - lw[i])
    # 6. limit to 4 influences and normalise
    order = np.argsort(-W, axis=1)
    mask = np.zeros_like(W, dtype=bool)
    rows = np.arange(len(W))[:, None]
    mask[rows, order[:, :4]] = True
    W = np.where(mask, W, 0)
    s = W.sum(1, keepdims=True)
    empty = s[:, 0] <= 1e-6
    W = np.where(s > 1e-6, W / np.maximum(s, 1e-9), W)
    # unweighted verts: nearest bone by distance (rare)
    if empty.any():
        W[empty, idx[P + 'Hips']] = 1.0
    write_weights(mesh, names, W)
    return int(empty.sum())


def smooth_weights(mesh, repeat):
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=repeat, expand=0.0)
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def rig(cid):
    cfg = dict(CHARS[cid])
    ov = load_overrides().get(cid, {})
    cfg.update({k: v for k, v in ov.items() if k in ('skirt', 'coat', 'hem_z', 'hem_r')})
    mesh, src = import_character(cfg['uuid'])
    V = np.array([v.co[:] for v in mesh.data.vertices])
    L, info = measure(V, dict(ov, skirt=cfg.get('skirt', False)))
    arm = build_armature(L)
    distance_weights(mesh, arm, L, ov)
    empty = clean_weights(mesh, L, cfg)
    smooth_weights(mesh, ov.get('smooth', 1))
    # parent mesh to armature with armature modifier
    mesh.parent = arm
    mod = mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    # scale to real height
    s = cfg['height']
    for o in (arm,):
        o.scale = (s, s, s)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # pack and save
    od = os.path.join(OUT, cid)
    os.makedirs(od, exist_ok=True)
    for img in bpy.data.images:
        if img.source == 'FILE':
            img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(od, cid + '.blend'))
    lm = {k: [round(c * s, 4) for c in v] for k, v in L.items() if not k.startswith('_')}
    with open(os.path.join(od, 'landmarks.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(char=cid, name=cfg['name'], source=os.path.relpath(src, ROOT), height_m=s,
                       measure_info=info, overrides=ov, unweighted_fallback=empty,
                       verts=len(mesh.data.vertices), tris=sum(len(p.vertices) - 2 for p in mesh.data.polygons),
                       landmarks_m=lm), f, ensure_ascii=False, indent=1)
    print('RIGGED', cid, 'verts', len(mesh.data.vertices), 'fallback', empty)


if __name__ == '__main__':
    arg = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
    for cid in (CHARS if arg == 'all' else arg.split(',')):
        rig(cid)
