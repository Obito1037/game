# 借光岛

《借光岛》是一款使用 Unity 与 Blender 制作的三维叙事解谜游戏。玩家扮演不会发光的孩子“小灯笼”，在长夜里守护三盏灯，照亮邮差的小路、阿婆的圆窗和等待归船的码头，在与岛民的相遇中理解分享、责任与自己的价值。

当前项目为 **v3 r2**：包含 11 段世界观开篇，以及序章、第一章、第二章、幕间、第三章、终章、尾声共七个流程章节。已制作 Windows 与 WebGL 本地试玩包和参赛材料；尚未完成最终美术与性能验收，也未公开部署网页游戏。

![借光岛标题画面](参赛提交/7_作品截图/01_标题画面.png)

## 克隆与打开

模型、纹理、音频和参赛文件使用 Git LFS。请先安装 Git 与 Git LFS，再克隆，避免仅获得大文件指针：

```powershell
git lfs install
git clone https://github.com/Obito1037/game.git
cd game
git lfs pull
```

使用 Unity Hub 安装 **Unity 6.3 LTS 6000.3.26f1**，并打开 `GameProject/`。首次打开需要下载包依赖并导入资源；包版本由 `GameProject/Packages/manifest.json` 和 `packages-lock.json` 固定，其中 URP 为 `17.0.1`，Input System 为 `1.20.1`。

打开 **`Assets/JieGuang/Scenes/JieGuang_Main.unity`** 后进入 Play 模式。当前运行所需的资源和 `.meta` 文件随工程保存，无需重新生成模型。`Assets/BorrowedLight/` 是此前项目的历史参考，旧场景已在构建列表中禁用，不是当前游戏入口。

Blender 制作环境为 **4.5.14 LTS**。Unity CLI 固定为实验版 `1.0.0-beta.13`，配套 `com.unity.pipeline` 为 `0.8.0-exp.1`；两者用于自动化，不是打开工程的前提。工具安装包、Unity 缓存和 `builds/` 下的历史构建不入库。

## 直接试玩与参赛材料

最终参赛 ZIP、视频、截图、PPT 和说明文件通过 Git LFS 随库保存。交付清单以 [参赛提交/提交清单.txt](参赛提交/提交清单.txt) 为准；部分历史验证文档中的截图数量、PPT 页数及旧 ZIP 名称早于本次材料整理。

| 材料 | 当前内容 |
| --- | --- |
| [参赛打包文件](参赛提交/10_参赛打包文件/借光岛_参赛打包文件.zip) | 一个 ZIP，974,959,925 字节（约 975 MB），191 个文件；含 Windows、WebGL、完整展示视频、作品介绍、运行说明、第三方资源与 AI 使用说明 |
| [作品截图](参赛提交/7_作品截图/) | 10 张 1920×1080 实机截图 |
| [作品评审视频](参赛提交/8_作品评审视频/) | 精华版 4 分 48 秒；完整流程版 11 分 08 秒 |
| [作品汇报 PPT](参赛提交/9_作品汇报PPT/借光岛_作品汇报.pptx) | 16 页，含演讲备注 |
| [AI 工具使用说明](参赛提交/9_作品汇报PPT/借光岛_人工智能工具使用情况说明.docx) | 单独上传用 Word 文件 |

将 ZIP 完整解压后，在 `借光岛_参赛打包文件/01_作品及成果文件/` 中运行：

- Windows：进入 `借光岛_Windows/`，双击 `JieGuang.exe`。
- WebGL：进入 `借光岛_WebGL/`，双击 `Open-Web.cmd`；需安装 Node.js，通过本地 HTTP 服务打开，不能直接双击 `index.html`。

仓库根目录的 `Open-JieGuang-V3.cmd` 和 `Open-JieGuang-V3-Web.cmd` 读取 [候选构建配置](setup/jieguang-v3-candidate.json)，依赖本机 `builds/candidates/jieguang-v3-r2/` 下的解包构建；仅克隆仓库后请先使用参赛 ZIP 试玩，或自行构建。

## 游戏操作

- 标题与地图：点击按钮或按 `Enter` 开始；开篇按 `Tab` 跳过。
- 行走：`WASD` 或方向键移动，左 `Shift` 加速；按住鼠标右键环顾，滚轮调整距离。
- 交互与对话：靠近目标按 `E`；空格、`Enter` 或鼠标点击推进对话。
- 调灯：靠近灯按 `E`，或在解谜阶段按 `Tab` 打开面板；`1/2/3` 选择已解锁灯具，`A/D` 或左右方向键调整方向，空格切换灯罩，`Enter` 检查结果。
- `Esc`：关闭调灯面板或打开/关闭暂停菜单，具体以画面提示为准。

## 构建与制作

在 Unity Build Profiles 中选择 Windows 或 Web 平台，确保构建场景是 `Assets/JieGuang/Scenes/JieGuang_Main.unity`。构建 WebGL 需要安装对应的 Unity Web Build Support 模块。

