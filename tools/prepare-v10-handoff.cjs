// Validate current v10 evidence, then stage documentation only. Never promotes a build.
// Usage: node tools/prepare-v10-handoff.cjs [--check-only]
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const draft = path.join(root, 'art/verification/v10-release-draft');
const args = process.argv.slice(2);
if (args.some(arg => arg !== '--check-only')) throw new Error('Only --check-only is supported.');
const checkOnly = args.includes('--check-only');
const evidence = {
  builds: 'art/verification/v10-build-reports.json',
  windowsQA: 'art/verification/run-025-v10/runtime-results.json',
  nativeIdentity: 'art/verification/run-025-v10/build-evidence.json',
  boulderProbes: 'art/verification/run-025-v10/boulder-approaches.json',
  webQA: 'art/verification/web-011-v10/runtime-results.json',
  webIdentity: 'art/verification/web-011-v10/artifact-identity.json',
  gaitManifest: 'art/verification/web-v10-gait-video/capture-manifest.json',
  gaitReview: 'art/verification/web-v10-gait-video/review.json',
  gaitIdentity: 'art/verification/web-v10-gait-video/artifact-identity.json',
  packageVerification: 'art/verification/v10-package-verification.json',
  releaseHTTPVerification: 'art/verification/v10-release-http-verification.json'
};
const assert = (value, message) => { if (!value) throw new Error(message); };
function local(file) {
  const resolved = path.resolve(root, file);
  const relative = path.relative(root, resolved);
  assert(relative && !relative.startsWith('..') && !path.isAbsolute(relative), 'Path outside workspace: ' + file);
  return resolved;
}
const read = file => fs.readFileSync(local(file), 'utf8').replace(/^\uFEFF/, '');
const json = file => JSON.parse(read(file));
const exists = file => fs.existsSync(local(file));
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(local(file))).digest('hex').toUpperCase();
const sameHash = (a, b) => typeof a === 'string' && typeof b === 'string' && /^[\da-f]{64}$/i.test(a) && a.toUpperCase() === b.toUpperCase();
const finite = (n, label) => { assert(Number.isFinite(n), 'Missing finite metric: ' + label); return n; };
const emptyErrors = (data, label) => assert(Array.isArray(data.errors) && data.errors.length === 0, label + ' has missing/non-empty errors.');
const builds = json(evidence.builds);
const native = json(evidence.windowsQA);
const web = json(evidence.webQA);
const video = json(evidence.gaitManifest);
const videoReview = json(evidence.gaitReview);
assert(builds.revision === 'v10', 'Build reports must identify revision v10.');
for (const [key, platform] of [['native', 'StandaloneWindows64'], ['web', 'WebGL']]) {
  const build = builds[key];
  assert(build && build.status === 'completed' && build.result === 'Succeeded', key + ' build did not succeed.');
  assert(build.platform === platform && /^build_[a-z0-9]+$/i.test(build.buildId), key + ' build identity/platform invalid.');
  assert(build.totalErrors === 0, key + ' build has errors.');
  emptyErrors(build, key + ' build');
}
assert(builds.native.buildId === 'build_6b2f1936c854', 'Native report differs from the reviewed v10 candidate; re-review before changing this guard.');
const nativeChecks = ['puzzleCompleted', 'menuKeyboardStart', 'pauseStopsMovement', 'resumeMovement', 'restartWorks',
  'endingReturnWorks', 'cabinCollisionWorks', 'walkwayGroundingWorks', 'boulderCollisionWorks',
  'observatoryGroundingWorks', 'observatoryInstrumentCollisionWorks', 'decorativeLeavesExcluded',
  'pierGroundingWorks', 'pierRailCollisionWorks', 'scrollZoomWorks'];
