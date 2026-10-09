using UnityEditor;

// The rigged event props and the event moves (Assets/Resources/EventRigs, built by ArtSource/event_rigs) are
// played with the legacy Animation component, like the game's characters: import them as Legacy, keep every
// key (wheels and the prize wheel spin fast), no materials (the game paints them with the baked atlases).
public sealed class CheckoutEventRigImport : AssetPostprocessor {
 const string Folder = "Assets/Resources/EventRigs";

 static bool IsRig(string path) => path.Replace('\\', '/').StartsWith(Folder + "/") && path.EndsWith(".fbx", System.StringComparison.OrdinalIgnoreCase);

 void OnPreprocessModel() {
  if (!IsRig(assetPath)) return;
  Configure((ModelImporter)assetImporter);
 }

 static bool Configure(ModelImporter importer) {
  bool changed = importer.animationType != ModelImporterAnimationType.Legacy || !importer.importAnimation
   || importer.animationCompression != ModelImporterAnimationCompression.Off
   || importer.materialImportMode != ModelImporterMaterialImportMode.None;
  importer.animationType = ModelImporterAnimationType.Legacy;
  importer.importAnimation = true;
  importer.animationCompression = ModelImporterAnimationCompression.Off;
  importer.materialImportMode = ModelImporterMaterialImportMode.None;
  importer.importCameras = false;
  importer.importLights = false;
  return changed;
 }

 // Rigs imported before this importer existed are switched once when the editor loads.
 [InitializeOnLoadMethod]
 static void FixExisting() {
  EditorApplication.delayCall += () => {
   if (!AssetDatabase.IsValidFolder(Folder)) return;
   foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { Folder })) {
    var path = AssetDatabase.GUIDToAssetPath(guid);
    if (AssetImporter.GetAtPath(path) is ModelImporter importer && Configure(importer)) importer.SaveAndReimport();
   }
  };
 }
}
