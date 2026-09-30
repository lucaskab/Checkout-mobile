using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace Checkout
{
    // Ground painted in the map editor: roads, bike lanes, sidewalks, grass... on a 1 m grid, with road
    // markings painted on top as a second layer. Each kind is one combined mesh, rebuilt when cells change.
    public class CheckoutPaintLayer : MonoBehaviour
    {
        public const float Cell = 1f, GroundY = .153f, MarkY = .161f;
        public static readonly string[] GroundNames = { "Nada", "Asfalto", "Ciclovia", "Calçada", "Grama", "Piso", "Terra", "Água", "Concreto" };
        public static readonly string[] GroundColors = { "", "3A3D42", "C8453A", "D9D4C9", "6DAA45", "C9A27E", "9A7550", "4E9CC9", "B9B6AE" };
        public static readonly string[] MarkNames = { "Nada", "Tracejado ↔", "Tracejado ↕", "Faixa de pedestre ↔", "Faixa de pedestre ↕", "Linha amarela ↔", "Linha amarela ↕", "Linha branca ↔", "Linha branca ↕", "Seta ciclovia" };
        struct Paint { public byte ground, mark; }
        readonly Dictionary<Vector2Int, Paint> cells = new Dictionary<Vector2Int, Paint>();
        readonly Dictionary<string, MeshFilter> layers = new Dictionary<string, MeshFilter>();
        readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
        bool dirty;

        public int Count => cells.Count;
        public static Vector2Int CellAt(Vector3 world) => new Vector2Int(Mathf.FloorToInt(world.x / Cell), Mathf.FloorToInt(world.z / Cell));
        public static Vector3 CenterOf(Vector2Int c, float y) => new Vector3((c.x + .5f) * Cell, y, (c.y + .5f) * Cell);

        // ground < 0 or mark < 0 leave that layer as it is; 0 erases it.
        public bool Set(Vector2Int c, int ground, int mark)
        {
            cells.TryGetValue(c, out var p);
            var before = p;
            if (ground >= 0) p.ground = (byte)ground;
            if (mark >= 0) p.mark = (byte)mark;
            if (p.ground == 0 && p.mark == 0) { if (!cells.Remove(c)) return false; }
            else { if (cells.ContainsKey(c) && before.ground == p.ground && before.mark == p.mark) return false; cells[c] = p; }
            dirty = true; return true;
        }

        public void Clear() { if (cells.Count == 0) return; cells.Clear(); dirty = true; }

        public string Save()
        {
            var sb = new StringBuilder();
            foreach (var pair in cells)
                sb.Append(pair.Key.x).Append(',').Append(pair.Key.y).Append(',').Append(pair.Value.ground).Append(',').Append(pair.Value.mark).Append(';');
            return sb.ToString();
        }

        public void Load(string data)
        {
            cells.Clear(); dirty = true;
            if (string.IsNullOrEmpty(data)) { Rebuild(); return; }
            foreach (var entry in data.Split(';'))
            {
                var f = entry.Split(',');
                if (f.Length < 4) continue;
                if (int.TryParse(f[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out var x) && int.TryParse(f[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out var z)
                    && byte.TryParse(f[2], out var g) && byte.TryParse(f[3], out var m) && (g > 0 || m > 0))
                    cells[new Vector2Int(x, z)] = new Paint { ground = (byte)Mathf.Min(g, GroundNames.Length - 1), mark = (byte)Mathf.Min(m, MarkNames.Length - 1) };
            }
            Rebuild();
        }

        void LateUpdate() { if (dirty) Rebuild(); }

        void Rebuild()
        {
            dirty = false;
            var verts = new Dictionary<string, List<Vector3>>(); var uvs = new Dictionary<string, List<Vector2>>();
            foreach (var pair in cells)
            {
                var c = pair.Key; var p = pair.Value;
                if (p.ground > 0) Quad(verts, uvs, "g" + p.ground, c, GroundY, false);
                if (p.mark > 0) Quad(verts, uvs, "m" + p.mark, c, MarkY, p.mark == 2 || p.mark == 4 || p.mark == 6 || p.mark == 8);
            }
            foreach (var key in layers.Keys) if (!verts.ContainsKey(key)) layers[key].sharedMesh.Clear();
            foreach (var pair in verts)
            {
                if (!layers.TryGetValue(pair.Key, out var filter))
                {
                    var go = new GameObject("Paint " + pair.Key); go.transform.SetParent(transform, false);
                    filter = go.AddComponent<MeshFilter>(); filter.sharedMesh = new Mesh { name = "Paint " + pair.Key };
                    var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = MaterialFor(pair.Key); r.shadowCastingMode = ShadowCastingMode.Off;
                    layers[pair.Key] = filter;
                }
                var mesh = filter.sharedMesh; mesh.Clear();
                mesh.indexFormat = pair.Value.Count > 60000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
                mesh.SetVertices(pair.Value); mesh.SetUVs(0, uvs[pair.Key]);
                var tris = new int[pair.Value.Count / 4 * 6];
                for (int i = 0, v = 0; v < pair.Value.Count; v += 4, i += 6) { tris[i] = v; tris[i + 1] = v + 1; tris[i + 2] = v + 2; tris[i + 3] = v; tris[i + 4] = v + 2; tris[i + 5] = v + 3; }
                mesh.SetTriangles(tris, 0);
                var normals = new Vector3[pair.Value.Count]; var colors = new Color32[pair.Value.Count];
                for (int i = 0; i < normals.Length; i++) { normals[i] = Vector3.up; colors[i] = new Color32(255, 255, 255, 255); }
                mesh.normals = normals; mesh.colors32 = colors;
                mesh.RecalculateBounds();
            }
        }

        static void Quad(Dictionary<string, List<Vector3>> verts, Dictionary<string, List<Vector2>> uvs, string key, Vector2Int c, float y, bool turn)
        {
            if (!verts.TryGetValue(key, out var v)) { verts[key] = v = new List<Vector3>(); uvs[key] = new List<Vector2>(); }
            var uv = uvs[key];
            float x0 = c.x * Cell, z0 = c.y * Cell, x1 = x0 + Cell, z1 = z0 + Cell;
            v.Add(new Vector3(x0, y, z0)); v.Add(new Vector3(x0, y, z1)); v.Add(new Vector3(x1, y, z1)); v.Add(new Vector3(x1, y, z0));
            if (!turn) { uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(0, 1)); uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(1, 0)); }
            else { uv.Add(new Vector2(0, 1)); uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(1, 0)); uv.Add(new Vector2(0, 0)); }
        }

        Material MaterialFor(string key)
        {
            if (materials.TryGetValue(key, out var m)) return m;
            int kind = int.Parse(key.Substring(1));
            if (key[0] == 'g')
            {
                m = new Material(Shader.Find("Standard")) { name = "Paint " + GroundNames[kind] };
                m.mainTexture = GroundTexture(kind); m.SetFloat("_Glossiness", kind == 7 ? .6f : .05f);
                m.enableInstancing = true;
            }
            else
            {
                m = new Material(Shader.Find("Sprites/Default")) { name = "Paint mark " + kind };
                m.mainTexture = MarkTexture(kind); m.renderQueue = 2450;
            }
            materials[key] = m;
            return m;
        }

        public static Color C(string hex) { ColorUtility.TryParseHtmlString("#" + hex, out var c); return c; }

        // Small procedural textures (one per 1 m cell).
        public static Texture2D GroundTexture(int kind)
        {
            const int n = 64;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Bilinear, name = "Paint " + kind };
            var baseColor = C(GroundColors[Mathf.Clamp(kind, 1, GroundColors.Length - 1)]);
            var rnd = new System.Random(kind * 977);
            var px = new Color[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float noise = (float)rnd.NextDouble() - .5f;
                    var c = baseColor * (1 + noise * (kind == 1 ? .16f : kind == 4 ? .22f : kind == 6 ? .2f : .08f));
                    if (kind == 3 && (x % 32 == 0 || y % 32 == 0)) c *= .82f;                          // sidewalk slabs
                    if (kind == 5) { int row = y / 16; int off = row % 2 == 0 ? 0 : 16; if (y % 16 == 0 || (x + off) % 32 == 0) c *= .78f; } // pavers
                    if (kind == 8 && (x == 0 || y == 0)) c *= .86f;                                   // concrete joints
                    if (kind == 7) c = Color.Lerp(c, Color.white, Mathf.PerlinNoise(x * .15f, y * .15f) * .18f);
                    if (kind == 4 && rnd.NextDouble() < .06) c = Color.Lerp(c, C("9BCB6A"), .7f);   // grass blades
                    c.a = 1; px[y * n + x] = c;
                }
            t.SetPixels(px); t.Apply(true);
            return t;
        }

        public static Texture2D MarkTexture(int kind)
        {
            const int n = 64;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear, name = "Paint mark " + kind };
            var px = new Color[n * n];
            var white = new Color(.96f, .96f, .93f, 1); var yellow = C("F2C230");
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float u = (x + .5f) / n, v = (y + .5f) / n; Color c = Color.clear;
                    switch (kind)
                    {
                        case 1: case 2: if (Mathf.Abs(v - .5f) < .05f && u > .2f && u < .8f) c = white; break;          // dashed centre line
                        case 3: case 4: if (Mathf.Repeat(v, .5f) < .3f && u > .04f && u < .96f) c = white; break;         // zebra stripes
                        case 5: case 6: if (Mathf.Abs(v - .5f) < .055f) c = yellow; break;
                        case 7: case 8: if (Mathf.Abs(v - .5f) < .04f) c = white; break;
                        case 9:                                                                                   // bike symbol arrow
                            float ax = u - .5f, ay = v - .5f;
                            if ((Mathf.Abs(ax) < .06f && ay > -.32f && ay < .12f) || (ay >= .12f && ay < .34f && Mathf.Abs(ax) < (.34f - ay) * .9f)) c = white;
                            break;
                    }
                    px[y * n + x] = c;
                }
            t.SetPixels(px); t.Apply(true);
            return t;
        }

        void OnDestroy() { foreach (var m in materials.Values) if (m) { Destroy(m.mainTexture); Destroy(m); } foreach (var f in layers.Values) if (f) Destroy(f.sharedMesh); }
    }
}
