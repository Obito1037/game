"""Integrity and budget verification for the offline handoff, without Unity."""
import json, hashlib, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art/generated/env-v1'
checks=[]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def check(name,passed,detail=''):checks.append(dict(name=name,passed=bool(passed),detail=detail))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
inventory=read(OUT/'inventory.json')
check('nine_original_sources',len(inventory['assets'])==9)
for a in inventory['assets']:
    check('original_hash:'+a['id'],sha(ROOT/a['source_path'])==a['sha256'])
    check('three_source_views:'+a['id'],len(a['previews'])==3 and all((ROOT/p).exists() for p in a['previews'].values()))
natural=read(OUT/'asset-manifest.json')
for a in natural['assets']:
    limit=3000 if '_reef_' in a['id'] else (30000 if a['id'] in ['tree_gold','boat'] else 12000 if a['kind']=='tree' else 8000)
    check('triangles:'+a['id'],a['lod0']['triangles']<=limit,f"{a['lod0']['triangles']} <= {limit}")
    for level in ['lod0','lod1']:
        if level in a:
            check('fbx_hash:'+a['id']+':'+level,sha(ROOT/a[level]['fbx'])==a[level]['sha256'])
    if a['kind'] in ['tree','rock'] and '_reef_' not in a['id']:
        ratio=a.get('lod1',{}).get('triangles',0)/max(1,a['lod0']['triangles'])
        check('lod_ratio:'+a['id'],.30<=ratio<=.48,f'{ratio:.4f}')
    for t in a['textures']:
        limit=2048 if a['id'] in ['tree_gold','boat'] else 1024
        check('texture_size:'+a['id']+':'+Path(t['path']).name,max(t['width'],t['height'])<=limit)
        check('texture_hash:'+a['id']+':'+Path(t['path']).name,sha(ROOT/t['path'])==t['sha256'])
props=read(OUT/'props/manifest.json')
check('sixteen_props',len(props['assets'])==16)
check('props_roundtrip_verified',read(OUT/'props/verification.json')['status']=='passed')
for a in props['assets']:check('prop_hash:'+a['asset_id'],sha(ROOT/a['fbx'])==a['fbx_sha256'])
data=read(OUT/'staging/scene-input.json');manifest=read(OUT/'manifest.json')
check('all_instances_have_models',not manifest['missingAssets'],manifest['missingAssets'])
check('eleven_houses',sum(i['group']=='Village' for i in data['instances'])==11)
check('exactly_three_lamps',sum(a['kind']=='lamp' for a in data['anchors'])==3)
check('budget_with_allowance_for_sky',manifest['allLODInstanceTriangles']+5000<=600000,manifest['allLODInstanceTriangles'])
pts=[(p['position'][0],p['position'][2]) for p in data['boundary']]
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
crossings=[]
for i in range(len(pts)):
    a,b=pts[i],pts[(i+1)%len(pts)]
    for j in range(i+2,len(pts)):
        if i==0 and j==len(pts)-1:continue
        c,d=pts[j],pts[(j+1)%len(pts)]
        if cross(a,b,c)*cross(a,b,d)<-1e-9 and cross(c,d,a)*cross(c,d,b)<-1e-9:crossings.append([i,j])
check('land_boundary_no_self_crossing',not crossings,crossings)
for chapter,beams in read(OUT/'puzzle-light-layout.json')['chapterStates'].items():
    for beam in beams:check('beam_centres:'+chapter+':'+beam['anchor'],beam['smallestCentrelineMarginDegrees']>=1,beam['smallestCentrelineMarginDegrees'])
for m in data['models']:
    for key in ['path','lod1']:
        p=m.get(key)
        if p:
            prefix='Assets/JieGuang/Environment/'
            check('staged_model:'+m['id']+':'+key,p.startswith(prefix) and '..' not in p and (OUT/'staging'/p[len(prefix):]).is_file())
for a in data['anchors']:
    check('finite_anchor:'+a['name'],all(math.isfinite(v) for v in a['position']+a['forward']))
report=dict(status='passed-offline-integrity' if all(c['passed'] for c in checks) else 'failed-offline-integrity',
            scope='Source and output hashes, manifest budgets and staging completeness. Triangle values come from Blender manifests; this is not an independent Unity import or FPS check.',
            checks=checks,failed=[c for c in checks if not c['passed']],unity='Separate Unity evidence: art/verification/env-v1/validation.json; this script checks offline assets only.')
(OUT/'package-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],checks=len(checks),failed=report['failed']),ensure_ascii=True))
raise SystemExit(0 if not report['failed'] else 1)
