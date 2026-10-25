using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // Keeps the game near 60 fps on integrated GPUs: when frames stay slow the 3D render scale
    // steps down (FSR upscaling keeps edges crisp; the UI is always native), and when frames
    // stay at the cap it steps back up. Players only (the pipeline asset is never edited in the
    // Editor), and changes are slow and hysteretic so the image never pumps.
    public sealed class AdaptiveResolution : MonoBehaviour
    {
        float minScale, maxScale, scale, slowFor, fastFor, holdUntil, smoothed = 1f / 60f;
        UniversalRenderPipelineAsset rp;

        public static float CurrentScale { get; private set; } = 1f;

        public static void Attach(GameObject host)
        {
#if !UNITY_EDITOR
            host.AddComponent<AdaptiveResolution>();
#endif
        }

        void Start()
        {
            rp = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            if (rp == null) { enabled = false; return; }
            bool web = Application.platform == RuntimePlatform.WebGLPlayer;
            maxScale = web ? Mathf.Min(rp.renderScale, 0.9f) : 1f;
            minScale = web ? 0.6f : 0.72f;
            scale = Mathf.Clamp(rp.renderScale, minScale, maxScale);
            rp.upscalingFilter = UpscalingFilterSelection.FSR;
            rp.fsrOverrideSharpness = true;
            rp.fsrSharpness = 0.6f;
            Apply();
            holdUntil = Time.unscaledTime + 6f; // let loading hitches pass
        }

        void Update()
        {
            float dt = Mathf.Min(Time.unscaledDeltaTime, 0.1f);
            smoothed = Mathf.Lerp(smoothed, dt, 0.05f);
            if (Time.unscaledTime < holdUntil) return;
            if (smoothed > 1f / 52f) { slowFor += dt; fastFor = 0f; }
            else if (smoothed < 1f / 58f) { fastFor += dt; slowFor = 0f; }
            else { slowFor = 0f; fastFor = 0f; }
            if (slowFor > 1.5f && scale > minScale + 0.001f)
            {
                scale = Mathf.Max(minScale, scale - 0.05f);
                Apply();
                slowFor = 0f;
                holdUntil = Time.unscaledTime + 2f;
            }
            else if (fastFor > 8f && scale < maxScale - 0.001f)
            {
                scale = Mathf.Min(maxScale, scale + 0.05f);
                Apply();
                fastFor = 0f;
                holdUntil = Time.unscaledTime + 4f;
            }
        }

        void Apply()
        {
            rp.renderScale = scale;
            CurrentScale = scale;
        }
    }
}
