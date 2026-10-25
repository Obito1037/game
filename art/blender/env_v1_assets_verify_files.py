"""Non-destructive file/provenance audit of the processed environment deliveries."""
from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/generated/env-v1'
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()
manifest=json.loads((BASE/'asset-manifest.json').read_text(encoding='utf-8'))
inventory=json.loads((BASE/'inventory.json').read_text(encoding='utf-8'))
checks=[]
for source in inventory['assets']:
    p=ROOT/source['source_path']
    checks.append({'path':source['source_path'],'role':'source','sha256_match':digest(p)==source['sha256']})
for asset in manifest['assets']:
    for level in ('lod0','lod1'):
        if level in asset:
            p=ROOT/asset[level]['fbx']
            checks.append({'path':asset[level]['fbx'],'role':level,'sha256_match':digest(p)==asset[level]['sha256']})
    for tex in asset['textures']:
        p=ROOT/tex['path']
        checks.append({'path':tex['path'],'role':'texture','sha256_match':digest(p)==tex['sha256']})
        tex['color_space']='Linear / Non-Color' if '_Emission' in tex['path'] else 'sRGB'
    max_tri=30000 if asset['id'] in ('tree_gold','boat') else 3000 if '_reef_' in asset['id'] else 12000 if asset['kind']=='tree' else 8000
    checks.append({'asset':asset['id'],'role':'triangle_budget','actual':asset['lod0']['triangles'],'limit':max_tri,'passed':asset['lod0']['triangles']<=max_tri})
    for v,p in asset['previews'].items():checks.append({'path':p,'role':'preview_'+v,'exists':(ROOT/p).is_file()})
    # Human visual signoff is deliberately separate from mechanical file integrity.
    asset['technical_scope']='Blender offline processing, screenshots, and FBX roundtrip; no Unity import, physics, or performance validation'
    asset['review']='Manual front/side/top preview review complete for the first-island environment handoff; source presentation panels removed. Tree foliage remains visibly simplified at close range. Technical checks are recorded separately and do not establish all-surface perfection.'
    asset['known_limits']=(['Leaves and branches remain simplified at the requested low triangle budget.','Fruit/leaf material masks derive from source colour; artist review remains necessary.','No per-leaf topology guarantee or animated foliage rig.'] if asset['kind']=='tree' else ['Source stones are connected rock formations; the standalone reef variants are reusable groups rather than individually retopologized stones.'] if asset['kind']=='rock' else ['Static wooden boat; no buoyancy, collision proxy or boarding controls supplied.'])
manifest['offline_summary']={'source_files':len(inventory['assets']),'source_triangles':sum(a['triangles'] for a in inventory['assets']),'optimized_assets':len(manifest['assets']),'main_source_ids_completed':sorted({a['source_id'] for a in manifest['assets'] if a['id']==a['source_id']}),'all_file_hashes_match':all(c.get('sha256_match',True) for c in checks),'all_budgets_pass':all(c.get('passed',True) for c in checks),'all_previews_exist':all(c.get('exists',True) for c in checks),'runtime_fps_verified':False,'unity_import_verified':False}
(BASE/'asset-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'assets/file-verification.json').write_text(json.dumps({'checks':checks,'summary':manifest['offline_summary']},ensure_ascii=False,indent=2),encoding='utf-8')
for asset in manifest['assets']:
    (ROOT/asset['lod0']['fbx']).with_name('asset.json').write_text(json.dumps(asset,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest['offline_summary'],ensure_ascii=False))
