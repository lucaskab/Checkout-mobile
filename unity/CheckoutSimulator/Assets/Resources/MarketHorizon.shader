// The city beyond the playable map (CheckoutCityHorizon): the same painted look as MarketDay/Soft Painted (toon ramp
// and warm ink contour), fading into the sky colour with the distance from the playable map, so the map stays
// crisp and the city around it melts into the haze instead of ending at a green void.
Shader "MarketDay/Horizon"
{
    Properties
    {
        _MainTex("Original material atlas",2D)="white"{}
        _Color("Tint",Color)=(1,1,1,1)
        _Outline("Illustrated contour width",Range(0,4))=0
        _OutlineColor("Warm ink",Color)=(0.19,0.10,0.045,1)
        _Flat("Ground (plain Lambert like the city tiles)",Float)=0
        _Tiled("Paving from the city tiles' atlas (4 m squares)",Float)=0
        _TileUV("Paving tile in the atlas (uv x, y, w, h)",Vector)=(0,0,1,1)
    }
    CGINCLUDE
    #include "UnityCG.cginc"
    float4 _HorizonPlayable;   // xmin, zmin, xmax, zmax of the playable map
    float4 _HorizonHaze;       // sky colour the city fades into
    float4 _HorizonFade;       // x: haze starts this far out, y: full haze this far out
    float HorizonHaze(float3 world)
    {
        float2 out1 = float2(_HorizonPlayable.x - world.x, _HorizonPlayable.y - world.z);
        float2 out2 = float2(world.x - _HorizonPlayable.z, world.z - _HorizonPlayable.w);
        float dist = length(max(max(out1, out2), 0));
        return smoothstep(_HorizonFade.x, _HorizonFade.y, dist);
    }
    ENDCG
    SubShader
    {
        Tags {"RenderType"="Opaque"}
        LOD 150
        Pass
        {
            Name "Illustrated contour"
            Cull Front
            ZWrite On
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            float _Outline; fixed4 _OutlineColor;
            struct appdata { float4 vertex:POSITION; float3 normal:NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 pos:SV_POSITION; float haze:TEXCOORD0; };
            v2f vert(appdata v)
            {
                UNITY_SETUP_INSTANCE_ID(v);
                v2f o; o.pos = UnityObjectToClipPos(v.vertex);
                float3 normal = mul((float3x3)UNITY_MATRIX_IT_MV, v.normal);
                float2 projected = TransformViewToProjection(normal.xy);
                o.pos.xy += normalize(projected + float2(.00001, .00001)) * _Outline * o.pos.w * 2 / _ScreenParams.xy;
                o.haze = HorizonHaze(mul(unity_ObjectToWorld, v.vertex).xyz);
                if (_Outline <= 0) o.pos = float4(0, 0, -2, 1);   // no contour: drop it
                return o;
            }
            fixed4 frag(v2f i):SV_Target { return fixed4(lerp(_OutlineColor.rgb, _HorizonHaze.rgb, i.haze), 1); }
            ENDCG
        }
        CGPROGRAM
        #pragma surface surf Market nofog noforwardadd finalcolor:haze
        #pragma multi_compile_instancing
        #pragma target 3.0
        sampler2D _MainTex; fixed4 _Color; float _Flat, _Tiled; float4 _TileUV;
        struct Input { float2 uv_MainTex; float3 worldPos; };
        void surf(Input IN, inout SurfaceOutput o)
        {
            float2 uv = _Tiled > .5 ? _TileUV.xy + frac(IN.worldPos.xz * .25) * _TileUV.zw : IN.uv_MainTex;
            fixed4 c = tex2D(_MainTex, uv) * _Color; o.Albedo = c.rgb; o.Alpha = 1;
        }
        half4 LightingMarket(SurfaceOutput s, half3 lightDir, half atten)
        {
            half n = dot(s.Normal, lightDir);
            half ramp = _Flat > .5 ? max(0, n) : lerp(.53, 1.0, smoothstep(-.16, .72, n));
            return half4(s.Albedo * _LightColor0.rgb * ramp * atten, 1);
        }
        void haze(Input IN, SurfaceOutput o, inout fixed4 color)
        {
            color.rgb = lerp(color.rgb, _HorizonHaze.rgb, HorizonHaze(IN.worldPos));
        }
        ENDCG
    }
    Fallback "Diffuse"
}
