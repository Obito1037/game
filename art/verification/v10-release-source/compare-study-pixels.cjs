// Read-only PNG analysis using browser image decoding. No images are edited.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const dir=path.resolve(process.argv[2]);
const pairs=JSON.parse(process.argv[3]);
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage();const rows=[];
  for(const [a,b] of pairs){
   const urls=[a,b].map(name=>'data:image/png;base64,'+fs.readFileSync(path.join(dir,name)).toString('base64'));
   const result=await page.evaluate(async urls=>{
    const decoded=[];
    for(const url of urls){const image=new Image();image.src=url;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);decoded.push({w:image.width,h:image.height,p:ctx.getImageData(0,0,image.width,image.height).data});}
    const [a,b]=decoded;if(a.w!==b.w||a.h!==b.h)throw Error('Dimensions differ');
    let sum=0,max=0,changed=0;const regions=[{name:'upper half',y0:0,y1:a.h/2,sum:0,changed:0},{name:'lower half',y0:a.h/2,y1:a.h,sum:0,changed:0}];
    for(let y=0;y<a.h;y++)for(let x=0;x<a.w;x++){let value=0;const i=(y*a.w+x)*4;for(let c=0;c<3;c++){const d=Math.abs(a.p[i+c]-b.p[i+c]);sum+=d;value+=d;max=Math.max(max,d);}if(value)changed++;const r=regions[y<a.h/2?0:1];r.sum+=value;if(value)r.changed++;}
    return {width:a.w,height:a.h,meanAbsoluteRGBByteDifference:sum/(a.w*a.h*3),maximumChannelDifference:max,changedPixelFraction:changed/(a.w*a.h),regions:regions.map(r=>({name:r.name,meanAbsoluteRGBByteDifference:r.sum/(a.w*(r.y1-r.y0)*3),changedPixelFraction:r.changed/(a.w*(r.y1-r.y0))}))};
   },urls);rows.push({a,b,...result});
  }
  const report={scope:'Decoded original screenshots, RGB byte differences. A/A differences can include unscaled shader effects or temporal AO; numerical change is not visual quality.',rows};
  fs.writeFileSync(path.join(dir,'pixel-comparison.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
