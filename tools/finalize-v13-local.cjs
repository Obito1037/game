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
const draft = 'art/verification/v13-release-draft';
const manifest = read('art/production-manifest.json'), checks = read('art/verification/release-checks.json');
const draftManifest = read(draft + '/production-manifest.json'), draftChecks = read(draft + '/release-checks.json');
const promotion = read('art/verification/v13-promotion.json');
assert.equal(manifest.revision, 'v13'); assert.equal(checks.revision, 'v13');
assert(promotion.passed === true && promotion.revision === 'v13' && promotion.previousRevision === 'v12' && promotion.candidateCopiesPreserved === true, 'Promotion record incomplete');
jsonEqual(promotion.buildIds, manifest.buildIds);
assertHash('art/production-manifest.json', promotion.draftSHA256['production-manifest.json']);
assertHash('art/verification/release-checks.json', promotion.draftSHA256['release-checks.json']);
for (const [name, digest] of Object.entries(promotion.draftSHA256)) assertHash(child(draft, name), digest);
assert(checks.windowsFunctionalPassed === true && checks.webFunctionalPassed === true && checks.buildIds.windows === manifest.buildIds.windows && checks.buildIds.web === manifest.buildIds.web, 'Draft acceptance/build IDs differ');
const nativeRun = checks.nativeRun, webRun = checks.webRun;
assert(typeof webRun === 'string' && /^web-\d+-v13$/.test(webRun), 'Invalid web QA session');
const nativeExecutable = checks.candidatePaths.native, nativeCandidate = path.dirname(nativeExecutable), webCandidate = checks.candidatePaths.web;
assert.equal(local(nativeExecutable), local('builds/candidates/v13-tree-refined/windows/BorrowedLight.exe'));
assert.equal(local(webCandidate), local('builds/candidates/v13/web'));
assert.equal(manifest.delivery.windowsCandidate, nativeExecutable); assert.equal(manifest.delivery.webCandidate, webCandidate);
jsonEqual(promotion.candidatePaths, checks.candidatePaths); assert.equal(promotion.webRun, webRun);
assert(typeof nativeRun === 'string' && /^run-\d+-v13$/.test(nativeRun), 'Invalid native QA session');
assert.equal(promotion.nativeRun, nativeRun);
assert.equal(checks.evidence.native, `art/verification/${nativeRun}/runtime-results.json`);
assert.equal(checks.evidence.nativeIdentity, `art/verification/${nativeRun}/build-evidence.json`);
assert.equal(checks.evidence.web, `art/verification/${webRun}/runtime-results.json`);
assert.equal(checks.evidence.webIdentity, `art/verification/${webRun}/artifact-identity.json`);
const nativeBuild = read(checks.evidence.nativeBuild), webBuild = read(checks.evidence.webBuild);
for (const [record, platform, id, output] of [[nativeBuild,'StandaloneWindows64',manifest.buildIds.windows,nativeExecutable],[webBuild,'WebGL',manifest.buildIds.web,webCandidate]]) {
  assert(record.status === 'completed' && record.result === 'Succeeded' && record.platform === platform && record.totalErrors === 0 && record.buildId === id, 'Build report status/platform/identity differs');
  assert.equal(local(record.outputPath), local(output), 'Actual build output path differs');
}

const pkg = read('art/verification/v13-package-verification.json');
const http = read('art/verification/v13-release-http-verification.json');
const page = read('art/verification/v13-review-page-verification.json');
assert(pkg.passed === true && pkg.requiredFilesPresent === true && pkg.debugFoldersExcluded === true && pkg.allZipFileHashesMatchCurrentBuild === true && pkg.zipFilesHashCompared === pkg.expectedPlayerFiles && pkg.expectedPlayerFiles > 0 && Array.isArray(pkg.failures) && pkg.failures.length === 0, 'ZIP verification incomplete');
assertHash('builds/BorrowedLight-Windows.zip', pkg.zipSHA256);
assert.equal(fs.statSync(local('builds/BorrowedLight-Windows.zip')).size, pkg.zipBytes);
assertHash('builds/windows/BorrowedLight_Data/resources.assets', pkg.nativeResourcesSHA256);
assertHash('builds/windows/BorrowedLight_Data/Managed/Assembly-CSharp.dll', pkg.nativeGameAssemblySHA256);
assert(http.passed === true && http.revision === 'v13' && http.indexReferencesCurrentFiles === true && local(http.root) === local('builds/web'), 'Current HTTP verification incomplete');
assert.equal(new URL(http.server).hostname, '127.0.0.1', 'Release must remain local');
assert(page.passed === true && page.page === 'visual-review-v13.html' && Array.isArray(page.errors) && page.errors.length === 0 && Array.isArray(page.missingLocalLinks) && page.missingLocalLinks.length === 0, 'Review page has not passed');
assertHash('art/verification/visual-review.html', promotion.draftSHA256['visual-review.html']);
assertHash('art/verification/visual-review-v13.html', promotion.draftSHA256['visual-review.html']);
if (page.sha256) assertHash('art/verification/visual-review-v13.html', page.sha256);
if (page.pageSHA256) assertHash('art/verification/visual-review-v13.html', page.pageSHA256);

