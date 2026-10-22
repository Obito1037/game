'use strict';

// Stage the complete v12 review after final normal-game QA. No browser or game launch.
// Links resolve from art/verification, where root promotes the page after review.
// node tools/prepare-v12-main-review.cjs [--check-only]
// BORROWED_LIGHT_NATIVE_QA selects a later final native session if required.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const verification = path.join(root, 'art/verification');
const output = path.join(verification, 'v12-release-draft/visual-review.html');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const number = value => Number(value.toFixed(4)).toString();
const links = new Set(), displayedImages = [];
function file(relative) {
  assert(typeof relative === 'string' && relative && !path.isAbsolute(relative) && !relative.includes('\\') && !/^[a-z][a-z\d+.-]*:/i.test(relative), 'Expected a relative evidence link.');
  const absolute = path.resolve(verification, relative), within = path.relative(root, absolute);
  assert(within && !path.isAbsolute(within) && within !== '..' && !within.startsWith('..' + path.sep), 'Evidence must stay in workspace: ' + relative);
  assert(fs.existsSync(absolute) && fs.statSync(absolute).isFile() && fs.statSync(absolute).size > 0, 'Missing/empty evidence: ' + relative);
  return absolute;
}
const read = relative => fs.readFileSync(file(relative), 'utf8').replace(/^\uFEFF/, '');
const json = relative => JSON.parse(read(relative));
const sha = relative => crypto.createHash('sha256').update(fs.readFileSync(file(relative))).digest('hex').toUpperCase();
const href = relative => { file(relative); links.add(relative); return escape(relative); };
const link = (relative, label) => `<a href="${href(relative)}">${escape(label)}</a>`;
function png(relative) {
  const bytes = fs.readFileSync(file(relative));
  assert(bytes.length >= 36 && bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))
    && bytes.toString('ascii', 12, 16) === 'IHDR' && bytes.toString('ascii', bytes.length - 8, bytes.length - 4) === 'IEND', 'Incomplete original PNG: ' + relative);
  const size = { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
  assert(size.width > 0 && size.height > 0, 'Invalid actual PNG dimensions: ' + relative);
  return size;
}
const sameSize = (a, b, label) => assert(a.width === b.width && a.height === b.height, 'Image dimensions differ: ' + label);
function acceptedDecision(relative) {
  const decision = json(relative);
  assert(decision.reviewed === true && decision.accepted === true, 'Require an accepted reviewed decision: ' + relative);
  assert(typeof decision.summary === 'string' && decision.summary.trim(), 'Missing decision summary: ' + relative);
  assert(Array.isArray(decision.limits) && decision.limits.every(item => typeof item === 'string' && item.trim()), 'Missing decision limits: ' + relative);
  assert(decision.aestheticObjectiveAchieved === false, 'This review must retain the unmet overall aesthetic objective.');
  return decision;
}

const nativeRun = process.env.BORROWED_LIGHT_NATIVE_QA || 'run-030-v12';
assert(/^run-\d+-v12$/.test(nativeRun), 'BORROWED_LIGHT_NATIVE_QA must name a v12 run such as run-030-v12.');
const nativePath = nativeRun + '/runtime-results.json', webPath = 'web-013-v12/runtime-results.json';
const native = json(nativePath), web = json(webPath);
// Native QA has individual assertions rather than a top-level passed field.
const nativeChecks = ['puzzleCompleted', 'menuKeyboardStart', 'pauseStopsMovement', 'resumeMovement', 'restartWorks',
  'endingReturnWorks', 'cabinCollisionWorks', 'walkwayGroundingWorks', 'boulderCollisionWorks',
  'observatoryGroundingWorks', 'observatoryInstrumentCollisionWorks', 'decorativeLeavesExcluded',
  'pierGroundingWorks', 'pierRailCollisionWorks', 'scrollZoomWorks'];
