# 阿婆木屋 v2 木材表面候选

本候选的几何由 `art/blender/env_v2_props.py` 从 v1 原始 blend 非破坏生成。先完成木材 UV 与材质，再按已定位的共面重叠修正新增瓦片/阁楼窗框；未写入 Unity Environment、未替换 Island.prefab、未操作 Unity。

## 文件

- `abode_grandma_v2_candidate.blend`：作者文件。
- `abode_grandma_v2_candidate.fbx`：米制、Y 向上导出；仍需实际 Unity 轴向验证。
- `material-before-front/side/window.png`、`material-after-front/side/window.png`：最新木材表面前后对照，全部 1000×1000，同几何、同机位与同中性棚灯。before 来自冻结的上轮真实 Blender 渲染，after 为本轮重新渲染。
- `before-front/side/window.png`、`after-front/side/window.png`：历史 v1 对 v2 造型变化，after 尚无木纹；不代表最新表面。
- `manifest.json`：源与输出 SHA256、实际面数、包围盒、四个 Marker 前后逐值对照、局部圆窗/入口射线及所有网格 UV 检查。
- `surface-manifest.json`：最新表面检查、164 个木构件 UV 前后范围、纹理信息、材质映射与输出 SHA256。
- `seam-before-front/side/window.png`、`seam-after-front/side/window.png`：最近一次共面黑块修正前后，全部 1000×1000，同机位和棚灯。当前最终外观以 `seam-after-*` 为准。
- `seam-manifest.json`：装饰网格改动的逐顶点清单、诊断面片、七项检查和最终文件 SHA256；`seam-fbx-roundtrip.json` 为最新 FBX 回导检查。
- `SEAM-REVIEW.zh-CN.md`：为什么是共面重叠、改了哪些顶点以及目视结果。
- `REVIEW.html`：木材表面与黑块修正对照页。
- `archive-flat-materials-20261022/`：本轮之前的完整候选文件、脚本与报告，未被覆盖。
- `archive-wood-surface-20261022/`：已完成木纹、尚未修正共面黑块的完整候选。根目录 `surface-*` 报告记录该阶段，其旧 FBX SHA 不表示最新几何；最终以 `seam-manifest.json` 为准。
- `rejected-surface-path-20261022/`：第一轮相对路径失效的紫色渲染与诊断，保留为失败证据；当前版已修复，blend 内嵌纹理。

## 已做的造型工作

旧版大平板屋顶及表面凸线替换为成排错层、有弧度的陶瓦；增加原高度包络内的阁楼外观、小窗、低铁皮烟囱。墙体增加独立旧木板、克制的钉头、石脚、檐下木构和金属门窗小件。保留原来的真正开孔圆窗、敞门、桌椅和本子，四个原 Marker 坐标与方向不变。修补旧门楣左侧窄墙缝。

两次几何收敛去掉了背侧多余倒角和过密的钉头。当前仍为 11,925 个三角面，低于本轮 12,100 上限。木材表面阶段全部几何逐值保持；随后解除共面重叠时只移动新增 `V2_Attic` 和 `V2_OverlappingClayTile` 的 1,672 个顶点，Y 位移 1.5–6 毫米，无新增面。其余 13 网格（包括原 `Structure`）、UV0、四 Marker、包围盒仍逐值保持。

## 最新木材处理

使用原创 `art/generated/env-v2/textures/wood_albedo_v1.png`，实测 1254×1254，sRGB，木纹沿图像 V。没有修改 PNG 像素或使用对标游戏贴图。

旧候选仅使用 Smart Project 打包 UV，本轮对 164 个独立木构件、3,057 个木材面重排 UV。普通板梁按连通块的长轴沿 V，横向墙板水平铺纹，柱和门沿竖向，圆窗框按弧长铺纹。普通构件保持 U 每 1 米、V 每 4.9 米的固定尺度；每块有小幅 UV 取样偏移。全部木材 V 实测落在 0.0454–0.95791，不跨原图上下接缝。为避免长梁跨缝，V 比例略拉长，这是目前的明确取舍。

所有木材只共用一张 albedo，计划在 Unity 使用 4 个独立房屋材质：浅色白洗木、灰旧木、蜜色木、深色梁。粗糙度分别为 0.78、0.82、0.72、0.80，无额外法线、AO 或微表面贴图。Blender 与接入 helper 使用相同色乘子与粗糙度；两种渲染器的最终观感仍需要 Unity 实看。

## 目视结果和限制

已实际查看三张最新候选图。白色墙面从大面积均匀色块变为可辨的顺板木纹；门板、檐梁、圆窗框的纹理方向不同且符合构件走向。前后对照说明木材表面有可见改善，不证明整岛夜景已达到对标游戏质量。

屋瓦、石脚、铜锈与金属仍主要使用颜色材质。木材端面共用普通木纹，尚无真实年轮切面；圆框存在一条 UV 接缝。四处已定位的共面黑方块已经修正，正常檐下接触阴影保留。阁楼只是外观，没有可上楼的室内或楼梯。新阁楼窗使用未点亮的琥珀材质；剧情点亮需要另接控制接口。

## 接入提醒

1. 先在独立环境测试场景验证导入方向和阴影。不要未经检查重复套用 v1 的 FBX 反射补偿。
2. 保留现有屋根、四个 Marker 与 Island 全部剧情锚点。候选外包围未扩大，但仍应复查人物门口、坐点和所有相关相机。
3. `Structure` 保留旧屋和原圆窗/门洞；`V2_*` 为新增细节。建议保持原玩法碰撞，避免给钉头、瓦片逐件生成碰撞。
4. 本地五条射线只检查圆窗和入口正前方，不证明实际三盏灯全部光锥、角色胶囊和运行时镜头已经通过。
5. FBX 材料名称与槽保留，最新合批映射应先使用独立 helper `art/generated/env-v2/staging/Editor/EnvV2HouseSurfaceBuilder.cs`，再走候选导入器原本的屋瓦/石材回退映射。不要修改旧岛共享木材。
6. Helper API：`JieGuang.EnvironmentTools.EnvV2HouseSurfaceBuilder.Prepare(string textureAssetPath, string materialFolder)` 返回源材质名到四个房屋木材的 `Dictionary<string, Material>`。建议贴图路径为 `Assets/JieGuang/Environment/Textures/v2/wood_albedo_v1.png`，材质目录为 `Assets/JieGuang/Environment/Materials/V2/HouseWood`，但本代理没有创建这些 Unity 资源。
7. Helper 仅更新指定贴图 importer（sRGB、Repeat、mipmap、Trilinear、4 倍各向异性、max 2048、NPOT 不缩放），并用 `SaveAssetIfDirty` 保存四个自有材质。`_BaseMap_ST` 保持单位缩放与零偏移；导入/合并网格必须保留本候选 UV0。不创建灯光，不改房屋碰撞和 Marker，不保存场景或别人的 dirty asset。
8. 材质 `V2_WhitewashedWood_0/3`、`Wall_LightTimber` → Weathered；`V2_WhitewashedWood_1/2`、`Wall_WarmIvory` → Whitewashed；`V2_OldTimber_0`、`Wood_DarkBeams` → DarkBeam；`V2_OldTimber_1/2`、`Wood_Honey/Endgrain` → Honey。

## 复现

在仓库根运行 Blender 后台脚本并传 `-- --surface-pass` 可复现木材阶段，它固定从平色归档读取。传 `-- --seam-pass` 可复现当前最终版，它固定从已归档木材候选读取，不叠加位移。没有参数时是历史几何生成流程，会重写当前候选，因此复现当前版本应使用明确的 `--seam-pass`。
