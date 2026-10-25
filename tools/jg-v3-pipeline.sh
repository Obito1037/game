#!/usr/bin/env bash
# v3 local pipeline: rebuild island + main scene, build Windows, run the automated seven-chapter
# flow (frame timing) and the passive flicker probe. Usage: bash tools/jg-v3-pipeline.sh <tag>
set -u
cd /c/Users/20665/Desktop/game
source tools/jg-qa.sh
TAG=${1:-r1}
wait_idle() { for i in $(seq 1 60); do r=$($U cmd eval --result-only -- 'return UnityEditor.EditorApplication.isCompiling+" "+UnityEditor.EditorApplication.isUpdating;' 2>&1 | grep -o '"result": *"[^"]*"'); case "$r" in *"False False"*) return 0;; esac; sleep 8; done; }
echo "== recompile"; recomp
echo "== island";  $U cmd eval --result-only -- 'JieGuang.EditorTools.IslandV2Builder.Build(); return 1;' >/dev/null 2>&1; wait_idle; grep shore GameProject/Assets/JieGuang/World/IslandV2-build-report.txt
echo "== scene";   $U cmd eval --result-only -- 'JieGuang.EditorTools.JieGuangSceneBuilder.Build(); return 1;' >/dev/null 2>&1; sleep 20; wait_idle
OUTB=builds/candidates/jieguang-v3-$TAG/windows
rm -rf "$OUTB"; mkdir -p "$OUTB"
echo "== build"
$U cmd build --target StandaloneWindows64 --outputPath "C:/Users/20665/Desktop/game/$OUTB/JieGuang.exe" --confirm true 2>&1 | grep -o 'build_[a-z0-9]*' | head -1
sleep 60
for i in $(seq 1 80); do r=$($U cmd build_status --result-only 2>&1 | grep -o '"status": *"[a-z]*"\|"result": *"[A-Za-z]*"\|"totalErrors": *[0-9]*' | head -3 | tr '\n' ' '); case "$r" in *completed*) echo "$r"; break;; esac; sleep 15; done
$U cmd build_status --result-only > "art/verification/game-v3-windows-$TAG-build.json" 2>&1
echo "== qa"
QA="art/verification/game-v3-native-$TAG-full"; rm -rf "$QA"; mkdir -p "$QA"
QAW=$(cygpath -w "$PWD/$QA")
timeout 1500 "$OUTB/JieGuang.exe" -screen-fullscreen 0 -screen-width 1600 -screen-height 900 -logFile "$QAW\\Player.log" --jg-qa --jg-qa-out "$QAW" >/dev/null 2>&1
python -I -c "
import json,sys; r=json.load(open(sys.argv[1],encoding='utf-8'))
print(r['status'], r['completedChapters'], 'errors', len(r['errors']), 'saveRestored', r['saveRestored'])
for f in r['frames']: print(f['scope'][:10], 'fps',round(f['meanFps'],1), 'p95',round(f['p95Ms'],1), 'cpu',round(f['cpuMainP50Ms'],1), 'gpu',round(f['gpuP50Ms'],1), 'scale',round(f['renderScaleMean'],2))" "$QA/qa-report.json"
echo "== flicker"
FL="art/verification/game-v3-flicker-$TAG"; rm -rf "$FL"; mkdir -p "$FL"
python -I 'C:\Users\20665\AppData\Local\Temp\claude\C--Users-20665-Desktop-game\48a43e10-50a8-49f7-99de-c617ce0843e8\scratchpad\probe\flicker_probe.py' "$(cygpath -w "$PWD/$OUTB/JieGuang.exe")" "$(cygpath -w "$PWD/$FL")" 150 2>&1 | grep -v Deprec
echo "== done"
