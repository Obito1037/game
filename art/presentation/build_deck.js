// 《借光岛》参赛作品汇报 — structured pptxgenjs deck (theme, layouts, placeholders, sections).
const path = require("path");
const pptxgen = require("./node_modules/pptxgenjs");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const IMG = path.join(__dirname, "img");
const img = f => path.join(IMG, f);
const V2_ISLAND = "C:/Users/20665/Desktop/game/art/verification/game-v2-visual-r8/01-island.png";
const OUT = process.argv[2];

const THEME = {
  name: "JieGuang Night",
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  colors: {
    dk1: "0B1026", lt1: "F5EDDB", dk2: "172046", lt2: "B9B3A3",
    accent1: "E9BE6E", accent2: "7FD8C7", accent3: "9BD96B", accent4: "F2A465", accent5: "7DA8EE", accent6: "C7A3E8",
    hlink: "E9BE6E", folHlink: "C7A3E8",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "借光岛 · 参赛作品汇报";
pres.author = "借光岛制作组";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const BG = C.text1, INK = C.background1, MUTED = C.background2, PANEL = C.text2, GOLD = C.accent1;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "COVER",
  background: { color: BG },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 7.0, h: 1.5, fontSize: 72, bold: true, color: INK, charSpacing: 12, valign: "middle" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.82, y: 4.25, w: 7.0, h: 1.4, fontSize: 22, color: INK, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    { image: { path: img("sparkle.png"), x: 0.55, y: 0.55, w: 0.36, h: 0.36 } },
    { placeholder: { options: { name: "title", type: "title", x: 1.0, y: 0.38, w: 11.7, h: 0.72, fontSize: 30, bold: true, color: INK, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "借光岛 · 参赛作品汇报", options: { x: 0.6, y: 6.98, w: 6, h: 0.3, fontSize: 10, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 6.98, w: 0.6, h: 0.3, fontSize: 10, color: MUTED, align: "right" },
});

// ---------------------------------------------------------------- helpers
let objectId = 0;
const name = n => `${n}-${++objectId}`;
const fs = require("fs");
// natural pixel size of a PNG or JPEG, so "cover" crops instead of stretching
function imageSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89) return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  let i = 2;
  while (i < b.length) {
    if (b[i] !== 0xff) { i++; continue; }
    const marker = b[i + 1], len = b.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xc3) return { w: b.readUInt16BE(i + 7), h: b.readUInt16BE(i + 5) };
    i += 2 + len;
  }
  throw new Error("unknown image size: " + file);
}
function coverImage(slide, file, x, y, w, h, alt) {
  const s = imageSize(file), aspect = s.w / s.h;
  // the picture keeps its aspect and is scaled to cover the box; the box crops it
  const iw = Math.max(w, h * aspect), ih = iw / aspect;
  slide.addImage({ path: file, x, y, w: iw, h: ih, sizing: { type: "cover", w, h }, objectName: name("image"), altText: alt || "" });
}
function framedImage(slide, file, x, y, w, h, opts = {}) {
  coverImage(slide, file, x, y, w, h, opts.alt);
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: GOLD, width: 1, transparency: 35 }, objectName: name("frame") });
}
function text(slide, t, o) {
  slide.addText(t, Object.assign({ isTextBox: true, margin: 0, color: INK, fontSize: 15, valign: "top" }, o, { objectName: name("text") }));
}
function dot(slide, x, y, d, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { type: "none" }, objectName: name("dot") });
}
function card(slide, x, y, w, h) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: PANEL }, line: { color: GOLD, width: 0.75, transparency: 70 }, objectName: name("card") });
}
function content(title, section, notes) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}

