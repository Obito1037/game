// Evaluate in the existing Editor. Creates an opt-in Resources material only.
// Does not touch normal gameplay's Remap, its Meadow files, or the island model.
string projectRoot = System.IO.Path.GetFullPath(System.IO.Path.Combine(UnityEngine.Application.dataPath, "..", ".."));
string original = System.IO.Path.Combine(projectRoot, "art", "generated", "ground-v12", "earth-detail-original.png");
string texturePath = "Assets/BorrowedLight/Resources/Textures/GroundDetailV12.png";
string shaderPath = "Assets/BorrowedLight/Shaders/GroundDetail.shader";
string materialPath = "Assets/BorrowedLight/Resources/Materials/GroundDetailV12.mat";
string expectedSHA = "483D36A325CA6B05BBB8580DD3E238AF866F331D762976CB0064569FD7925F1B";
string originalHash, resourceHash;
using (var sha = System.Security.Cryptography.SHA256.Create()) originalHash = System.BitConverter.ToString(sha.ComputeHash(System.IO.File.ReadAllBytes(original))).Replace("-", "");
if (originalHash != expectedSHA) throw new System.IO.InvalidDataException("Reviewed ground original identity changed");
string destination = System.IO.Path.Combine(UnityEngine.Application.dataPath, "BorrowedLight", "Resources", "Textures", "GroundDetailV12.png");
if (!System.IO.File.Exists(destination)) System.IO.File.Copy(original, destination, false);
using (var sha = System.Security.Cryptography.SHA256.Create()) resourceHash = System.BitConverter.ToString(sha.ComputeHash(System.IO.File.ReadAllBytes(destination))).Replace("-", "");
if (resourceHash != originalHash) throw new System.IO.InvalidDataException("Ground Resources copy differs from original; refusing to overwrite");
UnityEditor.AssetDatabase.ImportAsset(shaderPath, UnityEditor.ImportAssetOptions.ForceUpdate);
UnityEditor.AssetDatabase.ImportAsset(texturePath, UnityEditor.ImportAssetOptions.ForceUpdate);
var importer = UnityEditor.AssetImporter.GetAtPath(texturePath) as UnityEditor.TextureImporter;
if (importer == null) throw new System.IO.InvalidDataException("Ground detail texture importer missing");
importer.textureType = UnityEditor.TextureImporterType.Default;
importer.sRGBTexture = true;
importer.alphaSource = UnityEditor.TextureImporterAlphaSource.None;
importer.mipmapEnabled = true;
importer.streamingMipmaps = false;
importer.npotScale = UnityEditor.TextureImporterNPOTScale.None;
importer.wrapMode = UnityEngine.TextureWrapMode.Repeat;
importer.filterMode = UnityEngine.FilterMode.Trilinear;
importer.anisoLevel = 4;
importer.maxTextureSize = 2048;
importer.textureCompression = UnityEditor.TextureImporterCompression.Uncompressed;
// Preserve the original 1254x1254 sampling; no editor image processing or resizing.
foreach (string platform in new[] { "Standalone", "WebGL" })
{
    var settings = importer.GetPlatformTextureSettings(platform);
    settings.name = platform; settings.overridden = true; settings.maxTextureSize = 2048;
    settings.format = UnityEditor.TextureImporterFormat.RGBA32;
    settings.textureCompression = UnityEditor.TextureImporterCompression.Uncompressed;
    settings.crunchedCompression = false;
    importer.SetPlatformTextureSettings(settings);
}
importer.SaveAndReimport();
var texture = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>(texturePath);
var shader = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Shader>(shaderPath);
if (texture == null || shader == null) throw new System.IO.InvalidDataException("Ground candidate assets did not import");
var meadow = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>("Assets/BorrowedLight/Resources/Textures/Meadow.png");
var normal = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>("Assets/BorrowedLight/Resources/Textures/MeadowNormal.png");
if (meadow == null || normal == null) throw new System.IO.InvalidDataException("Frozen v11 Meadow assets missing");
var material = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>(materialPath);
if (material == null) { material = new UnityEngine.Material(shader); UnityEditor.AssetDatabase.CreateAsset(material, materialPath); }
material.shader = shader;
material.SetTexture("_BaseMap", meadow); material.SetColor("_BaseColor", UnityEngine.Color.white);
material.SetTextureScale("_BaseMap", UnityEngine.Vector2.one); material.SetTextureOffset("_BaseMap", UnityEngine.Vector2.zero);
material.SetTexture("_BumpMap", normal); material.SetFloat("_BumpScale", .22f);
material.SetTexture("_DetailAlbedoMap", texture);
material.SetTextureScale("_DetailAlbedoMap", UnityEngine.Vector2.one / 1.8f);
material.SetTextureOffset("_DetailAlbedoMap", UnityEngine.Vector2.zero);
material.SetFloat("_DetailAlbedoMapScale", .55f); material.SetFloat("_DetailNormalMapScale", 0);
material.SetFloat("_Metallic", 0); material.SetFloat("_Smoothness", 0); material.SetFloat("_Cull", 0);
material.SetFloat("_SpecularHighlights", 0); material.SetFloat("_EnvironmentReflections", 0);
material.SetColor("_EmissionColor", UnityEngine.Color.black); material.SetFloat("_Surface", 0);
material.doubleSidedGI = true;
material.EnableKeyword("_NORMALMAP"); material.EnableKeyword("_SPECULARHIGHLIGHTS_OFF"); material.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
material.DisableKeyword("_DETAIL_MULX2"); material.DisableKeyword("_DETAIL_SCALED"); material.DisableKeyword("_EMISSION");
UnityEditor.EditorUtility.SetDirty(material); UnityEditor.AssetDatabase.SaveAssets();
var shaderMessages = new System.Collections.Generic.List<object>();
foreach (var message in UnityEditor.ShaderUtil.GetShaderMessages(shader)) shaderMessages.Add(new { severity = message.severity.ToString(), message = message.message, line = message.line, platform = message.platform.ToString() });
return new { stagingOnly = true, normalGameplayRemapUnchanged = true, originalHash, resourceHash,
    texture = texture.name, texture.width, texture.height, format = texture.format.ToString(), texture.mipmapCount,
    imageContentsHash = texture.imageContentsHash.ToString(), importer.sRGBTexture,
    filter = texture.filterMode.ToString(), aniso = texture.anisoLevel, shader = shader.name, supported = shader.isSupported,
    tileMetres = 1.8, strength = .55, originalNormalScale = .22,
    authoredLinearLuminanceMean = .15805805065816778, clampedRatioMean = .9620164207456156,
    shaderMessages, studyArgument = "-borrowedLightGroundDetailStudy", materialPath };
