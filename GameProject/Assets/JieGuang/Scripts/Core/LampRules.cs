using System;

namespace JieGuang
{
    public enum Chapter { Title = 0, Prologue = 1, One = 2, Two = 3, Interlude = 4, Three = 5, Finale = 6, Epilogue = 7 }

    [Flags]
    public enum Target { None = 0, Path = 1, Bench = 2, Window = 4, Pier = 8, All = 15 }

    [Serializable]
    public sealed class LampSetting
    {
        public int Direction; // 0, 1 = towards the island; 2 = up (sky)
        public bool Wide;
        public bool On;
        public LampSetting Clone() => (LampSetting)MemberwiseClone();
    }

    public struct LampResult
    {
        public Target Required, Covered;
        public int SkyLoss, SkyAllowed;
        public bool Solved;
    }

    // Pure puzzle rules for the three oldest lamps on the cape (no Unity dependencies).
    //   晚风灯  dir0: path (wide: path + bench)   dir1: bench        dir2: sky
    //   月窗灯  dir0: window                      dir1: pier (wide: window + pier)   dir2: sky
    //   归航灯  dir0: bench                       dir1: open sea      dir2: sky
    // Every wide shield and every beam that lights nothing costs one unit of night sky;
    // each night allows one unit. Chapter 3 solution: 3 → D → 2 → D → Space → 1 → Space → Enter.
    public static class LampRules
    {
        public const int LampCount = 3;
        public const int Directions = 3;
        public static readonly string[] LampNames = { "晚风灯", "月窗灯", "归航灯" };

        public static int Wrap(int d) => ((d % Directions) + Directions) % Directions;

        public static Target Coverage(int lamp, LampSetting s)
        {
            if (s == null || !s.On) return Target.None;
            int d = Wrap(s.Direction);
            switch (lamp)
            {
                case 0: return d == 0 ? (s.Wide ? Target.Path | Target.Bench : Target.Path) : d == 1 ? Target.Bench : Target.None;
                case 1: return d == 0 ? Target.Window : d == 1 ? (s.Wide ? Target.Window | Target.Pier : Target.Pier) : Target.None;
                case 2: return d == 0 ? Target.Bench : Target.None;
            }
            return Target.None;
        }

        public static int SkyLoss(int lamp, LampSetting s)
        {
            if (s == null || !s.On) return 0;
            return (s.Wide ? 1 : 0) + (Coverage(lamp, s) == Target.None ? 1 : 0);
        }

        public static Target Required(Chapter c)
        {
            switch (c)
            {
                case Chapter.One: return Target.Path | Target.Bench;
                case Chapter.Two: return Target.Path | Target.Bench | Target.Window;
                case Chapter.Three: return Target.All;
                default: return Target.None;
            }
        }

        public static int UnlockedLamps(Chapter c)
        {
            switch (c)
            {
                case Chapter.One: return 1;
                case Chapter.Two: return 2;
                case Chapter.Three: return 3;
                default: return 0;
            }
        }

        public static LampResult Evaluate(Chapter c, LampSetting[] lamps)
        {
            var r = new LampResult { Required = Required(c), SkyAllowed = 1 };
            for (int i = 0; i < LampCount && i < lamps.Length; ++i)
            {
                r.Covered |= Coverage(i, lamps[i]);
                r.SkyLoss += SkyLoss(i, lamps[i]);
            }
            r.Solved = r.Required != Target.None && (r.Covered & r.Required) == r.Required && r.SkyLoss <= r.SkyAllowed;
            return r;
        }

        // State at the start of each chapter: what the previous night left behind.
        public static LampSetting[] StartState(Chapter c)
        {
            var l = new[]
            {
                new LampSetting { Direction = 2, Wide = false, On = true },  // 晚风灯 tilted to the sky
                new LampSetting { Direction = 2, Wide = false, On = false },
                new LampSetting { Direction = 2, Wide = false, On = false },
            };
            if (c >= Chapter.Two)
            {
                l[0] = new LampSetting { Direction = 0, Wide = true, On = true };
                l[1] = new LampSetting { Direction = 2, Wide = true, On = true };
            }
            if (c >= Chapter.Three)
            {
                l[1] = new LampSetting { Direction = 0, Wide = false, On = true };
                l[2] = new LampSetting { Direction = 2, Wide = false, On = true };
            }
            return l;
        }

        public static string DirectionName(int lamp, int dir)
        {
            dir = Wrap(dir);
            if (dir == 2) return "天空";
            switch (lamp)
            {
                case 0: return dir == 0 ? "小路" : "长椅";
                case 1: return dir == 0 ? "圆窗" : "码头";
                default: return dir == 0 ? "长椅" : "远海";
            }
        }

        public static string TargetName(Target t)
        {
            switch (t)
            {
                case Target.Path: return "小路";
                case Target.Bench: return "长椅";
                case Target.Window: return "圆窗";
                case Target.Pier: return "码头";
                default: return "";
            }
        }

        public static string Hint(Chapter c, LampSetting[] lamps, LampResult r)
        {
            if (r.Solved) return "灯都照对了地方。按 Enter 确认。";
            if (c == Chapter.One)
                return Wrap(lamps[0].Direction) != 0 ? "把晚风灯的灯头转向地面（A / D）。" : "小路亮了。换上宽罩（空格），光能一直铺到长椅。";
            if (c == Chapter.Two)
                return (r.Covered & Target.Window) == 0 ? "月窗灯转向圆窗（先按 2 选中它）。" : "两束宽光太多了，夜空会发白。给月窗灯换窄罩。";
            if (r.SkyLoss > r.SkyAllowed) return "宽光太多了，星星会看不见。想想哪一盏灯的宽光能同时照到两处。";
            if ((r.Covered & Target.Pier) == 0) return "月窗灯转向码头时，宽光能同时照到圆窗和码头。";
            if ((r.Covered & Target.Bench) == 0) return "长椅还在等人。归航灯转过去，窄光就够了。";
            if ((r.Covered & Target.Path) == 0) return "晚风灯的窄光，可以安静地照亮小路。";
            return "让每一束光都落在需要它的地方。";
        }
    }
}
