// Rain puddle on the pavement: a thin, glossy film of water that darkens the ground, mirrors the sky
// and is dotted with raindrop ripples. Drops are procedural: the ground is split into small cells and
// each cell (plus its neighbours, so rings cross cell borders) hosts one drop at a random spot and time.
// Mesh: an irregular blob; vertex colour alpha fades from 1 in the middle to 0 at the rim (soft wet edge),
// uv is the local position in puddle radii. _Rain (0..1) scales the ripples, _Fade the whole puddle.
Shader "MarketDay/Rain Puddle"
{
    Properties
    {
        _WaterColor ("Water colour", Color) = (.30,.40,.50,1)
        _WetColor ("Wet rim colour", Color) = (.10,.11,.13,1)
        _SkyColor ("Reflected sky", Color) = (.62,.72,.82,1)
        _Rain ("Rain amount", Range(0,1)) = 1
        _Fade ("Fade", Range(0,1)) = 1
        _DropCell ("Metres per drop cell", Float) = .38
        _DropRate ("Drops per cell per second", Float) = .9
        _RingSpeed ("Ring speed", Float) = .55
        _Glossiness ("Smoothness", Range(0,1)) = .96
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="AlphaTest+20" "IgnoreProjector"="True" }
        LOD 300
        ZWrite Off
        Cull Off
        Offset -1, -1
        CGPROGRAM
        #pragma surface surf Standard alpha:fade nolightmap
        #pragma target 3.0
        fixed4 _WaterColor, _WetColor, _SkyColor;
        half _Rain, _Fade, _DropCell, _DropRate, _RingSpeed, _Glossiness;
        struct Input { float3 worldPos; float4 color : COLOR; };

        float2 hash2(float2 p)
        {
            p = float2(dot(p, float2(127.1, 311.7)), dot(p, float2(269.5, 183.3)));
            return frac(sin(p) * 43758.5453);
        }

        // Ripple rings of the drops around p: returns the slope (xy) and the crest brightness (z).
        float3 Drops(float2 p)
        {
            float2 cell = floor(p / _DropCell);
            float2 slope = 0; float crest = 0;
            [unroll] for (int j = -1; j <= 1; j++)
            [unroll] for (int i = -1; i <= 1; i++)
            {
                float2 c = cell + float2(i, j);
                float2 h = hash2(c);
                float2 h2 = hash2(c + 17.3);
                float t = frac(_Time.y * _DropRate * (.7 + .6 * h2.x) + h2.y);
                float2 centre = (c + .15 + .7 * h) * _DropCell;
                float2 d = p - centre; float dist = length(d) + 1e-4;
                float radius = t * _RingSpeed * .55;
                float x = dist - radius;
                float life = (1 - t) * (1 - t);
                // A short wave train: two crests trailing the front.
                float envelope = exp(-x * x * 900) * life;
                slope += (d / dist) * cos(x * 110) * envelope;
                crest += saturate(sin(x * 110)) * envelope;
                // The splash itself: a bright dot right when the drop lands.
                crest += exp(-dist * dist * 4000) * saturate(1 - t * 8) * 1.5;
            }
            return float3(slope, crest);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float edge = saturate(IN.color.a);
            // Deep water only in the middle; a darker wet band towards the rim.
            float water = smoothstep(.15, .55, edge);
            float3 drops = Drops(IN.worldPos.xz) * _Rain * water;
            o.Normal = normalize(float3(drops.xy * .8, 1));
            float3 albedo = lerp(_WetColor.rgb, _WaterColor.rgb, water);
            albedo += drops.z * .3;
            o.Albedo = albedo;
            o.Smoothness = lerp(.08, _Glossiness, smoothstep(.5, 1, water));
            o.Metallic = 0;
            // Water is see-through at a steep angle and mirrors the sky at a grazing one.
            float fresnel = pow(1 - saturate(normalize(_WorldSpaceCameraPos - IN.worldPos).y), 3);
            // The overcast sky mirrored in the water (the scene has no reflection probe out here),
            // broken up by the ripples.
            float mirror = water * (.28 + fresnel * .45) * (1 - saturate(length(drops.xy)) * .6);
            o.Emission = _SkyColor.rgb * mirror + drops.z * .08;
            o.Alpha = saturate((lerp(.3, .72, water) + fresnel * .2) * smoothstep(0, .3, edge) + drops.z * .25 * water) * _Fade;
        }
        ENDCG
    }
    Fallback Off
}
