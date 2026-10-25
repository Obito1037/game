using UnityEngine;
using UnityEngine.UI;

namespace JieGuang
{
    // Shared look for every screen (modelled on the reference's storybook UI): one serif face,
    // warm ivory text, gold accents and four-point sparkles, thin gold-edged translucent panels,
    // rounded key caps and a parchment sheet. All sprites are generated here, no image files.
    public static class UiKit
    {
        public static readonly Color Ivory = new Color(0.96f, 0.93f, 0.86f);
        public static readonly Color Gold = new Color(0.93f, 0.76f, 0.42f);
        public static readonly Color GoldDim = new Color(0.93f, 0.76f, 0.42f, 0.55f);
        public static readonly Color Ink = new Color(0.13f, 0.16f, 0.27f);
        public static readonly Color Night = new Color(0.035f, 0.06f, 0.15f);
        public static readonly Color PanelFill = new Color(0.07f, 0.06f, 0.05f, 0.72f);

        static Font font;
        static Sprite sparkle, softDot, panel, pill, keycap, circle, parchment, glow;

        public static Font Font => font != null ? font : (font = Resources.Load<Font>("Fonts/NotoSerifSC"));

        // The reference spaces display type widely; legacy Text has no tracking, so pad with
        // hair spaces between characters.
        public static string Track(string s, int spaces = 1)
        {
            if (string.IsNullOrEmpty(s)) return s;
            var pad = new string(' ', spaces);
            var sb = new System.Text.StringBuilder(s.Length * (spaces + 1));
            for (int i = 0; i < s.Length; ++i)
            {
                sb.Append(s[i]);
                if (i < s.Length - 1 && s[i] != '\n' && s[i + 1] != '\n') sb.Append(pad);
            }
            return sb.ToString();
        }

