using System;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Tilemaps;

public static class CheckoutCityBuilder
{
    public const string AssetRoot = "Assets/Art/CityTiles/";
    public static readonly string[] TileNames = { "Street", "Crosswalk", "Sidewalk", "Plaza", "Asphalt", "SidewalkEdge", "SidewalkCorner" };
    const string DetailsName = "City Block";

    [MenuItem("Supermarket/Apply city tileset")]
    public static void Apply()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode before editing the city.");
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation) throw new InvalidOperationException("Open the supermarket scene.");
        ApplyToWorld(simulation.world);
        EditorSceneManager.MarkSceneDirty(simulation.gameObject.scene);
        EditorSceneManager.SaveScene(simulation.gameObject.scene);
        AssetDatabase.SaveAssets();
        SceneView.RepaintAll();
        Debug.Log("CHECKOUT_CITY_OK");
    }

    [MenuItem("Supermarket/Capture city preview")]
    public static void Capture() => MarketBuilder.Capture("ArtSource/TerrainTiles/CityPreview.png");

    public static MarketCityTile[] ConfigureTiles()
    {
        var sprites = AssetDatabase.LoadAllAssetsAtPath(AssetRoot+"CityTileset.png").OfType<Sprite>().ToDictionary(sprite=>sprite.name);
        var tiles = new MarketCityTile[TileNames.Length];
        for (int i=0;i<tiles.Length;i++)
        {
            string path=AssetRoot+TileNames[i]+"Tile.asset";
            var tile=AssetDatabase.LoadAssetAtPath<MarketCityTile>(path);
            if (!tile) { tile=ScriptableObject.CreateInstance<MarketCityTile>();AssetDatabase.CreateAsset(tile,path); }
            tile.kind=(MarketCityKind)i;
            tile.m_DefaultColliderType=Tile.ColliderType.None;
            tile.m_DefaultSprite=sprites[i==0?"StreetStraight":i==1?"StreetCrosswalk":TileNames[i]];
            tile.m_TilingRules.Clear();
            if (tile.IsStreet)
            {
                var masks=new[]{15,14,12,5,1,0};
                var names=new[]{"StreetCross","StreetT","StreetCorner",i==1?"StreetCrosswalk":"StreetStraight","StreetStraight","StreetStraight"};
                for (int ruleIndex=0;ruleIndex<masks.Length;ruleIndex++)
                {
                    var rule=new RuleTile.TilingRule
                    {
                        m_Id=masks[ruleIndex],
                        m_Sprites=new[]{sprites[names[ruleIndex]]},
                        m_RuleTransform=RuleTile.TilingRuleOutput.Transform.Rotated,
                        m_ColliderType=Tile.ColliderType.None
                    };
                    rule.m_NeighborPositions.Clear();
                    for (int direction=0;direction<4;direction++)
                    {
                        rule.m_NeighborPositions.Add(MarketTerrainTile.Neighbors[direction]);
                        rule.m_Neighbors.Add((masks[ruleIndex]&(1<<direction))!=0?
                            RuleTile.TilingRuleOutput.Neighbor.This:RuleTile.TilingRuleOutput.Neighbor.NotThis);
                    }
                    tile.m_TilingRules.Add(rule);
                }
            }
            tile.UpdateNeighborPositions();
            EditorUtility.SetDirty(tile);tiles[i]=tile;
        }
        return tiles;
    }

    public static void ApplyToWorld(Transform world)
    {
        var map=UnityEngine.Object.FindObjectsByType<Tilemap>().FirstOrDefault(t=>t.name==CheckoutTerrainBuilder.TerrainName);
        if (!map) throw new InvalidOperationException("Create the supermarket terrain grid first.");
        var tiles=ConfigureTiles();
        var layout=world.GetComponent<MarketOutdoorLayout>()??Undo.AddComponent<MarketOutdoorLayout>(world.gameObject);
        if (layout.cityVersion<1)
        {
            Undo.RegisterCompleteObjectUndo(map,"Build city block");
            Undo.RecordObject(layout,"Build city block");
            Paint(map,tiles);
            foreach (Transform item in world)
                if (item.name=="Farm" || item.name=="Anim_Cow" || item.name=="Anim_Tractor" ||
                    item.name.StartsWith("Anim_Chicken") || item.name=="Environment" || item.name=="Riverbank Details")
                {
                    Undo.RecordObject(item.gameObject,"Replace rural scenery");
                    item.gameObject.SetActive(false);
                }
            AddCityDetails(world);
            layout.cityVersion=1;
            EditorUtility.SetDirty(layout);
        }
        var material=AssetDatabase.LoadAssetAtPath<Material>(AssetRoot+"CityTiles.mat");
        if (!material)
        {
            material=new Material(Shader.Find("MarketDay/City Tiles"));
            AssetDatabase.CreateAsset(material,AssetRoot+"CityTiles.mat");
        }
        material.shader=Shader.Find("MarketDay/City Tiles");
        material.SetColor("_Color",new Color(.72f,.75f,.78f,1));
        EditorUtility.SetDirty(material);
        var renderer=map.GetComponent<TilemapRenderer>();
        Undo.RecordObject(renderer,"Use supplied city tiles");
        renderer.sharedMaterial=material;renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=true;
        map.RefreshAllTiles();
        if (AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Models/MapModels/CuteHouse/CuteHouse.fbx"))
            CheckoutCityModelsBuilder.ApplyToWorld(world);
    }

    static void Paint(Tilemap map,MarketCityTile[] tiles)
    {
        void Set(int x,int y,MarketCityKind kind)=>map.SetTile(new Vector3Int(x,y,0),tiles[(int)kind]);
        map.ClearAllTiles();
        for (int x=-10;x<=9;x++)
            for (int y=-9;y<=11;y++) Set(x,y,MarketCityKind.Sidewalk);
        // Streets continue through neighboring blocks instead of forming an isolated farm loop.
        for (int x=-10;x<=9;x++) { Set(x,-4,MarketCityKind.Street);Set(x,7,MarketCityKind.Street); }
        for (int y=-9;y<=11;y++) { Set(-6,y,MarketCityKind.Street);Set(5,y,MarketCityKind.Street); }
        for (int x=-5;x<=-3;x++)
            for (int y=-2;y<=4;y++) Set(x,y,MarketCityKind.Asphalt);
        Set(-4,-3,MarketCityKind.Street);
        // Retain the real loading yard and its vehicle clearance.
        for (int x=-2;x<=3;x++)
            for (int y=4;y<=6;y++) Set(x,y,MarketCityKind.Asphalt);
        for (int y=-2;y<=3;y++) Set(2,y,MarketCityKind.Asphalt);
        Set(1,3,MarketCityKind.Asphalt);Set(3,3,MarketCityKind.Asphalt);
        Set(4,4,MarketCityKind.Street);
        Set(-1,-4,MarketCityKind.Crosswalk);Set(-6,0,MarketCityKind.Crosswalk);Set(5,1,MarketCityKind.Crosswalk);
        Set(-1,7,MarketCityKind.Crosswalk);
        Set(-3,5,MarketCityKind.Plaza);Set(-4,5,MarketCityKind.Plaza);
        Set(3,0,MarketCityKind.Plaza);Set(3,-3,MarketCityKind.Plaza);
        // Edge pieces from the supplied sheet border the pedestrian pocket square.

    }

    public static void RebuildDetails(Transform world)
    {
        var old=world.Find(DetailsName);
        if(old) Undo.DestroyObjectImmediate(old.gameObject);
        AddCityDetails(world);
    }

    static void AddCityDetails(Transform world)
    {
        if (world.Find(DetailsName)) return;
        var root=new GameObject(DetailsName).transform;
        root.SetParent(world,false);root.SetPositionAndRotation(Vector3.zero,Quaternion.identity);
        Undo.RegisterCreatedObjectUndo(root.gameObject,"Add city details");
        Material stone=Material("Stone","AAA99D"),dark=Material("Metal","354348"),glass=Material("Glass","43626B");
        Material white=Material("Paint","E5DED0"),wood=Material("Wood","A38356"),soil=Material("Soil","685849");
        Material blue=Material("Blue","758F99"),sage=Material("Sage","A4B1A0"),brick=Material("Brick","B98B73");
        var lamp=Material("Lamp","EBD9A9");

        bool supplied = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Models/MapModels/CuteHouse/CuteHouse.fbx");
        // Six customer spaces occupy the former crop/animal footprint.
        for (int bay=0;bay<6;bay++)
        {
            float z=-5.5f+bay*4f;
            Box(root,"Parking line",new Vector3(-16.1f,.151f,z-1.65f),new Vector3(5.2f,.018f,.10f),white);
            Box(root,"Parking line",new Vector3(-16.1f,.151f,z+1.65f),new Vector3(5.2f,.018f,.10f),white);
            Box(root,"Wheel stop",new Vector3(-18.2f,.22f,z),new Vector3(.24f,.17f,1.65f),stone);
            if (!supplied && (bay==0||bay==2||bay==4)) Car(root,new Vector3(-16.2f,.13f,z),bay==0?blue:bay==2?brick:sage,dark,glass,lamp);
        }
        // Shops have flat roofs and display windows, keeping the market the main landmark.
        if (!supplied)
        {
        Building(root,new Vector3(-31f,.13f,-2f),new Vector3(8f,4.3f,9f),sage,stone,glass,dark,white,"CAFÉ");
        Building(root,new Vector3(-31f,.13f,13f),new Vector3(8f,5.8f,8f),blue,stone,glass,dark,white,"FARMÁCIA");
        Building(root,new Vector3(-15f,.13f,39f),new Vector3(8f,4.4f,8f),brick,stone,glass,dark,white,"PAPELARIA");
        Building(root,new Vector3(-4f,.13f,39f),new Vector3(9f,6f,8f),sage,stone,glass,dark,white,"LOJAS");
        Building(root,new Vector3(9f,.13f,39f),new Vector3(8f,4.8f,8f),blue,stone,glass,dark,white,"CAFÉ");
        Building(root,new Vector3(32f,.13f,16f),new Vector3(9f,5f,10f),brick,stone,glass,dark,white,"SERVIÇOS");
        }

        foreach(var point in new[]{new Vector2(-24.7f,-10f),new Vector2(-24.7f,8f),new Vector2(-24.7f,26f),
            new Vector2(24.7f,-9f),new Vector2(24.7f,9f),new Vector2(24.7f,27f),new Vector2(-12f,32.8f),new Vector2(12f,32.8f)})
        {
            var p=new Vector3(point.x,.13f,point.y);
            Box(root,"Streetlight pole",p+Vector3.up*2f,new Vector3(.13f,4f,.13f),dark);
            Box(root,"Streetlight arm",p+new Vector3(.38f,3.95f,0),new Vector3(.85f,.12f,.14f),dark);
            Box(root,"Streetlight canopy",p+new Vector3(.73f,3.87f,0),new Vector3(.58f,.13f,.36f),dark);
            Box(root,"Streetlight lens",p+new Vector3(.73f,3.79f,0),new Vector3(.49f,.035f,.29f),lamp);
        }
        var landscape=world.Find("Landscape Models");
        var positions=new[]{new Vector2(-25.5f,-7),new Vector2(-25.5f,19),new Vector2(-19f,24),
            new Vector2(18f,7),new Vector2(18f,-7),new Vector2(18.2f,26),new Vector2(-10f,33.6f),
            new Vector2(8f,33.6f),new Vector2(27f,-5)};
        if (landscape)
            for(int i=0;i<positions.Length;i++)
            {
                var tree=landscape.Find("Tree "+(i+1));
                if(!tree)continue;
                Undo.RecordObject(tree,"Plant street tree");
                var bounds=tree.GetComponentsInChildren<Renderer>()[0].bounds;
                foreach(var renderer in tree.GetComponentsInChildren<Renderer>())bounds.Encapsulate(renderer.bounds);
                var p=positions[i];tree.position+=new Vector3(p.x-bounds.center.x,0,p.y-bounds.center.z);
                Box(root,"Tree bed",new Vector3(p.x,.17f,p.y),new Vector3(2f,.075f,2f),stone);
                Box(root,"Tree soil",new Vector3(p.x,.21f,p.y),new Vector3(1.75f,.04f,1.75f),soil);
            }
        foreach(float z in new[]{21.5f,24.5f})
        {
            for(int slat=0;slat<4;slat++)
                Box(root,"Plaza bench",new Vector3(-13f,.66f,z+slat*.16f),new Vector3(2.3f,.12f,.12f),wood);
            foreach(float x in new[]{-13.8f,-12.2f})
                Box(root,"Bench leg",new Vector3(x,.38f,z+.25f),new Vector3(.10f,.5f,.6f),dark);
        }
        Batch(root);
    }

    static void Building(Transform root,Vector3 p,Vector3 size,Material facade,Material stone,Material glass,Material dark,Material white,string name)
    {
        Box(root,"City shop "+name,p+Vector3.up*size.y*.5f,size,facade);
        Box(root,"Shop plinth",p+Vector3.up*.2f,new Vector3(size.x+.2f,.4f,size.z+.2f),stone);
        Box(root,"Flat roof",p+Vector3.up*(size.y+.12f),new Vector3(size.x+.25f,.25f,size.z+.25f),dark);
        Box(root,"Roof inset",p+Vector3.up*(size.y+.27f),new Vector3(size.x-.55f,.07f,size.z-.55f),stone);
        float front=p.z-size.z*.5f-.03f;
        for(int i=0;i<3;i++)
        {
            float x=p.x+(i-1)*size.x*.29f;
            Box(root,"Display surround",new Vector3(x,p.y+1.45f,front),new Vector3(size.x*.245f,2.35f,.10f),white);
            Box(root,"Display glass",new Vector3(x,p.y+1.45f,front-.06f),new Vector3(size.x*.215f,2.13f,.05f),glass);
            Box(root,"Window mullion",new Vector3(x,p.y+1.45f,front-.10f),new Vector3(.075f,2.13f,.06f),white);
        }
        Box(root,"Shop sign board",new Vector3(p.x,p.y+3.15f,front-.06f),new Vector3(size.x-.6f,.68f,.12f),dark);
        Label(root,name,new Vector3(p.x,p.y+3.15f,front-.14f),0f,white.color,.20f);
        Box(root,"Shop awning",new Vector3(p.x,p.y+2.72f,front-.38f),new Vector3(size.x-.25f,.13f,.85f),facade);
        if(size.y>5f)
            for(int i=-1;i<=1;i++)
                Box(root,"Upper window",new Vector3(p.x+i*size.x*.29f,p.y+4.55f,front-.01f),new Vector3(1.25f,1.25f,.08f),glass);
    }

    static void Car(Transform root,Vector3 p,Material body,Material dark,Material glass,Material lamp)
    {
        Box(root,"Parked car body",p+Vector3.up*.55f,new Vector3(3.8f,.62f,1.85f),body);
        Box(root,"Parked car cabin",p+new Vector3(-.15f,1.08f,0),new Vector3(2.15f,.65f,1.65f),glass);
        Box(root,"Parked car roof",p+new Vector3(-.15f,1.42f,0),new Vector3(2f,.12f,1.65f),body);
        foreach(float x in new[]{-1.2f,1.2f})
            foreach(float z in new[]{-.9f,.9f})
            {
                var wheel=Box(root,"Car wheel",p+new Vector3(x,.32f,z),new Vector3(.56f,.16f,.56f),dark,PrimitiveType.Cylinder);
                wheel.transform.rotation=Quaternion.Euler(90,0,0);
            }
        foreach(float z in new[]{-.6f,.6f})
            Box(root,"Car headlight",p+new Vector3(1.91f,.63f,z),new Vector3(.025f,.21f,.33f),lamp);
    }

    static void Label(Transform root,string value,Vector3 position,float yaw,Color color,float size)
    {
        var item=new GameObject(value,typeof(TextMesh));item.transform.SetParent(root,false);
        item.transform.SetPositionAndRotation(position,Quaternion.Euler(0,yaw,0));
        var text=item.GetComponent<TextMesh>();text.text=value;text.fontSize=64;text.characterSize=size;
        text.anchor=TextAnchor.MiddleCenter;text.color=color;
        text.font=Resources.Load<Font>("MarketBold")??Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        item.GetComponent<Renderer>().sharedMaterial=text.font.material;
    }

    static Material Material(string name,string hex)
    {
        string path=AssetRoot+"City"+name+".mat";
        var material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if(!material){material=new Material(Shader.Find("Standard"));AssetDatabase.CreateAsset(material,path);}
        material.color=MarketSimulation.C(hex);material.SetFloat("_Glossiness",.08f);EditorUtility.SetDirty(material);return material;
    }

    static GameObject Box(Transform root,string name,Vector3 position,Vector3 size,Material material,PrimitiveType shape=PrimitiveType.Cube)
    {
        var item=GameObject.CreatePrimitive(shape);item.name=name;item.transform.SetParent(root,false);
        item.transform.position=position;item.transform.localScale=size;item.GetComponent<Renderer>().sharedMaterial=material;
        UnityEngine.Object.DestroyImmediate(item.GetComponent<Collider>());return item;
    }

    static void Batch(Transform root)
    {
        var parts=root.GetComponentsInChildren<MeshFilter>().Where(part=>part.sharedMesh).ToArray();
        foreach(var group in parts.GroupBy(part=>part.GetComponent<Renderer>().sharedMaterial))
        {
            var mesh=new Mesh{name=group.Key.name+"Geometry"};
            mesh.CombineMeshes(group.Select(part=>new CombineInstance{mesh=part.sharedMesh,transform=root.worldToLocalMatrix*part.transform.localToWorldMatrix}).ToArray());
            string path=AssetRoot+mesh.name+".asset";
            var saved=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(saved){saved.Clear();saved.vertices=mesh.vertices;saved.normals=mesh.normals;saved.uv=mesh.uv;saved.triangles=mesh.triangles;saved.RecalculateBounds();EditorUtility.SetDirty(saved);UnityEngine.Object.DestroyImmediate(mesh);}
            else{AssetDatabase.CreateAsset(mesh,path);saved=mesh;}
            var item=new GameObject(group.Key.name,typeof(MeshFilter),typeof(MeshRenderer));item.transform.SetParent(root,false);
            item.GetComponent<MeshFilter>().sharedMesh=saved;item.GetComponent<Renderer>().sharedMaterial=group.Key;
        }
        foreach(var part in parts)UnityEngine.Object.DestroyImmediate(part.gameObject);
    }
}
