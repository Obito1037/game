using UnityEngine;
using UnityEngine.InputSystem;
using System.Collections.Generic;

namespace BorrowedLight
{
 public sealed class TravelerMotor : MonoBehaviour
 {
  public bool CanMove;public Camera ViewCamera;public float WalkSpeed=2.3f;
  Transform visual,leftLeg,rightLeg,leftArm,rightArm,head,scarf,blinkLeft,blinkRight;Vector3 lastPosition;float walkTime;float blinkTime=-1,nextBlink=3.4f;
  Vector3 headUp,headRight,headForward;float headTurn;
  Dictionary<Transform,Quaternion> bind=new Dictionary<Transform,Quaternion>();
  public float Speed {get;private set;}
  public void Bind(Transform model)
  {visual=model;leftLeg=Find(model,"Leg_L");rightLeg=Find(model,"Leg_R");leftArm=Find(model,"Arm_L");rightArm=Find(model,"Arm_R");head=Find(model,"Head");scarf=Find(model,"ScarfTail");blinkLeft=Find(model,"Blink_L");blinkRight=Find(model,"Blink_R");foreach(var t in new[]{leftLeg,rightLeg,leftArm,rightArm,head,scarf})if(t!=null)bind[t]=t.localRotation;if(head!=null){headUp=head.InverseTransformDirection(transform.up).normalized;headRight=head.InverseTransformDirection(transform.right).normalized;headForward=head.InverseTransformDirection(transform.forward).normalized;}lastPosition=transform.position;}
  static Transform Find(Transform t,string name){foreach(var child in t.GetComponentsInChildren<Transform>(true))if(child.name==name)return child;return null;}
  void Update()
  {
   var keyboard=Keyboard.current;var move=Vector2.zero;float turnHint=0;
   if(CanMove&&keyboard!=null){if(keyboard.wKey.isPressed||keyboard.upArrowKey.isPressed)move.y++;if(keyboard.sKey.isPressed||keyboard.downArrowKey.isPressed)move.y--;if(keyboard.aKey.isPressed||keyboard.leftArrowKey.isPressed)move.x--;if(keyboard.dKey.isPressed||keyboard.rightArrowKey.isPressed)move.x++;}
   if(move.sqrMagnitude>0){move.Normalize();var forward=Vector3.ProjectOnPlane(ViewCamera.transform.forward,Vector3.up).normalized;var right=Vector3.ProjectOnPlane(ViewCamera.transform.right,Vector3.up).normalized;var direction=forward*move.y+right*move.x;var p=ResolveMotion(transform.position,direction*(WalkSpeed*Time.deltaTime));var flat=new Vector2(p.x,p.z);if(flat.magnitude>8.1f&&!(p.x>5.2f&&p.x<9.8f&&p.z>-3.9f&&p.z<-2.8f)){flat=flat.normalized*8.1f;p.x=flat.x;p.z=flat.y;}p.y=Ground(p);transform.position=p;turnHint=Mathf.Clamp(Vector3.SignedAngle(transform.forward,direction,Vector3.up)*.16f,-4,4);transform.rotation=Quaternion.Slerp(transform.rotation,Quaternion.LookRotation(direction),Time.deltaTime*10);}
   Speed=Mathf.Lerp(Speed,(transform.position-lastPosition).magnitude/Mathf.Max(.001f,Time.deltaTime),Time.deltaTime*10);lastPosition=transform.position;walkTime+=Time.deltaTime*(Speed>.1f?8:1.3f);
   float gait=Mathf.Clamp01(Speed/WalkSpeed);float swing=Mathf.Sin(walkTime)*gait;float breath=Mathf.Sin(Time.time*1.8f);
   SetRotation(leftLeg,swing*19,0,0);SetRotation(rightLeg,-swing*19,0,0);
   // The rigid shoulder pivots keep a small asymmetry without inventing elbow joints.
   // The lantern arm retains clearance beside the coat and has a gentler walking arc.
   SetRotation(leftArm,1.5f-swing*9+breath*.35f,0,-.8f);
   SetRotation(rightArm,-2.5f+swing*5+breath*.2f,0,1);
   headTurn=Mathf.Lerp(headTurn,turnHint,1-Mathf.Exp(-Time.deltaTime*5));
   if(head!=null){float idle=1-gait*.65f;float glance=headTurn+Mathf.Sin(Time.time*.37f)*1.8f*idle;float nod=breath*.55f;float tilt=Mathf.Sin(Time.time*.43f+.7f)*.65f*idle;head.localRotation=bind[head]*Quaternion.AngleAxis(glance,headUp)*Quaternion.AngleAxis(nod,headRight)*Quaternion.AngleAxis(tilt,headForward);}
   SetRotation(scarf,Mathf.Sin(Time.time*1.8f)*4-8,0,Mathf.Sin(Time.time*1.1f)*7);
   if(visual!=null){var p=visual.localPosition;p.y=Mathf.Abs(swing)*.025f+Mathf.Sin(Time.time*1.8f)*.006f;visual.localPosition=p;}
   if(Time.time>=nextBlink&&blinkTime<0)blinkTime=0;
   if(blinkTime>=0){blinkTime+=Time.deltaTime;float close=blinkTime<.08f?blinkTime/.08f:1-(blinkTime-.08f)/.1f;float s=Mathf.Lerp(.001f,1,Mathf.Clamp01(close));var scale=new Vector3(s,s,1);if(blinkLeft!=null)blinkLeft.localScale=scale;if(blinkRight!=null)blinkRight.localScale=scale;if(blinkTime>=.18f){blinkTime=-1;nextBlink=Time.time+Random.Range(3.2f,5.8f);}}
  }
  void SetRotation(Transform t,float x,float y,float z){if(t!=null)t.localRotation=bind[t]*Quaternion.Euler(x,y,z);}
  public Vector3 ResolveMotion(Vector3 position,Vector3 motion)
  {
   // A short capsule sweep keeps the coat clear of solid furniture and walls.
   for(int i=0;i<2&&motion.sqrMagnitude>.0000001f;i++)
   {
    float length=motion.magnitude;var direction=motion/length;
    if(!Physics.CapsuleCast(position+Vector3.up*.28f,position+Vector3.up*1.03f,.22f,direction,out var hit,length+.025f,1<<9,QueryTriggerInteraction.Ignore)){position+=motion;break;}
    var travel=direction*Mathf.Max(0,hit.distance-.025f);position+=travel;
    motion=Vector3.ProjectOnPlane(motion-travel,hit.normal);motion.y=0;
   }
   return position;
  }
  float Ground(Vector3 p){if(Physics.Raycast(new Vector3(p.x,6,p.z),Vector3.down,out var hit,12,1<<8))return hit.point.y+.03f;return .06f;}
 }
}