// ================================================================ 1 cover
pres.addSection({ title: "作品概述" });
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "作品概述" });
  coverImage(s, img("photo_02-house-window.jpg"), 0, 0, 13.333, 7.5, "借光岛岬角：阿婆的木屋、金色光树与三盏铜灯");
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 7.6, h: 7.5, fill: { color: BG, transparency: 22 }, line: { type: "none" }, objectName: name("cover-scrim") });
  s.addImage({ path: img("sparkle.png"), x: 0.85, y: 1.55, w: 0.5, h: 0.5, objectName: name("sparkle"), altText: "金色星点" });
  s.addText("借光岛", { placeholder: "title" });
  text(s, "THE ISLAND OF BORROWED LIGHT", { x: 0.85, y: 3.72, w: 7, h: 0.4, fontSize: 14, color: GOLD, charSpacing: 6 });
  s.addText([
    { text: "参赛作品汇报", options: { fontSize: 26, bold: true, breakLine: true } },
    { text: "原创剧情冒险游戏 · Unity 6 · Windows / WebGL", options: { fontSize: 16, color: MUTED } },
  ], { placeholder: "body" });
  s.addNotes("开场：《借光岛》是一款原创剧情冒险游戏。画面是游戏里的岬角：阿婆的木屋、金色光树和岛上最老的三盏铜灯。");
}

// ================================================================ 2 overview
{
  const s = content("一句话看懂《借光岛》", "作品概述",
    "用一句话介绍作品，再用四个数字说明体量。重点：这是一个完整可玩、有开篇、有结尾的故事。");
  text(s, "在一颗没有太阳的小星球上，不会发光的少年“小灯笼”替出海的朋友守护三盏灯，学会把借来的光，照在需要的地方。",
    { x: 0.9, y: 1.45, w: 11.6, h: 1.3, fontSize: 24, color: INK, lineSpacingMultiple: 1.25 });
  const stats = [["7", "个章节\n开篇 · 序章 · 三章 · 幕间 · 终章 · 尾声"], ["11", "段开篇镜头\n先讲清世界观与人物"], ["3", "个调灯关卡\n一盏灯到三盏灯"], ["5", "位主要角色\n每人一种萤光"]];
  stats.forEach(([n, label], i) => {
    const x = 0.9 + i * 3.0;
    card(s, x, 3.15, 2.75, 2.45);
    text(s, n, { x: x + 0.25, y: 3.3, w: 2.3, h: 1.1, fontSize: 60, bold: true, color: GOLD, valign: "middle" });
    text(s, label, { x: x + 0.25, y: 4.45, w: 2.35, h: 1.05, fontSize: 14, color: INK, lineSpacingMultiple: 1.15 });
  });
  text(s, "类型：剧情冒险 + 光线解谜　｜　平台：Windows / WebGL　｜　时长：约 20–30 分钟　｜　引擎：Unity 6（URP）",
    { x: 0.9, y: 6.05, w: 11.6, h: 0.4, fontSize: 14, color: MUTED });
}

// ================================================================ 3 theme & values
pres.addSection({ title: "故事与世界" });
{
  const s = content("主题：你不必是最亮的那一盏", "故事与世界",
    "这是一个没有坏人的故事。三位老人分别取材于乡邮员、塞罕坝造林者、海岛守岛人这三种平凡坚守的精神，人物均为虚构。");
  card(s, 0.9, 1.45, 5.2, 4.9);
  s.addImage({ path: img("sparkle.png"), x: 1.25, y: 1.8, w: 0.42, h: 0.42, objectName: name("sparkle"), altText: "金色星点" });
  text(s, "你不必是最亮的那一盏。\n借来的光照亮了别人，\n就成了自己的光。", { x: 1.25, y: 2.45, w: 4.6, h: 2.0, fontSize: 24, bold: true, color: INK, lineSpacingMultiple: 1.3 });
  text(s, "一个没有坏人的故事：身边的人都很好、很亮，少年却越来越不敢抬头。故事不劝他“想开点”，只陪他走过一个长夜。",
    { x: 1.25, y: 4.6, w: 4.6, h: 1.5, fontSize: 15, color: MUTED, lineSpacingMultiple: 1.2 });
  const rows = [
    ["敬业", "邮差爷爷", "一辈子沿环岛小路送信，铃声响到哪里，信就送到哪里", "原型：乡邮员", C.accent2],
    ["奉献", "阿婆", "年轻时一筐一筐背土，在荒岩上种出第一片光树", "原型：塞罕坝造林者", C.accent4],
    ["坚守", "灯伯", "老伴走后，照旧每天升旗、每晚挂灯", "原型：海岛守岛人", C.accent1],
  ];
  rows.forEach(([v, who, what, src, color], i) => {
    const y = 1.55 + i * 1.62;
    dot(s, 6.65, y + 0.1, 0.62, color);
    text(s, v, { x: 6.65, y: y + 0.1, w: 0.62, h: 0.62, fontSize: 15, bold: true, color: BG, align: "center", valign: "middle" });
    text(s, who + "　·　" + src, { x: 7.5, y: y + 0.02, w: 5.0, h: 0.4, fontSize: 18, bold: true, color: INK });
    text(s, what, { x: 7.5, y: y + 0.5, w: 5.0, h: 0.8, fontSize: 15, color: MUTED, lineSpacingMultiple: 1.15 });
  });
}

