# 环境 v2 实施审计：基于本地画面与实际 URP 源码

日期：2026-10-22。范围：环境实现的只读审计。本报告只新增本文件，未操作 Unity、未修改实现或其他分工目录。未亲自打开或游玩 littleprince.dev，因而下列判断是对《借光岛》已有证据的分析和改进方案，不是对参考作品的实测结论，也不构成“追平”证明。

## 证据与约束

- 逐张查看 `art/verification/env-v1/01-title.png`、`02-cape.png`、`03-pier.png`、`04-village.png`，均为 1440×900。这些是独立 EnvTest，不含实际人物、UI 或各章剧情状态。
- 已读最新质感优化提示词、第二版素材方向、唯一故事 07、v1 HANDOFF、Environment 的 Builder/PathConformer/Shaders，以及只读的 GameDirector、NightSky。
- 原始 v1 已验证最高 LOD 380,368 面，含备用 LOD 506,767 面；168 个 Renderer、51 材质、35 LODGroup。它们不等于运行时绘制量或 draw calls。
- 新素材约定目录 `C:/Users/20665/Downloads/借光岛_v2模型` 在本次检查时不存在；不能声称 v2 Tripo 模型已收到或已接入。
- `Packages/manifest.json` 声明 URP 17.0.1，但实际 `Library/PackageCache/com.unity.render-pipelines.universal@746735fb06f2/package.json` 为 **17.3.0 / Unity 6000.3**，依赖 Core 17.3.0。实现应以本地实际头文件为依据，不凭 manifest 推断编译 API；不改 Packages。
- 所有锚点世界位置、朝向、LampHead 转轴契约、房屋真实门窗开口和现有碰撞保持不变。暖琥珀色实灯、冷蓝环境色、细弧蓝白地球、长夜世界观不可为了画面改成日间。

## 已观察的具体问题

| 严重性 | 本地证据 | 现象及影响 | 环境内解决办法 |
|---|---|---|---|
| P0 | 四张图，尤以岬角/码头 | 大面积地面由均匀橄榄色块组成，无草根、落叶、低矮植被，石板像放在地面上的整齐薄片；低角度缺少前景尺度 | 先做地表中频混合和石板边缘接地，再铺有疏密的风草与花簇；不靠整体提亮掩盖 |
| P0 | 岬角前缘、村子内湾崖面 | 崖面大块长直折线，前缘可见黑色竖缝；远景像截断的多边形地台 | 首先查接缝是否为重复/反向面或边界开口，修真正问题；对非行走崖面细分与岩层塑形，保留顶面和锚点，不能用草遮洞 |
| P0 | 码头近景中央木屋 | 背墙呈近黑的大矩形，屋顶方格重复；主视觉材质像原色积木，夜晚建筑细节丢失 | 用低频蓝灰环境反射显出暗部，木纹、板缝、边角形成层次；曝光提升要和发光亮度一起测，避免果实过曝 |
| P0 | 全部画面 | 果实和窗可见但缺少柔软光晕，近岸与远海层次弱 | 测试相机开启 HDR + 后期；以温和 Bloom、色调映射和有距离梯度的空气色完成层次 |
| P1 | 岬角/村子树冠 | 叶片偏褐、橙，银绿色辨识不足；树干和根的细节很密，地面却极简，材质密度失衡 | 调整叶槽色相、粗糙度和有节制的透光；保留果实独立发光；优先改善英雄金树轮廓，普通树用 LOD |
| P1 | 海面四图 | 水面同向长条纹非常规则，没有清楚的近岸变化、码头倒影或浪痕，地面与海面像硬拼 | 用两组低幅不同方向波形、视角菲涅耳、柔和灯光反射和岸边湿色带；避免昂贵全屏反射 |
| P1 | 村子 | 房屋同形同高度、窗是亮方块，缺少窗框厚度和生活痕迹 | 不移动窗的可控子物体；墙板/檐口/窗框/小件增加非碰撞细节，有限变化屋面色，保留原布局 |
| P1 | 地球、海平线 | 地球暗面有程序条纹，轮廓像贴花；天空干净但空，缺少远近层 | 地球暗面压低、少量不规则低频云形；稀疏透明度低的远云和海雾色，不让云遮掉谜题星空 |
| P2 | 码头图下缘 | 船下部被截，部分机位地球被裁掉 | 测试机位另加材质近景；同机位 A/B 不可暗改相机。正式镜头由 Claude 改 |

