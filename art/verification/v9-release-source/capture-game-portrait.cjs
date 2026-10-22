// Normal-input portrait / blink evidence. This recording is not an FPS benchmark.
// Environment: BORROWED_LIGHT_QA_URL / BUILD_ID / REVISION / PORTRAIT_DIR / PORTRAIT_PROFILE.
// Based on capture-game-gait.cjs; no screenshots, game transforms or time overrides.
const fs = require('node:fs'), path = require('node:path');
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve('tools/playwright-media');
const { chromium } = require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const out = path.resolve(process.env.BORROWED_LIGHT_PORTRAIT_DIR || 'art/verification/web-v9-portrait-video');
const profile = path.resolve(process.env.BORROWED_LIGHT_PORTRAIT_PROFILE || 'tools/game-browser-profile-v9-portrait-normal-wheel');
const requestedUrl = process.env.BORROWED_LIGHT_QA_URL || 'http://127.0.0.1:8765/';
const revision = process.env.BORROWED_LIGHT_REVISION || 'v9';

(async () => {
  fs.mkdirSync(out, { recursive: true });
  let context = null, page = null, video = null, videoFile = null;
  let navigationStartedAt = Date.now(), portraitStart = null, portraitEnd = null;
  let completed = false, failure = null, canvasMetrics = null, finalUrl = null;
  const messages = [], errors = [], phases = [], events = [], servedBuildResources = [], buildResponses = [];
  const stamp = (type, data = {}) => events.push({ type, sinceNavigationMs: Date.now() - navigationStartedAt, ...data });
  const fail = message => { errors.push(message); if (!failure) failure = message; };
  const canvasState = () => page.evaluate(() => {
    const canvas = document.getElementById('unity-canvas');
    if (!canvas) return null;
    const bounds = canvas.getBoundingClientRect();
    return { width: canvas.width, height: canvas.height, cssWidth: bounds.width, cssHeight: bounds.height,
      cssLeft: bounds.left, cssTop: bounds.top, devicePixelRatio, viewportWidth: innerWidth, viewportHeight: innerHeight,
      visibility: document.visibilityState, documentFocused: document.hasFocus(), canvasFocused: document.activeElement === canvas };
  });
  const press = async key => {
    stamp('keyboard-press-start', { key, delayRequestedMs: 90 });
    await page.keyboard.press(key, { delay: 90 });
    stamp('keyboard-press-end', { key });
    await page.waitForTimeout(280);
  };
  const orbit = async pass => {
    await page.mouse.move(700, 440);
    // Let the unpressed reposition clear before holding RMB; otherwise Unity
    // could consume its delta in the same input update as button-down.
    await page.waitForTimeout(120);
    const start = Date.now();
    stamp('right-mouse-orbit-start', { pass, from: [700, 440], to: [1300, 430], deltaX: 600,
      nominalYawDeltaDegrees: 78, nominalSensitivityDegreesPerPixel: 0.13 });
    await page.mouse.down({ button: 'right' });
    try {
      await page.waitForTimeout(60);
      await page.mouse.move(1300, 430, { steps: 16 });
      await page.waitForTimeout(100);
    } finally { await page.mouse.up({ button: 'right' }); }
    stamp('right-mouse-orbit-end', { pass, actualHeldMs: Date.now() - start });
    await page.waitForTimeout(180);
  };
  try {
    context = await chromium.launchPersistentContext(profile, {
      channel: 'msedge', headless: false, viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1,
      recordVideo: { dir: path.join(out, 'raw-video'), size: { width: 1440, height: 900 } }
    });
    page = context.pages()[0] || await context.newPage();
    video = page.video();
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/Build/') && !servedBuildResources.includes(url)) servedBuildResources.push(url);
    });
    page.on('response', response => {
      if (response.url().includes('/Build/')) buildResponses.push({ url: response.url(), status: response.status() });
    });
    page.on('requestfailed', request => {
      const message = 'Request failed: ' + request.url() + ' — ' + (request.failure()?.errorText || 'unknown');
      errors.push(message); stamp('request-failed', { url: request.url(), message });
    });
    page.on('console', message => {
      const text = message.text(); messages.push(text);
      if (message.type() === 'error') errors.push(text);
      const match = text.match(/BORROWED_LIGHT_PHASE:(\d+)/);
      if (match) { const phase = Number(match[1]); phases.push(phase); stamp('game-phase', { phase }); }
    });
    page.on('pageerror', error => { errors.push(error.message); stamp('page-error', { message: error.message }); });
    page.on('crash', () => { errors.push('Game renderer crashed'); stamp('renderer-crashed'); });

    navigationStartedAt = Date.now();
    stamp('navigation-start', { requestedUrl });
    await page.goto(requestedUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    finalUrl = page.url();
    await page.waitForFunction(() => !!window.borrowedLight, null, { timeout: 180000 });
    await page.bringToFront();
    await page.waitForTimeout(6500);
    canvasMetrics = { ready: await canvasState() };
    stamp('game-ready', { url: finalUrl, canvas: canvasMetrics.ready });
    if (!canvasMetrics.ready || canvasMetrics.ready.width !== 1440 || canvasMetrics.ready.height !== 900)
      throw new Error('Expected a 1440×900 game canvas for the fixed real-input coordinates.');

    stamp('menu-click', { at: [195, 566] });
    await page.mouse.click(195, 566);
    await page.waitForTimeout(2000);
    for (const key of ['1', 'd', 'Enter', '2', 'd', 'Enter', '3', 'd', '2', 'd', 'Space', '1', 'Space', 'Enter']) await press(key);
    if (phases.at(-1) !== 4) throw new Error('Did not complete the puzzle: ' + JSON.stringify(phases));
    stamp('puzzle-completed', { phases: [...phases], method: 'Actual keyboard input' });
    await page.waitForTimeout(6500);
    stamp('return-to-island-click', { at: [210, 634] });
    await page.mouse.click(210, 634);
    await page.waitForTimeout(6500);
    await page.bringToFront();
    await page.evaluate(() => document.getElementById('unity-canvas')?.focus());

    await orbit(1);
    await orbit(2);
    // The short input diagnostic confirmed positive deltaY pulls away.
    // Use normal negative 120 pulses after the production normalized-scroll
    // sensitivity fix (.004 -> .35). Do not use huge diagnostic wheel values
    // to hide an input usability problem. Actual framing still needs review.
    await page.mouse.move(1000, 440);
    for (let pulse = 1; pulse <= 8; pulse++) {
      await page.mouse.wheel(0, -120);
      stamp('wheel-negative-y', { pulse, deltaY: -120, intendedEffect: 'Zoom closer using normal wheel input after normalized-scroll sensitivity fix' });
      await page.waitForTimeout(120);
    }
    stamp('camera-settle-start', { requestedDurationMs: 3000, nominalTotalYawDegrees: 156,
      sourceDistanceClampMinimum: 2.5, actualCameraStateMeasured: false });
    await page.waitForTimeout(3000);
    canvasMetrics.portraitStart = await canvasState();
    if (canvasMetrics.portraitStart.visibility !== 'visible' || !canvasMetrics.portraitStart.documentFocused)
      throw new Error('Game page was not visible and focused at portrait start.');
    portraitStart = Date.now();
    stamp('portrait-window-start', { requestedDurationMs: 15000, canvas: canvasMetrics.portraitStart });
    // No keyboard/mouse input, screenshots, frame pacing, or blink control here.
    await page.waitForTimeout(15000);
    portraitEnd = Date.now();
    stamp('portrait-window-end', { durationMs: portraitEnd - portraitStart });
    canvasMetrics.portraitEnd = await canvasState();
    if (canvasMetrics.portraitEnd.visibility !== 'visible' || !canvasMetrics.portraitEnd.documentFocused)
      throw new Error('Game page was not visible and focused at portrait end.');
    if (errors.length) throw new Error('Browser error during capture: ' + errors[0]);
    completed = true;
  } catch (error) {
    failure = error.message; stamp('capture-failed', { message: error.message });
  } finally {
    if (page) {
      finalUrl = page.url();
      await page.mouse.up({ button: 'right' }).catch(() => {});
      for (const key of ['w', 'a', 's', 'd', 'Space', 'Enter']) await page.keyboard.up(key).catch(() => {});
    }
    if (context) await context.close().catch(error => fail('Context close failed: ' + error.message));
    if (video) {
      try {
        const source = await video.path();
        videoFile = 'portrait-session-includes-loading.webm';
        fs.copyFileSync(source, path.join(out, videoFile));
        if (!fs.statSync(path.join(out, videoFile)).size) throw new Error('Video file is empty');
      } catch (error) { videoFile = null; fail('Video finalization failed: ' + error.message); }
    } else fail('No Playwright video object was available.');
    if (failure) completed = false;
    fs.writeFileSync(path.join(out, 'browser-console.txt'), messages.join('\n'));
    fs.writeFileSync(path.join(out, 'events.json'), JSON.stringify(events, null, 2));
    fs.writeFileSync(path.join(out, 'build-evidence.json'), JSON.stringify({
      requestedUrl, finalUrl, declaredBuildId: process.env.BORROWED_LIGHT_BUILD_ID || null,
      requestedRevision: revision, servedBuildResources, buildResponses,
      limitation: 'The declared build ID is caller-supplied; resource URLs/statuses are observed. This is not a binary hash verification.'
    }, null, 2));
    fs.writeFileSync(path.join(out, 'capture-manifest.json'), JSON.stringify({
      completed, error: failure, requestedRevision: revision, requestedUrl, finalUrl, profile,
      purpose: 'Normal real-input idle and blink visual evidence after puzzle completion and return to the island.',
      recordedVideo: videoFile, videoOnly: true, screenshotsTaken: 0, width: 1440, height: 900,
      videoScope: 'Full session including loading, keyboard puzzle completion, return to island, camera drag/zoom, settling, and the 15-second portrait window. Not a trimmed clip.',
      canvasMetrics, phases, errors, events,
      portraitWindow: portraitStart && portraitEnd ? {
        startSinceNavigationMs: portraitStart - navigationStartedAt,
        endSinceNavigationMs: portraitEnd - navigationStartedAt, durationMs: portraitEnd - portraitStart
      } : null,
      inputMethod: 'Actual keyboard puzzle completion and UI clicks; two right drags (700,440)->(1300,430), then eight normal browser wheel pulses with deltaY=-120. No actor/camera transform injection.',
      priorAttemptCorrection: 'Both earlier attempts failed near-framing acceptance. Merely reversing wheel sign did not fix the old .004 sensitivity with normalized Input System units. They remain in far-camera-attempt and second-framing-attempt archives. The separate real-input diagnostic confirmed positive deltaY pulls away; this capture uses normal negative pulses after the production sensitivity fix, pending visual framing review.',
      cameraExpectation: { nominalYawDeltaDegrees: 156, requestedMinimumDistance: 2.5,
        limitation: 'Nominal values follow WorldDirector input sensitivity/clamp. Actual camera pose, input consumption, collision correction and framing require video review.' },
      completionLimit: 'completed means the scripted capture finished without detected errors. Return-to-island is a real UI click, not a queried game-mode assertion; the reviewer must confirm exploration, framing and visible blink transitions in the video.',
      animationScope: 'Normal unmodified idle and blink logic. Capturing 15 seconds does not automatically prove every blendshape intermediate; a reviewer must inspect the video.',
      performanceLimit: 'Playwright recordVideo samples/resamples browser output. Video FPS, browser capture cadence and wall-clock duration are not actual engine FPS; no performance claim or engine frame-rate change is made.',
      timingLimit: 'Event times are navigation-relative wall-clock aids. Recording starts before navigation; these are not exact video frame timestamps.',
      focusLimit: 'Visibility/focus are checked at portrait endpoints only; these checks do not prove continuous foreground residency.',
      errorScope: 'Browser console.error, page exceptions, renderer crash, failed network requests and capture finalization; full Unity console text is retained separately.'
    }, null, 2));
    console.log('PORTRAIT_CAPTURE', JSON.stringify({ completed, video: videoFile,
      durationMs: portraitStart && portraitEnd ? portraitEnd - portraitStart : null, error: failure }));
  }
  if (failure) throw new Error(failure);
})().catch(error => { console.error(error); process.exitCode = 1; });
