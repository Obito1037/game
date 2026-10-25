Shader "JieGuang/Environment/NightSky"
{
    Properties
    {
        _Zenith("Zenith", Color) = (0.008, 0.018, 0.05, 1)
        _Horizon("Horizon", Color) = (0.027, 0.046, 0.073, 1)
        _EarthDirection("Earth direction", Vector) = (-0.30, 0.15, 0.94, 0)
        _EarthRadius("Earth angular radius", Range(0.02,0.18)) = 0.066
        _Stars("Star brightness", Range(0,2)) = 0.8
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Background" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "NightSky"
            Tags { "LightMode"="SRPDefaultUnlit" }
            Cull Front ZWrite Off ZTest LEqual
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionOS : TEXCOORD0; };
            CBUFFER_START(UnityPerMaterial)
                half4 _Zenith, _Horizon;
                float4 _EarthDirection;
                float _EarthRadius, _Stars;
            CBUFFER_END
            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.positionOS = input.positionOS.xyz;
                return output;
            }
            float Hash(float2 p) { return frac(sin(dot(p, float2(127.1,311.7))) * 43758.5453); }
            half4 Frag(Varyings input) : SV_Target
            {
                float3 d = normalize(input.positionOS);
                half3 color = lerp(_Horizon.rgb,_Zenith.rgb,pow(saturate(d.y),.55));
                float2 uv = float2(atan2(d.z,d.x) * .15915494 + .5, asin(clamp(d.y,-1,1)) * .31830989 + .5);
                float2 cells = uv * float2(450,225);
                float2 cell = floor(cells);
                float seed = Hash(cell);
                float2 starAt = float2(Hash(cell+17.1),Hash(cell+51.7));
                float dist = length((frac(cells)-starAt)*float2(max(.35,cos((uv.y-.5)*3.14159)),1));
                float star = (1-smoothstep(.014,.052,dist)) * step(.986,seed) * smoothstep(-.03,.16,d.y);
                color += star * _Stars * lerp(half3(.48,.61,.75),half3(.9,.86,.7),Hash(cell+7));
                float3 axis = normalize(_EarthDirection.xyz);
                float3 right = normalize(cross(float3(0,1,0),axis));
                float3 up = cross(axis,right);
                float2 q = float2(dot(d,right),dot(d,up)) / _EarthRadius;
                float radius = length(q);
                float disk = (1-smoothstep(.98,1.01,radius)) * step(0,dot(d,axis));
                // A mostly dark blue Earth with a thin, blue-white illuminated crescent.
                float shifted = length(q-float2(-.13,.015));
                float crescent = smoothstep(.97,1.01,shifted) * disk;
                float cloud = .5+.5*sin(q.x*24+sin(q.y*18)*2.1)*sin(q.y*31+q.x*8);
                half3 earthDark = half3(.012,.025,.042) * (.8+.2*cloud);
                half3 earthLight = lerp(half3(.16,.38,.64),half3(.64,.78,.87),cloud);
                color = lerp(color, earthDark, disk);
                color += earthLight*crescent*.82;
                return half4(color,1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
