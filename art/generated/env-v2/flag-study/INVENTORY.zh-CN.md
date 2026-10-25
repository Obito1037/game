# 旧蓝旗：只读结构、材质与轻风可行性审计

结论：**旧旗足够继续承担当前剧情中的识别符号，暂不需要重做旗杆或加面。轻风是可选的气氛改善，不是 07 / v2 提示词明文要求的旗帜动画。** 若继续研究，应仅针对独立 `FlagFabric` 做小幅、固定挂杆边的离线验证；当前没有建立候选、修改模型、操作 Unity 或编写 C#。

现有旗并未达到 v2 A15 的完整材质要求：没有织物/补针/刺绣贴图，只有底边的分段白色几何；两颗星为五角，A15 指定四角星。旗面已经有静态褶皱，单靠摇动不会补足这些差距。

## 依据与实际看过的图

- `07_完整故事与生图提示词（最终版）.md:43,211–233`：细木旗杆、磨白边的蓝旗、小光树、一大一小两颗星、半腰铁钩、灯伯与老伴缝旗的记忆，以及把灯笼挂上铁钩的关键剧情。233 / 245 / 425 行有风中的铃声、海风和铃铛晃动；没有指定旗面的幅度、频率或强风模拟。
- `借光岛_第二版_生图与Tripo提示词.md:35,133–140`：可动旗面尽量单独；A14 旗杆约 5.5 米、挂钩约 1.8 米；A15 旗面约 1.3 × .85 米，≤1,500 面，褪色深海蓝、白边、补针、小树和一大一小四角星。旧杆 4.97 米、旧钩 1.77 米是已有玩法合同，不能仅因参考数字更大而移动。
- 已实际看源 `art/generated/env-v1/props/flagpole_blue/preview.png`（640×640）：蓝旗、白底边、小树与两星可读；布料呈规整条折、星像附加片，材质简洁。
- 已实际看历史 `art/verification/env-v1/03-pier.png`（1440×900）：旗杆/港灯在码头尽头，旗面角度及背景使图案不易分辨。这张历史单帧不能证明当前候选夜景、反面图案或动态效果。

## 源资产的实测数据

直接用 Blender 4.5 后台打开现有 `flagpole_blue.blend`，没有保存。源 blend SHA256：`dfc8e6a755bf88acfb36ce0e81cd219aadc2a25fd36200d8dc8a98e982fcd033`。源 FBX 与正式 Environment 下 FBX 相同：`bf20fa6d547aa1d17424fdd4fde804471c8926d145b9a48b1a022480a89c8903`。

| 对象 | 源顶点 | 三角面 | 材质槽 | 当前动画 |
|---|---:|---:|---:|---|
| Structure：木杆、杆脚、顶饰、升旗绳、铁钩 | 220 | 416 | 4 | 无 |
| FlagFabric：布、底边、树、两星 | 287 | 479 | 4 | 无 |
| 合计，实际岛中 1 件 | 507 | 895 | 两个 Renderer | 无 |

这是真实 Blender authored 顶点数，未测 Unity 导入后的拆分顶点数。FlagFabric 无 shape key、骨架、Cloth、修改器或动画数据；只有普通 `UVMap`，没有风权重颜色或根位置 UV 通道。模型原点在杆底，整体最高 Z=4.9700003 米。

FlagFabric 包围盒：X=.078500～1.341500、Y=-.108149～.117739、Z=3.676584～4.630000 米。蓝布本体由原 12×5 网格加 .007 米厚度形成，实际 156 顶点 / 308 三角面；整体不是一张焊接的布：

| 连通部分 | 数量 | 合计三角面 |
|---|---:|---:|
| 厚蓝布 | 1 | 308 |
| 底边短条 | 12 | 144 |
| 树冠 + 树干 | 2 | 11 |
| 一大一小星形片 | 2 | 16 |

共 **17 个独立连通件**。白边是 12 根小棱条，星和树是开放单面多边形，没有真正刺绣或毛边。按源布解析公式在徽记顶点处估算，徽记与布中面的 Y 差为 **.01841～.03892 米**；此值未扣厚度或检查三角插值，只证明图案并非共享布顶点，不能当作接触或穿插测试结果。

## 实际 Island.prefab 接口

读取的是 `Assets/JieGuang/Environment/Island.prefab`，SHA256：`d17154fd0cf79cf55e65225dbb517626216c80be2a3741dcc3bc53eabff1ae45`。通过 YAML 逐层矩阵计算得到：

| 节点 | 世界位置 / 约束 |
|---|---|
| Island/Props/Flagpole | (10, 2.48, -10.2)，yaw 180°，scale 1 |
| Flagpole/LOD0 | 保留现有 -90° X 导入旋转与 (-1,1,1) 反射缩放 |
| Flagpole/LOD0/Marker_FlagpoleHook | (10, 4.25, -10.5) |
| Island/Anchor_FlagpoleHook | (10, 4.25, -10.5)，与 Marker 同位 |
| Island/Props/HarborLantern | (10, 3.46, -10.5)，独立兄弟对象 |
| Island/NPC_DengBo_Box | (10.65, 3.04, -10.8)，坐面合同 |
| Island/Target_Pier | (10, 2.48, -16) |
| Island/Cam_Pier | (22, 8, -11) |

`Flagpole/LOD0/FlagFabric` 为独立 MeshFilter + enabled MeshRenderer，Layer 9，`m_StaticEditorFlags=0`，没有 Animator、Cloth、MonoBehaviour 或 Collider。它不在静态合批中。网格引用 GUID `fdc0bf24328aadd49893cdd87b0d6075`，fileID `-753759321034671569`。源 FBX importer 当前 `isReadable=1`、`meshCompression=0`、`addColliders=0`。

