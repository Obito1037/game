$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$unityExe = Join-Path $workspacePath 'tools\unity-cli\bin\unity.exe'
$blenderDir = Join-Path $workspacePath 'tools\blender-4.5.14-windows-x64'
$blenderExe = Join-Path $blenderDir 'blender.exe'
$editorDir = Join-Path $env:ProgramFiles 'Unity\Hub\Editor\6000.3.26f1\Editor'
$hubExe = Join-Path $env:ProgramFiles 'Unity Hub\Unity Hub.exe'
$projectPath = Join-Path $workspacePath 'GameProject'

function Read-JsonOrNull {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        try { return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json) }
        catch { return $null }
    }
    return $null
}

function Get-Field {
    param($Value, [string]$Name)
    if ($null -ne $Value) {
        $property = $Value.PSObject.Properties[$Name]
        if ($null -ne $property) { return $property.Value }
    }
    return $null
}

function Get-HashOrNull {
    param([string]$Path, [string]$Algorithm)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return (Get-FileHash -LiteralPath $Path -Algorithm $Algorithm).Hash
    }
    return $null
}

function Compare-Hash {
    param($Actual, $Expected)
    if ([string]::IsNullOrWhiteSpace($Actual) -or [string]::IsNullOrWhiteSpace($Expected)) { return $null }
    return $Actual -eq $Expected
}

function Invoke-UnityJson {
    param([string[]]$CliArguments)
    $checkedAt = (Get-Date).ToString('o')
    $exitCode = $null
    $parsed = $null
    $errorCodes = @()
    if (Test-Path -LiteralPath $unityExe -PathType Leaf) {
        # Expected nonzero results (for example, no open Editors) must not abort
        # all checks. Never print raw account data or stderr.
        $ErrorActionPreference = 'Continue'
        $PSNativeCommandUseErrorActionPreference = $false
        try {
            $rawOutput = & $unityExe @CliArguments 2>$null | Out-String
            $exitCode = $LASTEXITCODE
            $parsed = $rawOutput | ConvertFrom-Json -ErrorAction Stop
            $errorCodes = @(Get-Field $parsed 'errors' | ForEach-Object {
                $code = Get-Field $_ 'code'
                if ($null -ne $code) { $code }
            })
        }
        catch { $errorCodes = @('CLI_RESULT_UNAVAILABLE') }
    }
    else { $errorCodes = @('EXECUTABLE_MISSING') }
    return [pscustomobject]@{
        checkedAt = $checkedAt
        exitCode = $exitCode
        success = ($null -ne $parsed -and (Get-Field $parsed 'success') -eq $true -and $exitCode -eq 0)
        data = Get-Field $parsed 'data'
        errorCodes = $errorCodes
    }
}

$manifest = Read-JsonOrNull (Join-Path $projectPath 'Packages\manifest.json')
$blenderResultPath = Join-Path $PSScriptRoot 'verification\blender-result.json'
$blenderResult = Read-JsonOrNull $blenderResultPath
$cliRelease = Read-JsonOrNull (Join-Path $workspacePath 'downloads\unity-cli-1.0.0-beta.13.json')
$cliHash = Get-HashOrNull $unityExe 'SHA256'
$blenderArchiveHash = Get-HashOrNull (Join-Path $workspacePath 'downloads\blender-4.5.14-windows-x64.zip') 'SHA256'
$hubArchivePath = Join-Path $workspacePath 'downloads\UnityHubSetup-3.22.3-x64.exe'
$hubArchiveHash = Get-HashOrNull $hubArchivePath 'SHA512'
$hubExpectedHash = [BitConverter]::ToString([Convert]::FromBase64String('M3JBFlfmEPLel7O0iB1aUFCEqzFnY4OlpVlvyz4ckvZwF48mxgWca/AmOppd+58urHMsxPui9e8lw2jE5coFCw==')).Replace('-', '')
$hubSignatureValid = $null
if (Test-Path -LiteralPath $hubArchivePath -PathType Leaf) {
    $hubSignature = Get-AuthenticodeSignature -LiteralPath $hubArchivePath
    $hubSignatureValid = $hubSignature.Status -eq 'Valid' -and $hubSignature.SignerCertificate.Subject -match 'Unity Technologies'
}

# Fresh CLI snapshots: do not reuse the initial project/account report.
$authResult = Invoke-UnityJson -CliArguments @('auth', 'status', '--json', '--non-interactive')
$liveResult = Invoke-UnityJson -CliArguments @('pipeline', 'list', '--json', '--non-interactive')
$editorStatusResult = Invoke-UnityJson -CliArguments @('status', '--project-path', $projectPath, '--json', '--non-interactive')
$projectResult = Invoke-UnityJson -CliArguments @('projects', 'verify', $projectPath, '--json', '--non-interactive')
$liveSummary = Get-Field $liveResult.data 'summary'
$statusInstances = @(Get-Field $editorStatusResult.data 'instances' | Where-Object { $null -ne $_ })
$readyEditors = @($statusInstances | Where-Object { (Get-Field $_ 'state') -eq 'ready' }).Count
if ($readyEditors -eq 0 -and (Get-Field $editorStatusResult.data 'state') -eq 'ready') { $readyEditors = 1 }
$editorLiveVerified = $editorStatusResult.success -and $readyEditors -gt 0