// ================================================================ 4 world
{
  const s = content("世界观：一座借光生活的岛", "故事与世界",
    "开篇用 11 个实机镜头讲清这些设定。科学依据：真实的“地照”（新月前后月亮暗面的灰光）与光污染。");
  framedImage(s, img("qa_00-intro-02.jpg"), 0.9, 1.45, 6.4, 3.6, { alt: "开篇“地光”：海面上方的蓝色地球" });
  text(s, "开篇实机画面：天上最亮的，是一颗蓝色的星——地球", { x: 0.9, y: 5.15, w: 6.4, h: 0.35, fontSize: 12, color: MUTED });
  const items = [
    ["地光", "太阳太远，地球反射的光薄薄地落在岛上", C.accent5],
    ["光树与光果", "叶子接住地光，存进会发光的果子；岛上的灯都烧光果", C.accent3],
    ["灯罩", "照向天空的光会散掉，还会把夜空照白——光要照在需要的地方", C.accent1],
    ["长夜", "每年一次，地球缩成一道细线；采光船出海运回光果", C.accent6],
    ["萤光", "每个人身上都有颜色不同的微光，只有主角不会发光", C.accent2],
  ];
  items.forEach(([h, d, color], i) => {
    const y = 1.45 + i * 0.98;
    dot(s, 7.75, y + 0.1, 0.26, color);
    text(s, h, { x: 8.2, y: y, w: 4.3, h: 0.4, fontSize: 17, bold: true });
    text(s, d, { x: 8.2, y: y + 0.4, w: 4.55, h: 0.55, fontSize: 13, color: MUTED });
  });
  text(s, "科学依据：真实的“地照”现象与光污染", { x: 0.9, y: 5.75, w: 6.4, h: 0.4, fontSize: 14, color: GOLD });
}

// ================================================================ 5 characters
{
  const s = content("人物：五种不同的光", "故事与世界",
    "每个人物都有剧本规定的萤光颜色，游戏里以边缘光和光点呈现。主角不会发光，直到终章才出现最淡的琥珀色微光。");
  const people = [
    ["char_boy.jpg", "小灯笼", "主角，12 岁。不会发光，走到哪里都提着一盏灯笼", "无 → 终章琥珀色", C.accent4],
    ["char_aying.jpg", "阿萤", "13 岁，全岛最亮的孩子；其实很怕黑", "绿里带金", C.accent3],
    ["char_abo.jpg", "阿婆", "岬角的守夜人，种下第一片光树", "暖橙，今年快看不见了", C.accent4],
    ["char_postman.jpg", "邮差爷爷", "送了一辈子信，邮包上挂着小铜铃", "青白，像清晨的薄雾", C.accent2],
    ["char_dengbo.jpg", "灯伯", "守码头的人，每晚挂灯", "淡橙，像快熄的炭火", C.accent1],
  ];
  people.forEach(([f, n, d, glow, color], i) => {
    const x = 0.9 + i * 2.38, w = 2.18;
    framedImage(s, img(f), x, 1.4, w, 2.95, { alt: n });
    text(s, n, { x, y: 4.52, w, h: 0.42, fontSize: 19, bold: true });
    dot(s, x, 5.06, 0.18, color);
    text(s, glow, { x: x + 0.27, y: 4.99, w: w - 0.27, h: 0.32, fontSize: 12, color: GOLD });
    text(s, d, { x, y: 5.42, w, h: 1.1, fontSize: 13.5, color: MUTED, lineSpacingMultiple: 1.15 });
  });
}

