$ErrorActionPreference = 'Stop'
$taskRootPath = Split-Path -Parent $PSScriptRoot
$taskPlayerDirectory = Join-Path $taskRootPath 'builds\windows'
if (-not (Test-Path -LiteralPath (Join-Path $taskPlayerDirectory 'BorrowedLight.exe'))) { throw 'Build the native game before packaging.' }
$taskPackageFiles = Get-ChildItem -LiteralPath $taskPlayerDirectory | Where-Object { $_.Name -notmatch 'DoNotShip|BackUpThisFolder' }
$taskZipPath = Join-Path $taskRootPath 'builds\BorrowedLight-Windows.zip'
Compress-Archive -LiteralPath $taskPackageFiles.FullName -DestinationPath $taskZipPath -Force
Get-Item -LiteralPath $taskZipPath | Select-Object FullName,Length,LastWriteTime
