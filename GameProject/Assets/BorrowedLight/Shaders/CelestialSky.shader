Shader "BorrowedLight/CelestialSky"
{
 Properties { _Night("Night", Range(0,1)) = 0.35 _Nebula("Painted Nebula",2D)="black"{} _PaintBlend("Paint blend",Range(0,1))=0 }
 SubShader {
  Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
  Cull Off ZWrite Off
  Pass {
   HLSLPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
   struct A { float4 positionOS : POSITION; };
   struct V { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };
   float _Night;
   TEXTURE2D(_Nebula);SAMPLER(sampler_Nebula);float _PaintBlend;
   V vert(A v) { V o; o.positionCS=TransformObjectToHClip(v.positionOS.xyz); o.dir=v.positionOS.xyz; return o; }
   float hash(float2 p) { p=frac(p*float2(123.34,456.21)); p+=dot(p,p+45.32); return frac(p.x*p.y); }
   float noise(float2 p) { float2 i=floor(p),f=frac(p); f=f*f*(3-2*f); return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y); }
   float fbm(float2 p) { float a=0.5,s=0; for(int i=0;i<4;i++){s+=a*noise(p);p=p*2.03+7.1;a*=0.5;}return s; }
   half4 frag(V i) : SV_Target {
    float3 d=normalize(i.dir);float2 uv=float2(atan2(d.z,d.x)*0.15915494+0.5,asin(d.y)*0.31830989+0.5);
    float neb=fbm(uv*float2(8,5));float mist=pow(saturate(1-abs(d.y-0.08)),5);
    float3 col=lerp(float3(0.008,0.020,0.055),float3(0.018,0.068,0.100),mist);
    col+=float3(0.012,0.030,0.045)*neb+float3(0.022,0.012,0.038)*pow(fbm(uv*13+14),3);
    float bandDistance=(d.y+d.x*.3-.12)*3.7;
    float band=exp(-bandDistance*bandDistance)*pow(max(0,fbm(uv*float2(16,9)+2.1)),1.5);
    col+=band*float3(.06,.075,.14)+pow(neb,4)*float3(.04,.025,.065);
    float2 paintUV=float2(frac(uv.x*3),saturate(uv.y*3-.45));
    float clarity=smoothstep(.48,.98,_Night);
    float3 painted=SAMPLE_TEXTURE2D(_Nebula,sampler_Nebula,paintUV).rgb;
    // The sky responds to the lamp puzzle: diffuse skyglow recedes before
    // the painted Milky Way and smaller stars become legible.
    col=lerp(col,painted,_PaintBlend*lerp(.22,1,clarity));
    col+=float3(.026,.031,.032)*mist*(1-clarity);
    for(int layer=0;layer<2;layer++) {
     float scale=layer==0?260.0:110.0;float2 p=uv*float2(scale*2,scale);float2 cell=floor(p);float2 f=frac(p)-0.5;
     float h=hash(cell+layer*37);float2 off=float2(hash(cell+6.3),hash(cell+23.7))*.65-.325;float r=length(f-off);
     float star=pow(saturate(1-r*float(layer==0?13:9)),3)*step(layer==0?.975:.98,h);
     float twinkle=.75+.25*sin(_Time.y*(.5+h)+h*73);col+=star*twinkle*lerp(float3(.35,.65,.85),float3(1.6,1.2,.65),h)*lerp(.12,2.4,clarity);
    }
    float glow=pow(saturate(dot(d,normalize(float3(-.4,.25,.7)))),32);col+=glow*float3(.065,.055,.025);
    return half4(col,1);
   }
   ENDHLSL
  }
 }
}
