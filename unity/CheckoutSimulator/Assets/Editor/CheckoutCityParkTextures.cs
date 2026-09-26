using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

// Paints the seamless textures (albedo + normal map) used by the city scenery built by
// CheckoutCentralParkBuilder: aged brick, corrugated roofing, weathered timber, cut stone, granite,
// bronze, rust, concrete, foliage and so on. Every pattern is generated on a periodic lattice so it tiles.
// The look follows the game's hand-painted models: clean readable shapes, baked edge light and
// crevice shadow, moderate grain; relief comes from the normal map.
public static class CheckoutCityParkTextures
{
    public const string Folder = "Assets/Art/CityPark/Textures/";
    const int Size = 512;
    const string Version = "v2";

    public struct Surface { public Texture2D albedo, normal; public float tiling, bump; }
    static readonly Dictionary<string, Surface> cache = new Dictionary<string, Surface>();

    // metres per tile and normal strength for each kind.
    static readonly Dictionary<string, (float tiling, float bump)> kinds = new Dictionary<string, (float, float)>
    {
        {"brick",(2.4f,1.4f)}, {"corrugated_rust",(1.4f,1.6f)}, {"corrugated_paint",(1.4f,1.6f)}, {"concrete",(3f,.9f)},
        {"stone_blocks",(2.6f,1.3f)}, {"granite",(1.6f,.5f)}, {"wood",(1.3f,1.1f)}, {"castiron",(1.1f,.7f)},
        {"bronze",(1.2f,.8f)}, {"gold",(.9f,.7f)}, {"rust",(1.5f,1.2f)}, {"foliage",(.9f,1.5f)}, {"flowers",(.9f,1.4f)},
        {"soil",(1.1f,1.2f)}, {"canvas",(1.2f,.6f)}, {"awning",(1.6f,.6f)}, {"paint",(2f,.6f)}, {"paintedwood",(1.4f,1f)},
        {"mulch",(.9f,1.3f)}, {"pebbles",(.7f,1.5f)}, {"rock",(2.2f,1.6f)}, {"water",(2.4f,.8f)}, {"brushed",(.9f,.35f)}, {"dirtyglass",(1.4f,.3f)}, {"grate",(.9f,1.4f)},
    };

    public static bool Has(string kind) => kinds.ContainsKey(kind);

