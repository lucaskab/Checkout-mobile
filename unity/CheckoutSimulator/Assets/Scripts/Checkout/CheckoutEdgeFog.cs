using UnityEngine;

namespace Checkout
{
    // Fog that starts at the edge of the playable map: an image effect on the camera that rebuilds each pixel's
    // world position from the depth buffer and blends it into the fog colour by how far outside the map it is
    // (the map itself is never touched, whatever the camera's angle or zoom). The fog colour is the camera's
    // background colour, so the rain and the night tint it with the sky.
    [RequireComponent(typeof(Camera))]
    public sealed class CheckoutEdgeFog : MonoBehaviour
    {
        Camera view; Material material; Rect playable; Vector2 range = new Vector2(0, 26);
        static readonly int ClipToWorld = Shader.PropertyToID("_ClipToWorld"), Playable = Shader.PropertyToID("_Playable"),
            FogColor = Shader.PropertyToID("_FogColor"), FogRange = Shader.PropertyToID("_FogRange");

        public void Configure(Rect map, float start, float end) { playable = map; range = new Vector2(start, end); }

        void OnEnable()
        {
            view = GetComponent<Camera>();
            view.depthTextureMode |= DepthTextureMode.Depth;
            if (!material)
            {
                var shader = Resources.Load<Shader>("MarketEdgeFog");
                if (shader && shader.isSupported) material = new Material(shader) { hideFlags = HideFlags.HideAndDontSave };
            }
            // A camera copied for a QA shot takes the fog of the game camera.
            if (playable.width <= 0 && Camera.main && Camera.main != view && Camera.main.TryGetComponent<CheckoutEdgeFog>(out var game)) { playable = game.playable; range = game.range; }
        }

        void OnDestroy() { if (material) Destroy(material); }

        void OnRenderImage(RenderTexture source, RenderTexture destination)
        {
            if (!material || playable.width <= 0) { Graphics.Blit(source, destination); return; }
            var projection = GL.GetGPUProjectionMatrix(view.projectionMatrix, false);
            material.SetMatrix(ClipToWorld, (projection * view.worldToCameraMatrix).inverse);
            material.SetVector(Playable, new Vector4(playable.xMin, playable.yMin, playable.xMax, playable.yMax));
            var c = view.backgroundColor; material.SetColor(FogColor, new Color(c.r, c.g, c.b, 1));
            material.SetVector(FogRange, new Vector4(range.x, range.y, 0, 0));
            Graphics.Blit(source, destination, material);
        }
    }
}
