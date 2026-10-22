using System;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;

namespace BorrowedLight
{
 public sealed class StoryHUD : MonoBehaviour
 {
  public Action Begin,Resume,TurnLeft,TurnRight,ChangeShade,Continue,Restart,ToggleSound,ToggleExplore,ReturnToIsland;
  public Action<int> ChooseLamp;
  Canvas canvas; Font font; RectTransform root;
  GameObject menu,playing,ending,settings;
  Text chapterTitle,chapterNumber,story,objective,lightStatus,skyStatus,hint,soundLabel,modeLabel,endText,toast,puzzleHint;
  Button[] lampButtons=new Button[3];GameObject dialoguePanel,controlPanel;
  Button nextButton,resumeButton;Image veil; CanvasGroup toastGroup;float toastUntil;
  readonly Color ink=new Color(.88f,.89f,.85f),gold=new Color(.94f,.74f,.39f),muted=new Color(.58f,.69f,.72f);
  public bool IsMenu {get;private set;}=true;
  public bool IsSettings=>settings!=null&&settings.activeSelf;
  public void Create()
  {
   font=Resources.Load<Font>("Fonts/StorySerif");
   if(font==null)font=Font.CreateDynamicFontFromOSFont(new[]{"Microsoft YaHei","Georgia","Arial"},28);
   canvas=gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=20;
   var scaler=gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1920,1080);scaler.matchWidthOrHeight=0;
   gameObject.AddComponent<GraphicRaycaster>();root=transform as RectTransform;
   if(FindAnyObjectByType<EventSystem>()==null){var es=new GameObject("Story Input");es.AddComponent<EventSystem>();es.AddComponent<InputSystemUIInputModule>();}
   EventSystem.current.sendNavigationEvents=false;
   menu=Panel("The invitation",root,Vector2.zero,Vector2.one,Vector2.zero,Vector2.zero,Color.clear).gameObject;
   Label("BORROWED LIGHT",menu.transform,120,76,650,35,16,gold,FontStyle.Normal,TextAnchor.UpperLeft,4);
   Line(menu.transform,120,126,105,1,new Color(gold.r,gold.g,gold.b,.65f));
   Label("借 光 岛",menu.transform,112,255,720,150,108,ink);
   Label("把星空，还给夜晚。",menu.transform,126,429,620,70,31,ink);
   Label("有一座岛，借走了所有的星光。\n今晚，替每一个晚归的人，留一盏恰好的灯。",menu.transform,128,535,620,105,20,muted,FontStyle.Normal,TextAnchor.UpperLeft,1.6f);
   var start=TextButton("启 程    →",menu.transform,128,718,270,70,26,()=>Begin?.Invoke());
   AddButtonFrame(start,gold);
   resumeButton=TextButton("继续上次的旅程",menu.transform,128,808,320,40,18,()=>Resume?.Invoke());
   Label("一则可以亲手改变的星空童话",menu.transform,128,973,600,30,16,muted);
   Label("第一卷   /   守夜人的来信",menu.transform,1400,986,410,30,15,muted,FontStyle.Normal,TextAnchor.UpperRight);
   playing=Panel("The journey",root,Vector2.zero,Vector2.one,Vector2.zero,Vector2.zero,Color.clear).gameObject;
   Label("借 光 岛",playing.transform,64,46,360,50,28,ink);
   chapterNumber=Label("CHAPTER 01",playing.transform,67,105,450,30,13,gold);
   chapterTitle=Label("让光，落在需要的地方",playing.transform,65,148,620,55,28,ink);
   objective=Label("",playing.transform,67,217,610,90,18,muted);
   skyStatus=Label("夜空正在等你",playing.transform,1375,52,475,50,20,gold,FontStyle.Normal,TextAnchor.UpperRight);
   Pin(skyStatus.rectTransform,new Vector2(1,1),new Vector2(1,1),new Vector2(-64,-52));skyStatus.rectTransform.sizeDelta=new Vector2(750,80);
   soundLabel=TextButton("声音  开",root,1750,116,105,36,15,()=>ToggleSound?.Invoke()).GetComponentInChildren<Text>();
   var soundText=soundLabel.rectTransform;soundText.anchorMin=soundText.anchorMax=new Vector2(0,1);
   Pin(soundLabel.transform.parent as RectTransform,new Vector2(1,1),new Vector2(1,1),new Vector2(-65,-116));
   var settingButton=TextButton("设置",root,1750,158,105,36,15,()=>ShowSettings(!IsSettings));
   Pin(settingButton.GetComponent<RectTransform>(),new Vector2(1,1),new Vector2(1,1),new Vector2(-65,-158));
   for(int i=0;i<3;i++){int lamp=i;var b=TextButton("0"+(i+1),playing.transform,67+i*72,335,56,44,18,()=>ChooseLamp?.Invoke(lamp));lampButtons[i]=b;AddButtonFrame(b,new Color(gold.r,gold.g,gold.b,.30f));}
   puzzleHint=Label("",playing.transform,67,402,545,120,17,muted,FontStyle.Normal,TextAnchor.UpperLeft,1.3f);
   var bottom=Panel("The lamp desk",playing.transform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,0),new Vector2(770,100),new Color(.018f,.045f,.065f,.88f));
   bottom.pivot=new Vector2(.5f,0);bottom.anchoredPosition=new Vector2(0,38);
   controlPanel=bottom.gameObject;
   lightStatus=Label("",bottom,25,16,340,33,18,ink);
   TextButton("← 转向",bottom,28,57,115,30,17,()=>TurnLeft?.Invoke());
   TextButton("转向 →",bottom,165,57,115,30,17,()=>TurnRight?.Invoke());
   TextButton("切换灯罩  SPACE",bottom,410,35,325,42,18,()=>ChangeShade?.Invoke());
   Line(bottom,365,19,1,63,new Color(gold.r,gold.g,gold.b,.3f));
   hint=Label("鼠标选择灯具  ·  A / D 转向  ·  空格切换灯罩",playing.transform,560,1014,800,26,14,muted,FontStyle.Normal,TextAnchor.UpperCenter);
   Pin(hint.rectTransform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,12));hint.rectTransform.sizeDelta=new Vector2(1200,26);
   var dialogue=Panel("A voice from the island",playing.transform,new Vector2(0,0),new Vector2(0,0),new Vector2(0,0),new Vector2(440,177),new Color(.018f,.045f,.065f,.78f));
   dialogue.pivot=Vector2.zero;dialogue.anchoredPosition=new Vector2(65,180);
   dialoguePanel=dialogue.gameObject;
   Line(dialogue,0,0,3,177,new Color(gold.r,gold.g,gold.b,.7f));
   story=Label("",dialogue,23,23,390,125,19,ink,FontStyle.Normal,TextAnchor.UpperLeft,1.4f);
   nextButton=TextButton("收下这束星光  →",playing.transform,1400,905,440,60,22,()=>Continue?.Invoke());AddButtonFrame(nextButton,gold);
   Pin(nextButton.GetComponent<RectTransform>(),new Vector2(1,0),new Vector2(1,0),new Vector2(-65,167));
   modeLabel=TextButton("自由漫步  TAB",playing.transform,1490,985,350,40,16,()=>ToggleExplore?.Invoke()).GetComponentInChildren<Text>();
   Pin(modeLabel.transform.parent as RectTransform,new Vector2(1,0),new Vector2(1,0),new Vector2(-65,73));
   ending=Panel("The stars return",root,Vector2.zero,Vector2.one,Vector2.zero,Vector2.zero,Color.clear).gameObject;
   Label("THE NIGHT REMEMBERS",ending.transform,120,160,920,36,16,gold);
   Label("原来，星星一直都在。",ending.transform,112,254,1330,120,67,ink);
   endText=Label("",ending.transform,124,405,800,190,23,ink,FontStyle.Normal,TextAnchor.UpperLeft,1.7f);
   var replay=TextButton("再借一夜星光  →",ending.transform,124,731,340,65,23,()=>Restart?.Invoke());AddButtonFrame(replay,gold);
   TextButton("回到岛上",ending.transform,124,821,340,45,19,()=>ReturnToIsland?.Invoke());
   Label("把灯留给归人，把夜留给星辰。",ending.transform,124,973,850,40,18,muted);
   settings=Panel("Pause",root,Vector2.zero,Vector2.one,Vector2.zero,Vector2.zero,new Color(.008f,.022f,.04f,.94f)).gameObject;
   Label("片刻，听一听风。",settings.transform,575,260,900,90,48,ink);
   TextButton("继续旅程",settings.transform,690,430,550,60,26,()=>ShowSettings(false));
   TextButton("声音 开 / 关",settings.transform,690,530,550,60,22,()=>ToggleSound?.Invoke());
   TextButton("重新开始",settings.transform,690,630,550,60,22,()=>{ShowSettings(false);Restart?.Invoke();});
