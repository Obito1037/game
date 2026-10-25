using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.InputSystem;

namespace JieGuang
{
    // Explicit native photo/performance study. Fixed diagnostic cameras are not walking QA.
    public sealed class JgRenderStudy : MonoBehaviour
    {
        [Serializable] class Sample { public string name; public int frames; public float seconds, meanFps, p50Ms, p95Ms, renderScale, gpuP50Ms; }
        [Serializable] class Report { public string gpu, method, walkResult; public int width, height; public List<Sample> samples = new List<Sample>(); }
        string folder;
        bool photos, restored, locked;
        int[] saved = new int[3];
        bool[] existed = new bool[3];
        readonly string[] keys = { "jieguang.chapter", "jieguang.unlocked", "jieguang.debugStart" };
        Camera camera;
        Vector3 position, target;
        Report report;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Bootstrap()
        {
#if UNITY_STANDALONE && !UNITY_EDITOR
            var args = Environment.GetCommandLineArgs();
            bool photo = Array.IndexOf(args, "--jg-visual-study") >= 0;
            if (!photo && Array.IndexOf(args, "--jg-render-study") < 0 && Array.IndexOf(args,"--jg-walk-study") < 0) return;
            int i = Array.IndexOf(args, "--jg-qa-out");
            if (i < 0 || i + 1 >= args.Length || !Path.IsPathRooted(args[i + 1])) { Application.Quit(2); return; }
            var go = new GameObject("JgRenderStudy_OptIn");
            DontDestroyOnLoad(go);
            go.AddComponent<JgRenderStudy>().Initialize(args[i + 1], photo);
#endif
        }
        void Initialize(string path, bool photo)
        {
            folder = path; photos = photo;
            if (File.Exists(Path.Combine(folder, "render-study.json"))) folder = Path.Combine(folder, DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
            Directory.CreateDirectory(folder);
            for (int i = 0; i < keys.Length; i++) { existed[i] = PlayerPrefs.HasKey(keys[i]); saved[i] = PlayerPrefs.GetInt(keys[i]); }
            File.WriteAllText(Path.Combine(folder, "study-save-backup.txt"), string.Join("\n", new[] { keys[0]+":"+existed[0]+":"+saved[0], keys[1]+":"+existed[1]+":"+saved[1], keys[2]+":"+existed[2]+":"+saved[2] }));
            PlayerPrefs.SetInt("jieguang.debugStart", 7);
            PlayerPrefs.Save();
            Application.runInBackground = true;
            Application.quitting += Restore;
            StartCoroutine(Run());
        }
        void Restore()
        {
            if (restored) return;
            for (int i = 0; i < keys.Length; i++) { if (existed[i]) PlayerPrefs.SetInt(keys[i], saved[i]); else PlayerPrefs.DeleteKey(keys[i]); }
            PlayerPrefs.Save(); restored = true;
        }
        void LateUpdate()
        {
            if (locked && camera != null) { camera.transform.position = position; camera.transform.rotation = Quaternion.LookRotation(target-position); }
        }
        IEnumerator Run()
        {
            yield return new WaitForSecondsRealtime(18f);
            camera = Camera.main;
            if (camera == null) { Restore(); Application.Quit(2); yield break; }
            var director = FindFirstObjectByType<CameraDirector>();
            if (director != null) { director.StopAllCoroutines(); director.enabled = false; }
            foreach (var c in FindObjectsByType<Canvas>(FindObjectsSortMode.None)) c.enabled = false;
            report = new Report { gpu = SystemInfo.graphicsDeviceName, width = Screen.width, height = Screen.height, method = "Native epilogue fixed camera. Each change is followed by baseline recovery. 3 s settling + 10 s sampling. Diagnostic screenshots and FPS do not establish sustained gameplay or collision coverage." };
            locked = true;
            if (Array.IndexOf(Environment.GetCommandLineArgs(),"--jg-walk-study") >= 0)
            {
                report.method = "Diagnostic start placement on pier at x=9.4 to route around the existing flagpole, then ordinary GameInput.Hold -> PlayerController -> CharacterController movement over A12/A13 seam and back. Route correction only, not a game collision fix. No position writes after start. Limited route only; not manual input or whole-island collision coverage.";
                var pc=FindFirstObjectByType<PlayerController>();
                pc.Teleport(new Vector3(9.4f,2.6f,-14.8f),0f);
                position=new Vector3(9.4f,7f,-23f);target=new Vector3(9.4f,2.5f,-10f);
                yield return new WaitForSecondsRealtime(3f);
                yield return Shot("walk-start",position,target);
                var csv=new System.Text.StringBuilder("seconds,phase,x,y,z,grounded\n");
                bool outDone=false,backDone=false;float minY=pc.transform.position.y;
                for(int phase=0;phase<2;phase++)
                {
                    float deadline=Time.realtimeSinceStartup+14f;
                    while(Time.realtimeSinceStartup<deadline)
                    {
                        var p=pc.transform.position;minY=Mathf.Min(minY,p.y);
                        csv.AppendLine(FormattableString.Invariant($"{Time.realtimeSinceStartup:F3},{phase},{p.x:F3},{p.y:F3},{p.z:F3},{pc.GetComponent<CharacterController>().isGrounded}"));
                        if(phase==0 && p.z>=-8.85f){outDone=true;break;}
                        if(phase==1 && p.z<=-14.55f){backDone=true;break;}
                        GameInput.Hold(phase==0?Key.W:Key.S,.15f);
                        yield return new WaitForSecondsRealtime(.2f);
                    }
                    yield return new WaitForSecondsRealtime(1.5f);
                    yield return Shot(phase==0?"walk-A13-stopped":"walk-return-stopped",position,target);
                }
                File.WriteAllText(Path.Combine(folder,"walk-positions.csv"),csv.ToString());
                report.walkResult="out="+outDone+"; back="+backDone+"; minimumRootY="+minY.ToString("F3",System.Globalization.CultureInfo.InvariantCulture);
            }
            else if (photos)
            {
                yield return Shot("01-island", new Vector3(31,28,-48), new Vector3(-2,3,-4));
                yield return Shot("02-house-window", new Vector3(12,6,-24), new Vector3(5,3.5f,-16));
                yield return Shot("03-tree-path", new Vector3(-11,7,-14), new Vector3(0,3,-18));
                yield return Shot("04-village", new Vector3(7,13,6), new Vector3(-7,9,19));
                yield return Shot("05-pier", new Vector3(19,7,-29), new Vector3(12,2,-15));
                yield return Shot("06-sea-house", new Vector3(23,2,-25), new Vector3(6,3,-15));
                yield return Shot("07-sea-earth", new Vector3(9,1.2f,-30), new Vector3(38,12,-87));
                yield return Shot("08-coast", new Vector3(-20,5,-28), new Vector3(-4,1,-18));
                yield return Shot("09-meadow-near", new Vector3(-3,3.2f,-22), new Vector3(0,2.5f,-18));
                yield return Shot("10-meadow-middle", new Vector3(-7,6,-26), new Vector3(0,2.5f,-18));
                yield return Shot("11-meadow-far", new Vector3(-13,12,-34), new Vector3(0,2.5f,-18));
            }
            else
            {
                position = new Vector3(12,6,-24); target = new Vector3(3,3,-15);
                var rp = (UniversalRenderPipelineAsset)GraphicsSettings.currentRenderPipeline;
                int cascades = rp.shadowCascadeCount;
                var lights = FindObjectsByType<Light>(FindObjectsSortMode.None);
                var shadows = new LightShadows[lights.Length]; for (int i=0;i<lights.Length;i++) shadows[i]=lights[i].shadows;
                var rendererField = typeof(UniversalRenderPipelineAsset).GetField("m_RendererDataList", BindingFlags.Instance|BindingFlags.NonPublic);
                var data = rendererField?.GetValue(rp) as ScriptableRendererData[];
                ScriptableRendererFeature ao = null;
                if (data != null) foreach(var d in data) if(d != null) foreach(var f in d.rendererFeatures) if(f.name.Contains("AmbientOcclusion")) ao=f;
                bool aoWas = ao != null && ao.isActive;
                // v3 GPU-cost study: each change is measured against an adjacent baseline,
                // at the fixed render scale adaptive resolution settles on for this GPU
                foreach (var a in FindObjectsByType<AdaptiveResolution>(FindObjectsSortMode.None)) a.enabled = false;
                rp.renderScale = 0.72f;
                var budgets = FindObjectsByType<IslandFoliageBudget>(FindObjectsSortMode.None);
                var camData = Camera.main.GetUniversalAdditionalCameraData();
                var look = FindFirstObjectByType<ChapterLook>();
                var seaGo = GameObject.Find("NightSea");
                var skirt = GameObject.Find("ShoreSkirtV3");
                var ground = GameObject.Find("GroundSurfaceV2");
                // v3 regression hunt: the features new in v3, each against an adjacent baseline
                var boulders = GameObject.Find("ShoreBoulders");
                var rimHolders = new List<(Renderer r, Material[] m)>();
                foreach (var r in FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None))
                {
                    var mats = r.sharedMaterials;
                    if (mats.Length > 1 && mats[mats.Length - 1] != null && mats[mats.Length - 1].shader.name == "JieGuang/CharacterRim") rimHolders.Add((r, mats));
                }
                var halos = new List<GameObject>(); foreach (var t in FindObjectsByType<Transform>(FindObjectsSortMode.None)) if (t.name == "WindowHalo" && t.gameObject.activeSelf) halos.Add(t.gameObject);
                var lookVolume = look != null ? look.GetComponent<UnityEngine.Rendering.Volume>() : null;
                var filter = rp.upscalingFilter;
                yield return Measure("A-normal", rp);
                rp.renderScale = 1f; rp.upscalingFilter = UpscalingFilterSelection.Auto;
                yield return Measure("B-scale1-noFSR", rp);
                rp.renderScale = 0.72f; rp.upscalingFilter = UpscalingFilterSelection.Linear;
                yield return Measure("C-072-linear", rp);
                rp.upscalingFilter = filter;
                yield return Measure("A1-normal", rp);
                if (boulders != null) boulders.SetActive(false);
                yield return Measure("D-no-boulders", rp);
                if (boulders != null) boulders.SetActive(true);
                yield return Measure("A2-normal", rp);
                if (skirt != null) skirt.GetComponent<Renderer>().enabled = false;
                yield return Measure("E-no-skirt", rp);
                if (skirt != null) skirt.GetComponent<Renderer>().enabled = true;
                yield return Measure("A3-normal", rp);
                foreach (var h in rimHolders) { var m = new Material[h.m.Length - 1]; System.Array.Copy(h.m, m, m.Length); h.r.sharedMaterials = m; }
                yield return Measure("F-no-rim", rp);
                foreach (var h in rimHolders) h.r.sharedMaterials = h.m;
                yield return Measure("A4-normal", rp);
                var clear = camera.clearFlags; camera.clearFlags = CameraClearFlags.SolidColor;
                yield return Measure("G-no-skybox", rp);
                camera.clearFlags = clear;
                yield return Measure("A5-normal", rp);
                if (lookVolume != null) lookVolume.enabled = false;
                yield return Measure("H-no-chapter-look", rp);
                if (lookVolume != null) lookVolume.enabled = true;
                yield return Measure("A6-normal", rp);
                foreach (var h in halos) h.SetActive(false);
                yield return Measure("I-no-window-halos", rp);
                foreach (var h in halos) h.SetActive(true);
                yield return Measure("A7-normal", rp);
            }
            File.WriteAllText(Path.Combine(folder,"render-study.json"), JsonUtility.ToJson(report,true));
            Restore(); Application.Quit();
        }
        IEnumerator Shot(string name, Vector3 p, Vector3 t)
        {
            position=p; target=t; yield return new WaitForSecondsRealtime(3f);
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
            yield return new WaitForSecondsRealtime(1.5f);
        }
        IEnumerator Measure(string name, UniversalRenderPipelineAsset rp)
        {
            yield return new WaitForSecondsRealtime(3f);
            var values = new List<float>(); float end = Time.realtimeSinceStartup+10f, sum=0;
            var gpu = new List<float>(); var ft = new FrameTiming[1];
            while(Time.realtimeSinceStartup<end) { yield return null; values.Add(Time.unscaledDeltaTime*1000f); sum+=Time.unscaledDeltaTime;
                FrameTimingManager.CaptureFrameTimings(); if (FrameTimingManager.GetLatestTimings(1, ft) > 0) gpu.Add((float)ft[0].gpuFrameTime); }
            values.Sort(); gpu.Sort();
            report.samples.Add(new Sample {name=name,frames=values.Count,seconds=sum,meanFps=values.Count/sum,p50Ms=values[values.Count/2],p95Ms=values[Mathf.Min(values.Count-1,(int)(values.Count*.95f))],renderScale=rp.renderScale,gpuP50Ms=gpu.Count>0?gpu[gpu.Count/2]:-1});
            File.WriteAllText(Path.Combine(folder,"render-study.json"), JsonUtility.ToJson(report,true));
            yield return new WaitForEndOfFrame(); ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
            yield return new WaitForSecondsRealtime(1f);
        }
    }
}
