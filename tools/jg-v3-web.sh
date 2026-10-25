#!/usr/bin/env bash
# v3 WebGL: switch the Editor to WebGL (and wait until it is really settled), build, serve
# locally and run the real-browser check. Usage: bash tools/jg-v3-web.sh <tag>
set -u
cd /c/Users/20665/Desktop/game
source tools/jg-qa.sh
TAG=${1:-r2}
echo "== switch to WebGL"
$U cmd switch_build_target --target WebGL --confirm true 2>&1 | grep -o '"status":"[a-z]*"' | head -1
sleep 60
for i in $(seq 1 80); do
  r=$($U cmd eval --result-only -- 'return UnityEditor.EditorUserBuildSettings.activeBuildTarget+" "+UnityEditor.EditorApplication.isCompiling+" "+UnityEditor.EditorApplication.isUpdating;' 2>&1 | grep -o '"result": *"[^"]*"')
  case "$r" in *"WebGL False False"*) echo "$r"; break;; esac
  sleep 15
done
OUTW=builds/candidates/jieguang-v3-$TAG/web
rm -rf "$OUTW"; mkdir -p "$OUTW"
echo "== build web"
$U cmd build --target WebGL --outputPath "C:/Users/20665/Desktop/game/$OUTW" --confirm true 2>&1 | grep -o 'build_[a-z0-9]*' | head -1
sleep 120
for i in $(seq 1 120); do r=$($U cmd build_status --result-only 2>&1 | grep -o '"status": *"[a-z]*"\|"result": *"[A-Za-z]*"\|"totalErrors": *[0-9]*' | head -3 | tr '\n' ' '); case "$r" in *completed*) echo "$r"; break;; esac; sleep 15; done
$U cmd build_status --result-only > "art/verification/game-v3-web-$TAG-build.json" 2>&1
ls "$OUTW" "$OUTW/Build" 2>/dev/null | head -20
echo "== serve + browser check"
BORROWED_LIGHT_PORT=8768 BORROWED_LIGHT_BUILD_ROOT="$(cygpath -w "$PWD/$OUTW")" node tools/serve-game.cjs > "art/verification/game-v3-web-$TAG-serve.log" 2>&1 &
SERVER=$!
sleep 4
WEBOUT="art/verification/game-v3-web-$TAG"; rm -rf "$WEBOUT"; mkdir -p "$WEBOUT"
node 'C:\Users\20665\AppData\Local\Temp\claude\C--Users-20665-Desktop-game\48a43e10-50a8-49f7-99de-c617ce0843e8\scratchpad\probe\web_v3_check.cjs' http://127.0.0.1:8768/ "$(cygpath -w "$PWD/$WEBOUT")" 2>&1 | tail -3
kill $SERVER 2>/dev/null
echo "== done"
