# A04 第一朵花 · 离线资产交接

当前推荐 **candidate-c**，可进入 Unity 单体导入与真实镜头验证。它用于由 Claude 替换 `GameDirector.EnsureFlower()` 的球体；本轮没有导入 Unity、挂接金树、接入剧情或修改已有锚点。根代理已实际查看开放、侧面、闭合、夜景四张图，认可其作为第一轮独立模型候选，尚非正式场景验收。

设计依据是唯一故事 `07_完整故事与生图提示词（最终版）.md:261` 的“最低的一根斜枝上，开出了第一朵花”和 v2 美术提示 A04。全部网格与花瓣渐变贴图均为原创程序化制作，没有借用对标游戏资产。

## 最终文件

- [推荐 FBX](candidate-c/first_flower_A04.fbx)
- [可编辑 Blend](candidate-c/first_flower_A04.blend)
- [原创花瓣颜色贴图](candidate-c/A04_petal_albedo.png)，256×128；Blend 内另有打包副本。FBX 同目录 `first_flower_A04.fbm/` 保存导出的贴图副本。
- [可复现脚本](../../../blender/env_v2_first_flower.py)
- [几何与灯光报告](candidate-c/asset-report.json)、[FBX 新进程往返报告](candidate-c/fbx-roundtrip.json)、[Blend 新进程重开报告](candidate-c/blend-reopen.json)、[9 个插值采样检查](candidate-c/morph-interpolation-audit.json)
- [本地预览页](REVIEW.html)、[交付清单与哈希](manifest.json)

`candidate-a` 保留首轮偏平、光照过强与花苞顶口问题；`candidate-b` 保留花瓣根部交叉造成“小内瓣”错觉的问题。两者是历史记录，不推荐导入。c 收窄花瓣根部，增加圆润边缘采样、花瓣弧度，合拢花苞，并让两片叶子在主机位均可见。

## 模型与接口

| 项 | 已交付值 |
|---|---|
| 三角面 / 顶点 | **1,968 / 1,010**，所有形态相同；低于 2,000 上限 |
| 花冠 | 6 片有闭合厚度的奶油白浅金花瓣，细金边；开放时花冠平面最大直径 **0.250 m** |
| 花心 / 枝叶 | 单个小琥珀花心、弯曲短斜枝、两片银绿叶；没有花球堆叠 |
| 网格与材质 | 单 Mesh，5 个独立材质槽；内有 13 个分别封闭的部件，枝叶接合处有正常的几何重叠 |
| 米制 / 导出 | Blender Metric，scale_length=1；FBX `axis_forward=-Z, axis_up=Y`、单位换算开启，无额外全局缩放 |
| 根物体 | `FirstFlower_A04`，位置/旋转为零，比例 1；枝根切面中心为原点 |
| 网格物体 | `FirstFlower_Geometry`；有 BlendShape 的网格预期由 Unity 作为 SkinnedMeshRenderer 使用，尚未实机验证 |
| 附着接口 | `Marker_AttachRoot` 位于局部 `(0,0,0)`，没有指定世界坐标或任何金树锚点 |
| 镜头接口 | `Marker_BloomCenter`；Blender 局部 `(0.047,0.008,0.181)`，局部 +Z 朝向花冠法线；导入后直接使用其 Transform，不硬编码转换坐标 |
| 原始花冠法线 | Blender 局部约 `(0.25008,-0.17005,0.95330)`；以标记实际旋转为准 |
| 默认状态 | 闭合花苞；不发光、没有 Light 或 Collider，没有运行时脚本 |

原点是倾斜枝根的切面中心，不是 AABB 最低点。切面边缘最低约为 Blender z=-0.000859 m，不能把这不到 1 mm 的斜切面当悬空错误再自动挪轴心。整个开放件包围盒约 x `[-.082,.1794]`、y `[-.1185,.1144]`、z `[-.00086,.2686]` m；闭合花苞最高约 `.2983 m`。接入后不能再沿用旧球体的 `.22` 缩放，实例根应从比例 1 开始。

## BlendShape 数值合同

Blender Basis 名为 `ClosedBud`；FBX 往返导入会把 Basis 显示为 `Basis`，不作为一个可驱动的增量形态。另两个形态名称是 **`HalfOpen`** 和 **`Open`**。Unity 要启用 BlendShape 导入并在实际导入后检查名称；若导入器添加名称前缀，按后缀定位，不假定固定索引。

| 形态 | HalfOpen 权重（Unity 0–100） | Open 权重（Unity 0–100） |
|---|---:|---:|
| 闭合 | 0 | 0 |
| 半开 | 100 | 0 |
| 完全开放 | 0 | 100 |

设开花进度 `t∈[0,1]`，使用两段插值：

```text
t <= 0.5: HalfOpen = 200*t;       Open = 0
t >  0.5: HalfOpen = 200*(1-t);   Open = 200*t-100
```