// ================================================================ 6 story structure
{
  const s = content("故事结构：一个长夜，八段旅程", "故事与世界",
    "按时间顺序：从开篇认识世界，到尾声在岛上漫步。每一章都有一个“把光照对地方”的选择。");
  const beats = [
    ["开篇", "认识借光岛与岛上的人"], ["序章", "阿萤出海，把光分给小灯笼"],
    ["第一章", "扶正晚风灯，照亮回家的小路"], ["第二章", "一束窄光，照亮阿婆的圆窗"],
    ["幕间", "船没回来，读到萤火虫信"], ["第三章", "把灯放低，让夜空重新变黑"],
    ["终章", "黑暗里看见自己的光，船回来了"], ["尾声", "沿着小路，和每个人说说话"],
  ];
  const x0 = 1.05, step = 1.55, yLine = 3.85;
  s.addShape(pres.shapes.LINE, { x: x0 + 0.2, y: yLine, w: step * 7, h: 0, line: { color: GOLD, width: 1.5, transparency: 40 }, objectName: name("timeline") });
  beats.forEach(([h, d], i) => {
    const cx = x0 + i * step;
    dot(s, cx, yLine - 0.2, 0.4, i === 6 ? C.accent4 : GOLD);
    const up = i % 2 === 0;
    text(s, h, { x: cx - 0.55, y: up ? 2.0 : 4.35, w: 1.5, h: 0.45, fontSize: 18, bold: true, align: "center" });
    text(s, d, { x: cx - 0.6, y: up ? 2.45 : 4.8, w: 1.6, h: 0.9, fontSize: 13.5, color: MUTED, align: "center" });
  });
  text(s, "全流程约 20–30 分钟；每章结束回到“旅程地图”，下一站在羊皮纸地图上亮起。", { x: 0.9, y: 6.1, w: 11.6, h: 0.4, fontSize: 14, color: MUTED });
}

// ================================================================ 7 core gameplay
pres.addSection({ title: "玩法设计" });
{
  const s = content("核心玩法：把光照在需要的地方", "玩法设计",
    "玩法与主题一致：光不必最亮，而要照对地方。每晚只允许一份光漏向天空，多了夜空就会变白。");
  framedImage(s, img("qa_05-puzzle-before.jpg"), 0.9, 1.45, 7.2, 4.05, { alt: "第三章调灯面板" });
  text(s, "第三章调灯面板：三盏灯、四个地方", { x: 0.9, y: 5.6, w: 7.2, h: 0.35, fontSize: 12, color: MUTED });
  const steps = [
    ["观察", "哪里黑、哪里亮，光漏到了哪里"],
    ["选灯", "数字键 1 / 2 / 3 选择要调的灯"],
    ["调整", "A / D 转动灯头，空格切换宽光、窄光"],
    ["平衡", "照亮目标的同时，让漏向天空的光最少"],
  ];
  steps.forEach(([h, d], i) => {
    const y = 1.5 + i * 1.08;
    dot(s, 8.55, y, 0.5, GOLD);
    text(s, String(i + 1), { x: 8.55, y, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: BG, align: "center", valign: "middle" });
    text(s, h, { x: 9.25, y: y - 0.02, w: 3.4, h: 0.4, fontSize: 18, bold: true });
    text(s, d, { x: 9.25, y: y + 0.4, w: 3.4, h: 0.55, fontSize: 13.5, color: MUTED });
  });
  card(s, 8.55, 5.85 - 0.05, 4.2, 0.62);
  text(s, "宽光照得广却会漏光；窄光集中却照不全", { x: 8.75, y: 5.85, w: 3.9, h: 0.5, fontSize: 13.5, color: GOLD, valign: "middle" });
}

