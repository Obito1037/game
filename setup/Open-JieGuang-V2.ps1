param([switch]$Web)
$ErrorActionPreference = 'Stop'
$jgWorkspace = Split-Path -Parent $PSScriptRoot
$jgConfigPath = Join-Path $PSScriptRoot 'jieguang-v2-candidate.json'
if (-not (Test-Path -LiteralPath $jgConfigPath)) { throw 'The candidate has not passed startup checks yet.' }
$jgConfig = Get-Content -LiteralPath $jgConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Web) {
    $jgPlayer = Join-Path $jgWorkspace $jgConfig.windowsExe
    if (-not (Test-Path -LiteralPath $jgPlayer)) { throw "Missing player: $jgPlayer" }
    Start-Process -FilePath $jgPlayer -WorkingDirectory (Split-Path -Parent $jgPlayer) -ArgumentList @('-screen-width','1600','-screen-height','900','-screen-fullscreen','0')
    exit
}
$jgWebRoot = Join-Path $jgWorkspace $jgConfig.webRoot
if (-not (Test-Path -LiteralPath (Join-Path $jgWebRoot 'index.html'))) { throw "Missing WebGL build: $jgWebRoot" }
$jgNode = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $jgNode) { throw 'Node.js is required for the local WebGL launcher.' }
$env:BORROWED_LIGHT_BUILD_ROOT = $jgWebRoot
$env:BORROWED_LIGHT_PORT = [string]$jgConfig.webPort
$jgLogs = Join-Path $jgWorkspace 'art/verification/game-v2-launcher'
New-Item -ItemType Directory -Path $jgLogs -Force | Out-Null
$jgStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
Start-Process -FilePath $jgNode -ArgumentList @('tools/serve-game.cjs','--open') -WorkingDirectory $jgWorkspace -WindowStyle Hidden -RedirectStandardOutput (Join-Path $jgLogs "$jgStamp-out.log") -RedirectStandardError (Join-Path $jgLogs "$jgStamp-error.log")
