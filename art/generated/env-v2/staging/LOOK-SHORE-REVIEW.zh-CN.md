# Look / Sky / Sea 离线复核与海岸距离图接口

状态：**此前 C# 离线编译通过；Sky/Sea 的限定 Direct3D HLSL 离线探针通过，仍未经过 Unity 导入编译。本代理未在 Unity 生成或验证实际海岸图，未验证画面、WebGL 或帧率。** 追加复核仅修改 staging 的两个 Sky/Sea Shader 和本文，没有控制 Editor、修改 Assets、修改 PackageCache 或写全局 RenderSettings。C# 通过与 Shader 通过是两项独立证据。

## Look 复核

`Runtime/EnvironmentLookLibrary.cs`、`Runtime/EnvironmentLookRig.cs`、`Editor/EnvV2LookBuilder.cs` 无 C# 编译错误，本次保持原文件不变。与新增 Shore Builder 一起使用以下本机程序集联合离线编译成功：

- Unity 6000.3.26f1 自带 `NetCoreRuntime/dotnet.exe`、`DotNetSdkRoslyn/csc.dll`；参数 `-target:library -define:UNITY_EDITOR -langversion:9 -nostdlib+`。
- Unity 的 `NetStandard/ref/2.1.0/netstandard.dll`、`Managed/UnityEditor.dll`、`Managed/UnityEngine/*.dll`。
- 当前项目 `Library/ScriptAssemblies/Unity.RenderPipelines.Core.Runtime.dll` 与 `Unity.RenderPipelines.Universal.Runtime.dll`，对应本地 URP 17.3。
- 成功输出：`C:/Users/20665/AppData/Local/Temp/EnvV2LookShoreCompile_1545ec24d29d4f19980d2af9838bdde6.dll`，编译退出码 0、无诊断输出。临时 DLL 不进入项目。

没有 Awake/Start/Update/LateUpdate/OnEnable 自动写场景逻辑。`ApplyChapter(id)` 默认 `applyGlobalEnvironment=false`，只更新显式引用的自有灯、Volume 和天空/海面 PropertyBlock；`ApplyGlobalEnvironment` 必须由唯一剧情控制入口显式调用。不能同时让 Claude 的 NightSky.LateUpdate 和该入口写 ambient/fog。

注意：MaterialPropertyBlock 不作为 Prefab 的持久序列化材质设置保存。游戏开始/章节切换时仍应由剧情显式调用 `ApplyChapter`，或由主代理设置自有材质的初始默认值。Attach 只建立组件引用及夜间 Profile，不自动启动剧情、不改变全局天空。

## 两个 Shader 的限定修正

1. Sky/Sea 显式声明 target 3.5，目标为 WebGL2 能力等级；这不代替 WebGL 实测。
2. Sea 增加主光（含 cascades、screen shadow）、附加光和软阴影变体，反射乘 `shadowAttenuation`；此前采样颜色/距离衰减而忽略阴影，会让受遮挡的反射仍出现。
3. Sea 的 Forward+ 附加方向光循环使用本地 `CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK`，变量名保持其要求的 `lightIndex`。
4. Sea 为两块巨大三角形，级联阴影必须按片元世界位置选择，不能在海面四顶点选完再跨级联插值；screen shadow 分支则使用 ComputeScreenPos。
5. `_ShoreRect.zw` 加最小正数保护，`_ShoreEnabled` 限在 0–1。没有更改天空/海洋的艺术参数或章节数值。
6. 追加 Sky 退化保护：眼点恰好重合时采用有限视向；`_EarthDirection` 为零或极小时回退到现有默认方向；接近正/负 Y 轴时换用 Z 参考轴建立正交基，避免叉积变零；`_EarthRadius` 的除数最低为 0.001，防止脚本绕过 Inspector Range 后传入零或负数。有效默认参数的颜色、方向和半径均保持原值。
7. Sea 视向改用 `SafeNormalize(GetWorldSpaceViewDir(positionWS))`，透视与正交相机走本地 URP 对应分支。海面法线的 Y 恒为 1，原先的法线 normalize 不存在零向量问题，保留原式。
8. Sea 无主光阴影时明确使用零 shadowCoord；单图/级联仍按片元变换，screen shadow 仍使用 ComputeScreenPos。

### 本地 URP 接口核对

