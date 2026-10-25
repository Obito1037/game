# 给 Claude 的 v2 联调与质感改进需求

本稿来自 2026-10-22 对当前磁盘源码、主场景 YAML、环境 Prefab 和唯一故事文档 `07_完整故事与生图提示词（最终版）.md` 的只读审计。没有操作 Unity，没有运行主场景，没有修改 Claude 的文件或 PlayerPrefs。数字公式已在独立 CPU 脚本复算；视觉表现、实测性能和真实输入手感仍待运行验收。机器可读证据与 SHA256 见同目录 `code-audit.json`。

源码审计与对标观察分开记录。根代理亲自在真实浏览器采集，本审计代理逐张查看保存的参考图；当前已复核R37浇水提示、R38动作、R39/R40实际对白。没有把根代理的键盘操作说成本代理亲自运行，也没有把环境静帧当主游戏实机。以下代码修复主要由我们自己的故事要求、代码和接口契约推出。参数是待试验的起点，不是假称测得的竞品参数。不要等用户看效果才继续，但遵守单方操作 Unity 的约定。

## 先修阻止环境升级真正进入游戏的问题

### C01 · P0 · 主场景仍引用灰盒岛

- 证据：`GameProject/Assets/JieGuang/Scenes/JieGuang_Main.unity:151` 为 `IslandPrefab: {fileID: 0}`；`Scripts/World/IslandLayout.cs:50–58` 在空引用时调用 `GrayboxIsland.Build()`。现有环境 Prefab 的 GUID 为 `a7a9419fcb5d9514797f43ce0d69249b`。
- 要改：由 Claude 给主场景的 `GameDirector.IslandPrefab` 赋值。不要为了赋值整场重建而意外重置手工修改；接入后让缺失必需锚点成为可见错误，避免静默退回另一组灰盒坐标。
- 验收：实际主场景实例 `UsingGraybox=false`；唯一 `Island` 包含实际村子、35 个旧版 LODGroup 或新版经记录的替代数量；截图 `ours/title.png`、`ours/first-control.png` 确认实际使用新版岛。环境测试场景截图不能替代此项。

### C02 · P0 · 两套天空和两套灯光没有统一所有权

- 证据：`Scripts/Story/GameDirector.cs:63–70` 无条件生成剧情 `NightSky` 和 0.12 强度的蓝色 Directional；环境 `Editor/EnvV1Builder.cs:950–977` 另有 NightSky Renderer、内置地球与星星，以及 0.60 / 0.25 的两盏暖色 Directional。当前主场景尚未引用真岛，所以这是接入后必然重复生成的契约问题，不是本次观察到的实机截图。
- 要改：只保留一个天空渲染权威，剧情驱动其 `Pollution / EarthPhase / EarthBrightness`。若暂时保留 Claude 天空，仅关闭环境 `Atmosphere/NightSky` Renderer，不要关闭包括海面的整个 Atmosphere。若采用环境新天空，则让剧情调用其适配接口，停止旧 Stars / Earth 的生成。冷蓝环境地光符合新提示词，地球反射的补光不应与实体暖灯混为一谈；统一光照预算，避免叠加三盏 Directional 造成无来源的亮岛。
- 验收：同一帧只有一个地球、一套星空；污染 0→1→0 时所有星空都参与渐隐；同机位 `sky-clean / sky-polluted / sky-restored` 三图。不得靠让旧天空永久隐藏来绕过剧情控制。

### C03 · P0 · 地球圆缺公式与剧情相反

- 证据：`Scripts/World/NightSky.cs:99–119` 的 `off=Lerp(.02,.9,phase/.5)` 与 `dx=fx+.98-off` 使 phase 越小，遮挡圆偏移越大。按原代码 256² 像素公式复算，phase=0.008 时亮像素占圆盘约 **63.805%**，phase=0.5 时却只有 **3.278%**（阈值 lit>0.5，不含暗面与光晕）。`GameDirector.cs:232` 第三章恰好设为 0.008。这是公式级错误；没有声称已截图测出亮盘比例。
- 要改：用真实半球受光投影或单调遮罩，使 `EarthPhase` 明确定义为可见亮盘比例。建议用球面法线与光向量点积，光轴 z 分量设 `2*phase-1`；保留蓝白云纹、低强度暗面和独立薄晕。不要只把公式反过来后仍把错误面积叫作 phase。
- 验收：phase=0 / .008 / .03 / .16 / .5 的离屏图和二值面积测试；亮盘面积单调增加，phase=.008 只能是细弧，.5 约为半盘；序章、长夜、终章亮边变化与 07 一致。

