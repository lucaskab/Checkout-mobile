using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

public static class CheckoutCityLifeBuilder
{
    [MenuItem("Supermarket/Populate city establishments")]
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode first.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("City Establishments"))throw new InvalidOperationException("City establishments already exist.");
        var root=new GameObject("City Establishments").transform;root.SetParent(world,false);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Populate city establishments");
        var streets=world.GetComponentInChildren<CheckoutCityStreets>();
        Undo.RecordObject(streets,"Extend city pedestrian destinations");
        var walks=new List<Bounds>(streets.sidewalks);
        var entrances=new List<Vector3>(streets.entrances);
        Vector3 Place(string model,Vector3 center,Vector3 size,float yaw)
        {
            var building=CheckoutMapModelsBuilder.Create(root,model,model,yaw);
            Bounds Measure(){var rs=building.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;}
            var bounds=Measure();building.localScale*=Mathf.Min(size.x/bounds.size.x,size.y/bounds.size.y,size.z/bounds.size.z);
            bounds=Measure();building.position+=new Vector3(center.x-bounds.center.x,.13f-bounds.min.y,center.z-bounds.center.z);
            bounds=Measure();
            var door=center.z>35?new Vector3(center.x,.15f,bounds.min.z-.4f):new Vector3(center.x>0?bounds.min.x-.4f:bounds.max.x+.4f,.15f,center.z);
            var sidewalk=center.z>35?new Vector3(door.x,.15f,34):new Vector3(Mathf.Sign(center.x)*27.5f,.15f,door.z);
            walks.Add(new Bounds((door+sidewalk)*.5f-Vector3.up*.1f,new Vector3(Mathf.Abs(door.x-sidewalk.x)+1.8f,.2f,Mathf.Abs(door.z-sidewalk.z)+1.8f)));
            entrances.Add(door);return door;
        }
        var hospital=Place("Hospital",new Vector3(32,0,-3),new Vector3(8,8,10),270);
        var pharmacy=Place("Pharmacy",new Vector3(-32,0,-12),new Vector3(7,6,7),90);
        var gym=Place("Gym",new Vector3(23,0,39),new Vector3(9,8,8),180);
        streets.sidewalks=walks.ToArray();streets.entrances=entrances.ToArray();
        var source=world.Find("Customer_01");
        NavMeshAgent Person(string name,Vector3 position)
        {
            var person=UnityEngine.Object.Instantiate(source.gameObject,root);person.name=name;
            foreach(var component in person.GetComponents<CheckoutWalker>())UnityEngine.Object.DestroyImmediate(component);
            var agent=person.GetComponent<NavMeshAgent>();if(!agent)agent=person.AddComponent<NavMeshAgent>();
            agent.radius=.28f;agent.height=2.3f;agent.speed=1.35f;agent.acceleration=4;agent.stoppingDistance=.2f;agent.updateRotation=false;agent.updatePosition=true;
            person.transform.position=position;CheckoutShoppingProps.SetVisible(person.transform,false);return agent;
        }
        foreach(var entrance in new[]{hospital,pharmacy,gym})
        {
            var person=Person("City resident",entrance);person.gameObject.SetActive(true);person.gameObject.AddComponent<CheckoutCityPedestrian>().home=entrance;
        }
        var traffic=root.gameObject.AddComponent<CheckoutNeighborhoodTraffic>();
        CheckoutNeighborhoodTraffic.Visit Stop(float x,float z,Vector3 door=default)
        {
            var sidewalk=Mathf.Abs(x)>24?new Vector3(Mathf.Sign(x)*27.5f,.15f,z):new Vector3(x,.15f,34);
            return new CheckoutNeighborhoodTraffic.Visit{road=new Vector3(x,.15f,z),sidewalk=sidewalk,entrance=door};
        }
        traffic.route=new[]{Stop(25,-17),Stop(25,-3,hospital),Stop(25,16,entrances[5]),Stop(25,31.5f),Stop(23,31.5f,gym),Stop(9,31.5f,entrances[4]),Stop(-15,31.5f,entrances[2]),Stop(-25,31.5f),Stop(-25,13,entrances[1]),Stop(-25,-2,entrances[0]),Stop(-25,-12,pharmacy),Stop(-25,-17)};
        var templates=world.GetComponentInChildren<CheckoutCityTraffic>().vehicles;
        traffic.cars=new CheckoutNeighborhoodTraffic.Car[3];
        for(int i=0;i<traffic.cars.Length;i++)
        {
            var vehicle=UnityEngine.Object.Instantiate(templates[i].gameObject,root).transform;vehicle.name="Neighborhood car "+(i+1);vehicle.gameObject.SetActive(true);
            var person=Person("City driver "+(i+1),Vector3.zero);person.gameObject.SetActive(false);
            traffic.cars[i]=new CheckoutNeighborhoodTraffic.Car{vehicle=vehicle,visitor=person};
        }
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
    }
}
