# 栈桥与长椅整合器只读代码复核

结论：**本轮未发现确定的接入阻塞。** 可继续由 root 接入候选流程，实际 Unity 导入、执行和场景验收仍未完成。本复核没有运行 Unity、没有改 helper/CandidateBuilder，也没有重复编译；作者先前报告的联合编译结果不是本复核亲自执行的结果。

审阅文件：`art/generated/env-v2/staging/Editor/EnvV2PierBenchBuilder.cs`，SHA256 `EEF78C6E5EFAF2FD8658746D59E39ED776B3ABB048BA05D1F37FFBFA4D1242BD`。已通读完整文件，并核对当前离线两份 FBX 和木纹文件哈希与代码常量一致。

## 矩阵、绕序与法线

第 115–125 行的变换为：

`旧Structure.worldToLocal × 旧Marker.localToWorld × 新Marker.worldToLocal × 新Structure.localToWorld`

它把新 Mesh 局部点经完整新 Marker 坐标架对齐到旧 Marker，再转入旧 Structure 局部空间。包含旋转、尺度和反射，不是只比较位置或 forward。栈桥同时复算 Entry/Exit 两个完整 Marker 矩阵，避免只对齐一端却把另一端偏移。长椅只有一个座位 Marker，后续逐面几何匹配补充约束。

第 256–277 行以逆转置矩阵变换法线，负行列式时交换每个三角形的后两个索引，逻辑正确；新 UV0 对应的 tangent 会重算。第 279–318 行把新旧点转到同一个旧 Structure 的世界矩阵后双向比较；法线比较在共同的旧 Structure 局部坐标中进行，坐标系一致。每材质槽内按有向三角形逐个一对一匹配，只允许循环顶点旋转，保留重复面的数量，能够拒绝翻面、跨槽重分配和缺面。它没有依赖 FBX 顶点索引不变。

## 修改范围与碰撞

第 80–94、201–235 行限定原 `Pier/PierDeck_01..03` 和 `Props/Bench` 四实例，并校验原位置、模型 GUID、层级、槽名、Collider、活动状态、Renderer 数量等；拒绝已有属性块和重复接入。全岛旧模型 GUID 数量要求为 3 个 pier_module、1 个 bench、0 个 pier_end；第 131 行锁定 `3×456+324=1692` 三角面。

第 149 行仅给这四个原 MeshFilter/Renderer 换网格和材质引用，没有新增/删除 Transform、Collider 或 Renderer。原三个栈桥 BoxCollider 保留。长椅要求 MeshCollider 原本指向旧视觉 Mesh，替换后明确仍指向旧 `originalMesh`；没有把新 UV 网格赋给碰撞，避免无必要的 Collider 重烹。

`ProtectedState`（第 338 行起）保存全部 Transform/组件身份，以及 Collider、Renderer、MeshFilter 的序列化状态，只豁免四个目标的 Mesh 和 Materials 字段。碰撞与锚点记录也在提交后逐项比较；旧模型内存内容哈希与原磁盘文件哈希再次核对。对于本轮限定的四处材质/UV替换，保护范围合理。

## 材质、来源和输出路径

`MakeWoodMaterials` 第 319–335 行新建四个独立的 URP Lit 木材材质，共享原木纹。颜色、Roughness 转 Smoothness、Opaque、Metallic=0、关闭 emission/normal/alpha clip 的映射明确；原铁件槽直接保留旧材质引用。不会改房屋等旧共享木材。

`LoadSource` 第 237–254 行只加载两条固定 Environment/ModelsV2 路径，验证候选文件 SHA、可读性、无自动碰撞/动画、静态单 Structure 及所需 Marker。实读离线源文件 SHA 与常量一致：

- pier_module FBX：`1155f4cfa54dea293089377ba08df626596a1aec26a35712c176d279cbd6465f`
- bench FBX：`c5bb3190f178f1b217cdcbc888b329bf8654c78330b7a564cab6f585251f194e`
- wood_albedo_v1.png：`2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1`

来源几何哈希在报告中明确只作 Blender manifest 参考，没有冒充 Unity 重排后的顶点缓冲哈希。`OwnedPath` 第 422–434 行限制 Environment 前缀、拒绝相对越界/盘符/控制字符等，复核绝对路径及目录链的 reparse point；输出放在独立时间戳+随机后缀的 Generated 子目录，不覆盖原模型或旧材质。

## 异常与执行边界

第 379 行起要求 Editor 空闲、非 Play/编译/导入中，Island 位于已加载的未保存临时场景，根为 identity、无 Prefab 实例/Prefab Mode。helper 没有打开/关闭/切换/保存场景，也没有修改全局渲染设置或 importer；Unity 独占权和主场景 dirty/active 状态仍由调用者的场景保护负责。

先完成全部几何预检，再创建独立材质/网格并交换引用。第 185–198 行异常路径尽量恢复四个原 Mesh/Materials 引用，销毁尚未成为持久资产的临时网格。它**不是完整资产事务回滚**：失败时可残留本次独立 Generated 资产，调用者必须丢弃该临时候选场景；这一限制已经在代码文档中明确，不应把异常场景继续保存为成功候选。

后续 Unity 验收仍要实际检查四处引用交换、Box/MeshCollider 引用保持、Marker 姿态、UV/mipmap/重复纹理、走桥和坐椅。严格的旧 GUID/层级/面匹配若不满足会主动拒绝，不能删掉保护条件来强行通过。未得出视觉优于基线、正常玩法已验证、帧率或 WebGL 通过结论。
