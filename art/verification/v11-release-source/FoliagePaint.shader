Shader "BorrowedLight/FoliagePaint"
{
    Properties
    {
        [MainColor] _BaseColor("Painted colour", Color) = (0.55,0.53,0.48,1)
        [MainTexture] _BaseMap("Base map (depth-pass compatibility)", 2D) = "white" {}
        _Smoothness("Smoothness", Range(0,1)) = 0
        _Metallic("Metallic", Range(0,1)) = 0
        [Toggle(_FOLIAGE_NORMAL_UP_20)] _FoliageNormalUp20("Study: 20% normal up blend (default 40%)", Float) = 0
        [Toggle(_FOLIAGE_LEGACY_AUX)] _FoliageLegacyAux("Study: original unanimated auxiliary passes", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull", Float) = 0
        [HideInInspector] _Cutoff("Alpha cutoff", Range(0,1)) = 0.5
        [HideInInspector] _Surface("Surface", Float) = 0
        [HideInInspector] _AlphaClip("Alpha clip", Float) = 0
        [HideInInspector] _BumpMap("Normal map", 2D) = "bump" {}
        [HideInInspector] _BumpScale("Normal scale", Float) = 1
        [HideInInspector] _SpecColor("Specular", Color) = (0.2,0.2,0.2,1)
        [HideInInspector] _EmissionColor("Emission", Color) = (0,0,0,0)
        [HideInInspector] _OcclusionStrength("Occlusion strength", Range(0,1)) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        LOD 300
        Pass
        {
            Name "FoliageForward"
            Tags { "LightMode"="UniversalForward" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex FoliageVertex
            #pragma fragment FoliageFragment
            #pragma multi_compile_instancing
            #pragma instancing_options renderinglayer
            #pragma shader_feature_local _FOLIAGE_VERTEX_COLOR
            #pragma shader_feature_local_fragment _FOLIAGE_NORMAL_UP_20
            #pragma shader_feature_local_fragment _FOLIAGE_LEGACY_AUX
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ EVALUATE_SH_MIXED EVALUATE_SH_VERTEX
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_ATLAS
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile _ _LIGHT_LAYERS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile _ LIGHTMAP_SHADOW_MIXING
            #pragma multi_compile _ SHADOWS_SHADOWMASK
            #pragma multi_compile _ DIRLIGHTMAP_COMBINED
            #pragma multi_compile _ LIGHTMAP_ON
            #pragma multi_compile _ DYNAMICLIGHTMAP_ON
            #pragma multi_compile _ USE_LEGACY_LIGHTMAPS
            #pragma multi_compile_fragment _ LIGHTMAP_BICUBIC_SAMPLING
            #pragma multi_compile_fragment _ REFLECTION_PROBE_ROTATION
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DOTS.hlsl"

            // Every pass uses the same official material CBUFFER. Study toggles
            // select local variants and therefore need no extra uniform fields.
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "FoliageSurface.hlsl"
            #ifndef REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
                #define REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
            #endif
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitForwardPass.hlsl"

            Varyings FoliageVertex(Attributes input
            #ifdef _FOLIAGE_VERTEX_COLOR
                , half4 vertexTint : COLOR, out half4 foliageTint : COLOR0
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
            #ifdef _FOLIAGE_VERTEX_COLOR
                foliageTint = vertexTint;
            #endif
                input.positionOS.xyz = FoliageWindPositionOS(input.positionOS.xyz);
                return LitPassVertex(input);
            }

            void FoliageFragment(Varyings input,
            #ifdef _FOLIAGE_VERTEX_COLOR
                half4 foliageTint : COLOR0,
            #endif
                FRONT_FACE_TYPE frontFace : FRONT_FACE_SEMANTIC,
                out half4 outColor : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half faceSign = IS_FRONT_VFACE(frontFace, 1.0h, -1.0h);
                input.normalWS = FoliageShadingNormalWS(input.normalWS, faceSign);

                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = _BaseColor.rgb;
            #ifdef _FOLIAGE_VERTEX_COLOR
                surfaceData.albedo *= foliageTint.rgb;
            #endif
                surfaceData.metallic = saturate(_Metallic);
                surfaceData.specular = 0;
                surfaceData.smoothness = saturate(_Smoothness);
                surfaceData.normalTS = half3(0,0,1);
                surfaceData.occlusion = 1;
                surfaceData.emission = _EmissionColor.rgb;
                surfaceData.alpha = 1;
                surfaceData.clearCoatMask = 0;
                surfaceData.clearCoatSmoothness = 0;

                InputData inputData;
                InitializeInputData(input, surfaceData.normalTS, inputData);
                InitializeBakedGIData(input, inputData);
                half4 colour = UniversalFragmentBlinnPhong(inputData, surfaceData);
                colour.rgb = MixFog(colour.rgb, inputData.fogCoord);
                colour.a = 1;
                outColor = colour;
            #ifdef _WRITE_RENDERING_LAYERS
                outRenderingLayers = EncodeMeshRenderingLayer();
            #endif
            }
            ENDHLSL
        }

        // URP 17.3 auxiliary implementations remain responsible for instancing,
        // alpha/LOD clipping, punctual-light bias and normal-buffer encoding.
        // The legacy study delegates directly to those original entry points.
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex FoliageShadowVertex
            #pragma fragment ShadowPassFragment
            #pragma shader_feature_local _ALPHATEST_ON
            #pragma shader_feature_local_fragment _SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A
            #pragma shader_feature_local_vertex _FOLIAGE_LEGACY_AUX
            #pragma multi_compile_instancing
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DOTS.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "FoliageSurface.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/ShadowCasterPass.hlsl"

            Varyings FoliageShadowVertex(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
            #if !defined(_FOLIAGE_LEGACY_AUX)
                input.positionOS.xyz = FoliageWindPositionOS(input.positionOS.xyz);
            #endif
                // Keep the geometric normal for URP's shadow bias. Camera-facing
                // leaf normals belong to shading, not to shadow-caster geometry.
                return ShadowPassVertex(input);
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On
            ColorMask R
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex FoliageDepthOnlyVertex
            #pragma fragment DepthOnlyFragment
            #pragma shader_feature_local _ALPHATEST_ON
            #pragma shader_feature_local_fragment _SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A
            #pragma shader_feature_local_vertex _FOLIAGE_LEGACY_AUX
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_instancing
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DOTS.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "FoliageSurface.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/DepthOnlyPass.hlsl"

            Varyings FoliageDepthOnlyVertex(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
            #if !defined(_FOLIAGE_LEGACY_AUX)
                input.position.xyz = FoliageWindPositionOS(input.position.xyz);
            #endif
                return DepthOnlyVertex(input);
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex FoliageDepthNormalsVertex
            #pragma fragment FoliageDepthNormalsFragment
            #pragma shader_feature_local _NORMALMAP
            #pragma shader_feature_local _PARALLAXMAP
            #pragma shader_feature_local _ _DETAIL_MULX2 _DETAIL_SCALED
            #pragma shader_feature_local _ALPHATEST_ON
            #pragma shader_feature_local_fragment _SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A
            #pragma shader_feature_local_fragment _FOLIAGE_NORMAL_UP_20
            #pragma shader_feature_local _FOLIAGE_LEGACY_AUX
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            #pragma multi_compile_instancing
            #pragma instancing_options renderinglayer
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DOTS.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "FoliageSurface.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitDepthNormalsPass.hlsl"

            Varyings FoliageDepthNormalsVertex(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
            #if !defined(_FOLIAGE_LEGACY_AUX)
                input.positionOS.xyz = FoliageWindPositionOS(input.positionOS.xyz);
            #endif
                return DepthNormalsVertex(input);
            }

            void FoliageDepthNormalsFragment(Varyings input,
                FRONT_FACE_TYPE frontFace : FRONT_FACE_SEMANTIC,
                out half4 outNormalWS : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
            #if defined(_FOLIAGE_LEGACY_AUX)
                // Exact original URP fragment path, including its unflipped normal.
                DepthNormalsFragment(input, outNormalWS
                #ifdef _WRITE_RENDERING_LAYERS
                    , outRenderingLayers
                #endif
                );
            #else
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                #if defined(_ALPHATEST_ON)
                    Alpha(SampleAlbedoAlpha(input.uv, TEXTURE2D_ARGS(_BaseMap, sampler_BaseMap)).a, _BaseColor, _Cutoff);
                #endif
                #if defined(LOD_FADE_CROSSFADE)
                    LODFadeCrossFade(input.positionCS);
                #endif
                // Match the forward shader: authored normals, a camera-facing
                // side and one shared upward blend. Foliage has no normal map.
                half faceSign = IS_FRONT_VFACE(frontFace, 1.0h, -1.0h);
                float3 normalWS = FoliageShadingNormalWS(input.normalWS, faceSign);
                #if defined(_GBUFFER_NORMALS_OCT)
                    // Same fp32 octahedral packing as URP 17.3.
                    float2 octNormalWS = PackNormalOctQuadEncode(normalize(normalWS));
                    float2 remappedOctNormalWS = saturate(octNormalWS * 0.5 + 0.5);
                    half3 packedNormalWS = PackFloat2To888(remappedOctNormalWS);
                    outNormalWS = half4(packedNormalWS, 0.0);
                #else
                    outNormalWS = half4(NormalizeNormalPerPixel(normalWS), 0.0);
                #endif
                #ifdef _WRITE_RENDERING_LAYERS
                    outRenderingLayers = EncodeMeshRenderingLayer();
                #endif
            #endif
            }
            ENDHLSL
        }
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
