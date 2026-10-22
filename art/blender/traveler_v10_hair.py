"""Original layered hair candidate; pure Python, canonical unproportioned metres.

The caller owns Blender objects, the retained scalp, face/brows/lashes, weights,
materials and the v6 proportion transform.  Front is -Y.  This module neither
imports bpy nor reads/writes assets.  It returns five overlapping broad rooted
wedges and seventeen subordinate surface-following ridges, not round tubes.
The original dark hair material belongs on ``verts/faces``; the existing muted
hair-light material belongs on ``high_verts/high_faces``.  No yellow material.

All primary/secondary wedges are closed, positively wound volumes. Highlights
are intentionally open, outward-facing strips. They are not collision meshes.
This geometry has not been visually accepted: CPU/native views remain required.
"""

from math import sqrt, sin, pi, isfinite


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
    width = spec['width'] * (.72 + .28*_smooth(0, .21, t))
    width *= 1-.965*_smooth(spec.get('taper', .43), 1.0, t)
    width *= 1+spec.get('asymmetry', .04)*sin(pi*t)
    depth = spec['depth'] * (.20+.80*_smooth(0, .20, t))
    depth *= 1-.97*_smooth(.48, 1.0, t)
    return width, depth


def _surface(spec, t, u, offset=0.0):
    center, _, across, outward = _frame(spec['curve'], t)
    width, depth = _dimensions(spec, t)
    return _add(_add(center, _mul(across, width*u)),
                _mul(outward, depth*_profile_height(u)+offset))


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
    definitions = [
        ('left_swept_mass', ((.014,.028,1.232), (.028,-.027,1.286),
                             (-.070,-.088,1.231), (-.137,-.044,1.145)), .047, .011, .49),
        ('central_overlapping_fringe', ((.044,.026,1.228), (.055,-.035,1.291),
                                        (.018,-.099,1.224), (-.033,-.091,1.153)), .036, .009, .39),
        ('right_swept_mass', ((.073,.033,1.216), (.107,-.002,1.266),
                              (.148,-.048,1.208), (.134,-.042,1.128)), .029, .007, .46),
        ('left_rear_mass', ((-.011,.035,1.235), (-.055,.084,1.274),
                             (-.143,.106,1.192), (-.143,.038,1.103)), .049, .009, .54),
        ('right_rear_mass', ((.038,.037,1.231), (.093,.093,1.263),
                              (.096,.124,1.185), (.074,.112,1.100)), .052, .008, .48),
    ]
    main = []
    for name, controls, width, depth, taper in definitions:
        main.append({'name': name, 'role': 'primary_broad_rooted_wedge',
                     'curve': lambda t, p=controls: _bezier(p, t),
                     'width': width, 'depth': depth, 'taper': taper})

    verts, faces, high_verts, high_faces, pieces = [], [], [], [], []
    for spec in main:
        pieces.append(_append_wedge(verts, faces, spec))

    # Different lengths, side drift, widths and terminal offsets. Each piece is
    # laid ON its main parent wedge, so the readable hierarchy remains five
    # masses instead of seventeen new isolated sausages. No random noise.
    arrangements = (
        ((-.60,-.72,.16,.97,.23), (-.16,-.40,.13,.90,.18),
         (.36,.08,.24,1.00,.27), (.70,.55,.30,.85,.16)),
        ((-.53,-.74,.19,.94,.23), (.07,-.13,.15,1.00,.28), (.63,.42,.28,.87,.18)),
        ((-.54,-.65,.18,.98,.29), (.06,-.12,.29,.90,.22), (.61,.49,.22,.83,.20)),
        ((-.68,-.73,.20,.87,.23), (-.23,-.38,.17,.99,.26),
         (.29,.05,.28,.91,.20), (.68,.49,.24,.82,.21)),
        ((-.57,-.66,.21,.96,.25), (-.05,-.25,.14,.88,.29), (.54,.32,.26,.98,.22)),
    )
    secondary = []
    for parent, layout in zip(main, arrangements):
        for index, (u0, u1, begin, end, width_fraction) in enumerate(layout):
            def curve(t, p=parent, ua=u0, ub=u1, start=begin, stop=end, i=index):
                pt = start+(stop-start)*t
                side = ua+(ub-ua)*_smooth(0.0, 1.0, t)
                # Root tucks just under the broad parent surface. A slight tip
                # release adds a few broken ends; the whole root remains joined.
                lift = -.00065*(1-_smooth(0.0,.18,t))+.0011*_smooth(.55,1.0,t)
                point = _surface(p, pt, side, lift)
                if stop > .95:
                    tangent = _tangent(p['curve'], pt)
                    point = _add(point, _mul(tangent, (.003+.001*i)*_smooth(.70,1.0,t)))
                return point
            spec = {'name': parent['name']+'_ridge_'+str(index),
                    'role': 'subordinate_surface_ridge', 'curve': curve,
                    'width': parent['width']*width_fraction,
                    'depth': .0015+.00035*(index%3),
                    'taper': .35+.05*(index%3), 'asymmetry': -.025}
            secondary.append(spec)
            pieces.append(_append_wedge(verts, faces, spec))

    # A small selection of broken strokes follows the actual shallow ridge
    # surface. They taper in width and never form detached round wires.
    for index in (0, 2, 4, 6, 8, 10, 12, 14, 16):
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
        'version': 'character-v10-hair-candidate', 'original_local_procedural_geometry': True,
        'coordinate_space': 'v6 unproportion canonical metres; front=-Y; caller applies proportion once',
        'primary_masses': len(main), 'secondary_surface_ridges': len(secondary),
        'highlight_strips': 9, 'geometry': geometry, 'highlights': highlights, 'pieces': pieces,
        'caller_preserves': ['existing 640-vertex scalp', 'face and brow/lash choices',
                             'skeleton and attachment transforms', 'two existing hair materials'],
        'material_intent': 'original dark brown; subdued existing hairLight; no yellow',
        'topology': 'closed shallow asymmetric wedge volumes; open outward highlight strips',
        'root_contact': 'primary roots overlap retained cap; subordinate roots overlap parent wedge',
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
