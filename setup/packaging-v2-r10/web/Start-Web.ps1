$ErrorActionPreference='Stop'
$jgNode=(Get-Command node -ErrorAction SilentlyContinue).Source
if(-not $jgNode){throw 'Node.js is required. Install Node.js or serve this folder using an HTTP server.'}
$env:BORROWED_LIGHT_BUILD_ROOT=$PSScriptRoot
$env:BORROWED_LIGHT_PORT='8767'
$jgServer=Join-Path $PSScriptRoot 'serve-game.cjs'
$jgLogs=Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Path $jgLogs -Force | Out-Null
$jgStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
Start-Process -FilePath $jgNode -ArgumentList @(('"'+$jgServer+'"'),'--open') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $jgLogs ($jgStamp+'-out.log')) -RedirectStandardError (Join-Path $jgLogs ($jgStamp+'-error.log'))
