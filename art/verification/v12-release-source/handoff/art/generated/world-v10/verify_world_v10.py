"""Read-only world-v10 BLEND/FBX/GLB audit; writes only its JSON report.

Run in Blender's background Python. This script never saves or exports a scene,
updates the manifest, renders, or changes a frozen input file.
"""
import bpy
import hashlib
import json
import math
import struct
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


OUT = Path(__file__).resolve().parent
BASE = OUT.parent / 'world-v8'
REPORT = OUT / 'interchange-verification.json'
TARGETS = {'Garden_GrassTufts', 'Garden_CreepingMeadowLeaves'}
GRASS = 'Garden_GrassTufts'
COVER = 'Garden_CreepingMeadowLeaves'
POSITION_TOL = 1e-5
ROOT_TOL = 1e-5
NORMAL_TOL_DEGREES = 0.2
UP_NORMAL_TOL = 1e-7
SURFACE_MIN = -0.001
SURFACE_MAX = 0.018
FLOAT_TOL = 1e-7
ROOT_CLEARANCE = {GRASS: -0.0008, COVER: -0.0006}
TEXTURES = ['meadow-watercolor.png', 'meadow-normal.png']
FORMATS = ['blend', 'fbx', 'glb']
MODEL_TOL = 1e-7
U16_HALF_STEP = 0.5 / 65535.0
RAW_TOL = U16_HALF_STEP + float(np.finfo(np.float32).eps)
PART_TOPOLOGY = {'short_grass': (7, 5, 2), 'long_grass': (9, 7, 2),
                 'broad_grass': (13, 16, 1), 'creeping_leaf': (9, 8, 1)}

report = {
    'passed': False,
    'in_progress': True,
    'stage': 'started',
    'checks': [],
    'scope': (
        'Clean-scene same-format comparison to frozen world-v8. Preserve 27 '
        'non-target mesh fingerprints including normals/UV/colour/material slots '
        'and transforms, all used material node/socket/image content, and 14 '
        'anchor matrices. Audit target position/normal/linear colour readback, '
        'actual root-edge contact, low-leaf vertices/triangle centres/edge '
        'midpoints, and static full-height obstacle projection. No animated '
        'wind, continuous-intersection, runtime, aesthetic or performance claim. '
        'Target GLB colour acceptance requires exact raw UINT16 export codes and '
        'a local CORNER BYTE_COLOR importer model, not a widened error threshold.'
    ),
    'limits': {
        'position_metres': POSITION_TOL,
        'corner_normal_degrees': NORMAL_TOL_DEGREES,
        'root_contact_error_metres': ROOT_TOL,
        'expected_root_clearance_metres': ROOT_CLEARANCE,
        'creeping_sample_clearance_metres': [SURFACE_MIN, SURFACE_MAX],
        'geometric_up_normal_negative_tolerance': UP_NORMAL_TOL,
        'surface_comparison_numeric_tolerance_metres': FLOAT_TOL,
        'obstacle_ray_blender_z': 6.0,
        'obstacle_ray_length_metres': 9.0,
        'world_triangle_budget': 510293,
        'raw_glb_uint16_error_bound': RAW_TOL,
        'glb_local_byte_model_residual': MODEL_TOL,
        'historical_glb_0_0045_is_diagnostic_only': True,
    },
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checkpoint(stage, in_progress=True):
    report['stage'] = stage
    report['in_progress'] = in_progress
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WORLD_V10_AUDIT_STAGE', stage, flush=True)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load(path, kind):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if kind == 'blend':
        bpy.ops.wm.open_mainfile(filepath=str(path))
    elif kind == 'fbx':
        bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True, colors_type='LINEAR')
    else:
        bpy.ops.import_scene.gltf(filepath=str(path))


def fingerprint(obj):
    m = obj.data
    payload = {
        'matrix': [list(row) for row in obj.matrix_world],
        'vertices': [list(v.co) for v in m.vertices],
        'faces': [list(p.vertices) for p in m.polygons],
        'mi': [p.material_index for p in m.polygons],
        'smooth': [p.use_smooth for p in m.polygons],
        'mats': [mat.name for mat in m.materials],
        'uv': [[list(d.uv) for d in uv.data] for uv in m.uv_layers],
        'colours': [[a.name, a.domain, a.data_type, [list(c.color) for c in a.data]]
                    for a in m.color_attributes],
        'normals': hashlib.sha256(np.asarray(
            [tuple(n.vector) for n in m.corner_normals], dtype='<f4').tobytes()).hexdigest(),
    }
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


def socket_values(sockets):
    values = []
    for socket in sockets:
        if not hasattr(socket, 'default_value'):
            continue
        value = socket.default_value
        if not isinstance(value, (int, float, str, bool)):
            try:
                value = list(value)
            except TypeError:
                value = str(value)
        values.append([socket.identifier, value])
    return values


