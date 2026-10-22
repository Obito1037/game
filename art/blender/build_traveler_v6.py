"""Sculpt a compatible v6 traveler from the frozen, continuously skinned v5.

All authored changes and evidence stay in character-v6. No Unity or v5 files
are written. Blender 4.5 LTS: --background --python-exit-code 1 --python this.py
Optional arguments after --: --render / --verify / --render-only.
"""
import bpy, bmesh, json, math, hashlib, sys
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.kdtree import KDTree
from math import sin, cos, pi, exp, atan2, sqrt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'art/generated/character-v6'
SOURCE = ROOT/'art/generated/character-v5/traveler.blend'
OUT.mkdir(parents=True, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a))); return t*t*(3-2*t)

ZMAP=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
def proportion(v):
    k=next((i for i in range(len(ZMAP)-1) if v.z<=ZMAP[i+1][0]),len(ZMAP)-2)
    a,b=ZMAP[k],ZMAP[k+1]
    return Vector((v.x*(.91-.04*smooth(.21,.28,v.z)+.05*smooth(.90,.98,v.z)),
                   v.y*(1-.10*smooth(.36,.45,v.z)+.04*smooth(.90,.98,v.z)),
                   a[1]+(v.z-a[0])*(b[1]-a[1])/(b[0]-a[0])))

def unproportion(v):
    k=next((i for i in range(len(ZMAP)-1) if v.z<=ZMAP[i+1][1]),len(ZMAP)-2)
    a,b=ZMAP[k],ZMAP[k+1]; z=a[0]+(v.z-a[1])*(b[0]-a[0])/(b[1]-a[1])
    return Vector((v.x/(.91-.04*smooth(.21,.28,z)+.05*smooth(.90,.98,z)),
                   v.y/(1-.10*smooth(.36,.45,z)+.04*smooth(.90,.98,z)),z))

FACE_LEVELS=[(.932,.012,.020,-.023),(.940,.038,.036,-.021),(.953,.061,.052,-.017),(.975,.083,.072,-.011),(1.006,.103,.089,-.006),(1.045,.119,.105,-.002),(1.081,.128,.111,.001),(1.119,.127,.103,.008),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]
def face_section(z):
    k=next((i for i in range(len(FACE_LEVELS)-1) if FACE_LEVELS[i+1][0]>=z),len(FACE_LEVELS)-2)
    k=max(0,k); t=max(0,min(1,(z-FACE_LEVELS[k][0])/(FACE_LEVELS[k+1][0]-FACE_LEVELS[k][0])))
    rows=[FACE_LEVELS[max(0,min(len(FACE_LEVELS)-1,j))] for j in [k-1,k,k+1,k+2]]
    result=[]
    for d in [1,2,3]:
        value=.5*((2*rows[1][d])+(-rows[0][d]+rows[2][d])*t+(2*rows[0][d]-5*rows[1][d]+4*rows[2][d]-rows[3][d])*t*t+(-rows[0][d]+3*rows[1][d]-3*rows[2][d]+rows[3][d])*t*t*t)
        result.append(max(.002,value) if d<3 else value)
    return result

def old_face_y(x,z):
    rx,ry,cy=face_section(z); f=sqrt(max(0,1-(x/rx)**2)); front=f**5
    cheek=(exp(-((x-.078)/.034)**2)+exp(-((x+.078)/.034)**2))*exp(-((z-1.047)/.03)**2)
    socket=(exp(-((x-.048)/.029)**2)+exp(-((x+.048)/.029)**2))*exp(-((z-1.086)/.019)**2)
    bridge=.009*exp(-(x/.011)**2-((z-1.066)/.027)**2)
    tip=.020*exp(-(x/.014)**2-((z-1.045)/.012)**2)
    ala=.004*(exp(-((x-.013)/.008)**2)+exp(-((x+.013)/.008)**2))*exp(-((z-1.039)/.008)**2)
    lips=.0012*exp(-(x/.021)**4-((z-1.010)/.008)**2)
    philtrum=.0014*exp(-(x/.006)**2-((z-1.023)/.008)**2)
    return cy-ry*f+front*(-.0055*cheek+.004*socket-bridge-tip-ala-lips+philtrum-.0015*exp(-((z-.984)/.019)**2))

