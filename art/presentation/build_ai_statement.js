// 《借光岛》AI 使用说明 (.docx) — run with NODE_PATH pointing at a node_modules that has docx.
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, BorderStyle, LevelFormat, Footer, PageNumber, TableLayoutType,
} = require("docx");

const OUT = process.argv[2];
const BODY = "SimSun", HEAD = "Microsoft YaHei";
const INK = "1F2937", ACCENT = "8A5A00", LINE = "C9B98F", SHADE = "F3EEE2";
const PAGE_W = 11906, MARGIN = 1300, CONTENT_W = PAGE_W - MARGIN * 2; // A4

const run = (text, o = {}) => new TextRun({ text, font: o.font || BODY, size: o.size || 22, bold: o.bold, color: o.color || INK, italics: o.italics });
const p = (children, o = {}) => new Paragraph({
  children: Array.isArray(children) ? children : [run(children, o)],
  spacing: { before: o.before || 0, after: o.after ?? 120, line: o.line || 360 },
  alignment: o.align || AlignmentType.JUSTIFIED,
  indent: o.indent ? { firstLine: 440 } : undefined,
});
const h1 = text => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, font: HEAD, size: 30, bold: true, color: INK })],
  spacing: { before: 360, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 4 } },
});
const h2 = text => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, font: HEAD, size: 24, bold: true, color: ACCENT })],
  spacing: { before: 240, after: 100 },
});
const bullet = (parts, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  children: (Array.isArray(parts) ? parts : [parts]).map(x => typeof x === "string" ? run(x) : x),
  spacing: { after: 80, line: 340 },
});
const label = (a, b) => [run(a, { bold: true }), run(b)];

function table(headers, rows, widths) {
  const total = widths.reduce((s, w) => s + w, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (text, w, head) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders,
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: SHADE } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: (Array.isArray(text) ? text : [text]).map(t => new Paragraph({
      children: [run(t, { bold: head, font: head ? HEAD : BODY, size: head ? 21 : 20 })],
      spacing: { after: 40, line: 300 },
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, widths[i], false)) })),
    ],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 120 } });

const W2 = [2300, CONTENT_W - 2300];
const W3 = [2000, 3150, CONTENT_W - 5150];