def material_fingerprint(mat):
    # Reuse the previous audit's packed-image handling. Staged path spelling is
    # intentionally ignored; image bytes and colour-space interpretation are not.
    nodes, links = [], []
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            image_identity = None
            if node.type == 'TEX_IMAGE' and node.image:
                image = node.image
                if image.packed_file:
                    image_hash = hashlib.sha256(bytes(image.packed_file.data)).hexdigest()
                elif image.filepath:
                    image_hash = sha(Path(bpy.path.abspath(image.filepath)))
                else:
                    raise RuntimeError('No readable image content: ' + image.name)
                image_identity = [image.name, image_hash, image.colorspace_settings.name,
                                  image.alpha_mode]
            settings = {}
            for key in ('blend_type', 'operation', 'data_type', 'attribute_name',
                        'attribute_type', 'layer_name', 'uv_map', 'vector_type',
                        'space', 'interpolation', 'extension', 'projection',
                        'projection_blend', 'distribution', 'subsurface_method',
                        'clamp_factor', 'clamp_result', 'invert', 'use_clamp'):
                if hasattr(node, key):
                    value = getattr(node, key)
                    if isinstance(value, (int, float, str, bool)):
                        settings[key] = value
            nodes.append([node.name, node.bl_idname, socket_values(node.inputs),
                          socket_values(node.outputs), settings, image_identity])
        links = sorted((link.from_node.name, link.from_socket.identifier,
                        link.to_node.name, link.to_socket.identifier)
                       for link in mat.node_tree.links)
    payload = [mat.name, list(mat.diffuse_color), mat.use_nodes,
               mat.use_backface_culling, mat.surface_render_method, nodes, links]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


def used_materials():
    return {mat.name: material_fingerprint(mat) for mat in bpy.data.materials if mat.users}


def anchors():
    return {ob.name: [list(row) for row in ob.matrix_world]
            for ob in bpy.context.scene.objects if ob.type == 'EMPTY'}


def colour_at(mesh, loop):
    attr = mesh.color_attributes.active_color
    require(attr is not None, 'Missing active vertex colour: ' + mesh.name)
    require(attr.domain in {'CORNER', 'POINT'}, 'Unexpected colour domain: ' + mesh.name)
    index = loop.index if attr.domain == 'CORNER' else loop.vertex_index
    return tuple(float(v) for v in attr.data[index].color)


def stats(values):
    if not values:
        return {'count': 0, 'min': None, 'max': None, 'mean': None}
    data = np.asarray(values, dtype=float)
    return {'count': len(values), 'min': float(data.min()),
            'p05': float(np.percentile(data, 5)), 'median': float(np.median(data)),
            'p95': float(np.percentile(data, 95)), 'p99': float(np.percentile(data, 99)),
            'max': float(data.max()), 'mean': float(data.mean())}


def world_bvh(name):
    obj = bpy.data.objects[name]
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    bvh = BVHTree.FromPolygons(points, [tuple(p.vertices) for p in obj.data.polygons],
                               all_triangles=False)
    bounds = (min(p.x for p in points), max(p.x for p in points),
              min(p.y for p in points), max(p.y for p in points))
    return bvh, bounds


def ground_height(bvh, point):
    hit = bvh.ray_cast(Vector((point.x, point.y, 6)), Vector((0, 0, -1)), 9)[0]
    return None if hit is None else hit.z


def importer_evidence():
    import io_scene_gltf2.blender.imp.mesh as mesh_importer
    import io_scene_gltf2.blender.exp.primitive_attributes as attributes_exporter
    result = {}
    for label, module, needles in (
        ('importer', mesh_importer, ["mesh.color_attributes.new(name, 'BYTE_COLOR'",
                                   "layer.data.foreach_set('color', squish(loop_cols"]),
        ('exporter', attributes_exporter, ["data['data'] *= 65535",
                                          "data['data'] += 0.5",
                                          "data['data'].astype(np.uint16)"]),
    ):
        path = Path(module.__file__).resolve()
        lines = path.read_text(encoding='utf-8').splitlines()
        hits = [{'line': i + 1, 'source': line.strip()} for i, line in enumerate(lines)
                if any(needle in line for needle in needles)]
        require(len(hits) == len(needles), 'Local implementation changed: ' + label)
        result[label] = {'path': str(path), 'sha256': sha(path), 'evidence': hits}
    return result

def error_stats(a, b):
    delta = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return {'max_rgba': float(delta.max()), 'max_rgb': float(delta[:, :3].max()),
            'mean_absolute_rgba': float(delta.mean()),
            'mean_absolute_rgb': float(delta[:, :3].mean()),
            'rows': len(delta)}

def match_positions(points, reference, label):
    ids = np.empty(len(points), dtype=np.int32)
    maximum = 0.0
    for i, point in enumerate(points):
        _, source_id, distance = reference['tree'].find(Vector(point))
        require(source_id is not None and distance <= POSITION_TOL,
                label + ': no source POSITION correspondence at ' + str(i))
        ids[i] = source_id
        maximum = max(maximum, float(distance))
    return ids, maximum