- 依据 `com.unity.render-pipelines.universal@746735fb06f2`（17.3）与 `com.unity.render-pipelines.core@9e589b64c45d`，没有根据网上其他版本猜测 API。
- `Core.hlsl` 根据 `_CLUSTER_LIGHT_LOOP` 定义 `USE_CLUSTER_LIGHT_LOOP`，并在 clustered 路径自动定义 `_ADDITIONAL_LIGHTS`。Sea 使用当前关键词，未依赖已弃用的 `_FORWARD_PLUS`。
- `RealtimeLights.hlsl` 的 clustered `LIGHT_LOOP_BEGIN` 直接引用局部变量 `inputData.positionWS` 和 `inputData.normalizedScreenSpaceUV`；Sea 在循环前填写这两项，循环内部保留宏要求的 `lightIndex`。附加方向光单独循环，点光/聚光由宏遍历；普通 Forward 用 `GetAdditionalLightsCount()` 与 per-object 索引。
- `GetMainLight(float4,float3,half4)` 和 `GetAdditionalLight(uint,float3,half4)` 都存在，并提供 shadowAttenuation。`Light`、`InputData`、世界/屏幕坐标 API 与 CBUFFER/纹理宏在实际 include 链中可用。
- 当前 PC Renderer 配置值 2 是 Forward+，Mobile Renderer 值 0 是 Forward；两份 RP Asset 的附加光模式值 1 均为 PerPixel。本轮没有改这些配置。未声明“附加光按顶点”模式的海面高光实现。
- Material 的颜色/向量/数值统一放在 `UnityPerMaterial` CBUFFER，Shore texture/sampler 在 CBUFFER 外；LookRig 当前设置的属性名与两个 Shader 一致。保留材质参数接口。
- Sky/Sea 当前不调用 URP `MixFog`：海面使用自身已有的远距渐变，天空使用自有地平线渐变。本轮未在缺少画面证据时更改此艺术行为；章节全局雾与海天交界仍需实景核对。

### 独立 HLSL 编译探针及边界

2026-10-22 使用系统 `C:/Windows/System32/D3DCompiler_47.dll` 的 `D3DCompile`，由 PowerShell / C# P/Invoke 在内存完成；没有运行 Unity Editor、UnityShaderCompiler.exe、Unity CLI，也没有输出或导入编译字节码。系统 DLL 版本 `10.0.26100.9168`，SHA256 `6B3DEE26A3FA46ADCE2FD1C543B0A3605C5DE16B636BD42341ADE6F1D7A27A44`。

探针取每个 Shader 的 HLSLPROGRAM，递归展开本机实际 PackageCache includes，并保留条件编译。设置 `SHADER_API_D3D11=1`、`SHADER_TARGET=35`、`UNITY_COMPILER_HLSL=1`，按阶段设置 `SHADER_STAGE_VERTEX` 或 `SHADER_STAGE_FRAGMENT`，再显式定义下表的变体。D3DCompile 使用 backward compatibility 标志 4096，使本地库的 half 类型按此 DX11 路径处理。

| Shader / 阶段 | 编译路径 | 成功 / 失败 | 字节码长度 |
|---|---|---|---|
| Sky / vertex | vs_4_0，基础 | 1 / 0 | 5380 |
| Sky / fragment | ps_4_0，基础 | 1 / 0 | 28832 |
| Sea / vertex | vs_4_0，基础 | 1 / 0 | 5416 |
| Sea / fragment | ps_4_0，100 个灯光/阴影组合 | 100 / 0 | 10568–36920 |

以上成功结果的 HRESULT 均为 0。另一次基础探针中，Sky/Sea 的 vs_5_0 与 ps_5_0 共 4 项也通过。100 个 Sea fragment 组合具体为：

- Forward 无附加光：4 个主阴影状态 × 5 个软阴影状态 = 20。
- Forward 有附加光：上述 20 × 附加阴影开/关 = 40。
- Forward+：上述 20 × 附加阴影开/关 = 40；特意只定义 `_CLUSTER_LIGHT_LOOP`，验证 Core 自动启用附加光的路径。

主阴影状态为无、`_MAIN_LIGHT_SHADOWS`、`_MAIN_LIGHT_SHADOWS_CASCADE`、`_MAIN_LIGHT_SHADOWS_SCREEN`。软阴影状态为无、`_SHADOWS_SOFT`、`_SHADOWS_SOFT_LOW`、`_SHADOWS_SOFT_MEDIUM`、`_SHADOWS_SOFT_HIGH`。附加阴影关键词为 `_ADDITIONAL_LIGHT_SHADOWS`。部分组合在实际剔除后不会保留，这里主动检查了其源码编译路径。

**探针与 Unity 编译的差异必须保留：**

