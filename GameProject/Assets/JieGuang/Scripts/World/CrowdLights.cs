using System.Collections.Generic;
using UnityEngine;

namespace JieGuang
{
    // The villagers seen only as lights (the story never shows the crowd itself): warm orbs
    // that stand along the pier and the road. Raised high they wash out the sky; lowered,
    // they dim and the stars return.
    public sealed class CrowdLights : MonoBehaviour
    {
        sealed class Orb { public Transform T; public Vector3 Base; public float Phase; public Light L; }

        readonly List<Orb> orbs = new List<Orb>();
        float raised, raisedTarget, visible, visibleTarget = 1f;
        Material mat;

        public float Raised => raised;

        public static CrowdLights Create(string name) => new GameObject(name).AddComponent<CrowdLights>();

        public void Spawn(IList<Vector3> points, float jitter, int seed)
        {
            mat = MaterialKit.Additive(new Color(1f, 0.75f, 0.45f, 0.9f));
            var rng = new System.Random(seed);
            for (int i = 0; i < points.Count; ++i)
            {
                var s = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                Destroy(s.GetComponent<Collider>());
                s.transform.SetParent(transform, false);
                Vector3 p = points[i] + new Vector3((float)rng.NextDouble() - 0.5f, 0f, (float)rng.NextDouble() - 0.5f) * jitter;
                p.y = Ground(p) + 1.1f + (float)rng.NextDouble() * 0.3f;
                s.transform.position = p;
                s.transform.localScale = Vector3.one * 0.16f;
                s.GetComponent<Renderer>().sharedMaterial = mat;
                var orb = new Orb { T = s.transform, Base = p, Phase = (float)rng.NextDouble() * 6f };
                if (i % 4 == 0)
                {
                    orb.L = s.AddComponent<Light>();
                    orb.L.type = LightType.Point;
                    orb.L.color = new Color(1f, 0.72f, 0.42f);
                    orb.L.range = 3.5f;
                    orb.L.shadows = LightShadows.None;
                }
                orbs.Add(orb);
            }
        }

        static float Ground(Vector3 p)
        {
            return Physics.Raycast(p + Vector3.up * 30f, Vector3.down, out var hit, 80f, ~0, QueryTriggerInteraction.Ignore) ? hit.point.y : p.y;
        }

        public void SetRaised(bool up) => raisedTarget = up ? 1f : 0f;
        public void SetVisible(bool on) => visibleTarget = on ? 1f : 0f;
        public void SetVisibleInstant(bool on) { visible = visibleTarget = on ? 1f : 0f; }

        void Update()
        {
            raised = Mathf.MoveTowards(raised, raisedTarget, Time.deltaTime * 0.35f);
            visible = Mathf.MoveTowards(visible, visibleTarget, Time.deltaTime * 0.6f);
            foreach (var o in orbs)
            {
                float bob = Mathf.Sin(Time.time * 1.3f + o.Phase) * 0.05f;
                o.T.position = o.Base + Vector3.up * (bob + raised * 1.0f - (1f - raised) * 0.45f);
                o.T.localScale = Vector3.one * (0.12f + 0.08f * raised) * visible;
                if (o.L != null) o.L.intensity = visible * (0.5f + 1.2f * raised);
            }
        }
    }
}
