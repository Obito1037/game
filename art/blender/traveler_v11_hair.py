"""Original layered hair candidate; pure Python, canonical unproportioned metres.

The caller owns Blender objects, the retained scalp, face/brows/lashes, weights,
materials and the v6 proportion transform. Front is -Y. This module neither
imports bpy nor reads/writes assets. It returns nine overlapping broad rooted
wedges and twenty-four subordinate surface ridges, not round tubes. This is a
new revision: rejected traveler_v10_hair.py remains frozen. The main paths now
follow the retained scalp ellipsoid, with side/back coverage below its cut edge.
The original dark hair material belongs on ``verts/faces``; the existing muted
hair-light material belongs on ``high_verts/high_faces``.  No yellow material.

All primary/secondary wedges are closed, positively wound volumes. Highlights
are intentionally open, outward-facing strips. They are not collision meshes.
This geometry has not been visually accepted: CPU/native views remain required.
"""

from math import sqrt, sin, cos, pi, isfinite


def _add(a, b):
    return tuple(a[k] + b[k] for k in range(3))


def _sub(a, b):
    return tuple(a[k] - b[k] for k in range(3))


def _mul(a, s):
    return tuple(v * s for v in a)


def _dot(a, b):
    return sum(a[k] * b[k] for k in range(3))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(a):
    length = sqrt(_dot(a, a))
    if length < 1e-12:
        raise ValueError('Undefined hair frame')
    return _mul(a, 1.0/length)


def _lerp(a, b, t):
    return _add(_mul(a, 1-t), _mul(b, t))


def _smooth(a, b, t):
    t = max(0.0, min(1.0, (t-a)/(b-a)))
    return t*t*(3-2*t)


def _bezier(points, t):
    a, b, c, d = points
    return tuple((1-t)**3*a[k] + 3*(1-t)**2*t*b[k] +
                 3*(1-t)*t*t*c[k] + t**3*d[k] for k in range(3))


def _tangent(curve, t):
    return _unit(_sub(curve(min(1.0, t+.0001)), curve(max(0.0, t-.0001))))


def _frame(curve, t):
    center = curve(t)
    tangent = _tangent(curve, t)
    # Ellipsoid-gradient outward direction, projected perpendicular to the path.
    radial = (center[0]/.128**2, (center[1]-.011)/.116**2, (center[2]-1.11)/.132**2)
    outward = _unit(_sub(radial, _mul(tangent, _dot(radial, tangent))))
    across = _unit(_cross(tangent, outward))
    return center, tangent, across, outward


# Broad top planes with one off-centre ridge; a thin concealed underside.
# Cross section is a flattened asymmetric wedge, not an ellipse. Top sequence
# runs left -> right, then the underside returns right -> left.
_TOP = ((-1.0, 0.0), (-.66, .49), (-.18, 1.0), (.29, .76), (.70, .33), (1.0, 0.0))
_PROFILE = _TOP + ((.74, -.12), (0.0, -.24), (-.74, -.12))


def _profile_height(u):
    u = max(-1.0, min(1.0, u))
    for (a, ha), (b, hb) in zip(_TOP, _TOP[1:]):
        if u <= b:
            return ha + (hb-ha)*(u-a)/(b-a)
    return 0.0


def _dimensions(spec, t):
    # Root has substantial width and is buried in the retained cap. There is no
    # repeated sin(pi*t) bell/sausage envelope. Taper begins late and is varied.
    width = spec['width'] * (.78 + .22*_smooth(0, .21, t))
    width *= 1-.965*_smooth(spec.get('taper', .63), 1.0, t)
    width *= 1+spec.get('asymmetry', .04)*sin(pi*t)
    depth = spec['depth'] * (.25+.75*_smooth(0, .16, t))
    depth *= 1-.97*_smooth(spec.get('depth_taper', .68), 1.0, t)
    return width, depth


def _surface(spec, t, u, offset=0.0):
    center, _, across, outward = _frame(spec['curve'], t)
    width, depth = _dimensions(spec, t)
    return _add(_add(center, _mul(across, width*u)),
                _mul(outward, depth*_profile_height(u)+offset))


