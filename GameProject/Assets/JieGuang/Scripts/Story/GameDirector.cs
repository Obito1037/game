using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // Runs 《借光岛》 from the title screen to the walking epilogue, following
    // art/design/script/07_完整故事与生图提示词（最终版）.md chapter by chapter.
    public sealed class GameDirector : MonoBehaviour
    {
        public GameObject IslandPrefab;
        public GameObject PlayerPrefab, AYingPrefab, PostmanPrefab, ABoPrefab, DengBoPrefab;

        const string SaveKey = "jieguang.chapter";
        const int PlayerLayer = 2; // Ignore Raycast: ground probes and the camera skip the player
        static readonly int WorldMask = ~(1 << PlayerLayer);

        static readonly Color GlowAYing = new Color(0.55f, 1f, 0.45f);
        static readonly Color GlowPostman = new Color(0.65f, 0.95f, 1f);
        static readonly Color GlowABo = new Color(1f, 0.6f, 0.3f);
        static readonly Color GlowDengBo = new Color(1f, 0.55f, 0.35f);
        static readonly Color GlowPlayer = new Color(1f, 0.78f, 0.45f);

        IslandLayout layout;
        CameraDirector cam;
        GameUI ui;
        NightSky sky;
        CharacterActor player, aying, postman, abo, dengbo;
        PlayerController pc;
        Lantern lantern, horseLamp;
        Transform harborLantern;
        readonly Dictionary<Light, float> harborLights = new Dictionary<Light, float>();
        Fireflow ayingGlow, postmanGlow, aboGlow, dengboGlow, playerGlow;
        readonly LampPost[] lamps = new LampPost[LampRules.LampCount];
        LampSetting[] settings = LampRules.StartState(Chapter.One);
        CrowdLights pierCrowd, roadCrowd;
        WindowGlow roundWindow;
        readonly List<WindowGlow> villageWindows = new List<WindowGlow>();
        Transform boat, flower;
        IslandSoundscape soundscape;
        StoryProps storyProps;
        readonly List<Coroutine> chapterEffects = new List<Coroutine>();
        readonly List<GameObject> transientObjects = new List<GameObject>();

        public Chapter Current { get; private set; } = Chapter.Title;
        int selected;
        bool puzzleOpen, wrongTurnSaid;
        float extraPollution;
        Vector3 safePosition;
        float safeYaw, nextSafeRecord;
        bool hasSafePosition;

        // Test hook: PlayerPrefs "jieguang.debugStart" = chapter number skips the title once.
        const string DebugKey = "jieguang.debugStart";

        void Start() => StartCoroutine(Boot());

        // ------------------------------------------------------------------ setup
        IEnumerator Boot()
        {
            Application.targetFrameRate = 60;
            AdaptiveResolution.Attach(gameObject);
            cam = CameraDirector.Create();
            cam.Camera.GetUniversalAdditionalCameraData().requiresDepthTexture = true;
            ui = GameUI.Create();
            ui.SetCamera(cam.Camera);
            StartCoroutine(ui.FadeTo(1f, 0f));
            layout = new GameObject("IslandLayout").AddComponent<IslandLayout>();
            layout.IslandPrefab = IslandPrefab;
            layout.Build();
            sky = new GameObject("NightSky").AddComponent<NightSky>();
            sky.Setup(cam.Camera);
            // the only directional light: cool earthlight from the Earth's side of the sky
            var earthLight = new GameObject("Earthlight").AddComponent<Light>();
            earthLight.type = LightType.Directional;
            earthLight.color = new Color(0.70f, 0.80f, 1f);
            earthLight.intensity = layout.UsingGraybox ? 0.35f : 1.0f;
            earthLight.shadows = LightShadows.Soft;
            earthLight.shadowStrength = 0.6f;
            earthLight.transform.rotation = Quaternion.LookRotation(-sky.EarthDirection, Vector3.up);
            if (!layout.UsingGraybox) sky.Sun = earthLight;
            if (FindObjectsByType<UnityEngine.Rendering.Volume>(FindObjectsSortMode.None).Length == 0)
                FallbackLook.Create();

            for (int i = 0; i < LampRules.LampCount; ++i)
            {
                lamps[i] = new GameObject("Lamp").AddComponent<LampPost>();
                lamps[i].Setup(i, layout.LampAnchor(i));
                lamps[i].WideAngle = layout.WideConeAngle(i);
            }
            roundWindow = layout.Get("Target_Window").GetComponentInChildren<WindowGlow>();
            if (roundWindow == null) roundWindow = FindRoundWindow();
            foreach (var w in layout.VillageWindows())
            {
                var g = w.GetComponent<WindowGlow>();
                if (g == null && w.GetComponent<Renderer>() != null) g = w.gameObject.AddComponent<WindowGlow>();
                if (g != null) villageWindows.Add(g);
            }
            boat = IslandLayout.FindChild(layout.IslandRoot.transform, "ReturningBoat");
            if (boat == null) boat = IslandLayout.FindChild(layout.IslandRoot.transform, "Boat");
            harborLantern = IslandLayout.FindChild(layout.IslandRoot.transform, "HarborLantern");
            if (harborLantern != null)
                foreach (var l in harborLantern.GetComponentsInChildren<Light>(true)) harborLights[l] = l.intensity;

            player = Spawn(PlayerPrefab, "Anchor_PlayerSpawn");
            player.gameObject.layer = PlayerLayer;
            foreach (var t in player.GetComponentsInChildren<Transform>()) t.gameObject.layer = PlayerLayer;
            pc = PlayerController.Attach(player.gameObject, 1.45f);
            pc.CameraTransform = cam.transform;
            cam.Follow = player.transform;
            lantern = Lantern.Create();
            lantern.FollowHand = player.LeftHand;
            playerGlow = Fireflow.Attach(player.gameObject, GlowPlayer, 0f);

            aying = Spawn(AYingPrefab, "NPC_AYing");
            postman = Spawn(PostmanPrefab, "NPC_Postman");
            abo = Spawn(ABoPrefab, "NPC_ABo_Door");
            dengbo = Spawn(DengBoPrefab, "NPC_DengBo_Box");
            ayingGlow = Fireflow.Attach(aying.gameObject, GlowAYing, 1.4f);
            postmanGlow = Fireflow.Attach(postman.gameObject, GlowPostman, 0.7f);
            aboGlow = Fireflow.Attach(abo.gameObject, GlowABo, 0.25f);
            dengboGlow = Fireflow.Attach(dengbo.gameObject, GlowDengBo, 0.35f);

            BuildCrowds();
            soundscape = gameObject.AddComponent<IslandSoundscape>();
            soundscape.Setup(cam.transform, layout.Pos("Target_Pier"));
            storyProps = gameObject.AddComponent<StoryProps>();
            storyProps.Setup(lantern, postman, player);

            yield return null;
            int debug = PlayerPrefs.GetInt(DebugKey, 0);
            if (debug >= (int)Chapter.Prologue && debug <= (int)Chapter.Epilogue)
            {
                PlayerPrefs.DeleteKey(DebugKey);
                flow = StartCoroutine(Journey((Chapter)debug));
                yield break;
            }
            flow = StartCoroutine(Journey(null));
        }

        WindowGlow FindRoundWindow()
        {
            var t = IslandLayout.FindChild(layout.IslandRoot.transform, "RoundWindow");
            if (t == null) return null;
            var g = t.GetComponent<WindowGlow>();
            return g != null ? g : t.gameObject.AddComponent<WindowGlow>();
        }

        CharacterActor Spawn(GameObject prefab, string anchor)
        {
            var a = layout.Get(anchor);
            var go = Instantiate(prefab, a.position, a.rotation);
            go.name = prefab.name;
            return go.GetComponent<CharacterActor>();
        }

        void BuildCrowds()
        {
            var pts = new List<Vector3>();
            Vector3 pier = layout.Pos("Target_Pier");
            for (int i = 0; i < 18; ++i) pts.Add(pier + PierOff(i % 2 == 0 ? 0.6f : -0.6f, 0f, i * 0.42f));
            pierCrowd = CrowdLights.Create("PierCrowd");
            pierCrowd.Spawn(pts, 0.3f, 3);
            pts.Clear();
            Vector3 gate = layout.Pos("Anchor_VillageGate"), village = layout.Pos("Village_Windows"), cross = layout.Pos("Target_Path");
            for (int i = 0; i < 16; ++i) pts.Add(Vector3.Lerp(village, gate, i / 15f));
            for (int i = 0; i < 8; ++i) pts.Add(Vector3.Lerp(gate, cross, i / 7f));
            roadCrowd = CrowdLights.Create("RoadCrowd");
            roadCrowd.Spawn(pts, 1.4f, 5);
            pierCrowd.SetVisibleInstant(false);
            roadCrowd.SetVisibleInstant(false);
        }

        // ------------------------------------------------------------------ flow
        static readonly Chapter[] Order = { Chapter.Prologue, Chapter.One, Chapter.Two, Chapter.Interlude, Chapter.Three, Chapter.Finale, Chapter.Epilogue };
        const string UnlockKey = "jieguang.unlocked";
        Coroutine flow, chapterRun;
        readonly Dictionary<Chapter, Texture> vignettes = new Dictionary<Chapter, Texture>();
        Transform markerTarget;
        bool pausing;

        // Title page → journey map → chapter card → chapter → back to the map with the next place
        // unveiled. `direct` skips the title and map (QA / debug start).
        IEnumerator Journey(Chapter? direct)
        {
            yield return RenderVignettes();
            if (direct.HasValue)
            {
                yield return PlayChapter(direct.Value);
                yield break;
            }
            yield return TitlePage();
            int focus = Mathf.Clamp(PlayerPrefs.GetInt(UnlockKey, 0), 0, Order.Length - 1);
            int justUnlocked = -1;
            while (true)
            {
                Chapter? pick = null;
                yield return ui.JourneyMap(MapNodes(justUnlocked), focus, c => pick = c);
                if (!pick.HasValue) { yield return TitlePage(); continue; }
                yield return PlayChapter(pick.Value);
                int done = System.Array.IndexOf(Order, pick.Value);
                justUnlocked = UnlockAfter(pick.Value);
                focus = Mathf.Min(done + 1, Order.Length - 1);
            }
        }

        IEnumerator TitlePage()
        {
            Current = Chapter.Title;
            pc.InputEnabled = false;
            ui.ShowHud(false);
            Stage(Chapter.Prologue);
            Place(player, "Anchor_PlayerSpawn");
            var t = layout.Get("Cam_Title");
            // turn the shot left so the island sits on the right and the title block reads on the left
            cam.Cut(t.position, Quaternion.Euler(0f, -16f, 0f) * t.rotation * Quaternion.Euler(-4f, 0f, 0f));
            sky.PinEarth(cam.Camera, new Vector2(0.76f, 0.8f));
            sky.EarthPhase = 0.3f;
            sky.SetMood(Chapter.Title, true);
            yield return ui.FadeTo(0f, 1.5f);
            yield return ui.Title(null);
        }

        List<GameUI.MapNode> MapNodes(int justUnlocked)
        {
            int unlocked = PlayerPrefs.GetInt(UnlockKey, 0);
            var list = new List<GameUI.MapNode>();
            for (int i = 0; i < Order.Length; ++i)
            {
                vignettes.TryGetValue(Order[i], out var tex);
                list.Add(new GameUI.MapNode { Info = StoryText.Info(Order[i]), Vignette = tex, Unlocked = i <= unlocked, JustUnlocked = i == justUnlocked });
            }
            return list;
        }

        IEnumerator PlayChapter(Chapter c)
        {
            yield return ui.FadeTo(1f, 0.6f);
            if (c == Chapter.Prologue)
            {
                Stage(Chapter.Prologue);
                yield return WorldIntro();
            }
            Current = c;
            PlayerPrefs.SetInt(SaveKey, (int)c);
            PlayerPrefs.Save();
            var info = StoryText.Info(c);
            vignettes.TryGetValue(c, out var tex);
            float ready = 0f;
            var card = StartCoroutine(ui.ChapterCard(info, tex, () => ready));
            yield return null;
            Stage(c);
            ready = 0.6f;
            yield return null;
            ready = 1f;
            yield return card;
            ui.ShowHud(true);
            ui.SetQuest(info.Quest);
            bool finished = false;
            chapterRun = StartCoroutine(RunChapterBody(c, () => finished = true));
            while (!finished) yield return null;
            chapterRun = null;
            pc.InputEnabled = false;
            player.SetMoveSpeed(0f);
            ui.SetQuest(null);
            SetMarker(null, null);
            ui.ShowHud(false);
            yield return ui.FadeTo(1f, 0.6f);
        }

        IEnumerator RunChapterBody(Chapter c, System.Action done)
        {
            switch (c)
            {
                case Chapter.Prologue: yield return Prologue(); break;
                case Chapter.One: yield return ChapterOne(); break;
                case Chapter.Two: yield return ChapterTwo(); break;
                case Chapter.Interlude: yield return Interlude(); break;
                case Chapter.Three: yield return ChapterThree(); break;
                case Chapter.Finale: yield return Finale(); break;
                case Chapter.Epilogue: yield return Epilogue(); break;
            }
            done();
        }

        void Update()
        {
            if (player == null) return;
            if (pc.InputEnabled && !pausing) RecoverFromFall();
            if (markerTarget != null) ui.MarkerDistance = Flat(markerTarget.position - player.transform.position).magnitude;
            bool inChapter = Current != Chapter.Title && chapterRun != null && !pausing && !puzzleOpen && !ui.InOverlay;
            if (inChapter && GameInput.Down(Key.Escape)) StartCoroutine(PauseMenu());
        }

        void RecoverFromFall()
        {
            Vector3 p = player.transform.position;
            if (p.y < -4f)
            {
                Vector3 back = hasSafePosition ? safePosition : layout.Pos("Anchor_PlayerSpawn");
                pc.Teleport(back + Vector3.up * .08f, hasSafePosition ? safeYaw : 0f);
                player.SetMoveSpeed(0f);
                cam.FollowPlayer(true);
                ui.Toast("海边风大，回到刚才的小路上。", 3f);
                return;
            }
            if (Time.time < nextSafeRecord) return;
            nextSafeRecord = Time.time + 1f;
            // Four support probes keep a last-safe point away from cliff and pier edges.
            foreach (var offset in new[] { Vector3.forward, Vector3.back, Vector3.left, Vector3.right })
                if (!Physics.Raycast(p + offset * .3f + Vector3.up * .18f, Vector3.down, out var h, .45f, WorldMask, QueryTriggerInteraction.Ignore)
                    || h.normal.y < .7f) return;
            safePosition = p;
            safeYaw = player.transform.eulerAngles.y;
            hasSafePosition = true;
        }

        IEnumerator PauseMenu()
        {
            pausing = true;
            var info = StoryText.Info(Current);
            GameUI.PauseChoice choice = GameUI.PauseChoice.Resume;
            yield return ui.Pause(info.Number.Replace(" ", "") + " · " + info.Title, ch => choice = ch);
            pausing = false;
            if (choice == GameUI.PauseChoice.Resume) yield break;
            // leave the chapter: stop its script and tidy everything it may have left open
            if (chapterRun != null) StopCoroutine(chapterRun);
            if (flow != null) StopCoroutine(flow);
            StopChapterEffects();
            chapterRun = null;
            if (puzzleOpen) ClosePuzzle();
            pc.InputEnabled = false;
            ui.HideDialogue();
            ui.ShowLampPanel(false);
            ui.SetPrompt(null);
            ui.SetQuest(null);
            ui.SetObjective(null, null);
            SetMarker(null, null);
            ui.ShowHud(false);
            yield return ui.FadeTo(1f, 0.6f);
            if (choice == GameUI.PauseChoice.ClearProgress)
            {
                PlayerPrefs.DeleteKey(UnlockKey);
                PlayerPrefs.DeleteKey(SaveKey);
                PlayerPrefs.Save();
            }
            flow = StartCoroutine(choice == GameUI.PauseChoice.Map ? JourneyFromMap() : Journey(null));
        }

        IEnumerator JourneyFromMap()
        {
            int focus = System.Array.IndexOf(Order, Current);
            Current = Chapter.Title;
            int justUnlocked = -1;
            while (true)
            {
                Chapter? pick = null;
                yield return ui.JourneyMap(MapNodes(justUnlocked), Mathf.Max(0, focus), c => pick = c);
                if (!pick.HasValue) { flow = StartCoroutine(Journey(null)); yield break; }
                yield return PlayChapter(pick.Value);
                justUnlocked = UnlockAfter(pick.Value);
                focus = Mathf.Min(System.Array.IndexOf(Order, pick.Value) + 1, Order.Length - 1);
                Current = Chapter.Title;
            }
        }

        int UnlockAfter(Chapter finished)
        {
            int next = System.Array.IndexOf(Order, finished) + 1;
            if (next <= PlayerPrefs.GetInt(UnlockKey, 0) || next >= Order.Length) return -1;
            PlayerPrefs.SetInt(UnlockKey, next);
            PlayerPrefs.Save();
            return next;
        }

        Coroutine ChapterEffect(IEnumerator effect)
        {
            var routine = StartCoroutine(effect);
            chapterEffects.Add(routine);
            return routine;
        }

        void StopChapterEffects()
        {
            foreach (var routine in chapterEffects) if (routine != null) StopCoroutine(routine);
            chapterEffects.Clear();
            foreach (var go in transientObjects) if (go != null) Destroy(go);
            transientObjects.Clear();
        }

        void SetMarker(string label, Transform target)
        {
            markerTarget = target;
            ui.SetMarker(label, target != null ? target.position : (Vector3?)null);
        }

        // ------------------------------------------------------------------ opening
        // 开篇: before the prologue the island introduces itself — the planet, the Earth and its
        // borrowed light, light trees and light fruit, the copper shades, the long night, the
        // islanders' glow, and then each of the people in the story. Tab skips it.
        IEnumerator WorldIntro()
        {
            bool skipped = false;
            Current = Chapter.Prologue;
            pc.InputEnabled = false;
            ui.ShowHud(false);
            Place(player, "Anchor_PlayerSpawn");
            postman.gameObject.SetActive(true);
            Place(postman, "Anchor_VillageGate");
            dengbo.gameObject.SetActive(true);
            Place(dengbo, "NPC_DengBo_Box");
            abo.gameObject.SetActive(true);
            Place(abo, "NPC_ABo_Door");
            aying.gameObject.SetActive(true);
            Place(aying, "NPC_AYing");
            foreach (var a in new[] { player, aying, postman, abo, dengbo }) a.Play("Locomotion", 0f);
            dengbo.Play("Sit_Idle", 0f);
            roadCrowd.SetVisibleInstant(false);
            Vector3 center = layout.Pos("Anchor_PlayerSpawn");
            StartCoroutine(ui.Letterbox(true));
            for (int i = 0; i < StoryText.Intro.Length && !skipped; i++)
            {
                var beat = StoryText.Intro[i];
                IntroFrame(beat.Shot, center, out Vector3 from, out Vector3 look, out float focus);
                if (beat.Shot == StoryText.IntroShot.Glow) { roadCrowd.SetVisibleInstant(true); pierCrowd.SetVisibleInstant(true); }
                if (i > 0) yield return ui.FadeTo(1f, 0.45f);
                cam.Cut(from, Quaternion.LookRotation(look - from, Vector3.up));
                if (beat.Shot == StoryText.IntroShot.Planet) sky.PinEarth(cam.Camera, new Vector2(0.7f, 0.8f));
                else if (beat.Shot == StoryText.IntroShot.Earth || beat.Shot == StoryText.IntroShot.LongNight) sky.PinEarth(cam.Camera, new Vector2(0.5f, 0.66f));
                else sky.UnpinEarth();
                // a slow push in for the whole beat
                Vector3 to = from + (look - from).normalized * Mathf.Min(1.6f, Vector3.Distance(from, look) * 0.18f);
                cam.ShotLookAt(to, look, 0.12f);
                if (focus > 0f) ChapterLook.Instance?.Focus(focus); else ChapterLook.Instance?.ClearFocus();
                Coroutine phase = beat.Shot == StoryText.IntroShot.LongNight ? StartCoroutine(IntroLongNight()) : null;
                yield return ui.FadeTo(0f, i == 0 ? 1.4f : 0.6f);
                yield return ui.IntroBeat(beat.Heading, beat.Body, () => skipped = true);
                if (phase != null) StopCoroutine(phase);
                sky.EarthPhase = 0.3f;
            }
            ChapterLook.Instance?.ClearFocus();
            yield return ui.FadeTo(1f, 0.6f);
            sky.UnpinEarth();
            ui.HideIntroText();
            yield return ui.Letterbox(false, 0.01f);
            roadCrowd.SetVisibleInstant(false);
        }

        Vector3 IslandCenter()
        {
            var g = IslandLayout.FindChild(layout.IslandRoot.transform, "IslandGround");
            var c = g != null ? g.GetComponent<Collider>() : null;
            return c != null ? c.bounds.center : layout.Pos("Anchor_PlayerSpawn");
        }

        // The long night, shown on the Earth: the lit edge narrows to a thread and returns.
        IEnumerator IntroLongNight()
        {
            yield return new WaitForSeconds(1.2f);
            for (float t = 0f; t < 1f; t += Time.deltaTime / 6f)
            {
                sky.EarthPhase = Mathf.Lerp(0.3f, 0.006f, Mathf.SmoothStep(0f, 1f, t));
                yield return new WaitForSeconds(0.08f);
            }
            sky.EarthPhase = 0.006f;
        }

        void IntroFrame(StoryText.IntroShot shot, Vector3 center, out Vector3 from, out Vector3 look, out float focus)
        {
            focus = 0f;
            switch (shot)
            {
                case StoryText.IntroShot.Planet:
                {
                    // far out over the sea, the whole crescent island small below the sky
                    Vector3 away = Flat(center - IslandCenter()).normalized;
                    from = IslandCenter() + away * 78f + Vector3.up * 30f + Vector3.Cross(Vector3.up, away) * 12f;
                    look = IslandCenter() + Vector3.up * 14f;
                    break;
                }
                case StoryText.IntroShot.Earth:
                case StoryText.IntroShot.LongNight:
                {
                    // standing on the pier, looking out to the open sea and up at the sky
                    Vector3 pier = layout.Pos(shot == StoryText.IntroShot.Earth ? "Target_Pier" : "Anchor_FlagpoleHook");
                    Vector3 away = Flat(pier - IslandCenter()).normalized;
                    from = pier + Vector3.up * (shot == StoryText.IntroShot.Earth ? 1.6f : 0.4f) - away * 1.5f;
                    look = from + away * 20f + Vector3.up * 6.5f;
                    break;
                }
                case StoryText.IntroShot.LightTree:
                {
                    var tree = layout.Pos("Anchor_GoldenTree");
                    from = Toward(tree, "Target_Pier", 8.5f, 2.4f, 2.2f);
                    look = tree + Vector3.up * 3.2f;
                    break;
                }
                case StoryText.IntroShot.Lamp:
                {
                    // the copper shade on the lamp head, the round window glowing behind it
                    var head = layout.LampHeadPosition(1);
                    var lamp = layout.LampAnchor(1).position;
                    from = Toward(lamp, "Target_Pier", 3.4f, 0f, 1.4f);
                    from.y = head.y - 0.15f;
                    // aim below the head so the shade sits in the upper third, clear of the text
                    look = head - Vector3.up * 1.15f;
                    focus = 3.4f;
                    break;
                }
                case StoryText.IntroShot.Glow:
                {
                    var village = layout.Pos("Village_Windows");
                    from = layout.Get("Cam_Village") != null ? layout.Pos("Cam_Village") : village + new Vector3(12f, 10f, -10f);
                    look = Vector3.Lerp(village, layout.Pos("Anchor_VillageGate"), 0.4f);
                    break;
                }
                default:
                {
                    var actor = shot == StoryText.IntroShot.AYing ? aying : shot == StoryText.IntroShot.ABo ? abo
                              : shot == StoryText.IntroShot.Postman ? postman : shot == StoryText.IntroShot.DengBo ? dengbo : player;
                    var t = actor.transform;
                    float h = shot == StoryText.IntroShot.DengBo ? 0.95f : 1.25f;
                    // aim low so the face sits in the upper half, clear of the narration
                    from = t.position + t.forward * 2.9f + t.right * 1.0f + Vector3.up * (h + 0.15f);
                    look = t.position + Vector3.up * (h - 0.55f);
                    focus = 2.6f;
                    break;
                }
            }
        }

        // Each place on the journey map is a real view of the island, rendered once at boot while
        // the screen is still black. URP render requests draw straight into each texture; the old
        // Camera.Render() path could leave one frame of a 512px viewport on the back buffer, which
        // players saw as the picture suddenly shrinking into a corner with the rest blank.
        IEnumerator RenderVignettes()
        {
            if (vignettes.Count > 0) yield break;
            var shots = new Dictionary<Chapter, (Vector3 pos, Vector3 at)>
            {
                { Chapter.Prologue, (layout.Pos("Cam_Pier"), layout.Pos("Anchor_FlagpoleHook")) },
                { Chapter.One, (Toward(layout.Pos("Target_Bench"), "Anchor_PlayerSpawn", 7f, 3.2f, 2f), layout.Pos("Target_Bench") + Vector3.up * 0.8f) },
                { Chapter.Two, (Toward(layout.Pos("Target_Window"), "Anchor_PlayerSpawn", 6.5f, 1.2f, -2.2f), layout.Pos("Target_Window")) },
                { Chapter.Interlude, (Toward(layout.Pos("Anchor_GoldenTree"), "Anchor_PlayerSpawn", 9f, 2.6f, 2.5f), layout.Pos("Anchor_GoldenTree") + Vector3.up * 3f) },
                { Chapter.Three, (layout.Pos("Anchor_FlagpoleHook") + PierOff(-5.5f, 1.2f, -5.5f), layout.Pos("Anchor_FlagpoleHook") + Vector3.down * 0.8f) },
                { Chapter.Finale, (layout.Pos("Cam_Title"), layout.Pos("Anchor_PlayerSpawn")) },
                { Chapter.Epilogue, (layout.Get("Cam_Village") != null ? layout.Pos("Cam_Village") : layout.Pos("Cam_Title"), layout.Pos("Village_Windows")) },
            };
            var go = new GameObject("VignetteCamera");
            var vc = go.AddComponent<Camera>();
            vc.CopyFrom(cam.Camera);
            vc.rect = new Rect(0f, 0f, 1f, 1f);
            vc.fieldOfView = 46f;
            vc.enabled = false;
            var vcData = vc.GetUniversalAdditionalCameraData();
            vcData.renderPostProcessing = true;
            vcData.antialiasing = AntialiasingMode.None;
            // the night is very dark at map scale: lift the ambient for these small paintings only
            var amb = RenderSettings.ambientSkyColor;
            var ambE = RenderSettings.ambientEquatorColor;
            foreach (var kv in shots)
            {
                var rt = new RenderTexture(512, 512, 24, RenderTextureFormat.ARGB32) { name = "Vignette_" + kv.Key };
                rt.Create();
                go.transform.SetPositionAndRotation(kv.Value.pos, Quaternion.LookRotation(kv.Value.at - kv.Value.pos, Vector3.up));
                RenderSettings.ambientSkyColor = amb * 3.2f;
                RenderSettings.ambientEquatorColor = ambE * 3.2f;
                var request = new UniversalRenderPipeline.SingleCameraRequest { destination = rt };
                if (UnityEngine.Rendering.RenderPipeline.SupportsRenderRequest(vc, request))
                    UnityEngine.Rendering.RenderPipeline.SubmitRenderRequest(vc, request);
                RenderSettings.ambientSkyColor = amb;
                RenderSettings.ambientEquatorColor = ambE;
                vignettes[kv.Key] = rt;
                yield return null; // one small render per frame keeps the boot hitch-free
            }
            Destroy(go);
        }

        // Puts every actor and light where a chapter begins (also used when continuing a save).
        void Stage(Chapter c)
        {
            StopChapterEffects();
            pc.InputEnabled = false;
            player.SetMoveSpeed(0f);
            player.ReturnToLocomotion(0f);
            hasSafePosition = false;
            soundscape.SetChapter(c);
            storyProps.SetChapter(c);
            ui.SetObjective(null, null);
            ui.SetPrompt(null);
            settings = LampRules.StartState(c == Chapter.Prologue ? Chapter.One : c == Chapter.Interlude ? Chapter.Three : c >= Chapter.Finale ? Chapter.Three : c);
            if (c >= Chapter.Finale) settings = SolvedState();
            if (c == Chapter.Prologue) foreach (var s in settings) s.On = false;
            ApplyLamps(true);
            lantern.Hook = null;
            lantern.FollowHand = player.LeftHand;
            lantern.Brightness = c == Chapter.Prologue ? 0.6f : 1.2f;
            lantern.HasBell = c >= Chapter.Two;
            playerGlow.Strength = c >= Chapter.Finale ? 0.5f : 0f;
            if (horseLamp != null) { Destroy(horseLamp.gameObject); horseLamp = null; }
            SetHarborLamp(c < Chapter.Finale, 1f);
            if (c >= Chapter.Finale) { lantern.Hook = layout.Get("Anchor_FlagpoleHook"); lantern.FollowHand = null; }
            if (roundWindow != null) roundWindow.Set(c != Chapter.Two, true);
            bool villageLit = c != Chapter.Three && c != Chapter.Finale;
            foreach (var w in villageWindows) w.Set(villageLit || c == Chapter.Three, true);
            pierCrowd.SetVisibleInstant(c == Chapter.Prologue || c == Chapter.Interlude || c == Chapter.Three);
            roadCrowd.SetVisibleInstant(c == Chapter.Interlude || c == Chapter.Three);
            pierCrowd.SetRaised(c == Chapter.Interlude || c == Chapter.Three);
            roadCrowd.SetRaised(c == Chapter.Interlude || c == Chapter.Three);
            extraPollution = c == Chapter.Interlude || c == Chapter.Three ? 0.75f : 0f;
            // 07: 序章约三分之一亮 → 第一夜细弧 → 第二夜发丝 → 第三夜几乎看不见 → 终章亮起新的边
            sky.SetMood(c, true);
            sky.UnpinEarth();
            sky.EarthPhase = c <= Chapter.Prologue ? 0.3f : c == Chapter.One ? 0.08f : c == Chapter.Two ? 0.03f : c <= Chapter.Three ? 0.01f : c == Chapter.Finale ? 0.006f : 0.05f;
            UpdatePollution();
            if (flower != null) flower.gameObject.SetActive(c >= Chapter.Epilogue);
            Place(aying, "NPC_AYing");
            aying.gameObject.SetActive(c == Chapter.Prologue || c >= Chapter.Epilogue);
            Place(postman, c >= Chapter.Epilogue ? "NPC_Postman" : "Anchor_VillageGate");
            postman.gameObject.SetActive(c == Chapter.One || c >= Chapter.Epilogue);
            Place(abo, "NPC_ABo_Door");
            abo.gameObject.SetActive(c == Chapter.Prologue || c == Chapter.Two || c >= Chapter.Finale);
            Place(dengbo, "NPC_DengBo_Box");
            dengbo.gameObject.SetActive(c >= Chapter.Three);
            foreach (var a in new[] { aying, postman, abo, dengbo })
            {
                a.SetMoveSpeed(0f);
                if (a.gameObject.activeSelf) a.Play("Locomotion", 0f);
            }
            // The pier keeper waits seated during the crisis and reunion. Stage used to put
            // him in standing locomotion on his seat anchor, crowding the finale close-up.
            if (c == Chapter.Three || c == Chapter.Finale) dengbo.Play("Sit_Idle", 0f);
            if (boat != null) boat.position = layout.Pos("Anchor_Boat") + (c == Chapter.Prologue || c >= Chapter.Epilogue ? Vector3.zero : PierOff(0f, 0f, 80f));
        }

        static LampSetting[] SolvedState() => new[]
        {
            new LampSetting { Direction = 0, Wide = false, On = true },
            new LampSetting { Direction = 1, Wide = true, On = true },
            new LampSetting { Direction = 0, Wide = false, On = true },
        };

        // ------------------------------------------------------------------ chapters
        IEnumerator Prologue()
        {
            Stage(Chapter.Prologue);
            Vector3 pier = layout.Pos("Target_Pier");
            Vector3 behind = pier + PierOff(0f, 0f, -2.4f);
            PlaceAt(player, behind, PierYaw(true));
            Place(aying, "NPC_AYing");
            aying.FaceTowards(player.transform.position);
            cam.Cut(layout.Get("Cam_Pier").position, layout.Get("Cam_Pier").rotation);
            yield return ui.FadeTo(0f, 1.5f);
            yield return ui.Say(StoryText.PrologueOpening);
            // 阿萤 jumps off the boat and runs to him
            Vector3 meet = player.transform.position + player.transform.forward * 0.85f;
            yield return Walk(aying, meet, aying.RunSpeed * 0.8f);
            aying.FaceTowards(player.transform.position);
            cam.ShotLookAt(player.transform.position + PierOff(-2.2f, 1.3f, 1.6f), Vector3.Lerp(player.transform.position, aying.transform.position, 0.5f) + Vector3.up * 0.7f, 1.2f);
            yield return aying.PlayAndWait("Kneel_Down");
            lantern.Brightness = 1.6f;
            ChapterEffect(LightStream(aying.RightHand != null ? aying.RightHand : aying.transform, lantern.transform, GlowAYing));
            yield return ui.SayOne(StoryText.PrologueAYing[0]);
            yield return aying.PlayAndWait("Kneel_StandUp");
            yield return ui.SayOne(StoryText.PrologueAYing[1]);
            ui.HideDialogue();
            // back to the boat; the boat sails off and her light becomes a star
            ChapterEffect(Walk(aying, layout.Pos("NPC_AYing") + PierOff(0f, 0f, 3.5f), aying.RunSpeed * 0.7f));
            player.Play("Wave");
            cam.ShotLookAt(player.transform.position + PierOff(1.6f, 1.8f, -2.6f), layout.Pos("Anchor_Boat") + Vector3.up, 0.8f);
            yield return new WaitForSeconds(2.2f);
            aying.gameObject.SetActive(false);
            if (boat != null) ChapterEffect(MoveOver(boat, boat.position + PierOff(0f, 0f, 70f), 14f));
            yield return ui.Say(StoryText.PrologueAfterBoat);
            yield return ui.FadeTo(1f, 1.2f);
            pierCrowd.SetVisibleInstant(false);
            // that night, 阿婆 gives him the three copper shields
            Place(abo, "NPC_ABo_Door");
            Vector3 front = abo.transform.position + abo.transform.forward * 1.3f;
            PlaceAt(player, front, abo.transform.eulerAngles.y + 180f);
            abo.FaceTowards(player.transform.position);
            player.Play("Locomotion", 0f);
            cam.ShotLookAt(Vector3.Lerp(abo.transform.position, player.transform.position, 0.5f) + abo.transform.right * 2.6f + Vector3.up * 1.4f,
                Vector3.Lerp(abo.transform.position, player.transform.position, 0.5f) + Vector3.up * 1.1f, 3f);
            cam.transform.SetPositionAndRotation(Vector3.Lerp(abo.transform.position, player.transform.position, 0.5f) + abo.transform.right * 2.6f + Vector3.up * 1.4f, cam.transform.rotation);
            yield return ui.FadeTo(0f, 1f);
            yield return ui.Say(StoryText.PrologueABo, i =>
            {
                if (i == 1) abo.Play("Talk");
                if (i == 3) player.Play("Idle_Sad");
                if (i == 4) { abo.Play("Locomotion"); player.Play("Locomotion"); }
            });
            yield return ui.Card(StoryText.PrologueCard);
            yield return ui.FadeTo(1f, 0.8f);
        }

        IEnumerator ChapterOne()
        {
            Stage(Chapter.One);
            Place(player, "Anchor_PlayerSpawn");
            cam.FollowPlayer(true);
            yield return ui.FadeTo(0f, 1.2f);
            // the postman's bell comes down the road
            postman.gameObject.SetActive(true);
            Place(postman, "Anchor_VillageGate");
            var walkIn = ChapterEffect(Walk(postman, layout.Pos("NPC_Postman"), postman.WalkSpeed, ringBell: true));
            cam.ShotLookAt(Toward(layout.Pos("Target_Path"), "Anchor_PlayerSpawn", 5f, 3.2f, 1.5f), postman.transform.position + Vector3.up, 0.7f);
            yield return ui.Say(StoryText.Chapter1Opening);
            yield return walkIn;
            postman.transform.rotation = layout.Get("NPC_Postman").rotation;
            cam.FollowPlayer(true);
            pc.InputEnabled = true;
            ui.SetObjective("路口有人停下了，过去看看", "WASD 行走 · 按住右键环顾");
            SetMarker("路口", postman.transform);
            yield return WaitTalk(postman, "和邮差爷爷说话");
            yield return Converse(postman, StoryText.Chapter1Ask);
            wrongTurnSaid = false;
            yield return Puzzle(Chapter.One);
            // he sits on the bench in the new light and tells his story
            pc.InputEnabled = false;
            yield return Walk(postman, SeatPos("NPC_Bench") + layout.Get("NPC_Bench").forward * 0.5f, postman.WalkSpeed);
            Place(postman, "NPC_Bench");
            yield return postman.PlayAndWait("Sit_Down");
            postman.Play("Sit_Talking");
            Vector3 seat = SeatPos("NPC_Bench");
            PlaceAt(player, seat + layout.Get("NPC_Bench").forward * 1.4f + layout.Get("NPC_Bench").right * 0.4f, 0f);
            player.FaceTowards(seat);
            cam.ShotLookAt(seat + layout.Get("NPC_Bench").forward * 2.6f + layout.Get("NPC_Bench").right * -1.8f + Vector3.up * 1.3f, seat + Vector3.up * 0.8f, 1.2f);
            yield return ui.Say(StoryText.Chapter1Bench);
            postman.Play("Sit_Idle");
            yield return ui.SayOne(StoryText.Chapter1Bell[0]);
            lantern.HasBell = true;
            lantern.RingBell();
            yield return ui.Say(new[] { StoryText.Chapter1Bell[1], StoryText.Chapter1Bell[2] });
            yield return ui.Card(StoryText.Chapter1Done);
            yield return ui.FadeTo(1f, 0.8f);
        }

        IEnumerator ChapterTwo()
        {
            Stage(Chapter.Two);
            Place(player, "Anchor_PlayerSpawn");
            Place(abo, "NPC_ABo_Window");
            abo.Play("Sit_Writing", 0f);
            cam.ShotLookAt(Toward(layout.Pos("Target_Window"), "Anchor_PlayerSpawn", 6f, 0.8f, -2.5f), layout.Pos("Target_Window"), 2f);
            cam.transform.position = Toward(layout.Pos("Target_Window"), "Anchor_PlayerSpawn", 6f, 0.8f, -2.5f);
            yield return ui.FadeTo(0f, 1.2f);
            yield return ui.Say(StoryText.Chapter2Opening);
            cam.FollowPlayer(true);
            yield return Puzzle(Chapter.Two);
            pc.InputEnabled = false;
            roundWindow?.Set(true);
            cam.ShotLookAt(Toward(layout.Pos("Target_Window"), "Anchor_PlayerSpawn", 4.2f, 0.4f, -1.8f), layout.Pos("Target_Window"), 1f);
            yield return new WaitForSeconds(1.2f);
            yield return ui.Say(StoryText.Chapter2Lit);
            yield return ui.FadeTo(1f, 0.8f);
            yield return ui.FadeTo(0.25f, 0.8f);
            Transform tree = layout.Get("Anchor_GoldenTree");
            yield return ui.Say(StoryText.Chapter2Story, i =>
            {
                if (i == 1) cam.ShotLookAt(Toward(layout.Pos("Anchor_GoldenTree"), "Anchor_PlayerSpawn", 7f, 2.5f, -2f), tree.position + Vector3.up * 2f, 0.3f);
                if (i == 8) cam.ShotLookAt(Toward(tree.position, "Anchor_PlayerSpawn", 4.4f, 1.2f, -1f), tree.position + Vector3.up * 2.6f, 0.4f);
                if (i == 10) cam.ShotLookAt(Toward(layout.Pos("Target_Window"), "Anchor_PlayerSpawn", 4.2f, 0.4f, -1.8f), layout.Pos("Target_Window"), 0.6f);
            });
            yield return ui.FadeTo(0f, 0.5f);
            yield return ui.Card(StoryText.Chapter2Done);
            yield return ui.FadeTo(1f, 0.8f);
        }

        IEnumerator Interlude()
        {
            Stage(Chapter.Interlude);
            Vector3 pierStart = layout.Pos("Target_Pier") + PierOff(0f, 0f, -3.2f);
            PlaceAt(player, pierStart, PierYaw(true));
            cam.ShotLookAt(pierStart + PierOff(-4.5f, 3f, -2f), layout.Pos("Target_Pier") + PierOff(0f, 1f, 4f), 2f);
            cam.transform.position = pierStart + PierOff(-4.5f, 3f, -2f);
            yield return ui.FadeTo(0f, 1.2f);
            yield return ui.Say(StoryText.InterludeHarbor);
            // he slips away, alone, to the golden tree
            player.Play("Locomotion");
            cam.FollowPlayer(true);
            pc.InputEnabled = true;
            ui.SetObjective("一个人走回岬角，到金色光树下", null);
            SetMarker("金色光树", layout.Get("Anchor_GoldenTree"));
            yield return WaitReach(layout.Pos("Anchor_GoldenTree"), 3.2f);
            pc.InputEnabled = false;
            player.FaceTowards(layout.Pos("Anchor_GoldenTree"));
            cam.ShotLookAt(player.transform.position + player.transform.right * 2.2f + player.transform.forward * 1.5f + Vector3.up * 1.2f, player.transform.position + Vector3.up * 0.9f, 1.2f);
            ui.SetObjective(null, null);
            yield return ui.SayOne(StoryText.InterludeAlone[0]);
            lantern.Brightness = 0f;
            yield return ui.SayOne(StoryText.InterludeAlone[1]);
            player.Play("Idle_Sad");
            yield return ui.SayOne(StoryText.InterludeAlone[2]);
            yield return ui.FadeTo(1f, 1f);
            postman.gameObject.SetActive(true);
            PlaceAt(postman, player.transform.position + player.transform.forward * 1.3f, 0f);
            postman.FaceTowards(player.transform.position);
            lantern.RingBell();
            yield return ui.FadeTo(0.2f, 1f);
            storyProps.ShowLetter(true);
            yield return ui.Say(new[] { StoryText.InterludeAlone[3], StoryText.InterludeAlone[4] });
            yield return ui.Letter();
            storyProps.ShowLetter(false);
            yield return ui.FadeTo(0f, 0.8f);
            postman.gameObject.SetActive(false);
            player.Play("Locomotion");
            yield return ui.SayOne(StoryText.InterludeAfterLetter[0]);
            yield return ui.SayOne(StoryText.InterludeAfterLetter[1]);
            lantern.Brightness = 1.2f;
            lantern.RingBell();
            yield return ui.SayOne(StoryText.InterludeAfterLetter[2]);
            ui.HideDialogue();
        }

        IEnumerator ChapterThree()
        {
            Stage(Chapter.Three);
            if (!pc.InputEnabled) { Place(player, "Anchor_GoldenTree"); player.transform.position = Toward(player.transform.position, "Anchor_PlayerSpawn", 2.5f, 0f, 0f); }
            cam.FollowPlayer(true);
            yield return ui.FadeTo(0f, 0.6f);
            pc.InputEnabled = true;
            ui.SetObjective("跑到码头去", "按住 Shift 跑。天被照得白蒙蒙的，一颗星也看不见。");
            SetMarker("码头", layout.Get("Target_Pier"));
            yield return WaitReach(layout.Pos("Target_Pier") + PierOff(0f, 0f, -3f), 2.6f);
            pc.InputEnabled = false;
            player.FaceTowards(layout.Pos("Target_Pier") + Vector3.back * 5f);
            cam.ShotLookAt(player.transform.position + PierOff(-3.5f, 2.6f, 1f), player.transform.position + PierOff(0f, 1.2f, 3f), 1.2f);
            ui.SetObjective(null, null);
            yield return ui.Say(StoryText.Chapter3Shout, i =>
            {
                if (i == 0) player.Play("Point_Forward");
                if (i == 2)
                {
                    pierCrowd.SetRaised(false);
                    roadCrowd.SetRaised(false);
                    foreach (var w in villageWindows) w.Set(false);
                    extraPollution = 0f;
                    UpdatePollution();
                }
            });
            player.ReturnToLocomotion();
            dengbo.gameObject.SetActive(true);
            Place(dengbo, "NPC_DengBo_Box");
            dengbo.Play("Sit_Idle", 0f);
            if (harborLantern != null) SetHarborLamp(true, 0.5f);
            else
            {
                horseLamp = Lantern.Create();
                horseLamp.transform.localScale = Vector3.one * 1.8f;
                horseLamp.Hook = layout.Get("Anchor_FlagpoleHook");
                horseLamp.Brightness = 0.5f;
            }
            pc.InputEnabled = true;
            ui.SetObjective("去栈桥尽头找灯伯", null);
            SetMarker("灯伯", dengbo.transform);
            yield return WaitTalk(dengbo, "和灯伯说话");
            dengbo.Play("Sit_Talking");
            yield return Converse(dengbo, StoryText.Chapter3DengBo, faceNpc: false);
            dengbo.Play("Sit_Idle");
            yield return Puzzle(Chapter.Three);
            pc.InputEnabled = false;
            Vector3 hook = layout.Pos("Anchor_FlagpoleHook");
            cam.ShotLookAt(hook + PierOff(-3.2f, -0.4f, -3.2f), hook, 1f);
            yield return new WaitForSeconds(0.6f);
            yield return ui.SayOne(StoryText.Chapter3LampOut[0]);
            if (horseLamp != null) horseLamp.Brightness = 0f;
            SetHarborLamp(true, 0f);
            yield return ui.Say(new[] { StoryText.Chapter3LampOut[1], StoryText.Chapter3LampOut[2], StoryText.Chapter3LampOut[3] });
            cam.FollowPlayer(true);
            pc.InputEnabled = true;
            ui.SetObjective("最暗的地方，是旗杆上", null);
            SetMarker("旗杆", layout.Get("Anchor_FlagpoleHook"));
            yield return WaitReachPrompt(new Vector3(hook.x, player.transform.position.y, hook.z), 1.8f, "把灯笼挂上旗杆");
            SetMarker(null, null);
            pc.InputEnabled = false;
            ui.SetObjective(null, null);
            player.FaceTowards(hook);
            player.Play("Reach_Out");
            yield return new WaitForSeconds(1.1f);
            lantern.FollowHand = null;
            lantern.Hook = layout.Get("Anchor_FlagpoleHook");
            if (horseLamp != null) { Destroy(horseLamp.gameObject); horseLamp = null; }
            SetHarborLamp(false, 0f);
            lantern.RingBell();
            yield return new WaitForSeconds(0.8f);
            player.ReturnToLocomotion();
            PlaceAt(player, player.transform.position - player.transform.forward * 0.8f, player.transform.eulerAngles.y);
            cam.ShotLookAt(hook + PierOff(2.5f, 0.2f, -3.6f), hook + Vector3.down * 0.6f, 0.8f);
            yield return ui.Say(StoryText.Chapter3Hung);
            yield return ui.Card(StoryText.Chapter3Done);
            yield return ui.FadeTo(1f, 0.8f);
        }

        IEnumerator Finale()
        {
            Stage(Chapter.Finale);
            Vector3 hook = layout.Pos("Anchor_FlagpoleHook");
            PlaceAt(player, new Vector3(hook.x, layout.Pos("NPC_DengBo_Box").y, hook.z) + PierOff(-0.6f, 0f, -1.3f), PierYaw(false));
            pierCrowd.SetVisibleInstant(true);
            pierCrowd.SetRaised(false);
            playerGlow.Strength = 0f;
            cam.ShotLookAt(player.transform.position + player.transform.forward * 1.4f + Vector3.up * 1.2f + player.transform.right * 0.4f, player.transform.position + Vector3.up * 0.9f, 2f);
            cam.transform.position = player.transform.position + player.transform.forward * 1.4f + Vector3.up * 1.2f;
            yield return ui.FadeTo(0f, 1.6f);
            yield return ui.SayOne(StoryText.FinaleHands[0]);
            playerGlow.Strength = 0.5f;
            yield return ui.Say(new[] { StoryText.FinaleHands[1], StoryText.FinaleHands[2], StoryText.FinaleHands[3] });
            // the boat comes in; 阿萤 jumps down and finds him
            if (boat != null) { boat.position = layout.Pos("Anchor_Boat") + PierOff(0f, 0f, 40f); ChapterEffect(MoveOver(boat, layout.Pos("Anchor_Boat"), 6f)); }
            cam.ShotLookAt(player.transform.position + PierOff(-3f, 2.4f, -2.5f), layout.Pos("Anchor_Boat") + Vector3.up, 0.6f);
            yield return new WaitForSeconds(5.5f);
            aying.gameObject.SetActive(true);
            PlaceAt(aying, layout.Pos("NPC_AYing") + PierOff(0f, 0f, 4f), PierYaw(false));
            yield return Walk(aying, player.transform.position + player.transform.forward * 0.9f, aying.RunSpeed * 0.8f);
            aying.FaceTowards(player.transform.position);
            player.FaceTowards(aying.transform.position);
            cam.ShotLookAt(Vector3.Lerp(player.transform.position, aying.transform.position, 0.5f) + player.transform.right * 2.2f + Vector3.up * 1.4f,
                Vector3.Lerp(player.transform.position, aying.transform.position, 0.5f) + Vector3.up * 1f, 1.2f);
            yield return ui.Say(StoryText.FinaleReunion, i => { if (i == 1) { aying.Play("Reach_Out"); player.Play("Reach_Out"); } if (i == 2) player.ReturnToLocomotion(); });
            // the island relights; the golden tree flowers
            ChapterEffect(RelightVillage());
            sky.EarthPhase = 0.05f;
            EnsureFlower();
            flower.gameObject.SetActive(true);
            Transform tree = layout.Get("Anchor_GoldenTree");
            yield return ui.Say(StoryText.FinaleBloom, i =>
            {
                if (i == 1) cam.ShotLookAt(Toward(tree.position, "Anchor_PlayerSpawn", 4.8f, 1.4f, 0f), flower.position, 0.6f);
                if (i == 3) cam.Shot(layout.Get("Cam_Title"), 0.25f);
            });
            yield return ui.Card(StoryText.Theme, 46);
            yield return ui.Card(StoryText.FinaleStar);
            yield return ui.Card(StoryText.FinaleCard);
        }

        IEnumerator Epilogue()
        {
            Stage(Chapter.Epilogue);
            EnsureFlower();
            flower.gameObject.SetActive(true);
            Place(player, "Anchor_PlayerSpawn");
            Place(abo, "NPC_ABo_Door");
            dengbo.Play("Locomotion", 0f);
            Vector3 hook = layout.Pos("Anchor_FlagpoleHook");
            PlaceAt(dengbo, new Vector3(hook.x, layout.Pos("NPC_DengBo_Box").y, hook.z) + PierOff(-0.9f, 0f, -0.6f), 200f);
            cam.FollowPlayer(true);
            pc.InputEnabled = true;
            yield return ui.FadeTo(0f, 1.2f);
            ui.SetObjective("长夜过去了。沿着小路走走吧。", "走近大家，听听他们想说的话。");
            var npcs = new[] { (aying, Speaker.AYing), (postman, Speaker.Postman), (abo, Speaker.ABo), (dengbo, Speaker.DengBo) };
            var heard = new HashSet<Speaker>();
            var talks = new Dictionary<Speaker, int>();
            var away = new HashSet<Speaker>(); // walked off since the last line: the next visit says more
            bool closingShown = false;
            while (true)
            {
                foreach (var (a, who) in npcs)
                {
                    if (!a.gameObject.activeSelf) continue;
                    float d = Flat(a.transform.position - player.transform.position).magnitude;
                    bool fresh = !heard.Contains(who) || away.Contains(who);
                    if (d < 2.2f && fresh)
                    {
                        heard.Add(who);
                        away.Remove(who);
                        talks.TryGetValue(who, out int n);
                        var lines = StoryText.EpilogueLines(who);
                        talks[who] = n + 1;
                        a.FaceTowards(player.transform.position);
                        a.Play(who == Speaker.DengBo ? "Wave" : "Talk");
                        ui.Toast(StoryText.Name(who) + "：“" + lines[n % lines.Length] + "”", 6f);
                        if (who == Speaker.Postman) { lantern.RingBell(); }
                    }
                    else if (d > 4f && heard.Contains(who))
                    {
                        away.Add(who);
                        if (a.CurrentAction == "Talk") a.ReturnToLocomotion();
                    }
                }
                if (heard.Count == 4 && !closingShown)
                {
                    closingShown = true;
                    yield return new WaitForSeconds(6f);
                    pc.InputEnabled = false;
                    yield return ui.Card(StoryText.EpilogueClosing);
                    pc.InputEnabled = true;
                }
                yield return null;
            }
        }

        // ------------------------------------------------------------------ the lamp puzzle
        IEnumerator Puzzle(Chapter c)
        {
            settings = LampRules.StartState(c);
            ApplyLamps(true);
            int unlocked = LampRules.UnlockedLamps(c);
            selected = 0;
            pc.InputEnabled = true;
            cam.FollowPlayer();
            puzzleOpen = false;
            ui.SetObjective(StoryText.Objective(c), "走到灯下按 E 调灯，或按 Tab 远眺三盏灯。");
            int focusLamp = unlocked - 1;
            SetMarker(LampRules.LampNames[focusLamp], layout.LampAnchor(focusLamp));
            while (true)
            {
                var r = LampRules.Evaluate(c, settings);
                if (!puzzleOpen)
                {
                    int near = NearestLamp(unlocked, 2.4f);
                    ui.SetPrompt(near >= 0 ? "调整" + LampRules.LampNames[near] : null, near >= 0 ? layout.LampHeadPosition(near) : (Vector3?)null);
                    if (GameInput.Down(Key.E) && near >= 0) OpenPuzzle(c, near);
                    else if (GameInput.Down(Key.Tab)) OpenPuzzle(c, selected);
                }
                else
                {
                    bool changed = false;
                    for (int i = 0; i < unlocked; ++i)
                        if (GameInput.AnyDown((Key)((int)Key.Digit1 + i), (Key)((int)Key.Numpad1 + i))) { selected = i; changed = true; }
                    var s = settings[selected];
                    if (GameInput.AnyDown(Key.A, Key.LeftArrow)) { s.Direction = LampRules.Wrap(s.Direction - 1); changed = true; }
                    if (GameInput.AnyDown(Key.D, Key.RightArrow)) { s.Direction = LampRules.Wrap(s.Direction + 1); changed = true; }
                    if (GameInput.Down(Key.Space)) { s.Wide = !s.Wide; changed = true; }
                    if (changed)
                    {
                        soundscape.LampTurn(GameInput.Down(Key.Space));
                        ApplyLamps(false);
                        r = LampRules.Evaluate(c, settings);
                        if (c == Chapter.One && !wrongTurnSaid && LampRules.Wrap(settings[0].Direction) == 1)
                        {
                            wrongTurnSaid = true;
                            ui.Toast("邮差爷爷：“" + StoryText.Chapter1WrongTurn[0].Text + "”", 4f);
                        }
                    }
                    ui.SetLampPanel(c, settings, selected, r);
                    ui.SetObjective(StoryText.Objective(c), LampRules.Hint(c, settings, r));
                    for (int i = 0; i < lamps.Length; ++i) lamps[i].Selected = i == selected;
                    if (GameInput.AnyDown(Key.Enter, Key.NumpadEnter))
                    {
                        if (r.Solved)
                        {
                            soundscape.PuzzleSolved();
                            SetMarker(null, null);
                            ClosePuzzle();
                            ui.SetObjective(null, null);
                            yield return new WaitForSeconds(0.8f);
                            yield break;
                        }
                        ui.Toast(LampRules.Hint(c, settings, r), 3f);
                    }
                    if (GameInput.AnyDown(Key.Escape, Key.Tab)) ClosePuzzle();
                }
                yield return null;
            }
        }

        void OpenPuzzle(Chapter c, int lamp)
        {
            puzzleOpen = true;
            selected = lamp;
            pc.InputEnabled = false;
            player.SetMoveSpeed(0f);
            ui.SetPrompt(null);
            ui.ShowLampPanel(true);
            ui.SetLampPanel(c, settings, selected, LampRules.Evaluate(c, settings));
            cam.Shot(layout.Get("Cam_Puzzle"), 1.4f);
        }

        void ClosePuzzle()
        {
            puzzleOpen = false;
            foreach (var l in lamps) l.Selected = false;
            ui.ShowLampPanel(false);
            pc.InputEnabled = true;
            cam.FollowPlayer();
        }

        int NearestLamp(int unlocked, float radius)
        {
            int best = -1;
            float bd = radius;
            for (int i = 0; i < unlocked; ++i)
            {
                float d = Flat(layout.LampAnchor(i).position - player.transform.position).magnitude;
                if (d < bd) { bd = d; best = i; }
            }
            return best;
        }

        void ApplyLamps(bool instant)
        {
            for (int i = 0; i < lamps.Length; ++i)
                lamps[i].Apply(settings[i], layout.AimPoint(i, settings[i].Direction, settings[i].Wide), instant);
            UpdatePollution();
        }

        // Beams aimed at the sky wash it out most; wide shields a little; raised crowd lights a lot.
        void UpdatePollution()
        {
            float p = extraPollution;
            for (int i = 0; i < settings.Length; ++i)
            {
                if (!settings[i].On) continue;
                if (LampRules.Wrap(settings[i].Direction) == 2) p += settings[i].Wide ? 0.42f : 0.3f;
                else if (settings[i].Wide) p += 0.06f;
            }
            sky.Pollution = Mathf.Clamp01(p);
        }

        // ------------------------------------------------------------------ helpers
        IEnumerator Converse(CharacterActor npc, Line[] lines, bool faceNpc = true)
        {
            pc.InputEnabled = false;
            player.SetMoveSpeed(0f);
            ui.SetPrompt(null);
            player.FaceTowards(npc.transform.position);
            if (faceNpc) npc.FaceTowards(player.transform.position);
            Vector3 mid = Vector3.Lerp(player.transform.position, npc.transform.position, 0.5f);
            Vector3 side = Vector3.Cross(Vector3.up, (npc.transform.position - player.transform.position).normalized);
            cam.ShotLookAt(ClearSide(mid, side, 2.6f, 1.5f), mid + Vector3.up * 1.0f, 1.4f);
            yield return ui.Say(lines, i =>
            {
                var who = lines[i].Who;
                if (who != Speaker.Narrator && who != Speaker.Player && npc.CurrentAction == "Locomotion") npc.Play("Talk");
            });
            if (npc.CurrentAction == "Talk") npc.ReturnToLocomotion();
            cam.FollowPlayer();
            pc.InputEnabled = true;
        }

        IEnumerator WaitTalk(CharacterActor npc, string prompt)
        {
            while (true)
            {
                if (pausing) { yield return null; continue; }
                bool near = Flat(npc.transform.position - player.transform.position).magnitude < 2.4f;
                ui.SetPrompt(near ? prompt : null, npc.transform.position + Vector3.up * 1.2f);
                if (near && GameInput.Down(Key.E)) break;
                yield return null;
            }
            ui.SetPrompt(null);
            SetMarker(null, null);
        }

        IEnumerator WaitReach(Vector3 pos, float radius)
        {
            while (pausing || Flat(pos - player.transform.position).magnitude > radius) yield return null;
            SetMarker(null, null);
        }

        IEnumerator WaitReachPrompt(Vector3 pos, float radius, string prompt)
        {
            while (true)
            {
                if (pausing) { yield return null; continue; }
                bool near = Flat(pos - player.transform.position).magnitude < radius;
                ui.SetPrompt(near ? prompt : null, pos + Vector3.up * 1.2f);
                if (near && GameInput.Down(Key.E)) break;
                yield return null;
            }
            ui.SetPrompt(null);
        }

        IEnumerator Walk(CharacterActor a, Vector3 to, float speed, bool ringBell = false)
        {
            if (a.CurrentAction != "Locomotion") a.ReturnToLocomotion(0.2f);
            float bell = 0f;
            while (true)
            {
                Vector3 d = Flat(to - a.transform.position);
                if (d.magnitude < 0.1f) break;
                Vector3 dir = d.normalized;
                a.transform.rotation = Quaternion.RotateTowards(a.transform.rotation, Quaternion.LookRotation(dir), 360f * Time.deltaTime);
                Vector3 p = a.transform.position + dir * Mathf.Min(d.magnitude, speed * Time.deltaTime);
                p.y = GroundY(p, a.transform.position.y);
                a.transform.position = p;
                a.SetMoveSpeed(speed);
                if (ringBell && (bell += Time.deltaTime) > 1.4f) { bell = 0f; PlayChime(a.transform.position, 0.35f); }
                yield return null;
            }
            a.SetMoveSpeed(0f);
        }

        IEnumerator MoveOver(Transform t, Vector3 to, float seconds)
        {
            Vector3 from = t.position;
            for (float k = 0f; k < 1f; k += Time.deltaTime / seconds)
            {
                t.position = Vector3.Lerp(from, to, Mathf.SmoothStep(0f, 1f, k));
                yield return null;
            }
            t.position = to;
        }

        IEnumerator LightStream(Transform from, Transform to, Color color)
        {
            var go = new GameObject("SharedLight");
            transientObjects.Add(go);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.startLifetime = 0.6f;
            main.startSpeed = 0f;
            main.startSize = 0.05f;
            main.startColor = color;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = ps.emission;
            em.rateOverTime = 60f;
            var shape = ps.shape;
            shape.radius = 0.05f;
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = MaterialKit.SoftParticle();
            ps.Play();
            for (float t = 0f; t < 2.6f; t += Time.deltaTime)
            {
                go.transform.position = Vector3.Lerp(from.position, to.position, Mathf.PingPong(t * 1.6f, 1f));
                yield return null;
            }
            ps.Stop();
            Destroy(go, 1f);
        }

        IEnumerator RelightVillage()
        {
            foreach (var w in villageWindows) { w.Set(true); yield return new WaitForSeconds(0.45f); }
            roadCrowd.SetVisible(false);
        }

        void EnsureFlower()
        {
            if (flower != null) return;
            var tree = layout.Get("Anchor_GoldenTree");
            // the user's Tripo flower (A04) when present, else a glowing bud
            var model = Resources.Load<GameObject>("Props/A04_first_flower");
            GameObject f;
            if (model != null)
            {
                f = Instantiate(model);
                f.transform.localScale = Vector3.one * 1.6f;
                f.transform.rotation = Quaternion.LookRotation(Flat(layout.Pos("Anchor_PlayerSpawn") - tree.position)) * model.transform.localRotation;
            }
            else
            {
                f = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                Destroy(f.GetComponent<Collider>());
                f.transform.localScale = Vector3.one * 0.22f;
                f.GetComponent<Renderer>().material = MaterialKit.LitInstance(new Color(1f, 0.9f, 0.6f), new Color(1f, 0.75f, 0.35f) * 3f);
            }
            f.name = "FirstFlower";
            f.transform.position = Toward(tree.position, "Anchor_PlayerSpawn", 1.2f, 2.1f, 0f);
            var l = new GameObject("FlowerLight").AddComponent<Light>();
            l.transform.SetParent(f.transform, false);
            l.transform.localPosition = Vector3.up * 0.2f;
            l.type = LightType.Point;
            l.color = new Color(1f, 0.8f, 0.45f);
            l.range = 2.5f;
            l.intensity = 1.5f;
            flower = f.transform;
        }

        void PlayChime(Vector3 at, float volume)
        {
            var clip = Resources.Load<AudioClip>("Audio/LanternChime");
            if (clip != null) AudioSource.PlayClipAtPoint(clip, at, volume);
        }

        void Place(CharacterActor a, string anchor)
        {
            var t = layout.Get(anchor);
            if (IsSeat(anchor))
            {
                a.transform.SetPositionAndRotation(SeatFloor(t.position), Quaternion.Euler(0f, t.eulerAngles.y, 0f));
                // A01 interior platform sits above the sampled island ground. Its writing
                // chair is raised to the circular sill; retain the measured pose offset.
                if (anchor == "NPC_ABo_Window") a.transform.position += Vector3.up * .38f;
                return;
            }
            PlaceAt(a, t.position, t.eulerAngles.y);
        }

        static bool IsSeat(string anchor) => anchor == "NPC_Bench" || anchor == "NPC_ABo_Window" || anchor == "NPC_DengBo_Box";

        // Seat anchors mark the seat / pelvis; a seated Mixamo clip wants its root on the floor below.
        Vector3 SeatPos(string anchor) => SeatFloor(layout.Pos(anchor));

        static Vector3 SeatFloor(Vector3 seat)
        {
            float floor = seat.y;
            bool found = false;
            foreach (var h in Physics.RaycastAll(seat + Vector3.up * 0.3f, Vector3.down, 2.2f, WorldMask, QueryTriggerInteraction.Ignore))
                if (!found || h.point.y < floor) { floor = h.point.y; found = true; }
            return new Vector3(seat.x, floor, seat.z);
        }

        // Of the two sides of a conversation, frame from the one with a clear line of sight.
        Vector3 ClearSide(Vector3 mid, Vector3 side, float dist, float height)
        {
            Vector3 eye = mid + Vector3.up * 1.1f;
            foreach (float s in new[] { 1f, -1f })
            {
                Vector3 p = mid + side * (dist * s) + Vector3.up * height;
                if (!Physics.Linecast(eye, p, WorldMask, QueryTriggerInteraction.Ignore)) return p;
            }
            return mid - (cam.transform.position - mid).normalized * -dist + Vector3.up * (height + 1.5f);
        }

        void SetHarborLamp(bool present, float level)
        {
            if (harborLantern == null) return;
            harborLantern.gameObject.SetActive(present);
            foreach (var kv in harborLights) if (kv.Key != null) kv.Key.intensity = kv.Value * level;
        }

        void PlaceAt(CharacterActor a, Vector3 pos, float yaw)
        {
            pos.y = GroundY(pos, pos.y);
            if (a == player) pc.Teleport(pos, yaw);
            else a.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
        }

        static float GroundY(Vector3 p, float fallback)
        {
            return Physics.Raycast(p + Vector3.up * 1.6f, Vector3.down, out var hit, 4f, WorldMask, QueryTriggerInteraction.Ignore) ? hit.point.y : fallback;
        }

        // Offsets in the pier's frame: out = from the shore toward the flagpole, side = to its right.
        Vector3 PierOff(float side, float up, float outward)
        {
            Vector3 axis = Flat(layout.Pos("Anchor_FlagpoleHook") - layout.Pos("Target_Pier")).normalized;
            Vector3 right = Vector3.Cross(Vector3.up, axis);
            return right * side + Vector3.up * up + axis * outward;
        }

        float PierYaw(bool outward)
        {
            Vector3 axis = PierOff(0f, 0f, outward ? 1f : -1f);
            return Quaternion.LookRotation(axis).eulerAngles.y;
        }

        // A point `dist` from `from` toward an anchor, raised by `up` and shifted sideways.
        Vector3 Toward(Vector3 from, string anchor, float dist, float up, float side)
        {
            Vector3 d = Flat(layout.Pos(anchor) - from).normalized;
            return from + d * dist + Vector3.up * up + Vector3.Cross(Vector3.up, d) * side;
        }

        static Vector3 Flat(Vector3 v) { v.y = 0f; return v; }
    }
}
