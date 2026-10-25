param(
    [Parameter(Mandatory=$true)][string]$PlayerPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
if(Get-Process -Name JieGuang -ErrorAction SilentlyContinue){throw 'A JieGuang player is already running.'}
$jgPlayerPath=(Resolve-Path -LiteralPath $PlayerPath).Path
$jgOut=[System.IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath (Join-Path $jgOut 'render-study.json')){throw 'Use a fresh output directory; existing evidence is preserved.'}
New-Item -ItemType Directory -Path $jgOut -Force | Out-Null
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class JgRenderContext {
  [StructLayout(LayoutKind.Sequential)] public struct PowerStatus {
    public byte ACLineStatus, BatteryFlag, BatteryLifePercent, SystemStatusFlag;
    public int BatteryLifeTime, BatteryFullLifeTime;
  }
  [DllImport("kernel32.dll")] public static extern bool GetSystemPowerStatus(out PowerStatus s);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
$jgPower=New-Object JgRenderContext+PowerStatus
[JgRenderContext]::GetSystemPowerStatus([ref]$jgPower) | Out-Null
$jgPlayer=Start-Process -FilePath $jgPlayerPath -ArgumentList @('-screen-width','1600','-screen-height','900','-screen-fullscreen','0','--jg-render-study','--jg-qa-out',$jgOut,'-logFile',(Join-Path $jgOut 'Player.log')) -WindowStyle Normal -PassThru
$jgTimer=[Diagnostics.Stopwatch]::StartNew()
while($jgTimer.Elapsed.TotalSeconds -lt 15){
    $jgPlayer.Refresh()
    if($jgPlayer.HasExited -or $jgPlayer.MainWindowHandle -ne [IntPtr]::Zero){break}
    Start-Sleep -Milliseconds 200
}
$jgFocusRequested=if($jgPlayer.MainWindowHandle -ne [IntPtr]::Zero){[JgRenderContext]::SetForegroundWindow($jgPlayer.MainWindowHandle)}else{$false}
$jgSamples=[System.Collections.Generic.List[object]]::new()
$jgLastProgress=-1
while(-not $jgPlayer.HasExited -and $jgTimer.Elapsed.TotalSeconds -lt 240){
    $jgForegroundPid=[uint32]0
    [JgRenderContext]::GetWindowThreadProcessId([JgRenderContext]::GetForegroundWindow(),[ref]$jgForegroundPid) | Out-Null
    $jgGpu=Get-Counter '\GPU Engine(*)\Utilization Percentage' -MaxSamples 1 -ErrorAction SilentlyContinue
    $jgBusy=@($jgGpu.CounterSamples | Where-Object {$_.CookedValue -ge 5 -and $_.InstanceName -match 'engtype_3d'} | ForEach-Object {
        $jgEnginePid=if($_.InstanceName -match 'pid_(\d+)_'){[int]$Matches[1]}else{0}
        [pscustomobject]@{pid=$jgEnginePid;process=(Get-Process -Id $jgEnginePid -ErrorAction SilentlyContinue).ProcessName;percent=$_.CookedValue;engine=$_.InstanceName}
    })
    $jgSamples.Add([pscustomobject]@{seconds=$jgTimer.Elapsed.TotalSeconds;utc=[DateTime]::UtcNow.ToString('o');foregroundPid=$jgForegroundPid;playerForeground=$jgForegroundPid -eq $jgPlayer.Id;gpu3D=$jgBusy})
    $jgProgress=[int][Math]::Floor($jgTimer.Elapsed.TotalSeconds/30)
    if($jgProgress -gt $jgLastProgress){$jgLastProgress=$jgProgress; Write-Output ('JG_CONTEXT '+([pscustomobject]@{seconds=[int]$jgTimer.Elapsed.TotalSeconds;playerPid=$jgPlayer.Id;foregroundPid=$jgForegroundPid;gpu=$jgBusy} | ConvertTo-Json -Depth 4 -Compress))}
    Start-Sleep -Milliseconds 1000
    $jgPlayer.Refresh()
}
[pscustomobject]@{playerPath=$jgPlayerPath;playerPid=$jgPlayer.Id;initialFocusRequestSucceeded=$jgFocusRequested;powerAtStart=$jgPower;playerExited=$jgPlayer.HasExited;samples=$jgSamples;limits='A fixed-camera diagnostic, not normal full-island play. Only one initial foreground request; later focus changes are observed. GPU counters are approximate utilization snapshots, not GPU frame time. Background processes are not stopped.'} | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $jgOut 'gpu-focus-context.json') -Encoding utf8
if(-not $jgPlayer.HasExited){throw 'Player still running after monitor timeout; no process was forcibly stopped.'}
Write-Output ('JG_CONTEXT_COMPLETE '+$jgOut)