### C04 · P0 · 第三章“窗与码头同时亮”目前只在逻辑里成立

- 证据：`IslandLayout.cs:103` 月窗灯 direction=1 只指向 Target_Pier；`LampPost.cs:9` 宽光整角 78°，半角 39°；`LampRules.cs:47` 却直接判窗与码头双覆盖。按当前冻结锚点，两目标从灯头看夹角 **43.37287°**，圆窗中心在 39° 锥外。`art/generated/env-v1/puzzle-light-layout.json` 已记录双目标角平分线方案。
- 要改：让瞄准点依赖灯罩状态：月窗灯 wide + direction=1 时，取窗/码头两条单位方向的角平分线；晚风灯 wide + direction=0 同理取路/椅角平分线。当前布局建议晚风宽光整角 56°、月窗宽光 60°、窄光 24–26°。不要移动既有锚点去迎合灰盒代码。灯光锥中轴和 Shader 可见束必须使用同一方向、角度与原点。
- 验收：第一章两个目标、第二章三个目标、第三章四个目标的完整光锥与遮挡检查；中心点在锥内且至少留 5° 边距，拍解谜前后同机位图；要求真实表面照度变化，不能只看 `LampRules.Solved=true`。

### C05 · P0 · 相机未启用 URP 后期，新增 Volume 不会自动生效

- 证据：`CameraDirector.cs:24–36` 只创建 Camera，没有 AdditionalCameraData 或 `renderPostProcessing=true`。安装的 URP `Runtime/UniversalAdditionalCameraData.cs:466` 默认值是 false；在全部 JieGuang 游戏/编辑器代码中没有相关配置。
- 要改：创建相机时显式获取 `UniversalAdditionalCameraData`、打开 `renderPostProcessing`，设置能覆盖环境 Volume 的 `volumeLayerMask`（默认层 0 可用），确认 HDR 与 renderer postProcessData。Environment 的章节 Profile 由 GPT 创建，Claude 根据章节切换或调用过渡接口；请不要另建互相覆盖的全局调色。
- 候选起点：Linear + HDR；Tonemapping Neutral；Bloom intensity .25–.45、threshold .9–1.1；Vignette .08–.14；Filmic grain 0–.025；常态行走关闭景深，人物特写单独启用。最终参数以根代理的环境 Profile 为准。
- 验收：真实主相机后期开关 A/B 差异图；走路、对话、解谜均有正确 Profile，UI 不被景深模糊。Iris Xe 和 WebGL 分别记录成本，不将编辑器截图的流畅感当帧率。

## 灯光与环境接口

### C06 · P0 · “马灯熄灭”只关灯，不关发光模型

- 证据：`GameDirector.cs:87–89` 只缓存港灯 Light；`:884–889` 的 SetHarborLamp 只改 active/Light，第三章 `:477` 调 `SetHarborLamp(true,0)` 保留模型。真实港灯 Structure 的原 `Lantern_AmberCore` 在 **slot 1**；`MaterialKit.cs:67–71` 使用 `r.material`，只会改 **slot 0** 的铁框，不能拿它直接控制整灯 Renderer。
- 要改：按每实例、明确材质槽绑定，用带 materialIndex 的 MaterialPropertyBlock 或独立实例材质控制发光，禁止改共享材质。新 d 光果目前在 **slot 3**，优先按材质名 **`V2_Lamp_LightFruit_Controlled`** 查找并核对实际槽；slot 1 的 **`V2_Lamp_AmberGlass_AlwaysVisible`** 永不自发光，level=0 时仍保留玻璃和金属框，最后移走马灯时才隐藏整个对象。
- 初始化合同：原 HarborLight Point 基准强度 **1.2** 保留供 Boot 缓存，之后随 level 调整。旧光芯可缓存非零原始 `_EmissionColor`；新 d 光果默认 emission=0，须另设经 Unity 验证的发光峰值，不能缓存默认 0 再乘 level。默认 0 **不表示已接入或修复剧情亮灭**。
- 候选状态：路灯和港灯 d 的六张离线图已由 root 审阅认可为待 Unity 审阅的候选，尚未进入 Assets。贴图、槽名、透明策略和限制见[灯具交接](../../../generated/env-v2/lamp-study/HANDOFF.zh-CN.md)与[实际审图记录](../../../generated/env-v2/lamp-study/root-review.json)；不把离线认可视为主场景通过。
- 验收：固定旗杆近景 level=1 / .5 / 0 / 1；0 时光果无自发光、无 Bloom 光晕、Point=0，但玻璃/框架可见，恢复时重新亮起；三盏路灯和人物手提灯笼不受联动。截图必须包含“还差一点”台词帧。

