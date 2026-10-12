using System.Linq;
using UnityEditor;
using UnityEngine;

// Import settings of the construction crew (Assets/Resources/CheckoutCrew, see CheckoutCrew) and of the motoboy on
// the bike (Resources/CheckoutDelivery/delivery_rider): built by ArtSource/NPCs, they come in with the same settings
// as the market's characters — Legacy animation (CheckoutWorksScene plays clips by name), the clip names without
// the Blender rig prefix ("Worker_ConstructionM_Rig|Hammer" -> "Hammer"), looping work and walk cycles.
public class CheckoutCrewImport : AssetPostprocessor
{
    const string Crew = "Assets/Resources/CheckoutCrew/";
    const string Rider = "Assets/Resources/CheckoutDelivery/delivery_rider";
    static readonly string[] Loops = { "Idle", "Walking", "CarryIdle", "CarryWalking", "Hammer", "Sledge" };

    void OnPreprocessModel()
    {
        var importer = (ModelImporter)assetImporter;
        if (assetPath.StartsWith(Crew))
        {
            importer.animationType = ModelImporterAnimationType.Legacy;
            importer.importAnimation = true; importer.importCameras = false; importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;     // CheckoutCrew assigns Resources/CheckoutCrew/<name>.mat
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.useFileScale = true; importer.globalScale = 1;
        }
        else if (assetPath.StartsWith(Rider))
        {
            importer.animationType = ModelImporterAnimationType.None;
            importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
            importer.useFileScale = true; importer.globalScale = 1;
        }
    }

    void OnPreprocessAnimation()
    {
        if (!assetPath.StartsWith(Crew)) return;
        var importer = (ModelImporter)assetImporter;
        var clips = importer.defaultClipAnimations;
        foreach (var clip in clips)
        {
            var name = clip.name.Contains("|") ? clip.name.Substring(clip.name.LastIndexOf('|') + 1) : clip.name;
            clip.name = name;
            clip.loopTime = Loops.Contains(name);
            clip.wrapMode = clip.loopTime ? WrapMode.Loop : WrapMode.ClampForever;
        }
        importer.clipAnimations = clips;
    }
}
