'use strict';
// Real browser startup/input evidence for JieGuang, without game-state injection.
// A fresh ephemeral context isolates the game save. Run only against a local build.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.JG_PLAYWRIGHT || 'C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const url = process.env.JG_QA_URL || 'http://127.0.0.1:8765/';
let out = path.resolve(process.env.JG_QA_OUT || 'art/verification/game-v2-web-qa');
if (fs.existsSync(path.join(out, 'web-report.json'))) out = path.join(out, new Date().toISOString().replace(/[:.]/g, '-'));
fs.mkdirSync(out, { recursive: true });
const width = Number(process.env.JG_QA_WIDTH || 1600), height = Number(process.env.JG_QA_HEIGHT || 900);
const duration = Number(process.env.JG_QA_SAMPLE_MS || 12000);
const requestedAudioDuration = Number(process.env.JG_QA_AUDIO_SAMPLE_MS || 70000);
const audioDuration = Math.max(70000, Number.isFinite(requestedAudioDuration) ? requestedAudioDuration : 70000);
const messages = [], errors = [], requests = [], performanceSamples = [], screenshots = [];
const report = {
  status: 'pending', url, startedUtc: new Date().toISOString(), requestedViewport: { width, height },
  inputs: [], screenshots, errors, performanceSamples,
  defaultBrowserAutoplayPolicy: true,
  audioListeningVerified: false,
  measurementLimits: 'requestAnimationFrame measures browser callback cadence, not Unity rendered FPS. GetMetricsInfo interval fps and rolling movingAverageFps are engine-reported readings, not a separately instrumented render-frame counter. Short samples on this machine do not verify performance on an ordinary laptop. Navigation screenshots require visual confirmation; this tool has no in-engine chapter-state bridge.',
};

const percentile = (values, p) => values.length ? [...values].sort((a,b)=>a-b)[Math.max(0, Math.ceil(values.length*p)-1)] : null;
const write = () => fs.writeFileSync(path.join(out, 'web-report.json'), JSON.stringify(report, null, 2));