const children = [
  new Paragraph({ children: [new TextRun({ text: "《借光岛》AI 使用说明", font: HEAD, size: 44, bold: true, color: INK })], alignment: AlignmentType.CENTER, spacing: { before: 200, after: 120 } }),
  new Paragraph({ children: [run("参赛作品 AI 工具使用情况披露", { size: 24, color: "6B7280" })], alignment: AlignmentType.CENTER, spacing: { after: 360 } }),
  table(["项目", "内容"], [
    ["作品名称", "《借光岛》"],
    ["作品类型", "原创剧情冒险游戏（三维场景 + 光线解谜）"],
    ["运行平台", "Windows（主要版本）、WebGL 网页版"],
    ["开发工具", "Unity 6（6000.3，URP）、Blender 4.5"],
    ["参赛者", "（请填写）"],
    ["说明日期", "2026 年 10 月 23 日"],
  ], W2),

  h1("一、总体声明"),
  p("《借光岛》的文学故事是本作品的核心内核，由作者原创。故事的主题“你不必是最亮的那一盏。借来的光照亮了别人，就成了自己的光”，“借光岛”的世界观，五位主要人物及其性格与经历，从序章到尾声的完整情节、关键台词与结局，以及“把光照在需要的地方”的玩法核心，均出自作者的独立构思。", { indent: true }),
  p("在把故事做成游戏的过程中，作者使用了多种人工智能（AI）工具，主要用于程序编写、三维素材的生成与处理、音频合成、测试构建以及展示材料的制作。这些 AI 工具均按照作者的原创设定和创作要求工作；创作方向、审美取舍和最终采用由作者决定。", { indent: true }),
  p("本说明如实列出 AI 参与的每一个环节、使用的工具与产出，不夸大，也不隐瞒。", { indent: true }),

  h1("二、作者原创与主导的内容"),
  table(["内容", "说明"], [
    ["文学故事与核心创意", ["主题、世界观（没有太阳的小星球、地球反射的“地光”、光树与光果、灯罩、长夜、每个人身上的萤光）、人物、情节、关键台词与结局。", "三位老人分别取材于乡邮员、塞罕坝造林者、海岛守岛人这三种平凡坚守的精神，人物均为虚构。"]],
    ["玩法设计核心", "三盏灯、宽窄两种灯罩、四个需要照亮的地方，以及“光污染会把夜空照白、每晚只允许一份光漏向天空”的规则，与故事主题一一对应。"],
    ["创作方向与审美把关", "确定对标作品的质感目标；否定不满意的人物形象与画面版本并要求重做；在多个剧本版本中选定最终版本；提出删除副标题等修改。"],
    ["美术素材的生成操作", "依据原创人物与道具设定，使用 AI 生图工具生成人物四视图和道具参考图，并在 Tripo 中完成图生三维模型。"],
    ["试玩、反馈与最终取舍", "多轮试玩，指出闪屏、画面偏暗、海岸生硬、故事设定交代不清等问题，决定修改优先级和提交内容。"],
  ], W2),

  h1("三、使用的 AI 工具"),
  table(["工具", "提供方", "主要用途"], [
    ["Claude Opus 5.5（Claude Code 编程代理）", "Anthropic", "游戏核心程序（剧情流程、界面、镜头、调灯谜题、存档）；夜空、海面、人物萤光等着色器；角色自动绑骨与模型处理脚本；第三版画面优化；生图与建模提示词整理；开篇介绍与尾声补充台词的扩写；自动化测试、评审视频录制工具、汇报 PPT 与说明文档。"],
    ["GPT（Codex 编程代理）", "OpenAI", "第一、二版环境搭建（岛屿地形、地表、植被、海面与灯光）；程序合成音效与配乐的脚本；自动化测试与打包脚本。"],
    ["GPT 图像生成", "OpenAI", "作者依据原创设定生成五位人物的四视图，以及房屋、灯具、栈桥、树木、岩石、船只等道具与场景参考图。"],
    ["Tripo（图生三维）", "VAST（Tripo AI）", "作者把参考图生成为三维模型：5 个角色、38 件道具与建筑。"],
  ], W3),
  gap(),
  p([run("非 AI 工具与素材：", { bold: true }), run("Unity 6 游戏引擎、Blender 4.5 三维软件；Adobe Mixamo 动作库（动作捕捉动作，可免费用于个人与商业项目，非生成式 AI）；思源宋体 Noto Serif SC 字体（SIL Open Font License 1.1）。")]),

  h1("四、各环节 AI 使用详情"),
  h2("4.1 文学剧本与游戏文本"),
  bullet(label("原创部分：", "故事主体（主题、世界观、人物、情节、关键台词、结局）由作者原创，见第二节。")),
  bullet(label("AI 整理：", "在作者原创故事的基础上，AI 协助把剧本整理成游戏可用的格式，包括分章、对白分行、旁白卡片、章节标题与任务提示。")),
  bullet(label("AI 扩写：", "第三版新增的“开篇”11 段世界观与人物介绍文字、尾声四位人物的补充台词、评审视频中的玩法说明字幕，由 AI 依据作者原创的世界观与人物设定扩写，经作者审定后采用，不改变原作的情节与人物。")),

  h2("4.2 美术与三维素材"),
  bullet(label("人物：", "作者使用 AI 生图工具依据人物设定生成五位人物的四视图，再用 Tripo 生成三维模型；随后由 AI 编写的 Blender 脚本完成减面、骨骼绑定与蒙皮权重，并接入 Mixamo 动作库中的 25 个动作。")),
  bullet(label("道具与建筑：", "作者依据提示词生成参考图，在 Tripo 中生成 38 件模型；AI 编写的 Blender 脚本统一减面、换算真实尺寸与处理贴图，AI 编写的 Unity 编辑器脚本把模型摆放进场景。")),
  bullet(label("环境：", "岛屿地形、海岸坡地、地表材质、草地与野花、夜空与地球、海面均由 AI 编写的程序和着色器生成，属于程序化生成，没有使用第三方图片素材。")),
  bullet(label("界面：", "标题页、旅程地图、章节卡、对白框等界面图形（羊皮纸、星点、金线）由程序生成；界面字体为思源宋体。")),
  bullet(label("视觉参考：", "开发中参考了 littleprince.dev 等作品的画面质感，参考截图只用于对比，没有用作游戏素材。")),

  h2("4.3 程序"),
  bullet("全部 C# 程序与着色器由 AI 编程代理（Claude、GPT）按作者的需求编写；作者提出功能与修改要求，并通过试玩进行验收。"),
  bullet("主要模块：剧情导演与章节流程、调灯谜题规则、界面系统、镜头、人物萤光、夜空与章节色调、海面、海岸生成、自适应分辨率、自动化测试。"),

  h2("4.4 音频"),
  bullet("海浪、风声、夜虫等环境音，主题配乐与交互音效，由 AI 编写的 Python 程序合成，属于确定性的程序合成，没有使用外部录音或第三方音乐。"),
  bullet("作品评审视频的配乐由上述游戏内配乐与环境音混合而成。"),

  h2("4.5 测试、构建与打包"),
  bullet("AI 编写自动化测试程序，用真实按键从标题一路玩到尾声，记录截图、运行错误与帧率；另用逐帧录屏检测闪屏。"),
  bullet("Windows 版与网页版的构建与打包由 AI 完成，作者负责试玩与最终确认。"),

  h2("4.6 展示材料"),
  bullet(label("作品截图：", "均为游戏实机画面，由 AI 编写的录制工具在 1920×1080 分辨率下截取，未经 AI 修图。")),
  bullet(label("作品评审视频：", "游戏实机录制，由 AI 编写的展示程序自动游玩并添加说明字幕，没有使用 AI 生成的视频画面。")),
  bullet(label("汇报 PPT：", "由 AI 依据作品内容与实机截图制作，作者审定。")),
  bullet(label("本说明：", "由 AI 依据开发记录起草，作者审定。")),

  h1("五、人机分工一览"),
  table(["环节", "作者", "AI"], [
    ["文学故事", "原创全部故事、人物、主题与关键台词", "整理为游戏文本；扩写开篇介绍与尾声补充台词"],
    ["玩法", "设计三盏灯、宽窄灯罩与光污染规则", "用程序实现规则与调灯界面"],
    ["人物", "人物设定；生成四视图；在 Tripo 中建模", "绑骨、蒙皮、接入动作、萤光效果"],
    ["场景与道具", "生成参考图；在 Tripo 中建模；审美取舍", "模型处理与摆放；地形、海岸、天空、海面、植被"],
    ["程序", "提出需求、试玩验收", "编写全部代码与着色器"],
    ["音频", "确认风格与使用", "程序合成"],
    ["展示材料", "审定并提交", "录制视频、截取截图、制作 PPT 与说明文档"],
  ], W3),

  h1("六、素材来源与版权"),
  bullet("游戏中没有使用第三方受版权保护的图片、模型、音乐或录音。"),
  bullet("三维模型由作者使用 Tripo、依据自己生成的参考图生成。"),
  bullet("角色动作来自 Adobe Mixamo 动作库，按其使用条款用于本作品。"),
  bullet("字体为思源宋体 Noto Serif SC，采用 SIL Open Font License 1.1，许可文件随游戏附带。"),
  bullet("音频为程序合成的原创内容，界面图形为程序生成。"),

  h1("七、AI 生成内容的审核与把关"),
  bullet("每一个版本都经过实机截图审查和自动化全流程测试。"),
  bullet("作者否定了不满意的 AI 产出并要求重做，例如早期的人物形象、偏暗的画面和像“蛋糕”一样的竖直崖壁。"),
  bullet("文本、画面与玩法的最终采用，由作者决定。"),

  h1("八、声明"),
  p("本说明所述 AI 使用情况真实、完整。《借光岛》的文学故事与核心创意为作者原创；AI 工具在作者的创作意图与审定下，提供程序、素材制作与展示方面的辅助。", { indent: true }),
  new Paragraph({ children: [run("参赛者签名：＿＿＿＿＿＿＿＿　　　日期：2026 年 10 月 23 日")], spacing: { before: 480, after: 120 }, alignment: AlignmentType.RIGHT }),
];

const doc = new Document({
  creator: "借光岛",
  title: "《借光岛》AI 使用说明",
  styles: { default: { document: { run: { font: BODY, size: 22, color: INK } } } },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 260 } } } }],
    }],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1300, bottom: 1300, left: MARGIN, right: MARGIN } } },
    footers: {
      default: new Footer({
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "《借光岛》AI 使用说明　第 ", font: BODY, size: 18, color: "6B7280" }),
          new TextRun({ children: [PageNumber.CURRENT], font: BODY, size: 18, color: "6B7280" }),
          new TextRun({ text: " 页", font: BODY, size: 18, color: "6B7280" }),
        ] })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });
