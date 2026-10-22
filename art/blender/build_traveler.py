"""Original Borrowed Light traveler: Blender-authored, game-ready rigid animation.
Run using Blender 4.5 LTS --background --factory-startup --python-exit-code 1 --python.
Authoring axes X right, -Y forward, Z up. FBX export -Z forward / Y up.
"""
import bpy, math, json, random, hashlib
from pathlib import Path
from mathutils import Vector
from math import sin, cos, pi, tau

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art' / 'generated' / 'character-v4'
OUT.mkdir(parents=True, exist_ok=True)
random.seed(743)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in list(bpy.data.materials): bpy.data.materials.remove(block)

def mat(name, color, rough=.65, metal=0, emit=0, cloth=False):
    m=bpy.data.materials.new('Traveler_'+name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough
    p.inputs['Metallic'].default_value=metal
    if emit:
        p.inputs['Emission Color'].default_value=(*color,1); p.inputs['Emission Strength'].default_value=emit
    if cloth:
        p.inputs['Sheen Weight'].default_value=.22
        noise=m.node_tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=155
        noise.inputs['Detail'].default_value=2; noise.inputs['Roughness'].default_value=.72
        bump=m.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.13
        bump.inputs['Distance'].default_value=.004
        m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m

M={
 'cape':mat('Cape_TwilightTeal',(.055,.245,.294),.87,cloth=True),
 'capeEdge':mat('Cape_SeaMistBinding',(.115,.325,.34),.8,cloth=True),
 'lining':mat('Cape_DeepOceanLining',(.026,.102,.16),.9,cloth=True),
 'coat':mat('Coat_WashedBlue',(.08,.31,.34),.88,cloth=True),
 'hood':mat('Hood_DuskBlue',(.048,.16,.23),.9,cloth=True),
 'gold':mat('Scarf_HarvestGold',(.84,.47,.12),.86,cloth=True),
 'goldLight':mat('Scarf_EdgeHoney',(.97,.68,.24),.78,cloth=True),
 'hair':mat('Hair_Indigo',(.038,.030,.031),.72),
 'hairLight':mat('Hair_MidnightBlue',(.095,.064,.048),.74),
 'skin':mat('Face_PorcelainCream',(.86,.675,.515),.72),
 'skinLight':mat('Face_NoseCream',(.88,.695,.535),.7),
 'cheek':mat('Face_RoseCheeks',(.84,.61,.49),.75),
 'lip':mat('Face_SoftLips',(.55,.31,.235),.8),
 'nail':mat('Face_Fingernails',(.89,.735,.605),.68),
 'white':mat('Eye_Ivory',(.81,.795,.70),.36),
 'iris':mat('Eye_Chestnut',(.16,.078,.045),.3),
 'irisLight':mat('Eye_AmberRim',(.37,.21,.09),.36),
 'black':mat('Eye_Pupil',(.012,.018,.027),.23),
 'spark':mat('Eye_Catchlight',(1,.98,.87),.18,emit=.12),
 'trouser':mat('Trousers_Ink',(.035,.10,.14),.92,cloth=True),
 'boot':mat('Boots_WornChestnut',(.22,.105,.052),.73),
 'bootEdge':mat('Boots_HoneyLeather',(.37,.21,.105),.65),
 'sole':mat('Boots_DarkSole',(.075,.052,.04),.86),
 'brass':mat('Lantern_BrushedBrass',(.64,.37,.105),.36,.76),
 'brassLight':mat('Lantern_GoldEdges',(.88,.61,.23),.3,.72),
 'glass':mat('Lantern_AmberGlass',(.97,.58,.15),.28,.05,emit=.7),
 'flame':mat('Lantern_WarmHeart',(1,.77,.30),.32,0,emit=3.5),
 'seam':mat('Stitches_PaleFlax',(.60,.65,.51),.92),
 'glove':mat('Gloves_OatKnit',(.40,.415,.335),.93,cloth=True),
}
M['skin'].node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.055
CHAR=[]; BLINKS=[]

def parent_world(obj,parent):
    if parent:
        bpy.context.view_layer.update()
        w=obj.matrix_world.copy(); obj.parent=parent; obj.matrix_world=w
    return obj

def empty(name,loc,parent=None):
    o=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(o); o.location=loc
    o.empty_display_type='PLAIN_AXES'; o.empty_display_size=.06; parent_world(o,parent); CHAR.append(o)
    return o

def finish(o,name,material,parent=None,smooth=True):
    o.name=name
    if material: o.data.materials.append(M[material] if isinstance(material,str) else material)
    if o.type=='MESH' and smooth:
        for f in o.data.polygons: f.use_smooth=True
    parent_world(o,parent); CHAR.append(o); return o

def mesh(name,verts,faces,material,parent=None,smooth=True):
    me=bpy.data.meshes.new(name+'_mesh'); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    return finish(o,name,material,parent,smooth)

def ellipsoid(name,loc,scale,material,parent=None,seg=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=1,location=loc)
    o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,material,parent)

def tube(name,pts,radius,material,parent=None,sides=6,closed=False):
    pts=[Vector(x) for x in pts]; verts=[]; previous=None
    for i,p in enumerate(pts):
        tangent=(pts[(i+1)%len(pts)]-pts[(i-1)%len(pts)]) if closed else (pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)])
        tangent.normalize()
        if previous is None:
            ref=Vector((0,1,0))
            if abs(tangent.dot(ref))>.95: ref=Vector((1,0,0))
            a=tangent.cross(ref).normalized()
        else:
            a=(previous-tangent*previous.dot(tangent)).normalized()
        b=tangent.cross(a).normalized(); previous=a
        r=radius[i] if isinstance(radius,(list,tuple)) else radius
        verts += [tuple(p+r*(a*cos(j*tau/sides)+b*sin(j*tau/sides))) for j in range(sides)]
    faces=[]; count=len(pts) if closed else len(pts)-1
    for i in range(count):
        for j in range(sides): faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%len(pts))*sides+(j+1)%sides,((i+1)%len(pts))*sides+j))
    if not closed: faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(pts)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,material,parent)

def ringbody(name,levels,material,parent=None,n=24):
    verts=[]
    for z,rx,ry,cy in levels:
        for i in range(n):
            a=i*tau/n; v=1+.019*sin(a*5+z*19)+.009*sin(a*11-z*13)
            hem_wave=.0045*sin(a*5+.4)*math.exp(-((z-.445)/.055)**2)
            verts.append((rx*sin(a)*v,cy-ry*cos(a)*v,z+hem_wave))
    faces=[tuple(range(n-1,-1,-1)),tuple((len(levels)-1)*n+i for i in range(n))]
    for j in range(len(levels)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,verts,faces,material,parent)

def bevelbox(name,loc,scale,material,parent,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Soft hand finished edges','BEVEL'); mod.width=min(bevel,min(scale)*.42); mod.segments=3
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,material,parent)

