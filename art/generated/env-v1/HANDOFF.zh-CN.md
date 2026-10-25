# 环境 v1 交接：Unity Prefab 与四机位截图已交付

日期：2026-10-22。唯一设计依据：`art/design/script/07_完整故事与生图提示词（最终版）.md`；已落实 `setup/GPT6-追加要求.md`。

## 当前协作状态

用户交接 Unity 后，GPT 已完成环境导入、Build、Validate、地面采样与 Capture，现已结束 Unity 操作，Claude 可以接回。最后检查：活动场景为 `JieGuang_Main.unity`，未标脏，未运行，未编译，控制台无当前错误。没有进入 Play 模式，没有构建游戏。

51 个事前记录的受保护文件哈希全部未变，包括 AGENTS.md、Packages 清单、ProjectSettings、Claude 的 C# 和主场景，见 `art/verification/env-v1/protected-files-after.json`。Git 中已有的 AGENTS.md / EditorBuildSettings 改动未被撤销，也不是本轮环境操作产生。未修改 Claude 负责的实现文件或旧 BorrowedLight。

给 Claude 的接入汇报已写到共享文件 `TO_CLAUDE.zh-CN.txt`；这不表示已通过消息通道发送或被阅读。

## 交付与验证

| 交付 | 位置或结果 |
|---|---|
| 可直接拖入空场景的整岛 | `GameProject/Assets/JieGuang/Environment/Island.prefab` |
| 独立环境测试场景 | `GameProject/Assets/JieGuang/Environment/EnvTest.unity` |
| 图片及资产索引 | `art/generated/env-v1/REVIEW.html` |
| 实际 Unity 截图 | `art/verification/env-v1/01-title.png`、`02-cape.png`、`03-pier.png`、`04-village.png`，均为 1440×900 |
| 结构检查 | `art/verification/env-v1/validation.json`，236/236 通过 |
| 地面采样 | `art/verification/env-v1/ground-checks.json`，13/13 通过；新增三个脚底/树根锚点贴地误差 ≤0.03m |
| 最终目视记录 | `art/verification/env-v1/visual-review.json`，含截图和 Prefab/场景 SHA256 |
| 离线资产完整性 | `package-validation.json`，213/213 通过；`missingAssets=[]` |

Unity 最高 LOD 合计 **380,368 三角面**，连同备用 LOD 合计 **506,767 三角面**，两者均含天空与海面共 770 面。35 个 LODGroup、168 个 MeshRenderer、51 个材质、22 扇村窗、3 个谜题 Spot；这些数量不是 draw call 或每帧绘制面数。环境低于 60 万面的几何预算，**尚未验证 Iris Xe / 1440×900 / 60 FPS**。

四图已逐张目视：没有明显缺材质的粉色网格；标题显示整岛与细弧地球；窗与港灯发光可见。整体仍偏暗，木屋/道具有占位感，树叶轮廓较硬；码头近景的小船下缘被裁切。静态截图不代表最终美术验收或主剧情运行效果。

## 本轮完成内容

1. 九个原始 GLB 保留于 `art/incoming/env-2026-10-22/`，独立子文件夹，未改 Downloads 原件。原始共 17,155,606 三角面、约 526.5 MiB；`inventory.json` 和 27 张正/侧/俯源预览记录原始情况。
2. 从混有多视角展示板的源模型拆出 13 个可复用自然资产，清除展示板、重复视图和漂浮碎片，减面、LOD、缩图及重烘焙；树干/叶/发光果材质分开。来源哈希、面数与处理步骤见 `asset-manifest.json`、`manifest.json`。
3. 16 类程序化占位道具完成，独立总计 13,237 面。村屋 11 户，岬角 2.4m、村台 8.4m，相差 6m；可走陆地主体长约 59.5m，港湾、栈桥、三灯、树、阿婆屋和环岛路已组装。
4. Unity 导入后修正 FBX 根的 local-X 反射，校验窗/门/座点 Marker；村屋按共享材质合并并修正反射后的绕序，保留独立窗与碰撞。不要再整体翻转 Island 或锚点。
5. 用真实地形碰撞将石板路派生网格的 1,350 个顶点贴地并抬高 0.045m，300 面细分为 1,200 面；结果在 `Environment/Generated/Meshes/StonePathsConformed.asset`，源 FBX 保留。
6. 长椅改精确网格碰撞，栈桥加连续 Layer 8 碰撞；五条灯到目标中心射线、材质色彩空间与发光关键词检查通过。URP 发光材质使用 BakedEmissive 保持关键词，这不表示已做光照烘焙。
7. 新增五个剧情锚点；港灯加入可由剧情控制的暖色 Point；Village_Windows 父节点调整到村子中心，保留各窗的世界位置。