// Runs before Unity creates its AudioContext. Observe the normal output with a silent
// side branch; never resume a context, generate sound, or change autoplay settings.
function installAudioProbe() {
  const contexts = [], byContext = new WeakMap(), warnings = [];
  const originalConnect = window.AudioNode?.prototype.connect;
  const originalDisconnect = window.AudioNode?.prototype.disconnect;
  let gesture = null, timer;
  const note = error => { if (warnings.length < 32) warnings.push(String(error)); };
  const sample = () => {
    if (!gesture) return;
    for (const record of contexts) {
      let rms = null, peak = null;
      if (record.analyser) {
        try {
          record.analyser.getFloatTimeDomainData(record.buffer);
          let sum = 0; peak = 0;
          for (const value of record.buffer) { sum += value * value; peak = Math.max(peak, Math.abs(value)); }
          rms = Math.sqrt(sum / record.buffer.length);
        } catch (error) { note(error); }
      }
      record.samples.push({ elapsedMs: performance.now() - gesture.atMs,
        state: record.context.state, contextTime: record.context.currentTime, rms, peak,
        connectedOutputCount: [...record.taps.values()].reduce((n, outputs) => n + outputs.size, 0),
        visibility: document.visibilityState, focused: document.hasFocus() });
    }
  };
  const snapshot = () => ({
    firstTrustedGesture: gesture,
    elapsedSinceGestureMs: gesture ? performance.now() - gesture.atMs : 0,
    sampleIntervalMs: 250, fftSize: 2048, warnings: [...warnings],
    method: 'A zero-gain analyser side branch observes nodes connected to the normal AudioContext destination. Original output connections remain intact. No resume call or autoplay-policy override is used. RMS samples are graph-level mono windows, not an audio recording or a listening test.',
    contexts: contexts.map(record => ({ id: record.id, sampleRate: record.context.sampleRate,
      state: record.context.state, stateChanges: record.stateChanges, samples: record.samples,
      baseLatency: record.context.baseLatency ?? null, outputLatency: record.context.outputLatency ?? null }))
  });
  window.__jieGuangAudioQa = { snapshot, stop: () => { clearInterval(timer); sample(); return snapshot(); } };
  const onGesture = event => {
    if (gesture || !event.isTrusted) return;
    gesture = { type: event.type, atMs: performance.now(), trusted: true, targetId: event.target?.id || null,
      contextsBeforeGesture: contexts.map(record => ({ id: record.id, state: record.context.state })) };
    sample();
  };
  window.addEventListener('pointerdown', onGesture, { capture: true, passive: true });
  window.addEventListener('keydown', onGesture, { capture: true, passive: true });
  timer = setInterval(sample, 250);

  const track = context => {
    if (byContext.has(context)) return;
    const record = { id: contexts.length + 1, context, taps: new Map(), samples: [],
      stateChanges: [{ atMs: performance.now(), state: context.state }] };
    contexts.push(record); byContext.set(context, record);
    context.addEventListener('statechange', () => record.stateChanges.push({ atMs: performance.now(), state: context.state }));
  };
  if (!originalConnect || !originalDisconnect) { note('AudioNode hooks unavailable'); return; }
  const wrappers = new Map();
  for (const name of ['AudioContext', 'webkitAudioContext']) {
    const Original = window[name];
    if (!Original) continue;
    try {
      if (!wrappers.has(Original)) wrappers.set(Original, new Proxy(Original, {
        construct(target, args, newTarget) {
          const context = Reflect.construct(target, args, newTarget);
          try { track(context); } catch (error) { note(error); }
          return context;
        }
      }));
      window[name] = wrappers.get(Original);
    } catch (error) { note(error); }
  }
  window.AudioNode.prototype.connect = function(...args) {
    const result = Reflect.apply(originalConnect, this, args);
    const record = byContext.get(this.context);
    if (!record || args[0] !== this.context.destination) return result;
    try {
      if (!record.analyser) {
        record.analyser = this.context.createAnalyser();
        record.analyser.fftSize = 2048;
        record.analyser.smoothingTimeConstant = 0;
        record.buffer = new Float32Array(record.analyser.fftSize);
        record.silentSink = this.context.createGain();
        record.silentSink.gain.value = 0;
        Reflect.apply(originalConnect, record.analyser, [record.silentSink]);
        Reflect.apply(originalConnect, record.silentSink, [this.context.destination]);
      }
      const output = args[1] ?? 0;
      const outputs = record.taps.get(this) || new Set();
      if (!outputs.has(output)) {
        Reflect.apply(originalConnect, this, [record.analyser, output, 0]);
        outputs.add(output); record.taps.set(this, outputs);
      }
    } catch (error) { note(error); }
    return result;
  };
  window.AudioNode.prototype.disconnect = function(...args) {
    const result = Reflect.apply(originalDisconnect, this, args);
    const record = byContext.get(this.context), outputs = record?.taps.get(this);
    if (!outputs) return result;
    const all = args.length === 0;
    const byOutput = typeof args[0] === 'number';
    const byDestination = args[0] === this.context.destination;
    if (!all && !byOutput && !byDestination) return result;
    const selectedOutput = byOutput ? args[0] : (byDestination ? args[1] : undefined);
    for (const output of [...outputs]) {
      if (selectedOutput !== undefined && output !== selectedOutput) continue;
      // A disconnect-all/output call already removes the silent branch. Destination-
      // specific disconnects also remove our observation tap so stale sound cannot pass.
      if (byDestination) try { Reflect.apply(originalDisconnect, this, [record.analyser, output, 0]); } catch (error) { note(error); }
      outputs.delete(output);
    }
    if (!outputs.size) record.taps.delete(this);
    return result;
  };
}

