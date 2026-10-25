using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // Pulls the user's v3 generated images out of Downloads\借光岛_v3模型\ into the project.
    // Currently: S07 (fully lit Earth disc) → Resources/World/S07_earth.png, readable, so
    // NightSky relights it for every phase. Models go through art/blender/process_props_v2.py.
    public static class V3DownloadsImporter
    {
        const string Folder = "借光岛_v3模型";

        [MenuItem("JieGuang/Import v3 Downloads")]
        public static void Import()
        {
            string downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads", Folder);
            if (!Directory.Exists(downloads)) { Debug.Log("[JieGuang] No " + downloads + " yet."); return; }
            string earth = Path.Combine(downloads, "v3_S07_earth_full.png");
            if (File.Exists(earth))
            {
                const string dst = "Assets/JieGuang/Resources/World/S07_earth.png";
                Directory.CreateDirectory(Path.GetDirectoryName(dst));
                File.Copy(earth, dst, true);
                AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceUpdate);
                var importer = (TextureImporter)AssetImporter.GetAtPath(dst);
                importer.isReadable = true;
                importer.mipmapEnabled = false;
                importer.maxTextureSize = 2048;
                importer.textureCompression = TextureImporterCompression.Uncompressed;
                importer.SaveAndReimport();
                Debug.Log("[JieGuang] S07 Earth imported: " + dst);
            }
        }
    }
}
