const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.env.BORROWED_LIGHT_QA_DIR||'art/verification/web-001');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve(process.env.BORROWED_LIGHT_QA_PROFILE||'tools/game-browser-profile'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1});
 const browser=context.browser();browser.on('disconnected',()=>console.log('BROWSER_DISCONNECTED'));
 const page=await context.newPage(),errors=[],phases=[],messages=[],performanceViews=[],servedBuildResources=[];
 page.on('request',r=>{const url=r.url();if(url.includes('/Build/')&&!servedBuildResources.includes(url))servedBuildResources.push(url);});
 page.on('console',m=>{const t=m.text();messages.push(t);if(m.type()==='error')errors.push(t);const p=t.match(/BORROWED_LIGHT_PHASE:(\d+)/);if(p){phases.push(Number(p[1]));console.log('PHASE',p[1]);}});
 page.on('pageerror',e=>errors.push(e.message));
 page.on('crash',()=>{errors.push('The game page renderer crashed');console.log('PAGE_CRASHED');});
 const ready=async()=>{await page.bringToFront();await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.waitForTimeout(7000);console.log('CANVAS',JSON.stringify(await page.evaluate(()=>({width:document.querySelector('canvas').width,height:document.querySelector('canvas').height,dpr:devicePixelRatio}))));};
 const shot=async name=>page.screenshot({path:path.join(out,name),timeout:90000});
 const press=async key=>{await page.keyboard.press(key,{delay:90});await page.waitForTimeout(280);};
 const expectPhase=async p=>{await page.waitForTimeout(400);if(phases[phases.length-1]!==p)throw new Error('Expected phase '+p+', got '+JSON.stringify(phases));};
 const sampleMetrics=async view=>{
  await page.bringToFront();await page.evaluate(()=>document.getElementById('unity-canvas')?.focus());
  const samples=[],start=Date.now();
  for(let i=0;i<6;i++){
   await page.waitForTimeout(500);
   samples.push(await page.evaluate(()=>{const m=window.borrowedLight.GetMetricsInfo?.();return {timestampMs:performance.now(),visibility:document.visibilityState,focused:document.hasFocus(),fps:m?.fps??null,movingAverageFps:m?.movingAverageFps??null};}));
  }
  const ordered=samples.map(s=>s.movingAverageFps).filter(Number.isFinite).sort((a,b)=>a-b),mid=Math.floor(ordered.length/2);
  const medianMovingAverageFps=ordered.length?(ordered.length%2?ordered[mid]:(ordered[mid-1]+ordered[mid])/2):null;
  const intervalOrdered=samples.map(s=>s.fps).filter(Number.isFinite).sort((a,b)=>a-b),intervalMid=Math.floor(intervalOrdered.length/2);
  const medianIntervalFps=intervalOrdered.length?(intervalOrdered.length%2?intervalOrdered[intervalMid]:(intervalOrdered[intervalMid-1]+intervalOrdered[intervalMid])/2):null;
  const result={view,requestedDurationMs:3000,elapsedMs:Date.now()-start,intervalMs:500,samples,medianIntervalFps,medianMovingAverageFps,allSamplesForeground:samples.every(s=>s.visibility==='visible'&&s.focused),measurement:'Unity GetMetricsInfo: medianIntervalFps summarizes the six samples[].fps interval readings; medianMovingAverageFps summarizes the separate rolling-history readings, which may include preceding camera views. Neither is an independent rendered-frame counter. No draw interception or graphics modification is used.'};
  performanceViews.push(result);console.log('VIEW_METRICS',JSON.stringify(result));return result;
 };
 try{
  await page.goto(process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8765/',{waitUntil:'domcontentloaded',timeout:30000});
  await shot('00-loading.png');await ready();await sampleMetrics('menu');await shot('01-invitation.png');
  const isolation=await page.evaluate(()=>crossOriginIsolated);
  await page.mouse.click(195,566);await page.waitForTimeout(2000);await expectPhase(1);
  await press('1');await press('d');await press('Enter');await expectPhase(2);await page.waitForTimeout(2000);await shot('02-window.png');
  await page.reload({waitUntil:'domcontentloaded'});await ready();await page.mouse.click(215,624);await page.waitForTimeout(1500);await expectPhase(2);await shot('03-resumed.png');
  await press('2');await press('d');await press('Enter');await expectPhase(3);
  for(const k of ['3','d','2','d','Space','1','Space'])await press(k);
  await page.waitForTimeout(2500);await shot('04-harbor-solved.png');await press('Enter');await expectPhase(4);
  await page.waitForTimeout(6500);await sampleMetrics('ending');await shot('05-stars-return.png');
  await page.mouse.click(210,634);await page.waitForTimeout(2500);await page.keyboard.down('w');await page.waitForTimeout(1100);await page.keyboard.up('w');
  // The return-to-island toast lasts five seconds; settle beyond that before capture.
  await page.waitForTimeout(2200);await sampleMetrics('walking');await shot('06-walking.png');
  await press('Tab');await page.waitForTimeout(3000);await shot('07-returned-to-ending.png');
  const graphics=await page.evaluate(()=>{const c=document.getElementById('unity-canvas'),gl=c.getContext('webgl2');if(!gl)return null;const e=gl.getExtension('WEBGL_debug_renderer_info');return {renderer:e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),metrics:window.borrowedLight.GetMetricsInfo?.()};});
  if(errors.length)throw new Error('Browser reported '+errors.length+' errors: '+errors[0]);
  const engineDiagnostics=[...new Set(messages.filter(t=>/ERROR: Shader|shader is not supported|INVALID_ENUM|Trying to get length of sound|deprecated/.test(t)))];
  fs.writeFileSync(path.join(out,'runtime-results.json'),JSON.stringify({passed:true,title:await page.title(),phases,persistedProgressReload:true,realKeyboardPuzzleCompletion:true,crossOriginIsolated:isolation,graphics,performanceViews,errors,errorScope:'Browser console.error, page exceptions and renderer crashes; Unity log diagnostics are reported separately.',engineDiagnostics,defaultBrowserAutoplayPolicy:true,audioContextResumeObserved:messages.some(t=>t.includes('Audio context resumed')),width:1440,height:900},null,2));
  console.log('WEB_QA_PASSED',JSON.stringify({phases,errors:errors.length,isolation}));
 }catch(e){await shot('failure.png').catch(()=>{});fs.writeFileSync(path.join(out,'runtime-results.json'),JSON.stringify({passed:false,error:e.message,phases,performanceViews,errors},null,2));throw e;}
 finally{fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));fs.writeFileSync(path.join(out,'build-evidence.json'),JSON.stringify({declaredBuildId:process.env.BORROWED_LIGHT_BUILD_ID||null,servedBuildResources},null,2));await context.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
