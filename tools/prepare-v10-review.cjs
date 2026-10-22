'use strict';

// Stage a review page only after the final v10 QA and actual video review exist.
// Links intentionally resolve from art/verification AFTER root promotes this draft.
// This script never opens a browser, runs the game or changes production sources.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const verification = path.join(root, 'art', 'verification');
const draft = path.join(verification, 'v10-release-draft');

function requireThat(condition, message) {
  if (!condition) throw new Error(message);
}
function workspaceFile(relative) {
  const absolute = path.resolve(root, relative);
  const within = path.relative(root, absolute);
  requireThat(within && !path.isAbsolute(within) && within !== '..' && !within.startsWith('..' + path.sep),
    'Evidence path must remain in the workspace: ' + relative);
  requireThat(fs.existsSync(absolute) && fs.statSync(absolute).isFile() && fs.statSync(absolute).size > 0,
    'Required evidence is missing or empty: ' + relative);
  return absolute;
}
function readJson(relative) {
  return JSON.parse(fs.readFileSync(workspaceFile(relative), 'utf8').replace(/^\uFEFF/, ''));
}
function textValue(value, name) {
  requireThat(typeof value === 'string' && value.trim().length > 0, 'Missing evidence text: ' + name);
  return value.trim();
}
function escape(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}
const links = new Set();
const imageFiles = [];
function localFile(file) {
  requireThat(typeof file === 'string' && !path.isAbsolute(file) && !file.includes('\\') && !/^[a-z][a-z\d+.-]*:/i.test(file),
    'Expected a relative review link: ' + file);
  workspaceFile(path.relative(root, path.resolve(verification, file)));
  links.add(file);
  return escape(file);
}
function localLink(file, label) {
  return `<a href="${localFile(file)}">${escape(label)}</a>`;
}

const data = readJson('art/verification/v10-release-draft/handoff-data.json');
requireThat(data.revision === 'v10' && data.aestheticObjectiveAchieved === false,
  'Expected the v10 handoff draft with the aesthetic objective still unachieved');
for (const key of ['visual', 'scope', 'validation', 'performance']) textValue(data[key], 'handoff.' + key);
for (const key of ['windows', 'web']) textValue(data.buildIds?.[key], 'handoff.buildIds.' + key);
const expectedEvidence = {
  windowsQA: 'art/verification/run-025-v10/runtime-results.json',
  webQA: 'art/verification/web-011-v10/runtime-results.json',
  gaitManifest: 'art/verification/web-v10-gait-video/capture-manifest.json',
  gaitReview: 'art/verification/web-v10-gait-video/review.json'
};
for (const [key, file] of Object.entries(expectedEvidence)) {
  requireThat(data.evidence?.[key] === file, 'Handoff evidence does not identify the final v10 session: ' + key);
}
const native = readJson(expectedEvidence.windowsQA);
const web = readJson(expectedEvidence.webQA);
const capture = readJson(expectedEvidence.gaitManifest);
const videoReview = readJson(expectedEvidence.gaitReview);
const nativeIdentity = readJson('art/verification/run-025-v10/build-evidence.json');
const webIdentity = readJson('art/verification/web-011-v10/artifact-identity.json');
const videoIdentity = readJson('art/verification/web-v10-gait-video/build-evidence.json');

// Native QA has individual assertions, not a top-level "passed" field.
const nativeChecks = ['puzzleCompleted', 'menuKeyboardStart', 'pauseStopsMovement', 'resumeMovement',
  'restartWorks', 'endingReturnWorks', 'cabinCollisionWorks', 'walkwayGroundingWorks',
  'boulderCollisionWorks', 'observatoryGroundingWorks', 'observatoryInstrumentCollisionWorks',
  'decorativeLeavesExcluded', 'pierGroundingWorks', 'pierRailCollisionWorks', 'scrollZoomWorks'];
requireThat(nativeChecks.every(key => native[key] === true), 'Final native functional QA is incomplete');
const webChecks = ['passed', 'realKeyboardPuzzleCompletion', 'persistedProgressReload',
  'crossOriginIsolated', 'audioContextResumeObserved'];
requireThat(webChecks.every(key => web[key] === true) && Array.isArray(web.errors) && web.errors.length === 0,
  'Final normal browser QA is incomplete or has errors');
requireThat(nativeIdentity.buildId === data.buildIds.windows, 'Native QA build identity differs from handoff');
requireThat(webIdentity.passed === true && webIdentity.buildId === data.buildIds.web &&
  webIdentity.declaredBuildMatches === true && webIdentity.requestedAllCurrentFiles === true &&
  Array.isArray(webIdentity.files) && webIdentity.files.length > 0 && webIdentity.files.every(file => file.matches === true),
  'Normal browser artifact identity is incomplete or differs from handoff');
