param([string]$OutputName = 'package-verification.json')
$ErrorActionPreference = 'Stop'
$taskRootPath = Split-Path -Parent $PSScriptRoot
$taskPlayerPath = [IO.Path]::GetFullPath((Join-Path $taskRootPath 'builds\windows'))
$taskZipPath = Join-Path $taskRootPath 'builds\BorrowedLight-Windows.zip'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskZip = [IO.Compression.ZipFile]::OpenRead($taskZipPath)
$taskHasher = [Security.Cryptography.SHA256]::Create()
$taskCompared = 0
$taskFailures = [Collections.Generic.List[string]]::new()
$taskRequired = @('BorrowedLight.exe', 'UnityPlayer.dll', 'BorrowedLight_Data/resources.assets', 'BorrowedLight_Data/Managed/Assembly-CSharp.dll', 'PLAY.zh-CN.txt', 'AI-使用与素材来源.zh-CN.txt', 'OFL-NotoSerifCJK.txt', 'FONT-SUBSET-NOTICE.txt', '主题依据.zh-CN.txt')
try {
    $taskNames = @($taskZip.Entries | ForEach-Object { $_.FullName.Replace('\','/') })
    foreach ($taskName in $taskRequired) { if ($taskName -notin $taskNames) { $taskFailures.Add('Missing required entry: ' + $taskName) } }
    $taskExpectedFiles = @(Get-ChildItem -LiteralPath $taskPlayerPath -File -Recurse | Where-Object { $_.FullName -notmatch 'DoNotShip|BackUpThisFolder' })
    foreach ($taskFile in $taskExpectedFiles) {
        $taskExpectedName = $taskFile.FullName.Substring($taskPlayerPath.Length + 1).Replace('\','/')
        if ($taskExpectedName -notin $taskNames) { $taskFailures.Add('Built file omitted from ZIP: ' + $taskExpectedName) }
    }
    foreach ($taskEntry in $taskZip.Entries) {
        $taskRelative = $taskEntry.FullName.Replace('/', '\')
        if ($taskRelative -match 'DoNotShip|BackUpThisFolder') { $taskFailures.Add('Debug folder shipped: ' + $taskRelative) }
        if ($taskEntry.Name.Length -eq 0) { continue }
        $taskDiskPath = [IO.Path]::GetFullPath((Join-Path $taskPlayerPath $taskRelative))
        if (-not $taskDiskPath.StartsWith($taskPlayerPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected ZIP path outside player directory.' }
        if (-not (Test-Path -LiteralPath $taskDiskPath -PathType Leaf)) { $taskFailures.Add('No matching built file: ' + $taskRelative); continue }
        $taskStream = $taskEntry.Open()
        try { $taskEntryHash = [BitConverter]::ToString($taskHasher.ComputeHash($taskStream)).Replace('-', '') }
        finally { $taskStream.Dispose() }
        $taskDiskHash = (Get-FileHash -LiteralPath $taskDiskPath -Algorithm SHA256).Hash
        if ($taskEntryHash -ne $taskDiskHash) { $taskFailures.Add('Hash mismatch: ' + $taskRelative) }
        $taskCompared++
    }
    $taskResult = [ordered]@{
        passed = $taskFailures.Count -eq 0
        zipEntries = $taskZip.Entries.Count
        zipFilesHashCompared = $taskCompared
        expectedPlayerFiles = $taskExpectedFiles.Count
        requiredFilesPresent = @($taskRequired | Where-Object { $_ -notin $taskNames }).Count -eq 0
        debugFoldersExcluded = @($taskNames | Where-Object { $_ -match 'DoNotShip|BackUpThisFolder' }).Count -eq 0
        allZipFileHashesMatchCurrentBuild = $taskFailures.Count -eq 0
        zipBytes = (Get-Item -LiteralPath $taskZipPath).Length
        zipSHA256 = (Get-FileHash -LiteralPath $taskZipPath -Algorithm SHA256).Hash
        nativeResourcesSHA256 = (Get-FileHash -LiteralPath (Join-Path $taskPlayerPath 'BorrowedLight_Data\resources.assets') -Algorithm SHA256).Hash
        nativeGameAssemblySHA256 = (Get-FileHash -LiteralPath (Join-Path $taskPlayerPath 'BorrowedLight_Data\Managed\Assembly-CSharp.dll') -Algorithm SHA256).Hash
        failures = @($taskFailures)
    }
    $taskJson = $taskResult | ConvertTo-Json -Depth 5
    $taskReportPath = Join-Path $taskRootPath ('art\verification\' + $OutputName)
    [IO.File]::WriteAllText($taskReportPath, $taskJson, [Text.UTF8Encoding]::new($false))
    $taskJson
    if (-not $taskResult.passed) { throw 'Package verification failed; see report.' }
}
finally { $taskHasher.Dispose(); $taskZip.Dispose() }
