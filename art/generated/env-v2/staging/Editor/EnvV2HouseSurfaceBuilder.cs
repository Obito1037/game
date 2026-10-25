#if UNITY_EDITOR
// Explicit helper only. No menu, initialize-on-load, scene access or prefab mutation.
// Called by the candidate integrator after importing the UV-corrected house FBX.
using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace JieGuang.EnvironmentTools
{
    public static class EnvV2HouseSurfaceBuilder
    {
        const string AllowedRoot = "Assets/JieGuang/Environment/";

        /// <summary>
        /// Creates four HOUSE-ONLY URP wood materials and returns the original
        /// FBX material name to shared Material mapping. Caller must consult this
        /// dictionary before its fallback material mapping and retain imported UV0.
        /// Writes only the supplied Environment texture importer and materialFolder.
        /// Does not modify old shared materials, meshes, scenes, prefabs or gameplay.
        /// </summary>
        public static Dictionary<string, Material> Prepare(string textureAssetPath, string materialFolder)
        {
            textureAssetPath = ValidatePath(textureAssetPath, "textureAssetPath");
            materialFolder = ValidatePath(materialFolder, "materialFolder").TrimEnd('/');
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(textureAssetPath);
            if (!texture) throw new InvalidOperationException("Import original wood texture first: " + textureAssetPath);
            var importer = AssetImporter.GetAtPath(textureAssetPath) as TextureImporter;
            if (importer == null) throw new InvalidOperationException("Not a texture importer: " + textureAssetPath);
            importer.textureType = TextureImporterType.Default;
            importer.sRGBTexture = true;
            importer.alphaSource = TextureImporterAlphaSource.None;
            importer.mipmapEnabled = true;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Trilinear;
            importer.anisoLevel = 4;
            importer.maxTextureSize = 2048;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            texture = AssetDatabase.LoadAssetAtPath<Texture2D>(textureAssetPath);
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (!shader) throw new InvalidOperationException("URP Lit shader is unavailable");
            EnsureFolder(materialFolder);

            var white = Create(materialFolder, "Whitewashed", shader, texture, new Color(1f, .96f, .86f, 1f), .78f);
            var weather = Create(materialFolder, "Weathered", shader, texture, new Color(.88f, .82f, .70f, 1f), .82f);
            var honey = Create(materialFolder, "Honey", shader, texture, new Color(.46f, .31f, .18f, 1f), .72f);
            var dark = Create(materialFolder, "DarkBeam", shader, texture, new Color(.25f, .17f, .10f, 1f), .80f);
            return new Dictionary<string, Material>(StringComparer.Ordinal)
            {
                { "V2_WhitewashedWood_0", weather }, { "V2_WhitewashedWood_1", white },
                { "V2_WhitewashedWood_2", white }, { "V2_WhitewashedWood_3", weather },
                { "V2_OldTimber_0", dark }, { "V2_OldTimber_1", honey }, { "V2_OldTimber_2", honey },
                { "Wall_WarmIvory", white }, { "Wall_LightTimber", weather },
                { "Wood_Honey", honey }, { "Wood_Endgrain", honey }, { "Wood_DarkBeams", dark }
            };
        }

        static Material Create(string folder, string suffix, Shader shader, Texture2D texture, Color tint, float roughness)
        {
            string path = folder + "/HouseWood_" + suffix + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!material)
            {
                material = new Material(shader) { name = "HouseWood_" + suffix };
                AssetDatabase.CreateAsset(material, path);
            }
            material.shader = shader;
            material.SetTexture("_BaseMap", texture);
            material.SetTextureScale("_BaseMap", Vector2.one);
            material.SetTextureOffset("_BaseMap", Vector2.zero);
            material.SetColor("_BaseColor", tint);
            material.SetFloat("_Metallic", 0f);
            material.SetFloat("_Smoothness", 1f - roughness);
            material.SetFloat("_Surface", 0f);
            material.SetFloat("_AlphaClip", 0f);
            material.SetFloat("_Cull", 2f);
            material.DisableKeyword("_ALPHATEST_ON");
            material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
            material.DisableKeyword("_NORMALMAP");
            material.DisableKeyword("_METALLICSPECGLOSSMAP");
            material.DisableKeyword("_EMISSION");
            material.renderQueue = -1;
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            // Avoid saving unrelated dirty assets in this concurrently used project.
            AssetDatabase.SaveAssetIfDirty(material);
            return material;
        }

        static string ValidatePath(string value, string argument)
        {
            if (string.IsNullOrEmpty(value)) throw new ArgumentException("Required", argument);
            value = value.Replace('\\', '/');
            if (!value.StartsWith(AllowedRoot, StringComparison.Ordinal) || value.Contains("../") || value.Contains("/..") || value.Contains(":"))
                throw new ArgumentException("Path must stay inside " + AllowedRoot, argument);
            return value;
        }

        static void EnsureFolder(string folder)
        {
            var parts = folder.Split('/');
            string parent = parts[0];
            for (int i = 1; i < parts.Length; ++i)
            {
                string next = parent + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(parent, parts[i]);
                parent = next;
            }
        }
    }
}
#endif
