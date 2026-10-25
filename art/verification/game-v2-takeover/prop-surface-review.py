import bpy, collections, math, json
from mathutils import Vector
root=r'C:\Users\20665\Desktop\game'
for prop in ('A13_pier_end','A02_desk_set'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=root+'/art/generated/props-v2/'+prop+'/'+prop+'.fbx')
    heights=collections.defaultdict(float)
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH': continue
        obj.data.calc_loop_triangles()
        for tri in obj.data.loop_triangles:
            a,b,c=[obj.matrix_world@obj.data.vertices[v].co for v in tri.vertices]
            cross=(b-a).cross(c-a)
            if cross.length<1e-9: continue
            if cross.normalized().z>.92:
                z=(a.z+b.z+c.z)/3
                heights[round(z/.04)*.04]+=cross.length*.5
    print('HORIZONTAL_SURFACES',prop,json.dumps(sorted(heights.items(),key=lambda kv:-kv[1])[:15]))
