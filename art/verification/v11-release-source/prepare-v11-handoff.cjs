'use strict';

// Validate v11 evidence and stage five handoff files. Never promotes or packages a build.
// node tools/prepare-v11-handoff.cjs [--check-only]
// BORROWED_LIGHT_NATIVE_QA selects the native session, e.g. run-029-v11.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const draft = path.join(root, 'art/verification/v11-release-draft');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const nativeRun = process.env.BORROWED_LIGHT_NATIVE_QA || 'run-029-v11';
if (!/^run-\d+-v11$/.test(nativeRun)) throw new Error('BORROWED_LIGHT_NATIVE_QA must be a v11 session name such as run-029-v11.');
const evidence = {
  builds: 'art/verification/v11-build-reports.json',
  windowsQA: `art/verification/${nativeRun}/runtime-results.json`,
  nativeIdentity: `art/verification/${nativeRun}/build-evidence.json`,
  boulderProbes: `art/verification/${nativeRun}/boulder-approaches.json`,
  webQA: 'art/verification/web-012-v11/runtime-results.json',
  webIdentity: 'art/verification/web-012-v11/artifact-identity.json',
  plantDecision: 'art/verification/v11-plants-candidate/decision.json',
  captureComparison: 'art/verification/v11-plants-candidate/capture-condition-comparison.json',
  importComparison: 'art/verification/v11-plants-candidate/unity-import-comparison.json',
  interchange: 'art/generated/world-v8/interchange-verification.json',
  packageVerification: 'art/verification/v11-package-verification.json',
  releaseHTTPVerification: 'art/verification/v11-release-http-verification.json'
};
const assert = (condition, message) => { if (!condition) throw new Error(message); };
function local(file) {
  const full = path.resolve(root, file), relative = path.relative(root, full);
  assert(relative && !path.isAbsolute(relative) && relative !== '..' && !relative.startsWith('..' + path.sep), 'Path outside workspace: ' + file);
  return full;
}
const read = file => fs.readFileSync(local(file), 'utf8').replace(/^\uFEFF/, '');
const json = file => JSON.parse(read(file));
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(local(file))).digest('hex').toUpperCase();
const sameHash = (a, b) => typeof a === 'string' && /^[0-9a-f]{64}$/i.test(a) && typeof b === 'string' && a.toUpperCase() === b.toUpperCase();
const positive = (value, label) => { assert(Number.isFinite(value) && value > 0, 'Missing positive value: ' + label); return value; };
const noErrors = (data, label) => assert(Array.isArray(data.errors) && data.errors.length === 0, label + ' errors missing/non-empty.');
const builds = json(evidence.builds), native = json(evidence.windowsQA), web = json(evidence.webQA);
assert(builds.revision === 'v11', 'Expected v11 build reports.');
for (const [name, platform] of [['native', 'StandaloneWindows64'], ['web', 'WebGL']]) {
  const build = builds[name];
  assert(build?.status === 'completed' && build.result === 'Succeeded' && build.platform === platform && /^build_[a-z0-9]+$/i.test(build.buildId), name + ' build incomplete/wrong platform.');
  assert(build.totalErrors === 0, name + ' build has errors.');
  noErrors(build, name + ' build');
}
assert(builds.native.buildId === 'build_45ae373ba8b1', 'Native build differs from the reviewed v11 candidate.');
const nativeChecks = ['puzzleCompleted', 'menuKeyboardStart', 'pauseStopsMovement', 'resumeMovement', 'restartWorks',
  'endingReturnWorks', 'cabinCollisionWorks', 'walkwayGroundingWorks', 'boulderCollisionWorks',
  'observatoryGroundingWorks', 'observatoryInstrumentCollisionWorks', 'decorativeLeavesExcluded',
  'pierGroundingWorks', 'pierRailCollisionWorks', 'scrollZoomWorks'];
