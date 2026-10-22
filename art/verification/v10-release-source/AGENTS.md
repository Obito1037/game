# Local game development tools

- Answer this project's user in Chinese.
- Unity project: `GameProject/`, Unity 6.3 LTS `6000.3.26f1`, official URP 3D template.
- Unity CLI: `tools/unity-cli/bin/unity.exe`, version `1.0.0-beta.13` (experimental).
- Blender: `tools/blender-4.5.14-windows-x64/blender.exe`, version `4.5.14 LTS`; includes Python and background CLI. Configuration is portable.
- Use full executable paths if this chat's inherited PATH has not refreshed.
- Unity's official `com.unity.pipeline` package is pinned to `0.8.0-exp.1` in `GameProject/Packages/manifest.json`. It is experimental and distinct from the rendering pipeline.
- Input System is pinned to `1.20.1`, the official released version for Unity 6.3. The template's original `1.12.0` failed compilation because it referenced the removed `BuildTarget.ReservedCFE` enum member.
- Global Codex MCP server `unity` runs the official Unity CLI's `mcp --project-path` for this project. A fresh chat/application reload may be necessary to load it.
- Before live Unity operations, check `unity status --json` and `unity pipeline list --json`. A prepared manifest or configured MCP server alone does not prove the Editor is connected.
- The Unity account is now signed in, and the Editor successfully resolved its license entitlements during startup. Recheck current runtime state before operations; do not infer lack of a license from a failed CLI licensing-client query alone.
- `Open-GameProject.cmd` uses `setup/Open-GameProject.ps1` to pass the existing Windows proxy to Unity Package Manager and bypass proxying for localhost. This fixes package download timeouts without changing persistent system proxy settings. Use this launcher when reopening the project.
- Auto-Rig Pro was not found during verification. Do not claim it is available. Tripo and Mixamo are web services; their account access was not configured by this setup.
- Blender smoke verification: `blender --background --factory-startup --python-exit-code 1 --python setup/verify_blender.py`; outputs are in `setup/verification/`.
- Live MCP verification: `node setup/verify_unity_mcp.mjs --verify-editor` performs a read-only Editor version query. This passed with 160 discovered tools and Unity `6000.3.26f1`. Keep the Editor open for MCP use.
- Borrowed Light v10 is built for Windows x64 and WebGL. Native QA: `art/verification/run-025-v10/`; normal browser QA: `art/verification/web-011-v10/`; real-input motion evidence: `art/verification/web-v10-gait-video/`. Build identities, reviewed frames and limits are recorded per session. Launchers remain `Open-Borrowed-Light.cmd` and `Open-Borrowed-Light-Web.cmd`; localhost only. Overall visual superiority over the reference is not yet established.
- Game revision v10 uses frozen `art/generated/world-v7/` and `art/generated/character-v9/`, plus generated stone texture `art/generated/stone-v10/`. Keep the world-v6 and character-v5/v6/v7/v8 dependency chain. The seven changed silhouette meshes pass FBX/GLB pose/normal checks, with 55 non-target meshes and protected connections retained. The inherited v8 GLB zero-area-endpoint limitation is not erased by the scoped v9 checks. Runtime uses FBX. Prior v9 Windows/Web artifacts are archived.
- v10 retains face fill 0.23, night lights, ground textures and AO settings. Hero rocks use the original generated triplanar texture; foliage uses synchronized wind/depth/double-sided normals at Fixed40 (Fixed20 rejected). Character changes concern hair/sleeves/coat/trousers; face/eyes and material values are preserved. Staged A/B frames differ slightly due to unfrozen rendering effects; see `art/verification/visual-review.html`.
- User handoff: `setup/NEXT-STEPS.zh-CN.txt`. Local launchers are in the workspace root.

- v9 fixes normalized Input System scroll sensitivity (.004 to .35 metres per step, distance clamp 2.5–10). Native QA tests positive/reverse normalized steps; actual Web mouse recording verifies accessible near framing. Earlier failed captures and pre-fix builds remain historical evidence. `tools/run-game-qa.ps1` accepts `-BuildId`, candidate `-PlayerPath`, and opt-in Tour/PortraitCompare/FaceStudy/FaceEyeStudy/GroundStudy modes.

- v10 local studies are opt-in `StoneStudy`, `FoliageStudy` and `SilhouetteStudy` modes in `tools/run-game-qa.ps1`. These are frozen diagnostics and do not represent normal gameplay or FPS measurements.