for (const key of nativeChecks) assert(native[key] === true, 'Normal native QA failed/missing: ' + key);
assert(Number.isFinite(native.walkingDistance) && native.walkingDistance > 0 && Math.abs(native.normalizedScrollStepMetres - 0.35) < 0.0001, 'Native movement/normalized scroll evidence incomplete.');
for (const key of ['width', 'height']) assert(Number.isInteger(native[key]) && native[key] > 0, 'Missing native dimensions: ' + key);
for (const key of ['passed', 'realKeyboardPuzzleCompletion', 'persistedProgressReload', 'crossOriginIsolated', 'audioContextResumeObserved', 'defaultBrowserAutoplayPolicy']) {
  assert(web[key] === true, 'Normal Web QA failed/missing: ' + key);
}
assert(Array.isArray(web.errors) && web.errors.length === 0, 'Normal Web QA errors missing/non-empty.');
for (const key of ['width', 'height']) assert(Number.isInteger(web[key]) && web[key] > 0, 'Missing Web dimensions: ' + key);
const nativeIdentityPath = nativeRun + '/build-evidence.json', webIdentityPath = 'web-013-v12/artifact-identity.json';
const nativeIdentity = json(nativeIdentityPath), webIdentity = json(webIdentityPath);
assert(/^build_[a-z0-9]+$/i.test(nativeIdentity.buildId) && !/study/i.test(nativeIdentity.mode || ''), 'Native normal-session build identity missing or diagnostic.');
assert(webIdentity.passed === true && /^build_[a-z0-9]+$/i.test(webIdentity.buildId) && webIdentity.declaredBuildMatches === true
  && webIdentity.requestedAllCurrentFiles === true && webIdentity.session === 'web-013-v12'
  && Array.isArray(webIdentity.files) && webIdentity.files.length === 4 && webIdentity.files.every(item => item.matches === true), 'Normal Web artifact identity incomplete.');
const nativeImagePath = nativeRun + '/07-walking.png';
const nativeSize = png(nativeImagePath);
sameSize(nativeSize, native, 'normal native walking image versus runtime record');

const grassDir = 'v12-grass-refined', groundDir = 'v12-ground-detail-refined';
const grassDecisionPath = grassDir + '/decision.json', groundDecisionPath = groundDir + '/decision.json';
const grassDecision = acceptedDecision(grassDecisionPath), groundDecision = acceptedDecision(groundDecisionPath);
assert(groundDecision.selectedVariant === 'detail-soft' && Math.abs(groundDecision.strength - 0.35) < 0.0001, 'Expected the reviewed 0.35 detail-soft selection.');
const capturePath = grassDir + '/capture-condition-comparison.json', importPath = grassDir + '/unity-import-comparison.json';
const capture = json(capturePath), imported = json(importPath);
assert(capture.passed === true && capture.sceneMatch === true && capture.viewMatch === true && capture.lightsMatch === true && capture.bothStable === true, 'Grass fixed-capture comparison incomplete.');
assert(imported.passed === true && imported.anchorsUnchanged === true && imported.nonTargetUnchanged === true
  && imported.allMaterialsUnchanged === true && imported.allTransformsUnchanged === true && imported.targetChangesPresent === true,
  'Grass Unity preservation comparison incomplete.');
assert(imported.trianglesBefore === grassDecision.trianglesBefore && imported.trianglesAfter === grassDecision.trianglesAfter, 'Grass triangle records disagree.');
const grassStudy = json(grassDir + '/material-study.json');
const grassBaselineStudy = json('v11-plants-candidate/material-study.json');
assert(grassStudy.allInvariantsPassed === true && grassBaselineStudy.allInvariantsPassed === true, 'Grass material study incomplete.');
const groundStudyPath = groundDir + '/ground-detail-study.json';
const groundStudy = json(groundStudyPath);
assert(groundStudy.allInvariantsPassed === true && Array.isArray(groundStudy.views) && groundStudy.views.length === 15, 'Require all fifteen refined ground study views.');
assert(Number.isFinite(groundStudy.tileMetres) && groundStudy.tileMetres > 0
  && Math.abs(groundDecision.tileMetres - groundStudy.tileMetres) < 0.0001, 'Ground tile parameter disagrees with decision.');