// ================================================================ 8 level progression
{
  const s = content("关卡递进：一盏灯到三盏灯", "玩法设计",
    "三个关卡逐步增加灯和目标。第三章同时要对抗光污染：大家把灯举得太高，夜空发白，船看不见星星。");
  const levels = [
    ["qa_02-puzzle-solved.jpg", "第一章 · 山路上的铃铛", "1 盏灯 · 2 个目标", "照亮小路和长椅；学会转灯头、换灯罩"],
    ["qa_03-puzzle-solved.jpg", "第二章 · 荒原上的窗", "2 盏灯 · 3 个目标", "加上阿婆的圆窗；宽与窄的取舍"],
    ["qa_05-puzzle-solved.jpg", "第三章 · 船还没回来", "3 盏灯 · 4 个目标", "小路、长椅、圆窗、码头；只能有一束宽光"],
  ];
  levels.forEach(([f, h, n, d], i) => {
    const x = 0.9 + i * 3.95, w = 3.7;
    framedImage(s, img(f), x, 1.45, w, 2.08, { alt: h });
    text(s, h, { x, y: 3.7, w, h: 0.42, fontSize: 17, bold: true });
    text(s, n, { x, y: 4.15, w, h: 0.42, fontSize: 22, bold: true, color: GOLD });
    text(s, d, { x, y: 4.65, w, h: 0.8, fontSize: 14, color: MUTED });
  });
  text(s, "规则：每一个宽灯罩、每一束什么也没照到的光，都会让夜空少一份黑；每晚只允许一份。",
    { x: 0.9, y: 5.85, w: 11.6, h: 0.45, fontSize: 14, color: INK });
}

// ================================================================ 9 narrative staging
{
  const s = content("叙事与演出", "玩法设计",
    "演出以实机镜头完成：开篇介绍、分光、读信、星空与重逢。界面统一为“金色星点 + 衬线字 + 羊皮纸”的绘本风格。");
  const moments = [
    ["qa_01-sharing-light.jpg", "序章 · 分光", "阿萤把自己的光分给小灯笼"],
    ["qa_04-letter.jpg", "幕间 · 萤火虫信", "“你一直在暗处，所以你知道哪里最暗。”"],
    ["qa_06-reunion-hands.jpg", "终章 · 重逢", "一只亮得像春天，一只淡得像一口哈气"],
  ];
  moments.forEach(([f, h, d], i) => {
    const x = 0.9 + i * 3.95, w = 3.7;
    framedImage(s, img(f), x, 1.45, w, 2.08, { alt: h });
    text(s, h, { x, y: 3.7, w, h: 0.42, fontSize: 17, bold: true });
    text(s, d, { x, y: 4.15, w, h: 0.8, fontSize: 14, color: MUTED });
  });
  const ui = [["旅程地图", "羊皮纸地图，章节逐站解锁"], ["章节卡", "星空背景与章节插图"], ["开篇镜头", "11 段实机镜头，可按 Tab 跳过"], ["尾声漫步", "回访每个人，台词逐次展开"]];
  ui.forEach(([h, d], i) => {
    const x = 0.9 + i * 2.95;
    card(s, x, 5.2, 2.75, 1.1);
    text(s, h, { x: x + 0.2, y: 5.3, w: 2.4, h: 0.4, fontSize: 15, bold: true, color: GOLD });
    text(s, d, { x: x + 0.2, y: 5.72, w: 2.45, h: 0.5, fontSize: 12.5, color: MUTED });
  });
}

