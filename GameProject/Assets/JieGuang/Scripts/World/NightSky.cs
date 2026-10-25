using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // The night over 借光岛: a large blue Earth, stars, an earthlit horizon and cloud bank, and a
    // sky that turns milky grey when light leaks upward (Pollution 0 = clean dark, 1 = washed out).
    // Art direction: "no sun, but the night is bright and has colour" — each chapter has its own
    // mood (sky, ambient, earthlight, post look), blended when a chapter is staged.
    public sealed class NightSky : MonoBehaviour
    {
        [Range(0f, 1f)] public float Pollution;
        [Range(0f, 0.5f)] public float EarthPhase = 0.12f; // lit fraction of the Earth disc
        public float EarthBrightness = 1f;
        // Optional user-authored S01 panorama. No stock/reference-site art is substituted.
        public Texture2D Panorama;
        public Light Sun;

        static readonly Color DeepNight = new Color(0.012f, 0.02f, 0.05f);
        // Direction of the earthlight (unit vector from the viewer). High (about 50 degrees) and
        // behind-right of the main story cameras, so it keys roofs, paths and canopies in
        // three-quarter light instead of back-lighting them.
        static readonly Vector3 EarthDir = new Vector3(0.29f, 0.77f, -0.57f).normalized;
        public Vector3 EarthDirection => EarthDir;
        // Where the Earth's disc is drawn: low over the sea (about 14 degrees up) on the side the
        // title, chapter-one and village cameras face, so it rises inside the story framings. The
        // key light is deliberately cheated from behind those cameras (EarthDir) for readable faces.
        static readonly Vector3 DefaultEarthSkyDir = new Vector3(-0.64f, 0.24f, 0.73f).normalized;
        Vector3 EarthSkyDir = DefaultEarthSkyDir;
        public Vector3 EarthSkyDirection => EarthSkyDir;

        // Cinematic cheat for title and opening shots: hang the Earth at a chosen point of the
        // camera's frame (viewport coordinates), never lower than a few degrees above the sea.
        public void PinEarth(Camera view, Vector2 viewport)
        {
            var dir = view.ViewportPointToRay(new Vector3(viewport.x, viewport.y, 0f)).direction;
            if (dir.y < 0.1f) { dir.y = 0.1f; dir.Normalize(); }
            SetEarthSkyDir(dir);
        }
        public void UnpinEarth() => SetEarthSkyDir(DefaultEarthSkyDir);

        void SetEarthSkyDir(Vector3 dir)
        {
            EarthSkyDir = dir.normalized;
            if (skyMat != null) skyMat.SetVector("_EarthDir", EarthSkyDir);
        }
        const float EarthDistance = 80f;
        static readonly Color Washed = new Color(0.16f, 0.15f, 0.16f);

        // ------------------------------------------------------------------ chapter moods
        public struct Mood
        {
            public Color Zenith, Horizon, HorizonGlow, CloudLit, AmbientSky, AmbientEquator, AmbientGround, Light;
            public float LightIntensity, Fog, Stars, MilkyWay, CloudBank, Exposure, Saturation, EarthSize;
        }

        static Mood M(Color zenith, Color horizon, Color glow, Color ambient, float light, float stars, float milky, float bank,
                      float exposure, float saturation, float earthSize) => new Mood
        {
            Zenith = zenith, Horizon = horizon, HorizonGlow = glow,
            CloudLit = new Color(horizon.r * 2.2f + 0.08f, horizon.g * 2.0f + 0.10f, horizon.b * 1.7f + 0.14f),
            AmbientSky = ambient,
            AmbientEquator = new Color(ambient.r * 0.62f + horizon.r * 0.4f, ambient.g * 0.55f + horizon.g * 0.35f, ambient.b * 0.55f + horizon.b * 0.4f),
            AmbientGround = new Color(ambient.r * 0.22f, ambient.g * 0.28f, ambient.b * 0.22f),
            Light = new Color(0.72f, 0.83f, 1f), LightIntensity = light, Fog = 0.0040f,
            Stars = stars, MilkyWay = milky, CloudBank = bank, Exposure = exposure, Saturation = saturation, EarthSize = earthSize,
        };

        static Color C(float r, float g, float b) => new Color(r, g, b);

        public static Mood MoodFor(Chapter c)
        {
            switch (c)
            {
                // a full, bright earthlit night before the long night: silver-blue and lively
                case Chapter.Title:
                case Chapter.Prologue:
                    return M(C(.030f, .060f, .155f), C(.150f, .250f, .390f), C(.26f, .52f, .62f), C(.44f, .56f, .76f), 1.55f, .8f, .45f, .75f, .25f, 14f, .115f);
                // first night: violet blue, a little quieter
                case Chapter.One:
                    return M(C(.028f, .040f, .125f), C(.175f, .160f, .330f), C(.30f, .36f, .58f), C(.36f, .40f, .62f), 1.20f, .9f, .55f, .60f, .15f, 12f, .105f);
                // second night: cold blue outside, so the round window glows warm
                case Chapter.Two:
                    return M(C(.020f, .040f, .110f), C(.095f, .175f, .300f), C(.18f, .38f, .52f), C(.29f, .38f, .56f), 1.00f, 1f, .6f, .50f, .05f, 10f, .10f);
                // the night the lights go out
                case Chapter.Interlude:
                    return M(C(.012f, .020f, .060f), C(.070f, .090f, .160f), C(.10f, .17f, .26f), C(.20f, .24f, .35f), .62f, 1f, .7f, .35f, -.10f, 0f, .095f);
                case Chapter.Three:
                    return M(C(.020f, .032f, .095f), C(.120f, .140f, .260f), C(.20f, .30f, .46f), C(.27f, .32f, .50f), .95f, 1f, .7f, .40f, .05f, 8f, .095f);
                // total darkness, then a sky full of stars
                case Chapter.Finale:
                    return M(C(.008f, .014f, .050f), C(.055f, .085f, .170f), C(.10f, .20f, .36f), C(.19f, .23f, .38f), .50f, 1f, 1f, .20f, 0f, 14f, .095f);
                // after the long night: the warmest, most colourful sky of the game
                default:
                    return M(C(.026f, .050f, .145f), C(.200f, .220f, .420f), C(.34f, .46f, .66f), C(.42f, .50f, .74f), 1.45f, 1f, .9f, .65f, .25f, 18f, .105f);
            }
        }

        Mood mood = MoodFor(Chapter.Title), moodFrom, moodTo = MoodFor(Chapter.Title);
        float moodT = 1f;
        ChapterLook look;

        public void SetMood(Chapter c, bool instant = false)
        {
            moodFrom = mood;
            moodTo = MoodFor(c);
            moodT = instant ? 1f : 0f;
            if (instant) mood = moodTo;
        }

        static Mood Blend(Mood a, Mood b, float t) => new Mood
        {
            Zenith = Color.Lerp(a.Zenith, b.Zenith, t), Horizon = Color.Lerp(a.Horizon, b.Horizon, t), HorizonGlow = Color.Lerp(a.HorizonGlow, b.HorizonGlow, t),
            CloudLit = Color.Lerp(a.CloudLit, b.CloudLit, t), AmbientSky = Color.Lerp(a.AmbientSky, b.AmbientSky, t),
            AmbientEquator = Color.Lerp(a.AmbientEquator, b.AmbientEquator, t), AmbientGround = Color.Lerp(a.AmbientGround, b.AmbientGround, t),
            Light = Color.Lerp(a.Light, b.Light, t), LightIntensity = Mathf.Lerp(a.LightIntensity, b.LightIntensity, t), Fog = Mathf.Lerp(a.Fog, b.Fog, t),
            Stars = Mathf.Lerp(a.Stars, b.Stars, t), MilkyWay = Mathf.Lerp(a.MilkyWay, b.MilkyWay, t), CloudBank = Mathf.Lerp(a.CloudBank, b.CloudBank, t),
            Exposure = Mathf.Lerp(a.Exposure, b.Exposure, t), Saturation = Mathf.Lerp(a.Saturation, b.Saturation, t), EarthSize = Mathf.Lerp(a.EarthSize, b.EarthSize, t),
        };

        Camera cam;
        ParticleSystem stars;
        ParticleSystem.Particle[] starBuf;
        float[] starBase;
        Transform earth;
        Material earthMat, skyMat;
        static readonly int HorizonId = Shader.PropertyToID("_JG_SkyHorizon"), ZenithId = Shader.PropertyToID("_JG_SkyZenith");
        static readonly int EarthDirectionId = Shader.PropertyToID("_JG_EarthDirection");
        static readonly int EarthReflectionId = Shader.PropertyToID("_JG_EarthReflectionColor");
        Texture2D earthTex;
        float shownPollution, shownPhase = -1f;

        public void Setup(Camera camera)
        {
            cam = camera;
            // The sea reads opaque depth for its shore contact foam, including on WebGL.
            cam.depthTextureMode |= DepthTextureMode.Depth;
            cam.GetUniversalAdditionalCameraData().requiresDepthTexture = true;
            earthTex = new Texture2D(512, 512, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp };
            look = ChapterLook.Create();
            var baseSky = Resources.Load<Material>("Materials/Base_Skybox");
            if (baseSky != null)
            {
                // stars, milky way and the Earth all live in the skybox: never fogged, and the
                // sea and ambient pick up the night colours instead of a daylight default
                skyMat = new Material(baseSky);
                skyMat.SetTexture("_EarthTex", earthTex);
                skyMat.SetVector("_EarthDir", EarthSkyDir);
                var panorama = Panorama != null ? Panorama : Resources.Load<Texture2D>("World/S01_sky");
                if (panorama != null) skyMat.SetTexture("_PanoramaTex", panorama);
                skyMat.SetFloat("_PanoramaBlend", panorama != null ? 0.65f : 0f);
                RenderSettings.skybox = skyMat;
                cam.clearFlags = CameraClearFlags.Skybox;
            }
            else
            {
                BuildStars();
                BuildEarth();
                RenderSettings.skybox = null;
                cam.clearFlags = CameraClearFlags.SolidColor;
            }
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.reflectionIntensity = 0.32f;
            RenderSettings.fog = true;
            // exponential-squared haze: clear around the island, the far sea melts into the horizon
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = 0.0042f;
            ApplyAtmosphere(0f, mood.Zenith, mood.Horizon);
        }

        void BuildStars()
        {
            var go = new GameObject("Stars");
            go.transform.SetParent(transform, false);
            stars = go.AddComponent<ParticleSystem>();
            stars.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = stars.main;
            main.loop = false;
            main.playOnAwake = false;
            main.maxParticles = 2400;
            main.simulationSpace = ParticleSystemSimulationSpace.Local;
            main.startLifetime = 1e6f;
            var emission = stars.emission;
            emission.enabled = false;
            var shape = stars.shape;
            shape.enabled = false;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = MaterialKit.Additive(Color.white);
            r.minParticleSize = 0f;
            r.maxParticleSize = 0.02f;
            var rng = new System.Random(2026);
            starBuf = new ParticleSystem.Particle[2200];
            starBase = new float[starBuf.Length];
            for (int i = 0; i < starBuf.Length; ++i)
            {
                // upper hemisphere, denser toward the horizon band
                float u = (float)rng.NextDouble() * 2f * Mathf.PI;
                float y = Mathf.Pow((float)rng.NextDouble(), 0.8f) * 0.98f + 0.02f;
                float rr = Mathf.Sqrt(1f - y * y);
                Vector3 p = new Vector3(Mathf.Cos(u) * rr, y, Mathf.Sin(u) * rr) * 380f;
                float mag = Mathf.Pow((float)rng.NextDouble(), 3f);
                starBase[i] = 0.25f + 0.75f * mag;
                float tint = (float)rng.NextDouble();
                starBuf[i].position = p;
                starBuf[i].startSize = 0.9f + 2.2f * mag;
                starBuf[i].startColor = Color.Lerp(new Color(0.75f, 0.85f, 1f), new Color(1f, 0.9f, 0.75f), tint) * starBase[i];
                starBuf[i].remainingLifetime = 1e6f;
                starBuf[i].startLifetime = 1e6f;
            }
            stars.Play();
            stars.SetParticles(starBuf, starBuf.Length);
        }

        void BuildEarth()
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            Destroy(q.GetComponent<Collider>());
            q.name = "Earth";
            q.transform.SetParent(transform, false);
            earth = q.transform;
            // Fallback only; the normal path renders the Earth directly in the skybox.
            earth.localScale = Vector3.one * (34f * EarthDistance / 360f);
            earthMat = MaterialKit.Additive(Color.white);
            earthMat.SetTexture("_BaseMap", earthTex);
            q.GetComponent<Renderer>().sharedMaterial = earthMat;
        }

        const float DiscRadius = 0.86f;

        static readonly Color ZenithWashed = new Color(0.095f, 0.105f, 0.14f), HorizonWashed = new Color(0.19f, 0.19f, 0.205f);

        void ApplyAtmosphere(float p, Color zen, Color hor)
        {
            Shader.SetGlobalColor(HorizonId, hor + mood.HorizonGlow * 0.35f);
            Shader.SetGlobalColor(ZenithId, zen);
            Shader.SetGlobalVector(EarthDirectionId, EarthSkyDir);
            float strength = EarthBrightness * Mathf.Lerp(0.6f, 1f, Mathf.Clamp01(EarthPhase * 3f)) * Mathf.Lerp(1f, 0.5f, p);
            Shader.SetGlobalColor(EarthReflectionId, new Color(0.34f, 0.48f, 0.68f) * strength);
            RenderSettings.fogColor = Color.Lerp(hor * 1.05f + mood.HorizonGlow * 0.25f, new Color(0.22f, 0.22f, 0.24f), p);
            RenderSettings.fogDensity = Mathf.Lerp(mood.Fog, 0.009f, p);
            // Readable sky light, a violet horizon bounce and a green ground bounce. Light
            // pollution greys everything out without crushing the face/path shadows.
            RenderSettings.ambientSkyColor = Color.Lerp(mood.AmbientSky, new Color(0.34f, 0.35f, 0.40f), p);
            RenderSettings.ambientEquatorColor = Color.Lerp(mood.AmbientEquator, new Color(0.22f, 0.21f, 0.24f), p);
            RenderSettings.ambientGroundColor = mood.AmbientGround;
            if (Sun != null)
            {
                Sun.color = mood.Light;
                Sun.intensity = mood.LightIntensity * Mathf.Lerp(1f, 0.75f, p);
            }
            if (look != null) look.Apply(mood.Exposure - p * 0.1f, mood.Saturation * (1f - p), p);
        }

        void SkyUpdate()
        {
            if (moodT < 1f)
            {
                moodT = Mathf.MoveTowards(moodT, 1f, Time.deltaTime / 2.5f);
                mood = Blend(moodFrom, moodTo, Mathf.SmoothStep(0f, 1f, moodT));
            }
            if (!Mathf.Approximately(shownPhase, EarthPhase)) { shownPhase = EarthPhase; PaintEarth(EarthPhase); }
            shownPollution = Mathf.MoveTowards(shownPollution, Pollution, Time.deltaTime * 0.5f);
            float p = shownPollution;
            Color zen = Color.Lerp(mood.Zenith, ZenithWashed, p), hor = Color.Lerp(mood.Horizon, HorizonWashed, p);
            skyMat.SetColor("_Zenith", zen);
            skyMat.SetColor("_Horizon", hor);
            skyMat.SetColor("_HorizonGlow", Color.Lerp(mood.HorizonGlow, new Color(0.2f, 0.2f, 0.21f), p));
            skyMat.SetColor("_CloudLit", Color.Lerp(mood.CloudLit, new Color(0.3f, 0.3f, 0.32f), p));
            skyMat.SetFloat("_CloudBank", mood.CloudBank);
            skyMat.SetFloat("_EarthSize", mood.EarthSize);
            skyMat.SetFloat("_Stars", Mathf.Clamp01(mood.Stars - p * 1.2f));
            skyMat.SetFloat("_MilkyWay", Mathf.Lerp(mood.MilkyWay, 0f, p));
            skyMat.SetFloat("_EarthBrightness", EarthBrightness * Mathf.Lerp(1f, 0.5f, p));
            skyMat.SetColor("_Glow", Color.Lerp(new Color(0.25f, 0.42f, 0.78f), new Color(0.25f, 0.25f, 0.28f), p) * Mathf.Lerp(0.5f, 1.2f, Mathf.Clamp01(EarthPhase * 2.5f)));
            ApplyAtmosphere(p, zen, hor);
        }

        // Lit amount of a sphere point seen at disc coordinates (fx, fy) in [-1, 1].
        // EarthPhase is the visible lit fraction of the disc: the light direction has
        // z = 2*phase - 1 toward the viewer, so 0 = new (dark), .5 = half disc, 1 = full disc.
        static float Lit(float fx, float fy, float phase)
        {
            float r2 = (fx * fx + fy * fy) / (DiscRadius * DiscRadius);
            if (r2 >= 1f) return 0f;
            float lz = 2f * Mathf.Clamp01(phase) - 1f, lx = Mathf.Sqrt(1f - lz * lz);
            float ndl = fx / DiscRadius * lx + Mathf.Sqrt(1f - r2) * lz;
            return Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(-0.03f, 0.05f, ndl));
        }

        // QA helper: fraction of the disc that is lit (lit > 0.5) for a given phase.
        public static float LitFraction(float phase, int n = 256)
        {
            int disc = 0, lit = 0;
            for (int y = 0; y < n; ++y)
                for (int x = 0; x < n; ++x)
                {
                    float fx = (x + 0.5f) / n * 2f - 1f, fy = (y + 0.5f) / n * 2f - 1f;
                    if (fx * fx + fy * fy >= DiscRadius * DiscRadius) continue;
                    ++disc;
                    if (Lit(fx, fy, phase) > 0.5f) ++lit;
                }
            return disc == 0 ? 0f : (float)lit / disc;
        }

        static float Fbm(float x, float y)
        {
            float v = 0f, a = 0.5f;
            for (int o = 0; o < 5; ++o) { v += Mathf.PerlinNoise(x, y) * a; x = x * 2.03f + 17.1f; y = y * 2.03f + 9.7f; a *= 0.5f; }
            return v;
        }

        // Blue Earth seen from very far: deep oceans, green-ochre continents, swirling white
        // cloud, a faint earthshine on the dark side and a thin atmosphere glow on the lit limb.
        Color[] earthSurface;
        float[] earthDepth;

        // The surface (oceans, continents, clouds) is noise-heavy, so it is painted once;
        // each phase change only relights it, which is cheap enough to animate the long night.
        void PaintSurface(int n)
        {
            earthSurface = new Color[n * n];
            earthDepth = new float[n * n];
            // The user's S07 painting (a fully lit Earth disc, ~84% of the square) replaces the
            // procedural surface when present; the phase lighting below stays procedural.
            var painted = Resources.Load<Texture2D>("World/S07_earth");
            if (painted != null && painted.isReadable)
            {
                for (int y = 0; y < n; ++y)
                    for (int x = 0; x < n; ++x)
                    {
                        float fx = (x + 0.5f) / n * 2f - 1f, fy = (y + 0.5f) / n * 2f - 1f;
                        float d = Mathf.Sqrt(fx * fx + fy * fy);
                        if (d > DiscRadius + 0.08f) continue;
                        earthSurface[y * n + x] = painted.GetPixelBilinear(0.5f + fx / DiscRadius * 0.42f, 0.5f + fy / DiscRadius * 0.42f);
                        earthDepth[y * n + x] = Mathf.Sqrt(Mathf.Max(0f, 1f - (d / DiscRadius) * (d / DiscRadius)));
                    }
                return;
            }
            var ocean = new Color(0.10f, 0.30f, 0.72f);
            var shallow = new Color(0.18f, 0.50f, 0.82f);
            var land = new Color(0.36f, 0.48f, 0.26f);
            var desert = new Color(0.66f, 0.56f, 0.38f);
            var cloud = new Color(0.97f, 0.98f, 1f);
            for (int y = 0; y < n; ++y)
                for (int x = 0; x < n; ++x)
                {
                    float fx = (x + 0.5f) / n * 2f - 1f, fy = (y + 0.5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(fx * fx + fy * fy);
                    if (d > DiscRadius + 0.08f) continue;
                    // fake sphere mapping so features compress toward the limb
                    float z = Mathf.Sqrt(Mathf.Max(0f, 1f - (d / DiscRadius) * (d / DiscRadius)));
                    float sx = fx / DiscRadius / (0.6f + z * 0.4f), sy = fy / DiscRadius / (0.6f + z * 0.4f);
                    float continent = Fbm(sx * 1.6f + 3.1f, sy * 1.6f + 5.3f);
                    float landMask = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.50f, 0.56f, continent));
                    float coast = Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(0.44f, 0.52f, continent)) * (1f - landMask);
                    Color surface = Color.Lerp(ocean, shallow, coast * 0.8f);
                    surface = Color.Lerp(surface, Color.Lerp(land, desert, Mathf.Clamp01((Fbm(sx * 4f, sy * 4f) - 0.45f) * 3f)), landMask);
                    float swirl = Fbm(sx * 2.6f + Mathf.Sin(sy * 3f) * 0.6f + 11f, sy * 5.2f + 2f);
                    float clouds = Mathf.Clamp01((swirl - 0.50f) * 3.4f);
                    earthSurface[y * n + x] = Color.Lerp(surface, cloud, clouds * 0.9f);
                    earthDepth[y * n + x] = z;
                }
        }

        void PaintEarth(float phase)
        {
            int n = earthTex.width;
            if (earthSurface == null) PaintSurface(n);
            var px = new Color32[n * n];
            for (int y = 0; y < n; ++y)
                for (int x = 0; x < n; ++x)
                {
                    float fx = (x + 0.5f) / n * 2f - 1f, fy = (y + 0.5f) / n * 2f - 1f;
                    float d = Mathf.Sqrt(fx * fx + fy * fy);
                    if (d > DiscRadius + 0.08f) { px[y * n + x] = new Color32(0, 0, 0, 255); continue; }
                    float disc = Mathf.Clamp01((DiscRadius - d) * 120f);
                    float lit = Lit(fx, fy, phase) * disc;
                    float z = earthDepth[y * n + x];
                    Color surface = earthSurface[y * n + x];
                    float limb = Mathf.Clamp01(1f - Mathf.Abs(d - DiscRadius) * 16f);
                    float glow = limb * 0.45f * Mathf.Clamp01(Lit(fx * 0.97f, fy * 0.97f, phase) * 3f);
                    Color c = surface * (lit * 1.2f * (0.75f + 0.25f * z) + disc * 0.03f) + new Color(0.45f, 0.68f, 1f) * glow;
                    c.a = 1f;
                    px[y * n + x] = c;
                }
            earthTex.SetPixels32(px);
            earthTex.Apply(true);
        }

        void LateUpdate()
        {
            if (cam == null) return;
            if (skyMat != null) { SkyUpdate(); return; }
            if (moodT < 1f) { moodT = Mathf.MoveTowards(moodT, 1f, Time.deltaTime / 2.5f); mood = Blend(moodFrom, moodTo, Mathf.SmoothStep(0f, 1f, moodT)); }
            transform.position = cam.transform.position;
            earth.position = cam.transform.position + EarthSkyDir * EarthDistance;
            earth.rotation = Quaternion.LookRotation(earth.position - cam.transform.position, Vector3.up) * Quaternion.Euler(0f, 0f, -28f);
            if (!Mathf.Approximately(shownPhase, EarthPhase)) { shownPhase = EarthPhase; PaintEarth(EarthPhase); }
            MaterialKit.SetColor(earthMat, Color.white * EarthBrightness);

            shownPollution = Mathf.MoveTowards(shownPollution, Pollution, Time.deltaTime * 0.5f);
            Color sky = Color.Lerp(DeepNight, Washed, shownPollution);
            cam.backgroundColor = sky;
            ApplyAtmosphere(shownPollution, Color.Lerp(mood.Zenith, ZenithWashed, shownPollution), Color.Lerp(mood.Horizon, HorizonWashed, shownPollution));
            float visible = Mathf.Clamp01(1f - shownPollution * 1.15f);
            for (int i = 0; i < starBuf.Length; ++i)
            {
                float tw = 0.85f + 0.15f * Mathf.Sin(Time.time * (1.3f + (i % 7) * 0.4f) + i);
                var c = starBuf[i].startColor;
                Color col = c;
                col.a = Mathf.Clamp01(starBase[i] * tw * visible * (starBase[i] > 0.6f ? 1f : visible));
                starBuf[i].startColor = col;
            }
            stars.SetParticles(starBuf, starBuf.Length);
        }

        void OnDestroy()
        {
            if (RenderSettings.skybox == skyMat) RenderSettings.skybox = null;
            if (skyMat != null) Destroy(skyMat);
            if (earthMat != null) Destroy(earthMat);
            if (earthTex != null) Destroy(earthTex);
        }
    }
}
