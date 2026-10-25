# V2 环境候选整合工具交接

状态：**已完成离线 C# 联合编译；尚未导入 Assets、执行 Builder、操作 Unity、截图或验证运行效果。** 本文件描述将要执行的动作，不是它们已经成功的证据。

工具：`Editor/EnvV2CandidateBuilder.cs`。仅有两个显式入口：`BuildCandidate()`、`CaptureCandidate()`，没有自动执行回调、Play 或打包入口。不调用 `EnvV1Builder.Build()`。

## 导入前准备

由当前持有 Unity 操作权的一方先按 AGENTS 检查 `unity status --json`、`unity pipeline list --json`。本离线工具不替代操作权协调。它只允许 Editor 空闲、非 Play/编译/导入状态运行。

将本 staging 的 Editor、Runtime、Shaders 源分别放入自己的 `Assets/JieGuang/Environment/` 对应目录。Surface / Meadow 应使用最新逐片元级联阴影修正版。必须存在以下已导入资源：

| 离线来源 | Unity 目标路径 |
|---|---|
| `art/generated/env-v2/props/abode_grandma/abode_grandma_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/abode_grandma_v2_candidate.fbx` |
| **`art/generated/env-v2/terrain/candidate-b/coastal_cliff_v2_candidate.fbx`** | `Assets/JieGuang/Environment/ModelsV2/coastal_terrain_v2_candidate.fbx` |
| `art/generated/env-v2/textures/meadow_albedo_v1.png` | `Assets/JieGuang/Environment/Textures/v2/meadow_albedo_v1.png` |
| `art/generated/env-v2/textures/wood_albedo_v1.png` | `Assets/JieGuang/Environment/Textures/v2/wood_albedo_v1.png` |
| `art/generated/env-v2/village/cottage_teal/cottage_teal_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_teal_v2_candidate.fbx` |
| `art/generated/env-v2/village/cottage_ochre/cottage_ochre_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_ochre_v2_candidate.fbx` |
| `art/generated/env-v2/village/cottage_slate/cottage_slate_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_slate_v2_candidate.fbx` |
| `art/generated/env-v2/pier-bench/pier_module/pier_module_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/pier_module/pier_module_v2_candidate.fbx` |
| `art/generated/env-v2/pier-bench/bench/bench_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/bench/bench_v2_candidate.fbx` |

注意地形来源是 **candidate-b**，导入名称有意不同。B 含 `IslandGround` 与 `CoastalCliff`；A 仅崖壁，不能替代。工具只设置这七个新 FBX 的 Read/Write、关闭导入动画和自动 Collider，不猜测或覆盖轴转换、单位缩放设置。三款村屋与栈桥/长椅已通过离线 FBX 往返和目视审阅，Unity 仍待验。第一朵花与灯具 d 仍为独立候选，不在此处自动接入剧情；`pier_end` 未在原岛使用，不额外加入。

依赖的现有基线为 `Environment/Island.prefab`、`Environment/EnvTest.unity`。不会重新从旧生成脚本搭岛；不会打开或保存 `Scenes/JieGuang_Main.unity` 文件；只读记录已加载场景的保护状态。

## BuildCandidate 的处理与失败条件

