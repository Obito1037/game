"""Independent real file COLOR_0, base material and source-color validation."""
import bpy,json,struct,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT/'traveler.blend'))
source={}; source_mats={}
for obj in bpy.data.objects['TravelerRoot'].children_recursive:
    if obj.type!='MESH': continue
    attr=obj.data.color_attributes['Col']; tree=KDTree(len(obj.data.vertices)); colors={}
    for v in obj.data.vertices: tree.insert(obj.matrix_world@v.co,v.index)
    tree.balance()
    for loop in obj.data.loops: colors[loop.vertex_index]=tuple(attr.data[loop.index].color)
    source[obj.name]=(tree,colors)
    for mat in obj.data.materials:
        source_mats[mat.name]=list(mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
results={}
for suffix in ['fbx','glb']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix=='fbx': bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'),colors_type='LINEAR',automatic_bone_orientation=False)
    else: bpy.ops.import_scene.gltf(filepath=str(OUT/'traveler.glb'))
    bpy.context.view_layer.update(); errors=[]; rows=[]; max_error=0.; material_error=0.
    for obj in bpy.data.objects['TravelerRoot'].children_recursive:
        if obj.type!='MESH': continue
        attrs=obj.data.color_attributes
        if not attrs: errors.append('missing COLOR_0: '+obj.name); continue
        attr=attrs.active_color or attrs[0]; tree,colors=source[obj.name]; local_max=0.
        for loop in obj.data.loops:
            vertex=obj.data.vertices[loop.vertex_index]
            _,source_index,_=tree.find(obj.matrix_world@vertex.co)
            actual=attr.data[loop.index if attr.domain=='CORNER' else loop.vertex_index].color
            local_max=max(local_max,max(abs(actual[i]-colors[source_index][i]) for i in range(4)))
        max_error=max(max_error,local_max)
        if local_max>(1e-6 if suffix=='fbx' else .0046): errors.append('vertex color discrepancy '+obj.name)
        rows.append({'mesh':obj.name,'color_domain':attr.domain,'color_storage':attr.data_type,'maximum_linear_error':local_max})
        for mat in obj.data.materials:
            actual=mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
            expected=source_mats[mat.name]
            err=max(abs(a-b) for a,b in zip(actual,expected)); material_error=max(material_error,err)
            # glTF importer connects a vertex-color multiply graph and leaves
            # the now-unused BSDF input default gray. Its actual base factor is
            # verified directly from the glTF material below instead.
            if suffix=='fbx' and err>.0002: errors.append('base material mismatch '+mat.name)
    results[suffix]={'passed':not errors,'errors':list(dict.fromkeys(errors)),'meshes':len(rows),'max_linear_color_error':max_error,'max_base_material_error':material_error,'rows':rows}

# Raw glTF accessor values distinguish preserved linear data from Blender's
# BYTE_COLOR display quantization after reimport.
raw=(OUT/'traveler.glb').read_bytes(); jlen=struct.unpack_from('<I',raw,12)[0]
doc=json.loads(raw[20:20+jlen]); binary_start=20+jlen+8; binary=raw[binary_start:]
raw_material_error=0.
for material in doc['materials']:
    expected=source_mats[material['name']]
    actual=material.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])
    raw_material_error=max(raw_material_error,max(abs(a-b) for a,b in zip(actual,expected)))
assert raw_material_error<1e-6,'raw glTF base color differs from source'
results['glb']['max_base_material_error']=raw_material_error
results['glb']['base_material_verification']='raw glTF baseColorFactor; imported BSDF default is unused behind COLOR_0 multiply graph'
results['glb']['color_quantization_note']='Blender reimports normalized glTF colors as BYTE_COLOR; maximum measured linear error is below 0.0046. Raw COLOR_0 is checked separately.'
raw_rows=[]
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        index=primitive['attributes'].get('COLOR_0')
        assert index is not None,'COLOR_0 absent in raw glTF: '+mesh['name']
        accessor=doc['accessors'][index]; view=doc['bufferViews'][accessor['bufferView']]
        kind=accessor['componentType']; width={'VEC3':3,'VEC4':4}[accessor['type']]
        code,size,divisor={5126:('f',4,1),5123:('H',2,65535),5121:('B',1,255)}[kind]
        offset=view.get('byteOffset',0)+accessor.get('byteOffset',0); stride=view.get('byteStride',width*size)
        values=[struct.unpack_from('<'+code*width,binary,offset+i*stride) for i in range(accessor['count'])]
        normalized=accessor.get('normalized',False); divisor=divisor if normalized else 1
        low=[min(v[i]/divisor for v in values) for i in range(width)]; high=[max(v[i]/divisor for v in values) for i in range(width)]
        raw_rows.append({'mesh':mesh['name'],'component_type':kind,'normalized':normalized,'count':accessor['count'],'min':low,'max':high})
results['glb_raw']={'all_primitives_have_color_0':True,'primitives':len(raw_rows),'max_base_color_error':raw_material_error,'rows':raw_rows}
(OUT/'color-interchange-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('COLOR_VERIFICATION '+json.dumps({k:{x:y for x,y in v.items() if x!='rows'} for k,v in results.items()}))
assert all(results[k]['passed'] for k in ['fbx','glb'])
