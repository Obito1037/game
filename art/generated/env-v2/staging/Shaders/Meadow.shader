Shader "JieGuang/Environment/Meadow"
{
    Properties
    {
        _RootColor("Silver grass - shaded root", Color) = (0.11,0.18,0.135,1)
        _TipColor("Silver grass - soft tip", Color) = (0.43,0.52,0.40,1)
        _FlowerColor("Cream petals", Color) = (0.85,0.80,0.64,1)
        _PollenColor("Warm pollen", Color) = (0.56,0.39,0.16,1)
        _WindDirection("Wind direction XZ", Vector) = (0.8,0,0.6,0)
        _WindAmplitude("Tip movement in metres", Range(0,0.12)) = 0.045
        _WindSpeed("Wind cycle speed", Range(0,2)) = 0.26
        _WindTime("Fixed capture time (-1 = animate)", Float) = -1
        _Translucency("Modest leaf transmission", Range(0,0.3)) = 0.09
        _NormalUp("Soft leaf normal", Range(0,0.6)) = 0.32
        _FadeStart("Density fade start metres", Float) = 28
        _FadeEnd("Density fade end metres", Float) = 36
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Packing.hlsl"
        #if defined(LOD_FADE_CROSSFADE)
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/LODCrossFade.hlsl"
        #endif

        CBUFFER_START(UnityPerMaterial)
            half4 _RootColor, _TipColor, _FlowerColor, _PollenColor;
            float4 _WindDirection;
            float _WindAmplitude, _WindSpeed, _WindTime;
            half _Translucency, _NormalUp;
            float _FadeStart, _FadeEnd;
        CBUFFER_END

        float3 _LightDirection;
        float3 _LightPosition;

        // uv: width, root-to-tip weight, species (0 leaf / 1 stem / 2 petal / 3 pollen), seed.
        // root: root position in this mesh's local space, plant height in metres.
        struct Attributes
        {
            float4 positionOS : POSITION;
            float3 normalOS : NORMAL;
            half4 color : COLOR;
            float4 uv : TEXCOORD0;
            float4 root : TEXCOORD1;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };
        struct Varyings
        {
            float4 positionCS : SV_POSITION;
            float3 positionWS : TEXCOORD0;
            half3 normalWS : TEXCOORD1;
            half4 color : TEXCOORD2;
            float4 uv : TEXCOORD3;
            float3 rootWS : TEXCOORD4;
            half4 fogAndVertexLight : TEXCOORD5;
            float4 shadowCoord : TEXCOORD6;
            UNITY_VERTEX_INPUT_INSTANCE_ID
            UNITY_VERTEX_OUTPUT_STEREO
        };

        float StableHash(float n) { return frac(sin(n * 71.131 + 19.719) * 13758.5453); }

        float3 MeadowSafeNormal(float3 normalWS)
        {
            float lengthSquared = dot(normalWS, normalWS);
            return lengthSquared > 1e-10 ? normalWS * rsqrt(max(lengthSquared, 1e-10)) : float3(0,1,0);
        }

        // One deformation function is used by colour, depth, normals and shadow passes.
        // Roots never move, and the stored root makes all vertices in a plant share phase.
        void Deform(Attributes input, out float3 positionWS, out float3 normalWS, out float3 rootWS)
        {
            positionWS = TransformObjectToWorld(input.positionOS.xyz);
            normalWS = TransformObjectToWorldNormal(input.normalOS);
            rootWS = TransformObjectToWorld(input.root.xyz);
            float2 direction = _WindDirection.xz;
            direction /= max(length(direction), 0.001);
            float time = _WindTime >= 0 ? _WindTime : _Time.y;
            float phase = dot(rootWS.xz, float2(0.41,0.27)) + input.uv.w * 6.2831853;
            float cycle = time * _WindSpeed * 6.2831853;
            float wind = sin(cycle + phase) * 0.72 + sin(cycle * 2.7 + phase * 1.9) * 0.28;
            float gust = 0.72 + 0.28 * sin(time * 0.19 + dot(rootWS.xz,float2(0.11,-0.08)));
            float h = saturate(input.uv.y);
            float2 shift = direction * (_WindAmplitude * wind * gust);
            positionWS.xz += shift * h * h;
            // Inverse-transpose for the approximate vertical shear, keeping lighting attached.
            float2 slope = shift * (2.0 * h / max(input.root.w, 0.08));
            normalWS.y -= dot(normalWS.xz, slope);
            normalWS = MeadowSafeNormal(normalWS);
        }

        Varyings MeadowVertex(Attributes input)
        {
            Varyings output = (Varyings)0;
            UNITY_SETUP_INSTANCE_ID(input);
            UNITY_TRANSFER_INSTANCE_ID(input, output);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
            Deform(input, output.positionWS, output.normalWS, output.rootWS);
            output.positionCS = TransformWorldToHClip(output.positionWS);
            output.color = input.color;
            output.uv = input.uv;
            output.fogAndVertexLight = half4(ComputeFogFactor(output.positionCS.z), VertexLighting(output.positionWS, output.normalWS));
            VertexPositionInputs positions = (VertexPositionInputs)0;
            positions.positionWS = output.positionWS;
            positions.positionCS = output.positionCS;
            output.shadowCoord = GetShadowCoord(positions);
            return output;
        }

        Varyings MeadowShadowVertex(Attributes input)
        {
            Varyings output = MeadowVertex(input);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = SafeNormalize(_LightPosition - output.positionWS);
            #else
                float3 lightDirectionWS = _LightDirection;
            #endif
            output.positionCS = TransformWorldToHClip(ApplyShadowBias(output.positionWS, output.normalWS, lightDirectionWS));
            output.positionCS = ApplyShadowClamping(output.positionCS);
            return output;
        }

        void MeadowClip(Varyings input)
        {
            float distanceXZ = length(input.rootWS.xz - GetCameraPositionWS().xz);
            float visibility = 1.0 - smoothstep(_FadeStart, max(_FadeEnd, _FadeStart + 0.1), distanceXZ);
            // Whole-plant deterministic thinning; no changing screen-space noise or frame seed.
            clip(visibility - StableHash(input.uv.w * 213.17) - 0.00001);
            #if defined(LOD_FADE_CROSSFADE)
                LODFadeCrossFade(input.positionCS);
            #endif
        }

        half3 EvaluateLeafLight(Light light, half3 normalWS, half3 viewWS, half3 albedo, half height, half transmission)
        {
            half ndl = dot(normalWS, light.direction);
            half diffuse = saturate((ndl + 0.10h) / 1.10h);
            half back = pow(saturate(dot(-viewWS, light.direction)), 3) * saturate(-ndl);
            half3 reflected = albedo * (diffuse + transmission * back * height);
            return reflected * light.color * (light.distanceAttenuation * light.shadowAttenuation);
        }

        half4 MeadowFragment(Varyings input, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(input);
            UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
            MeadowClip(input);
            half faceSign = IS_FRONT_VFACE(facing, 1.0h, -1.0h);
            half3 normalWS = MeadowSafeNormal(lerp(input.normalWS * faceSign, half3(0,1,0), _NormalUp));
            half height = saturate(input.uv.y);
            half3 albedo = lerp(_RootColor.rgb, _TipColor.rgb, smoothstep(0,1,height)) * input.color.rgb;
            half flower = step(1.5, input.uv.z);
            albedo = lerp(albedo, _FlowerColor.rgb * input.color.rgb, flower);
            albedo = lerp(albedo, _PollenColor.rgb * input.color.rgb, step(2.5,input.uv.z));

            InputData inputData = (InputData)0;
            inputData.positionWS = input.positionWS;
            inputData.positionCS = input.positionCS;
            inputData.normalWS = normalWS;
            inputData.viewDirectionWS = SafeNormalize(GetWorldSpaceViewDir(input.positionWS));
            inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
            // Match URP: cascade selection must happen per fragment, never interpolate
            // coordinates from vertices that may belong to different shadow atlases.
            #if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
                inputData.shadowCoord = input.shadowCoord;
            #elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
                inputData.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
            #else
                inputData.shadowCoord = float4(0,0,0,0);
            #endif
            inputData.shadowMask = half4(1,1,1,1);
            inputData.bakedGI = SampleSH(normalWS);
            inputData.fogCoord = InitializeInputDataFog(float4(input.positionWS,1), input.fogAndVertexLight.x);
            AmbientOcclusionFactor ao = CreateAmbientOcclusionFactor(inputData.normalizedScreenSpaceUV, 1.0h);
            half3 color = albedo * inputData.bakedGI * lerp(0.65h,1.0h,height) * ao.indirectAmbientOcclusion;
            half transmission = _Translucency * (1.0h - flower * 0.7h);
            Light main = GetMainLight(inputData, inputData.shadowMask, ao);
            color += EvaluateLeafLight(main, normalWS, inputData.viewDirectionWS, albedo, height, transmission);
            #if defined(_ADDITIONAL_LIGHTS)
                uint pixelLightCount = GetAdditionalLightsCount();
                #if USE_CLUSTER_LIGHT_LOOP
                    [loop] for (uint lightIndex = 0; lightIndex < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); lightIndex++)
                    {
                        CLUSTER_LIGHT_LOOP_SUBTRACTIVE_LIGHT_CHECK
                        Light extra = GetAdditionalLight(lightIndex, inputData, inputData.shadowMask, ao);
                        color += EvaluateLeafLight(extra, normalWS, inputData.viewDirectionWS, albedo, height, transmission);
                    }
                #endif
                LIGHT_LOOP_BEGIN(pixelLightCount)
                    Light extra = GetAdditionalLight(lightIndex, inputData, inputData.shadowMask, ao);
                    color += EvaluateLeafLight(extra, normalWS, inputData.viewDirectionWS, albedo, height, transmission);
                LIGHT_LOOP_END
            #endif
            #if defined(_ADDITIONAL_LIGHTS_VERTEX)
                color += albedo * input.fogAndVertexLight.yzw;
            #endif
            return half4(MixFog(color, inputData.fogCoord), 1);
        }

        half4 MeadowDepthFragment(Varyings input) : SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(input);
            MeadowClip(input);
            return 0;
        }

        half4 MeadowNormalsFragment(Varyings input, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(input);
            MeadowClip(input);
            half3 normalWS = MeadowSafeNormal(lerp(input.normalWS * IS_FRONT_VFACE(facing, 1.0h, -1.0h), half3(0,1,0), _NormalUp));
            #if defined(_GBUFFER_NORMALS_OCT)
                float2 octNormal = PackNormalOctQuadEncode(normalWS);
                return half4(PackFloat2To888(saturate(octNormal * 0.5 + 0.5)),0);
            #else
                return half4(normalWS,0);
            #endif
        }
        ENDHLSL

        Pass
        {
            Name "MeadowForward"
            Tags { "LightMode"="UniversalForwardOnly" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex MeadowVertex
            #pragma fragment MeadowFragment
            #pragma multi_compile_instancing
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            ENDHLSL
        }
        Pass
        {
            Name "MeadowShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ColorMask 0
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex MeadowShadowVertex
            #pragma fragment MeadowDepthFragment
            #pragma multi_compile_instancing
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            ENDHLSL
        }
        Pass
        {
            Name "MeadowDepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ColorMask R
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex MeadowVertex
            #pragma fragment MeadowDepthFragment
            #pragma multi_compile_instancing
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            ENDHLSL
        }
        Pass
        {
            Name "MeadowDepthNormals"
            Tags { "LightMode"="DepthNormalsOnly" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex MeadowVertex
            #pragma fragment MeadowNormalsFragment
            #pragma multi_compile_instancing
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            ENDHLSL
        }
    }
    Fallback Off
}