for (const key of nativeChecks) assert(native[key] === true, 'Native QA failed/missing: ' + key);
positive(native.walkingDistance, 'walkingDistance');
assert(native.riggedSoles === 2 && native.soleGroundSamples > 0 && Number.isFinite(native.minimumIdleSoleClearanceMetres), 'Native sole evidence incomplete.');
assert(Math.abs(native.normalizedScrollStepMetres - 0.35) < 0.0001, 'Normalized scroll step differs.');
for (const view of ['menu', 'overview', 'walking', 'portrait']) positive(native.fpsSamples?.[view], 'native FPS ' + view);
positive(native.fpsAtFinalView, 'native final FPS');
for (const key of ['width', 'height']) positive(native[key], 'native ' + key);
// A final width/height alone cannot describe earlier samples after a window resize.
for (const name of ['01-invitation.png', '02-island.png', '03-path-solved.png', '04-window-solved.png', '05-harbor-solved.png', '06-stars-return.png', '07-walking.png', '08-restarted.png', '09-traveler-portrait.png']) {
  const bytes = fs.readFileSync(local(`art/verification/${nativeRun}/${name}`));
  assert(bytes.length >= 24 && bytes.toString('ascii', 12, 16) === 'IHDR' && bytes.readUInt32BE(16) === native.width && bytes.readUInt32BE(20) === native.height, 'Native QA has mixed screenshot dimensions: ' + nativeRun + '/' + name);
}
const nativeIdentity = json(evidence.nativeIdentity);
const nativeDirectory = path.dirname(local(builds.native.outputPath));
assert(nativeIdentity.buildId === builds.native.buildId && local(nativeIdentity.playerDirectory) === nativeDirectory, 'Native QA used another build.');
const nativeFiles = new Map((nativeIdentity.files || []).map(file => [file.name.replace(/\\/g, '/'), file]));
for (const name of ['BorrowedLight.exe', 'UnityPlayer.dll', 'BorrowedLight_Data/resources.assets', 'BorrowedLight_Data/Managed/Assembly-CSharp.dll']) {
  assert(sameHash(sha(path.join(nativeDirectory, name)), nativeFiles.get(name)?.sha256), 'Native bytes changed after QA: ' + name);
}
const probes = json(evidence.boulderProbes);
assert(probes.allPassed === true && probes.probes?.length === 16 && probes.probes.every(p => p.startsClear === true && p.blockedBeforeCentre === true), 'Boulder probes incomplete.');
for (const key of ['passed', 'realKeyboardPuzzleCompletion', 'persistedProgressReload', 'crossOriginIsolated', 'audioContextResumeObserved', 'defaultBrowserAutoplayPolicy']) {
  assert(web[key] === true, 'Web QA failed/missing: ' + key);
}
noErrors(web, 'Web QA');
for (const key of ['width', 'height']) positive(web[key], 'web ' + key);
const payload = builds.web.payload;
assert(payload?.files?.length === 4 && Number.isSafeInteger(payload.bytes) && payload.bytes > 0 && new Set(payload.files.map(f => f.name)).size === 4, 'Web core payload missing/invalid.');
assert(payload.files.reduce((sum, file) => sum + file.bytes, 0) === payload.bytes, 'Web payload size sum differs.');
const webIdentity = json(evidence.webIdentity);
assert(webIdentity.passed === true && webIdentity.buildId === builds.web.buildId && webIdentity.declaredBuildMatches === true && webIdentity.requestedAllCurrentFiles === true, 'Web QA build identity incomplete.');
for (const file of payload.files) {
  assert(path.basename(file.name) === file.name && !file.name.includes('\\') && Number.isSafeInteger(file.bytes) && file.bytes > 0, 'Invalid web payload file.');
  const actual = path.join(local(builds.web.outputPath), 'Build', file.name);
  const record = webIdentity.files?.find(item => item.name === file.name);
  assert(fs.statSync(actual).size === file.bytes && sameHash(sha(actual), file.sha256), 'Web candidate changed: ' + file.name);
  assert(record?.matches === true && record.bytes === file.bytes && sameHash(record.httpSHA256, file.sha256) && sameHash(record.diskSHA256, file.sha256), 'Web QA hash identity differs: ' + file.name);
}
function webFPS(view) {
  const item = web.performanceViews?.find(v => v.view === view);
  assert(item?.allSamplesForeground === true && item.samples?.length === 6 && item.intervalMs === 500 && item.samples.every(s => s.visibility === 'visible' && s.focused === true && Number.isFinite(s.fps)), 'Missing foreground performance scope: ' + view);
  return positive(item.medianIntervalFps, view + ' medianIntervalFps');
}
const walkingFPS = webFPS('walking'), endingFPS = webFPS('ending');
const asset = json('art/generated/world-v8/asset-manifest.json');
const interchange = json(evidence.interchange), imported = json(evidence.importComparison), capture = json(evidence.captureComparison), decision = json(evidence.plantDecision);
assert(asset.revision === 'world-v8' && asset.triangles === 510293 && asset.changed_meshes?.length === 2 && asset.changed_meshes.includes('Garden_FeatherFerns') && asset.changed_meshes.includes('Garden_LavenderAndSeedHeads'), 'World-v8 scope differs.');
assert(interchange.passed === true && interchange.checks?.length === 3 && interchange.checks.every(c => c.passed === true && c.mesh_count === 29 && c.anchor_count === 14 && c.materials_identical === true && c.anchors_identical === true && c.unchanged_non_targets?.length === 27 && c.unchanged_non_targets.every(m => m.same === true)), 'World three-format preservation failed.');
assert(Object.values(interchange.textures_byte_identical || {}).length === 2 && Object.values(interchange.textures_byte_identical).every(v => v === true), 'World texture preservation failed.');
assert(imported.passed === true && imported.anchorsUnchanged === true && imported.nonTargetUnchanged === true && imported.allTransformsUnchanged === true && imported.trianglesAfter === 510293, 'Unity import comparison failed.');
assert(capture.passed === true && capture.sceneMatch === true && capture.viewMatch === true && capture.lightsMatch === true, 'Fixed capture conditions differ.');
assert(decision.reviewed === true && decision.accepted === true && decision.windowsBuild === builds.native.buildId && decision.aestheticObjectiveAchieved === false, 'Plant adoption decision incomplete.');
for (const [name, expected] of Object.entries(asset.sha256)) assert(sameHash(sha('art/generated/world-v8/' + name), expected), 'Frozen world asset changed: ' + name);
assert(sameHash(sha('GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx'), asset.sha256['island.fbx']) && sameHash(decision.worldFbxSHA256, asset.sha256['island.fbx']), 'Unity world or decision differs from frozen world-v8.');
const character = json('art/generated/character-v9/traveler-manifest.json');
assert(sameHash(sha('art/generated/character-v9/traveler.fbx'), character.sha256['traveler.fbx']) && sameHash(sha('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx'), character.sha256['traveler.fbx']), 'Frozen character-v9 changed.');
const previous = json('art/production-manifest.json');
assert(sameHash(previous.geometry.travelerFbxSHA256, character.sha256['traveler.fbx']), 'Character differs from the stable character-v9.');
for (const file of ['setup/Check-Tools.ps1', 'setup/tool-status.json', 'Open-Borrowed-Light.cmd', 'Open-Borrowed-Light-Web.cmd', 'Open-GameProject.cmd', 'art/verification/visual-review-v11-plants.html']) assert(fs.statSync(local(file)).isFile(), 'Referenced handoff file missing: ' + file);

