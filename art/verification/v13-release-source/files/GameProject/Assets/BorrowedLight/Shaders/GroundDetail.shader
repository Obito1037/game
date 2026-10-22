Shader "BorrowedLight/GroundDetail"
{
    Properties
    {
        [MainTexture] _BaseMap("Original Meadow / unchanged atlas UV", 2D) = "white" {}
        [MainColor] _BaseColor("Original Meadow colour", Color) = (1,1,1,1)
        _Smoothness("Smoothness", Range(0,1)) = 0
        _Metallic("Metallic", Range(0,1)) = 0
        [Normal] _BumpMap("Original Meadow normal", 2D) = "bump" {}
        _BumpScale("Original normal scale", Float) = 0.22
        _DetailAlbedoMap("Original earth detail / sRGB", 2D) = "white" {}
        _DetailAlbedoMapScale("Normalized albedo detail strength", Range(0,1)) = 0.55
        [HideInInspector] _DetailMask("Unused official detail mask", 2D) = "white" {}
        [HideInInspector][Normal] _DetailNormalMap("Unused official detail normal", 2D) = "bump" {}
        [HideInInspector] _DetailNormalMapScale("Unused detail normal scale", Float) = 0
        [ToggleOff] _SpecularHighlights("Specular Highlights", Float) = 0
        [ToggleOff] _EnvironmentReflections("Environment Reflections", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull", Float) = 0
        [HideInInspector] _WorkflowMode("Workflow", Float) = 1
        [HideInInspector] _Cutoff("Alpha cutoff", Range(0,1)) = 0.5
        [HideInInspector] _Surface("Surface", Float) = 0
        [HideInInspector] _AlphaClip("Alpha clip", Float) = 0
        [HideInInspector] _SpecColor("Specular", Color) = (0.2,0.2,0.2,1)
        [HideInInspector] _EmissionColor("Emission", Color) = (0,0,0,0)
        [HideInInspector] _EmissionMap("Emission map", 2D) = "white" {}
        [HideInInspector] _OcclusionStrength("Occlusion strength", Float) = 1
        [HideInInspector] _OcclusionMap("Occlusion map", 2D) = "white" {}
        [HideInInspector] _Parallax("Parallax", Float) = 0
        [HideInInspector] _ParallaxMap("Parallax map", 2D) = "black" {}
        [HideInInspector] _MetallicGlossMap("Metallic map", 2D) = "white" {}
        [HideInInspector] _SpecGlossMap("Specular map", 2D) = "white" {}
        [HideInInspector] _ClearCoatMask("Clear coat mask", Float) = 0
        [HideInInspector] _ClearCoatSmoothness("Clear coat smoothness", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "UniversalMaterialType"="Lit" "Queue"="Geometry" }
        LOD 300
        Pass
        {
            Name "GroundDetailForward"
            Tags { "LightMode"="UniversalForward" }
            ZWrite On
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex LitPassVertex
            #pragma fragment GroundDetailFragment
            #pragma shader_feature_local _NORMALMAP
            #pragma shader_feature_local _RECEIVE_SHADOWS_OFF
            #pragma shader_feature_local_fragment _ALPHATEST_ON
            #pragma shader_feature_local_fragment _EMISSION
            #pragma shader_feature_local_fragment _OCCLUSIONMAP
            #pragma shader_feature_local_fragment _SPECULARHIGHLIGHTS_OFF
            #pragma shader_feature_local_fragment _ENVIRONMENTREFLECTIONS_OFF
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ EVALUATE_SH_MIXED EVALUATE_SH_VERTEX
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _SCREEN_SPACE_IRRADIANCE
            #pragma multi_compile_fragment _ _DBUFFER_MRT1 _DBUFFER_MRT2 _DBUFFER_MRT3
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
            #pragma multi_compile _ LOD_FADE_CROSSFADE
            #pragma multi_compile_fragment _ DEBUG_DISPLAY
            #pragma multi_compile_instancing
            #pragma instancing_options renderinglayer
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DOTS.hlsl"

            // No custom UnityPerMaterial declaration: all fields and offsets below
            // come from the installed URP 17.3 LitInput, including the Detail fields.
            // Do NOT enable URP's _DETAIL keywords: they would add a second detail
            // multiplication and alter the normal path. Only albedo changes here.
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #ifndef REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
                #define REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
            #endif
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitForwardPass.hlsl"

            // Exact authored PNG statistics: analyze-original.cjs, SHA256
            // 483D36A325CA6B05BBB8580DD3E238AF866F331D762976CB0064569FD7925F1B.
            // Constants introduce NO extra material/CBUFFER layout or texture edits.
            static const float GroundOriginalLinearMean = 0.15805805065816778;
            static const float GroundClampedRatioMean = 0.9620164207456156;

            void GroundDetailFragment(Varyings input, out half4 outColor : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                SurfaceData surfaceData;
                InitializeStandardLitSurfaceData(input.uv, surfaceData);
                float2 detailUV = input.positionWS.xz * _DetailAlbedoMap_ST.xy + _DetailAlbedoMap_ST.zw;
                half3 originalDetail = SAMPLE_TEXTURE2D(_DetailAlbedoMap, sampler_DetailAlbedoMap, detailUV).rgb;
                float luminance = dot(originalDetail, float3(0.2126,0.7152,0.0722));
                float relativeValue = clamp(luminance / GroundOriginalLinearMean, 0.35, 2.25) / GroundClampedRatioMean;
                surfaceData.albedo *= lerp(1.0, relativeValue, saturate(_DetailAlbedoMapScale));
                // Preserve the existing atlas colour, normals, roughness, occlusion,
                // alpha and all URP lighting/GI/shadow behaviour.
            #ifdef LOD_FADE_CROSSFADE
                LODFadeCrossFade(input.positionCS);
            #endif
                InputData inputData;
                InitializeInputData(input, surfaceData.normalTS, inputData);
                SETUP_DEBUG_TEXTURE_DATA(inputData, UNDO_TRANSFORM_TEX(input.uv, _BaseMap));
            #if defined(_DBUFFER)
                ApplyDecalToSurfaceData(input.positionCS, surfaceData, inputData);
            #endif
                InitializeBakedGIData(input, inputData);
                half4 colour = UniversalFragmentPBR(inputData, surfaceData);
                colour.rgb = MixFog(colour.rgb, inputData.fogCoord);
                colour.a = OutputAlpha(colour.a, IsSurfaceTypeTransparent(_Surface));
                outColor = colour;
            #ifdef _WRITE_RENDERING_LAYERS
                outRenderingLayers = EncodeMeshRenderingLayer();
            #endif
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
