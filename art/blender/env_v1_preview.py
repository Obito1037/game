"""Offline arrangement previews only; not Unity screenshots or performance tests."""
import bpy, sys, math, json, random
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import env_v1_pack as P
ROOT=P.ROOT; OUT=P.OUT/'preview'
OUT.mkdir(parents=True,exist_ok=True)
data=P.make()
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def bv(v):return Vector((v[0],-v[2],v[1]))

def load(model):
    path=P.STAGE / model['path'].split('Environment/',1)[1]
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    obs=list(set(bpy.data.objects)-before)
    root=bpy.data.objects.new('_template_'+model['id'],None)
    bpy.context.collection.objects.link(root)
    for ob in obs:
        if ob.parent not in obs:
            m=ob.matrix_world.copy();ob.parent=root;ob.matrix_world=m
    return root,obs

templates={m['id']:load(m) for m in data['models']}
# FBX texture relative paths refer to the artist output folders; staging uses its
# own self-contained layout. Bind from the explicit manifest, as the Unity builder does.
specs={m['name']:m for m in data['materials']}
for m in list(bpy.data.materials):
    name=m.name
    if name not in specs and name.rsplit('.',1)[-1].isdigit():name=name.rsplit('.',1)[0]
    if name not in specs:continue
    spec=specs[name];m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    p=nt.nodes.new('ShaderNodeBsdfPrincipled');out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(p.outputs['BSDF'],out.inputs['Surface'])
    p.inputs['Base Color'].default_value=spec['color'];p.inputs['Roughness'].default_value=spec['roughness'];p.inputs['Metallic'].default_value=spec['metallic']
    p.inputs['Emission Color'].default_value=(*spec['emission'],1);p.inputs['Emission Strength'].default_value=spec['strength']
    for key,socket in [('texture','Base Color'),('emissionTexture','Emission Color')]:
        if spec[key]:
            tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P.STAGE/spec[key].split('Environment/',1)[1]),check_existing=True)
            tex.image.colorspace_settings.name='Non-Color' if key=='emissionTexture' else 'sRGB'
            nt.links.new(tex.outputs['Color'],p.inputs[socket])

def clone(asset,name,position,yaw=0,scale=1):
    if asset not in templates:return None
    src,obs=templates[asset];cp={}
    for old in [src]+obs:
        new=old.copy(); bpy.context.collection.objects.link(new); cp[old]=new
    for old,new in cp.items():
        new.parent=cp.get(old.parent)
        new.hide_render=False
    root=cp[src];root.name=name;root.location=bv(position);root.rotation_euler[2]=math.radians(yaw);root.scale=(scale,)*3
    return root

for i in data['instances']:clone(i['asset'],i['name'],i['position'],i['yaw'],i['scale'])
for a in data['anchors']:
    if a['kind']=='lamp':
        root=clone('copper_roadlamp',a['name'],a['position'])
        for ob in root.children_recursive:
            if ob.name.startswith('LampHead'):
                ob.rotation_euler=bv(a['forward']).to_track_quat('-Y','Z').to_euler()
            if ob.name.startswith('Structure'):ob.scale.z*=a['height']/3.8
        ld=bpy.data.lights.new(a['name']+'_light','SPOT');ld.energy=210;ld.color=(1,.63,.27)
        ld.spot_size=math.radians(56 if 'WanFeng' in a['name'] else 24);ld.spot_blend=.45;ld.shadow_soft_size=.15
        ob=bpy.data.objects.new(ld.name,ld);bpy.context.collection.objects.link(ob);ob.location=bv(a['position'])
        ob.rotation_euler=bv(a['forward']).to_track_quat('-Z','Y').to_euler()

for src,obs in templates.values():
    for ob in obs+[src]:bpy.data.objects.remove(ob,do_unlink=True)

def mat(name,c,emit=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1)
    p.inputs['Roughness'].default_value=.64;p.inputs['Emission Color'].default_value=(*c,1);p.inputs['Emission Strength'].default_value=emit
    return m

sea=mat('Preview_Sea',(.018,.055,.081))
sea.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(.012,.032,.052,1)
sea.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=.3
# Fade the finite sea plane into the same radiance as the night background.
# This avoids a visible square edge while preserving the intended near water.
nt=sea.node_tree;surface=nt.nodes.get('Principled BSDF');output=nt.nodes.get('Material Output')
geo=nt.nodes.new('ShaderNodeNewGeometry');distance=nt.nodes.new('ShaderNodeVectorMath');distance.operation='LENGTH'
nt.links.new(geo.outputs['Position'],distance.inputs[0])
fade=nt.nodes.new('ShaderNodeMapRange');fade.clamp=True
fade.inputs['From Min'].default_value=85;fade.inputs['From Max'].default_value=250
nt.links.new(distance.outputs['Value'],fade.inputs['Value'])
background=nt.nodes.new('ShaderNodeEmission');background.inputs['Color'].default_value=(.035,.055,.10,1);background.inputs['Strength'].default_value=.35
mix=nt.nodes.new('ShaderNodeMixShader');nt.links.new(fade.outputs['Result'],mix.inputs[0])
nt.links.new(surface.outputs['BSDF'],mix.inputs[1]);nt.links.new(background.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],output.inputs['Surface'])
bpy.ops.mesh.primitive_plane_add(size=600, location=(0,0,-.16));bpy.context.object.name='Preview_Sea';bpy.context.object.data.materials.append(sea)
# Small broken concentric contours keep the sea readable without expensive water effects.
foam=mat('Preview_Shore',(.10,.25,.29),.06)
random.seed(721)
for x,z in [(-30,3),(25,-18),(24,10),(3,-35),(-8,36)]:
    for j in range(3):
        bpy.ops.mesh.primitive_plane_add(size=1,location=(x+j*.4,-z-j*.7,-.145))
        ob=bpy.context.object;ob.scale=(1.5+j*.45,.035,1);ob.rotation_euler[2]=.2;ob.data.materials.append(foam)

