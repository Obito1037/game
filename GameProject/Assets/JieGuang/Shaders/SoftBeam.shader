// A thin visible lamp beam, independent of the Spot light that illuminates the island.
// One cone shell and one opaque-depth sample per fragment; no volumetric ray marching.
Shader "JieGuang/SoftBeam"
{
    Properties
    {
        _BaseColor ("Beam colour", Color) = (1, 0.7, 0.38, 1)
        _BeamDensity ("Linear beam density", Range(0, 0.1)) = 0.018
        _EdgeSoftness ("Silhouette softness", Range(0.05, 1)) = 1
        _DepthFade ("Opaque contact fade (metres)", Float) = 0.35
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Name "SoftBeam"
            Tags { "LightMode"="UniversalForward" }
            // Density is multiplied exactly once in the fragment, independent of Color.a.
            Blend One One
            ColorMask RGB
            ZWrite Off
            ZTest LEqual
            Cull Off

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                float _BeamDensity;
                float _EdgeSoftness;
                float _DepthFade;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float along : TEXCOORD2;
            };

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.positionWS = TransformObjectToWorld(input.positionOS.xyz);
                output.positionCS = TransformWorldToHClip(output.positionWS);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.along = input.uv.y;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float3 normalWS = normalize(input.normalWS);
                float3 viewWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
                // Both sides belong to the same shell. Grazing silhouettes fade to zero,
                // while its centre stays visibly warm even with the narrow shade fitted.
                float facing = abs(dot(normalWS, viewWS));
                float sideFade = smoothstep(0.0, max(_EdgeSoftness, 0.05), facing);
                float along = saturate(input.along);
                float lengthFade = smoothstep(0.0, 0.025, along)
                                 * (1.0 - smoothstep(0.1, 1.0, along));

                float eyeDepth = -TransformWorldToView(input.positionWS).z;
                float rawDepth = SampleSceneDepth(GetNormalizedScreenSpaceUV(input.positionCS));
                float sceneDepth = unity_OrthoParams.w == 0.0
                    ? LinearEyeDepth(rawDepth, _ZBufferParams)
                    : LinearDepthToEyeDepth(rawDepth);
                // _CameraDepthTexture contains opaque terrain, rocks and characters only.
                // The transparent sea and this shell do not write into it.
                float contactFade = smoothstep(0.0, max(_DepthFade, 0.001), sceneDepth - eyeDepth);
                float cameraFade = smoothstep(0.12, 0.45, eyeDepth);
                float density = saturate(_BeamDensity) * sideFade * lengthFade * contactFade * cameraFade;
                return half4(_BaseColor.rgb * density, 0.0);
            }
            ENDHLSL
        }
    }
}
