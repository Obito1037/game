"""Read-only frozen ground inspection. No rendering or asset writes."""
import bpy,json,math,hashlib
import numpy as np
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
BASE=ROOT/'art/generated/world-v7'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'island.blend'))
ground=bpy.data.objects['Island_Meadow'];mesh=ground.data
uv=mesh.uv_layers.active
uv_error=[]
for p in mesh.polygons:
    for li in p.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co
        uv_error.append(max(abs(uv.data[li].uv.x-(co.x+9)/18),abs(uv.data[li].uv.y-(-co.y+9)/18)))
normals=[float(p.normal.z) for p in mesh.polygons]
images={}
for name,space in [('meadow-watercolor.png','sRGB'),('meadow-normal.png','Non-Color')]:
    image=bpy.data.images.load(str(BASE/'textures'/name),check_existing=False)
    image.colorspace_settings.name=space
    w,h=image.size;arr=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(arr);arr=arr.reshape(h,w,4)
    item={'width':w,'height':h,'linear_rgb_mean':[float(x) for x in arr[:,:,:3].mean(axis=(0,1))],
          'rgba_byte_sha256':hashlib.sha256((BASE/'textures'/name).read_bytes()).hexdigest()}
    if name.endswith('normal.png'):
        encoded=arr[:,:,:3]
        measurements=[]
        for mip in [0,1,2,3]:
            if mip:encoded=encoded.reshape(encoded.shape[0]//2,2,encoded.shape[1]//2,2,3).mean(axis=(1,3))
            xy=encoded[:,:,:2]*2-1
            z=np.sqrt(np.maximum(1e-6,1-(xy*xy).sum(axis=2)))
            for strength in [.22,.45,1.0]:
                # Installed URP unpack scales x/y while retaining unpacked z;
                # lighting then normalizes the result. No GPU compression simulated.
                angle=np.degrees(np.arctan2(np.sqrt((xy*xy).sum(axis=2))*strength,z))
                measurements.append({'mip':mip,'scale':strength,'angle_degrees_mean':float(angle.mean()),
                  'angle_degrees_p50_p90_p99_max':[float(v) for v in np.percentile(angle,[50,90,99,100])]})
        item['decoded_uncompressed_estimates']=measurements
    else:
        # A route/lantern-near sample and a clear soil gap: statistics, not edits.
        patches=[]
        for x,z,r in [(0,-5.4,.35),(0,-3.5,.25),(-.6,-5.2,.25),(1.7,-4.7,.25)]:
            ix=int((x+9)/18*w);iy=int((z+9)/18*h);rr=max(1,int(r/18*w))
            patch=arr[iy-rr:iy+rr,ix-rr:ix+rr,:3]
            luma=patch@np.array([.2126,.7152,.0722])
            patches.append({'unity_xz':[x,z],'radius_metres':r,'linear_luminance_mean':float(luma.mean()),'linear_luminance_std':float(luma.std())})
        item['ground_patch_statistics']=patches
    images[name]=item

report={'scope':'Read-only Blender scene/PNG inspection; no render, no GPU, no runtime material query.',
 'ground_mesh':{'name':ground.name,'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),'materials':[m.name for m in mesh.materials],
   'uv_layer':uv.name,'uv_formula':'u=(Unity.x+9)/18; v=(Unity.z+9)/18','maximum_uv_error':max(uv_error),
   'atlas_span_metres':18,'base_texel_metres':18/2048,'polygon_normal_blender_z_min_max':[min(normals),max(normals)]},
 'images':images,
 'normal_estimate_limits':'Original PNG and ideal arithmetic mip averages only. Unity compression, derivative LOD, filtering, tangent basis and GPU output are not measured.'}
(OUT/'ground-material-inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
