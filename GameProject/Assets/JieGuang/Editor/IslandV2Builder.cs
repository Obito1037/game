using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // Builds Assets/JieGuang/World/IslandV2.prefab: a copy of the environment track's Island.prefab
    // (left untouched) dressed with the user's Tripo v2 models from Assets/JieGuang/Props/.
    // Every replaced object keeps its transform, colliders, lights and anchors; only its renderers
    // are hidden and the new model is fitted to the old object's bounds.
    public static class IslandV2Builder
    {
        const string SourcePrefab = "Assets/JieGuang/Environment/Island.prefab";
        public const string OutputPrefab = "Assets/JieGuang/World/IslandV2.prefab";
        const string PropsRoot = "Assets/JieGuang/Props";
        const string RuntimePropsRoot = "Assets/JieGuang/Resources/Props";

        enum Fit { Height, Footprint, Max }

        static readonly List<string> report = new List<string>();

        [MenuItem("JieGuang/Build Island V2 (Tripo props)")]
        public static void Build()
        {
            report.Clear();
            Directory.CreateDirectory("Assets/JieGuang/World");
            Directory.CreateDirectory(RuntimePropsRoot);
            Directory.CreateDirectory(PropsRoot + "/Materials");
            var prefabs = PrepareProps();

            var src = AssetDatabase.LoadAssetAtPath<GameObject>(SourcePrefab);
            var root = (GameObject)Object.Instantiate(src);
            root.name = "Island";
            var t = root.transform;

            BuildGrandmotherHouse(t, prefabs);

            // landmarks and props
            Dress(t, "Props/Bench", prefabs, "A08_bench", Fit.Footprint, yawFrom: t.Find("NPC_Bench"), yawOffset: 90f);
            Dress(t, "Props/Armillary", prefabs, "A10_armillary", Fit.Footprint);
            Dress(t, "Props/CrescentMemorial", prefabs, "A11_crescent", Fit.Height);
            Dress(t, "Props/Flagpole", prefabs, "A14_flagpole", Fit.Height);
            AlignStoryFurniture(t);
            Dress(t, "Props/HarborLantern", prefabs, "A16_harbor_lantern", Fit.Height);
            AlignHarborLantern(t);
            Dress(t, "Props/Well", prefabs, "C06_well", Fit.Footprint);
            Dress(t, "Props/ClothesLine", prefabs, "C07_laundry", Fit.Max);
            Dress(t, "Props/ReturningBoat", prefabs, "C01_light_ship", Fit.Max, scaleMul: 1.35f);
            Dress(t, "Rocks/PostmanWaystone", prefabs, "A09_boulder", Fit.Max);
            Dress(t, "Rocks/OuterRockArch", prefabs, "D08_rock_arch", Fit.Max);
            for (int i = 1; i <= 3; ++i) Dress(t, "Pier/PierDeck_0" + i, prefabs, "A12_pier_segment", Fit.Footprint, yawOffset: 90f, alignTop: true);
            BuildPierEnd(t, prefabs);

            // the three lamps: post and turning head (shades are attached at runtime by LampPost)
            foreach (var lamp in new[] { "Anchor_Lamp_WanFeng", "Anchor_Lamp_YueChuang", "Anchor_Lamp_GuiHang" })
            {
                Dress(t, lamp + "/Structure", prefabs, "A05_lamp_post", Fit.Height);
                Dress(t, lamp + "/LampHead", prefabs, "A06_lamp_head", Fit.Max, scaleMul: 0.85f, asChildLocal: true, authoredScale: true);
            }

            // village: eleven houses cycling the three Tripo cottages; the merged batches go dark
            var batches = t.Find("Village_Batches");
            if (batches != null) foreach (var r in batches.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            string[] houses = { "C03_house_teal", "C04_house_ochre", "C05_house_slate" };
            var village = t.Find("Village");
            int h = 0;
            if (village != null)
                foreach (Transform house in village)
                    Dress(house, null, prefabs, houses[h++ % houses.Length], Fit.Height, faceFrom: NearestWindow(t, house), height: 3.2f + (h % 4) * .35f);
            // window quads become warm lights inside the new cottages (WindowGlow drives both)
            var windows = t.Find("Village_Windows");
            if (windows != null)
                foreach (Transform w in windows)
                {
                    foreach (var r in w.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
                    var lg = new GameObject("WindowLight");
                    lg.transform.SetParent(w, false);
                    lg.transform.localPosition = Vector3.zero;
                    var l = lg.AddComponent<Light>();
                    l.type = LightType.Point;
                    l.color = new Color(1f, 0.72f, 0.4f);
                    l.range = 3.5f;
                    l.intensity = 1.6f;
                    l.shadows = LightShadows.None;
                }

            // forest and the golden tree
            string[] trees = { "D01_tree_tall", "D02_tree_round", "D03_tree_rock", "D01_tree_tall", "D02_tree_round" };
            var forest = t.Find("Forest");
            int k = 0;
            if (forest != null)
                foreach (Transform tree in forest)
                {
                    if (tree.name == "GoldenLightTree") { Dress(tree, null, prefabs, "A03_golden_tree", Fit.Height, scaleMul: 1.15f); continue; }
                    string id = tree.name == "LightTree_13" || tree.name == "LightTree_12" ? "C08_village_tree" : trees[k++ % trees.Length];
                    Dress(tree, null, prefabs, id, Fit.Height);
                }

            // shore rocks and distant reefs
            string[] rocks = { "D05_rocks_low", "D06_rocks_peak", "D07_rock_table", "D09_rock_pillar", "D05_rocks_low", "D10_reef" };
            var rocksRoot = t.Find("Rocks");
            int q = 0;
            if (rocksRoot != null)
                foreach (Transform rock in rocksRoot)
                {
                    if (rock.name.StartsWith("ShoreRock")) Dress(rock, null, prefabs, rocks[q++ % rocks.Length], Fit.Max);
                    else if (rock.name.StartsWith("DistantReef")) Dress(rock, null, prefabs, q++ % 2 == 0 ? "D10_reef" : "D06_rocks_peak", Fit.Max);
                }

            // extras the story stages around the pier and the cape
            Physics.SyncTransforms();
            Place(t, prefabs, "C02_rowboat", t.Find("Props/ReturningBoat"), new Vector3(-3.2f, 0f, 2.5f), 25f);
            Place(t, prefabs, "D04_sapling", t.Find("Anchor_GoldenTree"), new Vector3(-2.2f, 0f, 1.6f), 0f, snap: true);

            IslandTerrainBuilder.Build(t);
            report.Add(IslandShoreBuilder.Build(t));
            // one sky (the story's skybox) and the new night sea
            var atmos = t.Find("Atmosphere");
            if (atmos != null)
            {
                var envSky = atmos.Find("NightSky");
                if (envSky != null) envSky.GetComponent<Renderer>().enabled = false;
                var sea = atmos.Find("NightSea");
                var seaMat = AssetDatabase.LoadAssetAtPath<Material>("Assets/JieGuang/Resources/Materials/Base_Sea.mat");
                if (sea != null && seaMat != null)
                {
                    var r = sea.GetComponent<Renderer>();
                    r.sharedMaterial = seaMat;
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                }
            }
            report.Add("terrain: Unity Terrain with grass/flower details built");
            PrefabUtility.SaveAsPrefabAsset(root, OutputPrefab);
            Object.DestroyImmediate(root);
            File.WriteAllLines("Assets/JieGuang/World/IslandV2-build-report.txt", report);
            AssetDatabase.ImportAsset("Assets/JieGuang/World/IslandV2-build-report.txt");
            Debug.Log("[JieGuang] IslandV2 built: " + report.Count + " entries");
        }

        static Transform Named(Transform root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == name);

        static void AlignStoryFurniture(Transform root)
        {
            // Measured against the accepted Mixamo sitting poses: keep feet at ground/deck
            // height, and bring the seat surface below the pelvis instead of lifting actors.
            var bench = root.Find("Props/Bench");
            if (bench != null) bench.localScale = new Vector3(1f, .76f, 1f);
            var box = root.Find("Props/KeeperBox");
            if (box != null) box.localScale = new Vector3(1f, .57f, 1f);

            // The old flag fabric biased the renderer bounds used by Dress by ~0.6 m.
            // Align the actual lower shaft with its retained solid collider, then use the
            // measured attachment point on the imported hook for the carried lantern.
            var pole = root.Find("Props/Flagpole");
            var model = Named(root, "V2_A14_flagpole");
            if (pole == null || model == null) return;
            var filter = model.GetComponentInChildren<MeshFilter>();
            var vertices = filter.sharedMesh.vertices.Select(v => filter.transform.TransformPoint(v)).ToArray();
            float bottom = vertices.Min(v => v.y), top = vertices.Max(v => v.y);
            var shaft = vertices.Where(v => v.y > Mathf.Lerp(bottom, top, .20f) && v.y < Mathf.Lerp(bottom, top, .28f)).ToArray();
            if (shaft.Length == 0) throw new System.InvalidOperationException("A14 shaft measurement failed.");
            var center = new Vector3((shaft.Min(v=>v.x)+shaft.Max(v=>v.x))*.5f, pole.position.y,
                (shaft.Min(v=>v.z)+shaft.Max(v=>v.z))*.5f);
            model.position += new Vector3(pole.position.x-center.x, 0f, pole.position.z-center.z);
            var hook = model.TransformPoint(new Vector3(-.01f, .33f, 1.91f));
            foreach (var name in new[] { "Anchor_FlagpoleHook", "Marker_FlagpoleHook" })
            {
                var marker = Named(root, name);
                if (marker != null) marker.position = hook;
            }
            report.Add("STORY seats bench Y=.76 / keeper box Y=.57; A14 shaft aligned to solid collider, lantern hook="+hook);
        }

        static void AlignHarborLantern(Transform root)
        {
            var lamp = root.Find("Props/HarborLantern");
            var model = Named(root, "V2_A16_harbor_lantern");
            var hook = root.Find("Anchor_FlagpoleHook");
            if (lamp == null || model == null || hook == null) return;
            var bounds = MeshBounds(model.gameObject);
            // The old ship lamp and the player's replacement share the physical A14 hook.
            lamp.position += hook.position - new Vector3(bounds.center.x, bounds.max.y, bounds.center.z);
            report.Add("A16 top ring aligned to A14 hook="+hook.position);
        }

        static void BuildGrandmotherHouse(Transform root, Dictionary<string, GameObject> prefabs)
        {
            var old = Named(root, "GrandmotherHouse");
            if (old == null || !prefabs.TryGetValue("A01_grandma_house", out var prefab)) return;
            foreach (var r in old.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            foreach (var c in old.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            foreach (var l in old.GetComponentsInChildren<LODGroup>(true)) l.enabled = false;
            var model = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            model.name = "V2_A01_grandma_house";
            model.transform.SetParent(root, false);
            // The processed FBX front is -X after Blender-to-Unity handedness conversion.
            var yaw = Quaternion.Euler(0, old.eulerAngles.y + 90f, 0);
            model.transform.SetPositionAndRotation(old.position, yaw * prefab.transform.localRotation);
            var front = Quaternion.Euler(0, old.eulerAngles.y, 0) * Vector3.forward;
            var window = model.transform.TransformPoint(new Vector3(-1.65f, 1.18f, 1.30f));
            var target = Named(root, "Target_Window");
            var delta = window - target.position;
            foreach (var name in new[] { "Marker_Window", "Marker_ABo_Seat", "Marker_Desk", "NPC_ABo_Window", "Target_Window" })
            {
                var a = Named(root, name);
                if (a != null) a.position += delta;
            }
            // Seat anchor means the seat surface, as consumed by CharacterActor.SitAt.
            var seat = Named(root, "NPC_ABo_Window");
            seat.position = window - front * 1.04f - Vector3.up * .83f;
            seat.rotation = Quaternion.LookRotation(front);
            Named(root, "Marker_ABo_Seat").position = seat.position;
            var desk = Named(root, "Marker_Desk");
            desk.position = window - front * .99f - Vector3.up * 1.05f;
            desk.rotation = Quaternion.LookRotation(front);
            var deskGo = (GameObject)PrefabUtility.InstantiatePrefab(prefabs["A02_desk_set"]);
            deskGo.name = "V2_A02_desk_set"; deskGo.transform.SetParent(model.transform, true);
            deskGo.transform.SetPositionAndRotation(desk.position, Quaternion.LookRotation(front) * prefabs["A02_desk_set"].transform.localRotation);
            var entry = Named(root, "NPC_ABo_Door");
            if (entry != null) entry.position = model.transform.TransformPoint(new Vector3(-2.8f, -.8f, 0f));
            // Wall/floor volumes aligned to the actual cottage; independent of the old hull.
            var hull = new GameObject("A01_Colliders").transform; hull.SetParent(root, false);
            hull.SetPositionAndRotation(model.transform.position, yaw);
            Box(hull, "Floor", new Vector3(0,.10f,0), new Vector3(4.5f,.20f,4.5f));
            Box(hull, "FrontWall", new Vector3(-2.08f,1.15f,0), new Vector3(.22f,2.3f,4.3f));
            Box(hull, "BackWall", new Vector3(2.05f,1.15f,0), new Vector3(.22f,2.3f,4.3f));
            Box(hull, "SideWallA", new Vector3(0,1.15f,-2.12f), new Vector3(4.3f,2.3f,.22f));
            Box(hull, "SideWallB", new Vector3(0,1.15f,2.12f), new Vector3(4.3f,2.3f,.22f));
            // A warm interior backdrop leaves the opening unobstructed for the seated actor.
            var backdrop = GameObject.CreatePrimitive(PrimitiveType.Cube); backdrop.name="WindowInterior";
            Object.DestroyImmediate(backdrop.GetComponent<Collider>());
            backdrop.transform.SetParent(root, false);
            backdrop.transform.SetPositionAndRotation(window-front*1.65f, Quaternion.LookRotation(front));
            backdrop.transform.localScale=new Vector3(1.8f,1.8f,.05f);
            var matPath="Assets/JieGuang/World/WindowInterior.mat";
            var mat=AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if(mat==null){mat=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(mat,matPath);}
            mat.SetColor("_BaseColor",new Color(.23f,.13f,.07f));backdrop.GetComponent<Renderer>().sharedMaterial=mat;
            var lightGo=new GameObject("A01_WindowLight");lightGo.transform.SetParent(target,false);
            lightGo.transform.position=window-front*.25f+Vector3.up*.3f;
            var light=lightGo.AddComponent<Light>();light.type=LightType.Point;light.color=new Color(1,.73f,.43f);light.intensity=2.8f;light.range=9f;light.shadows=LightShadows.None;
            if(target.GetComponent<WindowGlow>()==null) target.gameObject.AddComponent<WindowGlow>();
            report.Add("A01 open window "+window+" seat "+seat.position+" desk "+desk.position+"; derived mesh from v2_house_window.py");
        }

        static void Box(Transform parent, string name, Vector3 center, Vector3 size)
        { var go=new GameObject(name);go.transform.SetParent(parent,false);var c=go.AddComponent<BoxCollider>();c.center=center;c.size=size; }

        static void BuildPierEnd(Transform root, Dictionary<string, GameObject> prefabs)
        {
            var last=Named(root,"PierDeck_03");
            if(last==null||!prefabs.TryGetValue("A13_pier_end",out var prefab))return;
            var go=(GameObject)PrefabUtility.InstantiatePrefab(prefab);go.name="V2_A13_pier_end";go.transform.SetParent(root,false);
            go.transform.rotation=Quaternion.Euler(0,90,0)*prefab.transform.localRotation;
            var bounds=MeshBounds(go);
            // Platform extends the final segment (north, +Z) and shares its walking height.
            go.transform.position+=new Vector3(last.position.x-bounds.center.x,2.48f-1.0f,last.position.z+2.4f-bounds.center.z);
            var hull=new GameObject("A13_DeckCollider").transform;hull.SetParent(root,false);
            hull.position=new Vector3(last.position.x,2.33f,last.position.z+2.4f);
            Box(hull,"Deck",Vector3.zero,new Vector3(3.7f,.30f,3.7f));
            report.Add("EXTRA A13 end platform at "+go.transform.position);
        }

        static Transform NearestWindow(Transform root, Transform house)
        {
            var windows = root.Find("Village_Windows");
            if (windows == null) return null;
            Transform best = null;
            float bd = 4f;
            foreach (Transform w in windows)
            {
                float d = Vector3.Distance(Flat(w.position), Flat(house.position));
                if (d < bd) { bd = d; best = w; }
            }
            return best;
        }

        static Vector3 Flat(Vector3 v) { v.y = 0f; return v; }

        // Hides `path`'s renderers and fits the prop to their bounds (bottom centre, same yaw).
        static void Dress(Transform root, string path, Dictionary<string, GameObject> prefabs, string id, Fit fit,
            Transform yawFrom = null, Transform faceFrom = null, float scaleMul = 1f, bool asChildLocal = false, float yawOffset = 0f, bool alignTop = false, float height = 0f, bool authoredScale = false)
        {
            var target = path == null ? root : root.Find(path);
            if (target == null) { report.Add("MISSING target " + path); return; }
            if (!prefabs.TryGetValue(id, out var prefab)) { report.Add("MISSING prop " + id); return; }
            var rends = target.GetComponentsInChildren<Renderer>(true).Where(r => !(r is ParticleSystemRenderer)).ToArray();
            if (rends.Length == 0) { report.Add("NO RENDERERS " + target.name); return; }
            var old = rends[0].bounds;
            foreach (var r in rends) old.Encapsulate(r.bounds);
            foreach (var r in rends) r.enabled = false;
            foreach (var lod in target.GetComponentsInChildren<LODGroup>(true)) lod.enabled = false;

            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            inst.name = "V2_" + id;
            var nb = MeshBounds(inst);
            float s;
            switch (fit)
            {
                case Fit.Height: s = old.size.y / Mathf.Max(nb.size.y, 1e-3f); break;
                case Fit.Footprint: s = Mathf.Max(old.size.x, old.size.z) / Mathf.Max(Mathf.Max(nb.size.x, nb.size.z), 1e-3f); break;
                default: s = Mathf.Max(old.size.x, old.size.y, old.size.z) / Mathf.Max(Mathf.Max(nb.size.x, nb.size.y), Mathf.Max(nb.size.z, 1e-3f)); break;
            }
            s *= scaleMul;
            if (height > 0f) s = height / Mathf.Max(nb.size.y, 1e-3f);
            if (authoredScale) s = scaleMul;
            float yaw = target.eulerAngles.y + yawOffset;
            if (yawFrom != null) yaw = yawFrom.eulerAngles.y + yawOffset;
            if (faceFrom != null)
            {
                Vector3 d = Flat(faceFrom.position - target.position);
                if (d.sqrMagnitude > 0.01f) yaw = Quaternion.LookRotation(d).eulerAngles.y + yawOffset;
            }
            inst.transform.SetParent(target, false);
            if (asChildLocal)
            {
                inst.transform.localRotation = prefab.transform.localRotation;
                inst.transform.localScale = Vector3.one * (s / Mathf.Max(target.lossyScale.x, 1e-3f));
                // centre the head on its pivot (the turning axis)
                var b2 = MeshBounds(inst);
                inst.transform.position += target.position - b2.center;
            }
            else
            {
                // keep the FBX root's own axis conversion (-90° X from Blender) under the yaw
                inst.transform.rotation = Quaternion.Euler(0f, yaw, 0f) * prefab.transform.localRotation;
                var ls = target.lossyScale;
                inst.transform.localScale = new Vector3(s / Mathf.Max(ls.x, 1e-3f), s / Mathf.Max(ls.y, 1e-3f), s / Mathf.Max(ls.z, 1e-3f));
                var b2 = MeshBounds(inst);
                float dy = alignTop ? old.max.y - b2.max.y : old.min.y - b2.min.y;
                // A12 has a mooring post above its plank deck. Do not align that post to the floor.
                if (id == "A12_pier_segment") dy = 2.48f - (inst.transform.position.y + .80f * s);
                inst.transform.position += new Vector3(old.center.x - b2.center.x, dy, old.center.z - b2.center.z);
            }
            report.Add(string.Format("{0} <- {1} scale {2:F2} old {3} new {4}", target.name, id, s, old.size.ToString("F2"), MeshBounds(inst).size.ToString("F2")));
        }

        static void Place(Transform root, Dictionary<string, GameObject> prefabs, string id, Transform near, Vector3 offset, float yaw, bool snap = false)
        {
            if (near == null || !prefabs.TryGetValue(id, out var prefab)) { report.Add("SKIP extra " + id); return; }
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            inst.name = "V2_" + id;
            inst.transform.SetParent(root, false);
            Vector3 p = near.position + near.rotation * offset;
            if (snap && Physics.Raycast(p + Vector3.up * 5f, Vector3.down, out var hit, 20f)) p.y = hit.point.y;
            inst.transform.SetPositionAndRotation(p, Quaternion.Euler(0f, near.eulerAngles.y + yaw, 0f) * prefab.transform.localRotation);
            report.Add("EXTRA " + id + " at " + p.ToString("F1"));
        }

        static Bounds MeshBounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
            var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }

        // Import settings + URP materials + one prefab per processed prop.
        static Dictionary<string, GameObject> PrepareProps()
        {
            var result = new Dictionary<string, GameObject>();
            foreach (var dir in Directory.GetDirectories(PropsRoot))
            {
                string id = Path.GetFileName(dir);
                if (id == "Materials" || id == "Prefabs") continue;
                string fbx = dir + "/" + id + ".fbx";
                if (id == "A01_grandma_house" && File.Exists(dir + "/" + id + "_open.fbx")) fbx = dir + "/" + id + "_open.fbx";
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
                if (model == null) continue;
                var albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(dir + "/" + id + "_albedo.jpg");
                var normal = AssetDatabase.LoadAssetAtPath<Texture2D>(dir + "/" + id + "_normal.png");
                string matPath = PropsRoot + "/Materials/" + id + ".mat";
                var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
                if (mat == null)
                {
                    mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                    AssetDatabase.CreateAsset(mat, matPath);
                }
                mat.SetTexture("_BaseMap", albedo);
                mat.SetColor("_BaseColor", Color.white);
                mat.SetFloat("_Smoothness", id.StartsWith("A07") || id.StartsWith("A06") || id.StartsWith("A05") || id.StartsWith("A16") ? 0.45f : 0.18f);
                mat.SetFloat("_Metallic", id.StartsWith("A07") || id.StartsWith("A10") || id.StartsWith("A11") ? 0.55f : 0f);
                if (normal != null)
                {
                    mat.SetTexture("_BumpMap", normal);
                    mat.EnableKeyword("_NORMALMAP");
                }
                EditorUtility.SetDirty(mat);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                foreach (var r in go.GetComponentsInChildren<Renderer>()) r.sharedMaterials = Enumerable.Repeat(mat, r.sharedMaterials.Length).ToArray();
                // props that the story code spawns at runtime live under Resources
                bool runtime = id.StartsWith("B0") || id.StartsWith("A04") || id.StartsWith("A07");
                string dst = (runtime ? RuntimePropsRoot : PropsRoot) + "/" + id + ".prefab";
                result[id] = PrefabUtility.SaveAsPrefabAsset(go, dst);
                Object.DestroyImmediate(go);
            }
            AssetDatabase.SaveAssets();
            report.Add("props prepared: " + string.Join(", ", result.Keys));
            return result;
        }
    }

    // Tripo props: meters, no animation, no cameras/lights, readable meshes off.
    public sealed class JieGuangPropImport : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith("Assets/JieGuang/Props/")) return;
            var m = (ModelImporter)assetImporter;
            m.importAnimation = false;
            m.importCameras = false;
            m.importLights = false;
            m.materialImportMode = ModelImporterMaterialImportMode.None;
            m.animationType = ModelImporterAnimationType.None;
            m.isReadable = false;
            m.bakeAxisConversion = false;
        }

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith("Assets/JieGuang/Props/")) return;
            var ti = (TextureImporter)assetImporter;
            if (assetPath.EndsWith("_normal.png")) ti.textureType = TextureImporterType.NormalMap;
            ti.maxTextureSize = 2048;
            ti.mipmapEnabled = true;
        }
    }
}

