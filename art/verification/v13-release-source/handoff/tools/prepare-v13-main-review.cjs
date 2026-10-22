'use strict';

// Stage the v13 main review only after final native/Web reports and QA exist.
// Links resolve from art/verification after root promotes this draft.
// node tools/prepare-v13-main-review.cjs [--check-only]
// BORROWED_LIGHT_NATIVE_QA / BORROWED_LIGHT_WEB_QA can select later v13 sessions.
// No browser, game launch, binary hash or full-image read is performed here.
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '..'), verification = path.join(root, 'art/verification');
const output = path.join(verification, 'v13-release-draft/visual-review.html');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const assert = (value, message) => { if (!value) throw new Error(message); };
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const nativeRun = process.env.BORROWED_LIGHT_NATIVE_QA || 'run-033-v13';
const webRun = process.env.BORROWED_LIGHT_WEB_QA || 'web-014-v13';
assert(/^run-\d+-v13$/.test(nativeRun) && /^web-\d+-v13$/.test(webRun), 'Expected v13 normal QA session names.');
const links = new Set(), displayedImages = [];
function file(relative) {
  assert(typeof relative === 'string' && relative && !path.isAbsolute(relative) && !relative.includes('\\') && !/^[a-z][a-z\d+.-]*:/i.test(relative), 'Expected a relative evidence path.');
  const full = path.resolve(verification, relative), within = path.relative(root, full);
  assert(within && !path.isAbsolute(within) && within !== '..' && !within.startsWith('..' + path.sep), 'Path outside workspace: ' + relative);
  assert(fs.existsSync(full) && fs.statSync(full).isFile() && fs.statSync(full).size > 0, 'Missing/empty evidence: ' + relative);
  return full;
}
const read = relative => fs.readFileSync(file(relative), 'utf8').replace(/^\uFEFF/, '');
const json = relative => JSON.parse(read(relative));
const href = relative => { file(relative); links.add(relative); return escape(relative); };
const link = (relative, label) => `<a href="${href(relative)}">${escape(label)}</a>`;
const hashSame = (a, b) => typeof a === 'string' && /^[a-f0-9]{64}$/i.test(a) && typeof b === 'string' && a.toUpperCase() === b.toUpperCase();
function png(relative) {
  const full = file(relative), length = fs.statSync(full).size;
  assert(length >= 36, 'PNG too short: ' + relative);
  const handle = fs.openSync(full, 'r'), head = Buffer.alloc(24), tail = Buffer.alloc(12);
  try {
    assert(fs.readSync(handle, head, 0, head.length, 0) === head.length && fs.readSync(handle, tail, 0, tail.length, length - tail.length) === tail.length, 'PNG metadata read incomplete: ' + relative);
  } finally { fs.closeSync(handle); }
  assert(head.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) && head.toString('ascii', 12, 16) === 'IHDR'
    && tail.equals(Buffer.from([0,0,0,0,73,69,78,68,174,66,96,130])), 'Incomplete original PNG: ' + relative);
  const size = { width: head.readUInt32BE(16), height: head.readUInt32BE(20) };
  assert(size.width > 0 && size.height > 0, 'Invalid PNG dimensions: ' + relative); return size;
}
const sameSize = (a, b, label) => assert(a.width === b.width && a.height === b.height, 'Dimensions differ: ' + label);
function successfulBuild(relative, platform) {
  const report = json(relative);
  assert(report.status === 'completed' && report.result === 'Succeeded' && report.platform === platform && /^build_[a-z0-9]+$/i.test(report.buildId)
    && report.totalErrors === 0 && Array.isArray(report.errors) && report.errors.length === 0, 'Final build report incomplete: ' + relative);
  return report;
}
const nativeReportPath = 'v13-native-build.json', webReportPath = 'v13-web-build.json';
const nativeReport = successfulBuild(nativeReportPath, 'StandaloneWindows64'), webReport = successfulBuild(webReportPath, 'WebGL');
const nativePath = nativeRun + '/runtime-results.json', webPath = webRun + '/runtime-results.json';
const native = json(nativePath), web = json(webPath);
for (const key of ['puzzleCompleted', 'menuKeyboardStart', 'pauseStopsMovement', 'resumeMovement', 'restartWorks', 'endingReturnWorks',
  'cabinCollisionWorks', 'walkwayGroundingWorks', 'boulderCollisionWorks', 'observatoryGroundingWorks', 'observatoryInstrumentCollisionWorks',
  'decorativeLeavesExcluded', 'pierGroundingWorks', 'pierRailCollisionWorks', 'scrollZoomWorks']) assert(native[key] === true, 'Native QA failed/missing: ' + key);
