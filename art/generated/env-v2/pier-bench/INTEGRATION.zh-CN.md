# 栈桥与长椅表面候选：独立整合接口

2026-10-22。本轮只新增 `staging/Editor/EnvV2PierBenchBuilder.cs` 与本文，没有改 CandidateBuilder、Assets、主场景或全局交接文件，没有操作 Unity。root 已接受离线表面候选进入后续验证；这不代表 Unity 导入、碰撞游玩或画面验收已经通过。

## 调用与输入

```csharp
EnvV2PierBenchBuilder.Report report = EnvV2PierBenchBuilder.Build(
    island,
    generationFolder,
    "Assets/JieGuang/Environment/Textures/v2/wood_albedo_v1.png");
```

命名空间 `JieGuang.EnvironmentTools`，完整入口为：

```csharp
public static Report Build(GameObject island, string generationFolder, string woodTexture)
```

- `island`：调用方自己的、完全脱离 prefab 的 `Island` 根对象，所在场景已加载且尚未保存；根必须为单位变换。拒绝 prefab 资产、任何仍连接 prefab 的后代、Prefab Mode、播放/编译/导入期间。调用方仍须遵守 Unity 独占和 `status` / `pipeline list` 前置检查。
- `generationFolder`：必须位于 `Assets/JieGuang/Environment/Generated/` 内。辅助器在其下创建带时间和随机后缀的 `PierBench_*` 独立目录，拒绝越界、相对跳转、符号链接/目录联接、覆盖已有资产。
- `woodTexture`：Environment 内已经导入的原始 `wood_albedo_v1.png`。原文件 SHA256 必须为 `2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1`；要求 sRGB、mipmap、Repeat、非 Point 过滤。本辅助器只读 importer，不重新导入或修改屋子等共享纹理的设置。

调用前由 root 的现有 `PrepareModel` 准备以下两个 FBX：readable=true，importAnimation=false，addCollider=false；保留其现有轴/单位设置。

| 导入路径 | 审阅候选 FBX SHA256 |
|---|---|
| `Assets/JieGuang/Environment/ModelsV2/pier_module/pier_module_v2_candidate.fbx` | `1155f4cfa54dea293089377ba08df626596a1aec26a35712c176d279cbd6465f` |
| `Assets/JieGuang/Environment/ModelsV2/bench/bench_v2_candidate.fbx` | `c5bb3190f178f1b217cdcbc888b329bf8654c78330b7a564cab6f585251f194e` |

对应源文件位于本目录的 `pier_module/` 与 `bench/` 子目录。代码有意固定审阅版本的哈希；候选版本改变时必须重新审阅并明确更新，不自动接纳不同文件。`pier_end` 不导入、不实例化、不参与替换。

## 修改范围与保留合同

仅访问真实布局中的 `Pier/PierDeck_01..03/LOD0/Structure` 和 `Props/Bench/LOD0/Structure`。核验其旧 mesh GUID、根世界矩阵、层级、单个 renderer、面数、原始材质槽和碰撞设置。全岛必须恰有 3 个原 pier_module 网格、1 个原 bench 网格、0 个 pier_end 网格，拒绝重复整合或静默跳过。若目标 Renderer 有 MaterialPropertyBlock 则中止，避免未知覆盖遮住新木纹。

只更换这 **4 个现有 MeshFilter.sharedMesh** 和 **4 个现有 MeshRenderer.sharedMaterials**；不新建场景对象，不移除组件，不调用 SetActive，不更改任何原 TRS、父级、层级顺序、名称、Layer、灯、锚点、Marker、Renderer 的阴影/探针/启用等其它序列化属性。

- 三段桥仍各用独立 Layer 8 `WalkableDeck/BoxCollider`，center `(0,-.1,0)`，size `(2.4,.2,3)`，原组件和设置不变。
- 长椅仍用同一 `Structure/MeshCollider`，继续引用旧 bench mesh。更换的是同 GO 上 MeshFilter 的引用，不修改旧 mesh 资产，也不把新视觉网格分配给碰撞。
- 保留全部原世界变换，包括 `NPC_Bench` 的正式坐向。FBX `Marker_Seat.forward` 并非人物坐向，本辅助器不据它旋转人物或椅子。
- 不删除旧模型资产。生成 4 个独立网格副本（3 段桥各一份，便于保留并报告各自推导矩阵），以及 4 个共享木材材质。旧铁箍材质引用保持不变。

