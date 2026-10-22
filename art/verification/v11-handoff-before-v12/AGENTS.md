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
- Borrowed Light v11 is built for Windows x64 and WebGL. Final native QA: `art/verification/run-029-v11/`; normal browser QA: `art/verification/web-012-v11/`. Native final samples used 1440x900 fullscreen; prior v11 runs include concurrent-load and resized-window limitations. Launchers: `Open-Borrowed-Light-Fullscreen.cmd`, `Open-Borrowed-Light.cmd`, and `Open-Borrowed-Light-Web.cmd`; localhost only. Overall visual superiority over the reference is not yet established.
- Game revision v11 uses frozen `art/generated/world-v8/` (510293 triangles), `art/generated/character-v9/`, and stone-v10. Keep world-v7/world-v6 and character-v5/v6/v7/v8 dependencies. Only lavender and ferns changed in world-v8; 27 other meshes, 14 anchors, materials and textures pass same-format BLEND/FBX/GLB and Unity preservation checks. Prior character GLB endpoint limitations remain. v10 Windows/Web artifacts are archived.
- v11 retains v10 game code, shaders, materials, lights and character. The new plant shapes pass fixed path/roots/lamp review; finer purple flowers are less prominent at distance. Grass distribution and ground transitions remain unfinished. See `art/verification/visual-review.html`; the v10 gait video is historical, not a new v11 dynamic review.
- User handoff: `setup/NEXT-STEPS.zh-CN.txt`. Local launchers are in the workspace root.

- v9 fixes normalized Input System scroll sensitivity (.004 to .35 metres per step, distance clamp 2.5–10). Native QA tests positive/reverse normalized steps; actual Web mouse recording verifies accessible near framing. Earlier failed captures and pre-fix builds remain historical evidence. `tools/run-game-qa.ps1` accepts `-BuildId`, candidate `-PlayerPath`, and opt-in Tour/PortraitCompare/FaceStudy/FaceEyeStudy/GroundStudy modes.

- v10 local studies are opt-in `StoneStudy`, `FoliageStudy` and `SilhouetteStudy` modes in `tools/run-game-qa.ps1`. These are frozen diagnostics and do not represent normal gameplay or FPS measurements.

- `tools/run-game-qa.ps1 -Fullscreen` requests 1440x900 fullscreen for comparable native captures. Record actual PNG sizes; a requested size alone does not establish rendering conditions. v11 source/evidence snapshots are in `art/verification/v11-release-source/`.
