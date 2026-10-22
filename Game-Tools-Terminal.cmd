@echo off
set "PATH=%~dp0tools\unity-cli\bin;%~dp0tools\blender-4.5.14-windows-x64;%PATH%"
cd /d "%~dp0"
echo Game tools: unity --help / blender --help
echo Project: GameProject
powershell.exe -NoLogo -NoExit
