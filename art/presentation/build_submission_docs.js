// 参赛打包文件中的文字材料：AI 使用情况说明（官方模板结构，.docx + .pdf）、作品介绍文档、
// 运行说明、第三方资源说明（.pdf）。全部匿名，不含学校、成员与指导教师信息。
// NODE_PATH 需包含 docx；PDF 用 Playwright + Edge 无头打印。
const fs = require("fs"), path = require("path");
const D = require("docx");
const { chromium } = require("C:/Users/20665/AppData/Local/OpenAI/Codex/runtimes/cua_node/78fb63cda1a9e2b2/bin/node_modules/playwright");
const OUT = process.argv[2];

// ---------------------------------------------------------------- content
// blocks: ["h1", text] ["h2", text] ["p", text] ["ul", [items]] ["table", headers, rows, widths%] ["note", text]
const AI = {
  title: "人工智能工具使用情况说明",
  subtitle: "2026 年第十四届全国大学生数字媒体科技作品及创意竞赛 · 参赛作品《借光岛》",
  blocks: [
    ["h1", "一、作品基本信息与 AI 使用状态"],
    ["table", ["项目", "填写内容"], [
      ["作品名称", "《借光岛》"],
      ["作品编号（如有）", "（以报名系统为准）"],
      ["参赛赛道／赛项", "（以报名系统为准）"],
      ["AI 使用情况", "■ 已使用"],
    ], [30, 70]],
    ["note", "作品的文学故事（主题、世界观、人物、情节、关键台词与结局）与“把光照在需要的地方”的玩法核心为学生原创；AI 工具用于程序编写、三维素材生成与处理、音频合成、测试构建和展示材料制作。"],

    ["h1", "二、主要 AI 工具及使用情况"],
    ["table", ["工具／模型", "使用环节", "AI 主要用途或产出", "学生后续处理"], [
      ["Claude Opus 5.5（Anthropic，Claude Code 编程代理）", "程序开发、角色处理、画面优化、展示材料", "Unity 游戏程序（剧情流程、界面、镜头、调灯谜题、存档）、夜空／海面／人物萤光着色器、角色绑骨与模型处理脚本、开篇介绍与尾声补充台词的扩写、自动化测试、评审视频录制工具与汇报 PPT", "提出功能与修改需求；试玩反馈；否定不满意的版本并要求重做；审定文字与画面"],
      ["GPT（OpenAI，Codex 编程代理）", "环境搭建、音频、测试打包", "第一、二版岛屿地形、地表、植被、海面与灯光；程序合成的环境音、配乐与音效；测试与打包脚本", "确定环境风格与质感目标；试玩反馈并要求修改"],
      ["GPT 图像生成（OpenAI）", "美术参考图", "依据学生撰写的人物与道具设定生成五位人物四视图、道具与场景参考图", "撰写设定与提示要求；筛选可用图片；不满意的重新生成"],
      ["Tripo（VAST，图生三维）", "三维建模", "由参考图生成 5 个角色、38 件道具与建筑的三维模型", "筛选模型（剔除悬空、破碎的结果），送入后续处理流程"],
    ], [20, 16, 38, 26]],

    ["h1", "三、代表性 AI 使用过程"],
    ["h2", "环节 1：人物从设定到可动的三维角色"],
    ["table", ["说明项目", "具体内容"], [
      ["使用环节及目的", "把原创人物（小灯笼、阿萤、阿婆、邮差爷爷、灯伯）做成可在游戏中行走、交谈的三维角色"],
      ["主要工具／模型", "GPT 图像生成、Tripo 图生三维、Claude（编写 Blender 绑骨脚本）"],
      ["主要输入或素材来源", "学生撰写的人物外貌与性格设定（见剧本“人物”一节）"],
      ["AI 主要输出", "人物四视图 → 三维模型 → 骨骼与蒙皮权重；接入 Mixamo 动作库的 25 个动作"],
      ["学生筛选、修改或再创作", "依据设定筛选四视图与模型；否定早期不满意的人物形象并要求重做；检查举手、弯腿、转身等动作的变形问题"],
      ["最终成果中的应用位置", "游戏全部章节中的五位人物；开篇人物介绍镜头"],
      ["可核验材料（如有）", "绑骨脚本 art/blender/rig_characters_v1.py；角色模型 art/generated/characters-v1/"],
    ], [28, 72]],
    ["h2", "环节 2：把原创故事做成可玩的游戏程序"],
    ["table", ["说明项目", "具体内容"], [
      ["使用环节及目的", "实现章节流程、对白、调灯谜题、界面与画面效果"],
      ["主要工具／模型", "Claude Code（Claude Opus 5.5）、GPT（Codex）编程代理"],
      ["主要输入或素材来源", "学生原创剧本《借光岛》（序章至尾声）、玩法规则（三盏灯、宽窄灯罩、四个照明目标、光污染限制）"],
      ["AI 主要输出", "Unity C# 程序与着色器；剧本被整理为分章对白、旁白卡片与任务提示"],
      ["学生筛选、修改或再创作", "多轮试玩并提出问题（闪屏、画面偏暗、海岸生硬、故事设定交代不清等）；决定修改优先级与最终采用版本"],
      ["最终成果中的应用位置", "整个可运行程序（Windows 版与网页版）"],
      ["可核验材料（如有）", "工程目录 GameProject/Assets/JieGuang/；自动化测试截图与报告"],
    ], [28, 72]],
    ["h2", "环节 3：开篇世界观介绍与展示材料"],
    ["table", ["说明项目", "具体内容"], [
      ["使用环节及目的", "在序章前讲清作品设定；制作评审视频、截图与汇报 PPT"],
      ["主要工具／模型", "Claude Code（Claude Opus 5.5）"],
      ["主要输入或素材来源", "学生原创的世界观与人物设定"],
      ["AI 主要输出", "11 段开篇介绍文字与镜头；尾声人物补充台词；游戏实机录制的评审视频、1080p 截图、汇报 PPT"],
      ["学生筛选、修改或再创作", "审定开篇与台词内容，确认不改变原作情节与人物；选定提交的视频与截图"],
      ["最终成果中的应用位置", "游戏开篇、尾声；作品评审视频、作品截图、作品汇报 PPT"],
      ["可核验材料（如有）", "文本 GameProject/Assets/JieGuang/Scripts/Core/StoryText.cs"],
    ], [28, 72]],

    ["h1", "四、最终成果中的 AI 生成或辅助内容"],
    ["table", ["内容／成果", "AI 生成或辅助部分", "学生修改与整合", "最终使用位置"], [
      ["三维模型", "Tripo 依据参考图生成角色与道具模型", "筛选；按设定摆放与取舍", "游戏场景全部角色、建筑、道具"],
      ["程序与着色器", "AI 编程代理编写", "需求设计、试玩验收、版本取舍", "整个游戏程序"],
      ["环境与画面", "程序化生成的地形、海岸、草地、夜空、海面", "确定美术方向与每章色调目标", "游戏全部场景"],
      ["音频", "AI 编写的程序合成环境音、配乐与音效（无外部录音）", "确认风格与使用位置", "游戏环境音、配乐；视频配乐"],
      ["游戏文字", "整理剧本为游戏格式；扩写开篇介绍与尾声补充台词", "原创故事主体；审定扩写内容", "全部章节对白、开篇、尾声"],
      ["展示材料", "实机录制视频、截图与 PPT 由 AI 工具制作", "审定并选择提交内容", "评审视频、作品截图、汇报 PPT"],
    ], [16, 32, 26, 26]],

    ["h1", "五、学生原创贡献说明"],
    ["p", "学生自主完成的核心工作："],
    ["ul", [
      "原创文学故事：主题“你不必是最亮的那一盏。借来的光照亮了别人，就成了自己的光”；“借光岛”世界观（没有太阳的星球、地光、光树与光果、灯罩、长夜、萤光）；五位人物；序章至尾声的情节、关键台词与结局。三位老人分别取材于乡邮员、塞罕坝造林者、海岛守岛人的平凡坚守精神（人物均为虚构）。",
      "玩法设计：三盏灯、宽窄灯罩、四个照明目标与“每晚只允许一份光漏向天空”的光污染规则，与故事主题对应。",
      "美术方向与审美把关：确定对标作品与质感目标；撰写人物与道具设定，生成参考图并完成图生三维；否定不满意的版本并要求重做。",
      "测试与取舍：多轮试玩、指出问题、决定修改优先级与最终提交内容。",
    ]],
    ["p", "AI 与学生工作边界说明："],
    ["ul", [
      "故事的主题、核心情节、人物关系与结局由学生构思；AI 只在学生设定的基础上做格式整理和少量扩写（开篇介绍、尾声补充台词、视频字幕），不改变原作情节与人物。",
      "程序、着色器、绑骨脚本由 AI 编程代理按学生需求编写；需求、验收与取舍由学生完成。",
    ]],

    ["h1", "六、代表性过程材料"],
    ["p", "工程中保留了主要过程材料，可按需核验：人物与道具生图提示词（art/design/v2/、art/design/v3/）、模型处理记录（art/generated/props-v2/ 各目录 record.json）、各版本实机截图与自动化测试报告（art/verification/）。不提交全部对话记录。"],

    ["h1", "七、资源来源与合规说明"],
    ["p", "第三方资源（游戏引擎、动作库、字体、AI 平台）的名称、来源、用途与授权情况见同包内《第三方资源说明》。游戏中没有使用第三方受版权保护的图片、模型、音乐或录音；AI 生成的三维模型与音频均经学生筛选审核后使用，没有使用第三方素材作为 AI 生成的输入。"],

    ["h1", "八、填写确认"],
    ["p", "本说明真实反映 AI 工具使用情况、学生自主工作与最终成果状态。相关真实性、原创性及知识产权承诺按本届统一《参赛承诺书》执行。"],
  ],
};

