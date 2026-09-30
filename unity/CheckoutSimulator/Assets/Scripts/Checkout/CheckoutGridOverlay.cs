using UnityEngine;

namespace Checkout
{
    // The square grid drawn on the floor while arranging the map (build mode, map editor). The lines start at
    // the area's corner so they match the snapping of CheckoutInterior.Snap.
    public static class CheckoutGridOverlay
    {
        static GameObject quad; static Mesh mesh; static Material material; static Texture2D texture;

        public static void Show(Rect area, float y, float cell, Color tint)
        {
            if (cell <= .01f || area.width <= 0 || area.height <= 0) { Hide(); return; }
            if (!quad)
            {
                texture = new Texture2D(32, 32, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Trilinear, anisoLevel = 4, name = "Grid" };
                var px = new Color[32 * 32];
                for (int j = 0; j < 32; j++) for (int i = 0; i < 32; i++) px[j * 32 + i] = i < 3 || j < 3 ? Color.white : new Color(1, 1, 1, 0);
                texture.SetPixels(px); texture.Apply(true);
                material = new Material(Shader.Find("Sprites/Default")) { mainTexture = texture, renderQueue = 3050, name = "Grid" };
                quad = new GameObject("Map Grid"); mesh = new Mesh { name = "Map Grid" };
                quad.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = quad.AddComponent<MeshRenderer>(); r.sharedMaterial = material; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            }
            float u = area.width / cell, v = area.height / cell;
            mesh.Clear();
            mesh.vertices = new[] { new Vector3(area.xMin, y, area.yMin), new Vector3(area.xMin, y, area.yMax), new Vector3(area.xMax, y, area.yMax), new Vector3(area.xMax, y, area.yMin) };
            mesh.uv = new[] { new Vector2(0, 0), new Vector2(0, v), new Vector2(u, v), new Vector2(u, 0) };
            mesh.colors = new[] { tint, tint, tint, tint };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateBounds();
            quad.SetActive(true);
        }

        public static void Hide() { if (quad) quad.SetActive(false); }
    }
}
