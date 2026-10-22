$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$projectPath = Join-Path $workspacePath 'GameProject'
$editorPath = Join-Path $env:ProgramFiles 'Unity\Hub\Editor\6000.3.26f1\Editor\Unity.exe'

# Unity Package Manager needs explicit proxy variables. Match the user's
# existing Windows proxy for this process; leave persistent settings alone.
$proxySettings = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
if ($proxySettings.ProxyEnable -eq 1 -and $proxySettings.ProxyServer) {
    $proxyEntries = @{}
    foreach ($part in ($proxySettings.ProxyServer -split ';')) {
        if ($part -match '^([^=]+)=(.+)$') {
            $proxyEntries[$Matches[1].ToLowerInvariant()] = $Matches[2]
        } else {
            $proxyEntries['default'] = $part
        }
    }
    foreach ($scheme in @('http', 'https')) {
        $proxyAddress = $proxyEntries[$scheme]
        if (-not $proxyAddress) { $proxyAddress = $proxyEntries['default'] }
        if ($proxyAddress) {
            if ($proxyAddress -notmatch '^\w+://') { $proxyAddress = 'http://' + $proxyAddress }
            if ($scheme -eq 'http' -and -not $env:HTTP_PROXY) { $env:HTTP_PROXY = $proxyAddress }
            if ($scheme -eq 'https' -and -not $env:HTTPS_PROXY) { $env:HTTPS_PROXY = $proxyAddress }
        }
    }
}
$bypassEntries = @(($env:NO_PROXY -split ',') + @('localhost', '127.0.0.1', '::1'))
$env:NO_PROXY = ($bypassEntries | Where-Object { $_ } | Select-Object -Unique) -join ','

$runningEditor = Get-Process -Name Unity -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $editorPath }
if ($runningEditor) {
    Write-Output 'The Unity Editor is already running. Close it before relaunching to apply proxy changes.'
    exit 0
}
$logPath = Join-Path $PSScriptRoot 'verification\unity-editor-current.log'
$editorProcess = Start-Process -FilePath $editorPath -ArgumentList @('-projectPath', ('"' + $projectPath + '"'), '-logFile', ('"' + $logPath + '"')) -PassThru
Write-Output ('Opened GameProject. Editor PID: ' + $editorProcess.Id)
