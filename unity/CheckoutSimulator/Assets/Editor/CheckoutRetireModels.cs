using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Models no longer in the game (Lucas, Oct 2026): their objects come out of the scene and their files go to
// <project>/_Unused/retired (nothing is deleted: "Restore assets moved out of the build" brings files back, the
// scene objects come back from git). A file still needed by the scene or by Resources after the clean-up is kept.
public static class CheckoutRetireModels
{
    // Whole folders (model, its textures and materials) and single files.
    static readonly string[] Folders =
    {
        "Assets/Art/Models/MapModels/AmusementPark",
        "Assets/Art/Models/MapModels/Cow",
        "Assets/Art/Models/MapModels/Sandbox",
        "Assets/Art/Models/MapModels/PickupBed",
        "Assets/Art/Models/MapModels/PlaygroundForge",
    };
    static readonly string[] Files =
    {
        "Assets/Art/Models/MapModels/GirlCustomer/GirlCustomer.fbx",
        "Assets/Art/Models/MapModels/CheckoutWoman/CheckoutWoman.fbx",
        "Assets/Art/Interior/Models/sector-bebidas.fbx",
        "Assets/Art/Interior/Models/sector-adega.fbx",
        "Assets/Art/Interior/Models/sector-queijaria.fbx",
        "Assets/Art/Interior/Models/sector-acougue.fbx",
        "Assets/Art/Interior/Models/sector-sorvetes.fbx",
    };
    const string Store = "_Unused";
    const string Manifest = Store + "/moved.txt";

    [MenuItem("Supermarket/Performance/Retire unused models (scene + files)")]
    public static void Retire()
    {
        if (EditorApplication.isPlaying) { Debug.LogError("CHECKOUT_RETIRE leave Play Mode first"); return; }
        var report = new StringBuilder("Retire unused models " + System.DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "\n");
        var models = new HashSet<string>(Files.Where(f => f.EndsWith(".fbx")));
        foreach (var folder in Folders)
            if (AssetDatabase.IsValidFolder(folder))
                foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { folder })) models.Add(AssetDatabase.GUIDToAssetPath(guid));

        // 1. Scene objects built from those models (the outermost instance; plain copies of their meshes too).
        var scene = EditorSceneManager.GetActiveScene();
        if (scene.path != "Assets/Scenes/Supermarket.unity")
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            scene = EditorSceneManager.OpenScene("Assets/Scenes/Supermarket.unity", OpenSceneMode.Single);
        }
        var doomed = new List<GameObject>();
        foreach (var root in scene.GetRootGameObjects())
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                var go = t.gameObject;
                string source = PrefabUtility.IsAnyPrefabInstanceRoot(go) ? PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(go) : null;
                var mf = go.GetComponent<MeshFilter>();
                string mesh = mf && mf.sharedMesh ? AssetDatabase.GetAssetPath(mf.sharedMesh) : null;
                if ((source != null && models.Contains(source)) || (mesh != null && models.Contains(mesh)))
                    if (!doomed.Any(d => t.IsChildOf(d.transform))) { doomed.RemoveAll(d => d.transform.IsChildOf(t)); doomed.Add(go); }
            }
        foreach (var go in doomed) { report.AppendLine("scene: removed " + Path(go.transform)); Object.DestroyImmediate(go); }
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);

        // 2. Files, unless something kept still uses them.
        var needed = new HashSet<string>(AssetDatabase.GetDependencies(EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(), true));
        foreach (var guid in AssetDatabase.FindAssets("", new[] { "Assets/Resources" }))
            foreach (var dep in AssetDatabase.GetDependencies(AssetDatabase.GUIDToAssetPath(guid), true)) needed.Add(dep);
        var files = new List<string>(Files.Where(File.Exists));
        foreach (var folder in Folders)
            if (Directory.Exists(folder)) files.AddRange(Directory.GetFiles(folder).Where(f => !f.EndsWith(".meta")).Select(f => f.Replace('\\', '/')));
        var moved = new List<string>();
        foreach (var file in files.Distinct())
        {
            if (needed.Contains(file)) { report.AppendLine("kept (still used): " + file); continue; }
            string target = System.IO.Path.Combine(Store, file);
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
            if (File.Exists(target)) File.Delete(target);
            File.Move(file, target);
            if (File.Exists(file + ".meta")) { if (File.Exists(target + ".meta")) File.Delete(target + ".meta"); File.Move(file + ".meta", target + ".meta"); }
            moved.Add(file); report.AppendLine("moved: " + file);
        }
        foreach (var folder in Folders)
            if (Directory.Exists(folder) && !Directory.EnumerateFileSystemEntries(folder).Any())
            {
                Directory.Delete(folder);
                string target = System.IO.Path.Combine(Store, folder);
                Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
                if (File.Exists(folder + ".meta")) { if (File.Exists(target + ".meta")) File.Delete(target + ".meta"); File.Move(folder + ".meta", target + ".meta"); }
            }
        Directory.CreateDirectory(Store);
        File.AppendAllLines(Manifest, moved);
        AssetDatabase.Refresh();
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/retire_report.txt", report.ToString());
        Debug.Log($"CHECKOUT_RETIRE {doomed.Count} scene objects removed, {moved.Count} files moved (Logs/retire_report.txt)");
    }

    static string Path(Transform t) => t.parent ? Path(t.parent) + "/" + t.name : t.name;
}