#if UNITY_WEBGL && !UNITY_EDITOR
   Label("旅程会自动保存，可随时关闭本页。",settings.transform,690,730,550,60,18,muted,FontStyle.Normal,TextAnchor.MiddleCenter);
#else
   TextButton("退出游戏",settings.transform,690,730,550,60,20,()=>Application.Quit());
#endif
   var t=Panel("A small thought",root,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,0),new Vector2(900,74),new Color(.025f,.065f,.09f,.93f));t.pivot=new Vector2(.5f,1);t.anchoredPosition=new Vector2(0,-50);
   toast=Label("",t,20,20,860,40,20,ink,FontStyle.Normal,TextAnchor.MiddleCenter);toastGroup=t.gameObject.AddComponent<CanvasGroup>();toastGroup.alpha=0;toastGroup.blocksRaycasts=false;
   var fade=Panel("Curtain",root,Vector2.zero,Vector2.one,Vector2.zero,Vector2.zero,new Color(.008f,.02f,.04f,1));veil=fade.GetComponent<Image>();veil.raycastTarget=false;
   settings.SetActive(false);playing.SetActive(false);ending.SetActive(false);
  }
  public void SetResumeAvailable(bool yes){resumeButton.gameObject.SetActive(yes);}
  public void ShowMenu(){IsMenu=true;menu.SetActive(true);playing.SetActive(false);ending.SetActive(false);}
  public void ShowPlay(){IsMenu=false;menu.SetActive(false);playing.SetActive(true);ending.SetActive(false);}
  public void ShowEnding(string text=null){IsMenu=false;menu.SetActive(false);playing.SetActive(false);ending.SetActive(true);if(text!=null)endText.text=text;}
  public void ShowSettings(bool yes){settings.SetActive(yes);}
  public void SetChapter(int index,string title,string task,string dialogue){chapterNumber.text="CHAPTER 0"+index+"    /    三封守夜人的来信";chapterTitle.text=title;objective.text=task;story.text=dialogue;}
  public void SetLamp(int index,int direction,bool wide){lightStatus.text="第 "+(index+1)+" 盏灯  ·  "+(wide?"宽光":"窄光")+"  /  "+StoryData.DirectionName(index,direction);}
  public void SetSky(float progress,int satisfied,int total,int pollution=0,int budget=1){skyStatus.text="星空清晰度  "+Mathf.RoundToInt(progress*100)+"%    /    "+satisfied+" / "+total+" 处安心的灯光\n散光 "+pollution+" / "+budget+"   ·   留住一束宽光的夜晚";}
  public void SetPuzzleHint(string text,int unlocked){puzzleHint.text=text;for(int i=0;i<3;i++){lampButtons[i].interactable=i<unlocked;var group=lampButtons[i].GetComponent<CanvasGroup>();if(group==null)group=lampButtons[i].gameObject.AddComponent<CanvasGroup>();group.alpha=i<unlocked?1:.23f;}}
  public void SetContinue(bool show){nextButton.gameObject.SetActive(show);}
  public void SetExploring(bool exploring){modeLabel.text=exploring?"回到观景  TAB":"自由漫步  TAB";hint.text=exploring?"W A S D 漫步  ·  按住右键环顾  ·  E 调整附近的灯  ·  TAB 返回":"鼠标选择灯具  ·  A / D 转向  ·  空格切换灯罩";controlPanel.SetActive(!exploring);dialoguePanel.SetActive(!exploring);puzzleHint.gameObject.SetActive(!exploring);objective.gameObject.SetActive(!exploring);chapterTitle.gameObject.SetActive(!exploring);foreach(var b in lampButtons)b.gameObject.SetActive(!exploring);}
  public void SetSound(bool on){soundLabel.text=on?"声音  开":"声音  关";}
  public void Toast(string text,float seconds=4){toast.text=text;toastUntil=Time.unscaledTime+seconds;}
  public void SetCurtain(float alpha){if(veil!=null)veil.color=new Color(.008f,.02f,.04f,alpha);}
  void Update(){if(toastGroup!=null)toastGroup.alpha=Mathf.MoveTowards(toastGroup.alpha,Time.unscaledTime<toastUntil?1:0,Time.unscaledDeltaTime*2);}
  public bool PointerOverUI()=>EventSystem.current!=null&&EventSystem.current.IsPointerOverGameObject();
  RectTransform Panel(string name,Transform parent,Vector2 amin,Vector2 amax,Vector2 pos,Vector2 size,Color color)
  {var o=new GameObject(name,typeof(RectTransform));o.transform.SetParent(parent,false);var r=(RectTransform)o.transform;r.anchorMin=amin;r.anchorMax=amax;r.anchoredPosition=pos;r.sizeDelta=size;r.pivot=new Vector2(.5f,.5f);var im=o.AddComponent<Image>();im.color=color;im.raycastTarget=color.a>.1f;return r;}
  Text Label(string text,Transform parent,float x,float y,float w,float h,int size,Color color,FontStyle style=FontStyle.Normal,TextAnchor align=TextAnchor.UpperLeft,float line=1.2f)
  {var o=new GameObject("Text "+text,typeof(RectTransform));o.transform.SetParent(parent,false);var r=(RectTransform)o.transform;r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);var t=o.AddComponent<Text>();t.font=font;t.text=text;t.fontSize=size;t.color=color;t.fontStyle=style;t.alignment=align;t.lineSpacing=line;t.raycastTarget=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Overflow;return t;}
  Button TextButton(string text,Transform parent,float x,float y,float w,float h,int size,Action action)
  {var o=new GameObject(text,typeof(RectTransform));o.transform.SetParent(parent,false);var r=(RectTransform)o.transform;r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);var im=o.AddComponent<Image>();im.color=new Color(.08f,.13f,.16f,.12f);var b=o.AddComponent<Button>();b.targetGraphic=im;var cs=b.colors;cs.normalColor=Color.white;cs.highlightedColor=new Color(1,.88f,.6f,1);cs.pressedColor=new Color(.8f,.7f,.5f,1);cs.selectedColor=cs.normalColor;b.colors=cs;b.onClick.AddListener(()=>action?.Invoke());var t=Label(text,o.transform,0,0,w,h,size,gold,FontStyle.Normal,TextAnchor.MiddleCenter);return b;}
  void Line(Transform parent,float x,float y,float w,float h,Color color){var r=Panel("A fine gold line",parent,new Vector2(0,1),new Vector2(0,1),new Vector2(x,-y),new Vector2(w,h),color);r.pivot=new Vector2(0,1);r.GetComponent<Image>().raycastTarget=false;}
  void AddButtonFrame(Button button,Color color){var r=button.GetComponent<RectTransform>();Line(r,0,0,r.sizeDelta.x,1,color);Line(r,0,r.sizeDelta.y-1,r.sizeDelta.x,1,color);}
  static void Pin(RectTransform rect,Vector2 anchor,Vector2 pivot,Vector2 position){rect.anchorMin=rect.anchorMax=anchor;rect.pivot=pivot;rect.anchoredPosition=position;}
 }
}
