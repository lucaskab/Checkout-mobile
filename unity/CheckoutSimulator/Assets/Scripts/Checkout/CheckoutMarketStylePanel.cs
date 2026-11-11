using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout
{
    // "Estilo do mercado" picker (Lucas 08/11). Same shape as "Cores do mercado" (CheckoutMarketPaintPanel): a panel on the
    // right, the live market on the left wearing every choice the moment it is tapped (CheckoutMarketStyle.Preview).
    // Four tabs: Piso, Parede, Uniforme, Letreiro. Each item is a card (texture, colours or the font itself) with its price,
    // "Seu" once bought or "Grátis"; tintable items open a colour grid; the sign also picks its look, effect, two colours,
    // the palette of "Letras coloridas" and the effect's speed. The footer charges every new item of the draft at once
    // (coins or diamonds); owned items and colours are free. Rules and prices: src/data/market-style.ts (applyMarketStyle).
    // Opened from Loja › Decoração ("@style").
    public class CheckoutMarketStylePanel : MonoBehaviour
    {
        public static bool Open => instance && instance.root && instance.root.gameObject.activeSelf;
        static CheckoutMarketStylePanel instance;
        static StyleChoice kept; static int keptTab;

        static bool Phone => CheckoutScreen.Handheld;
        static float Tap => Phone ? 72 : 54;

        RectTransform root, panel, content, toastRect;
        TextMeshProUGUI toastText, nowLabel;
        Image toastFace;
        CheckoutDesktopButton applyCoins, applyGems, cancel, classic;
        readonly CheckoutDesktopButton[] tabs = new CheckoutDesktopButton[4];
        readonly List<Canvas> hidden = new List<Canvas>();
        // the cards and swatches of the tab shown, for the selection marks
        readonly List<(Image ring, string kind, string id)> cards = new List<(Image, string, string)>();
        readonly List<(Image ring, string hex)> swatches = new List<(Image, string)>();
        readonly List<(Image ring, string id)> paletteChips = new List<(Image, string)>();
        readonly List<(CheckoutDesktopButton button, int value)> speedButtons = new List<(CheckoutDesktopButton, int)>();
        CheckoutDesktopButton slotA, slotB; Image slotADot, slotBDot;

        StyleChoice draft = new StyleChoice();
        int tab, slot; bool busy; float toastUntil; string builtKey = "";
        (Vector3 focus, float zoom) cameraBefore; bool cameraSaved; Camera cameraShifted; float shift;

        void LateUpdate()
        {
            if (!cameraShifted || shift <= 0) return;
            cameraShifted.ResetProjectionMatrix();
            cameraShifted.projectionMatrix = Matrix4x4.Translate(new Vector3(-shift, 0, 0)) * cameraShifted.projectionMatrix;
        }

        // ------------------------------------------------------------------ open / close
        public static void Show()
        {
            var style = CheckoutMarketStyle.Active; var host = CheckoutDesktopHost.Active;
            if (!style || !host || CheckoutBuildMode.Open) return;
            if (!instance) instance = new GameObject("CheckoutMarketStylePanel").AddComponent<CheckoutMarketStylePanel>();
            instance.Enter();
        }
        public static void Hide() { if (Open) instance.Leave(false); }

        void Enter()
        {
            if (!root) Build();
            var style = CheckoutMarketStyle.Active;
            draft = (kept ?? style.Saved).Clone(); tab = kept != null ? keptTab : (State != null && !State.insideUnlocked && State.signUnlocked ? 3 : 0);
            kept = null; slot = 0; busy = false; builtKey = "";
            root.gameObject.SetActive(true);
            GameHud(false);
            FrameMarket(true);
            RebuildTab();
            Preview();
            Refresh();
        }

        void Leave(bool keepDraft)
        {
            if (keepDraft) { kept = draft.Clone(); keptTab = tab; }
            root.gameObject.SetActive(false);
            CheckoutMarketStyle.Active?.EndPreview();
            FrameMarket(false);
            GameHud(true);
        }

        void GameHud(bool show)
        {
            if (!show)
            {
                hidden.Clear();
                var desktop = FindAnyObjectByType<CheckoutDesktopHUD>();
                var own = desktop ? desktop.transform.Find("CheckoutDesktopHUD")?.GetComponent<Canvas>() : null;
                if (own && own.enabled) { own.enabled = false; hidden.Add(own); }
                var stock = FindAnyObjectByType<CheckoutStockroom>();
                var stockCanvas = stock ? stock.transform.Find("CheckoutStockroom")?.GetComponent<Canvas>() : null;
                if (stockCanvas && stockCanvas.enabled) { stockCanvas.enabled = false; hidden.Add(stockCanvas); }
            }
            else { foreach (var c in hidden) if (c) c.enabled = true; hidden.Clear(); }
        }

        void FrameMarket(bool on)
        {
            var cam = Camera.main; var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
            if (on)
            {
                Canvas.ForceUpdateCanvases();
                var screen = (RectTransform)root.parent; float w = screen.rect.width;
                shift = w > 0 ? Mathf.Clamp01((panel.rect.width + 24) / w) : .45f; cameraShifted = cam;
                if (sim) { cameraBefore = sim.CameraState; cameraSaved = true; sim.cameraLocked = true; sim.pinchLocked = true; }
                Aim();
            }
            else
            {
                if (cameraShifted) cameraShifted.ResetProjectionMatrix(); cameraShifted = null; shift = 0;
                if (sim) { sim.cameraLocked = false; sim.pinchLocked = false; if (cameraSaved) sim.Focus(cameraBefore.focus, cameraBefore.zoom); }
                cameraSaved = false;
            }
        }

        // Floor, walls and uniform: inside the shop. The sign: the back wall, where the letters stand.
        void Aim()
        {
            var sim = FindAnyObjectByType<MarketDay.MarketSimulation>(); if (!sim) return;
            var shell = FindAnyObjectByType<CheckoutMarketShell>();
            var fp = CheckoutStall.Small || !shell ? CheckoutStall.Footprint : shell.Footprint;
            float size = Mathf.Max(fp.size.x, fp.size.z);
            if (tab == 3 && SignBounds(out var sign)) { sim.Focus(new Vector3(sign.center.x, 0, sign.center.z - 4f), Mathf.Max(9, sign.size.x * 1.5f)); return; }
            sim.Focus(new Vector3(fp.center.x, 0, fp.center.z), Mathf.Max(7, size * (CheckoutStall.Small ? .9f : .62f)));
        }
        static bool SignBounds(out Bounds bounds)
        {
            bounds = default;
            var dressing = GameObject.Find("Market Stage Dressing"); if (!dressing) return false;
            foreach (var name in new[] { "S4 name", "S2 name", "S1 rear sign", "S0 name board" })
            {
                var t = dressing.transform.Find(name); if (!t || !t.gameObject.activeInHierarchy) continue;
                bool any = false;
                foreach (var r in t.GetComponentsInChildren<Renderer>(false)) { if (!any) { bounds = r.bounds; any = true; } else bounds.Encapsulate(r.bounds); }
                if (any) return true;
            }
            return false;
        }

        // ------------------------------------------------------------------ build
        void Build()
        {
            root = U.Canvas(transform, "CheckoutMarketStyle", 72);
            var block = N.Image(root, "Blocker", new Color(0, 0, 0, 0), 0); U.Stretch(block.rectTransform, Vector2.zero, Vector2.one); block.raycastTarget = true;

            float width = Phone ? 660 : 580, pad = Phone ? 14 : 16;
            var edge = N.Image(root, "Panel", K.Border, 26); panel = edge.rectTransform; edge.raycastTarget = true;
            panel.anchorMin = new Vector2(1, 0); panel.anchorMax = Vector2.one; panel.pivot = new Vector2(1, .5f);
            panel.sizeDelta = new Vector2(width, -(Phone ? 12 : 24)); panel.anchoredPosition = new Vector2(-(Phone ? 6 : 12), 0);
            var face = N.Image(panel, "Face", K.Cream, 24); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 6), new Vector2(-3, -3));

            float headH = Phone ? 64 : 62;
            var head = N.Node("Header", face.transform); U.Stretch(head, new Vector2(0, 1), Vector2.one, new Vector2(pad, -headH), new Vector2(-pad, -6));
            U.Icon(head, "Icon", "Icons/paint", new Vector2(0, .5f), new Vector2(headH - 14, headH - 14), new Vector2((headH - 14) * .5f, 0));
            float headButtons = Phone ? 2 * 138 + 8 : 2 * 128 + 8;
            var title = U.Label(head, "Title", K.Headline, 24, "4A3624", TextAlignmentOptions.Left); title.text = "Estilo do mercado";
            title.enableAutoSizing = true; title.fontSizeMin = 16; title.fontSizeMax = 24;
            U.Stretch(title.rectTransform, Vector2.zero, Vector2.one, new Vector2(headH - 4, 0), new Vector2(-(headButtons + 6), 0));
            var headRow = N.Node("Header buttons", head); headRow.anchorMin = new Vector2(1, 0); headRow.anchorMax = Vector2.one; headRow.pivot = new Vector2(1, .5f);
            headRow.sizeDelta = new Vector2(headButtons, -6); headRow.anchoredPosition = Vector2.zero;
            var hr = N.Row(headRow.gameObject, 8); hr.childForceExpandWidth = true; hr.childControlHeight = true; hr.childForceExpandHeight = true;
            classic = Btn(headRow, "Clássico", "secondary", BackToClassic, headH - 10);
            cancel = Btn(headRow, "Cancelar", "danger", Cancel, headH - 10);

            // Tabs.
            float tabH = Tap - 6;
            var tabRow = N.Node("Tabs", face.transform); U.Stretch(tabRow, new Vector2(0, 1), Vector2.one, new Vector2(pad, -headH - 8 - tabH), new Vector2(-pad, -headH - 8));
            var tr = N.Row(tabRow.gameObject, 6); tr.childForceExpandWidth = true; tr.childControlHeight = true; tr.childForceExpandHeight = true;
            string[] names = { "Piso", "Parede", "Uniforme", "Letreiro" };
            for (int i = 0; i < 4; i++) { int k = i; tabs[i] = Btn(tabRow, names[i], "secondary", () => PickTab(k), tabH); }

            float footH = Tap + 12;
            var foot = N.Node("Footer", face.transform); U.Stretch(foot, Vector2.zero, new Vector2(1, 0), new Vector2(pad, 10), new Vector2(-pad, footH));
            var r1 = N.Row(foot.gameObject, 10); r1.childForceExpandWidth = true; r1.childControlHeight = true; r1.childForceExpandHeight = true;
            applyCoins = Btn(foot, "Aplicar", "coin", () => ApplyWith("coins"), Tap);
            applyGems = Btn(foot, "Aplicar", "gem", () => ApplyWith("diamonds"), Tap);

            float top = headH + 8 + tabH + 6;
            var view = N.Node("Viewport", face.transform); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(pad, footH + 8), new Vector2(-pad, -top));
            view.gameObject.AddComponent<RectMask2D>(); var hit = view.gameObject.AddComponent<Image>(); hit.color = new Color(1, 1, 1, 0);
            content = N.Node("Content", view); content.anchorMin = new Vector2(0, 1); content.anchorMax = Vector2.one; content.pivot = new Vector2(.5f, 1); content.offsetMin = content.offsetMax = Vector2.zero;
            N.Column(content.gameObject, 10, new RectOffset(0, 0, 4, 12));
            content.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = content; scroll.horizontal = false; scroll.vertical = true; scroll.viewport = view; scroll.movementType = ScrollRect.MovementType.Clamped; scroll.scrollSensitivity = 30;

            var toastEdge = N.Image(root, "Toast", K.C("427A24"), 18); toastRect = toastEdge.rectTransform;
            toastRect.anchorMin = toastRect.anchorMax = new Vector2(0, 0); toastRect.pivot = new Vector2(0, 0); toastRect.sizeDelta = new Vector2(Phone ? 560 : 520, Phone ? 64 : 58); toastRect.anchoredPosition = new Vector2(Phone ? 12 : 16, Phone ? 12 : 16);
            toastFace = N.Image(toastRect, "Face", K.C("5DA637"), 16); U.Stretch(toastFace.rectTransform, Vector2.zero, Vector2.one, new Vector2(0, 4), Vector2.zero);
            toastText = U.Label(toastFace.transform, "Text", K.Label, Phone ? 20 : 19, "FFFFFF"); U.Stretch(toastText.rectTransform, Vector2.zero, Vector2.one, new Vector2(14, 0), new Vector2(-14, 0));
            toastText.textWrappingMode = TextWrappingModes.Normal;
            toastRect.gameObject.SetActive(false);
            root.gameObject.SetActive(false);
        }

        CheckoutDesktopButton Btn(Transform parent, string label, string variant, Action onClick, float height)
        {
            var b = CheckoutDesktopButton.Create(parent, height, Phone ? 19 : 18, 14);
            b.Apply(Data(label, variant, true, ""));
            b.Clicked = _ => onClick();
            return b;
        }
        static DesktopButton Data(string label, string variant, bool enabled, string icon, bool active = false) =>
            new DesktopButton { label = label, variant = variant, enabled = enabled, active = active, icon = icon, action = "", args = "[]", route = "", after = "", ok = "", fail = "" };

        TextMeshProUGUI Caption(Transform parent, string text)
        {
            var t = U.Label(parent, "Caption", K.Label, Phone ? 17 : 15, "8A7560", TextAlignmentOptions.Left); t.text = text;
            t.gameObject.AddComponent<LayoutElement>().preferredHeight = Phone ? 26 : 22; return t;
        }

        RectTransform Grid(Transform parent, string name, int columns, float height)
        {
            var g = N.Node(name, parent);
            var gl = g.gameObject.AddComponent<GridLayoutGroup>();
            float w = (panel.rect.width > 0 ? panel.rect.width : (Phone ? 660 : 580)) - (Phone ? 34 : 38);
            float gap = Phone ? 8 : 8;
            gl.cellSize = new Vector2((w - gap * (columns - 1)) / columns, height); gl.spacing = new Vector2(gap, gap);
            gl.constraint = GridLayoutGroup.Constraint.FixedColumnCount; gl.constraintCount = columns; gl.childAlignment = TextAnchor.UpperLeft;
            return g;
        }

        // ------------------------------------------------------------------ data
        StyleState State => CheckoutMarketStyle.Active ? CheckoutMarketStyle.Active.State : null;
        StyleItem Item(string kind, string id) => State?.items?.FirstOrDefault(i => i.kind == kind && i.id == id);
        IEnumerable<StyleItem> Items(string kind) => State?.items?.Where(i => i.kind == kind) ?? Enumerable.Empty<StyleItem>();
        bool Owned(StyleItem item) => item != null && (item.free || (State?.owned ?? Array.Empty<string>()).Contains(item.kind + ":" + item.id));

        string Chosen(string kind) => kind switch
        {
            "floor" => draft.floor, "wall" => draft.wall, "uniform" => draft.uniform,
            "font" => draft.sign.font, "look" => draft.sign.look, "effect" => draft.sign.effect, _ => "",
        };

        // The new items of the draft (not owned yet) and what they cost together.
        List<StyleItem> ToBuy()
        {
            var list = new List<StyleItem>();
            foreach (var kind in new[] { "floor", "wall", "uniform", "font", "look", "effect" })
            {
                var item = Item(kind, Chosen(kind));
                if (item != null && !Owned(item)) list.Add(item);
            }
            return list;
        }

        // ------------------------------------------------------------------ tabs
        void PickTab(int t) { tab = t; slot = 0; RebuildTab(); Aim(); Refresh(); }

        void RebuildTab()
        {
            foreach (Transform c in content) Destroy(c.gameObject);
            cards.Clear(); swatches.Clear(); paletteChips.Clear(); speedButtons.Clear(); slotA = slotB = null;
            var s = State;
            builtKey = Key();
            nowLabel = Caption(content, "");
            if (tab <= 2 && s != null && !s.insideUnlocked) { Note("Piso, parede e uniforme chegam com a Conveniência, a primeira loja com espaço dentro."); return; }
            if (tab == 3 && s != null && !s.signUnlocked) { Note("O letreiro grande chega com o Mercadinho, na parede do fundo."); return; }
            switch (tab)
            {
                case 0:
                    Caption(content, "Pisos");
                    ItemGrid("floor", 3, Phone ? 168 : 150);
                    if (Item("floor", draft.floor)?.tintable == true) { Caption(content, "Cor do piso"); SwatchGrid(); }
                    break;
                case 1:
                    Caption(content, "Paredes");
                    ItemGrid("wall", 3, Phone ? 168 : 150);
                    if (Item("wall", draft.wall)?.tintable == true) { Caption(content, "Cor da parede"); SwatchGrid(); }
                    break;
                case 2:
                    Caption(content, "Uniforme da equipe");
                    ItemGrid("uniform", 3, Phone ? 120 : 108);
                    if (Item("uniform", draft.uniform)?.tintable == true) { Slots("Roupa", "Detalhes"); SwatchGrid(); }
                    break;
                case 3:
                    Caption(content, "Fonte");
                    ItemGrid("font", 4, Phone ? 108 : 96);
                    Caption(content, "Estilo das letras");
                    ItemGrid("look", 3, Phone ? 110 : 98);
                    Caption(content, "Efeito");
                    ItemGrid("effect", 3, Phone ? 110 : 98);
                    if (draft.sign.effect != CheckoutMarketStyle.Static) Speeds();
                    if (draft.sign.look == "colorido") { Caption(content, "Cores das letras"); Palettes(); }
                    if (draft.sign.look != CheckoutMarketStyle.Classic) { Slots(draft.sign.look == "degrade" ? "Em cima" : "Cor principal", draft.sign.look == "degrade" ? "Embaixo" : "Segunda cor"); SwatchGrid(); }
                    break;
            }
        }
        // What decides the tab's layout (a tintable item picked, a look with colours...): it is rebuilt when this changes.
        string Key() => tab + "|" + (Item("floor", draft.floor)?.tintable == true) + (Item("wall", draft.wall)?.tintable == true) + (Item("uniform", draft.uniform)?.tintable == true)
            + draft.sign.look + (draft.sign.effect == CheckoutMarketStyle.Static) + (State?.insideUnlocked ?? true) + (State?.signUnlocked ?? true) + (State?.items?.Length ?? 0);

        void Note(string text)
        {
            var box = N.Image(content, "Note", K.Paper, 16); box.gameObject.AddComponent<LayoutElement>().preferredHeight = Phone ? 120 : 100;
            var t = U.Label(box.transform, "Text", K.Body, Phone ? 20 : 18, "6B5640"); t.text = text; t.textWrappingMode = TextWrappingModes.Normal;
            U.Stretch(t.rectTransform, Vector2.zero, Vector2.one, new Vector2(16, 8), new Vector2(-16, -8));
        }

        void ItemGrid(string kind, int columns, float height)
        {
            var items = Items(kind).ToList();
            var grid = Grid(content, kind + " grid", columns, height);
            foreach (var item in items) { var it = item; Card(grid, it, () => PickItem(it)); }
        }

        void Card(RectTransform grid, StyleItem item, Action onTap)
        {
            var ring = N.Image(grid, "Card " + item.kind + " " + item.id, K.Border, 16); ring.raycastTarget = true;
            var face = N.Image(ring.transform, "Face", K.Cream, 14); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 3), new Vector2(-3, -3));
            bool big = item.kind == "floor" || item.kind == "wall";
            float split = big ? .36f : item.kind == "uniform" ? .4f : .44f;
            var art = N.Node("Art", face.transform); U.Stretch(art, new Vector2(0, split), Vector2.one, new Vector2(6, 2), new Vector2(-6, -6));
            if (big)
            {
                var tex = item.free ? null : Resources.Load<Texture2D>("CheckoutStyle/Textures/" + (item.kind == "floor" ? "Floor_" : "Wall_") + item.id + "_thumb");
                if (tex)
                {
                    var raw = new GameObject("Texture", typeof(RectTransform)).AddComponent<RawImage>(); raw.transform.SetParent(art, false); raw.texture = tex; raw.raycastTarget = false;
                    U.Stretch(raw.rectTransform, Vector2.zero, Vector2.one);
                    if (item.tintable) raw.color = Color.Lerp(Color.white, K.C(CheckoutMarketStyle.Hex(item.color, "FFFFFF")), .6f);
                }
                else { var plain = N.Image(art, "Classic", K.C(item.kind == "floor" ? "EDE3D0" : "F3ECDD"), 10); U.Stretch(plain.rectTransform, Vector2.zero, Vector2.one); }
            }
            else if (item.kind == "uniform")
            {
                if (item.free) { var t = U.Label(art, "Original", K.Label, Phone ? 18 : 16, "4A3624"); t.text = "Original"; U.Stretch(t.rectTransform, Vector2.zero, Vector2.one); }
                else
                {
                    var a = N.Image(art, "Main", K.C(CheckoutMarketStyle.Hex(item.main, "888888")), 12); U.Stretch(a.rectTransform, new Vector2(.08f, .06f), new Vector2(.62f, .94f));
                    var b = N.Image(art, "Detail", K.C(CheckoutMarketStyle.Hex(item.detail, "CCCCCC")), 12); U.Stretch(b.rectTransform, new Vector2(.5f, .06f), new Vector2(.92f, .94f));
                    if (item.tintable) { var q = U.Label(art, "Any", K.Headline, Phone ? 26 : 22, "FFFFFF"); q.text = "?"; U.Stretch(q.rectTransform, Vector2.zero, Vector2.one); }
                }
            }
            else
            {
                var t = U.Label(art, "Sample", item.kind == "font" ? CheckoutMarketStyle.SignFont(item.id) : K.Headline, Phone ? 30 : 26, "1D2B4F");
                t.text = item.kind == "font" ? "Abc" : Sample(item.id); t.enableAutoSizing = true; t.fontSizeMin = 12; t.fontSizeMax = Phone ? 32 : 28;
                U.Stretch(t.rectTransform, Vector2.zero, Vector2.one);
                if (item.kind == "look") StyleSample(t, item.id);
            }
            var name = U.Label(face.transform, "Name", K.Label, Phone ? 16 : 14, "4A3624"); name.text = CheckoutI18n.T(item.name);
            name.enableAutoSizing = true; name.fontSizeMin = 10; name.fontSizeMax = Phone ? 16 : 14;
            U.Stretch(name.rectTransform, new Vector2(0, split * .42f), new Vector2(1, split), new Vector2(4, 0), new Vector2(-4, 0));
            var price = U.Label(face.transform, "Price", K.Body, Phone ? 15 : 13, "8A7560"); price.name = "Price";
            U.Stretch(price.rectTransform, Vector2.zero, new Vector2(1, split * .45f), new Vector2(4, 2), new Vector2(-4, 0));
            U.Tap(ring, onTap);
            cards.Add((ring, item.kind, item.id));
        }

        static string Sample(string id) => id switch
        {
            "fixo" => "ABC", "pulsar" => "◐", "piscar" => "✦", "falhando" => "A_C", "letra" => "A··", "onda" => "∿", "alternar" => "⇄", "arco-iris" => "★", "brilho" => "✧", _ => "ABC",
        };
        static void StyleSample(TextMeshProUGUI t, string look)
        {
            t.text = "ABC";
            switch (look)
            {
                case "classico": t.color = K.C("D9A521"); break;
                case "liso": t.color = K.C("E53935"); break;
                case "caixa": t.color = K.C("FFD54F"); t.fontStyle = FontStyles.Bold; break;
                case "contorno": t.color = K.C("FFD54F"); t.outlineWidth = .3f; t.outlineColor = K.C("1D2B4F"); break;
                case "degrade": t.enableVertexGradient = true; t.color = Color.white; t.colorGradient = new VertexGradient(K.C("FFD54F"), K.C("FFD54F"), K.C("E53935"), K.C("E53935")); break;
                case "colorido": t.text = "<color=#E53935>A</color><color=#FDD835>B</color><color=#1E88E5>C</color>"; t.richText = true; break;
                case "neon": t.color = K.C("FF4FD8"); break;
                case "neon-placa": t.color = K.C("4FF5FF"); break;
                case "lampadas": t.text = "•ABC•"; t.color = K.C("FFB300"); break;
            }
        }

        void SwatchGrid()
        {
            var grid = N.Node("Swatches", content);
            var gl = grid.gameObject.AddComponent<GridLayoutGroup>(); float cell = Phone ? 70 : 56; gl.cellSize = new Vector2(cell, cell); gl.spacing = new Vector2(Phone ? 6 : 9, Phone ? 7 : 9);
            gl.constraint = GridLayoutGroup.Constraint.FixedColumnCount; gl.constraintCount = 8; gl.childAlignment = TextAnchor.UpperCenter;
            var list = State?.swatches != null && State.swatches.Length > 0 ? State.swatches : Fallback;
            // the sign also wants the neon colours
            if (tab == 3) list = list.Concat(new[] { "FF4FD8", "4FF5FF", "B6FF4F", "FFF35C", "FF6B3D", "FFFFFF", "9D7CFF", "FF2E63" }).ToArray();
            foreach (var hex in list)
            {
                var h = hex;
                var ring = N.Image(grid, "Swatch " + h, K.Border, 14); ring.raycastTarget = true;
                var face = N.Image(ring.transform, "Face", K.C(h), 12); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(4, 4), new Vector2(-4, -4));
                U.Tap(ring, () => PickColour(h));
                swatches.Add((ring, h));
            }
        }
        static readonly string[] Fallback = { "1D2B4F", "2F6FA8", "0F6A6E", "1E8C7A", "1F4D36", "4F6129", "7CB342", "D3A53D", "F2C230", "E38B2C", "B9561A", "C0392B", "8A1C2B", "A8436A", "E86A9E", "5E4F8C", "4B2A6B", "3B2418", "4A2C20", "8D6E63", "2E3236", "6B7280", "BFC5CC", "F4F6F8" };

        void Slots(string a, string b)
        {
            var row = N.Node("Slots", content); var sr = N.Row(row.gameObject, 10); sr.childForceExpandWidth = true; sr.childControlHeight = true; row.gameObject.AddComponent<LayoutElement>().preferredHeight = Tap;
            slotA = Btn(row, a, "secondary", () => { slot = 0; Refresh(); }, Tap);
            slotB = Btn(row, b, "secondary", () => { slot = 1; Refresh(); }, Tap);
            slotADot = Dot(slotA); slotBDot = Dot(slotB);
        }
        Image Dot(CheckoutDesktopButton b)
        {
            var dot = N.Image(b.transform.Find("Face"), "Colour", Color.white, 10); dot.transform.SetAsFirstSibling();
            var le = dot.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = le.preferredHeight = Phone ? 34 : 28;
            var o = dot.gameObject.AddComponent<Outline>(); o.effectColor = new Color(.29f, .21f, .14f, .6f); o.effectDistance = new Vector2(2, -2);
            return dot;
        }

        void Palettes()
        {
            var grid = Grid(content, "Palettes", 3, Phone ? 72 : 62);
            foreach (var p in State?.palettes ?? Array.Empty<StylePalette>())
            {
                var pal = p;
                var ring = N.Image(grid, "Palette " + p.id, K.Border, 14); ring.raycastTarget = true;
                var face = N.Image(ring.transform, "Face", K.Cream, 12); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 3), new Vector2(-3, -3));
                int n = Mathf.Max(1, p.colors?.Length ?? 0);
                for (int i = 0; i < n; i++) { var c = N.Image(face.transform, "C" + i, K.C(p.colors[i]), 4); U.Stretch(c.rectTransform, new Vector2((float)i / n, .45f), new Vector2((float)(i + 1) / n, 1), new Vector2(i == 0 ? 6 : 1, 0), new Vector2(i == n - 1 ? -6 : -1, -6)); }
                var name = U.Label(face.transform, "Name", K.Label, Phone ? 14 : 12, "4A3624"); name.text = CheckoutI18n.T(p.name); U.Stretch(name.rectTransform, Vector2.zero, new Vector2(1, .45f));
                U.Tap(ring, () => { draft.sign.palette = pal.id; Changed(); });
                paletteChips.Add((ring, p.id));
            }
        }

        void Speeds()
        {
            Caption(content, "Velocidade do efeito");
            var row = N.Node("Speeds", content); var sr = N.Row(row.gameObject, 8); sr.childForceExpandWidth = true; sr.childControlHeight = true; row.gameObject.AddComponent<LayoutElement>().preferredHeight = Tap - 8;
            string[] labels = { "Devagar", "Normal", "Rápido" };
            for (int i = 0; i < 3; i++) { int v = i; speedButtons.Add((Btn(row, labels[i], "secondary", () => { draft.sign.speed = v; Changed(); }, Tap - 8), v)); }
        }

        // ------------------------------------------------------------------ picking
        void PickItem(StyleItem item)
        {
            switch (item.kind)
            {
                case "floor": draft.floor = item.id; if (item.tintable && CheckoutMarketStyle.Hex(draft.floorColor, "") == "") draft.floorColor = item.color; if (!item.tintable) draft.floorColor = ""; break;
                case "wall": draft.wall = item.id; if (item.tintable && CheckoutMarketStyle.Hex(draft.wallColor, "") == "") draft.wallColor = item.color; if (!item.tintable) draft.wallColor = ""; break;
                case "uniform":
                    draft.uniform = item.id;
                    if (!item.tintable) { draft.uniformMain = item.main ?? ""; draft.uniformDetail = item.detail ?? ""; }
                    else if (CheckoutMarketStyle.Hex(draft.uniformMain, "") == "") { draft.uniformMain = item.main; draft.uniformDetail = item.detail; }
                    break;
                case "font": draft.sign.font = item.id; break;
                case "look":
                    draft.sign.look = item.id;
                    if (item.id != CheckoutMarketStyle.Classic && CheckoutMarketStyle.Hex(draft.sign.main, "") == "") { draft.sign.main = item.id.StartsWith("neon") ? "FF4FD8" : "FFD54F"; draft.sign.second = item.id.StartsWith("neon") ? "4FF5FF" : "E53935"; }
                    if (item.id == CheckoutMarketStyle.Classic) { draft.sign.main = ""; draft.sign.second = ""; }
                    break;
                case "effect": draft.sign.effect = item.id; break;
            }
            Changed();
        }

        void PickColour(string hex)
        {
            switch (tab)
            {
                case 0: draft.floorColor = hex; break;
                case 1: draft.wallColor = hex; break;
                case 2: if (slot == 0) draft.uniformMain = hex; else draft.uniformDetail = hex; break;
                case 3: if (slot == 0) draft.sign.main = hex; else draft.sign.second = hex; break;
            }
            Changed();
        }

        void Changed()
        {
            if (Key() != builtKey) RebuildTab();
            Preview(); Refresh();
        }

        void Preview() => CheckoutMarketStyle.Active?.Preview(draft);

        bool IsChanged { get { var s = CheckoutMarketStyle.Active; return s && !draft.Same(s.Saved); } }
        static bool IsClassic(StyleChoice c) => c.Same(new StyleChoice());

        string CurrentColour()
        {
            switch (tab)
            {
                case 0: return CheckoutMarketStyle.Hex(draft.floorColor, "");
                case 1: return CheckoutMarketStyle.Hex(draft.wallColor, "");
                case 2: return CheckoutMarketStyle.Hex(slot == 0 ? draft.uniformMain : draft.uniformDetail, "");
                default: return CheckoutMarketStyle.Hex(slot == 0 ? draft.sign.main : draft.sign.second, "");
            }
        }

        void Refresh()
        {
            if (!root || !root.gameObject.activeSelf) return;
            if (Key() != builtKey) RebuildTab();
            var bridge = FindAnyObjectByType<CheckoutBridge>();
            double coins = bridge && bridge.State != null ? bridge.State.coins : 0, gems = bridge && bridge.State != null ? bridge.State.diamonds : 0;
            var buy = ToBuy();
            int coinPrice = buy.Sum(i => i.coinPrice), gemPrice = buy.Sum(i => i.diamondPrice);
            bool changed = IsChanged;
            if (nowLabel) nowLabel.text = !changed ? CheckoutI18n.T("Toque numa opção para ver no seu mercado")
                : buy.Count == 0 ? CheckoutI18n.T("Prévia · tudo isso já é seu: aplique de graça")
                : CheckoutI18n.F("Prévia · novidades: {0}", string.Join(", ", buy.Select(i => CheckoutI18n.T(i.name))));
            bool pay = changed && buy.Count > 0 && !busy;
            applyGems.gameObject.SetActive(buy.Count > 0);
            if (!changed) applyCoins.Apply(Data("Escolha algo para mudar", "secondary", false, ""));
            else if (buy.Count == 0) applyCoins.Apply(Data("Aplicar · grátis", "success", !busy, "Icons/success"));
            else applyCoins.Apply(Data(pay && coins < coinPrice ? CheckoutI18n.F("Faltam {0} moedas", CheckoutI18n.Number(coinPrice - coins)) : CheckoutI18n.F("Comprar · {0}", CheckoutI18n.Number(coinPrice)), "coin", pay && coins >= coinPrice, "Icons/coin"));
            applyGems.Apply(Data(CheckoutI18n.F("Comprar · {0}", CheckoutI18n.Number(gemPrice)), "gem", pay, "Icons/diamond"));
            classic.Apply(Data("Clássico", "secondary", !busy && !IsClassic(draft), ""));
            cancel.Apply(Data("Cancelar", "danger", !busy, ""));
            string[] names = { "Piso", "Parede", "Uniforme", "Letreiro" };
            for (int i = 0; i < 4; i++) tabs[i].Apply(Data(names[i], "secondary", true, "", tab == i));
            foreach (var c in cards)
            {
                bool on = Chosen(c.kind) == c.id;
                Mark(c.ring, on);
                var item = Item(c.kind, c.id); var price = c.ring.transform.Find("Face/Price")?.GetComponent<TextMeshProUGUI>();
                if (price && item != null) price.text = item.free ? CheckoutI18n.T("Grátis") : Owned(item) ? CheckoutI18n.T("✓ Seu") : CheckoutI18n.F("{0} moedas", CheckoutI18n.Number(item.coinPrice));
            }
            var current = CurrentColour();
            foreach (var w in swatches) Mark(w.ring, w.hex == current);
            foreach (var p in paletteChips) Mark(p.ring, p.id == draft.sign.palette);
            foreach (var sb in speedButtons) sb.button.Apply(Data(sb.button.Data?.label ?? "", "secondary", true, "", draft.sign.speed == sb.value));
            if (slotA)
            {
                string a = tab == 2 ? draft.uniformMain : draft.sign.main, b = tab == 2 ? draft.uniformDetail : draft.sign.second;
                slotA.Apply(Data(slotA.Data?.label ?? "", "secondary", true, "", slot == 0)); slotB.Apply(Data(slotB.Data?.label ?? "", "secondary", true, "", slot == 1));
                slotADot.color = K.C(CheckoutMarketStyle.Hex(a, "FFFFFF")); slotBDot.color = K.C(CheckoutMarketStyle.Hex(b, "FFFFFF"));
            }
        }
        static void Mark(Image ring, bool on) { ring.color = on ? K.C("E0A441") : K.Border; ring.rectTransform.localScale = on ? Vector3.one * 1.04f : Vector3.one; }

        // ------------------------------------------------------------------ actions
        void ApplyWith(string currency)
        {
            if (busy || !IsChanged) return;
            var host = CheckoutDesktopHost.Active; if (!host) return;
            var buy = ToBuy(); var bridge = FindAnyObjectByType<CheckoutBridge>();
            int coinPrice = buy.Sum(i => i.coinPrice);
            if (buy.Count > 0 && currency == "coins" && bridge && bridge.State != null && bridge.State.coins < coinPrice)
            { Toast(CheckoutI18n.F("Faltam {0} moedas.", CheckoutI18n.Number(coinPrice - bridge.State.coins)), false); return; }
            busy = true; Refresh();
            var choice = draft.Clone();
            // the choice travels as one JSON string argument
            string json = choice.Json().Replace("\\", "\\\\").Replace("\"", "\\\"");
            host.Action("applyMarketStyle", "[\"" + json + "\",\"" + currency + "\"]", "", (ok, reason) =>
            {
                busy = false;
                if (ok)
                {
                    CheckoutMarketStyle.Active?.Adopt(choice);
                    Toast(buy.Count > 0 ? "Estilo novo no mercado!" : "Estilo aplicado!", true);
                    StartCoroutine(U.Pop(panel, 1.03f, .3f));
                    Refresh();
                    return;
                }
                var now = FindAnyObjectByType<CheckoutBridge>()?.State;
                if (currency == "diamonds" && now != null && now.diamonds < buy.Sum(i => i.diamondPrice))
                { Leave(true); var hud = FindAnyObjectByType<CheckoutDesktopHUD>(); if (hud) hud.Notify(reason, false); return; }
                Toast(string.IsNullOrEmpty(reason) || reason == "game-rule-rejected" ? CheckoutI18n.T("Não foi possível agora.") : reason, false);
                Refresh();
            });
        }

        // Back to the classic look in the draft (applying it is free: everything classic is free).
        void BackToClassic()
        {
            if (busy) return;
            draft = new StyleChoice(); slot = 0;
            Changed();
        }

        void Cancel() { if (Open) Leave(false); }

        void Toast(string message, bool ok)
        {
            toastText.text = CheckoutI18n.T(message);
            toastFace.color = K.C(ok ? "5DA637" : "E15533"); toastRect.GetComponent<Image>().color = K.C(ok ? "427A24" : "C0401F");
            toastRect.gameObject.SetActive(true); toastRect.SetAsLastSibling(); toastUntil = Time.unscaledTime + 2.4f;
        }

        void Update()
        {
            if (!Open) return;
            if (toastRect.gameObject.activeSelf && Time.unscaledTime > toastUntil) toastRect.gameObject.SetActive(false);
            if (Input.GetKeyDown(KeyCode.Escape)) { Cancel(); return; }
            if (Time.frameCount % 15 == 0) Refresh();
        }

        // ------------------------------------------------------------------ QA (CheckoutAutoTest "eventsstyle")
        public static string QaStatus => !instance ? "no panel" : $"open={Open} tab={instance.tab} busy={instance.busy} changed={instance.IsChanged} buy={string.Join(",", instance.ToBuy().Select(i => i.kind + ":" + i.id))} draft={instance.draft.Json()}";
        public static bool QaBusy => instance && instance.busy;
        public static void QaTab(int t) { if (Open) instance.PickTab(t); }
        public static bool QaPick(string kind, string id) { if (!Open) return false; var item = instance.Item(kind, id); if (item == null) return false; instance.PickItem(item); return true; }
        public static void QaColour(int slotIndex, string hex) { if (!Open) return; instance.slot = slotIndex; instance.PickColour(hex); }
        public static void QaSpeed(int v) { if (!Open) return; instance.draft.sign.speed = v; instance.Changed(); }
        public static void QaPalette(string id) { if (!Open) return; instance.draft.sign.palette = id; instance.Changed(); }
        public static CheckoutDesktopButton QaButton(string which) => !instance ? null : which switch
        {
            "coins" => instance.applyCoins, "diamonds" => instance.applyGems, "classic" => instance.classic, "cancel" => instance.cancel, _ => null,
        };
    }
}
