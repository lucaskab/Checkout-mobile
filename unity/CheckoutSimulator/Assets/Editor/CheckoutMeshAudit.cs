using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Before/after check for the lighter (decimated in Blender) versions of the heavy models: every mesh inside every
// model under Assets/Art and Assets/Resources with its triangles and bounds, plus the scene's renderers that lost
// their mesh. Snapshot before replacing the FBX files, compare after: the bounds must match (same size, same place)
// and no scene object may point at a missing mesh.
public static class CheckoutMeshAudit
{
    const string Before = "Logs/mesh_audit_before.txt";
    const string After = "Logs/mesh_audit_after.txt";
    const string Report = "Logs/mesh_audit_report.txt";

    [MenuItem("Supermarket/Performance/Mesh audit: snapshot (before)")]
    public static void SnapshotBefore() => File.WriteAllText(Before, Snapshot());

    [MenuItem("Supermarket/Performance/Mesh audit: compare (after)")]
    public static void CompareAfter()
    {
        AssetDatabase.Refresh();
        File.WriteAllText(After, Snapshot());
        var before = Parse(File.Exists(Before) ? File.ReadAllLines(Before) : new string[0]);
        var after = Parse(File.ReadAllLines(After));
        var sb = new StringBuilder();
        long trisBefore = 0, trisAfter = 0; int changed = 0, problems = 0;
        foreach (var pair in before)
        {
            if (!after.TryGetValue(pair.Key, out var now)) { sb.AppendLine("MISSING " + pair.Key); problems++; continue; }
            var was = pair.Value;
            if (was.tris == now.tris) continue;
            changed++; trisBefore += was.tris; trisAfter += now.tris;
            float size = Vector3.Distance(was.size, now.size) / Mathf.Max(.0001f, was.size.magnitude);
            float centre = Vector3.Distance(was.centre, now.centre) / Mathf.Max(.0001f, was.size.magnitude);
            string flag = size > .05f || centre > .05f ? "CHECK " : "ok    ";
            if (flag != "ok    ") problems++;
            sb.AppendLine($"{flag}{pair.Key}: {was.tris} -> {now.tris} tris, size {was.size:F3} -> {now.size:F3}, centre {was.centre:F3} -> {now.centre:F3}");
        }
        foreach (var key in after.Keys.Where(k => !before.ContainsKey(k))) sb.AppendLine("NEW " + key);
        string head = $"Mesh audit {System.DateTime.Now:yyyy-MM-dd HH:mm}: {changed} meshes lighter, {trisBefore:N0} -> {trisAfter:N0} tris, {problems} problems\n" + (File.Exists(Before) ? File.ReadLines(Before).First() : "") + "\n# after:  " + SceneCheck() + "\n";
        File.WriteAllText(Report, head + sb);
        Debug.Log("CHECKOUT_MESH_AUDIT " + head.Trim());
    }

    static string Snapshot()
    {
        var sb = new StringBuilder("# before: " + SceneCheck() + "\n");
        foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { "Assets/Art", "Assets/Resources" }))
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            foreach (var mesh in AssetDatabase.LoadAllAssetsAtPath(path).OfType<Mesh>())
            {
                long tris = 0; for (int s = 0; s < mesh.subMeshCount; s++) tris += mesh.GetIndexCount(s) / 3;
                var b = mesh.bounds;
                string F(float v) => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
                sb.AppendLine($"{path}|{mesh.name}|{tris}|{F(b.center.x)},{F(b.center.y)},{F(b.center.z)}|{F(b.size.x)},{F(b.size.y)},{F(b.size.z)}");
            }
        }
        return sb.ToString();
    }

    struct Entry { public long tris; public Vector3 centre, size; }
    static Dictionary<string, Entry> Parse(IEnumerable<string> lines)
    {
        var map = new Dictionary<string, Entry>();
        foreach (var line in lines)
        {
            var p = line.Split('|'); if (p.Length < 5) continue;
            Vector3 V(string s) { var c = s.Split(','); return new Vector3(float.Parse(c[0], System.Globalization.CultureInfo.InvariantCulture), float.Parse(c[1], System.Globalization.CultureInfo.InvariantCulture), float.Parse(c[2], System.Globalization.CultureInfo.InvariantCulture)); }
            map[p[0] + "|" + p[1]] = new Entry { tris = long.Parse(p[2]), centre = V(p[3]), size = V(p[4]) };
        }
        return map;
    }

    // Scene objects that lost their mesh (a renamed node in a re-exported FBX would show up here).
    static string SceneCheck()
    {
        var scene = EditorSceneManager.GetActiveScene();
        int empty = 0, total = 0; var names = new List<string>();
        foreach (var root in scene.GetRootGameObjects())
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                total++;
                if (mf.sharedMesh) continue;
                empty++; if (names.Count < 20) names.Add(mf.name);
            }
        return $"scene {scene.name}: {total} mesh filters, {empty} without mesh {(names.Count > 0 ? "(" + string.Join(", ", names) + ")" : "")}";
    }
}
