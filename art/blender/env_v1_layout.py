"""Offline spatial contract for the new island. No Unity or old game dependency."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/generated/env-v1"
OUT.mkdir(parents=True, exist_ok=True)
CAPE = (7.0, 2.4, -21.0)
# Houses are kept clear of the sloping shoreline and form two small streets.
HOUSE_SITES=[(-17.5,3.6,90,.8),(-17.8,6.7,90,.8),(-17.8,9.9,90,.8),
             (-17.8,13.1,90,.8),(-16.8,16.3,90,.8),(-14,18.3,180,.8),
             (-9,3.7,270,.8),(-9.4,7.1,270,.8),(-9.5,10.5,270,.8),
             (-9,13.9,270,.8),(-7.8,17.3,270,.8)]
# X, Z, half-width, centre elevation; ordered from cape tip to northern tip.
NODES = [(13,-27,.08,2.4),(10,-23,7.6,2.4),(5,-18,8.5,2.4),
         (0,-12,7.3,3.0),(-9,-7,8.7,4.7),(-14,2,10.2,7.2),
         (-14,12,9.5,8.4),(-10,20,7.2,7.7),(-1,26,5.5,5.5),
         (8,27,3.3,3.1),(14,24,.08,1.0)]

def catmull(p0,p1,p2,p3,t):
    return tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
                 for a,b,c,d in zip(p0,p1,p2,p3))

CENTRES=[]
for i in range(len(NODES)-1):
    for j in range(12):
        CENTRES.append(catmull(NODES[max(i-1,0)],NODES[i],NODES[i+1],NODES[min(i+2,len(NODES)-1)],j/12))
CENTRES.append(NODES[-1])

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)

def locate(x,z):
    best=None
    for i in range(len(CENTRES)-1):
        a,b=CENTRES[i:i+2]
        dx,dz=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
        cx,cz=a[0]+t*dx,a[1]+t*dz
        dist=math.hypot(x-cx,z-cz)
        width=max(.08,a[2]+(b[2]-a[2])*t)
        if best is None or dist<best[0]:
            best=(dist,width,a[3]+(b[3]-a[3])*t,i+t)
    return best

def base_height(x,z):
    dist,width,h,u=locate(x,z)
    v=dist/width
    # Broad level cape and village terraces support the interactive objects.
    cape=smooth(12,7,math.hypot(x-CAPE[0],z-CAPE[2]))
    h=h*(1-cape)+CAPE[1]*cape
    village=smooth(12,7,math.hypot(x+14,z-11))
    h=h*(1-village)+8.4*village
    h-=.12*min(1,v*v)
    h=(1-smooth(.78,1,v))*h+smooth(.78,1,v)*.32
    return h

def height(x,z):
    h=base_height(x,z)
    # Flatten just the house footprint and a short doorstep approach; keep the
    # continuous slope elsewhere. Blend weights remove abrupt pad boundaries.
    for hx,hz,yaw,s in HOUSE_SITES:
        rad=math.radians(yaw);dx=x-hx;dz=z-hz
        lx=math.cos(rad)*dx-math.sin(rad)*dz
        lz=math.sin(rad)*dx+math.cos(rad)*dz
        extent=max(abs(lx)/(1.8*s),abs(lz)/(1.7*s))
        weight=1-smooth(1,1.6,extent)
        if weight>0:h=h*(1-weight)+base_height(hx,hz)*weight
    return h

def local(x,y,z):
    return [CAPE[0]+x,CAPE[1]+y,CAPE[2]+z]

def grounded(x,z,lift=0):
    return [x,height(x,z)+lift,z]

def anchor(name,pos,forward=(0,0,1),kind="point",**extras):
    return dict(name=name,position=list(pos),forward=list(forward),kind=kind,**extras)

def aim(origin,targets):
    vectors=[]
    for target in targets:
        d=[b-a for a,b in zip(origin,target)];length=math.sqrt(sum(v*v for v in d))
        vectors.append([v/length for v in d])
    d=[sum(v[i] for v in vectors) for i in range(3)];length=math.sqrt(sum(v*v for v in d))
    return [v/length for v in d]

WAN=(1.0,3.8,4.5)
WINDOW=(-2.99836,1.62,2.82607)

ANCHORS=[
 anchor("Anchor_PlayerSpawn",local(4.4,.05,-3.5)),
 anchor("Anchor_Lamp_WanFeng",local(*WAN),aim(WAN,[(-1.5,.05,0),(2,.45,0)]),"lamp",height=3.8),
 anchor("Anchor_Lamp_YueChuang",local(-3,4,0),aim((-3,4,0),[WINDOW]),"lamp",height=4),
 anchor("Anchor_Lamp_GuiHang",local(4,3.8,3),(-.40637,-.68067,-.60955),"lamp",height=3.8),
 anchor("Target_Path",local(-1.5,.05,0),kind="target"),
 anchor("Target_Bench",local(2,.45,0),kind="target"),
 anchor("Target_Window",local(*WINDOW),(.438371,0,-.898794),"target"),
 anchor("Target_Pier",local(3,.08,5),kind="target"),
 anchor("Anchor_FlagpoleHook",local(3,1.85,10.5),(0,0,-1),"hook"),
 anchor("NPC_AYing",local(2.7,.08,8.5),(0,0,-1),"npc_feet"),
 anchor("NPC_Postman",grounded(CAPE[0]+1,CAPE[2]+8,.05),(0,0,-1),"npc_feet"),
 anchor("NPC_Bench",local(2,.45,.04),(0,0,1),"npc_seat"),
 anchor("NPC_ABo_Window",local(-3.58358,.49,4.02596),(.438371,0,-.898794),"npc_seat"),
 anchor("NPC_DengBo_Box",local(3.65,.64,10.2),(0,0,1),"npc_seat"),
 anchor("Anchor_VillageGate",grounded(-12,4),(.37139068,0,-.92847669),"npc_feet"),
 anchor("Anchor_GoldenTree",grounded(1.8,-21.4)),
 anchor("Anchor_Boat",[12.2,-.45,-12.3],(0,0,-1)),
 anchor("Target_Sea",[10,-.16,19.5],kind="target"),
 anchor("NPC_ABo_Door",grounded(6.20143,-18.23588),(.438371,0,-.898794),"npc_feet"),
 anchor("Cam_Title",[57,44,-73],[-62,-39,74],"camera",fov=45,lookAt=[-5,5,1]),
 anchor("Cam_Puzzle",[27,18,-45],[-20,-13,27],"camera",fov=43,lookAt=[7,5,-18]),
 anchor("Cam_Pier",[22,8,-11],[-12,-4,-4],"camera",fov=48,lookAt=[10,4,-15]),
 anchor("Cam_Village",[12,21,-8],[-26,-11,20],"camera",fov=48,lookAt=[-14,10,12]),
 anchor("Sky_ScatterZone_Village",[-13,11,11],kind="scatter",size=[21,5,18]),
 anchor("Sky_ScatterZone_Pier",local(3,2,7),kind="scatter",size=[3.3,3.5,9]),
]

# Eleven village houses frame a real central street, facing toward it.
HOUSES=[dict(name=f"VillageHouse_{i+1:02}",asset=f"cottage_{['teal','ochre','slate'][i%3]}",
             position=grounded(x,z),yaw=yaw,scale=s)
        for i,(x,z,yaw,s) in enumerate(HOUSE_SITES)]

PATHS=[
 dict(name="CapeVillage",width=1.75,points=[local(-1.5,.02,-1),local(-1.5,.02,0),local(0,.02,1.3),
      local(2.5,.02,1.8),local(2.5,.02,4.8),local(2.5,.02,6.4),local(0,.02,8),
      grounded(3,-11),grounded(0,-8.2),grounded(-5,-5),grounded(-10,-1),grounded(-12,4),
      grounded(-13,10),grounded(-12,16),grounded(-9,21),grounded(-3,25)]),
 dict(name="OuterCoast",width=1.35,points=[grounded(-12,4),grounded(-18,0),grounded(-20.9,4),
      grounded(-21.4,11),grounded(-19.2,17),grounded(-15.5,21),grounded(-9,23),grounded(-3,25)]),
 dict(name="CapePier",width=1.9,points=[local(-1.5,.03,0),local(0,.03,1),local(3,.03,2)]),
 dict(name="CapeHome",width=1.1,points=[local(-1.5,.03,0),local(-.6,.03,2.35),local(-1.06159,.03,3.3034)]),
 dict(name="SpawnLane",width=1.3,points=[local(4.4,.02,-3.5),local(4.4,.02,-1.5),local(3.8,.02,1.2),local(2.5,.02,1.8)]),
]

PROP_SITES=[
 dict(name="GrandmotherHouse",asset="abode_grandma",position=local(-3,0,4.7),yaw=154,scale=1),
 dict(name="Bench",asset="bench",position=local(2,0,0),yaw=0,scale=1),
 dict(name="Armillary",asset="armillary_platform",position=local(0,0,-3),yaw=0,scale=1),
 dict(name="CrescentMemorial",asset="crescent_sculpture",position=local(-5.8,0,-3.6),yaw=-20,scale=1),
 dict(name="Flagpole",asset="flagpole_blue",position=local(3,.08,10.8),yaw=180,scale=1),
 dict(name="HarborLantern",asset="harbor_lantern",position=local(3,1.06,10.5),yaw=0,scale=1),
 dict(name="KeeperBox",asset="dock_crate",position=local(3.65,.08,10.2),yaw=0,scale=1),
 dict(name="KeeperKettle",asset="dock_kettle",position=local(4.1,.08,10.0),yaw=0,scale=1),
 dict(name="Well",asset="village_well",position=grounded(-14.6,13),yaw=0,scale=1),
 dict(name="ClothesLine",asset="laundry_line",position=grounded(-15.5,5),yaw=90,scale=1),
]

if __name__=="__main__":
    report=dict(schema="jieguang.environment.layout.v1",units="metres",up="Y",capeOrigin=CAPE,
                source="art/design/script/07_完整故事与生图提示词（最终版）.md",
                anchors=ANCHORS,houses=HOUSES,props=PROP_SITES,paths=PATHS,
                lamps=dict(narrowAngle=24,wideAngle=60,wanfengWideAngle=56),
                note="Offline planned coordinates. Mesh clearance and Unity import verification pending.")
    (OUT/"layout.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(anchors=len(ANCHORS),houses=len(HOUSES),output=str(OUT/"layout.json"))))
