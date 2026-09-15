Shader "MarketDay/Painted Terrain Tiles"
{
    Properties
    {
        [PerRendererData] _MainTex ("Sprite", 2D) = "white" {}
        _GrassTex ("Painted grass", 2D) = "white" {}
        _RoadTex ("Painted asphalt", 2D) = "white" {}
        _WaterTex ("Painted water", 2D) = "white" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Off
        CGPROGRAM
        #pragma surface surf Lambert vertex:vert addshadow
        #pragma target 3.0
        sampler2D _GrassTex, _RoadTex, _WaterTex;
        struct Input { float2 tileUV; float4 tileData; float3 worldPos; };
        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            o.tileUV = v.texcoord.xy;
            // RGB metadata is linearized by TilemapRenderer; alpha is unchanged.
            #ifdef UNITY_COLORSPACE_GAMMA
                o.tileData.rgb = v.color.rgb;
            #else
                o.tileData.rgb = LinearToGammaSpace(v.color.rgb);
            #endif
            o.tileData.a = v.color.a;
        }
        float bit(float mask, float divisor) { return fmod(floor(mask / divisor), 2); }
        float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
        float noise(float2 p)
        {
            float2 i=floor(p), f=frac(p); f=f*f*(3-2*f);
            return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
        }
        float pathDistance(float2 p, float mask, out float along)
        {
            float n=bit(mask,1), e=bit(mask,2), s=bit(mask,4), w=bit(mask,8);
            along=p.y;
            if(mask==5) return abs(p.x);
            if(mask==10) { along=p.x; return abs(p.y); }
            if(mask==3 || mask==6 || mask==12 || mask==9)
            {
                float2 corner=float2(e>.5?.5:-.5,n>.5?.5:-.5);
                float2 q=p-corner;
                along=atan2(q.y,q.x)*.5;
                return abs(length(q)-.5);
            }
            float distance=length(p);
            if(n>.5 && p.y>=0) distance=min(distance,abs(p.x));
            if(s>.5 && p.y<=0) distance=min(distance,abs(p.x));
            if(e>.5 && p.x>=0) distance=min(distance,abs(p.y));
            if(w>.5 && p.x<=0) distance=min(distance,abs(p.y));
            return distance;
        }
        float areaDistance(float2 p,float mask,float diagonal,float inset)
        {
            float h=p.x>=0?bit(mask,2):bit(mask,8);
            float v=p.y>=0?bit(mask,1):bit(mask,4);
            float corner=p.y>=0?(p.x>=0?bit(diagonal,1):bit(diagonal,8)):
                (p.x>=0?bit(diagonal,2):bit(diagonal,4));
            float2 q=abs(p);
            if(h>.5 && v>.5) return corner>.5?-1:inset-length(q-.5);
            if(h>.5) return q.y-(.5-inset);
            if(v>.5) return q.x-(.5-inset);
            float radius=.23;
            float2 d=q-(.5-inset-radius);
            return length(max(d,0))+min(max(d.x,d.y),0)-radius;
        }
        fixed3 waterColor(float2 uv,float distance)
        {
            fixed3 waterTexture=tex2D(_WaterTex,uv*.65+float2(_Time.y*.003,-_Time.y*.004)).rgb;
            float depth=smoothstep(-.025,-.34,distance);
            fixed3 water=lerp(fixed3(.23,.57,.53),fixed3(.055,.32,.36),depth);
            water=lerp(water,waterTexture*.7,.20);
            float wave=sin(uv.x*15+uv.y*9+_Time.y*1.1+noise(uv*2)*6);
            water+=smoothstep(.93,1,wave)*.025;
            float foam=(1-smoothstep(.008,.027,abs(distance+.022)))*(.45+.25*sin(uv.x*4+uv.y*7+_Time.y));
            return lerp(water,fixed3(.73,.86,.69),foam);
        }
        void surf(Input IN, inout SurfaceOutput o)
        {
            float kind=floor(IN.tileData.x*8+.5)-1;
            float mask=floor(IN.tileData.y*15+.5), diagonal=floor(IN.tileData.z*15+.5);
            float apronMask=floor((1-IN.tileData.a)*32+.5);
            float2 uv=IN.worldPos.xz/4, p=IN.tileUV-.5;
            float variation=noise(IN.worldPos.xz*.10);
            fixed3 grass=tex2D(_GrassTex,uv*.68).rgb;
            grass=lerp(grass,fixed3(.31,.46,.15),.42)*lerp(.90,1.09,variation);
            grass=lerp(grass,fixed3(.48,.54,.24),smoothstep(.64,.86,noise(uv*.63+17))*.16);
            fixed3 color=grass;
            if(kind>.5)
            {
                float along, d=pathDistance(p,mask,along);
                if(kind>1.5 && kind<2.5)
                {
                    float edge=areaDistance(p,mask,diagonal,.085);
                    // World-space detail makes the bank uneven without tile seams.
                    edge+=(noise(IN.worldPos.xz*1.5)-.5)*.020;
                    color=lerp(grass,fixed3(.47,.42,.25),1-smoothstep(.045,.075,edge));
                    color=lerp(color,fixed3(.68,.63,.42),1-smoothstep(.005,.047,edge));
                    color=lerp(color,waterColor(uv,edge),1-smoothstep(-.004,.004,edge));
                }
                else if(kind>4.5)
                {
                    float edge=areaDistance(p,diagonal,15,.085);
                    color=lerp(grass,fixed3(.68,.63,.42),1-smoothstep(0,.055,edge));
                    color=lerp(color,waterColor(uv,edge),1-smoothstep(-.004,.004,edge));
                    float width=.43;
                    float across=mask==10?p.y:p.x;
                    float plank=frac(along*18);
                    fixed3 wood=lerp(fixed3(.37,.23,.12),fixed3(.64,.43,.24),smoothstep(.02,.12,plank));
                    wood*=.93+.07*noise(uv*16);
                    color=lerp(color,wood,1-smoothstep(width-.006,width+.006,d));
                    color=lerp(color,fixed3(.31,.25,.16),1-smoothstep(.006,.022,abs(abs(across)-.405)));
                    color=lerp(color,fixed3(.76,.59,.33),1-smoothstep(.006,.012,abs(abs(across)-.395)));
                }
                else if(kind>3.5)
                {
                    float edge=d-.255;
                    color=lerp(grass,fixed3(.38,.39,.24),1-smoothstep(.025,.055,edge));
                    float2 paver=uv*6;
                    paver.x+=fmod(floor(paver.y),2)*.5;
                    float2 joint=min(frac(paver),1-frac(paver));
                    float jointMask=1-smoothstep(.012,.04,min(joint.x,joint.y));
                    fixed3 stone=lerp(fixed3(.72,.66,.48),fixed3(.84,.78,.60),hash(floor(paver)));
                    stone=lerp(stone,fixed3(.47,.44,.32),jointMask*.65);
                    color=lerp(color,stone,1-smoothstep(-.006,.006,edge));
                    color=lerp(color,fixed3(.79,.75,.58),1-smoothstep(.008,.018,abs(edge-.012)));
                }
                else if(kind>2.5)
                {
                    float edge=areaDistance(p,mask,diagonal,.015);
                    fixed3 asphalt=tex2D(_RoadTex,uv).rgb*fixed3(.67,.73,.76);
                    color=lerp(grass,fixed3(.65,.65,.53),1-smoothstep(.005,.032,edge));
                    color=lerp(color,asphalt,1-smoothstep(-.005,.005,edge));
                }
                else
                {
                    float apron=max(bit(apronMask,1)*smoothstep(.16,.48,p.y),bit(apronMask,4)*smoothstep(.16,.48,-p.y));
                    apron=max(apron,max(bit(apronMask,2)*smoothstep(.16,.48,p.x),bit(apronMask,8)*smoothstep(.16,.48,-p.x)));
                    float width=.395+.11*apron;
                    float edge=d-width;
                    color=lerp(grass,fixed3(.42,.43,.30),1-smoothstep(.025,.055,edge));
                    color=lerp(color,fixed3(.73,.72,.58),1-smoothstep(.010,.029,edge));
                    fixed3 asphalt=tex2D(_RoadTex,uv*.85).rgb*fixed3(.60,.66,.70);
                    float marking=(1-smoothstep(.007,.012,d))*step(.42,frac(along*4+.15));
                    if(mask!=5 && mask!=10 && mask!=3 && mask!=6 && mask!=12 && mask!=9) marking=0;
                    asphalt=lerp(asphalt,fixed3(.91,.77,.38),marking*.85);
                    float shoulder=1-smoothstep(.005,.010,abs(d-(width-.048)));
                    asphalt=lerp(asphalt,fixed3(.83,.82,.69),shoulder*.65*(1-apron));
                    color=lerp(color,asphalt,1-smoothstep(-.004,.004,edge));
                }
            }
            o.Albedo=color;
            o.Alpha=1;
        }
        ENDCG
    }
    Fallback "Diffuse"
}
