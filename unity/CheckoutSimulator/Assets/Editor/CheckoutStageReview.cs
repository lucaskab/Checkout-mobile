using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEngine;

// Dev helper: renders the market at every expansion stage (game camera + close ortho view).
public static class CheckoutStageReview
{
    [MenuItem("Supermarket/Review market stages")]
    public static void Review()
    {
        var world = Object.FindAnyObjectByType<MarketSimulation>().world;
        var session = new GameObject("Stage review") { hideFlags = HideFlags.HideAndDontSave };
        var layout = session.AddComponent<CheckoutMarketLayout>();
        layout.Initialize(world);
        var sectors = new[] { "padaria", "queijaria", "acougue", "bebidas", "peixaria", "sorvetes", "adega" };
        var saved = new List<(GameObject, bool)>();
        foreach (var id in sectors)
        {
            var p = world.Find("Sector Construction/" + id); if (p) saved.Add((p.gameObject, p.gameObject.activeSelf));
            var s = world.Find("Sector_" + id); if (s) saved.Add((s.gameObject, s.gameObject.activeSelf));
            var c = world.Find("Sector Construction/" + id + "/Construction visual"); if (c) saved.Add((c.gameObject, c.gameObject.activeSelf));
        }
        try
        {
            for (int stage = 0; stage <= 4; stage++)
            {
                var next = CheckoutExpansionPreviewWindow.CreateLayout(stage);
                layout.Apply(next);
                foreach (var id in sectors)
                {
                    var progress = world.Find("Sector Construction/" + id)?.GetComponent<CheckoutSectorProgress>();
                    if (!progress) continue;
                    bool present = next.sectorIds.Contains(id);
                    progress.gameObject.SetActive(true);
                    progress.Apply(present, false);
                    if (!present && progress.construction) progress.construction.gameObject.SetActive(true);
                }
                var dressing = world.GetComponentInChildren<CheckoutStageDressing>(true);
                if (dressing) dressing.Apply(layout, next.stage, false);
                MarketBuilder.Capture("ArtSource/StageReview/Stage" + stage + "_Game.png");
                CheckoutShot.Capture("ArtSource/StageReview/Stage" + stage + "_Close.png", 3f, 1.5f, 14.5f, -36, 40);
            }
        }
        finally
        {
            layout.Apply(new MarketLayout { stage = 4, widthScale = 1, depthScale = 1, storage = true, parking = true, loadingYard = true, premium = true, sectorIds = sectors });
            layout.ResetToBase();
            var restore = world.GetComponentInChildren<CheckoutStageDressing>(true);
            if (restore) restore.Apply(layout, 3, false);
            foreach (var (go, active) in saved) if (go) go.SetActive(active);
            Object.DestroyImmediate(session);
        }
        Debug.Log("CHECKOUT_STAGE_REVIEW_OK");
    }
}
