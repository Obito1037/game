using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace BorrowedLight.Editor
{
    // Edit-mode only. Builds a temporary, inactive copy of the ORIGINAL hierarchy
    // as the reference, then checks every merged vertex and triangle against it.
    public static class StarfieldGeometryVerification
    {
        [Serializable]
        public sealed class Report
        {
            public bool passed;
            public string scope = "Edit-mode CPU geometry audit; not a GPU shader or visual/FPS test.";
            public int originalStars, originalGlints, originalRenderers;
            public int expectedVertices, actualVertices, expectedTriangles, actualTriangles, actualSubmeshes;
            public int colorComponents, minimumPhase = int.MaxValue, maximumPhase = int.MinValue;
            public string colorFormat;
            public int positionSamples, normalSamples, tangentSamples, uvSamples, phaseSamples, triangleIndexSamples;
            public int movingPositionSamples, boundsExtremeSamples;
            public float maxPositionError, maxNormalError, maxTangentError, maxUvError, maxMovingPositionError;
            public float[] sampleTimes = { 0, 17.5f, 90.25f };
            public Vector3 boundsCenter, boundsSize;
            public List<string> failures = new List<string>();
        }

        sealed class OriginalPart
        {
            public Transform Transform;
            public Mesh Mesh;
            public bool IsGlint;
            public int Phase;
        }

        public static string Run(string outputPath)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Run the starfield geometry audit in Edit mode only.");
            GameObject originalRoot = null;
            Mesh combined = null;
            var report = new Report();
            const float tolerance = .00002f;
            try
            {
                originalRoot = new GameObject("Temporary legacy star geometry audit");
                originalRoot.hideFlags = HideFlags.HideAndDontSave;
                originalRoot.SetActive(false);
                var originals = CreateLegacyHierarchy(originalRoot.transform);
                combined = CelestialStarField.BuildMesh(originals[0].Mesh, originals[1].Mesh, 9);
                var vertices = combined.vertices;
                var normals = combined.normals;
                var tangents = combined.tangents;
                var uv = combined.uv;
                var colors = combined.colors;
                var indices = combined.triangles;
                report.actualVertices = combined.vertexCount;
                report.actualTriangles = indices.Length / 3;
                report.actualSubmeshes = combined.subMeshCount;
                report.colorFormat = combined.GetVertexAttributeFormat(VertexAttribute.Color).ToString();
                report.colorComponents = combined.GetVertexAttributeDimension(VertexAttribute.Color);
                report.boundsCenter = combined.bounds.center;
                report.boundsSize = combined.bounds.size;
                if (report.colorFormat != "Float32" || report.colorComponents != 4)
                    report.failures.Add("Phase COLOR must contain four Float32 components.");
                if (normals.Length != vertices.Length || tangents.Length != vertices.Length ||
                    uv.Length != vertices.Length || colors.Length != vertices.Length)
                    throw new InvalidOperationException("Merged normal/tangent/UV/COLOR channel is incomplete.");

                int vertexStart = 0, indexStart = 0;
                foreach (var original in originals)
                {
                    report.originalRenderers++;
                    if (original.IsGlint) report.originalGlints++; else report.originalStars++;
                    var sourceVertices = original.Mesh.vertices;
                    var sourceNormals = original.Mesh.normals;
                    var sourceTangents = original.Mesh.tangents;
                    var sourceUv = original.Mesh.uv;
                    var sourceIndices = original.Mesh.triangles;
                    report.expectedVertices += sourceVertices.Length;
                    report.expectedTriangles += sourceIndices.Length / 3;
                    if (sourceNormals.Length != sourceVertices.Length || sourceUv.Length != sourceVertices.Length)
                        throw new InvalidOperationException("Original primitive lacks complete normals/UVs.");
                    var matrix = original.Transform.localToWorldMatrix;
                    var normalMatrix = matrix.inverse.transpose;
                    for (int j = 0; j < sourceVertices.Length; j++)
                    {
                        int mergedIndex = vertexStart + j;
                        var expectedPosition = original.Transform.TransformPoint(sourceVertices[j]);
                        report.maxPositionError = Mathf.Max(report.maxPositionError,
                            Vector3.Distance(expectedPosition, vertices[mergedIndex]));
                        report.positionSamples++;
                        var expectedNormal = normalMatrix.MultiplyVector(sourceNormals[j]).normalized;
                        report.maxNormalError = Mathf.Max(report.maxNormalError,
                            Vector3.Distance(expectedNormal, normals[mergedIndex]));
                        report.normalSamples++;
                        report.maxUvError = Mathf.Max(report.maxUvError, Vector2.Distance(sourceUv[j], uv[mergedIndex]));
                        report.uvSamples++;
                        if (sourceTangents.Length == sourceVertices.Length)
                        {
                            var sourceTangent = sourceTangents[j];
                            var direction = matrix.MultiplyVector(new Vector3(sourceTangent.x, sourceTangent.y, sourceTangent.z)).normalized;
                            var expectedTangent = new Vector4(direction.x, direction.y, direction.z, sourceTangent.w);
                            report.maxTangentError = Mathf.Max(report.maxTangentError,
                                Vector4.Distance(expectedTangent, tangents[mergedIndex]));
                            report.tangentSamples++;
                        }
                        var metadata = colors[mergedIndex];
                        if (metadata.r != original.Phase || metadata.g != 0 || metadata.b != 0 || metadata.a != 1)
                            throw new InvalidOperationException("A merged vertex lost its original drift phase.");
                        report.minimumPhase = Mathf.Min(report.minimumPhase, (int)metadata.r);
                        report.maximumPhase = Mathf.Max(report.maximumPhase, (int)metadata.r);
                        report.phaseSamples++;
                        foreach (float time in report.sampleTimes)
                        {
                            // Reference is the literal old WorldAtmosphere.Update
                            // formula, evaluated from this part's ORIGINAL index.
                            var legacyOffset = new Vector3(Mathf.Sin(time * .035f + original.Phase) * .35f,
                                Mathf.Sin(time * .12f + original.Phase * .7f) * .10f, 0);
                            var expectedMoved = expectedPosition + legacyOffset;
                            var mergedMoved = vertices[mergedIndex] + CelestialStarField.DriftAt(time, (int)metadata.r);
                            report.maxMovingPositionError = Mathf.Max(report.maxMovingPositionError,
                                Vector3.Distance(expectedMoved, mergedMoved));
                            report.movingPositionSamples++;
                        }
                        for (int x = -1; x <= 1; x += 2)
                            for (int y = -1; y <= 1; y += 2)
                            {
                                var extreme = vertices[mergedIndex] + new Vector3(x * .35f, y * .10f, 0);
                                if (!ContainsWithTolerance(combined.bounds, extreme, tolerance))
                                    throw new InvalidOperationException("Mesh bounds omit a drift extreme.");
                                report.boundsExtremeSamples++;
                            }
                    }
                    for (int j = 0; j < sourceIndices.Length; j++)
                    {
                        if (indices[indexStart + j] != vertexStart + sourceIndices[j])
                            throw new InvalidOperationException("Primitive triangle order or winding changed.");
                        report.triangleIndexSamples++;
                    }
                    vertexStart += sourceVertices.Length;
                    indexStart += sourceIndices.Length;
                }
                if (report.originalStars != 47 || report.originalGlints != 20 || report.originalRenderers != 67)
                    report.failures.Add("Legacy primitive inventory differs from 47 spheres and 20 cubes.");
                if (report.actualVertices != report.expectedVertices || report.actualTriangles != report.expectedTriangles || report.actualSubmeshes != 1)
                    report.failures.Add("Merged geometry totals or submesh count differ.");
                if (report.minimumPhase != 9 || report.maximumPhase != 55)
                    report.failures.Add("Nine preceding cloud drifters were not preserved.");
                if (report.maxPositionError > tolerance || report.maxNormalError > tolerance || report.maxTangentError > tolerance ||
                    report.maxUvError > tolerance || report.maxMovingPositionError > tolerance)
                    report.failures.Add("An original geometry channel exceeded the 0.00002 tolerance.");
            }
            catch (Exception exception)
            {
                report.failures.Add(exception.GetType().Name + ": " + exception.Message);
            }
            finally
            {
                if (combined != null) UnityEngine.Object.DestroyImmediate(combined);
                if (originalRoot != null) UnityEngine.Object.DestroyImmediate(originalRoot);
            }
            report.passed = report.failures.Count == 0;
            string json = JsonUtility.ToJson(report, true);
            if (!string.IsNullOrEmpty(outputPath))
            {
                string absolute = Path.GetFullPath(outputPath);
                Directory.CreateDirectory(Path.GetDirectoryName(absolute));
                File.WriteAllText(absolute, json);
            }
            return json;
        }

        static List<OriginalPart> CreateLegacyHierarchy(Transform root)
        {
            var parts = new List<OriginalPart>();
            var random = new System.Random(17);
            for (int i = 0; i < 47; i++)
            {
                var position = new Vector3((float)random.NextDouble() * 100 - 50,
                    (float)random.NextDouble() * 26 + 2, (float)random.NextDouble() * 45 + 18);
                var star = new GameObject("Legacy star " + i).transform;
                star.SetParent(root, false);
                star.position = position;
                float scale = .025f + (float)random.NextDouble() * .055f;
                AddPrimitive(parts, star, PrimitiveType.Sphere, Vector3.one * scale, Quaternion.identity, i + 9, false);
                if (i % 5 == 0)
                {
                    var glintScale = new Vector3(scale * 6, scale * .22f, scale * .22f);
                    AddPrimitive(parts, star, PrimitiveType.Cube, glintScale, Quaternion.identity, i + 9, true);
                    AddPrimitive(parts, star, PrimitiveType.Cube, glintScale, Quaternion.Euler(0, 0, 90), i + 9, true);
                }
            }
            return parts;
        }

        static void AddPrimitive(List<OriginalPart> parts, Transform parent, PrimitiveType type,
            Vector3 scale, Quaternion rotation, int phase, bool isGlint)
        {
            var primitive = GameObject.CreatePrimitive(type);
            primitive.SetActive(false);
            primitive.transform.SetParent(parent, false);
            primitive.transform.localScale = scale;
            primitive.transform.localRotation = rotation;
            parts.Add(new OriginalPart { Transform = primitive.transform,
                Mesh = primitive.GetComponent<MeshFilter>().sharedMesh, Phase = phase, IsGlint = isGlint });
        }

        static bool ContainsWithTolerance(Bounds bounds, Vector3 point, float tolerance)
        {
            var min = bounds.min - Vector3.one * tolerance;
            var max = bounds.max + Vector3.one * tolerance;
            return point.x >= min.x && point.x <= max.x && point.y >= min.y && point.y <= max.y && point.z >= min.z && point.z <= max.z;
        }
    }
}
