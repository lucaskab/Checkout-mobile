// A Standard (metallic) material of the market with the player's colours (MarketPaint.cginc). CheckoutMarketPaint
// swaps the market's opaque Standard materials for a copy with this shader only while a palette other than Clássico
// is on, copying colour, albedo, smoothness, metallic, normal map and emission; the look is the Standard one.
Shader "MarketDay/Painted Standard"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
        _MainTex ("Albedo", 2D) = "white" {}
        _Glossiness ("Smoothness", Range(0,1)) = 0.5
        _Metallic ("Metallic", Range(0,1)) = 0
        [Normal] _BumpMap ("Normal map", 2D) = "bump" {}
        _BumpScale ("Normal strength", Float) = 1
        _EmissionColor ("Emission", Color) = (0,0,0,1)
        _EmissionMap ("Emission map", 2D) = "white" {}
        _PaintWhole ("Paint: whole material (1 navy, 2 gold)", Float) = 0
        _PaintUseMask ("Paint: use mask", Float) = 0
        _PaintMask ("Paint mask (R navy, G gold)", 2D) = "black" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        #pragma multi_compile_local __ _NORMALMAP
        #include "Assets/Resources/CheckoutPaint/MarketPaint.cginc"
        sampler2D _MainTex, _BumpMap, _EmissionMap;
        fixed4 _Color, _EmissionColor;
        half _Glossiness, _Metallic, _BumpScale;
        struct Input { float2 uv_MainTex; };
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            o.Albedo = MarketPaint(c.rgb, IN.uv_MainTex);
            #ifdef _NORMALMAP
            o.Normal = UnpackScaleNormal(tex2D(_BumpMap, IN.uv_MainTex), _BumpScale);
            #endif
            o.Emission = tex2D(_EmissionMap, IN.uv_MainTex).rgb * _EmissionColor.rgb;
            o.Smoothness = _Glossiness;
            o.Metallic = _Metallic;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
