"""Frozen-v6 derivative: four restrained planar Hero rocks, no scene regeneration."""
import bpy, bmesh, math, json, hashlib, shutil, argparse, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/world-v6'
OUT=ROOT/'art/generated/world-v7'; OUT.mkdir(parents=True,exist_ok=True)
args=argparse.ArgumentParser()
args.add_argument('--preview',choices=['none','gray','color'],default='none')
args.add_argument('--export',action='store_true')
opts=args.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
scene=bpy.context.scene
baseline=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
HERO='Garden_HeroBoulders'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return Vector((p[0],p[2],-p[1]))
def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def smin(a,b,k):
    h=max(0.,min(1.,.5+.5*(b-a)/k));return b+(a-b)*h-k*h*(1-h)
def fingerprint(obj):
    mesh=obj.data
    payload={'matrix':[list(r) for r in obj.matrix_world],
        'vertices':[list(v.co) for v in mesh.vertices],
        'faces':[list(p.vertices) for p in mesh.polygons],
        'mi':[p.material_index for p in mesh.polygons],
        'smooth':[p.use_smooth for p in mesh.polygons],
        'mats':[m.name for m in mesh.materials],
        'uv':[[list(d.uv) for d in uv.data] for uv in mesh.uv_layers],
        'colours':[[a.name,a.domain,a.data_type,[list(c.color) for c in a.data]] for a in mesh.color_attributes]}
    return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

old_fingerprints={o.name:fingerprint(o) for o in scene.objects if o.type=='MESH' and o.name!=HERO}
old_anchors={o.name:[list(r) for r in o.matrix_world] for o in scene.objects if o.type=='EMPTY'}
obj=bpy.data.objects[HERO]; mesh=obj.data
old_coords=[v.co.copy() for v in mesh.vertices]
old_faces=[tuple(p.vertices) for p in mesh.polygons]
old_bvh=BVHTree.FromPolygons(old_coords,old_faces,all_triangles=True)

# Cut only inward from the frozen shape. Preserve the buried foot and low rim;
# upper silhouette vertices may recede inside the existing projected footprint.
specs=[(-1.20,-5.15,.46,.29,.41,.36),
       (1.20,-4.20,.51,.36,.44,-.48),
       (2.00,-2.70,.61,.39,.47,.70),
       (-2.30,-2.20,.43,.27,.37,-.24)]
components=[]; adjacency=[[] for _ in mesh.vertices]
for e in mesh.edges:
    a,b=e.vertices;adjacency[a].append(b);adjacency[b].append(a)
seen=set()
for i in range(len(mesh.vertices)):
    if i in seen:continue
    component=[];stack=[i];seen.add(i)
    while stack:
        j=stack.pop();component.append(j)
        for k in adjacency[j]:
            if k not in seen:seen.add(k);stack.append(k)
    components.append(component)
