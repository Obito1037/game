"""Original Borrowed Light Island. Coordinates are authored in Unity Y-up metres.
Run: blender --background --factory-startup --python-exit-code 1 --python this.py
"""
import bpy, bmesh, math, random, json, os, time, sys, argparse, hashlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path

random.seed(7319)
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'GameProject').is_dir())
parser=argparse.ArgumentParser(description='Author the original Borrowed Light island without overwriting release assets.')
parser.add_argument('--output-dir',default=str(ROOT/'art'/'generated'/'world-v6'))
parser.add_argument('--samples',type=int,default=32)
parser.add_argument('--skip-render',action='store_true',help='Freeze interchange assets without studio previews.')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=Path(args.output_dir).resolve()
assert OUT!=ROOT/'art'/'generated', 'Use a versioned output directory; release assets must remain intact.'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for d in list(bpy.data.materials): bpy.data.materials.remove(d)

def material(name, color, roughness=.82, metallic=0, emission=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness; p.inputs['Metallic'].default_value=metallic
    if emission:
        p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emission
    return m

MAT={}
palette={
 'soil':(.19,.24,.26),'soil_light':(.28,.34,.35),'rock':(.12,.21,.27),'rock_light':(.23,.34,.40),
 'rock_dark':(.075,.13,.20),'rock_blue':(.17,.27,.36),'grass':(.25,.37,.17),'grass_sage':(.29,.40,.23),
 'grass_light':(.43,.49,.25),'moss':(.36,.43,.19),'stone':(.40,.48,.48),'stone_light':(.53,.58,.54),
 'stone_dark':(.30,.38,.39),'plaster':(.79,.72,.53),'plaster_light':(.91,.84,.64),'wood':(.25,.18,.13),
 'wood_light':(.44,.31,.19),'wood_cut':(.58,.43,.27),'roof':(.12,.30,.29),'roof_light':(.18,.39,.35),
 'roof_dark':(.09,.22,.25),'leaf':(.24,.38,.17),'leaf_light':(.38,.51,.23),'leaf_gold':(.61,.55,.24),
 'leaf_dark':(.15,.27,.15),'leaf_blue':(.22,.36,.30),'flower_cream':(.95,.83,.53),'flower_coral':(.81,.35,.28),
 'leaf_meadow_deep':(.15,.225,.085),'leaf_meadow_olive':(.29,.37,.14),
 'leaf_meadow_young':(.38,.48,.205),'leaf_meadow_dry':(.43,.37,.19),
 'leaf_ground_sage':(.29,.40,.21),'leaf_ground_lime':(.38,.465,.20),
 'stone_path_slate':(.29,.345,.32),'stone_path_warm':(.355,.365,.315),
 'stone_path_ochre':(.395,.385,.315),'stone_path_edge':(.225,.27,.25),
 'stone_path_grain':(.43,.445,.37),
 'rock_hero_warm':(.39,.365,.305),'rock_hero_slate':(.32,.35,.32),
 'flower_lilac':(.49,.43,.65),'flower_blue':(.29,.55,.60),'stem':(.16,.34,.24),'book':(.30,.46,.49),
 'paper':(.91,.82,.59),'brass':(.62,.44,.19),'brass_light':(.86,.67,.31),'metal_dark':(.12,.22,.26),
 'quartz':(.42,.64,.62),'mushroom':(.72,.36,.24),'mushroom_spot':(.91,.77,.50),
}
for n,c in palette.items(): MAT[n]=material('BI_'+n,c, metallic=.58 if n.startswith('brass') else .05,roughness=.47 if n.startswith('brass') else .86)
MAT['window']=material('BI_window_honey',(.98,.62,.20),.4,0,1.4)
MAT['starlight']=material('BI_star_warm',(.98,.78,.36),.4,.25,1.2)
MAT['glass']=material('BI_sea_glass',(.25,.60,.62),.3,.2)

# A real UV image survives both FBX and GLB. Broad pigment blooms, fine granulation
# and fibres provide a quiet watercolor ground without conspicuous triangle colors.
texdir=OUT/'textures'; texdir.mkdir(exist_ok=True)
size=2048; rng=np.random.default_rng(41); accum=np.zeros((size,size),dtype=np.float32)
fields={}
coords=np.linspace(0,1,size,endpoint=False)
for cells,weight in [(5,.31),(13,.25),(35,.18),(90,.12),(256,.08),(680,.04)]:
    grid=rng.random((cells+1,cells+1),dtype=np.float32)
    p=coords*cells; ids=np.floor(p).astype(int); t=p-ids; t=t*t*(3-2*t)
    rows=grid[:,ids]*(1-t)[None,:]+grid[:,ids+1]*t[None,:]
    field=rows[ids,:]*(1-t)[:,None]+rows[ids+1,:]*t[:,None]
    accum+=field*weight
    if cells in (5,13,35,90): fields[cells]=field.copy()
accum+=rng.normal(0,.025,(size,size)).astype(np.float32)
# A higher middle-value meadow gives moonlight a visible surface to illuminate.
# Large grass/olive masses, medium moss islands and tiny mineral grains are
# authored independently, instead of multiplying a dark uniform green wash.
dark=np.array([.25,.315,.17]); light=np.array([.44,.50,.285])
tone=np.clip((fields[5]*.55+fields[13]*.30+fields[35]*.15-.18)*1.65,0,1)
rgb=dark[None,None,:]+(light-dark)[None,None,:]*tone[:,:,None]
moss_weight=np.clip((fields[13]-.49)*2.3+(fields[35]-.5)*.45,0,.68)
moss_rgb=np.array([.38,.425,.235])[None,None,:]+(fields[90][:,:,None]-.5)*np.array([.09,.085,.045])[None,None,:]
rgb=rgb*(1-moss_weight[:,:,None])+moss_rgb*moss_weight[:,:,None]
rgb+=(accum[:,:,None]-.5)*np.array([.065,.075,.04])[None,None,:]
rgb+=(fields[90][:,:,None]-.5)*np.array([.08,.09,.045])[None,None,:]
gx,gz=np.meshgrid(coords*18-9,coords*18-9)
path_layout=[[(0,-6),(0,-3.6),(-1,-1.7),(-1.7,-.8)],[(-1,.9),(-2.4,1.8),(-3.9,2.5),(-4.1,2.9)],[(1.6,0),(3.6,-.4),(5.4,-1.8),(6.1,-3.35)],[(-1.6,-.3),(-3.7,-.4),(-5.8,.1)]]
dist=np.full((size,size),30,dtype=np.float32)
for route in path_layout:
    for (ax,az),(bx,bz) in zip(route[:-1],route[1:]):
        dx,dz=bx-ax,bz-az; t=np.clip(((gx-ax)*dx+(gz-az)*dz)/(dx*dx+dz*dz),0,1)
        dist=np.minimum(dist,np.sqrt((gx-ax-t*dx)**2+(gz-az-t*dz)**2))
# Painterly but spatially truthful path wear: stone gaps show soil; its uneven
# margins dissolve into moss. Additional mud nests collect beneath the trees.
wear=np.clip((.77-dist+(fields[35]-.5)*.30+(fields[90]-.5)*.13)/.57,0,1)
soil=np.array([.39,.345,.255])[None,None,:]+(accum[:,:,None]-.5)*np.array([.13,.11,.085])[None,None,:]
rgb=rgb*(1-wear[:,:,None]*.92)+soil*(wear[:,:,None]*.92)
# Scuffed moss-and-leaf pockets beneath existing trees, keeping the same layout.
for tx,tz,rr in [(-6.55,3.9,1.15),(5.1,3.0,.7),(2.7,6.4,.95)]:
    pocket=np.clip((rr-np.sqrt((gx-tx)**2+(gz-tz)**2)+(fields[35]-.5)*.4)/.5,0,.64)
    rgb=rgb*(1-pocket[:,:,None])+np.array([.30,.33,.205])[None,None,:]*pocket[:,:,None]
height=(accum*.13+wear*.025).astype(np.float32)
# Original tiny oval clover, moss flecks and leaf litter are synthesized directly
# into this new texture. No existing image is read or edited.
for i in range(10800):
    px,py=rng.integers(5,size-5,size=2); rx=int(rng.integers(2,6)); ry=int(rng.integers(1,4)); ang=float(rng.random()*math.tau)
    x0,x1=max(0,px-rx-ry-2),min(size,px+rx+ry+3); y0,y1=max(0,py-rx-ry-2),min(size,py+rx+ry+3)
    yy,xx=np.mgrid[y0:y1,x0:x1]; xx=xx-px; yy=yy-py
    u=xx*math.cos(ang)+yy*math.sin(ang); v=-xx*math.sin(ang)+yy*math.cos(ang)
    mask=np.clip(1-(u/rx)**2-(v/ry)**2,0,1)**.28
    leaf=np.array(random.choice([(.46,.40,.23),(.35,.42,.22),(.49,.46,.30),(.27,.35,.18),(.38,.46,.26)]))
    rgb[y0:y1,x0:x1]=rgb[y0:y1,x0:x1]*(1-mask[:,:,None]*.70)+leaf*mask[:,:,None]*.70
    height[y0:y1,x0:x1]+=mask*.035
rgb=np.clip(rgb,0,1)
rgba=np.concatenate((rgb,np.ones((size,size,1))),axis=2).astype(np.float32)
img=bpy.data.images.new('Meadow Watercolor Pigment',width=size,height=size,alpha=True)
img.pixels.foreach_set(rgba.ravel()); img.filepath_raw=str(texdir/'meadow-watercolor.png'); img.file_format='PNG'; img.save()
node=MAT['grass'].node_tree.nodes.new('ShaderNodeTexImage'); node.image=img
MAT['grass'].node_tree.links.new(node.outputs['Color'],MAT['grass'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
dy,dx=np.gradient(height); scale=13.0
nrm=np.stack((-dx*scale,-dy*scale,np.ones_like(dx)),axis=2); nrm/=np.linalg.norm(nrm,axis=2)[:,:,None]
nrgba=np.concatenate((nrm*.5+.5,np.ones((size,size,1))),axis=2).astype(np.float32)
normalimg=bpy.data.images.new('Meadow Moss And Litter Normal',width=size,height=size,alpha=True)
normalimg.colorspace_settings.name='Non-Color'; normalimg.pixels.foreach_set(nrgba.ravel())
normalimg.filepath_raw=str(texdir/'meadow-normal.png'); normalimg.file_format='PNG'; normalimg.save()
texnormal=MAT['grass'].node_tree.nodes.new('ShaderNodeTexImage'); texnormal.image=normalimg
normalnode=MAT['grass'].node_tree.nodes.new('ShaderNodeNormalMap'); normalnode.inputs['Strength'].default_value=.45
MAT['grass'].node_tree.links.new(texnormal.outputs['Color'],normalnode.inputs['Color'])
MAT['grass'].node_tree.links.new(normalnode.outputs['Normal'],MAT['grass'].node_tree.nodes.get('Principled BSDF').inputs['Normal'])
texture_stats={'mean_linear_rgb':[float(v) for v in rgb.mean(axis=(0,1))]}
del gx,gz,dist,rgb,rgba,nrgba,nrm,soil,wear,rows,field,fields,moss_rgb,moss_weight,tone

def B(v): return (v[0],-v[2],v[1])
def tup(v): return tuple(v)

def ground_height(x,z):
    """Subtle living terrain; anchor, route and building footprints stay at Y=0."""
    if x*x+(z-.35)**2<2.05**2 or (-6.05<x<-2.2 and 2.25<z<5.85): return 0.0
    if x>4.5 and -4.5<z<-2.25: return 0.0
    for px,pz in [(-4.5,-2),(1.8,3.4),(4.7,-2.4),(-6.55,3.9),(5.1,3),(2.7,6.4),(-5.8,.15)]:
        if (x-px)**2+(z-pz)**2<.72**2: return 0.0
    distance=99.0
    for route in path_layout:
        for (ax,az),(bx,bz) in zip(route[:-1],route[1:]):
            dx,dz=bx-ax,bz-az; t=max(0,min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz)))
            distance=min(distance,math.hypot(x-ax-t*dx,z-az-t*dz))
    fade=max(0,min(1,(distance-.62)/.70))
    hummock=.024+.040*math.sin(x*.91+z*.34)*math.cos(z*.81-.3)+.020*math.sin(x*2.1-z*1.6)
    hummock+=.035*math.exp(-((x+3.5)**2+(z+3.6)**2)/3.1)+.028*math.exp(-((x-5.7)**2+(z-.8)**2)/2.3)
    return max(-.035,min(.115,hummock))*fade

class Mesh:
    def __init__(self,name): self.name=name; self.v=[]; self.f=[]; self.mi=[]; self.mats=[]
    def face(self,pts,mat):
        if mat not in self.mats: self.mats.append(mat)
        ids=[]
        for p in pts: ids.append(len(self.v)); self.v.append(B(p))
        self.f.append(ids); self.mi.append(self.mats.index(mat))
    def indexed(self,vs,fs,mat):
        if mat not in self.mats: self.mats.append(mat)
        start=len(self.v); self.v.extend(B(p) for p in vs)
        self.f.extend([[start+i for i in f] for f in fs]); self.mi.extend([self.mats.index(mat)]*len(fs))
    def box(self,c,s,mat,rot=0,bevel=0):
        x,y,z=c; sx,sy,sz=[a/2 for a in s]
        if bevel:
            a=min(bevel,sx*.8,sz*.8)
            ring=[(-sx+a,-sz),(sx-a,-sz),(sx,-sz+a),(sx,sz-a),(sx-a,sz),(-sx+a,sz),(-sx,sz-a),(-sx,-sz+a)]
        else: ring=[(-sx,-sz),(sx,-sz),(sx,sz),(-sx,sz)]
        vs=[]
        for yy in [-sy,sy]:
            for xx,zz in ring: vs.append((x+xx*math.cos(rot)-zz*math.sin(rot),y+yy,z+xx*math.sin(rot)+zz*math.cos(rot)))
        n=len(ring); fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        self.indexed(vs,fs,mat)
    def cylinder(self,a,b,r,mat,n=10,r2=None):
        a,b=Vector(a),Vector(b); axis=(b-a).normalized(); ref=Vector((0,1,0))
        if abs(axis.dot(ref))>.95: ref=Vector((1,0,0))
        u=axis.cross(ref).normalized(); w=axis.cross(u).normalized(); rr=r if r2 is None else r2
        vs=[]
        for p,rad in [(a,r),(b,rr)]:
            vs.extend(tup(p+(u*math.cos(i*math.tau/n)+w*math.sin(i*math.tau/n))*rad) for i in range(n))
        fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)); self.indexed(vs,fs,mat)
    def ellipsoid(self,c,r,mat,seg=9,rings=5,phase=0):
        vs=[]
        for j in range(rings+1):
            ph=math.pi*j/rings
            for i in range(seg):
                th=math.tau*i/seg+phase
                wob=1+random.uniform(-.045,.045)
                vs.append((c[0]+r[0]*math.sin(ph)*math.cos(th)*wob,c[1]+r[1]*math.cos(ph)*wob,c[2]+r[2]*math.sin(ph)*math.sin(th)*wob))
        fs=[]
        for j in range(rings):
            for i in range(seg): fs.append((j*seg+i,j*seg+(i+1)%seg,(j+1)*seg+(i+1)%seg,(j+1)*seg+i))
        self.indexed(vs,fs,mat)
    def torus(self,c,major,minor,mat,axis=(0,1,0),n=48,m=6,start=0,end=math.tau):
        c=Vector(c); axis=Vector(axis).normalized(); ref=Vector((1,0,0)) if abs(axis.x)<.95 else Vector((0,0,1))
        u=axis.cross(ref).normalized(); w=axis.cross(u).normalized(); vs=[]
        closed=abs(end-start-math.tau)<.01; count=n if closed else n+1
        for i in range(count):
            ang=start+(end-start)*i/n; rad=u*math.cos(ang)+w*math.sin(ang)
            for j in range(m):
                a=math.tau*j/m; vs.append(tup(c+rad*(major+minor*math.cos(a))+axis*(minor*math.sin(a))))
        fs=[]
        for i in range(n):
            ni=(i+1)%count
            for j in range(m): fs.append((i*m+j,ni*m+j,ni*m+(j+1)%m,i*m+(j+1)%m))
        self.indexed(vs,fs,mat)
    def finish(self,smooth=False):
        if not self.v: return None
        mesh=bpy.data.meshes.new(self.name); mesh.from_pydata(self.v,[],self.f); mesh.update()
        for n in self.mats: mesh.materials.append(MAT[n])
        for p,i in zip(mesh.polygons,self.mi): p.material_index=i; p.use_smooth=smooth
        bm=bmesh.new(); bm.from_mesh(mesh)
        if smooth: bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(mesh); bm.free()
        uv=mesh.uv_layers.new(name='WatercolorUV')
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                co=mesh.vertices[mesh.loops[li].vertex_index].co
                uv.data[li].uv=((co.x+9)/18,(-co.y+9)/18)
        obj=bpy.data.objects.new(self.name,mesh); bpy.context.collection.objects.link(obj); return obj

