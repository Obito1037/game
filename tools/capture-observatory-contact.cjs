// Targeted real-input visual check; isolated from FPS and GPU measurements.
const fs=require('node:fs'),path=require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.resolve('tools/playwright-media');
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const out=path.resolve('art/verification/web-v6-gait-fixed/observatory-contact');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve('tools/game-browser-profile-v6-gait-fixed'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1,recordVideo:{dir:path.join(out,'raw-video'),size:{width:1440,height:900}}});
 const page=context.pages()[0]||await context.newPage(),video=page.video(),events=[],messages=[],errors=[],resources=[];
 const started=Date.now();let completed=false,error=null;
 const stamp=(type,data={})=>events.push({type,sinceStartMs:Date.now()-started,...data});
 page.on('console',m=>{messages.push(m.text());if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const u=r.url();if(u.includes('/Build/')&&!resources.includes(u))resources.push(u);});
 const shot=async file=>{const requested=Date.now()-started;await page.screenshot({path:path.join(out,file),timeout:90000});stamp('screenshot',{file,captureRequestedMs:requested});};
 try{
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.bringToFront();await page.waitForTimeout(6500);
  // The completed gait session persisted the epilogue. Continue it, then return.
  await page.mouse.click(215,624);await page.waitForTimeout(3500);
  if(!messages.some(t=>t.includes('BORROWED_LIGHT_PHASE:4')))throw new Error('Completed save did not resume at epilogue');
  await page.mouse.click(210,634);await page.waitForTimeout(5800);await page.evaluate(()=>document.getElementById('unity-canvas')?.focus());await shot('00-default-approach.png');
  await page.keyboard.down('w');stamp('w-down');await page.waitForTimeout(3600);await page.keyboard.up('w');stamp('w-up');await page.waitForTimeout(1000);await shot('01-contact-before.png');
  await page.keyboard.down('w');stamp('continued-w-down');await page.waitForTimeout(1600);await page.keyboard.up('w');stamp('continued-w-up');await page.waitForTimeout(1000);await shot('02-contact-after.png');
  await page.mouse.move(700,440);await page.mouse.down({button:'right'});await page.mouse.move(1040,440,{steps:16});await page.mouse.up({button:'right'});stamp('right-mouse-orbit',{deltaX:340});await page.waitForTimeout(1600);await shot('03-contact-side.png');
  if(errors.length)throw new Error(errors[0]);completed=true;
 }catch(e){error=e.message;await page.keyboard.up('w').catch(()=>{});await shot('failure.png').catch(()=>{});}
 finally{
  await context.close();if(video)fs.copyFileSync(await video.path(),path.join(out,'observatory-contact-full-session.webm'));
  fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));
  fs.writeFileSync(path.join(out,'capture-manifest.json'),JSON.stringify({completed,error,declaredBuildId:'build_d4eac3ac8c31',servedBuildResources:resources,input:'Real keyboard W from spawn with default camera; stop, press W again, and right-mouse side view. No programmatic movement or game-state injection.',measurement:'Visual collision check only. Full recording includes loading/resume and uses Playwright sampled video, not engine FPS.',events,errors},null,2));
 }
 console.log('OBSERVATORY_CAPTURE',JSON.stringify({completed,error}));if(error)throw new Error(error);
})().catch(e=>{console.error(e);process.exitCode=1;});
