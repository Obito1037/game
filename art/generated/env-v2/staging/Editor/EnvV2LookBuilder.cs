#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV2LookBuilder
    {
        public const string Root = "Assets/JieGuang/Environment/Generated/V2Looks";
        public static EnvironmentLookLibrary CreateLibrary()
        {
            EnsureFolder(Root);
            string path = Root + "/EnvironmentLooks.asset";
            var library = AssetDatabase.LoadAssetAtPath<EnvironmentLookLibrary>(path);
            if (library == null) { library = ScriptableObject.CreateInstance<EnvironmentLookLibrary>(); AssetDatabase.CreateAsset(library, path); }
            string[] ids = { "prologue", "night-1", "night-2", "night-3", "before-dawn" };
            string[] labels = { "序章·送行", "第一章·长夜", "第二章·圆窗", "第三章·归航", "终章·天亮前" };
            float[] exposure = { .12f, .05f, .04f, .02f, .20f };
            float[] bloom = { .20f, .19f, .18f, .18f, .16f };
            float[] phases = { .16f, .065f, .025f, .012f, .09f };
            library.looks = new EnvironmentLookLibrary.Look[ids.Length];
            for (int i = 0; i < ids.Length; i++)
            {
                bool dawn = i == 4;
                float lift = dawn ? 1.28f : i == 0 ? 1.1f : 1;
                var look = new EnvironmentLookLibrary.Look {
                    id=ids[i], displayName=labels[i], profile=CreateProfile(ids[i],exposure[i],bloom[i],dawn),
                    ambientSky=new Color(.10f,.145f,.225f)*lift,
                    ambientEquator=new Color(.055f,.078f,.115f)*lift,
                    ambientGround=new Color(.026f,.033f,.043f)*lift,
                    zenith=new Color(.009f,.018f,.043f)*lift,
                    horizon=new Color(.045f,.073f,.105f)*lift,
                    seaDeep=new Color(.012f,.031f,.043f)*lift,
                    seaShallow=new Color(.042f,.087f,.101f)*lift,
                    earthLitFraction=phases[i], stars=dawn?.72f:.95f,
                    cloudOpacity=dawn?.085f:.055f,
                    keyIntensity=dawn?.48f:.42f, fillIntensity=dawn?.18f:.14f,
                    fogStart=45, fogEnd=190,
                };
                library.looks[i]=look;
            }
            EditorUtility.SetDirty(library); AssetDatabase.SaveAssetIfDirty(library);
            return library;
        }
        static VolumeProfile CreateProfile(string id,float exposure,float bloom,bool dawn)
        {
            string path=Root+"/"+id+".asset";
            var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
            if(profile==null){profile=ScriptableObject.CreateInstance<VolumeProfile>();profile.name=id;AssetDatabase.CreateAsset(profile,path);}
            var tone=Get<Tonemapping>(profile);tone.mode.Override(TonemappingMode.Neutral);
            var color=Get<ColorAdjustments>(profile);
            color.postExposure.Override(exposure);color.contrast.Override(4);color.saturation.Override(-3);
            var glow=Get<Bloom>(profile);
            glow.threshold.Override(1.05f);glow.intensity.Override(bloom);glow.scatter.Override(.62f);
            glow.clamp.Override(6);glow.highQualityFiltering.Override(false);glow.maxIterations.Override(4);
            var vignette=Get<Vignette>(profile);vignette.intensity.Override(dawn?.065f:.085f);vignette.smoothness.Override(.5f);
            var grain=Get<FilmGrain>(profile);grain.intensity.Override(0);grain.response.Override(.8f);
            // Explicitly disabled for gameplay; camera-owned close-ups can opt into a separate profile.
            var dof=Get<DepthOfField>(profile);dof.mode.Override(DepthOfFieldMode.Off);
            dof.gaussianStart.Override(18);dof.gaussianEnd.Override(40);dof.gaussianMaxRadius.Override(.65f);
            foreach(var component in profile.components) EditorUtility.SetDirty(component);
            EditorUtility.SetDirty(profile);AssetDatabase.SaveAssetIfDirty(profile);
            return profile;
        }
        static T Get<T>(VolumeProfile profile) where T:VolumeComponent
        {
            if(!profile.TryGet(out T component)) { component=profile.Add<T>(false);AssetDatabase.AddObjectToAsset(component,profile); }
            component.active=true;return component;
        }
        public static EnvironmentLookRig Attach(GameObject island,EnvironmentLookLibrary library)
        {
            if(island==null||library==null)throw new ArgumentNullException();
            Transform atmosphere=island.transform.Find("Atmosphere");
            if(atmosphere==null)throw new InvalidOperationException("Expected owned Atmosphere subtree.");
            var rig=atmosphere.GetComponent<EnvironmentLookRig>();if(rig==null)rig=atmosphere.gameObject.AddComponent<EnvironmentLookRig>();
            rig.library=library;
            Transform volumeObject=atmosphere.Find("ChapterVolume_EnvV2");
            if(volumeObject==null){var go=new GameObject("ChapterVolume_EnvV2");go.transform.SetParent(atmosphere,false);volumeObject=go.transform;}
            var volume=volumeObject.GetComponent<Volume>();if(volume==null)volume=volumeObject.gameObject.AddComponent<Volume>();
            volume.isGlobal=true;volume.priority=5;volume.weight=1;volume.sharedProfile=library.Get("night-1").profile;
            rig.volume=volume;
            rig.warmKey=atmosphere.Find("WarmEnvironmentKey")?.GetComponent<Light>();
            rig.warmFill=atmosphere.Find("WarmEnvironmentFill")?.GetComponent<Light>();
            rig.skyRenderer=atmosphere.Find("NightSky")?.GetComponent<Renderer>();
            rig.seaRenderer=atmosphere.Find("NightSea")?.GetComponent<Renderer>();
            // Serialized baseline is set on the scene, never by Awake/LateUpdate competing with story NightSky.
            rig.currentLook="night-1";
            return rig;
        }
        public static void ConfigureTestCamera(Camera camera)
        {
            camera.allowHDR=true;
            var data=camera.GetUniversalAdditionalCameraData();
            data.renderPostProcessing=true;data.volumeLayerMask=1;
            data.requiresDepthTexture=true;
        }
        static void EnsureFolder(string path)
        {
            if(!path.StartsWith("Assets/JieGuang/Environment/",StringComparison.Ordinal))throw new InvalidOperationException("Environment path required.");
            if(AssetDatabase.IsValidFolder(path))return;
            string parent=Path.GetDirectoryName(path).Replace('\\','/');
            if(!AssetDatabase.IsValidFolder(parent))EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent,Path.GetFileName(path));
        }
    }
}
#endif
