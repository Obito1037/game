// Read-only runtime texture/importer identity for the active Unity build target.
var assetPath="Assets/BorrowedLight/Resources/Textures/GroundDetailV12.png";
var importer=(UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(assetPath);
var texture=UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Texture2D>(assetPath);
var platforms=new System.Collections.Generic.List<object>();
foreach(var name in new[]{"Standalone","WebGL"}){
 var p=importer.GetPlatformTextureSettings(name);
 platforms.Add(new { name,p.overridden,p.maxTextureSize,format=p.format.ToString(),compression=p.textureCompression.ToString(),p.compressionQuality,p.crunchedCompression });
}
string hash;using(var sha=System.Security.Cryptography.SHA256.Create())hash=System.BitConverter.ToString(sha.ComputeHash(System.IO.File.ReadAllBytes(assetPath))).Replace("-","");
return new { activeTarget=UnityEditor.EditorUserBuildSettings.activeBuildTarget.ToString(),assetPath,sourceSHA256=hash,texture.width,texture.height,format=texture.format.ToString(),mips=texture.mipmapCount,filter=texture.filterMode.ToString(),aniso=texture.anisoLevel,sRGB=importer.sRGBTexture,readable=importer.isReadable,mipmaps=importer.mipmapEnabled,wrap=texture.wrapMode.ToString(),runtimeMemorySizeBytes=UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(texture),runtimeMemorySizeScope="Unity Profiler object memory, not a direct GPU allocation counter",platforms };
