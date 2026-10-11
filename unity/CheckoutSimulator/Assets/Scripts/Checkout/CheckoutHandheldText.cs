using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace Checkout
{
    // Phone legibility floor. The HUD was laid out for the 1600x1000 desktop canvas, where 12-16 unit texts are fine;
    // on an iPhone in landscape those come out at 7-9 pt. On handheld devices every screen-space text made by the
    // HUD factories (CheckoutDesktopCard.Text, CheckoutDesktopButton) grows toward 20 units (about 11.5 pt) through
    // TMP auto-size: it never draws smaller than the size the code asked for, and it only grows where the box has room,
    // so nothing that fits today starts overflowing. Button labels may also shrink a little (to 80%) instead of
    // cutting the text with "...". Desktop and world-space texts (signs, shelf tags) are left untouched.
    public static class CheckoutHandheldText
    {
        public const float Floor = 20f;     // units on the handheld canvas (680 tall): about 11.5 pt on an iPhone
        static readonly List<TMP_Text> pending = new List<TMP_Text>();
        static readonly List<float> shrink = new List<float>();
        static bool hooked;

        /// <summary>Queue a text for the handheld floor (applied before the canvases render, once it sits in its canvas).
        /// minScale below 1 lets it shrink to fit instead of showing "..." (button labels).</summary>
        public static void Register(TMP_Text text, float minScale = 1f)
        {
            if (!text || !CheckoutScreen.Handheld) return;
            pending.Add(text); shrink.Add(minScale);
            if (!hooked) { hooked = true; Canvas.willRenderCanvases += Flush; }
        }

        /// <summary>The size a desktop size becomes on a phone: +30%, up to the floor; 20 and above stay.</summary>
        public static float Boost(float size) => size >= Floor ? size : Mathf.Min(Floor, size * 1.3f);

        static void Flush()
        {
            if (pending.Count == 0) return;
            for (int i = 0; i < pending.Count; i++)
            {
                var t = pending[i];
                if (!t) continue;
                var canvas = t.GetComponentInParent<Canvas>(true);
                if (!canvas || canvas.rootCanvas.renderMode == RenderMode.WorldSpace) continue;
                if (t.enableAutoSizing)
                {
                    t.fontSizeMax = Boost(t.fontSizeMax);
                    if (shrink[i] < 1f) t.fontSizeMin = Mathf.Min(t.fontSizeMin, t.fontSizeMax * shrink[i]);
                    continue;
                }
                float size = t.fontSize, max = Boost(size), min = size * shrink[i];
                if (max <= size && min >= size) continue;
                t.fontSizeMin = min; t.fontSizeMax = max; t.enableAutoSizing = true;
            }
            pending.Clear(); shrink.Clear();
        }
    }
}