这些截图无法证明角色脚贴地、动画、UI、完整路线通行、章节光污染切换、FPS 或 WebGL 兼容。对应验证应单独进行。

## 保护接口的改造方法

1. 从已验证的 Island.prefab 读取并保存锚点的路径、位置、旋转、缩放快照，新增环境装饰作为独立子层级。应用后逐项比较，位置误差限 0.001m、旋转误差限 0.01°；除明确另议，不改变任何坐点或目标点。
2. 地表材质/草/小石只是视觉层。Layer 8 地面和栈桥、Layer 9 现有墙岩碰撞保留；新草、花、装饰落叶不加 Collider、不阻挡灯光目标射线。
3. 草和细节位置使用**实际修正后地形 MeshCollider**的射线，不能复用未经 Unity X 反射修正的 FBX 包围盒。现有正确世界中心与村子方位不得再翻转。
4. 新房屋到货后对外观 Renderers 做替换，窗/门/座点三个固定测量标记必须对齐；不能为凑房屋尺度移动 `Target_Window`、`NPC_ABo_Window`、`NPC_ABo_Door`。若新模型无法保持真实洞口，必须重新切割模型。
5. 三盏灯只更换灯柱/灯头视觉网格，灯头模型零点对齐原转轴、+Z 为出光方向，保留同一 Spot 和参数接口；不能新增不可控“装饰灯”冒充谜题照明。
6. `Village_Windows` 22 个子窗仍逐一独立；静态合批仅合不需独立控制的建筑主体。`ReturningBoat` 根、`HarborLantern/HarborLight` 不改名字及父子契约。

## 推荐实施顺序与初始参数

下面数值是可测的首轮候选值，不是参考作品实测值或最终定值。每组只改变一个主要因素，保持四机位、1440×900、同一章状态，并记录 HDR/后期/灯光/环境色/时间的实际状态。

### 1. 修好画面基础：地面、崖壁、材质尺度

- 用 3–6m 的缓慢苔藓/土壤色变化、0.25–0.8m 的颗粒/浅斑两层分开调，避免满屏均匀噪点。颜色保持暗鼠尾草绿、灰褐土而不是白天鲜绿；粗糙度 0.85–0.95、法线强度候选 0.20–0.35。
- 地面保留当前高度；道路仍用既有贴地派生网格。石板材质以世界尺寸约 0.8–1.2m 对齐纹理，可少量做破角、2–4cm 倒角/厚边；沿边用 5–15cm 的泥/苔色过渡。新增可碰撞台阶需另测，不在本阶段引入。
- 崖壁只细分非行走面，层状裂纹为主，岩块形体为辅；几何增量先限 12k 面。不同片区色差不超过约 15%，减少当前岩石橙色与崖壁深灰的断层感。
- 木纹方向沿木板长轴，主纹尺度 8–20cm，微纹只在近景看得见；木材 metallic=0，roughness 0.65–0.85，避免把整块屋墙变成反光塑料。倒角/板端是主要质感，不靠过强黑色缝线。
- 旧铜 metallic=0.65–0.85，roughness 0.35–0.55；铜锈区降低金属度，颜色偏灰青，不要只在均匀橙色上降低粗糙度。按槽独立控制发光玻璃与金属，玻璃面不能发光带亮铜框。
- 新素材未到前可做程序化原创建模/材质，明确标记为程序资产。若需要生成位图，走项目图像工具/技能，不从参考作品抽取。

### 2. 草地与花：在可读性和预算内建立真实层次

**建议首版是分块合并的弯曲草叶网格 + 顶点风**，不依赖 Geometry Shader、Compute Shader、Indirect Draw；这样无需改管线/Packages，更易覆盖 WebGL。GPU Instancing 可作为后续已经测过的优化，不能用 `enableInstancing=true` 就声称已实例化或已提升性能。

