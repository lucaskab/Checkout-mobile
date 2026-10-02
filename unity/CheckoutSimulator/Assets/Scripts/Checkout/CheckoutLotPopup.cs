using TMPro;
using UnityEngine;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout
{
    // The panel a locked lot opens when it is clicked (like the locked plots of Township or the closed areas of
    // Idle Supermarket Tycoon): what stands there, what the lot is needed for and the one thing to do now —
    // buy it, clear it, speed the clearing up, or (not next to the player's land yet) which lot comes first.
    // It stays next to the lot on screen and follows the snapshot (a purchase turns "Comprar" into "Limpar").
    public static class CheckoutLotPopup
    {
        static RectTransform canvas, card;
        static TextMeshProUGUI title, subtitle, status, needed, note;
        static CheckoutDesktopButton action, close;
        static Image badge; static TextMeshProUGUI badgeText;
        static string lotId; static Vector3 anchor;
        static CheckoutLotSites owner;
        static Runner runner;

        class Runner : MonoBehaviour
        {
            void LateUpdate()
            {
                if (!card || !card.gameObject.activeSelf) return;
                if (Input.GetKeyDown(KeyCode.Escape)) { Hide(); return; }
                // Click outside the card closes it.
                if (Input.GetMouseButtonDown(0) && !RectTransformUtility.RectangleContainsScreenPoint(card, Input.mousePosition, null)) { Hide(); return; }
                var cam = Camera.main; if (!cam || !canvas) return;
                var sp = cam.WorldToScreenPoint(anchor);
                if (sp.z < 0) { Hide(); return; }
                RectTransformUtility.ScreenPointToLocalPointInRectangle(canvas, sp, null, out var local);
                var half = canvas.rect.size * .5f; var size = card.rect.size;
                local.x = Mathf.Clamp(local.x + size.x * .5f + 40, -half.x + size.x * .5f + 16, half.x - size.x * .5f - 16);
                local.y = Mathf.Clamp(local.y + 30, -half.y + size.y * .5f + 120, half.y - size.y * .5f - 110);
                card.anchoredPosition = local;
            }
        }

        static void Build()
        {
            if (canvas) return;
            var host = Object.FindAnyObjectByType<CheckoutDesktopHost>();
            canvas = U.Canvas(host ? host.transform : null, "Lot popup", 55);
            runner = canvas.gameObject.AddComponent<Runner>();
            var edge = N.Image(canvas, "Card", K.Border, 22); card = edge.rectTransform;
            card.anchorMin = card.anchorMax = new Vector2(.5f, .5f); card.pivot = new Vector2(.5f, .5f); card.sizeDelta = new Vector2(440, 300);
            U.Shadow(card, new Vector2(480, 330), new Vector2(0, -10)).transform.SetAsFirstSibling();
            var face = N.Image(card, "Face", K.Cream, 20); U.Stretch(face.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 7), new Vector2(-3, -3));
            var f = face.rectTransform;
            title = U.Label(f, "Title", K.Headline, 30, "4A3624", TextAlignmentOptions.Left);
            U.Stretch(title.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(22, -58), new Vector2(-60, -14));
            subtitle = U.Label(f, "Ruin", K.Body, 18, "8A7560", TextAlignmentOptions.Left);
            U.Stretch(subtitle.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(22, -84), new Vector2(-22, -58));
            badge = N.Image(f, "Badge", K.C("E7DCCB"), 14); U.At(badge.rectTransform, new Vector2(1, 1), new Vector2(124, 30), new Vector2(-118, -34));
            badgeText = U.Label(badge.rectTransform, "Text", K.Label, 15, "4A3624"); U.Stretch(badgeText.rectTransform, Vector2.zero, Vector2.one);
            status = U.Label(f, "Status", K.Label, 18, "4A3624", TextAlignmentOptions.TopLeft);
            status.textWrappingMode = TextWrappingModes.Normal; status.overflowMode = TextOverflowModes.Overflow;
            U.Stretch(status.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(22, -150), new Vector2(-22, -94));
            needed = U.Label(f, "Needed", K.Body, 17, "8A7560", TextAlignmentOptions.Left);
            U.Stretch(needed.rectTransform, new Vector2(0, 1), new Vector2(1, 1), new Vector2(22, -178), new Vector2(-22, -154));
            var row = N.Node("Buttons", f); U.Stretch(row, new Vector2(0, 0), new Vector2(1, 0), new Vector2(18, 14), new Vector2(-18, 72));
            var h = N.Row(row.gameObject, 10); h.childControlHeight = true; h.childForceExpandHeight = true; h.childControlWidth = true; h.childForceExpandWidth = true;
            action = U.Button(row, "", "coin", Act, 56, 21);
            note = U.Label(f, "Note", K.Body, 15, "C0401F", TextAlignmentOptions.Center);
            U.Stretch(note.rectTransform, new Vector2(0, 0), new Vector2(1, 0), new Vector2(18, 76), new Vector2(-18, 100));
            close = CheckoutDesktopButton.Create(f, 36, 18, 18);
            close.Apply(new DesktopButton { label = "X", variant = "secondary", enabled = true, icon = "", action = "", args = "[]", route = "", after = "", ok = "", fail = "" });
            close.Clicked = _ => Hide();
            var cr = (RectTransform)close.transform; cr.anchorMin = cr.anchorMax = new Vector2(1, 1); cr.sizeDelta = new Vector2(38, 38); cr.anchoredPosition = new Vector2(-28, -30);
            badge.transform.SetSiblingIndex(close.transform.GetSiblingIndex());
            card.gameObject.SetActive(false);
        }

        public static void Show(CheckoutLotSites sites, LotRect lot)
        {
            if (lot == null) return;
            Build();
            owner = sites; lotId = lot.id;
            anchor = new Vector3((lot.x0 + lot.x1) * .5f, 2f, (lot.z0 + lot.z1) * .5f);
            card.gameObject.SetActive(true);
            Fill(lot);
            card.localScale = Vector3.one * .9f;
            runner.StartCoroutine(U.Scale(card, Vector3.one, .14f, true));
        }

        public static void Hide() { if (card) card.gameObject.SetActive(false); lotId = null; }

        /// <summary>New snapshot: the open panel follows the lot (bought, clearing, cleared...).</summary>
        public static void Refresh(CheckoutLotSites sites)
        {
            if (!card || !card.gameObject.activeSelf || string.IsNullOrEmpty(lotId)) return;
            var lot = sites.Lot(lotId);
            if (lot == null) { Hide(); return; }
            Fill(lot);
        }

        static string act; static string[] actArgs; static string route;

        static void Fill(LotRect lot)
        {
            title.text = lot.label;
            subtitle.text = string.IsNullOrEmpty(lot.ruinName) ? "" : "Tem: " + lot.ruinName.ToLowerInvariant();
            needed.text = string.IsNullOrEmpty(lot.neededBy) ? "" : "Necessário para: " + lot.neededBy;
            note.text = "";
            double coins = owner ? owner.Coins : 0, gems = owner ? owner.Diamonds : 0;
            string time = CheckoutConstructionSite.Countdown(lot.clearDurationMs);
            act = null; route = null; actArgs = new[] { lot.id };
            switch (lot.status)
            {
                case "bloqueado":
                    Badge("BLOQUEADO", "E7DCCB", "8A7560");
                    status.text = "Compre antes um terreno vizinho do seu. Preço: " + CheckoutLotSites.Money(lot.price) + " moedas.";
                    Button("Ver terrenos", "secondary", true); route = "~loja:terrenos";
                    break;
                case "venda":
                    Badge("À VENDA", "FFF1CF", "8A5A00");
                    status.text = "Depois de comprar, a equipe limpa o terreno (" + CheckoutLotSites.Money(lot.clearCost) + " moedas · " + time + ").";
                    Button("Comprar · " + CheckoutLotSites.Money(lot.price), "coin", coins >= lot.price); act = "buyLot";
                    if (coins < lot.price) note.text = "Faltam " + CheckoutLotSites.Money(lot.price - coins) + " moedas";
                    break;
                case "comprado":
                    Badge("FALTA LIMPAR", "FCE4DC", "C0401F");
                    status.text = "O terreno é seu. A equipe tira tudo em " + time + ".";
                    bool busy = owner && owner.ClearingBusy;
                    Button(busy ? "Equipe ocupada" : "Limpar · " + CheckoutLotSites.Money(lot.clearCost), "coin", !busy && coins >= lot.clearCost); act = "clearLot";
                    if (busy) note.text = "A equipe está limpando outro terreno";
                    else if (coins < lot.clearCost) note.text = "Faltam " + CheckoutLotSites.Money(lot.clearCost - coins) + " moedas";
                    break;
                case "limpando":
                    Badge("LIMPANDO", "EAF6DF", "427A24");
                    double left = lot.clearEndsAt - CheckoutConstructionSite.Now;
                    status.text = "A equipe está trabalhando: falta " + CheckoutConstructionSite.Countdown(left) + ".";
                    Button("Acelerar · " + lot.skipCost + " diamantes", "gem", gems >= lot.skipCost && lot.skipCost > 0); act = "finishLotClearingNow"; actArgs = new string[0];
                    break;
                default:
                    Hide(); break;
            }
        }

        static void Badge(string text, string back, string ink) { badge.color = K.C(back); badgeText.text = text; badgeText.color = K.C(ink); }

        static void Button(string label, string variant, bool enabled)
        {
            action.Apply(new DesktopButton { label = label, variant = variant, enabled = enabled, icon = "", action = "", args = "[]", route = "", after = "", ok = "", fail = "" });
        }

        static void Act()
        {
            if (action.Data != null && !action.Data.enabled) return;
            var host = Object.FindAnyObjectByType<CheckoutDesktopHost>();
            if (!host) return;
            if (!string.IsNullOrEmpty(route)) { host.Route(route); Hide(); return; }
            if (string.IsNullOrEmpty(act)) return;
            var args = "[" + string.Join(",", System.Array.ConvertAll(actArgs, a => "\"" + a + "\"")) + "]";
            host.Action(act, args, "");
        }
    }
}