assert len(components)==4
components.sort(key=lambda c:min(c))
vertex_plane={};vertex_cut={};vertex_cut_depth={};vertex_pigment={};plane_normals={};vertex_targets={};rock_reports=[]
for rock_index,(ids,spec) in enumerate(zip(components,specs)):
    cx,cz,rx,ry,rz,turn=spec;gy=baseline['hero_boulders'][rock_index]['center_unity'][1]
    base_y=gy+ry*.47;sy=ry*.91;cs=math.cos(turn);sn=math.sin(turn)
    # Supporting planes: top plus broad near-vertical fractures. Small differences
    # are intentional sculpture parameters, not another layer of random noise.
    planes=[(.10+rock_index*.018,1.,-.11,.73+[.01,-.035,.025,-.015][rock_index]),
            (.12,.18,-.98,.75+[0,.025,-.025,.01][rock_index]),
            (.98,.15,.12,.78+[.015,-.025,.015,0][rock_index]),
            (-.97,.20,.18,.79+[0,.025,-.02,-.01][rock_index]),
            (.10,.20,.98,.83+[.015,-.01,.025,0][rock_index])]
    for pi,(a,b,c,d) in enumerate(planes):
        n=Vector((a/rx,b/sy,c/rz)).normalized()
        n=Vector((n.x*cs-n.z*sn,n.y,n.x*sn+n.z*cs))
        plane_normals[(rock_index,pi)]=B(n).normalized()
    moved=0;kept_low=0;cut_distance=[];ids_set=set(ids)
    for vi in ids:
        old=U(old_coords[vi]);dx=old.x-cx;dz=old.z-cz
        x=dx*cs+dz*sn;z=-dx*sn+dz*cs;u=x/rx;w=z/rz;v=(old.y-base_y)/sy
        local=Vector((u,v,w))
        ratios=[]
        for a,b,c,d in planes:
            dot=a*u+b*v+c*w;ratios.append(d/dot if dot>.05 else 10.)
        pi=min(range(len(ratios)),key=lambda k:ratios[k]);ratio=min(1.,ratios[pi])
        for ci,value in enumerate(ratios):
            if ci!=pi:ratio=smin(ratio,value,.012)
        ratio=min(1.,max(.4,ratio))
        carved=local*ratio
        # A restrained, incomplete bedding step on the camera-facing flank.
        # This is a shallow offset of one layer, not a ring of Gaussian dents.
        front=smooth(-.18,-.58,w)
        extent=1-smooth(.38,.72,abs(u+.10))
        layer_y=gy+ry*(.69+.08*u)+[.0,.018,-.012,.01][rock_index]
        lower_layer=1-smooth(-.012,.012,old.y-layer_y)
        layer_depth=.0055*front*extent*lower_layer
        # Preserve the complete lower 8 cm above authored terrain, and use a
        # short transition only where a fracture approaches that frozen rim.
        foot_fade=smooth(gy+.08,gy+.16,old.y)
        px=carved.x*rx;pz=carved.z*rz
        candidate=Vector((cx+px*cs-pz*sn,base_y+carved.y*sy,cz+px*sn+pz*cs))
        # Inset the lower section of one front flank, retaining the top section
        # as a very shallow bedding lip. No full-circumference crease.
        candidate-=U(plane_normals[(rock_index,1)])*layer_depth
        candidate=old.lerp(candidate,foot_fade)
        mesh.vertices[vi].co=B(candidate)
        cut_depth=(candidate-old).length;was_cut=cut_depth>.00001
        vertex_cut[vi]=was_cut;vertex_plane[vi]=(rock_index,pi)
        vertex_cut_depth[vi]=cut_depth
        target=Vector((0,0,0))
        for ci,value in enumerate(ratios):
            target+=plane_normals[(rock_index,ci)]*math.exp(-min(60,max(0,(value-ratios[pi])/.018)))
        vertex_targets[vi]=target.normalized()
        if was_cut:moved+=1;cut_distance.append(cut_depth)
        if old.y<=gy+.08:
            assert mesh.vertices[vi].co==old_coords[vi]
            kept_low+=1
        # Quiet mineral tone and slight layer variation; no centimeter-scale
        # noisy pigment. RGB remains a linear multiplier, alpha stays opaque.
        pigment=.91+.018*math.sin(u*1.4+w*.8+rock_index*.7)-.025*front*extent*lower_layer
        vertex_pigment[vi]=(pigment,pigment,pigment)
    points=[U(mesh.vertices[i].co) for i in ids]
    rock_reports.append({'index':rock_index,'center_unity':[cx,gy,cz],
      'bounds_min_unity':[min(p[k] for p in points) for k in range(3)],
      'bounds_max_unity':[max(p[k] for p in points) for k in range(3)],
      'route_centerline_clearance_metres':baseline['hero_boulders'][rock_index]['route_centerline_clearance_metres'],
      'moved_upper_vertices':moved,'frozen_lower_vertices':kept_low,
      'maximum_inward_cut_metres':max(cut_distance,default=0),
      'plane_parameters':planes,'projected_vertices_identical':False})

