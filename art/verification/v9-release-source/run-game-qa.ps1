param(
    [string]$RunName = 'run-001',
    [string]$PlayerPath = 'builds\windows\BorrowedLight.exe',
    [string]$BuildId = '',
    [ValidateSet('Tour', 'PortraitCompare', 'FaceStudy', 'FaceEyeStudy', 'GroundStudy')][string]$Mode = 'Tour'
)
$ErrorActionPreference = 'Stop'
$taskRootPath = Split-Path -Parent $PSScriptRoot
$taskGamePath = if ([System.IO.Path]::IsPathRooted($PlayerPath)) { $PlayerPath } else { Join-Path $taskRootPath $PlayerPath }
if (-not (Test-Path -LiteralPath $taskGamePath)) { throw 'Build the Windows player first.' }
$taskOutputPath = Join-Path $taskRootPath ('art\verification\' + $RunName)
New-Item -ItemType Directory -Path $taskOutputPath -Force | Out-Null
$taskLogPath = Join-Path $taskOutputPath 'player.log'
$taskPlayerDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($taskGamePath))
$taskBinaryFiles = @('BorrowedLight.exe', 'UnityPlayer.dll', 'BorrowedLight_Data\resources.assets', 'BorrowedLight_Data\Managed\Assembly-CSharp.dll')
$taskBinaryEvidence = foreach ($taskBinaryName in $taskBinaryFiles) { [ordered]@{ name=$taskBinaryName.Replace('\','/'); sha256=(Get-FileHash -LiteralPath (Join-Path $taskPlayerDirectory $taskBinaryName) -Algorithm SHA256).Hash } }
$taskEvidence = [ordered]@{ buildId=$BuildId; playerDirectory=$taskPlayerDirectory; capturedBeforeLaunchUtc=[DateTime]::UtcNow.ToString('o'); files=@($taskBinaryEvidence); scope='Read-only hashes of the player files immediately before launching this QA session. Runtime acceptance is recorded separately.' }
[IO.File]::WriteAllText((Join-Path $taskOutputPath 'build-evidence.json'), ($taskEvidence | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
$taskModeArgument = switch ($Mode) { 'PortraitCompare' { '-borrowedLightPortraitCompare' } 'FaceStudy' { '-borrowedLightFaceStudy' } 'FaceEyeStudy' { '-borrowedLightFaceEyeStudy' } 'GroundStudy' { '-borrowedLightGroundStudy' } default { '-borrowedLightQA' } }
$taskProcess = Start-Process -FilePath $taskGamePath -ArgumentList @($taskModeArgument, ('"' + $taskOutputPath + '"'), '-screen-fullscreen', '0', '-screen-width', '1440', '-screen-height', '900', '-logFile', ('"' + $taskLogPath + '"')) -PassThru
[pscustomobject]@{ProcessId=$taskProcess.Id;Output=$taskOutputPath;Log=$taskLogPath} | ConvertTo-Json