def read_glb(path):
    blob = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', blob)
    require(magic == 0x46546c67 and version == 2 and length == len(blob), 'Invalid GLB header')
    document = binary = None
    offset = 12
    while offset < len(blob):
        size, kind = struct.unpack_from('<II', blob, offset)
        chunk = blob[offset + 8:offset + 8 + size]
        if kind == 0x4e4f534a:
            document = json.loads(chunk.decode('utf-8'))
        elif kind == 0x004e4942:
            binary = chunk
        offset += 8 + size
    require(document is not None and binary is not None, 'Missing GLB chunks')
    return document, binary

def accessor(document, binary, index, component_type, width):
    item = document['accessors'][index]
    require(item['componentType'] == component_type and item['type'] == 'VEC' + str(width)
            and not item.get('sparse'), 'Unexpected accessor layout: ' + str(index))
    view = document['bufferViews'][item['bufferView']]
    require(view.get('buffer', 0) == 0, 'External accessor buffer unsupported')
    dtype = np.dtype('<f4' if component_type == 5126 else '<u2')
    start = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    stride = view.get('byteStride', width * dtype.itemsize)
    values = np.ndarray((item['count'], width), dtype=dtype, buffer=binary,
                        offset=start, strides=(stride, dtype.itemsize)).copy()
    return item, values

def node_world_matrices(document):
    found = []
    def visit(index, parent, ancestors):
        require(index not in ancestors, 'Cycle in glTF nodes')
        node = document['nodes'][index]
        if 'matrix' in node:
            # glTF stores column-major matrices, mathutils takes rows.
            local = Matrix([node['matrix'][row::4] for row in range(4)])
        else:
            x, y, z, w = node.get('rotation', [0, 0, 0, 1])
            local = (Matrix.Translation(Vector(node.get('translation', [0, 0, 0]))) @
                     Quaternion((w, x, y, z)).to_matrix().to_4x4() @
                     Matrix.Diagonal((*node.get('scale', [1, 1, 1]), 1)))
        world = parent @ local
        if node.get('name') in TARGETS:
            found.append((index, node, world))
        for child in node.get('children', []):
            visit(child, world, ancestors | {index})
    scene = document['scenes'][document.get('scene', 0)]
    for root in scene.get('nodes', []):
        visit(root, Matrix.Identity(4), set())
    require(sorted(node['name'] for _, node, _ in found) == sorted(TARGETS),
            'Expected exactly one scene instance of each target')
    return found

def audit_raw_glb(path, source):
    """Map raw GLB colours to source vertices by transformed POSITION only."""
    document, binary = read_glb(path)
    summaries, raw_by_source = [], {}
    for node_id, node, world in node_world_matrices(document):
        name = node['name']
        reference = source[name]
        source_colours = np.asarray(reference['colours'], dtype=np.float32)
        mapped = np.full((reference['vertices'], 4), np.nan, dtype=np.float32)
        primitive_rows = []
        raw_values, source_values = [], []
        max_position = 0.0
        code_mismatches = 0
        for primitive_id, primitive in enumerate(document['meshes'][node['mesh']]['primitives']):
            require(primitive.get('mode', 4) == 4, 'Expected triangle primitive: ' + name)
            _, positions = accessor(document, binary, primitive['attributes']['POSITION'], 5126, 3)
            colour_meta, codes = accessor(document, binary, primitive['attributes']['COLOR_0'], 5123, 4)
            require(colour_meta.get('normalized') is True and len(codes) == len(positions),
                    'Expected normalized UINT16 colours: ' + name)
            # Transform by the complete glTF node hierarchy before the Y-up mapping.
            gltf_world = np.c_[positions.astype(np.float64), np.ones(len(positions))] @ np.asarray(world).T
            blender_world = gltf_world[:, [0, 2, 1]].copy()
            blender_world[:, 1] *= -1
            ids, position_error = match_positions(blender_world, reference, name + '/raw')
            max_position = max(max_position, position_error)
            exact_linear = codes.astype(np.float64) / 65535.0
            float_linear = exact_linear.astype(np.float32)  # BinaryData.decode_accessor_obj.
            expected_codes = np.clip(source_colours[ids], 0, 1).copy()
            expected_codes *= np.float32(65535)
            expected_codes += np.float32(0.5)
            expected_codes = expected_codes.astype(np.uint16)
            code_mismatches += int(np.count_nonzero(codes != expected_codes))
            for j, source_id in enumerate(ids):
                previous = mapped[source_id]
                require(np.isnan(previous[0]) or np.array_equal(previous, float_linear[j]),
                        'POSITION has conflicting raw colours: ' + name)
                mapped[source_id] = float_linear[j]
            raw_values.append(exact_linear)
            source_values.append(source_colours[ids])
            primitive_rows.append({'primitive': primitive_id, 'vertices': len(ids),
                                   'position_accessor': primitive['attributes']['POSITION'],
                                   'colour_accessor': primitive['attributes']['COLOR_0']})
        coverage = int(np.count_nonzero(np.isfinite(mapped[:, 0])))
        require(coverage == reference['vertices'], 'Raw POSITION does not cover every source vertex: ' + name)
        raw_values, source_values = np.concatenate(raw_values), np.concatenate(source_values)
        errors = error_stats(raw_values, source_values)
        passed = errors['max_rgba'] <= RAW_TOL and code_mismatches == 0
        summaries.append({'mesh': name, 'node': node_id, 'mesh_index': node['mesh'],
                          'node_world_matrix_gltf': [list(row) for row in world],
                          'coordinate_conversion': 'node world, then (x, -z, y), metre scale 1',
                          'source_vertices_covered': coverage, 'primitives': primitive_rows,
                          'max_position_error_metres': max_position,
                          'raw_linear_to_source_error': errors,
                          'expected_export_uint16_code_mismatches': code_mismatches,
                          'ideal_uint16_half_step': U16_HALF_STEP,
                          'float32_arithmetic_allowance': float(np.finfo(np.float32).eps),
                          'raw_linear_error_bound': RAW_TOL, 'passed': passed})
        raw_by_source[name] = mapped
    return summaries, raw_by_source

