// "Estilo do mercado" (CheckoutMarketStyle.cs): the floors and walls the player picks for the shop. Same world-space
// triplanar projection as "MarketDay/City Park Triplanar" (the market's own floor and plaster, so a new floor lines up
// with the build grid and needs no UVs), plus the player's colour: _TintMask (white = takes the colour) multiplies
// those texels by _TintColor, so a glazed tile changes colour and its grout stays grey.
Shader "MarketDay/Style Surface"
{
    Properties
    {
        _MainTex ("Albedo (A = smoothness)", 2D) = "white" {}
        [Normal] _BumpMap ("Normal map", 2D) = "bump" {}
        _BumpScale ("Normal strength", Float) = 1
        _Tiling ("Metres per texture tile", Float) = 1
        _Glossiness ("Smoothness", Range(0,1)) = .3
        _Variation ("Large scale colour variation", Range(0,1)) = .08
        _TintMask ("Tint mask (R)", 2D) = "black" {}
        _TintColor ("Player colour", Color) = (1,1,1,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        #include "Assets/Resources/CheckoutPaint/CheckoutSnow.cginc"
        sampler2D _MainTex, _BumpMap, _TintMask;
        fixed4 _TintColor;
        half _BumpScale, _Tiling, _Glossiness, _Variation;
        struct Input { float3 worldPos; float3 worldNormal; INTERNAL_DATA };

        float3 WorldToTangentNormalVector(Input IN, float3 normal)
        {
            float3 t2w0 = WorldNormalVector(IN, float3(1,0,0));
            float3 t2w1 = WorldNormalVector(IN, float3(0,1,0));
            float3 t2w2 = WorldNormalVector(IN, float3(0,0,1));
            float3x3 t2w = float3x3(t2w0, t2w1, t2w2);
            return normalize(mul(t2w, normal));
        }
        float hash(float3 p) { return frac(sin(dot(p, float3(127.1, 311.7, 74.7))) * 43758.5453); }
        float noise(float3 p)
        {
            float3 i = floor(p), f = frac(p); f = f * f * (3 - 2 * f);
            return lerp(lerp(lerp(hash(i), hash(i + float3(1,0,0)), f.x), lerp(hash(i + float3(0,1,0)), hash(i + float3(1,1,0)), f.x), f.y),
                        lerp(lerp(hash(i + float3(0,0,1)), hash(i + float3(1,0,1)), f.x), lerp(hash(i + float3(0,1,1)), hash(i + float3(1,1,1)), f.x), f.y), f.z);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            IN.worldNormal = WorldNormalVector(IN, float3(0,0,1));
            float3 n = IN.worldNormal;
            float3 blend = pow(abs(n), 4); blend /= max(dot(blend, 1), 1e-4);
            float3 p = IN.worldPos / max(_Tiling, .01);
            float2 uvX = p.zy, uvY = p.xz, uvZ = p.xy;
            fixed4 albedo = tex2D(_MainTex, uvX) * blend.x + tex2D(_MainTex, uvY) * blend.y + tex2D(_MainTex, uvZ) * blend.z;
            half tint = tex2D(_TintMask, uvX).r * blend.x + tex2D(_TintMask, uvY).r * blend.y + tex2D(_TintMask, uvZ).r * blend.z;

            half3 nx = UnpackScaleNormal(tex2D(_BumpMap, uvX), _BumpScale);
            half3 ny = UnpackScaleNormal(tex2D(_BumpMap, uvY), _BumpScale);
            half3 nz = UnpackScaleNormal(tex2D(_BumpMap, uvZ), _BumpScale);
            float3 axisSign = sign(n);
            nx.x *= axisSign.x; ny.x *= axisSign.y; nz.x *= -axisSign.z;
            nx = half3(nx.xy + n.zy, abs(nx.z) * n.x);
            ny = half3(ny.xy + n.xz, abs(ny.z) * n.y);
            nz = half3(nz.xy + n.xy, abs(nz.z) * n.z);
            float3 worldNormal = normalize(nx.zyx * blend.x + ny.xzy * blend.y + nz.xyz * blend.z);

            float drift = noise(IN.worldPos * .35) * .65 + noise(IN.worldPos * 1.3) * .35;
            // the masked texels are a neutral grey (≈ 0.8): ×1.25 brings them to the player's colour with the texture's shading
            float3 colour = lerp(albedo.rgb, albedo.rgb * _TintColor.rgb * 1.25, tint);
            o.Albedo = colour * lerp(1 - _Variation, 1 + _Variation * .5, drift);
            o.Albedo = CheckoutSnow(o.Albedo, IN.worldPos, CheckoutSnowUp(worldNormal), 1);
            o.Normal = WorldToTangentNormalVector(IN, worldNormal);
            o.Smoothness = _Glossiness * albedo.a;
            o.Metallic = 0;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
