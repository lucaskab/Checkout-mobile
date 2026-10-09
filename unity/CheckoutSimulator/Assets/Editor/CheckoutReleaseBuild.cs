using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using Debug = UnityEngine.Debug;

// Builds the game to send to testers: Windows x64 (zip) and macOS Apple Silicon + Intel (tar.gz).
// The game store (desktop/host.ts) is compiled with Bun into a stand-alone executable that goes into
// StreamingAssets, so the testers need nothing installed. Release builds hide the Dev tab and the
// map editor (CheckoutDesktopHost.IsRelease). Output: unity/builds/release/.
//   Menu: Checkout/Desktop/Build Release for testers     (tool runner: "menu Checkout/Desktop/Build Release for testers")
public static class CheckoutReleaseBuild
{
    const string Menu = "Checkout/Desktop/Build Release for testers";
    static string Project => Directory.GetCurrentDirectory();
    static string Repo => Path.GetFullPath(Path.Combine(Project, "..", ".."));
    static string Out => Path.GetFullPath(Path.Combine(Project, "..", "builds", "release"));
    static string Hosts => Path.Combine(Out, "hosts");
    static readonly StringBuilder log = new StringBuilder();

    [MenuItem(Menu)]
    public static void BuildAll()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Saia do Play antes de gerar a versão.");
        log.Clear();
        var started = DateTime.Now;
        var stamp = DateTime.Now.ToString("yyyy-MM-dd");
        Directory.CreateDirectory(Out);

        // 1. The game host for each OS.
        Step("Compilando o host do jogo (bun)...");
        var bun = Run("cmd.exe", $"/c bun scripts/release/build-host.ts \"{Hosts}\"", Repo, 600);
        if (bun != 0) throw new Exception("bun build-host falhou (veja Logs/release_result.txt)\n" + log);