def audit_imported_byte_colours(source, raw_by_source):
    """Use an unsaved temporary CORNER BYTE_COLOR attribute, exactly like importer."""
    summaries = []
    for name in TARGETS:
        obj = bpy.data.objects[name]
        mesh = obj.data
        attr = mesh.color_attributes.get('Color')
        require(attr is not None and attr.data_type == 'BYTE_COLOR' and attr.domain == 'CORNER',
                'Local importer storage changed: ' + name)
        positions = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        ids, position_error = match_positions(positions, source[name], name + '/import')
        coverage = len(np.unique(ids))
        require(coverage == source[name]['vertices'], 'Import POSITION coverage differs: ' + name)
        loop_vertices = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get('vertex_index', loop_vertices)
        loop_ids = ids[loop_vertices]
        raw = np.ascontiguousarray(raw_by_source[name][loop_ids], dtype=np.float32)
        original = np.asarray(source[name]['colours'], dtype=np.float32)[loop_ids]
        actual = np.empty((len(mesh.loops), 4), dtype=np.float32)
        attr.data.foreach_get('color', actual.ravel())
        active_index = mesh.color_attributes.active_color_index
        render_index = mesh.color_attributes.render_color_index
        temporary = mesh.color_attributes.new('__quantization_proof_unsaved__', 'BYTE_COLOR', 'CORNER')
        try:
            temporary.data.foreach_set('color', raw.ravel())
            expected = np.empty_like(raw)
            temporary.data.foreach_get('color', expected.ravel())
        finally:
            mesh.color_attributes.remove(temporary)
            mesh.color_attributes.active_color_index = active_index
            mesh.color_attributes.render_color_index = render_index
        residual = error_stats(actual, expected)
        actual_error = error_stats(actual, original)
        worst_loop, worst_channel = np.unravel_index(np.abs(actual - original).argmax(), actual.shape)
        summaries.append({
            'mesh': name, 'attribute_type': attr.data_type, 'attribute_domain': attr.domain,
            'loops': len(mesh.loops), 'source_vertices_covered': coverage,
            'max_position_error_metres': position_error,
            'raw_float32_to_source_error': error_stats(raw, original),
            'local_byte_conversion_to_raw_error': error_stats(expected, raw),
            'predicted_byte_to_source_error': error_stats(expected, original),
            'actual_import_to_source_error': actual_error,
            'actual_import_minus_predicted_byte_error': residual,
            'model_residual_tolerance': MODEL_TOL,
            'exactly_equal_model_components': int(np.count_nonzero(actual == expected)),
            'total_components': int(actual.size),
            'exceeds_old_import_threshold_0_0045': actual_error['max_rgba'] > 0.0045,
            'worst_source_error': {'loop': int(worst_loop), 'channel': int(worst_channel),
                'source_vertex': int(loop_ids[worst_loop]),
                'source_linear': original[worst_loop].tolist(),
                'raw_glb_linear_float32': raw[worst_loop].tolist(),
                'predicted_local_byte_linear': expected[worst_loop].tolist(),
                'actual_import_linear': actual[worst_loop].tolist()},
            'passed': residual['max_rgba'] <= MODEL_TOL,
        })
    return summaries


