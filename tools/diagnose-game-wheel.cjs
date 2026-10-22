// Short real-input wheel diagnostic; no video and no Unity state mutations.
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const out=path.resolve('art/verification/web-v9-portrait-wheel-diagnostic');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve('tools/game-browser-profile-v9-portrait-near'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1});
 const page=context.pages()[0]||await context.newPage(),messages=[],errors=[],phases=[],events=[],snapshots=[];
 const start=Date.now();let failure=null;
 const stamp=(type,data={})=>events.push({type,elapsedMs:Date.now()-start,...data});
 page.on('console',m=>{messages.push(m.text());if(m.type()==='error')errors.push(m.text());const match=m.text().match(/BORROWED_LIGHT_PHASE:(\d+)/);if(match)phases.push(+match[1]);});
 page.on('pageerror',e=>errors.push(e.message));
 const state=()=>page.evaluate(()=>{const c=document.getElementById('unity-canvas'),r=c.getBoundingClientRect();return {canvas:[c.width,c.height],bounds:{x:r.x,y:r.y,width:r.width,height:r.height},visible:document.visibilityState,focused:document.hasFocus(),active:document.activeElement?.id,events:window.__portraitWheelObservation||[]};});
 const shot=async name=>{await page.waitForTimeout(1700);const data=await state();await page.screenshot({path:path.join(out,name)});snapshots.push({file:name,elapsedMs:Date.now()-start,state:data});console.log('WHEEL_DIAGNOSTIC_SHOT',name,JSON.stringify({eventCount:data.events.length,lastEvent:data.events.at(-1)}));};
 const wheel=async(label,deltaY,count,interval)=>{stamp('wheel-test-start',{label,deltaY,count,intervalMs:interval});for(let i=0;i<count;i++){await page.mouse.wheel(0,deltaY);await page.waitForTimeout(interval);}stamp('wheel-test-end',{label});await shot(label+'.png');};
 try{
  await page.goto(process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8779/',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.bringToFront();await page.waitForTimeout(6500);
  // New journey + Tab gives the same normal exploring wheel branch without
  // repeating the three puzzles. This diagnostic is not completion evidence.
  await page.mouse.click(195,566);await page.waitForTimeout(2000);await page.keyboard.press('Tab',{delay:90});await page.waitForTimeout(3000);
  await page.evaluate(()=>{const c=document.getElementById('unity-canvas');c.focus();window.__portraitWheelObservation=[];document.addEventListener('wheel',e=>window.__portraitWheelObservation.push({deltaX:e.deltaX,deltaY:e.deltaY,deltaMode:e.deltaMode,clientX:e.clientX,clientY:e.clientY,target:e.target?.id,isTrusted:e.isTrusted,defaultPrevented:e.defaultPrevented,observedAtMs:performance.now()}),{capture:true,passive:true});});
  for(let i=0;i<2;i++){await page.mouse.move(700,440);await page.waitForTimeout(120);await page.mouse.down({button:'right'});await page.waitForTimeout(60);await page.mouse.move(1300,430,{steps:16});await page.waitForTimeout(100);await page.mouse.up({button:'right'});await page.waitForTimeout(180);}
  await page.mouse.move(1000,440);await shot('00-before-wheel.png');
  await wheel('01-positive-240-x8',240,8,120);
  await wheel('02-positive-12000-x8',12000,8,250);
  await wheel('03-negative-12000-x16',-12000,16,250);
  await wheel('04-positive-120000-x4',120000,4,250);
  if(errors.length)throw Error(errors[0]);
 }catch(e){failure=e.message;stamp('error',{message:e.message});}
 finally{await page.mouse.up({button:'right'}).catch(()=>{});await context.close();fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));fs.writeFileSync(path.join(out,'diagnostic.json'),JSON.stringify({completed:!failure,error:failure,errors,phases,url:process.env.BORROWED_LIGHT_QA_URL||'http://127.0.0.1:8779/',events,snapshots,scope:'Real browser input and screenshots only; no video, Unity transform/state changes or frame-rate override. Passive DOM observer records delivered wheel inputs but cannot measure Unity scroll units directly. New-journey Tab exploring is used to avoid repeating puzzles; this is not final portrait/blink acceptance.'},null,2));}
 if(failure)throw Error(failure);
})().catch(e=>{console.error(e);process.exitCode=1;});
