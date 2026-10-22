"""Actual evaluated skin connection-band preservation in three joint poses."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Quaternion
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[2]
namespace={'__file__':str(ROOT/'art/blender/build_traveler_v9.py')}
# Load only pure coordinate helpers; never invoke the builder.
for filename,names in [('build_traveler_v6.py',{'smooth','unproportion'}),
                       ('build_traveler_v9.py',{'nearest_curve'})]:
    tree=ast.parse((ROOT/'art/blender'/filename).read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),filename,'exec'))
ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
SLEEVE_PATH=[(.112,.002,.908),(.145,.002,.894),(.18,.001,.873),(.202,-.001,.831),(.222,.002,.774),(.237,-.004,.719),(.248,-.018,.660),(.256,-.036,.610),(.262,-.048,.574)]
scope=json.loads((OUT/'v8-preservation-verification.json').read_text()); targets=set(scope['targets'])

def evaluated(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh()
    values=[ev.matrix_world@v.co for v in mesh.vertices]; ev.to_mesh_clear(); return values

def collect(path,bands=None):
    bpy.ops.wm.open_mainfile(filepath=str(path)); root=bpy.data.objects['TravelerRoot']
    objects={o.name:o for o in root.children_recursive if o.type=='MESH'}
    if bands is None:
        bands={}
        for name,obj in objects.items():
            if name not in targets:
                bands[name]=list(range(len(obj.data.vertices))); continue
            if name.startswith('Head_Hair'): continue
            ids=[]; side=-1 if name.endswith('_L') else 1
            for v in obj.data.vertices:
                p=unproportion(obj.matrix_world@v.co)
                if name.startswith('Sleeve_'):
                    path=[Vector((side*x,y,z)) for x,y,z in SLEEVE_PATH]
                    i,t,_=nearest_curve(p,path); progress=(i+t)/(len(path)-1)
                    protect=progress<=.04 or progress>=.92
                elif name.startswith('Trouser_'): protect=p.z<=.228 or p.z>=.485
                else: protect=p.y<=-.09 or p.z>=.62
                if protect: ids.append(v.index)
            bands[name]=ids
    object_bind={o.name:o.matrix_basis.copy() for o in [root]+list(root.children_recursive)}
    bones={p.name:(o,p) for o in root.children_recursive if o.type=='ARMATURE' for p in o.pose.bones}
    bone_bind={name:p.matrix_basis.copy() for name,(o,p) in bones.items()}; result={}
    for pose,factor in [('neutral',0.),('stride_bend',1.),('opposite_bend',-.7)]:
        for name,matrix in object_bind.items(): bpy.data.objects[name].matrix_basis=matrix
        for name,matrix in bone_bind.items(): bones[name][1].matrix_basis=matrix
        for name,angle in [('Leg_L',-25),('Leg_R',14)]:
            o=bpy.data.objects[name]; bind=object_bind[name].to_quaternion()
            axis=o.matrix_world.to_quaternion().inverted()@Vector((1,0,0))
            o.rotation_mode='QUATERNION'; o.rotation_quaternion=bind@Quaternion(axis,math.radians(angle*factor))
        for name,angle in [('Knee_L',42),('Ankle_L',-17),('HipAnchor_L',25),('Knee_R',8),('Ankle_R',-22),('HipAnchor_R',-14),('Elbow_L',-35),('Elbow_R',-20)]:
            rig,p=bones[name]; axis=(rig.matrix_world@p.bone.matrix_local).to_quaternion().inverted()@Vector((1,0,0))
            p.rotation_mode='QUATERNION'; p.rotation_quaternion=Quaternion(axis,math.radians(angle*factor))
        bpy.context.view_layer.update()
        result[pose]={}
        for name,ids in bands.items():
            points=evaluated(objects[name]); result[pose][name]=[points[i] for i in ids]
    return result,bands

baseline,bands=collect(ROOT/'art/generated/character-v8/traveler.blend')
candidate,_=collect(OUT/'traveler.blend',bands); rows=[]; errors=[]
for pose,meshes in baseline.items():
    for name,points in meshes.items():
        maximum=max([(a-b).length for a,b in zip(points,candidate[pose][name])] or [0])
        if maximum>5e-7: errors.append(pose+' '+name+' protected boundary moved')
        rows.append({'pose':pose,'mesh':name,'is_boundary_subset':name in targets,'vertices':len(points),'maximum_world_error_m':maximum})
result={'passed':not errors,'errors':errors,'poses':3,'rows':rows,
        'scope':'Neutral and two opposed joint poses: actual evaluated original vs new sleeve shoulder-root/cuff, trouser waist/boot boundary, tunic front/collar plus all 55 fully protected meshes. This is a connection preservation test, not a full dynamic gait or collision sweep.'}
(OUT/'connection-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('CONNECTIONS '+json.dumps({'passed':not errors,'errors':errors,'poses':3,'max_error':max(row['maximum_world_error_m'] for row in rows)}))
assert not errors
