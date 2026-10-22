const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const [revision,...sessions]=process.argv.slice(2);
assert(/^v\d+$/.test(revision||'')&&sessions.length&&sessions.every(x=>/^[a-z0-9-]+$/.test(x)),'Supply revision and QA session directory names');
const root=path.resolve(__dirname,'..'),origin=process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8780/';
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8').replace(/^\uFEFF/,''));
const report=read('art/verification/'+revision+'-build-reports.json');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const get=url=>new Promise((resolve,reject)=>{const request=http.get(url,response=>{const chunks=[];response.on('data',x=>chunks.push(x));response.on('end',()=>response.statusCode===200?resolve(Buffer.concat(chunks)):reject(Error('HTTP '+response.statusCode)));response.on('error',reject);});request.on('error',reject);request.setTimeout(30000,()=>request.destroy(Error('HTTP timeout')));});
(async()=>{
 const fileChecks=await Promise.all(report.web.payload.files.map(async f=>{
  const bytes=await get(new URL('Build/'+f.name,origin)),disk=fs.readFileSync(path.join(root,'builds/candidates',revision,'web/Build',f.name));
  const httpSHA256=hash(bytes),diskSHA256=hash(disk);
  return {name:f.name,bytes:bytes.length,httpSHA256,diskSHA256,buildReportSHA256:f.sha256,matches:httpSHA256===diskSHA256&&diskSHA256===f.sha256&&bytes.length===f.bytes};
 }));
 for(const name of sessions){
  const session=read('art/verification/'+name+'/build-evidence.json'),urls=session.servedBuildResources||[];
  const requestedAllCurrentFiles=report.web.payload.files.every(f=>urls.some(url=>new URL(url).pathname==='/Build/'+f.name));
  const declaredBuildMatches=session.declaredBuildId===report.web.buildId;
  const proof={passed:fileChecks.every(f=>f.matches)&&requestedAllCurrentFiles&&declaredBuildMatches,buildId:report.web.buildId,declaredBuildMatches,session:name,
   scope:'Session request URLs plus subsequent raw HTTP/disk SHA-256 checks against the candidate payload recorded after build. Historical response bodies were not intercepted.',requestedAllCurrentFiles,servedBuildResources:urls,files:fileChecks};
  fs.writeFileSync(path.join(root,'art/verification',name,'artifact-identity.json'),JSON.stringify(proof,null,2)+'\n');
  console.log(JSON.stringify({session:name,passed:proof.passed,files:fileChecks.length}));if(!proof.passed)process.exitCode=1;
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
