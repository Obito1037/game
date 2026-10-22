using System;
using UnityEngine;

namespace BorrowedLight
{
    [DisallowMultipleComponent]
    public sealed class GameLogic : MonoBehaviour
    {
        private const string SaveKey = "BorrowedLight.Journey.v1";
        private const int SaveVersion = 1;
        private LampState[] lamps;
        private int moves;
        private int stageMoves;
        private bool initialized;
        private bool hadSave;
        private bool wasSolved;

        public GamePhase Phase { get; private set; } = GamePhase.Prologue;
        public int SelectedLamp { get; private set; }
        public GameSnapshot Current { get { EnsureInitialized(); return BuildSnapshot(); } }

        public event Action<GameSnapshot> OnChanged;
        public event Action<GamePhase> OnPhaseChanged;
        public event Action<string> OnNarration;

        [Serializable]
        private sealed class SavedJourney
        {
            public int Version;
            public int Phase;
            public int SelectedLamp;
            public int Moves;
            public int StageMoves;
            public LampState[] Lamps;
        }

        private void Awake() { EnsureInitialized(); }

        // Loads a saved chapter if available; otherwise presents the prologue.
        // Advance() starts the first chapter from that prologue.
        public void BeginJourney(bool resume = true)
        {
            initialized = false;
            Initialize(resume);
            Publish(true, true);
        }

        public void SelectLamp(int index)
        {
            EnsureInitialized();
            if (!IsPlayable || index < 0 || index >= lamps.Length || !lamps[index].IsUnlocked) return;
            if (SelectedLamp == index) return;
            SelectedLamp = index;
            Save();
            Publish(false, false);
        }

        public void RotateSelected(int step)
        {
            EnsureInitialized();
            LampState lamp = lamps[SelectedLamp];
            SetLamp(SelectedLamp, lamp.Direction + step, lamp.Wide, lamp.IsOn);
        }

        public void ToggleSelectedShade()
        {
            EnsureInitialized();
            LampState lamp = lamps[SelectedLamp];
            SetLamp(SelectedLamp, lamp.Direction, !lamp.Wide, lamp.IsOn);
        }

        public void ToggleSelectedPower()
        {
            EnsureInitialized();
            LampState lamp = lamps[SelectedLamp];
            SetLamp(SelectedLamp, lamp.Direction, lamp.Wide, !lamp.IsOn);
        }

        public void SetLamp(int index, int direction, bool wide, bool on)
        {
            EnsureInitialized();
            if (!IsPlayable || index < 0 || index >= lamps.Length || !lamps[index].IsUnlocked) return;
            LampState lamp = lamps[index];
            direction = LampPuzzle.NormalizeDirection(direction);
            if (lamp.Direction == direction && lamp.Wide == wide && lamp.IsOn == on) return;
            lamp.Direction = direction;
            lamp.Wide = wide;
            lamp.IsOn = on;
            ++moves;
            ++stageMoves;
            Save();
            Publish(false, false);
        }

        public bool Advance()
        {
            EnsureInitialized();
            if (Phase == GamePhase.Epilogue)
            {
                RestartJourney();
                return true;
            }
            if (Phase != GamePhase.Prologue && !LampPuzzle.Evaluate(Phase, lamps).IsSolved) return false;
            EnterPhase((GamePhase)((int)Phase + 1));
            return true;
        }

        public void RetryStage()
        {
            EnsureInitialized();
            if (!IsPlayable) return;
            // Restores the solved previous chapter, then introduces the current lamp.
            lamps = LampPuzzle.CreateInitialLamps();
            if (Phase >= GamePhase.Window)
            {
                lamps[0].Direction = 0;
                lamps[0].Wide = true;
            }
            if (Phase >= GamePhase.Harbor)
            {
                lamps[1].Direction = 0;
                lamps[1].Wide = false;
                lamps[1].IsOn = true;
            }
            ApplyUnlocks(true);
            SelectedLamp = Math.Max(0, LampPuzzle.GetUnlockedLampCount(Phase) - 1);
            stageMoves = 0;
            wasSolved = false;
            Save();
            Publish(false, true);
        }

        public void RestartJourney()
        {
            PlayerPrefs.DeleteKey(SaveKey);
            PlayerPrefs.Save();
            initialized = false;
            Initialize(false);
            Publish(true, true);
        }

        public GameSnapshot GetState() { return Current; }
        public bool HasSavedProgress { get { return PlayerPrefs.HasKey(SaveKey); } }
        private bool IsPlayable { get { return Phase >= GamePhase.Path && Phase <= GamePhase.Harbor; } }

        private void EnsureInitialized()
        {
            if (!initialized) Initialize(true);
        }

