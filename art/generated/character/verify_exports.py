"""Round-trip check of exported traveler hierarchy, scale and animated pivots."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
results={}
expected={'TravelerRoot':(0,0,0),'Body':(0,0,.67),'Head':(0,0,.945),'Arm_L':(-.19,0,.855),'Arm_R':(.19,0,.855),'Leg_L':(-.083,0,.505),'Leg_R':(.083,0,.505),'ScarfTail':(.045,.075,.895),'Lantern':(.276,-.066,.52)}
for suffix in ['fbx','glb']:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'))
    else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    bpy.context.view_layer.update()
    errors=[]; pivots={}
    for name,position in expected.items():
        o=bpy.data.objects.get(name)
        if o is None: errors.append('missing '+name); continue
        actual=o.matrix_world.translation; pivots[name]=list(actual)
        if (actual-Vector(position)).length>.0001: errors.append('wrong pivot '+name+' '+str(list(actual)))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=[min(p[i] for p in points) for i in range(3)]; hi=[max(p[i] for p in points) for i in range(3)]
    if not .001<lo[2]<.01: errors.append('incorrect foot contact')
    if not 1.23<hi[2]<1.28: errors.append('incorrect scale or height')
    lantern=bpy.data.objects.get('Lantern')
    if lantern is not None and (not lantern.parent or lantern.parent.name!='Arm_R'): errors.append('lantern not attached to right hand')
    triangles=0
    for o in meshes: o.data.calc_loop_triangles(); triangles+=len(o.data.loop_triangles)
    if triangles>=25000: errors.append('runtime triangle budget exceeded')
    hood=bpy.data.objects.get('Hood_OuterShell'); n=hood.matrix_world.to_3x3().inverted().transposed()
    dots=[(n@p.normal).normalized().dot((hood.matrix_world@p.center-Vector((0,.03,1.048))).normalized()) for p in hood.data.polygons]
    hood_normals={'polygons':len(dots),'outward':sum(d>0 for d in dots),'inward':sum(d<0 for d in dots),'mean_radial_dot':sum(dots)/len(dots)}
    if hood_normals['inward']>0: errors.append('hood exterior contains inward-facing polygons')
    blinks={}
    for name in ['Blink_L','Blink_R']:
        blink=bpy.data.objects.get(name)
        if not blink: errors.append('missing '+name); continue
        if not blink.parent or blink.parent.name!='Head': errors.append('wrong blink parent '+name)
        open_scale=list(blink.scale)
        if abs(blink.scale.y-.001)>.00001 or abs(blink.scale.x-.001)>.00001: errors.append('wrong blink open scale '+name)
        descendants=[o for o in blink.children_recursive if o.type=='MESH']
        open_points=[o.matrix_world@Vector(c) for o in descendants for c in o.bound_box]
        open_height=max(p.z for p in open_points)-min(p.z for p in open_points)
        open_width=max(p.x for p in open_points)-min(p.x for p in open_points)
        blink.scale=(1,1,1); bpy.context.view_layer.update()
        closed_points=[o.matrix_world@Vector(c) for o in descendants for c in o.bound_box]
        closed_height=max(p.z for p in closed_points)-min(p.z for p in closed_points)
        if not open_height<.0002: errors.append('blink not hidden '+name)
        if not open_width<.0002: errors.append('blink width not hidden '+name)
        if not .078<closed_height<.085: errors.append('blink axis or expansion wrong '+name)
        blink.scale=(.001,.001,1); bpy.context.view_layer.update()
        blinks[name]={'open_local_scale':open_scale,'open_height_m':open_height,'open_width_m':open_width,'closed_height_m':closed_height,'axes':'local X and Y'}
    results[suffix]={'passed':not errors,'errors':errors,'pivots_blender_world':pivots,'bounds_blender':{'min':lo,'max':hi},'triangles':triangles,'mesh_renderers':len(meshes),'hood_normal_validation':hood_normals,'blink_validation':blinks}
(OUT/'export-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
assert all(v['passed'] for v in results.values()),'export verification failed'
