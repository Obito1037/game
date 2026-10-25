// Quiet blue water. Broad earthlight and warm lamp reflections stay separate from the
// low-contrast water colour; ripples never turn the whole ocean into bright marble stripes.
Shader "JieGuang/NightSea"
{
    Properties
    {
        _Deep ("Deep water", Color) = (0.008, 0.027, 0.060, 1)
        _Shallow ("Near water", Color) = (0.025, 0.075, 0.095, 1)
        _WaveHeight ("Swell height", Float) = 0.035
        _Ripple ("Ripple strength", Range(0, 0.3)) = 0.10
        _Fresnel ("Sky reflection", Range(0, 1)) = 0.5
        _Gloss ("Glint sharpness", Float) = 180
        _EarthReflection ("Earth reflection", Range(0, 2)) = 0.65
        _FoamWidth ("Shore foam depth", Float) = 0.9
        _Foam ("Shore foam", Range(0, 1)) = 0.65
        _FoamColor ("Foam colour", Color) = (0.26, 0.42, 0.48, 1)
    }
    SubShader
    {
        // Draw after the opaque depth copy. The sea itself must not enter the depth texture,
        // otherwise its own zero depth gap would turn the whole surface into foam.
        Tags { "RenderType"="Transparent" "Queue"="Transparent-100" "RenderPipeline"="UniversalPipeline" }
        Pass
        {
            Tags { "LightMode"="UniversalForward" }
            ZWrite Off
            // The source ocean is a finite 300 m quad. Its outer ring fades into the sky's
            // lower hemisphere, hiding the square silhouette without adding distant geometry.
            Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
            float4 _Deep, _Shallow, _FoamColor;
            float _WaveHeight, _Ripple, _Fresnel, _Gloss, _EarthReflection, _FoamWidth, _Foam;
            CBUFFER_END
            float4 _JG_SkyHorizon, _JG_SkyZenith;
            float4 _JG_EarthDirection, _JG_EarthReflectionColor;

            struct A { float4 pos : POSITION; };
            struct V { float4 pos : SV_POSITION; float3 ws : TEXCOORD0; float2 localXZ : TEXCOORD1; };

            float swell(float2 p, float t)
            {
                return sin(dot(p, float2(0.19, 0.13)) + t * 0.42) * 0.6
                     + sin(dot(p, float2(-0.12, 0.24)) - t * 0.31) * 0.4;
            }

            V vert(A i)
            {
                V o;
                float3 ws = TransformObjectToWorld(i.pos.xyz);
                ws.y += swell(ws.xz, _Time.y) * _WaveHeight;
                o.ws = ws;
                o.pos = TransformWorldToHClip(ws);
                o.localXZ = i.pos.xz;
                return o;
            }

            float hash21(float2 p)
            {
                p = frac(p * float2(123.34, 456.21));
                p += dot(p, p + 45.32);
                return frac(p.x * p.y);
            }

            float noise(float2 p)
            {
                float2 cell = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash21(cell), hash21(cell + float2(1, 0)), f.x),
                            lerp(hash21(cell + float2(0, 1)), hash21(cell + 1), f.x), f.y);
            }

            // Fade frequencies as they approach pixel size, avoiding shimmer at the horizon.
            float2 ripples(float2 p, float t, float footprint)
            {
                float2 g = float2(0.8, 0.6) * cos(dot(p, float2(0.64, 0.48)) + t * 0.7) * 0.38;
                g += float2(-0.32, 0.95) * cos(dot(p, float2(-0.54, 1.61)) - t * 0.81) * 0.28 * exp(-footprint * 1.7);
                g += float2(0.94, -0.34) * cos(dot(p, float2(3.29, -1.19)) + t * 1.18) * 0.2 * exp(-footprint * 3.5);
                return g;
            }

            // Narrow across the light, broad towards the viewer: a broken long reflection trail.
            float reflectionTrail(float3 lightDir, float3 viewDir, float2 gradient, float width, float lengthwise)
            {
                float3 h = SafeNormalize(lightDir + viewDir);
                float2 along = lightDir.xz * rsqrt(max(dot(lightDir.xz, lightDir.xz), 0.0001));
                float2 across = float2(-along.y, along.x);
                float2 slope = h.xz / max(h.y, 0.08) + gradient;
                float sx = dot(slope, across) / width;
                float sy = dot(slope, along) / lengthwise;
                return exp(-sx * sx - sy * sy) * saturate(lightDir.y * 5.0);
            }

            half4 frag(V i) : SV_Target
            {
                float t = _Time.y;
                float2 screenUV = GetNormalizedScreenSpaceUV(i.pos);
                float footprint = max(length(ddx(i.ws.xz)), length(ddy(i.ws.xz)));
                float2 g = ripples(i.ws.xz, t, footprint) * min(_Ripple, 0.18);
                float3 n = normalize(float3(-g.x, 1, -g.y));
                float3 v = SafeNormalize(GetWorldSpaceViewDir(i.ws));
                // Use the mean normal for broad Fresnel colour, and ripple normals only for
                // the glints. This prevents white ribbons across all of the distant water.
                float fres = pow(1 - saturate(v.y), 5);
                float3 r = reflect(-v, n);
                float3 sky = lerp(_JG_SkyHorizon.rgb, _JG_SkyZenith.rgb, saturate(r.y));
                float dist = length(i.ws - _WorldSpaceCameraPos);

                float surfaceDepth = -TransformWorldToView(i.ws).z;
                float verticalDepth = 100.0;
                // Beyond the island's shore there is neither contact foam nor a nearby lamp.
                // Avoid a depth sample and the expensive clustered light loop over far water.
                if (dist < 90.0)
                {
                    float rawDepth = SampleSceneDepth(screenUV);
                    float sceneDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                    float gap = max(sceneDepth - surfaceDepth, 0);
                    verticalDepth = gap * max(v.y, 0.18);
                }
                float nearShore = 1 - smoothstep(0.15, 3.0, verticalDepth);
                float3 water = lerp(_Deep.rgb, _Shallow.rgb, nearShore * 0.8);
                // A little diffuse sky bounce keeps the unlit water readable under ACES.
                // It is low-contrast blue, not the old high-amplitude grey normal stripes.
                water = max(water, _JG_SkyHorizon.rgb * 0.13);
                float3 col = lerp(water, sky, saturate(fres * _Fresnel + 0.06));
                col *= 0.975 + 0.025 * swell(i.ws.xz, t);

                // broken glitter instead of a regular sine: no parallel stripes inside the long trail
                float micro = 0.45 + 0.9 * smoothstep(0.3, 0.85, noise(i.ws.xz * float2(0.9, 2.3) + float2(t * 0.35, -t * 0.2)) * 0.6 + noise(i.ws.xz * float2(2.7, 5.1) - t * 0.5) * 0.4);
                float3 earthDir = SafeNormalize(_JG_EarthDirection.xyz);
                float trail = reflectionTrail(earthDir, v, g * 0.7, 0.075, 0.48);
                col += _JG_EarthReflectionColor.rgb * trail * micro * _EarthReflection;

                // Real lights: puzzle lamps and the lantern affect their own reflections.
                if (dist < 90.0)
                {
                    InputData inputData = (InputData)0;
                    inputData.positionWS = i.ws;
                    inputData.normalizedScreenSpaceUV = screenUV;
                    uint count = GetAdditionalLightsCount();
                    LIGHT_LOOP_BEGIN(count)
                        Light l = GetAdditionalLight(lightIndex, i.ws);
                        float warmTrail = reflectionTrail(l.direction, v, g, 0.12, 0.5);
                        // Surface lighting uses inverse-square attenuation. A reflected visible
                        // light needs a softer falloff to remain legible, while still following
                        // the actual enabled light, spot direction and range (zero stays zero).
                        float reflectedAttenuation = sqrt(max(l.distanceAttenuation, 0.0)) * 0.55;
                        col += l.color * reflectedAttenuation * warmTrail * micro;
                    LIGHT_LOOP_END
                }

                // Broken contact foam where opaque shore/rocks meet the water, fading in the
                // distance. Requires the camera's opaque depth texture (enabled by NightSky).
                if (dist < 90.0 && verticalDepth < max(_FoamWidth, 0.06))
                {
                    float foamNoise = noise(i.ws.xz * 2.1 + float2(t * 0.06, -t * 0.09));
                    float foamBand = 1 - smoothstep(0.05, max(_FoamWidth, 0.06), verticalDepth);
                    float crest = 0.5 + 0.5 * sin(verticalDepth * 10 - t * 1.4 + foamNoise * 3);
                    float foam = foamBand * smoothstep(0.25, 0.7, foamNoise + crest * 0.3) * _Foam;
                    foam *= 1 - smoothstep(60, 90, dist);
                    col = lerp(col, _FoamColor.rgb, foam);
                }
                // Four-vertex ocean: evaluating fog per pixel avoids relying on corner depths.
                float fog = ComputeFogFactorZ0ToFar(max(surfaceDepth - _ProjectionParams.y, 0.0));
                col = MixFog(col, fog);
                float opacity = 1 - smoothstep(105.0, 145.0, length(i.localXZ));
                return half4(col, opacity);
            }
            ENDHLSL
        }
    }
}
