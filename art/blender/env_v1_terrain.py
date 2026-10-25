"""Generate the continuous crescent island and paths without using Unity."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import env_v1_layout as layout
import bpy
import math
import random
import json
import hashlib
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v1/terrain'
OUT.mkdir(parents=True,exist_ok=True)
random.seed(221026)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name,color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.86
    return m

MATS=[material('Ground_Moss',(.17,.235,.17)),material('Ground_Sage',(.25,.29,.19)),
      material('Ground_Earth',(.32,.25,.17)),material('Cliff_BlueSlate',(.16,.205,.235)),
      material('Cliff_SoftSlate',(.24,.265,.27)),material('Path_WeatheredStone',(.42,.44,.40)),
      material('Path_WarmStone',(.48,.44,.36)),material('Shore_Sand',(.40,.40,.30))]

def xyz(p):
    x,y,z=p
    return (x,-z,y)

def mesh(name,verts,faces,indices):
    me=bpy.data.meshes.new(name)
    me.from_pydata([xyz(p) for p in verts],[],faces)
    me.update()
    ob=bpy.data.objects.new(name,me)
    bpy.context.collection.objects.link(ob)
    for m in MATS:me.materials.append(m)
    for i,p in enumerate(me.polygons):
        p.material_index=indices[i] if isinstance(indices,list) else indices
        p.use_smooth=name=='IslandGround'
    bpy.context.view_layer.objects.active=ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    return ob

centres=layout.CENTRES
N=len(centres); W=24
verts=[]; boundary_left=[];boundary_right=[]
for i,(x,z,w,h) in enumerate(centres):
    a=centres[max(0,i-1)];b=centres[min(N-1,i+1)]
    dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
    nx,nz=dz/length,-dx/length
    for j in range(W+1):
        v=-1+2*j/W
        # Small coherent shore irregularity, no coarse disconnected chunks.
        shore=1+.025*math.sin(i*.49)+.018*math.cos(i*.17)
        xx,zz=x+nx*w*v*shore,z+nz*w*v*shore
        yy=layout.height(xx,zz)
        verts.append((xx,yy,zz))
    for sign,target in [(-1,boundary_left),(1,boundary_right)]:
        # Include the full coastal path; the controller's slope test still guards
        # the sloping shore. Pier is a separate boundary union in the builder.
        xx,zz=x+nx*w*.84*sign,z+nz*w*.84*sign
        target.append([xx,layout.height(xx,zz)+.03,zz])
faces=[];indices=[]
for i in range(N-1):
    for j in range(W):
        a=i*(W+1)+j;b=a+W+1
        faces.extend([(a,b,b+1),(a,b+1,a+1)])
        v=abs(-1+2*(j+.5)/W)
        index=7 if v>.96 else (4 if v>.84 else (1 if math.sin(i*.2+j*.3)>.6 else 0))
        indices.extend([index,index])
ground=mesh('IslandGround',verts,faces,indices)

# Layered watertight visible cliff skirt goes down below the sea.
edge_ids=[i*(W+1) for i in range(N)]+[i*(W+1)+W for i in reversed(range(N))]
edge=[verts[i] for i in edge_ids]
skirtverts=[]
for band in range(3):
    for k,(x,y,z) in enumerate(edge):
        offset=0 if band==0 else (.5 if band==1 else 1.05)
        cx,cz=-7,1
        d=math.hypot(x-cx,z-cz)
        skirtverts.append((x+(x-cx)/max(d,.1)*offset,
                           y if band==0 else (-1.1 if band==1 else -3.4)-.18*math.sin(k*.8),
                           z+(z-cz)/max(d,.1)*offset))
skirtfaces=[];skirtmats=[];L=len(edge)
for band in range(2):
    for k in range(L):
        a=band*L+k;b=band*L+(k+1)%L
        skirtfaces.append((a,b,b+L,a+L));skirtmats.append(3 if (k//7+band)%3 else 4)
cliff=mesh('CoastalCliff',skirtverts,skirtfaces,skirtmats)

# Individually readable stone slabs, combined into one low-overhead mesh.
pathverts=[];pathfaces=[];pathmats=[];path_samples=[]
for path in layout.PATHS:
    pts=path['points'];samples=[]
    for i in range(len(pts)-1):
        a,b=Vector(pts[i]),Vector(pts[i+1]);dist=(Vector((b.x,0,b.z))-Vector((a.x,0,a.z))).length
        count=max(1,round(dist/.82))
        for j in range(count):
            t=j/count;p=a.lerp(b,t)
            samples.append(p)
    samples.append(Vector(pts[-1]))
    for i,p in enumerate(samples[:-1]):
        q=samples[i+1];d=Vector((q.x-p.x,0,q.z-p.z));length=d.length
        if length<.05:continue
        d.normalize();n=Vector((d.z,0,-d.x))
        cen=(p+q)*.5;half=path['width']*.48
        # Four flat facets across each rounded path stone.
        jag=[.06*math.sin(i*2.1+k) for k in range(4)]
        corners=[cen-d*length*.46-n*(half+jag[0]),cen+d*length*.46-n*(half+jag[1]),
                 cen+d*length*.46+n*(half+jag[2]),cen-d*length*.46+n*(half+jag[3])]
        base=len(pathverts)
        for c in corners:pathverts.append((c.x,layout.height(c.x,c.z)+.045,c.z))
        pathfaces.append(tuple(base+k for k in range(4)));pathmats.append(5+i%2)
        path_samples.append([cen.x,layout.height(cen.x,cen.z)+.045,cen.z])
paths=mesh('StonePaths',pathverts,pathfaces,pathmats)

bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1
for ob in bpy.context.scene.objects:ob.select_set(ob.type=='MESH')
bpy.ops.export_scene.fbx(filepath=str(OUT/'island_terrain.fbx'),use_selection=True,
    object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,
    bake_space_transform=False,add_leaf_bones=False,path_mode='RELATIVE',use_mesh_modifiers=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_terrain.blend'))

bb=[p for p in verts]
report=dict(schema='jieguang.environment.terrain.v1',source_script=str(Path(__file__).relative_to(ROOT)),
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    bounds_unity=dict(min=[min(p[k] for p in bb) for k in range(3)],max=[max(p[k] for p in bb) for k in range(3)]),
    coordinate_mapping='Blender(x,y,z) -> intended Unity(x,z,-y); verify after FBX import.',
    meshes=[dict(name=ob.name,triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)) for ob in (ground,cliff,paths)],
    boundary=boundary_left[4:-4]+list(reversed(boundary_right[4:-4])),
    path_samples=path_samples,
    material_settings=[dict(name=m.name,color=list(m.diffuse_color),roughness=.86) for m in MATS],
    collider_notes='IslandGround static MeshCollider Layer8; paths cosmetic at +.045m, pier has separate continuous collider.',
    status='offline geometry generated; Unity import, walkability and screenshots pending')
(OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENV_TERRAIN='+json.dumps({k:report[k] for k in ('bounds_unity','meshes')}),flush=True)
