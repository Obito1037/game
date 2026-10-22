using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace BorrowedLight
{
 public sealed partial class WorldDirector
 {
  [Serializable] sealed class EyeSurfaceSample
  {
   public string image,view,variant;public int width,height;
   public float contact,iris,fieldOfView;public Vector3 cameraPosition;public Quaternion cameraRotation;
   public bool pngComplete,transformsMatch,lightsMatch,materialsMatch,assignmentsMatch,cameraMatch;
  }
  [Serializable] sealed class EyeSurfaceRecord
  {
   public string purpose="Fixed v11 geometry eye-colour study. Original Lit, neutral custom Lit, contact-only, iris-only, combined and baseline-repeat; staged pose, not normal gameplay or FPS.";
   public bool completed,failed,allInvariantsPassed,saveRestored;public string stage,failure;
   public int width,height,expectedImages=18,capturedImages;public string[] targets,variants;
   public FaceLightCondition[] lights;public MaterialStudyCondition[] originalEyeMaterials;
   public EyeSurfaceSample[] samples=new EyeSurfaceSample[18];
  }
  IEnumerator EyeSurfaceStudy(string output)
  {
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string saved=PlayerPrefs.GetString(saveKey);float oldTimeScale=Time.timeScale;
   bool success=false;var record=new EyeSurfaceRecord{width=Screen.width,height=Screen.height,stage="setup"};
   var targets=new List<Renderer>();var originals=new List<Material[]>();var candidates=new List<Material>();
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   try{
    Directory.CreateDirectory(output);
    StartJourney(false);Logic.SetLamp(0,0,true,true);Logic.Advance();Logic.SetLamp(1,0,false,true);Logic.Advance();
    Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
    HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
    traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);atmosphere.Night=1;
    foreach(var label in new[]{"Blink_L","Blink_R"}){var pivot=Find(traveler.transform,label);if(pivot==null)throw new InvalidDataException("Blink pivot missing");pivot.localScale=new Vector3(.001f,.001f,1);}
    yield return null;yield return new WaitForEndOfFrame();atmosphere.enabled=false;Time.timeScale=0;
    var template=Resources.Load<Material>("Materials/EyeSurface");
    if(template==null||!template.shader.isSupported)throw new InvalidDataException("EyeSurface material/shader unavailable");
    var targetNames=new[]{"Head_Eye_Ivory","Head_Eye_AmberRim","Head_Eye_Chestnut"};
    record.targets=targetNames;record.originalEyeMaterials=new MaterialStudyCondition[3];
    for(int i=0;i<targetNames.Length;i++){
     var t=Find(traveler.transform,targetNames[i]);var r=t==null?null:t.GetComponent<Renderer>();
     if(r==null||r.sharedMaterials.Length!=1)throw new InvalidDataException("Eye renderer contract changed: "+targetNames[i]);
     targets.Add(r);originals.Add(r.sharedMaterials);record.originalEyeMaterials[i]=MaterialStudySettings(r.sharedMaterial);
     var m=new Material(r.sharedMaterial);m.shader=template.shader;m.name=r.sharedMaterial.name+" / eye surface study";m.SetFloat("_EyePart",i);m.SetFloat("_EyeContact",0);m.SetFloat("_EyeIris",0);candidates.Add(m);
    }
    var transforms=new List<Transform>();foreach(var t in FindObjectsByType<Transform>(FindObjectsInactive.Include,FindObjectsSortMode.None))
     if(t!=StoryCamera.transform&&!t.IsChildOf(StoryCamera.transform))transforms.Add(t);
    var matrices=new Matrix4x4[transforms.Count];for(int i=0;i<matrices.Length;i++)matrices[i]=transforms[i].localToWorldMatrix;
    var lights=FindObjectsByType<Light>(FindObjectsInactive.Include,FindObjectsSortMode.None);record.lights=new FaceLightCondition[lights.Length];
    var lightJSON=new string[lights.Length];for(int i=0;i<lights.Length;i++){record.lights[i]=FaceLightSettings(lights[i]);lightJSON[i]=JsonUtility.ToJson(record.lights[i]);}
    var renderers=FindObjectsByType<Renderer>(FindObjectsInactive.Include,FindObjectsSortMode.None);
    var assignments=new Material[renderers.Length][];var originalMaterials=new HashSet<Material>();
    for(int i=0;i<renderers.Length;i++){assignments[i]=renderers[i].sharedMaterials;foreach(var m in assignments[i])if(m!=null)originalMaterials.Add(m);}
    if(RenderSettings.skybox!=null)originalMaterials.Add(RenderSettings.skybox);
    var materialJSON=new Dictionary<Material,string>();foreach(var m in originalMaterials)materialJSON[m]=JsonUtility.ToJson(FaceLightMaterialSettings(m));
    var variants=new[]{"baseline","neutral-shader","contact-only","iris-only","combined","baseline-repeat"};record.variants=variants;
    var views=new[]{"front","three-quarter","gameplay-distance"};var angles=new[]{180f,145f,155f};
    bool allPassed=true;float frozenTime=Time.time;
    for(int view=0;view<views.Length;view++){
     var target=new Vector3(0,view==2?.83f:1.27f,-3.3f);
     var offset=Quaternion.Euler(0,angles[view],0)*new Vector3(0,view==2?.25f:0,view==2?-2.65f:-1.1f);
     StoryCamera.fieldOfView=view==2?40:30;StoryCamera.transform.position=target+offset;StoryCamera.transform.LookAt(target);
     var cameraMatrix=StoryCamera.transform.localToWorldMatrix;float fov=StoryCamera.fieldOfView;
     for(int variant=0;variant<variants.Length;variant++){
      bool useCandidate=variant>0&&variant<5;float contact=variant==2||variant==4?1:0,iris=variant==3||variant==4?1:0;
      for(int i=0;i<targets.Count;i++){candidates[i].SetFloat("_EyeContact",contact);candidates[i].SetFloat("_EyeIris",iris);targets[i].sharedMaterials=useCandidate?new[]{candidates[i]}:originals[i];}
      record.stage=views[view]+"-"+variants[variant];string filename=record.stage+".png",imagePath=Path.Combine(output,filename);
      if(File.Exists(imagePath))File.Delete(imagePath);
      yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();ScreenCapture.CaptureScreenshot(imagePath);
      int width=0,height=0;float deadline=Time.realtimeSinceStartup+5;
      while(!GroundPNGSize(imagePath,out width,out height)&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(.1f);
      if(width<=0||height<=0)throw new IOException("Complete PNG missing: "+filename);
      bool sameTransforms=Time.time==frozenTime&&Time.timeScale==0;
      for(int i=0;i<transforms.Count;i++)sameTransforms&=transforms[i]!=null&&transforms[i].localToWorldMatrix==matrices[i];
      bool sameLights=lights.Length==FindObjectsByType<Light>(FindObjectsInactive.Include,FindObjectsSortMode.None).Length;
      for(int i=0;i<lights.Length;i++)sameLights&=lights[i]!=null&&JsonUtility.ToJson(FaceLightSettings(lights[i]))==lightJSON[i];
      bool sameMaterials=true;foreach(var pair in materialJSON)sameMaterials&=pair.Key!=null&&JsonUtility.ToJson(FaceLightMaterialSettings(pair.Key))==pair.Value;
      bool sameAssignments=renderers.Length==FindObjectsByType<Renderer>(FindObjectsInactive.Include,FindObjectsSortMode.None).Length;
      for(int i=0;i<renderers.Length;i++){
       if(renderers[i]==null){sameAssignments=false;continue;}
       int targetIndex=targets.IndexOf(renderers[i]);var expected=targetIndex>=0&&useCandidate?new[]{candidates[targetIndex]}:assignments[i];
       var actual=renderers[i].sharedMaterials;sameAssignments&=actual.Length==expected.Length;
       for(int j=0;j<Math.Min(actual.Length,expected.Length);j++)sameAssignments&=actual[j]==expected[j];
      }
      bool cameraMatch=StoryCamera.transform.localToWorldMatrix==cameraMatrix&&StoryCamera.fieldOfView==fov;
      var sample=new EyeSurfaceSample{image=filename,view=views[view],variant=variants[variant],width=width,height=height,contact=contact,iris=iris,fieldOfView=fov,
       cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,pngComplete=true,transformsMatch=sameTransforms,lightsMatch=sameLights,materialsMatch=sameMaterials,assignmentsMatch=sameAssignments,cameraMatch=cameraMatch};
      record.samples[record.capturedImages++]=sample;
      allPassed&=width==record.width&&height==record.height&&sameTransforms&&sameLights&&sameMaterials&&sameAssignments&&cameraMatch;
      File.WriteAllText(Path.Combine(output,"eye-surface-study.json"),JsonUtility.ToJson(record,true));
     }
    }
    record.allInvariantsPassed=allPassed&&record.capturedImages==record.expectedImages;success=record.allInvariantsPassed;
   }finally{
    for(int i=0;i<targets.Count;i++)if(targets[i]!=null)targets[i].sharedMaterials=originals[i];
    foreach(var m in candidates)if(m!=null)Destroy(m);
    if(hadSave)PlayerPrefs.SetString(saveKey,saved);else PlayerPrefs.DeleteKey(saveKey);PlayerPrefs.Save();
    record.saveRestored=PlayerPrefs.HasKey(saveKey)==hadSave&&(!hadSave||PlayerPrefs.GetString(saveKey)==saved);
    Time.timeScale=oldTimeScale;success&=record.saveRestored;record.completed=success;record.failed=!success;
    if(!success)record.failure="Incomplete study or capture invariant failed at "+record.stage;
    File.WriteAllText(Path.Combine(output,"eye-surface-study.json"),JsonUtility.ToJson(record,true));Application.Quit(success?0:1);
   }
  }
 }
}

