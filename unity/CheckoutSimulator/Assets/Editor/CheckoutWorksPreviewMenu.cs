using Checkout;
using UnityEditor;
using UnityEngine;

// Play mode only: shows an expansion's works (CheckoutEraWorks) at a chosen progress, next to the current shop,
// without starting anything in the save. "Stop" goes back to what the game says.
public static class CheckoutWorksPreviewMenu
{
    const string Root = "Checkout/Dev/Works preview/";
    const double Minutes = 10 * 60 * 1000;
    public static float CloseUp = 13f; static string tag = ""; static string[] only;

    static void Show(string era, float progress)
    {
        if (!EditorApplication.isPlaying) { Debug.LogWarning("Works preview: enter Play mode first."); return; }
        double now = CheckoutBridge.Now, start = now - progress * Minutes;
        CheckoutEraWorks.Preview = new EraConstruction { eraId = era, name = era, startedAt = start, endsAt = start + Minutes };
        Refresh();
    }

    static void Refresh()
    {
        var map = Object.FindAnyObjectByType<CheckoutMap>();
        if (map) map.Reapply();
    }

    [MenuItem(Root + "Banca 5%")] static void Banca5() => Show("banca", .05f);
    [MenuItem(Root + "Banca 35%")] static void Banca35() => Show("banca", .35f);
    [MenuItem(Root + "Banca 70%")] static void Banca70() => Show("banca", .7f);
    [MenuItem(Root + "Banca 95%")] static void Banca95() => Show("banca", .95f);
    [MenuItem(Root + "Tenda 50%")] static void Tenda50() => Show("tenda", .5f);
    [MenuItem(Root + "Conteiner 50%")] static void Conteiner50() => Show("conteiner", .5f);
    // Close-up pictures of the works (four sides, game-like angle) to Temp/qa/works_<era>_<side>.png.
    [MenuItem(Root + "Capture close-ups")]
    static void Capture()
    {
        if (!EditorApplication.isPlaying) return;
        GameObject site = null;
        foreach (var go in Object.FindObjectsByType<CheckoutWorksScene>(FindObjectsSortMode.None)) if (go.name.StartsWith("Expansion works")) site = go.gameObject;
        if (!site) { Debug.LogWarning("Works preview: no expansion works in the scene."); return; }
        var b = CheckoutWorksKit.Bounds(site);
        var lines = new System.Text.StringBuilder();
        foreach (var r in site.GetComponentsInChildren<Renderer>(false))
            lines.AppendLine($"{r.name} <- {(r.transform.parent ? r.transform.parent.name : "")} <- {(r.transform.parent && r.transform.parent.parent ? r.transform.parent.parent.name : "")} centre {r.bounds.center} size {r.bounds.size}");
        System.IO.Directory.CreateDirectory("Temp/qa");
        System.IO.File.WriteAllText("Temp/qa/works_renderers.txt", lines.ToString());
        System.IO.Directory.CreateDirectory("Temp/qa");
        var camGo = new GameObject("Works capture camera"); var cam = camGo.AddComponent<Camera>();
        var main = Camera.main; if (main) { cam.CopyFrom(main); cam.orthographic = false; }
        cam.fieldOfView = 38; cam.nearClipPlane = .1f; cam.farClipPlane = 400;
        var rt = new RenderTexture(1600, 1000, 24); cam.targetTexture = rt;
        // Frame on the countdown pill (it floats over what is being built), close enough to read the crew.
        var pill = site.transform.Find("Works countdown");
        if (pill) b = new Bounds(new Vector3(pill.position.x, 1.2f, pill.position.z), new Vector3(10, 2.4f, 10));
        float dist = CloseUp;
        string era = site.name.Replace("Expansion works ", "");
        foreach (var (side, yaw) in new[] { ("sw", 45f), ("se", -45f), ("nw", 135f), ("top", 45f) })
        {
            if (only != null && System.Array.IndexOf(only, side) < 0) continue;
            float pitch = side == "top" ? 62f : 34f;
            var rot = Quaternion.Euler(pitch, yaw, 0);
            cam.transform.SetPositionAndRotation(b.center - rot * Vector3.forward * dist, rot);
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply();
            System.IO.File.WriteAllBytes($"Temp/qa/works_{era}_{side}{tag}.png", tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
        }
        RenderTexture.active = null; cam.targetTexture = null; Object.DestroyImmediate(rt); Object.DestroyImmediate(camGo);
        Debug.Log($"CHECKOUT_WORKS_CAPTURE {era} centre {b.center} size {b.size}");
    }

    [MenuItem(Root + "Capture closer")] static void Closer() { CloseUp = 8f; tag = "_close"; Capture(); CloseUp = 13f; tag = ""; }

    // Eight close-ups of one side over four seconds (to see the crew's animations): works_<era>_sw_seq<n>.png.
    [MenuItem(Root + "Capture animation sequence")]
    static void Sequence()
    {
        int n = 0; double next = EditorApplication.timeSinceStartup;
        void Step()
        {
            if (!EditorApplication.isPlaying || n >= 8) { EditorApplication.update -= Step; return; }
            if (EditorApplication.timeSinceStartup < next) return;
            next += .5; CloseUp = 8f; tag = "_seq" + n; only = new[] { "sw", "se" }; Capture(); CloseUp = 13f; tag = ""; only = null; n++;
        }
        EditorApplication.update += Step;
    }

    [MenuItem(Root + "Stop")] static void Stop() { CheckoutEraWorks.Preview = null; Refresh(); }
}
