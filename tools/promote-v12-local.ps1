param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$taskRootPath = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$taskPriorZipHash = 'CD823F949941B85101DFE71A5429837D23A0173DEC1807AB1BA1919229566B15'
function Resolve-TaskPath([string]$Relative) {
    $resolved = [IO.Path]::GetFullPath($(if ([IO.Path]::IsPathRooted($Relative)) { $Relative } else { Join-Path $taskRootPath $Relative }))
    if (-not $resolved.StartsWith($taskRootPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Path outside workspace: $Relative" }
    $cursor = $resolved
    while ($cursor -and $cursor.Length -ge $taskRootPath.Length) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse-point path refused: $cursor" }
        }
        $cursor = Split-Path -Parent $cursor
    }
    return $resolved
}
function Resolve-Child([string]$Parent, [string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Name) -or [IO.Path]::IsPathRooted($Name) -or $Name -match '(^|[\\/])\.\.?([\\/]|$)' -or $Name.Contains(':')) { throw "Invalid child path: $Name" }
    $resolved = Resolve-TaskPath (Join-Path $Parent $Name)
    if (-not $resolved.StartsWith($Parent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Child escaped its expected directory.' }
    return $resolved
}
function Read-TaskJson([string]$Relative) { return Get-Content -LiteralPath (Resolve-TaskPath $Relative) -Raw -Encoding UTF8 | ConvertFrom-Json }
function Get-TaskHash([string]$Absolute) { return (Get-FileHash -LiteralPath $Absolute -Algorithm SHA256).Hash }
function Assert-Hash([string]$Absolute, [string]$Expected) {
    if ($Expected -notmatch '^[A-Fa-f0-9]{64}$' -or (Get-TaskHash $Absolute) -ne $Expected) { throw "Hash mismatch: $Absolute" }
}
function Get-TreeHashes([string]$Directory) {
    $Directory = Resolve-TaskPath $Directory
    $result = @{}
    foreach ($item in Get-ChildItem -LiteralPath $Directory -Recurse -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point inside build: $($item.FullName)" }
        if (-not $item.PSIsContainer) { $result[$item.FullName.Substring($Directory.Length + 1)] = Get-TaskHash $item.FullName }
    }
    if ($result.Count -eq 0) { throw "Empty build directory: $Directory" }
    return $result
}
function Assert-Tree([hashtable]$Expected, [string]$Directory) {
    $actual = Get-TreeHashes $Directory
    if ($actual.Count -ne $Expected.Count) { throw "Copied file inventory differs: $Directory" }
    foreach ($name in $Expected.Keys) { if ($actual[$name] -ne $Expected[$name]) { throw "Copied file differs: $Directory / $name" } }
}

$taskDraftPath = Resolve-TaskPath 'art\verification\v12-release-draft'
$taskManifest = Read-TaskJson 'art\verification\v12-release-draft\production-manifest.json'
$taskChecks = Read-TaskJson 'art\verification\v12-release-draft\release-checks.json'
if ($taskManifest.revision -ne 'v12' -or $taskChecks.revision -ne 'v12' -or $taskChecks.windowsFunctionalPassed -ne $true -or $taskChecks.webFunctionalPassed -ne $true) { throw 'Expected accepted v12 draft and runtime evidence.' }
if ($taskChecks.buildIds.windows -ne $taskManifest.buildIds.windows -or $taskChecks.buildIds.web -ne $taskManifest.buildIds.web) { throw 'Draft build IDs disagree.' }
$taskNativeRun = [string]$taskChecks.nativeRun
if ($taskNativeRun -notmatch '^run-\d+-v12$' -or $taskChecks.evidence.native -ne ('art/verification/' + $taskNativeRun + '/runtime-results.json') -or $taskChecks.evidence.nativeIdentity -ne ('art/verification/' + $taskNativeRun + '/build-evidence.json') -or $taskChecks.evidence.web -ne 'art/verification/web-013-v12/runtime-results.json') { throw 'Unexpected final QA sessions.' }
$taskNative = Read-TaskJson $taskChecks.evidence.native
foreach ($name in @('puzzleCompleted','menuKeyboardStart','pauseStopsMovement','resumeMovement','restartWorks','endingReturnWorks','cabinCollisionWorks','walkwayGroundingWorks','boulderCollisionWorks','observatoryGroundingWorks','observatoryInstrumentCollisionWorks','decorativeLeavesExcluded','pierGroundingWorks','pierRailCollisionWorks','scrollZoomWorks')) {
    if ($taskNative.$name -ne $true) { throw "Native QA failed or missing: $name" }
}
$taskWeb = Read-TaskJson 'art\verification\web-013-v12\runtime-results.json'
foreach ($name in @('passed','realKeyboardPuzzleCompletion','persistedProgressReload','crossOriginIsolated','audioContextResumeObserved','defaultBrowserAutoplayPolicy')) {
    if ($taskWeb.$name -ne $true) { throw "Web QA failed or missing: $name" }
}
if ($null -eq $taskWeb.errors -or @($taskWeb.errors).Count -ne 0) { throw 'Web errors missing/nonempty.' }
$taskNativeCandidate = Resolve-TaskPath 'builds\candidates\v12\windows'
$taskWebCandidate = Resolve-TaskPath 'builds\candidates\v12\web'
$taskNativeEvidence = Read-TaskJson $taskChecks.evidence.nativeIdentity
if ($taskNativeEvidence.mode -ne 'Tour' -or $taskNativeEvidence.buildId -ne $taskManifest.buildIds.windows -or [IO.Path]::GetFullPath($taskNativeEvidence.playerDirectory) -ne $taskNativeCandidate) { throw 'Native QA used a different candidate or diagnostic mode.' }
$taskNativeNames = @('BorrowedLight.exe','UnityPlayer.dll','BorrowedLight_Data/resources.assets','BorrowedLight_Data/Managed/Assembly-CSharp.dll')
if (@($taskNativeEvidence.files).Count -ne 4) { throw 'Expected four native QA identity files.' }
foreach ($name in $taskNativeNames) {
    $taskMatches = @($taskNativeEvidence.files | Where-Object { $_.name.Replace('\','/') -ceq $name })
    if ($taskMatches.Count -ne 1) { throw "Native identity missing/duplicate: $name" }
    Assert-Hash (Resolve-Child $taskNativeCandidate $name) $taskMatches[0].sha256
}
$taskIdentity = Read-TaskJson 'art\verification\web-013-v12\artifact-identity.json'
if ($taskIdentity.passed -ne $true -or $taskIdentity.declaredBuildMatches -ne $true -or $taskIdentity.requestedAllCurrentFiles -ne $true -or $taskIdentity.buildId -ne $taskManifest.buildIds.web -or $taskIdentity.session -ne 'web-013-v12') { throw 'Web candidate identity incomplete.' }
if (@($taskManifest.webPayload.files).Count -ne 4 -or @($taskIdentity.files).Count -ne 4 -or @($taskManifest.webPayload.files.name | Sort-Object -Unique).Count -ne 4) { throw 'Expected exactly four unique web payload files.' }
$taskWebBytes = 0L
foreach ($file in $taskManifest.webPayload.files) {
    if ($file.name -match '[\\/:]' -or $file.name -in @('.','..')) { throw 'Invalid web payload basename.' }
    $payloadPath = Resolve-Child (Join-Path $taskWebCandidate 'Build') $file.name
    Assert-Hash $payloadPath $file.sha256
    if ((Get-Item -LiteralPath $payloadPath).Length -ne $file.bytes -or $file.bytes -le 0) { throw 'Web payload size differs.' }
    $taskWebBytes += $file.bytes
    $taskMatches = @($taskIdentity.files | Where-Object name -CEQ $file.name)
    if ($taskMatches.Count -ne 1 -or $taskMatches[0].matches -ne $true -or $taskMatches[0].bytes -ne $file.bytes -or $taskMatches[0].httpSHA256 -ne $file.sha256 -or $taskMatches[0].diskSHA256 -ne $file.sha256) { throw 'Web QA bytes differ from draft.' }
}
if ($taskWebBytes -ne $taskManifest.webPayload.bytes) { throw 'Web payload total differs.' }
Assert-Hash (Resolve-TaskPath 'GameProject\Assets\BorrowedLight\Resources\Models\Island.fbx') $taskManifest.geometry.worldFbxSHA256
Assert-Hash (Resolve-TaskPath 'GameProject\Assets\BorrowedLight\Resources\Models\Traveler.fbx') $taskManifest.geometry.travelerFbxSHA256

# Intentional ground integration is audited explicitly; do not require all v11 code unchanged.
$taskAudit = $taskManifest.sourceAudit
if ($taskAudit.allChangesWithinScope -ne $true -or $taskAudit.baseline -ne 'art/verification/v11-release-source/source-files.json' -or @($taskAudit.files).Count -eq 0) { throw 'Missing source allowlist audit.' }
if (($taskAudit | ConvertTo-Json -Depth 30 -Compress) -cne ($taskChecks.sourceAudit | ConvertTo-Json -Depth 30 -Compress)) { throw 'Draft source audits disagree.' }
foreach ($row in $taskAudit.files) {
    if ($row.allowed -ne $true -or $row.status -notin @('unchanged','modified','added','unbaselined-existing')) { throw "Source outside reviewed scope: $($row.source)" }
    Assert-Hash (Resolve-TaskPath $row.source) $row.sha256
}
if (@($taskAudit.allowedChangedExisting).Count -ne 1 -or $taskAudit.allowedChangedExisting[0] -ne 'GameProject/Assets/BorrowedLight/Runtime/WorldDirector.cs') { throw 'Unexpected existing-source allowlist.' }
foreach ($row in @($taskAudit.files | Where-Object status -EQ 'modified')) { if ($row.source -notin $taskAudit.allowedChangedExisting) { throw 'Unapproved source modification.' } }
foreach ($row in @($taskAudit.files | Where-Object status -EQ 'added')) { if ($row.source -notin $taskAudit.allowedAdded) { throw 'Unapproved source addition.' } }
$taskExpectedAdded = @('Runtime/GroundDetailStudy.cs','Runtime/GroundDetailStudy.cs.meta','Shaders/GroundDetail.shader','Shaders/GroundDetail.shader.meta','Resources/Textures/GroundDetailV12.png','Resources/Textures/GroundDetailV12.png.meta','Resources/Materials/GroundDetailV12.mat','Resources/Materials/GroundDetailV12.mat.meta') | ForEach-Object { 'GameProject/Assets/BorrowedLight/' + $_ }
if (Compare-Object ($taskExpectedAdded | Sort-Object) (@($taskAudit.allowedAdded) | Sort-Object)) { throw 'Unexpected source-addition allowlist.' }
$taskInventoryRoots = @('Runtime','Shaders','Resources/Materials','Resources/Textures') | ForEach-Object { 'GameProject/Assets/BorrowedLight/' + $_ }
$taskExtensions = @('.cs','.shader','.hlsl','.mat','.png','.meta')
if ((Compare-Object ($taskInventoryRoots | Sort-Object) (@($taskAudit.inventoryRoots) | Sort-Object)) -or (Compare-Object ($taskExtensions | Sort-Object) (@($taskAudit.inventoryExtensions) | Sort-Object))) { throw 'Source inventory scope differs.' }
$taskBaseline = @(Read-TaskJson 'art\verification\v11-release-source\source-files.json')
if ($taskBaseline.Count -ne 16 -or @($taskBaseline.source | Sort-Object -Unique).Count -ne 16) { throw 'Unexpected v11 source baseline.' }
$taskExtra = @($taskBaseline.source | Where-Object { $source = $_; -not @($taskInventoryRoots | Where-Object { $source.StartsWith($_ + '/', [StringComparison]::Ordinal) }).Count })
if (Compare-Object ($taskExtra | Sort-Object) (@($taskAudit.inventoryExtraFiles) | Sort-Object)) { throw 'Source extra-file inventory differs.' }
$taskInventory = @($taskExtra)
foreach ($directory in $taskInventoryRoots) {
    foreach ($item in Get-ChildItem -LiteralPath (Resolve-TaskPath $directory) -Recurse -Force) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in source inventory.' }
        if (-not $item.PSIsContainer -and $item.Extension -in $taskExtensions) { $taskInventory += $item.FullName.Substring($taskRootPath.Length + 1).Replace('\','/') }
    }
}
$taskInventory = @($taskInventory | Sort-Object -Unique)
if ((Compare-Object $taskInventory (@($taskAudit.inventoryFiles) | Sort-Object)) -or (Compare-Object $taskInventory (@($taskAudit.files.source) | Sort-Object))) { throw 'Source files added/deleted since handoff audit.' }
foreach ($row in $taskAudit.files) {
    $old = @($taskBaseline | Where-Object source -CEQ $row.source)
    if ($old.Count -eq 1) {
        if ($row.baselineSHA256 -ne $old[0].sha256) { throw 'Recorded v11 source hash was changed.' }
        $expectedStatus = if ($row.sha256 -eq $old[0].sha256) { 'unchanged' } else { 'modified' }
    } else {
        if ($null -ne $row.baselineSHA256) { throw 'Previously unbaselined source falsely claims a baseline.' }
        $expectedStatus = if ($row.source -in $taskExpectedAdded) { 'added' } else { 'unbaselined-existing' }
    }
    if ($row.status -ne $expectedStatus) { throw "Source status mismatch: $($row.source)" }
}
foreach ($name in @($taskBaseline.source) + @($taskExpectedAdded)) { if ($name -notin $taskInventory) { throw "Required source missing: $name" } }

$taskPriorManifest = Read-TaskJson 'art\production-manifest.json'
if ($taskPriorManifest.revision -ne 'v11') { throw 'Expected v11 stable before v12 promotion.' }
Assert-Hash (Resolve-TaskPath 'builds\BorrowedLight-Windows.zip') $taskPriorZipHash
Assert-Hash (Resolve-TaskPath 'builds\archive\BorrowedLight-v11-Windows.zip') $taskPriorZipHash
$taskArchivePath = Resolve-TaskPath 'builds\archive\BorrowedLight-v11-Web'
$taskStagePath = Resolve-TaskPath 'builds\candidates\v12-promotion-staging'
$taskHandoffArchive = Resolve-TaskPath 'art\verification\v11-handoff-before-v12'
$taskPromotionRecord = Resolve-TaskPath 'art\verification\v12-promotion.json'
foreach ($destination in @($taskArchivePath,$taskStagePath,$taskHandoffArchive,$taskPromotionRecord,(Resolve-TaskPath 'art\verification\visual-review-v12.html'))) {
    if (Test-Path -LiteralPath $destination) { throw "Historical/staging destination already exists; inspect before retry: $destination" }
}
$taskDraftNames = @('PLAY.zh-CN.txt','AI-使用与素材来源.zh-CN.txt','NEXT-STEPS.zh-CN.txt','production-manifest.json','release-checks.json','visual-review.html')
$taskDraftHashes = @{}
foreach ($name in $taskDraftNames) { $taskDraftHashes[$name] = Get-TaskHash (Resolve-Child $taskDraftPath $name) }
foreach ($name in @('PLAY.zh-CN.txt','AI-使用与素材来源.zh-CN.txt','NEXT-STEPS.zh-CN.txt')) {
    $draftText = Get-Content -LiteralPath (Resolve-Child $taskDraftPath $name) -Raw -Encoding UTF8
    if ($draftText -match '尚未晋级|尚未替换正式交付|待root审核|本工具只准备草稿|（草稿）|v12草稿') { throw "Draft-only text cannot be published: $name" }
}
$taskPlayText = Get-Content -LiteralPath (Resolve-Child $taskDraftPath 'PLAY.zh-CN.txt') -Raw -Encoding UTF8
if (-not $taskPlayText.Contains('开始游玩') -or -not $taskPlayText.Contains('双击本目录中的 Open-Borrowed-Light.cmd。')) { throw 'PLAY package adaptation markers changed.' }
$taskPriorFiles = @('AGENTS.md','PLAY.zh-CN.txt','AI-使用与素材来源.zh-CN.txt','setup\NEXT-STEPS.zh-CN.txt','art\production-manifest.json','art\verification\release-checks.json','art\verification\visual-review.html')
foreach ($name in $taskPriorFiles) { if (-not (Test-Path -LiteralPath (Resolve-TaskPath $name) -PathType Leaf)) { throw "Missing prior handoff: $name" } }
$taskNoticeNames = @('OFL-NotoSerifCJK.txt','FONT-SUBSET-NOTICE.txt','主题依据.zh-CN.txt')
foreach ($name in $taskNoticeNames) { if (-not (Test-Path -LiteralPath (Resolve-TaskPath ('builds\windows\' + $name)) -PathType Leaf)) { throw "Missing existing package notice: $name" } }
if (-not (Test-Path -LiteralPath (Resolve-TaskPath 'tools\package-templates\Play-Fullscreen.cmd') -PathType Leaf)) { throw 'Missing fullscreen package launcher.' }
$taskStableTrees = @{}; $taskCandidateTrees = @{}
foreach ($kind in @('windows','web')) {
    if (Test-Path -LiteralPath (Resolve-TaskPath ('builds\candidates\v11-' + $kind + '-previous'))) { throw 'Previous-release destination already exists.' }
    $taskStableTrees[$kind] = Get-TreeHashes (Resolve-TaskPath ('builds\' + $kind))
    $taskCandidateTrees[$kind] = Get-TreeHashes (Resolve-TaskPath ('builds\candidates\v12\' + $kind))
}
foreach ($file in $taskPriorManifest.webPayload.files) { Assert-Hash (Resolve-Child (Resolve-TaskPath 'builds\web\Build') $file.name) $file.sha256 }
if ($CheckOnly) { [ordered]@{revision='v12';previousRevision='v11';checkOnly=$true;passed=$true;sourceAuditChecked=$true} | ConvertTo-Json; return }

# All required sources are checked before the first mutation. No recursive deletion or
# overwrite of an archive occurs. Partial failures preserve the record for manual recovery.
$taskRecord = [ordered]@{revision='v12';previousRevision='v11';nativeRun=$taskNativeRun;passed=$false;phase='staging';buildIds=$taskManifest.buildIds;draftSHA256=$taskDraftHashes;previousWindowsZIP=$taskPriorZipHash;steps=@();startedAtUTC=[DateTime]::UtcNow.ToString('o')}
function Save-Record { [IO.File]::WriteAllText($taskPromotionRecord, ($taskRecord | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false)) }
Save-Record
try {
    New-Item -ItemType Directory -Path $taskStagePath | Out-Null
    foreach ($kind in @('windows','web')) {
        $stage = Resolve-Child $taskStagePath $kind
        Copy-Item -LiteralPath (Resolve-TaskPath ('builds\candidates\v12\' + $kind)) -Destination $stage -Recurse
        Assert-Tree $taskCandidateTrees[$kind] $stage
    }
    $taskPlayText = Get-Content -LiteralPath (Resolve-Child $taskDraftPath 'PLAY.zh-CN.txt') -Raw -Encoding UTF8
    if (-not $taskPlayText.Contains('开始游玩') -or -not $taskPlayText.Contains('双击本目录中的 Open-Borrowed-Light.cmd。')) { throw 'PLAY package adaptation markers changed.' }
    $taskNativePlay = $taskPlayText.Replace('开始游玩', "本压缩包为 Windows 运行包。下文 art/、GameProject/、tools/ 等开发记录位于制作工作区，未包含在此包内。`r`n`r`n开始游玩").Replace('双击本目录中的 Open-Borrowed-Light.cmd。','双击本目录中的 BorrowedLight.exe。').Replace('Open-Borrowed-Light-Fullscreen.cmd','Play-Fullscreen.cmd').Replace('启动器会打开 builds\windows\BorrowedLight.exe，默认采用','游戏默认采用').Replace('请保留整个 builds\windows 文件夹','请保留整个解压后的文件夹').Replace('4. 浏览器版：双击','4. 浏览器版在制作工作区另行提供：于工作区双击')
    [IO.File]::WriteAllText((Resolve-Child $taskStagePath 'windows\PLAY.zh-CN.txt'),$taskNativePlay,[Text.UTF8Encoding]::new($false))
    Copy-Item -LiteralPath (Resolve-TaskPath 'tools\package-templates\Play-Fullscreen.cmd') -Destination (Resolve-Child $taskStagePath 'windows\Play-Fullscreen.cmd') -Force
    Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'PLAY.zh-CN.txt') -Destination (Resolve-Child $taskStagePath 'web\PLAY.zh-CN.txt') -Force
    foreach ($kind in @('windows','web')) {
        Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'AI-使用与素材来源.zh-CN.txt') -Destination (Resolve-Child $taskStagePath ($kind + '\AI-使用与素材来源.zh-CN.txt')) -Force
        foreach ($name in $taskNoticeNames) { Copy-Item -LiteralPath (Resolve-TaskPath ('builds\windows\' + $name)) -Destination (Resolve-Child $taskStagePath ($kind + '\' + $name)) -Force }
    }
    New-Item -ItemType Directory -Path $taskHandoffArchive | Out-Null
    foreach ($name in $taskPriorFiles) {
        $destination = Resolve-Child $taskHandoffArchive $name
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath (Resolve-TaskPath $name) -Destination $destination
        Assert-Hash $destination (Get-TaskHash (Resolve-TaskPath $name))
    }
    Copy-Item -LiteralPath (Resolve-TaskPath 'builds\web') -Destination $taskArchivePath -Recurse
    Assert-Tree $taskStableTrees.web $taskArchivePath
    $taskRecord.steps += 'v11 web and handoff archived'; Save-Record
    foreach ($name in $taskDraftNames) { Assert-Hash (Resolve-Child $taskDraftPath $name) $taskDraftHashes[$name] }
    foreach ($kind in @('windows','web')) {
        Assert-Tree $taskStableTrees[$kind] (Resolve-TaskPath ('builds\' + $kind))
        Assert-Tree $taskCandidateTrees[$kind] (Resolve-TaskPath ('builds\candidates\v12\' + $kind))
    }
    foreach ($kind in @('windows','web')) {
        $stable = Resolve-TaskPath ('builds\' + $kind)
        $previous = Resolve-TaskPath ('builds\candidates\v11-' + $kind + '-previous')
        # Resolve and boundary-check both absolute targets immediately before move.
        Move-Item -LiteralPath $stable -Destination $previous
        $taskRecord.steps += ('preserved v11 ' + $kind); Save-Record
        Move-Item -LiteralPath (Resolve-Child $taskStagePath $kind) -Destination $stable
        $taskRecord.steps += ('installed v12 ' + $kind); Save-Record
    }
    foreach ($name in @('PLAY.zh-CN.txt','AI-使用与素材来源.zh-CN.txt')) { Copy-Item -LiteralPath (Resolve-Child $taskDraftPath $name) -Destination (Resolve-TaskPath $name) -Force }
    Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'NEXT-STEPS.zh-CN.txt') -Destination (Resolve-TaskPath 'setup\NEXT-STEPS.zh-CN.txt') -Force
    Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'production-manifest.json') -Destination (Resolve-TaskPath 'art\production-manifest.json') -Force
    Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'release-checks.json') -Destination (Resolve-TaskPath 'art\verification\release-checks.json') -Force
    foreach ($name in @('visual-review.html','visual-review-v12.html')) { Copy-Item -LiteralPath (Resolve-Child $taskDraftPath 'visual-review.html') -Destination (Resolve-TaskPath ('art\verification\' + $name)) -Force }
    foreach ($file in $taskNativeEvidence.files) { Assert-Hash (Resolve-Child (Resolve-TaskPath 'builds\windows') $file.name) $file.sha256 }
    foreach ($file in $taskManifest.webPayload.files) { Assert-Hash (Resolve-Child (Resolve-TaskPath 'builds\web\Build') $file.name) $file.sha256 }
    $taskRecord.phase='promoted-awaiting-package-and-http'; $taskRecord.passed=$true
    $taskRecord.candidateCopiesPreserved=$true; $taskRecord.localOnly=$true; $taskRecord.packageVerificationPending=$true
    $taskRecord.completedAtUTC=[DateTime]::UtcNow.ToString('o'); Save-Record
    $taskRecord | ConvertTo-Json -Depth 20
} catch {
    $taskRecord.phase='failed-preserved-for-inspection'; $taskRecord.error=$_.Exception.Message; Save-Record
    throw
}
