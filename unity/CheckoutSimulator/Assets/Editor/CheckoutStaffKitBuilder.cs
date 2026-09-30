using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Staff Kit: the hired stock clerk and cleaner (rigged, legacy clips) and their props — rear roller door, cleaning
// cart, wet-floor sign, step ladder, doorstep pallet, spill, dirt and the walkway swatch. All modelled in Blender
// (scripts/blender/build_staff_characters.py and build_staff_props.py) and mapped to the painted Interior Kit
// materials. CheckoutStaff and CheckoutIncidents clone the templates at runtime.
public static partial class CheckoutMarketStagesBuilder
{
    const string StaffFolder = "Assets/Art/Staff/Models/";
    const string StaffKitName = "Staff Kit";
    static readonly string[] StaffClips = { "Idle", "Walking", "CarryWalking", "CarryIdle", "Pickup", "PutDown", "Restock", "PushWalking", "PushIdle", "Mop", "ReachUp" };
    static readonly string[] StaffLoops = { "Idle", "Walking", "CarryWalking", "CarryIdle", "Restock", "PushWalking", "PushIdle", "Mop", "ReachUp" };
    static readonly string[] StaffProps = { "staff-door", "staff-warehouse-door", "staff-cart", "staff-wetsign", "staff-ladder", "staff-pallet", "staff-puddle", "staff-dirt-a", "staff-dirt-b", "staff-path" };
    // Staff reuse the delivery worker's body (head joint at 1.96 m); the shop's workers stand a little shorter.
    const float StaffScale = .85f;