### C07 · P0 · 阿婆圆窗没有运行时可控制对象

- 证据：`GameDirector.cs:77–78,130–135` 查 Target_Window 下的 WindowGlow，再退回名为 RoundWindow 的物体。当前环境 Prefab 只有空的 Target_Window / Marker_Window，没有 RoundWindow；因此 roundWindow 为 null，`Stage` 和第二章 `:365` 的亮灭请求被略过。
- 要改：GPT 在环境中给出可独立控制的圆窗/室内光 Renderer，保持看得到阿婆的真正圆孔；Claude 绑定 WindowGlow 或更明确的室内发光控制接口。兼容多个发光材质槽，不能让整栋木屋发亮。
- 验收：第二章开始时窗暗，调灯成功后窗内桌面/阿婆变得可读；圆窗孔没有被新的发光圆片堵住，窄光没有照到整面房屋。记录 roundWindow 非空及目标材质槽。

### C08 · P1 · 三盏实体灯与手提灯笼的发光不完全受状态控制

- 证据：`LampPost.cs:79,155` 仅在 BuildGraybox 创建 bulb 引用，复用环境 LampHead 时不会绑定；实体灯罩中的发光部分不会随 On 改变。真实 CopperHood 原 `Lantern_AmberCore` 在 **slot 1**，而 `MaterialKit.cs:67–71` 的 `r.material` 只改 **slot 0** 的铜壳；仅把整个 CopperHood Renderer 填给 bulb 仍会改错槽。人物手提灯另有独立问题：`Lantern.cs:40` 的 Glass 使用常亮 Additive 材质，`:81–84` 只改 Point 和 fruit 发光，Brightness=0 不改 Glass。
- 实体三灯要改：复用现有 LampHead/Spot，按每灯实例查找发光槽。新 d 光果目前为 **slot 3**，优先按名 **`V2_Lamp_LightFruit_Controlled`** 绑定并核对 materialIndex，按同一 On/onLevel 驱动；**`V2_Lamp_AmberGlass_AlwaysVisible`** 永不 emission，铜壳/玻璃保持正常反射。不能通过 slot 0 或共享材质控制。新光果默认 0，必须配置实际发光峰值后才能响应点亮，不能把默认黑芯视为剧情已修复；d 的离线认可、尚未进入 Assets 的状态与文件链接见 C06。
- 手提灯笼要改：其玻璃高亮/加色仍须单独按 shown 比例衰减，允许普通反射但不得仍像点亮的灯；不要因环境玻璃改为 AlwaysVisible 就跳过 `Lantern.cs` 的常亮 Additive 问题。序章三盏 Off 时、幕间手提灯熄灭时，各自使用对应的同一状态源，不能互相串联。
- 验收：同曝光近景逐灯 On/Off/On，只有被切换的光果槽和原 Spot 改变，铜壳不发光、另两灯与港灯不受影响；0 光时无自发光泄漏。幕间手提黑灯在轮廓可读的前提下保持玻璃内完全无光。

### C09 · P1 · 海天颜色没有随光污染同步

