using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

// What the last player build is made of (Lucas 18/10: the Android install is 1.2 GB): every packed asset from the
// last build report, grouped by type and by folder, biggest first. Output: Logs/size_report.txt.
public static class CheckoutSizeReport {
    [MenuItem("Checkout/Android/Size report")]
    public static void Run() {
        BuildReport report = null;
        var objs = UnityEditorInternal.InternalEditorUtility.LoadSerializedFileAndForget("Library/LastBuild.buildreport");
        foreach (var o in objs) if (o is BuildReport r) report = r;
        var sb = new StringBuilder();
        if (report == null) { File.WriteAllText("Logs/size_report.txt", "no report"); return; }
        sb.AppendLine($"platform {report.summary.platform} total {report.summary.totalSize / 1048576f:0.0} MB result {report.summary.result}");
        var items = report.packedAssets.SelectMany(p => p.contents.Select(c => (file: p.shortPath, path: c.sourceAssetPath, type: c.type != null ? c.type.Name : "?", size: (long)c.packedSize))).ToList();
        sb.AppendLine($"packed total {items.Sum(i => i.size) / 1048576f:0.0} MB in {items.Count} entries");
        sb.AppendLine("== by type");
        foreach (var g in items.GroupBy(i => i.type).OrderByDescending(g => g.Sum(i => i.size)).Take(20)) sb.AppendLine($"{g.Sum(i => i.size) / 1048576f,9:0.0} MB  {g.Count(),6}  {g.Key}");
        sb.AppendLine("== by folder");
        foreach (var g in items.GroupBy(i => Folder(i.path)).OrderByDescending(g => g.Sum(i => i.size)).Take(40)) sb.AppendLine($"{g.Sum(i => i.size) / 1048576f,9:0.0} MB  {g.Count(),6}  {g.Key}");
        sb.AppendLine("== by bundle file");
        foreach (var g in items.GroupBy(i => i.file).OrderByDescending(g => g.Sum(i => i.size)).Take(15)) sb.AppendLine($"{g.Sum(i => i.size) / 1048576f,9:0.0} MB  {g.Key}");
        sb.AppendLine("== biggest assets");
        foreach (var g in items.GroupBy(i => i.path).OrderByDescending(g => g.Sum(i => i.size)).Take(120)) {
            var first = g.First(); string extra = "";
            var ti = AssetImporter.GetAtPath(g.Key) as TextureImporter;
            if (ti != null) { var ps = ti.GetPlatformTextureSettings("Android"); var t = AssetDatabase.LoadAssetAtPath<Texture>(g.Key); extra = $" tex {(t ? t.width + "x" + t.height : "?")} max {ti.maxTextureSize} fmt {(ps.overridden ? ps.format.ToString() : "default")} comp {ti.textureCompression} mip {ti.mipmapEnabled} readable {ti.isReadable}"; }
            sb.AppendLine($"{g.Sum(i => i.size) / 1048576f,8:0.00} MB  {first.type,-14} {g.Key}{extra}");
        }
        File.WriteAllText("Logs/size_report.txt", sb.ToString());
        Debug.Log("CHECKOUT_SIZE done");
    }
    // Same pictures, smaller files (Lucas 18/10: "preciso que o tamanho fique otimizado", but never uglier assets):
    //  - 2D screens and icons (CheckoutDesktop): ASTC 4x4 on Android (high quality block compression; some were
    //    stored at ~3 bytes per pixel) and no mipmaps (they are drawn at screen size, mips only added a third);
    //  - textures still uncompressed on Android (the city tileset, the market atlas): ASTC 4x4;
    //  - meshes: unused vertex channels stripped and mesh data optimized.
    // Resolution is never reduced here.
    [MenuItem("Checkout/Android/Optimize build size")]
    public static void Optimize() {
        PlayerSettings.stripUnusedMeshComponents = true;
        PlayerSettings.mipStripping = false;
        int changed = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets" })) {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            if (path.Contains("/Editor/") || path.StartsWith("Assets/Art/AppIcon")) continue;
            var ti = AssetImporter.GetAtPath(path) as TextureImporter;
            if (ti == null || ti.textureType == TextureImporterType.NormalMap) continue;
            bool ui = path.StartsWith("Assets/Resources/CheckoutDesktop/");
            bool raw = ti.textureCompression == TextureImporterCompression.Uncompressed;
            if (!ui && !raw) continue;
            var ps = ti.GetPlatformTextureSettings("Android");
            bool dirty = false;
            if (!ps.overridden || ps.format != TextureImporterFormat.ASTC_4x4) {
                ps.overridden = true; ps.format = TextureImporterFormat.ASTC_4x4; ps.maxTextureSize = ti.maxTextureSize;
                ps.compressionQuality = 100; ti.SetPlatformTextureSettings(ps); dirty = true;
            }
            if (ui && ti.mipmapEnabled) { ti.mipmapEnabled = false; dirty = true; }
            if (dirty) { ti.SaveAndReimport(); changed++; }
        }
        Debug.Log("CHECKOUT_SIZE optimize textures changed=" + changed);
        WorldCap(1024);   // 3D world textures at 1024 on Android (approved by Lucas 18/10 on side-by-side shots)
    }

    // The 3D world's textures capped at 1024 on Android (2D screens untouched); approved by Lucas 18/10 after comparing
    // shots. "2048" puts them back exactly as they were.
    [MenuItem("Checkout/Android/World textures 1024")] public static void World1024() => WorldCap(1024);
    [MenuItem("Checkout/Android/World textures 2048")] public static void World2048() => WorldCap(0);
    static void WorldCap(int cap) {
        int changed = 0;
        AssetDatabase.StartAssetEditing();
        try {
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets" })) {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.Contains("/Editor/") || path.StartsWith("Assets/Art/AppIcon") || path.StartsWith("Assets/Resources/CheckoutDesktop/")) continue;
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                if (ti == null || ti.maxTextureSize <= 1024) continue;
                var ps = ti.GetPlatformTextureSettings("Android");
                int want = cap > 0 ? cap : ti.maxTextureSize;
                if (ps.overridden && ps.maxTextureSize == want) continue;
                if (cap == 0 && !ps.overridden) continue;
                if (!ps.overridden) { ps.overridden = true; ps.format = TextureImporterFormat.Automatic; }
                ps.maxTextureSize = want;
                ti.SetPlatformTextureSettings(ps); ti.SaveAndReimport(); changed++;
            }
        } finally { AssetDatabase.StopAssetEditing(); }
        Debug.Log($"CHECKOUT_SIZE world cap {cap} changed={changed}");
        File.WriteAllText("Logs/world_cap.txt", $"cap {cap} changed {changed}");
    }

    static string Folder(string p) {
        if (string.IsNullOrEmpty(p)) return "(built-in)";
        var parts = p.Replace('\\', '/').Split('/');
        return string.Join("/", parts.Take(Mathf.Min(parts.Length - 1, 4)));
    }
}
