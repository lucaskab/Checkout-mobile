#if UNITY_IOS
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditor.iOS.Xcode;

// The iPhone's Xcode project gets the "Sign in with Apple" capability (entitlement com.apple.developer.applesignin),
// which Plugins/iOS/CheckoutSignIn.mm needs (Lucas 19/10: the App Store asks for it next to the Google login).
// The App ID in the Apple Developer account must have "Sign in with Apple" turned on too (automatic signing does it).
public static class CheckoutIosSignIn
{
    [PostProcessBuild(100)]
    public static void OnPostprocessBuild(BuildTarget target, string path)
    {
        if (target != BuildTarget.iOS) return;
        var projectPath = PBXProject.GetPBXProjectPath(path);
        var project = new PBXProject();
        project.ReadFromFile(projectPath);
        var manager = new ProjectCapabilityManager(projectPath, "Unity-iPhone/Checkout.entitlements", null, project.GetUnityMainTargetGuid());
        manager.AddSignInWithApple();
        manager.WriteToFile();
    }
}
#endif
