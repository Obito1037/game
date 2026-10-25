#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    /// <summary>
    /// Explicit editor entry point; no InitializeOnLoad, Menu auto-run or scene-wide search.
    /// Adds/replaces only the owned Meadow_EnvV2 child on the supplied scene/prefab-content instance.
    /// Uses original procedural geometry, no textures, runtime scripts, compute or geometry shaders.
    /// Caller owns prefab/scene saving and Editor coordination. Never saves another asset or scene.
    /// </summary>
    public static class EnvV2MeadowBuilder
    {
        public const string OwnedName = "Meadow_EnvV2";
        public const string ShaderName = "JieGuang/Environment/Meadow";
        const string MarkerName = "__OwnedBy_EnvV2MeadowBuilder_v1";
        const string AllowedRoot = "Assets/JieGuang/Environment/";

        [Serializable]
        public sealed class Settings
        {
            public int seed = 20261022;
            public int maxTrianglesIncludingLod = 70000;
            public int maxGrassClumps = 3300;
            public int maxFlowers = 100;
            public int maxFerns = 40;
            public float candidateSpacing = .29f;
            public float grassClumpsPerSquareMetre = 7.5f;
            public float chunkSize = 6f;
            public float minimumGroundY = .35f;
            public float maximumSlopeDegrees = 38f;
            public float pathClearance = .09f;
            public float solidClearance = .16f;
            public float anchorClearance = .48f;
            public float windAmplitude = .045f;
            public float lod1DistanceAtReferenceFov = 12f;
            public float cullDistanceAtReferenceFov = 40f;
            public float referenceVerticalFov = 50f;
            public float shaderFadeStart = 28f;
            public float shaderFadeEnd = 36f;
            public bool castGrassShadows = false;
        }

        [Serializable] public sealed class Check { public string name; public bool passed; public string detail; }
        [Serializable] public sealed class Placement
        {
            public string kind;
            public Vector3 position;
            public Vector3 normal;
            public float pathDistance;
            public float seed;
        }
        [Serializable]
        public sealed class BuildReport
        {
            public string status;
            public string generatedUtc;
            public string unityVersion;
            public string outputPath;
            public string ownership = OwnedName + "/" + MarkerName;
            public Settings settings;
            public int grassClumps, flowers, ferns, chunks, renderers;
            public int lod0Triangles, lod1Triangles, totalTriangles;
            public int candidatePoints, groundQueries, groundMisses, steepRejected, pathRejected, solidRejected, anchorRejected;
            public int pathTriangles, ownGroundColliders, ownSolidColliders;
            public double buildSeconds;
            public string lodNote = "LODGroup distances are estimates at referenceVerticalFov; shader thinning uses actual camera XZ distance. No measured FPS claim.";
            public List<Check> checks = new List<Check>();
            public List<Placement> placements = new List<Placement>();
            public List<string> assets = new List<string>();
            public List<string> warnings = new List<string>();
        }

        struct Candidate
        {
            public Vector3 position, normal;
            public float seed, order, pathDistance, obstacleDistance;
            public int cellX, cellZ;
        }
        struct Disc { public Vector3 center; public float radius; }
        struct Triangle
        {
            public Vector3 a, b, c;
            public Bounds bounds;
        }
        sealed class Mask
        {
            public Collider[] ground;
            public Bounds[] solids;
            public Bounds[] decks;
            public List<Disc> discs = new List<Disc>();
            public List<Triangle> paths = new List<Triangle>();
            public Dictionary<Vector2Int,List<int>> pathCells = new Dictionary<Vector2Int,List<int>>();
            public Bounds bounds;
            public float rayTop, rayLength;
        }
        sealed class Tile
        {
            public Vector3 origin;
            public MeshData high = new MeshData();
            public MeshData low = new MeshData();
        }
        sealed class ForeignState
        {
            public Transform transform, parent;
            public string name;
            public int layer;
            public Vector3 position, scale;
            public Quaternion rotation;
        }

        sealed class MeshData
        {
            public readonly List<Vector3> vertices = new List<Vector3>();
            public readonly List<Vector3> normals = new List<Vector3>();
            public readonly List<Color> colors = new List<Color>();
            public readonly List<Vector4> uv = new List<Vector4>();
            public readonly List<Vector4> roots = new List<Vector4>();
            public readonly List<int> triangles = new List<int>();
            public int TriangleCount => triangles.Count / 3;
            public int Add(Vector3 p, Vector3 normal, Color tint, float side, float height01, float species, float seed, Vector3 root, float plantHeight)
            {
                int index = vertices.Count;
                vertices.Add(p); normals.Add(normal.normalized); colors.Add(tint);
                // Derive the shared wind weight from physical height: leaflets/petals and
                // stems meeting at the same point must stay attached even on sloping ground.
                float anchoredHeight = Mathf.Clamp01((p.y-root.y)/Mathf.Max(plantHeight,.08f));
                uv.Add(new Vector4(side, anchoredHeight, species, seed));
                roots.Add(new Vector4(root.x, root.y, root.z, plantHeight));
                return index;
            }
            public void Tri(int a, int b, int c) { triangles.Add(a); triangles.Add(b); triangles.Add(c); }
            public void Append(MeshData other)
            {
                int offset = vertices.Count;
                vertices.AddRange(other.vertices); normals.AddRange(other.normals); colors.AddRange(other.colors);
                uv.AddRange(other.uv); roots.AddRange(other.roots);
                foreach (int index in other.triangles) triangles.Add(index + offset);
            }
            public Mesh ToMesh(string name, float windMargin)
            {
                var mesh = new Mesh { name = name, indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                mesh.SetVertices(vertices); mesh.SetNormals(normals); mesh.SetColors(colors);
                mesh.SetUVs(0,uv); mesh.SetUVs(1,roots); mesh.SetTriangles(triangles,0);
                mesh.RecalculateBounds();
                Bounds bounds = mesh.bounds; bounds.Expand(new Vector3(windMargin*2,.04f,windMargin*2)); mesh.bounds = bounds;
                return mesh;
            }
        }

        /// <param name="islandRoot">Live instance or PrefabUtility.LoadPrefabContents result; never a persistent asset.</param>
        /// <param name="outputAssetFolder">Owned output inside Assets/JieGuang/Environment, e.g. .../Generated/MeadowV2.</param>
        /// <remarks>Does not call SaveAssets, SaveScene, SaveAsPrefabAsset, Play, or refresh the project.</remarks>
        public static BuildReport Build(GameObject islandRoot, string outputAssetFolder, Settings settings = null)
        {
            Settings config = settings ?? new Settings();
            ValidateArguments(islandRoot, outputAssetFolder, config);
            Shader shader = Shader.Find(ShaderName);
            if (shader == null) throw new InvalidOperationException("Import the owned Meadow.shader before calling Build.");
            if (!shader.isSupported) throw new InvalidOperationException("Meadow shader is unsupported on the current renderer; no scene objects changed.");
            Transform oldRoot = FindDirectChild(islandRoot.transform,OwnedName);
            if (oldRoot != null) AssertOwned(oldRoot);
            ForeignState[] foreign = CaptureForeign(islandRoot.transform, oldRoot);
            var clock = Stopwatch.StartNew();
            var report = new BuildReport {
                settings = config, generatedUtc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion,
                status = "generating"
            };
            Physics.SyncTransforms();
            Mask mask = GatherMask(islandRoot.transform, oldRoot, config, report);
            List<Candidate> candidates = MakeCandidates(mask, config, report);
            // Global stable random ordering prevents the first rows of the grid taking all the budget.
            candidates.Sort((a,b) => { int order=a.order.CompareTo(b.order); if(order!=0)return order; order=a.cellX.CompareTo(b.cellX); return order!=0?order:a.cellZ.CompareTo(b.cellZ); });
            var tiles = new Dictionary<Vector2Int,Tile>();
            foreach (Candidate candidate in candidates)
            {
                string kind = ChooseKind(candidate, config, report);
                if (kind == null) continue;
                Vector2Int key = new Vector2Int(Mathf.FloorToInt(candidate.position.x/config.chunkSize),Mathf.FloorToInt(candidate.position.z/config.chunkSize));
                Vector3 origin = new Vector3((key.x+.5f)*config.chunkSize,0,(key.y+.5f)*config.chunkSize);
                var high = new MeshData(); var low = new MeshData();
                if (kind == "fern") AddFern(high,low,candidate,origin);
                else if (kind == "flower") AddFlower(high,low,candidate,origin);
                else AddGrass(high,low,candidate,origin,kind == "broadleaf");
                int count = high.TriangleCount + low.TriangleCount;
                if (report.totalTriangles + count > config.maxTrianglesIncludingLod) continue;
                if (!tiles.TryGetValue(key,out Tile tile)) tiles.Add(key,tile = new Tile { origin = origin });
                tile.high.Append(high); tile.low.Append(low);
                report.lod0Triangles += high.TriangleCount; report.lod1Triangles += low.TriangleCount; report.totalTriangles += count;
                if(kind=="flower")report.flowers++; else if(kind=="fern")report.ferns++; else report.grassClumps++;
                report.placements.Add(new Placement { kind=kind, position=candidate.position, normal=candidate.normal, pathDistance=candidate.pathDistance, seed=candidate.seed });
            }
            if (report.grassClumps < 20 || tiles.Count == 0) throw new InvalidOperationException("Fewer than 20 grass clumps passed masks. Inspect terrain/path/solid masks; old meadow is preserved.");
            GameObject generated = null;
            try
            {
                // Every generation owns a new folder. Previous generated assets are retained deliberately.
                // This avoids mutating materials/meshes still referenced by the previous prefab or a reviewer.
                string generation = outputAssetFolder.TrimEnd('/').Replace('\\','/') + "/MeadowGeneration_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff");
                EnsureOwnFolder(generation);
                report.outputPath = generation;
                var material = new Material(shader) { name = "Meadow_SilverGreen", enableInstancing = true };
                material.SetFloat("_WindAmplitude",config.windAmplitude);
                material.SetFloat("_FadeStart",config.shaderFadeStart); material.SetFloat("_FadeEnd",config.shaderFadeEnd);
                SaveNewAsset(material,generation+"/Meadow_SilverGreen.mat",report);
                generated = new GameObject(OwnedName+"_Candidate");
                generated.transform.SetParent(islandRoot.transform,false);
                new GameObject(MarkerName).transform.SetParent(generated.transform,false);
                foreach (var entry in tiles.OrderBy(t=>t.Key.x).ThenBy(t=>t.Key.y))
                {
                    string tileName = "Meadow_"+entry.Key.x.ToString(CultureInfo.InvariantCulture)+"_"+entry.Key.y.ToString(CultureInfo.InvariantCulture);
                    GameObject tileObject = new GameObject(tileName);
                    tileObject.transform.SetParent(generated.transform,false);
                    tileObject.transform.SetPositionAndRotation(entry.Value.origin,Quaternion.identity);
                    Renderer high = MakeRenderer(tileObject.transform,"LOD0",entry.Value.high,material,generation+"/"+tileName+"_LOD0.asset",config,report);
                    Renderer low = MakeRenderer(tileObject.transform,"LOD1",entry.Value.low,material,generation+"/"+tileName+"_LOD1.asset",config,report);
                    LODGroup lod = tileObject.AddComponent<LODGroup>();
                    float lodSize = Mathf.Max(config.chunkSize,high.bounds.size.y);
                    lod.size = lodSize;
                    Vector3 center = high.bounds.center;
                    lod.localReferencePoint = tileObject.transform.InverseTransformPoint(center);
                    float fovScale = 2*Mathf.Tan(config.referenceVerticalFov*Mathf.Deg2Rad*.5f);
                    float first = Mathf.Clamp(lodSize/(config.lod1DistanceAtReferenceFov*fovScale),.025f,.95f);
                    float last = Mathf.Clamp(lodSize/(config.cullDistanceAtReferenceFov*fovScale),.005f,first-.005f);
                    lod.fadeMode = LODFadeMode.CrossFade; lod.animateCrossFading = false;
                    lod.SetLODs(new[] { new LOD(first,new[] { high }) { fadeTransitionWidth=.18f }, new LOD(last,new[] { low }) { fadeTransitionWidth=.15f } });
                }
                report.chunks = tiles.Count; report.renderers = tiles.Count*2;
                AddValidation(generated,islandRoot,config,report);
                Add(report,"foreign-transforms-preserved",ForeignUnchanged(foreign),"Names, parents, layers, world poses and local scales recorded outside owned Meadow.");
                if(report.checks.Any(c=>!c.passed)) throw new InvalidOperationException("Meadow validation failed; previous meadow is preserved: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name)));
                report.status = "generated-awaiting-runtime-and-visual-verification";
                report.buildSeconds = clock.Elapsed.TotalSeconds;
                report.warnings.Add("No gameplay, WebGL, frame-time, LOD-transition or visual approval claimed by this generator.");
                report.warnings.Add("Old generated assets are retained; only the owned Meadow subtree is replaced. Caller must explicitly save its own prefab/scene.");
                string jsonPath = generation+"/build-report.json";
                File.WriteAllText(ProjectFilePath(jsonPath),JsonUtility.ToJson(report,true),new System.Text.UTF8Encoding(false));
                AssetDatabase.ImportAsset(jsonPath,ImportAssetOptions.ForceSynchronousImport);
                // Commit the scene change last. Failed masks, mesh validation or report IO
                // leave the old subtree and every foreign object untouched.
                if(oldRoot!=null) Object.DestroyImmediate(oldRoot.gameObject);
                generated.name = OwnedName;
                return report;
            }
            catch
            {
                if(generated!=null && generated.name!=OwnedName) Object.DestroyImmediate(generated);
                throw;
            }
        }

        /// <summary>Read-only scene validation; not a substitute for animated captures or GPU measurements.</summary>
        public static BuildReport Validate(GameObject islandRoot, int maximumTriangles = 70000)
        {
            if(islandRoot==null)throw new ArgumentNullException(nameof(islandRoot));
            Transform owned=FindDirectChild(islandRoot.transform,OwnedName);
            if(owned==null)throw new InvalidOperationException("No owned Meadow subtree exists.");
            AssertOwned(owned);
            var report=new BuildReport { status="read-only-structure-validation", unityVersion=Application.unityVersion, generatedUtc=DateTime.UtcNow.ToString("O") };
            AddValidation(owned.gameObject,islandRoot,new Settings { maxTrianglesIncludingLod=maximumTriangles },report);
            return report;
        }

        static void ValidateArguments(GameObject root,string output,Settings s)
        {
            if(root==null)throw new ArgumentNullException(nameof(root));
            if(EditorUtility.IsPersistent(root) || !root.scene.IsValid())throw new ArgumentException("Pass a scene instance or loaded prefab contents, never a persistent prefab asset.");
            if(!root.activeInHierarchy)throw new ArgumentException("Island must be active so its own colliders can be sampled.");
            if((root.transform.lossyScale-Vector3.one).sqrMagnitude>0.000001f)throw new ArgumentException("Island requires unit world scale; do not rescale its anchor contract.");
            if(string.IsNullOrWhiteSpace(output))throw new ArgumentException("An explicit owned asset folder is required.");
            string normalized=output.Replace('\\','/').TrimEnd('/');
            string absolute=ProjectFilePath(normalized).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
            string allowed=ProjectFilePath(AllowedRoot).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
            if(!normalized.StartsWith(AllowedRoot,StringComparison.Ordinal) || !absolute.StartsWith(allowed,StringComparison.OrdinalIgnoreCase) || normalized.Contains(".."))
                throw new ArgumentException("Output must be a subdirectory of "+AllowedRoot);
            if(s.maxTrianglesIncludingLod<100 || s.maxTrianglesIncludingLod>70000 || s.maxGrassClumps<20 || s.maxFlowers<0 || s.maxFerns<0)
                throw new ArgumentException("Triangle budget must be 100..70000 and plant maxima nonnegative.");
            float[] finite={s.candidateSpacing,s.grassClumpsPerSquareMetre,s.chunkSize,s.minimumGroundY,s.maximumSlopeDegrees,s.pathClearance,s.solidClearance,s.anchorClearance,s.windAmplitude,s.lod1DistanceAtReferenceFov,s.cullDistanceAtReferenceFov,s.referenceVerticalFov,s.shaderFadeStart,s.shaderFadeEnd};
            if(finite.Any(v=>float.IsNaN(v)||float.IsInfinity(v)) || s.candidateSpacing<.18f || s.chunkSize<3 || s.chunkSize>12 || s.maximumSlopeDegrees<0 || s.maximumSlopeDegrees>50 || s.windAmplitude<0 || s.windAmplitude>.12f || s.pathClearance<0 || s.solidClearance<0 || s.anchorClearance<.2f || s.grassClumpsPerSquareMetre<=0 || s.lod1DistanceAtReferenceFov<2 || s.cullDistanceAtReferenceFov<=s.lod1DistanceAtReferenceFov+2 || s.referenceVerticalFov<20 || s.referenceVerticalFov>90 || s.shaderFadeEnd<=s.shaderFadeStart || s.shaderFadeStart<2)
                throw new ArgumentException("Invalid finite placement, wind or LOD settings.");
        }

        static Mask GatherMask(Transform root,Transform old,Settings s,BuildReport report)
        {
            Collider[] own=root.GetComponentsInChildren<Collider>(true).Where(c=>c!=null&&c.enabled&&c.gameObject.activeInHierarchy&&!c.isTrigger&&(old==null||!c.transform.IsChildOf(old))).ToArray();
            var mask=new Mask();
            // Explicit own-collider raycasts, never Physics.Raycast into a neighbouring loaded scene.
            mask.ground=own.Where(c=>c.gameObject.layer==8 && c is MeshCollider && c.name.StartsWith("IslandGround",StringComparison.Ordinal)).ToArray();
            if(mask.ground.Length==0)throw new InvalidOperationException("Expected at least one own active Layer 8 IslandGround MeshCollider; no fallback to global scene physics.");
            mask.bounds=mask.ground[0].bounds;
            foreach(Collider c in mask.ground)mask.bounds.Encapsulate(c.bounds);
            mask.rayTop=mask.bounds.max.y+10; mask.rayLength=mask.bounds.size.y+30;
            // Cliff bounds enclose much of the island and must not be treated as building exclusion boxes.
            mask.solids=own.Where(c=>c.gameObject.layer==9 && c.name.IndexOf("Cliff",StringComparison.OrdinalIgnoreCase)<0).Select(c=>c.bounds).ToArray();
            mask.decks=own.Where(c=>c.gameObject.layer==8&&!mask.ground.Contains(c)).Select(c=>c.bounds).ToArray();
            foreach(Transform t in root.GetComponentsInChildren<Transform>(true))
            {
                if(old!=null&&t.IsChildOf(old))continue;
                if(t.name.StartsWith("NPC_",StringComparison.Ordinal) || t.name=="Anchor_PlayerSpawn" || t.name=="Anchor_VillageGate" || t.name=="NPC_ABo_Door" || t.name=="Target_Bench")
                    mask.discs.Add(new Disc {center=t.position,radius=s.anchorClearance});
                else if(t.name.StartsWith("Anchor_Lamp_",StringComparison.Ordinal))mask.discs.Add(new Disc {center=t.position,radius=.38f});
            }
            foreach(MeshFilter mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if(!mf.name.StartsWith("StonePaths",StringComparison.Ordinal) || mf.sharedMesh==null || (old!=null&&mf.transform.IsChildOf(old)))continue;
                Mesh mesh=mf.sharedMesh;
                if(!mesh.isReadable)throw new InvalidOperationException("Road mask requires readable StonePaths; do not remove path exclusion to continue.");
                Vector3[] points=mesh.vertices; int[] indices=mesh.triangles;
                for(int i=0;i<indices.Length;i+=3)
                {
                    Vector3 a=mf.transform.TransformPoint(points[indices[i]]),b=mf.transform.TransformPoint(points[indices[i+1]]),c=mf.transform.TransformPoint(points[indices[i+2]]);
                    if(Mathf.Abs(CrossXZ(b-a,c-a))<.000001f)continue;
                    Bounds bounds=new Bounds(a,Vector3.zero); bounds.Encapsulate(b); bounds.Encapsulate(c);
                    int index=mask.paths.Count; mask.paths.Add(new Triangle {a=a,b=b,c=c,bounds=bounds});
                    for(int x=Mathf.FloorToInt((bounds.min.x-2)/3);x<=Mathf.FloorToInt((bounds.max.x+2)/3);x++)
                        for(int z=Mathf.FloorToInt((bounds.min.z-2)/3);z<=Mathf.FloorToInt((bounds.max.z+2)/3);z++)
                        { var key=new Vector2Int(x,z); if(!mask.pathCells.TryGetValue(key,out List<int> list))mask.pathCells[key]=list=new List<int>(); list.Add(index); }
                }
            }
            if(mask.paths.Count==0)throw new InvalidOperationException("No readable StonePaths triangles found. Refusing to grow grass over the navigation route.");
            report.pathTriangles=mask.paths.Count; report.ownGroundColliders=mask.ground.Length; report.ownSolidColliders=mask.solids.Length;
            return mask;
        }

        static List<Candidate> MakeCandidates(Mask mask,Settings s,BuildReport report)
        {
            var candidates=new List<Candidate>();
            int minX=Mathf.FloorToInt(mask.bounds.min.x/s.candidateSpacing),maxX=Mathf.CeilToInt(mask.bounds.max.x/s.candidateSpacing);
            int minZ=Mathf.FloorToInt(mask.bounds.min.z/s.candidateSpacing),maxZ=Mathf.CeilToInt(mask.bounds.max.z/s.candidateSpacing);
            if((long)(maxX-minX+1)*(maxZ-minZ+1)>100000)throw new InvalidOperationException("Candidate grid exceeds 100k points; confirm the passed island and world scale.");
            float minUp=Mathf.Cos(s.maximumSlopeDegrees*Mathf.Deg2Rad);
            for(int x=minX;x<=maxX;x++)for(int z=minZ;z<=maxZ;z++)
            {
                report.candidatePoints++;
                float seed=Hash(x,z,s.seed);
                float px=(x+.15f+.70f*seed)*s.candidateSpacing,pz=(z+.15f+.70f*Hash(x,z,s.seed+19))*s.candidateSpacing;
                float macro=Noise(px*.21f,pz*.21f,s.seed+71),small=Noise(px*.69f,pz*.69f,s.seed+213);
                // A few coherent open patches, continuous mid-density and dense banks.
                float density=Mathf.SmoothStep(.07f,1f,Mathf.Clamp01((macro-.22f)/.58f))*Mathf.Lerp(.65f,1.1f,small);
                float chance=Mathf.Clamp01(s.grassClumpsPerSquareMetre*s.candidateSpacing*s.candidateSpacing*density);
                if(Hash(x,z,s.seed+31)>chance)continue;
                if(!SampleGround(mask,px,pz,out RaycastHit hit,report)){report.groundMisses++;continue;}
                if(hit.point.y<s.minimumGroundY || hit.normal.y<minUp){report.steepRejected++;continue;}
                Vector3 p=hit.point+Vector3.up*.002f;
                float path=PathDistance(mask,p);
                if(path<s.pathClearance){report.pathRejected++;continue;}
                float edgeDensity=Mathf.Lerp(.20f,1f,Mathf.SmoothStep(0,1,Mathf.Clamp01((path-s.pathClearance)/.45f)));
                if(Hash(x,z,s.seed+35)>edgeDensity)continue;
                float obstacle=ObstacleDistance(mask,p);
                if(obstacle<s.solidClearance){report.solidRejected++;continue;}
                if(mask.decks.Any(b=>InsideExpandedXZ(b,p,.2f)&&p.y<=b.max.y+.5f)){report.solidRejected++;continue;}
                if(mask.discs.Any(d=>DistanceXZ(d.center,p)<d.radius)){report.anchorRejected++;continue;}
                candidates.Add(new Candidate {position=p,normal=hit.normal.normalized,seed=seed,order=Hash(x,z,s.seed+997),pathDistance=path,obstacleDistance=obstacle,cellX=x,cellZ=z});
            }
            return candidates;
        }

        static string ChooseKind(Candidate c,Settings s,BuildReport r)
        {
            float species=Hash(c.cellX,c.cellZ,s.seed+941);
            float floralPatch=Noise(c.position.x*.36f+17,c.position.z*.36f-29,s.seed+511);
            if(r.ferns<s.maxFerns && c.obstacleDistance>.25f && c.obstacleDistance<1.35f && c.pathDistance>.35f && species<.14f)return "fern";
            if(r.flowers<s.maxFlowers && c.pathDistance>.30f && c.pathDistance<2.5f && floralPatch>.53f && species>.76f)return "flower";
            if(r.grassClumps>=s.maxGrassClumps)return null;
            return species<.11f&&c.pathDistance>.40f?"broadleaf":"grass";
        }

        static void AddGrass(MeshData high,MeshData low,Candidate c,Vector3 origin,bool broad)
        {
            float edge=Mathf.SmoothStep(0,1,Mathf.Clamp01(c.pathDistance/.55f));
            float h=Mathf.Lerp(.10f,.30f,Hash(c.cellX,c.cellZ,201))*Mathf.Lerp(.58f,1,edge);
            if(Hash(c.cellX,c.cellZ,301)>.94f&&edge>.9f)h*=1.35f;
            float yaw=c.seed*Mathf.PI*2;
            Color tint=Color.Lerp(new Color(.84f,.93f,.90f),new Color(1.08f,1.04f,.92f),Hash(c.cellX,c.cellZ,707));
            Vector3 root=c.position-origin;
            // Five finer two-segment blades give a denser silhouette at the same
            // 15-triangle budget as three broad three-segment leaves.
            int blades=broad?3:5;
            for(int i=0;i<blades;i++)
            {
                float angle=yaw+i*(Mathf.PI*2/blades+.047f);
                Vector3 direction=Vector3.ProjectOnPlane(new Vector3(Mathf.Sin(angle),0,Mathf.Cos(angle)),c.normal).normalized;
                Vector3 leafRoot=root+direction*(i==0?0:.025f);
                float height=h*(1-i*(broad?.14f:.09f));
                float width=(broad?.055f:.015f)*Mathf.Lerp(.8f,1.2f,c.seed);
                AddBlade(high,leafRoot,c.normal,direction,height,width,height*(broad?.4f:.28f),tint,c.seed,root,h,0,broad);
                if(i==0)AddBlade(low,leafRoot,c.normal,direction,height,width*1.15f,height*.28f,tint,c.seed,root,h,0,false);
            }
        }

        // 3 smooth-width segments ending in a real pointed tip: 5 triangles high / 3 low.
        static void AddBlade(MeshData data,Vector3 start,Vector3 groundNormal,Vector3 direction,float height,float width,float bend,Color tint,float seed,Vector3 plantRoot,float plantHeight,float species,bool high)
        {
            Vector3 up=Vector3.Slerp(groundNormal,Vector3.up,.80f).normalized;
            Vector3 across=Vector3.Cross(up,direction).normalized;
            float[] levels=high?new[]{0f,.36f,.72f}:new[]{0f,.58f};
            int previous=-1;
            foreach(float h in levels)
            {
                Vector3 center=start+up*(height*h)+direction*(bend*h*h);
                Vector3 tangent=(up*height+direction*(2*bend*h)).normalized;
                Vector3 normal=Vector3.Cross(across,tangent).normalized;
                float half=width*.5f*Mathf.Lerp(.82f,1,Mathf.Sin(h*Mathf.PI))*(1-h*.7f);
                float weight=(center.y-plantRoot.y)/Mathf.Max(.08f,plantHeight);
                int left=data.Add(center-across*half,normal,tint,0,weight,species,seed,plantRoot,plantHeight);
                int right=data.Add(center+across*half,normal,tint,1,weight,species,seed,plantRoot,plantHeight);
                if(previous>=0){data.Tri(previous,previous+1,left);data.Tri(previous+1,right,left);}
                previous=left;
            }
            Vector3 tip=start+up*height+direction*bend;
            int end=data.Add(tip,Vector3.Cross(across,up*height+direction*2*bend),tint,.5f,(tip.y-plantRoot.y)/Mathf.Max(.08f,plantHeight),species,seed,plantRoot,plantHeight);
            data.Tri(previous,previous+1,end);
        }

        static void AddFlower(MeshData high,MeshData low,Candidate c,Vector3 origin)
        {
            Vector3 root=c.position-origin;
            float height=Mathf.Lerp(.19f,.36f,c.seed),radius=Mathf.Lerp(.025f,.043f,c.seed);
            Vector3 direction=new Vector3(Mathf.Sin(c.seed*6.28f),0,Mathf.Cos(c.seed*6.28f));
            Color green=new Color(.90f,.98f,.91f),cream=Color.Lerp(Color.white,new Color(1,.95f,.87f),c.seed);
            AddBlade(high,root,c.normal,direction,height,.008f,.022f,green,c.seed,root,height,1,false);
            AddBlade(low,root,c.normal,direction,height,.010f,.022f,green,c.seed,root,height,1,false);
            Vector3 center=root+Vector3.Slerp(c.normal,Vector3.up,.80f).normalized*height+direction*.022f;
            for(int i=0;i<5;i++)
            {
                float a=c.seed*6.28f+i*Mathf.PI*2/5;
                Vector3 radial=new Vector3(Mathf.Cos(a),0,Mathf.Sin(a)),across=Vector3.Cross(Vector3.up,radial);
                Vector3 inner=center+radial*radius*.22f,outer=center+radial*radius+Vector3.down*.006f;
                int p=high.Add(inner,Vector3.up,cream,.5f,1,2,c.seed,root,height);
                int l=high.Add(outer-across*radius*.32f,Vector3.up,cream,0,1,2,c.seed,root,height);
                int t=high.Add(outer+radial*radius*.14f,Vector3.up,cream,.5f,1,2,c.seed,root,height);
                int r=high.Add(outer+across*radius*.32f,Vector3.up,cream,1,1,2,c.seed,root,height);
                high.Tri(p,l,t);high.Tri(p,t,r);
                int p0=low.Add(inner,Vector3.up,cream,.5f,1,2,c.seed,root,height);
                int p1=low.Add(outer-across*radius*.35f,Vector3.up,cream,0,1,2,c.seed,root,height);
                int p2=low.Add(outer+across*radius*.35f,Vector3.up,cream,1,1,2,c.seed,root,height);
                low.Tri(p0,p1,p2);
            }
            foreach(MeshData data in new[]{high,low})
            {
                int centerIndex=data.Add(center+Vector3.up*.003f,Vector3.up,Color.white,.5f,1,3,c.seed,root,height);
                for(int i=0;i<5;i++)
                {
                    float a=i*Mathf.PI*2/5,b=(i+1)*Mathf.PI*2/5;
                    int p=data.Add(center+new Vector3(Mathf.Cos(a),.01f,Mathf.Sin(a))*radius*.26f,Vector3.up,Color.white,0,1,3,c.seed,root,height);
                    int q=data.Add(center+new Vector3(Mathf.Cos(b),.01f,Mathf.Sin(b))*radius*.26f,Vector3.up,Color.white,1,1,3,c.seed,root,height);
                    data.Tri(centerIndex,p,q);
                }
            }
        }

        static void AddFern(MeshData high,MeshData low,Candidate c,Vector3 origin)
        {
            Vector3 root=c.position-origin;
            float height=Mathf.Lerp(.22f,.40f,c.seed),length=height*.95f;
            Color tint=new Color(.88f,1.01f,.86f);
            for(int frond=0;frond<3;frond++)
            {
                float angle=c.seed*6.28f+frond*2.0944f;
                Vector3 forward=new Vector3(Mathf.Sin(angle),0,Mathf.Cos(angle));
                Vector3 across=Vector3.Cross(Vector3.up,forward);
                AddBlade(high,root,c.normal,forward,height,.009f,length,tint,c.seed,root,height,1,true);
                if(frond==0)AddBlade(low,root,c.normal,forward,height,.012f,length,tint,c.seed,root,height,1,false);
                for(int pair=1;pair<=5;pair++)
                {
                    float h=pair/6f;
                    Vector3 stem=root+Vector3.Slerp(c.normal,Vector3.up,.80f).normalized*height*h+forward*(length*h*h);
                    float reach=height*.37f*Mathf.Sin(h*Mathf.PI)*Mathf.Lerp(1,.5f,h);
                    foreach(int sign in new[]{-1,1})
                    {
                        Vector3 tip=stem+across*(reach*sign)+forward*reach*.38f+Vector3.up*.015f;
                        Vector3 side=forward*(reach*.13f);
                        int a=high.Add(stem-side*.35f,Vector3.up,tint,0,h,0,c.seed,root,height);
                        int b=high.Add(stem+side*.35f,Vector3.up,tint,1,h,0,c.seed,root,height);
                        Vector3 middle=Vector3.Lerp(stem,tip,.55f);
                        int d=high.Add(middle-side,Vector3.up,tint,0,h+.04f,0,c.seed,root,height);
                        int e=high.Add(middle+side,Vector3.up,tint,1,h+.04f,0,c.seed,root,height);
                        int t=high.Add(tip,Vector3.up,tint,.5f,h+.06f,0,c.seed,root,height);
                        high.Tri(a,b,d);high.Tri(b,e,d);high.Tri(d,e,t);
                        if(frond==0&&pair%2==1)
                        {
                            int la=low.Add(stem-side,Vector3.up,tint,0,h,0,c.seed,root,height);
                            int lb=low.Add(stem+side,Vector3.up,tint,1,h,0,c.seed,root,height);
                            int lt=low.Add(tip,Vector3.up,tint,.5f,h+.06f,0,c.seed,root,height);
                            low.Tri(la,lb,lt);
                        }
                    }
                }
            }
        }

        static Renderer MakeRenderer(Transform parent,string name,MeshData data,Material material,string assetPath,Settings config,BuildReport report)
        {
            Mesh mesh=data.ToMesh(Path.GetFileNameWithoutExtension(assetPath),config.windAmplitude+.025f);
            SaveNewAsset(mesh,assetPath,report);
            GameObject go=new GameObject(name);go.transform.SetParent(parent,false);
            go.AddComponent<MeshFilter>().sharedMesh=mesh;
            MeshRenderer renderer=go.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;
            renderer.shadowCastingMode=config.castGrassShadows?ShadowCastingMode.TwoSided:ShadowCastingMode.Off;
            renderer.receiveShadows=true;renderer.lightProbeUsage=LightProbeUsage.BlendProbes;renderer.reflectionProbeUsage=ReflectionProbeUsage.Off;
            return renderer;
        }

        static void AddValidation(GameObject meadow,GameObject island,Settings settings,BuildReport report)
        {
            MeshFilter[] filters=meadow.GetComponentsInChildren<MeshFilter>(true);
            MeshRenderer[] renderers=meadow.GetComponentsInChildren<MeshRenderer>(true);
            int high=0,low=0;bool finite=true,channels=true,ownedAssets=true;
            foreach(MeshFilter f in filters)
            {
                Mesh m=f.sharedMesh;
                if(m==null){channels=false;continue;}
                if(f.name=="LOD1")low+=m.triangles.Length/3;else high+=m.triangles.Length/3;
                finite &= m.vertices.All(v=>Finite(v.x)&&Finite(v.y)&&Finite(v.z));
                var roots=new List<Vector4>();var uv=new List<Vector4>();m.GetUVs(1,roots);m.GetUVs(0,uv);
                channels &= roots.Count==m.vertexCount&&uv.Count==m.vertexCount&&m.normals.Length==m.vertexCount&&m.colors.Length==m.vertexCount;
                ownedAssets &= AssetDatabase.GetAssetPath(m).StartsWith(AllowedRoot,StringComparison.Ordinal) && AssetDatabase.GetAssetPath(m).Contains("/MeadowGeneration_");
            }
            report.lod0Triangles=high;report.lod1Triangles=low;report.totalTriangles=high+low;report.renderers=renderers.Length;report.chunks=meadow.GetComponentsInChildren<LODGroup>(true).Length;
            Add(report,"triangle-budget",report.totalTriangles>0&&report.totalTriangles<=settings.maxTrianglesIncludingLod,report.totalTriangles+" authored triangles including inactive LODs.");
            Add(report,"finite-vertices",finite,"No NaN or Infinity positions.");
            Add(report,"required-vertex-channels",channels,"Normals, colours, root data and wind/species UV data match each vertex.");
            Add(report,"owned-generated-mesh-paths",ownedAssets,"All meshes under Environment/.../MeadowGeneration_.");
            Add(report,"no-meadow-colliders",meadow.GetComponentsInChildren<Collider>(true).Length==0,"Visual foliage never enters collision or lamp-target raycasts.");
            Add(report,"no-gameplay-layers",meadow.GetComponentsInChildren<Transform>(true).All(t=>t.gameObject.layer!=8&&t.gameObject.layer!=9),"Ground and solid collision layers are untouched.");
            Add(report,"exact-two-lods",meadow.GetComponentsInChildren<LODGroup>(true).All(g=>g.GetLODs().Length==2&&g.fadeMode==LODFadeMode.CrossFade),"Two spatially chunked LOD meshes, crossfade and shader distance thinning.");
            Add(report,"shared-supported-meadow-material",renderers.All(r=>r.sharedMaterial!=null&&r.sharedMaterial.shader!=null&&r.sharedMaterial.shader.name==ShaderName&&r.sharedMaterial.shader.isSupported),"Every mesh uses the owned foliage shader.");
            Add(report,"owned-direct-parent",meadow.transform.parent==island.transform,"No objects were reparented into existing environment groups.");
        }

        static bool SampleGround(Mask mask,float x,float z,out RaycastHit closest,BuildReport report)
        {
            report.groundQueries++;closest=default;bool found=false;float distance=float.PositiveInfinity;
            Ray ray=new Ray(new Vector3(x,mask.rayTop,z),Vector3.down);
            foreach(Collider c in mask.ground)
                if(c.Raycast(ray,out RaycastHit hit,mask.rayLength)&&hit.distance<distance){closest=hit;distance=hit.distance;found=true;}
            return found;
        }
        static float PathDistance(Mask mask,Vector3 p)
        {
            var key=new Vector2Int(Mathf.FloorToInt(p.x/3),Mathf.FloorToInt(p.z/3));
            if(!mask.pathCells.TryGetValue(key,out List<int> indices))return 10;
            float best=10;
            foreach(int i in indices)
            {
                Triangle t=mask.paths[i];
                if(p.y<t.bounds.min.y-.8f||p.y>t.bounds.max.y+.8f)continue;
                float a=CrossXZ(t.b-t.a,p-t.a),b=CrossXZ(t.c-t.b,p-t.b),c=CrossXZ(t.a-t.c,p-t.c);
                if((a>=0&&b>=0&&c>=0)||(a<=0&&b<=0&&c<=0))return 0;
                best=Mathf.Min(best,SegmentDistance(p,t.a,t.b),SegmentDistance(p,t.b,t.c),SegmentDistance(p,t.c,t.a));
            }
            return best;
        }
        static float ObstacleDistance(Mask mask,Vector3 p)
        {
            float distance=10;
            foreach(Bounds b in mask.solids)
            {
                if(p.y>b.max.y+.15f || p.y<b.min.y-.45f)continue;
                float dx=Mathf.Max(0,b.min.x-p.x,p.x-b.max.x),dz=Mathf.Max(0,b.min.z-p.z,p.z-b.max.z);
                distance=Mathf.Min(distance,Mathf.Sqrt(dx*dx+dz*dz));
            }
            return distance;
        }
        static bool InsideExpandedXZ(Bounds b,Vector3 p,float pad) => p.x>=b.min.x-pad&&p.x<=b.max.x+pad&&p.z>=b.min.z-pad&&p.z<=b.max.z+pad;
        static float SegmentDistance(Vector3 p,Vector3 a,Vector3 b)
        {
            Vector2 ap=new Vector2(p.x-a.x,p.z-a.z),ab=new Vector2(b.x-a.x,b.z-a.z);
            float t=Mathf.Clamp01(Vector2.Dot(ap,ab)/Mathf.Max(.0000001f,ab.sqrMagnitude));return(ap-ab*t).magnitude;
        }
        static float CrossXZ(Vector3 a,Vector3 b)=>a.x*b.z-a.z*b.x;
        static float DistanceXZ(Vector3 a,Vector3 b)=>new Vector2(a.x-b.x,a.z-b.z).magnitude;
        static float Noise(float x,float z,int seed)
        {
            int ix=Mathf.FloorToInt(x),iz=Mathf.FloorToInt(z);float fx=x-ix,fz=z-iz;
            fx=fx*fx*(3-2*fx);fz=fz*fz*(3-2*fz);
            return Mathf.Lerp(Mathf.Lerp(Hash(ix,iz,seed),Hash(ix+1,iz,seed),fx),Mathf.Lerp(Hash(ix,iz+1,seed),Hash(ix+1,iz+1,seed),fx),fz);
        }
        static float Hash(int x,int z,int seed)
        {
            unchecked { uint v=(uint)x*374761393u+(uint)z*668265263u+(uint)seed*2246822519u;v=(v^(v>>13))*1274126177u;v^=v>>16;return(v&0x00ffffffu)/16777216f; }
        }
        static bool Finite(float n)=>!float.IsNaN(n)&&!float.IsInfinity(n);
        static string ProjectFilePath(string assetPath)=>Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Application.dataPath),assetPath));
        static void Add(BuildReport report,string name,bool passed,string detail)=>report.checks.Add(new Check{name=name,passed=passed,detail=detail});
        static Transform FindDirectChild(Transform parent,string name)
        {
            Transform match=null;foreach(Transform t in parent)if(t.name==name){if(match!=null)throw new InvalidOperationException("Duplicate owned root name: "+name);match=t;}return match;
        }
        static void AssertOwned(Transform root)
        {
            if(FindDirectChild(root,MarkerName)==null)throw new InvalidOperationException("Existing "+OwnedName+" lacks ownership marker; refusing replacement.");
            foreach(Component c in root.GetComponentsInChildren<Component>(true))
                if(!(c is Transform)&&!(c is MeshFilter)&&!(c is MeshRenderer)&&!(c is LODGroup))throw new InvalidOperationException("Owned Meadow contains unknown/user components; refusing replacement.");
            foreach(MeshFilter filter in root.GetComponentsInChildren<MeshFilter>(true))
                if(filter.sharedMesh==null||!AssetDatabase.GetAssetPath(filter.sharedMesh).StartsWith(AllowedRoot,StringComparison.Ordinal)||!AssetDatabase.GetAssetPath(filter.sharedMesh).Contains("/MeadowGeneration_"))
                    throw new InvalidOperationException("Existing Meadow contains a foreign mesh; refusing replacement.");
        }
        static ForeignState[] CaptureForeign(Transform root,Transform exclude)=>root.GetComponentsInChildren<Transform>(true).Where(t=>exclude==null||!t.IsChildOf(exclude)).Select(t=>new ForeignState{transform=t,parent=t.parent,name=t.name,layer=t.gameObject.layer,position=t.position,rotation=t.rotation,scale=t.localScale}).ToArray();
        static bool ForeignUnchanged(IEnumerable<ForeignState> saved)=>saved.All(s=>s.transform!=null&&s.transform.parent==s.parent&&s.transform.name==s.name&&s.transform.gameObject.layer==s.layer&&(s.transform.position-s.position).sqrMagnitude<1e-12f&&Quaternion.Angle(s.rotation,s.transform.rotation)<.001f&&(s.scale-s.transform.localScale).sqrMagnitude<1e-12f);
        static void EnsureOwnFolder(string path)
        {
            if(!path.StartsWith(AllowedRoot,StringComparison.Ordinal)||path.Contains(".."))throw new InvalidOperationException("Refusing folder outside owned Environment subtree.");
            string[] parts=path.Split('/');string current=parts[0];for(int i=1;i<parts.Length;i++){string next=current+"/"+parts[i];if(!AssetDatabase.IsValidFolder(next))AssetDatabase.CreateFolder(current,parts[i]);current=next;}
        }
        static void SaveNewAsset(Object asset,string path,BuildReport report)
        {
            if(!path.StartsWith(AllowedRoot,StringComparison.Ordinal)||!path.Contains("/MeadowGeneration_")||AssetDatabase.LoadMainAssetAtPath(path)!=null||File.Exists(ProjectFilePath(path)))throw new InvalidOperationException("Refusing to overwrite or create a foreign asset: "+path);
            AssetDatabase.CreateAsset(asset,path);AssetDatabase.SaveAssetIfDirty(asset);report.assets.Add(path);
        }
    }
}
#endif
