using UnityEngine;

namespace JieGuang
{
    // 小灯笼's lantern: copper frame, glass and a light-fruit inside. It hangs below the hand
    // it follows (or from a fixed hook) and swings a little; brightness and the bell are story state.
    public sealed class Lantern : MonoBehaviour
    {
        public Transform FollowHand;
        public Transform Hook;
        public float Brightness = 1f;   // 0 = out, 1 = normal, >1 = after 阿萤's share
        public bool HasBell;

        Light glow;
        Renderer fruit;
        GameObject bell;
        Vector3 lastPos, swing;
        float shown;
        AudioSource audioSource;

        public static Lantern Create()
        {
            var root = new GameObject("Lantern").AddComponent<Lantern>();
            root.Build();
            return root;
        }

        void Build()
        {
            var copper = MaterialKit.Lit(new Color(0.6f, 0.36f, 0.18f), 0.55f);
            Part(PrimitiveType.Cylinder, new Vector3(0f, -0.04f, 0f), new Vector3(0.16f, 0.015f, 0.16f), copper);
            Part(PrimitiveType.Cylinder, new Vector3(0f, -0.25f, 0f), new Vector3(0.17f, 0.015f, 0.17f), copper);
            for (int i = 0; i < 4; ++i)
            {
                float a = i * Mathf.PI / 2f + Mathf.PI / 4f;
                Part(PrimitiveType.Cube, new Vector3(Mathf.Cos(a) * 0.07f, -0.145f, Mathf.Sin(a) * 0.07f), new Vector3(0.012f, 0.2f, 0.012f), copper);
            }
            var handle = Part(PrimitiveType.Cube, new Vector3(0f, 0f, 0f), new Vector3(0.012f, 0.06f, 0.012f), MaterialKit.Lit(new Color(0.55f, 0.47f, 0.33f)));
            handle.name = "RopeHandle";
            var glass = Part(PrimitiveType.Cylinder, new Vector3(0f, -0.145f, 0f), new Vector3(0.13f, 0.095f, 0.13f), MaterialKit.Additive(new Color(1f, 0.85f, 0.6f, 0.12f)));
            glass.name = "Glass";
            var f = Part(PrimitiveType.Sphere, new Vector3(0f, -0.15f, 0f), Vector3.one * 0.06f, null);
            fruit = f.GetComponent<Renderer>();
            fruit.material = MaterialKit.LitInstance(new Color(1f, 0.85f, 0.5f), Color.black);
            bell = Part(PrimitiveType.Sphere, new Vector3(0.09f, -0.03f, 0f), new Vector3(0.035f, 0.04f, 0.035f), MaterialKit.Lit(new Color(0.8f, 0.6f, 0.25f), 0.7f));
            bell.name = "Bell";
            var lg = new GameObject("Glow");
            lg.transform.SetParent(transform, false);
            lg.transform.localPosition = new Vector3(0f, -0.15f, 0f);
            glow = lg.AddComponent<Light>();
            glow.type = LightType.Point;
            glow.color = new Color(1f, 0.76f, 0.42f);
            glow.range = 4.5f;
            glow.shadows = LightShadows.None;
            audioSource = gameObject.AddComponent<AudioSource>();
            audioSource.spatialBlend = 0.6f;
            audioSource.playOnAwake = false;
            UseTripoModel();
        }

        // The user's Tripo lantern (B01) replaces the primitive frame; the fruit becomes a soft
        // additive halo so the lantern still reads as lit through its painted glass.
        Renderer halo;

        void UseTripoModel()
        {
            var prefab = Resources.Load<GameObject>("Props/B01_lantern");
            if (prefab == null) return;
            foreach (Transform c in transform)
                if (c.GetComponent<Renderer>() != null) c.gameObject.SetActive(false);
            var m = Instantiate(prefab, transform);
            m.name = "LanternModel";
            m.transform.localPosition = new Vector3(0f, -0.3f, 0f);
            m.transform.localRotation = prefab.transform.localRotation;
            foreach (var r in m.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var h = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Destroy(h.GetComponent<Collider>());
            h.name = "Halo";
            h.transform.SetParent(transform, false);
            h.transform.localPosition = new Vector3(0f, -0.17f, 0f);
            h.transform.localScale = Vector3.one * 0.2f;
            halo = h.GetComponent<Renderer>();
            halo.material = MaterialKit.Additive(new Color(1f, 0.72f, 0.38f, 0.35f));
            halo.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            bell.SetActive(false);
            bell = new GameObject("BellPlaceholder");
            bell.transform.SetParent(transform, false);
        }

        GameObject Part(PrimitiveType t, Vector3 pos, Vector3 scale, Material m)
        {
            var go = GameObject.CreatePrimitive(t);
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(transform, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            if (m != null) go.GetComponent<Renderer>().sharedMaterial = m;
            go.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        public void RingBell()
        {
            var clip = Resources.Load<AudioClip>("Audio/LanternChime");
            if (clip != null && HasBell) audioSource.PlayOneShot(clip, 0.8f);
        }

        void LateUpdate()
        {
            bell.SetActive(HasBell);
            shown = Mathf.MoveTowards(shown, Brightness, Time.deltaTime * 0.8f);
            glow.intensity = shown * 2.6f;
            glow.range = Hook != null ? 10f : 3.5f + shown * 1.5f; // a 16 m light lit most of the screen in every shader
            MaterialKit.SetEmission(fruit, new Color(1f, 0.7f, 0.35f) * (shown * 4f));
            if (halo != null) MaterialKit.SetAdditive(halo.material, new Color(1f, 0.72f, 0.38f, 0.28f * Mathf.Clamp01(shown)));
            Vector3 anchor;
            if (Hook != null) anchor = Hook.position;
            else if (FollowHand != null) anchor = FollowHand.position + Vector3.down * 0.05f;
            else return;
            // pendulum-like sway from the hand's motion
            Vector3 vel = (anchor - lastPos) / Mathf.Max(Time.deltaTime, 1e-3f);
            lastPos = anchor;
            swing = Vector3.Lerp(swing, Vector3.ClampMagnitude(-vel * 0.12f, 0.5f), Time.deltaTime * 4f);
            transform.position = anchor;
            transform.rotation = Quaternion.FromToRotation(Vector3.down, (Vector3.down + new Vector3(swing.x, 0f, swing.z)).normalized);
        }
    }
}
