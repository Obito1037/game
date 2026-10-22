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
- Borrowed Light v13 is built for Windows x64 and WebGL. Final native QA: `art/verification/run-033-v13/`; normal browser QA: `art/verification/web-014-v13/`. Launchers remain local; no public deployment. Fixed tree studies and short performance samples do not establish overall superiority over the reference.
- Game revision v13 uses frozen `art/generated/world-v12/` (538118 triangles, derived from world-v10), character-v9, stone-v10 and retained ground-v12. Keep world-v10/v8/v7/v6 and character-v5/v6/v7/v8/v9 dependencies. Only three tree meshes changed; 26 non-target meshes, 14 anchors, material slots and world textures are preserved. Rejected world-v11 and prior v12 releases remain archived.
- v13 changes three tree meshes and adds opt-in TreeStudy diagnostics in WorldDirector/WorldMaterialStudy. The complete 91-file v12 source/resource baseline allows only those two diagnostic source changes; normal WorldDirector equals baseline after removing the single TreeStudy entry. Ground detail .35 / tile 1.8m / normal .22, stone, grass, character and gameplay remain from v12. Low 39 trunk/root components are preserved, but upper tree collider geometry changes; no dedicated all-tree collision or all-pose test is claimed.
- User handoff: `setup/NEXT-STEPS.zh-CN.txt`. Local launchers are in the workspace root.

- v9 fixes normalized Input System scroll sensitivity (.004 to .35 metres per step, distance clamp 2.5–10). Native QA tests positive/reverse normalized steps; actual Web mouse recording verifies accessible near framing. Earlier failed captures and pre-fix builds remain historical evidence. `tools/run-game-qa.ps1` accepts `-BuildId`, candidate `-PlayerPath`, and opt-in Tour/PortraitCompare/FaceStudy/FaceEyeStudy/GroundStudy modes.

- v10 local studies are opt-in `StoneStudy`, `FoliageStudy` and `SilhouetteStudy` modes in `tools/run-game-qa.ps1`. These are frozen diagnostics and do not represent normal gameplay or FPS measurements.

- `tools/run-game-qa.ps1 -Fullscreen` requests 1440x900 fullscreen for comparable native captures. Record actual PNG sizes; a requested size alone does not establish rendering conditions. v11 source/evidence snapshots are in `art/verification/v11-release-source/`.

- v12 source/evidence snapshots: `art/verification/v12-release-source/`. Source status distinguishes tracked unchanged/modified, intended additions and previously unbaselined files; do not infer all game code stayed unchanged.

- v13 source/evidence snapshots: `art/verification/v13-release-source/`. Five fixed tree views are limited static evidence; prior gait videos do not verify this revision. No isolated tree performance A/B/A or sustained minimum FPS claim.

- Working project now contains the v14 character candidate: `art/generated/character-v11/`, 81968 authored / 81964 Unity triangles. Stable launchers/builds/ZIP stay v13; `Open-Borrowed-Light-Character-Candidate.cmd` opens the independently tested Windows candidate. See `art/verification/v14-work-in-progress.json` and `visual-review-v14-character.html`. New FaceLightStudy is opt-in; its raised-light candidate was rejected. The later normal-light balance is documented below. Continue improving face rendering before release promotion; no v14 WebGL or release ZIP exists.

- Latest v14 candidate now uses softer carried light (.18, previously .52) and neutral face fill RGB (1,.95,.88), with its original intensity/position. Native build `build_4c8f842d85ef`, `builds/candidates/v14-balanced-light/windows/`, normal QA `run-035-v14/` passed; the character candidate launcher points there. Earlier v14 original-light images/builds remain historical. Opt-in FaceContributionStudy and FaceBalanceStudy replay the original .52/warm-fill baseline and isolate contributions; main shadows and SSAO stay enabled in normal play. Character-v12 and character-v13 nose/mouth experiments are rejected and were never imported; their decision.json and all preview/source files are retained. Unity still uses character-v11. Fixed face baseline under accepted lights is `art/verification/v14-lower-face-baseline/`.

- Latest user direction after personal playtest (2026-10-21): the game is reasonably enjoyable, but the character is explicitly rejected as unattractive and far below the reference; the main story lacks appeal. The user requires socialist core values and emotional/spiritual strength, and requested a complete creative questionnaire before further production. Thirty-eight questions have been asked; answers are pending in `art/design/redesign-brief.json`. Wait for the user's answers before choosing or implementing the redesign. Preserve the current playable build. Do not substitute further eye/blink micro-adjustments for the requested character and narrative redesign, and do not treat silence as agreement. The original overall quality goal remains unachieved.