requireThat(videoIdentity.declaredBuildId === data.buildIds.web, 'Gait recording identifies another Web build');
const requestedVideoFiles = new Set((videoIdentity.servedBuildResources || []).map(url => path.posix.basename(new URL(url).pathname)));
requireThat(webIdentity.files.every(file => requestedVideoFiles.has(file.name)),
  'Gait session request URLs do not identify all final Web payload files');
// Request filenames establish only this association, not historical response-body hashes.

requireThat(capture.completed === true && capture.error === null && Array.isArray(capture.errors) && capture.errors.length === 0,
  'Gait capture did not complete without browser errors');
requireThat(capture.requestedRevision === 'v10' && capture.videoOnly === true &&
  capture.recordedVideo === 'gait-session-includes-loading.webm', 'Expected the original v10 video-only gait session');
requireThat(capture.canvasMetrics?.width === capture.width && capture.canvasMetrics?.height === capture.height &&
  capture.width > 0 && capture.height > 0, 'Recorded canvas dimensions are missing or inconsistent');
requireThat(capture.gaitWindow && Number.isFinite(capture.gaitWindow.startSinceNavigationMs) &&
  Number.isFinite(capture.gaitWindow.endSinceNavigationMs) && capture.gaitWindow.durationMs > 0 &&
  capture.gaitWindow.endSinceNavigationMs > capture.gaitWindow.startSinceNavigationMs,
  'Gait action interval is missing');
requireThat(Array.isArray(capture.events) && !capture.events.some(event => event.type === 'screenshot') &&
  ['gait-window-start', 'gait-window-end', 'movement-start', 'movement-stop'].every(type => capture.events.some(event => event.type === type)),
  'Continuous input/video evidence is incomplete');
requireThat(videoReview.reviewed === true && videoReview.acceptedForLimitedScope === true,
  'The actual gait video needs an explicit limited-scope visual review');
if (videoReview.revision !== undefined) requireThat(videoReview.revision === 'v10', 'Video review is for another revision');
if (videoReview.declaredBuildId !== undefined) requireThat(videoReview.declaredBuildId === data.buildIds.web, 'Video review build differs from handoff');
if (videoReview.buildId !== undefined) requireThat(videoReview.buildId === data.buildIds.web, 'Video review build differs from handoff');
const videoSummary = textValue(videoReview.summary, 'gait review summary');
const rawVideoLimits = videoReview.limitations ?? videoReview.limits;
const videoLimits = typeof rawVideoLimits === 'string' ? [rawVideoLimits] : rawVideoLimits;
requireThat(Array.isArray(videoLimits) && videoLimits.length > 0, 'Gait review must state its actual coverage limitations');
videoLimits.forEach((value, index) => textValue(value, 'gait review limitation ' + index));
for (const key of ['videoScope', 'inputMethod', 'frameRateLimit', 'timingLimit']) textValue(capture[key], 'capture.' + key);

const stone = readJson('art/verification/v10-stone-study/material-study.json');
const stonePixels = readJson('art/verification/v10-stone-study/pixel-comparison.json');
const silhouette = readJson('art/verification/v10-silhouette-candidate/capture-condition-comparison.json');
const foliage = readJson('art/verification/v10-foliage-study/review.json');
requireThat(stone.allInvariantsPassed === true && silhouette.passed === true, 'Fixed-study capture conditions are incomplete');
requireThat(foliage.reviewed === true && foliage.acceptedForLimitedScope === true &&
  foliage.recommendedDefault === 'fixed40' && foliage.fixed20RecommendedAsDefault === false,
  'Foliage decision no longer agrees with this review page');
const aa = stonePixels.rows?.find(row => row.a === 'path-baseline.png' && row.b === 'path-baseline-repeat.png');
requireThat(aa && Number.isFinite(aa.meanAbsoluteRGBByteDifference), 'Stone repeat-capture measurement is missing');

// Reuse the already-reviewed presentation and original-image dialog; no game script.
const previous = fs.readFileSync(workspaceFile('art/verification/visual-review-v8.html'), 'utf8');
const style = previous.match(/<style>[\s\S]*?<\/style>/)?.[0];
const viewerStart = previous.indexOf('<dialog aria-label=');
requireThat(style && viewerStart >= 0, 'Previous review page is missing its style or image dialog');
const viewer = previous.slice(viewerStart);
requireThat(viewer.includes('dialog.showModal') && viewer.includes('</html>'), 'Image dialog template is incomplete');

