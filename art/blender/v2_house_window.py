"""Reproducible A01 window study/derived open-window mesh; originals stay intact."""
import bpy, os, sys, json, math
from mathutils import Vector
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'../..'))
OUT=os.path.join(ROOT,'art/generated/props-v2-window')
os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT,'art/generated/props-v2/A01_grandma_house/A01_grandma_house.fbx'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mat=bpy.data.materials.new('House');mat.use_nodes=True
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(os.path.join(ROOT,'art/generated/props-v2/A01_grandma_house/A01_grandma_house_albedo.jpg'))
mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
obj.data.materials.clear();obj.data.materials.append(mat)
sc=bpy.context.scene;sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='TEXTURE'
sc.world=bpy.data.worlds.new('World');sc.world.color=(.25,.25,.25)
sc.render.resolution_x=sc.render.resolution_y=800;sc.render.resolution_percentage=100
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=6.2
for name,d in [('front',(1,0,0)),('side',(0,-1,0))]:
    cam.location=Vector((0,0,2.75))+Vector(d)*15;cam.rotation_euler=(-Vector(d)).to_track_quat('-Z','Y').to_euler();sc.render.filepath=os.path.join(OUT,name+'.png');bpy.ops.render.render(write_still=True)
print('BOUNDS', [list(obj.matrix_world@Vector(v)) for v in obj.bound_box])
# Orthographic measurement: front is +X, circular glazing centre Y=1.18,Z=1.30.
# Cut glazing and crossbars, keep the timber surround. The original FBX is never overwritten.
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.51,depth=3.4,location=(2.0,1.18,1.30),rotation=(0,math.pi/2,0))
cutter=bpy.context.object
bpy.context.view_layer.objects.active=obj
mod=obj.modifiers.new('Open circular story window','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
dst=os.path.join(ROOT,'GameProject/Assets/JieGuang/Props/A01_grandma_house/A01_grandma_house_open.fbx')
bpy.ops.export_scene.fbx(filepath=dst,use_selection=True,object_types={'MESH'},apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',path_mode='STRIP',mesh_smooth_type='FACE')
cam.location=(15,0,2.75);cam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();sc.render.filepath=os.path.join(OUT,'front-open.png');bpy.ops.render.render(write_still=True)
json.dump({'source':'art/generated/props-v2/A01_grandma_house/A01_grandma_house.fbx','window_blender':[2.0,1.18,1.30],'radius':.51,'output':dst},open(os.path.join(OUT,'record.json'),'w'),indent=2)
