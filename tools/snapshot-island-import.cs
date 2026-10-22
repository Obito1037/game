// Read-only snapshot of the actual Unity-imported island, before/after FBX replacement.
var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.GameObject>("Assets/BorrowedLight/Resources/Models/Island.fbx");
if (prefab == null) throw new System.IO.InvalidDataException("Island prefab is missing");
var meshes = new System.Collections.Generic.List<object>();
long totalTriangles = 0;
foreach (var filter in prefab.GetComponentsInChildren<UnityEngine.MeshFilter>(true))
{
    var mesh = filter.sharedMesh;
    var stream = new System.IO.MemoryStream();
    var writer = new System.IO.BinaryWriter(stream);
    foreach (var p in mesh.vertices) { writer.Write(p.x); writer.Write(p.y); writer.Write(p.z); }
    foreach (var n in mesh.normals) { writer.Write(n.x); writer.Write(n.y); writer.Write(n.z); }
    foreach (var t in mesh.tangents) { writer.Write(t.x); writer.Write(t.y); writer.Write(t.z); writer.Write(t.w); }
    foreach (var uv in mesh.uv) { writer.Write(uv.x); writer.Write(uv.y); }
    foreach (var c in mesh.colors) { writer.Write(c.r); writer.Write(c.g); writer.Write(c.b); writer.Write(c.a); }
    int triangles = 0;
    for (int s = 0; s < mesh.subMeshCount; s++)
    {
        var indices = mesh.GetIndices(s); writer.Write(indices.Length);
        foreach (var index in indices) writer.Write(index);
        triangles += indices.Length / 3;
    }
    writer.Flush();
    string hash;
    using (var sha = System.Security.Cryptography.SHA256.Create()) hash = System.BitConverter.ToString(sha.ComputeHash(stream.ToArray())).Replace("-", "");
    writer.Dispose(); stream.Dispose();
    var materials = new System.Collections.Generic.List<object>();
    foreach (var m in filter.GetComponent<UnityEngine.Renderer>().sharedMaterials)
    {
        var c = m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor") : m.HasProperty("_Color") ? m.GetColor("_Color") : UnityEngine.Color.white;
        materials.Add(new { name = m.name, shader = m.shader.name, rgba = new[] { c.r, c.g, c.b, c.a } });
    }
    var matrix = new float[16]; for (int i = 0; i < 16; i++) matrix[i] = filter.transform.localToWorldMatrix[i];
    meshes.Add(new { name = filter.name, vertices = mesh.vertexCount, triangles, submeshes = mesh.subMeshCount,
        normalCount = mesh.normals.Length, colorCount = mesh.colors.Length, geometrySHA256 = hash, matrix, materials });
    totalTriangles += triangles;
}
var anchors = new System.Collections.Generic.List<object>();
foreach (var t in prefab.GetComponentsInChildren<UnityEngine.Transform>(true))
{
    if (t.GetComponent<UnityEngine.MeshFilter>() != null || t == prefab.transform) continue;
    var matrix = new float[16]; for (int i = 0; i < 16; i++) matrix[i] = t.localToWorldMatrix[i];
    anchors.Add(new { name = t.name, matrix });
}
return new { asset = "Assets/BorrowedLight/Resources/Models/Island.fbx", unity = UnityEngine.Application.unityVersion,
    scope = "Actual imported mesh positions/normals/tangents/UV/color/index bytes, submesh materials, transforms and anchors. Not a visual quality judgment.",
    totalTriangles, meshes, anchors };
