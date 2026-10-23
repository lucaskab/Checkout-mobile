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
                    if (name.Contains("Adaptive")) icon.SetTextures(bg, fg);   // Unity's adaptive layers: 0 background, 1 foreground (fg first showed only the blue)
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

    // iPhone (23/10, TestFlight): every iOS icon slot gets the 1024 art (Unity scales it; RGB, no alpha, as the App
    // Store asks). Includes the 1024 marketing icon (IconKind.Store) that App Store Connect validates on upload.
    [MenuItem("Checkout/iPhone/Apply app icons")]
    public static void ApplyIos() {
        var big = Load("app_icon_1024.png");
        if (!big) { Debug.LogError("CHECKOUT_ICON missing " + Dir + "/app_icon_1024.png"); return; }
        foreach (var kind in new[] { IconKind.Application, IconKind.Spotlight, IconKind.Settings, IconKind.Notification, IconKind.Store }) {
            var sizes = PlayerSettings.GetIconSizes(NamedBuildTarget.iOS, kind);
            if (sizes == null || sizes.Length == 0) continue;
            PlayerSettings.SetIcons(NamedBuildTarget.iOS, Enumerable.Repeat(big, sizes.Length).ToArray(), kind);
        }
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_ICON iOS done");
    }

    // the tool runner only takes plain names (no parentheses): the Play build under a short name, icons first
    [MenuItem("Checkout/Android/Build AAB for Play")]
    public static void BuildForPlay() { Apply(); EditorApplication.ExecuteMenuItem("Checkout/Android/Build AAB (Google Play)"); }

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
