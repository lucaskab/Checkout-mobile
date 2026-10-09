// CheckoutEdgeFog: blends whatever lies outside the playable map into the fog colour by its distance from the map.
Shader "Hidden/MarketDay/EdgeFog"
{
    Properties { _MainTex("", 2D) = "white" {} }
    SubShader
    {
        Cull Off ZWrite Off ZTest Always
        Pass
        {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #include "UnityCG.cginc"
            sampler2D _MainTex;
            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);
            float4x4 _ClipToWorld;
            float4 _Playable;   // xmin, zmin, xmax, zmax
            float4 _FogColor;
            float4 _FogRange;   // x: fog starts this far out, y: solid this far out
            fixed4 frag(v2f_img i) : SV_Target
            {
                fixed4 c = tex2D(_MainTex, i.uv);
                float raw = SAMPLE_DEPTH_TEXTURE(_CameraDepthTexture, i.uv);
                #if defined(UNITY_REVERSED_Z)
                    float z = raw; bool sky = raw <= 1e-6;
                #else
                    float z = raw * 2 - 1; bool sky = raw >= .999999;
                #endif
                float4 world = mul(_ClipToWorld, float4(i.uv * 2 - 1, z, 1));
                world.xyz /= world.w;
                float2 outside = max(float2(_Playable.x - world.x, _Playable.y - world.z), float2(world.x - _Playable.z, world.z - _Playable.w));
                float fog = smoothstep(_FogRange.x, _FogRange.y, length(max(outside, 0)));
                if (sky) fog = 1;
                return fixed4(lerp(c.rgb, _FogColor.rgb, fog), c.a);
            }
            ENDCG
        }
    }
}
