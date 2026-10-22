'use strict';
// Verify every encoded VP8 packet of a stream-copy excerpt against its source.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
function packets(filename){
 const b=fs.readFileSync(filename),out=[];let scale=1000000,durationTicks=null;
 const vint=(at,identifier=false)=>{let n=1,mask=128;while(n<=8&&!(b[at]&mask)){mask>>=1;n++;}if(n>8)throw new Error('Invalid EBML VINT');let value=identifier?b[at]:b[at]&(mask-1);for(let i=1;i<n;i++)value=value*256+b[at+i];return {n,value};};
 const uint=(at,end)=>{let n=0;for(;at<end;at++)n=n*256+b[at];return n;};
 function walk(start,end,clusterTime=0){
  for(let p=start;p<end;){const id=vint(p,true);p+=id.n;const size=vint(p);p+=size.n;const stop=Math.min(end,p+size.value);
   if(id.value===0x18538067||id.value===0x1549a966||id.value===0x1f43b675)walk(p,stop,id.value===0x1f43b675?0:clusterTime);
   else if(id.value===0x2ad7b1)scale=uint(p,stop);
   else if(id.value===0x4489)durationTicks=stop-p===8?b.readDoubleBE(p):stop-p===4?b.readFloatBE(p):null;
   else if(id.value===0xe7)clusterTime=uint(p,stop);
   else if(id.value===0xa3){const track=vint(p),t=b.readInt16BE(p+track.n),flags=b[p+track.n+2];if(flags&6)throw new Error('Laced block unsupported');const payload=b.subarray(p+track.n+3,stop);out.push({timeMs:(clusterTime+t)*scale/1000000,keyframe:!!(flags&128),bytes:payload.length,sha256:crypto.createHash('sha256').update(payload).digest('hex')});}
   p=stop;
  }
 }
 walk(0,b.length);return {packets:out,durationSeconds:durationTicks==null?null:durationTicks*scale/1e9};
}
const fullData=packets(path.join(__dirname,'portrait-session-includes-loading.webm')),cutData=packets(path.join(__dirname,'portrait-time-cut.webm'));
const full=fullData.packets,cut=cutData.packets,start=full.findIndex(p=>p.sha256===cut[0]?.sha256);
const equal=start>=0&&cut.length>0&&cut.every((p,i)=>p.sha256===full[start+i]?.sha256&&p.bytes===full[start+i]?.bytes);
const finalIndex=start+cut.length-1,finalCadence=full[finalIndex+1]?full[finalIndex+1].timeMs-full[finalIndex].timeMs:full[finalIndex]?.timeMs-full[finalIndex-1]?.timeMs;
const result={passed:equal,method:'Parse EBML SimpleBlock payloads and compare the SHA-256 of every encoded VP8 packet in order. No decoding or re-encoding.',fullPackets:full.length,excerptPackets:cut.length,sourceFirstPacketMs:full[start]?.timeMs,sourceLastPacketMs:full[finalIndex]?.timeMs,sourceEndExclusiveMs:full[finalIndex]?.timeMs+finalCadence,excerptFirstPacketMs:cut[0]?.timeMs,excerptLastPacketMs:cut.at(-1)?.timeMs,allEncodedPacketsByteIdentical:equal,startsAtKeyframe:cut[0]?.keyframe,fullContainerDurationSeconds:fullData.durationSeconds,excerptContainerDurationSeconds:cutData.durationSeconds,requestedTrimStartSeconds:Number(process.argv[2]),requestedTrimDurationSeconds:Number(process.argv[3]),trimLimit:'FFmpeg input seeking with stream copy starts at a prior keyframe. The actual verified source range is reported. The recording cadence is not game engine FPS.'};
fs.writeFileSync(path.join(__dirname,'time-cut-verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));if(!equal)process.exitCode=1;
