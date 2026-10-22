using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace BorrowedLight
{
    // The background stars keep the original Unity primitive geometry. One
    // forward renderer replaces their individual renderers and CPU transforms.
    public sealed class CelestialStarField : MonoBehaviour
    {
        public const int StarCount = 47;
        public const int GlintCount = 20;
        public const string ShaderName = "BorrowedLight/Starfield";

        public readonly struct StarSpec
        {
            public readonly Vector3 Position;
            public readonly float Scale;
            public readonly int DriftIndex;
            public readonly bool HasGlint;

            public StarSpec(Vector3 position, float scale, int driftIndex, bool hasGlint)
            {
                Position = position;
                Scale = scale;
                DriftIndex = driftIndex;
                HasGlint = hasGlint;
            }
        }

        public Mesh CombinedMesh { get; private set; }
        public Material RuntimeMaterial { get; private set; }
        public int DriftIndexOffset { get; private set; }

        // Pure layout calculation: same seed, draw order, range and float casts
        // as WorldAtmosphere.CreateStars. Clouds consume drift indices first.
        public static StarSpec[] GenerateLayout(int driftIndexOffset)
        {
            var result = new StarSpec[StarCount];
            var random = new System.Random(17);
            for (int i = 0; i < result.Length; i++)
            {
                var position = new Vector3(
                    (float)random.NextDouble() * 100 - 50,
                    (float)random.NextDouble() * 26 + 2,
                    (float)random.NextDouble() * 45 + 18);
                float scale = .025f + (float)random.NextDouble() * .055f;
                result[i] = new StarSpec(position, scale, driftIndexOffset + i, i % 5 == 0);
            }
            return result;
        }

        // Exposed for geometry-only comparison with the old CPU drift loop.
        public static Vector3 DriftAt(float time, int originalDriftIndex)
        {
            return new Vector3(Mathf.Sin(time * .035f + originalDriftIndex) * .35f,
                Mathf.Sin(time * .12f + originalDriftIndex * .7f) * .10f, 0);
        }

        public static Mesh BuildMesh(Mesh sphere, Mesh cube, int driftIndexOffset)
        {
            if (sphere == null || cube == null)
                throw new ArgumentException("The original Unity sphere and cube meshes are required.");
            var vertices = new List<Vector3>(StarCount * sphere.vertexCount + GlintCount * cube.vertexCount);
            var normals = new List<Vector3>(vertices.Capacity);
            var tangents = new List<Vector4>(vertices.Capacity);
            var uv = new List<Vector2>(vertices.Capacity);
            var metadata = new List<Color>(vertices.Capacity);
            var indices = new List<int>();

            // Read each primitive once; reuse all original vertices/indices,
            // including UV seams and the sphere's original pole topology.
            var sphereData = new PrimitiveData(sphere);
            var cubeData = new PrimitiveData(cube);
            foreach (var star in GenerateLayout(driftIndexOffset))
            {
                Append(sphereData, Matrix4x4.TRS(star.Position, Quaternion.identity,
                    Vector3.one * star.Scale), star.DriftIndex, vertices, normals, tangents, uv, metadata, indices);
                if (!star.HasGlint) continue;
                var glintScale = new Vector3(star.Scale * 6, star.Scale * .22f, star.Scale * .22f);
                Append(cubeData, Matrix4x4.TRS(star.Position, Quaternion.identity, glintScale),
                    star.DriftIndex, vertices, normals, tangents, uv, metadata, indices);
                Append(cubeData, Matrix4x4.TRS(star.Position, Quaternion.Euler(0, 0, 90), glintScale),
                    star.DriftIndex, vertices, normals, tangents, uv, metadata, indices);
            }

            var mesh = new Mesh { name = "47 original stars and 20 solid glints",
                indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            mesh.SetVertices(vertices);
            mesh.SetNormals(normals);
            mesh.SetTangents(tangents);
            mesh.SetUVs(0, uv);
            // Float COLOR is intentional: phase indices can exceed one.
            // Color32 would clamp them and synchronize unrelated stars.
            mesh.SetColors(metadata);
            mesh.SetTriangles(indices, 0, true);
            var bounds = mesh.bounds;
            bounds.Expand(new Vector3(.70f, .20f, 0));
            mesh.bounds = bounds;
            return mesh;
        }

        // Call in place of CreateStars, passing drifters.Count and the Resources
        // material that retains Starfield.shader in player builds. The caller
        // can retain the old CreateStars implementation as a null-return fallback.
        public static CelestialStarField TryCreate(Transform parent, int driftIndexOffset, Material retainedMaterial)
        {
            if (parent == null || retainedMaterial == null || retainedMaterial.shader == null ||
                retainedMaterial.shader.name != ShaderName) return null;

            GameObject sphere = null, cube = null, root = null;
            Mesh mesh = null;
            Material material = null;
            try
            {
                sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                sphere.SetActive(false);
                cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cube.SetActive(false);
                mesh = BuildMesh(sphere.GetComponent<MeshFilter>().sharedMesh,
                    cube.GetComponent<MeshFilter>().sharedMesh, driftIndexOffset);

                material = new Material(retainedMaterial) { name = "The original warm distant starlight" };
                var color = new Color(1, .77f, .4f);
                material.SetColor("_BaseColor", color);
                material.SetFloat("_Smoothness", .25f);
                material.SetFloat("_Metallic", 0);
                material.SetColor("_EmissionColor", color * 2.8f);

                // Geometry is authored in the legacy stars' world coordinates.
                // Preserve world identity when parenting to the fixed atmosphere.
                root = new GameObject("A field of 47 distant stars");
                root.transform.SetParent(parent, true);
                root.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = root.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = material;
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = true;
                var field = root.AddComponent<CelestialStarField>();
                field.CombinedMesh = mesh;
                field.RuntimeMaterial = material;
                field.DriftIndexOffset = driftIndexOffset;
                return field;
            }
            catch (Exception exception)
            {
                if (root != null) Release(root);
                Release(mesh);
                Release(material);
                Debug.LogWarning("Could not combine distant stars; retain the legacy fallback. " + exception.Message);
                return null;
            }
            finally
            {
                Release(sphere);
                Release(cube);
            }
        }

        sealed class PrimitiveData
        {
            public readonly Vector3[] Vertices, Normals;
            public readonly Vector4[] Tangents;
            public readonly Vector2[] UV;
            public readonly int[] Indices;
            public PrimitiveData(Mesh mesh)
            {
                Vertices = mesh.vertices; Normals = mesh.normals;
                Tangents = mesh.tangents; UV = mesh.uv; Indices = mesh.triangles;
                if (Normals.Length != Vertices.Length || UV.Length != Vertices.Length)
                    throw new ArgumentException("Primitive normal and UV data must be complete.");
            }
        }

        static void Append(PrimitiveData source, Matrix4x4 matrix, int driftIndex,
            List<Vector3> vertices, List<Vector3> normals, List<Vector4> tangents,
            List<Vector2> uv, List<Color> metadata, List<int> indices)
        {
            int first = vertices.Count;
            var normalMatrix = matrix.inverse.transpose;
            for (int i = 0; i < source.Vertices.Length; i++)
            {
                vertices.Add(matrix.MultiplyPoint3x4(source.Vertices[i]));
                normals.Add(normalMatrix.MultiplyVector(source.Normals[i]).normalized);
                var tangent = source.Tangents.Length == source.Vertices.Length ? source.Tangents[i] : new Vector4(1, 0, 0, 1);
                var direction = matrix.MultiplyVector(new Vector3(tangent.x, tangent.y, tangent.z)).normalized;
                tangents.Add(new Vector4(direction.x, direction.y, direction.z, tangent.w));
                uv.Add(source.UV[i]);
                metadata.Add(new Color(driftIndex, 0, 0, 1));
            }
            foreach (int index in source.Indices) indices.Add(first + index);
        }

        void OnDestroy()
        {
            Release(CombinedMesh);
            Release(RuntimeMaterial);
        }

        static void Release(UnityEngine.Object value)
        {
            if (value == null) return;
            if (Application.isPlaying) Destroy(value); else DestroyImmediate(value);
        }
    }
}
