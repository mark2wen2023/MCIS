Shader "MCIS/ResearchSection" {
 Properties { _Color ("Color", Color) = (.45,.6,.7,1) }
 SubShader { Tags { "RenderType"="Opaque" } Cull Off
 Pass {
 CGPROGRAM
 #pragma vertex vert
 #pragma fragment frag
 #include "UnityCG.cginc"
 fixed4 _Color;
 float _SectionX, _SectionEnabled;
 struct app { float4 vertex:POSITION; float3 normal:NORMAL; };
 struct v2f { float4 pos:SV_POSITION; float3 world:TEXCOORD0; float3 norm:TEXCOORD1; };
 v2f vert(app v) { v2f o; o.pos=UnityObjectToClipPos(v.vertex); o.world=mul(unity_ObjectToWorld,v.vertex).xyz; o.norm=UnityObjectToWorldNormal(v.normal); return o; }
 fixed4 frag(v2f i):SV_Target { if(_SectionEnabled>.5) clip(i.world.x-_SectionX); float light=.46+.54*abs(dot(normalize(i.norm),normalize(float3(-.3,.78,.48))));return fixed4(_Color.rgb*light,1); }
 ENDCG
 }
 }
}
