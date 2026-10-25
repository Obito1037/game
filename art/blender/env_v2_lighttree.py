"""Independent original gold-light-tree geometry exploration; no Unity writes.

Blender 4.5 --background --factory-startup --python art/blender/env_v2_lighttree.py
"""
import bpy,bmesh,math,random,json,hashlib,sys
from pathlib import Path
from mathutils import Vector,Quaternion

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v2/vegetation-geometry';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'art/generated/env-v1/assets/tree_gold/tree_gold/tree_gold_optimized.blend'
SOURCE_LO=Vector((-2.6977651119232178,-2.678226947784424,.0039684586226940155))
SOURCE_HI=Vector((2.7082040309906006,2.6721808910369873,4.997349262237549))
RNG=random.Random(630507)
LOD1_FIX_ONLY='--lod1-fix-only' in sys.argv
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def mat(name,color,roughness=.8,emission=None,strength=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
    if emission:bs.inputs['Emission Color'].default_value=(*emission,1);bs.inputs['Emission Strength'].default_value=strength
    return m
def mesh(name,vertices,faces,mats,indices=None,smooth=True):
    d=bpy.data.meshes.new(name);d.from_pydata(vertices,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o)
    for m in mats:d.materials.append(m)
    for p in d.polygons:p.use_smooth=smooth;p.material_index=indices[p.index] if indices else 0
    return o
def catmull(points,t):
    points=[Vector(p) for p in points];u=max(0,min(.999999,t))*(len(points)-1);i=int(u);f=u-i
    p0=points[max(0,i-1)];p1=points[i];p2=points[min(len(points)-1,i+1)];p3=points[min(len(points)-1,i+2)]
    return .5*((2*p1)+(-p0+p2)*f+(2*p0-5*p1+4*p2-p3)*f*f+(-p0+3*p1-3*p2+p3)*f*f*f)
def tangent(points,t):return (catmull(points,min(1,t+.008))-catmull(points,max(0,t-.008))).normalized()
def tube(name,points,radii,segments,sides,material):
    vertices=[];faces=[];old_u=None
    for j in range(segments+1):
        t=j/segments;p=catmull(points,t);direction=tangent(points,t)
        if old_u is None:
            old_u=Vector((1,0,0)) if abs(direction.x)<.85 else Vector((0,1,0))
        u=(old_u-direction*old_u.dot(direction)).normalized();v=direction.cross(u).normalized();old_u=u
        rr=t*(len(radii)-1);ri=min(len(radii)-2,int(rr));rf=rr-ri;r=radii[ri]*(1-rf)+radii[ri+1]*rf
        for k in range(sides):
            a=2*math.pi*k/sides;vertices.append(p+(u*math.cos(a)+v*math.sin(a))*r)
    for j in range(segments):
        for k in range(sides):n=(k+1)%sides;faces.append((j*sides+k,j*sides+n,(j+1)*sides+n,(j+1)*sides+k))
    faces.append(tuple(range(sides-1,-1,-1)));faces.append(tuple(segments*sides+k for k in range(sides)))
    return mesh(name,vertices,faces,[material])
def combine(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;return o
def tri(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def asset_objects(level=0):return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.endswith('_LOD'+str(level))]
def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
def normalized_normals(o):
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
def lod_decimate(o,target):
    bpy.context.view_layer.objects.active=o
    if tri(o)>target:
        d=o.modifiers.new('Budget-constrained geometry study','DECIMATE');d.ratio=target/tri(o);d.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=d.name)
    for p in o.data.polygons:p.use_smooth=True
def uv_wood(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.wm.read_factory_settings(use_empty=True)
root=bpy.data.objects.new('GoldenLightTree_Exploration',None);bpy.context.collection.objects.link(root)
BARK=mat('Study_BarkWarmGrey',(.22,.15,.10),.83)
LEAF=mat('Study_SilverGreenBlade',(.32,.48,.40),.73)
EDGE=mat('Study_ThinGoldLeafEdge',(.54,.35,.10),.5,(1,.61,.20),.12)
FRUIT=mat('Study_WarmAmberFruit',(.55,.27,.065),.38,(1,.52,.16),.78)
# Modest procedural bark variation, no image textures or borrowed meshes.
nodes=BARK.node_tree.nodes;links=BARK.node_tree.links;bs=nodes.get('Principled BSDF')
coord=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(6,6,.65);links.new(coord.outputs['Object'],scale.inputs[0])
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.65;links.new(scale.outputs[0],noise.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.17;ramp.color_ramp.elements[0].color=(.115,.083,.055,1);ramp.color_ramp.elements[1].position=.85;ramp.color_ramp.elements[1].color=(.29,.22,.15,1)
links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bs.inputs['Base Color'])
# Each authored blade carries small restrained silver-green differences.
attr=LEAF.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='BladeTint';LEAF.node_tree.links.new(attr.outputs['Color'],LEAF.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])

TRUNK=[(0,0,.02),(-.14,.04,.38),(-.26,.05,.82),(-.10,0,1.25),(.20,0,1.70),(.32,.04,2.16),(.18,.10,2.66),(-.05,.10,3.14),(-.18,.05,3.60),(.03,.10,4.12),(.23,.05,4.45)]
BRANCHES=[
 {'id':'low_flower','p':[(-.18,.02,1.06),(-.72,-.10,1.35),(-1.22,-.22,1.48),(-1.55,-.33,1.42)],'r':[.105,.075,.038,.018],'crown':False},
 {'id':'left_mid','p':[(.27,.04,2.08),(-.24,.14,2.46),(-.95,.28,2.62),(-1.72,.27,2.89),(-2.10,.10,3.35)],'r':[.145,.112,.074,.042,.022],'crown':True},
 {'id':'right_low','p':[(.13,.02,1.62),(.76,.16,2.09),(1.40,.08,2.44),(1.88,-.10,2.99)],'r':[.138,.099,.055,.021],'crown':True},
 {'id':'back_mid','p':[(.23,.07,2.48),(.12,.82,2.78),(-.20,1.58,3.12),(-.35,2.05,3.45)],'r':[.118,.085,.05,.024],'crown':True},
 {'id':'front_mid','p':[(.10,.06,2.67),(.52,-.54,3.01),(.83,-1.14,3.12),(1.00,-1.62,3.62)],'r':[.108,.075,.042,.020],'crown':True},
 {'id':'left_high','p':[(-.07,.09,3.18),(-.63,-.15,3.51),(-1.35,-.40,3.65),(-1.77,-.55,4.12)],'r':[.102,.071,.040,.020],'crown':True},
 {'id':'right_high','p':[(-.17,.06,3.55),(.43,.20,3.85),(1.05,.32,4.03),(1.64,.32,4.38)],'r':[.088,.061,.035,.018],'crown':True},
 {'id':'back_high','p':[(-.02,.09,4.02),(-.34,.55,4.15),(-.65,1.03,4.32),(-.86,1.45,4.55)],'r':[.062,.049,.033,.018],'crown':True},
 {'id':'crown_tip','p':[(-.17,.05,3.59),(.02,.10,4.10),(.23,.05,4.45),(.48,-.06,4.60)],'r':[.072,.051,.032,.016],'crown':True},
]
wood=[tube('Trunk',TRUNK,[.32,.30,.27,.235,.205,.175,.145,.12,.095,.065,.028],44,12,BARK)]
for branch in BRANCHES:wood.append(tube(branch['id'],branch['p'],branch['r'],18,10,BARK))
for i in range(5):
    angle=2*math.pi*i/5+.28;end=Vector((math.cos(angle),math.sin(angle),0))*RNG.uniform(.43,.67)
    pts=[(.02,0,.16),tuple(end*.45+Vector((0,0,.095))),tuple(end+Vector((0,0,.025)))]
    wood.append(tube('RootFlare',pts,[.17,.10,.015],9,8,BARK))
wood=combine(wood,'MainWood_LOD0');normalized_normals(wood)
bpy.context.view_layer.objects.active=wood
remesh=wood.modifiers.new('Continuous principal forks','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.019;remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=wood.modifiers.new('Soften voxel junctions','SMOOTH');smooth.factor=.55;smooth.iterations=3;bpy.ops.object.modifier_apply(modifier=smooth.name)
# Cut the organic root bottoms at a shared ground plane; merely translating the
# lowest remesh vertex had left the peripheral roots visibly suspended.
bm=bmesh.new();bm.from_mesh(wood.data)
cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=(0,0,0),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
rim=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
if rim:bmesh.ops.holes_fill(bm,edges=rim,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(wood.data);bm.free()
lod_decimate(wood,2950);uv_wood(wood)

sprigs=[]
for branch in BRANCHES:
    if not branch['crown']:continue
    for j,t in enumerate([.40,.66,.88]):
        p=catmull(branch['p'],t);direction=tangent(branch['p'],t);side=Vector((-direction.y,direction.x,0)).normalized()*(-1 if j%2 else 1)
        reach=RNG.uniform(.40,.63);end=p+side*reach+direction*RNG.uniform(.14,.29)+Vector((0,0,RNG.uniform(.15,.32)))
        # Lower canopy sprigs spread, upper sprigs remain below the original top.
        end.z=min(end.z,4.63)
        path=[p,p+side*reach*.35+direction*.10+Vector((0,0,.08)),end]
        sprigs.append({'id':branch['id']+'_side_'+str(j),'p':path,'kind':'twig','leaves':[7,8,8][j]})
    sprigs.append({'id':branch['id']+'_tip','p':[catmull(branch['p'],.78),catmull(branch['p'],.92),catmull(branch['p'],1)],'kind':'existing','leaves':7})
sprigs.append({'id':'flower_branch_two_leaves','p':[Vector(BRANCHES[0]['p'][-2]),Vector(BRANCHES[0]['p'][-1])],'kind':'existing','leaves':2})
LEAVES=[];twigs=[]
for sp in sprigs:
    if sp['kind']=='twig':twigs.append(tube('SecondaryTwig',sp['p'],[.025,.018,.009],5,6,BARK))
    for j in range(sp['leaves']):
        t=.32+(j/max(1,sp['leaves']-1))*.66;attach=catmull(sp['p'],t);along=tangent(sp['p'],t)
        side=Vector((-along.y,along.x,0)).normalized()*(1 if j%2 else -1)
        direction=(along*.56+side*.80+Vector((0,0,RNG.uniform(-.18,.20)))).normalized()
        base=attach+direction*RNG.uniform(.035,.065)
        length=RNG.uniform(.43,.62);width=length*RNG.uniform(.42,.51)
        if sp['id']=='flower_branch_two_leaves':length=.29;width=.13
        # Avoid an upright spear at the top of the tree.
        if base.z>4.45:direction.z=min(direction.z,.05);direction.normalize();length*=.85
        LEAVES.append({'attach':attach,'base':base,'direction':direction,'length':length,'width':width,'roll':RNG.uniform(-.72,.72),
                       'curl':RNG.uniform(-.060,.018),'tint':RNG.uniform(.88,1.12),'sprig':sp['id']})
twigmesh=combine(twigs,'SecondaryWood_LOD0');uv_wood(twigmesh)

def leaves_mesh(level):
    segments=5 if level==0 else 3;vertices=[];faces=[];midx=[];face_smooth=[];colors=[];uvcoords=[];petioles=[]
    cutoff=sorted(d['length'] for d in LEAVES)[int(len(LEAVES)*.20)]
    selected=[d for d in LEAVES if level==0 or d['length']>=cutoff or d['sprig']=='flower_branch_two_leaves']
    for leaf in selected:
        base=leaf['base'];along=leaf['direction'];right=along.cross(Vector((0,0,1))).normalized();normal=right.cross(along).normalized()
        rot=Quaternion(along,leaf['roll']);right=rot@right;normal=rot@normal
        def pt(u,v,bottom=False):
            half=leaf['width']*.5*(math.sin(math.pi*u)**.72)
            ridge=.014*math.sin(math.pi*u)*(1-abs(v))
            curve=leaf['curl']*u*u+.015*math.sin(math.pi*u)
            return base+along*(u*leaf['length'])+right*(v*half)+normal*(curve+ridge-(.0045 if bottom else 0))
        grids=[]
        for bottom in [False,True]:
            rows=[]
            for i in range(segments+1):
                u=i/segments;vs=[0] if i in [0,segments] else ([-1,0,1] if bottom else [-1,-.96,0,.96,1]);row=[]
                for v in vs:
                    row.append(len(vertices));vertices.append(pt(u,v,bottom));uvcoords.append((u,(v+1)*.5));colors.append((.32*leaf['tint'],.48*leaf['tint'],.40*leaf['tint'],1))
                rows.append(row)
            for i in range(segments):
                a,b=rows[i],rows[i+1]
                for k in range(2 if bottom else 4):
                    f=(a[0],b[k],b[k+1]) if len(a)==1 else ((a[k],b[0],a[k+1]) if len(b)==1 else (a[k],b[k],b[k+1],a[k+1]))
                    if bottom:f=tuple(reversed(f))
                    faces.append(f);midx.append(1 if k in [0,3] and not bottom else 0);face_smooth.append(True)
            grids.append(rows)
        for side in [0,-1]:
            for i in range(segments):
                faces.append((grids[0][i][side],grids[1][i][side],grids[1][i+1][side],grids[0][i+1][side]));midx.append(0);face_smooth.append(False)
        if level==0:petioles.append(tube('LeafPetiole',[leaf['attach'],leaf['base']],[.0055,.0035],1,3,BARK))
        else:
            # A closed triangular cone gives four valid triangles. Decimating
            # these millimetre stems created five export-cleaned degenerate faces.
            ring=[leaf['attach']+(right*math.cos(a)+normal*math.sin(a))*.005 for a in [0,2*math.pi/3,4*math.pi/3]]
            petioles.append(mesh('LeafPetiole',ring+[leaf['base']],[(0,2,1),(0,1,3),(1,2,3),(2,0,3)],[BARK]))
    obj=mesh('SilverGreenLeaves_LOD'+str(level),vertices,faces,[LEAF,EDGE],midx)
    # Both shells and the two side walls need consistent outward winding.
    # The first construction had 12 non-contiguous edges per closed blade.
    normalized_normals(obj)
    for p,smooth in zip(obj.data.polygons,face_smooth):p.use_smooth=smooth
    attr=obj.data.color_attributes.new(name='BladeTint',type='FLOAT_COLOR',domain='CORNER');uv=obj.data.uv_layers.new(name='UVMap')
    for p in obj.data.polygons:
        for li in p.loop_indices:
            vi=obj.data.loops[li].vertex_index;attr.data[li].color=colors[vi];uv.data[li].uv=uvcoords[vi]
    pet=combine(petioles,'LeafPetioles_LOD'+str(level));uv_wood(pet)
    normalized_normals(pet)
    return obj,pet,len(selected)

leaf0,pet0,leaf_count0=leaves_mesh(0)
FRUITS=[]
for i,sp in enumerate(sprigs):
    if i%3!=1 or len(FRUITS)>=11:continue
    attach=catmull(sp['p'],.78);pos=attach+Vector((.015,-.006,-.13));FRUITS.append((attach,pos,RNG.uniform(.035,.044)))
def fruits_mesh(level):
    objs=[]
    for attach,pos,radius in FRUITS:
        objs.append(tube('FruitStem',[attach,pos+Vector((0,0,radius*.8))],[.005,.003],1,5 if level==0 else 4,BARK))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8 if level==0 else 6,ring_count=5 if level==0 else 4,radius=radius,location=pos)
        o=bpy.context.object;o.name='SparseWarmFruit';o.scale=(.95,.95,1.18);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(FRUIT)
        for p in o.data.polygons:p.use_smooth=True
        objs.append(o)
    return combine(objs,'SparseWarmFruit_LOD'+str(level))
fruit0=fruits_mesh(0)

# LOD1 reduces secondary detail and the smallest inner blades rather than
# blindly decimating all thin edge rings into spikes.
wood1=wood.copy();wood1.data=wood.data.copy();bpy.context.collection.objects.link(wood1);wood1.name='MainWood_LOD1';lod_decimate(wood1,1180)
twig1=twigmesh.copy();twig1.data=twigmesh.data.copy();bpy.context.collection.objects.link(twig1);twig1.name='SecondaryWood_LOD1';lod_decimate(twig1,590)
leaf1,pet1,leaf_count1=leaves_mesh(1);fruit1=fruits_mesh(1)
# LOD1 petioles are authored cones, not decimated tiny cylinders.

flower=bpy.data.objects.new('Marker_FirstFlower_Study',None);bpy.context.collection.objects.link(flower);flower.location=BRANCHES[0]['p'][-1];flower.parent=root
for o in asset_objects(0)+asset_objects(1):o.parent=root
# Uniformly fit the original dimensional envelope; a bottom-centred root is an
# asset origin only, not a promise to preserve the old collider.
before_bounds=bounds(asset_objects(0));sizes=[before_bounds['max'][i]-before_bounds['min'][i] for i in range(3)]
horizontal=min(5.30/max(sizes[0],1e-5),5.24/max(sizes[1],1e-5),1.0);vertical=min(4.93/max(sizes[2],1e-5),1.0)
center=Vector(((before_bounds['min'][0]+before_bounds['max'][0])*.5,(before_bounds['min'][1]+before_bounds['max'][1])*.5,before_bounds['min'][2]))
for o in asset_objects(0)+asset_objects(1):
    for v in o.data.vertices:
        p=o.matrix_world@v.co-center;v.co=(p.x*horizontal,p.y*horizontal,p.z*vertical)
    o.matrix_world.identity()
flower.location=((flower.location.x-center.x)*horizontal,(flower.location.y-center.y)*horizontal,(flower.location.z-center.z)*vertical)
for o in asset_objects(1):o.hide_render=True;o.hide_set(True)
root.location=(0,0,0);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1

model_report={'lod0':{'triangles':sum(tri(o) for o in asset_objects(0)),'leaves':leaf_count0,'bounds':bounds(asset_objects(0)),
                       'objects':[{'name':o.name,'triangles':tri(o)} for o in asset_objects(0)]},
              'lod1':{'triangles':sum(tri(o) for o in asset_objects(1)),'leaves':leaf_count1,'bounds':bounds(asset_objects(1))},
              'materials':[m.name for m in [BARK,LEAF,EDGE,FRUIT]],'fruit_count':len(FRUITS),'first_flower_marker':list(flower.location),
              'pre_fit_bounds':before_bounds,'fit_scale':[horizontal,horizontal,vertical],
              'source_bounds':{'min':list(SOURCE_LO),'max':list(SOURCE_HI)}}
model_report['lod1']['ratio']=model_report['lod1']['triangles']/model_report['lod0']['triangles']
model_report['mesh_audit']=[]
for o in asset_objects(0)+asset_objects(1):
    bm=bmesh.new();bm.from_mesh(o.data);remaining=set(bm.verts);component_count=0
    while remaining:
        component_count+=1;stack=[remaining.pop()]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                other=e.other_vert(v)
                if other in remaining:remaining.remove(other);stack.append(other)
    model_report['mesh_audit'].append({'name':o.name,'connected_components':component_count,
        'boundary_edges':sum(e.is_boundary for e in bm.edges),'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),
        'non_contiguous_edges':sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
        'signed_volume':bm.calc_volume(signed=True),'ground_contact_vertices':sum((o.matrix_world@v.co).z<=.001 for v in bm.verts)})
    bm.free()
model_report['checks']={'lod0_budget_25000':model_report['lod0']['triangles']<=25000,
    'root_bottom_center':abs(model_report['lod0']['bounds']['min'][2])<1e-6,
    'inside_source_horizontal_envelope':all(model_report['lod0']['bounds']['min'][i]>=SOURCE_LO[i] and model_report['lod0']['bounds']['max'][i]<=SOURCE_HI[i] for i in [0,1]),
    'inside_source_height':model_report['lod0']['bounds']['max'][2]<=SOURCE_HI.z,
    'materials_3_to_5':3<=len(model_report['materials'])<=5,
    'closed_consistent_surface_winding':all(r['non_manifold_edges']==0 and r['non_contiguous_edges']==0 for r in model_report['mesh_audit']),
    'lod1_35_to_47_percent':.35<=model_report['lod1']['ratio']<=.47}
dump('geometry-manifest.json',model_report)
if not all(model_report['checks'].values()):raise RuntimeError(json.dumps(model_report['checks']))
blend=OUT/'gold_lighttree_geometry_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
for level in [0,1]:
    bpy.ops.object.select_all(action='DESELECT')
    for o in asset_objects(level):o.hide_set(False);o.select_set(True)
    root.select_set(True);flower.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'gold_lighttree_geometry_LOD{level}.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
        axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',bake_space_transform=False,
        use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    for o in asset_objects(1):o.hide_set(True)

CENTRE=(SOURCE_LO+SOURCE_HI)*.5;SPAN=max(SOURCE_HI-SOURCE_LO)
VIEWS={
 'whole':{'position':list(CENTRE+Vector((.20,-1,.20)).normalized()*SPAN*3),'look':list(CENTRE),'scale':SPAN*1.20},
 'canopy':{'position':list(Vector((0,0,3.40))+Vector((.30,-1,.10)).normalized()*SPAN*3),'look':[0,0,3.40],'scale':SPAN*.80},
 'side':{'position':[16,0,5.0],'look':[0,0,2.6],'scale':SPAN*1.20},
 'forks':{'position':[6,-10,3.0],'look':[0,0,2.4],'scale':3.8},
 'underside':{'position':[1.5,-8,1.0],'look':[0,0,3.6],'scale':4.2},
}
def setup_rig(kind):
    sc=bpy.context.scene
    for o in list(sc.objects):
        if o.type in ['LIGHT','CAMERA'] or o.name.startswith('Study_Ground'):bpy.data.objects.remove(o,do_unlink=True)
    sc.render.engine='CYCLES';sc.cycles.samples=28;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1000;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=0;sc.view_settings.gamma=1
    world=bpy.data.worlds.new('Study_'+kind);world.use_nodes=True;sc.world=world
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.055,.085,.16,1) if kind=='night' else (.22,.24,.25,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45 if kind=='night' else .7
    lamps=[((3,-4,3.2),240,1.2,(1,.55,.24))] if kind=='night' else [((3,-4,7),1300,5,(1,.95,.86)),((-4,-2,5),850,5,(.8,.88,1)),((0,4,6),1000,4,(1,.98,.9))]
    for pos,power,size,color in lamps:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;o.data.color=color;o.rotation_euler=(Vector((0,0,2.4))-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001));o=bpy.context.object;o.name='Study_Ground';o.data.materials.append(mat('Study_Ground_'+kind,(.075,.09,.085),.94))
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Study_Camera';cam.data.type='ORTHO';sc.camera=cam;return cam
def render_views(prefix,kind,names):
    cam=setup_rig(kind)
    for name in names:
        cfg=VIEWS[name];cam.location=cfg['position'];cam.rotation_euler=(Vector(cfg['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cfg['scale']
        bpy.context.scene.render.filepath=str(OUT/f'{prefix}-{kind}-{name}.png');bpy.ops.render.render(write_still=True)

if not LOD1_FIX_ONLY:
    render_views('candidate','neutral',['whole','canopy','side','forks','underside'])
    render_views('candidate','night',['whole','canopy'])
# Separate low-detail evidence uses the very same camera/light rig.
for o in asset_objects(0):o.hide_render=True
for o in asset_objects(1):o.hide_render=False
render_views('candidate-lod1','neutral',['whole'])

source_sha=sha(SOURCE);bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
if not LOD1_FIX_ONLY:
    render_views('reference','neutral',['whole','canopy'])
    render_views('reference','night',['whole','canopy'])
model_report.update({'status':'independent-exploration-not-approved-for-integration','script_sha256':sha(Path(__file__)),
                     'reference_source':str(SOURCE.relative_to(ROOT)),'reference_sha256':source_sha,'source_unchanged':sha(SOURCE)==source_sha,
                     'views':VIEWS,'render_resolution':[1000,1000],'night_lighting':'Matches vegetation-study: cold ambient .055/.085/.16 times .45; warm 240W area at (3,-4,3.2), RGB 1/.55/.24; no bloom.',
                     'collision_note':'New original geometry. No original tree collider, navigation footprint or interaction alignment is claimed preserved.',
                     'material_export_note':'Bark procedural grain and per-blade tint are Blender review features; generic FBX material shaders do not reproduce them automatically.',
                     'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.iterdir()) if p.suffix in ['.fbx','.blend','.png']]})
dump('geometry-manifest.json',model_report)
roundtrip=[]
for level in [0,1]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/f'gold_lighttree_geometry_LOD{level}.fbx'))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    roundtrip.append({'lod':level,'triangles':sum(tri(o) for o in meshes),'mesh_count':len(meshes),'bounds':bounds(meshes),
        'materials':sorted({m.name for o in meshes for m in o.data.materials if m}),
        'mesh_details':[{'name':o.name,'triangles':tri(o),'uv_layers':[u.name for u in o.data.uv_layers],
                         'color_attributes':[a.name for a in o.data.color_attributes]} for o in meshes],
        'checks':{'triangle_count':sum(tri(o) for o in meshes)==model_report['lod'+str(level)]['triangles'],
                  'mesh_count_5':len(meshes)==5,'root_exists':bpy.data.objects.get('GoldenLightTree_Exploration') is not None,
                  'study_flower_marker_exists':bpy.data.objects.get('Marker_FirstFlower_Study') is not None,
                  'bounds_within_0_1mm':all(abs(bounds(meshes)[key][axis]-model_report['lod'+str(level)]['bounds'][key][axis])<.0001 for key in ['min','max'] for axis in range(3))}})
dump('fbx-roundtrip.json',{'results':roundtrip,'all_pass':all(all(r['checks'].values()) for r in roundtrip)})
print('GOLD_LIGHTTREE_STUDY_DONE',model_report['lod0']['triangles'],model_report['lod1']['triangles'],flush=True)
