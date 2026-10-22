using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering;

namespace BorrowedLight
{
 public sealed class LampTouch : MonoBehaviour { public int Index; }
 public sealed class TransientBeam : MonoBehaviour
 { public Mesh OwnedMesh;public Material OwnedMaterial;void OnDestroy(){if(OwnedMesh!=null)Destroy(OwnedMesh);if(OwnedMaterial!=null)Destroy(OwnedMaterial);} }
 public sealed class TransientCollisionMesh : MonoBehaviour
 { public Mesh OwnedMesh;void OnDestroy(){if(OwnedMesh!=null)Destroy(OwnedMesh);} }
 public sealed partial class WorldDirector : MonoBehaviour
 {
  public GameLogic Logic {get;private set;}
  public Camera StoryCamera {get;private set;}
  public StoryHUD HUD {get;private set;}
  public bool Exploring {get;private set;}
  WorldAtmosphere atmosphere;TravelerMotor traveler;GameObject island;bool hasFoliageVertexColors;
  readonly Vector3[] lampPoints={new Vector3(-4.5f,1.85f,-2),new Vector3(1.8f,1.85f,3.4f),new Vector3(4.7f,1.85f,-2.4f)};
  readonly Vector3[] targetPoints={new Vector3(-1.8f,.08f,-3.2f),new Vector3(-5.8f,.1f,.15f),new Vector3(-4.1f,1.6f,3.05f),new Vector3(6.9f,.12f,-3.35f)};
  Transform[] lampHeads=new Transform[3];Light[] lampLights=new Light[3];LineRenderer[] selectionRings=new LineRenderer[3];
  Transform beamRoot;Light[] destinationLights=new Light[4];GameObject[] targetGlows=new GameObject[4];
  Dictionary<string,Material> materials=new Dictionary<string,Material>();
  float fade=1;bool started,finished,soundOn=true;float yaw=0,pitch=12,distance=4.9f;float lastSound;AudioSource music,fx;AudioClip bell;
  Vector3 desiredCamera,desiredLook,currentLook;float nightTarget=.35f;float cameraHold;int previousPhase=-1;float averageFps;int fpsFrames;float fpsTime;
  readonly string[] titles={"","让光，落在需要的地方","一扇窗，也有它的星空","把星光，借给晚归的人","星星一直都在"};
  readonly string[] tasks={"","照亮小路与长椅。\n旋转第一盏灯，试着打开宽光罩。","为读书的窗留一束安静的光。\n小路与长椅也要保持明亮。","让小路、长椅、窗户与码头都有光。\n重新分配三盏灯，给天空留下一片黑夜。",""};
  void Awake()
  {
#if UNITY_WEBGL
   QualitySettings.SetQualityLevel(1,true);
#endif
   Application.targetFrameRate=60;QualitySettings.vSyncCount=0;QualitySettings.shadowDistance=38;
   CreateCamera();CreateIsland();CreateAtmosphere();CreateTraveler();CreateLamps();CreateAudio();
   HUD=new GameObject("A book of light",typeof(RectTransform)).AddComponent<StoryHUD>();HUD.Create();
   Logic=gameObject.AddComponent<GameLogic>();
   Logic.OnChanged+=OnChanged;Logic.OnNarration+=text=>HUD.Toast(text);Logic.OnPhaseChanged+=OnPhaseChanged;
   HUD.Begin=()=>StartJourney(false);HUD.Resume=()=>StartJourney(true);HUD.ChooseLamp=Select;
   HUD.TurnLeft=()=>{Logic.RotateSelected(-1);Chime();};HUD.TurnRight=()=>{Logic.RotateSelected(1);Chime();};HUD.ChangeShade=()=>{Logic.ToggleSelectedShade();Chime();};
   HUD.Continue=()=>Logic.Advance();HUD.Restart=()=>{finished=false;started=true;Exploring=false;traveler.CanMove=false;traveler.transform.SetPositionAndRotation(new Vector3(0,.07f,-5.6f),Quaternion.identity);yaw=0;pitch=12;distance=4.9f;HUD.SetExploring(false);HUD.ShowPlay();atmosphere.ClearCelebration();Logic.RestartJourney();if(Logic.Phase==GamePhase.Prologue)Logic.Advance();};
   HUD.ToggleSound=()=>{soundOn=!soundOn;AudioListener.volume=soundOn?1:0;HUD.SetSound(soundOn);};
   HUD.ToggleExplore=ToggleExplore;HUD.ReturnToIsland=()=>{finished=false;HUD.ShowPlay();ToggleExplore(true);};
   HUD.SetResumeAvailable(Logic.HasSavedProgress);
   HUD.ShowMenu();desiredCamera=new Vector3(21,17,-26);desiredLook=new Vector3(-2,.4f,0);StoryCamera.transform.position=desiredCamera;currentLook=desiredLook;StoryCamera.transform.LookAt(currentLook);
   var args=Environment.GetCommandLineArgs();for(int i=0;i+1<args.Length;i++){
    if(args[i]=="-borrowedLightQA"){StartCoroutine(AutomatedTour(args[i+1]));break;}
    if(args[i]=="-borrowedLightPortraitCompare"){StartCoroutine(PortraitLightComparison(args[i+1]));break;}
    if(args[i]=="-borrowedLightFaceStudy"){StartCoroutine(FaceGeometryStudy(args[i+1]));break;}
    if(args[i]=="-borrowedLightFaceEyeStudy"){StartCoroutine(FaceGeometryStudy(args[i+1],true));break;}
    if(args[i]=="-borrowedLightGroundStudy"){StartCoroutine(GroundContactStudy(args[i+1]));break;}
    if(args[i]=="-borrowedLightStoneStudy"){StartCoroutine(WorldMaterialStudy(args[i+1],false));break;}
    if(args[i]=="-borrowedLightFoliageStudy"){StartCoroutine(WorldMaterialStudy(args[i+1],true));break;}
    if(args[i]=="-borrowedLightSilhouetteStudy"){StartCoroutine(WorldMaterialStudy(args[i+1],false,true));break;}
   }
  }
  void CreateCamera()
  {
   var go=new GameObject("The storyteller's camera",typeof(Camera),typeof(AudioListener));StoryCamera=go.GetComponent<Camera>();StoryCamera.tag="MainCamera";StoryCamera.clearFlags=CameraClearFlags.Skybox;StoryCamera.backgroundColor=new Color(.018f,.04f,.065f);StoryCamera.nearClipPlane=.15f;StoryCamera.farClipPlane=220;StoryCamera.fieldOfView=36;StoryCamera.allowHDR=true;StoryCamera.allowMSAA=true;
   var cameraData=go.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();cameraData.antialiasing=UnityEngine.Rendering.Universal.AntialiasingMode.FastApproximateAntialiasing;
  }
  void CreateIsland()
  {
   var prefab=Resources.Load<GameObject>("Models/Island");
   if(prefab==null){Debug.LogError("Island model missing. Run the Blender asset pipeline.");return;}
   island=Instantiate(prefab,Vector3.zero,Quaternion.identity);island.name="The island that borrowed all the light";
   var calibration=Find(island.transform,"Anchor_Lamp_A");if(calibration!=null&&calibration.position.x>0){var scale=island.transform.localScale;scale.x=-scale.x;island.transform.localScale=scale;}
   foreach(var mf in island.GetComponentsInChildren<MeshFilter>())if(mf.sharedMesh!=null&&mf.sharedMesh.HasVertexAttribute(VertexAttribute.Color)){hasFoliageVertexColors=true;break;}
   foreach(var r in island.GetComponentsInChildren<Renderer>()){bool vertexColors=HasVertexColors(r);var mapped=new Material[r.sharedMaterials.Length];for(int i=0;i<mapped.Length;i++)mapped[i]=Remap(r.sharedMaterials[i],vertexColors);r.sharedMaterials=mapped;bool finePlants=r.name.Contains("GrassTufts")||r.name.Contains("Wildflowers")||r.name.Contains("Ferns")||r.name.Contains("Lavender")||r.name.Contains("LeafEdges")||r.name.Contains("CreepingMeadow");r.shadowCastingMode=finePlants?ShadowCastingMode.Off:ShadowCastingMode.On;r.receiveShadows=true;}
   foreach(var mf in island.GetComponentsInChildren<MeshFilter>())
   {
    if(mf.name=="Observatory_StoneAndBrass"){CreateObservatoryColliders(mf);continue;}
    if(mf.name=="Cliff_Pier"){CreatePierColliders(mf);continue;}
    // Decorative creeping leaves are not a walking surface.
    bool ground=mf.name=="Island_Meadow"||mf.name=="Garden_Walkways";
    bool obstacle=mf.name.Contains("Cabin")||mf.name.Contains("TreeTrunks")||mf.name.Contains("Bench")||mf.name.Contains("HeroBoulders");
    if((ground||obstacle)&&mf.sharedMesh!=null){mf.gameObject.layer=ground?8:9;var c=mf.gameObject.AddComponent<MeshCollider>();c.sharedMesh=mf.sharedMesh;}
   }
   // The island stays fixed after calibration. Unity retains each renderer's
   // culling and the original collider/anchor objects while sharing static data.
   StaticBatchingUtility.Combine(island);
   int batched=0;foreach(var r in island.GetComponentsInChildren<Renderer>())if(r.isPartOfStaticBatch)batched++;
   Debug.Log("ISLAND_STATIC_BATCH_RENDERERS: "+batched);
   var anchor=Find(island.transform,"Anchor_Lamp_A");if(anchor!=null)Debug.Log("ISLAND_ANCHOR_A: "+anchor.position);
   Debug.Log("ISLAND_RENDERERS: "+island.GetComponentsInChildren<Renderer>().Length);
  }
  static void CreatePierColliders(MeshFilter source)
  {
   var original=source.sharedMesh;if(original==null)return;
   // A continuous deck proxy bridges the authored 2 cm plank gaps. Tiny nails,
   // paper and mooring-ring details should not lift or obstruct the traveler.
   var deck=new GameObject("Pier walkable deck");deck.transform.position=new Vector3(7.55f,.105f,-3.35f);deck.transform.SetParent(source.transform,true);deck.layer=8;
   var box=deck.AddComponent<BoxCollider>();box.size=new Vector3(5.335f,.13f,1.20f);
   var vertices=original.vertices;var indices=new List<int>();var triangles=original.triangles;
   for(int t=0;t<triangles.Length;t+=3){
    float lowest=float.PositiveInfinity,highest=float.NegativeInfinity;
    for(int j=0;j<3;j++){float y=source.transform.TransformPoint(vertices[triangles[t+j]]).y;lowest=Mathf.Min(lowest,y);highest=Mathf.Max(highest,y);}
    if(lowest>=-.20f&&highest<=.24f)continue;
    indices.Add(triangles[t]);indices.Add(triangles[t+1]);indices.Add(triangles[t+2]);
   }
   var mesh=new Mesh{name="Pier solid rails",indexFormat=original.indexFormat};mesh.vertices=vertices;mesh.SetTriangles(indices,0);mesh.RecalculateBounds();
   var rails=new GameObject(mesh.name);rails.transform.SetParent(source.transform,false);rails.layer=9;rails.AddComponent<MeshCollider>().sharedMesh=mesh;rails.AddComponent<TransientCollisionMesh>().OwnedMesh=mesh;
  }
  static void CreateObservatoryColliders(MeshFilter source)
  {
   // The authored mesh combines three low steps (including dial inlays below
   // 0.305 m) and the tall instrument. Only the steps should support the feet.
   var original=source.sharedMesh;if(original==null)return;
   var vertices=original.vertices;var sourceMaterials=source.GetComponent<Renderer>().sharedMaterials;
   var ground=new List<int>();var obstacle=new List<int>();
   for(int sub=0;sub<original.subMeshCount;sub++){
    // Keep the instrument pedestal's downward-facing bottom with its sides.
    bool solidBase=sub<sourceMaterials.Length&&sourceMaterials[sub]!=null&&sourceMaterials[sub].name.Contains("BI_metal_dark");var triangles=original.GetTriangles(sub);
    for(int i=0;i<triangles.Length;i+=3){float highest=float.NegativeInfinity;for(int j=0;j<3;j++)highest=Mathf.Max(highest,source.transform.TransformPoint(vertices[triangles[i+j]]).y);var target=!solidBase&&highest<=.305f?ground:obstacle;target.Add(triangles[i]);target.Add(triangles[i+1]);target.Add(triangles[i+2]);}
   }
   for(int i=0;i<2;i++){
    var indices=i==0?ground:obstacle;if(indices.Count==0)continue;
    var mesh=new Mesh{name=i==0?"Observatory walkable steps":"Observatory solid instrument",indexFormat=original.indexFormat};mesh.vertices=vertices;mesh.SetTriangles(indices,0);mesh.RecalculateBounds();
    var go=new GameObject(mesh.name);go.transform.SetParent(source.transform,false);go.layer=i==0?8:9;go.AddComponent<MeshCollider>().sharedMesh=mesh;go.AddComponent<TransientCollisionMesh>().OwnedMesh=mesh;
   }
  }
  static bool HasVertexColors(Renderer renderer)
  {
   var mesh=renderer is SkinnedMeshRenderer skin?skin.sharedMesh:renderer.GetComponent<MeshFilter>()?.sharedMesh;
   return mesh!=null&&mesh.HasVertexAttribute(VertexAttribute.Color);
  }
  Material Remap(Material source,bool vertexColors=false)
  {
   if(source==null)return WorldAtmosphere.MaterialFor(new Color(.4f,.5f,.5f));
   string cacheKey=source.name+(vertexColors?"|painted-vertices":"|plain");
   if(materials.TryGetValue(cacheKey,out var cached))return cached;
   Color c=source.HasProperty("_BaseColor")?source.GetColor("_BaseColor"):source.HasProperty("_Color")?source.color:Color.white;
   string materialName=source.name.ToLowerInvariant();bool metal=materialName.Contains("brass")||materialName.Contains("metal")||materialName.Contains("goldedges");
   var m=WorldAtmosphere.MaterialFor(c);m.name=source.name+" — story light";m.SetFloat("_Smoothness",metal?.58f:.17f);
   if(materialName.StartsWith("bi_")&&(materialName.Contains("rock")||materialName.Contains("stone")||materialName.Contains("wood")||materialName.Contains("plaster")||materialName.Contains("roof")||materialName.Contains("leaf"))){bool foliage=materialName.Contains("leaf");var painted=Resources.Load<Material>(foliage?(hasFoliageVertexColors?"Materials/FoliageTinted":"Materials/FoliagePaint"):"Materials/PaintedSurface");if(painted!=null){m.shader=painted.shader;m.SetColor("_BaseColor",c);if(foliage&&hasFoliageVertexColors)m.EnableKeyword("_FOLIAGE_VERTEX_COLOR");if(!foliage)m.SetFloat("_SurfaceKind",materialName.Contains("wood")?1:materialName.Contains("plaster")?2:materialName.Contains("roof")?3:0);}}
   if(metal){m.SetFloat("_Metallic",.72f);}
   else {m.SetFloat("_Cull",0);m.doubleSidedGI=true;}
   if(materialName.StartsWith("traveler_")&&(materialName.Contains("cape_")||materialName.Contains("coat_")||materialName.Contains("hood_")||materialName.Contains("scarf_")||materialName.Contains("trousers_")||materialName.Contains("gloves_"))){var cloth=Resources.Load<Material>("Materials/PaintedSurface");if(cloth!=null){m.shader=cloth.shader;m.SetColor("_BaseColor",c);m.SetFloat("_SurfaceKind",5);m.SetFloat("_Smoothness",.09f);}}
   if(materialName.Contains("face_"))m.SetFloat("_Smoothness",.22f);
   bool paintedCharacter=materialName.StartsWith("traveler_")&&(materialName.Contains("face_")||m.shader.name=="BorrowedLight/PaintedSurface");
   if(vertexColors&&(materialName.StartsWith("bi_rock_hero_")||paintedCharacter)){
    var tint=Resources.Load<Material>("Materials/PaintedTinted");
    if(tint!=null){m.shader=tint.shader;m.EnableKeyword("_PAINT_VERTEX_COLOR");m.SetColor("_BaseColor",c);if(materialName.Contains("face_")){m.SetFloat("_SurfaceKind",6);m.SetFloat("_Smoothness",.20f);}}
   }
   if(materialName.StartsWith("bi_rock_hero_"))m.SetFloat("_SurfaceKind",7);
   if(materialName.Contains("eye_"))m.SetFloat("_Smoothness",.72f);
   // The shallow stylized eyes retain their painted catchlight without a wide
   // specular band obscuring the iris under the island's side lights.
   if(materialName.StartsWith("traveler_eye_ivory"))m.SetFloat("_Smoothness",.18f);
   else if(materialName.StartsWith("traveler_eye_amberrim")||materialName.StartsWith("traveler_eye_chestnut"))m.SetFloat("_Smoothness",.32f);
   else if(materialName.StartsWith("traveler_eye_pupil"))m.SetFloat("_Smoothness",.50f);
   if(materialName.Contains("grass")||materialName.Contains("leaf")||materialName.Contains("fern"))m.SetFloat("_Smoothness",.08f);
   if(materialName.StartsWith("bi_")&&(materialName.Contains("grass")||materialName.Contains("leaf")||materialName.Contains("flower")||materialName.Contains("stem")||materialName.Contains("moss"))){m.SetFloat("_Metallic",0);m.SetFloat("_Smoothness",0);if(m.HasProperty("_SpecularHighlights")){m.SetFloat("_SpecularHighlights",0);m.SetFloat("_EnvironmentReflections",0);m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");}m.SetColor("_EmissionColor",Color.black);m.DisableKeyword("_EMISSION");}
   Texture texture=source.HasProperty("_BaseMap")?source.GetTexture("_BaseMap"):source.HasProperty("_MainTex")?source.mainTexture:null;
   if(source.name=="BI_grass"||source.name.StartsWith("BI_grass.")){var meadow=Resources.Load<Texture2D>("Textures/Meadow");if(meadow!=null)texture=meadow;var normal=Resources.Load<Texture2D>("Textures/MeadowNormal");if(normal!=null){m.SetTexture("_BumpMap",normal);m.SetFloat("_BumpScale",.22f);m.EnableKeyword("_NORMALMAP");}}
   if(texture!=null){m.SetTexture("_BaseMap",texture);if(source.name.StartsWith("BI_grass"))m.SetColor("_BaseColor",Color.white);}
   if(materialName.StartsWith("bi_rock_hero_")){
    var stone=Resources.Load<Material>("Materials/PaintedRockV10");
    if(stone!=null&&stone.GetTexture("_BaseMap")!=null){m.EnableKeyword("_ROCK_TEXTURE");m.SetTexture("_BaseMap",stone.GetTexture("_BaseMap"));m.SetTextureScale("_BaseMap",stone.GetTextureScale("_BaseMap"));m.SetFloat("_BumpScale",stone.GetFloat("_BumpScale"));}
   }
   if(materialName.Contains("window")||materialName.Contains("warm_glow")){m.EnableKeyword("_EMISSION");m.SetColor("_EmissionColor",new Color(1,.52f,.15f)*1.4f);}
   if(materialName.Contains("amberglass")||materialName.Contains("warmheart")||materialName.Contains("catchlight")){m.EnableKeyword("_EMISSION");m.SetColor("_EmissionColor",c*(materialName.Contains("warmheart")?3.5f:materialName.Contains("catchlight")?.3f:.7f));}
   materials[cacheKey]=m;return m;
  }
  void CreateAtmosphere(){atmosphere=new GameObject("A sky full of unwritten letters").AddComponent<WorldAtmosphere>();atmosphere.Create(StoryCamera);}
  void CreateTraveler()
  {
   var actor=new GameObject("The little light keeper");actor.transform.position=new Vector3(0,.07f,-5.6f);traveler=actor.AddComponent<TravelerMotor>();traveler.ViewCamera=StoryCamera;
   var prefab=Resources.Load<GameObject>("Models/Traveler");
   if(prefab!=null){var model=Instantiate(prefab,actor.transform);model.name="Traveler";foreach(var r in model.GetComponentsInChildren<Renderer>()){bool vertexColors=HasVertexColors(r);var mapped=new Material[r.sharedMaterials.Length];for(int i=0;i<mapped.Length;i++)mapped[i]=Remap(r.sharedMaterials[i],vertexColors);r.sharedMaterials=mapped;}traveler.Bind(model.transform);}
   var lamp=WorldAtmosphere.NewLight("The light we carry",LightType.Point,new Color(1,.70f,.39f),.52f,Vector3.zero);var lanternAnchor=Find(actor.transform,"Lantern")??actor.transform;lamp.transform.SetParent(lanternAnchor,false);lamp.transform.localPosition=lanternAnchor==actor.transform?new Vector3(.33f,.7f,.18f):Vector3.zero;lamp.range=2.2f;
   var face=WorldAtmosphere.NewLight("A soft reflection on the traveler",LightType.Point,new Color(1,.88f,.74f),.23f,Vector3.zero);face.transform.SetParent(actor.transform,false);face.transform.localPosition=new Vector3(0,1.25f,.55f);face.range=1.1f;
  }
  void CreateLamps()
  {
   beamRoot=new GameObject("Where the light lands").transform;
   var brass=WorldAtmosphere.MaterialFor(new Color(.46f,.32f,.14f));brass.SetFloat("_Metallic",.7f);brass.SetFloat("_Smoothness",.55f);
   var glass=WorldAtmosphere.MaterialFor(new Color(1,.68f,.28f),3.5f);
   var ringMat=WorldAtmosphere.MaterialFor(new Color(1,.75f,.34f),1.05f);
   for(int i=0;i<3;i++){
    var head=new GameObject("Lamp "+(char)('A'+i)+" — turnable lantern");head.transform.position=lampPoints[i];lampHeads[i]=head.transform;
    var touch=head.AddComponent<LampTouch>();touch.Index=i;var collider=head.AddComponent<SphereCollider>();collider.radius=.62f;
    Primitive("Lantern lower rim",PrimitiveType.Cylinder,head.transform,new Vector3(0,.05f,0),new Vector3(.34f,.04f,.34f),brass);
    Primitive("Lantern upper rim",PrimitiveType.Cylinder,head.transform,new Vector3(0,.49f,0),new Vector3(.34f,.045f,.34f),brass);
    WorldAtmosphere.Sphere("A borrowed sun",head.transform,new Vector3(0,.27f,0),new Vector3(.21f,.33f,.21f),glass);
    for(int j=0;j<4;j++){float a=j*Mathf.PI/2;Primitive("A brass rib",PrimitiveType.Cylinder,head.transform,new Vector3(Mathf.Cos(a)*.145f,.27f,Mathf.Sin(a)*.145f),new Vector3(.023f,.22f,.023f),brass);}
    var roof=Primitive("Lantern's little roof",PrimitiveType.Cylinder,head.transform,new Vector3(0,.59f,0),new Vector3(.41f,.055f,.41f),brass);roof.transform.localRotation=Quaternion.Euler(0,45,0);
    WorldAtmosphere.Sphere("Lantern finial",head.transform,new Vector3(0,.72f,0),Vector3.one*.10f,brass);
    lampLights[i]=WorldAtmosphere.NewLight("Warmth from lamp "+i,LightType.Point,new Color(1,.66f,.29f),2.3f,lampPoints[i]+Vector3.up*.2f);lampLights[i].range=5;
    var ring=WorldAtmosphere.Ring("Select light "+i,transform,.55f,.025f,ringMat);ring.transform.position=new Vector3(lampPoints[i].x,.14f,lampPoints[i].z);selectionRings[i]=ring.GetComponent<LineRenderer>();
   }
   for(int i=0;i<4;i++){
    destinationLights[i]=WorldAtmosphere.NewLight("A place that needs light "+i,LightType.Point,new Color(1,.71f,.39f),0,targetPoints[i]+Vector3.up*.6f);destinationLights[i].range=i==2?2.5f:3.5f;
    targetGlows[i]=WorldAtmosphere.Ring("A little circle of safety",transform,i==2?.42f:.75f,.018f,ringMat);targetGlows[i].transform.position=targetPoints[i]+Vector3.up*.02f;if(i==2)targetGlows[i].transform.rotation=Quaternion.Euler(90,0,0);
   }
  }
  static GameObject Primitive(string name,PrimitiveType type,Transform parent,Vector3 pos,Vector3 scale,Material mat){var o=GameObject.CreatePrimitive(type);o.name=name;o.transform.SetParent(parent,false);o.transform.localPosition=pos;o.transform.localScale=scale;o.GetComponent<Renderer>().sharedMaterial=mat;Destroy(o.GetComponent<Collider>());return o;}
  void CreateAudio()
  {
   music=gameObject.AddComponent<AudioSource>();music.playOnAwake=false;music.volume=.22f;music.spatialBlend=0;var score=Resources.Load<AudioClip>("Audio/NightLetters");if(score!=null)StartCoroutine(StartMusicWhenReady(score));
   fx=gameObject.AddComponent<AudioSource>();fx.playOnAwake=false;fx.volume=.22f;bell=Resources.Load<AudioClip>("Audio/LanternChime");if(bell!=null&&bell.loadState==AudioDataLoadState.Unloaded)bell.LoadAudioData();
  }
  IEnumerator StartMusicWhenReady(AudioClip clip){if(clip.loadState==AudioDataLoadState.Unloaded)clip.LoadAudioData();while(music!=null&&clip.loadState==AudioDataLoadState.Loading)yield return null;if(music==null||clip.loadState!=AudioDataLoadState.Loaded)yield break;while(!started)yield return null;music.clip=clip;music.loop=true;music.Play();}
  void Chime(){if(Time.unscaledTime-lastSound>.09f&&bell!=null&&bell.loadState==AudioDataLoadState.Loaded){fx.pitch=.92f+Logic.SelectedLamp*.12f;fx.PlayOneShot(bell);lastSound=Time.unscaledTime;}}
  void StartJourney(bool resume){started=true;finished=false;Exploring=false;traveler.CanMove=false;HUD.SetExploring(false);HUD.ShowPlay();Logic.BeginJourney(resume);if(Logic.Phase==GamePhase.Prologue)Logic.Advance();OnChanged(Logic.Current);HUD.Toast("每一束光，都有它要去的地方。",5);}
  public void Select(int index){if(!started||finished)return;Logic.SelectLamp(index);Chime();}
  void ToggleExplore(){ToggleExplore(!Exploring);}
  void ToggleExplore(bool yes){if(!yes&&Logic.Phase==GamePhase.Epilogue){Exploring=false;finished=true;traveler.CanMove=false;HUD.ShowEnding();return;}Exploring=yes;traveler.CanMove=yes&&!HUD.IsSettings;HUD.SetExploring(yes);if(yes)HUD.Toast(Logic.Phase==GamePhase.Epilogue?"星空已经回来了。慢慢走，按 TAB 重读守夜人的来信。":"跟着脚下的光，慢慢走。靠近灯具按 E，可以回到调灯。",5);}
  void OnPhaseChanged(GamePhase phase){
#if UNITY_WEBGL
   Debug.Log("BORROWED_LIGHT_PHASE:"+(int)phase);
#endif
   if(phase==GamePhase.Epilogue&&!finished){finished=true;Exploring=false;traveler.CanMove=false;atmosphere.CelebratoryConstellation();HUD.ShowEnding("小路上有归人，窗边有故事。\n码头的灯，等到了最后一艘船。\n\n你没有带走一颗星，\n却为整座岛找回了星空。");Chime();}}
  void OnChanged(GameSnapshot s)
  {
   int phase=(int)s.Phase;int chapter=Mathf.Clamp(phase,1,3);
   if(phase!=previousPhase){previousPhase=phase;cameraHold=Time.time+1;}
   HUD.SetChapter(chapter,titles[chapter],tasks[chapter],s.Narration);
   HUD.SetLamp(s.SelectedLamp,s.Lamps[s.SelectedLamp].Direction,s.Lamps[s.SelectedLamp].Wide);
   HUD.SetContinue(s.CanAdvance&&s.Phase!=GamePhase.Epilogue&&s.Phase!=GamePhase.Prologue);
   int lit=0,total=s.Phase==GamePhase.Path?2:s.Phase==GamePhase.Window?3:4;
   int allMask=0;
   for(int i=0;i<3;i++)allMask|=LampPuzzle.GetCoverageMask(i,s.Lamps[i].Direction,s.Lamps[i].Wide,s.Lamps[i].IsOn);
   for(int i=0;i<4;i++)if((allMask&(1<<i))!=0){lit++;}
   nightTarget=s.Phase==GamePhase.Epilogue?1:Mathf.Clamp01(.15f+(1-s.Pollution/6f)*.72f);
   HUD.SetSky(nightTarget,Mathf.Min(lit,total),total,s.Pollution,s.AllowedPollution);HUD.SetPuzzleHint(s.Hint,LampPuzzle.GetUnlockedLampCount(s.Phase));UpdateLightPresentation(s,allMask);
  }
  void UpdateLightPresentation(GameSnapshot s,int allMask)
  {
   for(int c=beamRoot.childCount-1;c>=0;c--)Destroy(beamRoot.GetChild(c).gameObject);
   var veilSource=Resources.Load<Material>("Materials/LightVeil");
   for(int i=0;i<3;i++){
    var lamp=s.Lamps[i];lampHeads[i].localRotation=Quaternion.Euler(0,lamp.Direction*75,0);selectionRings[i].widthMultiplier=i==s.SelectedLamp?.045f:.014f;selectionRings[i].gameObject.SetActive(started&&!finished&&s.Phase!=GamePhase.Epilogue);lampLights[i].intensity=lamp.IsOn?2.1f:0;
    int mask=LampPuzzle.GetCoverageMask(i,lamp.Direction,lamp.Wide,lamp.IsOn);
    for(int j=0;j<4;j++)if((mask&(1<<j))!=0&&veilSource!=null){CreateBeam(i,j,lamp.Wide,veilSource);}
    if(mask==0&&lamp.IsOn&&veilSource!=null){CreateBeamTo(lampPoints[i]+Vector3.up*.25f,lampPoints[i]+Vector3.up*5+new Vector3(1,0,1),lamp.Wide?.85f:.28f,veilSource,new Color(1,.67f,.28f,.055f));}
   }
   for(int i=0;i<4;i++){bool lit=(allMask&(1<<i))!=0;destinationLights[i].intensity=lit?1.6f:0;targetGlows[i].SetActive(started&&!finished&&s.Phase!=GamePhase.Epilogue);var r=targetGlows[i].GetComponent<LineRenderer>();r.startColor=r.endColor=lit?new Color(1,.82f,.48f,.85f):new Color(.25f,.45f,.55f,.3f);}
  }
  void CreateBeam(int lamp,int target,bool wide,Material material){CreateBeamTo(lampPoints[lamp]+Vector3.up*.27f,targetPoints[target]+Vector3.up*.06f,wide?.85f:.32f,material,new Color(1,.69f,.3f,.065f));}
  void CreateBeamTo(Vector3 from,Vector3 to,float width,Material source,Color color)
  {
   var o=new GameObject("Light, finding its purpose");o.transform.SetParent(beamRoot);var mf=o.AddComponent<MeshFilter>();var mr=o.AddComponent<MeshRenderer>();var dir=(to-from).normalized;var side=Vector3.Cross(dir,StoryCamera.transform.forward).normalized;if(side.sqrMagnitude<.01f)side=Vector3.right;
   var mesh=new Mesh();mesh.vertices=new[]{from-side*.08f,from+side*.08f,to-side*width,to+side*width};mesh.uv=new[]{new Vector2(.1f,0),new Vector2(.9f,0),new Vector2(0,.97f),new Vector2(1,.97f)};mesh.triangles=new[]{0,1,2,2,1,3};mesh.RecalculateNormals();mf.sharedMesh=mesh;var m=new Material(source);m.SetColor("_Color",color);mr.sharedMaterial=m;mr.shadowCastingMode=ShadowCastingMode.Off;mr.receiveShadows=false;var allocation=o.AddComponent<TransientBeam>();allocation.OwnedMesh=mesh;allocation.OwnedMaterial=m;
  }
  void Update()
  {
   fade=Mathf.MoveTowards(fade,0,Time.unscaledDeltaTime*.4f);HUD.SetCurtain(fade);atmosphere.Night=Mathf.Lerp(atmosphere.Night,started?nightTarget:1,Time.deltaTime*.8f);
   traveler.CanMove=started&&Exploring&&!HUD.IsSettings&&!finished;
   var keyboard=Keyboard.current;if(keyboard!=null){if(keyboard.escapeKey.wasPressedThisFrame){HUD.ShowSettings(!HUD.IsSettings);traveler.CanMove=Exploring&&!HUD.IsSettings;}if(!HUD.IsSettings){if(!started&&keyboard.enterKey.wasPressedThisFrame)StartJourney(false);else if(started&&!finished){if(keyboard.tabKey.wasPressedThisFrame)ToggleExplore();if(!Exploring){if(keyboard.aKey.wasPressedThisFrame||keyboard.leftArrowKey.wasPressedThisFrame){Logic.RotateSelected(-1);Chime();}if(keyboard.dKey.wasPressedThisFrame||keyboard.rightArrowKey.wasPressedThisFrame){Logic.RotateSelected(1);Chime();}if(keyboard.spaceKey.wasPressedThisFrame){Logic.ToggleSelectedShade();Chime();}if(keyboard.digit1Key.wasPressedThisFrame)Select(0);if(keyboard.digit2Key.wasPressedThisFrame)Select(1);if(keyboard.digit3Key.wasPressedThisFrame)Select(2);if(keyboard.enterKey.wasPressedThisFrame&&Logic.Current.CanAdvance)Logic.Advance();}else if(keyboard.eKey.wasPressedThisFrame){int closest=0;float best=float.MaxValue;for(int i=0;i<3;i++){float d=Vector3.Distance(traveler.transform.position,lampPoints[i]);if(d<best){closest=i;best=d;}}if(best<4){ToggleExplore(false);Select(closest);}else HUD.Toast("再靠近一盏灯吧。",2);}}}}
   // Input System 1.20 uses normalized scroll steps (normally +/-1), not Windows' legacy +/-120 units.
   var mouse=Mouse.current;if(mouse!=null&&started&&!finished&&!HUD.IsSettings){if(Exploring){if(mouse.rightButton.isPressed){var delta=mouse.delta.ReadValue();yaw+=delta.x*.13f;pitch=Mathf.Clamp(pitch-delta.y*.10f,8,65);}distance=Mathf.Clamp(distance-mouse.scroll.ReadValue().y*.35f,2.5f,10);}else if(mouse.leftButton.wasPressedThisFrame&&!HUD.PointerOverUI()){var ray=StoryCamera.ScreenPointToRay(mouse.position.ReadValue());if(Physics.Raycast(ray,out var hit,100)){var lamp=hit.collider.GetComponentInParent<LampTouch>();if(lamp!=null)Select(lamp.Index);}}}
   fpsTime+=Time.unscaledDeltaTime;fpsFrames++;if(fpsTime>=1){averageFps=fpsFrames/fpsTime;fpsTime=0;fpsFrames=0;}
  }
  void LateUpdate()
  {
   if(HUD==null||StoryCamera==null)return;
   if(!started){float orbit=Mathf.Sin(Time.time*.035f)*.8f;desiredCamera=new Vector3(18+orbit,14,-23);desiredLook=new Vector3(-2.8f,.6f,0);}
   else if(finished){desiredCamera=new Vector3(18,14,-27);desiredLook=new Vector3(-3,3,2);}
   else if(Exploring){float r=yaw*Mathf.Deg2Rad;float p=pitch*Mathf.Deg2Rad;desiredLook=traveler.transform.position+Vector3.up*Mathf.Lerp(.69f,.84f,Mathf.InverseLerp(2.2f,4.9f,distance));desiredCamera=desiredLook+new Vector3(Mathf.Sin(r)*Mathf.Cos(p)*distance,Mathf.Sin(p)*distance,-Mathf.Cos(r)*Mathf.Cos(p)*distance);var sight=desiredCamera-desiredLook;if(Physics.SphereCast(desiredLook,.18f,sight.normalized,out var cameraHit,sight.magnitude,1<<9,QueryTriggerInteraction.Ignore))desiredCamera=desiredLook+sight.normalized*Mathf.Max(.65f,cameraHit.distance-.15f);}
   else {int selected=Logic.SelectedLamp;desiredCamera=new Vector3(15,15.2f,-21);desiredLook=new Vector3(-.6f,.3f,.2f);if(selected==1)desiredCamera=new Vector3(11.5f,15,-23);else if(selected==2)desiredCamera=new Vector3(17.5f,14.5f,-19);}
   float damping=Exploring?5:1.3f;StoryCamera.transform.position=Vector3.Lerp(StoryCamera.transform.position,desiredCamera,1-Mathf.Exp(-Time.unscaledDeltaTime*damping));currentLook=Vector3.Lerp(currentLook,desiredLook,1-Mathf.Exp(-Time.unscaledDeltaTime*damping));StoryCamera.transform.LookAt(currentLook);
   StoryCamera.fieldOfView=Mathf.Lerp(StoryCamera.fieldOfView,Exploring?Mathf.Lerp(40,48,Mathf.InverseLerp(2.2f,4.9f,distance)):36,1-Mathf.Exp(-Time.unscaledDeltaTime*3));
  }
  static Transform Find(Transform root,string name){foreach(var t in root.GetComponentsInChildren<Transform>())if(t.name==name)return t;return null;}
  IEnumerator AutomatedTour(string output)
  {
   Directory.CreateDirectory(output);yield return new WaitForSeconds(7);float menuFps=averageFps;ScreenCapture.CaptureScreenshot(Path.Combine(output,"01-invitation.png"));yield return new WaitForSeconds(2);
   bool menuKeyboard=false;if(Keyboard.current!=null){InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.Enter));yield return new WaitForSeconds(.15f);InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return new WaitForSeconds(.3f);menuKeyboard=started;}if(!started)StartJourney(false);
   yield return new WaitForSeconds(5);float overviewFps=averageFps;ScreenCapture.CaptureScreenshot(Path.Combine(output,"02-island.png"));yield return new WaitForSeconds(1);
   Logic.SetLamp(0,0,true,true);yield return new WaitForSeconds(2);ScreenCapture.CaptureScreenshot(Path.Combine(output,"03-path-solved.png"));yield return new WaitForSeconds(.4f);Logic.Advance();yield return new WaitForSeconds(2);
   Logic.SetLamp(1,0,false,true);yield return new WaitForSeconds(2);ScreenCapture.CaptureScreenshot(Path.Combine(output,"04-window-solved.png"));yield return new WaitForSeconds(.4f);Logic.Advance();yield return new WaitForSeconds(2);
   Logic.SetLamp(1,1,true,true);Logic.SetLamp(2,0,false,true);Logic.SetLamp(0,0,false,true);yield return new WaitForSeconds(4);ScreenCapture.CaptureScreenshot(Path.Combine(output,"05-harbor-solved.png"));
   bool completed=Logic.Current.CanAdvance;yield return new WaitForSeconds(.4f);Logic.Advance();yield return new WaitForSeconds(6);ScreenCapture.CaptureScreenshot(Path.Combine(output,"06-stars-return.png"));yield return new WaitForSeconds(2);
   HUD.ReturnToIsland?.Invoke();yield return new WaitForSeconds(6);var walkStart=traveler.transform.position;
   if(Keyboard.current!=null){InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.W));yield return new WaitForSeconds(1.3f);InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return new WaitForSeconds(.3f);}
   float moved=Vector3.Distance(walkStart,traveler.transform.position);float walkingFps=averageFps;ScreenCapture.CaptureScreenshot(Path.Combine(output,"07-walking.png"));yield return new WaitForSeconds(1);
   bool scrollZoomWorks=false;float scrollStepMetres=0;
   if(Mouse.current!=null){float initialDistance=distance;InputSystem.QueueDeltaStateEvent(Mouse.current.scroll,new Vector2(0,1));yield return null;yield return null;scrollStepMetres=initialDistance-distance;InputSystem.QueueDeltaStateEvent(Mouse.current.scroll,new Vector2(0,-1));yield return null;yield return null;scrollZoomWorks=Mathf.Abs(scrollStepMetres-.35f)<.001f&&Mathf.Abs(distance-initialDistance)<.001f;}
   yaw=155;pitch=9;distance=2.65f;yield return new WaitForSeconds(3);float portraitFps=averageFps;ScreenCapture.CaptureScreenshot(Path.Combine(output,"09-traveler-portrait.png"));yield return new WaitForSeconds(.5f);yaw=0;pitch=12;distance=4.9f;
   // Inspect actual Unity-deformed soles after the portrait FPS sample. This
   // one-shot diagnostic is outside the performance sampling windows.
   int riggedSoles=0,soleGroundSamples=0;float minSoleClearance=float.PositiveInfinity;
   foreach(var skin in traveler.GetComponentsInChildren<SkinnedMeshRenderer>())if(skin.name.StartsWith("BootSole_")){
    var baked=new Mesh();skin.BakeMesh(baked);riggedSoles++;
    foreach(var vertex in baked.vertices){var p=skin.transform.TransformPoint(vertex);if(Physics.Raycast(p+Vector3.up,Vector3.down,out var hit,2,1<<8,QueryTriggerInteraction.Ignore)){minSoleClearance=Mathf.Min(minSoleClearance,p.y-hit.point.y);soleGroundSamples++;}}
    Destroy(baked);
   }
   HUD.ShowSettings(true);yield return new WaitForSeconds(.2f);var pauseStart=traveler.transform.position;
   if(Keyboard.current!=null){InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.W));yield return new WaitForSeconds(.6f);InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return new WaitForSeconds(.2f);}
   bool pauseStopsMovement=Vector3.Distance(pauseStart,traveler.transform.position)<.02f;HUD.ShowSettings(false);yield return new WaitForSeconds(.2f);var resumeStart=traveler.transform.position;
   if(Keyboard.current!=null){InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.W));yield return new WaitForSeconds(.6f);InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return new WaitForSeconds(.2f);}
   bool resumesMovement=Vector3.Distance(resumeStart,traveler.transform.position)>.5f;
   float measuredFps=averageFps;if(Keyboard.current!=null){InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState(Key.Tab));yield return new WaitForSeconds(.15f);InputSystem.QueueStateEvent(Keyboard.current,new KeyboardState());yield return new WaitForSeconds(.3f);}bool endingReturnWorks=finished&&!Exploring&&Logic.Phase==GamePhase.Epilogue;
   var cabinProbe=traveler.ResolveMotion(new Vector3(-4.1f,.08f,1.8f),new Vector3(0,0,2));bool cabinCollisionWorks=cabinProbe.z<2.8f&&cabinProbe.z>1.8f;
   var boulderProbe=traveler.ResolveMotion(new Vector3(0,.08f,-5.15f),new Vector3(-1.5f,0,0));bool boulderCollisionWorks=boulderProbe.x>-.7f&&boulderProbe.x<-.2f;
   WriteHeroBoulderChecks(output);
   bool observatoryGroundingWorks=Physics.Raycast(new Vector3(.85f,2,.65f),Vector3.down,out var observatoryGround,3,1<<8)&&observatoryGround.collider.name=="Observatory walkable steps"&&observatoryGround.point.y>=.255f&&observatoryGround.point.y<=.305f;
   bool decorativeLeavesExcluded=true;foreach(var collider in island.GetComponentsInChildren<Collider>())if(collider.name=="Garden_CreepingMeadowLeaves")decorativeLeavesExcluded=false;
   bool pierGroundingWorks=true;foreach(float x in new[]{6.785f,9.59f,9.7175f})pierGroundingWorks&=Physics.Raycast(new Vector3(x,2,-3.35f),Vector3.down,out var pierGround,3,1<<8)&&pierGround.collider.name=="Pier walkable deck"&&Mathf.Abs(pierGround.point.y-.17f)<.001f;
   var pierLeft=traveler.ResolveMotion(new Vector3(7.35f,.20f,-3.35f),new Vector3(0,0,-.8f));var pierRight=traveler.ResolveMotion(new Vector3(7.35f,.20f,-3.35f),new Vector3(0,0,.8f));
   bool pierRailCollisionWorks=pierLeft.z> -3.85f&&pierLeft.z< -3.35f&&pierRight.z< -2.85f&&pierRight.z> -3.35f;
   var instrumentProbe=traveler.ResolveMotion(new Vector3(0,.29f,-.7f),new Vector3(0,0,1.1f));bool observatoryInstrumentCollisionWorks=instrumentProbe.z>-.7f&&instrumentProbe.z<.2f;
   bool walkwayGroundingWorks=false;
   foreach(var ground in island.GetComponentsInChildren<MeshCollider>())if(ground.name.Contains("Walkways")){
    var vertices=ground.sharedMesh.vertices;var triangles=ground.sharedMesh.triangles;
    for(int t=0;t<triangles.Length;t+=3){var a=ground.transform.TransformPoint(vertices[triangles[t]]);var b=ground.transform.TransformPoint(vertices[triangles[t+1]]);var c=ground.transform.TransformPoint(vertices[triangles[t+2]]);if(Mathf.Abs(Vector3.Cross(b-a,c-a).normalized.y)<.8f)continue;var p=(a+b+c)/3; if(Physics.Raycast(p+Vector3.up,Vector3.down,out var surface,2,1<<8)&&surface.collider==ground){walkwayGroundingWorks=true;break;}}
   }
   HUD.Restart?.Invoke();yield return new WaitForSeconds(2);bool restartWorks=Logic.Phase==GamePhase.Path&&!Exploring;ScreenCapture.CaptureScreenshot(Path.Combine(output,"08-restarted.png"));yield return new WaitForSeconds(.5f);
   File.WriteAllText(Path.Combine(output,"runtime-results.json"),"{\"game\":\"Borrowed Light\",\"puzzleCompleted\":"+(completed?"true":"false")+",\"menuKeyboardStart\":"+(menuKeyboard?"true":"false")+",\"walkingDistance\":"+moved.ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+",\"pauseStopsMovement\":"+(pauseStopsMovement?"true":"false")+",\"resumeMovement\":"+(resumesMovement?"true":"false")+",\"restartWorks\":"+(restartWorks?"true":"false")+",\"fpsAtFinalView\":"+measuredFps.ToString("F1",System.Globalization.CultureInfo.InvariantCulture)+",\"width\":"+Screen.width+",\"height\":"+Screen.height+",\"gpu\":\""+SystemInfo.graphicsDeviceName+"\"}");
   string reportPath=Path.Combine(output,"runtime-results.json");string json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"endingReturnWorks\":"+(endingReturnWorks?"true":"false")+",\"cabinCollisionWorks\":"+(cabinCollisionWorks?"true":"false")+",\"fpsSamples\":{\"menu\":"+menuFps.ToString("F1",System.Globalization.CultureInfo.InvariantCulture)+",\"overview\":"+overviewFps.ToString("F1",System.Globalization.CultureInfo.InvariantCulture)+",\"walking\":"+walkingFps.ToString("F1",System.Globalization.CultureInfo.InvariantCulture)+",\"portrait\":"+portraitFps.ToString("F1",System.Globalization.CultureInfo.InvariantCulture)+"}}";File.WriteAllText(reportPath,json);
   json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"walkwayGroundingWorks\":"+(walkwayGroundingWorks?"true":"false")+"}";File.WriteAllText(reportPath,json);
   json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"boulderCollisionWorks\":"+(boulderCollisionWorks?"true":"false")+",\"riggedSoles\":"+riggedSoles+",\"soleGroundSamples\":"+soleGroundSamples+",\"minimumIdleSoleClearanceMetres\":"+(soleGroundSamples>0?minSoleClearance.ToString("F6",System.Globalization.CultureInfo.InvariantCulture):"null")+"}";File.WriteAllText(reportPath,json);
   json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"observatoryGroundingWorks\":"+(observatoryGroundingWorks?"true":"false")+",\"observatoryInstrumentCollisionWorks\":"+(observatoryInstrumentCollisionWorks?"true":"false")+"}";File.WriteAllText(reportPath,json);
   json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"decorativeLeavesExcluded\":"+(decorativeLeavesExcluded?"true":"false")+",\"pierGroundingWorks\":"+(pierGroundingWorks?"true":"false")+",\"pierRailCollisionWorks\":"+(pierRailCollisionWorks?"true":"false")+"}";File.WriteAllText(reportPath,json);
   json=File.ReadAllText(reportPath);json=json.Substring(0,json.Length-1)+",\"scrollZoomWorks\":"+(scrollZoomWorks?"true":"false")+",\"normalizedScrollStepMetres\":"+scrollStepMetres.ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+"}";File.WriteAllText(reportPath,json);
   yield return new WaitForSeconds(2);Application.Quit();
  }
 }
}