const INTRO = {
  title: "作品介绍文档",
  subtitle: "《借光岛》· 原创剧情冒险游戏",
  blocks: [
    ["h1", "一、项目定位"],
    ["p", "《借光岛》是一款三维剧情冒险游戏。在一颗没有太阳的小星球上，人们借地球反射的“地光”生活；每年一次的“长夜”里，不会发光的少年“小灯笼”替出海采光的朋友阿萤守护岬角的三盏灯。玩家调整灯头方向与灯罩宽窄，把有限的光照在需要的地方：照亮回家的小路、阿婆的圆窗、等船归来的码头，同时避免光污染把夜空照白、让海上的人看不见星星回家。"],
    ["p", "作品面向青少年与大众玩家，表达“你不必是最亮的那一盏，借来的光照亮了别人，就成了自己的光”的主题。三位老人取材于乡邮员、塞罕坝造林者、海岛守岛人的平凡坚守精神，传递敬业、奉献与坚守。"],
    ["h1", "二、主要创新"],
    ["ul", [
      "玩法与主题同构：调灯谜题本身就是“把光照对地方”，宽灯罩与照向天空的光会造成光污染，每晚只允许一份光漏向天空。",
      "科学设定入故事：以真实的“地照”现象和光污染问题为依据，构建“借光生活”的世界观。",
      "没有坏人的成长叙事：以友善与互助中的自我认同为主线，七个章节逐步展开，终章主角第一次看见自己的光。",
    ]],
    ["h1", "三、技术或创作实现"],
    ["ul", [
      "引擎与平台：Unity 6（URP），Windows 原生版与 WebGL 网页版。",
      "资产流程：人物与道具设定 → AI 生成参考图 → Tripo 图生三维 → Blender 处理（减面、比例、绑骨）→ Unity 自动摆放。",
      "画面：程序化海岸与草地、自定义夜空（地球、银河、云海）、海面倒影与人物萤光着色器，每章一套夜色。",
      "流程：开篇世界观介绍（11 段镜头）→ 序章 → 三章 → 幕间 → 终章 → 尾声；旅程地图与章节卡串联。",
      "质量保障：自动化测试以真实按键从标题玩到尾声，记录截图、错误与帧率；集成显卡上自适应分辨率。",
    ]],
    ["h1", "四、成果状态"],
    ["table", ["状态", "内容"], [
      ["已完成", "完整剧情（开篇至尾声，约 20–30 分钟）；三个调灯关卡；五位人物；Windows 版七章自动流程通过测试；网页版可运行至序章开头并已打包"],
      ["正在完善", "部分海岸近景、植被细节；集成显卡上的稳定 60 帧"],
      ["后续计划", "村民群像、配乐与配音、网页版性能优化"],
    ], [20, 80]],
    ["h1", "五、团队分工与原创贡献"],
    ["table", ["成员", "主要工作", "实际完成成果"], [
      ["成员 A", "文学故事、玩法设计、美术方向", "原创剧本与人物、调灯规则、参考图与三维模型筛选、试玩与取舍"],
      ["AI 工具", "程序、素材处理、展示材料（详见 AI 使用情况说明）", "游戏程序与着色器、绑骨与模型处理、音频合成、视频与 PPT"],
    ], [18, 36, 46]],
    ["h1", "六、应用价值"],
    ["ul", [
      "暗夜保护科普：玩家在解谜中体会“按需照明、减少光污染”，理解保护星空不是不用灯，而是把光照对地方。",
      "价值引领：以乡邮员、塞罕坝造林者、海岛守岛人为原型，用没有说教的故事传递敬业、奉献与坚守。",
      "面向青少年与大众：20–30 分钟可完整体验，操作简单，Windows 离线版与网页版均可运行，适合课堂、科普活动与展览场景。",
    ]],
  ],
};

