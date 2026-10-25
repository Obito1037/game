"""Numerical follow-up for parent-proposed cape routes; no Unity changes."""
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
import env_v1_props_layout_review as r
import json,math
L=r.layout
house=dict(r.sites['GrandmotherHouse']);house['yaw']=154
poly=r.wall_footprint(house)
routes=[{'name':'ProposedCapeVillage','width':1.75,'points':[L.local(x,.03,z) for x,z in [(-1.5,-1),(-1.5,0),(0,.8),(2.5,1.5),(2.5,4.8),(2.5,6.4),(0,8)]]+[L.grounded(3,-11),L.grounded(0,-8.2)]},
        {'name':'ProposedSpawnLane','width':1.3,'points':[L.local(x,.03,z) for x,z in [(4.4,-3.5),(4.4,-1.5),(3.8,1.2),(2.5,1.5)]]}]
out=[]
for route in routes:
    points=[p for a,b in zip(route['points'],route['points'][1:]) for p in r.sample(a,b,.08)]
    minhouse=min(r.point_polygon_distance((p[0],p[2]),poly) for p in points)
    lamps=[]
    for name,anchor in r.anchors.items():
        if anchor['kind']!='lamp':continue
        q=anchor['position'];dist=min(math.hypot(p[0]-q[0],p[2]-q[2]) for p in points)
        lamps.append({'name':name,'centerline_to_pole':dist,'paved_edge_to_base':dist-route['width']/2-.24})
    # Evaluate width, not only route centre, at both sides of each segment.
    samples=[]
    for a,b in zip(route['points'],route['points'][1:]):
        dx,dz=b[0]-a[0],b[2]-a[2];length=math.hypot(dx,dz)
        for p in r.sample(a,b,.2):
            for side in [-1,0,1]:
                x=p[0]+side*dz/length*route['width']/2;z=p[2]-side*dx/length*route['width']/2;loc=L.locate(x,z)
                samples.append({'xz':[x,z],'v':loc[0]/loc[1],'ground':L.height(x,z)})
    bench=r.sites['Bench'];bp=[]
    for x,z in [(-.98,-.295),(.98,-.295),(.98,.295),(-.98,.295)]:
        q=r.world(bench,[x,0,z]);bp.append([q[0],q[2]])
    bdist=min(r.point_polygon_distance((p[0],p[2]),bp) for p in points)
    inst=r.sites['Armillary']['position'];adist=min(math.hypot(p[0]-inst[0],p[2]-inst[2])-1.22 for p in points)
    out.append({'route':route['name'],'house_wall_to_path_centerline':minhouse,'house_wall_to_paved_edge':minhouse-route['width']/2,'lamp_distances':lamps,'max_shore_fraction_including_path_width':max(s['v'] for s in samples),'minimum_ground':min(s['ground'] for s in samples),'maximum_ground':max(s['ground'] for s in samples),'bench_wall_to_paved_edge':bdist-route['width']/2,'armillary_wall_to_paved_edge':adist-route['width']/2})

# Re-evaluate first house alternatives against current parent routes.
first=[]
for x,z in [(-17.9,3.6),(-17.5,3.6),(-17.2,3.6),(-17.0,3.4),(-17.5,3.4)]:
    site=dict(r.candidates[0]['site']);site['position']=L.grounded(x,z)
    q=r.check_site(site)
    first.append({'xz':[x,z],'shore':q['max_shore_fraction'],'paths':q['path_conflicts']})
result={'scope':'Proposed routes numerical verification. No Unity or collision simulation.','routes':out,'first_house_alternatives':first,'source_layout_sha256':r.report['source_sha256']}
(r.OUT/'proposed-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PROPOSED',json.dumps(result,ensure_ascii=False,indent=2))