// ================================================================ 10 art direction
pres.addSection({ title: "美术与技术" });
{
  const s = content("美术：没有太阳，但夜晚是亮的、有颜色的", "美术与技术",
    "美术方向参考动画短片的夜景：一颗巨大的蓝色地球把岛染成银蓝，暗部是青与紫而不是黑，每章一套夜色。");
  const labels = ["序章", "第一章", "第二章", "幕间", "第三章", "终章", "尾声"];
  labels.forEach((l, i) => {
    const x = 0.9 + i * 1.68, w = 1.52;
    framedImage(s, img(`pal_${i + 1}.jpg`), x, 1.45, w, 2.15, { alt: l + "色调" });
    text(s, l, { x, y: 3.7, w, h: 0.35, fontSize: 14, bold: true, align: "center" });
  });
  const points = [
    ["每章一套夜色", "银蓝、蓝紫、冷蓝、最暗、乳白到清透、星河、最暖", C.accent5],
    ["大地球与地平线光带", "地球圆缺随长夜变化；海面云海与地光倒影", C.accent2],
    ["萤光与暖光", "人物边缘萤光；灯、窗、灯笼的暖色点缀", C.accent4],
  ];
  points.forEach(([h, d, color], i) => {
    const x = 0.9 + i * 3.95;
    dot(s, x, 4.45, 0.3, color);
    text(s, h, { x: x + 0.45, y: 4.38, w: 3.4, h: 0.42, fontSize: 17, bold: true });
    text(s, d, { x: x + 0.45, y: 4.85, w: 3.4, h: 0.85, fontSize: 13.5, color: MUTED });
  });
}

// ================================================================ 11 technical pipeline
{
  const s = content("技术实现：从生图到可玩的岛", "美术与技术",
    "资产流程：概念图 → Tripo 图生 3D → Blender 减面、定比例、定轴心 → Unity 自动摆放与适配。场景由编辑器脚本一键重建。");
  const flow = [
    ["生图", "AI 概念参考图"], ["Tripo", "图生 3D\n38 件道具 · 5 个角色"], ["Blender", "减面 · 比例 · 绑骨"],
    ["Unity 6", "URP 场景 · 着色器\n剧情与界面"], ["自动化 QA", "全流程通关\n性能 · 闪屏检测"],
  ];
  flow.forEach(([h, d], i) => {
    const x = 0.9 + i * 2.48, w = 2.1;
    card(s, x, 1.5, w, 1.75);
    text(s, h, { x: x + 0.15, y: 1.65, w: w - 0.3, h: 0.45, fontSize: 18, bold: true, color: GOLD, align: "center" });
    text(s, d, { x: x + 0.15, y: 2.15, w: w - 0.3, h: 1.0, fontSize: 13, color: INK, align: "center" });
    if (i < flow.length - 1)
      s.addShape(pres.shapes.RIGHT_ARROW, { x: x + w + 0.08, y: 2.2, w: 0.3, h: 0.32, fill: { color: GOLD }, line: { type: "none" }, objectName: name("arrow") });
  });
  const tech = [
    ["程序化海岸与草地", "外圈陡坡自动生成坡肩、草坡、沙滩与礁石"],
    ["自定义着色器", "夜空（地球、银河、云海）、海面倒影、人物萤光"],
    ["自适应分辨率", "集成显卡上自动调节渲染比例，保持流畅"],
    ["双端发布", "Windows 原生版 + WebGL 网页版"],
  ];
  tech.forEach(([h, d], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.9 + col * 3.15, y = 3.75 + row * 1.25;
    dot(s, x, y + 0.05, 0.26, [C.accent2, C.accent6, C.accent3, C.accent5][i]);
    text(s, h, { x: x + 0.4, y, w: 2.65, h: 0.4, fontSize: 15.5, bold: true });
    text(s, d, { x: x + 0.4, y: y + 0.42, w: 2.65, h: 0.75, fontSize: 12.5, color: MUTED });
  });
  framedImage(s, img("photo_06-sea-house.jpg"), 7.4, 3.75, 5.3, 2.5, { alt: "海面与地球" });
}

