# C01–C05 实机截图（2026-10-22，Unity 6000.3.26f1 编辑器 Play，1440×900，相机直出含 UI）

主场景 `Assets/JieGuang/Scenes/JieGuang_Main.unity` 已引用真岛 `Environment/Island.prefab`（GUID a7a9419f…）。

| 文件 | 内容 |
|---|---|
| 02_title_final | 标题，真岛 + 唯一冷色地光 |
| 03/04_prologue_* | 序章栈桥送行、阿萤跪下分光（真岛） |
| 09/10_ch1_close_before/after | 第一章：晚风灯朝天（前）→ 宽罩照小路和长椅（后），近景看地面照度 |
| 11/12_ch2_window_before/after | 第二章：月窗灯朝天（前）→ 窄罩照圆窗（后），窗内阿婆可见 |
| 13_ch3_puzzle_start | 第三章开调灯 |
| 14/15_ch3_close_before/after | 第三章按 3→D→2→D→空格→1→空格 解开前后 |
| 16_ch3_after_seaside | 第三章解开后从海侧看：码头中段被月窗灯宽光照到 |
| 17_ch3_moonlamp_narrow_seaside | 对照：月窗灯换窄罩只照码头 |
| 18/19_post_on/off | 后期开/关 A/B（同机位） |
| 21_earth_phase_0.3/0.08/0.01 | 地球圆缺：序章约三分之一、第一夜细弧、第三夜几乎看不见 |
| diagnostics/ | 调试过程图（修正前偏暗的标题、灯光强度排查、地球方框问题等），不代表最终效果 |

光锥数值核对（Play 中计算）：每个被照目标都在光锥内，边距 ≥ 8°（要求 ≥ 5°），距离 ≤ 8.7 m（灯光范围 20 m）。
未验证：持续帧率、WebGL、Iris Xe；第四章以后的完整流程本轮未跑。
