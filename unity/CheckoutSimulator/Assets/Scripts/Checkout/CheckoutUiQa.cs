#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Checkout
{
    // Phone UI check (Editor / development builds): opens every HUD page and the game windows one after another,
    // saves a screenshot of each at the device resolution (run it in the Device Simulator) and measures the UI:
    // text size in points on the real screen, text that does not fit its box, buttons too small to tap, buttons and
    // texts covering each other, things outside the safe area. Output: Logs/ui_qa/*.png and Logs/ui_qa/report.txt.
    // Start: Checkout > QA > Capture phone UI (Play mode) or the CHECKOUT_UI_QA=1 environment variable.
    public sealed class CheckoutUiQa : MonoBehaviour
    {
        const float MinTextPt = 10f;      // iOS points (Apple HIG body minimum is 11 pt; 10 flags the clearly small ones)
        const float MinTapPt = 40f;       // iOS points: 44 pt recommended; flag clearly smaller targets
        // iOS points (= Android dp): about dpi / 160 pixels each (3 px on an iPhone 13 Pro).
        static float PxPerPt => (Screen.dpi > 0 ? Screen.dpi : 460f) / 160f;
        public static bool Running { get; private set; }

        static readonly string[] Routes =
        {
            "", "day", "requests", "store", "shelves", "products", "capacity", "storage", "storageexpand", "suppliers",
            "logistics", "sectors", "missions", "album", "achievements", "guia", "kitchen",
            "loja:destaques", "loja:moveis", "loja:melhorias", "loja:equipe", "loja:terrenos", "loja:expansoes",
            "loja:decoracao", "loja:moedas",
        };

        static bool counterOnly;
        /// <summary>counter: only the checkout mini-game, played through its phases (scan, pay, change, card).</summary>
        public static void Begin(bool counter = false)
        {
            if (Running || !Application.isPlaying) return;
            counterOnly = counter;
            var go = new GameObject("Checkout UI QA");
            DontDestroyOnLoad(go);
            go.AddComponent<CheckoutUiQa>();
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Auto()
        {
            if (System.Environment.GetEnvironmentVariable("CHECKOUT_UI_QA") == "1") Begin();
        }

        string dir;
        readonly StringBuilder report = new StringBuilder();
        int index;

        IEnumerator Start()
        {
            Running = true;
            dir = Path.Combine(Application.dataPath, "..", "Logs", "ui_qa");
            if (Directory.Exists(dir)) foreach (var f in Directory.GetFiles(dir)) File.Delete(f);
            Directory.CreateDirectory(dir);
            float dpi = Screen.dpi > 0 ? Screen.dpi : 460f;
            report.AppendLine($"Phone UI QA {System.DateTime.Now:yyyy-MM-dd HH:mm}  screen {Screen.width}x{Screen.height}  dpi {dpi:0}  safe {Screen.safeArea}  usable {CheckoutScreen.Usable(Screen.safeArea)}  orientation {Screen.orientation}  handheld={CheckoutScreen.Handheld}");
            report.AppendLine($"Thresholds: text < {MinTextPt} pt, tap target < {MinTapPt} pt (iOS pt, 1 pt = {PxPerPt:0.0} px)");
            // Wait for the game to be running (title screen dismissed by the tester or auto-play).
            float wait = 0;
            while (CheckoutDesktopHost.Active == null && wait < 30) { wait += Time.unscaledDeltaTime; yield return null; }
            yield return new WaitForSecondsRealtime(2f);

            if (counterOnly) { yield return CounterPhases(); Finish(); yield break; }
            foreach (var route in Routes)
            {
                CloseWindows();
                CheckoutDesktopHost.Active?.Route(route == "" ? "" : "!" + route);
                yield return new WaitForSecondsRealtime(1.2f);
                yield return Shot(route == "" ? "hud" : route.Replace(':', '_'));
            }
            CheckoutDesktopHost.Active?.Route("");
            yield return new WaitForSecondsRealtime(.6f);

            // Game windows.
            yield return CounterPhases();
            yield return Window("restock", () => { CheckoutRestockGame.Show(); return CheckoutRestockGame.Instance && CheckoutRestockGame.Instance.IsOpen; });
            yield return Window("receiving", () => { CheckoutReceivingGame.Show(); return CheckoutReceivingGame.Instance && CheckoutReceivingGame.Instance.IsOpen; });
            yield return Window("supplier_shop", () => { CheckoutSupplierShop.Show(); return CheckoutSupplierShop.Instance && CheckoutSupplierShop.Instance.IsOpen; });
            yield return Window("delivery_app", () => { CheckoutSupplierShop.ShowDelivery(); return CheckoutSupplierShop.Instance && CheckoutSupplierShop.Instance.IsOpen; });
            Finish();
        }

        void Finish()
        {
            CloseWindows();
            File.WriteAllText(Path.Combine(dir, "report.txt"), report.ToString());
            Debug.Log("CHECKOUT_UI_QA done: " + index + " screens in Logs/ui_qa");
            Running = false;
            Destroy(gameObject);
        }

        // The checkout played like a player: scan everything, take the cash, give the change; then a card customer.
        IEnumerator CounterPhases()
        {
            var game = CheckoutCounterGame.Instance;
            if (!game) { report.AppendLine("\n## counter phases: no register in this save"); yield break; }
            CloseWindows(); CheckoutDesktopHost.Active?.Route("");
            yield return new WaitForSecondsRealtime(.4f);
            CheckoutEntry Fake(string method) => new CheckoutEntry { id = "qa", customerId = "qa", customerName = "Dona Neide", method = method, total = 23, cashGiven = 50, readyAt = 0,
                items = new[] { new CheckoutLine { productId = 21, quantity = 2, name = "Água mineral", unitPrice = 7 }, new CheckoutLine { productId = 1, quantity = 1, name = "Tomate", unitPrice = 9 } } };
            game.OpenPreview(Fake("dinheiro"));
            yield return new WaitForSecondsRealtime(1.6f); yield return Shot("counter_1_scan");
            yield return game.QaScanAll();
            yield return new WaitForSecondsRealtime(2.2f); yield return Shot("counter_2_pay");
            game.QaPayAll();
            yield return new WaitForSecondsRealtime(2.4f); yield return Shot("counter_3_change");
            game.QaGive(20); yield return new WaitForSecondsRealtime(.8f); yield return Shot("counter_4_change_given");
            CloseWindows(); yield return new WaitForSecondsRealtime(.4f);
            game.OpenPreview(Fake("cartao"));
            yield return new WaitForSecondsRealtime(1.2f);
            yield return game.QaScanAll();
            yield return new WaitForSecondsRealtime(2.4f); yield return Shot("counter_5_card");
            CloseWindows();
        }

        IEnumerator Window(string name, System.Func<bool> open)
        {
            CloseWindows();
            CheckoutDesktopHost.Active?.Route("");
            yield return new WaitForSecondsRealtime(.4f);
            bool opened = false;
            try { opened = open(); } catch (System.Exception ex) { report.AppendLine($"\n## {name}: could not open ({ex.Message})"); }
            if (!opened) { report.AppendLine($"\n## {name}: not available in this save"); yield break; }
            yield return new WaitForSecondsRealtime(1.2f);
            yield return Shot("window_" + name);
        }

        static void CloseWindows()
        {
            foreach (var mb in new MonoBehaviour[] { CheckoutCounterGame.Instance, CheckoutRestockGame.Instance, CheckoutReceivingGame.Instance, CheckoutSupplierShop.Instance, CheckoutStockroom.Instance, CheckoutPackingGame.Instance, CheckoutIncidents.Instance })
                if (mb) mb.SendMessage("Close", SendMessageOptions.DontRequireReceiver);
        }

        IEnumerator Shot(string name)
        {
            index++;
            string file = $"{index:00}_{name}";
            yield return new WaitForEndOfFrame();
            var tex = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(dir, file + ".jpg"), tex.EncodeToJPG(80));
            Destroy(tex);
            Measure(file);
        }

        struct Item { public string kind, path, text; public Rect r; public float pt; public bool overflow; }

        void Measure(string file)
        {
            float px = PxPerPt;
            var screen = new Rect(0, 0, Screen.width, Screen.height);
            var safe = CheckoutScreen.Usable(Screen.safeArea);
            var items = new List<Item>();
            foreach (var canvas in FindObjectsByType<Canvas>(FindObjectsSortMode.None))
            {
                if (!canvas.isActiveAndEnabled || !canvas.isRootCanvas) continue;
                var cam = canvas.renderMode == RenderMode.ScreenSpaceOverlay ? null : canvas.worldCamera;
                if (canvas.renderMode == RenderMode.WorldSpace) continue;
                float scale = canvas.scaleFactor;
                foreach (var t in canvas.GetComponentsInChildren<TMP_Text>(false))
                {
                    if (!t.isActiveAndEnabled || string.IsNullOrWhiteSpace(t.text) || t.color.a < .05f || Hidden(t)) continue;
                    var r = ScreenRect(t.rectTransform, cam);
                    if (r.width < 2 || r.height < 2 || !r.Overlaps(screen)) continue;
                    float size = (t.enableAutoSizing ? t.fontSize : t.fontSize) * scale * t.rectTransform.lossyScale.y / Mathf.Max(.0001f, canvas.transform.lossyScale.y);
                    items.Add(new Item { kind = "text", path = NodePath(t.transform), text = Clip(t.text), r = r, pt = size / px, overflow = t.isTextOverflowing || t.isTextTruncated });
                }
                foreach (var s in canvas.GetComponentsInChildren<Selectable>(false))
                {
                    if (!s.isActiveAndEnabled || !s.interactable || Hidden(s)) continue;
                    var r = ScreenRect((RectTransform)s.transform, cam);
                    if (r.width < 2 || r.height < 2 || !r.Overlaps(screen)) continue;
                    items.Add(new Item { kind = "button", path = NodePath(s.transform), text = Label(s), r = r, pt = Mathf.Min(r.width, r.height) / px });
                }
            }
            report.AppendLine($"\n## {file}  ({items.Count(i => i.kind == "text")} texts, {items.Count(i => i.kind == "button")} buttons)");
            foreach (var i in items.Where(i => i.kind == "text" && i.pt < MinTextPt).OrderBy(i => i.pt).Take(25))
                report.AppendLine($"SMALL_TEXT {i.pt:0.0}pt \"{i.text}\"  [{i.path}]");
            foreach (var i in items.Where(i => i.kind == "text" && i.overflow).Take(25))
                report.AppendLine($"OVERFLOW \"{i.text}\"  [{i.path}]");
            foreach (var i in items.Where(i => i.kind == "button" && i.pt < MinTapPt).OrderBy(i => i.pt).Take(25))
                report.AppendLine($"SMALL_TAP {i.pt:0}pt \"{i.text}\"  [{i.path}]");
            foreach (var i in items.Where(i => !Contains(safe, i.r, 2)).Take(15))
                report.AppendLine($"OUTSIDE_SAFE {i.kind} \"{i.text}\"  [{i.path}]");
            // Overlaps: buttons with buttons, texts with texts of another branch.
            var list = items.Where(i => i.kind == "button").ToList();
            int n = 0;
            for (int a = 0; a < list.Count && n < 20; a++)
                for (int b = a + 1; b < list.Count && n < 20; b++)
                    if (Covers(list[a], list[b])) { report.AppendLine($"OVERLAP_BUTTONS \"{list[a].text}\" x \"{list[b].text}\"  [{list[a].path}] [{list[b].path}]"); n++; }
            var texts = items.Where(i => i.kind == "text").ToList();
            n = 0;
            for (int a = 0; a < texts.Count && n < 20; a++)
                for (int b = a + 1; b < texts.Count && n < 20; b++)
                    if (Covers(texts[a], texts[b])) { report.AppendLine($"OVERLAP_TEXT \"{texts[a].text}\" x \"{texts[b].text}\"  [{texts[a].path}] [{texts[b].path}]"); n++; }
        }

        // Children of the same element (an icon and its label) are allowed to share space.
        static bool Covers(Item a, Item b)
        {
            if (a.path.StartsWith(b.path) || b.path.StartsWith(a.path)) return false;
            var i = Rect.MinMaxRect(Mathf.Max(a.r.xMin, b.r.xMin), Mathf.Max(a.r.yMin, b.r.yMin), Mathf.Min(a.r.xMax, b.r.xMax), Mathf.Min(a.r.yMax, b.r.yMax));
            if (i.width <= 0 || i.height <= 0) return false;
            float small = Mathf.Min(a.r.width * a.r.height, b.r.width * b.r.height);
            return i.width * i.height > small * .25f;
        }

        static bool Contains(Rect outer, Rect inner, float tolerance) =>
            inner.xMin >= outer.xMin - tolerance && inner.yMin >= outer.yMin - tolerance && inner.xMax <= outer.xMax + tolerance && inner.yMax <= outer.yMax + tolerance;

        // Clipped away by a scroll view or a mask: not on screen.
        static bool Hidden(Component c)
        {
            var group = c.GetComponentInParent<CanvasGroup>();
            if (group && group.alpha < .05f) return true;
            var rt = (RectTransform)c.transform;
            var mask = c.GetComponentInParent<RectMask2D>();
            if (mask && mask.transform != c.transform)
            {
                var a = ScreenRect(rt, null); var m = ScreenRect(mask.rectTransform, null);
                if (!a.Overlaps(m)) return true;
            }
            return false;
        }

        static Rect ScreenRect(RectTransform rt, Camera cam)
        {
            var c = new Vector3[4]; rt.GetWorldCorners(c);
            Vector2 min = new Vector2(float.MaxValue, float.MaxValue), max = new Vector2(float.MinValue, float.MinValue);
            foreach (var w in c) { var s = RectTransformUtility.WorldToScreenPoint(cam, w); min = Vector2.Min(min, s); max = Vector2.Max(max, s); }
            return Rect.MinMaxRect(min.x, min.y, max.x, max.y);
        }

        static string Label(Selectable s)
        {
            var t = s.GetComponentInChildren<TMP_Text>();
            return t ? Clip(t.text) : s.name;
        }

        static string Clip(string s)
        {
            s = System.Text.RegularExpressions.Regex.Replace(s ?? "", "<[^>]+>", "").Replace("\n", " ").Trim();
            return s.Length > 40 ? s.Substring(0, 40) + "…" : s;
        }

        static string NodePath(Transform t)
        {
            var parts = new List<string>();
            for (int i = 0; t && i < 6; i++, t = t.parent) parts.Add(t.name);
            parts.Reverse();
            return string.Join("/", parts);
        }
    }
}
#endif
