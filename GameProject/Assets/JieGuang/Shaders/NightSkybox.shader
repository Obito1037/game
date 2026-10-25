// Night skybox for 借光岛: horizon-to-zenith gradient, a soft glow and halo around the Earth,
// a faint milky-way band, procedural twinkling stars and the Earth crescent itself (texture
// painted by NightSky.cs). Everything fades as light pollution washes the sky out.
Shader "JieGuang/NightSkybox"
{
    Properties
    {
        _Zenith ("Zenith", Color) = (0.010, 0.018, 0.055, 1)
        _Horizon ("Horizon", Color) = (0.05, 0.08, 0.15, 1)
        _Glow ("Earth glow", Color) = (0.25, 0.4, 0.75, 1)
        _EarthDir ("Earth direction", Vector) = (0.29, 0.77, -0.57, 0)
        _EarthTex ("Earth", 2D) = "black" {}
        _EarthSize ("Earth angular radius", Float) = 0.075
        _EarthBrightness ("Earth brightness", Float) = 1
        _Stars ("Stars", Range(0, 1)) = 1
        _MilkyWay ("Milky way", Range(0, 1)) = 0.35
        _PanoramaTex ("Optional S01 equirectangular sky", 2D) = "black" {}
        _PanoramaBlend ("Panorama blend", Range(0, 1)) = 0
        _PanoramaExposure ("Panorama exposure", Range(0, 2)) = 0.65
        _Clouds ("High thin cloud", Range(0, 1)) = 0.3
        _HorizonGlow ("Earth-lit horizon band", Color) = (0.20, 0.42, 0.52, 1)
        _CloudBank ("Low cloud bank over the sea", Range(0, 1)) = 0.6
        _CloudLit ("Cloud bank colour", Color) = (0.42, 0.52, 0.72, 1)
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
            float4 _Zenith, _Horizon, _Glow, _EarthDir;
            float _EarthSize, _EarthBrightness, _Stars, _MilkyWay;
            float _PanoramaBlend, _PanoramaExposure, _Clouds;
            float4 _HorizonGlow, _CloudLit;
            float _CloudBank;
            CBUFFER_END
            TEXTURE2D(_EarthTex); SAMPLER(sampler_EarthTex);
            TEXTURE2D(_PanoramaTex); SAMPLER(sampler_PanoramaTex);

            struct A { float4 pos : POSITION; };
            struct V { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };

            V vert(A i)
            {
                V o;
                o.pos = TransformObjectToHClip(i.pos.xyz);
                o.dir = i.pos.xyz;
                return o;
            }

            float hash31(float3 p)
            {
                p = frac(p * 0.1031);
                p += dot(p, p.yzx + 33.33);
                return frac((p.x + p.y) * p.z);
            }

            float vnoise(float3 p)
            {
                float3 i = floor(p), f = frac(p);
                f = f * f * (3 - 2 * f);
                float n000 = hash31(i), n100 = hash31(i + float3(1,0,0)), n010 = hash31(i + float3(0,1,0)), n110 = hash31(i + float3(1,1,0));
                float n001 = hash31(i + float3(0,0,1)), n101 = hash31(i + float3(1,0,1)), n011 = hash31(i + float3(0,1,1)), n111 = hash31(i + float3(1,1,1));
                return lerp(lerp(lerp(n000, n100, f.x), lerp(n010, n110, f.x), f.y), lerp(lerp(n001, n101, f.x), lerp(n011, n111, f.x), f.y), f.z);
            }

            float stars(float3 d, float scale, float threshold)
            {
                float3 p = d * scale;
                float3 cell = floor(p);
                float r = hash31(cell);
                if (r < threshold) return 0;
                float3 c = cell + 0.5 + (float3(hash31(cell + 7.1), hash31(cell + 3.7), hash31(cell + 1.3)) - 0.5) * 0.7;
                float dist = length(p - c);
                float mag = (r - threshold) / (1 - threshold);
                float tw = 0.9 + 0.1 * sin(_Time.y * (0.6 + r * 1.5) + r * 50);
                return (1 - smoothstep(0.04, 0.22 + mag * 0.13, dist)) * (0.12 + mag * 0.68) * tw;
            }

            half4 frag(V i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float3 e = normalize(_EarthDir.xyz);
                float h = d.y;
                float3 col = lerp(_Horizon.rgb, _Zenith.rgb, smoothstep(-0.02, 0.6, h));
                // A continuous horizon avoids the old hard horizontal band over the sea.
                col *= lerp(0.78, 1.0, smoothstep(-0.2, 0.06, h));
                if (_PanoramaBlend > 0.001)
                {
                    float2 panoUV = float2(atan2(d.z, d.x) / (2 * PI) + 0.5, asin(clamp(d.y, -1, 1)) / PI + 0.5);
                    float3 panorama = SAMPLE_TEXTURE2D(_PanoramaTex, sampler_PanoramaTex, panoUV).rgb;
                    col = lerp(col, panorama * _PanoramaExposure, _PanoramaBlend);
                }
                float3 e2 = normalize(float3(e.x, 0, e.z));
                float towardEarth = saturate(dot(normalize(float3(d.x, 0, d.z) + 1e-5), e2) * 0.5 + 0.5);
                // Earth-lit airglow: a luminous band hugging the horizon, strongest under the Earth.
                float band0 = exp(-abs(h - 0.02) * 9.0);
                col += _HorizonGlow.rgb * band0 * lerp(0.45, 1.25, towardEarth * towardEarth) * _EarthBrightness;
                // This lower hemisphere is the distant ocean/haze behind the finite sea mesh.
                if (h < -0.005) return half4(col, 1);
                float ce = saturate(dot(d, e));
                col += _Glow.rgb * (pow(ce, 60) * 0.6 + pow(ce, 7) * 0.16) * _EarthBrightness;

                // a soft bank of low clouds resting on the sea horizon, lit from the Earth's side
                float3 hd = normalize(float3(d.x, 0, d.z) + 1e-5);
                float bankN = vnoise(float3(hd.x * 4.0 + _Time.y * 0.004, h * 23.0, hd.z * 4.0)) * 0.6
                            + vnoise(float3(hd.x * 11.0, h * 55.0, hd.z * 11.0)) * 0.3
                            + vnoise(float3(hd.x * 27.0, h * 130.0, hd.z * 27.0)) * 0.1;
                float bankShape = smoothstep(0.42, 0.68, bankN - h * 3.2) * smoothstep(-0.005, 0.03, h) * (1 - smoothstep(0.05, 0.2, h));
                float3 bankCol = _CloudLit.rgb * lerp(0.55, 1.15, towardEarth) * (0.75 + 0.5 * smoothstep(0.3, 0.8, bankN));
                col = lerp(col, bankCol * _EarthBrightness, bankShape * _CloudBank);

                // milky way: a tilted soft band with clumpy noise
                float3 n = normalize(float3(0.55, 0.35, 0.76));
                float band = exp(-pow(dot(d, n), 2) * 22);
                float clump = vnoise(d * 9) * 0.6 + vnoise(d * 23) * 0.4;
                col += lerp(float3(0.45, 0.5, 0.85), float3(0.75, 0.55, 0.85), clump) * band * clump * 0.12 * _MilkyWay * _Stars;

                // A few broad translucent wisps provide atmospheric depth, without hiding the
                // stars in the story's clean night. There is no sun, daylight cloud bank or moon.
                float cloud = vnoise(d * float3(7, 18, 7) + float3(_Time.y * 0.003, 0, 0));
                cloud = smoothstep(0.54, 0.82, cloud) * smoothstep(-0.02, 0.25, h);
                col += float3(0.055, 0.075, 0.11) * cloud * _Clouds;

                float s = stars(d, 260, 0.982) + stars(d, 120, 0.994) * 1.1;
                s *= smoothstep(0.0, 0.18, h) * (0.6 + band * 0.8);
                col += float3(0.85, 0.91, 1.0) * s * _Stars * (1 - cloud * 0.5) * (1 - bankShape * _CloudBank);

                // the Earth: project onto a plane facing the viewer around the Earth direction
                float3 right = normalize(cross(float3(0, 1, 0), e));
                float3 up = cross(e, right);
                float2 uv = float2(dot(d, right), dot(d, up)) / _EarthSize;
                const float rot = -0.49; // tilt of the crescent
                uv = float2(uv.x * cos(rot) - uv.y * sin(rot), uv.x * sin(rot) + uv.y * cos(rot));
                if (dot(d, e) > 0.5 && abs(uv.x) < 1 && abs(uv.y) < 1)
                {
                    half3 earth = SAMPLE_TEXTURE2D(_EarthTex, sampler_EarthTex, uv * 0.5 + 0.5).rgb;
                    float discMask = saturate((0.86 - length(uv)) * 40);
                    // the dark side hides the stars but keeps a soft earthshine, never a black hole in the sky
                    col = lerp(col, col * 0.62 + float3(0.012, 0.022, 0.05) * _EarthBrightness, discMask);
                    col += earth * _EarthBrightness;
                    float rim = exp(-abs(length(uv) - 0.87) * 22.0) * (1 - discMask * 0.6);
                    col += _Glow.rgb * rim * 0.35 * _EarthBrightness;
                }
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
}
