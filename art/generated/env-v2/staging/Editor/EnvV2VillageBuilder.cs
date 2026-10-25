#if UNITY_EDITOR
// Explicit offline-authored integration helper. No menu, load hook, scene/prefab save or global rendering writes.
// Invoke only on the caller's fully unpacked Island in a disposable, unsaved candidate scene.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV2VillageBuilder
    {
        const string Root = "Assets/JieGuang/Environment/";
        const string OwnedName = "__EnvV2VillageBatches";
        const float PoseTolerance = .002f;
        const int HouseCount = 11, WindowCount = 22, MaxAdditionalTrianglesPerHouse = 700;
        static readonly string[] TypeIds = { "cottage_teal", "cottage_ochre", "cottage_slate" };
        static readonly int[] HouseTypes = { 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1 };
        static readonly string[] Roofs = { "AgedTeal", "OchreRed", "WarmSlate" };
        static readonly string[] Highlights = { "TealHighlight", "RedHighlight", "SlateHighlight" };

        [Serializable] public sealed class Check { public string name, detail; public bool passed; }
        [Serializable] public sealed class Mapping { public string source, destination, assetPath; }
        [Serializable] public sealed class ModelResult
        {
            public string type, sourceAsset, sourceGuid, orientation;
            public int instances, oldStructureTriangles, newStructureTriangles, additionalPerHouse, weightedAdditional;
            public float worstAsImportedMarkerError, worstReflectedMarkerError, worstChosenMarkerError, worstWindowVertexError;
        }
        [Serializable] public sealed class InterfaceRecord
        {
            public string path, kind, payload;
            public int componentInstanceId, meshInstanceId;
            public float[] worldMatrix;
        }
        [Serializable] public sealed class Report
        {
            public string status, generationPath, reportAssetPath;
            public int houses, windowsBefore, windowsAfter, boxCollidersBefore, boxCollidersAfter;
            public int markerCountBefore, markerCountAfter, protectedTransforms, originalBatchRenderersRemoved;
            public int sharedMaterials, newBatchRenderers, oldVisibleStructureTriangles, newVisibleStructureTriangles;
            public int preservedWindowTriangles, additionalTriangles, totalVillageTrianglesIncludingWindows;
            public int preservedDisabledStructureTriangles, actualBatchTriangleDelta;
            public int allMeshFiltersBefore, allMeshFiltersAfter;
            public long allMeshFilterTrianglesBefore, expectedAllMeshFilterTrianglesAfter, allMeshFilterTrianglesAfter;
            public long villageAllMeshFilterTrianglesBefore, villageAllMeshFilterTrianglesAfter;
            public List<ModelResult> models = new List<ModelResult>();
            public List<Mapping> materialMapping = new List<Mapping>();
            public List<InterfaceRecord> before = new List<InterfaceRecord>(), after = new List<InterfaceRecord>();
            public List<Check> checks = new List<Check>();
            public List<string> meshAssets = new List<string>(), warnings = new List<string>();
            public string geometryDeduplication = "Only candidate Structure submeshes are read once per house. Imported Window_00/01 and Marker_Door are measured but never instantiated or batched. Old visible batch renderer/filter components are removed from this candidate only; their assets and GameObjects remain. Per-material vertex indexing reuses a source vertex within the same house, including mapped slots sharing that material; no cross-house welding or decorative face removal.";
        }

        /// <summary>
        /// Reads three already-imported ModelsV2/{cottage_*}_v2_candidate.fbx assets.
        /// Builds only this disposable candidate's visible village and preserves original interfaces.
        /// generatedFolder must be under Environment/Generated; woodTexturePath must be an owned Texture2D.
        /// Caller must discard the disposable candidate scene on any exception. This method never saves it.
        /// </summary>
        public static Report Build(GameObject island, string generatedFolder, string woodTexturePath)
        {
            ValidateCandidate(island);
            generatedFolder = OwnedPath(generatedFolder, Root + "Generated/").TrimEnd('/');
            woodTexturePath = OwnedPath(woodTexturePath, Root);
            Need(AssetDatabase.LoadAssetAtPath<Texture2D>(woodTexturePath) != null, "Import the owned wood texture first.");
            Transform village = Direct(island.transform, "Village");
            Transform windows = Direct(island.transform, "Village_Windows");
            Transform batches = Direct(island.transform, "Village_Batches");
            Need(batches.Find(OwnedName) == null, "Already integrated. Start from a fresh unpacked baseline candidate; never accumulate duplicate village geometry.");
            Need(village.childCount == HouseCount && windows.childCount == WindowCount, "Expected exactly 11 original houses and 22 direct story windows.");
            Need(MatrixError(batches.localToWorldMatrix, island.transform.localToWorldMatrix) < .000001f,
                "Village_Batches must retain its original identity pose relative to Island.");

            var report = new Report { status = "preflight", houses = HouseCount };
            report.allMeshFiltersBefore = island.GetComponentsInChildren<MeshFilter>(true).Length;
            report.allMeshFilterTrianglesBefore = AllMeshFilterTriangles(island.transform);
            report.villageAllMeshFilterTrianglesBefore = AllMeshFilterTriangles(village) + AllMeshFilterTriangles(windows) + AllMeshFilterTriangles(batches);
            var oldBatches = batches.GetComponentsInChildren<MeshRenderer>(true);
            Need(oldBatches.Length == 14 && batches.childCount == 14, "Expected the 14 original v1 village material batches.");
            foreach (MeshRenderer renderer in oldBatches)
            {
                Need(renderer.transform.parent == batches && renderer.name.StartsWith("Batch_", StringComparison.Ordinal)
                    && renderer.enabled && renderer.sharedMaterials.Length == 1 && renderer.sharedMaterial != null,
                    "Unexpected original batch layout; refusing to remove unrelated rendering components.");
                MeshFilter filter = renderer.GetComponent<MeshFilter>();
                Need(filter != null && filter.sharedMesh != null && renderer.GetComponents<Collider>().Length == 0,
                    "An original batch must have a mesh and no collision component.");
                report.oldVisibleStructureTriangles += Triangles(filter.sharedMesh);
            }
            Need(batches.GetComponentsInChildren<MeshFilter>(true).Length == 14, "Unexpected extra batch MeshFilters.");
            var removable = new HashSet<Component>(oldBatches.Cast<Component>().Concat(oldBatches.Select(r => (Component)r.GetComponent<MeshFilter>())));
            var protectedState = new ProtectedState(island, removable);
            var materials = new Dictionary<string, Material>(StringComparer.Ordinal);
            var houses = new House[HouseCount];
            for (int i = 0; i < HouseCount; ++i)
            {
                string name = "VillageHouse_" + (i + 1).ToString("00");
                Transform house = Direct(village, name), lod = Direct(house, "LOD0");
                MeshFilter structure = Direct(lod, "Structure").GetComponent<MeshFilter>();
                MeshRenderer renderer = structure == null ? null : structure.GetComponent<MeshRenderer>();
                Need(structure != null && structure.sharedMesh != null && renderer != null && !renderer.enabled,
                    "Original disabled Structure is required: " + name);
                Need(Triangles(structure.sharedMesh) == 1000, "Expected frozen v1 1000-triangle Structure: " + name);
                report.preservedDisabledStructureTriangles += Triangles(structure.sharedMesh);
                Need(house.GetComponentsInChildren<MeshRenderer>(true).Length == 1 && house.GetComponentsInChildren<MeshFilter>(true).Length == 1,
                    "Village source hierarchy changed or still contains windows: " + name);
                string[] slots = Slots(HouseTypes[i]);
                ValidateSlots(structure.sharedMesh, renderer.sharedMaterials, slots, name);
                for (int m = 0; m < slots.Length; ++m)
                {
                    if (materials.TryGetValue(slots[m], out Material existing))
                        Need(existing == renderer.sharedMaterials[m], "Original material is not shared consistently: " + slots[m]);
                    else materials.Add(slots[m], renderer.sharedMaterials[m]);
                }
                Transform marker = Unique(lod, "Marker_Door");
                Need(house.GetComponentsInChildren<Transform>(true).Count(t => t.name.StartsWith("Marker_", StringComparison.Ordinal)) == 1,
                    "Unexpected village Marker interface: " + name);
                var box = Direct(house, "SolidCollision").GetComponent<BoxCollider>();
                Need(box != null && box.enabled && !box.isTrigger && box.gameObject.layer == 9
                    && house.GetComponentsInChildren<Collider>(true).Length == 1, "Keep one original Layer 9 solid BoxCollider per house.");
                var windowFilters = new MeshFilter[2];
                for (int w = 0; w < 2; ++w)
                {
                    Transform window = Direct(windows, name + "_Window_" + w.ToString("00"));
                    MeshRenderer wr = window.GetComponent<MeshRenderer>(); windowFilters[w] = window.GetComponent<MeshFilter>();
                    Need(wr != null && wr.enabled && windowFilters[w] != null && windowFilters[w].sharedMesh != null
                        && wr.sharedMaterials.Length == 1 && wr.sharedMaterial != null && Clean(wr.sharedMaterial.name) == "Window_AmberEmission"
                        && window.GetComponentsInChildren<Collider>(true).Length == 0 && window.gameObject.layer == 9,
                        "A story window must retain its own direct Renderer, mesh, emission material and no collider: " + window.name);
                    Need(Triangles(windowFilters[w].sharedMesh) == 12, "Original window should have 12 triangles.");
                    report.preservedWindowTriangles += 12;
                }
                houses[i] = new House { transform = house, marker = marker, type = HouseTypes[i], windows = windowFilters };
            }
            Need(village.GetComponentsInChildren<Collider>(true).Length == HouseCount && report.oldVisibleStructureTriangles == 11000,
                "Frozen original visible village geometry/collision count mismatch.");
            report.before = InterfaceRecords(island.transform, village, windows);
            report.windowsBefore = windows.childCount;
            report.boxCollidersBefore = village.GetComponentsInChildren<BoxCollider>(true).Length;
            report.markerCountBefore = island.GetComponentsInChildren<Transform>(true).Count(IsMarker);
            report.protectedTransforms = protectedState.transforms;

            // Pure asset reads and measurements precede all generated asset/material or scene mutations.
            Source[] sources = Enumerable.Range(0, 3).Select(LoadSource).ToArray();
            for (int t = 0; t < sources.Length; ++t)
            {
                Source source = sources[t];
                var item = new ModelResult { type = TypeIds[t], sourceAsset = source.path, sourceGuid = AssetDatabase.AssetPathToGUID(source.path),
                    instances = houses.Count(h => h.type == t), oldStructureTriangles = 1000, newStructureTriangles = Triangles(source.mesh) };
                item.additionalPerHouse = item.newStructureTriangles - item.oldStructureTriangles;
                Need(item.additionalPerHouse >= 0 && item.additionalPerHouse <= MaxAdditionalTrianglesPerHouse,
                    "New Structure must preserve the baseline and add at most 700 triangles: " + TypeIds[t]);
                item.weightedAdditional = item.instances * item.additionalPerHouse;
                bool? choice = null;
                foreach (House house in houses.Where(h => h.type == t))
                {
                    Matrix4x4 imported = house.transform.localToWorldMatrix * source.importedRoot;
                    Matrix4x4 reflected = house.transform.localToWorldMatrix * source.reflectedRoot;
                    float a = MatrixError(house.marker.localToWorldMatrix, imported * source.markerToRoot);
                    float b = MatrixError(house.marker.localToWorldMatrix, reflected * source.markerToRoot);
                    bool reflect = b < a;
                    Need(Mathf.Min(a, b) <= PoseTolerance && Mathf.Max(a, b) > .05f,
                        "Marker_Door does not unambiguously determine import orientation: " + house.transform.name);
                    Need(!choice.HasValue || choice.Value == reflect, "A single model requires inconsistent orientation across village instances.");
                    choice = reflect; house.sourceWorld = reflect ? reflected : imported;
                    item.worstAsImportedMarkerError = Mathf.Max(item.worstAsImportedMarkerError, a);
                    item.worstReflectedMarkerError = Mathf.Max(item.worstReflectedMarkerError, b);
                    item.worstChosenMarkerError = Mathf.Max(item.worstChosenMarkerError, Mathf.Min(a, b));
                    for (int w = 0; w < 2; ++w)
                    {
                        Matrix4x4 candidateWindow = house.sourceWorld * source.windowToRoot[w];
                        Need(MatrixError(candidateWindow, house.windows[w].transform.localToWorldMatrix) <= PoseTolerance,
                            "Candidate window pose differs from the original story window: " + house.windows[w].name);
                        float error = VertexSetError(house.windows[w], source.windows[w].sharedMesh, candidateWindow);
                        item.worstWindowVertexError = Mathf.Max(item.worstWindowVertexError, error);
                        Need(error <= PoseTolerance, "Candidate changed the preserved window geometry: " + house.windows[w].name);
                    }
                }
                item.orientation = choice.Value ? "measured-reflected-import-root-X" : "measured-as-imported";
                report.models.Add(item); report.additionalTriangles += item.weightedAdditional;
                report.newVisibleStructureTriangles += item.instances * item.newStructureTriangles;
            }
            Need(report.models.Select(x => x.instances).SequenceEqual(new[] { 4, 4, 3 }) && report.additionalTriangles <= 7700,
                "Village type/geometry budget exceeded.");
            report.totalVillageTrianglesIncludingWindows = report.newVisibleStructureTriangles + report.preservedWindowTriangles;
            // The stored original disabled Structures remain real MeshFilter instances and stay in the all-mesh budget.
            // The only deductible geometry is the measured old Village_Batches whose filters are actually removed below.
            report.actualBatchTriangleDelta = report.newVisibleStructureTriangles - report.oldVisibleStructureTriangles;
            Need(report.actualBatchTriangleDelta == report.additionalTriangles, "Per-model delta disagrees with the actual removed old batch geometry.");
            report.expectedAllMeshFilterTrianglesAfter = report.allMeshFilterTrianglesBefore + report.actualBatchTriangleDelta;
            Need(report.expectedAllMeshFilterTrianglesAfter <= 600000, "This village integration would exceed the 600k all-MeshFilter-instance budget, including disabled/rendererless meshes and every LOD.");
            CheckPassed(report, "source-orientation-and-window-geometry", "All 11 Marker_Door matrices and 22 source-window poses/vertex sets align within 2 mm; source windows are validation inputs only.");
            CheckPassed(report, "source-and-weighted-triangle-budget", "Each original Structure is 1000 triangles; each candidate adds 0..700; type counts 4/4/3, whole village additional <=7700.");

            report.generationPath = generatedFolder + "/Village_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff") + "_" + Guid.NewGuid().ToString("N").Substring(0, 8);
            EnsureFolder(report.generationPath);
            var wood = EnvV2HouseSurfaceBuilder.Prepare(woodTexturePath, report.generationPath + "/Wood");
            var groups = new Dictionary<Material, List<Part>>();
            for (int i = 0; i < houses.Length; ++i)
            {
                House house = houses[i]; Source source = sources[house.type];
                Matrix4x4 matrix = island.transform.worldToLocalMatrix * house.sourceWorld * source.structureToRoot;
                Need(Mathf.Abs(matrix.determinant) > .000001f, "Degenerate source-to-island transform.");
                for (int s = 0; s < source.mesh.subMeshCount; ++s)
                {
                    if (source.mesh.GetIndexCount(s) == 0) continue;
                    string key = Clean(source.renderer.sharedMaterials[s].name);
                    Material chosen = wood.TryGetValue(key, out Material textured) ? textured : materials[key];
                    if (!groups.TryGetValue(chosen, out List<Part> parts)) groups.Add(chosen, parts = new List<Part>());
                    parts.Add(new Part { house = i, mesh = source.mesh, submesh = s, matrix = matrix });
                    if (!report.materialMapping.Any(m => m.source == key)) report.materialMapping.Add(new Mapping {
                        source = key, destination = chosen.name, assetPath = AssetDatabase.GetAssetPath(chosen) });
                }
            }
            Need(groups.Count > 0 && groups.Count <= 16, "Visible village exceeds the 16 shared-material budget.");
            report.sharedMaterials = groups.Count;
            GameObject newRoot = null;
            try
            {
                newRoot = new GameObject(OwnedName); newRoot.SetActive(false); newRoot.transform.SetParent(batches, false); newRoot.layer = 9;
                int combinedTriangles = 0;
                foreach (var pair in groups.OrderBy(p => p.Key.name, StringComparer.Ordinal))
                {
                    Mesh mesh = Combine(pair.Value, "VillageV2_" + pair.Key.name);
                    combinedTriangles += Triangles(mesh);
                    string path = report.generationPath + "/" + mesh.name + ".asset";
                    Need(AssetDatabase.LoadMainAssetAtPath(path) == null, "Refusing to overwrite a mesh asset.");
                    AssetDatabase.CreateAsset(mesh, path); AssetDatabase.SaveAssetIfDirty(mesh); report.meshAssets.Add(path);
                    GameObject child = new GameObject("Batch_" + pair.Key.name); child.transform.SetParent(newRoot.transform, false); child.layer = 9;
                    child.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var renderer = child.AddComponent<MeshRenderer>(); renderer.sharedMaterial = pair.Key;
                    renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true;
                    // No lightmap/static flags are copied: these meshes have no newly baked lightmaps.
                }
                Need(combinedTriangles == report.newVisibleStructureTriangles, "Combined mesh duplicated or lost triangles.");
                protectedState.Verify();
                // Commit last. These are components on this detached candidate only, never their referenced mesh/material assets.
                foreach (MeshRenderer renderer in oldBatches)
                {
                    MeshFilter filter = renderer.GetComponent<MeshFilter>();
                    Object.DestroyImmediate(renderer); Object.DestroyImmediate(filter);
                }
                newRoot.SetActive(true);
                protectedState.Verify();
                report.after = InterfaceRecords(island.transform, village, windows);
                Need(JsonUtility.ToJson(new Records { values = report.before }) == JsonUtility.ToJson(new Records { values = report.after }),
                    "A preserved window, collider or Marker interface changed.");
                report.windowsAfter = windows.childCount;
                report.boxCollidersAfter = village.GetComponentsInChildren<BoxCollider>(true).Length;
                report.markerCountAfter = island.GetComponentsInChildren<Transform>(true).Count(IsMarker);
                report.originalBatchRenderersRemoved = oldBatches.Length; report.newBatchRenderers = newRoot.GetComponentsInChildren<MeshRenderer>(true).Length;
                report.allMeshFiltersAfter = island.GetComponentsInChildren<MeshFilter>(true).Length;
                report.allMeshFilterTrianglesAfter = AllMeshFilterTriangles(island.transform);
                report.villageAllMeshFilterTrianglesAfter = AllMeshFilterTriangles(village) + AllMeshFilterTriangles(windows) + AllMeshFilterTriangles(batches);
                Need(report.allMeshFilterTrianglesAfter == report.expectedAllMeshFilterTrianglesAfter && report.allMeshFilterTrianglesAfter <= 600000,
                    "Actual all-MeshFilter-instance triangle budget differs from the measured old-batch/new-batch delta or exceeds 600k.");
                Need(report.allMeshFiltersAfter == report.allMeshFiltersBefore - oldBatches.Length + groups.Count
                    && report.villageAllMeshFilterTrianglesAfter == report.villageAllMeshFilterTrianglesBefore + report.actualBatchTriangleDelta
                    && report.villageAllMeshFilterTrianglesAfter == report.preservedDisabledStructureTriangles + report.totalVillageTrianglesIncludingWindows,
                    "A retained disabled Structure or another original MeshFilter was incorrectly removed from the budget.");
                Need(village.GetComponentsInChildren<MeshRenderer>(true).All(r => !r.enabled)
                    && batches.GetComponentsInChildren<MeshRenderer>(true).Length == groups.Count,
                    "Old/new visible geometry would be rendered twice.");
                CheckPassed(report, "all-original-transform-and-renderer-contracts", "All original transform references, parents, local/world matrices, name, sibling order, layer and active state retained; all non-batch Renderer/MeshFilter component identities and serialized values retained.");
                CheckPassed(report, "windows-colliders-markers-identical", "Original 22 direct story windows, all original island Colliders and Markers retain component identity, mesh/material references, serialized settings and world pose. Village retains the original 11 BoxColliders, not new mesh collision.");
                CheckPassed(report, "old-rendering-removed-without-asset-deletion", "Only 14 old batch Renderer/MeshFilter pairs removed from this candidate; old batch transforms, disabled house Structures and all referenced assets retained.");
                CheckPassed(report, "triangle-dedup-and-material-budget", "Combined triangle sum equals 11 new Structures exactly; 264 original window triangles remain separate; " + groups.Count + " shared opaque batch materials (limit 16).");
                CheckPassed(report, "all-meshfilter-budget-including-retained-structure", "All MeshFilter instances counted with includeInactive=true, regardless of Renderer existence/enabled state; all LODs and retained 11000-triangle disabled village Structures stay counted. Delta equals new batches minus the measured old batches actually removed. The whole candidate must be counted again after subsequent builders run.");
                report.status = "built-and-structurally-checked-in-disposable-candidate-awaiting-rendered-validation";
                report.warnings.Add("Runtime contract checks are not image, shader, gameplay or FPS validation. This helper's initial delivery was offline C# compilation only.");
                report.warnings.Add("Old village BoxColliders deliberately remain unchanged. New roof/trim/chimney details are visual geometry, without new collision.");
                report.warnings.Add("Four wood materials are new generation-local assets. EnvV2HouseSurfaceBuilder configures the explicitly supplied owned texture importer. Other shared materials/importers are read-only.");
                report.warnings.Add("No prefab/scene save, AssetDatabase.SaveAssets, global RenderSettings write, gameplay mutation, source FBX instantiation or source-asset deletion occurs.");
                report.reportAssetPath = report.generationPath + "/village-report.json";
                File.WriteAllText(ProjectFile(report.reportAssetPath), JsonUtility.ToJson(report, true), new System.Text.UTF8Encoding(false));
                return report;
            }
            catch
            {
                if (newRoot != null) Object.DestroyImmediate(newRoot);
                // Generated assets intentionally remain available for failure diagnosis. The caller must discard its disposable scene,
                // including a rare failure after commit; recreating removed components would not preserve their object identities.
                throw;
            }
        }

        sealed class House { public Transform transform, marker; public int type; public MeshFilter[] windows; public Matrix4x4 sourceWorld; }
        sealed class Source
        {
            public string path; public Mesh mesh; public MeshRenderer renderer; public MeshFilter[] windows;
            public Matrix4x4 importedRoot, reflectedRoot, markerToRoot, structureToRoot;
            public Matrix4x4[] windowToRoot;
        }
        sealed class Part { public int house, submesh; public Mesh mesh; public Matrix4x4 matrix; }
        [Serializable] sealed class Records { public List<InterfaceRecord> values; }

        static Source LoadSource(int type)
        {
            string path = Root + "ModelsV2/" + TypeIds[type] + "_v2_candidate.fbx";
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            Need(asset != null && EditorUtility.IsPersistent(asset), "Import the candidate FBX before invoking: " + path);
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            Need(importer != null && importer.isReadable && !importer.importAnimation && !importer.addCollider,
                "Importer must be readable, animations disabled, addCollider false. Caller prepares only owned ModelsV2 assets; this helper changes no FBX importer.");
            Transform root = asset.transform, structure = Unique(root, "Structure"), marker = Unique(root, "Marker_Door");
            Need(root.name == TypeIds[type] || root.name == TypeIds[type] + "_v2_candidate", "Unexpected source model root name: " + root.name);
            Need(asset.GetComponentsInChildren<MeshFilter>(true).Length == 3 && asset.GetComponentsInChildren<Renderer>(true).Length == 3
                && asset.GetComponentsInChildren<Collider>(true).Length == 0
                && asset.GetComponentsInChildren<Transform>(true).Count(IsMarker) == 1,
                "Expected only Structure, two Window meshes and one Marker_Door in " + path);
            MeshFilter filter = structure.GetComponent<MeshFilter>(); var renderer = structure.GetComponent<MeshRenderer>();
            Need(filter != null && renderer != null && filter.sharedMesh != null && filter.sharedMesh.isReadable, "Readable source Structure is required.");
            ValidateSlots(filter.sharedMesh, renderer.sharedMaterials, Slots(type), path);
            Need(filter.sharedMesh.vertices.Length == filter.sharedMesh.normals.Length && filter.sharedMesh.vertices.Length == filter.sharedMesh.uv.Length,
                "Source Structure needs real normals and authored UV0; no invented UVs/upward normals.");
            Vector3 p = root.localPosition, scale = root.localScale; Quaternion q = root.localRotation;
            var result = new Source { path = path, mesh = filter.sharedMesh, renderer = renderer,
                importedRoot = Matrix4x4.TRS(p, q, scale),
                reflectedRoot = Matrix4x4.TRS(new Vector3(-p.x, p.y, p.z), new Quaternion(q.x, -q.y, -q.z, q.w), new Vector3(-scale.x, scale.y, scale.z)),
                markerToRoot = root.worldToLocalMatrix * marker.localToWorldMatrix,
                structureToRoot = root.worldToLocalMatrix * structure.localToWorldMatrix,
                windows = new MeshFilter[2], windowToRoot = new Matrix4x4[2] };
            for (int w = 0; w < 2; ++w)
            {
                Transform window = Unique(root, "Window_" + w.ToString("00")); var wr = window.GetComponent<MeshRenderer>();
                MeshFilter wf = window.GetComponent<MeshFilter>();
                Need(wf != null && wf.sharedMesh != null && wf.sharedMesh.isReadable && Triangles(wf.sharedMesh) == 12 && wr != null
                    && wr.sharedMaterials.Length == 1 && wr.sharedMaterial != null && Clean(wr.sharedMaterial.name) == "Window_AmberEmission",
                    "Candidate source must retain each 12-triangle window and its original material identity.");
                result.windows[w] = wf; result.windowToRoot[w] = root.worldToLocalMatrix * window.localToWorldMatrix;
            }
            return result;
        }

        static Mesh Combine(List<Part> parts, string name)
        {
            var vertices = new List<Vector3>(); var normals = new List<Vector3>(); var uv = new List<Vector2>(); var triangles = new List<int>();
            var remap = new Dictionary<(int house, int mesh, int vertex), int>();
            foreach (Part part in parts)
            {
                Vector3[] v = part.mesh.vertices, n = part.mesh.normals; Vector2[] tex = part.mesh.uv;
                Need(v.Length == n.Length && v.Length == tex.Length, "Source normals and UV0 are required.");
                Matrix4x4 normalMatrix = part.matrix.inverse.transpose;
                int[] sourceTriangles = part.mesh.GetTriangles(part.submesh); bool reflected = part.matrix.determinant < 0;
                foreach (int i in sourceTriangles.Distinct())
                {
                    var key = (part.house, part.mesh.GetInstanceID(), i);
                    if (remap.ContainsKey(key)) continue;
                    Vector3 normal = normalMatrix.MultiplyVector(n[i]);
                    Need(normal.sqrMagnitude > .00000001f && Finite(normal) && Finite(v[i]) && Finite(tex[i]), "Invalid authored vertex/normal/UV.");
                    remap.Add(key, vertices.Count); vertices.Add(part.matrix.MultiplyPoint3x4(v[i])); normals.Add(normal.normalized); uv.Add(tex[i]);
                }
                for (int i = 0; i < sourceTriangles.Length; i += 3)
                {
                    triangles.Add(remap[(part.house, part.mesh.GetInstanceID(), sourceTriangles[i])]);
                    triangles.Add(remap[(part.house, part.mesh.GetInstanceID(), sourceTriangles[i + (reflected ? 2 : 1)])]);
                    triangles.Add(remap[(part.house, part.mesh.GetInstanceID(), sourceTriangles[i + (reflected ? 1 : 2)])]);
                }
            }
            var result = new Mesh { name = name, indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            result.SetVertices(vertices); result.SetNormals(normals); result.SetUVs(0, uv); result.SetTriangles(triangles, 0, false);
            result.RecalculateBounds(); result.RecalculateTangents(); // Tangent handedness derives from already-correct winding and original UV0.
            return result;
        }

        sealed class ProtectedState
        {
            sealed class Pose
            {
                public Transform reference, parent; public string name; public int sibling, layer; public bool active;
                public Vector3 position, scale; public Quaternion rotation; public Matrix4x4 world;
            }
            sealed class ComponentState { public Component reference; public string json; }
            readonly Pose[] poses; readonly ComponentState[] components;
            public int transforms => poses.Length;
            public ProtectedState(GameObject island, HashSet<Component> removable)
            {
                poses = island.GetComponentsInChildren<Transform>(true).Select(t => new Pose { reference = t, parent = t.parent, name = t.name,
                    sibling = t.GetSiblingIndex(), layer = t.gameObject.layer, active = t.gameObject.activeSelf,
                    position = t.localPosition, rotation = t.localRotation, scale = t.localScale, world = t.localToWorldMatrix }).ToArray();
                components = island.GetComponentsInChildren<Component>(true)
                    .Where(c => c != null && (c is Collider || c is Renderer || c is MeshFilter) && !removable.Contains(c))
                    .Select(c => new ComponentState { reference = c, json = EditorJsonUtility.ToJson(c) }).ToArray();
            }
            public void Verify()
            {
                foreach (Pose p in poses)
                {
                    Transform t = p.reference;
                    Need(t != null && t.parent == p.parent && t.name == p.name && t.GetSiblingIndex() == p.sibling && t.gameObject.layer == p.layer
                        && t.gameObject.activeSelf == p.active && t.localPosition.Equals(p.position) && t.localRotation.Equals(p.rotation)
                        && t.localScale.Equals(p.scale) && t.localToWorldMatrix.Equals(p.world), "Protected original transform changed: " + p.name);
                }
                foreach (ComponentState c in components) Need(c.reference != null && EditorJsonUtility.ToJson(c.reference) == c.json,
                    "Protected original collision/rendering component changed.");
            }
        }

        static List<InterfaceRecord> InterfaceRecords(Transform island, Transform village, Transform windows)
        {
            var records = new List<InterfaceRecord>();
            foreach (Transform t in windows)
            {
                var renderer = t.GetComponent<MeshRenderer>(); var filter = t.GetComponent<MeshFilter>();
                records.Add(new InterfaceRecord { path = PathOf(t, island), kind = "story-window", componentInstanceId = renderer.GetInstanceID(),
                    meshInstanceId = filter.sharedMesh.GetInstanceID(), worldMatrix = MatrixValues(t.localToWorldMatrix), payload = EditorJsonUtility.ToJson(renderer) });
            }
            foreach (BoxCollider c in village.GetComponentsInChildren<BoxCollider>(true)) records.Add(new InterfaceRecord {
                path = PathOf(c.transform, island), kind = "original-box-collider", componentInstanceId = c.GetInstanceID(),
                worldMatrix = MatrixValues(c.transform.localToWorldMatrix), payload = EditorJsonUtility.ToJson(c) });
            foreach (Transform t in island.GetComponentsInChildren<Transform>(true).Where(IsMarker)) records.Add(new InterfaceRecord {
                path = PathOf(t, island), kind = "original-marker", componentInstanceId = t.GetInstanceID(), worldMatrix = MatrixValues(t.localToWorldMatrix) });
            return records.OrderBy(r => r.path, StringComparer.Ordinal).ThenBy(r => r.kind, StringComparer.Ordinal).ToList();
        }
        static void ValidateCandidate(GameObject island)
        {
            Need(!EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isCompiling && !EditorApplication.isUpdating,
                "Editor must be idle; caller must own Unity and complete status/pipeline checks before invoking.");
            Need(island != null && !EditorUtility.IsPersistent(island) && island.scene.IsValid() && island.scene.isLoaded
                && string.IsNullOrEmpty(island.scene.path) && island.transform.parent == null && island.name == "Island",
                "Only an explicit detached Island root in the caller's disposable unsaved scene is supported.");
            Need(PrefabStageUtility.GetCurrentPrefabStage() == null && !island.GetComponentsInChildren<Transform>(true).Any(t => PrefabUtility.IsPartOfPrefabInstance(t.gameObject)),
                "Unpack the candidate completely; no prefab asset, prefab instance or Prefab Mode edits.");
            Need(island.transform.localPosition == Vector3.zero && island.transform.localRotation == Quaternion.identity
                && island.transform.localScale == Vector3.one, "Candidate root must retain original identity transform.");
        }
        static string[] Slots(int type) => new[] { "Stone_SoftGrey", type == 1 ? "Wall_LightTimber" : "Wall_WarmIvory", "Wood_DarkBeams", "Wood_Endgrain", "Wood_Honey", "Copper_Aged", "Stone_WarmLimestone", "Roof_" + Roofs[type], "Roof_" + Highlights[type] };
        static void ValidateSlots(Mesh mesh, Material[] materials, string[] slots, string label)
        {
            Need(mesh.subMeshCount == slots.Length && materials.Length == slots.Length, "Expected nine material slots: " + label);
            for (int i = 0; i < slots.Length; ++i) Need(materials[i] != null && Clean(materials[i].name) == slots[i]
                && mesh.GetTopology(i) == MeshTopology.Triangles && mesh.GetIndexCount(i) % 3 == 0, "Unexpected material slot/topology " + i + ": " + label);
        }
        static float VertexSetError(MeshFilter original, Mesh candidate, Matrix4x4 candidateWorld)
        {
            Need(original.sharedMesh.isReadable, "Original windows must be readable for geometric comparison.");
            Vector3[] a = original.sharedMesh.vertices.Select(original.transform.TransformPoint).ToArray();
            Vector3[] b = candidate.vertices.Select(candidateWorld.MultiplyPoint3x4).ToArray();
            Need(a.Length > 0 && b.Length > 0 && Triangles(original.sharedMesh) == Triangles(candidate), "Window topology is missing or changed.");
            float worst = 0;
            foreach (Vector3 p in a) worst = Mathf.Max(worst, b.Min(q => Vector3.Distance(p, q)));
            foreach (Vector3 p in b) worst = Mathf.Max(worst, a.Min(q => Vector3.Distance(p, q)));
            return worst;
        }
        // Compare origin plus basis endpoints: catches position, rotation, scale and handedness, not just a coincident marker point.
        static float MatrixError(Matrix4x4 a, Matrix4x4 b)
        {
            float worst = 0;
            foreach (Vector3 v in new[] { Vector3.zero, Vector3.right, Vector3.up, Vector3.forward })
                worst = Mathf.Max(worst, Vector3.Distance(a.MultiplyPoint3x4(v), b.MultiplyPoint3x4(v)));
            return worst;
        }
        static float[] MatrixValues(Matrix4x4 m) => Enumerable.Range(0, 16).Select(i => m[i]).ToArray();
        static bool IsMarker(Transform t) => t.name.StartsWith("Marker_", StringComparison.Ordinal);
        static bool Finite(Vector3 v) => Finite(v.x) && Finite(v.y) && Finite(v.z);
        static bool Finite(Vector2 v) => Finite(v.x) && Finite(v.y);
        static bool Finite(float v) => !float.IsNaN(v) && !float.IsInfinity(v);
        static int Triangles(Mesh mesh)
        {
            long n = 0;
            for (int i = 0; i < mesh.subMeshCount; ++i) { Need(mesh.GetTopology(i) == MeshTopology.Triangles, "Triangle topology required."); n += mesh.GetIndexCount(i) / 3; }
            Need(n <= int.MaxValue, "Triangle count overflow."); return (int)n;
        }
        static long AllMeshFilterTriangles(Transform root) => root.GetComponentsInChildren<MeshFilter>(true)
            .Where(f => f.sharedMesh != null).Sum(f => (long)Triangles(f.sharedMesh));
        static string Clean(string s) => Regex.Replace(s.Replace(" (Instance)", ""), @"\.\d{3}$", "");
        static Transform Direct(Transform root, string name)
        {
            Transform[] matches = root.Cast<Transform>().Where(t => t.name == name).ToArray();
            Need(matches.Length == 1, "Expected one direct child " + name + " under " + root.name); return matches[0];
        }
        static Transform Unique(Transform root, string name)
        {
            Transform[] matches = root.GetComponentsInChildren<Transform>(true).Where(t => t.name == name).ToArray();
            Need(matches.Length == 1, "Expected one " + name + " in " + root.name); return matches[0];
        }
        static string PathOf(Transform t, Transform root)
        { var names = new List<string>(); for (; t != null && t != root; t = t.parent) names.Add(t.name); names.Reverse(); return string.Join("/", names); }
        static string OwnedPath(string path, string prefix)
        {
            Need(!string.IsNullOrWhiteSpace(path), "Owned asset path is required."); path = path.Replace('\\', '/');
            Need(path.StartsWith(prefix, StringComparison.Ordinal) && !path.Contains("..") && !path.Contains(":") && !path.Contains("//"),
                "Path must remain under " + prefix); return path;
        }
        static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            int split = folder.LastIndexOf('/'); string parent = folder.Substring(0, split);
            Need(folder.StartsWith(Root + "Generated/", StringComparison.Ordinal), "Only generation folders may be created.");
            Need(AssetDatabase.IsValidFolder(parent) || parent.StartsWith(Root + "Generated/", StringComparison.Ordinal), "Create the Environment/Generated root before invoking.");
            if (!AssetDatabase.IsValidFolder(parent)) EnsureFolder(parent);
            Need(!string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent, folder.Substring(split + 1))), "Could not create owned generation folder.");
        }
        static string ProjectFile(string path) => Path.GetFullPath(Path.Combine(Directory.GetParent(Application.dataPath).FullName, path));
        static void CheckPassed(Report report, string name, string detail) => report.checks.Add(new Check { name = name, passed = true, detail = detail });
        static void Need(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
#endif
