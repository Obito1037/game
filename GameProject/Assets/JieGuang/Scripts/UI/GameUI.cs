using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;

namespace JieGuang
{
    // All screens of 《借光岛》, styled after the storybook reference: title page, parchment journey
    // map, starfield chapter card, quiet HUD (gold sparkle quest + step, in-world key prompts and
    // distance markers), gold-edged dialogue, narration cards, the letter, the lamp panel and pause.
    public sealed class GameUI : MonoBehaviour
    {
        public enum PauseChoice { Resume, Map, Title, ClearProgress }

        RectTransform canvas;
        Camera worldCam;
        Image fade;

        // HUD
        CanvasGroup hudGroup;
        RectTransform questRoot, promptRoot, markerRoot;
        Text questText, stepText, hintText, promptText, markerText, toastText;
        Image questStar;
        Vector3? promptWorld, markerWorld;
        string markerLabel;
        float toastUntil;
        CanvasGroup toastGroup;

        // dialogue
        GameObject dialogueRoot, narrationRoot;
        RectTransform namePill;
        Text nameText, lineText, narrationText;
        Image continueStar;

        // overlays
        GameObject cardRoot, letterRoot, lampPanel, keyLegend, titleRoot, mapRoot, chapterRoot, pauseRoot;
        Text cardText, letterBody, lampText;
        Button letterButton;
        int lastAdvanceFrame = -1;

        public bool InOverlay => (introRoot != null && introRoot.activeSelf) || cardRoot.activeSelf || letterRoot.activeSelf || mapRoot.activeSelf || chapterRoot.activeSelf || titleRoot.activeSelf || pauseRoot.activeSelf;

        public static GameUI Create()
        {
            var go = new GameObject("UI");
            var ui = go.AddComponent<GameUI>();
            ui.Build();
            return ui;
        }

        public void SetCamera(Camera c) => worldCam = c;

        void Build()
        {
            var c = gameObject.AddComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            c.sortingOrder = 10;
            var scaler = gameObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;
            gameObject.AddComponent<GraphicRaycaster>();
            canvas = (RectTransform)transform;
            if (FindFirstObjectByType<EventSystem>() == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<InputSystemUIInputModule>();
            }
            BuildHud();
            BuildDialogue();
            BuildLampPanel();
            BuildCard();
            BuildLetter();
            mapRoot = UiKit.Stretch(canvas, "JourneyMap").gameObject;
            mapRoot.SetActive(false);
            chapterRoot = UiKit.Stretch(canvas, "ChapterCard").gameObject;
            chapterRoot.SetActive(false);
            titleRoot = UiKit.Stretch(canvas, "Title").gameObject;
            titleRoot.SetActive(false);
            pauseRoot = UiKit.Stretch(canvas, "Pause").gameObject;
            pauseRoot.SetActive(false);
            BuildIntro();
            fade = UiKit.Image(canvas, "Fade", null, Color.black, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(5000f, 5000f));
        }

        // ================================================================ opening (world intro)
        GameObject introRoot;
        RectTransform barTop, barBottom;
        CanvasGroup introTextGroup;
        Text introHeading, introBody, introSkip;

        void BuildIntro()
        {
            introRoot = UiKit.Stretch(canvas, "Intro").gameObject;
            barTop = UiKit.Image(introRoot.transform, "BarTop", null, Color.black, new Vector2(0.5f, 1f), Vector2.zero, new Vector2(5000f, 0f)).rectTransform;
            barTop.pivot = new Vector2(0.5f, 1f);
            barBottom = UiKit.Image(introRoot.transform, "BarBottom", null, Color.black, new Vector2(0.5f, 0f), Vector2.zero, new Vector2(5000f, 0f)).rectTransform;
            barBottom.pivot = new Vector2(0.5f, 0f);
            var textRoot = UiKit.Stretch(introRoot.transform, "Text");
            introTextGroup = textRoot.gameObject.AddComponent<CanvasGroup>();
            var wash = UiKit.Image(textRoot, "Wash", UiKit.VGradient, new Color(0f, 0.01f, 0.03f, 0.72f), new Vector2(0.5f, 0f), new Vector2(0f, 96f), new Vector2(4000f, 330f));
            wash.rectTransform.pivot = new Vector2(0.5f, 0f);
            UiKit.GoldRule(textRoot, "Rule", new Vector2(0.5f, 0f), new Vector2(0f, 352f), 220f);
            introHeading = UiKit.Text(textRoot, "Heading", "", 26, UiKit.Gold, TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 392f), new Vector2(900f, 44f));
            introHeading.rectTransform.pivot = new Vector2(0.5f, 0.5f);
            introBody = UiKit.Text(textRoot, "Body", "", 33, UiKit.Ivory, TextAnchor.UpperCenter, new Vector2(0.5f, 0f), new Vector2(0f, 330f), new Vector2(1420f, 230f));
            introBody.rectTransform.pivot = new Vector2(0.5f, 1f);
            introBody.lineSpacing = 1.45f;
            introSkip = UiKit.Text(introRoot.transform, "Skip", UiKit.Track("Tab 跳过开篇"), 20, UiKit.GoldDim, TextAnchor.MiddleRight, new Vector2(1f, 0f), new Vector2(-150f, 40f), new Vector2(300f, 36f));
            introRoot.SetActive(false);
        }

        public bool IntroSkipPressed() => GameInput.Down(Key.Tab);

        public IEnumerator Letterbox(bool on, float seconds = 0.9f)
        {
            if (on) { introRoot.SetActive(true); introTextGroup.alpha = 0f; introRoot.transform.SetSiblingIndex(fade.transform.GetSiblingIndex()); }
            float from = barTop.sizeDelta.y, to = on ? 104f : 0f;
            for (float t = 0f; t < 1f; t += Time.unscaledDeltaTime / seconds)
            {
                float h = Mathf.Lerp(from, to, Mathf.SmoothStep(0f, 1f, t));
                barTop.sizeDelta = barBottom.sizeDelta = new Vector2(5000f, h);
                introSkip.color = new Color(UiKit.Gold.r, UiKit.Gold.g, UiKit.Gold.b, 0.55f * h / 104f);
                yield return null;
            }
            barTop.sizeDelta = barBottom.sizeDelta = new Vector2(5000f, to);
            if (!on) introRoot.SetActive(false);
        }

