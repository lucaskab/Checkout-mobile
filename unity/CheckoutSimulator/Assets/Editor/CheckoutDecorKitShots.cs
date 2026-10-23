using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// QA helper (decor v4, 22/10/2026): renders every build-mode decoration of the "Interior Kit" templates with the
// game's real materials and the scene light, one PNG per decoration in Temp/qa/decor_kit/<id>.png, from the high
// 3/4 angle of the game camera. Other kit pieces are hidden while each shot is taken.
public static class CheckoutDecorKitShots
{
    [MenuItem("Supermarket/Capture decor kit shots")]
    public static void Capture()
    {
        var kit = Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(t => t.name == "Interior Kit");
        if (!kit) { Debug.LogError("CHECKOUT_DECOR_SHOTS: no \"Interior Kit\" in the open scene."); return; }
        string folder = Path.Combine(Directory.GetCurrentDirectory(), "Temp", "qa", "decor_kit");
        Directory.CreateDirectory(folder);
        var children = Enumerable.Range(0, kit.childCount).Select(i => kit.GetChild(i)).ToList();
        var wasActive = children.ToDictionary(c => c, c => c.gameObject.activeSelf);
        var go = new GameObject("Decor shot camera") { hideFlags = HideFlags.HideAndDontSave };
        var cam = go.AddComponent<Camera>();
        cam.orthographic = true; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.93f, .9f, .84f);
        cam.nearClipPlane = .05f; cam.farClipPlane = 200;
        var rt = new RenderTexture(640, 640, 24) { antiAliasing = 8 };
        var image = new Texture2D(640, 640, TextureFormat.RGB24, false);
        int count = 0;
        // Lift the kit (normally 40 m under the map) above everything so the ground does not shadow it.
        var home = kit.position; kit.position = home + Vector3.up * 300; bool kitActive = kit.gameObject.activeSelf; kit.gameObject.SetActive(true);
        try
        {
            foreach (var target in children)
            {
                if (target.name.StartsWith("shelf-") || target.name.StartsWith("sector-") || target.name == "checkout" || target.name == "kiosk" || target.name == "bread-basket") continue;
                foreach (var c in children) c.gameObject.SetActive(c == target);
                var renderers = target.GetComponentsInChildren<Renderer>();
                if (renderers.Length == 0) continue;
                var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                var dir = Quaternion.Euler(48, -35, 0) * Vector3.forward;
                cam.transform.position = b.center - dir * 30; cam.transform.rotation = Quaternion.LookRotation(dir);
                cam.orthographicSize = Mathf.Max(b.extents.magnitude * 1.05f, .6f);
                cam.targetTexture = rt; cam.Render();
                var active = RenderTexture.active; RenderTexture.active = rt;
                image.ReadPixels(new Rect(0, 0, 640, 640), 0, 0); image.Apply();
                RenderTexture.active = active;
                File.WriteAllBytes(Path.Combine(folder, target.name + ".png"), image.EncodeToPNG());
                count++;
            }
        }
        finally
        {
            kit.position = home; kit.gameObject.SetActive(kitActive);
            foreach (var kv in wasActive) if (kv.Key) kv.Key.gameObject.SetActive(kv.Value);
            cam.targetTexture = null;
            Object.DestroyImmediate(image); Object.DestroyImmediate(rt); Object.DestroyImmediate(go);
        }
        Debug.Log($"CHECKOUT_DECOR_SHOTS: {count} decorations rendered to {folder}");
    }
}
