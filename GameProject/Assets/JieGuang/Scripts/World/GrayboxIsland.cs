using UnityEngine;

namespace JieGuang
{
    // Placeholder island used until Island.prefab exists: the cape (cottage, golden tree,
    // armillary, bench, boulder, pier and flagpole), a ramp through the light-tree wood and a
    // village plateau. Primitive shapes only; every anchor sits where IslandLayout expects it.
    public static class GrayboxIsland
    {
        static readonly Color Stone = new Color(0.42f, 0.42f, 0.40f);
        static readonly Color Grass = new Color(0.20f, 0.27f, 0.22f);
        static readonly Color Wood = new Color(0.36f, 0.25f, 0.16f);
        static readonly Color Cream = new Color(0.82f, 0.78f, 0.68f);
        static readonly Color Teal = new Color(0.20f, 0.42f, 0.42f);
        static readonly Color Ochre = new Color(0.55f, 0.27f, 0.18f);
        static readonly Color Slate = new Color(0.36f, 0.38f, 0.40f);
        static readonly Color Copper = new Color(0.62f, 0.38f, 0.22f);
        public static readonly Color WindowWarm = new Color(1f, 0.72f, 0.38f);

        static Transform root;

        static GameObject Prim(PrimitiveType t, string name, Vector3 pos, Vector3 scale, Color c, Vector3? euler = null, Transform parent = null, bool collider = true, Color? emission = null)
        {
            var go = GameObject.CreatePrimitive(t);
            go.name = name;
            go.transform.SetParent(parent != null ? parent : root, false);
            go.transform.localPosition = pos;
            go.transform.localScale = scale;
            if (euler.HasValue) go.transform.localEulerAngles = euler.Value;
            go.GetComponent<Renderer>().sharedMaterial = MaterialKit.Lit(c, 0.12f, emission);
            if (!collider) Object.Destroy(go.GetComponent<Collider>());
            else if (t == PrimitiveType.Cylinder)
            {
                // the built-in capsule collider would round the top of flat discs
                Object.DestroyImmediate(go.GetComponent<Collider>());
                go.AddComponent<MeshCollider>().sharedMesh = go.GetComponent<MeshFilter>().sharedMesh;
            }
            return go;
        }

        static Transform Group(string name, Transform parent = null)
        {
            var g = new GameObject(name).transform;
            g.SetParent(parent != null ? parent : root, false);
            return g;
        }