anchors={
 'Lamp_A':[-4.5,0,-2.0], 'Lamp_B':[1.8,0,3.4], 'Lamp_C':[4.7,0,-2.4],
 'LampHead_A':[-4.5,1.85,-2.0], 'LampHead_B':[1.8,1.85,3.4], 'LampHead_C':[4.7,1.85,-2.4],
 'Target_Path':[-1.8,.08,-3.2], 'Target_Bench':[-5.8,.1,.15], 'Target_Window':[-4.1,1.6,3.05],
 'Target_Dock':[6.9,.12,-3.35], 'Cabin':[-4.1,0,4.05], 'StarAltar':[0,.08,.35], 'Moon':[3.3,1.8,5.4],
 'PlayerSpawn':[0,.1,-5.6]
}
for name,p in anchors.items():
    o=bpy.data.objects.new('Anchor_'+name,None); bpy.context.collection.objects.link(o); o.location=B(p); o.empty_display_size=.16

# Sculpted floating stratum, with asymmetrical faceted layers and exposed gold veins.
terrain=Mesh('Island_Strata')
N=96
rings=[]
for level,(rad,height) in enumerate([(8.65,-.08),(9.0,-.52),(8.8,-1.0),(7.9,-1.7),(7.45,-2.35),(6.1,-3.2),(4.4,-4.0),(2.4,-4.65),(.35,-4.9)]):
    ring=[]
    for i in range(N):
        ang=math.tau*i/N; mod=1+.025*math.sin(ang*5+.3)+.025*math.cos(ang*9)
        rr=rad*mod+random.uniform(-.14,.14)
        ring.append((rr*math.cos(ang),height+random.uniform(-.12,.12),rr*math.sin(ang)))
    rings.append(ring)
for j in range(len(rings)-1):
    for i in range(N):
        pts=[rings[j][i],rings[j][(i+1)%N],rings[j+1][(i+1)%N],rings[j+1][i]]
        col=random.choices(['rock','rock_light','rock_blue','rock_dark'],[4,1,3,2])[0]
        terrain.face(pts[:3],col); terrain.face([pts[0],pts[2],pts[3]],col)
terrain.face(rings[-1],'rock_dark'); terrain.finish()

top=Mesh('Island_Meadow')
top_rings=[[(0,0,0)]]
MEADOW_RINGS=36
for j in range(1,MEADOW_RINGS+1):
    rr=j/MEADOW_RINGS*8.67; pts=[]
    for i in range(N):
        a=i*math.tau/N; r=rr*(1+.025*math.sin(5*a+.3)+.025*math.cos(9*a))
        x,z=r*math.cos(a),r*math.sin(a)
        h=ground_height(x,z)
        if j>MEADOW_RINGS-2: h=h*(MEADOW_RINGS-j)/2-.075*(j-(MEADOW_RINGS-2))/2
        pts.append((x,h,z))
    top_rings.append(pts)
for i in range(N): top.face([top_rings[0][0],top_rings[1][i],top_rings[1][(i+1)%N]],'grass')
for j in range(1,MEADOW_RINGS):
    for i in range(N):
        a,b=top_rings[j][i],top_rings[j][(i+1)%N]; c,d=top_rings[j+1][(i+1)%N],top_rings[j+1][i]
        col='grass'
        top.face([a,b,c],col); top.face([a,c,d],col)
top.finish(smooth=True)

# Radial cliff outcrops, moss caps and tiny drifting satellites.
edge=Mesh('Island_CliffGardens')
for i in range(42):
    a=random.uniform(0,math.tau); r=random.uniform(8.0,8.75); x,z=r*math.cos(a),r*math.sin(a)
    sx=random.uniform(.30,.85); sy=random.uniform(.12,.32)
    edge.ellipsoid((x,-.08,z),(sx,sy,sx*.75),random.choice(['stone_dark','rock_light','rock_blue']),7,4)
    if i%2==0: edge.ellipsoid((x,.03,z),(sx*.8,.08,sx*.60),'moss',7,3)
