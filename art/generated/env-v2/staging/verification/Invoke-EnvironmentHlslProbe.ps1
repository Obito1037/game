#requires -Version 7.0
<#
Independent, in-memory DX11 HLSL probe. Does not launch Unity or write Assets.
FXC does not parse ShaderLab: variant pragmas are explicitly selected below.
The sole library compatibility substitution is an unused PopMarker() declaration.
Run from any directory with PowerShell 7:
  pwsh -File ./art/generated/env-v2/staging/verification/Invoke-EnvironmentHlslProbe.ps1
#>
param(
 [switch]$SmokeOnly,
 [ValidateSet('Meadow','TerrainSurface')][string[]]$ShaderNames=@('Meadow','TerrainSurface'),
 [ValidatePattern('^[A-Za-z0-9_.-]+\.json$')][string]$ReportName='meadow-surface-dx11.json'
)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../..'))
$stagingRoot=Split-Path -Parent $PSScriptRoot
$watch=[Diagnostics.Stopwatch]::StartNew()
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class EnvHlslProbe {
 [ComImport, Guid("8BA5FB08-5195-40e2-AC58-0D989C3A0102"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
 interface Blob { [PreserveSig] IntPtr GetBufferPointer(); [PreserveSig] UIntPtr GetBufferSize(); }
 [DllImport("d3dcompiler_47.dll", CallingConvention=CallingConvention.StdCall)]
 static extern int D3DCompile(byte[] source, UIntPtr length, [MarshalAs(UnmanagedType.LPStr)] string name, IntPtr defines, IntPtr includes,
 [MarshalAs(UnmanagedType.LPStr)] string entry, [MarshalAs(UnmanagedType.LPStr)] string target, uint flags1, uint flags2,
 [MarshalAs(UnmanagedType.Interface)] out Blob code, [MarshalAs(UnmanagedType.Interface)] out Blob errors);
 public static string Compile(string source, string name, string entry, string target) {
  byte[] bytes=Encoding.UTF8.GetBytes(source); Blob code,errors;
  int hr=D3DCompile(bytes,(UIntPtr)bytes.Length,name,IntPtr.Zero,IntPtr.Zero,entry,target,4096,0,out code,out errors);
  string message="";
  if(errors!=null) { message=Marshal.PtrToStringAnsi(errors.GetBufferPointer(),(int)errors.GetBufferSize()); Marshal.ReleaseComObject(errors); }
  ulong size=0;if(code!=null) { size=code.GetBufferSize().ToUInt64();Marshal.ReleaseComObject(code); }
  return "hr="+hr+" bytes="+size+"\n"+message;
 }
}
'@
$nl=[Environment]::NewLine
$packageMap=@{}
Get-ChildItem -Directory -LiteralPath (Join-Path $projectRoot 'GameProject/Library/PackageCache') | ForEach-Object { $packageMap[$_.Name.Split('@')[0]]=$_.FullName }
$flattenCache=@{}
function Expand-ProbeSource([string]$source,[string]$sourcePath) {
 [regex]::Replace($source,'(?m)^\s*#include(?:_with_pragmas)?\s+"([^"]+)"\s*$',{
  param($m)
  $includeName=$m.Groups[1].Value
  if ($includeName.StartsWith('Packages/')) {
   $parts=$includeName.Split('/',3); if (!$packageMap.ContainsKey($parts[1])) { return '#error PROBE_MISSING_PACKAGE '+$includeName+$nl }; $resolved=Join-Path $packageMap[$parts[1]] $parts[2]
  } else { $resolved=Join-Path (Split-Path -Parent $sourcePath) $includeName }
  if (!(Test-Path -LiteralPath $resolved)) { return '#error PROBE_MISSING_INCLUDE '+$includeName+$nl }
  if ($flattenCache.ContainsKey($resolved)) { return $flattenCache[$resolved] }
  $guard='ENV_PROBE_FILE_'+([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($resolved)))).Substring(0,20)
  $flattenCache[$resolved]=''
  $body=Get-Content -Raw -LiteralPath $resolved
  $body=[regex]::Replace($body,'(?m)^\s*#pragma once\s*$','')
  $flat=Expand-ProbeSource $body $resolved
  $resumeLine=($source.Substring(0,$m.Index+$m.Length).Split([char]10).Length+1)
  $result='#ifndef '+$guard+$nl+'#define '+$guard+$nl+'#line 1 "'+$resolved.Replace('\','/')+'"'+$nl+$flat+$nl+'#endif'+$nl+'#line '+$resumeLine+' "'+$sourcePath.Replace('\','/')+'"'+$nl
  $flattenCache[$resolved]=$result
  return $result
 })
}

function Get-ProbeVariants([string]$passName,[bool]$isMeadow) {
 $cases=[Collections.Generic.List[object]]::new()
 $cases.Add(@{Name='Base';Defines=@()})
 if($SmokeOnly) { return ,$cases }
 if($passName.EndsWith('Forward')) {
  $cases.Add(@{Name='SingleMainShadow';Defines=@('_MAIN_LIGHT_SHADOWS')})
  $cases.Add(@{Name='CascadePixelLights';Defines=@('_MAIN_LIGHT_SHADOWS_CASCADE','_ADDITIONAL_LIGHTS','_SHADOWS_SOFT')})
  $cases.Add(@{Name='ScreenMainShadow';Defines=@('_MAIN_LIGHT_SHADOWS_SCREEN','_ADDITIONAL_LIGHTS')})
  $cases.Add(@{Name='ForwardPlus';Defines=@('_CLUSTER_LIGHT_LOOP')})
  $all=@('_CLUSTER_LIGHT_LOOP','_MAIN_LIGHT_SHADOWS_CASCADE','_ADDITIONAL_LIGHT_SHADOWS','_SHADOWS_SOFT_MEDIUM','_SCREEN_SPACE_OCCLUSION','INSTANCING_ON','FOG_EXP2')
  if($isMeadow) { $all+='LOD_FADE_CROSSFADE' } else { $all+='_LIGHT_COOKIES' }
  $cases.Add(@{Name='ForwardPlusCombined';Defines=$all})
  $cases.Add(@{Name='VertexAdditionalLights';Defines=@('_ADDITIONAL_LIGHTS_VERTEX')})
  $cases.Add(@{Name='Instanced';Defines=@('INSTANCING_ON')})
  foreach($fog in @('FOG_LINEAR','FOG_EXP','FOG_EXP2')) { $cases.Add(@{Name=$fog;Defines=@($fog)}) }
  if($isMeadow) {
   $cases.Add(@{Name='LodCrossfade';Defines=@('LOD_FADE_CROSSFADE')})
  } else {
   $cases.Add(@{Name='ForwardCookies';Defines=@('_ADDITIONAL_LIGHTS','_LIGHT_COOKIES','_MAIN_LIGHT_SHADOWS','INSTANCING_ON')})
  }
 } elseif($passName.EndsWith('ShadowCaster')) {
  $cases.Add(@{Name='Punctual';Defines=@('_CASTING_PUNCTUAL_LIGHT_SHADOW')})
  $cases.Add(@{Name='Instanced';Defines=@('INSTANCING_ON')})
  $combined=@('_CASTING_PUNCTUAL_LIGHT_SHADOW','INSTANCING_ON')
  if($isMeadow) { $combined+='LOD_FADE_CROSSFADE' }
  $cases.Add(@{Name='PunctualInstanced';Defines=$combined})
 } elseif($passName.EndsWith('DepthNormals')) {
  $cases.Add(@{Name='OctNormals';Defines=@('_GBUFFER_NORMALS_OCT')})
  $cases.Add(@{Name='Instanced';Defines=@('INSTANCING_ON')})
  $combined=@('_GBUFFER_NORMALS_OCT','INSTANCING_ON')
  if($isMeadow) { $combined+='LOD_FADE_CROSSFADE' }
  $cases.Add(@{Name='OctInstanced';Defines=$combined})
 } elseif($passName.EndsWith('DepthOnly')) {
  $cases.Add(@{Name='Instanced';Defines=@('INSTANCING_ON')})
  if($isMeadow) {
   $cases.Add(@{Name='LodCrossfade';Defines=@('LOD_FADE_CROSSFADE')})
   $cases.Add(@{Name='LodInstanced';Defines=@('LOD_FADE_CROSSFADE','INSTANCING_ON')})
  }
 }
 return ,$cases
}
$results=[Collections.Generic.List[object]]::new()
$sourceRecords=[Collections.Generic.List[object]]::new()
foreach($shaderName in $ShaderNames) {
 $shaderPath=Join-Path $stagingRoot ('Shaders/'+$shaderName+'.shader')
 $shader=Get-Content -Raw -LiteralPath $shaderPath
 $sourceRecords.Add(@{path=$shaderPath;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $shaderPath).Hash})
 $shared=[regex]::Match($shader,'(?s)HLSLINCLUDE(.*?)ENDHLSL').Groups[1].Value
 $passes=[regex]::Matches($shader,'(?s)\bPass\s*\{(.*?)HLSLPROGRAM(.*?)ENDHLSL\s*\}')
 if($passes.Count -ne 4) { throw "Expected exactly 4 HLSL passes in $shaderName, found $($passes.Count)" }
 foreach($pass in $passes) {
  $passName=[regex]::Match($pass.Groups[1].Value,'Name\s+"([^"]+)"').Groups[1].Value
  $program=$pass.Groups[2].Value
  $vertexEntry=[regex]::Match($program,'#pragma\s+vertex\s+(\w+)').Groups[1].Value
  $fragmentEntry=[regex]::Match($program,'#pragma\s+fragment\s+(\w+)').Groups[1].Value
  $hasFog=$program.Contains('/Fog.hlsl')
  $vertexOnly=@();$fragmentOnly=@()
  foreach($line in [regex]::Matches($program,'#pragma\s+multi_compile_(vertex|fragment)\s+([^\r\n]+)')) {
   $keywords=@($line.Groups[2].Value -split '\s+' | Where-Object { $_ -ne '_' -and $_ })
   if($line.Groups[1].Value -eq 'vertex') { $vertexOnly+=$keywords } else { $fragmentOnly+=$keywords }
  }
  $combined=$shared+$nl+$program
  $combined=[regex]::Replace($combined,'(?m)^\s*#pragma\s+(target|vertex|fragment|multi_compile\w*).*$', '')
  $flat=Expand-ProbeSource $combined $shaderPath
  # Native FXC does not understand Unity pragma declarations inside Fog.hlsl.
  $flat=[regex]::Replace($flat,'(?m)^\s*#pragma\s+(multi_compile\w*|dynamic_branch).*$', '')
  if($flat -match '(?m)^\s*(?!#).*?\bPopMarker\s*\(') { throw 'Probe cannot alter a library macro that is called by source.' }
  $flat=$flat.Replace('#define PopMarker()','#define PopMarker(unused)')
  $preamble='#define SHADER_API_D3D11 1'+$nl+'#define SHADER_TARGET 35'+$nl+'#define UNITY_COMPILER_HLSL 1'+$nl
  $variants=Get-ProbeVariants $passName ($shaderName -eq 'Meadow')
  foreach($variant in $variants) {
   foreach($stage in @('vertex','fragment')) {
    $profile=if($stage -eq 'vertex') {'vs_4_0'}else{'ps_4_0'}
    $entry=if($stage -eq 'vertex') {$vertexEntry}else{$fragmentEntry}
    $stageDefines=if($stage -eq 'vertex') {'#define SHADER_STAGE_VERTEX 1'+$nl}else{'#define SHADER_STAGE_FRAGMENT 1'+$nl}
    $active=@($variant.Defines | Where-Object { if($stage -eq 'vertex') { $_ -notin $fragmentOnly }else{ $_ -notin $vertexOnly } })
    $defines=($active | ForEach-Object { '#define '+$_+' 1'+$nl }) -join ''
    # Unity emits declared-keyword metadata; emulate only selected static fog branches.
    if($hasFog) {
     foreach($fog in @('FOG_LINEAR','FOG_EXP','FOG_EXP2')) {
      if($active -contains $fog) { $defines+='#define '+$fog+'_KEYWORD_DECLARED 1'+$nl }
     }
    }
    $compile=[EnvHlslProbe]::Compile(($preamble+$stageDefines+$defines+$flat),$shaderPath,$entry,$profile)
    $prefix=[regex]::Match($compile,'^hr=(-?\d+) bytes=(\d+)\r?\n')
    if(!$prefix.Success) { throw 'Unrecognized native compiler result.' }
    $entryResult=[ordered]@{
     shader=$shaderName;pass=$passName;variant=$variant.Name;stage=$stage;entry=$entry;profile=$profile
     keywords=$active;hresult=[int]$prefix.Groups[1].Value;bytecodeBytes=[int]$prefix.Groups[2].Value
     diagnostics=$compile.Substring($prefix.Length).TrimEnd([char]0,[char]13,[char]10)
    }
    $results.Add($entryResult)
    if($entryResult.hresult -ne 0) { Write-Host ('FAIL '+$shaderName+'/'+$passName+'/'+$variant.Name+'/'+$stage+': '+$entryResult.diagnostics) }
   }
  }
  Write-Host ('Checked '+$shaderName+'/'+$passName+' '+$variants.Count+' variants x 2 stages.')
 }
}
$watch.Stop()
$failures=@($results | Where-Object { $_.hresult -ne 0 })
$compilerPath='C:/Windows/System32/D3DCompiler_47.dll'
$report=[ordered]@{
 schema='jieguang-offline-hlsl-probe-v1';timestampUtc=[DateTime]::UtcNow.ToString('o')
 scriptSha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash
 smokeOnly=[bool]$SmokeOnly;elapsedSeconds=[Math]::Round($watch.Elapsed.TotalSeconds,3)
 compiler=@{path=$compilerPath;fileVersion=(Get-Item -LiteralPath $compilerPath).VersionInfo.FileVersion;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $compilerPath).Hash;flags=4096}
 platform='D3D11';shaderTarget=35;shaderModelProfiles=@('vs_4_0','ps_4_0')
 sources=$sourceRecords
 passCount=$results.Count;successCount=($results.Count-$failures.Count);failureCount=$failures.Count
 scope='Independent D3DCompile HLSL check only. Not Unity import/ShaderLab or GLSL/WebGL compilation; no rendering.'
 fixtureAdjustments=@('Extract HLSLINCLUDE and each HLSLPROGRAM; strip Unity pragmas; select keywords manually.',
 'Expand actual package includes in memory with separate guards; missing inactive private-platform packages become conditional #error.',
 'Unused library declaration PopMarker() becomes PopMarker(unused) in memory for native FXC; disk package files untouched.',
 'For selected static FOG_* variants, define the matching FOG_*_KEYWORD_DECLARED metadata manually.',
 'Respect vertex-only and fragment-only multi_compile keywords for each stage. No DOTS/XR/native-half coverage.')
 results=$results
}
$reportPath=Join-Path $PSScriptRoot $ReportName
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8
[pscustomobject]@{report=$reportPath;success=$report.successCount;failed=$report.failureCount;elapsedSeconds=$report.elapsedSeconds} | ConvertTo-Json -Compress
if($failures.Count -gt 0) { exit 1 }

