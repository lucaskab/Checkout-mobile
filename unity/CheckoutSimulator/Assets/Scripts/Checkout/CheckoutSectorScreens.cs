using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // The special sectors' screens and name boards ("Evoluções dos móveis", docs-drafts/evolucoes-moveis.md 5.9). The
    // models carry no words: blank quads (slots E_PriceScreen, E_TicketScreen, E_NamePanel, found by the tier builder,
    // CheckoutFixtureTierBuilder.SlotQuads) and the game writes on them:
    //  - price boards: one row per product on the sector's counter, its pictogram and the price customers pay there
    //    (snapshot sectors[].board, the T3 premium included), numbers written the player's way;
    //  - the ticket display: "now serving", one more for every customer who buys at the sector;
    //  - the name board: the sector's name in the player's language.
    // iPhone: one TextMeshPro per screen; the pictograms and the coin come from one shared sprite atlas (drawn once
    // into a render texture), so a panel is two draw calls. Texts change only when a price, the language or the
    // ticket changes, and a sector off screen waits until it is seen.
    public class CheckoutSectorScreens : MonoBehaviour
    {
        [Serializable] public struct Quad { public Vector3 center; public Vector2 size; }
        public Quad[] prices = new Quad[0], tickets = new Quad[0], names = new Quad[0];

        string sectorId, nameText = "", boardKey = "", shownKey = "";
        Sector.BoardRow[] board = new Sector.BoardRow[0];
        readonly List<TextMeshPro> priceTexts = new List<TextMeshPro>(), ticketTexts = new List<TextMeshPro>(), nameTexts = new List<TextMeshPro>();
        Renderer body; bool built;

        // Customers who bought at each sector (the ticket numbers); new ids only.
        static readonly Dictionary<string, int> tickets0 = new Dictionary<string, int>();
        static readonly HashSet<string> counted = new HashSet<string>();
        public static int Ticket(string sectorId) => tickets0.TryGetValue(sectorId ?? "", out var n) ? n : 0;

        /// <summary>Every snapshot: count the new customers who buy at a sector counter ("sector-&lt;id&gt;…" slots).</summary>
        public static void Feed(Snapshot s)
        {
            if (s?.customers == null) return;
            foreach (var c in s.customers)
            {
                if (c == null || string.IsNullOrEmpty(c.id) || c.purchases == null || counted.Contains(c.id)) continue;
                bool any = false;
                foreach (var p in c.purchases)
                {
                    var sector = SectorOf(p?.shelfId);
                    if (sector == null) continue;
                    any = true; tickets0.TryGetValue(sector, out var n); tickets0[sector] = n + 1; break;
                }
                if (any || c.purchases.Length > 0) counted.Add(c.id);
            }
            if (counted.Count > 4000) counted.Clear();
        }

        static string SectorOf(string shelfId)
        {
            if (string.IsNullOrEmpty(shelfId) || !shelfId.StartsWith("sector-")) return null;
            var rest = shelfId.Substring(7); int cut = rest.IndexOfAny(new[] { ':', '-', '#' });
            return cut > 0 ? rest.Substring(0, cut) : rest;
        }

        /// <summary>What this sector shows (CheckoutInterior, every snapshot).</summary>
        public void Show(Sector sector)
        {
            if (sector == null) return;
            sectorId = sector.id; nameText = sector.name ?? "";
            board = sector.board ?? new Sector.BoardRow[0];
            var key = new System.Text.StringBuilder(nameText);
            foreach (var row in board) key.Append('|').Append(row.productId).Append(':').Append(row.price);
            boardKey = key.ToString();
        }

        void OnEnable() { CheckoutI18n.Changed += Invalidate; }
        void OnDisable() { CheckoutI18n.Changed -= Invalidate; }
        void Invalidate() => shownKey = "";

        /// <summary>Write now, seen or not (autotest close-ups from their own camera).</summary>
        public void RefreshNow() { shownKey = "~"; Refresh(true); }

        void LateUpdate() => Refresh(false);

        void Refresh(bool force)
        {
            if (string.IsNullOrEmpty(sectorId)) return;
            if (!body) body = GetComponentInChildren<MeshRenderer>();
            if (!force && body && !body.isVisible) return; // off screen: written when it is seen again
            string key = boardKey + "#" + Ticket(sectorId) + "#" + CheckoutI18n.Language;
            if (key == shownKey) return;
            shownKey = key;
            if (!built) Build();
            Write();
        }

        void Build()
        {
            built = true;
            foreach (var q in prices) priceTexts.Add(Text(q, "Price", K.Number, TextAlignmentOptions.Left, new Color(.96f, .97f, .93f)));
            foreach (var q in tickets) ticketTexts.Add(Text(q, "Ticket", K.Number, TextAlignmentOptions.Center, new Color(1f, .42f, .3f)));
            foreach (var q in names) nameTexts.Add(Text(q, "Name", K.Headline, TextAlignmentOptions.Center, new Color(.11f, .17f, .31f)));
        }

        TextMeshPro Text(Quad q, string name, TMP_FontAsset font, TextAlignmentOptions align, Color color)
        {
            var go = new GameObject(name + " text"); go.transform.SetParent(transform, false);
            // a hair in front of the quad (its customer side, -Z), inside a small margin
            go.transform.localPosition = q.center + new Vector3(0, 0, -.006f);
            var t = go.AddComponent<TextMeshPro>();
            t.font = font; t.color = color; t.alignment = align; t.textWrappingMode = TextWrappingModes.NoWrap;
            t.enableAutoSizing = true; t.fontSizeMin = .05f; t.fontSizeMax = 8; t.overflowMode = TextOverflowModes.Truncate;
            t.rectTransform.sizeDelta = new Vector2(q.size.x * .9f, q.size.y * .84f);
            t.spriteAsset = CheckoutSectorIcons.Asset;
            var r = t.GetComponent<MeshRenderer>(); r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off; r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            return t;
        }

        void Write()
        {
            foreach (var t in nameTexts) if (t) t.text = CheckoutI18n.T(nameText).ToUpperInvariant();
            string ticket = (Ticket(sectorId) % 1000).ToString("000");
            foreach (var t in ticketTexts) if (t) t.text = ticket;
            // The products, spread over the panels left to right (up to three rows each).
            int panels = priceTexts.Count; if (panels == 0) return;
            int perPanel = Mathf.Clamp(Mathf.CeilToInt(board.Length / (float)panels), 1, 3);
            for (int p = 0; p < panels; p++)
            {
                var sb = new System.Text.StringBuilder();
                for (int i = p * perPanel; i < Mathf.Min(board.Length, (p + 1) * perPanel); i++)
                {
                    if (sb.Length > 0) sb.Append('\n');
                    var icon = CheckoutSectorIcons.Tag(board[i].productId);
                    sb.Append(icon).Append(icon.Length > 0 ? " " : "").Append(CheckoutSectorIcons.CoinTag).Append(' ').Append(CheckoutI18n.Number(board[i].price));
                }
                if (priceTexts[p]) priceTexts[p].text = sb.ToString();
            }
        }
    }

    // One sprite atlas for the sector screens: the coin and the pictogram of every product shown, drawn on demand into
    // a render texture (the product pictures are not readable on the CPU), as a TextMeshPro sprite asset.
    public static class CheckoutSectorIcons
    {
        const int Size = 1024, Cell = 64, PerRow = Size / Cell;
        static TMP_SpriteAsset asset; static RenderTexture atlas; static bool tried;
        static readonly Dictionary<int, string> tags = new Dictionary<int, string>();
        static int next;
        public const string CoinTag = "<sprite name=\"c\">";
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)] static void Reset() { asset = null; atlas = null; tried = false; tags.Clear(); next = 0; }

        public static TMP_SpriteAsset Asset
        {
            get
            {
                if (asset || tried) return asset;
                tried = true;
                var mat = Resources.Load<Material>("CheckoutDesktop/CoinTextSprite");
                if (!mat) return null;
                atlas = new RenderTexture(Size, Size, 0, RenderTextureFormat.ARGB32) { name = "Sector icons", useMipMap = true, autoGenerateMips = false, filterMode = FilterMode.Trilinear };
                atlas.Create();
                var prev = RenderTexture.active; RenderTexture.active = atlas; GL.Clear(true, true, new Color(0, 0, 0, 0)); RenderTexture.active = prev;
                var a = ScriptableObject.CreateInstance<TMP_SpriteAsset>();
                a.name = "Sector icons"; a.spriteSheet = atlas; a.material = new Material(mat) { mainTexture = atlas };
                var version = typeof(TMP_SpriteAsset).GetField("m_Version", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                if (version != null) version.SetValue(a, "1.1.0");
                var faceField = typeof(TMP_SpriteAsset).GetField("m_FaceInfo", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                if (faceField != null) faceField.SetValue(a, new UnityEngine.TextCore.FaceInfo { pointSize = Cell, scale = 1f, ascentLine = Cell * .8f, lineHeight = Cell, baseline = 0, descentLine = -Cell * .2f });
                asset = a;
                Add("c", Resources.Load<Texture2D>("CheckoutDesktop/Icons/coin"), .8f);
                return asset;
            }
        }

        /// <summary>The sprite tag of a product's pictogram ("" when it has none).</summary>
        public static string Tag(int productId)
        {
            if (tags.TryGetValue(productId, out var tag)) return tag;
            var sprite = CheckoutFixtureArt.Product(productId);
            tag = sprite && Asset && Add("p" + productId, sprite.texture, 1.15f, sprite.textureRect) ? "<sprite name=\"p" + productId + "\">" : "";
            tags[productId] = tag;
            return tag;
        }

        static bool Add(string name, Texture2D tex, float scale, Rect? source = null)
        {
            if (!tex || !asset || next >= PerRow * PerRow) return false;
            int k = next++; int x = k % PerRow * Cell, y = k / PerRow * Cell;
            var src = source ?? new Rect(0, 0, tex.width, tex.height);
            // fit the picture in its cell, keeping its shape
            float aspect = src.width / Mathf.Max(1, src.height); float w = Cell - 4, h = Cell - 4;
            if (aspect > 1) h = w / aspect; else w = h * aspect;
            // (drawn in GUI space, top-left origin, as Graphics.DrawTexture expects; the glyph rects count from the bottom)
            var dest = new Rect(x + (Cell - w) * .5f, Size - y - Cell + (Cell - h) * .5f, w, h);
            var prev = RenderTexture.active; RenderTexture.active = atlas;
            GL.PushMatrix(); GL.LoadPixelMatrix(0, Size, Size, 0);
            Graphics.DrawTexture(dest, tex, new Rect(src.x / tex.width, src.y / tex.height, src.width / tex.width, src.height / tex.height), 0, 0, 0, 0);
            GL.PopMatrix(); RenderTexture.active = prev;
            atlas.GenerateMips();
            var glyph = new TMP_SpriteGlyph((uint)asset.spriteGlyphTable.Count, new UnityEngine.TextCore.GlyphMetrics(Cell, Cell, 0, Cell * .78f, Cell * 1.04f), new UnityEngine.TextCore.GlyphRect(x, y, Cell, Cell), scale, 0);
            asset.spriteGlyphTable.Add(glyph);
            asset.spriteCharacterTable.Add(new TMP_SpriteCharacter(0xE000 + (uint)asset.spriteCharacterTable.Count, glyph) { name = name, scale = 1f });
            asset.UpdateLookupTables();
            return true;
        }
    }
}