assert(native.walkingDistance > 0 && Math.abs(native.normalizedScrollStepMetres - 0.35) < 0.0001, 'Native movement/scroll evidence incomplete.');
for (const key of ['passed', 'realKeyboardPuzzleCompletion', 'persistedProgressReload', 'crossOriginIsolated', 'audioContextResumeObserved', 'defaultBrowserAutoplayPolicy']) assert(web[key] === true, 'Web QA failed/missing: ' + key);
assert(Array.isArray(web.errors) && web.errors.length === 0, 'Web QA errors missing/non-empty.');
for (const [name, record] of [['native', native], ['Web', web]]) for (const key of ['width', 'height']) assert(Number.isInteger(record[key]) && record[key] > 0, 'Missing ' + name + ' dimensions: ' + key);
const nativeIdentityPath = nativeRun + '/build-evidence.json', webIdentityPath = webRun + '/artifact-identity.json';
const nativeIdentity = json(nativeIdentityPath), webIdentity = json(webIdentityPath);
assert(nativeIdentity.mode === 'Tour' && nativeIdentity.buildId === nativeReport.buildId, 'Normal native QA identifies another build or diagnostic mode.');
const nativeDirectory = path.dirname(path.resolve(nativeReport.outputPath));
assert(path.resolve(nativeIdentity.playerDirectory) === nativeDirectory, 'Native QA directory differs from final report.');
assert(webIdentity.passed === true && webIdentity.buildId === webReport.buildId && webIdentity.session === webRun
  && webIdentity.declaredBuildMatches === true && webIdentity.requestedAllCurrentFiles === true, 'Normal Web identity incomplete.');
const payload = webReport.payload;
assert(payload?.files?.length === 4 && new Set(payload.files.map(item => item.name)).size === 4 && Number.isSafeInteger(payload.bytes) && payload.bytes > 0
  && payload.files.reduce((sum, item) => sum + item.bytes, 0) === payload.bytes && webIdentity.files?.length === 4, 'Final Web payload incomplete.');
for (const item of payload.files) {
  const identity = webIdentity.files.find(row => row.name === item.name);
  assert(path.basename(item.name) === item.name && !/[\\/:]/.test(item.name) && Number.isSafeInteger(item.bytes) && item.bytes > 0
    && identity?.matches === true && identity.bytes === item.bytes && hashSame(identity.httpSHA256, item.sha256) && hashSame(identity.diskSHA256, item.sha256), 'Web QA/report payload identity differs: ' + item.name);
}
const nativeImage = nativeRun + '/07-walking.png';
sameSize(png(nativeImage), native, 'normal native walking PNG versus runtime');

const baselineDir = 'v13-trees-baseline', refinedDir = 'v13-trees-refined';
const decisionPath = refinedDir + '/decision.json', decision = json(decisionPath);
const views = ['path', 'island', 'left-tree', 'gold-tree', 'right-pine'];
assert(decision.accepted === true && decision.candidateGame === 'v13' && decision.candidateWorld === 'world-v12' && decision.buildId === nativeReport.buildId,
  'Accepted tree decision differs from final game/model/build.');
assert(typeof decision.reviewer === 'string' && decision.reviewer.trim() && Array.isArray(decision.reviewedOriginals)
  && views.every(view => decision.reviewedOriginals.includes(view + '-current.png')), 'Root review of all five originals missing.');
assert(Array.isArray(decision.improvements) && decision.improvements.length > 0 && decision.improvements.every(item => typeof item === 'string' && item.trim())
  && Array.isArray(decision.limitations) && decision.limitations.length > 0 && decision.limitations.every(item => typeof item === 'string' && item.trim())
  && Array.isArray(decision.blockingProblems) && decision.blockingProblems.length === 0, 'Accepted visual conclusion/limits incomplete.');
const staticIdentity = json(refinedDir + '/build-evidence.json'), baselineIdentity = json(baselineDir + '/build-evidence.json');
assert(staticIdentity.mode === 'TreeStudy' && baselineIdentity.mode === 'TreeStudy' && staticIdentity.buildId === decision.buildId
  && baselineIdentity.buildId === decision.baselineBuildId, 'Static tree build identities differ from decision.');