| 项 | 首轮候选 |
|---|---|
| 区域 | 村坡、树林空隙、岬角边缘；海拔低于岸线、坡度 >38°、道路/屋/台面/座位区域排除 |
| 密度 | 开阔处 3–7 簇/m²，重点路缘 8–12 簇/m²，裸土区 0–1；用低频簇状分布，不用均匀撒点 |
| 几何 | 每簇 6 片弯草，每片 2 三角面；LOD0 总簇上限 4,000 → 48k 面，LOD1 约 1/3 → 16k 面 |
| 高度 | 主草 0.12–0.32m；路边短草 0.05–0.12m；偶有 0.35–0.45m 的高草，仅约 5% |
| 颜色 | 深根到较浅银绿尖，簇间亮度 ±12%、轻微暖灰/蓝灰变化；禁止发光青草 |
| 分块 | 6–8m 方块，每块局部 AABB，避免全岛合一块让所有草一直绘制；每块最大风幅扩边至少 0.12m |
| LOD / 远裁 | 0–12m 完整，12–24m 约 1/3，24–32m 平滑稀疏，32m 后裁除；标题视角保留地表颜色层，不靠远处单草 |
| 路沿 | 石板实际轮廓内排除，边缘 0.15–0.30m 带用短草，保持至少约 1.2m 的清晰可走路面 |
| 野花 | 4–8 朵一小簇，花径 0.03–0.08m，奶白/淡黄/少量浅紫；数量先限 150–250 朵，不平均铺满所有草区 |
| 阴影 | 草先 receive shadows=true、cast shadows=false；近景少量大叶可单独测开启，不能使所有小草进入 3 盏 Spot 的阴影图 |

风的顶点位移候选：用世界 XZ 与固定簇 seed 决定相位，两个不同周期的正弦叠加；低频 0.18–0.35Hz，高频 0.6–0.9Hz，叶尖水平幅度 0.02–0.07m；乘 `height01²` 锁住根。每簇方向略不同，主风向一致，避免所有叶尖同时摇同一角度。导出后由 uv.y/vertex color 保存根到尖权重，不能拿全岛世界高度当权重。

每帧 CPU 只更新时间/风参数，不重建网格、不分配矩阵列表；固定随机种子便于 A/B。新增 `_EnvTimeOverride` 或等价参数可在截图中冻结风与波纹，使同机位比较可复现。近处草叶和远处地色的交接要同时检查静止画面与 10 秒移动录像，防止闪烁/骤隐。

### 3. 灯光、天空和海面

- 现有场景两盏暖 Directional 分别 0.6 / 0.25。先保持位置与强度获取新地面基线，再降低第二盏对墙面的均匀照射；冷蓝来自环境光/天空反射，暖实灯构成视觉焦点，不增加第四盏谜题 Spot。
- 本地原画叶片变成褐橙且天空极黑，不能单靠暖主光继续加亮。建议试验环境 sky=(0.09,0.13,0.21)、equator=(0.045,0.065,0.10)、ground=(0.02,0.025,0.035)，并保持灯罩/果实暖色；实际值必须与 ColorSpace/HDR 状态一起记录。
- 天空只加低对比、缓慢移动的薄云层，不能常亮遮星。远海渐变色与天空 horizon 使用同一参数；海雾首先用材质距离混合，不开高成本体积雾。
- 水面波形改为 2 个不同方向、波长约 2.5m 和 7m 的低幅扰动，消除当前斜长条重复；岸边用静态距离纹理或离线边界距离建立 0.4–1.2m 的湿色/浅浪，不依赖全屏 depth 采样才可显示。
- 光在水上的反射用有限、很柔的暖色拉伸斑，不画清晰实体镜面倒影；全部仍服从剧情关灯。纹理/参数应是原创，不复制参考星球或云。
- 主线当前仍生成单独 `NightSky`，它的 `LateUpdate` 每帧写 ambient/fog。v2 若也写全局环境色会互相覆盖。环境交付章节参数数据，**最终让 Claude 在唯一剧情入口应用**；不能用两个 Update 抢写 RenderSettings。
- EnvTest 能独立显示的天空保留，但主线只启用一套天空/地球。海面的 `_Horizon` 已有，可随污染度同步；现有海面 Shader 未走通用 Fog，因此只改 RenderSettings.fogColor 不会自动改变海面远处颜色。

### 4. 独立 Volume Profiles 与真实生效检查

现有 `EnvV1Builder.ConfigureCamera` 设置 `camera.allowHDR=false`，且没有启用 `UniversalAdditionalCameraData.renderPostProcessing`。因此**只创建 Profile 文件不算完成后期**。Environment 自有测试相机可改为 HDR 并启用后期；主游戏相机由 Claude 接入。不得改 `Assets/Settings` 或 ProjectSettings 来偷偷获得对比优势。

