/** Read-only MCP check. --verify-editor also queries the Editor version. */
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const setupDir = dirname(fileURLToPath(import.meta.url));
const workspaceDir = resolve(setupDir, '..');
const executable = resolve(workspaceDir, 'tools/unity-cli/bin/unity.exe');
const projectPath = resolve(workspaceDir, 'GameProject');
const resultPath = resolve(setupDir, 'verification/unity-mcp-result.json');
const startedAt = Date.now();
const verifyEditor = process.argv.includes('--verify-editor');
const result = {
  checkedAtUtc: new Date().toISOString(),
  executable,
  projectPath,
  commandArguments: ['mcp', '--project-path', projectPath],
  timeoutMs: 24000,
  protocolHandshake: { success: false },
  toolsCount: null,
  toolNames: [],
  editorLive: {
    verified: false,
    reason: 'Only protocol and tool discovery are tested unless --verify-editor is supplied.',
  },
  invokedMethods: [],
  stderr: '',
  nonProtocolStdout: [],
};

let child;
let lines;
let timer;
let nextId = 1;
const pending = new Map();
let exited;

function failPending(error) {
  for (const item of pending.values()) item.reject(error);
  pending.clear();
}

function request(method, params) {
  const id = nextId++;
  result.invokedMethods.push(method);
  return new Promise((resolveRequest, reject) => {
    pending.set(id, { resolve: resolveRequest, reject });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n', (error) => {
      if (error) {
        pending.delete(id);
        reject(error);
      }
    });
  });
}

async function verify() {
  child = spawn(executable, result.commandArguments, {
    cwd: workspaceDir,
    windowsHide: true,
    shell: false,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  result.spawnedPid = child.pid ?? null;
  exited = new Promise((resolveExit) => {
    child.once('close', (code, signal) => {
      result.processExit = { code, signal };
      failPending(new Error(`Local MCP process closed (${code ?? signal})`));
      resolveExit();
    });
  });
  child.on('error', failPending);
  child.stdin.on('error', failPending);
  child.stderr.on('data', (data) => {
    result.stderr = (result.stderr + data.toString('utf8')).slice(-16000);
  });
  lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  lines.on('line', (line) => {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      if (result.nonProtocolStdout.length < 10) result.nonProtocolStdout.push(line.slice(0, 1000));
      return;
    }
    if (message.jsonrpc !== '2.0' || !pending.has(message.id)) return;
    const item = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) item.reject(new Error(JSON.stringify(message.error)));
    else item.resolve(message.result);
  });

  const initialization = await request('initialize', {
    protocolVersion: '2025-03-26',
    capabilities: {},
    clientInfo: { name: 'local-readonly-install-verifier', version: '1.0.0' },
  });
  if (!initialization?.protocolVersion || !initialization?.serverInfo) {
    throw new Error('Initialize response is missing protocolVersion or serverInfo');
  }
  result.protocolHandshake.initialize = initialization;

  result.invokedMethods.push('notifications/initialized');
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');

  const listing = await request('tools/list', {});
  if (!Array.isArray(listing?.tools)) throw new Error('tools/list did not return a tools array');
  result.toolsCount = listing.tools.length;
  result.toolNames = listing.tools.map((tool) => tool.name);
  result.protocolHandshake.success = true;
  result.protocolHandshake.protocolVersion = initialization.protocolVersion;
  result.protocolHandshake.serverInfo = initialization.serverInfo;

  if (verifyEditor) {
    const evalTool = listing.tools.find((tool) => tool.name === 'eval');
    if (!evalTool?.inputSchema?.properties?.code) {
      throw new Error('The connected Editor did not expose the expected read-only eval check');
    }
    const response = await request('tools/call', {
      name: evalTool.name,
      arguments: { code: 'return UnityEngine.Application.unityVersion;' },
    });
    result.editorLive.response = response;
    if (response?.isError || !JSON.stringify(response).includes('6000.3.26f1')) {
      throw new Error('Editor version query did not return the installed Unity version');
    }
    result.editorLive.verified = true;
    result.editorLive.reason = 'A read-only MCP tools/call returned the running Editor version.';
    result.editorLive.command = 'eval';
    result.editorLive.editorVersion = '6000.3.26f1';
  }
}

try {
  const deadline = new Promise((_, reject) => {
    timer = setTimeout(() => {
      const error = new Error('Local MCP handshake timed out after 24000 ms');
      failPending(error);
      reject(error);
    }, result.timeoutMs);
  });
  await Promise.race([verify(), deadline]);
} catch (error) {
  result.error = error?.stack ?? String(error);
  process.exitCode = 1;
} finally {
  clearTimeout(timer);
  lines?.close();
  if (child && child.exitCode === null && child.signalCode === null) {
    result.cleanupTerminationRequested = child.kill();
  }
  if (exited) {
    await Promise.race([
      exited,
      new Promise((resolveWait) => {
        const cleanupTimer = setTimeout(resolveWait, 500);
        cleanupTimer.unref();
      }),
    ]);
  }
  result.elapsedMs = Date.now() - startedAt;
  await mkdir(dirname(resultPath), { recursive: true });
  await writeFile(resultPath, JSON.stringify(result, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ resultPath, ...result }, null, 2));
}
