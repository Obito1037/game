'use strict';

// Ground-only refined-session review. Writes no stable page or production assets.
// node tools/prepare-v12-ground-review.cjs [--check-only]
const fs = require('node:fs'), path = require('node:path');
const verification = path.resolve(__dirname, '../art/verification');
const folder = 'v12-ground-detail-refined';
const output = path.join(verification, 'visual-review-v12-ground.html');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const assert = (value, message) => { if (!value) throw new Error(message); };
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
function file(relative) {
  assert(typeof relative === 'string' && !path.isAbsolute(relative) && !relative.includes('\\') && !relative.split('/').includes('..'), 'Expected a local review path.');
  const absolute = path.join(verification, relative);
  assert(fs.existsSync(absolute) && fs.statSync(absolute).isFile() && fs.statSync(absolute).size > 0, 'Required input missing/empty: ' + relative);
  return absolute;
}
const read = relative => fs.readFileSync(file(relative), 'utf8').replace(/^\uFEFF/, '');
const studyPath = folder + '/ground-detail-study.json', decisionPath = folder + '/decision.json';
const record = JSON.parse(read(studyPath)), decision = JSON.parse(read(decisionPath));
assert(record.allInvariantsPassed === true && Array.isArray(record.views) && record.views.length === 15, 'Require all 15 completed views with passing invariants.');
assert(Number.isInteger(record.screenWidth) && record.screenWidth > 0 && Number.isInteger(record.screenHeight) && record.screenHeight > 0, 'Missing recorded dimensions.');
assert(Number.isFinite(record.tileMetres) && record.tileMetres > 0, 'Missing actual detail tile size.');
assert(decision.reviewed === true && typeof decision.accepted === 'boolean', 'Decision requires reviewed:true and accepted:boolean.');
assert(['detail', 'detail-soft'].includes(decision.selectedVariant), 'Only detail or detail-soft may be selected.');
assert(typeof decision.summary === 'string' && decision.summary.trim(), 'Missing decision summary.');
assert(Array.isArray(decision.limits) && decision.limits.every(v => typeof v === 'string' && v.trim()), 'Decision limits must be a string array.');
const variants = ['baseline', 'detail', 'detail-soft', 'normal-only', 'baseline-repeat'];
assert(Array.isArray(record.variants) && record.variants.length === 5 && new Set(record.variants).size === 5 && variants.every(v => record.variants.includes(v)), 'Unexpected recorded variants.');
const views = ['path', 'roots', 'lamp'], images = new Map();
for (const view of views) for (const variant of variants) {
  const name = view + '-' + variant + '.png';
  const matches = record.views.filter(row => row?.image === name && row.variant === variant);
  assert(matches.length === 1, 'Missing/duplicate actual view record: ' + name);
  const row = matches[0];
  assert(row.sceneUnchanged === true && row.otherMaterialsUnchanged === true && row.baseTexturesUnchanged === true, 'Per-view invariant failed: ' + name);
  assert(Number.isFinite(row.detailStrength) && Number.isFinite(row.normalScale), 'Missing actual material parameters: ' + name);
  const relative = folder + '/' + name, bytes = fs.readFileSync(file(relative));
  assert(bytes.length >= 36 && bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) && bytes.toString('ascii', 12, 16) === 'IHDR' && bytes.toString('ascii', bytes.length - 8, bytes.length - 4) === 'IEND', 'Missing complete original PNG: ' + name);
  const width = bytes.readUInt32BE(16), height = bytes.readUInt32BE(20);
  assert(width === record.screenWidth && height === record.screenHeight && row.actualPNGWidth === width && row.actualPNGHeight === height, 'Recorded/actual PNG dimensions differ: ' + name);
  images.set(name, { relative, row, width, height });
}
assert(new Set(record.views.map(row => row.image)).size === 15, 'Unexpected repeated image record.');
const template = read('visual-review-v10.html');
const style = template.match(/<style\b[^>]*>[\s\S]*?<\/style>/i)?.[0];
const dialog = template.match(/<dialog\b[^>]*>[\s\S]*?<\/dialog>/i)?.[0];
assert(style && dialog, 'Original-image CSS/dialog template missing.');
const number = value => Number(value.toFixed(4)).toString();
const labels = { baseline: '原地面基线', detail: '细节颜色', 'detail-soft': '低强度细节颜色', 'normal-only': '仅法线候选', 'baseline-repeat': '基线复拍' };
function parameters(image) {
  return '颜色细节强度 ' + number(image.row.detailStrength) + ' · 法线强度 ' + number(image.row.normalScale)
    + (['detail', 'detail-soft'].includes(image.row.variant) ? ' · 记录平铺尺度 ' + number(record.tileMetres) + ' m' : '');
}
function figure(view, variant) {
  const image = images.get(view + '-' + variant + '.png');
  const title = labels[variant] + ' · ' + view;
  return `<figure><div class="card-top"><span class="source ours">${escape(labels[variant])}</span><span class="resolution">${image.width} × ${image.height} · 原图</span></div><a class="picture" href="${image.relative}" data-title="${escape(title)}"><img src="${image.relative}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)}</strong>${escape(parameters(image))}<div class="file">${image.relative}</div></figcaption></figure>`;
}
function imageLink(view, variant) {
  const image = images.get(view + '-' + variant + '.png');
  return `<a href="${image.relative}">${escape(labels[variant])}（${escape(parameters(image))}）</a>`;
}
const titles = { path: '01 / 路径完整画面', roots: '02 / 岩脚与草根', lamp: '03 / 灯座近景' };
const sections = views.map(view => `<section><div class="section-head"><h2>${titles[view]}</h2><p class="section-note">同一 refined 采集中的基线与审阅变体</p></div><div class="grid">${figure(view, 'baseline')}${figure(view, decision.selectedVariant)}</div><p class="section-note">备选原图：${['detail', 'detail-soft', 'normal-only', 'baseline-repeat'].map(v => imageLink(view, v)).join(' · ')}</p></section>`).join('\n');
const selection = decision.accepted ? '仅在所审静态范围采用' : '本候选未采用';
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v12 · 地面材质固定机位对照</title>${style}</head>
<body><main><header><div class="eyebrow">Borrowed Light · Refined ground material study</div><h1>地面材质 · v12 固定机位对照</h1><p class="lede">${escape(decision.summary)}</p><p class="lede">仅展示本次 refined 会话的原图及记录参数，不混用旧模型会话的十二张图。本页不是正常游戏、动态闪烁、性能或整体视觉优于参考的验收。</p><div class="tags"><span class="tag">${selection}</span><span class="tag">审阅变体 ${escape(decision.selectedVariant)}</span><span class="tag">${record.screenWidth} × ${record.screenHeight} 原图</span></div></header>
${sections}
<aside class="review"><div><h2>判断与证据边界</h2><p>${escape(decision.summary)}</p><p><a href="${studyPath}">十五张采集记录与实际参数</a> · <a href="${decisionPath}">图评决定与采用范围</a></p><p>工具核对十五张完整 PNG 的尺寸及逐图记录；sceneUnchanged、otherMaterialsUnchanged、baseTexturesUnchanged 均需为 true 才能生成此页。该记录不代替动态测试。</p><p>Time.timeScale 与冻结时间不会冻结全部逐帧随机项，不声称复拍逐像素相同，也不将差异全部归于单一材质参数。</p></div><ul class="criteria">${decision.limits.map(item => `<li>${escape(item)}</li>`).join('')}<li>原图没有裁切、调色、重绘或生成缩略图文件。</li><li>静态材质对照不证明帧率、完整游戏体验或整体审美目标达成。</li></ul></aside>
<footer>借光岛 · 本地独立地面诊断页 · 保留备选原图与限制</footer></main>${dialog}
<script>
(function(){
 const dialog=document.querySelector('dialog');
 document.querySelectorAll('.picture').forEach(function(link){
  const img=link.querySelector('img'),badge=link.closest('figure').querySelector('.resolution'),state=link.querySelector('.image-state');
  function loaded(){link.classList.add('loaded');link.classList.remove('missing');badge.textContent=img.naturalWidth+' × '+img.naturalHeight+' · 原图';}
  function missing(){link.classList.add('missing');badge.textContent='原图无法载入';state.textContent='请检查本地原图路径';}
  img.addEventListener('load',loaded);img.addEventListener('error',missing);if(img.complete){if(img.naturalWidth)loaded();else missing();}
  link.addEventListener('click',function(event){if(!img.naturalWidth||!dialog.showModal)return;event.preventDefault();dialog.querySelector('img').src=link.getAttribute('href');dialog.querySelector('img').alt=img.alt;dialog.querySelector('.dialog-bar span').textContent=link.dataset.title+' · '+img.naturalWidth+' × '+img.naturalHeight;dialog.querySelector('.original').href=link.getAttribute('href');dialog.showModal();});
 });
 dialog.querySelector('button').addEventListener('click',function(){dialog.close();});dialog.addEventListener('click',function(event){if(event.target===dialog)dialog.close();});
})();
</script></body></html>\n`;
if (!checkOnly) fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({ checkOnly, output, inputDirectory: folder, reviewed: true, accepted: decision.accepted,
  selectedVariant: decision.selectedVariant, actualImageCount: images.size, width: record.screenWidth, height: record.screenHeight,
  tileMetres: record.tileMetres, evidence: [studyPath, decisionPath] }, null, 2));