const variants = ['baseline', 'detail', 'detail-soft', 'normal-only', 'baseline-repeat'];
assert(Array.isArray(groundStudy.variants) && groundStudy.variants.length === 5 && variants.every(variant => groundStudy.variants.includes(variant)), 'Unexpected ground study variants.');
const views = ['path', 'roots', 'lamp'], groundImages = new Map();
for (const view of views) for (const variant of variants) {
  const image = view + '-' + variant + '.png';
  const matches = groundStudy.views.filter(row => row.image === image && row.variant === variant);
  assert(matches.length === 1, 'Ground view missing/duplicated: ' + image);
  const row = matches[0], relative = groundDir + '/' + image, size = png(relative);
  assert(row.sceneUnchanged === true && row.otherMaterialsUnchanged === true && row.baseTexturesUnchanged === true, 'Ground invariant failed: ' + image);
  assert(Number.isFinite(row.detailStrength) && Number.isFinite(row.normalScale), 'Ground parameters missing: ' + image);
  sameSize(size, { width: groundStudy.screenWidth, height: groundStudy.screenHeight }, image);
  sameSize(size, { width: row.actualPNGWidth, height: row.actualPNGHeight }, image + ' per-view record');
  if (variant === groundDecision.selectedVariant) assert(Math.abs(row.detailStrength - groundDecision.strength) < 0.0001
    && Math.abs(row.normalScale - groundDecision.normalScale) < 0.0001, 'Selected ground parameters differ: ' + image);
  groundImages.set(image, { relative, row, size });
}
// The original ground A/B images used RGBA32. They cannot stand in for the
// later native-only compressed importer review or identify the final player.
const compressionDir = 'v12-ground-compression';
const compressionDecisionPath = compressionDir + '/decision.json';
const compressionStudyPath = compressionDir + '/ground-detail-study.json';
const compressionIdentityPath = compressionDir + '/build-evidence.json';
const compressionImportPath = compressionDir + '/unity-import.json';
const compressionDecision = acceptedDecision(compressionDecisionPath);
const compressionStudy = json(compressionStudyPath), compressionIdentity = json(compressionIdentityPath), compressionImport = json(compressionImportPath);
assert(compressionDecision.windowsBuild === compressionIdentity.buildId && compressionIdentity.buildId === nativeIdentity.buildId
  && compressionIdentity.mode === 'GroundDetailStudy', 'Select final compressed native QA with BORROWED_LIGHT_NATIVE_QA; compression and normal player identities must agree.');
const nativeFiles = new Map((nativeIdentity.files || []).map(item => [item.name.replace(/\\/g, '/'), item.sha256]));
assert(nativeFiles.size === 4 && compressionIdentity.files?.length === 4 && compressionIdentity.files.every(item =>
  /^[a-f0-9]{64}$/i.test(item.sha256) && item.sha256.toUpperCase() === nativeFiles.get(item.name.replace(/\\/g, '/'))?.toUpperCase()), 'Compressed study and native QA file hashes differ.');
assert(compressionDecision.selectedVariant === groundDecision.selectedVariant && Math.abs(compressionDecision.strength - groundDecision.strength) < 0.0001
  && Math.abs(compressionDecision.normalScale - groundDecision.normalScale) < 0.0001
  && Math.abs(compressionDecision.tileMetres - groundStudy.tileMetres) < 0.0001, 'Compressed study selection parameters differ.');
assert(compressionStudy.allInvariantsPassed === true && compressionStudy.views?.length === 15, 'Compression study incomplete.');
assert(compressionStudy.detailMap?.format === 'DXT1' && compressionImport.format === 'DXT1' && compressionStudy.detailMap.width === compressionImport.width
  && compressionStudy.detailMap.height === compressionImport.height && compressionStudy.detailMap.mipCount === compressionImport.mips, 'Compressed runtime texture differs from import record.');
const originalSHA = sha('../generated/ground-v12/earth-detail-original.png');
assert(originalSHA === sha('../../GameProject/Assets/BorrowedLight/Resources/Textures/GroundDetailV12.png')
  && [compressionStudy.originalSHA256, groundStudy.originalSHA256, compressionDecision.textureSHA256, compressionImport.sourceSHA256].every(value => value?.toUpperCase() === originalSHA), 'Original ground PNG identity differs.');
