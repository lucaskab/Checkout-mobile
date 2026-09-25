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
            foreach(float x in new[]{-27.5f,-19.5f,19.5f,27.5f})
            {
                foreach(var span in new[]{new Vector2(min.z,-19.45f),new Vector2(-11.55f,26.05f),new Vector2(33.95f,max.z)})
                    Walk(new Vector3(x,0,span.x),new Vector3(x,0,span.y));
                patrol.Add(new Vector3(x,.15f,min.z+.5f));patrol.Add(new Vector3(x,.15f,max.z-.5f));
            }
            foreach(float z in new[]{-19.5f,-11.5f,26f,34f})
            {
                foreach(var span in new[]{new Vector2(min.x,-27.45f),new Vector2(-19.55f,19.55f),new Vector2(27.45f,max.x)})
                    Walk(new Vector3(span.x,0,z),new Vector3(span.y,0,z));
                patrol.Add(new Vector3(min.x+.5f,.15f,z));patrol.Add(new Vector3(max.x-.5f,.15f,z));
            }
            Walk(new Vector3(-27.5f,0,-8.5f),new Vector3(-19.5f,0,-8.5f),2.5f);
            Walk(new Vector3(19.5f,0,0),new Vector3(27.5f,0,0),2.5f);
            Walk(new Vector3(-4,0,26),new Vector3(-4,0,34),2.5f);
            Walk(new Vector3(-1.75f,0,-19.5f),new Vector3(-1.75f,0,-9.2f),2.5f);
            // Crossing strips are inset from each junction; the road itself is never walkable.
            foreach(float x in new[]{-23.5f,23.5f})foreach(float z in new[]{-21f,-10f,24.5f,35.5f})
            {
                Walk(new Vector3(x-4.2f,0,z),new Vector3(x+4.2f,0,z),1.6f);
                Walk(new Vector3(x-4.2f,0,z),new Vector3(x-4.2f,0,z<0?(z< -15?-19.5f:-11.5f):(z<30?26:34)),1.6f);
                Walk(new Vector3(x+4.2f,0,z),new Vector3(x+4.2f,0,z<0?(z< -15?-19.5f:-11.5f):(z<30?26:34)),1.6f);
            }
            foreach(float z in new[]{-15.5f,30f})foreach(float x in new[]{-29f,-18f,18f,29f})
            {
                Walk(new Vector3(x,0,z-4.2f),new Vector3(x,0,z+4.2f),1.6f);
                Walk(new Vector3(x,0,z-4.2f),new Vector3(x<0?(x< -23?-27.5f:-19.5f):(x>23?27.5f:19.5f),0,z-4.2f),1.6f);
                Walk(new Vector3(x,0,z+4.2f),new Vector3(x<0?(x< -23?-27.5f:-19.5f):(x>23?27.5f:19.5f),0,z+4.2f),1.6f);
            }
            var world=FindAnyObjectByType<MarketDay.MarketSimulation>().world;
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
                        bool north=b.center.z>30;
                        door=new Vector3(b.center.x,.15f,north?b.min.z-.5f:b.max.z+.5f);curb=new Vector3(door.x,.15f,north?34:26);
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
