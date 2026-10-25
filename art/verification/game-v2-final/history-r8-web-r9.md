# 《借光岛》第二版验收记录

**当前可试玩候选：Windows r8 七章自动流程通过；同源 Web r9 启动、序章输入及暂停/恢复通过。第二版仍未通过完整美术与性能验收，未公开发布。**

本地入口：[Windows](../../../Open-JieGuang-V2-Candidate.cmd) · [浏览器版](../../../Open-JieGuang-V2-Web.cmd) · [试玩说明](../../../setup/JieGuang-V2-试玩说明.txt)。Web 请通过入口启动本机服务，不直接双击构建内的 `index.html`。

r8 [重逢画面](../game-v2-native-r8-full/06-reunion-hands.png)中双方站在同一栈桥板面，已修复 r7 的主角站箱回归；[A16 大灯](../game-v2-native-r8-full/05-dengbo-seated.png)顶部已接到实际挂钩。[定向审图报告](../game-v2-native-r8-full/read-only-review.json)另确认分光、坐姿/手杖、窗内人物与 UI 的已修复状态保持，未把静态画面当作完整动作验收。

最新环境图为 r8：[02 房前](../game-v2-visual-r8/02-house-window.png)、[06 朝屋海面](../game-v2-visual-r8/06-sea-house.png)、[07 地光海面](../game-v2-visual-r8/07-sea-earth.png)、[08 海岸](../game-v2-visual-r8/08-coast.png)。所示视角没有 r4 的锯齿破片和过亮厚光锥，长反射与连续天际线保留。06 近船水面有弱暖条，**尚未隔离窗/挂灯来源及亮灭同步**；07 月牙不在镜头内。岸底暗直边、草簇重复及裸地过渡仍需打磨，不能宣称达到参考质量。

[本地画面对比页](review.html)现以 r8 为主图，r5/r4/r3 和中间 Editor 画面均保留历史入口。

## 最新候选与证据

| 项目 | 标识 / 证据 | 当前结论 |
|---|---|---|
| Windows r8 构建 | [build_a68184bd1ea9](windows-r8-build.json)；`builds/candidates/jieguang-v2-r8/windows/JieGuang.exe` | Succeeded，0 errors / 3 warnings；两条 RP 内部名与文件名不一致，一条实验 Pipeline 运行时配置未启用。 |
| r8 原生全章 | [正式报告](../game-v2-native-r8-full/qa-report.json)、[审图报告](../game-v2-native-r8-full/read-only-review.json)、[36 图目录](../game-v2-native-r8-full/) | 标题→七章→尾声完成，解锁 1–6，三谜题经输入，四位尾声 NPC 已访，errors=[]、saveRestored=true。36 图均实测 1600×900；定向目检 9 图。接近目标用诊断传送，不是人工走遍全岛。 |
| r8 章节帧时 | [各章原始样本](../game-v2-native-r8-full/qa-report.json) | i5-13500H / Iris Xe / 16GB / D3D11 / PC / 1600×900；各章均值 59.939–59.975 FPS，p95 16.702–16.725ms，每章约 14.84–63.88 秒。自动正常/剧情镜头，排除预热、截图与传送稳定；不是全岛持续移动最低帧率。 |
| r8 原生环境 | [11 张固定视角](../game-v2-visual-r8/)、[Player.log](../game-v2-visual-r8/Player.log)、[诊断报告](../game-v2-visual-r8/render-study.json) | PNG 实测 1600×900，日志未检出 Error/Exception；本次目检 02/06/07/08/09。采集与 Web 构建并行，且 `samples=[]`、`walkResult=""`，仅作画面证据，不提供性能或实走结论。 |
| 码头往返（r7 历史） | [报告](../game-v2-walk-r7/render-study.json)、[58 点坐标](../game-v2-walk-r7/walk-positions.csv)、[A13 停稳](../game-v2-walk-r7/walk-A13-stopped.png)、[返回停稳](../game-v2-walk-r7/walk-return-stopped.png) | out=True / back=True，58 点均 grounded，最低 rootY=2.490，最远 z=-8.717。起点放置后经 GameInput.Hold→PlayerController→CharacterController 实走；仅该路线，非手工按键或全岛验收，不冒充 r8 重测。 |
| Web r9 构建与启动 | [build_0c4ae14117f9](web-r9-build.json)；`builds/candidates/jieguang-v2-r8/web-r9/`；[正式浏览器报告 / 8 图](../game-v2-web-r9/web-report.json) | 同源重新构建成功，0 errors / 3 warnings；真实点击标题、进入序章、推进对白、暂停/恢复，errors=[]。[独立 GL 诊断](../game-v2-web-r9-render-diagnostic/gl-diagnostic.json) 24,755 次绘制、0 失败。实际输出 [174,572,270 bytes](web-r9-output-inventory.json)；BuildReport 的 6,135 bytes 未计 Build 资源。 |
| Web 短样本与音频信号 | [正式报告](../game-v2-web-r9/web-report.json)；Iris Xe / Edge 155 / canvas 1600×900 / Mobile RP renderScale=0.8 | 序章约 12 秒 Unity interval FPS 中位 56.696、最低读数 33.602；标题中位 73.969、最低 25.322，**未达到全面 ≥30 的证明**。70.591 秒检测 284/284 次非零音频信号；未审听。canvas 尺寸不等于内部渲染尺寸。 |
| 冻结源指纹 | [r8](r8-source-manifest.json)、[r8 对 r7](r8-vs-r7-source-diff.json)、[Web r9 后复核](r8-post-web-r9-source-check.json) | 57 文件及对应 .meta 与 Windows r8 全部匹配，包括 shader、RP 和 ProjectSettings；Web 修复未改 runtime/配置。r8 对 r7 仅两项 C# 修改及其 prefab/主场景变化。此范围不是完整美术资源闭包。 |

