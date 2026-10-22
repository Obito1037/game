"""Original deterministic meadow atlas + frozen-root contact colour candidate.
No existing PNG supplies image pixels to the generator. Frozen PNGs are read only
after generation as a verification oracle. No geometry or source file is saved.
"""
import bpy, math, random, json, hashlib, time
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/meadow-v9';OUT.mkdir(parents=True,exist_ok=True)
WORLD=ROOT/'art/generated/world-v7'
SOURCE=ROOT/'art/blender/build_island_v6.py'
start=time.time()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
frozen_paths=[WORLD/'island.blend',WORLD/'island.fbx',WORLD/'island.glb',
 WORLD/'textures/meadow-watercolor.png',WORLD/'textures/meadow-normal.png',
 ROOT/'GameProject/Assets/BorrowedLight/Resources/Textures/Meadow.png',
 ROOT/'GameProject/Assets/BorrowedLight/Resources/Textures/MeadowNormal.png']
frozen_hashes={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}

# Exact original colour algorithm, including draw order and scalar precision.
# Copied from frozen build_island_v6.py, before any geometry-generation RNG.
random.seed(7319)
size=2048;rng=np.random.default_rng(41);accum=np.zeros((size,size),dtype=np.float32)
fields={};coords=np.linspace(0,1,size,endpoint=False)
for cells,weight in [(5,.31),(13,.25),(35,.18),(90,.12),(256,.08),(680,.04)]:
    grid=rng.random((cells+1,cells+1),dtype=np.float32)
    p=coords*cells;ids=np.floor(p).astype(int);t=p-ids;t=t*t*(3-2*t)
    rows=grid[:,ids]*(1-t)[None,:]+grid[:,ids+1]*t[None,:]
    field=rows[ids,:]*(1-t)[:,None]+rows[ids+1,:]*t[:,None]
    accum+=field*weight
    if cells in (5,13,35,90):fields[cells]=field.copy()
