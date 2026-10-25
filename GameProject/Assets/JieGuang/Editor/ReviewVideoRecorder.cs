using System;
using System.Collections;
using System.IO;
using Unity.Collections;
using UnityEditor;
using UnityEditor.Media;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // JieGuang/Record Review Video: enters Play mode with the showcase runner and records the
    // camera (UI included) at 1920×1080, 30 fps in game time, to an H.264/AAC MP4 with the
    // built-in MediaEncoder — no extra packages or tools. The soundtrack is the music bed made
    // by tools/make_review_soundtrack.py; stills requested by the runner are saved as PNGs.
    public static class ReviewVideoRecorder
    {
        const string Pending = "jieguang.recordReviewVideo";

        [MenuItem("JieGuang/Record Review Video")]
        public static void Record() => Start(1);

        // A condensed (~5 min) edition of the same playthrough at a lower bitrate.
        [MenuItem("JieGuang/Record Review Video (Condensed)")]
        public static void RecordCondensed() => Start(2);

        // A ~4 minute highlights cut, edited live: only the marked segments are encoded.
        [MenuItem("JieGuang/Record Review Video (Highlights)")]
        public static void RecordHighlights() => Start(3);

        static void Start(int mode)
        {
            if (EditorApplication.isPlaying) { Debug.LogWarning("[JieGuang] Stop Play mode first."); return; }
            PlayerPrefs.SetInt("jieguang.showcase", mode);
            PlayerPrefs.Save();
            SessionState.SetBool(Pending, true);
            EditorApplication.EnterPlaymode();
        }

        [InitializeOnLoadMethod]
        static void Hook()
        {
            EditorApplication.playModeStateChanged += state =>
            {
                if (state != PlayModeStateChange.EnteredPlayMode || !SessionState.GetBool(Pending, false)) return;
                SessionState.SetBool(Pending, false);
                var go = new GameObject("ReviewVideoCapture");
                UnityEngine.Object.DontDestroyOnLoad(go);
                go.AddComponent<ReviewVideoCapture>();
            };
        }
    }

    public sealed class ReviewVideoCapture : MonoBehaviour
    {
        const int Width = 1920, Height = 1080, Fps = 30, SampleRate = 44100, Channels = 2;
        static readonly string Root = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "art", "demo-video"));

        RenderTexture target;
        Texture2D frame;
        MediaEncoder encoder;
        NativeArray<float> block;
        float[] music;
        int musicPos, frames;
        float fade = 1f;
        string stillDir;

        IEnumerator Start()
        {
            Time.captureFramerate = Fps;
            Directory.CreateDirectory(Root);
            stillDir = Path.Combine(Root, "screenshots");
            Directory.CreateDirectory(stillDir);
            music = LoadWav(Path.Combine(Root, "review_soundtrack_bed.wav"));
            target = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { name = "ReviewVideoTarget" };
            target.Create();
            frame = new Texture2D(Width, Height, TextureFormat.RGBA32, false);
            var video = new VideoTrackAttributes { frameRate = new MediaRational(Fps), width = Width, height = Height, includeAlpha = false, bitRateMode = JgShowcaseRunner.Fast ? VideoBitrateMode.Medium : VideoBitrateMode.High };
            var audio = new AudioTrackAttributes { sampleRate = new MediaRational(SampleRate), channelCount = Channels, language = "zh" };
            string path = Path.Combine(Root, JgShowcaseRunner.Highlights ? "借光岛_作品评审视频_精华版.mp4" : JgShowcaseRunner.Fast ? "借光岛_作品评审视频_精简版.mp4" : "借光岛_作品评审视频.mp4");
            encoder = new MediaEncoder(path, video, audio);
            block = new NativeArray<float>(SampleRate / Fps * Channels, Allocator.Persistent);
            Debug.Log("[JieGuang] Recording review video to " + path);
            var endOfFrame = new WaitForEndOfFrame();
            while (!JgShowcaseRunner.Finished && EditorApplication.isPlaying)
            {
                yield return endOfFrame;
                if (Camera.main == null || Camera.main.targetTexture != target) continue;
                if (!JgShowcaseRunner.Recording) continue; // cut: this frame is not part of the edit
                RenderTexture.active = target;
                frame.ReadPixels(new Rect(0, 0, Width, Height), 0, 0, false);
                RenderTexture.active = null;
                encoder.AddFrame(frame);
                if (JgShowcaseRunner.Ending) fade = Mathf.Max(0f, fade - 1f / (Fps * 6f));
                for (int i = 0; i < block.Length; i++)
                {
                    block[i] = music != null && musicPos < music.Length ? music[musicPos] * fade : 0f;
                    musicPos++;
                }
                encoder.AddSamples(block);
                frames++;
                string still = JgShowcaseRunner.StillRequest;
                if (still != null)
                {
                    JgShowcaseRunner.StillRequest = null;
                    File.WriteAllBytes(Path.Combine(stillDir, still + ".png"), frame.EncodeToPNG());
                }
            }
            Finish();
            EditorApplication.ExitPlaymode();
        }

        // Render the main camera and every screen-space canvas into the 1080p target.
        void LateUpdate()
        {
            // skipped stretches run in real time; recorded ones advance exactly one video frame
            Time.captureFramerate = JgShowcaseRunner.Recording ? Fps : 0;
            var cam = Camera.main;
            if (cam == null || target == null) return;
            if (cam.targetTexture != target) cam.targetTexture = target;
            foreach (var canvas in FindObjectsByType<Canvas>(FindObjectsSortMode.None))
            {
                if (!canvas.isRootCanvas) continue;
                if (canvas.renderMode == RenderMode.ScreenSpaceOverlay || (canvas.renderMode == RenderMode.ScreenSpaceCamera && canvas.worldCamera != cam))
                {
                    canvas.renderMode = RenderMode.ScreenSpaceCamera;
                    canvas.worldCamera = cam;
                    canvas.planeDistance = canvas.sortingOrder >= 40 ? 0.4f : 0.5f;
                }
            }
        }

        void Finish()
        {
            if (encoder != null) { encoder.Dispose(); encoder = null; }
            if (block.IsCreated) block.Dispose();
            Time.captureFramerate = 0;
            if (Camera.main != null && Camera.main.targetTexture == target) Camera.main.targetTexture = null;
            Debug.Log("[JieGuang] Review video finished: " + frames + " frames (" + (frames / (float)Fps).ToString("F1") + " s)");
        }

        void OnDestroy() { if (encoder != null) Finish(); }

        static float[] LoadWav(string path)
        {
            if (!File.Exists(path)) { Debug.LogWarning("[JieGuang] Soundtrack missing: " + path); return null; }
            byte[] b = File.ReadAllBytes(path);
            int pos = 12, dataStart = -1, dataLen = 0;
            while (pos + 8 <= b.Length)
            {
                string id = System.Text.Encoding.ASCII.GetString(b, pos, 4);
                int len = BitConverter.ToInt32(b, pos + 4);
                if (id == "data") { dataStart = pos + 8; dataLen = Math.Min(len, b.Length - dataStart); break; }
                pos += 8 + len + (len & 1);
            }
            if (dataStart < 0) return null;
            var samples = new float[dataLen / 2];
            for (int i = 0; i < samples.Length; i++) samples[i] = BitConverter.ToInt16(b, dataStart + i * 2) / 32768f;
            return samples;
        }
    }
}