const textureMeta = read('../../GameProject/Assets/BorrowedLight/Resources/Textures/GroundDetailV12.png.meta');
function platformSettings(name) {
  const block = textureMeta.split(/\n  - serializedVersion:/).find(text => new RegExp('buildTarget:\\s*' + name + '(?:\\s|$)').test(text));
  assert(block, 'Current texture platform missing: ' + name);
  const value = key => { const match = block.match(new RegExp('^\\s*' + key + ':\\s*(-?\\d+)', 'm')); assert(match, 'Platform parameter missing: ' + name + '/' + key); return Number(match[1]); };
  return { overridden: value('overridden'), format: value('textureFormat'), maxSize: value('maxTextureSize') };
}
const standaloneSettings = platformSettings('Standalone'), webSettings = platformSettings('WebGL');
assert(standaloneSettings.overridden === 1 && standaloneSettings.format === 10 && standaloneSettings.maxSize === compressionImport.width,
  'Current native import no longer matches reviewed DXT1 texture.');
assert(groundStudy.detailMap?.format === 'RGBA32' && webSettings.overridden === 1 && webSettings.format === 4
  && webSettings.maxSize >= Math.max(groundStudy.detailMap.width, groundStudy.detailMap.height), 'Original RGBA32/Web import configuration differs.');
for (const view of views) {
  const image = view + '-' + groundDecision.selectedVariant + '.png';
  const matches = compressionStudy.views.filter(row => row.image === image && row.variant === groundDecision.selectedVariant);
  assert(matches.length === 1, 'Compressed selected image missing/duplicated: ' + image);
  const row = matches[0], size = png(compressionDir + '/' + image), baseline = groundImages.get(image);
  assert(row.sceneUnchanged === true && row.otherMaterialsUnchanged === true && row.baseTexturesUnchanged === true,
    'Compressed image invariant failed: ' + image);
  sameSize(size, baseline.size, 'compression original pair ' + view);
  sameSize(size, { width: row.actualPNGWidth, height: row.actualPNGHeight }, 'compression per-view record ' + view);
  assert(Math.abs(row.detailStrength - groundDecision.strength) < 0.0001 && Math.abs(row.normalScale - groundDecision.normalScale) < 0.0001,
    'Compressed image material parameters differ: ' + image);
}
const originalFormat = `${groundStudy.detailMap.width} × ${groundStudy.detailMap.height} ${groundStudy.detailMap.format}`;
const nativeFormat = `${compressionStudy.detailMap.width} × ${compressionStudy.detailMap.height} ${compressionStudy.detailMap.format}`;
const grassImages = new Map();
for (const view of views) {
  const image = view + '-fixed40.png';
  for (const [folder, study] of [['v11-plants-candidate', grassBaselineStudy], [grassDir, grassStudy]]) {
    const relative = folder + '/' + image, size = png(relative);
    const rows = study.views?.filter(row => row.image === image && row.variant === 'fixed40');
    assert(rows?.length === 1 && rows[0].transformsAndLightsUnchanged === true && Number.isFinite(rows[0].fieldOfView), 'Grass capture row incomplete: ' + relative);
    sameSize(size, study, relative + ' capture dimensions');
    grassImages.set(relative, { relative, size, row: rows[0] });
  }
  sameSize(grassImages.get('v11-plants-candidate/' + image).size, grassImages.get(grassDir + '/' + image).size, 'grass ' + view);
}