mesh.update()
# Continuous corner normals approach the authored supporting-plane normal in
# broad interiors; edge bands blend toward the actual geometry. Never switch
# the shading abruptly based on which side of a tiny triangle a pixel occupies.
normal_values=[tuple(n.vector) for n in mesh.corner_normals]
flat_region_faces=0
for p in mesh.polygons:
    keys={vertex_plane[v] for v in p.vertices}
    if len(keys)==1 and all(vertex_cut[v] for v in p.vertices):
        key=next(iter(keys));target=plane_normals[key]
        if p.normal.dot(target)>.995:flat_region_faces+=1
for loop in mesh.loops:
    vi=loop.vertex_index;original=Vector(normal_values[loop.index])
    amount=smooth(.002,.018,vertex_cut_depth[vi])
    normal_values[loop.index]=tuple(original.lerp(vertex_targets[vi],amount).normalized())
mesh.normals_split_custom_set(normal_values)
attr=mesh.color_attributes.active_color
for loop in mesh.loops:attr.data[loop.index].color=(*vertex_pigment[loop.vertex_index],1.)

assert [tuple(p.vertices) for p in mesh.polygons]==old_faces
assert len(mesh.loop_triangles)==0 or len(mesh.loop_triangles)<=20480
assert all(fingerprint(bpy.data.objects[name])==fp for name,fp in old_fingerprints.items())
assert old_anchors=={o.name:[list(r) for r in o.matrix_world] for o in scene.objects if o.type=='EMPTY'}
mesh.calc_loop_triangles();assert len(mesh.loop_triangles)==20480
assert all(t.area>1e-12 for t in mesh.loop_triangles)

# Every candidate vertex/edge-midpoint/triangle-centroid projection must remain
# within the old actual footprint. Ignore tiny numerical silhouette hits via
# a 0.25mm nearest-surface check, never a broad radius approximation.
projected_samples=[]
for v in mesh.vertices:projected_samples.append(v.co.copy())
for e in mesh.edges:projected_samples.append((mesh.vertices[e.vertices[0]].co+mesh.vertices[e.vertices[1]].co)*.5)
for p in mesh.polygons:projected_samples.append(p.center.copy())
outside=0
for co in projected_samples:
    if old_bvh.ray_cast(Vector((co.x,co.y,1.5)),Vector((0,0,-1)),2)[0] is not None:continue
    # Exact old silhouette points can be rejected by a tangent ray. A second
    # ray shifted 0.25mm toward this rock's unchanged center resolves that.
    rock=min(rock_reports,key=lambda r:(co.x-r['center_unity'][0])**2+(-co.y-r['center_unity'][2])**2)
    inward=Vector((rock['center_unity'][0]-co.x,-rock['center_unity'][2]-co.y,0)).normalized()*.00025
    if old_bvh.ray_cast(Vector((co.x+inward.x,co.y+inward.y,1.5)),Vector((0,0,-1)),2)[0] is None:outside+=1
assert outside==0,'Candidate expands beyond frozen footprint'
bvh=BVHTree.FromPolygons([v.co for v in mesh.vertices],old_faces,all_triangles=True)
plant_checks=[]
for entry in baseline['plant_cleanup']:
    plant=bpy.data.objects[entry['mesh']];hits=0
    for v in plant.data.vertices:
        co=plant.matrix_world@v.co
        if not any(r['bounds_min_unity'][0]-.001<=co.x<=r['bounds_max_unity'][0]+.001 and r['bounds_min_unity'][2]-.001<=-co.y<=r['bounds_max_unity'][2]+.001 for r in rock_reports):continue
        if bvh.ray_cast(Vector((co.x,co.y,1.5)),Vector((0,0,-1)),2)[0] is not None:hits+=1
    plant_checks.append({'mesh':plant.name,'vertices_projecting_into_hero':hits})
assert all(p['vertices_projecting_into_hero']==0 for p in plant_checks)

