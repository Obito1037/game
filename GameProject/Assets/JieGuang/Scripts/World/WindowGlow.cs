using UnityEngine;

namespace JieGuang
{
    // Fades a window's warm emission on and off (village windows, 阿婆's round window).
    // Village windows carry a real point light only while the camera is near; from farther away
    // a soft additive glow sprite keeps them lit for a fraction of the GPU cost.
    public sealed class WindowGlow : MonoBehaviour
    {
        public float Intensity = 1.6f;
        public Color Warm = new Color(1f, 0.72f, 0.38f);
        public bool Lit = true;
        public float FadeSeconds = 1.2f;
        const float LightDistance = 24f;

        Renderer rend;
        Light lamp;
        Transform halo;
        Material haloMat;
        float level, lampIntensity, nextCull;
        bool near = true;

        void Awake()
        {
            rend = GetComponent<Renderer>();
            // IslandV2 replaces window quads with a warm light inside the new cottages
            lamp = GetComponentInChildren<Light>(true);
            if (lamp != null)
            {
                lampIntensity = lamp.intensity;
                // only small village window lights get the sprite; the round window keeps its light
                if (lamp.range <= 6f) BuildHalo();
                else near = true;
            }
            level = Lit ? 1f : 0f;
            Apply();
        }

        void BuildHalo()
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = "WindowHalo";
            halo = q.transform;
            halo.SetParent(lamp.transform, false);
            halo.localScale = Vector3.one * 1.3f;
            haloMat = new Material(MaterialKit.SoftParticle());
            var r = q.GetComponent<Renderer>();
            r.sharedMaterial = haloMat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
        }

        public void Set(bool lit, bool instant = false)
        {
            Lit = lit;
            if (instant) { level = lit ? 1f : 0f; Apply(); }
        }

        void Update()
        {
            if (halo != null && Time.unscaledTime >= nextCull)
            {
                nextCull = Time.unscaledTime + 0.4f + Random.value * 0.2f;
                var cam = Camera.main;
                bool n = cam != null && (cam.transform.position - lamp.transform.position).sqrMagnitude < LightDistance * LightDistance;
                if (n != near) { near = n; Apply(); }
            }
            float target = Lit ? 1f : 0f;
            if (Mathf.Approximately(level, target)) return;
            level = Mathf.MoveTowards(level, target, Time.deltaTime / Mathf.Max(0.01f, FadeSeconds));
            Apply();
        }

        void LateUpdate()
        {
            if (halo == null || level <= 0.01f) return;
            var cam = Camera.main;
            if (cam != null) halo.rotation = Quaternion.LookRotation(halo.position - cam.transform.position, Vector3.up);
        }

        void Apply()
        {
            if (lamp != null) { lamp.intensity = lampIntensity * level; lamp.enabled = level > 0.01f && near; }
            if (halo != null)
            {
                halo.gameObject.SetActive(level > 0.01f);
                haloMat.SetColor("_BaseColor", Warm * (0.55f * level));
            }
            if (rend == null || !rend.enabled) return;
            MaterialKit.SetEmission(rend, Warm * (Intensity * level));
            MaterialKit.SetColor(rend.material, Color.Lerp(new Color(0.08f, 0.07f, 0.07f), Warm, level * 0.6f));
        }
    }
}
