const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'art/verification');
const old=fs.readFileSync(path.join(dir,'visual-review-v8.html'),'utf8');
const style=old.match(/<style>[\s\S]*?<\/style>/)[0];
const viewer=old.slice(old.indexOf('<dialog aria-label='));
const data=JSON.parse(fs.readFileSync(path.join(dir,'v9-release-draft/handoff-data.json'),'utf8'));
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const files=[];
function figure(file,title,caption,label='本作 / 原始实机截图'){
 files.push(file);return `<figure><div class="card-top"><span class="source ours">${label}</span><span class="resolution">检测图片尺寸…</span></div><a class="picture" href="${file}" data-title="${escape(title)}"><img src="${file}" alt="${escape(title)}" loading="lazy"><span class="image-state">正在载入原图…</span></a><figcaption><strong>${title}</strong>${caption}<div class="file">${file}</div></figcaption></figure>`;
}
const section=(n,title,note,figures)=>`<section><div class="section-head"><h2>${n} / ${title}</h2><p class="section-note">${note}</p></div><div class="grid">${figures.join('\n')}</div></section>`;
const parts=[];
parts.push(section('01','参考与本作实际游玩','常规游戏镜头；参考为日景，本作为夜景',[
 figure('../reference/littleprince-gameplay.png','参考作品实际游玩','Saccc_c 原网站截图，仅用于本地比较。人物、衣料与地景的自然度仍更成熟。','参考 / littleprince.dev'),
 figure('run-024-v9/07-walking.png','v9 · 正常漫步视角','实际巡游截图。岛屿、草地、两袖与腿部沿用 v8，本轮聚焦脸部。')
]));
parts.push(section('02','打包游戏人物近景','QA 在可操作镜头范围内设定取景；不同运行的待机姿态略有差异，不能逐像素比较',[
 figure('run-022-v8/09-traveler-portrait.png','v8 · 原人物近景','旧版保留作对照；本图不是 v9 的运行证据。'),
 figure('run-024-v9/09-traveler-portrait.png','v9 · 新脸与眼部材质','下颊、鼻唇和眼周有局部改善；嘴部和材质仍简化，未达到整体审美目标。此图由原生 QA 设定相机，真实鼠标取景见后面的网页录像。')
]));
parts.push(section('03','固定正面：旧脸与采用候选','更近的造型诊断镜头；相同姿态、夜景灯光和 0.23 补光',[
 figure('v9-face-study-baseline/01-front-open.png','旧脸 · 诊断基线','下颊有较明显的横向明暗转折；眼眶呈粗棕色亮环。'),
 figure('v9-face-study-eye-material/01-front-open.png','新脸 · 采用眼部材质','下颊更连续、眼眶更克制。模型、头部顶点色和三个眼部底色同时更新，不能把改善全部归于插值修正。')
]));
parts.push(section('04','固定侧面与闭眼','静态全闭眼检查不能代替中间帧验证',[
 figure('v9-face-study-baseline/03-side-open.png','旧脸 · 侧面','鼻尖突出，鼻下至上唇的轮廓急弯。'),
 figure('v9-face-study-eye-material/03-side-open.png','新脸 · 侧面','鼻下过渡较顺；眼裂仍窄、侧面仍偏平。'),
 figure('v9-face-study-baseline/04-front-closed.png','旧脸 · 全闭眼','保持旧图，供检查眼周与面部过渡。'),
 figure('v9-face-study-eye-material/04-front-closed.png','新脸 · 全闭眼','本张未见明显眼白漏出；几何遮挡报告与实际动态录像分别保留。')
]));
parts.push(section('05','独立眼材质对照','相同新模型、相机与灯光；只有四个眼材质的光滑度改变',[
 figure('v9-face-study-candidate/02-three-quarter-open.png','新脸 + 原有高光','横向亮条盖过虹膜，正面也出现较强蓝色反光。'),
 figure('v9-face-study-eye-material/02-three-quarter-open.png','新脸 + 降低眼部光滑度','亮条消失，虹膜与瞳孔重新可读；这组隔离对照支持高光是主要原因。')
]));
parts.push(section('06','地面候选：不采用','原/新/恢复三机位对照完成；正常游玩尺寸改善不足',[
 figure('v9-ground-contact-study/lamp-baseline.png','原地面 · 灯座近景','两张贴图在诊断中用相同 RGBA32、sRGB、mip 和过滤设置，正常资源仍为原地面。'),
 figure('v9-ground-contact-study/lamp-candidate.png','接触染色候选 · 未合入','局部暗化可辨，但根部可信度没有稳定改善。早期颜色空间统计误标已纠正；见原始审计，不以“更暗”判定更自然。')
]));
parts.push(section('07','v9 浏览器原始画面','正常真实键盘通关与刷新续玩验收',[
 figure('web-010-v9/05-stars-return.png','网页 · 星空结尾','本次浏览器构建的原始截图。'),
 figure('web-010-v9/06-walking.png','网页 · 漫步视角','正常 QA 与另行录屏分开；此图前的帧率样本在松开 W 后采集，不是连续行走均值。')
]));
const videoFile='web-v9-portrait-video/portrait-time-cut.webm';files.push(videoFile);
parts.push(`<section><div class="section-head"><h2>08 / 实际镜头与自然眨眼录像</h2><p class="section-note">真实键鼠 · 普通待机与眨眼逻辑 · 录屏不是性能测试</p></div><figure><video class="clip" controls preload="metadata" playsinline src="${videoFile}" aria-label="借光岛 v9 实际待机与自然眨眼录像"></video><figcaption><strong>近景待机、轻微转头和自然眨眼</strong>以真实右键与滚轮移动游戏镜头，随后记录普通待机；没有注入人物、相机或骨骼变换。<a href="web-v9-portrait-video/review.json">所见帧审查</a>与<a href="web-v9-portrait-video/time-cut-verification.json">截取验证</a>保留具体范围。录像帧率不是引擎 FPS，所见动作不覆盖所有姿态。</figcaption></figure></section>`);
for(const file of files)if(!fs.existsSync(path.resolve(dir,file)))throw Error('Missing review evidence: '+file);
const html=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>借光岛 v9 · 本地实机美术对照</title>${style}</head><body><main><header><div class="eyebrow">Borrowed Light · v9 · Local visual review</div><h1>借光岛 v9 · 人物面部对照</h1><p class="lede">${data.visual}</p><p class="lede">来源：<a href="https://littleprince.dev/">Saccc_c 原网站</a> · <a href="https://x.com/Saccc_c/status/2110694725640474759">原推文</a> · <a href="visual-review-v8.html">保留的 v8 审阅页</a>。本页仅供本地审阅，未发布。</p><div class="tags"><span class="tag">run-024-v9</span><span class="tag">web-010-v9</span><span class="tag">1440 × 900 原图</span><span class="tag">脸部近景与实际眨眼分别验证</span><span class="tag pending">整体审美目标未达到</span></div></header>${parts.join('\n')}<aside class="review"><div><h2>结论与证据边界</h2><p>${data.visual}</p><p>${data.performance}</p><p>固定近景比正常游玩更近，属于造型诊断。所有展示图片链接原始截图，没有裁切、调色或重绘；Blender 预览没有混入实机证据。</p></div><ul class="criteria"><li>嘴部表情与眼周仍可改进</li><li>衣料重量和材质层次仍较简单</li><li>地面与石材自然度仍落后参考</li><li>未声称单一路线覆盖全部姿态</li></ul></aside><footer>借光岛 v9 · 原创角色与场景 · 参考署名 Saccc_c · 无统计或上传功能</footer></main>${viewer}`;
fs.writeFileSync(path.join(dir,'v9-release-draft/visual-review.html'),html);
fs.writeFileSync(path.join(dir,'v9-release-draft/visual-review-files.json'),JSON.stringify({allFilesExist:true,count:files.length,files},null,2));
console.log(JSON.stringify({filesChecked:files.length,draft:'art/verification/v9-release-draft/visual-review.html'}));
