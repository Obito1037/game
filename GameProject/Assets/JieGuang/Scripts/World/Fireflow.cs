using UnityEngine;

namespace JieGuang
{
    // The islanders' "萤光": a soft coloured light around the body, a faint emissive tint on
    // the character's material and a few drifting motes. 0 strength = none (小灯笼 until the end).
    public sealed class Fireflow : MonoBehaviour
    {
        public Color Tint = new Color(0.6f, 1f, 0.5f);
        public float Strength = 1f;

        Light halo;
        ParticleSystem motes;
        Renderer[] bodies;
        Material rim;
        float shown = -1f;

        public static Fireflow Attach(GameObject character, Color tint, float strength)
        {
            var f = character.AddComponent<Fireflow>();
            f.Tint = tint;
            f.Strength = strength;
            f.Build();
            return f;
        }

        void Build()
        {
            var lg = new GameObject("FireflowLight");
            lg.transform.SetParent(transform, false);
            // above the head and a little behind, so the glow rims the figure without flattening the face
            lg.transform.localPosition = new Vector3(0f, 1.9f, -0.35f);
            halo = lg.AddComponent<Light>();
            halo.type = LightType.Point;
            halo.shadows = LightShadows.None;
            bodies = GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach (var r in bodies) r.material = new Material(r.sharedMaterial);
            // the glow on the body itself: one shared additive rim material per character
            var rimBase = Resources.Load<Material>("Materials/Base_CharacterRim");
            if (rimBase != null)
            {
                rim = new Material(rimBase);
                foreach (var r in bodies)
                {
                    var mats = r.sharedMaterials;
                    var list = new System.Collections.Generic.List<Material>(mats) { rim };
                    r.sharedMaterials = list.ToArray();
                }
            }

            var pg = new GameObject("Motes");
            pg.transform.SetParent(transform, false);
            pg.transform.localPosition = new Vector3(0f, 0.9f, 0f);
            motes = pg.AddComponent<ParticleSystem>();
            motes.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = motes.main;
            main.startLifetime = 2.6f;
            main.startSpeed = 0.08f;
            main.startSize = 0.035f;
            main.maxParticles = 40;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = motes.shape;
            shape.shapeType = ParticleSystemShapeType.Sphere;
            shape.radius = 0.45f;
            var vel = motes.velocityOverLifetime;
            vel.enabled = true;
            vel.x = new ParticleSystem.MinMaxCurve(-0.03f, 0.03f);
            vel.y = new ParticleSystem.MinMaxCurve(0.05f, 0.18f);
            vel.z = new ParticleSystem.MinMaxCurve(-0.03f, 0.03f);
            var col = motes.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.3f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            pg.GetComponent<ParticleSystemRenderer>().sharedMaterial = MaterialKit.SoftParticle();
            motes.Play();
        }

        void Update()
        {
            if (Mathf.Approximately(shown, Strength)) return;
            shown = Mathf.MoveTowards(shown < 0f ? Strength : shown, Strength, Time.deltaTime * 0.5f);
            halo.color = Tint;
            halo.intensity = 0.9f * shown;
            halo.range = 1.6f + 1.2f * shown;
            foreach (var r in bodies)
            {
                r.material.EnableKeyword("_EMISSION");
                r.material.SetColor("_EmissionColor", Tint * (0.02f * shown));
            }
            if (rim != null)
            {
                rim.SetColor("_RimColor", Tint);
                rim.SetFloat("_RimStrength", 0.9f * shown);
            }
            var main = motes.main;
            main.startColor = new Color(Tint.r, Tint.g, Tint.b, 0.9f);
            var em = motes.emission;
            em.rateOverTime = 9f * shown;
        }
    }
}
