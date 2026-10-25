# 村屋候选整合器交接

状态：独立整合器已编写并完成离线 C# 联合编译；未导入 Assets，未操作 Unity，未运行 Build，未验证实际 FBX 导入、画面、碰撞游玩或性能。三款素材正在由资产代理制作，本文的预期路径/材质接口不能当作素材成品证据。

## 入口与调用位置

代码：`art/generated/env-v2/staging/Editor/EnvV2VillageBuilder.cs`，命名空间 `JieGuang.EnvironmentTools`。

```csharp
EnvV2VillageBuilder.Report village = EnvV2VillageBuilder.Build(
    island,
    report.generation + "/Village",
    WoodTexture);
// 可将 village.generationPath / village.reportAssetPath 保存进总报告。
// 抛出异常时必须丢弃本次临时候选场景；不要保存不完整候选。
```

由 root 最后接入 `EnvV2CandidateBuilder`，本次没有修改整合器之外的实现文件。调用时必须是从 v1 岛复制、完全 Unpack 后的自有 `Island` 根物体，位于临时且尚未保存的场景；根无父级、坐标/旋转/缩放为原始单位变换；不能在 Play、导入、编译或 Prefab Mode 中调用。原基线 prefab、EnvTest 和主场景均不能作为此 API 的直接编辑对象。

整合器没有菜单、自动加载回调、Update，也不保存任何场景或 prefab，不修改 RenderSettings，不调用 `AssetDatabase.SaveAssets`。运行阶段的 Unity 所有权及 status/pipeline 检查由调用方负责。本交付没有执行这些运行阶段操作。

## 已对齐的模型输入

资产代理工作区输出预期：

| 类型 | 离线 FBX | root 导入后的路径 | 实例 |
|---|---|---|---:|
| 蓝绿屋顶 | `art/generated/env-v2/village/cottage_teal/cottage_teal_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_teal_v2_candidate.fbx` | 4 |
| 赭红屋顶 | `art/generated/env-v2/village/cottage_ochre/cottage_ochre_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_ochre_v2_candidate.fbx` | 4 |
| 灰屋顶 | `art/generated/env-v2/village/cottage_slate/cottage_slate_v2_candidate.fbx` | `Assets/JieGuang/Environment/ModelsV2/cottage_slate_v2_candidate.fbx` | 3 |

导入参数由 root 在自己的 ModelsV2 资产上准备：Read/Write 开启，Import Animation 关闭，Add Collider 关闭。整合器只读取 FBX/ModelImporter，绝不猜测或改写缩放、轴变换和 FBX importer。

每个来源必须包含且仅包含 3 个网格 `Structure`、`Window_00`、`Window_01`，以及唯一 `Marker_Door`。允许 Unity 的模型根名为资产原名或带 `_v2_candidate` 的文件名。两窗各保持 12 三角面、`Window_AmberEmission` 材质、原位置/矩阵/顶点集合。所有新增木纹、瓦沿、门框、窗框、石脚和烟囱细节必须合入 `Structure`；不要新增以 `Window_` 开头的装饰物，也不要新增 Marker。

`Structure` 必须保留 9 个原材质槽及顺序：

| 槽 | 材质 |
|---:|---|
| 0 | `Stone_SoftGrey` |
| 1 | `Wall_WarmIvory`；赭红款为 `Wall_LightTimber` |
| 2 | `Wood_DarkBeams` |
| 3 | `Wood_Endgrain` |
| 4 | `Wood_Honey` |
| 5 | `Copper_Aged` |
| 6 | `Stone_WarmLimestone` |
| 7 | `Roof_AgedTeal` / `Roof_OchreRed` / `Roof_WarmSlate` |
| 8 | `Roof_TealHighlight` / `Roof_RedHighlight` / `Roof_SlateHighlight` |

三款原模型各 1024 三角面，其中 Structure 1000、两窗共 24。候选 Structure 必须为 1000–1700 三角面，不能用减少原结构面数掩盖超过 700 的新增细节。这里的三角面计数可以验证总预算；“原主体面是否逐面保持”的证据仍应以资产代理的 source/candidate 比对报告为准。

## 朝向测量与几何处理

不实例化任何候选 FBX。直接读取源资产层级矩阵，分别计算 as-import 和与 v1 CloneModel 相同的根 X 反射方案；用每栋原 `Marker_Door` 的原点及 3 个基向量端点比较完整矩阵。最优方案误差必须 ≤2 mm，另一方案必须 >5 cm，避免位置重合但朝向错误或方案不可区分。同一类型的所有实例必须选择相同方案。

