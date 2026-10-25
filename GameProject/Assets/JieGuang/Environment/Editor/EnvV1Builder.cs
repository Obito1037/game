#if UNITY_EDITOR
// Offline-authored assembly tool for the new JieGuang environment only.
// Copy into Assets/JieGuang/Environment/Editor with scene-input.json and the staged assets.
// This file does not execute on import. Build/Validate/Capture are explicit editor commands.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV1Builder
    {
        public const string Root = "Assets/JieGuang/Environment";
        public const string PrefabPath = Root + "/Island.prefab";
        public const string TestScenePath = Root + "/EnvTest.unity";
        private const int GroundLayer = 8;
        private const int SolidLayer = 9;
        private const int Width = 1440;
        private const int Height = 900;
        private const float LodHigh = .18f;
        private const float LodCull = .012f;

        [Serializable] public sealed class InputData
        {
            public ModelData[] models;
            public MaterialData[] materials;
            public InstanceData[] instances;
            public AnchorData[] anchors;
            public PointData[] boundary;
        }
        [Serializable] public sealed class ModelData
        { public string id, path, lod1, kind; }
        [Serializable] public sealed class MaterialData
        {
            public string name, texture, emissionTexture;
            public float[] color, emission;
            public float strength, metallic, roughness;
        }
        [Serializable] public sealed class InstanceData
        {
            public string name, asset, group, collider;
            public float[] position;
            public float yaw;
            public float scale = 1;
        }
        [Serializable] public sealed class AnchorData
        {
            public string name, kind;
            public float[] position, forward, size;
            public float fov, height;
        }
        [Serializable] public sealed class PointData { public float[] position; }
        [Serializable] public sealed class Check
        { public string name, detail; public bool passed; }
        [Serializable] public sealed class Report
        {
            public string status, utc, scope, prefab;
            public string renderingMetricsNote = "meshRenderers and materials are object/asset inventory counts, not draw-call counts. Draw calls are not measured by this validator.";
            public long activeLod0Triangles, trianglesIncludingBothLods, skyAndSeaTriangles;
            public int meshRenderers, materials, lodGroups, groundColliders, solidColliders, windows, spotlights;
            public List<Check> checks = new List<Check>();
            public List<string> warnings = new List<string>();
            public List<ImportRecord> imports = new List<ImportRecord>();
            public List<MarkerRecord> markerComparisons = new List<MarkerRecord>();
        }
        [Serializable] public sealed class ImportRecord
        {
            public string id, path, lod;
            public int meshes;
            public long triangles;
            public float[] boundsCenter, boundsSize, rootLocalPosition, rootLocalEuler, rootLocalScale;
            public bool importAnimation, addCollider, isReadable, useFileScale, bakeAxisConversion;
            public float globalScale;
        }
        [Serializable] public sealed class MarkerRecord
        {
            public string instance, marker, anchor;
            public float[] actualWorldPosition, anchorWorldPosition, actualWorldForward, anchorWorldForward;
            public float distanceMetres, forwardAngleDegrees, toleranceMetres;
        }
        [Serializable] public sealed class CaptureRecord
        { public string file, camera, renderMethod; public int width, height; }
        [Serializable] public sealed class CaptureReport
        {
            public string status, utc, scope;
            public string isolationCaveat = "Preview-scene camera.scene isolation is requested. Absence of other-scene realtime lighting influence still needs verification in the running Unity Editor.";
            public List<CaptureRecord> images = new List<CaptureRecord>();
        }

        private static readonly string[] RequiredNames = {
            "Anchor_PlayerSpawn", "Anchor_Lamp_WanFeng", "Anchor_Lamp_YueChuang", "Anchor_Lamp_GuiHang",
            "Target_Path", "Target_Bench", "Target_Window", "Target_Pier", "Anchor_FlagpoleHook",
            "NPC_AYing", "NPC_Postman", "NPC_Bench", "NPC_ABo_Window", "NPC_DengBo_Box",
            "Cam_Title", "Cam_Puzzle", "Cam_Pier", "Village_Windows",
            "Sky_ScatterZone_Village", "Sky_ScatterZone_Pier", "Walkable_Boundary",
            "Anchor_VillageGate", "Anchor_GoldenTree", "Anchor_Boat", "Target_Sea", "NPC_ABo_Door"
        };
        private static readonly string[] AllowedGroups = { "Terrain", "Props", "Village", "Forest", "Rocks", "Pier" };
        private static readonly List<string> BuildWarnings = new List<string>();
        private static string ProjectDirectory => Directory.GetParent(Application.dataPath).FullName;
        private static string RepositoryDirectory => Directory.GetParent(ProjectDirectory).FullName;
        private static string EvidenceDirectory => Path.Combine(RepositoryDirectory, "art/verification/env-v1");

        [MenuItem("JieGuang/Environment/1 Build Island and EnvTest")]
        public static void Build()
        {
            AssertEditorIdle();
            InputData data = ReadInput();
            CheckInput(data);
            BuildWarnings.Clear();
            PrepareImports(data);
            EnsureFolder(Root + "/Generated/Materials");
            EnsureFolder(Root + "/Generated/Meshes");
            var materials = MakeMaterials(data.materials);
            var models = data.models.ToDictionary(m => m.id, StringComparer.Ordinal);
            var loaded = new Dictionary<string, GameObject>(StringComparer.Ordinal);
            foreach (ModelData model in data.models)
            {
                loaded.Add(model.id, LoadModel(model.path));
                if (!string.IsNullOrEmpty(model.lod1)) LoadModel(model.lod1);
            }

            Scene previous = SceneManager.GetActiveScene();
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            try
            {
                SceneManager.SetActiveScene(scene);
                GameObject island = new GameObject("Island");
                var groups = AllowedGroups.ToDictionary(g => g, g => Child(island.transform, g));
                GameObject windows = Child(island.transform, "Village_Windows");
                foreach (InstanceData item in data.instances)
                {
                    ModelData model = models[item.asset];
                    GameObject instance = Child(groups[item.group].transform, item.name);
                    instance.transform.localPosition = Vector(item.position);
                    instance.transform.localRotation = Quaternion.Euler(0, item.yaw, 0);
                    instance.transform.localScale = Vector3.one * item.scale;
                    GameObject high = CloneModel(loaded[item.asset], instance.transform, "LOD0", materials);
                    if (!string.IsNullOrEmpty(model.lod1))
                    {
                        GameObject low = CloneModel(LoadModel(model.lod1), instance.transform, "LOD1", materials);
                        var lod = instance.AddComponent<LODGroup>();
                        lod.fadeMode = LODFadeMode.None;
                        lod.animateCrossFading = false;
                        lod.SetLODs(new[] {
                            new LOD(LodHigh, high.GetComponentsInChildren<Renderer>(true)),
                            new LOD(LodCull, low.GetComponentsInChildren<Renderer>(true))
                        });
                        lod.RecalculateBounds();
                    }
                    AddCollision(instance, high, item, model);
                    if (model.kind == "terrain")
                        EnvV1PathConformer.Conform(high, Root + "/Generated/Meshes/StonePathsConformed.asset");
                    if (item.group == "Village") ExtractWindows(high.transform, windows.transform, item.name);
                    if (item.name == "HarborLantern")
                    {
                        Light harbor = Child(instance.transform, "HarborLight").AddComponent<Light>();
                        harbor.transform.localPosition = new Vector3(0,.38f,0);
                        harbor.type = LightType.Point;
                        harbor.color = new Color(1,.63f,.27f);
                        harbor.intensity = 1.2f;
                        harbor.range = 3.5f;
                        harbor.shadows = LightShadows.None;
                    }
                }
                // Story code uses this parent's position as the village gathering centre.
                // Moving it must preserve every separately switchable window's world pose.
                var windowPositions = windows.transform.Cast<Transform>().Select(t => t.position).ToArray();
                windows.transform.position = new Vector3(-13,8.4f,10);
                for (int w = 0; w < windows.transform.childCount; w++) windows.transform.GetChild(w).position = windowPositions[w];
                foreach (AnchorData anchor in data.anchors)
                {
                    if (anchor.name == "Village_Windows")
                    {
                        // The window parent's village-centre pose was set without moving its children.
                        continue;
                    }
                    if (anchor.name == "Walkable_Boundary") continue;
                    GameObject go = Child(island.transform, anchor.name);
                    go.transform.localPosition = Vector(anchor.position);
                    Vector3 forward = Direction(anchor.forward);
                    if (anchor.kind == "lamp")
                        MakeLamp(go, anchor, loaded["copper_roadlamp"], materials);
                    else
                        go.transform.localRotation = Quaternion.LookRotation(forward, Vector3.up);
                    if (anchor.kind == "scatter")
                    {
                        BoxCollider box = go.AddComponent<BoxCollider>();
                        box.isTrigger = true;
                        box.size = Vector(anchor.size);
                    }
                }
                MakeBoundary(island.transform, data.boundary);
                MakePierBoundary(island.transform, data.instances);
                CombineVillage(groups["Village"].transform, island.transform);
                MakeAtmosphere(island.transform);
                // RenderSettings are saved only into our active EnvTest scene.
                // Main gameplay owns its own NightSky settings and is never saved here.
                RenderSettings.ambientMode = AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = new Color(.07f,.09f,.15f);
                RenderSettings.ambientEquatorColor = new Color(.04f,.05f,.08f);
                RenderSettings.ambientGroundColor = new Color(.015f,.015f,.02f);
                RenderSettings.reflectionIntensity = .12f;
                RenderSettings.skybox = null;
                RenderSettings.fog = false;
                RenderSettings.sun = island.transform.Find("Atmosphere/WarmEnvironmentKey").GetComponent<Light>();
                GameObject prefab = PrefabUtility.SaveAsPrefabAsset(island, PrefabPath, out bool saved);
                if (!saved || prefab == null) throw new InvalidOperationException("Could not save " + PrefabPath);
                CreateTestCamera(island.transform, data);
                if (!EditorSceneManager.SaveScene(scene, TestScenePath, false))
                    throw new InvalidOperationException("Could not save " + TestScenePath);
                Directory.CreateDirectory(EvidenceDirectory);
                File.WriteAllText(Path.Combine(EvidenceDirectory, "build-notes.json"),
                    JsonUtility.ToJson(new Report {
                        status = "built-not-yet-visually-reviewed", utc = DateTime.UtcNow.ToString("o"),
                        scope = "Environment-only prefab and additive EnvTest save. No player build. No performance claim.",
                        prefab = PrefabPath, warnings = new List<string>(BuildWarnings)
                    }, true));
                Debug.Log("[EnvV1] Saved " + PrefabPath + " and " + TestScenePath + ". Other scenes were not saved.");
            }
            finally
            {
                if (previous.IsValid() && previous.isLoaded) SceneManager.SetActiveScene(previous);
                if (scene.IsValid() && scene.isLoaded) EditorSceneManager.CloseScene(scene, true);
            }
        }

        [MenuItem("JieGuang/Environment/2 Validate Island")]
        public static void Validate()
        {
            AssertEditorIdle();
            InputData data = ReadInput();
            CheckInput(data);
            GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (source == null) throw new FileNotFoundException("Build Island before validation.", PrefabPath);
            Scene preview = EditorSceneManager.NewPreviewScene();
            GameObject island = null;
            Report report = new Report {
                utc = DateTime.UtcNow.ToString("o"), prefab = PrefabPath,
                scope = "Prefab structure, geometry totals, layers, colliders and geometric light-target rays. No gameplay or FPS claim."
            };
            try
            {
                island = (GameObject)PrefabUtility.InstantiatePrefab(source, preview);
                Transform[] transforms = island.GetComponentsInChildren<Transform>(true);
                foreach (string required in RequiredNames)
                    AddCheck(report, "unique:" + required, transforms.Count(t => t.name == required) == 1, "Exactly one required named object.");
                foreach (AnchorData a in data.anchors)
                {
                    Transform t = transforms.FirstOrDefault(x => x.name == a.name);
                    if (t == null || a.name == "Village_Windows" || a.name == "Walkable_Boundary") continue;
                    AddCheck(report, "position:" + a.name, Vector3.Distance(t.position, Vector(a.position)) < .005f,
                        "Position compared with scene-input.json, tolerance 5 mm.");
                }
                MeshRenderer[] renderers = island.GetComponentsInChildren<MeshRenderer>(true);
                report.meshRenderers = renderers.Count(r => r.enabled);
                report.materials = renderers.SelectMany(r => r.sharedMaterials).Where(m => m != null).Distinct().Count();
                var materialFailures = new List<string>();
                foreach (MeshRenderer r in renderers)
                {
                    if (!r.enabled) continue;
                    Mesh mesh = r.GetComponent<MeshFilter>()?.sharedMesh;
                    if (mesh == null) continue;
                    long triangles = 0;
                    for (int s = 0; s < mesh.subMeshCount; s++) triangles += (long)mesh.GetIndexCount(s) / 3;
                    report.trianglesIncludingBothLods += triangles;
                    if (!HasAncestor(r.transform, "LOD1")) report.activeLod0Triangles += triangles;
                    if (r.name == "NightSky" || r.name == "NightSea") report.skyAndSeaTriangles += triangles;
                    if (r.sharedMaterials.Any(m => m == null || m.shader == null || !m.shader.isSupported))
                        materialFailures.Add(r.name);
                }
                AddCheck(report, "triangle-budget", report.activeLod0Triangles <= 600000,
                    "Sum of enabled LOD0 meshes including sky and sea (only LOD1 excluded): " + report.activeLod0Triangles + "; sky/sea subset: " + report.skyAndSeaTriangles);
                AddCheck(report, "materials-supported", materialFailures.Count == 0, string.Join(", ", materialFailures));
                foreach (MaterialData spec in data.materials.Where(m => m.strength > 0))
                {
                    Material emissive = AssetDatabase.LoadAssetAtPath<Material>(Root + "/Generated/Materials/" + SafeName(spec.name) + ".mat");
                    AddCheck(report, "emission-enabled:" + spec.name,
                        emissive != null && emissive.IsKeywordEnabled("_EMISSION") &&
                        (emissive.globalIlluminationFlags & MaterialGlobalIlluminationFlags.AnyEmissive) != 0 &&
                        emissive.GetColor("_EmissionColor").maxColorComponent > 0,
                        "URP material validation must retain visible emission after saving/importing.");
                }
                Collider[] colliders = island.GetComponentsInChildren<Collider>(true);
                report.groundColliders = colliders.Count(c => c.gameObject.layer == GroundLayer && !c.isTrigger);
                report.solidColliders = colliders.Count(c => c.gameObject.layer == SolidLayer && !c.isTrigger);
                AddCheck(report, "ground-layer-8", report.groundColliders > 0, "Walkable colliders exist on numeric layer 8.");
                AddCheck(report, "solid-layer-9", report.solidColliders > 0, "Solid colliders exist on numeric layer 9.");
                report.lodGroups = island.GetComponentsInChildren<LODGroup>(true).Length;
                foreach (LODGroup group in island.GetComponentsInChildren<LODGroup>(true))
                {
                    LOD[] levels = group.GetLODs();
                    AddCheck(report, "lod:" + group.name, levels.Length == 2 &&
                        Mathf.Abs(levels[0].screenRelativeTransitionHeight - LodHigh) < .001f &&
                        Mathf.Abs(levels[1].screenRelativeTransitionHeight - LodCull) < .001f, "LOD0 18%, LOD1 1.2%, then cull; preserves trees in the distant title view.");
                }
                Light[] lights = island.GetComponentsInChildren<Light>(true);
                report.spotlights = lights.Count(l => l.type == LightType.Spot);
                AddCheck(report, "exactly-three-spotlights", report.spotlights == 3, "Three copper puzzle lamps only.");
                Transform harborLantern = transforms.FirstOrDefault(t => t.name == "HarborLantern");
                Light harborLight = harborLantern == null ? null : harborLantern.GetComponentInChildren<Light>(true);
                AddCheck(report, "harbor-light-control", harborLight != null && harborLight.type == LightType.Point && harborLight.intensity > 0 && harborLight.shadows == LightShadows.None,
                    "Story initialization can cache a nonzero warm point light; it is not a fourth puzzle Spot.");
                Transform boatAnchor = transforms.FirstOrDefault(t => t.name == "Anchor_Boat");
                Transform boatRoot = transforms.FirstOrDefault(t => t.name == "ReturningBoat");
                AddCheck(report, "boat-mooring-anchor", boatAnchor != null && boatRoot != null && Vector3.Distance(boatAnchor.position,boatRoot.position)<.001f && Quaternion.Angle(boatAnchor.rotation,boatRoot.rotation)<.01f,
                    "Anchor matches the actual moored boat root pose.");
                foreach (string name in RequiredNames.Where(n => n.StartsWith("Anchor_Lamp_", StringComparison.Ordinal)))
                {
                    Transform lamp = transforms.FirstOrDefault(t => t.name == name);
                    Transform head = lamp == null ? null : lamp.Find("LampHead");
                    AddCheck(report, "lamp-pivot:" + name, lamp != null && head != null &&
                        Quaternion.Angle(lamp.localRotation, Quaternion.identity) < .01f && head.localPosition.sqrMagnitude < .00001f,
                        "Anchor has identity rotation; LampHead local origin is the swivel; only LampHead rotates.");
                }
                Transform windows = transforms.FirstOrDefault(t => t.name == "Village_Windows");
                report.windows = windows == null ? 0 : windows.childCount;
                AddCheck(report,"village-story-centre",windows != null && Vector3.Distance(windows.position,new Vector3(-13,8.4f,10))<.001f,
                    "Village_Windows parent is the village story centre; child window poses remain preserved.");
                AddCheck(report, "independent-village-windows", report.windows >= 20,
                    "At least two separately switchable windows for each of ten houses: " + report.windows);
                foreach (string name in new[] { "Sky_ScatterZone_Village", "Sky_ScatterZone_Pier" })
                {
                    BoxCollider c = transforms.FirstOrDefault(t => t.name == name)?.GetComponent<BoxCollider>();
                    AddCheck(report, "trigger:" + name, c != null && c.isTrigger && c.size.x > 0 && c.size.y > 0 && c.size.z > 0,
                        "Positive-size BoxCollider trigger.");
                }
                Transform boundary = transforms.FirstOrDefault(t => t.name == "Walkable_Boundary");
                bool closed = boundary != null && boundary.childCount >= 4 &&
                    Vector3.Distance(boundary.GetChild(0).position, boundary.GetChild(boundary.childCount - 1).position) < .001f;
                AddCheck(report, "closed-boundary", closed, "Ordered Point_ children repeat the first point at the end; no visible line in normal play.");
                Transform pierBoundary = transforms.FirstOrDefault(t => t.name == "PierBoundary");
                bool pierClosed = pierBoundary != null && pierBoundary.childCount >= 4 &&
                    Vector3.Distance(pierBoundary.GetChild(0).position, pierBoundary.GetChild(pierBoundary.childCount - 1).position) < .001f;
                AddCheck(report, "closed-pier-boundary", pierClosed, "Separate ordered pier footprint. Traversable area is land boundary OR PierBoundary, not a mixed point sequence.");
                RecordImportBounds(data, report);
                CheckTextureImports(data, report);
                CheckAuthoredMarkers(island, data, report);
                Physics.SyncTransforms();
                CheckBeamRays(island, report);
                string[] dependencies = AssetDatabase.GetDependencies(PrefabPath, true);
                AddCheck(report, "no-legacy-game-dependency", !dependencies.Any(p => p.StartsWith("Assets/BorrowedLight/", StringComparison.Ordinal)),
                    "The new Island prefab does not reference old BorrowedLight assets.");
                report.status = report.checks.All(c => c.passed) ? "passed-structural-checks" : "failed-structural-checks";
                report.warnings.Add("Static validation does not establish sustained 1440x900 performance, all-route navigation, animation fit, or final lighting quality.");
                Directory.CreateDirectory(EvidenceDirectory);
                File.WriteAllText(Path.Combine(EvidenceDirectory, "validation.json"), JsonUtility.ToJson(report, true));
                if (report.checks.Any(c => !c.passed))
                    throw new InvalidOperationException("EnvV1 structural checks failed: " + string.Join(", ", report.checks.Where(c => !c.passed).Select(c => c.name)));
                Debug.Log("[EnvV1] Structural validation passed. Evidence: art/verification/env-v1/validation.json");
            }
            finally
            {
                if (island != null) Object.DestroyImmediate(island);
                EditorSceneManager.ClosePreviewScene(preview);
            }
        }

        [MenuItem("JieGuang/Environment/3 Capture Four Views 1440x900")]
        public static void Capture()
        {
            AssertEditorIdle();
            InputData data = ReadInput();
            GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (source == null) throw new FileNotFoundException("Build Island before capture.", PrefabPath);
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(TestScenePath) == null)
                throw new FileNotFoundException("Build EnvTest before capture.", TestScenePath);
            Scene previous = SceneManager.GetActiveScene();
            Scene preview = EditorSceneManager.OpenScene(TestScenePath,OpenSceneMode.Additive);
            SceneManager.SetActiveScene(preview);
            GameObject island = null;
            var report = new CaptureReport {
                status = "in-progress", utc = DateTime.UtcNow.ToString("o"),
                scope = "Four fixed offscreen editor renders of the saved additive EnvTest scene with its own night RenderSettings. Camera.scene restricts culling; previous active scene is restored and never saved. No runtime frame-time measurement or gameplay validation."
            };
            try
            {
                island = preview.GetRootGameObjects().Single(go => go.name == "Island");
                Camera camera = preview.GetRootGameObjects().SelectMany(go => go.GetComponentsInChildren<Camera>(true)).FirstOrDefault();
                if (camera == null) camera = island.transform.Find("Cam_Title").gameObject.AddComponent<Camera>();
                foreach (Camera other in preview.GetRootGameObjects().SelectMany(go => go.GetComponentsInChildren<Camera>(true)))
                    other.enabled = false;
                ConfigureCamera(camera);
                camera.scene = preview;
                camera.enabled = false;
                var names = new[] { "Cam_Title", "Cam_Puzzle", "Cam_Pier", "Cam_Village" };
                var files = new[] { "01-title.png", "02-cape.png", "03-pier.png", "04-village.png" };
                Directory.CreateDirectory(EvidenceDirectory);
                for (int i = 0; i < names.Length; i++)
                {
                    AnchorData a = data.anchors.FirstOrDefault(x => x.name == names[i]);
                    if (a == null) throw new InvalidOperationException("Screenshot anchor missing: " + names[i]);
                    camera.transform.SetPositionAndRotation(Vector(a.position), Quaternion.LookRotation(Direction(a.forward), Vector3.up));
                    camera.fieldOfView = a.fov > 0 ? a.fov : 45;
                    string method = RenderPng(camera, Path.Combine(EvidenceDirectory, files[i]));
                    report.images.Add(new CaptureRecord { file = files[i], camera = names[i], width = Width, height = Height, renderMethod = method });
                }
                report.status = "captured-awaiting-visual-review";
                Debug.Log("[EnvV1] Four 1440x900 captures written; inspect each image before accepting visual quality.");
            }
            finally
            {
                Directory.CreateDirectory(EvidenceDirectory);
                File.WriteAllText(Path.Combine(EvidenceDirectory, "captures.json"), JsonUtility.ToJson(report, true));
                if (previous.IsValid() && previous.isLoaded) SceneManager.SetActiveScene(previous);
                if (preview.IsValid() && preview.isLoaded) EditorSceneManager.CloseScene(preview,true);
            }
        }

        private static void AssertEditorIdle()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
                throw new InvalidOperationException("Run environment commands with the Editor idle, outside Play Mode/import/compilation.");
        }
        private static InputData ReadInput()
        {
            string input = Path.Combine(ProjectDirectory, Root, "scene-input.json");
            if (!File.Exists(input)) input = Path.Combine(RepositoryDirectory, "art/generated/env-v1/staging/scene-input.json");
            if (!File.Exists(input)) throw new FileNotFoundException("scene-input.json was not found.", input);
            InputData data = JsonUtility.FromJson<InputData>(File.ReadAllText(input));
            if (data == null) throw new InvalidDataException("scene-input.json is empty or invalid.");
            return data;
        }
        private static void CheckInput(InputData d)
        {
            if (d.models == null || d.materials == null || d.instances == null || d.anchors == null || d.boundary == null)
                throw new InvalidDataException("Input requires models, materials, instances, anchors and boundary arrays.");
            if (d.boundary.Length < 3) throw new InvalidDataException("boundary requires at least three {position:[x,y,z]} objects.");
            if (d.models.Select(m => m.id).Distinct().Count() != d.models.Length) throw new InvalidDataException("Duplicate model IDs.");
            if (d.instances.Select(m => m.name).Distinct().Count() != d.instances.Length) throw new InvalidDataException("Duplicate instance names.");
            if (d.anchors.Select(m => m.name).Distinct().Count() != d.anchors.Length) throw new InvalidDataException("Duplicate anchor names.");
            if (d.anchors.Count(a => a.kind == "lamp") != 3) throw new InvalidDataException("Exactly three lamp anchors are required.");
            var ids = new HashSet<string>(d.models.Select(m => m.id));
            if (!ids.Contains("copper_roadlamp")) throw new InvalidDataException("copper_roadlamp model is required.");
            foreach (ModelData m in d.models) { AssertAssetPath(m.path); if (!string.IsNullOrEmpty(m.lod1)) AssertAssetPath(m.lod1); }
            foreach (InstanceData i in d.instances)
            {
                if (!ids.Contains(i.asset)) throw new InvalidDataException("Missing model for " + i.name + ": " + i.asset);
                if (!AllowedGroups.Contains(i.group)) throw new InvalidDataException("Unsupported group: " + i.group);
                if (i.asset == "copper_roadlamp") throw new InvalidDataException("Copper lamps are created by the three anchors, not by instances.");
                if (i.scale <= 0) throw new InvalidDataException("Positive scale required for " + i.name);
                Vector(i.position);
            }
            foreach (string name in RequiredNames.Where(n => n != "Village_Windows" && n != "Walkable_Boundary"))
                if (!d.anchors.Any(a => a.name == name)) throw new InvalidDataException("Required anchor absent: " + name);
        }
        private static void AssertAssetPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path) || !path.StartsWith(Root + "/", StringComparison.Ordinal) || path.Contains("..") || path.Contains('\\'))
                throw new InvalidDataException("Asset must remain under " + Root + ": " + path);
        }
        private static void EnsureFolder(string path)
        {
            AssertAssetPath(path);
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = path.Substring(0, path.LastIndexOf('/'));
            if (parent != Root) EnsureFolder(parent);
            if (!AssetDatabase.IsValidFolder(parent)) throw new DirectoryNotFoundException("Stage the Environment root before running: " + parent);
            AssetDatabase.CreateFolder(parent, path.Substring(path.LastIndexOf('/') + 1));
        }
        private static T SaveOwnAsset<T>(T created, string path) where T : Object
        {
            AssertAssetPath(path);
            T existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing != null)
            {
                EditorUtility.CopySerialized(created, existing);
                Object.DestroyImmediate(created);
                EditorUtility.SetDirty(existing);
                AssetDatabase.SaveAssetIfDirty(existing);
                return existing;
            }
            AssetDatabase.CreateAsset(created, path);
            AssetDatabase.SaveAssetIfDirty(created);
            return created;
        }
        private static GameObject LoadModel(string path)
        {
            AssertAssetPath(path);
            var result = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (result == null) throw new FileNotFoundException("Stage/import this model before building.", path);
            return result;
        }
        private static void PrepareImports(InputData data)
        {
            Dictionary<string, bool> textureRoles = TextureImportRoles(data.materials);
            string[] paths = data.models.SelectMany(m => new[] { m.path, m.lod1 })
                .Where(p => !string.IsNullOrEmpty(p)).Distinct(StringComparer.Ordinal).ToArray();
            foreach (string path in paths)
            {
                AssertAssetPath(path);
                if (!(AssetImporter.GetAtPath(path) is ModelImporter importer))
                    throw new InvalidDataException("Expected a staged ModelImporter at own Environment path: " + path);
                bool changed = importer.importAnimation || importer.addCollider || !importer.isReadable;
                if (!changed) continue;
                // Deliberately retain globalScale/useFileScale/bakeAxisConversion and every other authoring setting.
                importer.importAnimation = false;
                importer.addCollider = false;
                importer.isReadable = true;
                importer.SaveAndReimport();
                BuildWarnings.Add("Prepared own model import: animation off, generated colliders off, Read/Write on; existing axis/scale preserved: " + path);
            }
            foreach (KeyValuePair<string, bool> role in textureRoles)
            {
                if (!(AssetImporter.GetAtPath(role.Key) is TextureImporter importer))
                    throw new InvalidDataException("Expected a staged TextureImporter at own Environment path: " + role.Key);
                bool changed = importer.sRGBTexture != role.Value || !importer.mipmapEnabled || importer.maxTextureSize < 2048;
                if (!changed) continue;
                importer.sRGBTexture = role.Value;
                importer.mipmapEnabled = true;
                importer.maxTextureSize = Mathf.Max(importer.maxTextureSize, 2048);
                importer.SaveAndReimport();
                BuildWarnings.Add("Prepared own texture import: " + (role.Value ? "sRGB BaseColor" : "linear emission") +
                    ", mipmaps on, max size at least 2048 (larger existing limit preserved): " + role.Key);
            }
        }
        private static Dictionary<string, bool> TextureImportRoles(MaterialData[] materials)
        {
            var roles = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
            foreach (MaterialData material in materials)
            {
                string[] paths = { material.texture, material.emissionTexture };
                for (int i = 0; i < paths.Length; i++)
                {
                    string path = paths[i];
                    if (string.IsNullOrEmpty(path)) continue;
                    AssertAssetPath(path);
                    bool srgb = i == 0;
                    if (roles.TryGetValue(path, out bool prior) && prior != srgb)
                        throw new InvalidDataException("One texture path cannot be both sRGB BaseColor and linear emission: " + path);
                    roles[path] = srgb;
                }
            }
            return roles;
        }
        private static void CheckTextureImports(InputData data, Report report)
        {
            foreach (KeyValuePair<string, bool> role in TextureImportRoles(data.materials))
            {
                TextureImporter importer = AssetImporter.GetAtPath(role.Key) as TextureImporter;
                AddCheck(report,"texture-import:"+role.Key,importer != null && importer.sRGBTexture == role.Value &&
                    importer.mipmapEnabled && importer.maxTextureSize >= 2048,
                    "Expected " + (role.Value ? "sRGB BaseColor" : "linear emission") + ", mipmaps enabled and maximum texture size >= 2048. Source textures smaller than this limit are not upscaled.");
            }
        }
        private static void RecordImportBounds(InputData data, Report report)
        {
            foreach (ModelData model in data.models)
            {
                RecordImportBounds(model.id, model.path, "LOD0", report);
                if (!string.IsNullOrEmpty(model.lod1)) RecordImportBounds(model.id, model.lod1, "LOD1", report);
            }
        }
        private static void RecordImportBounds(string id, string path, string lod, Report report)
        {
            GameObject model = LoadModel(path);
            MeshFilter[] filters = model.GetComponentsInChildren<MeshFilter>(true);
            var record = new ImportRecord { id = id, path = path, lod = lod, meshes = filters.Length,
                rootLocalPosition = Array(model.transform.localPosition), rootLocalEuler = Array(model.transform.localEulerAngles),
                rootLocalScale = Array(model.transform.localScale) };
            bool first = true;
            Bounds bounds = new Bounds();
            foreach (MeshFilter filter in filters)
            {
                if (filter.sharedMesh == null) continue;
                Mesh mesh = filter.sharedMesh;
                for (int i = 0; i < mesh.subMeshCount; i++) record.triangles += (long)mesh.GetIndexCount(i) / 3;
                Bounds b = mesh.bounds;
                // Asset-root local scale/rotation must be included, rather than cancelled by worldToLocalMatrix.
                Matrix4x4 matrix = filter.transform.localToWorldMatrix;
                for (int x=-1; x<=1; x+=2) for (int y=-1; y<=1; y+=2) for (int z=-1; z<=1; z+=2)
                {
                    Vector3 point = matrix.MultiplyPoint3x4(b.center + Vector3.Scale(b.extents,new Vector3(x,y,z)));
                    if (first) { bounds = new Bounds(point,Vector3.zero); first = false; } else bounds.Encapsulate(point);
                }
            }
            record.boundsCenter = Array(bounds.center);
            record.boundsSize = Array(bounds.size);
            if (AssetImporter.GetAtPath(path) is ModelImporter importer)
            {
                record.importAnimation = importer.importAnimation;
                record.addCollider = importer.addCollider;
                record.isReadable = importer.isReadable;
                record.globalScale = importer.globalScale;
                record.useFileScale = importer.useFileScale;
                record.bakeAxisConversion = importer.bakeAxisConversion;
                AddCheck(report,"import-settings:"+id+":"+lod,
                    !importer.importAnimation && !importer.addCollider && importer.isReadable,
                    "Own ModelImporter: animation off, generated collider off, Read/Write on. Axis/scale are recorded, not changed.");
            }
            report.imports.Add(record);
            AddCheck(report,"import-bounds:"+id+":"+lod,!first && record.triangles>0 &&
                record.boundsSize.All(v => !float.IsNaN(v) && !float.IsInfinity(v)) && bounds.size.sqrMagnitude>.000001f,
                "Effective imported bounds in metres, including imported root scale/rotation: " + bounds.size.ToString("F4"));
        }
        private static void CheckAuthoredMarkers(GameObject island, InputData data, Report report)
        {
            CheckAuthoredMarker(island,data,report,"abode_grandma",new[] {"Marker_Window"},"Target_Window");
            CheckAuthoredMarker(island,data,report,"abode_grandma",new[] {"Marker_ABo_Seat"},"NPC_ABo_Window");
            CheckAuthoredMarker(island,data,report,"flagpole_blue",new[] {"Marker_FlagpoleHook","Marker_Hook"},"Anchor_FlagpoleHook");
            CheckAuthoredMarker(island,data,report,"bench",new[] {"Marker_Seat"},"NPC_Bench");
            CheckAuthoredMarker(island,data,report,"dock_crate",new[] {"Marker_Seat"},"NPC_DengBo_Box");
        }
        private static void CheckAuthoredMarker(GameObject island, InputData data, Report report,
            string asset, string[] acceptedMarkers, string targetName)
        {
            InstanceData[] matches = data.instances.Where(i => i.asset==asset).ToArray();
            if (matches.Length!=1)
            {
                AddCheck(report,"marker:"+targetName,false,"Expected exactly one instance of "+asset+" for an unambiguous authored marker comparison.");
                return;
            }
            InstanceData item=matches[0];
            Transform instance=island.transform.Find(item.group+"/"+item.name);
            Transform marker=instance==null ? null : instance.GetComponentsInChildren<Transform>(true)
                .FirstOrDefault(t => acceptedMarkers.Contains(t.name));
            Transform target=island.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name==targetName);
            if (marker==null || target==null)
            {
                AddCheck(report,"marker:"+targetName,false,"Missing imported marker "+string.Join(" or ",acceptedMarkers)+" or destination anchor.");
                return;
            }
            float distance=Vector3.Distance(marker.position,target.position);
            const float tolerance=.025f;
            report.markerComparisons.Add(new MarkerRecord {
                instance=item.name, marker=marker.name, anchor=targetName,
                actualWorldPosition=Array(marker.position),anchorWorldPosition=Array(target.position),
                actualWorldForward=Array(marker.forward),anchorWorldForward=Array(target.forward),
                distanceMetres=distance,forwardAngleDegrees=Vector3.Angle(marker.forward,target.forward),toleranceMetres=tolerance
            });
            AddCheck(report,"marker:"+targetName,distance<=tolerance,
                "Imported "+item.name+"/"+marker.name+" versus anchor: "+distance.ToString("F5")+" m; tolerance 0.025 m. Forward angle is recorded for review, not assumed from FBX empty-axis conventions.");
        }
        private static Dictionary<string, Material> MakeMaterials(MaterialData[] entries)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("URP/Lit shader is unavailable; this tool does not change render pipeline settings.");
            var result = new Dictionary<string, Material>(StringComparer.Ordinal);
            foreach (MaterialData data in entries)
            {
                if (result.ContainsKey(data.name)) throw new InvalidDataException("Duplicate material name: " + data.name);
                var material = new Material(shader) { name = data.name, enableInstancing = true };
                material.SetColor("_BaseColor", ColorValue(data.color, Color.white));
                material.SetFloat("_Metallic", Mathf.Clamp01(data.metallic));
                material.SetFloat("_Smoothness", 1 - Mathf.Clamp01(data.roughness));
                if (!string.IsNullOrEmpty(data.texture)) material.SetTexture("_BaseMap", LoadTexture(data.texture));
                if (data.strength > 0)
                {
                    material.EnableKeyword("_EMISSION");
                    material.SetColor("_EmissionColor", ColorValue(data.emission, Color.black) * data.strength);
                    if (!string.IsNullOrEmpty(data.emissionTexture)) material.SetTexture("_EmissionMap", LoadTexture(data.emissionTexture));
                    // URP's material validator disables _EMISSION when neither
                    // emissive flag is set. This marks the surface emissive; no
                    // lighting bake is requested and no realtime GI is enabled.
                    material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
                }
                result.Add(data.name, SaveOwnAsset(material, Root + "/Generated/Materials/" + SafeName(data.name) + ".mat"));
            }
            return result;
        }
        private static Texture2D LoadTexture(string path)
        {
            AssertAssetPath(path);
            Texture2D t = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (t == null) throw new FileNotFoundException("Texture is missing or not imported.", path);
            return t;
        }
        private static GameObject CloneModel(GameObject source, Transform parent, string name, Dictionary<string, Material> materials)
        {
            GameObject model = Object.Instantiate(source, parent, false);
            model.name = name;
            // Blender FBX imports reflect local X when converting handedness. The
            // authored layout and marker contract use (Blender x,z,-y), so undo
            // that reflection inside each asset, leaving instance/world poses intact.
            Vector3 importedPosition = model.transform.localPosition;
            Quaternion importedRotation = model.transform.localRotation;
            Vector3 importedScale = model.transform.localScale;
            model.transform.localPosition = new Vector3(-importedPosition.x,importedPosition.y,importedPosition.z);
            model.transform.localRotation = new Quaternion(importedRotation.x,-importedRotation.y,-importedRotation.z,importedRotation.w);
            model.transform.localScale = new Vector3(-importedScale.x,importedScale.y,importedScale.z);
            foreach (Light unwanted in model.GetComponentsInChildren<Light>(true)) Object.DestroyImmediate(unwanted);
            foreach (Camera unwanted in model.GetComponentsInChildren<Camera>(true)) Object.DestroyImmediate(unwanted);
            foreach (Collider unwanted in model.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(unwanted);
            // Separate LOD FBX files may carry importer-created LODGroups. The instance
            // owns the only authoritative group combining the two files.
            foreach (LODGroup unwanted in model.GetComponentsInChildren<LODGroup>(true)) Object.DestroyImmediate(unwanted);
            foreach (Renderer renderer in model.GetComponentsInChildren<Renderer>(true))
            {
                Material[] mapped = renderer.sharedMaterials;
                for (int i = 0; i < mapped.Length; i++)
                {
                    string key = mapped[i] == null ? "" : mapped[i].name.Replace(" (Instance)", "");
                    if (!materials.TryGetValue(key, out Material replacement))
                    {
                        int dot = key.LastIndexOf('.');
                        bool duplicateSuffix = dot > 0 && key.Length-dot == 4 && int.TryParse(key.Substring(dot+1),out int suffix);
                        if (!duplicateSuffix || !materials.TryGetValue(key.Substring(0,dot),out replacement))
                            throw new InvalidDataException("No material mapping for '" + key + "' on " + source.name + "/" + renderer.name);
                        string note = "Blender duplicate material suffix mapped: " + key + " -> " + key.Substring(0,dot);
                        if (!BuildWarnings.Contains(note)) BuildWarnings.Add(note);
                    }
                    mapped[i] = replacement;
                }
                renderer.sharedMaterials = mapped;
                renderer.shadowCastingMode = ShadowCastingMode.On;
                renderer.receiveShadows = true;
                renderer.lightProbeUsage = LightProbeUsage.Off;
                renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }
            return model;
        }
        private static void AddCollision(GameObject instance, GameObject high, InstanceData item, ModelData model)
        {
            if (item.collider == "none") return;
            if (model.kind == "terrain" || item.group == "Terrain")
            {
                foreach (MeshFilter filter in high.GetComponentsInChildren<MeshFilter>(true))
                {
                    bool cliff = filter.name.IndexOf("Cliff", StringComparison.OrdinalIgnoreCase) >= 0;
                    bool path = filter.name.IndexOf("Path", StringComparison.OrdinalIgnoreCase) >= 0;
                    filter.gameObject.layer = cliff ? SolidLayer : GroundLayer;
                    if (!path && filter.sharedMesh != null)
                    {
                        MeshCollider mesh = filter.gameObject.AddComponent<MeshCollider>();
                        mesh.sharedMesh = filter.sharedMesh;
                        mesh.convex = false;
                    }
                }
                return;
            }
            if (item.asset == "pier_module" || item.asset == "pier_end")
            {
                GameObject deck = Child(instance.transform, "WalkableDeck");
                deck.layer = GroundLayer;
                BoxCollider box = deck.AddComponent<BoxCollider>();
                box.center = new Vector3(0, -.1f, 0);
                box.size = new Vector3(2.4f, .2f, item.asset == "pier_end" ? 3.6f : 3f);
                SetLayerRecursive(high.transform, GroundLayer);
                return;
            }
            if (item.asset == "abode_grandma" || item.asset == "bench" || item.collider == "ground")
            {
                foreach (MeshFilter filter in high.GetComponentsInChildren<MeshFilter>(true))
                {
                    filter.gameObject.layer = item.collider == "ground" ? GroundLayer : SolidLayer;
                    if (filter.sharedMesh == null || filter.name.StartsWith("Window_", StringComparison.Ordinal)) continue;
                    MeshCollider mesh = filter.gameObject.AddComponent<MeshCollider>();
                    mesh.sharedMesh = filter.sharedMesh;
                    mesh.convex = false;
                }
                return;
            }
            Bounds bounds = LocalBounds(instance.transform, high.GetComponentsInChildren<MeshFilter>(true));
            GameObject collision = Child(instance.transform, "SolidCollision");
            collision.layer = SolidLayer;
            BoxCollider solid = collision.AddComponent<BoxCollider>();
            if (model.kind.IndexOf("tree", StringComparison.OrdinalIgnoreCase) >= 0 || item.group == "Forest")
            {
                float height = Mathf.Min(2.2f, bounds.size.y * .6f);
                float width = Mathf.Clamp(Mathf.Min(bounds.size.x, bounds.size.z) * .13f, .2f, .65f);
                solid.center = new Vector3(0, bounds.min.y + height * .5f, 0);
                solid.size = new Vector3(width, height, width);
            }
            else if (item.asset == "flagpole_blue")
            {
                solid.center = new Vector3(0, Mathf.Min(2, bounds.size.y) * .5f, 0);
                solid.size = new Vector3(.22f, Mathf.Min(2, bounds.size.y), .22f);
            }
            else { solid.center = bounds.center; solid.size = bounds.size; }
            SetLayerRecursive(high.transform, SolidLayer);
        }
        private static Bounds LocalBounds(Transform localTo, MeshFilter[] filters)
        {
            bool first = true;
            Bounds total = new Bounds(Vector3.zero, Vector3.zero);
            foreach (MeshFilter mf in filters)
            {
                if (mf.sharedMesh == null) continue;
                Bounds b = mf.sharedMesh.bounds;
                Matrix4x4 matrix = localTo.worldToLocalMatrix * mf.transform.localToWorldMatrix;
                for (int x = -1; x <= 1; x += 2) for (int y = -1; y <= 1; y += 2) for (int z = -1; z <= 1; z += 2)
                {
                    Vector3 p = matrix.MultiplyPoint3x4(b.center + Vector3.Scale(b.extents, new Vector3(x, y, z)));
                    if (first) { total = new Bounds(p, Vector3.zero); first = false; } else total.Encapsulate(p);
                }
            }
            return total;
        }
        private static void ExtractWindows(Transform source, Transform windows, string houseName)
        {
            Transform[] found = source.GetComponentsInChildren<Transform>(true)
                .Where(t => t.name.StartsWith("Window_", StringComparison.Ordinal)).ToArray();
            foreach (Transform window in found)
            {
                window.name = houseName + "_" + window.name;
                window.SetParent(windows, true);
            }
        }
        private static void CombineVillage(Transform village, Transform island)
        {
            var groups = new Dictionary<Material, List<CombineInstance>>();
            MeshRenderer[] renderers = village.GetComponentsInChildren<MeshRenderer>(true);
            foreach (MeshRenderer renderer in renderers)
            {
                MeshFilter mf = renderer.GetComponent<MeshFilter>();
                if (!renderer.enabled || mf == null || mf.sharedMesh == null || HasAncestor(renderer.transform, "LOD1")) continue;
                Material[] mats = renderer.sharedMaterials;
                for (int i = 0; i < mf.sharedMesh.subMeshCount; i++)
                {
                    if (i >= mats.Length || mats[i] == null) throw new InvalidDataException("Village submesh material is missing.");
                    if (!groups.TryGetValue(mats[i], out List<CombineInstance> list)) groups.Add(mats[i], list = new List<CombineInstance>());
                    list.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = i,
                        transform = island.worldToLocalMatrix * mf.transform.localToWorldMatrix });
                }
                renderer.enabled = false; // Keep the original collider/transform hierarchy intact.
            }
            Transform batches = Child(island, "Village_Batches").transform;
            foreach (var entry in groups)
            {
                Mesh mesh = new Mesh { name = "Village_" + entry.Key.name, indexFormat = IndexFormat.UInt32 };
                mesh.CombineMeshes(entry.Value.ToArray(), true, true, false);
                // CombineMeshes bakes reflected transforms but does not reverse
                // triangle winding. Every village model has the same X correction.
                if (entry.Value.All(c => c.transform.determinant < 0))
                {
                    int[] triangles = mesh.triangles;
                    for (int t = 0; t < triangles.Length; t += 3)
                    { int tmp = triangles[t+1]; triangles[t+1] = triangles[t+2]; triangles[t+2] = tmp; }
                    mesh.triangles = triangles;
                    Vector4[] tangents = mesh.tangents;
                    for (int t = 0; t < tangents.Length; t++) tangents[t].w *= -1;
                    if (tangents.Length > 0) mesh.tangents = tangents;
                }
                else if (entry.Value.Any(c => c.transform.determinant < 0))
                    throw new InvalidOperationException("Village batch contains mixed handedness; bake each source before combining.");
                mesh.RecalculateBounds();
                Mesh asset = SaveOwnAsset(mesh, Root + "/Generated/Meshes/" + SafeName(mesh.name) + ".asset");
                GameObject go = Child(batches, "Batch_" + entry.Key.name);
                go.layer = SolidLayer;
                go.AddComponent<MeshFilter>().sharedMesh = asset;
                go.AddComponent<MeshRenderer>().sharedMaterial = entry.Key;
            }
        }
        private static void MakeLamp(GameObject anchor, AnchorData data, GameObject source, Dictionary<string, Material> materials)
        {
            anchor.transform.localRotation = Quaternion.identity;
            GameObject temporary = CloneModel(source, anchor.transform, "LampSource", materials);
            Transform sourceStructure = temporary.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Structure");
            Transform sourceHead = temporary.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "LampHead");
            if (sourceStructure == null || sourceHead == null) throw new InvalidDataException("copper_roadlamp requires Structure and LampHead meshes.");
            Transform structure = Child(anchor.transform, "Structure").transform;
            sourceStructure.SetParent(structure, true);
            sourceStructure.name = "CopperColumn";
            structure.localScale = new Vector3(1, (data.height > 0 ? data.height : 3.8f) / 3.8f, 1);
            Transform head = Child(anchor.transform, "LampHead").transform;
            sourceHead.SetParent(head, true);
            sourceHead.name = "CopperHood";
            head.localRotation = Quaternion.LookRotation(Direction(data.forward), Vector3.up);
            Object.DestroyImmediate(temporary);
            SetLayerRecursive(structure, SolidLayer);
            GameObject columnCollision = Child(structure, "ColumnCollision");
            columnCollision.layer = SolidLayer;
            BoxCollider collision = columnCollision.AddComponent<BoxCollider>();
            collision.center = new Vector3(0, -1.9f, 0);
            collision.size = new Vector3(.24f, 3.8f, .24f);
            GameObject lightObject = Child(head, "Spot");
            lightObject.transform.localPosition = new Vector3(0, 0, .29f);
            Light light = lightObject.AddComponent<Light>();
            light.type = LightType.Spot;
            light.color = new Color(1, .69f, .34f);
            light.intensity = 16;
            light.range = 18;
            light.spotAngle = data.name == "Anchor_Lamp_WanFeng" ? 56 : 24;
            light.innerSpotAngle = light.spotAngle * .8f;
            light.shadows = LightShadows.Soft;
            light.shadowStrength = .8f;
            light.shadowBias = .035f;
            light.shadowNormalBias = .1f;
            light.bounceIntensity = 0;
        }
        private static void MakeBoundary(Transform island, PointData[] points)
        {
            Transform boundary = Child(island, "Walkable_Boundary").transform;
            var positions = points.Select(p => Vector(p.position)).ToList();
            if (Vector3.Distance(positions[0], positions[positions.Count - 1]) > .001f) positions.Add(positions[0]);
            for (int i = 0; i < positions.Count; i++) Child(boundary, "Point_" + i.ToString("D3")).transform.localPosition = positions[i];
        }
        private static void MakePierBoundary(Transform island, InstanceData[] instances)
        {
            InstanceData[] decks = instances.Where(i => i.asset == "pier_module" || i.asset == "pier_end").ToArray();
            if (decks.Length == 0) throw new InvalidDataException("PierBoundary requires at least one pier deck instance.");
            var corners = new List<Vector3>();
            foreach (InstanceData deck in decks)
            {
                float length = deck.asset == "pier_end" ? 3.6f : 3f;
                Vector3 origin = Vector(deck.position);
                Quaternion rotation = Quaternion.Euler(0, deck.yaw, 0);
                foreach (int x in new[] { -1, 1 }) foreach (int z in new[] { -1, 1 })
                    corners.Add(origin + rotation * (new Vector3(x * 1.2f, 0, z * length * .5f) * deck.scale));
            }
            // The authored modules form one straight, continuous dock. A convex footprint is exact for that layout.
            // Refuse bent/disconnected assumptions instead of silently filling a large region of sea.
            float referenceYaw = decks[0].yaw;
            if (decks.Any(d => Mathf.Abs(Mathf.DeltaAngle(d.yaw, referenceYaw)) > .01f))
                throw new InvalidDataException("Bent pier requires an explicit non-convex boundary; automatic hull only supports this scene's straight dock.");
            Quaternion inverse = Quaternion.Inverse(Quaternion.Euler(0, referenceYaw, 0));
            Vector3 referencePosition = Vector(decks[0].position);
            var intervals = decks.Select(d => {
                Vector3 delta = inverse * (Vector(d.position) - referencePosition);
                if (Mathf.Abs(delta.x) > .01f || Mathf.Abs(delta.y) > .01f)
                    throw new InvalidDataException("Pier modules must share a straight centerline and deck height.");
                float half = (d.asset == "pier_end" ? 1.8f : 1.5f) * d.scale;
                return new Vector2(delta.z-half,delta.z+half);
            }).OrderBy(v => v.x).ToArray();
            float end = intervals[0].y;
            for (int i = 1; i < intervals.Length; i++)
            {
                if (intervals[i].x > end + .01f) throw new InvalidDataException("Pier modules have a gap; collision/footprint would not be continuous.");
                end = Mathf.Max(end, intervals[i].y);
            }
            Vector3[] points = corners.OrderBy(p => p.x).ThenBy(p => p.z).ToArray();
            var hull = new List<Vector3>();
            foreach (Vector3 p in points)
            {
                while (hull.Count >= 2 && CrossXZ(hull[hull.Count-2],hull[hull.Count-1],p) <= .000001f) hull.RemoveAt(hull.Count-1);
                hull.Add(p);
            }
            int lowerCount = hull.Count;
            for (int i = points.Length-2; i >= 0; i--)
            {
                Vector3 p = points[i];
                while (hull.Count > lowerCount && CrossXZ(hull[hull.Count-2],hull[hull.Count-1],p) <= .000001f) hull.RemoveAt(hull.Count-1);
                hull.Add(p);
            }
            Transform boundary = Child(island, "PierBoundary").transform;
            for (int i = 0; i < hull.Count; i++) Child(boundary,"Point_"+i.ToString("D3")).transform.localPosition = hull[i];
        }
        private static float CrossXZ(Vector3 a, Vector3 b, Vector3 c)
        { return (b.x-a.x)*(c.z-a.z)-(b.z-a.z)*(c.x-a.x); }
        private static void MakeAtmosphere(Transform island)
        {
            Transform group = Child(island, "Atmosphere").transform;
            Shader skyShader = Shader.Find("JieGuang/Environment/NightSky");
            Shader seaShader = Shader.Find("JieGuang/Environment/NightSea");
            if (skyShader == null || seaShader == null) throw new InvalidOperationException("Stage both Environment shaders before building.");
            Material sky = new Material(skyShader) { name = "NightSky" };
            sky.SetVector("_EarthDirection", new Vector4(-.30f, .15f, .94f, 0));
            sky = SaveOwnAsset(sky, Root + "/Generated/Materials/NightSky.mat");
            GameObject skyObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            skyObject.name = "NightSky";
            skyObject.transform.SetParent(group, false);
            skyObject.transform.localScale = Vector3.one * 360;
            Object.DestroyImmediate(skyObject.GetComponent<Collider>());
            skyObject.GetComponent<Renderer>().sharedMaterial = sky;
            skyObject.GetComponent<Renderer>().shadowCastingMode = ShadowCastingMode.Off;
            skyObject.GetComponent<Renderer>().receiveShadows = false;
            Material sea = SaveOwnAsset(new Material(seaShader) { name = "NightSea" }, Root + "/Generated/Materials/NightSea.mat");
            var seaMesh = new Mesh { name = "NightSea" };
            seaMesh.vertices = new[] { new Vector3(-150,-.16f,-150),new Vector3(-150,-.16f,150),new Vector3(150,-.16f,150),new Vector3(150,-.16f,-150) };
            seaMesh.uv = new[] { Vector2.zero,Vector2.up,Vector2.one,Vector2.right };
            seaMesh.triangles = new[] { 0,1,2,0,2,3 };
            seaMesh.RecalculateNormals(); seaMesh.RecalculateBounds();
            GameObject water = Child(group, "NightSea");
            water.AddComponent<MeshFilter>().sharedMesh = SaveOwnAsset(seaMesh, Root + "/Generated/Meshes/NightSea.asset");
            MeshRenderer waterRenderer = water.AddComponent<MeshRenderer>();
            waterRenderer.sharedMaterial = sea;
            waterRenderer.shadowCastingMode = ShadowCastingMode.Off;
            waterRenderer.receiveShadows = false;
            MakeDirectional(group, "WarmEnvironmentKey", new Vector3(42,-28,0), .6f, new Color(1,.86f,.67f), true);
            MakeDirectional(group, "WarmEnvironmentFill", new Vector3(32,145,0), .25f, new Color(1,.91f,.77f), false);
        }
        private static void MakeDirectional(Transform parent, string name, Vector3 angles, float intensity, Color color, bool shadows)
        {
            GameObject go = Child(parent, name);
            go.transform.localRotation = Quaternion.Euler(angles);
            Light light = go.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = intensity;
            light.color = color;
            light.shadows = shadows ? LightShadows.Soft : LightShadows.None;
            light.shadowStrength = .6f;
            light.shadowNormalBias = .2f;
            light.bounceIntensity = 0;
        }
        private static void CreateTestCamera(Transform island, InputData data)
        {
            AnchorData title = data.anchors.First(a => a.name == "Cam_Title");
            Camera camera = new GameObject("EnvTestCamera").AddComponent<Camera>();
            camera.transform.SetPositionAndRotation(Vector(title.position), Quaternion.LookRotation(Direction(title.forward), Vector3.up));
            ConfigureCamera(camera);
            camera.fieldOfView = title.fov > 0 ? title.fov : 45;
        }
        private static void ConfigureCamera(Camera camera)
        {
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(.006f,.013f,.032f,1);
            camera.nearClipPlane = .08f;
            camera.farClipPlane = 450;
            camera.allowHDR = false;
            camera.allowMSAA = true;
            camera.aspect = (float)Width / Height;
        }
        private static string RenderPng(Camera camera, string path)
        {
            RenderTexture target = RenderTexture.GetTemporary(Width, Height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB, 1);
            RenderTexture previous = RenderTexture.active;
            RenderTexture oldTarget = camera.targetTexture;
            Texture2D pixels = null;
            try
            {
                camera.targetTexture = target;
                string method;
                if (GraphicsSettings.currentRenderPipeline != null)
                {
                    var request = new RenderPipeline.StandardRequest { destination = target };
                    if (!RenderPipeline.SupportsRenderRequest(camera, request))
                        throw new NotSupportedException("Active render pipeline does not support StandardRequest. Capture manually in EnvTest; do not change pipeline settings.");
                    RenderPipeline.SubmitRenderRequest(camera, request);
                    method = "RenderPipeline.StandardRequest";
                }
                else { camera.Render(); method = "Camera.Render (built-in pipeline)"; }
                RenderTexture.active = target;
                pixels = new Texture2D(Width, Height, TextureFormat.RGB24, false, false);
                pixels.ReadPixels(new Rect(0,0,Width,Height),0,0,false);
                pixels.Apply(false,false);
                File.WriteAllBytes(path, pixels.EncodeToPNG());
                return method;
            }
            finally
            {
                if (pixels != null) Object.DestroyImmediate(pixels);
                camera.targetTexture = oldTarget;
                RenderTexture.active = previous;
                RenderTexture.ReleaseTemporary(target);
            }
        }
        private static void CheckBeamRays(GameObject island, Report report)
        {
            Transform[] all = island.GetComponentsInChildren<Transform>(true);
            var pairs = new[] {
                new[] { "Anchor_Lamp_WanFeng", "Target_Path" },
                new[] { "Anchor_Lamp_WanFeng", "Target_Bench" },
                new[] { "Anchor_Lamp_YueChuang", "Target_Window" },
                new[] { "Anchor_Lamp_YueChuang", "Target_Pier" },
                new[] { "Anchor_Lamp_GuiHang", "Target_Bench" }
            };
            Collider[] own = island.GetComponentsInChildren<Collider>(true).Where(c => !c.isTrigger && c.enabled).ToArray();
            foreach (string[] pair in pairs)
            {
                Transform lamp = all.FirstOrDefault(t => t.name == pair[0]);
                Transform target = all.FirstOrDefault(t => t.name == pair[1]);
                if (lamp == null || target == null) continue;
                Vector3 delta = target.position - lamp.position;
                Ray ray = new Ray(lamp.position + delta.normalized * .45f, delta.normalized);
                float distance = Mathf.Max(0, delta.magnitude - .8f);
                var blockers = new List<string>();
                foreach (Collider collider in own)
                {
                    if (collider.transform.IsChildOf(lamp)) continue;
                    if (collider.Raycast(ray, out RaycastHit hit, distance)) blockers.Add(FullPath(collider.transform, island.transform));
                }
                AddCheck(report, "beam-clear:" + pair[0] + "->" + pair[1], blockers.Count == 0,
                    blockers.Count == 0 ? "No own non-trigger collider before target; 35 cm receiver tolerance." : string.Join("; ", blockers));
            }
        }
        private static void AddCheck(Report report, string name, bool passed, string detail)
        { report.checks.Add(new Check { name = name, passed = passed, detail = detail }); }
        private static GameObject Child(Transform parent, string name)
        { var go = new GameObject(name); go.transform.SetParent(parent, false); return go; }
        private static bool HasAncestor(Transform node, string name)
        { for (Transform t = node; t != null; t = t.parent) if (t.name == name) return true; return false; }
        private static void SetLayerRecursive(Transform node, int layer)
        { foreach (Transform t in node.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer; }
        private static Vector3 Vector(float[] values)
        {
            if (values == null || values.Length < 3 || values.Take(3).Any(v => float.IsNaN(v) || float.IsInfinity(v)))
                throw new InvalidDataException("Expected a finite [x,y,z] array.");
            return new Vector3(values[0], values[1], values[2]);
        }
        private static Vector3 Direction(float[] values)
        { Vector3 direction = values == null ? Vector3.forward : Vector(values); return direction.sqrMagnitude < .000001f ? Vector3.forward : direction.normalized; }
        private static Color ColorValue(float[] values, Color fallback)
        { return values == null || values.Length < 3 ? fallback : new Color(values[0],values[1],values[2],values.Length > 3 ? values[3] : 1); }
        private static float[] Array(Vector3 value) { return new[] { value.x,value.y,value.z }; }
        private static string SafeName(string name)
        { foreach (char c in Path.GetInvalidFileNameChars()) name = name.Replace(c,'_'); return name.Replace('/','_').Replace('\\','_'); }
        private static string FullPath(Transform transform, Transform root)
        {
            var names = new List<string>();
            for (Transform t = transform; t != null && t != root; t = t.parent) names.Add(t.name);
            names.Reverse(); return string.Join("/", names);
        }
    }
}
#endif