for x,y,z,s in [(-8.8,-2,-3,1.0),(7.6,-2.9,4.6,.8),(3,-4.4,-6,.52),(-4.7,-5.4,1.5,.42)]:
    edge.ellipsoid((x,y,z),(s,s*.72,s*.8),'rock_blue',7,4)
    edge.ellipsoid((x,y+s*.4,z),(s*.73,.13,s*.65),'moss',7,3)
for i in range(22):
    a=random.uniform(0,math.tau); y=random.uniform(-3.7,-.9); r=(8.9+y*.75)
    p=(r*math.cos(a),y,r*math.sin(a)); q=((r+.06)*math.cos(a+.018),y-.5,(r+.06)*math.sin(a+.018))
    edge.cylinder(p,q,.026,'brass',5,r2=.012)
edge.finish()

# A celestial brass meridian threads around the rock, an unmistakable island silhouette.
orbit=Mesh('Island_BrassMeridian')
last=None
for i in range(181):
    a=math.tau*i/180; p=(9.06*math.cos(a),-1.90+.43*math.sin(a-.3),9.06*math.sin(a))
    if last: orbit.cylinder(last,p,.026,'brass',6)
    last=p
for a in [3.7,4.5,5.4,6.0]:
    x,z=9.06*math.cos(a),9.06*math.sin(a); y=-1.9+.43*math.sin(a-.3)
    orbit.cylinder((x,y,z),(x,y-.45,z),.009,'brass_light',5)
    pts=[]
    for j in range(8):
        ang=j*math.tau/8; r=.16 if j%2==0 else .046
        pts.append((x+math.cos(ang)*r,y-.59+math.sin(ang)*r,z))
    orbit.face(pts,'brass_light')
orbit.finish()

# Stepping-stone paths consciously lead the eye between the house, altar and pier.
paths=Mesh('Garden_Walkways')
PATH_SEGMENTS=[]
stone_count=0
def worn_path_stone(center,length,width,angle,seed):
    """A connected worn slab with a shallow crown, soft shoulder and chipped outline."""
    rngstone=random.Random(5200+seed)
    count=rngstone.choice([8,9,10,11]); outline=[]
    for k in range(count):
        a=math.tau*k/count+rngstone.uniform(-.10,.10)
        radial=rngstone.uniform(.80,1.09)
        # Independent radii and an off-centre outline remove the regular cookie shape.
        outline.append((math.cos(a)*length*.5*radial,math.sin(a)*width*.5*radial))
    height=rngstone.uniform(.063,.084)
    topcol=rngstone.choice(['stone_path_slate','stone_path_warm','stone_path_ochre'])
    def transform(x,y,z):
        return (center.x+x*math.cos(angle)-z*math.sin(angle),y,center.z+x*math.sin(angle)+z*math.cos(angle))
    verts=[]
    tilt_x,tilt_z=rngstone.uniform(-.022,.022),rngstone.uniform(-.022,.022)
    corner_wear=[rngstone.uniform(-.005,.005) for _ in outline]
    # Four shared rings: buried foot, lower bulge, worn upper shoulder and broad
    # inner crown. The upper faces slope gently instead of reading as one cut lid.
    for level,factor in [(-.003,.86),(height*.28,1.0),(height*.70,.94),(height*.94,.60)]:
        for k,(x,z) in enumerate(outline):
            yy=level+tilt_x*x+tilt_z*z+corner_wear[k]*(.35 if factor==.60 else 1)
            if level<0:yy=max(-.006,yy)
            verts.append(transform(x*factor,yy,z*factor))
    centre=transform(rngstone.uniform(-.035,.035),height+.004,rngstone.uniform(-.025,.025))
    verts.append(centre)
    # All facets share vertices and the underside closes the volume. Recalculating
    # normals on disconnected single polygons had flipped 206 top triangles in v4.
    # A manifold slab gives the normal pass an unambiguous outward orientation.
    faces=[tuple(range(count))]
    for k in range(count):
        j=(k+1)%count
        faces.extend([(k,count+k,count+j,j),(count+k,2*count+k,2*count+j,count+j),
                      (2*count+k,3*count+k,3*count+j,2*count+j),(4*count,3*count+j,3*count+k)])
    paths.indexed(verts,faces,topcol)

def path_curve(points,width=.52):
    global stone_count
    for k in range(len(points)-1):
        a,b=Vector(points[k]),Vector(points[k+1]); n=max(1,int((b-a).length/.62))
        PATH_SEGMENTS.append((a,b))
        for i in range(n):
            p=a.lerp(b,(i+.15)/n); ang=math.atan2(b.z-a.z,b.x-a.x)
            stone_width=width*random.uniform(.88,1.14)
            random.choice(['stone','stone_light','stone_dark']) # retain scene random contract
            stone_angle=ang+random.uniform(-.28,.28)
            worn_path_stone(p,.51,stone_width,stone_angle,stone_count)
            stone_count+=1
path_curve([(0,0,-6),(0,0,-3.6),(-1,0,-1.7),(-1.7,0,-.8)])
path_curve([(-1.0,0,.9),(-2.4,0,1.8),(-3.9,0,2.5),(-4.1,0,2.9)])
path_curve([(1.6,0,0),(3.6,0,-.4),(5.4,0,-1.8),(6.1,0,-3.35)])
path_curve([(-1.6,0,-.3),(-3.7,0,-.4),(-5.8,0,.1)])
walkway_object=paths.finish()
# Broad, low curvature makes these worn stones read as volumes; preserve a soft
# faceted top while blending the narrower erosion bands at their perimeter.
for p in walkway_object.data.polygons:
    p.use_smooth=p.center.z<.053
walkway_tops=[p for p in walkway_object.data.polygons if p.center.z>.045 and abs(p.normal.z)>.90]
assert walkway_tops and all(p.normal.z>0 for p in walkway_tops), 'Stepping-stone top faces must point upward'

# Four original weathered boulders, deliberately outside the established routes.
# Their shared object adds one renderer and reuses existing stone materials.
# Sculptural displacement and vertex-normal curvature survive both FBX and GLB;
# no Blender-only noise nodes or new textures are involved.
hero=Mesh('Garden_HeroBoulders')
HERO_BOULDERS=[]
HERO_VERTEX_COLOURS=[]
def rock_noise(x,y,z,seed=0):
    """Deterministic continuous value noise, unrelated to scene placement RNG."""
    ix,iy,iz=math.floor(x),math.floor(y),math.floor(z)
    fx,fy,fz=x-ix,y-iy,z-iz
    fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy);fz=fz*fz*(3-2*fz)
    def h(a,b,c):
        n=(a*73856093)^(b*19349663)^(c*83492791)^(seed*2654435761)
        n=(n^(n>>13))*1274126177;n=(n^(n>>16))&0xffffffff
        return n/4294967295
    def mix(a,b,t):return a+(b-a)*t
    return mix(mix(mix(h(ix,iy,iz),h(ix+1,iy,iz),fx),mix(h(ix,iy+1,iz),h(ix+1,iy+1,iz),fx),fy),
               mix(mix(h(ix,iy,iz+1),h(ix+1,iy,iz+1),fx),mix(h(ix,iy+1,iz+1),h(ix+1,iy+1,iz+1),fx),fy),fz)
def smooth_minimum(a,b,k=.08):
    h=max(0,min(1,.5+.5*(b-a)/k));return b+(a-b)*h-k*h*(1-h)
template=bmesh.new();bmesh.ops.create_icosphere(template,subdivisions=5,radius=1)
template.verts.ensure_lookup_table();template.verts.index_update()
rock_directions=[v.co.copy().normalized() for v in template.verts]
rock_faces=[tuple(v.index for v in f.verts) for f in template.faces]
template.free()
for rock_index,(cxr,czr,rx,ry,rz,turn) in enumerate([
    (-1.20,-5.15,.46,.29,.41,.36),
    (1.20,-4.20,.51,.36,.44,-.48),
    (2.00,-2.70,.61,.39,.47,.70),
    (-2.30,-2.20,.43,.27,.37,-.24),
]):
    rr=random.Random(8803+rock_index); gy=ground_height(cxr,czr)
    phase=rr.uniform(0,math.tau)
    # Broad asymmetric fracture planes, with softened intersections. Uniform
    # icosphere topology gives these planes and narrow recesses enough support
    # without rings/poles or a flat tablet-like cap.
    planes=[(Vector((.12,.97,-.20)).normalized(),.83),
            (Vector((.94,.20,.15)).normalized(),.89),
            (Vector((-.82,.31,.46)).normalized(),.86),
            (Vector((.17,.32,.94)).normalized(),.88),
            (Vector((-.26,.18,-.96)).normalized(),.94)]
    vs=[]
    for direction in rock_directions:
        radius=1.035
        for normal,cut in planes:
            dot=direction.dot(normal)
            if dot>.1:radius=smooth_minimum(radius,(cut+math.sin(phase+normal.x*3)*.045)/dot,.085)
        u,v,w=direction*radius
        coarse=rock_noise(u*2.4+phase,v*2.4,w*2.4,17+rock_index)
        medium=rock_noise(u*7.5,v*7.5+phase,w*7.5,53+rock_index)
        fine=rock_noise(u*19,v*19,w*19+phase,71+rock_index)
        # A shallow broken bedding seam and one short oblique fracture. They
        # follow directions rather than adding evenly distributed pebble noise.
        seam_axis=v+.23*u-.12*w-.02+.075*(rock_noise(u*4,w*4,v*3,99)-.5)
        seam_mask=max(0,min(1,(rock_noise(u*2+phase,v*1.3,w*2,31)-.28)*2.8))
        seam=.024*math.exp(-(seam_axis/.047)**2)*seam_mask
        cross_axis=w+.43*u-.18+.045*math.sin(v*5+phase)
        cross_mask=max(0,min(1,(v+.1)*1.2))*max(0,min(1,(.85-u)*1.7))
        cross=.017*math.exp(-(cross_axis/.037)**2)*cross_mask
        eroded=(coarse-.5)*.060+(medium-.5)*.022+(fine-.5)*.007-seam-cross
        x=rx*u+direction.x*eroded;z=rz*w+direction.z*eroded
        y=gy+ry*.47+ry*.91*v+direction.y*eroded
        x+=rx*.07*v*w;z+=rz*.045*u*v
        vs.append((cxr+x*math.cos(turn)-z*math.sin(turn),y,czr+x*math.sin(turn)+z*math.cos(turn)))
        pigment=.81+(coarse-.5)*.23+(medium-.5)*.15+(fine-.5)*.04
        pigment*=1-min(.30,(seam+cross)*7.0)
        moss=max(0,min(1,(rock_noise(u*3+phase,v*3,w*3,113)-.52)*3))*max(0,min(1,(v-.1)*1.5))*.30
        colour=[pigment*(1-moss*.22),pigment*(1-moss*.05),pigment*(1-moss*.30)]
        HERO_VERTEX_COLOURS.append(tuple(max(.42,min(1,c)) for c in colour))
    fs=rock_faces
    # Each vertex carries continuous mineral/crevice pigment; there are no
    # hard-colour moss polygons and no additional texture assets.
    start=len(hero.v);hero.v.extend(B(p) for p in vs)
    for face in fs:
        mat='rock_hero_warm' if rock_index%2==0 else 'rock_hero_slate'
        if mat not in hero.mats:hero.mats.append(mat)
        hero.f.append([start+i for i in face]);hero.mi.append(hero.mats.index(mat))
    minv=[min(p[k] for p in vs) for k in range(3)];maxv=[max(p[k] for p in vs) for k in range(3)]
    route_clearance=min(math.hypot(cxr-a.x-max(0,min(1,((cxr-a.x)*(b.x-a.x)+(czr-a.z)*(b.z-a.z))/(b-a).length_squared))*(b.x-a.x),czr-a.z-max(0,min(1,((cxr-a.x)*(b.x-a.x)+(czr-a.z)*(b.z-a.z))/(b-a).length_squared))*(b.z-a.z)) for a,b in PATH_SEGMENTS)-max(rx,rz)*1.15
    assert route_clearance>.40, 'Hero boulder encroaches on route corridor'
    HERO_BOULDERS.append({'index':rock_index,'center_unity':[cxr,gy,czr],'bounds_min_unity':minv,'bounds_max_unity':maxv,'route_centerline_clearance_metres':route_clearance})