- 证据：`NightSky.cs:131–137` 改相机 clear color、雾与环境光，但没有访问环境海面；`Environment/Shaders/EnvNightSea.shader:7,41–43` 使用固定 `_Horizon`、不直接应用 URP 雾。Shader 提供属性不代表剧情已经连接。
- 要改：统一章节大气状态，在污染插值时同步海面 `_Horizon` 与天空地平线；考虑海面仍有可辨识的低对比细波。使用实例材质或 PropertyBlock，不改共享资产原色。
- 验收：清净/污染状态相同海天线机位，不能出现深蓝海突然接灰白天的硬接缝；相机旋转到其他方向也检查。原始昼夜世界观不变，没有太阳和远方其他岛。

## 移动、镜头和动画

### C10 · P1 · 可走边界未被控制器消费，NPC 地面查询包含房顶

- 证据：`PlayerController.cs:59–86` 只有重力 Move，无越界/坠海恢复；游戏代码没有读取 Walkable_Boundary。`GameDirector.cs:760–775` 的 NPC Walk 直接沿端点直线改 Transform，`:900` GroundY 使用除玩家层外的所有层；`CrowdLights.cs:50` 也查询所有层。环境契约已经区分 Layer 8 可走面、Layer 9 房屋/岩石。
- 要改：地面探测限定 Layer 8，障碍避让/相机碰撞另用 8|9；NPC 沿石路有序路点行走，并在碰撞前停下或绕行。用陆地与栈桥边界的并集约束玩家，维护最近安全位置，坠海时平滑恢复；不要只用岛的 AABB。保留现有 stepOffset=.35、slopeLimit=48 的实测余量，再用路线验证决定收紧。
- 验收：邮差村口→岬角、邮差→椅子、阿萤→玩家完整录像；无穿屋、上屋顶、飞坡。玩家沿全岸/栈桥边缘走一圈，离开边界不永久下坠，仍能进入港桥和村子。此为代码识别的高风险，尚未亲测掉落。

### C11 · P1 · 停止输入不停止步行动画，速度标定也不一致

- 证据：`PlayerController.cs:67` InputEnabled=false 时不清 actor.SetMoveSpeed；`GameDirector.cs:399` 到树下停步等多处只关输入；玩家 WalkSpeed=1.6，但 `Editor/JieGuangAssetSetup.cs:75` 玩家步行 BlendTree 阈值为 1.2，所以普通走路已混入跑步。`CharacterActor.cs:53–54` PlayAndWait 只读一个时间点的当前状态长度，没有验证进入目标状态。
- 要改：通过统一的控制权切换 API 清除移动目标速度；速度标定要由步态实际脚掌位移决定，先把玩家行走与阈值统一到 1.2–1.6 m/s 中经校准的同一值；加速/减速试验 4/6 m/s²，转向 360–480°/s。动作等待按目标 state hash / normalizedTime 确认，并有超时记录。
- 验收：持续按 W 跨入对话、树下停步、章节卡，0.2s 内转待机且不原地迈步；10m 行走两侧脚跟不连续滑动；蹲起、坐下、伸手镜头均完整。数值候选需与人物实际骨架比例验证。

### C12 · P1 · 固定剧情镜头不进行避障，跟随碰撞也会继续插值进墙

- 证据：`CameraDirector.cs:67–72` shotMode 直接 Lerp 无碰撞；行走 SphereCast 后 `:101` 继续从旧位置 Lerp，不保证当前帧留在障碍前；`GameDirector.cs:881` 对话两侧都堵时退到另一个未经检查的位置。
- 要改：剧情镜头使用环境审定机位、过渡路径采样和 SphereCast；跟随被压缩时立即到碰撞安全距离、离墙时慢慢放开；将遮挡修正与审美阻尼分开。现值 FOV50、距离4.2、目标高度1.25 可先保留为基线，试验普通镜头 FOV46–50、半衰期 .12–.18s、对话FOV36–42；禁止用固定FOV改变代替构图检查。
- 验收：村屋间转360°、圆窗对话、长椅对话、金树幕间、旗杆挂灯；相机和主角始终在可读侧，人物面部不被树枝/墙遮挡，转场无穿地或急拉近。录制视频才能评价阻尼。

### C13 · P1 · 主角终章亮度不是全岛最淡，萤光不是轮廓材质