const native = read(checks.evidence.native), web = read(checks.evidence.web);
for (const key of ['puzzleCompleted','menuKeyboardStart','pauseStopsMovement','resumeMovement','restartWorks','endingReturnWorks','cabinCollisionWorks','walkwayGroundingWorks','boulderCollisionWorks','observatoryGroundingWorks','observatoryInstrumentCollisionWorks','decorativeLeavesExcluded','pierGroundingWorks','pierRailCollisionWorks','scrollZoomWorks']) assert.equal(native[key], true, 'Native QA: ' + key);
for (const key of ['passed','realKeyboardPuzzleCompletion','persistedProgressReload','crossOriginIsolated','audioContextResumeObserved','defaultBrowserAutoplayPolicy']) assert.equal(web[key], true, 'Web QA: ' + key);
assert(Array.isArray(web.errors) && web.errors.length === 0, 'Web errors present');
const launch = read(checks.evidence.nativeIdentity);
assert.equal(launch.buildId, manifest.buildIds.windows);
assert.equal(launch.mode, 'Tour');
assert.equal(local(launch.playerDirectory), local(nativeCandidate));
const nativeNames = ['BorrowedLight.exe','UnityPlayer.dll','BorrowedLight_Data/resources.assets','BorrowedLight_Data/Managed/Assembly-CSharp.dll'];
assert.deepEqual(launch.files.map(x => x.name.replace(/\\/g, '/')).sort(), [...nativeNames].sort());
const nativeIdentity = launch.files.map(file => {
  const candidateSHA256 = hash(child(nativeCandidate, file.name));
  const releaseSHA256 = hash(child('builds/windows', file.name));
  assert(sameHash(file.sha256, candidateSHA256) && sameHash(candidateSHA256, releaseSHA256), 'Native candidate/release differs from QA');
  return {name:file.name, qaSHA256:file.sha256, candidateSHA256, releaseSHA256};
});
const webIdentity = read(checks.evidence.webIdentity);
assert(webIdentity.passed === true && webIdentity.declaredBuildMatches === true && webIdentity.requestedAllCurrentFiles === true && webIdentity.buildId === manifest.buildIds.web && webIdentity.session === webRun, 'Web QA identity differs');
const payloadNames = manifest.webPayload.files.map(f => f.name);
assert(payloadNames.length === 4 && new Set(payloadNames).size === 4);
assert.deepEqual(webIdentity.files.map(f => f.name).sort(), [...payloadNames].sort());
assert.deepEqual(http.files.map(f => f.name).sort(), [...payloadNames].sort());
let payloadBytes = 0;
for (const file of manifest.webPayload.files) {
  assert(path.basename(file.name) === file.name && !/[\\/:]/.test(file.name), 'Payload must be a basename');
  for (const dir of [webCandidate + '/Build','builds/web/Build']) {
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

// Complete v12 baseline: only two opt-in diagnostic sources may change.
// Ground, stone, character and all other resource/shader files stay frozen.
const audit = draftManifest.sourceAudit;
jsonEqual(audit, draftChecks.sourceAudit); jsonEqual(audit, manifest.sourceAudit); jsonEqual(audit, checks.sourceAudit);
assert(audit && audit.allChangesWithinScope === true && audit.baseline === 'art/verification/v12-release-source/source-files.json', 'Missing source audit');
const prefix = 'GameProject/Assets/BorrowedLight/';
const allowedChanged = [prefix + 'Runtime/WorldDirector.cs', prefix + 'Runtime/WorldMaterialStudy.cs'];
const allowedAdded = [];
const inventoryRoots = ['Runtime','Shaders','Resources/Materials','Resources/Textures'].map(x => prefix + x);
const inventoryExtensions = ['.cs','.shader','.hlsl','.mat','.png','.meta'];
const sorted = list => [...list].sort();
jsonEqual(sorted(audit.allowedChangedExisting), sorted(allowedChanged)); jsonEqual(sorted(audit.allowedAdded), sorted(allowedAdded));
jsonEqual(sorted(audit.inventoryRoots), sorted(inventoryRoots)); jsonEqual(sorted(audit.inventoryExtensions), sorted(inventoryExtensions));
const baseline = read(audit.baseline);
assert(Array.isArray(baseline) && baseline.length === 91, 'Unexpected v12 tracked source inventory');
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
    assert(sameHash(item.baselineSHA256, previous), 'v12 baseline hash rewritten');
    const changed = !sameHash(previous, item.sha256);
    assert.equal(item.status, changed ? 'modified' : 'unchanged');
    assert(!changed || allowedChanged.includes(item.source), 'Unexpected tracked source modification');
  } else {
    assert.fail('Source absent from complete v12 baseline: ' + item.source);
  }
  return {source:item.source, sha256:hash(item.source), baselineSHA256:item.baselineSHA256, status:item.status, snapshot:'files/' + item.source};
});
for (const file of [...baselineMap.keys(), ...allowedAdded]) assert(inventory.has(file), 'Missing baseline/allowed-addition file: ' + file);
for (const item of baseline) assertHash(child('art/verification/v12-release-source', item.snapshot), item.sha256);
assert.equal(audit.normalWorldDirectorUnchangedExceptStudyBranch, true);
const directorRow = baseline.find(item => item.source === prefix + 'Runtime/WorldDirector.cs');
const directorBefore = readText(child('art/verification/v12-release-source', directorRow.snapshot)).replace(/\r\n/g, '\n');
const directorNow = readText(directorRow.source).replace(/\r\n/g, '\n');
const treeEntry = '    if(args[i]=="-borrowedLightTreeStudy"){StartCoroutine(WorldMaterialStudy(args[i+1],false,false,true));break;}\n';
assert.equal(directorNow.split(treeEntry).length, 2, 'Expected a single opt-in TreeStudy branch');
assert.equal(directorNow.replace(treeEntry,''), directorBefore, 'Normal WorldDirector changed');

