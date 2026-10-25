# 原创地表材质候选：接入与验证

2026-10-22。此交付仅为离线候选：`Shaders/TerrainSurface.shader`、`Editor/EnvV2SurfaceBuilder.cs`。C# 已使用本机 Unity 6000.3.26f1 的 Roslyn、UnityEditor.dll、UnityEngine 模块和 netstandard 参考程序集离线编译通过；没有导入 Assets、操作 Unity 或编译验证 HLSL。图片效果、游戏灯光联调、WebGL 和帧率均未验证。

已先查看用户生成的 `art/generated/env-v2/textures/meadow_albedo_v1.png`，未修改它。原图以苔藓/草根/碎土颗粒构成，直接乘暖色会强化黄褐；候选保留它的亮度纹理，少量保留原始色彩，再由原创银绿、深灰土调色控制整体。源图 SHA256：`44cbb021fe261d82ef024c42bc04a16525011234cc9c825f0ecb21e58224c74a`。

## 明确入口和写入范围

由主代理在拥有 Unity 操作权并完成状态检查后，导入两个候选文件和自己的原图。原图按 Default、sRGB、Repeat、有 mip、双线性或三线性导入；Builder 只检查，不替你改 Importer。

```csharp
using JieGuang.EnvironmentTools;

// islandInstance 是自己的 EnvTest 实例或 LoadPrefabContents 的结果，不能传磁盘 prefab 资产。
var plan = EnvV2SurfaceBuilder.Plan(islandInstance); // 只读，先核对槽位
var report = EnvV2SurfaceBuilder.Build(
    islandInstance,
    "Assets/JieGuang/Environment/Textures/v2/meadow_albedo_v1.png");
// 主代理检查报告、截图后，自行保存自己的 prefab/场景。
```

报告写到 `Assets/JieGuang/Environment/Generated/V2Surface/SurfaceGeneration_时间戳/surface-report.json`。每次生成独立材质，旧材质及旧生成目录全部保留；不调用 SaveAssets、SaveScene 或 SaveAsPrefabAsset，不改几何、碰撞、Transform、Package 或其他目录。

只识别给定 Island 的唯一直属 `Terrain` 下这三种唯一 Renderer，以及明确的材质槽：

| Renderer | 可替换的原材质名 |
|---|---|
| IslandGround | Ground_Moss、Ground_Sage、Ground_Earth |
| StonePaths | Path_WeatheredStone、Path_WarmStone |
| CoastalCliff | Cliff_BlueSlate、Cliff_SoftSlate、Shore_Sand |

未知槽保持原引用；某 Renderer 缺失、重复或完全没有匹配槽即终止。没有“按名字包含 Ground 就全局替换”的后备操作。允许在本候选已有材质上重新生成，报告保存的是此次替换前的引用，所以可以逐代回退。

```csharp
EnvV2SurfaceBuilder.Revert(islandInstance, report.generationPath + "/surface-report.json");
```

Revert 在动手前检查所有槽仍对应指定报告；有后来编辑就拒绝覆盖。Builder 失败回滚也只恢复仍然持有本次候选材质的槽。窗口、光树、铜木道具和其他 Renderer 不在范围内。

## Shader 全部自定义参数

Shader 名：`JieGuang/Environment/TerrainSurface`。各材质共用代码，模式为每次 draw 固定值；没有依据像素随机切换材质的分支。