随后检查源两窗推算出的世界矩阵，并对源/原窗世界顶点集合做双向最近点误差检查，均要求 ≤2 mm，三角数均为 12。此检查验证几何占位，不声称对窗口索引绕序、UV 或材质像素做了完整拓扑同一性证明；实际原窗根本不被替换，相关原组件和引用在前后合同中严格保留。

### 真实 prefab 矩阵离线复核

再次只读解析 `Island.prefab` 中全部 11 栋与 22 窗的实际 serialized TRS，并用双精度矩阵独立复算。以下来自已保存 prefab，不是运行中的 Unity 或新的 V2 FBX 导入结果。

| 原屋代表实例 | Marker 世界位置（m） | as-import 与正确反射的 Marker 原点差 | 完整矩阵四点最大差 |
|---|---|---:|---:|
| 01 / teal | (-16.096000, 8.445084, 4.096000) | 0.992000 m | 2.592000 m |
| 02 / ochre | (-16.336000, 8.563678, 7.236000) | 1.072000 m | 2.672000 m |
| 03 / slate | (-16.336000, 8.561579, 10.340000) | 0.880000 m | 2.480000 m |

在本实现限定的两种根变换之间，三款门标记不在 X 中轴，单点已能区分这两个方案；完整矩阵额外覆盖旋转、缩放、手性。单标记不能泛化为对任意几何变形、任意来源错轴的全面证明，源资产仍需回读证据。

源 Blender 窗口中心经已知 Unity X 手性转换，再乘实际房屋与 LOD0 矩阵，与保存的 22 个窗口世界矩阵相比，最大四点差 **0.000001756 m**（约 0.00176 mm）。例如 01 的两窗世界位置为 `(-16.4095993,9.38908424,3.0048)` 与 `(-18.5904007,9.38908424,3.6)`。

这里没有对原窗口重复反射：v1 `CloneModel` 对导入根作 X 修正，`ExtractWindows` 只用 `SetParent(...,true)` 保存世界变换，随后移动 `Village_Windows` 中心时也保持子级世界 pose；窗负 X 尺度是原世界变换的分解结果。当前 helper 对**源模型根**构造一次候选反射，再直接比较源窗推导矩阵与原窗 `localToWorldMatrix`，没有对原窗再乘反射矩阵。

后窗 `Window_01` 原模型中心 X=0，仅比较它的原点或对称长方体顶点集合，确实不能识别某些左右镜像；当前完整矩阵检查在错误反射方案下产生约 **1.6 m** 的基向量端点差，会拒绝该方案。前窗错误方案差为 **1.056–1.2864 m**。双向顶点集合用于补充检查真实占位，不独自承担手性判断，也不能证明 UV 图案未镜像；原剧情窗并不替换，所以它的原 UV/材质不会受候选窗口数据影响。

只把各栋候选 `Structure` 子网格烘焙到岛局部空间，再按共享材质合批。法线用 inverse-transpose，负行列式变换翻转三角形第二/第三索引；在保留 UV0、已修正绕序和法线的基础上重新计算 tangent。必须有真实源法线及 UV0，遇到无效数据即失败，不补空 UV 或统一朝上的假法线。

去重含义：每个房屋主体只加入一次；源窗/标记仅测量、不实例化也不合并；新可见批次完成后删除本候选原 14 个批次的 Renderer/MeshFilter 组件。因此不会同时画旧合批和新模型。单一材质批次内按“房屋编号、源 mesh、顶点索引”复用顶点，合并映射到同一木材的槽时也可复用；不跨房屋焊接，不擅自删除新模型表面。报告检查输出总面数恰等于 11 栋新 Structure 之和。

## 原场景接口与碰撞保持

旧房屋分布固定，类型序列为 teal/ochre/slate/teal/ochre/slate/teal/ochre/slate/teal/ochre。

| 名称 | 类型 | 原局部位置（m，供审阅） | 原 yaw |
|---|---|---|---:|
| `VillageHouse_01` | teal | (-17.5, 8.269084, 3.6) | 90 |
| `VillageHouse_02` | ochre | (-17.8, 8.387678, 6.7) | 90 |
| `VillageHouse_03` | slate | (-17.8, 8.385579, 9.9) | 90 |
| `VillageHouse_04` | teal | (-17.8, 8.379089, 13.1) | 90 |
| `VillageHouse_05` | ochre | (-16.8, 8.376409, 16.3) | 90 |
| `VillageHouse_06` | slate | (-14, 8.388405, 18.3) | 180 |
| `VillageHouse_07` | teal | (-9, 8.026995, 3.7) | 270 |
| `VillageHouse_08` | ochre | (-9.4, 8.368514, 7.1) | 270 |
| `VillageHouse_09` | slate | (-9.5, 8.371063, 10.5) | 270 |
| `VillageHouse_10` | teal | (-9, 8.371510, 13.9) | 270 |
| `VillageHouse_11` | ochre | (-7.8, 8.184994, 17.3) | 270 |

