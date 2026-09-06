using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.EventSystems;
using MarketDay;

public static class MarketBuilder
{
    public const string ScenePath="Assets/Scenes/Supermarket.unity";
    [MenuItem("Supermarket/Build fresh scene")]
    public static void Build()
    {
        if(EditorApplication.isPlaying)throw new InvalidOperationException("Leave Play mode before rebuilding.");
        Directory.CreateDirectory("Assets/Scenes");Directory.CreateDirectory("Assets/Art/Materials");
        var modelImporter=(ModelImporter)AssetImporter.GetAtPath("Assets/Art/Models/MarketWorld.fbx");
        modelImporter.globalScale=1;modelImporter.useFileScale=true;modelImporter.importCameras=false;modelImporter.importLights=false;
        modelImporter.isReadable=false;modelImporter.meshCompression=ModelImporterMeshCompression.Off;
        modelImporter.materialImportMode=ModelImporterMaterialImportMode.None;modelImporter.SaveAndReimport();
        var ti=(TextureImporter)AssetImporter.GetAtPath("Assets/Art/Textures/MarketAtlas.png");ti.sRGBTexture=true;ti.mipmapEnabled=true;ti.wrapMode=TextureWrapMode.Clamp;ti.maxTextureSize=1024;ti.textureCompression=TextureImporterCompression.Uncompressed;ti.anisoLevel=4;ti.SaveAndReimport();
        var mat=AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/MarketPaint.mat");
        if(!mat){mat=new Material(Shader.Find("MarketDay/Soft Painted"));AssetDatabase.CreateAsset(mat,"Assets/Art/Materials/MarketPaint.mat");}
        mat.shader=Shader.Find("MarketDay/Soft Painted");mat.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Art/Textures/MarketAtlas.png");
        mat.SetFloat("_Outline",1.45f);mat.SetColor("_OutlineColor",new Color(.22f,.115f,.055f,1));
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var model=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Art/Models/MarketWorld.fbx");
        if(!model)throw new InvalidOperationException("Blender model was not imported.");
        var world=(GameObject)PrefabUtility.InstantiatePrefab(model);world.name="Supermarket World";
        PrefabUtility.UnpackPrefabInstance(world,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);
        world.transform.rotation=Quaternion.Euler(0,180,0);
        foreach(var actor in world.transform.Cast<Transform>().Where(t=>t.name.StartsWith("Worker_")||t.name.StartsWith("Customer_")).ToArray())
        {
            var wrapper=new GameObject(actor.name);wrapper.transform.SetParent(world.transform);wrapper.transform.position=actor.position;wrapper.transform.rotation=Quaternion.identity;
            string assetPath="Assets/Art/Characters/"+actor.name+".fbx";
            var importer=(ModelImporter)AssetImporter.GetAtPath(assetPath);
            if(importer==null)throw new Exception("Missing reference character: "+assetPath);
            importer.animationType=ModelImporterAnimationType.Legacy;importer.importAnimation=true;
            importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.importCameras=false;importer.importLights=false;
            importer.animationCompression=ModelImporterAnimationCompression.Off;
            var clips=importer.defaultClipAnimations;
            foreach(var clip in clips){foreach(string logical in new[]{"Idle","Walking","GetFromShelf","BuyAtSpecialSector","PayAtCheckout"})if(clip.name.Contains(logical))clip.name=logical;clip.loopTime=clip.name=="Idle"||clip.name=="Walking";clip.wrapMode=clip.loopTime?WrapMode.Loop:WrapMode.ClampForever;}
            importer.clipAnimations=clips;importer.SaveAndReimport();
            var character=AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            var visual=UnityEngine.Object.Instantiate(character,wrapper.transform);visual.name="Visual";
            visual.transform.localPosition=Vector3.zero;visual.transform.localRotation=Quaternion.Euler(0,180,0);
            UnityEngine.Object.DestroyImmediate(actor.gameObject);
            var player=visual.GetComponent<Animation>();if(!player)player=visual.AddComponent<Animation>();
            foreach(var clip in AssetDatabase.LoadAllAssetsAtPath(assetPath).OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__"))){player.AddClip(clip,clip.name);Debug.Log("CHARACTER_CLIP "+wrapper.name+" "+clip.name+" "+clip.length);}
            foreach(string required in new[]{"Idle","Walking","GetFromShelf","BuyAtSpecialSector","PayAtCheckout"})if(!player[required])throw new Exception("Missing clip "+wrapper.name+" "+required);
            player.playAutomatically=false;player.cullingType=AnimationCullingType.AlwaysAnimate;
            wrapper.AddComponent<MarketCharacterAnimator>().animationPlayer=player;
        }
        foreach(var actor in world.transform.Cast<Transform>().Where(t=>t.name.StartsWith("Anim_")).ToArray())
        {
            var wrapper=new GameObject(actor.name);wrapper.transform.SetParent(world.transform);wrapper.transform.position=actor.GetComponent<Renderer>().bounds.center;wrapper.transform.rotation=Quaternion.identity;
            actor.name="Visual";actor.SetParent(wrapper.transform,true);
        }
        var glass=AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/Glass.mat");
        if(!glass){glass=new Material(Shader.Find("Sprites/Default"));AssetDatabase.CreateAsset(glass,"Assets/Art/Materials/Glass.mat");}
        glass.color=new Color(.38f,.85f,.89f,.14f);
        foreach(var r in world.GetComponentsInChildren<Renderer>())r.sharedMaterials=r.sharedMaterials.Length>1?new[]{mat,glass}:new[]{mat};
        var camObject=new GameObject("Isometric Camera",typeof(Camera),typeof(AudioListener));var cam=camObject.GetComponent<Camera>();
        cam.orthographic=true;cam.orthographicSize=13.5f;cam.nearClipPlane=.1f;cam.farClipPlane=150;cam.backgroundColor=MarketSimulation.C("BBD7B4");cam.clearFlags=CameraClearFlags.SolidColor;cam.allowHDR=false;cam.allowMSAA=true;cam.tag="MainCamera";
        cam.allowDynamicResolution=false;cam.gameObject.AddComponent<MarketSharpness>().shader=Shader.Find("Hidden/MarketDay/Native Clarity");
        var focus=new Vector3(-.6f,.1f,2.4f);cam.transform.position=focus+new Vector3(28,33,-38);cam.transform.LookAt(focus);
        var sun=new GameObject("Warm afternoon sun",typeof(Light)).GetComponent<Light>();sun.type=LightType.Directional;sun.color=new Color(1,.94f,.80f);sun.intensity=1.12f;sun.shadows=LightShadows.Soft;sun.shadowStrength=.48f;sun.shadowBias=.04f;sun.shadowNormalBias=.2f;sun.transform.rotation=Quaternion.Euler(47,-35,0);
        RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.47f,.49f,.40f);RenderSettings.fog=false;RenderSettings.skybox=null;
        QualitySettings.shadowDistance=85;QualitySettings.shadowResolution=ShadowResolution.High;QualitySettings.shadows=ShadowQuality.All;QualitySettings.antiAliasing=4;QualitySettings.vSyncCount=0;
        var manager=new GameObject("Market Simulation",typeof(MarketSimulation)).GetComponent<MarketSimulation>();manager.world=world.transform;manager.view=cam;
        manager.gameObject.AddComponent<MarketPlaytest>();
        manager.gameObject.AddComponent<MarketAmbientLife>();
        var ui=new GameObject("Market Interface",typeof(RectTransform));var hud=ui.AddComponent<MarketHUD>();manager.hud=hud;
        new GameObject("Event System",typeof(EventSystem),typeof(StandaloneInputModule));
        Hit(world.transform,"Bakery",0,MarketSimulation.P(-6.1f,.1f)+Vector3.up, new Vector3(4,2.7f,6.7f));
        Hit(world.transform,"Groceries",1,MarketSimulation.P(.15f,-.4f)+Vector3.up,new Vector3(5.8f,2.8f,6));
        Hit(world.transform,"Fishery",2,MarketSimulation.P(1.5f,4.3f)+Vector3.up,new Vector3(3.9f,2.6f,1.8f));
        Hit(world.transform,"Butcher",3,MarketSimulation.P(6.5f,4.3f)+Vector3.up,new Vector3(4.1f,2.6f,1.9f));
        Hit(world.transform,"Produce",4,MarketSimulation.P(6.55f,.45f)+Vector3.up,new Vector3(3.1f,2.5f,2.3f));
        PlayerSettings.companyName="Independent Studio";PlayerSettings.productName="Supermarket Simulator";
        PlayerSettings.defaultInterfaceOrientation=UIOrientation.LandscapeLeft;PlayerSettings.allowedAutorotateToLandscapeLeft=true;PlayerSettings.allowedAutorotateToLandscapeRight=true;PlayerSettings.allowedAutorotateToPortrait=false;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;
        PlayerSettings.defaultScreenWidth=1600;PlayerSettings.defaultScreenHeight=1000;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.runInBackground=true;PlayerSettings.colorSpace=ColorSpace.Linear;
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android,"com.marketday.supermarketsimulator");
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS,"com.marketday.supermarketsimulator");
        PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;
        PlayerSettings.iOS.targetOSVersionString="15.0";
        EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};
        EditorSceneManager.SaveScene(scene,ScenePath);AssetDatabase.SaveAssets();
        if(SceneView.lastActiveSceneView){SceneView.lastActiveSceneView.LookAt(focus,cam.transform.rotation,24,true);SceneView.lastActiveSceneView.Repaint();}
        Debug.Log("MARKET_BUILD_OK | "+world.GetComponentsInChildren<MeshFilter>().Sum(f=>f.sharedMesh.vertexCount)+" vertices | "+world.GetComponentsInChildren<Renderer>().Length+" renderers");
    }
    static void Hit(Transform root,string label,int id,Vector3 center,Vector3 size)
    {
        var go=new GameObject(label+" touch target");go.transform.SetParent(root);go.transform.position=center;go.AddComponent<BoxCollider>().size=size;go.AddComponent<DepartmentTarget>().department=id;
    }
    [MenuItem("Supermarket/Validate economy and routes")]
    public static void Validate()
    {
        int checks=0;Action<bool,string> require=(ok,msg)=>{if(!ok)throw new Exception(msg);checks++;};
        var m=MarketEconomy.Fresh();require(m.Valid(),"Fresh save invalid");int initial=m.coins;
        require(m.Order(0,out _),"Cannot order fresh supply");require(m.coins==initial-60,"Order did not charge once");
        require(!m.Order(0,out _),"Duplicate pending order accepted");m.Tick(11);require(m.departments[0].reserve==24,"Delivery arrived early");
        m.Tick(1);require(m.departments[0].reserve==44&&m.departments[0].incoming==0,"Delivery quantity lost");
        int total=m.departments[0].stock+m.departments[0].reserve;require(m.Refill(0)==8,"Refill should clamp to capacity");require(m.departments[0].stock+m.departments[0].reserve==total,"Refill created inventory");
        m.departments[0].stock=0;require(!m.TakeFromShelf(0),"Empty display sold stock");require(m.departments[0].stock==0,"Negative stock");
        m.coins=0;require(!m.Upgrade(0,out _),"Unaffordable upgrade accepted");require(!m.Hire(out _),"Unaffordable hire accepted");require(!m.Order(1,out _),"Unaffordable order accepted");
        m.served=5;require(m.Claim(0),"Completed goal not claimable");require(!m.Claim(0),"Goal rewarded twice");
        var roundtrip=JsonUtility.FromJson<MarketEconomy>(JsonUtility.ToJson(m));require(roundtrip.Valid(),"Save roundtrip invalid");
        require(roundtrip.coins==m.coins&&roundtrip.claimed[0],"Save lost state");
        var sim=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if(sim&&Application.isPlaying)
        {
            for(int i=0;i<5;i++)require(sim.Route(MarketSimulation.P(-1.75f,-8.5f),sim.browse[i]).Count>0,"No route to "+sim.names[i]);
        }
        string message="MARKET_TESTS_OK | "+checks+" checks";Debug.Log(message);
        Directory.CreateDirectory("ArtSource");File.WriteAllText("ArtSource/validation.txt",message+"\n"+DateTime.UtcNow.ToString("O"));
    }
    public static void Capture(string path)
    {
        var cam=Camera.main;if(!cam)throw new Exception("No camera");
        var old=cam.targetTexture;var active=RenderTexture.active;var rt=new RenderTexture(1600,1000,24);rt.antiAliasing=4;
        cam.targetTexture=rt;Canvas.ForceUpdateCanvases();
        var hud=UnityEngine.Object.FindAnyObjectByType<MarketHUD>();if(hud)hud.Relayout();
        Canvas.ForceUpdateCanvases();cam.Render();RenderTexture.active=rt;
        var img=new Texture2D(1600,1000,TextureFormat.RGB24,false);img.ReadPixels(new Rect(0,0,1600,1000),0,0);img.Apply();File.WriteAllBytes(path,img.EncodeToPNG());
        cam.targetTexture=old;RenderTexture.active=active;UnityEngine.Object.DestroyImmediate(img);UnityEngine.Object.DestroyImmediate(rt);Debug.Log("MARKET_CAPTURE_OK "+path);
    }
    [MenuItem("Supermarket/Build Windows preview")]
    public static void BuildWindows()
    {
        Directory.CreateDirectory("../WindowsPreview");
        var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName="../WindowsPreview/SupermarketSimulator.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.CleanBuildCache});
        if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Windows preview build failed: "+report.summary.result);
        Debug.Log("MARKET_WINDOWS_BUILD_OK "+report.summary.totalSize);
    }
    public static void BuildAndWindows()
    {
        Build();Validate();BuildWindows();
    }
    [MenuItem("Supermarket/Build Android APK")]
    public static void BuildAndroid()
    {
        PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
        PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)36;
        EditorUserBuildSettings.buildAppBundle=false;
        Directory.CreateDirectory("../Android");
        var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName="../Android/SupermarketSimulator.apk",target=BuildTarget.Android,options=BuildOptions.None});
        if(report.summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Android build failed: "+report.summary.result);
        Debug.Log("MARKET_ANDROID_BUILD_OK "+report.summary.totalSize);
    }
}