function identityMap(record) {
  assert(Array.isArray(record.files), 'Identity file list missing.');
  return new Map(record.files.map(item => [item.name.replace(/\\/g, '/'), item.sha256]));
}
const normalFiles = identityMap(nativeIdentity), staticFiles = identityMap(staticIdentity), baselineFiles = identityMap(baselineIdentity);
const identityNames = ['BorrowedLight.exe', 'UnityPlayer.dll', 'BorrowedLight_Data/resources.assets', 'BorrowedLight_Data/Managed/Assembly-CSharp.dll'];
assert(normalFiles.size === 4 && staticFiles.size === 4 && baselineFiles.size === 4, 'Expected four player identity files per session.');
for (const name of identityNames) assert(hashSame(normalFiles.get(name), staticFiles.get(name)), 'Normal player differs from accepted static capture: ' + name);
for (const name of identityNames.filter(name => !name.endsWith('resources.assets'))) assert(hashSame(baselineFiles.get(name), staticFiles.get(name)), 'Baseline/refined diagnostic program identity differs: ' + name);
for (const folder of [baselineDir, refinedDir]) {
  const study = json(folder + '/material-study.json');
  assert(study.materialFamily === 'tree-geometry' && study.geometryStudy === true && study.completed === true && study.captureComplete === true
    && study.failed === false && study.allInvariantsPassed === true && study.expectedImageCount === 10 && study.completedImages === 10
    && study.capturedImageCount === 10 && study.views?.length === 10, 'Incomplete ten-image tree study: ' + folder);
  for (const view of views) for (const variant of ['current', 'repeat']) {
    const image = view + '-' + variant + '.png', rows = study.views.filter(row => row?.image === image && row.variant === variant);
    assert(rows.length === 1, 'Tree image missing/duplicated: ' + folder + '/' + image);
    const row = rows[0], size = png(folder + '/' + image);
    assert(row.materialsUnchanged === true && row.transformsAndLightsUnchanged === true && Number.isFinite(row.fieldOfView)
      && row.cameraPosition && row.cameraRotation && row.lookTarget, 'Tree per-view conditions incomplete: ' + image);
    sameSize(size, study, folder + '/' + image);
    sameSize(size, { width: row.actualPNGWidth, height: row.actualPNGHeight }, 'actual tree PNG versus per-view record');
  }
}
const capturePath = refinedDir + '/capture-condition-comparison.json', importPath = refinedDir + '/unity-import-comparison.json';
const capture = json(capturePath), imported = json(importPath);
assert(['passed', 'sceneMatch', 'viewMatch', 'lightsMatch', 'bothStable'].every(key => capture[key] === true)
  && ['completeCaptures', 'materialsMatch', 'ambientMatch', 'targetsMatch', 'viewDetailsMatch'].every(key => capture.treeConditions?.[key] === true), 'Static tree conditions do not match.');
assert(path.resolve(capture.baseline) === path.join(verification, baselineDir) && path.resolve(capture.candidate) === path.join(verification, refinedDir), 'Static condition comparison identifies other sessions.');
assert(['passed', 'anchorsUnchanged', 'nonTargetUnchanged', 'allMaterialsUnchanged', 'allTransformsUnchanged', 'vertexChannelsComplete', 'targetChangesPresent'].every(key => imported[key] === true), 'Unity tree preservation comparison incomplete.');
const worldSummaryPath = '../generated/world-v12/freeze-summary.json', interchangePath = '../generated/world-v12/interchange-verification.json';
const worldSummary = json(worldSummaryPath), interchange = json(interchangePath);
assert(worldSummary.revision === 'world-v12' && worldSummary.gameCandidate === 'v13' && worldSummary.triangles === 538118
  && worldSummary.fullInterchangePassed === true && worldSummary.frozenSourceFilesUnchanged === true && imported.trianglesAfter === worldSummary.triangles, 'Frozen tree model identity/triangle record differs.');
assert(interchange.revision === 'world-v12' && interchange.game_candidate === 'v13' && interchange.passed === true && interchange.in_progress === false
  && interchange.checks?.length === 3 && interchange.checks.every(item => item.passed === true && item.triangles === worldSummary.triangles
    && item.materials_identical === true && item.anchors_identical === true && item.unchanged_non_targets?.length === 26 && item.unchanged_non_targets.every(row => row.same === true)), 'World three-format preservation incomplete.');