        // One beat of the opening: a small gold heading and a paragraph that reveals line by line.
        // Returns early (skipped = true) if the player presses Tab.
        public IEnumerator IntroBeat(string heading, string body, Action onSkip)
        {
            introHeading.text = UiKit.Track(heading);
            introBody.text = "";
            yield return FadeGroup(introTextGroup, 1f, 0.5f);
            string[] parts = body.Split('\n');
            var shown = new StringBuilder();
            for (int p = 0; p < parts.Length; p++)
            {
                if (p > 0) shown.Append('\n');
                string line = parts[p];
                for (float t = 0f; t < line.Length; t += Time.unscaledDeltaTime * 26f)
                {
                    if (IntroSkipPressed()) { onSkip(); yield break; }
                    if (AdvancePressed()) { t = line.Length; }
                    introBody.text = shown.ToString() + line.Substring(0, Mathf.Min(line.Length, Mathf.CeilToInt(t)));
                    yield return null;
                }
                shown.Append(line);
                introBody.text = shown.ToString();
                if (p < parts.Length - 1)
                    for (float w = 0f; w < 0.5f; w += Time.unscaledDeltaTime)
                    {
                        if (IntroSkipPressed()) { onSkip(); yield break; }
                        if (AdvancePressed()) break;
                        yield return null;
                    }
            }
            yield return null;
            while (!AdvancePressed())
            {
                if (IntroSkipPressed()) { onSkip(); yield break; }
                yield return null;
            }
            yield return FadeGroup(introTextGroup, 0f, 0.35f);
        }

        public void HideIntroText() => introTextGroup.alpha = 0f;

        static CanvasGroup Group(GameObject g)
        {
            var cg = g.GetComponent<CanvasGroup>();
            return cg != null ? cg : g.AddComponent<CanvasGroup>();
        }

        static IEnumerator FadeGroup(CanvasGroup g, float to, float seconds)
        {
            float from = g.alpha;
            for (float t = 0f; t < 1f; t += Time.unscaledDeltaTime / Mathf.Max(0.01f, seconds))
            {
                g.alpha = Mathf.Lerp(from, to, Mathf.SmoothStep(0f, 1f, t));
                yield return null;
            }
            g.alpha = to;
        }

        static void Clear(GameObject root)
        {
            for (int i = root.transform.childCount - 1; i >= 0; --i) Destroy(root.transform.GetChild(i).gameObject);
        }

        static RawImage Backdrop(Transform parent)
        {
            var rt = UiKit.Stretch(parent, "Starfield");
            var raw = rt.gameObject.AddComponent<RawImage>();
            raw.texture = UiKit.Starfield;
            raw.raycastTarget = true;
            return raw;
        }

        static void Sparkles(Transform parent, int count, int seed, Rect area, float minSize = 14f, float maxSize = 34f)
        {
            var rng = new System.Random(seed);
            for (int i = 0; i < count; ++i)
            {
                var p = new Vector2(Mathf.Lerp(area.xMin, area.xMax, (float)rng.NextDouble()), Mathf.Lerp(area.yMin, area.yMax, (float)rng.NextDouble()));
                float s = Mathf.Lerp(minSize, maxSize, Mathf.Pow((float)rng.NextDouble(), 2f));
                var img = UiKit.Image(parent, "Sparkle", UiKit.Sparkle, UiKit.Gold, new Vector2(0.5f, 0.5f), p, new Vector2(s, s));
                img.gameObject.AddComponent<Twinkle>().Speed = 0.7f + (float)rng.NextDouble();
            }
        }

        // ================================================================ HUD
        void BuildHud()
        {
            var hud = UiKit.Stretch(canvas, "HUD");
            hudGroup = Group(hud.gameObject);
            questRoot = UiKit.Rect(hud, "Quest", new Vector2(0f, 1f), new Vector2(84f, -64f), new Vector2(900f, 110f), new Vector2(0f, 1f));
            questStar = UiKit.Image(questRoot, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 1f), new Vector2(14f, -22f), new Vector2(30f, 30f));
            questStar.gameObject.AddComponent<Twinkle>().Min = 0.6f;
            questText = UiKit.Text(questRoot, "Title", "", 36, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(44f, -2f), new Vector2(860f, 50f));
            questText.rectTransform.pivot = new Vector2(0f, 1f);
            stepText = UiKit.Text(questRoot, "Step", "", 25, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(44f, -56f), new Vector2(860f, 40f));
            stepText.rectTransform.pivot = new Vector2(0f, 1f);
            hintText = UiKit.Text(questRoot, "Hint", "", 21, new Color(1f, 1f, 1f, 0.72f), TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(44f, -96f), new Vector2(860f, 70f));
            hintText.rectTransform.pivot = new Vector2(0f, 1f);

            promptRoot = UiKit.Rect(hud, "Prompt", new Vector2(0f, 0f), Vector2.zero, new Vector2(420f, 44f), new Vector2(0f, 0.5f));
            UiKit.KeyCap(promptRoot, "E", new Vector2(0f, 0.5f), new Vector2(18f, 0f), 36f);
            promptText = UiKit.Text(promptRoot, "Action", "", 26, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(50f, 0f), new Vector2(380f, 44f));
            promptText.rectTransform.pivot = new Vector2(0f, 0.5f);
            promptRoot.gameObject.SetActive(false);

