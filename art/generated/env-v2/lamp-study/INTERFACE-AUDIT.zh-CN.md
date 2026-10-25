# 路灯与港灯：真实 Island 和剧情接口审计

2026-10-22，只读检查已保存Island.prefab及当前磁盘 `LampPost.cs`、`GameDirector.cs`、`MaterialKit.cs`、v1构建器。未操作Unity，未导入候选，未写整合器/Builder。以下代码风险来自磁盘源码，不声称运行中的主场景已经复现；素材候选和正式接入仍由root另行审图决定。

## 实际数量、网格与层级

`copper_roadlamp`在真实岛上恰好 **3份**，但不是完整FBX实例。v1构建器把其两个mesh拆到原锚点下：每灯 `CopperColumn` 348tri + `CopperHood` 258tri，共606tri；三份合1818tri。`harbor_lantern` **1份**、Structure436tri。现有港灯是Point，不是第四盏谜题Spot。

```text
Island/Anchor_Lamp_WanFeng（YueChuang / GuiHang相同结构）
  Structure
    CopperColumn           MeshFilter + MeshRenderer，Layer 9
    ColumnCollision        BoxCollider，Layer 9
  LampHead                 原旋转轴，localPosition=0，scale1
    CopperHood             MeshFilter + MeshRenderer，Layer 0，无Collider
    Spot                   Light，Layer 0，无网格/Collider

Island/Props/HarborLantern
  LOD0                     原FBX根轴变换
    Structure              MeshFilter + MeshRenderer，Layer 0，无Collider
    Marker_HangingPoint    空物体
  HarborLight              一个Point Light，无Collider
```

路灯mesh GUID=`e144afd88863a6e4f9e3331c1ef21896`；Column mesh fileID=`-1542031950021933715`，Hood=`739741886781755277`。港灯GUID=`610280d8bc703474cb93467807bd22a8`、Structure fileID=`-1542031950021933715`。

源路灯FBX的 `Marker_Bulb`、`Marker_Base` **不在现有Island的三灯层级中**：`EnvV1Builder.cs:851–867`取出Structure和LampHead后销毁临时模型，Marker留在临时根随之消失。不要把“源FBX有Marker”误写成“当前prefab已提供该Marker接口”；如以后增加控制锚点，应先由root/Claude明确约定，不能擅自替换现有Spot。

## 三个LampHead和原Spot

| 灯 | Anchor/LampHead世界位置m | 初始Spot角度 | Structure局部Y比例 |
|---|---|---:|---:|
| WanFeng | (8,6.2,-16.5) | 56° | 1 |
| YueChuang | (4,6.4,-21) | 24° | 1.0526316（4/3.8） |
| GuiHang | (11,6.2,-18) | 24° | 1 |

Anchor本身rotation identity，灯头在Anchor局部原点，只有LampHead旋转；柱体没有跟随灯头俯仰。柱碰撞均是原 `Structure/ColumnCollision` 上enabled、非trigger的Box，center `(0,-1.9,0)`、size `(.24,3.8,.24)`，随Structure的Y比例形成3.8m/4m高柱，底部约Y=2.4。

三个Spot均已存在，是LampHead的**直接子级、CopperHood的同级**：局部位置 `(0,0,.29)`、rotation identity、scale1；光束沿自身/Head的 **+Z**。初始强度16、range18、soft shadows、shadowStrength.8、bias.035、normalBias.1、shadowNearPlane.2。`EnvV1Builder.cs:873–886`明确创建此结构。prefab中三个Spot GO分别在第21368、20624、31928行。

各Hood本身保留导入轴转换：local rotation约X=-90°，scale `(-1,1,1)`，局部原点0；Blender遮光罩前向-Y经过它变成Head局部+Z。不能再对LampHead额外旋转90°，也不能把柱子的Y比例套给Hood/Spot。

从真实prefab TRS离线复算的初始Spot世界位置/前向：

| 灯 | Spot世界位置m | +Z前向单位向量约值 |
|---|---|---|
| WanFeng | (7.9671454,6.0218865,-16.7264866) | (-.1132916,-.6141845,-.7809883) |
| YueChuang | (4.0001287,6.2131937,-20.7781816) | (.0004439,-.6441597,.7648909) |
| GuiHang | (10.8821527,6.0026056,-18.1767696) | (-.4063701,-.6806703,-.6095502) |

这些是磁盘初始状态，不是当前解谜状态。`LampPost.cs:29–38`先找原LampHead和其Spot并复用，缺失时才新建；`:40–45`覆盖部分Light参数。运行中`:134,144–149`按目标转Head、调角度/强度。因此不要加“另一个剧情Spot”，不要删/改名原Spot令Setup误走fallback。`IslandLayout.cs:111–115`用真实Head位置作为灯头位置。

## 灯罩与发光槽的确定风险

真实Hood材质顺序是 `[0 Copper_Aged, 1 Lantern_AmberCore, 2 Gold_WornEdges]`。港灯Structure顺序 `[0 Iron_Blackened, 1 Lantern_AmberCore, 2 Copper_Aged]`。四个发光槽共用 `Lantern_AmberCore`，GUID=`001f3437dd6c77443ba1fb1978dd313d`；材质第28行启用 `_EMISSION`，第133行 `_EmissionColor=(2.2,1.276,.418,2.2)`，第126行 `_Surface=0`，是现有不透明发光芯。

