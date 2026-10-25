# 铜路灯与港灯离线研究交接

本轮只写 `art/generated/env-v2/lamp-study/` 与 `art/blender/env_v2_lamp_study.py`。未操作 Unity，未修改 Assets、v1 模型、Claude 代码或 CandidateBuilder。故事依据是 07 最终版第 24–26、39–43、95、119、129、155、207–237 行；美术目标是 v2 提示词 A05–A07。

## 当前决定

**c 的表面不推荐接入。** root 实看旧版/c 的路灯夜景后指出：壳体斑纹仍似迷彩或污渍、内罩反射似橙色液体、光果和铜反射罩结构不够清晰。c 模型和证据完整保留。

**当前使用 d 作为离线材质候选。** root 已亲看 d 路灯的中性、亮灯、灭灯三图，确认花斑和熔融反射显著改善，同意把此材质扩展到港灯。仍是简化单颗光芯，不是最终质感达标，也未获主场景导入验收。

d 不改 c 几何：壳体低频色差显著减弱，粗糙度约 .56；内罩粗糙度 .62；玻璃采用 IOR 1.04 的弱折射视觉近似，而非声称真实玻璃物性。没有把不同几何或照明混入这次 c/d 比较。

a 是大块铜锈版本，代理自审拒绝；b 的实心港灯玻璃与悬空提环由 c 修正。a/b/c 都是过程候选，不能据其文件存在推断已被主场景采用。

## 最终离线文件

- [14 张成对图与历史拒绝版本](REVIEW.html)
- 路灯：[FBX](candidate-d/copper_roadlamp/copper_roadlamp_v2_candidate.fbx)、[Blend](candidate-d/copper_roadlamp/copper_roadlamp_v2_candidate.blend)、[实际材质参数](candidate-d/copper_roadlamp/material-specs.json)
- 港灯：[FBX](candidate-d/harbor_lantern/harbor_lantern_v2_candidate.fbx)、[Blend](candidate-d/harbor_lantern/harbor_lantern_v2_candidate.blend)、[实际材质参数](candidate-d/harbor_lantern/material-specs.json)
- [所有最终候选文件的大小与 SHA256](manifest.json)、[7 组成对条件/几何/源文件未改校验](delivery-verification.json)

贴图都在 `candidate-d/textures/`：`Lamp_Copper_Albedo.png`、`Lamp_Copper_Roughness.png`、`Lamp_Copper_Height.png`、`Lamp_Copper_MetallicSmoothness.png`。四图均为 512×512 的 16-bit PNG，已打包进两个 Blend。FBX 导出包含嵌入纹理，但复杂节点映射仍需手工验证，不能仅凭 FBX 内有图认定 URP 已配置。

| 文件 | SHA256 |
|---|---|
| 路灯 FBX | `283f2425476c17fe8660e5bb73eb4bbad15d9ae6d23502e6cb17459783f59f0e` |
| 路灯 Blend | `cbe3a20385af55f0c03d4dc5929db336825cf3ee2ee04fd626c32af0c75178a5` |
| 港灯 FBX | `a74893796f7c937690708edac4a537d079fc3e34eb0f9db010ddcead1fa3c8d8` |
| 港灯 Blend | `e65730fdfffb2dc07fdb20ab7a8f5cb6efde0eeb1bcbf6296a09d55dbe3e4825` |
| Copper Albedo | `b3be9dd8637abc45963800ab40566f5d268d7788e261f0e0ff3a974b52434bb6` |
| Copper Roughness | `818cc1f2e853e97ce33810f64774ab4130dc7668fcc2012cad1b9f1dac7ac8c2` |
| Copper Height | `c449fc055fff63ee2cf2e70a73f50b55073d6b2dcde58eb489930bc7094bba72` |
| Copper MetallicSmoothness | `49f1240c2727a58dac1b0fc6c5bcbd7c532b7e382ac19f41d4122c40e73694d8` |

