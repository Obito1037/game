param(
    [string]$RunName = 'run-001',
    [string]$PlayerPath = 'builds\windows\BorrowedLight.exe',
    [string]$BuildId = '',
    [switch]$Fullscreen,
    [ValidateSet('Tour', 'PortraitCompare', 'FaceStudy', 'FaceEyeStudy', 'GroundStudy', 'GroundDetailStudy', 'StoneStudy', 'FoliageStudy', 'SilhouetteStudy', 'TreeStudy', 'FaceLightStudy', 'FaceContributionStudy', 'FaceBalanceStudy', 'EyeSurfaceStudy')][string]$Mode = 'Tour'
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
$taskEvidence = [ordered]@{ buildId=$BuildId; playerDirectory=$taskPlayerDirectory; capturedBeforeLaunchUtc=[DateTime]::UtcNow.ToString('o'); requestedFullscreen=[bool]$Fullscreen; requestedWidth=1440; requestedHeight=900; mode=$Mode; files=@($taskBinaryEvidence); scope='Read-only hashes and requested display settings immediately before launching this QA session. Actual image dimensions and runtime acceptance are recorded separately.' }
[IO.File]::WriteAllText((Join-Path $taskOutputPath 'build-evidence.json'), ($taskEvidence | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
$taskModeArgument = switch ($Mode) { 'PortraitCompare' { '-borrowedLightPortraitCompare' } 'FaceStudy' { '-borrowedLightFaceStudy' } 'FaceEyeStudy' { '-borrowedLightFaceEyeStudy' } 'GroundStudy' { '-borrowedLightGroundStudy' } 'GroundDetailStudy' { '-borrowedLightGroundDetailStudy' } 'StoneStudy' { '-borrowedLightStoneStudy' } 'FoliageStudy' { '-borrowedLightFoliageStudy' } 'SilhouetteStudy' { '-borrowedLightSilhouetteStudy' } 'TreeStudy' { '-borrowedLightTreeStudy' } 'FaceLightStudy' { '-borrowedLightFaceLightStudy' } 'FaceContributionStudy' { '-borrowedLightFaceContributionStudy' } 'FaceBalanceStudy' { '-borrowedLightFaceBalanceStudy' } 'EyeSurfaceStudy' { '-borrowedLightEyeSurfaceStudy' } default { '-borrowedLightQA' } }
$taskFullScreenArgument = if ($Fullscreen) { '1' } else { '0' }
$taskProcess = Start-Process -FilePath $taskGamePath -ArgumentList @($taskModeArgument, ('"' + $taskOutputPath + '"'), '-screen-fullscreen', $taskFullScreenArgument, '-screen-width', '1440', '-screen-height', '900', '-logFile', ('"' + $taskLogPath + '"')) -PassThru
[pscustomobject]@{ProcessId=$taskProcess.Id;Output=$taskOutputPath;Log=$taskLogPath} | ConvertTo-Json