const scope = 'v11 采用 world-v8：岛屿 510,293 三角，只更新 Garden_LavenderAndSeedHeads 与 Garden_FeatherFerns 两个植物网格；其余 27 个网格、14 个锚点、全部纹理与材质保留。角色仍为冻结的 character-v9（77,132 三角、62 mesh renderer、28 skinned mesh、12 bones）；stone-v10 材质和 Foliage Fixed40 保持。';
const visual = '固定机位原图中，紫花由等大尖柱变为细碎花冠，蕨叶的黑硬菱片减少；路径完整画面也能看到改善。新紫穗更细，中远景色量减弱；草群的均匀针状分布和地面层次仍是下一重点。整体审美超过参考站的目标仍未达成。';
const performance = `${native.gpu} 原生 ${nativeIdentity.requestedFullscreen ? '全屏' : '窗口'} ${native.width}×${native.height} 短样本：菜单 ${native.fpsSamples.menu}、总览 ${native.fpsSamples.overview}、漫步视角 ${native.fpsSamples.walking}、近景 ${native.fpsSamples.portrait}、末段 ${native.fpsAtFinalView} FPS。网页 ${web.width}×${web.height} 各视角 6×500 ms 前台区间指标中位：停步后的漫步视角 ${walkingFPS.toFixed(2)}、结尾 ${endingFPS.toFixed(2)}。这些短样本不是持续行走平均、全程最低或独立渲染帧计数，不支持版本间性能收益结论。`;
const validation = `Windows ${builds.native.buildId}：${nativeRun} 的三章通关、启动、行走、暂停恢复、重开、结尾返回、归一化滚轮及既有碰撞／接地检查通过；16/16 主石指定方向探测通过。两只实际蒙皮鞋底共 ${native.soleGroundSamples} 个静止采样，最小净空 ${native.minimumIdleSoleClearanceMetres} m，不覆盖全部动态姿态。\nWeb ${builds.web.buildId}：web-012-v11 的真实键盘通关、刷新续玩、默认策略音频恢复和跨源隔离通过；浏览器异常数组为空，引擎兼容性提示以原日志为准。\n${performance}\n网页四个压缩核心文件共 ${payload.bytes.toLocaleString('en-US')} bytes（约 ${(payload.bytes / 1e6).toFixed(1)} MB），本机缓存测试不代表首次网络下载。\n运行包完整性记录见 art/verification/v11-package-verification.json；本机网页文件校验见 art/verification/v11-release-http-verification.json，以记录为准。`;
const source = '世界脚本 art/blender/build_island_v8.py 读取冻结 world-v7/island.blend，保留 world-v7→world-v6 复现链；三格式 BLEND/FBX/GLB 回读与保护检查见 art/generated/world-v8/interchange-verification.json。本轮是植物几何更新，没有新增图片生成、音频或字体。';
const limits = `三组固定植物对照见 art/verification/visual-review-v11-plants.html，条件和采用范围见 art/verification/v11-plants-candidate/ 的比较记录及 decision.json。固定时间不冻结全部渲染随机项，不声称像素完全一致。v10 行走录像仅为历史证据，本版没有新行走录像审查，不能据旧录像验收新植物动态风摆或当前步态。run-026-v11 受并行 Blender 工作影响；run-027-v11 的窗口曾中途缩放，均不用于跨版性能比较。当前原生交付依据为 ${nativeRun}。`;
const characterLimit = 'character-v9 保持冻结，本轮没有重新全面验证人物各格式、眨眼和全部步态。其继承自 character-v8 的 GLB 六个零面积下睑／嘴线端点全角法线限制保留；既有七个目标网格法线通过不等于所有格式全域通过。游戏仍使用 FBX。';
const playSource = read('PLAY.zh-CN.txt'), start = playSource.indexOf('当前交付与验证范围'), end = playSource.indexOf('素材与参赛');
assert(start > 0 && end > start, 'PLAY section boundaries changed.');
const prefix = playSource.slice(0, start).replace(/中文试玩说明 · v\d+/, '中文试玩说明 · v11').replace(/压缩游戏数据、代码与加载器合计约 [\d.]+ MB/, `压缩游戏数据、代码与加载器合计约 ${(payload.bytes / 1e6).toFixed(1)} MB`);
const play = prefix + '当前交付与验证范围\n\n' + scope + '\n\n' + validation + '\n\n' + visual + '\n\n' + characterLimit + '\n\n' + limits + '\n\n' + playSource.slice(end);
const disclosure = `借光岛 v11 · 制作记录与 AI 使用披露\n\n用户提出单人参赛、48 小时范围和参考要求。Blender 脚本、模型、Unity 程序、材质、音频合成、验收脚本及说明由 Codex 代理生成或修改；本人取舍、修改、试玩与提交须据实记录，不把尚未发生的工作写作学生贡献。没有代为报名或公网发布。\n\n${scope}\n${source}\n${characterLimit}\n\n既有天空与 stone-v10 为内置 image_gen 依原创提示生成；提示词与 SHA256 在 art/generated/sky/manifest.json、art/generated/stone-v10/manifest.json。石纹是生成式颜色图和艺术性浅凹凸，不是实测扫描。模型为本地 Blender 脚本制作；音乐与提示音为本地原创合成，无第三方录音采样。未使用 Auto-Rig Pro、Tripo 或 Mixamo。\n字体为 Noto Serif CJK SC 的改名子集 BorrowedLight Story Serif，SIL OFL 1.1，来源和许可保留于 art/generated/fonts/，脚本 tools/font-subset/build_subset.py。\n视觉参考：https://littleprince.dev/ 与 https://x.com/Saccc_c/status/2110694725640474759 。没有复制其程序、模型、人物、音频或原作文字；研究截图不打包为本作资源。暗夜依据见 art/reference/dark-sky-theme-sources.zh-CN.txt；散光预算是无量纲规则，暖色不代表无生态影响。\n\n${validation}\n\n${limits}\n${visual}\n`;
const next = `本地游戏工具与试玩说明（v11）\n\n双击根目录 Open-Borrowed-Light.cmd 或 Open-Borrowed-Light-Web.cmd，详细操作见 PLAY.zh-CN.txt。浏览器只在 localhost 提供服务，没有公网部署。运行包无需登录 Unity；编辑工程使用 Open-GameProject.cmd 继承已有进程级代理。\n\n${scope}\n\n${validation}\n\n${visual}\n\n正常运行记录：art/verification/${nativeRun}/ 与 art/verification/web-012-v11/；固定植物图评：art/verification/visual-review-v11-plants.html。本版没有新增行走录像验收，旧版录像只作历史参考。旧版归档在 builds/archive/，各版本范围以记录为准。\n\n环境为 Unity 6000.3.26f1、Blender 4.5.14 LTS；编辑前按 AGENTS.md 检查 Unity status 与 pipeline list。工具检查：setup/Check-Tools.ps1、setup/tool-status.json；Auto-Rig Pro 未安装，Tripo/Mixamo 账号未配置。\n`;
const manifest = structuredClone(previous);
manifest.revision = 'v11'; delete manifest.inProgressRevision; delete manifest.inProgressScope;
manifest.authoring.scene = 'generated/world-v8/island.blend';
manifest.authoring.sceneScript = 'blender/build_island_v8.py';
manifest.authoring.sceneDependencies = ['generated/world-v7/', 'generated/world-v6/'];
manifest.geometry.islandTriangles = 510293;
manifest.geometry.worldFbxSHA256 = asset.sha256['island.fbx'].toUpperCase();
manifest.buildIds = { windows: builds.native.buildId, web: builds.web.buildId };
manifest.webPayload = payload;
manifest.verification = {
  blenderInterchange: evidence.interchange + ': BLEND/FBX/GLB passed; 29 meshes/14 anchors; 27 non-target meshes, textures and materials preserved. This is format/preservation evidence, not full runtime collision or animation coverage.',
  characterRoundTrip: characterLimit,
  purePuzzleRules: previous.verification.purePuzzleRules,
  windowsRuntime: evidence.windowsQA + ': individual native functional checks and 16 boulder probes passed.',
  webRuntime: evidence.webQA + ': real keyboard completion, reload persistence, default-policy audio resume and isolation passed.',
  artifactIdentity: [evidence.nativeIdentity, evidence.webIdentity],
  performance,
  fixedPlantComparison: [evidence.plantDecision, evidence.captureComparison, evidence.importComparison],
  shaderChecks: 'Existing stone-v10 and Foliage Fixed40 retained; no new shader performance comparison or zero-cost claim.',
  scrollInput: 'Existing normalized .35 metres/step retained; native forward/reverse-step QA passed.',
  finalVisualComparison: visual,
  currentAnimationLimit: 'No new gait/idle/blink-video review for v11. Functional movement QA does not replace exhaustive visual animation review.'
};
manifest.historicalEvidence = { ...(previous.historicalEvidence || {}),
  v10GaitVideo: { review: 'verification/web-v10-gait-video/review.json', scope: 'v10 historical limited-scope video only; not current v11 dynamic acceptance.' },
  v11ConcurrentNativeRun: { session: 'verification/run-026-v11/', scope: 'Historical run affected by parallel Blender work; current evidence: ' + nativeRun },
  v11ResizedNativeRun: { session: 'verification/run-027-v11/', scope: 'Window changed from 1440x900 to 1078x672 mid-run; not used for cross-version performance comparison.' }
};
manifest.delivery = { package: '../builds/BorrowedLight-Windows.zip',
  packageVerification: 'verification/v11-package-verification.json',
  releaseHTTPVerification: 'verification/v11-release-http-verification.json',
  previousStableWindowsArchive: '../builds/archive/BorrowedLight-v10-Windows.zip',
  previousStableWebArchive: '../builds/archive/BorrowedLight-v10-Web/',
  packageVerificationPassed: false, releaseHTTPVerified: false, stagingOnly: true };