assertHash('GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx', manifest.geometry.worldFbxSHA256);
assertHash('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx', manifest.geometry.travelerFbxSHA256);
const world = read('art/generated/world-v12/asset-manifest.json');
const interchange = read('art/generated/world-v12/interchange-verification.json');
assert(world.revision === 'world-v12' && world.triangles === 538118 && interchange.passed === true, 'Unexpected world or incomplete readback');
assert(sameHash(world.sha256['island.fbx'], manifest.geometry.worldFbxSHA256));
for (const [name, digest] of Object.entries(world.sha256)) assertHash(child('art/generated/world-v12', name), digest);
const ground = read('art/generated/ground-v12/manifest.json');
assert.equal(ground.detailStrength, 0.35); assert.equal(ground.intendedTileMetres, 1.8);
assertHash('art/generated/ground-v12/earth-detail-original.png', ground.sha256);
assertHash(prefix + 'Resources/Textures/GroundDetailV12.png', ground.sha256);
assertHash('builds/archive/BorrowedLight-v12-Windows.zip', '6B03683B947CFC646EB2D088B77692611D7C0EE8C83556D0D1D623FA499C6C79');
assert(exists('builds/archive/BorrowedLight-v12-Web') && exists('builds/candidates/v12-windows-previous') && exists('builds/candidates/v12-web-previous'), 'Prior release preservation missing');

