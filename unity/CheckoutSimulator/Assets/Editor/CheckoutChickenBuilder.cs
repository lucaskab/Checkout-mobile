using System;
using System.IO;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CheckoutChickenBuilder
{
    const string WhitePath = "Assets/Art/Animals/Chickens/White/ChickenWhite.fbx";
    const string BrownPath = "Assets/Art/Animals/Chickens/Brown/ChickenBrown.fbx";
    const float VisualScale = 0.9f;
    static readonly string[] Clips = { "Idle", "Walk", "Eat" };

    [MenuItem("Supermarket/Apply Tripo chickens to current scene")]
    public static void Apply()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation) throw new InvalidOperationException("Missing MarketSimulation.");

        ApplyToWorld(simulation.world);
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_CHICKENS_OK");
    }

    public static void ApplyToWorld(Transform world)
    {
        ConfigureImport(WhitePath);
        ConfigureImport(BrownPath);
        var whiteMaterial = ConfigureMaterial(WhitePath, "tripo_node_9ce47831-0eff-4795-be8e-d910a13ab399_BaseColor.jpg", "ChickenWhite.mat");
        var brownMaterial = ConfigureMaterial(BrownPath, "tripo_node_2c6a210e-60ad-4021-b96e-737470b65e6f_BaseColor.jpg", "ChickenBrown.mat");

        var chickens = world.Cast<Transform>()
            .Where(child => child.name.StartsWith("Anim_Chicken_"))
            .OrderBy(child => child.name)
            .ToArray();
        if (chickens.Length == 0) throw new InvalidOperationException("Missing chicken markers in market world.");

        for (var index = 0; index < chickens.Length; index++)
        {
            var chicken = chickens[index];
            var useWhite = index % 2 == 0;
            var path = useWhite ? WhitePath : BrownPath;
            var material = useWhite ? whiteMaterial : brownMaterial;
            var oldVisuals = chicken.Cast<Transform>().Where(child => child.name == "Visual").ToArray();
            foreach (var oldVisual in oldVisuals) UnityEngine.Object.DestroyImmediate(oldVisual.gameObject);

            chicken.position = new Vector3(chicken.position.x, MarketSimulation.P(0f, 0f).y, chicken.position.z);
            chicken.rotation = Quaternion.Euler(0f, 180f + index * 27f, 0f);

            var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (!source) throw new InvalidOperationException("Missing Tripo chicken: " + path);
            var visual = UnityEngine.Object.Instantiate(source, chicken);
            visual.name = "Visual";
            visual.transform.localPosition = Vector3.zero;
            visual.transform.localRotation = Quaternion.identity;
            visual.transform.localScale = Vector3.one * VisualScale;

            var bounds = GetBounds(visual.transform);
            visual.transform.position += Vector3.up * (MarketSimulation.P(0f, 0f).y - bounds.min.y);
            foreach (var renderer in visual.GetComponentsInChildren<Renderer>())
                renderer.sharedMaterials = Enumerable.Repeat(material, renderer.sharedMaterials.Length).ToArray();

            var player = visual.GetComponent<Animation>();
            if (!player) player = visual.AddComponent<Animation>();
            foreach (var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(clip => !clip.name.StartsWith("__preview__")))
                player.AddClip(clip, clip.name);
            foreach (var clip in Clips)
                if (!player[clip]) throw new InvalidOperationException("Missing chicken clip: " + path + " / " + clip);
            player.playAutomatically = false;
            player.cullingType = AnimationCullingType.AlwaysAnimate;

            var animator = chicken.GetComponent<MarketChickenAnimator>();
            if (!animator) animator = chicken.gameObject.AddComponent<MarketChickenAnimator>();
            animator.animationPlayer = player;
        }
    }

    [MenuItem("Supermarket/Validate Tripo chickens")]
    public static void Validate()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var chickens = world.Cast<Transform>().Where(child => child.name.StartsWith("Anim_Chicken_")).ToArray();
        if (chickens.Length != 4) throw new InvalidOperationException("Expected four chickens, found " + chickens.Length + ".");

        foreach (var chicken in chickens)
        {
            var animator = chicken.GetComponent<MarketChickenAnimator>();
            if (!animator || !animator.animationPlayer) throw new InvalidOperationException("Missing chicken animator: " + chicken.name);
            var body = animator.animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>().Single();
            if (!body.sharedMaterial.mainTexture || body.sharedMesh.vertexCount > 25000)
                throw new InvalidOperationException("Invalid chicken mesh or material: " + chicken.name);
            var renderedBounds = GetBounds(animator.animationPlayer.transform);
            if (renderedBounds.size.x > 2f || renderedBounds.size.y > 2f || renderedBounds.size.z > 2f ||
                Vector3.Distance(renderedBounds.center, chicken.position) > 2f)
                throw new InvalidOperationException("Chicken is incorrectly scaled or displaced: " + chicken.name + " / " + renderedBounds);
            if (Camera.main && !GeometryUtility.TestPlanesAABB(GeometryUtility.CalculateFrustumPlanes(Camera.main), renderedBounds))
                throw new InvalidOperationException("Chicken is outside the game camera: " + chicken.name);
            foreach (var clipName in Clips)
            {
                var clip = animator.animationPlayer[clipName].clip;
                var baked = new Mesh();
                clip.SampleAnimation(animator.animationPlayer.gameObject, 0f);
                body.BakeMesh(baked);
                var start = baked.vertices;
                clip.SampleAnimation(animator.animationPlayer.gameObject, clip.length * 0.35f);
                body.BakeMesh(baked);
                var end = baked.vertices;
                if (!end.Where((point, index) => (point - start[index]).sqrMagnitude > 0.000001f).Any())
                    throw new InvalidOperationException("Static chicken clip: " + chicken.name + " / " + clipName);
                UnityEngine.Object.DestroyImmediate(baked);
            }
        }
        Debug.Log("CHECKOUT_CHICKEN_VALIDATION_OK chickens=" + chickens.Length);
    }

    [MenuItem("Supermarket/Capture Tripo chicken preview")]
    public static void CapturePreview()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation) throw new InvalidOperationException("Missing MarketSimulation.");

        var renderers = simulation.world.Cast<Transform>()
            .Where(child => child.name.StartsWith("Anim_Chicken_"))
            .SelectMany(chicken => chicken.GetComponentsInChildren<Renderer>(true))
            .ToArray();
        if (renderers.Length == 0) throw new InvalidOperationException("Missing rendered chickens.");
        foreach (var renderer in renderers)
        {
            var skin = renderer as SkinnedMeshRenderer;
            Debug.Log($"CHECKOUT_CHICKEN_RENDERER name={renderer.transform.root.name}/{renderer.name} " +
                $"position={renderer.transform.position} scale={renderer.transform.lossyScale} bounds={renderer.bounds} " +
                $"bakedBounds={GetRendererBounds(renderer)} enabled={renderer.enabled} active={renderer.gameObject.activeInHierarchy} " +
                $"materials={renderer.sharedMaterials.Length} forceOff={renderer.forceRenderingOff} " +
                $"bones={(skin ? skin.bones.Length.ToString() : "n/a")} vertices={(skin && skin.sharedMesh ? skin.sharedMesh.vertexCount.ToString() : "n/a")} " +
                $"localBounds={(skin ? skin.localBounds.ToString() : "n/a")} rootBone={(skin && skin.rootBone ? skin.rootBone.position.ToString() : "n/a")}");
        }

        var bounds = GetRendererBounds(renderers[0]);
        foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(GetRendererBounds(renderer));

        var cameraObject = new GameObject("Tripo Chicken Preview Camera");
        var camera = cameraObject.AddComponent<Camera>();
        var gameCamera = Camera.main;
        if (gameCamera) camera.CopyFrom(gameCamera);
        camera.enabled = false;
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.72f, 0.83f, 0.68f, 1f);
        camera.orthographic = true;
        camera.orthographicSize = Mathf.Max(2.1f, bounds.extents.x / 1.35f, bounds.extents.z * 1.15f);
        camera.transform.position = bounds.center + new Vector3(-4.5f, 5f, -4.5f);
        camera.transform.LookAt(bounds.center + Vector3.up * 0.2f);

        var target = RenderTexture.GetTemporary(1200, 800, 24, RenderTextureFormat.ARGB32);
        var previousTarget = camera.targetTexture;
        var previousActive = RenderTexture.active;
        camera.targetTexture = target;
        camera.Render();
        RenderTexture.active = target;
        var image = new Texture2D(target.width, target.height, TextureFormat.RGB24, false);
        image.ReadPixels(new Rect(0f, 0f, target.width, target.height), 0, 0);
        image.Apply();
        var outputPath = "/tmp/checkout-tripo-chickens.png";
        File.WriteAllBytes(outputPath, image.EncodeToPNG());

        camera.targetTexture = previousTarget;
        RenderTexture.active = previousActive;
        RenderTexture.ReleaseTemporary(target);
        UnityEngine.Object.DestroyImmediate(image);
        UnityEngine.Object.DestroyImmediate(cameraObject);
        Debug.Log($"CHECKOUT_CHICKEN_CAPTURE_OK path={outputPath} bounds={bounds}");
    }

    static void ConfigureImport(string path)
    {
        var importer = (ModelImporter)AssetImporter.GetAtPath(path);
        if (!importer) throw new InvalidOperationException("Missing chicken importer: " + path);
        importer.animationType = ModelImporterAnimationType.Legacy;
        importer.importAnimation = true;
        importer.importCameras = false;
        importer.importLights = false;
        importer.materialImportMode = ModelImporterMaterialImportMode.None;
        importer.useFileScale = true;
        importer.globalScale = 1f;
        importer.animationCompression = ModelImporterAnimationCompression.Optimal;
        importer.meshCompression = ModelImporterMeshCompression.Medium;
        importer.isReadable = false;
        importer.optimizeMeshPolygons = true;
        importer.optimizeMeshVertices = true;
        var clips = importer.defaultClipAnimations;
        foreach (var clip in clips)
        {
            foreach (var name in Clips)
                if (clip.name.EndsWith(name, StringComparison.OrdinalIgnoreCase)) clip.name = name;
            clip.loopTime = true;
            clip.wrapMode = WrapMode.Loop;
        }
        importer.clipAnimations = clips;
        importer.SaveAndReimport();
    }

    static Material ConfigureMaterial(string modelPath, string textureName, string materialName)
    {
        var folder = modelPath.Substring(0, modelPath.LastIndexOf('/') + 1);
        var texturePath = folder + "Textures/" + textureName;
        var textureImporter = (TextureImporter)AssetImporter.GetAtPath(texturePath);
        if (!textureImporter) throw new InvalidOperationException("Missing chicken texture: " + texturePath);
        textureImporter.sRGBTexture = true;
        textureImporter.mipmapEnabled = true;
        textureImporter.maxTextureSize = 1024;
        textureImporter.textureCompression = TextureImporterCompression.CompressedHQ;
        if (AssetDatabase.WriteImportSettingsIfDirty(texturePath)) AssetDatabase.ImportAsset(texturePath);

        var materialPath = folder + materialName;
        var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        if (!material)
        {
            material = new Material(Shader.Find("MarketDay/Soft Painted"));
            AssetDatabase.CreateAsset(material, materialPath);
        }
        material.shader = Shader.Find("MarketDay/Soft Painted");
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        material.SetFloat("_Outline", 0.32f);
        material.SetColor("_OutlineColor", new Color(0.2f, 0.1f, 0.05f, 1f));
        EditorUtility.SetDirty(material);
        return material;
    }

    static Bounds GetBounds(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0) throw new InvalidOperationException("No chicken renderer found.");
        var bounds = GetRendererBounds(renderers[0]);
        for (var index = 1; index < renderers.Length; index++) bounds.Encapsulate(GetRendererBounds(renderers[index]));
        return bounds;
    }

    static Bounds GetRendererBounds(Renderer renderer)
    {
        if (!(renderer is SkinnedMeshRenderer skin)) return renderer.bounds;
        var mesh = new Mesh();
        skin.BakeMesh(mesh);
        if (mesh.vertexCount == 0)
        {
            UnityEngine.Object.DestroyImmediate(mesh);
            return renderer.bounds;
        }

        var vertices = mesh.vertices;
        var bounds = new Bounds(renderer.transform.TransformPoint(vertices[0]), Vector3.zero);
        for (var index = 1; index < vertices.Length; index++) bounds.Encapsulate(renderer.transform.TransformPoint(vertices[index]));
        UnityEngine.Object.DestroyImmediate(mesh);
        return bounds;
    }
}