hero_object=hero.finish(smooth=True)
assert len(hero_object.data.vertices)==len(HERO_VERTEX_COLOURS),'Hero tint topology changed unexpectedly'

# Round brass inlaid observatory altar: engraved dial, radial ticks, armillary sphere.
altar=Mesh('Observatory_StoneAndBrass')
for rad,h,mat in [(1.72,.07,'stone_dark'),(1.57,.16,'stone'),(1.40,.26,'stone_light')]:
    altar.cylinder((0,h-.07,.35),(0,h,.35),rad,mat,64)
altar.torus((0,.273,.35),1.28,.025,'brass',n=80,m=5)
altar.torus((0,.275,.35),1.06,.012,'brass',n=80,m=4)
for i in range(48):
    a=math.tau*i/48; ri=1.12 if i%4==0 else 1.20
    altar.cylinder((ri*math.cos(a),.285,.35+ri*math.sin(a)),(1.265*math.cos(a),.285,.35+1.265*math.sin(a)),.013 if i%4==0 else .007,'brass',5)
for i in range(8):
    a=math.tau*i/8; d=Vector((math.cos(a),0,math.sin(a))); side=Vector((-math.sin(a),0,math.cos(a)))
    c=Vector((0,.285,.35)); length=.90 if i%2==0 else .63
    altar.face([tup(c),tup(c+d*length+side*.01),tup(c+d*.29+side*.085)],'brass_light')
    altar.face([tup(c),tup(c+d*length-side*.01),tup(c+d*.29-side*.085)],'brass')
altar.cylinder((0,.29,.35),(0,.56,.35),.33,'metal_dark',16,r2=.22)
altar.cylinder((0,.56,.35),(0,.65,.35),.26,'brass',24)
altar.torus((0,1.12,.35),.56,.027,'brass_light',axis=(0,0,1),n=60,m=6)
altar.torus((0,1.12,.35),.56,.018,'brass',axis=(.55,.25,.83),n=60,m=5)
altar.torus((0,1.12,.35),.43,.015,'brass_light',axis=(0,1,0),n=60,m=5)
altar.cylinder((-.44,.68,.35),(.44,1.56,.35),.015,'brass_light',8)
altar.ellipsoid((0,1.12,.35),(.13,.13,.13),'quartz',12,8)
altar.ellipsoid((-.45,.67,.35),(.05,.05,.05),'brass_light',8,4)
altar.ellipsoid((.45,1.57,.35),(.06,.06,.06),'starlight',8,4)
altar.finish()

# Cottage, every roof shingle, timber joint and sill individually modeled in shared meshes.
cx,cz=-4.1,4.05
house=Mesh('Cabin_PlasterAndFoundation'); wood=Mesh('Cabin_Timber'); roof=Mesh('Cabin_IndividualShingles')
house.box((cx,.12,cz),(3.4,.25,2.8),'stone_dark',bevel=.20)
house.box((cx,1.05,cz),(2.9,1.85,2.3),'plaster',bevel=.10)
for zz in [cz-1.15,cz+1.15]: house.face([(cx-1.45,1.9,zz),(cx,3.08,zz),(cx+1.45,1.9,zz)],'plaster_light')
for xx in [-1.40,1.40]:
    for zz in [-1.11,1.11]: wood.box((cx+xx,1.10,cz+zz),(.13,1.98,.13),'wood_light',bevel=.02)
for h in [.25,1.85]:
    wood.box((cx,h,cz-1.18),(2.95,.12,.12),'wood'); wood.box((cx,h,cz+1.18),(2.95,.12,.12),'wood')
for side in [-1,1]:
    # The ridge sits lengthways. Staggered overlapping teal clay shingles.
    for row in range(8):
        x0=side*(row/8*1.78); x1=side*((row+1.14)/8*1.78)
        y0=3.15-abs(x0)*.72; y1=3.15-abs(x1)*.72
        for col in range(12):
            z0=cz-1.45+col*.25+(.12 if row%2 else 0); z1=z0+.275
            rr=random.choice(['roof','roof','roof_light','roof_dark'])
            roof.face([(cx+x0,y0+.025,z0),(cx+x0,y0+.025,z1),(cx+x1,y1+.025,z1-.02),(cx+x1,y1+.025,z0+.02)],rr)
            roof.face([(cx+x1,y1+.025,z0+.02),(cx+x1,y1+.025,z1-.02),(cx+x1,y1-.025,z1-.02),(cx+x1,y1-.025,z0+.02)],'roof_dark')
for i in range(13): roof.cylinder((cx,3.16,cz-1.45+i*.245),(cx,3.16,cz-1.45+(i+1)*.245),.075,'roof_light',8)
for zz in [cz-1.48,cz+1.48]:
    for side in [-1,1]: wood.cylinder((cx,3.10,zz),(cx+side*1.83,1.82,zz),.075,'wood_light',8)
house.box((cx+.86,2.80,cz+.55),(.45,1.28,.48),'stone_dark',bevel=.05)
house.box((cx+.86,3.42,cz+.55),(.60,.12,.60),'stone',bevel=.04)
house.box((cx+.86,3.49,cz+.55),(.30,.035,.31),'rock_dark')
house.finish(); roof.finish()

# Front warm reading window. Separate mesh/material allows runtime dimming.
window=Mesh('Cabin_ReadingWindow_Glow')
window.box((cx,1.60,cz-1.183),(.79,.78,.025),'window',bevel=.12); window.finish()
for xx in [-.46,.46]: wood.box((cx+xx,1.60,cz-1.22),(.09,.99,.10),'wood')
for yy in [1.12,2.08]: wood.box((cx,yy,cz-1.22),(1.0,.09,.10),'wood')
wood.box((cx,1.60,cz-1.235),(.045,.85,.05),'wood_light')
wood.box((cx,1.60,cz-1.235),(.85,.045,.05),'wood_light')
wood.box((cx,1.09,cz-1.32),(1.11,.12,.37),'wood_cut',bevel=.04)
for side in [-1,1]:
    wood.box((cx+side*.65,1.59,cz-1.22),(.26,.94,.07),'roof_dark')
    for q in range(5): wood.box((cx+side*.65,1.23+q*.17,cz-1.28),(.23,.045,.035),'wood_light')
# Side door on right wall and its miniature stoop.
door=Mesh('Cabin_DoorAndAccessories')
door.box((cx+1.465,.90,cz-.20),(.035,1.55,.84),'wood',bevel=.08)
for i in range(6): door.box((cx+1.49,.9,cz-.55+i*.14),(.025,1.45,.12),'wood_light')
door.ellipsoid((cx+1.54,.91,cz+.02),(.04,.04,.04),'brass_light',8,4)
door.box((cx+1.68,.11,cz-.20),(.58,.16,1.10),'stone',bevel=.09)
door.box((cx+1.95,.035,cz-.20),(.36,.07,1.22),'stone_dark',bevel=.10)
# Book left open on a low table below the reading window.
door.box((cx, .68,cz-1.66),(.90,.08,.55),'wood_light',bevel=.04)
for dx in [-.32,.32]:
    for dz in [-.15,.15]: door.box((cx+dx,.38,cz-1.66+dz),(.07,.58,.07),'wood')
door.box((cx-.12,.745,cz-1.66),(.27,.045,.34),'paper',rot=-.1)
door.box((cx+.13,.745,cz-1.66),(.27,.045,.34),'paper',rot=.1)
for i in range(4): door.box((cx-.12,.773,cz-1.76+i*.045),(.20,.005,.006),'wood_light')
# Gable round attic window with brass radial mullions.
door.cylinder((cx,2.47,cz-1.19),(cx,2.47,cz-1.22),.22,'window',24)
door.torus((cx,2.47,cz-1.24),.24,.038,'wood_light',axis=(0,0,1),n=32,m=6)
door.cylinder((cx-.20,2.47,cz-1.26),(cx+.20,2.47,cz-1.26),.018,'wood',6)
door.cylinder((cx,2.27,cz-1.26),(cx,2.67,cz-1.26),.018,'wood',6)
door.finish(); wood.finish()

# Three cast-iron lamp stands. Rotating heads are intentionally absent for Unity.
for key in ['A','B','C']:
    x,_,z=anchors['Lamp_'+key]; lamp=Mesh('LampBase_'+key)
    lamp.cylinder((x,.015,z),(x,.12,z),.41,'stone_dark',12)
    lamp.cylinder((x,.12,z),(x,.19,z),.29,'brass',12)
    lamp.cylinder((x,.19,z),(x,.38,z),.18,'metal_dark',10,r2=.11)
    lamp.cylinder((x,.36,z),(x,1.78,z),.065,'metal_dark',10,r2=.045)
    for h in [.45,1.45,1.72]: lamp.torus((x,h,z),.075,.018,'brass_light',n=16,m=5)
    lamp.cylinder((x,1.78,z),(x,1.85,z),.12,'brass',12)
    for a in [0,math.pi/2,math.pi,math.pi*1.5]:
        lamp.ellipsoid((x+.23*math.cos(a),.16,z+.23*math.sin(a)),(.04,.03,.04),'brass_light',6,3)
    lamp.finish()

