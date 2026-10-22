using System.Collections.Generic;
using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace BorrowedLight
{
 public sealed class WorldAtmosphere : MonoBehaviour
 {
  public float Night=.35f;public float Wind=1;
  Material sky;Light sun,fill;Transform moon;ParticleSystem motes;List<Transform> drifters=new List<Transform>();List<Vector3> driftOrigins=new List<Vector3>();
  Transform constellation;
  static readonly Color Gold=new Color(1,.69f,.28f);
  public void Create(Camera camera)
  {
   sky=Resources.Load<Material>("Materials/CelestialSky");if(sky!=null){sky=new Material(sky);var nebula=Resources.Load<Texture2D>("Textures/Nebula");if(nebula!=null){sky.SetTexture("_Nebula",nebula);sky.SetFloat("_PaintBlend",.42f);}RenderSettings.skybox=sky;}
   RenderSettings.ambientMode=AmbientMode.Trilight;RenderSettings.ambientSkyColor=new Color(.50f,.59f,.70f);RenderSettings.ambientEquatorColor=new Color(.37f,.45f,.52f);RenderSettings.ambientGroundColor=new Color(.23f,.28f,.33f);
   RenderSettings.fog=true;RenderSettings.fogColor=new Color(.025f,.065f,.085f);RenderSettings.fogMode=FogMode.Exponential;RenderSettings.fogDensity=.0025f;
   sun=NewLight("The light of the moon",LightType.Directional,new Color(.773f,.816f,.867f),.8f,Vector3.zero);sun.transform.rotation=Quaternion.Euler(38,-35,0);sun.shadows=LightShadows.Soft;sun.shadowBias=.035f;sun.shadowNormalBias=.22f;
   fill=NewLight("Blue hour",LightType.Directional,new Color(.32f,.57f,.85f),.35f,Vector3.zero);fill.transform.rotation=Quaternion.Euler(22,135,0);fill.shadows=LightShadows.None;
   var warmth=NewLight("The warmth of remembered stories",LightType.Directional,new Color(1,.878f,.741f),.18f,Vector3.zero);warmth.transform.rotation=Quaternion.Euler(24,50,0);
   var window=NewLight("Someone is still awake",LightType.Point,new Color(1,.72f,.4f),1.25f,new Vector3(-4.1f,2.3f,2.6f));window.range=4.5f;
   var vol=new GameObject("A little cinematic light").AddComponent<Volume>();vol.isGlobal=true;vol.priority=10;vol.profile=ScriptableObject.CreateInstance<VolumeProfile>();
   var bloom=vol.profile.Add<Bloom>(true);bloom.threshold.value=1.2f;bloom.intensity.value=.12f;bloom.scatter.value=.55f;
   var tone=vol.profile.Add<Tonemapping>(true);tone.mode.value=TonemappingMode.ACES;
   var grading=vol.profile.Add<ColorAdjustments>(true);grading.postExposure.value=.1f;grading.contrast.value=7;grading.saturation.value=4;
   var vignette=vol.profile.Add<Vignette>(true);vignette.intensity.value=.18f;vignette.smoothness.value=.55f;vignette.color.value=new Color(.025f,.04f,.075f);
   camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
   CreateMoon();CreateClouds();CreateStars();CreateFireflies();CreateOrbits();
  }
  void CreateMoon()
  {
   moon=new GameObject("The faraway moon").transform;moon.position=new Vector3(-4,3,27);
   var moonMat=Resources.Load<Material>("Materials/MoonPaint");if(moonMat==null)moonMat=MaterialFor(new Color(.82f,.79f,.65f),.15f);
   var body=Sphere("A silver world",moon,Vector3.zero,new Vector3(6.3f,6.3f,6.3f),moonMat);
   var gold=MaterialFor(new Color(.74f,.53f,.27f),.5f);
   var ring=Ring("The moon's brass orbit",moon,4.6f,.018f,gold);ring.transform.localRotation=Quaternion.Euler(65,28,24);
  }
  void CreateClouds()
  {
   var cloud=Resources.Load<Material>("Materials/CloudVeil");if(cloud==null)return;var rnd=new System.Random(61);
   for(int i=0;i<9;i++){float a=i*Mathf.PI*2/9;float distance=18+(float)rnd.NextDouble()*8;var cluster=new GameObject("Cloud bank "+i).transform;cluster.SetParent(transform);cluster.position=new Vector3(Mathf.Cos(a)*distance,-6-(float)rnd.NextDouble()*3,Mathf.Sin(a)*distance);cluster.localScale=Vector3.one*(.7f+(float)rnd.NextDouble()*.65f);for(int j=0;j<4;j++)Sphere("Cloud fold",cluster,new Vector3((j-1.5f)*1.9f,(float)rnd.NextDouble()*.7f,(float)rnd.NextDouble()*1.1f),new Vector3(6,2.4f+(float)rnd.NextDouble()*1.3f,4.1f),cloud);drifters.Add(cluster);driftOrigins.Add(cluster.position);}
  }
  void CreateStars()
  {
   var starMat=MaterialFor(new Color(1,.77f,.4f),2.8f);var rnd=new System.Random(17);
   for(int i=0;i<47;i++){var pos=new Vector3((float)rnd.NextDouble()*100-50,(float)rnd.NextDouble()*26+2,(float)rnd.NextDouble()*45+18);var star=new GameObject("A distant star").transform;star.SetParent(transform);star.position=pos;float s=.025f+(float)rnd.NextDouble()*.055f;Sphere("Star",star,Vector3.zero,Vector3.one*s,starMat);if(i%5==0){var h=GameObject.CreatePrimitive(PrimitiveType.Cube);h.name="The star's glint";h.transform.SetParent(star,false);h.transform.localScale=new Vector3(s*6,s*.22f,s*.22f);h.GetComponent<Renderer>().sharedMaterial=starMat;Destroy(h.GetComponent<Collider>());var v=Instantiate(h,star);v.transform.localRotation=Quaternion.Euler(0,0,90);}drifters.Add(star);driftOrigins.Add(pos);}
  }
  void CreateFireflies()
  {
   var go=new GameObject("Letters made of fireflies");go.transform.SetParent(transform);go.transform.position=new Vector3(0,1.5f,0);motes=go.AddComponent<ParticleSystem>();
   var main=motes.main;main.startLifetime=10;main.startSpeed=.12f;main.startSize=new ParticleSystem.MinMaxCurve(.018f,.065f);main.startColor=new ParticleSystem.MinMaxGradient(new Color(1,.85f,.45f,.9f),new Color(.45f,.95f,.9f,.6f));main.maxParticles=240;main.simulationSpace=ParticleSystemSimulationSpace.World;main.prewarm=true;
   var emission=motes.emission;emission.rateOverTime=16;var shape=motes.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=new Vector3(17,4,17);
   var noise=motes.noise;noise.enabled=true;noise.strength=.25f;noise.frequency=.17f;noise.scrollSpeed=.1f;
   var size=motes.sizeOverLifetime;size.enabled=true;size.size=new ParticleSystem.MinMaxCurve(1,new AnimationCurve(new Keyframe(0,0),new Keyframe(.2f,1),new Keyframe(.8f,1),new Keyframe(1,0)));
   var col=motes.colorOverLifetime;col.enabled=true;var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(new Color(1,.78f,.35f),0),new GradientColorKey(new Color(.52f,.86f,.94f),1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.8f,.2f),new GradientAlphaKey(.7f,.75f),new GradientAlphaKey(0,1)});col.color=gradient;
   var renderer=go.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=Resources.Load<Material>("Materials/Firefly");motes.Play();
  }
  void CreateOrbits()
  {
   var material=MaterialFor(new Color(.7f,.52f,.25f),.3f);
   var t=Ring("A thread around the world",transform,12,.019f,material);t.transform.localPosition=new Vector3(0,-3.5f,0);t.transform.localRotation=Quaternion.Euler(8,0,6);
  }
  public void CelebratoryConstellation()
  {
   ClearCelebration();var root=new GameObject("The way home is written in stars").transform;constellation=root;root.position=new Vector3(0,7.4f,5.5f);
   Vector3[] points={new Vector3(-5,0,0),new Vector3(-3,1.7f,0),new Vector3(-1,.6f,0),new Vector3(1,3.6f,0),new Vector3(3,2.4f,0),new Vector3(5,3.5f,0)};
   var mat=MaterialFor(new Color(1,.77f,.37f),3);
   var stars=new List<Transform>();foreach(var p in points){var star=Sphere("A star to guide you",root,p,Vector3.one*.02f,mat);stars.Add(star.transform);}
   var lr=root.gameObject.AddComponent<LineRenderer>();lr.positionCount=2;lr.useWorldSpace=false;lr.SetPosition(0,points[0]);lr.SetPosition(1,points[0]);lr.widthMultiplier=.026f;lr.sharedMaterial=MaterialFor(new Color(.8f,.6f,.32f),1);lr.startColor=lr.endColor=new Color(1,.82f,.4f,.8f);
   StartCoroutine(WriteTheStars(root,points,stars,lr));
  }
  IEnumerator WriteTheStars(Transform root,Vector3[] points,List<Transform> stars,LineRenderer line)
  {
   var go=new GameObject("All the little lights are going home");go.transform.SetParent(root);var particles=go.AddComponent<ParticleSystem>();var main=particles.main;main.startLifetime=12;main.startSpeed=0;main.startSize=.045f;main.maxParticles=160;main.simulationSpace=ParticleSystemSimulationSpace.World;var emission=particles.emission;emission.enabled=false;var shape=particles.shape;shape.enabled=false;go.GetComponent<ParticleSystemRenderer>().sharedMaterial=Resources.Load<Material>("Materials/Firefly");particles.Play();
   var dots=new ParticleSystem.Particle[144];float elapsed=0;
   while(elapsed<6&&root!=null){elapsed+=Time.deltaTime;float progress=Mathf.Clamp01(elapsed/5.5f);for(int i=0;i<dots.Length;i++){float p=Mathf.Clamp01((elapsed-i*.008f)/4.5f);var destination=root.TransformPoint(points[i%points.Length]);float angle=i*2.399963f;var begin=new Vector3(Mathf.Cos(angle)*.7f,.55f,Mathf.Sin(angle)*.7f+.35f);var control=(begin+destination)*.5f+new Vector3(Mathf.Sin(angle)*2,3,Mathf.Cos(angle));dots[i].position=(1-p)*(1-p)*begin+2*(1-p)*p*control+p*p*destination;dots[i].startSize=(.025f+(i%4)*.013f)*(1-p*.6f);dots[i].startColor=new Color(1,.76f,.34f,Mathf.Sin(Mathf.PI*Mathf.Clamp(p,.05f,.95f)));dots[i].remainingLifetime=1;}
    particles.SetParticles(dots,dots.Length);float write=Mathf.Clamp01((progress-.45f)/.55f)*(points.Length-1);int whole=Mathf.FloorToInt(write);line.positionCount=Mathf.Min(points.Length,whole+2);for(int j=0;j<line.positionCount;j++)line.SetPosition(j,j<=whole?points[j]:Vector3.Lerp(points[whole],points[Mathf.Min(whole+1,points.Length-1)],write-whole));for(int j=0;j<stars.Count;j++)stars[j].localScale=Vector3.one*Mathf.Lerp(.01f,.16f,Mathf.Clamp01((write-j+.7f)*2));yield return null;
   }
   if(go!=null)Destroy(go);if(root!=null){line.positionCount=points.Length;line.SetPositions(points);}
  }
  public void ClearCelebration(){if(constellation!=null)Destroy(constellation.gameObject);}
  void Update()
  {
   if(sky!=null)sky.SetFloat("_Night",Night);
   if(sun!=null)sun.intensity=Mathf.Lerp(.8f,.62f,Night);
   for(int i=0;i<drifters.Count;i++){if(drifters[i]==null)continue;var origin=driftOrigins[i];drifters[i].position=origin+new Vector3(Mathf.Sin(Time.time*.035f+i)*.35f,Mathf.Sin(Time.time*.12f+i*.7f)*.10f,0);}
  }
  public static Light NewLight(string name,LightType type,Color color,float intensity,Vector3 pos){var go=new GameObject(name);go.transform.position=pos;var light=go.AddComponent<Light>();light.type=type;light.color=color;light.intensity=intensity;light.range=5;light.shadows=LightShadows.None;return light;}
  public static Material MaterialFor(Color color,float emission=0)
  {var material=new Material(Shader.Find("Universal Render Pipeline/Lit"));material.SetColor("_BaseColor",color);material.SetFloat("_Smoothness",.25f);if(emission>0){material.EnableKeyword("_EMISSION");material.SetColor("_EmissionColor",color*emission);}return material;}
  public static GameObject Sphere(string name,Transform parent,Vector3 local,Vector3 scale,Material mat){var o=GameObject.CreatePrimitive(PrimitiveType.Sphere);o.name=name;o.transform.SetParent(parent,false);o.transform.localPosition=local;o.transform.localScale=scale;o.GetComponent<Renderer>().sharedMaterial=mat;Destroy(o.GetComponent<Collider>());return o;}
  public static GameObject Ring(string name,Transform parent,float radius,float width,Material mat)
  {var o=new GameObject(name);o.transform.SetParent(parent,false);var line=o.AddComponent<LineRenderer>();line.useWorldSpace=false;line.loop=true;line.positionCount=192;line.widthMultiplier=width;line.sharedMaterial=mat;for(int j=0;j<192;j++){float a=j*Mathf.PI*2/192;line.SetPosition(j,new Vector3(Mathf.Cos(a)*radius,0,Mathf.Sin(a)*radius));}return o;}
 }
}
