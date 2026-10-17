// 3D text on signs (TextMesh): the font atlas alpha times the text colour, hidden behind what stands in front of it.
// The built-in font material ignores depth, so a sign's name showed through the other blade and through people.
Shader "Checkout/Text3D" {
 Properties { _MainTex ("Font Texture", 2D) = "white" {} _Color ("Text Color", Color) = (1,1,1,1) }
 SubShader {
  Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" }
  Lighting Off Cull Off ZWrite Off ZTest LEqual
  Blend SrcAlpha OneMinusSrcAlpha
  Offset -1, -1
  Pass {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #include "UnityCG.cginc"
   sampler2D _MainTex; float4 _MainTex_ST; fixed4 _Color;
   struct appdata { float4 vertex : POSITION; fixed4 color : COLOR; float2 uv : TEXCOORD0; };
   struct v2f { float4 pos : SV_POSITION; fixed4 color : COLOR; float2 uv : TEXCOORD0; };
   v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.color = v.color * _Color; o.uv = TRANSFORM_TEX(v.uv, _MainTex); return o; }
   fixed4 frag (v2f i) : SV_Target { fixed4 c = i.color; c.a *= tex2D(_MainTex, i.uv).a; return c; }
   ENDCG
  }
 }
}