# Bench with bent slats and iron feet, warm scarf draped over one end.
bench=Mesh('Garden_Bench')
bx,bz=-5.8,.15
for i in range(4): bench.box((bx,.53,bz-.30+i*.18),(1.65,.085,.14),'wood_light',bevel=.025)
for i in range(3): bench.box((bx,.85+i*.15,bz+.36),(1.65,.12,.075),'wood_cut',bevel=.025)
for dx in [-.64,.64]:
    bench.cylinder((bx+dx,.05,bz-.27),(bx+dx,.60,bz-.27),.04,'metal_dark',8)
    bench.cylinder((bx+dx,.05,bz+.28),(bx+dx,1.22,bz+.34),.04,'metal_dark',8)
    bench.cylinder((bx+dx,.81,bz-.29),(bx+dx,.81,bz+.35),.035,'metal_dark',8)
bench.box((bx-.48,.60,bz-.06),(.30,.035,.62),'flower_coral',bevel=.04)
bench.box((bx-.48,.43,bz-.40),(.30,.35,.035),'flower_coral',bevel=.02)
for i in range(6): bench.cylinder((bx-.61+i*.05,.25,bz-.41),(bx-.61+i*.05,.17,bz-.41),.008,'flower_cream',4)
bench.finish()

# Overhanging dock with individually worn planks, ropes, mooring rings and a folded chart.
dock=Mesh('Cliff_Pier')
for i in range(21):
    x=5.0+i*.255; dock.box((x,.105,-3.35),(.235,.13,1.26+random.uniform(-.05,.05)),random.choice(['wood_light','wood_cut','wood']),bevel=.025)
    for zz in [-3.80,-2.90]: dock.cylinder((x,.18,zz),(x,.187,zz),.014,'metal_dark',6)
for z in [-3.81,-2.89]: dock.box((7.50,-.08,z),(5.4,.23,.14),'wood')
for x in [5.4,7.35,9.7]:
    for z in [-4.0,-2.70]:
        dock.cylinder((x,-.52,z),(x,.78,z),.075,'wood',9,r2=.06)
        dock.cylinder((x,.76,z),(x,.82,z),.095,'wood_cut',10)
for z in [-4.0,-2.70]:
    for start in [5.4,7.35]:
        end=7.35 if start==5.4 else 9.7
        last=(start,.62,z)
        for j in range(1,13):
            t=j/12; p=(start+(end-start)*t,.62-.18*math.sin(t*math.pi),z)
            dock.cylinder(last,p,.019,'paper',5); last=p
dock.torus((9.5,.205,-3.75),.12,.025,'brass',axis=(0,1,0),n=20,m=5)
dock.box((8.1,.20,-3.40),(.72,.03,.52),'paper',rot=.20,bevel=.04)
for i in range(5): dock.box((7.91+i*.085,.219,-3.40),(.025,.005,.35),'brass',rot=.20)
dock.finish()

# Real hierarchical branchwork and thousands of small folded leaves replace the
# former spherical canopy. The silhouettes retain the same three tree locations.
trees=Mesh('Garden_TreeTrunks'); canopies=Mesh('Garden_TreeCanopies'); leafskin=Mesh('Garden_CanopyLeafEdges')
def leaf_shape(mesh,center,length,width,angle,color,pitch=.12):
    c=Vector(center); direction=Vector((math.cos(angle),pitch,math.sin(angle))).normalized()
    side=direction.cross(Vector((0,1,0))).normalized(); normal=side.cross(direction).normalized()
    # A six-triangle shallow fold gives the leaf a central vein and soft tip.
    base=c-direction*length*.46; tip=c+direction*length*.54+normal*length*.04
    left1=c-direction*length*.17+side*width*.9-normal*width*.13
    left2=c+direction*length*.20+side*width*.65-normal*width*.22
    right2=c+direction*length*.20-side*width*.65-normal*width*.22
    right1=c-direction*length*.17-side*width*.9-normal*width*.13
    ridge=c+normal*width*.16
    mesh.indexed([tup(p) for p in [base,left1,left2,tip,right2,right1,ridge]],[(6,0,1),(6,1,2),(6,2,3),(6,3,4),(6,4,5),(6,5,0)],color)

def leaf_cluster(center,radii,count,colors,phase=0):
    c=Vector(center)
    for k in range(count):
        az=random.uniform(0,math.tau); yy=random.uniform(-1,1); rr=(max(.001,1-yy*yy)**.5)*random.random()**.28
        local=Vector((math.cos(az)*rr*radii[0],yy*radii[1],math.sin(az)*rr*radii[2]))
        p=c+local
        col=random.choices(colors,[2,5,2] if len(colors)==3 else [3,5,2,1])[0]
        leaf_shape(canopies,p,random.uniform(.16,.28),random.uniform(.048,.083),az+phase+random.uniform(-.8,.8),col,random.uniform(-.45,.50))

def curved_branch(points,radii,col='wood',segments=8):
    for i in range(len(points)-1):
        trees.cylinder(points[i],points[i+1],radii[i],col,segments,r2=radii[i+1])

def tree(x,z,kind):
    base=Vector((x,0,z))
    if kind in ('broad','gold'):
        gold=kind=='gold'; height=2.55 if gold else 3.50
        trunk=[base,base+Vector((.12,.72,0)),base+Vector((-.06,1.35,.10)),base+Vector((.12,height*.70,.04)),base+Vector((.04,height*.88,.14))]
        curved_branch(trunk,[.21,.175,.135,.085,.025],segments=10)
        branch_count=8 if gold else 10
        colors=['leaf','leaf_gold','leaf_light'] if gold else ['leaf_dark','leaf','leaf_light']
        for i in range(branch_count):
            az=i*2.39996+random.uniform(-.20,.20); span=random.uniform(.78,1.25)*(1 if gold else 1.16)
            branchbase=base+Vector((.03,1.28+(i%3)*.18,.04))
            elbow=base+Vector((math.cos(az)*span*.45,height*.73+random.uniform(-.11,.15),math.sin(az)*span*.44))
            end=base+Vector((math.cos(az)*span,height*.83+random.uniform(-.23,.20),math.sin(az)*span*.87))
            curved_branch([branchbase,elbow,end],[.075,.046,.018],col='wood_light',segments=7)
            for k in range(3):
                a=az+(k-1)*.80; reach=random.uniform(.32,.57)
                twig=end+Vector((math.cos(a)*reach,.18+random.uniform(-.12,.24),math.sin(a)*reach*.86))
                mid=end.lerp(twig,.5)+Vector((0,.10,0))
                curved_branch([end,mid,twig],[.021,.012,.0045],col='wood_light',segments=5)
                leaf_cluster(twig+Vector((0,.06,0)),(.43,.25 if gold else .32,.38),72 if gold else 79,colors,phase=az)
        # Smaller high crown pockets conceal branch joins without closing every gap.
        for i in range(4):
            a=i*2.4; c=base+Vector((math.cos(a)*.40,height*.96+random.uniform(-.08,.13),math.sin(a)*.38))
            leaf_cluster(c,(.44,.28,.40),86,colors,phase=a)
    else:
        trunk=[base,base+Vector((.04,1.2,.03)),base+Vector((-.04,2.5,.04)),base+Vector((.02,4.25,.02))]
        curved_branch(trunk,[.17,.13,.075,.011],segments=9)
        for tier in range(11):
            y=1.13+tier*.275; span=.78*(1-tier/13)+.09
            for k in range(3):
                a=k*math.tau/3+tier*1.63+random.uniform(-.18,.18)
                start=base+Vector((0,y,0)); end=base+Vector((math.cos(a)*span,y+.18+random.uniform(-.08,.1),math.sin(a)*span*.85))
                mid=start.lerp(end,.55)+Vector((0,-.05,0))
                curved_branch([start,mid,end],[.034,.021,.005],segments=5)
                for j in range(3):
                    t=.38+j*.25; c=start.lerp(end,t)+Vector((0,.13,0))
                    leaf_cluster(c,(span*.26,.21,span*.24),25,['leaf_dark','leaf_blue','leaf'],phase=a)
        leaf_cluster(base+Vector((.02,4.14,.02)),(.20,.26,.19),65,['leaf_dark','leaf_blue','leaf'])
    for j in range(5):
        a=j*math.tau/5+.15; end=(x+math.cos(a)*random.uniform(.43,.62),.014,z+math.sin(a)*random.uniform(.43,.62))
        curved_branch([(x,.21,z),(x+math.cos(a)*.23,.045,z+math.sin(a)*.23),end],[.09,.05,.008],segments=6)
    # Small dangling leaf sprigs punctuate the outline rather than a uniform shell.
    for i in range(34):
        a=random.uniform(0,math.tau); rr=1.30 if kind=='broad' else 1.08 if kind=='gold' else .52
        y=(2.7 if kind=='broad' else 2.05 if kind=='gold' else 2.4)+random.uniform(-.3,.45)
        p=Vector((x+math.cos(a)*rr,y,z+math.sin(a)*rr*.85))
        leaf_shape(leafskin,p,random.uniform(.17,.25),.060,a,random.choice(['leaf','leaf_light'] if kind!='gold' else ['leaf_gold','leaf_light']),-.35)

tree(-6.55,3.9,'broad'); tree(5.1,3.0,'cypress'); tree(2.7,6.4,'gold')
trees.finish(smooth=True); canopies.finish(); leafskin.finish()

# Moondial: a sculptural crescent built from a continuous tapering bronze arc.
moon=Mesh('MoonDial_Sculpture'); mx,mz=3.3,5.4
moon.cylinder((mx,0,mz),(mx,.16,mz),.55,'stone_dark',24)
moon.cylinder((mx,.16,mz),(mx,.9,mz),.055,'brass',10)
moon.torus((mx,1.80,mz),.85,.045,'brass',axis=(0,0,1),n=64,m=7)
vs=[]; fs=[]; n=56; m=8
for i in range(n+1):
    a=.24+((math.tau-.48)*i/n); thickness=.025+.17*(math.sin(math.pi*i/n)**1.2)
    for j in range(m):
        ph=j*math.tau/m; radial=.79+thickness*math.cos(ph)
        vs.append((mx+radial*math.cos(a),1.8+radial*math.sin(a),mz+thickness*.55*math.sin(ph)))
