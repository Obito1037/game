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
  }
  [Serializable] sealed class MaterialStudyRecord
  {
   public string purpose="Fixed scene material A/B/repeat study. Staged bind pose and frozen time; not normal gameplay or performance evidence.";
   public string materialFamily,textureName,textureFormat;public int width,height,textureWidth,textureHeight;
   public float frozenTime,night,textureScale;public bool allInvariantsPassed;
   public string[] materialNames;public FaceStudyLight[] lights;public MaterialStudyView[] views;
  }
  IEnumerator WorldMaterialStudy(string output,bool foliageStudy,bool silhouetteStudy=false)
  {
   // Execute before the first animation update, and preserve the user's journey.
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   Directory.CreateDirectory(output);
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   try{
    StartJourney(false);Logic.SetLamp(0,0,true,true);Logic.Advance();
    Logic.SetLamp(1,0,false,true);Logic.Advance();
    Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
    HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
    traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);
    atmosphere.Night=1;
    yield return null;yield return new WaitForEndOfFrame();
    atmosphere.enabled=false;Time.timeScale=0;
    var texture=Resources.Load<Texture2D>("Textures/StoneV10");
    if(!foliageStudy&&texture==null)throw new InvalidDataException("StoneV10 texture missing");
    var affected=new HashSet<Material>();
    foreach(var renderer in island.GetComponentsInChildren<Renderer>())foreach(var material in renderer.sharedMaterials){
     if(material==null)continue;
     if(foliageStudy?material.shader.name=="BorrowedLight/FoliagePaint":material.name.StartsWith("BI_rock_hero_"))affected.Add(material);
    }
    if(affected.Count==0)throw new InvalidDataException("Study matched no materials");
    var variants=silhouetteStudy?new[]{"current"}:foliageStudy?new[]{"legacy40","fixed40","fixed20","legacy40-repeat"}:new[]{"baseline","texture","baseline-repeat"};
    var record=new MaterialStudyRecord{materialFamily=silhouetteStudy?"character-silhouette":foliageStudy?"foliage":"hero-rock",width=Screen.width,height=Screen.height,
     frozenTime=Time.time,night=atmosphere.Night,textureName=texture?.name,textureFormat=texture?.format.ToString(),
     textureWidth=texture==null?0:texture.width,textureHeight=texture==null?0:texture.height,textureScale=.9f,
     materialNames=new string[affected.Count],views=new MaterialStudyView[3*variants.Length],allInvariantsPassed=true};
    int index=0;foreach(var m in affected)record.materialNames[index++]=m.name;
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
    for(int view=0;view<3;view++){
     StoryCamera.fieldOfView=silhouetteStudy?36:view==0?48:42;StoryCamera.transform.position=positions[view];StoryCamera.transform.LookAt(targets[view]);
     var cameraMatrix=StoryCamera.transform.localToWorldMatrix;
     for(int variant=0;variant<variants.Length;variant++){
      foreach(var material in affected){
       if(silhouetteStudy)continue;
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
      yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();
      ScreenCapture.CaptureScreenshot(Path.Combine(output,filename));yield return new WaitForSecondsRealtime(.5f);
      bool fixedScene=StoryCamera.transform.localToWorldMatrix==cameraMatrix;
      for(int i=0;i<transforms.Count;i++)fixedScene&=transforms[i].localToWorldMatrix==matrices[i];
      for(int i=0;i<lights.Length;i++){var l=lights[i];var old=record.lights[i];fixedScene&=l.transform.position==old.position&&l.transform.rotation==old.rotation&&l.color==old.color&&l.intensity==old.intensity&&l.range==old.range;}
      record.allInvariantsPassed&=fixedScene;
      record.views[view*variants.Length+variant]=new MaterialStudyView{image=filename,variant=variants[variant],cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,fieldOfView=StoryCamera.fieldOfView,transformsAndLightsUnchanged=fixedScene};
     }
    }
    File.WriteAllText(Path.Combine(output,"material-study.json"),JsonUtility.ToJson(record,true));
   }finally{
    if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);
    PlayerPrefs.Save();Time.timeScale=1;Application.Quit();
   }
  }
 }
}