表中浮点值只用于阅读；代码保留现有 transform，绝不按表内舍入值重建。每栋 scale 0.8；`LOD0` 包含原 -90° X 与负 X 比例转换，保持不变。

整合器保存并严格复核原有所有 Transform 引用、父级、名称、同级次序、局部 pose、世界矩阵、layer 和 active 状态。原 11 个 `LOD0/Structure` 的 MeshFilter/disabled Renderer 不被替换或启用；原 `SolidCollision` 上的 11 个 BoxCollider 对象本身、所有字段/引用、Layer 9 以及变换保持原值。村屋不是 MeshCollider；新装饰外伸不会自动得到新碰撞，不把新屋顶当作可走内景。

`Village_Windows` 原世界中心 (-13, 8.4, 10) 保持；22 个直接子物体 `VillageHouse_XX_Window_00/01` 各自保留同物体 Renderer、原 MeshFilter/mesh、原琥珀自发光 material 和世界矩阵。不会增加包裹层，不会把窗合批。剧情代码按直接子级和同物体 Renderer 找窗，因此这个层级契约必须保留。

原岛全部 Collider、Renderer、MeshFilter 都检查组件身份与完整序列化值；唯一允许移除的是原 `Village_Batches` 下 14 对 Renderer/MeshFilter。它们的 GameObject/Transform 和指向的 mesh/material 资产均保留。新可见几何只加入 `Village_Batches/__EnvV2VillageBatches`。已有此子树时直接拒绝重复运行，要求调用方重新从 v1 建立新候选，避免累计重复网格。

合同报告额外记录所有 `Marker_*` 以及 22 窗/11 BoxCollider 的前后路径、组件 ID、世界矩阵、mesh ID 和序列化字段；更广泛的 Anchor/Target/NPC/Cam 等也由“所有原 Transform”检查覆盖。

## 材质、文件写入和预算

复用 `EnvV2HouseSurfaceBuilder.Prepare` 建立当次 generation 内的 4 种木色：Whitewashed、Weathered、Honey、DarkBeam。`Wood_Endgrain` 与 `Wood_Honey` 共用 Honey；两种墙色、深梁分别映射对应木色。其它石材、铜、屋顶和屋顶高光直接引用原共享 Material，不改原材质。按现有 14 个原材质名减 5 个木色名再加 4 个新木色，预计 **13 个可见主体批次/共享材质**；运行时硬上限为 16，实际数量写入报告。原 22 窗继续单独显示，不计入上述主体材质数。

提供的木纹 texture 必须位于自有 Environment 路径。现有 HouseSurfaceBuilder 会将**这个明确传入的 texture importer**设置为 sRGB、Repeat、mipmap、Trilinear、aniso 4、最大 2048、CompressedHQ 并重新导入；不会修改其它纹理 importer。每次为村屋单独创建 4 个 generation 局部材质，避免覆盖祖母屋或先前候选材质。

所有生成资产写入传入 `Environment/Generated/...` 下唯一子目录 `Village_<UTC>_<id>/`，含 4 个 Wood 材质、按材质的合批 Mesh 与 `village-report.json`。不覆盖已有生成资产，不修改源 FBX，不删除旧 mesh/material。Mesh 不携带旧场景的 lightmap/static 标记。

面数预算：旧主体共 11,000，原窗共 264。新增上限 4×700 + 4×700 + 3×700 = **7,700**，所以村屋主体最高 18,700，总可见村屋含原窗最高 **18,964**。这只是几何/合批预算，不证明 Intel Iris Xe 的帧率。

**600k 的计数口径另行严格统计所有 MeshFilter 实例**，使用 `GetComponentsInChildren<MeshFilter>(true)`；不以是否有 Renderer、是否 enabled/active、是否当前 LOD 为筛选条件。引用同一 mesh 的多个实例按实例分别计数。原 11 个 disabled Structure 合计 **11,000** 面始终保留、始终计入，因此村屋三个分组的全 MeshFilter 基线为 **22,264**（旧可见批次 11,000 + 保留主体 11,000 + 窗 264）；替换后的全 MeshFilter 最高 **29,964**，绝不是把旧 disabled 主体虚假扣除后的 18,964。