1. **真实三灯没有绑定bulb Renderer。** `LampPost.cs:18`声明bulb，但唯一赋值在灰盒 `BuildGraybox():79`；已有真实LampHead时不走该函数。因此`:155`的 `if(bulb!=null)`无法控制真实Hood里的AmberCore，Spot熄灭不等于该可见光芯熄灭。
2. **直接把整灯Renderer赋给bulb也不足。** `MaterialKit.cs:67–71`通过 `r.material`只改第一材质。真实发光槽是index1，slot0是铜/铁；这样会改错槽。把shared Material直接改黑又会把3灯+港灯绑成同一亮灭状态。
3. **灰盒与真实模型要使用同一状态、明确槽控制。** 后续应由Claude针对每实例发光槽控制（例如明确material index的MPB，或独立实例材质）；铜/玻璃可见性与发光强度分别考虑。仅拆新模型/新增Controlled槽，不会自动把这套接口修好。本轮不修改Claude代码。

`LampPost.cs:109–123`还会动态创建可见Beam/BeamInner；它们是沿+Z的锥形网格，不是附加Light。`:153–154`控制Beam active/alpha，与Hood发光槽并非同一个控制接口。不能把光锥、真实Spot、材质自发光混为一种“灯”。

旧镜片几何在 `env_v1_props.py:417`：Head局部+Z中心约.27、厚.022，前表面约.281；Spot在+.29，约比镜片前表面靠前9mm。罩口约+.335（`:408`）。Hood当前cast/receive shadows均开启。若候选在光轴前添加光果/玻璃，应验证它与Spot、罩口的相对位置、透明材质/ShadowCaster和遮光效果；不能只看Blender美图。现有shadowNearPlane=.2，近几何关系并不能单独证明自遮挡已经发生或一定不会发生。不要靠改变Spot位置/角度、整体关闭铜罩阴影来掩盖未验证问题。

## 港灯位置与熄灯剧情

港灯根 `(10,3.46,-10.5)`、rotation identity、scale1。LOD0保留X约-90°/负X轴转换，`Marker_HangingPoint`原局部 `(0,0,.79)`，世界约 `(10,4.25,-10.5)`，与 `Anchor_FlagpoleHook`位置一致。FBX Marker.forward约世界+Y，Hook自身则朝世界-Z；保留各自矩阵，不凭Marker.forward覆盖Hook朝向。

`HarborLight`与LOD0同级，局部 `(0,.38,0)`，世界 `(10,3.84,-10.5)`，Point强度 **1.2**、range **3.5**、无阴影。源构建器`:162–170`明确设置非零初始值，供剧情缓存。港灯没有Collider，不要在视觉替换时新增阻挡旗杆/挂灯操作的碰撞。Prefab根第7611行，HarborLight GO第28789行，Hook第32695行。

**确定的熄灯缺口**：`GameDirector.cs:87–89`只缓存HarborLantern下Light及初始强度；`:884–889`的 `SetHarborLamp`只改整个港灯active和这些Light强度。第三章`:477`调用 `SetHarborLamp(true,0f)`，此时对象仍可见、原共享AmberCore自发光保持非零，所以从源码可确定没有执行材质熄灭；实际画面残亮程度仍需Unity验证。`:491`才调用false隐藏整个对象。不能提前隐藏整灯去替代“灯具仍在但熄灭”的剧情状态，也不要把初始Point强度设为0使Boot缓存失去恢复亮度的基值。

素材代理提出的新Controlled发光槽默认0，可避免未经剧情接入就常亮，但它也意味着未绑定控制前不会自动变亮。旧玻璃、铜铁、受控光果各槽的责任应写入材质映射，并由Claude完成每实例初始化/半亮/熄灭/隐藏；不得把默认黑芯当作已经修好全剧情亮灭。

## 碰撞保留与后续验收边界

这两类灯具当前 **无MeshCollider**：三根柱只用3个Box，港灯无Collider。升级视觉可保留原柱Box和全部Anchor/Head/Spot/Hook/挂点的变换、组件身份。新旋钮/光果等装饰不应额外影响道路、光线碰撞查询或角色操作空间；如改柱尺寸或大幅外伸，则需要另行碰撞决策，不能自动把候选网格烘成新碰撞。

root决定接入后，至少核对：仍仅3个Spot与1个港灯Point；Head旋转只带Hood/Spot/可见Beam，不带柱；三灯独立开关与宽窄状态不串材质；港灯满亮/半亮/熄灭但实体保留/最后隐藏；从不同方向看铜罩、玻璃与光果，检查透明排序、轮廓和阴影。当前没有运行、截图胜出、帧率或WebGL结论。

基线SHA256：Island.prefab=`D17154FD0CF79CF55E65225DBB517626216C80BE2A3741DCC3BC53EABFF1AE45`；EnvV1Builder.cs=`B5961804E22847028B68034A738DD9EE2EC2B604CE5AD841B7E9B439992CDC02`；LampPost.cs=`FFCF50936B2EBE3198351501EE4867AFD4BCDA13FD77D2C6A90BE67104BCC4F6`；GameDirector.cs=`01633A8052E3E691033AE6F387FA4DB0F8E5A5AE96EA2170B30C45C1ED9BD21A`。
