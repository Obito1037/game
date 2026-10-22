'use strict';
// Compare raw HTTP payloads (including gzip bytes) with the candidate on disk.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const expectedRoot=path.resolve(process.argv[2]||'builds/candidates/v8/web');
const sessions=process.argv.slice(3);
if(!sessions.length)throw new Error('Pass the actual candidate directory followed by evidence session directories.');
const digest=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const get=url=>new Promise((resolve,reject)=>{http.get(url,res=>{const chunks=[];res.on('data',b=>chunks.push(b));res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:Buffer.concat(chunks)}));res.on('error',reject);}).on('error',reject);});
(async()=>{
 const base=process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8778/';
 const healthResponse=await get(new URL('/__borrowed_light_health',base));
 const health=JSON.parse(healthResponse.body.toString('utf8'));
 if(healthResponse.status!==200||path.resolve(health.root)!==expectedRoot)throw new Error('Unexpected candidate server root: '+JSON.stringify(health));
 const buildDir=path.join(expectedRoot,'Build');
 const diskResources=fs.readdirSync(buildDir).filter(n=>/\.(?:js|gz)$/.test(n)).sort().map(name=>{const b=fs.readFileSync(path.join(buildDir,name));return {name,bytes:b.length,sha256:digest(b)};});
 const sessionResults=[];
 for(const session of sessions){
  const evidence=JSON.parse(fs.readFileSync(path.join(session,'build-evidence.json'),'utf8'));
  const resources=[];
  for(const url of evidence.servedBuildResources){
   const parsed=new URL(url);if(parsed.origin!==new URL(base).origin)throw new Error('Session requested a different origin: '+url);
   const name=decodeURIComponent(path.posix.basename(parsed.pathname)),disk=diskResources.find(r=>r.name===name);
   if(!disk)throw new Error('Session requested a missing disk resource: '+name);
   const response=await get(url),sha256=digest(response.body);
   resources.push({url,name,status:response.status,bytes:response.body.length,sha256,contentEncoding:response.headers['content-encoding']||null,matchesDisk:response.status===200&&response.body.length===disk.bytes&&sha256===disk.sha256});
  }
  const requestedNames=resources.map(r=>r.name).sort();
  sessionResults.push({session:path.relative(process.cwd(),path.resolve(session)).replaceAll('\\','/'),declaredBuildId:evidence.declaredBuildId,requestedNames,namesMatchDisk:JSON.stringify(requestedNames)===JSON.stringify(diskResources.map(r=>r.name)),resources,allRawResponsesMatchDisk:resources.every(r=>r.matchesDisk)});
 }
 const report={passed:sessionResults.every(s=>s.namesMatchDisk&&s.allRawResponsesMatchDisk),scope:'Each session captured its actual Build request URLs. After the sessions, raw HTTP response bytes from those URLs are SHA-256 compared with the candidate disk files. This independently verifies current served resource identity; the historical session body bytes were not separately intercepted. The declared build ID alone is not identity proof.',server:base,serverRoot:health.root,checkedAt:new Date().toISOString(),totalPayloadBytes:diskResources.reduce((n,r)=>n+r.bytes,0),diskResources,sessions:sessionResults};
 fs.writeFileSync(path.join(__dirname,'artifact-identity.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({passed:report.passed,totalPayloadBytes:report.totalPayloadBytes,resources:diskResources,sessions:sessionResults.map(s=>({session:s.session,namesMatchDisk:s.namesMatchDisk,allRawResponsesMatchDisk:s.allRawResponsesMatchDisk}))}));
 if(!report.passed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
