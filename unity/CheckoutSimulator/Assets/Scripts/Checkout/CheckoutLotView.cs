using System.Collections.Generic;
using TMPro;
using UnityEngine;
using MarketDay;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // "Ver lotes": the block seen from above, split in its lots (src/data/market-lots.ts). Lots the
    // market already has are gold, the ones the next era takes are green, the free square is purple.
    // Opened from the Loja ("Evolução" → "Ver lotes", route "@lots"); "Voltar" puts the camera back.
    public class CheckoutLotView : MonoBehaviour
    {
        public static bool Open { get; private set; }
        static CheckoutLotView instance;
        CheckoutBridge bridge; MarketSimulation simulation;
        GameObject overlay; RectTransform ui; Material material;
        (Vector3 focus, float zoom) cameraBefore;
        const float Height = .22f;

        static readonly Color Owned = new Color(1f, .6f, .05f, .62f), Next = new Color(.2f, .8f, .4f, .55f),
            Plaza = new Color(.62f, .42f, .9f, .42f), Free = new Color(1, 1, 1, .16f), Edge = new Color(1, 1, 1, .9f),
            Clearing = new Color(.95f, .35f, .2f, .5f), Blocked = new Color(.1f, .12f, .2f, .35f);

        public void Initialize(CheckoutBridge owner)
        {
            bridge = owner; simulation = FindAnyObjectByType<MarketSimulation>(); instance = this;
        }

        // The lot view was replaced by the lots themselves (a padlock on each locked lot, a panel on click:
        // CheckoutLotSites, CheckoutLotPopup). The old route "@lots" now does nothing.
        public static void Show() { }

        void Enter()
        {
            var era = bridge.State?.era;
            if (Open || era?.grid == null || era.grid.columns <= 0 || CheckoutBuildMode.Open) return;
            Open = true;
            cameraBefore = simulation.CameraState;
            simulation.Focus(new Vector3(era.grid.x0 + era.grid.width * .5f, 0, era.grid.z0 + era.grid.depth * .42f), 38);
            BuildOverlay(era);
            BuildUi(era);
        }

        void Exit()
        {
            if (!Open) return;
            Open = false;
            if (overlay) Destroy(overlay);
            if (ui) Destroy(ui.gameObject);
            simulation.Focus(cameraBefore.focus, cameraBefore.zoom);
        }

        string shownEra;
        // Redraw when the expansion or any lot's status changes (bought, cleared…).
        static string Signature(EraState era)
        {
            var sb = new System.Text.StringBuilder(era.id);
            if (era.lotRects != null) foreach (var l in era.lotRects) sb.Append('|').Append(l.id).Append(l.status);
            return sb.ToString();
        }
        void Update()
        {
            if (!Open) return;
            if (Input.GetKeyDown(KeyCode.Escape)) { Exit(); return; }
            // The era changed while the lots are shown (evolution finished, DEV jump): redraw them.
            var era = bridge.State?.era;
            if (era != null && Signature(era) != shownEra && era.grid != null)
            {
                if (overlay) Destroy(overlay);
                if (ui) Destroy(ui.gameObject);
                BuildOverlay(era); BuildUi(era);
            }
        }

        // ------------------------------------------------------------------ 3D
        void BuildOverlay(EraState era)
        {
            if (!material)
            {
                material = new Material(Shader.Find("Sprites/Default")) { name = "Lot overlay" };
                material.renderQueue = 3100;
            }
            overlay = new GameObject("Lot view");
            shownEra = Signature(era);
            var g = era.grid;
            float w = g.width / g.columns, d = g.depth / g.rows;
            var owned = new HashSet<string>(era.lots ?? new string[0]);
            var next = new HashSet<string>(era.nextLots ?? new string[0]);
            var plaza = new HashSet<string>(era.plazaLots ?? new string[0]);
            if (era.lotRects != null && era.lotRects.Length > 0)
            {
                // Lots of different sizes following the market building (the depot is one big lot).
                foreach (var lot in era.lotRects)
                {
                    // Land status (src/services/market-lots.ts): yours, for sale, bought (to clear), clearing.
                    string st = lot.status ?? "";
                    var colour = st == "seu" || owned.Contains(lot.id) ? Owned : st == "praca" || plaza.Contains(lot.id) ? Plaza
                        : st == "comprado" || st == "limpando" ? Clearing : next.Contains(lot.id) ? Next : st == "bloqueado" ? Blocked : Free;
                    float lw = lot.x1 - lot.x0, ld = lot.z1 - lot.z0;
                    Quad(lot.id, new Vector3(lot.x0 + .12f, Height, lot.z0 + .12f), new Vector3(lot.x1 - .12f, Height, lot.z1 - .12f), colour);
                    Frame(lot.id, lot.x0, lot.z0, lw, ld);
                    string price = lot.price.ToString("N0", System.Globalization.CultureInfo.GetCultureInfo("pt-BR"));
                    string tag = st == "seu" ? "SEU" : st == "praca" ? "GRATUITA" : st == "comprado" ? "COMPRADO · LIMPAR"
                        : st == "limpando" ? "LIMPANDO" : st == "venda" ? "À VENDA · " + price : st == "bloqueado" ? price
                        : owned.Contains(lot.id) ? "SEU" : next.Contains(lot.id) ? "PRÓXIMA" : plaza.Contains(lot.id) ? "GRATUITA" : "";
                    float size = Mathf.Clamp(Mathf.Min(lw, ld) * .55f, 1.6f, 4.2f);
                    Label(lot.label, tag, new Vector3((lot.x0 + lot.x1) * .5f, Height + .05f, (lot.z0 + lot.z1) * .5f), size);
                }
            }
            else
            for (int c = 0; c < g.columns; c++)
                for (int r = 0; r < g.rows; r++)
                {
                    string id = (char)('A' + c) + (r + 1).ToString();
                    var colour = owned.Contains(id) ? Owned : next.Contains(id) ? Next : plaza.Contains(id) ? Plaza : Free;
                    float x0 = g.x0 + c * w, z0 = g.z0 + r * d;
                    Quad(id, new Vector3(x0 + .12f, Height, z0 + .12f), new Vector3(x0 + w - .12f, Height, z0 + d - .12f), colour);
                    Frame(id, x0, z0, w, d);
                    string tag = owned.Contains(id) ? "SEU" : next.Contains(id) ? "PRÓXIMA" : plaza.Contains(id) ? "PRAÇA" : "";
                    Label(id, tag, new Vector3(x0 + w * .5f, Height + .05f, z0 + d * .5f));
                }
            // The first expansions stand on the sidewalk in front of the first lot.
            if (owned.Count == 0)
            {
                float cx = g.x0 + g.width * .5f;
                Quad("Sidewalk spot", new Vector3(cx - 2.5f, Height, g.z0 - 3.6f), new Vector3(cx + 2.5f, Height, g.z0 - .3f), Owned);
                Label("Calçada", "SEU", new Vector3(cx, Height + .05f, g.z0 - 1.9f), 2.2f);
            }
        }

        void Quad(string name, Vector3 a, Vector3 b, Color colour)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(overlay.transform, false);
            var mesh = new Mesh { name = name };
            mesh.vertices = new[] { new Vector3(a.x, a.y, a.z), new Vector3(a.x, a.y, b.z), new Vector3(b.x, a.y, b.z), new Vector3(b.x, a.y, a.z) };
            mesh.colors = new[] { colour, colour, colour, colour };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateBounds();
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
        }

        void Frame(string id, float x0, float z0, float w, float d)
        {
            const float t = .12f;
            float y = Height + .01f;
            Quad(id + " edge S", new Vector3(x0, y, z0), new Vector3(x0 + w, y, z0 + t), Edge);
            Quad(id + " edge N", new Vector3(x0, y, z0 + d - t), new Vector3(x0 + w, y, z0 + d), Edge);
            Quad(id + " edge W", new Vector3(x0, y, z0), new Vector3(x0 + t, y, z0 + d), Edge);
            Quad(id + " edge E", new Vector3(x0 + w - t, y, z0), new Vector3(x0 + w, y, z0 + d), Edge);
        }

        void Label(string id, string tag, Vector3 at, float size = 4.2f)
        {
            var go = new GameObject("Lot " + id);
            go.transform.SetParent(overlay.transform, false);
            go.transform.position = at;
            // Flat on the ground, turned to read from where the camera looks.
            go.transform.rotation = Quaternion.Euler(90, simulation.view ? simulation.view.transform.eulerAngles.y : 0, 0);
            var text = go.AddComponent<TextMeshPro>();
            text.font = K.Headline;
            text.text = string.IsNullOrEmpty(tag) ? id : id + "\n<size=45%>" + tag + "</size>";
            text.fontSize = size * 4;
            text.alignment = TextAlignmentOptions.Center;
            text.color = Color.white;
            text.outlineColor = new Color32(24, 33, 59, 255);
            text.outlineWidth = .25f;
            text.rectTransform.sizeDelta = new Vector2(9, 6);
            text.textWrappingMode = TextWrappingModes.NoWrap;
            text.fontMaterial.renderQueue = 3200;
        }

        // ------------------------------------------------------------------ HUD
        void BuildUi(EraState era)
        {
            ui = U.Canvas(transform, "CheckoutLotView", 70);
            var bar = U.Shape(ui, "Bar", "1D2B4F", 22, new Vector2(.5f, 1), new Vector2(980, 120), new Vector2(0, -80));
            var title = U.Label(bar.transform, "Title", K.Headline, 30, "FFFFFF", TextAlignmentOptions.Left);
            U.Stretch(title.rectTransform, new Vector2(0, .5f), Vector2.one).offsetMin = new Vector2(28, 0);
            title.text = "Lotes do quarteirão · " + era.name;
            var legend = U.Label(bar.transform, "Legend", K.Body, 18, "E8DFC8", TextAlignmentOptions.Left);
            var lr = U.Stretch(legend.rectTransform, Vector2.zero, new Vector2(1, .5f)); lr.offsetMin = new Vector2(28, 10); lr.offsetMax = new Vector2(-380, 0);
            legend.text = "<color=#F9BD2E>■</color> seus   <color=#F26A3A>■</color> comprados (limpar)   <color=#4DD973>■</color> " + era.nextName + " precisa   <color=#FFFFFF>■</color> à venda   <color=#A06BE6>■</color> praça";
            var back = U.Button(bar.transform, "Voltar", "primary", Exit, 64, 22);
            U.At((RectTransform)back.transform, new Vector2(1, .5f), new Vector2(170, 64), new Vector2(-105, 0));
            // Straight to the land shop (Loja → Terrenos).
            var buy = U.Button(bar.transform, "Terrenos", "secondary", () => { Exit(); var host = FindAnyObjectByType<CheckoutDesktopHost>(); if (host) host.Route("~loja:terrenos"); }, 64, 22);
            U.At((RectTransform)buy.transform, new Vector2(1, .5f), new Vector2(170, 64), new Vector2(-285, 0));
        }
    }
}
