using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

// The game's app icon (Lucas 18/10): the C with the basket, on navy. Android gets the full icon for the legacy and round
// launchers, and an adaptive icon (navy background + the art at 66% in the foreground, so the launcher's circle keeps it
// whole). The 1024 PNGs live in Assets/Art/AppIcon; the store listing uses the 512 copy outside the project.
public static class CheckoutAppIcon {
    const string Dir = "Assets/Art/AppIcon";

    [MenuItem("Checkout/Android/Apply app icons")]
    public static void Apply() {
        var big = Load("app_icon_1024.png");
        var fg = Load("app_icon_fg_1024.png");
        var bg = Load("app_icon_bg_1024.png");
        if (!big || !fg || !bg) { Debug.LogError("CHECKOUT_ICON missing textures in " + Dir); return; }
        foreach (var kind in PlayerSettings.GetSupportedIconKinds(NamedBuildTarget.Android)) {
            var name = kind.ToString();
            Debug.Log("CHECKOUT_ICON kind " + name);
            if (!name.Contains("Adaptive") && !name.Contains("Legacy") && !name.Contains("Round")) continue;
            try {
                var icons = PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android, kind);
                if (icons == null || icons.Length == 0) { Debug.LogWarning("CHECKOUT_ICON no slots for " + name); continue; }
                foreach (var icon in icons) {
                    if (name.Contains("Adaptive")) icon.SetTextures(fg, bg);   // layer 0 foreground, layer 1 background
                    else icon.SetTextures(big);
                }
                PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android, kind, icons);
                Debug.Log("CHECKOUT_ICON set " + name + " slots=" + icons.Length);
            } catch (Exception e) {
                Debug.LogError("CHECKOUT_ICON " + name + ": " + e.Message);
            }
        }
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_ICON done");
    }

    static Texture2D Load(string file) {
        var path = Dir + "/" + file;
        var imp = AssetImporter.GetAtPath(path) as TextureImporter;
        if (imp == null) { AssetDatabase.ImportAsset(path); imp = AssetImporter.GetAtPath(path) as TextureImporter; }
        if (imp != null) {
            imp.textureType = TextureImporterType.Default;
            imp.sRGBTexture = true;
            imp.mipmapEnabled = false;
            imp.isReadable = false;
            imp.npotScale = TextureImporterNPOTScale.None;
            imp.maxTextureSize = 1024;
            imp.SaveAndReimport();
        }
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }
}