        var originalTarget = EditorUserBuildSettings.activeBuildTarget;
        var fullScreen = PlayerSettings.fullScreenMode;
        var resizable = PlayerSettings.resizableWindow;
        var results = new List<string>();
        try
        {
            // Testers open the game full screen (borderless) at their own resolution; Alt+Enter goes windowed.
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.resizableWindow = true;

            // 2. Windows.
            var winDir = Path.Combine(Out, "Windows", "Checkout");
            Clean(winDir);
            Player(BuildTarget.StandaloneWindows64, Path.Combine(winDir, "Checkout.exe"));
            CopyHost("checkout-host-win-x64.exe", Path.Combine(winDir, "Checkout_Data", "StreamingAssets"));
            File.WriteAllText(Path.Combine(winDir, "LEIA-ME.txt"), WindowsReadme, new UTF8Encoding(true));
            var winZip = Path.Combine(Out, $"Checkout-Windows-{stamp}.zip");
            Zip(winDir, "Checkout", winZip);
            results.Add($"Windows: {winZip} ({Mb(winZip)} MB)");

            // 3. macOS (needs "Mac Build Support (Mono)" in Unity Hub).
            if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneOSX))
                results.Add("macOS: PULADO. Instale o módulo \"Mac Build Support (Mono)\" no Unity Hub (Installs > engrenagem > Add modules) e rode de novo.");
            else
            {
                var macDir = Path.Combine(Out, "Mac", "Checkout");
                Clean(macDir);
                SetMacUniversal();
                var app = Path.Combine(macDir, "Checkout.app");
                Player(BuildTarget.StandaloneOSX, app);
                var data = Path.Combine(app, "Contents", "Resources", "Data", "StreamingAssets");
                CopyHost("checkout-host-mac-arm64", data);
                CopyHost("checkout-host-mac-x64", data);
                File.WriteAllText(Path.Combine(macDir, "Instalar Checkout.command"), MacInstaller.Replace("\r\n", "\n"), new UTF8Encoding(false));
                File.WriteAllText(Path.Combine(macDir, "LEIA-ME.txt"), MacReadme, new UTF8Encoding(false));
                var tar = Path.Combine(Out, $"Checkout-Mac-{stamp}.tar.gz");
                TarGz(macDir, "Checkout", tar);
                results.Add($"macOS: {tar} ({Mb(tar)} MB)");
            }
        }
        finally
        {
            PlayerSettings.fullScreenMode = fullScreen;
            PlayerSettings.resizableWindow = resizable;
            if (EditorUserBuildSettings.activeBuildTarget != originalTarget)
            {
                Step($"Voltando o editor para {originalTarget}...");
                EditorUserBuildSettings.SwitchActiveBuildTarget(BuildPipeline.GetBuildTargetGroup(originalTarget), originalTarget);
            }
            var text = $"release {DateTime.Now:yyyy-MM-dd HH:mm} ({(DateTime.Now - started).TotalMinutes:0.0} min)\n{string.Join("\n", results)}\n\n--- log ---\n{log}";
            File.WriteAllText(Path.Combine(Project, "Logs", "release_result.txt"), text);
        }
        Debug.Log("CHECKOUT_RELEASE_OK\n" + string.Join("\n", results));
        EditorUtility.RevealInFinder(Out);
    }

    // ------------------------------------------------------------------ players
    static void Player(BuildTarget target, string path)
    {
        Step($"Gerando {target}...");
        var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        if (scenes.Length == 0) throw new InvalidOperationException("Nenhuma cena ativa em Build Settings.");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = scenes, locationPathName = path, target = target, options = BuildOptions.None });
        if (report.summary.result != BuildResult.Succeeded) throw new Exception($"Build {target} falhou: {report.summary.result}");
        Step($"{target} ok ({report.summary.totalSize / 1048576} MB)");
    }

    static void SetMacUniversal()
    {
        // UnityEditor.OSXStandalone.UserBuildSettings only exists with the Mac module installed: reflection keeps this file compiling without it.
        try
        {
            var type = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("UnityEditor.OSXStandalone.UserBuildSettings")).FirstOrDefault(t => t != null);
            var property = type?.GetProperty("architecture", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            if (property == null) { Step("aviso: não achei UserBuildSettings.architecture (fica a arquitetura padrão)"); return; }
            property.SetValue(null, Enum.Parse(property.PropertyType, "x64ARM64"));
            Step("macOS: Apple Silicon + Intel");
        }
        catch (Exception e) { Step("aviso: arquitetura do Mac não ajustada: " + e.Message); }
    }

    static void CopyHost(string name, string streamingAssets)
    {
        var source = Path.Combine(Hosts, name);
        if (!File.Exists(source)) throw new FileNotFoundException("Host não gerado: " + source);
        Directory.CreateDirectory(streamingAssets);
        File.Copy(source, Path.Combine(streamingAssets, name), true);
    }

    static void Clean(string dir)
    {
        try { if (Directory.Exists(dir)) Directory.Delete(dir, true); }
        catch (Exception e) { throw new Exception($"Não deu para apagar a versão anterior em {dir}. Feche o jogo (Checkout.exe) se estiver aberto e rode de novo. ({e.Message})"); }
        Directory.CreateDirectory(dir);
    }

    // Burst/IL2CPP debug folders are not for players.
    static bool Skip(string relative) => relative.Split('/').Any(part => part.EndsWith("_DoNotShip") || part.EndsWith("_BackUpThisFolder_ButDontShipItWithYourGame"));

    static IEnumerable<string> Files(string dir) =>
        Directory.GetFiles(dir, "*", SearchOption.AllDirectories).OrderBy(f => f, StringComparer.Ordinal);

    static string Relative(string root, string path) => path.Substring(root.Length).TrimStart('\\', '/').Replace('\\', '/');

    // ------------------------------------------------------------------ Windows: zip
    static void Zip(string dir, string rootName, string zipPath)
    {
        Step("Compactando " + Path.GetFileName(zipPath));
        if (File.Exists(zipPath)) File.Delete(zipPath);
        using var stream = new FileStream(zipPath, FileMode.Create);
        using var zip = new ZipArchive(stream, ZipArchiveMode.Create);
        foreach (var file in Files(dir))
        {
            var relative = Relative(dir, file);
            if (Skip(relative)) continue;
            var entry = zip.CreateEntry(rootName + "/" + relative, System.IO.Compression.CompressionLevel.Optimal);
            entry.LastWriteTime = File.GetLastWriteTime(file);
            using var input = File.OpenRead(file);
            using var output = entry.Open();
            input.CopyTo(output);
        }
    }

    // ------------------------------------------------------------------ macOS: tar.gz keeps the executable bits
    // (a zip made on Windows would lose them and the app would not open).
    static bool Executable(string relative)
    {
        var name = Path.GetFileName(relative);
        return relative.Contains("/Contents/MacOS/") || name.StartsWith("checkout-host-mac") || name.EndsWith(".command") || name.EndsWith(".dylib");
    }

    static void TarGz(string dir, string rootName, string tarPath)
    {
        Step("Compactando " + Path.GetFileName(tarPath));
        if (File.Exists(tarPath)) File.Delete(tarPath);
        using var stream = new FileStream(tarPath, FileMode.Create);
        using var gzip = new GZipStream(stream, System.IO.Compression.CompressionLevel.Optimal);
        var dirs = new SortedSet<string>(StringComparer.Ordinal) { rootName };
        var files = new List<(string path, string name)>();
        foreach (var file in Files(dir))
        {
            var relative = Relative(dir, file);
            if (Skip(relative)) continue;
            var name = rootName + "/" + relative;
            for (var slash = name.LastIndexOf('/'); slash > 0; slash = name.LastIndexOf('/', slash - 1)) dirs.Add(name.Substring(0, slash));
            files.Add((file, name));
        }
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        foreach (var d in dirs) TarHeader(gzip, d + "/", 0, Convert.ToInt32("755", 8), '5', now);
        var buffer = new byte[81920];
        foreach (var (path, name) in files)
        {
            var length = new FileInfo(path).Length;
            TarHeader(gzip, name, length, Convert.ToInt32(Executable(name) ? "755" : "644", 8), '0', now);
            using (var input = File.OpenRead(path))
            {
                int read;
                while ((read = input.Read(buffer, 0, buffer.Length)) > 0) gzip.Write(buffer, 0, read);
            }
            var pad = (int)((512 - length % 512) % 512);
            if (pad > 0) gzip.Write(new byte[pad], 0, pad);
        }
        gzip.Write(new byte[1024], 0, 1024);
    }

    static void TarHeader(Stream output, string name, long size, int mode, char type, long mtime)
    {
        var header = new byte[512];
        var bytes = Encoding.UTF8.GetBytes(name);
        string prefix = "", shortName = name;
        if (bytes.Length > 100)
        {
            // ustar: split the path into prefix (<=155) and name (<=100) at a slash.
            var split = -1;
            for (var i = name.IndexOf('/'); i >= 0 && i < name.Length - 1; i = name.IndexOf('/', i + 1))
                if (Encoding.UTF8.GetByteCount(name.Substring(i + 1)) <= 100 && Encoding.UTF8.GetByteCount(name.Substring(0, i)) <= 155) { split = i; break; }
            if (split < 0) throw new Exception("Caminho longo demais para tar: " + name);
            prefix = name.Substring(0, split); shortName = name.Substring(split + 1);
        }
        void Put(int offset, int length, string value) { var b = Encoding.UTF8.GetBytes(value); Array.Copy(b, 0, header, offset, Math.Min(b.Length, length)); }
        void Octal(int offset, int length, long value) => Put(offset, length, Convert.ToString(value, 8).PadLeft(length - 1, '0') + "\0");
        Put(0, 100, shortName);
        Octal(100, 8, mode);
        Octal(108, 8, 501);
        Octal(116, 8, 20);
        Octal(124, 12, size);
        Octal(136, 12, mtime);
        for (var i = 148; i < 156; i++) header[i] = (byte)' ';
        header[156] = (byte)type;
        Put(257, 6, "ustar\0");
        Put(263, 2, "00");
        Put(265, 32, "tester");
        Put(297, 32, "staff");
        Put(345, 155, prefix);
        long sum = 0; foreach (var b in header) sum += b;
        Put(148, 8, Convert.ToString(sum, 8).PadLeft(6, '0') + "\0 ");
        output.Write(header, 0, 512);
    }

    // ------------------------------------------------------------------ helpers
    static void Step(string text)
    {
        log.AppendLine($"[{DateTime.Now:HH:mm:ss}] {text}");
        Debug.Log("CHECKOUT_RELEASE " + text);
    }

    static int Run(string exe, string args, string cwd, int timeoutSeconds)
    {
        var info = new ProcessStartInfo(exe, args) { WorkingDirectory = cwd, UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
        using var process = new Process { StartInfo = info };
        var output = new StringBuilder();
        process.OutputDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
        process.ErrorDataReceived += (_, e) => { if (e.Data != null) lock (output) output.AppendLine(e.Data); };
        process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
        if (!process.WaitForExit(timeoutSeconds * 1000)) { try { process.Kill(); } catch { } lock (output) log.Append(output); return -1; }
        process.WaitForExit();
        lock (output) log.Append(output);
        return process.ExitCode;
    }

    static string Mb(string path) => (new FileInfo(path).Length / 1048576.0).ToString("0");

    // ------------------------------------------------------------------ texts for the testers
    const string WindowsReadme =
@"CHECKOUT - Supermercado Simulator (versão de teste)

Como jogar:
1. Clique com o botão direito no .zip e escolha ""Extrair tudo"" (não rode de dentro do zip).
2. Abra a pasta Checkout e dê dois cliques em Checkout.exe.
3. Se o Windows mostrar ""O Windows protegeu o seu PC"", clique em ""Mais informações"" e depois em ""Executar assim mesmo"".
   (Aparece porque o jogo ainda não tem assinatura digital.)

Dicas:
- Alt+Enter alterna entre tela cheia e janela. Alt+F4 fecha o jogo.
- O progresso fica salvo no seu computador e continua de onde parou.

Depois conte o que achou: o que foi divertido, o que ficou confuso, onde travou ou ficou chato.
";

    const string MacReadme =
@"CHECKOUT - Supermercado Simulator (versão de teste)

Como instalar (só na primeira vez):
1. Dê dois cliques no arquivo .tar.gz para extrair. Vai aparecer a pasta Checkout.
2. Abra o Terminal (Cmd+Espaço, digite Terminal, Enter).
3. Digite  bash  e um espaço, arraste o arquivo ""Instalar Checkout.command"" para a janela do Terminal e aperte Enter.
   Ele libera o jogo no macOS (o jogo ainda não tem assinatura da Apple) e abre o Checkout.
4. Se quiser, arraste o Checkout.app para a pasta Aplicativos (antes do passo 3, ou rode o passo 3 de novo depois).

Das próximas vezes é só abrir o Checkout.app.

Dicas:
- Cmd+Q fecha o jogo.
- O progresso fica salvo no seu Mac e continua de onde parou.

Depois conte o que achou: o que foi divertido, o que ficou confuso, onde travou ou ficou chato.
";

    const string MacInstaller =
@"#!/bin/bash
# Libera o Checkout no macOS: tira a quarentena do download e assina o app localmente (ad-hoc).
cd ""$(dirname ""$0"")""
APP=""Checkout.app""
[ -d ""/Applications/Checkout.app"" ] && [ ! -d ""$APP"" ] && APP=""/Applications/Checkout.app""
if [ ! -d ""$APP"" ]; then echo ""Não achei o Checkout.app ao lado deste arquivo.""; exit 1; fi
echo ""Liberando $APP ...""
xattr -cr ""$APP""
chmod +x ""$APP""/Contents/MacOS/* ""$APP""/Contents/Resources/Data/StreamingAssets/checkout-host-mac-* 2>/dev/null
# Every Mach-O must carry a signature on Apple Silicon: sign the inner pieces first, then the app.
find ""$APP"" -type f \( -name '*.dylib' -o -name '*.so' -o -perm -u+x \) -print0 | while IFS= read -r -d '' f; do codesign --force --sign - ""$f"" >/dev/null 2>&1; done
find ""$APP"" -type d -name '*.bundle' -print0 | while IFS= read -r -d '' b; do codesign --force --sign - ""$b"" >/dev/null 2>&1; done
codesign --force --sign - ""$APP"" >/dev/null 2>&1 || codesign --force --deep --sign - ""$APP""
echo ""Pronto! Abrindo o Checkout...""
open ""$APP""
";
}
