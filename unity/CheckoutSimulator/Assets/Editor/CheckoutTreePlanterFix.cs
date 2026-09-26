using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Round tree beds for every tree built from TreeWithPlanter: a ring of garden stones around warm bark
// mulch. Square beds looked crooked because the trees are placed with random headings.
public static class CheckoutTreePlanterFix
{
    const string PrefabPath = "Assets/Prefabs/City/Nature/TreeWithPlanter.prefab";

    public static Material Bed(string name, string kind, float gloss)
    {
        string path = "Assets/Art/CityPark/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        var textures = CheckoutCityParkTextures.Get(kind);
        material.shader = Shader.Find("MarketDay/City Park Triplanar");
        material.SetTexture("_MainTex", textures.albedo);
        material.SetTexture("_BumpMap", textures.normal);
        material.SetFloat("_Tiling", textures.tiling);
        material.SetFloat("_BumpScale", textures.bump);
        material.SetFloat("_Metallic", 0);
        material.SetFloat("_Glossiness", gloss);
        material.SetFloat("_Variation", .1f);
        material.SetVector("_Scroll", Vector4.zero);
        material.color = Color.white;
        EditorUtility.SetDirty(material);
        return material;
    }

    [MenuItem("Supermarket/Round tree planters")]
    public static void Apply()
    {
        var stones = Bed("TreeBedStones", "pebbles", .3f);
        var mulch = Bed("TreeBedMulch", "mulch", .12f);
        var cylinder = Resources.GetBuiltinResource<Mesh>("Cylinder.fbx");

        var root = PrefabUtility.LoadPrefabContents(PrefabPath);
        foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
        {
            if (filter.name != "Planter Base" && filter.name != "Soil") continue;
            if (filter.sharedMesh != cylinder)
            {
                // The primitive cylinder is 2 m tall where the cube is 1 m: halve the thin axis.
                var s = filter.transform.localScale; filter.transform.localScale = new Vector3(s.x, s.y * .5f, s.z);
                filter.sharedMesh = cylinder;
            }
            filter.GetComponent<MeshRenderer>().sharedMaterial = filter.name == "Soil" ? mulch : stones;
            // A compact bed (the square one was 2.2 m): stone ring 1.55 m around 1.2 m of mulch.
            float size = filter.name == "Soil" ? 1.2f : 1.55f;
            { var s = filter.transform.localScale; filter.transform.localScale = new Vector3(size, s.y, size); }
        }
        PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        PrefabUtility.UnloadPrefabContents(root);

        // Scene trees may carry overrides (their materials were copied from templates): follow the prefab.
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        var parts = prefab.GetComponentsInChildren<MeshFilter>(true).Where(f => f.name == "Planter Base" || f.name == "Soil").ToDictionary(f => f.name);
        int fixedCount = 0;
        foreach (var filter in Object.FindObjectsByType<MeshFilter>(FindObjectsInactive.Include))
        {
            if (!parts.TryGetValue(filter.name, out var source)) continue;
            var instanceRoot = PrefabUtility.GetNearestPrefabInstanceRoot(filter.gameObject);
            if (!instanceRoot || PrefabUtility.GetCorrespondingObjectFromSource(instanceRoot) != prefab) continue;
            filter.sharedMesh = source.sharedMesh;
            filter.transform.localScale = source.transform.localScale;
            filter.GetComponent<MeshRenderer>().sharedMaterial = source.GetComponent<MeshRenderer>().sharedMaterial;
            PrefabUtility.RecordPrefabInstancePropertyModifications(filter);
            PrefabUtility.RecordPrefabInstancePropertyModifications(filter.transform);
            PrefabUtility.RecordPrefabInstancePropertyModifications(filter.GetComponent<MeshRenderer>());
            fixedCount++;
        }
        AssetDatabase.SaveAssets();
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Debug.Log("ROUND_TREE_PLANTERS_OK parts=" + fixedCount);
    }
}