for i in range(n):
    for j in range(m): fs.append((i*m+j,(i+1)*m+j,(i+1)*m+(j+1)%m,i*m+(j+1)%m))
moon.indexed(vs,fs,'brass_light')
for a in [.4,1.8,3.4,4.8]:
    moon.ellipsoid((mx+.60*math.cos(a),1.80+.60*math.sin(a),mz),(.035,.035,.035),'starlight',6,4)
moon.finish()

# Flora is clustered along paths and cliff edges, leaving readable navigable negative space.
flora=Mesh('Garden_Wildflowers'); grass=Mesh('Garden_GrassTufts'); props=Mesh('Garden_MushroomsAndPebbles')
def flower(x,z,h,col):
    gy=ground_height(x,z)
    lean=Vector((random.uniform(-.035,.035),0,random.uniform(-.035,.035)))
    c=Vector((x,gy+h,z))+lean; prev=Vector((x,gy+.025,z))
    for j in range(1,4):
        t=j/3; q=Vector((x,gy+.025+(h-.025)*t,z))+lean*t*t
        flora.cylinder(tup(prev),tup(q),.0028,'stem',4,r2=.0018); prev=q
    phase=random.uniform(0,math.tau)
    for j in range(2):
        angle=phase+j*2.7; d=Vector((math.cos(angle),.65,math.sin(angle))); side=Vector((-math.sin(angle),0,math.cos(angle)))
        p=Vector((x,gy+h*(.35+j*.21),z))+lean*.3; end=p+d*random.uniform(.055,.085)
        flora.face([tup(p),tup(p.lerp(end,.45)+side*.018),tup(end),tup(p.lerp(end,.45)-side*.018)],'leaf_light')
    normal=Vector((random.uniform(-.32,.32),1,random.uniform(-.32,.32))).normalized()
    tangent=normal.cross(Vector((0,0,1))).normalized(); bitangent=normal.cross(tangent).normalized()
    petals=random.choice([5,6,7]); radius=random.uniform(.043,.073)
    for p in range(petals):
        a=p*math.tau/petals+phase; direction=tangent*math.cos(a)+bitangent*math.sin(a)
        side=normal.cross(direction).normalized(); length=radius*random.uniform(.88,1.13)
        vs=[]; fs=[]
        for k in range(5):
            t=k/4; center=c+direction*(.010+length*t)+normal*(.009+math.sin(t*math.pi)*.018-t*t*.010)
            width=(max(0,math.sin(t*math.pi))**.60)*length*.34+.0005
            vs.extend([tup(center-side*width),tup(center+side*width)])
        for k in range(4): fs.append((k*2,k*2+1,k*2+3,k*2+2))
        flora.indexed(vs,fs,col)
    flora.ellipsoid(tup(c+normal*.016),(.014,.010,.014),'brass_light',6,3)
clusters=[(-5.6,-1.35,1.1),(-3.4,-3.5,1.0),(1.3,-5.0,1.2),(5.4,-.9,1.1),(-6.4,5.1,.9),(2.0,5.5,.8),(6.6,1.2,.8),(-1.7,3.8,.8)]
def planting_allowed(x,z,margin=.45):
    if x*x+(z-.35)**2<1.95**2: return False
    if -5.9<x<-2.35 and 2.4<z<5.8: return False
    if 4.7<x and -4.4<z<-2.4: return False
    for a,b in PATH_SEGMENTS:
        p=Vector((x,0,z)); ab=b-a; tt=max(0,min(1,(p-a).dot(ab)/ab.length_squared))
        if (p-(a+ab*tt)).length<margin: return False
    return True

# Each bank has a few denser mini-colonies and quiet gaps. Mixed small flower
# silhouettes avoid eight conspicuously identical circular flower beds.
for ix,(cx1,cz1,rad) in enumerate(clusters):
    for k in range([39,45,48,32,43,38,33,40][ix]):
        a=random.uniform(0,math.tau); r=rad*math.sqrt(random.random())
        x,z=cx1+math.cos(a)*r,cz1+math.sin(a)*r*.78
        if not planting_allowed(x,z,.48): continue
        colony=.55+.45*math.sin(x*4.7+z*3.1+ix)
        if random.random()>.35+.65*colony: continue
        col=['flower_cream','flower_coral','flower_lilac','flower_blue'][ix%4]
        if random.random()<.18: col='flower_cream'
        flower(x,z,random.uniform(.12,.27)*( .78+colony*.38),col)

# Ribbon blades grow in coherent meadow banks with large quiet areas and
# variable blades, height, width, lean and local hue. No repeated grass clumps.
for i in range(5100):
    a=random.uniform(0,math.tau); r=math.sqrt(random.random())*8.45; x,z=r*math.cos(a),r*math.sin(a)
    if not planting_allowed(x,z): continue
    patch=.50+.24*math.sin(x*1.63+z*.54)+.20*math.cos(z*1.35-x*.41)+.10*math.sin(x*3.2+z*2.1)
    patch=max(0,min(1,patch))
    if random.random()>.19+patch*.72: continue
    h=random.uniform(.10,.29)*(.72+patch*.85)
    tint=random.choices(['leaf_meadow_olive','leaf_meadow_young','leaf_meadow_deep','leaf_meadow_dry'],[6,4 if patch<.5 else 3,1,.6])[0]
    gy=ground_height(x,z); breeze=.6+math.sin(x*.30+z*.17)*.45
    for j in range(random.choice([3,4,4,5])):
        angle=breeze+random.uniform(-1.65,1.65); width=random.uniform(.0028,.0062); lean=random.uniform(.045,.16)
        side=Vector((math.cos(angle),0,math.sin(angle))); bend=Vector((-math.sin(angle),0,math.cos(angle)))
        root=Vector((x+random.uniform(-.06,.06),gy+.008,z+random.uniform(-.06,.06)))
        blade_height=h*random.uniform(.62,1.18)
        vs=[]; fs=[]
        for k in range(5):
            t=k/4; c=root+Vector((0,blade_height*(t-.12*t*t-.055*t**4),0))+bend*(lean*t*t)+side*(.007*math.sin(t*math.pi))
            ribbon_side=side*math.cos(t*.44)+bend*math.sin(t*.44)
            w=width*(1-t**1.15); vs.extend([tup(c-ribbon_side*w),tup(c+ribbon_side*w)])
        for k in range(3): fs.append((k*2,k*2+1,k*2+3,k*2+2))
        fs.append((6,7,8)); grass.indexed(vs,fs,tint)
    # Sparse soft broad leaves are folded along a central vein, not rigid spikes.
    if i%17==0 and patch>.45:
        direction=Vector((math.cos(angle),0,math.sin(angle))); vs=[]; fs=[]
        for k in range(5):
            t=k/4; c=root+direction*(h*.6*t*t)+Vector((0,h*.65*math.sin(t*1.65),0)); w=.018*math.sin(t*math.pi)
            vs.extend([tup(c-side*w-Vector((0,.003,0))),tup(c+Vector((0,.006,0))),tup(c+side*w-Vector((0,.003,0)))])
        for k in range(4):
            fs.extend([(k*3,k*3+1,(k+1)*3+1,(k+1)*3),(k*3+1,k*3+2,(k+1)*3+2,(k+1)*3+1)])
        grass.indexed(vs,fs,'leaf')

# A short sward underlayer closes the bare gaps between the hero grass tufts.
# Each bent blade uses five triangles, with naturally broken colony edges.
# Deep green / olive / young-green / occasional straw colors remain compatible
# with BI_leaf remapping and do not require another texture or transparency.
for i in range(17800):
    a=random.uniform(0,math.tau); r=math.sqrt(random.random())*8.43
    x,z=r*math.cos(a),r*math.sin(a)
    if not planting_allowed(x,z,.34): continue
    colony=.51+.22*math.sin(x*2.4+z*.43)+.21*math.cos(z*1.95-x*.80)
    if random.random()>max(.30,min(.98,.52+colony*.52)): continue
    gy=ground_height(x,z); clump_height=random.uniform(.045,.155)
    clump_pattern=rock_noise(x*2.1+.3,0,z*2.1,421)
    clump_height*=.65+clump_pattern*.80
    col=random.choices(['leaf_meadow_deep','leaf_meadow_olive','leaf_meadow_young','leaf_meadow_dry'],[1,6,4,.3])[0]
    clump_vertex_start=len(grass.v);clump_face_start=len(grass.f)
    for j in range(3):
        angle=random.uniform(0,math.tau); side=Vector((math.cos(angle),0,math.sin(angle)))
        bend=Vector((-math.sin(angle),0,math.cos(angle))); width=random.uniform(.0036,.0077)
        root=Vector((x+random.uniform(-.065,.065),gy+.006,z+random.uniform(-.065,.065)))
        h=clump_height*random.uniform(.70,1.18)
        lean=random.uniform(.28,.65);vs=[]
        for t in [0,.38,.73]:
            c=root+Vector((0,h*(t-.08*t*t),0))+bend*h*lean*t*t
            c+=side*h*.035*math.sin(t*math.pi)
            ribbon_side=side*math.cos(t*.42)+bend*math.sin(t*.42)
            w=width*(1-t)**.82;vs.extend([tup(c-ribbon_side*w),tup(c+ribbon_side*w)])
        tip=root+Vector((0,h*.92,0))+bend*h*lean
        vs.append(tup(tip));grass.indexed(vs,[(0,1,3,2),(2,3,5,4),(4,5,6)],col)
    # Keep generation RNG intact while thinning the short sward into softer,
    # spatially coherent colonies. Tall tufts and creeping leaves remain intact.
    retention=.86+.14*clump_pattern
    selector=(math.sin(i*12.9898+4.1)*43758.5453)%1
    if selector>retention:
        del grass.v[clump_vertex_start:];del grass.f[clump_face_start:];del grass.mi[clump_face_start:]

