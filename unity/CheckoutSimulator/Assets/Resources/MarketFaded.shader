// See-through copy of a facade material (CheckoutStageDressing.Fade): the entrance canopies of the bigger shops
// stay readable but let the player see the door and the people under them. A depth pre-pass keeps the piece
// from showing its own back faces through itself. _Tiling > 0 samples the texture in world space like
// MarketDay/City Park Triplanar (metres per repeat), otherwise the mesh UVs.
Shader "MarketDay/Faded"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
        _MainTex ("Albedo", 2D) = "white" {}
        _Tiling ("World tiling (0 = UV)", Float) = 0
        _EmissionColor ("Emission", Color) = (0,0,0,1)
        _Fade ("Opacity", Range(0,1)) = .5
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }
        LOD 200
        Pass { ZWrite On ColorMask 0 }

        CGPROGRAM
        #pragma surface surf Lambert alpha:fade
        #pragma target 3.0
        sampler2D _MainTex;
        fixed4 _Color, _EmissionColor;
        half _Fade;
        float _Tiling;
        struct Input { float2 uv_MainTex; float3 worldPos; float3 worldNormal; };
        void surf (Input IN, inout SurfaceOutput o)
        {
            fixed4 c;
            if (_Tiling > 0)
            {
                float3 n = abs(IN.worldNormal); n /= (n.x + n.y + n.z + 1e-4);
                float3 p = IN.worldPos / _Tiling;
                c = tex2D(_MainTex, p.zy) * n.x + tex2D(_MainTex, p.xz) * n.y + tex2D(_MainTex, p.xy) * n.z;
            }
            else c = tex2D(_MainTex, IN.uv_MainTex);
            c *= _Color;
            o.Albedo = c.rgb;
            o.Emission = _EmissionColor.rgb;
            o.Alpha = _Fade;
        }
        ENDCG
    }
    Fallback Off
}
