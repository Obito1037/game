"""Create an offline, self-contained Unity import payload; never writes Assets."""
import sys, json, hashlib, shutil, math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0, str(Path(__file__).parent))
import env_v1_layout as L

ROOT=L.ROOT
OUT=L.OUT
STAGE=OUT/'staging'
PREFIX='Assets/JieGuang/Environment/'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def copy_asset(path, subdir):
    source=ROOT/path
    dest=STAGE/subdir/source.name
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(dest.read_bytes()).digest():
        shutil.copy2(source,dest)
    return PREFIX+dest.relative_to(STAGE).as_posix()

def make():
    STAGE.mkdir(parents=True,exist_ok=True)
    models=[]; materials=[]; sources=[]
    props=read(OUT/'props/manifest.json')
    for a in props['assets']:
        models.append(dict(id=a['asset_id'],path=copy_asset(a['fbx'],'Models/Props'),lod1='',kind='prop'))
        sources.append(dict(id=a['asset_id'],triangles=a['triangles'],sha256=a['fbx_sha256'],source=a['fbx'],
                            source_script=a['source_script'],source_script_sha256=a['source_script_sha256'],
                            postprocessing=a.get('postprocessing',[]),
                            steps=['Original procedural low-poly model; modifiers applied; face normals checked.',
                                   'Metric FBX Y-up export; Blender FBX roundtrip validation.']))
    for m in props['materials']:
        materials.append(dict(name=m['name'],color=m['base_color'],emission=m['base_color'][:3],
                              strength=m['emission_strength'],metallic=m['metallic'],roughness=m['roughness'],texture='',emissionTexture=''))
    terrain=read(OUT/'terrain/manifest.json')
    models.append(dict(id='island_terrain',path=copy_asset('art/generated/env-v1/terrain/island_terrain.fbx','Models/Terrain'),lod1='',kind='terrain'))
    terrain_path='art/generated/env-v1/terrain/island_terrain.fbx'
    sources.append(dict(id='island_terrain',triangles=sum(m['triangles'] for m in terrain['meshes']),source=terrain_path,
                        sha256=hashlib.sha256((ROOT/terrain_path).read_bytes()).hexdigest(),
                        source_script=terrain['source_script'],source_script_sha256=terrain['source_sha256'],
                        steps=['Continuous crescent surface and cliff skirt generated from final story layout.',
                               'House pads levelled and walkable stone path geometry generated.',
                               'Metric Y-up FBX export.']))
    for m in terrain['material_settings']:
        materials.append(dict(name=m['name'],color=m['color'],emission=[0,0,0],strength=0,metallic=0,roughness=m['roughness'],texture='',emissionTexture=''))
    am=OUT/'asset-manifest.json'
    if am.exists():
        for a in read(am)['assets']:
            models.append(dict(id=a['id'],path=copy_asset(a['lod0']['fbx'],'Models/Natural/'+a['source_id']),
                               lod1=copy_asset(a['lod1']['fbx'],'Models/Natural/'+a['source_id']) if a.get('lod1') else '',kind=a['kind']))
            sources.append(dict(id=a['id'],triangles=a['lod0']['triangles'],lod1Triangles=a.get('lod1',{}).get('triangles',0),
                                source=a['source_path'],source_sha256=a['source_sha256'],sha256=a['lod0']['sha256'],steps=a['steps']))
            for m in a['materials']:
                if any(e['name']==m['name'] for e in materials): continue
                tex=copy_asset(m['base_color_texture'],'Textures/'+a['source_id']) if m.get('base_color_texture') else ''
                emi=copy_asset(m['emission_texture'],'Textures/'+a['source_id']) if m.get('emission_texture') else ''
                base=m.get('base_color',[1,1,1,1]);base=list(base)+([1] if len(base)==3 else [])
                materials.append(dict(name=m['name'],color=base,emission=([1,1,1] if emi else m.get('emission_color',[0,0,0])),
                                      strength=m.get('emission_strength',0),metallic=0,roughness=m['roughness'],texture=tex,emissionTexture=emi))
    instances=[dict(name='IslandTerrain',asset='island_terrain',position=[0,0,0],yaw=0,scale=1,group='Terrain',collider='ground')]
    for a in L.HOUSES:
        instances.append(dict(a,group='Village',collider='solid'))
    for a in L.PROP_SITES:
        instances.append(dict(a,group='Props',collider='solid' if a['asset'] not in ['dock_kettle','laundry_line','harbor_lantern'] else 'none'))
    for i,z in enumerate([3.5,6.5,9.5]):
        instances.append(dict(name=f'PierDeck_{i+1:02}',asset='pier_module',position=L.local(3,.08,z),yaw=0,scale=1,group='Pier',collider='ground'))
    def natural(name,asset,x,z,scale=1,yaw=0,y=None,group='Forest',collider='solid'):
        instances.append(dict(name=name,asset=asset,position=L.grounded(x,z) if y is None else [x,y,z],yaw=yaw,scale=scale,group=group,collider=collider))
    natural('GoldenLightTree','tree_gold',1.8,-21.4,1,18)
    tree_sites=[(-1,-14,.76),(-2.2,-10.5,.87),(-6,-11.5,.76),(-8,-8,.82),(-12,-6,.84),(-16,-4,.78),
                (-19,-1,.64),(-13.2,-1.5,.70),(-6,2,.80),(-4.8,-9,.86),(-12.7,-3.8,.69),(-11,25,.65),(-14.7,9,.9)]
    for i,(x,z,s) in enumerate(tree_sites):
        sink=.30 if i==7 else (.20 if i==9 else .05)
        natural(f'LightTree_{i+1:02}', ['tree_a','tree_b','tree_c'][i%3],x,z,s,(i*137)%360,y=L.height(x,z)-sink)
    # Cliffs / rocks are set into the shore, never scattered over the puzzle targets.
    rock_sites=[(14,-24,.50),(16,-20,.48),(11,-27,.47),(0,-24,.40),(-7,-17,.48),(-14,-14,.55),
                (-22,-7,.55),(-26,2,.58),(-25,16,.60),(-19,25,.63),(-6,30,.55),(5,31,.55),(13,28,.65)]
    for i,(x,z,s) in enumerate(rock_sites):
        natural(f'ShoreRock_{i+1:02}', ['rock_mass','rock_cluster','rock_mountain'][i%3],x,z,s,(i*73)%360,y=-.22,group='Rocks')
    natural('PostmanWaystone','rock_mass',L.CAPE[0],L.CAPE[2]+9.4,.22,47,group='Rocks')
    natural('OuterRockArch','rock_arch',19,21,.65,80,y=-.25,group='Rocks')
    for i,(x,z) in enumerate([(24,35),(33,16),(30,-25),(-31,24),(-30,-12),(3,40)]):
        natural(f'DistantReef_{i+1:02}',f'rock_cluster_reef_{i%2+1:02}',x,z,.75+(i%3)*.1,i*71,y=-.16,group='Rocks',collider='none')
    natural('ReturningBoat','boat',12.2,-12.3,.90,180,y=-.45,group='Props',collider='none')
    available={a['id'] for a in models}
    missing=sorted({a['asset'] for a in instances}-available)
    by_id={a['id']:a for a in sources}
    active=sum(by_id.get(a['asset'],{}).get('triangles',0) for a in instances)+3*by_id['copper_roadlamp']['triangles']
    stored=active+sum(by_id.get(a['asset'],{}).get('lod1Triangles',0) for a in instances)
    data=dict(models=models,materials=materials,instances=instances,anchors=L.ANCHORS,
              boundary=[dict(position=p) for p in terrain['boundary']],boundaryNote='Main land loop. Separate Pier boundary is generated by builder.',
              sourceDesign='art/design/script/07_完整故事与生图提示词（最终版）.md')
    (STAGE/'scene-input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(schema='jieguang.environment.manifest.v1',status='offline_staging_NOT_Unity_verified',
                original_sources='inventory.json',processed_sources='asset-manifest.json',sources=sources,
                missingAssets=missing,instances=len(instances),highestLODInstanceTriangles=active,
                allLODInstanceTriangles=stored,countsExclude='Procedural sky/ocean/extra colliders, actual Unity import not measured.',
                fps='Not measured. 60 FPS is a target only.',unityPermission='User says wait for notification; no files copied into Assets.')
    (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    anchors={a['name']:a for a in L.ANCHORS}
    def beam(lamp,targets,angle):
        origin=anchors['Anchor_Lamp_'+lamp]['position']
        points=[anchors['Target_'+t]['position'] for t in targets]
        forward=L.aim(origin,points)
        offsets=[]
        for point in points:
            d=L.aim(origin,[point]);offsets.append(math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(d,forward)))))))
        return dict(anchor='Anchor_Lamp_'+lamp,targets=['Target_'+t for t in targets],
                    forward=forward,fullSpotAngleDegrees=angle,targetOffsetsDegrees=offsets,
                    smallestCentrelineMarginDegrees=angle/2-max(offsets))
    states=dict(chapter1=[beam('WanFeng',['Path','Bench'],56)],
                chapter2=[beam('WanFeng',['Path','Bench'],56),beam('YueChuang',['Window'],24)],
                chapter3=[beam('WanFeng',['Path'],24),beam('YueChuang',['Window','Pier'],60),beam('GuiHang',['Bench'],24)])
    (OUT/'puzzle-light-layout.json').write_text(json.dumps(dict(
        status='Analytical target-centre geometry only. Actual mesh occlusion requires verification.',
        transformRule='Anchor stays upright; rotate its LampHead child. Forward is world +Z for the spot.',
        chapterStates=states),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(models=len(models),instances=len(instances),missing=missing,triangles=active)))
    return data

if __name__=='__main__': make()
