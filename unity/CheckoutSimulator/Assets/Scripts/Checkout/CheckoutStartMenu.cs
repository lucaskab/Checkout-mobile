using System;
using TMPro;
using MarketDay;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // First screen on desktop: "Jogar" starts the real game (its own save), "Opções" opens the settings window
    // (CheckoutSettings, also reachable in the game: music / sound-effects volume and the game's language, PT, EN,
    // ES, FR, DE, saved for the next time) and "Modo edição" opens the map editor on a separate sandbox save. CHECKOUT_START=play|edit skips the screen (automated runs).
    public class CheckoutStartMenu : MonoBehaviour
    {
        public static bool EditMode { get; private set; }
        // Visual QA runs (Logs/autotest.txt asks for "events…"): no menu, and a copy of the save so the player's game is untouched.
        public static bool QaMode { get; private set; }
        public static bool Chosen { get; private set; }
        public static bool Showing => current;
        static CheckoutStartMenu current;
        static bool returning, hooked;
        RectTransform root, page; TextMeshProUGUI subtitle, hint; MarketSimulation simulation; float orbit; bool release;

        public static void Show(GameObject bridge)
        {
            if (!hooked) { hooked = true; SceneManager.sceneLoaded += Reloaded; }
            Chosen = false;
            var env = Environment.GetEnvironmentVariable("CHECKOUT_START");
            if (env == "play" || env == "edit") { Launch(bridge, env == "edit"); return; }
            try { QaMode = System.IO.File.Exists("Logs/autotest.txt") && System.IO.File.ReadAllText("Logs/autotest.txt").Contains("events"); } catch { QaMode = false; }
            if (QaMode) { Launch(bridge, false); return; }
            bridge.AddComponent<CheckoutStartMenu>().Build();
        }

        // "Sair" in the editor (or a later "menu" button): the scene starts over and the choice is asked again.
        public static void ReturnToMenu()
        {
            returning = true;
            var scene = SceneManager.GetActiveScene();
            SceneManager.LoadScene(scene.buildIndex >= 0 ? scene.buildIndex : 0);
        }

        static void Reloaded(Scene scene, LoadSceneMode mode)
        {
            if (!returning) return;
            returning = false;
            CheckoutMapDesign.Load(); // unsaved editor changes are dropped
            var bridge = FindAnyObjectByType<CheckoutBridge>();
            if (bridge) bridge.gameObject.AddComponent<CheckoutStartMenu>().Build();
        }

        static void Launch(GameObject bridge, bool edit)
        {
            EditMode = edit; Chosen = true;
            CheckoutMapDesign.Load();
            bridge.AddComponent<CheckoutDesktopHost>();
        }

        void Build()
        {
            current = this; Chosen = false;
            simulation = FindAnyObjectByType<MarketSimulation>();
            release = CheckoutDesktopHost.IsRelease;
            root = U.Canvas(transform, "CheckoutStartMenu", 300);
            var shade = U.Box(root, "Shade", "0F1830", 0, Vector2.zero, Vector2.one); shade.color = new Color(.06f, .09f, .19f, .8f); shade.raycastTarget = true;
            U.Stretch(shade.rectTransform, Vector2.zero, Vector2.one, new Vector2(-900, -900), new Vector2(900, 900)); // past the safe area: the whole screen

            // Phones have a short screen: the title sits higher and smaller, the cards below it (see Clear: page scale).
            bool phone = CheckoutScreen.Handheld;
            var title = U.Label(root, "Title", K.Headline, phone ? 64 : 92, "E0B040"); U.At(title.rectTransform, new Vector2(.5f, 1), new Vector2(1200, phone ? 84 : 120), new Vector2(0, phone ? -52 : -170));
            title.text = "CHECKOUT";
            subtitle = U.Label(root, "Subtitle", K.Label, 30, "FFFFFF"); U.At(subtitle.rectTransform, new Vector2(.5f, 1), new Vector2(1200, 50), new Vector2(0, phone ? -104 : -245));
            hint = U.Label(root, "Hint", K.Body, 18, "BFD0E8"); U.At(hint.rectTransform, new Vector2(.5f, 0), new Vector2(1200, 40), new Vector2(0, 60));
            CheckoutI18n.Changed += Relabel;
            ShowMain();
        }

        // ── Main screen: Jogar · Opções · (Modo edição) ──────────────────────────────────────────────────
        // Lucas 19/10: the language moved into Opções (tab "Idioma"); the card's text says so. No pill with the
        // language in use: the player is reading it.
        void ShowMain()
        {
            Clear();
            subtitle.text = L("Supermercado Simulator");
            int count = release ? 2 : 3; float width = count == 3 ? 380 : 440, gap = count == 3 ? 420 : 480;
            float X(int i) => (i - (count - 1) * .5f) * gap;
            Option(new Vector2(X(0), -40), width, L("Jogar"), L("Continue o seu mercado de onde parou."), null, "Icons/market", "success", () => Choose(false));
            Option(new Vector2(X(1), -40), width, L("Opções"), L("Música, sons, idioma e conta."), null, "Icons/settings", "coin", () => CheckoutSettings.Show());
            if (!release) Option(new Vector2(X(2), -40), width, L("Modo edição"), L("Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."), null, "Icons/hammer", "secondary", () => Choose(true));
            hint.text = L(release ? "Enter = Jogar" : "Enter = Jogar   •   E = Modo edição") + "   •   " + L("O = Opções");
        }

        // A language picked in Opções: the cards are written again in it.
        void Relabel() { if (!Chosen && root) ShowMain(); }

        static string L(string text) => CheckoutI18n.T(text);

        void Clear()
        {
            if (page) Destroy(page.gameObject);
            page = CheckoutDesktopCard.Node("Page", root); U.Stretch(page, Vector2.zero, Vector2.one);
            // Phones: the cards a little smaller and lower, clear of the title.
            if (CheckoutScreen.Handheld) { page.localScale = Vector3.one * .82f; page.anchoredPosition = new Vector2(0, -36); }
        }

        void Option(Vector2 offset, float width, string label, string text, string badge, string icon, string variant, Action onClick)
        {
            var edge = U.Shape(page, label, "E0B040", 30, new Vector2(.5f, .5f), new Vector2(width, 380), offset);
            var face = U.Box(edge.transform, "Face", "1D2B4F", 28, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(4, 8); face.rectTransform.offsetMax = new Vector2(-4, -4);
            U.Icon(face.transform, "Icon", icon, new Vector2(.5f, 1), new Vector2(96, 96), new Vector2(0, -78));
            var name = U.Label(face.transform, "Name", K.Headline, 40, "FFFFFF"); U.At(name.rectTransform, new Vector2(.5f, 1), new Vector2(width - 40, 56), new Vector2(0, -164));
            name.text = label; name.enableAutoSizing = true; name.fontSizeMin = 26; name.fontSizeMax = 40; // long names ("Bearbeitungsmodus") on the narrower cards
            var desc = U.Label(face.transform, "Text", K.Body, 19, "BFD0E8"); desc.textWrappingMode = TextWrappingModes.Normal; desc.overflowMode = TextOverflowModes.Truncate;
            U.At(desc.rectTransform, new Vector2(.5f, 1), new Vector2(width - 70, 90), new Vector2(0, -236)); desc.text = text;
            // A gold pill under the text (no card uses one now).
            if (!string.IsNullOrEmpty(badge)) { U.At(desc.rectTransform, new Vector2(.5f, 1), new Vector2(width - 70, 40), new Vector2(0, -214)); var pill = U.Shape(face.transform, "Current", "E0B040", 18, new Vector2(.5f, 1), new Vector2(200, 36), new Vector2(0, -258)); var pt = U.Label(pill.transform, "Text", K.Label, 20, "1D2B4F"); U.Stretch(pt.rectTransform, Vector2.zero, Vector2.one); pt.text = badge; }
            var b = U.Button(face.transform, label, variant, onClick, 64, 24);
            U.At((RectTransform)b.transform, new Vector2(.5f, 0), new Vector2(Mathf.Min(300, width - 80), 64), new Vector2(0, 56));
            U.Tap(face, onClick);
        }

        void Choose(bool edit)
        {
            if (Chosen) return;
            if (simulation) simulation.HomeCamera();
            Launch(gameObject, edit);
            Destroy(root.gameObject); Destroy(this);
        }

        void OnDestroy() { CheckoutI18n.Changed -= Relabel; if (current == this) current = null; }

        void Update()
        {
            if (Chosen) return;
            if (CheckoutSettings.Open) { } // the Opções window is on top: its keys are its own
            else
            {
                if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter)) { Choose(false); return; }
                if (!release && Input.GetKeyDown(KeyCode.E)) { Choose(true); return; }
                if (Input.GetKeyDown(KeyCode.O)) CheckoutSettings.Show();
                if (Input.GetKeyDown(KeyCode.L)) CheckoutSettings.Show("idioma");
            }
            // The map turns slowly behind the menu.
            if (simulation)
            {
                orbit += Time.unscaledDeltaTime * .12f;
                simulation.Focus(new Vector3(Mathf.Cos(orbit) * 7f, 0, 6 + Mathf.Sin(orbit) * 5f), 24);
            }
        }
    }
}
