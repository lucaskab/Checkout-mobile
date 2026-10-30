using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout
{
    // Build-mode HUD, redesigned 20/10 (Lucas: "o inventário de coisas para colocar está patético"). Modelled on the
    // decoration trays of Hay Day (edit storage works like the deco shop), The Sims FreePlay (one catalog for owned and
    // for sale, tap a card to place), June's Journey (stored copies share one slot with a count) and Township (actions
    // float over the selected piece):
    //  - top bar: Dentro / Fora (moves the camera), the hint, the wallet, Cancelar and Concluir;
    //  - bottom tray: tabs Guardados (what is bought and not placed: shop furniture and decorations) · Decoração ·
    //    Melhorias, and a strip of item cards. An owned card places the piece where the camera looks at one tap and
    //    the tray stays open, so several pieces go down in a row. A card for sale opens a small sheet above it with the
    //    description and the price buttons; buying places the piece as soon as the purchase lands. The chevron folds
    //    the tray down to its tabs to see more of the shop;
    //  - over the selected piece: its name, turn left / right and Guardar.
    public partial class CheckoutBuildMode
    {
        static bool Phone => CheckoutScreen.Handheld;
        static float TrayH => Phone ? 228 : 276;
        static float TrayHeadH => Phone ? 46 : 58;
        static float CardW => Phone ? 132 : 158;

        RectTransform tray, trayStrip, trayList, sheet, floatBar, sheetButtons;
        TextMeshProUGUI emptyNote, floatName, sheetTitle, sheetZone, sheetBody;
        Image sheetIcon; GameObject sheetUpgrade;
        CheckoutDesktopButton zoneInside, zoneOutside, foldButton, rotateLeft, rotateRight, gridButton;
        readonly Dictionary<string, (CheckoutDesktopButton button, GameObject badge, TextMeshProUGUI count)> tabs = new Dictionary<string, (CheckoutDesktopButton, GameObject, TextMeshProUGUI)>();
        readonly List<CheckoutBuildCard> cardPool = new List<CheckoutBuildCard>();
        readonly List<CheckoutDesktopButton> sheetPool = new List<CheckoutDesktopButton>();
        string tab = "", sheetFor; bool folded, tabChosen; float floatHeight; Coroutine foldMove;
        // A decoration just bought from its sheet: it goes into the shop as soon as the purchase shows up.
        string placeAfterBuy; float placeAfterBuyUntil;

        // ------------------------------------------------------------------ build
        void BuildHud()
        {
            hud = Node(root, "Build HUD"); U.Stretch(hud, Vector2.zero, Vector2.one);
            BuildTopBar();
            BuildTray();
            BuildSheet();
            BuildFloatBar();
            hud.gameObject.SetActive(false);
        }

        void BuildTopBar()
        {
            float h = Phone ? 58 : 66, pad = Phone ? 10 : 16;
            var bar = Node(hud, "Top bar"); bar.anchorMin = new Vector2(0, 1); bar.anchorMax = Vector2.one; bar.pivot = new Vector2(.5f, 1);
            bar.sizeDelta = new Vector2(-pad * 2, h); bar.anchoredPosition = new Vector2(0, -(Phone ? 8 : 14));
            var row = N.Row(bar.gameObject, Phone ? 8 : 12); row.childForceExpandHeight = true; row.childControlHeight = true;

            // Dentro | Fora: one segmented pill.
            var seg = N.Image(bar, "Zones", K.Border, 22); var segFace = N.Image(seg.transform, "Face", K.Cream, 20); U.Stretch(segFace.rectTransform, Vector2.zero, Vector2.one, new Vector2(2, 4), new Vector2(-2, -2));
            var segRow = N.Row(segFace.gameObject, 4, new RectOffset(5, 5, 4, 4)); segRow.childForceExpandHeight = true;
            var segLayout = seg.gameObject.AddComponent<LayoutElement>(); segLayout.preferredWidth = Phone ? 300 : 360;
            zoneInside = U.Button(segFace.transform, "Dentro", "secondary", () => Focus("inside"), h - 14, Phone ? 17 : 19);
            zoneOutside = U.Button(segFace.transform, "Fora", "secondary", () => Focus("outside"), h - 14, Phone ? 17 : 19);

            // The hint: what to do now, or what is wrong (in red).
            var hint = N.Image(bar, "Hint", new Color(.11f, .17f, .31f, .86f), 22);
            hint.gameObject.AddComponent<LayoutElement>().flexibleWidth = 1;
            U.Icon(hint.transform, "Hammer", "Icons/hammer", new Vector2(0, .5f), new Vector2(h - 18, h - 18), new Vector2(h * .5f + 4, 0));
            status = U.Label(hint.transform, "Status", K.Body, Phone ? 15 : 17, "FFFFFF", TextAlignmentOptions.Left);
            status.textWrappingMode = TextWrappingModes.Normal; status.overflowMode = TextOverflowModes.Ellipsis; status.maxVisibleLines = 2;
            U.Stretch(status.rectTransform, Vector2.zero, Vector2.one, new Vector2(h + 6, 4), new Vector2(-14, -4));

            coins = WalletPill(bar, "Icons/coin"); diamonds = WalletPill(bar, "Icons/diamond");
            U.Button(bar, "Cancelar", "secondary", Cancel, h, Phone ? 17 : 19).SetWidth(Phone ? 118 : 140);
            var done = U.Button(bar, "Concluir", "success", Finish, h, Phone ? 19 : 22); done.Apply(Data("Concluir", "success", true, "Icons/success")); done.SetWidth(Phone ? 158 : 190);
        }

        static TextMeshProUGUI WalletPill(RectTransform parent, string icon)
        {
            var pill = N.Image(parent, "Wallet", K.Cream, 22);
            var le = pill.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = Phone ? 128 : 160;
            var edge = pill.gameObject.AddComponent<Outline>(); edge.effectColor = K.Border; edge.effectDistance = new Vector2(2, -2);
            float s = Phone ? 30 : 36;
            U.Icon(pill.transform, "Icon", icon, new Vector2(0, .5f), new Vector2(s, s), new Vector2(s * .5f + 8, 0));
            var t = U.Label(pill.transform, "Value", K.Number, Phone ? 17 : 20, "4A3624", TextAlignmentOptions.Right);
            U.Stretch(t.rectTransform, Vector2.zero, Vector2.one, new Vector2(s + 12, 0), new Vector2(-12, 0));
            return t;
        }

        // The picker opens over the build mode (what was placed stays as it is): the build HUD steps aside meanwhile.
        void OpenPaint()
        {
            CloseSheet(); Select(null);
            hud.gameObject.SetActive(false);
            CheckoutMarketPaintPanel.Show(() => { if (Open) { hud.gameObject.SetActive(true); Focus(shopZone); } });
            if (!CheckoutMarketPaintPanel.Open) hud.gameObject.SetActive(true);
        }

        void BuildTray()
        {
            float pad = Phone ? 10 : 16;
            var edge = N.Image(hud, "Tray", K.Border, 26); tray = edge.rectTransform;
            tray.anchorMin = Vector2.zero; tray.anchorMax = new Vector2(1, 0); tray.pivot = new Vector2(.5f, 0);
            tray.sizeDelta = new Vector2(-pad * 2, TrayH); tray.anchoredPosition = new Vector2(0, Phone ? 6 : 12);
            edge.raycastTarget = true; // taps on the tray never reach the shop floor
            var face = N.Image(tray, "Face", K.Cream, 24); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 6), new Vector2(-3, -3));

            // Header: tabs on the left, the fold chevron on the right.
            var head = Node(face.transform, "Tabs"); U.Stretch(head, new Vector2(0, 1), Vector2.one, new Vector2(10, -TrayHeadH), new Vector2(-10, -6));
            var hr = N.Row(head.gameObject, Phone ? 6 : 8); hr.childForceExpandHeight = true;
            Tab(head, "guardados", "Guardados", "Icons/package");
            Tab(head, "decoracao", "Decoração", "Icons/plant");
            Tab(head, "melhorias", "Melhorias", "Icons/lightning");
            var spacer = Node(head, "Spacer"); spacer.gameObject.AddComponent<LayoutElement>().flexibleWidth = 1;
            // The floor grid: on, pieces snap to its squares (G on a keyboard does the same).
            // "Cores do mercado": the picker over the live market (the build mode closes first, keeping what was placed).
            var paintButton = U.Button(head, "Cores", "secondary", OpenPaint, TrayHeadH - 10, Phone ? 16 : 18); paintButton.SetWidth(Phone ? 130 : 150);
            paintButton.Apply(Data("Cores", "secondary", true, "Icons/paint"));
            gridButton = U.Button(head, "Grade", "secondary", ToggleGrid, TrayHeadH - 10, Phone ? 16 : 18); gridButton.SetWidth(Phone ? 130 : 150);
            foldButton = U.Button(head, "", "primary", () => Fold(!folded), TrayHeadH - 10, 16); foldButton.SetWidth(TrayHeadH + 8); BigIcon(foldButton, (TrayHeadH - 10) * .7f);

            // The strip of cards (scrolls sideways; the mouse wheel scrolls it too).
            var shelf = N.Image(face.transform, "Strip", K.Paper, 18); trayStrip = shelf.rectTransform;
            U.Stretch(trayStrip, Vector2.zero, Vector2.one, new Vector2(10, 10), new Vector2(-10, -TrayHeadH - 4));
            var view = Node(trayStrip, "Viewport"); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(6, 4), new Vector2(-6, -4));
            view.gameObject.AddComponent<RectMask2D>(); var hit = view.gameObject.AddComponent<Image>(); hit.color = new Color(1, 1, 1, 0);
            trayList = Node(view, "Cards"); trayList.anchorMin = Vector2.zero; trayList.anchorMax = new Vector2(0, 1); trayList.pivot = new Vector2(0, .5f); trayList.offsetMin = trayList.offsetMax = Vector2.zero;
            var lr = N.Row(trayList.gameObject, Phone ? 10 : 12, new RectOffset(4, 16, 6, 6)); lr.childForceExpandHeight = true; lr.childControlHeight = true;
            trayList.gameObject.AddComponent<ContentSizeFitter>().horizontalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = trayList; scroll.vertical = false; scroll.horizontal = true; scroll.viewport = view;
            scroll.scrollSensitivity = 50; scroll.movementType = ScrollRect.MovementType.Elastic; scroll.inertia = true;
            emptyNote = U.Label(trayStrip, "Empty", K.Body, Phone ? 16 : 18, "8A7560"); U.Stretch(emptyNote.rectTransform, Vector2.zero, Vector2.one, new Vector2(30, 0), new Vector2(-30, 0));
            emptyNote.textWrappingMode = TextWrappingModes.Normal;
        }

        void Tab(RectTransform parent, string key, string label, string icon)
        {
            var b = U.Button(parent, label, "secondary", () => ShowTab(key, true), TrayHeadH - 10, Phone ? 16 : 18);
            b.Apply(Data(label, "secondary", true, icon)); b.SetWidth(Phone ? 168 : 196);
            var pill = N.Image(b.transform, "Count", K.C("E15533"), 11); var pr = pill.rectTransform; pr.anchorMin = pr.anchorMax = pr.pivot = Vector2.one; pr.anchoredPosition = new Vector2(6, 8); pr.sizeDelta = new Vector2(30, 24);
            var t = N.Text(pill.transform, "Text", K.Number, 14, Color.white); t.alignment = TextAlignmentOptions.Center; U.Stretch(t.rectTransform, Vector2.zero, Vector2.one);
            pill.gameObject.AddComponent<CheckoutPulse>(); pill.gameObject.SetActive(false);
            tabs[key] = (b, pill.gameObject, t);
        }

        // The sheet over a card that is for sale (or still locked): picture, name, where it goes, what it does, price.
        void BuildSheet()
        {
            var edge = N.Image(hud, "Sheet", K.Border, 22); sheet = edge.rectTransform; edge.raycastTarget = true;
            sheet.anchorMin = sheet.anchorMax = new Vector2(.5f, 0); sheet.pivot = new Vector2(.5f, 0);
            float w = Phone ? 400 : 460; sheet.sizeDelta = new Vector2(w, 10);
            var col = N.Column(edge.gameObject, 0, new RectOffset(3, 3, 3, 6));
            sheet.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var face = N.Image(sheet, "Face", K.Cream, 20); N.Column(face.gameObject, Phone ? 6 : 8, new RectOffset(16, 16, 14, 14));
            var head = Node(face.transform, "Head"); var hr = N.Row(head.gameObject, 12);
            var art = N.Image(head, "Art", K.C("F7E6C8"), 16); var al = art.gameObject.AddComponent<LayoutElement>(); al.preferredWidth = al.preferredHeight = Phone ? 76 : 88;
            var glow = N.Image(art.transform, "Glow", Color.white, 0); glow.sprite = U.Glow(); U.Stretch(glow.rectTransform, Vector2.zero, Vector2.one, new Vector2(4, 4), new Vector2(-4, -4));
            sheetIcon = N.Image(art.transform, "Icon", Color.white, 0); sheetIcon.preserveAspect = true; U.Stretch(sheetIcon.rectTransform, Vector2.zero, Vector2.one, new Vector2(6, 6), new Vector2(-6, -6));
            var texts = Node(head, "Texts"); var tcol = N.Column(texts.gameObject, 2); tcol.childAlignment = TextAnchor.MiddleLeft; tcol.childForceExpandWidth = false; texts.gameObject.AddComponent<LayoutElement>().flexibleWidth = 1;
            sheetTitle = N.Text(texts, "Title", K.Headline, Phone ? 21 : 24, K.Ink);
            sheetZone = N.Text(texts, "Zone", K.Body, Phone ? 14 : 15, K.Muted);
            var up = N.Image(texts, "Upgrade", CheckoutDesktopHUD.ShopGold, 10); sheetUpgrade = up.gameObject;
            N.Row(up.gameObject, 4, new RectOffset(8, 10, 2, 2));
            var ui = N.Image(up.transform, "Icon", Color.white, 0); ui.sprite = K.Icon("Icons/lightning"); ui.preserveAspect = true; var uil = ui.gameObject.AddComponent<LayoutElement>(); uil.preferredWidth = uil.preferredHeight = 18;
            var ut = N.Text(up.transform, "Text", K.Label, 13, K.Ink); ut.text = "Melhoria"; ut.textWrappingMode = TextWrappingModes.NoWrap;
            sheetBody = N.Text(face.transform, "Body", K.Body, Phone ? 15 : 16, K.Ink);
            sheetButtons = Node(face.transform, "Buttons"); var br = N.Row(sheetButtons.gameObject, 8); br.childForceExpandWidth = true;
            sheet.gameObject.SetActive(false);
        }

        // Name and actions floating over the selected piece.
        void BuildFloatBar()
        {
            var bar = N.Image(hud, "Selection", new Color(.11f, .17f, .31f, .92f), 24); floatBar = bar.rectTransform; bar.raycastTarget = true;
            floatBar.anchorMin = floatBar.anchorMax = new Vector2(.5f, .5f); floatBar.pivot = new Vector2(.5f, 0);
            var row = N.Row(bar.gameObject, 8, new RectOffset(16, 8, 6, 8)); row.childForceExpandHeight = false;
            var fit = bar.gameObject.AddComponent<ContentSizeFitter>(); fit.horizontalFit = fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            float h = Phone ? 50 : 56;
            selectedIcon = N.Image(floatBar, "Picture", Color.white, 0); selectedIcon.preserveAspect = true; var pl = selectedIcon.gameObject.AddComponent<LayoutElement>(); pl.preferredWidth = pl.preferredHeight = h;
            floatName = N.Text(floatBar, "Name", K.Label, Phone ? 17 : 19, Color.white); floatName.textWrappingMode = TextWrappingModes.NoWrap; floatName.overflowMode = TextOverflowModes.Ellipsis; floatName.alignment = TextAlignmentOptions.MidlineLeft;
            var nl = floatName.gameObject.AddComponent<LayoutElement>(); nl.preferredWidth = Phone ? 170 : 200; nl.preferredHeight = h;
            rotateLeft = U.Button(floatBar, "", "primary", () => Rotate(-45), h, 16); rotateLeft.SetWidth(h + 6);
            rotateRight = U.Button(floatBar, "", "primary", () => Rotate(45), h, 16); rotateRight.SetWidth(h + 6);
            storeButton = U.Button(floatBar, "Guardar", "danger", Store, h, Phone ? 16 : 17); storeButton.Apply(Data("Guardar", "danger", true, "Icons/package")); storeButton.SetWidth(Phone ? 136 : 150);
            rotateLeft.SetIconSprite(CheckoutGlyph.Get("turn-left")); rotateRight.SetIconSprite(CheckoutGlyph.Get("turn-right"));
            BigIcon(rotateLeft, h * .78f); BigIcon(rotateRight, h * .78f);
            floatBar.gameObject.SetActive(false);
        }

        // The glyph buttons carry no label: their icon may fill most of the face.
        static void BigIcon(CheckoutDesktopButton b, float size)
        {
            var icon = b.transform.Find("Face/Icon"); var le = icon ? icon.GetComponent<LayoutElement>() : null;
            if (le) le.preferredWidth = le.preferredHeight = size;
        }

        static void TintIcon(CheckoutDesktopButton b, Color c) { var icon = b.transform.Find("Face/Icon"); var img = icon ? icon.GetComponent<Image>() : null; if (img) img.color = c; }

        // ------------------------------------------------------------------ refresh
        sealed class Entry
        {
            public string key, id, name, sprite, price, priceIcon, badge, badgeColor, note;
            public bool owned, waiting, locked, afford, upgrade, isNew;
            public DecorEntry decor;
        }

        List<Entry> Entries(string which)
        {
            var list = new List<Entry>(); var s = bridge.State; if (s == null || Interior == null) return list;
            if (which == "guardados")
            {
                // Shop furniture first (the checkout before everything: the shop opens with it), then the decorations.
                foreach (var w in Interior.waiting.OrderBy(w => w.Value.type == "checkout" || w.Value.type == "kiosk" ? 0 : 1).ThenBy(w => w.Key))
                {
                    var build = Interior.PendingBuild(w.Key);
                    list.Add(new Entry
                    {
                        key = "w:" + w.Key, id = w.Key, name = WaitingName(w.Key, w.Value.type), sprite = "Decor/" + w.Value.template, owned = true, waiting = true,
                        price = build != null ? string.Format("Obra · {0}", CheckoutConstructionSite.Countdown(build.durationMs)) : "Colocar", priceIcon = build != null ? "Icons/construction" : "Icons/success",
                        badge = w.Value.type == "checkout" || w.Value.type == "kiosk" ? "CAIXA" : "MÓVEL", badgeColor = "2E8CAE",
                    });
                }
                foreach (var d in s.decorCatalog ?? new DecorEntry[0])
                {
                    int free = Interior.Owned(d.id) - Interior.Placed(d.id);
                    if (free > 0) list.Add(DecorCard(d, s, free));
                }
                return list;
            }
            bool upgrades = which == "melhorias";
            foreach (var d in s.decorCatalog ?? new DecorEntry[0])
            {
                if (d.upgrade != upgrades) continue;
                string zone = string.IsNullOrEmpty(d.zone) ? "inside" : d.zone;
                if (zone != shopZone && zone != "both") continue;
                list.Add(DecorCard(d, s, Interior.Owned(d.id) - Interior.Placed(d.id)));
            }
            // In hand first, then what can be bought (cheapest first), then the locked ones by level.
            return list.OrderBy(e => e.owned ? 0 : e.locked ? 2 : 1).ThenBy(e => e.locked ? e.decor.requiredLevel : 0)
                .ThenBy(e => e.decor.coinPrice > 0 ? e.decor.coinPrice : e.decor.diamondPrice * 400).ToList();
        }

        Entry DecorCard(DecorEntry d, Snapshot s, int free)
        {
            bool levelOk = s.level >= d.requiredLevel, gems = d.coinPrice <= 0;
            int cost = gems ? d.diamondPrice : d.coinPrice;
            var e = new Entry
            {
                key = "d:" + d.id, id = d.id, name = d.name, sprite = "Decor/" + d.id, decor = d, upgrade = d.upgrade,
                owned = free > 0, locked = !levelOk, afford = gems ? s.diamonds >= cost : s.coins >= cost,
            };
            if (e.owned) { e.price = "Colocar"; e.priceIcon = "Icons/success"; e.badge = "x" + free; e.badgeColor = "5DA637"; }
            else if (e.locked) { e.price = string.Format("Nível {0}", d.requiredLevel); e.priceIcon = "Icons/lock"; }
            else { e.price = CheckoutI18n.Number(cost); e.priceIcon = gems ? "Icons/diamond" : "Icons/coin"; }
            // Machines pay only up to their limit: "2/3" placed.
            int placed = Interior.Placed(d.id);
            if (d.limit > 0 && placed > 0) e.note = placed + "/" + d.limit;
            e.isNew = levelOk && !e.owned && IsNew(d);
            if (e.isNew && string.IsNullOrEmpty(e.badge)) { e.badge = "NOVO"; e.badgeColor = "E15533"; }
            return e;
        }

        void RefreshTray()
        {
            if (!tray || Interior == null || bridge.State == null) return;
            int stored = Interior.waiting.Count + (bridge.State.decorCatalog ?? new DecorEntry[0]).Sum(d => Mathf.Max(0, Interior.Owned(d.id) - Interior.Placed(d.id)));
            // The first look goes to what is waiting to be placed (a new shop starts with its furniture there).
            if (!tabChosen) { tab = stored > 0 ? "guardados" : "decoracao"; tabChosen = true; }
            SetTabCount("guardados", stored);
            SetTabCount("decoracao", Entries("decoracao").Count(e => e.isNew));
            SetTabCount("melhorias", Entries("melhorias").Count(e => e.isNew));
            foreach (var t in tabs) t.Value.button.Apply(Data(t.Value.button.Data.label, "secondary", true, t.Value.button.Data.icon, t.Key == tab));

            var entries = Entries(tab);
            while (cardPool.Count < entries.Count) { var c = CheckoutBuildCard.Create(trayList, CardW); c.Tapped = TapCard; cardPool.Add(c); }
            for (int i = 0; i < cardPool.Count; i++)
            {
                bool on = i < entries.Count; cardPool[i].gameObject.SetActive(on);
                if (on) { var e = entries[i]; cardPool[i].Apply(e.key, e.name, e.sprite, e.price, e.priceIcon, e.badge, e.badgeColor, e.note, e.owned, e.waiting, e.locked, e.afford, e.upgrade, e.key == sheetFor); }
            }
            emptyNote.gameObject.SetActive(entries.Count == 0);
            if (entries.Count == 0) emptyNote.text = tab == "guardados" ? "Nada guardado. O que você comprar ou guardar aparece aqui." : "Nada aqui por enquanto.";
            if (sheetFor != null && !entries.Any(e => e.key == sheetFor)) CloseSheet();
            else if (sheetFor != null) FillSheet(entries.First(e => e.key == sheetFor));
            zoneInside.Apply(Data("Dentro", "secondary", true, "Icons/shelf", shopZone == "inside"));
            zoneOutside.Apply(Data("Fora", "secondary", true, "Icons/garden", shopZone == "outside"));
            foldButton.Apply(Data("", "primary", true)); foldButton.SetIconSprite(CheckoutGlyph.Get(folded ? "up" : "down"));
            gridButton.Apply(Data("Grade", "secondary", true, "", CheckoutInterior.GridOn)); gridButton.SetIconSprite(CheckoutGlyph.Get("grid")); TintIcon(gridButton, K.Ink);
        }

        void SetTabCount(string key, int n)
        {
            if (!tabs.TryGetValue(key, out var t)) return;
            t.badge.SetActive(n > 0); t.count.text = n > 9 ? "9+" : n.ToString();
            // "Guardados" counts in the brand red; new things in the shop tabs too (they pulse).
        }

        void ShowTab(string key, bool tapped)
        {
            if (tapped) Sound();
            tab = key; tabChosen = true; CloseSheet();
            if (folded) Fold(false);
            RefreshTray();
            var scroll = trayList.parent.GetComponent<ScrollRect>(); if (scroll) scroll.horizontalNormalizedPosition = 0;
        }

        void Fold(bool fold)
        {
            folded = fold; CloseSheet();
            float h = fold ? TrayHeadH + 10 : TrayH;
            if (foldMove != null) StopCoroutine(foldMove);
            foldMove = StartCoroutine(Resize(tray, h, .18f));
            foldButton.SetIconSprite(CheckoutGlyph.Get(folded ? "up" : "down"));
        }

        static System.Collections.IEnumerator Resize(RectTransform r, float h, float seconds)
        {
            float from = r.sizeDelta.y;
            for (float t = 0; t < 1; t += Time.unscaledDeltaTime / seconds) { r.sizeDelta = new Vector2(r.sizeDelta.x, Mathf.Lerp(from, h, 1 - (1 - t) * (1 - t))); yield return null; }
            r.sizeDelta = new Vector2(r.sizeDelta.x, h);
        }

        // ------------------------------------------------------------------ cards
        void TapCard(CheckoutBuildCard card)
        {
            var key = card.Key; var e = Entries(tab).FirstOrDefault(x => x.key == key); if (e == null) return;
            Sound();
            if (e.waiting) { CloseSheet(); PlaceWaiting(e.id); return; }
            if (e.owned) { CloseSheet(); PlaceFromStock(e.id); return; }
            // For sale or locked: the sheet (a second tap on the same card closes it).
            if (sheetFor == key) { CloseSheet(); return; }
            sheetFor = key; FillSheet(e); sheet.gameObject.SetActive(true);
            var at = U.PointIn(hud, (RectTransform)card.transform).x;
            float half = sheet.sizeDelta.x * .5f, room = hud.rect.width * .5f - 12;
            sheet.anchoredPosition = new Vector2(Mathf.Clamp(at, -room + half, room - half), tray.anchoredPosition.y + tray.sizeDelta.y + 10);
            StartCoroutine(U.Pop(sheet, 1.04f, .16f));
            RefreshTray();
        }

        void FillSheet(Entry e)
        {
            var d = e.decor; if (d == null) return; var s = bridge.State;
            sheetIcon.sprite = K.Icon(e.sprite); sheetIcon.color = e.locked ? new Color(1, 1, 1, .55f) : Color.white;
            sheetTitle.text = d.name;
            sheetZone.text = d.zone == "both" ? "Dentro ou fora do mercado" : d.zone == "outside" ? "Fora do mercado" : "Dentro do mercado";
            sheetUpgrade.SetActive(d.upgrade);
            sheetBody.text = d.upgrade && d.description.StartsWith("Melhoria: ") ? d.description.Substring(10) : d.description;
            var buttons = new List<DesktopButton>();
            if (e.locked) buttons.Add(Data(string.Format("Libera no nível {0}", d.requiredLevel), "secondary", false, "Icons/lock"));
            else
            {
                bool busy = bridge.HasPending("purchaseDecor");
                if (d.coinPrice > 0) buttons.Add(Data(s.coins >= d.coinPrice ? CheckoutI18n.Number(d.coinPrice) : string.Format("Faltam {0} moedas", CheckoutI18n.Number(d.coinPrice - s.coins)), "coin", s.coins >= d.coinPrice && !busy, "Icons/coin"));
                if (d.diamondPrice > 0) buttons.Add(Data(s.diamonds >= d.diamondPrice ? CheckoutI18n.Number(d.diamondPrice) : string.Format("Faltam {0} diamantes", CheckoutI18n.Number(d.diamondPrice - s.diamonds)), "gem", s.diamonds >= d.diamondPrice && !busy, "Icons/diamond"));
            }
            while (sheetPool.Count < buttons.Count)
            {
                var b = CheckoutDesktopButton.Create(sheetButtons, Phone ? 50 : 54, Phone ? 18 : 20, 14);
                b.Clicked = x => { if (x.Data != null && x.Data.enabled) BuyFromSheet(x.Data.variant == "gem"); };
                sheetPool.Add(b);
            }
            for (int i = 0; i < sheetPool.Count; i++) { bool on = i < buttons.Count; sheetPool[i].gameObject.SetActive(on); if (on) sheetPool[i].Apply(buttons[i]); }
        }

        void CloseSheet()
        {
            bool was = sheetFor != null; sheetFor = null;
            if (sheet) sheet.gameObject.SetActive(false);
            if (was) RefreshTray();
        }

        void BuyFromSheet(bool gems)
        {
            var key = sheetFor; if (key == null || !key.StartsWith("d:")) return;
            var id = key.Substring(2);
            bridge.Command("purchaseDecor", "[\"" + id + "\",\"" + (gems ? "diamonds" : "coins") + "\"]");
            placeAfterBuy = id; placeAfterBuyUntil = Time.unscaledTime + 6;
            MarkSeen(id);
            CloseSheet(); Say("Comprado! Já vai para o mercado: arraste até o lugar.");
        }

        // A purchase from the sheet lands a moment later: then the piece goes in where the camera looks.
        void PlaceBought()
        {
            if (placeAfterBuy == null) return;
            if (Time.unscaledTime > placeAfterBuyUntil) { placeAfterBuy = null; return; }
            if (Interior.Owned(placeAfterBuy) - Interior.Placed(placeAfterBuy) <= 0) return;
            var id = placeAfterBuy; placeAfterBuy = null; PlaceFromStock(id);
        }

        // ------------------------------------------------------------------ selection
        void ShowSelection(CheckoutInterior.Item it)
        {
            floatBar.gameObject.SetActive(it != null && it.root);
            if (it == null || !it.root) return;
            floatName.text = Name(it);
            selectedIcon.sprite = K.Icon("Decor/" + it.template); selectedIcon.gameObject.SetActive(selectedIcon.sprite);
            storeButton.gameObject.SetActive(!it.design);
            // Height of the piece: the bar floats just over its top.
            var rs = it.root.GetComponentsInChildren<Renderer>(); float top = it.root.position.y + 1.5f;
            if (rs.Length > 0) { var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); top = b.max.y; }
            floatHeight = top - it.root.position.y + .25f;
            LayoutRebuilder.ForceRebuildLayoutImmediate(floatBar);
            PlaceFloatBar();
        }

        void PlaceFloatBar()
        {
            if (!floatBar || !floatBar.gameObject.activeSelf || selected == null || !selected.root || simulation == null || !simulation.view) return;
            var screen = simulation.view.WorldToScreenPoint(selected.root.position + Vector3.up * floatHeight);
            if (screen.z < 0) return;
            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(hud, screen, null, out var local)) return;
            var r = hud.rect; float w = floatBar.rect.width, h = floatBar.rect.height;
            float bottom = r.yMin + tray.anchoredPosition.y + tray.sizeDelta.y + 8, top = r.yMax - (Phone ? 76 : 92) - h;
            local.x = Mathf.Clamp(local.x, r.xMin + w * .5f + 8, r.xMax - w * .5f - 8);
            local.y = Mathf.Clamp(local.y + 6, bottom, Mathf.Max(bottom, top));
            floatBar.anchoredPosition = local;
        }

        // ------------------------------------------------------------------ new in the shop
        // Decorations unlocked since the player last opened the tray get a "NOVO" ribbon (the first visit seeds the
        // list quietly, so a new game does not start with every card shouting).
        const string SeenKey = "checkout.decorSeen";
        HashSet<string> seen;
        HashSet<string> Seen
        {
            get
            {
                if (seen != null) return seen;
                seen = new HashSet<string>();
                try
                {
                    if (PlayerPrefs.HasKey(SeenKey))
                    {
                        foreach (var id in PlayerPrefs.GetString(SeenKey).Split(',')) if (id.Length > 0) seen.Add(id);
                    }
                    else
                    {
                        var s = bridge.State; foreach (var d in s?.decorCatalog ?? new DecorEntry[0]) if (s.level >= d.requiredLevel) seen.Add(d.id);
                        SaveSeen();
                    }
                }
                catch { }
                return seen;
            }
        }
        bool IsNew(DecorEntry d) => !Seen.Contains(d.id);
        void MarkSeen(string id) { if (Seen.Add(id)) SaveSeen(); }
        void SaveSeen() { try { PlayerPrefs.SetString(SeenKey, string.Join(",", seen)); } catch { } }
        // Leaving the build mode: what was on show is no longer new.
        void SeeAll()
        {
            var s = bridge.State; if (s?.decorCatalog == null) return;
            bool changed = false; foreach (var d in s.decorCatalog) if (s.level >= d.requiredLevel && Seen.Add(d.id)) changed = true;
            if (changed) SaveSeen();
        }

        void Sound() { var hudView = FindAnyObjectByType<CheckoutDesktopHUD>(); if (hudView) hudView.Tap(); }
    }

    // One card of the build tray: the piece on a soft glow, a ribbon (x2 / NOVO / MÓVEL), the name and its price or
    // what a tap does. Taps that start a sideways drag scroll the tray instead (the ScrollRect takes the drag).
    public sealed class CheckoutBuildCard : MonoBehaviour, IPointerClickHandler, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        Image edge, face, art, glow, icon, ribbonBack, priceIcon, lockIcon, upgrade; TextMeshProUGUI title, price, ribbon, note; GameObject noteBack;
        public string Key { get; private set; }
        public System.Action<CheckoutBuildCard> Tapped;
        bool pressed, chosen;

        public static CheckoutBuildCard Create(Transform parent, float width)
        {
            var root = N.Node("Card", parent); var c = root.gameObject.AddComponent<CheckoutBuildCard>();
            var le = root.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = le.minWidth = width;
            c.edge = root.gameObject.AddComponent<Image>(); c.edge.sprite = K.Rounded(18); c.edge.type = Image.Type.Sliced; c.edge.raycastTarget = true;
            c.face = N.Image(root, "Face", K.Cream, 16); U.Stretch(c.face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 6), new Vector2(-3, -3));
            bool phone = CheckoutScreen.Handheld; float textH = phone ? 50 : 58;
            c.art = N.Image(c.face.transform, "Art", K.C("F7E6C8"), 14); U.Stretch(c.art.rectTransform, Vector2.zero, Vector2.one, new Vector2(6, textH), new Vector2(-6, -6));
            c.glow = N.Image(c.art.transform, "Glow", Color.white, 0); c.glow.sprite = U.Glow(); U.Stretch(c.glow.rectTransform, Vector2.zero, Vector2.one, new Vector2(6, 2), new Vector2(-6, -2));
            c.icon = N.Image(c.art.transform, "Icon", Color.white, 0); c.icon.preserveAspect = true; U.Stretch(c.icon.rectTransform, Vector2.zero, Vector2.one, new Vector2(-6, -2), new Vector2(6, 6)); // the renders keep a margin: a little past the panel reads bigger
            c.lockIcon = N.Image(c.art.transform, "Lock", Color.white, 0); c.lockIcon.sprite = K.Icon("Icons/lock"); c.lockIcon.preserveAspect = true;
            var lr = c.lockIcon.rectTransform; lr.anchorMin = lr.anchorMax = lr.pivot = new Vector2(1, 0); lr.anchoredPosition = new Vector2(-4, 4); lr.sizeDelta = new Vector2(30, 30);
            // Upgrade mark (top-left): a gold coin with a lightning bolt.
            c.upgrade = N.Image(c.art.transform, "Upgrade", CheckoutDesktopHUD.ShopGold, 13); var ur = c.upgrade.rectTransform; ur.anchorMin = ur.anchorMax = ur.pivot = new Vector2(0, 1); ur.anchoredPosition = new Vector2(4, -4); ur.sizeDelta = new Vector2(28, 28);
            var bolt = N.Image(c.upgrade.transform, "Bolt", Color.white, 0); bolt.sprite = K.Icon("Icons/lightning"); bolt.preserveAspect = true; U.Stretch(bolt.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 3), new Vector2(-3, -3));
            // Ribbon (top-right): x2 owned, NOVO, MÓVEL.
            c.ribbonBack = N.Image(c.art.transform, "Ribbon", K.C("5DA637"), 10); var rr = c.ribbonBack.rectTransform; rr.anchorMin = rr.anchorMax = rr.pivot = Vector2.one; rr.anchoredPosition = new Vector2(-4, -4);
            N.Row(c.ribbonBack.gameObject, 0, new RectOffset(8, 8, 2, 2)); var rf = c.ribbonBack.gameObject.AddComponent<ContentSizeFitter>(); rf.horizontalFit = rf.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            c.ribbon = N.Text(c.ribbonBack.transform, "Text", K.Label, phone ? 12 : 13, Color.white); c.ribbon.textWrappingMode = TextWrappingModes.NoWrap;
            // How many are out of the limit ("2/3"), bottom-left of the art.
            var nb = N.Image(c.art.transform, "Note", new Color(.11f, .17f, .31f, .85f), 9); c.noteBack = nb.gameObject; var nr = nb.rectTransform; nr.anchorMin = nr.anchorMax = nr.pivot = Vector2.zero; nr.anchoredPosition = new Vector2(4, 4);
            N.Row(nb.gameObject, 0, new RectOffset(7, 7, 1, 1)); var nf = nb.gameObject.AddComponent<ContentSizeFitter>(); nf.horizontalFit = nf.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            c.note = N.Text(nb.transform, "Text", K.Number, 12, Color.white); c.note.textWrappingMode = TextWrappingModes.NoWrap;
            // Name, then the price line.
            c.title = U.Label(c.face.transform, "Name", K.Label, phone ? 14 : 16, "4A3624"); c.title.enableAutoSizing = true; c.title.fontSizeMin = phone ? 11 : 12; c.title.fontSizeMax = phone ? 14 : 16; U.Stretch(c.title.rectTransform, Vector2.zero, new Vector2(1, 0), new Vector2(6, textH - (phone ? 24 : 27)), new Vector2(-6, textH - 2));
            var line = N.Node("Price", c.face.transform); U.Stretch(line, Vector2.zero, new Vector2(1, 0), new Vector2(6, 4), new Vector2(-6, phone ? 25 : 30));
            var row = N.Row(line.gameObject, 4); row.childAlignment = TextAnchor.MiddleCenter;
            c.priceIcon = N.Image(line, "Icon", Color.white, 0); c.priceIcon.preserveAspect = true; var pl = c.priceIcon.gameObject.AddComponent<LayoutElement>(); pl.preferredWidth = pl.preferredHeight = phone ? 20 : 24;
            c.price = N.Text(line, "Value", K.Number, phone ? 14 : 16, K.Ink); c.price.textWrappingMode = TextWrappingModes.NoWrap; c.price.overflowMode = TextOverflowModes.Ellipsis;
            return c;
        }

        public void Apply(string key, string name, string sprite, string priceText, string priceSprite, string badge, string badgeColor, string limit,
            bool owned, bool waiting, bool locked, bool afford, bool isUpgrade, bool isChosen)
        {
            Key = key; chosen = isChosen;
            // Gold edge on the card whose sheet is open; green for what is in hand; blue for shop furniture.
            edge.color = chosen ? K.C("E0A441") : owned ? K.C("8CC063") : K.Border;
            art.color = waiting ? K.C("CFE7F1") : owned ? K.C("D9EFC6") : locked ? K.C("E4DACB") : K.C("F7E6C8");
            glow.color = new Color(1, 1, 1, locked ? .35f : .9f);
            var s = K.Icon(sprite); icon.sprite = s; icon.gameObject.SetActive(s); icon.color = locked ? new Color(.55f, .55f, .55f, .8f) : Color.white;
            lockIcon.gameObject.SetActive(locked && lockIcon.sprite);
            upgrade.gameObject.SetActive(isUpgrade);
            bool hasBadge = !string.IsNullOrEmpty(badge); ribbonBack.gameObject.SetActive(hasBadge);
            if (hasBadge) { ribbon.text = badge; ribbonBack.color = K.C(badgeColor ?? "5DA637"); }
            noteBack.SetActive(!string.IsNullOrEmpty(limit)); if (!string.IsNullOrEmpty(limit)) note.text = limit;
            if (title.text != name) title.text = name;
            price.text = K.Clean(priceText);
            price.color = owned ? K.C("427A24") : locked ? K.Muted : afford ? K.Ink : K.C("C0401F");
            var ps = K.Icon(priceSprite); priceIcon.sprite = ps; priceIcon.gameObject.SetActive(ps);
            Layout();
        }

        void Layout() { transform.localScale = Vector3.one * (pressed ? .96f : chosen ? 1.03f : 1f); }
        public void OnPointerDown(PointerEventData e) { if (e.button != PointerEventData.InputButton.Left) return; pressed = true; Layout(); }
        public void OnPointerUp(PointerEventData e) { pressed = false; Layout(); }
        public void OnPointerExit(PointerEventData e) { pressed = false; Layout(); }
        public void OnPointerClick(PointerEventData e) { if (e.button == PointerEventData.InputButton.Left) Tapped?.Invoke(this); }
    }

    // Small white glyphs drawn in code for the build tools (turn left / right, fold the tray). The painted icon set
    // has no arrows, and a glyph this simple reads better flat on a coloured button.
    public static class CheckoutGlyph
    {
        static readonly Dictionary<string, Sprite> cache = new Dictionary<string, Sprite>();

        public static Sprite Get(string kind)
        {
            if (cache.TryGetValue(kind, out var s)) return s;
            const int n = 96; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color32[n * n]; float pixel = 2f / n;
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    var p = new Vector2((x + .5f) / n * 2 - 1, (y + .5f) / n * 2 - 1);
                    float d = Distance(kind, p);
                    px[y * n + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(.5f - d / pixel) * 255));
                }
            tex.SetPixels32(px); tex.Apply();
            s = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(.5f, .5f)); cache[kind] = s; return s;
        }

        static float Distance(string kind, Vector2 p)
        {
            const float stroke = .12f;
            switch (kind)
            {
                case "down": return Mathf.Min(Segment(p, new Vector2(-.45f, .2f), new Vector2(0, -.25f)), Segment(p, new Vector2(0, -.25f), new Vector2(.45f, .2f))) - stroke;
                case "up": return Mathf.Min(Segment(p, new Vector2(-.45f, -.2f), new Vector2(0, .25f)), Segment(p, new Vector2(0, .25f), new Vector2(.45f, -.2f))) - stroke;
                case "ring": return Mathf.Abs(p.magnitude - .8f) - .13f;
                case "grid":
                {
                    // A 3 x 3 floor grid: four lines each way inside a square.
                    float d = 1, s = .1f;
                    foreach (var c in new[] { -.66f, -.22f, .22f, .66f })
                    {
                        d = Mathf.Min(d, Segment(p, new Vector2(c, -.66f), new Vector2(c, .66f)));
                        d = Mathf.Min(d, Segment(p, new Vector2(-.66f, c), new Vector2(.66f, c)));
                    }
                    return d - s * .7f;
                }
                case "turn-left": p.x = -p.x; goto case "turn-right";
                case "turn-right":
                {
                    // A ring open at the top, the arrow head on its left end pointing into the gap (clockwise).
                    const float radius = .5f, gapFrom = 55, gapTo = 125;
                    float angle = Mathf.Atan2(p.y, p.x) * Mathf.Rad2Deg; if (angle < 0) angle += 360;
                    float ring = angle > gapFrom && angle < gapTo
                        ? Mathf.Min(Vector2.Distance(p, Polar(radius, gapFrom)), Vector2.Distance(p, Polar(radius, gapTo))) - stroke
                        : Mathf.Abs(p.magnitude - radius) - stroke;
                    // Head at 120°, pointing along the clockwise tangent.
                    var at = Polar(radius, gapTo); float a = gapTo * Mathf.Deg2Rad;
                    var tangent = new Vector2(Mathf.Sin(a), -Mathf.Cos(a)); var normal = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                    float head = Triangle(p, at + tangent * .42f, at + normal * .3f - tangent * .06f, at - normal * .3f - tangent * .06f);
                    return Mathf.Min(ring, head);
                }
                default: return 1;
            }
        }

        static Vector2 Polar(float r, float degrees) { float a = degrees * Mathf.Deg2Rad; return new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r; }
        static float Segment(Vector2 p, Vector2 a, Vector2 b) { var ab = b - a; float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude); return Vector2.Distance(p, a + ab * t); }
        // Signed distance to a triangle (negative inside).
        static float Triangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float d = Mathf.Min(Segment(p, a, b), Mathf.Min(Segment(p, b, c), Segment(p, c, a)));
            float s1 = Cross(b - a, p - a), s2 = Cross(c - b, p - b), s3 = Cross(a - c, p - c);
            bool inside = (s1 >= 0 && s2 >= 0 && s3 >= 0) || (s1 <= 0 && s2 <= 0 && s3 <= 0);
            return inside ? -d : d;
        }
        static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;
    }
}