const RUN = {
  title: "运行说明",
  subtitle: "《借光岛》",
  blocks: [
    ["h1", "一、Windows 版（推荐）"],
    ["ul", ["解压参赛打包文件，进入“01_作品及成果文件/借光岛_Windows”文件夹。", "双击 JieGuang.exe 运行，无需安装；默认 1600×900 窗口，Alt+Enter 切换全屏。", "运行环境：Windows 10/11 64 位；支持 DirectX 11 的显卡（集成显卡可运行，游戏自动调节渲染分辨率）；内存 8GB 以上。"]],
    ["h1", "二、网页版（可选）"],
    ["ul", ["进入“01_作品及成果文件/借光岛_WebGL”文件夹，双击 Open-Web.cmd（需已安装 Node.js），浏览器会打开本机地址。", "不要直接双击 index.html；首次进入请点击“开始旅程”，以获得键盘焦点并播放声音。"]],
    ["h1", "三、操作"],
    ["table", ["按键", "作用"], [
      ["点击 / Enter", "开始旅程；在旅程地图上进入章节"],
      ["WASD / 方向键；左 Shift", "移动；跑动"],
      ["鼠标右键拖动；滚轮", "转动视角；拉近拉远"],
      ["E", "与附近的人或物交互"],
      ["空格 / Enter", "继续对白"],
      ["Tab", "跳过开篇介绍；需要调灯时打开调灯面板"],
      ["调灯面板", "数字键 1/2/3 选灯，A/D 转动灯头，空格切换宽、窄灯罩，Enter 确认"],
      ["Esc", "暂停（继续游戏、回到地图、回到标题、清除进度）"],
    ], [34, 66]],
    ["h1", "四、有效测试方式"],
    ["p", "启动后点击“开始旅程”，在旅程地图按 Enter 进入序章，按提示依次完成各章；全流程约 20–30 分钟。"],
  ],
};