def face_shift(p):
    # Broad continuous volume, rather than additional attached cheek/nose balls.
    x,y,z=p; front=smooth(.012,.075,-y)*smooth(.958,.985,z)
    cheeks=(exp(-((x-.071)/.034)**2)+exp(-((x+.071)/.034)**2))*exp(-((z-1.046)/.025)**2)
    bridge=exp(-(x/.015)**2-((z-1.070)/.032)**2)
    tip=exp(-(x/.017)**2-((z-1.045)/.014)**2)
    ala=(exp(-((x-.016)/.009)**2)+exp(-((x+.016)/.009)**2))*exp(-((z-1.039)/.009)**2)
    brow=(exp(-((x-.047)/.035)**2)+exp(-((x+.047)/.035)**2))*exp(-((z-1.112)/.013)**2)
    chin=exp(-(x/.034)**2-((z-.978)/.019)**2)
    return Vector((0,front*(-.0035*cheeks-.0035*bridge-.0055*tip-.0020*ala-.0018*brow-.0015*chin),0))

def new_face_y(x,z):
    y=old_face_y(x,z); return y+face_shift(Vector((x,y,z))).y

def triangle_count(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)

def geometry(o,evaluated=False):
    if not evaluated: return [tuple(o.matrix_world@v.co) for v in o.data.vertices]
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
    pts=[tuple(ev.matrix_world@v.co) for v in me.vertices]; ev.to_mesh_clear(); return pts

def weights(o):
    return [[(o.vertex_groups[g.group].name,round(g.weight,8)) for g in v.groups] for v in o.data.vertices]

def matrix_rows(m): return [[float(x) for x in row] for row in m]

def scene_contract(root):
    objects=[root]+list(root.children_recursive)
    return {o.name:{'type':o.type,'parent':o.parent.name if o.parent else None,
                    'parent_type':o.parent_type,'parent_bone':o.parent_bone,
                    'matrix_basis':matrix_rows(o.matrix_basis),
                    'matrix_parent_inverse':matrix_rows(o.matrix_parent_inverse),
                    'bones':{b.name:{'parent':b.parent.name if b.parent else None,'matrix_local':matrix_rows(b.matrix_local)} for b in o.data.bones} if o.type=='ARMATURE' else None}
            for o in objects}

def set_vertex_colors(o):
    attr=o.data.color_attributes.get('Col') or o.data.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='CORNER')
    material=o.data.materials[0].name
    values=[]
    for vertex in o.data.vertices:
        p=unproportion(o.matrix_world@vertex.co); x,y,z=p; color=Vector((1,1,1))
        if 'Face_' in material and o.parent and (o.parent.name=='Head' or o.name.endswith('_LidCover')):
            front=smooth(.008,.065,-y)
            cheek=(exp(-((x-.070)/.031)**2)+exp(-((x+.070)/.031)**2))*exp(-((z-1.048)/.022)**2)*front
            nose=exp(-(x/.025)**2-((z-1.045)/.018)**2)*front
            eye=(exp(-((x-.048)/.030)**2)+exp(-((x+.048)/.030)**2))*exp(-((z-1.074)/.011)**2)*front
            temple=exp(-((abs(x)-.112)/.016)**2-((z-1.081)/.044)**2)*front
            color-=Vector((.003,.120,.145))*cheek
            color-=Vector((.002,.078,.105))*nose
            color-=Vector((.020,.032,.034))*eye
            color-=Vector((.016,.029,.032))*temple
        elif any(s in material for s in ['Coat_','Cape_','Hood_','Trousers_','Scarf_','Gloves_']):
            # Modulation is broad and aperiodic at silhouette scale; fabric grain
            # remains the runtime shader's responsibility.
            shade=.974+.014*sin(x*29+z*11)*cos(y*31-z*7)+.009*sin(z*43+x*13)
            color=Vector((shade,shade,shade))
        values.append(tuple(max(.70,min(1.,c)) for c in color)+(1.,))
    for loop in o.data.loops: attr.data[loop.index].color=values[loop.vertex_index]
    o.data.color_attributes.active_color=attr
    return {'min':[min(v[i] for v in values) for i in range(4)],'max':[max(v[i] for v in values) for i in range(4)]}