| 参数 | 默认/候选值 | 含义与注意 |
|---|---|---|
| `_SurfaceMode` | 0 地面 / 1 石板或砂岩 / 2 崖壁 | Ground 采样原创图；Stone/Cliff 使用原创程序纹理，不把草根图贴到崖壁 |
| `_BaseMap` | 已导入原创 albedo | 只 Ground 读取。旧网格 UV 不使用；贴图 ST 不作为尺度入口 |
| `_BaseColor` | 各槽独立，地面约 (.235,.315,.270) | 主色。颜色只在材质候选内调整，原材质不变 |
| `_SecondaryColor` | 地面约 (.155,.225,.190) | 低频色斑中的次色，避免整片同色，差异保持克制 |
| `_SoilColor` | (.135,.155,.145) | 中性深土，不用偏橙泥土抢走暖灯颜色 |
| `_TextureMeters` | 2m | 地面主纹完整重复的世界尺度，不随原 UV 或对象缩放而改变 |
| `_TexturePivot` | .18 | 原图线性亮度中心，用于将亮度细节归一化。不是曝光值 |
| `_TextureContrast` | .32 | 源纹理亮度调制比例；增大前先看走动时的高频闪烁 |
| `_TextureChroma` | .08 | 原始纹理色彩保留量；0 只保留亮度，.08 保留少量自然偏色 |
| `_MacroMeters` | 5.5m | 世界 XZ 上慢变化色斑，建议 4–7m；不是硬边拼贴 |
| `_SoilAmount` | 苔藓 .10 / 鼠尾草 .12 / 土 .65 | 用同一慢色斑控制深土混合 |
| `_StoneMeters` | .85m | 石面自然宽色差尺度；不生成额外方格、砂浆线或假石板边 |
| `_CliffMeters` | 2.7m | 崖壁三平面岩石宽纹理尺度，按世界法线四次权重混合 |
| `_LayerMeters` | 1.3m | 经 XZ 噪声扭曲的地质色层尺度，使用非周期噪声，不画等距水平波纹 |
| `_DetailStrength` | .07–.12 | Stone/Cliff 小尺度灰度差，避免白噪点、满屏细裂纹 |
| `_Roughness` | .86–.96 | 1 最粗糙；全部 metallic 固定 0，保持软石/土的漫反射 |
| `_RoughnessVariation` | .045 | 随细纹轻微变化，防止整片塑料式均匀反光 |
| `_ReliefMeters` | Ground .004m / Stone .007m / Cliff .024m | 微弱高度场导数凹凸；设 0 可单独做开关对比。它不改变实际表面和轮廓 |

基础色与色斑由同一世界位置计算，纹理没有逐帧漂移。两次地面采样采用不同静止方向和尺度进行轻混合，减少原图的重复感；这不是宣称原图已完全无缝，必须在俯视与沿路移动时检查。

## 法线、光照与开销

- **没有独立 normal 贴图**。高度来自已有 albedo 亮度或同一程序石纹，利用屏幕导数构造微弱表面法线；Forward 和 DepthNormals 用相同方法。没有顶点位移、细分、额外几何，也不补救真实地形开口或硬折线。
- URP 使用本地 17.3 的 `UniversalFragmentPBR`、`_CLUSTER_LIGHT_LOOP`、主光/附加灯及阴影变体；含软阴影、SSAO 接口、Light Cookie 与 Fog。Shader emission 固定 0，草地不会自行发光。
- 光照环境采用 SH，适配当前没有烘焙地形光照的方案；此候选不提供烘焙 lightmap UV2/Meta Pass 接入，不能声称支持完整烘焙流程。
- Ground 每片元两次 albedo 采样 + 一组低频值噪声。Stone 不采样纹理。Cliff 使用低频三平面程序值纹理和少量细节，不含反射、透明、深度取样、POM 或体积效果。DepthNormals 需要再求同一高度场，是否有实际成本取决于活动 Renderer 的深度/SSAO 管线，尚未测 GPU 时间。
- 目标为 WebGL2 的 Shader target 3.5，无 compute/geometry shader；这只是实现选择，须在目标 WebGL 构建/浏览器实际验证后才能称为兼容。

## 报告与验证接口

`Plan()` 给出 Renderer 相对路径、槽索引、原材质路径/GUID、原键名和模式。`Build()` 在真实执行时额外核对：所有原 Transform 世界矩阵未动、Mesh 引用未动、碰撞序列化状态未动、仅明确槽改变、所有旧材质序列化内容未动、恰好三个 Renderer、无 emission；保存可回退的前后 GUID。

需要主代理完成的实际验证：

1. 检查 HLSL 导入错误和 Windows/WebGL2 变体；`shader.isSupported` 不替代错误日志和目标平台验证。
2. 同一机位 1440×900，固定时间，先只切换地表材质，对照旧图与候选；先保持灯光/曝光相同，再与草及后期组合。
3. 近看地面细纹是否太尖/太密、沿路走动是否闪烁；检查崖面是否出现三平面轴向接缝、宽条纹或异常高光。
4. 让三盏谜题 Spot 逐个开/关并移动照向，确认草地和路面确实响应附加光与阴影，不只响应 Directional。
5. 以 `_ReliefMeters=0` 和默认值比较轮廓阴影/表面法线；它不应改变可走高度或掩盖网格问题。
6. 回看锚点/灯光射线/角色通行，并采集持续帧时。仅材料校验通过不得写“质感追平”或“60 FPS”。