def _scalp_curve(theta0, theta1, phi0, phi1, release, tip_drop=0.0):
    """Follow the actual cap scale instead of bridging above it with an arch.

    Wide roots lie just inside the cap; middles follow its outside contour,
    then the lower silhouette breaks into short released tips. The old cap's
    horizontal rear edge is at z~=1.103: side/back ends go below that edge.
    """
    def curve(t):
        theta = theta0+(theta1-theta0)*t
        phi = phi0+(phi1-phi0)*_smooth(0.0, 1.0, t)
        radial = .992+.057*_smooth(.0,.20,t)
        radial += release*_smooth(.70,1.0,t)
        # The retained scalp has tiny angular waves. 3-7 mm depth covers them
        # while keeping the supporting root/body on the existing head shape.
        return (.128*sin(theta)*cos(phi)*radial,
                .011+.116*sin(theta)*sin(phi)*radial,
                1.11+.132*cos(theta)-tip_drop*_smooth(.65,1.0,t))
    return curve


def _append_wedge(verts, faces, spec):
    start_v, start_f = len(verts), len(faces)
    # Rows near the thin tip avoid a broad, blunt end. A single terminal point
    # closes the wedge with nondegenerate triangles, not a zero-width ring.
    stations = (0., .055, .12, .20, .29, .39, .50, .61, .71, .80, .87, .925, .966)
    sides = len(_PROFILE)
    for t in stations:
        center, _, across, outward = _frame(spec['curve'], t)
        width, depth = _dimensions(spec, t)
        for u, h in _PROFILE:
            verts.append(_add(_add(center, _mul(across, width*u)), _mul(outward, depth*h)))
    for row in range(len(stations)-1):
        for k in range(sides):
            a = start_v+row*sides+k
            b = start_v+row*sides+(k+1)%sides
            faces.append((a, b, b+sides, a+sides))
    # A buried fan cap is robust for interchange triangulators.
    root = len(verts)
    verts.append(spec['curve'](0.0))
    for k in range(sides):
        faces.append((root, start_v+(k+1)%sides, start_v+k))
    tip = len(verts)
    verts.append(spec['curve'](1.0))
    end = start_v+(len(stations)-1)*sides
    for k in range(sides):
        faces.append((end+k, end+(k+1)%sides, tip))
    return {'name': spec['name'], 'role': spec['role'],
            'vertex_start': start_v, 'vertex_count': len(verts)-start_v,
            'face_start': start_f, 'face_count': len(faces)-start_f,
            'root': spec['curve'](0.0), 'tip': spec['curve'](1.0),
            'half_width_m': spec['width'], 'ridge_depth_m': spec['depth']}


def _append_highlight(verts, faces, spec, u, begin, end, half_width):
    first = len(verts)
    # Surface colour mark: six to nine millimetres wide would read as a toy
    # stripe, so these are deliberately only 0.5-1.3 mm at their broadest.
    rows = 11
    for j in range(rows):
        s = j/(rows-1)
        t = begin+(end-begin)*s
        width, _ = _dimensions(spec, t)
        taper = .10+.90*sin(pi*s)**.7
        du = min(.055, half_width*taper/max(width, .0001))
        for sign in (-1, 1):
            verts.append(_surface(spec, t, u+sign*du, .00015))
    for j in range(rows-1):
        a = first+j*2
        faces.append((a, a+1, a+3, a+2))


def _audit(verts, faces, closed):
    edges, triangle_count, minimum_area = {}, 0, float('inf')
    signed_volume = 0.0
    for face in faces:
        if len(set(face)) != len(face) or min(face) < 0 or max(face) >= len(verts):
            raise ValueError('Invalid hair face')
        for a, b in zip(face, face[1:]+face[:1]):
            key = (min(a, b), max(a, b))
            edges.setdefault(key, []).append(1 if a < b else -1)
        for j in range(1, len(face)-1):
            a, b, c = (verts[face[k]] for k in (0, j, j+1))
            cross = _cross(_sub(b, a), _sub(c, a))
            minimum_area = min(minimum_area, sqrt(_dot(cross, cross))*.5)
            signed_volume += _dot(a, _cross(b, c))/6
            triangle_count += 1
    if not all(isfinite(v) for p in verts for v in p) or minimum_area <= 1e-13:
        raise ValueError('Nonfinite or degenerate hair geometry')
    if closed and any(len(v) != 2 or sum(v) != 0 for v in edges.values()):
        raise ValueError('Hair wedge is not consistently closed')
    if closed and signed_volume <= 0:
        raise ValueError('Hair wedge normals point inward')
    return {'vertices': len(verts), 'faces': len(faces), 'triangles': triangle_count,
            'bounds_min': [min(p[k] for p in verts) for k in range(3)],
            'bounds_max': [max(p[k] for p in verts) for k in range(3)],
            'minimum_fan_triangle_area_m2': minimum_area,
            'signed_volume_m3': signed_volume,
            'boundary_edges': sum(len(v) == 1 for v in edges.values()),
            'closed_wedges': closed}


