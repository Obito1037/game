#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    /// <summary>
    /// Explicit material-only patch on the supplied Island instance. No scene searches,
    /// import-setting changes, scene/prefab saves, mesh/collider changes or auto execution.
    /// </summary>
    public static class EnvV2SurfaceBuilder
    {
        public const string ShaderName = "JieGuang/Environment/TerrainSurface";
        public const string OutputRoot = "Assets/JieGuang/Environment/Generated/V2Surface";
        const string EnvironmentRoot = "Assets/JieGuang/Environment/";
        const string MaterialPrefix = "EnvV2Surf_";
        static readonly string[] RendererNames = { "IslandGround", "StonePaths", "CoastalCliff" };

        [Serializable] public sealed class Settings
        {
            public float textureMeters = 2f;
            public float textureLuminancePivot = .18f;
            public float textureContrast = .32f;
            public float textureChroma = .08f;
            public float macroMeters = 5.5f;
            public float stoneMeters = .85f;
            public float cliffMeters = 2.7f;
            public float layerMeters = 1.3f;
            public float groundReliefMeters = .004f;
            public float stoneReliefMeters = .007f;
            public float cliffReliefMeters = .024f;
        }
        [Serializable] public sealed class Check { public string name; public bool passed; public string detail; }
        [Serializable] public sealed class SlotChange
        {
            public string rendererPath;
            public int materialSlot;
            public string sourceKey;
            public string originalMaterialPath, originalMaterialGuid;
            public string replacementMaterialPath, replacementMaterialGuid;
            public int surfaceMode;
        }
        [Serializable] public sealed class Report
        {
            public string status, generatedUtc, unityVersion, generationPath, texturePath;
            public Settings settings;
            public int rendererCount, changedSlots;
            public string normalModel = "No imported normal map. Small world-height derivative bump, also evaluated in DepthNormals. No vertex displacement.";
            public List<SlotChange> bindings = new List<SlotChange>();
            public List<Check> checks = new List<Check>();
            public List<string> warnings = new List<string>();
        }
        sealed class Palette
        {
            public int mode;
            public Color primary, secondary, soil;
            public float roughness, soilAmount, detail;
        }
        sealed class PlannedSlot
        {
            public Renderer renderer;
            public Material oldMaterial, newMaterial;
            public SlotChange binding;
            public Palette palette;
        }
        sealed class Snapshot
        {
            public Transform[] transforms;
            public Matrix4x4[] matrices;
            public MeshFilter[] filters;
            public Mesh[] meshes;
            public Collider[] colliders;
            public string[] colliderStates;
            public Renderer[] renderers;
            public Material[][] materials;
            public Dictionary<Material,string> sourceMaterialStates;
        }

        /// <summary>
        /// Explicit entry: Build(islandInstance, importedMeadowAlbedoPath).
        /// Texture must already be imported under the owned Environment subtree.
        /// Only exact slots on IslandGround / StonePaths / CoastalCliff below direct Terrain change.
        /// Output always stays below Generated/V2Surface, preserving every original material asset.
        /// </summary>
        public static Report Build(GameObject islandRoot, string meadowAlbedoAssetPath, Settings settings = null)
        {
            if (islandRoot==null) throw new ArgumentNullException(nameof(islandRoot));
            if(EditorUtility.IsPersistent(islandRoot)||!islandRoot.scene.IsValid())throw new ArgumentException("Pass a live instance or loaded prefab contents; persistent prefab assets are read-only here.");
            Settings config=settings??new Settings();ValidateSettings(config);
            Shader shader=Shader.Find(ShaderName);
            if(shader==null||!shader.isSupported)throw new InvalidOperationException("Import/compile the owned TerrainSurface shader first; no material slots have changed.");
            string texturePath=(meadowAlbedoAssetPath??"").Replace('\\','/');
            if(!texturePath.StartsWith(EnvironmentRoot,StringComparison.Ordinal)||texturePath.Contains(".."))throw new ArgumentException("The albedo must already be imported under "+EnvironmentRoot);
            Texture2D texture=AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
            if(texture==null)throw new FileNotFoundException("No imported meadow Texture2D at "+texturePath);
            var report=new Report {status="planning",generatedUtc=DateTime.UtcNow.ToString("O"),unityVersion=Application.unityVersion,settings=config,texturePath=texturePath};
            CheckTexture(texturePath,texture,report);
            List<PlannedSlot> slots=PlanSlots(islandRoot.transform);
            Snapshot before=Capture(islandRoot);
            string generation=OutputRoot+"/SurfaceGeneration_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff");
            EnsureFolder(generation);
            report.generationPath=generation;
            var replacements=new Dictionary<string,Material>(StringComparer.Ordinal);
            foreach(PlannedSlot slot in slots)
            {
                string key=slot.binding.sourceKey;
                if(!replacements.TryGetValue(key,out Material material))
                {
                    material=MakeMaterial(shader,texture,key,slot.palette,config);
                    string path=generation+"/"+material.name+".mat";
                    if(AssetDatabase.LoadMainAssetAtPath(path)!=null||File.Exists(ProjectFile(path)))throw new InvalidOperationException("Refusing to overwrite an existing material: "+path);
                    AssetDatabase.CreateAsset(material,path);AssetDatabase.SaveAssetIfDirty(material);
                    replacements.Add(key,material);
                }
                slot.newMaterial=material;
                slot.binding.replacementMaterialPath=AssetDatabase.GetAssetPath(material);
                slot.binding.replacementMaterialGuid=AssetDatabase.AssetPathToGUID(slot.binding.replacementMaterialPath);
                report.bindings.Add(slot.binding);
            }
            try
            {
                foreach(var group in slots.GroupBy(s=>s.renderer))
                {
                    Material[] materials=group.Key.sharedMaterials;
                    foreach(PlannedSlot slot in group)
                    {
                        if(materials[slot.binding.materialSlot]!=slot.oldMaterial)throw new InvalidOperationException("A source slot changed while preparing the candidate; abort instead of overwriting another edit.");
                        materials[slot.binding.materialSlot]=slot.newMaterial;
                    }
                    group.Key.sharedMaterials=materials;
                }
                report.rendererCount=slots.Select(s=>s.renderer).Distinct().Count();report.changedSlots=slots.Count;
                AddChecks(before,slots,report);
                if(report.checks.Any(c=>!c.passed))throw new InvalidOperationException("Surface scope verification failed: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name)));
                report.status="applied-to-passed-instance-awaiting-visual-and-runtime-verification";
                report.warnings.Add("Original material assets remain unchanged. Caller must explicitly save its own Environment prefab/scene.");
                report.warnings.Add("No Unity shader compile, gameplay light-cone, image quality or FPS claim is made by the offline candidate. These require actual Editor verification after import.");
                string json=generation+"/surface-report.json";
                File.WriteAllText(ProjectFile(json),JsonUtility.ToJson(report,true),new System.Text.UTF8Encoding(false));
                AssetDatabase.ImportAsset(json,ImportAssetOptions.ForceSynchronousImport);
                return report;
            }
            catch
            {
                // Restore only slots still containing this generation's replacement. A concurrent
                // external change is never overwritten by rollback, and no original asset is mutated.
                foreach(var group in slots.GroupBy(s=>s.renderer))
                {
                    if(group.Key==null)continue;
                    Material[] materials=group.Key.sharedMaterials;bool changed=false;
                    foreach(PlannedSlot slot in group)
                        if(slot.binding.materialSlot<materials.Length&&materials[slot.binding.materialSlot]==slot.newMaterial){materials[slot.binding.materialSlot]=slot.oldMaterial;changed=true;}
                    if(changed)group.Key.sharedMaterials=materials;
                }
                throw;
            }
        }

        /// <summary>Read-only binding plan; does not require the candidate shader or a texture import.</summary>
        public static Report Plan(GameObject islandRoot)
        {
            if(islandRoot==null)throw new ArgumentNullException(nameof(islandRoot));
            List<PlannedSlot> slots=PlanSlots(islandRoot.transform);
            return new Report {status="read-only-binding-plan",generatedUtc=DateTime.UtcNow.ToString("O"),unityVersion=Application.unityVersion,rendererCount=slots.Select(s=>s.renderer).Distinct().Count(),changedSlots=slots.Count,bindings=slots.Select(s=>s.binding).ToList()};
        }

        /// <summary>Explicit revert of one report. All current slots must still equal that report's outputs.</summary>
        public static void Revert(GameObject islandRoot,string surfaceReportAssetPath)
        {
            if(islandRoot==null||EditorUtility.IsPersistent(islandRoot)||!islandRoot.scene.IsValid())throw new ArgumentException("Pass a live own Island instance.");
            string path=(surfaceReportAssetPath??"").Replace('\\','/');
            if(!path.StartsWith(OutputRoot+"/SurfaceGeneration_",StringComparison.Ordinal)||!path.EndsWith("/surface-report.json",StringComparison.Ordinal)||path.Contains(".."))throw new ArgumentException("Revert only accepts an owned generation report.");
            Report report=JsonUtility.FromJson<Report>(File.ReadAllText(ProjectFile(path)));
            if(report==null||report.bindings==null||report.bindings.Count==0)throw new InvalidDataException("Report has no material bindings.");
            Transform terrain=DirectTerrain(islandRoot.transform);
            var changes=new List<PlannedSlot>();
            foreach(SlotChange binding in report.bindings)
            {
                Transform target=islandRoot.transform.Find(binding.rendererPath);
                if(target==null||!target.IsChildOf(terrain)||!RendererNames.Contains(target.name))throw new InvalidDataException("Report target no longer matches the owned Terrain contract.");
                Renderer renderer=target.GetComponent<Renderer>();
                Material original=AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(binding.originalMaterialGuid));
                Material replacement=AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(binding.replacementMaterialGuid));
                if(renderer==null||original==null||replacement==null||binding.materialSlot<0||binding.materialSlot>=renderer.sharedMaterials.Length||renderer.sharedMaterials[binding.materialSlot]!=replacement)
                    throw new InvalidOperationException("A source or replacement slot has changed since the report; refusing to overwrite a later edit.");
                changes.Add(new PlannedSlot {renderer=renderer,oldMaterial=original,newMaterial=replacement,binding=binding});
            }
            foreach(var group in changes.GroupBy(s=>s.renderer))
            {
                Material[] mats=group.Key.sharedMaterials;foreach(PlannedSlot slot in group)mats[slot.binding.materialSlot]=slot.oldMaterial;group.Key.sharedMaterials=mats;
            }
        }

        static List<PlannedSlot> PlanSlots(Transform root)
        {
            Transform terrain=DirectTerrain(root);
            var result=new List<PlannedSlot>();
            foreach(string name in RendererNames)
            {
                Renderer[] found=terrain.GetComponentsInChildren<Renderer>(true).Where(r=>r.name==name).ToArray();
                if(found.Length!=1)throw new InvalidOperationException("Expected exactly one Terrain renderer named "+name+", found "+found.Length+". No fuzzy matching fallback.");
                Renderer renderer=found[0];Material[] materials=renderer.sharedMaterials;int count=0;
                for(int slot=0;slot<materials.Length;slot++)
                {
                    Material source=materials[slot];if(source==null)throw new InvalidOperationException("Missing material in "+name+" slot "+slot);
                    string key=source.name;
                    if(source.shader!=null&&source.shader.name==ShaderName&&key.StartsWith(MaterialPrefix,StringComparison.Ordinal))key=key.Substring(MaterialPrefix.Length);
                    if(!TryPalette(name,key,out Palette palette))continue;
                    string sourcePath=AssetDatabase.GetAssetPath(source);
                    if(string.IsNullOrEmpty(sourcePath))throw new InvalidOperationException("A target material is transient. Save the intended material in Environment before a reversible replacement.");
                    result.Add(new PlannedSlot {
                        renderer=renderer,oldMaterial=source,palette=palette,
                        binding=new SlotChange {rendererPath=PathFromRoot(root,renderer.transform),materialSlot=slot,sourceKey=key,originalMaterialPath=sourcePath,originalMaterialGuid=AssetDatabase.AssetPathToGUID(sourcePath),surfaceMode=palette.mode}
                    });count++;
                }
                if(count==0)throw new InvalidOperationException("No approved material slots found on "+name+". Unknown slots are preserved, never guessed.");
            }
            return result;
        }
        static bool TryPalette(string renderer,string key,out Palette p)
        {
            p=null;
            if(renderer=="IslandGround")
            {
                if(key=="Ground_Moss")p=Colour(0,new Color(.235f,.315f,.270f),new Color(.155f,.225f,.190f),.90f,.10f,.10f);
                else if(key=="Ground_Sage")p=Colour(0,new Color(.265f,.330f,.285f),new Color(.185f,.250f,.210f),.89f,.12f,.10f);
                else if(key=="Ground_Earth")p=Colour(0,new Color(.185f,.215f,.195f),new Color(.140f,.175f,.157f),.94f,.65f,.08f);
            }
            else if(renderer=="StonePaths")
            {
                if(key=="Path_WeatheredStone")p=Colour(1,new Color(.40f,.44f,.425f),new Color(.29f,.34f,.33f),.86f,0,.10f);
                else if(key=="Path_WarmStone")p=Colour(1,new Color(.44f,.445f,.405f),new Color(.32f,.34f,.305f),.87f,0,.09f);
            }
            else if(renderer=="CoastalCliff")
            {
                if(key=="Cliff_BlueSlate")p=Colour(2,new Color(.225f,.270f,.285f),new Color(.145f,.190f,.205f),.92f,0,.12f);
                else if(key=="Cliff_SoftSlate")p=Colour(2,new Color(.285f,.310f,.305f),new Color(.195f,.225f,.220f),.91f,0,.10f);
                else if(key=="Shore_Sand")p=Colour(1,new Color(.33f,.35f,.32f),new Color(.245f,.275f,.255f),.96f,0,.07f);
            }
            return p!=null;
        }
        static Palette Colour(int mode,Color primary,Color secondary,float rough,float soil,float detail)=>new Palette{mode=mode,primary=primary,secondary=secondary,soil=new Color(.135f,.155f,.145f),roughness=rough,soilAmount=soil,detail=detail};
        static Material MakeMaterial(Shader shader,Texture2D texture,string key,Palette p,Settings s)
        {
            var m=new Material(shader){name=MaterialPrefix+key,enableInstancing=true};
            m.SetFloat("_SurfaceMode",p.mode);m.SetTexture("_BaseMap",texture);
            m.SetColor("_BaseColor",p.primary);m.SetColor("_SecondaryColor",p.secondary);m.SetColor("_SoilColor",p.soil);
            m.SetFloat("_TextureMeters",s.textureMeters);m.SetFloat("_TexturePivot",s.textureLuminancePivot);
            m.SetFloat("_TextureContrast",s.textureContrast);m.SetFloat("_TextureChroma",s.textureChroma);
            m.SetFloat("_MacroMeters",s.macroMeters);m.SetFloat("_SoilAmount",p.soilAmount);
            m.SetFloat("_StoneMeters",s.stoneMeters);m.SetFloat("_CliffMeters",s.cliffMeters);m.SetFloat("_LayerMeters",s.layerMeters);
            m.SetFloat("_DetailStrength",p.detail);m.SetFloat("_Roughness",p.roughness);m.SetFloat("_RoughnessVariation",.045f);
            m.SetFloat("_ReliefMeters",p.mode==0?s.groundReliefMeters:p.mode==1?s.stoneReliefMeters:s.cliffReliefMeters);
            m.globalIlluminationFlags=MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            return m;
        }

        static Snapshot Capture(GameObject root)
        {
            Transform[] ts=root.GetComponentsInChildren<Transform>(true);MeshFilter[] fs=root.GetComponentsInChildren<MeshFilter>(true);
            Collider[] cs=root.GetComponentsInChildren<Collider>(true);Renderer[] rs=root.GetComponentsInChildren<Renderer>(true);
            return new Snapshot {transforms=ts,matrices=ts.Select(t=>t.localToWorldMatrix).ToArray(),filters=fs,meshes=fs.Select(f=>f.sharedMesh).ToArray(),colliders=cs,colliderStates=cs.Select(c=>EditorJsonUtility.ToJson(c)).ToArray(),renderers=rs,materials=rs.Select(r=>r.sharedMaterials).ToArray(),sourceMaterialStates=rs.SelectMany(r=>r.sharedMaterials).Where(m=>m!=null).Distinct().ToDictionary(m=>m,m=>EditorJsonUtility.ToJson(m))};
        }
        static void AddChecks(Snapshot before,List<PlannedSlot> slots,Report report)
        {
            bool transforms=true,meshes=true,colliders=true,materialScope=true;
            for(int i=0;i<before.transforms.Length;i++)transforms&=before.transforms[i]!=null&&before.transforms[i].localToWorldMatrix==before.matrices[i];
            for(int i=0;i<before.filters.Length;i++)meshes&=before.filters[i]!=null&&before.filters[i].sharedMesh==before.meshes[i];
            for(int i=0;i<before.colliders.Length;i++)colliders&=before.colliders[i]!=null&&EditorJsonUtility.ToJson(before.colliders[i])==before.colliderStates[i];
            for(int r=0;r<before.renderers.Length;r++)
            {
                Renderer renderer=before.renderers[r];if(renderer==null){materialScope=false;continue;}
                Material[] current=renderer.sharedMaterials;if(current.Length!=before.materials[r].Length){materialScope=false;continue;}
                for(int slot=0;slot<current.Length;slot++)
                {
                    PlannedSlot change=slots.FirstOrDefault(p=>p.renderer==renderer&&p.binding.materialSlot==slot);
                    materialScope&=current[slot]==(change==null?before.materials[r][slot]:change.newMaterial);
                }
            }
            Add(report,"world-poses-unchanged",transforms,"No transform or anchor matrix changed.");
            Add(report,"mesh-references-unchanged",meshes,"No ground/path/cliff geometry changed.");
            Add(report,"collider-state-unchanged",colliders,"Collider serialized states remain byte-for-byte identical.");
            Add(report,"only-approved-material-slots",materialScope,"All other renderers and material slots, including trees and windows, retain their references.");
            Add(report,"source-material-assets-unchanged",before.sourceMaterialStates.All(p=>p.Key!=null&&EditorJsonUtility.ToJson(p.Key)==p.Value),"No shared original material was mutated.");
            Add(report,"three-approved-renderers",slots.Select(s=>s.renderer).Distinct().Count()==3,"Only IslandGround, StonePaths and CoastalCliff under Terrain.");
            Add(report,"non-emissive-ground-stone-cliff",slots.All(s=>s.newMaterial.shader.name==ShaderName&&!s.newMaterial.IsKeywordEnabled("_EMISSION")),"Shader emission is hard-coded zero; no glow or decorative light added.");
        }
        static void CheckTexture(string path,Texture2D texture,Report report)
        {
            var importer=AssetImporter.GetAtPath(path) as TextureImporter;
            if(importer==null)throw new InvalidOperationException("Albedo path is not backed by a TextureImporter.");
            if(!importer.sRGBTexture||importer.textureType!=TextureImporterType.Default)throw new InvalidOperationException("Import the original albedo as Default/sRGB first; this builder does not mutate import settings.");
            if(!importer.mipmapEnabled||texture.mipmapCount<=1)report.warnings.Add("Albedo has no mip chain; root should enable mips before judging moving-camera aliasing.");
            if(texture.wrapMode!=TextureWrapMode.Repeat)report.warnings.Add("Albedo wrap is not Repeat. Fix its owned import settings before visual verification.");
            if(texture.filterMode==FilterMode.Point)report.warnings.Add("Point filtering is unsuitable for this soft ground candidate; no filter override was applied.");
        }
        static Transform DirectTerrain(Transform root)
        {
            var terrain=new List<Transform>();foreach(Transform t in root)if(t.name=="Terrain")terrain.Add(t);
            if(terrain.Count!=1)throw new InvalidOperationException("Expected one direct Terrain child on the supplied Island root.");return terrain[0];
        }
        static string PathFromRoot(Transform root,Transform t)
        {
            var parts=new List<string>();for(Transform p=t;p!=root;p=p.parent){if(p==null)throw new InvalidOperationException("Renderer escaped the supplied root.");parts.Add(p.name);}parts.Reverse();return string.Join("/",parts);
        }
        static void ValidateSettings(Settings s)
        {
            float[] v={s.textureMeters,s.textureLuminancePivot,s.textureContrast,s.textureChroma,s.macroMeters,s.stoneMeters,s.cliffMeters,s.layerMeters,s.groundReliefMeters,s.stoneReliefMeters,s.cliffReliefMeters};
            if(v.Any(n=>float.IsNaN(n)||float.IsInfinity(n))||s.textureMeters<.5f||s.textureMeters>8||s.textureLuminancePivot<.04f||s.textureLuminancePivot>.6f||s.textureContrast<0||s.textureContrast>1||s.textureChroma<0||s.textureChroma>.5f||s.macroMeters<2||s.macroMeters>12||s.stoneMeters<.15f||s.cliffMeters<.5f||s.layerMeters<.3f||s.groundReliefMeters<0||s.groundReliefMeters>.04f||s.stoneReliefMeters<0||s.stoneReliefMeters>.04f||s.cliffReliefMeters<0||s.cliffReliefMeters>.04f)throw new ArgumentException("Surface settings are outside their finite material ranges.");
        }
        static void Add(Report r,string name,bool passed,string detail)=>r.checks.Add(new Check{name=name,passed=passed,detail=detail});
        static string ProjectFile(string path)=>Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Application.dataPath),path));
        static void EnsureFolder(string path)
        {
            if(!path.StartsWith(OutputRoot+"/SurfaceGeneration_",StringComparison.Ordinal)||path.Contains(".."))throw new InvalidOperationException("Refusing to create a folder outside Generated/V2Surface generations.");
            string[] parts=path.Split('/');string current=parts[0];for(int i=1;i<parts.Length;i++){string next=current+"/"+parts[i];if(!AssetDatabase.IsValidFolder(next))AssetDatabase.CreateFolder(current,parts[i]);current=next;}
        }
    }
}
#endif
