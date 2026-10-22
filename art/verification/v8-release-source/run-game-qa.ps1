param(
    [string]$RunName = 'run-001',
    [string]$PlayerPath = 'builds\windows\BorrowedLight.exe',
    [ValidateSet('Tour', 'PortraitCompare')][string]$Mode = 'Tour'
)
$ErrorActionPreference = 'Stop'
$taskRootPath = Split-Path -Parent $PSScriptRoot
$taskGamePath = if ([System.IO.Path]::IsPathRooted($PlayerPath)) { $PlayerPath } else { Join-Path $taskRootPath $PlayerPath }
if (-not (Test-Path -LiteralPath $taskGamePath)) { throw 'Build the Windows player first.' }
$taskOutputPath = Join-Path $taskRootPath ('art\verification\' + $RunName)
New-Item -ItemType Directory -Path $taskOutputPath -Force | Out-Null
$taskLogPath = Join-Path $taskOutputPath 'player.log'
$taskModeArgument = if ($Mode -eq 'PortraitCompare') { '-borrowedLightPortraitCompare' } else { '-borrowedLightQA' }
$taskProcess = Start-Process -FilePath $taskGamePath -ArgumentList @($taskModeArgument, ('"' + $taskOutputPath + '"'), '-screen-fullscreen', '0', '-screen-width', '1440', '-screen-height', '900', '-logFile', ('"' + $taskLogPath + '"')) -PassThru
[pscustomobject]@{ProcessId=$taskProcess.Id;Output=$taskOutputPath;Log=$taskLogPath} | ConvertTo-Json
