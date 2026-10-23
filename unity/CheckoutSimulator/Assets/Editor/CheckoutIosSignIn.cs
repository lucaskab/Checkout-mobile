#if UNITY_IOS
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditor.iOS.Xcode;

// The iPhone's Xcode project gets the "Sign in with Apple" capability (entitlement com.apple.developer.applesignin),
// which Plugins/iOS/CheckoutSignIn.mm needs (Lucas 19/10: the App Store asks for it next to the Google login).
// The App ID in the Apple Developer account must have "Sign in with Apple" turned on too (automatic signing does it).
// 23/10 (TestFlight): also the In-App Purchase capability (diamond store) and ITSAppUsesNonExemptEncryption = NO in
// Info.plist (the game only uses HTTPS), so App Store Connect does not hold every build for the export question.
public static class CheckoutIosSignIn
{
    // 23/10: the Google Mobile Ads dependency list adds CocoaPods' old GitHub index (source
    // 'https://github.com/CocoaPods/Specs'), which makes the first "pod install" clone several GB into ~/.cocoapods and
    // filled the Mac's disk. The CDN source (https://cdn.cocoapods.org/) has the same pods: keep only that one.
    // Runs between the External Dependency Manager writing the Podfile (order 40) and running pod install (order 50).
    [PostProcessBuild(45)]
    public static void UseCocoaPodsCdnOnly(BuildTarget target, string path)
    {
        if (target != BuildTarget.iOS) return;
        var podfile = System.IO.Path.Combine(path, "Podfile");
        if (!System.IO.File.Exists(podfile)) return;
        var lines = System.IO.File.ReadAllLines(podfile);
        var kept = System.Array.FindAll(lines, l => !l.Contains("github.com/CocoaPods/Specs"));
        if (kept.Length != lines.Length) System.IO.File.WriteAllLines(podfile, kept);
    }

    [PostProcessBuild(100)]
    public static void OnPostprocessBuild(BuildTarget target, string path)
    {
        if (target != BuildTarget.iOS) return;
        var projectPath = PBXProject.GetPBXProjectPath(path);
        var project = new PBXProject();
        project.ReadFromFile(projectPath);
        var manager = new ProjectCapabilityManager(projectPath, "Unity-iPhone/Checkout.entitlements", null, project.GetUnityMainTargetGuid());
        manager.AddSignInWithApple();
        manager.AddInAppPurchase();
        manager.WriteToFile();

        var plistPath = System.IO.Path.Combine(path, "Info.plist");
        var plist = new PlistDocument();
        plist.ReadFromFile(plistPath);
        plist.root.SetBoolean("ITSAppUsesNonExemptEncryption", false);
        plist.WriteToFile(plistPath);
    }
}
#endif
