// World-space triplanar surface for the procedurally built city scenery (park, roundabout, plaza,
// abandoned warehouse). Box primitives have no useful UVs once baked together, so the albedo and
// normal maps are projected from the three world axes at a fixed texel density (_Tiling metres per tile).
// Normal blending follows Ben Golus' "whiteout" triplanar method for surface shaders.
Shader "MarketDay/City Park Triplanar"
{
    Properties
    {
        _Color ("Tint", Color) = (1,1,1,1)
        _MainTex ("Albedo (A = smoothness)", 2D) = "white" {}
        [Normal] _BumpMap ("Normal map", 2D) = "bump" {}
        _BumpScale ("Normal strength", Float) = 1
        _Tiling ("Metres per texture tile", Float) = 1
        _Glossiness ("Smoothness", Range(0,1)) = .3
        _Metallic ("Metallic", Range(0,1)) = 0
        _Variation ("Large scale colour variation", Range(0,1)) = .12
        _Scroll ("Texture scroll per second (xy)", Vector) = (0,0,0,0)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        sampler2D _MainTex, _BumpMap;
        fixed4 _Color;
        half _BumpScale, _Tiling, _Glossiness, _Metallic, _Variation;
        float4 _Scroll;
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
            float2 scroll = _Scroll.xy * _Time.y;
            float2 uvX = p.zy + scroll, uvY = p.xz + scroll, uvZ = p.xy + scroll;
            fixed4 cx = tex2D(_MainTex, uvX), cy = tex2D(_MainTex, uvY), cz = tex2D(_MainTex, uvZ);
            fixed4 albedo = cx * blend.x + cy * blend.y + cz * blend.z;

            half3 nx = UnpackScaleNormal(tex2D(_BumpMap, uvX), _BumpScale);
            half3 ny = UnpackScaleNormal(tex2D(_BumpMap, uvY), _BumpScale);
            half3 nz = UnpackScaleNormal(tex2D(_BumpMap, uvZ), _BumpScale);
            float3 axisSign = sign(n);
            nx.x *= axisSign.x; ny.x *= axisSign.y; nz.x *= -axisSign.z;
            nx = half3(nx.xy + n.zy, abs(nx.z) * n.x);
            ny = half3(ny.xy + n.xz, abs(ny.z) * n.y);
            nz = half3(nz.xy + n.xy, abs(nz.z) * n.z);
            float3 worldNormal = normalize(nx.zyx * blend.x + ny.xzy * blend.y + nz.xyz * blend.z);

            // Broad, soft colour drift so repeated tiles never read as a flat pattern.
            float drift = noise(IN.worldPos * .35) * .65 + noise(IN.worldPos * 1.3) * .35;
            o.Albedo = albedo.rgb * _Color.rgb * lerp(1 - _Variation, 1 + _Variation * .5, drift);
            o.Normal = WorldToTangentNormalVector(IN, worldNormal);
            o.Smoothness = _Glossiness * albedo.a;
            o.Metallic = _Metallic;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
