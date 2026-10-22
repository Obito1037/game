Shader "BorrowedLight/PaintedSurface"
{
    Properties
    {
        [MainColor] _BaseColor("Painted colour", Color) = (0.55,0.53,0.48,1)
        [MainTexture] _BaseMap("Base map (depth-pass compatibility)", 2D) = "white" {}
        _Smoothness("Smoothness", Range(0,1)) = 0.17
        _Metallic("Metallic", Range(0,1)) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull", Float) = 2
        [Enum(Stone,0,Wood,1,Plaster,2,OldTiles,3,Cloth,5)] _SurfaceKind("Painted surface", Float) = 0

        // Official Lit auxiliary passes use these same defaults / material fields.
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
            Name "PaintedForward"
            Tags { "LightMode"="UniversalForward" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex LitPassVertex
            #pragma fragment PaintedPassFragment
            #pragma multi_compile_instancing

            // Keep the light / shadow / SSAO paths of the installed URP Lit pass.
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

            // Reuse the official material layout, vertex pass and InputData/GI setup.
            // The procedural pattern never samples mesh UVs or imported image data.
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #ifndef REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
                #define REQUIRES_WORLD_SPACE_POS_INTERPOLATOR
            #endif
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitForwardPass.hlsl"

            // Outside Lit's immutable UnityPerMaterial layout so the three official
            // UsePass entries retain exactly their expected field offsets.
            float _SurfaceKind;

            float PaintHash(float3 p)
            {
                p = frac(p * 0.1031);
                p += dot(p, p.yzx + 33.33);
                return frac((p.x + p.y) * p.z);
            }

            float PaintNoise(float3 p)
            {
                float3 cell = floor(p);
                float3 f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                float a = lerp(PaintHash(cell), PaintHash(cell + float3(1,0,0)), f.x);
                float b = lerp(PaintHash(cell + float3(0,1,0)), PaintHash(cell + float3(1,1,0)), f.x);
                float c = lerp(PaintHash(cell + float3(0,0,1)), PaintHash(cell + float3(1,0,1)), f.x);
                float d = lerp(PaintHash(cell + float3(0,1,1)), PaintHash(cell + float3(1,1,1)), f.x);
                return lerp(lerp(a,b,f.y), lerp(c,d,f.y), f.z);
            }

            half3 PaintedAlbedo(float3 worldPosition, half3 worldNormal, out float relief)
            {
                relief = 0;
                // Metre-based world coordinates keep adjacent meshes visually related.
                float3 p = worldPosition + float3(17.4, 6.2, -9.7);
                float broad = PaintNoise(p * 0.78);
                float variation;
                half3 colour = _BaseColor.rgb;

                if (_SurfaceKind < 0.5)
                {
                    float mineral = PaintNoise(p * 7.5 + float3(5.2,1.7,8.4));
                    variation = (broad - 0.5) * 0.32 + (mineral - 0.5) * 0.16;
                    relief = broad * 0.018 + mineral * 0.012;
                    colour *= 1.0 + variation;

                    // Small, soft-edged patches on upward-facing rock; no green speckle.
                    float moss = smoothstep(0.56, 0.79, PaintNoise(p * 1.35 + float3(4.1,0.7,2.3)));
                    moss *= smoothstep(0.25, 0.82, worldNormal.y) * 0.24;
                    half luminance = dot(colour, half3(0.2126,0.7152,0.0722));
                    half3 mossColour = half3(0.63,0.83,0.57) * max(luminance, 0.03h);
                    colour = lerp(colour, mossColour, moss);
                }
                else if (_SurfaceKind < 1.5)
                {
                    // Vertical beams have long fibres; horizontal planks use a quiet
                    // world-space grain. A derivative fade prevents distant shimmer.
                    float2 grainUV = abs(worldNormal.y) > 0.55 ? p.zx : float2(p.x + p.z * 0.71, p.y);
                    float longGrain = PaintNoise(float3(grainUV.x * 7.0, grainUV.y * 0.55, 3.7));
                    float warp = PaintNoise(float3(grainUV.x * 1.6, grainUV.y * 0.65, 9.1));
                    float phase = grainUV.x * 58.0 + warp * 5.0;
                    float grainFade = saturate(1.0 - fwidth(phase) * 0.2);
                    float fibre = smoothstep(0.68, 0.98, sin(phase)) * grainFade;
                    variation = (broad - 0.5) * 0.22 + (longGrain - 0.5) * 0.16 - fibre * 0.055;
                    relief = longGrain * 0.004 - fibre * 0.002;
                    colour *= 1.0 + variation;
                }
                else if (_SurfaceKind < 2.5)
                {
                    // A broad wash with faint paper fibres, rather than gritty plaster.
                    float paper = PaintNoise(p * float3(4.3,52.0,5.7));
                    float wash = PaintNoise(p * 2.1 + float3(2.2,7.4,1.1));
                    variation = (broad - 0.5) * 0.12 + (wash - 0.5) * 0.055 + (paper - 0.5) * 0.025;
                    relief = paper * 0.0015;
                    colour *= 1.0 + variation;
                }
                else if (_SurfaceKind < 3.5)
                {
                    // Existing tile geometry supplies the seams; this only varies glaze.
                    float glaze = PaintNoise(p * float3(4.7,2.3,4.1));
                    float dust = PaintNoise(p * 13.5 + float3(0.2,8.7,3.4));
                    variation = (broad - 0.5) * 0.13 + (glaze - 0.5) * 0.09 + (dust - 0.5) * 0.035;
                    relief = glaze * 0.004;
                    colour *= 1.0 + variation;
                }
                else
                {
                    // Very shallow, derivative-filtered cloth weave. It disappears
                    // at gameplay distance rather than producing shimmering threads.
                    float3 local = TransformWorldToObject(worldPosition);
                    float3 localNormal = abs(TransformWorldToObjectDir(worldNormal));
                    float2 fabricUV = localNormal.z > max(localNormal.x,localNormal.y) ? local.xy
                        : localNormal.y > localNormal.x ? local.xz : local.zy;
                    float2 thread = fabricUV * 900.0;
                    float weaveFade = saturate(1.0 - max(fwidth(thread.x), fwidth(thread.y)) * 0.4);
                    float weave = sin(thread.x) * sin(thread.y) * weaveFade;
                    float wornDye = PaintNoise(local * 31.0);
                    colour *= 1.0 + (broad - 0.5) * 0.06 + (wornDye - 0.5) * 0.08 + weave * 0.01;
                    relief = weave * 0.00003;
                }
                return max(colour, half3(0.0,0.0,0.0));
            }

            void PaintedPassFragment(Varyings input,
                out half4 outColor : SV_Target0
            #ifdef _WRITE_RENDERING_LAYERS
                , out uint outRenderingLayers : SV_Target1
            #endif
            )
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

                SurfaceData surfaceData = (SurfaceData)0;
                float relief;
                surfaceData.albedo = PaintedAlbedo(input.positionWS, normalize(input.normalWS), relief);
                surfaceData.metallic = saturate(_Metallic);
                surfaceData.specular = _SpecColor.rgb;
                surfaceData.smoothness = saturate(_Smoothness);
                surfaceData.normalTS = half3(0,0,1);
                surfaceData.occlusion = 1;
                surfaceData.emission = _EmissionColor.rgb;
                surfaceData.alpha = 1;
                surfaceData.clearCoatMask = 0;
                surfaceData.clearCoatSmoothness = 0;

                InputData inputData;
                InitializeInputData(input, surfaceData.normalTS, inputData);
                // Derivative bump gives stone pores and wood grain a small response
                // to moving light without extra texture memory or mesh density.
                float3 dx = ddx(input.positionWS), dy = ddy(input.positionWS);
                float3 r1 = cross(dy, inputData.normalWS), r2 = cross(inputData.normalWS, dx);
                float determinant = dot(dx, r1);
                float3 gradient = (ddx(relief) * r1 + ddy(relief) * r2)
                    * sign(determinant) / max(abs(determinant), 0.00001);
                inputData.normalWS = normalize(inputData.normalWS - gradient);
                InitializeBakedGIData(input, inputData);
                // Foliage has its own fixed shader, so solid surfaces compile only PBR.
                half4 colour = UniversalFragmentPBR(inputData, surfaceData);
                colour.rgb = MixFog(colour.rgb, inputData.fogCoord);
                colour.a = 1;
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