        public static GameObject Build()
        {
            root = new GameObject("Island (graybox)").transform;
            // sea and land
            var sea = Prim(PrimitiveType.Plane, "Sea", new Vector3(0f, -0.35f, 0f), new Vector3(60f, 1f, 60f), new Color(0.03f, 0.06f, 0.11f));
            sea.GetComponent<Renderer>().sharedMaterial = MaterialKit.Lit(new Color(0.03f, 0.06f, 0.11f), 0.92f);
            Object.Destroy(sea.GetComponent<Collider>());
            Prim(PrimitiveType.Cylinder, "Cape", new Vector3(-1f, -0.6f, 0f), new Vector3(24f, 0.6f, 22f), Grass);
            Prim(PrimitiveType.Cylinder, "VillagePlateau", new Vector3(-27f, 5.4f, 16f), new Vector3(26f, 0.6f, 22f), Grass);
            Prim(PrimitiveType.Cylinder, "VillagePlinth", new Vector3(-27f, 2.4f, 16f), new Vector3(24f, 3f, 20f), new Color(0.3f, 0.3f, 0.28f));
            // ramp from the crossroad up to the village (about 22 degrees)
            Vector3 a = new Vector3(-9.5f, -0.05f, -2.5f), b = new Vector3(-19.5f, 6f, 8.5f);
            Vector3 mid = (a + b) / 2f, d = b - a;
            var ramp = Prim(PrimitiveType.Cube, "SlopeRoad", mid + Vector3.down * 0.25f, new Vector3(5f, 0.5f, d.magnitude + 1f), Grass);
            ramp.transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
            var road = Prim(PrimitiveType.Cube, "SlopeRoadStones", mid + Vector3.up * 0.01f, new Vector3(1.6f, 0.02f, d.magnitude), Stone, collider: false);
            road.transform.rotation = ramp.transform.rotation;
            road.transform.position = mid + ramp.transform.up * 0.02f;
            // light-tree wood along the slope
            var wood = Group("LightTreeWood");
            var rng = new System.Random(7);
            for (int i = 0; i < 26; ++i)
            {
                float t = (float)rng.NextDouble();
                float side = (rng.Next(2) == 0 ? -1f : 1f) * (3.6f + 5f * (float)rng.NextDouble());
                Vector3 p = Vector3.Lerp(a, b, t) + Vector3.Cross(Vector3.up, d.normalized) * side;
                p.y = Mathf.Lerp(a.y, b.y, t) - 0.6f;
                Tree(wood, p, 0.8f + 0.5f * (float)rng.NextDouble(), new Color(0.55f, 0.66f, 0.60f), new Color(0.05f, 0.12f, 0.09f));
            }
            // cape path: crossroad -> armillary -> cottage, and a branch to the pier
            Path(new Vector3(-8f, 0f, -5f), new Vector3(-4f, 0f, -2f));
            Path(new Vector3(-4f, 0f, -2f), new Vector3(0f, 0f, 1f));
            Path(new Vector3(0f, 0f, 1f), new Vector3(3.4f, 0f, 2.2f));
            Path(new Vector3(-1f, 0f, -0.5f), new Vector3(2f, 0f, -5.8f));
            Prim(PrimitiveType.Sphere, "Boulder", new Vector3(-8.6f, 0.35f, -3.4f), new Vector3(1.5f, 1.2f, 1.3f), Stone);
            // bench by the path
            var bench = Group("Bench");
            bench.position = new Vector3(-4.2f, 0f, -6.6f);
            Prim(PrimitiveType.Cube, "Seat", new Vector3(0f, 0.42f, 0f), new Vector3(1.5f, 0.08f, 0.45f), Wood, parent: bench);
            Prim(PrimitiveType.Cube, "Back", new Vector3(0f, 0.75f, -0.22f), new Vector3(1.5f, 0.5f, 0.06f), Wood, parent: bench, collider: false);
            for (int s = -1; s <= 1; s += 2)
                Prim(PrimitiveType.Cube, "Leg", new Vector3(0.65f * s, 0.2f, 0f), new Vector3(0.08f, 0.4f, 0.4f), Wood, parent: bench, collider: false);
            // cottage with the round window
            var house = Group("ABoCottage");
            house.position = new Vector3(4.6f, 0f, 4.6f);
            Prim(PrimitiveType.Cube, "Walls", new Vector3(0f, 1.5f, 0f), new Vector3(4.2f, 3f, 3.6f), Cream, parent: house);
            var roof = Prim(PrimitiveType.Cube, "Roof", new Vector3(0f, 3.35f, 0f), new Vector3(3.3f, 3.3f, 3.9f), Teal, new Vector3(0f, 0f, 45f), house, false);
            roof.transform.localScale = new Vector3(3.2f, 3.2f, 3.9f);
            var window = Prim(PrimitiveType.Cylinder, "RoundWindow", new Vector3(-1f, 1.7f, -1.83f), new Vector3(0.95f, 0.03f, 0.95f), new Color(0.15f, 0.12f, 0.1f), new Vector3(90f, 0f, 0f), house, false);
            window.AddComponent<WindowGlow>();
            Prim(PrimitiveType.Cube, "Door", new Vector3(1.1f, 1f, -1.82f), new Vector3(0.9f, 2f, 0.06f), Wood, parent: house, collider: false);
            // golden tree and crescent sculpture
            var gold = Group("GoldenTree");
            gold.position = new Vector3(6.5f, 0f, -0.5f);
            Prim(PrimitiveType.Cylinder, "Trunk", new Vector3(0f, 1.3f, 0f), new Vector3(0.35f, 1.3f, 0.35f), Wood, parent: gold);
            Prim(PrimitiveType.Sphere, "Crown", new Vector3(0f, 3.3f, 0f), new Vector3(3.2f, 2.4f, 3.2f), new Color(0.75f, 0.6f, 0.25f), parent: gold, collider: false, emission: new Color(0.22f, 0.15f, 0.03f));
            var crescent = Group("CrescentSculpture", gold);
            crescent.localPosition = new Vector3(-2.2f, 0f, -1.4f);
            for (int i = 0; i < 7; ++i)
            {
                float ang = Mathf.Lerp(-70f, 70f, i / 6f) * Mathf.Deg2Rad;
                Prim(PrimitiveType.Sphere, "Arc", new Vector3(Mathf.Sin(ang) * 0.8f, 1.1f + Mathf.Cos(ang) * 0.8f, 0f), Vector3.one * (0.32f - Mathf.Abs(i - 3) * 0.04f), new Color(0.85f, 0.65f, 0.25f), parent: crescent, collider: false, emission: new Color(0.25f, 0.17f, 0.04f));
            }
            // armillary on a round stone platform
            var arm = Group("Armillary");
            arm.position = new Vector3(0f, 0f, 2.2f);
            Prim(PrimitiveType.Cylinder, "Platform", new Vector3(0f, 0.12f, 0f), new Vector3(3f, 0.12f, 3f), Stone, parent: arm);
            for (int i = 0; i < 3; ++i)
                Prim(PrimitiveType.Cylinder, "Ring", new Vector3(0f, 1.3f, 0f), new Vector3(1.4f, 0.01f, 1.4f), Copper, new Vector3(90f, i * 60f, 23f), arm, false);
            // pier, flagpole, crate and the boat
            Prim(PrimitiveType.Cube, "PierDeck", new Vector3(2f, 0.25f, -12f), new Vector3(2.2f, 0.3f, 12.6f), Wood);
            for (int i = 0; i < 7; ++i)
                for (int s = -1; s <= 1; s += 2)
                    Prim(PrimitiveType.Cylinder, "PierPost", new Vector3(2f + 1.05f * s, -0.2f, -6.2f - i * 2f), new Vector3(0.2f, 0.6f, 0.2f), Wood, collider: false);
            var flag = Group("Flagpole");
            flag.position = new Vector3(2f, 0.4f, -17.9f);
            Prim(PrimitiveType.Cylinder, "Pole", new Vector3(0f, 2.5f, 0f), new Vector3(0.1f, 2.5f, 0.1f), Wood, parent: flag);
            Prim(PrimitiveType.Cube, "Flag", new Vector3(0.55f, 4.5f, 0f), new Vector3(1f, 0.65f, 0.02f), new Color(0.16f, 0.27f, 0.5f), parent: flag, collider: false);
            Prim(PrimitiveType.Cube, "Hook", new Vector3(0f, 2.05f, 0.08f), new Vector3(0.05f, 0.05f, 0.18f), new Color(0.2f, 0.2f, 0.2f), parent: flag, collider: false);
            Prim(PrimitiveType.Cube, "Crate", new Vector3(2.9f, 0.62f, -17.1f), new Vector3(0.7f, 0.45f, 0.55f), Wood);
            var boat = Group("Boat");
            boat.position = new Vector3(3.8f, 0f, -19.5f);
            Prim(PrimitiveType.Cube, "Hull", new Vector3(0f, 0.1f, 0f), new Vector3(1.8f, 0.6f, 4.2f), Wood, parent: boat, collider: false);
            // village: houses whose windows the director lights and darkens
            var windows = Group("Village_Windows");
            var houses = Group("VillageHouses");
            Color[] roofs = { Teal, Ochre, Slate };
            for (int i = 0; i < 11; ++i)
            {
                float ang = i * 33f * Mathf.Deg2Rad;
                float r = 4f + (i % 4) * 2.4f;
                Vector3 p = new Vector3(-27f + Mathf.Cos(ang) * r, 6f, 16f + Mathf.Sin(ang) * r);
                var h = Group("House" + i, houses);
                h.position = p;
                h.rotation = Quaternion.LookRotation(new Vector3(0f, 0f, -12f) - p, Vector3.up);
                h.rotation = Quaternion.Euler(0f, h.eulerAngles.y, 0f);
                Prim(PrimitiveType.Cube, "Walls", new Vector3(0f, 1.2f, 0f), new Vector3(2.6f, 2.4f, 2.2f), Cream, parent: h);
                Prim(PrimitiveType.Cube, "Roof", new Vector3(0f, 2.75f, 0f), new Vector3(2.1f, 2.1f, 2.5f), roofs[i % 3], new Vector3(0f, 90f, 45f), h, false).transform.localScale = new Vector3(2.0f, 2.0f, 2.8f);
                var w = Prim(PrimitiveType.Quad, "Window" + i, new Vector3(0f, 0f, 0f), new Vector3(0.7f, 0.6f, 1f), WindowWarm, collider: false, parent: windows);
                w.transform.position = h.TransformPoint(new Vector3(-0.5f, 1.4f, 1.12f));
                w.transform.rotation = h.rotation * Quaternion.Euler(0f, 180f, 0f);
                w.AddComponent<WindowGlow>().Intensity = 2.2f;
            }
            Prim(PrimitiveType.Cylinder, "Well", new Vector3(-27f, 6.4f, 16f), new Vector3(1.1f, 0.4f, 1.1f), Stone);
            Tree(root, new Vector3(-24.5f, 6f, 19f), 1.6f, new Color(0.55f, 0.66f, 0.60f), new Color(0.06f, 0.14f, 0.1f));
            return root.gameObject;
        }

