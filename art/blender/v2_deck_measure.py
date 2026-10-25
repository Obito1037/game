import bpy,os,collections,json
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'../..'))
for aid in ['A12_pier_segment','A13_pier_end']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT,'art/generated/props-v2',aid,aid+'.fbx'))
 o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
 bins=collections.defaultdict(float)
 for p in o.data.polygons:
  n=o.matrix_world.to_3x3()@p.normal
  if n.z>.8:
   z=(o.matrix_world@p.center).z;bins[round(z,1)]+=p.area
 print(aid,sorted(bins.items(),key=lambda x:-x[1])[:12],flush=True)
