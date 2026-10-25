"""Read-only Blender FBX triangle audit; writes reports only beside this script."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import bpy

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ASSETS = ROOT / 'GameProject/Assets/JieGuang'
source = (ASSETS / 'World/IslandV2.prefab').read_text(encoding='utf-8-sig')
instances = Counter(re.findall(r'm_SourcePrefab: \{fileID: \d+, guid: ([0-9a-f]+)', source))
guid_paths = {}
for path in ASSETS.rglob('*.prefab.meta'):
    guid = re.search(r'^guid: (\w+)', path.read_text(encoding='utf-8-sig'), re.M)
    if guid:
        guid_paths[guid.group(1)] = path.with_suffix('')
placed = Counter()
fbx_guid_paths = {}
for path in (ASSETS / 'Props').glob('*/*.fbx.meta'):
    guid = re.search(r'^guid: (\w+)', path.read_text(encoding='utf-8-sig'), re.M)
    if guid:
        fbx_guid_paths[guid.group(1)] = path.with_suffix('')
for guid, count in instances.items():
    path = guid_paths.get(guid)
    if path and ('Props' in path.parts):
        # Resolve the actual mesh dependency; A01 now selects an opened-window derivative.
        prefab_text = path.read_text(encoding='utf-8-sig')
        mesh_guids = [g for g in re.findall(r'm_SourcePrefab: \{fileID: -?\d+, guid: ([0-9a-f]+)', prefab_text) if g in fbx_guid_paths]
        if not mesh_guids:
            mesh_guids = re.findall(r'm_Mesh: \{fileID: -?\d+, guid: ([0-9a-f]+)', prefab_text)
        for mesh_guid in mesh_guids:
            mesh_path = fbx_guid_paths.get(mesh_guid)
            if mesh_path:
                placed[mesh_path.stem] += count

rows = []
for path in sorted((ASSETS / 'Props').glob('*/*.fbx')):
    aid = path.stem
    recpath = ROOT / 'art/generated/props-v2' / aid / 'record.json'
    rec = json.loads(recpath.read_text(encoding='utf-8')) if recpath.exists() else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    triangles = vertices = meshes = material_slots = 0
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            ob.data.calc_loop_triangles()
            triangles += len(ob.data.loop_triangles)
            vertices += len(ob.data.vertices)
            meshes += 1
            material_slots += len(ob.data.materials)
    generated = ROOT / 'art/generated/props-v2' / aid / path.name
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    original_matches = generated.exists() and sha == hashlib.sha256(generated.read_bytes()).hexdigest()
    row = dict(id=aid, imported_fbx=str(path.relative_to(ROOT)), triangles=triangles,
               vertices=vertices, meshes=meshes, material_slots=material_slots,
               record_triangles=rec['tris_after'] if rec else None, record_matches=triangles == rec['tris_after'] if rec else None,
               generated_fbx_matches=original_matches if generated.exists() else None, sha256=sha,
               static_instances=placed[aid], static_triangles=triangles * placed[aid])
    rows.append(row)
    print('AUDIT', aid, triangles, 'x', placed[aid], flush=True)

rows.sort(key=lambda r: r['static_triangles'], reverse=True)
report = dict(scope='Read-only FBX import + nested prefab instance count. No Unity Editor operations.',
              limitations='Static IslandV2 instances only; excludes runtime props/characters/terrain/old environment meshes and all extra shadow/depth passes. This is not measured triangles per frame.',
              fbx_asset_count=len(rows), static_instance_count=sum(r['static_instances'] for r in rows),
              unique_triangles=sum(r['triangles'] for r in rows), static_triangles=sum(r['static_triangles'] for r in rows),
              all_available_record_counts_match=all(r['record_matches'] for r in rows if r['record_matches'] is not None),
              all_available_generated_fbx_copies_match=all(r['generated_fbx_matches'] for r in rows if r['generated_fbx_matches'] is not None), rows=rows)
(OUT / 'prop-budget-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('SUMMARY', json.dumps({k: v for k, v in report.items() if k != 'rows'}), flush=True)
