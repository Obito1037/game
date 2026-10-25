# 《借光岛》第二版交付记录

**Windows / WebGL r10 已打包交付。Windows 七章自动流程通过；Web 启动、输入、暂停/返回及地图/Esc 排版修复通过。按用户要求，本轮到此停止，不再继续美术、性能迭代或追加测试。**

下载：[Windows ZIP](../../../builds/packages/JieGuang-v2-r10-Windows.zip) · [WebGL ZIP](../../../builds/packages/JieGuang-v2-r10-WebGL.zip)。本地试玩：[Windows 入口](../../../Open-JieGuang-V2-Candidate.cmd) · [Web 入口](../../../Open-JieGuang-V2-Web.cmd) · [试玩说明](../../../setup/JieGuang-V2-试玩说明.txt)。

**当前原生性能未达标：r10 各章样本均值 26.09–53.69 FPS，低于要求的 60 FPS。** r8 旧样本的近 60 FPS 结果只保留为历史，不能替代本轮结果。

## 当前构建与交付

| 项目 | 标识 / 证据 | 状态与范围 |
|---|---|---|
| Windows r10 | [build_6ea1dda0e4bd](windows-r10-build.json)；builds/candidates/jieguang-v2-r10/windows/JieGuang.exe | 构建成功，0 errors / 3 warnings：两条 RP 内部名与文件名不一致，一条实验 Pipeline 运行时配置未启用。 |
| r10 原生全章 | [正式报告](../game-v2-native-r10-full/qa-report.json)、[36 图](../game-v2-native-r10-full/) | 标题→七章→尾声完成；解锁 1–6，三谜题经输入，四位尾声 NPC 已访。errors=[]、saveRestored=true，PNG 均为 1600×900。接近目标用诊断传送，未人工走遍全岛。 |
| r10 当前帧时 | [各章原始样本](../game-v2-native-r10-full/qa-report.json) | i5-13500H / Iris Xe / 16GB / D3D11 / PC / 1600×900；各章均值 26.09–53.69 FPS，p95 28.170–65.758ms，每章约 15.02–64.60 秒。未达 60 FPS；无证据将下降归因于 Chrome 或 UI 修改。本轮不再追加性能测试。 |
| Web r10 | [build_24563aa4e1b2](web-r10-build.json)；[正式报告](../game-v2-web-r10/web-report.json)、[8 图审阅](../game-v2-web-r10/read-only-review.json) | 构建成功，0 errors / 3 warnings。真实点击→地图→序章→对白→暂停/返回通过，地图标签及 Esc 排版修复确认。浏览器原始状态为 startup-with-errors：1 条 WASM net::ERR_ABORTED；同 URL 亦有 HTTP 200，ready=100，游戏正常运行。未见 GL 绘制失败，但保留其他控制台警告，**不称浏览器零错误**。 |
| Web r10 短样本 / 音频 | [原始数据及限制](../game-v2-web-r10/read-only-review.json) | Iris Xe / Edge 155 / canvas 1600×900 / Mobile RP renderScale=0.8；约 12 秒标题样本中位 78.213、最低读数 49.875 FPS，序章中位 57.988、最低 46.281 FPS。70.609 秒内 285/285 次非零音频信号，未审听；不代表全程或其他设备性能。 |
| 最终 ZIP / 入口 | [打包校验](packages-r10.json) | Windows：215,693,767 bytes / 176 entries；WebGL：183,559,984 bytes / 10 entries。全部条目路径与解压长度匹配，关键文件解压 SHA256 匹配。两端入口已切换 r10。Web 需本机服务，不能直接双击构建内 index.html。 |
| r10 源码指纹 | [源快照](r10-source-manifest.json)、[对 r8 差异](r10-vs-r8-source-diff.json) | 记录范围内仅 GameUI.cs 变化，修正地图底部章名重叠与两处 Esc 提示排版。57 文件及对应 .meta 的指纹范围不等于完整美术资源闭包。 |

当前[交付与画面对比页](review.html)以 r10 原生流程和 Web 启动为最新证据；环境 11 图仍为 r8 历史美术记录。r10 仅修改 GameUI 三处，场景未改，未把旧图冒充 r10 重拍。所有旧图、失败记录与源码快照保留。此次只静态检查文档链接，未重新渲染页面或启动游戏。

## 原九项要求的当前状态

下表保留已验证范围和未达项；这些限制随候选交付记录，本轮不再由此扩展制作任务。