# Creeping leaves form a readable near-ground layer between upright ribbons.
# Eight triangles give each creeping leaf a rounded oval outline and a soft vein.
groundcover=Mesh('Garden_CreepingMeadowLeaves')
for i in range(3300):
    a=random.uniform(0,math.tau); r=math.sqrt(random.random())*8.4
    x,z=r*math.cos(a),r*math.sin(a)
    if not planting_allowed(x,z,.31): continue
    bank=.5+.25*math.sin(x*1.7+z*2.1)+.20*math.cos(z*2.8-x*.75)
    if random.random()>.28+bank*.60: continue
    gy=ground_height(x,z)
    for j in range(random.choice([2,3,3])):
        angle=random.uniform(0,math.tau); length=random.uniform(.065,.14)
        direction=Vector((math.cos(angle),0,math.sin(angle))); side=Vector((-direction.z,0,direction.x))
        base=Vector((x+random.uniform(-.07,.07),gy+.015,z+random.uniform(-.07,.07)))
        tip=base+direction*length+Vector((0,random.uniform(.018,.045),0))
        middle=base.lerp(tip,.52)+Vector((0,.014,0)); width=length*random.uniform(.24,.39)
        ridge=middle+Vector((0,.004,0));outline=[base]
        for t in [.22,.52,.80]:
            center=base.lerp(tip,t)+Vector((0,.012*math.sin(t*math.pi),0))
            outline.append(center+side*width*math.sin(t*math.pi)**.80)
        outline.append(tip)
        for t in [.80,.52,.22]:
            center=base.lerp(tip,t)+Vector((0,.012*math.sin(t*math.pi),0))
            outline.append(center-side*width*math.sin(t*math.pi)**.80)
        groundcover.indexed([tup(p) for p in outline]+[tup(ridge)],[(k,(k+1)%8,8) for k in range(8)],random.choice(['leaf_ground_sage','leaf_ground_lime','leaf_meadow_olive']))
groundcover.finish()

# Individual feathered ferns occupy the sheltered margins of rocks and buildings.
ferns=Mesh('Garden_FeatherFerns')
for i in range(43):
    a=random.uniform(0,math.tau); rr=random.uniform(4.8,8.2); x,z=rr*math.cos(a),rr*math.sin(a)
    if not planting_allowed(x,z,.60): continue
    for frond in range(4):
        ang=frond*math.tau/4+random.uniform(-.30,.30); d=Vector((math.cos(ang),0,math.sin(ang))); side=Vector((-math.sin(ang),0,math.cos(ang)))
        length=random.uniform(.31,.55); base=Vector((x,ground_height(x,z)+.02,z)); prev=base
        for k in range(1,9):
            t=k/8; p=base+d*length*t+Vector((0,math.sin(t*math.pi*.89)*length*.66,0))
            ferns.cylinder(tup(prev),tup(p),.003,'stem',3)
            for ss in [-1,1]:
                ll=math.sin(t*math.pi)*length*.26+.012; end=p+side*ll*ss-d*.035
                middle=p.lerp(end,.48)
                ferns.face([tup(p),tup(middle-d*.023),tup(end+Vector((0,.010,0))),tup(middle+d*.018)],random.choice(['leaf','leaf_light','grass_sage']))
            prev=p
ferns.finish()

# Tall flowering spires add a second botanical rhythm amongst the low daisies.
spires=Mesh('Garden_LavenderAndSeedHeads')
for i in range(76):
    cx1,cz1,rad=clusters[i%len(clusters)]; x,z=cx1+random.uniform(-rad,rad),cz1+random.uniform(-rad,rad)
    if not planting_allowed(x,z): continue
    h=random.uniform(.32,.58)
    gy=ground_height(x,z)
    spires.cylinder((x,gy+.02,z),(x,gy+h,z),.006,'stem',4)
    for k in range(6):
        ang=k*2.4; yy=gy+h-.15+k*.025
        spires.ellipsoid((x+math.cos(ang)*.025,yy,z+math.sin(ang)*.025),(.025,.036,.025),'flower_lilac',5,3)
spires.finish()
for cx1,cz1 in [(-6.0,2.2),(4.3,4.4),(-3.0,-4.7),(6.8,-.6)]:
    for j in range(5):
        x,z=cx1+random.uniform(-.42,.42),cz1+random.uniform(-.42,.42); h=random.uniform(.10,.24); r=h*.60
        props.cylinder((x,.01,z),(x,h,z),r*.24,'paper',6)
        props.ellipsoid((x,h,z),(r,r*.50,r),'mushroom',9,4)
        for k in range(3):
            a=random.uniform(0,math.tau); rr=r*.50; props.ellipsoid((x+rr*math.cos(a),h+r*.35,z+rr*math.sin(a)),(.018,.008,.018),'mushroom_spot',5,3)
for i in range(52):
    a=random.uniform(0,math.tau); r=random.uniform(6.9,8.1); x,z=math.cos(a)*r,math.sin(a)*r
    props.ellipsoid((x,.05,z),(random.uniform(.08,.28),random.uniform(.06,.18),random.uniform(.09,.24)),random.choice(['stone','stone_dark','rock_blue']),7,3)
flora.finish(smooth=True); grass.finish(smooth=True); props.finish()

# Curated details: crates, stacked firewood, watering can, a tiny telescope, cliff pennants.
details=Mesh('Garden_StoryDetails')
# Climbing ivy follows the shady cottage corner and catches on the gable beam.
vine=Mesh('Cabin_ClimbingIvy')
last=None
for i in range(38):
    t=i/37; p=Vector((cx-1.34+.08*math.sin(t*18),.12+t*1.92,cz-1.27))
    if last: vine.cylinder(tup(last),tup(p),.012,'stem',5)
    if i%2==0:
        side=-1 if i%4==0 else 1; q=p+Vector((side*.15,.08,-.02))
        vine.face([tup(p),tup(q+Vector((-.06,.04,0))),tup(q+Vector((0,.13,-.01))),tup(q+Vector((.065,.04,0)))],random.choice(['leaf','leaf_light','leaf_gold']))
    last=p
vine.finish()
details.box((-5.88,.25,4.15),(.55,.48,.60),'wood',bevel=.03)
for yy in [.08,.42]: details.box((-5.88,yy,3.83),(.57,.06,.04),'wood_cut')
for i in range(7):
    xx=-5.97+(i%3)*.17; yy=.14+(i//3)*.14
    details.cylinder((xx,yy,4.65),(xx,yy,5.1),.085,'wood',8)
    details.cylinder((xx,yy,4.63),(xx,yy,4.65),.068,'wood_cut',8)
# Barrel of collected rain and curved metal handle.
details.cylinder((-2.3,.03,4.5),(-2.3,.53,4.5),.28,'wood_light',14,r2=.25)
for yy in [.12,.43]: details.torus((-2.3,yy,4.5),.275,.022,'metal_dark',n=20,m=5)
details.cylinder((-2.3,.53,4.5),(-2.3,.54,4.5),.23,'glass',20)
# Telescope points beyond the cliff near the blue cypress.
for dx,dz in [(-.32,-.25),(.32,-.25),(0,.35)]: details.cylinder((5.85,1.0,1.7),(5.85+dx,.03,1.7+dz),.025,'brass',6)
details.cylinder((5.5,1.17,1.55),(6.22,1.48,1.87),.105,'brass',12,r2=.14)
details.cylinder((6.22,1.48,1.87),(6.25,1.49,1.88),.12,'glass',16)
# Little directional sign at the path fork.
details.cylinder((2.4,0,-1.4),(2.4,.83,-1.4),.038,'wood',8)
details.box((2.4,.72,-1.4),(.65,.20,.07),'wood_cut',bevel=.05)
for i in range(4): details.ellipsoid((2.22+i*.11,.735,-1.445),(.020,.020,.005),'brass_light',5,3)
details.finish()

# Interchange hygiene: merged legacy flower poles contain 33 coincident duplicate
# triangles. Blender's GLB importer silently removes those. Remove duplicates and
# any zero-area triangles before export so all three formats agree.
degenerate_cleanup=[]
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    obj.data.calc_loop_triangles()
    bad=sum(t.area<1e-12 for t in obj.data.loop_triangles)
    duplicate_count=len(obj.data.loop_triangles)-len({tuple(sorted(t.vertices)) for t in obj.data.loop_triangles})
    if not bad and not duplicate_count:continue
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bm.verts.index_update();seen_faces=set();dead=[]
    for f in bm.faces:
        key=tuple(sorted(v.index for v in f.verts))
        if f.calc_area()<1e-12 or key in seen_faces:dead.append(f)
        seen_faces.add(key)
    bmesh.ops.delete(bm,geom=dead,context='FACES_ONLY')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    degenerate_cleanup.append({'mesh':obj.name,'removed_zero_area_triangles':bad,'removed_duplicate_triangles':duplicate_count})

# One portable COLOR_0/CORNER channel: all ordinary geometry stays white. Each
# connected blade receives a mild root-to-tip multiplier, without changing its
# material, silhouette, triangle count or the established placement RNG stream.
vertex_color_report=[]
colored_meshes={'Garden_GrassTufts','Garden_CreepingMeadowLeaves','Garden_FeatherFerns'}
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    mesh=obj.data;attr=mesh.color_attributes.new(name='BL_FoliageTint',type='FLOAT_COLOR',domain='CORNER')
    mesh.color_attributes.active_color=attr
    vertex_values=[1.0]*len(mesh.vertices)
    count=0
    if obj.name in colored_meshes:
        adj=[[] for _ in mesh.vertices]
        for e in mesh.edges:
            a,b=e.vertices;adj[a].append(b);adj[b].append(a)
        seen=set()
        for idx in range(len(mesh.vertices)):
            if idx in seen:continue
            pending=[idx];seen.add(idx);component=[]
            while pending:
                current=pending.pop();component.append(current)
                for linked in adj[current]:
                    if linked not in seen:seen.add(linked);pending.append(linked)
            low=min(mesh.vertices[v].co.z for v in component);high=max(mesh.vertices[v].co.z for v in component)
            variation=.975+.025*((math.sin(idx*12.9898+37.42)*43758.5453)%1)
            for v in component:
                t=max(0,min(1,(mesh.vertices[v].co.z-low)/max(.005,high-low)))
                vertex_values[v]=(.80+.20*(t*t*(3-2*t)))*variation
            count+=1
    packed=[]
    for loop in mesh.loops:
        value=vertex_values[loop.vertex_index]
        rgb=HERO_VERTEX_COLOURS[loop.vertex_index] if obj.name=='Garden_HeroBoulders' else (value,value,value)
        packed.extend((*rgb,1.0))
    attr.data.foreach_set('color',packed)
    rgb_values=[packed[i] for i in range(len(packed)) if i%4!=3]
    vertex_color_report.append({'mesh':obj.name,'attribute':'BL_FoliageTint','domain':'CORNER','color_space':'linear','min_rgb':min(rgb_values),'max_rgb':max(rgb_values),'connected_leaves':count,'purpose':'continuous mineral/crevice pigment' if obj.name=='Garden_HeroBoulders' else 'root-tip foliage multiplier' if obj.name in colored_meshes else 'white'})
for name,mat in MAT.items():
    if not (name.startswith('leaf') or name.startswith('rock_hero')):continue
    node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='BL_FoliageTint'
    mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1.0
    principled=mat.node_tree.nodes.get('Principled BSDF');mix.inputs[1].default_value=principled.inputs['Base Color'].default_value
    mat.node_tree.links.new(node.outputs['Color'],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],principled.inputs['Base Color'])

