#if UNITY_EDITOR
// Explicit candidate-only helper. No menu/load hooks, prefab/scene save, importer or global settings writes.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV2PierBenchBuilder
    {
        const string Root = "Assets/JieGuang/Environment/";
        const string PierGuid = "3ba3734652ccd4b4a907f24c903b84d9", BenchGuid = "eb87eb5efe6a6fa41b958080400c27de";
        const string EndGuid = "e46c0304041391a4b9451bf07fbf3f28";
        const string WoodSha = "2507398730afcf58404ccfe7e75debefb688d760945f212250702e6d938c3fc1";
        // 20 micrometres allows single-precision import/world-transform roundoff, not intentional shape edits.
        const float GeometryTolerance = .00002f, MarkerTolerance = .00002f;
        static readonly string[] PierSlots = { "Wood_Endgrain", "Wood_Honey", "Wood_DarkBeams", "Wood_Weathered", "Iron_Blackened" };
        static readonly string[] BenchSlots = { "Wood_Endgrain", "Wood_DarkBeams", "Wood_Honey" };
        static readonly string[] WoodNames = { "Wood_Endgrain", "Wood_Honey", "Wood_DarkBeams", "Wood_Weathered" };
        static readonly string[] CoastalNames = { "CoastalWood_Light", "CoastalWood_Brown", "CoastalWood_Dark", "CoastalWood_Silver" };
        static readonly Color[] Tints = { new Color(.62f,.57f,.46f,1), new Color(.48f,.42f,.33f,1), new Color(.26f,.22f,.17f,1), new Color(.38f,.38f,.32f,1) };
        static readonly float[] Roughness = { .88f, .87f, .90f, .92f };

        [Serializable] public sealed class MaterialRecord { public string source, destination, assetPath; public Color tint; public float roughness; }
        [Serializable] public sealed class MarkerRecord { public string path; public int instanceId; public float[] worldMatrix; }
        [Serializable] public sealed class CollisionRecord
        {
            public string path, type, serializedState, meshAsset, meshGuid; public int instanceId, meshInstanceId;
            public float[] worldMatrix;
        }
        [Serializable] public sealed class Replacement
        {
            public string path, type, originalMeshAsset, originalMeshFileSha256, originalMeshContentSha256;
            public string candidateAsset, candidateFileSha256, manifestGeometrySha256Reference, generatedMeshAsset, generatedMeshContentSha256;
            public int trianglesBefore, trianglesAfter, submeshes, oldVertices, newVertices;
            public int uvVertices, matchedOrientedTriangles; public bool flippedWinding, uv0Present;
            public float matrixDeterminant, markerMatrixError, bidirectionalVertexErrorWorld, triangleCornerErrorWorld;
            public float largestNormalAngleDegrees; public float[] newMeshToOldStructure;
        }
        [Serializable] public sealed class Report
        {
            public string status, generationPath, reportAssetPath, woodTexture, woodTextureSha256;
            public int pierModules, benches, pierEnds, targetTrianglesBefore, targetTrianglesAfter, additionalTriangles;
            public int meshFiltersBefore, meshFiltersAfter, protectedTransforms, sharedWoodMaterials;
            public long allMeshFilterTrianglesBefore, allMeshFilterTrianglesAfter;
            public List<Replacement> replacements = new List<Replacement>();
            public List<MaterialRecord> materialMapping = new List<MaterialRecord>();
            public List<MarkerRecord> markersBefore = new List<MarkerRecord>(), markersAfter = new List<MarkerRecord>();
            public List<CollisionRecord> collisionsBefore = new List<CollisionRecord>(), collisionsAfter = new List<CollisionRecord>();
            public List<string> checks = new List<string>(), limitations = new List<string>();
        }
        sealed class Target
        {
            public string type; public Transform root, lod; public MeshFilter filter; public MeshRenderer renderer;
            public Transform[] markers; public Mesh originalMesh; public Material[] originalMaterials;
            public string originalContentHash; public Mesh baked; public Replacement result;
        }
        sealed class Source
        {
            public string path, sha, geometryReference; public GameObject root; public MeshFilter filter; public Transform[] markers;
        }

        /// <summary>
        /// Replaces only the existing 3 pier_module + 1 bench visual mesh/material references on a disposable,
        /// completely unpacked Island in an unsaved scene. Imported source FBX must already be readable.
        /// Keeps the old bench MeshCollider.sharedMesh and all original hierarchy/renderer settings.
        /// On failure references are restored where possible; caller must discard the candidate scene.
        /// </summary>
        public static Report Build(GameObject island, string generationFolder, string woodTexture)
        {
            ValidateCandidate(island);
            generationFolder = OwnedPath(generationFolder, Root + "Generated/").TrimEnd('/');
            woodTexture = OwnedPath(woodTexture, Root);
            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(woodTexture);
            Need(texture != null && ShaFile(woodTexture) == WoodSha, "Use the exact original wood_albedo_v1.png from the coastal manifest.");
            var ti = AssetImporter.GetAtPath(woodTexture) as TextureImporter;
            Need(ti != null && ti.sRGBTexture && ti.mipmapEnabled && ti.wrapMode == TextureWrapMode.Repeat && ti.filterMode != FilterMode.Point,
                "Caller must prepare the owned wood texture as sRGB, mipmapped, Repeat and filtered. This helper never edits importers.");
            Shader shader = Shader.Find("Universal Render Pipeline/Lit"); Need(shader != null, "URP Lit is required.");
            Transform pier = Direct(island.transform, "Pier"), props = Direct(island.transform, "Props");
            Target[] targets = new Target[4];
            for (int i = 0; i < 3; i++) targets[i] = LoadTarget(Direct(pier, "PierDeck_" + (i+1).ToString("00")), false,
                new Vector3(10,2.48f,-17.5f + i*3));
            targets[3] = LoadTarget(Direct(props, "Bench"), true, new Vector3(9,2.4f,-21));
            MeshFilter[] allFilters = island.GetComponentsInChildren<MeshFilter>(true);
            Need(allFilters.Count(f => MeshGuid(f.sharedMesh) == PierGuid) == 3 && allFilters.Count(f => MeshGuid(f.sharedMesh) == BenchGuid) == 1
                && allFilters.Count(f => MeshGuid(f.sharedMesh) == EndGuid) == 0,
                "Expected exactly 3 original pier_module meshes, 1 original bench, no pier_end; refuses repeated or changed integration.");
            Need(Vector3.Distance(Unique(island.transform,"NPC_Bench").position, targets[3].markers[0].position) < GeometryTolerance,
                "Original bench seat marker no longer matches the story NPC position.");
            var report = new Report { status = "preflight", pierModules = 3, benches = 1, pierEnds = 0, woodTexture = woodTexture,
                woodTextureSha256 = WoodSha, meshFiltersBefore = allFilters.Length, allMeshFilterTrianglesBefore = TotalTriangles(island) };
            report.collisionsBefore = Collisions(targets, island.transform); report.markersBefore = Markers(island.transform);
            var protectedState = new ProtectedState(island, targets); report.protectedTransforms = protectedState.TransformCount;
            Source pierSource = LoadSource(false), benchSource = LoadSource(true);
            try
            {
                // Every source, slot, marker, face and collider preflight passes before scene/material mutations.
                foreach (Target target in targets)
                {
                    Source source = target.type == "bench" ? benchSource : pierSource;
                    var result = new Replacement { path = HierarchyPath(target.filter.transform,island.transform), type = target.type,
                        originalMeshAsset = AssetDatabase.GetAssetPath(target.originalMesh), originalMeshContentSha256 = target.originalContentHash,
                        originalMeshFileSha256 = ShaFile(AssetDatabase.GetAssetPath(target.originalMesh)), candidateAsset = source.path,
                        candidateFileSha256 = source.sha, manifestGeometrySha256Reference = source.geometryReference,
                        trianglesBefore = Triangles(target.originalMesh), oldVertices = target.originalMesh.vertexCount };
                    // Full marker frames, not forward-only or origin-only: no guessed FBX -90X/X reflection.
                    Matrix4x4 sourceToOld = target.filter.transform.worldToLocalMatrix * target.markers[0].localToWorldMatrix
                        * source.markers[0].worldToLocalMatrix * source.filter.transform.localToWorldMatrix;
                    ValidateMatrix(sourceToOld); result.matrixDeterminant = sourceToOld.determinant;
                    result.newMeshToOldStructure = MatrixValues(sourceToOld); result.flippedWinding = sourceToOld.determinant < 0;
                    for (int j = 0; j < target.markers.Length; j++)
                    {
                        Matrix4x4 predicted = target.filter.transform.localToWorldMatrix * sourceToOld
                            * source.filter.transform.worldToLocalMatrix * source.markers[j].localToWorldMatrix;
                        result.markerMatrixError = Mathf.Max(result.markerMatrixError, MatrixError(predicted,target.markers[j].localToWorldMatrix));
                    }
                    Need(result.markerMatrixError <= MarkerTolerance, "Full marker frames disagree: " + result.path);
                    target.baked = Bake(source.filter.sharedMesh,sourceToOld,target.type + "_CoastalUV"); target.result = result;
                    CompareGeometry(target.originalMesh,target.baked,target.filter.transform.localToWorldMatrix,result);
                    result.generatedMeshContentSha256 = MeshContentHash(target.baked);
                    report.replacements.Add(result); report.targetTrianglesBefore += result.trianglesBefore; report.targetTrianglesAfter += result.trianglesAfter;
                }
                Need(report.targetTrianglesBefore == 1692 && report.targetTrianglesAfter == 1692, "Frozen four-instance geometry must remain 3*456+324 = 1692 triangles.");
                Need(report.allMeshFilterTrianglesBefore <= 600000, "Candidate already exceeds the 600k all-MeshFilter budget, including disabled/rendererless meshes and LODs.");
                report.generationPath = generationFolder + "/PierBench_" + DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff") + "_" + Guid.NewGuid().ToString("N").Substring(0,8);
                EnsureFolder(report.generationPath);
                Dictionary<string,Material> wood = MakeWoodMaterials(shader,texture,report);
                // Save independent mesh copies. Never mutate either the original mesh or the imported FBX mesh.
                for (int i = 0; i < targets.Length; i++)
                {
                    Target target = targets[i];
                    string path = report.generationPath + "/" + target.root.name + "_CoastalUV.asset";
                    Need(AssetDatabase.LoadMainAssetAtPath(path) == null, "Refusing to overwrite a generated mesh.");
                    AssetDatabase.CreateAsset(target.baked,path); AssetDatabase.SaveAssetIfDirty(target.baked);
                    target.result.generatedMeshAsset = path;
                }
                foreach (Target target in targets)
                {
                    string[] slots = target.type == "bench" ? BenchSlots : PierSlots;
                    Material[] mapped = slots.Select((name,index) => wood.TryGetValue(name,out Material material) ? material : target.originalMaterials[index]).ToArray();
                    target.filter.sharedMesh = target.baked; target.renderer.sharedMaterials = mapped;
                }
                protectedState.Verify(island);
                foreach (Target target in targets)
                {
                    Need(MeshContentHash(target.originalMesh) == target.originalContentHash, "An original mesh changed in memory.");
                    Need(ShaFile(target.result.originalMeshAsset) == target.result.originalMeshFileSha256, "An original model file changed.");
                    Need(target.filter.sharedMesh == target.baked, "Visual replacement did not retain its generated mesh.");
                    Need(MeshContentHash(target.baked) == target.result.generatedMeshContentSha256, "Generated visual mesh changed during commit.");
                    if (target.type == "bench") Need(target.filter.GetComponent<MeshCollider>().sharedMesh == target.originalMesh,
                        "Bench MeshCollider must continue referencing the frozen original mesh.");
                }
                report.collisionsAfter = Collisions(targets,island.transform); report.markersAfter = Markers(island.transform);
                Need(RecordsEqual(report.collisionsBefore,report.collisionsAfter) && RecordsEqual(report.markersBefore,report.markersAfter),
                    "Original collider/component identities or marker matrices changed.");
                report.meshFiltersAfter = island.GetComponentsInChildren<MeshFilter>(true).Length;
                report.allMeshFilterTrianglesAfter = TotalTriangles(island);
                Need(report.meshFiltersAfter == report.meshFiltersBefore && report.allMeshFilterTrianglesAfter == report.allMeshFilterTrianglesBefore,
                    "Zero-geometry surface replacement changed the all-MeshFilter count/budget.");
                report.additionalTriangles = report.targetTrianglesAfter - report.targetTrianglesBefore;
                report.checks.AddRange(new[] { "3 pier_module + 1 bench; pier_end absent", "All original transforms, component identities and non-material renderer properties preserved",
                    "Full marker matrices derive source-to-existing-Structure transforms; both pier end markers agree", "Per-slot triangle counts and oriented triangle multisets match; bidirectional world vertex comparison passes",
                    "Original 3 deck BoxColliders and bench MeshCollider/sharedMesh preserved", "4 shared coastal wood materials; old iron material unchanged; no importer/global rendering writes",
                    "All MeshFilter instances, including disabled and rendererless originals, have identical before/after triangle totals" });
                report.limitations.AddRange(new[] { "Runtime report proves only checks actually executed by this call, not visual superiority or playtest success.",
                    "Source geometry hashes are Blender manifest references; they are not claimed to be hashes of Unity's reordered vertex buffers.",
                    "Normals are transformed with inverse transpose and checked against matching original triangle corners; tangents are recalculated for new UV0.",
                    "No normal map or annual-ring texture; Blender and URP color-management/lighting equivalence is not claimed.",
                    "Three-module repetition, mip/filter behavior, deck walking and bench sitting need later Unity validation.",
                    "On any exception discard the disposable candidate. Generated diagnostic assets may remain; originals are never deleted." });
                report.status = "candidate-references-replaced-and-contracts-checked-awaiting-visual-playtest";
                report.reportAssetPath = report.generationPath + "/pier-bench-report.json";
                File.WriteAllText(ProjectFile(report.reportAssetPath),JsonUtility.ToJson(report,true));
                AssetDatabase.ImportAsset(report.reportAssetPath,ImportAssetOptions.ForceSynchronousImport);
                return report;
            }
            catch
            {
                // Restore references only; no object destruction, undo of someone else's scene, or shared-asset mutation.
                foreach (Target target in targets)
                {
                    if (target.filter) target.filter.sharedMesh = target.originalMesh;
                    if (target.renderer) target.renderer.sharedMaterials = target.originalMaterials;
                }
                throw;
            }
            finally
            {
                foreach (Target target in targets) if (target.baked != null && !EditorUtility.IsPersistent(target.baked)) Object.DestroyImmediate(target.baked);
            }
        }

        static Target LoadTarget(Transform root,bool bench,Vector3 position)
        {
            Need(Vector3.Distance(root.position,position) <= GeometryTolerance && MatrixError(Matrix4x4.TRS(root.position,Quaternion.identity,Vector3.one),root.localToWorldMatrix) <= GeometryTolerance,
                "Frozen prop root pose changed: " + root.name);
            Transform lod = Direct(root,"LOD0"), structure = Direct(lod,"Structure");
            var filter = structure.GetComponent<MeshFilter>(); var renderer = structure.GetComponent<MeshRenderer>();
            Need(filter && filter.sharedMesh && filter.sharedMesh.isReadable && renderer && renderer.enabled && structure.gameObject.activeInHierarchy,
                "Expected an active readable original Structure: " + root.name);
            Need(!renderer.HasPropertyBlock(), "Unexpected prop MaterialPropertyBlock; resolve its texture/tint overrides explicitly before integration.");
            Need(root.GetComponentsInChildren<MeshFilter>(true).Length == 1 && root.GetComponentsInChildren<Renderer>(true).Length == 1,
                "Unexpected prop rendering hierarchy: " + root.name);
            Need(MeshGuid(filter.sharedMesh) == (bench?BenchGuid:PierGuid) && Triangles(filter.sharedMesh) == (bench?324:456), "Frozen source GUID/face count differs.");
            ValidateSlots(filter.sharedMesh,renderer.sharedMaterials,bench?BenchSlots:PierSlots);
            Transform[] markers = (bench?new[]{"Marker_Seat"}:new[]{"Marker_Entry","Marker_Exit"}).Select(n=>Direct(lod,n)).ToArray();
            Need(lod.childCount == markers.Length+1 && root.childCount == (bench?1:2)
                && root.GetComponentsInChildren<Transform>(true).Count(t=>t.name.StartsWith("Marker_",StringComparison.Ordinal)) == markers.Length,
                "Unexpected prop marker hierarchy.");
            Collider[] colliders = root.GetComponentsInChildren<Collider>(true);
            Need(colliders.Length == 1 && colliders[0].enabled && !colliders[0].isTrigger, "Prop must retain exactly one enabled solid collider.");
            if (bench)
            {
                var mc = structure.GetComponent<MeshCollider>();
                Need(mc != null && colliders[0] == mc && mc.sharedMesh == filter.sharedMesh && !mc.convex && (int)mc.cookingOptions == 30
                    && mc.sharedMaterial == null && structure.gameObject.layer == 9, "Frozen bench MeshCollider contract differs.");
            }
            else
            {
                Transform deck = Direct(root,"WalkableDeck"); var box = deck.GetComponent<BoxCollider>();
                Need(box != null && colliders[0] == box && deck.gameObject.layer == 8 && structure.gameObject.layer == 8
                    && box.center == new Vector3(0,-.1f,0) && box.size == new Vector3(2.4f,.2f,3)
                    && deck.localPosition == Vector3.zero && deck.localRotation == Quaternion.identity && deck.localScale == Vector3.one,
                    "Frozen bridge BoxCollider/pose differs.");
            }
            return new Target { type=bench?"bench":"pier_module",root=root,lod=lod,filter=filter,renderer=renderer,markers=markers,
                originalMesh=filter.sharedMesh,originalMaterials=renderer.sharedMaterials,originalContentHash=MeshContentHash(filter.sharedMesh) };
        }
        static Source LoadSource(bool bench)
        {
            string type=bench?"bench":"pier_module", path=Root+"ModelsV2/"+type+"/"+type+"_v2_candidate.fbx";
            string sha=ShaFile(path), expected=bench?"c5bb3190f178f1b217cdcbc888b329bf8654c78330b7a564cab6f585251f194e":"1155f4cfa54dea293089377ba08df626596a1aec26a35712c176d279cbd6465f";
            Need(sha == expected,"Candidate FBX differs from the reviewed offline surface candidate: "+path);
            GameObject source=AssetDatabase.LoadAssetAtPath<GameObject>(path); Need(source != null,"Import candidate FBX first: "+path);
            var importer=AssetImporter.GetAtPath(path) as ModelImporter;
            Need(importer != null && importer.isReadable && !importer.addCollider && !importer.importAnimation,"Prepare readable candidate models without generated colliders/animation first.");
            MeshFilter[] filters=source.GetComponentsInChildren<MeshFilter>(true);
            Need(filters.Length==1 && filters[0].name=="Structure" && filters[0].sharedMesh && filters[0].sharedMesh.isReadable
                && source.GetComponentsInChildren<Collider>(true).Length==0 && source.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length==0,
                "Candidate must have one static Structure and no collision/character geometry.");
            MeshRenderer renderer=filters[0].GetComponent<MeshRenderer>(); Need(renderer != null,"Missing source renderer.");
            ValidateSlots(filters[0].sharedMesh,renderer.sharedMaterials,bench?BenchSlots:PierSlots);
            Transform[] markers=(bench?new[]{"Marker_Seat"}:new[]{"Marker_Entry","Marker_Exit"}).Select(n=>Unique(source.transform,n)).ToArray();
            Need(source.GetComponentsInChildren<Transform>(true).Count(t=>t.name.StartsWith("Marker_",StringComparison.Ordinal))==markers.Length,"Unexpected source markers.");
            return new Source {path=path,sha=sha,root=source,filter=filters[0],markers=markers,
                geometryReference=bench?"5c8e7f0018f9d3e9ef04b73046c815eda838d9d0e54b1870a2cd175d0664cf0e":"2fd4c411007ae5d2a26c89b7f8291b210f4539f03c2581a0d9b6323ed833c20b"};
        }
        static Mesh Bake(Mesh source,Matrix4x4 matrix,string name)
        {
            Need(source.blendShapeCount==0 && source.uv.Length==source.vertexCount && source.normals.Length==source.vertexCount,"Readable mesh normals and UV0 are required.");
            Vector3[] vertices=source.vertices, normals=source.normals; Matrix4x4 normalMatrix=matrix.inverse.transpose;
            for(int i=0;i<vertices.Length;i++)
            {
                vertices[i]=matrix.MultiplyPoint3x4(vertices[i]); normals[i]=normalMatrix.MultiplyVector(normals[i]).normalized;
                Need(Finite(vertices[i]) && Finite(normals[i]) && normals[i].sqrMagnitude>.99f,"Invalid transformed source vertex/normal.");
            }
            Need(source.uv.All(uv=>Finite(uv.x)&&Finite(uv.y)),"Invalid UV0 values.");
            Mesh result=Object.Instantiate(source);
            try
            {
                result.name=name; result.vertices=vertices; result.normals=normals;
                if(matrix.determinant<0) for(int s=0;s<result.subMeshCount;s++)
                {
                    int[] indices=result.GetIndices(s); for(int i=0;i<indices.Length;i+=3){int t=indices[i+1];indices[i+1]=indices[i+2];indices[i+2]=t;}
                    result.SetIndices(indices,MeshTopology.Triangles,s,false);
                }
                result.RecalculateBounds(); result.RecalculateTangents(); return result;
            }
            catch { Object.DestroyImmediate(result); throw; }
        }
        static void CompareGeometry(Mesh original,Mesh candidate,Matrix4x4 world,Replacement result)
        {
            Need(original.subMeshCount==candidate.subMeshCount && Triangles(original)==Triangles(candidate),"Source topology/triangle count changed.");
            Vector3[] a=original.vertices.Select(world.MultiplyPoint3x4).ToArray(), b=candidate.vertices.Select(world.MultiplyPoint3x4).ToArray();
            Need(a.Length>0&&b.Length>0,"Empty mesh.");
            float maximum=0;
            foreach(Vector3 p in a) maximum=Mathf.Max(maximum,b.Min(q=>Vector3.Distance(p,q)));
            foreach(Vector3 p in b) maximum=Mathf.Max(maximum,a.Min(q=>Vector3.Distance(p,q)));
            Need(maximum<=GeometryTolerance,"Bidirectional world vertex mismatch: "+result.path); result.bidirectionalVertexErrorWorld=maximum;
            Vector3[] an=original.normals,bn=candidate.normals; Need(an.Length==a.Length&&bn.Length==b.Length,"Missing normals.");
            // Matching is per material slot, one-to-one and oriented (cyclic rotations only), preserving duplicate face multiplicity.
            // Raw vertex IDs may differ because FBX import splits UV seams/reorders vertices; this does not authorize topology changes.
            for(int s=0;s<original.subMeshCount;s++)
            {
                int[] ai=original.GetIndices(s),bi=candidate.GetIndices(s); Need(ai.Length==bi.Length,"Submesh index count differs at slot "+s);
                Need(ai.All(i=>i>=0&&i<a.Length)&&bi.All(i=>i>=0&&i<b.Length),"Out-of-range triangle index.");
                bool[] used=new bool[bi.Length/3];
                for(int i=0;i<ai.Length;i+=3)
                {
                    int match=-1,rotation=-1; float best=float.PositiveInfinity,angle=0;
                    for(int j=0;j<bi.Length;j+=3) if(!used[j/3]) for(int r=0;r<3;r++)
                    {
                        float error=0,normalAngle=0;
                        for(int c=0;c<3;c++)
                        {
                            int ia=ai[i+c],ib=bi[j+(c+r)%3];
                            error=Mathf.Max(error,Vector3.Distance(a[ia],b[ib])); normalAngle=Mathf.Max(normalAngle,Vector3.Angle(an[ia],bn[ib]));
                        }
                        if(error<=GeometryTolerance && normalAngle<=.25f && error<best){best=error;match=j/3;rotation=r;angle=normalAngle;}
                    }
                    Need(match>=0&&rotation>=0,"Oriented face, material slot or corner normal changed at slot "+s+", triangle "+i/3+": "+result.path);
                    used[match]=true; result.matchedOrientedTriangles++; result.triangleCornerErrorWorld=Mathf.Max(result.triangleCornerErrorWorld,best);
                    result.largestNormalAngleDegrees=Mathf.Max(result.largestNormalAngleDegrees,angle);
                }
                Need(used.All(x=>x),"Unmatched candidate triangles.");
            }
            result.trianglesAfter=Triangles(candidate); result.submeshes=candidate.subMeshCount; result.newVertices=candidate.vertexCount;
            result.uvVertices=candidate.uv.Length; result.uv0Present=result.uvVertices==candidate.vertexCount;
            Need(result.uv0Present && candidate.uv.Distinct().Count()>2,"Candidate UV0 is missing or collapsed.");
        }
        static Dictionary<string,Material> MakeWoodMaterials(Shader shader,Texture2D texture,Report report)
        {
            var result=new Dictionary<string,Material>(StringComparer.Ordinal);
            for(int i=0;i<WoodNames.Length;i++)
            {
                var material=new Material(shader){name=CoastalNames[i],enableInstancing=true};
                material.SetTexture("_BaseMap",texture); material.SetTextureScale("_BaseMap",Vector2.one); material.SetTextureOffset("_BaseMap",Vector2.zero);
                material.SetColor("_BaseColor",Tints[i]); material.SetFloat("_Metallic",0); material.SetFloat("_Smoothness",1-Roughness[i]);
                material.SetFloat("_Surface",0); material.SetFloat("_AlphaClip",0); material.SetFloat("_Cull",2);
                material.SetColor("_EmissionColor",Color.black); material.DisableKeyword("_EMISSION"); material.DisableKeyword("_NORMALMAP");
                material.DisableKeyword("_ALPHATEST_ON"); material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT"); material.renderQueue=-1;
                string path=report.generationPath+"/"+CoastalNames[i]+".mat";
                Need(AssetDatabase.LoadMainAssetAtPath(path)==null,"Refusing to overwrite a shared material.");
                AssetDatabase.CreateAsset(material,path); AssetDatabase.SaveAssetIfDirty(material); result.Add(WoodNames[i],material);
                report.materialMapping.Add(new MaterialRecord{source=WoodNames[i],destination=CoastalNames[i],assetPath=path,tint=Tints[i],roughness=Roughness[i]});
            }
            report.sharedWoodMaterials=result.Count; return result;
        }

        sealed class ProtectedState
        {
            sealed class Pose { public Transform t,parent; public string name; public int sibling,layer; public bool active; public Vector3 p,s; public Quaternion q; public Matrix4x4 world; }
            sealed class State { public Component component; public string json; public bool allowMaterials,allowMesh; }
            readonly Pose[] poses; readonly State[] states; readonly int[] componentIds;
            public int TransformCount=>poses.Length;
            public ProtectedState(GameObject island,Target[] targets)
            {
                poses=island.GetComponentsInChildren<Transform>(true).Select(t=>new Pose{t=t,parent=t.parent,name=t.name,sibling=t.GetSiblingIndex(),layer=t.gameObject.layer,
                    active=t.gameObject.activeSelf,p=t.localPosition,q=t.localRotation,s=t.localScale,world=t.localToWorldMatrix}).ToArray();
                Component[] components=island.GetComponentsInChildren<Component>(true); Need(components.All(c=>c!=null),"Candidate contains a missing script/component.");
                componentIds=components.Select(c=>c.GetInstanceID()).OrderBy(x=>x).ToArray();
                states=components.Where(c=>c is Collider||c is Renderer||c is MeshFilter).Select(c=>new State{component=c,
                    allowMaterials=targets.Any(t=>t.renderer==c),allowMesh=targets.Any(t=>t.filter==c)}).ToArray();
                foreach(State state in states) state.json=StateJson(state);
            }
            public void Verify(GameObject island)
            {
                Need(componentIds.SequenceEqual(island.GetComponentsInChildren<Component>(true).Select(c=>c.GetInstanceID()).OrderBy(x=>x)),"Original components were added/removed.");
                foreach(Pose p in poses) Need(p.t&&p.t.parent==p.parent&&p.t.name==p.name&&p.t.GetSiblingIndex()==p.sibling&&p.t.gameObject.layer==p.layer
                    &&p.t.gameObject.activeSelf==p.active&&p.t.localPosition.Equals(p.p)&&p.t.localRotation.Equals(p.q)&&p.t.localScale.Equals(p.s)
                    &&p.t.localToWorldMatrix.Equals(p.world),"Original transform/anchor/layer/active state changed: "+p.name);
                foreach(State state in states) Need(state.component&&StateJson(state)==state.json,"Protected collider/renderer/filter property changed.");
            }
            static string StateJson(State state)
            {
                string json=EditorJsonUtility.ToJson(state.component);
                if(state.allowMaterials) json=Regex.Replace(json,"\"m_Materials\"\\s*:\\s*\\[[^\\]]*\\]","\"m_Materials\":[]");
                if(state.allowMesh) json=Regex.Replace(json,"\"m_Mesh\"\\s*:\\s*\\{[^}]*\\}","\"m_Mesh\":{}");
                return json;
            }
        }
        static List<MarkerRecord> Markers(Transform island)=>island.GetComponentsInChildren<Transform>(true)
            .Where(t=>t.name.StartsWith("Marker_",StringComparison.Ordinal)||t.name.StartsWith("Anchor_",StringComparison.Ordinal)||t.name.StartsWith("NPC_",StringComparison.Ordinal)||t.name.StartsWith("Target_",StringComparison.Ordinal)||t.name.StartsWith("Cam_",StringComparison.Ordinal))
            .Select(t=>new MarkerRecord{path=HierarchyPath(t,island),instanceId=t.GetInstanceID(),worldMatrix=MatrixValues(t.localToWorldMatrix)}).OrderBy(x=>x.path,StringComparer.Ordinal).ToList();
        static List<CollisionRecord> Collisions(Target[] targets,Transform island)=>targets.SelectMany(t=>t.root.GetComponentsInChildren<Collider>(true))
            .Select(c=>new CollisionRecord{path=HierarchyPath(c.transform,island),type=c.GetType().Name,instanceId=c.GetInstanceID(),serializedState=EditorJsonUtility.ToJson(c),
                worldMatrix=MatrixValues(c.transform.localToWorldMatrix),meshAsset=c is MeshCollider mc?AssetDatabase.GetAssetPath(mc.sharedMesh):"",
                meshGuid=c is MeshCollider m?MeshGuid(m.sharedMesh):"",meshInstanceId=c is MeshCollider mm&&mm.sharedMesh?mm.sharedMesh.GetInstanceID():0})
            .OrderBy(x=>x.path,StringComparer.Ordinal).ToList();
        static bool RecordsEqual<T>(List<T>a,List<T>b)=>a.Count==b.Count&&a.Select(x=>JsonUtility.ToJson(x)).SequenceEqual(b.Select(x=>JsonUtility.ToJson(x)));
        static void ValidateCandidate(GameObject island)
        {
            Need(!EditorApplication.isPlayingOrWillChangePlaymode&&!EditorApplication.isCompiling&&!EditorApplication.isUpdating,"Editor must be idle and caller must own Unity operation.");
            Need(island&&!EditorUtility.IsPersistent(island)&&island.scene.IsValid()&&island.scene.isLoaded&&string.IsNullOrEmpty(island.scene.path)
                &&island.name=="Island"&&island.transform.parent==null,"Use caller's detached Island root in a disposable unsaved scene.");
            Need(PrefabStageUtility.GetCurrentPrefabStage()==null&&!island.GetComponentsInChildren<Transform>(true).Any(t=>PrefabUtility.IsPartOfPrefabInstance(t.gameObject)),"Fully unpack candidate; never edit a prefab instance/asset/Prefab Mode.");
            Need(island.transform.localPosition==Vector3.zero&&island.transform.localRotation==Quaternion.identity&&island.transform.localScale==Vector3.one,"Island root must be identity.");
        }
        static void ValidateSlots(Mesh mesh,Material[] materials,string[] slots)
        {
            Need(mesh.subMeshCount==slots.Length&&materials.Length==slots.Length,"Original material/submesh slots changed.");
            for(int i=0;i<slots.Length;i++) Need(materials[i]&&Clean(materials[i].name)==slots[i]&&mesh.GetTopology(i)==MeshTopology.Triangles
                &&mesh.GetIndexCount(i)%3==0,"Unexpected slot name/topology: "+slots[i]);
        }
        static string MeshContentHash(Mesh mesh)
        {
            using(var memory=new MemoryStream())
            {
                using(var writer=new BinaryWriter(memory,System.Text.Encoding.UTF8,true))
                {
                    writer.Write(mesh.vertexCount); foreach(Vector3 v in mesh.vertices){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);}
                    foreach(Vector3 v in mesh.normals){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);}
                    foreach(Vector4 v in mesh.tangents){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);writer.Write(v.w);}
                    for(int channel=0;channel<8;channel++){var uv=new List<Vector4>();mesh.GetUVs(channel,uv);writer.Write(uv.Count);foreach(Vector4 v in uv){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);writer.Write(v.w);}}
                    foreach(Color v in mesh.colors){writer.Write(v.r);writer.Write(v.g);writer.Write(v.b);writer.Write(v.a);}
                    writer.Write(mesh.subMeshCount); for(int s=0;s<mesh.subMeshCount;s++){writer.Write((int)mesh.GetTopology(s));int[] ii=mesh.GetIndices(s);writer.Write(ii.Length);foreach(int i in ii)writer.Write(i);}
                }
                using(var sha=SHA256.Create())return Hex(sha.ComputeHash(memory.ToArray()));
            }
        }
        static string ShaFile(string path){using(var sha=SHA256.Create())using(var stream=File.OpenRead(ProjectFile(OwnedPath(path,Root))))return Hex(sha.ComputeHash(stream));}
        static string Hex(byte[] bytes)=>BitConverter.ToString(bytes).Replace("-","").ToLowerInvariant();
        static string MeshGuid(Mesh mesh)=>mesh?AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(mesh)):"";
        static long TotalTriangles(GameObject root)=>root.GetComponentsInChildren<MeshFilter>(true).Where(f=>f.sharedMesh).Sum(f=>(long)Triangles(f.sharedMesh));
        static int Triangles(Mesh mesh){long sum=0;for(int s=0;s<mesh.subMeshCount;s++){Need(mesh.GetTopology(s)==MeshTopology.Triangles&&mesh.GetIndexCount(s)%3==0,"Only triangle submeshes supported.");sum+=mesh.GetIndexCount(s)/3;}Need(sum<=int.MaxValue,"Triangle overflow.");return(int)sum;}
        static void ValidateMatrix(Matrix4x4 matrix){Need(Enumerable.Range(0,16).All(i=>Finite(matrix[i]))&&Mathf.Abs(matrix.determinant)>1e-7f,"Non-finite/degenerate marker-derived transform.");}
        static float MatrixError(Matrix4x4 a,Matrix4x4 b)=>new[]{Vector3.zero,Vector3.right,Vector3.up,Vector3.forward}.Max(p=>Vector3.Distance(a.MultiplyPoint3x4(p),b.MultiplyPoint3x4(p)));
        static float[] MatrixValues(Matrix4x4 m)=>Enumerable.Range(0,16).Select(i=>m[i]).ToArray();
        static bool Finite(float f)=>!float.IsNaN(f)&&!float.IsInfinity(f); static bool Finite(Vector3 v)=>Finite(v.x)&&Finite(v.y)&&Finite(v.z);
        static string Clean(string name)=>Regex.Replace(name.Replace(" (Instance)",""),@"\.\d{3}$","");
        static Transform Direct(Transform parent,string name){Transform[] found=parent.Cast<Transform>().Where(t=>t.name==name).ToArray();Need(found.Length==1,"Expected one direct child "+name+" under "+parent.name);return found[0];}
        static Transform Unique(Transform parent,string name){Transform[] found=parent.GetComponentsInChildren<Transform>(true).Where(t=>t.name==name).ToArray();Need(found.Length==1,"Expected one "+name);return found[0];}
        static string HierarchyPath(Transform t,Transform root){var parts=new List<string>();for(;t&&t!=root;t=t.parent)parts.Add(t.name);parts.Reverse();return string.Join("/",parts);}
        static string OwnedPath(string path,string prefix)
        {
            Need(!string.IsNullOrWhiteSpace(path),"Owned asset path required.");path=path.Replace('\\','/');
            Need(path.StartsWith(prefix,StringComparison.Ordinal)&&!path.Contains("..")&&!path.Contains(":")&&!path.Contains("//")
                &&!path.Any(c=>char.IsControl(c))&&!path.Split('/').Any(p=>p.EndsWith(" ",StringComparison.Ordinal)||p.EndsWith(".",StringComparison.Ordinal)),"Path must remain inside "+prefix);
            string absolute=ProjectFile(path),owned=ProjectFile(Root);
            Need(absolute.StartsWith(owned,StringComparison.OrdinalIgnoreCase),"Resolved path escaped Environment.");
            string project=Directory.GetParent(Application.dataPath).FullName;
            for(string current=absolute;current!=null&&current.StartsWith(project,StringComparison.OrdinalIgnoreCase);current=Path.GetDirectoryName(current))
                if(File.Exists(current)||Directory.Exists(current))Need((File.GetAttributes(current)&FileAttributes.ReparsePoint)==0,"No symlink/junction destinations.");
            return path;
        }
        static string ProjectFile(string path)=>Path.GetFullPath(Path.Combine(Directory.GetParent(Application.dataPath).FullName,path));
        static void EnsureFolder(string folder)
        {
            OwnedPath(folder,Root+"Generated/");if(AssetDatabase.IsValidFolder(folder))return;
            string parent=folder.Substring(0,folder.LastIndexOf('/'));
            Need(AssetDatabase.IsValidFolder(parent)||parent.StartsWith(Root+"Generated/",StringComparison.Ordinal),"Create owned Generated root first.");
            if(!AssetDatabase.IsValidFolder(parent))EnsureFolder(parent);
            Need(!string.IsNullOrEmpty(AssetDatabase.CreateFolder(parent,folder.Substring(folder.LastIndexOf('/')+1))),"Could not create unique generation folder.");
        }
        static void Need(bool condition,string message){if(!condition)throw new InvalidOperationException(message);}
    }
}
#endif
