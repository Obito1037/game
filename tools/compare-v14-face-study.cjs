'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base='art/verification/v14-face-geometry-baseline',candidate='art/verification/v14-face-geometry-candidate';
const read=dir=>JSON.parse(fs.readFileSync(path.join(root,dir,'face-study.json'),'utf8').replace(/^\uFEFF/,''));
const a=read(base),b=read(candidate),names=['01-front-open.png','02-three-quarter-open.png','03-side-open.png','04-front-closed.png','05-front-open-repeat.png'];
const sort=rows=>[...rows].sort((x,y)=>x.name.localeCompare(y.name));
for(const key of ['width','height','travelerPosition','travelerRotation','lookTarget','frozenTime','night','fillIntensity'])assert.deepEqual(b[key],a[key],key);
assert.deepEqual(sort(b.lights),sort(a.lights),'Scene lights differ');
assert.deepEqual(sort(b.materials),sort(a.materials),'Recorded face materials differ');
for(const record of [a,b]){assert.equal(record.allBodyPosesUnchanged,true);assert.deepEqual(record.views.map(v=>v.image),names);assert(record.views.every(v=>v.bodyPoseUnchanged));}
for(let i=0;i<names.length;i++)assert.deepEqual(b.views[i],a.views[i],'Camera/pose differs: '+names[i]);
const images=[];
for(const directory of [base,candidate])for(const name of names){
 const bytes=fs.readFileSync(path.join(root,directory,name));
 assert(bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
 assert(bytes.subarray(-12).equals(Buffer.from('0000000049454e44ae426082','hex')),'Incomplete PNG');
 assert.equal(bytes.readUInt32BE(16),1440);assert.equal(bytes.readUInt32BE(20),900);
 images.push({path:directory+'/'+name,width:1440,height:900,complete:true});
}
const report={passed:true,baseline:base,candidate,lightsMatch:true,recordedMaterialsMatch:true,camerasAndPosesMatch:true,images,scope:'Five fixed bind-pose views at original lighting; recorded material properties match. Does not establish normal gameplay, all animation poses, full material byte identity or aesthetic acceptance.'};
fs.writeFileSync(path.join(root,candidate,'capture-condition-comparison.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({passed:true,images:images.length,lightsMatch:true,recordedMaterialsMatch:true,camerasAndPosesMatch:true}));