## 接口与坐标

米制、Unity Y 向上，环境根位置/旋转为零、缩放为一。地面与栈桥碰撞 Layer 8，房屋/墙/岩石 Layer 9；不要求命名这些层，不改 TagManager。

| 新增锚点 | 世界位置 X/Y/Z（米） | 朝向/用途 |
|---|---|---|
| `Anchor_VillageGate` | (-12, 8.38550, 4) | 朝下坡，forward=(.371391,0,-.928477) |
| `Anchor_GoldenTree` | (1.8, 2.36404, -21.4) | 金树根地面，+Z |
| `Anchor_Boat` | (12.2, -.45, -12.3) | 与 ReturningBoat 系泊根完全一致，yaw=180° |
| `Target_Sea` | (10, -.16, 19.5) | 栈桥外约30m海面 |
| `NPC_ABo_Door` | (6.20143, 2.39917, -18.23588) | 门外贴地，朝屋外 yaw=154° |

原要求的锚点/层级均已验证唯一存在：

- 起点和灯：`Anchor_PlayerSpawn`、`Anchor_Lamp_WanFeng`、`Anchor_Lamp_YueChuang`、`Anchor_Lamp_GuiHang`。
- 目标与钩：`Target_Path`、`Target_Bench`、`Target_Window`、`Target_Pier`、`Anchor_FlagpoleHook`。
- NPC：`NPC_AYing`、`NPC_Postman`、`NPC_Bench`、`NPC_ABo_Window`、`NPC_DengBo_Box`。
- 镜头：`Cam_Title`、`Cam_Puzzle`、`Cam_Pier`（另有测试用 `Cam_Village`）。
- 村窗和范围：`Village_Windows`、`Sky_ScatterZone_Village`、`Sky_ScatterZone_Pier`、`Walkable_Boundary`。

三盏灯的锚点位于灯头转轴，`LampHead` 本地原点为转轴、+Z 为光束方向；子级 `Spot` 位于 (0,0,.29)，只转灯头，柱体保持竖直。现有灯直接复用。章节建议方向和角度见 `puzzle-light-layout.json`；五条中心射线通过不代替完整光锥、全部章节表现验证。

`Village_Windows` 父物体在 (-13,8.4,10)，22 个直属子窗可逐个亮灭。村屋主体在 `Village_Batches`，不要依赖原房屋 Renderer 控窗。两处 Sky_ScatterZone 使用 trigger BoxCollider。

三个座点均为坐面/骨盆参考点，不能直接当站姿脚底。`Walkable_Boundary` 为陆地闭合点列，`PierBoundary` 为码头闭合点列，可走范围取两者并集，不要串成自交线。石门槛约0.152m，离线道路局部坡度约36°，建议控制器 stepOffset≥0.20m、slopeLimit≥40°并由 Claude 实测通行。

`Props/ReturningBoat` 可供剧情移动；`Props/HarborLantern/HarborLight` 是暖色 Point，初始 intensity=1.2、range=3.5、无阴影，供剧情缓存初始值；它不计入三盏谜题 Spot。

## Claude 接入时必须协调

1. 在自己的主场景给 `GameDirector.IslandPrefab` 指定本次 Island.prefab。本轮没有修改主场景引用，故当前主场景仍需 Claude 接入环境。
2. 避免叠加两套夜空与地球：环境有 `Atmosphere/NightSky`，剧情也会生成星空/地球。建议保留剧情系统，只禁用环境 NightSky 的 Renderer；保留 Atmosphere 中海面和暖色环境灯。剧情冷蓝 Earthlight 需删除或协调成暖光，以符合所有灯光暖琥珀色要求。
3. 港灯亮灭必须同时控制 Point 与 `Lantern_AmberCore` 的 `_EmissionColor`。按材质槽使用 MaterialPropertyBlock 缓存并缩放初始发光，避免修改共享材质影响其他灯。目前仅设 Point=0 仍会发亮。
4. 海面 Shader **已提供并验证 `_Horizon` 属性**，剧情调整海面与天空颜色时一起同步它，以保留远海过渡。

以上只写入交接，未越界修改 Claude 的剧情代码。

## 重建与历史证据

