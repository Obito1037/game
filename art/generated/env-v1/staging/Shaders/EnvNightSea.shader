Shader "JieGuang/Environment/NightSea"
{
    Properties
    {
        _Deep("Deep sea", Color) = (0.009, 0.027, 0.043, 1)
        _Shallow("Soft wave", Color) = (0.021, 0.055, 0.07, 1)
        _Horizon("Distant horizon", Color) = (0.027, 0.046, 0.073, 1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "NightSea"
            Tags { "LightMode"="SRPDefaultUnlit" }
            Cull Off ZWrite On
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; };
            CBUFFER_START(UnityPerMaterial)
                half4 _Deep, _Shallow, _Horizon;
            CBUFFER_END
            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionWS = TransformObjectToWorld(input.positionOS.xyz);
                output.positionCS = TransformWorldToHClip(output.positionWS);
                return output;
            }
            half4 Frag(Varyings input) : SV_Target
            {
                float2 p = input.positionWS.xz;
                float wave = sin(p.y*1.4+p.x*.17+sin(p.x*.37)*.6+_Time.y*.16);
                float second = sin(p.y*.63-p.x*.27+_Time.y*.09);
                float stripes = pow(saturate(wave*.5+.5),14) * (.35+.3*second);
                half3 color = lerp(_Deep.rgb,_Shallow.rgb,saturate(.20+stripes));
                float3 view = normalize(GetCameraPositionWS()-input.positionWS);
                color += half3(.008,.014,.018) * pow(1-saturate(view.y),3);
                // Match NightSky's horizon before the finite sea plane reaches its outer edges.
                float distantFade = smoothstep(85.0,130.0,length(p));
                color = lerp(color,_Horizon.rgb,distantFade);
                return half4(color,1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