const THIRD = {
  title: "第三方资源说明",
  subtitle: "《借光岛》",
  blocks: [
    ["table", ["资源名称", "类型", "来源", "用途", "授权或许可"], [
      ["Unity 6（6000.3）及 URP", "游戏引擎", "Unity Technologies", "游戏开发与发布", "Unity 个人版许可"],
      ["Input System 1.20.1", "引擎插件", "Unity 官方包", "键盘、鼠标、手柄输入", "Unity Companion License"],
      ["Blender 4.5", "三维软件", "Blender Foundation", "模型处理、绑骨", "GNU GPL（软件本身，产出归使用者）"],
      ["Mixamo 动作库（25 个动作）", "动作数据", "Adobe Mixamo", "人物行走、交谈等动作", "Adobe 条款：可免费用于个人与商业项目"],
      ["思源宋体 Noto Serif SC", "字体", "Google / Adobe", "界面与字幕文字", "SIL Open Font License 1.1（许可随游戏附带）"],
      ["Tripo（图生三维）", "AI 平台服务", "VAST（Tripo AI）", "生成角色与道具三维模型", "按平台用户协议使用，详见 AI 使用情况说明"],
      ["GPT 图像生成", "AI 平台服务", "OpenAI", "生成人物与道具参考图（不直接用于游戏画面）", "按平台用户协议使用"],
    ], [24, 12, 18, 22, 24]],
    ["p", "游戏中的图片、音乐、音效均为程序生成或 AI 程序合成的原创内容，没有使用第三方受版权保护的图片、音乐或录音。"],
  ],
};

