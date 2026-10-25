# 栈桥与长椅：真实 Island 接口审计

2026-10-22，仅只读检查已保存 `GameProject/Assets/JieGuang/Environment/Island.prefab`、v1 构建器、源模型 manifest 和相关剧情源码。没有操作 Unity，没有导入/替换资产，没有编写整合器，没有做碰撞游玩验证。制作代理先出独立候选，是否接入由 root 看图后决定。

## 实际实例与层级

| 资产 | 真实实例数 | 路径 | 原网格 |
|---|---:|---|---:|
| `pier_module` | **3** | `Island/Pier/PierDeck_01`、`02`、`03` | 每段单 `Structure`，456 三角面 |
| `pier_end` | **0** | 没有该资产的实例 | 源资产668三角面，但当前岛未使用 |
| `bench` | **1** | `Island/Props/Bench` | 单 `Structure`，324三角面 |

确认方式是逐个核对 MeshFilter 的 mesh GUID，而非按场景名称猜模型。`pier_end` GUID `e46c0304041391a4b9451bf07fbf3f28` 在整个 prefab 中出现 **0 次**；最末 `PierDeck_03` 仍使用普通 `pier_module`，不要擅自将它换成长3.6m的 pier_end。

```text
Island/Pier/PierDeck_0N
  LOD0                         ← 原FBX轴变换，保持
    Structure                  ← MeshFilter + enabled MeshRenderer；Layer 8
    Marker_Entry               ← 原标记；Layer 8
    Marker_Exit                ← 原标记；Layer 8
  WalkableDeck                 ← 独立 BoxCollider；Layer 8，无网格

Island/Props/Bench
  LOD0                         ← 原FBX轴变换，保持
    Structure                  ← MeshFilter + enabled MeshRenderer + MeshCollider；Layer 9
    Marker_Seat                ← 原标记；Layer 0
```

三段根均 scale1、rotation identity，位置依次为 `(10,2.48,-17.5)`、`(10,2.48,-14.5)`、`(10,2.48,-11.5)`。长椅根为 `(9,2.4,-21)`，rotation identity、scale1。各自 `LOD0` 都有原始 X约-90°旋转、scale `(-1,1,1)`；`Structure` 本地为单位变换。不可为“统一坐标”清空这些原层级变换。

prefab定位：Bench GO第1168行；PierDeck_01第33683行、02第18089行、03第25669行。来源构建逻辑：`EnvV1Builder.cs:738–746` 是桥面Box，`:748–757` 是长椅MeshCollider。

## 桥面碰撞与标记

三段 `WalkableDeck` 都是 enabled、非trigger的 **BoxCollider，不是MeshCollider**。相对根变换为 identity，center `(0,-.1,0)`、size `(2.4,.2,3)`，顶面世界Y=2.48，长向沿世界Z。三个区间分别为 `[-19,-16]`、`[-16,-13]`、`[-13,-10]`，连续无缝；木板视觉缝隙不进入角色碰撞。

| 段 | BoxCollider fileID | Marker_Entry 世界位置 | Marker_Exit 世界位置 |
|---|---|---|---|
| 01 | `5272130622103418426` | (10,2.48,-16) | (10,2.48,-19) |
| 02 | `3673873826428090989` | (10,2.48,-13) | (10,2.48,-16) |
| 03 | `4024413438321902313` | (10,2.48,-10) | (10,2.48,-13) |

以上坐标为实际序列化TRS离线复算的舍入展示；源浮点约有1e-7m误差，整合时保留原对象/值，不根据表内舍入数重建。Entry/Exit名称与方向照原样保存，不按自己的“入桥/出桥”理解互换。

`Island/PierBoundary`（第5157行）以5个点闭合：`(8.8,2.48,-19)`、`(11.2,2.48,-19)`、`(11.2,2.48,-10)`、`(8.8,2.48,-10)`、首点。此边界与三段桥面整体一致，不能因视觉木纹、倒角、桩饰而改动。

其它同区锚点均保持：`Target_Pier=(10,2.48,-16)`、`NPC_AYing=(9.7,2.48,-12.5)`、`NPC_DengBo_Box=(10.65,3.04,-10.8)`、`Anchor_FlagpoleHook=(10,4.25,-10.5)`、`Cam_Pier=(22,8,-11)`。原旋转同样保留，尤其NPC坐向与相机朝向。

