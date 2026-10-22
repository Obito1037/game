const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'art/verification');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase();
const model=read('art/generated/character-v8/traveler-manifest.json'),old=read('art/verification/v8-release-source/source-files.json');
const archive=path.join(dir,'v9-release-source');fs.mkdirSync(archive,{recursive:true});
const allowed=new Set(['WorldDirector.cs','WorldVisualDiagnostics.cs']);
const sources=old.map(x=>{
 const sha256=hash(x.source),changed=sha256!==x.sha256;
 assert(!changed||allowed.has(path.basename(x.source)),`Unexpected protected source change: ${x.source}`);
 fs.copyFileSync(path.join(root,x.source),path.join(archive,path.basename(x.source)));
 return {source:x.source,sha256,changedFromV8:changed};
});
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx'),model.sha256['traveler.fbx'].toUpperCase());
const worldSHA=hash('GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx');
assert.equal(worldSHA,'91C6D643698C414D0582D86AA42EBFAA1E470124DDDD7FAA7852860877806F64');
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Textures/Meadow.png'),'889C373C911C8FD5E4BE519CBBC957436909B380481D1DE22051BB22EF0D3C7F');
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Textures/MeadowNormal.png'),'BBAF18FC6DD0F38E7D0E3FBA17B98AE72FD55D47597971FFCC712460B2C321BC');
const native=read('art/verification/run-024-v9/runtime-results.json'),boulders=read('art/verification/run-024-v9/boulder-approaches.json');
const web=read('art/verification/web-010-v9/runtime-results.json'),builds=read('art/verification/v9-build-reports.json');
const geometryCompare=read('art/verification/v9-face-study-candidate/capture-condition-comparison.json'),eyeCompare=read('art/verification/v9-face-study-eye-material/capture-condition-comparison.json');
assert(geometryCompare.captureConditionsPassed&&eyeCompare.captureConditionsPassed&&boulders.allPassed&&web.passed&&native.scrollZoomWorks);
const report={revision:'v9',date:'2026-10-21',worldFbxSHA256:worldSHA,travelerFbxSHA256:model.sha256['traveler.fbx'].toUpperCase(),
 geometry:{worldTriangles:412815,worldMeshes:29,travelerTriangles:model.triangles,travelerRenderers:62,skinnedRenderers:28,armatures:4,bones:12},
 preservation:{character:'../generated/character-v8/v7-preservation-file-verification.json',nonTargetMeshesUnchanged:48,nonTargetMaterialsUnchanged:26,allRigsPivotsAttachmentsPreserved:true,worldAndGroundBytesUnchanged:true,protectedSources:sources.filter(x=>!allowed.has(path.basename(x.source)))},
 characterNormalLimit:'FBX all modified-head corner normals passed (max .0445 degrees). GLB strict all-corner check fails at six zero-area line endpoints; drawable faces passed (max .2015 degrees).',
 faceStudy:{geometry:'v9-face-study-candidate/capture-condition-comparison.json',eyeMaterial:'v9-face-study-eye-material/capture-condition-comparison.json',bothConditionsPassed:true,stagedScope:'Bind pose and closer fixed camera, not normal gameplay or performance evidence',eyeSmoothness:{Ivory:.18,AmberRim:.32,Chestnut:.32,Pupil:.5,Catchlight:.72},faceFill:.23,skinShaderUnchanged:true},
 groundCandidate:{adopted:false,review:'v9-ground-contact-study/review.zh-CN.txt',statisticsCorrection:'Encoded-vs-linear darkening labeling error corrected in retained candidate audit; no candidate pixels shipped.'},
 native:{buildId:builds.native.buildId,evidence:'run-024-v9/runtime-results.json',results:native,boulderApproaches:boulders.probes.length,boulderChecksPassed:boulders.allPassed},
 web:{buildId:builds.web.buildId,evidence:'web-010-v9/runtime-results.json',passed:web.passed,errors:web.errors,engineDiagnostics:web.engineDiagnostics,payload:builds.web.payload,walkingViewStoppedIntervalMedian:web.performanceViews.find(v=>v.view==='walking').medianIntervalFps,endingIntervalMedian:web.performanceViews.find(v=>v.view==='ending').medianIntervalFps},
 dynamicPortrait:{capture:'web-v9-portrait-video/capture-manifest.json',review:'web-v9-portrait-video/review.json'},
 scrollFix:{normalizedStepMetres:.35,legacyCoefficient:.004,nativeNormalizedInputCheck:native.scrollZoomWorks,minimumDistance:2.5,maximumDistance:10,diagnostic:'web-v9-portrait-wheel-diagnostic/diagnostic.json'},
 limits:['Overall aesthetic objective remains unachieved.','Native/browser short samples are not continuous movement averages, minima or isolated performance gains.','No new GPU profile. Older observatory/gait recordings remain historical.','Actual portrait footage has limited resolution and pose coverage; it cannot prove every eyelid intermediate.'],aestheticObjectiveAchieved:false};
fs.writeFileSync(path.join(archive,'source-files.json'),JSON.stringify(sources,null,2));
fs.writeFileSync(path.join(dir,'v9-integration-checks.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({sources:sources.length,changed:sources.filter(s=>s.changedFromV8).map(s=>s.source),modelsAndGroundMatch:true,nativeBuild:builds.native.buildId,webBuild:builds.web.buildId}));
