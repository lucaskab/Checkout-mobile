using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // "Cores do mercado" (Lucas 30/10): the player repaints the market in two colours of their choice. The market's
    // brand is navy #1D2B4F (with its support blue) and gold #D3A53D, from the sidewalk table to the chain; the
    // player's "cor principal" takes the place of the navy family and the "cor de destaque" the place of the gold.
    //
    // How (MarketPaint.cginc): only the market's own renderers (the shell, the stage dressing, the stall models and the
    // furniture placed in the shop) get painted copies of their materials, and only while a palette other than Clássico
    // is on; Clássico puts the original materials back, so a player who never repaints draws exactly what was drawn
    // before. Each material is classified once (Classify): a flat navy / gold colour is repainted whole, the era atlases
    // use a mask baked offline (Resources/CheckoutPaint/*_PaintMask.png), a few reviewed textures with navy or gold
    // parts use a tight colour key, everything else (products, people, lamps, hazard stripes, the sector colours…) is
    // left alone. The colours themselves are two global vectors, so trying colours in the picker costs nothing.
    // The HUD stays navy and gold: it is the game's brand, not the player's shop.
    public class CheckoutMarketPaint : MonoBehaviour
    {
        public const string ClassicPrimary = "1D2B4F", ClassicAccent = "D3A53D";
        public static CheckoutMarketPaint Active { get; private set; }

        // The player's colours (snapshot) and what the market shows now (they differ while the picker previews).
        public string SavedPrimary { get; private set; } = ClassicPrimary;
        public string SavedAccent { get; private set; } = ClassicAccent;
        public string ShownPrimary { get; private set; } = ClassicPrimary;
        public string ShownAccent { get; private set; } = ClassicAccent;
        public PaintState State { get; private set; }
        public bool Previewing { get; private set; }
        public bool Painting => !IsClassic(ShownPrimary, ShownAccent);
        /// <summary>Renderers and materials painted now (QA log).</summary>
        public int PaintedRenderers => tracked.Count;
        public int PaintedMaterials => originalOf.Count;

        Transform world;
        // Market roots under "Supermarket World"; the stall models are its children named "Era…". The storages (the
        // stock room "Warehouse" and the central warehouse "Warehouse Large") wear the market's colours too (Lucas 30/10).
        static readonly string[] Roots = { "Market Shell", "Market Stage Dressing", "Market Interior", "Warehouse", "Warehouse Large" };
        static readonly string[] Storages = { "Warehouse Large", "Warehouse" };
        // Never inside these (builders, scaffolding, the construction show, staff and shoppers).
        static readonly string[] SkipBranches = { "Construction", "Works", "Builder", "Scaffold", "Worker", "Staff", "Customer", "Shopper" };

        readonly Dictionary<Material, Material> paintedOf = new Dictionary<Material, Material>();   // original → copy (null: left alone)
        readonly Dictionary<Material, Material> originalOf = new Dictionary<Material, Material>();  // copy → original
        readonly HashSet<Renderer> tracked = new HashSet<Renderer>();
        readonly Dictionary<Renderer, bool> eligible = new Dictionary<Renderer, bool>(); // false: under a skipped branch
        readonly List<Transform> roots = new List<Transform>();
        int nextRoot;
        Transform interior;
        readonly List<Renderer> scratch = new List<Renderer>();
        readonly List<Material> mats = new List<Material>();
        float nextScan;
        static Shader painted;

        public void Initialize(Transform root) { world = root; Active = this; }
        void OnDestroy() { if (Active == this) Active = null; }

        // ------------------------------------------------------------------ state
        public static string Norm(string hex)
        {
            hex = (hex ?? "").Trim().TrimStart('#').ToUpperInvariant();
            if (hex.Length != 6) return "";
            foreach (var c in hex) if (!System.Uri.IsHexDigit(c)) return "";
            return hex;
        }
        public static bool IsClassic(string primary, string accent) =>
            (Norm(primary) == ClassicPrimary || Norm(primary) == "") && (Norm(accent) == ClassicAccent || Norm(accent) == "");

        /// <summary>The player's palette from the game state (every snapshot).</summary>
        public void Apply(PaintState state)
        {
            State = state;
            var p = Norm(state?.primary); var a = Norm(state?.accent);
            SavedPrimary = p == "" ? ClassicPrimary : p; SavedAccent = a == "" ? ClassicAccent : a;
            if (!Previewing) Show(SavedPrimary, SavedAccent);
        }

        /// <summary>The picker tries colours on the market (nothing is saved).</summary>
        public void Preview(string primary, string accent) { Previewing = true; Show(primary, accent); }
        /// <summary>The picker closed: back to the player's colours (the new ones, once the purchase landed).</summary>
        public void EndPreview() { Previewing = false; Show(SavedPrimary, SavedAccent); }
        /// <summary>The purchase landed: these are the player's colours now (the snapshot confirms them a moment later).</summary>
        public void Adopt(string primary, string accent)
        {
            var p = Norm(primary); var a = Norm(accent);
            if (p != "") SavedPrimary = p; if (a != "") SavedAccent = a;
            EndPreview();
        }

        void Show(string primary, string accent)
        {
            primary = Norm(primary); accent = Norm(accent);
            if (primary == "") primary = ClassicPrimary; if (accent == "") accent = ClassicAccent;
            bool was = Painting;
            ShownPrimary = primary; ShownAccent = accent;
            if (!Painting) { if (was) RestoreAll(); return; }
            Shader.SetGlobalVector("_MarketPaintPrimary", Oklab(primary));
            Shader.SetGlobalVector("_MarketPaintAccent", Oklab(accent));
            if (!was) { Scan(); nextScan = Time.unscaledTime + .5f; }
        }

        /// <summary>The storage building standing now (the central warehouse, else the stock room), for the picker's camera.</summary>
        public bool StorageBounds(out Bounds bounds)
        {
            bounds = default;
            if (!world) return false;
            foreach (var name in Storages)
            {
                var t = world.Find(name);
                if (!t || !t.gameObject.activeInHierarchy) continue;
                bool any = false;
                foreach (var r in t.GetComponentsInChildren<MeshRenderer>(false))
                {
                    if (!r.enabled) continue;
                    if (!any) { bounds = r.bounds; any = true; } else bounds.Encapsulate(r.bounds);
                }
                if (any) return true;
            }
            return false;
        }

        /// <summary>A piece just built or shown (furniture placed, a stall model loaded): painted at once.</summary>
        public static void Touch(GameObject go) { if (Active && Active.Painting && go) Active.PaintUnder(go.transform); }

        // Pieces appear (furniture placed, stage dressing shown) and other code swaps materials (the faded canopies):
        // while painted, one market root is checked every half second (each root about every 3 s), so no frame pays
        // for the whole market at once.
        void Update()
        {
            if (!Painting || Time.unscaledTime < nextScan) return;
            nextScan = Time.unscaledTime + .5f;
            if (nextRoot == 0) CollectRoots();
            if (roots.Count == 0) return;
            var root = roots[nextRoot % roots.Count];
            nextRoot = (nextRoot + 1) % roots.Count;
            if (root) PaintUnder(root);
        }

        void CollectRoots()
        {
            roots.Clear();
            if (!world) return;
            foreach (var name in Roots) { var t = world.Find(name); if (t) roots.Add(t); }
            // The furniture placed in the shop lives in its own scene object (CheckoutInterior's holder).
            if (!interior) { var go = GameObject.Find("Market Interior"); interior = go ? go.transform : null; }
            if (interior) roots.Add(interior);
            foreach (Transform child in world) if (child.name.StartsWith("Era")) roots.Add(child);
        }

        /// <summary>Paints everything of the market now (first paint, QA). Returns the milliseconds it took.</summary>
        public double Scan()
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            CollectRoots();
            foreach (var root in roots) if (root) PaintUnder(root);
            return watch.Elapsed.TotalMilliseconds;
        }
        /// <summary>One periodic step (QA: what a frame pays while painted). Returns the milliseconds it took.</summary>
        public double QaStep()
        {
            var watch = System.Diagnostics.Stopwatch.StartNew();
            if (roots.Count == 0) CollectRoots();
            if (roots.Count > 0) { var root = roots[nextRoot % roots.Count]; nextRoot = (nextRoot + 1) % roots.Count; if (root) PaintUnder(root); }
            return watch.Elapsed.TotalMilliseconds;
        }

        void PaintUnder(Transform root)
        {
            root.GetComponentsInChildren(true, scratch);
            foreach (var r in scratch) PaintRenderer(r, root);
            scratch.Clear();
        }

        void PaintRenderer(Renderer r, Transform root)
        {
            if (!(r is MeshRenderer) || !r) return;
            if (!eligible.TryGetValue(r, out var ok)) eligible[r] = ok = !Skipped(r.transform, root);
            if (!ok) return;
            r.GetSharedMaterials(mats);
            bool changed = false;
            for (int i = 0; i < mats.Count; i++)
            {
                var m = mats[i];
                if (!m || originalOf.ContainsKey(m)) continue;
                var copy = PaintedCopy(m);
                if (!copy) continue;
                mats[i] = copy; changed = true;
            }
            if (changed) { r.sharedMaterials = mats.ToArray(); tracked.Add(r); }
            mats.Clear();
        }

        static bool Skipped(Transform t, Transform root)
        {
            for (var p = t; p && p != root; p = p.parent)
            {
                var n = p.name;
                foreach (var s in SkipBranches) if (n.IndexOf(s, System.StringComparison.OrdinalIgnoreCase) >= 0) return true;
                if (p.GetComponent<Animator>()) return true;
            }
            return false;
        }

        void RestoreAll()
        {
            foreach (var r in tracked)
            {
                if (!r) continue;
                r.GetSharedMaterials(mats);
                bool changed = false;
                for (int i = 0; i < mats.Count; i++)
                    if (mats[i] && originalOf.TryGetValue(mats[i], out var original)) { mats[i] = original; changed = true; }
                if (changed) r.sharedMaterials = mats.ToArray();
                mats.Clear();
            }
            tracked.Clear();
        }

        // ------------------------------------------------------------------ materials
        Material PaintedCopy(Material m)
        {
            if (paintedOf.TryGetValue(m, out var cached)) return cached;
            Material copy = null;
            int kind = Classify(m, out var mask);
            if (kind != 0)
            {
                var shader = m.shader.name;
                if (shader == "Standard")
                {
                    if (!painted) painted = Shader.Find("MarketDay/Painted Standard");
                    if (painted)
                    {
                        copy = new Material(painted);
                        copy.SetColor("_Color", m.color);
                        copy.mainTexture = m.mainTexture; copy.mainTextureScale = m.mainTextureScale; copy.mainTextureOffset = m.mainTextureOffset;
                        copy.SetFloat("_Glossiness", m.GetFloat("_Glossiness")); copy.SetFloat("_Metallic", m.GetFloat("_Metallic"));
                        if (m.IsKeywordEnabled("_NORMALMAP") && m.GetTexture("_BumpMap"))
                        { copy.SetTexture("_BumpMap", m.GetTexture("_BumpMap")); copy.SetFloat("_BumpScale", m.GetFloat("_BumpScale")); copy.EnableKeyword("_NORMALMAP"); }
                        if (m.IsKeywordEnabled("_EMISSION"))
                        { copy.SetColor("_EmissionColor", m.GetColor("_EmissionColor")); if (m.GetTexture("_EmissionMap")) copy.SetTexture("_EmissionMap", m.GetTexture("_EmissionMap")); }
                        else copy.SetColor("_EmissionColor", Color.black);
                    }
                }
                else { copy = new Material(m); copy.EnableKeyword("MARKET_PAINT"); }
                if (copy)
                {
                    copy.name = m.name + " (paint)";
                    copy.SetFloat("_PaintWhole", kind == 1 ? 1 : kind == 2 ? 2 : 0);
                    copy.SetFloat("_PaintUseMask", kind == 3 ? 1 : 0);
                    if (mask) copy.SetTexture("_PaintMask", mask);
                    originalOf[copy] = m;
                }
            }
            paintedOf[m] = copy;
            return copy;
        }

        // Materials that may look navy or gold but are not the market's paint: lights, people, products, the sector
        // awnings, construction and hazard yellows, cheese, flowers, balloons, screens, glass…
        static readonly string[] NotPaint =
        {
            "Glow", "Bulb", "Led", "Lamp", "Light", "HardHat", "Hazard", "Crane", "Cone", "Cheese", "Rind", "Mustard", "Products",
            "Balloon", "Bloom", "Flower", "Leaf", "Polo", "Yellow", "IK_Awning_", "IK_PS_", "Stripes", "Labels", "Screen", "Glass",
            "Worker", "Staff", "Customer", "Solar", "Graffiti", "Hoarding", "LotBillboard", "Photo", "PromoCard", "CanPyramid", "Ride",
        };
        // Textures that are all navy / all gold, and textures reviewed for a colour key (navy or gold parts on them).
        static readonly HashSet<string> WholeNavy = new HashSet<string> { "MS_NavyPanel_albedo", "MS_Cladding_albedo", "IK_V2_PaintNavy_albedo" };
        static readonly HashSet<string> WholeGold = new HashSet<string> { "MS_Gold_albedo" };
        static readonly HashSet<string> Keyed = new HashSet<string>
        {
            "MS_Awning_albedo", "IK_PriceRail_albedo", "IK_V2_SignCart_albedo", "IK_V3_ClawArt_albedo", "IK_V3_CupSign_albedo",
            "IK_D4_Atm_albedo", "IK_D4_Bench_albedo", "IK_D4_ClawMachine_albedo", "IK_D4_DigitalTotem_albedo", "IK_D4_Gumball_albedo",
            "IK_D4_NeonCart_albedo", "IK_D4_RecycleBins_albedo", "IK_D4_SwingSet_albedo",
        };
        static readonly Dictionary<string, Texture2D> masks = new Dictionary<string, Texture2D>();

        /// <summary>0 = leave alone, 1 = all navy, 2 = all gold, 3 = baked mask, 4 = colour key.</summary>
        public static int Classify(Material m, out Texture2D mask)
        {
            mask = null;
            if (!m || !m.shader) return 0;
            var shader = m.shader.name;
            bool standard = shader == "Standard", faded = shader == "MarketDay/Faded";
            if (!standard && !faded && shader != "MarketDay/Soft Painted" && shader != "MarketDay/City Park Triplanar") return 0;
            if (standard && (m.renderQueue >= 2450 || (m.HasProperty("_Mode") && m.GetFloat("_Mode") > .5f))) return 0;
            foreach (var n in NotPaint) if (m.name.IndexOf(n, System.StringComparison.OrdinalIgnoreCase) >= 0) return 0;
            var tex = m.HasProperty("_MainTex") ? m.mainTexture : null;
            if (!tex)
            {
                if (!m.HasProperty("_Color")) return 0;
                var w = Key(m.color.linear);
                return w.x > .5f ? 1 : w.y > .5f ? 2 : 0;
            }
            var name = tex.name;
            foreach (var n in NotPaint) if (name.IndexOf(n, System.StringComparison.OrdinalIgnoreCase) >= 0) return 0;
            if (name.StartsWith("Era") && name.EndsWith("_BaseColor"))
            {
                var key = name.Substring(0, name.Length - "_BaseColor".Length);
                if (!masks.TryGetValue(key, out mask)) masks[key] = mask = Resources.Load<Texture2D>("CheckoutPaint/" + key + "_PaintMask");
                return mask ? 3 : 0;
            }
            if (WholeNavy.Contains(name)) return 1;
            if (WholeGold.Contains(name)) return 2;
            return Keyed.Contains(name) ? 4 : 0;
        }

        // ------------------------------------------------------------------ colour maths (same as MarketPaint.cginc)
        public static Vector4 Oklab(string hex)
        {
            ColorUtility.TryParseHtmlString("#" + hex, out var c);
            var lab = ToOklab(c.linear);
            return new Vector4(lab.x, lab.y, lab.z, 1);
        }
        public static Vector3 ToOklab(Color lin)
        {
            float l = .4122214708f * lin.r + .5363325363f * lin.g + .0514459929f * lin.b;
            float m = .2119034982f * lin.r + .6806995451f * lin.g + .1073969566f * lin.b;
            float s = .0883024619f * lin.r + .2817188376f * lin.g + .6299787005f * lin.b;
            l = Mathf.Pow(Mathf.Max(l, 1e-7f), 1 / 3f); m = Mathf.Pow(Mathf.Max(m, 1e-7f), 1 / 3f); s = Mathf.Pow(Mathf.Max(s, 1e-7f), 1 / 3f);
            return new Vector3(.2104542553f * l + .7936177850f * m - .0040720468f * s,
                               1.9779984951f * l - 2.4285922050f * m + .4505937099f * s,
                               .0259040371f * l + .7827717662f * m - .8086757660f * s);
        }
        static float Smooth(float a, float b, float x) { float t = Mathf.Clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
        /// <summary>How navy (x) and how gold (y) a linear colour is.</summary>
        public static Vector2 Key(Color lin)
        {
            var lab = ToOklab(lin);
            float c = new Vector2(lab.y, lab.z).magnitude;
            var hue = new Vector2(lab.y, lab.z) / Mathf.Max(c, 1e-5f);
            float toNavy = Vector2.Dot(hue, new Vector2(-.06427f, -.99793f)), toGold = Vector2.Dot(hue, new Vector2(.10051f, .99494f));
            float navy = Smooth(.9397f, .9781f, toNavy) * Smooth(.025f, .045f, c) * Smooth(.08f, .12f, lab.x) * (1 - Smooth(.50f, .56f, lab.x));
            float gold = Smooth(.9903f, .9969f, toGold) * Smooth(.100f, .118f, c) * Smooth(.64f, .68f, lab.x) * (1 - Smooth(.90f, .95f, lab.x));
            return new Vector2(navy, gold);
        }
    }
}
