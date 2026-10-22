using System;

namespace BorrowedLight
{
    public enum GamePhase { Prologue, Path, Window, Harbor, Epilogue }

    [Serializable]
    public sealed class LampState
    {
        public int Index;
        public string Name;
        public int Direction;
        public bool Wide;
        public bool IsOn;
        public bool IsUnlocked;
        public int CoverageMask;

        public LampState Copy()
        {
            return (LampState)MemberwiseClone();
        }
    }

    [Serializable]
    public sealed class TargetState
    {
        public string Id;
        public string Name;
        public bool IsLit;
        public bool IsRequired;
    }

    [Serializable]
    public sealed class GameSnapshot
    {
        public GamePhase Phase;
        public LampState[] Lamps;
        public TargetState[] Targets;
        public int SelectedLamp;
        public int RequiredMask;
        public int CoveredMask;
        public int Pollution;
        public int AllowedPollution;
        public int Moves;
        public int StageMoves;
        public bool IsSolved;
        public bool CanAdvance;
        public bool HasSavedProgress;
        public float JourneyProgress;
        public string StageTitle;
        public string Objective;
        public string Hint;
        public string Narration;
    }

    public struct PuzzleEvaluation
    {
        public int RequiredMask;
        public int CoveredMask;
        public int Pollution;
        public int AllowedPollution;
        public bool IsSolved;
    }

    // Pure rules: no rendering, physics, input, hierarchy or Unity dependencies.
    public static class LampPuzzle
    {
        public const int Path = 1;
        public const int Bench = 2;
        public const int Window = 4;
        public const int Dock = 8;
        public const int AllTargets = Path | Bench | Window | Dock;
        public const int LampCount = 3;
        public const int DirectionCount = 3;

        public static int NormalizeDirection(int direction)
        {
            return ((direction % DirectionCount) + DirectionCount) % DirectionCount;
        }

        public static int GetCoverageMask(int lampIndex, int direction, bool wide, bool on)
        {
            if (!on || lampIndex < 0 || lampIndex >= LampCount) return 0;
            direction = NormalizeDirection(direction);
            switch (lampIndex)
            {
                case 0:
                    if (direction == 0) return wide ? Path | Bench : Path;
                    if (direction == 1) return Bench;
                    break;
                case 1:
                    if (direction == 0) return Window;
                    if (direction == 1) return wide ? Window | Dock : Dock;
                    break;
                case 2:
                    if (direction == 0) return Bench;
                    break;
            }
            return 0;
        }

        // A broad beam consumes one unit. A beam lost to the sky consumes one more.
        // This is a deliberately readable game abstraction, not a physical light meter.
        public static int GetPollution(int lampIndex, int direction, bool wide, bool on)
        {
            if (!on || lampIndex < 0 || lampIndex >= LampCount) return 0;
            return (wide ? 1 : 0) + (GetCoverageMask(lampIndex, direction, wide, true) == 0 ? 1 : 0);
        }

        public static int GetRequiredMask(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path: return Path | Bench;
                case GamePhase.Window: return Path | Bench | Window;
                case GamePhase.Harbor:
                case GamePhase.Epilogue: return AllTargets;
                default: return 0;
            }
        }

        public static int GetUnlockedLampCount(GamePhase phase)
        {
            switch (phase)
            {
                case GamePhase.Path: return 1;
                case GamePhase.Window: return 2;
                case GamePhase.Harbor:
                case GamePhase.Epilogue: return 3;
                default: return 0;
            }
        }

        public static PuzzleEvaluation Evaluate(GamePhase phase, LampState[] lamps)
        {
            var result = new PuzzleEvaluation
            {
                RequiredMask = GetRequiredMask(phase),
                AllowedPollution = 1
            };
            if (lamps != null)
            {
                for (int i = 0; i < lamps.Length && i < LampCount; ++i)
                {
                    LampState lamp = lamps[i];
                    if (lamp == null) continue;
                    result.CoveredMask |= GetCoverageMask(i, lamp.Direction, lamp.Wide, lamp.IsOn);
                    result.Pollution += GetPollution(i, lamp.Direction, lamp.Wide, lamp.IsOn);
                }
            }
            result.IsSolved = phase != GamePhase.Prologue &&
                (result.CoveredMask & result.RequiredMask) == result.RequiredMask &&
                result.Pollution <= result.AllowedPollution;
            return result;
        }

        public static LampState[] CreateInitialLamps()
        {
            return new[]
            {
                new LampState { Index = 0, Name = "晚风灯", Direction = 2, Wide = true, IsOn = true },
                new LampState { Index = 1, Name = "月窗灯", Direction = 2, Wide = false, IsOn = false },
                new LampState { Index = 2, Name = "归航灯", Direction = 2, Wide = false, IsOn = false }
            };
        }
    }
}
