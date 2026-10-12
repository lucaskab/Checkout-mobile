using System.IO;
using Checkout;
using UnityEditor;
using UnityEngine;

// QA of the lot clearing (Lucas 12/10: the house shrank instead of breaking, the skip stayed shallow): in Play mode
// builds a "casa" lot being cleared far from the map (CheckoutLotSites.PreviewClearing) over 30 s and takes five
// pictures along the way, front three-quarter view: Logs/ui_qa/clearing_<n>.png. The preview is removed afterwards.
public static class CheckoutLotClearingQa
{
    static GameObject root; static Camera cam; static double started; static int shot; static string ruin = "casa";
    static readonly float[] At = { 3f, 9f, 15f, 21f, 28.5f };

    [MenuItem("Checkout/QA/Capture lot clearing (Play mode)")]
    public static void Capture() { Run("casa"); }

    public static void Run(string which)
    {
        if (!Application.isPlaying) { Debug.LogWarning("CHECKOUT_CLEARING_QA needs Play mode"); return; }
        var lots = Object.FindAnyObjectByType<CheckoutLotSites>();
        if (!lots) { Debug.LogWarning("CHECKOUT_CLEARING_QA no lots"); return; }
        ruin = which;
        var origin = new Vector3(900, 0, 900);
        root = lots.PreviewClearing(ruin, origin, 30f);
        cam = new GameObject("Clearing QA camera").AddComponent<Camera>();
        cam.transform.position = origin + new Vector3(-9f, 9.5f, -13.5f);
        cam.transform.LookAt(origin + new Vector3(0, 1.2f, 0));
        cam.fieldOfView = 42; cam.enabled = false;
        started = EditorApplication.timeSinceStartup; shot = 0;
        EditorApplication.update -= Tick; EditorApplication.update += Tick;
    }

    static void Tick()
    {
        if (!Application.isPlaying || !cam) { Done(); return; }
        double t = EditorApplication.timeSinceStartup - started;
        if (shot >= At.Length) { Done(); return; }
        if (t < At[shot]) return;
        var rt = new RenderTexture(1600, 1000, 24) { antiAliasing = 4 };
        cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
        var img = new Texture2D(1600, 1000, TextureFormat.RGB24, false); img.ReadPixels(new Rect(0, 0, 1600, 1000), 0, 0); img.Apply();
        RenderTexture.active = null; cam.targetTexture = null; rt.Release();
        Directory.CreateDirectory("Logs/ui_qa");
        File.WriteAllBytes($"Logs/ui_qa/clearing_{ruin}_{shot}.png", img.EncodeToPNG());
        Object.Destroy(img);
        // A close look at the foreman's clipboard on the middle shot.
        var board = shot == 2 && root ? Find(root.transform.parent ? root.transform.parent : root.transform, "Clipboard") : null;
        if (board)
        {
            var close = new GameObject("Close").AddComponent<Camera>(); close.enabled = false; close.fieldOfView = 30;
            close.transform.position = board.position + new Vector3(-1.2f, 1.1f, -2.4f); close.transform.LookAt(board.position + Vector3.up * .1f);
            var rt2 = new RenderTexture(900, 900, 24) { antiAliasing = 4 };
            close.targetTexture = rt2; close.Render(); RenderTexture.active = rt2;
            var img2 = new Texture2D(900, 900, TextureFormat.RGB24, false); img2.ReadPixels(new Rect(0, 0, 900, 900), 0, 0); img2.Apply();
            RenderTexture.active = null; close.targetTexture = null; rt2.Release();
            File.WriteAllBytes($"Logs/ui_qa/clearing_{ruin}_foreman.png", img2.EncodeToPNG());
            Object.Destroy(img2); Object.Destroy(close.gameObject);
        }
        shot++;
    }

    static Transform Find(Transform t, string name)
    {
        foreach (var c in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None)) if (c.name == name && (c.position - new Vector3(900, 0, 900)).sqrMagnitude < 30 * 30) return c;
        return null;
    }

    static void Done()
    {
        EditorApplication.update -= Tick;
        if (cam) Object.Destroy(cam.gameObject);
        if (root) Object.Destroy(root);
        Debug.Log("CHECKOUT_CLEARING_QA_OK " + ruin);
    }
}