// ---------------------------------------------------------------- HTML → PDF
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
function html(doc) {
  const body = doc.blocks.map(b => {
    if (b[0] === "h1") return `<h1>${esc(b[1])}</h1>`;
    if (b[0] === "h2") return `<h2>${esc(b[1])}</h2>`;
    if (b[0] === "p") return `<p>${esc(b[1])}</p>`;
    if (b[0] === "note") return `<p class="note">${esc(b[1])}</p>`;
    if (b[0] === "ul") return `<ul>${b[1].map(i => `<li>${esc(i)}</li>`).join("")}</ul>`;
    const [, head, rows, w] = b;
    return `<table><colgroup>${w.map(x => `<col style="width:${x}%">`).join("")}</colgroup><tr>${head.map(h => `<th>${esc(h)}</th>`).join("")}</tr>${rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</table>`;
  }).join("\n");
  return `<!doctype html><meta charset="utf-8"><style>
  body{font-family:"SimSun","Songti SC",serif;font-size:10.5pt;line-height:1.75;color:#111}
  .t{text-align:center;font-family:"Microsoft YaHei",sans-serif;font-size:18pt;font-weight:bold;margin:0 0 4px}
  .s{text-align:center;color:#555;margin:0 0 18px}
  h1{font-family:"Microsoft YaHei",sans-serif;font-size:13pt;margin:16px 0 6px}
  h2{font-family:"Microsoft YaHei",sans-serif;font-size:11pt;margin:12px 0 4px}
  p{margin:4px 0;text-indent:2em} .note{text-indent:0;color:#333;background:#f4f1e8;padding:6px 10px}
  ul{margin:4px 0 4px 1.4em;padding:0} li{margin:2px 0}
  table{border-collapse:collapse;width:100%;margin:6px 0;table-layout:fixed}
  th,td{border:1px solid #888;padding:4px 6px;vertical-align:top;font-size:9.5pt;word-break:break-all}
  th{background:#eee;font-family:"Microsoft YaHei",sans-serif}
  </style><div class="t">${esc(doc.title)}</div><div class="s">${esc(doc.subtitle)}</div>${body}`;
}

