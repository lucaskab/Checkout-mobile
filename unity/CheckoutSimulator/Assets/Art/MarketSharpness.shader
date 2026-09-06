Shader "Hidden/MarketDay/Native Clarity"
{
    Properties {_MainTex("Image",2D)="white"{} _Strength("Clarity",Range(0,1))=.38}
    SubShader
    {
        Cull Off ZWrite Off ZTest Always
        Pass
        {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #include "UnityCG.cginc"
            sampler2D _MainTex;float4 _MainTex_TexelSize;float _Strength;
            fixed4 frag(v2f_img i):SV_Target
            {
                float2 p=_MainTex_TexelSize.xy;
                float3 c=tex2D(_MainTex,i.uv).rgb;
                float3 n=tex2D(_MainTex,i.uv+float2(0,p.y)).rgb;
                float3 s=tex2D(_MainTex,i.uv-float2(0,p.y)).rgb;
                float3 e=tex2D(_MainTex,i.uv+float2(p.x,0)).rgb;
                float3 w=tex2D(_MainTex,i.uv-float2(p.x,0)).rgb;
                float3 low=min(c,min(min(n,s),min(e,w)));
                float3 high=max(c,max(max(n,s),max(e,w)));
                // Local bounds prevent bright halos along the ink contours.
                float3 crisp=clamp(c+(c-(n+s+e+w)*.25)*_Strength,low,high);
                return float4(crisp,1);
            }
            ENDCG
        }
    }
}
