
    'use strict';
    const canvas = document.getElementById('unity-canvas');
    const loading = document.getElementById('loading');
    const status = document.getElementById('status');
    const progress = document.getElementById('progress');
    const track = document.querySelector('.track');
    let failed = false;
    window.jieGuangPage = { state: 'loading', progress: 0, firstTrustedGesture: null };

    const config = {
      arguments: [],
      dataUrl: 'Build/template-test-file',
      frameworkUrl: 'Build/template-test-file',

      workerUrl: 'Build/template-test-file',


      codeUrl: 'Build/template-test-file',

      streamingAssetsUrl: 'StreamingAssets',
      companyName: "JieGuang",
      productName: "JieGuang",
      productVersion: "JieGuang",
      autoSyncPersistentDataPath: true,
      matchWebGLToCanvasSize: true,
      devicePixelRatio: 1,
      showBanner(message, type) {
        if (type === 'error') fail(message);
        else if (type === 'warning') console.warn(message);
      }
    };

    function fail(reason) {
      failed = true;
      window.jieGuangPage.state = 'failed';
      loading.hidden = false;
      loading.classList.remove('leaving');
      status.textContent = '暂时没能抵达小岛，请重新试试。';
      document.getElementById('retry').hidden = false;
      console.error('[JieGuang] Loading failed:', reason);
    }
    document.getElementById('retry').addEventListener('click', () => location.reload());

    // Unity 6000.3's Audio.js already resumes its AudioContext after a browser user
    // gesture. Keep that normal policy: focus on a real click/key, do not fabricate a
    // click or create a second context, and never disable browser autoplay protection.
    function userGesture(event) {
      if (event.isTrusted && !window.jieGuangPage.firstTrustedGesture)
        window.jieGuangPage.firstTrustedGesture = { type: event.type, atMs: performance.now() };
      if (event.target === canvas) canvas.focus({ preventScroll: true });
    }
    canvas.addEventListener('pointerdown', userGesture);
    canvas.addEventListener('keydown', userGesture);
    canvas.addEventListener('contextmenu', event => event.preventDefault());
    window.addEventListener('keydown', event => {
      if (document.activeElement === canvas && ['Tab', ' ', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key))
        event.preventDefault();
    });

    if (typeof createUnityInstance !== 'function') fail('Unity loader unavailable');
    else createUnityInstance(canvas, config, value => {
      const percent = Math.max(0, Math.min(100, Math.round(value * 100)));
      window.jieGuangPage.progress = percent;
      progress.style.width = percent + '%';
      track.setAttribute('aria-valuenow', String(percent));
      status.textContent = value < .9 ? '正在抵达小岛…… ' + percent + '%' : '小岛就在眼前……';
    }).then(instance => {
      window.jieGuangInstance = instance;
      if (failed) return;
      window.jieGuangPage.state = 'ready';
      loading.classList.add('leaving');
      setTimeout(() => { if (!failed) loading.hidden = true; }, 700);
      canvas.focus({ preventScroll: true });
    }).catch(fail);
  
