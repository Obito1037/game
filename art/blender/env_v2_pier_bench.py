"""Zero-geometry offline wood surface candidates for JieGuang pier/bench.
Writes only art/generated/env-v2/pier-bench; does not import into Unity.
"""
import bpy,bmesh,json,hashlib,random,math,struct,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
import numpy as np

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'art/generated/env-v2/pier-bench';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'art/generated/env-v1/props';SCENE=ROOT/'art/generated/env-v1/staging/scene-input.json'
TEXTURE=ROOT/'art/generated/env-v2/textures/wood_albedo_v1.png'
IDS=['pier_module','pier_end','bench']
PRESETS={'Wood_Endgrain':{'shared':'CoastalWood_Light','tint':[.62,.57,.46],'roughness':.88},
         'Wood_Honey':{'shared':'CoastalWood_Brown','tint':[.48,.42,.33],'roughness':.87},
         'Wood_DarkBeams':{'shared':'CoastalWood_Dark','tint':[.26,.22,.17],'roughness':.90},
         'Wood_Weathered':{'shared':'CoastalWood_Silver','tint':[.38,.38,.32],'roughness':.92}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def meshes():return [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('Study_')]
def tris(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def bounds(objects):
    pts=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {key:[fn(v[i] for v in pts) for i in range(3)] for key,fn in [('min',min),('max',max)]}
def geometry():
    return {o.name:{'matrix':[list(r) for r in o.matrix_world],'vertices':[list(v.co) for v in o.data.vertices],
                   'polygons':[list(f.vertices) for f in o.data.polygons],'slots':[m.name for m in o.data.materials],
                   'indices':[f.material_index for f in o.data.polygons],'smooth':[f.use_smooth for f in o.data.polygons]} for o in meshes()}
def markers():return {o.name:{'world':[list(r) for r in o.matrix_world],'local':[list(r) for r in o.matrix_local],'parent':o.parent.name if o.parent else None} for o in bpy.context.scene.objects if o.type=='EMPTY'}
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
def components(o):
    adjacency=[set() for _ in o.data.vertices]
    for edge in o.data.edges:
        a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
    groups=[];remain=set(range(len(adjacency)))
    while remain:
        seed=min(remain);remain.remove(seed);stack=[seed];ids=[]
        while stack:
            v=stack.pop();ids.append(v)
            for n in adjacency[v]:
                if n in remain:remain.remove(n);stack.append(n)
        groups.append(sorted(ids))
    lookup={v:i for i,g in enumerate(groups) for v in g};polys=[[] for _ in groups]
    for f in o.data.polygons:polys[lookup[f.vertices[0]]].append(f.index)
    return list(zip(groups,polys))
def assign_uv():
    reports=[];global_min=1.;global_max=0.
    for o in meshes():
        d=o.data;uv=d.uv_layers.active or d.uv_layers.new(name='UVMap');uv.name='UVMap'
        for ci,(vertices,faces) in enumerate(components(o)):
            wood_faces=[d.polygons[i] for i in faces if d.materials[d.polygons[i].material_index].name in PRESETS]
            if not wood_faces:continue
            pts=np.array([list(d.vertices[i].co) for i in vertices]);center=Vector(pts.mean(axis=0));values,vectors=np.linalg.eigh(np.cov((pts-pts.mean(axis=0)).T))
            axis=Vector(vectors[:,int(np.argmax(values))].tolist()).normalized()
            if axis[max(range(3),key=lambda k:abs(axis[k]))]<0:axis=-axis
            projections=[axis.dot(d.vertices[i].co) for i in vertices];lo=min(projections);span=max(projections)-lo
            rng=random.Random(9601+ci);v_offset=.04+rng.random()*max(0,.92-span/4.9);u_offset=rng.uniform(.04,.96);endfaces=0;sidefaces=0;changes=0
            for face in wood_faces:
                n=face.normal.normalized();vaxis=axis-n*axis.dot(n)
                endgrain=vaxis.length<.15
                if endgrain:
                    # Planar short end-cap sample of the same original wood. No
                    # fabricated annual-ring or dedicated cut-end texture claim.
                    uaxis=Vector(vectors[:,0].tolist());uaxis=(uaxis-n*uaxis.dot(n)).normalized();vaxis=n.cross(uaxis).normalized();endfaces+=1
                else:vaxis.normalize();uaxis=n.cross(vaxis).normalized();sidefaces+=1
                for li in face.loop_indices:
                    p=d.vertices[d.loops[li].vertex_index].co
                    if endgrain:new=(uaxis.dot(p-center)/.70+u_offset,vaxis.dot(p-center)/.70+.50)
                    else:new=(uaxis.dot(p-center)+u_offset,(axis.dot(p)-lo)/4.9+v_offset)
                    old=list(uv.data[li].uv);uv.data[li].uv=new;changes+=old!=list(uv.data[li].uv)
                    global_min=min(global_min,new[1]);global_max=max(global_max,new[1])
            reports.append({'object':o.name,'component':ci,'materials':sorted({d.materials[f.material_index].name for f in wood_faces}),
                'long_axis':list(axis),'length_m':span,'side_faces':sidefaces,'end_faces':endfaces,'changed_uv_corners':changes,
                'size':list(np.ptp(pts,axis=0))})
    return {'u_metres':1.0,'v_metres':4.9,'end_cap_patch_metres':.70,'wood_components':reports,'v_range':[global_min,global_max],
            'end_cap_limitation':'Same original wood image in planar end projection; no dedicated annual-ring texture or baked normal map.'}
def materials():
    image=bpy.data.images.load(str(TEXTURE),check_existing=True);image.colorspace_settings.name='sRGB';image.filepath=str(TEXTURE);image.pack();used=[]
    for name,preset in PRESETS.items():
        m=bpy.data.materials.get(name)
        if not m:continue
        m.use_nodes=True;nodes=m.node_tree.nodes;nodes.clear();links=m.node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.name='OriginalWoodAlbedo';tex.image=image;tex.extension='REPEAT';tex.interpolation='Linear'
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UVMap';links.new(uv.outputs[0],tex.inputs[0])
        mult=nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(*preset['tint'],1);links.new(tex.outputs['Color'],mult.inputs[1])
        bs=nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Roughness'].default_value=preset['roughness'];links.new(mult.outputs[0],bs.inputs['Base Color'])
        out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs[0]);m.diffuse_color=(*preset['tint'],1);used.append({'source_name':name,**preset})
    return image,used
def camera_set(asset):
    if asset=='bench':return {'whole':{'position':[2.7,-4.4,2.55],'look':[0,0,.52],'scale':2.55},'surface':{'position':[1.9,-3.6,2.5],'look':[0,0,.62],'scale':2.15}}
    return {'whole':{'position':[5.8,-7.6,4.5],'look':[0,0,-1.30],'scale':5.55},'surface':{'position':[4.3,-5.6,5.1],'look':[0,0,-.13],'scale':4.65 if asset=='pier_module' else 5.1}}
def render(asset,dest,prefix,kind):
    for o in list(bpy.context.scene.objects):
        if o.type in ['LIGHT','CAMERA'] or o.name.startswith('Study_'):bpy.data.objects.remove(o,do_unlink=True)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True;sc.render.resolution_x=900;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=0;sc.view_settings.gamma=1
    world=bpy.data.worlds.new('Study_'+kind);world.use_nodes=True;sc.world=world;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.10,.17,1) if kind=='night' else (.18,.21,.23,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
    bench=asset=='bench';look=Vector((0,0,.4 if bench else -.45));factor=.23 if bench else 1
    lamps=[((3,-4,4),330*factor,2.5,(1,.63,.32)),((-3,3,3),100*factor,3,(.55,.67,1))] if kind=='night' else [((3,-4,6),1050*factor,4,(1,.96,.90)),((-4,-2,4),650*factor,4,(.84,.91,1)),((1,4,5),800*factor,3,(1,.97,.88))]
    for pos,power,size,color in lamps:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='Study_Light';o.data.energy=power;o.data.size=size;o.data.color=color;o.rotation_euler=(look-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004 if bench else -3.204));o=bpy.context.object;o.name='Study_Ground';m=bpy.data.materials.new('Study_Ground_Mat');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.09,.11,.11,1);o.data.materials.append(m)
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Study_Camera';cam.data.type='ORTHO';sc.camera=cam
    for name,cfg in camera_set(asset).items():
        cam.location=cfg['position'];cam.rotation_euler=(Vector(cfg['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cfg['scale'];sc.render.filepath=str(dest/f'{prefix}-{kind}-{name}.png');bpy.ops.render.render(write_still=True)
    for o in list(sc.objects):
        if o.type in ['LIGHT','CAMERA'] or o.name.startswith('Study_'):bpy.data.objects.remove(o,do_unlink=True)
def check_fbx(asset,dest,expected,b0,m0):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(dest/(asset+'_v2_candidate.fbx')))
    actual={o.name:o for o in meshes()};errors={}
    for name,record in expected.items():
        pts=[actual[name].matrix_world@v.co for v in actual[name].data.vertices];tree=KDTree(len(pts))
        for i,p in enumerate(pts):tree.insert(p,i)
        tree.balance();source_points=[Matrix(record['matrix'])@Vector(v) for v in record['vertices']]
        source_tree=KDTree(len(source_points))
        for i,p in enumerate(source_points):source_tree.insert(p,i)
        source_tree.balance();errors[name]=max(max(tree.find(v)[2] for v in source_points),max(source_tree.find(v)[2] for v in pts))
    b1=bounds(meshes());m1=markers()
    checks={'one_structure_mesh':set(actual)=={'Structure'},'triangles_exact':tris(actual['Structure'])==expected['Structure']['triangles'],
            'material_slots_exact':[m.name for m in actual['Structure'].data.materials]==expected['Structure']['slots'],
            'bounds_within_1micrometre':all(abs(b0[k][i]-b1[k][i])<1e-6 for k in ['min','max'] for i in range(3)),
            'root_marker_names_exact':set(m0)==set(m1),
            'root_marker_matrices_within_1micrometre':all(abs(m0[n][kind][r][c]-m1[n][kind][r][c])<1e-6 for n in m0 for kind in ['world','local'] for r in range(4) for c in range(4)),
            'vertices_within_1micrometre':all(v<1e-6 for v in errors.values()),'uv0_exists':'UVMap' in [u.name for u in actual['Structure'].data.uv_layers]}
    return {'checks':checks,'all_pass':all(checks.values()),'triangles':tris(actual['Structure']),'bounds':b1,'maximum_vertex_errors_m':errors}

def process(asset,instance_rows,source_record):
    path=SOURCE/asset/(asset+'.blend');source_hash=sha(path);dest=OUT/asset;dest.mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update();g0=geometry();m0=markers();b0=bounds(meshes());total=sum(tris(o) for o in meshes())
    o=bpy.data.objects['Structure'];o.data.calc_loop_triangles();protected_z=0 if asset.startswith('pier') else .45
    protected=[{'vertex':v.index,'xyz':list(v.co)} for v in o.data.vertices if abs(v.co.z-protected_z)<1e-6]
    source_inspection={'asset_id':asset,'source':str(path.relative_to(ROOT)),'source_sha256':source_hash,'triangles':total,'mesh_count':len(meshes()),'bounds':b0,'markers':m0,
                       'instances':instance_rows,'instance_count':len(instance_rows),'protected_plane_z':protected_z,'protected_plane_vertices':protected,'original_mesh_hash':digest(g0),
                       'actual_pile_bottom':b0['min'][2] if asset.startswith('pier') else None,'source_manifest_record':source_record}
    dump(dest/'source-inventory.json',source_inspection)
    for kind in ['neutral','night']:render(asset,dest,'before',kind)
    uv=assign_uv();image,mapping=materials();g1=geometry();m1=markers();b1=bounds(meshes());total_after=sum(tris(o) for o in meshes())
    checks={'geometry_indices_slots_smoothing_exact':g0==g1,'root_marker_poses_exact':m0==m1,'bounds_exact':b0==b1,'triangles_exact':total==total_after,
            'protected_deck_or_seat_vertices_exact':all(list(o.data.vertices[p['vertex']].co)==p['xyz'] for p in protected),
            'source_hash_unchanged':sha(path)==source_hash,'wood_V_does_not_wrap':uv['v_range'][0]>=.039 and uv['v_range'][1]<=.961}
    report={'asset_id':asset,'status':'offline-surface-candidate-awaiting-visual-review','source_sha256':source_hash,'source_inspection':'source-inventory.json',
            'before_triangles':total,'after_triangles':total_after,'additional_triangles':total_after-total,'scene_input_instances':instance_rows,'instance_count':len(instance_rows),
            'geometry_before_sha256':digest(g0),'geometry_after_sha256':digest(g1),'before_bounds':b0,'after_bounds':b1,'markers_before':m0,'markers_after':m1,
            'checks':checks,'wood_uv':uv,'material_mapping':mapping,'texture':{'path':str(TEXTURE.relative_to(ROOT)),'size':list(image.size),'sha256':sha(TEXTURE)},
            'protected_plane_z':protected_z,'protected_plane_vertex_count':len(protected),'render_resolution':[900,900],'views':camera_set(asset),
            'surface_limitations':['No new bitmap, normal or end-ring texture was synthesized.','Wood_Endgrain is a historical material name: it includes full planks; UVs distinguish actual end caps.','No geometry, bevels, nail heads, seams or collider changes. Bench already has rounded slats.']}
    dump(dest/'manifest.json',report)
    if not all(checks.values()):raise RuntimeError(json.dumps(checks))
    blend=dest/(asset+'_v2_candidate.blend');fbx=dest/(asset+'_v2_candidate.fbx');bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    for kind in ['neutral','night']:render(asset,dest,'after',kind)
    expected=geometry();expected['Structure']['triangles']=total_after;rt=check_fbx(asset,dest,expected,b0,m0);dump(dest/'fbx-roundtrip.json',rt)
    report['fbx_roundtrip']=rt;report['script_sha256']=sha(Path(__file__));report['files']=[{'path':str(f.relative_to(ROOT)),'sha256':sha(f),'bytes':f.stat().st_size} for f in [blend,fbx]+sorted(dest.glob('*.png'))];dump(dest/'manifest.json',report)
    print('PIER_BENCH_ASSET_DONE',asset,total_after,rt['all_pass'],flush=True);return report

if __name__=='__main__':
    scene=json.loads(SCENE.read_text(encoding='utf-8'));source=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    selected=[arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--asset=')];chosen=selected or IDS
    if any(x not in IDS for x in chosen):raise RuntimeError('Invalid asset selection')
    results=[process(asset,[r for r in scene['instances'] if r['asset']==asset],next(r for r in source['assets'] if r['asset_id']==asset)) for asset in chosen]
    results += [json.loads((OUT/asset/'manifest.json').read_text(encoding='utf-8')) for asset in IDS if asset not in chosen and (OUT/asset/'manifest.json').exists()]
    report={'status':'offline-candidates-awaiting-review','scene_input':str(SCENE.relative_to(ROOT)),'scene_input_sha256':sha(SCENE),'source_manifest_sha256':sha(SOURCE/'manifest.json'),'assets':results,
            'instance_counts':{a:sum(r['asset']==a for r in scene['instances']) for a in IDS},'added_triangles_actual_island':sum(r['additional_triangles']*r['instance_count'] for r in results),'budget_actual_island':1200}
    dump(OUT/'manifest.json',report);print('PIER_BENCH_DONE',report['instance_counts'],report['added_triangles_actual_island'],flush=True)