**跨平台构建前，先切换并确认 Editor 的活动构建目标。** 使用 CLI 时先执行 `switch_build_target`，等待状态完成，确认 `EditorUserBuildSettings.activeBuildTarget` 匹配目标且 `EditorApplication.isCompiling`、`isUpdating` 均为 false，再调用 `build`。只给实验版构建命令传入 `target` 不足以保证 URP 使用正确的平台变体；历史上曾因此出现 WebGL 场景几何消失。切换期间的域重载可能产生过早的失败状态，应以 Editor 重连后的实际状态为准。

如需根据生成器重建，按顺序使用 `JieGuang/Build Island V2 (Tripo props)` 和 `JieGuang/Build Main Scene`；这些操作会重写生成的岛屿与场景，普通试玩无需执行。现有 `tools/jg-v3-pipeline.sh`、`tools/jg-v3-web.sh` 和部分验收脚本保存了原工作站路径、工具依赖及输出清理操作，换机器后应先检查并调整，不要直接作为通用构建入口运行。操作正在运行的 Editor 前，按 [AGENTS.md](AGENTS.md) 检查 `unity status --json` 与 `unity pipeline list --json`，并保持同一时间只有一个自动化操作者。

| 路径 | 内容 |
| --- | --- |
| `GameProject/Assets/JieGuang/` | 当前游戏场景、剧情、交互、UI、角色、环境、动画、声音与渲染资源 |
| `GameProject/Packages/`、`GameProject/ProjectSettings/` | 包依赖锁定和工程设置 |
| `art/design/script/07_完整故事与生图提示词（最终版）.md` | 当前游戏采用的故事来源；文档旧副标题不沿用 |
| `art/design/v3/` | 第三版改进计划和素材提示词 |
| `art/generated/` | 当前制作链的 `characters-v1/`、`env-v1/`、`env-v2/`、`props-v2/`、`props-v2-window/` 等源资源，以及保留的历史资源 |
| `art/blender/`、`art/incoming/` | 资产处理脚本及保留的输入素材 |
| `art/presentation/`、`art/demo-video/` | 参赛文档、演示视频的制作脚本与素材 |
| `art/verification/` | 按版本保存的测试报告、源码快照和保留的画面证据 |
| `tools/`、`setup/` | 项目自写的启动、构建、打包和验证脚本 |
| `参赛提交/` | 本轮整理完成的参赛交付文件 |

旧 Borrowed Light 的角色与世界生成链保留为历史资料；编号更高的实验资源不代表已被当前游戏采用。被排除的参考网站截图、缓存及批量中间验收媒体仍留在原工作站，部分历史 HTML 对比页因此不能仅靠克隆仓库完整显示。

## 已有验证与限制

以下结论来自保存的历史构建记录，本次 Git 归档没有重新运行游戏测试：

- Windows v3 r2 构建 `build_9d1476f74d8d` 的 [七章自动流程报告](art/verification/game-v3-native-r2-full/qa-report.json) 为 `passed-automated-flow`，完成七章、恢复存档，`errors=[]`，留下 47 张截图（含 11 段开篇）。流程通过输入操作解谜，但使用诊断传送接近交互点，不能替代全岛步行与碰撞验收。
- 同次 Windows 报告在 i5-13500H / Iris Xe、1600×900 输出下，各章平均约 **28.95–37.85 FPS**，自适应渲染比例约 0.72；这些是静态、过场和诊断移动混合采样，尚未达到稳定 60 FPS，不能作为完整游戏的最低帧率。
- WebGL v3 r2 构建 `build_b9ecc0629b1b` 的 [浏览器流程记录](art/verification/game-v3-web-r2-flow/web-v3-report.json) 覆盖标题、地图、开篇及跳过后进入序章，未覆盖网页端七章完整流程；启动阶段的短时帧率读数不能证明持续性能。
- 美术与参考作品的整体差距、部分海岸旧崖壁、道具与动画的完整检查、音频听感仍有待验收。参赛文件已整理不等于这些质量目标全部达成。

其余制作与验证说明见 [v3 r2 记录](art/verification/game-v3-final/README.md)；该页的早期交付文件列表已被上述最新参赛清单替代。历史 v2 和 Borrowed Light 报告仅说明各自当时的构建，不作为当前版本的通过证据。

## 历史、来源与使用

本轮按模块拆分提交，保存当前文件、制作过程和既有验证记录，便于后续追踪。**这些归档提交不等于恢复原始开发时间线**，不倒填日期，也不把留存文件伪称为当时已经提交的 Git 历史。范围说明见 [Git 归档说明](setup/GIT-归档说明.zh-CN.txt)。

文学故事与创作核心由作者原创；AI 辅助范围、制作流程及第三方素材说明见参赛 ZIP 中的相关文档、单独的 [AI 工具使用说明](参赛提交/9_作品汇报PPT/借光岛_人工智能工具使用情况说明.docx)，以及各资产目录保留的来源记录。根目录旧版 AI 与参赛说明保留为历史资料。字体许可证随相关源文件与 Unity 资源保存。

本仓库没有为项目自有代码与美术指定开源许可证；公开可见不等于授予自由再分发许可。第三方素材分别遵循所附授权。
