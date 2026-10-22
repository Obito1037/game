@echo off
cd /d "%~dp0"
if exist "builds\windows\BorrowedLight.exe" (
  start "Borrowed Light" "builds\windows\BorrowedLight.exe" -screen-fullscreen 0 -screen-width 1440 -screen-height 900
) else (
  echo The game is not built yet. Open GameProject and use Borrowed Light / Build Windows Game.
  pause
)
