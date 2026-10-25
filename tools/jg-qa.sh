# helpers for driving the Unity editor
U=/c/Users/20665/Desktop/game/tools/unity-cli/bin/unity.exe
OUTDIR=${OUTDIR:-/c/Users/20665/Desktop/game/art/verification/game-v2}
mkdir -p $OUTDIR
cap(){ $U cmd capture_game_view --json --save_path "Temp/jg/$1.png" --source screen --width 1600 --height 900 >/dev/null 2>&1; sleep 1; mv /c/Users/20665/Desktop/game/GameProject/Assets/Temp/jg/$1.png $OUTDIR/ 2>/dev/null; rm -f /c/Users/20665/Desktop/game/GameProject/Assets/Temp/jg/$1.png.meta; echo "cap $1"; }
key(){ $U cmd simulate_key --json --key "$1" ${2:+--action $2} 2>&1 | grep -E '"success"' | head -1; }
ev(){ $U cmd eval --result-only -- "$1" 2>&1 | grep -E '"result"|"error|message' | head -3; }
errs(){ $U cmd console --level error --tail 20 2>&1 | grep -o '"message":"[^"]\{0,300\}' | grep -v "api/commands\|api/exec\|headers are sent" | sort -u | head -15; }
uicam(){ ev 'var c=UnityEngine.GameObject.Find("UI").GetComponent<UnityEngine.Canvas>(); c.renderMode=UnityEngine.RenderMode.ScreenSpaceCamera; c.worldCamera=UnityEngine.Camera.main; c.planeDistance=0.5f; return "ok";' >/dev/null; }
capc(){ uicam; $U cmd capture_game_view --json --save_path "Temp/jg/$1.png" --source camera --width 1600 --height 900 >/dev/null 2>&1; sleep 1; mv /c/Users/20665/Desktop/game/GameProject/Assets/Temp/jg/$1.png $OUTDIR/ 2>/dev/null; rm -f /c/Users/20665/Desktop/game/GameProject/Assets/Temp/jg/*.meta; echo "cap $1"; }
recomp(){ $U cmd recompile --json >/dev/null 2>&1; sleep 12; for i in $(seq 1 30); do s=$($U cmd recompile_status --result-only 2>&1 | grep -o '"status": *"[a-z_]*"'); case "$s" in *completed*|*up_to_date*) break;; esac; sleep 4; done; echo $s; }
play(){ $U cmd clear_console --json >/dev/null; $U cmd editor_play --json >/dev/null; sleep ${1:-12}; }
stop(){ $U cmd editor_stop --json >/dev/null; sleep 3; }
press(){ for k in "$@"; do $U cmd eval --result-only -- "JieGuang.GameInput.Queue(UnityEngine.InputSystem.Key.$k); return 1;" >/dev/null 2>&1; sleep 0.4; done; }
state(){ ev 'var d=UnityEngine.Object.FindFirstObjectByType<JieGuang.GameDirector>(); var t=UnityEngine.GameObject.Find("Line"); var o=UnityEngine.GameObject.Find("Objective"); return d.Current+" | line="+(t!=null&&t.activeInHierarchy?t.GetComponent<UnityEngine.UI.Text>().text:"-")+" | obj="+(o!=null?o.GetComponent<UnityEngine.UI.Text>().text:"");'; }
tpnear(){ ev "var p=UnityEngine.Object.FindFirstObjectByType<JieGuang.PlayerController>(); var t=UnityEngine.GameObject.Find(\"$1\").transform; var pos=t.position+new UnityEngine.Vector3($2f,0,$3f); p.Teleport(pos, 0); return pos.ToString();"; }
# UI capture without post-processing so colours match the overlay the player sees
capu(){ ev 'UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(UnityEngine.Camera.main).renderPostProcessing=false; return 1;' >/dev/null; sleep 0.5; capc $1; ev 'UnityEngine.Rendering.Universal.CameraExtensions.GetUniversalAdditionalCameraData(UnityEngine.Camera.main).renderPostProcessing=true; return 1;' >/dev/null; }
shot(){ ev "var c=UnityEngine.Object.FindFirstObjectByType<JieGuang.CameraDirector>(); c.ShotLookAt(new UnityEngine.Vector3($1), new UnityEngine.Vector3($2), 50f); return 1;" >/dev/null; sleep 1.5; }
