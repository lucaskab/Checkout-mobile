using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

// Moves assets the game no longer uses out of Assets/ (so out of the build: everything under Resources ships whether
// used or not) into <project>/_Unused/, keeping their .meta files. Nothing is deleted: "Restore" puts them back with
// the same GUIDs. Audit of Oct 2026: the v1 event props (Resources/EventProps, replaced by EventProps2 except the
// market portal and steps), two unused delivery backdrops, temporary decor sketches and Unity's scene backups.
public static class CheckoutUnusedAssets
{
    const string Store = "_Unused";
    const string Manifest = Store + "/moved.txt";
    static readonly string[] KeepEventProps = { "MarketPortal", "MarketSteps" };

    [MenuItem("Supermarket/Performance/Move unused assets out of the build")]
    public static void Move()
    {
        var list = Candidates();
        long bytes = list.Sum(p => new FileInfo(p).Length);
        if (!EditorUtility.DisplayDialog("Move unused assets", $"Move {list.Count} files ({bytes / 1048576f:0.0} MB) to {Store}/? Nothing is deleted; Supermarket > Performance > Restore puts them back.", "Move", "Cancel")) return;
        var moved = new List<string>();
        foreach (var path in list)
        {
            string target = Path.Combine(Store, path);
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            if (File.Exists(target)) File.Delete(target);
            File.Move(path, target);
            if (File.Exists(path + ".meta")) { if (File.Exists(target + ".meta")) File.Delete(target + ".meta"); File.Move(path + ".meta", target + ".meta"); }
            moved.Add(path);
        }
        // Folders left empty (and their .meta) go too.
        foreach (var dir in moved.Select(Path.GetDirectoryName).Distinct().OrderByDescending(d => d.Length))
            if (Directory.Exists(dir) && !Directory.EnumerateFileSystemEntries(dir).Any())
            {
                string target = Path.Combine(Store, dir);
                Directory.CreateDirectory(Path.GetDirectoryName(target));
                Directory.Delete(dir);
                if (File.Exists(dir + ".meta")) { if (File.Exists(target + ".meta")) File.Delete(target + ".meta"); File.Move(dir + ".meta", target + ".meta"); }
            }
        File.AppendAllLines(Manifest, moved);
        AssetDatabase.Refresh();
        Debug.Log($"CHECKOUT_UNUSED moved {moved.Count} files ({bytes / 1048576f:0.0} MB) to {Store}/ (list in {Manifest})");
    }

    [MenuItem("Supermarket/Performance/Restore assets moved out of the build")]
    public static void Restore()
    {
        if (!File.Exists(Manifest)) { Debug.Log("CHECKOUT_UNUSED nothing to restore"); return; }
        int count = 0;
        foreach (var path in File.ReadAllLines(Manifest).Where(l => l.Length > 0).Distinct())
        {
            string source = Path.Combine(Store, path);
            if (!File.Exists(source)) continue;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string dirMeta = Path.Combine(Store, Path.GetDirectoryName(path)) + ".meta";
            if (File.Exists(dirMeta) && !File.Exists(Path.GetDirectoryName(path) + ".meta")) File.Move(dirMeta, Path.GetDirectoryName(path) + ".meta");
            File.Move(source, path);
            if (File.Exists(source + ".meta")) File.Move(source + ".meta", path + ".meta");
            count++;
        }
        File.Delete(Manifest);
        AssetDatabase.Refresh();
        Debug.Log("CHECKOUT_UNUSED restored " + count + " files");
    }

    static List<string> Candidates()
    {
        var list = new List<string>();
        // v1 event props: every model except the ones still placed, and every atlas/texture those don't use.
        var keepTextures = new HashSet<string>();
        foreach (var name in KeepEventProps)
        {
            var prefab = Resources.Load<GameObject>("EventProps/" + name);
            if (!prefab) continue;
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials)
                {
                    if (!m) continue;
                    string n = m.name; int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
                    if (n.StartsWith("G_") || n.StartsWith("T_")) keepTextures.Add(n.Substring(2));
                }
            keepTextures.Add(name);
        }
        const string v1 = "Assets/Resources/EventProps";
        if (Directory.Exists(v1))
            foreach (var file in Directory.GetFiles(v1, "*", SearchOption.AllDirectories))
            {
                if (file.EndsWith(".meta")) continue;
                string stem = Path.GetFileNameWithoutExtension(file);
                bool model = Path.GetDirectoryName(file).Replace('\\', '/') == v1;
                if (model ? KeepEventProps.Contains(stem) : keepTextures.Contains(stem)) continue;
                list.Add(file.Replace('\\', '/'));
            }
        foreach (var file in new[]
        {
            "Assets/Resources/CheckoutDesktop/Delivery/delivery_backdrop.png",
            "Assets/Resources/CheckoutDesktop/Delivery/delivery_backdrop.jpg",
            "Assets/Resources/CheckoutDesktop/Delivery/delivery_room.png",
        })
            if (File.Exists(file)) list.Add(file);
        if (Directory.Exists("Assets/Resources/CheckoutDesktop/Decor"))
            list.AddRange(Directory.GetFiles("Assets/Resources/CheckoutDesktop/Decor", "_tmp_staff-*").Where(f => !f.EndsWith(".meta")).Select(f => f.Replace('\\', '/')));
        // Unity's own scene backups (never in the build, 9 copies of the 12 MB scene).
        if (Directory.Exists("Assets/_Recovery"))
            list.AddRange(Directory.GetFiles("Assets/_Recovery", "*", SearchOption.AllDirectories).Where(f => !f.EndsWith(".meta")).Select(f => f.Replace('\\', '/')));
        var report = new StringBuilder("Unused asset candidates\n");
        foreach (var f in list) report.AppendLine(f);
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/unused_candidates.txt", report.ToString());
        return list;
    }
}
