Shader "BorrowedLight/FoliagePaint"
{
    Properties
    {
        [MainColor] _BaseColor("Painted colour", Color) = (0.55,0.53,0.48,1)
        [MainTexture] _BaseMap("Base map (depth-pass compatibility)", 2D) = "white" {}
        _Smoothness("Smoothness", Range(0,1)) = 0
        _Metallic("Metallic", Range(0,1)) = 0
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
            #pragma shader_feature_local _FOLIAGE_VERTEX_COLOR
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

            // This is PaintedSurface's original kind-4 path with its choice fixed
            // at compile time. Lit's unchanged material layout also matches UsePass.
            // No material property lives outside the UnityPerMaterial CBUFFER.
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
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
            #ifdef _FOLIAGE_VERTEX_COLOR
                foliageTint = vertexTint;
            #endif
                float3 p = TransformObjectToWorld(input.positionOS.xyz);
                float rooted = smoothstep(0.08, 0.48, p.y);
                float gust = sin(p.x * 0.73 + p.z * 0.46 - _Time.y * 1.25);
                float flutter = sin(p.x * 3.1 + p.z * 1.8 + _Time.y * 2.5);
                p.xz += float2(1, 0.42) * (gust * 0.025 + flutter * 0.006) * rooted;
                input.positionOS.xyz = TransformWorldToObject(p);
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
                half3 leafNormal = normalize(input.normalWS) * faceSign;
                input.normalWS = normalize(lerp(leafNormal, half3(0,1,0), 0.40h));

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

        // Match the existing foliage's depth, normal and shadow behavior exactly.
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
    }
    FallBack "Hidden/Universal Render Pipeline/FallbackError"
}