def build_hair_geometry():
    """Return canonical vertices/faces and honest construction/audit metadata.

    Apply the existing v6 proportion() once, then the retained hair object's
    inverse world matrix. No mesh, bone, material or Blender operation occurs.
    """
    # Three asymmetrical swept frontal masses, two broad temples, four rear
    # overlapping masses. Unlike the first attempt, width is retained deep into
    # each side/back section, so these cover the cap instead of sitting atop it.
    # theta0/theta1 and phi0/phi1 are in radians, with frontal phi near -pi/2.
    definitions = [
        ('left_swept_fringe', .16,1.31, -.25,-2.27, .048,.0105,.66,.040,.000),
        ('central_swept_fringe', .12,1.17, .20,-1.64, .041,.0095,.71,.032,.009),
        ('right_swept_fringe', .34,1.34, .20,-.67, .039,.0090,.70,.045,.004),
        ('left_temple_mass', .56,1.80, -2.60,-2.95, .036,.0085,.84,.065,.004),
        ('right_temple_mass', .49,1.77, -.34,-.19, .037,.0085,.86,.060,.006),
        ('right_rear_mass', .34,1.77, .28,.38, .044,.0090,.86,.065,.002),
        ('rear_right_mass', .20,1.82, .75,1.12, .049,.0095,.84,.055,.001),
        ('rear_left_mass', .24,1.70, 1.48,1.98, .051,.0090,.88,.065,.006),
        ('left_rear_mass', .39,1.78, 2.22,2.62, .043,.0085,.86,.060,.003),
    ]
    main = []
    for name, t0, t1, p0, p1, width, depth, taper, release, drop in definitions:
        main.append({'name': name, 'role': 'primary_broad_rooted_wedge',
                     'curve': _scalp_curve(t0,t1,p0,p1,release,drop),
                     'width': width, 'depth': depth, 'taper': taper,
                     'depth_taper': max(.68,taper-.08)})

    verts, faces, high_verts, high_faces, pieces = [], [], [], [], []
    for spec in main:
        pieces.append(_append_wedge(verts, faces, spec))

    # Different lengths, side drift, widths and terminal offsets. Each piece is
    # laid ON its main parent wedge, so their roots have no dark moat. Longer
    # temple ridges produce four uneven visible ends per side; posterior ones
    # keep cap-edge breakup through local overlap, rather than a flat haircut.
    arrangements = (
        ((-.63,-.78,.12,.96,.25), (-.21,-.41,.13,.87,.21),
         (.30,.06,.24,1.00,.28), (.72,.56,.25,.82,.20)),
        ((-.58,-.76,.15,.92,.26), (.02,-.16,.12,1.00,.29), (.62,.43,.24,.85,.23)),
        ((-.57,-.70,.17,.97,.27), (.04,-.12,.21,.87,.24), (.61,.45,.17,.92,.25)),
        ((-.62,-.78,.20,.98,.34), (-.07,-.22,.13,.88,.33), (.55,.39,.28,.94,.30)),
        ((-.61,-.78,.16,.91,.32), (-.06,-.27,.21,.98,.34), (.53,.36,.18,.85,.31)),
        ((-.46,-.66,.17,.95,.38), (.43,.20,.22,.86,.35)),
        ((-.49,-.65,.12,.89,.37), (.41,.21,.25,.98,.35)),
        ((-.48,-.69,.19,.97,.38), (.45,.25,.17,.88,.35)),
        ((-.50,-.68,.15,.87,.35), (.42,.20,.21,.96,.39)),
    )
    secondary = []
    for parent, layout in zip(main, arrangements):
        for index, (u0, u1, begin, end, width_fraction) in enumerate(layout):
            def curve(t, p=parent, ua=u0, ub=u1, start=begin, stop=end, i=index):
                pt = start+(stop-start)*t
                side = ua+(ub-ua)*_smooth(0.0, 1.0, t)
                # Root tucks just under the broad parent surface. A slight tip
                # release adds a few broken ends; the whole root remains joined.
                lift = -.00080*(1-_smooth(0.0,.18,t))+.0007*_smooth(.65,1.0,t)
                point = _surface(p, pt, side, lift)
                if stop > .95:
                    tangent = _tangent(p['curve'], pt)
                    point = _add(point, _mul(tangent, (.004+.0015*i)*_smooth(.70,1.0,t)))
                return point
            spec = {'name': parent['name']+'_ridge_'+str(index),
                    'role': 'subordinate_surface_ridge', 'curve': curve,
                    'width': parent['width']*width_fraction,
                    'depth': .0024+.00045*(index%3),
                    'taper': .60+.04*(index%3), 'asymmetry': -.025}
            secondary.append(spec)
            pieces.append(_append_wedge(verts, faces, spec))

    # A small selection of broken strokes follows the actual shallow ridge
    # surface. They taper in width and never form detached round wires.
    for index in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22):
        spec = secondary[index]
        _append_highlight(high_verts, high_faces, spec, -.10, .20,
                          .65+.035*(index%3), .00027+.00008*(index%4))

    geometry = _audit(verts, faces, True)
    highlights = _audit(high_verts, high_faces, False)
    # Validate each volume independently, rather than relying on aggregate sign.
    for piece in pieces:
        v0, nv = piece['vertex_start'], piece['vertex_count']
        f0, nf = piece['face_start'], piece['face_count']
        local_faces = [tuple(i-v0 for i in f) for f in faces[f0:f0+nf]]
        piece['audit'] = _audit(verts[v0:v0+nv], local_faces, True)
    assert geometry['triangles'] <= 12000
    assert highlights['triangles'] <= 1000
    assert max(abs(geometry['bounds_min'][0]), abs(geometry['bounds_max'][0])) < .165
    assert geometry['bounds_max'][2] < 1.278
    metadata = {
        'version': 'character-v11-hair-candidate', 'original_local_procedural_geometry': True,
        'coordinate_space': 'v6 unproportion canonical metres; front=-Y; caller applies proportion once',
        'primary_masses': len(main), 'secondary_surface_ridges': len(secondary),
        'highlight_strips': 12, 'geometry': geometry, 'highlights': highlights, 'pieces': pieces,
        'caller_preserves': ['existing 640-vertex scalp', 'face and brow/lash choices',
                             'skeleton and attachment transforms', 'two existing hair materials'],
        'material_intent': 'original dark brown; subdued existing hairLight; no yellow',
        'topology': 'closed shallow asymmetric wedge volumes; open outward highlight strips',
        'root_contact': 'ellipsoid-following primary roots overlap cap; no arched free bridge; subordinate roots overlap parent wedge',
        'revision_reason': 'v10 original views showed exposed cap/black root gaps and absent temple/rear volume; v10 is preserved',
        'visual_targets': ['unequal forehead ends above brows', 'four layered ends per temple down to ~1.075m',
                           'posterior volume ~y.14 and staggered cap-edge coverage below z1.103'],
        'limitations': ['Scalp/face are not loaded here; contact needs assembled-scene inspection.',
                        'No render or visual acceptance is claimed.',
                        'No guarantee against every facial morph or view before integration checks.'],
        'visual_review_pending': True,
    }
    return {'verts': verts, 'faces': faces, 'high_verts': high_verts,
            'high_faces': high_faces, 'metadata': metadata}


if __name__ == '__main__':
    import json
    result = build_hair_geometry()
    print(json.dumps({k: result['metadata'][k] for k in
                      ('primary_masses', 'secondary_surface_ridges', 'geometry', 'highlights')}, indent=2))
