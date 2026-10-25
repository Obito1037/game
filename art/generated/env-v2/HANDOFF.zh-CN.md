# 环境第二版：已暂停并移交 Claude

日期：2026-10-22。唯一故事依据为 `art/design/script/07_完整故事与生图提示词（最终版）.md`。目前**尚未导入第二版 Assets、生成 IslandV2、运行 Unity 验证或取得第二版整岛截图**，不宣称已经追平参考作品。

## 协作与当前可用版本

**最新用户指令：任务暂时交给 Claude 接手。GPT 已停止开发和 Unity 操作，后续由 Claude 接手，避免继续同时写入。** 最新交接入口为 `TO_CLAUDE.zh-CN.txt`。此前环境 v1 已交付并释放编辑器，V2 本轮始终未进入 Unity；现有 `Environment/Island.prefab` 和 `EnvTest.unity` 保持第一版。旧的追加文件已落实，不代表当前 V2 已完成导入。

2026-10-22 再次阅读追加要求，并在实际 Island.prefab 与 v1 检查记录核实以下五个节点均存在：

| 名称 | 已验证世界位置（米，X/Y/Z） | 合同 |
|---|---|---|
| Anchor_VillageGate | -12 / 8.38550 / 4 | 脚底贴地、朝下坡 |
| Anchor_GoldenTree | 1.8 / 2.36404 / -21.4 | 金树根地面 |
| Anchor_Boat | 12.2 / -0.45 / -12.3 | 与 ReturningBoat 根一致，yaw 180° |
| Target_Sea | 10 / -0.16 / 19.5 | 栈桥外约 30 米海面 |
| NPC_ABo_Door | 6.20143 / 2.39917 / -18.23588 | 门外贴地、朝外 yaw 154° |

二版会保留所有原锚点世界变换、三灯 LampHead 转轴和既有 Spot、22 扇可独立控制的村窗、座点骨盆语义、ReturningBoat 与 HarborLantern 名称，以及 Layer 8/9 数字合同。禁止进入主场景 Play；不会改 Claude 的文件、项目设置或旧 BorrowedLight。

## 已实际完成的离线工作