assert(interchange.low_trunk_component_checks?.length > 0 && interchange.low_trunk_component_checks.every(row => row.geometry_uv_colour_exact === true), 'Low trunk/root geometry protection incomplete.');
const ground = json('../generated/ground-v12/manifest.json');
assert(ground.adopted === true && Math.abs(ground.detailStrength - 0.35) < 0.0001 && Math.abs(ground.intendedTileMetres - 1.8) < 0.0001, 'Retained ground-v12 parameters differ.');
const template = read('visual-review-v12.html');
const style = template.match(/<style\b[^>]*>[\s\S]*?<\/style>/i)?.[0], dialog = template.match(/<dialog\b[^>]*>[\s\S]*?<\/dialog>/i)?.[0];
assert(style && dialog, 'Original-image CSS/dialog template missing.');
function figure(relative, title, caption, label, reference = false) {
  const size = png(relative), url = href(relative); displayedImages.push(relative);
  return `<figure><div class="card-top"><span class="source ${reference ? 'reference' : 'ours'}">${escape(label)}</span><span class="resolution">${size.width} × ${size.height} · 原图</span></div><a class="picture" href="${url}" data-title="${escape(title)}" data-width="${size.width}" data-height="${size.height}"><img src="${url}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)}</strong>${escape(caption)}<div class="file">${escape(relative)}</div></figcaption></figure>`;
}
const normalSection = `<section><div class="section-head"><h2>01 / 参考与 v13 正常游戏</h2><p class="section-note">不同作品、日夜与构图，不是受控 A/B。</p></div><div class="grid">${figure('../reference/littleprince-gameplay.png', '参考网站 · 实际游玩画面', '仅供本地视觉研究；此参考截图没有成熟树冠，不能用来宣称复刻参考树形。', '参考 / Saccc_c', true)}${figure(nativeImage, '借光岛 v13 · 正常游戏漫步视角', '本次正常运行的完整实图；游戏版本 v13 使用树木模型 world-v12。角色 character-v9 与 ground-v12 材质参数沿用。', '本作 / 正常游戏')}</div><p class="section-note"><a href="https://littleprince.dev/">参考原网站</a> · <a href="https://x.com/Saccc_c/status/2110694725640474759">原推文</a> · ${link(nativePath, 'Windows 正常检查')} · ${link(webPath, '网页正常检查')}</p></section>`;
const names = { path: '路径完整构图', island: '全岛构图', 'left-tree': '左阔叶', 'gold-tree': '金树与金环', 'right-pine': '右侧针叶树' };
const treeSections = views.map((view, index) => {
  const before = baselineDir + '/' + view + '-current.png', after = refinedDir + '/' + view + '-current.png';
  sameSize(png(before), png(after), 'tree fixed-camera pair ' + view);
  return `<section><div class="section-head"><h2>0${index + 2} / 树形 · ${names[view]}</h2><p class="section-note">同源程序的 TreeStudy：固定姿态、机位、灯光与实际材质；不是正常游戏帧率或动态录像。</p></div><div class="grid">${figure(before, 'world-v10 基线 · ' + names[view], 'v12 成品使用的世界模型，在本轮相同 TreeStudy 程序下重新采集。', '树形 / 原模型基线')}${figure(after, 'world-v12 修正版 · ' + names[view], '本轮游戏 v13 采用的世界模型，保留低部根干并改善三树枝叶；此处仅作静态局部对照。', '树形 / 已采用修正版')}</div></section>`;
}).join('\n');
const evidence = [link('visual-review-v13-trees.html', '三版树木独立对照页（保留未采用首版）'), link(decisionPath, '静态采用当时的决定与限制'),
  link(refinedDir + '/independent-review.json', '修正版独立图评'), link('v13-trees-candidate/decision.json', '首版拒绝决定'),
  link(capturePath, '相机、灯光、实际材质与环境对照'), link(importPath, 'Unity 目标与保护对照'), link(interchangePath, 'BLEND / FBX / GLB 回读与低部保护记录'),
  link(worldSummaryPath, '模型冻结摘要')].join(' · ');
const runtimeEvidence = [link(nativeReportPath, '原生最终构建报告'), link(webReportPath, '网页最终构建报告'), link(nativeIdentityPath, '原生正常运行产物身份'),
  link(webIdentityPath, '网页正常运行产物身份'), link(baselineDir + '/build-evidence.json', '基线诊断产物身份'), link(refinedDir + '/build-evidence.json', '修正版诊断产物身份')].join(' · ');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v13 · 实机与树木对照</title>${style}</head>
