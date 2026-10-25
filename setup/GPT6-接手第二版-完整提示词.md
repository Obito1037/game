# 《借光岛》第二版：GPT-6 全面接手提示词

> 用法：把下面整段发给 GPT-6（Codex）。从这一刻起，环境、玩法、UI、剧情、主场景都由 GPT-6 一人负责，Claude 不再同时操作 Unity Editor。

---

## 0. 你的身份和目标

你接手 Unity 游戏《借光岛》（标题只有这三个字；“把星空还给夜晚”这个副标题/主题已被用户删除，任何地方都不要出现）。
目标：做出一个**完整可玩、画面质感对标 https://littleprince.dev（同样是 Unity WebGL）**的第二版。
剧本唯一依据：`art/design/script/07_完整故事与生图提示词（最终版）.md`（**不是** `01_完整文学剧本.docx`，那是另一个故事）。
始终用中文回复用户。

“完美”的验收标准（第 7 节）是硬性的。没有截图证据的事情，不要说“已完成”。

## 1. 先读这些（按顺序）

1. `AGENTS.md`：工具路径、Unity 版本、协作规则
2. `art/design/script/07_完整故事与生图提示词（最终版）.md`：剧情、人物、章节
3. `art/design/v2/借光岛_第二版_生图与Tripo提示词.md`：全部模型、贴图、天空和 UI 的需求编号（A01–D10、T01–T06、V01–V04、S01–S03、U01–U13、P01–P05）
4. `setup/GPT6-对标小王子-质感优化提示词.md`：对标分析
5. 现有截图：
   - `art/verification/game-v2-ui/`：标题、地图、章节卡、HUD 和灯面板，已达标，作为 UI 基线
   - `art/verification/game-v2-terrain/`：新地形的现状，**未达标**
   - `art/verification/game-v2-c01-c05/`

## 2. 当前工程状态（Claude 交接时）

**工程与流程**
- Unity `6000.3.26f1`，URP 17（Forward+、HDR、Linear）。只用 Input System；所有输入都经过 `Scripts/Core/GameInput.cs`。
- 新游戏代码在 `GameProject/Assets/JieGuang/`，主场景是 `Scenes/JieGuang_Main.unity`。主场景由菜单 `JieGuang/Build Main Scene`（`Editor/JieGuangSceneBuilder.cs`）生成。
- 流程（`Scripts/Story/GameDirector.cs`）：标题页 → 旅程地图（节点逐章解锁）→ 章节卡（进度条加载）→ 章节正文 → 解锁下一章并回到地图。按 Esc 打开暂停菜单。
- 存档键：`jieguang.unlocked`、`jieguang.chapter`。测试跳章：`PlayerPrefs.SetInt("jieguang.debugStart", 章号)`。
- 章节信息在 `Scripts/Core/StoryText.cs` 的 `Chapters[]`（序章 … 尾声）。

**UI**
- `Scripts/UI/UiKit.cs` 用代码生成 UI：星点、光晕、羊皮纸、金线、键帽等程序化 sprite。
- `Scripts/UI/GameUI.cs`：HUD、目标、世界坐标提示（E 键帽）、标记、对话、旁白、信件、灯面板、标题、地图、章节卡、暂停、淡入淡出。

**角色**
- 5 个 Tripo 角色已绑骨，Humanoid，Mixamo 骨架，25 个原地动画（`Characters/`、`Animations/`）。
- 绑骨脚本：`art/blender/rig_characters_v1.py`。

**道具**
- 38 个 Tripo 道具已处理：减面、真实尺寸（米）、底部中心为轴心、贴图 ≤2048。
- 脚本：`art/blender/process_props_v2.py`。产物在 `art/generated/props-v2/<id>/`（含 `record.json` 和 `preview.png`），Unity 资源在 `Assets/JieGuang/Props/<id>/`。
- 源 GLB 已复制到 `art/incoming/tripo-v2-2026-10-22/`，编号与 uuid 的对应写在脚本的 `ASSETS` 表里。
- 导入规则（`IslandV2Builder.cs` 里的 `JieGuangPropImport`）：`bakeAxisConversion=false`。prefab 根节点自带 -90° X 旋转，**摆放时必须写成 `Quaternion.Euler(0,yaw,0) * prefab.transform.localRotation`**，否则模型会躺倒。

