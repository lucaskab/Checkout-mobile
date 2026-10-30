using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEngine;

namespace Checkout
{
    // The game's language. Every text is written in Portuguese; the other languages translate it on the way to
    // the screen with the catalog of src/i18n (the desktop host sends it after start, see CheckoutDesktopHost).
    // Same rules as src/i18n/translator.ts: exact text → pattern ("Faltam {0} itens") → the text split at its
    // separators, each piece on its own. Whatever the catalog does not know stays in Portuguese.
    public static class CheckoutI18n
    {
        public const string PrefKey = "checkout.language";

        /// <summary>Languages the player can pick, each written in its own language.</summary>
        public static readonly (string id, string name)[] Languages =
        {
            ("pt", "Português"), ("en", "English"), ("es", "Español"), ("fr", "Français"), ("de", "Deutsch"),
        };

        static string language;
        /// <summary>"pt", "en", "es", "fr" or "de" (saved; the first time it follows the computer's language).</summary>
        public static string Language
        {
            get
            {
                if (language != null) return language;
                var saved = PlayerPrefs.GetString(PrefKey, "");
                language = IsLanguage(saved) ? saved : FromSystem();
                return language;
            }
        }
        public static bool IsPortuguese => Language == "pt";
        public static event Action Changed;

        public static bool IsLanguage(string id) => Languages.Any(l => l.id == id);
        public static string NameOf(string id) { foreach (var l in Languages) if (l.id == id) return l.name; return id; }

        static string FromSystem()
        {
            switch (Application.systemLanguage)
            {
                case SystemLanguage.Portuguese: return "pt";
                case SystemLanguage.Spanish: return "es";
                case SystemLanguage.French: return "fr";
                case SystemLanguage.German: return "de";
                default: return "en";
            }
        }

        public static void SetLanguage(string id)
        {
            if (!IsLanguage(id)) id = "pt";
            PlayerPrefs.SetString(PrefKey, id); PlayerPrefs.Save();
            if (id == language) return;
            language = id; Build(null, null);
            Changed?.Invoke();
        }

        // ── Catalog ────────────────────────────────────────────────────────────────────────────────────────
        class Pattern { public Regex regex; public string target, probe; public int weight; }
        static readonly Dictionary<string, string> exact = new Dictionary<string, string>();
        static readonly Dictionary<string, string> upper = new Dictionary<string, string>();
        static readonly Dictionary<string, string> lower = new Dictionary<string, string>();
        static readonly List<Pattern> patterns = new List<Pattern>();
        static readonly Dictionary<string, string> cache = new Dictionary<string, string>();
        static bool built;

        static readonly Regex Slot = new Regex(@"\{(\d+)\}");
        static readonly Regex Glued = new Regex(@"\{(\d+)\}\{(\d+)\}");
        static readonly Regex Sentences = new Regex(@"((?<=[.!?…])\s+)");
        static readonly Regex Separators = new Regex(@"(\s+·\s+|\s*\n\s*|\s+•\s+|\s+—\s+|\s+\|\s+|:\s+|;\s+|\s+›\s+|\s{2,})");
        static readonly Regex ListSeparators = new Regex(@"(,\s+|\s+e\s+)");
        static readonly Regex Around = new Regex(@"^([^\p{L}]*)([\s\S]*?\p{L})([^\p{L}]*)$");
        static readonly Regex Letter = new Regex(@"\p{L}");

        /// <summary>The catalog of the current language, sent by the game host (keys are the Portuguese texts).</summary>
        public static void Load(string lang, string[] keys, string[] values)
        {
            if (keys == null || values == null || keys.Length != values.Length) return;
            if (IsLanguage(lang) && lang != Language) { language = lang; }
            Build(keys, values);
            Changed?.Invoke();
        }

