namespace BorrowedLight
{
    public static class StoryData
    {
        public static string StageTitle(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path: return "第一封信 · 晚风有路";
                case GamePhase.Window: return "第二封信 · 一扇亮着的窗";
                case GamePhase.Harbor: return "第三封信 · 给远方留一点夜色";
                case GamePhase.Epilogue: return "星星一直都在";
                default: return "借光岛";
            }
        }

        public static string Objective(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path: return "让小路和长椅都亮起来。";
                case GamePhase.Window: return "照亮书桌，也留住小路与长椅的光。";
                case GamePhase.Harbor: return "照亮四处生活，只留一束宽光。";
                case GamePhase.Epilogue: return "你把光留给生活，把夜晚还给星空。";
                default: return "一座小岛，三盏灯，一片等待被看见的星空。";
            }
        }

        public static string Narration(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path:
                    return "守夜人把第一盏灯交给你。\n“请替晚归的人，照亮脚下的路。”";
                case GamePhase.Window:
                    return "窗里的人合上书，又轻轻翻开。\n“我只想读完这一页，不必照亮整片天空。”";
                case GamePhase.Harbor:
                    return "码头传来最后一声船铃。\n“有人在等一盏归航的灯。也有人，在等一颗星。”";
                case GamePhase.Epilogue:
                    return "灯光安静地落在需要它的地方。\n小岛没有睡去，星空却醒了。\n\n“原来，星星一直都在。”";
                default:
                    return "你记得回家的方向，\n却找不到那颗指路的星。\n\n今夜，借光岛上的人们，愿意借给你一点光。";
            }
        }

        public static string CompletedNarration(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path: return "晚归的脚步慢了下来。长椅上，有人终于等到了朋友。";
                case GamePhase.Window: return "书页亮了，窗外的夜色也被温柔地留下。";
                case GamePhase.Harbor: return "小路、长椅、窗户与码头，都有了自己的光。抬头看看吧。";
                default: return Narration(phase);
            }
        }

        public static string Hint(GamePhase phase, LampState[] lamps, PuzzleEvaluation evaluation)
        {
            if (phase == GamePhase.Prologue) return "按下开始，或按 Enter，走进这个夜晚。";
            if (phase == GamePhase.Epilogue) return "愿每一束光，都能找到需要它的地方。";
            if (evaluation.IsSolved) return "这一封信已经送达。继续旅程吧。";
            if (phase == GamePhase.Path)
                return "选中晚风灯，转向地面。宽光能同时照到小路和长椅。";
            if (phase == GamePhase.Window)
            {
                if ((evaluation.CoveredMask & LampPuzzle.Window) == 0)
                    return "把月窗灯转向窗户，试试更集中的窄光。";
                return "还要照顾小路与长椅。每一束宽光都会占用一点夜色。";
            }
            if (evaluation.Pollution > evaluation.AllowedPollution)
                return "两盏宽灯太耀眼了。让归航灯接过长椅的光，再收窄晚风灯。";
            if ((evaluation.CoveredMask & LampPuzzle.Dock) == 0)
                return "月窗灯转向码头时，宽光可以同时照到窗户和码头。";
            if ((evaluation.CoveredMask & LampPuzzle.Bench) == 0)
                return "长椅还在等人。把归航灯转向它，窄光就够了。";
            if ((evaluation.CoveredMask & LampPuzzle.Path) == 0)
                return "晚风灯的窄光，可以安静地照亮小路。";
            return "让灯光落向生活的地方，留下更完整的夜空。";
        }

        public static string DirectionName(int lampIndex, int direction)
        {
            direction = LampPuzzle.NormalizeDirection(direction);
            if (direction == 2) return "星空";
            if (lampIndex == 0) return direction == 0 ? "小路" : "长椅";
            if (lampIndex == 1) return direction == 0 ? "窗户" : "码头";
            return direction == 0 ? "长椅" : "远海";
        }
    }
}
