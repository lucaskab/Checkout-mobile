using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Social v1 invite rewards (art approved by Lucas 01/11, ArtSource/social_art): the three exclusive decorations — the
// bench "Banco do Bairro" (1 friend), the lamp "Poste da Amizade" (3, a swaying banner and a glowing lantern) and the
// statue "Estátua dos Amigos" (5). Same import as the decor v4 kit pieces (KitModel: Assets/Art/Interior/Models/<id>.fbx,
// the painted atlas in Assets/Art/Interior/Textures; the static body baked, "Anim Sway" kept live for
// CheckoutInteriorLife), saved as prefabs in Resources/CheckoutFixtureTiers, where CheckoutInterior.TemplateObject finds
// templates that are not in the scene's Interior Kit (so the scene itself is not touched).
public static partial class CheckoutMarketStagesBuilder
{
    // Footprint half-size (x, z) and marker height, from ArtSource/social_art/report.json (rounded up a little).
    static readonly Dictionary<string, Vector3> InviteDecorSize = new Dictionary<string, Vector3>
    {
        { "invite-reward-1", new Vector3(.98f, .32f, 1.3f) },
        { "invite-reward-3", new Vector3(.83f, .37f, 3.35f) },
        { "invite-reward-5", new Vector3(.66f, .66f, 2.08f) },
    };
    const string InviteDecorFolder = "Assets/Resources/CheckoutFixtureTiers/";

    [MenuItem("Supermarket/Build invite decorations")]
    public static void BuildInviteDecorations()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear(); persisted.Clear();
        if (!AssetDatabase.IsValidFolder("Assets/Resources/CheckoutFixtureTiers")) AssetDatabase.CreateFolder("Assets/Resources", "CheckoutFixtureTiers");
        var report = new List<string>();
        foreach (var pair in InviteDecorSize)
        {
            var id = pair.Key; var s = pair.Value;
            var root = new GameObject(id);
            try
            {
                var piece = Piece(root.transform, new Vector2(-s.x, -s.y), new Vector2(s.x, s.y), 0, s.z);
                if (!KitModel(root.transform)) { report.Add(id + ": missing " + KitFolder + "Models/" + id + ".fbx"); continue; }
                Finish(root.transform, piece, new List<Transform>());
                var prefab = PrefabUtility.SaveAsPrefabAsset(root, InviteDecorFolder + id + ".prefab");
                int tris = root.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh).Sum(f => f.sharedMesh.triangles.Length / 3);
                var mats = root.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Where(m => m).Select(m => m.name).Distinct();
                var sway = root.GetComponentsInChildren<Transform>(true).Count(t => t.name.StartsWith("Anim Sway"));
                report.Add($"{id}: {(prefab ? "ok" : "FAILED")} {tris} tris, materials {string.Join(",", mats)}, sway nodes {sway}");
            }
            finally { UnityEngine.Object.DestroyImmediate(root); }
        }
        AssetDatabase.SaveAssets(); AssetDatabase.Refresh();
        Debug.Log("INVITE_DECOR\n" + string.Join("\n", report));
    }
}