        static void Build(string[] keys, string[] values)
        {
            exact.Clear(); upper.Clear(); lower.Clear(); patterns.Clear(); cache.Clear(); built = true;
            if (IsPortuguese) return;
            var entries = new List<KeyValuePair<string, string>>();
            // The start screen and the HUD's first frames need a few texts before the host is running.
            if (BuiltIn.TryGetValue(Language, out var own)) foreach (var pair in own) entries.Add(pair);
            if (keys != null) for (int i = 0; i < keys.Length; i++) entries.Add(new KeyValuePair<string, string>(keys[i], values[i]));
            var known = new HashSet<string>(entries.Select(e => e.Key));
            // A text of several sentences also teaches each sentence on its own.
            foreach (var e in entries.ToList())
            {
                var from = Pieces(Sentences, e.Key); var to = Pieces(Sentences, e.Value ?? "");
                if (from.Count < 2 || from.Count != to.Count) continue;
                for (int i = 0; i < from.Count; i++)
                {
                    string a = from[i], b = to[i];
                    var lead = Regex.Match(a, @"^\{\d+\}\s+");
                    if (lead.Success && b.StartsWith(lead.Value)) { a = a.Substring(lead.Length); b = b.Substring(lead.Length); }
                    if (!known.Contains(a) && SlotsOf(a) == SlotsOf(b)) { known.Add(a); entries.Add(new KeyValuePair<string, string>(a, b)); }
                }
            }
            bool keepNounCase = Language == "de";
            foreach (var e in entries)
            {
                string source = e.Key, target = e.Value;
                if (string.IsNullOrEmpty(source) || string.IsNullOrEmpty(target)) continue;
                for (var g = Glued.Match(source); g.Success; g = Glued.Match(source))
                {
                    if (!target.Contains(g.Value)) break;
                    source = source.Replace(g.Value, "{" + g.Groups[1].Value + "}");
                    target = target.Replace(g.Value, "{" + g.Groups[1].Value + "}");
                }
                if (Slot.IsMatch(source))
                {
                    var literal = Slot.Replace(source, "");
                    if (Letters(literal) < 3) continue;
                    var order = new List<int>(); var body = new System.Text.StringBuilder("^");
                    foreach (var piece in Regex.Split(source, @"(\{\d+\})"))
                    {
                        var slot = Regex.Match(piece, @"^\{(\d+)\}$");
                        if (slot.Success) { order.Add(int.Parse(slot.Groups[1].Value)); body.Append(@"((?:(?![.!?…]\s)[\s\S])+?)"); }
                        else body.Append(Regex.Escape(piece));
                    }
                    body.Append("$");
                    var probe = Regex.Split(source, @"\{\d+\}").OrderByDescending(p => p.Length).First();
                    var mapped = Slot.Replace(target, m => "{#" + order.IndexOf(int.Parse(m.Groups[1].Value)) + "}");
                    try { patterns.Add(new Pattern { regex = new Regex(body.ToString(), RegexOptions.CultureInvariant), target = mapped, probe = probe, weight = literal.Length }); } catch { }
                }
                else
                {
                    exact[source] = target;
                    var up = source.ToUpperInvariant();
                    if (up != source && !upper.ContainsKey(up)) upper[up] = target.ToUpperInvariant();
                    var first = source.Substring(0, 1);
                    if (first != first.ToLowerInvariant())
                    {
                        var low = first.ToLowerInvariant() + source.Substring(1);
                        if (!lower.ContainsKey(low)) lower[low] = keepNounCase ? target : target.Substring(0, 1).ToLowerInvariant() + target.Substring(1);
                    }
                }
            }
            patterns.Sort((a, b) => b.weight.CompareTo(a.weight));
        }

        static List<string> Pieces(Regex separator, string text)
        {
            var all = separator.Split(text); var list = new List<string>();
            for (int i = 0; i < all.Length; i += 2) list.Add(all[i]);
            return list;
        }
        static string SlotsOf(string text) => string.Join(",", Slot.Matches(text).Cast<Match>().Select(m => m.Value).OrderBy(v => v));
        static int Letters(string text) { int n = 0; foreach (var c in text) if (char.IsLetter(c)) n++; return n; }

        /// <summary>The text in the player's language (unchanged in Portuguese or when unknown).</summary>
        public static string T(string text)
        {
            if (string.IsNullOrEmpty(text) || IsPortuguese) return text;
            if (!built) Build(null, null);
            if (cache.TryGetValue(text, out var hit)) return hit;
            if (!Letter.IsMatch(text)) return text;
            var result = Find(text, 0) ?? text;
            if (cache.Count > 20000) cache.Clear();
            cache[text] = result;
            return result;
        }