# Read this launch's log. Export anonymous evidence only, never raw log lines,
# account identifiers, entitlement IDs, or tokens.
$editorLogPath = Join-Path $PSScriptRoot 'verification\unity-editor-current.log'
$editorLog = $null
$editorLogUpdatedAt = $null
if (Test-Path -LiteralPath $editorLogPath -PathType Leaf) {
    try {
        $editorLog = Get-Content -LiteralPath $editorLogPath -Raw -Encoding UTF8
        $editorLogUpdatedAt = (Get-Item -LiteralPath $editorLogPath).LastWriteTime.ToString('o')
    }
    catch { $editorLog = $null }
}
$entitlementResolved = $null
$compilationState = 'unknown-no-current-log'
$compilerErrorCount = $null
$licenseState = 'unknown'
if ($null -ne $editorLog) {
    $entitlementMatches = [regex]::Matches($editorLog, '(?im)Successfully resolved entitlement details')
    $licenseFailureMatches = [regex]::Matches($editorLog, '(?im)No valid Unity Editor license|No valid license found|License activation failed')
    $entitlementResolved = $entitlementMatches.Count -gt 0
    $lastEntitlementIndex = if ($entitlementResolved) { $entitlementMatches[$entitlementMatches.Count - 1].Index } else { -1 }
    $lastLicenseFailureIndex = if ($licenseFailureMatches.Count -gt 0) { $licenseFailureMatches[$licenseFailureMatches.Count - 1].Index } else { -1 }
    if ($editorLiveVerified -and $entitlementResolved -and $lastEntitlementIndex -gt $lastLicenseFailureIndex) {
        $licenseState = 'available-editor-ready'
    }
    elseif ($lastLicenseFailureIndex -gt $lastEntitlementIndex) { $licenseState = 'failure-observed-in-current-log' }
    elseif ($entitlementResolved) { $licenseState = 'entitlement-resolved-awaiting-editor-ready' }

    $compilerErrors = [regex]::Matches($editorLog, '(?im)\berror\s+CS\d+\b')
    $compilationFailures = [regex]::Matches($editorLog, '(?im)Compilation failed|Scripts have compiler errors|Script compilation failed|CompilationFailureException')
    $compilationSuccesses = [regex]::Matches($editorLog, '(?im)Compilation succeeded|Compilation completed successfully|Script compilation finished successfully')
    $compilerErrorCount = $compilerErrors.Count
    $lastCompilationFailure = -1
    if ($compilerErrors.Count -gt 0) { $lastCompilationFailure = $compilerErrors[$compilerErrors.Count - 1].Index }
    if ($compilationFailures.Count -gt 0) {
        $lastCompilationFailure = [Math]::Max($lastCompilationFailure, $compilationFailures[$compilationFailures.Count - 1].Index)
    }
    $lastCompilationSuccess = if ($compilationSuccesses.Count -gt 0) { $compilationSuccesses[$compilationSuccesses.Count - 1].Index } else { -1 }
    if ($lastCompilationFailure -ge 0 -and $lastCompilationFailure -ge $lastCompilationSuccess) { $compilationState = 'errors-observed-in-current-log' }
    elseif ($lastCompilationSuccess -gt $lastCompilationFailure) { $compilationState = 'success-observed-in-current-log' }
    elseif ($editorLiveVerified) { $compilationState = 'editor-ready-no-compiler-errors-observed' }
    elseif ($editorLog -match '(?im)Requested script compilation|Starting:.*ScriptCompilationBuildProgram') { $compilationState = 'compilation-started-completion-not-confirmed' }
    else { $compilationState = 'no-compilation-result-observed' }
}

# This is a recorded historical protocol check, not a fresh MCP handshake.
$mcpResult = Read-JsonOrNull (Join-Path $PSScriptRoot 'verification\unity-mcp-result.json')
$mcpCheckedAt = Get-Field $mcpResult 'checkedAtUtc'
if ($null -eq $mcpCheckedAt) { $mcpCheckedAt = Get-Field $mcpResult 'checkedAt' }
$autoRigDirectories = @(
    (Join-Path $blenderDir '4.5\scripts\addons'),
    (Join-Path $blenderDir '4.5\scripts\addons_core'),
    (Join-Path $blenderDir 'portable\scripts\addons'),
    (Join-Path $blenderDir 'portable\extensions\user_default')
)
$autoRigMatches = @($autoRigDirectories | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | ForEach-Object {
    Get-ChildItem -LiteralPath $_ -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '(?i)^auto[_-]?rig[_-]?pro(?:[_-]|$)' }
})
$cliVersion = $null
if (Test-Path -LiteralPath $unityExe -PathType Leaf) {
    $cliVersion = (& $unityExe --version 2>$null | Out-String).Trim()
}
$hubVersion = $null
if (Test-Path -LiteralPath $hubExe -PathType Leaf) { $hubVersion = (Get-Item -LiteralPath $hubExe).VersionInfo.ProductVersion }