const handoffSources = ['AGENTS.md','PLAY.zh-CN.txt','CONCEPT-48H.zh-CN.txt','SUBMISSION-演示与材料.zh-CN.txt','AI-使用与素材来源.zh-CN.txt','setup/NEXT-STEPS.zh-CN.txt','Open-Borrowed-Light.cmd','Open-Borrowed-Light-Web.cmd','Open-Borrowed-Light-Fullscreen.cmd','tools/package-templates/Play-Fullscreen.cmd','art/production-manifest.json','art/verification/release-checks.json','art/verification/visual-review-v13.html',
  'tools/run-game-qa.ps1','tools/snapshot-island-import.cs','tools/compare-island-import.cjs','tools/compare-material-study-conditions.cjs','tools/prepare-v13-handoff.cjs','tools/verify-visual-review.cjs','tools/record-game-builds.cjs','tools/verify-candidate-artifacts.cjs','tools/verify-game-web.cjs','tools/verify-game-release-http.cjs','tools/promote-v13-local.ps1','tools/finalize-v13-local.cjs',
  'art/blender/build_island_v12.py','art/generated/world-v12/verify_world_v12.py','art/generated/world-v12/asset-manifest.json','art/generated/world-v12/asset-manifest-at-audit.json','art/generated/world-v12/IMPORT-NOTES.zh-CN.txt','art/generated/world-v12/freeze-summary.json','art/generated/world-v12/interchange-verification.json','art/generated/world-v12/visual-review.json',
  'art/verification/v13-trees-refined/decision.json','art/verification/v13-trees-refined/independent-review.json','art/verification/v13-trees-candidate/decision.json','art/verification/v13-trees-refined/capture-condition-comparison.json','art/verification/v13-trees-refined/unity-import-comparison.json'];
handoffSources.push('tools/prepare-v13-main-review.cjs');
for (const file of handoffSources) assert(fs.statSync(local(file)).isFile(), 'Missing snapshot input: ' + file);
const archive = 'builds/archive/BorrowedLight-v13-Windows.zip', snapshot = 'art/verification/v13-release-source';
for (const destination of [archive, snapshot, 'art/verification/v13-release-checks.json','art/verification/v13-finalization.json']) assert(!exists(destination), 'Historical destination already exists; inspect before retry: ' + destination);
let agents = readText('AGENTS.md');
function replaceAgentLine(pattern, replacement) {
  assert.equal((agents.match(new RegExp(pattern.source, 'gm')) || []).length, 1, 'AGENTS release marker missing/ambiguous');
  agents = agents.replace(pattern, replacement);
}
replaceAgentLine(/^- Borrowed Light v12 is built.*$/m, '- Borrowed Light v13 is built for Windows x64 and WebGL. Final native QA: `art/verification/'+nativeRun+'/`; normal browser QA: `art/verification/'+webRun+'/`. Launchers remain local; no public deployment. Fixed tree studies and short performance samples do not establish overall superiority over the reference.');
replaceAgentLine(/^- Game revision v12 uses.*$/m, '- Game revision v13 uses frozen `art/generated/world-v12/` (538118 triangles, derived from world-v10), character-v9, stone-v10 and retained ground-v12. Keep world-v10/v8/v7/v6 and character-v5/v6/v7/v8/v9 dependencies. Only three tree meshes changed; 26 non-target meshes, 14 anchors, material slots and world textures are preserved. Rejected world-v11 and prior v12 releases remain archived.');
replaceAgentLine(/^- v12 refines two grass meshes.*$/m, '- v13 changes three tree meshes and adds opt-in TreeStudy diagnostics in WorldDirector/WorldMaterialStudy. The complete 91-file v12 source/resource baseline allows only those two diagnostic source changes; normal WorldDirector equals baseline after removing the single TreeStudy entry. Ground detail .35 / tile 1.8m / normal .22, stone, grass, character and gameplay remain from v12. Low 39 trunk/root components are preserved, but upper tree collider geometry changes; no dedicated all-tree collision or all-pose test is claimed.');
agents += '\n- v13 source/evidence snapshots: `art/verification/v13-release-source/`. Five fixed tree views are limited static evidence; prior gait videos do not verify this revision. No isolated tree performance A/B/A or sustained minimum FPS claim.\n';

