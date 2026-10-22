$ErrorActionPreference = 'Stop'
$taskRootPath = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
function Resolve-TaskPath([string]$Relative) {
    $taskResolved = [IO.Path]::GetFullPath((Join-Path $taskRootPath $Relative))
    if (-not $taskResolved.StartsWith($taskRootPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Path is outside the game workspace.' }
    return $taskResolved
}
$taskDraftPath = Resolve-TaskPath 'art\verification\v9-release-draft'
$taskManifest = Get-Content -LiteralPath (Join-Path $taskDraftPath 'production-manifest.json') -Raw | ConvertFrom-Json
if ($taskManifest.revision -ne 'v9') { throw 'Expected reviewed v9 draft.' }
foreach ($taskEvidenceName in @('web-010-v9', 'web-v9-portrait-video')) {
    $taskIdentity = Get-Content -LiteralPath (Resolve-TaskPath ('art\verification\' + $taskEvidenceName + '\artifact-identity.json')) -Raw | ConvertFrom-Json
    if (-not $taskIdentity.passed) { throw 'Candidate byte verification has not passed.' }
    if ($taskIdentity.buildId -ne $taskManifest.buildIds.web) { throw 'Web evidence buildId does not match the release draft.' }
    foreach ($taskPayload in $taskManifest.webPayload.files) {
        $taskIdentityFile = @($taskIdentity.files | Where-Object name -eq $taskPayload.name)
        if ($taskIdentityFile.Count -ne 1 -or $taskIdentityFile[0].diskSHA256 -ne $taskPayload.sha256 -or $taskIdentityFile[0].httpSHA256 -ne $taskPayload.sha256) { throw 'Web evidence file does not match the release draft.' }
    }
}
$taskNativeEvidence = Get-Content -LiteralPath (Resolve-TaskPath 'art\verification\run-024-v9\build-evidence.json') -Raw | ConvertFrom-Json
if ($taskNativeEvidence.buildId -ne $taskManifest.buildIds.windows) { throw 'Native QA buildId does not match the release draft.' }
foreach ($taskBinary in $taskNativeEvidence.files) {
    if ((Get-FileHash -LiteralPath (Resolve-TaskPath ('builds\candidates\v9\windows\' + $taskBinary.name)) -Algorithm SHA256).Hash -ne $taskBinary.sha256) { throw 'Native candidate changed since QA launch.' }
}
foreach ($taskFile in $taskManifest.webPayload.files) {
    $taskFilePath = Resolve-TaskPath ('builds\candidates\v9\web\Build\' + $taskFile.name)
    if ((Get-FileHash -LiteralPath $taskFilePath -Algorithm SHA256).Hash -ne $taskFile.sha256) { throw 'Candidate payload changed after QA.' }
}
$taskPriorManifest = Get-Content -LiteralPath (Resolve-TaskPath 'art\production-manifest.json') -Raw | ConvertFrom-Json
if ($taskPriorManifest.revision -ne 'v8') { throw 'Expected v8 stable release before promotion.' }
$taskPriorZip = Resolve-TaskPath 'builds\BorrowedLight-Windows.zip'
$taskPriorArchiveZip = Resolve-TaskPath 'builds\archive\BorrowedLight-v8-Windows.zip'
if ((Get-FileHash -LiteralPath $taskPriorZip -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $taskPriorArchiveZip -Algorithm SHA256).Hash) { throw 'The existing Windows ZIP has not been preserved in the v8 archive.' }
$taskArchivePath = Resolve-TaskPath 'builds\archive\BorrowedLight-v8-Web'
if (Test-Path -LiteralPath $taskArchivePath) { throw 'The v8 Web archive already exists; inspect before retrying.' }
foreach ($taskKind in @('windows', 'web')) {
    if (Test-Path -LiteralPath (Resolve-TaskPath ('builds\candidates\v8-' + $taskKind + '-previous'))) { throw 'Previous-release destination already exists.' }
    if (-not (Test-Path -LiteralPath (Resolve-TaskPath ('builds\candidates\v9\' + $taskKind)))) { throw 'Missing v9 candidate.' }
}
Copy-Item -LiteralPath (Resolve-TaskPath 'builds\web') -Destination $taskArchivePath -Recurse
foreach ($taskFile in $taskPriorManifest.webPayload.files) {
    if ((Get-FileHash -LiteralPath (Join-Path $taskArchivePath ('Build\' + $taskFile.name)) -Algorithm SHA256).Hash -ne $taskFile.sha256) { throw 'v8 Web archive hash mismatch.' }
}
foreach ($taskKind in @('windows', 'web')) {
    $taskStablePath = Resolve-TaskPath ('builds\' + $taskKind)
    $taskPreviousPath = Resolve-TaskPath ('builds\candidates\v8-' + $taskKind + '-previous')
    $taskCandidatePath = Resolve-TaskPath ('builds\candidates\v9\' + $taskKind)
    Move-Item -LiteralPath $taskStablePath -Destination $taskPreviousPath
    Copy-Item -LiteralPath $taskCandidatePath -Destination $taskStablePath -Recurse
}
foreach ($taskName in @('PLAY.zh-CN.txt', 'AI-使用与素材来源.zh-CN.txt')) { Copy-Item -LiteralPath (Join-Path $taskDraftPath $taskName) -Destination (Resolve-TaskPath $taskName) -Force }
Copy-Item -LiteralPath (Join-Path $taskDraftPath 'NEXT-STEPS.zh-CN.txt') -Destination (Resolve-TaskPath 'setup\NEXT-STEPS.zh-CN.txt') -Force
Copy-Item -LiteralPath (Join-Path $taskDraftPath 'production-manifest.json') -Destination (Resolve-TaskPath 'art\production-manifest.json') -Force
Copy-Item -LiteralPath (Join-Path $taskDraftPath 'release-checks.json') -Destination (Resolve-TaskPath 'art\verification\release-checks.json') -Force
foreach ($taskName in @('visual-review.html', 'visual-review-v9.html')) { Copy-Item -LiteralPath (Join-Path $taskDraftPath 'visual-review.html') -Destination (Resolve-TaskPath ('art\verification\' + $taskName)) -Force }
$taskPlayText = Get-Content -LiteralPath (Resolve-TaskPath 'PLAY.zh-CN.txt') -Raw
$taskNativePlay = $taskPlayText.Replace('开始游玩', "本压缩包为 Windows 运行包。下文的 art/、GameProject/、tools/ 等开发记录路径位于制作工作区，未包含在此运行包内。`r`n`r`n开始游玩").Replace('双击本目录中的 Open-Borrowed-Light.cmd。', '双击本目录中的 BorrowedLight.exe。').Replace('启动器会打开 builds\windows\BorrowedLight.exe，默认采用', '游戏默认采用').Replace('请保留整个 builds\windows 文件夹', '请保留整个解压后的文件夹').Replace('4. 浏览器版：双击', '4. 浏览器版在制作工作区另行提供：于工作区双击')
[IO.File]::WriteAllText((Resolve-TaskPath 'builds\windows\PLAY.zh-CN.txt'), $taskNativePlay, [Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Resolve-TaskPath 'PLAY.zh-CN.txt') -Destination (Resolve-TaskPath 'builds\web\PLAY.zh-CN.txt') -Force
foreach ($taskKind in @('windows', 'web')) {
    $taskTargetPath = Resolve-TaskPath ('builds\' + $taskKind)
    Copy-Item -LiteralPath (Resolve-TaskPath 'AI-使用与素材来源.zh-CN.txt') -Destination $taskTargetPath -Force
    foreach ($taskName in @('OFL-NotoSerifCJK.txt', 'FONT-SUBSET-NOTICE.txt', '主题依据.zh-CN.txt')) {
        Copy-Item -LiteralPath (Resolve-TaskPath ('builds\candidates\v8-windows-previous\' + $taskName)) -Destination $taskTargetPath -Force
    }
}
[ordered]@{ revision='v9'; previousWebArchived=$true; candidateCopiesPreserved=$true; localOnly=$true; packageVerificationPending=$true } | ConvertTo-Json
