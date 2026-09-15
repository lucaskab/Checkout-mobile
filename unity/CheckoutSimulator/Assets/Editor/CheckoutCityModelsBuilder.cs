using System;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CheckoutCityModelsBuilder
{
    const string RootName="Supplied City Models";
    [MenuItem("Supermarket/Apply supplied city buildings and traffic")]
    public static void Apply()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play Mode before editing the city.");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        CheckoutCityBuilder.RebuildDetails(world);
        ApplyToWorld(world);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
        AssetDatabase.SaveAssets();
        MarketBuilder.Capture("ArtSource/TerrainTiles/CityModelsPreview.png");
    }
    public static void ApplyToWorld(Transform world)
    {
        if(world.Find(RootName))return;
        var root=new GameObject(RootName).transform;
        root.SetParent(world,false);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Add supplied city models");
        Place(root,"CuteHouse","Corner house",new Vector3(-31,.13f,-2),new Vector3(8,7,9),90);
        Place(root,"StylizedBuilding","West apartment building",new Vector3(-31,.13f,13),new Vector3(8,9,8),90);
        Place(root,"StylizedHouse","North townhouse",new Vector3(-15,.13f,39),new Vector3(8,7.8f,8),180);
        Place(root,"StylizedBuilding","North apartments",new Vector3(-4,.13f,39),new Vector3(9,9.5f,8),180);
        Place(root,"CuteHouse","Garden house",new Vector3(9,.13f,39),new Vector3(8,7,8),180);
        Place(root,"StylizedHouse","East townhouse",new Vector3(32,.13f,16),new Vector3(9,8,10),270);
        var traffic=root.gameObject.AddComponent<CheckoutCityTraffic>();
        traffic.vehicles=new Transform[3];
        var models=new[]{"CartoonCar","StylizedCar","ToyVan"};
        for(int i=0;i<models.Length;i++)
        {
            var vehicle=new GameObject(models[i]+" customer vehicle").transform;
            vehicle.SetParent(root,false);
            // Vehicle root forward is its driving direction. Keep all source model corrections on its visual child.
            Place(vehicle,models[i],"Visual",Vector3.zero,new Vector3(2.1f,2.5f,4.2f),0);
            vehicle.SetPositionAndRotation(new Vector3(-16.1f,.15f,CheckoutCityTraffic.BayZ(i)),Quaternion.LookRotation(Vector3.left));
            traffic.vehicles[i]=vehicle;
        }
    }
    static Transform Place(Transform root,string model,string name,Vector3 position,Vector3 maximum,float yaw)
    {
        var visual=CheckoutMapModelsBuilder.Create(root,model,name,yaw);
        Bounds Measure(){var renderers=visual.GetComponentsInChildren<Renderer>();var bounds=renderers[0].bounds;foreach(var r in renderers)bounds.Encapsulate(r.bounds);return bounds;}
        var bounds=Measure();
        visual.localScale*=Mathf.Min(maximum.x/bounds.size.x,maximum.y/bounds.size.y,maximum.z/bounds.size.z);
        bounds=Measure();visual.position+=new Vector3(position.x-bounds.center.x,position.y-bounds.min.y,position.z-bounds.center.z);
        return visual;
    }
}
