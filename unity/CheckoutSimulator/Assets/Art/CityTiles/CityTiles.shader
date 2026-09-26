Shader "MarketDay/City Tiles"
{
    Properties
    {
        [PerRendererData] _MainTex ("Tileset", 2D) = "white" {}
        _LoadingAccessEnabled ("Loading yard entrance", Float) = 0
        _LoadingAccess ("Loading entrance center and half size", Vector) = (9.5,26,5,1.5)
        _WideStreets ("Wide city streets", Float) = 0
        _ExpansionProjection ("Project purchased market areas", Float) = 0
        _ExpansionFeatures ("Storage parking loading premium", Vector) = (1,1,1,1)
        _ParkingSpaces ("Purchased parking spaces", Float) = 5
        _MarketFootprint ("Market center and half size", Vector) = (0,0,9.4,7.4)
        _Color ("Pavement tint", Color) = (0.72,0.75,0.78,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Off
        CGPROGRAM
        #pragma surface surf Lambert vertex:vert
        #pragma target 3.0
        sampler2D _MainTex;
        fixed4 _Color;
        float _WideStreets;
        float _ParkingSpaces;
        float _ExpansionProjection;
        float4 _ExpansionFeatures, _MarketFootprint;
        float _LoadingAccessEnabled;
        float4 _LoadingAccess;
        struct Input { float2 uv_MainTex; float3 worldPos; float4 tileData; };
        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input,o);
            v.normal=float3(0,0,-1);
            v.tangent=float4(1,0,0,-1);
            #ifdef UNITY_COLORSPACE_GAMMA
                o.tileData=v.color;
            #else
                o.tileData=float4(LinearToGammaSpace(v.color.rgb),v.color.a);
            #endif
        }
        float bit(float m,float d) { return fmod(floor(m/d),2); }
        float hash(float2 p) { return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
        float noise(float2 p)
        {
            float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
            return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
        }
        void surf(Input IN,inout SurfaceOutput o)
        {
            float kind=round(IN.tileData.r*7), mask=round(IN.tileData.g*15);
            float2 world=IN.worldPos.xz;
            float2 p=frac(world/4)-.5;
            float3 color=tex2D(_MainTex,IN.uv_MainTex).rgb*_Color.rgb;
            float3 asphalt=float3(.075,.095,.125)+(noise(world*28)-.5)*.007;
            if(kind<1.5)
            {
                // Same curb width and corner radius for every connection. No painted tile borders.
                float h=p.x>=0?bit(mask,2):bit(mask,8);
                float v=p.y>=0?bit(mask,1):bit(mask,4);
                float2 q=abs(p);
                float d;
                if(h>.5 && v>.5) d=length(max(.40-q,0))-.08;
                else if(v>.5) d=.32-q.x;
                else if(h>.5) d=.32-q.y;
                else d=.32-length(q);
                float aa=max(fwidth(d),.001);
                float road=smoothstep(-aa,aa,d);
                // All street shoulders sample the same pavement, without source-road shadows or stretching.
                float2 pavementUV=(float2(854,482)+frac(world/4)*float2(344,332))/1254;
                color=tex2D(_MainTex,pavementUV).rgb*_Color.rgb;
                float curb=smoothstep(-.028-aa,-.028+aa,d)*(1-road);
                color=lerp(color,float3(.53,.53,.50),curb);
                color=lerp(color,asphalt,road);
                float vertical=(mask==5 || mask==1 || mask==4 || (mask==0));
                float horizontal=(mask==10 || mask==2 || mask==8);
                float axis=vertical>.5?p.x:p.y;
                float along=vertical>.5?world.y:world.x;
                float dashed=1-smoothstep(.045,.07,abs(frac(along/2)-.5)-.25);
                float marking=1-smoothstep(.010,.018,abs(axis));
                float straight=saturate(vertical+horizontal);
                // Terminate junction markings inside the approaches, keeping the crossing center clear.
                if(straight<.5)
                {
                    float northSouth=(p.y>=0?bit(mask,1):bit(mask,4))*(1-smoothstep(.010,.018,abs(p.x)))*smoothstep(.27,.30,abs(p.y));
                    float eastWest=(p.x>=0?bit(mask,2):bit(mask,8))*(1-smoothstep(.010,.018,abs(p.y)))*smoothstep(.27,.30,abs(p.x));
                    marking=max(northSouth,eastWest);dashed=1;
                }
                if(kind>.5 && straight>.5)
                {
                    float crossing=(1-smoothstep(.19,.20,abs(vertical>.5?p.y:p.x)))*(1-smoothstep(.26,.27,abs(axis)));
                    float stripes=1-smoothstep(.56,.64,frac((axis+.5)*10));
                    marking=lerp(marking*dashed,stripes,crossing);marking*=road;
                }
                else marking*=dashed*road;
                color=lerp(color,float3(.79,.78,.70),marking);
            }
            else if(kind>3.5 && kind<4.5) color=asphalt;
            if(_WideStreets>.5)
            {
                float dx=abs(abs(world.x)-23.5)-3;
                float dz=min(abs(world.y+15.5),abs(world.y-30))-3;
                float blend=saturate(.5+.5*(dz-dx)/.8);
                float street=lerp(dz,dx,blend)-.8*blend*(1-blend);
                float2 drive=abs(world-float2(-11.2,-10))-float2(2.2,5.5);
                float driveway=max(drive.x,drive.y);
                float distance=min(street,driveway);
                float aa=max(fwidth(distance),.015);
                float2 uv=(float2(854,482)+frac(world/4)*float2(344,332))/1254;
                if(kind<1.5)color=tex2D(_MainTex,uv).rgb*_Color.rgb;
                float pavement=step(.03,street)*(1-smoothstep(1.95,2.05,street));
                float2 slab=abs(frac(world)-.5);
                float joint=smoothstep(.475,.495,max(slab.x,slab.y));
                float3 sidewalk=lerp(float3(.43,.45,.44),float3(.30,.32,.31),joint*.35);
                color=lerp(color,sidewalk,pavement);
                float curb=(1-smoothstep(.04,.12,abs(distance)));
                color=lerp(color,float3(.65,.65,.60),curb);
                float road=1-smoothstep(-aa,aa,distance);
                color=lerp(color,asphalt,road);
                float vaxis=abs(abs(world.x)-23.5), haxis=min(abs(world.y+15.5),abs(world.y-30));
                // Centre-line dashes are whole 1.6 m segments. Each segment is kept or dropped as a unit,
                // judged at its own centre, so no stub is ever cut by a junction, crosswalk or driveway.
                float zc=floor(world.y/3)*3+1.5, xc=floor(world.x/3)*3+1.5;
                float dashShapeV=step(abs(world.y-zc),.8), dashShapeH=step(abs(world.x-xc),.8);
                // Clearance from the dash centre to every crossing on that street (junction box + corner
                // crosswalks reach 6.3 m from the junction centre).
                float clearV=min(abs(zc+15.5),abs(zc-30))-6.3;
                clearV=min(clearV,world.x<0?abs(zc+8.5)-1.25:abs(zc)-1.25);
                float clearH=abs(abs(xc)-23.5)-6.3;
                clearH=min(clearH,world.y>7?abs(xc+4)-1.25:min(abs(xc+1.75)-1.25,abs(xc+11.2)-2.2));
                float dashV=dashShapeV*(1-smoothstep(.06,.10,vaxis))*step(1.3,clearV);
                float dashH=dashShapeH*(1-smoothstep(.06,.10,haxis))*step(1.3,clearH);
                float crossV=step(abs(world.y+8.5),1.25)*step(world.x,0);
                float crossE=step(abs(world.y),1.25)*step(0,world.x);
                float crossN=step(abs(world.x+4),1.25)*step(7,world.y);
                float crossS=step(abs(world.x+1.75),1.25)*step(world.y,7);
                float cornerZ=min(min(abs(world.y+21),abs(world.y+10)),min(abs(world.y-24.5),abs(world.y-35.5)));
                float cornerX=min(abs(abs(world.x)-29),abs(abs(world.x)-18));
                float crossAlongV=max(max(crossV,crossE),step(cornerZ,.8))*step(vaxis,2.8);
                float crossAlongH=max(max(crossN,crossS),step(cornerX,.8))*step(haxis,2.8);
                // Zebra bars are symmetric about the centre line: eight bars, a gap on the axis itself,
                // so the lane divider never appears to run through a crosswalk.
                float barsV=step(abs(frac(vaxis/.7)-.5),.3);
                float barsH=step(abs(frac(haxis/.7)-.5),.3);
                float markings=max(dashV,dashH);
                markings=lerp(markings,barsV,crossAlongV);
                markings=lerp(markings,barsH,crossAlongH);
                color=lerp(color,float3(.79,.78,.70),markings*road*step(.1,driveway));
                float parkingCross=step(abs(world.x+11.2),2.05)*step(abs(world.y+11.5),.85);
                color=lerp(color,float3(.79,.78,.70),parkingCross*road*step(.4,frac(world.x/.7)));
                float2 loadingDelta=abs(world-_LoadingAccess.xy);
                float loadingAccess=step(loadingDelta.x,_LoadingAccess.z)*step(loadingDelta.y,_LoadingAccess.w)*_LoadingAccessEnabled;
                color=lerp(color,asphalt,loadingAccess);
                float loadingCross=loadingAccess*step(loadingDelta.y,.7)*step(.42,frac((world.x-_LoadingAccess.x)/.9));
                color=lerp(color,float3(.79,.78,.70),loadingCross);
            }
            if(_ExpansionProjection>.5)
            {
                // The whole market block uses the same gray square paving as the surrounding city
                // blocks. Purchased areas draw only their own surfaces below, so the old painted
                // tiles never show through as loose asphalt patches around the building.
                float block=step(abs(world.x),19)*step(abs(world.y-6.5),19);
                float2 pavementUV=(float2(854,482)+frac(world/4)*float2(344,332))/1254;
                float3 pavement=tex2D(_MainTex,pavementUV).rgb*_Color.rgb;
                // Keep only the painted plaza stones of the purchased park.
                float plaza=step(abs(kind-3),.5)*step(abs(world.x+14.1),4.6)*step(abs(world.y-21),4)*_ExpansionFeatures.w;
                color=lerp(color,pavement,block*(1-plaza));
                // These connections remain public even while the surrounding lots are locked.
                float frontWalk=step(abs(world.y+11.5),1)*step(abs(world.x),20.4);
                float2 slab=abs(frac(world)-.5);
                float joints=smoothstep(.475,.495,max(slab.x,slab.y));
                color=lerp(color,lerp(float3(.43,.45,.44),float3(.30,.32,.31),joints*.35),frontWalk);
                float entranceDrive=step(abs(world.x+11.2),2.2)*step(abs(world.y+12),4)*_ExpansionFeatures.y;
                float lotEnd=-5.5+max(0,_ParkingSpaces-1)*4+2;
                float lot=step(abs(world.x+14.1),4.6)*step(-7.5,world.y)*step(world.y,lotEnd)*_ExpansionFeatures.y;
                // Loading yard apron under the truck bays, joined to the north street entrance.
                float yard=step(abs(world.x-9.25),6.95)*step(abs(world.y-20.35),5.15)*_ExpansionFeatures.z;
                color=lerp(color,asphalt,max(max(entranceDrive,lot),yard));
                float crossing=entranceDrive*step(abs(world.y+11.5),.8)*step(.4,frac(world.x/.7));
                color=lerp(color,float3(.79,.78,.70),crossing);
            }
            o.Albedo=color;
            o.Alpha=1;
        }
        ENDCG
    }
    Fallback "Diffuse"
}
