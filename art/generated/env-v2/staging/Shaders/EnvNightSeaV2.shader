Shader "JieGuang/Environment/NightSeaV2"
{
 Properties
 {
  _Deep("Deep sea",Color)=(.012,.031,.043,1)
  _Shallow("Shallow reflection",Color)=(.042,.087,.101,1)
  _Horizon("Horizon",Color)=(.045,.073,.105,1)
  _WaveStrength("Wave reflection strength",Range(0,.5))=.11
  _ShoreMap("Coast distance (R metres / 8)",2D)="white"{}
  _ShoreRect("Coast map world XZ min and size",Vector)=(-40,-40,80,80)
  _ShoreEnabled("Use baked coast map",Float)=0
  _EnvTime("Frozen time (-1 uses live time)",Float)=-1
 }
 SubShader
 {
  Tags {"RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline"}
  Pass
  {
   Name "NightSeaV2"
   Tags {"LightMode"="UniversalForward"}
   Cull Off ZWrite On
   HLSLPROGRAM
   #pragma target 3.5
   #pragma vertex Vert
   #pragma fragment Frag
   #pragma multi_compile _ _ADDITIONAL_LIGHTS
   #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
   #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
   #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
   #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
   TEXTURE2D(_ShoreMap);SAMPLER(sampler_ShoreMap);
   CBUFFER_START(UnityPerMaterial)
    half4 _Deep,_Shallow,_Horizon;
    float4 _ShoreRect;
    float _WaveStrength,_ShoreEnabled,_EnvTime;
   CBUFFER_END
   struct A{float4 p:POSITION;};
   struct V{float4 p:SV_POSITION;float3 ws:TEXCOORD0;};
   V Vert(A a){V o;o.ws=TransformObjectToWorld(a.p.xyz);o.p=TransformWorldToHClip(o.ws);return o;}
   float Hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
   float Noise(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(Hash(i),Hash(i+float2(1,0)),f.x),lerp(Hash(i+float2(0,1)),Hash(i+1),f.x),f.y);}
   half3 LightReflection(Light light,float3 n,float3 v)
   {
    float3 h=SafeNormalize(light.direction+v);
    float roughSpec=pow(saturate(dot(n,h)),45)*.11;
    return light.color*roughSpec*(light.distanceAttenuation*light.shadowAttenuation);
   }
   half4 Frag(V i):SV_Target
   {
    float t=_EnvTime<0?_Time.y:_EnvTime;
    float2 p=i.ws.xz;
    float warp=Noise(p*.16+float2(t*.008,-t*.006));
    float a=dot(p,float2(.36,.93))*2.1+t*.45+warp*.7;
    float b=dot(p,float2(-.84,.54))*.88-t*.25+warp*1.1;
    float c=dot(p,float2(.96,-.27))*4.4+t*.64;
    float2 gradient=float2(.36,.93)*cos(a)*.055+float2(-.84,.54)*cos(b)*.035+float2(.96,-.27)*cos(c)*.009;
    float3 normal=normalize(float3(-gradient.x,1,-gradient.y));
    float3 view=SafeNormalize(GetWorldSpaceViewDir(i.ws));
    float fresnel=pow(1-saturate(dot(normal,view)),3);
    float ripple=saturate(.45+.22*sin(a)+.18*sin(b)+.08*sin(c));
    half3 color=lerp(_Deep.rgb,_Shallow.rgb,.16+ripple*_WaveStrength);
    color=lerp(color,_Horizon.rgb,fresnel*.72);
    // The sea is a very large two-triangle plane: choose shadow cascades per fragment.
    #if defined(_MAIN_LIGHT_SHADOWS_SCREEN)
     float4 mainShadow=ComputeScreenPos(TransformWorldToHClip(i.ws));
    #elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
     float4 mainShadow=TransformWorldToShadowCoord(i.ws);
    #else
     float4 mainShadow=float4(0,0,0,0);
    #endif
    Light main=GetMainLight(mainShadow,i.ws,half4(1,1,1,1));color+=LightReflection(main,normal,view)*.18;
    // Real point/spot colors and intensity drive the small warm highlights; no permanently lit fake harbor reflection.
    InputData inputData=(InputData)0;
    inputData.positionWS=i.ws;inputData.normalWS=normal;inputData.viewDirectionWS=view;
    inputData.normalizedScreenSpaceUV=GetNormalizedScreenSpaceUV(i.p);
    #if defined(_ADDITIONAL_LIGHTS)
     #if USE_CLUSTER_LIGHT_LOOP
      [loop] for(uint lightIndex=0;lightIndex<min(URP_FP_DIRECTIONAL_LIGHTS_COUNT,MAX_VISIBLE_LIGHTS);lightIndex++)
      {
       CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
       Light l=GetAdditionalLight(lightIndex,i.ws,half4(1,1,1,1));color+=LightReflection(l,normal,view)*.12;
      }
     #endif
     uint pixelLightCount=GetAdditionalLightsCount();
     LIGHT_LOOP_BEGIN(pixelLightCount)
      Light l=GetAdditionalLight(lightIndex,i.ws,half4(1,1,1,1));color+=LightReflection(l,normal,view);
     LIGHT_LOOP_END
    #endif
    float2 mapUV=(p-_ShoreRect.xy)/max(_ShoreRect.zw,float2(.001,.001));
    float inMap=step(0,mapUV.x)*step(0,mapUV.y)*step(mapUV.x,1)*step(mapUV.y,1)*saturate(_ShoreEnabled);
    float shoreDistance=SAMPLE_TEXTURE2D(_ShoreMap,sampler_ShoreMap,mapUV).r*8;
    float wash=(1-smoothstep(.2,1.35,shoreDistance))*inMap;
    float foam=smoothstep(.4,.8,Noise(p*1.8+float2(t*.06,0)))*(.5+.5*sin(shoreDistance*7-t*.75+warp*2));
    color=lerp(color,_Shallow.rgb*1.08,wash*foam*.22);
    float distantFade=smoothstep(75,130,length(p));
    color=lerp(color,_Horizon.rgb,distantFade);
    return half4(color,1);
   }
   ENDHLSL
  }
 }
 Fallback Off
}