// ================================================================ 12 development & before/after
{
  const s = content("开发过程：人机协作，三轮迭代", "美术与技术",
    "作者负责原创文学故事、人物、调灯玩法规则与审美把关；AI 工具协助程序实现、模型处理、环境美术与展示材料（详见 AI 使用情况说明）。下方对比第二版与第三版的同一视角。");
  framedImage(s, V2_ISLAND, 0.9, 1.45, 5.6, 3.15, { alt: "第二版全岛" });
  framedImage(s, img("photo_01-island.jpg"), 6.9, 1.45, 5.6, 3.15, { alt: "第三版全岛" });
  text(s, "第二版：竖直暗色崖壁，整体偏暗", { x: 0.9, y: 4.7, w: 5.6, h: 0.35, fontSize: 13, color: MUTED });
  text(s, "第三版：自然海岸与沙滩，明亮有层次的夜色", { x: 6.9, y: 4.7, w: 5.6, h: 0.35, fontSize: 13, color: GOLD });
  const versions = [
    ["第一版", "按剧本重写；5 个角色绑骨与 25 个动作；核心玩法与流程"],
    ["第二版", "Tripo 道具全面替换；地形、草地、海与天空；绘本风 UI"],
    ["第三版", "海岸重塑、章节色调、开篇世界观、人物萤光、性能与闪屏修复"],
  ];
  versions.forEach(([h, d], i) => {
    const x = 0.9 + i * 3.95;
    text(s, h, { x, y: 5.25, w: 3.7, h: 0.4, fontSize: 16, bold: true, color: GOLD });
    text(s, d, { x, y: 5.65, w: 3.7, h: 0.75, fontSize: 13, color: MUTED });
  });
}

// ================================================================ 13 quality
{
  const s = content("质量保障：自动化验证", "美术与技术",
    "QA 机器人以真实按键从标题一路玩到尾声，记录截图、错误与每章帧时（区分 CPU 与 GPU）。另用录屏逐帧检测闪屏。");
  const stats = [["7 / 7", "章节自动通关\n从标题到尾声"], ["0", "运行时错误\n存档自动恢复"], ["150 秒", "逐帧录屏检测\n无画面缩小或空白帧"], ["47 张", "每轮自动截图\n用于逐章审图"]];
  stats.forEach(([n, label], i) => {
    const x = 0.9 + i * 3.0;
    card(s, x, 1.5, 2.75, 2.35);
    text(s, n, { x: x + 0.25, y: 1.65, w: 2.35, h: 1.0, fontSize: 40, bold: true, color: GOLD, valign: "middle" });
    text(s, label, { x: x + 0.25, y: 2.75, w: 2.35, h: 0.95, fontSize: 14, lineSpacingMultiple: 1.15 });
  });
  const notes = [
    "渲染开销逐项测试：泛光、阴影、点光、环境光遮蔽、海面、草地、天空分别对照，按 GPU 耗时取舍",
    "自适应分辨率：集成显卡上自动在 72%–100% 之间调节，界面始终保持原生清晰",
    "跨平台构建前强制确认目标平台，避免网页版着色器变体缺失",
  ];
  s.addText(notes.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < notes.length - 1 } })),
    { x: 0.9, y: 4.25, w: 6.3, h: 2.4, fontSize: 15, color: INK, paraSpaceAfter: 10, valign: "top", isTextBox: true, objectName: name("text") });
  framedImage(s, img("qa_montage.jpg"), 7.6, 4.2, 4.9, 2.45, { alt: "自动化 QA 每章截图" });
}

