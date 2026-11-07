// The city's Standard (metallic) materials while it snows (CheckoutSnowCover swaps them for a copy with this shader
// during the "nevasca" event and back when the snow has melted): the Standard look with the snow cover of
// CheckoutSnow.cginc on the faces that look up (roofs, tree tops, car roofs, benches...).
Shader "MarketDay/Snowy Standard"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
        _MainTex ("Albedo", 2D) = "white" {}
        _Cutoff ("Alpha cutoff", Range(0,1)) = 0.5
        _Glossiness ("Smoothness", Range(0,1)) = 0.5
        _Metallic ("Metallic", Range(0,1)) = 0
        [Normal] _BumpMap ("Normal map", 2D) = "bump" {}
        _BumpScale ("Normal strength", Float) = 1
        _EmissionColor ("Emission", Color) = (0,0,0,1)
        _EmissionMap ("Emission map", 2D) = "white" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_local __ _NORMALMAP
        #pragma multi_compile_local __ _ALPHATEST_ON
        #include "Assets/Resources/CheckoutPaint/CheckoutSnow.cginc"
        sampler2D _MainTex, _BumpMap, _EmissionMap;
        fixed4 _Color, _EmissionColor;
        half _Glossiness, _Metallic, _BumpScale, _Cutoff;
        struct Input { float2 uv_MainTex; float3 worldPos; float3 worldNormal; INTERNAL_DATA };
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            fixed4 c = tex2D(_MainTex, IN.uv_MainTex) * _Color;
            #ifdef _ALPHATEST_ON
            clip(c.a - _Cutoff);
            #endif
            #ifdef _NORMALMAP
            o.Normal = UnpackScaleNormal(tex2D(_BumpMap, IN.uv_MainTex), _BumpScale);
            #else
            o.Normal = float3(0, 0, 1);
            #endif
            o.Albedo = CheckoutSnow(c.rgb, IN.worldPos, CheckoutSnowUp(WorldNormalVector(IN, o.Normal)), 1);
            o.Emission = tex2D(_EmissionMap, IN.uv_MainTex).rgb * _EmissionColor.rgb;
            o.Smoothness = _Glossiness;
            o.Metallic = _Metallic;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
