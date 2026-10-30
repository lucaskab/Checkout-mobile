using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    // "Evoluções dos móveis" (docs-drafts/evolucoes-moveis.md): the furniture evolves in tiers, each a model of its own
    // (Resources/CheckoutFixtureTiers/<kind>_T<n>, built by CheckoutMarketStagesBuilder.BuildFixtureTiers) with a bigger
    // footprint. The app says which tier each piece wants (snapshot shelves[].tierTemplate, fixtureTiers, interior.tiers).
    //
    // Space rule (saves and evolutions): a piece never moves by itself and never goes back to the inventory. It shows
    // the biggest of its tiers that fits where it stands; when the wanted one does not fit it is flagged ("pronto
    // para crescer") and grows as soon as it fits — after the player moves it in build mode, or when the space
    // around it frees up.
    public partial class CheckoutInterior
    {
        const string TierFolder = "CheckoutFixtureTiers/";
        static readonly Dictionary<string, GameObject> tierPrefabs = new Dictionary<string, GameObject>();
        // Decoration id → its tier models (ATM, gumball, claw machine) and the three cart stations.
        readonly Dictionary<string, string> decorTemplates = new Dictionary<string, string>();
        static readonly Dictionary<string, string> StationTemplates = new Dictionary<string, string>
        {
            { "basket-station", "carts_T1" }, { "cart-corral", "carts_T2" }, { "big-cart-corral", "carts_T3" },
            { "atm", "atm_T1" }, { "gumball", "gumball_T1" }, { "claw-machine", "claw_T1" },
        };

        /// <summary>Kit template or tier prefab with this name (null when neither exists).</summary>
        public GameObject TemplateObject(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            var t = kit ? kit.Find(name) : null;
            if (t) return t.gameObject;
            if (!tierPrefabs.TryGetValue(name, out var prefab)) tierPrefabs[name] = prefab = Resources.Load<GameObject>(TierFolder + name);
            return prefab;
        }

        static bool IsTierTemplate(string name) => !string.IsNullOrEmpty(name) && name.Length > 3 && name[name.Length - 3] == '_' && name[name.Length - 2] == 'T' && char.IsDigit(name[name.Length - 1]);

        /// <summary>The model a decoration shows: its tier (ATM, machines), the station of the carts, or the kit's own.</summary>
        public string DecorTemplate(string type)
        {
            if (string.IsNullOrEmpty(type)) return type;
            if (decorTemplates.TryGetValue(type, out var t) && TemplateObject(t)) return t;
            if (StationTemplates.TryGetValue(type, out t) && TemplateObject(t)) return t;
            return type;
        }

        void ReadDecorTiers(Snapshot s)
        {
            decorTemplates.Clear();
            foreach (var d in s.interior?.tiers ?? Array.Empty<DecorTier>())
                if (d != null && !string.IsNullOrEmpty(d.type) && !string.IsNullOrEmpty(d.template)) decorTemplates[d.type] = d.template;
        }

        /// <summary>A shelf's model: its tier when the app sends one and the model exists, else the kit's.</summary>
        string ShelfTierTemplate(Shelf shelf, string kitTemplate) =>
            shelf != null && shelf.tier > 0 && TemplateObject(shelf.tierTemplate) ? shelf.tierTemplate : kitTemplate;

        string CheckoutTierTemplate(Snapshot s)
        {
            var t = s.fixtureTiers?.checkoutTemplate;
            return CheckoutStall.Small && !CheckoutStall.PlacedCounter ? "checkout" : TemplateObject(t) ? t : "checkout";
        }

        /// <summary>The wanted tier and every smaller one of the same kind, biggest first.</summary>
        string[] TierSteps(string desired)
        {
            if (!IsTierTemplate(desired)) return new[] { desired };
            string kind = desired.Substring(0, desired.Length - 3);
            int n = desired[desired.Length - 1] - '0';
            var list = new List<string>();
            for (int k = n; k >= 1; k--) { var name = kind + "_T" + k; if (TemplateObject(name)) list.Add(name); }
            return list.Count > 0 ? list.ToArray() : new[] { desired };
        }

        CheckoutInteriorPiece PieceOf(string template)
        {
            var go = TemplateObject(template);
            return go ? go.GetComponent<CheckoutInteriorPiece>() : null;
        }

        /// <summary>Would `it` fit at its spot with the model `template`? (Measured with that model's footprint.)</summary>
        public bool FitsAs(Item it, string template)
        {
            var piece = PieceOf(template);
            if (!piece || !it.root) return false;
            var saved = it.piece; it.piece = piece;
            bool ok = Fits(it, it.root.position, it.rot, out _);
            it.piece = saved;
            return ok;
        }

        /// <summary>Would `it` fit here with the footprint of `template`? (The shelf panel asks before "Evoluir".)</summary>
        public bool FitsTier(string id, string template)
        {
            var it = Get(id);
            if (it == null) return true; // not standing in the shop (stored, a stall): nothing to check
            if (!TemplateObject(template)) return true;
            return FitsAs(it, template);
        }

        void SwapTemplate(Item it, string template)
        {
            if (it.template == template && it.root) return;
            if (it.root) Destroy(it.root.gameObject);
            it.template = template; Build(it);
            if (!it.root) return;
            Place(it); Dress(it);
        }

        /// <summary>Each tiered piece shows the biggest of its tiers that fits where it stands (never moved).</summary>
        bool FitTiers()
        {
            bool changed = false;
            foreach (var it in items.Values.Where(i => i.root && !i.ghost && !i.design && IsTierTemplate(i.desired)).OrderBy(i => i.id).ToList())
            {
                var steps = TierSteps(it.desired);
                if (steps.Length < 2) { it.wantsGrow = false; continue; }
                int at = Array.IndexOf(steps, it.template); if (at < 0) at = 0;
                // Grow back towards the wanted tier when it fits now.
                for (int k = 0; k < at; k++) if (FitsAs(it, steps[k])) { SwapTemplate(it, steps[k]); at = k; changed = true; break; }
                // Too big for its spot (a save's first load, an evolution bought): the biggest one that fits.
                if (!Fits(it, it.root.position, it.rot, out _))
                    for (int k = at + 1; k < steps.Length; k++) if (FitsAs(it, steps[k])) { SwapTemplate(it, steps[k]); changed = true; break; }
                it.wantsGrow = it.template != it.desired;
            }
            return changed;
        }

        /// <summary>Build mode: a piece the player just moved takes the size it wants if it fits there.</summary>
        public bool TryGrow(Item it)
        {
            if (it == null || !it.root || !IsTierTemplate(it.desired) || it.template == it.desired) return false;
            foreach (var step in TierSteps(it.desired))
            {
                if (step == it.template) break;
                if (FitsAs(it, step)) { SwapTemplate(it, step); it.wantsGrow = it.template != it.desired; return true; }
            }
            return false;
        }

        // ------------------------------------------------------------------ the premium finish (★)
        // The T4 model with a warm LED skirting along the customer side and a gold line above it: the gold follows
        // "Cores do mercado" (its flat gold colour is the market's accent), the light never does.
        static Material premiumLed, premiumGold;
        void Dress(Item it)
        {
            if (!it.root || it.piece == null) return;
            var old = it.root.Find("Premium finish");
            if (!it.premium || it.template != it.desired) { if (old) Destroy(old.gameObject); return; }
            if (old) return;
            if (!premiumLed)
            {
                premiumLed = new Material(Shader.Find("Standard")) { name = "FT_Premium_Led", color = new Color(1f, .86f, .55f) };
                premiumLed.EnableKeyword("_EMISSION"); premiumLed.SetColor("_EmissionColor", new Color(1f, .78f, .42f) * 1.6f);
                var shader = Shader.Find("MarketDay/Soft Painted");
                premiumGold = new Material(shader ? shader : Shader.Find("Standard")) { name = "FT_Premium_C_D3A53D", color = MarketSimulation.C("D3A53D") };
            }
            var p = it.piece; float w = p.max.x - p.min.x - .08f, cx = (p.min.x + p.max.x) * .5f;
            var finish = new GameObject("Premium finish").transform; finish.SetParent(it.root, false);
            void Strip(string name, Material m, float y, float h, float z)
            {
                var q = GameObject.CreatePrimitive(PrimitiveType.Cube); q.name = name; Destroy(q.GetComponent<Collider>());
                q.transform.SetParent(finish, false); q.transform.localPosition = new Vector3(cx, y, z); q.transform.localScale = new Vector3(w, h, .025f);
                var r = q.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            Strip("Led skirting", premiumLed, .05f, .035f, p.min.y + .02f);
            Strip("Gold line", premiumGold, .095f, .018f, p.min.y + .02f);
            if (p.max.y - p.min.y >= .95f) { Strip("Led skirting back", premiumLed, .05f, .035f, p.max.y - .02f); Strip("Gold line back", premiumGold, .095f, .018f, p.max.y - .02f); }
            CheckoutMarketPaint.Touch(finish.gameObject);
        }
    }
}