$status = [ordered]@{
    checkedAt = (Get-Date).ToString('o')
    workspace = $workspacePath
    blender = [ordered]@{
        installed = Test-Path -LiteralPath $blenderExe
        version = '4.5.14 LTS'
        executable = $blenderExe
        archiveSha256MatchesOfficial = Compare-Hash $blenderArchiveHash 'b9533d2397ac1984db4466fb23a7a4649391cca93f6e84209f9bcc60d071c8b9'
        smokeTest = if ($null -ne $blenderResult) { Get-Field $blenderResult 'status' } else { 'not-run' }
        smokeTestSource = 'recorded-result-not-retested'
    }
    unityCli = [ordered]@{
        installed = Test-Path -LiteralPath $unityExe
        version = $cliVersion
        executable = $unityExe
        binarySha256MatchesOfficial = Compare-Hash $cliHash $cliRelease.binaries.'win32-x64'.sha256
        loggedIn = Get-Field $authResult.data 'loggedIn'
        authCheckedAt = $authResult.checkedAt
        authCheckSucceeded = $authResult.success
        authErrorCodes = @($authResult.errorCodes)
    }
    unityHub = [ordered]@{
        installed = Test-Path -LiteralPath $hubExe
        version = $hubVersion
        installerSha512MatchesOfficial = Compare-Hash $hubArchiveHash $hubExpectedHash
        installerSignatureValid = $hubSignatureValid
    }
    unityEditor = [ordered]@{
        installed = Test-Path -LiteralPath (Join-Path $editorDir 'Unity.exe')
        version = '6000.3.26f1'
        packageManagerInstalled = Test-Path -LiteralPath (Join-Path $editorDir 'Data\Resources\PackageManager\Server\UnityPackageManager.exe')
        webBuildSupportInstalled = Test-Path -LiteralPath (Join-Path $editorDir 'Data\PlaybackEngines\WebGLSupport\UnityEditor.WebGL.Extensions.dll')
        currentLogUpdatedAt = $editorLogUpdatedAt
        license = [ordered]@{
            state = $licenseState
            basis = 'current-editor-log-and-live-readiness'
            entitlementResolved = $entitlementResolved
        }
        compilation = [ordered]@{ state = $compilationState; compilerErrorsObserved = $compilerErrorCount }
        buildValidation = 'not-tested'
        readyEditors = $readyEditors
        statusCheckedAt = $editorStatusResult.checkedAt
        statusCheckSucceeded = $editorStatusResult.success
        statusErrorCodes = @($editorStatusResult.errorCodes)
    }
    project = [ordered]@{
        path = $projectPath
        pipelineManifestVersion = $manifest.dependencies.'com.unity.pipeline'
        structuralVerificationPassed = Get-Field $projectResult.data 'ok'
        structuralVerificationCheckedAt = $projectResult.checkedAt
        structuralVerificationCommandSucceeded = $projectResult.success
        structuralVerificationErrorCodes = @($projectResult.errorCodes)
        structuralVerificationSummary = Get-Field $projectResult.data 'summary'
        mcpProtocolHandshakePassed = Get-Field (Get-Field $mcpResult 'protocolHandshake') 'success'
        mcpToolsAtHandshake = Get-Field $mcpResult 'toolsCount'
        mcpProtocolHandshakeCheckedAt = $mcpCheckedAt
        mcpProtocolHandshakeSource = 'recorded-result-not-retested'
        mcpReadOnlyEditorCommandPassed = Get-Field (Get-Field $mcpResult 'editorLive') 'verified'
        editorLiveVerified = $editorLiveVerified
        liveEditors = Get-Field $liveSummary 'runningInstances'
        reachableServers = Get-Field $liveSummary 'reachableServers'
        pipelineCheckedAt = $liveResult.checkedAt
        pipelineCheckSucceeded = $liveResult.success
        pipelineErrorCodes = @($liveResult.errorCodes)
    }
    autoRigPro = [ordered]@{
        detectedInPortableScripts = $autoRigMatches.Count -gt 0
        scope = 'portable-addon-directories-only'
        purchaseStatus = 'unknown-not-checked'
    }
    tripo = [ordered]@{ type = 'web-service'; accountStatus = 'unknown-not-checked' }
    mixamo = [ordered]@{ type = 'web-service'; accountStatus = 'unknown-not-checked' }
}
$outputPath = Join-Path $PSScriptRoot 'tool-status.json'
$status | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$status | ConvertTo-Json -Depth 8
Write-Host "Saved: $outputPath"
