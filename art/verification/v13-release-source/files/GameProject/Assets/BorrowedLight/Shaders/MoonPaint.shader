Shader "BorrowedLight/MoonPaint"
{
 SubShader {Tags {"RenderType"="Opaque" "RenderPipeline"="UniversalPipeline"} Pass {HLSLPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #pragma target 3.0
 #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
 struct A{float4 positionOS:POSITION;float3 normalOS:NORMAL;float2 uv:TEXCOORD0;};struct V{float4 positionCS:SV_POSITION;float3 normalWS:TEXCOORD0;float2 uv:TEXCOORD1;float3 positionWS:TEXCOORD2;};
 V vert(A i){V o;o.positionCS=TransformObjectToHClip(i.positionOS.xyz);o.normalWS=TransformObjectToWorldNormal(i.normalOS);o.uv=i.uv;o.positionWS=TransformObjectToWorld(i.positionOS.xyz);return o;}
 float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.54);}
 float noise(float2 p){float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(a),hash(a+float2(1,0)),f.x),lerp(hash(a+float2(0,1)),hash(a+1),f.x),f.y);}
 // Original, deterministic lunar relief. The smaller layer fades with screen
 // derivatives, retaining broad maria and crater rims at the overview distance.
 float craters(float2 uv,float scale,out float rim)
 {
  float2 p=uv*float2(scale*2,scale),cell=floor(p);float height=0;rim=0;
  float detail=saturate(1-max(fwidth(p.x),fwidth(p.y))*.7);
  for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++)
  {
   float2 c=cell+float2(x,y);float seed=hash(c+19.3);
   float2 center=c+.2+float2(hash(c+3.1),hash(c+8.7))*.6;
   float radius=lerp(.13,.35,seed);float d=length(p-center)/radius;
   float lip=exp(-pow((d-.9)*9,2));
   float bowl=1-smoothstep(.05,.86,d);float active=step(.32,seed)*detail;
   height+=(lip*.30-bowl*.40)*active;rim+=lip*active;
  }
  return height;
 }
 half4 frag(V i):SV_Target
 {
  float3 n=normalize(i.normalWS);float rimA,rimB;
  float broad=noise(i.uv*float2(15,8)+3.7);
  float maria=smoothstep(.44,.68,broad+.13*noise(i.uv*31));
  float relief=craters(i.uv,6,rimA)*.020+craters(i.uv,14,rimB)*.005;
  float3 dx=ddx(i.positionWS),dy=ddy(i.positionWS);
  float3 r1=cross(dy,n),r2=cross(n,dx);float determinant=dot(dx,r1);
  float3 gradient=(ddx(relief)*r1+ddy(relief)*r2)*sign(determinant)/max(abs(determinant),.00001);
  float3 reliefNormal=normalize(n-gradient*.85);
  float3 light=normalize(float3(-.4,.65,-.75));
  float illumination=smoothstep(-.13,.66,dot(reliefNormal,light));
  float grain=(noise(i.uv*97)-.5)*.045;
  float3 chalk=lerp(float3(.84,.80,.68),float3(.40,.45,.47),maria*.61);
  chalk*=1+rimA*.08+rimB*.035+grain;
  float3 color=lerp(float3(.014,.035,.058),chalk,illumination);
  return half4(color,1);
 }
 ENDHLSL}}
}
