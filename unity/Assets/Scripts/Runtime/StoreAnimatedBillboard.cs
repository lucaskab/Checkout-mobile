using UnityEngine;

public sealed class StoreAnimatedBillboard : MonoBehaviour
{
    private Renderer targetRenderer;
    private Material animatedMaterial;
    private Vector3 baseLocalPosition;
    private Vector3 baseLocalScale;
    private int frameCount = 1;
    private float framesPerSecond = 1f;
    private float phase;

    public void Configure(Texture2D texture, int frames, float speed, float phaseOffset)
    {
        targetRenderer = GetComponent<Renderer>();
        if (targetRenderer == null)
        {
            return;
        }

        animatedMaterial = new Material(targetRenderer.sharedMaterial)
        {
            mainTexture = texture,
        };
        targetRenderer.sharedMaterial = animatedMaterial;
        baseLocalPosition = transform.localPosition;
        baseLocalScale = transform.localScale;
        frameCount = Mathf.Max(1, frames);
        framesPerSecond = Mathf.Max(0.1f, speed);
        phase = phaseOffset;
        animatedMaterial.mainTextureScale = new Vector2(1f / frameCount, 1f);
    }

    private void LateUpdate()
    {
        if (targetRenderer == null || animatedMaterial == null)
        {
            return;
        }

        if (Camera.main != null)
        {
            transform.LookAt(Camera.main.transform);
        }

        var animationTime = Time.time * framesPerSecond + phase;
        var frame = Mathf.FloorToInt(animationTime) % frameCount;
        animatedMaterial.mainTextureOffset = new Vector2(frame / (float)frameCount, 0f);

        var bob = Mathf.Sin(animationTime * Mathf.PI * 2f) * 0.035f;
        var squash = 1f + Mathf.Sin(animationTime * Mathf.PI * 4f) * 0.012f;
        transform.localPosition = baseLocalPosition + Vector3.up * bob;
        transform.localScale = new Vector3(baseLocalScale.x * squash, baseLocalScale.y / squash, baseLocalScale.z);
    }

    private void OnDestroy()
    {
        if (animatedMaterial != null)
        {
            Destroy(animatedMaterial);
        }
    }
}
