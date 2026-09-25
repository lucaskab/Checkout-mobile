using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Area = Checkout.CheckoutExpansionNeighborhood.Area;

public static class CheckoutExpansionNeighborhoodBuilder
{
    [MenuItem("Supermarket/Prepare expansion neighborhood")]
    public static void Apply()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var existing = world.Find("Expansion Neighborhood");
        if (existing) throw new InvalidOperationException("Expansion neighborhood already exists.");
        var root = new GameObject("Expansion Neighborhood");
        Undo.RegisterCreatedObjectUndo(root, "Prepare expansion neighborhood");
        root.transform.SetParent(world, false);
        var neighborhood = root.AddComponent<CheckoutExpansionNeighborhood>();
        var lots = new List<CheckoutExpansionNeighborhood.Lot>();

        void Place(string source, string name, Area area, Vector3 position, Vector3 size, int stage = 0)
        {
            // Reuse the supplied neighborhood meshes and their existing shared materials.
            var template = world.Find("Supplied City Models/" + source);
            if (!template) throw new InvalidOperationException("Missing neighborhood model: " + source);
            var building = UnityEngine.Object.Instantiate(template.gameObject, root.transform);
            building.name = name;
            Bounds Measure()
            {
                var renderers = building.GetComponentsInChildren<Renderer>(true);
                var bounds = renderers[0].bounds;
                foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
                return bounds;
            }
            var b = Measure();
            building.transform.localScale *= Mathf.Min(size.x / b.size.x, size.y / b.size.y, size.z / b.size.z);
            b = Measure();
            building.transform.position += new Vector3(position.x - b.center.x, position.y - b.min.y, position.z - b.center.z);
            lots.Add(new CheckoutExpansionNeighborhood.Lot { building = building, area = area, replacedAtStage = stage });
        }

        Place("Corner house", "Storage house", Area.Storage, new Vector3(-5, .13f, 21), new Vector3(4.5f, 4.5f, 6));
        Place("North apartments", "Storage apartments", Area.Storage, new Vector3(.1f, .13f, 21), new Vector3(4, 5.3f, 6));
        Place("Corner house", "Parking south house", Area.Parking, new Vector3(-14, .13f, -5), new Vector3(6, 5.5f, 5.5f));
        Place("West apartment building", "Parking apartments", Area.Parking, new Vector3(-14, .13f, 2.5f), new Vector3(6, 6.5f, 6));
        Place("North townhouse", "Parking north house", Area.Parking, new Vector3(-14, .13f, 10), new Vector3(6, 5.5f, 5.5f));
        // Keep the rear-door path and the active delivery corridor clear before the loading yard is bought.
        Place("North townhouse", "Loading street house", Area.LoadingYard, new Vector3(8, .13f, 12.5f), new Vector3(4, 4.5f, 3.6f));
        Place("West apartment building", "Loading street apartments", Area.LoadingYard, new Vector3(16.4f, .13f, 12.5f), new Vector3(4.5f, 5.5f, 3.6f));
        Place("Corner house", "Park house", Area.Premium, new Vector3(-16.5f, .13f, 21), new Vector3(3.5f, 4.5f, 5.5f));
        Place("North townhouse", "Park townhouse", Area.Premium, new Vector3(-12, .13f, 21), new Vector3(3.5f, 4.5f, 5.5f));
        Place("Corner house", "Market first lot", Area.Market, new Vector3(-5, .13f, 4.2f), new Vector3(4, 4, 3.2f), 1);
        Place("North townhouse", "Market second lot", Area.Market, new Vector3(0, .13f, 5.4f), new Vector3(4, 4, 2.8f), 2);
        Place("Corner house", "Market third lot", Area.Market, new Vector3(-5, .13f, 7.8f), new Vector3(4, 4, 3.2f), 3);
        Place("North townhouse", "Market final lot", Area.Market, new Vector3(0, .13f, 9.5f), new Vector3(4, 4, 3), 4);
        neighborhood.lots = lots.ToArray();
        MoveToStreets(neighborhood);
        // Edit mode shows the authored full-size market. Runtime applies the player's purchased layout.
        neighborhood.Apply(new MarketLayout { stage = 4, storage = true, parking = true, loadingYard = true, premium = true });
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
    }

    public static void MoveToStreets(CheckoutExpansionNeighborhood neighborhood)
    {
        var centers = new Dictionary<string, Vector2> {
            {"Market first lot",new Vector2(16.5f,-7)}, {"Market second lot",new Vector2(16.5f,-1)},
            {"Market third lot",new Vector2(16.5f,5)}, {"Market final lot",new Vector2(16.5f,11)},
            {"Loading street house",new Vector2(16.5f,17)}, {"Loading street apartments",new Vector2(16.5f,22)},
            {"Storage house",new Vector2(-5,23)}, {"Storage apartments",new Vector2(.1f,23)},
            {"Park house",new Vector2(-16.5f,23)}, {"Park townhouse",new Vector2(-12,23)}
        };
        foreach(var lot in neighborhood.lots)
        {
            if(!centers.TryGetValue(lot.building.name,out var center))continue;
            var root=lot.building.transform;Undo.RecordObject(root,"Move houses to streets");
            var renderers=root.GetComponentsInChildren<Renderer>(true);var bounds=renderers[0].bounds;foreach(var r in renderers)bounds.Encapsulate(r.bounds);
            root.position+=new Vector3(center.x-bounds.center.x,0,center.y-bounds.center.z);
        }
    }
}
