"""Independent, low-sample Blender near-ground inspection; never changes exports."""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'island.blend'))
scene=bpy.context.scene
def B(v): return Vector((v[0],-v[2],v[1]))
world=bpy.data.worlds.new('V6 inspection twilight')
scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.37,.45,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45
for name,pos,color,power,size in [('Cool fill',(4,10,-4),(.63,.76,1),1300,10),('Warm key',(-4,6,-7),(1,.80,.55),1100,8)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=B(pos)
    obj.rotation_euler=(B((0,0,-2))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('V6 ground detail');obj=bpy.data.objects.new('V6 ground detail',data);scene.collection.objects.link(obj)
obj.location=B((1.7,1.55,-5.5));obj.rotation_euler=(B((.2,.22,-3.0))-obj.location).to_track_quat('-Z','Y').to_euler()
data.lens=47;scene.camera=obj
scene.render.engine='CYCLES';scene.cycles.samples=6;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
scene.render.resolution_x=512;scene.render.resolution_y=354;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.2
scene.render.filepath=str(OUT/'blender-ground-closeup.png')
bpy.ops.render.render(write_still=True)
obj.location=B((0,1.72,-6.5));obj.rotation_euler=(B((0,.36,-1.9))-obj.location).to_track_quat('-Z','Y').to_euler()
data.lens=30
scene.render.resolution_x=512;scene.render.resolution_y=320
scene.render.filepath=str(OUT/'blender-path-context.png')
bpy.ops.render.render(write_still=True)
obj.location=B((2.5,.85,-5.45));obj.rotation_euler=(B((1.2,.22,-4.2))-obj.location).to_track_quat('-Z','Y').to_euler()
data.lens=48
scene.render.resolution_x=512;scene.render.resolution_y=512
scene.render.filepath=str(OUT/'blender-rock-detail.png')
bpy.ops.render.render(write_still=True)
report=json.loads((OUT/'asset-manifest.json').read_text(encoding='utf-8'))
for name in ['blender-ground-closeup.png','blender-path-context.png','blender-rock-detail.png']:
    if name not in report['files']:report['files'].append(name)
    report['sha256'][name]=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
report['preview_scope']='512px, six-sample CPU Blender ground/rock inspections only. Actual Unity runtime appearance must be checked after integration.'
(OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
