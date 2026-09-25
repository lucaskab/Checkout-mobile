using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class CheckoutRainUmbrellaBuilder
{
    const string SourcePath = "Assets/Art/Events/Rain/ColorfulUmbrella.glb";
    const string GeneratedFolder = "Assets/Art/Events/Rain/Generated";
    const string PrefabPath = "Assets/Art/Events/Rain/Resources/Rain/ColorfulUmbrella.prefab";
    const string MeshPath = GeneratedFolder + "/ColorfulUmbrellaMesh.asset";
    const string TexturePath = GeneratedFolder + "/ColorfulUmbrellaAlbedo.asset";
    const string MaterialPath = GeneratedFolder + "/ColorfulUmbrellaMaterial.mat";

    [MenuItem("Supermarket/Build rain umbrella from GLB")]
    public static void BuildAsset()
    {
        var existingPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        var existingTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
        if (existingPrefab && existingTexture && existingTexture.width <= 1024)
        {
            Debug.Log("CHECKOUT_RAIN_UMBRELLA_READY " + PrefabPath);
            return;
        }
        if (existingPrefab) AssetDatabase.DeleteAsset(PrefabPath);
        if (existingPrefab || existingTexture)
        {
            AssetDatabase.DeleteAsset(MaterialPath);
            AssetDatabase.DeleteAsset(MeshPath);
            AssetDatabase.DeleteAsset(TexturePath);
        }

        string absolutePath = Path.Combine(Directory.GetParent(Application.dataPath).FullName, SourcePath);
        if (!File.Exists(absolutePath)) throw new FileNotFoundException("Rain umbrella GLB not found", absolutePath);
        if (!AssetDatabase.IsValidFolder(GeneratedFolder)) AssetDatabase.CreateFolder("Assets/Art/Events/Rain", "Generated");
        if (!AssetDatabase.IsValidFolder("Assets/Art/Events/Rain/Resources/Rain")) AssetDatabase.CreateFolder("Assets/Art/Events/Rain/Resources", "Rain");

        var glb = Parse(File.ReadAllBytes(absolutePath));
        var meshData = glb.json.meshes[0].primitives[0];
        var mesh = new Mesh { name = "Colorful umbrella mesh", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
        var positions = ReadVectors3(glb, meshData.attributes.POSITION);
        var normals = ReadVectors3(glb, meshData.attributes.NORMAL);
        var uv = ReadVectors2(glb, meshData.attributes.TEXCOORD_0);
        var indices = ReadIndices(glb, meshData.indices);
        for (int i = 0; i < positions.Count; i++)
        {
            positions[i] = new Vector3(positions[i].x, positions[i].y, -positions[i].z);
            if (i < normals.Count) normals[i] = new Vector3(normals[i].x, normals[i].y, -normals[i].z);
            if (i < uv.Count) uv[i] = new Vector2(uv[i].x, 1 - uv[i].y);
        }
        for (int i = 0; i + 2 < indices.Length; i += 3) (indices[i + 1], indices[i + 2]) = (indices[i + 2], indices[i + 1]);
        mesh.SetVertices(positions);
        mesh.SetNormals(normals);
        mesh.SetUVs(0, uv);
        mesh.SetTriangles(indices, 0, true);
        mesh.RecalculateBounds();

        var textureBytes = ReadImage(glb, glb.json.materials[meshData.material].pbrMetallicRoughness.baseColorTexture.index);
        var texture = new Texture2D(2, 2, TextureFormat.RGBA32, true) { name = "Colorful umbrella albedo", wrapMode = TextureWrapMode.Repeat };
        if (!ImageConversion.LoadImage(texture, textureBytes, false)) throw new InvalidDataException("Could not decode the umbrella base-color image");
        if (Mathf.Max(texture.width, texture.height) > 1024)
        {
            float ratio = 1024f / Mathf.Max(texture.width, texture.height);
            texture.Reinitialize(Mathf.Max(1, Mathf.RoundToInt(texture.width * ratio)), Mathf.Max(1, Mathf.RoundToInt(texture.height * ratio)), TextureFormat.RGBA32, true);
            texture.Apply(true, true);
        }
        var material = new Material(Shader.Find("Standard")) { name = "Colorful umbrella material", mainTexture = texture };
        material.SetFloat("_Glossiness", .42f);
        material.SetFloat("_Metallic", 0);

        var savedMesh = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
        if (savedMesh) UnityEngine.Object.DestroyImmediate(mesh); else AssetDatabase.CreateAsset(mesh, MeshPath);
        mesh = savedMesh ? savedMesh : mesh;
        var savedTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
        if (savedTexture) UnityEngine.Object.DestroyImmediate(texture); else AssetDatabase.CreateAsset(texture, TexturePath);
        texture = savedTexture ? savedTexture : texture;
        var savedMaterial = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
        if (savedMaterial) UnityEngine.Object.DestroyImmediate(material); else AssetDatabase.CreateAsset(material, MaterialPath);
        material = savedMaterial ? savedMaterial : material;
        material.mainTexture = texture;
        EditorUtility.SetDirty(material);
        var root = new GameObject("Colorful umbrella");
        var surface = new GameObject("Umbrella mesh");
        surface.transform.SetParent(root.transform, false);
        surface.AddComponent<MeshFilter>().sharedMesh = mesh;
        surface.AddComponent<MeshRenderer>().sharedMaterial = material;
        var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        UnityEngine.Object.DestroyImmediate(root);
        if (!prefab) throw new InvalidOperationException("Could not save the rain umbrella prefab");
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log("CHECKOUT_RAIN_UMBRELLA_READY " + PrefabPath + " vertices=" + positions.Count + " triangles=" + indices.Length / 3);
    }

    static Gltf Parse(byte[] bytes)
    {
        if (bytes.Length < 20 || BitConverter.ToUInt32(bytes, 0) != 0x46546C67) throw new InvalidDataException("Invalid GLB header");
        int cursor = 12;
        string json = null;
        byte[] binary = null;
        while (cursor + 8 <= bytes.Length)
        {
            int length = (int)BitConverter.ToUInt32(bytes, cursor);
            uint type = BitConverter.ToUInt32(bytes, cursor + 4);
            int start = cursor + 8;
            if (start + length > bytes.Length) throw new InvalidDataException("Invalid GLB chunk length");
            if (type == 0x4E4F534A) json = System.Text.Encoding.UTF8.GetString(bytes, start, length).TrimEnd('\0', ' ', '\t', '\r', '\n');
            if (type == 0x004E4942)
            {
                binary = new byte[length];
                Buffer.BlockCopy(bytes, start, binary, 0, length);
            }
            cursor = start + length;
        }
        if (json == null || binary == null) throw new InvalidDataException("GLB must contain JSON and binary chunks");
        return new Gltf { json = JsonUtility.FromJson<Root>(json), binary = binary };
    }

    static List<Vector3> ReadVectors3(Gltf glb, int accessorIndex)
    {
        var accessor = glb.json.accessors[accessorIndex];
        var view = glb.json.bufferViews[accessor.bufferView];
        int stride = view.byteStride > 0 ? view.byteStride : 12;
        int start = view.byteOffset + accessor.byteOffset;
        var values = new List<Vector3>(accessor.count);
        for (int i = 0; i < accessor.count; i++)
        {
            int offset = start + i * stride;
            values.Add(new Vector3(BitConverter.ToSingle(glb.binary, offset), BitConverter.ToSingle(glb.binary, offset + 4), BitConverter.ToSingle(glb.binary, offset + 8)));
        }
        return values;
    }

    static List<Vector2> ReadVectors2(Gltf glb, int accessorIndex)
    {
        var accessor = glb.json.accessors[accessorIndex];
        var view = glb.json.bufferViews[accessor.bufferView];
        int stride = view.byteStride > 0 ? view.byteStride : 8;
        int start = view.byteOffset + accessor.byteOffset;
        var values = new List<Vector2>(accessor.count);
        for (int i = 0; i < accessor.count; i++)
        {
            int offset = start + i * stride;
            values.Add(new Vector2(BitConverter.ToSingle(glb.binary, offset), BitConverter.ToSingle(glb.binary, offset + 4)));
        }
        return values;
    }

    static int[] ReadIndices(Gltf glb, int accessorIndex)
    {
        var accessor = glb.json.accessors[accessorIndex];
        var view = glb.json.bufferViews[accessor.bufferView];
        int componentSize = accessor.componentType == 5125 ? 4 : accessor.componentType == 5123 ? 2 : 1;
        int stride = view.byteStride > 0 ? view.byteStride : componentSize;
        int start = view.byteOffset + accessor.byteOffset;
        var indices = new int[accessor.count];
        for (int i = 0; i < accessor.count; i++)
        {
            int offset = start + i * stride;
            indices[i] = componentSize == 4 ? (int)BitConverter.ToUInt32(glb.binary, offset) : componentSize == 2 ? BitConverter.ToUInt16(glb.binary, offset) : glb.binary[offset];
        }
        return indices;
    }

    static byte[] ReadImage(Gltf glb, int textureIndex)
    {
        int imageIndex = glb.json.textures[textureIndex].source;
        var image = glb.json.images[imageIndex];
        var view = glb.json.bufferViews[image.bufferView];
        var bytes = new byte[view.byteLength];
        Buffer.BlockCopy(glb.binary, view.byteOffset, bytes, 0, view.byteLength);
        return bytes;
    }

    sealed class Gltf { public Root json; public byte[] binary; }
    [Serializable] sealed class Root { public Accessor[] accessors; public BufferView[] bufferViews; public GltfMesh[] meshes; public GltfMaterial[] materials; public Texture[] textures; public Image[] images; }
    [Serializable] sealed class Accessor { public int bufferView; public int byteOffset; public int componentType; public int count; public int byteStride; }
    [Serializable] sealed class BufferView { public int byteOffset; public int byteLength; public int byteStride; }
    [Serializable] sealed class GltfMesh { public Primitive[] primitives; }
    [Serializable] sealed class Primitive { public Attributes attributes; public int indices; public int material; }
    [Serializable] sealed class Attributes { public int POSITION; public int NORMAL; public int TEXCOORD_0; }
    [Serializable] sealed class GltfMaterial { public MetallicRoughness pbrMetallicRoughness; }
    [Serializable] sealed class MetallicRoughness { public BaseColorTexture baseColorTexture; }
    [Serializable] sealed class BaseColorTexture { public int index; }
    [Serializable] sealed class Texture { public int source; }
    [Serializable] sealed class Image { public int bufferView; }
}
