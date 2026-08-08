using UnityEngine;

public static class StoreVisualFactory
{
    public static readonly Color Floor = new Color(0.98f, 0.94f, 0.88f);
    public static readonly Color FloorLight = new Color(1f, 0.98f, 0.94f);
    public static readonly Color Grass = new Color(0.36f, 0.72f, 0.22f);
    public static readonly Color GrassLight = new Color(0.52f, 0.82f, 0.32f);
    public static readonly Color GrassDark = new Color(0.22f, 0.56f, 0.18f);
    public static readonly Color Path = new Color(0.92f, 0.72f, 0.48f);
    public static readonly Color PathLight = new Color(0.98f, 0.86f, 0.68f);
    public static readonly Color Wood = new Color(0.55f, 0.32f, 0.14f);
    public static readonly Color Teal = new Color(0.08f, 0.52f, 0.62f);
    public static readonly Color TealLight = new Color(0.18f, 0.72f, 0.78f);
    public static readonly Color Orange = new Color(1f, 0.52f, 0.12f);
    public static readonly Color Cream = new Color(1f, 0.97f, 0.9f);
    public static readonly Color Leaf = new Color(0.22f, 0.68f, 0.18f);
    public static readonly Color Berry = new Color(0.95f, 0.18f, 0.14f);
    public static readonly Color WallWhite = new Color(0.96f, 0.96f, 0.94f);
    public static readonly Color RoofBlue = new Color(0.22f, 0.52f, 0.78f);
    public static readonly Color Sky = new Color(0.52f, 0.84f, 0.96f);

    private static Shader cachedShader;

    public static Material Material(Color color, float smoothness = 0.12f)
    {
        cachedShader ??= Shader.Find("Universal Render Pipeline/Lit");
        cachedShader ??= Shader.Find("Standard");
        cachedShader ??= Shader.Find("Unlit/Color");
        var material = new Material(cachedShader) { color = color };
        if (material.HasProperty("_Smoothness"))
        {
            material.SetFloat("_Smoothness", smoothness);
        }
        return material;
    }

    public static GameObject Cube(string name, Vector3 position, Vector3 scale, Color color, Transform parent = null)
    {
        var objectInstance = GameObject.CreatePrimitive(PrimitiveType.Cube);
        objectInstance.name = name;
        objectInstance.transform.SetParent(parent);
        objectInstance.transform.position = position;
        objectInstance.transform.localScale = scale;
        objectInstance.GetComponent<Renderer>().sharedMaterial = Material(color);
        return objectInstance;
    }

    public static GameObject TexturedCube(
        string name,
        Vector3 position,
        Vector3 scale,
        Color tint,
        Texture2D texture,
        Vector2 tiling,
        Transform parent = null)
    {
        var objectInstance = Cube(name, position, scale, tint, parent);
        if (texture != null)
        {
            objectInstance.GetComponent<Renderer>().sharedMaterial = TexturedMaterial(tint, texture, tiling);
        }
        return objectInstance;
    }

    public static GameObject Cylinder(string name, Vector3 position, Vector3 scale, Color color, Transform parent = null)
    {
        var objectInstance = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        objectInstance.name = name;
        objectInstance.transform.SetParent(parent);
        objectInstance.transform.position = position;
        objectInstance.transform.localScale = scale;
        objectInstance.GetComponent<Renderer>().sharedMaterial = Material(color, 0.24f);
        return objectInstance;
    }

    public static GameObject Sphere(string name, Vector3 position, Vector3 scale, Color color, Transform parent = null)
    {
        var objectInstance = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        objectInstance.name = name;
        objectInstance.transform.SetParent(parent);
        objectInstance.transform.position = position;
        objectInstance.transform.localScale = scale;
        objectInstance.GetComponent<Renderer>().sharedMaterial = Material(color, 0.3f);
        return objectInstance;
    }

    public static TextMesh Label(string text, Vector3 position, float characterSize, Color color, Transform parent = null)
    {
        var objectInstance = new GameObject("Label_" + text);
        objectInstance.transform.SetParent(parent);
        objectInstance.transform.position = position;
        objectInstance.transform.rotation = Quaternion.Euler(55f, 0f, 0f);
        var label = objectInstance.AddComponent<TextMesh>();
        label.text = text;
        label.anchor = TextAnchor.MiddleCenter;
        label.alignment = TextAlignment.Center;
        label.characterSize = characterSize;
        label.fontSize = 48;
        label.color = color;
        return label;
    }

    public static void AddClickTarget(GameObject root, string targetId, string actionType)
    {
        var clickable = root.GetComponent<StoreClickable>() ?? root.AddComponent<StoreClickable>();
        clickable.Configure(targetId, actionType);
    }

    public static GameObject SpawnModel(string modelName, Vector3 position, Quaternion rotation, Vector3 scale, Transform parent = null)
    {
        var prefab = Resources.Load<GameObject>("Models/" + modelName);
        if (prefab == null)
        {
            Debug.LogWarning($"Model not found: Models/{modelName} — falling back to cube");
            return Cube(modelName, position, scale, Teal, parent);
        }

        var instance = Object.Instantiate(prefab, position, rotation, parent);
        instance.name = modelName;
        instance.transform.localScale = scale;
        return instance;
    }

    public static void AddProductCard(Transform parent, string productId, Vector3 position, float size = 0.42f)
    {
        var texture = Resources.Load<Texture2D>("Products/product-" + productId.PadLeft(3, '0'));
        if (texture == null)
        {
            return;
        }

        var card = TextureQuad("ProductArt_" + productId, texture, position, new Vector2(size, size), parent);
        card.AddComponent<StoreProductBillboard>();
    }

    public static GameObject TextureQuad(string name, Texture2D texture, Vector3 position, Vector2 size, Transform parent = null)
    {
        var quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
        quad.name = name;
        quad.transform.SetParent(parent);
        quad.transform.position = position;
        quad.transform.localScale = new Vector3(size.x, size.y, 1f);
        var collider = quad.GetComponent<Collider>();
        if (collider != null)
        {
            Object.Destroy(collider);
        }

        quad.GetComponent<Renderer>().sharedMaterial = TextureMaterial(texture);
        return quad;
    }

    public static GameObject MapBackdrop(Texture2D texture, Vector3 position, Vector2 size, Transform parent = null)
    {
        var backdrop = TextureQuad("MarketMapBackdrop", texture, position, size, parent);
        backdrop.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
        return backdrop;
    }

    public static GameObject AddAtlasBillboard(
        Transform parent,
        Texture2D texture,
        Vector3 position,
        Vector2 size,
        int atlasIndex)
    {
        var icon = TextureQuad("SectorArt_" + atlasIndex, texture, position, size, parent);
        var material = icon.GetComponent<Renderer>().sharedMaterial;
        var column = atlasIndex % 2;
        var row = atlasIndex / 2;
        material.mainTextureScale = new Vector2(0.46f, 0.46f);
        material.mainTextureOffset = new Vector2(0.02f + column * 0.5f, row == 0 ? 0.52f : 0.02f);
        icon.AddComponent<StoreProductBillboard>();
        return icon;
    }

    private static Material TextureMaterial(Texture2D texture)
    {
        var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Unlit/Transparent");
        return new Material(shader) { mainTexture = texture, color = Color.white };
    }

    private static Material TexturedMaterial(Color tint, Texture2D texture, Vector2 tiling)
    {
        var material = Material(tint, 0.2f);
        texture.wrapMode = TextureWrapMode.Repeat;
        material.mainTexture = texture;
        material.mainTextureScale = tiling;
        return material;
    }
}
