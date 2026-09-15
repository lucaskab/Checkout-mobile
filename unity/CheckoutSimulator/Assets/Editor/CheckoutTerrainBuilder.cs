using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Tilemaps;
using UnityEngine.Rendering;
using MarketDay;

public static class CheckoutTerrainBuilder
{
    public const string AssetRoot = "Assets/Art/TerrainTiles/";
    public const string TerrainName = "Painted Terrain";

    [MenuItem("Supermarket/Apply painted terrain and expanded yard")]
    public static void Apply()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        ApplyToWorld(UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world);
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        AssetDatabase.SaveAssets();
        Capture();
        Debug.Log("CHECKOUT_TERRAIN_OK");
    }

    [MenuItem("Supermarket/Capture painted terrain preview")]
    public static void Capture() => MarketBuilder.Capture("ArtSource/TerrainTiles/MapPreview.png");

    public static void ApplyToWorld(Transform world)
    {
        var existingLayout = world.GetComponent<MarketOutdoorLayout>();
        if (existingLayout && existingLayout.cityVersion > 0)
        {
            CheckoutCityBuilder.ApplyToWorld(world);
            return;
        }
        var tiles = ConfigureTiles();
        var map = UnityEngine.Object.FindObjectsByType<Tilemap>().FirstOrDefault(t => t.name == TerrainName);
        if (!map)
        {
            var gridObject = new GameObject("Market Terrain Grid", typeof(Grid));
            gridObject.transform.position = new Vector3(0f, .13f, 0f);
            gridObject.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
            gridObject.GetComponent<Grid>().cellSize = new Vector3(4f, 4f, 1f);
            var terrain = new GameObject(TerrainName, typeof(Tilemap), typeof(TilemapRenderer));
            terrain.transform.SetParent(gridObject.transform, false);
            map = terrain.GetComponent<Tilemap>();
            for (int x = -8; x < 8; x++)
                for (int z = -6; z < 10; z++) map.SetTile(new Vector3Int(x, z, 0), tiles[0]);
            // A circulation road surrounds a generous, walkable central property.
            for (int x = -6; x <= 5; x++) { map.SetTile(new Vector3Int(x,-4,0),tiles[1]); map.SetTile(new Vector3Int(x,7,0),tiles[1]); }
            for (int z = -4; z <= 7; z++) { map.SetTile(new Vector3Int(-6,z,0),tiles[1]); map.SetTile(new Vector3Int(5,z,0),tiles[1]); }
            for (int z = -6; z < 10; z++) map.SetTile(new Vector3Int(-8,z,0),tiles[2]);
            for (int x = -8; x < 8; x++) map.SetTile(new Vector3Int(x,-6,0),tiles[2]);
            // Loading courtyard and access road, with no road markings under parked trucks.
            for (int x = -2; x <= 3; x++)
                for (int z = 2; z <= 6; z++) map.SetTile(new Vector3Int(x,z,0),tiles[3]);
            for (int z = -2; z < 2; z++) map.SetTile(new Vector3Int(2,z,0),tiles[3]);
            map.SetTile(new Vector3Int(4,4,0),tiles[1]);
            // The existing entrance ramp meets this short approach from the front road.
            map.SetTile(new Vector3Int(-1,-3,0),tiles[3]);
            map.SetTile(new Vector3Int(0,-3,0),tiles[3]);
        }
        var material = AssetDatabase.LoadAssetAtPath<Material>(AssetRoot + "PaintedTerrain.mat");
        if (!material) { material = new Material(Shader.Find("MarketDay/Painted Terrain Tiles")); AssetDatabase.CreateAsset(material,AssetRoot + "PaintedTerrain.mat"); }
        material.shader = Shader.Find("MarketDay/Painted Terrain Tiles");
        material.SetTexture("_GrassTex",AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot + "Grass.png"));
        material.SetTexture("_RoadTex",AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot + "Road.png"));
        material.SetTexture("_WaterTex",AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot + "Water.png"));
        EditorUtility.SetDirty(material);
        var renderer = map.GetComponent<TilemapRenderer>();
        renderer.sharedMaterial = material;
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        renderer.receiveShadows = true;
        map.RefreshAllTiles();
        KeepTrees(world.Find("Environment"));
        ExpandYard(world);
        CheckoutLoadingYardBuilder.Apply(world,map,tiles);
        CheckoutLandscapeModelsBuilder.Apply(world);
        CheckoutTerrainLevelBuilder.Apply(world, map, tiles);
        var camera = Camera.main;
        var focus = new Vector3(0f,.1f,6f);
        camera.orthographicSize = 20.5f;
        camera.transform.position = focus + new Vector3(28f,33f,-38f);
        camera.transform.LookAt(focus);
        Validate(world,map);
        if (AssetDatabase.LoadAssetAtPath<Texture2D>(CheckoutCityBuilder.AssetRoot + "CityTileset.png"))
            CheckoutCityBuilder.ApplyToWorld(world);
    }

    public static MarketTerrainTile[] ConfigureTiles()
    {
        var names = new[] { "Grass", "Road", "Water", "Courtyard", "Path", "Bridge" };
        var tiles = new MarketTerrainTile[names.Length];
        for (int i = 0; i < names.Length; i++)
        {
            string texturePath = AssetRoot + (i >= 3 ? "Road" : names[i]) + ".png";
            var importer = (TextureImporter)AssetImporter.GetAtPath(texturePath);
            importer.textureType = TextureImporterType.Sprite;
            importer.spriteImportMode = SpriteImportMode.Single;
            importer.GetSourceTextureWidthAndHeight(out int width,out int height);
            importer.spritePixelsPerUnit = width / 4f;
            importer.spritePivot = new Vector2(.5f,.5f);
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.mipmapEnabled = true;
            importer.maxTextureSize = 2048;
            importer.filterMode = FilterMode.Bilinear;
            var settings = new TextureImporterSettings();
            importer.ReadTextureSettings(settings);
            settings.spriteMeshType = SpriteMeshType.FullRect;
            importer.SetTextureSettings(settings);
            if (AssetDatabase.WriteImportSettingsIfDirty(texturePath)) AssetDatabase.ImportAsset(texturePath);
            string path = AssetRoot + names[i] + "Tile.asset";
            tiles[i] = AssetDatabase.LoadAssetAtPath<MarketTerrainTile>(path);
            if (!tiles[i]) { tiles[i] = ScriptableObject.CreateInstance<MarketTerrainTile>(); AssetDatabase.CreateAsset(tiles[i],path); }
            tiles[i].kind = (MarketTerrainKind)i;
            tiles[i].sprite = AssetDatabase.LoadAssetAtPath<Sprite>(texturePath);
            CheckoutTerrainRules.Configure(tiles[i]);
            EditorUtility.SetDirty(tiles[i]);
        }
        return tiles;
    }

    static void KeepTrees(Transform root)
    {
        const string path = "Assets/Art/Models/MarketWorld.fbx";
        var importer = (ModelImporter)AssetImporter.GetAtPath(path);
        bool readable = importer.isReadable;
        try
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(path).transform.Find("Environment").GetComponent<MeshFilter>().sharedMesh;
            var mesh = UnityEngine.Object.Instantiate(source);
            var vertices = mesh.vertices;
            var points = vertices.Select(root.TransformPoint).ToArray();
            var parents = Enumerable.Range(0,vertices.Length).ToArray();
            Func<int,int> find=null;
            find=i=>parents[i]==i?i:parents[i]=find(parents[i]);
            var triangles=mesh.triangles;
            for(int i=0;i<triangles.Length;i+=3) { parents[find(triangles[i+1])]=find(triangles[i]); parents[find(triangles[i+2])]=find(triangles[i]); }
            var keep=Enumerable.Range(0,points.Length).GroupBy(i=>find(i)).Where(g=>g.Max(i=>points[i].y)>.6f).Select(g=>g.Key).ToHashSet();
            for(int submesh=0;submesh<mesh.subMeshCount;submesh++)
            {
                triangles=mesh.GetTriangles(submesh);
                var kept=new System.Collections.Generic.List<int>();
                for(int i=0;i<triangles.Length;i+=3) if(keep.Contains(find(triangles[i]))) kept.AddRange(new[]{triangles[i],triangles[i+1],triangles[i+2]});
                mesh.SetTriangles(kept,submesh);
            }
            mesh.RecalculateBounds();
            string output=AssetRoot+"ExistingTrees.asset";
            var saved=AssetDatabase.LoadAssetAtPath<Mesh>(output);
            if(saved) { EditorUtility.CopySerialized(mesh,saved); UnityEngine.Object.DestroyImmediate(mesh); }
            else { AssetDatabase.CreateAsset(mesh,output); saved=mesh; }
            root.GetComponent<MeshFilter>().sharedMesh=saved;
        }
        finally { importer.isReadable=readable; importer.SaveAndReimport(); }
    }

    static void ExpandYard(Transform world)
    {
        var layout=world.GetComponent<MarketOutdoorLayout>();
        if(!layout) layout=world.gameObject.AddComponent<MarketOutdoorLayout>();
        world.Find("Warehouse").position+=Vector3.forward*(8f-layout.warehouseShift);
        foreach(Transform root in world)
            if(root.name=="Delivery" || root.name=="Worker_Delivery" || root.name.StartsWith("Anim_Truck"))
                root.position+=Vector3.forward*(6f-layout.deliveryShift);
        layout.warehouseShift=8f;
        layout.deliveryShift=6f;
        EditorUtility.SetDirty(layout);
    }

    static void Validate(Transform world,Tilemap map)
    {
        var material=map.GetComponent<TilemapRenderer>().sharedMaterial;
        for(int pass=0;pass<material.passCount;pass++) ShaderUtil.CompilePass(material,pass,true);
        var errors=ShaderUtil.GetShaderMessages(material.shader).Where(message=>message.severity==UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error).ToArray();
        if(errors.Length>0) throw new InvalidOperationException(string.Join("\n",errors.Select(message=>message.message)));
        var warehouse=world.Find("Warehouse/ReplacementVisual").GetComponentsInChildren<Renderer>();
        var bounds=warehouse[0].bounds;
        foreach(var renderer in warehouse) bounds.Encapsulate(renderer.bounds);
        float gap=bounds.min.z-7.4f;
        if(gap<9f) throw new InvalidOperationException("Warehouse clearance is still too small: "+gap);
        foreach(var kind in new[]{MarketTerrainKind.Grass,MarketTerrainKind.Road,MarketTerrainKind.River})
            if(!map.GetTilesBlock(map.cellBounds).OfType<MarketTerrainTile>().Any(tile=>tile.kind==kind)) throw new InvalidOperationException("Missing terrain type: "+kind);
        Debug.Log("CHECKOUT_TERRAIN_VALIDATION_OK size=64x64 warehouseGap="+gap.ToString("F2")+" paintedCells="+map.GetTilesBlock(map.cellBounds).Count(tile=>tile));
    }
}