- **参考实机研究**：已真实游玩 littleprince.dev 第一章并完成坐椅看日落，最新 `80-chair-stable.png` 明确坐姿与启程提示，`83-departure-held.png` 回到第二章高亮的章节地图。尚未进入第二章或实听音频，不是全游戏通关。常用1440×900、DPR 1；82帧因浏览器窗口状态变化实际1076×637，83已恢复1440×900，逐图尺寸以索引为准。截图仅放 `art/design/v2/benchmark/reference/`，没有下载/解包游戏素材，不把截图延迟当帧率、动画或加载精确时长。
- **拆解与协作请求**：`art/design/v2/benchmark/littleprince-teardown.zh-CN.md`、`side-by-side.html`、`REQUESTS-FOR-CLAUDE.zh-CN.md`。13 项研究中缺少的音频、完整结尾等仍标缺证；现有四张我方图片是 v1 EnvTest 静态图，不是主线对应实机画面。
- **输入盘点**：`incoming-inventory.json` 与 `ASSET-GAPS.zh-CN.md`。检查时 Downloads 中没有 `借光岛_v2模型` 新素材目录；现有九个 GLB 已保留清理成果，十张剩余项参考图不等于十个模型。
- **阿婆屋**：`props/abode_grandma/`。11,925 三角面候选增加瓦片、阁楼外观、烟囱和结构细节；原 Marker、门窗真洞和外形边界检查通过。164 个木构件 UV 已按长轴重排，使用 4 张共享木材材质。屋檐/阁楼四处黑块经射线定位为共面重叠，修正新增装饰的 1,672 个顶点、位移 1.5–6mm，面数/四 Marker/包围盒不变；`seam-after-*` 同机位已目视，黑块消失且正常阴影保留。阁楼没有可行走室内，不冒充故事过场已实现。
- **海岸修复**：`terrain/candidate-b/`。补齐原地面与崖壁间 48 条缺失边界对应的破口，并改善端部细柱；只改可走范围外 186 个地面顶点，原路网与可走范围内顶点保留。16 项 Blender 检查通过；Unity 碰撞重烹和实际画面仍待验证。
- **三款村屋**：`village/`。顺纹木墙/梁、48 块曲瓦、窗框、石脚和开口烟囱完成；修复窗角、柱脚和门楣共面黑块。每款 1,478 三角面（主体 1,454＋原窗 24），每栋增 454、11 栋共增 4,994。原两窗、门 Marker、根、包围盒与9材质槽合同、三款 FBX 回读均通过；24 张 900×900 Blender 对照已由制作者审阅，主代理另外查看蓝绿正面中性、赭红背面中性、灰瓦正面夜景三组成对图，确认有明确改善。屋瓦仍是简洁材质，Unity 共享瓦材质与离线 roughness 不完全相同，不能据此声称游戏画面已通过。
- **终章第一朵花 A04**：独立 `first-flower/candidate-c/first_flower_A04.fbx`，1,968 面、5 材质、花冠直径0.25m，6片厚花瓣/单琥珀心/斜枝2叶；具备闭合、半开、开放形态。新进程FBX往返、Blend重开与9个插值样本检查通过，主代理实际看过开放/闭合/侧面/夜景。没有自动挂接金树、导入Assets或改剧情。枝根是轴心，镜头应改瞄 `Marker_BloomCenter`；Unity权重按 `first-flower/HANDOFF.zh-CN.md` 的两段公式，不能HalfOpen/Open同时100。叶缘和花心近看仍偏低模，真实枝头位置/Unity变形/夜景/终章镜头未验证。
- **栈桥和长椅**：`pier-bench/` 三款仅改UV与材质，全部几何、面槽、Marker、桥面/座面、包围盒保持；每段456面、长椅324面，实际3段+1椅共1692面、新增0。`pier_end`668面仅作为备用、岛内没有实例。24张同条件对照已审，主代理另看5张记录于root-review；三件独立进程FBX/UV/打包Blend核对通过。顺纹更明确，桩顶仍非真实年轮、重复纹理和Unity过滤未验证。独立4个CoastalWood材质包含Weathered，不复用屋材tint。
- **路灯与港灯 d**：`lamp-study/candidate-d/`，路灯830面/盏，三灯增加672；港灯788面、增加352。保留轴心/挂点/旧几何主体，玻璃与独立光果槽分开；弱化铜斑和内罩刺眼反射。主代理实看两资产共6张中性/亮/灭图，接受为离线候选，玻璃夜间轮廓弱、光芯简化，未称最终达标。FBX/UV/打包Blend验证通过；4张512²原创铜纹理，参数和SHA见其HANDOFF/manifest。**未加入CandidateBuilder或Assets**。真实LampPost只给灰盒bulb赋值，MaterialKit只控slot0；港灯只控Light，均仍需Claude按实例、按名绑定光果槽。默认emission=0不等于剧情已修复，也不能缓存0再乘level。
- **旗帜只读盘点**：`flag-study/`。旧旗布479面、17个分离组件，图案离布面较远，直接加波浪可能穿插；旗杆/Hook已有合同保持。保留旧旗，不做未经审阅的动态替换。五角星/单面徽记等与新提示词差异已记录，未生成新旗候选。
- **草地、地表、天空、海面和五章 Look**：源候选在 `staging/`。草/野花按低频簇分布，近路及碰撞区域排除，距离 LOD 与风动；原创草地纹理与分层地表 Shader；修正地球圆缺公式；暖色灯、冷蓝环境与低强度后期。仅离线代码验证，不能据此宣称 Shader 已编译或 FPS 达标。
- **独立候选整合工具**：`staging/Editor/EnvV2CandidateBuilder.cs`，显式 BuildCandidate / CaptureCandidate，输出计划为 `Environment/Candidates/IslandV2.prefab` 和 `EnvV2Test.unity`；保留原 Island。C# 联合离线编译通过；已增加五个补充锚点唯一断言、独立截图场景剔除位和自有 Volume 临时层隔离、RenderSettings 恢复检查，以及四材质木纹 helper。仍需真实 Editor 执行。
- **村屋合批接入源**：独立 `EnvV2VillageBuilder` 已接入上述候选生成器；保留11栋原disabled主体、22扇剧情窗、11个BoxCollider和原Marker，只更新候选岛的14组可见旧合批。朝向通过完整门标记矩阵和窗口双向点集比对；全岛同时报告全部Renderer与全部MeshFilter面数，后者包含无Renderer的保留旧网格，仍要求≤600k。最新7个Editor＋2个Runtime联合离线编译 exit 0、无诊断，源哈希见 `staging/verification/candidate-village-csharp.json`。未实际在Editor运行。
- **栈桥/长椅接入源**：`EnvV2PierBenchBuilder` 已由主代理接入CandidateBuilder，输入增加两个FBX（当前共7个FBX、2张贴图）。以完整Marker矩阵和逐槽有向三角面核对后，仅替换4个视觉MF/材质，保留旧桥面Box和长椅MeshCollider/sharedMesh。8个Editor＋2个Runtime最新联合离线编译exit0、无诊断，证据 `staging/verification/candidate-coastal-csharp.json`；独立源码复核无确定阻塞。先前村屋编译是历史记录，最新全部源SHA以coastal记录为准。运行时几何/碰撞检查未执行，不放宽失败公差掩盖差异。
- **独立 HLSL 检查**：Sky/Sea 103 项 SM4 探针（其中海面灯/阴影组合 100 项）、Meadow/TerrainSurface 四 Pass 共 92 项均通过；后者可复现夹具与记录在 `staging/verification/`。这是本机 D3DCompile 的受限 DX11 证据，含明确的 include/pragma 适配，**不是 Unity ShaderLab 导入、WebGL 或画面通过**。
- **树材质诊断**：`vegetation-study/` 的 A/B 已完成，B 不接入。许多叶面实际仍落在 Bark 槽，LeafVeins 占普通树 A 表面积 1.067%、金树 8.559%；仅改叶脉 tint 无法获得银绿树冠。原纹理与网格保持，逐面分组仅为诊断，不能据此自动染色。
- **独立金树几何探索**：`vegetation-geometry/` 两轮尝试增加柔软厚叶和真实落地根。主代理已看实际正/侧/夜景及原作对照：候选枝叶仍呈水平分层，主干过于均匀，果实辨识度弱，整体未胜原作，**拒绝正式替换**。保留研究与失败诊断；没有接入 Builder、Island 或变更现有树碰撞。

