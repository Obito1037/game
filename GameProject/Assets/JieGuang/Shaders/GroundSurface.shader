Shader "JieGuang/GroundSurface"
{
    Properties
    {
        _GrassMap("Existing grass texture", 2D) = "white" {}
        _DirtMap("Existing dirt texture", 2D) = "white" {}
        _StoneMap("Existing path texture", 2D) = "white" {}
        _CliffMap("Existing cliff texture", 2D) = "white" {}
        _RockStart("Rock fully shown below this normal.y", Float) = 0.809
        _RockEnd("Grass fully shown above this normal.y", Float) = 0.927
        _GrassVariation("Large-scale grass colour variation", Float) = 0
    }
    SubShader
    {
        Tags { "RenderPipeline"="UniversalPipeline" "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Back
        ZWrite On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_GrassMap); SAMPLER(sampler_GrassMap);
        TEXTURE2D(_DirtMap); SAMPLER(sampler_DirtMap);
        TEXTURE2D(_StoneMap); SAMPLER(sampler_StoneMap);
        TEXTURE2D(_CliffMap); SAMPLER(sampler_CliffMap);
        CBUFFER_START(UnityPerMaterial)
            float4 _GrassMap_ST, _DirtMap_ST, _StoneMap_ST, _CliffMap_ST;
            float _RockStart, _RockEnd, _GrassVariation;
        CBUFFER_END
        struct Attributes
        {
            float4 positionOS : POSITION;
            float3 normalOS : NORMAL;
            half4 color : COLOR;
            UNITY_VERTEX_INPUT_INSTANCE_ID
        };
        struct Varyings
        {
            float4 positionCS : SV_POSITION;
            float3 positionWS : TEXCOORD0;
            half3 normalWS : TEXCOORD1;
            half4 weights : TEXCOORD2;
            half fog : TEXCOORD3;
            UNITY_VERTEX_INPUT_INSTANCE_ID
            UNITY_VERTEX_OUTPUT_STEREO
        };
        Varyings GroundVertex(Attributes v)
        {
            Varyings o = (Varyings)0;
            UNITY_SETUP_INSTANCE_ID(v);
            UNITY_TRANSFER_INSTANCE_ID(v,o);
            UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
            o.positionCS = TransformWorldToHClip(o.positionWS);
            o.normalWS = TransformObjectToWorldNormal(v.normalOS);
            o.weights = v.color;
            o.fog = ComputeFogFactor(o.positionCS.z);
            return o;
        }
        ENDHLSL
        Pass
        {
            Name "GroundForward"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex GroundVertex
            #pragma fragment GroundFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            float RockHash(float2 p)
            {
                float3 q = frac(float3(p.x,p.y,p.x) * .1031);
                q += dot(q,q.yzx + 33.33);
                return frac((q.x+q.y)*q.z);
            }
            float RockNoise(float2 p)
            {
                float2 cell = floor(p), f = frac(p);
                f = f*f*(3-2*f);
                return lerp(lerp(RockHash(cell),RockHash(cell+float2(1,0)),f.x),
                            lerp(RockHash(cell+float2(0,1)),RockHash(cell+float2(1,1)),f.x),f.y);
            }
            float2 RockOblique(float2 uv)
            {
                return float2(.857*uv.x-.515*uv.y,.515*uv.x+.857*uv.y) + float2(2.137,5.791);
            }
            half4 GroundFragment(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                half3 n = normalize(i.normalWS);
                half3 weights = max(i.weights.rgb,0);
                weights /= max(dot(weights,half3(1,1,1)),.001);
                half3 grass = SAMPLE_TEXTURE2D(_GrassMap,sampler_GrassMap,i.positionWS.xz/3.2).rgb * half3(1.18,1.05,1.14);
                half3 dirt = SAMPLE_TEXTURE2D(_DirtMap,sampler_DirtMap,i.positionWS.xz/2.6).rgb * half3(1.05,1.08,1.12);
                half3 stone = SAMPLE_TEXTURE2D(_StoneMap,sampler_StoneMap,i.positionWS.xz/2.2).rgb;
                half rockWeight = max(i.weights.a,1-smoothstep(_RockStart,_RockEnd,n.y));
                half3 rock = 0;
                float broad = RockNoise((i.positionWS.xz + i.positionWS.y*float2(.37,-.29))*.31);
                // Most ground is grass: skip the six triplanar rock samples where no rock shows.
                // explicit gradients: texture sampling inside a dynamic branch must not use implicit ones
                float3 dpx = ddx(i.positionWS), dpy = ddy(i.positionWS);
                UNITY_BRANCH if (rockWeight > 0.003)
                {
                // Side projections keep vertical rock texels square. Blending all three axes
                // removes UV seams where the exact original mesh turns around the coastline.
                half3 blend = pow(abs(n),4);
                blend /= max(dot(blend,half3(1,1,1)),.001);
                // The retained T04 has nine regular bands per tile. Two cheap, nonperiodic
                // world-space noise scales bend their phase; an oblique larger-scale repeat
                // breaks long matching contours without adding any new image resource.
                float2 noisePlane = i.positionWS.xz + i.positionWS.y*float2(.37,-.29);
                float detail = RockNoise(noisePlane*.83 + float2(17.3,41.7));
                float3 rockPosition = i.positionWS;
                rockPosition.y += (broad-.5)*1.65 + (detail-.5)*.48;
                rockPosition.xz += float2(detail-.5,broad-.5)*.55;
                half3 rockX = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,rockPosition.zy/3.5,dpx.zy/3.5,dpy.zy/3.5).rgb;
                half3 rockY = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,rockPosition.xz/3.5,dpx.xz/3.5,dpy.xz/3.5).rgb;
                half3 rockZ = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,rockPosition.xy/3.5,dpx.xy/3.5,dpy.xy/3.5).rgb;
                half3 largeX = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,RockOblique(rockPosition.zy/5.7),dpx.zy/5.7,dpy.zy/5.7).rgb;
                half3 largeY = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,RockOblique(rockPosition.xz/5.7),dpx.xz/5.7,dpy.xz/5.7).rgb;
                half3 largeZ = SAMPLE_TEXTURE2D_GRAD(_CliffMap,sampler_CliffMap,RockOblique(rockPosition.xy/5.7),dpx.xy/5.7,dpy.xy/5.7).rgb;
                half3 fineRock = rockX*blend.x+rockY*blend.y+rockZ*blend.z;
                half3 largeRock = largeX*blend.x+largeY*blend.y+largeZ*blend.z;
                rock = lerp(largeRock,fineRock,.4);
                // Compress fine-band contrast around the retained T04's approximate linear
                // mean, then restore quiet metre-scale variation rather than uniform grey.
                rock = lerp(half3(.074,.069,.065),rock,.72) * (.91+.18*broad);
                rock *= half3(1.18,1.23,1.28);
                }
                grass *= lerp(1, lerp(half3(.82,.92,.78), half3(1.12,1.04,.86), broad), _GrassVariation);
                half3 albedo = lerp(grass*weights.r+dirt*weights.g+stone*weights.b,rock,rockWeight);
                InputData lightInput = (InputData)0;
                lightInput.positionWS = i.positionWS;
                lightInput.normalWS = n;
                lightInput.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                #if defined(_MAIN_LIGHT_SHADOWS_SCREEN)
                    lightInput.shadowCoord = ComputeScreenPos(TransformWorldToHClip(i.positionWS));
                #else
                    lightInput.shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                #endif
                lightInput.bakedGI = SampleSH(n);
                lightInput.shadowMask = half4(1,1,1,1);
                lightInput.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                lightInput.vertexLighting = VertexLighting(i.positionWS,n);
                SurfaceData surface = (SurfaceData)0;
                surface.albedo = albedo;
                surface.alpha = 1;
                surface.occlusion = 1;
                surface.normalTS = half3(0,0,1);
                surface.smoothness = .04;
                half4 color = UniversalFragmentPBR(lightInput,surface);
                color.rgb = MixFog(color.rgb,i.fog);
                return half4(color.rgb,1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ColorMask 0
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex GroundShadowVertex
            #pragma fragment GroundShadowFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            float3 _LightDirection;
            float3 _LightPosition;
            Varyings GroundShadowVertex(Attributes v)
            {
                Varyings o = GroundVertex(v);
                #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                    float3 direction = normalize(_LightPosition-o.positionWS);
                #else
                    float3 direction = _LightDirection;
                #endif
                o.positionCS = TransformWorldToHClip(ApplyShadowBias(o.positionWS,normalize(o.normalWS),direction));
                o.positionCS = ApplyShadowClamping(o.positionCS);
                return o;
            }
            half4 GroundShadowFragment(Varyings i) : SV_Target { return 0; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ColorMask R
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex GroundVertex
            #pragma fragment GroundDepthFragment
            #pragma multi_compile_instancing
            half4 GroundDepthFragment(Varyings i) : SV_Target { return i.positionCS.z; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex GroundVertex
            #pragma fragment GroundNormalFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            half4 GroundNormalFragment(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
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