            markerRoot = UiKit.Rect(hud, "Marker", new Vector2(0f, 0f), Vector2.zero, new Vector2(320f, 36f), new Vector2(0f, 0.5f));
            UiKit.Image(markerRoot, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 0.5f), new Vector2(12f, 0f), new Vector2(24f, 24f)).gameObject.AddComponent<Twinkle>();
            markerText = UiKit.Text(markerRoot, "Label", "", 22, new Color(1f, 1f, 1f, 0.85f), TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(32f, 0f), new Vector2(300f, 36f));
            markerText.rectTransform.pivot = new Vector2(0f, 0.5f);
            markerRoot.gameObject.SetActive(false);

            toastText = UiKit.Text(hud, "Toast", "", 26, UiKit.Ivory, TextAnchor.MiddleCenter, new Vector2(0.5f, 1f), new Vector2(0f, -170f), new Vector2(1300f, 60f));
            toastGroup = Group(toastText.gameObject);
            toastGroup.alpha = 0f;
        }

        public void SetQuest(string quest) => StartCoroutine(SwapText(questText, quest));

        public void SetObjective(string step, string hint)
        {
            if (stepText.text != (step ?? "")) StartCoroutine(SwapText(stepText, step));
            hintText.text = hint ?? "";
            questRoot.gameObject.SetActive(!string.IsNullOrEmpty(questText.text) || !string.IsNullOrEmpty(step));
        }

        IEnumerator SwapText(Text t, string s)
        {
            var g = Group(t.gameObject);
            if (!string.IsNullOrEmpty(t.text)) yield return FadeGroup(g, 0f, 0.25f);
            t.text = s ?? "";
            var rt = t.rectTransform;
            Vector2 p = rt.anchoredPosition;
            for (float k = 0f; k < 1f; k += Time.unscaledDeltaTime / 0.45f)
            {
                g.alpha = k;
                rt.anchoredPosition = p + new Vector2(0f, -8f * (1f - Mathf.SmoothStep(0f, 1f, k)));
                yield return null;
            }
            g.alpha = 1f;
            rt.anchoredPosition = p;
        }

        // Old call sites pass "E  调整晚风灯"; the key cap is drawn separately.
        public void SetPrompt(string text) => SetPrompt(text, null);

        public void SetPrompt(string text, Vector3? world)
        {
            if (string.IsNullOrEmpty(text)) { promptRoot.gameObject.SetActive(false); return; }
            if (text.StartsWith("E")) text = text.Substring(1).TrimStart();
            promptText.text = text;
            promptWorld = world;
            promptRoot.gameObject.SetActive(true);
        }

        public void SetMarker(string label, Vector3? world)
        {
            markerLabel = label;
            markerWorld = world;
            markerRoot.gameObject.SetActive(world.HasValue && !string.IsNullOrEmpty(label));
        }

        public void Toast(string text, float seconds = 3f)
        {
            toastText.text = text;
            toastUntil = Time.unscaledTime + seconds;
        }

        public void ShowHud(bool on) => hudGroup.alpha = on ? 1f : 0f;

        Vector2 ToCanvas(Vector3 world, out bool inFront)
        {
            var sp = worldCam.WorldToScreenPoint(world);
            inFront = sp.z > 0f;
            Vector2 local;
            var cv = canvas.GetComponent<Canvas>();
            var uiCam = cv.renderMode == RenderMode.ScreenSpaceOverlay ? null : cv.worldCamera;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(canvas, sp, uiCam, out local);
            return local + canvas.rect.size * 0.5f;
        }

        void LateUpdate()
        {
            toastGroup.alpha = Mathf.MoveTowards(toastGroup.alpha, Time.unscaledTime < toastUntil ? 1f : 0f, Time.unscaledDeltaTime * 2.5f);
            if (worldCam == null) return;
            Vector2 size = canvas.rect.size;
            if (promptRoot.gameObject.activeSelf)
            {
                if (promptWorld.HasValue)
                {
                    var p = ToCanvas(promptWorld.Value, out bool front);
                    promptRoot.anchoredPosition = front ? new Vector2(Mathf.Clamp(p.x + 30f, 40f, size.x - 420f), Mathf.Clamp(p.y, 60f, size.y - 60f)) : new Vector2(size.x * 0.5f, 300f);
                }
                else promptRoot.anchoredPosition = new Vector2(size.x * 0.5f - 90f, 300f);
            }
            if (markerRoot.gameObject.activeSelf && markerWorld.HasValue)
            {
                var p = ToCanvas(markerWorld.Value + Vector3.up * 1.6f, out bool front);
                if (!front) p = new Vector2(size.x - p.x, 80f);
                markerRoot.anchoredPosition = new Vector2(Mathf.Clamp(p.x, 40f, size.x - 300f), Mathf.Clamp(p.y, 80f, size.y - 160f));
                markerText.text = markerLabel + "  ·  " + Mathf.Max(1, Mathf.RoundToInt(MarkerDistance)) + " 米";
            }
        }

        // Set by the director each frame from the player's position (camera distance would mislead).
        public float MarkerDistance { get; set; }

        // ================================================================ input
        public bool AdvancePressed()
        {
            if (pauseRoot.activeSelf) return false;
            if (Time.frameCount == lastAdvanceFrame) return false;
            var mouse = Mouse.current;
            var pad = Gamepad.current;
            bool p = GameInput.AnyDown(Key.Space, Key.Enter, Key.NumpadEnter, Key.E)
                     || (mouse != null && mouse.leftButton.wasPressedThisFrame)
                     || (pad != null && pad.buttonSouth.wasPressedThisFrame);
            if (p) lastAdvanceFrame = Time.frameCount;
            return p;
        }

        IEnumerator WaitAdvance()
        {
            yield return null;
            while (!AdvancePressed()) yield return null;
        }

        // ================================================================ dialogue
        void BuildDialogue()
        {
            // spoken lines: gold-edged translucent box with a name pill
            var box = UiKit.Panel(canvas, "Dialogue", new Vector2(0.5f, 0f), new Vector2(0f, 64f), new Vector2(1300f, 210f), 0.74f);
            box.pivot = new Vector2(0.5f, 0f);
            dialogueRoot = box.gameObject;
            namePill = UiKit.Rect(box, "NamePill", new Vector2(0f, 1f), new Vector2(46f, 0f), new Vector2(190f, 50f), new Vector2(0f, 0.5f));
            var pillFill = namePill.gameObject.AddComponent<Image>();
            pillFill.sprite = UiKit.PanelFillSprite;
            pillFill.type = Image.Type.Sliced;
            pillFill.color = new Color(0.08f, 0.07f, 0.05f, 0.92f);
            var pillEdge = UiKit.Image(namePill, "Edge", UiKit.Pill, UiKit.Gold, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero, true);
            pillEdge.rectTransform.anchorMin = Vector2.zero;
            pillEdge.rectTransform.anchorMax = Vector2.one;
            UiKit.Image(namePill, "Icon", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 0.5f), new Vector2(28f, 0f), new Vector2(22f, 22f));
            nameText = UiKit.Text(namePill, "Name", "", 26, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(50f, 1f), new Vector2(200f, 44f));
            nameText.rectTransform.pivot = new Vector2(0f, 0.5f);
            lineText = UiKit.Text(box, "Line", "", 34, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(56f, -52f), new Vector2(1180f, 140f));
            lineText.rectTransform.pivot = new Vector2(0f, 1f);
            lineText.lineSpacing = 1.3f;
            continueStar = UiKit.Image(box, "More", UiKit.Sparkle, UiKit.Gold, new Vector2(1f, 0f), new Vector2(-40f, 32f), new Vector2(26f, 26f));
            continueStar.gameObject.AddComponent<Twinkle>().Speed = 3f;
            dialogueRoot.SetActive(false);

            // narration: centred subtitle over a soft wash, no box
            var nar = UiKit.Rect(canvas, "Narration", new Vector2(0.5f, 0f), new Vector2(0f, 0f), new Vector2(4000f, 330f), new Vector2(0.5f, 0f));
            narrationRoot = nar.gameObject;
            var wash = UiKit.Image(nar, "Wash", UiKit.VGradient, new Color(0f, 0f, 0.02f, 0.78f), new Vector2(0.5f, 0f), Vector2.zero, new Vector2(4000f, 330f));
            wash.rectTransform.pivot = new Vector2(0.5f, 0f);
            narrationText = UiKit.Text(nar, "Text", "", 32, UiKit.Ivory, TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 120f), new Vector2(1320f, 140f));
            narrationText.lineSpacing = 1.35f;
            narrationRoot.SetActive(false);
        }

        public IEnumerator Say(Line[] lines, Action<int> onLine = null)
        {
            for (int i = 0; i < lines.Length; ++i)
            {
                onLine?.Invoke(i);
                yield return SayOne(lines[i]);
            }
            HideDialogue();
        }

        public IEnumerator SayOne(Line line)
        {
            bool narration = line.Who == Speaker.Narrator || (line.Who == Speaker.Player && line.Text.StartsWith("连"));
            Text target;
            if (narration)
            {
                dialogueRoot.SetActive(false);
                narrationRoot.SetActive(true);
                narrationText.fontStyle = line.Who == Speaker.Narrator ? FontStyle.Normal : FontStyle.Italic;
                target = narrationText;
            }
            else
            {
                narrationRoot.SetActive(false);
                dialogueRoot.SetActive(true);
                nameText.text = UiKit.Track(StoryText.Name(line.Who));
                namePill.sizeDelta = new Vector2(80f + nameText.preferredWidth, 50f);
                target = lineText;
            }
            string body = narration ? line.Text : line.Text;
            continueStar.enabled = false;
            var sb = new StringBuilder();
            float t = 0f;
            int shown = 0;
            target.text = "";
            yield return null;
            while (shown < body.Length)
            {
                if (pauseRoot.activeSelf) { yield return null; continue; }
                t += Time.unscaledDeltaTime * 30f;
                int n = Mathf.Min(body.Length, Mathf.FloorToInt(t));
                if (n > shown) { sb.Append(body, shown, n - shown); shown = n; target.text = sb.ToString(); }
                if (AdvancePressed()) { target.text = body; break; }
                yield return null;
            }
            continueStar.enabled = true;
            yield return WaitAdvance();
        }

        public void HideDialogue()
        {
            dialogueRoot.SetActive(false);
            narrationRoot.SetActive(false);
        }

        // ================================================================ narration card
        void BuildCard()
        {
            cardRoot = UiKit.Stretch(canvas, "Card").gameObject;
            Backdrop(cardRoot.transform);
            Sparkles(cardRoot.transform, 9, 7, new Rect(-900f, -480f, 1800f, 960f));
            UiKit.GoldRule(cardRoot.transform, "Rule", new Vector2(0.5f, 0.5f), new Vector2(0f, 210f), 360f);
            cardText = UiKit.Text(cardRoot.transform, "Text", "", 40, UiKit.Ivory, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(0f, 0f), new Vector2(1400f, 380f));
            cardText.lineSpacing = 1.45f;
            UiKit.Image(cardRoot.transform, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0.5f, 0f), new Vector2(-96f, 96f), new Vector2(22f, 22f)).gameObject.AddComponent<Twinkle>();
            UiKit.Text(cardRoot.transform, "Hint", UiKit.Track("点击 · 继续"), 22, UiKit.Gold, TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(10f, 96f), new Vector2(300f, 40f));
            cardRoot.SetActive(false);
        }

        public IEnumerator Card(string text, int size = 40, bool waitInput = true, float hold = 2.5f)
        {
            cardRoot.SetActive(true);
            // above the black fade: these screens are opaque and bring their own fades
            fade.transform.SetAsLastSibling();
            cardRoot.transform.SetAsLastSibling();
            cardText.text = text;
            cardText.fontSize = size;
            var g = Group(cardRoot);
            g.alpha = 0f;
            yield return FadeGroup(g, 1f, 0.8f);
            if (waitInput) yield return WaitAdvance(); else yield return new WaitForSecondsRealtime(hold);
            yield return FadeGroup(g, 0f, 0.7f);
            cardRoot.SetActive(false);
        }

        // ================================================================ letter
        void BuildLetter()
        {
            letterRoot = UiKit.Stretch(canvas, "Letter").gameObject;
            var dim = letterRoot.AddComponent<Image>();
            dim.color = new Color(0.01f, 0.02f, 0.05f, 0.86f);
            var paper = UiKit.Image(letterRoot.transform, "Paper", UiKit.Parchment, Color.white, new Vector2(0.5f, 0.5f), new Vector2(0f, 40f), new Vector2(1180f, 860f));
            letterBody = UiKit.Text(paper.transform, "Body", "", 29, new Color(0.2f, 0.15f, 0.1f), TextAnchor.UpperLeft, new Vector2(0.5f, 0.5f), new Vector2(0f, -10f), new Vector2(1000f, 740f), false);
            letterBody.lineSpacing = 1.3f;
            var b = UiKit.Rect(letterRoot.transform, "Relight", new Vector2(0.5f, 0f), new Vector2(0f, 46f), new Vector2(460f, 64f), new Vector2(0.5f, 0f));
            var hit = b.gameObject.AddComponent<Image>();
            hit.color = new Color(0f, 0f, 0f, 0.001f);
            letterButton = b.gameObject.AddComponent<Button>();
            UiKit.Image(b, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 0.5f), new Vector2(40f, 0f), new Vector2(26f, 26f)).gameObject.AddComponent<Twinkle>();
            UiKit.Text(b, "Label", UiKit.Track(StoryText.LetterButton), 32, UiKit.Gold, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(20f, 0f), new Vector2(420f, 60f));
            letterRoot.SetActive(false);
        }

        public IEnumerator Letter()
        {
            letterRoot.SetActive(true);
            letterRoot.transform.SetAsLastSibling();
            letterBody.text = StoryText.LetterText;
            // Keep every paragraph and the signature inside the existing paper at 1600×900.
            // Preferred height uses the actual loaded Chinese font, rather than an assumed
            // line height; otherwise the last paragraph ran into the relight button.
            letterBody.fontSize = 29;
            Canvas.ForceUpdateCanvases();
            while (letterBody.fontSize > 20 && letterBody.preferredHeight > letterBody.rectTransform.rect.height)
                --letterBody.fontSize;
            var g = Group(letterRoot);
            g.alpha = 0f;
            yield return FadeGroup(g, 1f, 0.8f);
            bool clicked = false;
            letterButton.onClick.RemoveAllListeners();
            letterButton.onClick.AddListener(() => clicked = true);
            yield return null;
            while (!clicked && !GameInput.AnyDown(Key.Enter, Key.NumpadEnter)) yield return null;
            yield return FadeGroup(g, 0f, 0.6f);
            letterRoot.SetActive(false);
        }

        // ================================================================ lamp panel
        void BuildLampPanel()
        {
            var p = UiKit.Panel(canvas, "LampPanel", new Vector2(1f, 0.5f), new Vector2(-60f, 80f), new Vector2(600f, 440f), 0.78f);
            p.pivot = new Vector2(1f, 0.5f);
            lampPanel = p.gameObject;
            UiKit.Image(p, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 1f), new Vector2(40f, -42f), new Vector2(26f, 26f));
            UiKit.Text(p, "Title", UiKit.Track("调 灯"), 32, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 1f), new Vector2(66f, -42f), new Vector2(300f, 44f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.GoldRule(p, "Rule", new Vector2(0.5f, 1f), new Vector2(0f, -78f), 520f, 0.04f);
            lampText = UiKit.Text(p, "Body", "", 25, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 1f), new Vector2(40f, -100f), new Vector2(530f, 320f));
            lampText.rectTransform.pivot = new Vector2(0f, 1f);
            lampText.supportRichText = true;
            lampText.lineSpacing = 1.35f;
            lampPanel.SetActive(false);

            // key legend along the bottom, in the reference's key-cap style
            keyLegend = UiKit.Rect(canvas, "KeyLegend", new Vector2(0.5f, 0f), new Vector2(0f, 40f), new Vector2(1400f, 50f), new Vector2(0.5f, 0f)).gameObject;
            float x = -560f;
            foreach (var (keys, label) in new[] { (new[] { "1", "2", "3" }, "选灯"), (new[] { "A", "D" }, "转向"), (new[] { "空格" }, "换灯罩"), (new[] { "Enter" }, "确认"), (new[] { "Esc" }, "返回") })
            {
                foreach (var k in keys)
                {
                    var cap = UiKit.KeyCap(keyLegend.transform, k, new Vector2(0.5f, 0.5f), new Vector2(x, 0f), 34f);
                    // This row advances x from the left edge, including wide key caps.
                    cap.pivot = new Vector2(0f, 0.5f);
                    x += cap.sizeDelta.x + 6f;
                }
                var t = UiKit.Text(keyLegend.transform, "L", label, 22, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0.5f, 0.5f), new Vector2(x + 4f, 0f), new Vector2(120f, 40f));
                t.rectTransform.pivot = new Vector2(0f, 0.5f);
                x += t.preferredWidth + 44f;
            }
            keyLegend.SetActive(false);
        }

        public void ShowLampPanel(bool on)
        {
            lampPanel.SetActive(on);
            keyLegend.SetActive(on);
        }

        public void SetLampPanel(Chapter c, LampSetting[] lamps, int selected, LampResult r)
        {
            var sb = new StringBuilder();
            int unlocked = LampRules.UnlockedLamps(c);
            for (int i = 0; i < LampRules.LampCount; ++i)
            {
                bool sel = i == selected;
                if (i >= unlocked) { sb.Append("<color=#8A8A90>   ").Append(LampRules.LampNames[i]).Append("　还用不上</color>\n"); continue; }
                sb.Append(sel ? "<color=#EEC26B>✦ " : "   ").Append(LampRules.LampNames[i]).Append("　照向 ").Append(LampRules.DirectionName(i, lamps[i].Direction))
                  .Append("　").Append(lamps[i].Wide ? "宽罩" : "窄罩").Append(sel ? "</color>" : "").Append('\n');
            }
            sb.Append("\n<size=22><color=#CFC6B4>需要照亮</color></size>\n");
            foreach (Target t in new[] { Target.Path, Target.Bench, Target.Window, Target.Pier })
            {
                if ((r.Required & t) == 0) continue;
                bool lit = (r.Covered & t) != 0;
                sb.Append(lit ? "<color=#EEC26B>● " : "<color=#8A8A90>○ ").Append(LampRules.TargetName(t)).Append("</color>　");
            }
            bool skyward = false;
            for (int i = 0; i < unlocked; ++i) skyward |= lamps[i].On && LampRules.Wrap(lamps[i].Direction) == 2;
            sb.Append("\n<size=22><color=#CFC6B4>夜空</color></size>　");
            sb.Append(skyward ? "<color=#E8907A>有光漏到天上了</color>" : r.SkyLoss <= r.SkyAllowed ? "<color=#EEC26B>星星看得见</color>" : "<color=#E8907A>宽光太多，天被照白了</color>");
            lampText.text = sb.ToString();
        }

        // ================================================================ title page
        public IEnumerator Title(Action onStart)
        {
            Clear(titleRoot);
            titleRoot.SetActive(true);
            // above the black fade: these screens are opaque and bring their own fades
            fade.transform.SetAsLastSibling();
            titleRoot.transform.SetAsLastSibling();
            var t = titleRoot.transform;
            var wash = UiKit.Image(t, "Wash", UiKit.HGradient, new Color(0.01f, 0.02f, 0.07f, 0.88f), new Vector2(0f, 0.5f), Vector2.zero, new Vector2(1250f, 2200f));
            wash.rectTransform.pivot = new Vector2(0f, 0.5f);
            Sparkles(t, 10, 3, new Rect(-940f, -500f, 1880f, 1000f));
            var block = UiKit.Rect(t, "Block", new Vector2(0f, 0.5f), new Vector2(170f, 60f), new Vector2(760f, 420f), new Vector2(0f, 0.5f));
            UiKit.Text(block, "Name", UiKit.Track("借光岛", 3), 150, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(0f, 70f), new Vector2(760f, 190f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            var rule = UiKit.GoldRule(block, "Rule", new Vector2(0f, 0.5f), new Vector2(4f, -54f), 480f);
            rule.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(block, "Latin", UiKit.Track(StoryText.MapLatin, 2), 21, new Color(UiKit.Ivory.r, UiKit.Ivory.g, UiKit.Ivory.b, 0.8f), TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(4f, -98f), new Vector2(760f, 36f)).rectTransform.pivot = new Vector2(0f, 0.5f);

            var start = UiKit.Rect(t, "Start", new Vector2(0.5f, 0f), new Vector2(0f, 120f), new Vector2(420f, 60f), new Vector2(0.5f, 0f));
            var hit = start.gameObject.AddComponent<Image>();
            hit.color = new Color(0f, 0f, 0f, 0.001f);
            var btn = start.gameObject.AddComponent<Button>();
            UiKit.Image(start, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0.5f, 0.5f), new Vector2(-150f, 2f), new Vector2(24f, 24f)).gameObject.AddComponent<Twinkle>();
            var label = UiKit.Text(start, "Label", UiKit.Track("点击 · 开始旅程"), 28, UiKit.Gold, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(14f, 0f), new Vector2(400f, 56f));
            label.gameObject.AddComponent<Twinkle>().Min = 0.7f;
            UiKit.Text(t, "Small", UiKit.Track("也可以按 Enter"), 18, new Color(1f, 1f, 1f, 0.5f), TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 96f), new Vector2(400f, 30f));
            bool go = false;
            btn.onClick.AddListener(() => go = true);
            var g = Group(titleRoot);
            g.alpha = 0f;
            StartCoroutine(FadeGroup(g, 1f, 1.4f));
            while (!go && !GameInput.AnyDown(Key.Enter, Key.NumpadEnter, Key.Space)) yield return null;
            onStart?.Invoke();
            yield return FadeGroup(g, 0f, 0.8f);
            titleRoot.SetActive(false);
        }

        // ================================================================ journey map
        public sealed class MapNode
        {
            public StoryText.ChapterInfo Info;
            public Texture Vignette;
            public bool Unlocked, JustUnlocked;
        }

        static readonly Vector2[] NodePos =
        {
            new Vector2(-620f, 150f), new Vector2(-210f, 170f), new Vector2(200f, 150f), new Vector2(600f, 175f),
            // Keep lower-row labels clear of the selected chapter details below.
            new Vector2(-420f, -60f), new Vector2(0f, -45f), new Vector2(420f, -65f),
        };

        // Returns the chosen chapter through onPick, or null through onPick when the player backs out.
        public IEnumerator JourneyMap(List<MapNode> nodes, int focus, Action<Chapter?> onPick)
        {
            Clear(mapRoot);
            mapRoot.SetActive(true);
            // above the black fade: these screens are opaque and bring their own fades
            fade.transform.SetAsLastSibling();
            mapRoot.transform.SetAsLastSibling();
            var root = mapRoot.transform;
            Backdrop(root);
            Sparkles(root, 8, 11, new Rect(-940f, -520f, 1880f, 1040f), 18f, 40f);
            var sheet = UiKit.Image(root, "Parchment", UiKit.Parchment, Color.white, new Vector2(0.5f, 0.5f), new Vector2(0f, -10f), new Vector2(1760f, 960f));
            var s = sheet.transform;
            Sparkles(s, 6, 19, new Rect(-820f, -420f, 1640f, 840f), 20f, 44f);
            UiKit.Text(s, "Latin", UiKit.Track(StoryText.MapLatin, 2), 18, new Color(UiKit.Ink.r, UiKit.Ink.g, UiKit.Ink.b, 0.45f), TextAnchor.MiddleCenter, new Vector2(0.5f, 1f), new Vector2(0f, -40f), new Vector2(900f, 30f), false);
            UiKit.Text(s, "Title", UiKit.Track(StoryText.MapTitle, 2), 52, UiKit.Ink, TextAnchor.MiddleCenter, new Vector2(0.5f, 1f), new Vector2(0f, -92f), new Vector2(900f, 70f), false);
            var rule = UiKit.GoldRule(s, "Rule", new Vector2(0.5f, 1f), new Vector2(0f, -134f), 260f);
            UiKit.Text(s, "Sub", UiKit.Track(StoryText.MapSubtitle), 22, new Color(UiKit.Ink.r, UiKit.Ink.g, UiKit.Ink.b, 0.75f), TextAnchor.MiddleCenter, new Vector2(0.5f, 1f), new Vector2(0f, -162f), new Vector2(700f, 36f), false);

            // dotted route between consecutive places
            for (int i = 0; i + 1 < nodes.Count && i + 1 < NodePos.Length; ++i)
            {
                Vector2 a = NodePos[i], b = NodePos[i + 1];
                int dots = Mathf.CeilToInt(Vector2.Distance(a, b) / 22f);
                for (int k = 2; k < dots - 1; ++k)
                {
                    var p = Vector2.Lerp(a, b, k / (float)dots) + new Vector2(0f, Mathf.Sin(k * 0.5f) * 6f);
                    UiKit.Image(s, "Dot", UiKit.SoftDot, new Color(0.62f, 0.45f, 0.22f, nodes[i + 1].Unlocked ? 0.75f : 0.3f), new Vector2(0.5f, 0.5f), p, new Vector2(7f, 7f));
                }
            }
            var nodeImgs = new List<RawImage>();
            var rings = new List<Image>();
            int selected = Mathf.Clamp(focus, 0, nodes.Count - 1);
            for (int i = 0; i < nodes.Count && i < NodePos.Length; ++i)
            {
                int idx = i;
                var n = nodes[i];
                var holder = UiKit.Rect(s, "Node" + i, new Vector2(0.5f, 0.5f), NodePos[i], new Vector2(230f, 230f));
                var halo = UiKit.Image(holder, "Wash", UiKit.Glow, new Color(0.55f, 0.66f, 0.85f, 0.45f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(300f, 300f));
                var maskImg = holder.gameObject.AddComponent<Image>();
                maskImg.sprite = UiKit.Circle;
                maskImg.raycastTarget = true;
                holder.gameObject.AddComponent<Mask>().showMaskGraphic = false;
                var rawRt = UiKit.Stretch(holder, "Vignette");
                var raw = rawRt.gameObject.AddComponent<RawImage>();
                raw.texture = n.Vignette;
                raw.raycastTarget = false;
                raw.color = n.Unlocked && !n.JustUnlocked ? Color.white : new Color(0.55f, 0.62f, 0.85f, 0.9f);
                nodeImgs.Add(raw);
                var ring = UiKit.Image(s, "Ring" + i, UiKit.Ring, UiKit.Gold, new Vector2(0.5f, 0.5f), NodePos[i], new Vector2(252f, 252f));
                ring.enabled = false;
                rings.Add(ring);
                UiKit.Text(s, "Label" + i, n.Info.Number, 20, new Color(UiKit.Ink.r, UiKit.Ink.g, UiKit.Ink.b, n.Unlocked ? 0.85f : 0.4f), TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), NodePos[i] + new Vector2(0f, -140f), new Vector2(240f, 30f), false);
                var btn = holder.gameObject.AddComponent<Button>();
                btn.transition = Selectable.Transition.None;
                btn.onClick.AddListener(() => { if (nodes[idx].Unlocked) selected = idx; });
            }

            // chapter info and the "enter" action at the bottom of the sheet
            var number = UiKit.Text(s, "Number", "", 20, new Color(UiKit.Ink.r, UiKit.Ink.g, UiKit.Ink.b, 0.55f), TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 220f), new Vector2(600f, 30f), false);
            var name = UiKit.Text(s, "Name", "", 30, UiKit.Ink, TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 182f), new Vector2(1200f, 44f), false);
            var desc = UiKit.Text(s, "Desc", "", 25, new Color(UiKit.Ink.r, UiKit.Ink.g, UiKit.Ink.b, 0.85f), TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 140f), new Vector2(1300f, 40f), false);
            var enter = UiKit.Rect(s, "Enter", new Vector2(0.5f, 0f), new Vector2(0f, 90f), new Vector2(420f, 52f), new Vector2(0.5f, 0.5f));
            var enterHit = enter.gameObject.AddComponent<Image>();
            enterHit.color = new Color(0f, 0f, 0f, 0.001f);
            var enterBtn = enter.gameObject.AddComponent<Button>();
            UiKit.Image(enter, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0.5f, 0.5f), new Vector2(-110f, 0f), new Vector2(24f, 24f)).gameObject.AddComponent<Twinkle>();
            var enterText = UiKit.Text(enter, "Label", "", 30, UiKit.Ink, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(14f, 0f), new Vector2(380f, 48f), false);
            var backHint = UiKit.Rect(root, "BackHint", new Vector2(0f, 0f), new Vector2(110f, 56f), new Vector2(300f, 40f), new Vector2(0f, 0f));
            var backKey = UiKit.KeyCap(backHint, "Esc", new Vector2(0f, 0.5f), Vector2.zero, 40f);
            var backLabel = UiKit.Text(backHint, "Back", "回到标题", 22, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(backKey.rect.width + 16f, 1f), new Vector2(200f, 40f));
            backHint.sizeDelta = new Vector2(backKey.rect.width + 16f + backLabel.preferredWidth, 40f);
            bool go = false;
            enterBtn.onClick.AddListener(() => go = true);

            var g = Group(mapRoot);
            g.alpha = 0f;
            yield return FadeGroup(g, 1f, 0.9f);

            // newly reached place: colour floods back into its vignette
            for (int i = 0; i < nodes.Count; ++i)
                if (nodes[i].JustUnlocked) StartCoroutine(Unveil(nodeImgs[i], rings[i]));

            int shownSel = -1;
            while (true)
            {
                if (GameInput.AnyDown(Key.RightArrow, Key.D)) selected = NextUnlocked(nodes, selected, +1);
                if (GameInput.AnyDown(Key.LeftArrow, Key.A)) selected = NextUnlocked(nodes, selected, -1);
                if (selected != shownSel)
                {
                    shownSel = selected;
                    var info = nodes[selected].Info;
                    number.text = UiKit.Track(info.Number);
                    name.text = UiKit.Track(info.Title + " · " + info.Subtitle);
                    desc.text = info.Description;
                    enterText.text = UiKit.Track(info.Enter);
                    for (int i = 0; i < rings.Count; ++i) rings[i].enabled = i == selected;
                }
                float pulse = 1f + 0.03f * Mathf.Sin(Time.unscaledTime * 2.2f);
                rings[selected].rectTransform.localScale = Vector3.one * pulse;
                if (go || GameInput.AnyDown(Key.Enter, Key.NumpadEnter)) { onPick(nodes[selected].Info.Id); break; }
                if (GameInput.Down(Key.Escape)) { onPick(null); break; }
                yield return null;
            }
            yield return FadeGroup(g, 0f, 0.7f);
            mapRoot.SetActive(false);
        }

        static int NextUnlocked(List<MapNode> nodes, int from, int dir)
        {
            for (int i = from + dir; i >= 0 && i < nodes.Count; i += dir)
                if (nodes[i].Unlocked) return i;
            return from;
        }

        IEnumerator Unveil(RawImage img, Image ring)
        {
            var from = img.color;
            yield return new WaitForSecondsRealtime(0.4f);
            for (float k = 0f; k < 1f; k += Time.unscaledDeltaTime / 1.6f)
            {
                img.color = Color.Lerp(from, Color.white, Mathf.SmoothStep(0f, 1f, k));
                yield return null;
            }
            img.color = Color.white;
        }

        // ================================================================ chapter card
        // Starfield card with the chapter's name and a vignette "planet"; the bar fills while the
        // director prepares the scene behind it (progress 0..1 is polled every frame).
        public IEnumerator ChapterCard(StoryText.ChapterInfo info, Texture vignette, Func<float> progress)
        {
            Clear(chapterRoot);
            chapterRoot.SetActive(true);
            // above the black fade: these screens are opaque and bring their own fades
            fade.transform.SetAsLastSibling();
            chapterRoot.transform.SetAsLastSibling();
            var t = chapterRoot.transform;
            Backdrop(t);
            // the place, drifting in from the right like the reference's planet
            var planet = UiKit.Rect(t, "Planet", new Vector2(1f, 0.5f), new Vector2(-170f, 70f), new Vector2(560f, 560f), new Vector2(0.5f, 0.5f));
            UiKit.Image(planet, "Glow", UiKit.Glow, new Color(0.55f, 0.7f, 1f, 0.35f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(760f, 760f));
            var mask = planet.gameObject.AddComponent<Image>();
            mask.sprite = UiKit.Circle;
            planet.gameObject.AddComponent<Mask>().showMaskGraphic = false;
            var raw = UiKit.Stretch(planet, "Vignette").gameObject.AddComponent<RawImage>();
            raw.texture = vignette;
            // dotted trail from the text block to the place
            for (int i = 0; i < 70; ++i)
            {
                float k = i / 69f;
                var p = new Vector2(Mathf.Lerp(-760f, 480f, k), Mathf.Lerp(-210f, -150f, k) - Mathf.Sin(k * Mathf.PI) * 40f);
                UiKit.Image(t, "Dot", UiKit.SoftDot, new Color(UiKit.Gold.r, UiKit.Gold.g, UiKit.Gold.b, Mathf.Lerp(0.15f, 0.7f, k)), new Vector2(0.5f, 0.5f), p, new Vector2(5f, 5f));
            }
            var block = UiKit.Rect(t, "Block", new Vector2(0f, 0.5f), new Vector2(190f, 110f), new Vector2(900f, 420f), new Vector2(0f, 0.5f));
            UiKit.Text(block, "Number", UiKit.Track(info.Number), 22, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(0f, 150f), new Vector2(400f, 36f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(block, "Title", UiKit.Track(info.Title, 2), 72, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(0f, 76f), new Vector2(1000f, 100f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            var rule = UiKit.GoldRule(block, "Rule", new Vector2(0f, 0.5f), new Vector2(0f, 14f), 220f, 1f);
            rule.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(block, "Sub", UiKit.Track(info.Subtitle), 24, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(0f, -26f), new Vector2(800f, 36f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            var d = UiKit.Text(block, "Desc", UiKit.Track(info.Description), 27, UiKit.Ivory, TextAnchor.UpperLeft, new Vector2(0f, 0.5f), new Vector2(0f, -66f), new Vector2(640f, 120f));
            d.rectTransform.pivot = new Vector2(0f, 1f);
            d.lineSpacing = 1.4f;

            var bar = UiKit.Rect(t, "Bar", new Vector2(0.5f, 0f), new Vector2(0f, 128f), new Vector2(600f, 30f), new Vector2(0.5f, 0.5f));
            UiKit.Image(bar, "Track", null, new Color(UiKit.Gold.r, UiKit.Gold.g, UiKit.Gold.b, 0.35f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(600f, 1.4f));
            var fill = UiKit.Image(bar, "Fill", null, UiKit.Gold, new Vector2(0f, 0.5f), Vector2.zero, new Vector2(0f, 2f));
            fill.rectTransform.pivot = new Vector2(0f, 0.5f);
            var rider = UiKit.Image(bar, "Rider", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 0.5f), Vector2.zero, new Vector2(30f, 30f));
            var pct = UiKit.Text(t, "Pct", "", 18, new Color(1f, 1f, 1f, 0.7f), TextAnchor.MiddleCenter, new Vector2(0.5f, 0f), new Vector2(0f, 96f), new Vector2(600f, 30f));

            var g = Group(chapterRoot);
            g.alpha = 0f;
            float shown = 0f, t0 = Time.unscaledTime;
            StartCoroutine(FadeGroup(g, 1f, 0.9f));
            while (true)
            {
                float target = Mathf.Min(progress != null ? progress() : 1f, (Time.unscaledTime - t0) / 2.8f);
                shown = Mathf.MoveTowards(shown, target, Time.unscaledDeltaTime * 0.8f);
                fill.rectTransform.sizeDelta = new Vector2(600f * shown, 2f);
                rider.rectTransform.anchoredPosition = new Vector2(600f * shown, 0f);
                pct.text = UiKit.Track("正在准备画面") + "  ·  " + Mathf.RoundToInt(shown * 100f) + "%";
                planet.anchoredPosition = new Vector2(-170f - 30f * (1f - shown), 70f);
                if (shown >= 0.999f) break;
                yield return null;
            }
            yield return new WaitForSecondsRealtime(0.9f);
            yield return FadeGroup(g, 0f, 1.0f);
            chapterRoot.SetActive(false);
        }

        // ================================================================ pause
        public IEnumerator Pause(string chapterLine, Action<PauseChoice> onChoice)
        {
            Clear(pauseRoot);
            pauseRoot.SetActive(true);
            pauseRoot.transform.SetAsLastSibling();
            var t = pauseRoot.transform;
            var dim = t.gameObject.GetComponent<Image>();
            if (dim == null) dim = t.gameObject.AddComponent<Image>();
            dim.color = new Color(0f, 0f, 0.01f, 0.55f);
            var wash = UiKit.Image(t, "Wash", UiKit.HGradient, new Color(0f, 0f, 0.02f, 0.75f), new Vector2(0f, 0.5f), Vector2.zero, new Vector2(900f, 2200f));
            wash.rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(t, "Name", UiKit.Track("借光岛", 2), 72, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 1f), new Vector2(160f, -150f), new Vector2(600f, 100f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(t, "Paused", UiKit.Track("暂 停"), 22, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 1f), new Vector2(162f, -250f), new Vector2(400f, 30f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            UiKit.Text(t, "Chapter", UiKit.Track(chapterLine), 28, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 1f), new Vector2(162f, -290f), new Vector2(700f, 40f)).rectTransform.pivot = new Vector2(0f, 0.5f);
            var rule = UiKit.GoldRule(t, "Rule", new Vector2(0f, 1f), new Vector2(162f, -320f), 300f, 1f);
            rule.pivot = new Vector2(0f, 0.5f);
            var items = new[] { ("继续", PauseChoice.Resume), ("回到旅程地图", PauseChoice.Map), ("回到标题", PauseChoice.Title), ("清除进度", PauseChoice.ClearProgress) };
            var labels = new List<Text>();
            var stars = new List<Image>();
            int sel = 0;
            PauseChoice? picked = null;
            for (int i = 0; i < items.Length; ++i)
            {
                int idx = i;
                var row = UiKit.Rect(t, "Item" + i, new Vector2(0f, 1f), new Vector2(160f, -420f - i * 78f), new Vector2(520f, 64f), new Vector2(0f, 0.5f));
                var hit = row.gameObject.AddComponent<Image>();
                hit.color = new Color(0f, 0f, 0f, 0.001f);
                var b = row.gameObject.AddComponent<Button>();
                b.transition = Selectable.Transition.None;
                b.onClick.AddListener(() => picked = items[idx].Item2);
                stars.Add(UiKit.Image(row, "Star", UiKit.Sparkle, UiKit.Gold, new Vector2(0f, 0.5f), new Vector2(10f, 0f), new Vector2(26f, 26f)));
                var l = UiKit.Text(row, "Label", UiKit.Track(items[i].Item1), 38, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(44f, 0f), new Vector2(480f, 60f));
                l.rectTransform.pivot = new Vector2(0f, 0.5f);
                labels.Add(l);
            }
            var backHint = UiKit.Rect(t, "BackHint", new Vector2(0.5f, 0f), new Vector2(0f, 64f), new Vector2(300f, 40f), new Vector2(0.5f, 0f));
            var backKey = UiKit.KeyCap(backHint, "Esc", new Vector2(0f, 0.5f), Vector2.zero, 40f);
            var backLabel = UiKit.Text(backHint, "Back", "返回游戏", 24, UiKit.Ivory, TextAnchor.MiddleLeft, new Vector2(0f, 0.5f), new Vector2(backKey.rect.width + 16f, 1f), new Vector2(200f, 40f));
            backHint.sizeDelta = new Vector2(backKey.rect.width + 16f + backLabel.preferredWidth, 40f);
            float prevScale = Time.timeScale;
            Time.timeScale = 0f;
            var g = Group(pauseRoot);
            g.alpha = 0f;
            StartCoroutine(FadeGroup(g, 1f, 0.3f));
            yield return null;
            while (picked == null)
            {
                if (GameInput.AnyDown(Key.DownArrow, Key.S)) sel = (sel + 1) % items.Length;
                if (GameInput.AnyDown(Key.UpArrow, Key.W)) sel = (sel + items.Length - 1) % items.Length;
                if (GameInput.AnyDown(Key.Enter, Key.NumpadEnter, Key.Space)) picked = items[sel].Item2;
                if (GameInput.Down(Key.Escape)) picked = PauseChoice.Resume;
                for (int i = 0; i < items.Length; ++i)
                {
                    stars[i].enabled = i == sel;
                    labels[i].color = i == sel ? UiKit.Gold : UiKit.Ivory;
                }
                yield return null;
            }
            yield return FadeGroup(g, 0f, 0.25f);
            pauseRoot.SetActive(false);
            lastAdvanceFrame = Time.frameCount;
            Time.timeScale = prevScale == 0f ? 1f : prevScale;
            onChoice(picked.Value);
        }

        // ================================================================ fade
        public IEnumerator FadeTo(float alpha, float seconds)
        {
            fade.transform.SetAsLastSibling();
            float a0 = fade.color.a;
            for (float t = 0f; t < 1f; t += Time.unscaledDeltaTime / Mathf.Max(0.01f, seconds))
            {
                fade.color = new Color(0f, 0f, 0f, Mathf.Lerp(a0, alpha, Mathf.SmoothStep(0f, 1f, t)));
                yield return null;
            }
            fade.color = new Color(0f, 0f, 0f, alpha);
        }
    }
}