def read_source_targets(expected):
    load(OUT / 'island.blend', 'blend')
    require(abs(bpy.context.scene.unit_settings.scale_length - 1.0) < 1e-12,
            'Raw GLB coordinate proof requires the frozen metre-scale scene')
    mesh_names = {ob.name for ob in bpy.context.scene.objects if ob.type == 'MESH'}
    require(len(mesh_names) == 29 and TARGETS <= mesh_names, 'Unexpected candidate mesh inventory')
    require(len(anchors()) == 14, 'Candidate BLEND must have 14 anchors')
    source = {}
    summaries = []
    actual_classes = Counter()
    for name in sorted(TARGETS):
        obj = bpy.data.objects[name]
        mesh = obj.data
        mesh.calc_loop_triangles()
        positions = [obj.matrix_world @ v.co for v in mesh.vertices]
        tree = KDTree(len(positions))
        for i, point in enumerate(positions):
            tree.insert(point, i)
        tree.balance()
        normals = [[] for _ in positions]
        colours = [None] * len(positions)
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        for loop, normal in zip(mesh.loops, mesh.corner_normals):
            value = tuple((normal_matrix @ normal.vector).normalized())
            if value not in normals[loop.vertex_index]:
                normals[loop.vertex_index].append(value)
            colour = colour_at(mesh, loop)
            previous = colours[loop.vertex_index]
            require(previous is None or max(abs(a-b) for a, b in zip(previous, colour)) < 1e-7,
                    'Candidate has corner-dependent source colour: ' + name)
            colours[loop.vertex_index] = colour
        require(all(normals) and all(c is not None for c in colours),
                'Unreferenced target vertex: ' + name)
        roots = set()
        vertex_cursor = face_cursor = 0
        parts = expected['parts'][name]
        source_components = set()
        for part in parts:
            kind = part['kind']
            require(kind in PART_TOPOLOGY and ((name == COVER) == (kind == 'creeping_leaf')),
                    'Unexpected source part kind: ' + name)
            nv, nf, root_count = PART_TOPOLOGY[kind]
            require(part['vertex_start'] == vertex_cursor and part['face_start'] == face_cursor,
                    'Non-contiguous source part ranges: ' + name)
            require(part['vertex_count'] == nv and part['face_count'] == nf,
                    'Unexpected source part topology: ' + name)
            offsets = part['root_vertex_offsets']
            require(isinstance(offsets, list) and len(offsets) == root_count and
                    len(set(offsets)) == root_count and all(isinstance(i, int) and 0 <= i < nv for i in offsets),
                    'Invalid explicit root-vertex offsets: ' + name)
            source_component = part['source_component_index']
            require(isinstance(source_component, int) and source_component >= 0 and
                    source_component not in source_components, 'Duplicate/invalid source component: ' + name)
            source_components.add(source_component)
            for polygon in mesh.polygons[face_cursor:face_cursor + nf]:
                require(len(polygon.vertices) == 3 and all(vertex_cursor <= i < vertex_cursor + nv
                        for i in polygon.vertices), 'Part face crosses component range: ' + name)
            roots.update(vertex_cursor + i for i in offsets)
            actual_classes[kind] += 1
            vertex_cursor += nv
            face_cursor += nf
        require(vertex_cursor == len(mesh.vertices) and face_cursor == len(mesh.polygons),
                'Source parts do not cover target mesh: ' + name)
        require(len(parts) == expected['live_component_counts'][name],
                'Part count differs from manifest: ' + name)
        source[name] = {'tree': tree, 'normals': normals, 'colours': colours,
                        'root_ids': roots, 'triangles': len(mesh.loop_triangles),
                        'vertices': len(positions), 'parts': len(parts),
                        'materials': [mat.name for mat in mesh.materials]}
        summaries.append({'mesh': name, 'vertices': len(positions),
                          'triangles': len(mesh.loop_triangles), 'parts': len(parts),
                          'root_edge_source_vertices': len(roots),
                          'part_ranges_cover_source': True})
    require(dict(actual_classes) == expected['retained_classes'], 'Retained class counts differ')
    report['retained_part_classes'] = dict(actual_classes)
    report['source_part_validation'] = summaries
    return source, mesh_names


def raw_glb_colours(expected):
    raw = (OUT / 'island.glb').read_bytes()
    require(raw[:4] == b'glTF', 'Invalid GLB signature')
    json_length, chunk_kind = struct.unpack_from('<I4s', raw, 12)
    require(chunk_kind == b'JSON', 'Missing GLB JSON chunk')
    gltf = json.loads(raw[20:20 + json_length])
    binary = 20 + json_length + 8
    require(raw[20 + json_length + 4:binary] == b'BIN\x00', 'Missing GLB BIN chunk')
    wanted = {entry['mesh']: entry for entry in expected['vertex_colors']}
    result = []
    for gm in gltf['meshes']:
        lo, hi, types = 1.0, 0.0, set()
        for primitive in gm['primitives']:
            acc = gltf['accessors'][primitive['attributes']['COLOR_0']]
            require(acc['type'] == 'VEC4' and 'sparse' not in acc, 'Unsupported GLB colour layout')
            view = gltf['bufferViews'][acc['bufferView']]
            typ = acc['componentType']
            types.add(typ)
            dtype = np.dtype({5123: '<u2', 5126: '<f4', 5121: 'u1'}[typ])
            require(typ == 5126 or acc.get('normalized') is True, 'Unnormalized integer COLOR_0')
            offset = binary + view.get('byteOffset', 0) + acc.get('byteOffset', 0)
            stride = view.get('byteStride', dtype.itemsize * 4)
            array = np.ndarray((acc['count'], 4), dtype=dtype, buffer=raw, offset=offset,
                               strides=(stride, dtype.itemsize)).astype(float)
            if acc.get('normalized'):
                array /= 65535 if typ == 5123 else 255
            require(np.isfinite(array).all(), 'Nonfinite raw GLB colours')
            lo, hi = min(lo, float(array[:, :3].min())), max(hi, float(array[:, :3].max()))
            require(np.max(np.abs(array[:, 3] - 1)) < 0.00004, 'Nonopaque raw GLB colour alpha')
        want = wanted[gm['name']]
        delta = max(abs(lo - want['min_rgb']), abs(hi - want['max_rgb']))
        result.append({'mesh': gm['name'], 'component_types': sorted(types),
                       'range_error': delta, 'linear_range_matches_manifest': delta < 0.00004,
                       'linear': delta < 0.00004})
    require({entry['mesh'] for entry in result} == set(wanted), 'Raw GLB colour mesh inventory differs')
    return result