world=bpy.data.worlds.new('Preview_Night');bpy.context.scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.035,.055,.10,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35

def unlit(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    p=nt.nodes.new('ShaderNodeEmission');p.inputs['Color'].default_value=(*color,1)
    out=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(p.outputs[0],out.inputs['Surface']);return m
def sky_mesh(name,verts,faces,material):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([bv(v) for v in verts],[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.data.materials.append(material)
    ob.visible_shadow=False
    return ob

# Offline analogue of the staged sky shader, not a Unity screenshot.
axis=Vector((-.30,.15,.94)).normalized();centre=axis*180
right=Vector((axis.z,0,-axis.x)).normalized();up=axis.cross(right).normalized();r=180*.066
dark=unlit('Preview_EarthDark',(.009,.017,.031));arc=unlit('Preview_EarthArc',(.32,.59,.85))
disk=[centre]+[centre+(right*math.cos(i*math.tau/96)+up*math.sin(i*math.tau/96))*r for i in range(96)]
sky_mesh('Preview_EarthDisk',disk,[(0,i+1,(i+1)%96+1) for i in range(96)],dark)
vs=[];fs=[];a=math.acos(-.065);b=math.acos(.065)
for i in range(81):
    t=i/80;ao=-a+2*a*t;ai=-b+2*b*t
    vs.append(centre-axis*.03+(right*math.cos(ao)+up*math.sin(ao))*r)
    vs.append(centre-axis*.03+(right*(-.13+math.cos(ai))+up*math.sin(ai))*r)
    if i:fs.append((2*i-2,2*i,2*i+1,2*i-1))
sky_mesh('Preview_EarthCrescent',vs,fs,arc)
stars=unlit('Preview_Stars',(.46,.60,.74));vs=[];fs=[]
random.seed(827)
for i in range(300):
    theta=random.uniform(0,math.tau);y=random.uniform(.035,.85);rr=math.sqrt(1-y*y)
    d=Vector((rr*math.cos(theta),y,rr*math.sin(theta)));c=d*170
    right=Vector((d.z,0,-d.x)).normalized();up=d.cross(right);size=random.uniform(.025,.075)
    j=len(vs);vs.extend([c+right*size,c+up*size,c-right*size,c-up*size]);fs.append((j,j+1,j+2,j+3))
sky_mesh('Preview_Stars',vs,fs,stars)
sun=bpy.data.lights.new('Preview_SoftFill','SUN');sun.energy=1.1;sun.color=(1,.84,.65);sun.angle=.25
ob=bpy.data.objects.new('Preview_SoftFill',sun);bpy.context.collection.objects.link(ob);ob.rotation_euler=(.38,-.5,-.5)
fill=bpy.data.lights.new('Preview_WarmFrontFill','SUN');fill.energy=.50;fill.color=(1,.91,.77);fill.angle=.6
ob=bpy.data.objects.new('Preview_WarmFrontFill',fill);bpy.context.collection.objects.link(ob);ob.rotation_euler=(.5,.75,2.8)

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=750;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
camd=bpy.data.cameras.new('PreviewCamera');cam=bpy.data.objects.new('PreviewCamera',camd);bpy.context.collection.objects.link(cam);scene.camera=cam
camd.clip_end=700
camd.sensor_fit='VERTICAL';camd.sensor_height=24
scene.render.film_transparent=False
scene.use_nodes=True
nt=scene.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='MEDIUM';gl.threshold=1.5
out=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],gl.inputs['Image']);nt.links.new(gl.outputs['Image'],out.inputs['Image'])
title=next(a for a in data['anchors'] if a['name']=='Cam_Title')
cam.location=bv(title['position']);cam.rotation_euler=bv(title['forward']).to_track_quat('-Z','Y').to_euler()
camd.lens=camd.sensor_height/(2*math.tan(math.radians(title['fov'])/2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island_offline.blend'))
views=[a for a in data['anchors'] if a['kind']=='camera']
if '--' in sys.argv:
    selected=sys.argv[sys.argv.index('--')+1:]
    if selected:views=[a for a in views if a['name'] in selected]
for a in views:
    cam.location=bv(a['position']);cam.rotation_euler=bv(a['forward']).to_track_quat('-Z','Y').to_euler()
    camd.lens=camd.sensor_height/(2*math.tan(math.radians(a['fov'])/2))
    scene.render.filepath=str(OUT/(a['name']+'.png'));bpy.ops.render.render(write_still=True)
    print('OFFLINE_PREVIEW='+a['name'],flush=True)
(OUT/'status.json').write_text(json.dumps(dict(source='Blender offline assembly',unity=False,missingAssets=json.loads((P.OUT/'manifest.json').read_text())['missingAssets'],views=[a['name'] for a in views]),indent=2),encoding='utf-8')