| # | 用户要求 | 当前状态与限制 |
|---|---|---|
| 1 | A01、新窗桌座锚点与剧情演出 | 新屋已接入，r10 有[第一章](../game-v2-native-r10-full/02-normal.png)与[亮窗](../game-v2-native-r10-full/03-window-lit-grandmother.png)截图；窗桌座全部接触和完整动作尚未逐项验证。 |
| 2 | 38 种 Tripo 道具正确摆放 | A01/A02/A13 与 B02/B03/B04 已接入；r7 有限 A12/A13 往返通过。未逐件证明 38 种均无躺倒、悬空、穿地；见[既有清单](../game-v2-takeover/prop-placement-review.txt)。 |
| 3 | 3m 内草叶野花清晰、远景成片 | [r8 近景](../game-v2-visual-r8/09-meadow-near.png)、[中景](../game-v2-visual-r8/10-meadow-middle.png)、[远景](../game-v2-visual-r8/11-meadow-far.png)保留，草簇重复及裸地过渡仍明显，整体美术未达到参考。 |
| 4 | 现有贴图改善地表、石板路、悬崖 | 黑地和 r4 大片破口已修复；岸脚仍有暗直边，石板路偏暗、零散。按用户指示继续使用现有素材；T/V/S 未生成不列为阻塞。 |
| 5 | 干净海、长反射、暖倒影、岸沫 | [r8 海面](../game-v2-visual-r8/07-sea-earth.png)长反射可见，旧海方角未再见；[朝屋水面](../game-v2-visual-r8/06-sea-house.png)弱暖条尚未隔离窗/挂灯来源。[五个自定义 shader 的 ShaderUtil 消息](custom-shader-messages-web-r9.json)均为空，包括 NightSea。 |
| 6 | 天空/雾/光照接近参考、柔亮干净 | 过亮厚光锥已消退；尚无小王子同构图正式通过结论。白天参考 04 与本版夜景 09 条件不同，不能据此宣称达到参考。 |
| 7 | 标题到尾声无软锁、无报错 | **r10 自动流程通过**，七章完成、每章有图、errors=[]。未将诊断传送流程外推为全岛行走、全部动画或 Web 七章通过。 |
| 8 | Windows 1600×900 ≥60 FPS；Web 普通笔记本 ≥30 FPS | **整体未通过**：r10 Windows 章节均值 26.09–53.69 FPS；Web r10 两个约 12 秒样本的最低引擎区间读数均超过 30 FPS，不能外推为全程或所有普通笔记本达标。 |
| 9 | Windows 与 Web 均可启动 | **r10 双端启动通过**；Web 覆盖地图、序章对白、暂停/返回，保留 1 条未阻断流程的网络取消记录。Web 未跑完整七章。 |

音频仍未做主观审听；Web r10 点击后 70.609 秒内检测 285/285 次非零音频信号，只证明信号存在，未证明点击解锁声音。完整动作、全岛碰撞与所有道具接触尚未全面覆盖。两套 Builder 已用于重建，但未额外做重复构建结果的完整差异验收。

## 历史证据

- [r8 Windows / r9 Web 完整记录](history-r8-web-r9.md)、[历史对比页](review-r8-web-r9.html)、[页面渲染检查](review-render-check.json)：r8 全章均值 59.939–59.975 FPS；r9 序章短样本中位 56.696、最低读数 33.602，标题最低 25.322，均不覆盖 r10。
- [Web r9 审图](../game-v2-web-r9/read-only-review.json)：发现地图“终章/序章”标签重叠、Esc 键帽与说明基线错位，促成本次 r10 UI 修正。
- [Web r8 失败](../game-v2-web-r8-render-diagnostic/decision.json)为构建平台上下文错误；[r8 日志](../game-v2-web-r8-render-diagnostic/r8-build-context.log)仅收集 PC，[r9 日志](../game-v2-web-r8-render-diagnostic/r9-build-context.log)包含 Mobile 与 PC，同源重建后恢复绘制。失败画面不作为性能证据。
- [r1–r4 记录](history-r1-r4.md)保留黑地、海方角、岸坡竖条、r4 破片和过亮光束；[r7 审图](../game-v2-native-r7-full/read-only-review.json)保留终章站箱回归，已由 [r8 复验](../game-v2-native-r8-full/read-only-review.json)确认修复。

本轮全流程验证、双端构建启动复验、ZIP 与入口交付已完成，按用户要求停止。已知质量限制随本记录保留，不另行追加迭代。