报告字段 `actualBatchTriangleDelta` 使用实际读取的 `newVisibleStructureTriangles - oldVisibleStructureTriangles`，即仅扣除此次真正移除 MeshFilter 的旧批次。`allMeshFilterTrianglesBefore/expectedAllMeshFilterTrianglesAfter/allMeshFilterTrianglesAfter` 记录整个传入候选的前/预计后/实测后总数，要求后值恰等于前值加真实批次差额，且 ≤600,000。另核验 `villageAllMeshFilterTrianglesBefore/After` 与保留的 `preservedDisabledStructureTriangles`、`allMeshFiltersBefore/After`。这项检查只覆盖本 helper 调用结束这一刻；后续草地、海面或其它 builder 运行完成后，总整合器还必须重新以同一全 MeshFilter 口径检查 600k，不能只遍历 Renderer 而漏掉已移除 Renderer 的保留旧网格。

采用“先预检，再在失活新子树内建好网格，最后移除旧渲染组件并启用新子树”的顺序。失败时删除仅本次创建的子树，但不会伪造已删除组件的旧对象身份，也不删除生成资产；调用方必须按总整合器现有 finally 流程丢弃临时场景。生成后需要 root 的独立候选截图与正常游玩验证，才能判断材质和形体是否改善。

## 离线编译证据与边界

2026-10-22，本机 `6000.3.26f1` 的 Roslyn 与 UnityEngine/UnityEditor 程序集，对当时 staging 的 **7 个 Editor 文件 + 2 个 Runtime 文件**联合编译成功，exitCode **0**，无编译诊断。包括新 `EnvV2VillageBuilder`、原 `EnvV2HouseSurfaceBuilder` 和 root 的 `EnvV2CandidateBuilder`。

首轮输出临时 DLL：`C:\Users\20665\AppData\Local\Temp\EnvV2VillageCompile_c952c2ef716f4e5d981cfb51b04e84aa.dll`。这只是普通 dotnet/csc 调用，没有启动或请求运行中的 Unity Editor。

补充全 MeshFilter 预算后重新联合编译仍为 exitCode **0**、无诊断，输出 `C:\Users\20665\AppData\Local\Temp\EnvV2VillageCompile_ccb85e6f9b574b3ea1fd45593ac9ace3.dll`，同样 7 个 Editor + 2 个 Runtime 文件。

可复现 PowerShell（在仓库根运行，只写系统 temp DLL）：

```powershell
$unityData = 'C:/Program Files/Unity/Hub/Editor/6000.3.26f1/Editor/Data'
$target = Join-Path ([IO.Path]::GetTempPath()) ('EnvV2VillageCompile_' + [guid]::NewGuid().ToString('N') + '.dll')
$compilerArgs = @('-nologo', '-target:library', '-define:UNITY_EDITOR', '-langversion:9', '-nostdlib+', ('-out:' + $target),
    ('-r:' + $unityData + '/NetStandard/ref/2.1.0/netstandard.dll'),
    ('-r:' + $unityData + '/Managed/UnityEditor.dll'),
    '-r:GameProject/Library/ScriptAssemblies/Unity.RenderPipelines.Core.Runtime.dll',
    '-r:GameProject/Library/ScriptAssemblies/Unity.RenderPipelines.Universal.Runtime.dll')
$compilerArgs += Get-ChildItem -LiteralPath ($unityData + '/Managed/UnityEngine') -Filter *.dll | ForEach-Object { '-r:' + $_.FullName }
$compilerArgs += Get-ChildItem -LiteralPath 'art/generated/env-v2/staging/Editor' -Filter *.cs | ForEach-Object { $_.FullName }
$compilerArgs += Get-ChildItem -LiteralPath 'art/generated/env-v2/staging/Runtime' -Filter *.cs | ForEach-Object { $_.FullName }
& ($unityData + '/NetCoreRuntime/dotnet.exe') ($unityData + '/DotNetSdkRoslyn/csc.dll') @compilerArgs
$LASTEXITCODE
```

C# 离线编译仅证明所用 C# 语法、类型与本机 DLL 接口能编译；不证明模型成功导入、Build 运行通过、Shader/HLSL/GLSL 编译通过、窗口剧情动画正确或画面质量达标。后续 root 应检查报告中的 11/22/11 数量、4/4/3 类型、各型号朝向误差、原窗/Collider 合同、合批面数和真实候选截图。