## 原创纹理检查

`textures/` 中两张生成图实际均为 **1254×1254**，不是提示词期望的 2048。来源与原始提示词见 `generation-manifest.json`，只读像素统计见 `texture-audit.json`，重复目视图见 `tile-review.png`。

草地图的边界跳变约为普通相邻像素的 1.16/1.18 倍；木纹上下约 2.36 倍。CSS 重复预览没有明显的大块明暗分界，木纹存在可识别的重复结节及局部跨边纹路中断；因此不把它们称为数学无缝纹理。木屋按独立木板长轴安排 UV、避免木纹 V 跨边重复；地面采用两套不同尺度/方向采样减弱重复。仍需实际模型与 Unity 近景验收。

## Claude 接手后的建议顺序

1. 检查 CLI status 与 pipeline list，记录当前场景、编译/Play 状态和受保护文件哈希。
2. 按 `staging/CANDIDATE-INTEGRATION.zh-CN.md` 复制自有源、FBX 与原创贴图；仅导入 Environment。
3. 查看真实 C#/Shader 编译错误，修复自己范围内的错误；执行 BuildCandidate 并逐项读报告。
4. CaptureCandidate 使用原样基线、冻结基线、冻结候选相同机位 1440×900；检查标题、岬角、码头、村子及近地研究位。研究位不冒充人物实机。
5. 目视迭代后再考虑升级正式 Island；主线接入、相机后期、唯一夜空控制器、第三章宽光锥和港灯发光由 Claude 处理。

## 未完成的验收

第二版 Unity Shader、材质、模型朝向与碰撞；所有章节及真实人物/相机画面；持续 Iris Xe 1440×900 帧率、Draw Calls、WebGL 兼容和包体；与参考相同类别的完整实机并排证据。这些目前均未验证。总代码/几何检查通过不等于美术或整款游戏完成。