r8 全章前 `chapter/unlocked/debugStart` 三键均不存在，结束后报告确认存档恢复、进程退出。此结论来自完整流程报告，环境固定截图不单独证明从零逐章解锁。

## 九项验收状态与剩余证据

| # | 用户要求 | 现有证据 / 状态 | 剩余证据 |
|---|---|---|---|
| 1 | A01、新窗桌座锚点与剧情演出 | r8 [第一章开场](../game-v2-native-r8-full/02-normal.png)、[亮窗演出](../game-v2-native-r8-full/03-window-lit-grandmother.png)已采集；[尾声房前固定视角](../game-v2-visual-r8/02-house-window.png)补充展示新屋。 | 窗桌座接触仍需核对；建议侧视检查臀/手/脚与椅桌，头部高光仍需注意。 |
| 2 | 38 种 Tripo 道具全部正确摆放 | A01/A02/A13 与 B02/B03/B04 已接入；r7 有限 A12/A13 往返通过，未逐件验收。 | 按原要求提供环岛 8 图，证明所有道具无躺倒、悬空、穿地；建议逐件映射 38 种便于复核。核对 A06 尺寸、A07 宽/窄朝向及剧情道具状态。见[清单](../game-v2-takeover/prop-placement-review.txt)。 |
| 3 | 3m 内草叶野花清晰，远景成片 | r8 [近景](../game-v2-visual-r8/09-meadow-near.png)、[中景](../game-v2-visual-r8/10-meadow-middle.png)、[远景](../game-v2-visual-r8/11-meadow-far.png)已采集，整体审美尚未通过。 | 近中远可读性和成片效果仍需审美复核；建议另查风动、LOD 与路径过渡，静态图不证明动态平顺。 |
| 4 | 现有贴图改善后的地表、石板路、悬崖 | 黑地与 r4 破片已修复，r8 所示岸壁连续；按用户后续指示使用现有素材推进。 | 补齐地表/石板路/悬崖近、中、远景对应证据，核对石板路可读性、岸底暗直边、坡面纹理及接触；不等待未生成贴图。 |
| 5 | 干净海、长反射、暖倒影、岸沫 | r8 06/07/08 有长带、岸沫与弱暖条，未见旧海方角。 | 窗口和灯笼暖倒影仍需明确证据；建议分别亮→灭→亮核验来源。按原要求检查 NightSea 的 ShaderUtil 警告。 |
| 6 | 天空/雾/光照接近参考，柔亮干净 | r8 保持薄光束改善；参考 04 与夜景 09 条件不同。 | 与小王子同构图的正式对比，冷暖层次、暗部、Bloom、月牙与章节雾；**跨昼夜图不证明达到参考**。 |
| 7 | 标题到尾声无软锁、无报错 | **本项自动流程通过**：r8 七章完成、每章有图、errors=[]，干净解锁及终章同板面复验通过。 | 更广玩法收尾仍需核对暂停/重进、完整动作过渡和全岛行走，不从传送流程外推；折信 B03 的可辨识度归入道具复核，不否定本项流程结果。 |
| 8 | Windows 1600×900 ≥60 FPS；WebGL 普通笔记本 ≥30 FPS | **尚未完整通过**：原生章节均值 59.939–59.975；Web 序章短样本中位 56.696、最低读数 33.602，标题最低 25.322。 | 保留短样本、机器和 renderScale 条件；不能宣称持续最低帧率达标。Web GetMetricsInfo interval 为引擎报告读数，不是独立逐帧计数；浏览器 rAF 不能替代 Unity 渲染帧率。 |
| 9 | Windows 与 WebGL 均可启动 | **双端启动通过**：Windows r8 完整自动流程；Web r9 真实点击进入序章、对白、暂停/恢复，场景几何正常，errors=[]。 | 启动结论不外推为 Web 七章流程、美术或性能全部通过；本地入口及精确构建标识见上。 |

