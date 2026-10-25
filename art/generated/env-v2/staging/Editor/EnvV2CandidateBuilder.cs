#if UNITY_EDITOR
// Offline-authored, explicit commands only. Never rebuilds v1, opens the main scene,
// saves another scene, enters Play, builds a player, or changes project settings.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV2CandidateBuilder
    {
        const string Root = "Assets/JieGuang/Environment";
        const string BaselinePrefab = Root + "/Island.prefab";
        const string BaselineScene = Root + "/EnvTest.unity";
        const string CandidatePrefab = Root + "/Candidates/IslandV2.prefab";
        const string CandidateScene = Root + "/EnvV2Test.unity";
        const string HouseModel = Root + "/ModelsV2/abode_grandma_v2_candidate.fbx";
        const string TerrainModel = Root + "/ModelsV2/coastal_terrain_v2_candidate.fbx";
        const string MeadowTexture = Root + "/Textures/v2/meadow_albedo_v1.png";
        const string WoodTexture = Root + "/Textures/v2/wood_albedo_v1.png";
        static readonly string[] VillageModels = { Root + "/ModelsV2/cottage_teal_v2_candidate.fbx", Root + "/ModelsV2/cottage_ochre_v2_candidate.fbx", Root + "/ModelsV2/cottage_slate_v2_candidate.fbx" };
        static readonly string[] CoastalPropModels = { Root + "/ModelsV2/pier_module/pier_module_v2_candidate.fbx", Root + "/ModelsV2/bench/bench_v2_candidate.fbx" };
        const int Width = 1440, Height = 900;
        const float FreezeSeconds = 12f;
        static string Repository => Directory.GetParent(Directory.GetParent(Application.dataPath).FullName).FullName;
        static string Evidence => Path.Combine(Repository, "art/verification/env-v2");

        [Serializable] sealed class CheckResult { public string name, detail; public bool passed; }
        [Serializable] sealed class Pose
        {
            public string path; public Vector3 position, scale; public Quaternion rotation;
            public int layer; public bool active; public string colliderJson;
        }
        [Serializable] sealed class Sample
        {
            public string name; public Vector3 point; public bool hit; public float height;
            public string collider;
        }
        [Serializable] sealed class Beam { public string lamp, target; public string[] blockers; }
        [Serializable] sealed class Mapping { public string source, destination; }
        [Serializable] sealed class BuildReport
        {
            public string status = "in-progress", utc = DateTime.UtcNow.ToString("O"), unityVersion = Application.unityVersion;
            public string source = BaselinePrefab, candidate = CandidatePrefab, scene = CandidateScene, generation;
            public string houseOrientation, terrainOrientation;
            public float houseAsImportedError, houseReflectedError, terrainAsImportedMatch, terrainReflectedMatch;
            public int spots, windows, houseMaterials, houseTriangles;
            public long allLodRendererTriangles, enabledLodRendererTriangles;
            public long allMeshFilterTriangles, retainedNonRenderingMeshTriangles;
            public List<Pose> anchorsBefore = new List<Pose>(), anchorsAfter = new List<Pose>();
            public List<Pose> houseCollidersBefore = new List<Pose>(), houseCollidersAfter = new List<Pose>();
            public List<Sample> groundBefore = new List<Sample>(), groundAfter = new List<Sample>();
            public List<Beam> beamsBefore = new List<Beam>(), beamsAfter = new List<Beam>();
            public List<Mapping> houseMaterialMapping = new List<Mapping>();
            public List<CheckResult> checks = new List<CheckResult>();
            public List<string> warnings = new List<string>();
            public string surfaceReport, meadowReport, shoreReport, houseWoodTexture=WoodTexture, houseWoodMaterials;
            public string villageReport, pierBenchReport;
        }
        [Serializable] sealed class CaptureRow
        {
            public string group, file, camera, shaderTime, method; public int width = Width, height = Height;
            public Vector3 position, forward; public float fov, near, far;
            public bool hdr, postProcessing, fog; public float reflectionIntensity;
            public Color ambientSky, ambientEquator, ambientGround; public int msaa;
            public string sceneCullingMask; public int originalVolumeMask, isolatedVolumeMask, ownVolumes;
        }
        [Serializable] sealed class CaptureReport
        {
            public string status = "in-progress", utc = DateTime.UtcNow.ToString("O");
            public bool foreignScenesPreserved; public string sceneStateDetail;
            public string scope = "Offscreen fixed-camera editor study, no characters/UI, gameplay, animation or measured FPS claim.";
            public string isolation = "An unused native scene-culling bit is assigned to the temporary study scene and camera override. Own Volumes are moved only in that unsaved scene to a layer unused by every foreign loaded Volume; camera volume mask selects that layer. No foreign object or project layer definition is modified. Rendered-image verification is still required.";
            public string comparison = "baseline-original preserves saved V1 HDR/post/lighting and live shader time. baseline-frozen changes only V1 _Time.y to 12 through copied diagnostic shaders/materials. candidate freezes Sky/Sea/Meadow at 12, HDR/post and V2 look differ intentionally.";
            public List<CaptureRow> images = new List<CaptureRow>();
        }
        sealed class View
        {
            public string name, file; public Vector3 position, look; public float fov;
            public View(string n, string f, Vector3 p, Vector3 l, float v) { name=n;file=f;position=p;look=l;fov=v; }
        }
        // Four exact v1 scene-input poses. Fifth is a new shared close-ground study,
        // not a screenshot of the player controller or a benchmark-matched gameplay camera.
        static readonly View[] Views = {
            new View("Cam_Title","01-title.png",new Vector3(57,44,-73),new Vector3(-5,5,1),45),
            new View("Cam_Puzzle","02-cape.png",new Vector3(27,18,-45),new Vector3(7,5,-18),43),
            new View("Cam_Pier","03-pier.png",new Vector3(22,8,-11),new Vector3(10,4,-15),48),
            new View("Cam_Village","04-village.png",new Vector3(12,21,-8),new Vector3(-14,10,12),48),
            new View("GameplayStudy","05-gameplay-study.png",new Vector3(12,4.15f,-24.2f),new Vector3(5.2f,3.9f,-16.7f),50)
        };
        static readonly string[] Required = {
            "Anchor_PlayerSpawn","Anchor_Lamp_WanFeng","Anchor_Lamp_YueChuang","Anchor_Lamp_GuiHang",
            "Target_Path","Target_Bench","Target_Window","Target_Pier","Anchor_FlagpoleHook",
            "NPC_AYing","NPC_Postman","NPC_Bench","NPC_ABo_Window","NPC_DengBo_Box",
            "Cam_Title","Cam_Puzzle","Cam_Pier","Cam_Village","Village_Windows",
            "Sky_ScatterZone_Village","Sky_ScatterZone_Pier","Walkable_Boundary",
            "Anchor_VillageGate","Anchor_GoldenTree","Anchor_Boat","Target_Sea","NPC_ABo_Door"
        };

        [MenuItem("JieGuang/Environment/V2/Build Candidate (never overwrite Island)")]
        public static void BuildCandidate()
        {
            Idle(); AssertClosed(CandidateScene);
            GameObject baseline = Load<GameObject>(BaselinePrefab);
            Load<GameObject>(HouseModel); Load<GameObject>(TerrainModel); Load<Texture2D>(MeadowTexture); Load<Texture2D>(WoodTexture);
            foreach (string path in VillageModels) Load<GameObject>(path);
            foreach (string path in CoastalPropModels) Load<GameObject>(path);
            foreach (string shader in new[] {"JieGuang/Environment/NightSkyV2","JieGuang/Environment/NightSeaV2",EnvV2SurfaceBuilder.ShaderName,EnvV2MeadowBuilder.ShaderName})
                RequireShader(shader);
            var report = new BuildReport();
            report.generation = Root + "/Generated/V2Candidates/Generation_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff");
            EnsureFolder(report.generation); EnsureFolder(Root+"/Candidates");
            var guard = new SceneGuard(); Scene scene = default;
            try
            {
                PrepareModel(HouseModel); PrepareModel(TerrainModel);
                foreach (string path in VillageModels) PrepareModel(path);
                foreach (string path in CoastalPropModels) PrepareModel(path);
                scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
                Need(SceneManager.SetActiveScene(scene),"Could not activate owned candidate scene.");
                GameObject island = (GameObject)PrefabUtility.InstantiatePrefab(baseline,scene);
                PrefabUtility.UnpackPrefabInstance(island,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);
                Need(!PrefabUtility.IsPartOfPrefabInstance(island),"Unpack must remove all inherited prefab links before editing candidate.");
                island.name = "Island";
                Need(island.transform.position.sqrMagnitude<1e-8f && Quaternion.Angle(island.transform.rotation,Quaternion.identity)<.001f && (island.transform.lossyScale-Vector3.one).sqrMagnitude<1e-8f,"Baseline must have identity root pose.");
                foreach (string name in Required) Unique(island.transform,name);
                report.anchorsBefore = Contract(island);
                Transform house = Find(island.transform,"Props/GrandmotherHouse");
                report.houseCollidersBefore = ColliderState(house);
                MeshFilter paths = UniqueComponent<MeshFilter>(Find(island.transform,"Terrain"),"StonePaths");
                Mesh originalPathMesh = paths.sharedMesh;
                Matrix4x4 originalPathMatrix = paths.transform.localToWorldMatrix;
                Physics.SyncTransforms();
                report.groundBefore = GroundSamples(island);
                report.beamsBefore = BeamSamples(island);
                ReplaceHouse(island,house,report);
                ReplaceTerrain(island,report);
                var village = EnvV2VillageBuilder.Build(island,report.generation,WoodTexture);
                report.villageReport = village.reportAssetPath;
                Need(village.checks.All(c=>c.passed),"Village helper reported a failed check.");
                report.warnings.AddRange(village.warnings);
                var pierBench = EnvV2PierBenchBuilder.Build(island,report.generation,WoodTexture);
                report.pierBenchReport = pierBench.reportAssetPath;
                Need(pierBench.targetTrianglesBefore==1692 && pierBench.targetTrianglesAfter==1692 && pierBench.additionalTriangles==0,
                    "Pier/bench helper must preserve all four instances' geometry.");
                report.warnings.AddRange(pierBench.limitations);
                AddWindowReceiver(island,report.generation);
                var surface = EnvV2SurfaceBuilder.Build(island,MeadowTexture);
                report.surfaceReport = surface.generationPath + "/surface-report.json";
                Need(surface.checks.All(c=>c.passed),"Surface helper reported a failed check.");
                var meadow = EnvV2MeadowBuilder.Build(island,Root+"/Generated/V2Meadow",new EnvV2MeadowBuilder.Settings {maxTrianglesIncludingLod=70000});
                report.meadowReport = meadow.outputPath+"/build-report.json";
                Need(meadow.checks.All(c=>c.passed),"Meadow helper reported a failed check.");
                ApplyLookAndCoast(island,report);
                Physics.SyncTransforms();
                report.anchorsAfter = Contract(island);
                report.houseCollidersAfter = ColliderState(house);
                report.groundAfter = GroundSamples(island,report.groundBefore);
                report.beamsAfter = BeamSamples(island);
                Check(report,"all-contract-poses-preserved",SamePoses(report.anchorsBefore,report.anchorsAfter),"All original Anchor/Target/NPC/Cam/Marker, LampHead, scatter and boundary/window transforms; 0.1mm/0.001 degree tolerance.");
                Check(report,"house-original-colliders-preserved",SamePoses(report.houseCollidersBefore,report.houseCollidersAfter),"Same paths, transform/layer/active state and serialized Collider payload, including original mesh references.");
                Check(report,"stone-path-mesh-and-transform-unchanged",paths.sharedMesh==originalPathMesh && MatrixNear(originalPathMatrix,paths.transform.localToWorldMatrix),"Surface material may change, conformed geometry must stay exactly the original asset.");
                Validate(island,report);
                FailChecks(report);
                Backup(CandidatePrefab,report.generation+"/Previous_IslandV2.prefab");
                Backup(CandidateScene,report.generation+"/Previous_EnvV2Test.unity");
                // Prefab remains animated by default. Frozen material copies belong to our test scene only.
                GameObject savedPrefab=PrefabUtility.SaveAsPrefabAsset(island,CandidatePrefab,out bool saved);
                Need(saved&&savedPrefab!=null,"SaveAsPrefabAsset returned false/null.");
                Need(PrefabUtility.GetPrefabAssetType(savedPrefab)==PrefabAssetType.Regular,"Candidate must be a regular prefab, not a variant referencing baseline.");
                FreezeOwnedTestMaterials(island,report.generation+"/TestMaterials");
                Camera camera = new GameObject("EnvV2TestCamera").AddComponent<Camera>();
                SceneManager.MoveGameObjectToScene(camera.gameObject,scene);
                ConfigureCandidateCamera(camera); SetView(camera,Views[0]);
                camera.scene=scene;
                Need(EditorSceneManager.SaveScene(scene,CandidateScene,false),"Saving owned EnvV2Test failed.");
                report.status="candidate-saved-structure-checks-passed-awaiting-visual-gameplay-and-performance-validation";
                report.warnings.Add("Island.prefab and the main scene were not changed. Candidate/own test scene only; no measured frame rate, player collision traversal, shader image or WebGL claim.");
                report.warnings.Add("House original collision intentionally remains v1, including old roof collision. New roof/attic is visual; not a new walkable interior.");
                report.warnings.Add("Game integration must choose one owner of sky/global ambient/fog and explicitly invoke EnvironmentLookRig.ApplyChapter. No Claude script is referenced or attached here.");
            }
            catch(Exception ex) { report.status="failed: "+ex.GetType().Name+": "+ex.Message; throw; }
            finally
            {
                guard.RestoreAndClose(scene);
                bool preserved=guard.Unchanged();
                Check(report,"foreign-scenes-preserved",preserved,guard.Describe());
                if(!preserved)report.status="failed-foreign-scene-state-changed-inspect-without-saving";
                WriteJson(Path.Combine(Repository,"art/generated/env-v2/candidate-integration-report.json"),report);
                Need(preserved,"Foreign scene state changed unexpectedly. It was not saved or cleared by this tool; inspect the integration report.");
            }
        }

        [MenuItem("JieGuang/Environment/V2/Capture Candidate and Baseline 1440x900")]
        public static void CaptureCandidate()
        {
            Idle(); AssertClosed(BaselineScene); AssertClosed(CandidateScene);
            Load<SceneAsset>(BaselineScene); Load<SceneAsset>(CandidateScene);
            var report=new CaptureReport(); var guard=new SceneGuard();
            string folder=Path.Combine(Evidence,"capture-"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff"));
            Directory.CreateDirectory(folder);
            try
            {
                CaptureScene(BaselineScene,"baseline-original",folder,report,false,false);
                CaptureScene(BaselineScene,"baseline-frozen",folder,report,true,false);
                CaptureScene(CandidateScene,"candidate",folder,report,false,true);
                report.status="captured-awaiting-human-image-review";
            }
            catch(Exception ex){report.status="failed: "+ex.Message;throw;}
            finally
            {
                guard.RestoreAndClose(default);
                report.foreignScenesPreserved=guard.Unchanged();report.sceneStateDetail=guard.Describe();
                if(!report.foreignScenesPreserved)report.status="failed-foreign-scene-state-changed-inspect-without-saving";
                WriteJson(Path.Combine(folder,"captures.json"),report);
                Need(report.foreignScenesPreserved,"Capture did not preserve foreign scene state. Inspect without saving other scenes.");
            }
        }

        static void ReplaceHouse(GameObject island,Transform house,BuildReport report)
        {
            var originals=house.GetComponentsInChildren<Renderer>(true);
            var oldMarkers=house.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("Marker_",StringComparison.Ordinal)).ToDictionary(t=>t.name,t=>t.position);
            Need(oldMarkers.Count>=4,"Four original house Markers are required to measure orientation.");
            // This helper and PNG now exist. Use the reviewed directional-UV FBX;
            // do not stage the earlier Smart-UV-only visual candidate by mistake.
            report.houseWoodMaterials=report.generation+"/HouseWood";
            Dictionary<string,Material> wood=EnvV2HouseSurfaceBuilder.Prepare(WoodTexture,report.houseWoodMaterials);
            GameObject model=Object.Instantiate(Load<GameObject>(HouseModel),house,false);
            model.name="__HouseImportProbe";
            try
            {
                Pose root=LocalPose(model.transform);
                report.houseAsImportedError=MarkerError(model,oldMarkers);
                ReflectRoot(model.transform,root);
                report.houseReflectedError=MarkerError(model,oldMarkers);
                bool reflect=report.houseReflectedError<report.houseAsImportedError;
                if(!reflect) RestoreLocal(model.transform,root);
                report.houseOrientation=reflect?"measured-reflected-import-root-X":"measured-as-imported";
                Need(Mathf.Min(report.houseAsImportedError,report.houseReflectedError)<=.025f,"Candidate house Markers cannot align within 2.5cm; do not guess axis fixes.");
                var materials=island.GetComponentsInChildren<Renderer>(true).Where(r=>!r.transform.IsChildOf(model.transform)).SelectMany(r=>r.sharedMaterials).Where(m=>m!=null).GroupBy(m=>Clean(m.name)).ToDictionary(g=>g.Key,g=>g.First());
                Material attic=NewLit("V2_AtticGlass_Unlit",new Color(.26f,.17f,.065f),.10f,.36f,report.generation+"/AtticGlass.mat");
                var groups=new Dictionary<Material,List<MeshPart>>();
                foreach(MeshFilter f in model.GetComponentsInChildren<MeshFilter>(true))
                {
                    Renderer r=f.GetComponent<Renderer>();if(r==null||f.sharedMesh==null)continue;
                    Need(f.sharedMesh.isReadable,"Candidate house mesh must be readable.");
                    Need(r.sharedMaterials.Length>=f.sharedMesh.subMeshCount,"Missing imported house material slot.");
                    for(int s=0;s<f.sharedMesh.subMeshCount;s++)
                    {
                        if(f.sharedMesh.GetIndexCount(s)==0)continue;
                        string source=Clean(r.sharedMaterials[s]==null?"":r.sharedMaterials[s].name);
                        Material chosen=wood.TryGetValue(source,out Material texturedWood)?texturedWood:MapHouseMaterial(source,materials,attic);
                        if(!groups.TryGetValue(chosen,out var parts)) groups.Add(chosen,parts=new List<MeshPart>());
                        parts.Add(new MeshPart(f.sharedMesh,s,house.worldToLocalMatrix*f.transform.localToWorldMatrix));
                        if(!report.houseMaterialMapping.Any(m=>m.source==source))report.houseMaterialMapping.Add(new Mapping {source=source,destination=chosen.name});
                    }
                }
                Need(groups.Count>0&&groups.Count<=16,"House material consolidation must result in 1..16 shared non-empty slots.");
                Material[] mapped=groups.Keys.OrderBy(m=>m.name,StringComparer.Ordinal).ToArray();
                Mesh combined=Combine(mapped.Select(m=>groups[m]).ToArray(),"GrandmotherHouse_V2_Visual");
                SaveNew(combined,report.generation+"/GrandmotherHouseVisual.asset");
                report.houseMaterials=mapped.Length;report.houseTriangles=(int)TriangleCount(combined);
                Need(report.houseTriangles<=12100,"Candidate house unexpectedly exceeds 12.1k triangles.");
                GameObject visual=new GameObject("Visual_V2");visual.transform.SetParent(house,false);visual.layer=9;
                visual.AddComponent<MeshFilter>().sharedMesh=combined;
                var renderer=visual.AddComponent<MeshRenderer>();renderer.sharedMaterials=mapped;renderer.shadowCastingMode=ShadowCastingMode.On;renderer.receiveShadows=true;
                // Keep every original transform, Marker, MeshFilter and Collider. Remove old rendering components only.
                foreach(Renderer r in originals)Object.DestroyImmediate(r);
            }
            finally{Object.DestroyImmediate(model);}
        }
        static Material MapHouseMaterial(string source,Dictionary<string,Material> old,Material attic)
        {
            if(old.TryGetValue(source,out Material exact))return exact;
            string key;
            if(source.StartsWith("V2_WhitewashedWood_"))key=source.EndsWith("0")?"Wall_LightTimber":"Wall_WarmIvory";
            else if(source.StartsWith("V2_OldTimber_"))key=source.EndsWith("0")?"Wood_DarkBeams":"Wood_Honey";
            else if(source.StartsWith("V2_TealClay_"))key=source.EndsWith("4")||source.EndsWith("2")?"Roof_TealHighlight":"Roof_AgedTeal";
            else if(source.StartsWith("V2_FoundationStone_"))key=source.EndsWith("0")?"Stone_SoftGrey":"Stone_WarmLimestone";
            else if(source=="V2_BlackenedIron")key="Iron_Blackened";
            else if(source=="V2_OldBrass")key="Copper_Aged";
            else if(source=="V2_AtticUnlitAmberGlass")return attic;
            else throw new InvalidDataException("Unmapped house material: "+source);
            Need(old.ContainsKey(key),"Baseline shared material absent: "+key);return old[key];
        }

        static void ReplaceTerrain(GameObject island,BuildReport report)
        {
            Transform terrain=Find(island.transform,"Terrain");
            MeshFilter ground=UniqueComponent<MeshFilter>(terrain,"IslandGround");
            Need(ground.sharedMesh.isReadable,"Original ground must be readable for orientation measurement.");
            // Match imported points to the frozen baseline: B changes 186/3025 coastal vertices.
            Vector3[] original=WorldVertices(ground);
            GameObject model=Object.Instantiate(Load<GameObject>(TerrainModel),terrain,false);model.name="__TerrainImportProbe";
            try
            {
                Pose root=LocalPose(model.transform);
                MeshFilter importedGround=UniqueComponent<MeshFilter>(model.transform,"IslandGround");
                report.terrainAsImportedMatch=PointMatch(original,WorldVertices(importedGround));
                ReflectRoot(model.transform,root);
                report.terrainReflectedMatch=PointMatch(original,WorldVertices(importedGround));
                bool reflect=report.terrainReflectedMatch>report.terrainAsImportedMatch;
                if(!reflect)RestoreLocal(model.transform,root);
                report.terrainOrientation=reflect?"measured-reflected-import-root-X":"measured-as-imported";
                Need(Mathf.Max(report.terrainAsImportedMatch,report.terrainReflectedMatch)>.90f,"Terrain import has <90% baseline vertex matches; axes/scale or candidate source are wrong.");
                foreach(string name in new[]{"IslandGround","CoastalCliff"})
                {
                    MeshFilter old=UniqueComponent<MeshFilter>(terrain,name,model.transform);
                    MeshFilter source=UniqueComponent<MeshFilter>(model.transform,name);
                    Renderer oldRenderer=old.GetComponent<Renderer>(), sourceRenderer=source.GetComponent<Renderer>();
                    var oldMats=oldRenderer.sharedMaterials.ToDictionary(m=>Clean(m.name),m=>m);
                    var groups=new Dictionary<Material,List<MeshPart>>();
                    for(int s=0;s<source.sharedMesh.subMeshCount;s++)
                    {
                        if(source.sharedMesh.GetIndexCount(s)==0)continue;
                        string key=Clean(sourceRenderer.sharedMaterials[s].name);
                        Need(oldMats.TryGetValue(key,out Material material),"Terrain has an unknown material: "+key);
                        if(!groups.TryGetValue(material,out var parts))groups.Add(material,parts=new List<MeshPart>());
                        parts.Add(new MeshPart(source.sharedMesh,s,old.transform.worldToLocalMatrix*source.transform.localToWorldMatrix));
                    }
                    Material[] mats=groups.Keys.OrderBy(m=>m.name,StringComparer.Ordinal).ToArray();
                    Mesh mesh=Combine(mats.Select(m=>groups[m]).ToArray(),name+"_V2_B");
                    SaveNew(mesh,report.generation+"/"+name+".asset");
                    old.sharedMesh=mesh;oldRenderer.sharedMaterials=mats;
                    MeshCollider[] colliders=old.GetComponents<MeshCollider>();
                    Need(colliders.Length==1,"Expected one original "+name+" MeshCollider.");
                    colliders[0].sharedMesh=null;colliders[0].sharedMesh=mesh;
                    Need(old.gameObject.layer==(name=="IslandGround"?8:9),"Terrain collision layer changed unexpectedly.");
                }
            }
            finally{Object.DestroyImmediate(model);}
        }

        static void AddWindowReceiver(GameObject island,string generation)
        {
            Transform target=Unique(island.transform,"Target_Window");
            Need(target.GetComponentsInChildren<Renderer>(true).Length==0,"Target_Window already has a renderer; inspect the gameplay interface instead of duplicating it.");
            // True aperture radius is ~.55m. This annulus occupies .48.. .51m only;
            // centre remains open. Position it 25mm inside, facing the existing target forward.
            var vertices=new List<Vector3>();var uv=new List<Vector2>();var indices=new List<int>();
            const int n=64;
            for(int i=0;i<n;i++)for(int j=0;j<2;j++)
            {float a=i*Mathf.PI*2/n,r=j==0?.48f:.51f;vertices.Add(new Vector3(Mathf.Cos(a)*r,Mathf.Sin(a)*r,-.025f));uv.Add(new Vector2((float)i/n,j));}
            for(int i=0;i<n;i++){int a=i*2,b=((i+1)%n)*2;indices.AddRange(new[]{a,a+1,b,a+1,b+1,b});}
            var mesh=new Mesh {name="RoundWindow_InnerAnnulus"};mesh.SetVertices(vertices);mesh.SetUVs(0,uv);mesh.SetTriangles(indices,0);mesh.RecalculateNormals();mesh.RecalculateBounds();
            SaveNew(mesh,generation+"/RoundWindowAnnulus.asset");
            Material material=NewLit("RoundWindow_WarmReflection",new Color(.40f,.24f,.10f),.28f,.34f,generation+"/RoundWindowWarmReflection.mat");
            material.SetFloat("_Cull",0);material.EnableKeyword("_EMISSION");material.SetColor("_EmissionColor",new Color(1,.54f,.19f)*.12f);
            material.globalIlluminationFlags=MaterialGlobalIlluminationFlags.RealtimeEmissive;
            EditorUtility.SetDirty(material);AssetDatabase.SaveAssetIfDirty(material);
            var go=new GameObject("RoundWindow");go.transform.SetParent(target,false);go.layer=9;
            go.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=go.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;
            renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=true;
            // No Collider or WindowGlow is attached. Claude owns the gameplay binding.
        }

        static void ApplyLookAndCoast(GameObject island,BuildReport report)
        {
            Renderer sky=UniqueComponent<Renderer>(Find(island.transform,"Atmosphere"),"NightSky");
            Renderer sea=UniqueComponent<Renderer>(Find(island.transform,"Atmosphere"),"NightSea");
            var skyMat=new Material(RequireShader("JieGuang/Environment/NightSkyV2")){name="NightSky_V2"};
            var seaMat=new Material(RequireShader("JieGuang/Environment/NightSeaV2")){name="NightSea_V2"};
            sky.sharedMaterial=skyMat;sea.sharedMaterial=seaMat;
            var library=EnvV2LookBuilder.CreateLibrary();var rig=EnvV2LookBuilder.Attach(island,library);var look=library.Get("night-1");
            skyMat.SetColor("_Zenith",look.zenith);skyMat.SetColor("_Horizon",look.horizon);skyMat.SetFloat("_EarthLitFraction",look.earthLitFraction);skyMat.SetFloat("_Stars",look.stars);skyMat.SetFloat("_CloudOpacity",look.cloudOpacity);
            seaMat.SetColor("_Deep",look.seaDeep);seaMat.SetColor("_Shallow",look.seaShallow);seaMat.SetColor("_Horizon",look.horizon);
            skyMat.SetFloat("_EnvTime",-1);seaMat.SetFloat("_EnvTime",-1);
            var seaFilter=sea.GetComponent<MeshFilter>();Vector3[] seaVertices=WorldVertices(seaFilter);
            Need(seaVertices.Length>0 && seaVertices.Max(v=>v.y)-seaVertices.Min(v=>v.y)<.001f,"NightSea must be a flat world-Y plane.");
            var coast=EnvV2ShoreMapBuilder.Bake(island,seaVertices[0].y,256,9);
            Need(coast.report.checks.All(c=>c.passed),"Coast map failed validation.");
            report.shoreReport=coast.report.reportAssetPath;
            report.warnings.AddRange(coast.report.warnings);
            if(!coast.report.contourClosed)report.warnings.Add("Shore contour is open; inspect the shoreline image before acceptance.");
            seaMat.SetTexture("_ShoreMap",coast.texture);seaMat.SetVector("_ShoreRect",coast.worldRect);seaMat.SetFloat("_ShoreEnabled",1);
            SaveNew(skyMat,report.generation+"/NightSky.mat");SaveNew(seaMat,report.generation+"/NightSea.mat");
            rig.ApplyChapter("night-1",true);RenderSettings.skybox=null;
        }

        static void Validate(GameObject island,BuildReport report)
        {
            var all=island.GetComponentsInChildren<Transform>(true);
            foreach(string name in Required)Check(report,"required:"+name,all.Count(t=>t.name==name)==1,"Exactly one.");
            report.spots=island.GetComponentsInChildren<Light>(true).Count(l=>l.type==LightType.Spot);
            Transform windows=Unique(island.transform,"Village_Windows");
            report.windows=windows.childCount;
            Check(report,"three-spotlights",report.spots==3,"Total Spot components, including inactive.");
            Check(report,"22-village-window-children",report.windows==22&&windows.Cast<Transform>().All(t=>t.GetComponentsInChildren<Renderer>(true).Length==1),"Each individually switchable child has exactly one renderer.");
            Check(report,"round-window-receiver",Unique(island.transform,"Target_Window").GetComponentsInChildren<Renderer>(true).Count(r=>r.name=="RoundWindow")==1,"Narrow interior annulus; no filled disk and no added collider.");
            foreach(Renderer r in island.GetComponentsInChildren<Renderer>(true))
            {
                MeshFilter f=r.GetComponent<MeshFilter>();if(f==null||f.sharedMesh==null)continue;
                long count=TriangleCount(f.sharedMesh);report.allLodRendererTriangles+=count;
                if(r.enabled&&r.gameObject.activeInHierarchy)report.enabledLodRendererTriangles+=count;
            }
            Check(report,"triangle-budget-including-all-lods",report.allLodRendererTriangles<=600000,"Count every render mesh instance, all LOD levels, inactive renderers, sky/sea; collider-only retained old meshes are separately preserved, not drawn.");
            foreach(MeshFilter filter in island.GetComponentsInChildren<MeshFilter>(true))
            {
                if(filter.sharedMesh==null)continue;
                long count=TriangleCount(filter.sharedMesh);report.allMeshFilterTriangles+=count;
                if(filter.GetComponent<Renderer>()==null)report.retainedNonRenderingMeshTriangles+=count;
            }
            Check(report,"conservative-budget-all-mesh-filters",report.allMeshFilterTriangles<=600000,"Count every MeshFilter instance including all LODs, disabled original village Structures and preserved old meshes without a Renderer. This conservative asset inventory is not a measured per-frame triangle count or FPS result.");
            Check(report,"ground-rays-preserved",report.groundBefore.Zip(report.groundAfter,(a,b)=>a.hit==b.hit&&(!a.hit||Mathf.Abs(a.height-b.height)<=.025f)).All(x=>x),"Baseline ground samples at anchors, original path vertices and 2m walkable interior grid; max height delta 2.5cm, own layer-8 colliders only.");
            Check(report,"lamp-target-blockers-preserved",report.beamsBefore.Zip(report.beamsAfter,(a,b)=>a.lamp==b.lamp&&a.target==b.target&&a.blockers.SequenceEqual(b.blockers)).All(x=>x),"Same seven beam rays, including GuiHang -> Target_Sea/Pier; same collider names before/after. Baseline blockers are reported, not silently called clear.");
            foreach(Beam b in report.beamsAfter.Where(b=>b.blockers.Length>0))report.warnings.Add("Existing beam blockers retained: "+b.lamp+" -> "+b.target+": "+string.Join(", ",b.blockers));
            foreach(var check in EnvV2MeadowBuilder.Validate(island).checks)Check(report,"meadow:"+check.name,check.passed,check.detail);
        }

        static List<Pose> Contract(GameObject root)
        {
            return root.GetComponentsInChildren<Transform>(true).Where(t=>
                t.name.StartsWith("Anchor_",StringComparison.Ordinal)||t.name.StartsWith("Target_",StringComparison.Ordinal)||t.name.StartsWith("NPC_",StringComparison.Ordinal)||t.name.StartsWith("Cam_",StringComparison.Ordinal)||t.name.StartsWith("Marker_",StringComparison.Ordinal)||
                t.name=="LampHead"||t.name.StartsWith("Sky_ScatterZone_",StringComparison.Ordinal)||t.name=="Village_Windows"||t.name=="Walkable_Boundary"||Ancestor(t,"Walkable_Boundary")||Ancestor(t,"Village_Windows"))
                .Select(t=>WorldPose(t,root.transform)).OrderBy(p=>p.path,StringComparer.Ordinal).ToList();
        }
        static List<Pose> ColliderState(Transform root)
        {
            return root.GetComponentsInChildren<Collider>(true).Select(c=>{Pose p=WorldPose(c.transform,root);p.path+="/"+c.GetType().Name;p.colliderJson=EditorJsonUtility.ToJson(c);return p;}).OrderBy(p=>p.path,StringComparer.Ordinal).ToList();
        }
        static List<Sample> GroundSamples(GameObject root,List<Sample> previous=null)
        {
            var positions=new List<Sample>();
            if(previous!=null)positions=previous.Select(s=>new Sample {name=s.name,point=s.point}).ToList();
            else
            {
                foreach(Transform t in root.GetComponentsInChildren<Transform>(true).Where(t=>t.name.StartsWith("Anchor_")||t.name.StartsWith("Target_")||t.name.StartsWith("NPC_")))positions.Add(new Sample {name=PathOf(t,root.transform),point=t.position});
                MeshFilter path=UniqueComponent<MeshFilter>(Find(root.transform,"Terrain"),"StonePaths");
                Vector3[] points=WorldVertices(path);for(int i=0;i<points.Length;i+=3)positions.Add(new Sample {name="path-vertex-"+i,point=points[i]});
                Transform boundary=Unique(root.transform,"Walkable_Boundary");LineRenderer line=boundary.GetComponent<LineRenderer>();
                Vector3[] polygon;
                if(line!=null&&line.positionCount>=3)
                {
                    polygon=new Vector3[line.positionCount];line.GetPositions(polygon);
                    if(!line.useWorldSpace)for(int i=0;i<polygon.Length;i++)polygon[i]=line.transform.TransformPoint(polygon[i]);
                }
                else
                {
                    // v1's actual prefab stores Point_000... children, not a LineRenderer.
                    Transform[] pointsInOrder=boundary.Cast<Transform>().Where(t=>Regex.IsMatch(t.name,@"^Point_\d+$")).OrderBy(t=>int.Parse(t.name.Substring(6),CultureInfo.InvariantCulture)).ToArray();
                    polygon=pointsInOrder.Select(t=>t.position).ToArray();
                }
                if(polygon.Length>3&&(polygon[0]-polygon[polygon.Length-1]).sqrMagnitude<1e-8f)polygon=polygon.Take(polygon.Length-1).ToArray();
                Need(polygon.Length>=3,"Expected a closed boundary LineRenderer or ordered Point_000 child contract.");
                for(float x=polygon.Min(p=>p.x)+1;x<polygon.Max(p=>p.x);x+=2)
                    for(float z=polygon.Min(p=>p.z)+1;z<polygon.Max(p=>p.z);z+=2)
                        if(Inside(new Vector3(x,0,z),polygon))positions.Add(new Sample {name="walk-grid-"+positions.Count,point=new Vector3(x,0,z)});
            }
            Collider[] ground=root.GetComponentsInChildren<Collider>(true).Where(c=>c.enabled&&!c.isTrigger&&c.gameObject.activeInHierarchy&&c.gameObject.layer==8).ToArray();
            foreach(Sample s in positions)
            {
                var ray=new Ray(new Vector3(s.point.x,60,s.point.z),Vector3.down);float best=float.PositiveInfinity;
                foreach(Collider collider in ground)if(collider.Raycast(ray,out RaycastHit hit,100)&&hit.distance<best){best=hit.distance;s.hit=true;s.height=hit.point.y;s.collider=PathOf(collider.transform,root.transform);}
            }
            return positions;
        }
        static List<Beam> BeamSamples(GameObject root)
        {
            var pairs=new[]{new[]{"Anchor_Lamp_WanFeng","Target_Path"},new[]{"Anchor_Lamp_WanFeng","Target_Bench"},new[]{"Anchor_Lamp_YueChuang","Target_Window"},new[]{"Anchor_Lamp_YueChuang","Target_Pier"},new[]{"Anchor_Lamp_GuiHang","Target_Bench"},new[]{"Anchor_Lamp_GuiHang","Target_Pier"},new[]{"Anchor_Lamp_GuiHang","Target_Sea"}};
            Collider[] colliders=root.GetComponentsInChildren<Collider>(true).Where(c=>c.enabled&&!c.isTrigger&&c.gameObject.activeInHierarchy).ToArray();
            var result=new List<Beam>();
            foreach(string[] pair in pairs)
            {
                Transform lamp=Unique(root.transform,pair[0]),target=Unique(root.transform,pair[1]);Vector3 delta=target.position-lamp.position;
                Ray ray=new Ray(lamp.position+delta.normalized*.45f,delta.normalized);
                result.Add(new Beam {lamp=pair[0],target=pair[1],blockers=colliders.Where(c=>!c.transform.IsChildOf(lamp)&&c.Raycast(ray,out _,Mathf.Max(0,delta.magnitude-.8f))).Select(c=>PathOf(c.transform,root.transform)).OrderBy(x=>x,StringComparer.Ordinal).ToArray()});
            }
            return result;
        }

        static void CaptureScene(string path,string group,string folder,CaptureReport report,bool frozenBaseline,bool candidate)
        {
            Scene previous=SceneManager.GetActiveScene(),scene=EditorSceneManager.OpenScene(path,OpenSceneMode.Additive);
            var transient=new List<Object>();
            try
            {
                Need(SceneManager.SetActiveScene(scene),"Could not activate owned capture scene.");
                GameObject island=scene.GetRootGameObjects().Single(g=>g.name=="Island");
                Camera[] cameras=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Camera>(true)).ToArray();
                Need(cameras.Length==1,"Expected exactly one saved owned study camera; do not select an arbitrary gameplay camera.");
                Camera camera=cameras[0];camera.enabled=false;camera.scene=scene;camera.aspect=(float)Width/Height;
                ulong cullingMask=EditorSceneManager.CalculateAvailableSceneCullingMask();
                Need(cullingMask!=0,"No isolated native scene culling bit is available.");
                EditorSceneManager.SetSceneCullingMask(scene,cullingMask);camera.overrideSceneCullingMask=cullingMask;
                foreach(Scene other in LoadedScenes().Where(s=>s.handle!=scene.handle))
                    Need((EditorSceneManager.GetSceneCullingMask(other)&cullingMask)==0,"Temporary scene mask overlaps a foreign scene.");
                var cameraData=camera.GetComponent<UniversalAdditionalCameraData>();
                int originalVolumeMask=cameraData!=null?cameraData.volumeLayerMask.value:1;
                int isolatedVolumeMask=IsolateOwnVolumes(scene,camera,originalVolumeMask,out int ownVolumes);
                if(candidate)
                {
                    Need(camera.allowHDR&&camera.GetComponent<UniversalAdditionalCameraData>()?.renderPostProcessing==true,"Candidate test scene must persist HDR and postprocessing.");
                    island.GetComponentInChildren<EnvironmentLookRig>(true).ApplyChapter("night-1",true);
                    FreezeBlocks(island);
                }
                if(frozenBaseline)FreezeBaselineShaders(island,transient);
                string destination=Path.Combine(folder,group);Directory.CreateDirectory(destination);
                foreach(View view in Views)
                {
                    SetView(camera,view);
                    var row=new CaptureRow {group=group,file=group+"/"+view.file,camera=view.name,position=view.position,forward=(view.look-view.position).normalized,fov=camera.fieldOfView,near=camera.nearClipPlane,far=camera.farClipPlane,hdr=camera.allowHDR,postProcessing=camera.GetComponent<UniversalAdditionalCameraData>()?.renderPostProcessing==true,fog=RenderSettings.fog,reflectionIntensity=RenderSettings.reflectionIntensity,ambientSky=RenderSettings.ambientSkyColor,ambientEquator=RenderSettings.ambientEquatorColor,ambientGround=RenderSettings.ambientGroundColor,msaa=1,sceneCullingMask="0x"+cullingMask.ToString("X16"),originalVolumeMask=originalVolumeMask,isolatedVolumeMask=isolatedVolumeMask,ownVolumes=ownVolumes,shaderTime=candidate?"V2 _EnvTime/_WindTime = 12":frozenBaseline?"Copied V1 diagnostic shader: _Time.y constant 12; other settings original":"Unmodified original V1 shader _Time.y (live; not frozen)"};
                    row.method=Render(camera,Path.Combine(destination,view.file));report.images.Add(row);
                }
            }
            finally
            {
                if(previous.IsValid()&&previous.isLoaded)SceneManager.SetActiveScene(previous);
                if(scene.IsValid()&&scene.isLoaded)EditorSceneManager.CloseScene(scene,true);
                foreach(Object o in transient)if(o!=null)Object.DestroyImmediate(o);
            }
        }
        static int IsolateOwnVolumes(Scene scene,Camera camera,int originalMask,out int count)
        {
            var data=camera.GetComponent<UniversalAdditionalCameraData>();
            Volume[] included=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<Volume>(true)).Where(v=>(originalMask&(1<<v.gameObject.layer))!=0).ToArray();
            count=included.Length;
            // With postprocessing off, the original baseline must not gain AdditionalCameraData.
            if(data==null||!data.renderPostProcessing)return originalMask;
            // Include registered preview/hidden volumes too, rather than assuming every
            // foreign Volume belongs to a normal loaded SceneManager scene.
            Volume[] excluded=Resources.FindObjectsOfTypeAll<Volume>().Where(v=>!included.Contains(v)).ToArray();
            int layer=-1;
            for(int i=31;i>=0;i--)if(!excluded.Any(v=>v.gameObject.layer==i)){layer=i;break;}
            Need(layer>=0,"All 32 layers contain foreign Volumes; cannot isolate without changing them.");
            // Layer reassignment is on our temporary scene only and never saved.
            foreach(Volume v in included)
            {
                // Volume.UpdateLayer runs on a later Editor update. Explicit disable/enable
                // unregisters the old layer and registers the new layer before immediate capture.
                bool enabled=v.enabled;v.enabled=false;v.gameObject.layer=layer;v.enabled=enabled;
            }
            data.volumeLayerMask=1<<layer;
            return data.volumeLayerMask.value;
        }
        static Scene[] LoadedScenes(){var result=new List<Scene>();for(int i=0;i<SceneManager.sceneCount;i++){Scene s=SceneManager.GetSceneAt(i);if(s.isLoaded)result.Add(s);}return result.ToArray();}
        static void FreezeBaselineShaders(GameObject island,List<Object> transient)
        {
            string folder=Root+"/Generated/V2CaptureDiagnostics/FrozenV1_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff");EnsureFolder(folder);
            var shaderCache=new Dictionary<Shader,Shader>();var materialCache=new Dictionary<Material,Material>();int index=0;
            foreach(Renderer renderer in island.GetComponentsInChildren<Renderer>(true))
            {
                Material[] mats=renderer.sharedMaterials;bool changed=false;
                for(int i=0;i<mats.Length;i++)
                {
                    Material original=mats[i];if(original==null||original.shader==null)continue;
                    string shaderPath=AssetDatabase.GetAssetPath(original.shader);
                    if(!shaderPath.StartsWith(Root+"/Shaders/",StringComparison.Ordinal))continue;
                    string text=File.ReadAllText(ProjectFile(shaderPath));if(!Regex.IsMatch(text,@"\b_Time\.y\b"))continue;
                    if(!shaderCache.TryGetValue(original.shader,out Shader shader))
                    {
                        string name="JieGuang/Environment/Diagnostics/FrozenV1_"+Guid.NewGuid().ToString("N");
                        text=Regex.Replace(text,"Shader\\s+\"[^\"]+\"","Shader \""+name+"\"",RegexOptions.None);
                        text=Regex.Replace(text,@"\b_Time\.y\b",FreezeSeconds.ToString("0.0",CultureInfo.InvariantCulture));
                        string asset=folder+"/Frozen_"+(index++)+".shader";File.WriteAllText(ProjectFile(asset),text);
                        AssetDatabase.ImportAsset(asset,ImportAssetOptions.ForceSynchronousImport);
                        shader=Load<Shader>(asset);Need(!ShaderUtil.ShaderHasError(shader),"Copied frozen V1 shader failed compilation.");shaderCache.Add(original.shader,shader);
                    }
                    if(!materialCache.TryGetValue(original,out Material copy))
                    {copy=new Material(original){name=original.name+"_Time12Diagnostic",shader=shader};materialCache.Add(original,copy);transient.Add(copy);}
                    mats[i]=copy;changed=true;
                }
                if(changed)renderer.sharedMaterials=mats;
            }
            Need(shaderCache.Count>=1,"No V1 time shader was replaced; a frozen label would be false.");
        }
        static void FreezeOwnedTestMaterials(GameObject island,string folder)
        {
            EnsureFolder(folder);var copies=new Dictionary<Material,Material>();int n=0;
            foreach(Renderer r in island.GetComponentsInChildren<Renderer>(true))
            {
                Material[] mats=r.sharedMaterials;bool changed=false;
                for(int i=0;i<mats.Length;i++)
                {
                    Material m=mats[i];if(m==null||(!m.HasProperty("_EnvTime")&&!m.HasProperty("_WindTime")))continue;
                    if(!copies.TryGetValue(m,out Material copy))
                    {copy=new Material(m){name=m.name+"_StudyTime12"};if(copy.HasProperty("_EnvTime"))copy.SetFloat("_EnvTime",FreezeSeconds);if(copy.HasProperty("_WindTime"))copy.SetFloat("_WindTime",FreezeSeconds);SaveNew(copy,folder+"/Time12_"+(n++)+".mat");copies.Add(m,copy);}
                    mats[i]=copy;changed=true;
                }
                if(changed)r.sharedMaterials=mats;
            }
        }
        static void FreezeBlocks(GameObject root)
        {
            foreach(Renderer r in root.GetComponentsInChildren<Renderer>(true))
            {var block=new MaterialPropertyBlock();r.GetPropertyBlock(block);if(r.sharedMaterials.Any(m=>m!=null&&m.HasProperty("_EnvTime")))block.SetFloat("_EnvTime",FreezeSeconds);if(r.sharedMaterials.Any(m=>m!=null&&m.HasProperty("_WindTime")))block.SetFloat("_WindTime",FreezeSeconds);r.SetPropertyBlock(block);}
        }
        static string Render(Camera camera,string path)
        {
            RenderTexture rt=RenderTexture.GetTemporary(Width,Height,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB,1);
            RenderTexture active=RenderTexture.active,old=camera.targetTexture;Texture2D pixels=null;
            try
            {
                camera.targetTexture=rt;var request=new RenderPipeline.StandardRequest {destination=rt};
                Need(RenderPipeline.SupportsRenderRequest(camera,request),"Current pipeline does not support StandardRequest.");
                RenderPipeline.SubmitRenderRequest(camera,request);RenderTexture.active=rt;
                pixels=new Texture2D(Width,Height,TextureFormat.RGB24,false,false);pixels.ReadPixels(new Rect(0,0,Width,Height),0,0,false);pixels.Apply(false,false);File.WriteAllBytes(path,pixels.EncodeToPNG());
                return "RenderPipeline.StandardRequest / ARGB32 sRGB output / internal HDR follows saved camera";
            }
            finally{camera.targetTexture=old;RenderTexture.active=active;if(pixels!=null)Object.DestroyImmediate(pixels);RenderTexture.ReleaseTemporary(rt);}
        }
        static void ConfigureCandidateCamera(Camera camera)
        {camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.006f,.013f,.032f,1);camera.nearClipPlane=.08f;camera.farClipPlane=450;camera.allowMSAA=true;camera.aspect=(float)Width/Height;EnvV2LookBuilder.ConfigureTestCamera(camera);}
        static void SetView(Camera camera,View view){camera.transform.SetPositionAndRotation(view.position,Quaternion.LookRotation(view.look-view.position,Vector3.up));camera.fieldOfView=view.fov;}

        sealed class MeshPart { public Mesh mesh;public int submesh;public Matrix4x4 matrix;public MeshPart(Mesh m,int s,Matrix4x4 t){mesh=m;submesh=s;matrix=t;} }
        static Mesh Combine(List<MeshPart>[] groups,string name)
        {
            var vertices=new List<Vector3>();var normals=new List<Vector3>();var uv=new List<Vector2>();var indices=new List<int[]>();
            foreach(List<MeshPart> group in groups)
            {
                var faces=new List<int>();
                foreach(MeshPart p in group)
                {
                    Need(p.mesh!=null&&p.mesh.isReadable&&p.mesh.GetTopology(p.submesh)==MeshTopology.Triangles,"Readable triangular mesh required.");
                    Vector3[] v=p.mesh.vertices,n=p.mesh.normals;Vector2[] tex=p.mesh.uv;Matrix4x4 normal=p.matrix.inverse.transpose;
                    Need(n.Length==v.Length&&tex.Length==v.Length,"Candidate source must contain real normals and UVs; refusing invented upward normals/empty UVs.");
                    int[] tris=p.mesh.GetTriangles(p.submesh);bool reflected=p.matrix.determinant<0;
                    var remap=new Dictionary<int,int>();
                    foreach(int i in tris.Distinct())
                    {
                        remap.Add(i,vertices.Count);vertices.Add(p.matrix.MultiplyPoint3x4(v[i]));
                        normals.Add(n.Length==v.Length?normal.MultiplyVector(n[i]).normalized:Vector3.up);
                        uv.Add(tex.Length==v.Length?tex[i]:Vector2.zero);
                    }
                    for(int t=0;t<tris.Length;t+=3){faces.Add(remap[tris[t]]);faces.Add(remap[tris[t+(reflected?2:1)]]);faces.Add(remap[tris[t+(reflected?1:2)]]);}
                }
                indices.Add(faces.ToArray());
            }
            var mesh=new Mesh {name=name,indexFormat=vertices.Count>65535?IndexFormat.UInt32:IndexFormat.UInt16};mesh.SetVertices(vertices);mesh.SetNormals(normals);mesh.SetUVs(0,uv);mesh.subMeshCount=indices.Count;
            for(int i=0;i<indices.Count;i++)mesh.SetTriangles(indices[i],i,false);mesh.RecalculateBounds();mesh.RecalculateTangents();return mesh;
        }
        static float MarkerError(GameObject model,Dictionary<string,Vector3> expected)
        {
            float worst=0;foreach(var pair in expected){Transform t=Unique(model.transform,pair.Key);worst=Mathf.Max(worst,Vector3.Distance(t.position,pair.Value));}return worst;
        }
        static Vector3[] WorldVertices(MeshFilter filter)
        {Need(filter!=null&&filter.sharedMesh!=null&&filter.sharedMesh.isReadable,"Readable mesh required for geometry measurement.");return filter.sharedMesh.vertices.Select(v=>filter.transform.TransformPoint(v)).ToArray();}
        static float PointMatch(Vector3[] original,Vector3[] candidate)
        {
            // Millimetre cells, neighbour search avoids rounding-boundary false mismatches.
            const float cell=.003f;var grid=new Dictionary<Vector3Int,List<Vector3>>();
            Func<Vector3,Vector3Int> key=v=>new Vector3Int(Mathf.FloorToInt(v.x/cell),Mathf.FloorToInt(v.y/cell),Mathf.FloorToInt(v.z/cell));
            foreach(Vector3 v in original){var k=key(v);if(!grid.TryGetValue(k,out var list))grid.Add(k,list=new List<Vector3>());list.Add(v);}
            var unique=candidate.GroupBy(v=>key(v)).Select(g=>g.First()).ToArray();int matches=0;
            foreach(Vector3 v in unique){var k=key(v);bool match=false;for(int x=-1;x<=1&&!match;x++)for(int y=-1;y<=1&&!match;y++)for(int z=-1;z<=1&&!match;z++)if(grid.TryGetValue(k+new Vector3Int(x,y,z),out var points))match=points.Any(p=>(p-v).sqrMagnitude<.000004f);if(match)matches++;}
            return unique.Length==0?0:(float)matches/unique.Length;
        }
        static bool Inside(Vector3 p,Vector3[] polygon)
        {bool inside=false;for(int i=0,j=polygon.Length-1;i<polygon.Length;j=i++){Vector3 a=polygon[i],b=polygon[j];if((a.z>p.z)!=(b.z>p.z)&&p.x<(b.x-a.x)*(p.z-a.z)/(b.z-a.z)+a.x)inside=!inside;}return inside;}
        static Pose LocalPose(Transform t)=>new Pose {position=t.localPosition,rotation=t.localRotation,scale=t.localScale};
        static void RestoreLocal(Transform t,Pose p){t.localPosition=p.position;t.localRotation=p.rotation;t.localScale=p.scale;}
        static void ReflectRoot(Transform t,Pose p){t.localPosition=new Vector3(-p.position.x,p.position.y,p.position.z);t.localRotation=new Quaternion(p.rotation.x,-p.rotation.y,-p.rotation.z,p.rotation.w);t.localScale=new Vector3(-p.scale.x,p.scale.y,p.scale.z);}
        static Pose WorldPose(Transform t,Transform root)=>new Pose {path=PathOf(t,root),position=t.position,rotation=t.rotation,scale=t.localScale,layer=t.gameObject.layer,active=t.gameObject.activeSelf};
        static bool SamePoses(List<Pose> a,List<Pose> b)=>a.Count==b.Count&&a.Zip(b,(x,y)=>x.path==y.path&&(x.position-y.position).sqrMagnitude<1e-8f&&(x.rotation.Equals(y.rotation)||Quaternion.Angle(x.rotation,y.rotation)<.001f)&&(x.scale-y.scale).sqrMagnitude<1e-8f&&x.layer==y.layer&&x.active==y.active&&x.colliderJson==y.colliderJson).All(v=>v);
        static bool MatrixNear(Matrix4x4 a,Matrix4x4 b){for(int i=0;i<16;i++)if(Mathf.Abs(a[i]-b[i])>1e-7f)return false;return true;}
        static long TriangleCount(Mesh m){long n=0;for(int i=0;i<m.subMeshCount;i++)if(m.GetTopology(i)==MeshTopology.Triangles)n+=(long)m.GetIndexCount(i)/3;return n;}
        static string Clean(string value)=>Regex.Replace(value.Replace(" (Instance)",""),@"\.\d{3}$","");
        static bool Ancestor(Transform t,string name){for(Transform p=t.parent;p!=null;p=p.parent)if(p.name==name)return true;return false;}
        static string PathOf(Transform t,Transform root){var names=new List<string>();for(;t!=null&&t!=root;t=t.parent)names.Add(t.name);names.Reverse();return string.Join("/",names);}
        static Transform Find(Transform root,string path){Transform t=root.Find(path);Need(t!=null,"Missing path "+path);return t;}
        static Transform Unique(Transform root,string name){Transform[] matches=root.GetComponentsInChildren<Transform>(true).Where(t=>t.name==name).ToArray();Need(matches.Length==1,"Expected exactly one "+name+"; found "+matches.Length);return matches[0];}
        static T UniqueComponent<T>(Transform root,string name,Transform excluded=null) where T:Component
        {T[] matches=root.GetComponentsInChildren<T>(true).Where(c=>c.name==name&&(excluded==null||!c.transform.IsChildOf(excluded))).ToArray();Need(matches.Length==1,"Expected one "+typeof(T).Name+" named "+name+"; found "+matches.Length);return matches[0];}
        static T Load<T>(string path) where T:Object {T result=AssetDatabase.LoadAssetAtPath<T>(path);if(result==null)throw new FileNotFoundException("Stage/import the required owned asset before running.",path);return result;}
        static Shader RequireShader(string name){Shader shader=Shader.Find(name);Need(shader!=null&&shader.isSupported&&!ShaderUtil.ShaderHasError(shader),"Missing/unsupported/failed shader "+name);return shader;}
        static Material NewLit(string name,Color color,float metallic,float smoothness,string path)
        {var m=new Material(RequireShader("Universal Render Pipeline/Lit")){name=name,enableInstancing=true};m.SetColor("_BaseColor",color);m.SetFloat("_Metallic",metallic);m.SetFloat("_Smoothness",smoothness);SaveNew(m,path);return m;}
        static void PrepareModel(string path)
        {
            var importer=AssetImporter.GetAtPath(path) as ModelImporter;Need(importer!=null,"Expected FBX ModelImporter at "+path);
            if(!importer.isReadable||importer.importAnimation||importer.addCollider){importer.isReadable=true;importer.importAnimation=false;importer.addCollider=false;importer.SaveAndReimport();}
            // Existing axis/globalScale/useFileScale/bakeAxisConversion are never guessed or overwritten.
        }
        static void EnsureFolder(string path)
        {Need(path.StartsWith(Root+"/",StringComparison.Ordinal)&&!path.Contains(".."),"Owned Environment output required.");if(AssetDatabase.IsValidFolder(path))return;string parent=path.Substring(0,path.LastIndexOf('/'));if(parent!=Root)EnsureFolder(parent);Need(AssetDatabase.IsValidFolder(parent),"Environment root must exist.");AssetDatabase.CreateFolder(parent,path.Substring(path.LastIndexOf('/')+1));}
        static string ProjectFile(string path)=>Path.GetFullPath(Path.Combine(Directory.GetParent(Application.dataPath).FullName,path));
        static void SaveNew(Object asset,string path){EnsureFolder(path.Substring(0,path.LastIndexOf('/')));Need(AssetDatabase.LoadMainAssetAtPath(path)==null,"Refusing to overwrite generated asset "+path);AssetDatabase.CreateAsset(asset,path);AssetDatabase.SaveAssetIfDirty(asset);}
        static void Backup(string source,string destination){if(AssetDatabase.LoadMainAssetAtPath(source)!=null)Need(AssetDatabase.CopyAsset(source,destination),"Could not back up old candidate output.");}
        static void WriteJson(string path,object report){Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,JsonUtility.ToJson(report,true),new System.Text.UTF8Encoding(false));}
        static void Idle(){Need(!EditorApplication.isPlayingOrWillChangePlaymode&&!EditorApplication.isCompiling&&!EditorApplication.isUpdating,"Editor must be idle, outside Play/import/compilation. Obtain ownership and run CLI status/pipeline checks before invoking.");Need(PrefabStageUtility.GetCurrentPrefabStage()==null,"Exit Prefab Mode before operating independent study scenes; no prefab stage is closed or saved automatically.");}
        static void AssertClosed(string path){for(int i=0;i<SceneManager.sceneCount;i++)Need(SceneManager.GetSceneAt(i).path!=path,"Close the owned study scene before running: "+path+". This tool never closes a user's already-open scene.");}
        static void Need(bool ok,string message){if(!ok)throw new InvalidOperationException(message);}
        static void Check(BuildReport report,string name,bool passed,string detail)=>report.checks.Add(new CheckResult {name=name,passed=passed,detail=detail});
        static void FailChecks(BuildReport report){Need(report.checks.All(c=>c.passed),"Candidate validation failed: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name)));}
        sealed class SceneGuard
        {
            readonly Scene active=SceneManager.GetActiveScene();readonly List<Scene> scenes=new List<Scene>();readonly List<bool> dirty=new List<bool>();
            readonly List<ulong> masks=new List<ulong>();readonly List<bool> loaded=new List<bool>();readonly EnvironmentSnapshot environment=new EnvironmentSnapshot();
            public SceneGuard(){for(int i=0;i<SceneManager.sceneCount;i++){Scene s=SceneManager.GetSceneAt(i);scenes.Add(s);dirty.Add(s.isDirty);loaded.Add(s.isLoaded);masks.Add(s.isLoaded?EditorSceneManager.GetSceneCullingMask(s):0);}}
            public void RestoreAndClose(Scene owned)
            {
                // Unity selects the active scene's serialized lighting settings. Restore that
                // owner, rather than writing copied global values into somebody else's scene.
                if(active.IsValid()&&active.isLoaded)Need(SceneManager.SetActiveScene(active),"Failed to restore previous active scene.");
                if(owned.IsValid()&&owned.isLoaded&&!scenes.Any(s=>s.handle==owned.handle))EditorSceneManager.CloseScene(owned,true);
            }
            public bool Unchanged()=>SceneManager.GetActiveScene().handle==active.handle&&SceneManager.sceneCount==scenes.Count&&scenes.Select((s,i)=>s.IsValid()&&s.isLoaded==loaded[i]&&s.isDirty==dirty[i]&&(!s.isLoaded||EditorSceneManager.GetSceneCullingMask(s)==masks[i])).All(v=>v)&&environment.EqualsCurrent();
            public string Describe()=>"Original active scene="+active.path+"; original loaded scene count="+scenes.Count+"; original dirty flags="+string.Join(",",dirty)+"; RenderSettings restored="+environment.EqualsCurrent()+". Active owner restoration is verified against original fog/ambient/reflection/skybox/sun values; no foreign scene saved, closed, cleared or restored from disk.";
        }
        sealed class EnvironmentSnapshot
        {
            readonly AmbientMode ambientMode=RenderSettings.ambientMode;
            readonly Color ambient=RenderSettings.ambientLight,sky=RenderSettings.ambientSkyColor,equator=RenderSettings.ambientEquatorColor,ground=RenderSettings.ambientGroundColor,fogColor=RenderSettings.fogColor;
            readonly float intensity=RenderSettings.ambientIntensity,reflection=RenderSettings.reflectionIntensity,fogStart=RenderSettings.fogStartDistance,fogEnd=RenderSettings.fogEndDistance,fogDensity=RenderSettings.fogDensity;
            readonly bool fog=RenderSettings.fog;readonly FogMode fogMode=RenderSettings.fogMode;
            readonly Material skybox=RenderSettings.skybox;readonly Light sun=RenderSettings.sun;
            public bool EqualsCurrent()=>ambientMode==RenderSettings.ambientMode&&ambient.Equals(RenderSettings.ambientLight)&&sky.Equals(RenderSettings.ambientSkyColor)&&equator.Equals(RenderSettings.ambientEquatorColor)&&ground.Equals(RenderSettings.ambientGroundColor)&&fogColor.Equals(RenderSettings.fogColor)&&intensity.Equals(RenderSettings.ambientIntensity)&&reflection.Equals(RenderSettings.reflectionIntensity)&&fogStart.Equals(RenderSettings.fogStartDistance)&&fogEnd.Equals(RenderSettings.fogEndDistance)&&fogDensity.Equals(RenderSettings.fogDensity)&&fog==RenderSettings.fog&&fogMode==RenderSettings.fogMode&&skybox==RenderSettings.skybox&&sun==RenderSettings.sun;
        }
    }
}
#endif