def verify_target(name, kind, source, ground, obstacles, errors):
    obj = bpy.data.objects[name]
    mesh = obj.data
    saved = source[name]
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    points = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
    mapping = []
    max_position_error = 0.0
    for point in points:
        _, source_id, distance = saved['tree'].find(point)
        mapping.append(source_id)
        max_position_error = max(max_position_error, distance)
    normal_error = colour_error = 0.0
    bad_normals = 0
    for loop, normal in zip(mesh.loops, mesh.corner_normals):
        source_id = mapping[loop.vertex_index]
        actual = normal_matrix @ normal.vector
        if actual.length_squared < 1e-16:
            bad_normals += 1
            normal_error = 180.0
        else:
            actual.normalize()
            dot = max(float(actual.dot(Vector(value))) for value in saved['normals'][source_id])
            angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
            normal_error = max(normal_error, angle)
            bad_normals += angle > NORMAL_TOL_DEGREES
        colour = colour_at(mesh, loop)
        colour_error = max(colour_error, max(abs(a-b) for a, b in
                           zip(colour, saved['colours'][source_id])))

    root_values, root_errors = [], []
    seen_roots = set()
    missing_roots = 0
    for vertex_id, point in enumerate(points):
        source_id = mapping[vertex_id]
        if source_id not in saved['root_ids']:
            continue
        seen_roots.add(source_id)
        height = ground_height(ground, point)
        if height is None:
            missing_roots += 1
            continue
        clearance = point.z - height
        root_values.append(clearance)
        root_errors.append(abs(clearance - ROOT_CLEARANCE[name]))
    missing_source_root_ids = len(saved['root_ids'] - seen_roots)
    max_root_error = max(root_errors, default=math.inf)

    vertex_hits, centre_hits = Counter(), Counter()
    first_hits = []
    def obstacle_check(point, counts, sample_kind, index):
        for obstacle_name, (bvh, bounds) in obstacles.items():
            x0, x1, y0, y1 = bounds
            if not (x0 <= point.x <= x1 and y0 <= point.y <= y1):
                continue
            if bvh.ray_cast(Vector((point.x, point.y, 6)), Vector((0, 0, -1)), 9)[0] is not None:
                counts[obstacle_name] += 1
                if len(first_hits) < 8:
                    first_hits.append({'obstacle': obstacle_name, 'sample': sample_kind,
                                       'index': index, 'position_blender_world': list(point)})
    for i, point in enumerate(points):
        obstacle_check(point, vertex_hits, 'vertex', i)

    up_min = 1.0
    negative_faces = nonpositive_faces = 0
    centres = []
    edges = set()
    for i, triangle in enumerate(mesh.loop_triangles):
        ids = tuple(triangle.vertices)
        a, b, c = (points[index] for index in ids)
        centre = (a + b + c) / 3
        obstacle_check(centre, centre_hits, 'triangle_centroid', i)
        normal = (b-a).cross(c-a)
        if normal.length_squared <= 1e-24:
            negative_faces += 1
            up_min = -1.0
        else:
            normal.normalize()
            up_min = min(up_min, normal.z)
            negative_faces += normal.z < -UP_NORMAL_TOL
            nonpositive_faces += normal.z <= 0
        if name == COVER:
            centres.append(centre)
            for a_id, b_id in zip(ids, ids[1:] + ids[:1]):
                edges.add((min(a_id, b_id), max(a_id, b_id)))

    surface = None
    if name == COVER:
        values = {'vertices': [], 'triangle_centroids': [], 'edge_midpoints': []}
        missing = Counter()
        below = Counter()
        above = Counter()
        collections = [('vertices', points), ('triangle_centroids', centres),
                       ('edge_midpoints', ((points[a] + points[b]) * 0.5 for a, b in edges))]
        for sample_kind, samples in collections:
            for point in samples:
                height = ground_height(ground, point)
                if height is None:
                    missing[sample_kind] += 1
                    continue
                clearance = point.z - height
                values[sample_kind].append(clearance)
                below[sample_kind] += clearance < SURFACE_MIN - FLOAT_TOL
                above[sample_kind] += clearance > SURFACE_MAX + FLOAT_TOL
        surface = {'clearance_metres': {key: stats(value) for key, value in values.items()},
                   'missing_ground_hits': dict(missing),
                   'samples_below_minus_1mm': dict(below),
                   'samples_above_18mm': dict(above),
                   'passed': not sum(missing.values()) and not sum(below.values()) and not sum(above.values())}
        if not surface['passed']:
            errors.append('Creeping surface clearance failed: ' + name)

    if len(mesh.loop_triangles) != saved['triangles']:
        errors.append('Target triangle count changed: ' + name)
    if [mat.name for mat in mesh.materials] != saved['materials']:
        errors.append('Target material slots changed: ' + name)
    if max_position_error > POSITION_TOL:
        errors.append('Target positions failed: ' + name)
    if bad_normals:
        errors.append('Target corner normals failed: ' + name)
    if kind != 'glb' and colour_error > 0.00001:
        errors.append('Target linear colours failed: ' + name)
    if missing_roots or missing_source_root_ids or max_root_error > ROOT_TOL:
        errors.append('Actual root-edge contact failed: ' + name)
    if negative_faces:
        errors.append('Target geometric faces point downward: ' + name)
    if vertex_hits or centre_hits:
        errors.append('Full-height static obstacle projection failed: ' + name)
    return {
        'mesh': name, 'vertices': len(points), 'triangles': len(mesh.loop_triangles),
        'max_position_error_metres': max_position_error,
        'max_corner_normal_error_degrees': normal_error,
        'normal_corners_over_0_2_degrees': bad_normals,
        'max_linear_colour_error': colour_error,
        'colour_acceptance': ('raw UINT16 export codes + local BYTE_COLOR model'
                              if kind == 'glb' else 'linear RGBA error <= 0.00001'),
        'exceeds_historical_glb_0_0045': kind == 'glb' and colour_error > 0.0045,
        'geometric_face_up_normal_min': up_min,
        'geometric_faces_below_negative_tolerance': negative_faces,
        'geometric_faces_nonpositive_before_tolerance': nonpositive_faces,
        'root_edge_contact': {'source_root_vertex_count': len(saved['root_ids']),
                              'matched_unique_source_root_vertices': len(seen_roots),
                              'unmatched_source_root_vertices': missing_source_root_ids,
                              'missing_ground_hits': missing_roots,
                              'clearance_metres': stats(root_values),
                              'max_error_from_expected_metres': max_root_error if root_errors else None,
                              'expected_clearance_metres': ROOT_CLEARANCE[name]},
        'creeping_surface_samples': surface,
        'full_height_obstacle_projection': {
            'vertices_tested': len(points), 'triangle_centroids_tested': len(mesh.loop_triangles),
            'vertex_hits': dict(vertex_hits), 'triangle_centroid_hits': dict(centre_hits),
            'first_hits': first_hits,
        },
    }