实际当前资产已把桩底补到 Blender Z=-3.20m，世界约Y=-.72m；海面Y=-.16m。`env_v1_props.py:425–444`仍是早期生成函数，包含约-1.96m旧桩底描述；当前 `asset.json` 的补深说明与现有blend/FBX才是此次候选应保持的基线。不能从旧函数重生出短桩。

## 长椅碰撞与坐点

`Bench/LOD0/Structure` 的 MeshFilter 和 MeshCollider **同时指向同一旧bench mesh**：GUID `eb87eb5efe6a6fa41b958080400c27de`、fileID `-1542031950021933715`。MeshCollider组件fileID `5300954306759827645`，prefab第19822行；enabled1、isTrigger0、convex0、cookingOptions30、PhysicsMaterial为空。保留此组件本身、所有设置、原sharedMesh引用和祖先变换。

`Marker_Seat` 世界约 `(9,2.85,-20.96)`，与 `NPC_Bench`一致；`Target_Bench=(9,2.85,-21)` 则是另一个瞄准点，不能合并。`EnvV1Builder.cs:608`明确检查Marker_Seat与NPC_Bench位置。坐面为原局部高度.45m，不是角色脚点。

**方向注意**：FBX Marker_Seat 经原-90°X根变换后，`forward`约世界+Y；NPC_Bench原旋转为identity、面向世界+Z。FBX Marker用于位置契约，不能拿它的 `forward`替代人物坐向。保留两者完整世界矩阵；坐向以NPC_Bench为准。

## 视觉替换时保留旧碰撞的判断

可以有条件保留。MeshCollider的 `sharedMesh` 与MeshFilter的 `sharedMesh` 是独立组件引用；修改视觉网格引用不会自动要求更换碰撞网格。安全范围是只更新候选视觉，保留旧Collider对象、旧mesh资产、原位置/尺度/手性，且新外观不改变桥面高度/净宽/拼接区、长椅坐面/腿部主要包络和人物接触位置。

不能修改两个组件仍共同引用的旧mesh资产本体，否则碰撞也随之失去冻结基线。不能为了关闭旧显示而SetActive整个原Structure或LOD0，因为长椅Collider在同一GO上；只能安排视觉Renderer的替换/禁用并保留碰撞有效。若新视觉另挂子树，禁止复制生成第二套碰撞。

桥面只需保留原3个BoxCollider；桥桩和板缝目前没有精确碰撞，不要擅自添加阻塞通行的逐板/逐桩MeshCollider。长椅若增加超出旧包络的扶手或改变靠背/座面，会出现“可见外伸但无碰撞”或人物接触不符，应先限制为表面细节，不能把“旧碰撞保持”写成新模型碰撞已完整验证。

保留原MeshFilter的旧网格仍须进入root的 **所有MeshFilter（含inactive/disabled/无Renderer）600k预算**。只有真的从当前候选移除的可见旧MeshFilter可计为扣减；仅关Renderer不等于减少该口径面数。此审计没有决定实际采用哪种整合策略。

## 给素材与后续整合的契约

- 保留root、Structure、所有原Marker的名称、父级、局部/世界矩阵与单位；新细节可有独立候选，但不要自行接入岛。
- pier_module/end原5槽顺序：`Wood_Endgrain, Wood_Honey, Wood_DarkBeams, Wood_Weathered, Iron_Blackened`；bench原3槽：`Wood_Endgrain, Wood_DarkBeams, Wood_Honey`。材质升级应明确新旧映射，不能假设屋子四木材映射已覆盖Wood_Weathered。
- 栈桥保持板面Y、轮廓、桥接端点和补深桩底；长椅保持座面/坐点、稳定支撑与原Collider包络。新增细节几何/UV/法线需独立回读，不能只看总面数。
- 后续root若选择候选，再验证Marker世界矩阵、原Collider对象与mesh引用、桥界、三段拼接走过、长椅落座与近物镜头。当前没有Unity、碰撞游玩、FPS或视觉胜出结论。

审计基线SHA256：Island.prefab=`D17154FD0CF79CF55E65225DBB517626216C80BE2A3741DCC3BC53EABFF1AE45`；EnvV1Builder.cs=`B5961804E22847028B68034A738DD9EE2EC2B604CE5AD841B7E9B439992CDC02`。
