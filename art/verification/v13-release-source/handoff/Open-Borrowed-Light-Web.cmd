@echo off
chcp 65001 >nul
setlocal
set "BORROWED_LIGHT_ROOT=%~dp0"
set "BORROWED_LIGHT_NODE="
if exist "D:\node\node.exe" set "BORROWED_LIGHT_NODE=D:\node\node.exe"
if not defined BORROWED_LIGHT_NODE for /f "delims=" %%N in ('where node.exe 2^>nul') do if not defined BORROWED_LIGHT_NODE set "BORROWED_LIGHT_NODE=%%N"
if not defined BORROWED_LIGHT_NODE (
  echo 没有找到 Node.js。请安装 Node.js 后重新启动借光岛。
  echo 按任意键关闭此窗口。
  pause >nul
  exit /b 1
)
if not exist "%BORROWED_LIGHT_ROOT%tools\serve-game.cjs" (
  echo 启动文件不完整：tools\serve-game.cjs
  echo 请恢复启动文件后重试。按任意键关闭此窗口。
  pause >nul
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ErrorActionPreference='Stop'; try { $gameScript=Join-Path $env:BORROWED_LIGHT_ROOT 'tools\serve-game.cjs'; $quotedScript=[char]34+$gameScript+[char]34; Start-Process -FilePath $env:BORROWED_LIGHT_NODE -ArgumentList @($quotedScript,'--open') -WorkingDirectory $env:BORROWED_LIGHT_ROOT -WindowStyle Hidden } catch { Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show(('启动借光岛失败：'+$_.Exception.Message),'借光岛') | Out-Null; exit 1 }"
exit /b %errorlevel%
