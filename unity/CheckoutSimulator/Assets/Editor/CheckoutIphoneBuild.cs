using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

// The stand-alone iPhone build: the whole game in the Unity player, with the game logic (desktop/host.ts bundled
// by scripts/release/build-embedded.ts into Resources/CheckoutGame/game.txt) running inside it in JavaScriptCore
// (Plugins/iOS/CheckoutJS.mm, CheckoutDesktopHost with CHECKOUT_EMBEDDED). No React Native app around it.
// A development build for Lucas's own phone: open the Xcode project, pick the Apple ID team, Run on the iPhone.
//   Menu: Checkout/iPhone/Build Xcode project (stand-alone)    Output: unity/builds/iphone/
public static class CheckoutIphoneBuild
{
    const string Menu = "Checkout/iPhone/Build Xcode project (stand-alone)";
    public const string BundleId = "com.lucasfurini.checkout.dev";

    // Play mode in the Editor behaves like the phone (bigger UI, safe area): set the Game view to a phone resolution.
    const string PreviewMenu = "Checkout/iPhone/Preview phone UI in Play mode";
    [MenuItem(PreviewMenu)]
    static void TogglePreview() { EditorPrefs.SetBool(Checkout.CheckoutScreen.PreviewKey, !EditorPrefs.GetBool(Checkout.CheckoutScreen.PreviewKey, false)); }
    [MenuItem(PreviewMenu, true)]
    static bool TogglePreviewCheck() { UnityEditor.Menu.SetChecked(PreviewMenu, EditorPrefs.GetBool(Checkout.CheckoutScreen.PreviewKey, false)); return true; }

    // Opens the last generated Xcode project (to pick the signing team and press Run).
    [MenuItem("Checkout/iPhone/Open Xcode project")]
    public static void OpenXcode()
    {
        var project = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "builds", "iphone", "Unity-iPhone.xcodeproj"));
        if (!Directory.Exists(project)) throw new Exception("Gere o projeto primeiro: " + Menu);
        EditorUtility.OpenWithDefaultApp(project);
    }

    // ---- TestFlight / App Store (Lucas 23/10: paid Apple Developer account; only the Unity game ships, no React Native) ----
    // Release build with the store bundle id (the same as the Android package), Boot scene first like the Android AAB,
    // the app icon, a new build number every time and the signing team from Player Settings. Output:
    // unity/builds/iphone-store/ -> Xcode: Product › Archive › Distribute App › App Store Connect.
    public const string StoreBundleId = "com.lucasfurini.checkout";
    const string StoreMenu = "Checkout/iPhone/Build for TestFlight";

    [MenuItem(StoreMenu)]
    public static void BuildForTestFlight()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Saia do Play antes de gerar o build do iPhone.");
        if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.iOS)
            throw new Exception("Mude a plataforma para iOS (File › Build Profiles) antes de gerar o build do TestFlight.");
        if (!File.Exists("Assets/Resources/CheckoutGame/game.txt"))
            throw new Exception("Falta Assets/Resources/CheckoutGame/game.txt: rode  bun scripts/release/build-embedded.ts  na raiz do repositório.");
        if (string.IsNullOrEmpty(PlayerSettings.iOS.appleDeveloperTeamID))
            throw new Exception("Preencha o Team ID da conta paga em Player Settings › iOS › Other Settings › Signing Team ID.");
        var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        if (scenes.Length < 2 || !scenes[0].EndsWith("/Boot.unity"))
            throw new Exception("A lista de cenas precisa começar pela cena Boot (Assets/Scenes/Boot.unity) e depois a Supermarket.");
        EditorSceneManager.SaveOpenScenes(); AssetDatabase.SaveAssets();

        CheckoutAppIcon.ApplyIos();
        PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS, StoreBundleId);
        PlayerSettings.iOS.sdkVersion = iOSSdkVersion.DeviceSDK;
        PlayerSettings.iOS.targetOSVersionString = "16.4";
        PlayerSettings.iOS.appleEnableAutomaticSigning = true;
        // iPhone only for the first release: an iPad build would need its own set of App Store screenshots.
        PlayerSettings.iOS.targetDevice = iOSTargetDevice.iPhoneOnly;
        PlayerSettings.productName = "Checkout";
        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
        PlayerSettings.allowedAutorotateToLandscapeLeft = true; PlayerSettings.allowedAutorotateToLandscapeRight = true;
        PlayerSettings.allowedAutorotateToPortrait = false; PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
        // App Store Connect refuses a build number it has already seen (for the same version).
        int.TryParse(PlayerSettings.iOS.buildNumber, out var number);
        PlayerSettings.iOS.buildNumber = (number + 1).ToString();
        AssetDatabase.SaveAssets();

        var out_ = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "builds", "iphone-store"));
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = out_,
            target = BuildTarget.iOS,
            options = BuildOptions.None,
            extraScriptingDefines = new[] { "CHECKOUT_EMBEDDED" },
        });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build do iPhone (TestFlight) falhou: " + report.summary.result);
        Debug.Log($"CHECKOUT_IPHONE_STORE_OK {out_} (version {PlayerSettings.bundleVersion} build {PlayerSettings.iOS.buildNumber})");
        EditorUtility.RevealInFinder(Path.Combine(out_, "Unity-iPhone.xcodeproj"));
    }

    [MenuItem(Menu)]
    public static void Build()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Saia do Play antes de gerar o build do iPhone.");
        if (!File.Exists("Assets/Resources/CheckoutGame/game.txt"))
            throw new Exception("Falta Assets/Resources/CheckoutGame/game.txt: rode  bun scripts/release/build-embedded.ts  na raiz do repositório.");
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        if (scene.path != MarketBuilder.ScenePath) scene = EditorSceneManager.OpenScene(MarketBuilder.ScenePath, OpenSceneMode.Single);
        EditorSceneManager.SaveScene(scene); AssetDatabase.SaveAssets();

        // Settings of this build only; the React Native export (Supermarket menu) keeps its own afterwards.
        var id = PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS);
        var sdk = PlayerSettings.iOS.sdkVersion;
        var orientation = PlayerSettings.defaultInterfaceOrientation;
        var name = PlayerSettings.productName;
        try
        {
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS, BundleId);
            PlayerSettings.iOS.sdkVersion = iOSSdkVersion.DeviceSDK;
            PlayerSettings.iOS.targetOSVersionString = "16.4";
            PlayerSettings.iOS.appleEnableAutomaticSigning = true;
            PlayerSettings.productName = "Checkout";
            // The game is made for a wide screen: landscape only.
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
            PlayerSettings.allowedAutorotateToLandscapeLeft = true; PlayerSettings.allowedAutorotateToLandscapeRight = true;
            PlayerSettings.allowedAutorotateToPortrait = false; PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;
            var out_ = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "builds", "iphone"));
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { MarketBuilder.ScenePath },
                locationPathName = out_,
                target = BuildTarget.iOS,
                options = BuildOptions.Development,
                extraScriptingDefines = new[] { "CHECKOUT_EMBEDDED" },
            });
            if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build do iPhone falhou: " + report.summary.result);
            Debug.Log("CHECKOUT_IPHONE_OK " + out_);
            EditorUtility.RevealInFinder(Path.Combine(out_, "Unity-iPhone.xcodeproj"));
        }
        finally
        {
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.iOS, id);
            PlayerSettings.iOS.sdkVersion = sdk;
            PlayerSettings.defaultInterfaceOrientation = orientation;
            PlayerSettings.productName = name;
        }
    }
}