建议 `Environment/Profiles/` 中创建序章/长夜/天亮前 3 个 Profile，以长夜作为基础，各章灯光与天空参数另存数据。值为首轮候选：

| 项 | 长夜基础 | 序章 | 天亮前 |
|---|---|---|---|
| Tonemapping | Neutral；可单独比较 ACES 是否过度压黄 | 同 | 同 |
| Post exposure | +0.15 EV | +0.25 EV | +0.35 EV |
| Contrast / saturation | +5 / -4 | +3 / -3 | +2 / -2 |
| Bloom threshold / intensity / scatter | 1.0 / 0.18 / 0.60 | 1.0 / 0.16 / 0.60 | 1.0 / 0.14 / 0.58 |
| Bloom iterations / quality | 4 / 低过滤起步，half | 同 | 同 |
| Vignette intensity / smoothness | 0.10 / 0.45 | 0.08 / 0.45 | 0.06 / 0.45 |
| Film grain | 关闭，保留组件参数供特写启用，最高 0.025 | 同 | 同 |
| DOF | 实机关闭；标题/固定特写单独试 Gaussian，start=18m/end=40m/radius=0.7 | 按镜头 | 按镜头 |

强景深不得遮掉谜题目标、字幕、进路障碍；景深只是可选镜头效果，不是地面/模型细节不足的遮挡。天亮前仅增浅冷环境色，不能出现太阳或明亮白昼。

## 已核实的本地 API 和 Shader 注意事项

版本源根：`GameProject/Library/PackageCache/com.unity.render-pipelines.universal@746735fb06f2/`，以下均来自本地实际源码。

1. `Runtime/UniversalAdditionalCameraData.cs`：扩展 `camera.GetUniversalAdditionalCameraData()` 存在（约182行）；`requiresDepthTexture`、`volumeLayerMask`、`volumeTrigger`、`renderPostProcessing` 均可设置。只改测试相机时检查它是否已包含对应组件，避免反复新增。
2. Core `Runtime/Volume/VolumeProfile.cs`：`profile.Add<T>(bool overrides=false)` 和 `TryGet<T>(out T)` 存在；新建持久 Profile 时必须把 VolumeComponents 存成对应资产的子资产，不能只 `CreateInstance` 后丢在内存。Volume 支持 `isGlobal`、`priority`、`sharedProfile`。参数 overrideState 必须开，且相机 mask 包含该 Volume 所在层。
3. `Runtime/Overrides/` 里有 `Tonemapping.mode`、`ColorAdjustments.postExposure/contrast/saturation`、`Bloom.threshold/intensity/scatter/clamp/downscale/maxIterations/highQualityFiltering`、`Vignette.intensity/smoothness`、`FilmGrain.intensity/response`、`DepthOfField.mode/gaussianStart/gaussianEnd/gaussianMaxRadius/highQualitySampling`。不要用 HDRP 的体积雾/曝光组件名代替 URP。
4. `Shaders/Lit.shader` 当前用 `#pragma multi_compile _ _CLUSTER_LIGHT_LOOP`，`ShaderLibrary/RealtimeLights.hlsl` 的实现为 **`USE_CLUSTER_LIGHT_LOOP`**。仅拷旧 `_FORWARD_PLUS` 样例容易在当前 Forward+ 下漏掉附加灯。草、地面不能只取 GetMainLight，因为谜题核心是 3 个附加 Spot。
5. 优先复用 `ShaderLibrary/Lighting.hlsl` 的 `UniversalFragmentPBR(InputData, SurfaceData)` 或按本地实际 LIGHT_LOOP_BEGIN/END 实现，填写 `InputData.positionWS`、`normalWS`、`viewDirectionWS`、`shadowCoord`、`bakedGI`、`normalizedScreenSpaceUV` 等完整数据；支持主光/附加光阴影与 fog。不能只开 multi_compile 却不调用阴影衰减。
6. `ShaderLibrary/LODCrossFade.hlsl` 的函数是 `LODFadeCrossFade(float4 positionCS)`，读取 `_DitheringTexture` 与 `unity_LODFade.x`；标准 Lit 在 Forward/Depth/Shadow pass 中编译 `LOD_FADE_CROSSFADE`。如果采用 LODGroup CrossFade，自定义草的相应 Pass 都需要一致支持，且 WebGL 需要实际验证全局抖动纹理/变体未被剥离。
7. `Shaders/ShadowCasterPass.hlsl` 会根据 `_CASTING_PUNCTUAL_LIGHT_SHADOW` 选 `_LightPosition` 或 `_LightDirection`，再调用 `ApplyShadowBias`、`ApplyShadowClamping`。不能将额外点/聚光灯阴影简单按 Directional 方向计算。
8. 所有风变形必须共享同一个函数用于 Forward、DepthOnly、DepthNormals（若 SSAO/景深需要）、ShadowCaster（若开启）。直接 `UsePass` 标准 Lit 阴影会留下静止影子；只有 Forward 顶点风会导致深度/草叶分离。草默认不投影仍应提供一致的 Depth Pass。
9. `Shaders/Lit.shader` 有 `multi_compile_instancing`，实例化输入传递要有 `UNITY_SETUP_INSTANCE_ID` 等宏；材料数据放 UnityPerMaterial CBUFFER。静态批处理把网格烘为世界空间时，不应依赖原模型物体中心做随机风相位。
10. 本地 PC_RPAsset 写有 HDR=1、MSAA=2、renderScale=1、附加灯阴影支持、shadowDistance=50；Mobile_RPAsset 是 renderScale=0.8、无附加灯阴影。**这些是磁盘资产值，不证明当前或 WebGL 实际选了哪套**，须在验证中记录 `GraphicsSettings.currentRenderPipeline`、当前质量等级和相机状态。该审计未操作 Editor，也未确认运行时选择。

