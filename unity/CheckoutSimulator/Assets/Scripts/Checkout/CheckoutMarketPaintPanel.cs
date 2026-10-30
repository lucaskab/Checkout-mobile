using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout
{
    // "Cores do mercado" picker (Lucas 30/10: "como é mobile, tem que ser bem fácil de fazer"). A panel on the right of the
    // screen; the market stays in view on the left (the camera draws only there and frames the shop) and wears every
    // colour the moment it is tapped (CheckoutMarketPaint.Preview). From the top:
    //  - curated palettes as big one-tap chips (both colours and the name), and "Recentes" (the last 3 applied);
    //  - two slot tabs, Principal (the navy's place) and Destaque (the gold's place), each showing its colour;
    //  - for the slot picked: 24 swatches, then a hue bar and a brightness bar (big handles) for any colour at all;
    //  - the price buttons ("Aplicar · 7.700" coins / "Aplicar · 25" diamonds, only when something changed),
    //    "Voltar ao clássico" (free) and "Cancelar" (the market goes back to the player's colours).
    // Nothing is typed. The rules and prices are the game's (src/data/market-paint.ts, applyMarketPaint / resetMarketPaint).
    // Opened from Loja › Decoração ("@paint") and from the build mode's tray ("Cores").
    public class CheckoutMarketPaintPanel : MonoBehaviour
    {
        public static bool Open => instance && instance.root && instance.root.gameObject.activeSelf;
        static CheckoutMarketPaintPanel instance;
        // What the player was trying when the panel closed for the diamond store: it comes back on the next open.
        static string keptPrimary, keptAccent;

        static bool Phone => CheckoutScreen.Handheld;
        static float Tap => Phone ? 72 : 54;          // ≥ 44 pt on an iPhone in landscape (680 units ≈ 430 pt)
        static readonly CultureInfo Br = new CultureInfo("pt-BR");

        RectTransform root, panel, paletteList, recentRow, recentList, swatchGrid, toastRect;
        TextMeshProUGUI title, nowLabel, toastText, slotHint;
        Image primaryChip, accentChip, hueHandle, lightHandle, toastFace;
        RawImage hueBar, lightBar; Texture2D hueTex, lightTex;
        CheckoutDesktopButton slotPrimary, slotAccent, applyCoins, applyGems, classic, cancel, viewFront, viewInside, viewStorage;
        readonly List<(Image face, Image ring, PaintPalette palette)> chips = new List<(Image, Image, PaintPalette)>();
        readonly List<(Image face, Image ring, PaintPalette palette)> recentChips = new List<(Image, Image, PaintPalette)>();
        readonly List<(Image face, Image ring, string hex)> swatches = new List<(Image, Image, string)>();
        readonly List<Canvas> hidden = new List<Canvas>();
        GameObject blocker;

        string draftPrimary = CheckoutMarketPaint.ClassicPrimary, draftAccent = CheckoutMarketPaint.ClassicAccent;
        int slot; // 0 = principal, 1 = destaque
        float hue, light = .5f, baseSat = .7f; // the bars of the slot shown
        bool busy; int camView; float toastUntil; // view: 0 façade, 1 inside, 2 storage
        (Vector3 focus, float zoom) cameraBefore; bool cameraSaved;
        // The game camera keeps the whole screen; its picture is moved left by the panel's share, so the market sits in
        // the middle of the free part and the panel covers only city.
        Camera cameraShifted; float shift;
        void LateUpdate()
        {
            if (!cameraShifted || shift <= 0) return;
            cameraShifted.ResetProjectionMatrix();
            cameraShifted.projectionMatrix = Matrix4x4.Translate(new Vector3(-shift, 0, 0)) * cameraShifted.projectionMatrix;
        }
        string lastPaletteKey = "";

        // ------------------------------------------------------------------ open / close
        public static void Show() => Show(null);
        /// <summary>Opens the picker; `closed` runs when it closes (the build mode hides its HUD meanwhile and shows it again).</summary>
        public static void Show(Action closed)
        {
            var paint = CheckoutMarketPaint.Active; var host = CheckoutDesktopHost.Active;
            if (!paint || !host || (CheckoutBuildMode.Open && closed == null)) return;
            if (!instance) instance = new GameObject("CheckoutMarketPaintPanel").AddComponent<CheckoutMarketPaintPanel>();
            instance.onClosed = closed;
            instance.Enter();
        }
        Action onClosed;
        public static void Hide() { if (Open) instance.Leave(false); }

        void Enter()
        {
            if (!root) Build();
            var paint = CheckoutMarketPaint.Active;
            draftPrimary = keptPrimary ?? paint.SavedPrimary; draftAccent = keptAccent ?? paint.SavedAccent;
            keptPrimary = keptAccent = null;
            slot = 0; busy = false; camView = 0;
            root.gameObject.SetActive(true);
            GameHud(false);
            FrameMarket(true);
            RebuildPalettes();
            SyncBars();
            Preview();
            Refresh();
        }

        void Leave(bool keepDraft)
        {
            if (keepDraft) { keptPrimary = draftPrimary; keptAccent = draftAccent; }
            root.gameObject.SetActive(false);
            CheckoutMarketPaint.Active?.EndPreview();
            FrameMarket(false);
            GameHud(true);
            var closed = onClosed; onClosed = null; closed?.Invoke();
        }

        // The game's HUD (wallet, toolbar, stockroom buttons) steps aside like in the build mode; the HUD stays navy and gold.
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

        // The camera draws on the left of the panel and frames the shop (the façade, or inside with "Dentro").
        void FrameMarket(bool on)
        {
            var cam = Camera.main; var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
            if (on)
            {
                shift = PanelShare(); cameraShifted = cam;
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
        float PanelShare()
        {
            Canvas.ForceUpdateCanvases();
            var screen = (RectTransform)root.parent; float w = screen.rect.width;
            return w > 0 ? Mathf.Clamp01((panel.rect.width + 24) / w) : .45f;
        }
        void Aim()
        {
            var sim = FindAnyObjectByType<MarketDay.MarketSimulation>(); if (!sim) return;
            var shell = FindAnyObjectByType<CheckoutMarketShell>();
            var fp = CheckoutStall.Small || !shell ? CheckoutStall.Footprint : shell.Footprint;
            float size = Mathf.Max(fp.size.x, fp.size.z);
            if (camView == 2 && CheckoutMarketPaint.Active && CheckoutMarketPaint.Active.StorageBounds(out var depot))
            { sim.Focus(new Vector3(depot.center.x, 0, depot.center.z - depot.size.z * .1f), Mathf.Max(8, Mathf.Max(depot.size.x, depot.size.z) * 1.05f)); return; }
            if (camView == 1) sim.Focus(new Vector3(fp.center.x, 0, fp.center.z), Mathf.Max(7, size * .62f));
            else sim.Focus(new Vector3(fp.center.x, 0, fp.center.z - size * .18f), Mathf.Max(8, size * (CheckoutStall.Small ? 1.5f : .95f)));
        }

        // ------------------------------------------------------------------ build
        void Build()
        {
            root = U.Canvas(transform, "CheckoutMarketPaint", 72);
            // Taps on the market while choosing would open its windows: a clear blocker over the game.
            var block = N.Image(root, "Blocker", new Color(0, 0, 0, 0), 0); U.Stretch(block.rectTransform, Vector2.zero, Vector2.one); block.raycastTarget = true; blocker = block.gameObject;

            float width = Phone ? 640 : 560, pad = Phone ? 14 : 16;
            var edge = N.Image(root, "Panel", K.Border, 26); panel = edge.rectTransform; edge.raycastTarget = true;
            panel.anchorMin = new Vector2(1, 0); panel.anchorMax = Vector2.one; panel.pivot = new Vector2(1, .5f);
            panel.sizeDelta = new Vector2(width, -(Phone ? 12 : 24)); panel.anchoredPosition = new Vector2(-(Phone ? 6 : 12), 0);
            var face = N.Image(panel, "Face", K.Cream, 24); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 6), new Vector2(-3, -3));

            // Header: the title, "Clássico" (back to the brand look, free) and "Cancelar" (the market goes back as it was).
            float headH = Phone ? 64 : 62;
            var head = N.Node("Header", face.transform); U.Stretch(head, new Vector2(0, 1), Vector2.one, new Vector2(pad, -headH), new Vector2(-pad, -6));
            U.Icon(head, "Icon", "Icons/paint", new Vector2(0, .5f), new Vector2(headH - 14, headH - 14), new Vector2((headH - 14) * .5f, 0));
            float headButtons = Phone ? 2 * 138 + 8 : 2 * 128 + 8;
            title = U.Label(head, "Title", K.Headline, Phone ? 24 : 24, "4A3624", TextAlignmentOptions.Left); title.text = "Cores do mercado";
            title.enableAutoSizing = true; title.fontSizeMin = 16; title.fontSizeMax = 24;
            U.Stretch(title.rectTransform, Vector2.zero, Vector2.one, new Vector2(headH - 4, 0), new Vector2(-(headButtons + 6), 0));
            var headRow = N.Node("Header buttons", head); headRow.anchorMin = new Vector2(1, 0); headRow.anchorMax = Vector2.one; headRow.pivot = new Vector2(1, .5f);
            headRow.sizeDelta = new Vector2(headButtons, -6); headRow.anchoredPosition = Vector2.zero;
            var hr = N.Row(headRow.gameObject, 8); hr.childForceExpandWidth = true; hr.childControlHeight = true; hr.childForceExpandHeight = true;
            classic = Btn(headRow, "Clássico", "secondary", BackToClassic, headH - 10);
            cancel = Btn(headRow, "Cancelar", "danger", Cancel, headH - 10);

            // Footer: the two prices (or, when the classic look is picked, its free button).
            float footH = Tap + 12;
            var foot = N.Node("Footer", face.transform); U.Stretch(foot, Vector2.zero, new Vector2(1, 0), new Vector2(pad, 10), new Vector2(-pad, footH));
            var r1 = N.Row(foot.gameObject, 10); r1.childForceExpandWidth = true; r1.childControlHeight = true; r1.childForceExpandHeight = true;
            applyCoins = Btn(foot, "Aplicar", "coin", () => ApplyWith("coins"), Tap);
            applyGems = Btn(foot, "Aplicar", "gem", () => ApplyWith("diamonds"), Tap);

            // Middle: scrolls when the phone is short.
            var view = N.Node("Viewport", face.transform); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(pad, footH + 8), new Vector2(-pad, -headH - 4));
            view.gameObject.AddComponent<RectMask2D>(); var hit = view.gameObject.AddComponent<Image>(); hit.color = new Color(1, 1, 1, 0);
            var content = N.Node("Content", view); content.anchorMin = new Vector2(0, 1); content.anchorMax = Vector2.one; content.pivot = new Vector2(.5f, 1); content.offsetMin = content.offsetMax = Vector2.zero;
            N.Column(content.gameObject, Phone ? 10 : 10, new RectOffset(0, 0, 4, 10));
            content.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = content; scroll.horizontal = false; scroll.vertical = true; scroll.viewport = view; scroll.movementType = ScrollRect.MovementType.Clamped; scroll.scrollSensitivity = 30;

            nowLabel = Caption(content, "");
            Caption(content, "Paletas");
            paletteList = Strip(content, "Palettes", Phone ? 104 : 96, out _);
            var recentHolder = N.Node("Recent", content); N.Column(recentHolder.gameObject, 6); recentRow = recentHolder;
            Caption(recentHolder, "Recentes");
            recentList = Strip(recentHolder, "Recent chips", Phone ? 104 : 96, out _);

            // The two slots.
            var slots = N.Node("Slots", content); var sr = N.Row(slots.gameObject, 10); sr.childForceExpandWidth = true; sr.childControlHeight = true; slots.gameObject.AddComponent<LayoutElement>().preferredHeight = Tap;
            slotPrimary = Btn(slots, "Cor principal", "secondary", () => PickSlot(0), Tap);
            slotAccent = Btn(slots, "Cor de destaque", "secondary", () => PickSlot(1), Tap);
            primaryChip = SlotDot(slotPrimary); accentChip = SlotDot(slotAccent);
            slotHint = Caption(content, "");

            // Swatches: 3 rows of 8 (70 units ≈ 44 pt on a phone).
            var grid = N.Node("Swatches", content); swatchGrid = grid;
            var gl = grid.gameObject.AddComponent<GridLayoutGroup>(); float cell = Phone ? 70 : 56; gl.cellSize = new Vector2(cell, cell); gl.spacing = new Vector2(Phone ? 5 : 9, Phone ? 7 : 9);
            gl.constraint = GridLayoutGroup.Constraint.FixedColumnCount; gl.constraintCount = 8; gl.childAlignment = TextAnchor.UpperCenter;

            // Any colour: hue and brightness, big handles.
            Caption(content, "Qualquer cor");
            hueTex = new Texture2D(256, 1, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            for (int i = 0; i < 256; i++) hueTex.SetPixel(i, 0, Color.HSVToRGB(i / 255f, .85f, .95f));
            hueTex.Apply();
            lightTex = new Texture2D(256, 1, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
            hueBar = Bar(content, "Hue", hueTex, out hueHandle, v => { hue = v; FromBars(); });
            lightBar = Bar(content, "Brightness", lightTex, out lightHandle, v => { light = v; FromBars(); });
            var ends = N.Node("Ends", content); ends.gameObject.AddComponent<LayoutElement>().preferredHeight = 20;
            var dark = U.Label(ends, "Dark", K.Body, 15, "8A7560", TextAlignmentOptions.Left); dark.text = "Escuro"; U.Stretch(dark.rectTransform, Vector2.zero, Vector2.one);
            var lightText = U.Label(ends, "Light", K.Body, 15, "8A7560", TextAlignmentOptions.Right); lightText.text = "Claro"; U.Stretch(lightText.rectTransform, Vector2.zero, Vector2.one);

            // Camera: the façade or the inside.
            var seg = N.Image(root, "View", K.Border, 22); var segRect = seg.rectTransform; seg.raycastTarget = true;
            segRect.anchorMin = segRect.anchorMax = new Vector2(0, 1); segRect.pivot = new Vector2(0, 1); segRect.sizeDelta = new Vector2(Phone ? 450 : 420, Tap); segRect.anchoredPosition = new Vector2(Phone ? 12 : 16, -(Phone ? 10 : 16));
            var segFace = N.Image(seg.transform, "Face", K.Cream, 20); U.Stretch(segFace.rectTransform, Vector2.zero, Vector2.one, new Vector2(2, 4), new Vector2(-2, -2));
            var segRow = N.Row(segFace.gameObject, 4, new RectOffset(5, 5, 4, 4)); segRow.childForceExpandHeight = true; segRow.childControlHeight = true; segRow.childForceExpandWidth = true;
            viewFront = Btn(segFace.transform, "Fachada", "secondary", () => { camView = 0; Aim(); Refresh(); }, Tap - 14);
            viewInside = Btn(segFace.transform, "Dentro", "secondary", () => { camView = 1; Aim(); Refresh(); }, Tap - 14);
            viewStorage = Btn(segFace.transform, "Depósito", "secondary", () => { camView = 2; Aim(); Refresh(); }, Tap - 14);

            // Our own toast (the HUD's is hidden while the picker is open).
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
            t.gameObject.AddComponent<LayoutElement>().preferredHeight = Phone ? 24 : 22; return t;
        }

        RectTransform Strip(Transform parent, string name, float height, out ScrollRect scroll)
        {
            var view = N.Image(parent, name, K.Paper, 16); view.gameObject.AddComponent<LayoutElement>().preferredHeight = height + 12;
            view.gameObject.AddComponent<RectMask2D>(); view.raycastTarget = true;
            var list = N.Node("Chips", view.transform); list.anchorMin = Vector2.zero; list.anchorMax = new Vector2(0, 1); list.pivot = new Vector2(0, .5f); list.offsetMin = list.offsetMax = Vector2.zero;
            var row = N.Row(list.gameObject, Phone ? 10 : 8, new RectOffset(6, 12, 6, 6)); row.childForceExpandHeight = true; row.childControlHeight = true;
            list.gameObject.AddComponent<ContentSizeFitter>().horizontalFit = ContentSizeFitter.FitMode.PreferredSize;
            scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = list; scroll.vertical = false; scroll.horizontal = true; scroll.viewport = view.rectTransform; scroll.movementType = ScrollRect.MovementType.Clamped;
            return list;
        }

        // A palette chip: the two colours side by side in a rounded tile and the name under them.
        (Image face, Image ring) Chip(RectTransform list, PaintPalette p, Action onTap)
        {
            float w = Phone ? 104 : 88;
            var ring = N.Image(list, "Chip " + p.id, K.Border, 18); ring.gameObject.AddComponent<LayoutElement>().preferredWidth = w; ring.raycastTarget = true;
            var face = N.Image(ring.transform, "Face", K.Cream, 16); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 3), new Vector2(-3, -3));
            var left = N.Image(face.transform, "Primary", K.C(p.primary), 12); U.Stretch(left.rectTransform, new Vector2(0, .34f), new Vector2(.62f, 1), new Vector2(6, 0), new Vector2(0, -6));
            var right = N.Image(face.transform, "Accent", K.C(p.accent), 12); U.Stretch(right.rectTransform, new Vector2(.5f, .34f), new Vector2(1, 1), new Vector2(0, 0), new Vector2(-6, -6));
            var name = U.Label(face.transform, "Name", K.Label, Phone ? 15 : 13, "4A3624"); name.text = p.name; U.Stretch(name.rectTransform, Vector2.zero, new Vector2(1, .34f), new Vector2(2, 2), new Vector2(-2, 0));
            U.Tap(ring, onTap);
            return (face, ring);
        }

        Image SlotDot(CheckoutDesktopButton b)
        {
            var faceT = b.transform.Find("Face");
            var dot = N.Image(faceT, "Colour", Color.white, 10); dot.transform.SetAsFirstSibling();
            var le = dot.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = le.preferredHeight = Phone ? 34 : 28;
            var outline = dot.gameObject.AddComponent<Outline>(); outline.effectColor = new Color(.29f, .21f, .14f, .6f); outline.effectDistance = new Vector2(2, -2);
            return dot;
        }

        RawImage Bar(Transform parent, string name, Texture2D tex, out Image handle, Action<float> onValue)
        {
            var holder = N.Node(name, parent); holder.gameObject.AddComponent<LayoutElement>().preferredHeight = Tap;
            var frame = N.Image(holder, "Frame", K.Border, 14); U.Stretch(frame.rectTransform, Vector2.zero, Vector2.one, new Vector2(Tap * .3f, 8), new Vector2(-Tap * .3f, -8));
            var ramp = new GameObject("Ramp", typeof(RectTransform)).AddComponent<RawImage>(); ramp.transform.SetParent(frame.transform, false); ramp.texture = tex;
            U.Stretch(ramp.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 3), new Vector2(-3, -3)); ramp.raycastTarget = false;
            handle = N.Image(frame.transform, "Handle", Color.white, 14);
            var h = handle.rectTransform; h.anchorMin = h.anchorMax = new Vector2(0, .5f); h.pivot = new Vector2(.5f, .5f); h.sizeDelta = new Vector2(Tap * .55f, Tap);
            var inner = N.Image(h, "Inner", Color.white, 10); U.Stretch(inner.rectTransform, Vector2.zero, Vector2.one, new Vector2(5, 5), new Vector2(-5, -5)); inner.name = "Colour";
            var outline = handle.gameObject.AddComponent<Outline>(); outline.effectColor = new Color(.29f, .21f, .14f, .8f); outline.effectDistance = new Vector2(2, -2);
            var drag = frame.gameObject.AddComponent<CheckoutPaintBar>(); frame.raycastTarget = true; drag.Changed = onValue;
            // the whole strip (with its margins) takes the finger
            var pad = N.Image(holder, "Touch", new Color(1, 1, 1, 0), 0); U.Stretch(pad.rectTransform, Vector2.zero, Vector2.one); pad.raycastTarget = true; pad.transform.SetAsFirstSibling();
            var padDrag = pad.gameObject.AddComponent<CheckoutPaintBar>(); padDrag.Changed = onValue; padDrag.Track = frame.rectTransform;
            return ramp;
        }

        // ------------------------------------------------------------------ data
        PaintState State => CheckoutMarketPaint.Active ? CheckoutMarketPaint.Active.State : null;

        void RebuildPalettes()
        {
            var s = State; var palettes = s?.palettes ?? Array.Empty<PaintPalette>(); var recent = s?.recent ?? Array.Empty<PaintPalette>();
            var key = string.Join(",", palettes.Select(p => p.id + p.name)) + "|" + string.Join(",", recent.Select(p => p.primary + p.accent + p.name));
            if (key == lastPaletteKey && swatches.Count > 0) return;
            lastPaletteKey = key;
            foreach (Transform c in paletteList) Destroy(c.gameObject);
            foreach (Transform c in recentList) Destroy(c.gameObject);
            chips.Clear(); recentChips.Clear();
            foreach (var p in palettes) { var pal = p; var c = Chip(paletteList, pal, () => PickPalette(pal)); chips.Add((c.face, c.ring, pal)); }
            foreach (var p in recent) { var pal = p; var c = Chip(recentList, pal, () => PickPalette(pal)); recentChips.Add((c.face, c.ring, pal)); }
            recentRow.gameObject.SetActive(recent.Length > 0);
            if (swatches.Count == 0)
                foreach (var hex in Swatches)
                {
                    var h = hex;
                    var ring = N.Image(swatchGrid, "Swatch " + h, K.Border, 14); ring.raycastTarget = true;
                    var face = N.Image(ring.transform, "Face", K.C(h), 12); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(4, 4), new Vector2(-4, -4));
                    U.Tap(ring, () => PickSwatch(h));
                    swatches.Add((face, ring, h));
                }
        }
        // Same as MARKET_PAINT_SWATCHES (src/data/market-paint.ts).
        static readonly string[] Swatches =
        {
            "1D2B4F", "2F6FA8", "0F6A6E", "1E8C7A", "1F4D36", "4F6129", "7CB342", "D3A53D",
            "F2C230", "E38B2C", "B9561A", "C0392B", "8A1C2B", "A8436A", "E86A9E", "5E4F8C",
            "4B2A6B", "3B2418", "4A2C20", "8D6E63", "2E3236", "6B7280", "BFC5CC", "F4F6F8",
        };

        string Current => slot == 0 ? draftPrimary : draftAccent;
        void SetCurrent(string hex) { if (slot == 0) draftPrimary = hex; else draftAccent = hex; }

        void PickPalette(PaintPalette p) { draftPrimary = CheckoutMarketPaint.Norm(p.primary); draftAccent = CheckoutMarketPaint.Norm(p.accent); SyncBars(); Preview(); Refresh(); }
        void PickSlot(int s) { slot = s; SyncBars(); Refresh(); }
        void PickSwatch(string hex) { SetCurrent(hex); SyncBars(); Preview(); Refresh(); }

        // The bars follow the slot's colour: hue, and brightness from dark (left) through the colour (middle) to light (right).
        void SyncBars()
        {
            Color.RGBToHSV(K.C(Current), out var h, out var s, out var v);
            hue = h; baseSat = Mathf.Max(.05f, s);
            light = .5f * Mathf.Clamp01((v - .1f) / .9f);
            PaintBars();
        }
        void FromBars()
        {
            Color c;
            if (light <= .5f) c = Color.HSVToRGB(hue, baseSat, Mathf.Lerp(.1f, 1f, light * 2));
            else c = Color.HSVToRGB(hue, Mathf.Lerp(baseSat, 0f, (light - .5f) * 2 * .92f), 1f);
            if (baseSat < .12f && light <= .5f) baseSat = .7f; // a grey picked first: moving the hue gives colour
            SetCurrent(ColorUtility.ToHtmlStringRGB(c));
            PaintBars(); Preview(); Refresh();
        }
        void PaintBars()
        {
            for (int i = 0; i < 256; i++)
            {
                float t = i / 255f;
                lightTex.SetPixel(i, 0, t <= .5f ? Color.HSVToRGB(hue, baseSat, Mathf.Lerp(.1f, 1f, t * 2)) : Color.HSVToRGB(hue, Mathf.Lerp(baseSat, 0f, (t - .5f) * 2 * .92f), 1f));
            }
            lightTex.Apply();
            Place(hueHandle, hue); Place(lightHandle, light);
            var col = K.C(Current);
            hueHandle.transform.Find("Colour").GetComponent<Image>().color = Color.HSVToRGB(hue, .85f, .95f);
            lightHandle.transform.Find("Colour").GetComponent<Image>().color = col;
        }
        static void Place(Image handle, float v) { var r = handle.rectTransform; var parent = (RectTransform)r.parent; r.anchoredPosition = new Vector2(Mathf.Clamp01(v) * parent.rect.width, 0); }

        void Preview() => CheckoutMarketPaint.Active?.Preview(draftPrimary, draftAccent);

        bool Changed
        {
            get { var p = CheckoutMarketPaint.Active; return p && (draftPrimary != p.SavedPrimary || draftAccent != p.SavedAccent); }
        }
        static bool IsClassic(string p, string a) => CheckoutMarketPaint.IsClassic(p, a);

        void Refresh()
        {
            if (!root || !root.gameObject.activeSelf) return;
            var s = State; var paint = CheckoutMarketPaint.Active; var bridge = FindAnyObjectByType<CheckoutBridge>();
            double coins = bridge && bridge.State != null ? bridge.State.coins : 0, gems = bridge && bridge.State != null ? bridge.State.diamonds : 0;
            int coinPrice = s?.coinPrice ?? 0, gemPrice = s?.diamondPrice ?? 25;
            bool changed = Changed, toClassic = IsClassic(draftPrimary, draftAccent);
            bool savedClassic = paint && IsClassic(paint.SavedPrimary, paint.SavedAccent);
            string name = PaletteName(draftPrimary, draftAccent);
            nowLabel.text = changed ? CheckoutI18n.F("Prévia: {0} · toque em Aplicar para pintar", CheckoutI18n.T(name)) : CheckoutI18n.F("Seu mercado agora: {0}", CheckoutI18n.T(name));
            // Prices only when something changed. The classic look picked (chip or button) over other colours: one free
            // green button instead of the prices.
            bool pay = changed && !toClassic && !busy, freeBack = changed && toClassic;
            applyGems.gameObject.SetActive(!freeBack);
            if (freeBack) applyCoins.Apply(Data("Voltar ao clássico · grátis", "success", !busy, "Icons/success"));
            else applyCoins.Apply(Data(pay && coins < coinPrice ? CheckoutI18n.F("Faltam {0} moedas", CheckoutI18n.Number(coinPrice - coins)) : CheckoutI18n.F("Aplicar · {0}", CheckoutI18n.Number(coinPrice)), "coin", pay && coins >= coinPrice, "Icons/coin"));
            applyGems.Apply(Data(CheckoutI18n.F("Aplicar · {0}", CheckoutI18n.Number(gemPrice)), "gem", pay, "Icons/diamond"));
            classic.Apply(Data("Clássico", "secondary", !busy && !(savedClassic && toClassic), "", toClassic));
            cancel.Apply(Data("Cancelar", "danger", !busy, ""));
            slotPrimary.Apply(Data("Cor principal", "secondary", true, "", slot == 0));
            slotAccent.Apply(Data("Cor de destaque", "secondary", true, "", slot == 1));
            primaryChip.color = K.C(draftPrimary); accentChip.color = K.C(draftAccent);
            Place(hueHandle, hue); Place(lightHandle, light);
            slotHint.text = slot == 0 ? "No lugar do azul: paredes, toldos, móveis" : "No lugar do dourado: frisos, letreiros, detalhes";
            viewFront.Apply(Data("Fachada", "secondary", true, "", camView == 0)); viewInside.Apply(Data("Dentro", "secondary", true, "", camView == 1));
            // The storage button only when the market has a storage building standing.
            bool hasStorage = paint && paint.StorageBounds(out _);
            viewStorage.gameObject.SetActive(hasStorage); if (!hasStorage && camView == 2) { camView = 0; Aim(); }
            viewStorage.Apply(Data("Depósito", "secondary", true, "", camView == 2));
            foreach (var c in chips) Mark(c.ring, CheckoutMarketPaint.Norm(c.palette.primary) == draftPrimary && CheckoutMarketPaint.Norm(c.palette.accent) == draftAccent);
            foreach (var c in recentChips) Mark(c.ring, CheckoutMarketPaint.Norm(c.palette.primary) == draftPrimary && CheckoutMarketPaint.Norm(c.palette.accent) == draftAccent);
            foreach (var w in swatches) Mark(w.ring, w.hex == Current);
        }
        static void Mark(Image ring, bool on) { ring.color = on ? K.C("E0A441") : K.Border; ring.rectTransform.localScale = on ? Vector3.one * 1.06f : Vector3.one; }

        string PaletteName(string p, string a)
        {
            var s = State;
            var hit = s?.palettes?.FirstOrDefault(x => CheckoutMarketPaint.Norm(x.primary) == p && CheckoutMarketPaint.Norm(x.accent) == a);
            if (hit != null) return hit.name;
            return IsClassic(p, a) ? "Clássico" : "Sua cor";
        }

        // ------------------------------------------------------------------ actions
        void ApplyWith(string currency)
        {
            if (busy || !Changed) return;
            if (IsClassic(draftPrimary, draftAccent)) { BackToClassic(); return; }
            var host = CheckoutDesktopHost.Active; if (!host) return;
            var s = State; var bridge = FindAnyObjectByType<CheckoutBridge>();
            if (currency == "coins" && bridge && bridge.State != null && s != null && bridge.State.coins < s.coinPrice)
            { Toast(CheckoutI18n.F("Faltam {0} moedas.", CheckoutI18n.Number(s.coinPrice - bridge.State.coins)), false); return; }
            busy = true; Refresh();
            string p = draftPrimary, a = draftAccent;
            host.Action("applyMarketPaint", "[\"" + p + "\",\"" + a + "\",\"" + currency + "\"]", "", (ok, reason) =>
            {
                busy = false;
                if (ok)
                {
                    CheckoutMarketPaint.Active?.Adopt(p, a);
                    CheckoutMarketPaint.Active?.Preview(p, a);
                    Toast("Mercado pintado!", true);
                    StartCoroutine(U.Pop(panel, 1.03f, .3f));
                    Refresh();
                    return;
                }
                // Too few diamonds: the game opens the diamond store; the picker closes and keeps the colours for later.
                var now = FindAnyObjectByType<CheckoutBridge>()?.State;
                if (currency == "diamonds" && now != null && now.diamonds < (State?.diamondPrice ?? 25))
                { Leave(true); var hud = FindAnyObjectByType<CheckoutDesktopHUD>(); if (hud) hud.Notify(reason, false); return; }
                Toast(string.IsNullOrEmpty(reason) || reason == "game-rule-rejected" ? CheckoutI18n.T("Não foi possível agora.") : reason, false);
                Refresh();
            });
        }

        void BackToClassic()
        {
            if (busy) return;
            var paint = CheckoutMarketPaint.Active; if (!paint) return;
            draftPrimary = CheckoutMarketPaint.ClassicPrimary; draftAccent = CheckoutMarketPaint.ClassicAccent; SyncBars();
            if (IsClassic(paint.SavedPrimary, paint.SavedAccent)) { Preview(); Refresh(); return; }
            var host = CheckoutDesktopHost.Active; if (!host) return;
            busy = true; Refresh();
            host.Action("resetMarketPaint", "[]", "", (ok, reason) =>
            {
                busy = false;
                if (ok) { paint.Adopt(CheckoutMarketPaint.ClassicPrimary, CheckoutMarketPaint.ClassicAccent); paint.Preview(draftPrimary, draftAccent); Toast("Cores clássicas de volta!", true); }
                else Toast(CheckoutI18n.T("Não foi possível agora."), false);
                Refresh();
            });
        }

        void Cancel() { if (Open) Leave(false); }

        void Toast(string message, bool ok)
        {
            toastText.text = message;
            toastFace.color = K.C(ok ? "5DA637" : "E15533"); toastRect.GetComponent<Image>().color = K.C(ok ? "427A24" : "C0401F");
            toastRect.gameObject.SetActive(true); toastRect.SetAsLastSibling(); toastUntil = Time.unscaledTime + 2.4f;
        }

        void Update()
        {
            if (!Open) return;
            if (toastRect.gameObject.activeSelf && Time.unscaledTime > toastUntil) toastRect.gameObject.SetActive(false);
            if (Input.GetKeyDown(KeyCode.Escape)) { Cancel(); return; }
            // Wallet and prices change while the picker is open (the day goes on).
            if (Time.frameCount % 15 == 0) { RebuildPalettes(); Refresh(); }
        }

        // ------------------------------------------------------------------ QA (CheckoutAutoTest "eventspaintui")
        public static string QaStatus => !instance ? "no panel" : $"open={Open} draft={instance.draftPrimary}/{instance.draftAccent} slot={instance.slot} busy={instance.busy} changed={instance.Changed} saved={CheckoutMarketPaint.Active?.SavedPrimary}/{CheckoutMarketPaint.Active?.SavedAccent} shown={CheckoutMarketPaint.Active?.ShownPrimary}/{CheckoutMarketPaint.Active?.ShownAccent}";
        public static bool QaBusy => instance && instance.busy;
        public static CheckoutDesktopButton QaButton(string which) => !instance ? null : which switch
        {
            "coins" => instance.applyCoins, "diamonds" => instance.applyGems, "classic" => instance.classic, "cancel" => instance.cancel,
            "primary" => instance.slotPrimary, "accent" => instance.slotAccent, "inside" => instance.viewInside, "front" => instance.viewFront, "storage" => instance.viewStorage, _ => null,
        };
        public static GameObject QaChip(string paletteId) => !instance ? null : instance.chips.Where(c => c.palette.id == paletteId).Select(c => c.ring.gameObject).FirstOrDefault();
        public static GameObject QaSwatch(int index) => !instance || index < 0 || index >= instance.swatches.Count ? null : instance.swatches[index].ring.gameObject;
        public static RectTransform QaBar(bool hueBar) => !instance ? null : (RectTransform)(hueBar ? instance.hueBar : instance.lightBar).transform.parent;
    }

    // A colour bar: the finger anywhere on it (or dragging along it) sets the value 0–1.
    public class CheckoutPaintBar : MonoBehaviour, IPointerDownHandler, IDragHandler, IInitializePotentialDragHandler
    {
        public Action<float> Changed;
        public RectTransform Track;
        public void OnInitializePotentialDrag(PointerEventData e) { e.useDragThreshold = false; }
        public void OnPointerDown(PointerEventData e) => Set(e);
        public void OnDrag(PointerEventData e) => Set(e);
        void Set(PointerEventData e)
        {
            var rect = Track ? Track : (RectTransform)transform;
            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(rect, e.position, e.pressEventCamera, out var local)) return;
            Changed?.Invoke(Mathf.Clamp01((local.x - rect.rect.xMin) / Mathf.Max(1, rect.rect.width)));
        }
    }
}