当前 Unity 结果已经完成，无需为了接入再次生成。若今后主动重建，先按 AGENTS.md 检查 `unity status --json` / `unity pipeline list --json` 并确认协作占用，再执行已导入项目编译类型 `JieGuang.EnvironmentTools.EnvV1Builder.Build()` → `Validate()` → `EnvV1GroundChecks.Check()` → `Capture()`。使用项目内编译类型；临时 run_script 动态程序集曾遇到 JsonUtility DTO 反序列化限制。

组装器、辅助检查与 Shader 的源副本位于 `staging/`，对应导入副本在 Environment。没有导入自动执行生成或 Play 的逻辑。独立 LOD1 FBX 的命名警告为导入器历史警告；嵌套自动 LODGroup 已移除，最终使用35组显式 LODGroup。

`preview/island_offline.blend` SHA256：`0ce6e6c6ae971447581aae8723cf82bf4cd865c39bababe1cfd715f39f0b072e`。其四张1200×750图是此前 Blender 离线证据，未包含后续 Unity 贴路/材质等修正，不与新 Unity 截图混用。离线摆放最高378,698面、含备用505,097面；与当前 Unity 计数的差额来自天空海面及石路细分。

单个自然资产以 `asset-manifest.json` 的 `blend` 字段为准，旧 `*_processed.blend` 属中间件。为游戏删除的埋底面/树根接口仍有开口；tree_b 补枝交叠连接，未做水密布尔融合。

## 占位道具限制与 Tripo 补充建议


Downloads 中“剩余10项”文件夹经清点包含 10 张 PNG 和说明文本，属于概念参考图，不是另外 10 个模型。当前按已有 GLB 对应金色光树、三种树林、木船和岩石族；平坦岩台、陡峭岩柱等细分轮廓并非逐张参考图的独立精确重建。`missingAssets=[]` 仅指当前整岛摆放所引用的模型都已备齐。

现有占位道具可用于搭建和玩法联调，正式美术优先替换以下几项。每次生成只放一个物体的单一三分之四视角，纯色背景；不要把三视图、细节放大图、文字排版板送进单次重建，以免再次得到粘连展示板。

| 优先级 | 建议补充 | 可复制的参考提示词 |
|---|---|---|
| 1 | 阿婆木屋（目前无阁楼） | 温暖绘本风游戏3D木屋，米白木板墙、旧蓝绿瓦、人字屋顶，小阁楼朝海开小窗，正面右侧一个直径约1.1米的真正开孔圆窗，左侧敞开木门，黄铜铰链，朴素温柔的手工质感；单栋独立物体，单一三分之四视角，纯灰背景，无地台无人无文字，不要多视图拼图。需要单独制作可见室内书桌和摊开的厚本子。 |
| 1 | 铜路灯 | 温暖绘本风旧铜路灯，纤细约3.8米高灯柱，顶端明确可转动铰链，深罩挡住向上溢光，一颗暖琥珀色光果位于灯罩内，灯头与灯柱分离制作，单一物体单一视角纯灰背景，无电线无霓虹无人物。 |
| 2 | 铜浑天仪 | 绘本风小型旧黄铜浑天仪，同心铜环、有使用磨损，立在圆形低石台上，整件约1.6米高，安静朴素、结构清楚、低复杂度，单一三分之四视角、纯灰背景、无人物文字。 |
| 2 | 村屋三种 | 绘本风海岛朴素小木屋，约4米宽，木墙与石脚、旧瓦屋顶，两个独立暖琥珀光窗、木门，屋顶分别生成蓝绿色/赭红色/灰色三个单独资产，轮廓略有手工不规则，单栋单视角纯背景，无院落地台无人物。 |
| 3 | 港湾栈桥/长椅/旗杆 | 分别单独生成：旧木栈桥模块宽2.4米长3米、低矮系船桩且无高栏杆；1.8米宽旧木长椅、坐高0.45米；5米高纤细木旗杆、磨白边的旧蓝旗、1.8米处小铁钩。温暖绘本风，单物体单视角纯背景。 |

- 现有村屋不可进入，旗帜和晾衣布为静态；阿婆屋有真实开洞圆窗和门、桌椅及书本，但没有阁楼。
- 用户已有树、岩石和船源文件，先使用清理后的版本。树叶轮廓仍可见重建模型的硬边，近距离英雄特写应另作人工美术验收；需要重生成时按单资产单视角制作，避免重复得到展示板模型。


## 验证界限

环境几何预算、结构检查和静态截图已完成；FPS、draw calls、完整角色胶囊行走、坐姿、动画、主线所有章节与存档状态均未验收。地面检查只覆盖13个采样点。没有测试最终主剧情下所有灯与天空效果。当前为可接入联调的环境第一版，不宣称最终美术或整款游戏已经完成。
