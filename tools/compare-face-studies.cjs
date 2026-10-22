// Compare actual Player capture conditions. Visual quality still requires image review.
const fs = require('node:fs');
const path = require('node:path');
const [baselineDir, candidateDir] = process.argv.slice(2).map(p => path.resolve(p));
if (!baselineDir || !candidateDir) throw new Error('Usage: node compare-face-studies.cjs baselineDir candidateDir');
const read = dir => JSON.parse(fs.readFileSync(path.join(dir, 'face-study.json'), 'utf8').replace(/^\uFEFF/, ''));
const a = read(baselineDir), b = read(candidateDir);
const close = (x, y) => typeof x === 'number' && typeof y === 'number' ? Math.abs(x - y) < 0.00001 :
  x && y && typeof x === 'object' && typeof y === 'object' ? Object.keys(x).length === Object.keys(y).length && Object.keys(x).every(k => close(x[k], y[k])) : x === y;
const pick = (x, keys) => Object.fromEntries(keys.map(k => [k, x[k]]));
const cameraKeys = ['image','cameraPosition','cameraRotation','fieldOfView','eyesClosed'];
const sceneKeys = ['width','height','travelerPosition','travelerRotation','lookTarget','night','fillIntensity'];
const lights = x => [...x.lights].sort((p,q) => p.name.localeCompare(q.name));
const captures = (dir, study) => study.views.map(v => {
  const filename = path.join(dir, v.image), buffer = fs.readFileSync(filename);
  const validPNG = buffer.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]));
  return {image:v.image, bytes:buffer.length, validPNG,
    dimensionsMatch:validPNG && buffer.readUInt32BE(16) === study.width && buffer.readUInt32BE(20) === study.height};
});
const materialChanges = [];
const materialsA = new Map(a.materials.map(m => [m.name,m]));
for (const m of b.materials) if (!close(materialsA.get(m.name), m)) materialChanges.push({name:m.name,baseline:materialsA.get(m.name),candidate:m});
const report = {purpose:'Capture-condition verification, not an automatic aesthetic judgment. Frozen times/background shader animation can differ.',
  baselineDir,candidateDir,sceneConditionsMatch:close(pick(a,sceneKeys),pick(b,sceneKeys)),
  viewConditionsMatch:close(a.views.map(v=>pick(v,cameraKeys)),b.views.map(v=>pick(v,cameraKeys))),
  lightsMatch:close(lights(a),lights(b)),bodyPosesStable:a.allBodyPosesUnchanged && b.allBodyPosesUnchanged,
  captures:{baseline:captures(baselineDir,a),candidate:captures(candidateDir,b)},materialChanges,
  removedMaterials:a.materials.filter(m=>!b.materials.some(n=>n.name===m.name)).map(m=>m.name)};
report.captureConditionsPassed=report.sceneConditionsMatch && report.viewConditionsMatch && report.lightsMatch && report.bodyPosesStable && Object.values(report.captures).flat().every(c=>c.validPNG && c.dimensionsMatch);
fs.writeFileSync(path.join(candidateDir,'capture-condition-comparison.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if (!report.captureConditionsPassed) process.exitCode=1;
