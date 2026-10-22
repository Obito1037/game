using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace BorrowedLight
{
 public sealed partial class WorldDirector
 {
  [Serializable] sealed class MaterialStudyView
  {
   public string image,variant;public Vector3 cameraPosition;public Quaternion cameraRotation;
   public float fieldOfView;public bool transformsAndLightsUnchanged;
   public Vector3 lookTarget;public int actualPNGWidth,actualPNGHeight;public bool materialsUnchanged;
  }
  [Serializable] sealed class MaterialStudyCondition
  {
   public string name,shader,baseMap,normalMap,detailMap;public string[] keywords;
   public Color baseColor;public float metallic,smoothness,normalScale,detailStrength,cull,foliageLegacyAux,foliageNormalUp20;
   public Vector2 baseTiling,baseOffset,detailTiling,detailOffset;
   public bool doubleSidedGI;
  }
  static MaterialStudyCondition MaterialStudySettings(Material m)
  {
   var keywords=m.shaderKeywords;Array.Sort(keywords,StringComparer.Ordinal);
   return new MaterialStudyCondition{name=m.name,shader=m.shader.name,keywords=keywords,doubleSidedGI=m.doubleSidedGI,
    baseColor=m.HasProperty("_BaseColor")?m.GetColor("_BaseColor"):Color.white,
    baseMap=m.HasProperty("_BaseMap")?m.GetTexture("_BaseMap")?.name:null,
    normalMap=m.HasProperty("_BumpMap")?m.GetTexture("_BumpMap")?.name:null,
    detailMap=m.HasProperty("_DetailAlbedoMap")?m.GetTexture("_DetailAlbedoMap")?.name:null,
    baseTiling=m.HasProperty("_BaseMap")?m.GetTextureScale("_BaseMap"):Vector2.one,
    baseOffset=m.HasProperty("_BaseMap")?m.GetTextureOffset("_BaseMap"):Vector2.zero,
    detailTiling=m.HasProperty("_DetailAlbedoMap")?m.GetTextureScale("_DetailAlbedoMap"):Vector2.one,
    detailOffset=m.HasProperty("_DetailAlbedoMap")?m.GetTextureOffset("_DetailAlbedoMap"):Vector2.zero,
    metallic=m.HasProperty("_Metallic")?m.GetFloat("_Metallic"):0,
    smoothness=m.HasProperty("_Smoothness")?m.GetFloat("_Smoothness"):0,
    normalScale=m.HasProperty("_BumpScale")?m.GetFloat("_BumpScale"):0,
    detailStrength=m.HasProperty("_DetailAlbedoMapScale")?m.GetFloat("_DetailAlbedoMapScale"):0,
    cull=m.HasProperty("_Cull")?m.GetFloat("_Cull"):0,
    foliageLegacyAux=m.HasProperty("_FoliageLegacyAux")?m.GetFloat("_FoliageLegacyAux"):0,
    foliageNormalUp20=m.HasProperty("_FoliageNormalUp20")?m.GetFloat("_FoliageNormalUp20"):0};
  }
  [Serializable] sealed class MaterialStudyRecord
  {
   public string purpose="Fixed scene material A/B/repeat study. Staged bind pose and frozen time; not normal gameplay or performance evidence.";
   public string materialFamily,textureName,textureFormat;public int width,height,textureWidth,textureHeight;
   public float frozenTime,night,textureScale;public bool allInvariantsPassed;
   public string[] materialNames;public FaceStudyLight[] lights;public MaterialStudyView[] views;
   public bool geometryStudy;public string[] targetRenderers;public MaterialStudyCondition[] materialConditions;
   public Color ambientSky,ambientEquator,ambientGround;public float ambientIntensity;public string ambientMode;
   public bool captureComplete,completed,failed;public int expectedImageCount,completedImages,capturedImageCount;public string failure;
  }
  IEnumerator WorldMaterialStudy(string output,bool foliageStudy,bool silhouetteStudy=false,bool treeStudy=false)
  {
   // Execute before the first animation update, and preserve the user's journey.
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   Directory.CreateDirectory(output);
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   float previousTimeScale=Time.timeScale;
   MaterialStudyRecord record=null;bool reachedSuccessfulEnd=false;
   try{
    StartJourney(false);Logic.SetLamp(0,0,true,true);Logic.Advance();
    Logic.SetLamp(1,0,false,true);Logic.Advance();
    Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
    HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
    traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);
    atmosphere.Night=1;
    yield return null;yield return new WaitForEndOfFrame();
    atmosphere.enabled=false;Time.timeScale=0;
    var texture=treeStudy?null:Resources.Load<Texture2D>("Textures/StoneV10");
    if(!treeStudy&&!foliageStudy&&texture==null)throw new InvalidDataException("StoneV10 texture missing");
    var affected=new HashSet<Material>();
    var treeRenderers=new List<string>();
    if(treeStudy)foreach(var r in island.GetComponentsInChildren<Renderer>())if(r.name=="Garden_TreeTrunks"||r.name=="Garden_TreeCanopies"||r.name=="Garden_CanopyLeafEdges")treeRenderers.Add(r.name);
    if(treeStudy&&treeRenderers.Count!=3)throw new InvalidDataException("Tree study requires the three original tree renderers");
    foreach(var renderer in island.GetComponentsInChildren<Renderer>())foreach(var material in renderer.sharedMaterials){
     if(material==null)continue;
     if(treeStudy?treeRenderers.Contains(renderer.name):foliageStudy?material.shader.name=="BorrowedLight/FoliagePaint":material.name.StartsWith("BI_rock_hero_"))affected.Add(material);
    }
    if(affected.Count==0)throw new InvalidDataException("Study matched no materials");
    var variants=treeStudy?new[]{"current","repeat"}:silhouetteStudy?new[]{"current"}:foliageStudy?new[]{"legacy40","fixed40","fixed20","legacy40-repeat"}:new[]{"baseline","texture","baseline-repeat"};
    record=new MaterialStudyRecord{materialFamily=treeStudy?"tree-geometry":silhouetteStudy?"character-silhouette":foliageStudy?"foliage":"hero-rock",width=Screen.width,height=Screen.height,
     frozenTime=Time.time,night=atmosphere.Night,textureName=texture?.name,textureFormat=texture?.format.ToString(),
     textureWidth=texture==null?0:texture.width,textureHeight=texture==null?0:texture.height,textureScale=treeStudy?0:.9f,
     materialNames=new string[affected.Count],views=new MaterialStudyView[(treeStudy?5:3)*variants.Length],allInvariantsPassed=false,
     geometryStudy=treeStudy,targetRenderers=treeRenderers.ToArray(),ambientSky=RenderSettings.ambientSkyColor,ambientEquator=RenderSettings.ambientEquatorColor,
     ambientGround=RenderSettings.ambientGroundColor,ambientIntensity=RenderSettings.ambientIntensity,ambientMode=RenderSettings.ambientMode.ToString()};
    if(treeStudy)record.purpose="Tree geometry fixed-camera current/repeat study at five views. Original materials/keywords, ground detail .35, character and lights retained; frozen bind pose/time. NOT normal gameplay, animation acceptance or FPS evidence; temporal AO may differ.";
    int index=0;foreach(var m in affected)record.materialNames[index++]=m.name;
    var allMaterials=new HashSet<Material>();
    foreach(var r in island.GetComponentsInChildren<Renderer>())foreach(var m in r.sharedMaterials)if(m!=null)allMaterials.Add(m);
    foreach(var r in traveler.GetComponentsInChildren<Renderer>())foreach(var m in r.sharedMaterials)if(m!=null)allMaterials.Add(m);
    var materialList=new List<Material>(allMaterials);materialList.Sort((a,b)=>StringComparer.Ordinal.Compare(a.name,b.name));
    record.materialConditions=new MaterialStudyCondition[materialList.Count];var initialMaterials=new string[materialList.Count];
    for(int i=0;i<materialList.Count;i++){record.materialConditions[i]=MaterialStudySettings(materialList[i]);initialMaterials[i]=JsonUtility.ToJson(record.materialConditions[i]);}
    record.expectedImageCount=record.views.Length;bool allChecksPassed=true;
    var transforms=new List<Transform>(island.GetComponentsInChildren<Transform>());
    transforms.AddRange(traveler.GetComponentsInChildren<Transform>());
    var matrices=new Matrix4x4[transforms.Count];
    for(int i=0;i<transforms.Count;i++)matrices[i]=transforms[i].localToWorldMatrix;
    var lights=FindObjectsByType<Light>(FindObjectsSortMode.None);record.lights=new FaceStudyLight[lights.Length];
    for(int i=0;i<lights.Length;i++){var l=lights[i];record.lights[i]=new FaceStudyLight{name=l.name,type=l.type.ToString(),position=l.transform.position,rotation=l.transform.rotation,color=l.color,intensity=l.intensity,range=l.range};}
    var positions=foliageStudy?new[]{new Vector3(0,1.9f,-8.1f),new Vector3(1.55f,.65f,-4.4f),new Vector3(-3.35f,.65f,-3.2f)}
     :new[]{new Vector3(0,1.9f,-8.1f),new Vector3(-1.85f,.74f,-6.45f),new Vector3(2.15f,.72f,-5.45f)};
    var targets=foliageStudy?new[]{new Vector3(0,.7f,-3.3f),new Vector3(1,.04f,-3.1f),new Vector3(-4.2f,.04f,-2.25f)}
     :new[]{new Vector3(0,.7f,-3.3f),new Vector3(-1.2f,.25f,-5.15f),new Vector3(1.2f,.25f,-4.2f)};
    var names=foliageStudy?new[]{"path","roots","lamp"}:new[]{"path","left-rock","right-rock"};
    if(silhouetteStudy){
     positions=new[]{new Vector3(0,.95f,.3f),new Vector3(2.06f,.95f,-.35f),new Vector3(3.6f,.95f,-3.3f)};
     targets=new[]{new Vector3(0,.8f,-3.3f),new Vector3(0,.8f,-3.3f),new Vector3(0,.8f,-3.3f)};
     names=new[]{"front","three-quarter","profile"};
    }
    if(treeStudy){
     positions=new[]{new Vector3(0,1.9f,-8.1f),new Vector3(21,17,-26),new Vector3(-10.6f,2.8f,-2.6f),new Vector3(-1.2f,3,.4f),new Vector3(9.8f,3,-4.6f)};
     targets=new[]{new Vector3(0,.7f,-3.3f),new Vector3(-2,.4f,0),new Vector3(-6.4f,1.9f,3.9f),new Vector3(3,1.4f,5.7f),new Vector3(5.1f,2.1f,3)};
     names=new[]{"path","island","left-tree","gold-tree","right-pine"};
    }
    var treeFieldsOfView=new[]{48f,36f,38f,38f,34f};
    for(int view=0;view<positions.Length;view++){
     StoryCamera.fieldOfView=treeStudy?treeFieldsOfView[view]:silhouetteStudy?36:view==0?48:42;StoryCamera.transform.position=positions[view];StoryCamera.transform.LookAt(targets[view]);
     var cameraMatrix=StoryCamera.transform.localToWorldMatrix;
     for(int variant=0;variant<variants.Length;variant++){
      foreach(var material in affected){
       if(silhouetteStudy||treeStudy)continue;
       if(foliageStudy){
        material.SetFloat("_FoliageLegacyAux",variant==0||variant==3?1:0);
        material.SetFloat("_FoliageNormalUp20",variant==2?1:0);
        if(variant==0||variant==3)material.EnableKeyword("_FOLIAGE_LEGACY_AUX");else material.DisableKeyword("_FOLIAGE_LEGACY_AUX");
        if(variant==2)material.EnableKeyword("_FOLIAGE_NORMAL_UP_20");else material.DisableKeyword("_FOLIAGE_NORMAL_UP_20");
       }else{
        material.SetTexture("_BaseMap",texture);material.SetTextureScale("_BaseMap",new Vector2(.9f,.9f));material.SetFloat("_BumpScale",1);
        if(variant==1)material.EnableKeyword("_ROCK_TEXTURE");else material.DisableKeyword("_ROCK_TEXTURE");
       }
      }
      string filename=names[view]+"-"+variants[variant]+".png";
      string imagePath=Path.Combine(output,filename);if(File.Exists(imagePath))File.Delete(imagePath);
      yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();
      ScreenCapture.CaptureScreenshot(imagePath);
      int actualWidth=0,actualHeight=0;float deadline=Time.realtimeSinceStartup+5;
      while(!GroundPNGSize(imagePath,out actualWidth,out actualHeight)&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(.1f);
      if(actualWidth==0||actualHeight==0)throw new IOException("Complete PNG was not written: "+filename);
      bool fixedScene=StoryCamera.transform.localToWorldMatrix==cameraMatrix;
      for(int i=0;i<transforms.Count;i++)fixedScene&=transforms[i].localToWorldMatrix==matrices[i];
      for(int i=0;i<lights.Length;i++){var l=lights[i];var old=record.lights[i];fixedScene&=l.transform.position==old.position&&l.transform.rotation==old.rotation&&l.color==old.color&&l.intensity==old.intensity&&l.range==old.range;}
      bool materialsUnchanged=true;for(int i=0;i<materialList.Count;i++)materialsUnchanged&=JsonUtility.ToJson(MaterialStudySettings(materialList[i]))==initialMaterials[i];
      if(treeStudy)fixedScene&=Time.time==record.frozenTime&&RenderSettings.ambientSkyColor==record.ambientSky&&RenderSettings.ambientEquatorColor==record.ambientEquator&&RenderSettings.ambientGroundColor==record.ambientGround&&RenderSettings.ambientIntensity==record.ambientIntensity&&RenderSettings.ambientMode.ToString()==record.ambientMode;
      allChecksPassed&=fixedScene&&actualWidth==record.width&&actualHeight==record.height&&(!treeStudy||materialsUnchanged);
      record.views[view*variants.Length+variant]=new MaterialStudyView{image=filename,variant=variants[variant],cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,fieldOfView=StoryCamera.fieldOfView,lookTarget=targets[view],actualPNGWidth=actualWidth,actualPNGHeight=actualHeight,materialsUnchanged=materialsUnchanged,transformsAndLightsUnchanged=fixedScene};
      record.completedImages++;record.capturedImageCount=record.completedImages;record.captureComplete=record.completedImages==record.expectedImageCount;
      record.allInvariantsPassed=allChecksPassed&&record.captureComplete;
      File.WriteAllText(Path.Combine(output,"material-study.json"),JsonUtility.ToJson(record,true));
     }
    }
    record.completed=record.captureComplete&&record.allInvariantsPassed;
    File.WriteAllText(Path.Combine(output,"material-study.json"),JsonUtility.ToJson(record,true));
    reachedSuccessfulEnd=record.completed;
   }finally{
    bool treeFailure=treeStudy&&(!reachedSuccessfulEnd||record==null||!record.completed);
    if(treeStudy){
     if(record==null)record=new MaterialStudyRecord{materialFamily="tree-geometry",geometryStudy=true,expectedImageCount=10,width=Screen.width,height=Screen.height};
     record.completed=!treeFailure;record.failed=treeFailure;
     if(treeFailure){record.allInvariantsPassed=false;record.failure="Tree geometry study did not finish all expected complete PNGs and unchanged-scene checks; see player.log.";}
     try{File.WriteAllText(Path.Combine(output,"material-study.json"),JsonUtility.ToJson(record,true));}
     catch(Exception error){treeFailure=true;Debug.LogError("TREE_STUDY_RECORD_FAILED: "+error);}
    }
    try{
     if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);
     PlayerPrefs.Save();
    }catch(Exception error){
     if(!treeStudy)throw;
     treeFailure=true;record.completed=false;record.failed=true;record.allInvariantsPassed=false;record.failure="PlayerPrefs restoration failed: "+error.Message;
     Debug.LogError("TREE_STUDY_SAVE_RESTORE_FAILED: "+error);
     try{File.WriteAllText(Path.Combine(output,"material-study.json"),JsonUtility.ToJson(record,true));}catch(Exception writeError){Debug.LogError("TREE_STUDY_RECORD_FAILED: "+writeError);}
    }finally{Time.timeScale=previousTimeScale;if(treeStudy)Application.Quit(treeFailure?1:0);else Application.Quit();}
   }
  }
 }
}
