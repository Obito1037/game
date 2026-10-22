// Diagnostic only: temporary draw omission in an isolated browser measures GPU cost.
// The shipping game, assets, shaders, and verifier are never changed by this script.
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.env.BORROWED_LIGHT_PROFILE_DIR||'art/verification/web-v4-profile');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve('tools/game-browser-profile-diagnostic'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1});
 const page=await context.newPage(),phases=[],messages=[];
 page.on('console',m=>{messages.push(m.text());const p=m.text().match(/BORROWED_LIGHT_PHASE:(\d+)/);if(p)phases.push(+p[1]);});
 await page.addInitScript(()=>{
  const proto=WebGL2RenderingContext.prototype,shaderSources=new WeakMap(),programs=new WeakMap(),locations=new WeakMap();let nextId=1,current=null;
  const diag=window.__drawDiagnostic={mode:'baseline',records:[],draws:0,omitted:0,triangles:0,skyFrames:0,foliageDraws:0};
  const wrap=(name,fn)=>{const original=proto[name];proto[name]=function(...args){return fn.call(this,original,args);};};
  wrap('shaderSource',function(original,args){shaderSources.set(args[0],args[1]);return original.apply(this,args);});
  wrap('attachShader',function(original,args){let info=programs.get(args[0]);if(!info){info={id:nextId++,sources:[],uniforms:{},draws:0,triangles:0,kind:'other'};programs.set(args[0],info);diag.records.push(info);}info.sources.push(shaderSources.get(args[1])||'');return original.apply(this,args);});
  wrap('linkProgram',function(original,args){const p=programs.get(args[0]);if(p){const source=p.sources.join('\n');p.kind=source.includes('_SurfaceKind')?'painted':source.includes('_Night')?'sky':source.includes('43758')&&source.includes('311.7')?'moon':'other';}return original.apply(this,args);});
  wrap('useProgram',function(original,args){current=programs.get(args[0])||null;return original.apply(this,args);});
  wrap('getUniformLocation',function(original,args){const loc=original.apply(this,args);if(loc)locations.set(loc,{program:programs.get(args[0]),name:args[1]});return loc;});
  for(const name of ['uniform1f','uniform1fv'])wrap(name,function(original,args){const loc=locations.get(args[0]);if(loc?.program){const val=name==='uniform1f'?args[1]:args[1][args[2]||0];loc.program.uniforms[loc.name]=val;if(loc.name.includes('_SurfaceKind'))loc.program.surfaceKind=val;}return original.apply(this,args);});
  for(const name of ['drawElements','drawArrays','drawElementsInstanced','drawArraysInstanced'])wrap(name,function(original,args){
   const count=name.includes('Elements')?args[1]:args[2],instances=name.endsWith('Instanced')?args[args.length-1]:1;
   const triangles=args[0]===this.TRIANGLES?count/3*instances:0;
   diag.draws++;diag.triangles+=triangles;if(current){current.draws++;current.triangles+=triangles;if(current.kind==='sky')diag.skyFrames++;}
   const foliage=current?.kind==='painted'&&current.surfaceKind>3.5&&current.surfaceKind<4.5;if(foliage)diag.foliageDraws++;
   const skip=(diag.mode==='skip-moon'&&current?.kind==='moon')||(diag.mode==='skip-foliage'&&foliage)||(diag.mode==='skip-painted'&&current?.kind==='painted')||(diag.mode==='skip-sky'&&current?.kind==='sky')||diag.mode==='skip-all';
   if(skip){diag.omitted++;return;}return original.apply(this,args);
  });
 });
 const press=async k=>{await page.keyboard.press(k,{delay:90});await page.waitForTimeout(280);};
 const sample=async(view,mode)=>{
  await page.bringToFront();await page.evaluate(mode=>window.__drawDiagnostic.mode=mode,mode);await page.waitForTimeout(1000);
  const result=await page.evaluate(async()=>{const d=window.__drawDiagnostic,start=performance.now(),draws=d.draws,omitted=d.omitted,triangles=d.triangles,skyFrames=d.skyFrames,foliageDraws=d.foliageDraws;let frames=0;await new Promise(resolve=>{const frame=()=>{frames++;if(performance.now()-start>=5000)resolve();else requestAnimationFrame(frame);};requestAnimationFrame(frame);});const elapsed=performance.now()-start,renderFrames=d.skyFrames-skyFrames;return {mode:d.mode,elapsedMs:elapsed,renderedFrameFps:renderFrames*1000/elapsed,rafFps:frames*1000/elapsed,drawsPerRenderedFrame:(d.draws-draws)/renderFrames,foliageDrawsPerRenderedFrame:(d.foliageDraws-foliageDraws)/renderFrames,omittedPerRenderedFrame:(d.omitted-omitted)/renderFrames,trianglesPerRenderedFrame:(d.triangles-triangles)/renderFrames,visibility:document.visibilityState,focused:document.hasFocus(),metrics:window.borrowedLight.GetMetricsInfo?.()};});
  result.view=view;console.log('SAMPLE',JSON.stringify(result));return result;
 };
 try{
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.bringToFront();await page.waitForTimeout(7000);
  const samples=[];for(const mode of ['baseline','skip-moon','baseline'])samples.push(await sample('menu',mode));
  await page.evaluate(()=>window.__drawDiagnostic.mode='baseline');await page.mouse.click(195,566);await page.waitForTimeout(2000);
  for(const k of ['1','d','Enter','2','d','Enter','3','d','2','d','Space','1','Space','Enter'])await press(k);
  if(phases.at(-1)!==4)throw new Error('Did not reach epilogue: '+JSON.stringify(phases));await page.waitForTimeout(6500);
  for(const mode of ['baseline','skip-moon','baseline'])samples.push(await sample('epilogue',mode));
  await page.evaluate(()=>window.__drawDiagnostic.mode='baseline');await page.mouse.click(210,634);await page.waitForTimeout(2500);await page.keyboard.down('w');await page.waitForTimeout(1100);await page.keyboard.up('w');await page.waitForTimeout(700);
  for(const mode of ['baseline','skip-foliage','baseline','skip-foliage','baseline','skip-painted','baseline','skip-moon','baseline','skip-all'])samples.push(await sample('walking',mode));
  await page.evaluate(()=>window.__drawDiagnostic.mode='baseline');await page.waitForTimeout(1500);await page.screenshot({path:path.join(out,'baseline-restored.png')});
  const records=await page.evaluate(()=>window.__drawDiagnostic.records);fs.writeFileSync(path.join(out,'programs.json'),JSON.stringify(records,null,2));
  fs.writeFileSync(path.join(out,'profile-results.json'),JSON.stringify({diagnosticOnly:true,viewSize:[1440,900],phases,samples},null,2));
 }finally{fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));await context.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
