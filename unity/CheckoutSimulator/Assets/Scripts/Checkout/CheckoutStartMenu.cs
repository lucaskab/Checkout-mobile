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
    // First screen on desktop: "Jogar" starts the real game (its own save), "Modo edição" opens the map editor
    // on a separate sandbox save. CHECKOUT_START=play|edit skips the screen (automated runs).
    public class CheckoutStartMenu : MonoBehaviour
    {
        public static bool EditMode { get; private set; }
        public static bool Chosen { get; private set; }
        public static bool Showing => current;
        static CheckoutStartMenu current;
        static bool returning, hooked;
        RectTransform root; MarketSimulation simulation; float orbit;

        public static void Show(GameObject bridge)
        {
            if (!hooked) { hooked = true; SceneManager.sceneLoaded += Reloaded; }
            Chosen = false;
            var env = Environment.GetEnvironmentVariable("CHECKOUT_START");
            if (env == "play" || env == "edit") { Launch(bridge, env == "edit"); return; }
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
            root = U.Canvas(transform, "CheckoutStartMenu", 300);
            var shade = U.Box(root, "Shade", "0F1830", 0, Vector2.zero, Vector2.one); shade.color = new Color(.06f, .09f, .19f, .8f); shade.raycastTarget = true;

            var title = U.Label(root, "Title", K.Headline, 92, "E0B040"); U.At(title.rectTransform, new Vector2(.5f, 1), new Vector2(1200, 120), new Vector2(0, -170));
            title.text = "CHECKOUT";
            var sub = U.Label(root, "Subtitle", K.Label, 30, "FFFFFF"); U.At(sub.rectTransform, new Vector2(.5f, 1), new Vector2(1200, 50), new Vector2(0, -245));
            sub.text = "Supermercado Simulator";

            Option(new Vector2(-270, -40), "Jogar", "Continue o seu mercado de onde parou.", "Icons/market", "success", () => Choose(false));
            Option(new Vector2(270, -40), "Modo edição", "Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado.", "Icons/hammer", "primary", () => Choose(true));

            var hint = U.Label(root, "Hint", K.Body, 18, "BFD0E8"); U.At(hint.rectTransform, new Vector2(.5f, 0), new Vector2(1200, 40), new Vector2(0, 60));
            hint.text = "Enter = Jogar   •   E = Modo edição";
        }

        void Option(Vector2 offset, string label, string text, string icon, string variant, Action onClick)
        {
            var edge = U.Shape(root, label, "E0B040", 30, new Vector2(.5f, .5f), new Vector2(480, 380), offset);
            var face = U.Box(edge.transform, "Face", "1D2B4F", 28, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(4, 8); face.rectTransform.offsetMax = new Vector2(-4, -4);
            U.Icon(face.transform, "Icon", icon, new Vector2(.5f, 1), new Vector2(96, 96), new Vector2(0, -78));
            var name = U.Label(face.transform, "Name", K.Headline, 40, "FFFFFF"); U.At(name.rectTransform, new Vector2(.5f, 1), new Vector2(440, 56), new Vector2(0, -164));
            name.text = label;
            var desc = U.Label(face.transform, "Text", K.Body, 19, "BFD0E8"); desc.textWrappingMode = TextWrappingModes.Normal; desc.overflowMode = TextOverflowModes.Truncate;
            U.At(desc.rectTransform, new Vector2(.5f, 1), new Vector2(410, 90), new Vector2(0, -236)); desc.text = text;
            var b = U.Button(face.transform, label, variant, onClick, 64, 24);
            U.At((RectTransform)b.transform, new Vector2(.5f, 0), new Vector2(300, 64), new Vector2(0, 56));
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
            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter)) { Choose(false); return; }
            if (Input.GetKeyDown(KeyCode.E)) { Choose(true); return; }
            // The map turns slowly behind the menu.
            if (simulation)
            {
                orbit += Time.unscaledDeltaTime * .12f;
                simulation.Focus(new Vector3(Mathf.Cos(orbit) * 7f, 0, 6 + Mathf.Sin(orbit) * 5f), 24);
            }
        }
    }
}