function summarizeAudio(data) {
  const samples = data.contexts.flatMap(context => context.samples);
  const measured = samples.filter(sample => Number.isFinite(sample.rms) && sample.connectedOutputCount > 0);
  const running = measured.filter(sample => sample.state === 'running');
  const threshold = 0.00001;
  const nonSilent = running.filter(sample => sample.rms > threshold);
  const span = measured.length ? Math.max(...measured.map(x => x.elapsedMs)) - Math.min(...measured.map(x => x.elapsedMs)) : 0;
  return { ...data, requestedDurationMs: audioDuration, measuredSpanMs: span,
    thresholdRms: threshold, measuredSamples: measured.length, runningSamples: running.length,
    nonSilentSamples: nonSilent.length, nonSilentFractionOfRunningSamples: running.length ? nonSilent.length / running.length : null,
    medianRunningRms: percentile(running.map(x => x.rms), .5), maximumRms: measured.length ? Math.max(...measured.map(x => x.rms)) : null,
    observedAtLeastSeventySeconds: span >= 70000,
    status: span < 70000 ? 'insufficient-measurement-window'
      : !running.length ? 'no-running-output-observed'
      : nonSilent.length ? 'non-silent-signal-observed' : 'only-silence-observed',
    listeningVerified: false };
}

(async () => {
  const browser = await chromium.launch({ channel: process.env.JG_BROWSER_CHANNEL || 'msedge', headless: process.env.JG_HEADLESS === '1' });
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  await context.addInitScript(installAudioProbe);
  const page = await context.newPage();
  report.browserVersion = browser.version();
  page.on('console', msg => {
    const item = { type: msg.type(), text: msg.text(), at: Date.now() };
    messages.push(item);
    if (msg.type() === 'error') errors.push(item);
    // Chromium reports failed GPU draw calls as warnings, even when every model
    // disappears. Keep the full console log and promote the first such warning.
    if (/GL_INVALID_OPERATION|GL_INVALID_FRAMEBUFFER_OPERATION|CONTEXT_LOST_WEBGL/.test(item.text)
        && !errors.some(x => x.type === 'webgl-draw-failure'))
      errors.push({ ...item, type: 'webgl-draw-failure' });
  });
  page.on('pageerror', err => errors.push({ type: 'pageerror', text: err.stack || err.message }));
  page.on('crash', () => errors.push({ type: 'crash', text: 'Page renderer crashed' }));
  page.on('requestfailed', req => errors.push({ type: 'requestfailed', text: req.failure()?.errorText, url: req.url() }));
  page.on('response', res => {
    if (res.url().includes('/Build/')) requests.push({ url: res.url(), status: res.status(), headers: res.headers() });
    if (res.status() >= 400) errors.push({ type: 'http', status: res.status(), url: res.url() });
  });

  const shot = async (name, intendedStage) => {
    const target = path.join(out, name + '.png');
    await page.screenshot({ path: target, timeout: 90000 });
    const dimensions = await page.locator('#unity-canvas').evaluate(c => ({ bufferWidth: c.width, bufferHeight: c.height, cssWidth: c.clientWidth, cssHeight: c.clientHeight, devicePixelRatio, visibility: document.visibilityState, focused: document.hasFocus() }));
    screenshots.push({ path: target, intendedStage, actualChapterRequiresVisualReview: true, ...dimensions });
    write();
  };
  const key = async key => {
    await page.keyboard.press(key, { delay: 90 });
    report.inputs.push({ action: 'keyboard', key, at: new Date().toISOString() });
    await page.waitForTimeout(650);
  };
  const sample = async view => {
    await page.bringToFront();
    await page.locator('#unity-canvas').focus();
    const data = await page.evaluate(async ms => {
      const engine = [], raf = [];
      const start = performance.now(); let previous;
      let metricsError = null;
      const read = () => {
        try {
          const m = window.jieGuangInstance?.GetMetricsInfo?.();
          engine.push({ elapsedMs: performance.now()-start, fps: Number.isFinite(m?.fps) ? m.fps : null, movingAverageFps: Number.isFinite(m?.movingAverageFps) ? m.movingAverageFps : null,
            visibility: document.visibilityState, focused: document.hasFocus() });
        } catch (e) { metricsError = String(e); }
      };
      read();
      const interval = setInterval(read, 500);
      await new Promise(resolve => {
        const frame = t => {
          if (previous !== undefined) raf.push(t-previous);
          previous = t;
          if (t-start >= ms) resolve(); else requestAnimationFrame(frame);
        };
        requestAnimationFrame(frame);
      });
      clearInterval(interval); read();
      return { elapsedMs: performance.now()-start, engineSamples: engine, rafFrameIntervalsMs: raf, metricsError };
    }, duration);
    const intervalFps = data.engineSamples.map(x=>x.fps).filter(Number.isFinite);
    const rolling = data.engineSamples.map(x=>x.movingAverageFps).filter(Number.isFinite);
    performanceSamples.push({ view, ...data, medianEngineIntervalFps: percentile(intervalFps,.5), minimumEngineIntervalReading: intervalFps.length ? Math.min(...intervalFps) : null,
      medianEngineRollingFps: percentile(rolling,.5), browserRafP50Ms: percentile(data.rafFrameIntervalsMs,.5), browserRafP95Ms: percentile(data.rafFrameIntervalsMs,.95),
      engineThirtyFpsObservedInEveryInterval: intervalFps.length > 0 ? intervalFps.every(x=>x>=30) : null,
      allSamplesForeground: data.engineSamples.every(x=>x.visibility==='visible' && x.focused) });
    console.log('JG_WEB_SAMPLE', JSON.stringify({ view, medianEngineIntervalFps: percentile(intervalFps,.5), browserRafP95Ms: percentile(data.rafFrameIntervalsMs,.95) }));
    write();
  };
  const finishAudioSample = async () => {
    await page.bringToFront();
    await page.locator('#unity-canvas').focus();
    let data = await page.evaluate(() => window.__jieGuangAudioQa?.snapshot());
    if (!data) { report.audio = { status: 'probe-unavailable', listeningVerified: false }; return; }
    // Sampling began at the genuine title click and continues during the existing keys.
    // Leave a small margin for the timer's first post-gesture callback.
    while (data.firstTrustedGesture) {
      const measured = data.contexts.flatMap(context => context.samples)
        .filter(sample => Number.isFinite(sample.rms) && sample.connectedOutputCount > 0);
      const firstMeasured = measured.length ? Math.min(...measured.map(sample => sample.elapsedMs)) : 0;
      const targetElapsed = Math.max(audioDuration + 500, firstMeasured + audioDuration + 250);
      const remaining = targetElapsed - data.elapsedSinceGestureMs;
      if (remaining <= 0) break;
      console.log('JG_WEB_AUDIO_WAIT', JSON.stringify({ remainingMs: Math.ceil(remaining) }));
      await page.waitForTimeout(Math.min(10000, remaining));
      data = await page.evaluate(() => window.__jieGuangAudioQa.snapshot());
    }
    report.audio = summarizeAudio(await page.evaluate(() => window.__jieGuangAudioQa.stop()));
    console.log('JG_WEB_AUDIO', JSON.stringify({ status: report.audio.status, measuredSpanMs: report.audio.measuredSpanMs,
      runningSamples: report.audio.runningSamples, nonSilentSamples: report.audio.nonSilentSamples,
      medianRunningRms: report.audio.medianRunningRms, listeningVerified: false }));
    write();
  };

  try {
    write();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await shot('00-loading', 'loading page');
    await page.waitForFunction(() => !!window.jieGuangInstance || window.jieGuangPage?.state === 'failed', null, { timeout: 300000 });
    const state = await page.evaluate(() => window.jieGuangPage);
    if (state?.state === 'failed') throw new Error('Template reports startup failure');
    await page.bringToFront();
    await page.waitForTimeout(6000);
    if (await page.title() !== '借光岛') throw new Error('Unexpected browser title');
    await shot('01-title', 'Unity title');
    await sample('title-before-user-gesture');

    // Actual title Start button: reference UI is 1920×1080; row center is 150 px
    // above its bottom. A trusted Playwright mouse click also unlocks normal audio.
    const bounds = await page.locator('#unity-canvas').boundingBox();
    const scale = Math.sqrt((bounds.width/1920)*(bounds.height/1080));
    const point = { x: bounds.x+bounds.width/2, y: bounds.y+bounds.height-150*scale };
    await page.mouse.click(point.x, point.y, { delay: 100 });
    report.inputs.push({ action: 'real-title-click', ...point, at: new Date().toISOString() });
    await page.waitForTimeout(2600);
    await shot('02-map-after-title-click', 'journey map after genuine title Start click');
    // The fresh browser context has no saved progress, so the selected map node is
    // Prologue. Enter uses the game's standard input route; no SendMessage/eval.
    await key('Enter');
    await page.waitForTimeout(1700);
    await shot('03-prologue-card', 'prologue loading card');
    await page.waitForTimeout(6500);
    await shot('04-prologue-opening', 'prologue normal camera and opening narration');
    await sample('prologue-opening');
    await key('Space'); await key('Space');
    await page.waitForTimeout(1200);
    await shot('05-prologue-dialogue-input', 'prologue after real dialogue keys');
    await key('Escape');
    await page.waitForTimeout(700);
    await shot('06-pause-menu', 'pause menu after real Escape');
    await key('Escape');
    await page.waitForTimeout(700);
    await shot('07-resumed-prologue', 'prologue resumed after real Escape');
    await finishAudioSample();

    report.page = await page.evaluate(() => ({ title: document.title, state: window.jieGuangPage, crossOriginIsolated,
      userAgent: navigator.userAgent, hardwareConcurrency: navigator.hardwareConcurrency, deviceMemoryGb: navigator.deviceMemory ?? null,
      canvas: (()=>{ const c=document.getElementById('unity-canvas');return {width:c.width,height:c.height,cssWidth:c.clientWidth,cssHeight:c.clientHeight}; })() }));
    report.graphics = await page.evaluate(() => {
      const gl=document.getElementById('unity-canvas').getContext('webgl2');
      if (!gl) return null;
      const ext=gl.getExtension('WEBGL_debug_renderer_info');
      return { renderer:gl.getParameter(ext?ext.UNMASKED_RENDERER_WEBGL:gl.RENDERER), version:gl.getParameter(gl.VERSION) };
    });
    report.audioContextResumeLogged = messages.some(m=>m.text.includes('Audio context resumed'));
    report.audioListeningVerified = false;
    report.navigationStatus = 'real click and keyboard exercised; confirm map/prologue screenshots visually';
    report.status = errors.length ? 'startup-with-errors'
      : report.audio?.status !== 'non-silent-signal-observed' ? 'startup-passed-audio-not-verified'
      : 'startup-passed-navigation-needs-visual-review';
    if (errors.length) process.exitCode=1;
    else if (report.audio?.status !== 'non-silent-signal-observed') process.exitCode=2;
  } catch (err) {
    report.status='failed'; report.failure=err.stack || err.message; process.exitCode=1;
    await shot('failure', 'failure state').catch(()=>{});
  } finally {
    if (!report.audio) {
      try {
        const data = await page.evaluate(() => window.__jieGuangAudioQa?.stop());
        report.audio = data ? summarizeAudio(data) : { status: 'probe-unavailable', listeningVerified: false };
      } catch (error) { report.audio = { status: 'probe-read-failed', error: String(error), listeningVerified: false }; }
    }
    report.completedUtc=new Date().toISOString();
    report.servedBuildResources=requests;
    write();
    fs.writeFileSync(path.join(out,'browser-console.json'),JSON.stringify(messages,null,2));
    console.log('JG_WEB_RESULT',JSON.stringify({status:report.status,out,errors:errors.length}));
    await context.close(); await browser.close();
  }
})().catch(err=>{ report.status='launch-failed';report.failure=err.stack||String(err);write();console.error(err);process.exitCode=1; });
