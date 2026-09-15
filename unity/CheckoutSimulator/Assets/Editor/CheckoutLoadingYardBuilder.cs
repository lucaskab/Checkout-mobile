using System;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

public static class CheckoutLoadingYardBuilder
{
    const string AssetRoot = CheckoutTerrainBuilder.AssetRoot;

    public static void Apply(Transform world, Tilemap map, MarketTerrainTile[] tiles)
    {
        var layout = world.GetComponent<MarketOutdoorLayout>();
        foreach (Transform actor in world)
            if (actor.name == "Delivery" || actor.name == "Worker_Delivery" || actor.name.StartsWith("Anim_Truck"))
                actor.position += Vector3.right * (1.5f - layout.deliverySideShift);
        layout.deliverySideShift = 1.5f;
        if (layout.yardVersion < 1)
        {
            // Replace the empty forecourt with a garden, keeping the service corridor open.
            for (int x = -2; x <= 0; x++)
                for (int z = 2; z <= 3; z++)
                    if (map.GetTile<MarketTerrainTile>(new Vector3Int(x,z,0))?.kind == MarketTerrainKind.Courtyard)
                        map.SetTile(new Vector3Int(x,z,0),tiles[0]);
            map.SetTile(new Vector3Int(1,2,0),tiles[0]);
            map.SetTile(new Vector3Int(3,2,0),tiles[0]);
            layout.yardVersion = 1;
        }
        EditorUtility.SetDirty(layout);
        KeepDeliveryCargo(world.Find("Delivery"));
        var old = world.Find("Loading Yard Details");
        if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var root = new GameObject("Loading Yard Details").transform;
        root.SetParent(world,false);
        root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        root.localScale = Vector3.one;
        var paint = Material("YardPaint","F5E6B9");
        var yellow = Material("YardSafetyYellow","E9B93F");
        var curb = Material("YardCurb","BCB9A6");
        var paving = Material("YardPavers","CABFA4",true);
        var joint = Material("YardPaverJoint","8B826E");
        var charcoal = Material("YardCharcoal","354949");
        var soil = Material("YardSoil","70513B");
        var clay = Material("YardPlanter","B97D50");
        var leaf = Material("YardLeaves","779F3E");
        var lightLeaf = Material("YardLightLeaves","95B84D");
        var wood = Material("YardWood","AD7942");
        var lamp = Material("YardLamp","F5DE9C");

        var trucks = world.Cast<Transform>().Where(t=>t.name.StartsWith("Anim_Truck")).OrderBy(t=>BoundsOf(t.Find("ReplacementVisual")).center.x).ToArray();
        foreach (var truck in trucks)
        {
            var bounds = BoundsOf(truck.Find("ReplacementVisual"));
            float x = bounds.center.x;
            const float front = 15.9f, back = 23.1f, halfWidth = 1.42f;
            if (bounds.min.x < x-halfWidth+.15f || bounds.max.x > x+halfWidth-.15f || bounds.min.z < front || bounds.max.z > back)
                throw new InvalidOperationException("Truck does not fit its parking bay: "+truck.name+" "+bounds);
            Box(root,"Bay left",new Vector3(x-halfWidth,.16f,(front+back)/2),new Vector3(.10f,.015f,back-front),paint);
            Box(root,"Bay right",new Vector3(x+halfWidth,.16f,(front+back)/2),new Vector3(.10f,.015f,back-front),paint);
            Box(root,"Bay front",new Vector3(x,.16f,front),new Vector3(halfWidth*2,.015f,.10f),paint);
            Box(root,"Wheel stop",new Vector3(x,.22f,front+.45f),new Vector3(1.65f,.17f,.22f),charcoal);
            for (int stripe=0;stripe<3;stripe++)
                Box(root,"Reflector",new Vector3(x-.6f+stripe*.6f,.31f,front+.45f),new Vector3(.28f,.015f,.22f),yellow);
            Number(root,Array.IndexOf(trucks,truck)+1,new Vector3(x,.18f,front-.65f),paint.color);
            Debug.Log("CHECKOUT_TRUCK_BAY_OK "+truck.name+" center="+x.ToString("F2")+" bounds="+bounds);
        }

        // Paved footway links the rear service door to the warehouse loading porch.
        Box(root,"Service footway",new Vector3(4f,.125f,12.8f),new Vector3(1.7f,.05f,8.4f),paving);
        Box(root,"Warehouse porch",new Vector3(-.8f,.125f,16.3f),new Vector3(10f,.05f,1.35f),paving);
        for (float z=9f;z<16.5f;z+=1.2f)
            Box(root,"Footway joint",new Vector3(4f,.157f,z),new Vector3(1.7f,.008f,.025f),joint);
        for (float x=-5.5f;x<3f;x+=1.2f)
            Box(root,"Porch joint",new Vector3(x,.157f,16.3f),new Vector3(.025f,.008f,1.35f),joint);
        Box(root,"Footway curb",new Vector3(3.05f,.22f,12.1f),new Vector3(.14f,.18f,7f),curb);
        Box(root,"Garden curb",new Vector3(-1.5f,.22f,15.5f),new Vector3(9.2f,.18f,.14f),curb);
        Box(root,"West lot curb",new Vector3(-8f,.22f,21.9f),new Vector3(.18f,.18f,12f),curb);
        Box(root,"East lot curb",new Vector3(16f,.22f,24.9f),new Vector3(.18f,.18f,6f),curb);


        // A marked loading strip remains clear beside the warehouse.
        for (float z=18.4f;z<23.5f;z+=.72f)
        {
            var hatch=Box(root,"Loading hatch",new Vector3(3.6f,.163f,z),new Vector3(1.25f,.015f,.10f),yellow);
            hatch.transform.rotation=Quaternion.Euler(0,-30f,0);
        }
        foreach (float z in new[]{17.45f,23.7f})
        {
            Box(root,"Loading bollard",new Vector3(2.65f,.6f,z),new Vector3(.16f,.9f,.16f),charcoal);
            Box(root,"Bollard reflector",new Vector3(2.65f,.85f,z),new Vector3(.18f,.16f,.18f),yellow);
        }
        // Delivery access is marked by the pedestrian crossing, without directional arrows.

        // Break up the old concrete expanse with a planted rest area.
        Box(root,"Planting bed",new Vector3(-3.3f,.25f,11.7f),new Vector3(7.4f,.24f,2.5f),clay);
        Box(root,"Planting soil",new Vector3(-3.3f,.38f,11.7f),new Vector3(7.15f,.035f,2.25f),soil);
        for(int i=0;i<5;i++)
        {
            float x=-6.1f+i*1.4f;
            Box(root,"Shrub",new Vector3(x,.79f,11.7f),new Vector3(1.2f,.95f,1.2f),i%2==0?leaf:lightLeaf,PrimitiveType.Sphere);
            Box(root,"Shrub crown",new Vector3(x+.3f,1.05f,11.9f),new Vector3(.72f,.65f,.8f),lightLeaf,PrimitiveType.Sphere);
        }
        foreach(var position in new[]{new Vector3(-6.9f,0,15.2f),new Vector3(15.1f,0,14.6f)})
        {
            Box(root,"Yard lamp post",position+Vector3.up*1.8f,new Vector3(.12f,3.4f,.12f),charcoal);
            Box(root,"Lamp arm",position+new Vector3(-.3f,3.45f,0),new Vector3(.75f,.10f,.12f),charcoal);
            Box(root,"Lamp shade",position+new Vector3(-.6f,3.36f,0),new Vector3(.55f,.12f,.4f),charcoal);
            Box(root,"Lamp lens",position+new Vector3(-.6f,3.28f,0),new Vector3(.44f,.04f,.32f),lamp);
        }
        Batch(root);
        map.RefreshAllTiles();
        Debug.Log("CHECKOUT_LOADING_YARD_OK bays=3 serviceWalkway=clear");
    }

