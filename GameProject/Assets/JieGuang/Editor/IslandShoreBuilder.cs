using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // v3 shore: replaces the island's steep outer rim (which read as the vertical wall of a
    // "cake") with a natural coast — a rounded shoulder, a slope with exposed rock, low beaches
    // where the land is low, and Tripo boulders scattered along the waterline. The walkable top
    // surface (IslandGround) is untouched; only steep ground connected to the open sea is covered.
    // The skirt is one mesh drawn with the same GroundSurface material, so it blends into the
    // existing ground, and it carries a collider so the player stands on what they see.
    public static class IslandShoreBuilder
    {
        const string MeshPath = "Assets/JieGuang/World/Terrain/MeshV2/ShoreSkirtV3.asset";
        const float Cell = 0.4f, Margin = 13f, SeaY = 0f, BeachY = SeaY + 0.14f, FloorY = SeaY - 3.4f;
        static readonly string[] RockIds = { "D05_rocks_low", "D06_rocks_peak", "D07_rock_table", "D10_reef", "A09_boulder" };

        public static string Build(Transform island)
        {
            var old = island.Find("ShoreSkirtV3");
            if (old != null) Object.DestroyImmediate(old.gameObject);
            var groundT = FindDeep(island, "IslandGround");
            var surface = island.Find("GroundSurfaceV2");
            if (groundT == null || surface == null) return "shore: skipped (IslandGround or GroundSurfaceV2 missing)";
            var ground = groundT.GetComponent<Collider>();
            Physics.SyncTransforms();
            Bounds b = ground.bounds;
            float x0 = b.min.x - Margin, z0 = b.min.z - Margin;
            int nx = Mathf.CeilToInt((b.size.x + Margin * 2f) / Cell) + 1, nz = Mathf.CeilToInt((b.size.z + Margin * 2f) / Cell) + 1;

            // 1. sample the ground: gentle cells are the walkable top that stays as it is
            var landH = new float[nz, nx];
            var gentle = new bool[nz, nx];
            var hitAny = new bool[nz, nx];
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    var o = new Vector3(x0 + x * Cell, b.max.y + 20f, z0 + z * Cell);
                    if (ground.Raycast(new Ray(o, Vector3.down), out var hit, b.size.y + 60f))
                    {
                        hitAny[z, x] = true;
                        landH[z, x] = hit.point.y;
                        gentle[z, x] = hit.normal.y > 0.8f && hit.point.y > SeaY + 0.25f;
                    }
                }

            // 2. the outer region: everything not gentle that the open sea reaches
            var outer = new bool[nz, nx];
            var queue = new Queue<Vector2Int>();
            for (int x = 0; x < nx; x++) { Seed(0, x); Seed(nz - 1, x); }
            for (int z = 0; z < nz; z++) { Seed(z, 0); Seed(z, nx - 1); }
            void Seed(int z, int x) { if (!gentle[z, x] && !outer[z, x]) { outer[z, x] = true; queue.Enqueue(new Vector2Int(x, z)); } }
            while (queue.Count > 0)
            {
                var c = queue.Dequeue();
                for (int dz = -1; dz <= 1; dz++)
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int xx = c.x + dx, zz = c.y + dz;
                        if (xx < 0 || zz < 0 || xx >= nx || zz >= nz || outer[zz, xx] || gentle[zz, xx]) continue;
                        outer[zz, xx] = true;
                        queue.Enqueue(new Vector2Int(xx, zz));
                    }
            }

            // 3. distance to the gentle top (metres) and the height of the nearest top cell
            var dist = new float[nz, nx];
            var top = new float[nz, nx];
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    dist[z, x] = outer[z, x] ? 1e6f : 0f;
                    top[z, x] = landH[z, x];
                }
            for (int pass = 0; pass < 2; pass++)
            {
                int s = pass == 0 ? 1 : -1;
                for (int z = pass == 0 ? 0 : nz - 1; z >= 0 && z < nz; z += s)
                    for (int x = pass == 0 ? 0 : nx - 1; x >= 0 && x < nx; x += s)
                    {
                        if (!outer[z, x]) continue;
                        Relax(z, x, z - s, x, Cell); Relax(z, x, z, x - s, Cell);
                        Relax(z, x, z - s, x - s, Cell * 1.4142f); Relax(z, x, z - s, x + s, Cell * 1.4142f);
                    }
            }
            void Relax(int z, int x, int zz, int xx, float w)
            {
                if (zz < 0 || xx < 0 || zz >= nz || xx >= nx) return;
                float d = dist[zz, xx] + w;
                if (d < dist[z, x]) { dist[z, x] = d; top[z, x] = top[zz, xx]; }
            }

            // 4. heights: rounded shoulder → slope → beach shelf (low land only) → sea floor
            int structureMask = ~0;
            var heights = new float[nz, nx];
            var weights = new Color[nz, nx];
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    float wx = x0 + x * Cell, wz = z0 + z * Cell;
                    if (!outer[z, x])
                    {
                        // tuck just under the existing top so the seam hides beneath it
                        heights[z, x] = landH[z, x] - 0.12f;
                        weights[z, x] = new Color(1f, 0f, 0f, 0f);
                        continue;
                    }
                    float d = dist[z, x], t0 = top[z, x];
                    float n1 = Mathf.PerlinNoise(wx * 0.11f + 3.7f, wz * 0.11f + 8.1f);
                    float n2 = Mathf.PerlinNoise(wx * 0.23f + 11.3f, wz * 0.23f + 1.9f);
                    float rise = Mathf.Max(0.2f, t0 - BeachY);
                    float slopeW = Mathf.Clamp(rise * 1.05f + 2.2f, 2.8f, 10f) * Mathf.Lerp(0.72f, 1.3f, n1);
                    float beachW = t0 < 3.2f ? Mathf.Lerp(0.4f, 3.2f, Mathf.SmoothStep(0f, 1f, n2)) : Mathf.Lerp(0f, 1.2f, n2);
                    float h;
                    if (d <= slopeW)
                    {
                        float t = d / slopeW;
                        float shaped = t * t * (3f - 2f * t);
                        h = t0 - rise * shaped;
                        // lumpy bulges on the slope face, none at the shoulder or the foot
                        float relief = (Mathf.PerlinNoise(wx * 0.31f + 5.1f, wz * 0.31f + 7.7f) - 0.5f) * 1.5f
                                     + (Mathf.PerlinNoise(wx * 0.9f + 2.3f, wz * 0.9f + 4.4f) - 0.5f) * 0.45f;
                        h += relief * Mathf.Min(rise, 4f) * t * (1f - t) * 1.4f;
                        // gentle terraces on the high slopes, like old slumped ground
                        if (rise > 3f) h += (Mathf.Round(h * 0.8f) / 0.8f - h) * 0.35f * Mathf.Clamp01((n1 - 0.4f) * 3f);
                    }
                    else if (d <= slopeW + beachW) h = BeachY - (d - slopeW) / Mathf.Max(beachW, 0.01f) * 0.32f;
                    else h = Mathf.Max(FloorY, BeachY - 0.32f - (d - slopeW - beachW) * 0.55f);
                    // never rise into the pier, boats or props standing over the water
                    var from = new Vector3(wx, 40f, wz);
                    foreach (var hit in Physics.RaycastAll(from, Vector3.down, 60f, structureMask, QueryTriggerInteraction.Ignore))
                    {
                        if (hit.collider == ground || hit.collider.transform.IsChildOf(island) == false) continue;
                        string n = hit.collider.name;
                        if (n.Contains("Cliff") || n.Contains("Ground") || n.Contains("Shore") || n.Contains("Boundary")) continue;
                        if (hit.point.y > h - 0.2f && hit.point.y < h + 6f) h = Mathf.Min(h, hit.point.y - 0.55f);
                    }
                    heights[z, x] = h;
                    float sand = 1f - Mathf.Clamp01((h - BeachY) / 0.9f);
                    float grassy = Mathf.Clamp01((h - BeachY - 0.45f) / 0.9f);
                    float exposed = Mathf.Clamp01((n2 - 0.45f) * 3f) * Mathf.Clamp01(d / slopeW * 2f) * Mathf.Clamp01((h - BeachY) / 0.6f) * (rise > 2.5f ? 1f : 0.4f);
                    weights[z, x] = new Color(grassy * (1f - sand), sand * 0.55f + (1f - grassy) * (1f - sand) * 0.35f, sand * 0.45f, exposed * 0.85f);
                }

            // 5. mesh: only cells that touch the outer region; one ring of tucked top cells
            var verts = new List<Vector3>();
            var cols = new List<Color>();
            var tris = new List<int>();
            var index = new int[nz, nx];
            for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++) index[z, x] = -1;
            int V(int z, int x)
            {
                if (index[z, x] >= 0) return index[z, x];
                index[z, x] = verts.Count;
                verts.Add(new Vector3(x0 + x * Cell, heights[z, x], z0 + z * Cell));
                cols.Add(weights[z, x]);
                return index[z, x];
            }
            for (int z = 0; z < nz - 1; z++)
                for (int x = 0; x < nx - 1; x++)
                {
                    bool any = outer[z, x] || outer[z + 1, x] || outer[z, x + 1] || outer[z + 1, x + 1];
                    if (!any) continue;
                    float lo = Mathf.Max(Mathf.Max(heights[z, x], heights[z + 1, x]), Mathf.Max(heights[z, x + 1], heights[z + 1, x + 1]));
                    if (lo <= FloorY + 0.01f) continue;
                    int a = V(z, x), c1 = V(z + 1, x), c2 = V(z + 1, x + 1), c3 = V(z, x + 1);
                    tris.Add(a); tris.Add(c1); tris.Add(c2);
                    tris.Add(a); tris.Add(c2); tris.Add(c3);
                }
            var mesh = new Mesh { name = "ShoreSkirtV3", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.SetVertices(verts);
            mesh.SetColors(cols);
            mesh.SetTriangles(tris, 0);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
            if (existing != null) { existing.Clear(); EditorUtility.CopySerialized(mesh, existing); mesh = existing; }
            else AssetDatabase.CreateAsset(mesh, MeshPath);

            var go = new GameObject("ShoreSkirtV3");
            go.transform.SetParent(island, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = SkirtMaterial(surface.GetComponent<Renderer>().sharedMaterial);
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            go.AddComponent<MeshCollider>().sharedMesh = mesh;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);

            int rocks = ScatterRocks(island, go.transform, nx, nz, x0, z0, outer, dist, top, heights);
            AssetDatabase.SaveAssets();
            return $"shore: skirt {verts.Count} verts / {tris.Count / 3} tris over {nx}x{nz} cells, {rocks} boulders";
        }

        // Same textures as the top ground, but grass holds on slopes up to about 40 degrees
        // before rock shows, with broad colour variation so the hillsides are not flat green.
        static Material SkirtMaterial(Material ground)
        {
            const string path = "Assets/JieGuang/World/Terrain/MeshV2/ShoreSkirtV3.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(ground); AssetDatabase.CreateAsset(m, path); }
            else m.CopyPropertiesFromMaterial(ground);
            m.shader = ground.shader;
            // stylised hillsides: grass holds up to ~55 degrees; rock shows in the exposed patches
            m.SetFloat("_RockStart", 0.50f);
            m.SetFloat("_RockEnd", 0.66f);
            m.SetFloat("_GrassVariation", 1f);
            EditorUtility.SetDirty(m);
            ground.SetFloat("_GrassVariation", 0.7f);
            // the original top also keeps grass on its moderate inner slopes (the village hill)
            ground.SetFloat("_RockStart", 0.68f);
            ground.SetFloat("_RockEnd", 0.84f);
            EditorUtility.SetDirty(ground);
            return m;
        }

        static int ScatterRocks(Transform island, Transform parent, int nx, int nz, float x0, float z0, bool[,] outer, float[,] dist, float[,] top, float[,] heights)
        {
            var prefabs = new List<GameObject>();
            foreach (var id in RockIds)
            {
                var p = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/JieGuang/Props/" + id + ".prefab");
                if (p != null) prefabs.Add(p);
            }
            if (prefabs.Count == 0) return 0;
            var root = new GameObject("ShoreBoulders").transform;
            root.SetParent(parent, false);
            var rng = new System.Random(3);
            int count = 0;
            const int step = 9; // ~3.6 m candidate grid, jittered
            for (int z = step / 2; z < nz - step; z += step)
                for (int x = step / 2; x < nx - step; x += step)
                {
                    int jx = x + rng.Next(-3, 4), jz = z + rng.Next(-3, 4);
                    if (jx < 1 || jz < 1 || jx >= nx - 1 || jz >= nz - 1 || !outer[jz, jx]) continue;
                    float h = heights[jz, jx];
                    // on the slope face and along the waterline, not out on the sea floor
                    if (h < BeachY - 0.5f || dist[jz, jx] < 0.8f) continue;
                    if (rng.NextDouble() > 0.5) continue;
                    var prefab = prefabs[rng.Next(prefabs.Count)];
                    var r = (GameObject)PrefabUtility.InstantiatePrefab(prefab, root);
                    foreach (var c in r.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
                    // set dressing: no shadow casting, static-batched with the skirt
                    foreach (var rr in r.GetComponentsInChildren<Renderer>())
                    {
                        rr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                        var mats = rr.sharedMaterials;
                        for (int m = 0; m < mats.Length; m++) mats[m] = Darkened(mats[m]);
                        rr.sharedMaterials = mats;
                    }
                    foreach (var tr in r.GetComponentsInChildren<Transform>()) GameObjectUtility.SetStaticEditorFlags(tr.gameObject, StaticEditorFlags.BatchingStatic);
                    float s = Mathf.Lerp(0.35f, 0.9f, (float)rng.NextDouble()) * (top[jz, jx] > 4f ? 1.25f : 0.85f);
                    r.transform.localScale = prefab.transform.localScale * s;
                    var bounds = Bounds(r);
                    float yaw = (float)rng.NextDouble() * 360f;
                    // lean with the slope, then bury the downhill side so nothing floats
                    var normal = Vector3.Cross(new Vector3(0f, heights[jz + 1, jx] - heights[jz - 1, jx], 2f * Cell),
                                               new Vector3(2f * Cell, heights[jz, jx + 1] - heights[jz, jx - 1], 0f)).normalized;
                    if (normal.y < 0f) normal = -normal;
                    var lean = Quaternion.FromToRotation(Vector3.up, Vector3.Slerp(Vector3.up, normal, 0.6f));
                    r.transform.rotation = lean * Quaternion.Euler(0f, yaw, 0f) * prefab.transform.localRotation;
                    float lowest = Mathf.Min(Mathf.Min(heights[jz + 1, jx], heights[jz - 1, jx]), Mathf.Min(heights[jz, jx + 1], heights[jz, jx - 1]));
                    r.transform.position = new Vector3(x0 + jx * Cell, Mathf.Min(h, lowest + 0.1f) - bounds.size.y * 0.42f, z0 + jz * Cell);
                    count++;
                }
            return count;
        }

        // The daylight-neutral Tripo rock albedo reads as white specks under the blue night;
        // boulders use saved, darker copies of their materials (property blocks do not survive
        // in a prefab asset).
        static readonly Dictionary<Material, Material> darkened = new Dictionary<Material, Material>();
        static Material Darkened(Material source)
        {
            if (source == null) return null;
            if (darkened.TryGetValue(source, out var d) && d != null) return d;
            string path = "Assets/JieGuang/World/Terrain/MeshV2/Boulder_" + source.name.Replace(" ", "_") + ".mat";
            d = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (d == null) { d = new Material(source); AssetDatabase.CreateAsset(d, path); }
            else d.CopyPropertiesFromMaterial(source);
            if (d.HasProperty("_BaseColor")) d.SetColor("_BaseColor", source.GetColor("_BaseColor") * new Color(0.55f, 0.57f, 0.6f, 1f));
            EditorUtility.SetDirty(d);
            darkened[source] = d;
            return d;
        }

        static Bounds Bounds(GameObject g)
        {
            var rs = g.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) return new Bounds(g.transform.position, Vector3.one);
            var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }

        static Transform FindDeep(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var f = FindDeep(c, name); if (f != null) return f; }
            return null;
        }
    }
}