        private void Initialize(bool resume)
        {
            initialized = true;
            lamps = LampPuzzle.CreateInitialLamps();
            Phase = GamePhase.Prologue;
            SelectedLamp = 0;
            moves = 0;
            stageMoves = 0;
            hadSave = false;
            if (resume && PlayerPrefs.HasKey(SaveKey))
            {
                try
                {
                    SavedJourney saved = JsonUtility.FromJson<SavedJourney>(PlayerPrefs.GetString(SaveKey));
                    if (saved != null && saved.Version == SaveVersion && saved.Phase >= 0 &&
                        saved.Phase <= (int)GamePhase.Epilogue && saved.Lamps != null && saved.Lamps.Length == 3)
                    {
                        Phase = (GamePhase)saved.Phase;
                        for (int i = 0; i < lamps.Length; ++i)
                        {
                            if (saved.Lamps[i] == null) continue;
                            lamps[i].Direction = LampPuzzle.NormalizeDirection(saved.Lamps[i].Direction);
                            lamps[i].Wide = saved.Lamps[i].Wide;
                            lamps[i].IsOn = saved.Lamps[i].IsOn;
                        }
                        moves = Math.Max(0, saved.Moves);
                        stageMoves = Math.Max(0, saved.StageMoves);
                        SelectedLamp = Math.Max(0, Math.Min(2, saved.SelectedLamp));
                        hadSave = true;
                    }
                }
                catch (Exception)
                {
                    // A truncated / older local save starts a clean, playable journey.
                    hadSave = false;
                }
            }
            ApplyUnlocks(false);
            if (!lamps[SelectedLamp].IsUnlocked) SelectedLamp = 0;
            wasSolved = LampPuzzle.Evaluate(Phase, lamps).IsSolved;
        }

        private void EnterPhase(GamePhase next)
        {
            Phase = next;
            stageMoves = 0;
            wasSolved = false;
            ApplyUnlocks(true);
            SelectedLamp = Math.Max(0, LampPuzzle.GetUnlockedLampCount(Phase) - 1);
            Save();
            Publish(true, true);
        }

        private void ApplyUnlocks(bool activateNewLamp)
        {
            int count = LampPuzzle.GetUnlockedLampCount(Phase);
            for (int i = 0; i < lamps.Length; ++i)
            {
                bool newUnlock = !lamps[i].IsUnlocked && i < count;
                lamps[i].IsUnlocked = i < count;
                if (!lamps[i].IsUnlocked) lamps[i].IsOn = false;
                else if (activateNewLamp && newUnlock) lamps[i].IsOn = true;
            }
        }

        private GameSnapshot BuildSnapshot()
        {
            PuzzleEvaluation evaluation = LampPuzzle.Evaluate(Phase, lamps);
            var lampCopies = new LampState[lamps.Length];
            for (int i = 0; i < lamps.Length; ++i)
            {
                lampCopies[i] = lamps[i].Copy();
                lampCopies[i].CoverageMask = LampPuzzle.GetCoverageMask(i, lamps[i].Direction, lamps[i].Wide, lamps[i].IsOn);
            }
            string[] targetIds = { "path", "bench", "window", "dock" };
            string[] targetNames = { "小路", "长椅", "窗户", "码头" };
            var targets = new TargetState[4];
            for (int i = 0; i < targets.Length; ++i)
            {
                targets[i] = new TargetState
                {
                    Id = targetIds[i], Name = targetNames[i],
                    IsLit = (evaluation.CoveredMask & (1 << i)) != 0,
                    IsRequired = (evaluation.RequiredMask & (1 << i)) != 0
                };
            }
            return new GameSnapshot
            {
                Phase = Phase, Lamps = lampCopies, Targets = targets,
                SelectedLamp = SelectedLamp, RequiredMask = evaluation.RequiredMask,
                CoveredMask = evaluation.CoveredMask, Pollution = evaluation.Pollution,
                AllowedPollution = evaluation.AllowedPollution, Moves = moves, StageMoves = stageMoves,
                IsSolved = evaluation.IsSolved,
                CanAdvance = Phase == GamePhase.Prologue || Phase == GamePhase.Epilogue || evaluation.IsSolved,
                HasSavedProgress = hadSave,
                JourneyProgress = Phase == GamePhase.Epilogue ? 1f : Math.Max(0f, ((int)Phase - 1 + (evaluation.IsSolved ? 1 : 0)) / 3f),
                StageTitle = StoryData.StageTitle(Phase), Objective = StoryData.Objective(Phase),
                Hint = StoryData.Hint(Phase, lamps, evaluation),
                Narration = evaluation.IsSolved && IsPlayable ? StoryData.CompletedNarration(Phase) : StoryData.Narration(Phase)
            };
        }

        private void Publish(bool phaseChanged, bool narrate)
        {
            GameSnapshot state = BuildSnapshot();
            bool newlySolved = state.IsSolved && !wasSolved && IsPlayable;
            wasSolved = state.IsSolved;
            OnChanged?.Invoke(state);
            if (phaseChanged) OnPhaseChanged?.Invoke(Phase);
            if (narrate || newlySolved) OnNarration?.Invoke(state.Narration);
        }

        private void Save()
        {
            if (Phase == GamePhase.Prologue) return;
            var saved = new SavedJourney
            {
                Version = SaveVersion, Phase = (int)Phase, SelectedLamp = SelectedLamp,
                Moves = moves, StageMoves = stageMoves, Lamps = lamps
            };
            PlayerPrefs.SetString(SaveKey, JsonUtility.ToJson(saved));
            PlayerPrefs.Save();
            hadSave = true;
        }

        private void OnApplicationPause(bool paused) { if (paused && initialized) Save(); }
        private void OnApplicationQuit() { if (initialized) Save(); }
    }
}