root=empty('TravelerRoot',(0,0,0))
body=empty('Body',(0,0,.67),root)
head=empty('Head',(0,0,.945),root)
arms={}; legs={}
for side,x in [('L',-.19),('R',.19)]:
    arms[side]=empty('Arm_'+side,(x,0,.855),root)
for side,x in [('L',-.083),('R',.083)]:
    legs[side]=empty('Leg_'+side,(x,0,.505),root)
scarf=empty('ScarfTail',(.045,.075,.895),root)

# Tailored trousers and lasted leather boots: a flat sole and defined toe box.
def offset_loft(name,x,levels,material,parent,n=28,boxiness=1):
    verts=[]; faces=[]
    def shape(v): return math.copysign(abs(v)**boxiness,v)
    for z,rx,ry,cy in levels:
        for i in range(n):
            a=i*tau/n
            verts.append((x+rx*shape(sin(a)),cy-ry*shape(cos(a)),z))
    faces.extend([tuple(range(n-1,-1,-1)),tuple((len(levels)-1)*n+i for i in range(n))])
    for j in range(len(levels)-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return mesh(name,verts,faces,material,parent)

for side,s in [('L',-1),('R',1)]:
    p=legs[side]; x=s*.083
    offset_loft('Trouser_'+side,x,[(.203,.047,.048,.012),(.232,.056,.056,.014),(.266,.054,.059,.012),(.304,.057,.058,.009),(.345,.053,.06,.006),(.387,.057,.062,.007),(.454,.058,.063,.004),(.515,.048,.049,.003)],'trouser',p,24)
    for j,(z,w) in enumerate([(.245,.045),(.282,.045),(.348,.047)]):
        tube('TrouserFold_'+side+str(j),[(x-w,-.004,z+.008),(x-.008,-.048,z),(x+w,-.005,z+.004)],[.0005,.0022,.0005],'hood',p,5)
    offset_loft('BootUpper_'+side,x,[(.035,.06,.103,-.033),(.052,.064,.106,-.034),(.074,.063,.102,-.029),(.096,.056,.085,-.012),(.127,.052,.064,.005),(.174,.052,.057,.013),(.213,.056,.061,.013),(.228,.057,.061,.013)],'boot',p,28,.78)
    offset_loft('BootSole_'+side,x,[(.004,.059,.103,-.033),(.011,.064,.108,-.033),(.025,.065,.109,-.033),(.036,.061,.105,-.033)],'sole',p,28,.76)
    tube('BootCuff_'+side,[(x+.057*cos(i*tau/28),.013+.061*sin(i*tau/28),.224) for i in range(28)],.0043,'bootEdge',p,6,True)
    tube('BootWelt_'+side,[(x+.063*math.copysign(abs(cos(i*tau/32))**.78,cos(i*tau/32)),-.033+.106*math.copysign(abs(sin(i*tau/32))**.78,sin(i*tau/32)),.035) for i in range(32)],.0025,'bootEdge',p,5,True)
    for j in range(3):
        z=.135+j*.023
        tube('BootLace_'+side+str(j),[(x-.018,-.051,z),(x+.018,-.051,z+.009)],.0018,'bootEdge',p,5)
        tube('BootLaceCross_'+side+str(j),[(x+.018,-.052,z),(x-.018,-.052,z+.009)],.0016,'bootEdge',p,5)
        for ss in [-1,1]: ellipsoid('BootEyelet_'+side,(x+ss*.022,-.05,z+.005),(.0033,.0018,.0033),'brass',p,10,6)
    tube('BootToeSeam_'+side,[(x+.056*cos(i*pi/16),-.026-.091*sin(i*pi/16),.087-.01*sin(i*pi/16)) for i in range(17)],.0014,'bootEdge',p,5)
    for j in range(3):
        z=.108+j*.012
        tube('BootLeatherCrease_'+side+str(j),[(x-.033,-.059,z+.003),(x-.009,-.066,z),(x+.022,-.061,z+.002)],[.0003,.001,.0003],'bootEdge',p,5)

ringbody('TailoredTunic',[(.425,.155,.103,0),(.446,.163,.108,0),(.478,.16,.109,0),(.521,.151,.107,0),(.58,.142,.106,0),(.64,.137,.103,0),(.72,.14,.104,0),(.79,.153,.106,0),(.84,.169,.107,0),(.874,.164,.101,0),(.901,.137,.087,0),(.926,.092,.07,0),(.944,.065,.058,0)],'coat',body,40)
tube('CoatFrontSeam',[(.004,-.113,.45),(.004,-.115,.58),(.004,-.111,.72),(.004,-.104,.83)],.0035,'capeEdge',body,6)
for z in [.55,.635,.72,.805]: ellipsoid('TinyBrassButton',(.009,-.116,z),(.008,.0048,.008),'brassLight',body,12,8)
for side in [-1,1]:
    for j in range(20):
        z=.46+j*.018
        tube('Coat_HandStitch',[(side*.013,-.118,z),(side*.015,-.118,z+.006)],.0009,'capeEdge',body,4)
    for j in range(3):
        x=side*(.085+j*.023)
        tube('Coat_HemSoftFold',[(x,-.108,.462),(x+side*.004,-.111,.489),(x+side*.002,-.11,.522)], [.0003,.0021,.0003],'capeEdge',body,5)

# Tapered sleeves, separate relaxed fingers, thumb saddle and fingerless knit.
for side,s in [('L',-1),('R',1)]:
    p=arms[side]
    # Overlapping, rounded shoulder cap continues the collar line. Subtle
    # elbow bend and an oval taper replace the old rigid conical cylinder.
    pts=[(s*.112,.002,.908),(s*.145,.002,.894),(s*.18,.001,.873),(s*.202,-.001,.831),(s*.222,.002,.774),(s*.237,-.004,.719),(s*.248,-.018,.660),(s*.256,-.036,.610),(s*.262,-.048,.574)]
    tube('Sleeve_'+side,pts,[.043,.061,.060,.059,.055,.049,.045,.043,.040],'coat',p,24)
    end=Vector(pts[-1]); axis=(end-Vector(pts[-2])).normalized()
    ref=axis.cross(Vector((0,1,0))).normalized(); other=axis.cross(ref).normalized()
    tube('SleeveCuff_'+side,[tuple(end+(ref*cos(i*tau/20)+other*sin(i*tau/20))*.043) for i in range(20)],.007,'capeEdge',p,6,True)
    ellipsoid('Hand_'+side,(s*.266,-.055,.548),(.027,.021,.035),'skin',p,24,14)
    ellipsoid('ThumbSaddle_'+side,(s*.245,-.058,.546),(.013,.017,.022),'skin',p,18,10)
    thumb_tip=(s*.256,-.070,.525) if side=='R' else (s*.249,-.078,.522)
    tube('Thumb_'+side,[(s*.247,-.059,.552),(s*.238,-.068,.542),(s*.24,-.078,.528),thumb_tip],[.009,.0095,.0075,.0045],'skin',p,10)
    for i,(spread,length) in enumerate([(-.019,.032),(-.006,.042),(.007,.04),(.019,.031)]):
        x=s*(.266+spread); z=.531
        curl=.008+[.001,.004,.007,.010][i]
        points=[(x,-.057,z+.006),(x+s*.001,-.068,z-.006),(x+s*.0015,-.073,z-length*.65),(x+s*.0007,-.07+curl*.55,z-length+curl)]
        if side=='R':
            # The middle fingers turn back underneath the curved handle;
            # fingertips no longer hang straight beside it.
            points=[(x,-.057,z+.006),(x+s*.001,-.072,z-.008),(x+s*.0015,-.069,z-.024),(x+s*.0007,-.045,z-.010+(.002 if i in [1,2] else 0))]
        tube('Finger_'+side+'_'+str(i),points,[.0067,.0065,.0057,.0043],'skin',p,9)
        ellipsoid('FingerKnuckle_'+side+'_'+str(i),(x,-.071,z-.005),(.0065,.003,.0072),'skinLight',p,10,6)
        end=Vector(points[-1]); ellipsoid('Fingernail_'+side+'_'+str(i),(end.x,end.y-.0045,end.z+.005),(.0039,.001,.0054),'nail',p,10,6)
        tube('FingerCrease_'+side+'_'+str(i),[(x-.003,-.077,z-.012),(x+.003,-.077,z-.011)],.0006,'cheek',p,4)
    ellipsoid('KnitGlove_'+side,(s*.266,-.052,.561),(.0285,.023,.026),'glove',p,20,12)
    tube('KnitGlove_Cuff_'+side,[(s*.266+.029*cos(i*tau/24),-.052+.024*sin(i*tau/24),.577) for i in range(24)],.0028,'glove',p,5,True)
    for j in range(5):
        x=s*.266+(j-2)*.009
        tube('KnitGlove_Rib_'+side+str(j),[(x,-.072,.545),(x+.001,-.077,.554),(x-.001,-.075,.566),(x,-.07,.575)],.00065,'seam',p,4)
    for j in range(3):
        z=.541+j*.008
        tube('Sleeve_Fold_'+side+str(j),[(s*.244,-.064,z+.062),(s*.261,-.087,z+.057),(s*.281,-.067,z+.061)],[.0002,.0017,.0002],'capeEdge',p,5)

# Cloak: sculpted open-front bell with hand-designed layered folds and wavy hem.
cape_levels=[(.938,.071,.063),(.914,.138,.091),(.864,.174,.113),(.80,.179,.13),(.735,.173,.151),(.68,.171,.161),(.645,.169,.164)]
segments=42; begin=1.46; end=tau-1.46; verts=[]; faces=[]
for j,(z,rx,ry) in enumerate(cape_levels):
    for i in range(segments+1):
        a=begin+(end-begin)*i/segments; fold=(.005+.007*j/6)*sin(7*a+.2)
        verts.append(((rx+fold)*sin(a),-(ry+fold)*cos(a)+.028,z+.009*sin(5*a)*(j/6)**2))
for j in range(len(cape_levels)-1):
    for i in range(segments):
        a=j*(segments+1)+i; faces.append((a,a+1,a+1+segments+1,a+segments+1))
cape=mesh('Cloak_Outer',verts,faces,'cape',body)
solid=cape.modifiers.new('Wool cloth thickness','SOLIDIFY'); solid.thickness=.008; solid.offset=0
bpy.context.view_layer.objects.active=cape; bpy.ops.object.modifier_apply(modifier=solid.name)
hem=[verts[(len(cape_levels)-1)*(segments+1)+i] for i in range(segments+1)]
tube('Cloak_HemBinding',hem,.007,'capeEdge',body,6)
for edge in [0,segments]:
    tube('Cloak_FrontBinding_'+str(edge),[verts[j*(segments+1)+edge] for j in range(len(cape_levels))],.0075,'capeEdge',body,6)
for k in [5,11,18,25,32,38]:
    path=[]
    for j in range(2,len(cape_levels)):
        x,y,z=verts[j*(segments+1)+k]; path.append((x*1.018,y*1.018,z+.001))
    tube('Cloak_QuietFold_'+str(k),path,.0023,'lining',body,5)
for k in range(1,segments,2):
    a=Vector(hem[k]); b=Vector(hem[min(k+1,segments)])
    a.z+=.012; b.z+=.012
    mid=(a+b)/2
    tube('Cloak_HemStitch_'+str(k),[tuple(a*.32+mid*.68),tuple(b*.32+mid*.68)],.0012,'seam',body,4)
backseam=[]
for j,(z,rx,ry) in enumerate(cape_levels): backseam.append((.001,ry+.031,z))
tube('Cloak_BackTailorSeam',backseam,.0019,'capeEdge',body,5)
for j in range(18):
    t=j/17*5; k=min(4,int(t)); f=t-k
    a=Vector(backseam[k+1]); b=Vector(backseam[k+2]); p=a.lerp(b,f)
    tube('Cloak_BackHandStitch',[tuple(p+Vector((-.003,.002,-.002))),tuple(p+Vector((.003,.002,.002)))],.0008,'seam',body,4)

# The hood is down: a soft folded pouch on the upper back, leaving the
# jaw, ears and layered hair visible instead of a circular helmet silhouette.
hood_levels=[(.756,.012,.016,.172),(.773,.043,.023,.178),(.811,.076,.031,.163),(.853,.095,.034,.143),(.893,.105,.035,.114),(.921,.094,.034,.083),(.935,.070,.027,.063)]
ringbody('Hood_DrapedBackPouch',hood_levels,'hood',body,40)
hoodrim=[(-.075,.055,.932),(-.109,.095,.911),(-.105,.155,.865),(-.075,.190,.825),(0,.211,.797),(.075,.190,.825),(.105,.155,.865),(.109,.095,.911),(.075,.055,.932)]
tube('Hood_FoldedWoolRim',hoodrim,[.010,.013,.016,.015,.013,.015,.016,.013,.010],'capeEdge',body,10)
for s in [-1,1]:
    tube('Hood_DrapedFold_'+str(s),[(s*.066,.139,.904),(s*.052,.184,.862),(s*.018,.202,.807)],[.0003,.0035,.0004],'hood',body,7)
face_levels=[(.932,.012,.020,-.023),(.940,.038,.036,-.021),(.953,.061,.052,-.017),(.975,.083,.072,-.011),(1.006,.103,.089,-.006),(1.045,.119,.105,-.002),(1.081,.128,.111,.001),(1.119,.127,.103,.008),(1.154,.118,.092,.014),(1.189,.092,.072,.019),(1.216,.050,.041,.023),(1.224,.006,.006,.025)]
def face_section(z):
    k=next((i for i in range(len(face_levels)-1) if face_levels[i+1][0]>=z),len(face_levels)-2)
    k=max(0,k); t=max(0,min(1,(z-face_levels[k][0])/(face_levels[k+1][0]-face_levels[k][0])))
    rows=[face_levels[max(0,min(len(face_levels)-1,j))] for j in [k-1,k,k+1,k+2]]
    return [max(.002,.5*((2*rows[1][d])+(-rows[0][d]+rows[2][d])*t+(2*rows[0][d]-5*rows[1][d]+4*rows[2][d]-rows[3][d])*t*t+(-rows[0][d]+3*rows[1][d]-3*rows[2][d]+rows[3][d])*t*t*t)) if d<3 else .5*((2*rows[1][d])+(-rows[0][d]+rows[2][d])*t+(2*rows[0][d]-5*rows[1][d]+4*rows[2][d]-rows[3][d])*t*t+(-rows[0][d]+3*rows[1][d]-3*rows[2][d]+rows[3][d])*t*t*t) for d in [1,2,3]]
def sculpt_face_y(x,z,y,front):
    cheek=(math.exp(-((x-.078)/.034)**2)+math.exp(-((x+.078)/.034)**2))*math.exp(-((z-1.047)/.03)**2)
    socket=(math.exp(-((x-.048)/.029)**2)+math.exp(-((x+.048)/.029)**2))*math.exp(-((z-1.086)/.019)**2)
    # Nose, philtrum and lips are part of the head surface, so raking light
    # describes a single anatomical surface without an attached cone seam.
    bridge=.009*math.exp(-(x/.011)**2-((z-1.066)/.027)**2)
    tip=.020*math.exp(-(x/.014)**2-((z-1.045)/.012)**2)
    ala=.004*(math.exp(-((x-.013)/.008)**2)+math.exp(-((x+.013)/.008)**2))*math.exp(-((z-1.039)/.008)**2)
    lips=.0012*math.exp(-(x/.021)**4-((z-1.010)/.008)**2)
    philtrum=.0014*math.exp(-(x/.006)**2-((z-1.023)/.008)**2)
    return y+front*(-.0055*cheek+.004*socket-bridge-tip-ala-lips+philtrum-.0015*math.exp(-((z-.984)/.019)**2))
def face_front_y(x,z):
    rx,ry,cy=face_section(z); f=math.sqrt(max(0,1-(x/rx)**2))
    return sculpt_face_y(x,z,cy-ry*f,f**5)
fv=[]; ff=[]; face_n=112; face_rows=72
for j in range(face_rows):
    z=.932+(1.224-.932)*j/(face_rows-1); rx,ry,cy=face_section(z)
    for i in range(face_n):
        a=i*tau/face_n; x=rx*sin(a); y=cy-ry*cos(a)
        fv.append((x,sculpt_face_y(x,z,y,max(0,cos(a))**5),z))
ff.extend([tuple(range(face_n-1,-1,-1)),tuple((face_rows-1)*face_n+i for i in range(face_n))])
for j in range(face_rows-1):
    for i in range(face_n): ff.append((j*face_n+i,j*face_n+(i+1)%face_n,(j+1)*face_n+(i+1)%face_n,(j+1)*face_n+i))
mesh('Face_SculptedContours',fv,ff,'skin',head)
ellipsoid('Face_Neck',(0,.006,.938),(.046,.046,.055),'skin',head,24,14)
for s in [-1,1]:
    ellipsoid('Ear_'+str(s),(s*.125,.002,1.061),(.014,.015,.029),'skin',head,20,12)
    ellipsoid('EarInner_'+str(s),(s*.134,-.010,1.062),(.004,.004,.016),'cheek',head,14,8)
    ex=s*.048; ez=1.086; ey=face_front_y(ex,ez)
    def eye_layer(name,loc,scale,material,seg,rings):
        o=ellipsoid(name,loc,scale,material,head,seg,rings)
        bpy.context.view_layer.update(); inverse=o.matrix_world.inverted()
        for vertex in o.data.vertices:
            w=o.matrix_world@vertex.co
            w.y+=face_front_y(w.x,w.z)-ey
            vertex.co=inverse@w
        return o
    ev=[(ex,ey-.0030,ez)]; ef=[]; eye_n=32
    for r in [.25,.5,.75,1]:
        for i in range(eye_n):
            a=i*tau/eye_n; dx=.0235*r*cos(a); dz=(.0145 if sin(a)>0 else .0105)*r*sin(a)
            x=ex+dx; z=ez+dz
            ev.append((x,face_front_y(x,z)-.0008-.0022*(1-r*r),z))
    ef.extend((0,1+i,1+(i+1)%eye_n) for i in range(eye_n))
    for j in range(3):
        for i in range(eye_n): ef.append((1+j*eye_n+i,1+(j+1)*eye_n+i,1+(j+1)*eye_n+(i+1)%eye_n,1+j*eye_n+(i+1)%eye_n))
    mesh('EyeWhite_'+str(s),ev,ef,'white',head)
    eye_layer('EyeIris_'+str(s),(ex,ey-.0032,ez+.001),(.0108,.0010,.0115),'irisLight',24,12)
    eye_layer('EyeIrisDeep_'+str(s),(ex,ey-.0040,ez+.001),(.0087,.0006,.0102),'iris',20,10)
    eye_layer('EyePupil_'+str(s),(ex,ey-.0047,ez+.0015),(.0042,.0005,.0068),'black',16,10)
    eye_layer('EyeSparkle_'+str(s),(ex-.003,ey-.0055,ez+.005),(.0018,.0004,.002),'spark',12,8)
    upper=[]; lower=[]
    for i in range(17):
        a=i*pi/16; x=ex+.0235*cos(a); z=ez+.0145*sin(a)
        upper.append((x,face_front_y(x,z)-.0013,z))
        z=ez-.0105*sin(a); lower.append((x,face_front_y(x,z)-.001,z))
    tube('UpperLid_'+str(s),upper,[.00015]+[.0007]*15+[.00015],'hair',head,6)
    tube('LowerLid_'+str(s),lower,[.0001]+[.0005]*15+[.0001],'skinLight',head,5)
    brow=[]
    for dx,dz in [(-.028,0),(-.011,.006),(.01,.005),(.025,.001)]:
        x=ex+dx; z=1.119+dz; brow.append((x,face_front_y(x,z)-.003,z))
    tube('Brow_'+str(s),brow,[.0005,.0019,.002,.0004],'hair',head,6)
    # Scale pivot LOCAL X and Y: .001 is open, 1 is fully closed. Shrinking
    # both axes removes the thin resting strip of a one-axis-only eyelid.
    # The +90deg X bind rotation makes local Y the authored vertical axis.
    blink=empty('Blink_'+('L' if s<0 else 'R'),(ex,ey-.008,ez+.023),head)
    blink.rotation_euler.x=pi/2
    # A thin domed cover blends into the face at its perimeter. It avoids
    # the floating-disc silhouette of a full sphere placed over the eye.
    lid_front=ey-.0069
    lv=[(ex,lid_front,ez)]; lf=[]; lid_n=32
    def lid_depth(x,z,r):
        return face_front_y(x,z)-.0001-.0068*max(0,1-r*r)**1.8
    for r in [.2,.4,.6,.8,.92,1]:
        for i in range(lid_n):
            a=i*tau/lid_n; x=ex+.034*r*cos(a); z=ez+.023*r*sin(a)
            lv.append((x,lid_depth(x,z,r),z))
    lf.extend((0,1+i,1+(i+1)%lid_n) for i in range(lid_n))
    for j in range(5):
        for i in range(lid_n): lf.append((1+j*lid_n+i,1+(j+1)*lid_n+i,1+(j+1)*lid_n+(i+1)%lid_n,1+j*lid_n+(i+1)%lid_n))
    mesh(blink.name+'_LidCover',lv,lf,'skin',blink)
    lash=[]
    for dx,dz in [(-.023,-.001),(-.011,-.004),(0,-.005),(.011,-.004),(.023,-.001)]:
        x=ex+dx; z=ez+dz; r=math.sqrt((dx/.034)**2+(dz/.023)**2)
        lash.append((x,lid_depth(x,z,r)-.0015,z))
    tube(blink.name+'_ClosedLash',lash,[.0002,.00075,.00085,.00075,.0002],'hair',blink,6)
    BLINKS.append(blink)
for s in [-1,1]:
    nostril=[]
    for x,z in [(s*.008,1.035),(s*.012,1.0345),(s*.015,1.036)]: nostril.append((x,face_front_y(x,z)-.0006,z))
    tube('Nostril_'+str(s),nostril,[.0002,.0008,.0002],'cheek',head,5)
mouth=[]
for x,z in [(-.019,1.015),(-.010,1.012),(0,1.0115),(.010,1.0125),(.019,1.016)]: mouth.append((x,face_front_y(x,z)-.0006,z))
tube('QuietSmile',mouth,[.0002,.0006,.0007,.0006,.0002],'lip',head,6)
lower_lip=[(x,face_front_y(x,z)-.0003,z) for x,z in [(-.012,1.008),(0,1.007),(.012,1.008)]]
tube('LowerLip',lower_lip,[.0001,.00045,.0001],'cheek',head,5)

# An asymmetric layered crown and swept, curved locks inside the open hood.
hv=[]; hf=[]; hn=40; hr=16
for j in range(hr):
    t=j/(hr-1)
    for i in range(hn):
        phi=i*tau/hn; front=max(0,-sin(phi)); limit=1.62-.68*front**1.5
        theta=.012+(limit-.012)*t
        wave=1+.025*sin(7*phi+theta*2)+.016*sin(13*phi-theta)
        hv.append((.128*sin(theta)*cos(phi)*wave,.011+.116*sin(theta)*sin(phi)*wave,1.11+.132*cos(theta)))
for j in range(hr-1):
    for i in range(hn): hf.append((j*hn+i,(j+1)*hn+i,(j+1)*hn+(i+1)%hn,j*hn+(i+1)%hn))
mesh('Hair_OrganicCrown',hv,hf,'hair',head)

def hairlock(name,points,widths,depth=.46):
    verts=[]; faces=[]; sides=10
    for i,p in enumerate(points):
        p=Vector(p); t=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        t.normalize(); a=t.cross(Vector((0,-1,0)))
        if a.length<.00001: a=t.cross(Vector((1,0,0)))
        a.normalize(); b=t.cross(a).normalized()
        for k in range(sides): verts.append(tuple(p+a*cos(k*tau/sides)*widths[i]+b*sin(k*tau/sides)*widths[i]*depth))
    for i in range(len(points)-1):
        for k in range(sides): faces.append((i*sides+k,i*sides+(k+1)%sides,(i+1)*sides+(k+1)%sides,(i+1)*sides+k))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+i for i in range(sides))])
    mesh(name,verts,faces,'hair',head)
    tube(name+'_Strand',[(p[0],p[1]-.005,p[2]+.002) for p in points[2:-2]],.0008,'hairLight',head,4)