1. 在新的自有 additive 空场景实例化现有 Island，然后 unpack。记录原来的 active scene、已加载场景和 dirty 标志。最后只关闭自己新建的场景并恢复原 active；从不清除、保存或重新加载别人的场景。
2. 记录全部原始 Anchor / Target / NPC / Cam / Marker、LampHead、村窗与可走边界点变换。记录阿婆屋原 Collider 的完整序列化内容。保留原锚点对象，不重新计算故事坐标。
3. 阿婆屋导入模型分别试“原导入变换”和“导入根 X 反射”，以 **4 个实际 Marker 最大世界位置误差**择优。最大误差超过 2.5cm 就失败。原模型的 Renderer 被移除，原 MeshFilter、Collider、Marker 和层级保留；新视觉网格合并到 `Props/GrandmotherHouse/Visual_V2`。
4. 26 个源材质名先查 `EnvV2HouseSurfaceBuilder.Prepare` 返回表，木材映射到 generation/HouseWood 内四张独立纹理材质，再用原明确表映射瓦、石和金属等旧共享材质。阁楼暗色玻璃新增一张不发光材质。以最终共享材质合并 submesh，丢弃空槽与未引用顶点；超过 16 张非空材质或 12,100 三角面会失败。源 FBX 为 11,925 面，此处阈值留少量导入容差，不表示已经测得 Unity 面数。
5. 地形同样比较原导入/X 反射两种实际世界点云。B 只改 186/3025 个海岸顶点，必须有 **>90% 候选唯一顶点**与旧地面重合（2mm），否则失败。择优后把两个网格烘焙到原对象局部坐标；法线用逆转置，负行列式翻三角绕序。保留原对象和 MeshCollider 组件，替换 sharedMesh；`IslandGround` 仍层 8、`CoastalCliff` 仍层 9。
6. **StonePaths 的原贴地 mesh 和变换必须完全保留**，只允许 Surface helper 更新材质。不会运行旧 Conformer。
7. `Target_Window/RoundWindow` 是半径 0.48–0.51m、位于目标内侧 2.5cm 的窄环，中心没有面。材质为低亮暖反射面、无 Collider。Claude 可按现有逻辑从 Target_Window 子级查到 Renderer；本工具不引用 Claude 类型，也不挂 WindowGlow 或任何剧情脚本。需实际确认环与旧窗框没有 z-fighting。
8. 顺序调用 `EnvV2SurfaceBuilder.Build`、`EnvV2MeadowBuilder.Build`、`EnvV2LookBuilder.CreateLibrary/Attach`、`EnvV2ShoreMapBuilder.Bake`。海岸图来自实际替换后的地形和实际海面 Y，绑定 `_ShoreMap`、`_ShoreRect`、`_ShoreEnabled=1`。有开放轮廓时保留并报告警告，不能称海岸画面已验证。
9. Sky/Sea 的 night-1 初始颜色、月相和星点参数实际写进**候选自有材质**，不只放不会持久化的 PropertyBlock。自有测试场景明确应用 night-1 ambient/fog、清空 skybox、开启 HDR 与 URP 后期；主场景不受此调用。
10. 检查恰好 **3 个 Spot、22 个独立村窗**、原始锚点/原屋 Collider 不变、地面采样高度差 ≤2.5cm、7 条灯目标射线遮挡者列表不变（包含归航灯→桥、远海）。地面采样来自锚点、原石路顶点和闭合可走边界内 2m 网格；只射自己岛的层 8 Collider，避免其他已加载场景污染射线。
11. 地形替换后、草地生成前调用 `EnvV2VillageBuilder.Build`。它测量三款源屋的完整门标记矩阵和双向窗口点集，保留11栋原 disabled Structure、22扇独立窗、11个 BoxCollider、所有 Marker 与旧合批空物体；只移除候选岛14组旧合批的 Renderer/MeshFilter，合并新 Structure。每栋新增≤700面，全村实际新旧合批差额≤7700面；不能把仍保留的原 Structure 从计数中扣掉。详细契约见 `../village/VILLAGE-INTEGRATION.zh-CN.md`。
12. 全岛 renderer 实例面数连同全部 LOD、未激活 Renderer、天空/海面合计须 ≤600,000。同时新增更保守的所有 MeshFilter 实例计数（包括无 Renderer 的旧屋网格），也须≤600,000；报告分别列出两种计数、无 Renderer 的保留量和 enabled renderer 总量。它们均不是 Draw Call、LOD0 每帧实际面数或帧率。

村屋之后、Surface/Meadow 之前显式调用 `EnvV2PierBenchBuilder.Build`，由完整 Marker 矩阵推导 FBX 到原 Structure 局部的变换；双向顶点与逐材质有向三角面必须匹配，世界位置容差20微米、角点法线差≤0.25°。只换3段桥与1张椅子的视觉 MeshFilter/材质引用，四实例总面数保持1692、新增0；全部TRS、原3个桥面BoxCollider、长椅MeshCollider与其旧sharedMesh保留。独立4个 CoastalWood 材质包含 `Wood_Weathered` 映射，原铁材质不变，不套用屋材颜色。失败就中止，不临时放宽公差。完整报告路径写入 `pierBenchReport`，细节见 `../pier-bench/INTEGRATION.zh-CN.md`。