// ================================================================ 14 innovation, value, authorship
pres.addSection({ title: "总结" });
{
  const s = content("核心创新、应用价值与原创贡献", "总结",
    "三列分别回答：这个作品新在哪里、对谁有用、哪些是作者自己完成的。程序、模型处理等 AI 协助部分见 AI 使用情况说明。");
  const cols = [
    ["核心创新", C.accent1, [
      "玩法即主题：调灯谜题就是“把光照对地方”，光污染成为谜题规则",
      "科学设定入故事：以真实的“地光”现象和光污染问题构建世界观",
      "没有坏人的成长叙事：在互助中找到自己的价值",
    ]],
    ["应用价值", C.accent2, [
      "暗夜保护科普：在游戏中体会按需照明、减少光污染",
      "价值引领：以乡邮员、造林者、守岛人为原型，传递敬业、奉献与坚守",
      "适合青少年：20–30 分钟完整体验，可用于课堂与科普活动",
    ]],
    ["作者原创贡献", C.accent4, [
      "原创文学故事、世界观与五位人物",
      "调灯玩法规则与三章关卡设计",
      "美术方向与人物、道具设定",
      "参考图与模型筛选，多轮试玩取舍",
    ]],
  ];
  cols.forEach(([h, color, items], i) => {
    const x = 0.9 + i * 3.95;
    card(s, x, 1.45, 3.7, 4.2);
    dot(s, x + 0.3, 1.72, 0.32, color);
    text(s, h, { x: x + 0.78, y: 1.66, w: 2.7, h: 0.45, fontSize: 19, bold: true, color: GOLD, valign: "middle" });
    s.addText(items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })),
      { x: x + 0.3, y: 2.4, w: 3.15, h: 3.1, fontSize: 15, color: INK, paraSpaceAfter: 14, lineSpacingMultiple: 1.15, valign: "top", isTextBox: true, objectName: name("text") });
  });
  text(s, "程序实现、模型处理、音频与展示材料由 AI 工具协助完成，具体环节见《人工智能工具使用情况说明》。",
    { x: 0.9, y: 5.95, w: 11.6, h: 0.4, fontSize: 14, color: MUTED });
}

// ================================================================ 15 gallery
{
  const s = content("游戏画面", "总结", "实机截图，均来自当前版本（1920×1080）。");
  const shots = ["photo_01-island.jpg", "photo_02-house-window.jpg", "photo_04-village.jpg", "photo_05-pier.jpg", "qa_06-first-flower.jpg", "qa_03-window-lit-grandmother.jpg"];
  shots.forEach((f, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    framedImage(s, img(f), 0.9 + col * 3.95, 1.45 + row * 2.6, 3.7, 2.08, { alt: "游戏截图" });
  });
}

// ================================================================ 16 summary
{
  const s = content("总结与展望", "总结",
    "收尾：作品已完整可玩；下一步补充村民群像、宣传片音乐与网页版优化。最后回到主题。");
  card(s, 0.9, 1.45, 5.7, 3.6);
  text(s, "已经做到", { x: 1.2, y: 1.65, w: 5.2, h: 0.45, fontSize: 19, bold: true, color: GOLD });
  const done = ["完整剧情：开篇到尾声，约 20–30 分钟", "玩法与主题一致：把光照在需要的地方", "绘本风界面、章节色调与人物萤光", "Windows / WebGL 双端，自动化验证"];
  s.addText(done.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < done.length - 1 } })),
    { x: 1.2, y: 2.25, w: 5.2, h: 2.7, fontSize: 17, color: INK, paraSpaceAfter: 14, valign: "top", isTextBox: true, objectName: name("text") });
  card(s, 6.9, 1.45, 5.6, 3.6);
  text(s, "下一步", { x: 7.2, y: 1.65, w: 5.0, h: 0.45, fontSize: 19, bold: true, color: GOLD });
  const next = ["补充村民角色，丰富送行与尾声的群像", "更细腻的海岸、植被与近景材质", "宣传片配乐与镜头剪辑", "网页版在普通笔记本上的性能优化"];
  s.addText(next.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < next.length - 1 } })),
    { x: 7.2, y: 2.25, w: 5.0, h: 2.7, fontSize: 17, color: INK, paraSpaceAfter: 14, valign: "top", isTextBox: true, objectName: name("text") });
  s.addImage({ path: img("sparkle.png"), x: 0.9, y: 5.6, w: 0.4, h: 0.4, objectName: name("sparkle"), altText: "金色星点" });
  text(s, "愿每一个觉得自己不够亮的人，都能找到自己的光。", { x: 1.45, y: 5.57, w: 11.1, h: 0.5, fontSize: 20, color: INK, valign: "middle" });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})().catch(e => { console.error(e); process.exit(1); });