def build():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE)); root=bpy.data.objects['TravelerRoot']
    original=[root]+list(root.children_recursive)
    before_contract=scene_contract(root)
    original_geometry={o.name:geometry(o) for o in original if o.type=='MESH'}
    original_weights={o.name:weights(o) for o in original if o.type=='MESH'}
    material_names=sorted({m.name for o in original if o.type=='MESH' for m in o.data.materials})
    # These runtime contacts and grasped rigid assemblies are intentionally exact.
    frozen_names=[o.name for o in original if o.type=='MESH' and
                  (o.name.startswith(('Boot','Leg_','Arm_','Lantern','ScarfTail')) and not o.name.startswith('Sleeve'))]
    original_blend_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    subdivision=[]
    for name,levels in [('Trouser_L',2),('Trouser_R',2),('Sleeve_L',1),('Sleeve_R',1),('TailoredTunic',1)]:
        obj=bpy.data.objects[name]; prior=[v.co.copy() for v in obj.data.vertices]
        prior_weights=weights(obj); old_count=len(prior)
        bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Cloth fold sampling; preserve source cage','SUBSURF'); mod.subdivision_type='SIMPLE'; mod.levels=levels
        # Run before the armature so added samples share interpolated bind weights.
        bpy.ops.object.modifier_move_up(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        tree=KDTree(len(obj.data.vertices))
        for vertex in obj.data.vertices: tree.insert(vertex.co,vertex.index)
        tree.balance(); current_weights=weights(obj); max_weight_error=0.; max_pos=0.
        for p,w in zip(prior,prior_weights):
            nearest,index,distance=tree.find(p); max_pos=max(max_pos,distance)
            a,b=dict(w),dict(current_weights[index])
            max_weight_error=max(max_weight_error,max([abs(a.get(k,0)-b.get(k,0)) for k in set(a)|set(b)] or [0]))
        assert max_pos<3e-7 and max_weight_error<2e-7,(name,max_pos,max_weight_error)
        subdivision.append({'mesh':name,'old_vertices':old_count,'new_vertices':len(obj.data.vertices),'retained_cage_position_error_m':max_pos,'retained_cage_weight_error':max_weight_error})

    changed=[]
    for obj in [o for o in original if o.type=='MESH']:
        name=obj.name; mat=obj.data.materials[0].name; inverse=obj.matrix_world.inverted()
        face_object=(obj.parent and obj.parent.name=='Head' and ('Face_' in mat or 'Eye_' in mat or name=='QuietSmile' or name=='Head_Hair_Indigo'))
        cloth=name in ['TailoredTunic','Sleeve_L','Sleeve_R','Trouser_L','Trouser_R']
        if not (face_object or cloth): continue
        maximum=0.
        for vertex in obj.data.vertices:
            world=obj.matrix_world@vertex.co; p=unproportion(world); before=p.copy()
            if face_object:
                # Brow and upper eyelid curves follow skin; swept hair above 1.14
                # and the cranial silhouette remain unchanged.
                if mat=='Traveler_Hair_Indigo':
                    if p.z<1.139 and p.y<-.05:
                        p+=face_shift(p)
                        if p.z<1.104:
                            p.z=1.086+(p.z-1.086)*.80
                else:
                    if mat=='Traveler_Eye_Ivory':
                        old_y=old_face_y(p.x,p.z)
                        p.z=1.086+(p.z-1.086)*(.82 if p.z>1.086 else .94)
                        p.y+=old_face_y(p.x,p.z)-old_y
                    if 'Eye_' in mat and mat!='Traveler_Eye_Ivory':
                        sign=-1 if p.x<0 else 1; center=Vector((sign*.048,0,1.087))
                        old_y=old_face_y(p.x,p.z)
                        p.x=center.x+(p.x-center.x)*.90; p.z=center.z+(p.z-center.z)*.94
                        p.y+=old_face_y(p.x,p.z)-old_y
                    p+=face_shift(p)
            elif name=='TailoredTunic':
                radius=sqrt(p.x*p.x+p.y*p.y); angle=atan2(p.x,-p.y)
                gate=smooth(.438,.485,p.z)*(1-smooth(.856,.905,p.z))
                front=smooth(.02,.075,-p.y)
                seam=1-exp(-(p.x/.024)**2)
                drape=.0062*sin(angle*7.1+p.z*5.2)*exp(-((p.z-.51)/.12)**2)
                tension=.0022*sin(p.z*58+abs(p.x)*19)*exp(-((p.z-.71)/.095)**2)*front
                diagonal=.0024*sin(p.z*43-p.x*37)*exp(-((p.z-.83)/.072)**2)*front
                radial=(drape+tension+diagonal)*gate*(.2+.8*seam)
                if radius>.02:
                    p.x+=p.x/radius*radial; p.y+=p.y/radius*radial
            elif name.startswith('Sleeve'):
                sign=-1 if name.endswith('L') else 1
                center_x=sign*(.247-(p.z-.66)*.23); center_y=-.018+(p.z-.66)*.10
                dx,dy=p.x-center_x,p.y-center_y; radius=sqrt(dx*dx+dy*dy); angle=atan2(dy,dx)
                gate=smooth(.589,.632,p.z)*(1-smooth(.843,.896,p.z))
                elbow=.0032*sin((p.z-.775)*92+angle*1.3)*exp(-((p.z-.78)/.060)**2)
                wrist=.0018*sin((p.z-.64)*104-angle*1.8)*exp(-((p.z-.645)/.040)**2)
                longitudinal=.0013*sin(angle*5.2+p.z*8)*exp(-((p.z-.73)/.15)**2)
                if radius>.012:
                    delta=(elbow+wrist+longitudinal)*gate
                    p.x+=dx/radius*delta; p.y+=dy/radius*delta
            elif name.startswith('Trouser'):
                sign=-1 if name.endswith('L') else 1; center_x=sign*.083
                dx,dy=p.x-center_x,p.y-.008; radius=sqrt(dx*dx+dy*dy); angle=atan2(dy,dx)
                gate=smooth(.235,.265,p.z)*(1-smooth(.442,.487,p.z))
                knee=.0035*sin((p.z-.345)*99+angle*1.2)*exp(-((p.z-.345)/.062)**2)
                ankle=.0030*sin((p.z-.27)*106-angle*1.7)*exp(-((p.z-.27)/.040)**2)
                drape=.0012*sin(angle*4.3+p.z*8)*exp(-((p.z-.36)/.15)**2)
                if radius>.01:
                    delta=(knee+ankle+drape)*gate
                    p.x+=dx/radius*delta; p.y+=dy/radius*delta
            point=proportion(p); maximum=max(maximum,(point-world).length)
            vertex.co=inverse@point
        obj.data.update(); changed.append({'mesh':name,'max_displacement_m':maximum})

    # Broad skin ribbons give the eye socket actual lid thickness and transition
    # into the existing continuous face. Join to the existing skin renderer.
    verts=[]; faces=[]; arc_count=32; row_count=5
    for side in [-1,1]:
        for upper in [True,False]:
            start=len(verts); sign=1 if upper else -1
            for row in range(row_count):
                t=row/(row_count-1)
                for k in range(arc_count+1):
                    angle=k*pi/arc_count; width=.0235+.0028*t
                    height=(.0114 if upper else .0097)+(.0048 if upper else .0022)*t
                    x=side*.048+width*cos(angle); z=1.086+sign*height*sin(angle)
                    lift=((.0010+.0008*sin(pi*t)) if upper else (.00042+.0004*sin(pi*t)))*sin(angle)**.8*(1-t)**.75
                    y=new_face_y(x,z)-lift-.00004
                    verts.append(tuple(proportion(Vector((x,y,z)))))
            for row in range(row_count-1):
                for k in range(arc_count):
                    i=start+row*(arc_count+1)+k
                    faces.append((i,i+1,i+arc_count+2,i+arc_count+1) if upper else (i+1,i,i+arc_count+1,i+arc_count+2))
    mesh=bpy.data.meshes.new('V6_SoftSocketLids'); mesh.from_pydata(verts,[],faces); mesh.update()
    lids=bpy.data.objects.new('V6_SoftSocketLids',mesh); bpy.context.collection.objects.link(lids)
    lids.data.materials.append(bpy.data.materials['Traveler_Face_PorcelainCream'])
    for polygon in mesh.polygons: polygon.use_smooth=True
    face=bpy.data.objects['Head_Face_PorcelainCream']
    bpy.ops.object.select_all(action='DESELECT'); face.select_set(True); lids.select_set(True)
    bpy.context.view_layer.objects.active=face; bpy.ops.object.join()

    # Replace the angular four-segment eyebrow islands with smooth, tapered
    # natural arcs. Hair, temple locks and lashes remain the existing assembly.
    hair=bpy.data.objects['Head_Hair_Indigo']; bm=bmesh.new(); bm.from_mesh(hair.data)
    seen=set(); remove=[]
    for seed in bm.verts:
        if seed in seen: continue
        island=[]; stack=[seed]; seen.add(seed)
        while stack:
            v=stack.pop(); island.append(v)
            for edge in v.link_edges:
                n=edge.other_vert(v)
                if n not in seen: seen.add(n); stack.append(n)
        points=[unproportion(hair.matrix_world@v.co) for v in island]
        if points and all(1.115<p.z<1.132 and abs(p.x)<.084 and p.y<-.053 for p in points): remove.extend(island)
    bmesh.ops.delete(bm,geom=remove,context='VERTS'); bm.to_mesh(hair.data); bm.free()
    bv=[]; bf=[]; count=20; sides=6
    for side in [-1,1]:
        start=len(bv); previous=None
        for k in range(count+1):
            t=k/count; x=side*.048+(.049*t-.026)
            z=1.119+.0045*sin(pi*t)+.001*(1-t)
            p=Vector((x,new_face_y(x,z)-.0013,z))
            radius=.00015+.0010*sin(pi*t)**.65
            for q in range(sides):
                angle=q*2*pi/sides
                bv.append(tuple(proportion(p+Vector((0,cos(angle)*radius*.50,sin(angle)*radius)))))
        for k in range(count):
            for q in range(sides):
                a=start+k*sides+q; b=start+k*sides+(q+1)%sides
                bf.append((a,b,b+sides,a+sides))
    brow_mesh=bpy.data.meshes.new('V6_SoftBrows'); brow_mesh.from_pydata(bv,[],bf); brow_mesh.update()
    brows=bpy.data.objects.new('V6_SoftBrows',brow_mesh); bpy.context.collection.objects.link(brows)
    brows.data.materials.append(bpy.data.materials['Traveler_Hair_Indigo'])
    for p in brow_mesh.polygons: p.use_smooth=True
    bpy.ops.object.select_all(action='DESELECT'); hair.select_set(True); brows.select_set(True)
    bpy.context.view_layer.objects.active=hair; bpy.ops.object.join()

    # Closed lids must follow the altered face too. Work in their full-closure
    # geometry, then restore the exact .001/.001/1 open transform contract.
    for side in ['L','R']:
        pivot=bpy.data.objects['Blink_'+side]; bind_scale=pivot.scale.copy()
        pivot.scale=(1,1,1); bpy.context.view_layer.update()
        for obj in [o for o in pivot.children if o.type=='MESH']:
            inverse=obj.matrix_world.inverted()
            for vertex in obj.data.vertices:
                p=unproportion(obj.matrix_world@vertex.co)
                sign=-1 if side=='L' else 1
                r=sqrt(((p.x-sign*.048)/.034)**2+((p.z-1.086)/.023)**2)
                p+=face_shift(p)
                p.y-=.0014*max(0,1-r*r)**1.5
                vertex.co=inverse@proportion(p)
            obj.data.update()
            if obj.name.endswith('_LidCover'):
                normals=[]; normal_matrix=obj.matrix_world.to_3x3().transposed()
                for vertex in obj.data.vertices:
                    p=unproportion(obj.matrix_world@vertex.co); x,y,z=p
                    r=sqrt(((x-sign*.048)/.034)**2+((z-1.086)/.023)**2)
                    h=.00012
                    a=proportion(Vector((x+h,new_face_y(x+h,z),z)))-proportion(Vector((x-h,new_face_y(x-h,z),z)))
                    b=proportion(Vector((x,new_face_y(x,z+h),z+h)))-proportion(Vector((x,new_face_y(x,z-h),z-h)))
                    skin_normal=a.cross(b).normalized()
                    target=(normal_matrix@skin_normal).normalized()
                    blend=smooth(.62,.95,r)
                    normals.append(tuple(vertex.normal.lerp(target,blend).normalized()))
                obj.data.normals_split_custom_set_from_vertices(normals)
        pivot.scale=bind_scale; bpy.context.view_layer.update()

    bpy.context.view_layer.update(); current=[root]+list(root.children_recursive)
    after_contract=scene_contract(root)
    assert before_contract==after_contract,'Object/bone transform or parenting contract changed'
    blink_scales={name:bpy.data.objects[name].scale.copy() for name in ['Blink_L','Blink_R']}
    for name in blink_scales: bpy.data.objects[name].scale=(1,1,1)
    bpy.context.view_layer.update()
    color_report={o.name:set_vertex_colors(o) for o in current if o.type=='MESH'}
    for name,scale in blink_scales.items(): bpy.data.objects[name].scale=scale
    bpy.context.view_layer.update()
    # The node graph mirrors runtime relative vertex color multiplication. This
    # is still an FBX/glTF asset; generated vertex colors, not Blender bump alone,
    # carry the principal face color treatment into Unity.
    for name in material_names:
        mat=bpy.data.materials[name]; tree=mat.node_tree; bsdf=tree.nodes.get('Principled BSDF')
        if name=='Traveler_Eye_AmberRim':
            # A restrained chestnut limbal transition replaces the bright ring
            # that made the existing concentric iris layers read as beads.
            mat.diffuse_color=(.265,.155,.078,1)
            bsdf.inputs['Base Color'].default_value=mat.diffuse_color
        node=tree.nodes.new('ShaderNodeVertexColor'); node.layer_name='Col'; node.label='Unity COLOR_0 relative paint'
        mul=tree.nodes.new('ShaderNodeMixRGB'); mul.blend_type='MULTIPLY'; mul.inputs[0].default_value=1
        mul.inputs[1].default_value=bsdf.inputs['Base Color'].default_value
        tree.links.new(node.outputs['Color'],mul.inputs[2]); tree.links.new(mul.outputs['Color'],bsdf.inputs['Base Color'])
        if 'Face_' in name:
            bsdf.inputs['Subsurface Weight'].default_value=.065
            bsdf.inputs['Subsurface Radius'].default_value=(1,.45,.24)
            bsdf.inputs['Roughness'].default_value=.76
            bsdf.inputs['Specular IOR Level'].default_value=.22
    # Existing procedural cloth bump was a preview-only exaggerated material.
    # Keep preview's microstructure finer than the newly modelled major folds.
    for name in material_names:
        if any(tag in name for tag in ['Coat_','Cape_','Hood_','Trousers_','Scarf_','Gloves_']):
            for node in bpy.data.materials[name].node_tree.nodes:
                if node.type=='BUMP': node.inputs['Distance'].default_value=.00045; node.inputs['Strength'].default_value=.18
                elif node.type=='TEX_NOISE': node.inputs['Scale'].default_value=240

    preserved=[]
    for name in frozen_names:
        obj=bpy.data.objects[name]; a=original_geometry[name]; b=geometry(obj)
        delta=max((Vector(x)-Vector(y)).length for x,y in zip(a,b))
        assert len(a)==len(b) and delta<1e-8 and original_weights[name]==weights(obj),(name,delta)
        preserved.append({'mesh':name,'position_max_error_m':delta,'weights_unchanged':True})
    triangles=sum(triangle_count(o) for o in current if o.type=='MESH')
    assert triangles<=80000,triangles
    assert len([o for o in current if o.type=='MESH'])==62
    assert sorted({m.name for o in current if o.type=='MESH' for m in o.data.materials})==material_names
    for obj in current:
        if obj.type=='MESH' and any(m.type=='ARMATURE' for m in obj.modifiers):
            for vertex in obj.data.vertices:
                assert abs(sum(g.weight for g in vertex.groups)-1)<.000002,(obj.name,vertex.index)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in current: obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    # FBX material diffuse values stay the original base colors. Remap uses these
    # and keyword-enabled COLOR_0; it does not need to evaluate Blender nodes.
    saved=[]
    for name in material_names:
        m=bpy.data.materials[name]; p=m.node_tree.nodes.get('Principled BSDF')
        for link in list(p.inputs['Base Color'].links):
            saved.append((m,link.from_socket,p.inputs['Base Color'])); m.node_tree.links.remove(link)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,
        object_types={'MESH','EMPTY','ARMATURE'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
        use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',
        use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,
        primary_bone_axis='Y',secondary_bone_axis='X',colors_type='LINEAR',
        path_mode='COPY',embed_textures=True)
    # Export original constant base colors while color attributes are retained;
    # procedural node graphs are preview-only and not glTF material graphs.
    bpy.ops.export_scene.gltf(filepath=str(OUT/'traveler.glb'),export_format='GLB',
        use_selection=True,export_yup=True,export_apply=False,export_materials='EXPORT',
        export_extras=True,export_skins=True,export_animations=False,
        export_vertex_color='ACTIVE',export_all_vertex_colors=True)
    for m,a,b in saved: m.node_tree.links.new(a,b)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))
    report={'version':6,'source':str(SOURCE.relative_to(ROOT)), 'source_sha256':original_blend_sha,
        'triangles':triangles,'mesh_renderers':62,'skinned_meshes':28,'armatures':4,'bones':12,
        'material_names':material_names,'material_count':len(material_names),
        'contract_unchanged':True,'subdivision_preserves_source_cage_weights':subdivision,
        'frozen_contact_and_accessory_geometry':preserved,'changed_geometry':changed,
        'colors':color_report,'vertex_color_contract':{'name':'Col','domain':'CORNER','type':'FLOAT_COLOR','rgb':'linear relative albedo multiplication, neutral white','alpha':1,'range':'0.70..1.0, measured per mesh above'},
        'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'traveler.blend',OUT/'traveler.fbx',OUT/'traveler.glb']}}
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==original_blend_sha
    (OUT/'traveler-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('V6_EXPORTED '+json.dumps({'triangles':triangles,'renderers':62,'source_unchanged':True}),flush=True)

def render():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.device='CPU'
    scene.render.threads_mode='FIXED'; scene.render.threads=6; scene.cycles.samples=20
    scene.cycles.use_denoising=True; scene.render.resolution_x=900; scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    camera=bpy.data.objects['PREVIEW_Camera']; scene.camera=camera
    def shot(name,loc,target,scale):
        camera.location=loc; camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.type='ORTHO'; camera.data.ortho_scale=scale
        scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)
    shot('render-neutral.png',(1.45,-4.5,1.5),(0,0,.66),1.60)
    shot('render-portrait.png',(.65,-3.8,1.40),(0,-.015,1.135),.48)
    shot('render-side.png',(4.5,-.75,1.5),(0,0,.66),1.60)
    for name in ['Blink_L','Blink_R']: bpy.data.objects[name].scale=(1,1,1)
    shot('render-blink.png',(.65,-3.8,1.40),(0,-.015,1.135),.48)

if '--render-only' in ARGS:
    render()
else:
    build()
    if '--render' in ARGS: render()