function figure(file, title, caption, reference = false) {
  const href = localFile(file);
  imageFiles.push(file);
  return `<figure><div class="card-top"><span class="source ${reference ? 'reference' : 'ours'}">${reference ? '参考 / Saccc_c' : '本作 / 原始实机截图'}</span><span class="resolution">检测图片尺寸…</span></div><a class="picture" href="${href}" data-title="${escape(title)}"><img src="${href}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${escape(title)}</strong>${escape(caption)}<div class="file">${escape(file)}</div></figcaption></figure>`;
}
function section(number, title, note, figures, tail = '') {
  return `<section><div class="section-head"><h2>${number} / ${escape(title)}</h2><p class="section-note">${escape(note)}</p></div><div class="grid">${figures.join('\n')}</div>${tail}</section>`;
}

const parts = [];
parts.push(section('01', '参考与 v10 实际游玩', '日景与夜景、不同作品与构图；这不是受控 A/B', [
  figure('../reference/littleprince-gameplay.png', '参考作品 · 实际游玩画面',
    'Saccc_c 原网站截图，仅供本地研究。人物、衣料和自然环境的整体成熟度仍是本作尚未达到的目标。', true),
  figure('run-025-v10/07-walking.png', '借光岛 v10 · 正常游戏镜头',
    '本次 Windows 最终候选的漫步视角截图。画面展示采用后的整体效果，不能用日夜和取景差异证明优于参考。')
]));
parts.push(section('02', '石材固定对照', '相同几何、相机与灯光；新增纹理及其材质响应一起比较', [
  figure('v10-stone-study/path-baseline.png', '原石材 · 固定基线',
    '四块前景岩石的大断面保持，表面原先较平滑。此组是固定机位材质诊断，并非正常玩法录像。'),
  figure('v10-stone-study/path-texture.png', '采用石材 · 相同机位',
    '矿物纹理、色差、粗糙度变化及浅起伏共同作用；不能将观察到的差异全部归于单一参数。'),
  figure('v10-stone-study/left-rock-texture.png', '采用石材 · 左侧近景',
    '近景用于看断面、颗粒与层理；这是单张候选近景，不是另一次受控新旧比较。全部角度与动态闪烁仍有覆盖限制。')
], `<p class="section-note">冻结时间不冻结所有渲染随机项；SSAO 蓝噪声按相机渲染更新。基线复拍 RGB 平均绝对差为 ${aa.meanAbsoluteRGBByteDifference.toFixed(3)}/255，不能声称逐像素相同，也不能把该数值全部归因于 AO。${localLink('v10-stone-study/pixel-comparison.json', '复拍差异')} · ${localLink('v10-stone-study/decision.json', '采用范围')}</p>`));
parts.push(section('03', '人物轮廓固定对照', '相同相机、灯光及摆好的姿态；本轮只改变 7 个目标网格', [
  figure('v10-silhouette-baseline/three-quarter-current.png', '原人物 · 三分之四视角',
    '旧袖部、裤腿与发束轮廓，保留为同条件基线。此姿态属于造型诊断。'),
  figure('v10-silhouette-candidate/three-quarter-current.png', '采用轮廓 · 三分之四视角',
    '袖部收窄、膝部轮廓放松及发梢不对称变化；55 个非目标网格与骨架、权重、材质保留。静态对照不证明所有行走姿态。')
], `<p class="section-note">${localLink('v10-silhouette-candidate/capture-condition-comparison.json', '相机与灯光条件')} · ${localLink('v10-silhouette-candidate/decision.json', '轮廓采用范围')}。逐帧 AO 等波动仍存在，不作像素完全一致的宣称。</p>`));
parts.push(section('04', '植被辅助通道修正', '保留 40% 向上法线混合；20% 候选未采用', [
  figure('v10-foliage-study/lamp-legacy40.png', '原辅助通道 · 40%',
    '灯座近景基线。旧前向画面的风摆、双面法线处理未同步到深度/法线通道。'),
  figure('v10-foliage-study/lamp-fixed40.png', '同步后的辅助通道 · 40%',
    '所审三个固定机位未见新增明显黑叶、脏圈或悬浮阴影；静态差异有限，不称整体自然度明显提升。20% 会让部分细叶更暗，收益不足以改变默认。')
], `<p class="section-note">${localLink('v10-foliage-study/review.json', '三机位原图审查与限制')}。画面中原有的简化叶形仍可见。</p>`));

