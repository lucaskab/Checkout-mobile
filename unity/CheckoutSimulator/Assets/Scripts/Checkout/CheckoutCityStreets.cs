using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;

namespace Checkout
{
    public class CheckoutCityStreets : MonoBehaviour
    {
        public Bounds[] sidewalks;
        public Vector3[] entrances;
        public Vector3[] patrolPoints { get; private set; }
        public Bounds cityBounds { get; private set; }
        public void AddNavigation(List<NavMeshBuildSource> sources)
        {
            // Follow the painted street grid across the whole terrain, not only the central block.
            var terrain=FindAnyObjectByType<UnityEngine.Tilemaps.TilemapRenderer>();
            cityBounds=terrain?terrain.bounds:new Bounds(new Vector3(0,0,6),new Vector3(80,1,84));
            var min=cityBounds.min+Vector3.one*1.5f;var max=cityBounds.max-Vector3.one*1.5f;
            var walks=new List<Bounds>();var patrol=new List<Vector3>();var doors=new List<Vector3>();
            void Walk(Vector3 a,Vector3 b,float width=1.8f)
            {
                var size=new Vector3(Mathf.Abs(a.x-b.x)+width,.2f,Mathf.Abs(a.z-b.z)+width);
                walks.Add(new Bounds(new Vector3((a.x+b.x)*.5f,.05f,(a.z+b.z)*.5f),size));
            }
            // Narrow local streets at x ±23.5 and the four-lane avenue at z -24.5..-12.5, with wide sidewalks
            // (the footway is behind the cycle lane; see CheckoutStreetLayout). The market block runs north
            // to the map edge: there is no back street.
            const float IX=CheckoutStreetLayout.InnerWalkX,OX=CheckoutStreetLayout.OuterWalkX,NZ=CheckoutStreetLayout.NorthWalkZ,SZ=CheckoutStreetLayout.SouthWalkZ;
            foreach(float x in new[]{-OX,-IX,IX,OX})
            {
                foreach(var span in new[]{new Vector2(min.z,SZ+.05f),new Vector2(NZ-.05f,max.z)})
                    Walk(new Vector3(x,0,span.x),new Vector3(x,0,span.y),2.6f);
                patrol.Add(new Vector3(x,.15f,min.z+.5f));patrol.Add(new Vector3(x,.15f,max.z-.5f));
            }
            foreach(float z in new[]{SZ,NZ})
            {
                foreach(var span in new[]{new Vector2(min.x,-OX+.05f),new Vector2(-IX-.05f,IX+.05f),new Vector2(OX-.05f,max.x)})
                    Walk(new Vector3(span.x,0,z),new Vector3(span.y,0,z),2f);
                patrol.Add(new Vector3(min.x+.5f,.15f,z));patrol.Add(new Vector3(max.x-.5f,.15f,z));
            }
            var circle=CheckoutRoundabout.Current;
            bool Round(float x)=>circle&&Mathf.Abs(circle.center.x-x)<.1f&&Mathf.Abs(circle.center.z+18.5f)<.1f;
            float arm=CheckoutStreetLayout.CircleCrossing;
            // Market entrance straight across the avenue to the park's central gate.
            Walk(new Vector3(-1.75f,0,SZ),new Vector3(-1.75f,0,-9.2f),2.5f);
            // Crossing strips; the road itself is never walkable. Local streets are crossed in line with the
            // avenue footways, the avenue in line with the local footways. At Columbus Circle the crossings sit
            // on the approach arms beyond the sidewalk ring (north z -18.5+arm, south z -18.5-arm, west x -23.5-arm);
            // there is none at the market corner.
            foreach(float x in new[]{-23.5f,23.5f})foreach(float z in Round(x)?new[]{-18.5f-arm,-18.5f+arm}:new[]{SZ,NZ})
            {
                Walk(new Vector3(x-(OX-23.5f),0,z),new Vector3(x+(OX-23.5f),0,z),1.6f);
                if(Round(x)){float walk=z<-18.5f?SZ:NZ;Walk(new Vector3(-OX,0,z),new Vector3(-OX,0,walk),1.6f);Walk(new Vector3(-IX,0,z),new Vector3(-IX,0,walk),1.6f);}
            }
            foreach(float x in Round(-23.5f)?new[]{-23.5f-arm,IX,OX}:new[]{-OX,-IX,IX,OX})
            {
                Walk(new Vector3(x,0,SZ),new Vector3(x,0,NZ),1.6f);
                if(x< -30f){Walk(new Vector3(x,0,SZ),new Vector3(-OX,0,SZ),1.6f);Walk(new Vector3(x,0,NZ),new Vector3(-OX,0,NZ),1.6f);}
            }
            var world=FindAnyObjectByType<MarketDay.MarketSimulation>().world;
            // Central Park South: gates from the 59th Street sidewalk onto the park drive and the paths.
            if(world.Find("Central Park South"))
            {
                float Drive(float x)=>CheckoutCityPark.DriveZ(x);
                float gateX=CheckoutCityPark.PathX(CheckoutCityPark.North);
                Walk(new Vector3(gateX,0,SZ),new Vector3(gateX,0,Drive(gateX)),1.6f);
                var east=CheckoutCityPark.EastPath;
                Walk(new Vector3(east[0].x,0,SZ),new Vector3(east[0].x,0,east[0].y),1.6f);
                for(int i=0;i<east.Length-1;i++)Walk(new Vector3(east[i].x,0,east[i].y),new Vector3(east[i+1].x,0,east[i+1].y),1.4f);
                // The drive opens onto both side streets' sidewalks.
                foreach(float side in new[]{-1f,1f}){float x=side*CheckoutCityPark.East;Walk(new Vector3(side*IX,0,Drive(x)),new Vector3(x,0,Drive(x)),1.8f);}
                for(float x=CheckoutCityPark.West;x<CheckoutCityPark.East-.5f;x+=3f)Walk(new Vector3(x,0,Drive(x)),new Vector3(Mathf.Min(x+3,CheckoutCityPark.East),0,Drive(Mathf.Min(x+3,CheckoutCityPark.East))),1.8f);
                foreach(float x in new[]{-12f,-1.75f,9f})patrol.Add(new Vector3(x,.15f,Drive(x)));
                // Footpaths: the central path, the diagonal from Merchants' Gate and the loop round the pond.
                for(float z=-43.5f;z<Drive(-1.75f);z+=2.5f)Walk(new Vector3(CheckoutCityPark.PathX(z),0,z),new Vector3(CheckoutCityPark.PathX(z+2.5f),0,z+2.5f),1.4f);
                var diagonal=System.Array.ConvertAll(CheckoutCityPark.Diagonal,p=>new Vector3(p.x,0,Mathf.Max(p.y,-43.5f)));
                for(int i=0;i<diagonal.Length-1;i++)for(int k=0;k<4;k++)Walk(Vector3.Lerp(diagonal[i],diagonal[i+1],k/4f),Vector3.Lerp(diagonal[i],diagonal[i+1],(k+1)/4f),1.4f);
                Vector3 Ring(float a){var e=new Vector2(Mathf.Cos(a)*CheckoutCityPark.PondRadii.x,Mathf.Sin(a)*CheckoutCityPark.PondRadii.y);var p=CheckoutCityPark.Pond+e+e.normalized*CheckoutCityPark.RingOffset;return new Vector3(p.x,.15f,Mathf.Max(p.y,-43.6f));}
                for(int i=0;i<16;i++)Walk(Ring(i*Mathf.PI/8),Ring((i+1)*Mathf.PI/8),1.3f);
                Walk(Ring(Mathf.PI*.5f),new Vector3(Ring(Mathf.PI*.5f).x,0,Drive(Ring(Mathf.PI*.5f).x)),1.3f);
                foreach(float a in new[]{0f,1.6f,3.1f,4.7f})patrol.Add(Ring(a));
                patrol.Add(new Vector3(CheckoutCityPark.PathX(-42f),.15f,-42f));patrol.Add(new Vector3(-7f,.15f,-42f));
            }
            foreach(string groupName in new[]{"Supplied City Models","City Establishments","Expansion Neighborhood"})
            {
                var group=world.Find(groupName);if(!group)continue;
                foreach(Transform building in group)
                {
                    if(!building.gameObject.activeInHierarchy||building.name.Contains("vehicle")||building.name.StartsWith("City ")||building.name.StartsWith("Neighborhood car"))continue;
                    var renderers=building.GetComponentsInChildren<MeshRenderer>();if(renderers.Length==0)continue;
                    var b=renderers[0].bounds;foreach(var r in renderers)b.Encapsulate(r.bounds);
                    Vector3 door,curb;
                    if(Mathf.Abs(b.center.x)>CheckoutStreetLayout.LocalCurbOuter)
                    {
                        float side=Mathf.Sign(b.center.x);
                        door=new Vector3(b.center.x-side*(b.extents.x+.5f),.15f,b.center.z);curb=new Vector3(side*CheckoutStreetLayout.OuterWalkX,.15f,door.z);
                    }
                    else if(b.center.z>20)
                    {
                        // Rear lots face north. East of the loading yard they join the east sidewalk; the rest
                        // share a rear path at z 26 to the west sidewalk, behind the other rear lots.
                        door=new Vector3(b.center.x,.15f,b.max.z+.5f);
                        curb=b.center.x>8?new Vector3(CheckoutStreetLayout.InnerWalkX,.15f,door.z):new Vector3(-CheckoutStreetLayout.InnerWalkX,.15f,26);
                    }
                    else
                    {
                        float side=Mathf.Sign(b.center.x);
                        door=new Vector3(b.center.x+side*(b.extents.x+.5f),.15f,b.center.z);curb=new Vector3(side*CheckoutStreetLayout.InnerWalkX,.15f,door.z);
                    }
                    Walk(door,curb);doors.Add(door);
                    sources.Add(new NavMeshBuildSource{shape=NavMeshBuildSourceShape.Box,transform=Matrix4x4.TRS(new Vector3(b.center.x,1.5f,b.center.z),Quaternion.identity,Vector3.one),size=new Vector3(b.size.x,3,b.size.z),area=1});
                }
            }
            sidewalks=walks.ToArray();entrances=doors.ToArray();patrolPoints=patrol.ToArray();
            foreach(var bounds in sidewalks)
                sources.Add(new NavMeshBuildSource{shape=NavMeshBuildSourceShape.Box,transform=Matrix4x4.TRS(bounds.center,Quaternion.identity,Vector3.one),size=bounds.size,area=0});
        }
    }
}
