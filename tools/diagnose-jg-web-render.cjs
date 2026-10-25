'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright');
const out = path.resolve(process.env.JG_QA_OUT || 'art/verification/game-v2-web-r8-render-diagnostic');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: false });
  const context = await browser.newContext({ viewport: { width: 1600, height: 900 } });
  await context.addInitScript(() => {
    const proto = WebGL2RenderingContext.prototype, textures = new WeakMap();
    const failures = [], programs = new WeakSet();
    let draws = 0, checked = 0;
    window.jgGlDiagnostic = { failures, snapshot: () => ({ failures, draws, checked }) };
    for (const name of ['texImage2D', 'texStorage2D', 'texImage3D', 'texStorage3D']) {
      const original = proto[name];
      proto[name] = function(...args) {
        const result = Reflect.apply(original, this, args);
        const target = args[0];
        const binding = target === this.TEXTURE_2D ? this.TEXTURE_BINDING_2D : target === this.TEXTURE_2D_ARRAY ? this.TEXTURE_BINDING_2D_ARRAY : target === this.TEXTURE_3D ? this.TEXTURE_BINDING_3D : null;
        if (binding) {
          const tex = this.getParameter(binding);
          if (tex) textures.set(tex, { api: name, args: args.slice(0, name.includes('Storage') ? 6 : 8).map(x => typeof x === 'number' ? x : typeof x) });
        }
        return result;
      };
    }
    const samplerTypes = new Set([35678,35680,35682,36289,36292,36293,36298,36299,36300,36303,36306,36307,36308,36311]);
    for (const name of ['drawElements', 'drawArrays', 'drawElementsInstanced', 'drawArraysInstanced']) {
      const original = proto[name];
      proto[name] = function(...args) {
        draws++;
        if (failures.length >= 5) return Reflect.apply(original, this, args);
        const before = this.getError();
        const result = Reflect.apply(original, this, args);
        const error = this.getError(); checked++;
        if (!error) return result;
        const program = this.getParameter(this.CURRENT_PROGRAM);
        if (!program || programs.has(program)) return result;
        programs.add(program);
        const active = this.getParameter(this.ACTIVE_TEXTURE), uniforms = [];
        for (let i = 0; i < this.getProgramParameter(program, this.ACTIVE_UNIFORMS); i++) {
          const info = this.getActiveUniform(program, i);
          if (!samplerTypes.has(info.type)) continue;
          const value = this.getUniform(program, this.getUniformLocation(program, info.name));
          const unit = typeof value === 'number' ? value : value?.[0];
          this.activeTexture(this.TEXTURE0 + unit);
          const tex = this.getParameter(this.TEXTURE_BINDING_2D);
          const sampler = this.getParameter(this.SAMPLER_BINDING);
          uniforms.push({ name: info.name, type: info.type, size: info.size, unit,
            texture2D: tex ? textures.get(tex) || 'untracked' : null,
            textureCompareMode: tex ? this.getTexParameter(this.TEXTURE_2D, this.TEXTURE_COMPARE_MODE) : null,
            samplerCompareMode: sampler ? this.getSamplerParameter(sampler, this.TEXTURE_COMPARE_MODE) : null });
        }
        this.activeTexture(active);
        failures.push({ draw: draws, api: name, args, before, error, uniforms,
          shaders: this.getAttachedShaders(program).map(s => ({ type: this.getShaderParameter(s, this.SHADER_TYPE), source: this.getShaderSource(s) })) });
        return result;
      };
    }
  });
  const page = await context.newPage();
  await page.goto(process.env.JG_QA_URL || 'http://127.0.0.1:8767/');
  await page.waitForFunction(() => !!window.jieGuangInstance, null, { timeout: 300000 });
  await page.waitForTimeout(8000);
  const data = await page.evaluate(() => window.jgGlDiagnostic.snapshot());
  fs.writeFileSync(path.join(out, 'gl-diagnostic.json'), JSON.stringify(data, null, 2));
  await page.screenshot({ path: path.join(out, 'title.png') });
  console.log(JSON.stringify({ out, draws: data.draws, checked: data.checked, failures: data.failures.map(({shaders,...x})=>x) }));
  await context.close(); await browser.close();
})().catch(e => { console.error(e); process.exitCode = 1; });
