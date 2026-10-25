"""Offline actual-mesh review. Reads the saved island and never overwrites it."""
import sys
sys.dont_write_bytecode=True
import bpy
import json
import math
import hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import importlib.util

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/env-v1'
BLEND=BASE/'preview/island_offline.blend'
DEST=BASE/'props/integrated-geometry-review.json'
spec=importlib.util.spec_from_file_location('checked_layout',ROOT/'art/blender/env_v1_layout.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
data=json.loads((BASE/'staging/scene-input.json').read_text(encoding='utf-8-sig'))
assembly_manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8-sig'))
scene_hash=hashlib.sha256(BLEND.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=2
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
anchors={a['name']:a for a in L.ANCHORS}
instance={a['name']:a for a in data['instances']}
instance.update({a['name']:dict(asset='copper_roadlamp',collider='solid',group='Lamp') for a in L.ANCHORS if a['kind']=='lamp'})

def bv(p):return Vector((p[0],-p[2],p[1]))
def uv(p):return [float(p.x),float(p.z),float(-p.y)]
def root_name(o):
    while o.parent:o=o.parent
    return o.name
def stamp(p):return hashlib.sha256(p.read_bytes()).hexdigest()

pose_mismatches=[]
for entry in data['instances']+[a for a in L.ANCHORS if a['kind']=='lamp']:
    obj=bpy.data.objects.get(entry['name'])
    if obj and 'position' in entry:
        actual=obj.matrix_world.translation
        error=(actual-bv(entry['position'])).length
        yaw_error=abs((math.degrees(obj.rotation_euler.z)-entry.get('yaw',0)+180)%360-180)
        scale_error=max(abs(v-entry.get('scale',1)) for v in obj.matrix_world.to_scale())
        if error>.001 or yaw_error>.001 or scale_error>.001:
            pose_mismatches.append({'name':entry['name'],'saved_scene_world':uv(actual),'current_contract_world':entry['position'],'position_error':error,'yaw_error_degrees':yaw_error,'maximum_scale_error':scale_error})

def lamp_origin(name):
    obj=bpy.data.objects.get(name)
    return obj.matrix_world.translation.copy() if obj else bv(anchors[name]['position'])

records=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    root=root_name(o)
    if root not in instance:continue
    eo=o.evaluated_get(dg);em=eo.to_mesh();em.calc_loop_triangles()
    verts=[o.matrix_world@v.co for v in em.vertices]
    tris=[tuple(t.vertices) for t in em.loop_triangles]
    mi=[t.material_index for t in em.loop_triangles]
    mats=[s.material.name if s.material else '' for s in o.material_slots]
    if verts and tris:
        records.append(dict(name=o.name,root=root,bvh=BVHTree.FromPolygons(verts,tris,all_triangles=True),
                            triangles=len(tris),mi=mi,mats=mats,group=instance[root].get('group',''),
                            collider=instance[root].get('collider','none'),asset=instance[root]['asset'],
                            bounds_min=[min(v[k] for v in verts) for k in range(3)],bounds_max=[max(v[k] for v in verts) for k in range(3)],
                            foot_vertices=[tuple(v) for v in verts] if '_Base' in o.name else []))
    eo.to_mesh_clear()
ground=[r for r in records if r['root']=='IslandTerrain' and r['name'].startswith('IslandGround')]
solid=[r for r in records if r['collider']=='solid']

def ray(a,b,selected=None,ignore=()):
    a,b=Vector(a),Vector(b);delta=b-a;distance=delta.length
    if distance<1e-8:return None
    direction=delta/distance;closest=None
    for r in records if selected is None else selected:
        if r['root'] in ignore:continue
        offset=Vector(r.get('translation',(0,0,0)))
        hit,normal,index,hit_distance=r['bvh'].ray_cast(a-offset,direction,distance)
        if hit is not None:hit+=offset
        if hit is not None and (closest is None or hit_distance<closest['distance']):
            mid=r['mi'][index];mat=r['mats'][mid] if mid<len(r['mats']) else ''
            closest={'root':r['root'],'object':r['name'],'world_position':uv(hit),'world_normal':uv(normal),'distance':float(hit_distance),'material':mat}
    return closest

def ground_at(x,z):
    return ray(bv((x,40,z)),bv((x,-10,z)),ground)

def marker(root,prefix):
    ob=bpy.data.objects.get(root)
    found=[o for o in ob.children_recursive if o.name.startswith(prefix)] if ob else []
    return uv(found[0].matrix_world.translation) if found else None

window_actual=marker('GrandmotherHouse','Marker_Window')
desk_actual=marker('GrandmotherHouse','Marker_Desk')
seat_actual=marker('GrandmotherHouse','Marker_ABo_Seat')
groups=[('WanFeng_Path','Anchor_Lamp_WanFeng','Target_Path'),('WanFeng_Bench','Anchor_Lamp_WanFeng','Target_Bench'),
        ('YueChuang_Window','Anchor_Lamp_YueChuang','Target_Window'),('YueChuang_Pier','Anchor_Lamp_YueChuang','Target_Pier'),
        ('GuiHang_Bench','Anchor_Lamp_GuiHang','Target_Bench')]
rays=[]
for name,lamp,target in groups:
    a=lamp_origin(lamp);b=bv(anchors[target]['position']);hit=ray(a,b,ignore=[lamp])
    remaining=(b-a).length-hit['distance'] if hit else None
    clear=hit is None or remaining<.075
    rays.append({'name':name,'lamp':lamp,'target':target,'origin':uv(a),'destination':uv(b),'first_hit':hit,'distance_before_target':remaining,'clear_to_receiver_tolerance_075m':clear})

window_rays=[]
if window_actual:
    a=lamp_origin('Anchor_Lamp_YueChuang');w=bv(window_actual)
    extended=w+(w-a).normalized()*.60
    hit=ray(a,extended,ignore=['Anchor_Lamp_YueChuang'])
    window_rays.append({'name':'through_real_window_center_and_60cm_inside','origin':uv(a),'destination':uv(extended),'first_hit':hit,
                        'passed_opening':hit is None or hit['distance']>(w-a).length+.03})
    # Sample nine points inside the physical aperture plane, deliberately below its frame.
    root=bpy.data.objects['GrandmotherHouse'];right=root.matrix_world.to_3x3()@Vector((1,0,0));right.normalize()
    for dx,dz in [(0,0),(.25,0),(-.25,0),(0,.25),(0,-.25),(.20,.20),(-.20,.20),(.20,-.20),(-.20,-.20)]:
        p=w+right*dx+Vector((0,0,dz));end=p+(p-a).normalized()*.10
        h=ray(a,end,ignore=['Anchor_Lamp_YueChuang'])
        window_rays.append({'name':f'aperture_sample_{dx}_{dz}','first_hit':h,'passed_opening':h is None or h['distance']>(p-a).length+.025})
    if desk_actual:
        d=bv(desk_actual);h=ray(a,d,ignore=['Anchor_Lamp_YueChuang'])
        window_rays.append({'name':'light_to_actual_ledger_desk','destination':desk_actual,'first_hit':h,'distance_before_target':(d-a).length-h['distance'] if h else None,'passed_opening':h is None or h['distance']>(w-a).length})

house_dims={'cottage_teal':(3.1,2.65),'cottage_ochre':(3.35,2.8),'cottage_slate':(2.75,2.8),'abode_grandma':(4,3.25)}
foundations=[]
for name,ins in instance.items():
    if ins['asset'] not in house_dims:continue
    o=bpy.data.objects.get(name)
    if o is None:continue
    w,d=house_dims[ins['asset']];samples=[]
    for xx,yy in [(-1,-1),(0,-1),(1,-1),(-1,0),(0,0),(1,0),(-1,1),(0,1),(1,1)]:
        p=o.matrix_world@Vector((xx*w*.5,yy*d*.5,0));q=uv(p);g=ground_at(q[0],q[2]);delta=g['world_position'][1]-q[1] if g else None
        samples.append({'foot':q,'terrain':g['world_position'] if g else None,'terrain_minus_base':delta})
    deltas=[s['terrain_minus_base'] for s in samples if s['terrain_minus_base'] is not None]
    foundations.append({'root':name,'samples':samples,'terrain_found_all_samples':len(deltas)==9,
                        'maximum_penetration':max(deltas) if deltas else None,'maximum_floating_gap':-min(deltas) if deltas else None,
                        'within_20cm':len(deltas)==9 and all(abs(v)<=.20 for v in deltas)})

paths=[]
camera_samples=[]
for route in L.PATHS:
    checks=[];last=None;max_slope=0
    for ai,(p,q) in enumerate(zip(route['points'],route['points'][1:])):
        delta=Vector((q[0]-p[0],q[2]-p[2]));n=max(1,math.ceil(delta.length/.40))
        for j in range(n+1):
            t=j/n;x=p[0]+(q[0]-p[0])*t;z=p[2]+(q[2]-p[2])*t
            g=ground_at(x,z)
            if not g:
                checks.append({'segment':ai,'xz':[x,z],'ground_missing':True});continue
            y=g['world_position'][1];foot=Vector((x,-z,y));blockers=[]
            # Thin radial mesh probes approximate a 0.3m-radius traveller; this is
            # a diagnostic, not a claim of swept-capsule Unity collision testing.
            for h in [.16,.85,1.45]:
                a=foot+Vector((0,0,h))
                for k in range(8):
                    b=a+Vector((math.cos(k*math.tau/8)*.30,math.sin(k*math.tau/8)*.30,0))
                    hit=ray(a,b,solid)
                    if hit and hit['root'] not in {x['root'] for x in blockers}:blockers.append(hit)
            vh=ray(foot+Vector((0,0,.08)),foot+Vector((0,0,1.65)),solid)
            if vh and vh['root'] not in {x['root'] for x in blockers}:blockers.append(vh)
            if blockers:checks.append({'segment':ai,'xz':[x,z],'ground_height':y,'capsule_probe_blockers':blockers})
            if last:
                run=math.hypot(x-last[0],z-last[2])
                if run>.01:max_slope=max(max_slope,abs(math.degrees(math.atan2(y-last[1],run))))
            last=[x,y,z]
            if j==n//2:camera_samples.append({'route':route['name'],'position':[x,y+1.1,z]})
    paths.append({'name':route['name'],'flagged_samples':checks,'maximum_sampled_terrain_slope_degrees':max_slope})

camera_views=[]
for a in L.ANCHORS:
    if a['kind']!='camera':continue
    target=a.get('lookAt')
    views=[]
    points=[{'name':n,'position':v['position']} for n,v in anchors.items() if n.startswith('Target_') or n=='Anchor_PlayerSpawn']
    for target in points:
        end=bv(target['position'])+Vector((0,0,.65));start=bv(a['position']);hit=ray(start,end)
        views.append({'target':target['name'],'first_hit':hit,'line_clear':hit is None or (end-start).length-hit['distance']<.15})
    camera_views.append({'camera':a['name'],'views':views})

piers=[]
for z in [2,3,5,6.5,8,9.5,10.8,11]:
    p=L.local(3,0,z);hit=ray(bv((p[0],20,p[2])),bv((p[0],-1,p[2])),[r for r in records if r['group']=='Pier'])
    probes=[]
    for dz in [-.06,.06]:
        pp=L.local(3,0,z+dz);probes.append(ray(bv((pp[0],20,pp[2])),bv((pp[0],-1,pp[2])),[r for r in records if r['group']=='Pier']))
    piers.append({'cape_z':z,'top_surface':hit,'neighboring_boards_6cm_either_side':probes})

def seg_distance(x,z,p,q):
    dx,dz=q[0]-p[0],q[2]-p[2];d=dx*dx+dz*dz
    t=max(0,min(1,((x-p[0])*dx+(z-p[2])*dz)/d)) if d else 0
    return math.hypot(x-p[0]-t*dx,z-p[2]-t*dz)

wan_candidates=[]
for x,z in [(1.2,4),(1.2,4.5),(1.2,5),(1.0,4.5),(1.35,4.5),(2,4.5),(2.5,4.5),(3,4.5),(3.8,5),(3.8,6),(1.2,8),(1.2,9)]:
    p=L.local(x,3.8,z);start=bv(p);hits=[]
    for target in ['Target_Path','Target_Bench']:
        end=bv(anchors[target]['position']);h=ray(start,end,ignore=['Anchor_Lamp_WanFeng'])
        hits.append({'target':target,'hit':h,'clear':h is None or (end-start).length-h['distance']<.075})
    route_gap=min(seg_distance(p[0],p[2],a,b)-route['width']/2-.24 for route in L.PATHS for a,b in zip(route['points'],route['points'][1:]))
    ground_hit=ground_at(p[0],p[2]);under=ground_hit['world_position'][1] if ground_hit else None
    wan_candidates.append({'cape_xz':[x,z],'light_rays':hits,'minimum_paved_edge_to_base':route_gap,'ground_height':under,'inside_pier_deck':1.8<=x<=4.2 and 2<=z<=11})

tree_candidates=[]
for name,x,z in [('LightTree_08',-5.5,0),('LightTree_08',-13.2,-1.5),('LightTree_10',-1.4,-5.8),('LightTree_10',-4.8,-9)]:
    src=[r for r in solid if r['root']==name]
    if not src:continue
    # Stage JSON may already describe the next revision while the saved scene is
    # still rendering. Translate from the actual saved root, never that JSON pose.
    old=uv(bpy.data.objects[name].matrix_world.translation);new=L.grounded(x,z);offset=bv(new)-bv(old)
    shifted=[dict(r,translation=tuple(offset)) for r in src];flags=[]
    for route in L.PATHS:
        for ai,(p,q) in enumerate(zip(route['points'],route['points'][1:])):
            n=max(1,math.ceil(math.hypot(q[0]-p[0],q[2]-p[2])/.4))
            for j in range(n+1):
                xx=p[0]+(q[0]-p[0])*j/n;zz=p[2]+(q[2]-p[2])*j/n;g=ground_at(xx,zz)
                if not g:continue
                foot=bv(g['world_position']);hit=None
                for h in [.16,.85,1.45]:
                    a=foot+Vector((0,0,h))
                    for k in range(8):
                        b=a+Vector((math.cos(k*math.tau/8)*.30,math.sin(k*math.tau/8)*.30,0))
                        hit=ray(a,b,shifted)
                        if hit:break
                    if hit:break
                if not hit:hit=ray(foot+Vector((0,0,.08)),foot+Vector((0,0,1.65)),shifted)
                if hit:flags.append({'path':route['name'],'xz':[xx,zz],'hit':hit})
    bases=[r for r in src if '_Base' in r['name']]
    footchecks=[]
    actual_vertex_gaps=[]
    for base in bases:
        mn=Vector(base['bounds_min'])+offset;mx=Vector(base['bounds_max'])+offset
        for xx,yy in [(mn.x,mn.y),(mn.x,mx.y),(mx.x,mn.y),(mx.x,mx.y)]:
            g=ground_at(xx,-yy)
            footchecks.append({'xz':[xx,-yy],'base_bottom':float(mn.z),'ground_y':g['world_position'][1] if g else None,'floating_gap':float(mn.z)-g['world_position'][1] if g else None})
        # Actual low base vertices, not empty bounding-box corners.
        for raw in base['foot_vertices']:
            if raw[2]>base['bounds_min'][2]+.10:continue
            p=Vector(raw)+offset;g=ground_at(p.x,-p.y)
            if g:actual_vertex_gaps.append({'position':uv(p),'gap':p.z-g['world_position'][1]})
    exact={'vertices_sampled':len(actual_vertex_gaps),'maximum_gap':max(actual_vertex_gaps,key=lambda a:a['gap']) if actual_vertex_gaps else None,'maximum_burial':min(actual_vertex_gaps,key=lambda a:a['gap']) if actual_vertex_gaps else None}
    tree_candidates.append({'name':name,'proposed_position':new,'path_flags':flags,'base_aabb_terrain_checks_conservative':footchecks,'actual_low_base_vertex_contact':exact,'base_bounding_widths':[{'x':r['bounds_max'][0]-r['bounds_min'][0],'z':r['bounds_max'][1]-r['bounds_min'][1]} for r in bases]})

present_roots={r['root'] for r in records}
missing=[{'name':a['name'],'asset':a['asset']} for a in data['instances'] if a['name'] not in present_roots]
source_contract={s['id']:s for s in assembly_manifest['sources']}
version_checks=[]
for model in data['models']:
    asset=model['id'];expected=source_contract.get(asset,{})
    fbx=BASE/'staging'/model['path'].split('Environment/',1)[1]
    fbx_hash=stamp(fbx)
    instance_triangles=[{'root':name,'triangles':sum(r['triangles'] for r in records if r['root']==name)} for name,entry in instance.items() if entry['asset']==asset and name in present_roots]
    version_checks.append({'asset':asset,'staged_fbx_sha256':fbx_hash,'manifest_sha256':expected.get('sha256'),'hash_matches_manifest':fbx_hash==expected.get('sha256'),
                           'expected_triangles_per_instance':expected.get('triangles'),'saved_scene_instances':instance_triangles,
                           'triangle_counts_match':all(a['triangles']==expected.get('triangles') for a in instance_triangles)})
pier_depths=[]
for name,entry in instance.items():
    if entry['asset'] not in ['pier_module','pier_end']:continue
    rr=[r for r in records if r['root']==name]
    if rr:pier_depths.append({'root':name,'lowest_world_y':min(r['bounds_min'][2] for r in rr),'highest_world_y':max(r['bounds_max'][2] for r in rr),'sea_y':-.16,'submerged_pile_depth':-.16-min(r['bounds_min'][2] for r in rr)})
waystone_candidates=[]
stone_records=[r for r in solid if r['root']=='PostmanWaystone']
if stone_records:
    old=bpy.data.objects['PostmanWaystone'].matrix_world.translation.copy()
    old_u=uv(old)
    npc=anchors['NPC_Postman']['position']
    # The three lanes cover the path centre and both walkable edges. Their
    # 0.30m radial probes leave the paved 1.75m road available to a person.
    stone_probes=[]
    for route in L.PATHS:
        for p,q in zip(route['points'],route['points'][1:]):
            dx,dz=q[0]-p[0],q[2]-p[2];length=math.hypot(dx,dz)
            if length<.001:continue
            n=max(1,math.ceil(length/.25))
            for j in range(n+1):
                x=p[0]+dx*j/n;z=p[2]+dz*j/n
                if math.hypot(x-old_u[0],z-old_u[2])>5:continue
                for lateral in [0,-max(0,route['width']/2-.30),max(0,route['width']/2-.30)]:
                    xx=x-dz/length*lateral;zz=z+dx/length*lateral;g=ground_at(xx,zz)
                    if g:stone_probes.append((route['name'],lateral,bv(g['world_position'])))
    for ix in range(-8,9):
        for iz in range(0,17):
            x=old_u[0]+ix*.10;z=old_u[2]+iz*.10;g=ground_at(x,z)
            if not g:continue
            candidate=bv(g['world_position']);offset=candidate-old
            shifted=[dict(r,translation=tuple(offset)) for r in stone_records]
            flags=[]
            for route,lateral,foot in stone_probes:
                if math.hypot(foot.x-x,-foot.y-z)>2.6:continue
                hittest=None
                for height in [.16,.85,1.45]:
                    a=foot+Vector((0,0,height))
                    for k in range(8):
                        b=a+Vector((math.cos(k*math.tau/8)*.30,math.sin(k*math.tau/8)*.30,0))
                        hittest=ray(a,b,shifted)
                        if hittest:break
                    if hittest:break
                if not hittest:hittest=ray(foot+Vector((0,0,.08)),foot+Vector((0,0,1.65)),shifted)
                if hittest:flags.append({'path':route,'lane_offset':lateral,'path_xz':[foot.x,-foot.y],'hit':hittest})
            waystone_candidates.append({'position':uv(candidate),'cape_xz':[x-L.CAPE[0],z-L.CAPE[2]],'move_xz':[x-old_u[0],z-old_u[2]],'move_distance':math.hypot(x-old_u[0],z-old_u[2]),'distance_to_postman':math.hypot(x-npc[0],z-npc[2]),'path_probe_count':len(flags),'first_flag':flags[0] if flags else None})
    waystone_candidates.sort(key=lambda c:(c['path_probe_count']!=0,c['move_distance'],c['distance_to_postman']))
walk_obstacles=[];low_steps=[]
for route in paths:
    for sample in route['flagged_samples']:
        if sample.get('ground_missing'):
            walk_obstacles.append({'path':route['name'],**sample});continue
        for hit in sample.get('capsule_probe_blockers',[]):
            step_height=hit['world_position'][1]-sample['ground_height']
            is_home_step=(route['name']=='CapeHome' and hit['root']=='GrandmotherHouse' and hit['material'].startswith('Stone_WarmLimestone') and hit['world_normal'][1]>.9 and 0<step_height<=.20)
            evidence={'path':route['name'],'xz':sample['xz'],'first_hit':hit,'height_above_terrain':step_height}
            (low_steps if is_home_step else walk_obstacles).append(evidence)
offline_summary={'lamp_rays_passed':sum(r['clear_to_receiver_tolerance_075m'] for r in rays),'lamp_ray_count':len(rays),
                 'window_samples_passed':sum(r['passed_opening'] for r in window_rays),'window_sample_count':len(window_rays),
                 'foundations_within_20cm':sum(h['within_20cm'] for h in foundations),'foundation_count':len(foundations),
                 'maximum_foundation_penetration_m':max(h['maximum_penetration'] for h in foundations),'maximum_foundation_floating_gap_m':max(h['maximum_floating_gap'] for h in foundations),
                 'remaining_sampled_walk_obstacles':walk_obstacles,'low_doorstep_surfaces_requiring_player_step_support':low_steps,
                 'pose_consistency_pass':not pose_mismatches,'staged_asset_hashes_pass':all(v['hash_matches_manifest'] for v in version_checks),
                 'saved_scene_asset_triangle_counts_pass':all(v['triangle_counts_match'] for v in version_checks),'all_expected_instances_present':not missing,
                 'all_pier_piles_extend_below_sea':bool(pier_depths) and all(d['submerged_pile_depth']>0 for d in pier_depths),
                 'environment_600000_triangle_budget_pass':sum(r['triangles'] for r in records)<=600000,
                 'unity_import_controller_render_performance_verified':False}
result={'scope':'Offline evaluated mesh BVH rays from the saved Blender assembly. No Unity operation, no scene/model modification, no swept-capsule engine test.',
 'snapshot_notes':sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [],
 'inputs':{'blend':str(BLEND.relative_to(ROOT)),'blend_sha256':scene_hash,'layout_sha256':stamp(ROOT/'art/blender/env_v1_layout.py'),'staging_sha256':stamp(BASE/'staging/scene-input.json'),'assembly_manifest_sha256':stamp(BASE/'manifest.json')},
 'summary':offline_summary,
 'input_pose_mismatches':pose_mismatches,'input_consistency':'mismatched_revisions_do_not_treat_as_final' if pose_mismatches else 'poses_match_current_contract',
 'mesh_count':len(records),'triangles':sum(r['triangles'] for r in records),'missing_instances':missing,'source_version_checks':version_checks,'pier_pile_world_depths':pier_depths,
 'anchor_actual_mesh':{'window_actual_world':window_actual,'window_target_error':(bv(window_actual)-bv(anchors['Target_Window']['position'])).length if window_actual else None,'seat_actual_world':seat_actual,'seat_anchor_error':(bv(seat_actual)-bv(anchors['NPC_ABo_Window']['position'])).length if seat_actual else None},
 'five_lamp_target_rays':rays,'real_window_aperture_rays':window_rays,'house_foundations':foundations,'walk_path_mesh_probes':paths,'camera_visibility_rays':camera_views,'pier_centerline_top_surfaces':piers,'wanfeng_position_candidates':wan_candidates,'tree_position_candidates':tree_candidates,'postman_waystone_candidates':waystone_candidates,
 'limitations':['Missing asset instances are excluded, so their future occlusion and collisions remain unverified.','Trees have evaluated render geometry, which may differ from future simplified Unity colliders.','Camera rays are visibility diagnostics; a blocked ray does not alone establish an unusable composition.','Walk probes use eight radial spokes and vertical samples, not a continuous capsule sweep.','Foundation check is nine points per wall footprint; narrow local protrusions may be missed.']}
DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'rays':[(r['name'],r['clear_to_receiver_tolerance_075m'],r['first_hit']) for r in rays],
                  'window_samples_passed':sum(r['passed_opening'] for r in window_rays),'window_samples_total':len(window_rays),
                  'foundations_outside_tolerance':[{'name':h['root'],'penetration':h['maximum_penetration'],'floating':h['maximum_floating_gap']} for h in foundations if not h['within_20cm']],
                  'paths':[(p['name'],len(p['flagged_samples']),p['maximum_sampled_terrain_slope_degrees']) for p in paths],
                  'missing':missing,'output':str(DEST.relative_to(ROOT))},ensure_ascii=False,indent=2),flush=True)