if (checkOnly) {
  console.log(JSON.stringify({revision:'v13',checkOnly:true,passed:true,sourceFiles:sourceFiles.length,sourceAuditWithinAllowlist:true,packageSHA256:pkg.zipSHA256},null,2));
  process.exit(0);
}
const finalization = {revision:'v13',passed:false,stage:'started',startedAtUTC:new Date().toISOString(),sourceAuditWithinAllowlist:true};
write('art/verification/v13-finalization.json', finalization);
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
  Object.assign(checks,{stagingOnly:false,releaseReady:true,status:'Promoted locally after limited tree reviews, final native/Web QA, package/HTTP and review-page checks. Overall aesthetic objective remains unachieved.',packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,visualReviewPageVerification:'art/verification/v13-review-page-verification.json',packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,nativeCandidateIdentity:nativeIdentity,sourceAuditWithinAllowlist:true,sourceSnapshot:'art/verification/v13-release-source/',previousStableWebArchivePresent:true,finalizedAtUTC:new Date().toISOString()});
  delete checks.gameSourcesUnchangedFromV10; delete checks.gameSourcesUnchangedFromV11;
  const withoutCompletedStagingNote = values => Array.isArray(values) ? values.filter(item => !(typeof item === 'string' && item.startsWith('本工具只准备草稿：'))) : values;
  checks.limitations = withoutCompletedStagingNote(checks.limitations);
  if (manifest.scope) manifest.scope.limits = withoutCompletedStagingNote(manifest.scope.limits);
  manifest.verification.limits = withoutCompletedStagingNote(manifest.verification.limits);
  Object.assign(manifest.delivery,{stagingOnly:false,releaseReady:true,package:'../builds/BorrowedLight-Windows.zip',packageVerification:'verification/v13-package-verification.json',releaseHTTPVerification:'verification/v13-release-http-verification.json',packageVerificationPassed:true,releaseHTTPVerified:true,visualReviewPageVerified:true,packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,currentWindowsArchive:'../'+archive,previousStableWindowsArchive:'../builds/archive/BorrowedLight-v12-Windows.zip',previousStableWebArchive:'../builds/archive/BorrowedLight-v12-Web/',previousStableWebArchivePresent:true});
  manifest.verification.currentVisualReview='verification/visual-review-v13.html';
  manifest.verification.sourceAudit='verification/v13-release-source/source-audit.json';
  manifest.aestheticObjectiveAchieved=false;
  // Frozen authoring/ground manifests are read-only during finalization; release adoption is recorded here.
  manifest.scope.trees.releaseAdoption={game:'v13',nativeQA:checks.evidence.native,webQA:checks.evidence.web,limitedStaticAccepted:true,limits:'Upper tree collider changed; no dedicated all-tree collision or complete dynamic-pose coverage.'};
  write('art/verification/release-checks.json',checks); write('art/verification/v13-release-checks.json',checks);
  write('art/production-manifest.json',manifest); write('AGENTS.md',agents);
  const handoffFiles=[];
  for (const source of handoffSources) {
    const target=child(snapshot,'handoff/'+source);
    fs.mkdirSync(path.dirname(target),{recursive:true}); fs.copyFileSync(local(source),target,fs.constants.COPYFILE_EXCL);
    const digest=hash(source); assertHash(target,digest); handoffFiles.push({source,sha256:digest,snapshot:'handoff/'+source});
  }
  write(snapshot+'/handoff-files.json',handoffFiles);
  write('art/verification/v13-work-in-progress.json',{revision:'v13',status:'Promoted locally after limited tree review, native/Web QA and package/HTTP verification.',aestheticObjectiveAchieved:false,releaseChecks:'v13-release-checks.json',limits:'Fixed studies and short QA samples do not establish all-angle foliage, exhaustive animation or overall visual superiority.'});
  Object.assign(finalization,{passed:true,stage:'complete',completedAtUTC:new Date().toISOString(),packageBytes:pkg.zipBytes,packageSHA256:pkg.zipSHA256,sourceFiles:sourceFiles.length,handoffFiles:handoffFiles.length});
  write('art/verification/v13-finalization.json',finalization);
  console.log(JSON.stringify(finalization,null,2));
} catch(error) {
  Object.assign(finalization,{passed:false,stage:'failed-preserved-for-inspection',error:String(error.stack||error)});
  write('art/verification/v13-finalization.json',finalization); throw error;
}
