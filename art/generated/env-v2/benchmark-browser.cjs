// Interactive, isolated browser for observation only. No asset response bodies are saved.
const {chromium}=require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const path=require('node:path');
(async()=>{
 const context=await chromium.launchPersistentContext(path.join(__dirname,'benchmark-browser-profile'),{
  executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless:false,viewport:null,chromiumSandbox:true,acceptDownloads:false,
  args:['--remote-debugging-port=9337','--force-device-scale-factor=1','--window-size=1456,1038','--window-position=0,0'],
 });
 console.log('BENCHMARK_BROWSER_READY http://127.0.0.1:9337');
 await new Promise(resolve=>context.on('close',resolve));
 console.log('BENCHMARK_BROWSER_CLOSED');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
