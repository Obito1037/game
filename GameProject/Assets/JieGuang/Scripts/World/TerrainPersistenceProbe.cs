using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace JieGuang
{
    // Runs once only during native QA. Records what the player actually loaded, so a successful
    // Editor check cannot be mistaken for correct serialized terrain in the Windows/WebGL build.
    public sealed class TerrainPersistenceProbe : MonoBehaviour
    {
        void Start()
        {
            var args = Environment.GetCommandLineArgs();
            if (Array.IndexOf(args, "--jg-qa") < 0 && Array.IndexOf(args, "--jg-terrain-audit") < 0) return;
            var terrain = GetComponent<Terrain>();
            var data = terrain != null ? terrain.terrainData : null;
            var report = new StringBuilder("Loaded terrain runtime audit\n");
            report.AppendLine("platform=" + Application.platform + "; unity=" + Application.unityVersion);
            var surface = transform.parent != null ? transform.parent.Find("GroundSurfaceV2") : null;
            if (surface != null)
            {
                var mesh = surface.GetComponent<MeshFilter>().sharedMesh;
                var renderer = surface.GetComponent<MeshRenderer>();
                var groundMaterial = renderer.sharedMaterial;
                report.AppendLine("groundSurface=" + surface.gameObject.activeInHierarchy + "; renderer=" + renderer.enabled + "; triangles=" + mesh.triangles.Length / 3 + "; bounds=" + renderer.bounds);
                report.AppendLine("groundShader=" + groundMaterial.shader.name + "; supported=" + groundMaterial.shader.isSupported + "; passCount=" + groundMaterial.passCount);
            }
            else report.AppendLine("groundSurface=absent (older heightfield renderer)");
            if (terrain != null && Array.IndexOf(args, "--jg-terrain-no-instancing") >= 0)
            {
                terrain.drawInstanced = false;
                report.AppendLine("DIAGNOSTIC: --jg-terrain-no-instancing overrides drawInstanced=false for this run only.");
            }
            if (terrain == null || data == null) report.AppendLine("ERROR=missing Terrain or TerrainData");
            else
            {
                report.AppendLine("active=" + gameObject.activeInHierarchy + "; enabled=" + terrain.enabled + "; drawHeightmap=" + terrain.drawHeightmap + "; instanced=" + terrain.drawInstanced);
                report.AppendLine("data=" + data.name + "; size=" + data.size + "; heightRes=" + data.heightmapResolution + "; layers=" + data.terrainLayers.Length);
                var material = terrain.materialTemplate;
                report.AppendLine("material=" + (material != null ? material.name : "null") + "; shader=" + (material != null && material.shader != null ? material.shader.name : "null"));
                if (material != null && material.shader != null)
                    report.AppendLine("shaderSupported=" + material.shader.isSupported + "; passCount=" + material.passCount + "; keywords=" + string.Join(",", material.shaderKeywords));
                var weights = data.GetAlphamaps(0, 0, data.alphamapWidth, data.alphamapHeight);
                double[] sums = new double[weights.GetLength(2)];
                for (int z = 0; z < weights.GetLength(0); z++) for (int x = 0; x < weights.GetLength(1); x++) for (int l = 0; l < sums.Length; l++) sums[l] += weights[z, x, l];
                report.AppendLine("alphamap=" + data.alphamapWidth + "x" + data.alphamapHeight + "; textures=" + data.alphamapTextureCount);
                var layers = data.terrainLayers;
                for (int l = 0; l < sums.Length; l++)
                {
                    var diffuse = l < layers.Length && layers[l] != null ? layers[l].diffuseTexture : null;
                    report.AppendLine("layer" + l + " sum=" + sums[l].ToString("F3") + "; diffuse=" + (diffuse != null ? diffuse.name : "null"));
                }
                var holes = data.GetHoles(0, 0, data.holesResolution, data.holesResolution);
                int solid = 0;
                foreach (bool cell in holes) if (cell) solid++;
                report.AppendLine("solidCells=" + solid + "/" + holes.Length + "; centreHeight=" + data.GetInterpolatedHeight(.5f, .5f));
            }
            Debug.Log("[JieGuangTerrain]\n" + report);
            int outIndex = Array.IndexOf(args, "--jg-qa-out");
            if (outIndex >= 0 && outIndex + 1 < args.Length)
            {
                Directory.CreateDirectory(args[outIndex + 1]);
                File.WriteAllText(Path.Combine(args[outIndex + 1], "terrain-runtime-audit.txt"), report.ToString());
            }
        }
    }
}