// ---------------------------------------------------------------- docx (AI statement)
function docx(doc) {
  const run = (t, o = {}) => new D.TextRun({ text: t, font: o.font || "SimSun", size: o.size || 21, bold: o.bold, color: o.color });
  const W = 9300;
  const kids = [
    new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { after: 80 }, children: [run(doc.title, { font: "Microsoft YaHei", size: 34, bold: true })] }),
    new D.Paragraph({ alignment: D.AlignmentType.CENTER, spacing: { after: 280 }, children: [run(doc.subtitle, { color: "555555" })] }),
  ];
  const border = { style: D.BorderStyle.SINGLE, size: 4, color: "888888" };
  for (const b of doc.blocks) {
    if (b[0] === "h1") kids.push(new D.Paragraph({ heading: D.HeadingLevel.HEADING_1, spacing: { before: 240, after: 100 }, children: [run(b[1], { font: "Microsoft YaHei", size: 26, bold: true })] }));
    else if (b[0] === "h2") kids.push(new D.Paragraph({ heading: D.HeadingLevel.HEADING_2, spacing: { before: 160, after: 80 }, children: [run(b[1], { font: "Microsoft YaHei", size: 22, bold: true })] }));
    else if (b[0] === "p" || b[0] === "note") kids.push(new D.Paragraph({ spacing: { after: 80, line: 340 }, indent: b[0] === "p" ? { firstLine: 420 } : undefined, children: [run(b[1])] }));
    else if (b[0] === "ul") for (const i of b[1]) kids.push(new D.Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 60, line: 320 }, children: [run(i)] }));
    else {
      const [, head, rows, pct] = b;
      const widths = pct.map(x => Math.round(W * x / 100)); widths[widths.length - 1] += W - widths.reduce((a, c) => a + c, 0);
      const cell = (t, i, h) => new D.TableCell({ width: { size: widths[i], type: D.WidthType.DXA }, borders: { top: border, bottom: border, left: border, right: border },
        shading: h ? { type: D.ShadingType.CLEAR, color: "auto", fill: "EEEEEE" } : undefined, margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: [new D.Paragraph({ spacing: { line: 300 }, children: [run(t, { size: 19, bold: h, font: h ? "Microsoft YaHei" : "SimSun" })] })] });
      kids.push(new D.Table({ width: { size: W, type: D.WidthType.DXA }, columnWidths: widths, layout: D.TableLayoutType.FIXED,
        rows: [new D.TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) }), ...rows.map(r => new D.TableRow({ children: r.map((c, i) => cell(c, i, false)) }))] }));
      kids.push(new D.Paragraph({ children: [], spacing: { after: 60 } }));
    }
  }
  return new D.Document({
    styles: { default: { document: { run: { font: "SimSun", size: 21 } } } },
    numbering: { config: [{ reference: "b", levels: [{ level: 0, format: D.LevelFormat.BULLET, text: "•", alignment: D.AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 260 } } } }] }] },
    sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1300, right: 1300 } } }, children: kids }],
  });
}

(async () => {
  const dir = n => { const p = path.join(OUT, n); fs.mkdirSync(p, { recursive: true }); return p; };
  const docs = [
    [AI, dir("07_AI工具使用补充说明"), "借光岛_人工智能工具使用情况说明"],
    [INTRO, dir("03_作品介绍文档"), "借光岛_作品介绍文档"],
    [RUN, dir("04_运行或使用说明"), "借光岛_运行说明"],
    [THIRD, dir("06_第三方资源说明"), "借光岛_第三方资源说明"],
  ];
  fs.writeFileSync(path.join(OUT, "07_AI工具使用补充说明", "借光岛_人工智能工具使用情况说明.docx"), await D.Packer.toBuffer(docx(AI)));
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage();
  for (const [doc, folder, name] of docs) {
    await page.setContent(html(doc), { waitUntil: "load" });
    await page.pdf({ path: path.join(folder, name + ".pdf"), format: "A4", margin: { top: "18mm", bottom: "18mm", left: "18mm", right: "18mm" }, printBackground: true,
      displayHeaderFooter: true, headerTemplate: "<span></span>", footerTemplate: '<div style="width:100%;text-align:center;font-size:8pt;color:#777">第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</div>' });
    console.log("pdf", name);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
