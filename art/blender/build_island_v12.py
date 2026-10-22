"""Game v13 revised tree candidate, derived only from frozen world-v10.

All geometry is locally authored. Replace three named tree meshes; preserve
complete source trunk components reaching below Unity Y=1.20 m. No rendering.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import shutil
import sys
from collections import Counter

import bpy
import numpy as np
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'art/generated/world-v10'
OUT = ROOT / 'art/generated/world-v12'
TARGETS = {'Garden_TreeTrunks', 'Garden_TreeCanopies', 'Garden_CanopyLeafEdges'}
BASES = {'broad': Vector((-6.55, 0, 3.9)), 'gold': Vector((2.7, 0, 6.4)),
         'cypress': Vector((5.1, 0, 3.0))}
LOW_Y = 1.20
UP = Vector((0, 1, 0))
RNG = random.Random(13112026)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def B(p):
    return Vector((p[0], -p[2], p[1]))


def U(p):
    return Vector((p[0], p[2], -p[1]))


spec = importlib.util.spec_from_file_location('frozen_world_audit', BASE / 'verify_world_v10.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def components(obj):
    mesh = obj.data
    neighbors = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].append(b)
        neighbors[b].append(a)
    seen = set()
    groups, component_ids = [], {}
    for start in range(len(neighbors)):
        if start in seen:
            continue
        pending, ids = [start], []
        seen.add(start)
        while pending:
            vertex = pending.pop()
            ids.append(vertex)
            component_ids[vertex] = len(groups)
            for neighbor in neighbors[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        groups.append({'vertices': sorted(ids), 'faces': []})
    for polygon in mesh.polygons:
        groups[component_ids[polygon.vertices[0]]]['faces'].append(polygon.index)
    return groups


def component_payload(mesh, group):
    # Local vertex numbering makes this independent of insertion/reordering.
    mapping = {v: i for i, v in enumerate(group['vertices'])}
    faces = []
    for face_id in group['faces']:
        face = mesh.polygons[face_id]
        faces.append({'vertices': [mapping[v] for v in face.vertices],
                      'material': mesh.materials[face.material_index].name,
                      'smooth': face.use_smooth,
                      'uv': [[list(layer.data[i].uv) for i in face.loop_indices] for layer in mesh.uv_layers],
                      'colours': [[list(attr.data[i if attr.domain == 'CORNER' else mesh.loops[i].vertex_index].color)
                                   for i in face.loop_indices] for attr in mesh.color_attributes],
                      'normals': [list(mesh.corner_normals[i].vector) for i in face.loop_indices]})
    return {'vertices': [list(mesh.vertices[v].co) for v in group['vertices']], 'faces': faces}


def digest(payload):
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


def inspect_source():
    obj = bpy.data.objects['Garden_TreeTrunks']
    mesh = obj.data
    mesh.calc_loop_triangles()
    tri_count = Counter(t.polygon_index for t in mesh.loop_triangles)
    groups = components(obj)
    records = []
    preserved = []
    for index, group in enumerate(groups):
        coords = [U(obj.matrix_world @ mesh.vertices[i].co) for i in group['vertices']]
        low, high = min(v.y for v in coords), max(v.y for v in coords)
        center = sum(coords, Vector()) / len(coords)
        kind = min(BASES, key=lambda k: (center.x-BASES[k].x)**2+(center.z-BASES[k].z)**2)
        keep = low < LOW_Y
        record = {'source_component': index, 'tree': kind, 'keep_entire_component': keep,
                  'vertices': len(coords), 'polygons': len(group['faces']),
                  'triangles': sum(tri_count[i] for i in group['faces']),
                  'min_unity': [min(v[a] for v in coords) for a in range(3)],
                  'max_unity': [max(v[a] for v in coords) for a in range(3)],
                  'geometry_uv_colour_normal_sha256': digest(component_payload(mesh, group))}
        records.append(record)
        if keep:
            preserved.append((index, group))
    result = {'source': 'world-v10', 'rule': 'Keep every whole connected component containing any world Unity Y < 1.20 m vertex.',
              'threshold_unity_y': LOW_Y, 'components': records,
              'preserved_components': len(preserved),
              'preserved_triangles': sum(r['triangles'] for r in records if r['keep_entire_component']),
              'limits': 'Source edge-connected components, not a bounding-box reconstruction. Upper collision geometry may change.'}
    (OUT / 'frozen-trunk-components.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('TREE_SOURCE_LOW_COMPONENTS', result['preserved_components'], result['preserved_triangles'], flush=True)
    return preserved, result


class TreeMesh:
    def __init__(self, name):
        self.name = name
        source = bpy.data.objects[name].data
        self.materials = [m.name for m in source.materials]
        self.uv_names = [layer.name for layer in source.uv_layers]
        self.colour_specs = [(a.name, a.domain, a.data_type) for a in source.color_attributes]
        assert len(self.uv_names) == 1 and len(self.colour_specs) == 1
        assert self.colour_specs[0][1:] == ('CORNER', 'FLOAT_COLOR')
        self.v, self.faces, self.parts = [], [], []

    def add(self, vertices, faces, material, colours, kind, tree, normal=None):
        start, first_face = len(self.v), len(self.faces)
        self.v.extend(B(p) for p in vertices)
        for indices in faces:
            indices = tuple(indices)
            if normal is not None:
                a, b, c = [vertices[i] for i in indices[:3]]
                if (b-a).cross(c-a).dot(normal) < 0:
                    indices = tuple(reversed(indices))
            self.faces.append({'vs': tuple(start+i for i in indices), 'mi': self.materials.index(material),
                               'smooth': True, 'uv': [((vertices[i].x+9)/18, (vertices[i].z+9)/18) for i in indices],
                               'colours': [colours[i] for i in indices], 'normals': None})
        self.parts.append({'kind': kind, 'tree': tree, 'vertex_start': start, 'vertex_count': len(vertices),
                           'source_face_start': first_face, 'face_count': len(faces)})

    def keep(self, mesh, group, component_id):
        mapping = {old: len(self.v)+i for i, old in enumerate(group['vertices'])}
        self.v.extend(mesh.vertices[i].co.copy() for i in group['vertices'])
        first = len(self.faces)
        for face_id in group['faces']:
            face = mesh.polygons[face_id]
            self.faces.append({'vs': tuple(mapping[i] for i in face.vertices), 'mi': face.material_index,
                               'smooth': face.use_smooth,
                               'uv': [tuple(mesh.uv_layers[0].data[i].uv) for i in face.loop_indices],
                               'colours': [tuple(mesh.color_attributes[0].data[i].color) for i in face.loop_indices],
                               'normals': [tuple(mesh.corner_normals[i].vector) for i in face.loop_indices]})
        self.parts.append({'kind': 'frozen_low_component', 'source_component': component_id,
                           'vertex_start': min(mapping.values()), 'vertex_count': len(mapping),
                           'source_face_start': first, 'face_count': len(group['faces'])})

    def finish(self):
        obj = bpy.data.objects[self.name]
        old, old_name = obj.data, obj.data.name
        assert all(abs(obj.matrix_world[i][j]-(1 if i == j else 0)) < 1e-8 for i in range(4) for j in range(4))
        # FBX material slot order follows first polygon use. Sorting polygons
        # keeps the original slots without inserting dummy/degenerate faces.
        order = sorted(range(len(self.faces)), key=lambda i: self.faces[i]['mi'])
        reverse = {old_index: new_index for new_index, old_index in enumerate(order)}
        me = bpy.data.meshes.new(self.name+'_candidate')
        me.from_pydata(self.v, [], [self.faces[i]['vs'] for i in order])
        for material in self.materials:
            me.materials.append(bpy.data.materials[material])
        uv = me.uv_layers.new(name=self.uv_names[0])
        name, domain, dtype = self.colour_specs[0]
        colour = me.color_attributes.new(name=name, domain=domain, type=dtype)
        # Adding another CustomData layer may reallocate storage and invalidate
        # a previously held RNA UV-layer wrapper. Acquire it after all layers.
        uv = me.uv_layers[self.uv_names[0]]
        colour = me.color_attributes[name]
        for polygon, old_index in zip(me.polygons, order):
            record = self.faces[old_index]
            polygon.material_index = record['mi']
            polygon.use_smooth = record['smooth']
            for j, loop_id in enumerate(polygon.loop_indices):
                uv.data[loop_id].uv = record['uv'][j]
                colour.data[loop_id].color = record['colours'][j]
        me.color_attributes.active_color = colour
        me.update()
        if self.name == 'Garden_TreeTrunks':
            normals = [tuple(n.vector) for n in me.corner_normals]
            for polygon, old_index in zip(me.polygons, order):
                frozen = self.faces[old_index]['normals']
                if frozen is not None:
                    for j, loop_id in enumerate(polygon.loop_indices):
                        normals[loop_id] = frozen[j]
            me.normals_split_custom_set(normals)
        obj.data = me
        if old.users == 0:
            bpy.data.meshes.remove(old)
        me.name = old_name
        for part in self.parts:
            first = part.pop('source_face_start')
            part['polygon_indices'] = [reverse[i] for i in range(first, first+part['face_count'])]
        return obj


def tube(builder, points, radii, material, sides, tree, kind):
    assert min(p.y-r for p, r in zip(points, radii)) >= LOW_Y, (tree, kind, min(p.y-r for p, r in zip(points, radii)))
    verts, faces = [], []
    previous = None
    for i, (point, radius) in enumerate(zip(points, radii)):
        tangent = (points[min(i+1, len(points)-1)]-points[max(0, i-1)]).normalized()
        if previous is None:
            reference = Vector((0, 0, 1)) if abs(tangent.z) < .85 else Vector((1, 0, 0))
            side = tangent.cross(reference).normalized()
        else:
            side = (previous-tangent*previous.dot(tangent)).normalized()
        other = tangent.cross(side).normalized()
        previous = side
        for j in range(sides):
            angle = j*math.tau/sides
            verts.append(point+radius*(side*math.cos(angle)+other*math.sin(angle)))
        if i:
            for j in range(sides):
                # Right-handed cross section, outward tube winding.
                a, b = (i-1)*sides+j, (i-1)*sides+(j+1)%sides
                faces.append((a, b, i*sides+(j+1)%sides, i*sides+j))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    builder.add(verts, faces, material, [(1, 1, 1, 1)]*len(verts), kind, tree)


def quadratic(a, control, b, t):
    return a*((1-t)**2)+control*(2*t*(1-t))+b*(t*t)


def leaf(builder, root, direction, length, half_width, material, tree, narrow=False):
    d = direction.normalized()
    outward = root-BASES[tree]
    outward.y = 0
    if outward.length < 1e-6:
        outward = Vector((1, 0, 0))
    preferred = (UP*.72+outward.normalized()*.28).normalized()
    n = preferred-d*preferred.dot(d)
    if n.length < .1:
        n = Vector((0, 0, 1))-d*d.z
    n.normalize()
    n = Quaternion(d, RNG.uniform(-.52, .52)) @ n
    side = n.cross(d).normalized()
    roll = RNG.uniform(-.10, .10)*length
    bow = length*RNG.uniform(.045, .13)
    droop = length*RNG.uniform(.10, .22)
    def axis(t):
        return root+d*(length*t)+n*(bow*math.sin(math.pi*t)-droop*t*t)+side*(roll*t*t)
    # Curved, pointed blade; leaf base is exactly attached to a twig station.
    if narrow:
        outline = [(0,0), (.30, .70), (.69,.52), (1,0), (.69,-.52), (.30,-.70)]
    else:
        outline = [(0,0), (.22,.68), (.52,1), (.80,.50), (1,0), (.80,-.48), (.52,-.94), (.22,-.64)]
    verts = [axis(t)+side*(half_width*w)-n*(half_width*.10*abs(w)) for t,w in outline]
    verts.append(axis(.48)+n*half_width*.09)
    center = len(verts)-1
    faces = [(center, i, (i+1)%center) for i in range(center)]
    tint = RNG.uniform(.87, 1.0)
    colours = [(tint*(.95 if i in (0, center) else 1),)*3+(1,) for i in range(len(verts))]
    builder.add(verts, faces, material, colours, 'needle' if narrow else 'curved_leaf', tree, normal=n)


def spray(wood, canopy, edges, start, end, tree, serial, leaves=13):
    """A real terminal shoot with alternate attached leaves, not an ellipsoid scatter."""
    delta = end-start
    side = delta.cross(UP)
    if side.length < .01:
        side = Vector((1, 0, 0))
    side.normalize()
    control = start.lerp(end,.52)+UP*RNG.uniform(.035,.095)+side*RNG.uniform(-.055,.055)
    points = [quadratic(start,control,end,t) for t in (0,.33,.67,1)]
    tube(wood, points, [.007,.0055,.0034,.0016], 'BI_wood_light', 4, tree, 'leaf_support_shoot')
    colours = ['BI_leaf_dark','BI_leaf','BI_leaf_light'] if tree == 'broad' else ['BI_leaf','BI_leaf_gold','BI_leaf_light']
    for i in range(leaves):
        t = .15+.82*(i/(leaves-1))+RNG.uniform(-.018,.018)
        root = quadratic(start,control,end,t)
        tangent = (quadratic(start,control,end,min(1,t+.02))-quadratic(start,control,end,max(0,t-.02))).normalized()
        sign = 1 if i%2 else -1
        horizontal = side*(sign*RNG.uniform(.75,1.0))+tangent*RNG.uniform(.13,.55)
        direction = (horizontal+UP*RNG.uniform(-.48,.58)).normalized()
        length = RNG.uniform(.125,.195) if tree == 'broad' else RNG.uniform(.095,.155)
        # Smaller leaves at the ends prevent a uniform exterior comb.
        length *= .82+.18*math.sin(math.pi*t)
        half_width = length*RNG.uniform(.23,.31)
        material = RNG.choices(colours,[2,5,2])[0]
        destination = canopy
        if serial%11 == 0 and i >= leaves-2:
            material = 'BI_leaf_gold' if tree == 'gold' else RNG.choice(['BI_leaf','BI_leaf_light'])
            destination = edges
        leaf(destination,root,direction,length,half_width,material,tree)


def deciduous(wood, canopy, edges, tree):
    base = BASES[tree]
    gold = tree == 'gold'
    if gold:
        trunk_local = [(-.06,1.35,.10),(.10,1.98,.13),(-.05,2.65,.26),(-.22,3.12,.33)]
        radii = [.135,.095,.048,.008]
        # Smaller asymmetric crown, predominantly behind and above the moondial.
        endpoints = [(-.79,2.73,.24),(-.43,3.13,-.04),(.32,3.32,.33),
                     (.64,2.96,.71),(-.63,3.46,.73),(.05,3.62,.75),(-.91,3.05,.92)]
    else:
        trunk_local = [(-.06,1.35,.10),(.10,2.05,.07),(-.08,2.76,.12),(-.22,3.42,.20),(-.31,3.94,.28)]
        radii = [.135,.105,.071,.034,.006]
        endpoints = [(-1.10,2.71,-.39),(-.91,3.42,.69),(.48,3.57,-.48),
                     (-.43,3.96,-.12),(.49,3.82,.64),(-.22,3.08,-.82),
                     (-1.32,3.36,.06),(-.60,4.15,.59),(.16,4.19,.20)]
    trunk = [base+Vector(p) for p in trunk_local]
    tube(wood,trunk,radii,'BI_wood',9,tree,'upper_trunk')
    serial = 0
    for index, endpoint in enumerate(endpoints):
        end = base+Vector(endpoint)
        # Branch attachment climbs with the terminal lobe instead of all arms
        # radiating from a single umbrella joint.
        attach_y = max(1.62,min(end.y-.68,2.78 if not gold else 2.52))
        pair = next((j for j in range(len(trunk)-1) if trunk[j].y<=attach_y<=trunk[j+1].y),len(trunk)-2)
        t = (attach_y-trunk[pair].y)/(trunk[pair+1].y-trunk[pair].y)
        attach = trunk[pair].lerp(trunk[pair+1],t)
        control = attach.lerp(end,.52)+Vector((0,.16,0))
        points = [quadratic(attach,control,end,t) for t in (0,.28,.65,1)]
        tube(wood,points,[.061,.048,.030,.013],'BI_wood_light',7,tree,'primary_bough')
        outward = end-base
        outward.y = 0
        outward.normalize()
        tangent = Vector((-outward.z,0,outward.x))
        arms = 3 if gold else 4
        for arm in range(arms):
            phase = arm*math.tau/arms+index*.91+RNG.uniform(-.22,.22)
            reach = RNG.uniform(.22,.39) if gold else RNG.uniform(.26,.46)
            arm_end = end+outward*(math.cos(phase)*reach*.65)+tangent*(math.sin(phase)*reach)+UP*RNG.uniform(-.13,.34)
            arm_start = points[2].lerp(end,.62+.10*arm/arms)
            mid = arm_start.lerp(arm_end,.52)+UP*.065
            tube(wood,[arm_start,mid,arm_end],[.015,.009,.0035],'BI_wood_light',5,tree,'secondary_bough')
            # Directions vary through a lobe's depth and height. Deliberately
            # leave some terminal sectors empty rather than close a ball shell.
            count = RNG.choice([6,7,8])
            for shoot in range(count):
                theta = phase+shoot*2.39996+RNG.uniform(-.25,.25)
                shoot_start = mid.lerp(arm_end,.22+.74*shoot/max(1,count-1))
                d = outward*(.30+math.cos(theta)*.48)+tangent*(math.sin(theta)*.77)+UP*RNG.uniform(-.35,.80)
                d.normalize()
                shoot_end = shoot_start+d*RNG.uniform(.26,.44 if not gold else .36)
                spray(wood,canopy,edges,shoot_start,shoot_end,tree,serial,leaves=RNG.choice([12,13,14]))
                serial += 1


def cypress(wood, canopy, edges):
    tree, base = 'cypress', BASES['cypress']
    # Begin above the highest preserved axial segment; the old lower branches
    # and stem can legitimately extend above the 1.20m preservation threshold.
    points = [base+Vector(p) for p in [(-.04,2.48,.04),(.015,3.09,.035),(-.035,3.76,.01),(.07,4.40,.015)]]
    tube(wood,points,[.076,.052,.031,.0045],'BI_wood',9,tree,'upper_trunk')
    # No repeated horizontal tiers. Independent origins and asymmetric spans.
    heights = [1.41,1.52,1.69,1.78,1.95,2.08,2.19,2.35,2.43,2.61,2.76,
               2.87,3.01,3.13,3.24,3.39,3.51,3.61,3.77,3.91,4.03,4.16]
    for index, y in enumerate(heights):
        angle = index*2.39996+.35+RNG.uniform(-.24,.24)
        span = (.96*(1-(y-1.3)/3.28)**.72)*RNG.uniform(.79,1.16)
        outward = Vector((math.cos(angle),0,math.sin(angle)))
        sideways = Vector((-outward.z,0,outward.x))
        origin = base+Vector((-.015,y,.03))
        end = origin+outward*span+UP*RNG.uniform(.08,.23)
        control = origin.lerp(end,.55)-UP*.10
        branch = [quadratic(origin,control,end,t) for t in (0,.35,.70,1)]
        radius = .032*(span/.8)**.7
        tube(wood,branch,[radius,radius*.75,radius*.40,.0028],'BI_wood_light',5,tree,'conifer_bough')
        for spray_id in range(7):
            t = .24+.73*(spray_id/6)
            start = quadratic(origin,control,end,t)
            sign = (-1 if spray_id%2 else 1)
            direction = (outward*.35+sideways*sign*.62+UP*RNG.uniform(.08,.57)).normalized()
            reach = RNG.uniform(.20,.34)*(.68+.32*span/.8)
            tip = start+direction*reach
            mid = start.lerp(tip,.55)+UP*.028
            tube(wood,[start,mid,tip],[.006,.0034,.0012],'BI_wood_light',4,tree,'conifer_spray')
            for i in range(24):
                t2 = .06+.93*i/23
                root = quadratic(start,mid,tip,t2)
                turn = i*2.39996+index*.87
                nside = direction.cross(UP).normalized()
                leafdir = (direction*.35+nside*math.cos(turn)*.90+UP*math.sin(turn)*.52).normalized()
                # Short, overlapping scale/lanceolate foliage builds a real
                # lateral volume. First candidate's .07-.12m needles vanished
                # at normal play scale and left isolated bare branch rings.
                length = RNG.uniform(.115,.175)*(.83+.17*math.sin(math.pi*t2))
                material = RNG.choices(['BI_leaf_dark','BI_leaf_blue','BI_leaf'],[3,3,4])[0]
                leaf(canopy,root,leafdir,length,length*RNG.uniform(.19,.27),material,tree,narrow=True)
    # Several slender upright leader sprays break the cut-off conical tip.
    for index in range(6):
        a = index*2.39996
        origin = points[-2].lerp(points[-1],.30+.11*index)
        end = origin+Vector((math.cos(a)*.12,.22,math.sin(a)*.12))
        mid = origin.lerp(end,.5)+UP*.035
        tube(wood,[origin,mid,end],[.005,.003,.0012],'BI_wood_light',4,tree,'conifer_leader')
        for i in range(16):
            p = quadratic(origin,mid,end,.10+.86*i/15)
            phi = i*2.39996+a
            leaf(canopy,p,Vector((math.cos(phi),.30,math.sin(phi))),RNG.uniform(.06,.09),.009,
                 RNG.choice(['BI_leaf_blue','BI_leaf','BI_leaf_dark']),tree,narrow=True)


def settle_deciduous_crowns(builders):
    """Keep frozen bases and new root joints; bring crowns back into framing."""
    def smooth(low,high,x):
        t=max(0,min(1,(x-low)/(high-low)))
        return t*t*(3-2*t)
    for builder in builders:
        for part in builder.parts:
            tree=part.get('tree')
            if tree not in ('broad','gold'):
                continue
            start,end=part['vertex_start'],part['vertex_start']+part['vertex_count']
            for index in range(start,end):
                point=U(builder.v[index])
                if tree=='broad':
                    # All original low components are excluded. New start-ring
                    # vertices remain below 1.40m and stay exactly at the join.
                    if point.y>1.40:point.y=1.40+(point.y-1.40)*.80
                else:
                    old_y=point.y
                    point.y-=.42*smooth(1.60,2.60,old_y)
                    # Shift peripheral crown and fine branchwork gradually;
                    # leave trunk/primary attachment axes unmoved in XZ.
                    if part['kind']!='upper_trunk':
                        r=math.hypot(point.x-(BASES['gold'].x-.05),point.z-(BASES['gold'].z+.20))
                        point.z+=.18*smooth(.25,.75,r)*smooth(1.80,2.50,old_y)
                builder.v[index]=B(point)
            for fi in range(part['source_face_start'],part['source_face_start']+part['face_count']):
                face=builder.faces[fi]
                face['uv']=[((builder.v[i].x+9)/18,(-builder.v[i].y+9)/18) for i in face['vs']]


def check_low_preservation(builder, source_audit):
    mesh = bpy.data.objects[builder.name].data
    source_records = {r['source_component']: r for r in source_audit['components'] if r['keep_entire_component']}
    items = []
    for part in builder.parts:
        if part['kind'] != 'frozen_low_component':
            continue
        group = {'vertices': list(range(part['vertex_start'],part['vertex_start']+part['vertex_count'])),
                 'faces': part['polygon_indices']}
        actual = digest(component_payload(mesh,group))
        expected = source_records[part['source_component']]['geometry_uv_colour_normal_sha256']
        items.append({'source_component': part['source_component'], 'expected_sha256': expected,
                      'actual_sha256': actual, 'exact': actual == expected})
    # Blender custom normals use internal packed representation. Any round-trip
    # normal change is measured separately; geometry/UV/colour may still be exact.
    return items


def generate(preserved, source_audit):
    baseline = json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
    for name in ['island.blend','island.fbx','island.glb']:
        assert sha(BASE/name) == baseline['sha256'][name]
    before = {o.name:audit.fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    anchors = audit.anchors()
    materials = audit.used_materials()
    matrices = {o.name:[list(r) for r in o.matrix_world] for o in bpy.context.scene.objects if o.type=='MESH'}
    wood = TreeMesh('Garden_TreeTrunks')
    canopy = TreeMesh('Garden_TreeCanopies')
    edges = TreeMesh('Garden_CanopyLeafEdges')
    original = bpy.data.objects[wood.name].data
    # Capture full payload, because mesh datablock is replaced later.
    kept_source = {i:component_payload(original,group) for i,group in preserved}
    for index, group in preserved:
        wood.keep(original,group,index)
    deciduous(wood,canopy,edges,'broad')
    deciduous(wood,canopy,edges,'gold')
    cypress(wood,canopy,edges)
    settle_deciduous_crowns((wood,canopy,edges))
    for builder in (wood,canopy,edges):
        builder.finish()
    low_checks = []
    for part in wood.parts:
        if part['kind'] != 'frozen_low_component':
            continue
        mesh = bpy.data.objects[wood.name].data
        group = {'vertices':list(range(part['vertex_start'],part['vertex_start']+part['vertex_count'])),
                 'faces':part['polygon_indices']}
        actual = component_payload(mesh,group)
        expected = kept_source[part['source_component']]
        max_delta = max((Vector(a)-Vector(b)).length for fa,fb in zip(actual['faces'],expected['faces'])
                        for a,b in zip(fa['normals'],fb['normals']))
        full_exact = actual == expected
        for payload in (actual,expected):
            for face in payload['faces']:
                del face['normals']
        exact = actual == expected
        if not exact:
            differences=[]
            if actual['vertices'] != expected['vertices']:
                differences.append(['vertices',actual['vertices'],expected['vertices']])
            for fi,(af,ef) in enumerate(zip(actual['faces'],expected['faces'])):
                for key in af:
                    if af[key] != ef[key]:
                        differences.append([fi,key,af[key],ef[key]])
            (OUT/'preservation-debug.json').write_text(json.dumps(differences[:8],indent=2),encoding='utf-8')
        assert exact and max_delta < 1e-4, (part['source_component'], exact, max_delta)
        low_checks.append({'source_component':part['source_component'],'geometry_uv_colour_exact':exact,
                           'normal_vector_max_error':max_delta,'including_normals_exact':full_exact,
                           'expected_geometry_uv_colour_sha256':digest(expected),'actual_geometry_uv_colour_sha256':digest(actual)})
    assert len(before) == 26 and before == {o.name:audit.fingerprint(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in TARGETS}
    assert anchors == audit.anchors() and len(anchors) == 14
    assert materials == audit.used_materials()
    assert matrices == {o.name:[list(r) for r in o.matrix_world] for o in bpy.context.scene.objects if o.type=='MESH'}
    objects, total = [], 0
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        me=obj.data
        me.calc_loop_triangles()
        count=len(me.loop_triangles)
        total+=count
        assert all(t.area>1e-12 for t in me.loop_triangles), obj.name+' zero-area triangle'
        assert len({tuple(sorted(t.vertices)) for t in me.loop_triangles})==count, obj.name+' duplicate triangle'
        assert all(math.isfinite(x) for v in me.vertices for x in v.co)
        coords=[U(obj.matrix_world@v.co) for v in me.vertices]
        objects.append({'name':obj.name,'vertices':len(me.vertices),'triangles':count,'materials':[m.name for m in me.materials],
                        'bounds_unity':[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]]})
    assert len(objects)==29 and total<=550000,total
    (OUT/'textures').mkdir(exist_ok=True)
    texture_names=['meadow-watercolor.png','meadow-normal.png']
    for name in texture_names:
        shutil.copy2(BASE/'textures'/name,OUT/'textures'/name)
    for image in bpy.data.images:
        name=Path(image.filepath).name
        if name in texture_names:
            image.filepath=str(OUT/'textures'/name)
    bpy.context.scene['tree_revision']='world-v12 / game v13: settled deciduous crowns, fuller irregular conifer'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
    for obj in bpy.context.scene.objects:
        obj.select_set(obj.type in ['MESH','EMPTY'])
    bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,
        mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,path_mode='COPY',embed_textures=True,colors_type='LINEAR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,
        export_apply=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    files=['island.blend','island.fbx','island.glb']+['textures/'+n for n in texture_names]
    manifest={'revision':'world-v12','game_candidate':'v13','source':'world-v10','triangles':total,
        'source_triangles':baseline['triangles'],'triangle_change':total-baseline['triangles'],'triangle_guardrail':550000,
        'objects':objects,'changed_meshes':sorted(TARGETS),'unchanged_non_target_fingerprints':before,
        'all_source_object_matrices':matrices,'anchors_unity':baseline['anchors_unity'],'anchors_frozen':anchors,
        'source_used_material_fingerprints':materials,'materials_added':[],'materials_changed':[],'renderer_count_change':0,
        'parts':{b.name:b.parts for b in (wood,canopy,edges)},'low_trunk_component_checks':low_checks,
        'low_collision_threshold_unity_y':LOW_Y,'new_wood_min_y':min(U(v).y for b in (wood,) for p in b.parts if p['kind']!='frozen_low_component' for v in b.v[p['vertex_start']:p['vertex_start']+p['vertex_count']]),
        'collision_limits':'Low original edge-connected components are retained. New upper branches change the TreeTrunks obstacle collider; runtime probes still required.',
        'design_changes':['Preserve all 26 non-tree meshes, object transforms, materials, texture bytes and 14 anchors.',
          'Replace level crowns with uneven branch-supported lobes and attached alternate curved leaves; no leaf images or shader changes.',
          'Broadleaf has tall and low pockets with gaps; gold crown is narrower, raised and behind the moondial; conifer has irregular separate bough origins and narrow curved foliage.',
          'Revision after world-v11 visual rejection: compress only new broad-tree geometry above 1.40m to 80% height; lower upper gold crown 0.42m and move peripheral fine branchwork rearward at most 0.18m.',
          'Conifer uses 22 non-tiered bough origins and 24 attached curved scale leaves per secondary spray; restore middle/lower crown volume without giant horizontal leaf sheets.',
          'Preserve original low trunk/root components exactly in position/topology/UV/colour; measure any custom-normal packing drift.'],
        'files':files,'sha256':{n:sha(OUT/n) for n in files},'baseline_sha256':baseline['sha256'],
        'textures_byte_identical':{n:sha(OUT/'textures'/n)==sha(BASE/'textures'/n) for n in texture_names},
        'verification_pending':True,'visual_review_pending':True}
    (OUT/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WORLD_V12_EXPORTED',total,'delta',total-baseline['triangles'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
    preserved,source_audit=inspect_source()
    if not args.inspect_only:
        generate(preserved,source_audit)