    [MenuItem("Supermarket/Build staff kit (clerk, cleaner, rear door)")]
    public static void BuildStaffKitMenu()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation || !simulation.world) throw new InvalidOperationException("Open the Supermarket scene first.");
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear();
        BuildStaffKit(simulation.world);
        EditorSceneManager.MarkSceneDirty(simulation.world.gameObject.scene);
        EditorSceneManager.SaveScene(simulation.world.gameObject.scene);
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_STAFF_KIT_OK");
    }

    public static void BuildStaffKit(Transform world)
    {
        var old = world.Find(StaffKitName); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var kit = new GameObject(StaffKitName).transform;
        kit.SetParent(world, false); kit.rotation = Quaternion.identity; kit.position = new Vector3(40, -40, 0);
        int slot = 0;
        Transform Next(string id) { var t = new GameObject(id).transform; t.SetParent(kit, false); t.localPosition = new Vector3(slot++ * 3f, 0, 0); return t; }
        var clerk = StaffCharacter(Next("Staff Clerk"), "Staff_Clerk", null);
        StaffCharacter(Next("Staff Cleaner"), "Staff_Cleaner", clerk);
        foreach (var p in StaffProps) StaffProp(Next(p), p);
        kit.gameObject.SetActive(false);
    }

    static void StaffImport(string path, bool animated)
    {
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (!importer) throw new InvalidOperationException("Missing staff model " + path + " (run the Blender scripts).");
        importer.importNormals = ModelImporterNormals.Import; importer.addCollider = false; importer.importCameras = false; importer.importLights = false;
        importer.materialLocation = ModelImporterMaterialLocation.InPrefab; importer.bakeAxisConversion = false;
        importer.importAnimation = animated;
        if (animated)
        {
            importer.animationType = ModelImporterAnimationType.Legacy; importer.animationCompression = ModelImporterAnimationCompression.Off;
            var seen = new HashSet<string>(); var clips = new List<ModelImporterClipAnimation>();
            foreach (var clip in importer.defaultClipAnimations)
            {
                string logical = clip.name.Substring(clip.name.LastIndexOf('|') + 1);
                int dot = logical.IndexOf('.'); if (dot > 0) logical = logical.Substring(0, dot);
                if (!StaffClips.Contains(logical) || !seen.Add(logical)) continue;
                clip.name = logical; clip.loopTime = StaffLoops.Contains(logical);
                clip.wrapMode = clip.loopTime ? WrapMode.Loop : WrapMode.ClampForever;
                clips.Add(clip);
            }
            importer.clipAnimations = clips.ToArray();
        }
        else importer.animationType = ModelImporterAnimationType.None;
        importer.SaveAndReimport();
    }

    // Body of a staff character: the recoloured Meshy worker texture (Staff_Clerk.png...) on the painted shader.
    static Material StaffBody(string materialName)
    {
        string name = materialName.Split('.')[0];
        string character = name.EndsWith("_Body") ? name.Substring(0, name.Length - 5) : name;
        if (materials.TryGetValue(name, out var cached)) return cached;
        const string folder = "Assets/Art/Staff/Materials";
        if (!AssetDatabase.IsValidFolder(folder)) AssetDatabase.CreateFolder("Assets/Art/Staff", "Materials");
        string texturePath = StaffFolder + character + ".png";
        var importer = AssetImporter.GetAtPath(texturePath) as TextureImporter;
        if (importer && (!importer.sRGBTexture || importer.maxTextureSize != 2048)) { importer.sRGBTexture = true; importer.mipmapEnabled = true; importer.maxTextureSize = 2048; importer.SaveAndReimport(); }
        string path = folder + "/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("MarketDay/Soft Painted")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("MarketDay/Soft Painted");
        material.color = Color.white;
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        material.SetFloat("_Outline", .35f);
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static void StaffRemap(GameObject model)
    {
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = mats[i] && mats[i].name.StartsWith("Staff_") ? StaffBody(mats[i].name) : KitRemap(mats[i]);
            r.sharedMaterials = mats;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
        }
    }

    // Root (identity, faces -Z like every market rig) > "Visual" (the FBX, legacy Animation with the logical clips).
    static Transform StaffCharacter(Transform root, string file, Transform reference)
    {
        string path = StaffFolder + file + ".fbx";
        StaffImport(path, true);
        var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var visual = (GameObject)PrefabUtility.InstantiatePrefab(source, root);
        PrefabUtility.UnpackPrefabInstance(visual, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        visual.name = "Visual"; visual.transform.localPosition = Vector3.zero; visual.transform.localScale *= StaffScale;
        StaffRemap(visual);
        var player = visual.GetComponent<Animation>(); if (!player) player = visual.AddComponent<Animation>();
        foreach (var state in player.Cast<AnimationState>().Select(s => s.name).ToList()) player.RemoveClip(state);
        foreach (var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")))
            if (StaffClips.Contains(clip.name) && !player[clip.name]) player.AddClip(clip, clip.name);
        foreach (var clip in StaffClips) if (!player[clip]) throw new InvalidOperationException("Missing staff clip " + file + " / " + clip);
        player.clip = player["Idle"].clip; player.playAutomatically = false; player.cullingType = AnimationCullingType.AlwaysAnimate;
        foreach (var s in visual.GetComponentsInChildren<SkinnedMeshRenderer>(true)) s.updateWhenOffscreen = true;

        // Facing: the box a clerk carries sits in front of the chest, so the body faces the side the box is on. Rigs
        // face -Z; turn the visual when the box came in on +Z. The cleaner shares the export settings.
        if (reference) visual.transform.localRotation = reference.Find("Visual").localRotation;
        else
        {
            player["Idle"].clip.SampleAnimation(visual, 0);
            var box = visual.GetComponentsInChildren<Renderer>(true).FirstOrDefault(r => r.name == "Box_caixa");
            var torso = visual.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Torso");
            if (box && torso && root.InverseTransformPoint(box.bounds.center).z > root.InverseTransformPoint(torso.position).z)
                visual.transform.localRotation = Quaternion.Euler(0, 180, 0) * visual.transform.localRotation;
        }
        // The soles sit at z 0 in Blender, so the rig stands on the root as imported.
        return root;
    }

    static void StaffProp(Transform t, string name)
    {
        string path = StaffFolder + name + ".fbx";
        StaffImport(path, false);
        var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var model = UnityEngine.Object.Instantiate(source, t, false);
        model.name = "Model"; model.transform.localPosition = Vector3.zero;
        StaffRemap(model);
    }
}
