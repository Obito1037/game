"""Independent read-only review of the environment layout and authored prop bounds."""
import sys
sys.dont_write_bytecode=True
import json
import math
import importlib.util
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art/blender/env_v1_layout.py'
spec=importlib.util.spec_from_file_location('reviewed_layout',SOURCE)
layout=importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
OUT=ROOT/'art/generated/env-v1/props'
props={x['asset_id']:x for x in json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))['assets']}
anchors={x['name']:x for x in layout.ANCHORS}
sites={x['name']:x for x in layout.PROP_SITES}

def world(site,p):
    a=math.radians(site.get('yaw',0));c=math.cos(a);s=math.sin(a);k=site.get('scale',1)
    return [site['position'][0]+k*(c*p[0]+s*p[2]),site['position'][1]+k*p[1],site['position'][2]+k*(-s*p[0]+c*p[2])]
def marker(site,name):
    return world(site,props[site['asset']]['markers'][name]['unity_xyz'])
def sub(a,b):return [x-y for x,y in zip(a,b)]
def length(a):return math.sqrt(sum(x*x for x in a))
def unit(a):return [x/length(a) for x in a]
def angle(a,b):return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(unit(a),unit(b)))))))
def segment_distance(p,a,b):
    dx,dz=b[0]-a[0],b[1]-a[1];n=dx*dx+dz*dz
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/n)) if n else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dz)
def inside(p,poly):
    sign=None
    for a,b in zip(poly,poly[1:]+poly[:1]):
        cross=(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        if abs(cross)<1e-8:continue
        s=cross>0
        if sign is None:sign=s
        elif sign!=s:return False
    return True
def point_polygon_distance(p,poly):
    return 0 if inside(p,poly) else min(segment_distance(p,a,b) for a,b in zip(poly,poly[1:]+poly[:1]))
def sample(a,b,step=.15):
    n=max(1,math.ceil(math.hypot(b[0]-a[0],b[2]-a[2])/step))
    return [[a[k]+(b[k]-a[k])*i/n for k in range(3)] for i in range(n+1)]
def wall_footprint(site):
    dims={'cottage_teal':(3.1,2.65),'cottage_ochre':(3.35,2.8),'cottage_slate':(2.75,2.8),'abode_grandma':(4,3.25)}
    w,d=dims[site['asset']]
    return [[p[0],p[2]] for p in [world(site,(x,0,z)) for x,z in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]]

bindings=[]
for site,mark,target in [('GrandmotherHouse','Marker_Window','Target_Window'),('GrandmotherHouse','Marker_ABo_Seat','NPC_ABo_Window'),('Flagpole','Marker_FlagpoleHook','Anchor_FlagpoleHook'),('KeeperBox','Marker_Seat','NPC_DengBo_Box'),('Bench','Marker_Seat','NPC_Bench')]:
    actual=marker(sites[site],mark);planned=anchors[target]['position'];delta=sub(planned,actual)
    bindings.append({'anchor':target,'prop':site,'marker':mark,'actual_world':actual,'actual_cape_local':sub(actual,layout.CAPE),'planned_world':planned,'offset_metres':length(delta),'delta_planned_minus_actual':delta})

house_reports=[]
for site in layout.HOUSES+[sites['GrandmotherHouse']]:
    footprint=wall_footprint(site)
    ground=[{'xz':p,'ground_height':layout.height(*p),'shore_fraction':layout.locate(*p)[0]/layout.locate(*p)[1]} for p in footprint]
    floor=site['position'][1]
    proximity=[]
    for path in layout.PATHS:
        mind=1e6;pos=None
        for a,b in zip(path['points'],path['points'][1:]):
            for p in sample(a,b):
                d=point_polygon_distance((p[0],p[2]),footprint)
                if d<mind:mind=d;pos=p
        if mind<path['width']*.5+.32:
            proximity.append({'path':path['name'],'minimum_centerline_to_wall_metres':mind,'path_half_width':path['width']*.5,'path_surface_overlaps_wall':mind<path['width']*.5,'closest_sample_xz':[pos[0],pos[2]]})
    house_reports.append({'name':site['name'],'asset':site['asset'],'position':site['position'],'wall_footprint':footprint,'footprint_ground_samples':ground,'max_ground_above_floor':max(g['ground_height']-floor for g in ground),'max_floor_above_ground':max(floor-g['ground_height'] for g in ground),'path_proximity':proximity})

path_reports=[]
for path in layout.PATHS:
    points=[]
    for a,b in zip(path['points'],path['points'][1:]):points+=sample(a,b,.30)
    steep=[];edges=[]
    for i,p in enumerate(points):
        loc=layout.locate(p[0],p[2]);fraction=loc[0]/loc[1]
        if fraction>.78:edges.append({'xz':[p[0],p[2]],'shore_fraction':fraction,'height':layout.height(p[0],p[2])})
        if i and math.hypot(p[0]-points[i-1][0],p[2]-points[i-1][2])>.01:
            q=points[i-1];run=math.hypot(p[0]-q[0],p[2]-q[2]);rise=layout.height(p[0],p[2])-layout.height(q[0],q[2]);slope=abs(math.degrees(math.atan2(rise,run)))
            if slope>30:steep.append({'xz':[p[0],p[2]],'slope_degrees':slope})
    path_reports.append({'name':path['name'],'shore_dropoff_samples':edges,'steep_samples_over_30_deg':steep,'max_slope_degrees':max([s['slope_degrees'] for s in steep] or [0])})

wan=anchors['Anchor_Lamp_WanFeng']['position'];yue=anchors['Anchor_Lamp_YueChuang']['position'];gui=anchors['Anchor_Lamp_GuiHang']['position']
path=anchors['Target_Path']['position'];bench=anchors['Target_Bench']['position'];pier=anchors['Target_Pier']['position'];win=marker(sites['GrandmotherHouse'],'Marker_Window')
def lights(name,origin,forward,targets):
    return {'lamp':name,'current_forward':forward,'target_angular_offsets_degrees':{target:angle(forward,sub(p,origin)) for target,p in targets.items()}}
light_reports=[lights('WanFeng',wan,anchors['Anchor_Lamp_WanFeng']['forward'],{'Path':path,'Bench':bench}),lights('YueChuang',yue,anchors['Anchor_Lamp_YueChuang']['forward'],{'ActualWindow':win,'PlannedWindow':anchors['Target_Window']['position'],'Pier':pier}),lights('GuiHang',gui,anchors['Anchor_Lamp_GuiHang']['forward'],{'Bench':bench,'Pier':pier})]
wp=angle(sub(win,yue),sub(pier,yue))
axis=unit([x+y for x,y in zip(unit(sub(win,yue)),unit(sub(pier,yue)))])
window_radius=.55
window_radius_angle=math.degrees(math.asin(window_radius/length(sub(win,yue))))
light_pair={'actual_window_to_pier_angle':wp,'minimum_full_cone_center_targets':wp,'symmetric_bisector_forward':axis,'window_angular_radius_estimate':window_radius_angle,'minimum_full_cone_including_window_radius_when_aim_optimized':wp+window_radius_angle,'sixty_degree_cone_centerline_margin':30-wp*.5}

spawn=anchors['Anchor_PlayerSpawn']['position'];instrument=sites['Armillary']['position']
spawn_info={'horizontal_distance_to_armillary_center':math.hypot(spawn[0]-instrument[0],spawn[2]-instrument[2]),'armillary_platform_radius':1.22,'spawn_height_above_platform_origin':spawn[1]-instrument[1],'platform_top_height':.21,'overlaps_instrument_platform':math.hypot(spawn[0]-instrument[0],spawn[2]-instrument[2])<1.22 and spawn[1]<instrument[1]+.21}

report={'status':'review_findings','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'scope':'Read-only numerical review of layout.py and prop metadata. No Unity use, no layout modifications. Geometric clearances are analytical estimates, not runtime collision tests.','bindings':bindings,'houses':house_reports,'paths':path_reports,'lights':light_reports,'chapter_three_window_pier_pair':light_pair,'spawn_platform':spawn_info,'grandmother_entry_actual_world':marker(sites['GrandmotherHouse'],'Marker_Entry'),'unverified':['No tree placements are defined in reviewed layout.py, so tree/path and tree/house clearance cannot yet be assessed.','No actual pier module placements are defined in reviewed layout.py; anchors imply a +Z quay but support connectivity and end margins are not yet measurable.','Terrain checks sample layout.height, not a mesh raycast.','House overlap review uses wall rectangles, not exact meshes.','User has not handed over Unity; no Editor or runtime verification performed.']}

def check_site(site):
    footprint=wall_footprint(site)
    hg=[layout.height(*p) for p in footprint]
    hits=[]
    for route in layout.PATHS:
        closest=min(point_polygon_distance((p[0],p[2]),footprint) for a,b in zip(route['points'],route['points'][1:]) for p in sample(a,b))
        if closest<route['width']*.5+.32:
            hits.append({'path':route['name'],'distance_to_wall':closest,'required':route['width']*.5+.32})
    return {'site':site,'footprint':footprint,'ground_range':max(hg)-min(hg),'max_shore_fraction':max(layout.locate(*p)[0]/layout.locate(*p)[1] for p in footprint),'path_conflicts':hits}

candidates=[]
for i,(x,z,yaw,scale) in enumerate([(-17.9,3.6,90,.80),(-17.8,6.7,90,.80),(-17.8,9.9,90,.80),(-17.8,13.1,90,.80),(-16.8,16.3,90,.80),(-14.0,18.3,180,.80),(-9.0,3.7,270,.80),(-9.4,7.1,270,.80),(-9.5,10.5,270,.80),(-9.0,13.9,270,.80),(-7.8,17.3,270,.80)]):
    site={'name':f'CandidateHouse_{i+1:02}','asset':f"cottage_{['teal','ochre','slate'][i%3]}",'position':layout.grounded(x,z),'yaw':yaw,'scale':scale}
    candidates.append(check_site(site))

def polygon_distance(a,b):
    # Separating axes first prevents missing edge crossings.
    separated=False
    for p in [a,b]:
        for v,w in zip(p,p[1:]+p[:1]):
            axis=(w[1]-v[1],v[0]-w[0]);pa=[q[0]*axis[0]+q[1]*axis[1] for q in a];pb=[q[0]*axis[0]+q[1]*axis[1] for q in b]
            if max(pa)<min(pb) or max(pb)<min(pa):separated=True
    if not separated:return 0
    return min([point_polygon_distance(q,b) for q in a]+[point_polygon_distance(q,a) for q in b])
near_pairs=[]
for i,a in enumerate(candidates):
    for b in candidates[i+1:]:
        d=polygon_distance(a['footprint'],b['footprint'])
        if d<.6:near_pairs.append({'a':a['site']['name'],'b':b['site']['name'],'wall_distance':d})
report['candidate_house_sites']=candidates
report['candidate_pairs_closer_than_60cm']=near_pairs

house_alts=[]
for dx in [0,-.3,-.5]:
    s=dict(sites['GrandmotherHouse']);s['position']=[s['position'][0]+dx,s['position'][1],s['position'][2]];s['yaw']=154
    c=check_site(s);c['x_offset']=dx
    c['markers']={n:marker(s,n) for n in ['Marker_Window','Marker_ABo_Seat','Marker_Entry']}
    c['lamp_floor_distances']={n:point_polygon_distance((a['position'][0],a['position'][2]),c['footprint']) for n,a in anchors.items() if a['kind']=='lamp'}
    win_alt=c['markers']['Marker_Window'];c['window_pier_angle']=angle(sub(win_alt,yue),sub(pier,yue))
    house_alts.append(c)
report['grandmother_yaw154_alternatives']=house_alts
(OUT/'layout-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'binding_offsets':[(x['anchor'],round(x['offset_metres'],3)) for x in bindings],'houses_with_path_overlap':[(x['name'],[(p['path'],round(p['minimum_centerline_to_wall_metres'],2)) for p in x['path_proximity'] if p['path_surface_overlaps_wall']]) for x in house_reports if any(p['path_surface_overlaps_wall'] for p in x['path_proximity'])],'paths':[(x['name'],len(x['shore_dropoff_samples']),round(x['max_slope_degrees'],1)) for x in path_reports],'window_pier':light_pair,'spawn':spawn_info},ensure_ascii=False,indent=2))
print('CANDIDATES',json.dumps({'houses':candidates,'near_pairs':near_pairs,'grandma_yaw154':house_alts},ensure_ascii=False,indent=2))
