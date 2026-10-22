const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),verification=path.join(root,'art/verification');
const read=file=>JSON.parse(fs.readFileSync(path.join(root,file),'utf8').replace(/^\uFEFF/,''));
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex').toUpperCase();
const write=(file,value)=>fs.writeFileSync(path.join(root,file),JSON.stringify(value,null,2)+'\n');
const pkg=read('art/verification/v11-package-verification.json'),http=read('art/verification/v11-release-http-verification.json');
const page=read('art/verification/v11-review-page-verification.json');
assert(pkg.passed&&http.passed&&page.passed,'Package, HTTP and review-page verification must pass');
assert.equal(hash('art/verification/visual-review.html'),hash('art/verification/visual-review-v11.html'),'Current review page differs from verified version');
const manifest=read('art/production-manifest.json'),checks=read('art/verification/release-checks.json');
assert.equal(manifest.revision,'v11');assert.equal(checks.revision,'v11');
const launch=read('art/verification/run-029-v11/build-evidence.json');
const identity=launch.files.map(file=>({name:file.name,qaSHA256:file.sha256,candidateSHA256:hash('builds/candidates/v11/windows/'+file.name),releaseSHA256:hash('builds/windows/'+file.name)}));
assert(identity.every(x=>x.qaSHA256===x.candidateSHA256&&x.candidateSHA256===x.releaseSHA256),'Native release differs from tested candidate');
const sourceFiles=read('art/verification/v10-release-source/source-files.json').map(x=>({source:x.source,sha256:hash(x.source),unchangedFromV10:hash(x.source)===x.sha256}));
assert(sourceFiles.every(x=>x.unchangedFromV10),'Unexpected game code/shader/material-settings change');
const handoffSources=['AGENTS.md','PLAY.zh-CN.txt','CONCEPT-48H.zh-CN.txt','SUBMISSION-演示与材料.zh-CN.txt','Open-Borrowed-Light-Fullscreen.cmd','tools/package-templates/Play-Fullscreen.cmd','AI-使用与素材来源.zh-CN.txt','setup/NEXT-STEPS.zh-CN.txt','art/production-manifest.json','art/verification/release-checks.json',
 'tools/run-game-qa.ps1','tools/snapshot-island-import.cs','tools/compare-island-import.cjs','tools/compare-material-study-conditions.cjs',
 'tools/prepare-v11-plant-review.cjs','tools/prepare-v11-main-review.cjs','tools/prepare-v11-handoff.cjs','tools/verify-visual-review.cjs',
 'tools/record-game-builds.cjs','tools/verify-candidate-artifacts.cjs','tools/verify-game-web.cjs','tools/verify-game-release-http.cjs',
 'tools/promote-v11-local.ps1','tools/finalize-v11-local.cjs','art/blender/build_island_v8.py','art/generated/world-v8/verify_world_v8.py'];
assert(handoffSources.every(p=>fs.existsSync(path.join(root,p))),'Missing source snapshot input');
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx'),manifest.geometry.worldFbxSHA256);
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx'),manifest.geometry.travelerFbxSHA256);
const archive='builds/archive/BorrowedLight-v11-Windows.zip';
assert(!fs.existsSync(path.join(root,archive)),'v11 archive exists; inspect before retrying');
assert.equal(hash('builds/BorrowedLight-Windows.zip'),pkg.zipSHA256);
fs.copyFileSync(path.join(root,'builds/BorrowedLight-Windows.zip'),path.join(root,archive));assert.equal(hash(archive),pkg.zipSHA256);
Object.assign(checks,{stagingOnly:false,releaseReady:true,status:'Promoted locally after scoped plant review, native/Web QA and package/HTTP checks. Overall aesthetic objective remains unachieved.',
 packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,visualReviewPageVerification:'art/verification/v11-review-page-verification.json',
 packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,nativeCandidateIdentity:identity,
 gameSourcesUnchangedFromV10:true,nativeDisplayComparison:'art/verification/v11-native-display-comparison.json',webCurrentHostComparison:'art/verification/v11-web-current-host-comparison.json',
 previousStableWebArchivePresent:fs.existsSync(path.join(root,'builds/archive/BorrowedLight-v10-Web')),finalizedAtUTC:new Date().toISOString()});
