using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace JieGuang.EditorTools
{
    // Builds the playable scene: base materials (so runtime-made materials keep their URP
    // shaders in builds), audio, and one GameDirector wired to the character prefabs and,
    // when the environment track has delivered it, Assets/JieGuang/Environment/Island.prefab.
    public static class JieGuangSceneBuilder
    {
        public const string ScenePath = "Assets/JieGuang/Scenes/JieGuang_Main.unity";
        const string IslandPrefabPath = "Assets/JieGuang/Environment/Island.prefab";

        [MenuItem("JieGuang/Build Main Scene")]
        public static void Build()
        {
            JieGuangQualityBuilder.Build();
            EnsureBaseMaterials();
            EnsureAudio();
            Directory.CreateDirectory("Assets/JieGuang/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var go = new GameObject("GameDirector");
            var d = go.AddComponent<GameDirector>();
            string P(string id) => "Assets/JieGuang/Prefabs/Characters/" + id + ".prefab";
            d.PlayerPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(P("xiaodenglong"));
            d.AYingPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(P("aying"));
            d.PostmanPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(P("postman"));
            d.ABoPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(P("abo"));
            d.DengBoPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(P("dengbo"));
            // the Tripo-dressed copy wins when it has been built
            d.IslandPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(IslandV2Builder.OutputPrefab) ?? AssetDatabase.LoadAssetAtPath<GameObject>(IslandPrefabPath);
            Debug.Log("[JieGuang] main scene built; island prefab " + (d.IslandPrefab != null ? "found" : "missing - graybox will be used"));
            EditorSceneManager.SaveScene(scene, ScenePath);
            var scenes = EditorBuildSettings.scenes;
            bool present = false;
            foreach (var s in scenes) present |= s.path == ScenePath;
            if (!present)
            {
                var list = new System.Collections.Generic.List<EditorBuildSettingsScene> { new EditorBuildSettingsScene(ScenePath, true) };
                foreach (var s in scenes) { s.enabled = false; list.Add(s); }
                EditorBuildSettings.scenes = list.ToArray();
            }
        }

        static void EnsureBaseMaterials()
        {
            const string dir = "Assets/JieGuang/Resources/Materials";
            Directory.CreateDirectory(dir);
            Make(dir + "/Base_Lit.mat", "Universal Render Pipeline/Lit", m => { m.SetFloat("_Smoothness", 0.15f); });
            Make(dir + "/Base_Unlit.mat", "Universal Render Pipeline/Unlit", m => { });
            Make(dir + "/Base_Beam.mat", "JieGuang/SoftBeam", m => { m.SetFloat("_BeamDensity", .018f); m.SetFloat("_EdgeSoftness", 1f); m.SetFloat("_DepthFade", .35f); });
            Make(dir + "/Base_Skybox.mat", "JieGuang/NightSkybox", m => { });
            Make(dir + "/Base_CharacterRim.mat", "JieGuang/CharacterRim", m => { m.renderQueue = 3000; });
            Make(dir + "/Base_Sea.mat", "JieGuang/NightSea", m => { m.SetFloat("_Ripple", .10f); m.SetFloat("_Fresnel", .5f); m.SetFloat("_WaveHeight", .035f); m.SetColor("_Deep", new Color(.008f,.027f,.060f)); m.SetColor("_Shallow", new Color(.025f,.075f,.095f)); m.renderQueue=-1; });
            Make(dir + "/Base_Additive.mat", "Universal Render Pipeline/Particles/Unlit", m =>
            {
                m.SetFloat("_Surface", 1f);
                m.SetFloat("_Blend", 2f);
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)BlendMode.One);
                m.SetFloat("_ZWrite", 0f);
                m.SetFloat("_Cull", 0f);
                m.SetOverrideTag("RenderType", "Transparent");
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                m.renderQueue = (int)RenderQueue.Transparent;
            });
        }

        static void Make(string path, string shader, System.Action<Material> setup)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(Shader.Find(shader));
                AssetDatabase.CreateAsset(m, path);
            }
            setup(m);
            EditorUtility.SetDirty(m);
        }

        static void EnsureAudio()
        {
            const string dir = "Assets/JieGuang/Resources/Audio";
            Directory.CreateDirectory(dir);
            foreach (var name in new[] { "LanternChime.wav", "NightLetters.wav" })
            {
                string src = "Assets/BorrowedLight/Resources/Audio/" + name, dst = dir + "/" + name;
                if (!File.Exists(dst) && File.Exists(src)) AssetDatabase.CopyAsset(src, dst);
            }
            AssetDatabase.SaveAssets();
        }
    }
}
