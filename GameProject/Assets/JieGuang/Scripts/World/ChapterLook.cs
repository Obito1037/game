using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // The game's post-processing look, driven by the chapter mood in NightSky: ACES, a soft warm
    // bloom for lamps, windows and glow, teal-violet shadows with warm highlights, a gentle
    // vignette, and depth of field that story shots can switch on.
    public sealed class ChapterLook : MonoBehaviour
    {
        Volume volume;
        ColorAdjustments color;
        SplitToning split;
        Bloom bloom;
        Vignette vignette;
        DepthOfField dof;
        float focus = 6f, focusTarget = 6f, dofWeight, dofTarget;

        public static ChapterLook Instance { get; private set; }

        public static ChapterLook Create()
        {
            if (Instance != null) return Instance;
            var go = new GameObject("ChapterLook");
            var look = go.AddComponent<ChapterLook>();
            look.Build();
            Instance = look;
            return look;
        }

        void Build()
        {
            volume = gameObject.AddComponent<Volume>();
            volume.isGlobal = true;
            volume.priority = 5f;
            var p = ScriptableObject.CreateInstance<VolumeProfile>();
            p.name = "ChapterLook";
            var tone = p.Add<Tonemapping>(true);
            tone.mode.value = TonemappingMode.ACES;
            bloom = p.Add<Bloom>(true);
            bloom.threshold.value = 0.82f;
            bloom.intensity.value = 0.85f;
            bloom.scatter.value = 0.72f;
            bloom.tint.value = new Color(1f, 0.9f, 0.78f);
            bloom.highQualityFiltering.value = false;
            bloom.downscale.value = BloomDownscaleMode.Quarter; // the soft glow survives; half the cost
            bloom.maxIterations.value = 5;
            color = p.Add<ColorAdjustments>(true);
            color.postExposure.value = 0.2f;
            color.contrast.value = 8f;
            color.saturation.value = 12f;
            split = p.Add<SplitToning>(true);
            split.shadows.value = new Color(0.38f, 0.48f, 0.62f);
            split.highlights.value = new Color(0.62f, 0.52f, 0.40f);
            split.balance.value = -10f;
            vignette = p.Add<Vignette>(true);
            vignette.intensity.value = 0.2f;
            vignette.smoothness.value = 0.5f;
            vignette.color.value = new Color(0.02f, 0.03f, 0.07f);
            dof = p.Add<DepthOfField>(true);
            dof.mode.value = DepthOfFieldMode.Gaussian;
            dof.gaussianStart.value = 8f;
            dof.gaussianEnd.value = 30f;
            dof.gaussianMaxRadius.value = 1.2f;
            dof.highQualitySampling.value = false;
            dof.active = false;
            volume.sharedProfile = p;
        }

        // exposure in EV, saturation in URP units (-100..100), pollution 0..1 greys the image
        public void Apply(float exposure, float saturation, float pollution)
        {
            if (color == null) return;
            color.postExposure.value = exposure;
            color.saturation.value = saturation;
            color.contrast.value = Mathf.Lerp(8f, -4f, pollution);
            split.balance.value = Mathf.Lerp(-10f, 0f, pollution);
        }

        // Story shots: blur the background past `distance` metres. Off for free walking.
        public void Focus(float distance) { focusTarget = distance; dofTarget = 1f; }
        public void ClearFocus() => dofTarget = 0f;

        void LateUpdate()
        {
            if (dof == null) return;
            dofWeight = Mathf.MoveTowards(dofWeight, dofTarget, Time.unscaledDeltaTime * 1.5f);
            focus = Mathf.Lerp(focus, focusTarget, 1f - Mathf.Exp(-Time.unscaledDeltaTime * 4f));
            dof.active = dofWeight > 0.01f;
            dof.gaussianStart.value = focus + 1.5f;
            dof.gaussianEnd.value = focus + Mathf.Lerp(80f, 14f, dofWeight);
        }

        void OnDestroy() { if (Instance == this) Instance = null; }
    }
}
