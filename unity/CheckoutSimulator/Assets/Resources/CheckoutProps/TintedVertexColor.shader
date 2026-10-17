// Lit colour × vertex colour: props baked with shading in their vertex colours (seams, rims) and tinted per
// instance, like the rain umbrellas (RainUmbrellaV2's canopy is near-white, each person's umbrella gets a colour).
Shader "Checkout/TintedVertexColor"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _Glossiness ("Smoothness", Range(0,1)) = 0.35
        _Metallic ("Metallic", Range(0,1)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        fixed4 _Color; half _Glossiness; half _Metallic;
        struct Input { float4 color : COLOR; };
        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            o.Albedo = _Color.rgb * IN.color.rgb;
            o.Smoothness = _Glossiness;
            o.Metallic = _Metallic;
            o.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
