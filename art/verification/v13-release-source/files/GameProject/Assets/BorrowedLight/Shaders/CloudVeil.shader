Shader "BorrowedLight/CloudVeil"
{
 Properties { _Color("Cloud tint",Color)=(.35,.52,.57,.15) }
 SubShader {Tags {"Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline"} Blend SrcAlpha OneMinusSrcAlpha ZWrite Off Cull Back
 Pass {HLSLPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
 struct A{float4 positionOS:POSITION;float3 normalOS:NORMAL;};
 struct V{float4 positionCS:SV_POSITION;float3 positionWS:TEXCOORD0;float3 normalWS:TEXCOORD1;};float4 _Color;
 V vert(A i){V o;o.positionCS=TransformObjectToHClip(i.positionOS.xyz);o.positionWS=TransformObjectToWorld(i.positionOS.xyz);o.normalWS=TransformObjectToWorldNormal(i.normalOS);return o;}
 half4 frag(V i):SV_Target{float facing=saturate(dot(normalize(i.normalWS),normalize(_WorldSpaceCameraPos-i.positionWS)));float wisp=.78+.22*sin(i.positionWS.x*.63+i.positionWS.z*.4+sin(i.positionWS.y*1.3));return half4(_Color.rgb,_Color.a*pow(facing,2.3)*wisp);}
 ENDHLSL}
 }
}
