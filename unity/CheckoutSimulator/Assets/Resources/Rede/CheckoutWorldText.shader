// The world's TextMesh letters (facade names, signs, mats): like the built-in "GUI/Text Shader" but depth-tested, so a
// sign stays behind whatever stands in front of it (Lucas 06/11: the facade's big letters showed over the totem).
// Lives in Resources so builds keep it (CheckoutWorldText finds it by name).
Shader "Checkout/World Text" {
 Properties {
  _MainTex ("Font Texture", 2D) = "white" {}
  _Color ("Text Color", Color) = (1,1,1,1)
 }
 SubShader {
  Tags { "Queue"="Transparent" "IgnoreProjector"="True" "RenderType"="Transparent" "PreviewType"="Plane" }
  Lighting Off Cull Back ZWrite Off ZTest LEqual
  Blend SrcAlpha OneMinusSrcAlpha
  Pass {
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_fog
   #include "UnityCG.cginc"
   struct appdata_t { float4 vertex : POSITION; fixed4 color : COLOR; float2 texcoord : TEXCOORD0; };
   struct v2f { float4 vertex : SV_POSITION; fixed4 color : COLOR; float2 texcoord : TEXCOORD0; UNITY_FOG_COORDS(1) };
   sampler2D _MainTex; uniform float4 _MainTex_ST; uniform fixed4 _Color;
   v2f vert (appdata_t v) {
    v2f o; o.vertex = UnityObjectToClipPos(v.vertex); o.color = v.color * _Color;
    o.texcoord = TRANSFORM_TEX(v.texcoord, _MainTex); UNITY_TRANSFER_FOG(o, o.vertex); return o;
   }
   fixed4 frag (v2f i) : SV_Target {
    fixed4 col = i.color; col.a *= tex2D(_MainTex, i.texcoord).a;
    UNITY_APPLY_FOG(unity_FogColor, col); return col;
   }
   ENDCG
  }
 }
}