两形态都是相对闭合 Basis 的增量，**不要同时设为 100/100**，否则会叠加过度。时间长度由 Claude 的真实剧情镜头决定，本资产没有把截图文件名当作动画时长。叶片、枝条、花心和附着标记保持原位，只展开花瓣。已检查 t=0、.125、.25、.375、.5、.625、.75、.875、1 的几何；这不是动画碰撞或全时段自交的完整证明。

## 材质与夜景说明

| 槽 | 名称 | 内容与 Blender 基准 |
|---:|---|---|
| 0 | `A04_Petals_CreamGold` | 原创浅金至奶油色渐变贴图；Roughness .56，少量 SSS/Transmission，仅 Blender 预览支持 |
| 1 | `A04_FineGoldEdges` | 花瓣/叶缘的细金边；Roughness .48、Metallic .16 |
| 2 | `A04_SingleAmberHeart` | 唯一琥珀心；Roughness .30、Metallic .02；交付文件发光强度为 0 |
| 3 | `A04_Twig_WarmBrown` | 枝条；Roughness .84 |
| 4 | `A04_Leaves_SilverGreen` | 叶与花托；Roughness .67 |

建议 Unity 先使用不透明 URP 材质，保留金边与厚度。Blender 的 SSS/Transmission 不等于 URP/Lit 已自动复现，不能靠降低整片 Alpha 让花瓣透明消失。若用 URP Smoothness，起点可取 `1-Roughness`，但最终光泽以实际夜岛机位校准。不得继续用 `Renderer.material = ...` 把单个发光材质覆盖全部 5 槽。

中性/夜景为同一 900×900 正交机位、同一曝光、同一开放形态的真实 Cycles 渲染，无后制拼图或 Bloom。中性图花不自发光；夜景只改变已记录的环境/区域灯，并让琥珀心 emission=2.0。**这不是已接入游戏的发光效果**。交付 FBX/Blend 保持中性无自发光，Claude 在实际终章可单独调整槽 2。不要未经镜头检查就复用旧球体范围 2.5 m、强度 1.5 的 Point，否则一朵小花会变成场景主灯。

## Claude 接入时要改的地方

1. `GameDirector.cs:823–839`：将 CreatePrimitive(Sphere) 换成独立花实例；保留上述材质槽与根比例 1，移除旧 `.22` 缩放与整球统一材质写法。
2. **先在真实金树模型上选择最低斜枝的可见连接点**，核对正/侧镜头后将 `Marker_AttachRoot` 接到该点，避开悬空或穿透大树皮。现有 `Toward(tree.position,...1.2f,2.1f...)` 只是旧代码推测位置，不能直接作为本资产已验证的落点。本轮不提供伪造的世界坐标，不改 `Anchor_GoldenTree`。
3. `GameDirector.cs:532–537`：终章可从闭合播放到开放；该镜头原来瞄准 `flower.position`，新根是枝根，应改为瞄准 `Marker_BloomCenter.position`，防止特写盯着枝根。
4. `GameDirector.cs:548–549`：直接跳入尾声时将形态设为开放（0/100）；不要让重新实例化的默认闭合形态留在尾声。Stage 的显隐仍由 Claude 管理，避免重放/回标题残留。
5. 在实际 Unity 导入后检查两个 BlendShape、变形法线、模型比例、5 材质槽、透明设置及 culling bounds。全开/半开/闭合、完整动画与最低斜枝特写都需要实机验证；本轮没有宣称已通过这些检查。

## 已完成验证与保留限制

- 三种主形态：1,968 三角面；全部坐标有限，无退化三角形、开放边或非流形边。各封闭部件在 9 个插值采样中体积方向一致。
- 新进程 FBX 再导入：1 Mesh、3 个 key（含 Basis）、5 材质，三种形态顶点数量和三角面相同；世界顶点最大误差 **5.38×10⁻⁸ m 以下**，UV 最大误差 **0**；两个标记位置误差小于 3×10⁻⁸ m。Unity 导入尚未验证。
- 新进程 Blend 重开：默认两驱动权重均为 0，贴图 256×128、已打包 37,109 字节；只有模型与标记，没有摄影机/灯对象，花心发光为 0。
- 自审及根代理观察认可 c 的 6 瓣、柔弧和真实侧厚，开放图两叶可辨。局限仍有：近看叶缘偏几何，夜景枝叶较暗，小花心轮廓能看到低面数；在真实镜头尺寸下再决定是否投入细化。没有无限增加面数来掩盖未接场景的事实。
- 没有操作 Unity、修改 Assets、Claude 代码或 CandidateBuilder；没有改金树和旧锚点，也没有宣称剧情已接入。

## 关键 SHA256

```text
FBX    df7a825797221681457b9c86350c861b5d32cfd0c80a082216a208fe573ac24d
Blend  e2c28b2283ebc6597dc142a16189d09b452306c48b332c1fb8004e67ecea60aa
PNG    f2cd069cea1787ffc34e57ea021d8cb8705667590e21f8e03a9f0bfdbb209fd6
Script 6f8a47b43d29ef3673b96af7feaea83d23b2fbafe378233aa18db0965b60a858
```
