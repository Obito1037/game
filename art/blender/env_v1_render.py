"""Render the saved offline scene without rewriting the verified geometry snapshot."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v1';PREVIEW=OUT/'preview'
path=PREVIEW/'island_offline.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
data=json.loads((OUT/'staging/scene-input.json').read_text(encoding='utf8'))
views=[a for a in data['anchors'] if a['kind']=='camera']
if '--' in sys.argv:
    selected=sys.argv[sys.argv.index('--')+1:]
    if selected:views=[a for a in views if a['name'] in selected]
def bv(v):return Vector((v[0],-v[2],v[1]))
scene=bpy.context.scene;cam=scene.camera
cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24
images=[]
for a in views:
    cam.location=bv(a['position']);cam.rotation_euler=bv(a['forward']).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=24/(2*math.tan(math.radians(a['fov'])/2))
    scene.render.filepath=str(PREVIEW/(a['name']+'.png'));bpy.ops.render.render(write_still=True)
    images.append(dict(name=a['name'],width=scene.render.resolution_x,height=scene.render.resolution_y))
    print('OFFLINE_RENDER='+a['name'],flush=True)
report=dict(source='Blender offline assembly, not Unity',unity=False,
            blend_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            missingAssets=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))['missingAssets'],images=images)
(PREVIEW/'status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