检查失败抛异常，不写成功状态。失败途中生成的自有 generation 资产保留用于排查，不删除别人的内容。已存在的候选 Prefab/测试场景会先复制到本次 generation 中备份。两项输出逐项保存，不承诺磁盘级原子事务；如果在第二项保存时失败，报告会明确失败，可使用保留的上一版备份。

## 输出

- `Assets/JieGuang/Environment/Candidates/IslandV2.prefab`：候选 prefab；原 `Island.prefab` 不覆盖。草/海/天空默认动态时间 `-1`。
- `Assets/JieGuang/Environment/EnvV2Test.unity`：自己的测试场景；独立复制所需时间材质，固定第 12 秒，不让冻结状态写回候选 Prefab。
- `Assets/JieGuang/Environment/Generated/V2Candidates/Generation_<UTC>/`：新网格、少量新材质、测试材质和上一版候选输出备份。
- Village / PierBench / Surface / Meadow / Look / Shore 各自 helper 的自有 Generated 输出和报告路径写入总报告。
- `art/generated/env-v2/candidate-integration-report.json`：执行后生成，含 before/after 锚点、屋 Collider、全部地面射线、灯遮挡列表、材质映射、朝向候选误差和全部检查结果。此文件当前尚未执行生成。

如果 EnvV2Test 已打开，Build 会拒绝，保留用户当前打开的研究场景。Capture 要求 EnvTest 与 EnvV2Test 均关闭；不会悄悄关闭已打开且可能有未保存改动的场景。

## CaptureCandidate 的比较规则

在 `art/verification/env-v2/capture-<UTC>/` 输出以下三组，每组 5 张 **1440×900** PNG 和统一 `captures.json`：

| 组 | 设置和时间 |
|---|---|
| `baseline-original/` | 读取保存的 EnvTest，保留其 HDR/后期/灯光/环境设置，V1 shader `_Time.y` 照常流动。原样基线，**不标成冻结**。 |
| `baseline-frozen/` | 同一个 EnvTest、同一设置和机位，仅在自有诊断目录生成 V1 shader 副本，把 `_Time.y` 替换成常数 12；临时材质只赋给本次打开的基线实例，关闭且不保存。 |
| `candidate/` | 读取已保存的 EnvV2Test，HDR/后期明确开启，night-1，Sky/Sea `_EnvTime=12`、Meadow `_WindTime=12`。 |

所有原 V1 Shader/Material 均不修改。冻结基线必须实际找到并替换时间表达式，诊断 Shader 若报错就停止，不生成虚假的“已冻结”证据。`baseline-frozen` 只解决动画时刻一致性，**HDR、后期和整体 Look 仍与候选不同**；报告逐图记录 HDR、后期、环境色、fog、反射强度、相机 clip、FOV 和时间策略。若要单独归因某个材质/模型改动，仍需后续增加同 Look 的隔离实验，不能直接归因所有提升。

| 名称 | 相机位置 | 看向点 | 垂直 FOV |
|---|---|---|---|
| Cam_Title | (57,44,-73) | (-5,5,1) | 45° |
| Cam_Puzzle | (27,18,-45) | (7,5,-18) | 43° |
| Cam_Pier | (22,8,-11) | (10,4,-15) | 48° |
| Cam_Village | (12,21,-8) | (-14,10,12) | 48° |
| GameplayStudy | (12,4.15,-24.2) | (5.2,3.9,-16.7) | 50° |

前四个来自原 scene-input，逐值相同。第五个为新增共享近地研究位，**不是角色控制器真实游玩截图，也不是与《小王子》相同场景的对齐机位**。离屏输出请求使用 URP StandardRequest、ARGB32 sRGB、1×目标采样；HDR 中间过程遵循保存的 Camera。实际 PNG 尺寸、后期是否生效、阴影和色彩均要人工看图检查。

截图给自己的临时研究场景分配 `CalculateAvailableSceneCullingMask()` 取得的独立 bit，并设置 `camera.overrideSceneCullingMask`。后期启用时，自有 Volume 临时移到未被任何其他 Volume 占用的数字层，camera volume mask 仅选择此层；只关闭/重新开启自己的 Volume 以同步 registry，关闭临时场景且不保存。不改 ProjectSettings 层定义，也不禁用或移动 Claude 的物体。报告逐图记录原/有效 Volume mask、独立 scene mask 和自己的 Volume 数量。代码隔离仍须实际截图检查，不能代替 Unity 验证；没有 FPS、WebGL 或人物游玩验证声明。

