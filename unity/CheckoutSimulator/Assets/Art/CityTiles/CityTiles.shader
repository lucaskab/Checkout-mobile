Shader "MarketDay/City Tiles"
{
    Properties
    {
        [PerRendererData] _MainTex ("Tileset", 2D) = "white" {}
        _LoadingAccessEnabled ("Loading yard entrance", Float) = 0
        _LoadingAccess ("Loading entrance center and half size", Vector) = (12.97,27.9,8.38,2.5)
        _WideStreets ("Wide city streets", Float) = 0
        _ExpansionProjection ("Project purchased market areas", Float) = 0
        _ExpansionFeatures ("Storage parking loading premium", Vector) = (1,1,1,1)
        _ParkingSpaces ("Purchased parking spaces", Float) = 5
        _MarketFootprint ("Market center and half size", Vector) = (0,0,9.4,7.4)
        _Color ("Pavement tint", Color) = (0.72,0.75,0.78,1)
        _RoundaboutEnabled ("Columbus Circle roundabout", Float) = 0
        _Roundabout ("Roundabout center xz, island and outer radius", Vector) = (-23.5,-18.5,3.4,7.5)
        _CityPark ("Central Park block across 59th Street", Float) = 0
        _HarbourPlaza ("Harbour Quay public plaza on the market block", Float) = 0
        _Basin ("Harbour basin center and half size", Vector) = (7.4,36.5,6.9,3)
        _DerelictLot ("Abandoned warehouse lot center and half size", Vector) = (-10.55,33.6,7.85,6.2)
        _GrandYardEnabled ("Central warehouse truck yard", Float) = 0
        _GrandYard ("Central warehouse yard center and half size", Vector) = (8.35,33.5,8.55,4.9)
        _GrandAccess ("Central warehouse yard driveway center and half size", Vector) = (19.1,33.5,2.25,2.2)
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
        float _RoundaboutEnabled, _CityPark, _HarbourPlaza;
        float4 _Roundabout, _Basin, _DerelictLot;
        float _GrandYardEnabled;
        float4 _GrandYard, _GrandAccess;
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
        float segment(float2 p,float2 a,float2 b){float2 pa=p-a,ba=b-a;float h=saturate(dot(pa,ba)/dot(ba,ba));return length(pa-ba*h);}
        // Central Park South layout; mirrors CheckoutCityPark.cs.
        float driveZ(float x){return -32.3+1.05*sin(x*.21+1.3);}
        float pondDistance(float2 p){float2 q=(p-float2(7.2,-39))/float2(5.4,3.2);return (length(q)-1)*3.2;}
        float parkPaths(float2 p,out float drive)
        {
            drive=abs(p.y-driveZ(p.x))-1.35;
            float diagonal=min(segment(p,float2(-13.2,-33.2),float2(-9.8,-35)),min(segment(p,float2(-9.8,-35),float2(-7.2,-39.5)),segment(p,float2(-7.2,-39.5),float2(-6.6,-44.5))))-.75;
            float central=abs(p.x-(-1.75+1.4*sin((p.y+28.5)*.28)))-.7;
            float ring=abs(pondDistance(p)-1.3)-.6;
            float east=min(segment(p,float2(12.9,-28.5),float2(12.7,-31.5)),segment(p,float2(12.7,-31.5),float2(11.6,-34.6)))-.7;
            return min(min(diagonal,central),min(ring,east));
        }
        // Central Park's hexagonal asphalt pavers: 1 inside a joint, 0 on a block.
        float hexJoint(float2 p)
        {
            p/=.46;
            float2 r=float2(1,1.7320508);
            float2 a=(frac(p/r)-.5)*r, b=(frac((p-r*.5)/r)-.5)*r;
            float2 g=dot(a,a)<dot(b,b)?a:b;
            float2 q=abs(g);
            float edge=max(q.x,dot(q,float2(.5,.8660254)));
            return smoothstep(.43,.48,edge);
        }
        void surf(Input IN,inout SurfaceOutput o)
        {
            float kind=round(IN.tileData.r*7), mask=round(IN.tileData.g*15);
            float2 world=IN.worldPos.xz;
            float bikeLane=0, bikeAcross=0, bikeAlong=0, bikeFord=0, bikeIcons=1;
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
                // Narrow local streets at x ±23.5 (4.5 m) and a four-lane avenue in front of the market
                // (z -24.5 to -12.5). There is no street behind the market block any more.
                float dx=abs(abs(world.x)-23.5)-2.25;
                float dz=abs(world.y+18.5)-6;
                float blend=saturate(.5+.5*(dz-dx)/.8);
                float street=lerp(dz,dx,blend)-.8*blend*(1-blend);
                // Columbus Circle: the west junction becomes a ring road around a monument island.
                float2 circleDelta=world-_Roundabout.xy;
                float rc=length(circleDelta);
                float circle=_RoundaboutEnabled*step(world.x,0);
                if(circle>.5)
                {
                    float ring=max(rc-_Roundabout.w,_Roundabout.z-rc);
                    street=min(max(street,_Roundabout.z-rc),ring);
                    // The circle's outer sidewalk is a plain avenue-style walk (no grass lawn).
                    blend*=step(_Roundabout.w+4.2,rc);
                }
                float ringClear=1-circle*(1-step(_Roundabout.w+.35,rc));
                float2 drive=abs(world-float2(-11.2,-10))-float2(2.2,5.5);
                float driveway=max(drive.x,drive.y);
                float distance=street; // the car park entrance is painted with the market block
                float aa=max(fwidth(distance),.015);
                float2 uv=(float2(854,482)+frac(world/4)*float2(344,332))/1254;
                if(kind<1.5)color=tex2D(_MainTex,uv).rgb*_Color.rgb;
                // 4 m sidewalks everywhere, like the one in front of the market (and round the circle).
                float band=4;
                float pavement=step(.03,street)*(1-smoothstep(band-.05,band+.05,street));
                float2 slab=abs(frac(world)-.5);
                float joint=smoothstep(.475,.495,max(slab.x,slab.y));
                float3 sidewalk=lerp(float3(.43,.45,.44),float3(.30,.32,.31),joint*.35);
                // Central Park South sidewalks use the park's dark hexagonal pavers.
                float hexWalk=_CityPark*step(world.y,-24.45)*step(abs(world.x),21.35)*(1-circle*step(rc,_Roundabout.w+2.2));
                sidewalk=lerp(sidewalk,lerp(float3(.33,.34,.33),float3(.21,.22,.22),hexJoint(world)),hexWalk);
                color=lerp(color,sidewalk,pavement);
                float vaxis=abs(abs(world.x)-23.5), haxis=abs(world.y+18.5);
                // Crossings line up with the footways behind the cycle lanes (CheckoutStreetLayout).
                float crossV=circle*step(abs(world.y+6.2),.8)*step(world.x,0); // north arm of the circle
                float crossE=0; // the mid-block crossing on the east street was removed
                float crossS=step(abs(world.x+1.75),1.25);
                float cornerZ=min(abs(world.y+9.8),abs(world.y+27.2));
                float cornerX=min(abs(abs(world.x)-18.55),abs(abs(world.x)-28.45));
                // Around the roundabout the crossings move out onto the approach arms, beyond the sidewalk ring
                // (south arm z -30.8, west arm x -35.8); there is none at the market corner by the circle.
                cornerZ=lerp(cornerZ,abs(world.y+30.8),circle);
                cornerX=lerp(cornerX,abs(world.x+35.8),circle);
                // Berlin style Radweg: a one-way cycle lane on every sidewalk, right beside the curb, in the same
                // dark grey as the Central Park drive. Painted last, over the market block surfaces.
                float laneCentre=.8;
                bikeAcross=street-laneCentre;
                bikeAlong=blend>.5?world.y:world.x;
                bikeLane=pavement*(1-smoothstep(.57,.61,abs(bikeAcross)))*(1-circle*step(rc,_Roundabout.z+.05));
                bikeIcons=1-circle*(1-step(_Roundabout.w+4,rc));
                float curb=(1-smoothstep(.04,.12,abs(distance)));
                color=lerp(color,float3(.65,.65,.60),curb);
                float road=1-smoothstep(-aa,aa,distance);
                color=lerp(color,asphalt,road);
                // Centre-line dashes are whole 1.6 m segments. Each segment is kept or dropped as a unit,
                // judged at its own centre, so no stub is ever cut by a junction, crosswalk or driveway.
                float zc=floor(world.y/3)*3+1.5, xc=floor(world.x/3)*3+1.5;
                float dashShapeV=step(abs(world.y-zc),.8), dashShapeH=step(abs(world.x-xc),.8);
                // Junction box plus corner crosswalks reach 10.3 m (local street) / 6.2 m (avenue) from the centre.
                // On the arms of the circle the lines run up to the ring, stopping only for the crosswalk.
                float dV=abs(zc+18.5), dH=abs(abs(xc)-23.5);
                float clearV=circle>.5?min(dV-8.6,abs(dV-12.3)-1.7)+1.3:dV-10.3;
                float clearH=circle>.5?min(dH-8.6,abs(dH-12.3)-1.7)+1.3:dH-6.2;
                clearH=min(clearH,abs(xc+1.75)-1.25);
                float dashV=dashShapeV*(1-smoothstep(.06,.10,vaxis))*step(1.3,clearV);
                // Avenue: dashed lane dividers 3 m either side of a solid double centre line.
                float dashH=dashShapeH*(1-smoothstep(.06,.10,abs(haxis-3)))*step(1.3,clearH);
                float dS=abs(abs(world.x)-23.5);
                float clearSolid=min(circle>.5?min(dS-7.7,abs(dS-12.3)-.9):dS-6.2,abs(world.x+1.75)-1.25);
                float centre=(1-smoothstep(.05,.08,abs(haxis-.14)))*step(0,clearSolid)*step(haxis,1);
                float crossAlongV=max(max(crossV,crossE),step(cornerZ,.8))*step(vaxis,2.05)*step(.99,blend);
                float crossAlongH=max(crossS,step(cornerX,.8))*step(haxis,5.8)*step(blend,.01);
                // Zebra bars are symmetric about the centre line, with a gap on the axis itself.
                float barsV=step(abs(frac(vaxis/.7)-.5),.3);
                float barsH=step(abs(frac(haxis/.7)-.5),.3);
                float markings=max(dashV,dashH);
                markings=lerp(markings,barsV,crossAlongV);
                markings=lerp(markings,barsH,crossAlongH);
                float onRoad=road*step(.1,driveway)*ringClear;
                color=lerp(color,float3(.79,.78,.70),markings*onRoad);
                color=lerp(color,float3(.86,.70,.28),centre*onRoad*(1-max(crossAlongH,crossAlongV)));
                // Columbus Circle is two lanes wide: a dashed white divider runs round the ring.
                float ringArc=atan2(circleDelta.y,circleDelta.x)*5.45;
                float ringDivider=circle*(1-smoothstep(.05,.08,abs(rc-5.45)))*step(frac(ringArc/3),.5);
                color=lerp(color,float3(.79,.78,.70),ringDivider*road);
                // Cycle crossings where the lanes cross a road at the east junction (the circle is ridden on the road).
                float fordAvenue=step(0,world.x)*step(vaxis,2.35)*max(step(abs(world.y+11.7),.6),step(abs(world.y+25.3),.6));
                float fordStreet=step(0,world.x)*step(haxis,6.1)*max(step(abs(world.x-20.45),.6),step(abs(world.x-26.55),.6));
                bikeFord=road*saturate(fordAvenue+fordStreet);
                if(circle>.5)
                {
                    float angle=atan2(circleDelta.y,circleDelta.x);
                    if(rc<_Roundabout.z)
                    {
                        // Monument island: granite curb, a lawn ring and a paved fountain terrace.
                        float3 granite=lerp(float3(.66,.64,.60),float3(.58,.56,.52),step(.5,frac(rc/.55))*.5+hash(floor(float2(angle*6,rc*2)))*.3);
                        float3 lawnColor=float3(.34,.50,.26)+(noise(world*3.3)-.5)*.05;
                        float3 island=lerp(granite,lawnColor,step(rc,_Roundabout.z-.45)*step(_Roundabout.z-1.25,rc));
                        island=lerp(island,float3(.74,.72,.67),1-smoothstep(_Roundabout.z-.3,_Roundabout.z-.22,rc));
                        color=lerp(island,float3(.74,.72,.67),step(_Roundabout.z-.22,rc));
                    }
                }
            }
            if(_CityPark>.5 && world.y<-28.45 && abs(world.x)<17.3)
            {
                // Southern tip of the park: meadows, a drive, winding paths and a pond.
                float driveDistance;
                float paths=parkPaths(world,driveDistance);
                float3 grass=float3(.33,.49,.25)+(noise(world*.9)-.5)*.07+(noise(world*6.5)-.5)*.035;
                // Blades and clover: fine light/dark flecks so the lawn is not a flat fill.
                float blade=hash(floor(world*18));
                grass*=.9+.2*blade;
                grass=lerp(grass,float3(.44,.60,.30),step(.94,hash(floor(world*9)))*.6);
                grass*=1-.06*step(.5,frac((world.x+world.y*.3)/2.2)); // mown stripes
                float3 park=grass;
                float aa=.04;
                // Fine gravel on the footpaths: speckled stones over a sandy base.
                float gravel=hash(floor(world*14));
                float3 pathColor=lerp(float3(.62,.60,.55),float3(.52,.50,.46),noise(world*4)*.7+gravel*.3);
                pathColor=lerp(pathColor,float3(.40,.38,.35),step(.9,gravel)*.6);
                park=lerp(park,float3(.42,.40,.32),1-smoothstep(0,.18,paths)); // soft soil edge
                park=lerp(park,pathColor,1-smoothstep(-aa,aa,paths));
                float3 driveColor=float3(.25,.27,.30)+(noise(world*18)-.5)*.01;
                park=lerp(park,float3(.42,.40,.32),1-smoothstep(0,.18,driveDistance));
                park=lerp(park,driveColor,1-smoothstep(-aa,aa,driveDistance));
                float driveOffset=world.y-driveZ(world.x);
                float bikeLine=(1-smoothstep(.03,.06,abs(abs(driveOffset)-.55)))*step(.5,frac(world.x/1.4));
                park=lerp(park,float3(.82,.80,.72),bikeLine*step(driveDistance,0));
                // The Pond with a rocky shore.
                float pond=pondDistance(world);
                float ripple=noise(world*2.2+_Time.y*float2(.35,.2))*.05;
                float3 water=lerp(float3(.19,.39,.47),float3(.30,.52,.58),saturate(-pond*.35)+ripple);
                float3 shore=lerp(float3(.47,.46,.42),float3(.36,.35,.33),noise(world*5.5));
                park=lerp(park,shore,1-smoothstep(.45,.55,pond));
                park=lerp(park,water,1-smoothstep(-aa,aa,pond));
                color=park;
            }
            if(_HarbourPlaza>.5)
            {
                // Harbour Quay public square on the market block (behind the avenue sidewalk).
                float block=step(abs(world.x),17.25)*step(-8.5,world.y);
                float plaza=step(abs(kind-3),.5)*step(abs(world.x+14.1),4.6)*step(abs(world.y-21),4)*_ExpansionFeatures.w*_ExpansionProjection;
                // Harbour Quay style public square: pale granite slabs with long basalt bands and the cracked
                // yard of the abandoned warehouse. (Cycling now uses the street lanes.)
                float slabRow=floor(world.y/.75);
                float2 slabUV=float2(frac((world.x+slabRow*.5)/1.5),frac(world.y/.75));
                float slabJoint=smoothstep(.46,.49,max(abs(slabUV.x-.5),abs(slabUV.y-.5)));
                float slabTone=hash(float2(floor((world.x+slabRow*.5)/1.5),slabRow));
                float3 quay=lerp(float3(.71,.69,.64),float3(.61,.59,.55),slabTone);
                quay*=.93+.1*noise(world*6.3)+.04*noise(world*23);           // grain
                quay=lerp(quay,float3(.46,.45,.42),slabJoint*.7);             // joints
                quay*=1-.07*smoothstep(.40,.47,slabUV.y)+.05*smoothstep(.1,.02,slabUV.y); // bevelled edges
                // Long dark basalt bands (1.1 m) every 7 m, laid in smaller setts.
                float basalt=smoothstep(2.9,2.95,abs(frac(world.y/7)-.5)*7);
                float2 sett=abs(frac(world*float2(2.5,2.5))-.5);
                float3 dark=lerp(float3(.36,.37,.38),float3(.30,.31,.32),hash(floor(world*2.5)))*(1-.35*smoothstep(.42,.49,max(sett.x,sett.y)));
                quay=lerp(quay,dark,basalt);
                color=lerp(color,quay,block*(1-plaza));
                float2 lotBox=abs(world-_DerelictLot.xy)-_DerelictLot.zw;
                float derelict=step(max(lotBox.x,lotBox.y),0);
                float cracks=1-smoothstep(.0,.035,abs(noise(world*.9)-.5)-.01*noise(world*7));
                float3 concrete=lerp(float3(.55,.54,.50),float3(.47,.46,.43),noise(world*1.7))*(1-cracks*.35);
                concrete=lerp(concrete,float3(.36,.44,.24),smoothstep(.62,.7,noise(world*.8+3.1))*.8);
                color=lerp(color,concrete,derelict);
            }
            if(_ExpansionProjection>.5)
            {
                // The whole market block uses the same gray square paving as the surrounding city
                // blocks. Purchased areas draw only their own surfaces below, so the old painted
                // tiles never show through as loose asphalt patches around the building.
                // The block runs from the avenue sidewalk to the north edge of the map (no back street).
                float block=step(abs(world.x),17.25)*step(-8.5,world.y);
                float2 pavementUV=(float2(854,482)+frac(world/4)*float2(344,332))/1254;
                float3 pavement=tex2D(_MainTex,pavementUV).rgb*_Color.rgb;
                // Keep only the painted plaza stones of the purchased park.
                float plaza=step(abs(kind-3),.5)*step(abs(world.x+14.1),4.6)*step(abs(world.y-21),4)*_ExpansionFeatures.w;
                color=lerp(color,pavement,block*(1-plaza)*(1-_HarbourPlaza));
                // Car park entrance: asphalt from the avenue curb across the sidewalk to the lot, once bought.
                float entranceDrive=step(abs(world.x+11.2),2.2)*step(-12.55,world.y)*step(world.y,-7.4)*_ExpansionFeatures.y;
                float lotEnd=-5.5+max(0,_ParkingSpaces-1)*4+2;
                float lot=step(abs(world.x+14.1),4.6)*step(-7.5,world.y)*step(world.y,lotEnd)*_ExpansionFeatures.y;
                // Loading yard apron under the truck bays, joined to the east street driveway.
                float yard=step(abs(world.x-9.25),6.95)*step(abs(world.y-20.35),5.15)*_ExpansionFeatures.z;
                // Truck yard of the central warehouse (replaces the old yard once bought).
                float2 grandDelta=abs(world-_GrandYard.xy);
                float grandYard=step(grandDelta.x,_GrandYard.z)*step(grandDelta.y,_GrandYard.w)*_GrandYardEnabled;
                color=lerp(color,asphalt,max(max(max(entranceDrive,lot),yard),grandYard));
                float crossing=entranceDrive*step(abs(world.y+9.8),.8)*step(.4,frac(world.x/.7));
                color=lerp(color,float3(.79,.78,.70),crossing);
            }
            if(_WideStreets>.5)
            {
                // Dark grey asphalt like the Central Park drive, a white line on the footway side and a bicycle
                // symbol every 16 m.
                float3 red=float3(.25,.27,.30)+(noise(world*18)-.5)*.012+(noise(world*2.5)-.5)*.02;
                float edge=1-smoothstep(.025,.05,abs(bikeAcross-.54));
                float u=(frac(bikeAlong/16)-.5)*16, v=bikeAcross;
                float2 q=float2(u,v);
                float icon=min(abs(length(q-float2(.28,-.05))-.16),abs(length(q-float2(-.28,-.05))-.16));
                icon=min(icon,min(segment(q,float2(-.28,-.05),float2(0,-.05)),segment(q,float2(0,-.05),float2(.13,.17))));
                icon=min(icon,min(segment(q,float2(-.28,-.05),float2(-.08,.17)),segment(q,float2(-.08,.17),float2(.13,.17))));
                icon=min(icon,min(segment(q,float2(.28,-.05),float2(.17,.25)),min(segment(q,float2(.12,.26),float2(.24,.26)),segment(q,float2(-.15,.2),float2(-.02,.2)))));
                float iconMask=(1-smoothstep(.02,.035,icon))*step(abs(u),.5)*bikeIcons;
                float3 lane=lerp(red,float3(.93,.92,.88),saturate(edge+iconMask));
                color=lerp(color,lane,bikeLane);
                color=lerp(color,float3(.25,.27,.30),bikeFord*.9);
            }
            if(_WideStreets>.5)
            {
                // Truck apron from the loading yard across the east sidewalk to the local street.
                float2 loadingDelta=abs(world-_LoadingAccess.xy);
                float loadingAccess=step(loadingDelta.x,_LoadingAccess.z)*step(loadingDelta.y,_LoadingAccess.w)*_LoadingAccessEnabled;
                color=lerp(color,asphalt,loadingAccess);
                float loadingEdge=loadingAccess*step(_LoadingAccess.w-.12,loadingDelta.y)*step(abs(abs(world.x)-19.25),2);
                color=lerp(color,float3(.79,.78,.70),loadingEdge);
                float2 grandAccessDelta=abs(world-_GrandAccess.xy);
                float grandAccess=step(grandAccessDelta.x,_GrandAccess.z)*step(grandAccessDelta.y,_GrandAccess.w)*_GrandYardEnabled;
                color=lerp(color,asphalt,grandAccess);
                color=lerp(color,float3(.79,.78,.70),grandAccess*step(_GrandAccess.w-.12,grandAccessDelta.y));
            }
            o.Albedo=color;
            o.Alpha=1;
        }
        ENDCG
    }
    Fallback "Diffuse"
}
