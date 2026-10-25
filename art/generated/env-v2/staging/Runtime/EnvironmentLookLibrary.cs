using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace JieGuang.EnvironmentTools
{
    /// <summary>Data only. Story code chooses when to apply a chapter; no automatic global-state writes.</summary>
    [CreateAssetMenu(menuName = "JieGuang/Environment look library")]
    public sealed class EnvironmentLookLibrary : ScriptableObject
    {
        [Serializable]
        public sealed class Look
        {
            public string id;
            public string displayName;
            public VolumeProfile profile;
            public Color ambientSky, ambientEquator, ambientGround;
            public Color zenith, horizon, seaDeep, seaShallow;
            [Range(0, .5f)] public float earthLitFraction = .04f;
            [Range(0, 2)] public float stars = .85f;
            [Range(0, 1)] public float cloudOpacity = .06f;
            public float keyIntensity = .48f, fillIntensity = .16f;
            public Color keyColor = new Color(1, .87f, .71f), fillColor = new Color(1, .94f, .83f);
            public float fogStart = 45, fogEnd = 190;
        }
        public Look[] looks = Array.Empty<Look>();
        public Look Get(string id)
        {
            foreach (Look look in looks) if (look.id == id) return look;
            throw new ArgumentException("Unknown environment look: " + id, nameof(id));
        }
        /// <summary>Call from the ONE owner of RenderSettings. Never called automatically by the environment.</summary>
        public static void ApplyGlobalEnvironment(Look look)
        {
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = look.ambientSky;
            RenderSettings.ambientEquatorColor = look.ambientEquator;
            RenderSettings.ambientGroundColor = look.ambientGround;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = look.horizon;
            RenderSettings.fogStartDistance = look.fogStart;
            RenderSettings.fogEndDistance = look.fogEnd;
            RenderSettings.reflectionIntensity = .18f;
        }
    }
}
