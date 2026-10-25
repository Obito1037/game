"""Offline village cottage upgrade; writes only env-v2/village. Never Unity."""
import bpy,bmesh,json,hashlib,math,random,sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v2/village';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'art/generated/env-v1/props'
TEXTURE=ROOT/'art/generated/env-v2/textures/wood_albedo_v1.png'
IDS=['cottage_teal','cottage_ochre','cottage_slate']
CONFIG={'cottage_teal':(3.1,2.65,2.22,1.10),'cottage_ochre':(3.35,2.8,2.28,1.0),'cottage_slate':(2.75,2.8,2.2,1.15)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def triangles(o):o.data.calc_loop_triangles();return len(o.data.loop_triangles)
def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
def meshes():return [o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('Study_')]
def components(o):
    adjacency=[set() for _ in o.data.vertices]
    for e in o.data.edges:
        a,b=e.vertices;adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(range(len(adjacency)));groups=[]
    while remaining:
        start=min(remaining);remaining.remove(start);stack=[start];ids=[]
        while stack:
            v=stack.pop();ids.append(v)
            for n in adjacency[v]:
                if n in remaining:remaining.remove(n);stack.append(n)
        groups.append(sorted(ids))
    polys=[[] for _ in groups];lookup={v:gi for gi,g in enumerate(groups) for v in g}
    for f in o.data.polygons:polys[lookup[f.vertices[0]]].append(f.index)
    result=[]
    for gi,ids in enumerate(groups):
        points=[o.matrix_world@o.data.vertices[v].co for v in ids]
        lo=[min(v[a] for v in points) for a in range(3)];hi=[max(v[a] for v in points) for a in range(3)]
        result.append({'index':gi,'vertices':ids,'faces':polys[gi],'materials':sorted({o.data.materials[o.data.polygons[f].material_index].name for f in polys[gi]}),
                       'min':lo,'max':hi,'center':[(lo[a]+hi[a])*.5 for a in range(3)],'size':[hi[a]-lo[a] for a in range(3)]})
    return result
def mesh_hash(o,include_uv=False):
    data={'matrix':[list(row) for row in o.matrix_world],'verts':[list(v.co) for v in o.data.vertices],
          'faces':[list(f.vertices) for f in o.data.polygons],'materials':[m.name for m in o.data.materials],
          'indices':[f.material_index for f in o.data.polygons]}
    if include_uv:data['uv']=[[list(v.uv) for v in uv.data] for uv in o.data.uv_layers]
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()
def interface():
    return {'root':{o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY' and o.parent is None},
            'markers':{o.name:[list(row) for row in o.matrix_world] for o in bpy.context.scene.objects if o.type=='EMPTY' and o.name.startswith('Marker_')},
            'windows':{o.name:{'matrix':[list(row) for row in o.matrix_world],'local_matrix':[list(row) for row in o.matrix_local],
                               'hash':mesh_hash(o,True),'bounds':bounds([o]),'parent':o.parent.name if o.parent else None} for o in meshes() if o.name.startswith('Window_')}}

def audit_sources():
    rows=[]
    original=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
    for asset in IDS:
        path=SOURCE/asset/(asset+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update()
        rows.append({'asset_id':asset,'source_blend':str(path.relative_to(ROOT)),'source_sha256':sha(path),
                     'manifest_record':next(x for x in original['assets'] if x['asset_id']==asset),
                     'mesh_count':len(meshes()),'triangles':sum(triangles(o) for o in meshes()),'bounds':bounds(meshes()),
                     'interface':interface(),'structure_components':components(bpy.data.objects['Structure'])})
    dump(OUT/'source-inventory.json',{'source_manifest_sha256':sha(SOURCE/'manifest.json'),'assets':rows,
                                    'texture':{'path':str(TEXTURE.relative_to(ROOT)),'sha256':sha(TEXTURE)}})
    return rows

PRESETS={'Whitewashed':((1,.96,.86),.78),'Weathered':((.88,.82,.70),.82),'Honey':((.46,.31,.18),.72),'DarkBeam':((.25,.17,.10),.80)}
WOODMAP={'Wall_WarmIvory':'Whitewashed','Wall_LightTimber':'Weathered','Wood_Honey':'Honey','Wood_Endgrain':'Honey','Wood_DarkBeams':'DarkBeam'}
VIEWS={'front':{'camera':[6.2,-9.0,6.0],'look':[0,0,1.8],'scale':6.2},
       'back':{'camera':[-6.2,9.0,5.5],'look':[0,0,1.8],'scale':6.2}}
def render(dest,prefix,kind):
    for o in list(bpy.context.scene.objects):
        if o.type in ['LIGHT','CAMERA'] or o.name.startswith('Study_'):bpy.data.objects.remove(o,do_unlink=True)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=20;sc.cycles.use_denoising=True
    sc.render.resolution_x=900;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG'
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=0;sc.view_settings.gamma=1
    world=bpy.data.worlds.new('VillageStudy_'+kind);world.use_nodes=True;sc.world=world
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.105,.18,1) if kind=='night' else (.18,.21,.23,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65 if kind=='night' else .65
    lights=[((3,-4,4),330,3,(1,.63,.32)),((-3,4,4),115,4,(.52,.64,1))] if kind=='night' else [((3,-4,7),1050,5,(1,.96,.90)),((-4,-2,4),650,5,(.84,.91,1)),((1,4,6),800,4,(1,.97,.88))]
    for pos,power,size,color in lights:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='Study_Light';o.data.energy=power;o.data.size=size;o.data.color=color
        o.rotation_euler=(Vector((0,0,1.6))-o.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004));o=bpy.context.object;o.name='Study_Ground'
    m=bpy.data.materials.new('Study_GroundMaterial');m.diffuse_color=(.10,.12,.12,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.10,.12,.12,1);o.data.materials.append(m)
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Study_Camera';cam.data.type='ORTHO';sc.camera=cam
    for view,cfg in VIEWS.items():
        cam.location=cfg['camera'];cam.rotation_euler=(Vector(cfg['look'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=cfg['scale']
        sc.render.filepath=str(dest/f'{prefix}-{kind}-{view}.png');bpy.ops.render.render(write_still=True)
    for o in list(sc.objects):
        if o.type in ['LIGHT','CAMERA'] or o.name.startswith('Study_'):bpy.data.objects.remove(o,do_unlink=True)

def add_mesh(name,verts,faces,material):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(material);return o
def box(name,loc,size,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);return o
def apply_wood_materials():
    image=bpy.data.images.load(str(TEXTURE),check_existing=True);image.colorspace_settings.name='sRGB';image.filepath=str(TEXTURE);image.pack()
    for name,preset in WOODMAP.items():
        m=bpy.data.materials.get(name)
        if not m:continue
        tint,rough=PRESETS[preset];m.use_nodes=True;n=m.node_tree.nodes;n.clear();links=m.node_tree.links
        out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');tex=n.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';tex.interpolation='Linear'
        uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap';links.new(uv.outputs[0],tex.inputs[0]);multiply=n.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=(*tint,1)
        links.new(tex.outputs['Color'],multiply.inputs[1]);links.new(multiply.outputs[0],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=rough;links.new(bs.outputs[0],out.inputs[0]);m.diffuse_color=(*tint,1)
    return image
def wood_uv(o):
    import numpy as np
    d=o.data;uv=d.uv_layers.active or d.uv_layers.new(name='UVMap');uv.name='UVMap';rows=[];vmin=1.;vmax=0.
    for comp in components(o):
        fs=[d.polygons[i] for i in comp['faces'] if d.materials[d.polygons[i].material_index].name in WOODMAP]
        if not fs:continue
        points=np.array([list(d.vertices[i].co) for i in comp['vertices']]);center=Vector(points.mean(axis=0));eigen,evec=np.linalg.eigh(np.cov((points-points.mean(axis=0)).T))
        axis=Vector(evec[:,int(np.argmax(eigen))].tolist()).normalized()
        if axis[max(range(3),key=lambda k:abs(axis[k]))]<0:axis=-axis
        rng=random.Random(501+comp['index']);uoffset=rng.uniform(.05,.95)
        for face in fs:
            matname=d.materials[face.material_index].name;normal=face.normal.normalized();grain=axis.copy()
            if matname.startswith('Wall_'):
                # Each visible wall plane represents horizontal timber courses.
                grain=Vector((0,1,0)) if abs(normal.x)>.8 else Vector((1,0,0))
            projection=grain-normal*grain.dot(normal)
            if projection.length<.1:
                grain=normal.cross(Vector((0,0,1))) if abs(normal.z)<.9 else normal.cross(Vector((1,0,0)))
                grain.normalize()
            else:grain=projection.normalized()
            across=normal.cross(grain).normalized()
            ps=[grain.dot(d.vertices[i].co) for i in comp['vertices']];span=max(ps)-min(ps);offset=.04+rng.random()*max(0,.92-span/4.9)
            for li in face.loop_indices:
                p=d.vertices[d.loops[li].vertex_index].co;u=across.dot(p-center)+uoffset;v=(grain.dot(p)-min(ps))/4.9+offset
                uv.data[li].uv=(u,v);vmin=min(vmin,v);vmax=max(vmax,v)
        rows.append({'component':comp['index'],'materials':comp['materials'],'wood_faces':len(fs),'size':comp['size']})
    return {'components':rows,'component_count':len(rows),'u_metres':1.0,'v_metres':4.9,'v_range':[vmin,vmax],'grain_axis_in_texture':'V'}

def upgrade(asset,row):
    dest=OUT/asset;dest.mkdir(exist_ok=True);path=SOURCE/asset/(asset+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update()
    before=interface();b0=bounds(meshes());structure=bpy.data.objects['Structure'];source_materials=[m.name for m in structure.data.materials]
    source_components=components(structure);w,d,h,rise=CONFIG[asset]
    protected={c['index']:[[list(structure.data.vertices[v].co) for v in c['vertices']], [list(structure.data.polygons[f].vertices) for f in c['faces']]] for c in source_components if c['index'] in [0,1,12,17]}
    for kind in ['neutral','night']:render(dest,'before',kind)
    # Only decorative grid lines/siding strips and the chimney cap are replaced.
    remove=[];changes=[];protected_positions=[tuple(structure.data.vertices[v].co) for c in source_components if c['index'] in [0,1,12,17] for v in c['vertices']]
    for c in source_components:
        mats=c['materials'];size=c['size'];x,y,z=c['center'];ids=c['vertices']
        old_grid=any(m.startswith('Roof_') and 'Highlight' in m for m in mats) and not(size[0]<.20 and size[1]>d and z>h+rise)
        old_siding=mats==['Wood_Endgrain'] and size[0]>w-.1 and size[2]<.03
        chimney_cap=mats==['Stone_WarmLimestone'] and z>h+rise*.7 and size[0]<.6
        if old_grid or old_siding or chimney_cap:
            remove.extend(ids);changes.append({'component':c['index'],'action':'replace','reason':'roof_grid' if old_grid else ('front_siding_strip' if old_siding else 'solid_chimney_cap')});continue
        if mats==['Wood_DarkBeams'] and size[0]<.14 and size[1]<.14 and size[2]>h:
            # Old post feet coincide with the vertical plinth faces between
            # z=.05 and .20. Terminate the wood at the retained stone top.
            changed=0
            for vi in ids:
                if structure.data.vertices[vi].co.z<.20:structure.data.vertices[vi].co.z=.202;changed+=1
            changes.append({'component':c['index'],'action':'resolve_post_plinth_coplanar_faces','vertices':changed,'old_lower_z':c['min'][2],'new_lower_z':.202})
        if mats==['Wood_DarkBeams'] and .89<size[0]<.93 and .10<size[2]<.14 and z>1.9 and y<0:
            for vi in ids:
                q=structure.data.vertices[vi].co;q.x=x+(q.x-x)*(size[0]+.004)/size[0]
            changes.append({'component':c['index'],'action':'resolve_lintel_post_end_coplanarity','end_extension_metres':.002})
        # The old rear frames sit behind their emissive plate. Correct only
        # decorative trim, keeping the actual two window meshes untouched.
        is_frame=mats==['Wood_DarkBeams'] and size[2]<1.1 and size[0]<1.1 and abs(abs(y)-d/2)<.14
        is_rear_sill=mats==['Wood_Endgrain'] and y>0 and size[0]<1.2 and z<1.1
        delta=0.
        if is_frame:
            if y>0:delta+=.08
            if size[0]>.4 and size[2]<.1:delta+=(.006 if abs(z-1.4)<.04 else .003)*(1 if y>0 else -1)
        if is_rear_sill:delta=.20
        if delta:
            for vi in ids:structure.data.vertices[vi].co.y+=delta
            changes.append({'component':c['index'],'action':'trim_depth_only','delta_y':delta})
    bm=bmesh.new();bm.from_mesh(structure.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in sorted(set(remove))],context='VERTS');bm.to_mesh(structure.data);bm.free()
    additions=[];mats={m.name:m for m in structure.data.materials};wall=mats['Wall_LightTimber' if asset=='cottage_ochre' else 'Wall_WarmIvory']
    roofmat=next(m for m in structure.data.materials if m.name.startswith('Roof_') and 'Highlight' not in m.name)
    highmat=next(m for m in structure.data.materials if m.name.startswith('Roof_') and 'Highlight' in m.name)
    rng=random.Random(743+IDS.index(asset))
    # 48 thin curved clay tiles. Hidden undersides and upper caps are omitted:
    # retained original roof slabs provide a continuous opaque backing.
    reach=w/2+.29;run=d+.47;rows=4;cols=6
    for side in [-1,1]:
        for r in range(rows):
            x0=.035+(reach-.055)*r/rows;x1=.035+(reach-.055)*(r+1)/rows+.035
            x1=min(x1,reach-.010)
            for c in range(cols):
                y0=-run/2+run*c/cols+r*.0018;y1=-run/2+run*(c+1)/cols-.006+r*.0018
                amp=rng.uniform(.024,.037);lift=.006+(rows-r)*.003;ripple=rng.uniform(-.003,.003)
                verts=[]
                for xx in [x0,x1]:
                    for k in range(4):
                        yy=y0+(y1-y0)*k/3
                        zz=h+.1+rise+.10-(rise+.05)*xx/reach+lift+amp*math.sin(math.pi*k/3)+ripple
                        verts.append((side*xx,yy,zz))
                for xx in [x0,x1]:
                    for yy in [y0,y1]:
                        zz=h+.1+rise+.10-(rise+.05)*xx/reach+.002
                        verts.append((side*xx,yy,zz))
                faces=[(k,k+1,5+k,4+k) for k in range(3)]
                # Eave nose follows the curved top and meets an inset flat base.
                faces += [(4,5,10),(5,6,11,10),(6,7,11),(0,4,10,8),(3,9,11,7)]
                if side>0:faces=[tuple(reversed(f)) for f in faces]
                o=add_mesh('V2_CurvedRoofTile',verts,faces,highmat if rng.random()<.18 else roofmat);additions.append(o)
                for poly in list(o.data.polygons)[:3]:poly.use_smooth=True
    # Six lapped horizontal timber courses per wall, 8–12 mm proud. They remain
    # behind both unchanged window panes and the old door leaf.
    for faceid in range(4):
        side=1 if faceid%2 else -1;front=faceid<2;length=w-.14 if front else d-.14
        for r in range(6):
            z0=.205+(h-.12)*r/6;z1=.205+(h-.12)*(r+1)/6-.009
            proud=.012+rng.uniform(-.002,.002);v=[]
            for outer,z in [(proud,z0),(.004,z1),(0,z1),(0,z0)]:
                for a in [-length/2,length/2]:v.append((a,side*(d/2+outer),z) if front else (side*(w/2+outer),a,z))
            faces=[(0,1,3,2),(2,3,5,4),(6,7,1,0)]
            if (front and side>0) or (not front and side<0):faces=[tuple(reversed(f)) for f in faces]
            additions.append(add_mesh('V2_LappedWallBoard',v,faces,wall))
    # Shallow fieldstone faces sit on the retained original plinth. No footpath
    # or doorstep displacement is introduced.
    for faceid in range(4):
        side=1 if faceid%2 else -1;front=faceid<2;length=w+.10 if front else d+.10;count=4 if front else 3
        for k in range(count):
            a0=-length/2+length*k/count+.012;a1=-length/2+length*(k+1)/count-.012;ztop=.19+rng.uniform(-.017,.003);outer=(d/2+.068 if front else w/2+.068)
            v=[]
            for radial,z in [(outer,.015),(outer,ztop),(outer-.012,ztop)]:
                for a in [a0,a1]:v.append((a,side*radial,z) if front else (side*radial,a,z))
            fs=[(0,1,3,2),(2,3,5,4)]
            if (front and side>0) or (not front and side<0):fs=[tuple(reversed(f)) for f in fs]
            additions.append(add_mesh('V2_FieldstoneFoot',v,fs,mats['Stone_WarmLimestone'] if k%3==0 else mats['Stone_SoftGrey']))
    # Replace the solid chimney lid with a shallow open ring, keeping its exact
    # original bounds. The old chimney body is the recessed floor beneath it.
    cx=w*.25;cy=d*.22;cz=h+rise*.8+.44
    for dx,dy,sx,sy in [(-.175,0,.09,.49),(.175,0,.09,.49),(0,-.195,.26,.10),(0,.195,.26,.10)]:
        additions.append(box('V2_OpenChimneyRim',(cx+dx,cy+dy,cz),(sx,sy,.09),mats['Stone_WarmLimestone']))
    additions.append(add_mesh('V2_ChimneyRecess',[(cx-.13,cy-.145,cz-.042),(cx+.13,cy-.145,cz-.042),(cx+.13,cy+.145,cz-.042),(cx-.13,cy+.145,cz-.042)],[(0,1,2,3)],mats['Wood_DarkBeams']))
    # Join visual details into the existing Structure, preserve the 9-slot order.
    bpy.ops.object.select_all(action='DESELECT');structure.select_set(True)
    for o in additions:o.select_set(True)
    bpy.context.view_layer.objects.active=structure;bpy.ops.object.join()
    # Recalculate only face normals through Blender; original closed shells and
    # open decorative faces coexist, so no watertight-mesh claim is made.
    structure.data.update();uv_report=wood_uv(structure);image=apply_wood_materials()
    for m in [roofmat,highmat]:m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82
    after=interface();b1=bounds(meshes());total=sum(triangles(o) for o in meshes());positions={tuple(v.co) for v in structure.data.vertices}
    checks={'windows_root_markers_exact':after==before,'original_material_slots_exact':[m.name for m in structure.data.materials]==source_materials,
            'bounds_exact_within_1micrometre':all(abs(b0[k][a]-b1[k][a])<.000001 for k in ['min','max'] for a in range(3)),
            'base_walls_door_step_vertices_preserved':all(p in positions for p in protected_positions),
            'added_triangles_le_700':total-row['triangles']<=700,'window_renderer_count_2':len(after['windows'])==2,
            'wood_V_inside_image':uv_report['v_range'][0]>=.039 and uv_report['v_range'][1]<=.961,
            'source_sha_unchanged':sha(path)==row['source_sha256']}
    report={'asset_id':asset,'status':'offline-candidate-awaiting-visual-review','source':str(path.relative_to(ROOT)),'source_sha256':row['source_sha256'],
            'before_triangles':row['triangles'],'after_triangles':total,'additional_triangles':total-row['triangles'],'structure_triangles':triangles(structure),
            'before_bounds':b0,'after_bounds':b1,'before_interface':before,'after_interface':after,'checks':checks,
            'changes':changes,'uv':uv_report,'materials':source_materials,'texture_sha256':sha(TEXTURE),'texture_dimensions':list(image.size),
            'collider_contract':'Original independent Unity SolidCollision BoxCollider and its transform/center/size must remain unchanged. Source door/wall/plinth/step vertices preserved; roof/trim visuals only are edited.',
            'render_views':VIEWS,'render_resolution':[900,900]}
    dump(dest/'manifest.json',report)
    if not all(checks.values()):raise RuntimeError(json.dumps(checks))
    blend=dest/(asset+'_v2_candidate.blend');fbx=dest/(asset+'_v2_candidate.fbx');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},global_scale=1,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_space_transform=False,use_mesh_modifiers=True,
        mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    for kind in ['neutral','night']:render(dest,'after',kind)
    report['files']=[{'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in [blend,fbx]+sorted(dest.glob('*.png'))]
    report['script_sha256']=sha(Path(__file__));dump(dest/'manifest.json',report)
    return report

if __name__=='__main__':
    rows=audit_sources()
    print('VILLAGE_SOURCE_AUDIT_DONE',flush=True)
    if '--audit-only' not in sys.argv:
        chosen=IDS if '--teal-only' not in sys.argv else IDS[:1]
        results=[upgrade(asset,next(r for r in rows if r['asset_id']==asset)) for asset in chosen]
        dump(OUT/'manifest.json',{'status':'offline-candidates-awaiting-visual-review','assets':results,'actual_island_instances':{'cottage_teal':4,'cottage_ochre':4,'cottage_slate':3},
            'added_triangles_11_instances':sum(r['additional_triangles']*(4 if r['asset_id']!='cottage_slate' else 3) for r in results),'script_sha256':sha(Path(__file__))})
        print('VILLAGE_CANDIDATES_DONE',[(r['asset_id'],r['after_triangles']) for r in results],flush=True)