def bezier_points(a,b,c,d,count=13):
    a,b,c,d=map(Vector,(a,b,c,d)); result=[]
    for i in range(count):
        t=i/(count-1); result.append(tuple((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d))
    return result

for i,(endx,endz) in enumerate([(-.139,1.16),(-.112,1.146),(-.083,1.148),(-.052,1.153),(-.018,1.164),(.020,1.174),(.057,1.167),(.097,1.141)]):
    sx=-.01+i*.009; endy=face_front_y(endx,endz)-.012
    points=bezier_points((sx,.022,1.231),(sx+.014,-.029,1.283-i*.002),(endx+.046,endy-.026,1.218),(endx,endy,endz),15)
    widths=[.0006+(.026 if i<5 else .022)*(1+.18*sin(i*2.14))*max(0,sin(pi*j/(len(points)-1)))**.65*(1-.2*j/(len(points)-1)) for j in range(len(points))]
    hairlock('Hair_SweptLock_'+str(i),points,widths)
for side,s in [('L',-1),('R',1)]:
    for j in range(3):
        points=bezier_points((s*(.087+j*.005),.014+j*.012,1.205),(s*.125,-.009+j*.012,1.178),(s*(.132-j*.003),-.021+j*.008,1.122),(s*(.115+j*.006),-.026+j*.011,1.055+j*.013),13)
        widths=[.0006+(.016+.002*j)*sin(pi*k/12)**.7 for k in range(13)]
        hairlock('Hair_Temple_'+side+str(j),points,widths,.30)
for i in range(3):
    tube('Hair_CrownFlyaway_'+str(i),[(.018+i*.012,-.03,1.235),(.028+i*.014,-.038,1.252-i*.002),(.048+i*.014,-.05,1.246-i*.003)],[.0017,.0012,.0002],'hair',head,5)

# Layered side and rear locks continue the swept crown. Each follows the
# scalp then leaves it only at the thin tip, avoiding a smooth hair-cap dome.
for i in range(13):
    phi=.05+(pi-.10)*i/12+.035*sin(i*2.31)
    points=[]
    for j in range(13):
        t=j/12; theta=.35+(.98+.30*(.5+.5*sin(i*2.7)))*t
        a=phi-.42*(1-t)+.11*sin(pi*t+i*.7)
        rr=1.018+.018*sin(pi*t)
        points.append((.130*sin(theta)*cos(a)*rr,.011+.118*sin(theta)*sin(a)*rr,1.11+.134*cos(theta)+.003*sin(pi*t)))
    widths=[.0006+(.025+.006*sin(i*1.8))*sin(pi*j/12)**.65 for j in range(13)]
    hairlock('Hair_BackLayer_'+str(i),points,widths,.24)

# The scarf is a complete collar plus an independently animated, flowing ribbon.
tube('Scarf_Collar',[(.091*cos(i*tau/40),.078*sin(i*tau/40)-.005,.912+.005*cos(i*tau/40)) for i in range(40)],.024,'gold',body,12,True)
tube('Scarf_CollarUpperStitch',[(.096*cos(i*tau/40),.083*sin(i*tau/40)-.005,.927+.005*cos(i*tau/40)) for i in range(40)],.0018,'goldLight',body,5,True)
ellipsoid('Scarf_Knot',(-.031,-.099,.905),(.028,.020,.025),'goldLight',body,20,12)
scarf_centers=[(.045,.078,.895),(.10,.12,.90),(.18,.17,.92),(.27,.21,.96),(.36,.22,.98),(.44,.24,.95),(.50,.25,.91)]
widths=[.037,.044,.047,.045,.043,.04,.037]; verts=[]; faces=[]
for i,(p,w) in enumerate(zip(scarf_centers,widths)):
    x,y,z=p
    for j in range(4):
        t=j/3; verts.append((x+.006*sin(t*pi),y+(t-.5)*w*.35,z+(t-.5)*w*2+.004*sin(t*pi+i)))
for i in range(len(scarf_centers)-1):
    for j in range(3):
        a=i*4+j; faces.append((a,a+4,a+5,a+1))
ribbon=mesh('Scarf_WindRibbon',verts,faces,'gold',scarf)
mod=ribbon.modifiers.new('Scarf thickness','SOLIDIFY'); mod.thickness=.006
bpy.context.view_layer.objects.active=ribbon; bpy.ops.object.modifier_apply(modifier=mod.name)
for k in [0,3]: tube('Scarf_Edge_'+str(k),[verts[i*4+k] for i in range(len(scarf_centers))],.0023,'goldLight',scarf,5)
for i in range(5):
    y=.243+i*.004; z=.88+i*.014
    tube('Scarf_EndFringe_'+str(i),[(.50,y,z),(.525,y+.01,z-.002)],.0025,'goldLight',scarf,5)
# Geometric running yarn strands remain visible after FBX export without a bake.
for r in [.18,.36,.64,.82]:
    yarn=[]
    for i,((x,y,z),w) in enumerate(zip(scarf_centers,widths)):
        yarn.append((x+.006*sin(r*pi),y+(r-.5)*w*.35-.004,z+(r-.5)*w*2+.004*sin(r*pi+i)))
    tube('Scarf_WovenWarp',yarn,.00085,'goldLight',scarf,4)
for i in range(1,6):
    x,y,z=scarf_centers[i]; w=widths[i]
    tube('Scarf_WovenWeft',[(x-.002,y-.005-w*.1,z-w*.55),(x+.002,y-.005+w*.1,z+w*.55)],.0007,'goldLight',scarf,4)
for i in range(8):
    z=.88+i*.009
    tube('Scarf_FineFringe',[(.506,.249+i*.0015,z),(.533+.002*sin(i),.258+i*.0015,z-.001)],.0011,'gold',scarf,4)

# Small brass star clasp: cut metal, rather than a printed emblem.
starverts=[]; starfaces=[]
for y in [-.12,-.133]:
    for i in range(10):
        a=pi/2+i*pi/5; r=.027 if i%2==0 else .0125
        starverts.append((.065+r*cos(a),y,.889+r*sin(a)))
starfaces.extend([tuple(range(9,-1,-1)),tuple(range(10,20))])
starfaces.extend((i,(i+1)%10,(i+1)%10+10,i+10) for i in range(10))
mesh('Star_ChestBrooch',starverts,starfaces,'brassLight',body,False)
ellipsoid('Brooch_AmberStone',(.065,-.137,.889),(.0055,.003,.006),'glass',body,12,8)

# A worn side satchel with rounded flap and sewn edging.
bag=bevelbox('Satchel_Body',(-.18,.048,.62),(.12,.075,.14),'boot',body,.023)
bevelbox('Satchel_Flap',(-.18,-.001,.665),(.127,.018,.068),'bootEdge',body,.015)
tube('Satchel_Strap',[(-.124,-.077,.876),(-.12,-.112,.78),(-.16,-.11,.68),(-.192,-.025,.65)],.009,'bootEdge',body,6)
bevelbox('Satchel_Clasp',(-.18,-.016,.641),(.018,.009,.024),'brass',body,.003)

# Lantern cage: bell-shaped six-sided brass roof, opal heart and tiny rivets.
lantern=empty('Lantern',(.276,-.066,.52),arms['R'])
lc=Vector((.277,-.067,.398)); radius=.047
for z,r in [(.332,.043),(.34,.051),(.452,.05),(.462,.04)]:
    tube('Lantern_CageRing_'+str(z),[(lc.x+r*cos(i*tau/24),lc.y+r*sin(i*tau/24),z) for i in range(24)],.0042,'brassLight',lantern,6,True)
for i in range(6):
    a=tau*i/6
    tube('Lantern_Rib_'+str(i),[(lc.x+.041*cos(a),lc.y+.041*sin(a),.335),(lc.x+.052*cos(a),lc.y+.052*sin(a),.389),(lc.x+.046*cos(a),lc.y+.046*sin(a),.455)],.0032,'brass',lantern,6)
    ellipsoid('Lantern_Rivet_'+str(i),(lc.x+.048*cos(a),lc.y+.048*sin(a),.453),(.004,.004,.004),'brassLight',lantern,8,6)
ellipsoid('Lantern_OpalGlass',tuple(lc),(.033,.033,.055),'glass',lantern,18,12)
ellipsoid('Lantern_Heart',(lc.x,lc.y,.4),(.019,.019,.04),'flame',lantern,16,10)
for z,r in [(.323,.028),(.47,.032)]:
    bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=r,radius2=r*.65,depth=.014,location=(lc.x,lc.y,z))
    finish(bpy.context.object,'Lantern_Cap_'+str(z),'brass',lantern)
