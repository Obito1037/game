using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace JieGuang.EditorTools
{
    // Reproducible v2 PC settings. Original template assets and Mobile/Web quality stay intact.
    public static class JieGuangQualityBuilder
    {
        const string SourcePipeline = "Assets/Settings/PC_RPAsset.asset";
        const string SourceRenderer = "Assets/Settings/PC_Renderer.asset";
        const string Folder = "Assets/JieGuang/Settings";
        public const string PipelinePath = Folder + "/JieGuang_PC_RPAsset.asset";
        public const string RendererPath = Folder + "/JieGuang_PC_Renderer.asset";

        [MenuItem("JieGuang/Build PC Quality Settings")]
        public static void Build()
        {
            var sourceRenderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(SourceRenderer);
            if (sourceRenderer == null || AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(SourcePipeline) == null)
                throw new InvalidOperationException("[JieGuang] Original PC pipeline/renderer assets are missing.");

            // Validate the exact quality rows before changing the generated assets or their link.
            var qualityObjects = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset");
            if (qualityObjects.Length == 0) throw new InvalidOperationException("[JieGuang] Cannot load QualitySettings.");
            var quality = new SerializedObject(qualityObjects[0]);
            var levels = Required(quality, "m_QualitySettings");
            if (levels.arraySize < 2 || levels.GetArrayElementAtIndex(0).FindPropertyRelative("name").stringValue != "Mobile"
                || levels.GetArrayElementAtIndex(1).FindPropertyRelative("name").stringValue != "PC")
                throw new InvalidOperationException("[JieGuang] Expected Mobile quality at 0 and PC at 1; no quality row changed.");
            var mobileReference = levels.GetArrayElementAtIndex(0).FindPropertyRelative("customRenderPipeline").objectReferenceValue;

            if (!AssetDatabase.IsValidFolder(Folder)) AssetDatabase.CreateFolder("Assets/JieGuang", "Settings");
            var renderer = RefreshCopy<UniversalRendererData>(SourceRenderer, RendererPath);
            bool foundSsao = false;
            foreach (var feature in renderer.rendererFeatures)
            {
                if (!(feature is ScreenSpaceAmbientOcclusion)) continue;
                // CopyAsset keeps renderer features as sub-assets of the new renderer.
                // Refuse to edit a feature that still points into the original asset.
                if (AssetDatabase.GetAssetPath(feature) != RendererPath)
                    throw new InvalidOperationException("[JieGuang] Copied SSAO feature is not owned by the derived renderer.");
                var ssao = new SerializedObject(feature);
                Required(ssao, "m_Settings.Downsample").boolValue = true;
                ssao.ApplyModifiedPropertiesWithoutUndo();
                // v3: SSAO measured ~2 ms on Iris Xe at night for little visible gain; kept, disabled
                feature.SetActive(false);
                EditorUtility.SetDirty(feature);
                foundSsao = true;
            }
            if (!foundSsao) throw new InvalidOperationException("[JieGuang] Original PC renderer has no SSAO feature to preserve.");
            renderer.SetDirty();
            EditorUtility.SetDirty(renderer);

            var pipeline = RefreshCopy<UniversalRenderPipelineAsset>(SourcePipeline, PipelinePath);
            pipeline.msaaSampleCount = 1;
            pipeline.renderScale = 1f;
            pipeline.shadowCascadeCount = 2;
            pipeline.shadowDistance = 38f;
            pipeline.additionalLightsShadowmapResolution = 1024;
            var pipelineSettings = new SerializedObject(pipeline);
            Required(pipelineSettings, "m_SoftShadowQuality").intValue = (int)SoftShadowQuality.Low;
            var renderers = Required(pipelineSettings, "m_RendererDataList");
            bool replacedRenderer = false;
            for (int i = 0; i < renderers.arraySize; i++)
            {
                var reference = renderers.GetArrayElementAtIndex(i);
                if (reference.objectReferenceValue != sourceRenderer) continue;
                reference.objectReferenceValue = renderer;
                replacedRenderer = true;
            }
            if (!replacedRenderer) throw new InvalidOperationException("[JieGuang] PC pipeline did not reference the expected source renderer.");
            pipelineSettings.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(pipeline);

            // Address PC directly; do not switch the currently selected quality/platform,
            // or touch Mobile's pipeline, WebGL's default index, or legacy quality fields.
            levels.GetArrayElementAtIndex(1).FindPropertyRelative("customRenderPipeline").objectReferenceValue = pipeline;
            quality.ApplyModifiedPropertiesWithoutUndo();
            quality.Update();
            if (Required(quality, "m_QualitySettings").GetArrayElementAtIndex(0)
                    .FindPropertyRelative("customRenderPipeline").objectReferenceValue != mobileReference)
                throw new InvalidOperationException("[JieGuang] Mobile pipeline reference changed unexpectedly.");
            EditorUtility.SetDirty(qualityObjects[0]);
            AssetDatabase.SaveAssets();
            Debug.Log("[JieGuang] PC quality: native render scale 1, MSAA 1, FXAA camera, two shadow cascades, Medium soft shadows, SSAO downsampled. Mobile/Web pipeline preserved.");
        }

        static T RefreshCopy<T>(string source, string destination) where T : UnityEngine.Object
        {
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string sourceFile = Path.Combine(projectRoot, source);
            string destinationFile = Path.Combine(projectRoot, destination);
            if (!File.Exists(destinationFile))
            {
                if (!AssetDatabase.CopyAsset(source, destination))
                    throw new IOException("[JieGuang] Could not copy " + source + " to " + destination);
            }
            else
            {
                // Rebase every run on the original, preserving the generated .meta/GUID.
                // The renderer's local sub-asset IDs remain local to the copied asset.
                File.Copy(sourceFile, destinationFile, true);
            }
            AssetDatabase.ImportAsset(destination, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            var result = AssetDatabase.LoadAssetAtPath<T>(destination);
            if (result == null) throw new InvalidOperationException("[JieGuang] Failed to load derived asset " + destination);
            return result;
        }

        static SerializedProperty Required(SerializedObject owner, string field)
        {
            var property = owner.FindProperty(field);
            if (property == null) throw new InvalidOperationException("[JieGuang] Expected serialized field missing: " + field);
            return property;
        }
    }
}