# Local plant cleanup after all generation and coloring: no random draws are
# skipped and surviving colors never get recalculated with shifted vertex IDs.
# The ray hits the actual boulder mesh, not a circular approximation. Removing
# the connected blade/flower component throughout its vertical footprint also
# removes detached lavender florets above a stem buried inside the rock.
hero_obj=bpy.data.objects['Garden_HeroBoulders']
hero_bvh=BVHTree.FromPolygons([v.co.copy() for v in hero_obj.data.vertices],
                             [tuple(p.vertices) for p in hero_obj.data.polygons],all_triangles=False)
plant_cleanup=[]
cleanup_meshes={'Garden_GrassTufts','Garden_CreepingMeadowLeaves','Garden_FeatherFerns',
                'Garden_LavenderAndSeedHeads','Garden_Wildflowers'}
def boulder_footprint_hit(co):
    ux,uz=co.x,-co.y
    if not any(r['bounds_min_unity'][0]-.007<=ux<=r['bounds_max_unity'][0]+.007 and
               r['bounds_min_unity'][2]-.007<=uz<=r['bounds_max_unity'][2]+.007 for r in HERO_BOULDERS):return False
    # Six millimetres covers tiny silhouette differences when nonplanar FBX
    # quads are triangulated differently by GLB/Unity. The actual mesh is still
    # the exclusion shape; this is not an approximate ellipsoid or large gap.
    for dx,dy in [(0,0),(.006,0),(-.006,0),(0,.006),(0,-.006),(.0042,.0042),(.0042,-.0042),(-.0042,.0042),(-.0042,-.0042)]:
        location,normal,index,distance=hero_bvh.ray_cast(Vector((co.x+dx,co.y+dy,1.5)),Vector((0,0,-1)),2.0)
        if location is not None:return True
    return False
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name in cleanup_meshes]:
    mesh=obj.data;before_tris=sum(len(p.vertices)-2 for p in mesh.polygons)
    adjacency=[[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices;adjacency[a].append(b);adjacency[b].append(a)
    seen=set();remove_ids=set();removed_components=0;component_bounds=[]
    for idx in range(len(mesh.vertices)):
        if idx in seen:continue
        stack=[idx];seen.add(idx);component=[]
        while stack:
            current=stack.pop();component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in seen:seen.add(neighbor);stack.append(neighbor)
        if not any(boulder_footprint_hit(mesh.vertices[v].co) for v in component):continue
        remove_ids.update(component);removed_components+=1
        component_bounds.append({'min_unity':[min(mesh.vertices[v].co.x for v in component),min(mesh.vertices[v].co.z for v in component),min(-mesh.vertices[v].co.y for v in component)],'max_unity':[max(mesh.vertices[v].co.x for v in component),max(mesh.vertices[v].co.z for v in component),max(-mesh.vertices[v].co.y for v in component)]})
    if remove_ids:
        bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.verts[i] for i in remove_ids],context='VERTS')
        bm.to_mesh(mesh);bm.free();mesh.update()
    after_tris=sum(len(p.vertices)-2 for p in mesh.polygons)
    plant_cleanup.append({'mesh':obj.name,'removed_components':removed_components,'removed_vertices':len(remove_ids),'removed_triangles':before_tris-after_tris,'remaining_triangles':after_tris,'removed_component_bounds_unity':component_bounds})
    assert not any(boulder_footprint_hit(v.co) for v in mesh.vertices),'Plant still projects into a new boulder'
    attr=mesh.color_attributes.active_color
    values=[float(c) for d in attr.data for c in d.color[:3]]
    entry=next(x for x in vertex_color_report if x['mesh']==obj.name)
    entry['min_rgb']=min(values);entry['max_rgb']=max(values)
    if entry['connected_leaves']:entry['connected_leaves']-=removed_components

# Export first: every model is named and material slots survive interchange.
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
for o in list(scene.objects): o.select_set(o.type in {'MESH','EMPTY'})
scene['asset_title']='Borrowed Light Island / 借光岛'
scene['authoring']='Original procedural Blender mesh; no third-party models.'
asset_objects=[o for o in scene.objects if o.type=='MESH']
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in asset_objects)
assert triangles<=450000, f'Budget exceeded: {triangles}'
inventory=[]
for o in asset_objects:
    inventory.append({'name':o.name,'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'materials':[m.name for m in o.data.materials]})
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'island.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,bake_space_transform=True,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False,add_leaf_bones=False,path_mode='COPY',embed_textures=True,colors_type='LINEAR')
bpy.ops.export_scene.gltf(filepath=str(OUT/'island.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_vertex_color='ACTIVE',export_all_vertex_colors=False)
report={'title':'借光岛 / Borrowed Light Island','units':'metres','unity_coordinates':'Y-up; Blender=(Unity.x,-Unity.z,Unity.y)','ground_y':0,'island_radius':9,'lamp_head_y':1.85,'anchors_unity':anchors,'triangles':triangles,'objects':inventory,'files':['island.blend','island.fbx','island.glb','blender-render.png'],'notes':['All models original, procedurally authored in Blender.','Lamp heads and light beams intentionally supplied by Unity.','Cabin_ReadingWindow_Glow is separately named for runtime material control.','FBX/GLB retain named component meshes and anchor empties.','Walkable paths designed near Y=0; top terrain only varies +/-4cm.']}
report['revision']='world-v6-candidate: weathered irregular boulders and curved narrow meadow blades'
report['notes'][-1]='Anchors, route corridors, buildings and interaction footprints remain Y=0; planted banks have smooth -3.5cm to +11.5cm humps.'
report['triangle_budget']=450000
report['design_changes']=['All 14 anchors, terrain, observatory, stepping-stone geometry and walkable surfaces remain identical to world-v5-r1. Ground textures are byte-identical.','Four boulders retain their centers and clear route corridors; uniform icosphere triangles support asymmetric broad fracture planes, rounded edges, restrained directional seams and multiscale erosion. New BI_rock_hero_warm/slate slots use continuous vertex pigment, not hard moss patches.','Short grass uses narrower curved five-triangle pointed blades, spatially varying heights and locally thinned colonies. Existing tall tufts become slender twisting ribbons; creeping leaves keep their low layer with rounded eight-triangle outlines.','BL_FoliageTint remains a linear color multiplier, with exact FBX LINEAR and normalized UINT16 GLB COLOR_0 export. Hero rock pigment requires root PaintedTinted shader keyword; original foliage keyword remains. No new textures.','All placement RNG is consumed as before. Boulders exclude intersecting plant components with actual BVH footprint plus 6mm edge allowance. Legacy duplicate flower-pole triangles are cleaned. Maximum total budget 450000 triangles.']
report['hero_boulders']=HERO_BOULDERS
report['vertex_colors']=vertex_color_report
report['degenerate_cleanup']=degenerate_cleanup
report['plant_cleanup']=plant_cleanup
report['ground_texture_statistics']=texture_stats
report['textures']={'base_color':'textures/meadow-watercolor.png','normal':'textures/meadow-normal.png','resolution':[2048,2048],'uv_contract':'u=(Unity.x+9)/18; v=(Unity.z+9)/18, unchanged'}
(OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('ASSET_EXPORT_READY',triangles,flush=True)
if args.skip_render:
    report['files']=['island.blend','island.fbx','island.glb']
    report['sha256']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in report['files']+['textures/meadow-watercolor.png','textures/meadow-normal.png']}
    report['preview_scope']='Interchange export only. Actual Unity runtime review is required after integration.'
    (OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BLENDER_WORLD_COMPLETE',triangles,flush=True)
    sys.exit(0)

# Dedicated studio presentation, excluded from exports. Gives immediate visual QA.
def point(name,pos,energy,color,size=2):
    d=bpy.data.lights.new(name,'AREA'); d.energy=energy; d.color=color; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=B(pos)
    o.rotation_euler=(Vector(B((0,0,0)))-o.location).to_track_quat('-Z','Y').to_euler(); return o
world=bpy.data.worlds.new('Twilight Studio') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world=world; world.use_nodes=True; world.node_tree.nodes['Background'].inputs['Color'].default_value=(.035,.065,.12,1); world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
point('Key_GoldenHour',(-8,15,-10),2100,(1,.80,.52),10)
point('Fill_Moon',(8,11,8),1700,(.39,.68,1),9)
point('Rim_Teal',(-8,4,9),1450,(.35,.83,.73),8)
point('Front_Soft',(6,7,-13),1000,(.72,.84,1),10)
for p in [(-4.1,1.5,2.45),(0,1.0,.35)]:
    d=bpy.data.lights.new('WarmDetail','POINT'); d.energy=30; d.color=(1,.55,.18); d.shadow_soft_size=1
    o=bpy.data.objects.new('WarmDetail',d); bpy.context.collection.objects.link(o); o.location=B(p)
camera_data=bpy.data.cameras.new('Camera_Presentation'); camera=bpy.data.objects.new('Camera_Presentation',camera_data); bpy.context.collection.objects.link(camera)
camera.location=B((18,16,-24)); target=Vector(B((0,-.4,.7))); camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO'; camera_data.ortho_scale=26.5; scene.camera=camera
scene.render.engine='CYCLES'; scene.cycles.samples=args.samples; scene.cycles.use_denoising=True
scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'; scene.view_settings.exposure=.7
scene.render.filepath=str(OUT/'blender-render.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'island.blend'))
bpy.ops.render.render(write_still=True)
camera_data.type='PERSP'; camera_data.lens=47
camera.location=B((1.7,1.55,-5.5)); target=Vector(B((.2,.22,-3.0)))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'blender-flora-closeup.png')
scene.render.resolution_x=1440; scene.render.resolution_y=1000
bpy.ops.render.render(write_still=True)
camera_data.lens=52
camera.location=B((-2.3,3.45,-.8)); target=Vector(B((-6.45,2.35,3.8)))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'blender-canopy-closeup.png')
scene.render.resolution_x=1200; scene.render.resolution_y=1100
bpy.ops.render.render(write_still=True)
report['files']=['island.blend','island.fbx','island.glb','blender-render.png','blender-flora-closeup.png','blender-canopy-closeup.png']
report['sha256']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in report['files']+['textures/meadow-watercolor.png','textures/meadow-normal.png']}
report['preview_scope']='Blender studio previews only; Unity runtime review must be performed after integration.'
(OUT/'asset-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLENDER_WORLD_COMPLETE',triangles,flush=True)
