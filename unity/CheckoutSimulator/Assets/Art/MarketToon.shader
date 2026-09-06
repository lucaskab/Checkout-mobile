Shader "MarketDay/Soft Painted"
{
    Properties { _MainTex("Original material atlas",2D)="white"{} _Color("Tint",Color)=(1,1,1,1) _Outline("Illustrated contour width",Range(0,4))=1.25 _OutlineColor("Warm ink",Color)=(0.19,0.10,0.045,1) }
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
            #include "UnityCG.cginc"
            float _Outline;fixed4 _OutlineColor;
            struct appdata {float4 vertex:POSITION;float3 normal:NORMAL;};
            struct v2f {float4 pos:SV_POSITION;};
            v2f vert(appdata v)
            {
                v2f o;o.pos=UnityObjectToClipPos(v.vertex);
                float3 normal=mul((float3x3)UNITY_MATRIX_IT_MV,v.normal);
                float2 projected=TransformViewToProjection(normal.xy);
                o.pos.xy+=normalize(projected+float2(.00001,.00001))*_Outline*o.pos.w*2/_ScreenParams.xy;
                return o;
            }
            fixed4 frag(v2f i):SV_Target{return _OutlineColor;}
            ENDCG
        }
        CGPROGRAM
        #pragma surface surf Market fullforwardshadows addshadow
        #pragma target 3.0
        sampler2D _MainTex;fixed4 _Color;
        struct Input {float2 uv_MainTex;};
        void surf(Input IN,inout SurfaceOutput o)
        {
            fixed4 c=tex2D(_MainTex,IN.uv_MainTex)*_Color;o.Albedo=c.rgb;o.Alpha=1;
        }
        half4 LightingMarket(SurfaceOutput s,half3 lightDir,half atten)
        {
            half n=dot(s.Normal,lightDir);
            half ramp=lerp(.53,1.0,smoothstep(-.16,.72,n));
            return half4(s.Albedo*_LightColor0.rgb*ramp*atten,1);
        }
        ENDCG
    }
    Fallback "Diffuse"
}
