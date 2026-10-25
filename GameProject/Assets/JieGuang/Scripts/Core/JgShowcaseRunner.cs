using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace JieGuang
{
    // Review-video playthrough (Editor only, opt-in through the JieGuang/Record Review Video menu).
    // It plays the real game from the title to the epilogue through the same GameInput keys as the
    // QA runner, but in game time and at a watchable pace, holding each line after it has finished
    // typing, fading around the diagnostic teleports and adding short captions for the judges.
    public sealed class JgShowcaseRunner : MonoBehaviour
    {
        public static bool Finished { get; private set; }
        public static bool Ending { get; private set; }
        public static string StillRequest;   // the recorder saves the next frame under this name
        public static bool Fast { get; private set; } // condensed edition: lines complete at once, shorter holds
        // Highlights edition: the recorder only writes frames while Recording is true, so the
        // video is cut live to the opening, chapter cards, key lines, puzzles and the ending.
        public static bool Highlights { get; private set; }
        public static bool Recording { get; private set; } = true;

        const BindingFlags Private = BindingFlags.Instance | BindingFlags.NonPublic;
        const string Flag = "jieguang.showcase";
        static readonly string[] SaveKeys = { "jieguang.chapter", "jieguang.unlocked", "jieguang.debugStart" };
        static readonly string[] EpilogueActors = { "aying", "postman", "abo", "dengbo" };

        GameDirector director;
        GameUI ui;
        PlayerController player;
        IslandLayout layout;
        readonly bool[] existed = new bool[3];
        readonly int[] saved = new int[3];
        readonly HashSet<string> stills = new HashSet<string>();
        readonly HashSet<int> captioned = new HashSet<int>();
        int nextChapter = 1, lastChapter, epilogueIndex, introBeats;
        bool titleStarted, mapEnterPending, letterEntered, restored;
        string advancedCard, lastIntroHeading = "", lastLine = "";
        float lineTypedAt = -1f;
        string typingLine = "";
        bool lineKept = true;

        // caption overlay
        CanvasGroup captionGroup, cardGroup;
        Text captionTitle, captionBody, cardTitle, cardBody;

#if UNITY_EDITOR
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Bootstrap()
        {
            int mode = PlayerPrefs.GetInt(Flag, 0);
            if (mode < 1 || mode > 3) return;
            PlayerPrefs.DeleteKey(Flag);
            Fast = mode >= 2;
            Highlights = mode == 3;
            Recording = true;
            Finished = false;
            Ending = false;
            var go = new GameObject("JgShowcaseRunner");
            DontDestroyOnLoad(go);
            go.AddComponent<JgShowcaseRunner>();
        }
#endif

        void Awake()
        {
            for (int i = 0; i < SaveKeys.Length; i++) { existed[i] = PlayerPrefs.HasKey(SaveKeys[i]); saved[i] = PlayerPrefs.GetInt(SaveKeys[i], 0); }
            foreach (var k in SaveKeys) PlayerPrefs.DeleteKey(k);
            PlayerPrefs.Save();
            Application.runInBackground = true;
            BuildOverlay();
            StartCoroutine(Run());
        }

        void Restore()
        {
            if (restored) return;
            for (int i = 0; i < SaveKeys.Length; i++) { if (existed[i]) PlayerPrefs.SetInt(SaveKeys[i], saved[i]); else PlayerPrefs.DeleteKey(SaveKeys[i]); }
            PlayerPrefs.Save();
            restored = true;
        }

        void OnDestroy() => Restore();

        // ------------------------------------------------------------------ reflection helpers
        T Read<T>(object owner, string field) where T : class => owner?.GetType().GetField(field, Private)?.GetValue(owner) as T;
        bool FlagOf(object owner, string field) => owner != null && owner.GetType().GetField(field, Private)?.GetValue(owner) is bool b && b;
        bool Active(string field) { var go = Read<GameObject>(ui, field); return go != null && go.activeInHierarchy; }
        string Objective => Read<Text>(ui, "stepText")?.text ?? "";
        string Dialogue => Active("dialogueRoot") ? Read<Text>(ui, "lineText")?.text ?? "" : Active("narrationRoot") ? Read<Text>(ui, "narrationText")?.text ?? "" : "";
        bool LineTyped { get { var star = Read<Image>(ui, "continueStar"); return star != null && star.enabled; } }
        bool ClearWorld => ui != null && !ui.InOverlay && (Read<Image>(ui, "fade")?.color.a ?? 1f) < .08f;
        static WaitForSeconds Wait(float s) => new WaitForSeconds(s);
        void Press(Key key) => GameInput.Queue(key);
        void Still(string name) { if (!Fast && stills.Add(name)) StillRequest = name; }
        float Pace(float normal, float fast) => Fast ? fast : normal;
        void Rec(bool on) { if (Highlights) Recording = on; }
        readonly Dictionary<int, int> linesShown = new Dictionary<int, int>();
        float idleSince = -1f;
        static readonly string[] KeyLines =
        {
            "我的光分你一半", "等我回来", "灯不用你照亮", "我年轻时也不会发光", "路是一段一段走的",
            "照得正好", "树不跟树比", "光灭了", "阿萤临走那天", "先把灯放低", "可灯不用最亮", "他退后两步",
            "看见了自己的手", "她低头看见了他的手", "只认得这一盏", "开出了第一朵花",
        };

        // ------------------------------------------------------------------ flow
        IEnumerator Run()
        {
            yield return OpeningCard();
            float started = Time.time;
            while (true)
            {
                if (director == null) director = FindFirstObjectByType<GameDirector>();
                if (ui == null) ui = FindFirstObjectByType<GameUI>();
                if (player == null) player = FindFirstObjectByType<PlayerController>();
                if (layout == null) layout = FindFirstObjectByType<IslandLayout>();
                if (director == null || ui == null || player == null || layout == null) { yield return null; continue; }
                if (Time.time - started > 1500f) break;

                if (Active("titleRoot"))
                {
                    if (!titleStarted) { Rec(true); yield return Wait(4.5f); Still("01-title"); yield return Wait(0.5f); Press(Key.Enter); titleStarted = true; Rec(false); }
                }
                else if (Active("mapRoot"))
                {
                    if (lastChapter > 0 && nextChapter <= lastChapter) nextChapter = lastChapter + 1;
                    var map = Read<GameObject>(ui, "mapRoot");
                    var group = map.GetComponent<CanvasGroup>();
                    if (group != null && group.alpha >= .99f && !mapEnterPending)
                    {
                        int selected = -1;
                        foreach (var img in map.GetComponentsInChildren<Image>())
                            if (img.enabled && img.name.StartsWith("Ring") && int.TryParse(img.name.Substring(4), out int index)) selected = index;
                        if (selected == nextChapter - 1)
                        {
                            if (nextChapter == 1) Rec(true);
                            yield return Wait(nextChapter == 1 ? 2.5f : 1.6f);
                            if (nextChapter == 1) Still("02-journey-map");
                            Press(Key.Enter);
                            Rec(false);
                            mapEnterPending = true;
                        }
                        else if (selected >= 0) { Press(selected > nextChapter - 1 ? Key.LeftArrow : Key.RightArrow); yield return Wait(0.4f); }
                    }
                }
                else if (Active("chapterRoot"))
                {
                    mapEnterPending = false;
                    lastChapter = (int)director.Current;
                    Rec(true);
                }
                else if (Active("letterRoot"))
                {
                    if (!letterEntered) { Rec(true); yield return Wait(2f); Still("10-letter"); yield return Wait(Pace(5f, 3f)); Press(Key.Enter); letterEntered = true; Rec(false); }
                }
                else if (Active("introRoot"))
                {
                    yield return IntroBeat();
                }
                else if (Active("cardRoot"))
                {
                    string text = Read<Text>(ui, "cardText")?.text ?? "";
                    var group = Read<GameObject>(ui, "cardRoot").GetComponent<CanvasGroup>();
                    if (advancedCard != text && (group == null || group.alpha >= .99f))
                    {
                        advancedCard = text;
                        Rec(true);
                        yield return Wait(Fast ? Mathf.Clamp(1.2f + text.Length * 0.04f, 2.2f, 4f) : Mathf.Clamp(1.6f + text.Length * 0.07f, 3f, 6.5f));
                        if (director.Current == Chapter.Epilogue && text == StoryText.EpilogueClosing)
                        {
                            Press(Key.Enter);
                            yield return Wait(1.5f);
                            break;
                        }
                        Press(Key.Enter);
                    }
                }
                else if (FlagOf(director, "puzzleOpen"))
                {
                    yield return Puzzle();
                }
                else
                {
                    int chapter = (int)director.Current;
                    if (chapter > 0 && ClearWorld && !captioned.Contains(chapter) && (Active("dialogueRoot") || Active("narrationRoot") || player.InputEnabled))
                    {
                        captioned.Add(chapter);
                        StartCoroutine(Caption(ChapterCaption(director.Current)));
                    }
                    if (Active("dialogueRoot") || Active("narrationRoot"))
                    {
                        idleSince = -1f;
                        yield return HoldLine();
                    }
                    else
                    {
                        // a cutscene with no line on screen: keep at most 2.5 s of it in the highlights
                        if (idleSince < 0f) idleSince = Time.time;
                        else if (Time.time - idleSince > 2.5f) Rec(false);
                        if (player.InputEnabled && ClearWorld)
                            yield return TravelOrInteract();
                    }
                }
                yield return null;
            }
            yield return EndCard();
            Restore();
            Finished = true;
        }

        IEnumerator HoldLine()
        {
            string line = Dialogue;
            if (!LineTyped)
            {
                if (Highlights) Rec(false);
                if (Fast && line.Length > 0 && line != typingLine) { typingLine = line; yield return Wait(Highlights ? 0.15f : 0.5f); Press(Key.Space); }
                yield return null;
                yield break;
            }
            bool keep;
            if (line != lastLine)
            {
                lastLine = line; lineTypedAt = Time.time; StillForLine(line);
                int c = (int)director.Current;
                linesShown.TryGetValue(c, out int n);
                linesShown[c] = n + 1;
                keep = n < 2 || System.Array.Exists(KeyLines, k => line.Contains(k));
                lineKept = keep;
                Rec(keep);
            }
            else keep = lineKept;
            float hold = Highlights && !keep ? 0.25f : Fast ? Mathf.Clamp(0.6f + line.Length * 0.035f, 1.3f, 3.0f) : Mathf.Clamp(0.9f + line.Length * 0.06f, 1.8f, 5.2f);
            if (Time.time - lineTypedAt >= hold) { Press(Key.Space); lastLine = ""; yield return Wait(0.15f); }
        }

        void StillForLine(string line)
        {
            var c = director.Current;
            if (c == Chapter.Prologue && line.Contains("我的光分你一半")) Still("05-sharing-light");
            else if (c == Chapter.One && line.Contains("我年轻时也不会发光")) Still("07-postman-bench");
            else if (c == Chapter.Two && line.Contains("照得正好")) Still("09-round-window");
            else if (c == Chapter.Three && line.Contains("可灯不用最亮")) Still("11-dengbo");
            else if (c == Chapter.Three && line.Contains("他退后两步")) Still("12-lantern-hung");
            else if (c == Chapter.Finale && line.Contains("她低头看见了他的手")) Still("13-reunion");
            else if (c == Chapter.Finale && line.Contains("开出了第一朵花")) Still("14-first-flower");
        }

        IEnumerator IntroBeat()
        {
            var body = Read<Text>(ui, "introBody");
            string heading = Read<Text>(ui, "introHeading")?.text ?? "";
            if (heading.Length == 0 || body == null) { yield return null; yield break; }
            if (heading != lastIntroHeading) { lastIntroHeading = heading; introBeats++; Rec(introBeats <= 6); }
            // typing has finished once the text stops changing for a moment
            string before = body.text;
            yield return Wait(0.9f);
            if (body.text != before || body.text.Length == 0) yield break;
            if (introBeats == 1 || introBeats == 2 || introBeats == 7 || introBeats == 11) Still("03-opening-" + introBeats.ToString("00"));
            Rec(true);
            yield return Wait(Fast ? Mathf.Clamp(body.text.Length * 0.018f, 1.2f, 2.2f) : Mathf.Clamp(body.text.Length * 0.03f, 1.6f, 3.4f));
            Press(Key.Space);
            yield return Wait(1.2f);
        }

        IEnumerator Puzzle()
        {
            Chapter chapter = director.Current;
            Rec(true);
            StartCoroutine(Caption(PuzzleCaption(chapter)));
            yield return Wait(2.2f);
            Still(chapter == Chapter.One ? "06-puzzle-chapter1" : chapter == Chapter.Two ? "08-puzzle-chapter2" : "11-puzzle-chapter3");
            Key[] keys = chapter == Chapter.One ? new[] { Key.D, Key.Space }
                : chapter == Chapter.Two ? new[] { Key.Digit2, Key.D, Key.Space }
                : new[] { Key.Digit3, Key.D, Key.Digit2, Key.D, Key.Space, Key.Digit1, Key.Space };
            foreach (var key in keys) { Press(key); yield return Wait(Pace(1.3f, 0.9f)); }
            yield return Wait(Pace(1.6f, 1.2f));
            Press(Key.Enter);
            yield return Wait(1f);
            Rec(false);
        }

        IEnumerator TravelOrInteract()
        {
            string objective = Objective;
            var c = director.Current;
            if (c == Chapter.One && objective.Contains("路口有人"))
            {
                var npc = Read<CharacterActor>(director, "postman");
                yield return Near(npc.transform.position + npc.transform.forward * 1.2f, npc.transform.position);
                Press(Key.E);
            }
            else if ((c == Chapter.One || c == Chapter.Two || c == Chapter.Three) && objective == StoryText.Objective(c))
            {
                yield return Wait(1.5f);
                Press(Key.Tab);
            }
            else if (c == Chapter.Interlude && objective.Contains("金色光树"))
            {
                Vector3 target = layout.Pos("Anchor_GoldenTree");
                yield return Near(target + DirectionToSpawn(target) * 2.4f, target);
            }
            else if (c == Chapter.Three && objective.Contains("跑到码头"))
            {
                Vector3 pier = layout.Pos("Target_Pier");
                Vector3 axis = layout.Pos("Anchor_FlagpoleHook") - pier; axis.y = 0f; axis.Normalize();
                yield return Near(pier - axis * 3f, pier);
            }
            else if (c == Chapter.Three && objective.Contains("找灯伯"))
            {
                var npc = Read<CharacterActor>(director, "dengbo");
                yield return Near(npc.transform.position + npc.transform.forward * 1.1f, npc.transform.position);
                Press(Key.E);
            }
            else if (c == Chapter.Three && objective.Contains("旗杆上"))
            {
                Vector3 hook = layout.Pos("Anchor_FlagpoleHook");
                Vector3 axis = hook - layout.Pos("Target_Pier"); axis.y = 0f; axis.Normalize();
                Vector3 pos = hook - axis * .9f; pos.y = layout.Pos("NPC_DengBo_Box").y;
                yield return Near(pos, hook);
                Press(Key.E);
            }
            else if (c == Chapter.Epilogue && epilogueIndex < EpilogueActors.Length)
            {
                if (epilogueIndex == 0) { yield return Wait(2.5f); Still("15-epilogue"); }
                var npc = Read<CharacterActor>(director, EpilogueActors[epilogueIndex++]);
                yield return Near(npc.transform.position + npc.transform.forward * 1.3f, npc.transform.position);
                if (epilogueIndex == 1 || epilogueIndex == 3) Rec(true);
                yield return Wait(Highlights && epilogueIndex != 1 && epilogueIndex != 3 ? 2.2f : Pace(5.5f, 3.2f));
                Rec(false);
            }
        }

        Vector3 DirectionToSpawn(Vector3 from)
        {
            Vector3 d = layout.Pos("Anchor_PlayerSpawn") - from; d.y = 0f;
            return d.sqrMagnitude > .01f ? d.normalized : Vector3.back;
        }

        // A short dip to black hides the jump of a diagnostic teleport in the video.
        IEnumerator Near(Vector3 position, Vector3 lookAt)
        {
            if (Vector3.Distance(player.transform.position, position) < .3f) yield break;
            Rec(false);
            if (Physics.Raycast(position + Vector3.up * 3f, Vector3.down, out var hit, 6f, ~(1 << 2), QueryTriggerInteraction.Ignore)) position.y = hit.point.y;
            Vector3 facing = lookAt - position; facing.y = 0f;
            yield return ui.FadeTo(1f, 0.35f);
            player.Teleport(position + Vector3.up * .04f, facing.sqrMagnitude > .01f ? Quaternion.LookRotation(facing).eulerAngles.y : 0f);
            yield return Wait(0.35f);
            yield return ui.FadeTo(0f, 0.45f);
        }

        // ------------------------------------------------------------------ captions for the judges
        static (string, string) ChapterCaption(Chapter c)
        {
            switch (c)
            {
                case Chapter.Prologue: return ("序章 · 长夜将至", "长夜前一天，阿萤随采光船出海，把自己的光分给了不会发光的小灯笼。");
                case Chapter.One: return ("第一章 · 山路上的铃铛", "晚风灯的灯头歪了，光漏向天空。帮邮差爷爷把光照回回家的小路。");
                case Chapter.Two: return ("第二章 · 荒原上的窗", "阿婆的圆窗是黑的。用一束不多也不少的光照亮它，听阿婆讲种下第一片光树的往事。");
                case Chapter.Interlude: return ("幕间 · 熄灯", "船没有按时回来。小灯笼吹熄了灯笼，读到阿萤留下的萤火虫形状的信。");
                case Chapter.Three: return ("第三章 · 长夜里，船还没回来", "大家把灯举得太高，夜空被照白，海上的船看不见星星。四个地方，只有三盏灯。");
                case Chapter.Finale: return ("终章 · 夜空里，多了一颗星", "在完全的黑暗里，小灯笼第一次看见自己的手在发光：光是给出去，才长出来的。");
                default: return ("尾声 · 长夜之后", "沿着小路走走，听岛上的人说说话。");
            }
        }

        static (string, string) PuzzleCaption(Chapter c)
        {
            switch (c)
            {
                case Chapter.One: return ("玩法 · 调灯", "数字键选灯，A / D 转动灯头，空格切换宽、窄灯罩。照亮需要的地方，漏到天上的光越少越好。");
                case Chapter.Two: return ("玩法 · 取舍", "宽光照得广却会漏光，窄光集中却照不全：两盏灯要同时守住路口和圆窗。");
                default: return ("玩法 · 把光照对地方", "四个地方、三盏灯、只能有一束宽光。光污染越少，夜空越黑，船越能看见星星回家。");
            }
        }

        void BuildOverlay()
        {
            var go = new GameObject("ShowcaseOverlay");
            go.transform.SetParent(transform, false);
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 40;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;
            var root = (RectTransform)go.transform;

            // lower-left explanatory caption
            var cap = UiKit.Rect(root, "Caption", new Vector2(0f, 0f), new Vector2(70f, 250f), new Vector2(980f, 150f), new Vector2(0f, 0f));
            captionGroup = cap.gameObject.AddComponent<CanvasGroup>();
            captionGroup.alpha = 0f;
            var wash = UiKit.Image(cap, "Wash", UiKit.HGradient, new Color(0f, 0.01f, 0.04f, 0.72f), new Vector2(0f, 0.5f), new Vector2(-70f, 0f), new Vector2(1180f, 170f));
            wash.rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.Image(cap, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 1f), new Vector2(10f, -26f), new Vector2(24f, 24f));
            captionTitle = UiKit.Text(cap, "Title", "", 28, UiKit.Gold, TextAnchor.MiddleLeft, new Vector2(0f, 1f), new Vector2(34f, -26f), new Vector2(900f, 42f));
            captionTitle.rectTransform.pivot = new Vector2(0f, 0.5f);
            captionBody = UiKit.Text(cap, "Body", "", 26, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(34f, -56f), new Vector2(900f, 100f));
            captionBody.rectTransform.pivot = new Vector2(0f, 1f);
            captionBody.lineSpacing = 1.3f;

            // full-screen title / end card
            var card = UiKit.Stretch(root, "Card");
            cardGroup = card.gameObject.AddComponent<CanvasGroup>();
            cardGroup.alpha = 0f;
            var black = card.gameObject.AddComponent<Image>();
            black.color = new Color(0.01f, 0.015f, 0.035f, 1f);
            UiKit.GoldRule(card, "Rule", new Vector2(0.5f, 0.5f), new Vector2(0f, 30f), 420f);
            cardTitle = UiKit.Text(card, "Title", "", 96, UiKit.Ivory, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(0f, 120f), new Vector2(1400f, 140f));
            cardBody = UiKit.Text(card, "Body", "", 28, UiKit.Ivory, TextAnchor.UpperCenter, new Vector2(0.5f, 0.5f), new Vector2(0f, 0f), new Vector2(1500f, 400f));
            cardBody.rectTransform.pivot = new Vector2(0.5f, 1f); // starts below the gold rule
            cardBody.lineSpacing = 1.5f;
        }

        IEnumerator Fade(CanvasGroup g, float to, float seconds)
        {
            float from = g.alpha;
            for (float t = 0f; t < 1f; t += Time.deltaTime / seconds) { g.alpha = Mathf.Lerp(from, to, Mathf.SmoothStep(0f, 1f, t)); yield return null; }
            g.alpha = to;
        }

        IEnumerator Caption((string title, string body) c)
        {
            captionTitle.text = UiKit.Track(c.title);
            captionBody.text = c.body;
            yield return Fade(captionGroup, 1f, 0.6f);
            yield return Wait(Fast ? Mathf.Clamp(c.body.Length * 0.09f, 3.5f, 5.5f) : Mathf.Clamp(c.body.Length * 0.12f, 4.5f, 7.5f));
            yield return Fade(captionGroup, 0f, 0.6f);
        }

        IEnumerator OpeningCard()
        {
            cardTitle.text = UiKit.Track("借光岛");
            cardBody.text = UiKit.Track("作品评审视频") + "\n\n原创剧情冒险 · Unity 6（URP）· Windows / WebGL";
            cardGroup.alpha = 1f;
            yield return Wait(4.2f);
            Still("00-title-card");
            yield return Fade(cardGroup, 0f, 1.2f);
        }

        IEnumerator EndCard()
        {
            Recording = true;
            Ending = true;
            cardTitle.text = UiKit.Track("借光岛");
            cardBody.text = "你不必是最亮的那一盏。借来的光照亮了别人，就成了自己的光。\n\n"
                          + "引擎：Unity 6（URP）　建模：Tripo + Blender　动作：Mixamo\n"
                          + "剧本、代码与美术流程：人机协作（Claude Opus 5.5 / GPT）\n\n感谢观看";
            yield return Fade(cardGroup, 1f, 1.2f);
            yield return Wait(1f);
            Still("16-end-card");
            yield return Wait(5.5f);
        }
    }
}