- 证据：`GameDirector.cs:105–108,515` 当前强度阿萤1.4、邮差.7、阿婆.25、灯伯.35、主角.5。`Fireflow.cs:71–82` 所有人用相同强度乘数，主角 Point/.02 发光系数均高于两位老人；`Fireflow.cs:76–77` 给整个材质匀加发光，没有 Fresnel/轮廓遮罩。
- 要改：主角终章先试 .12–.18，低于阿婆，保留可读手指轮廓。用材质轮廓项或轻柔背侧补光，不发光到整个脸；人物仍不透明。可将肤色与衣服发光分开，支持所有材质槽，不能仅 `Renderer.material` 第一槽。
- 验收：同距离同机位五人亮度并排以及手掌重逢近景；主角最淡但看得清。序章主角身体为0，只有手提灯的环境照射。不要通过过曝阿萤来“拉开差距”。

## 叙事、UI、音频与存档

### C14 · P1 · 幕间空间与文字冲突，第一朵花仍是球

- 证据：07:175–197 在阁楼床边收信；`GameDirector.cs:398–415` 人物停在金树下，邮差也直接放到树下，而 `StoryText.cs:138` 仍说“楼下”“床边”。环境 v1 尚无阁楼。`:823–838` EnsureFlower 生成 0.22m Sphere，位置按树根+偏移推测，并未绑定真正最低树枝。
- 要改：GPT 补阁楼/可用读信小景及花资产时，由 Claude 做树下熄灯→阁楼读信→下楼重燃的明确转场和动作；在阁楼未完成前，按07允许的全屏幕间卡清楚叙述转场，避免树下画面配床边对白。花由环境新增附着接口/资产接入，保留现有锚点位置契约。
- 验收：幕间“楼下”出现时画面空间可解释；灯灭→读信→重新点亮完整录屏；终章特写里是真正有花瓣、花心与枝条连接的小花，没有悬空球。不能删掉信或主角低谷来缩减工作量。

### C15 · P1 · UI 缺少信息层级与过渡，文本切换有旧句残留一帧

- 证据：`GameUI.cs:65–103` 使用固定纯色矩形；章节卡为整屏82%黑底，64px，淡入/出各0.625s、固定2.4s停留；对白32px、34字/s，无整体渐入；`:193–209` 启用对白后先 yield 一帧，未清空 lineText，下一句开始前会保留旧句；调灯面板640×520挤入大量文字。没有章节地图实现。
- 参考实证：已亲看保存的[真实对白R39](reference/39-rose-follow-00.png)和[R40说话人切换](reference/40-dialogue-sequence-0000ms.png)。R13的近身E提示没有大底板，而真实对白有底部宽半透明深板、细金边、说话人胶囊和继续标记；不能概括为参考所有UI都无背板。R39人物与玫瑰位于阅读板上方、探索HUD退去。R40没有逐字增长中间串，打字速度/淡入时长仍未测。
- 要改：先在 SayOne 开始清空 lineText/重置箭头，再做同一套原创纸纹与铜金细线风格，区分轻量动作提示与需要背板保障可读性的长对白，避免照搬对标胶囊边框、金星图标、构图和文案。说话人/正文/继续标记共用一条对话状态，结束后恢复当前目标；按键展开正文与推进下一句需防同帧误跳。1920×1080基准：正文30–34px、辅助22–24、说话人28–30；对白宽屏幕65–74%、底部安全边距5%，底板alpha .66–.76；对白淡入 .18–.24s，目标提示淡入 .3s，标题卡 .65s入/2.4s停/.65s出作为基线。UI 的纸纹来自用户自有或新制素材。
- 章节地图以借光岛实际地形和六个剧情地点为原创组织，并提供继续进度；若先不制作地图，拆解报告应明确“尚无”，不能把标题卡充作地图完成验收。
- 验收：1440×900 与1920×1080的标题、章节卡、最长对白、完整信、调灯、任务提示、尾声八类截图；不能遮住关键灯头/圆窗；对话逐帧录屏无旧字闪现，信纸内容不超出可读区。参考图编号为R13（轻提示）、R19（展开任务）、R39/R40（对白）；我们仍需真实主游戏同类截图。补验对白出现时任务HUD收起、说话人切换不闪旧句、按一次键不误跳两句、结束恢复正确目标；精确动画时间不从参考文件名照抄。