**岛**
- 当前主场景用的是 `World/IslandV2.prefab`，由菜单 `JieGuang/Build Island V2 (Tripo props)`（`Editor/IslandV2Builder.cs`）生成。
- 生成方式：复制你 v1 的 `Environment/Island.prefab`，隐藏旧渲染器，按旧物体包围盒套入 Tripo 模型。锚点、碰撞体和灯光都保留。构建日志在 `World/IslandV2-build-report.txt`。
- 地形：`Editor/IslandTerrainBuilder.cs` 生成 Unity Terrain。
  - 高度从 IslandGround 碰撞体射线采样，四层 splat（草、土、石、崖）。
  - 5 种细节草花（DetailRenderMode.Grass），共约 9 万株。
  - 地表贴图 `World/Terrain/T01_grass.png`、`T02_stone.png`、`T03_dirt.png`、`T04_cliff.png` **只在缺失时程序生成**；同名替换成高质量贴图后重新构建即可。
- 天空：`Shaders/NightSkybox.shader`（渐变、地球光晕、银河、程序星星、地球月牙贴图），由 `Scripts/World/NightSky.cs` 驱动，雾为 ExponentialSquared，密度 0.0062。
- 海：`Shaders/NightSea.shader`（涌浪、波纹、菲涅耳、主光和附加光高光）。

**QA 工具**：`tools/jg-qa.sh`（bash 里 `source` 后使用）

| 命令 | 作用 |
|---|---|
| `play` / `stop` | 进入 / 退出 Play 模式 |
| `recomp` | 重新编译并等待完成 |
| `ev '<C#>'` | 在 Editor 里执行一段 C# |
| `press E Space` | 注入按键 |
| `state` | 查看当前章节、对白和目标 |
| `tpnear 物体名 dx dz` | 把玩家传送到物体旁 |
| `shot "x,y,z" "x,y,z"` | 摆相机 |
| `capc 名字` | 带 UI 截图 |
| `capu 名字` | 关掉后期再截图，用于 UI 校色 |
| `errs` | 看控制台错误 |

截图输出到 `$OUTDIR`，**每批先 `source` 再设置 `OUTDIR`**。

## 3. 为什么页面上的房子“没换”（第一件要修的事）

- 村子里 11 栋小屋已经换成 C03、C04、C05 三种 Tripo 小屋，但它们离镜头远、比例偏小，所以不显眼。
- **最显眼的阿婆的家（`GrandmotherHouse`）故意没换，还是你 v1 的方块房。** 原因是剧情锚点 `Marker_Window`、`NPC_ABo_Window`、`Marker_Seat`、`Marker_ABo_Seat`、`Marker_Desk`、`Target_Window` 都按旧房子的窗洞定位。直接套 A01 会让阿婆坐在墙里、窗光错位。
- 另外，A01 阿婆的家、A02 书桌、A13 栈桥尽头、B02 光果、B03 萤火信、B04 拐杖**已经导入，但没有摆进场景**。

你要做的：
1. 把 A01 放到 GrandmotherHouse 的位置，朝向主路。用 Blender 或 Unity 找出 A01 的窗户中心，再把上面 6 个锚点**整体平移到新窗口**（如有需要，也调整剧情镜头 `Cam_*` 和 `Target_*`）。窗内放暖色点光和发光窗片。旧方块房的渲染器关掉，碰撞体按新模型重建（BoxCollider 组合即可）。
2. A02 放在窗内的 `Marker_Desk`。A13 接在 PierDeck_03 末端。B02、B03、B04 放到剧本对应的道具位置，或由 `GameDirector` 在对应章节里生成。
3. 村屋按 Height 而不是 Footprint 适配，高度为 3.2–4.5 m，避免像现在的 C05 一样被压到只有 1.9 m。
4. 灯头 A06 现在偏大（缩放 1.2–1.5），改为 0.8–0.9 倍。灯罩 A07 宽、窄两种的朝向要截图核对。

## 4. 未完成的地形、天空、海和光照（用户最在意的部分）

用户原话：“整个岛的陆地、道路、岛的外貌、月光、天气的质感和小王子比也差远了。”现状和要求如下。

1. **细节草花不可见**：数据存在（约 90265 株，`drawTreesAndFoliage=true`，材质 URP Terrain/Lit），但截图里山坡是光秃的绿色。排查顺序：
   - (a) 细节原型的 min/max 宽高是否太小。
   - (b) `detailObjectDensity` 和 `detailObjectDistance`。
   - (c) URP 的 Grass 模式 detail shader 是否被裁掉；可在 Graphics 设置里加入 `Hidden/TerrainEngine/Details/UniversalPipeline/*`，或改用 `DetailRenderMode.VertexLit` 加带 alpha 贴图的网格草或草卡片。
   - (d) 截图走 `--source camera` 时是否渲染了细节。

   验收：在玩家视角 3 m 内能看清一根根草叶和小花，远处成片起伏。用户正在用 GPT 生成 V01–V04 草和花的卡片贴图，放进 `~/Downloads`。
