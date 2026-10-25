# 栈桥与长椅离线材质候选

结论：三件作为**表面升级候选**推荐给 root 进 Unity 审阅，未自动接入。只改 UV、木纹贴图和木材色/粗糙度；没有新增几何，不能声称已经做了新磨损、沉钉或倒角。现有长椅已有圆角，栈桥的几何没有必要为增加细节而重做。

## 真实基线与保持项

| 模型 | 原 / 候选三角面 | 实际实例数 | 岛内新增 |
|---|---:|---:|---:|
| pier_module | 456 / 456 | 3 | 0 |
| pier_end | 668 / 668 | 0 | 0 |
| bench | 324 / 324 | 1 | 0 |

直接读取 env-v1/props 下最新 blend，所有源文件 SHA256 在各自 source-inventory.json。栈桥桩底保留 Blender Z=-3.20 米，没有从旧函数重建短桩。所有顶点、面索引、材质槽/面索引、平滑标记、对象矩阵、Marker 父级与矩阵、整体包围盒逐值一致；只改 UV 和材质节点。桥板 Z=0、长椅座面 Z=.45 的顶点单独列出并逐值核对。

真实 prefab 接口由独立审计记录于 INTERFACE-AUDIT.zh-CN.md：栈桥 3 个独立 WalkableDeck BoxCollider 连续；长椅原 Structure 上 MeshCollider 必须保留旧 sharedMesh 和组件。Marker_Seat 是坐面位置契约，人物朝向以 NPC_Bench 为准，不能误用导入 Marker.forward。此次没有操作 Unity 或测试落座/碰撞。

## 表面实现与局限

复用原创新木纹 env-v2/textures/wood_albedo_v1.png，真实 1254×1254，SHA256 2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1。未改图像像素。每个独立木件按 PCA 长轴定向，V 沿木长，U=1 米、V=4.9 米；使用图内 V 范围避免有问题的纵向平铺边。端面用同图局部平面投影，**没有专用年轮、法线或粗糙度图**。已 pack 原图进候选 blend。FBX 不保证携带 Blender 的乘色节点，Unity 应显式用下表原图×颜色及 roughness 转 smoothness。

| 原槽名 | 建议共享名 | Base tint RGB | Roughness / Unity smoothness |
|---|---|---|---|
| Wood_Endgrain | CoastalWood_Light | .62, .57, .46 | .88 / .12 |
| Wood_Honey | CoastalWood_Brown | .48, .42, .33 | .87 / .13 |
| Wood_DarkBeams | CoastalWood_Dark | .26, .22, .17 | .90 / .10 |
| Wood_Weathered | CoastalWood_Silver | .38, .38, .32 | .92 / .08 |

Wood_Endgrain 是历史槽名，实际也包含整块木板，不应按名字给整块木板改年轮。Iron_Blackened 原材质不改。这里四共享名不同于屋子的四木色；既有 HouseSurfaceBuilder 没有 Wood_Weathered，不能假定调用屋材映射就覆盖栈桥。该轮没有新增 C# 或指定未经验证的整合入口。

## 目视判断

实际查看所有三件的中性/夜间、全景/表面前后 PNG：板面与靠背木纹顺长轴，桥桩和腿部顺竖向；暖灯下木材可读性比原纯色块明确，未观察到新黑缝、共面闪黑或轮廓变化。长椅原有圆角、薄靠背和腿部结构保持。末端平台仅离线准备，不能说它已经改善了岛上的码头。

独立环境审阅代理还检查了 pier_module 四张 surface 图，确认方向正确、未见突兀接缝，建议不加面。保留意见：木纹较细且平行，夜图中部深纹会与真实板缝竞争，中性木色偏新；桩顶是平行木纹而非年轮。当前单件镜头不证明三段重复、mipmap 或中远景闪烁已验证。

## 证据与接入前事项

每款 8 张真实 900×900 Cycles 渲染，总计 24 张；同款 before/after 使用相同相机、世界、灯光和曝光。2 个视角不是完整后方/底面全覆盖；无新增几何，源有结构缺陷如需修复应另立变更，不能据此声称无所有缺陷。

fresh-process-verification.json 从新 Blender 进程重开原 blend / 候选 blend，再导入导出 FBX；核对完整几何合同、packed 原图、三角面、原槽、所有根/Marker 矩阵、双向顶点集合与 UV 角点集合。最大误差记在报告中；没有把请求尺寸当实际 PNG 尺寸。final-verification.json 另核对文件 SHA、源文件/纹理未变与 24 张 PNG 尺寸。

root 后续若采用，应只换视觉 MeshFilter 与材料，保留旧长椅 MeshCollider sharedMesh；不要 SetActive(false) 整个带碰撞的 Structure。桥界、3 个 WalkableDeck、NPC_Bench、全岛锚点保持；检查三段板纹重复/过滤、灯下是否过亮、角色坐面和通行。无 Unity/FPS/全岛最终质量结论。

文件路径：`art/generated/env-v2/pier-bench/{pier_module|pier_end|bench}/{asset}_v2_candidate.blend/.fbx`；生成脚本 `art/blender/env_v2_pier_bench.py`。未修改 Assets、旧 v1、Claude 文件、总 HANDOFF 或 CandidateBuilder。
