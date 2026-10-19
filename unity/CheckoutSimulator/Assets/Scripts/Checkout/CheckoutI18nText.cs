using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace Checkout
{
    // Puts every text on screen in the player's language. Pages and snapshots already come translated from the
    // game host; this catches the texts written in Unity itself (the register game, store mishaps, popups,
    // toasts). Each TMP text is checked once when it changes: right before the frame is drawn (LateUpdate, last
    // in order) for texts already known, and on its first draw for new ones.
    [DefaultExecutionOrder(32000)]
    public class CheckoutI18nText : MonoBehaviour
    {
        static CheckoutI18nText instance;
        // Each text and the last string we saw (or wrote) on it.
        static readonly Dictionary<TMP_Text, string> seen = new Dictionary<TMP_Text, string>();
        static readonly List<TMP_Text> pending = new List<TMP_Text>();
        static readonly List<TMP_Text> dead = new List<TMP_Text>();
        // The Portuguese a text had before we translated it: a later language change (Opções › Idioma, Lucas 19/10)
        // starts again from it, so a label written once in Unity does not stay in the previous language.
        static readonly Dictionary<TMP_Text, string> source = new Dictionary<TMP_Text, string>();

        // Started by CheckoutBoot once the game scene is loaded (the Boot scene comes first on Android).
        internal static void Boot() => Ensure();

        public static void Ensure()
        {
            if (instance) return;
            var go = new GameObject("CheckoutI18nText");
            DontDestroyOnLoad(go);
            instance = go.AddComponent<CheckoutI18nText>();
        }

        void OnEnable()
        {
            TMPro_EventManager.TEXT_CHANGED_EVENT.Add(OnTextChanged);
            CheckoutI18n.Changed += Retranslate;
        }

        void OnDisable()
        {
            TMPro_EventManager.TEXT_CHANGED_EVENT.Remove(OnTextChanged);
            CheckoutI18n.Changed -= Retranslate;
        }

        /// <summary>Follow a text from its creation (no Portuguese frame before its first draw).</summary>
        public static void Register(TMP_Text text)
        {
            if (!text || seen.ContainsKey(text)) return;
            Ensure();
            seen[text] = null;
        }

        static void OnTextChanged(Object changed)
        {
            if (changed is TMP_Text text && !seen.ContainsKey(text)) pending.Add(text);
        }

        // A new language: texts we translated go back to their Portuguese (if nobody changed them since), and every
        // text gets another look.
        static void Retranslate()
        {
            foreach (var pair in source)
                if (pair.Key && seen.TryGetValue(pair.Key, out var written) && ReferenceEquals(pair.Key.text, written)) pair.Key.text = pair.Value;
            source.Clear();
            var keys = new List<TMP_Text>(seen.Keys);
            foreach (var key in keys) seen[key] = null;
        }

        void LateUpdate()
        {
            if (CheckoutI18n.IsPortuguese) { pending.Clear(); return; }
            foreach (var text in pending) if (text && !seen.ContainsKey(text)) seen[text] = null;
            pending.Clear();
            foreach (var pair in seen)
            {
                var text = pair.Key;
                if (!text) { dead.Add(text); continue; }
                var current = text.text;
                if (ReferenceEquals(current, pair.Value) || string.IsNullOrEmpty(current)) continue;
                // Typed text (the map editor's search box) belongs to the player.
                if (text.GetComponentInParent<TMP_InputField>(true)) { dead.Add(text); continue; }
                var translated = CheckoutI18n.T(current);
                source.Remove(text); // new text from the game: its own words are the source now
                if (!ReferenceEquals(translated, current) && translated != current) { source[text] = current; text.text = translated; }
                changes.Add(text);
            }
            foreach (var text in changes) seen[text] = text.text;
            changes.Clear();
            foreach (var text in dead) { seen.Remove(text); source.Remove(text); }
            dead.Clear();
        }

        static readonly List<TMP_Text> changes = new List<TMP_Text>();
    }
}
