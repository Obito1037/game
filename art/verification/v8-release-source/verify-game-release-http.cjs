// Node http preserves compressed response bytes; fetch/Invoke-WebRequest can decode them.
'use strict';
const http=require('node:http'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..'),origin='http://127.0.0.1:8765/';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
const get=url=>new Promise((resolve,reject)=>{
 const req=http.get(url,response=>{const parts=[];response.on('data',b=>parts.push(b));response.on('end',()=>{
  if(response.statusCode!==200)return reject(new Error('HTTP '+response.statusCode+' '+url));
  resolve({bytes:Buffer.concat(parts),encoding:response.headers['content-encoding']||null});
 });response.on('error',reject);});req.on('error',reject);req.setTimeout(30000,()=>req.destroy(new Error('HTTP timeout')));
});
(async()=>{
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'art/production-manifest.json'),'utf8').replace(/^\uFEFF/,''));
 const health=JSON.parse((await get(origin+'__borrowed_light_health')).bytes);
 const index=(await get(origin)).bytes.toString('utf8'),files=[];
 const priorPath=path.join(root,'art/verification/v8-release-http-powershell-attempt.json');
 const prior=fs.existsSync(priorPath)?JSON.parse(fs.readFileSync(priorPath,'utf8').replace(/^\uFEFF/,'')):null;
 for(const file of manifest.webPayload.files){
  const response=await get(origin+'Build/'+file.name),disk=fs.readFileSync(path.join(root,'builds/web/Build',file.name));
  const httpSHA256=hash(response.bytes),diskSHA256=hash(disk),old=prior?.files.find(f=>f.name===file.name);
  const decodedHash=response.encoding==='gzip'&&old?hash(zlib.gunzipSync(response.bytes)):null;
  files.push({name:file.name,bytes:response.bytes.length,contentEncoding:response.encoding,httpSHA256,diskSHA256,
   manifestSHA256:file.sha256,matches:httpSHA256===diskSHA256&&diskSHA256===file.sha256&&response.bytes.length===file.bytes,
   previousPowerShellHashMatchesDecodedBytes:decodedHash?decodedHash===old.httpSHA256:null});
 }
 const indexReferencesCurrentFiles=manifest.webPayload.files.every(f=>index.includes(f.name));
 const proof={passed:files.every(f=>f.matches)&&indexReferencesCurrentFiles&&path.resolve(health.root)===path.join(root,'builds/web'),
  revision:manifest.revision,server:origin,root:health.root,indexReferencesCurrentFiles,
  method:'Node http raw response buffers; gzip Content-Encoding is not decoded before SHA-256 comparison.',
  previousAttemptLimit:'The earlier PowerShell response stream was transparently decompressed. Its hashes are checked against decoded bytes below; that attempt was not evidence of a corrupt release.',files};
 fs.writeFileSync(path.join(root,'art/verification/v8-release-http-verification.json'),JSON.stringify(proof,null,2));
 console.log(JSON.stringify(proof,null,2));if(!proof.passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
