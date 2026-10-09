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
    // First screen on desktop: "Jogar" starts the real game (its own save), "Idioma" picks the game's language
    // (PT, EN, ES, FR, DE; saved for the next time) and "Modo edição" opens the map editor on a separate sandbox
    // save. CHECKOUT_START=play|edit skips the screen (automated runs).
    public class CheckoutStartMenu : MonoBehaviour
    {
        public static bool EditMode { get; private set; }
        // Visual QA runs (Logs/autotest.txt asks for "events…"): no menu, and a copy of the save so the player's game is untouched.
        public static bool QaMode { get; private set; }
        public static bool Chosen { get; private set; }
        public static bool Showing => current;
        static CheckoutStartMenu current;
        static bool returning, hooked;
        RectTransform root, page; TextMeshProUGUI subtitle, hint; MarketSimulation simulation; float orbit; bool release, languages;

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

            var title = U.Label(root, "Title", K.Headline, 92, "E0B040"); U.At(title.rectTransform, new Vector2(.5f, 1), new Vector2(1200, 120), new Vector2(0, -170));
            title.text = "CHECKOUT";
            subtitle = U.Label(root, "Subtitle", K.Label, 30, "FFFFFF"); U.At(subtitle.rectTransform, new Vector2(.5f, 1), new Vector2(1200, 50), new Vector2(0, -245));
            hint = U.Label(root, "Hint", K.Body, 18, "BFD0E8"); U.At(hint.rectTransform, new Vector2(.5f, 0), new Vector2(1200, 40), new Vector2(0, 60));
            ShowMain();
        }

        // ── Main screen: Jogar · Idioma · (Modo edição) ───────────────────────────────────────────────────
        void ShowMain()
        {
            languages = false;
            Clear();
            subtitle.text = L("Supermercado Simulator");
            int count = release ? 2 : 3; float width = count == 3 ? 420 : 460, gap = count == 3 ? 450 : 520;
            float X(int i) => (i - (count - 1) * .5f) * gap;
            Option(new Vector2(X(0), -40), width, L("Jogar"), L("Continue o seu mercado de onde parou."), null, "Icons/market", "success", () => Choose(false));
            Option(new Vector2(X(1), -40), width, L("Idioma"), L("Escolha o idioma do jogo."), CheckoutI18n.NameOf(CheckoutI18n.Language), "Icons/globe", "primary", ShowLanguages);
            if (!release) Option(new Vector2(X(2), -40), width, L("Modo edição"), L("Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."), null, "Icons/hammer", "secondary", () => Choose(true));
            hint.text = L(release ? "Enter = Jogar" : "Enter = Jogar   •   E = Modo edição") + "   •   " + L("L = Idioma");
        }

        // ── Language screen: every language written in its own language; the pick applies at once ─────────
        void ShowLanguages()
        {
            languages = true;
            Clear();
            subtitle.text = L("Escolha o idioma do jogo.");
            var edge = U.Shape(page, "Languages", "E0B040", 30, new Vector2(.5f, .5f), new Vector2(560, 560), new Vector2(0, -50));
            var face = U.Box(edge.transform, "Face", "1D2B4F", 28, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(4, 8); face.rectTransform.offsetMax = new Vector2(-4, -4);
            U.Icon(face.transform, "Icon", "Icons/globe", new Vector2(.5f, 1), new Vector2(84, 84), new Vector2(-110, -58));
            var name = U.Label(face.transform, "Name", K.Headline, 40, "FFFFFF", TMPro.TextAlignmentOptions.Left);
            U.At(name.rectTransform, new Vector2(.5f, 1), new Vector2(240, 56), new Vector2(64, -58)); name.text = L("Idioma");
            var list = CheckoutI18n.Languages;
            for (int i = 0; i < list.Length; i++)
            {
                var id = list[i].id; bool active = id == CheckoutI18n.Language;
                var b = CheckoutDesktopButton.Create(face.transform, 58, 24, 14);
                b.Apply(new DesktopButton { label = list[i].name, icon = active ? "Icons/success" : "", variant = active ? "success" : "secondary", enabled = true, active = false, action = "", args = "[]", route = "", after = "", ok = "", fail = "", badge = "" });
                b.Clicked = _ => Pick(id);
                U.At((RectTransform)b.transform, new Vector2(.5f, 1), new Vector2(420, 58), new Vector2(0, -136 - i * 70));
            }
            var back = U.Button(face.transform, L("Voltar"), "primary", ShowMain, 56, 22);
            U.At((RectTransform)back.transform, new Vector2(.5f, 0), new Vector2(240, 56), new Vector2(0, 46));
            hint.text = L("Esc = Voltar") + "   •   1–5";
        }

        void Pick(string id)
        {
            CheckoutI18n.SetLanguage(id);
            ShowLanguages(); // the menu itself switches language at once
        }

        static string L(string text) => CheckoutI18n.T(text);

        void Clear()
        {
            if (page) Destroy(page.gameObject);
            page = CheckoutDesktopCard.Node("Page", root); U.Stretch(page, Vector2.zero, Vector2.one);
        }

        void Option(Vector2 offset, float width, string label, string text, string badge, string icon, string variant, Action onClick)
        {
            var edge = U.Shape(page, label, "E0B040", 30, new Vector2(.5f, .5f), new Vector2(width, 380), offset);
            var face = U.Box(edge.transform, "Face", "1D2B4F", 28, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(4, 8); face.rectTransform.offsetMax = new Vector2(-4, -4);
            U.Icon(face.transform, "Icon", icon, new Vector2(.5f, 1), new Vector2(96, 96), new Vector2(0, -78));
            var name = U.Label(face.transform, "Name", K.Headline, 40, "FFFFFF"); U.At(name.rectTransform, new Vector2(.5f, 1), new Vector2(width - 40, 56), new Vector2(0, -164));
            name.text = label;
            var desc = U.Label(face.transform, "Text", K.Body, 19, "BFD0E8"); desc.textWrappingMode = TextWrappingModes.Normal; desc.overflowMode = TextOverflowModes.Truncate;
            U.At(desc.rectTransform, new Vector2(.5f, 1), new Vector2(width - 70, 90), new Vector2(0, -236)); desc.text = text;
            // Idioma: the language in use, as a gold pill under the text.
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

        void OnDestroy() { if (current == this) current = null; }

        void Update()
        {
            if (Chosen) return;
            if (languages)
            {
                if (Input.GetKeyDown(KeyCode.Escape) || Input.GetKeyDown(KeyCode.Backspace) || Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter)) ShowMain();
                else for (int i = 0; i < CheckoutI18n.Languages.Length; i++)
                    if (Input.GetKeyDown(KeyCode.Alpha1 + i) || Input.GetKeyDown(KeyCode.Keypad1 + i)) { Pick(CheckoutI18n.Languages[i].id); break; }
            }
            else
            {
                if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter)) { Choose(false); return; }
                if (!release && Input.GetKeyDown(KeyCode.E)) { Choose(true); return; }
                if (Input.GetKeyDown(KeyCode.L)) ShowLanguages();
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