        /// <summary>A whole number written the player's way (same as localNumbers in src/i18n/index.ts): 14,000 in English,
        /// 14 000 in French, 14.000 in Portuguese, Spanish and German.</summary>
        public static string Number(double value)
        {
            var text = Math.Round(value).ToString("N0", System.Globalization.CultureInfo.InvariantCulture); // "14,000"
            switch (Language)
            {
                case "en": return text;
                case "fr": return text.Replace(",", "\u202f");
                default: return text.Replace(",", ".");
            }
        }

        /// <summary>Format then translate: F("Nível {0}", 3) looks up "Nível {0}" and fills it.</summary>
        public static string F(string pattern, params object[] values)
        {
            var text = string.Format(pattern, values);
            return T(text);
        }

        static string Word(string text)
        {
            if (exact.TryGetValue(text, out var v)) return v;
            if (upper.TryGetValue(text, out v)) return v;
            if (lower.TryGetValue(text, out v)) return v;
            return null;
        }

        static string Find(string text, int depth)
        {
            var word = Word(text);
            if (word != null) return word;
            var around = Around.Match(text);
            if (around.Success && (around.Groups[1].Length > 0 || around.Groups[3].Length > 0))
            {
                var inner = Word(around.Groups[2].Value);
                if (inner != null) return around.Groups[1].Value + inner + around.Groups[3].Value;
            }
            if (depth > 3) return null;
            foreach (var pattern in patterns)
            {
                if (pattern.probe.Length > 0 && text.IndexOf(pattern.probe, StringComparison.Ordinal) < 0) continue;
                var match = pattern.regex.Match(text);
                if (!match.Success) continue;
                var values = new string[match.Groups.Count - 1];
                for (int i = 1; i < match.Groups.Count; i++) values[i - 1] = Find(match.Groups[i].Value, depth + 1) ?? match.Groups[i].Value;
                return Regex.Replace(pattern.target, @"\{#(-?\d+)\}", m => { int n = int.Parse(m.Groups[1].Value); return n >= 0 && n < values.Length ? values[n] : ""; });
            }
            foreach (var separators in new[] { Sentences, Separators, ListSeparators })
            {
                var pieces = separators.Split(text);
                if (pieces.Length < 2) continue;
                bool changed = false;
                for (int i = 0; i < pieces.Length; i++)
                {
                    if (i % 2 == 1) { if (exact.TryGetValue(pieces[i], out var sep)) pieces[i] = sep; continue; }
                    if (!Letter.IsMatch(pieces[i])) continue;
                    var found = Find(pieces[i], depth + 1);
                    if (found == null) continue;
                    pieces[i] = found; changed = true;
                }
                if (changed) return string.Concat(pieces);
            }
            return null;
        }

