// Compare staged character-study conditions; image quality is reviewed separately.
const fs=require('node:fs'),path=require('node:path');
const [aDir,bDir]=process.argv.slice(2).map(p=>path.resolve(p));
if(!aDir||!bDir)throw Error('Supply baseline and candidate directories');
const read=dir=>JSON.parse(fs.readFileSync(path.join(dir,'material-study.json'),'utf8').replace(/^\uFEFF/,''));
const a=read(aDir),b=read(bDir);
const close=(x,y)=>typeof x==='number'&&typeof y==='number'?Math.abs(x-y)<1e-5:x&&y&&typeof x==='object'&&typeof y==='object'?Object.keys(x).length===Object.keys(y).length&&Object.keys(x).every(k=>close(x[k],y[k])):x===y;
const pick=(x,keys)=>Object.fromEntries(keys.map(k=>[k,x[k]]));
const viewKeys=['image','variant','cameraPosition','cameraRotation','fieldOfView'];
const sceneKeys=['materialFamily','width','height','frozenTime','night'];
const lights=x=>[...x.lights].sort((p,q)=>p.name.localeCompare(q.name));
const report={scope:'Scene/camera/light invariants only. Model identity is established by build/import evidence. Temporal AO is not frozen by Time.timeScale=0.',
 baseline:aDir,candidate:bDir,sceneMatch:close(pick(a,sceneKeys),pick(b,sceneKeys)),viewMatch:close(a.views.map(x=>pick(x,viewKeys)),b.views.map(x=>pick(x,viewKeys))),lightsMatch:close(lights(a),lights(b)),bothStable:a.allInvariantsPassed&&b.allInvariantsPassed};
report.passed=report.sceneMatch&&report.viewMatch&&report.lightsMatch&&report.bothStable;
if(a.geometryStudy||b.geometryStudy){
 const expected=['path','island','left-tree','gold-tree','right-pine'].flatMap(n=>['current','repeat'].map(v=>`${n}-${v}.png`));
 const complete=(record,dir)=>record.materialFamily==='tree-geometry'&&record.geometryStudy===true&&record.completed===true&&record.failed===false&&record.captureComplete===true&&record.expectedImageCount===10&&record.capturedImageCount===10&&record.views.length===expected.length&&
  record.views.every((v,i)=>{
   if(!v||v.image!==expected[i]||v.actualPNGWidth!==record.width||v.actualPNGHeight!==record.height||!v.transformsAndLightsUnchanged||!v.materialsUnchanged)return false;
   const file=path.join(dir,v.image);if(!fs.existsSync(file))return false;const png=fs.readFileSync(file);
   return png.length>=36&&png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))&&png.subarray(-12).equals(Buffer.from([0,0,0,0,73,69,78,68,174,66,96,130]))&&png.readUInt32BE(16)===record.width&&png.readUInt32BE(20)===record.height;
  });
 const ambientKeys=['ambientSky','ambientEquator','ambientGround','ambientIntensity','ambientMode'];
 report.treeConditions={completeCaptures:complete(a,aDir)&&complete(b,bDir),
  materialsMatch:Array.isArray(a.materialConditions)&&a.materialConditions.length>0&&close(a.materialConditions,b.materialConditions),
  ambientMatch:close(pick(a,ambientKeys),pick(b,ambientKeys)),
  targetsMatch:close([...a.targetRenderers].sort(),[...b.targetRenderers].sort()),
  viewDetailsMatch:close(a.views.map(x=>pick(x,['lookTarget','actualPNGWidth','actualPNGHeight'])),b.views.map(x=>pick(x,['lookTarget','actualPNGWidth','actualPNGHeight'])))};
 report.passed&&=Object.values(report.treeConditions).every(x=>x===true);
}
fs.writeFileSync(path.join(bDir,'capture-condition-comparison.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
