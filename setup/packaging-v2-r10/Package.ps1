$ErrorActionPreference='Stop'
$jgRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$jgPackages=Join-Path $jgRoot 'builds/packages'
$jgEvidence=Join-Path $jgRoot 'art/verification/game-v2-final'
New-Item -ItemType Directory -Path $jgPackages -Force | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$jgResults=[System.Collections.Generic.List[object]]::new()
foreach($jgPlatform in @('windows','web')){
    $jgSource=Join-Path $jgRoot ('builds/candidates/jieguang-v2-r10/'+$jgPlatform)
    $jgName=if($jgPlatform -eq 'windows'){'JieGuang-v2-r10-Windows.zip'}else{'JieGuang-v2-r10-WebGL.zip'}
    $jgZip=Join-Path $jgPackages $jgName
    if(Test-Path -LiteralPath $jgZip){throw ('Package already exists; preserve it: '+$jgZip)}
    [System.IO.Compression.ZipFile]::CreateFromDirectory($jgSource,$jgZip,[System.IO.Compression.CompressionLevel]::Fastest,$false)
    $jgAdditions=@(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot $jgPlatform) -File)
    if($jgPlatform -eq 'web'){$jgAdditions+=Get-Item -LiteralPath (Join-Path $jgRoot 'tools/serve-game.cjs')}
    $jgArchive=[System.IO.Compression.ZipFile]::Open($jgZip,[System.IO.Compression.ZipArchiveMode]::Update)
    try{foreach($jgFile in $jgAdditions){[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($jgArchive,$jgFile.FullName,$jgFile.Name,[System.IO.Compression.CompressionLevel]::Fastest) | Out-Null}}finally{$jgArchive.Dispose()}
    $jgExpected=@{}
    Get-ChildItem -LiteralPath $jgSource -Recurse -File | ForEach-Object {$jgExpected[$_.FullName.Substring($jgSource.Length+1).Replace('\','/')]=$_.Length}
    foreach($jgFile in $jgAdditions){$jgExpected[$jgFile.Name]=$jgFile.Length}
    $jgArchive=[System.IO.Compression.ZipFile]::OpenRead($jgZip)
    try{
        $jgEntries=@($jgArchive.Entries | Where-Object { $_.Name -ne '' })
        if($jgEntries.Count -ne $jgExpected.Count){throw 'ZIP entry count differs from source inventory.'}
        foreach($jgEntry in $jgEntries){if(-not $jgExpected.ContainsKey($jgEntry.FullName) -or $jgExpected[$jgEntry.FullName] -ne $jgEntry.Length){throw ('ZIP entry mismatch: '+$jgEntry.FullName)}}
        $jgCritical=if($jgPlatform -eq 'windows'){@('JieGuang.exe','UnityPlayer.dll')}else{@('index.html','serve-game.cjs','Start-Web.ps1')+@($jgExpected.Keys | Where-Object {$_ -like 'Build/*.wasm.unityweb' -or $_ -like 'Build/*.data.unityweb'})}
        $jgVerified=@(foreach($jgNameInZip in $jgCritical){
            $jgEntry=$jgArchive.GetEntry($jgNameInZip)
            if(-not $jgEntry){throw ('Missing critical entry '+$jgNameInZip)}
            $jgStream=$jgEntry.Open(); $jgSha=[Security.Cryptography.SHA256]::Create()
            try{$jgHash=[BitConverter]::ToString($jgSha.ComputeHash($jgStream)).Replace('-','').ToLowerInvariant()}finally{$jgSha.Dispose();$jgStream.Dispose()}
            $jgOriginal=if($jgNameInZip -in @('serve-game.cjs','Start-Web.ps1')){($jgAdditions | Where-Object Name -eq $jgNameInZip).FullName}else{Join-Path $jgSource $jgNameInZip}
            $jgOriginalHash=(Get-FileHash -LiteralPath $jgOriginal -Algorithm SHA256).Hash.ToLowerInvariant()
            if($jgHash -ne $jgOriginalHash){throw ('ZIP payload differs: '+$jgNameInZip)}
            [pscustomobject]@{entry=$jgNameInZip;sha256=$jgHash;matchesSource=$true}
        })
        $jgEntryCount=$jgEntries.Count
    }finally{$jgArchive.Dispose()}
    $jgResult=[pscustomobject]@{platform=$jgPlatform;path=$jgZip;bytes=(Get-Item -LiteralPath $jgZip).Length;sha256=(Get-FileHash -LiteralPath $jgZip -Algorithm SHA256).Hash.ToLowerInvariant();entries=$jgEntryCount;allEntryPathsAndLengthsMatch=$true;criticalPayloads=$jgVerified}
    $jgResults.Add($jgResult)
    Write-Output ('JG_PACKAGE '+($jgResult | Select-Object platform,path,bytes,entries | ConvertTo-Json -Compress))
}
[pscustomobject]@{candidate='jieguang-v2-r10';createdUtc=[DateTime]::UtcNow.ToString('o');method='ZIP entry inventory and uncompressed lengths compared to all source files; critical entries decompressed and SHA-256 matched. This package verification does not add gameplay coverage.';packages=$jgResults} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $jgEvidence 'packages-r10.json') -Encoding utf8