1. 原生 D3DCompile 不解析 ShaderLab，因此探针剥离 Unity 专有 pragma，手动选择平台/阶段/关键词；未验证 ShaderLab 导入、URP variant stripping、SRP Batcher 状态或材质资源绑定。
2. 为支持 in-memory include 展开，各 include 加独立保护宏；缺失平台私有包保留为条件分支中的 `#error`，本次 DX11 路径没有进入这些分支。
3. 首次探针在库 `Common.hlsl` 的空形参宏 `#define PopMarker()` 上被 FXC 旧预处理器拒绝。探针仅在内存将这个**候选 Shader 从未调用的声明**变成 `#define PopMarker(unused)` 后继续；磁盘 Common.hlsl 没变，也没有改任何着色运算。此前该失败是夹具兼容问题，不被当成游戏 Shader 编译错误。
4. 这证明受限 DX11 HLSL 路径可生成字节码，**不能声称 Unity Shader 编译已通过，也不能声称 WebGL2/GLSL 已编译或实际阴影已正确显示**。GLES、实际相机、真实灯开关、地球极轴输入与视觉效果仍需主代理在获授权的 Editor 阶段验证。

本次 Shader SHA256：

- `EnvNightSkyV2.shader`：`464A7C1726C4C2C44AE8957AA5E02415E983E4F0BD4248F0B18E91164BFB6D75`。
- `EnvNightSeaV2.shader`：`183B257151AC625AE0A66A95FA1C2BBAFFFBCFDD99796502CE9C9D98005D363A`。

另：Meadow / TerrainSurface 的逐片元级联阴影和 URP fragment fog 已在上一轮独立限定任务中修复，并通知整合代理。本轮未再次修改它们；上文的 103 项 SM4 探针结果**不包含**这两个 Shader。

## EnvV2ShoreMapBuilder

```csharp
using JieGuang.EnvironmentTools;

var coast = EnvV2ShoreMapBuilder.Bake(
    islandRoot: islandInstance,
    seaHeight: -0.16f, // 必须与实际平面海面世界 Y 一致
    resolution: 256,  // 仅 256 或 512
    paddingMetres: 9f);

// 由主代理自行对“自己的 SeaV2 材质”赋值并保存；Builder 不自动改任何 Renderer/材质。
ownedSeaV2Material.SetTexture("_ShoreMap", coast.texture);
ownedSeaV2Material.SetVector("_ShoreRect", coast.worldRect);
ownedSeaV2Material.SetFloat("_ShoreEnabled", 1f);
```

返回 `Result.texture`、`Result.worldRect`、`Result.report`。`worldRect=(minWorldX,minWorldZ,widthMetres,depthMetres)`；纹理 V/y 正方向与世界 Z 一致。

输出限定在 `Assets/JieGuang/Environment/Generated/V2ShoreMaps/ShoreGeneration_时间戳/`：

- `ShoreDistance_R8_Linear.asset`：R8 UNorm、linear、Clamp、Trilinear、完整 mip 链；CPU 可读以便后续验证。256 图含 mip 约 85KiB 的原始 R8 数据量，512 图约 341KiB；未据此声称实际 GPU 内存。
- `shore-report.json`：来源网格路径、源面数、算法分支、世界矩形、闭合情况、距离像素统计、格式检查及未验证项。

它只读传入 Island 唯一直属 Terrain 下实际的 `IslandGround` 和 `CoastalCliff` Mesh，应用各自当前世界变换（包括 v1 FBX 的反射修正）；必须 readable，不修改 Importer。

算法优先将源三角形与指定海面 Y 相交，得到**真实水线段**。不足三个线段时才改为焊接原始 Ground 顶点后的实际边界投影；报告明确标记 fallback，不用手绘月牙、Walkable_Boundary 或包围盒冒充海岸。按 1mm 坐标精度去重后，若存在端点度数不为 2，会保留警告，不能据图生成成功宣称地形水密或掩盖破面。

像素保存无符号 XZ 最近距离：`R = clamp(distanceMetres / 8,0,1)`，精度约 3.14cm/级，且空间采样还受 256/512 分辨率限制。图中陆地下方同样有距离值；它不是深度图或陆地遮罩，地面/崖壁正常遮挡海面。使用 8m 分格的线段索引缩小候选集，避免每个像素遍历整岛所有面。

边距会按像素大小自动抬高至 8m 之外，确认四条外边都是白色，使 Clamp 和 mip 不在远海产生假泡沫。格式/边距/非平凡距离场检查失败不保存纹理。没有物理射线、场景操作、全局状态、运行时 Update、贴图自动绑定或地形修改。

实际执行后的必要检查：海面高度是否匹配、报告是水线还是投影 fallback、轮廓开口警告、码头/岬角/村崖三个区域的浪痕是否贴真实接岸、地图边界外是否无亮边；然后再拍摄固定机位和移动视频。这里只实现并离线编译了生成器，还没有这些验证结果。