生成脚本是 `art/blender/env_v2_lamp_study.py`，最终脚本哈希在 manifest。`--audit` 盘点旧源；`--build copper_roadlamp` / `--build harbor_lantern` 生成当前 d；`--verify` 新进程回导 FBX/重开 Blend；`--finalize` 汇总校验与审查页。程序不会复刻 a/b/c 旧材质；旧过程文件单独保留。

## 已做出的几何及表面

| 资产 | v1 三角面 | 候选三角面 | 增量 | 几何改变 |
|---|---:|---:|---:|---|
| 每盏铜路灯 | 606 | 830 | 224 | 原柱/灯罩所有点与面保留；在灯头内加入一颗独立材质光果 |
| 三盏铜路灯合计 | 1818 | 2490 | **672** | 低于本轮三灯合计增面 1000 限制 |
| 港灯 c/d | 436 | 788 | 352 | 原全部点保留；玻璃两端整面改为 2.5 mm 薄壁环，加入内壁；加入单光果、细果柄、提环两端连接件 |

灯头从 258 变为 482 三角面，柱体仍 348。路灯仍是 `Structure` 与 `LampHead` 两个 Mesh；港灯仍是 `Structure` 一个 Mesh。所有装饰合入原 Mesh，没有额外 Renderer、Light 或 Collider。两个资产的所有原对象父子关系、局部/世界矩阵、轴心、Marker 均保持；港灯原非玻璃面保持。旧 v1 Blend/FBX 的哈希未变。

路灯旧玻璃圆片与港灯旧玻璃筒所在槽现在是**始终可见、永不自发光的玻璃**；光果是新追加的独立材质槽。出厂默认光果自发光 0。默认不亮是等待剧情绑定，**不表示灯具亮灭接口已修好**。

铜纹理是本脚本以固定种子的周期函数生成的自有图：512×512 Albedo、Roughness、Height、MetallicSmoothness；未读、未复用参考游戏资产。金属面 UV0 改为 .42 m 平铺投影；原金属 UV 不再作为保留合同，顶点和光路仍保留。玻璃 UV 保留（港灯新增内壁/环面单独赋 UV）。纹理不是照片，也不是基于真实旧铜扫描。

## 必须保留的 Unity 接口

完整只读证据与源码行号在 [INTERFACE-AUDIT.zh-CN.md](INTERFACE-AUDIT.zh-CN.md)，当前 prefab TRS 快照在 [prefab-contract.json](prefab-contract.json)。

```text
Anchor_Lamp_WanFeng / Anchor_Lamp_YueChuang / Anchor_Lamp_GuiHang
  Structure
    CopperColumn
    ColumnCollision
  LampHead                   转轴，localPosition 0，scale 1
    CopperHood               视觉网格
    Spot                     localPosition (0,0,.29)，沿 +Z 出光

Props/HarborLantern
  LOD0
    Structure
    Marker_HangingPoint
  HarborLight                原 Point；不增加第四个 Spot
```

现有 `CopperHood`/`CopperColumn` 已带 FBX 轴转换（约 X=-90°，负 X 比例）；不能再次盲目旋转/反射，更不能对 LampHead 旋转补偿。视觉替换应在验证导入模型基准后保留原三灯 wrapper、Spot、Collider 与锚点，仅换相应 Mesh/材质。不能直接把新完整 FBX 塞进旧 LampHead 形成重复 LampHead/柱体。

Blender 根为米制 Z-up，前向 -Y；FBX 按 Y-up/-Z 导出。源路灯 `Marker_Bulb`=(0,-.285,0)、`Marker_Base`=(0,0,-3.8)。这两个 Marker **存在源资产，但已被旧 Builder 从 Island 实例丢弃**，不能把它们当成当前主场景的必有接口。实际 Spot 是原灯头直接子级，位置与前向一律保持。

港灯原 `Marker_HangingPoint`=(0,0,.79)；根/包围盒不变。真实 Island 港灯根约 (10,3.46,-10.5)，挂点约 (10,4.25,-10.5)，与 Hook 匹配；这是已保存 prefab 的离线复算，不是本轮实机操作。不要用 Marker 的 forward 覆盖 Hook 朝向。