碰撞是旗杆下同级 `SolidCollision` 的独立 BoxCollider：center=(0,1,0)，size=(.22,2,.22)，enabled、非 trigger。旗布没有自己的碰撞。只能改变旗布的视觉，不能移动或禁用 Flagpole 父级、Structure、SolidCollision、Hook 或港灯。

## 材质和共享风险

四槽顺序为：`Flag_FadedIndigo`、`Flag_WeatheredEdge`、`Flag_SilverTree`、`Gold_WornEdges`。正式材质均为 URP Lit，所有图片槽为空，Cull=Back。前三个 metallic=0、smoothness=.32；金星用 metallic=.66、smoothness=.64 的 `Gold_WornEdges`，更像铜金片而非绣线。

`Gold_WornEdges` 在真实 prefab 共被 9 个 Renderer 引用，包括其他 Structure、路灯柱和灯罩；`Flag_FadedIndigo` 也有 2 个 Renderer 引用。**不能直接修改这些共享材质来给旗帜加风或改金属感。** 如果未来只做 CPU 克隆网格变形，可以原样保留四个共享材质引用；如果更换旗布 shader / 材质，需旗布专用候选副本并单独审阅，不能自动连带其他物体。

旧布本体有厚度，但树/星只有一面，现有背面剔除会让图案在反面不可见。不能把“布有两面”写成“刺绣图案双面已完成”。本轮没有改变 Cull。

## 轻风实现能否复用

在正式 Environment 中只找到海面和夜空 shader，没有现有旗风 helper。v2 staging 有 `Shaders/Meadow.shader` 和 `Editor/EnvV2MeadowBuilder.cs`：它们具备低频混合风、`_WindTime` 固定捕捉时间、颜色/阴影/深度/法线各 pass 共用变形函数、扩大网格 bounds。`EnvV2CandidateBuilder` 已识别 `_WindTime` 以固定截图时间。

**不能把 Meadow.shader 直接套给旗布。** Meadow 的 UV0 存高度权重、物种、随机种子，UV1 存根位置与株高，还使用顶点色；它按草根到草尖的竖直剪切处理法线，并有花朵/花粉与距离裁剪逻辑。旗布是固定竖向挂杆边的横向展开物，当前 UV 不具备这些语义。可参考风时钟、固定时间和各 pass 一致性的做法，不能复用整套草地材质。

另一条更小的研究路径是仅在将来的独立测试中克隆 `FlagFabric` 网格，对这一个可读小网格做低频形变，保留原四材质和所有其他对象。这不需要 Cloth 物理解算，也不需要增加面；仍须缓存顶点、正确更新法线/bounds、释放克隆网格，并实际测开销，不能因顶点少就声称已验证性能。

## 剧情依赖

- `IslandLayout.Build()` 按 Transform 名收集锚点，缺失时退回灰盒。`Anchor_FlagpoleHook` 名字及完整世界矩阵必须保留。
- `GameDirector.cs:87` 按 `HarborLantern` 查找已有港灯；461 / 472 / 489 / 505 / 553 行等用 Hook 处理熄灯、抵达、挂灯与镜头。906 行以 `Anchor_FlagpoleHook - Target_Pier` 推导码头朝向，移动 Hook 还会改变剧情站位/相机。
- `Lantern.cs:86–94` 用 Hook.position 跟随，摆动来自跟随点速度，不是恒定海风；固定 Hook 时会衰减。不能通过摇旗杆/铁钩来“顺便”制造灯笼风动。
- `EnvV1Builder.cs:607` 检查模型 Marker 与 Anchor 一致。没有发现剧情脚本按 `FlagFabric` 查找或控制旗面，因此限定在旗布内部的视觉研究可与现有剧情解耦，但未做运行验证。

## 最小合理下一步与预算

当前可以继续使用静态旧旗。若 root 决定探索轻风，先做**不新增拓扑的独立离线 A/B 动态研究**，不要直接接主岛：FlagFabric 保持 479 三角面，Structure 保持 416，整件 895；**新增预算 0 三角面**。A15 的 1,500 面是参考上限，不是需要填满的额度。

可从自由端 .015～.025 米、.12～.20 Hz 的缓慢摆幅开始，但这些只是尚未验证的起点。固定布边须依据实际左边列：蓝布前层 X=.08，背层约 .0837；网格全体最小 X=.0785 属于白边端部。不能只按“全网格最小 X”锁点，否则大多数挂边顶点仍会动。可测量约 1 厘米挂边带，前后壳及相邻白边同步固定。

必须先验证 17 个连通件的同步附着。对每个独立顶点直接套同一个连续波函数，不保证不同三角化的树/星在面内部与布同曲率；白边也可能浮离。若低幅零加面方案仍穿插，应停止并另评图案贴合/烘焙方案，不能用大摆幅遮盖问题或立刻细分全旗。

检查至少一完整周期的正、背、斜侧夜景，固定边逐值不动，树/星/白边无新穿插，影子/深度/法线跟随，bounds 不裁切；同时复核所有 Hook、Marker、NPC、港灯、杆和碰撞矩阵不变。静态截图只能看某一相位，不能证明动画自然。

完整机器可读数据、材质引用、11 个 prefab 节点矩阵、17 个连通件和源 SHA 在同目录 `inventory.json`。本轮仅新增该两份旗审计报告，以及父任务指定的 `pier-bench/root-review.json` 五图审阅记录；没有创建旗候选或更改任何源模型/Assets/C#/全局交接文档。