for (const key of nativeChecks) assert(native[key] === true, 'Native QA failed/missing: ' + key);
assert(native.walkingDistance > 0 && native.riggedSoles === 2 && native.soleGroundSamples > 0, 'Native movement/sole evidence missing.');
finite(native.minimumIdleSoleClearanceMetres, 'minimumIdleSoleClearanceMetres');
assert(Math.abs(native.normalizedScrollStepMetres - 0.35) < 0.0001, 'Normalized scroll step mismatch.');
for (const key of ['menu', 'overview', 'walking', 'portrait']) assert(finite(native.fpsSamples?.[key], key) > 0, 'Native FPS sample invalid.');
assert(finite(native.fpsAtFinalView, 'fpsAtFinalView') > 0, 'Final FPS sample invalid.');
assert(native.width === 1440 && native.height === 900, 'Native sample dimensions changed; revise description.');
const nativeIdentity = json(evidence.nativeIdentity);
assert(nativeIdentity.buildId === builds.native.buildId, 'Native QA build ID does not match reports.');
const nativeDirectory = path.dirname(local(builds.native.outputPath));
assert(path.resolve(local(nativeIdentity.playerDirectory)) === nativeDirectory, 'Native QA used another player directory.');
const nativeFiles = new Map((nativeIdentity.files || []).map(file => [file.name.replace(/\\/g, '/'), file]));
for (const name of ['BorrowedLight.exe', 'UnityPlayer.dll', 'BorrowedLight_Data/resources.assets', 'BorrowedLight_Data/Managed/Assembly-CSharp.dll']) {
  const item = nativeFiles.get(name);
  assert(item && sameHash(sha(path.join(nativeDirectory, name)), item.sha256), 'Native QA file changed: ' + name);
}
const probes = json(evidence.boulderProbes);
assert(probes.allPassed === true && probes.probes?.length === 16 && probes.probes.every(p => p.startsClear === true && p.blockedBeforeCentre === true), 'Boulder probes incomplete.');
for (const key of ['passed', 'realKeyboardPuzzleCompletion', 'persistedProgressReload', 'crossOriginIsolated', 'audioContextResumeObserved']) {
  assert(web[key] === true, 'Web QA failed/missing: ' + key);
}
emptyErrors(web, 'Web QA');
assert(web.width === 1440 && web.height === 900, 'Web sample dimensions changed; revise description.');
assert(web.defaultBrowserAutoplayPolicy === true, 'Audio evidence must use the default browser policy.');
const payload = builds.web.payload;
assert(payload && Number.isSafeInteger(payload.bytes) && payload.bytes > 0 && payload.files?.length === 4, 'Web core payload missing.');
assert(new Set(payload.files.map(f => f.name)).size === 4, 'Duplicate web payload name.');
assert(payload.files.reduce((sum, f) => sum + f.bytes, 0) === payload.bytes, 'Web payload byte sum mismatch.');
for (const file of payload.files) {
  assert(path.basename(file.name) === file.name && !file.name.includes('\\') && Number.isSafeInteger(file.bytes) && file.bytes > 0, 'Invalid payload file.');
  const actual = path.join(local(builds.web.outputPath), 'Build', file.name);
  assert(fs.statSync(actual).size === file.bytes && sameHash(sha(actual), file.sha256), 'Web candidate bytes/hash changed: ' + file.name);
}
function verifyWebIdentity(file, label) {
  const identity = json(file);
  assert(identity.passed === true && identity.buildId === builds.web.buildId && identity.declaredBuildMatches === true && identity.requestedAllCurrentFiles === true, label + ' identity is incomplete.');
  for (const item of payload.files) {
    const record = identity.files?.find(f => f.name === item.name);
    assert(record?.matches === true && record.bytes === item.bytes && sameHash(record.httpSHA256, item.sha256) && sameHash(record.diskSHA256, item.sha256), label + ' payload mismatch: ' + item.name);
  }
  return identity;
}
verifyWebIdentity(evidence.webIdentity, 'Web QA');
assert(video.completed === true && !video.error && video.requestedRevision === 'v10', 'Gait capture is incomplete or wrong revision.');
emptyErrors(video, 'Gait capture');
assert(videoReview.reviewed === true && videoReview.acceptedForLimitedScope === true, 'Gait visual review not accepted.');
if (videoReview.declaredBuildId !== undefined) assert(videoReview.declaredBuildId === builds.web.buildId, 'Gait review build mismatch.');
verifyWebIdentity(evidence.gaitIdentity, 'Gait capture');
assert(typeof video.recordedVideo === 'string' && video.recordedVideo.length > 0, 'Gait video filename missing.');
const gaitDirectory = path.dirname(local(evidence.gaitManifest));
const gaitVideo = local(path.join(gaitDirectory, video.recordedVideo));
assert(path.relative(gaitDirectory, gaitVideo).split(path.sep)[0] !== '..' && fs.statSync(gaitVideo).size > 0, 'Gait video missing/outside session.');
const frames = view => {
  const result = web.performanceViews?.find(v => v.view === view);
  assert(result?.allSamplesForeground === true && result.samples?.length === 6 && result.intervalMs === 500, 'Web sample scope differs: ' + view);
  assert(result.samples.every(s => s.visibility === 'visible' && s.focused === true && Number.isFinite(s.fps)), 'Web samples lack foreground evidence: ' + view);
  return finite(result.medianIntervalFps, view + ' medianIntervalFps');
};
const walkingFPS = frames('walking'), endingFPS = frames('ending');
const model = json('art/generated/character-v9/traveler-manifest.json');
const preservation = json('art/generated/character-v9/v8-preservation-file-verification.json');
assert(model.version === 9 && model.mesh_renderers === 62 && model.skinned_meshes === 28 && model.bones === 12, 'Character budget changed.');
assert(preservation.passed === true && preservation.object_contract_equal === true && preservation.material_graphs_equal === true, 'Character preservation checks failed.');
assert(preservation.meshes?.length === 62 && preservation.meshes.filter(m => m.is_target === true).length === 7 && preservation.meshes.every(m => m.protected_data_equal === true), 'Expected 7 targets / 55 protected meshes.');
for (const name of ['traveler.blend', 'traveler.fbx', 'traveler.glb']) assert(sameHash(sha('art/generated/character-v9/' + name), model.sha256[name]), 'Frozen character file changed: ' + name);
assert(sameHash(sha('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx'), model.sha256['traveler.fbx']), 'Unity uses another traveler FBX.');
for (const file of ['frozen-export-verification.json', 'color-interchange-verification.json', 'target-normal-interchange-verification.json']) {
  const data = json('art/generated/character-v9/' + file);
  for (const format of ['fbx', 'glb']) assert(data[format]?.passed === true, file + ': ' + format + ' failed.');
}
assert(json('art/generated/character-v9/connection-verification.json').passed === true, 'Character connection checks failed.');
const stone = json('art/generated/stone-v10/manifest.json');
assert(sameHash(sha('art/generated/stone-v10/' + stone.originalFile), stone.sha256), 'Original stone texture changed.');
assert(sameHash(sha('GameProject/Assets/BorrowedLight/Resources/Textures/StoneV10.png'), stone.sha256), 'Runtime stone PNG differs from source.');
const foliageReview = json('art/verification/v10-foliage-study/review.json');
assert(foliageReview.reviewed === true && foliageReview.acceptedForLimitedScope === true && foliageReview.recommendedDefault === 'fixed40' && foliageReview.fixed20RecommendedAsDefault === false, 'Foliage Fixed40 selection missing.');
assert(json('art/verification/v10-silhouette-candidate/decision.json').candidateCharacter === 'character-v9', 'Silhouette decision mismatch.');
const previous = json('art/production-manifest.json');
assert(sameHash(sha('art/generated/world-v7/island.fbx'), previous.geometry.worldFbxSHA256), 'Frozen world-v7 geometry changed.');