## Claude 需要处理的真实代码缺口

1. `LampPost.cs:29–38` 已复用真实 Head/Spot，但 `bulb` 唯一赋值在灰盒函数第 79 行；第 155 行无法控制真实灯头材质。新模型有光果槽，也不会自动绑定。
2. `MaterialKit.cs:67–71` 使用 `r.material`，只改 slot 0。原真实光芯是 slot 1，新光果是 slot 3；把整灯 Renderer 赋给 bulb 仍会改错铜材质。应针对每实例、明确材质槽控制，可用 per-material MPB 或独立实例材质。不要改共享材质导致三灯和港灯串联。
3. `GameDirector.cs:87–89` 只缓存港灯 Light；`SetHarborLamp` 第 884–889 行只改 active 与 Light 强度。第 477 行 `true,0` 保留灯体但没有关闭旧发光玻璃。新港灯必须同时将光果 emission 置 0，保留玻璃和框架 Renderer；直到后续明确隐藏剧情才隐藏整个对象。
4. 原港灯 Point 初始强度 1.2、range 3.5、无阴影，供 Boot 缓存。候选只默认材质 emission 0，**不要求把这个 Point 初始强度改为 0**。

这些是当前磁盘源码的确定控制缺口；尚未在 Unity 复现最终画面的残亮程度。本轮没有修改这些代码。

## 材质槽和映射

| Mesh | 顺序 |
|---|---|
| 路灯 Structure | 0 `V2_Lamp_AgedCopper`，1 `V2_Lamp_RubbedCopper` |
| 路灯 LampHead | 0 `V2_Lamp_AgedCopper`，1 `V2_Lamp_AmberGlass_AlwaysVisible`，2 `V2_Lamp_RubbedCopper`，3 `V2_Lamp_LightFruit_Controlled` |
| 港灯 Structure | 0 `V2_Lamp_WeatheredIron`，1 `V2_Lamp_AmberGlass_AlwaysVisible`，2 `V2_Lamp_AgedCopper`，3 `V2_Lamp_LightFruit_Controlled` |

槽名仍应在实际导入后核对；不要仅依赖序号，也不要给整个 Renderer 赋一个 `.material` 覆盖多槽。

d 的实际参数（颜色为 Blender 线性 RGB）：

| 材质 | Base Color / 纹理 | Metallic | Roughness | 其他 |
|---|---|---:|---:|---|
| AgedCopper | Albedo 贴图，以 (.34,.18,.074) 为底，低频仅微弱差异 | 贴图约 .62 | 贴图 .53–.59，中心 .56 | Height bump strength .06、distance .00015 m |
| RubbedCopper | (.48,.29,.12) | .58 | .62 | 无 bump；兼用于内反射罩、转轴盖、柱箍 |
| WeatheredIron | (.067,.083,.080) | .58 | .53 | 无 emission |
| AmberGlass_AlwaysVisible | (.98,.965,.94) | 0 | .06 | Transmission=1，IOR=1.04，Coat=.04、Coat roughness=.20，emission 永远 0 |
| LightFruit_Controlled | (.95,.47,.085) | 0 | .34 | SSS=.06、scale .02m；Emission 色 (1,.43,.085)，默认 strength 0，展示亮态 2.2 |

玻璃在 Blender 里以弱折射透射渲染，保持 Alpha=1；它既不是不透明白塑料，也不是把整个灯头 alpha 降低。移到 URP 时只给玻璃槽设置透明策略；使用不折射的清澈薄盖近似是允许的候选方向，具体 opacity/高光/排序必须在 Unity 里验证。铜、铁、光果保持不透明，不随玻璃一起透明。面数/粗糙度报告不能代替这一项实际材质映射。

Albedo 用 sRGB。Roughness、Height 和 MetallicSmoothness 用线性数据；MetallicSmoothness 的 R 为金属度、A 为 **1−roughness**。Height 是高度数据，不是 Unity 切线法线贴图，不能直接当 Normal Map 接。Blender 的玻璃 Transmission、IOR、SSS 与复杂节点并不会自动成为 URP 同效果材质；需显式建 URP 材质并实测。透明玻璃的 ShadowCaster、排序、背面和反射仍未验证，不能靠把整个铜罩阴影关闭来掩盖问题。