def verify_format(kind, expected, source, source_names, raw_by_source):
    load(BASE / ('island.' + kind), kind)
    frozen = {ob.name: fingerprint(ob) for ob in bpy.context.scene.objects
              if ob.type == 'MESH' and ob.name not in TARGETS}
    old_anchors = anchors()
    old_materials = used_materials()
    load(OUT / ('island.' + kind), kind)
    objects = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH']
    errors = []
    actual_names = {ob.name for ob in objects}
    if actual_names != source_names or len(objects) != 29:
        errors.append('Mesh inventory changed')
    if len(frozen) != 27:
        errors.append('Expected 27 frozen non-target meshes')
    unchanged = []
    for name, value in frozen.items():
        actual = fingerprint(bpy.data.objects[name]) if name in actual_names else None
        same = actual == value
        unchanged.append({'mesh': name, 'same': same,
                          'baseline_sha256': value, 'candidate_sha256': actual})
        if not same:
            errors.append('Non-target fingerprint mismatch: ' + name)
    new_materials = used_materials()
    materials_same = old_materials == new_materials
    if not materials_same:
        errors.append('Material node/value/image content changed')
    new_anchors = anchors()
    anchors_same = old_anchors == new_anchors
    if not anchors_same or len(new_anchors) != 14 or len(old_anchors) != 14:
        errors.append('Anchor matrices/count changed')
    triangles = 0
    zero, duplicates, invalid_normals = [], [], []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        bad = sum(t.area < 1e-12 for t in mesh.loop_triangles)
        duplicate = len(mesh.loop_triangles) - len({tuple(sorted(t.vertices)) for t in mesh.loop_triangles})
        if bad:
            zero.append([obj.name, bad])
        if duplicate:
            duplicates.append([obj.name, duplicate])
        if any(not math.isfinite(float(value)) for vertex in mesh.vertices for value in vertex.co):
            errors.append('Nonfinite positions: ' + obj.name)
        if any(not math.isfinite(float(value)) for normal in mesh.corner_normals for value in normal.vector):
            invalid_normals.append(obj.name)
    if triangles != expected['triangles'] or triangles > 510293:
        errors.append('Triangle total/budget mismatch')
    if zero or duplicates or invalid_normals:
        errors.append('Degenerate/duplicate/invalid normal data')
    ground, _ = world_bvh('Island_Meadow')
    obstacles = {name: world_bvh(name) for name in expected['full_height_obstacles']}
    target_checks = [verify_target(name, kind, source, ground, obstacles, errors)
                     for name in sorted(TARGETS)]
    byte_model = None
    if kind == 'glb':
        require(abs(bpy.context.scene.unit_settings.scale_length - 1.0) < 1e-12,
                'GLB import unit scale differs from the raw coordinate proof')
        byte_model = audit_imported_byte_colours(source, raw_by_source)
        for item in byte_model:
            if not item['passed']:
                errors.append('Local BYTE_COLOR importer model failed: ' + item['mesh'])
    return {'format': kind, 'mesh_count': len(objects), 'anchor_count': len(new_anchors),
            'triangles': triangles, 'unchanged_non_targets': unchanged,
            'materials_identical': materials_same, 'anchors_identical': anchors_same,
            'material_fingerprints': {'baseline': old_materials, 'candidate': new_materials},
            'zero_area_triangles': zero, 'duplicate_triangles': duplicates,
            'invalid_normal_meshes': invalid_normals, 'target_checks': target_checks,
            'local_byte_colour_model': byte_model,
            'sha256': sha(OUT / ('island.' + kind)), 'errors': errors, 'passed': not errors}


