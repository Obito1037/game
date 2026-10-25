using System.Collections.Generic;
using UnityEngine;

namespace JieGuang
{
    // Runtime materials cloned from base assets in Resources/Materials (created by the scene
    // builder), so the URP shaders and their variants are always part of the build.
    public static class MaterialKit
    {
        static readonly Dictionary<string, Material> cache = new Dictionary<string, Material>();
        static readonly int BaseColor = Shader.PropertyToID("_BaseColor");
        static readonly int Emission = Shader.PropertyToID("_EmissionColor");
        static readonly int Smoothness = Shader.PropertyToID("_Smoothness");
        static Material softParticle;

        static Material Base(string name)
        {
            var m = Resources.Load<Material>("Materials/" + name);
            if (m == null) Debug.LogError("[JieGuang] missing Resources/Materials/" + name);
            return m;
        }

        public static Material Lit(Color c, float smooth = 0.15f, Color? emission = null)
        {
            string key = "lit" + c + smooth + emission;
            if (cache.TryGetValue(key, out var m)) return m;
            m = new Material(Base("Base_Lit"));
            m.SetColor(BaseColor, c);
            m.SetFloat(Smoothness, smooth);
            if (emission.HasValue)
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor(Emission, emission.Value);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            }
            return cache[key] = m;
        }

        // Unique instance whose emission the caller animates.
        public static Material LitInstance(Color c, Color emission)
        {
            var m = new Material(Base("Base_Lit"));
            m.SetColor(BaseColor, c);
            m.SetFloat(Smoothness, 0.2f);
            m.EnableKeyword("_EMISSION");
            m.SetColor(Emission, emission);
            return m;
        }

        // Fold the requested opacity into RGB so callers can animate additive brightness.
        public static Material Additive(Color c)
        {
            var m = new Material(Base("Base_Additive"));
            SetAdditive(m, c);
            return m;
        }

        public static void SetAdditive(Material m, Color c) =>
            m.SetColor(BaseColor, new Color(c.r * c.a, c.g * c.a, c.b * c.a, 1f));

        // Keep the existing included particle shader and its vertex/lifetime alpha; only
        // these motes receive a radial alpha texture, leaving lamp/lantern materials alone.
        public static Material SoftParticle()
        {
            if (softParticle != null) return softParticle;
            softParticle = new Material(Base("Base_Additive")) { name = "FireflowSoftParticle" };
            softParticle.SetColor(BaseColor, Color.white);
            softParticle.SetTexture("_BaseMap", UiKit.SoftDot.texture);
            return softParticle;
        }

        public static Material Unlit(Color c)
        {
            var m = new Material(Base("Base_Unlit"));
            m.SetColor(BaseColor, c);
            return m;
        }

        public static void SetEmission(Renderer r, Color e)
        {
            var m = r.material;
            m.EnableKeyword("_EMISSION");
            m.SetColor(Emission, e);
        }

        public static void SetColor(Material m, Color c) => m.SetColor(BaseColor, c);
    }
}