2. **地表贴图**：T01–T06 地表贴图和 S01–S03 天空图也由用户生成并放进 `~/Downloads`。
   - 收到后复制到 `Assets/JieGuang/World/Terrain/`（按 T01_grass、T02_stone、T03_dirt、T04_cliff 命名），设为 Repeat，平铺 2–4 m；有法线贴图就一起用。
   - 小路（StonePaths）要读得出是石板路：可以用 splat 加贴花，或者沿路径摆石板网格。
3. **海**：现在是灰色大理石条纹，太丑。改为：
   - `_Ripple` 降到约 0.1，菲涅耳系数降到约 0.5，深水色更暗更蓝。
   - 远处与天际线融合，近岸加泡沫带（可用深度差，或按地形高度生成 mask 网格）。
   - 地球光在海面拖出一条长长的反光带，灯笼和窗口在海面有暖色倒影。
   - 用 `ShaderUtil.GetShaderMessages` 查 NightSea 剩下的那条着色器警告。
4. **天空**：收到 S01 全景天空后，可做成 Cubemap/Panoramic 天空，叠加现有程序星星；也可以只用它替换渐变和银河。地球月牙（S02）用作 `_EarthTex`。
5. **光照与后期**：
   - 主光为冷蓝的地球光，带柔和阴影；环境光三色为天青、地平线紫灰、地面深绿。
   - 暖色灯光点缀在灯、窗和灯笼上。
   - 后期：Bloom 阈值约 0.9、强度 0.6–0.8；ACES 色调映射；轻微暗角；Color Adjustments 让暗部偏蓝、高光偏暖。
   - 雾按章节的光污染强度变化。
   - 对比小王子截图：画面要“柔、亮、干净”，**不能漆黑**。夜景的可读性靠天光和轮廓光，不靠压暗。
6. **岛的外貌**：从海面和远景看，岛要有清晰的轮廓层次：悬崖岩石、植被、村落、山顶金色光树。岸边要有礁石、浪花，栈桥伸入海中。

## 5. 玩法、剧情和 UI 的收尾

- 从序章到尾声逐章通关，用 `debugStart` 跳章测试。每章要有：明确目标、标记、交互提示，以及剧本里的关键对白和演出。没有软锁，没有卡住的镜头。
- 章节切换、标题和地图沿用现有的小王子风格 UI，只修问题，不推倒。
- 角色：动作过渡平滑，不出现滑步、T-pose 或穿模；NPC 站位朝向正确。
- 音频：至少有海浪、风和夜虫环境音，配一首主题音乐和交互音效。现在只有 LanternChime 和 NightLetters 两个音频。
- 性能：Windows 原生 1600×900 下 ≥60 FPS；WebGL 在普通笔记本上 ≥30 FPS（如果超出预算，细节草的距离和密度要分档）。

## 6. 规则（必须遵守）

- 同一时间只有一个代理驱动 Unity Editor。开始前先运行 `tools/unity-cli/bin/unity.exe status --json`。
- `Assets/BorrowedLight/` 是旧游戏，只读，不要改，也不要删。
- 不要删除任何已有的验证截图、记录或旧版本资源。新证据放进 `art/verification/game-v2-*/`。
- 不要 git commit 或 push，除非用户明确要求。
- 不要在任何网站输入用户的账号密码。
- 能用编辑器脚本（Editor 菜单）重建的东西，不要手工拖进场景。保证 `Build Island V2` 加 `Build Main Scene` 能从头重建出同样的结果。
- 每次说“完成”时都要附上截图路径，并说明哪些项没验证。

## 7. 第二版验收清单（全部满足才算完成）

| # | 项目 | 证据 |
|---|---|---|
| 1 | 阿婆的家换成 A01，窗、桌、座位锚点对齐，剧情演出正常 | 第 1 章开场截图和窗边对话截图 |
| 2 | 所有 Tripo 道具已摆放，没有躺倒、悬空或穿地 | 环岛 8 张截图 |
| 3 | 草叶和野花在近景清晰可见，远景成片 | 近景、中景、远景各 1 张 |
| 4 | 新地表贴图、石板路和悬崖 | 同上 |
| 5 | 海面干净，有地球光反射带、暖色倒影和岸边泡沫 | 2 张 |
| 6 | 天空、雾和光照的质感接近小王子；画面不漆黑，Bloom 不过曝 | 与小王子同构图的对比图 |
| 7 | 从标题到尾声完整通关，无报错 | 每章 1 张截图，`errs` 为空 |
| 8 | 帧率达标 | 记录 FPS、分辨率和机器信息 |
| 9 | Windows 构建和 WebGL 构建都能启动 | 构建路径和启动截图 |

完成后写一份 `art/verification/game-v2-final/README.md`，列出每项的证据、仍存在的问题和下一步建议，再用中文向用户汇报。