    static Bounds BoundsOf(Transform root)
    {
        var renderers=root.GetComponentsInChildren<Renderer>();
        var bounds=renderers[0].bounds;
        foreach(var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }

    static Material Material(string name,string hex,bool textured=false)
    {
        string path=AssetRoot+name+".mat";
        var material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if(!material) { material=new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material,path); }
        material.color=MarketSimulation.C(hex);
        material.SetFloat("_Glossiness",.05f);
        if(textured) { material.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot+"Road.png"); material.color*=2.4f; }
        EditorUtility.SetDirty(material);
        return material;
    }

    static GameObject Box(Transform root,string name,Vector3 position,Vector3 size,Material material,PrimitiveType shape=PrimitiveType.Cube)
    {
        var item=GameObject.CreatePrimitive(shape);
        item.name=name;
        item.transform.SetParent(root,false);
        item.transform.position=position;
        item.transform.localScale=size;
        item.GetComponent<Renderer>().sharedMaterial=material;
        UnityEngine.Object.DestroyImmediate(item.GetComponent<Collider>());
        return item;
    }

    static void Number(Transform root,int number,Vector3 position,Color color)
    {
        var item=new GameObject("Parking bay "+number,typeof(TextMesh));
        item.transform.SetParent(root,false);
        item.transform.SetPositionAndRotation(position,Quaternion.Euler(90f,0f,0f));
        var text=item.GetComponent<TextMesh>();
        text.text=number.ToString("00");text.fontSize=64;text.characterSize=.085f;text.anchor=TextAnchor.MiddleCenter;text.color=color;
        text.font=Resources.Load<Font>("MarketRegular")??Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        item.GetComponent<Renderer>().sharedMaterial=text.font.material;
    }

    static void Arrow(Transform root,Vector3 position,float yaw,Material material)
    {
        var rotation=Quaternion.Euler(0,yaw,0);
        var shaft=Box(root,"Traffic arrow",position,new Vector3(.16f,.015f,1.3f),material);
        shaft.transform.rotation=rotation;
        foreach(int side in new[]{-1,1})
        {
            var head=Box(root,"Arrow head",position+rotation*new Vector3(side*.24f,0,.48f),new Vector3(.12f,.015f,.72f),material);
            head.transform.rotation=Quaternion.Euler(0,yaw-side*45f,0);
        }
    }

    static void KeepDeliveryCargo(Transform root)
    {
        const string sourcePath="Assets/Art/Models/MarketWorld.fbx";
        var importer=(ModelImporter)AssetImporter.GetAtPath(sourcePath);
        bool readable=importer.isReadable;
        try
        {
            importer.isReadable=true;importer.SaveAndReimport();
            var source=AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath).transform.Find("Delivery").GetComponent<MeshFilter>().sharedMesh;
            var mesh=UnityEngine.Object.Instantiate(source);
            var vertices=mesh.vertices;
            for(int submesh=0;submesh<mesh.subMeshCount;submesh++)
            {
                var indices=mesh.GetTriangles(submesh);
                var kept=new System.Collections.Generic.List<int>();
                for(int i=0;i<indices.Length;i+=3)
                    if(Mathf.Max(root.TransformPoint(vertices[indices[i]]).y,root.TransformPoint(vertices[indices[i+1]]).y,root.TransformPoint(vertices[indices[i+2]]).y)>.35f)
                        kept.AddRange(new[]{indices[i],indices[i+1],indices[i+2]});
                mesh.SetTriangles(kept,submesh);
            }
            root.GetComponent<MeshFilter>().sharedMesh=SaveMesh(mesh,"DeliveryCargo");
        }
        finally { importer.isReadable=readable;importer.SaveAndReimport(); }
    }

    static Mesh SaveMesh(Mesh mesh,string name)
    {
        mesh.name=name;
        string path=AssetRoot+name+".asset";
        var saved=AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if(saved) { EditorUtility.CopySerialized(mesh,saved);UnityEngine.Object.DestroyImmediate(mesh); }
        else { AssetDatabase.CreateAsset(mesh,path);saved=mesh; }
        return saved;
    }

    static void Batch(Transform root)
    {
        var parts=root.GetComponentsInChildren<MeshFilter>().Where(part=>part.sharedMesh).ToArray();
        foreach(var group in parts.GroupBy(part=>part.GetComponent<Renderer>().sharedMaterial))
        {
            var mesh=new Mesh();
            mesh.CombineMeshes(group.Select(part=>new CombineInstance{mesh=part.sharedMesh,transform=root.worldToLocalMatrix*part.transform.localToWorldMatrix}).ToArray());
            var item=new GameObject(group.Key.name,typeof(MeshFilter),typeof(MeshRenderer));
            item.transform.SetParent(root,false);
            item.GetComponent<MeshFilter>().sharedMesh=SaveMesh(mesh,group.Key.name+"Geometry");
            item.GetComponent<Renderer>().sharedMaterial=group.Key;
        }
        foreach(var part in parts) UnityEngine.Object.DestroyImmediate(part.gameObject);
    }
}