前后会比较全部原 Transform、组件身份，以及全部 Collider/Renderer/MeshFilter 的序列化状态。仅上述目标网格引用和材质数组被明确排除，其它字段必须一致；目标 Collider 另有显式身份、引用与序列化记录。全部 Marker、Anchor、NPC、Target、Cam 的世界矩阵也进入报告。旧源模型文件 SHA 与旧内存 mesh 内容哈希在提交后再次比较。

## 矩阵与几何校验

不猜 FBX 轴，不额外在原 GO 上应用 -90°X 或负 X。对旧 Structure 为 `O`、旧 Marker 为 `A`、新导入 Structure 为 `N`、新 Marker 为 `B`，使用完整世界矩阵：

```text
newMeshToOldStructure = inverse(O.world) × A.world × inverse(B.world) × N.world
```

比较 Marker 原点和三个基向量端点，而非仅位置。桥以 Entry 推导后，再用 Exit 的完整矩阵复核；长椅以唯一 Seat 的完整矩阵推导，并由完整几何校验封闭约束。所有现有 Marker 自身保持不变。

把新网格复制并烘焙到旧 Structure 的局部坐标，法线用逆转置变换。行列式为负时反转每个三角面的绕序，然后重算 bounds 和适配新 UV 的 tangents。不会覆盖原 mesh 或导入 FBX 的 mesh。

校验采用 **20 微米世界坐标/Marker 误差上限**，用于容纳单精度导入和世界矩阵运算误差；不是允许尺寸修改的制作公差：

1. 双向顶点点集最近距离比较，避免只验证单向子集。
2. 三角面总数、每个 submesh 的索引数量与三角拓扑、全部索引范围必须正确。
3. 每个原材质槽单独做一对一三角面匹配，允许循环起点变化，不允许反向绕序；重复面按重数计算，不能悄悄增删面、换材质槽或改三角剖分。
4. 对应三角面角点的法线夹角最多 `.25°`；明确保留光滑/硬边表现，仅重算新 UV 切线。
5. UV0 顶点数完整、数值有限且不塌缩。源 FBX 的准确文件哈希同时保证输入是审阅过的 UV 候选。

Unity 的 UV seam 可能拆顶点、重排顶点 ID，因此不要求新旧原始索引整数数组相同。这里验证的是经每槽索引解出的**有朝向的三角面集合、重数及角点法线**，不是宽松地以相同包围盒或面数代替几何验证。若导入改变三角剖分/法线而未满足合同，会明确中止，届时应检查实际导入差异，不擅自放宽公差。

## 专属四木材映射

直接使用此候选 manifest 的原图 × tint 与 roughness，不调用屋材 helper，不修改原共享材质。

| 源材质 | 共享候选材质 | RGB tint | roughness | URP smoothness |
|---|---|---|---:|---:|
| `Wood_Endgrain` | `CoastalWood_Light` | .62 / .57 / .46 | .88 | .12 |
| `Wood_Honey` | `CoastalWood_Brown` | .48 / .42 / .33 | .87 | .13 |
| `Wood_DarkBeams` | `CoastalWood_Dark` | .26 / .22 / .17 | .90 | .10 |
| `Wood_Weathered` | `CoastalWood_Silver` | .38 / .38 / .32 | .92 | .08 |

使用 URP/Lit，UV0 原比例、贴图 scale1/offset0、不透明、非金属、背面剔除、无自发光、无 normal map。原桥 5 槽与长椅 3 槽的顺序完全保留；桥第五槽 `Iron_Blackened` 继续使用原材质。

这些是相同数值参数，不能保证 Blender 与 URP 不同色彩管理/灯光下逐像素一致。端面仍是同一木图的平面取样，没有独立年轮图、烘焙法线、额外倒角或新接缝。

## 报告与面数

成功调用返回 `[Serializable] Report`，并在独立生成目录内保存 `pier-bench-report.json`。主要内容：

- 四实例路径、源/候选 FBX SHA256、旧/生成 mesh 内容哈希；Blender manifest 几何哈希单列为参考，不冒称与 Unity 重排后的 buffer 哈希相同。
- 每实例推导矩阵、行列式与是否翻绕序、Marker/双向顶点/每面角点最大误差、法线误差、匹配面数、submesh 与 UV0 数量。
- 保留的碰撞组件 ID、旧 mesh ID/GUID、完整序列化状态；锚点与 Marker 前后矩阵。
- 4 共享木材映射与输出路径，前后目标面数、前后全岛 MeshFilter 数与面数。