const videoFile = 'web-v10-gait-video/gait-session-includes-loading.webm';
const videoHref = localFile(videoFile);
const routeLabel = capture.route === 'diagonal-and-side' ? '斜向、侧向行走与松键停步'
  : capture.route === 'observatory-straight-approach' ? '观星台直行接近与松键停步' : '记录中的实际输入路线';
const navigationStart = (capture.gaitWindow.startSinceNavigationMs / 1000).toFixed(1);
const navigationEnd = (capture.gaitWindow.endSinceNavigationMs / 1000).toFixed(1);
parts.push(`<section><div class="section-head"><h2>05 / 网页完整原始行走录像</h2><p class="section-note">真实键鼠 · 原录像含加载与解谜 · 录屏不是性能测试</p></div><figure><video class="clip" controls preload="metadata" playsinline src="${videoHref}" aria-label="借光岛 v10 网页完整原始行走录像"></video><figcaption><strong>${escape(routeLabel)}</strong>${escape(videoSummary)}<p>完整原录像，没有把加载和解谜过程剪去。记录画幅 ${capture.width} × ${capture.height}；动作窗口约为导航后 ${navigationStart}–${navigationEnd} 秒，仅作定位参考，不是精确视频帧时间。</p><ul>${videoLimits.map(limit => `<li>${escape(limit)}</li>`).join('')}</ul><p>录像播放帧率与浏览器录制采样不等于游戏引擎 FPS；本页不据录像宣称性能提升。</p><p>${localLink('web-v10-gait-video/capture-manifest.json', '采集记录')} · ${localLink('web-v10-gait-video/review.json', '实际所见范围与限制')} · ${localLink(videoFile, '打开完整原录像')}</p><details><summary>采集限制原文</summary><p>${escape(capture.videoScope)}</p><p>${escape(capture.inputMethod)}</p><p>${escape(capture.frameRateLimit)}</p><p>${escape(capture.timingLimit)}</p></details></figcaption></figure></section>`);

const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v10 · 本地实机美术对照</title>${style}</head>
<body><main><header><div class="eyebrow">Borrowed Light · v10 · Local visual review</div><h1>借光岛 v10 · 石材与人物轮廓</h1><p class="lede">${escape(data.visual)}</p><p class="lede">来源：<a href="https://littleprince.dev/">Saccc_c 原网站</a> · <a href="https://x.com/Saccc_c/status/2110694725640474759">原推文</a>。本页供本地审阅，未发布公网。</p><div class="tags"><span class="tag">run-025-v10</span><span class="tag">web-011-v10</span><span class="tag">原图与完整录像</span><span class="tag pending">整体审美目标未达到</span></div></header>
${parts.join('\n')}
<aside class="review"><div><h2>结论与证据边界</h2><p>${escape(data.visual)}</p><p>${escape(data.performance)}</p><p>所有图片链接原始文件，没有裁切、调色或重绘。固定对照、正常游戏截图和实际输入录像各自证明的范围不同。</p></div><ul class="criteria"><li>本作与参考是非受控对照</li><li>固定 A/B 仍有逐帧渲染波动</li><li>有限录像不覆盖全部路线与姿态</li><li>短样本不支持版本性能收益结论</li><li>${localLink('run-025-v10/runtime-results.json', '原生 QA')} · ${localLink('web-011-v10/runtime-results.json', '正常网页 QA')}</li></ul></aside>
<footer>借光岛 v10 · 原创角色与场景 · 参考署名 Saccc_c · 本地证据页</footer></main>${viewer}`;

// All evidence, decisions and local links have been checked before either write.
// Do not alter art/verification/visual-review.html here: promotion belongs to root.
fs.writeFileSync(path.join(draft, 'visual-review.html'), html, 'utf8');
fs.writeFileSync(path.join(draft, 'visual-review-files.json'), JSON.stringify({
  revision: 'v10', allFilesExist: true, imageCount: imageFiles.length, videoCount: 1,
  count: imageFiles.length + 1, files: [...imageFiles, videoFile], localLinks: [...links],
  buildIds: data.buildIds, linkBaseAfterPromotion: 'art/verification',
  generatedFromAcceptedEvidence: true, browserLoadingVerified: false,
  limitation: 'Existence and recorded acceptance checks only. Root must verify static page/media loading after promotion.'
}, null, 2) + '\n');
console.log(JSON.stringify({draft: 'art/verification/v10-release-draft/visual-review.html',
  images: imageFiles.length, videos: 1, localLinksChecked: links.size, browserStarted: false}));
