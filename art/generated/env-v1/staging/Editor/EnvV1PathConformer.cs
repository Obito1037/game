#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    /// <summary>Derives the path surface from the imported ground collider without editing FBX assets.</summary>
    public static class EnvV1PathConformer
    {
        private const string OutputRoot = "Assets/JieGuang/Environment/Generated/Meshes/";
        private const float SurfaceOffset = .045f;

        // Call after the terrain's Layer 8 MeshCollider has been created.
        public static void Conform(GameObject high, string assetPath)
        {
            if (high == null) throw new ArgumentNullException(nameof(high));
            assetPath = ValidateOutputPath(assetPath);

            MeshCollider ground = null;
            foreach (MeshCollider candidate in high.GetComponentsInChildren<MeshCollider>(true))
            {
                if (candidate.gameObject.layer != 8 ||
                    !candidate.name.StartsWith("IslandGround", StringComparison.Ordinal)) continue;
                if (ground != null) throw new InvalidOperationException("Expected one IslandGround collider.");
                ground = candidate;
            }
            if (ground == null || ground.sharedMesh == null || !ground.enabled ||
                !ground.gameObject.activeInHierarchy || ground.convex)
                throw new InvalidOperationException("Create an active, non-convex Layer 8 IslandGround MeshCollider before conforming paths.");

            MeshFilter paths = null;
            foreach (MeshFilter candidate in high.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!candidate.name.StartsWith("StonePaths", StringComparison.Ordinal)) continue;
                if (paths != null) throw new InvalidOperationException("Expected one StonePaths MeshFilter.");
                paths = candidate;
            }
            if (paths == null || paths.sharedMesh == null)
                throw new InvalidOperationException("StonePaths mesh is missing from the imported terrain.");

            Mesh source = paths.sharedMesh;
            if (!source.isReadable) throw new InvalidOperationException("Import StonePaths with Read/Write enabled.");
            Object existingAsset = AssetDatabase.LoadMainAssetAtPath(assetPath);
            if (existingAsset != null && !(existingAsset is Mesh))
                throw new InvalidOperationException("The derived mesh destination contains another asset type: " + assetPath);
            if (source == existingAsset)
            {
                Debug.Log("StonePaths already references its derived mesh; subdivision skipped. Rebuild from the FBX to regenerate.", paths);
                return;
            }

            var vertices = new List<Vector3>(source.vertices);
            var colors = new List<Color>(source.colors);
            bool hasColors = colors.Count == vertices.Count;
            var uvChannels = new List<Vector4>[8];
            for (int channel = 0; channel < uvChannels.Length; channel++)
            {
                var uv = new List<Vector4>();
                source.GetUVs(channel, uv);
                if (uv.Count == vertices.Count) uvChannels[channel] = uv;
            }
            var midpointIndices = new Dictionary<ulong, int>();
            var submeshes = new List<int>[source.subMeshCount];
            int originalTriangles = 0;
            for (int submesh = 0; submesh < source.subMeshCount; submesh++)
            {
                if (source.GetTopology(submesh) != MeshTopology.Triangles)
                    throw new InvalidOperationException("StonePaths must contain triangle submeshes.");
                int[] triangles = source.GetTriangles(submesh);
                originalTriangles += triangles.Length / 3;
                var divided = new List<int>(triangles.Length * 4);
                submeshes[submesh] = divided;
                for (int t = 0; t < triangles.Length; t += 3)
                {
                    int a = triangles[t], b = triangles[t + 1], c = triangles[t + 2];
                    int ab = Midpoint(a, b, vertices, uvChannels, hasColors ? colors : null, midpointIndices);
                    int bc = Midpoint(b, c, vertices, uvChannels, hasColors ? colors : null, midpointIndices);
                    int ca = Midpoint(c, a, vertices, uvChannels, hasColors ? colors : null, midpointIndices);
                    // Preserve the imported local-space winding and submesh/material assignment.
                    divided.AddRange(new[] { a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca });
                }
            }

            Physics.SyncTransforms();
            int projectedVertices = 0;
            for (int i = 0; i < vertices.Count; i++)
            {
                Vector3 world = paths.transform.TransformPoint(vertices[i]);
                var ray = new Ray(world + Vector3.up * 20f, Vector3.down);
                // Query this collider exclusively; roofs, rocks and old paths cannot receive the projection.
                float distance = 20f + Mathf.Max(20f, world.y - ground.bounds.min.y + 1f);
                if (!ground.Raycast(ray, out RaycastHit hit, distance)) continue;
                world.y = hit.point.y + SurfaceOffset;
                vertices[i] = paths.transform.InverseTransformPoint(world);
                projectedVertices++;
            }

            Mesh created = new Mesh { name = Path.GetFileNameWithoutExtension(assetPath), indexFormat = IndexFormat.UInt32 };
            try
            {
                created.SetVertices(vertices);
                for (int channel = 0; channel < uvChannels.Length; channel++)
                    if (uvChannels[channel] != null) created.SetUVs(channel, uvChannels[channel]);
                if (hasColors) created.SetColors(colors);
                created.subMeshCount = submeshes.Length;
                for (int i = 0; i < submeshes.Length; i++) created.SetTriangles(submeshes[i], i, false);
                created.RecalculateNormals();
                created.RecalculateBounds();
                if (uvChannels[0] != null) created.RecalculateTangents();

                Mesh saved;
                if (existingAsset is Mesh existing)
                {
                    EditorUtility.CopySerialized(created, existing);
                    EditorUtility.SetDirty(existing);
                    AssetDatabase.SaveAssetIfDirty(existing);
                    saved = existing;
                }
                else
                {
                    AssetDatabase.CreateAsset(created, assetPath);
                    AssetDatabase.SaveAssetIfDirty(created);
                    saved = created;
                }
                paths.sharedMesh = saved;
                Debug.Log("StonePaths: imported " + originalTriangles + " triangles -> derived " +
                    originalTriangles * 4 + " triangles; projected " + projectedVertices + "/" + vertices.Count +
                    " vertices at +0.045 m. Saved " + assetPath + ". Original FBX mesh unchanged.", paths);
                if (projectedVertices != vertices.Count)
                    Debug.LogWarning("StonePaths projection missed " + (vertices.Count - projectedVertices) +
                        " vertices; their original positions were retained. Inspect the terrain coverage.", paths);
            }
            finally
            {
                if (created != null && !AssetDatabase.Contains(created)) Object.DestroyImmediate(created);
            }
        }

        private static int Midpoint(int a, int b, List<Vector3> vertices, List<Vector4>[] uvChannels,
            List<Color> colors, Dictionary<ulong, int> cache)
        {
            ulong key = ((ulong)(uint)Math.Min(a, b) << 32) | (uint)Math.Max(a, b);
            if (cache.TryGetValue(key, out int found)) return found;
            int index = vertices.Count;
            vertices.Add((vertices[a] + vertices[b]) * .5f);
            foreach (List<Vector4> uv in uvChannels)
                if (uv != null) uv.Add((uv[a] + uv[b]) * .5f);
            if (colors != null) colors.Add((colors[a] + colors[b]) * .5f);
            cache.Add(key, index);
            return index;
        }

        private static string ValidateOutputPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentNullException(nameof(path));
            path = path.Replace('\\', '/');
            if (!path.StartsWith(OutputRoot, StringComparison.Ordinal) ||
                !path.EndsWith(".asset", StringComparison.OrdinalIgnoreCase) ||
                path.Contains("..") || path.Contains("//") || path.Contains(":"))
                throw new ArgumentException("The derived path mesh must be a separate .asset inside " + OutputRoot, nameof(path));
            string folder = Path.GetDirectoryName(path).Replace('\\', '/');
            if (!AssetDatabase.IsValidFolder(folder))
                throw new DirectoryNotFoundException("Create the generated mesh folder before conforming paths: " + folder);
            return path;
        }
    }
}
#endif