def main():
    checkpoint('started')
    expected = json.loads((OUT / 'asset-manifest.json').read_text(encoding='utf-8'))
    baseline = json.loads((BASE / 'asset-manifest.json').read_text(encoding='utf-8'))
    require(expected['revision'] == 'world-v10' and expected['source'] == 'world-v8',
            'Manifest identifies another revision/source')
    require(set(expected['changed_meshes']) == TARGETS, 'Manifest target scope changed')
    require(expected['triangle_budget'] == 510293 and 0 < expected['triangles'] <= 510293,
            'Manifest budget is invalid')
    full_height = expected['full_height_obstacles']
    require(isinstance(full_height, list) and len(full_height) == len(set(full_height)) and
            {'Garden_HeroBoulders', 'Garden_Walkways', 'Observatory_StoneAndBrass', 'Cliff_Pier'} <= set(full_height),
            'Full-height obstacle scope is incomplete')
    report['full_height_obstacles'] = full_height
    report['expected_triangles'] = expected['triangles']
    paths = ['island.' + kind for kind in FORMATS] + ['textures/' + name for name in TEXTURES]
    initial_hashes = {str(directory / name): sha(directory / name)
                      for directory in (BASE, OUT) for name in paths}
    report['frozen_source_hashes_unchanged'] = {
        name: initial_hashes[str(BASE / name)].lower() == baseline['sha256'][name].lower() for name in paths}
    report['candidate_hashes_match'] = {
        name: initial_hashes[str(OUT / name)].lower() == expected['sha256'][name].lower() for name in paths}
    report['textures_byte_identical'] = {
        name: initial_hashes[str(OUT / 'textures' / name)] == initial_hashes[str(BASE / 'textures' / name)]
        for name in TEXTURES}
    for directory in (BASE, OUT):
        path = directory / 'asset-manifest.json'
        initial_hashes[str(path)] = sha(path)
    report['script_sha256'] = sha(__file__)
    report['glb_colour_implementation'] = importer_evidence()
    checkpoint('file_hashes')
    require(all(report['frozen_source_hashes_unchanged'].values()) and
            all(report['candidate_hashes_match'].values()) and
            all(report['textures_byte_identical'].values()), 'Frozen/candidate file hashes failed')
    source, source_names = read_source_targets(expected)
    checkpoint('source_parts_and_kdtrees')
    report['raw_glb_colours'] = raw_glb_colours(expected)
    report['raw_glb_target_quantization'], raw_by_source = audit_raw_glb(OUT / 'island.glb', source)
    checkpoint('raw_glb_linear_colours_and_uint16_codes')
    for kind in FORMATS:
        checkpoint('readback_' + kind)
        try:
            item = verify_format(kind, expected, source, source_names, raw_by_source)
        except Exception as error:
            item = {'format': kind, 'passed': False, 'errors': [str(error)],
                    'exception': traceback.format_exc()}
        report['checks'].append(item)
        checkpoint('completed_' + kind)
        print('WORLD_V10_READBACK', kind, 'PASS' if item['passed'] else item['errors'], flush=True)
    report['input_files_unchanged_during_audit'] = {
        name: sha(name) == digest for name, digest in initial_hashes.items()}
    report['passed'] = (len(report['checks']) == 3 and all(item['passed'] for item in report['checks']) and
                        all(item['linear'] for item in report['raw_glb_colours']) and
                        all(item['passed'] for item in report['raw_glb_target_quantization']) and
                        all(report['input_files_unchanged_during_audit'].values()))
    checkpoint('complete', in_progress=False)
    require(report['passed'], 'World-v10 audit failed; see interchange-verification.json')
    print('WORLD_V10_ALL_VERIFIED', expected['triangles'], flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        report['passed'] = False
        report['fatal_error'] = str(error)
        report['fatal_traceback'] = traceback.format_exc()
        checkpoint('failed', in_progress=False)
        raise
