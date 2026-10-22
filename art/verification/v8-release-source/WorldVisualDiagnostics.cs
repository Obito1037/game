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
 }
}
