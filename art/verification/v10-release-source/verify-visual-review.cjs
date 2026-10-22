const fs=require('node:fs'),path=require('node:path'),{pathToFileURL,fileURLToPath}=require('node:url');
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const revision=process.argv[2]||'v10',root=path.resolve(__dirname,'..'),dir=path.join(root,'art/verification');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(pathToFileURL(path.join(dir,'visual-review.html')).href,{waitUntil:'load'});
  const media=await page.evaluate(async()=>{
   // The dialog image intentionally has no source until the user opens a figure.
   const imgs=[...document.querySelectorAll('img[src]')].filter(img=>img.getAttribute('src'));for(const img of imgs)img.loading='eager';
   await Promise.all(imgs.map(img=>img.decode()));
   const videos=[...document.querySelectorAll('video')];await Promise.all(videos.map(video=>video.readyState>=1?Promise.resolve():new Promise((resolve,reject)=>{video.addEventListener('loadedmetadata',resolve,{once:true});video.addEventListener('error',()=>reject(Error('Video load failed')),{once:true});setTimeout(()=>reject(Error('Video metadata timeout')),15000);})));
   return {title:document.title,images:imgs.map(img=>({src:img.getAttribute('src'),complete:img.complete,width:img.naturalWidth,height:img.naturalHeight})),videos:videos.map(video=>({src:video.getAttribute('src'),width:video.videoWidth,height:video.videoHeight,duration:video.duration})),links:[...document.querySelectorAll('a[href]')].map(a=>a.href).filter(href=>href.startsWith('file:')),overflow:document.documentElement.scrollWidth>innerWidth};
  });
  const links=[...new Set(media.links)],missing=links.filter(link=>!fs.existsSync(fileURLToPath(link)));
  await page.locator('a.picture').first().click();const dialogOpened=await page.locator('dialog').evaluate(d=>d.open);await page.keyboard.press('Escape');
  await page.screenshot({path:path.join(dir,revision+'-review-page-top.png')});
  await page.locator('section').nth(2).screenshot({path:path.join(dir,revision+'-review-page-character.png')});
  const report={passed:missing.length===0&&errors.length===0&&!media.overflow&&dialogOpened,page:'visual-review.html',localLinksChecked:links.length,missingLocalLinks:missing,imagesChecked:media.images.length,videosChecked:media.videos.length,dialogOpened,errors,...media};
  fs.writeFileSync(path.join(dir,revision+'-review-page-verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,images:media.images.length,videos:media.videos.length,localLinks:links.length,overflow:media.overflow,errors}));if(!report.passed)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