## 性能预算和回归门槛

- 不把 60 FPS 当成已有结果。以 1440×900、完整实际视口为条件记录平均/中位/P95 帧时，并至少覆盖岬角密草、树林、村子、码头、三灯全开和第三章人群光点；至少 60 秒持续样本，热身后计时。Editor 静态 RenderTexture 耗时不能代替游戏帧率。
- 首轮新增几何预算：草 LOD0 48k + LOD1 16k、花/装饰 ≤5k、崖壁修复增量 ≤12k，共 ≤81k。在旧总量 506,767 面上约 ≤587,767 面；LOD0 约 ≤445,368 面。实际删除/新增必须重算，不把这个预算表当测量。
- 草块可见提交目标 ≤30，主要草材质 1 个、花材质 1 个；不要为每簇创建 GameObject/Material。当前 51 材质先不增加到数百，木/石/铜使用少量共享材质变体。
- 新增常驻贴图初始限 3 张 1024（地表、木、石/铜复用方案）和必要小图；用正确 mip/sRGB/NormalMap，记录实际导入压缩尺寸。不能仅用源 PNG 文件大小估 GPU 内存。
- 便携质量档先不启实时反射、体积云、屏幕空间反射、全部小草阴影、运动模糊。任何效果若显著增加 P95 帧时，按草可见范围、阴影、后期顺序逐项 A/B 定位，不能一次全关得出无归因结论。
- 每次应用后验证锚点快照、13 个原地面采样、五条原灯目标射线、3 灯与 22 窗的数量及层级；新增草不应使采样命中装饰物。
- 对照图按同机位原始 PNG 展示，所有不同设置写入 manifest。冻结风/海时间；暴露和泛光影响截图时，允许并列提供“相同曝光”和“完成调色”两组，不静默把较暗前图与较亮后图当几何进步。

## 给父任务的优先落地建议

第一轮：建立运行前锚点/参数快照 → 地面/崖壁视觉与边界修复 → 地表材质 → 风草/花簇 → 自有测试相机 HDR + 明确生效的轻后期 → 四机位 A/B 与移动录像。第二轮：木/铜/窗框材质 → 金树轮廓/叶色 → 海岸过渡/薄云/章节参数 → 接收新模型逐件替换。每一轮输出实际差异和未验证项。

Claude 负责的必要接入项：唯一 NightSky/环境色控制权、主相机 HDR/后期和镜头景深开关、章节 Profile 切换、港灯 Point 与玻璃发光同步、游戏实际性能采样、人物相机/轮廓光协调。此审计只指出接口，不修改那些实现，也不声称对方已采纳。
