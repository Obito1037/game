# 给 GPT-6 的追加说明（Claude 已读过 HANDOFF.zh-CN.md，2026-10-22）

> 把下面整段转给 GPT-6。

---

Claude 已读完 `art/generated/env-v1/HANDOFF.zh-CN.md`，离线成果很好。**Claude 已退出 Play 模式并停止操作 Unity，现在把 Unity 交给你**，按你交接文档里的 1–5 步执行（复制 staging → Build → Validate → Capture）。完成后告诉用户，Claude 再接回 Unity。

请在 `Island.prefab` 里**额外加 5 个空物体锚点**（名字一字不差；剧情代码会用到，缺了会退回灰盒坐标，位置就错了）：

| 锚点 | 位置要求 |
|---|---|
| `Anchor_VillageGate` | 村子台地边、石板路下坡的起点，脚底贴地；邮差爷爷从这里走下山 |
| `Anchor_GoldenTree` | 金色光树树根中心，地面高度 |
| `Anchor_Boat` | `Props/ReturningBoat` 靠岸系泊时的根位置与朝向（剧情会把船从远海移到这里） |
| `Target_Sea` | 归航灯“照向远海”时的瞄准点，栈桥外约 30 米海面上 |
| `NPC_ABo_Door` | 阿婆木屋门外的站立点，脚底贴地，面朝屋外 |

Claude 这边按你的接口已做的适配（你不需要改）：
- 座点 `NPC_Bench` / `NPC_ABo_Window` / `NPC_DengBo_Box` 当作坐面/骨盆参考点，代码会往下找地面放角色根节点；
- `LampHead` 下已有 `Spot` 时直接复用，不再新建灯；
- 小艇按名字 `ReturningBoat` 查找，港灯按 `HarborLantern` 查找并控制它下面的 Light 亮灭；
- Layer 8 / 9 按数字使用，不需要命名。

注意：Claude 的代码在 `GameProject/Assets/JieGuang/`（除 `Environment/` 外），导入时会一起编译，属于正常现象，请不要改动这些文件。Unity 里请不要进入 Play 模式运行 `JieGuang_Main.unity`，以免改动存档测试状态。

---
