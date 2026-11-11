using System.IO;
using UnityEditor;
using UnityEngine;

// Sets the app version (the "1.0.1" the stores show) from Logs/set_version.txt, so the tool runner can bump it
// without the Player Settings window (`menu Checkout/Release/Set version from Logs file`). The build numbers stay with
// the build menus (iPhone +1 per TestFlight build, Android versionCode +1 per AAB).
public static class CheckoutVersionTool
{
    const string File_ = "Logs/set_version.txt";

    // The tool runner refuses menu names with parentheses: the Android build under a plain name.
    [MenuItem("Checkout/Release/Build Android AAB")]
    static void BuildAndroid() => CheckoutAndroidBuild.Build();

    [MenuItem("Checkout/Release/Set version from Logs file")]
    static void SetFromFile()
    {
        if (!File.Exists(File_)) { Debug.LogError($"CHECKOUT_VERSION no {File_}"); return; }
        var v = File.ReadAllText(File_).Trim();
        if (!System.Text.RegularExpressions.Regex.IsMatch(v, @"^\d+(\.\d+){1,2}$")) { Debug.LogError($"CHECKOUT_VERSION bad '{v}'"); return; }
        var before = PlayerSettings.bundleVersion;
        PlayerSettings.bundleVersion = v;
        AssetDatabase.SaveAssets();
        Debug.Log($"CHECKOUT_VERSION {before} -> {v} (iPhone build {PlayerSettings.iOS.buildNumber}, Android code {PlayerSettings.Android.bundleVersionCode})");
        File.WriteAllText("Logs/version_result.txt", $"{before} -> {v}\niphone build {PlayerSettings.iOS.buildNumber}\nandroid code {PlayerSettings.Android.bundleVersionCode}\n");
    }
}

// (touched 08/11 to reload the editor scripts)
