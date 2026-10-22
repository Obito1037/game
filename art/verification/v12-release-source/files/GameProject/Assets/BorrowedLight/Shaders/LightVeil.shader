Shader "BorrowedLight/LightVeil"
{
 Properties { _Color("Color",Color)=(1,.72,.30,.10) }
 SubShader {
  Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" }
  Blend SrcAlpha One ZWrite Off Cull Off
  Pass {
   HLSLPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   struct A{float4 positionOS:POSITION;float2 uv:TEXCOORD0;};
   struct V{float4 positionCS:SV_POSITION;float2 uv:TEXCOORD0;};
   float4 _Color;
   V vert(A i){V o;o.positionCS=TransformObjectToHClip(i.positionOS.xyz);o.uv=i.uv;return o;}
   half4 frag(V i):SV_Target {float edge=pow(saturate(1-abs(i.uv.x-.5)*2),1.4);return half4(_Color.rgb,_Color.a*edge*pow(saturate(1-i.uv.y),1.1));}
   ENDHLSL
  }
 }
}