accum+=rng.normal(0,.025,(size,size)).astype(np.float32)
dark=np.array([.25,.315,.17]);light=np.array([.44,.50,.285])
tone=np.clip((fields[5]*.55+fields[13]*.30+fields[35]*.15-.18)*1.65,0,1)
rgb=dark[None,None,:]+(light-dark)[None,None,:]*tone[:,:,None]
moss_weight=np.clip((fields[13]-.49)*2.3+(fields[35]-.5)*.45,0,.68)
moss_rgb=np.array([.38,.425,.235])[None,None,:]+(fields[90][:,:,None]-.5)*np.array([.09,.085,.045])[None,None,:]
rgb=rgb*(1-moss_weight[:,:,None])+moss_rgb*moss_weight[:,:,None]
rgb+=(accum[:,:,None]-.5)*np.array([.065,.075,.04])[None,None,:]
rgb+=(fields[90][:,:,None]-.5)*np.array([.08,.09,.045])[None,None,:]
gx,gz=np.meshgrid(coords*18-9,coords*18-9)
path_layout=[[(0,-6),(0,-3.6),(-1,-1.7),(-1.7,-.8)],[(-1,.9),(-2.4,1.8),(-3.9,2.5),(-4.1,2.9)],[(1.6,0),(3.6,-.4),(5.4,-1.8),(6.1,-3.35)],[(-1.6,-.3),(-3.7,-.4),(-5.8,.1)]]
def path_distance(x,z):
    dist=np.full(x.shape,30,dtype=np.float32)
    for route in path_layout:
        for (ax,az),(bx,bz) in zip(route[:-1],route[1:]):
            dx,dz=bx-ax,bz-az;t=np.clip(((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz),0,1)
            dist=np.minimum(dist,np.sqrt((x-ax-t*dx)**2+(z-az-t*dz)**2))
    return dist
dist=path_distance(gx,gz)
wear=np.clip((.77-dist+(fields[35]-.5)*.30+(fields[90]-.5)*.13)/.57,0,1)
soil=np.array([.39,.345,.255])[None,None,:]+(accum[:,:,None]-.5)*np.array([.13,.11,.085])[None,None,:]
rgb=rgb*(1-wear[:,:,None]*.92)+soil*(wear[:,:,None]*.92)
for tx,tz,rr in [(-6.55,3.9,1.15),(5.1,3.0,.7),(2.7,6.4,.95)]:
    pocket=np.clip((rr-np.sqrt((gx-tx)**2+(gz-tz)**2)+(fields[35]-.5)*.4)/.5,0,.64)
    rgb=rgb*(1-pocket[:,:,None])+np.array([.30,.33,.205])[None,None,:]*pocket[:,:,None]
# Keep original height computations/draws even though this candidate does not
# produce a normal map. They make algorithm equivalence straightforward to audit.
height=(accum*.13+wear*.025).astype(np.float32)
for i in range(10800):
    px,py=rng.integers(5,size-5,size=2);rx=int(rng.integers(2,6));ry=int(rng.integers(1,4));ang=float(rng.random()*math.tau)
    x0,x1=max(0,px-rx-ry-2),min(size,px+rx+ry+3);y0,y1=max(0,py-rx-ry-2),min(size,py+rx+ry+3)
    yy,xx=np.mgrid[y0:y1,x0:x1];xx=xx-px;yy=yy-py
    u=xx*math.cos(ang)+yy*math.sin(ang);v=-xx*math.sin(ang)+yy*math.cos(ang)
    mask=np.clip(1-(u/rx)**2-(v/ry)**2,0,1)**.28
    leaf=np.array(random.choice([(.46,.40,.23),(.35,.42,.22),(.49,.46,.30),(.27,.35,.18),(.38,.46,.26)]))
    rgb[y0:y1,x0:x1]=rgb[y0:y1,x0:x1]*(1-mask[:,:,None]*.70)+leaf*mask[:,:,None]*.70
    height[y0:y1,x0:x1]+=mask*.035
rgb=np.clip(rgb,0,1)
base_rgb=rgb.copy()
del accum,fields,grid,rows,field,tone,moss_weight,moss_rgb,soil,height,wear,dist

# Capture physical root points from frozen authored meshes, not random texture
# flecks and not recalibrated Unity world coordinates.
bpy.ops.wm.open_mainfile(filepath=str(WORLD/'island.blend'))
ground=bpy.data.objects['Island_Meadow'];gm=ground.data
ground_bvh=BVHTree.FromPolygons([ground.matrix_world@v.co for v in gm.vertices],[tuple(p.vertices) for p in gm.polygons],all_triangles=False)
roots=[];extraction=[]
for name in ['Garden_GrassTufts','Garden_CreepingMeadowLeaves']:
    ob=bpy.data.objects[name];m=ob.data;adj=[[] for _ in m.vertices]
    for edge in m.edges:
        a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
    seen=set();components=0;rejected_no_ground=0;rejected_height=0;accepted=0
    for vi in range(len(m.vertices)):
        if vi in seen:continue
        stack=[vi];seen.add(vi);component=[]
        while stack:
            k=stack.pop();component.append(k)
            for q in adj[k]:
                if q not in seen:seen.add(q);stack.append(q)
        components+=1
        points=[ob.matrix_world@m.vertices[k].co for k in component]
        low=min(p.z for p in points);high=max(p.z for p in points)
        bases=[p for p in points if p.z<=low+.0015]
        root=sum(bases,Vector((0,0,0)))/len(bases)
        hit=ground_bvh.ray_cast(Vector((root.x,root.y,1.5)),Vector((0,0,-1)),2)[0]
        if hit is None:rejected_no_ground+=1;continue
        clearance=low-hit.z
        if not -.035<=clearance<=.06:rejected_height+=1;continue
        blade_height=high-low
        radius=max(.03,min(.08,.03+blade_height*.13)) if name=='Garden_GrassTufts' else .042
        # Leave one percentage point of headroom for 8-bit sRGB quantization.
        depth=min(.11,.08+blade_height*.14) if name=='Garden_GrassTufts' else .085
        roots.append({'id':len(roots),'mesh':name,'component_first_vertex':vi,'component_vertices':len(component),
            'root_unity':[float(root.x),float(low),float(-root.y)],'ground_y':float(hit.z),'root_clearance_metres':float(clearance),
            'uv':[(float(root.x)+9)/18,(-float(root.y)+9)/18],'height_metres':float(blade_height),
            'support_radius_metres':radius,'maximum_linear_darkening':depth})
        accepted+=1
    extraction.append({'mesh':name,'components':components,'accepted':accepted,'rejected_no_ground':rejected_no_ground,'rejected_root_clearance':rejected_height})
print('ROOTS_EXTRACTED',extraction,flush=True)

# Compact-support kernels with bounded MAX union. Nearby roots merge naturally
# without accumulating exponential darkness in dense grass. No new randomness.
darkening=np.zeros((size,size),dtype=np.float32)
pixel_scale=size/18
for root in roots:
    x,z=root['root_unity'][0],root['root_unity'][2];r=root['support_radius_metres'];d=root['maximum_linear_darkening']
    px=(x+9)*pixel_scale-.5;py=(z+9)*pixel_scale-.5;rp=r*pixel_scale
    x0=max(0,int(math.floor(px-rp)));x1=min(size,int(math.ceil(px+rp))+1)
    y0=max(0,int(math.floor(py-rp)));y1=min(size,int(math.ceil(py+rp))+1)
    yy,xx=np.mgrid[y0:y1,x0:x1]
    q=((xx-px)/rp)**2+((yy-py)/rp)**2
    field=np.maximum(0,1-q)**2*d
    np.maximum(darkening[y0:y1,x0:x1],field,out=darkening[y0:y1,x0:x1])
# Protect a 50cm-wide bare path core; fade from the exact boundary to 68cm.
# Contact sampling uses texel centres. Original base atlas math remains intact.
gx+=9/size;gz+=9/size
route_distance=path_distance(gx,gz)
fade=np.clip((route_distance-.25)/.09,0,1);fade=fade*fade*(3-2*fade)
darkening*=fade
protected=route_distance<=.25
# Rasterize the actual authored ground perimeter; no painted contact outside it.
edge_counts={}
for poly in gm.polygons:
    ids=list(poly.vertices)
    for a,b in zip(ids,ids[1:]+ids[:1]):
        key=tuple(sorted((a,b)));edge_counts[key]=edge_counts.get(key,0)+1
rim_ids={v for edge,count in edge_counts.items() if count==1 for v in edge}
rim=[ground.matrix_world@gm.vertices[v].co for v in rim_ids]
rim.sort(key=lambda p:math.atan2(-p.y,p.x))
island_mask=np.zeros((size,size),dtype=bool)
for a,b in zip(rim,rim[1:]+rim[:1]):
    ax,az=a.x,-a.y;bx,bz=b.x,-b.y
    if abs(bz-az)<1e-12:continue
    crossing=((az>gz)!=(bz>gz))&(gx<(bx-ax)*(gz-az)/(bz-az)+ax)
    island_mask^=crossing
darkening*=island_mask
assert not np.any(darkening[protected])
assert darkening.max()<=.110001
candidate_rgb=base_rgb*(1-darkening[:,:,None])
assert np.array_equal(base_rgb[darkening==0],candidate_rgb[darkening==0])

def save_colour(name,data,colour_space='sRGB'):
    image=bpy.data.images.new(name,width=size,height=size,alpha=True)
    image.colorspace_settings.name=colour_space
    rgba=np.concatenate((data,np.ones((size,size,1))),axis=2).astype(np.float32)
    image.pixels.foreach_set(rgba.ravel());image.file_format='PNG';image.filepath_raw=str(OUT/name);image.save()
    return image

# The original float-generated image uses default sRGB handling. The same
# Blender path reproduces the original linear-to-PNG encoding, then is verified.
save_colour('meadow-no-contact.png',base_rgb)
save_colour('meadow-contact.png',candidate_rgb)
save_colour('contact-mask.png',np.repeat((darkening/.11)[:,:,None],3,axis=2),'Non-Color')

def load_pixels(path):
    image=bpy.data.images.load(str(path),check_existing=False);image.colorspace_settings.name='sRGB'
    a=np.empty(size*size*4,dtype=np.float32);image.pixels.foreach_get(a)
    return a.reshape(size,size,4)
# Frozen PNG is exclusively a comparison oracle after both new outputs exist.
old=load_pixels(WORLD/'textures/meadow-watercolor.png')
fresh=load_pixels(OUT/'meadow-no-contact.png')
candidate=load_pixels(OUT/'meadow-contact.png')
oracle_delta=np.abs(old-fresh);pixel_equivalent=bool(np.array_equal(old,fresh))
outside=darkening==0;outside_delta=float(np.max(np.abs(candidate[outside]-fresh[outside])))
protected_delta=float(np.max(np.abs(candidate[protected]-fresh[protected])))
changed=np.max(np.abs(candidate-fresh),axis=2)>0
alpha_equal=bool(np.array_equal(candidate[:,:,3],fresh[:,:,3]))
assert pixel_equivalent,'No-contact generator does not reproduce frozen image pixels'
assert outside_delta==0 and protected_delta==0 and alpha_equal
assert all(sha(p)==frozen_hashes[str(p.relative_to(ROOT))] for p in frozen_paths)

luma_weights=np.array([.2126,.7152,.0722]);base_luma=base_rgb@luma_weights
actual_ratio=1-(candidate[:,:,:3]@luma_weights)/np.maximum(fresh[:,:,:3]@luma_weights,1e-8)
target=darkening>0
ideal_mips=[];mip_base=fresh[:,:,:3].copy();mip_contact=candidate[:,:,:3].copy()
for mip in range(5):
    if mip:
        mip_base=mip_base.reshape(mip_base.shape[0]//2,2,mip_base.shape[1]//2,2,3).mean(axis=(1,3))
        mip_contact=mip_contact.reshape(mip_contact.shape[0]//2,2,mip_contact.shape[1]//2,2,3).mean(axis=(1,3))
    span=mip_base.shape[0];xx,zz=np.meshgrid((np.arange(span)+.5)*18/span-9,(np.arange(span)+.5)*18/span-9)
    dd=path_distance(xx,zz);change=1-(mip_contact@luma_weights)/np.maximum(mip_base@luma_weights,1e-8)
    ideal_mips.append({'mip':mip,'resolution':span,'max_darkening_in_25cm_path_core':float(change[dd<=.25].max()),
       'max_darkening_in_15cm_path_center':float(change[dd<=.15].max()),
       'scope':'Ideal linear box averages at mip texel centers; actual Unity compression/LOD/bilinear still needs runtime A/B.'})
stats={'maximum_linear_darkening_before_quantization':float(darkening.max()),
 'mean_linear_darkening_whole_atlas':float(darkening.mean()),
 'mean_linear_darkening_contact_mask':float(darkening[target].mean()),
 'darkening_percentiles_contact_p50_p90_p99':[float(v) for v in np.percentile(darkening[target],[50,90,99])],
 'target_mask_pixels':int(target.sum()),'target_mask_fraction_atlas':float(target.mean()),'target_mask_area_m2':float(target.sum()*(18/size)**2),
 'actual_ground_pixels':int(island_mask.sum()),'actual_ground_area_m2':float(island_mask.sum()*(18/size)**2),
 'target_mask_fraction_actual_ground':float(target[island_mask].mean()),
 'mean_linear_darkening_actual_ground':float(darkening[island_mask].mean()),
 'encoded_changed_pixels':int(changed.sum()),'encoded_changed_fraction_atlas':float(changed.mean()),
 'fraction_atlas_darker_by_at_least_2pct':float((darkening>=.02).mean()),
 'fraction_atlas_darker_by_at_least_8pct':float((darkening>=.08).mean()),
 'fraction_atlas_darker_by_at_least_11pct':float((darkening>=.11).mean()),
 'maximum_encoded_linear_luminance_darkening':float(actual_ratio.max()),
 'maximum_encoded_ratio_error_from_target':float(np.max(np.abs(actual_ratio-darkening))),
 'mean_encoded_linear_luminance_darkening_whole_atlas':float(actual_ratio.mean()),
 'protected_bare_path_pixels':int(protected.sum()),'protected_bare_path_area_m2':float(protected.sum()*(18/size)**2),
 'protected_path_max_pixel_difference':protected_delta,'outside_mask_max_pixel_difference':outside_delta,'alpha_unchanged':alpha_equal,
 'ideal_mip_path_checks':ideal_mips}

root_report={'source_blend':str((WORLD/'island.blend').relative_to(ROOT)),'source_sha256':frozen_hashes[str((WORLD/'island.blend').relative_to(ROOT))],
 'coordinate_contract':'Authored Unity=(Blender.x, Blender.z, -Blender.y); UV=((x+9)/18,(z+9)/18), pixel centres at (index+.5)/2048.',
 'extraction':extraction,'root_count':len(roots),'roots':roots}
(OUT/'root-positions.json').write_text(json.dumps(root_report,ensure_ascii=False,indent=2),encoding='utf-8')
files=['meadow-contact.png','meadow-no-contact.png','contact-mask.png','root-positions.json']
report={'title':'Original meadow root contact colour candidate','status':'staged; requires fixed-pose Unity A/B approval',
 'generator':str(Path(__file__).relative_to(ROOT)),'original_algorithm':str(SOURCE.relative_to(ROOT)),'original_algorithm_file_sha256':sha(SOURCE),
 'seeds':{'python_random':7319,'numpy_default_rng':41},'resolution':[size,size],'new_runtime_texture_slots':0,
 'normal_unchanged':True,'geometry_unchanged':True,'old_png_used_only_as_read_only_oracle':True,
 'no_contact_vs_frozen':{'pixels_identical':pixel_equivalent,'maximum_decoded_linear_rgba_difference':float(oracle_delta.max()),
  'generated_png_sha256':sha(OUT/'meadow-no-contact.png'),'original_png_sha256':sha(WORLD/'textures/meadow-watercolor.png')},
 'root_extraction':extraction,'root_count':len(roots),'mask_method':'Root-derived compact quadratic kernels, MAX union, no random additions. Path distance<=.25m protected, smooth transition to .34m.',
 'mask_statistics':stats,'frozen_inputs_sha256':frozen_hashes,'all_frozen_inputs_unchanged':True,
 'files':files,'sha256':{name:sha(OUT/name) for name in files},'seconds':time.time()-start}
(OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('MEADOW_V9_READY',json.dumps(stats),flush=True)
