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
    public partial class CheckoutBuildMode : MonoBehaviour
    {
        public static bool Open { get; private set; }
        CheckoutBridge bridge; CheckoutMap map; MarketSimulation simulation;
        RectTransform root, hud; GameObject buildButton;
        CheckoutDesktopButton buildButtonView; int buildButtonCount = -1; GameObject inventoryBadge; TMPro.TextMeshProUGUI inventoryBadgeText;
        Dictionary<string, (string type, string template)> waitingBefore = new Dictionary<string, (string type, string template)>();
        TextMeshProUGUI status, coins, diamonds;
        Image selectedIcon;
        CheckoutDesktopButton storeButton;
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
        // The game is played mostly on phones (Lucas 20/10: "no celular não tem Ctrl, não tem G"): the hint talks about
        // fingers and the on-screen buttons; the keys (Ctrl + mouse, G, Delete, Esc) are only quiet extras on a computer.
        static string HowTo => CheckoutScreen.Handheld ? "Arraste as peças para mover  •  Gire com dois dedos ou nas setas" : "Arraste as peças para mover  •  Gire nas setas ou com Ctrl + mouse";

        public void Initialize(CheckoutBridge owner, CheckoutMap projection)
        {
            bridge = owner; map = projection; simulation = FindAnyObjectByType<MarketSimulation>(); instance = this;
            if (!Interior || !Interior.Ready) { enabled = false; return; }
            root = U.Canvas(transform, "CheckoutBuildMode", 60);
            // Lucas 24/10: just the hammer (the big "Montar loja" button was too much). A square key in the bottom-left
            // corner, level with the toolbar (same height, same row), with the red counter of pieces to place.
            float size = CheckoutScreen.Handheld ? 92 : 84, toolbarMid = CheckoutScreen.Handheld ? 6 + 50 : 14 + 52;
            var b = CheckoutDesktopButton.Create(root, size, 16, 22);
            b.Apply(Data("", "primary", true, "Icons/hammer"));
            b.Clicked = _ => Enter();
            var iconSize = b.transform.Find("Face/Icon")?.GetComponent<UnityEngine.UI.LayoutElement>();
            if (iconSize) iconSize.preferredWidth = iconSize.preferredHeight = Mathf.Round(size * .62f);
            U.At((RectTransform)b.transform, new Vector2(0, 0), new Vector2(size, size), new Vector2(16 + size * .5f, toolbarMid));
            buildButton = b.gameObject; buildButtonView = b;
            // Red counter in the corner: bought furniture waiting in the inventory for a spot.
            var pill = CheckoutDesktopCard.Image(b.transform, "Inventory badge", K.C("E15533"), 16);
            var pr = pill.rectTransform; pr.anchorMin = pr.anchorMax = pr.pivot = Vector2.one; pr.anchoredPosition = new Vector2(12, 12); pr.sizeDelta = new Vector2(34, 34);
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

        // The HUD itself (top bar, tray, sheet, selection) is in CheckoutBuildMode.Tray.cs.
        static RectTransform Node(Transform parent, string name) { var t = (RectTransform)new GameObject(name, typeof(RectTransform)).transform; t.SetParent(parent, false); return t; }

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
                // The stockroom buttons (ENTREGA, REPOR…) sit on their own canvas, over this one: they step aside too.
                var stock = FindAnyObjectByType<CheckoutStockroom>();
                var stockCanvas = stock ? stock.transform.Find("CheckoutStockroom")?.GetComponent<Canvas>() : null;
                if (stockCanvas && stockCanvas.enabled) { stockCanvas.enabled = false; hidden.Add(stockCanvas); }
            }
            else { foreach (var c in hidden) if (c) c.enabled = true; hidden.Clear(); }
            CheckoutBridge.Emit("{\"kind\":\"buildMode\",\"open\":" + (show ? "false" : "true") + "}");
        }

        // picked: the piece a long press lifted in the game; the camera stays where it is and the piece follows the finger.
        void Enter() => Enter(null);
        void Enter(CheckoutInterior.Item picked)
        {
            if (Open || bridge.State == null || CheckoutMapEditor.Open) return;
            Open = true; Interior.editing = true; GameHud(false);
            backup = Interior.Export();
            waitingBefore = new Dictionary<string, (string type, string template)>(Interior.waiting);
            tabChosen = false; folded = false; tray.sizeDelta = new Vector2(tray.sizeDelta.x, TrayH); placeAfterBuy = null;
            buildButton.SetActive(false); hud.gameObject.SetActive(true); CloseSheet();
            cameraBefore = simulation.CameraState;
            if (picked == null) { Focus("inside"); Select(null); }
            else
            {
                // Lifted with a long press: the tray starts folded so the shop around the finger stays in view.
                Focus(picked.outside ? "outside" : "inside", false); Select(picked);
                folded = true; tray.sizeDelta = new Vector2(tray.sizeDelta.x, TrayHeadH + 10);
            }
            RefreshTray();
            Say(HowTo);
        }

        void Focus(string zone) => Focus(zone, true);
        void Focus(string zone, bool moveCamera)
        {
            shopZone = zone;
            if (!moveCamera) { }
            else if (zone == "inside") { var f = Interior.FloorRect; simulation.Focus(new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height) * .62f); }
            else { var r = CheckoutInterior.BlockRect; simulation.Focus(new Vector3(r.center.x, 0, r.center.y - 6), 30); }
            // The tray follows: its decorations are the ones for this side of the door.
            if (Open) { CloseSheet(); RefreshTray(); }
        }

        void Leave()
        {
            Open = false; Interior.editing = false; dragging = null; rotating = twisting = false; GameHud(true); CheckoutGridOverlay.Hide();
            SeeAll(); CloseSheet(); placeAfterBuy = null;
            simulation.cameraLocked = false; simulation.pinchLocked = false;
            hud.gameObject.SetActive(false); buildButton.SetActive(true); Select(null);
            simulation.Focus(cameraBefore.focus, cameraBefore.zoom);
        }

        void Finish()
        {
            var misplaced = Interior.items.Values.FirstOrDefault(i => i.root && !i.design && !i.ghost && !Interior.Fits(i, i.root.position, i.rot, out _));
            if (misplaced != null) { Select(misplaced); Say(Name(misplaced) + " não cabe aí. Mova ou gire até a área ficar verde.", true); return; }
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
            simulation.pinchLocked = Open && it != null;
            ShowSelection(it);
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

        // Turning is always allowed: the footprint turns red where the turned piece does not fit (or blocks a
        // passage), and "Concluir" waits until every piece is green again.
        void Rotate(float delta)
        {
            if (selected == null) { Say("Selecione um móvel primeiro.", true); return; }
            float next = Mathf.Repeat(selected.rot + delta, 360);
            var from = selected.root.position;
            selected.rot = next; Interior.MoveTo(selected, Interior.Snap(selected, from, next, from));
            ShowFootprint(); map.FurnitureChanged(false);
        }

        void Store()
        {
            if (selected == null || selected.design) return;
            if (selected.functional)
            {
                if (bridge.State != null && bridge.State.isOpen) { Say("Feche a loja para guardar os móveis dela.", true); return; }
                if (selected.building) { Say("Espere a obra terminar para guardar.", true); return; }
                Interior.Unplace(selected); Select(null); ShowTab("guardados", false); map.FurnitureChanged(false);
                Say("Guardado em Guardados. A loja só abre com tudo no lugar.");
                return;
            }
            Interior.RemoveDecor(selected); Select(null); ShowTab("guardados", false); Say("Guardado. Está em Guardados para colocar de novo.");
        }

        // ------------------------------------------------------------------ furniture waiting to be placed
        string WaitingName(string id, string type)
        {
            if (type == "checkout") return id == "checkout:main" ? "Caixa" : "Caixa 2";
            if (type == "kiosk") return "Autoatendimento";
            if (type == "sector") { var s = bridge.State?.sectors?.FirstOrDefault(x => "sector:" + x.id == id); return s != null ? s.name : "Setor"; }
            var shelf = bridge.State?.shelves?.FirstOrDefault(x => "shelf:" + x.id == id); return shelf != null ? shelf.name : "Prateleira";
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
            at.x = counter ? zone.center.x : Mathf.Clamp(at.x, floor.xMin + 1.8f, Mathf.Max(floor.xMin + 1.8f, zone.xMin - 1.8f));
            at.z = Mathf.Clamp(at.z, floor.yMin + 1.5f, floor.yMax - 1.5f);
            var it = Interior.PlaceWaiting(id, at);
            if (it == null) { Say("Não há espaço livre para isso agora. Afaste algum móvel.", true); return; }
            RefreshTray(); Select(it); map.FurnitureChanged(false);
            Say(counter ? "O caixa fica na área dos caixas, junto à parede do estacionamento. Arraste para ajustar." : "Arraste para o lugar que quiser.");
        }

        void PlaceFromStock(string id)
        {
            if (Interior.Owned(id) - Interior.Placed(id) <= 0) return;
            var d = bridge.State?.decorCatalog?.FirstOrDefault(x => x.id == id);
            bool outside = d != null && (d.zone == "outside" || (d.zone == "both" && shopZone == "outside"));
            if ((outside ? "outside" : "inside") != shopZone) Focus(outside ? "outside" : "inside");
            var ray = simulation.view.ScreenPointToRay(new Vector3(Screen.width * .5f, Screen.height * .5f));
            var plane = new Plane(Vector3.up, new Vector3(0, outside ? CheckoutInterior.Ground : CheckoutInterior.Floor, 0));
            var at = plane.Raycast(ray, out var dist) ? ray.GetPoint(dist) : Interior.EntrancePoint;
            var r = outside ? CheckoutInterior.BlockRect : Interior.FloorRect;
            at.x = Mathf.Clamp(at.x, r.xMin + 1, r.xMax - 1); at.z = Mathf.Clamp(at.z, r.yMin + 1.5f, r.yMax - 1);
            var it = Interior.AddDecor(id, at, outside);
            if (it == null) { Say("Não há espaço livre para isso agora.", true); return; }
            MarkSeen(id); RefreshTray(); Select(it); map.FurnitureChanged(false); Say("Arraste para ajustar o lugar.");
        }

        void Say(string text, bool warn = false)
        {
            if (!status) return;
            // White on the navy hint pill; warnings in light red.
            status.text = text; status.color = K.C(warn ? "FFA48C" : "FFFFFF"); messageUntil = Time.unscaledTime + (warn ? 3.5f : 6f);
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
            // The turn stays; a red footprint shows it does not fit there yet.
            ShowFootprint(); map.FurnitureChanged(false);
        }

        // ------------------------------------------------------------------ pointer
        void Update()
        {
            // The map editor has its own tools: no build button while it is open.
            // At the stalls (CheckoutStall.Yard) only once there is something of the player's to place around it.
            bool hidden = Open || CheckoutMapEditor.Open || CheckoutDesktopHUD.ShopOpen
                || (CheckoutStall.Yard && (!Interior || (Interior.waiting.Count == 0 && !Interior.items.Values.Any(i => !i.design))));
            if (buildButton && !CheckoutStartMenu.Showing && buildButton.activeSelf == hidden) buildButton.SetActive(!hidden);
            if (buildButton && CheckoutStartMenu.Showing && buildButton.activeSelf) buildButton.SetActive(false);
            // Furniture waiting to be placed shows on the button (a new shop starts empty).
            // Pieces waiting in the inventory (the starter pieces of a new shop, bought ones) show as a red counter.
            int count = Interior ? Interior.waiting.Count : 0;
            int bought = Interior ? Interior.waiting.Keys.Count(id => Interior.PendingBuild(id) != null) : 0;
            if (buildButtonView && count * 100 + bought != buildButtonCount)
            {
                buildButtonCount = count * 100 + bought;
                // Icon only: green with the red counter while something waits to be placed.
                buildButtonView.Apply(Data("", count > 0 ? "success" : "primary", true, "Icons/hammer"));
                if (inventoryBadge) { inventoryBadge.SetActive(count > 0); inventoryBadgeText.text = count.ToString(); }
            }
            // A gentle pulse so the player notices there is something to place.
            if (inventoryBadge && inventoryBadge.activeSelf) inventoryBadge.transform.localScale = Vector3.one * (1 + Mathf.Abs(Mathf.Sin(Time.unscaledTime * 3)) * .12f);
            HoldToMove();
            if (!Open) return;
            refresh -= Time.unscaledDeltaTime;
            if (refresh <= 0)
            {
                refresh = .5f; var s = bridge.State;
                if (s != null)
                {
                    coins.text = ((long)s.coins).ToString("N0", br);
                    diamonds.text = ((long)s.diamonds).ToString("N0", br);
                }
                RefreshTray();
                if (Time.unscaledTime > messageUntil) Say(HowTo);
            }
            if (Input.GetKeyDown(KeyCode.G)) ToggleGrid();
            ShowGrid();
            if (Input.GetKeyDown(KeyCode.Delete)) Store();
            if (Input.GetKeyDown(KeyCode.Escape)) { if (sheetFor != null) CloseSheet(); else Cancel(); return; }
            PlaceBought();

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

            bool overUi = CheckoutPointer.OverUiNow();
            var ray = simulation.view.ScreenPointToRay(mouse);
            if (Input.GetMouseButtonDown(0) && !overUi && Input.touchCount < 2)
            {
                pointerDown = mouse; pointerMoved = false; CloseSheet();
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
            // A blocked passage is checked once the piece is let go (it walks the whole floor).
            if (ok && !selected.outside && dragging == null && !rotating && !Interior.Reachable(out var blocked))
            { ok = false; why = "Assim " + Name(blocked) + " fica sem passagem"; }
            if (!ok) Say(why, true);
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

        // The selection bar follows its piece (after this frame's drag and camera moves).
        void LateUpdate() { if (Open) PlaceFloatBar(); }

        void OnDestroy() { Open = false; }
    }
}