四实例绝对总面数固定为 **3 × 456 + 324 = 1692**，新增 **0**。顶层素材 manifest 的 `budget_actual_island=1200` 是原任务的“允许新增面上限”，不是绝对总面数；本整合器不使用该数字扣减旧几何。

全岛预算枚举所有 MeshFilter，包括 inactive、Renderer disabled、无 Renderer 与全部 LOD；本 helper 替换前后必须完全相等且不超过 600,000。既有失活 Structure 与其旧 mesh 仍计数，不以关 renderer 虚假扣面。最后若 root 又运行其它构建器，仍需重新核对最终全岛预算。

所有预检、几何匹配先通过，才建立生成资产并交换引用。发生异常会尽量恢复四个旧视觉网格/材质引用，不删除场景对象或旧资产；调用方仍须丢弃整个临时候选场景，不能把恢复引用当作事务完整回滚。已保存的独立诊断资产可能保留，辅助器不清理他人文件。

## 离线验证证据与边界

2026-10-22 22:52:24 UTC，使用本机 Unity `6000.3.26f1` 自带 NetCoreRuntime/dotnet、DotNetSdkRoslyn/csc 及本地 Unity/URP 引用程序集，联合编译 staging 的 **8 个 Editor + 2 个 Runtime** 文件：退出码 **0**，诊断 **0**，引用程序集 201 个。该批包含此 helper、CandidateBuilder、Village/House/Look/Meadow/Shore/Surface helpers 与两个 Look runtime 类；没有修改这些其它文件。

- 编译时本文件 SHA256：`EEF78C6E5EFAF2FD8658746D59E39ED776B3ABB048BA05D1F37FFBFA4D1242BD`
- 临时输出：`C:\Users\20665\AppData\Local\Temp\EnvV2PierBenchJoint_e39623e1a4c14fdf80ef529db14cebe3.dll`
- 单类编译也通过。首次夹具把旧 `UnityEditor.dll` 与模块 DLL 同时引用导致重复类型，排除旧聚合 DLL 后通过；该夹具错误不是 Unity 或模型校验失败。

可复现联合编译命令（仅在系统临时目录输出 DLL，不调用 Unity Editor）：

```powershell
$ed = 'C:\Program Files\Unity\Hub\Editor\6000.3.26f1\Editor\Data'
$out = Join-Path $env:TEMP ('EnvV2PierBenchJoint_' + [guid]::NewGuid().ToString('N') + '.dll')
$refs = @(Get-ChildItem -LiteralPath "$ed\NetStandard\ref\2.1.0" -Filter '*.dll') +
        @(Get-ChildItem -LiteralPath "$ed\Managed\UnityEngine" -Filter '*.dll') +
        @(Get-ChildItem -LiteralPath "$ed\Managed" -Filter 'UnityEditor*.dll' | Where-Object Name -ne 'UnityEditor.dll') +
        @(Get-ChildItem -LiteralPath 'GameProject/Library/ScriptAssemblies' -Filter 'Unity.*.dll')
$sources = @(Get-ChildItem -LiteralPath 'art/generated/env-v2/staging/Editor' -Filter '*.cs') +
           @(Get-ChildItem -LiteralPath 'art/generated/env-v2/staging/Runtime' -Filter '*.cs')
$arguments = @('/nologo','/target:library','/langversion:latest','/define:UNITY_EDITOR','/nostdlib+',('/out:'+$out))
$arguments += @($refs | ForEach-Object { '/reference:' + $_.FullName })
$arguments += @($sources.FullName)
& "$ed\NetCoreRuntime\dotnet.exe" "$ed\DotNetSdkRoslyn\csc.dll" @arguments
$LASTEXITCODE
```

**尚未执行** Build、FBX 在 Unity 内的导入/矩阵/逐面校验、报告生成、真实碰撞/落座、三模块木纹重复、过滤闪烁或性能测量。C# 离线编译只证明该代码对本地引用程序集可编译，不等于这些运行检查已经通过。接入前后仍需 root 在其拥有的 Unity 时段进行候选验证；不自动晋升正式 Island.prefab。
