#ifndef BORROWED_LIGHT_FOLIAGE_SURFACE_INCLUDED
#define BORROWED_LIGHT_FOLIAGE_SURFACE_INCLUDED

// Include after URP LitInput.hlsl. No material constants are added here:
// all passes retain URP 17.3's identical UnityPerMaterial / DOTS layout.
// Call UNITY_SETUP_INSTANCE_ID before this object/world-space conversion.
float3 FoliageWindPositionOS(float3 positionOS)
{
    float3 p = TransformObjectToWorld(positionOS);
    float rooted = smoothstep(0.08, 0.48, p.y);
    float gust = sin(p.x * 0.73 + p.z * 0.46 - _Time.y * 1.25);
    float flutter = sin(p.x * 3.1 + p.z * 1.8 + _Time.y * 2.5);
    p.xz += float2(1, 0.42) * (gust * 0.025 + flutter * 0.006) * rooted;
    return TransformWorldToObject(p);
}

half3 FoliageShadingNormalWS(half3 normalWS, half faceSign)
{
    half3 leafNormal = normalize(normalWS) * faceSign;
    // The legacy diagnostic always retains the original 40% forward normal.
    // The candidate is a local material keyword, not a new global uniform.
#if defined(_FOLIAGE_NORMAL_UP_20) && !defined(_FOLIAGE_LEGACY_AUX)
    const half upBlend = 0.20h;
#else
    const half upBlend = 0.40h;
#endif
    return normalize(lerp(leafNormal, half3(0,1,0), upBlend));
}

#endif