const template = read('visual-review-v11.html');
const style = template.match(/<style\b[^>]*>[\s\S]*?<\/style>/i)?.[0];
const dialog = template.match(/<dialog\b[^>]*>[\s\S]*?<\/dialog>/i)?.[0];
assert(style && dialog, 'Reviewed CSS/original-image dialog template missing.');
function figure(relative, title, caption, label, reference = false) {
  const size = png(relative), url = href(relative);
  displayedImages.push(relative);
  return `<figure><div class="card-top"><span class="source ${reference ? 'reference' : 'ours'}">${escape(label)}</span><span class="resolution">${size.width} × ${size.height} · 原图</span></div><a class="picture" href="${url}" data-title="${escape(title)}" data-width="${size.width}" data-height="${size.height}"><img src="${url}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)}</strong>${escape(caption)}<div class="file">${escape(relative)}</div></figcaption></figure>`;
}
const titles = { path: '路径完整画面', roots: '岩脚与草根', lamp: '灯座近景' };
const normalSection = `<section><div class="section-head"><h2>01 / 参考与 v12 正常游戏</h2><p class="section-note">不同作品、日夜与构图，不是受控 A/B。</p></div><div class="grid">${figure('../reference/littleprince-gameplay.png', '参考网站 · 实际游玩画面', '仅作本地视觉研究。草地、角色与环境关系仍是本作需要继续改善的部分。', '参考 / Saccc_c', true)}${figure(nativeImagePath, '借光岛 v12 · 正常游戏漫步视角', '本次 Windows 正常运行：新草形与低强度地面细节合用；细节纹理导入为 ' + nativeFormat + '。该原图不单独证明移动画面稳定或整体视觉超过参考。', '本作 / 正常游戏')}</div><p class="section-note"><a href="https://littleprince.dev/">参考原网站</a> · <a href="https://x.com/Saccc_c/status/2110694725640474759">原推文</a> · ${link(nativePath, 'Windows 正常检查')} · ${link(webPath, '网页正常检查')}</p></section>`;
const grassSections = views.map((view, index) => {
  const baseline = grassImages.get('v11-plants-candidate/' + view + '-fixed40.png');
  const candidate = grassImages.get(grassDir + '/' + view + '-fixed40.png');
  const caption = image => '原地面，未启用 v12 地面颜色细节；记录视场角 ' + number(image.row.fieldOfView) + '°。';
  return `<section><div class="section-head"><h2>0${index + 2} / 草形 · ${titles[view]}</h2><p class="section-note">v11 与 refined 新草同机位；本组两图均保留原地面，不能把后续材质收益归因于草形。</p></div><div class="grid">${figure(baseline.relative, 'v11 草形基线 · ' + view, caption(baseline), 'v11 / 草形基线')}${figure(candidate.relative, 'v12 refined 草形 · ' + view, caption(candidate), 'v12 / 已采用草形')}</div></section>`;
}).join('\n');
const groundSections = views.map((view, index) => {
  const baseline = groundImages.get(view + '-baseline.png');
  const chosen = groundImages.get(view + '-' + groundDecision.selectedVariant + '.png');
  const caption = image => '同一新草模型；颜色细节强度 ' + number(image.row.detailStrength) + '，原法线强度 ' + number(image.row.normalScale)
    + (image.row.variant === groundDecision.selectedVariant ? '，平铺尺度 ' + number(groundStudy.tileMetres) + ' m。' : '。');
  return `<section><div class="section-head"><h2>0${index + 5} / 地面 · ${titles[view]}</h2><p class="section-note">同一 refined 会话、同一新草模型，仅切换地面材质变体；细节候选使用 ${escape(originalFormat)}，不是最终 Windows 压缩配置的截图。</p></div><div class="grid">${figure(baseline.relative, '新草＋原地面 · ' + view, caption(baseline), '地面 / 原材质基线')}${figure(chosen.relative, '新草＋低强度地面细节 · ' + view, caption(chosen), '地面 / RGBA32 静态采用')}</div></section>`;
}).join('\n');
const grassEvidence = [link(grassDecisionPath, '草形采用决定'), link(capturePath, '同机位与灯光对照'), link(importPath, 'Unity 导入对照'),
  link(grassDir + '/visual-review-world-v10.json', '草形作者图评')].join(' · ');
const groundEvidence = [link('visual-review-v12-ground.html', '地面独立对照页与备选原图'), link(groundDecisionPath, '地面采用决定'),
  link(groundStudyPath, '十五图记录与实际参数'), link(groundDir + '/independent-review.json', '地面独立图评'),
  link('../generated/ground-v12/earth-detail-original.png', '生成的地面原图'), link('../generated/ground-v12/prompt.txt', '原图提示词')].join(' · ');
const compressionEvidence = [link(compressionDecisionPath, 'Windows 压缩采用决定'), link(compressionImportPath, '实际导入与平台配置'),
  link(compressionStudyPath, '压缩运行采集记录'), link(compressionIdentityPath, '压缩采集产物身份'),
  link(compressionDir + '/independent-review.json', '六图独立审查'),
  ...views.map(view => link(compressionDir + '/' + view + '-detail-soft.png', 'DXT1 原图 · ' + view))].join(' · ');
