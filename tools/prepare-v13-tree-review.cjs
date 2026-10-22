'use strict';

// Independent three-column static review; never changes the stable review page.
// node tools/prepare-v13-tree-review.cjs [--check-only]
const fs = require('node:fs'), path = require('node:path');
const verification = path.resolve(__dirname, '../art/verification');
const output = path.join(verification, 'visual-review-v13-trees.html');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const assert = (value, message) => { if (!value) throw new Error(message); };
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
const views = ['path', 'island', 'left-tree', 'gold-tree', 'right-pine'];
const names = { path: '正常路径构图', island: '全岛构图', 'left-tree': '左阔叶', 'gold-tree': '金树与金环', 'right-pine': '右侧针叶树' };
const targets = ['Garden_TreeTrunks', 'Garden_TreeCanopies', 'Garden_CanopyLeafEdges'].sort();
const columns = [
  { folder: 'v13-trees-baseline', world: 'world-v10', label: '原版基线', baseline: true },
  { folder: 'v13-trees-candidate', world: 'world-v11', label: '首版候选' },
  { folder: 'v13-trees-refined', world: 'world-v12', label: '修正版候选' }
];
const links = new Set(), images = new Map();
function file(relative) {
  assert(typeof relative === 'string' && relative && !path.isAbsolute(relative) && !relative.includes('\\')
    && !relative.split('/').includes('..') && !/^[a-z][a-z\d+.-]*:/i.test(relative), 'Expected a local verification path.');
  const absolute = path.join(verification, relative);
  assert(fs.existsSync(absolute) && fs.statSync(absolute).isFile() && fs.statSync(absolute).size > 0, 'Missing/empty input: ' + relative);
  return absolute;
}
const read = relative => fs.readFileSync(file(relative), 'utf8').replace(/^\uFEFF/, '');
const json = relative => JSON.parse(read(relative));
const link = (relative, label) => { file(relative); links.add(relative); return `<a href="${escape(relative)}">${escape(label)}</a>`; };
function png(relative) {
  const bytes = fs.readFileSync(file(relative));
  assert(bytes.length >= 36 && bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))
    && bytes.toString('ascii', 12, 16) === 'IHDR' && bytes.toString('ascii', bytes.length - 8, bytes.length - 4) === 'IEND', 'Incomplete original PNG: ' + relative);
  const size = { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
  assert(size.width > 0 && size.height > 0, 'Invalid PNG dimensions: ' + relative);
  images.set(relative, size); return size;
}
function close(a, b) {
  if (typeof a === 'number' && typeof b === 'number') return Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) < 1e-5;
  if (a && b && typeof a === 'object' && typeof b === 'object') {
    const keys = Object.keys(a); return keys.length === Object.keys(b).length && keys.every(key => Object.hasOwn(b, key) && close(a[key], b[key]));
  }
  return a === b;
}
const pick = (object, keys) => Object.fromEntries(keys.map(key => [key, object[key]]));
const byName = list => [...list].sort((a, b) => (a.name + '/' + (a.shader || '')).localeCompare(b.name + '/' + (b.shader || '')));
for (const column of columns) {
  const folder = column.folder, study = column.study = json(folder + '/material-study.json');
  const identity = column.identity = json(folder + '/build-evidence.json');
  assert(study.materialFamily === 'tree-geometry' && study.geometryStudy === true && study.allInvariantsPassed === true
    && study.completed === true && study.captureComplete === true && study.failed === false
    && study.expectedImageCount === 10 && study.completedImages === 10 && study.capturedImageCount === 10
    && Array.isArray(study.views) && study.views.length === 10, 'Tree session has not completed all ten invariant-checked captures: ' + folder);
  assert(Number.isInteger(study.width) && study.width > 0 && Number.isInteger(study.height) && study.height > 0, 'Missing actual frame dimensions: ' + folder);
  assert(Array.isArray(study.targetRenderers) && close([...study.targetRenderers].sort(), targets), 'Unexpected tree targets: ' + folder);
  assert(Array.isArray(study.materialConditions) && study.materialConditions.length > 0 && Array.isArray(study.lights) && study.lights.length > 0,
    'Material/light records missing: ' + folder);
  assert(identity.mode === 'TreeStudy' && /^build_[a-z0-9]+$/i.test(identity.buildId), 'Expected TreeStudy player identity: ' + folder);
  const seen = new Set();
  for (const view of views) for (const variant of ['current', 'repeat']) {
    const image = view + '-' + variant + '.png', matches = study.views.filter(row => row?.image === image && row.variant === variant);
    assert(matches.length === 1, 'Missing/duplicate image row: ' + folder + '/' + image);
    const row = matches[0], size = png(folder + '/' + image); seen.add(image);
    assert(row.transformsAndLightsUnchanged === true && row.materialsUnchanged === true, 'Per-view invariant failed: ' + folder + '/' + image);
    assert(size.width === study.width && size.height === study.height && row.actualPNGWidth === size.width && row.actualPNGHeight === size.height,
      'Recorded/actual PNG dimensions differ: ' + folder + '/' + image);
    assert(row.cameraPosition && row.cameraRotation && row.lookTarget && Number.isFinite(row.fieldOfView), 'Camera record incomplete: ' + image);
  }
  assert(seen.size === 10, 'Unexpected repeated image record: ' + folder);
  if (column.baseline) continue;
  const decision = column.decision = json(folder + '/decision.json');
  assert(typeof decision.accepted === 'boolean' && decision.candidateWorld === column.world && decision.candidateGame === 'v13', 'Missing/wrong-world visual decision: ' + folder);
  // The existing root decision records an explicit reviewer and five originals,
  // without a separate reviewed flag. Accept that exact evidence convention.
  assert((decision.reviewed === true || (typeof decision.reviewer === 'string' && decision.reviewer.trim()))
    && Array.isArray(decision.reviewedOriginals) && views.every(view => decision.reviewedOriginals.includes(view + '-current.png')),
    'Decision needs an explicit review of all five current originals: ' + folder);
  assert(decision.buildId === identity.buildId && decision.baselineBuildId === columns[0].identity.buildId, 'Decision/capture build identity differs: ' + folder);
  assert(typeof decision.scope === 'string' && decision.scope.trim(), 'Decision scope missing: ' + folder);
  assert(typeof decision.summary === 'string' && decision.summary.trim()
    || [decision.improvements, decision.blockingProblems].some(list => Array.isArray(list) && list.some(item => typeof item === 'string' && item.trim())),
    'Decision has no substantive visual conclusion: ' + folder);
  if (column.world === 'world-v11') assert(decision.accepted === false, 'The preserved first candidate must remain rejected.');
  const capture = json(folder + '/capture-condition-comparison.json');
  const imported = json(folder + '/unity-import-comparison.json');
  assert(capture.passed === true && capture.sceneMatch === true && capture.viewMatch === true && capture.lightsMatch === true && capture.bothStable === true
    && ['completeCaptures', 'materialsMatch', 'ambientMatch', 'targetsMatch', 'viewDetailsMatch'].every(key => capture.treeConditions?.[key] === true),
    'Tree capture comparison incomplete: ' + folder);
  assert(imported.passed === true && imported.anchorsUnchanged === true && imported.nonTargetUnchanged === true && imported.allMaterialsUnchanged === true
    && imported.allTransformsUnchanged === true && imported.targetChangesPresent === true, 'Tree Unity preservation check incomplete: ' + folder);
}
// Independently compare the recorded conditions across all three columns. This
// compares declared conditions; build/import evidence supplies asset identity.
const baseline = columns[0].study;
for (const column of columns.slice(1)) {
  const study = column.study;
  assert(close(pick(baseline, ['width', 'height', 'frozenTime', 'night', 'ambientSky', 'ambientEquator', 'ambientGround', 'ambientIntensity', 'ambientMode']),
    pick(study, ['width', 'height', 'frozenTime', 'night', 'ambientSky', 'ambientEquator', 'ambientGround', 'ambientIntensity', 'ambientMode'])), 'Recorded scene/ambient conditions differ: ' + column.folder);
  assert(close(byName(baseline.lights), byName(study.lights)) && close(byName(baseline.materialConditions), byName(study.materialConditions)), 'Recorded light/material conditions differ: ' + column.folder);
  const cameraKeys = ['cameraPosition', 'cameraRotation', 'lookTarget', 'fieldOfView', 'actualPNGWidth', 'actualPNGHeight'];
  for (const row of baseline.views) {
    const other = study.views.find(item => item.image === row.image && item.variant === row.variant);
    assert(other && close(pick(row, cameraKeys), pick(other, cameraKeys)), 'Recorded camera/image conditions differ: ' + column.folder + '/' + row.image);
  }
}
const template = read('visual-review-v10.html');
const style = template.match(/<style\b[^>]*>[\s\S]*?<\/style>/i)?.[0];
const dialog = template.match(/<dialog\b[^>]*>[\s\S]*?<\/dialog>/i)?.[0];
assert(style && dialog, 'Original-image CSS/dialog template missing.');
const status = column => column.baseline ? '对照基线，无本轮采用决定' : column.decision.accepted ? '静态图评采用' : '静态图评未采用';
function figure(column, view) {
  const relative = column.folder + '/' + view + '-current.png', size = images.get(relative);
  const row = column.study.views.find(item => item.image === view + '-current.png');
  const title = column.world + ' · ' + names[view];
  links.add(relative);
  return `<figure><div class="card-top"><span class="source ours">${escape(column.world)} / ${escape(column.label)}</span><span class="resolution">${size.width} × ${size.height} · 原图</span></div><a class="picture" href="${relative}" data-title="${escape(title)}" data-width="${size.width}" data-height="${size.height}"><img src="${relative}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)} · ${escape(status(column))}</strong>视场角 ${row.fieldOfView}°；采集及导入检查与美术采用分别判断。<div class="file">${relative}</div><div>${link(column.folder + '/' + view + '-repeat.png', '同机位复拍原图')}</div></figcaption></figure>`;
}
const sections = views.map((view, index) => `<section><div class="section-head"><h2>0${index + 1} / ${names[view]}</h2><p class="section-note">三版同机位完整原图；点击查看原始尺寸。</p></div><div class="grid three">${columns.map(column => figure(column, view)).join('')}</div></section>`).join('\n');
function decisionText(decision) {
  const lists = [['改善记录', decision.improvements], ['阻断或不足', decision.blockingProblems], ['限制', decision.limitations ?? decision.limits]];
  return (decision.summary ? `<p>${escape(decision.summary)}</p>` : '') + lists.filter(([, list]) => Array.isArray(list) && list.length)
    .map(([label, list]) => `<p>${label}：</p><ul>${list.map(item => `<li>${escape(item)}</li>`).join('')}</ul>`).join('');
}
const evidence = columns.map(column => `<div><h2>${escape(column.world)} · ${escape(status(column))}</h2><p>采集记录核对完成：${column.study.completedImages}/${column.study.expectedImageCount}；逐图不变量与完整 PNG 尺寸通过。此处“通过”不代表视觉采用。</p><p>${link(column.folder + '/material-study.json', '完整采集与条件记录')} · ${link(column.folder + '/build-evidence.json', '采集产物身份')}</p>${column.baseline ? '' : `<p>${link(column.folder + '/decision.json', '根代理的视觉决定')} · ${link(column.folder + '/capture-condition-comparison.json', '同机位条件对照')} · ${link(column.folder + '/unity-import-comparison.json', 'Unity 导入保护对照')}</p>${decisionText(column.decision)}<p>范围：${escape(column.decision.scope)}</p>`}</div>`).join('');
const independent = link('v13-trees-candidate/independent-review.json', '首版五对原图的独立拒绝意见');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v13 · 三版树木固定机位对照</title>${style}<style>.grid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.evidence-columns{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.evidence-columns>div{min-width:0}.evidence-columns ul{padding-left:20px}.evidence-columns p,.evidence-columns li{overflow-wrap:anywhere}@media(max-width:1100px){.grid.three,.evidence-columns{grid-template-columns:1fr}}</style></head>
<body><main><header><div class="eyebrow">Borrowed Light · Tree geometry study</div><h1>v13 树木 · 原版、首版与修正版</h1><p class="lede">五组固定机位，左为 world-v10 基线，中为未采用的 world-v11，右为 world-v12 修正版。所有列的采集与条件检查均须完成；视觉采用结果来自各自决定，不能以导入或计数通过代替。</p><div class="tags"><span class="tag">十五张展示原图</span><span class="tag">每列十张采集含复拍</span><span class="tag">修正版：${escape(status(columns[2]))}</span></div><p class="lede">只审查树形、叶团和遮挡的静态局部差异。整体视觉超过参考的目标尚未建立；此页独立于稳定版实机对照页。</p></header>
${sections}
<aside class="review"><div><h2>采集与视觉结论分开查看</h2><p>${independent}</p><div class="evidence-columns">${evidence}</div><p>贴图名称和材质参数记录不是源文件内容哈希；模型与产物身份以所附导入及构建证据为准。参考截图本身没有成熟树冠，不能据此宣称复刻参考树形。</p><p>Time.timeScale 与冻结时间不会冻结全部时域 AO 或随机项。复拍是静态重复采集，不是动态录像；不声称逐像素相同。</p><p>不验收风摆、移动闪烁、性能、碰撞、正常游戏流程或完整游戏审美。未裁切、调色、重绘或生成缩略图文件。</p></div></aside><footer>借光岛 v13 · 独立树木诊断页 · 静态结果不等同于正式发布</footer></main>${dialog}
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
assert((html.match(/<img\s+src=/g) || []).length === 15 && images.size === 30, 'Expected fifteen displayed originals and thirty checked current/repeat PNGs.');
if (!checkOnly) fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({checkOnly, output, displayedImages:15, completePNGsChecked:images.size, localLinksChecked:links.size,
  columns:columns.map(column => ({folder:column.folder,world:column.world,buildId:column.identity.buildId,status:status(column)})),
  scope:'Independent static tree study; does not replace visual-review.html or establish release/overall aesthetic acceptance.'}, null, 2));