    public static Surface Get(string kind)
    {
        if (cache.TryGetValue(kind, out var cached) && cached.albedo && cached.normal) return cached;
        if (!AssetDatabase.IsValidFolder("Assets/Art/CityPark/Textures")) AssetDatabase.CreateFolder("Assets/Art/CityPark", "Textures");
        string albedoPath = Folder + kind + "_" + Version + "_albedo.png", normalPath = Folder + kind + "_" + Version + "_normal.png";
        if (!File.Exists(albedoPath) || !File.Exists(normalPath))
        {
            var color = new Color[Size * Size]; var height = new float[Size * Size];
            Paint(kind, color, height);
            BakeLight(color, height, kind);
            Save(albedoPath, color);
            Save(normalPath, Normals(height, 1f));
            AssetDatabase.ImportAsset(albedoPath); AssetDatabase.ImportAsset(normalPath);
            Configure(albedoPath, false); Configure(normalPath, true);
        }
        var surface = new Surface
        {
            albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(albedoPath),
            normal = AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath),
            tiling = kinds[kind].tiling, bump = kinds[kind].bump,
        };
        cache[kind] = surface;
        return surface;
    }

    static void Configure(string path, bool normal)
    {
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
        importer.sRGBTexture = !normal;
        importer.wrapMode = TextureWrapMode.Repeat;
        importer.mipmapEnabled = true;
        importer.maxTextureSize = Size;
        importer.anisoLevel = 4;
        importer.alphaSource = normal ? TextureImporterAlphaSource.None : TextureImporterAlphaSource.FromInput;
        importer.textureCompression = TextureImporterCompression.Compressed;
        importer.SaveAndReimport();
    }

    static void Save(string path, Color[] pixels)
    {
        var texture = new Texture2D(Size, Size, TextureFormat.RGBA32, false);
        texture.SetPixels(pixels); texture.Apply();
        File.WriteAllBytes(path, texture.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(texture);
    }

    // ------------------------------------------------------------------ periodic noise
    static float Hash(int x, int y, int seed)
    {
        unchecked
        {
            uint h = (uint)(x * 374761393 + y * 668265263 + seed * 1442695041);
            h = (h ^ (h >> 13)) * 1274126177u; h ^= h >> 16;
            return (h & 0xffffff) / 16777215f;
        }
    }
    static int Wrap(int i, int p) { i %= p; return i < 0 ? i + p : i; }
    static float Noise(float x, float y, int px, int py, int seed)
    {
        int x0 = Mathf.FloorToInt(x), y0 = Mathf.FloorToInt(y);
        float fx = x - x0, fy = y - y0; fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
        int ax = Wrap(x0, px), bx = Wrap(x0 + 1, px), ay = Wrap(y0, py), by = Wrap(y0 + 1, py);
        return Mathf.Lerp(Mathf.Lerp(Hash(ax, ay, seed), Hash(bx, ay, seed), fx), Mathf.Lerp(Hash(ax, by, seed), Hash(bx, by, seed), fx), fy);
    }
    // u, v in [0,1): fractal noise tiling over the texture, with separate x / y base frequencies.
    static float Fbm(float u, float v, int fx, int fy, int octaves, int seed)
    {
        float sum = 0, amp = .5f, norm = 0;
        for (int o = 0; o < octaves; o++)
        {
            int px = fx << o, py = fy << o;
            sum += amp * Noise(u * px, v * py, px, py, seed + o * 31); norm += amp; amp *= .5f;
        }
        return sum / norm;
    }
    static float Fbm(float u, float v, int f, int octaves, int seed) => Fbm(u, v, f, f, octaves, seed);
    // Cellular noise: distance to nearest and second nearest feature point, plus the cell id.
    static void Voronoi(float u, float v, int cells, int seed, out float f1, out float f2, out int id, out Vector2 toCenter)
    {
        float x = u * cells, y = v * cells; int cx = Mathf.FloorToInt(x), cy = Mathf.FloorToInt(y);
        f1 = f2 = 9; id = 0; toCenter = Vector2.zero;
        for (int j = -1; j <= 1; j++)
            for (int i = -1; i <= 1; i++)
            {
                int gx = cx + i, gy = cy + j, wx = Wrap(gx, cells), wy = Wrap(gy, cells);
                float px = gx + .15f + .7f * Hash(wx, wy, seed), py = gy + .15f + .7f * Hash(wx, wy, seed + 7);
                float d = new Vector2(px - x, py - y).magnitude;
                if (d < f1) { f2 = f1; f1 = d; id = wy * cells + wx; toCenter = new Vector2(px - x, py - y); }
                else if (d < f2) f2 = d;
            }
    }
    static Color C(string hex) { ColorUtility.TryParseHtmlString("#" + hex, out var c); return c; }
    static Color Mix(Color a, Color b, float t) => Color.Lerp(a, b, Mathf.Clamp01(t));
    static float Smooth(float a, float b, float x) { float t = Mathf.Clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }

    // ------------------------------------------------------------------ patterns
    static void Paint(string kind, Color[] color, float[] height)
    {
        for (int y = 0; y < Size; y++)
            for (int x = 0; x < Size; x++)
            {
                float u = (x + .5f) / Size, v = (y + .5f) / Size; int i = y * Size + x;
                Color c; float h, s;
                switch (kind)
                {
                    case "brick": Brick(u, v, out c, out h, out s); break;
                    case "corrugated_rust": Corrugated(u, v, true, out c, out h, out s); break;
                    case "corrugated_paint": Corrugated(u, v, false, out c, out h, out s); break;
                    case "concrete": Concrete(u, v, out c, out h, out s); break;
                    case "stone_blocks": StoneBlocks(u, v, out c, out h, out s); break;
                    case "granite": Granite(u, v, out c, out h, out s); break;
                    case "wood": Wood(u, v, false, out c, out h, out s); break;
                    case "paintedwood": Wood(u, v, true, out c, out h, out s); break;
                    case "castiron": Metal(u, v, C("2A3033"), C("1C2123"), .08f, out c, out h, out s); break;
                    case "brushed": Brushed(u, v, out c, out h, out s); break;
                    case "bronze": Bronze(u, v, out c, out h, out s); break;
                    case "gold": Gold(u, v, out c, out h, out s); break;
                    case "rust": Rust(u, v, out c, out h, out s); break;
                    case "foliage": Foliage(u, v, false, out c, out h, out s); break;
                    case "flowers": Foliage(u, v, true, out c, out h, out s); break;
                    case "soil": Soil(u, v, out c, out h, out s); break;
                    case "mulch": Mulch(u, v, out c, out h, out s); break;
                    case "pebbles": Pebbles(u, v, out c, out h, out s); break;
                    case "canvas": Canvas(u, v, false, out c, out h, out s); break;
                    case "awning": Canvas(u, v, true, out c, out h, out s); break;
                    case "paint": PaintedMetal(u, v, out c, out h, out s); break;
                    case "rock": Rock(u, v, out c, out h, out s); break;
                    case "water": Water(u, v, out c, out h, out s); break;
                    case "dirtyglass": DirtyGlass(u, v, out c, out h, out s); break;
                    case "grate": Grate(u, v, out c, out h, out s); break;
                    default: c = Color.white; h = 0; s = .3f; break;
                }
                c.a = Mathf.Clamp01(s); color[i] = c; height[i] = h;
            }
    }

    // Aged red brick in running bond: chipped arrises, sooty patches and recessed lime mortar.
    static void Brick(float u, float v, out Color c, out float h, out float s)
    {
        const int rows = 12, cols = 6;
        int row = Mathf.FloorToInt(v * rows);
        float bu = u * cols + (row % 2) * .5f; int col = Mathf.FloorToInt(bu);
        float lx = bu - col, ly = v * rows - row; int bx = Wrap(col, cols);
        float edge = Mathf.Min(Mathf.Min(lx, 1 - lx) * 2.1f, Mathf.Min(ly, 1 - ly));
        float chip = Fbm(u, v, 24, 3, 11);
        float mortar = 1 - Smooth(.05f, .11f, edge + (chip - .5f) * .05f);
        float r = Hash(bx, row, 3), r2 = Hash(bx, row, 5);
        var brick = Mix(Mix(C("9C4F36"), C("B8683F"), r), C("7A3C2B"), r2 > .82f ? .8f : 0);
        brick = Mix(brick, C("C98A5A"), Fbm(u, v, 16, 4, 9) * .35f - .05f);
        brick = Mix(brick, C("4A3129"), Smooth(.58f, .8f, Fbm(u, v, 3, 4, 21)) * .55f); // soot
        brick *= .92f + .16f * Fbm(u, v, 64, 2, 13);
        var lime = Mix(C("B9B1A0"), C("8E877A"), Fbm(u, v, 32, 3, 17));
        c = Mix(brick, lime, mortar);
        h = (1 - mortar) * (.75f + .25f * Smooth(0, .25f, edge)) + (chip - .5f) * .12f * (1 - mortar);
        s = Mathf.Lerp(.35f, .15f, mortar);
    }

    // Corrugated steel sheet: sine ribs, lapped sheet joints with bolts, rust bleeding from the joints.
    static void Corrugated(float u, float v, bool rusted, out Color c, out float h, out float s)
    {
        const int ribs = 9;
        float rib = .5f + .5f * Mathf.Cos(u * ribs * Mathf.PI * 2);
        float lap = Mathf.Abs(Mathf.Repeat(v * 2, 1) - .5f); float joint = 1 - Smooth(.44f, .5f, lap);
        float dent = Fbm(u, v, 4, 3, 41);
        float rustMask = Smooth(rusted ? .32f : .58f, rusted ? .55f : .72f, Fbm(u, v, 5, 5, 43) + joint * .25f + (1 - rib) * .05f);
        float streak = Fbm(u, v, 48, 4, 1, 47);
        var paint = Mix(C("6E7C78"), C("8F9A94"), rib * .6f + dent * .3f);
        var rust = Mix(C("7A3A1C"), C("B0602C"), Fbm(u, v, 20, 4, 45));
        rust = Mix(rust, C("4E2A1A"), Smooth(.6f, .85f, streak));
        c = Mix(paint, rust, Mathf.Max(rustMask, rusted ? .55f + .45f * streak * streak : 0));
        c *= .78f + .3f * rib;
        float bolt = 0;
        float bu = Mathf.Repeat(u * ribs, 1), bv = Mathf.Repeat(v * 2 + .5f, 1);
        if (Mathf.Abs(bu - .5f) < .09f && Mathf.Abs(bv - .5f) < .03f) bolt = 1;
        c = Mix(c, C("3A3432"), bolt);
        h = rib * .8f + (dent - .5f) * .25f + joint * .15f + bolt * .3f;
        s = Mathf.Lerp(.45f, .15f, rustMask);
    }

    static void Concrete(float u, float v, out Color c, out float h, out float s)
    {
        float baseN = Fbm(u, v, 6, 5, 61);
        c = Mix(C("8C8A84"), C("A9A69D"), baseN);
        float stain = Smooth(.55f, .8f, Fbm(u, v, 3, 4, 63));
        c = Mix(c, C("5E5A52"), stain * .5f);
        float pores = Hash(Mathf.FloorToInt(u * 180), Mathf.FloorToInt(v * 180), 65) > .93f ? 1 : 0;
        Voronoi(u, v, 5, 67, out float f1, out float f2, out _, out _);
        float crackMask = Smooth(.5f, .65f, Fbm(u, v, 4, 3, 69));
        float crack = (1 - Smooth(.0f, .025f, f2 - f1)) * crackMask;
        c = Mix(c, C("3B3934"), Mathf.Max(crack, pores * .6f));
        c *= .94f + .1f * Fbm(u, v, 96, 2, 71);
        h = baseN * .3f - crack * .7f - pores * .25f;
        s = .2f;
    }

    // Cut stone (ashlar) courses with tooled faces, pale joints and weathered arrises.
    static void StoneBlocks(float u, float v, out Color c, out float h, out float s)
    {
        const int courses = 6;
        int row = Mathf.FloorToInt(v * courses); float ly = v * courses - row;
        int per = 3 + (row % 2);
        float offset = Hash(0, row, 81);
        float bu = Mathf.Repeat(u + offset, 1) * per; int col = Mathf.FloorToInt(bu); float lx = bu - col;
        float edge = Mathf.Min(Mathf.Min(lx, 1 - lx) * per / (float)courses * 1.9f, Mathf.Min(ly, 1 - ly));
        float tool = Fbm(u, v, 40, 3, 83);
        float joint = 1 - Smooth(.035f, .08f, edge + (tool - .5f) * .03f);
        float r = Hash(col, row, 85);
        var stone = Mix(C("9D978B"), C("B8B1A3"), r * .8f + Fbm(u, v, 8, 4, 87) * .4f);
        stone = Mix(stone, C("6F6A60"), Smooth(.55f, .85f, Fbm(u, v, 4, 4, 89)) * .45f);
        stone *= .9f + .18f * tool;
        c = Mix(stone, C("C9C2B2"), joint * .85f);
        float bevel = Smooth(0, .18f, edge);
        h = (1 - joint) * (.55f + .45f * bevel) + (tool - .5f) * .2f * (1 - joint);
        s = .25f;
    }

    static void Granite(float u, float v, out Color c, out float h, out float s)
    {
        float grain = Fbm(u, v, 48, 3, 91);
        c = Mix(C("B9B3A8"), C("CFC9BE"), grain);
        float dark = Hash(Mathf.FloorToInt(u * 260), Mathf.FloorToInt(v * 260), 93);
        float pink = Hash(Mathf.FloorToInt(u * 170), Mathf.FloorToInt(v * 170), 95);
        if (dark > .9f) c = Mix(c, C("3F3C39"), .8f);
        else if (pink > .93f) c = Mix(c, C("C39C8A"), .7f);
        c = Mix(c, C("8F897F"), Smooth(.6f, .9f, Fbm(u, v, 3, 4, 97)) * .35f);
        h = grain * .25f - (dark > .9f ? .1f : 0);
        s = .55f + .2f * grain;
    }

    // Timber boards: grain lines, knots and dark gaps; the painted variant wears through at the edges.
    static void Wood(float u, float v, bool painted, out Color c, out float h, out float s)
    {
        const int boards = 7;
        int board = Mathf.FloorToInt(v * boards); float lv = v * boards - board;
        float warp = Fbm(u, v, 3, 12, 3, 101 + board);
        float grain = .5f + .5f * Mathf.Sin((lv * 9 + warp * 5 + Hash(board, 0, 103) * 6) * Mathf.PI * 2);
        grain = Mathf.Lerp(grain, Fbm(u, v, 2, 64, 3, 105), .35f);
        float knotU = Hash(board, 1, 107), knot = 1 - Smooth(.0f, .05f, new Vector2((Mathf.Repeat(u - knotU + .5f, 1) - .5f) * .5f, (lv - .5f) / boards).magnitude);
        float gap = 1 - Smooth(.03f, .08f, Mathf.Min(lv, 1 - lv));
        var wood = Mix(C("8B5E3B"), C("B98A5A"), Hash(board, 2, 109) * .6f + grain * .4f);
        wood = Mix(wood, C("5A3A22"), knot * .8f + (1 - grain) * .15f);
        c = Mix(wood, C("2B1D14"), gap);
        h = (1 - gap) * (.7f + grain * .15f) - knot * .15f;
        s = .25f;
        if (painted)
        {
            float wear = Smooth(.62f, .78f, Fbm(u, v, 10, 4, 111) + (1 - Smooth(0, .18f, Mathf.Min(lv, 1 - lv))) * .35f);
            var paint = Mix(C("E8E2D4"), C("D3CCBC"), Fbm(u, v, 30, 3, 113));
            c = Mix(Mix(paint, C("2B1D14"), gap), wood, wear);
            h += (1 - wear) * .08f;
            s = Mathf.Lerp(.45f, .25f, wear);
        }
    }

    static void Metal(float u, float v, Color a, Color b, float wearAmount, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 16, 4, 121);
        c = Mix(a, b, n);
        float scratch = 1 - Smooth(.0f, .012f, Mathf.Abs(Fbm(u, v, 2, 40, 3, 123) - .5f));
        float wear = Smooth(1 - wearAmount - .1f, 1 - wearAmount, Fbm(u, v, 12, 4, 125));
        c = Mix(c, C("7C8082"), Mathf.Max(scratch * .35f, wear * .7f));
        c = Mix(c, C("6B3A22"), Smooth(.72f, .85f, Fbm(u, v, 6, 4, 127)) * .35f);
        h = n * .2f - scratch * .1f;
        s = .45f - wear * .15f;
    }

    static void Brushed(float u, float v, out Color c, out float h, out float s)
    {
        float lines = Fbm(u, v, 3, 128, 3, 131);
        c = Mix(C("9DA3A6"), C("C7CBCC"), lines);
        c = Mix(c, C("6F7477"), Smooth(.65f, .9f, Fbm(u, v, 4, 4, 133)) * .3f);
        h = lines * .15f; s = .7f;
    }

    static void Bronze(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 12, 5, 141);
        c = Mix(C("5C4428"), C("8A6A3E"), n);
        float patina = Smooth(.5f, .7f, Fbm(u, v, 5, 5, 143));
        c = Mix(c, C("5C8C78"), patina * .75f);
        h = n * .5f; s = Mathf.Lerp(.6f, .3f, patina);
    }

    static void Gold(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 20, 4, 151);
        c = Mix(C("B8862E"), C("F2CC6A"), n);
        h = n * .4f; s = .75f;
    }

    static void Rust(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 8, 5, 161), pits = Fbm(u, v, 64, 2, 163);
        c = Mix(C("6A2F18"), C("B15F2A"), n);
        c = Mix(c, C("3E2014"), Smooth(.6f, .8f, pits) * .6f);
        float paint = Smooth(.62f, .7f, Fbm(u, v, 5, 4, 165));
        c = Mix(c, C("5E6B63"), paint * .8f);
        h = n * .4f - Smooth(.6f, .8f, pits) * .3f + paint * .15f;
        s = .15f + paint * .2f;
    }

    // Dense leaf clusters: each cell is a leaf, lit from above, darker towards the gaps.
    static void Foliage(float u, float v, bool flowers, out Color c, out float h, out float s)
    {
        Voronoi(u, v, 22, 171, out float f1, out float f2, out int id, out Vector2 toCenter);
        float leaf = Smooth(.0f, .35f, f2 - f1);
        float r = Hash(id, 0, 173);
        c = Mix(C("2F5A26"), C("6FA046"), r * .7f + leaf * .4f + toCenter.y * .6f);
        c *= .55f + .5f * leaf;
        h = leaf;
        s = .3f;
        if (flowers && Hash(id, 1, 175) > .72f)
        {
            float petal = 1 - Smooth(.12f, .22f, f1);
            var bloom = Hash(id, 2, 177) > .5f ? C("E48AA6") : C("F2CD55");
            c = Mix(c, bloom * (.8f + .3f * leaf), petal);
            h += petal * .3f;
        }
    }

    static void Soil(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 10, 5, 181);
        c = Mix(C("3E2E22"), C("6A5140"), n);
        Voronoi(u, v, 30, 183, out float f1, out _, out int id, out _);
        float pebble = (Hash(id, 0, 185) > .7f ? 1 : 0) * (1 - Smooth(.18f, .3f, f1));
        c = Mix(c, Mix(C("8C8274"), C("B3A895"), Hash(id, 1, 187)), pebble);
        h = n * .5f + pebble * .5f; s = .12f + pebble * .2f;
    }

    // Tree beds: warm bark mulch with a few pebbles and moss, and a ring of rounded garden stones.
    static void Mulch(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 8, 4, 301);
        c = Mix(C("5A3B24"), C("7A5232"), n);
        Voronoi(u, v, 46, 303, out float f1, out float f2, out int id, out _);
        float chip = Smooth(0, .12f, f2 - f1);
        c = Mix(c * .72f, Mix(C("8A5C36"), C("A8744A"), Hash(id, 0, 305)), chip * (Hash(id, 1, 307) > .35f ? 1 : .5f));
        float moss = Smooth(.66f, .76f, Fbm(u, v, 6, 4, 309));
        c = Mix(c, C("6F8A3C"), moss * .55f);
        Voronoi(u, v, 14, 311, out float p1, out _, out int pid, out _);
        float pebble = (Hash(pid, 0, 313) > .8f ? 1 : 0) * (1 - Smooth(.2f, .3f, p1));
        c = Mix(c, Mix(C("C9BCA4"), C("E2D8C4"), Hash(pid, 1, 315)), pebble);
        h = chip * .45f + n * .25f + pebble * .6f; s = .1f + pebble * .2f;
    }

    static void Pebbles(float u, float v, out Color c, out float h, out float s)
    {
        Voronoi(u, v, 18, 321, out float f1, out float f2, out int id, out Vector2 toCenter);
        float gap = Smooth(.02f, .14f, f2 - f1);
        float r = Hash(id, 0, 323);
        var stone = r < .45f ? Mix(C("D9CCB2"), C("E9E0CE"), Hash(id, 1, 325)) : r < .8f ? Mix(C("B9AD98"), C("CFC4AE"), Hash(id, 2, 327)) : Mix(C("A8886A"), C("C29E78"), Hash(id, 3, 329));
        float dome = Mathf.Sqrt(Mathf.Clamp01(1 - toCenter.magnitude * 1.8f));
        stone *= .82f + .25f * dome + .06f * Fbm(u, v, 60, 2, 331);
        c = Mix(C("6A5A48"), stone, gap);
        h = gap * (.35f + .65f * dome); s = .22f;
    }

    static void Canvas(float u, float v, bool striped, out Color c, out float h, out float s)
    {
        float weave = .5f + .25f * (Mathf.Sin(u * Mathf.PI * 2 * 96) * Mathf.Sin(v * Mathf.PI * 2 * 96));
        float fold = Fbm(u, v, 3, 3, 191);
        c = Mix(C("E2DCCE"), C("F1ECE0"), fold * .35f + weave * .15f);
        if (striped && Mathf.Repeat(u * 8, 1) < .5f) c *= .62f;
        c = Mix(c, C("7A7466"), Smooth(.7f, .92f, Fbm(u, v, 4, 4, 193)) * .12f);
        h = fold * .35f + weave * .08f; s = .15f;
    }

    // Light painted surface (tinted by the material colour): orange peel, grime, scratches and chips.
    static void PaintedMetal(float u, float v, out Color c, out float h, out float s)
    {
        float peel = Fbm(u, v, 40, 2, 201);
        c = Mix(C("E4E1DA"), C("F4F1EA"), peel);
        c = Mix(c, C("8E877A"), Smooth(.55f, .85f, Fbm(u, v, 3, 5, 203)) * .4f);
        float chip = Smooth(.8f, .83f, Fbm(u, v, 10, 4, 205));
        float scratch = 1 - Smooth(.0f, .006f, Mathf.Abs(Fbm(u, v, 12, 2, 3, 207) - .5f));
        c = Mix(c, C("5A5550"), Mathf.Max(chip * .7f, scratch * .25f));
        h = peel * .1f - chip * .25f - scratch * .08f; s = .45f - chip * .3f;
    }

    // Layered schist with lichen.
    static void Rock(float u, float v, out Color c, out float h, out float s)
    {
        float warp = Fbm(u, v, 3, 4, 211);
        float layers = .5f + .5f * Mathf.Sin((v * 7 + warp * 2.5f) * Mathf.PI * 2);
        float n = Fbm(u, v, 12, 5, 213);
        c = Mix(C("5F5C57"), C("9A958B"), layers * .5f + n * .5f);
        Voronoi(u, v, 6, 215, out float f1, out float f2, out _, out _);
        float crack = 1 - Smooth(.0f, .03f, f2 - f1);
        c = Mix(c, C("2F2D2A"), crack * .8f);
        float lichen = Smooth(.64f, .74f, Fbm(u, v, 9, 4, 217));
        c = Mix(c, Mix(C("9CA35A"), C("C9B866"), Fbm(u, v, 30, 2, 219)), lichen * .7f);
        h = layers * .4f + n * .4f - crack * .6f; s = .2f;
    }

    static void Water(float u, float v, out Color c, out float h, out float s)
    {
        float n = Fbm(u, v, 6, 5, 221);
        c = Mix(C("2C6F82"), C("4F9BA8"), n);
        h = Fbm(u, v, 10, 4, 223) * .6f + n * .4f; s = .95f;
    }

    static void DirtyGlass(float u, float v, out Color c, out float h, out float s)
    {
        float smudge = Fbm(u, v, 4, 5, 231);
        c = Mix(C("2A3A40"), C("5D6E70"), Smooth(.45f, .85f, smudge));
        c = Mix(c, C("8B8676"), Smooth(.72f, .9f, Fbm(u, v, 3, 20, 3, 233)) * .5f); // drips
        h = smudge * .1f; s = Mathf.Lerp(.85f, .35f, smudge);
    }

    static void Grate(float u, float v, out Color c, out float h, out float s)
    {
        float gx = Mathf.Repeat(u * 10, 1), gy = Mathf.Repeat(v * 5, 1);
        float slot = (Mathf.Abs(gx - .5f) < .22f && Mathf.Abs(gy - .5f) < .38f) ? 1 : 0;
        Metal(u, v, C("2E3334"), C("1E2223"), .12f, out c, out h, out s);
        c = Mix(c, C("0E0F0F"), slot);
        h = 1 - slot + h;
    }

    // ------------------------------------------------------------------ lighting and normals
    // Hand-painted cue: brighten faces tilted towards a top-left light, darken crevices.
    static void BakeLight(Color[] color, float[] height, string kind)
    {
        float strength = kind == "water" || kind == "dirtyglass" || kind == "granite" ? .12f : .38f;
        var result = new Color[color.Length];
        for (int y = 0; y < Size; y++)
            for (int x = 0; x < Size; x++)
            {
                float dx = height[y * Size + Wrap(x + 1, Size)] - height[y * Size + Wrap(x - 1, Size)];
                float dy = height[Wrap(y + 1, Size) * Size + x] - height[Wrap(y - 1, Size) * Size + x];
                float light = (-dx + dy) * Size / 64f; // light from the upper left
                float cavity = 0;
                for (int k = 1; k <= 3; k++)
                {
                    int r = k * 3;
                    cavity += height[y * Size + x] - .25f * (height[y * Size + Wrap(x + r, Size)] + height[y * Size + Wrap(x - r, Size)] + height[Wrap(y + r, Size) * Size + x] + height[Wrap(y - r, Size) * Size + x]);
                }
                var c = color[y * Size + x];
                float shade = 1 + Mathf.Clamp(light, -1, 1) * strength + Mathf.Clamp(cavity, -.6f, .4f) * strength * .8f;
                result[y * Size + x] = new Color(c.r * shade, c.g * shade, c.b * shade, c.a);
            }
        Array.Copy(result, color, color.Length);
    }

    static Color[] Normals(float[] height, float strength)
    {
        var normals = new Color[height.Length];
        float scale = Size / 64f * strength * 4;
        for (int y = 0; y < Size; y++)
            for (int x = 0; x < Size; x++)
            {
                float dx = height[y * Size + Wrap(x + 1, Size)] - height[y * Size + Wrap(x - 1, Size)];
                float dy = height[Wrap(y + 1, Size) * Size + x] - height[Wrap(y - 1, Size) * Size + x];
                var n = new Vector3(-dx * scale, -dy * scale, 1).normalized;
                normals[y * Size + x] = new Color(n.x * .5f + .5f, n.y * .5f + .5f, n.z * .5f + .5f, 1);
            }
        return normals;
    }
}
