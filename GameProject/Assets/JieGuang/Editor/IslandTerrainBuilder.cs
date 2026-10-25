using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // Renders the exact IslandGround surface with blended world-scale materials. TerrainData is
    // retained for placement/masks only: its heightfield cannot represent the narrow steep coast.
    // The original collider still carries the player; splat layers
    // (grass / dirt / stone path / cliff) come from the StonePaths mesh and slope, and dense
    // waving grass and wild flowers use explicit mesh chunks, kept off paths and buildings.
    // This avoids the platform-dependent Hidden/TerrainEngine grass shader path entirely.
    // Ground textures live in Assets/JieGuang/World/Terrain/ — procedural until the user's
    // GPT textures (T01 grass, T02 stone, T03 dirt, T04 cliff) are dropped in with the same names.
    public static class IslandTerrainBuilder
    {
        const string Dir = "Assets/JieGuang/World/Terrain";
        const string MeshDir = Dir + "/MeshV2";
        const int HeightRes = 257, SplatRes = 256, DetailRes = 320;
        static readonly Vector3 Origin = new Vector3(-30f, -4f, -34f);
        static readonly Vector3 Size = new Vector3(52f, 16f, 72f);

        public static void Build(Transform island)
        {
            Directory.CreateDirectory(Dir);
            Directory.CreateDirectory(MeshDir);
            var ground = island.Find("Terrain/IslandTerrain/LOD0/IslandGround") ?? FindDeep(island, "IslandGround");
            var paths = FindDeep(island, "StonePaths");
            var cliff = FindDeep(island, "CoastalCliff");
            if (ground == null || ground.GetComponent<Collider>() == null)
                throw new System.InvalidOperationException("IslandGround collider is required to build terrain.");
            foreach (var name in new[] { "IslandTerrainV2", "MeadowMeshV2", "FlagstonesV2", "ShoreRimV2", "GroundSurfaceV2" })
            {
                var old = island.Find(name);
                if (old != null) Object.DestroyImmediate(old.gameObject);
            }
            Physics.SyncTransforms();

            // temporary collider on the path ribbon for mask raycasts
            MeshCollider pathCol = null;
            if (paths != null)
            {
                pathCol = paths.gameObject.AddComponent<MeshCollider>();
                pathCol.sharedMesh = paths.GetComponent<MeshFilter>().sharedMesh;
            }
            Physics.SyncTransforms();
            var groundCol = ground.GetComponent<Collider>();

            // TerrainData owns native height/alpha/hole textures. CopySerialized from a temporary
            // TerrainData does not safely transfer that ownership: the previous pipeline saved
            // an all-grass control texture after computing a four-layer splat. Always edit the
            // persistent object through its supported setters, and create it before populating it.
            string dataPath = MeshDir + "/IslandTerrain.asset";
            PreservePreInplaceTerrain(dataPath);
            PreservePreInplaceTerrain(dataPath, "IslandTerrain-before-shore-clip.asset");
            PreservePreInplaceTerrain(dataPath, "IslandTerrain-before-surface-mesh.asset");
            var data = AssetDatabase.LoadAssetAtPath<TerrainData>(dataPath);
            if (data == null)
            {
                data = new TerrainData { name = "IslandTerrain" };
                AssetDatabase.CreateAsset(data, dataPath);
            }
            data.name = "IslandTerrain";
            data.heightmapResolution = HeightRes;
            data.size = Size;
            data.alphamapResolution = SplatRes;
            data.SetDetailResolution(DetailRes, 32);
            float[,] h = new float[HeightRes, HeightRes];
            bool[,] land = new bool[HeightRes, HeightRes];
            for (int z = 0; z < HeightRes; ++z)
                for (int x = 0; x < HeightRes; ++x)
                {
                    var wp = Origin + new Vector3(x / (HeightRes - 1f) * Size.x, 40f, z / (HeightRes - 1f) * Size.z);
                    float y = -3.6f;
                    if (groundCol.Raycast(new Ray(wp, Vector3.down), out var hit, 80f)) { y = hit.point.y - 0.03f; land[z, x] = true; }
                    h[z, x] = Mathf.Clamp01((y - Origin.y) / Size.y);
                }
            // sea floor: ease the drop just outside the coast so the terrain hides under the cliff
            var hs = (float[,])h.Clone();
            for (int z = 1; z < HeightRes - 1; ++z)
                for (int x = 1; x < HeightRes - 1; ++x)
                    if (!land[z, x])
                    {
                        float m = 0f; int n = 0;
                        for (int dz = -1; dz <= 1; ++dz) for (int dx = -1; dx <= 1; ++dx) if (land[z + dz, x + dx]) { m += h[z + dz, x + dx]; n++; }
                        if (n > 0) hs[z, x] = Mathf.Lerp(h[z, x], m / n, 0.35f);
                    }
            data.SetHeights(0, 0, hs);
            // Undo the rejected r4 coastline hole mask. The heightfield now supplies data only;
            // rendering uses the original mesh topology below, without raster borders or holes.
            var solid = new bool[data.holesResolution, data.holesResolution];
            for (int z = 0; z < data.holesResolution; z++) for (int x = 0; x < data.holesResolution; x++)
                solid[z, x] = true;
            data.SetHoles(0, 0, solid);
            data.enableHolesTextureCompression = false;

            data.terrainLayers = new[]
            {
                Layer("Grass", "T01_grass", new Color(0.24f, 0.33f, 0.19f), 3.2f, NoiseKind.Grass),
                Layer("Dirt", "T03_dirt", new Color(0.36f, 0.28f, 0.2f), 2.6f, NoiseKind.Dirt),
                Layer("Stone", "T02_stone", new Color(0.46f, 0.45f, 0.42f), 2.2f, NoiseKind.Stone),
                Layer("Cliff", "T04_cliff", new Color(0.33f, 0.32f, 0.31f), 3.5f, NoiseKind.Cliff),
            };

            // splat: path stone with a dirt fringe, cliff on steep ground, grass elsewhere
            var splat = new float[SplatRes, SplatRes, 4];
            var pathMask = new float[SplatRes, SplatRes];
            int rockyCells = 0;
            float maximumSlope = 0f;
            for (int z = 0; z < SplatRes; ++z)
                for (int x = 0; x < SplatRes; ++x)
                {
                    var wp = Origin + new Vector3((x + 0.5f) / SplatRes * Size.x, 40f, (z + 0.5f) / SplatRes * Size.z);
                    pathMask[z, x] = pathCol != null && pathCol.Raycast(new Ray(wp, Vector3.down), out _, 80f) ? 1f : 0f;
                }
            for (int z = 0; z < SplatRes; ++z)
                for (int x = 0; x < SplatRes; ++x)
                {
                    float near = 0f;
                    for (int dz = -3; dz <= 3; ++dz)
                        for (int dx = -3; dx <= 3; ++dx)
                        {
                            int zz = Mathf.Clamp(z + dz, 0, SplatRes - 1), xx = Mathf.Clamp(x + dx, 0, SplatRes - 1);
                            near = Mathf.Max(near, pathMask[zz, xx] * (1f - Mathf.Sqrt(dx * dx + dz * dz) / 4f));
                        }
                    float nx = (x + .5f) / SplatRes, nz = (z + .5f) / SplatRes;
                    int hx = Mathf.Clamp(Mathf.RoundToInt(nx * (HeightRes - 1)), 1, HeightRes - 2);
                    int hz = Mathf.Clamp(Mathf.RoundToInt(nz * (HeightRes - 1)), 1, HeightRes - 2);
                    // Derive slope directly from the sampled heights in metres. Dilation catches
                    // the narrow coast transition, where bilinear splat filtering could expose grass.
                    float degrees = HeightSlope(hs, hx, hz);
                    for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++)
                        degrees = Mathf.Max(degrees, HeightSlope(hs, hx + dx, hz + dz));
                    maximumSlope = Mathf.Max(maximumSlope, degrees);
                    float steep = Mathf.InverseLerp(22f, 36f, degrees);
                    if (!land[hz, hx]) steep = 1f;
                    float worn = Mathf.Clamp01(Mathf.PerlinNoise(nx * 23f, nz * 23f) * 1.7f - 0.82f) * 0.7f; // bare patches
                    float stone = pathMask[z, x] * (0.75f + 0.25f * Mathf.PerlinNoise(nx * 60f, nz * 60f));
                    float dirt = Mathf.Clamp01(near * 1.15f - stone * 0.55f) + worn;
                    float cliffW = steep;
                    stone *= 1f - cliffW;
                    dirt *= 1f - cliffW;
                    if (cliffW >= .8f) rockyCells++;
                    float grass = Mathf.Max(0f, 1f - stone - dirt - cliffW);
                    float sum = grass + dirt + stone + cliffW + 1e-5f;
                    splat[z, x, 0] = grass / sum; splat[z, x, 1] = dirt / sum; splat[z, x, 2] = stone / sum; splat[z, x, 3] = cliffW / sum;
                }
            data.SetAlphamaps(0, 0, splat);
            data.SetBaseMapDirty();
            EditorUtility.SetDirty(data);
            foreach (var alpha in data.alphamapTextures) EditorUtility.SetDirty(alpha);
            AssetDatabase.SaveAssetIfDirty(data);
            VerifySplat(data, splat);
            Debug.Log("[JieGuang] Splat rock cells=" + rockyCells + "/" + (SplatRes * SplatRes) + ", maxSlope=" + maximumSlope.ToString("F1"));

            // Old terrain detail data and source PNGs stay on disk as evidence. The new renderer
            // is ordinary geometry with an explicitly referenced shader/material, including in WebGL.
            data.detailPrototypes = new DetailPrototype[0];
            BuildMeadow(island, groundCol, pathCol, data, splat);
            BuildFlagstones(island, groundCol, pathCol, data);
            BuildGroundSurface(island, ground, data, splat);

            EditorUtility.SetDirty(data);
            AssetDatabase.SaveAssetIfDirty(data);
            AssetDatabase.ImportAsset(dataPath, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            data = AssetDatabase.LoadAssetAtPath<TerrainData>(dataPath);
            VerifySplat(data, splat);
            var go = Terrain.CreateTerrainGameObject(data);
            go.name = "IslandTerrainV2";
            go.transform.SetParent(island, true);
            go.transform.position = Origin;
            go.layer = 8;
            var terrain = go.GetComponent<Terrain>();
            terrain.detailObjectDistance = 0f;
            terrain.detailObjectDensity = 0f;
            terrain.heightmapPixelError = 3f;
            terrain.basemapDistance = 60f;
            terrain.drawInstanced = true;
            terrain.drawHeightmap = false; // Exact GroundSurfaceV2 mesh is the only ground renderer.
            var terrainMat = AssetDatabase.LoadAssetAtPath<Material>(MeshDir + "/Terrain.mat");
            if (terrainMat == null)
            {
                terrainMat = new Material(Shader.Find("Universal Render Pipeline/Terrain/Lit"));
                AssetDatabase.CreateAsset(terrainMat, MeshDir + "/Terrain.mat");
            }
            terrainMat.name = "Terrain";
            terrainMat.enableInstancing = true;
            terrainMat.SetFloat("_EnableInstancedPerPixelNormal", 1f);
            terrainMat.EnableKeyword("_TERRAIN_INSTANCED_PERPIXEL_NORMAL");
            terrainMat.DisableKeyword("_ALPHATEST_ON");
            EditorUtility.SetDirty(terrainMat);
            terrain.materialTemplate = terrainMat;
            go.AddComponent<JieGuang.TerrainPersistenceProbe>();
            terrain.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            Object.DestroyImmediate(go.GetComponent<TerrainCollider>()); // IslandGround's collider stays authoritative

            // the old flat ground and path ribbon stop rendering; the cliff stays as the rock face
            ground.GetComponent<Renderer>().enabled = false;
            if (paths != null) { paths.GetComponent<Renderer>().enabled = false; Object.DestroyImmediate(pathCol); }
            if (cliff != null)
            {
                var r = cliff.GetComponent<Renderer>();
                var cliffMat = CliffMaterial(data.terrainLayers[3].diffuseTexture);
                var slots = r.sharedMaterials;
                for (int i = 0; i < slots.Length; i++) slots[i] = cliffMat;
                r.sharedMaterials = slots;
                // The original flat-colour FBX did not author cliff UVs. Generate world-scale
                // side projections on a new render mesh; leave the source and collision intact.
                var filter = cliff.GetComponent<MeshFilter>();
                var cliffMesh = Object.Instantiate(filter.sharedMesh);
                cliffMesh.name = "CoastalCliffMappedV2";
                var positions = cliffMesh.vertices; var normals = cliffMesh.normals;
                var uv = new Vector2[positions.Length];
                var rockWeights = new Color[positions.Length];
                for (int i = 0; i < positions.Length; i++)
                {
                    var p = cliff.TransformPoint(positions[i]);
                    var n = cliff.TransformDirection(normals[i]);
                    uv[i] = new Vector2((Mathf.Abs(n.x) > Mathf.Abs(n.z) ? p.z : p.x) / 3.5f, p.y / 3.5f);
                    rockWeights[i] = new Color(0f, 0f, 0f, 1f);
                }
                cliffMesh.uv = uv;
                cliffMesh.colors = rockWeights; // Same world-space rock as the ground/skirt; geometry and collider stay intact.
                filter.sharedMesh = SaveGenerated(cliffMesh, MeshDir + "/CoastalCliffMapped.asset");
            }
        }

        static Transform FindDeep(Transform root, string name)
        {
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t;
            return null;
        }

        static float HeightSlope(float[,] heights, int x, int z)
        {
            x = Mathf.Clamp(x, 1, HeightRes - 2); z = Mathf.Clamp(z, 1, HeightRes - 2);
            float dx = (heights[z, x + 1] - heights[z, x - 1]) * Size.y / (2f * Size.x / (HeightRes - 1));
            float dz = (heights[z + 1, x] - heights[z - 1, x]) * Size.y / (2f * Size.z / (HeightRes - 1));
            return Mathf.Atan(Mathf.Sqrt(dx * dx + dz * dz)) * Mathf.Rad2Deg;
        }

        static T SaveGenerated<T>(T asset, string path) where T : Object
        {
            if (asset is TerrainData) throw new System.InvalidOperationException("TerrainData must be updated in place, not CopySerialized.");
            asset.name = Path.GetFileNameWithoutExtension(path);
            var old = AssetDatabase.LoadAssetAtPath<T>(path);
            if (old == null) { AssetDatabase.CreateAsset(asset, path); return asset; }
            EditorUtility.CopySerialized(asset, old);
            EditorUtility.SetDirty(old);
            Object.DestroyImmediate(asset);
            return old;
        }

        static ulong EdgeKey(int a, int b)
        {
            uint low = (uint)Mathf.Min(a, b), high = (uint)Mathf.Max(a, b);
            return ((ulong)low << 32) | high;
        }

        static void BuildGroundSurface(Transform island, Transform ground, TerrainData data, float[,,] splat)
        {
            var source = ground.GetComponent<MeshFilter>().sharedMesh;
            var positions = source.vertices; var triangles = source.triangles;
            var world = new Vector3[positions.Length];
            var canonical = new int[positions.Length];
            var weld = new Dictionary<Vector3Int, int>();
            var buffer = new MeshBuffer();
            for (int i = 0; i < positions.Length; i++)
            {
                world[i] = ground.TransformPoint(positions[i]);
                var p = world[i];
                var key = new Vector3Int(Mathf.RoundToInt(p.x * 10000f), Mathf.RoundToInt(p.y * 10000f), Mathf.RoundToInt(p.z * 10000f));
                if (!weld.TryGetValue(key, out var index)) { index = weld.Count; weld.Add(key, index); }
                canonical[i] = index;
                int x = Mathf.Clamp(Mathf.FloorToInt((p.x - Origin.x) / Size.x * SplatRes), 0, SplatRes - 1);
                int z = Mathf.Clamp(Mathf.FloorToInt((p.z - Origin.z) / Size.z * SplatRes), 0, SplatRes - 1);
                // RGB retains path/dirt blending. The shader derives rock from the exact mesh
                // normal, never from the artificial heightfield-to-seabed drop. Alpha marks skirt.
                float grass = splat[z, x, 0], dirt = splat[z, x, 1], stone = splat[z, x, 2];
                float sum = grass + dirt + stone;
                Color weights = sum > .001f ? new Color(grass / sum, dirt / sum, stone / sum, 0f) : new Color(1f, 0f, 0f, 0f);
                p.y -= .008f;
                buffer.Vertex(p, Vector3.up, Vector2.zero, Vector2.zero, weights);
            }
            // Preserve the exact triangle geometry, but orient the baked world-space surface
            // upward. The exported Ground has reversed world winding from its FBX transform;
            // a standalone identity-transform mesh must not inherit that renderer handedness.
            double signedUpArea = 0;
            for (int i = 0; i < triangles.Length; i += 3)
                signedUpArea += Vector3.Cross(world[triangles[i + 1]] - world[triangles[i]], world[triangles[i + 2]] - world[triangles[i]]).y;
            if (signedUpArea < 0)
                for (int i = 0; i < triangles.Length; i += 3)
                { int swap = triangles[i + 1]; triangles[i + 1] = triangles[i + 2]; triangles[i + 2] = swap; }
            buffer.triangles.AddRange(triangles);
            var edges = new Dictionary<ulong, int>();
            var directed = new Dictionary<ulong, Vector2Int>();
            for (int i = 0; i < triangles.Length; i += 3) for (int e = 0; e < 3; e++)
            {
                int a = triangles[i + e], b = triangles[i + (e + 1) % 3];
                ulong key = EdgeKey(canonical[a], canonical[b]);
                edges.TryGetValue(key, out var count); edges[key] = count + 1;
                directed[key] = new Vector2Int(a, b);
            }
            // The measured outer border is 0.32–2.40m; the 8.40m high slopes are INTERNAL
            // source triangles and are already present above. A small closed skirt only joins
            // the exact outer border to the submerged original cliff, with no invented high wall.
            int boundaryEdges = 0;
            var degrees = new Dictionary<int, int>();
            foreach (var pair in edges) if (pair.Value == 1)
            {
                var edge = directed[pair.Key];
                int ca = canonical[edge.x], cb = canonical[edge.y];
                degrees.TryGetValue(ca, out var da); degrees[ca] = da + 1;
                degrees.TryGetValue(cb, out var db); degrees[cb] = db + 1;
                Vector3 a = buffer.positions[edge.x], b = buffer.positions[edge.y];
                Vector3 lowA = new Vector3(a.x, -1.2f, a.z), lowB = new Vector3(b.x, -1.2f, b.z);
                int start = buffer.positions.Count;
                foreach (var p in new[] { a, lowA, b, lowB })
                    buffer.Vertex(p, Vector3.up, Vector2.zero, Vector2.zero, new Color(0f, 0f, 0f, 1f));
                buffer.triangles.AddRange(new[] { start, start + 1, start + 2, start + 2, start + 1, start + 3 });
                boundaryEdges++;
            }
            foreach (var pair in degrees) if (pair.Value != 2)
                throw new System.InvalidOperationException("Ground border is not a closed manifold loop at vertex " + pair.Key);
            var shader = Shader.Find("JieGuang/GroundSurface");
            if (shader == null) throw new System.InvalidOperationException("GroundSurface shader must be imported before rebuilding IslandV2.");
            var material = AssetDatabase.LoadAssetAtPath<Material>(MeshDir + "/GroundSurface.mat");
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, MeshDir + "/GroundSurface.mat"); }
            material.name = "GroundSurface";
            material.shader = shader;
            material.enableInstancing = true;
            material.SetTexture("_GrassMap", data.terrainLayers[0].diffuseTexture);
            material.SetTexture("_DirtMap", data.terrainLayers[1].diffuseTexture);
            material.SetTexture("_StoneMap", data.terrainLayers[2].diffuseTexture);
            material.SetTexture("_CliffMap", data.terrainLayers[3].diffuseTexture);
            EditorUtility.SetDirty(material);
            var mesh = buffer.ToMesh("GroundSurface");
            mesh.RecalculateNormals();
            var go = new GameObject("GroundSurfaceV2", typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(island, true); go.layer = 8;
            go.GetComponent<MeshFilter>().sharedMesh = SaveGenerated(mesh, MeshDir + "/GroundSurface.asset");
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            renderer.receiveShadows = true;
            Debug.Log("[JieGuang] Exact ground surface: source=" + triangles.Length / 3 + ", skirt=" + boundaryEdges * 2 + " triangles; closed border=" + boundaryEdges + " edges; original collision unchanged; Terrain drawing disabled.");
        }

        static void PreservePreInplaceTerrain(string path, string backupName = "IslandTerrain-before-inplace.asset")
        {
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../art/verification/game-v2-terrain-persistence"));
            Directory.CreateDirectory(dir);
            string backup = Path.Combine(dir, backupName);
            if (File.Exists(path) && !File.Exists(backup))
            {
                File.Copy(path, backup);
                if (File.Exists(path + ".meta")) File.Copy(path + ".meta", backup + ".meta");
            }
        }

        static void VerifySplat(TerrainData data, float[,,] expected)
        {
            var actual = data.GetAlphamaps(0, 0, data.alphamapWidth, data.alphamapHeight);
            double[] intended = new double[4], retained = new double[4];
            float maximumDifference = 0f;
            for (int z = 0; z < SplatRes; z++) for (int x = 0; x < SplatRes; x++) for (int layer = 0; layer < 4; layer++)
            {
                intended[layer] += expected[z, x, layer];
                retained[layer] += actual[z, x, layer];
                maximumDifference = Mathf.Max(maximumDifference, Mathf.Abs(expected[z, x, layer] - actual[z, x, layer]));
            }
            var text = new System.Text.StringBuilder("Terrain data is edited in place; no CopySerialized.\n");
            text.AppendLine("asset=" + AssetDatabase.GetAssetPath(data));
            text.AppendLine("alphaTextures=" + data.alphamapTextureCount + "; maxSampleDifference=" + maximumDifference.ToString("F6"));
            for (int layer = 0; layer < 4; layer++) text.AppendLine("layer" + layer + ": intended=" + intended[layer].ToString("F3") + "; retained=" + retained[layer].ToString("F3"));
            foreach (var alpha in data.alphamapTextures)
                text.AppendLine("alpha=" + alpha.name + "; persistent=" + EditorUtility.IsPersistent(alpha) + "; path=" + AssetDatabase.GetAssetPath(alpha));
            string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../art/verification/game-v2-terrain-persistence"));
            Directory.CreateDirectory(dir);
            File.WriteAllText(Path.Combine(dir, "builder-splat-verification.txt"), text.ToString());
            if (maximumDifference > .02f)
                throw new System.InvalidOperationException("Terrain splat mismatch after save: " + maximumDifference + ". See builder-splat-verification.txt");
            Debug.Log("[JieGuang] Persistent splat verified; maximum quantization difference=" + maximumDifference.ToString("F6"));
        }

        sealed class MeshBuffer
        {
            public readonly List<Vector3> positions = new List<Vector3>();
            public readonly List<Vector3> normals = new List<Vector3>();
            public readonly List<Vector2> uv = new List<Vector2>();
            public readonly List<Vector2> wind = new List<Vector2>();
            public readonly List<Color> colors = new List<Color>();
            public readonly List<int> triangles = new List<int>();
            public void Vertex(Vector3 p, Vector3 n, Vector2 tex, Vector2 motion, Color c)
            { positions.Add(p); normals.Add(n); uv.Add(tex); wind.Add(motion); colors.Add(c); }
            public Mesh ToMesh(string name)
            {
                var mesh = new Mesh { name = name };
                if (positions.Count > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                mesh.SetVertices(positions); mesh.SetNormals(normals); mesh.SetUVs(0, uv);
                mesh.SetUVs(1, wind); mesh.SetColors(colors); mesh.SetTriangles(triangles, 0);
                mesh.RecalculateBounds();
                // Include shader sway in culling bounds.
                var bounds = mesh.bounds; bounds.Expand(0.3f); mesh.bounds = bounds;
                return mesh;
            }
        }

        static Texture2D ReadCard(string name, System.Func<Texture2D> fallback)
        {
            string p = Dir + "/" + name + ".png";
            if (!File.Exists(p)) return fallback();
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            t.LoadImage(File.ReadAllBytes(p));
            return t;
        }

        static void BuildMeadow(Transform island, Collider ground, Collider path, TerrainData data, float[,,] splat)
        {
            // Existing five procedural source cards are retained. Authored replacements can use
            // these single-tuft names after their V01/V02 atlas cells have been explicitly cropped.
            // Whole multi-object V atlases must not silently be used as one giant plant.
            var cards = new[]
            {
                ReadCard("GrassBlades", () => Blades(new Color(.42f,.58f,.3f), new Color(.62f,.7f,.36f), 9, 11)),
                ReadCard("GrassTall", () => Blades(new Color(.5f,.6f,.32f), new Color(.72f,.7f,.42f), 6, 23)),
                ReadCard("Daisies", () => Flowers(new Color(.96f,.95f,.88f), new Color(.95f,.78f,.25f), 31)),
                ReadCard("Lavender", () => Spikes(new Color(.62f,.52f,.86f), 37)),
                ReadCard("Buttercups", () => Flowers(new Color(.98f,.84f,.3f), new Color(.9f,.6f,.15f), 41)),
            };
            var atlas = new Texture2D(1024, 1024, TextureFormat.RGBA32, true);
            Rect[] rects = atlas.PackTextures(cards, 8, 2048, false);
            string atlasPath = MeshDir + "/MeadowAtlas.png";
            File.WriteAllBytes(atlasPath, atlas.EncodeToPNG());
            foreach (var card in cards) Object.DestroyImmediate(card);
            Object.DestroyImmediate(atlas);
            AssetDatabase.ImportAsset(atlasPath);
            var importer = (TextureImporter)AssetImporter.GetAtPath(atlasPath);
            importer.alphaIsTransparency = true;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.mipmapEnabled = true;
            importer.mipMapsPreserveCoverage = true;
            importer.alphaTestReferenceValue = .36f;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.anisoLevel = 4;
            importer.SaveAndReimport();
            var shader = Shader.Find("JieGuang/MeadowCards");
            if (shader == null) throw new System.InvalidOperationException("MeadowCards shader has not imported.");
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MeshDir + "/Meadow.mat");
            if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, MeshDir + "/Meadow.mat"); }
            mat.shader = shader;
            mat.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(atlasPath));
            mat.SetFloat("_Cutoff", .36f);
            mat.SetFloat("_Wind", .038f);
            mat.SetFloat("_Saturation", .78f);
            mat.SetFloat("_FoliageDistance", 48f);
            mat.enableInstancing = true;
            EditorUtility.SetDirty(mat);

            const float spacing = .255f, chunkSize = 6f;
            var dense = new Dictionary<Vector2Int, MeshBuffer>();
            var sparse = new Dictionary<Vector2Int, MeshBuffer>();
            var rng = new System.Random(612);
            var hits = new RaycastHit[64];
            int tuftCount = 0, flowerCount = 0;
            int xCount = Mathf.CeilToInt(Size.x / spacing), zCount = Mathf.CeilToInt(Size.z / spacing);
            for (int z = 0; z < zCount; z++) for (int x = 0; x < xCount; x++)
            {
                float px = Origin.x + (x + .15f + .7f * (float)rng.NextDouble()) * spacing;
                float pz = Origin.z + (z + .15f + .7f * (float)rng.NextDouble()) * spacing;
                float nx = (px - Origin.x) / Size.x, nz = (pz - Origin.z) / Size.z;
                int sx = Mathf.Clamp((int)(nx * SplatRes), 0, SplatRes - 1), sz = Mathf.Clamp((int)(nz * SplatRes), 0, SplatRes - 1);
                float grass = splat[sz, sx, 0];
                if (grass < .60f || data.GetSteepness(nx, nz) > 38f) continue;
                // Sparse ground cover between denser, irregular metre-scale clumps.
                float patch = Mathf.PerlinNoise(px * .48f + 14f, pz * .48f + 9f);
                float coverage = Mathf.Lerp(.35f, .95f, Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(.28f, .72f, patch)));
                if (rng.NextDouble() > coverage) continue;
                var ray = new Ray(new Vector3(px, 40f, pz), Vector3.down);
                if (!ground.Raycast(ray, out var gh, 80f) || gh.point.y < -.35f) continue;
                if (path != null && path.Raycast(ray, out _, 80f)) continue;
                // Only colliders belonging to the island being built count: an open main scene
                // often contains a previous IslandV2 at exactly the same coordinates.
                bool blocked = false;
                int hitCount = Physics.RaycastNonAlloc(ray, hits, 80f, ~0, QueryTriggerInteraction.Ignore);
                for (int hitIndex = 0; hitIndex < hitCount; hitIndex++)
                {
                    var other = hits[hitIndex];
                    if (other.collider != ground && other.collider != path && other.transform.IsChildOf(island)
                        && other.point.y > gh.point.y + .12f) { blocked = true; break; }
                }
                if (blocked) continue;
                float drift = Mathf.PerlinNoise(px * .22f + 3f, pz * .22f + 8f);
                int species = 0;
                double dice = rng.NextDouble();
                if (drift > .54f && dice < .06) species = 2;
                else if (drift < .43f && dice < .045) species = 3;
                else if (dice < .07) species = 4;
                else if (dice > .91) species = 1;
                float height = species == 1 ? .29f + (float)rng.NextDouble() * .06f : .18f + (float)rng.NextDouble() * .12f;
                if (species >= 2) height = .18f + (float)rng.NextDouble() * .09f;
                float width = species < 2 ? .28f + (float)rng.NextDouble() * .12f : .16f + (float)rng.NextDouble() * .08f;
                float yaw = (float)rng.NextDouble() * Mathf.PI;
                float tone = .76f + (float)rng.NextDouble() * .18f;
                var tint = new Color(tone * .98f, tone, tone * .84f, 1f);
                float y = Mathf.Max(gh.point.y, Origin.y + data.GetInterpolatedHeight(nx, nz)) - .028f;
                var centre = new Vector3(px, y, pz);
                var key = new Vector2Int(Mathf.FloorToInt((px - Origin.x) / chunkSize), Mathf.FloorToInt((pz - Origin.z) / chunkSize));
                if (!dense.ContainsKey(key)) { dense.Add(key, new MeshBuffer()); sparse.Add(key, new MeshBuffer()); }
                AddTuft(dense[key], centre, gh.normal, width, height, yaw, rects[species], tint);
                if ((tuftCount & 1) == 0 || species >= 2) AddTuft(sparse[key], centre, gh.normal, width, height, yaw, rects[species], tint);
                tuftCount++;
                if (species >= 2) flowerCount++;
            }
            var root = new GameObject("MeadowMeshV2");
            root.transform.SetParent(island, false);
            var filters = new List<MeshFilter>(); var high = new List<Mesh>(); var low = new List<Mesh>();
            foreach (var pair in dense)
            {
                string id = "Meadow_" + pair.Key.x.ToString("D2") + "_" + pair.Key.y.ToString("D2");
                var highMesh = SaveGenerated(pair.Value.ToMesh(id), MeshDir + "/" + id + ".asset");
                var lowMesh = SaveGenerated(sparse[pair.Key].ToMesh(id + "_Low"), MeshDir + "/" + id + "_Low.asset");
                var go = new GameObject(id, typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(root.transform, true); // vertices are sampled in world space
                go.layer = 8;
                var filter = go.GetComponent<MeshFilter>(); filter.sharedMesh = highMesh;
                var renderer = go.GetComponent<MeshRenderer>(); renderer.sharedMaterial = mat;
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                renderer.receiveShadows = true;
                filters.Add(filter); high.Add(highMesh); low.Add(lowMesh);
            }
            var budget = root.AddComponent<JieGuang.IslandFoliageBudget>();
            budget.Chunks = filters.ToArray(); budget.FullMeshes = high.ToArray(); budget.ReducedMeshes = low.ToArray();
            File.WriteAllText(MeshDir + "/Meadow-build-report.txt", "source=retained procedural cards; no new user V textures found/imported\nrevision=balanced-clustered-meadow\nseed=612\ntufts=" + tuftCount + "\nflowerTufts=" + flowerCount + "\nchunks=" + filters.Count + "\ngrassHeight=.18-.35; flowerHeight=.18-.27; flowerFraction=.07; saturation=.78\nwindowsDistance=48; webDistance=32; fullDensityDistance=18/12\nordinary MeshRenderer + alpha cutout; no Terrain Grass dependency\n");
            Debug.Log("[JieGuang] Meadow mesh: " + tuftCount + " tufts, " + flowerCount + " flowers, " + filters.Count + " chunks");
        }

        static void AddTuft(MeshBuffer mesh, Vector3 centre, Vector3 groundNormal, float width, float height, float yaw, Rect rect, Color color)
        {
            for (int plane = 0; plane < 2; plane++)
            {
                float angle = yaw + plane * Mathf.PI * .5f;
                var right = new Vector3(Mathf.Cos(angle), 0f, Mathf.Sin(angle)) * width * .5f;
                right.y = -(groundNormal.x * right.x + groundNormal.z * right.z) / Mathf.Max(.35f, groundNormal.y);
                int b = mesh.positions.Count;
                var normal = new Vector3(Mathf.Sin(angle) * .22f, .97f, Mathf.Cos(angle) * .22f).normalized;
                mesh.Vertex(centre - right, normal, new Vector2(rect.xMin, rect.yMin), Vector2.zero, color);
                mesh.Vertex(centre + right, normal, new Vector2(rect.xMax, rect.yMin), Vector2.zero, color);
                mesh.Vertex(centre + right + Vector3.up * height, normal, new Vector2(rect.xMax, rect.yMax), Vector2.one, color);
                mesh.Vertex(centre - right + Vector3.up * height, normal, new Vector2(rect.xMin, rect.yMax), Vector2.one, color);
                mesh.triangles.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
        }

        static void BuildFlagstones(Transform island, Collider ground, Collider path, TerrainData data)
        {
            if (path == null) return;
            var buffer = new MeshBuffer();
            var rng = new System.Random(8672);
            int count = 0;
            const float step = .62f;
            for (int z = 0; z < Mathf.CeilToInt(Size.z / step); z++) for (int x = 0; x < Mathf.CeilToInt(Size.x / step); x++)
            {
                float px = Origin.x + (x + .5f + (z % 2) * .5f) * step;
                float pz = Origin.z + (z + .5f) * step;
                var ray = new Ray(new Vector3(px, 40f, pz), Vector3.down);
                if (!path.Raycast(ray, out _, 80f) || !ground.Raycast(ray, out var gh, 80f)) continue;
                if (gh.point.y < -.2f) continue;
                float radiusX = .25f + .035f * (float)rng.NextDouble();
                float radiusZ = .24f + .04f * (float)rng.NextDouble();
                float yaw = ((float)rng.NextDouble() - .5f) * .3f;
                Vector3[] rim = new Vector3[8];
                bool valid = true;
                for (int i = 0; i < 8; i++)
                {
                    float angle = Mathf.PI * .25f * i + yaw;
                    var p = new Vector3(px + Mathf.Cos(angle) * radiusX, 40f, pz + Mathf.Sin(angle) * radiusZ);
                    var r = new Ray(p, Vector3.down);
                    if (!ground.Raycast(r, out var edge, 80f) || !path.Raycast(r, out _, 80f)) { valid = false; break; }
                    float nx = (p.x - Origin.x) / Size.x, nz = (p.z - Origin.z) / Size.z;
                    p.y = Mathf.Max(edge.point.y, Origin.y + data.GetInterpolatedHeight(nx, nz)) + .025f;
                    rim[i] = p;
                }
                if (!valid) continue;
                var centre = new Vector3(px, 0, pz);
                foreach (var p in rim) centre.y += p.y / 8f;
                centre.y += .012f;
                // Flat stone tops with chamfered, darker rims; 2.5-4 cm above the collision surface.
                float grey = .83f + (float)rng.NextDouble() * .17f;
                var color = new Color(grey, grey * .98f, grey * .94f, 1f);
                int b = buffer.positions.Count;
                buffer.Vertex(centre, gh.normal, new Vector2(px / 2.2f, pz / 2.2f), Vector2.zero, color);
                for (int i = 0; i < 8; i++) buffer.Vertex(rim[i], gh.normal, new Vector2(rim[i].x / 2.2f, rim[i].z / 2.2f), Vector2.zero, color);
                for (int i = 0; i < 8; i++) buffer.triangles.AddRange(new[] { b, b + 1 + (i + 1) % 8, b + 1 + i });
                for (int i = 0; i < 8; i++)
                {
                    var a = rim[i]; var c = rim[(i + 1) % 8];
                    int e = buffer.positions.Count;
                    var n = Vector3.Cross(c - a, Vector3.down).normalized;
                    buffer.Vertex(a, n, new Vector2(a.x / 2.2f, a.z / 2.2f), Vector2.zero, color * .74f);
                    buffer.Vertex(c, n, new Vector2(c.x / 2.2f, c.z / 2.2f), Vector2.zero, color * .74f);
                    buffer.Vertex(c - Vector3.up * .045f, n, new Vector2(c.x / 2.2f, c.z / 2.2f), Vector2.zero, color * .62f);
                    buffer.Vertex(a - Vector3.up * .045f, n, new Vector2(a.x / 2.2f, a.z / 2.2f), Vector2.zero, color * .62f);
                    buffer.triangles.AddRange(new[] { e, e + 1, e + 2, e, e + 2, e + 3 });
                }
                count++;
            }
            var mat = AssetDatabase.LoadAssetAtPath<Material>(MeshDir + "/Flagstones.mat");
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, MeshDir + "/Flagstones.mat"); }
            mat.SetTexture("_BaseMap", data.terrainLayers[2].diffuseTexture);
            mat.SetColor("_BaseColor", new Color(1.30f, 1.35f, 1.48f, 1f));
            mat.SetFloat("_Smoothness", .17f);
            EditorUtility.SetDirty(mat);
            var mesh = SaveGenerated(buffer.ToMesh("FlagstonesV2"), MeshDir + "/Flagstones.asset");
            var go = new GameObject("FlagstonesV2", typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(island, true); go.layer = 8;
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            go.GetComponent<MeshRenderer>().sharedMaterial = mat;
            Debug.Log("[JieGuang] Terrain-conforming flagstones: " + count);
        }

        static Material CliffMaterial(Texture2D tex)
        {
            string p = MeshDir + "/Cliff.mat";
            var shader = Shader.Find("JieGuang/GroundSurface");
            if (shader == null) throw new System.InvalidOperationException("GroundSurface shader is required for continuous coastal rock.");
            var m = AssetDatabase.LoadAssetAtPath<Material>(p);
            if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, p); }
            m.name = "Cliff";
            m.shader = shader;
            m.enableInstancing = true;
            m.SetTexture("_CliffMap", tex);
            // Vertex alpha is one everywhere on CoastalCliffMapped, so only rock contributes.
            // Bind the existing texture in every sampled slot for consistent platform imports.
            m.SetTexture("_GrassMap", tex);
            m.SetTexture("_DirtMap", tex);
            m.SetTexture("_StoneMap", tex);
            EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------ textures
        enum NoiseKind { Grass, Dirt, Stone, Cliff }

        static TerrainLayer Layer(string name, string userFile, Color tint, float tile, NoiseKind kind)
        {
            string png = Dir + "/" + userFile + ".png";
            if (!File.Exists(png)) File.WriteAllBytes(png, MakeTexture(kind, tint).EncodeToPNG());
            AssetDatabase.ImportAsset(png);
            var ti = (TextureImporter)AssetImporter.GetAtPath(png);
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.maxTextureSize = 2048;
            ti.anisoLevel = 8;
            ti.mipmapEnabled = true;
            ti.SaveAndReimport();
            var layer = new TerrainLayer
            {
                diffuseTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(png),
                tileSize = new Vector2(tile, tile),
                smoothness = kind == NoiseKind.Stone ? 0.18f : 0.05f,
            };
            if (kind == NoiseKind.Grass) layer.diffuseRemapMax = new Vector4(1.18f, 1.05f, 1.14f, 1f);
            if (kind == NoiseKind.Dirt) layer.diffuseRemapMax = new Vector4(1.05f, 1.08f, 1.12f, 1f);
            // Optional authored normal map; never infer a supplied albedo is already a normal.
            string normalPath = Dir + "/" + userFile + "_normal.png";
            if (File.Exists(normalPath))
            {
                AssetDatabase.ImportAsset(normalPath);
                var normalImporter = (TextureImporter)AssetImporter.GetAtPath(normalPath);
                normalImporter.textureType = TextureImporterType.NormalMap;
                normalImporter.wrapMode = TextureWrapMode.Repeat;
                normalImporter.SaveAndReimport();
                layer.normalMapTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
                layer.normalScale = 0.4f;
            }
            return SaveGenerated(layer, MeshDir + "/" + name + ".terrainlayer");
        }

        // Tileable fractal noise: sample a 4D torus via two Perlin planes.
        static float Tile(float u, float v, float freq, float seed)
        {
            float a = u * Mathf.PI * 2f, b = v * Mathf.PI * 2f, r = freq / (Mathf.PI * 2f);
            float n1 = Mathf.PerlinNoise(Mathf.Cos(a) * r + seed, Mathf.Sin(a) * r + seed * 0.7f);
            float n2 = Mathf.PerlinNoise(Mathf.Cos(b) * r - seed * 0.3f, Mathf.Sin(b) * r + seed * 1.3f);
            return (n1 + n2) * 0.5f;
        }

        static Texture2D MakeTexture(NoiseKind kind, Color tint)
        {
            const int n = 512;
            var t = new Texture2D(n, n, TextureFormat.RGB24, true);
            var px = new Color[n * n];
            for (int y = 0; y < n; ++y)
                for (int x = 0; x < n; ++x)
                {
                    float u = (float)x / n, v = (float)y / n;
                    float f = Tile(u, v, 6f, 1f) * 0.5f + Tile(u, v, 20f, 5f) * 0.3f + Tile(u, v, 70f, 9f) * 0.2f;
                    Color c = tint * Mathf.Lerp(0.72f, 1.25f, f);
                    switch (kind)
                    {
                        case NoiseKind.Grass:
                            c = Color.Lerp(c, new Color(0.45f, 0.42f, 0.22f), Mathf.Clamp01(Tile(u, v, 9f, 3f) * 2f - 1.1f));
                            break;
                        case NoiseKind.Stone:
                            // flagstones: voronoi-ish cells via quantised noise, dark joints
                            float cell = Tile(u, v, 14f, 2f);
                            float joint = Mathf.Abs(Mathf.Repeat(cell * 7f, 1f) - 0.5f);
                            c *= Mathf.Lerp(0.55f, 1.05f, Mathf.SmoothStep(0.02f, 0.12f, joint));
                            c = Color.Lerp(c, new Color(0.3f, 0.36f, 0.24f), Mathf.Clamp01((0.06f - joint) * 10f) * 0.5f);
                            break;
                        case NoiseKind.Dirt:
                            c *= 0.9f + 0.2f * Mathf.Clamp01(Tile(u, v, 120f, 7f) * 3f - 1.6f);
                            break;
                        case NoiseKind.Cliff:
                            c *= 0.75f + 0.35f * Mathf.Repeat(v * 9f + f * 2f, 1f);
                            break;
                    }
                    c.a = 1f;
                    px[y * n + x] = c;
                }
            t.SetPixels(px);
            t.Apply();
            return t;
        }

        // ------------------------------------------------------------------ detail sprites
        static Texture2D Canvas(int w, int h) { var t = new Texture2D(w, h, TextureFormat.RGBA32, false); var c = new Color[w * h]; t.SetPixels(c); return t; }

        static void Stroke(Texture2D t, Vector2 a, Vector2 b, float w0, float w1, Color c0, Color c1)
        {
            int steps = Mathf.CeilToInt(Vector2.Distance(a, b) * 1.5f);
            for (int i = 0; i <= steps; ++i)
            {
                float k = i / (float)steps;
                Vector2 p = Vector2.Lerp(a, b, k);
                float w = Mathf.Lerp(w0, w1, k);
                Color c = Color.Lerp(c0, c1, k);
                for (int dy = -(int)w - 1; dy <= w + 1; ++dy)
                    for (int dx = -(int)w - 1; dx <= w + 1; ++dx)
                    {
                        int x = (int)p.x + dx, y = (int)p.y + dy;
                        if (x < 0 || y < 0 || x >= t.width || y >= t.height) continue;
                        float d = Mathf.Sqrt(dx * dx + dy * dy);
                        float aa = Mathf.Clamp01(w + 0.5f - d);
                        if (aa <= 0f) continue;
                        var old = t.GetPixel(x, y);
                        t.SetPixel(x, y, Color.Lerp(old, new Color(c.r, c.g, c.b, 1f), aa));
                    }
            }
        }

        static Texture2D Blades(Color baseC, Color tipC, int count, int seed)
        {
            var t = Canvas(128, 128);
            var r = new System.Random(seed);
            for (int i = 0; i < count; ++i)
            {
                float x0 = 20f + (float)r.NextDouble() * 88f;
                float lean = ((float)r.NextDouble() - 0.5f) * 50f;
                float hgt = 70f + (float)r.NextDouble() * 55f;
                var mid = new Vector2(x0 + lean * 0.35f, hgt * 0.55f);
                var top = new Vector2(x0 + lean, Mathf.Min(126f, hgt));
                Stroke(t, new Vector2(x0, 0f), mid, 3.2f, 2.2f, baseC * 0.7f, Color.Lerp(baseC, tipC, 0.5f));
                Stroke(t, mid, top, 2.2f, 0.4f, Color.Lerp(baseC, tipC, 0.5f), tipC);
            }
            t.Apply();
            return t;
        }

        static Texture2D Flowers(Color petal, Color heart, int seed)
        {
            var t = Canvas(128, 128);
            var r = new System.Random(seed);
            var stem = new Color(0.36f, 0.52f, 0.26f);
            for (int i = 0; i < 4; ++i)
            {
                float x = 22f + (float)r.NextDouble() * 84f, h = 55f + (float)r.NextDouble() * 55f;
                Stroke(t, new Vector2(x, 0f), new Vector2(x + ((float)r.NextDouble() - 0.5f) * 14f, h), 1.6f, 1.2f, stem * 0.8f, stem);
                var c = new Vector2(x, h);
                for (int p = 0; p < 7; ++p)
                {
                    float a = p * Mathf.PI * 2f / 7f;
                    Stroke(t, c, c + new Vector2(Mathf.Cos(a), Mathf.Sin(a) * 0.7f) * 9f, 3.2f, 2.4f, petal, petal);
                }
                Stroke(t, c, c + Vector2.one * 0.5f, 3.4f, 3.4f, heart, heart);
            }
            t.Apply();
            return t;
        }

        static Texture2D Spikes(Color bloom, int seed)
        {
            var t = Canvas(128, 128);
            var r = new System.Random(seed);
            var stem = new Color(0.4f, 0.5f, 0.32f);
            for (int i = 0; i < 6; ++i)
            {
                float x = 18f + (float)r.NextDouble() * 92f, h = 70f + (float)r.NextDouble() * 50f;
                float lean = ((float)r.NextDouble() - 0.5f) * 16f;
                Stroke(t, new Vector2(x, 0f), new Vector2(x + lean, h), 1.4f, 1f, stem * 0.8f, stem);
                for (int k = 0; k < 9; ++k)
                {
                    float y = h - k * 3.6f;
                    float xx = x + lean * (y / h);
                    Stroke(t, new Vector2(xx - 2.2f, y), new Vector2(xx + 2.2f, y + 1.2f), 2f, 2f, bloom * (0.85f + 0.03f * k), bloom);
                }
            }
            t.Apply();
            return t;
        }
    }
}