在 3 个灯头和 1 个港灯各增加一个材质槽，理论上可增加 4 个 submesh 提交；实际 draw call/合批/透明 overdraw 未测。当前 4 张 512² 图未压缩 RGBA8 含 mip 约 5.33 MiB，共享后无需每灯一套；最终内存取决于 Unity importer 格式。没有添加实时灯，不能据面数推断 Iris Xe 的帧率。

## 对照图和验证的含义

每资产旧/新图为同镜头、同分辨率 900×900、同曝光、同三盏棚拍 Area Light。Cycles CPU 40 samples，AgX Medium High Contrast，无 Bloom、无后期修图。中性与熄灯图将全部 emission 设 0；亮灯图旧芯与新光果同设 Blender emission 2.2，但发光面积不同，**不是等流明实验**。

没有加入真实游戏 Spot/Point、没有雾或光锥。这些是离线材质/模型展示，不是主场景截图，也不是灯照小路/长椅/圆窗/码头的验收。旧版的 off 图人为将旧发光材质设 0，不能把它当成当前游戏 `SetHarborLamp(true,0)` 已能达到的画面。

d 已通过 fresh-process FBX 回导：面数、材质槽、原对象父子关系与矩阵；UV0 最大差 0；路灯世界点误差最大 6.26e-7 m，港灯 1.29e-7 m；Blend 重开确认所有四张图已打包、0 Camera/Light、光果及玻璃默认 emission 0。d 港灯无边界/非流形/退化面。路灯头继承旧罩内端的 16 条边界边，没有把它虚称为封闭 watertight Mesh；灯头不作碰撞。

d 与 c 原/新增顶点逐值相同、有向面加材质槽的集合相同、矩阵和包围盒相同；新光果的 96 个 polygon 顺序因独立进程的 primitive 生成而有排列差异，不把它虚称为所有 polygon 索引也相同。两份 FBX 各自与对应 Blend 的 UV 检查均通过。

[d 遮光几何射线](candidate-d/copper_roadlamp/shield-ray-study.json) 从原 Spot 位置发射：半角 13°/39° 各 32 方位全部无遮挡；80°/90°/110°/150°/180°各 32 方位全部被铜罩阻挡。此测试只查几何相交，排除玻璃/光果，不能替代 Unity 单面剔除、阴影 near plane、透明阴影或光度验证。罩子几何未变，宽/窄 26°/78°仍由 Claude 的 Spot 和 Beam 实现；**尚无两套可切换的 A07 实体罩型**。

自审剩余局限：铜的极近景仍沿用低模轮廓；光果是简化单颗暖芯，亮态细节少；港灯 d 的玻璃比 c 清澈许多，夜间玻璃反射/轮廓偏弱。不能用默认不发光或玻璃几乎不可见来替代最终画面验收。

## 接入前验收

- root 审核材质候选后才考虑视觉替换；仍需 Unity 独立场景检查轴转换、三灯 Spot 数量、原碰撞/挂点保持。
- Claude 完成每灯每槽独立亮灭后，验证满亮、半亮、熄灭、再次点亮；港灯熄灭时玻璃/框架保留、最后隐藏时才全隐藏。
- 按三章实际所有指向测试，Head/Spot/Beam 跟随，柱不旋转；78°/26°光路不被新果子/玻璃挡住，不出现串灯或额外 Spot。
- 用近景与正常玩法镜头核对金属高光、玻璃排序、光果大小、夜晚可读性。没有任何 Unity/WebGL/性能通过结论。

尚未完整实现 A05 新石墩/操纵手柄、A06 四面灯笼框架和顶部拱盖、A07 两个可切换罩型。本轮是保留旧光路与轴心的受控材质/光芯候选，不能宣布整套灯具美术目标已完成。
