// Local diagnostic only; never changes the shipping Unity code or graphics settings.
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve('art/verification/web-v5-gpu-profile');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const context=await chromium.launchPersistentContext(path.resolve('tools/game-browser-profile-v5-gpu'),{channel:'msedge',headless:false,viewport:{width:1440,height:900},deviceScaleFactor:1});
 const page=await context.newPage(),messages=[],phases=[];
 page.on('console',m=>{messages.push(m.text());const p=m.text().match(/BORROWED_LIGHT_PHASE:(\d+)/);if(p)phases.push(+p[1]);});
 await page.addInitScript(()=>{
  const proto=WebGL2RenderingContext.prototype,sources=new WeakMap(),programs=new WeakMap();let current=null,nextId=1,glRef=null,extension=null,checked=false,activeQuery=null;
  const state=window.__gpuProfile={records:[],pending:[],resolved:[],mode:'normal',skyFrames:0,draws:0,skipped:0,extensionAvailable:null,disjoint:false,capture:false,remaining:0,captureFrame:0};
  const closeQuery=()=>{if(activeQuery){glRef.endQuery(extension.TIME_ELAPSED_EXT);state.pending.push(activeQuery);activeQuery=null;}};
  const wrap=(name,fn)=>{const original=proto[name];proto[name]=function(...args){return fn.call(this,original,args);};};
  wrap('shaderSource',function(original,args){sources.set(args[0],args[1]);return original.apply(this,args);});
  wrap('attachShader',function(original,args){let p=programs.get(args[0]);if(!p){p={id:nextId++,sources:[],draws:0,triangles:0,kind:'other'};programs.set(args[0],p);state.records.push(p);}p.sources.push(sources.get(args[1])||'');return original.apply(this,args);});
  wrap('linkProgram',function(original,args){const p=programs.get(args[0]);if(p){const text=p.sources.join('\n');p.kind=text.includes('_SurfaceKind')?'painted':text.includes('_Night')?'sky':text.includes('43758')&&text.includes('311.7')?'moon':text.includes('0.730000')&&text.includes('_Time')?'foliage':'other';}return original.apply(this,args);});
  wrap('useProgram',function(original,args){if(activeQuery&&activeQuery.program!==programs.get(args[0])?.id)closeQuery();current=programs.get(args[0])||null;return original.apply(this,args);});
  for(const name of ['drawElements','drawArrays','drawElementsInstanced','drawArraysInstanced'])wrap(name,function(original,args){
   glRef=this;if(!checked){extension=this.getExtension('EXT_disjoint_timer_query_webgl2');checked=true;state.extensionAvailable=!!extension;}
   if(current?.kind==='sky'){
    state.skyFrames++;
    if(state.remaining>0){closeQuery();if(state.capture)state.remaining--;state.capture=state.remaining>0;if(state.capture)state.captureFrame++;}
   }
   const count=name.includes('Elements')?args[1]:args[2],instances=name.endsWith('Instanced')?args.at(-1):1,triangles=args[0]===this.TRIANGLES?count/3*instances:0;
   state.draws++;if(current){current.draws++;current.triangles+=triangles;}
   const skip=state.mode==='skip-foliage'&&current?.kind==='foliage'||state.mode==='skip-painted'&&current?.kind==='painted';
   if(skip){state.skipped++;return;}
   if(extension&&state.capture){if(!activeQuery){const query=this.createQuery();activeQuery={query,program:current?.id??0,kind:current?.kind??'unknown',frame:state.captureFrame,draws:0,triangles:0};this.beginQuery(extension.TIME_ELAPSED_EXT,query);}activeQuery.draws++;activeQuery.triangles+=triangles;}
   return original.apply(this,args);
  });
  state.arm=frames=>{if(!extension)throw new Error('GPU timer extension unavailable');state.remaining=frames;state.capture=false;};
  state.collect=()=>{if(!extension)return [];state.disjoint=!!glRef.getParameter(extension.GPU_DISJOINT_EXT);const waiting=[];for(const item of state.pending){if(glRef.getQueryParameter(item.query,glRef.QUERY_RESULT_AVAILABLE)){const ns=glRef.getQueryParameter(item.query,glRef.QUERY_RESULT);glRef.deleteQuery(item.query);const {query,...record}=item;state.resolved.push({...record,gpuMs:ns/1000000,disjoint:state.disjoint});}else waiting.push(item);}state.pending=waiting;return {remaining:state.remaining,pending:waiting.length,results:state.resolved,disjoint:state.disjoint};};
 });
 const press=async key=>{await page.keyboard.press(key,{delay:90});await page.waitForTimeout(280);};
 const sample=async mode=>{
  await page.bringToFront();await page.evaluate(mode=>window.__gpuProfile.mode=mode,mode);await page.waitForTimeout(750);
  const start=await page.evaluate(()=>({time:performance.now(),frames:__gpuProfile.skyFrames,draws:__gpuProfile.draws,skipped:__gpuProfile.skipped}));
  const metrics=[];for(let i=0;i<6;i++){await page.waitForTimeout(500);metrics.push(await page.evaluate(()=>({time:performance.now(),visibility:document.visibilityState,focused:document.hasFocus(),...window.borrowedLight.GetMetricsInfo()})));}
  const end=await page.evaluate(()=>({time:performance.now(),frames:__gpuProfile.skyFrames,draws:__gpuProfile.draws,skipped:__gpuProfile.skipped}));
  const result={mode,renderFps:(end.frames-start.frames)*1000/(end.time-start.time),drawsPerFrame:(end.draws-start.draws)/(end.frames-start.frames),skippedPerFrame:(end.skipped-start.skipped)/(end.frames-start.frames),metrics};console.log('SAMPLE',JSON.stringify(result));return result;
 };
 try{
  await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!window.borrowedLight,null,{timeout:180000});await page.bringToFront();await page.waitForTimeout(6500);
  const extension=await page.evaluate(()=>__gpuProfile.extensionAvailable);console.log('GPU_TIMER_EXTENSION',extension);
  await page.mouse.click(195,566);await page.waitForTimeout(2000);for(const key of ['1','d','Enter','2','d','Enter','3','d','2','d','Space','1','Space','Enter'])await press(key);
  if(phases.at(-1)!==4)throw new Error('Puzzle sequence did not finish: '+phases);await page.waitForTimeout(6500);await page.mouse.click(210,634);await page.waitForTimeout(2500);await page.keyboard.down('w');await page.waitForTimeout(1100);await page.keyboard.up('w');await page.waitForTimeout(2200);
  const baseline=await sample('normal');let timer=null,ab=[];
  if(extension){await page.evaluate(()=>__gpuProfile.arm(3));for(let i=0;i<10;i++){await page.waitForTimeout(500);timer=await page.evaluate(()=>__gpuProfile.collect());if(!timer.remaining&&!timer.pending)break;}console.log('GPU_TIMINGS',JSON.stringify(timer));}
  else for(const mode of ['skip-foliage','normal','skip-painted','normal'])ab.push(await sample(mode));
  await page.evaluate(()=>__gpuProfile.mode='normal');await page.waitForTimeout(500);await page.screenshot({path:path.join(out,'walking-normal-restored.png')});
  const records=await page.evaluate(()=>__gpuProfile.records);fs.writeFileSync(path.join(out,'programs.json'),JSON.stringify(records,null,2));
  fs.writeFileSync(path.join(out,'profile-results.json'),JSON.stringify({build:'v5',diagnosticOnly:true,width:1440,height:900,extension,phases,baseline,timer,ab},null,2));
 }finally{fs.writeFileSync(path.join(out,'browser-console.txt'),messages.join('\n'));await context.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
