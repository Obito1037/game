'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),prefix='GameProject/Assets/BorrowedLight/';
const read=file=>JSON.parse(fs.readFileSync(path.join(root,file),'utf8').replace(/^\uFEFF/,''));
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex').toUpperCase();
const baseline=read('art/verification/v13-release-source/source-files.json');
const changed=baseline.map(row=>({source:row.source,baselineSHA256:row.sha256,currentSHA256:hash(row.source)})).filter(row=>row.baselineSHA256.toUpperCase()!==row.currentSHA256);
assert.deepEqual(changed.map(row=>row.source),[prefix+'Runtime/WorldDirector.cs']);
const entries=['    if(args[i]=="-borrowedLightFaceLightStudy"){StartCoroutine(FaceLightStudy(args[i+1]));break;}\n','    if(args[i]=="-borrowedLightFaceContributionStudy"){StartCoroutine(FaceLightStudy(args[i+1],true));break;}\n','    if(args[i]=="-borrowedLightFaceBalanceStudy"){StartCoroutine(FaceLightStudy(args[i+1],true,true));break;}\n'];
const director=fs.readFileSync(path.join(root,changed[0].source),'utf8').replace(/\r\n/g,'\n');
const previous=baseline.find(row=>row.source===changed[0].source);
const previousDirector=fs.readFileSync(path.join(root,'art/verification/v13-release-source',previous.snapshot),'utf8').replace(/\r\n/g,'\n');
let normalDirector=director;for(const entry of entries){assert.equal(normalDirector.split(entry).length,2);normalDirector=normalDirector.replace(entry,'');}
const added=['Runtime/WorldFaceLightStudy.cs','Runtime/WorldFaceLightStudy.cs.meta'].map(file=>({source:prefix+file,sha256:hash(prefix+file)}));
const qa=read('art/verification/run-035-v14/runtime-results.json');
const required=['puzzleCompleted','menuKeyboardStart','pauseStopsMovement','resumeMovement','restartWorks','endingReturnWorks','cabinCollisionWorks','walkwayGroundingWorks','boulderCollisionWorks','observatoryGroundingWorks','observatoryInstrumentCollisionWorks','decorativeLeavesExcluded','pierGroundingWorks','pierRailCollisionWorks','scrollZoomWorks'];
for(const key of required)assert.equal(qa[key],true,key);
assert.equal(hash(prefix+'Resources/Models/Traveler.fbx'),'58E808F1AEC15F3E960E96E57B9484284BF7B9B214DE511D036C1567761B828B');
assert.equal(hash(prefix+'Resources/Models/Traveler.fbx.meta'),'1D61D3065894AD590DD356D5970F87888D5A5C2FE87768A233E40542577A240B');
const report={revision:'v14-candidate',stableRelease:'v13',recordedAtUTC:new Date().toISOString(),releaseReady:false,aestheticObjectiveAchieved:false,
 status:'Blender character-v11 with gentler carried light and neutral face fill in a tested independent Windows candidate. Stable Windows/Web/ZIP remain v13. Face geometry remains under development.',
 nativeBuild:'build_4c8f842d85ef',nativeCandidate:'builds/candidates/v14-balanced-light/windows/BorrowedLight.exe',nativeQA:'art/verification/run-035-v14/runtime-results.json',nativeFunctionalChecksPassed:true,
 character:{source:'art/generated/character-v11/',fbxSHA256:hash(prefix+'Resources/Models/Traveler.fbx'),authoringTriangles:81968,unityTriangles:81964,readback:'art/verification/v14-character-v11-fbx/fbx-readback.json'},
 sourceAudit:{baseline:'art/verification/v13-release-source/source-files.json',baselineFilesCompared:baseline.length,changedTrackedFiles:changed,addedDiagnosticFiles:added,normalDirectorUnchangedAfterRemovingDiagnosticEntries:normalDirector===previousDirector,normalChanges:['Carried light intensity .52 to .18; colour/range/anchor unchanged.','Face fill colour (1,.88,.74) to (1,.95,.88); intensity/range/position unchanged.']},
 geometryReview:'art/verification/v14-face-geometry-candidate/decision.json',reviewPage:'art/verification/visual-review-v14-character.html',
 rejectedLighting:'art/verification/v14-face-light-position-refined/decision.json',rejectedCharacter:'art/generated/character-v10/',
 lightContributionStudy:'art/verification/v14-face-contribution/face-light-study.json',lightBalanceStudy:'art/verification/v14-face-balance/face-light-study.json',lightDecision:'art/verification/v14-face-balance/decision.json',
 limits:['No candidate WebGL build or release ZIP.','Gray cheek region, simplified nose/mouth, fixed gaze and grooved hair remain; overall aesthetic target unachieved.','Static blink endpoints and short normal QA do not cover all animation poses.','Four inherited zero-area lower-lid endpoint triangles recorded; no new GLB export.'],
 geometryExperiments:[{source:'art/generated/character-v12/',accepted:false,decision:'art/generated/character-v12/decision.json'},{source:'art/generated/character-v13/',accepted:false,decision:'art/generated/character-v13/decision.json'}],
 nextAction:'Keep the tested v11 head and balanced lights. The nose/mouth cage experiments did not clearly improve naturalness; next improve eyelid/iris integration and expression at gameplay scale with a distinct, controlled character candidate.'};
fs.writeFileSync(path.join(root,'art/verification/v14-work-in-progress.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({recorded:true,stableRelease:'v13',candidate:report.nativeBuild,trackedFiles:baseline.length,changedTrackedFiles:changed.length,addedDiagnosticFiles:added.length,nativeFunctionalChecksPassed:true,releaseReady:false}));