        // Texts Unity shows before the game host sends the full catalog (start screen, loading, errors).
        static readonly Dictionary<string, Dictionary<string, string>> BuiltIn = new Dictionary<string, Dictionary<string, string>>
        {
            ["en"] = new Dictionary<string, string>
            {
                ["Jogar"] = "Play", ["Continue o seu mercado de onde parou."] = "Pick up your market where you left off.",
                ["Idioma"] = "Language", ["Escolha o idioma do jogo."] = "Choose the game's language.",
                ["Modo edição"] = "Edit mode", ["Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."] = "Build each store's map: move, add, resize and paint streets and bike lanes. Infinite money, on a separate save.",
                ["Voltar"] = "Back", ["Sair"] = "Quit", ["Supermercado Simulator"] = "Supermarket Simulator",
                [" e "] = " and ", ["Enter = Jogar"] = "Enter = Play", ["Enter = Jogar   •   E = Modo edição"] = "Enter = Play   •   E = Edit mode",
                ["L = Idioma"] = "L = Language", ["Esc = Voltar"] = "Esc = Back",
                ["O jogo parou de responder. Feche e abra de novo."] = "The game stopped responding. Close it and open it again.",
                ["O processo do jogo (node) parou. Veja o Console."] = "The game process (node) stopped. Check the Console.",
                ["Não foi possível agora."] = "Not possible right now.",
                // Opções window (CheckoutSettings) and its start-screen card.
                ["Opções"] = "Settings", ["Ajuste a música e os sons do jogo."] = "Adjust the game's music and sounds.", ["Música"] = "Music", ["Efeitos sonoros"] = "Sound effects", ["Ligada"] = "On", ["Desligada"] = "Off", ["Ligados"] = "On", ["Desligados"] = "Off", ["Fechar"] = "Close", ["Volume da música e dos efeitos sonoros."] = "Music and sound effects volume.", ["O = Opções"] = "O = Settings",
                ["Sons"] = "Sound", ["Música, sons, idioma e conta."] = "Music, sound, language, account.",
                // Opções › Conta on the start screen (before the host runs)
                ["Salve o seu progresso"] = "Save your progress", ["Guarde o mercado, as moedas e os diamantes na nuvem. Trocou de celular? É só entrar com a mesma conta."] = "Keep your market, coins and diamonds in the cloud. New phone? Just sign in with the same account.", ["Iniciar sessão com a Apple"] = "Sign in with Apple", ["Entrar com Google"] = "Sign in with Google", ["Entrando…"] = "Signing in…", ["Conta Apple"] = "Apple account", ["Conta Google"] = "Google account", ["O seu progresso vai para a nuvem quando o jogo começar."] = "Your progress goes to the cloud once the game starts.", ["Sair"] = "Exit", ["Apagar conta"] = "Delete account", ["Toque de novo"] = "Tap again", ["O login não está disponível nesta versão do jogo."] = "Sign-in isn't available in this version of the game.", ["Entrar com a Apple funciona no iPhone."] = "Sign in with Apple works on the iPhone.", ["Não deu para entrar com a Apple."] = "Couldn't sign in with Apple.", ["Não deu para entrar com o Google."] = "Couldn't sign in with Google.", ["Sem conexão com o servidor. Tente de novo."] = "No connection to the server. Try again.", ["O Google não confirmou o login ({0})."] = "Google didn't confirm the sign-in ({0}).", ["A Apple não confirmou o login ({0})."] = "Apple didn't confirm the sign-in ({0}).", ["O login demorou demais."] = "Sign-in took too long.",
                ["Conta"] = "Account", ["Sua conta"] = "Your account", ["Toque em Jogar e volte aqui para entrar e guardar o seu progresso na nuvem."] = "Tap Play and come back here to sign in and save your progress in the cloud.", ["Guarde o seu progresso na nuvem."] = "Keep your progress in the cloud.",
                // Opções footer (privacy policy, support) and the account deletion that needs a new sign-in (29/10)
                ["Política de privacidade"] = "Privacy policy", ["Suporte"] = "Support", ["A sua sessão expirou. Entre de novo para apagar a conta."] = "Your session has expired. Sign in again to delete your account.",
            },
            ["es"] = new Dictionary<string, string>
            {
                ["Jogar"] = "Jugar", ["Continue o seu mercado de onde parou."] = "Sigue con tu mercado donde lo dejaste.",
                ["Idioma"] = "Idioma", ["Escolha o idioma do jogo."] = "Elige el idioma del juego.",
                ["Modo edição"] = "Modo edición", ["Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."] = "Arma el mapa de cada tienda: mueve, añade, cambia el tamaño y pinta calles y carriles bici. Dinero infinito, en una partida aparte.",
                ["Voltar"] = "Volver", ["Sair"] = "Salir", ["Supermercado Simulator"] = "Supermercado Simulator",
                [" e "] = " y ", ["Enter = Jogar"] = "Enter = Jugar", ["Enter = Jogar   •   E = Modo edição"] = "Enter = Jugar   •   E = Modo edición",
                ["L = Idioma"] = "L = Idioma", ["Esc = Voltar"] = "Esc = Volver",
                ["O jogo parou de responder. Feche e abra de novo."] = "El juego dejó de responder. Ciérralo y vuelve a abrirlo.",
                ["O processo do jogo (node) parou. Veja o Console."] = "El proceso del juego (node) se detuvo. Mira la Consola.",
                ["Não foi possível agora."] = "No es posible ahora.",
                // Opções window (CheckoutSettings) and its start-screen card.
                ["Opções"] = "Opciones", ["Ajuste a música e os sons do jogo."] = "Ajusta la música y los sonidos del juego.", ["Música"] = "Música", ["Efeitos sonoros"] = "Efectos de sonido", ["Ligada"] = "Activada", ["Desligada"] = "Desactivada", ["Ligados"] = "Activados", ["Desligados"] = "Desactivados", ["Fechar"] = "Cerrar", ["Volume da música e dos efeitos sonoros."] = "Volumen de la música y de los efectos de sonido.", ["O = Opções"] = "O = Opciones",
                ["Sons"] = "Sonido", ["Música, sons, idioma e conta."] = "Música, sonido, idioma, cuenta.",
                // Opções › Conta on the start screen (before the host runs)
                ["Salve o seu progresso"] = "Guarda tu progreso", ["Guarde o mercado, as moedas e os diamantes na nuvem. Trocou de celular? É só entrar com a mesma conta."] = "Guarda el mercado, las monedas y los diamantes en la nube. ¿Cambiaste de móvil? Solo entra con la misma cuenta.", ["Iniciar sessão com a Apple"] = "Iniciar sesión con Apple", ["Entrar com Google"] = "Entrar con Google", ["Entrando…"] = "Entrando…", ["Conta Apple"] = "Cuenta de Apple", ["Conta Google"] = "Cuenta de Google", ["O seu progresso vai para a nuvem quando o jogo começar."] = "Tu progreso se sube a la nube cuando empiece el juego.", ["Sair"] = "Salir", ["Apagar conta"] = "Borrar cuenta", ["Toque de novo"] = "Toca de nuevo", ["O login não está disponível nesta versão do jogo."] = "El inicio de sesión no está disponible en esta versión del juego.", ["Entrar com a Apple funciona no iPhone."] = "Iniciar sesión con Apple funciona en el iPhone.", ["Não deu para entrar com a Apple."] = "No se pudo iniciar sesión con Apple.", ["Não deu para entrar com o Google."] = "No se pudo entrar con Google.", ["Sem conexão com o servidor. Tente de novo."] = "Sin conexión con el servidor. Inténtalo de nuevo.", ["O Google não confirmou o login ({0})."] = "Google no confirmó el inicio de sesión ({0}).", ["A Apple não confirmou o login ({0})."] = "Apple no confirmó el inicio de sesión ({0}).", ["O login demorou demais."] = "El inicio de sesión tardó demasiado.",
                ["Conta"] = "Cuenta", ["Sua conta"] = "Tu cuenta", ["Toque em Jogar e volte aqui para entrar e guardar o seu progresso na nuvem."] = "Toca Jugar y vuelve aquí para iniciar sesión y guardar tu progreso en la nube.", ["Guarde o seu progresso na nuvem."] = "Guarda tu progreso en la nube.",
                // Opções footer (privacy policy, support) and the account deletion that needs a new sign-in (29/10)
                ["Política de privacidade"] = "Política de privacidad", ["Suporte"] = "Soporte", ["A sua sessão expirou. Entre de novo para apagar a conta."] = "Tu sesión ha caducado. Vuelve a iniciar sesión para borrar la cuenta.",
            },
            ["fr"] = new Dictionary<string, string>
            {
                ["Jogar"] = "Jouer", ["Continue o seu mercado de onde parou."] = "Reprends ton magasin là où tu l'as laissé.",
                ["Idioma"] = "Langue", ["Escolha o idioma do jogo."] = "Choisis la langue du jeu.",
                ["Modo edição"] = "Mode édition", ["Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."] = "Construis la carte de chaque magasin : déplace, ajoute, redimensionne et peins rues et pistes cyclables. Argent infini, sur une sauvegarde à part.",
                ["Voltar"] = "Retour", ["Sair"] = "Quitter", ["Supermercado Simulator"] = "Supermarché Simulator",
                [" e "] = " et ", ["Enter = Jogar"] = "Entrée = Jouer", ["Enter = Jogar   •   E = Modo edição"] = "Entrée = Jouer   •   E = Mode édition",
                ["L = Idioma"] = "L = Langue", ["Esc = Voltar"] = "Échap = Retour",
                ["O jogo parou de responder. Feche e abra de novo."] = "Le jeu ne répond plus. Ferme-le et rouvre-le.",
                ["O processo do jogo (node) parou. Veja o Console."] = "Le processus du jeu (node) s'est arrêté. Regarde la Console.",
                ["Não foi possível agora."] = "Impossible pour le moment.",
                // Opções window (CheckoutSettings) and its start-screen card.
                ["Opções"] = "Options", ["Ajuste a música e os sons do jogo."] = "Règle la musique et les sons du jeu.", ["Música"] = "Musique", ["Efeitos sonoros"] = "Effets sonores", ["Ligada"] = "Activée", ["Desligada"] = "Désactivée", ["Ligados"] = "Activés", ["Desligados"] = "Désactivés", ["Fechar"] = "Fermer", ["Volume da música e dos efeitos sonoros."] = "Volume de la musique et des effets sonores.", ["O = Opções"] = "O = Options",
                ["Sons"] = "Son", ["Música, sons, idioma e conta."] = "Musique, son, langue, compte.",
                // Opções › Conta on the start screen (before the host runs)
                ["Salve o seu progresso"] = "Sauvegardez votre progression", ["Guarde o mercado, as moedas e os diamantes na nuvem. Trocou de celular? É só entrar com a mesma conta."] = "Garde ton marché, tes pièces et tes diamants dans le cloud. Nouveau téléphone ? Connecte-toi simplement avec le même compte.", ["Iniciar sessão com a Apple"] = "Se connecter avec Apple", ["Entrar com Google"] = "Se connecter avec Google", ["Entrando…"] = "Connexion…", ["Conta Apple"] = "Compte Apple", ["Conta Google"] = "Compte Google", ["O seu progresso vai para a nuvem quando o jogo começar."] = "Ta progression part dans le cloud dès que le jeu commence.", ["Sair"] = "Quitter", ["Apagar conta"] = "Supprimer le compte", ["Toque de novo"] = "Touche encore", ["O login não está disponível nesta versão do jogo."] = "La connexion n'est pas disponible dans cette version du jeu.", ["Entrar com a Apple funciona no iPhone."] = "Se connecter avec Apple fonctionne sur iPhone.", ["Não deu para entrar com a Apple."] = "Impossible de se connecter avec Apple.", ["Não deu para entrar com o Google."] = "Impossible de se connecter avec Google.", ["Sem conexão com o servidor. Tente de novo."] = "Pas de connexion au serveur. Réessayez.", ["O Google não confirmou o login ({0})."] = "Google n'a pas confirmé la connexion ({0}).", ["A Apple não confirmou o login ({0})."] = "Apple n'a pas confirmé la connexion ({0}).", ["O login demorou demais."] = "La connexion a pris trop de temps.",
                ["Conta"] = "Compte", ["Sua conta"] = "Ton compte", ["Toque em Jogar e volte aqui para entrar e guardar o seu progresso na nuvem."] = "Touche Jouer et reviens ici pour te connecter et sauvegarder ta progression dans le cloud.", ["Guarde o seu progresso na nuvem."] = "Garde ta progression dans le cloud.",
                // Opções footer (privacy policy, support) and the account deletion that needs a new sign-in (29/10)
                ["Política de privacidade"] = "Politique de confidentialité", ["Suporte"] = "Assistance", ["A sua sessão expirou. Entre de novo para apagar a conta."] = "Ta session a expiré. Reconnecte-toi pour supprimer le compte.",
            },
            ["de"] = new Dictionary<string, string>
            {
                ["Jogar"] = "Spielen", ["Continue o seu mercado de onde parou."] = "Mach mit deinem Markt da weiter, wo du aufgehört hast.",
                ["Idioma"] = "Sprache", ["Escolha o idioma do jogo."] = "Wähle die Sprache des Spiels.",
                ["Modo edição"] = "Bearbeitungsmodus", ["Monte o mapa de cada loja: mova, adicione, redimensione e pinte ruas e ciclovias. Dinheiro infinito, em um save separado."] = "Gestalte die Karte jedes Ladens: verschieben, hinzufügen, Größe ändern und Straßen und Radwege malen. Unendlich Geld, in einem eigenen Spielstand.",
                ["Voltar"] = "Zurück", ["Sair"] = "Beenden", ["Supermercado Simulator"] = "Supermarkt Simulator",
                [" e "] = " und ", ["Enter = Jogar"] = "Enter = Spielen", ["Enter = Jogar   •   E = Modo edição"] = "Enter = Spielen   •   E = Bearbeitungsmodus",
                ["L = Idioma"] = "L = Sprache", ["Esc = Voltar"] = "Esc = Zurück",
                ["O jogo parou de responder. Feche e abra de novo."] = "Das Spiel reagiert nicht mehr. Schließe es und öffne es erneut.",
                ["O processo do jogo (node) parou. Veja o Console."] = "Der Spielprozess (node) wurde beendet. Sieh in der Konsole nach.",
                ["Não foi possível agora."] = "Gerade nicht möglich.",
                // Opções window (CheckoutSettings) and its start-screen card.
                ["Opções"] = "Einstellungen", ["Ajuste a música e os sons do jogo."] = "Stell Musik und Töne des Spiels ein.", ["Música"] = "Musik", ["Efeitos sonoros"] = "Soundeffekte", ["Ligada"] = "An", ["Desligada"] = "Aus", ["Ligados"] = "An", ["Desligados"] = "Aus", ["Fechar"] = "Schließen", ["Volume da música e dos efeitos sonoros."] = "Lautstärke von Musik und Soundeffekten.", ["O = Opções"] = "O = Einstellungen",
                ["Sons"] = "Ton", ["Música, sons, idioma e conta."] = "Musik, Ton, Sprache, Konto.",
                // Opções › Conta on the start screen (before the host runs)
                ["Salve o seu progresso"] = "Sichere deinen Fortschritt", ["Guarde o mercado, as moedas e os diamantes na nuvem. Trocou de celular? É só entrar com a mesma conta."] = "Speichere Markt, Münzen und Diamanten in der Cloud. Neues Handy? Melde dich einfach mit demselben Konto an.", ["Iniciar sessão com a Apple"] = "Mit Apple anmelden", ["Entrar com Google"] = "Mit Google anmelden", ["Entrando…"] = "Anmeldung…", ["Conta Apple"] = "Apple-Konto", ["Conta Google"] = "Google-Konto", ["O seu progresso vai para a nuvem quando o jogo começar."] = "Dein Fortschritt wird in die Cloud geladen, sobald das Spiel startet.", ["Sair"] = "Beenden", ["Apagar conta"] = "Konto löschen", ["Toque de novo"] = "Noch einmal tippen", ["O login não está disponível nesta versão do jogo."] = "Die Anmeldung ist in dieser Spielversion nicht verfügbar.", ["Entrar com a Apple funciona no iPhone."] = "Mit Apple anmelden funktioniert auf dem iPhone.", ["Não deu para entrar com a Apple."] = "Anmeldung mit Apple fehlgeschlagen.", ["Não deu para entrar com o Google."] = "Anmeldung mit Google fehlgeschlagen.", ["Sem conexão com o servidor. Tente de novo."] = "Keine Verbindung zum Server. Versuch es noch einmal.", ["O Google não confirmou o login ({0})."] = "Google hat die Anmeldung nicht bestätigt ({0}).", ["A Apple não confirmou o login ({0})."] = "Apple hat die Anmeldung nicht bestätigt ({0}).", ["O login demorou demais."] = "Die Anmeldung hat zu lange gedauert.",
                ["Conta"] = "Konto", ["Sua conta"] = "Dein Konto", ["Toque em Jogar e volte aqui para entrar e guardar o seu progresso na nuvem."] = "Tippe auf Spielen und komm hierher zurück, um dich anzumelden und deinen Fortschritt in der Cloud zu speichern.", ["Guarde o seu progresso na nuvem."] = "Speichere deinen Fortschritt in der Cloud.",
                // Opções footer (privacy policy, support) and the account deletion that needs a new sign-in (29/10)
                ["Política de privacidade"] = "Datenschutzerklärung", ["Suporte"] = "Support", ["A sua sessão expirou. Entre de novo para apagar a conta."] = "Deine Sitzung ist abgelaufen. Melde dich erneut an, um das Konto zu löschen.",
            },
        };
    }
}
