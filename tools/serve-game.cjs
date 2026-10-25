'use strict';

// Borrowed Light Island: dependency-free, loopback-only Unity WebGL launcher.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const HOST = '127.0.0.1';
const PORT = Number(process.env.BORROWED_LIGHT_PORT || 8765);
const ADDRESS = `http://${HOST}:${PORT}/`;
const BUILD_ROOT = path.resolve(process.env.BORROWED_LIGHT_BUILD_ROOT || path.join(__dirname, '..', 'builds', 'web'));
const HEALTH_PATH = '/__borrowed_light_health';
const SERVICE_ID = 'borrowed-light-island-web-v1';
const SHOULD_OPEN = process.argv.includes('--open');
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.htm': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.wasm': 'application/wasm',
  '.data': 'application/octet-stream',
  '.unityweb': 'application/octet-stream',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ogg': 'audio/ogg',
  '.mp3': 'audio/mpeg',
  '.mp4': 'video/mp4',
};

function inside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

function securityHeaders() {
  return {
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'no-store',
  };
}

function message(response, status, text, method, extra = {}) {
  const body = Buffer.from(text, 'utf8');
  response.writeHead(status, {
    ...securityHeaders(),
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Length': body.length,
    ...extra,
  });
  response.end(method === 'HEAD' ? undefined : body);
}

function openBrowser() {
  let command, args;
  if (process.platform === 'win32') {
    command = 'rundll32.exe';
    args = ['url.dll,FileProtocolHandler', ADDRESS];
  } else if (process.platform === 'darwin') {
    command = 'open'; args = [ADDRESS];
  } else {
    command = 'xdg-open'; args = [ADDRESS];
  }
  const child = spawn(command, args, { detached: true, stdio: 'ignore', windowsHide: true });
  child.on('error', () => reportError(`游戏服务已启动，但浏览器未能自动打开。请在浏览器访问：\n${ADDRESS}`, false));
  child.unref();
}

function reportError(text, fatal = true) {
  console.error(`借光岛：${text}`);
  if (fatal) process.exitCode = 1;
  // The double-click launcher hides the helper console. Show startup errors
  // explicitly in that case; pass their text as environment data, never code.
  if (SHOULD_OPEN && process.platform === 'win32') {
    const child = spawn('powershell.exe', [
      '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command',
      'Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show($env:BORROWED_LIGHT_ERROR, "借光岛", "OK", "Warning") | Out-Null',
    ], { stdio: 'ignore', windowsHide: true, env: { ...process.env, BORROWED_LIGHT_ERROR: text } });
    child.on('error', () => {});
  }
}

function existingService() {
  return new Promise((resolve) => {
    let settled = false;
    const done = value => { if (!settled) { settled = true; resolve(value); } };
    const request = http.get({ host: HOST, port: PORT, path: HEALTH_PATH, timeout: 1500 }, response => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', chunk => {
        body += chunk;
        if (body.length > 4096) { response.destroy(); done(false); }
      });
      response.on('end', () => {
        try {
          const health = JSON.parse(body);
          done(response.statusCode === 200 && health.service === SERVICE_ID && path.resolve(health.root) === BUILD_ROOT);
        } catch { done(false); }
      });
      response.on('error', () => done(false));
    });
    request.on('timeout', () => { request.destroy(); done(false); });
    request.on('error', () => done(false));
  });
}

