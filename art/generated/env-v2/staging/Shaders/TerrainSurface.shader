Shader "JieGuang/Environment/TerrainSurface"
{
    Properties
    {
        [Enum(Ground,0,Stone,1,Cliff,2)] _SurfaceMode("Surface mode", Float) = 0
        _BaseMap("Original meadow albedo", 2D) = "white" {}
        _BaseColor("Primary neutral colour", Color) = (0.25,0.32,0.27,1)
        _SecondaryColor("Secondary neutral colour", Color) = (0.16,0.22,0.185,1)
        _SoilColor("Deep neutral soil", Color) = (0.145,0.16,0.15,1)
        _TextureMeters("Ground texture repeat metres", Range(0.5,8)) = 2
        _TexturePivot("Linear albedo luminance midpoint", Range(0.04,0.6)) = 0.18
        _TextureContrast("Texture luminance contrast", Range(0,1)) = 0.32
        _TextureChroma("Retained source colour", Range(0,0.5)) = 0.08
        _MacroMeters("Broad colour patch metres", Range(2,12)) = 5.5
        _SoilAmount("Ground soil blend", Range(0,1)) = 0.14
        _StoneMeters("Stone variation metres", Range(0.15,4)) = 0.85
        _CliffMeters("Triplanar rock feature metres", Range(0.5,8)) = 2.7
        _LayerMeters("Irregular geological layer metres", Range(0.3,4)) = 1.3
        _DetailStrength("Fine surface colour variation", Range(0,0.4)) = 0.10
        _Roughness("Roughness", Range(0.5,1)) = 0.88
        _RoughnessVariation("Roughness variation", Range(0,0.2)) = 0.045
        _ReliefMeters("Derivative bump height metres (0 disables)", Range(0,0.04)) = 0.004
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" "RenderPipeline"="UniversalPipeline" }
        Cull Back ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Packing.hlsl"
        TEXTURE2D(_BaseMap);
        SAMPLER(sampler_BaseMap);
        CBUFFER_START(UnityPerMaterial)
            half4 _BaseColor, _SecondaryColor, _SoilColor;
            float4 _BaseMap_ST;
            float _SurfaceMode, _TextureMeters, _TexturePivot, _MacroMeters, _StoneMeters, _CliffMeters, _LayerMeters;
            half _TextureContrast, _TextureChroma, _SoilAmount, _DetailStrength, _Roughness, _RoughnessVariation;
            float _ReliefMeters;
        CBUFFER_END
        float3 _LightDirection;
        float3 _LightPosition;

        struct Attributes
        {
            float4 positionOS : POSITION;
            float3 normalOS : NORMAL;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };
        struct Varyings
        {
            float4 positionCS : SV_POSITION;
            float3 positionWS : TEXCOORD0;
            half3 normalWS : TEXCOORD1;
            half4 fogAndVertexLight : TEXCOORD2;
            float4 shadowCoord : TEXCOORD3;
            UNITY_VERTEX_INPUT_INSTANCE_ID
            UNITY_VERTEX_OUTPUT_STEREO
        };

        // Texture-free value noise, no sine stripes, random grid lines or cellular outlines.
        float Hash2(float2 p)
        {
            float3 q = frac(float3(p.x,p.y,p.x) * 0.1031);
            q += dot(q, q.yzx + 33.33);
            return frac((q.x + q.y) * q.z);
        }
        float Noise(float2 p)
        {
            float2 cell = floor(p), f = frac(p);
            f = f*f*(3-2*f);
            return lerp(lerp(Hash2(cell),Hash2(cell+float2(1,0)),f.x),lerp(Hash2(cell+float2(0,1)),Hash2(cell+1),f.x),f.y);
        }
        float TriplanarNoise(float3 p, float3 weights)
        {
            return Noise(p.yz+float2(7.7,1.3))*weights.x
                 + Noise(p.xz+float2(19.4,2.8))*weights.y
                 + Noise(p.xy+float2(3.6,23.2))*weights.z;
        }

        // Height is used only for a small screen-derivative surface normal. No displacement,
        // tessellation, generated geometry or imported normal texture is used.
        void EvaluateSurface(float3 p, half3 geometricNormal, out half3 albedo, out half roughness, out float height)
        {
            float macro = Noise(p.xz/max(_MacroMeters,0.1)+float2(17.3,-8.1));
            float pattern, detail;
            UNITY_BRANCH if (_SurfaceMode < 0.5)
            {
                float2 uv = p.xz/max(_TextureMeters,0.1);
                // Two stationary projections of the same original map soften exact repetition.
                half3 texA = SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,uv).rgb;
                float2 secondUV = float2(uv.x*0.82+uv.y*0.57,-uv.x*0.57+uv.y*0.82)*0.713+float2(0.37,0.61);
                half3 texB = SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,secondUV).rgb;
                half3 sampleColor = lerp(texA,texB,0.27h);
                float luminance = dot(sampleColor,half3(0.2126,0.7152,0.0722));
                float neutralDetail = clamp(luminance/max(_TexturePivot,0.01),0.45,1.75);
                float gain = lerp(1,neutralDetail,_TextureContrast);
                half3 chroma = clamp(sampleColor/max(luminance,0.02),0.45h,1.55h);
                albedo = lerp(_BaseColor.rgb,_SecondaryColor.rgb,smoothstep(0.20,0.80,macro));
                albedo *= gain * lerp(half3(1,1,1),chroma,_TextureChroma);
                float soil = smoothstep(0.45,0.82,macro) * _SoilAmount;
                albedo = lerp(albedo,_SoilColor.rgb*gain,soil);
                detail = saturate(neutralDetail*0.55);
                pattern = macro;
                height = luminance * _ReliefMeters;
            }
            else if (_SurfaceMode < 1.5)
            {
                float2 uv = p.xz/max(_StoneMeters,0.1);
                pattern = Noise(float2(uv.x*0.93+uv.y*0.36,uv.y*0.93-uv.x*0.36));
                detail = Noise(uv*5.2+float2(23.7,7.3));
                // No false tile grid or black cracks: existing stone mesh defines each slab.
                albedo = lerp(_BaseColor.rgb,_SecondaryColor.rgb,smoothstep(0.16,0.84,pattern));
                albedo *= 1+(detail-0.5)*_DetailStrength;
                height = (pattern*0.65+detail*0.35)*_ReliefMeters;
            }
            else
            {
                float3 weights = abs(geometricNormal);
                weights *= weights; weights *= weights;
                weights /= max(dot(weights,float3(1,1,1)),0.0001);
                float3 localRock = p/max(_CliffMeters,0.1);
                float broad = TriplanarNoise(localRock,weights);
                detail = TriplanarNoise(localRock*3.8+float3(2.3,9.1,17.7),weights);
                // Geological changes are warped noise bands, not periodic horizontal sine lines.
                float warp = Noise(p.xz*0.31+float2(13.4,7.6))*1.15;
                float strata = Noise(float2(p.y+warp,p.x*0.09+p.z*0.13)/max(_LayerMeters,0.1)+float2(2.1,41.3));
                pattern = saturate(broad*0.65+strata*0.35);
                albedo = lerp(_BaseColor.rgb,_SecondaryColor.rgb,smoothstep(0.12,0.87,pattern));
                albedo *= 1+(detail-0.5)*_DetailStrength;
                height = (broad*0.45+strata*0.35+detail*0.20)*_ReliefMeters;
            }
            albedo = max(albedo,half3(0.001,0.001,0.001));
            roughness = saturate(_Roughness+(detail-0.5)*_RoughnessVariation);
        }

        float3 SurfaceSafeNormal(float3 normalWS)
        {
            float lengthSquared = dot(normalWS, normalWS);
            return lengthSquared > 1e-10 ? normalWS * rsqrt(max(lengthSquared, 1e-10)) : float3(0,1,0);
        }
        half3 SurfaceNormal(float3 positionWS, half3 geometricNormal, float height)
        {
            half3 n = SurfaceSafeNormal(geometricNormal);
            float3 dx = ddx(positionWS), dy = ddy(positionWS);
            float3 r1 = cross(dy,n), r2 = cross(n,dx);
            float determinant = dot(dx,r1);
            float3 gradient = sign(determinant)*(ddx(height)*r1+ddy(height)*r2);
            float3 bumped = abs(determinant)*n-gradient;
            float lengthSquared = dot(bumped,bumped);
            return abs(determinant)>1e-10 && lengthSquared>1e-30 ? bumped*rsqrt(max(lengthSquared,1e-30)) : n;
        }
        Varyings SurfaceVertex(Attributes input)
        {
            Varyings output = (Varyings)0;
            UNITY_SETUP_INSTANCE_ID(input);
            UNITY_TRANSFER_INSTANCE_ID(input,output);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
            VertexPositionInputs positions = GetVertexPositionInputs(input.positionOS.xyz);
            output.positionCS = positions.positionCS;
            output.positionWS = positions.positionWS;
            output.normalWS = TransformObjectToWorldNormal(input.normalOS);
            output.fogAndVertexLight = half4(ComputeFogFactor(positions.positionCS.z),VertexLighting(positions.positionWS,output.normalWS));
            output.shadowCoord = GetShadowCoord(positions);
            return output;
        }
        Varyings SurfaceShadowVertex(Attributes input)
        {
            Varyings output = SurfaceVertex(input);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 lightDirectionWS = SafeNormalize(_LightPosition-output.positionWS);
            #else
                float3 lightDirectionWS = _LightDirection;
            #endif
            output.positionCS = TransformWorldToHClip(ApplyShadowBias(output.positionWS,output.normalWS,lightDirectionWS));
            output.positionCS = ApplyShadowClamping(output.positionCS);
            return output;
        }
        half4 SurfaceFragment(Varyings input) : SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(input);
            UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
            half3 albedo; half roughness; float height;
            EvaluateSurface(input.positionWS,SurfaceSafeNormal(input.normalWS),albedo,roughness,height);
            InputData inputData = (InputData)0;
            inputData.positionWS = input.positionWS;
            inputData.positionCS = input.positionCS;
            inputData.normalWS = SurfaceNormal(input.positionWS,input.normalWS,height);
            inputData.viewDirectionWS = SafeNormalize(GetWorldSpaceViewDir(input.positionWS));
            // Cascades are selected from fragment position, as in URP LitForwardPass.
            #if defined(REQUIRES_VERTEX_SHADOW_COORD_INTERPOLATOR)
                inputData.shadowCoord = input.shadowCoord;
            #elif defined(MAIN_LIGHT_CALCULATE_SHADOWS)
                inputData.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
            #else
                inputData.shadowCoord = float4(0,0,0,0);
            #endif
            inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
            inputData.shadowMask = half4(1,1,1,1);
            inputData.bakedGI = SampleSH(inputData.normalWS);
            inputData.vertexLighting = input.fogAndVertexLight.yzw;
            inputData.fogCoord = InitializeInputDataFog(float4(input.positionWS,1),input.fogAndVertexLight.x);
            SurfaceData surface = (SurfaceData)0;
            surface.albedo = albedo;
            surface.specular = half3(0.04,0.04,0.04);
            surface.metallic = 0;
            surface.smoothness = 1-roughness;
            surface.normalTS = half3(0,0,1);
            surface.occlusion = 1;
            surface.alpha = 1;
            surface.emission = 0;
            half4 color = UniversalFragmentPBR(inputData,surface);
            color.rgb = MixFog(color.rgb,inputData.fogCoord);
            return color;
        }
        half4 SurfaceDepthFragment(Varyings input) : SV_Target { return 0; }
        half4 SurfaceNormalsFragment(Varyings input) : SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(input);
            half3 albedo; half roughness; float height;
            EvaluateSurface(input.positionWS,SurfaceSafeNormal(input.normalWS),albedo,roughness,height);
            half3 normalWS = SurfaceNormal(input.positionWS,input.normalWS,height);
            #if defined(_GBUFFER_NORMALS_OCT)
                return half4(PackFloat2To888(saturate(PackNormalOctQuadEncode(normalWS)*0.5+0.5)),0);
            #else
                return half4(normalWS,0);
            #endif
        }
        ENDHLSL

        Pass
        {
            Name "TerrainSurfaceForward"
            Tags { "LightMode"="UniversalForwardOnly" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex SurfaceVertex
            #pragma fragment SurfaceFragment
            #pragma multi_compile_instancing
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            ENDHLSL
        }
        Pass
        {
            Name "TerrainSurfaceShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ColorMask 0
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex SurfaceShadowVertex
            #pragma fragment SurfaceDepthFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            ENDHLSL
        }
        Pass
        {
            Name "TerrainSurfaceDepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ColorMask R
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex SurfaceVertex
            #pragma fragment SurfaceDepthFragment
            #pragma multi_compile_instancing
            ENDHLSL
        }
        Pass
        {
            Name "TerrainSurfaceDepthNormals"
            Tags { "LightMode"="DepthNormalsOnly" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex SurfaceVertex
            #pragma fragment SurfaceNormalsFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            ENDHLSL
        }
    }
    Fallback Off
}
