using UnityEngine;
using UnityEngine.AI;
using System.Collections.Generic;

namespace Checkout
{
    public class CheckoutCityStreets : MonoBehaviour
    {
        public Bounds[] sidewalks;
        public Vector3[] entrances;
        public void AddNavigation(List<NavMeshBuildSource> sources)
        {
            foreach(var bounds in sidewalks)
                sources.Add(new NavMeshBuildSource{shape=NavMeshBuildSourceShape.Box,transform=Matrix4x4.TRS(bounds.center,Quaternion.identity,Vector3.one),size=bounds.size,area=0});
        }
    }
}