额外收尾：海浪/风/夜虫、主题和交互音效仍需两端实际审听；Web r9 已检测真实音频图输出 70.591 秒非零信号，不能据此判定内容和听感。Build Island V2 + Build Main Scene 必须能从头重建相同结果；重复构建比对是建议的验证方法。UI 沿用认可基线；只用 Input System，经 GameInput 输入。T/V/S 新素材未制作，按用户指示用现有素材推进，**不列为等待阻塞**。

<details>
<summary>展开中间 Editor 画面与旧候选历史</summary>

- [Editor r7 归档](../game-v2-editor-r7/archive-manifest.json)：15 邮差坐姿、16 灯伯坐姿、17 挂钩试摆，均 1600×900，复制 SHA256 与源一致；均属中间画面，15 早于后续手杖前移。
- [Editor r5 归档](../game-v2-editor-r5/archive-manifest.json)：12/13 早于 T04 岩纹修正，14 早于最后 CoastalCliff 材质替换，不代表原生最终图。
- r1 未执行 prefab 重建；r2 存档解锁被并发旧进程污染；r3 修复黑地/海方角但岸坡竖条未合格；r4 破片和过亮光束明确拒绝。[r1–r4 完整历史](history-r1-r4.md)。
- [r5 环境图](../game-v2-visual-r5/)与[固定机位性能](../game-v2-render-r5/render-study.json)保留。C-two-cascades 当时是无改动项，不能推断收益；[后台采样](../game-v2-render-r5/gpu-context.json)仍见 GameViewerServer 8.7–12.8%，不称完全无后台。
- r5 行走 x=10 撞原旗杆；r6 仅将诊断路线改为 x=9.4 绕行，**不是游戏碰撞修复**。[r6 完整流程](../game-v2-native-r6-full/qa-report.json)、[审图](../game-v2-native-r6-full/read-only-review.json)保留。
- [r7 流程报告](../game-v2-native-r7-full/qa-report.json)通过，但[审图](../game-v2-native-r7-full/read-only-review.json)发现终章站箱回归，画面拒绝，已由 r8 复验修复。
- [Web r8 失败画面](../game-v2-web-r8/04-prologue-opening.png)仅余 UI、天空与光粒，不可试玩；[诊断](../game-v2-web-r8-render-diagnostic/decision.json)记录附加阴影 sampler 与颜色 dummy 纹理不匹配。[r8 预处理日志](../game-v2-web-r8-render-diagnostic/r8-build-context.log)仅收集 PC；切至 WebGL 后同源重建的 [r9 日志](../game-v2-web-r8-render-diagnostic/r9-build-context.log)包含 Mobile 与 PC，绘制恢复。根因为构建平台上下文；失败帧率不作为性能证据，原图和日志保留。
- 源码历史：[r5](r5-source-manifest.json) → [r6](r6-source-manifest.json)（[差异](r6-vs-r5-source-diff.json)）→ [r7](r7-source-manifest.json)（[差异](r7-vs-r6-source-diff.json)）；快照保留。
- takeover 的 07/08 窗边图仅 Play 试摆，不替代保存重建后的验收。

历史结论不自动转为当前候选通过；既有截图、旧资源和记录均保留。

</details>

下一步：补齐剩余美术、摆放、性能和音频审听证据。双端入口可试玩不代表第二版全部要求已完成。
