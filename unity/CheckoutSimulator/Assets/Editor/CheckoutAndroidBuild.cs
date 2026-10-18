using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

// The stand-alone Android build for Google Play: the whole game in the Unity player, with the game logic
// (desktop/host.ts bundled by scripts/release/build-embedded.ts into Resources/CheckoutGame/game.txt) running inside
// it in QuickJS (Plugins/Android/QuickJS/CheckoutJS.c, CheckoutDesktopHost with CHECKOUT_EMBEDDED). No React Native
// app around it. Signed with the upload key set in Player Settings › Publishing Settings (the passwords are typed
// there by hand; Unity forgets them when it restarts).
//   Menu: Checkout/Android/Build AAB (Google Play)    Output: unity/builds/play/checkout-<version>-<code>.aab
public static class CheckoutAndroidBuild
{
    const string Menu = "Checkout/Android/Build AAB (Google Play)";
    const string Define = "CHECKOUT_EMBEDDED";
    static NamedBuildTarget Android => NamedBuildTarget.Android;

    [MenuItem(Menu)]
    public static void Build()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Saia do Play antes de gerar o build do Android.");
        if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
            throw new Exception("Mude a plataforma para Android (File › Build Profiles) antes de gerar o AAB.");
        if (!File.Exists("Assets/Resources/CheckoutGame/game.txt"))
            throw new Exception("Falta Assets/Resources/CheckoutGame/game.txt: rode  bun scripts/release/build-embedded.ts  na raiz do repositório.");
        if (!PlayerSettings.Android.useCustomKeystore || string.IsNullOrEmpty(PlayerSettings.Android.keystorePass) || string.IsNullOrEmpty(PlayerSettings.Android.keyaliasPass))
            throw new Exception("Digite as senhas da keystore em Player Settings › Publishing Settings (o Unity esquece ao reiniciar).");

        var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        if (scenes.Length < 2 || !scenes[0].EndsWith("/Boot.unity"))
            throw new Exception("A lista de cenas precisa começar pela cena Boot (Assets/Scenes/Boot.unity) e depois a Supermarket.");

        // The game logic inside the player: kept in the Android defines, so a build from Build Profiles has it too.
        EnsureDefine();
        EditorUserBuildSettings.buildAppBundle = true;
        EditorUserBuildSettings.exportAsGoogleAndroidProject = false;
        PlayerSettings.Android.splitApplicationBinary = true;

        // Google Play refuses a version code it has already seen.
        PlayerSettings.Android.bundleVersionCode += 1;
        var code = PlayerSettings.Android.bundleVersionCode;
        var folder = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "builds", "play"));
        Directory.CreateDirectory(folder);
        var output = Path.Combine(folder, $"checkout-{PlayerSettings.bundleVersion}-{code}.aab");

        CheckoutSizeReport.Optimize();   // texture/mesh settings that keep the download small
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = output,
            target = BuildTarget.Android,
            // LZ4HC: the game data stays compressed on the phone (with None it was stored raw: 390 MB download
            // became 1.2 GB installed). Loading reads LZ4 chunks, which costs next to nothing.
            options = BuildOptions.CompressWithLz4HC,
        });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception("Build do Android falhou: " + report.summary.result);
        Debug.Log($"CHECKOUT_ANDROID_AAB_OK {output} (version code {code})");
        CheckoutSizeReport.Run();
        EditorUtility.RevealInFinder(output);
    }

    static void EnsureDefine()
    {
        PlayerSettings.GetScriptingDefineSymbols(Android, out var defines);
        if (defines.Contains(Define)) return;
        PlayerSettings.SetScriptingDefineSymbols(Android, defines.Append(Define).ToArray());
    }
}
