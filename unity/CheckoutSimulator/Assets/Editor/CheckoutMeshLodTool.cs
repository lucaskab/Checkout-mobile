using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

// The Tripo / Meshy models came in at 150-185k triangles each (a traffic light, a tree, a house): fine on a PC, far
// too much for a phone, where the city alone drew ~38M triangles a frame. Unity's Mesh LOD (import option) builds
// lighter versions of each mesh inside the same asset and picks one by on-screen size, so nothing in the scenes or
// the source art changes, and turning the option off restores the originals exactly.
public static class CheckoutMeshLodTool
{
    const int MinTriangles = 6000;
    static readonly string[] Roots =
    {
        "Assets/Art", "Assets/Resources",
    };

    [MenuItem("Supermarket/Performance/Generate Mesh LODs for heavy models")]
    public static void Generate() => Run(true);

    [MenuItem("Supermarket/Performance/Remove generated Mesh LODs")]
    public static void Remove() => Run(false);

    [MenuItem("Supermarket/Performance/Report heavy models")]
    public static void Report() => Run(null);

    static void Run(bool? enable)
    {
        var report = new StringBuilder();
        var rows = new List<(int tris, string path, bool skinned, bool lods)>();
        var guids = AssetDatabase.FindAssets("t:Model", Roots);
        var changed = new List<string>();
        try
        {
            AssetDatabase.StartAssetEditing();
            for (int i = 0; i < guids.Length; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                if (path.Contains("/_Recovery/")) continue;
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                if (importer == null) continue;
                EditorUtility.DisplayProgressBar("Mesh LOD", path, i / (float)guids.Length);
                int tris = 0;
                bool skinned = false;
                foreach (var asset in AssetDatabase.LoadAllAssetsAtPath(path))
                    if (asset is Mesh mesh) tris += Triangles(mesh);
                var root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (root && root.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length > 0) skinned = true;
                rows.Add((tris, path, skinned, importer.generateMeshLods));
                if (enable == null) continue;
                // Skinned characters keep their full mesh (the LOD builder ignores skin weights; Unity always skins LOD0).
                bool want = enable.Value && !skinned && tris >= MinTriangles;
                if (importer.generateMeshLods == want) continue;
                if (!enable.Value && !importer.generateMeshLods) continue;
                importer.generateMeshLods = want;
                importer.SaveAndReimport();
                changed.Add(path);
            }
        }
        finally
        {
            AssetDatabase.StopAssetEditing();
            EditorUtility.ClearProgressBar();
        }
        report.AppendLine($"Mesh LOD {(enable == null ? "report" : enable.Value ? "generate" : "remove")}  {System.DateTime.Now:yyyy-MM-dd HH:mm:ss}");
        report.AppendLine($"changed {changed.Count} models");
        foreach (var row in rows.OrderByDescending(r => r.tris).Take(120))
            report.AppendLine($"{row.tris,9:N0}  {(row.skinned ? "skinned" : "static "),-7}  lods={(changed.Contains(row.path) ? !row.lods : row.lods)}  {row.path}");
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/meshlod_report.txt", report.ToString());
        Debug.Log("CHECKOUT_MESHLOD " + changed.Count + " models changed. Logs/meshlod_report.txt");
    }

    // 3D textures (models, props, characters) capped at 1024 on iPhone: the world objects are small on a phone screen
    // and the 2048 maps filled ~1.9 GB. UI art (sprites, CheckoutDesktop) keeps its size. Only the iPhone build changes.
    static readonly string[] TextureRoots =
    {
        "Assets/Art", "Assets/Resources/EventProps", "Assets/Resources/EventProps2", "Assets/Resources/EventRigs",
        "Assets/Resources/CheckoutLots", "Assets/Resources/CheckoutWorks", "Assets/Resources/CheckoutEras",
        "Assets/Resources/CheckoutDelivery", "Assets/Resources/CheckoutProps", "Assets/Resources/Rain",
    };
    const int PhoneTexture = 1024;

    [MenuItem("Supermarket/Performance/Cap iPhone 3D textures at 1024")]
    public static void CapPhoneTextures() => PhoneTextures(true);

    [MenuItem("Supermarket/Performance/Remove iPhone texture cap")]
    public static void UncapPhoneTextures() => PhoneTextures(false);

    static void PhoneTextures(bool cap)
    {
        var existing = TextureRoots.Where(AssetDatabase.IsValidFolder).ToArray();
        var guids = AssetDatabase.FindAssets("t:Texture2D", existing);
        int changed = 0;
        try
        {
            AssetDatabase.StartAssetEditing();
            for (int i = 0; i < guids.Length; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                if (path.Contains("/_Recovery/") || path.Contains("/UI/") || path.Contains("/Icons/")) continue;
                var importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (importer == null || importer.textureType == TextureImporterType.Sprite || importer.textureType == TextureImporterType.GUI) continue;
                var phone = importer.GetPlatformTextureSettings("iPhone");
                if (cap)
                {
                    if (phone.overridden && phone.maxTextureSize <= PhoneTexture) continue;
                    if (importer.maxTextureSize <= PhoneTexture) continue;
                    phone.overridden = true;
                    phone.maxTextureSize = PhoneTexture;
                    phone.format = TextureImporterFormat.Automatic;
                }
                else
                {
                    if (!phone.overridden) continue;
                    phone.overridden = false;
                }
                importer.SetPlatformTextureSettings(phone);
                importer.SaveAndReimport();
                changed++;
            }
        }
        finally
        {
            AssetDatabase.StopAssetEditing();
        }
        Debug.Log("CHECKOUT_PHONE_TEXTURES " + (cap ? "capped " : "uncapped ") + changed);
        File.AppendAllText("Logs/meshlod_report.txt", $"\niPhone texture cap {(cap ? "on" : "off")}: {changed} textures\n");
    }

    static int Triangles(Mesh mesh)
    {
        long count = 0;
        for (int s = 0; s < mesh.subMeshCount; s++) count += mesh.GetIndexCount(s) / 3;
        return (int)count;
    }
}
