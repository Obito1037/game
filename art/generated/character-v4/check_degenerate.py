import bpy, json
from pathlib import Path
OUT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'traveler.fbx'))
rows=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH': continue
    o.data.calc_loop_triangles()
    bad=[{'vertices':list(t.vertices),'area':t.area,'points':[list(o.data.vertices[i].co) for i in t.vertices]} for t in o.data.loop_triangles if t.area<1e-16]
    if bad: rows.append({'name':o.name,'degenerates':bad})
(OUT/'degenerate-diagnostics.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
