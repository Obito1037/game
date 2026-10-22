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
fs.writeFileSync(path.join(bDir,'capture-condition-comparison.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