tube('Lantern_Handle',[(lc.x+.033*cos(i*pi/16),lc.y,.481+.045*sin(i*pi/16)) for i in range(17)],.0039,'brassLight',lantern,6)

# Refine cloth curvature before proportioning. The animation still uses rigid
# named groups, but shoulders no longer end in flat cylinder caps.
for o in [o for o in CHAR if o.type=='MESH' and (o.name.startswith('Sleeve_') or o.name=='TailoredTunic')]:
    bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Soft tailored cloth contour','SUBSURF'); mod.levels=1
    bpy.ops.object.modifier_apply(modifier=mod.name)

# A longer-legged, narrower silhouette with a proportionate uncovered head.
# Transform authored vertices and every pivot together in world coordinates,
# then retain each mesh's original local basis for runtime rigid animation.
bpy.context.view_layer.update()
z_map=[(0,0),(.228,.180),(.425,.560),(.515,.640),(.670,.765),(.945,1.010),(1.40,1.4195)]
def proportion(v):
    k=next((i for i in range(len(z_map)-1) if v.z<=z_map[i+1][0]),len(z_map)-2)
    a,b=z_map[k],z_map[k+1]; z=a[1]+(v.z-a[0])*(b[1]-a[1])/(b[0]-a[0])
    # Keep the head broad enough for a readable expressive childlike face;
    # torso is tailored, while boots retain a substantial leather toe.
    def blend(z,a,b):
        t=max(0,min(1,(z-a)/(b-a))); return t*t*(3-2*t)
    xs=.91-.04*blend(v.z,.21,.28)+.05*blend(v.z,.90,.98)
    ys=1-.10*blend(v.z,.36,.45)+.04*blend(v.z,.90,.98)
    return Vector((v.x*xs,v.y*ys,z))