write('art/verification/release-checks.json',checks);write('art/verification/v11-release-checks.json',checks);
Object.assign(manifest.delivery,{stagingOnly:false,packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,
 packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,currentWindowsArchive:'../'+archive,
 previousStableWebArchivePresent:checks.previousStableWebArchivePresent});
manifest.verification.currentVisualReview='verification/visual-review-v11.html';
manifest.verification.webCurrentHostComparison='verification/v11-web-current-host-comparison.json';
manifest.aestheticObjectiveAchieved=false;write('art/production-manifest.json',manifest);
const world=read('art/generated/world-v8/asset-manifest.json');
world.verification_pending=false;delete world.visual_review_pending;
world.adoption={game:'v11',status:'Adopted after format/preservation checks, fixed-camera review and integrated Windows/Web QA.',
 nativeQA:'../../verification/run-029-v11/runtime-results.json',webQA:'../../verification/web-012-v11/runtime-results.json',
 fixedReview:'../../verification/v11-plants-candidate/decision.json',dynamicLimit:'No exhaustive dynamic foliage or all-angle visual acceptance.',aestheticObjectiveAchieved:false};
write('art/generated/world-v8/asset-manifest.json',world);
const agentsFile=path.join(root,'AGENTS.md');let agents=fs.readFileSync(agentsFile,'utf8');
agents=agents.replace(/^- Borrowed Light v10 is built.*$/m,'- Borrowed Light v11 is built for Windows x64 and WebGL. Final native QA: `art/verification/run-029-v11/`; normal browser QA: `art/verification/web-012-v11/`. Native final samples used 1440x900 fullscreen; prior v11 runs include concurrent-load and resized-window limitations. Launchers: `Open-Borrowed-Light-Fullscreen.cmd`, `Open-Borrowed-Light.cmd`, and `Open-Borrowed-Light-Web.cmd`; localhost only. Overall visual superiority over the reference is not yet established.');
agents=agents.replace(/^- Game revision v10 uses.*$/m,'- Game revision v11 uses frozen `art/generated/world-v8/` (510293 triangles), `art/generated/character-v9/`, and stone-v10. Keep world-v7/world-v6 and character-v5/v6/v7/v8 dependencies. Only lavender and ferns changed in world-v8; 27 other meshes, 14 anchors, materials and textures pass same-format BLEND/FBX/GLB and Unity preservation checks. Prior character GLB endpoint limitations remain. v10 Windows/Web artifacts are archived.');
agents=agents.replace(/^- v10 retains face fill.*$/m,'- v11 retains v10 game code, shaders, materials, lights and character. The new plant shapes pass fixed path/roots/lamp review; finer purple flowers are less prominent at distance. Grass distribution and ground transitions remain unfinished. See `art/verification/visual-review.html`; the v10 gait video is historical, not a new v11 dynamic review.');
agents+='\n- `tools/run-game-qa.ps1 -Fullscreen` requests 1440x900 fullscreen for comparable native captures. Record actual PNG sizes; a requested size alone does not establish rendering conditions. v11 source/evidence snapshots are in `art/verification/v11-release-source/`.\n';
fs.writeFileSync(agentsFile,agents);
const snapshot=path.join(verification,'v11-release-source');fs.mkdirSync(snapshot,{recursive:true});
for(const x of sourceFiles)fs.copyFileSync(path.join(root,x.source),path.join(snapshot,path.basename(x.source)));
write('art/verification/v11-release-source/source-files.json',sourceFiles);
for(const source of handoffSources)fs.copyFileSync(path.join(root,source),path.join(snapshot,path.basename(source)));
write('art/verification/v11-release-source/handoff-files.json',handoffSources.map(source=>({source,sha256:hash(source)})));
write('art/verification/v11-work-in-progress.json',{revision:'v11',status:'Promoted locally after plant review, native/Web QA and package/HTTP verification.',aestheticObjectiveAchieved:false,releaseChecks:'v11-release-checks.json',nextArtPriority:'Grass clumps and ground transitions'});
console.log(JSON.stringify({revision:'v11',packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,archived:true,gameSourcesUnchangedFromV10:true}));
