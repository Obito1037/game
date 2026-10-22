借光岛 v8 发布来源快照 · 2026-10-21

已通过验证的构建：Windows build_95baec27b2f5；Web build_6a2cf444c9a6。
Windows 回退包：builds/archive/BorrowedLight-v8-Windows.zip。
ZIP SHA256：B2A148EA864AF993C55DCD361EE157D8FDE8A91ABD5CC9B94BF984A2E50A0C2F。
正常运行证据：../run-022-v8/ 与 ../web-008-v8/；实际动作：../web-v8-observatory-video/。
面部补光对照：../v8-portrait-light-compare/，比较后保留原强度 0.23。

此目录保存本轮相关运行源码、shader、构建器、模型导入 meta 和最终说明/清单。
source-files.json 记录 12 个原始项目文件及其 SHA256。HTML 使用上一级 verification 目录为相对链接基准。
角色源模型为 art/generated/character-v7/；岛屿为 art/generated/world-v7/。这些已冻结目录不重复拷贝。
复现脚本依赖完整的 character-v6、character-v5、world-v6 源目录、清单与纹理；必须保留。

本轮减少两袖的重复勒痕，增加四石的宽断面，使用 Hero 专属低幅凹凸；没有新增关卡或改变核心规则。
原生功能检查、16 个岩石方向探测及正常 Web 验收通过。录像只覆盖一条后视上阶路线，精细袖褶由近景图判断。
短时帧率与停步后的网页指标不是全程帧率或单项优化收益；未复测 v8 GPU draw profile。
人物、衣料与岩石自然度仍有差距，“比参考更惊艳”的整体目标尚未达到。