old_world={o:o.matrix_world.copy() for o in CHAR}
world_vertices={o:[o.matrix_world@v.co for v in o.data.vertices] for o in CHAR if o.type=='MESH'}
for o in CHAR:
    world=old_world[o].copy(); world.translation=proportion(world.translation); o.matrix_world=world
    bpy.context.view_layer.update()
for o,coords in world_vertices.items():
    inverse=o.matrix_world.inverted()
    is_lantern=o.parent==lantern
    for vertex,coord in zip(o.data.vertices,coords):
        deformed=proportion(old_world[lantern].translation)+(coord-old_world[lantern].translation)*.90 if is_lantern else proportion(coord)
        vertex.co=inverse@deformed
    o.data.update()

# Save exportable asset before adding a neutral presentation stage.
bpy.context.view_layer.update()
protected_prefixes=('Face','Eye','Nose','Ear','Brow','UpperLid','LowerLid','Blink','Hand','Finger','Thumb','Hair')
def tri_count(o):
    if o.type!='MESH': return 0
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)
eligible=[o for o in CHAR if o.type=='MESH' and len(o.data.polygons)>80 and not o.name.startswith(protected_prefixes)]
total_before=sum(tri_count(o) for o in CHAR); reducible=sum(tri_count(o) for o in eligible)
if total_before>54000 and reducible:
    ratio=max(.30,min(.98,(54000-(total_before-reducible))/reducible))
    print('TRAVELER_BUDGET '+json.dumps({'before':total_before,'fixed':total_before-reducible,'reducible':reducible,'ratio':ratio}),flush=True)
    for o in eligible:
        bpy.context.view_layer.objects.active=o
        mod=o.modifiers.new('Preserve face and hand detail budget','DECIMATE'); mod.ratio=ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
