using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Tilemaps;

public static class CheckoutCityStreetsBuilder
{
    [MenuItem("Supermarket/Upgrade streets and sidewalks")]
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode first.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("Connected City Sidewalks"))return;
        var root=new GameObject("Connected City Sidewalks").transform;root.SetParent(world,false);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Connect city sidewalks");
        var network=root.gameObject.AddComponent<CheckoutCityStreets>();
        var walks=new List<Bounds>();
        var material=new Material(Shader.Find("Standard")){color=new Color(.69f,.71f,.70f)};material.SetFloat("_Glossiness",.08f);
        var existingMaterial=AssetDatabase.LoadAssetAtPath<Material>(CheckoutCityBuilder.AssetRoot+"ConnectedSidewalk.mat");
        if(existingMaterial){UnityEngine.Object.DestroyImmediate(material);material=existingMaterial;}else AssetDatabase.CreateAsset(material,CheckoutCityBuilder.AssetRoot+"ConnectedSidewalk.mat");
        void Walk(float x,float z,float width,float length,bool visible=false)
        {
            walks.Add(new Bounds(new Vector3(x,.05f,z),new Vector3(width,.2f,length)));
            if(visible)Box(root,"Pedestrian connection",new Vector3(x,.13f,z),new Vector3(width,.04f,length),material);
        }
        foreach(float x in new[]{-27.5f,27.5f})Walk(x,8,2,55);
        foreach(float x in new[]{-19.5f,19.5f})Walk(x,7.25f,2,39.5f);
        foreach(float z in new[]{-19.5f,34f})Walk(0,z,57,2);
        foreach(float z in new[]{-11.5f,26f})Walk(0,z,41,2);
        Walk(-23.5f,-8.5f,8,2.5f);Walk(23.5f,0,8,2.5f);Walk(-4,30,2.5f,8);Walk(-1.75f,-15.5f,2.5f,8);
        Walk(-1.75f,-10.2f,2.8f,2);
        var models=world.Find("Supplied City Models");
        var entrances=new List<Vector3>();
        foreach(Transform building in models)
        {
            if(building.name.EndsWith("customer vehicle"))continue;
            var rs=building.GetComponentsInChildren<Renderer>();if(rs.Length==0)continue;
            var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
            Vector3 door;
            if(b.center.x< -25){door=new Vector3(b.max.x+.3f,.15f,b.center.z);Walk((door.x-27.5f)*.5f,door.z,Mathf.Abs(door.x+27.5f)+1,1.8f,true);}
            else if(b.center.x>25){door=new Vector3(b.min.x-.3f,.15f,b.center.z);Walk((door.x+27.5f)*.5f,door.z,Mathf.Abs(door.x-27.5f)+1,1.8f,true);}
            else {door=new Vector3(b.center.x,.15f,b.min.z-.3f);Walk(door.x,(door.z+34)*.5f,1.8f,Mathf.Abs(door.z-34)+1,true);}
            entrances.Add(door);
        }
        network.sidewalks=walks.ToArray();network.entrances=entrances.ToArray();
        var source=world.Find("Customer_01");
        for(int i=0;i<entrances.Count;i++)
        {
            var person=UnityEngine.Object.Instantiate(source.gameObject,root);person.name="City pedestrian "+(i+1);person.SetActive(true);
            foreach(var walker in person.GetComponents<CheckoutWalker>())UnityEngine.Object.DestroyImmediate(walker);
            var agent=person.GetComponent<NavMeshAgent>();if(!agent)agent=person.AddComponent<NavMeshAgent>();agent.radius=.3f;agent.height=2.3f;agent.speed=1.1f;agent.acceleration=4;agent.stoppingDistance=.2f;agent.updateRotation=false;agent.updatePosition=true;agent.avoidancePriority=60+i;
            person.transform.position=entrances[i];person.AddComponent<CheckoutCityPedestrian>().home=entrances[i];
        }
        var map=UnityEngine.Object.FindObjectsByType<Tilemap>().First(t=>t.name=="Painted Terrain");
        var pavement=map.GetComponent<TilemapRenderer>().sharedMaterial;Undo.RecordObject(pavement,"Widen city streets");pavement.SetFloat("_WideStreets",1);EditorUtility.SetDirty(pavement);
        var city=world.Find("City Block");
        var sign=city.Find("ESTACIONAMENTO");if(sign)Undo.DestroyObjectImmediate(sign.gameObject);
        // Edit only the portal, parking markings and poles embedded in the old combined meshes.
        foreach(var filter in city.GetComponentsInChildren<MeshFilter>())
        {
            var original=filter.sharedMesh;var mesh=UnityEngine.Object.Instantiate(original);var vertices=mesh.vertices;var kept=new List<int>();var indices=mesh.triangles;
            for(int i=0;i<indices.Length;i+=3)
            {
                var p=filter.transform.TransformPoint((vertices[indices[i]]+vertices[indices[i+1]]+vertices[indices[i+2]])/3);
                bool portal=p.x> -16.6f&&p.x< -11.4f&&p.z> -8.3f&&p.z< -7.7f&&p.y>.4f;
                bool parking=(filter.name=="CityPaint"||filter.name=="CityStone")&&p.x> -19&&p.x< -13&&p.z> -8&&p.z<17&&p.y<.4f;
                if(!portal&&!parking)kept.AddRange(new[]{indices[i],indices[i+1],indices[i+2]});
            }
            for(int i=0;i<vertices.Length;i++)
            {
                var p=filter.transform.TransformPoint(vertices[i]);
                if((filter.name=="CityMetal"||filter.name=="CityLamp"||filter.name=="CityStone"||filter.name=="CitySoil"))
                {
                    if(Mathf.Abs(p.x)>23&&Mathf.Abs(p.x)<26.6f)p.x+=Mathf.Sign(p.x)*3;
                    if(p.z>32.4f&&p.z<33.4f)p.z+=1.5f;
                }
                vertices[i]=filter.transform.InverseTransformPoint(p);
            }
            mesh.vertices=vertices;mesh.triangles=kept.ToArray();mesh.RecalculateBounds();
            string path=CheckoutCityBuilder.AssetRoot+filter.name+"ConnectedStreets.asset";AssetDatabase.CreateAsset(mesh,path);Undo.RecordObject(filter,"Remove parking portal");filter.sharedMesh=mesh;
        }
        var paint=new Material(Shader.Find("Standard")){color=new Color(.92f,.9f,.81f)};AssetDatabase.CreateAsset(paint,CheckoutCityBuilder.AssetRoot+"ParkingLayoutPaint.mat");
        for(int i=0;i<3;i++)
        {
            float z=CheckoutCityTraffic.BayZ(i);
            foreach(float offset in new[]{-2.1f,2.1f})Box(root,"Parking bay boundary",new Vector3(-16.3f,.16f,z+offset),new Vector3(5.3f,.03f,.1f),paint);
            Box(root,"Parking wheel stop",new Vector3(-18.4f,.23f,z),new Vector3(.22f,.18f,2.3f),material);
        }
        var traffic=models.GetComponent<CheckoutCityTraffic>();
        foreach(var car in traffic.vehicles)
        {
            var visual=car.Find("Visual");Undo.RecordObject(visual,"Correct vehicle front and size");
            visual.localRotation=Quaternion.AngleAxis(180,Vector3.up)*visual.localRotation;
            visual.localScale*=2.1f/1.3f;visual.localPosition*=2.1f/1.3f;
        }
        // Existing trees inside the widened roadway move to the outer sidewalk; other landscaping stays untouched.
        var landscape=world.Find("Landscape Models");
        if(landscape)foreach(Transform tree in landscape)
        {
            var renderers=tree.GetComponentsInChildren<Renderer>();if(renderers.Length==0)continue;var b=renderers[0].bounds;foreach(var r in renderers)b.Encapsulate(r.bounds);
            if(Mathf.Abs(b.center.x)>24&&Mathf.Abs(b.center.x)<26.6f){Undo.RecordObject(tree,"Clear widened roadway");tree.position+=Vector3.right*Mathf.Sign(b.center.x)*3;}
        }
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();
        MarketBuilder.Capture("ArtSource/TerrainTiles/ConnectedStreetsPreview.png");
    }
    static void Box(Transform parent,string name,Vector3 position,Vector3 size,Material material)
    {
        var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(parent,false);go.transform.position=position;go.transform.localScale=size;go.GetComponent<Renderer>().sharedMaterial=material;UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
    }
}
