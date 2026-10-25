Shader "JieGuang/Environment/NightSkyV2"
{
 Properties
 {
  _Zenith("Zenith",Color)=(.009,.018,.043,1)
  _Horizon("Horizon",Color)=(.045,.073,.105,1)
  _EarthDirection("Earth direction",Vector)=(-.30,.15,.94,0)
  _EarthRadius("Earth angular radius",Range(.02,.18))=.066
  _EarthLitFraction("Earth illuminated projected fraction",Range(0,.5))=.065
  _Stars("Stars",Range(0,2))=.95
  _CloudOpacity("Thin cloud opacity",Range(0,.3))=.055
  _EnvTime("Frozen time (-1 uses live time)",Float)=-1
 }
 SubShader
 {
  Tags {"RenderType"="Opaque" "Queue"="Background" "RenderPipeline"="UniversalPipeline"}
  Pass
  {
   Name "NightSkyV2"
   Tags {"LightMode"="SRPDefaultUnlit"}
   Cull Front ZWrite Off ZTest LEqual
   HLSLPROGRAM
   #pragma target 3.5
   #pragma vertex Vert
   #pragma fragment Frag
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   struct A {float4 p:POSITION;};
   struct V {float4 p:SV_POSITION;float3 ws:TEXCOORD0;};
   CBUFFER_START(UnityPerMaterial)
    half4 _Zenith,_Horizon;
    float4 _EarthDirection;
    float _EarthRadius,_EarthLitFraction,_Stars,_CloudOpacity,_EnvTime;
   CBUFFER_END
   V Vert(A a){V o;o.ws=TransformObjectToWorld(a.p.xyz);o.p=TransformWorldToHClip(o.ws);return o;}
   float Hash(float2 p){p=frac(p*float2(.1031,.11369));p+=dot(p,p.yx+19.19);return frac(p.x*p.y*17.17);}
   float Noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(Hash(i),Hash(i+float2(1,0)),f.x),lerp(Hash(i+float2(0,1)),Hash(i+1),f.x),f.y);}
   float Fbm(float2 p){return .57*Noise(p)+.28*Noise(p*2.07+9.3)+.15*Noise(p*4.17-3.7);}
   half4 Frag(V i):SV_Target
   {
    float t=_EnvTime<0?_Time.y:_EnvTime;
    float3 eyeToSky=i.ws-GetCameraPositionWS();
    float3 d=dot(eyeToSky,eyeToSky)>1e-10?SafeNormalize(eyeToSky):float3(0,0,1);
    half3 color=lerp(_Horizon.rgb,_Zenith.rgb,pow(saturate(d.y),.48));
    float2 uv=float2(atan2(d.z,d.x)*.15915494+.5,asin(clamp(d.y,-1,1))*.31830989+.5);
    float2 cells=uv*float2(420,210),cell=floor(cells);
    float seed=Hash(cell),brightness=pow(Hash(cell+7),2);
    float2 starAt=float2(Hash(cell+17.1),Hash(cell+51.7));
    float dist=length((frac(cells)-starAt)*float2(max(.35,cos((uv.y-.5)*3.14159)),1));
    float aa=max(fwidth(dist),.006);
    float core=1-smoothstep(.012,.022+aa,dist);
    float halo=exp2(-dist*dist*2200)*.16;
    float star=(core+halo)*step(.983,seed)*smoothstep(.015,.16,d.y);
    float twinkle=.93+.07*sin(t*(.5+seed)+seed*80);
    color+=star*_Stars*twinkle*(.28+.72*brightness)*lerp(half3(.55,.7,.91),half3(.92,.85,.70),Hash(cell+3));
    // Very low contrast atmospheric wisps, no opaque cloud layer hiding puzzle stars.
    float2 cloudUV=d.xz/(max(.13,d.y)+.24)*2.2+float2(t*.0017,0);
    float cloud=smoothstep(.45,.76,Fbm(cloudUV+Fbm(cloudUV*.37)*1.8));
    float cloudBand=smoothstep(-.04,.06,d.y)*(1-smoothstep(.24,.65,d.y));
    color=lerp(color,lerp(_Horizon.rgb,half3(.13,.17,.22),.18),cloud*cloudBand*_CloudOpacity);
    // MaterialPropertyBlock can bypass Inspector ranges; retain a finite frame for zero
    // direction, an almost vertical direction, and zero/negative radius.
    float3 axis=dot(_EarthDirection.xyz,_EarthDirection.xyz)>1e-10?SafeNormalize(_EarthDirection.xyz):SafeNormalize(float3(-.30,.15,.94));
    float3 referenceAxis=abs(axis.y)>.999?float3(0,0,1):float3(0,1,0);
    float3 right=SafeNormalize(cross(referenceAxis,axis)),up=cross(axis,right);
    float2 q=float2(dot(d,right),dot(d,up))/max(_EarthRadius,.001);
    float rr=dot(q,q),radius=sqrt(rr);
    float disk=(1-smoothstep(.995,1.008,radius))*step(0,dot(d,axis));
    float3 sphereNormal=float3(q.x,q.y,sqrt(saturate(1-rr)));
    // The projected illuminated fraction equals (1+cos(phaseAngle))/2.
    float cosPhase=2*saturate(_EarthLitFraction)-1;
    float sinPhase=sqrt(saturate(1-cosPhase*cosPhase));
    float ndl=dot(sphereNormal,float3(sinPhase,0,cosPhase));
    float lit=smoothstep(-.008,.015,ndl)*disk;
    float cloudEarth=Fbm(q*4.8+Fbm(q*2.1+7)*2.2);
    float cloudFine=Fbm(q*14.7+3);
    float clouds=smoothstep(.44,.7,cloudEarth*.77+cloudFine*.23);
    half3 earthDark=half3(.006,.012,.021)*(.8+.2*clouds);
    half3 earthLight=lerp(half3(.15,.34,.50),half3(.65,.78,.85),clouds);
    float limb=smoothstep(.75,1,radius)*lit;
    color=lerp(color,earthDark,disk);
    color+=earthLight*lit*(.5+.5*sqrt(saturate(ndl)))+half3(.11,.19,.26)*limb;
    return half4(color,1);
   }
   ENDHLSL
  }
 }
 Fallback Off
}
