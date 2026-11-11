using System.IO;
using UnityEditor;
using UnityEditor.Build.Player;
using UnityEngine;

// Compiles the game's scripts as a phone build would (UNITY_ANDROID / UNITY_IOS without UNITY_EDITOR), without
// building: the code behind "#if ... && !UNITY_EDITOR" (notifications, Firebase, sign-in, store) never compiles in the
// Editor, so a mistake there only shows when a build is made. Result in Logs/player_compile.txt.
public static class CheckoutPlayerCompileCheck
{
    // (the same without brackets: the tool runner takes plain names only)
    [MenuItem("Checkout/QA/Player compile check")]
    public static void RunPlain() => Run();

    [MenuItem("Checkout/QA/Compile player scripts (Android and iOS)")]
    public static void Run()
    {
        var report = new System.Text.StringBuilder();
        foreach (var (group, target) in new[] { (BuildTargetGroup.Android, BuildTarget.Android), (BuildTargetGroup.iOS, BuildTarget.iOS) })
        {
            var settings = new ScriptCompilationSettings { group = group, target = target, options = ScriptCompilationOptions.None };
            var output = Path.Combine("Temp", "PlayerCompile", target.ToString());
            Directory.CreateDirectory(output);
            var result = PlayerBuildInterface.CompilePlayerScripts(settings, output);
            bool ok = result.assemblies != null && result.assemblies.Contains("Assembly-CSharp.dll");
            report.AppendLine($"{target}: {(ok ? "OK" : "FAILED")} ({result.assemblies?.Count ?? 0} assemblies)");
        }
        File.WriteAllText(Path.Combine("Logs", "player_compile.txt"), report.ToString());
        Debug.Log("CHECKOUT_PLAYER_COMPILE\n" + report);
    }
}
