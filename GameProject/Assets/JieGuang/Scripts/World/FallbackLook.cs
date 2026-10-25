using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // Minimal global post-processing used only while the environment ships no Volume of its
    // own (the chapter looks belong to the environment track). Deliberately neutral: tone
    // mapping, a soft bloom for windows, lamps and light-fruit, and a light vignette. No colour
    // grading and no depth of field, so it never fights the environment's profiles.
    public static class FallbackLook
    {
        public static Volume Create()
        {
            var go = new GameObject("FallbackLook (no environment Volume)");
            var v = go.AddComponent<Volume>();
            v.isGlobal = true;
            v.priority = -10f;
            var p = ScriptableObject.CreateInstance<VolumeProfile>();
            p.name = "FallbackLook";

            var tone = p.Add<Tonemapping>(true);
            tone.mode.value = TonemappingMode.ACES;

            var bloom = p.Add<Bloom>(true);
            bloom.threshold.value = 0.9f;
            bloom.intensity.value = 0.65f;
            bloom.scatter.value = 0.65f;
            bloom.tint.value = new Color(1f, 0.92f, 0.82f);

            var split = p.Add<SplitToning>(true);
            split.shadows.value = new Color(.46f,.49f,.55f);
            split.highlights.value = new Color(.54f,.51f,.47f);
            split.balance.value = 0f;

            var vignette = p.Add<Vignette>(true);
            vignette.intensity.value = 0.1f;
            vignette.smoothness.value = 0.45f;

            v.sharedProfile = p;
            return v;
        }
    }
}
