// The islanders' 萤光 drawn on the body itself: a soft additive rim that follows the silhouette,
// brighter where the surface turns away from the camera, with a slow breathing shimmer.
// Added as an extra material on each character renderer by Fireflow.
Shader "JieGuang/CharacterRim"
{
    Properties
    {
        _RimColor ("Glow colour", Color) = (0.55, 1, 0.45, 1)
        _RimStrength ("Strength", Float) = 0
        _RimPower ("Edge tightness", Float) = 2.6
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            Blend One One
            ZWrite Off
            ZTest LEqual
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
            float4 _RimColor;
            float _RimStrength, _RimPower;
            CBUFFER_END

            struct A { float4 pos : POSITION; float3 normal : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 pos : SV_POSITION; float3 n : TEXCOORD0; float3 ws : TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };

            V vert(A i)
            {
                V o;
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.ws = TransformObjectToWorld(i.pos.xyz);
                o.pos = TransformWorldToHClip(o.ws);
                o.n = TransformObjectToWorldNormal(i.normal);
                return o;
            }

            half4 frag(V i) : SV_Target
            {
                float3 n = normalize(i.n);
                float3 v = normalize(GetWorldSpaceViewDir(i.ws));
                float rim = pow(1 - saturate(dot(n, v)), _RimPower);
                float shimmer = 0.85 + 0.15 * sin(_Time.y * 1.7 + i.ws.y * 6.0);
                return half4(_RimColor.rgb * rim * _RimStrength * shimmer, 1);
            }
            ENDHLSL
        }
    }
}
