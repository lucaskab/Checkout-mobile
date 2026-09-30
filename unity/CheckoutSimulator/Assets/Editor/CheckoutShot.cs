using System.IO;
using UnityEngine;

// Dev helper: renders an orthographic view of the scene to a PNG (used from the Unity CLI).
public static class CheckoutShot
{
    public static string Capture(string path, float x, float z, float size, float yaw = 0, float pitch = 38, int width = 1600, int height = 1000)
    {
        var go = new GameObject("Shot camera") { hideFlags = HideFlags.HideAndDontSave };
        var cam = go.AddComponent<Camera>();
        var main = Camera.main;
        if (main) { cam.clearFlags = main.clearFlags; cam.backgroundColor = main.backgroundColor; }
        cam.orthographic = true; cam.orthographicSize = size; cam.nearClipPlane = .1f; cam.farClipPlane = 400;
        var focus = new Vector3(x, 0, z);
        var dir = Quaternion.Euler(pitch, yaw, 0) * Vector3.forward;
        cam.transform.position = focus - dir * 120; cam.transform.LookAt(focus);
        var rt = new RenderTexture(width, height, 24) { antiAliasing = 4 };
        var active = RenderTexture.active;
        cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
        var image = new Texture2D(width, height, TextureFormat.RGB24, false);
        image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply();
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        File.WriteAllBytes(path, image.EncodeToPNG());
        RenderTexture.active = active; cam.targetTexture = null;
        Object.DestroyImmediate(image); Object.DestroyImmediate(rt); Object.DestroyImmediate(go);
        return path;
    }
}