        static void Path(Vector3 from, Vector3 to)
        {
            Vector3 d = to - from;
            var p = Prim(PrimitiveType.Cube, "PathStones", (from + to) / 2f + Vector3.up * 0.015f, new Vector3(1.3f, 0.03f, d.magnitude + 0.6f), Stone, collider: false);
            p.transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
        }

        static void Tree(Transform parent, Vector3 pos, float size, Color leaf, Color glow)
        {
            var t = Group("LightTree", parent);
            t.position = pos;
            Prim(PrimitiveType.Cylinder, "Trunk", new Vector3(0f, 1.1f * size, 0f), new Vector3(0.22f * size, 1.1f * size, 0.22f * size), Wood, parent: t);
            Prim(PrimitiveType.Sphere, "Crown", new Vector3(0f, 2.6f * size, 0f), new Vector3(2.2f, 1.8f, 2.2f) * size, leaf, parent: t, collider: false, emission: glow);
        }

        public static void OrientCameras(IslandLayout layout)
        {
            Look(layout.Get("Cam_Title"), new Vector3(-9f, 2f, -3f));
            Look(layout.Get("Cam_Puzzle"), new Vector3(-1.5f, 0f, -3.5f));
            Look(layout.Get("Cam_Pier"), new Vector3(2f, 1.2f, -15f));
        }

        static void Look(Transform cam, Vector3 at)
        {
            if (cam != null) cam.rotation = Quaternion.LookRotation(at - cam.position, Vector3.up);
        }
    }
}
