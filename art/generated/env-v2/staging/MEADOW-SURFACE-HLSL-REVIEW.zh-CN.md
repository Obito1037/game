# Meadow / TerrainSurface 离线 HLSL 复核

2026-10-22：**92 / 92 项主要分支编译成功，0 个错误、0 条编译器诊断。** 这是系统 Direct3D 编译器在内存完成的 DX11 HLSL 检查，**不是 Unity ShaderLab 导入或 WebGL / GLSL 编译通过**，没有验证实际渲染、风动、阴影外观或帧率。

本轮没有发现需要修复的确切 HLSL 编译错误，因此两个 Shader 保持上一轮修正后的内容。没有操作 Unity，也没有写入 Assets、PackageCache、ProjectSettings 或 Claude 的目录。

## 证据文件与复现

- 夹具：`verification/Invoke-EnvironmentHlslProbe.ps1`。
- 首轮基础结果：`verification/meadow-surface-smoke-before.json`，16 / 16 成功。
- 完整结果：`verification/meadow-surface-dx11.json`，92 / 92 成功；相同内容另存 `MEADOW-SURFACE-HLSL-REVIEW.json`。
- 完整轮时间：`2026-10-22T19:33:08.7506717Z`；耗时 82.342 秒。基础检查包含在完整轮之中，不把两轮相加冒充独立覆盖数。

需要 Windows 与 PowerShell 7；本次使用 PowerShell 7.6.5。从工作区根目录运行：

```powershell
pwsh -NoProfile -File "art/generated/env-v2/staging/verification/Invoke-EnvironmentHlslProbe.ps1" -SmokeOnly -ReportName "meadow-surface-smoke-before.json"
pwsh -NoProfile -File "art/generated/env-v2/staging/verification/Invoke-EnvironmentHlslProbe.ps1" -ReportName "meadow-surface-dx11.json"
```

脚本按自身位置定位项目，从本机 PackageCache 读取 include，只在自己的 `verification/` 目录写 JSON。没有调用 Editor、Unity CLI、UnityShaderCompiler.exe 或 AssetDatabase；字节码只存在内存中，记录长度后释放。失败返回退出码 1，并保留逐项诊断。

## 覆盖结果

每个“变体”分别编译 vertex 与 fragment；表中编译数是两阶段相加，不是 Unity 构建保留的变体总量。

| Shader | Pass | 变体数 | VS + PS 成功 / 失败 |
|---|---|---:|---:|
| Meadow | Forward | 12 | 24 / 0 |
| Meadow | ShadowCaster | 4 | 8 / 0 |
| Meadow | DepthOnly | 4 | 8 / 0 |
| Meadow | DepthNormals | 4 | 8 / 0 |
| TerrainSurface | Forward | 12 | 24 / 0 |
| TerrainSurface | ShadowCaster | 4 | 8 / 0 |
| TerrainSurface | DepthOnly | 2 | 4 / 0 |
| TerrainSurface | DepthNormals | 4 | 8 / 0 |

Forward 检查基础、主光单图阴影、级联阴影与附加逐像素光、screen shadow、Forward+、附加逐顶点光、GPU instancing、FOG_LINEAR / FOG_EXP / FOG_EXP2。组合项同时启用 Forward+、级联、附加阴影、软阴影、SSAO、实例化及 EXP2 雾；Meadow 同时加入 LOD crossfade，TerrainSurface 同时加入 light cookies。另分别检查 Meadow 独立 LOD crossfade 和 TerrainSurface 普通 Forward cookies。

ShadowCaster 检查方向光、点/聚光阴影、实例化和点光实例化组合；Meadow 的组合项还启用 LOD crossfade。DepthOnly 检查基础与实例化，Meadow 额外检查 LOD 与 LOD 实例化。DepthNormals 检查原始世界法线、oct 编码、实例化和 oct 实例化组合；Meadow 组合中保留 LOD。

脚本读取各 Pass 的 `#pragma vertex` / `fragment` 入口，并尊重 `multi_compile_vertex` / `multi_compile_fragment` 的阶段范围：例如 punctual 只定义在阴影 vertex，octnormals 只定义在法线 fragment。包含树叶两面法线、同风变形、草叶 density clip、地表三种运行时 SurfaceMode 分支与 derivative bump 的实际函数体，没有用替代函数伪造通过。

## 夹具边界

使用 `C:/Windows/System32/D3DCompiler_47.dll` 的 `D3DCompile`，版本 `10.0.26100.9168`。编译配置是 `SHADER_API_D3D11=1`、`SHADER_TARGET=35`、`UNITY_COMPILER_HLSL=1`，目标 `vs_4_0` / `ps_4_0`，backward compatibility 标志 4096。全部成功项 HRESULT 为 0，完整 JSON 保留每项关键词、阶段、入口、字节码长度与诊断。

这里的适配只发生在夹具内存，不能省略这些差异：

1. 原生 FXC 不解析 ShaderLab。脚本提取共享 HLSLINCLUDE 和每个 HLSLPROGRAM，剥离 Unity pragma，再按明确列出的关键词编译；不验证 Unity 的关键词生成、剔除、ShaderLab 标签与 Render State、资源绑定、SRP Batcher 或真正 GPU draw。
2. 使用实际本地 URP 17.3 / Core includes，展开时加文件保护宏。缺失的私有平台 include 留作条件分支中的 `#error`；本次 DX11 分支没有进入它们。
3. FXC 旧预处理器不接受库中的空形参声明 `#define PopMarker()`。夹具先确认展开代码没有调用它，再仅在内存改为 `#define PopMarker(unused)`；没有替换着色函数或修改磁盘库。
4. 为实际进入 URP 17.3 fragment fog 计算，在选中的静态 FOG_* 变体中手工定义相应 `FOG_*_KEYWORD_DECLARED=1`。这能检查雾函数体和类型，**不证明 Unity 导入阶段已正确生成关键词元数据**。本机 Fog config 的动态分支模式为 0；未模拟动态 fog keyword 模式。
5. 不包含 XR / stereo、DOTS、原生 16 位 half、GLSL/GLES、WebGL、shader stripping 或全平台编译。所用 DX11 half 行为与移动端精度不能直接等同。没有穷举全部关键词笛卡尔积。

下一阶段仍需由持有 Editor 权限的一方导入后查看实际 Shader 编译错误，确认 Forward / Shadow / Depth / DepthNormals 的运行选择；实际检查级联边缘、草风与深度/阴影一致、LOD 过渡和章节雾，再进行目标 WebGL 编译。这份报告不把那些待验证项标为通过。

## 文件指纹

| 文件 | SHA256 |
|---|---|
| Meadow.shader | `DAC2CDF8B0D5580C9FBB15DE91AB5E6229DD74088F197FBD6D1E69D3B96CACF0` |
| TerrainSurface.shader | `2D8037D1290794033F096B767F3A86229228979ECA909783F097CE53F553EECB` |
| Invoke-EnvironmentHlslProbe.ps1 | `260CB4A9D4B852A7026E75B49188E980FD91A6C15DECFE2998D3F1562DA717E1` |
| D3DCompiler_47.dll | `6B3DEE26A3FA46ADCE2FD1C543B0A3605C5DE16B636BD42341ADE6F1D7A27A44` |