(OUT/'textures').mkdir(exist_ok=True)
for name in ['meadow-watercolor.png','meadow-normal.png']:shutil.copyfile(BASE/'textures'/name,OUT/'textures'/name)
for img in bpy.data.images:
    if img.source=='FILE':
        filename=Path(bpy.path.abspath(img.filepath)).name
        if (OUT/'textures'/filename).exists():img.filepath=str(OUT/'textures'/filename)

report=json.loads(json.dumps(baseline));report['revision']='world-v7-candidate: broad restrained Hero fracture planes'
report['triangle_budget']=412815
report['design_changes']=['Load frozen world-v6; only four Hero rock upper vertices, custom corner normals and quiet linear vertex tint change.','Hero upper surfaces recede within the old actual projected footprint; lower rim, all 28 other mesh geometry/colour/UV/material fingerprints and 14 anchors are unchanged.','No random displacement, new texture, material or renderer. One partial shallow bedding step per rock. Render mesh collision is changed locally inward and must be runtime-tested.']
report['hero_boulders']=rock_reports
report['unchanged_world_v6_fingerprints']=old_fingerprints
report['hero_form_checks']={'same_projected_vertices':False,'projected_samples_checked':len(projected_samples),'samples_outside_baseline_footprint':outside,'silhouette_tangent_tolerance_metres':.00025,'same_hero_topology':True,'same_lower_rim':True,'explicit_planar_normal_faces':flat_region_faces,'baseline_hero_triangles':20480,'hero_triangles':20480,'plant_checks':plant_checks}
report['preview_scope']='512px, six-sample CPU Blender form inspections only; Unity material and collision review still required.'
for item in report['vertex_colors']:
    if item['mesh']==HERO:
        vals=[c for p in vertex_pigment.values() for c in p]
        item['min_rgb']=min(vals);item['max_rgb']=max(vals);item['purpose']='quiet mineral and restrained layer tint; no random noise'
report['files']=['island.blend']
scene['hero_revision']='world-v7 broad planes inside frozen projected footprint'
for o in scene.objects:o.select_set(o.type in {'MESH','EMPTY'})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
if opts.export:
    bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,path_mode='COPY',embed_textures=True,colors_type='LINEAR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
    report['files']+=['island.fbx','island.glb']
for previous in sorted(OUT.glob('gray-*.png')):report['files'].append(previous.name)
report['sha256']={name:sha(OUT/name) for name in report['files']+['textures/meadow-watercolor.png','textures/meadow-normal.png']}
(OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORLD_V7_FORM_READY',flat_region_faces,rock_reports,flush=True)

if opts.preview!='none':
    for light in [o for o in scene.objects if o.type=='LIGHT']:light.hide_render=True
    world=bpy.data.worlds.new('V7 neutral form inspection');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.50,.50,.50,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.22
    for name,pos,power,size in [('Neutral side key',(-4,5,-7),1000,3),('Neutral fill',(4,6,2),500,6)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
        light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=B(pos)
        light.rotation_euler=(B((0,.2,-3))-light.location).to_track_quat('-Z','Y').to_euler()
    if opts.preview=='gray':
        gray=bpy.data.materials.new('Preview only neutral Hero');gray.use_nodes=True
        bs=gray.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.36,.36,.36,1);bs.inputs['Roughness'].default_value=.85
        for i in range(len(mesh.materials)):mesh.materials[i]=gray
    data=bpy.data.cameras.new('V7 rock inspection');cam=bpy.data.objects.new('V7 rock inspection',data);scene.collection.objects.link(cam);scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=6;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.resolution_x=512;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.2
    for name,pos,target,lens,height in [('path-context',(0,1.72,-6.5),(0,.36,-1.9),30,320),('rock-low',(2.5,.65,-5.45),(1.2,.27,-4.2),48,512)]:
        cam.location=B(pos);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.lens=lens
        scene.render.resolution_y=height;filename=f'{opts.preview}-{name}.png';scene.render.filepath=str(OUT/filename)
        bpy.ops.render.render(write_still=True)
        report['files'].append(filename);report['sha256'][filename]=sha(OUT/filename)
    (OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORLD_V7_COMPLETE',flush=True)
