"""Measure actual skinned soles through a full grounded IK gait, and preview it.
This supplements interchange tests; Unity terrain/collision QA is still required.
"""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector, Quaternion
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
root=bpy.data.objects['TravelerRoot']
rigs=[o for o in root.children_recursive if o.type=='ARMATURE']
bones={p.name:(o,p) for o in rigs for p in o.pose.bones}
bind={o.name:o.matrix_basis.copy() for o in root.children_recursive if o.type=='EMPTY'}
bone_axes={name:(rig.matrix_world@pose.bone.matrix_local).to_quaternion().inverted()@Vector((1,0,0)) for name,(rig,pose) in bones.items()}
legs={}
for side in ['L','R']:
    hip=bpy.data.objects['Leg_'+side]
    kr,k=bones['Knee_'+side]; ar,a=bones['Ankle_'+side]
    h=hip.matrix_world.translation.copy(); knee=(kr.matrix_world@k.bone.matrix_local).translation; ankle=(ar.matrix_world@a.bone.matrix_local).translation
    upper=knee-h; lower=ankle-knee
    legs[side]={'hip':hip,'h':h,'a':ankle,'upper':Vector((upper.y,upper.z)).length,
        'lower':Vector((lower.y,lower.z)).length,'ua':math.atan2(-upper.y,-upper.z),'la':math.atan2(-lower.y,-lower.z)}

def hinge(name,degrees):
    rig,p=bones[name]; p.rotation_mode='QUATERNION'
    p.rotation_quaternion=Quaternion(bone_axes[name],math.radians(degrees))

def cycle(phase,gait):
    phase%=1
    if phase<.62: return (.2-.4*phase/.62)*gait,0.
    t=(phase-.62)/.38; smooth=t*t*(3-2*t); tangent=-.4/.62*.38
    return (-.2+.4*smooth+tangent*(2*t*t*t-3*t*t+t))*gait,math.sin(t*math.pi)**2*.028*gait

def pose(phase,gait=1,grounds=(0.,0.)):
    support_heights=[]
    for side,offset,ground in [('L',0,grounds[0]),('R',.5,grounds[1])]:
        leg=legs[side];f,lift=cycle(phase+offset,gait)
        if (phase+offset)%1<.62 or gait<.05:
            reach=leg['upper']+leg['lower']-.003
            horizontal=-(leg['a'].y-leg['h'].y)+f
            support_heights.append(ground+leg['a'].z-.003129+.004+math.sqrt(max(.01,reach*reach-horizontal*horizontal))-leg['h'].z)
    root.location.z=min(support_heights)
    joint_angles={}
    for side,offset,ground in [('L',0,grounds[0]),('R',.5,grounds[1])]:
        leg=legs[side]; f,lift=cycle(phase+offset,gait)
        target=leg['a'].copy();target.y-=f;target.z=ground+leg['a'].z-.003129+.004+lift
        hip=leg['h']+root.location;delta=target-hip
        distance=max(abs(leg['upper']-leg['lower'])+.001,min(leg['upper']+leg['lower']-.0002,Vector((delta.y,delta.z)).length))
        direction=math.atan2(-delta.y,-delta.z)
        upper=leg['upper'];lower=leg['lower']
        hip_offset=math.acos(max(-1,min(1,(upper*upper+distance*distance-lower*lower)/(2*upper*distance))))
        bend=math.pi-math.acos(max(-1,min(1,(upper*upper+lower*lower-distance*distance)/(2*upper*lower))))
        ua=direction+hip_offset;la=ua-bend
        hip_degrees=-math.degrees(ua-leg['ua'])
        knee_degrees=-math.degrees((la-ua)-(leg['la']-leg['ua']))
        obj=leg['hip'];obj.rotation_mode='QUATERNION';obj.rotation_quaternion=bind[obj.name].to_quaternion()@Quaternion(Vector((1,0,0)),math.radians(hip_degrees))
        hinge('Knee_'+side,knee_degrees);hinge('Ankle_'+side,-hip_degrees-knee_degrees)
        hinge('HipAnchor_'+side,-hip_degrees)
        joint_angles[side]={'hip':hip_degrees,'knee':knee_degrees,'ankle':-hip_degrees-knee_degrees}
    arm_swing=math.cos(phase*math.tau)*gait
    bpy.data.objects['Arm_L'].rotation_euler.x=math.radians(1.5+arm_swing*6)
    bpy.data.objects['Arm_R'].rotation_euler.x=math.radians(-2.5-arm_swing*3)
    hinge('Elbow_L',-3-gait*7-arm_swing*4);hinge('Elbow_R',-1-gait*4+arm_swing*1.5)
    bpy.context.view_layer.update()
    return joint_angles

samples=[]; errors=[]
for terrain,grounds in [('flat',(0.,0.)),('left_stone_9cm',(.09,0.)),('right_stone_9cm',(0.,.09))]:
    for frame in range(48):
        phase=frame/48;angles=pose(phase,grounds=grounds)
        row={'terrain':terrain,'phase':phase,'angles':angles,'feet':{}}
        for side,ground in zip(['L','R'],grounds):
            obj=bpy.data.objects['BootSole_'+side]
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=evaluated.to_mesh()
            pts=[evaluated.matrix_world@v.co for v in mesh.vertices];minimum=min(p.z for p in pts)
            evaluated.to_mesh_clear()
            row['feet'][side]={'sole_clearance_m':minimum-ground}
            if minimum-ground < .0035: errors.append(terrain+' / '+str(phase)+' / '+side+' sole penetrates ground')
        samples.append(row)
result={'passed':not errors,'errors':errors,'samples':len(samples),
    'min_sole_clearance_m':min(r['feet'][side]['sole_clearance_m'] for r in samples for side in ['L','R']),
    'max_knee_degrees':max(r['angles'][side]['knee'] for r in samples for side in ['L','R']),
    'scope':'Actual Blender evaluated skinned soles; steady full gait on flat ground and one foot on a 9 cm stone. Does not substitute for Unity raycast, animation timing, or moving terrain checks.',
    'frames':samples}
(OUT/'gait-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('GAIT_VERIFIED '+json.dumps({k:v for k,v in result.items() if k!='frames'}),flush=True)
assert result['passed']
if '--render' in sys.argv:
    scene=bpy.context.scene;scene.cycles.samples=12
    scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera
    for name,phase,location in [('render-gait-front.png',.33,(1.45,-4.5,1.5)),('render-gait-side.png',.33,(4.5,-.35,1.4))]:
        pose(phase)
        camera.location=location;camera.rotation_euler=(Vector((0,0,.64))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=1.6
        scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
