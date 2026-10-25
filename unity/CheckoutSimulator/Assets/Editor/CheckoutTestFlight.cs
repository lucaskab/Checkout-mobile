#if UNITY_EDITOR_OSX
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using UnityEditor;
using Debug = UnityEngine.Debug;

// TestFlight from the Mac (Lucas 23/10): after "Checkout/iPhone/Build for TestFlight" generates the Xcode project in
// unity/builds/iphone-store, these menus run Apple's own command-line tool (xcodebuild) with automatic signing and the
// Apple account already signed in to Xcode:
//   1 - Find paid team   reads the teams Xcode knows and puts Lucas's own paid team id in Player Settings
//   2 - Archive          xcodebuild archive  -> builds/iphone-store/Checkout.xcarchive (registers the App ID too)
//   3 - Upload           xcodebuild -exportArchive with destination "upload" -> App Store Connect / TestFlight
// Each step runs in the background and writes builds/iphone-store/testflight-<step>.log, ending with
// "CHECKOUT_TESTFLIGHT_EXIT <code>" (0 = done). The App Store Connect app (bundle id com.lucasfurini.checkout) must
// exist before step 3.
public static class CheckoutTestFlight
{
    static string Root => Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "builds", "iphone-store"));
    static string Archive => Path.Combine(Root, "Checkout.xcarchive");

    [MenuItem("Checkout/iPhone/TestFlight 1 - Find paid team")]
    public static void FindTeam()
    {
        var teams = Teams();
        Directory.CreateDirectory(Root);
        File.WriteAllLines(Path.Combine(Root, "testflight-teams.log"), teams.ConvertAll(t => $"{t.id} | {t.name} | free={t.free}"));
        // Lucas's own paid team (individual, "Lucas Lopes Furini" 282CN823D6), never another company's team that the
        // same Apple ID belongs to (Propstack GmbH).
        var paid = teams.FindAll(t => !t.free && t.name.Contains("Furini"));
        if (paid.Count == 0) { Debug.LogError("CHECKOUT_TESTFLIGHT no paid team in Xcode › Settings › Accounts (" + teams.Count + " teams)"); return; }
        PlayerSettings.iOS.appleDeveloperTeamID = paid[0].id;
        AssetDatabase.SaveAssets();
        Debug.Log($"CHECKOUT_TESTFLIGHT team {paid[0].id} ({paid[0].name})");
    }

    static List<(string id, string name, bool free)> Teams()
    {
        var list = new List<(string, string, bool)>();
        foreach (var key in new[] { "IDEProvisioningTeamByIdentifier", "IDEProvisioningTeams" })
        {
            var text = Capture("/usr/bin/defaults", $"read com.apple.dt.Xcode {key}");
            // old-style plist: { isFreeProvisioningTeam = 0; teamID = ABCDE12345; teamName = "Lucas Furini"; ... }
            foreach (Match block in Regex.Matches(text, @"\{[^{}]*teamID[^{}]*\}"))
            {
                var id = Regex.Match(block.Value, @"teamID\s*=\s*""?([A-Z0-9]{10})""?").Groups[1].Value;
                if (id.Length == 0 || list.Exists(t => t.Item1 == id)) continue;
                var name = Regex.Match(block.Value, @"teamName\s*=\s*""?([^"";]*)""?;").Groups[1].Value;
                var free = Regex.IsMatch(block.Value, @"isFreeProvisioningTeam\s*=\s*1");
                list.Add((id, name, free));
            }
        }
        return list;
    }

    static string Project()
    {
        var workspace = Path.Combine(Root, "Unity-iPhone.xcworkspace");   // CocoaPods (Google Mobile Ads) makes one
        return Directory.Exists(workspace) ? $"-workspace \"{workspace}\"" : $"-project \"{Path.Combine(Root, "Unity-iPhone.xcodeproj")}\"";
    }

    static string Team()
    {
        var team = PlayerSettings.iOS.appleDeveloperTeamID;
        if (string.IsNullOrEmpty(team)) throw new Exception("Rode antes: Checkout/iPhone/TestFlight 1 - Find paid team");
        return team;
    }

    [MenuItem("Checkout/iPhone/TestFlight 2 - Archive")]
    public static void ArchiveBuild()
    {
        if (!Directory.Exists(Path.Combine(Root, "Unity-iPhone.xcodeproj"))) throw new Exception("Gere o projeto primeiro: Checkout/iPhone/Build for TestFlight");
        if (Directory.Exists(Archive)) Directory.Delete(Archive, true);
        Run("archive", $"{Project()} -scheme Unity-iPhone -configuration Release -destination generic/platform=iOS " +
                       $"-archivePath \"{Archive}\" -allowProvisioningUpdates DEVELOPMENT_TEAM={Team()} CODE_SIGN_STYLE=Automatic archive");
    }

    [MenuItem("Checkout/iPhone/TestFlight 3 - Upload")]
    public static void Upload()
    {
        if (!Directory.Exists(Archive)) throw new Exception("Rode antes: Checkout/iPhone/TestFlight 2 - Archive");
        var options = Path.Combine(Root, "ExportOptions.plist");
        File.WriteAllText(options, $@"<?xml version=""1.0"" encoding=""UTF-8""?>
<!DOCTYPE plist PUBLIC ""-//Apple//DTD PLIST 1.0//EN"" ""http://www.apple.com/DTDs/PropertyList-1.0.dtd"">
<plist version=""1.0""><dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>{Team()}</string>
  <key>signingStyle</key><string>automatic</string>
  <key>uploadSymbols</key><true/>
  <key>manageAppVersionAndBuildNumber</key><false/>
</dict></plist>
");
        Run("upload", $"-exportArchive -archivePath \"{Archive}\" -exportOptionsPlist \"{options}\" -exportPath \"{Path.Combine(Root, "export")}\" -allowProvisioningUpdates");
    }

    static void Run(string step, string args)
    {
        Directory.CreateDirectory(Root);
        var logPath = Path.Combine(Root, $"testflight-{step}.log");
        var log = new StreamWriter(logPath, false) { AutoFlush = true };
        log.WriteLine("xcodebuild " + args);
        var p = new Process { StartInfo = new ProcessStartInfo("/usr/bin/xcodebuild", args) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true } };
        p.OutputDataReceived += (_, e) => { if (e.Data != null) lock (log) log.WriteLine(e.Data); };
        p.ErrorDataReceived += (_, e) => { if (e.Data != null) lock (log) log.WriteLine(e.Data); };
        p.Start(); p.BeginOutputReadLine(); p.BeginErrorReadLine();
        Task.Run(() => { p.WaitForExit(); lock (log) { log.WriteLine("CHECKOUT_TESTFLIGHT_EXIT " + p.ExitCode); log.Dispose(); } });
        Debug.Log($"CHECKOUT_TESTFLIGHT {step} started -> {logPath}");
    }

    static string Capture(string file, string args)
    {
        try
        {
            var p = Process.Start(new ProcessStartInfo(file, args) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true });
            var text = p.StandardOutput.ReadToEnd(); p.WaitForExit(); return text;
        }
        catch (Exception e) { Debug.LogWarning("CHECKOUT_TESTFLIGHT " + file + ": " + e.Message); return ""; }
    }
}
#endif
