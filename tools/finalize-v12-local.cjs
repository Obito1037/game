'use strict';
// Run only after local promotion, ZIP/HTTP checks and the static review-page check.
// --check-only evaluates every prerequisite without writing or archiving anything.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
assert(args.every(x => x === '--check-only') && args.length <= 1, 'Only --check-only is supported');
const checkOnly = args.includes('--check-only');
function local(file) {
  assert(typeof file === 'string' && file.length > 0, 'Empty path');
  const full = path.resolve(root, file), rel = path.relative(root, full);
  assert(rel && !path.isAbsolute(rel) && rel !== '..' && !rel.startsWith('..' + path.sep), 'Path outside workspace: ' + file);
  for (let cursor = full; cursor.length >= root.length; cursor = path.dirname(cursor)) {
    if (fs.existsSync(cursor)) assert(!fs.lstatSync(cursor).isSymbolicLink(), 'Reparse/symlink path refused: ' + cursor);
    if (cursor === root) break;
  }
  return full;
}
function child(directory, name) {
  assert(typeof name === 'string' && name && !path.isAbsolute(name) && !name.includes(':') && !name.split(/[\\/]/).some(x => x === '.' || x === '..'), 'Invalid child name');
  const base = local(directory), full = local(path.join(base, name));
  assert(full.startsWith(base + path.sep), 'Child escaped directory');
  return full;
}
const readText = file => fs.readFileSync(local(file), 'utf8').replace(/^\uFEFF/, '');
const read = file => JSON.parse(readText(file));
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(local(file))).digest('hex').toUpperCase();
const validHash = value => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
const sameHash = (a, b) => validHash(a) && validHash(b) && a.toUpperCase() === b.toUpperCase();
const assertHash = (file, expected) => assert(sameHash(hash(file), expected), 'Hash mismatch: ' + file);
const write = (file, value) => fs.writeFileSync(local(file), typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n');
const exists = file => fs.existsSync(local(file));
const jsonEqual = (a, b) => assert.deepEqual(a, b);
const draft = 'art/verification/v12-release-draft';
const manifest = read('art/production-manifest.json'), checks = read('art/verification/release-checks.json');
const draftManifest = read(draft + '/production-manifest.json'), draftChecks = read(draft + '/release-checks.json');
const promotion = read('art/verification/v12-promotion.json');
assert.equal(manifest.revision, 'v12'); assert.equal(checks.revision, 'v12');
assert(promotion.passed === true && promotion.revision === 'v12' && promotion.previousRevision === 'v11' && promotion.candidateCopiesPreserved === true, 'Promotion record incomplete');
jsonEqual(promotion.buildIds, manifest.buildIds);
assertHash('art/production-manifest.json', promotion.draftSHA256['production-manifest.json']);
assertHash('art/verification/release-checks.json', promotion.draftSHA256['release-checks.json']);
for (const [name, digest] of Object.entries(promotion.draftSHA256)) assertHash(child(draft, name), digest);
assert(checks.windowsFunctionalPassed === true && checks.webFunctionalPassed === true && checks.buildIds.windows === manifest.buildIds.windows && checks.buildIds.web === manifest.buildIds.web, 'Draft acceptance/build IDs differ');
const nativeRun = checks.nativeRun;
assert(typeof nativeRun === 'string' && /^run-\d+-v12$/.test(nativeRun), 'Invalid native QA session');
assert.equal(promotion.nativeRun, nativeRun);
assert.equal(checks.evidence.native, `art/verification/${nativeRun}/runtime-results.json`);
assert.equal(checks.evidence.nativeIdentity, `art/verification/${nativeRun}/build-evidence.json`);
assert.equal(checks.evidence.web, 'art/verification/web-013-v12/runtime-results.json');

const pkg = read('art/verification/v12-package-verification.json');
const http = read('art/verification/v12-release-http-verification.json');
const page = read('art/verification/v12-review-page-verification.json');
assert(pkg.passed === true && pkg.requiredFilesPresent === true && pkg.debugFoldersExcluded === true && pkg.allZipFileHashesMatchCurrentBuild === true && pkg.zipFilesHashCompared === pkg.expectedPlayerFiles && pkg.expectedPlayerFiles > 0 && Array.isArray(pkg.failures) && pkg.failures.length === 0, 'ZIP verification incomplete');
assertHash('builds/BorrowedLight-Windows.zip', pkg.zipSHA256);
assert.equal(fs.statSync(local('builds/BorrowedLight-Windows.zip')).size, pkg.zipBytes);
assertHash('builds/windows/BorrowedLight_Data/resources.assets', pkg.nativeResourcesSHA256);
assertHash('builds/windows/BorrowedLight_Data/Managed/Assembly-CSharp.dll', pkg.nativeGameAssemblySHA256);
assert(http.passed === true && http.revision === 'v12' && http.indexReferencesCurrentFiles === true && local(http.root) === local('builds/web'), 'Current HTTP verification incomplete');
assert.equal(new URL(http.server).hostname, '127.0.0.1', 'Release must remain local');
assert(page.passed === true && page.page === 'visual-review-v12.html' && Array.isArray(page.errors) && page.errors.length === 0 && Array.isArray(page.missingLocalLinks) && page.missingLocalLinks.length === 0, 'Review page has not passed');
assertHash('art/verification/visual-review.html', promotion.draftSHA256['visual-review.html']);
assertHash('art/verification/visual-review-v12.html', promotion.draftSHA256['visual-review.html']);
if (page.sha256) assertHash('art/verification/visual-review-v12.html', page.sha256);
if (page.pageSHA256) assertHash('art/verification/visual-review-v12.html', page.pageSHA256);

const native = read(checks.evidence.native), web = read(checks.evidence.web);
for (const key of ['puzzleCompleted','menuKeyboardStart','pauseStopsMovement','resumeMovement','restartWorks','endingReturnWorks','cabinCollisionWorks','walkwayGroundingWorks','boulderCollisionWorks','observatoryGroundingWorks','observatoryInstrumentCollisionWorks','decorativeLeavesExcluded','pierGroundingWorks','pierRailCollisionWorks','scrollZoomWorks']) assert.equal(native[key], true, 'Native QA: ' + key);
for (const key of ['passed','realKeyboardPuzzleCompletion','persistedProgressReload','crossOriginIsolated','audioContextResumeObserved','defaultBrowserAutoplayPolicy']) assert.equal(web[key], true, 'Web QA: ' + key);
assert(Array.isArray(web.errors) && web.errors.length === 0, 'Web errors present');
const launch = read(checks.evidence.nativeIdentity);
assert.equal(launch.buildId, manifest.buildIds.windows);
assert.equal(launch.mode, 'Tour');
assert.equal(local(launch.playerDirectory), local('builds/candidates/v12/windows'));
const nativeNames = ['BorrowedLight.exe','UnityPlayer.dll','BorrowedLight_Data/resources.assets','BorrowedLight_Data/Managed/Assembly-CSharp.dll'];
assert.deepEqual(launch.files.map(x => x.name.replace(/\\/g, '/')).sort(), [...nativeNames].sort());
const nativeIdentity = launch.files.map(file => {
  const candidateSHA256 = hash(child('builds/candidates/v12/windows', file.name));
  const releaseSHA256 = hash(child('builds/windows', file.name));
  assert(sameHash(file.sha256, candidateSHA256) && sameHash(candidateSHA256, releaseSHA256), 'Native candidate/release differs from QA');
  return {name:file.name, qaSHA256:file.sha256, candidateSHA256, releaseSHA256};
});
const webIdentity = read('art/verification/web-013-v12/artifact-identity.json');
assert(webIdentity.passed === true && webIdentity.declaredBuildMatches === true && webIdentity.requestedAllCurrentFiles === true && webIdentity.buildId === manifest.buildIds.web && webIdentity.session === 'web-013-v12', 'Web QA identity differs');
const payloadNames = manifest.webPayload.files.map(f => f.name);
assert(payloadNames.length === 4 && new Set(payloadNames).size === 4);
assert.deepEqual(webIdentity.files.map(f => f.name).sort(), [...payloadNames].sort());
assert.deepEqual(http.files.map(f => f.name).sort(), [...payloadNames].sort());
let payloadBytes = 0;
for (const file of manifest.webPayload.files) {
  assert(path.basename(file.name) === file.name && !/[\\/:]/.test(file.name), 'Payload must be a basename');
  for (const dir of ['builds/candidates/v12/web/Build','builds/web/Build']) {
    assertHash(child(dir, file.name), file.sha256);
    assert.equal(fs.statSync(child(dir, file.name)).size, file.bytes);
  }
  for (const report of [webIdentity, http]) {
    const item = report.files.find(x => x.name === file.name);
    assert(item.matches === true && item.bytes === file.bytes && sameHash(item.diskSHA256, file.sha256) && sameHash(item.httpSHA256, file.sha256), 'Web evidence byte mismatch');
  }
  payloadBytes += file.bytes;
}
assert.equal(payloadBytes, manifest.webPayload.bytes);

// The old v11 snapshot tracked only 16 files. Preserve that distinction instead
// of treating an incompletely baselined source tree as proven unchanged.
const audit = draftManifest.sourceAudit;
jsonEqual(audit, draftChecks.sourceAudit); jsonEqual(audit, manifest.sourceAudit); jsonEqual(audit, checks.sourceAudit);
assert(audit && audit.allChangesWithinScope === true && audit.baseline === 'art/verification/v11-release-source/source-files.json', 'Missing source audit');
const prefix = 'GameProject/Assets/BorrowedLight/';
const allowedChanged = [prefix + 'Runtime/WorldDirector.cs'];
const allowedAdded = ['Runtime/GroundDetailStudy.cs','Runtime/GroundDetailStudy.cs.meta','Shaders/GroundDetail.shader','Shaders/GroundDetail.shader.meta','Resources/Textures/GroundDetailV12.png','Resources/Textures/GroundDetailV12.png.meta','Resources/Materials/GroundDetailV12.mat','Resources/Materials/GroundDetailV12.mat.meta'].map(x => prefix + x);
const inventoryRoots = ['Runtime','Shaders','Resources/Materials','Resources/Textures'].map(x => prefix + x);
const inventoryExtensions = ['.cs','.shader','.hlsl','.mat','.png','.meta'];
const sorted = list => [...list].sort();
jsonEqual(sorted(audit.allowedChangedExisting), sorted(allowedChanged)); jsonEqual(sorted(audit.allowedAdded), sorted(allowedAdded));
jsonEqual(sorted(audit.inventoryRoots), sorted(inventoryRoots)); jsonEqual(sorted(audit.inventoryExtensions), sorted(inventoryExtensions));
const baseline = read(audit.baseline);
assert(Array.isArray(baseline) && baseline.length === 16, 'Unexpected v11 tracked source inventory');
const baselineMap = new Map(baseline.map(item => [item.source, item.sha256]));
assert.equal(baselineMap.size, baseline.length, 'Duplicate baseline paths');
const extra = baseline.map(item => item.source).filter(file => !inventoryRoots.some(dir => file.startsWith(dir + '/')));
jsonEqual(sorted(audit.inventoryExtraFiles), sorted(extra));
const inventory = new Set(extra);
function scan(directory) {
  for (const entry of fs.readdirSync(local(directory), {withFileTypes:true})) {
    const file = directory + '/' + entry.name;
    assert(!entry.isSymbolicLink(), 'Symlink in source inventory: ' + file);
    if (entry.isDirectory()) scan(file);
    else if (entry.isFile() && inventoryExtensions.includes(path.extname(entry.name).toLowerCase())) inventory.add(file);
  }
}
for (const dir of inventoryRoots) scan(dir);
jsonEqual(sorted(audit.inventoryFiles), sorted(inventory));
assert(new Set(audit.files.map(item => item.source)).size === audit.files.length, 'Duplicate source audit paths');
jsonEqual(sorted(audit.files.map(item => item.source)), sorted(inventory));
const sourceFiles = audit.files.map(item => {
  assert(item.allowed === true, 'Source not allowed: ' + item.source);
  assertHash(item.source, item.sha256);
  const previous = baselineMap.get(item.source);
  if (previous) {
    assert(sameHash(item.baselineSHA256, previous), 'v11 baseline hash rewritten');
    const changed = !sameHash(previous, item.sha256);
    assert.equal(item.status, changed ? 'modified' : 'unchanged');
    assert(!changed || allowedChanged.includes(item.source), 'Unexpected tracked source modification');
  } else {
    assert.equal(item.baselineSHA256, null, 'Untracked file falsely claims a v11 hash');
    assert.equal(item.status, allowedAdded.includes(item.source) ? 'added' : 'unbaselined-existing');
  }
  return {source:item.source, sha256:hash(item.source), baselineSHA256:item.baselineSHA256, status:item.status, snapshot:'files/' + item.source};
});
for (const file of [...baselineMap.keys(), ...allowedAdded]) assert(inventory.has(file), 'Missing baseline/allowed-addition file: ' + file);

assertHash('GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx', manifest.geometry.worldFbxSHA256);
assertHash('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx', manifest.geometry.travelerFbxSHA256);
const world = read('art/generated/world-v10/asset-manifest.json');
const interchange = read('art/generated/world-v10/interchange-verification.json');
assert(world.revision === 'world-v10' && world.triangles === 505782 && interchange.passed === true, 'Unexpected world or incomplete readback');
assert(sameHash(world.sha256['island.fbx'], manifest.geometry.worldFbxSHA256));
for (const [name, digest] of Object.entries(world.sha256)) assertHash(child('art/generated/world-v10', name), digest);
const ground = read('art/generated/ground-v12/manifest.json');
assert.equal(ground.detailStrength, 0.35); assert.equal(ground.intendedTileMetres, 1.8);
assertHash('art/generated/ground-v12/earth-detail-original.png', ground.sha256);
assertHash(prefix + 'Resources/Textures/GroundDetailV12.png', ground.sha256);
assertHash('builds/archive/BorrowedLight-v11-Windows.zip', 'CD823F949941B85101DFE71A5429837D23A0173DEC1807AB1BA1919229566B15');
assert(exists('builds/archive/BorrowedLight-v11-Web') && exists('builds/candidates/v11-windows-previous') && exists('builds/candidates/v11-web-previous'), 'Prior release preservation missing');

const handoffSources = ['AGENTS.md','PLAY.zh-CN.txt','CONCEPT-48H.zh-CN.txt','SUBMISSION-演示与材料.zh-CN.txt','AI-使用与素材来源.zh-CN.txt','setup/NEXT-STEPS.zh-CN.txt','Open-Borrowed-Light.cmd','Open-Borrowed-Light-Web.cmd','Open-Borrowed-Light-Fullscreen.cmd','tools/package-templates/Play-Fullscreen.cmd','art/production-manifest.json','art/verification/release-checks.json','art/verification/visual-review-v12.html',
  'tools/run-game-qa.ps1','tools/snapshot-island-import.cs','tools/compare-island-import.cjs','tools/compare-material-study-conditions.cjs','tools/prepare-v12-handoff.cjs','tools/prepare-v12-grass-review.cjs','tools/prepare-v12-ground-review.cjs','tools/verify-visual-review.cjs','tools/record-game-builds.cjs','tools/verify-candidate-artifacts.cjs','tools/verify-game-web.cjs','tools/verify-game-release-http.cjs','tools/promote-v12-local.ps1','tools/finalize-v12-local.cjs','tools/setup-ground-detail-v12.cs','art/blender/build_island_v10.py','art/generated/world-v10/verify_world_v10.py','art/generated/world-v10/asset-manifest.json','art/generated/world-v10/IMPORT-NOTES.zh-CN.txt','art/generated/ground-v12/manifest.json','art/generated/ground-v12/prompt.txt'];
for (const optional of ['tools/prepare-v12-review.cjs','tools/prepare-v12-main-review.cjs']) if (exists(optional)) handoffSources.push(optional);
for (const file of ['tools/compare-ground-study-conditions.cjs','tools/snapshot-ground-detail-import.cs','art/verification/v12-native-display-comparison.json','art/verification/v12-web-performance-context.json']) handoffSources.push(file);
for (const file of handoffSources) assert(fs.statSync(local(file)).isFile(), 'Missing snapshot input: ' + file);
const archive = 'builds/archive/BorrowedLight-v12-Windows.zip', snapshot = 'art/verification/v12-release-source';
for (const destination of [archive, snapshot, 'art/verification/v12-release-checks.json','art/verification/v12-finalization.json']) assert(!exists(destination), 'Historical destination already exists; inspect before retry: ' + destination);
let agents = readText('AGENTS.md');
function replaceAgentLine(pattern, replacement) {
  assert.equal((agents.match(new RegExp(pattern.source, 'gm')) || []).length, 1, 'AGENTS release marker missing/ambiguous');
  agents = agents.replace(pattern, replacement);
}
replaceAgentLine(/^- Borrowed Light v11 is built.*$/m, '- Borrowed Light v12 is built for Windows x64 and WebGL. Final native QA: `art/verification/'+nativeRun+'/`; normal browser QA: `art/verification/web-013-v12/`. Launchers remain local; no public deployment. Short performance samples and fixed visual studies are limited evidence, not a claim of overall superiority over the reference.');
replaceAgentLine(/^- Game revision v11 uses.*$/m, '- Game revision v12 uses frozen `art/generated/world-v10/` (505782 triangles), `art/generated/character-v9/`, stone-v10 and ground-v12. Keep world-v8/world-v7/world-v6 and character-v5/v6/v7/v8 dependencies. The grass candidate preserves 27 non-target meshes, 14 anchors and original world textures/materials; the separate ground shader/resource addition is intentional. Prior v11 Windows/Web releases are archived.');
replaceAgentLine(/^- v11 retains v10 game code.*$/m, '- v12 refines two grass meshes and adds a normalized ground albedo layer at strength 0.35 / tile 1.8 m, retaining the original Meadow map/normal. WorldDirector remapping and the GroundDetail diagnostic/shader/resources intentionally changed; other tracked v11 sources pass the explicit source audit. Unbaselined existing files are recorded honestly. Fixed path/roots/lamp reviews are limited; historical v10 gait video does not verify v12 animation.');
agents += '\n- v12 source/evidence snapshots: `art/verification/v12-release-source/`. Source status distinguishes tracked unchanged/modified, intended additions and previously unbaselined files; do not infer all game code stayed unchanged.\n';

if (checkOnly) {
  console.log(JSON.stringify({revision:'v12',checkOnly:true,passed:true,sourceFiles:sourceFiles.length,sourceAuditWithinAllowlist:true,packageSHA256:pkg.zipSHA256},null,2));
  process.exit(0);
}
const finalization = {revision:'v12',passed:false,stage:'started',startedAtUTC:new Date().toISOString(),sourceAuditWithinAllowlist:true};
write('art/verification/v12-finalization.json', finalization);
try {
  fs.copyFileSync(local('builds/BorrowedLight-Windows.zip'), local(archive), fs.constants.COPYFILE_EXCL);
  assertHash(archive, pkg.zipSHA256);
  fs.mkdirSync(local(snapshot));
  for (const item of sourceFiles) {
    const destination = child(snapshot, item.snapshot);
    fs.mkdirSync(path.dirname(destination), {recursive:true});
    fs.copyFileSync(local(item.source), destination, fs.constants.COPYFILE_EXCL);
    assertHash(destination, item.sha256);
  }
  write(snapshot + '/source-files.json', sourceFiles);
  write(snapshot + '/source-audit.json', audit);
  Object.assign(checks,{stagingOnly:false,releaseReady:true,status:'Promoted locally after limited grass/ground reviews, final native/Web QA, package/HTTP and review-page checks. Overall aesthetic objective remains unachieved.',packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,visualReviewPageVerification:'art/verification/v12-review-page-verification.json',packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,nativeCandidateIdentity:nativeIdentity,sourceAuditWithinAllowlist:true,sourceSnapshot:'art/verification/v12-release-source/',previousStableWebArchivePresent:true,finalizedAtUTC:new Date().toISOString()});
  delete checks.gameSourcesUnchangedFromV10; delete checks.gameSourcesUnchangedFromV11;
  const withoutCompletedStagingNote = values => Array.isArray(values) ? values.filter(item => !(typeof item === 'string' && item.startsWith('本工具只准备草稿：'))) : values;
  checks.limitations = withoutCompletedStagingNote(checks.limitations);
  if (manifest.scope) manifest.scope.limits = withoutCompletedStagingNote(manifest.scope.limits);
  manifest.verification.limits = withoutCompletedStagingNote(manifest.verification.limits);
  Object.assign(manifest.delivery,{stagingOnly:false,releaseReady:true,package:'../builds/BorrowedLight-Windows.zip',packageVerification:'verification/v12-package-verification.json',releaseHTTPVerification:'verification/v12-release-http-verification.json',packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,currentWindowsArchive:'../'+archive,previousStableWindowsArchive:'../builds/archive/BorrowedLight-v11-Windows.zip',previousStableWebArchive:'../builds/archive/BorrowedLight-v11-Web/',previousStableWebArchivePresent:true});
  manifest.verification.currentVisualReview='verification/visual-review-v12.html';
  manifest.verification.sourceAudit='verification/v12-release-source/source-audit.json';
  manifest.aestheticObjectiveAchieved=false;
  world.adoption={game:'v12',status:'Adopted after preservation/readback checks, limited fixed-camera review and final Windows/Web functional QA.',nativeQA:'../../verification/'+nativeRun+'/runtime-results.json',webQA:'../../verification/web-013-v12/runtime-results.json',fixedReview:'../../verification/v12-grass-refined/visual-review-world-v10.json',dynamicLimit:'No exhaustive dynamic foliage or all-angle visual acceptance.',aestheticObjectiveAchieved:false};
  world.visual_review_pending=false;
  if (world.visual_review) world.visual_review.release_acceptance_pending=false;
  Object.assign(ground,{stagingOnly:false,adopted:true,adoption:{game:'v12',detailStrength:0.35,tileMetres:1.8,normalScale:0.22,import:checks.selectedGround.import,nativeQA:'art/verification/'+nativeRun+'/runtime-results.json',webQA:'art/verification/web-013-v12/runtime-results.json',scope:'Fixed visual review plus final functional QA; no isolated ground-shader performance gain or all-angle claim.'}});
  if (ground.currentValidation) ground.currentValidation.performance='Final normal-game short samples are recorded in '+nativeRun+'/web-013-v12; no isolated shader performance attribution.';
  ground.title='Ground albedo detail v12 — adopted .35 layer';
  if (Array.isArray(ground.limitations)) ground.limitations=ground.limitations.map(item=>item==='Final normal native/WebGL performance and release adoption remain pending.'?'Final native/Web QA and local adoption completed; short samples do not establish isolated shader cost or sustained minimum FPS.':item);
  write('art/verification/release-checks.json',checks); write('art/verification/v12-release-checks.json',checks);
  write('art/production-manifest.json',manifest); write('art/generated/world-v10/asset-manifest.json',world); write('art/generated/ground-v12/manifest.json',ground); write('AGENTS.md',agents);
  const handoffFiles=[];
  for (const source of handoffSources) {
    const target=child(snapshot,'handoff/'+source);
    fs.mkdirSync(path.dirname(target),{recursive:true}); fs.copyFileSync(local(source),target,fs.constants.COPYFILE_EXCL);
    const digest=hash(source); assertHash(target,digest); handoffFiles.push({source,sha256:digest,snapshot:'handoff/'+source});
  }
  write(snapshot+'/handoff-files.json',handoffFiles);
  write('art/verification/v12-work-in-progress.json',{revision:'v12',status:'Promoted locally after limited grass/ground review, native/Web QA and package/HTTP verification.',aestheticObjectiveAchieved:false,releaseChecks:'v12-release-checks.json',limits:'Fixed studies and short QA samples do not establish all-angle foliage, exhaustive animation or overall visual superiority.'});
  Object.assign(finalization,{passed:true,stage:'complete',completedAtUTC:new Date().toISOString(),packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,sourceFiles:sourceFiles.length,handoffFiles:handoffFiles.length});
  write('art/verification/v12-finalization.json',finalization);
  console.log(JSON.stringify(finalization,null,2));
} catch(error) {
  Object.assign(finalization,{passed:false,stage:'failed-preserved-for-inspection',error:String(error.stack||error)});
  write('art/verification/v12-finalization.json',finalization); throw error;
}
