using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace BorrowedLight
{
 public sealed partial class WorldDirector
 {
  [Serializable] sealed class BoulderApproach
  {
   public int rock;public Vector3 start,direction,end;
   public float movedMetres;public string firstCollider;public bool startsClear,blockedBeforeCentre;
  }
  [Serializable] sealed class BoulderApproachReport
  {
   public string scope="Sixteen cardinal capsule approaches to the four authored boulders; geometric probes, not a walking animation test";
   public BoulderApproach[] probes;public bool allPassed;
   public string[] heroMaterialNames;public float[] heroSurfaceKinds;
  }
  void WriteHeroBoulderChecks(string output)
  {
   var centres=new[]{new Vector3(-1.2f,0,-5.15f),new Vector3(1.2f,0,-4.2f),new Vector3(2,0,-2.7f),new Vector3(-2.3f,0,-2.2f)};
   var directions=new[]{Vector3.right,Vector3.left,Vector3.forward,Vector3.back};
   var report=new BoulderApproachReport{probes=new BoulderApproach[16],allPassed=true};int n=0;
   var hero=Find(island.transform,"Garden_HeroBoulders").GetComponent<Renderer>().sharedMaterials;
   report.heroMaterialNames=new string[hero.Length];report.heroSurfaceKinds=new float[hero.Length];
   for(int i=0;i<hero.Length;i++){report.heroMaterialNames[i]=hero[i].name;report.heroSurfaceKinds[i]=hero[i].GetFloat("_SurfaceKind");}
   for(int rock=0;rock<centres.Length;rock++)foreach(var away in directions){
    var start=centres[rock]+away;
    if(Physics.Raycast(start+Vector3.up*2,Vector3.down,out var ground,3,1<<8))start.y=ground.point.y+.03f;
    var lower=start+Vector3.up*.28f;var upper=start+Vector3.up*1.03f;
    bool clear=!Physics.CheckCapsule(lower,upper,.22f,1<<9,QueryTriggerInteraction.Ignore);
    bool hit=Physics.CapsuleCast(lower,upper,.22f,-away,out var contact,1,1<<9,QueryTriggerInteraction.Ignore);
    var end=traveler.ResolveMotion(start,-away);float moved=Vector3.Dot(end-start,-away);
    bool blocked=clear&&hit&&contact.collider.name.Contains("HeroBoulders")&&moved>.02f&&moved<.9f;
    report.probes[n++]=new BoulderApproach{rock=rock,start=start,direction=-away,end=end,movedMetres=moved,
     firstCollider=hit?contact.collider.name:"none",startsClear=clear,blockedBeforeCentre=blocked};
    report.allPassed&=blocked;
   }
   File.WriteAllText(Path.Combine(output,"boulder-approaches.json"),JsonUtility.ToJson(report,true));
  }
  [Serializable] sealed class PortraitLightRecord
  {
   public string purpose="Controlled light comparison; staged pose, not gameplay or performance evidence";
   public string[] images={"01-fill-023.png","02-fill-016.png","03-fill-023-repeat.png"};
   public float[] intensities={.23f,.16f,.23f};
   public int width,height;public Vector3 cameraPosition,travelerPosition,fillLocalPosition;
   public Quaternion cameraRotation,travelerRotation;public float fieldOfView,fillRange,frozenTime;
   public Color fillColor;public bool cameraAndPoseUnchanged;
  }
  IEnumerator PortraitLightComparison(string output)
  {
   Directory.CreateDirectory(output);
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   yield return new WaitForSeconds(2);
   StartJourney(false);
   Logic.SetLamp(0,0,true,true);Logic.Advance();
   Logic.SetLamp(1,0,false,true);Logic.Advance();
   Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
   HUD.ReturnToIsland?.Invoke();
   traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);
   yaw=155;pitch=9;distance=2.65f;
   yield return new WaitForSeconds(6);
   var fill=Find(traveler.transform,"A soft reflection on the traveler").GetComponent<Light>();
   var record=new PortraitLightRecord{width=Screen.width,height=Screen.height,
    cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,
    fieldOfView=StoryCamera.fieldOfView,travelerPosition=traveler.transform.position,
    travelerRotation=traveler.transform.rotation,fillLocalPosition=fill.transform.localPosition,
    fillRange=fill.range,fillColor=fill.color,frozenTime=Time.time,cameraAndPoseUnchanged=true};
   // Freeze the settled camera and authored animation only for this explicit
   // command-line diagnostic. Ordinary play never enters this coroutine.
   traveler.enabled=false;atmosphere.enabled=false;enabled=false;HUD.enabled=false;Time.timeScale=0;
   var transforms=traveler.GetComponentsInChildren<Transform>(true);
   var matrices=new Matrix4x4[transforms.Length];
   for(int i=0;i<transforms.Length;i++)matrices[i]=transforms[i].localToWorldMatrix;
   for(int sample=0;sample<record.images.Length;sample++){
    fill.intensity=record.intensities[sample];
    yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();
    ScreenCapture.CaptureScreenshot(Path.Combine(output,record.images[sample]));
    yield return new WaitForSecondsRealtime(.5f);
    record.cameraAndPoseUnchanged&=StoryCamera.transform.position==record.cameraPosition
     &&StoryCamera.transform.rotation==record.cameraRotation&&StoryCamera.fieldOfView==record.fieldOfView;
    for(int i=0;i<transforms.Length;i++)record.cameraAndPoseUnchanged&=transforms[i].localToWorldMatrix==matrices[i];
   }
   File.WriteAllText(Path.Combine(output,"comparison.json"),JsonUtility.ToJson(record,true));
   if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);PlayerPrefs.Save();
   Time.timeScale=1;Application.Quit();
  }
  [Serializable] sealed class FaceStudyView
  {
   public string image;public Vector3 cameraPosition;public Quaternion cameraRotation;
   public float fieldOfView;public bool eyesClosed,bodyPoseUnchanged;
  }
  [Serializable] sealed class FaceStudyLight
  {
   public string name,type;public Vector3 position;public Quaternion rotation;
   public Color color;public float intensity,range;
  }
  [Serializable] sealed class FaceStudyMaterial
  {
   public string name,shader;public Color baseColor;public float smoothness,surfaceKind;
  }
  [Serializable] sealed class FaceStudyRecord
  {
   public string purpose="Controlled bind-pose face geometry/material study in the game's night lighting; not gameplay or performance evidence";
   public int width,height;public Vector3 travelerPosition,lookTarget;
   public Quaternion travelerRotation;public float frozenTime,night,fillIntensity;
   public FaceStudyView[] views;public FaceStudyLight[] lights;public FaceStudyMaterial[] materials;
   public bool allBodyPosesUnchanged;
  }
  IEnumerator FaceGeometryStudy(string output,bool eyeSurfaceTest=false)
  {
   // Called synchronously from Awake: preserve the imported bind pose before
   // the motor can apply idle, breathing, leg grounding or blink animation.
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   Directory.CreateDirectory(output);
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   StartJourney(false);
   Logic.SetLamp(0,0,true,true);Logic.Advance();
   Logic.SetLamp(1,0,false,true);Logic.Advance();
   Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
   HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
   traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);
   atmosphere.Night=1;
   var left=Find(traveler.transform,"Blink_L");var right=Find(traveler.transform,"Blink_R");
   var openScale=new Vector3(.001f,.001f,1);
   if(left!=null)left.localScale=openScale;if(right!=null)right.localScale=openScale;
   var fill=Find(traveler.transform,"A soft reflection on the traveler").GetComponent<Light>();
   fill.intensity=.23f;
   if(eyeSurfaceTest)foreach(var renderer in traveler.GetComponentsInChildren<Renderer>())foreach(var m in renderer.sharedMaterials){
    if(m.name.StartsWith("Traveler_Eye_Ivory"))m.SetFloat("_Smoothness",.18f);
    else if(m.name.StartsWith("Traveler_Eye_AmberRim")||m.name.StartsWith("Traveler_Eye_Chestnut"))m.SetFloat("_Smoothness",.32f);
    else if(m.name.StartsWith("Traveler_Eye_Pupil"))m.SetFloat("_Smoothness",.50f);
   }
   // Let the actual atmosphere update its night-light intensity before freezing.
   yield return null;yield return new WaitForEndOfFrame();
   atmosphere.enabled=false;Time.timeScale=0;
   var record=new FaceStudyRecord{width=Screen.width,height=Screen.height,
    travelerPosition=traveler.transform.position,travelerRotation=traveler.transform.rotation,
    lookTarget=new Vector3(0,1.27f,-3.3f),night=atmosphere.Night,fillIntensity=fill.intensity,
    frozenTime=Time.time,allBodyPosesUnchanged=true,views=new FaceStudyView[5]};
   var lights=FindObjectsByType<Light>(FindObjectsSortMode.None);record.lights=new FaceStudyLight[lights.Length];
   for(int i=0;i<lights.Length;i++){var l=lights[i];record.lights[i]=new FaceStudyLight{name=l.name,type=l.type.ToString(),position=l.transform.position,rotation=l.transform.rotation,color=l.color,intensity=l.intensity,range=l.range};}
   var usedMaterials=new System.Collections.Generic.Dictionary<string,Material>();
   foreach(var renderer in traveler.GetComponentsInChildren<Renderer>())foreach(var m in renderer.sharedMaterials)if(m!=null)usedMaterials[m.name]=m;
   record.materials=new FaceStudyMaterial[usedMaterials.Count];int materialIndex=0;
   foreach(var item in usedMaterials){var m=item.Value;record.materials[materialIndex++]=new FaceStudyMaterial{name=m.name,shader=m.shader.name,baseColor=m.HasProperty("_BaseColor")?m.GetColor("_BaseColor"):Color.white,smoothness=m.HasProperty("_Smoothness")?m.GetFloat("_Smoothness"):-1,surfaceKind=m.HasProperty("_SurfaceKind")?m.GetFloat("_SurfaceKind"):-1};}
   var transforms=traveler.GetComponentsInChildren<Transform>(true);var matrices=new Matrix4x4[transforms.Length];
   for(int i=0;i<transforms.Length;i++)matrices[i]=transforms[i].localToWorldMatrix;
   var angles=new[]{180f,145f,95f,180f,180f};
   var images=new[]{"01-front-open.png","02-three-quarter-open.png","03-side-open.png","04-front-closed.png","05-front-open-repeat.png"};
   StoryCamera.fieldOfView=30;
   for(int sample=0;sample<angles.Length;sample++){
    bool closed=sample==3;if(left!=null)left.localScale=closed?Vector3.one:openScale;if(right!=null)right.localScale=closed?Vector3.one:openScale;
    var offset=Quaternion.Euler(0,angles[sample],0)*new Vector3(0,0,-1.1f);
    StoryCamera.transform.position=record.lookTarget+offset;StoryCamera.transform.LookAt(record.lookTarget);
    yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();
    ScreenCapture.CaptureScreenshot(Path.Combine(output,images[sample]));
    yield return new WaitForSecondsRealtime(.5f);
    bool unchanged=true;
    for(int i=0;i<transforms.Length;i++){
     var t=transforms[i];bool blink=(left!=null&&(t==left||t.IsChildOf(left)))||(right!=null&&(t==right||t.IsChildOf(right)));
     if(!blink)unchanged&=t.localToWorldMatrix==matrices[i];
    }
    record.views[sample]=new FaceStudyView{image=images[sample],cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,fieldOfView=StoryCamera.fieldOfView,eyesClosed=closed,bodyPoseUnchanged=unchanged};
    record.allBodyPosesUnchanged&=unchanged;
   }
   File.WriteAllText(Path.Combine(output,"face-study.json"),JsonUtility.ToJson(record,true));
   if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);PlayerPrefs.Save();
   Time.timeScale=1;Application.Quit();
  }
  [Serializable] sealed class GroundStudyRecord
  {
   public string purpose="Albedo contact-layer A/B/A only. Both source PNGs use identical runtime RGBA32 sRGB/mip/filter settings; this is not final imported-texture, gameplay or performance evidence.";
   public string baselineSHA256,candidateSHA256;public int width,height,textureWidth,textureHeight;
   public float normalScale,frozenTime;public bool transformsAndLightsUnchanged;
   public FaceStudyView[] views;
  }
  static string FileSHA256(byte[] bytes)
  {using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","");}
  IEnumerator GroundContactStudy(string output)
  {
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   Directory.CreateDirectory(output);
   // The launcher stages these two explicitly selected input files beside the evidence.
   var baselineBytes=File.ReadAllBytes(Path.Combine(output,"baseline.png"));
   var candidateBytes=File.ReadAllBytes(Path.Combine(output,"candidate.png"));
   var baseline=new Texture2D(2,2,TextureFormat.RGBA32,true,false);
   var candidate=new Texture2D(2,2,TextureFormat.RGBA32,true,false);
   if(!baseline.LoadImage(baselineBytes)||!candidate.LoadImage(candidateBytes))throw new InvalidDataException("Ground study input PNG failed to load.");
   foreach(var texture in new[]{baseline,candidate}){texture.filterMode=FilterMode.Trilinear;texture.anisoLevel=4;texture.wrapMode=TextureWrapMode.Repeat;}
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   StartJourney(false);Logic.SetLamp(0,0,true,true);Logic.Advance();
   Logic.SetLamp(1,0,false,true);Logic.Advance();
   Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
   HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
   traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);atmosphere.Night=1;
   yield return null;yield return new WaitForEndOfFrame();atmosphere.enabled=false;Time.timeScale=0;
   var material=Find(island.transform,"Island_Meadow").GetComponent<Renderer>().sharedMaterial;
   var record=new GroundStudyRecord{baselineSHA256=FileSHA256(baselineBytes),candidateSHA256=FileSHA256(candidateBytes),
    width=Screen.width,height=Screen.height,textureWidth=baseline.width,textureHeight=baseline.height,
    normalScale=material.GetFloat("_BumpScale"),frozenTime=Time.time,transformsAndLightsUnchanged=true,views=new FaceStudyView[9]};
   var transforms=island.GetComponentsInChildren<Transform>();var matrices=new Matrix4x4[transforms.Length];
   for(int i=0;i<transforms.Length;i++)matrices[i]=transforms[i].localToWorldMatrix;
   var lights=FindObjectsByType<Light>(FindObjectsSortMode.None);var intensities=new float[lights.Length];
   for(int i=0;i<lights.Length;i++)intensities[i]=lights[i].intensity;
   var positions=new[]{new Vector3(0,1.9f,-8.1f),new Vector3(1.55f,.65f,-4.4f),new Vector3(-3.35f,.65f,-3.2f)};
   var targets=new[]{new Vector3(0,.7f,-3.3f),new Vector3(1,.04f,-3.1f),new Vector3(-4.2f,.04f,-2.25f)};
   var names=new[]{"path","roots","lamp"};
   for(int view=0;view<3;view++){
    StoryCamera.fieldOfView=view==0?48:42;StoryCamera.transform.position=positions[view];StoryCamera.transform.LookAt(targets[view]);
    for(int variant=0;variant<3;variant++){
     material.SetTexture("_BaseMap",variant==1?candidate:baseline);
     string filename=names[view]+"-"+(variant==1?"candidate":variant==0?"baseline":"baseline-repeat")+".png";
     yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();
     ScreenCapture.CaptureScreenshot(Path.Combine(output,filename));yield return new WaitForSecondsRealtime(.5f);
     bool fixedScene=true;
     for(int i=0;i<transforms.Length;i++)fixedScene&=transforms[i].localToWorldMatrix==matrices[i];
     for(int i=0;i<lights.Length;i++)fixedScene&=lights[i].intensity==intensities[i];
     record.transformsAndLightsUnchanged&=fixedScene;
     record.views[view*3+variant]=new FaceStudyView{image=filename,cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,fieldOfView=StoryCamera.fieldOfView,bodyPoseUnchanged=fixedScene};
    }
   }
   File.WriteAllText(Path.Combine(output,"ground-study.json"),JsonUtility.ToJson(record,true));
   if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);PlayerPrefs.Save();
   Time.timeScale=1;Application.Quit();
  }
 }
}