manifest.aestheticObjectiveAchieved = false;
const releaseChecks = { generatedAtUTC: new Date().toISOString(), revision: 'v11', stagingOnly: true,
  runtimeAcceptancePassed: true, releaseReady: false, windowsBuild: builds.native.buildId, webBuild: builds.web.buildId,
  windowsQA: evidence.windowsQA, webQA: evidence.webQA, nativeArtifactIdentity: evidence.nativeIdentity, webArtifactIdentity: evidence.webIdentity,
  plantDecision: evidence.plantDecision, worldInterchange: evidence.interchange,
  worldFbxSHA256: manifest.geometry.worldFbxSHA256, travelerFbxSHA256: manifest.geometry.travelerFbxSHA256,
  webPayloadBytes: payload.bytes, performanceScope: performance,
  packageVerification: evidence.packageVerification, packageVerificationPassed: false,
  releaseHTTPVerification: evidence.releaseHTTPVerification, releaseHTTPVerified: false,
  newGaitVideoReviewed: false, visualAcceptance: visual, aestheticObjectiveAchieved: false };
const outputs = { 'PLAY.zh-CN.txt': play, 'AI-使用与素材来源.zh-CN.txt': disclosure,
  'NEXT-STEPS.zh-CN.txt': next, 'production-manifest.json': manifest, 'release-checks.json': releaseChecks };
if (!checkOnly) {
  fs.mkdirSync(draft, { recursive: true });
  for (const [name, value] of Object.entries(outputs)) fs.writeFileSync(path.join(draft, name), typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', 'utf8');
}
console.log(JSON.stringify({ checkOnly, stagingOnly: true, nativeRun, draft, files: Object.keys(outputs), buildIds: manifest.buildIds,
  packageVerificationPassed: false, releaseHTTPVerified: false, newGaitVideoReviewed: false, aestheticObjectiveAchieved: false }, null, 2));
