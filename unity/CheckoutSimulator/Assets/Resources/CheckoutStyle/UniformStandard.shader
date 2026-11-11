// "Estilo do mercado": a Standard-lit copy for staff whose material uses Unity's "Standard" shader (the cashier,
// CheckoutWoman), with the uniform recolour of UniformPaint.cginc. CheckoutMarketStyle swaps it in only while a
// uniform other than the original is worn.
Shader "MarketDay/Uniform Standard"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
        _MainTex ("Albedo", 2D) = "white" {}
        _Glossiness ("Smoothness", Range(0,1)) = .3
        _Metallic ("Metallic", Range(0,1)) = 0
        _UniformMask ("Uniform mask (R main, G detail)", 2D) = "black" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #include "Assets/Resources/CheckoutStyle/UniformPaint.cginc"
        #include "Assets/Resources/CheckoutPaint/CheckoutSnow.cginc"
        sampler2D _MainTex;
        fixed4 _Color; half _Glossiness, _Metallic;
        struct Input { float2 uv_MainTex; float3 worldPos; float3 worldNormal; };
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            o.Albedo = UniformPaint(c.rgb, IN.uv_MainTex);
            o.Albedo = CheckoutSnow(o.Albedo, IN.worldPos, CheckoutSnowUp(IN.worldNormal), 1);
            o.Smoothness = _Glossiness; o.Metallic = _Metallic; o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
