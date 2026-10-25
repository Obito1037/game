using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace JieGuang
{
    // Explicit opt-in native diagnostics. No component is created in an ordinary game launch.
    // Inputs take the same GameInput route as the keyboard. Teleports are logged and deliberately
    // do not claim to test walking/navigation/collision. Puzzle state is inspected, never written.
    public sealed class JgQaRunner : MonoBehaviour
    {
        const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
        static readonly string[] SaveKeys = { "jieguang.chapter", "jieguang.unlocked", "jieguang.debugStart" };
        static readonly string[] EpilogueActors = { "aying", "postman", "abo", "dengbo" };
        static Mutex saveMutex;
        static bool ownsSaveMutex, exitBeforeGameplay;

        [Serializable] public class SavedKey { public string key; public bool existed; public int value; }
        [Serializable] public class SaveBackup { public SavedKey[] values; public string note; }
        [Serializable] public class RestoreResult { public string backupPath, completedUtc; public bool verified; public SaveBackup before, after; }
        [Serializable] public class InputEvent
        {
            public float seconds; public string chapter, action, objective, dialogue, detail;
        }
        [Serializable] public class ErrorRecord { public string type, message, stack; public float seconds; }
        [Serializable] public class Capture
        {
            public string name, path, chapter, objective; public int screenWidth, screenHeight, pngWidth, pngHeight; public bool saved;
        }
        [Serializable] public class FrameSummary
        {
            public string scope; public int samples; public float measuredSeconds, p50Ms, p95Ms, p99Ms, meanFps, p95EquivalentFps, cpuMainP50Ms, gpuP50Ms, renderScaleMean;
        }
        [Serializable] public class Report
        {
            public string status = "running", reason = "", startedUtc, completedUtc;
            public string unityVersion, os, cpu, gpu, graphicsApi, quality, outputDirectory;
            public int cpuThreads, systemMemoryMb, graphicsMemoryMb, actualWidth, actualHeight, targetFps, vSync;
            public string method = "Normal title/map/chapter flow. GameInput keys at >=0.5 s. Diagnostic teleports bypass traversal; no puzzle-state mutation. Automated static/cutscene samples do not establish sustained gameplay performance.";
            public bool titleSeen, epilogueClosingSeen, saveRestored;
            public List<int> enteredChapters = new List<int>();
            public List<int> completedChapters = new List<int>();
            public List<int> puzzleSolvedThroughInput = new List<int>();
            public List<int> unlockValues = new List<int>();
            public List<string> epilogueVisited = new List<string>();
            public List<Capture> screenshots = new List<Capture>();
            public List<ErrorRecord> errors = new List<ErrorRecord>();
            public List<FrameSummary> frames = new List<FrameSummary>();
            public string limitations = "No manual walking, collision-route coverage, listening test, subjective visual approval, WebGL or ordinary-laptop benchmark. Frame statistics exclude warm-up, captures and teleport settling; samples include scripted normal camera shots.";
        }

        string output;
        Report report;
        SaveBackup backup;
        GameDirector director;
        GameUI ui;
        PlayerController player;
        IslandLayout layout;
        float started, lastProgress, skipFramesUntil;
        string lastState = "";
        bool finishing, restored, titleStarted, mapEnterPending, letterEntered;
        string advancedCard;
        int nextChapter = 1, lastChapter;
        int epilogueIndex;
        float nextEpilogueVisit;
        readonly HashSet<string> captures = new HashSet<string>();
        readonly Dictionary<int, List<float>> chapterFrames = new Dictionary<int, List<float>>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Bootstrap()
        {
#if UNITY_STANDALONE && !UNITY_EDITOR
            string[] args = Environment.GetCommandLineArgs();
            bool qa = Array.IndexOf(args, "--jg-qa") >= 0;
            int restoreIndex = Array.IndexOf(args, "--jg-restore-save");
            if (!qa && restoreIndex < 0) return;
            if (!AcquireSaveMutex()) { exitBeforeGameplay = true; Application.Quit(3); return; }
            if (restoreIndex >= 0)
            {
                exitBeforeGameplay = true;
                Application.quitting += ReleaseSaveMutex;
                if (qa || restoreIndex + 1 >= args.Length) { Debug.LogError("[JG-QA] Use --jg-restore-save <absolute backup> without --jg-qa."); Application.Quit(2); return; }
                RestoreFromFile(args[restoreIndex + 1]);
                return;
            }
            int i = Array.IndexOf(args, "--jg-qa-out");
            if (i < 0 || i + 1 >= args.Length || !Path.IsPathRooted(args[i + 1]))
            {
                Debug.LogError("[JG-QA] --jg-qa-out requires an absolute output directory.");
                exitBeforeGameplay = true;
                Application.quitting += ReleaseSaveMutex;
                Application.Quit(2);
                return;
            }
            string folder = Path.GetFullPath(args[i + 1]);
            Directory.CreateDirectory(folder);
            // Never overwrite prior evidence when the same base directory is reused.
            if (File.Exists(Path.Combine(folder, "qa-report.json")))
                folder = Path.Combine(folder, DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
            Directory.CreateDirectory(folder);
            var root = new GameObject("JgQaRunner_OptIn");
            DontDestroyOnLoad(root);
            root.AddComponent<JgQaRunner>().Initialize(folder);
#endif
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void SuppressGameplayForRestore()
        {
            if (!exitBeforeGameplay) return;
            foreach (var director in FindObjectsByType<GameDirector>(FindObjectsSortMode.None)) director.enabled = false;
        }

        static bool AcquireSaveMutex()
        {
            saveMutex = new Mutex(false, "JieGuangNativeQaSaveLock");
            try { ownsSaveMutex = saveMutex.WaitOne(0); }
            catch (AbandonedMutexException) { ownsSaveMutex = true; }
            if (!ownsSaveMutex) Debug.LogError("[JG-QA] Another QA/restore process owns the save lock. No save keys changed.");
            return ownsSaveMutex;
        }

        static void ReleaseSaveMutex()
        {
            if (ownsSaveMutex) { saveMutex.ReleaseMutex(); ownsSaveMutex = false; }
            saveMutex?.Dispose(); saveMutex = null;
        }

        static SaveBackup SnapshotSave()
        {
            var snapshot = new SaveBackup { values = new SavedKey[SaveKeys.Length] };
            for (int i = 0; i < SaveKeys.Length; ++i)
                snapshot.values[i] = new SavedKey { key = SaveKeys[i], existed = PlayerPrefs.HasKey(SaveKeys[i]), value = PlayerPrefs.GetInt(SaveKeys[i],0) };
            return snapshot;
        }

        static void RestoreFromFile(string path)
        {
            try
            {
                if (!Path.IsPathRooted(path)) throw new ArgumentException("Backup path must be absolute");
                var source = JsonUtility.FromJson<SaveBackup>(File.ReadAllText(path));
                var keys = new HashSet<string>(StringComparer.Ordinal);
                if (source?.values == null || source.values.Length != SaveKeys.Length) throw new ArgumentException("Backup must contain exactly the three JieGuang save keys");
                foreach (var value in source.values)
                    if (value == null || Array.IndexOf(SaveKeys,value.key) < 0 || !keys.Add(value.key)) throw new ArgumentException("Unknown or duplicate save key; nothing restored");
                var result = new RestoreResult { backupPath = Path.GetFullPath(path), before = SnapshotSave() };
                foreach (var value in source.values)
                    if (value.existed) PlayerPrefs.SetInt(value.key,value.value); else PlayerPrefs.DeleteKey(value.key);
                PlayerPrefs.Save();
                result.after = SnapshotSave(); result.verified = true;
                foreach (var value in source.values)
                    result.verified &= PlayerPrefs.HasKey(value.key) == value.existed && (!value.existed || PlayerPrefs.GetInt(value.key) == value.value);
                result.completedUtc = DateTime.UtcNow.ToString("O");
                string evidence = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(path)), "restore-result-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff") + ".json");
                File.WriteAllText(evidence, JsonUtility.ToJson(result,true));
                Debug.Log("[JG-QA] Save restore verified=" + result.verified + "; evidence=" + evidence);
                Application.Quit(result.verified ? 0 : 2);
            }
            catch (Exception ex) { Debug.LogError("[JG-QA] Save restore failed: " + ex.Message); Application.Quit(2); }
        }

        void Initialize(string folder)
        {
            output = folder;
            started = Time.realtimeSinceStartup;
            lastProgress = started;
            skipFramesUntil = started + 10f;
            report = new Report
            {
                startedUtc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion,
                os = SystemInfo.operatingSystem, cpu = SystemInfo.processorType,
                cpuThreads = SystemInfo.processorCount, systemMemoryMb = SystemInfo.systemMemorySize,
                gpu = SystemInfo.graphicsDeviceName, graphicsMemoryMb = SystemInfo.graphicsMemorySize,
                graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
                quality = QualitySettings.names[QualitySettings.GetQualityLevel()], outputDirectory = folder
            };
            backup = new SaveBackup { values = new SavedKey[SaveKeys.Length], note = "Restore these keys if the QA process is force-killed. Normal completion and Application.quitting restore automatically." };
            for (int i = 0; i < SaveKeys.Length; ++i)
                backup.values[i] = new SavedKey { key = SaveKeys[i], existed = PlayerPrefs.HasKey(SaveKeys[i]), value = PlayerPrefs.GetInt(SaveKeys[i], 0) };
            File.WriteAllText(Path.Combine(output, "save-backup.json"), JsonUtility.ToJson(backup, true));
            foreach (string key in SaveKeys) PlayerPrefs.DeleteKey(key);
            PlayerPrefs.Save();
            Application.runInBackground = true;
            Application.logMessageReceived += OnLog;
            Application.quitting += OnQuit;
            Application.quitting += ReleaseSaveMutex;
            SaveReport();
            StartCoroutine(Run());
        }

        T Read<T>(object owner, string field) where T : class => owner?.GetType().GetField(field, Private)?.GetValue(owner) as T;
        bool Flag(object owner, string field) => owner != null && owner.GetType().GetField(field, Private)?.GetValue(owner) is bool b && b;
        bool Active(string field) { var go = Read<GameObject>(ui, field); return go != null && go.activeInHierarchy; }
        string Objective => Read<Text>(ui, "stepText")?.text ?? "";
        string Dialogue => Active("dialogueRoot") ? Read<Text>(ui, "lineText")?.text ?? "" : Active("narrationRoot") ? Read<Text>(ui, "narrationText")?.text ?? "" : "";
        bool ClearWorld => ui != null && !ui.InOverlay && (Read<Image>(ui, "fade")?.color.a ?? 1f) < .08f;

        IEnumerator Run()
        {
            while (!finishing)
            {
                if (director == null) director = FindFirstObjectByType<GameDirector>();
                if (ui == null) ui = FindFirstObjectByType<GameUI>();
                if (player == null) player = FindFirstObjectByType<PlayerController>();
                if (layout == null) layout = FindFirstObjectByType<IslandLayout>();
                if (Time.realtimeSinceStartup - started > 1200f) { Finish(false, "20 minute overall timeout"); yield break; }
                if (director == null || ui == null || player == null || layout == null)
                {
                    if (Time.realtimeSinceStartup - started > 90f) { Finish(false, "Game failed to initialize within 90 s"); yield break; }
                    yield return new WaitForSecondsRealtime(.5f);
                    continue;
                }

                string state = director.Current + "|" + Objective + "|" + Dialogue + "|" + Active("mapRoot") + "|" + Active("chapterRoot") + "|" + Active("cardRoot") + "|" + Active("letterRoot") + "|" + Flag(director, "puzzleOpen");
                if (state != lastState) { lastState = state; lastProgress = Time.realtimeSinceStartup; Event("state", state); }
                if (Time.realtimeSinceStartup - lastProgress > 120f)
                {
                    yield return CaptureFrame("failure-stalled");
                    Finish(false, "No state progression for 120 s: " + state);
                    yield break;
                }

                if (Active("titleRoot"))
                {
                    report.titleSeen = true;
                    if (!captures.Contains("00-title")) { yield return new WaitForSecondsRealtime(1.6f); yield return CaptureFrame("00-title"); }
                    if (!titleStarted) { Press(Key.Enter); titleStarted = true; }
                }
                else if (Active("mapRoot"))
                {
                    // Returning through this screen is the completion signal for the prior chapter.
                    if (lastChapter > 0 && !report.completedChapters.Contains(lastChapter))
                    {
                        report.completedChapters.Add(lastChapter);
                        int unlocked = PlayerPrefs.GetInt("jieguang.unlocked", 0);
                        report.unlockValues.Add(unlocked);
                        Event("chapter-completed", "unlocked=" + unlocked);
                        if (unlocked != lastChapter && lastChapter < 7) { Finish(false, "Unexpected unlock sequence; possible concurrent save contamination: expected " + lastChapter + ", got " + unlocked); yield break; }
                        nextChapter = lastChapter + 1;
                    }
                    var map = Read<GameObject>(ui, "mapRoot");
                    var group = map.GetComponent<CanvasGroup>();
                    if (group != null && group.alpha >= .99f)
                    {
                        string mapCapture = "map-before-" + nextChapter;
                        if (!captures.Contains(mapCapture)) yield return CaptureFrame(mapCapture);
                        int selected = -1;
                        foreach (var img in map.GetComponentsInChildren<Image>())
                            if (img.enabled && img.name.StartsWith("Ring") && int.TryParse(img.name.Substring(4), out int index)) selected = index;
                        if (!mapEnterPending)
                        {
                            if (selected == nextChapter - 1) { Press(Key.Enter); mapEnterPending = true; }
                            else if (selected >= 0) Press(selected > nextChapter - 1 ? Key.LeftArrow : Key.RightArrow);
                        }
                    }
                }
                else if (Active("chapterRoot"))
                {
                    mapEnterPending = false;
                    // Chapter cards advance on their normal loading timer. Do not inject keys.
                    int chapter = (int)director.Current;
                    if (!report.enteredChapters.Contains(chapter))
                    {
                        report.enteredChapters.Add(chapter);
                        lastChapter = chapter;
                        Event("chapter-entered", chapter.ToString());
                    }
                }
                else if (Active("letterRoot"))
                {
                    if (!captures.Contains("04-letter")) { yield return new WaitForSecondsRealtime(1f); yield return CaptureFrame("04-letter"); }
                    if (!letterEntered) { Press(Key.Enter); letterEntered = true; }
                }
                else if (Active("introRoot"))
                {
                    // 开篇: capture each beat once (by its heading), then advance like dialogue
                    string heading = Read<Text>(ui, "introHeading")?.text ?? "";
                    string name = "00-intro-" + (introBeats + 1).ToString("00");
                    if (heading.Length > 0 && heading != lastIntroHeading)
                    {
                        lastIntroHeading = heading;
                        introBeats++;
                        yield return new WaitForSecondsRealtime(2.5f);
                        yield return CaptureFrame(name);
                    }
                    Press(Key.Space);
                }
                else if (Active("cardRoot"))
                {
                    string text = Read<Text>(ui, "cardText")?.text ?? "";
                    if (director.Current == Chapter.Epilogue && text == StoryText.EpilogueClosing)
                    {
                        report.epilogueClosingSeen = true;
                        yield return new WaitForSecondsRealtime(1f);
                        yield return CaptureFrame("07-epilogue-closing");
                        report.completedChapters.Add(7);
                        Press(Key.Enter);
                        yield return new WaitForSecondsRealtime(1.5f);
                        Finish(true, "Normal title-to-epilogue progression completed; diagnostic travel only");
                        yield break;
                    }
                    string name = ((int)director.Current).ToString("00") + "-chapter-end-card";
                    if (!captures.Contains(name)) { yield return new WaitForSecondsRealtime(.9f); yield return CaptureFrame(name); }
                    var group = Read<GameObject>(ui,"cardRoot").GetComponent<CanvasGroup>();
                    if (advancedCard != text && (group == null || group.alpha >= .99f)) { Press(Key.Enter); advancedCard = text; }
                }
                else if (Flag(director, "puzzleOpen"))
                {
                    yield return SolvePuzzle();
                }
                else
                {
                    int chapter = (int)director.Current;
                    if (chapter > 0 && ClearWorld && !captures.Contains(chapter.ToString("00") + "-normal"))
                    {
                        yield return new WaitForSecondsRealtime(1.2f);
                        yield return CaptureFrame(chapter.ToString("00") + "-normal");
                        // An explicit short static sample, separately described in the report.
                        Event("static-sample-start", "8 seconds; no input/capture/teleport");
                        yield return new WaitForSecondsRealtime(8f);
                        Event("static-sample-end", "8 seconds");
                    }
                    if (Active("dialogueRoot") || Active("narrationRoot"))
                    {
                        string beat = StoryEvidenceName();
                        if (beat != null && !captures.Contains(beat)) { yield return new WaitForSecondsRealtime(1f); yield return CaptureFrame(beat); }
                        Press(Key.Space);
                    }
                    else if (player.InputEnabled && ClearWorld) TravelOrInteract();
                }
                SaveReport();
                yield return new WaitForSecondsRealtime(.5f);
            }
        }

        int introBeats;
        string lastIntroHeading = "";

        string StoryEvidenceName()
        {
            string line = Dialogue;
            if (director.Current == Chapter.Prologue && line.Contains("我的光分你一半")) return "01-sharing-light";
            if (director.Current == Chapter.One && line.Contains("我年轻时也不会发光")) return "02-postman-bench-cane";
            if (director.Current == Chapter.Two && line.Contains("照得正好")) return "03-window-lit-grandmother";
            if (director.Current == Chapter.Interlude && line.Contains("阿萤临走那天")) return "04-folded-letter-prop";
            if (director.Current == Chapter.Three && line.Contains("可灯不用最亮")) return "05-dengbo-seated";
            if (director.Current == Chapter.Three && line.Contains("他退后两步")) return "05-lantern-hung";
            if (director.Current == Chapter.Finale && line.Contains("她低头看见了他的手")) return "06-reunion-hands";
            if (director.Current == Chapter.Finale && line.Contains("开出了第一朵花")) return "06-first-flower";
            return null;
        }

        void TravelOrInteract()
        {
            string objective = Objective;
            if (director.Current == Chapter.One && objective.Contains("路口有人"))
            {
                var npc = Read<CharacterActor>(director, "postman");
                Near(npc.transform.position + npc.transform.forward * 1.2f, npc.transform.position);
                Press(Key.E);
            }
            else if ((director.Current == Chapter.One || director.Current == Chapter.Two || director.Current == Chapter.Three)
                     && objective == StoryText.Objective(director.Current)) Press(Key.Tab);
            else if (director.Current == Chapter.Interlude && objective.Contains("金色光树"))
            {
                Vector3 target = layout.Pos("Anchor_GoldenTree");
                Near(target + DirectionToSpawn(target) * 2.4f, target);
            }
            else if (director.Current == Chapter.Three && objective.Contains("跑到码头"))
            {
                Vector3 pier = layout.Pos("Target_Pier");
                Vector3 axis = layout.Pos("Anchor_FlagpoleHook") - pier; axis.y = 0f; axis.Normalize();
                Near(pier - axis * 3f, pier);
            }
            else if (director.Current == Chapter.Three && objective.Contains("找灯伯"))
            {
                var npc = Read<CharacterActor>(director, "dengbo");
                Near(npc.transform.position + npc.transform.forward * 1.1f, npc.transform.position);
                Press(Key.E);
            }
            else if (director.Current == Chapter.Three && objective.Contains("旗杆上"))
            {
                Vector3 hook = layout.Pos("Anchor_FlagpoleHook");
                Vector3 axis = hook - layout.Pos("Target_Pier"); axis.y = 0f; axis.Normalize();
                Vector3 pos = hook - axis * .9f; pos.y = layout.Pos("NPC_DengBo_Box").y;
                Near(pos, hook);
                Press(Key.E);
            }
            else if (director.Current == Chapter.Epilogue && epilogueIndex < EpilogueActors.Length && Time.realtimeSinceStartup > nextEpilogueVisit)
            {
                string who = EpilogueActors[epilogueIndex++];
                var npc = Read<CharacterActor>(director, who);
                Near(npc.transform.position + npc.transform.forward * 1.3f, npc.transform.position);
                report.epilogueVisited.Add(who);
                nextEpilogueVisit = Time.realtimeSinceStartup + 7f;
                Event("epilogue-visit", who);
            }
        }

        Vector3 DirectionToSpawn(Vector3 from)
        {
            Vector3 d = layout.Pos("Anchor_PlayerSpawn") - from; d.y = 0f;
            return d.sqrMagnitude > .01f ? d.normalized : Vector3.back;
        }

        void Near(Vector3 position, Vector3 lookAt)
        {
            if (Vector3.Distance(player.transform.position, position) < .3f) return;
            if (Physics.Raycast(position + Vector3.up * 3f, Vector3.down, out var hit, 6f, ~(1 << 2), QueryTriggerInteraction.Ignore)) position.y = hit.point.y;
            Vector3 facing = lookAt - position; facing.y = 0f;
            player.Teleport(position + Vector3.up * .04f, facing.sqrMagnitude > .01f ? Quaternion.LookRotation(facing).eulerAngles.y : 0f);
            skipFramesUntil = Time.realtimeSinceStartup + 1f;
            Event("diagnostic-teleport", position.ToString("F3"));
        }

        IEnumerator SolvePuzzle()
        {
            Chapter chapter = director.Current;
            string stem = ((int)chapter).ToString("00") + "-puzzle";
            if (!captures.Contains(stem + "-before")) yield return CaptureFrame(stem + "-before");
            Key[] keys = chapter == Chapter.One ? new[] { Key.D, Key.Space }
                : chapter == Chapter.Two ? new[] { Key.Digit2, Key.D, Key.Space }
                : new[] { Key.Digit3, Key.D, Key.Digit2, Key.D, Key.Space, Key.Digit1, Key.Space };
            foreach (var key in keys) { Press(key); yield return new WaitForSecondsRealtime(.5f); }
            var settings = Read<LampSetting[]>(director, "settings");
            var result = LampRules.Evaluate(chapter, settings);
            Event("puzzle-evaluated", "solved=" + result.Solved + "; covered=" + result.Covered + "; skyLoss=" + result.SkyLoss);
            if (!result.Solved) { Finish(false, "Actual key sequence did not solve " + chapter); yield break; }
            report.puzzleSolvedThroughInput.Add((int)chapter);
            yield return CaptureFrame(stem + "-solved");
            Press(Key.Enter);
            yield return new WaitForSecondsRealtime(.5f);
        }

        void Press(Key key) { GameInput.Queue(key); Event("key", key.ToString()); }

        IEnumerator CaptureFrame(string name)
        {
            if (!captures.Add(name)) yield break;
            skipFramesUntil = Time.realtimeSinceStartup + 1.5f;
            yield return new WaitForEndOfFrame();
            string path = Path.Combine(output, name + ".png");
            ScreenCapture.CaptureScreenshot(path);
            var capture = new Capture { name = name, path = path, chapter = director != null ? director.Current.ToString() : "boot", objective = Objective, screenWidth = Screen.width, screenHeight = Screen.height };
            float until = Time.realtimeSinceStartup + 5f;
            while (!File.Exists(path) && Time.realtimeSinceStartup < until) yield return null;
            capture.saved = File.Exists(path);
            if (capture.saved)
            {
                yield return new WaitForSecondsRealtime(.25f);
                try
                {
                    byte[] data = File.ReadAllBytes(path);
                    if (data.Length >= 24) { capture.pngWidth = BigInt(data,16); capture.pngHeight = BigInt(data,20); }
                    capture.saved = capture.pngWidth > 0 && capture.pngHeight > 0;
                }
                catch (IOException) { capture.saved = false; }
            }
            report.screenshots.Add(capture);
            Event("screenshot", name + "; saved=" + capture.saved);
            SaveReport();
            skipFramesUntil = Time.realtimeSinceStartup + 1f;
        }

        static int BigInt(byte[] b, int i) => (b[i] << 24) | (b[i+1] << 16) | (b[i+2] << 8) | b[i+3];

        void Update()
        {
            if (report == null || finishing || director == null || !ClearWorld || Time.realtimeSinceStartup < skipFramesUntil) return;
            int chapter = (int)director.Current;
            if (chapter < 1) return;
            if (!chapterFrames.TryGetValue(chapter, out var samples)) chapterFrames[chapter] = samples = new List<float>();
            samples.Add(Time.unscaledDeltaTime * 1000f);
            // CPU main thread vs GPU time (needs Frame Timing Stats in Player Settings)
            FrameTimingManager.CaptureFrameTimings();
            if (FrameTimingManager.GetLatestTimings(1, timing) > 0)
            {
                if (!chapterTimings.TryGetValue(chapter, out var t)) chapterTimings[chapter] = t = new List<Vector3>();
                t.Add(new Vector3((float)timing[0].cpuMainThreadFrameTime, (float)timing[0].gpuFrameTime, AdaptiveResolution.CurrentScale));
            }
        }
        readonly FrameTiming[] timing = new FrameTiming[1];
        readonly Dictionary<int, List<Vector3>> chapterTimings = new Dictionary<int, List<Vector3>>();

        void Event(string action, string detail)
        {
            var e = new InputEvent { seconds = Time.realtimeSinceStartup - started, chapter = director != null ? director.Current.ToString() : "boot", action = action, detail = detail, objective = Objective, dialogue = Dialogue };
            File.AppendAllText(Path.Combine(output, "events.jsonl"), JsonUtility.ToJson(e) + "\n");
        }

        void OnLog(string message, string stack, LogType type)
        {
            if (type != LogType.Error && type != LogType.Exception && type != LogType.Assert) return;
            report.errors.Add(new ErrorRecord { type = type.ToString(), message = message, stack = stack, seconds = Time.realtimeSinceStartup - started });
        }

        void SaveReport()
        {
            report.actualWidth = Screen.width; report.actualHeight = Screen.height;
            report.targetFps = Application.targetFrameRate; report.vSync = QualitySettings.vSyncCount;
            report.frames.Clear();
            foreach (var kv in chapterFrames)
            {
                if (kv.Value.Count == 0) continue;
                var values = kv.Value.ToArray(); Array.Sort(values);
                double total = 0; foreach (float value in values) total += value;
                float p95 = Percentile(values, .95f);
                report.frames.Add(new FrameSummary { scope = "chapter-" + kv.Key + " normal rendered frames; static/cutscene/diagnostic travel sample", samples = values.Length, measuredSeconds = (float)total / 1000f,
                    p50Ms = Percentile(values,.5f), p95Ms = p95, p99Ms = Percentile(values,.99f), meanFps = (float)(values.Length * 1000d / total), p95EquivalentFps = p95 > 0 ? 1000f / p95 : 0,
                    cpuMainP50Ms = TimingP50(kv.Key, 0), gpuP50Ms = TimingP50(kv.Key, 1), renderScaleMean = TimingMean(kv.Key, 2) });
            }
            File.WriteAllText(Path.Combine(output, "qa-report.json"), JsonUtility.ToJson(report, true));
        }

        float TimingP50(int chapter, int axis)
        {
            if (!chapterTimings.TryGetValue(chapter, out var t) || t.Count == 0) return -1f;
            var v = new float[t.Count]; for (int i = 0; i < v.Length; i++) v[i] = t[i][axis];
            Array.Sort(v); return Percentile(v, .5f);
        }
        float TimingMean(int chapter, int axis)
        {
            if (!chapterTimings.TryGetValue(chapter, out var t) || t.Count == 0) return -1f;
            float sum = 0; foreach (var x in t) sum += x[axis]; return sum / t.Count;
        }

        static float Percentile(float[] values, float p) => values[Mathf.Clamp(Mathf.CeilToInt(values.Length * p) - 1,0,values.Length-1)];

        void Finish(bool success, string reason)
        {
            if (finishing) return;
            finishing = true;
            bool allShots = true; foreach (var capture in report.screenshots) allShots &= capture.saved;
            report.status = success && report.errors.Count == 0 && allShots ? "passed-automated-flow" : "failed";
            report.reason = reason;
            report.completedUtc = DateTime.UtcNow.ToString("O");
            RestoreSave();
            SaveReport();
            Application.Quit(report.status == "passed-automated-flow" ? 0 : 2);
        }

        void RestoreSave()
        {
            if (restored || backup == null) return;
            foreach (var value in backup.values)
                if (value.existed) PlayerPrefs.SetInt(value.key,value.value); else PlayerPrefs.DeleteKey(value.key);
            PlayerPrefs.Save(); restored = true; report.saveRestored = true;
        }

        void OnQuit()
        {
            if (report == null) return;
            RestoreSave();
            if (!finishing) { report.status = "interrupted"; report.reason = "Application quit before automated flow completed"; }
            SaveReport();
        }

        void OnDestroy()
        {
            Application.logMessageReceived -= OnLog;
            Application.quitting -= OnQuit;
            RestoreSave();
            ReleaseSaveMutex();
        }
    }
}