## 本次离线验证与下一步

已用本机 Unity **6000.3.26f1** 的 `NetCoreRuntime/dotnet.exe` + `DotNetSdkRoslyn/csc.dll`，参数 `-target:library -define:UNITY_EDITOR -langversion:9 -nostdlib+`，联合编译所有 staging Editor / Runtime C#。引用 UnityEditor、UnityEngine 模块、netstandard 2.1、项目 URP/Core Runtime 程序集。成功输出为系统临时目录 `EnvV2CandidateCompile.dll`；不进入 Assets。C# 通过不证明 Shader 编译、物理采样或画面通过。

栈桥/长椅接入后的最新联合编译为 **8 个 Editor + 2 个 Runtime**、201 个本地引用，退出码0、无诊断。实际临时 DLL 路径、时间与全部源 SHA 见 `verification/candidate-coastal-csharp.json`；前述文件名属于较早编译。整合器经独立源码审查，没有已确认阻塞；这些证据仍不替代 Unity 实际执行。

后续执行顺序：确认 Unity 操作权和连接 → 导入自有资源并查编译错误 → BuildCandidate → 查总报告全部检查及警告 → CaptureCandidate → 逐张审图 → 再交 Claude 测试窗口发光、三灯、章节、角色碰撞和主相机后期。夜空唯一入口、第三盏灯扇区、港灯发光等 Claude 侧问题仍按 `art/design/v2/benchmark/REQUESTS-FOR-CLAUDE.zh-CN.md` 处理；本工具不会越界修改。

## 二次源码审查记录

- 追加要求的 `Anchor_VillageGate`、`Anchor_GoldenTree`、`Anchor_Boat`、`Target_Sea`、`NPC_ABo_Door` 已加入必需唯一列表；旧版本只是快照保存已有对象，缺失时不会主动失败，现在会。
- 全部 unpack 后断言脱离 prefab instance；保存后断言候选是 Regular Prefab，防止错误形成依赖旧岛的 Variant。
- SceneGuard 在模型 importer 操作前建立，记录 loaded/dirty、native culling mask，以及原 active 场景的 ambient、fog、reflection、skybox、sun。恢复 active 场景后逐项比较；异常不会偷偷清 dirty 或保存别人场景，报告也不能仍写 captured-success。处于 Prefab Mode 时拒绝操作，不自动关掉用户编辑状态。
- [Unity 的 SetActiveScene 文档](https://docs.unity.cn/6000.3/Documentation/ScriptReference/SceneManagement.SceneManager.SetActiveScene.html)说明 active 场景负责 lighting settings；因此工具恢复其所有者并验证值，不把拷贝的全局值再写进别人的场景。实际方法同时通过本机 6000.3 C# 编译验证。
- 本地 URP 17.3 `UniversalRenderPipeline.cs:550` 的 StandardRequest 调用正常 Render 流程；Editor 模式 `UpdateVolumeFramework` 每次更新。Core `VolumeManager.cs:789` 按 mask 收集，`:892` 另用 StageUtility 判断可见性。不能仅凭 camera.scene 推断同 main stage 的多场景完全隔离，因此新增独立 scene bit 与 Volume mask。
- Core `Volume.cs:163` 的 Layer 变更在下一 Update 才更新 registry；截图立刻发生，所以临时移层必须先 disable 再 enable 自有 Volume，而不是只改 layer。
- 地形作者只读确认 B 世界点云保留比例约93.85%、Ground/Cliff各一个原 MeshCollider、材质匹配和矩阵烘焙正确；Unity 接缝顶点数量可能改变，未写3025的硬断言。Combine只复制实际索引使用的顶点，负行列式翻绕序，真实 UV/normal 缺失时失败。
- 木材 PNG 与 helper 已存在并接入。阿婆屋方向 UV 和屋檐/阁楼四处补缝已完成 Blender 验证，最终 FBX SHA256 为 `2cb7d8c23bc5051bed94fd3318de6fe1d23d540a89650ad0578746d91e02a5a1`；Unity 夜景纹理及导入仍未验证。三款村屋的独立接口 helper 已接入本候选生成器，其最终源资产验收另外记录在 village 目录。
