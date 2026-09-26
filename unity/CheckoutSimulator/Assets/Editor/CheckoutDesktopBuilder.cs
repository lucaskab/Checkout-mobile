using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class CheckoutDesktopBuilder
{
    const string BuildRoot = "../builds/desktop";

    [MenuItem("Checkout/Desktop/Build macOS")]
    public static void BuildMacOS()
    {
        Build(BuildTarget.StandaloneOSX, Path.Combine(BuildRoot, "macOS", "Checkout.app"));
    }

    [MenuItem("Checkout/Desktop/Build Windows x64")]
    public static void BuildWindows()
    {
        Build(BuildTarget.StandaloneWindows64, Path.Combine(BuildRoot, "Windows", "Checkout.exe"));
    }

    public static void BuildAll()
    {
        BuildMacOS();
        BuildWindows();
    }

    static void Build(BuildTarget target, string outputPath)
    {
        if (EditorApplication.isPlaying)
            throw new InvalidOperationException("Stop Play Mode before building the desktop player.");

        var scenes = EditorBuildSettings.scenes
            .Where(scene => scene.enabled)
            .Select(scene => scene.path)
            .ToArray();
        if (scenes.Length == 0)
            throw new InvalidOperationException("Enable the Supermarket scene in Build Settings first.");

        var outputDirectory = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrEmpty(outputDirectory))
            Directory.CreateDirectory(outputDirectory);

        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = outputPath,
            target = target,
            options = BuildOptions.None
        });

        if (report.summary.result != BuildResult.Succeeded)
            throw new InvalidOperationException("Checkout desktop build failed for " + target + ": " + report.summary.result);

        Debug.Log("CHECKOUT_DESKTOP_BUILD_OK " + target + " " + report.summary.outputPath + " bytes=" + report.summary.totalSize);
    }
}
