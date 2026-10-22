// Pixel-based candidate locator only. Acceptance requires original full frames.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
function png(file){
 const b=fs.readFileSync(file),chunks=[];let width,height,channels;
 for(let at=8;at<b.length;){const size=b.readUInt32BE(at),type=b.toString('ascii',at+4,at+8),data=b.subarray(at+8,at+8+size);if(type==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);if(data[8]!==8||![2,6].includes(data[9]))throw Error('Unsupported PNG');channels=data[9]===2?3:4;}if(type==='IDAT')chunks.push(data);at+=size+12;}
 const packed=zlib.inflateSync(Buffer.concat(chunks)),stride=width*channels,out=Buffer.alloc(width*height*channels);
 for(let y=0;y<height;y++){const filter=packed[y*(stride+1)],at=y*(stride+1)+1;for(let x=0;x<stride;x++){const a=x>=channels?out[y*stride+x-channels]:0,c=y&&x>=channels?out[(y-1)*stride+x-channels]:0,up=y?out[(y-1)*stride+x]:0;let add=0;if(filter===1)add=a;else if(filter===2)add=up;else if(filter===3)add=Math.floor((a+up)/2);else if(filter===4){const p=a+up-c,pa=Math.abs(p-a),pb=Math.abs(p-up),pc=Math.abs(p-c);add=pa<=pb&&pa<=pc?a:pb<=pc?up:c;}else if(filter!==0)throw Error('Bad filter');out[y*stride+x]=(packed[at+x]+add)&255;}}
 return {width,height,channels,out};
}
const dir=path.join(__dirname,'blink-location'),files=fs.readdirSync(dir).filter(f=>/^face-\d+\.png$/.test(f)).sort();
const samples=files.map((file,index)=>{const p=png(path.join(dir,file));let dark=0;for(const [x0,x1]of[[106,125],[146,166]])for(let y=98;y<116;y++)for(let x=x0;x<x1;x++){const at=(y*p.width+x)*p.channels;const value=p.out[at]*.2126+p.out[at+1]*.7152+p.out[at+2]*.0722;if(value<110)dark++;}return {file,index:index+1,requestedSourceSeconds:43+index/25,darkEyeRegionPixels:dark};});
const minima=samples.filter((s,i)=>s.darkEyeRegionPixels<25&&(!i||s.darkEyeRegionPixels<=samples[i-1].darkEyeRegionPixels)&&(i===samples.length-1||s.darkEyeRegionPixels<=samples[i+1].darkEyeRegionPixels));
const result={purpose:'Locate possible closed-eye frames; pixel threshold is not an animation pass/fail test.',crop:[600,140,240,200],sourceCaptureRate:25,sourceRateLimit:'Browser video container cadence, not engine FPS.',allSamples:samples,localMinima:minima};
fs.writeFileSync(path.join(dir,'score-candidates.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({minima,smallest:[...samples].sort((a,b)=>a.darkEyeRegionPixels-b.darkEyeRegionPixels).slice(0,12)},null,2));
