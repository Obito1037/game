const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const report=read('art/verification/v10-build-reports.json');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const get=url=>new Promise((resolve,reject)=>{const request=http.get(url,response=>{const chunks=[];response.on('data',x=>chunks.push(x));response.on('end',()=>response.statusCode===200?resolve(Buffer.concat(chunks)):reject(Error('HTTP '+response.statusCode)));response.on('error',reject);});request.on('error',reject);request.setTimeout(30000,()=>request.destroy(Error('HTTP timeout')));});
(async()=>{
 const fileChecks=await Promise.all(report.web.payload.files.map(async f=>{
  const bytes=await get('http://127.0.0.1:8780/Build/'+f.name),disk=fs.readFileSync(path.join(root,'builds/candidates/v10/web/Build',f.name));
  return {name:f.name,bytes:bytes.length,httpSHA256:hash(bytes),diskSHA256:hash(disk),buildReportSHA256:f.sha256,matches:hash(bytes)===hash(disk)&&hash(disk)===f.sha256&&bytes.length===f.bytes};
 }));
 for(const name of ['web-011-v10','web-v10-gait-video']){
  const session=read('art/verification/'+name+'/build-evidence.json');
  const urls=session.servedBuildResources||[];
  const requestedAllCurrentFiles=report.web.payload.files.every(f=>urls.some(url=>new URL(url).pathname==='/Build/'+f.name));
  const declaredBuildMatches=session.declaredBuildId===report.web.buildId;
  const proof={passed:fileChecks.every(f=>f.matches)&&requestedAllCurrentFiles&&declaredBuildMatches,buildId:report.web.buildId,declaredBuildMatches,session:name,
   scope:'Session request URLs plus subsequent raw HTTP/disk SHA-256 checks against the unchanged candidate payload recorded after build. Historical response bodies were not intercepted; this does not claim per-response body hashing during gameplay.',requestedAllCurrentFiles,servedBuildResources:urls,files:fileChecks};
  fs.writeFileSync(path.join(root,'art/verification',name,'artifact-identity.json'),JSON.stringify(proof,null,2)+'\n');
  console.log(JSON.stringify({session:name,passed:proof.passed,files:fileChecks.length}));if(!proof.passed)process.exitCode=1;
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