async function main() {
  let realRoot;
  try {
    realRoot = await fs.promises.realpath(BUILD_ROOT);
    const index = await fs.promises.realpath(path.join(realRoot, 'index.html'));
    if (!inside(realRoot, index) || !(await fs.promises.stat(index)).isFile()) throw new Error('missing index');
  } catch {
    reportError(`浏览器版游戏尚未生成或文件不完整。\n需要的文件：${path.join(BUILD_ROOT, 'index.html')}\n请完成 WebGL 构建后再双击启动。`);
    return;
  }

  const server = http.createServer(async (request, response) => {
    const method = request.method || 'GET';
    if (method !== 'GET' && method !== 'HEAD') {
      message(response, 405, '仅支持 GET 和 HEAD 请求。', method, { Allow: 'GET, HEAD' });
      return;
    }
    let pathname;
    try { pathname = decodeURIComponent((request.url || '/').split('?')[0]); }
    catch { message(response, 400, '请求地址编码无效。', method); return; }
    if (pathname === HEALTH_PATH) {
      const body = Buffer.from(JSON.stringify({ service: SERVICE_ID, root: BUILD_ROOT }), 'utf8');
      response.writeHead(200, { ...securityHeaders(), 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': body.length });
      response.end(method === 'HEAD' ? undefined : body);
      return;
    }
    // Reject traversal before normalization, including Windows separators,
    // alternate data streams and control characters. Encoded traversal is decoded.
    if (!pathname.startsWith('/') || /[\\:\x00-\x1f]/.test(pathname) || pathname.split('/').includes('..')) {
      message(response, 403, '该地址不在游戏目录内。', method); return;
    }
    const candidate = path.resolve(realRoot, `.${pathname === '/' ? '/index.html' : pathname}`);
    if (!inside(realRoot, candidate)) { message(response, 403, '该地址不在游戏目录内。', method); return; }
    try {
      // realpath also blocks symlinks and Windows directory junctions leading out.
      const filename = await fs.promises.realpath(candidate);
      if (!inside(realRoot, filename)) { message(response, 403, '该地址不在游戏目录内。', method); return; }
      const stat = await fs.promises.stat(filename);
      if (!stat.isFile()) { message(response, 404, '没有找到这个游戏文件。', method); return; }
      let uncompressedName = filename;
      const headers = { ...securityHeaders(), 'Content-Length': stat.size };
      if (filename.endsWith('.gz')) { headers['Content-Encoding'] = 'gzip'; uncompressedName = filename.slice(0, -3); }
      else if (filename.endsWith('.br')) { headers['Content-Encoding'] = 'br'; uncompressedName = filename.slice(0, -3); }
      else if (filename.endsWith('.unityweb')) {
        // Decompression-fallback builds retain the .unityweb extension. Detect
        // gzip by its bytes so the browser can decode and stream WASM normally;
        // leave non-gzip fallback files to Unity's own decoder.
        const file = await fs.promises.open(filename, 'r');
        try {
          const signature = Buffer.alloc(3);
          await file.read(signature, 0, signature.length, 0);
          if (signature[0] === 0x1f && signature[1] === 0x8b && signature[2] === 0x08) {
            headers['Content-Encoding'] = 'gzip';
            uncompressedName = filename.slice(0, -9);
          }
        } finally { await file.close(); }
      }
      headers['Content-Type'] = MIME_TYPES[path.extname(uncompressedName).toLowerCase()] || 'application/octet-stream';
      if (method === 'HEAD') { response.writeHead(200, headers); response.end(); return; }
      const stream = fs.createReadStream(filename);
      stream.once('open', () => { response.writeHead(200, headers); stream.pipe(response); });
      stream.on('error', () => {
        if (!response.headersSent) message(response, 500, '读取游戏文件失败，请重新启动。', method);
        else response.destroy();
      });
      response.on('close', () => stream.destroy());
    } catch (error) {
      const missing = error.code === 'ENOENT' || error.code === 'ENOTDIR';
      message(response, missing ? 404 : 500, missing ? '没有找到这个游戏文件。' : '读取游戏文件失败，请重新启动。', method);
    }
  });

  server.requestTimeout = 30000;
  server.headersTimeout = 10000;
  server.keepAliveTimeout = 5000;
  server.on('error', async error => {
    if (error.code === 'EADDRINUSE') {
      if (await existingService()) {
        console.log(`借光岛已经启动：${ADDRESS}`);
        if (SHOULD_OPEN) openBrowser();
      } else {
        reportError(`本机端口 ${PORT} 已被其他程序占用。\n请关闭占用程序后重新双击启动。\n游戏地址：${ADDRESS}`);
      }
    } else {
      reportError(`本机服务启动失败：${error.message}`);
    }
  });
  server.listen(PORT, HOST, () => {
    console.log(`借光岛已启动：${ADDRESS}\n游戏目录：${BUILD_ROOT}\n按 Ctrl+C 可关闭服务。`);
    if (SHOULD_OPEN) openBrowser();
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => server.close(() => process.exit(0)));
}

main().catch(error => reportError(`启动失败：${error.message}`));