<body><main><header><div class="eyebrow">Borrowed Light · v13 visual evidence</div><h1>借光岛 v13 · 实机与树木对照</h1><p class="lede">游戏 v13 采用 world-v12（${worldSummary.triangles.toLocaleString('en-US')} 三角），改善左阔叶、金树与右侧针叶树的形体，保留低部根干。首组为参考与正常游戏，随后五组为同源程序的冻结姿态诊断。</p><p class="lede">角色仍为 character-v9，地面沿用 ground-v12：颜色细节强度 ${ground.detailStrength.toFixed(2)}，平铺 ${ground.intendedTileMetres.toFixed(1)} m。整体视觉超过参考网站的目标尚未达到。</p><div class="tags"><span class="tag">十二张完整原图</span><span class="tag">正常游戏与静态诊断分列</span><span class="tag">原生 ${native.width} × ${native.height}</span><span class="tag">网页 ${web.width} × ${web.height}</span></div></header>
${normalSection}
${treeSections}
<aside class="review"><div><h2>可见改善与实际范围</h2><ul>${decision.improvements.map(item => `<li>${escape(item)}</li>`).join('')}</ul><p>${evidence}</p><p>正常运行记录：Windows ${escape(nativeReport.buildId)}，网页 ${escape(webReport.buildId)}。${runtimeEvidence}</p><p>修正版静态诊断与 Windows 正常游戏的四项产物身份一致；基线与修正版诊断的程序身份一致，世界模型分别留证。相同机位下的模型对照与实际正常操作分别留证。功能检查通过不能替代全部机位、全部树枝碰撞、动态风摆或移动闪烁验收。</p><p>低部保护记录限于几何、UV 和颜色，不宣称自定义法线逐字节完全相同。固定时间不冻结全部时域 AO 或随机项，不声称逐像素重复。首版 world-v11 被拒绝的记录保留在独立页。</p><p>正常运行的短样本不是持续行走平均或全程最低；本页没有树版与旧成品的同条件性能 A/B，不据此宣称提速或无性能回退。此版没有新增行走录像审查。</p></div><ul class="criteria">${decision.limitations.map(item => `<li>${escape(item)}</li>`).join('')}<li>原图未裁切、调色、重绘或生成缩略图文件。</li><li>静态采用决定中的历史进度不代表当前运行检查状态；最终结果以本页所附正常 QA 与构建报告为准。</li></ul></aside><footer>借光岛 v13 · 局部树形改善与正常运行证据 · 整体审美目标仍未完成</footer></main>${dialog}
<script>
(function(){
 const dialog=document.querySelector('dialog');
 document.querySelectorAll('.picture').forEach(function(link){
  const img=link.querySelector('img'),badge=link.closest('figure').querySelector('.resolution'),state=link.querySelector('.image-state');
  function loaded(){const mismatch=img.naturalWidth!==Number(link.dataset.width)||img.naturalHeight!==Number(link.dataset.height);link.classList.add('loaded');link.classList.remove('missing');badge.textContent=img.naturalWidth+' × '+img.naturalHeight+(mismatch?' · 与记录尺寸不同':' · 原图');badge.classList.toggle('mismatch',mismatch);}
  function missing(){link.classList.add('missing');badge.textContent='原图无法载入';state.textContent='请检查本地原图路径';}
  img.addEventListener('load',loaded);img.addEventListener('error',missing);if(img.complete){if(img.naturalWidth)loaded();else missing();}
  link.addEventListener('click',function(event){if(!img.naturalWidth||!dialog.showModal)return;event.preventDefault();dialog.querySelector('img').src=link.getAttribute('href');dialog.querySelector('img').alt=img.alt;dialog.querySelector('.dialog-bar span').textContent=link.dataset.title+' · '+img.naturalWidth+' × '+img.naturalHeight;dialog.querySelector('.original').href=link.getAttribute('href');dialog.showModal();});
 });
 dialog.querySelector('button').addEventListener('click',function(){dialog.close();});dialog.addEventListener('click',function(event){if(event.target===dialog)dialog.close();});
})();
</script></body></html>\n`;
assert(displayedImages.length === 12 && new Set(displayedImages).size === 12 && (html.match(/<img\s+src=/g) || []).length === 12, 'Expected exactly twelve displayed original images.');
if (!checkOnly) { fs.mkdirSync(path.dirname(output), {recursive:true}); fs.writeFileSync(output, html, 'utf8'); }
console.log(JSON.stringify({checkOnly, output, displayedImages, imageCount:displayedImages.length, nativeQA:nativePath, webQA:webPath,
  finalBuilds:{native:nativeReport.buildId,web:webReport.buildId}, staticDecision:decisionPath, model:'world-v12', game:'v13', triangles:worldSummary.triangles,
  localLinksChecked:links.size, linkBaseAfterPromotion:'art/verification/', aestheticObjectiveAchieved:false}, null, 2));
