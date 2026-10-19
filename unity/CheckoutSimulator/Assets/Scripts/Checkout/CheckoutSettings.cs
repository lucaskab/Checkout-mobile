using System;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout
{
    // "Opções" window (Lucas 18/10): music volume, sound-effects volume and an on/off switch for each. Opens from the
    // start screen (card "Opções", key O) and during the game (gear button next to "?"; on phones in the toolbar).
    // It sits above the HUD and the mini-games; the game keeps running behind it. Settings live in CheckoutAudio.
    // Lucas 19/10: tabs, so more settings fit later. "Sons" (the two volumes), "Idioma" (the language picker that
    // used to be its own card on the start screen; a pick applies at once, in the game too: the host retranslates)
    // and "Conta" (sign in with Google, or Apple on the iPhone, so the progress is saved in the cloud: CheckoutCloud).
    [DefaultExecutionOrder(1000)] // after the HUD and the start screen: they see Open on the frame Esc closes it
    public sealed class CheckoutSettings : MonoBehaviour
    {
        public static bool Open => current;
        static CheckoutSettings current;
        // The tab shown when the window opens: the last one used.
        static string tab = "sons";

        class Row { public Slider slider; public TextMeshProUGUI value; public CheckoutDesktopButton toggle; public Image icon; }
        Row music, effects;
        RectTransform canvas, page, window;
        AudioSource preview;

        public static void Show() => Show(tab);

        public static void Show(string open)
        {
            tab = open == "idioma" || open == "conta" ? open : "sons";
            if (current) { current.BuildPage(false); return; }
            current = new GameObject("CheckoutSettings").AddComponent<CheckoutSettings>();
            current.Build();
        }

        public static void Hide() { if (current) Destroy(current.gameObject); }

        static string L(string text) => CheckoutI18n.T(text);

        void Build()
        {
            canvas = U.Canvas(transform, "CheckoutSettings", 450); // over the HUD (50), mini-games (80-96) and the start screen (300)
            // A short sound to hear the effects volume (it goes through the listener like every effect).
            preview = gameObject.AddComponent<AudioSource>(); preview.playOnAwake = false;
            CheckoutAudio.Changed += Refresh;
            CheckoutI18n.Changed += Relabel;
            CheckoutCloud.Changed += AccountChanged;
            BuildPage(true);
        }

        // The whole window; built again on a tab switch or a language change (every text is a Portuguese key).
        void BuildPage(bool pop)
        {
            if (page) Destroy(page.gameObject);
            music = effects = null;
            page = N.Node("Page", canvas); U.Stretch(page, Vector2.zero, Vector2.one);
            // Dim layer: a click outside the window closes it (the window is its sibling, so its clicks stay inside).
            var dim = U.Box(page, "Dim", "000000", 0, Vector2.zero, Vector2.one); dim.color = new Color(.14f, .09f, .05f, .62f); U.Bleed(dim); U.Tap(dim, Hide);

            var edge = U.Shape(page, "Window", "D4B482", 30, new Vector2(.5f, .5f), new Vector2(820, 640)); edge.raycastTarget = true;
            window = edge.rectTransform;
            var face = U.Box(edge.transform, "Face", "FFF7EC", 28, Vector2.zero, Vector2.one); face.rectTransform.offsetMin = new Vector2(4, 9); face.rectTransform.offsetMax = new Vector2(-4, -4);
            var f = face.transform;

            // Header: gear, title, subtitle and the close button.
            U.Icon(f, "Icon", "Icons/settings", new Vector2(.5f, 1), new Vector2(72, 72), new Vector2(-300, -62));
            var title = U.Label(f, "Title", K.Headline, 44, "4A3624", TextAlignmentOptions.Left);
            U.At(title.rectTransform, new Vector2(.5f, 1), new Vector2(520, 56), new Vector2(0, -48)); title.text = L("Opções");
            var subtitle = U.Label(f, "Subtitle", K.Body, 21, "8A7560", TextAlignmentOptions.Left);
            U.At(subtitle.rectTransform, new Vector2(.5f, 1), new Vector2(520, 32), new Vector2(0, -92));
            subtitle.text = L(tab == "idioma" ? "Escolha o idioma do jogo." : tab == "conta" ? "Guarde o seu progresso na nuvem." : "Ajuste a música e os sons do jogo.");
            var close = U.Button(f, "X", "danger", Hide, 60, 26);
            U.At((RectTransform)close.transform, new Vector2(1, 1), new Vector2(64, 64), new Vector2(-50, -50));

            // Tabs.
            Tab(f, "sons", L("Sons"), "Icons/sound", new Vector2(-248, -158));
            Tab(f, "idioma", L("Idioma"), "Icons/globe", new Vector2(0, -158));
            Tab(f, "conta", L("Conta"), "Icons/smartphone", new Vector2(248, -158));
            var line = U.Box(f, "TabLine", "E7D6BD", 2, new Vector2(.5f, 1), new Vector2(.5f, 1)); U.At(line.rectTransform, new Vector2(.5f, 1), new Vector2(740, 4), new Vector2(0, -192));

            if (tab == "idioma") BuildLanguages(f);
            else if (tab == "conta") BuildAccount(f);
            else
            {
                music = BuildRow(f, new Vector2(0, -280), L("Música"), K.C("8B5C9E"),
                    v => { if (v > 0 && !CheckoutAudio.MusicOn) CheckoutAudio.MusicOn = true; CheckoutAudio.MusicVolume = v; },
                    () => CheckoutAudio.MusicOn = !CheckoutAudio.MusicOn, null);
                effects = BuildRow(f, new Vector2(0, -445), L("Efeitos sonoros"), K.C("2E8CAE"),
                    v => { if (v > 0 && !CheckoutAudio.EffectsOn) CheckoutAudio.EffectsOn = true; CheckoutAudio.EffectsVolume = v; },
                    () => { CheckoutAudio.EffectsOn = !CheckoutAudio.EffectsOn; Sample(); }, Sample);
            }

            var done = U.Button(f, L("Fechar"), "success", Hide, 64, 24);
            U.At((RectTransform)done.transform, new Vector2(.5f, 0), new Vector2(260, 64), new Vector2(0, 48));

            Refresh();
            if (pop) StartCoroutine(U.Pop(window, 1.04f, .22f));
        }

        void Tab(Transform parent, string id, string label, string icon, Vector2 offset)
        {
            bool on = tab == id;
            var b = CheckoutDesktopButton.Create(parent, 58, 24, 16);
            b.Apply(new DesktopButton { label = label, icon = icon, variant = on ? "coin" : "secondary", enabled = true, active = on, action = "", args = "[]", route = "", after = "", ok = "", fail = "", badge = "" });
            b.Clicked = _ => { if (tab == id) return; tab = id; BuildPage(false); };
            U.At((RectTransform)b.transform, new Vector2(.5f, 1), new Vector2(226, 58), offset);
        }

        // ── Idioma: every language written in its own language; the pick applies at once ───────────────────
        void BuildLanguages(Transform parent)
        {
            var list = CheckoutI18n.Languages;
            for (int i = 0; i < list.Length; i++)
            {
                var id = list[i].id; bool active = id == CheckoutI18n.Language;
                var b = CheckoutDesktopButton.Create(parent, 64, 26, 16);
                b.Apply(new DesktopButton { label = list[i].name, icon = active ? "Icons/success" : "Icons/globe", variant = active ? "success" : "secondary", enabled = true, active = false, action = "", args = "[]", route = "", after = "", ok = "", fail = "", badge = "" });
                b.Clicked = _ => Pick(id);
                // Two columns; an odd last one sits in the middle.
                int row = i / 2; bool alone = i == list.Length - 1 && list.Length % 2 == 1;
                float x = alone ? 0 : (i % 2 == 0 ? -182 : 182);
                U.At((RectTransform)b.transform, new Vector2(.5f, 1), new Vector2(340, 64), new Vector2(x, -250 - row * 84));
            }
        }

        // ── Conta: Google (and Apple on the iPhone), what is saved, sign out, delete ───────────────────────────
        float deleteArmedUntil; string accountShown;
        void AccountChanged()
        {
            // Redraw only when what the tab shows changed (CheckoutCloud reports every sync).
            var cloud = CheckoutCloud.Active;
            var key = cloud ? cloud.State + "|" + cloud.Provider + "|" + cloud.Error + "|" + cloud.LastSyncAt : "";
            if (tab == "conta" && canvas && key != accountShown) BuildPage(false);
        }

        void BuildAccount(Transform parent)
        {
            var cloud = CheckoutCloud.Active;
            accountShown = cloud ? cloud.State + "|" + cloud.Provider + "|" + cloud.Error + "|" + cloud.LastSyncAt : "";
            var card = U.Shape(parent, "Account", "FBEEDA", 22, new Vector2(.5f, 1), new Vector2(740, 300), new Vector2(0, -360));
            var c = card.transform;
            var icon = U.Icon(c, "Icon", "Icons/key", new Vector2(0, 1), new Vector2(84, 84), new Vector2(70, -66));
            var title = U.Label(c, "Title", K.Headline, 30, "4A3624", TextAlignmentOptions.Left);
            U.At(title.rectTransform, new Vector2(0, 1), new Vector2(560, 42), new Vector2(410, -44));
            title.enableAutoSizing = true; title.fontSizeMin = 20; title.fontSizeMax = 30;
            var text = U.Label(c, "Text", K.Body, 20, "8A7560", TextAlignmentOptions.TopLeft);
            text.textWrappingMode = TextWrappingModes.Normal;
            U.At(text.rectTransform, new Vector2(0, 1), new Vector2(560, 90), new Vector2(410, -116));
            var row = N.Node("Buttons", c); U.At(row, new Vector2(.5f, 0), new Vector2(700, 64), new Vector2(0, 52));
            var h = N.Row(row.gameObject, 12); h.childAlignment = TextAnchor.MiddleCenter; h.childForceExpandWidth = true;

            string state = cloud ? cloud.State : "start";
            bool signedIn = cloud && !string.IsNullOrEmpty(cloud.Provider) && state != "signed-out";
            if (!cloud)
            {
                // The start screen: the cloud starts with the game.
                title.text = L("Sua conta");
                text.text = L("Toque em Jogar e volte aqui para entrar e guardar o seu progresso na nuvem.");
                return;
            }
            if (state == "unavailable")
            {
                title.text = L("Sua conta");
                text.text = L("O login não está disponível nesta versão do jogo.");
                return;
            }
            if (state == "conflict")
            {
                icon.sprite = K.Icon("Icons/warning");
                title.text = L("Qual progresso continua?");
                text.text = L("Este aparelho e a sua conta têm progressos diferentes. Escolha qual continua.");
                AccountButton(row, L("Escolher"), "Icons/warning", "coin", () => { Hide(); CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"!conta\"}"); });
                return;
            }
            if (!signedIn)
            {
                title.text = L("Salve o seu progresso");
                var lines = L("Guarde o mercado, as moedas e os diamantes na nuvem. Trocou de celular? É só entrar com a mesma conta.");
                if (!string.IsNullOrEmpty(cloud.Error)) lines += "\n<color=#C0401F>" + L(cloud.Error) + "</color>";
                text.text = lines;
                bool busy = state == "signing-in";
                foreach (var provider in CheckoutCloud.Providers)
                {
                    bool apple = provider == "apple";
                    var b = AccountButton(row, L(busy ? "Entrando…" : apple ? "Iniciar sessão com a Apple" : "Entrar com Google"), apple ? "" : "Icons/key", apple ? "apple" : "success", () => cloud.RequestSignIn(provider), !busy);
                    if (apple) b.SetIconSprite(CheckoutCloud.AppleLogo());
                }
                return;
            }
            // Signed in: who, when it was saved, save now, sign out, delete (asks twice).
            bool appleAccount = cloud.Provider == "apple";
            var logo = appleAccount ? CheckoutCloud.AppleLogo() : null;
            icon.sprite = K.Icon("Icons/success");
            title.text = !string.IsNullOrEmpty(cloud.PlayerName) ? cloud.PlayerName : L(appleAccount ? "Conta Apple" : "Conta Google");
            var when = cloud.LastSyncAt > 0 ? System.DateTimeOffset.FromUnixTimeMilliseconds(cloud.LastSyncAt).ToLocalTime().ToString("HH:mm") : "";
            string line = state == "syncing" ? L("Salvando na nuvem…")
                : state == "offline" ? L("Sem conexão: o progresso fica neste aparelho e vai para a nuvem quando a internet voltar.")
                : state == "error" ? L(string.IsNullOrEmpty(cloud.Error) ? "Não deu para falar com o servidor. Tente de novo daqui a pouco." : cloud.Error)
                : when.Length > 0 ? L("Tudo salvo na nuvem") + " · " + when : L("Conectado à nuvem.");
            text.text = (string.IsNullOrEmpty(cloud.Email) ? "" : cloud.Email + "\n") + line;
            AccountButton(row, L(state == "syncing" ? "Salvando…" : "Salvar agora"), "Icons/coin", "primary", cloud.RequestSync, state != "syncing");
            AccountButton(row, L("Sair"), "", "secondary", cloud.RequestSignOut);
            bool armed = Time.unscaledTime < deleteArmedUntil;
            AccountButton(row, L(armed ? "Toque de novo" : "Apagar conta"), "Icons/warning", "danger", () =>
            {
                if (Time.unscaledTime < deleteArmedUntil) { deleteArmedUntil = 0; cloud.RequestDelete(); }
                else { deleteArmedUntil = Time.unscaledTime + 6f; BuildPage(false); }
            });
            if (logo) { icon.sprite = logo; icon.color = K.C("111111"); }
        }

        CheckoutDesktopButton AccountButton(Transform row, string label, string icon, string variant, Action click, bool enabled = true)
        {
            var b = CheckoutDesktopButton.Create(row, 60, 21, 16);
            b.Apply(new DesktopButton { label = label, icon = icon, variant = variant, enabled = enabled, active = false, action = "", args = "[]", route = "", after = "", ok = "", fail = "", badge = "" });
            b.Clicked = _ => { if (enabled) click(); };
            return b;
        }

        static void Pick(string id)
        {
            if (id == CheckoutI18n.Language) return;
            CheckoutI18n.SetLanguage(id); // Changed → this window relabels itself, as do the HUD's own texts
            // In the game, the host translates the pages and names: tell it (on the start screen there is no host yet;
            // it starts in the language picked here).
            if (CheckoutDesktopHost.Active) CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"" + id + "\"}");
        }

        void Relabel() { if (canvas) BuildPage(false); }

        // A card with the big icon, the name and percentage, the slider and the on/off button.
        Row BuildRow(Transform parent, Vector2 offset, string name, Color fill, Action<float> changed, Action toggle, Action released)
        {
            var row = new Row();
            var card = U.Shape(parent, "Row", "FBEEDA", 22, new Vector2(.5f, 1), new Vector2(740, 150), offset);
            var c = card.transform;
            row.icon = U.Icon(c, "Icon", "", new Vector2(.5f, .5f), new Vector2(92, 92), new Vector2(-300, 0));
            var label = U.Label(c, "Name", K.Headline, 30, "4A3624", TextAlignmentOptions.Left);
            U.At(label.rectTransform, new Vector2(.5f, .5f), new Vector2(260, 44), new Vector2(-100, 32)); label.text = name;
            label.enableAutoSizing = true; label.fontSizeMin = 20; label.fontSizeMax = 30; // "Efectos de sonido" and friends
            row.value = U.Label(c, "Value", K.Number, 24, "8A7560", TextAlignmentOptions.Right);
            U.At(row.value.rectTransform, new Vector2(.5f, .5f), new Vector2(110, 40), new Vector2(95, 32));
            row.slider = MakeSlider(c, fill, new Vector2(390, 48), new Vector2(-35, -28));
            row.slider.onValueChanged.AddListener(v => changed(v));
            if (released != null) row.slider.gameObject.AddComponent<CheckoutPointerUp>().Up = released;
            row.toggle = CheckoutDesktopButton.Create(c, 64, 22, 14);
            row.toggle.Clicked = _ => toggle();
            U.At((RectTransform)row.toggle.transform, new Vector2(.5f, .5f), new Vector2(180, 64), new Vector2(262, 0));
            return row;
        }

        // Rounded track, coloured fill up to the knob, and a round knob. Big enough to drag with a finger.
        static Slider MakeSlider(Transform parent, Color fillColor, Vector2 size, Vector2 offset)
        {
            var node = N.Node("Slider", parent); U.At(node, new Vector2(.5f, .5f), size, offset);
            var track = N.Image(node, "Track", K.C("E7D6BD"), 11); track.raycastTarget = true;
            U.Stretch(track.rectTransform, new Vector2(0, .5f), new Vector2(1, .5f), new Vector2(0, -11), new Vector2(0, 11));
            var fillArea = N.Node("FillArea", node);
            U.Stretch(fillArea, new Vector2(0, .5f), new Vector2(1, .5f), new Vector2(22, -11), new Vector2(-22, 11));
            var fill = N.Image(fillArea, "Fill", fillColor, 11);
            fill.rectTransform.anchorMin = Vector2.zero; fill.rectTransform.anchorMax = new Vector2(0, 1);
            fill.rectTransform.offsetMin = new Vector2(-22, 0); fill.rectTransform.offsetMax = Vector2.zero;
            var handleArea = N.Node("HandleArea", node); U.Stretch(handleArea, Vector2.zero, Vector2.one, new Vector2(22, 0), new Vector2(-22, 0));
            var knobEdge = N.Image(handleArea, "Knob", K.Border, 22);
            var knob = knobEdge.rectTransform; knob.anchorMin = Vector2.zero; knob.anchorMax = new Vector2(0, 1); knob.sizeDelta = new Vector2(44, -4); knob.anchoredPosition = Vector2.zero;
            var knobFace = N.Image(knobEdge.transform, "Face", Color.white, 19); U.Stretch(knobFace.rectTransform, Vector2.zero, Vector2.one, new Vector2(3, 5), new Vector2(-3, -2));
            var slider = node.gameObject.AddComponent<Slider>();
            slider.transition = Selectable.Transition.None; slider.navigation = new Navigation { mode = Navigation.Mode.None };
            slider.direction = UnityEngine.UI.Slider.Direction.LeftToRight; slider.minValue = 0; slider.maxValue = 1; slider.wholeNumbers = false;
            slider.fillRect = fill.rectTransform; slider.handleRect = knob; slider.targetGraphic = knobFace;
            return slider;
        }

        void Refresh()
        {
            if (music == null || effects == null) return;
            Show(music, CheckoutAudio.MusicVolume, CheckoutAudio.MusicOn, "Icons/music", "Icons/music-off", "Ligada", "Desligada");
            Show(effects, CheckoutAudio.EffectsVolume, CheckoutAudio.EffectsOn, "Icons/sound", "Icons/sound-off", "Ligados", "Desligados");
        }

        static void Show(Row row, float volume, bool on, string icon, string iconOff, string onLabel, string offLabel)
        {
            row.slider.SetValueWithoutNotify(volume);
            row.value.text = Mathf.RoundToInt(volume * 100) + "%";
            row.icon.sprite = K.Icon(on ? icon : iconOff);
            row.toggle.Apply(new DesktopButton { label = L(on ? onLabel : offLabel), icon = on ? icon : iconOff, variant = on ? "success" : "secondary", enabled = true, active = false, action = "", args = "[]", route = "", after = "", ok = "", fail = "", badge = "" });
            // Off: the slider fades so it reads as "silenced" (it still works: dragging it turns the sound back on).
            foreach (var g in row.slider.GetComponentsInChildren<Graphic>()) { var col = g.color; col.a = on ? 1 : .45f; g.color = col; }
            row.value.alpha = on ? 1 : .45f;
        }

        void Sample()
        {
            if (!CheckoutAudio.EffectsOn || !preview) return;
            var clip = U.Sfx("coin_" + UnityEngine.Random.Range(0, 3));
            if (!clip) clip = U.Sfx("tap");
            if (clip) preview.PlayOneShot(clip, .6f);
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.Escape)) Hide();
        }

        void OnDestroy()
        {
            CheckoutAudio.Changed -= Refresh;
            CheckoutI18n.Changed -= Relabel;
            CheckoutCloud.Changed -= AccountChanged;
            if (current == this) current = null;
        }
    }

    /// <summary>Calls Up when the finger or mouse lets go of the control (the effects slider plays a sample).</summary>
    public sealed class CheckoutPointerUp : MonoBehaviour, IPointerUpHandler
    {
        public Action Up;
        public void OnPointerUp(PointerEventData e) => Up?.Invoke();
    }
}
