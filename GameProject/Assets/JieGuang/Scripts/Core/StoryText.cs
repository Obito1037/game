namespace JieGuang
{
    public enum Speaker { Narrator, Player, AYing, Postman, ABo, DengBo, Villager, Child }

    public struct Line
    {
        public Speaker Who;
        public string Text;
        public Line(Speaker who, string text) { Who = who; Text = text; }
    }

    // All story text, taken from art/design/script/07_完整故事与生图提示词（最终版）.md.
    public static class StoryText
    {
        public const string GameTitle = "借光岛";
        public const string Theme = "你不必是最亮的那一盏。\n借来的光照亮了别人，就成了自己的光。";

        public static string Name(Speaker s)
        {
            switch (s)
            {
                case Speaker.Player: return "小灯笼";
                case Speaker.AYing: return "阿萤";
                case Speaker.Postman: return "邮差爷爷";
                case Speaker.ABo: return "阿婆";
                case Speaker.DengBo: return "灯伯";
                case Speaker.Villager: return "村里的大人";
                case Speaker.Child: return "孩子";
                default: return "";
            }
        }

        static Line N(string t) => new Line(Speaker.Narrator, t);
        static Line P(string t) => new Line(Speaker.Player, t);
        static Line Y(string t) => new Line(Speaker.AYing, t);
        static Line M(string t) => new Line(Speaker.Postman, t);
        static Line B(string t) => new Line(Speaker.ABo, t);
        static Line D(string t) => new Line(Speaker.DengBo, t);

        // ---------- 开篇 · 借光岛（世界观介绍，序章之前播放，可按 Tab 跳过） ----------
        public enum IntroShot { Planet, Earth, LightTree, Lamp, LongNight, Glow, AYing, ABo, Postman, DengBo, Boy }
        public struct IntroBeat
        {
            public IntroShot Shot;
            public string Heading, Body;
            public IntroBeat(IntroShot shot, string heading, string body) { Shot = shot; Heading = heading; Body = body; }
        }
        public static readonly IntroBeat[] Intro =
        {
            new IntroBeat(IntroShot.Planet, "很远很远的地方",
                "宇宙很深的地方，有一颗很小很小的星球。它大半是海，海上只有一座岛。\n太阳离这里太远了，阳光从来没有到过这里。"),
            new IntroBeat(IntroShot.Earth, "地  光",
                "可这里的夜空并不黑。天上最亮的，是一颗蓝色的星——地球。\n地球把太阳的光反射过来，薄薄地落在岛上，像一层很淡的霜。\n岛上的人把这点光叫作“地光”，把自己的家，叫作借光岛。"),
            new IntroBeat(IntroShot.LightTree, "光树与光果",
                "地光太薄，留不住。岛上的人就种树。\n光树的叶子接住地光，一点一点存进会发光的果子里，人们叫它“光果”。\n岛上所有的灯，烧的都是光果。"),
            new IntroBeat(IntroShot.Lamp, "灯  罩",
                "借来的光很少，一点也浪费不得。照向天空的光会散回太空，还会把夜空照白。\n出海的人是靠星星和地球认路的。夜空一白，他们就找不到回家的方向。\n所以岛上的每一盏灯都戴着铜灯罩。老人们说：光，要照在需要的地方。"),
            new IntroBeat(IntroShot.LongNight, "长  夜",
                "每年有一次，地球会在天上慢慢缩成一道细线，地光几乎消失。这就是长夜。\n长夜之前，采光船要出海，去远方的采光站，把一船光果运回来。\n长夜里，岛上的灯，要有人守着。"),
            new IntroBeat(IntroShot.Glow, "萤  光",
                "岛上的人，皮肤和衣服的边上都有一层淡淡的萤光，像萤火虫，每个人的颜色都不一样。\n走夜路时，远远看见一团微光，就知道是谁来了。\n老人们常说：“光是给出去，才长出来的。”孩子们只当它是一句老话。"),
            new IntroBeat(IntroShot.AYing, "阿  萤",
                "十三岁，全岛最亮的孩子，萤光绿里带金。聪明，勇敢，人人都喜欢她。\n今年，她第一次跟着采光船出海。没有人知道，她其实很怕黑。"),
            new IntroBeat(IntroShot.ABo, "阿  婆",
                "岬角的守夜人。年轻时，她和伙伴们一筐一筐从海边背土，在光秃秃的石头上种下了岛上第一片光树。\n今年，她的萤光淡得快要看不见了。"),
            new IntroBeat(IntroShot.Postman, "邮差爷爷",
                "七十多岁，送了一辈子信。每天沿着环岛小路走一圈，邮包上挂着一只小铜铃。\n叮——叮——铃声响到哪里，哪里的人就知道，有信来了。"),
            new IntroBeat(IntroShot.DengBo, "灯  伯",
                "守码头的人。老伴走后，他照旧每天早上升旗，每天晚上挂灯。\n旗子磨白了边，他也没换过。"),
            new IntroBeat(IntroShot.Boy, "小灯笼",
                "岛上只有一个孩子，从生下来就不会发光。\n他和阿婆住在岬角，走到哪里，都提着一盏灯笼。\n村里的孩子都叫他——小灯笼。"),
        };

        // ---------- 序章 · 长夜将至 ----------
        public const string PrologueTitle = "序章 · 长夜将至";
        public static readonly Line[] PrologueOpening =
        {
            N("“小灯笼”这个名字，是阿萤起的。他一直不知道，她为什么这样叫他。"),
            N("长夜前一天，采光船要出海去远方采光果。全村的人都从坡上下来，挤在港湾的栈桥上送行。"),
            N("站在船头的，是阿萤。他站在人群最后面。"),
        };
        public static readonly Line[] PrologueAYing =
        {
            Y("我的光分你一半。"),
            Y("等我回来，我们一起看地球变圆。"),
        };
        public static readonly Line[] PrologueAfterBoat =
        {
            N("他笑着挥手，看着她的光在海面上缩成一颗星。"),
            P("连她分给我的光，都比我自己的亮。"),
        };
        public static readonly Line[] PrologueABo =
        {
            N("那天晚上，阿婆把三个铜灯罩放进他手里。"),
            B("晚风灯，照小路上从村子走来的人；月窗灯，照我那扇圆窗；归航灯，照码头边等船回来的人。"),
            B("长夜来了。今年，岬角的灯交给你守。"),
            P("……因为我上不了船吧。"),
            B("灯不用你照亮。你只要让它照对地方。"),
        };
        public const string PrologueCard = "阿萤是岛上最亮的孩子，\n也是你最好的朋友。\n她出海采光，你留下来守灯。\n阿婆说：“只要让光照对地方。”";

        // ---------- 第一章 · 山路上的铃铛 ----------
        public const string Chapter1Title = "第一章 · 山路上的铃铛";
        public static readonly Line[] Chapter1Opening =
        {
            N("长夜的第一个晚上，晚风灯的灯头歪着，光大半漏到了天上。岬角的夜空被照得发白，进岬角的那段小路却是黑的。"),
            N("叮——叮——铃声从村子那边一路响过来，在路口停住了。"),
        };
        public static readonly Line[] Chapter1Ask =
        {
            M("是阿婆家的小灯笼吧？"),
            M("爷爷今晚有点走不动，这段路太黑。你帮爷爷看看那盏灯？"),
        };
        public static readonly Line[] Chapter1WrongTurn = { M("不急，不急。灯这东西，慢慢就听话了。") };
        public static readonly Line[] Chapter1Bench =
        {
            M("我年轻时也不会发光，走得也比谁都慢。跟我一起学送信的，后来都去做了更了不起的事。可这条路，只有我一直在走。"),
            M("有一年长夜，我的灯在半路灭了，只好摸着石头走。走到天快亮，把最后一封信塞进门缝，坐在台阶上一低头——邮包上的露水，亮了。"),
            M("我自己都不知道它是什么时候来的。大概是走着走着，就来了吧。"),
        };
        public static readonly Line[] Chapter1Bell =
        {
            M("下回长夜，这条路就交给你了。"),
            P("这条路那么长，我走不了那么远。"),
            M("那就先走到长椅这儿。路是一段一段走的。"),
        };
        public const string Chapter1Done = "邮差爷爷在长椅上歇好了脚。\n他把邮包上的小铃，挂在了你的灯笼上。";

        // ---------- 第二章 · 荒原上的窗 ----------
        public const string Chapter2Title = "第二章 · 荒原上的窗";
        public static readonly Line[] Chapter2Opening =
        {
            N("长夜的第二个晚上，阿婆的圆窗是黑的。"),
            N("每年长夜，阿婆都坐在窗边，把岛上每一棵光树记进一本厚本子。今年光不够了，她自己的光也太淡，看不清字。"),
            N("路口也要光，晚风灯一个照不过来。"),
        };
        public static readonly Line[] Chapter2Lit = { B("照得正好。进来吧。") };
        public static readonly Line[] Chapter2Story =
        {
            B("这座岛原来是光秃秃的石头，没有林子，也没有村子。我们那一代年轻人从海边一筐一筐背土，在石头上凿坑种树。"),
            B("第一年，种下三百棵，一棵都没活。第二年，活了三棵。就是岬角上立着金色月牙的那个地方。"),
            B("有了三棵，就知道这里能活。有了树，才有光果；有了光果，坡上才住得下人。"),
            P("阿婆，你那时候……种得好吗？"),
            B("不好。我是那一拨里种得最差的。我最好的朋友叫阿槿，种什么活什么。我种十棵，死九棵。"),
            B("她对我可好了，种完自己那片就跑来帮我。可她越帮我，我越难受，总觉得她是光，我是光旁边的影子。"),
            B("后来才明白，影子也能种树。有的树三年开花，有的树十年。树不跟树比，谁先开花。它只管，把根扎下去。"),
            N("那天晚上，阿婆念，他写，把这一年的光树记完了。"),
            B("我种的第一片树，一棵都没活。屋前那棵金色的，是你出生那年种的。十二年了，还没开过花。我不急。"),
            N("他每天从那棵树下走过，借着它的光进门、出门。原来，有人为他种了一棵树。"),
            P("阿婆，你为什么让我守灯？阿萤她们，都比我……"),
            B("等你守完这个长夜，就知道了。"),
        };
        public const string Chapter2Done = "阿婆合上本子：\n“我种的第一片树，一棵都没活。\n屋前那棵金色的，是你出生那年种的。”";

        // ---------- 幕间 · 熄灯 ----------
        public const string InterludeTitle = "幕间 · 熄灯";
        public static readonly Line[] InterludeHarbor =
        {
            N("长夜的第三个晚上，采光船没有按时回来。"),
            N("全村的人都挤在港湾的栈桥上，举着灯望着海。一盏盏灯从村子一直连到码头，像一条从山坡上流下来的光河。"),
            new Line(Speaker.Child, "要是阿萤姐姐在就好了。她最亮了，船一定看得见。"),
            new Line(Speaker.Villager, "小灯笼守的灯也很亮的。"),
            N("他知道，大家是好意。可正因为大家都这么好，他才更难受。"),
        };
        public static readonly Line[] InterludeAlone =
        {
            N("走到金色光树下，他打开灯笼，对着光果轻轻吹了一口气。"),
            N("光灭了。"),
            P("反正我也照不亮谁。"),
            N("不知道过了多久，楼下传来一声铃响。邮差爷爷从码头一路走回岬角，把一封折成萤火虫形状的信放在床边。"),
            M("阿萤临走那天塞给我的。她说，长夜第三天晚上再交给你。她说，那时候你大概会需要。"),
        };
        public const string LetterText =
            "小灯笼：\n\n" +
            "其实我很怕黑。大家都说我最亮，可越亮，我越不敢暗下来，好像我一暗，大家就会失望。\n\n" +
            "第一次出海，海上好黑，我站在船头腿一直抖。后来我就想你，想你一个人提着灯笼从岬角走到村子的样子，不快也不慢，一步一步地走。然后我就没那么怕了。\n\n" +
            "你有一个本事，是我们谁都没有的。我们身上都有光，走到哪儿都亮堂堂的，所以从来看不见哪里黑。只有你看得见。\n\n" +
            "你一直在暗处，所以你知道哪里最暗。\n\n" +
            "阿婆让你守灯，不是因为你上不了船。等我回来。\n\n" +
            "　　　　　　　　　　　　阿萤";
        public const string LetterButton = "重新点亮灯笼 →";
        public static readonly Line[] InterludeAfterLetter =
        {
            N("港湾里，大家心急，把灯都举向天和海。整片天被照得白蒙蒙的，一颗星也看不见。"),
            N("海上的人，是靠星星认路的。"),
            N("他捡起那盏灭了的灯笼，捧在手心里轻轻摇了摇。光果醒了。小铃叮地响了一声。"),
        };

        // ---------- 第三章 · 长夜里，船还没回来 ----------
        public const string Chapter3Title = "第三章 · 长夜里，船还没回来";
        public static readonly Line[] Chapter3Shout =
        {
            P("大家能不能先把灯放低一点！天太亮了，船看不见星星。"),
            new Line(Speaker.Villager, "听小灯笼的，他守了三天灯，他知道。"),
            N("码头上的灯一盏一盏放低，村子里的窗也一扇扇拉上了帘子。头顶的夜空一点点黑了回来。"),
            N("可岬角的光果只够三盏灯了。小路、长椅、阿婆的窗、码头——四个地方，三盏灯，只能有一束宽光。"),
        };
        public static readonly Line[] Chapter3DengBo =
        {
            D("我跟老伴儿守这码头，守了大半辈子。每天早上她升旗，每天晚上我挂灯。旗是她缝的。"),
            D("她走以后，我照旧升旗，照旧挂灯。有人问我图个什么，那盏马灯又不是岛上最亮的灯，坡上随便一扇窗都比它亮。"),
            D("可灯不用最亮。要一直亮着，让船认得它。"),
        };
        public static readonly Line[] Chapter3LampOut =
        {
            N("可旗杆上的马灯，在他调灯的时候，最后一点光熄了。灯伯把手贴在玻璃上，想分一点自己的光进去。"),
            D("不够。还差一点。"),
            N("他低头看着自己的灯笼。上面挂着邮差爷爷的小铃，里面还留着阿萤分给他的光。那是他唯一的光。"),
            N("可现在，最暗的地方，是旗杆上。"),
        };
        public static readonly Line[] Chapter3Hung =
        {
            N("那只是一盏小小的灯笼。可今晚的天，被全岛的人一盏一盏收回了黑色；在那么干净的黑夜里，哪怕只有一点点光，海上也看得见。"),
            N("他退后两步，站在旗杆的影子里，手里什么都没有了。远远地，海上传来了一声船铃。"),
        };
        public const string Chapter3Done = "四处都有了光，可旗杆上还是黑的。\n你把挂着铃铛的灯笼，挂上了灯伯的旗杆。";

        // ---------- 终章 · 夜空里，多了一颗星 ----------
        public const string FinaleTitle = "终章 · 夜空里，多了一颗星";
        public static readonly Line[] FinaleHands =
        {
            N("码头上的人都在往栈桥边涌。没有人回头看他。"),
            N("在完全的黑暗里，他第一次看见了自己的手：手指的边缘，有一层很淡很淡的光，浅浅的琥珀色，像清晨窗玻璃上的一口哈气。"),
            N("他在发光。是岛上最淡的那一种。可那是他自己的光。"),
            N("原来，光是给出去，才长出来的。"),
        };
        public static readonly Line[] FinaleReunion =
        {
            Y("我听见铃铛，就知道是你在守灯。"),
            N("她低头看见了他的手。她没有大喊，只是笑了，把自己的手轻轻放在他的手旁边。一只亮得像春天，一只淡得像一口哈气。"),
            P("我还是最暗的。"),
            Y("嗯。可是我在海上，只认得这一盏。"),
            Y("小灯笼这个名字，你是不是一直不喜欢？我起这个名字，是因为每次天黑，我都先找你的灯。"),
        };
        public static readonly Line[] FinaleBloom =
        {
            N("小路上，邮差爷爷的铃响了；岬角上，阿婆的窗亮着；旗杆下，灯伯站起身，准备天亮升旗。"),
            N("阿婆屋前，那棵金色的光树，在最低的一根斜枝上，开出了第一朵花。"),
            B("你看，这棵树开花了。不早，也不晚。"),
            N("天边，那道细细的地球，亮起了一道新的边。长夜过去了。"),
        };
        public const string FinaleStar = "很远的地方，有个孩子指着夜空说：\n“那里多了一颗星星。”";
        public const string FinaleCard = "黑暗里，你看见了自己的手。\n它在发光，是岛上最淡的那一种。\n船靠岸了，阿萤跳下来：\n“我听见铃铛，就知道是你。”";

        // ---------- 漫步尾声 ----------
        public static string EpilogueLine(Speaker s) => EpilogueLines(s)[0];

        // Walking the island after the long night: each friend has a little more to say every
        // time he comes back to them.
        public static string[] EpilogueLines(Speaker s)
        {
            switch (s)
            {
                case Speaker.AYing: return new[]
                {
                    "下回出海，你来守灯，好不好？我只认得你的灯。",
                    "其实那天在船头，我腿一直在抖。后来海上起风，我就想你提着灯笼走路的样子。",
                    "你看天上，地球又亮了一点。等它变圆，我们一起去岬角看。",
                };
                case Speaker.Postman: return new[]
                {
                    "小铃是你的了。下回长夜，路就交给你。",
                    "今天的信不多，可每一封都要送到。走慢一点，路不会跑。",
                    "我数过，这条路一共一千二百三十步。你守着的那一段，最亮。",
                };
                case Speaker.ABo: return new[]
                {
                    "你看，这棵树开花了。不早，也不晚。",
                    "本子上今年多记了一行：岬角，金色光树，开花一朵。字是你写的。",
                    "阿槿要是还在，一定会笑我：你种的树，也终于开花了。",
                };
                case Speaker.DengBo: return new[]
                {
                    "旗是她缝的。灯，现在是你挂的。",
                    "明早升旗，你来不来？她总说，旗子要有人看着升起来，才算数。",
                    "那盏小灯笼，我给它换了根新绳子。挂了一夜，一点没歪。",
                };
                default: return new[] { "" };
            }
        }
        public const string EpilogueClosing = "如果你也常常觉得自己不如别人，\n试着把这份心情告诉一个你信任的人。";

        // ---------- 章节信息（章节地图、章节卡、任务栏） ----------
        public struct ChapterInfo
        {
            public Chapter Id;
            public string Number, Title, Subtitle, Description, Quest, MapPlace, Enter;
        }

        public const string MapTitle = "借光岛的长夜";
        public const string MapSubtitle = "故事，从一盏灯笼开始";
        public const string MapLatin = "THE ISLAND OF BORROWED LIGHT";

        public static readonly ChapterInfo[] Chapters =
        {
            new ChapterInfo { Id = Chapter.Prologue, Number = "序 章", Title = "长夜将至", Subtitle = "她出海采光，你留下来守灯",
                Description = "长夜前一天，采光船要出海。全村的人都下到栈桥上，为阿萤送行。", Quest = "为阿萤送行", MapPlace = "栈桥", Enter = "走上栈桥" },
            new ChapterInfo { Id = Chapter.One, Number = "第 一 章", Title = "山路上的铃铛", Subtitle = "照亮回家的小路",
                Description = "长夜的第一个晚上，晚风灯的灯头歪着。叮——叮——铃声在路口停住了。", Quest = "帮邮差爷爷照亮小路", MapPlace = "路口", Enter = "走到路口" },
            new ChapterInfo { Id = Chapter.Two, Number = "第 二 章", Title = "荒原上的窗", Subtitle = "一束不多也不少的光",
                Description = "阿婆的圆窗是黑的。今年光不够了，她看不清本子上的字。", Quest = "照亮阿婆的圆窗", MapPlace = "圆窗", Enter = "回到阿婆家" },
            new ChapterInfo { Id = Chapter.Interlude, Number = "幕 间", Title = "熄灯", Subtitle = "一封萤火虫形状的信",
                Description = "第三个晚上，采光船没有按时回来。他一个人走回岬角。", Quest = "长夜的第三个晚上", MapPlace = "金色光树", Enter = "走向港湾" },
            new ChapterInfo { Id = Chapter.Three, Number = "第 三 章", Title = "长夜里，船还没回来", Subtitle = "四个地方，三盏灯",
                Description = "天被照得白蒙蒙的，海上的人看不见星星。最暗的地方，在旗杆上。", Quest = "让船看见回家的灯", MapPlace = "旗杆", Enter = "跑向码头" },
            new ChapterInfo { Id = Chapter.Finale, Number = "终 章", Title = "夜空里，多了一颗星", Subtitle = "不早，也不晚",
                Description = "在完全的黑暗里，他第一次看见了自己的手。", Quest = "等船回来", MapPlace = "码头", Enter = "等船回来" },
            new ChapterInfo { Id = Chapter.Epilogue, Number = "尾 声", Title = "长夜之后", Subtitle = "沿着小路走走吧",
                Description = "长夜过去了。小路上，邮差爷爷的铃又响了。", Quest = "长夜过去了", MapPlace = "全岛", Enter = "走走看看" },
        };

        public static ChapterInfo Info(Chapter c)
        {
            foreach (var i in Chapters) if (i.Id == c) return i;
            return Chapters[0];
        }

        // ---------- 目标与提示 ----------
        public static string Objective(Chapter c)
        {
            switch (c)
            {
                case Chapter.One: return "让小路和长椅亮起来，别让光漏到天上。";
                case Chapter.Two: return "月窗灯换窄罩照窗，同时保持小路与长椅明亮。";
                case Chapter.Three: return "照亮小路、长椅、窗和码头——只能有一束宽光。";
                default: return "";
            }
        }
    }
}
