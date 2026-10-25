#if UNITY_EDITOR
// Explicit, read-only prefab verification. Does not run during import or save any Unity asset/scene.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV1GroundChecks
    {
        private const string PrefabPath = "Assets/JieGuang/Environment/Island.prefab";
        private const int GroundLayer = 8;
        private const float AnchorTolerance = .03f;

        [Serializable] public sealed class GroundReport
        {
            public string status = "in-progress", utc, prefab = PrefabPath;
            public string scope = "Downward rays against this prefab's enabled, non-trigger layer-8 colliders only, in an isolated preview scene. Three newly requested foot/root anchors require an absolute height delta <= 0.03 m. Other samples require a hit with an upward-facing normal; their height deltas are observations, not acceptance thresholds.";
            public string deltaDefinition = "deltaY = anchor world Y minus closest downward ground-hit world Y. Positive means above ground; negative means below ground. Road probes have no reference Y.";
            public string boundsDefinition = "Corrected scene/world bounds of the instantiated Terrain subtree, including the clone's reflection correction. These are not the raw imported FBX bounds.";
            public bool previousQueriesHitBackfaces, testedQueriesHitBackfaces;
            public int groundColliderCount, passedSamples, failedSamples;
            public BoundsRecord correctedTerrainBounds, correctedTerrainGroundBounds;
            public List<BoundsRecord> terrainMeshes = new List<BoundsRecord>();
            public List<SampleRecord> samples = new List<SampleRecord>();
            public List<string> errors = new List<string>();
            public List<string> limitations = new List<string> {
                "Finite point samples do not prove that every route is traversable or that character capsules fit.",
                "Layer-9 buildings, props and rocks are deliberately excluded from the ground-height query."
            };
        }

        [Serializable] public sealed class SampleRecord
        {
            public string name, kind, colliderPath, detail;
            public bool foundAnchor, hasReferenceY, enforceHeight, hit, upwardNormal, passed;
            public int anchorMatches, testedColliders;
            public float toleranceMetres, groundY, deltaY, rayLength, hitDistance;
            public float[] referencePosition, rayOrigin, hitPoint, hitNormal;
        }

        [Serializable] public sealed class BoundsRecord
        {
            public string path;
            public bool valid;
            public int layer, meshCount;
            public float worldDeterminant;
            public float[] center, size, min, max;
        }

        [MenuItem("JieGuang/Environment/4 Check Ground Contacts")]
        public static void Check()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
                throw new InvalidOperationException("Run ground checks with the Editor idle, outside Play Mode/import/compilation.");

            var report = new GroundReport {
                utc = DateTime.UtcNow.ToString("o"),
                previousQueriesHitBackfaces = Physics.queriesHitBackfaces,
                testedQueriesHitBackfaces = false
            };
            string projectDirectory = Directory.GetParent(Application.dataPath).FullName;
            string evidenceDirectory = Path.Combine(Directory.GetParent(projectDirectory).FullName, "art/verification/env-v1");
            string evidencePath = Path.Combine(evidenceDirectory, "ground-checks.json");
            Scene preview = default(Scene);
            GameObject island = null;
            try
            {
                GameObject source = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
                if (source == null) throw new FileNotFoundException("Build Island before checking ground contacts.", PrefabPath);
                preview = EditorSceneManager.NewPreviewScene();
                island = (GameObject)PrefabUtility.InstantiatePrefab(source, preview);
                Transform[] transforms = island.GetComponentsInChildren<Transform>(true);
                Collider[] ground = island.GetComponentsInChildren<Collider>(true)
                    .Where(c => c.enabled && c.gameObject.activeInHierarchy && !c.isTrigger && c.gameObject.layer == GroundLayer).ToArray();
                report.groundColliderCount = ground.Length;
                if (ground.Length == 0) throw new InvalidDataException("The Island prefab contains no enabled, non-trigger layer-8 collider.");

                // Collider.Raycast avoids hitting other open scenes. Disable back-face hits
                // temporarily so reversed collision winding cannot produce a false pass.
                Physics.queriesHitBackfaces = false;
                Physics.SyncTransforms();
                RecordCorrectedTerrainBounds(island.transform, report);
                float top = ground.Max(c => c.bounds.max.y) + 10f;
                float bottom = ground.Min(c => c.bounds.min.y) - 10f;

                CheckAnchor("Anchor_VillageGate", true, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("Anchor_GoldenTree", true, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("NPC_ABo_Door", true, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("Anchor_PlayerSpawn", false, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("NPC_AYing", false, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("Target_Pier", false, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("NPC_Postman", false, transforms, ground, island.transform, top, bottom, report);
                CheckAnchor("Target_Path", false, transforms, ground, island.transform, top, bottom, report);

                ProbeRoad("Road_VillageGate_-12_4", -12f, 4f, ground, island.transform, top, bottom, report);
                ProbeRoad("Road_VillageCentre_-13_10", -13f, 10f, ground, island.transform, top, bottom, report);
                ProbeRoad("Road_Descent_-10_minus1", -10f, -1f, ground, island.transform, top, bottom, report);
                ProbeRoad("Road_Coast_-18_0", -18f, 0f, ground, island.transform, top, bottom, report);
                ProbeRoad("Road_WestVillage_-21point4_11", -21.4f, 11f, ground, island.transform, top, bottom, report);

                report.passedSamples = report.samples.Count(s => s.passed);
                report.failedSamples = report.samples.Count - report.passedSamples;
                report.status = report.errors.Count == 0 && report.failedSamples == 0 ? "passed-ground-samples" : "failed-ground-samples";
            }
            catch (Exception ex)
            {
                report.status = "error";
                report.errors.Add(ex.GetType().Name + ": " + ex.Message);
                throw;
            }
            finally
            {
                Physics.queriesHitBackfaces = report.previousQueriesHitBackfaces;
                if (island != null) Object.DestroyImmediate(island);
                if (preview.IsValid()) EditorSceneManager.ClosePreviewScene(preview);
                Directory.CreateDirectory(evidenceDirectory);
                File.WriteAllText(evidencePath, JsonUtility.ToJson(report, true));
            }

            if (report.status != "passed-ground-samples")
                throw new InvalidOperationException("Ground checks failed: " + string.Join(", ", report.samples.Where(s => !s.passed).Select(s => s.name)) + ". See " + evidencePath);
            Debug.Log("[EnvV1] Ground checks passed: " + report.passedSamples + " samples. Evidence: " + evidencePath);
        }

        private static void CheckAnchor(string name, bool strict, Transform[] transforms, Collider[] ground,
            Transform island, float top, float bottom, GroundReport report)
        {
            Transform[] matches = transforms.Where(t => t.name == name).ToArray();
            var sample = new SampleRecord {
                name = name, kind = "anchor", foundAnchor = matches.Length == 1,
                anchorMatches = matches.Length, hasReferenceY = true, enforceHeight = strict,
                toleranceMetres = strict ? AnchorTolerance : 0f
            };
            if (matches.Length != 1)
            {
                sample.detail = "Expected exactly one named anchor; found " + matches.Length + ".";
                report.samples.Add(sample);
                return;
            }
            sample.referencePosition = Array(matches[0].position);
            Probe(sample, matches[0].position, ground, island, top, bottom);
            report.samples.Add(sample);
        }

        private static void ProbeRoad(string name, float x, float z, Collider[] ground, Transform island,
            float top, float bottom, GroundReport report)
        {
            var sample = new SampleRecord { name = name, kind = "road-probe", hasReferenceY = false };
            Vector3 position = new Vector3(x, 0, z);
            sample.referencePosition = Array(position);
            Probe(sample, position, ground, island, top, bottom);
            report.samples.Add(sample);
        }

        private static void Probe(SampleRecord sample, Vector3 position, Collider[] ground, Transform island,
            float top, float bottom)
        {
            Vector3 origin = new Vector3(position.x, Mathf.Max(top, position.y + 10f), position.z);
            float length = origin.y - bottom;
            sample.rayOrigin = Array(origin);
            sample.rayLength = length;
            sample.testedColliders = ground.Length;
            Ray ray = new Ray(origin, Vector3.down);
            RaycastHit closest = default(RaycastHit);
            Collider closestCollider = null;
            float distance = float.PositiveInfinity;
            foreach (Collider collider in ground)
            {
                if (collider.Raycast(ray, out RaycastHit hit, length) && hit.distance < distance)
                {
                    closest = hit;
                    closestCollider = collider;
                    distance = hit.distance;
                }
            }
            sample.hit = closestCollider != null;
            if (!sample.hit)
            {
                sample.detail = "No layer-8 ground hit on this prefab's colliders.";
                return;
            }
            sample.colliderPath = RelativePath(closestCollider.transform, island);
            sample.hitPoint = Array(closest.point);
            sample.hitNormal = Array(closest.normal);
            sample.hitDistance = closest.distance;
            sample.groundY = closest.point.y;
            sample.upwardNormal = closest.normal.y > 0f;
            sample.deltaY = sample.hasReferenceY ? position.y - closest.point.y : 0f;
            bool heightPass = !sample.enforceHeight || Mathf.Abs(sample.deltaY) <= AnchorTolerance;
            sample.passed = sample.upwardNormal && heightPass;
            sample.detail = !sample.upwardNormal ? "Ground normal does not face upward." :
                !heightPass ? "Absolute anchor-ground height delta exceeds 0.03 m." :
                sample.enforceHeight ? "Upward ground hit and height delta within 0.03 m." :
                "Upward ground hit; height delta is informational only.";
        }

        private static void RecordCorrectedTerrainBounds(Transform island, GroundReport report)
        {
            Transform terrain = island.Find("Terrain");
            if (terrain == null)
            {
                report.errors.Add("Missing Terrain subtree; corrected scene bounds cannot be recorded.");
                return;
            }
            bool any = false, anyGround = false;
            Bounds all = default(Bounds), ground = default(Bounds);
            int meshCount = 0, groundCount = 0;
            foreach (MeshFilter filter in terrain.GetComponentsInChildren<MeshFilter>(true))
            {
                if (filter.sharedMesh == null) continue;
                Bounds local = filter.sharedMesh.bounds;
                Matrix4x4 matrix = filter.transform.localToWorldMatrix;
                bool first = true;
                Bounds world = default(Bounds);
                for (int x = -1; x <= 1; x += 2)
                    for (int y = -1; y <= 1; y += 2)
                        for (int z = -1; z <= 1; z += 2)
                        {
                            Vector3 point = matrix.MultiplyPoint3x4(local.center + Vector3.Scale(local.extents, new Vector3(x, y, z)));
                            if (first) { world = new Bounds(point, Vector3.zero); first = false; }
                            else world.Encapsulate(point);
                        }
                BoundsRecord row = BoundsRow(RelativePath(filter.transform, island), world, 1);
                row.layer = filter.gameObject.layer;
                row.worldDeterminant = matrix.determinant;
                report.terrainMeshes.Add(row);
                if (!any) { all = world; any = true; } else all.Encapsulate(world);
                meshCount++;
                Collider collider = filter.GetComponent<Collider>();
                if (filter.gameObject.layer == GroundLayer && collider != null && collider.enabled && !collider.isTrigger)
                {
                    if (!anyGround) { ground = world; anyGround = true; } else ground.Encapsulate(world);
                    groundCount++;
                }
            }
            report.correctedTerrainBounds = any ? BoundsRow("Island/Terrain", all, meshCount) : new BoundsRecord { path = "Island/Terrain" };
            report.correctedTerrainGroundBounds = anyGround ? BoundsRow("Island/Terrain (layer-8 collider meshes)", ground, groundCount) : new BoundsRecord { path = "Island/Terrain (layer-8 collider meshes)" };
            if (!any || !anyGround) report.errors.Add("Terrain is missing render meshes or layer-8 ground collider meshes.");
        }

        private static BoundsRecord BoundsRow(string path, Bounds bounds, int meshCount)
        {
            return new BoundsRecord { path = path, valid = true, meshCount = meshCount,
                center = Array(bounds.center), size = Array(bounds.size), min = Array(bounds.min), max = Array(bounds.max) };
        }
        private static float[] Array(Vector3 value) => new[] { value.x, value.y, value.z };
        private static string RelativePath(Transform transform, Transform root)
        {
            var parts = new List<string>();
            for (Transform current = transform; current != null; current = current.parent)
            {
                parts.Add(current.name);
                if (current == root) break;
            }
            parts.Reverse();
            return string.Join("/", parts);
        }
    }
}
#endif
