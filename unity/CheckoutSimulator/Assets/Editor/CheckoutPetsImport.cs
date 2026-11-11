using System.Linq;
using UnityEditor;
using UnityEngine;

// Import settings of the store dog (Resources/CheckoutPets, ArtSource/pets) and of the shoplifter / security guard
// (Resources/CheckoutSecurity): Legacy animation like the market's characters (CheckoutPets / CheckoutSecurity play
// clips by name), clip names without the Blender rig prefix, loops for the cycles; materials are made in code.
public class CheckoutPetsImport : AssetPostprocessor
{
    static readonly string[] Roots = { "Assets/Resources/CheckoutPets/", "Assets/Resources/CheckoutSecurity/" };
    static readonly string[] Loops = { "Idle", "Walk", "Trot", "SitIdle", "Sleep", "CurlSleep", "Happy", "Sniff", "Sneak", "LookAround", "Run",
        "HandsUp", "WalkAshamed", "Radio", "Walking", "Idle0", "Cuffed", "CuffedWalk", "Escort" };

    bool Ours => Roots.Any(r => assetPath.StartsWith(r));

    void OnPreprocessModel()
    {
        if (!Ours) return;
        var importer = (ModelImporter)assetImporter;
        bool rigged = !assetPath.Contains("PetBed") && !assetPath.Contains("PetBowls") && !assetPath.Contains("Gate");
        importer.animationType = rigged ? ModelImporterAnimationType.Legacy : ModelImporterAnimationType.None;
        importer.importAnimation = rigged; importer.importCameras = false; importer.importLights = false;
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;   // names kept, swapped in code
        importer.animationCompression = ModelImporterAnimationCompression.Off;
        importer.useFileScale = true; importer.globalScale = 1;
    }

    void OnPreprocessAnimation()
    {
        if (!Ours) return;
        var importer = (ModelImporter)assetImporter;
        var clips = importer.defaultClipAnimations;
        foreach (var clip in clips)
        {
            var name = clip.name.Contains("|") ? clip.name.Substring(clip.name.LastIndexOf('|') + 1) : clip.name;
            clip.name = name;
            var core = name.Contains("_") ? name.Substring(name.IndexOf('_') + 1) : name;
            clip.loopTime = Loops.Contains(core);
            clip.wrapMode = clip.loopTime ? WrapMode.Loop : WrapMode.ClampForever;
        }
        importer.clipAnimations = clips;
    }

    // The dog's coat mesh carries two UV sets from Blender: FurUV (the fur direction helper of the painting) comes first,
    // the painted atlas ("UVMap") second. The game reads the first set, so the atlas one is moved there.
    void OnPostprocessModel(GameObject root)
    {
        if (!assetPath.EndsWith("CheckoutPets/Caramelo.fbx")) return;
        foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            FixUv(smr.sharedMesh);
        foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            FixUv(mf.sharedMesh);
    }

    static void FixUv(Mesh mesh)
    {
        if (!mesh || mesh.uv2 == null || mesh.uv2.Length == 0 || mesh.uv2.Length != mesh.vertexCount) return;
        mesh.uv = mesh.uv2;
        mesh.uv2 = null;
    }

    void OnPreprocessTexture()
    {
        if (!Ours) return;
        var importer = (TextureImporter)assetImporter;
        importer.maxTextureSize = 2048; importer.mipmapEnabled = true; importer.sRGBTexture = true;
        importer.alphaSource = TextureImporterAlphaSource.None;
        // Android build size: 3D world textures are capped at 1024 there (approved by Lucas).
        importer.SetPlatformTextureSettings(new TextureImporterPlatformSettings { name = "Android", overridden = true, maxTextureSize = 1024, format = TextureImporterFormat.Automatic });
    }
}
