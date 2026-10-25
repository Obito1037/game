Shader "JieGuang/MeadowCards"
{
    Properties
    {
        [MainTexture] _BaseMap("Grass and flowers atlas", 2D) = "white" {}
        _Cutoff("Leaf alpha threshold", Range(0,1)) = .36
        _Wind("Tip sway in metres", Range(0,.3)) = .085
        _Saturation("Leaf colour saturation", Range(0,1)) = .55
        _FoliageDistance("Fade distance in metres", Float) = 48
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="TransparentCutout" "Queue"="AlphaTest" }
        Cull Off
        ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            float _Cutoff, _Wind, _FoliageDistance, _Saturation;
        CBUFFER_END
        struct Attributes
        {
            float4 positionOS : POSITION;
            float3 normalOS : NORMAL;
            float2 uv : TEXCOORD0;
            float2 tip : TEXCOORD1;
            half4 color : COLOR;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };
        struct Varyings
        {
            float4 positionCS : SV_POSITION;
            float3 positionWS : TEXCOORD0;
            float2 uv : TEXCOORD1;
            half3 normalWS : TEXCOORD2;
            half4 color : COLOR;
            half fog : TEXCOORD3;
            UNITY_VERTEX_INPUT_INSTANCE_ID
            UNITY_VERTEX_OUTPUT_STEREO
        };
        Varyings MeadowVertex(Attributes v)
        {
            Varyings o = (Varyings)0;
            UNITY_SETUP_INSTANCE_ID(v);
            UNITY_TRANSFER_INSTANCE_ID(v,o);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            float3 p = TransformObjectToWorld(v.positionOS.xyz);
            float phase = p.x * .63 + p.z * .48 + _Time.y * 1.45;
            float wave = sin(phase) * .65 + sin(phase * 1.73 + _Time.y * .31) * .35;
            p.xz += float2(.82,.38) * wave * _Wind * v.tip.x * v.tip.x;
            o.positionWS = p;
            o.positionCS = TransformWorldToHClip(p);
            o.normalWS = TransformObjectToWorldNormal(v.normalOS);
            o.uv = v.uv;
            o.color = v.color;
            o.fog = ComputeFogFactor(o.positionCS.z);
            return o;
        }
        half4 MeadowSample(Varyings i)
        {
            half4 tex = SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv);
            clip(tex.a - _Cutoff);
            half grey = dot(tex.rgb, half3(.2126,.7152,.0722));
            tex.rgb = lerp(grey.xxx, tex.rgb, _Saturation);
            float fade = saturate((_FoliageDistance - distance(_WorldSpaceCameraPos,i.positionWS)) / 7.0);
            // Stable world-space dither avoids transparent sorting and preserves depth writing.
            float noise = frac(sin(dot(floor(i.positionWS.xz * 85),float2(12.9898,78.233))) * 43758.5453);
            clip(fade - noise - .001);
            return tex * i.color;
        }
        ENDHLSL
        Pass
        {
            Name "MeadowForward"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex MeadowVertex
            #pragma fragment MeadowFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            half4 MeadowFragment(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                half4 tex = MeadowSample(i);
                InputData lightInput = (InputData)0;
                lightInput.positionWS = i.positionWS;
                lightInput.normalWS = normalize(i.normalWS);
                lightInput.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                #if defined(_MAIN_LIGHT_SHADOWS_SCREEN)
                    lightInput.shadowCoord = ComputeScreenPos(TransformWorldToHClip(i.positionWS));
                #else
                    lightInput.shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                #endif
                lightInput.bakedGI = SampleSH(lightInput.normalWS);
                lightInput.shadowMask = half4(1,1,1,1);
                lightInput.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                lightInput.vertexLighting = VertexLighting(i.positionWS, lightInput.normalWS);
                SurfaceData surface = (SurfaceData)0;
                surface.albedo = tex.rgb;
                surface.alpha = 1;
                surface.occlusion = 1;
                surface.normalTS = half3(0,0,1);
                surface.smoothness = .04;
                half4 color = UniversalFragmentBlinnPhong(lightInput,surface);
                color.rgb = MixFog(color.rgb,i.fog);
                return half4(color.rgb,1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ColorMask R
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex MeadowVertex
            #pragma fragment DepthFragment
            #pragma multi_compile_instancing
            half4 DepthFragment(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                MeadowSample(i);
                return i.positionCS.z;
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex MeadowVertex
            #pragma fragment NormalFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            half4 NormalFragment(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                MeadowSample(i);
                float3 n = normalize(i.normalWS);
                #ifdef _GBUFFER_NORMALS_OCT
                    float2 oct = PackNormalOctQuadEncode(n);
                    return half4(PackFloat2To888(saturate(oct*.5+.5)),0);
                #else
                    return half4(n,0);
                #endif
            }
            ENDHLSL
        }
    }
}
