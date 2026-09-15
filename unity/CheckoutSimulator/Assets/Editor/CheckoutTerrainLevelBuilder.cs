using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Tilemaps;

public static class CheckoutTerrainLevelBuilder
{
    const string DetailsName = "Riverbank Details";

    [MenuItem("Supermarket/Improve terrain with RuleTiles")]
    public static void Improve()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play mode before editing terrain.");
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        var map = UnityEngine.Object.FindObjectsByType<Tilemap>().FirstOrDefault(t => t.name == CheckoutTerrainBuilder.TerrainName);
        if (!simulation || !map) throw new InvalidOperationException("Open the supermarket scene with painted terrain first.");
        var tiles = CheckoutTerrainBuilder.ConfigureTiles();
        Apply(simulation.world, map, tiles);
        EditorSceneManager.MarkSceneDirty(map.gameObject.scene);
        EditorSceneManager.SaveScene(map.gameObject.scene);
        AssetDatabase.SaveAssets();
        SceneView.RepaintAll();
    }

    public static void Apply(Transform world, Tilemap map, MarketTerrainTile[] tiles)
    {
        var layout = world.GetComponent<MarketOutdoorLayout>();
        if (!layout) layout = Undo.AddComponent<MarketOutdoorLayout>(world.gameObject);
        if (layout.terrainVersion < 1)
        {
            Undo.RegisterCompleteObjectUndo(map, "Improve supermarket terrain");
            Undo.RecordObject(layout, "Improve supermarket terrain");
            PaintLayout(map, tiles);
            AddDetails(world);
            layout.terrainVersion = 1;
            EditorUtility.SetDirty(layout);
        }
        map.RefreshAllTiles();
    }

    static void PaintLayout(Tilemap map, MarketTerrainTile[] tiles)
    {
        void Paint(int x, int y, MarketTerrainKind kind) => map.SetTile(new Vector3Int(x,y,0), tiles[(int)kind]);
        for (int x = -10; x <= 9; x++)
            for (int y = -9; y <= 11; y++)
            {
                var cell = new Vector3Int(x,y,0);
                var previous = map.GetTile<MarketTerrainTile>(cell);
                if (!previous || previous.kind == MarketTerrainKind.River) Paint(x,y,MarketTerrainKind.Grass);
            }

        // Two-cell-wide water merges into one surface. Varying banks and wider
        // pools replace the old constant-width channel without entering the lot.
        for (int y = -7; y <= 11; y++)
        {
            int west = y >= 5 && y <= 7 ? -10 : -9;
            for (int x = west; x <= -8; x++) Paint(x,y,MarketTerrainKind.River);
        }
        foreach (int y in new[] { 2,3,9,10 }) Paint(-7,y,MarketTerrainKind.River);
        for (int x = -10; x <= 9; x++)
        {
            Paint(x,-7,MarketTerrainKind.River);
            Paint(x,-6,MarketTerrainKind.River);
            if (x >= 3 && x <= 6) Paint(x,-8,MarketTerrainKind.River);
        }

        // Connect the circulation loop to the outside road across the river.
        Paint(-1,-5,MarketTerrainKind.Road);
        Paint(-1,-6,MarketTerrainKind.Bridge);
        Paint(-1,-7,MarketTerrainKind.Bridge);
        Paint(-1,-8,MarketTerrainKind.Road);
        Paint(-1,-9,MarketTerrainKind.Road);
        for (int x = 6; x <= 9; x++) Paint(x,4,MarketTerrainKind.Road);

        // A paved promenade reaches the entrance, farm frontage and service yard.
        for (int x = -5; x <= 3; x++) Paint(x,-3,MarketTerrainKind.Path);
        Paint(-1,-2,MarketTerrainKind.Path);
        for (int y = -2; y <= 2; y++) Paint(3,y,MarketTerrainKind.Path);
    }

    static void AddDetails(Transform world)
    {
        if (world.Find(DetailsName)) return;
        var root = new GameObject(DetailsName).transform;
        root.SetParent(world,false);
        root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject, "Add riverbank details");
        var wood = Material("BridgeWood","9D743E");
        var stone = Material("RiverStone","9B9F86");
        var reed = Material("RiverReed","778B3E");
        var reedHead = Material("RiverReedHead","75603D");
        var paint = AssetDatabase.LoadAssetAtPath<Material>(CheckoutTerrainBuilder.AssetRoot+"YardPaint.mat");

        // Bridge rails sit above the RuleTile deck; the water remains visible below.
        foreach (float x in new[] { -3.64f,-.36f })
        {
            for (float z = -27.8f; z <= -20.1f; z += 1.9f)
                Box(root,"Bridge post",new Vector3(x,.57f,z),new Vector3(.13f,.85f,.13f),wood);
            foreach (float height in new[] { .48f,.90f })
                Box(root,"Bridge rail",new Vector3(x,height,-24f),new Vector3(.12f,.11f,8.1f),wood);
        }
        // A pedestrian crossing aligns with the shop entrance and road access.
        if (paint)
            for (int stripe = 0; stripe < 6; stripe++)
                Box(root,"Entrance crossing",new Vector3(-2f,.151f,-15.30f+stripe*.52f),new Vector3(2.05f,.015f,.28f),paint);

        var points = new[]
        {
            new Vector2(-25.1f,17f),new Vector2(-25.0f,4.0f),new Vector2(-25.2f,-5.7f),
            new Vector2(-26.2f,-18.6f),new Vector2(-18.3f,-19.1f),new Vector2(-11.5f,-19.0f),
            new Vector2(6.4f,-19.0f),new Vector2(13.0f,-19.0f),new Vector2(20.4f,-19.0f),
            new Vector2(29.8f,-18.9f)
        };
        for (int i = 0; i < points.Length; i++)
        {
            var p = points[i];
            for (int j = 0; j < 3; j++)
            {
                float height=.38f+(i*3+j)%4*.12f;
                var position=new Vector3(p.x+j*.20f,.13f,p.y+(j%2)*.19f);
                Box(root,"River reed",position+Vector3.up*height*.5f,new Vector3(.045f,height,.045f),reed);
                Box(root,"Reed head",position+Vector3.up*(height+.05f),new Vector3(.095f,.18f,.095f),reedHead);
            }
            var rock=Box(root,"River stone",new Vector3(p.x+.65f,.23f,p.y+.3f),new Vector3(.62f,.26f,.46f),stone,PrimitiveType.Cube);
            rock.transform.rotation=Quaternion.Euler(9f,i*37f,6f);
        }
        Batch(root);
    }

    static Material Material(string name,string hex)
    {
        string path=CheckoutTerrainBuilder.AssetRoot+name+".mat";
        var material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material)
        {
            material=new Material(Shader.Find("Standard"));
            AssetDatabase.CreateAsset(material,path);
        }
        material.color=MarketSimulation.C(hex);
        material.SetFloat("_Glossiness",.05f);
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

    static void Batch(Transform root)
    {
        var parts=root.GetComponentsInChildren<MeshFilter>().Where(part=>part.sharedMesh).ToArray();
        foreach (var group in parts.GroupBy(part=>part.GetComponent<Renderer>().sharedMaterial))
        {
            var mesh=new Mesh { name="Riverbank"+group.Key.name+"Geometry" };
            mesh.CombineMeshes(group.Select(part=>new CombineInstance
            {
                mesh=part.sharedMesh,
                transform=root.worldToLocalMatrix*part.transform.localToWorldMatrix
            }).ToArray());
            string path=CheckoutTerrainBuilder.AssetRoot+mesh.name+".asset";
            var saved=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (saved) { EditorUtility.CopySerialized(mesh,saved);UnityEngine.Object.DestroyImmediate(mesh); }
            else { AssetDatabase.CreateAsset(mesh,path);saved=mesh; }
            var item=new GameObject(group.Key.name,typeof(MeshFilter),typeof(MeshRenderer));
            item.transform.SetParent(root,false);
            item.GetComponent<MeshFilter>().sharedMesh=saved;
            item.GetComponent<Renderer>().sharedMaterial=group.Key;
        }
        foreach (var part in parts) UnityEngine.Object.DestroyImmediate(part.gameObject);
    }
}
