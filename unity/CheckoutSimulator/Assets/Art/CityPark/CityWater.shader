// Moving water for the pond, the Columbus Circle fountain basin and the dancing fountain on the square.
// Two normal maps scroll against each other, the colour runs from shallow at the shore to deep in the
// middle (vertex colour alpha = normalised depth) and a band of broken foam laps at the edge.
// Ripple rings (ducks paddling, jets landing) come from a global array filled by CheckoutWaterRipples.
Shader "MarketDay/City Water"
{
    Properties
    {
        _ShallowColor ("Shallow colour", Color) = (.36,.58,.58,1)
        _DeepColor ("Deep colour", Color) = (.10,.28,.36,1)
        _FoamColor ("Foam colour", Color) = (.92,.95,.93,1)
        [Normal] _BumpMap ("Wave normals", 2D) = "bump" {}
        _Tiling ("Metres per wave tile", Float) = 2.6
        _BumpScale ("Wave strength", Float) = .55
        _Speed ("Wave speed", Float) = .06
        _FoamWidth ("Shore foam width (depth units)", Range(0,1)) = .16
        _Glossiness ("Smoothness", Range(0,1)) = .93
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry+1" }
        LOD 300
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0
        sampler2D _BumpMap;
        fixed4 _ShallowColor, _DeepColor, _FoamColor;
        half _Tiling, _BumpScale, _Speed, _FoamWidth, _Glossiness;
        // xy = world xz centre, z = current radius, w = strength (0 = unused).
        float4 _CheckoutRipples[12];
        struct Input { float3 worldPos; float4 color : COLOR; };

        float hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
        float noise(float2 p)
        {
            float2 i = floor(p), f = frac(p); f = f * f * (3 - 2 * f);
            return lerp(lerp(hash(i), hash(i + float2(1,0)), f.x), lerp(hash(i + float2(0,1)), hash(i + float2(1,1)), f.x), f.y);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float2 p = IN.worldPos.xz;
            float2 uv = p / max(_Tiling, .01);
            float t = _Time.y * _Speed;
            half3 n1 = UnpackScaleNormal(tex2D(_BumpMap, uv + float2(t, t * .63)), _BumpScale);
            half3 n2 = UnpackScaleNormal(tex2D(_BumpMap, uv * 1.73 + float2(-t * .77, t * 1.1) + .37), _BumpScale * .8);
            half3 n3 = UnpackScaleNormal(tex2D(_BumpMap, uv * .41 + float2(t * .3, -t * .45) + .71), _BumpScale * .6);
            float2 slope = n1.xy + n2.xy + n3.xy;

            // Ripple rings: a short wave train around each expanding radius.
            float crest = 0;
            [unroll] for (int i = 0; i < 12; i++)
            {
                float4 r = _CheckoutRipples[i];
                if (r.w <= 0) continue;
                float2 d = p - r.xy; float dist = length(d) + 1e-4;
                float x = dist - r.z;
                float envelope = exp(-x * x * 60) * r.w;
                slope += (d / dist) * cos(x * 38) * envelope * .9;
                crest += saturate(sin(x * 38)) * envelope;
            }
            o.Normal = normalize(half3(slope, 1));

            float depth = saturate(IN.color.a);
            float3 water = lerp(_ShallowColor.rgb, _DeepColor.rgb, pow(depth, .7));
            // Light catching the wave faces.
            water *= .92 + .16 * saturate(slope.x * .6 + slope.y * .4 + .5);
            // Foam: broken, slowly shifting lace at the shore, plus the crests of fresh ripples.
            float lace = noise(p * 5.5 + _Time.y * float2(.3, -.2)) * .6 + noise(p * 13 - _Time.y * .5) * .4;
            float shore = 1 - smoothstep(0, _FoamWidth, depth);
            float foam = saturate(shore * smoothstep(.35, .6, lace + shore * .5) + crest * .35);
            o.Albedo = lerp(water, _FoamColor.rgb, foam);
            o.Smoothness = lerp(_Glossiness, .35, foam);
            o.Metallic = 0;
            o.Alpha = 1;
        }
        ENDCG
    }
    Fallback "Standard"
}
