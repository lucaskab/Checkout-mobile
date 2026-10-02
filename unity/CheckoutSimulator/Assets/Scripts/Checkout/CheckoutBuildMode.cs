using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using MarketDay;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // Build mode: the player arranges the shop (shelves, counters, checkouts, decorations) and decorates the
    // city block around it. Drag to move; hold Ctrl and move the mouse (desktop) or twist two fingers (phone) to
    // turn. Pieces never leave their area: inside the shop they stop at the walls and snap flush against them,
    // outside they stay on the block's paving. New customers wait outside while it is open. "Concluir" saves the
    // layout in the app (saveInteriorLayout); nothing is saved while a counter, shelf or checkout line is blocked.
    public class CheckoutBuildMode : MonoBehaviour
    {
        public static bool Open { get; private set; }
        CheckoutBridge bridge; CheckoutMap map; MarketSimulation simulation;
        RectTransform root, hud, shopFace, grid, selectionBar, waitingPanel; GameObject buildButton, shopDim;
        CheckoutDesktopButton buildButtonView; int buildButtonCount = -1; GameObject inventoryBadge; TMPro.TextMeshProUGUI inventoryBadgeText;
        readonly Dictionary<string, CheckoutDesktopButton> waitingButtons = new Dictionary<string, CheckoutDesktopButton>();
        Dictionary<string, (string type, string template)> waitingBefore = new Dictionary<string, (string type, string template)>();
        TextMeshProUGUI status, coins, diamonds, shopCoins, shopDiamonds, selectedName, selectedZone;
        Image selectedIcon;
        CheckoutDesktopButton storeButton, tabInside, tabOutside, viewInside, viewOutside;
        CheckoutInterior.Item selected, dragging;
        Vector3 dragOffset, dragStartPosition; float dragStartRot; Vector2 pointerDown; bool pointerMoved, pressOnItem;
        bool rotating, twisting; float rotStart, rotAccum, lastTwist; Vector3 rotStartPosition; Vector2 lastMouse;
        InteriorItem[] backup;
        (Vector3 focus, float zoom) cameraBefore;
        Material okMaterial, badMaterial, spotMaterial;
        Transform footprint; readonly List<Transform> spots = new List<Transform>();
        float refresh, messageUntil; string shopZone = "inside";
        readonly CultureInfo br = new CultureInfo("pt-BR");

        CheckoutInterior Interior => map ? map.Interior : null;
        static CheckoutBuildMode instance;
        // The HUD's "Colocar" buttons (shop, inventory cards) open the build mode directly.
        public static void OpenFromHud() { if (instance && instance.enabled && !Open && !CheckoutMapEditor.Open) instance.Enter(); }
        static bool Touch => Input.touchSupported && Application.isMobilePlatform;
        string HowTo => Touch ? "Arraste para mover  •  Gire com dois dedos" : "Arraste para mover  •  Segure Ctrl e mova o mouse para girar  •  G liga/desliga a grade";

        public void Initialize(CheckoutBridge owner, CheckoutMap projection)
        {
            bridge = owner; map = projection; simulation = FindAnyObjectByType<MarketSimulation>(); instance = this;
            if (!Interior || !Interior.Ready) { enabled = false; return; }
            root = U.Canvas(transform, "CheckoutBuildMode", 60);
            var b = U.Button(root, "Construir", "primary", Enter, 72, 26);
            b.Apply(Data("Construir", "primary", true, "Icons/hammer"));
            U.At((RectTransform)b.transform, new Vector2(0, 0), new Vector2(240, 72), new Vector2(140, 200)); // above the desktop toolbar
            buildButton = b.gameObject; buildButtonView = b;
            // Red counter in the corner: bought furniture waiting in the inventory for a spot.
            var pill = CheckoutDesktopCard.Image(b.transform, "Inventory badge", K.C("E15533"), 16);
            var pr = pill.rectTransform; pr.anchorMin = pr.anchorMax = pr.pivot = Vector2.one; pr.anchoredPosition = new Vector2(10, 12); pr.sizeDelta = new Vector2(34, 34);
            inventoryBadgeText = CheckoutDesktopCard.Text(pill.transform, "Count", K.Number, 18, Color.white); inventoryBadgeText.alignment = TMPro.TextAlignmentOptions.Center;
            var tr = inventoryBadgeText.rectTransform; tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one; tr.offsetMin = tr.offsetMax = Vector2.zero;
            inventoryBadge = pill.gameObject; inventoryBadge.SetActive(false);
            BuildHud();
            okMaterial = Flat(new Color(.36f, .78f, .35f, .38f)); badMaterial = Flat(new Color(.9f, .28f, .22f, .42f)); spotMaterial = Flat(new Color(1f, .85f, .3f, .7f));
            footprint = Quad("Build footprint", okMaterial).transform;
            footprint.gameObject.SetActive(false);
        }

        static Material Flat(Color c) { var m = new Material(Shader.Find("Sprites/Default")); m.color = c; m.renderQueue = 3100; return m; }
        static GameObject Quad(string name, Material m)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad); q.name = name; Destroy(q.GetComponent<Collider>());
            q.GetComponent<Renderer>().sharedMaterial = m; q.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return q;
        }
        static DesktopButton Data(string label, string variant, bool enabled, string icon = "", bool active = false) =>
            new DesktopButton { label = label, variant = variant, enabled = enabled, active = active, icon = icon, action = "", args = "[]", route = "", after = "", ok = "", fail = "" };

        // ------------------------------------------------------------------ HUD
        void BuildHud()
        {
            hud = Node(root, "Build HUD"); U.Stretch(hud, Vector2.zero, Vector2.one);

            // Title card with the current hint.
            var edge = U.Shape(hud, "Banner edge", "D4B482", 26, new Vector2(.5f, 1), new Vector2(820, 112), new Vector2(0, -70));
            var face = U.Box(edge.transform, "Banner", "FFF7EC", 24, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(3, 7); face.rectTransform.offsetMax = new Vector2(-3, -3);
            U.Icon(face.transform, "Hammer", "Icons/hammer", new Vector2(0, .5f), new Vector2(64, 64), new Vector2(52, 0));
            var title = U.Label(face.transform, "Title", K.Headline, 32, "4A3624", TextAlignmentOptions.Left);
            U.Stretch(title.rectTransform, new Vector2(0, .5f), new Vector2(1, 1), new Vector2(96, 0), new Vector2(-20, -6)); title.text = "Modo construção";
            status = U.Label(face.transform, "Status", K.Body, 19, "8A7560", TextAlignmentOptions.Left);
            U.Stretch(status.rectTransform, new Vector2(0, 0), new Vector2(1, .5f), new Vector2(96, 10), new Vector2(-20, 0));

            // Where to build: inside the shop or on the block around it.
            var views = Row(hud, new Vector2(0, 1), new Vector2(430, 72), new Vector2(240, -70), 10, false);
            viewInside = U.Button(views, "Dentro", "secondary", () => Focus("inside"), 60, 21); viewInside.SetWidth(200);
            viewOutside = U.Button(views, "Fora", "secondary", () => Focus("outside"), 60, 21); viewOutside.SetWidth(200);

            // Shop furniture the player owns but has not placed yet: tap to put it in the shop.
            waitingPanel = Column(hud, new Vector2(0, .5f), new Vector2(330, 440), new Vector2(190, 10));
            var wbg = waitingPanel.gameObject.AddComponent<Image>(); wbg.sprite = K.Rounded(26); wbg.type = Image.Type.Sliced; wbg.color = new Color(.11f, .17f, .31f, .92f);
            var wl = waitingPanel.GetComponent<VerticalLayoutGroup>(); wl.padding = new RectOffset(16, 16, 14, 16); wl.spacing = 10;
            var wt = U.Label(waitingPanel, "Heading", K.Headline, 26, "FFD27A", TextAlignmentOptions.Left); wt.text = "Para colocar";
            wt.gameObject.AddComponent<LayoutElement>().preferredHeight = 34;
            var wh = U.Label(waitingPanel, "Hint", K.Body, 15, "DCE6F5", TextAlignmentOptions.Left); wh.text = "Toque para pôr na loja e arraste até o lugar. O que você comprou começa a obra quando concluir.";
            wh.textWrappingMode = TextWrappingModes.Normal; wh.overflowMode = TextOverflowModes.Overflow; wh.gameObject.AddComponent<LayoutElement>().preferredHeight = 58;
            waitingPanel.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            waitingPanel.gameObject.SetActive(false);

            // Wallet.
            var wallet = Row(hud, new Vector2(1, 1), new Vector2(380, 60), new Vector2(-220, -58), 8, true);
            coins = Pill(wallet, "Icons/coin"); diamonds = Pill(wallet, "Icons/diamond");

            var right = Column(hud, new Vector2(1, .5f), new Vector2(230, 250), new Vector2(-135, -10));
            U.Button(right, "Concluir", "success", Finish, 68, 24).Apply(Data("Concluir", "success", true, "Icons/success"));
            U.Button(right, "Loja", "coin", () => ToggleShop()).Apply(Data("Loja", "coin", true, "Icons/cart"));
            U.Button(right, "Cancelar", "secondary", Cancel, 60, 21);

            // Selected piece: picture, name and the actions that apply to it.
            selectionBar = Row(hud, new Vector2(.5f, 0), new Vector2(980, 104), new Vector2(0, 76), 14, true);
            var bar = selectionBar.gameObject.AddComponent<Image>(); bar.sprite = K.Rounded(28); bar.type = Image.Type.Sliced; bar.color = new Color(.11f, .17f, .31f, .92f);
            var pic = new GameObject("Picture", typeof(RectTransform)).AddComponent<Image>(); pic.transform.SetParent(selectionBar, false); pic.preserveAspect = true; pic.raycastTarget = false;
            var picLayout = pic.gameObject.AddComponent<LayoutElement>(); picLayout.preferredWidth = picLayout.preferredHeight = 84; selectedIcon = pic;
            var names = Node(selectionBar, "Names"); var nl = names.gameObject.AddComponent<LayoutElement>(); nl.preferredWidth = 290; nl.preferredHeight = 84;
            selectedName = U.Label(names, "Name", K.Label, 24, "FFFFFF", TextAlignmentOptions.Left); U.Stretch(selectedName.rectTransform, new Vector2(0, .45f), Vector2.one);
            selectedZone = U.Label(names, "Zone", K.Body, 17, "BFD0E8", TextAlignmentOptions.Left); U.Stretch(selectedZone.rectTransform, Vector2.zero, new Vector2(1, .45f));
            U.Button(selectionBar, "Girar -45°", "primary", () => Rotate(-45), 64, 20).SetWidth(160);
            U.Button(selectionBar, "Girar +45°", "primary", () => Rotate(45), 64, 20).SetWidth(160);
            storeButton = U.Button(selectionBar, "Guardar", "danger", Store, 64, 20); storeButton.SetWidth(150);

            BuildShop();
            hud.gameObject.SetActive(false);
        }

        static RectTransform Node(Transform parent, string name) { var t = (RectTransform)new GameObject(name, typeof(RectTransform)).transform; t.SetParent(parent, false); return t; }
        static RectTransform Column(RectTransform parent, Vector2 anchor, Vector2 size, Vector2 offset)
        {
            var t = Node(parent, "Column"); U.At(t, anchor, size, offset);
            var v = t.gameObject.AddComponent<VerticalLayoutGroup>(); v.spacing = 14; v.childControlHeight = v.childControlWidth = true; v.childForceExpandHeight = false; v.childForceExpandWidth = true;
            return t;
        }
        static RectTransform Row(RectTransform parent, Vector2 anchor, Vector2 size, Vector2 offset, float spacing, bool center)
        {
            var t = Node(parent, "Row"); U.At(t, anchor, size, offset);
            var h = t.gameObject.AddComponent<HorizontalLayoutGroup>(); h.spacing = spacing; h.padding = new RectOffset(16, 16, 8, 8); h.childAlignment = center ? TextAnchor.MiddleCenter : TextAnchor.MiddleLeft;
            h.childControlHeight = h.childControlWidth = true; h.childForceExpandHeight = false; h.childForceExpandWidth = false;
            return t;
        }

        // Cream pill with an icon and a number (coins, diamonds).
        static TextMeshProUGUI Pill(RectTransform parent, string icon)
        {
            var pill = U.Box(parent, "Pill", "FFF7EC", 22, Vector2.zero, Vector2.one);
            var le = pill.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = 170; le.preferredHeight = 46;
            U.Icon(pill.transform, "Icon", icon, new Vector2(0, .5f), new Vector2(38, 38), new Vector2(26, 0));
            var t = U.Label(pill.transform, "Value", K.Number, 21, "4A3624", TextAlignmentOptions.Right);
            U.Stretch(t.rectTransform, Vector2.zero, Vector2.one, new Vector2(48, 0), new Vector2(-14, 0));
            return t;
        }

        void BuildShop()
        {
            shopFace = U.Window(hud, out shopDim);
            var head = U.Label(shopFace, "Title", K.Headline, 36, "4A3624", TextAlignmentOptions.Left);
            U.Stretch(head.rectTransform, new Vector2(0, 1), new Vector2(.5f, 1), new Vector2(34, -76), new Vector2(0, -14));
            head.text = "Loja de decoração";
            var wallet = Row(shopFace, new Vector2(1, 1), new Vector2(380, 60), new Vector2(-400, -46), 8, true);
            shopCoins = Pill(wallet, "Icons/coin"); shopDiamonds = Pill(wallet, "Icons/diamond");
            var close = U.Button(shopFace, "Fechar", "secondary", () => ToggleShop(false), 54, 20);
            U.At((RectTransform)close.transform, new Vector2(1, 1), new Vector2(150, 54), new Vector2(-104, -46));
            var tabs = Row(shopFace, new Vector2(.5f, 1), new Vector2(760, 70), new Vector2(0, -118), 14, true);
            tabInside = U.Button(tabs, "Dentro do mercado", "secondary", () => ShowShopZone("inside"), 58, 21); tabInside.SetWidth(340);
            tabOutside = U.Button(tabs, "Fora do mercado", "secondary", () => ShowShopZone("outside"), 58, 21); tabOutside.SetWidth(340);

            // Scrolling grid of cards.
            var view = Node(shopFace, "Viewport"); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(24, 18), new Vector2(-24, -160));
            view.gameObject.AddComponent<RectMask2D>(); var hit = view.gameObject.AddComponent<Image>(); hit.color = new Color(1, 1, 1, 0);
            grid = Node(view, "Grid"); grid.anchorMin = new Vector2(0, 1); grid.anchorMax = new Vector2(1, 1); grid.pivot = new Vector2(.5f, 1); grid.offsetMin = grid.offsetMax = Vector2.zero;
            var g = grid.gameObject.AddComponent<GridLayoutGroup>(); g.cellSize = new Vector2(268, 350); g.spacing = new Vector2(14, 14); g.childAlignment = TextAnchor.UpperCenter; g.padding = new RectOffset(4, 4, 6, 12);
            var fit = grid.gameObject.AddComponent<ContentSizeFitter>(); fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = grid; scroll.horizontal = false; scroll.viewport = view; scroll.scrollSensitivity = 40; scroll.movementType = ScrollRect.MovementType.Clamped;
            shopDim.SetActive(false);
        }

        class Card { public GameObject go; public Image icon; public TextMeshProUGUI price, stock, lockLabel; public Image priceIcon, lockIcon; public GameObject stockBadge; public CheckoutDesktopButton buy, place; }
        readonly Dictionary<string, Card> cards = new Dictionary<string, Card>();

        Card MakeCard(DecorEntry d)
        {
            var c = new Card();
            var edge = U.Box(grid, d.id, "D4B482", 20, Vector2.zero, Vector2.one); c.go = edge.gameObject;
            var face = U.Box(edge.transform, "Face", "FFF7EC", 18, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(3, 6); face.rectTransform.offsetMax = new Vector2(-3, -3);
            var stage = U.Box(face.transform, "Stage", "FBEEDA", 16, new Vector2(0, 1), new Vector2(1, 1)); stage.rectTransform.offsetMin = new Vector2(10, -150); stage.rectTransform.offsetMax = new Vector2(-10, -10);
            c.icon = U.Icon(stage.transform, "Picture", "Decor/" + d.id, new Vector2(.5f, .5f), new Vector2(138, 138));
            var name = U.Label(face.transform, "Name", K.Label, 20, "4A3624"); U.Stretch(name.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(10, -184), new Vector2(-10, -154)); name.text = d.name;
            var desc = U.Label(face.transform, "Desc", K.Body, 14, "8A7560"); desc.textWrappingMode = TextWrappingModes.Normal; desc.overflowMode = TextOverflowModes.Truncate;
            U.Stretch(desc.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(14, -230), new Vector2(-14, -184)); desc.text = d.description;
            // Price (or level lock) and how many are waiting in stock.
            var priceRow = U.Box(face.transform, "Price", "FFFFFF", 16, new Vector2(.5f, 0), new Vector2(.5f, 0)); U.At(priceRow.rectTransform, new Vector2(.5f, 0), new Vector2(170, 36), new Vector2(0, 86));
            c.priceIcon = U.Icon(priceRow.transform, "Icon", d.coinPrice > 0 ? "Icons/coin" : "Icons/diamond", new Vector2(0, .5f), new Vector2(28, 28), new Vector2(22, 0));
            c.price = U.Label(priceRow.transform, "Value", K.Number, 18, "4A3624", TextAlignmentOptions.Right); U.Stretch(c.price.rectTransform, Vector2.zero, Vector2.one, new Vector2(40, 0), new Vector2(-12, 0));
            c.lockIcon = U.Icon(priceRow.transform, "Lock", "Icons/lock", new Vector2(0, .5f), new Vector2(26, 26), new Vector2(22, 0));
            c.stockBadge = U.Shape(face.transform, "Stock", "5DA637", 14, new Vector2(1, 1), new Vector2(64, 30), new Vector2(-40, -24)).gameObject;
            c.stock = U.Label(c.stockBadge.transform, "Value", K.Label, 16, "FFFFFF"); U.Stretch(c.stock.rectTransform, Vector2.zero, Vector2.one);
            var id = d.id;
            c.buy = U.Button(face.transform, "Comprar", "coin", () => Buy(id), 46, 17);
            U.Stretch((RectTransform)c.buy.transform, new Vector2(0, 0), new Vector2(.5f, 0), new Vector2(10, 14), new Vector2(-4, 60));
            c.place = U.Button(face.transform, "Colocar", "success", () => PlaceFromStock(id), 46, 17);
            U.Stretch((RectTransform)c.place.transform, new Vector2(.5f, 0), new Vector2(1, 0), new Vector2(4, 14), new Vector2(-10, 60));
            return c;
        }

        void RefreshShop()
        {
            var s = bridge.State; if (s?.decorCatalog == null) return;
            foreach (var d in s.decorCatalog)
            {
                if (!cards.TryGetValue(d.id, out var c)) cards[d.id] = c = MakeCard(d);
                string zone = string.IsNullOrEmpty(d.zone) ? "inside" : d.zone;
                c.go.SetActive(zone == shopZone);
                if (zone != shopZone) continue;
                bool levelOk = s.level >= d.requiredLevel, gems = d.coinPrice <= 0;
                int cost = gems ? d.diamondPrice : d.coinPrice;
                bool afford = gems ? s.diamonds >= cost : s.coins >= cost;
                int owned = Interior.Owned(d.id), free = owned - Interior.Placed(d.id);
                c.price.text = levelOk ? cost.ToString("N0", br) : "Nível " + d.requiredLevel;
                c.price.color = K.C(!levelOk ? "8A7560" : afford ? "4A3624" : "C0401F");
                c.priceIcon.gameObject.SetActive(levelOk); c.lockIcon.gameObject.SetActive(!levelOk);
                c.stockBadge.SetActive(owned > 0); c.stock.text = "x" + free;
                c.buy.Apply(Data("Comprar", gems ? "gem" : "coin", levelOk && afford && !bridge.HasPending("purchaseDecor")));
                c.place.Apply(Data("Colocar", "success", free > 0));
                c.icon.color = levelOk ? Color.white : new Color(1, 1, 1, .45f);
            }
            tabInside.Apply(Data("Dentro do mercado", "secondary", true, "Icons/shelf", shopZone == "inside"));
            tabOutside.Apply(Data("Fora do mercado", "secondary", true, "Icons/garden", shopZone == "outside"));
        }

        void ShowShopZone(string zone) { shopZone = zone; RefreshShop(); }

        // ------------------------------------------------------------------ enter / leave
        // The regular desktop HUD (level, wallet, toolbar) steps aside while building; the app hears about it too.
        readonly List<Canvas> hidden = new List<Canvas>();
        void GameHud(bool show)
        {
            if (!show)
            {
                hidden.Clear();
                var desktop = FindAnyObjectByType<CheckoutDesktopHUD>();
                // Only the HUD's own canvas: the mini-games and this build mode live on the same object.
                var own = desktop ? desktop.transform.Find("CheckoutDesktopHUD") : null;
                var canvas = own ? own.GetComponent<Canvas>() : null;
                if (canvas && canvas.enabled) { canvas.enabled = false; hidden.Add(canvas); }
            }
            else { foreach (var c in hidden) if (c) c.enabled = true; hidden.Clear(); }
            CheckoutBridge.Emit("{\"kind\":\"buildMode\",\"open\":" + (show ? "false" : "true") + "}");
        }

        void Enter()
        {
            if (Open || bridge.State == null || CheckoutMapEditor.Open) return;
            Open = true; Interior.editing = true; GameHud(false);
            backup = Interior.Export();
            waitingBefore = new Dictionary<string, (string type, string template)>(Interior.waiting);
            RefreshWaiting();
            buildButton.SetActive(false); hud.gameObject.SetActive(true); shopDim.SetActive(false);
            cameraBefore = simulation.CameraState;
            Focus("inside");
            Select(null);
            Say(HowTo);
        }

        void Focus(string zone)
        {
            shopZone = zone;
            if (zone == "inside") { var f = Interior.FloorRect; simulation.Focus(new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height) * .62f); }
            else { var r = CheckoutInterior.BlockRect; simulation.Focus(new Vector3(r.center.x, 0, r.center.y - 6), 30); }
            viewInside.Apply(Data("Dentro", "secondary", true, "Icons/shelf", zone == "inside"));
            viewOutside.Apply(Data("Fora", "secondary", true, "Icons/garden", zone == "outside"));
        }

        void Leave()
        {
            Open = false; Interior.editing = false; dragging = null; rotating = twisting = false; GameHud(true); CheckoutGridOverlay.Hide();
            simulation.cameraLocked = false; simulation.pinchLocked = false;
            hud.gameObject.SetActive(false); buildButton.SetActive(true); Select(null);
            simulation.Focus(cameraBefore.focus, cameraBefore.zoom);
        }

        void Finish()
        {
            if (!Interior.Reachable(out var blocked)) { Select(blocked); Say(Name(blocked) + " ficou sem passagem. Abra caminho para concluir.", true); return; }
            if (!Interior.items.Values.Any(i => i.root && i.type == "checkout" && !i.building) && Interior.waiting.Values.Any(w => w.type == "checkout"))
            { Say("Coloque o caixa na área dos caixas para concluir.", true); return; }
            bridge.Command("saveInteriorLayout", "[" + Interior.ExportJson() + "]");
            Interior.MarkPending();
            Leave();
            map.FurnitureChanged();
            CheckoutBlockPaths.Invalidate();
        }

        void Cancel()
        {
            // Put everything back as it was when build mode opened.
            foreach (var it in Interior.items.Values.ToArray())
                if (!it.functional && !it.design && backup.All(b => b.id != it.id)) Interior.RemoveDecor(it);
            // Furniture taken out of the inventory goes back into it; furniture stored meanwhile comes back.
            foreach (var id in waitingBefore.Keys) if (Interior.items.TryGetValue(id, out var placed)) Interior.Unplace(placed);
            foreach (var b in backup)
            {
                if (b.stored) continue;
                if (!Interior.items.TryGetValue(b.id, out var it)) it = CheckoutInterior.IsFunctional(b.type) ? Interior.RestoreWaiting(b) : Interior.RestoreDecor(b);
                if (it == null) continue;
                it.x = b.x; it.z = b.z; it.rot = b.rot; Interior.Place(it);
            }
            Leave();
            map.FurnitureChanged();
        }

        // ------------------------------------------------------------------ actions
        void Select(CheckoutInterior.Item it)
        {
            selected = it;
            selectionBar.gameObject.SetActive(it != null);
            simulation.pinchLocked = Open && it != null;
            if (it != null)
            {
                selectedName.text = Name(it);
                selectedZone.text = it.outside ? "Fora do mercado" : it.type == "checkout" || it.type == "kiosk" ? "Fica na área dos caixas" : it.functional ? "Móvel da loja" : "Decoração";
                selectedIcon.sprite = K.Icon("Decor/" + it.template);
                storeButton.gameObject.SetActive(!it.design);
            }
            ShowFootprint();
        }

        string Name(CheckoutInterior.Item it)
        {
            if (it == null) return "";
            if (it.type == "checkout") return it.id == "checkout:main" ? "Caixa" : "Caixa 2";
            if (it.type == "kiosk") return "Autoatendimento";
            if (it.type == "sector") { var s = bridge.State?.sectors?.FirstOrDefault(x => "sector:" + x.id == it.id); return s != null ? s.name : "Setor"; }
            if (it.type == "shelf") { var s = bridge.State?.shelves?.FirstOrDefault(x => "shelf:" + x.id == it.id); return s != null ? s.name : "Prateleira"; }
            var d = bridge.State?.decorCatalog?.FirstOrDefault(x => x.id == it.type);
            return d != null ? d.name : it.type;
        }

        void Rotate(float delta)
        {
            if (selected == null) { Say("Selecione um móvel primeiro.", true); return; }
            float before = selected.rot, next = Mathf.Repeat(before + delta, 360);
            var from = selected.root.position; var to = Interior.Snap(selected, from, next, from);
            if (!Interior.Fits(selected, to, next, out var why)) { Say(why + ": não dá para girar aqui.", true); return; }
            selected.rot = next; Interior.MoveTo(selected, to);
            if (!selected.outside && !Interior.Reachable(out var blocked)) { selected.rot = before; Interior.MoveTo(selected, from); Say("Assim " + Name(blocked) + " fica sem passagem.", true); }
            ShowFootprint(); map.FurnitureChanged(false);
        }

        void Store()
        {
            if (selected == null || selected.design) return;
            if (selected.functional)
            {
                if (bridge.State != null && bridge.State.isOpen) { Say("Feche a loja para guardar os móveis dela.", true); return; }
                if (selected.building) { Say("Espere a obra terminar para guardar.", true); return; }
                Interior.Unplace(selected); Select(null); RefreshWaiting(); map.FurnitureChanged(false);
                Say("Guardado em \"Para colocar\". A loja só abre com tudo no lugar.");
                return;
            }
            Interior.RemoveDecor(selected); Select(null); Say("Guardado. Está no estoque da loja para colocar de novo.");
        }

        // ------------------------------------------------------------------ furniture waiting to be placed
        string WaitingName(string id, string type)
        {
            if (type == "checkout") return id == "checkout:main" ? "Caixa" : "Caixa 2";
            if (type == "kiosk") return "Autoatendimento";
            if (type == "sector") { var s = bridge.State?.sectors?.FirstOrDefault(x => "sector:" + x.id == id); return s != null ? s.name : "Setor"; }
            var shelf = bridge.State?.shelves?.FirstOrDefault(x => "shelf:" + x.id == id); return shelf != null ? shelf.name : "Prateleira";
        }

        void RefreshWaiting()
        {
            if (!waitingPanel || Interior == null) return;
            foreach (var id in waitingButtons.Keys.Where(k => !Interior.waiting.ContainsKey(k)).ToList()) { if (waitingButtons[id]) Destroy(waitingButtons[id].gameObject); waitingButtons.Remove(id); }
            foreach (var w in Interior.waiting.OrderBy(w => w.Value.type == "checkout" || w.Value.type == "kiosk" ? 0 : 1).ThenBy(w => w.Key))
            {
                if (waitingButtons.ContainsKey(w.Key)) continue;
                string id = w.Key;
                var build = Interior.PendingBuild(id);
                string label = WaitingName(id, w.Value.type) + (build != null ? "  ·  obra " + CheckoutConstructionSite.Countdown(build.durationMs) : "");
                var b = U.Button(waitingPanel, label, "success", () => PlaceWaiting(id), 62, 19);
                b.Apply(Data(label, "success", true, "Decor/" + w.Value.template));
                waitingButtons[id] = b;
            }
            waitingPanel.gameObject.SetActive(Open && shopZone == "inside" && Interior.waiting.Count > 0);
        }

        void PlaceWaiting(string id)
        {
            if (!Interior.waiting.TryGetValue(id, out var w)) return;
            if (shopZone != "inside") Focus("inside");
            bool counter = w.type == "checkout" || w.type == "kiosk";
            var zone = Interior.CheckoutZone; var floor = Interior.FloorRect;
            // Counters start in the checkout area, everything else in the free part of the shop in view.
            var ray = simulation.view.ScreenPointToRay(new Vector3(Screen.width * .5f, Screen.height * .5f));
            var at = new Plane(Vector3.up, new Vector3(0, CheckoutInterior.Floor, 0)).Raycast(ray, out var dist) ? ray.GetPoint(dist) : new Vector3(floor.center.x, CheckoutInterior.Floor, floor.center.y);
            at.x = Mathf.Clamp(at.x, floor.xMin + 1.5f, floor.xMax - 1.5f);
            at.z = counter ? zone.center.y : Mathf.Clamp(at.z, zone.yMax + 1.8f, floor.yMax - 1.8f);
            var it = Interior.PlaceWaiting(id, at);
            if (it == null) { Say("Não há espaço livre para isso agora. Afaste algum móvel.", true); return; }
            RefreshWaiting(); Select(it); map.FurnitureChanged(false);
            Say(counter ? "O caixa fica na área dos caixas, perto da entrada. Arraste para ajustar." : "Arraste para o lugar que quiser.");
        }

        void ToggleShop(bool? open = null)
        {
            bool on = open ?? !shopDim.activeSelf;
            shopDim.SetActive(on); if (on) RefreshShop();
        }

        void Buy(string id)
        {
            var d = bridge.State?.decorCatalog?.FirstOrDefault(x => x.id == id); if (d == null) return;
            bool gems = d.coinPrice <= 0 || (bridge.State.coins < d.coinPrice && d.diamondPrice > 0 && bridge.State.diamonds >= d.diamondPrice);
            bridge.Command("purchaseDecor", "[\"" + id + "\",\"" + (gems ? "diamonds" : "coins") + "\"]");
            Say("Comprado! Toque em Colocar para pôr no lugar.");
        }

        void PlaceFromStock(string id)
        {
            if (Interior.Owned(id) - Interior.Placed(id) <= 0) return;
            var d = bridge.State?.decorCatalog?.FirstOrDefault(x => x.id == id);
            bool outside = d != null && d.zone == "outside";
            if ((outside ? "outside" : "inside") != shopZone) Focus(outside ? "outside" : "inside");
            var ray = simulation.view.ScreenPointToRay(new Vector3(Screen.width * .5f, Screen.height * .5f));
            var plane = new Plane(Vector3.up, new Vector3(0, outside ? CheckoutInterior.Ground : CheckoutInterior.Floor, 0));
            var at = plane.Raycast(ray, out var dist) ? ray.GetPoint(dist) : Interior.EntrancePoint;
            var r = outside ? CheckoutInterior.BlockRect : Interior.FloorRect;
            at.x = Mathf.Clamp(at.x, r.xMin + 1, r.xMax - 1); at.z = Mathf.Clamp(at.z, r.yMin + 1.5f, r.yMax - 1);
            var it = Interior.AddDecor(id, at, outside);
            if (it == null) { Say("Não há espaço livre para isso agora.", true); return; }
            ToggleShop(false); Select(it); Say("Arraste para ajustar o lugar.");
        }

        void Say(string text, bool warn = false)
        {
            if (!status) return;
            status.text = text; status.color = K.C(warn ? "C0401F" : "8A7560"); messageUntil = Time.unscaledTime + (warn ? 3.5f : 6f);
        }

        // ------------------------------------------------------------------ rotation (Ctrl + mouse, two-finger twist)
        static float SnapAngle(float a)
        {
            a = Mathf.Repeat(a, 360);
            float right = Mathf.Round(a / 45) * 45;
            return Mathf.Abs(Mathf.DeltaAngle(a, right)) < 6 ? Mathf.Repeat(right, 360) : Mathf.Repeat(Mathf.Round(a / 5) * 5, 360);
        }

        void BeginRotate() { rotating = true; rotStart = selected.rot; rotAccum = 0; rotStartPosition = selected.root.position; simulation.cameraLocked = true; }

        void ApplyRotate()
        {
            selected.rot = SnapAngle(rotStart + rotAccum);
            var p = Interior.Snap(selected, rotStartPosition, selected.rot, rotStartPosition);
            Interior.MoveTo(selected, p);
            ShowFootprint();
        }

        void EndRotate()
        {
            rotating = false; twisting = false; simulation.cameraLocked = false;
            if (selected == null) return;
            if (!Interior.Fits(selected, selected.root.position, selected.rot, out var why)) { selected.rot = rotStart; Interior.MoveTo(selected, rotStartPosition); Say(why + ": voltou como estava.", true); }
            else if (!selected.outside && !Interior.Reachable(out var blocked)) { selected.rot = rotStart; Interior.MoveTo(selected, rotStartPosition); Say("Assim " + Name(blocked) + " fica sem passagem.", true); }
            ShowFootprint(); map.FurnitureChanged(false);
        }

        // ------------------------------------------------------------------ pointer
        void Update()
        {
            // The map editor has its own tools: no build button while it is open.
            bool hidden = Open || CheckoutMapEditor.Open || CheckoutDesktopHUD.ShopOpen || (CheckoutStall.Small && !CheckoutStall.ShopInside);
            if (buildButton && !CheckoutStartMenu.Showing && buildButton.activeSelf == hidden) buildButton.SetActive(!hidden);
            if (buildButton && CheckoutStartMenu.Showing && buildButton.activeSelf) buildButton.SetActive(false);
            // Furniture waiting to be placed shows on the button (a new shop starts empty).
            // Bought pieces show as a red counter (the inventory); the starter pieces of a new shop as "Montar loja".
            int count = Interior ? Interior.waiting.Count : 0;
            int bought = Interior ? Interior.waiting.Keys.Count(id => Interior.PendingBuild(id) != null) : 0;
            if (buildButtonView && count * 100 + bought != buildButtonCount)
            {
                buildButtonCount = count * 100 + bought;
                bool starter = count > bought;
                buildButtonView.Apply(Data(starter ? "Montar loja" : bought > 0 ? "Colocar" : "Construir", count > 0 ? "success" : "primary", true, "Icons/hammer"));
                if (inventoryBadge) { inventoryBadge.SetActive(count > 0); inventoryBadgeText.text = count.ToString(); }
            }
            // A gentle pulse so the player notices there is something to place.
            if (inventoryBadge && inventoryBadge.activeSelf) inventoryBadge.transform.localScale = Vector3.one * (1 + Mathf.Abs(Mathf.Sin(Time.unscaledTime * 3)) * .12f);
            if (!Open) return;
            refresh -= Time.unscaledDeltaTime;
            if (refresh <= 0)
            {
                refresh = .5f; var s = bridge.State;
                if (s != null)
                {
                    coins.text = shopCoins.text = ((long)s.coins).ToString("N0", br);
                    diamonds.text = shopDiamonds.text = ((long)s.diamonds).ToString("N0", br);
                }
                if (shopDim.activeSelf) RefreshShop();
                RefreshWaiting();
                if (Time.unscaledTime > messageUntil) Say(HowTo);
            }
            if (Input.GetKeyDown(KeyCode.G)) { CheckoutInterior.GridOn = !CheckoutInterior.GridOn; Say(CheckoutInterior.GridOn ? "Grade ligada: as peças encaixam nos quadrados." : "Grade desligada: movimento livre (ainda encosta nas paredes e nos móveis)."); }
            ShowGrid();
            if (Input.GetKeyDown(KeyCode.Delete)) Store();
            if (Input.GetKeyDown(KeyCode.Escape)) { if (shopDim.activeSelf) ToggleShop(false); else Cancel(); return; }
            if (shopDim.activeSelf) return;

            // Two fingers on a selected piece turn it (the camera does not zoom meanwhile).
            if (Input.touchCount == 2 && selected != null)
            {
                if (dragging != null) Drop();
                var a = Input.GetTouch(0).position; var b = Input.GetTouch(1).position;
                float angle = Mathf.Atan2(b.y - a.y, b.x - a.x) * Mathf.Rad2Deg;
                if (!twisting) { BeginRotate(); twisting = true; lastTwist = angle; }
                else { rotAccum -= Mathf.DeltaAngle(lastTwist, angle); lastTwist = angle; ApplyRotate(); }
                return;
            }
            if (twisting && Input.touchCount < 2) { EndRotate(); pressOnItem = false; return; }

            // Ctrl + mouse movement turns the selected piece.
            bool ctrl = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl) || Input.GetKey(KeyCode.LeftCommand);
            Vector2 mouse = Input.mousePosition;
            if (ctrl && selected != null && !Touch)
            {
                if (dragging != null) Drop();
                if (!rotating) { BeginRotate(); lastMouse = mouse; }
                rotAccum += (mouse.x - lastMouse.x) * .6f; lastMouse = mouse;
                ApplyRotate();
                return;
            }
            if (rotating) EndRotate();

            bool overUi = EventSystem.current && (Input.touchCount > 0 ? EventSystem.current.IsPointerOverGameObject(Input.GetTouch(0).fingerId) : EventSystem.current.IsPointerOverGameObject());
            var ray = simulation.view.ScreenPointToRay(mouse);
            if (Input.GetMouseButtonDown(0) && !overUi && Input.touchCount < 2)
            {
                pointerDown = mouse; pointerMoved = false;
                var hit = Interior.Pick(ray); pressOnItem = hit != null;
                if (hit != null && PlaneOf(hit).Raycast(ray, out var d))
                {
                    dragging = hit; dragOffset = hit.root.position - ray.GetPoint(d); dragStartPosition = hit.root.position; dragStartRot = hit.rot;
                    simulation.cameraLocked = true; Select(hit);
                }
            }
            if (dragging != null && Input.GetMouseButton(0))
            {
                if ((mouse - pointerDown).magnitude > 8) pointerMoved = true;
                if (pointerMoved && PlaneOf(dragging).Raycast(ray, out var d))
                {
                    var p = ray.GetPoint(d) + dragOffset;
                    var here = dragging.root.position; here.y = p.y;
                    // Grid squares, flush against walls and neighbours, never inside another piece.
                    p = Interior.Snap(dragging, p, dragging.rot, here);
                    Interior.MoveTo(dragging, p);
                    dragging.root.position += Vector3.up * .06f;
                    ShowFootprint();
                }
            }
            if (Input.GetMouseButtonUp(0))
            {
                if (dragging != null) Drop();
                else if (!pressOnItem && !overUi && (mouse - pointerDown).magnitude < 8) Select(null);
                pressOnItem = false;
            }
        }

        void ShowGrid()
        {
            if (!CheckoutInterior.GridOn) { CheckoutGridOverlay.Hide(); return; }
            if (shopZone == "inside") CheckoutGridOverlay.Show(Interior.FloorRect, CheckoutInterior.Floor + .012f, CheckoutInterior.GridSize, new Color(1, 1, 1, .42f));
            else CheckoutGridOverlay.Show(CheckoutInterior.BlockRect, CheckoutInterior.Ground + .03f, CheckoutInterior.GridSize * 2, new Color(1, 1, 1, .18f));
        }

        Plane PlaneOf(CheckoutInterior.Item it) => new Plane(Vector3.up, new Vector3(0, it.outside ? CheckoutInterior.Ground : CheckoutInterior.Floor, 0));

        void Drop()
        {
            var it = dragging; dragging = null; simulation.cameraLocked = false;
            Interior.Place(it);
            if (pointerMoved)
            {
                if (!Interior.Fits(it, it.root.position, it.rot, out var why)) { Interior.MoveTo(it, dragStartPosition); Say(why + ". Voltou para o lugar anterior.", true); }
                else if (!it.outside && !Interior.Reachable(out var blocked)) { Interior.MoveTo(it, dragStartPosition); Say("Assim " + Name(blocked) + " fica sem passagem.", true); }
            }
            pointerMoved = false;
            ShowFootprint();
            map.FurnitureChanged(false);
        }

        void ShowFootprint()
        {
            foreach (var s in spots) if (s) s.gameObject.SetActive(false);
            if (selected == null || !selected.root) { footprint.gameObject.SetActive(false); return; }
            float y = selected.outside ? CheckoutInterior.Ground : CheckoutInterior.Floor;
            var position = selected.root.position; position.y = y;
            bool ok = Interior.Fits(selected, position, selected.rot, out var why);
            if (!ok && (dragging != null || rotating)) Say(why, true);
            var f = Interior.FootprintAt(selected, position, selected.rot);
            footprint.gameObject.SetActive(true);
            footprint.GetComponent<Renderer>().sharedMaterial = ok ? okMaterial : badMaterial;
            footprint.SetPositionAndRotation(new Vector3(f.c.x, y + .05f, f.c.y), Quaternion.Euler(90, selected.rot, 0));
            footprint.localScale = new Vector3(f.hx * 2 + .1f, f.hz * 2 + .1f, 1);
            int n = 0;
            foreach (var p in Interior.ServicePoints(selected, position, selected.rot))
            {
                if (spots.Count <= n) spots.Add(Quad("Build spot", spotMaterial).transform);
                var s = spots[n++]; s.gameObject.SetActive(true);
                s.SetPositionAndRotation(new Vector3(p.x, y + .06f, p.z), Quaternion.Euler(90, 45, 0)); s.localScale = Vector3.one * .28f;
            }
        }

        void OnDestroy() { Open = false; }
    }
}
