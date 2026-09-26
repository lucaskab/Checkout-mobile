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
            // Narrow local streets at x ±23.5 and the four-lane avenue at z -24.5..-12.5. The market
            // block runs north to the map edge: there is no back street.
            foreach(float x in new[]{-27.5f,-19.5f,19.5f,27.5f})
            {
                foreach(var span in new[]{new Vector2(min.z,-25.45f),new Vector2(-11.55f,max.z)})
                    Walk(new Vector3(x,0,span.x),new Vector3(x,0,span.y));
                patrol.Add(new Vector3(x,.15f,min.z+.5f));patrol.Add(new Vector3(x,.15f,max.z-.5f));
            }
            foreach(float z in new[]{-25.5f,-11.5f})
            {
                foreach(var span in new[]{new Vector2(min.x,-27.45f),new Vector2(-19.55f,19.55f),new Vector2(27.45f,max.x)})
                    Walk(new Vector3(span.x,0,z),new Vector3(span.y,0,z));
                patrol.Add(new Vector3(min.x+.5f,.15f,z));patrol.Add(new Vector3(max.x-.5f,.15f,z));
            }
            Walk(new Vector3(-27.5f,0,-8.5f),new Vector3(-19.5f,0,-8.5f),2.5f);
            Walk(new Vector3(19.5f,0,0),new Vector3(27.5f,0,0),2.5f);
            Walk(new Vector3(-1.75f,0,-25.5f),new Vector3(-1.75f,0,-9.2f),2.5f);
            // Crossing strips are inset from each junction; the road itself is never walkable. The west
            // junction can be a roundabout (Columbus Circle): its crossings sit outside the circle, on the
            // approach arms (south arm z -28.5, avenue arms x -32.25 / -14.75; north arm uses z -8.5).
            var circle=CheckoutRoundabout.Current;
            bool Round(float x)=>circle&&Mathf.Abs(circle.center.x-x)<.1f&&Mathf.Abs(circle.center.z+18.5f)<.1f;
            foreach(float x in new[]{-23.5f,23.5f})foreach(float z in Round(x)?new[]{-28.5f}:new[]{-27f,-10f})
            {
                float walk=z<-18.5f?-25.5f:-11.5f;
                Walk(new Vector3(x-4,0,z),new Vector3(x+4,0,z),1.6f);
                Walk(new Vector3(x-4,0,z),new Vector3(x-4,0,walk),1.6f);
                Walk(new Vector3(x+4,0,z),new Vector3(x+4,0,walk),1.6f);
            }
            foreach(float x in Round(-23.5f)?new[]{-32.25f,-14.75f,18.75f,28.25f}:new[]{-28.25f,-18.75f,18.75f,28.25f})
                Walk(new Vector3(x,0,-25.5f),new Vector3(x,0,-11.5f),1.6f);
            var world=FindAnyObjectByType<MarketDay.MarketSimulation>().world;
            // Central Park South: gates from the 59th Street sidewalk onto the park drive and the paths.
            if(world.Find("Central Park South"))
            {
                float Drive(float x)=>CheckoutCityPark.DriveZ(x);
                Walk(new Vector3(-1.75f,0,-25.5f),new Vector3(-1.75f,0,Drive(-1.75f)),1.6f);
                Walk(new Vector3(15.5f,0,-25.5f),new Vector3(15.5f,0,Drive(15.5f)),1.6f);
                Walk(new Vector3(-19.5f,0,-26.5f),new Vector3(-15f,0,-30.5f),1.6f);
                for(float x=-16f;x<17f;x+=3f)Walk(new Vector3(x,0,Drive(x)),new Vector3(x+3,0,Drive(x+3)),1.8f);
                foreach(float x in new[]{-12f,-1.75f,9f})patrol.Add(new Vector3(x,.15f,Drive(x)));
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
                    if(Mathf.Abs(b.center.x)>25)
                    {
                        float side=Mathf.Sign(b.center.x);
                        door=new Vector3(b.center.x-side*(b.extents.x+.5f),.15f,b.center.z);curb=new Vector3(side*27.5f,.15f,door.z);
                    }
                    else if(b.center.z>20)
                    {
                        // Rear lots face north. East of the loading yard they join the east sidewalk; the rest
                        // share a rear path at z 26 to the west sidewalk, behind the other rear lots.
                        door=new Vector3(b.center.x,.15f,b.max.z+.5f);
                        curb=b.center.x>8?new Vector3(19.5f,.15f,door.z):new Vector3(-19.5f,.15f,26);
                    }
                    else
                    {
                        float side=Mathf.Sign(b.center.x);
                        door=new Vector3(b.center.x+side*(b.extents.x+.5f),.15f,b.center.z);curb=new Vector3(side*19.5f,.15f,door.z);
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
