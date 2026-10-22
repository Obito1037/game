'use strict';

// Generate an independent static review page; never replaces the stable review.
// node tools/prepare-v11-plant-review.cjs [--check-only]
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const verification = path.join(root, 'art/verification');
const output = path.join(verification, 'visual-review-v11-plants.html');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const requireThat = (condition, message) => { if (!condition) throw new Error(message); };
const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
function file(relative) {
  requireThat(typeof relative === 'string' && !path.isAbsolute(relative) && !relative.includes('\\') && !relative.split('/').includes('..'), 'Expected a local relative evidence path.');
  const absolute = path.join(verification, relative);
  requireThat(fs.existsSync(absolute) && fs.statSync(absolute).isFile() && fs.statSync(absolute).size > 0, 'Missing/non-file/empty input: ' + relative);
  return absolute;
}
const read = relative => fs.readFileSync(file(relative), 'utf8').replace(/^\uFEFF/, '');
const json = relative => JSON.parse(read(relative));
const comparisonFile = 'v11-plants-candidate/capture-condition-comparison.json';
const importFile = 'v11-plants-candidate/unity-import-comparison.json';
const decisionFile = 'v11-plants-candidate/decision.json';
const conditions = json(comparisonFile);
const imports = json(importFile);
const decision = json(decisionFile);
for (const [name, data] of [[comparisonFile, conditions], [importFile, imports]]) {
  requireThat(data && typeof data === 'object' && !Array.isArray(data), 'Expected a JSON evidence object: ' + name);
}
requireThat(decision.reviewed === true && typeof decision.accepted === 'boolean', 'Decision requires reviewed:true and accepted:boolean.');
requireThat(typeof decision.summary === 'string' && decision.summary.trim().length > 0, 'Decision summary is missing.');
requireThat(Array.isArray(decision.limits) && decision.limits.every(item => typeof item === 'string' && item.trim().length > 0), 'Decision limits must be a string array.');
const dimensions = new Map();
function png(relative) {
  const bytes = fs.readFileSync(file(relative));
  requireThat(bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) && bytes.toString('ascii', 12, 16) === 'IHDR', 'Expected an original PNG: ' + relative);
  const size = { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
  requireThat(size.width > 0 && size.height > 0, 'Invalid PNG dimensions: ' + relative);
  dimensions.set(relative, size);
  return size;
}
const groups = [
  { view: 'path', title: '01 / 路径与前景花草', note: '按完整画面比例观察紫花与蕨叶轮廓。' },
  { view: 'roots', title: '02 / 岩脚与周边', note: '保留周边环境，检查非目标区域有无意外变化。' },
  { view: 'lamp', title: '03 / 灯座附近', note: '观察近景叶形及其与灯座、地面之间的关系。' }
];
for (const group of groups) {
  const baseline = png('v11-plants-baseline/' + group.view + '-fixed40.png');
  const candidate = png('v11-plants-candidate/' + group.view + '-fixed40.png');
  requireThat(baseline.width === candidate.width && baseline.height === candidate.height, 'A/B image dimensions differ: ' + group.view);
}
const template = read('visual-review-v10.html');
const style = template.match(/<style\b[^>]*>[\s\S]*?<\/style>/i)?.[0];
const dialog = template.match(/<dialog\b[^>]*>[\s\S]*?<\/dialog>/i)?.[0];
const scripts = [...template.matchAll(/<script\b[^>]*>[\s\S]*?<\/script>/gi)].map(match => match[0]);
requireThat(style && dialog && scripts.length === 1 && scripts[0].includes('dialog.showModal'), 'Expected the v10 CSS and original-image dialog script.');
const link = (relative, label) => { file(relative); return `<a href="${escape(relative)}">${escape(label)}</a>`; };
function figure(view, candidate) {
  const relative = (candidate ? 'v11-plants-candidate/' : 'v11-plants-baseline/') + view + '-fixed40.png';
  const label = candidate ? 'v11 候选' : 'v10 基线';
  const title = label + ' · ' + view + ' 固定机位';
  const size = dimensions.get(relative);
  return `<figure><div class="card-top"><span class="source ours">${label} / 原始固定机位截图</span><span class="resolution">${size.width} × ${size.height} · 原图</span></div><a class="picture" href="${relative}" data-title="${escape(title)}"><img src="${relative}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)}</strong>链接与显示均使用原始 PNG；点击可打开原图。<div class="file">${relative}</div></figcaption></figure>`;
}
const sections = groups.map(group => `<section><div class="section-head"><h2>${group.title}</h2><p class="section-note">${group.note}</p></div><div class="grid">${figure(group.view, false)}${figure(group.view, true)}</div></section>`).join('\n');
const resultLabel = decision.accepted ? '有限静态范围内采用' : '本候选未采用';
const status = data => data.passed === true ? '记录标记通过' : data.passed === false ? '记录标记未通过，不能据此声称受控一致' : '详见记录，不推断为通过';
const limits = decision.limits.map(item => `<li>${escape(item)}</li>`).join('');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v11 · 植物形态固定机位对照</title>${style}</head>
<body><main><header><div class="eyebrow">Borrowed Light · Plant geometry study</div><h1>植物形态 · v10 / v11 固定机位对照</h1><p class="lede">${escape(decision.summary)}</p><p class="lede">本页仅呈现三组固定机位原图与已有审查结论；不是正常游戏通关、动态风摆或性能验收，也不证明整体视觉优于参考作品。</p><div class="tags"><span class="tag">${resultLabel}</span><span class="tag">三组原始 PNG</span><span class="tag">本地独立对照页</span></div></header>
${sections}
<aside class="review"><div><h2>判断与条件记录</h2><p>${escape(decision.summary)}</p><p>${link(comparisonFile, '采集条件对照')}：${status(conditions)}。</p><p>${link(importFile, 'Unity 导入对照')}：${status(imports)}。</p><p>${link(decisionFile, '完整图评决定与范围')}。固定时间不等于冻结全部渲染随机项，不声称逐像素相同。</p></div><ul class="criteria">${limits}<li>原图未裁切、调色、重绘或生成缩略图文件。</li><li>静帧不验证完整步态、动态闪烁或帧率。</li></ul></aside>
<footer>借光岛 · 植物形态固定诊断 · 此页独立于稳定版实机对照页</footer></main>${dialog}
${scripts[0]}
</body></html>\n`;
if (!checkOnly) fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({ checkOnly, output, reviewed: true, accepted: decision.accepted, images: [...dimensions.keys()], evidence: [comparisonFile, importFile, decisionFile] }, null, 2));
