"""Local geometric repair of the detached tree_b bough; no Unity interaction."""
import sys,importlib.util,json,math
from pathlib import Path
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('env_assets',Path(__file__).with_name('env_v1_assets.py'))
env=importlib.util.module_from_spec(spec);spec.loader.exec_module(env)
import bpy
from mathutils import Vector

env.clear()
manifest=json.loads((env.OUT/'asset-manifest.json').read_text(encoding='utf-8'))
record=next(a for a in manifest['assets'] if a['id']=='tree_b')
bpy.ops.import_scene.fbx(filepath=str(env.ROOT/record['lod0']['fbx']))
obs=env.meshes()
for obj in obs:
    env.activate(obj);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
report=[]
for obj in obs:
    report.append(dict(name=obj.name,components=env.components(obj),bounds=[list(x) for x in env.bounds([obj])]))
env.dump(env.ASSETS/'tree_b/joint-inspection.json',report)
print(json.dumps(report))

tree=next(o for o in obs if o.name=='tree_b')
comps,labels=env.components(tree,True)
image=bpy.data.images.load(str(env.ROOT/next(t['path'] for t in record['textures'] if '_BaseColor' in t['path'])),check_existing=True)
import numpy as np
pixels=np.empty(image.size[0]*image.size[1]*4,dtype=np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(image.size[1],image.size[0],4)
uv=tree.data.uv_layers.active.data
candidates=[[],[]]
for face in tree.data.polygons:
    lab=int(labels[face.vertices[0]])
    group=0 if lab==comps[0]['label'] else 1 if lab==comps[1]['label'] else -1
    if group<0:continue
    center=sum((tree.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
    if not 1.4<center.z<3.2:continue
    xy=sum((uv[i].uv for i in face.loop_indices),Vector((0,0)))/len(face.loop_indices)
    r,g,b=pixels[min(image.size[1]-1,max(0,int(xy.y*image.size[1]))),min(image.size[0]-1,max(0,int(xy.x*image.size[0]))),:3]
    if r>g*1.6 and g>b*1.35 and r>.07:candidates[group].append(center.copy())
if not all(candidates):raise RuntimeError('No reliable brown-wood connector endpoints')
# Prefer the lower wooden part of the detached bough, not the canopy tips.
minimum=min(p.z for p in candidates[1]);branchpoints=[p for p in candidates[1] if p.z<minimum+.48]
a,b=min(((a,b) for a in candidates[0] for b in branchpoints),key=lambda ab:(ab[0]-ab[1]).length)
direction=(b-a).normalized();a=a-direction*.12;b=b+direction*.14
print('JOINT_ENDPOINTS',list(a),list(b),'distance',(b-a).length,flush=True)

material=bpy.data.materials.new('tree_b_BarkRepair');material.use_nodes=True
shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(.20,.070,.026,1);shader.inputs['Roughness'].default_value=.86

def branch(name,rings,sides):
    verts=[];faces=[]
    axis=(b-a).normalized();u=axis.cross(Vector((0,0,1))).normalized();v=axis.cross(u).normalized()
    for j in range(rings):
        t=j/(rings-1);center=a.lerp(b,t)+Vector((0,0,.10*math.sin(math.pi*t)))
        radius=.16*(1-t)+.11*t
        for k in range(sides):
            ang=2*math.pi*k/sides;verts.append(center+radius*(math.cos(ang)*u+math.sin(ang)*v))
    for j in range(rings-1):
        for k in range(sides):faces.append((j*sides+k,j*sides+(k+1)%sides,(j+1)*sides+(k+1)%sides,(j+1)*sides+k))
    faces.extend([tuple(reversed(range(sides))),tuple(range((rings-1)*sides,rings*sides))])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            vi=mesh.loops[li].vertex_index;layer.data[li].uv=(vi%sides/sides,vi//sides/(rings-1))
    return obj

joint=branch('tree_b_BranchRepair',5,6);obs.append(joint)
if sum(env.tri_count(o) for o in obs)>12000:raise RuntimeError('Tree budget exceeded')
fbx=env.ROOT/record['lod0']['fbx'];env.export_fbx(obs,fbx)
record['lod0']['triangles']=sum(env.tri_count(o) for o in obs);record['lod0']['sha256']=env.sha(fbx)
record['lod0']['objects']=[dict(name=o.name,triangles=env.tri_count(o)) for o in obs]
record['previews']=env.previews(obs,fbx.parent/'previews','processed',640)
for o in obs:o.hide_render=True;o.hide_set(True)
previous=set(env.meshes());fbx1=env.ROOT/record['lod1']['fbx'];bpy.ops.import_scene.fbx(filepath=str(fbx1));lod=[o for o in env.meshes() if o not in previous]
lod.append(branch('tree_b_BranchRepair_LOD1',4,4));env.export_fbx(lod,fbx1)
record['lod1'].update(sha256=env.sha(fbx1),triangles=sum(env.tri_count(o) for o in lod))
record['lod1']['ratio']=record['lod1']['triangles']/record['lod0']['triangles']
record['materials'].append(dict(name=material.name,role='BarkRepair',base_color=[.20,.070,.026,1],roughness=.86,emission_color=[0,0,0],emission_strength=0))
record['steps'].append('Add 56-triangle tapered curved wood connector between detached source bough and trunk; LOD1 connector 28 triangles')
record['branch_repair']=dict(start_blender_metres=list(a),end_blender_metres=list(b),lod0_triangles=env.tri_count(joint),note='Connector intersects original wood surfaces; it does not claim a watertight boolean union.')
for o in lod:o.hide_render=True;o.hide_set(True)
for o in obs:o.hide_render=False;o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(env.ROOT/record['blend']))
env.dump(env.OUT/'asset-manifest.json',manifest);env.dump(fbx.parent/'asset.json',record)
print('ENV_BRANCH_REPAIR_COMPLETE',record['lod0']['triangles'],record['lod1']['triangles'],flush=True)