// Packaging follows documentation staging; absent reports stay explicitly pending.
let packageReport = null, httpReport = null;
if (exists(evidence.packageVerification)) {
  packageReport = json(evidence.packageVerification);
  assert(packageReport.passed === true && packageReport.requiredFilesPresent === true && packageReport.debugFoldersExcluded === true && packageReport.allZipFileHashesMatchCurrentBuild === true && packageReport.failures?.length === 0, 'Package report failed.');
  assert(sameHash(packageReport.nativeResourcesSHA256, nativeFiles.get('BorrowedLight_Data/resources.assets').sha256) && sameHash(packageReport.nativeGameAssemblySHA256, nativeFiles.get('BorrowedLight_Data/Managed/Assembly-CSharp.dll').sha256), 'Package report belongs to another native build.');
  assert(sameHash(sha('builds/BorrowedLight-Windows.zip'), packageReport.zipSHA256) && fs.statSync(local('builds/BorrowedLight-Windows.zip')).size === packageReport.zipBytes, 'Package changed after verification.');
}
if (exists(evidence.releaseHTTPVerification)) {
  httpReport = json(evidence.releaseHTTPVerification);
  assert(httpReport.passed === true && httpReport.revision === 'v10' && httpReport.indexReferencesCurrentFiles === true, 'Release HTTP report failed/wrong revision.');
  for (const file of payload.files) {
    const record = httpReport.files?.find(f => f.name === file.name);
    assert(record?.matches === true && record.bytes === file.bytes && sameHash(record.httpSHA256, file.sha256) && sameHash(record.diskSHA256, file.sha256), 'Release HTTP payload mismatch: ' + file.name);
  }
}
const oldPlay = read('PLAY.zh-CN.txt');
for (const file of ['setup/Check-Tools.ps1', 'setup/tool-status.json', 'Open-Borrowed-Light.cmd', 'Open-Borrowed-Light-Web.cmd', 'Open-GameProject.cmd']) {
  assert(exists(file), 'User handoff references a missing file: ' + file);
}
const sectionStart = oldPlay.indexOf('当前交付与验证范围');
const sectionEnd = oldPlay.indexOf('素材与参赛');
assert(sectionStart > 0 && sectionEnd > sectionStart, 'PLAY section boundaries changed; review before staging.');
const visual = '固定 A/B 中，主石层理和粗糙感更清楚；角色发缘、肩袖和裤腿轮廓有所改善。植被采用通道同步的 Fixed40，20% 法线混合候选未采用。花草与地面衔接、头发和衣料仍有简化，整体视觉超过参考站的目标尚未证实。';
const scope = `v10 保留 world-v7：岛屿 412,815 三角；角色采用 character-v9：${model.triangles.toLocaleString('en-US')} 三角、62 mesh renderer、28 skinned mesh、4 armatures / 12 bones。\n本轮三项改动：原创 stone-v10 颜色图与三平面投影材质；Foliage Fixed40 的前向／深度／法线／阴影通道风摆同步；角色七个网格的头发、肩袖、衣摆和裤腿轮廓。55 个非目标网格、权重、骨架、材质及脸眼保留；脸部补光仍为 0.23。原地面资源保留，v9 根部染色候选未采用。`;
const performance = `${native.gpu} / 1440×900 原生短样本：菜单 ${native.fpsSamples.menu}、总览 ${native.fpsSamples.overview}、漫步视角 ${native.fpsSamples.walking}、近景 ${native.fpsSamples.portrait}、末段 ${native.fpsAtFinalView} FPS。网页各视角 6×500 ms 前台区间指标中位：停步后的漫步视角 ${walkingFPS.toFixed(2)}、结尾 ${endingFPS.toFixed(2)}。这是短时视角样本，不是持续行走平均、全程最低或独立渲染帧计数；录像帧率不作为游戏 FPS，也不据此宣称版本间性能提升。`;
const modelScope = 'character-v9 的 FBX/GLB 正常及弯曲姿态、颜色和七个目标网格法线回读检查通过；55 个非目标网格及全部权重／骨架／材质保护检查通过，另核对三种姿态的连接边界。它们不构成全地形步态穷举。旧 character-v8 的 GLB 六个零面积下睑／嘴线端点严格全角法线失败是继承限制，本轮七个目标通过不能写成全模型、所有格式重新全面通过。运行时使用 FBX。';
const packageStatus = '运行包完整性记录见 art/verification/v10-package-verification.json，以记录为准。';
const httpStatus = '本机网页文件校验见 art/verification/v10-release-http-verification.json，以记录为准。';
const validation = `Windows 构建 ${builds.native.buildId}：三章通关、键盘启动、行走、暂停恢复、重开、结尾返回、归一化滚轮及既有碰撞／接地检查通过；16/16 主石指定方向探测通过。两只实际蒙皮鞋底共 ${native.soleGroundSamples} 个静止采样，最小净空 ${native.minimumIdleSoleClearanceMetres} m，此数据不覆盖所有动态姿态。\nWeb 构建 ${builds.web.buildId}：真实键盘通关、刷新续玩、默认策略下音频恢复与跨源隔离通过，浏览器异常数组为空。引擎兼容性提示仍按原日志保留，不称日志完全无提示。\n实际键鼠录像与审查：web-v10-gait-video/，reviewed=true、acceptedForLimitedScope=true；仅接受录像中已查看的有限动作与可见范围，不据此证明所有步态、地形或姿态。\n${performance}\n压缩网页四个核心文件合计 ${payload.bytes.toLocaleString('en-US')} bytes（约 ${(payload.bytes / 1e6).toFixed(1)} MB）；本地缓存测试不代表首次网络加载速度。\n${packageStatus}\n${httpStatus}`;
const modelEvidence = 'art/generated/character-v9/review.zh-CN.txt、v8-preservation-file-verification.json、frozen-export-verification.json、target-normal-interchange-verification.json、color-interchange-verification.json、connection-verification.json';
const sourceChain = '角色脚本 art/blender/build_traveler_v9.py 读取冻结 character-v8/traveler.blend，依赖 v8→v7→v6/v5 及相应脚本和清单。世界仍为 build_island_v7.py 与 world-v7/，保留 world-v6 来源链。继续使用 Blender 自带骨架与权重，没有使用 Auto-Rig Pro、Tripo 或 Mixamo 账号。';
const diagnostics = '独立固定诊断：art/verification/v10-stone-study/、v10-foliage-study/、v10-silhouette-candidate/。固定时间、摆位与近镜只支持对应条件下的对照，不冒充正常游玩、动态或性能验证；A/A 存在非零差异，不称像素完全相同。';
const playPrefix = oldPlay.slice(0, sectionStart).replace(/中文试玩说明 · v\d+/, '中文试玩说明 · v10').replace(/压缩游戏数据、代码与加载器合计约 [\d.]+ MB/, `压缩游戏数据、代码与加载器合计约 ${(payload.bytes / 1e6).toFixed(1)} MB`);
const play = playPrefix + '当前交付与验证范围\n\n' + scope + '\n\n' + validation + '\n\n' + visual + '\n\n' + modelScope + '\n\n' + diagnostics + '\n\n正常运行证据：art/verification/run-025-v10/、art/verification/web-011-v10/。画面对照：art/verification/visual-review.html。\n\n' + oldPlay.slice(sectionEnd);
const disclosure = `借光岛 v10 · 制作记录与 AI 使用披露\n\n用户提出单人参赛、48 小时范围和视觉参考。Blender 脚本、模型、Unity 程序、材质、音频合成、验收脚本及文案由 Codex 代理生成或修改；不把尚未发生的工作记为学生已完成的贡献。本人后续创意取舍、修改与试玩应据实补记。没有代为报名或公网部署。\n\n${scope}\n${sourceChain}\n${modelScope}\n模型证据：${modelEvidence}。\n\nstone-v10 与天空均由内置 image_gen 依原创提示生成，来源、提示词和 SHA256 分别在 art/generated/stone-v10/manifest.json 与 art/generated/sky/manifest.json。石纹是生成颜色图及艺术性浅凹凸，不是实测扫描或物理校准材质。世界模型没有重新生成；Foliage Fixed40 只同步既有风摆和法线相关通道，未采用 20% 候选。\n音乐与提示音为本地原创合成，无第三方录音采样。字体为 Noto Serif CJK SC 的改名子集 BorrowedLight Story Serif，SIL OFL 1.1；完整来源、子集许可与修改记录保留于 art/generated/fonts/，复现脚本 tools/font-subset/build_subset.py。\n\n参考：https://littleprince.dev/ 与 https://x.com/Saccc_c/status/2110694725640474759 。仅参考气氛与叙事表达，没有复制其程序、模型、角色、音频或原作文字；研究截图不打包为本作素材。暗夜保护依据见 art/reference/dark-sky-theme-sources.zh-CN.txt；灯光预算是无量纲游戏规则，暖色不代表无生态影响。\n\n${validation}\n\n${diagnostics}\n历史 v8/v9 录像、GLB 检查与 GPU 分析不替代当前 v10 正常玩法和性能证据。${visual}\n提交前按正式模板如实填写 AI 使用环节与本人原创贡献。\n`;
const next = `本地游戏工具与试玩说明（v10）\n\n双击根目录 Open-Borrowed-Light.cmd 或 Open-Borrowed-Light-Web.cmd；网页仅 localhost 服务，没有公网部署。运行包不要求登录 Unity；编辑工程使用 Open-GameProject.cmd 以继承已有进程级代理。详细操作见根目录 PLAY.zh-CN.txt。\n\n${scope}\n\n${validation}\n\n${modelScope}\n\n${visual}\n\n旧版本归档位于 builds/archive/；各版本构建身份和验证范围以对应记录为准。\n\n环境：Unity 6000.3.26f1、Blender 4.5.14 LTS，工具启动器在根目录。编辑时按 AGENTS.md 检查 Unity status 与 pipeline list；Auto-Rig Pro 未安装，Tripo/Mixamo 账号未配置。完整环境检查见 setup/Check-Tools.ps1 和 setup/tool-status.json。\n`;
const manifest = structuredClone(previous);
manifest.revision = 'v10';
delete manifest.inProgressRevision; delete manifest.inProgressScope;
manifest.authoring.character = 'generated/character-v9/traveler.blend';
manifest.authoring.characterScript = 'blender/build_traveler_v9.py';
manifest.authoring.characterDependencies = ['generated/character-v8/', 'generated/character-v7/', 'generated/character-v6/', 'generated/character-v5/'];
manifest.buildIds = { windows: builds.native.buildId, web: builds.web.buildId };
manifest.geometry.travelerTriangles = model.triangles;
manifest.geometry.travelerFbxSHA256 = model.sha256['traveler.fbx'].toUpperCase();
manifest.geometry.travelerSkinnedMeshes = model.skinned_meshes;
manifest.webPayload = payload;
manifest.resources = manifest.resources.filter(item => item.name !== 'StoneV10 original colour texture');
manifest.resources.push({ name: 'StoneV10 original colour texture', source: 'Built-in image_gen; generated/stone-v10/manifest.json', type: 'original AI-generated bitmap; triplanar artistic relief, not measured PBR', sha256: stone.sha256.toUpperCase() });
manifest.verification = {
  blenderInterchange: previous.verification.blenderInterchange,
  purePuzzleRules: previous.verification.purePuzzleRules,
  characterRoundTrip: modelScope + ' ' + modelEvidence,
  windowsRuntime: evidence.windowsQA + ': ' + validation.split('Web 构建')[0],
  webRuntime: evidence.webQA + ': real keyboard completion, reload persistence, default-policy audio resume and cross-origin isolation passed.',
  browserGait: evidence.gaitReview + ': limited actual mouse/keyboard gait-video scope accepted; not exhaustive animation/terrain or FPS coverage.',
  artifactIdentity: [evidence.nativeIdentity, evidence.webIdentity, evidence.gaitIdentity],
  performance,
  shaderChecks: 'Original stone texture/triplanar shallow relief; Foliage Fixed40 auxiliary wind and normal consistency; 20% candidate not adopted. No new GPU profile and no unmeasured zero-cost claim.',
  historicalPortrait: 'verification/web-v9-portrait-video/ is v9 historical evidence, not a v10 portrait re-test.',
  rejectedGroundCandidate: previous.verification.rejectedGroundCandidate,
  scrollInput: 'Existing normalized .35 metres/step and 2.5–10 clamp retained; current native forward/reverse-step QA passed. No separate current web portrait/wheel review claimed.',
  fixedDiagnostics: diagnostics,
  finalVisualComparison: visual
};
manifest.delivery = {
  package: '../builds/BorrowedLight-Windows.zip',
  packageVerification: 'verification/v10-package-verification.json',
  previousStableWindowsArchive: '../builds/archive/BorrowedLight-v9-Windows.zip',
  previousStableWebArchive: '../builds/archive/BorrowedLight-v9-Web/',
  previousStableWebArchivePresent: exists('builds/archive/BorrowedLight-v9-Web'),
  releaseHTTPVerification: 'verification/v10-release-http-verification.json',
  packageVerificationPassed: Boolean(packageReport),
  releaseHTTPVerified: Boolean(httpReport),
  stagingOnly: true
};
if (packageReport) Object.assign(manifest.delivery, { packageSHA256: packageReport.zipSHA256, packageBytes: packageReport.zipBytes });
manifest.aestheticObjectiveAchieved = false;
const releaseChecks = {
  generatedAtUTC: new Date().toISOString(), revision: 'v10', stagingOnly: true,
  runtimeAcceptancePassed: true,
  releaseReady: Boolean(packageReport && httpReport && manifest.delivery.previousStableWebArchivePresent && exists('builds/archive/BorrowedLight-v9-Windows.zip')),
  status: 'Current Windows and normal Web QA passed; limited actual gait video reviewed. Draft generation does not promote artifacts or establish overall visual superiority.',
  windowsBuild: builds.native.buildId, webBuild: builds.web.buildId,
  windowsQA: evidence.windowsQA, webQA: evidence.webQA,
  nativeArtifactIdentity: evidence.nativeIdentity, webArtifactIdentity: evidence.webIdentity,
  gaitVideo: evidence.gaitManifest, gaitReview: evidence.gaitReview, gaitArtifactIdentity: evidence.gaitIdentity,
  fixedDiagnostics: ['v10-stone-study/', 'v10-foliage-study/', 'v10-silhouette-candidate/'],
  performanceScope: performance, worldFbxSHA256: manifest.geometry.worldFbxSHA256,
  travelerFbxSHA256: manifest.geometry.travelerFbxSHA256, webPayloadBytes: payload.bytes,
  packageVerification: evidence.packageVerification, packageVerificationPassed: Boolean(packageReport),
  releaseHTTPVerification: evidence.releaseHTTPVerification, releaseHTTPVerified: Boolean(httpReport),
  previousStableWebArchivePresent: manifest.delivery.previousStableWebArchivePresent,
  visualAcceptance: visual, aestheticObjectiveAchieved: false
};
const handoffData = { revision: 'v10', visual, scope, validation, performance, modelScope, diagnostics,
  buildIds: manifest.buildIds, evidence, webPayload: payload, aestheticObjectiveAchieved: false,
  inputSHA256: Object.fromEntries(Object.entries(evidence).filter(([, file]) => exists(file)).map(([key, file]) => [key, sha(file)])) };
const outputs = {
  'PLAY.zh-CN.txt': play,
  'AI-使用与素材来源.zh-CN.txt': disclosure,
  'NEXT-STEPS.zh-CN.txt': next,
  'production-manifest.json': manifest,
  'release-checks.json': releaseChecks,
  'handoff-data.json': handoffData
};
if (!checkOnly) {
  fs.mkdirSync(draft, { recursive: true });
  for (const [name, value] of Object.entries(outputs)) fs.writeFileSync(path.join(draft, name), typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', 'utf8');
}
console.log(JSON.stringify({ checkOnly, stagingOnly: true, draft, files: Object.keys(outputs), buildIds: manifest.buildIds,
  packageVerificationPassed: Boolean(packageReport), releaseHTTPVerified: Boolean(httpReport), aestheticObjectiveAchieved: false }, null, 2));