# Combine disconnected rigid details sharing a material under each pivot. The
# expressive pivot hierarchy is retained while runtime renderer count is reduced.
groups={}
for o in CHAR:
    if o.type=='MESH' and o.name!='Lantern_Heart':
        key=(o.parent.name,o.data.materials[0].name)
        groups.setdefault(key,[]).append(o)
for (part,material),members in groups.items():
    if len(members)<2: continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in members: o.select_set(True)
    bpy.context.view_layer.objects.active=members[0]
    bpy.ops.object.join()
    members[0].name=part+'_'+material.replace('Traveler_','')
CHAR=[root]+list(root.children_recursive)
for o in CHAR:
    if o.type=='MESH':
        bpy.context.view_layer.objects.active=o; o.select_set(True)
        if not o.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')
        o.select_set(False)
for blink in BLINKS: blink.scale=(.001,.001,1)
bpy.context.view_layer.update()

bpy.ops.object.select_all(action='DESELECT')
for o in CHAR: o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.fbx(filepath=str(OUT/'traveler.fbx'),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',use_space_transform=True,bake_space_transform=False,mesh_smooth_type='FACE',use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'traveler.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_materials='EXPORT',export_extras=True)

triangles=0
for o in CHAR:
    if o.type=='MESH':
        o.data.calc_loop_triangles(); triangles+=len(o.data.loop_triangles)
