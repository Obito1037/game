using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace BorrowedLight
{
 public sealed partial class WorldDirector
 {
  const string GroundDetailSourceSHA256="483D36A325CA6B05BBB8580DD3E238AF866F331D762976CB0064569FD7925F1B";
  const float GroundDetailTileMetres=1.8f,GroundDetailStrength=.55f,GroundDetailSoftStrength=.35f;
  [Serializable] sealed class GroundTextureIdentity
  {
   public string name,format,graphicsFormat;public int width,height,mipCount,aniso;
   public string filter,wrap;
  }
  [Serializable] sealed class GroundDetailView
  {
   public string image,variant,materialName,shader;public Vector3 cameraPosition;public Quaternion cameraRotation;
   public float fieldOfView,normalScale,detailStrength;public Color baseColor;
   public Vector2 baseTiling,baseOffset,detailTiling,detailOffset;
   public int actualPNGWidth,actualPNGHeight;public bool sceneUnchanged,otherMaterialsUnchanged,baseTexturesUnchanged;
  }
  [Serializable] sealed class GroundDetailRecord
  {
   public string purpose="Ground-only fixed path/roots/lamp baseline/detail .55/detail-soft .35/normal-only .65/baseline-repeat study. Frozen bind pose and time; NOT normal gameplay, FPS or release acceptance.";
   public bool stagingOnly=true,allInvariantsPassed=true;
   public string rendererName,meshName,detailResource="Textures/GroundDetailV12",originalSHA256=GroundDetailSourceSHA256;
   public string[] variants={"baseline","detail","detail-soft","normal-only","baseline-repeat"};
   public float[] variantDetailStrengths={0,GroundDetailStrength,GroundDetailSoftStrength,0,0};
   public int screenWidth,screenHeight,meshVertexCount;
   public float frozenTime,night,tileMetres=GroundDetailTileMetres,defaultDetailStrength=GroundDetailStrength,softDetailStrength=GroundDetailSoftStrength;
   public double authoredLinearLuminanceMean=.15805805065816778,clampedRatioMean=.9620164207456156;
   public GroundTextureIdentity baseMap,baseNormal,detailMap;public FaceStudyLight[] lights;
   public GroundDetailView[] views=new GroundDetailView[15];
  }
  static GroundTextureIdentity GroundTexture(Texture texture)
  {
   if(texture==null)return null;var t=texture as Texture2D;
   return new GroundTextureIdentity{name=texture.name,width=texture.width,height=texture.height,
    format=t==null?"not Texture2D":t.format.ToString(),graphicsFormat=texture.graphicsFormat.ToString(),
    mipCount=t==null?0:t.mipmapCount,
    aniso=texture.anisoLevel,filter=texture.filterMode.ToString(),wrap=texture.wrapMode.ToString()};
  }
  static bool GroundPNGSize(string file,out int width,out int height)
  {
   width=height=0;if(!File.Exists(file))return false;
   try{using(var f=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.ReadWrite)){
    if(f.Length<36)return false;var bytes=new byte[24];if(f.Read(bytes,0,24)!=24)return false;
    if(bytes[0]!=137||bytes[1]!=80||bytes[2]!=78||bytes[3]!=71)return false;
    // CaptureScreenshot writes asynchronously: the header alone is not completion.
    f.Position=f.Length-12;var end=new byte[12];if(f.Read(end,0,12)!=12)return false;
    if(end[0]!=0||end[1]!=0||end[2]!=0||end[3]!=0||end[4]!=73||end[5]!=69||end[6]!=78||end[7]!=68)return false;
    width=(bytes[16]<<24)|(bytes[17]<<16)|(bytes[18]<<8)|bytes[19];
    height=(bytes[20]<<24)|(bytes[21]<<16)|(bytes[22]<<8)|bytes[23];return width>0&&height>0;
   }}catch(IOException){return false;}
  }
  IEnumerator GroundDetailStudy(string output)
  {
   // This opt-in branch is the only caller. The normal Remap path stays v11.
   traveler.enabled=false;enabled=false;HUD.gameObject.SetActive(false);
   Directory.CreateDirectory(output);
   const string saveKey="BorrowedLight.Journey.v1";
   bool hadSave=PlayerPrefs.HasKey(saveKey);string previousSave=PlayerPrefs.GetString(saveKey);
   float previousTimeScale=Time.timeScale;
   Renderer ground=null;Material[] originalMaterials=null;Material detail=null,detailSoft=null,normalOnly=null;
   try{
    StartJourney(false);Logic.SetLamp(0,0,true,true);Logic.Advance();
    Logic.SetLamp(1,0,false,true);Logic.Advance();
    Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);Logic.Advance();
    HUD.ReturnToIsland?.Invoke();atmosphere.ClearCelebration();
    traveler.transform.SetPositionAndRotation(new Vector3(0,.1f,-3.3f),Quaternion.identity);atmosphere.Night=1;
    yield return null;yield return new WaitForEndOfFrame();
    atmosphere.enabled=false;Time.timeScale=0;
    foreach(var r in island.GetComponentsInChildren<Renderer>())if(r.name=="Island_Meadow"){
     if(ground!=null)throw new InvalidDataException("Ground detail study requires exactly one Island_Meadow renderer");ground=r;
    }
    if(ground==null)throw new InvalidDataException("Island_Meadow renderer missing");
    originalMaterials=ground.sharedMaterials;
    if(originalMaterials.Length!=1)throw new InvalidDataException("Unexpected ground material slots");
    var baseline=originalMaterials[0];var mesh=ground.GetComponent<MeshFilter>()?.sharedMesh;
    var detailTexture=Resources.Load<Texture2D>("Textures/GroundDetailV12");
    var template=Resources.Load<Material>("Materials/GroundDetailV12");
    if(mesh==null||baseline==null||detailTexture==null||template==null)throw new InvalidDataException("Ground candidate resources missing: evaluate tools/setup-ground-detail-v12.cs first");
    if(baseline.shader.name!="Universal Render Pipeline/Lit"||Mathf.Abs(baseline.GetFloat("_BumpScale")-.22f)>.0001f)
     throw new InvalidDataException("Baseline must be unchanged v11 URP/Lit with normal scale .22");
    if(template.shader.name!="BorrowedLight/GroundDetail"||!template.shader.isSupported)throw new InvalidDataException("Ground detail shader unsupported");
    var baseTexture=baseline.GetTexture("_BaseMap");var baseNormal=baseline.GetTexture("_BumpMap");
    if(baseTexture==null||baseNormal==null)throw new InvalidDataException("Meadow base maps missing");
    detail=new Material(baseline){name="BI_grass — ground detail v12 diagnostic",shader=template.shader};
    detail.SetTexture("_DetailAlbedoMap",detailTexture);detail.SetTextureScale("_DetailAlbedoMap",Vector2.one/GroundDetailTileMetres);
    detail.SetTextureOffset("_DetailAlbedoMap",Vector2.zero);detail.SetFloat("_DetailAlbedoMapScale",GroundDetailStrength);
    detail.SetFloat("_DetailNormalMapScale",0);detail.DisableKeyword("_DETAIL_MULX2");detail.DisableKeyword("_DETAIL_SCALED");
    detail.EnableKeyword("_NORMALMAP");
    detailSoft=new Material(detail){name="BI_grass — ground detail v12 soft diagnostic"};detailSoft.SetFloat("_DetailAlbedoMapScale",GroundDetailSoftStrength);
    normalOnly=new Material(baseline){name="BI_grass — normal .65 diagnostic"};normalOnly.SetFloat("_BumpScale",.65f);
    var variants=new[]{baseline,detail,detailSoft,normalOnly,baseline};
    var record=new GroundDetailRecord{rendererName=ground.name,meshName=mesh.name,meshVertexCount=mesh.vertexCount,
     screenWidth=Screen.width,screenHeight=Screen.height,frozenTime=Time.time,night=atmosphere.Night,
     baseMap=GroundTexture(baseTexture),baseNormal=GroundTexture(baseNormal),detailMap=GroundTexture(detailTexture)};
    var transforms=new List<Transform>(island.GetComponentsInChildren<Transform>());transforms.AddRange(traveler.GetComponentsInChildren<Transform>());
    var matrices=new Matrix4x4[transforms.Count];for(int i=0;i<transforms.Count;i++)matrices[i]=transforms[i].localToWorldMatrix;
    var filters=island.GetComponentsInChildren<MeshFilter>();var sourceMeshes=new Mesh[filters.Length];for(int i=0;i<filters.Length;i++)sourceMeshes[i]=filters[i].sharedMesh;
    var otherRenderers=new List<Renderer>();var otherMaterials=new List<Material[]>();
    foreach(var r in island.GetComponentsInChildren<Renderer>())if(r!=ground){otherRenderers.Add(r);otherMaterials.Add(r.sharedMaterials);}
    var lights=FindObjectsByType<Light>(FindObjectsSortMode.None);record.lights=new FaceStudyLight[lights.Length];
    for(int i=0;i<lights.Length;i++){var l=lights[i];record.lights[i]=new FaceStudyLight{name=l.name,type=l.type.ToString(),position=l.transform.position,rotation=l.transform.rotation,color=l.color,intensity=l.intensity,range=l.range};}
    var ambientSky=RenderSettings.ambientSkyColor;var ambientEquator=RenderSettings.ambientEquatorColor;var ambientGround=RenderSettings.ambientGroundColor;
    var ambientMode=RenderSettings.ambientMode;float ambientIntensity=RenderSettings.ambientIntensity;
    var positions=new[]{new Vector3(0,1.9f,-8.1f),new Vector3(1.55f,.65f,-4.4f),new Vector3(-3.35f,.65f,-3.2f)};
    var targets=new[]{new Vector3(0,.7f,-3.3f),new Vector3(1,.04f,-3.1f),new Vector3(-4.2f,.04f,-2.25f)};
    var names=new[]{"path","roots","lamp"};
    for(int view=0;view<3;view++){
     StoryCamera.fieldOfView=view==0?48:42;StoryCamera.transform.position=positions[view];StoryCamera.transform.LookAt(targets[view]);
     var cameraMatrix=StoryCamera.transform.localToWorldMatrix;
     for(int variant=0;variant<variants.Length;variant++){
      var material=variants[variant];ground.sharedMaterials=new[]{material};
      string filename=names[view]+"-"+record.variants[variant]+".png";string file=Path.Combine(output,filename);
      if(File.Exists(file))File.Delete(file);
      yield return new WaitForSecondsRealtime(.5f);yield return new WaitForEndOfFrame();ScreenCapture.CaptureScreenshot(file);
      int actualWidth=0,actualHeight=0;float deadline=Time.realtimeSinceStartup+5;
      while(!GroundPNGSize(file,out actualWidth,out actualHeight)&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(.1f);
      if(actualWidth==0||actualHeight==0)throw new IOException("Screenshot was not written: "+filename);
      bool fixedScene=StoryCamera.transform.localToWorldMatrix==cameraMatrix&&Time.time==record.frozenTime&&atmosphere.Night==record.night;
      fixedScene&=RenderSettings.ambientMode==ambientMode&&RenderSettings.ambientIntensity==ambientIntensity&&RenderSettings.ambientSkyColor==ambientSky&&RenderSettings.ambientEquatorColor==ambientEquator&&RenderSettings.ambientGroundColor==ambientGround;
      for(int i=0;i<transforms.Count;i++)fixedScene&=transforms[i].localToWorldMatrix==matrices[i];
      for(int i=0;i<filters.Length;i++)fixedScene&=filters[i].sharedMesh==sourceMeshes[i];
      for(int i=0;i<lights.Length;i++){var l=lights[i];var old=record.lights[i];fixedScene&=l.transform.position==old.position&&l.transform.rotation==old.rotation&&l.color==old.color&&l.intensity==old.intensity&&l.range==old.range;}
      bool unchangedOthers=true;for(int i=0;i<otherRenderers.Count;i++){
       var now=otherRenderers[i].sharedMaterials;var old=otherMaterials[i];unchangedOthers&=now.Length==old.Length;
       if(now.Length==old.Length)for(int j=0;j<now.Length;j++)unchangedOthers&=now[j]==old[j];
      }
      bool baseUnchanged=material.GetTexture("_BaseMap")==baseTexture&&material.GetTexture("_BumpMap")==baseNormal&&material.GetColor("_BaseColor")==baseline.GetColor("_BaseColor")&&material.GetTextureScale("_BaseMap")==baseline.GetTextureScale("_BaseMap")&&material.GetTextureOffset("_BaseMap")==baseline.GetTextureOffset("_BaseMap");
      record.allInvariantsPassed&=fixedScene&&unchangedOthers&&baseUnchanged&&actualWidth==record.screenWidth&&actualHeight==record.screenHeight;
      bool isDetail=material.shader.name=="BorrowedLight/GroundDetail";
      record.views[view*variants.Length+variant]=new GroundDetailView{image=filename,variant=record.variants[variant],materialName=material.name,shader=material.shader.name,
       cameraPosition=StoryCamera.transform.position,cameraRotation=StoryCamera.transform.rotation,fieldOfView=StoryCamera.fieldOfView,
       normalScale=material.GetFloat("_BumpScale"),detailStrength=isDetail?material.GetFloat("_DetailAlbedoMapScale"):0,baseColor=material.GetColor("_BaseColor"),
       baseTiling=material.GetTextureScale("_BaseMap"),baseOffset=material.GetTextureOffset("_BaseMap"),
       detailTiling=isDetail?material.GetTextureScale("_DetailAlbedoMap"):Vector2.zero,detailOffset=Vector2.zero,
       actualPNGWidth=actualWidth,actualPNGHeight=actualHeight,sceneUnchanged=fixedScene,otherMaterialsUnchanged=unchangedOthers,baseTexturesUnchanged=baseUnchanged};
      File.WriteAllText(Path.Combine(output,"ground-detail-study.json"),JsonUtility.ToJson(record,true));
     }
    }
    if(!record.allInvariantsPassed)throw new InvalidDataException("Ground detail study invariants failed; inspect ground-detail-study.json");
   }finally{
    if(ground!=null&&originalMaterials!=null)ground.sharedMaterials=originalMaterials;
    if(detail!=null)Destroy(detail);if(detailSoft!=null)Destroy(detailSoft);if(normalOnly!=null)Destroy(normalOnly);
    if(hadSave)PlayerPrefs.SetString(saveKey,previousSave);else PlayerPrefs.DeleteKey(saveKey);
    PlayerPrefs.Save();Time.timeScale=previousTimeScale;Application.Quit();
   }
  }
 }
}
