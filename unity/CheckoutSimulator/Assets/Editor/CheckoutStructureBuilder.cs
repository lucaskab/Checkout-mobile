using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class CheckoutStructureBuilder
{
    const string RootPath = "Assets/Art/Models/MapModels/";
    const string WorldPath = "Assets/Art/Models/MarketWorld.fbx";
    const string VisualName = "ReplacementVisual";

    public static void ApplyToWorld(Transform world)
    {
        Counter(world);
        Structure(world);
    }

    static void Counter(Transform world)
    {
        var root = world.Find("Checkout");
        RemoveVisual(root);
        root.GetComponent<Renderer>().enabled = false;
        var visual = CheckoutMapModelsBuilder.Create(root, "CheckoutCounter", VisualName, -90f);
        var bounds = GetBounds(visual);
        visual.localScale *= Mathf.Min(3.16f / bounds.size.x, 1.55f / bounds.size.z, 1.9f / bounds.size.y);
        bounds = GetBounds(visual);
        visual.position += new Vector3(-3.9f - bounds.center.x, .74f - bounds.min.y, -4.7f - bounds.center.z);
        var cashier = world.Find("Worker_Cashier");
        if (cashier) cashier.position = new Vector3(-4.65f, .74f, -3.66f);
        Debug.Log("CHECKOUT_COUNTER_BOUNDS " + GetBounds(visual));
    }

    static void Structure(Transform world)
    {
        var root = world.Find("Building");
        RemoveVisual(root);
        PreserveAccessGeometry(root);
        var importer = (ModelImporter)AssetImporter.GetAtPath(RootPath + "MarketStructure/MarketStructure.fbx");
        importer.isReadable = true;
        importer.SaveAndReimport();
        var visual = CheckoutMapModelsBuilder.Create(root, "MarketStructure", VisualName, 180f);
        PrefabUtility.UnpackPrefabInstance(visual.gameObject, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        var filter = visual.GetComponentInChildren<MeshFilter>();
        var mesh = UnityEngine.Object.Instantiate(filter.sharedMesh);
        var bounds = GetBounds(visual);
        var vertices = mesh.vertices;
        for (int i = 0; i < vertices.Length; i++)
        {
            var point = filter.transform.TransformPoint(vertices[i]);
            float height = (point.y - bounds.min.y) / bounds.size.y;
            point.x = (point.x - bounds.center.x) / bounds.size.x * 18.8f;
            point.z = (point.z - bounds.center.z) / bounds.size.z * 14.8f;
            // Match the existing walking surface (0.74) while retaining the new foundation.
            point.y = height < .0716f ? height / .0716f * .74f : .74f + (height - .0716f) / .9284f * 2.49f;
            if (height > .04f && height < .085f && Mathf.Abs(point.x) < 8.9f && Mathf.Abs(point.z) < 6.9f) point.y = .74f;
            vertices[i] = filter.transform.InverseTransformPoint(point);
        }
        var points = vertices.Select(filter.transform.TransformPoint).ToArray();
        var portal = points.Where(p => p.z < -6f && Mathf.Abs(p.x) < 4f && p.y > 1.9f).ToArray();
        if (portal.Length == 0) throw new InvalidOperationException("Cannot locate supplied entrance.");
        float portalLeft = portal.Min(p => p.x) - .6f;
        float portalRight = portal.Max(p => p.x) + .3f;
        // The GLB has a fixed central door. Keep the animated doorway at its original
        // navigation anchor, and extend the supplied low walls to meet its jambs.
        FilterTriangles(mesh, points, p => !(p.z < -6f && p.x > portalLeft && p.x < portalRight && p.y > .75f)
            && !(p.z > 6.9f && p.x > 3.48f && p.x < 4.58f && p.y > .75f && p.y < 2.65f));
        for (int i = 0; i < points.Length; i++)
        {
            var point = points[i];
            if (point.z < -6f && point.y > .75f)
            {
                if (point.x <= portalLeft) point.x = Mathf.Lerp(-9.4f, -3.25f, Mathf.InverseLerp(-9.4f, portalLeft, point.x));
                else if (point.x >= portalRight) point.x = Mathf.Lerp(-.25f, 9.4f, Mathf.InverseLerp(portalRight, 9.4f, point.x));
                else point.x = Mathf.Lerp(-3.25f, -.25f, Mathf.InverseLerp(portalLeft, portalRight, point.x));
            }
            vertices[i] = filter.transform.InverseTransformPoint(point);
        }
        mesh.vertices = vertices;
        mesh.RecalculateBounds();
        SaveMesh(mesh, RootPath + "MarketStructure/MarketStructureFitted.asset", filter);
        ValidatePassages(filter);
        importer.isReadable = false;
        importer.SaveAndReimport();
        Debug.Log("CHECKOUT_STRUCTURE_BOUNDS " + GetBounds(visual));
    }

    static void PreserveAccessGeometry(Transform root)
    {
        var importer = (ModelImporter)AssetImporter.GetAtPath(WorldPath);
        bool readable = importer.isReadable;
        try
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(WorldPath).transform.Find("Building").GetComponent<MeshFilter>().sharedMesh;
            var mesh = UnityEngine.Object.Instantiate(source);
            var points = mesh.vertices.Select(root.TransformPoint).ToArray();
            FilterTriangles(mesh, points, p => p.z < -7.43f || p.z > 7.32f
                || (p.z < -6.9f && p.x > -3.5f && p.x < 0f && p.y > .75f)
                || (p.z > 6.9f && p.x > 3.35f && p.x < 4.7f && p.y > .75f));
            SaveMesh(mesh, RootPath + "MarketStructure/MarketAccessGeometry.asset", root.GetComponent<MeshFilter>());
            root.GetComponent<Renderer>().enabled = true;
        }
        finally { importer.isReadable = readable; importer.SaveAndReimport(); }
    }

    static void FilterTriangles(Mesh mesh, Vector3[] points, Func<Vector3, bool> keep)
    {
        for (int submesh = 0; submesh < mesh.subMeshCount; submesh++)
        {
            var triangles = mesh.GetTriangles(submesh);
            var kept = new System.Collections.Generic.List<int>();
            for (int i = 0; i < triangles.Length; i += 3)
                if (keep((points[triangles[i]] + points[triangles[i + 1]] + points[triangles[i + 2]]) / 3f))
                    kept.AddRange(new[] { triangles[i], triangles[i + 1], triangles[i + 2] });
            mesh.SetTriangles(kept, submesh);
        }
    }

    static void ValidatePassages(MeshFilter filter)
    {
        var collider = filter.gameObject.AddComponent<MeshCollider>();
        collider.sharedMesh = filter.sharedMesh;
        try
        {
            foreach (float x in new[] { -2.8f, -1.75f, -.7f })
                if (collider.Raycast(new Ray(new Vector3(x, 1.5f, -8f), Vector3.forward), out _, 2f))
                    throw new InvalidOperationException("New structure blocks customer entrance at " + x);
            if (collider.Raycast(new Ray(new Vector3(4.03f, 1.5f, 8f), Vector3.back), out _, 2f))
                throw new InvalidOperationException("New structure blocks delivery access.");
            foreach (var point in new[] { new Vector3(-1.75f, 5f, -5f), new Vector3(0f, 5f, 0f), new Vector3(4f, 5f, 2f) })
                if (!collider.Raycast(new Ray(point, Vector3.down), out var hit, 6f) || Mathf.Abs(hit.point.y - .74f) > .025f)
                    throw new InvalidOperationException("New floor does not match the navigation surface.");
            Debug.Log("CHECKOUT_STRUCTURE_ACCESS_OK entrance=3 delivery=1 floor=3");
        }
        finally { UnityEngine.Object.DestroyImmediate(collider); }
    }

    static void RemoveVisual(Transform root)
    {
        if (!root) throw new InvalidOperationException("Missing market structure root.");
        var visual = root.Find(VisualName);
        if (visual) UnityEngine.Object.DestroyImmediate(visual.gameObject);
    }

    static void SaveMesh(Mesh mesh, string path, MeshFilter filter)
    {
        var saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (saved) { EditorUtility.CopySerialized(mesh, saved); UnityEngine.Object.DestroyImmediate(mesh); }
        else { AssetDatabase.CreateAsset(mesh, path); saved = mesh; }
        filter.sharedMesh = saved;
    }

    static Bounds GetBounds(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>();
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }
}
