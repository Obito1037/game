Shader "BorrowedLight/EyeSurface"
{
    Properties
    {
        [MainColor] _BaseColor("Authored eye colour", Color) = (0.7,0.695,0.63,1)
        [MainTexture] _BaseMap("Base map", 2D) = "white" {}
        _Smoothness("Smoothness", Range(0,1)) = 0.18
        _Metallic("Metallic", Range(0,1)) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull", Float) = 0
        [Enum(Ivory,0,AmberRim,1,Chestnut,2)] _EyePart("Eye region", Float) = 0
        _EyeContact("Upper-lid contact wash", Range(0,1)) = 0
        _EyeIris("Iris colour depth", Range(0,1)) = 0
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
        Pass
        {
            Name "EyeForward"
            Tags { "LightMode"="UniversalForward" }
            ZWrite On
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex LitPassVertex
            #pragma fragment EyePassFragment
            #pragma multi_compile_instancing
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
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitForwardPass.hlsl"

            // Outside Lit's material buffer; the official depth/shadow passes
            // retain the same layout. No custom normals or extra texture sampling.
            float _EyePart, _EyeContact, _EyeIris;

            half3 EyeColourWash(float2 uv)
            {
                // v11 head UVs store proportioned Blender X/Z, including both eyes.
                // Recover the authored coordinates, independent of actor motion.
                float x=(uv.x-0.5)/(3.0*0.92);
                float z=0.945+(((uv.y+1.7)*0.5)-1.010)/0.9;
                float side=x<0?-1.0:1.0;
                float t=saturate((side*x-(0.048-0.0306))/0.0612);
                float upper=1.0868+0.0018*(t-0.5)
                    +0.0168*(1.0+side*0.025)*pow(max(0.0,sin(PI*t)),0.82);
                float lidDistance=max(0.0,upper-z);
                float contact=(1.0-smoothstep(0.0005,0.0068,lidDistance))
                    *smoothstep(0.0,0.10,t)*(1.0-smoothstep(0.90,1.0,t));
                half3 wash=lerp(half3(1,1,1),half3(0.63,0.62,0.60),contact*saturate(_EyeContact));
                if(_EyePart>0.5)
                {
                    float2 q=float2((x-(side*0.048+0.00055))/0.0130,(z-1.0883)/0.0127);
                    float radius=length(q);
                    float lower=saturate(0.5-q.y*0.5);
                    half3 iris=lerp(half3(0.80,0.84,0.91),half3(1.16,1.08,0.90),lower);
                    iris*=lerp(1.10,0.69,smoothstep(0.64,1.0,radius));
                    iris*=lerp(0.85,1.0,smoothstep(0.34,0.56,radius));
                    wash*=lerp(half3(1,1,1),iris,saturate(_EyeIris));
                }
                return wash;
            }

            void EyePassFragment(Varyings input,out half4 outColor:SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                ,out uint outRenderingLayers:SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                SurfaceData surfaceData;
                InitializeStandardLitSurfaceData(input.uv,surfaceData);
                surfaceData.albedo*=EyeColourWash(input.uv);
                InputData inputData;
                InitializeInputData(input,surfaceData.normalTS,inputData);
                InitializeBakedGIData(input,inputData);
                half4 colour=UniversalFragmentPBR(inputData,surfaceData);
                colour.rgb=MixFog(colour.rgb,inputData.fogCoord);
                colour.a=1;
                outColor=colour;
            #ifdef _WRITE_RENDERING_LAYERS
                outRenderingLayers=EncodeMeshRenderingLayer();
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