hierarchy=[]
for o in CHAR:
    hierarchy.append({'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'blender_local_position':list(o.location),'blender_local_rotation_euler':list(o.rotation_euler),'blender_local_scale':list(o.scale),'mesh_triangles':sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else 0})
manifest={
 'asset':'Borrowed Light Island / Original traveler','version':4,'original':True,
 'files':{'blend':'traveler.blend','fbx':'traveler.fbx','glb':'traveler.glb','preview':'render.png','portrait':'render-portrait.png','side':'render-side.png','closed_eyes_preview':'render-blink.png'},
 'blender_axes':{'up':'+Z','forward':'-Y','ground':'Z=0','units':'meters'},
 'unity_import':{'up':'+Y','forward':'+Z','ground':'Y=0','scale':1,'fbx_axis_forward':'-Z','fbx_axis_up':'Y','import_bake_axis_conversion':True,'note':'FBX root may carry Blender axis conversion; preserve it. Animate named descendant pivots in their imported bind pose, local X is lateral hinge.'},
 'dimensions_m':{'target_height':1.30,'actual_height':max((o.matrix_world@Vector(c)).z for o in CHAR if o.type=='MESH' for c in o.bound_box),'foot_base':0.0032},
 'statistics':{'triangles':triangles,'polygons':sum(len(o.data.polygons) for o in CHAR if o.type=='MESH'),'vertices':sum(len(o.data.vertices) for o in CHAR if o.type=='MESH'),'objects':len(CHAR),'materials':len(M)},
 'animation':{'rig':'separate rigid groups, no skinning or external plugins required','pivots':{'TravelerRoot':'world origin; translate/rotate whole model','Body':'torso; subtle local Z breathing in Blender / local Y Unity','Head':'neck 0,0,1.010 Blender; idle look ±6° yaw','Arm_L':'left shoulder; hinge local X','Arm_R':'right shoulder; hinge local X; lantern child follows','Leg_L':'left hip; hinge local X','Leg_R':'right hip; hinge local X','ScarfTail':'neck rear; local X/Z small flutter','Lantern':'right hand hanging handle; child of Arm_R'},'suggested_unity_drive':'Store initial local rotations; bind * Quaternion.Euler(sin(t)*angle,0,0). Legs ±18 degrees opposed; arms opposed ±8 (right ±5); root y bob .008m; scarf ±4 X, ±7 Z. Lantern local X ±3 counter-swing.','contact_note':'Preserve root scale; only Blink_L/R use their documented local scale animation. Boots bottom is approximately Unity Y 0.0032. Model height approximately 1.30; runtime capsule may use height 1.30 radius .18 center y .65.'},
 'material_notes':'Principled diffuse/metallic/emission export to GLB. Procedural cloth bump and sheen are Blender preview enhancements; recreate with a fine URP normal or supplied colors. Lantern flame is emissive; runtime optional small warm point light.' ,
 'blink_contract':{'pivots':['Blink_L','Blink_R'],'parent':'Head','bind_rotation_note':'Keep imported bind rotation. Source local rotation X=+90 degrees makes pivot local Y its height expansion axis and X its width.','open_local_scale':[.001,.001,1],'closed_local_scale':[1,1,1],'drive':'float s = Mathf.Lerp(.001f,1f,closeAmount); localScale = new Vector3(s,s,1). closeAmount 0=open,1=closed; do not multiply .001 bind.y by closeAmount.','suggested_timing':'Close 0.06s, hold 0.025s, reopen 0.09s; intervals 3.2 to 5.5s with subtle independent offset. Optional disable blink children while fully open.','geometry':'Separate thin domed cream eyelid cover, face-blended perimeter and closed lash under each pivot; no skinning, no material transparency required.'},
 'geometry_details':['Integrated continuous nose, lips, eye sockets, cheek and chin shaping on a dense head surface','Surface-following almond eyes with reduced protrusion and shallow blink covers','Uncovered asymmetric swept hair crown with layered side/rear locks and temple wisps','Longer visible trouser legs, shorter boots and a narrower tailored coat','Rounded shoulder caps and subtly curved subdivided sleeves','Separate relaxed fingers, thumb saddle and small fingernails','Lasted leather boots with flat welt/sole, crossed laces and fine creases','Short open-back shoulder cape rather than a bell around the whole torso','Soft hood folded onto shoulder/back, leaving the complete head silhouette visible','Fingerless oat-knit gloves with geometric ribs','Scarf woven warp/weft strands and fine fringe'],
 'hierarchy':hierarchy,
}
(OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')

# Presentation: gentle warm key and cool rim, followed by a detailed portrait.
bpy.ops.object.select_all(action='DESELECT')
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=12
scene.cycles.use_denoising=True
scene.world.color=(.08,.08,.08)
world=scene.world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.035,.063,.10,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
stage=mat('PresentationFloor',(.025,.057,.08),.92)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001))
floor=bpy.context.object; floor.name='PREVIEW_Stage'; floor.data.materials.append(stage)
def area(name,loc,power,color,size):
    bpy.ops.object.light_add(type='AREA',location=loc); o=bpy.context.object; o.name=name
    o.data.energy=power; o.data.color=color; o.data.shape='DISK'; o.data.size=size
    o.rotation_euler=(Vector((0,0,.65))-o.location).to_track_quat('-Z','Y').to_euler()
area('PREVIEW_WarmKey',(-2,-3,4),270,(1,.79,.55),3)
area('PREVIEW_SoftFill',(2,-1,2.2),120,(.53,.76,1),2.5)
area('PREVIEW_Rim',(.4,2.8,3),330,(.44,.78,.91),2.4)
bpy.ops.object.light_add(type='POINT',location=(lc.x,lc.y-.03,.4)); light=bpy.context.object
light.name='PREVIEW_LanternLight'; light.data.energy=2.2; light.data.color=(1,.57,.20); light.data.shadow_soft_size=.10
bpy.ops.object.camera_add(location=(1.45,-4.5,1.50)); camera=bpy.context.object; camera.name='PREVIEW_Camera'
target=Vector((-.035,0,.66)); camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'; camera.data.ortho_scale=1.7; scene.camera=camera
scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(OUT/'render.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'traveler.blend'))
bpy.ops.render.render(write_still=True)
camera.location=(1.25,-3.8,1.43); target=Vector((.005,-.02,1.13))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.ortho_scale=.64
scene.cycles.samples=16; scene.render.filepath=str(OUT/'render-portrait.png')
bpy.ops.render.render(write_still=True)
camera.location=(4.5,-.55,1.5); target=Vector((0,0,.66))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.ortho_scale=1.7
scene.render.filepath=str(OUT/'render-side.png')
bpy.ops.render.render(write_still=True)
for blink in BLINKS: blink.scale=(1,1,1)
camera.location=(1.25,-3.8,1.43); target=Vector((.005,-.02,1.13))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler(); camera.data.ortho_scale=.66
scene.render.filepath=str(OUT/'render-blink.png')
bpy.ops.render.render(write_still=True)
for blink in BLINKS: blink.scale=(.001,.001,1)
print('TRAVELER_RENDERS_COMPLETE '+json.dumps({'triangles':triangles,'objects':len(CHAR),'out':str(OUT)},ensure_ascii=False),flush=True)

# Real interchange round-trip: preserve every rigid-animation pivot and blink.
expected={o.name:tuple(o.matrix_world.translation) for o in CHAR if o.type=='EMPTY'}
parents={o.name:o.parent.name if o.parent else None for o in CHAR if o.type=='EMPTY'}
verification={}
for suffix in ['fbx','glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'))
    else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    bpy.context.view_layer.update(); errors=[]; checked_pivots={}
    for name,position in expected.items():
        obj=bpy.data.objects.get(name)
        if obj is None: errors.append('missing pivot '+name); continue
        checked_pivots[name]=list(obj.matrix_world.translation)
        if (obj.matrix_world.translation-Vector(position)).length>.00015: errors.append('pivot moved '+name)
        if (obj.parent.name if obj.parent else None)!=parents[name]: errors.append('pivot parent changed '+name)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    bounds=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
    lo=[min(v[i] for v in bounds) for i in range(3)]; hi=[max(v[i] for v in bounds) for i in range(3)]
    if not .001<=lo[2]<=.009: errors.append('incorrect foot contact')
    if not 1.25<hi[2]<1.35: errors.append('height differs from 1.25–1.35 m contract')
    tris=sum(tri_count(o) for o in meshes)
    if tris>55000: errors.append('triangle budget above 55000')
    blink_check={}
    for name in ['Blink_L','Blink_R']:
        pivot=bpy.data.objects.get(name)
        if pivot is None: errors.append('missing blink '+name); continue
        if any(abs(pivot.scale[i]-.001)>.00002 for i in [0,1]): errors.append('incorrect open blink '+name)
        lids=[o for o in pivot.children_recursive if o.type=='MESH']
        open_pts=[o.matrix_world@Vector(c) for o in lids for c in o.bound_box]
        open_extent=[max(p[i] for p in open_pts)-min(p[i] for p in open_pts) for i in [0,2]]
        pivot.scale=(1,1,1); bpy.context.view_layer.update()
        close_pts=[o.matrix_world@Vector(c) for o in lids for c in o.bound_box]
        closed_height=max(p.z for p in close_pts)-min(p.z for p in close_pts)
        if max(open_extent)>.0002 or not .040<closed_height<.043: errors.append('blink geometry contract failed '+name)
        blink_check[name]={'open_width_m':open_extent[0],'open_height_m':open_extent[1],'closed_height_m':closed_height,'closed_local_scale':[1,1,1]}
        pivot.scale=(.001,.001,1); bpy.context.view_layer.update()
    verification[suffix]={'passed':not errors,'errors':errors,'triangles':tris,'mesh_renderers':len(meshes),'bounds_blender':{'min':lo,'max':hi},'pivots_blender_world':checked_pivots,'blink_validation':blink_check}
manifest['sha256']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['traveler.fbx','traveler.glb','traveler.blend','render.png','render-portrait.png','render-side.png','render-blink.png']}
manifest['source_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
manifest['roundtrip_verification']=verification
(OUT/'traveler-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
(OUT/'export-verification.json').write_text(json.dumps(verification,indent=2,ensure_ascii=False),encoding='utf-8')
print('TRAVELER_COMPLETE '+json.dumps({'triangles':triangles,'objects':len(CHAR),'out':str(OUT),'verification':verification},ensure_ascii=False),flush=True)
assert all(v['passed'] for v in verification.values()),'Export round-trip verification failed'
