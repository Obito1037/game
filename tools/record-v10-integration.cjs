const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'art/verification');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase();
const write=(p,x)=>fs.writeFileSync(path.join(root,p),JSON.stringify(x,null,2)+'\n');
const model=read('art/generated/character-v9/traveler-manifest.json');
const allowed=new Set(['WorldDirector.cs','PaintedSurface.shader','FoliagePaint.shader']);
const old=read('art/verification/v9-release-source/source-files.json');
const added=['GameProject/Assets/BorrowedLight/Runtime/WorldMaterialStudy.cs','GameProject/Assets/BorrowedLight/Shaders/FoliageSurface.hlsl','GameProject/Assets/BorrowedLight/Resources/Materials/PaintedRockV10.mat','GameProject/Assets/BorrowedLight/Resources/Textures/StoneV10.png.meta'];
const archive=path.join(dir,'v10-release-source');fs.mkdirSync(archive,{recursive:true});
const sources=old.map(x=>{const sha256=hash(x.source),changed=sha256!==x.sha256;assert(!changed||allowed.has(path.basename(x.source)),`Unexpected source change: ${x.source}`);return {source:x.source,sha256,changedFromV9:changed};});
sources.push(...added.map(source=>({source,sha256:hash(source),addedInV10:true})));
for(const x of sources)fs.copyFileSync(path.join(root,x.source),path.join(archive,path.basename(x.source)));
write('art/verification/v10-release-source/source-files.json',sources);
assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Models/Traveler.fbx'),model.sha256['traveler.fbx'].toUpperCase());
const unchanged={
 'GameProject/Assets/BorrowedLight/Resources/Models/Island.fbx':'91C6D643698C414D0582D86AA42EBFAA1E470124DDDD7FAA7852860877806F64',
 'GameProject/Assets/BorrowedLight/Resources/Textures/Meadow.png':'889C373C911C8FD5E4BE519CBBC957436909B380481D1DE22051BB22EF0D3C7F',
 'GameProject/Assets/BorrowedLight/Resources/Textures/MeadowNormal.png':'BBAF18FC6DD0F38E7D0E3FBA17B98AE72FD55D47597971FFCC712460B2C321BC'};
for(const [file,expected] of Object.entries(unchanged))assert.equal(hash(file),expected,file);
const image=read('art/generated/stone-v10/manifest.json');assert.equal(hash('GameProject/Assets/BorrowedLight/Resources/Textures/StoneV10.png'),image.sha256);
const native=read('art/verification/run-025-v10/runtime-results.json'),boulders=read('art/verification/run-025-v10/boulder-approaches.json');
const web=read('art/verification/web-011-v10/runtime-results.json'),builds=read('art/verification/v10-build-reports.json');
const silhouette=read('art/verification/v10-silhouette-candidate/capture-condition-comparison.json');
const foliage=read('art/verification/v10-foliage-study/review.json');
const motion=read('art/verification/web-v10-gait-video/review.json');
assert(silhouette.passed&&foliage.reviewed&&foliage.acceptedForLimitedScope&&boulders.allPassed&&web.passed&&native.scrollZoomWorks);
assert(motion.reviewed&&motion.acceptedForLimitedScope);
write('art/verification/v10-integration-checks.json',{
 revision:'v10',world:'world-v7',character:'character-v9',travelerFbxSHA256:model.sha256['traveler.fbx'].toUpperCase(),
 geometry:{worldTriangles:412815,travelerTriangles:model.triangles,travelerRenderers:62,skinned:28,bones:12},
 characterScope:'Seven silhouette meshes modified; 55 non-target meshes and all weights, rigs, material values, face/eyes, soles, hands and attachments retained. Three protected-connection pose checks pass.',
 interchangeLimit:'Seven target mesh FBX/GLB corner-normal checks pass. The prior character-v8 strict GLB failure at six zero-area non-target endpoints is inherited, not newly retested as globally passed.',
 worldAndGroundBytesUnchanged:true,generatedStone:image,
 shaderScope:{heroRock:'Texture triplanar colour/roughness and shallow artistic luminance relief',foliage:'Fixed40: shared wind and double-sided normal handling in Forward/DepthNormals; synchronized positions in depth/shadows',fixed20Adopted:false,aoSettingsChanged:false,lightingChanged:false},
 staticStudies:{stone:'v10-stone-study/decision.json',foliage:'v10-foliage-study/review.json',silhouette:'v10-silhouette-candidate/decision.json',repeatLimit:'Frozen transforms and time do not freeze per-camera SSAO blue-noise selection and random offsets. A/A captures are not pixel-identical.'},
 native:{buildId:builds.native.buildId,evidence:'run-025-v10/runtime-results.json',results:native,boulderApproaches:boulders.probes.length,boulderChecksPassed:boulders.allPassed},
 web:{buildId:builds.web.buildId,evidence:'web-011-v10/runtime-results.json',passed:web.passed,errors:web.errors,engineDiagnostics:web.engineDiagnostics,payload:builds.web.payload},
 motion:{capture:'web-v10-gait-video/capture-manifest.json',review:'web-v10-gait-video/review.json'},
 limits:['Short native/browser FPS samples are not full-session averages/minima or evidence of isolated performance gains.','No new GPU profile.','Motion review covers only the recorded route and inspected frames.','Foliage shape and cloth/skin shading remain simplified. Overall aesthetic objective remains unachieved.'],aestheticObjectiveAchieved:false
});
console.log(JSON.stringify({sources:sources.length,changed:sources.filter(x=>x.changedFromV9).map(x=>x.source),native:builds.native.buildId,web:builds.web.buildId}));