        // ---------------------------------------------------------------- procedural sprites
        static Sprite Make(int w, int h, System.Func<float, float, Color> f, Vector4 border = default, string name = "ui")
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = name };
            var px = new Color[w * h];
            for (int y = 0; y < h; ++y)
                for (int x = 0; x < w; ++x)
                    px[y * w + x] = f(x + 0.5f, y + 0.5f);
            t.SetPixels(px);
            t.Apply();
            return Sprite.Create(t, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, border);
        }

        // Four-point star: two thin crossed diamonds with a soft core.
        public static Sprite Sparkle => sparkle != null ? sparkle : sparkle = Make(128, 128, (x, y) =>
        {
            float u = Mathf.Abs(x - 64f) / 64f, v = Mathf.Abs(y - 64f) / 64f;
            float arm = Mathf.Max(Mathf.Clamp01(1f - (u + v * 6f)), Mathf.Clamp01(1f - (v + u * 6f)));
            float core = Mathf.Clamp01(1f - Mathf.Sqrt(u * u + v * v) * 3.2f);
            float a = Mathf.Clamp01(Mathf.Pow(arm, 0.8f) + core * 0.8f);
            return new Color(1f, 1f, 1f, a);
        }, default, "sparkle");

        public static Sprite SoftDot => softDot != null ? softDot : softDot = Make(64, 64, (x, y) =>
        {
            float d = Vector2.Distance(new Vector2(x, y), new Vector2(32f, 32f)) / 32f;
            return new Color(1f, 1f, 1f, Mathf.Clamp01(1f - d) * Mathf.Clamp01(1f - d));
        }, default, "dot");

        public static Sprite Glow => glow != null ? glow : glow = Make(128, 128, (x, y) =>
        {
            float d = Vector2.Distance(new Vector2(x, y), new Vector2(64f, 64f)) / 64f;
            return new Color(1f, 1f, 1f, Mathf.Pow(Mathf.Clamp01(1f - d), 2.2f));
        }, default, "glow");

        static Sprite ring;
        public static Sprite Ring => ring != null ? ring : ring = Make(256, 256, (x, y) =>
        {
            float d = Vector2.Distance(new Vector2(x, y), new Vector2(128f, 128f));
            return new Color(1f, 1f, 1f, Mathf.Clamp01(2.2f - Mathf.Abs(d - 124f)));
        }, default, "ring");

        public static Sprite Circle => circle != null ? circle : circle = Make(256, 256, (x, y) =>
        {
            float d = Vector2.Distance(new Vector2(x, y), new Vector2(128f, 128f));
            return new Color(1f, 1f, 1f, Mathf.Clamp01(127f - d));
        }, default, "circle");

        // Rounded rectangle, filled, with a 1.5px border in the alpha of the outline channel.
        static Sprite Rounded(int size, float radius, bool filled, float stroke, string name)
        {
            return Make(size, size, (x, y) =>
            {
                float c = size / 2f;
                float qx = Mathf.Max(Mathf.Abs(x - c) - (c - radius), 0f), qy = Mathf.Max(Mathf.Abs(y - c) - (c - radius), 0f);
                float outside = Mathf.Sqrt(qx * qx + qy * qy) - radius + Mathf.Min(Mathf.Max(Mathf.Abs(x - c) - (c - radius), Mathf.Abs(y - c) - (c - radius)), 0f);
                float shape = Mathf.Clamp01(0.5f - outside);
                // 1 inside the band -stroke..0 of the signed distance, antialiased by half a pixel
                float edge = Mathf.Clamp01(stroke * 0.5f - Mathf.Abs(outside + stroke * 0.5f) + 0.5f);
                return filled ? new Color(1f, 1f, 1f, shape) : new Color(1f, 1f, 1f, edge);
            }, new Vector4(radius + 2, radius + 2, radius + 2, radius + 2), name);
        }

        public static Sprite PanelFillSprite => panel != null ? panel : panel = Rounded(64, 6f, true, 0f, "panel");
        static Sprite panelEdge, keycapEdge;
        public static Sprite PanelEdge => panelEdge != null ? panelEdge : panelEdge = Rounded(64, 6f, false, 1.4f, "panelEdge");
        public static Sprite Pill => pill != null ? pill : pill = Rounded(64, 30f, false, 1.6f, "pill");
        public static Sprite KeycapEdge => keycapEdge != null ? keycapEdge : keycapEdge = Rounded(64, 12f, false, 2.2f, "keycap");

        // Aged paper with fibre noise, faint water stains and a torn, darkened edge.
        public static Sprite Parchment => parchment != null ? parchment : parchment = MakeParchment(1024, 640);

        static Sprite MakeParchment(int w, int h)
        {
            return Make(w, h, (x, y) =>
            {
                float nx = x / w, ny = y / h;
                float edge = Mathf.Min(Mathf.Min(nx, 1f - nx) * w / h, Mathf.Min(ny, 1f - ny));
                float torn = 0.025f + 0.018f * Mathf.PerlinNoise(nx * 38f, ny * 38f) + 0.012f * Mathf.PerlinNoise(nx * 140f + 7f, ny * 140f);
                if (edge < torn) return new Color(0, 0, 0, 0);
                float burn = Mathf.Clamp01((edge - torn) / 0.06f);
                float fibre = Mathf.PerlinNoise(nx * 220f, ny * 9f) * 0.05f + Mathf.PerlinNoise(nx * 9f, ny * 220f) * 0.04f;
                float stain = Mathf.PerlinNoise(nx * 4f + 3f, ny * 4f) * 0.12f + Mathf.PerlinNoise(nx * 11f, ny * 11f + 5f) * 0.06f;
                var paper = new Color(0.95f, 0.90f, 0.78f) * (1f - stain * 0.6f - fibre);
                paper = Color.Lerp(new Color(0.62f, 0.48f, 0.30f), paper, Mathf.Lerp(0.35f, 1f, burn));
                paper.a = 1f;
                return paper;
            }, default, "parchment");
        }

        static Texture2D starfield;
        static Sprite hGradient, vGradient;

        // Deep navy night with fine stars and a few four-point sparkles (chapter cards, map, title).
        public static Texture2D Starfield
        {
            get
            {
                if (starfield != null) return starfield;
                const int w = 1280, h = 720;
                var t = new Texture2D(w, h, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "starfield" };
                var px = new Color[w * h];
                var rng = new System.Random(612);
                for (int y = 0; y < h; ++y)
                    for (int x = 0; x < w; ++x)
                    {
                        float nx = (float)x / w, ny = (float)y / h;
                        float cloud = Mathf.PerlinNoise(nx * 3f + 2f, ny * 3f) * 0.6f + Mathf.PerlinNoise(nx * 9f, ny * 9f + 4f) * 0.4f;
                        var c = Color.Lerp(new Color(0.025f, 0.04f, 0.11f), new Color(0.07f, 0.10f, 0.24f), cloud * 0.8f + ny * 0.25f);
                        c.a = 1f;
                        px[y * w + x] = c;
                    }
                for (int i = 0; i < 1400; ++i)
                {
                    int x = rng.Next(w), y = rng.Next(h);
                    float b = Mathf.Pow((float)rng.NextDouble(), 3f);
                    float r = 0.6f + b * 1.4f;
                    for (int dy = -2; dy <= 2; ++dy)
                        for (int dx = -2; dx <= 2; ++dx)
                        {
                            int xx = x + dx, yy = y + dy;
                            if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
                            float k = Mathf.Clamp01(1f - Mathf.Sqrt(dx * dx + dy * dy) / r) * (0.35f + 0.65f * b);
                            px[yy * w + xx] = Color.Lerp(px[yy * w + xx], new Color(0.95f, 0.93f, 0.85f), k);
                        }
                }
                t.SetPixels(px);
                t.Apply();
                return starfield = t;
            }
        }

        // Alpha ramps for legibility washes: horizontal (opaque left) and vertical (opaque bottom).
        public static Sprite HGradient => hGradient != null ? hGradient : hGradient = Make(256, 4, (x, y) => new Color(1f, 1f, 1f, Mathf.SmoothStep(1f, 0f, x / 256f)), default, "hgrad");
        public static Sprite VGradient => vGradient != null ? vGradient : vGradient = Make(4, 256, (x, y) => new Color(1f, 1f, 1f, Mathf.SmoothStep(1f, 0f, y / 256f)), default, "vgrad");

        // ---------------------------------------------------------------- builders
        public static RectTransform Rect(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size, Vector2? pivot = null)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var rt = (RectTransform)go.transform;
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = pivot ?? anchor;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static RectTransform Stretch(Transform parent, string name)
        {
            var rt = Rect(parent, name, Vector2.zero, Vector2.zero, Vector2.zero);
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            return rt;
        }

        public static Text Text(Transform parent, string name, string text, int size, Color color, TextAnchor align, Vector2 anchor, Vector2 pos, Vector2 box, bool shadow = true)
        {
            var rt = Rect(parent, name, anchor, pos, box);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = Font;
            t.text = text;
            t.fontSize = size;
            t.color = color;
            t.alignment = align;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            t.lineSpacing = 1.15f;
            if (shadow)
            {
                var s = rt.gameObject.AddComponent<Shadow>();
                // small type gets a lighter shadow so it does not smear
                bool small = size < 28;
                s.effectColor = new Color(0f, 0f, 0.02f, small ? 0.35f : 0.55f);
                s.effectDistance = small ? new Vector2(0.8f, -1f) : new Vector2(1.2f, -1.6f);
            }
            return t;
        }

        public static Image Image(Transform parent, string name, Sprite sprite, Color color, Vector2 anchor, Vector2 pos, Vector2 size, bool sliced = false)
        {
            var rt = Rect(parent, name, anchor, pos, size);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite;
            img.color = color;
            img.raycastTarget = false;
            if (sliced) img.type = UnityEngine.UI.Image.Type.Sliced;
            return img;
        }

        // Thin gold rule with a sparkle riding on it (title blocks, chapter cards, loading bar).
        public static RectTransform GoldRule(Transform parent, string name, Vector2 anchor, Vector2 pos, float width, float sparkleAt = 0.5f)
        {
            var root = Rect(parent, name, anchor, pos, new Vector2(width, 24f));
            var line = Image(root, "Line", null, GoldDim, new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(width, 1.6f));
            line.color = new Color(Gold.r, Gold.g, Gold.b, 0.75f);
            Image(root, "Sparkle", Sparkle, Gold, new Vector2(sparkleAt, 0.5f), Vector2.zero, new Vector2(22f, 22f));
            return root;
        }

        // Panel = translucent dark fill + thin gold edge (dialogue, task card, lamp panel).
        public static RectTransform Panel(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size, float fillAlpha = 0.72f)
        {
            var rt = Rect(parent, name, anchor, pos, size);
            var fill = rt.gameObject.AddComponent<Image>();
            fill.sprite = PanelFillSprite;
            fill.type = UnityEngine.UI.Image.Type.Sliced;
            fill.color = new Color(PanelFill.r, PanelFill.g, PanelFill.b, fillAlpha);
            fill.raycastTarget = false;
            var edge = Image(rt, "Edge", PanelEdge, new Color(Gold.r, Gold.g, Gold.b, 0.55f), new Vector2(0.5f, 0.5f), Vector2.zero, size, true);
            edge.rectTransform.anchorMin = Vector2.zero;
            edge.rectTransform.anchorMax = Vector2.one;
            edge.rectTransform.sizeDelta = Vector2.zero;
            return rt;
        }

        // Rounded key cap with its key label, e.g. [E], [Esc], [Tab].
        public static RectTransform KeyCap(Transform parent, string key, Vector2 anchor, Vector2 pos, float height = 34f)
        {
            bool ascii = key.Length > 0 && key[0] < 128;
            float w = Mathf.Max(height, 22f + key.Length * height * (ascii ? 0.5f : 0.95f));
            var rt = Rect(parent, "Key_" + key, anchor, pos, new Vector2(w, height));
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = KeycapEdge;
            img.type = UnityEngine.UI.Image.Type.Sliced;
            img.color = new Color(Ivory.r, Ivory.g, Ivory.b, 0.85f);
            img.raycastTarget = false;
            Text(rt, "Label", key, Mathf.RoundToInt(height * 0.52f), Ivory, TextAnchor.MiddleCenter, new Vector2(0.5f, 0.5f), new Vector2(0f, 1f), new Vector2(w, height), false);
            return rt;
        }
    }

    // Gentle twinkle for decorative sparkles.
    public sealed class Twinkle : MonoBehaviour
    {
        public float Speed = 1.3f, Min = 0.45f, Phase;
        Graphic g;
        Color baseColor;
        Vector3 baseScale;

        void Start()
        {
            g = GetComponent<Graphic>();
            baseColor = g.color;
            baseScale = transform.localScale;
            if (Phase == 0f) Phase = Random.value * 6f;
        }

        void Update()
        {
            float k = Mathf.Lerp(Min, 1f, 0.5f + 0.5f * Mathf.Sin(Time.unscaledTime * Speed + Phase));
            var c = baseColor;
            c.a *= k;
            g.color = c;
            transform.localScale = baseScale * Mathf.Lerp(0.85f, 1.05f, k);
        }
    }
}
