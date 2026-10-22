// Separate visual evidence session. Playwright video capture is never a FPS benchmark.
const fs=require('node:fs'),path=require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH=path.resolve('tools/playwright-media');
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const out=path.resolve(process.env.BORROWED_LIGHT_GAIT_DIR||'art/verification/web-v6-gait');fs.mkdirSync(out,{recursive:true});
const videoOnly=process.env.BORROWED_LIGHT_GAIT_VIDEO_ONLY==='1';
const observatoryOnly=process.env.BORROWED_LIGHT_GAIT_ROUTE==='observatory';
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve(process.env.BORROWED_LIGHT_GAIT_PROFILE||'tools/game-browser-profile-v6-gait'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1,recordVideo:{dir:path.join(out,'raw-video'),size:{width:1440,height:900}}});
 const page=context.pages()[0]||await context.newPage(),video=page.video(),messages=[],errors=[],phases=[],events=[],servedBuildResources=[];
 page.on('request',r=>{const url=r.url();if(url.includes('/Build/')&&!servedBuildResources.includes(url))servedBuildResources.push(url);});
 let navigationStartedAt=Date.now(),actionStart=null,actionEnd=null,completed=false, failure=null,canvasMetrics=null;
 const stamp=(type,data={})=>events.push({type,sinceNavigationMs:Date.now()-navigationStartedAt,...data});
 page.on('console',m=>{messages.push(m.text());if(m.type()==='error')errors.push(m.text());const p=m.text().match(/BORROWED_LIGHT_PHASE:(\d+)/);if(p)phases.push(+p[1]);});
 page.on('pageerror',e=>errors.push(e.message));page.on('crash',()=>errors.push('Game renderer crashed'));
 const press=async key=>{await page.keyboard.press(key,{delay:90});await page.waitForTimeout(280);};
 const shot=async name=>{if(videoOnly){stamp('screenshot-skipped',{file:name,reason:'Keep recordVideo continuous; simultaneous page.screenshot produced transient scaled/cropped video frames on this machine.'});return;}const before=Date.now();await page.screenshot({path:path.join(out,name),timeout:90000});stamp('screenshot',{file:name,captureRequestedSinceNavigationMs:before-navigationStartedAt});};
 const move=async(keys,durationMs,captures)=>{
  for(const key of keys)await page.keyboard.down(key);const start=Date.now();stamp('movement-start',{keys,durationRequestedMs:durationMs});
  try{for(const capture of captures){await page.waitForTimeout(Math.max(0,capture.atMs-(Date.now()-start)));await shot(capture.file);}await page.waitForTimeout(Math.max(0,durationMs-(Date.now()-start)));}
  finally{for(const key of keys)await page.keyboard.up(key);stamp('movement-stop',{keys,actualHeldMs:Date.now()-start});}
 };
 const orbit=async deltaX=>{await page.mouse.move(700,440);await page.mouse.down({button:'right'});await page.mouse.move(700+deltaX,430,{steps:16});await page.mouse.up({button:'right'});stamp('right-mouse-orbit',{deltaX,nominalYawDeltaDegrees:deltaX*.13});};
 try{
  navigationStartedAt=Date.now();await page.goto(process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.bringToFront();await page.waitForTimeout(6500);
  canvasMetrics=await page.evaluate(()=>({width:document.getElementById('unity-canvas').width,height:document.getElementById('unity-canvas').height,devicePixelRatio,viewportWidth:innerWidth,viewportHeight:innerHeight}));
  await page.mouse.click(195,566);await page.waitForTimeout(2000);for(const key of ['1','d','Enter','2','d','Enter','3','d','2','d','Space','1','Space','Enter'])await press(key);
  if(phases.at(-1)!==4)throw new Error('Did not complete the puzzle: '+JSON.stringify(phases));
  await page.waitForTimeout(6500);await page.mouse.click(210,634);await page.waitForTimeout(observatoryOnly?6500:5800);
  await page.bringToFront();await page.evaluate(()=>document.getElementById('unity-canvas')?.focus());if(!observatoryOnly)await orbit(390);await page.waitForTimeout(850);await shot('00-side-rear-ready.png');
  actionStart=Date.now();stamp('gait-window-start');
  if(observatoryOnly){
   // Keep the default view for a repeatable straight approach. Dragging the
   // camera first can change this real-input route between recorded sessions.
   await move(['w'],4200,[]);await page.waitForTimeout(1500);
  }else{
  // In video-only mode, use the actual held durations observed in the prior
  // screenshot session. No screenshots interrupt or extend these intervals.
  await move(['w'],videoOnly?3100:1600,[{atMs:400,file:'01-walk-forward-a.png'},{atMs:1100,file:'02-walk-forward-b.png'}]);
  await page.waitForTimeout(1000);await shot('03-first-stop.png');
  // Camera-relative W follows the rear view. W+D exposes the knees/ankles at a
  // three-quarter angle while retaining real player input and the normal motor.
  await move(['w','d'],videoOnly?2500:2000,[{atMs:500,file:'04-diagonal-step-a.png'},{atMs:1400,file:'05-diagonal-step-b.png'}]);
  await page.waitForTimeout(1200);await shot('06-diagonal-stop.png');
  await move(['d'],videoOnly?3500:1600,[{atMs:400,file:'07-side-step-a.png'},{atMs:1150,file:'08-side-step-b.png'}]);
  await page.waitForTimeout(1400);await orbit(-150);await page.waitForTimeout(1800);await shot('09-final-planted-feet.png');
  }
  actionEnd=Date.now();stamp('gait-window-end',{durationMs:actionEnd-actionStart});
  if(errors.length)throw new Error('Browser error during capture: '+errors[0]);completed=true;
 }catch(e){failure=e.message;await page.keyboard.up('w').catch(()=>{});await page.keyboard.up('d').catch(()=>{});await page.mouse.up({button:'right'}).catch(()=>{});await shot('capture-failure.png').catch(()=>{});}
 finally{
  await context.close();let videoFile=null;
  if(video){const source=await video.path();videoFile='gait-session-includes-loading.webm';fs.copyFileSync(source,path.join(out,videoFile));}
  fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));
  fs.writeFileSync(path.join(out,'build-evidence.json'),JSON.stringify({declaredBuildId:process.env.BORROWED_LIGHT_BUILD_ID||null,servedBuildResources},null,2));
  fs.writeFileSync(path.join(out,'capture-manifest.json'),JSON.stringify({completed,error:failure,requestedRevision:process.env.BORROWED_LIGHT_REVISION||'v6',videoOnly,route:observatoryOnly?'observatory-straight-approach':'diagonal-and-side',canvasMetrics,purpose:'Actual browser gameplay animation review; separate from normal QA and GPU profiling.',recordedVideo:videoFile,videoScope:'Full Playwright session, including loading, puzzle completion, return to island, camera adjustment, and the gait review window. This is not a trimmed 10–15 second clip.',frameRateLimit:'Playwright recordVideo samples/resamples browser output. Video playback FPS and screenshot cadence are not native engine FPS and must not be reported as performance evidence.',inputMethod:observatoryOnly?'Actual keyboard only: after at least 6,500 ms camera settling, keep the default view, W for 4,200 ms, then release and stop for 1,500 ms. No camera drag, screenshots or transform injection.':'Actual mouse and keyboard only: right-mouse orbit, W, W+D, D, and released-key stops. Diagonal/side input reveals knee and ankle motion that camera-relative W alone hides.',width:1440,height:900,gaitWindow:actionStart&&actionEnd?{startSinceNavigationMs:actionStart-navigationStartedAt,endSinceNavigationMs:actionEnd-navigationStartedAt,durationMs:actionEnd-actionStart}:null,timingLimit:'Event times are relative to navigation; recording begins slightly before navigation. They are approximate video navigation aids, not exact frame timestamps.',phases,errors,events},null,2));
  console.log('GAIT_CAPTURE',JSON.stringify({completed,video:videoFile,durationMs:actionStart&&actionEnd?actionEnd-actionStart:null,error:failure}));
 }
 if(failure)throw new Error(failure);
})().catch(e=>{console.error(e);process.exitCode=1;});