### C16 · P1 · 存档校验、QA隔离与回标题状态未收口

- 证据：`GameDirector.cs:119–124` debugStart 直接 cast 到 enum；`:187–203` 每个章节开始立即写 `jieguang.chapter`；没有版本/合法范围校验。`:174–175` 每次 Title 累加闭包事件、不解绑；尾声 Esc `:586–590` 回标题前没有清 Objective/Toast，也不重新布置灯、船与人物。
- 要改：验证存档只接受1–7中的有效章节，非法值回安全起点；调试跳章使用隔离存储/禁写模式，不能误改用户进度；返回标题清 HUD、清理订阅、明确重置展示状态。输入/事件解绑必须覆盖协程中止路径。保留已有用户存档键，迁移须可恢复。
- 验收：无存档、合法每章、非法-1/99、尾声→标题→继续重复三次；每次只启动一条主流程，不残留任务字，不多次回调。QA前后用户真实 `jieguang.chapter` / `debugStart` 不变；不要为了截图清空用户PlayerPrefs。

### C17 · P2 · 场景环境音与章节动态音轨尚未实现

- 证据：`GameDirector.cs:111–116,841–844` 只播放 NightLetters 循环和铃声；Resources/Audio 也只有 NightLetters.wav、LanternChime.wav。没有风、海浪、脚步或转灯声的播放路径。
- 要改：使用自有/有授权音频，新增持续低声海浪与疏风，陆地/栈桥脚步区分，灯头转向轻铜声；幕间降低音乐并保留风声，重燃与挂灯给克制的音色反馈。音量建议以主旋律为0dB相对参考：海浪-12至-18dB、风-18至-24dB；转场交叉淡化1.5–3s，需实际听感校准而非绝对混音标准。
- 验收：标题→序章→幕间→挂灯的连续录音，无突然断音/叠播；风浪不盖过铃声，静音设置覆盖全部声源。没有实录前不报告音频已达到对标。

### C18 · P1 · WebGL / Iris Xe 预算不能用源代码目标帧率代替

- 证据：`GameDirector.cs:56` 只设 targetFrameRate=60；两套RP资产都是每对象附加光上限4（`Assets/Settings/PC_RPAsset.asset:48`、Mobile同位置）。当前剧情除3Spot外，还有人物Point、灯笼、约11个人群Point，环境另有灯；每对象可能抢光。Mobile资源渲染比例.8、附加光阴影关闭；是否当前WebGL使用该质量档需要构建时确认。
- 要改：由 Claude 记录实际平台/Quality/URP资产/renderer/相机配置、GPU与帧时间；优先让人群发光点用批次/粒子，只保留影响关键表面的少量Point。管线资产与ProjectSettings不属于GPT改动范围，需要的修改请Claude接手。不要盲目提升附加光数量。
- 验收：Iris Xe 1440×900，记录真实输出分辨率、10s预热后至少60s的标题/村子走动/第三章灯光负载帧时间p50/p95/p99、draw call和GPU/CPU瓶颈；另做真实WebGL加载与运行记录。结论限于测过的场景与设备，缺失实测就标未验证。

## 联调顺序与交接边界

建议先完成 C01→C02/C03/C04/C05→C06/C07/C08，再测第一章到终章。主场景进入真实岛后才有价值采集“我们”的对标帧。C10–C16 随章节逐项回归，避免只做 EnvTest 静态美图。

Claude 只修改自己负责的游戏、UI、人物、主场景；Environment 内的天空、海面、Volume、地形和模型由 GPT 修改。锚点旧名字/位置不变，新附着接口可追加且必须写交接。双方不得同时操作 Unity。

本稿代码问题仍是源码审计/数学复算结论，未由本代理运行Unity验证；对标已由根代理实机采集，本代理查看保存图，具体范围见 `observations.json`。R39/R40已证明实际对白与部分推进，完整对白结束、首章通关、音频审听与性能仍未验证；不能据此声称视觉“追平”、全流程通过或60FPS达标。
