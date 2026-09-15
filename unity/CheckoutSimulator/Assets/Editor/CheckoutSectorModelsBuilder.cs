using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using MarketDay;

public static class CheckoutSectorModelsBuilder
{
    const string RootPath = "Assets/Art/Models/MapModels/";
    const string WorldPath = "Assets/Art/Models/MarketWorld.fbx";
    const string VisualName = "ReplacementVisual";

    public static void ApplyToWorld(Transform world)
    {
        Replace(world, "Sector_acougue", "ButcherDisplay", new Vector3(6.5f, .74f, 3.35f), 4.15f, "Worker_Butcher");
        Replace(world, "Sector_peixaria", "SeafoodCounter", new Vector3(1.5f, .74f, 3.35f), 3.85f, "Worker_Fishmonger");
        Replace(world, "Sector_queijaria", "CheeseDisplay", new Vector3(-3.8f, .74f, 3.35f), 2.4f, null);
    }

    static void Replace(Transform world, string sector, string model, Vector3 front, float width, string workerName)
    {
        var root = world.Find(sector);
        if (!root) throw new InvalidOperationException("Missing sector: " + sector);
        var existing = root.Find(VisualName);
        if (existing) UnityEngine.Object.DestroyImmediate(existing.gameObject);
        if (sector == "Sector_peixaria") PreserveSeafoodFreezers(root);
        else root.GetComponent<Renderer>().enabled = false;

        var visual = CheckoutMapModelsBuilder.Create(root, model, VisualName, 180f);
        var bounds = GetBounds(visual);
        visual.localScale *= width / bounds.size.x;
        bounds = GetBounds(visual);
        visual.position += new Vector3(front.x - bounds.center.x, front.y - bounds.min.y, front.z - bounds.min.z);
        bounds = GetBounds(visual);
        if (bounds.max.z > 6.9f || bounds.max.y > 3.2f)
            throw new InvalidOperationException("Sector model exceeds available space: " + sector);
        if (workerName != null) PositionWorker(world.Find(workerName), visual, bounds);
        Debug.Log("CHECKOUT_SECTOR_MODEL_OK " + sector + " center=" + bounds.center.ToString("F3") + " size=" + bounds.size.ToString("F3"));
    }

    static void PreserveSeafoodFreezers(Transform root)
    {
        // The legacy sector also owns the two freezers along the east aisle.
        // Replace its rear service counter while retaining those separate fixtures.
        var importer = (ModelImporter)AssetImporter.GetAtPath(WorldPath);
        bool readable = importer.isReadable;
        try
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(WorldPath).transform.Find("Sector_peixaria").GetComponent<MeshFilter>().sharedMesh;
            var mesh = UnityEngine.Object.Instantiate(source);
            var points = mesh.vertices.Select(root.TransformPoint).ToArray();
            for (int submesh = 0; submesh < mesh.subMeshCount; submesh++)
            {
                var triangles = mesh.GetTriangles(submesh);
                var kept = new System.Collections.Generic.List<int>();
                for (int i = 0; i < triangles.Length; i += 3)
                {
                    var center = (points[triangles[i]] + points[triangles[i + 1]] + points[triangles[i + 2]]) / 3f;
                    if (center.z < 2.9f || center.x > 4.2f)
                        kept.AddRange(new[] { triangles[i], triangles[i + 1], triangles[i + 2] });
                }
                mesh.SetTriangles(kept, submesh);
            }
            string path = RootPath + "SeafoodCounter/ExistingFreezers.asset";
            var saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (saved) { EditorUtility.CopySerialized(mesh, saved); UnityEngine.Object.DestroyImmediate(mesh); }
            else { AssetDatabase.CreateAsset(mesh, path); saved = mesh; }
            root.GetComponent<MeshFilter>().sharedMesh = saved;
            root.GetComponent<Renderer>().enabled = true;
        }
        finally { importer.isReadable = readable; importer.SaveAndReimport(); }
    }

    static void PositionWorker(Transform worker, Transform visual, Bounds bounds)
    {
        if (!worker) throw new InvalidOperationException("Missing sector employee.");
        var position = new Vector3(bounds.center.x, bounds.min.y, bounds.center.z + bounds.size.z * .12f);
        var filter = visual.GetComponentInChildren<MeshFilter>();
        var collider = filter.gameObject.AddComponent<MeshCollider>();
        collider.sharedMesh = filter.sharedMesh;
        Physics.SyncTransforms();
        try
        {
            if (!collider.Raycast(new Ray(position + Vector3.up * 5f, Vector3.down), out var hit, 6f)
                || hit.point.y > bounds.min.y + bounds.size.y * .5f)
                throw new InvalidOperationException("Cannot locate the service worktop in " + visual.parent.name);
            // The grey interior surface is a worktop. Keep staff at market floor
            // height, with their lower body concealed behind the display cabinet.
            position.y = bounds.min.y;
            worker.position = position;
            worker.rotation = Quaternion.identity;
            Debug.Log("CHECKOUT_SECTOR_WORKER_OK " + worker.name + " position=" + position.ToString("F3"));
        }
        finally { UnityEngine.Object.DestroyImmediate(collider); }
    }

    static Bounds GetBounds(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>();
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }
}
