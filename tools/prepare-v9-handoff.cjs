// Stage documentation only after actual v9 runtime and portrait-video evidence exists.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),draft=path.join(root,'art/verification/v9-release-draft');
const read=p=>fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,'');
const json=p=>JSON.parse(read(p));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase();
const write=(p,v)=>fs.writeFileSync(path.join(draft,p),typeof v==='string'?v:JSON.stringify(v,null,2)+'\n');
const native=json('art/verification/run-024-v9/runtime-results.json'),web=json('art/verification/web-010-v9/runtime-results.json');
const builds=json('art/verification/v9-build-reports.json'),model=json('art/generated/character-v8/traveler-manifest.json');
const video=json('art/verification/web-v9-portrait-video/capture-manifest.json');
const videoReview=json('art/verification/web-v9-portrait-video/review.json');
if(!web.passed||!video.completed||!videoReview.reviewed||!videoReview.acceptedForLimitedScope||builds.web.result!=='Succeeded'||builds.native.result!=='Succeeded')throw Error('Required acceptance evidence incomplete');
if(!web.realKeyboardPuzzleCompletion||!web.persistedProgressReload||!web.crossOriginIsolated||!web.audioContextResumeObserved)throw Error('Web acceptance claim is missing its recorded evidence');
const nativeChecks=['puzzleCompleted','menuKeyboardStart','pauseStopsMovement','resumeMovement','restartWorks','endingReturnWorks','cabinCollisionWorks','walkwayGroundingWorks','boulderCollisionWorks','observatoryGroundingWorks','observatoryInstrumentCollisionWorks','decorativeLeavesExcluded','pierGroundingWorks','pierRailCollisionWorks'];
if(!nativeChecks.every(k=>native[k])||!native.scrollZoomWorks)throw Error('Native functional check failed');
const fps=view=>web.performanceViews.find(v=>v.view===view)?.medianIntervalFps;
const payload=builds.web.payload,mb=(payload.bytes/1e6).toFixed(1);
fs.mkdirSync(draft,{recursive:true});
const visual='新脸下颊与鼻唇衔接更连贯，粗棕色眼眶和遮住虹膜的高光条减少；眼裂仍窄、侧面较平，嘴部及衣料层次仍简化。整体视觉尚未达到“比参考更惊艳”的目标。';
const performance=`Iris Xe / 1440×900 原生短样本：菜单 ${native.fpsSamples.menu}、总览 ${native.fpsSamples.overview}、漫步视角 ${native.fpsSamples.walking}、近景 ${native.fpsSamples.portrait}、末段 ${native.fpsAtFinalView} FPS。网页各视角 6×500 ms 前台区间指标中位：停步后的漫步视角 ${fps('walking').toFixed(2)}、结尾 ${fps('ending').toFixed(2)}。这些短样本不是持续行走平均、全程最低或独立渲染帧计数，也不支持版本间性能收益结论。`;
const scope=`v9 使用 world-v7 与 character-v8，岛屿 412,815 三角，角色 ${model.triangles.toLocaleString('en-US')} 三角、62 renderer / 28 skinned / 12 bones。身体、两袖、腿鞋、骨架与附件的数据保护检查通过；游戏流程和地面资源保留。
人物面部采用按实际节点间距连续插值的剖面，并重做鼻颊口周、眼裂和闭眼片；头部顶点色与三个眼部底色也有更新，因此新旧脸的收益不能全部归于单一几何修正。眼白/虹膜/瞳孔分别降低光滑度，夜景灯光与 0.23 面部补光保持。
地面根部接触染色仅作为未采用候选保留：固定 A/B 的游玩尺寸收益不足，未加入运行包。其早期“线性暗化”统计误标已更正，实际图像、审计及拒绝理由保留。
修复新版 Input System 归一化滚轮与旧缩放系数不匹配的问题：每刻度距离变化改为 0.35，保留 2.5–10 的距离限制。原生输入正反刻度及网页真实滚轮分别验证。`;
const validation=`Windows 构建 ${builds.native.buildId}：三章通关、键盘启动、行走、暂停恢复、重开、返回结尾和既有碰撞/接地检查通过；16/16 主石指定方向探测通过。两只实际蒙皮鞋底 ${native.soleGroundSamples} 个静止采样，最小净空 ${native.minimumIdleSoleClearanceMetres} m，不能据此证明所有动态姿态。
Web 构建 ${builds.web.buildId}：真实键盘通关、刷新续玩、默认音频恢复和跨源隔离通过；浏览器异常数组为空。Unity 兼容性提示见原日志，不能称日志完全无提示。
本轮真实鼠标环视/缩放后的自然待机与眨眼录像见 web-v9-portrait-video/；录像审查范围和结论见 review.json。该路线不覆盖所有转头、眨眼中间姿态或完整步态，录制帧率不是游戏帧率。
${performance}
当前压缩网页四个核心文件共 ${payload.bytes.toLocaleString('en-US')} bytes（约 ${mb} MB）；缓存下的本机结果不代表首次网络加载速度。`;
let play=read('PLAY.zh-CN.txt');
const prefix=play.split('当前交付与验证范围')[0].replace('中文试玩说明 · v8','中文试玩说明 · v9').replace('合计约 48.7 MB',`合计约 ${mb} MB`);
const suffix=play.slice(play.indexOf('素材与参赛'));
write('PLAY.zh-CN.txt',prefix+'当前交付与验证范围\n\n'+scope+'\n\n'+validation+'\n\n'+visual+'\n\n原生证据：art/verification/run-024-v9/。网页证据：art/verification/web-010-v9/。\n固定近景对照：v9-face-study-baseline/、v9-face-study-candidate/、v9-face-study-eye-material/。\n实际游玩截图与对照页：art/verification/visual-review.html。较近的固定镜头属于造型诊断，不是正常游戏镜头。\n\n'+suffix);
write('AI-使用与素材来源.zh-CN.txt',`借光岛 v9 · 制作记录与 AI 使用披露

用户提出单人参赛、48 小时范围、参考网站与视觉要求。Blender 生产脚本、角色和场景、Unity 程序、程序材质、音频合成、验收脚本及说明由 Codex 代理生成或修改；不把尚未发生的工作写成学生已经完成的贡献。用户后续取舍、修改、试玩和最终提交须据实补记。
天空由内置 image_gen 按原创提示生成；模型没有使用参考游戏资产，音乐为本地原创合成，无第三方录音采样。当前未代为报名或发布公网。

本轮制作
${scope}
角色脚本 art/blender/build_traveler_v8.py 读取冻结 character-v7/traveler.blend，并复用 v6/v7 的纯函数；完整保留 character-v5/v6/v7 及其脚本、清单以复现来源链。世界仍使用 build_island_v7.py、world-v7/，其 world-v6 来源保持。
继续使用 Blender 自带骨架与权重，未使用 Auto-Rig Pro。
FBX/GLB 中性与弯曲姿态、颜色、闭眼遮挡检查通过；48 个非目标网格、26 个非目标材质和所有骨架/枢轴/附件保护检查通过。Unity 使用 FBX，改动网格的角法线最大误差约 0.0445°。GLB 严格全角法线检查保留失败：6 个零面积线端点在 Blender 回读时得到回退法线；有面积面最大误差约 0.2015°。不得写成所有格式所有检查全通过。
详细报告：art/generated/character-v8/review.zh-CN.txt、v7-preservation-file-verification.json、frozen-export-verification.json、color-interchange-verification.json、blink-verification.json。
未采用地面候选由 build_meadow_contact_v9.py 从原固定种子数学算法重新生成，旧 PNG 仅作只读比较；无接触输出与原图字节一致。它没有进入运行资源，误标修正及审计位于 art/generated/meadow-v9/ 和 art/verification/v9-ground-contact-study/。

字体与参考
字体为 Noto Serif CJK SC 的改名子集 BorrowedLight Story Serif，SIL Open Font License 1.1；完整字体、子集与许可在 art/generated/fonts/，复现脚本 tools/font-subset/build_subset.py。许可和修改记录随构建提供。
视觉参考为 Saccc_c：https://littleprince.dev/ 与 https://x.com/Saccc_c/status/2110694725640474759 。仅参考气氛与叙事表达，没有复制其程序、角色、模型、音频或原作文字。参考截图仅作本地研究，不打包为本作素材。

本轮实机证据
${validation}
固定脸部三组对照采用同机位、姿态、夜景灯光；截图条件与材料差异在各目录的 capture-condition-comparison.json。相机比正常游玩更近，不能混称正常游戏画面。实际待机眨眼录像由真实输入采集，没有注入角色或相机变换。
v8 上观星台录像、v7 GPU 分析等为历史证据，不替代 v9 当前性能或动态验收。来源与当前构建：art/production-manifest.json；原始画面：art/verification/visual-review.html。
${visual}
提交时按比赛正式格式和本人实际贡献如实填写 AI 协作记录。
`);
let next=read('setup/NEXT-STEPS.zh-CN.txt');
write('NEXT-STEPS.zh-CN.txt',next.slice(0,next.indexOf('既有版本已完成')).replace('（v8）','（v9）')+`《借光岛》v9 的 Windows 与 WebGL 构建和实际运行验证已完成。
试玩：双击上一级 Open-Borrowed-Light.cmd 或 Open-Borrowed-Light-Web.cmd；网页仅本机提供服务。
${scope}

${validation}

原生：art/verification/run-024-v9/；网页：art/verification/web-010-v9/；眨眼录像：art/verification/web-v9-portrait-video/。
固定脸部对照、未采用地面试验与限制见 art/verification/visual-review.html。
${visual}
旧版 v8 Windows 包与 Web 文件保存在 builds/archive/，完整复现依赖见 AI-使用与素材来源.zh-CN.txt。

`+next.slice(next.indexOf('已修复的首次导入问题：')));
const manifest=json('art/production-manifest.json');
manifest.revision='v9';delete manifest.inProgressRevision;delete manifest.inProgressScope;
manifest.authoring.character='generated/character-v8/traveler.blend';manifest.authoring.characterScript='blender/build_traveler_v8.py';
manifest.buildIds={windows:builds.native.buildId,web:builds.web.buildId};
manifest.geometry.travelerTriangles=model.triangles;manifest.geometry.travelerFbxSHA256=model.sha256['traveler.fbx'].toUpperCase();
manifest.webPayload=payload;
manifest.verification.characterRoundTrip='generated/character-v8/review.zh-CN.txt: 77132 triangles, 62 renderers/28 skinned, 4 armatures/12 bones. 48 non-target meshes, 26 non-target materials and all rigs/pivots/attachments preserved. FBX posed/color/blink/normal checks passed. GLB strict all-corner normals fail at six zero-area line endpoints; drawable-face normals passed.';
manifest.verification.windowsRuntime=validation.split('Web 构建')[0]+' '+performance;
manifest.verification.webRuntime='verification/web-010-v9/runtime-results.json; real-keyboard completion, reload persistence, audio resume and cross-origin isolation passed. '+performance;
manifest.verification.finalVisualComparison=visual;
manifest.verification.shaderChecks='Eye smoothness Ivory=.18, AmberRim/Chestnut=.32, Pupil=.50; catchlight .72. Captured A/B confirms iris-obscuring strip removed. Skin/cloth/world shader and night-light settings unchanged. 25 static-batched island renderers and 1 starfield renderer remain. No new GPU profile.';
delete manifest.verification.browserGait;
manifest.verification.browserPortrait='verification/web-v9-portrait-video/review.json: actual mouse/keyboard camera control followed by normal idle/blink recording; limited visible-pose review, not exhaustive animation or FPS coverage.';
manifest.verification.rejectedGroundCandidate='verification/v9-ground-contact-study/review.zh-CN.txt: root contact albedo candidate rejected; original ground remains. Earlier encoded-vs-linear darkening labels corrected in retained audit.';
manifest.delivery={package:'../builds/BorrowedLight-Windows.zip',packageVerification:'verification/v9-package-verification.json',previousStableWindowsArchive:'../builds/archive/BorrowedLight-v8-Windows.zip',previousStableWebArchive:'../builds/archive/BorrowedLight-v8-Web/',releaseHTTPVerification:'verification/v9-release-http-verification.json'};
manifest.aestheticObjectiveAchieved=false;write('production-manifest.json',manifest);
write('release-checks.json',{date:'2026-10-21',revision:'v9',status:'Windows and normal browser acceptance passed; limited actual portrait idle/blink video reviewed. Overall aesthetic objective remains unachieved.',windowsBuild:builds.native.buildId,webBuild:builds.web.buildId,windowsQA:'run-024-v9/runtime-results.json',webQA:'web-010-v9/runtime-results.json',webArtifactIdentity:'web-010-v9/artifact-identity.json',portraitVideo:'web-v9-portrait-video/capture-manifest.json',portraitReview:'web-v9-portrait-video/review.json',faceComparisons:['v9-face-study-candidate/capture-condition-comparison.json','v9-face-study-eye-material/capture-condition-comparison.json'],rejectedGroundCandidate:'v9-ground-contact-study/review.zh-CN.txt',performanceScope:performance,worldFbxSHA256:manifest.geometry.worldFbxSHA256,travelerFbxSHA256:manifest.geometry.travelerFbxSHA256,webPayloadBytes:payload.bytes,visualAcceptance:visual,aestheticObjectiveAchieved:false,packageVerification:'v9-package-verification.json',packageVerificationPassed:false,releaseHTTPVerification:'v9-release-http-verification.json',releaseHTTPVerified:false});
write('handoff-data.json',{visual,scope,validation,performance});
console.log(JSON.stringify({draft,files:fs.readdirSync(draft),nativeBuild:builds.native.buildId,webBuild:builds.web.buildId},null,2));