const compressionParagraph = `<p>上面六张地面诊断图来自原 ${escape(originalFormat)} 会话；最终 Windows 正常图使用 ${escape(nativeFormat)}，另有压缩对照与采用决定。Web 导入配置仍保留 ${escape(originalFormat)}。源 PNG 字节不变，Windows 引擎导入包含缩小和有损压缩，不声称两者画面完全一致。</p><p>${escape(compressionDecision.summary)}</p><p>${compressionEvidence}</p><p>压缩质量图评不证明帧率提升，正常运行短样本也不单独建立纹理压缩与性能变化的完整因果关系。</p>`;
const limits = [...new Set([...grassDecision.limits, ...groundDecision.limits, ...compressionDecision.limits])];
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v12 · 实机、草形与地面对照</title>${style}</head>
<body><main><header><div class="eyebrow">Borrowed Light · v12 visual evidence</div><h1>借光岛 v12 · 实机、草形与地面对照</h1><p class="lede">本轮采用保留低层覆盖的新草形，以及强度 ${number(groundDecision.strength)} 的地面颜色细节。正常游戏图展示两项合用；随后六组固定机位分别呈现草形与地面的局部收益和不足。</p><p class="lede">整体视觉超过参考网站的目标尚未达到。Windows 与网页功能记录另附；静态截图和功能通关不代表全部动态效果、性能或整体美术验收通过。</p><div class="tags"><span class="tag">十四张完整原图</span><span class="tag">草形与地面分组对照</span><span class="tag">原生 ${native.width} × ${native.height}</span><span class="tag">网页 ${web.width} × ${web.height}</span></div></header>
${normalSection}
${grassSections}
${groundSections}
<aside class="review"><div><h2>Windows 纹理导入的单独审查</h2>${compressionParagraph}</div></aside>
<aside class="review"><div><h2>采用范围与证据</h2><p>${escape(grassDecision.summary)}</p><p>${grassEvidence}</p><p>${escape(groundDecision.summary)}</p><p>${groundEvidence}</p><p>草形诊断中只更新目标草类网格，材质保护范围以导入记录为准；正常游戏同时接入新的地面着色器及运行时材质。本页不声称全部程序、着色器或材质未变。</p><p>正常运行记录：Windows ${escape(nativeIdentity.buildId)}，网页 ${escape(webIdentity.buildId)}。${link(nativeIdentityPath, '原生采集身份记录')} · ${link(webIdentityPath, '网页产物身份记录')}。功能检查通过只表示所列测试项通过，不等同于全角度渲染检查或性能无回归。</p><p>地面是颜色细节，没有新增地形几何或细节法线。Time.timeScale 与冻结时间不会冻结全部逐帧随机项，不声称逐像素相同，也不把对照中所有差异归于单一参数。</p></div><ul class="criteria">${limits.map(item => `<li>${escape(item)}</li>`).join('')}<li>以上限制引用静态采用时的记录；正常运行结果以本页 ${escape(nativeRun)} 与 web-013-v12 链接为准。</li><li>十四张展示图均链接完整原始 PNG，没有裁切、调色、重绘或生成缩略图文件。</li><li>本版未新增行走录像审查；静态图不证明完整步态、动态闪烁或持续帧率。</li></ul></aside>
<footer>借光岛 v12 · 局部改善与正常运行证据 · 整体审美目标仍未完成</footer></main>${dialog}
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
assert(displayedImages.length === 14 && new Set(displayedImages).size === 14 && (html.match(/<img\s+src=/g) || []).length === 14, 'Expected exactly fourteen displayed original images.');
if (!checkOnly) { fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, html, 'utf8'); }
console.log(JSON.stringify({ checkOnly, output, images: displayedImages, imageCount: displayedImages.length,
  nativeQA: nativePath, webQA: webPath, acceptedDecisions: [grassDecisionPath, groundDecisionPath],
  selectedGroundVariant: groundDecision.selectedVariant, groundStrength: groundDecision.strength,
  nativeDetailFormat: nativeFormat, originalGroundStudyFormat: originalFormat, compressionDecision: compressionDecisionPath,
  localLinksChecked: links.size, linkBaseAfterPromotion: 'art/verification/', aestheticObjectiveAchieved: false }, null, 2));
