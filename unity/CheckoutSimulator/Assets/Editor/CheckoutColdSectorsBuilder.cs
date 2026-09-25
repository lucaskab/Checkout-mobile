using System;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Adds only missing cold departments to the currently open market scene.
public static class CheckoutColdSectorsBuilder
{
    [MenuItem("Supermarket/Add cold production sectors")]
    public static void Apply()
    {
        var market = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!market || !market.world)
            throw new InvalidOperationException("Open the Supermarket scene first.");

        var world = market.world;
        var constructionRoot = world.Find("Sector Construction");
        if (!constructionRoot)
            throw new InvalidOperationException("Existing sector construction root is missing.");

        Add(world, constructionRoot, "bebidas", "Refrigerator", new Vector3(8.15f, .74f, 1.7f), 1.45f);
        Add(world, constructionRoot, "sorvetes", "IceCreamFreezer", new Vector3(-8.0f, .74f, 1.65f), 2.15f);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
        AssetDatabase.SaveAssets();
    }

    static void Add(Transform world, Transform constructionRoot, string id, string modelName, Vector3 floor, float width)
    {
        var finished = world.Find("Sector_" + id);
        if (!finished)
        {
            finished = new GameObject("Sector_" + id).transform;
            Undo.RegisterCreatedObjectUndo(finished.gameObject, "Add " + id + " sector");
            finished.SetParent(world, false);
            var model = CheckoutMapModelsBuilder.Create(finished, modelName, "Display", 180f);
            Fit(model, floor, width, 2.15f);
            finished.gameObject.SetActive(false);
        }

        var holder = constructionRoot.Find(id);
        if (holder) return;
        holder = new GameObject(id).transform;
        Undo.RegisterCreatedObjectUndo(holder.gameObject, "Add " + id + " construction");
        holder.SetParent(constructionRoot, false);
        holder.position = floor;
        var construction = new GameObject("Construction visual").transform;
        construction.SetParent(holder, false);
        var placeholder = CheckoutMapModelsBuilder.Create(construction, "ConstructionPlatform", "ConstructionPlatform", 180f);
        Fit(placeholder, floor, width, 1.5f);
        var progress = Undo.AddComponent<CheckoutSectorProgress>(holder.gameObject);
        progress.construction = construction;
        progress.finished = finished;
        progress.worker = null;
        construction.gameObject.SetActive(true);
        Debug.Log("CHECKOUT_COLD_SECTOR_ADDED " + id + " at " + floor.ToString("F2"));
    }

    static void Fit(Transform model, Vector3 floor, float width, float maxHeight)
    {
        var bounds = BoundsOf(model);
        model.localScale *= Mathf.Min(width / bounds.size.x, maxHeight / bounds.size.y);
        bounds = BoundsOf(model);
        model.position += new Vector3(floor.x - bounds.center.x, floor.y - bounds.min.y, floor.z - bounds.center.z);
    }

    static Bounds BoundsOf(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0) throw new InvalidOperationException("Cold sector model has no renderers: " + root.name);
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }
}
