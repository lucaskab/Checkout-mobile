// Soft additive light used by the street lamps: the warm pool on the ground, the faint beam and the halo.
// Unlit and pipeline-free, so every lamp lights the same way on PC and phone (no per-object light limit).
Shader "Checkout/StreetLightAdditive" {
 Properties { _MainTex ("Falloff", 2D) = "white" {} _Color ("Tint", Color) = (1,0.75,0.45,1) }
 SubShader {
  Tags { "Queue"="Transparent+5" "RenderType"="Transparent" "IgnoreProjector"="True" "PreviewType"="Plane" }
  Blend One One ZWrite Off Cull Off Fog { Mode Off }
  Pass {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #include "UnityCG.cginc"
   sampler2D _MainTex; float4 _MainTex_ST; fixed4 _Color;
   struct appdata { float4 vertex:POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; };
   struct v2f { float4 pos:SV_POSITION; float2 uv:TEXCOORD0; fixed4 color:COLOR; };
   v2f vert (appdata v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = TRANSFORM_TEX(v.uv,_MainTex); o.color = v.color; return o; }
   fixed4 frag (v2f i) : SV_Target { fixed4 t = tex2D(_MainTex,i.uv); return fixed4(_Color.rgb * _Color.a * t.r * i.color.rgb * i.color.a, 0); }
   ENDCG
  }
 }
}
