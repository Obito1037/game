"""Record completed offline visual review and verify deliverable provenance."""
from pathlib import Path
import json,hashlib,re,struct
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ids=['cottage_teal','cottage_ochre','cottage_slate'];manifest=read(OUT/'manifest.json');roundtrip=read(OUT/'fbx-roundtrip.json');source=read(OUT/'source-inventory.json')
verification={'fbx_roundtrip_all_pass':roundtrip['all_pass'],'source_blends_unchanged':{},'files_sha_match':{},'all_geometry_contract_checks':{},'image_dimensions':{}}
for asset in ids:
    folder=OUT/asset;m=read(folder/'manifest.json');m['status']='offline-visually-recommended-pending-root-unity-review';m['visual_review']='REVIEW.zh-CN.md';m['fbx_roundtrip']='fbx-roundtrip.json'
    write(folder/'manifest.json',m)
    row=next(r for r in source['assets'] if r['asset_id']==asset)
    verification['source_blends_unchanged'][asset]=sha(ROOT/row['source_blend'])==row['source_sha256']
    verification['all_geometry_contract_checks'][asset]=all(m['checks'].values())
    for f in m['files']:verification['files_sha_match'][f['path']]=sha(ROOT/f['path'])==f['sha256']
    for phase in ['before','after']:
        for light in ['neutral','night']:
            for view in ['front','back']:
                f=folder/f'{phase}-{light}-{view}.png';verification['image_dimensions'][str(f.relative_to(OUT))]=list(struct.unpack('>II',f.read_bytes()[16:24]))
manifest['assets']=[read(OUT/a/'manifest.json') for a in ids];manifest['status']='offline-visually-recommended-pending-root-unity-review';manifest['visual_review']='REVIEW.zh-CN.md';manifest['fbx_roundtrip']='fbx-roundtrip.json';write(OUT/'manifest.json',manifest)
verification['source_manifest_unchanged']=sha(ROOT/'art/generated/env-v1/props/manifest.json')==source['source_manifest_sha256']
verification['original_texture_unchanged']=sha(ROOT/source['texture']['path'])==source['texture']['sha256']
verification['gallery_missing_local_links']=[s for s in re.findall(r'(?:href|src)="([^"]+)"',(OUT/'REVIEW.html').read_text(encoding='utf-8')) if not (OUT/s).exists()]
write(OUT/'final-verification.json',verification)
write(OUT/'decision.json',{'status':'recommended-for-root-candidate-review-not-production-approved','unity_operated':False,'assets_written':False,
    'source_assets_modified':False,'automatic_candidate_builder_integration':False,'visual_review':'REVIEW.zh-CN.md',
    'reason':'三款均出现可见的顺纹木材、曲瓦层次、完整窗框和干净石脚/门楣；同机位中性/夜景对照明确改善。背景屋预算适中，保留所有原窗和门接口。',
    'limitations':['Unity合批、材料高光、相机/角色碰撞和性能尚未验证。','瓦石仍为颜色材质；烟囱浅开口；新增瓦片省略被原屋面遮挡的底面。'],
    'additional_triangles_per_asset':454,'additional_triangles_11_instances':4994})
print('VILLAGE_FINAL_VERIFICATION',json.dumps({'roundtrip':verification['fbx_roundtrip_all_pass'],'sources':all(verification['source_blends_unchanged'].values()),'files':all(verification['files_sha_match'].values()),'geometry':all(verification['all_geometry_contract_checks'].values()),'png_count':len(verification['image_dimensions']),'all_png_900':all(x==[900,900] for x in verification['image_dimensions'].values()),'missing_links':verification['gallery_missing_local_links']}))
