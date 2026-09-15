using System;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;
using Checkout;

public static class CheckoutCityDetailFixes
{
    const string Folder="Assets/Art/CityTiles/";
    [MenuItem("Supermarket/Fix entrance and city details")]
    public static void Apply()
    {
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("City Detail Repairs"))return;
        var repairs=new GameObject("City Detail Repairs").transform;repairs.SetParent(world,false);repairs.SetPositionAndRotation(Vector3.zero,Quaternion.identity);Undo.RegisterCreatedObjectUndo(repairs.gameObject,"Fix city details");
        foreach(var t in world.GetComponentsInChildren<Transform>(true))if(t && t.name=="Bench")Undo.DestroyObjectImmediate(t.gameObject);
        var yard=world.Find("Loading Yard Details");
        Cut(yard.Find("YardPaint").GetComponent<MeshFilter>(),p=>p.y<.3f&&p.z>12.9f&&p.z<14.1f&&p.x>4.3f&&p.x<13.6f,"YardWithoutCrossing");
        Cut(yard.Find("YardCharcoal").GetComponent<MeshFilter>(),p=>p.y<.7f&&p.x>-.4f&&p.x<1.6f&&p.z>13.4f&&p.z<14.1f,"YardWithoutBenchLegs");
        foreach(Transform item in world)if(item.name.StartsWith("Stock_bakery_"))foreach(var renderer in item.GetComponentsInChildren<Renderer>(true)){Undo.RecordObject(renderer,"Remove floating legacy bread");renderer.enabled=false;}
        var fish=world.Find("Sector_peixaria");
        if(!fish)
        {
            fish=new GameObject("Sector_peixaria").transform;fish.SetParent(world,false);fish.SetPositionAndRotation(Vector3.zero,Quaternion.identity);Undo.RegisterCreatedObjectUndo(fish.gameObject,"Restore seafood department");
            var visual=CheckoutMapModelsBuilder.Create(fish,"SeafoodCounter","ReplacementVisual",180);
            var b=BoundsOf(visual);visual.localScale*=3.85f/b.size.x;b=BoundsOf(visual);visual.position+=new Vector3(1.5f-b.center.x,.74f-b.min.y,3.35f-b.min.z);
        }
        var fishBounds=BoundsOf(fish);
        var fishWorker=world.Find("Worker_Fishmonger");Undo.RecordObject(fishWorker,"Align seafood employee");fishWorker.SetPositionAndRotation(new Vector3(fishBounds.center.x,.74f,fishBounds.center.z+fishBounds.size.z*.12f),Quaternion.identity);
        var cheese=world.Find("Sector_queijaria/ReplacementVisual");var cb=BoundsOf(cheese);
        Undo.RecordObject(cheese,"Ground cheese counter");cheese.position+=Vector3.up*(.74f-cb.min.y);cb=BoundsOf(cheese);
        var worker=world.Find("Worker_Cheesemaker");if(!worker){worker=UnityEngine.Object.Instantiate(world.Find("Worker_Baker"),world);worker.name="Worker_Cheesemaker";Undo.RegisterCreatedObjectUndo(worker.gameObject,"Place cheese employee");}
        Undo.RecordObject(worker,"Align cheese employee");worker.SetPositionAndRotation(new Vector3(cb.center.x,.74f,cb.center.z+cb.size.z*.12f),Quaternion.identity);
        Cut(world.Find("Building").GetComponent<MeshFilter>(),p=>p.x> -3.7f&&p.x<.25f&&p.z< -7.3f&&p.y<.8f,"BuildingWithoutDamagedRamp");
        var paving=Material("EntranceConcrete",new Color(.66f,.68f,.65f));
        var ramp=new Mesh{name="Continuous entrance approach"};
        ramp.vertices=new[]{new Vector3(-3.15f,.15f,-10.6f),new Vector3(-.35f,.15f,-10.6f),new Vector3(-3.15f,.74f,-7.05f),new Vector3(-.35f,.74f,-7.05f),new Vector3(-3.15f,.1f,-10.6f),new Vector3(-.35f,.1f,-10.6f),new Vector3(-3.15f,.1f,-7.05f),new Vector3(-.35f,.1f,-7.05f)};
        ramp.triangles=new[]{0,2,1,1,2,3,0,4,2,2,4,6,1,3,5,3,7,5,0,1,4,1,5,4};ramp.RecalculateNormals();ramp.RecalculateBounds();AssetDatabase.CreateAsset(ramp,Folder+"EntranceApproach.asset");
        var approach=new GameObject("Continuous entrance approach",typeof(MeshFilter),typeof(MeshRenderer));approach.transform.SetParent(repairs,false);approach.GetComponent<MeshFilter>().sharedMesh=ramp;approach.GetComponent<Renderer>().sharedMaterial=paving;
        var landscape=world.Find("Landscape Models");var targets=new[]{new Vector2(-32,-9),new Vector2(-32,23),new Vector2(-17,22.5f),new Vector2(16,10.5f),new Vector2(15.8f,-8.5f),new Vector2(16.6f,23),new Vector2(-20,38),new Vector2(17,38),new Vector2(31,-8)};
        foreach(string name in new[]{"CityStone","CitySoil"}){var r=world.Find("City Block/"+name).GetComponent<Renderer>();Undo.RecordObject(r,"Replace obstructing tree beds");r.enabled=false;}
        var soil=Material("RelocatedTreeSoil",new Color(.25f,.22f,.17f));
        for(int i=0;i<targets.Length;i++)
        {
            var tree=landscape.Find("Tree "+(i+1));if(!tree)continue;var b=BoundsOf(tree);var p=targets[i];Undo.RecordObject(tree,"Clear doors and sidewalks");tree.position+=new Vector3(p.x-b.center.x,0,p.y-b.center.z);
            Box(repairs,"Relocated tree bed "+i,new Vector3(p.x,.16f,p.y),new Vector3(2.2f,.06f,2.2f),paving);Box(repairs,"Relocated tree soil "+i,new Vector3(p.x,.2f,p.y),new Vector3(1.95f,.025f,1.95f),soil);
        }
        foreach(var person in world.GetComponentsInChildren<CheckoutCityPedestrian>(true))CheckoutShoppingProps.SetVisible(person.transform,false);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();MarketBuilder.Capture("ArtSource/TerrainTiles/CityDetailsFixed.png");
    }
    static Bounds BoundsOf(Transform root){var rs=root.GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;}
    static Material Material(string name,Color color){var m=new Material(Shader.Find("Standard")){color=color};m.SetFloat("_Glossiness",.08f);AssetDatabase.CreateAsset(m,Folder+name+".mat");return m;}
    static void Box(Transform root,string name,Vector3 p,Vector3 size,Material material){var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=name;o.transform.SetParent(root,false);o.transform.position=p;o.transform.localScale=size;o.GetComponent<Renderer>().sharedMaterial=material;UnityEngine.Object.DestroyImmediate(o.GetComponent<Collider>());}
    static void Cut(MeshFilter filter,Func<Vector3,bool> remove,string name)
    {
        var mesh=UnityEngine.Object.Instantiate(filter.sharedMesh);var vertices=mesh.vertices;
        for(int sub=0;sub<mesh.subMeshCount;sub++){var triangles=mesh.GetTriangles(sub);var keep=new List<int>();for(int i=0;i<triangles.Length;i+=3){var p=filter.transform.TransformPoint((vertices[triangles[i]]+vertices[triangles[i+1]]+vertices[triangles[i+2]])/3);if(!remove(p))keep.AddRange(new[]{triangles[i],triangles[i+1],triangles[i+2]});}mesh.SetTriangles(keep,sub);}
        mesh.RecalculateBounds();AssetDatabase.CreateAsset(mesh,Folder+name+".asset");Undo.RecordObject(filter,"Remove damaged detail");filter.sharedMesh=mesh;
    }
}
