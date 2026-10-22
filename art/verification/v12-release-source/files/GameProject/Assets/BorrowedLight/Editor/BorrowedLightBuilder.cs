using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace BorrowedLight.EditorTools
{
 public static class BorrowedLightBuilder
 {
  const string ScenePath="Assets/BorrowedLight/Scenes/BorrowedLight.unity";
  [MenuItem("Borrowed Light/Build Story Scene")]
  public static void CreateScene()
  {
   Directory.CreateDirectory("Assets/BorrowedLight/Scenes");
   AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
   Directory.CreateDirectory("Assets/BorrowedLight/Resources/Materials");
   foreach(var pair in new[]{new[]{"CelestialSky","BorrowedLight/CelestialSky"},new[]{"Starfield","BorrowedLight/Starfield"},new[]{"LightVeil","BorrowedLight/LightVeil"},new[]{"Firefly","BorrowedLight/Firefly"},new[]{"CloudVeil","BorrowedLight/CloudVeil"},new[]{"MoonPaint","BorrowedLight/MoonPaint"},new[]{"PaintedSurface","BorrowedLight/PaintedSurface"},new[]{"PaintedTinted","BorrowedLight/PaintedSurface"},new[]{"FoliagePaint","BorrowedLight/FoliagePaint"},new[]{"FoliageTinted","BorrowedLight/FoliagePaint"}}){var path="Assets/BorrowedLight/Resources/Materials/"+pair[0]+".mat";if(AssetDatabase.LoadAssetAtPath<Material>(path)==null){var shader=Shader.Find(pair[1]);if(shader==null)throw new Exception("Required shader missing: "+pair[1]);AssetDatabase.CreateAsset(new Material(shader),path);}}
   var paintedTint=AssetDatabase.LoadAssetAtPath<Material>("Assets/BorrowedLight/Resources/Materials/PaintedTinted.mat");paintedTint.EnableKeyword("_PAINT_VERTEX_COLOR");EditorUtility.SetDirty(paintedTint);
   var foliageTint=AssetDatabase.LoadAssetAtPath<Material>("Assets/BorrowedLight/Resources/Materials/FoliageTinted.mat");foliageTint.EnableKeyword("_FOLIAGE_VERTEX_COLOR");EditorUtility.SetDirty(foliageTint);
   foreach(var name in new[]{"Meadow","MeadowNormal","Nebula"}){var textureImporter=AssetImporter.GetAtPath("Assets/BorrowedLight/Resources/Textures/"+name+".png") as TextureImporter;if(textureImporter==null)continue;bool normal=name=="MeadowNormal";var type=normal?TextureImporterType.NormalMap:TextureImporterType.Default;if(textureImporter.textureType!=type||textureImporter.maxTextureSize!=2048){textureImporter.textureType=type;textureImporter.maxTextureSize=2048;textureImporter.anisoLevel=4;textureImporter.filterMode=FilterMode.Trilinear;textureImporter.SaveAndReimport();}}
   var mattePath="Assets/BorrowedLight/Resources/Materials/FoliageMatte.mat";var matte=AssetDatabase.LoadAssetAtPath<Material>(mattePath);if(matte==null){matte=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(matte,mattePath);}matte.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");matte.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");matte.SetFloat("_Smoothness",0);matte.SetFloat("_SpecularHighlights",0);matte.SetFloat("_EnvironmentReflections",0);EditorUtility.SetDirty(matte);
   foreach(var path in AssetDatabase.FindAssets("t:Model",new[]{"Assets/BorrowedLight"}).Select(AssetDatabase.GUIDToAssetPath)) {
    var importer=AssetImporter.GetAtPath(path) as ModelImporter;
    if(importer!=null && !importer.isReadable) { importer.isReadable=true; importer.SaveAndReimport(); }
   }
   var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
   var root=new GameObject("Borrowed Light — Story World");root.AddComponent<WorldDirector>();
   EditorSceneManager.SaveScene(scene,ScenePath);
   EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
   PlayerSettings.companyName="Borrowed Light Studio";PlayerSettings.productName="借光岛 · Borrowed Light";
   PlayerSettings.defaultScreenWidth=1440;PlayerSettings.defaultScreenHeight=900;
   PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.resizableWindow=true;
   PlayerSettings.runInBackground=true;PlayerSettings.colorSpace=ColorSpace.Linear;
   var pipeline=GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
   if(pipeline!=null){pipeline.msaaSampleCount=2;EditorUtility.SetDirty(pipeline);}
   PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
   PlayerSettings.SetApiCompatibilityLevel(NamedBuildTarget.Standalone,ApiCompatibilityLevel.NET_Standard);
   AssetDatabase.SaveAssets();
   Debug.Log("BORROWED_LIGHT_SCENE_READY: "+ScenePath);
  }
  [MenuItem("Borrowed Light/Build Windows Game")]
  public static void BuildWindows()
  {
   CreateScene();Directory.CreateDirectory("../builds/windows");
   var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName="../builds/windows/BorrowedLight.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
   Debug.Log("BORROWED_LIGHT_BUILD: "+report.summary.result+" bytes="+report.summary.totalSize);
   if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("Windows build failed");
  }
  [MenuItem("Borrowed Light/Build Web Game")]
  public static void BuildWeb()
  {
   CreateScene();Directory.CreateDirectory("../builds/web");
   ConfigureWeb();
   var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName="../builds/web",target=BuildTarget.WebGL,options=BuildOptions.None});
   Debug.Log("BORROWED_LIGHT_WEB_BUILD: "+report.summary.result);
   if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("Web build failed");
  }
  public static void ConfigureWeb()
  {
   PlayerSettings.WebGL.template="PROJECT:BorrowedLight";
   PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Gzip;
   PlayerSettings.WebGL.decompressionFallback=false;PlayerSettings.WebGL.dataCaching=true;
   PlayerSettings.WebGL.nameFilesAsHashes=true;
   PlayerSettings.WebGL.initialMemorySize=256;PlayerSettings.WebGL.maximumMemorySize=1024;
   PlayerSettings.WebGL.memoryGrowthMode=WebGLMemoryGrowthMode.Geometric;
   PlayerSettings.SetGraphicsAPIs(BuildTarget.WebGL,new[]{GraphicsDeviceType.OpenGLES3});
  }
 }
}
