using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Phones: the floating action buttons on the left edge (REPOR, ENTREGA, CAIXA, CONSERTAR) each had a fixed spot
    // made for the 1000-unit desktop height; on the 680-unit phone canvas they ran into the top bar and each other.
    // On handheld devices they stack instead: from just under the top bar, in a fixed order, only the visible ones,
    // a bit smaller, wrapping into a second column before they reach the Construir button. Desktop keeps its spots.
    public sealed class CheckoutFabRail : MonoBehaviour
    {
        const float Top = 104, Left = 8, Gap = 6, Scale = .76f, Bottom = 250; // Bottom: clear of Construir (bottom-left)
        static readonly List<CheckoutFabRail> all = new List<CheckoutFabRail>();
        static int created; int order, seq; RectTransform rect; Vector3 applied = Vector3.zero;

        /// <summary>Puts a floating button in the phone rail (order: 0 = top).</summary>
        public static void Add(RectTransform fab, int order)
        {
            if (!CheckoutScreen.Handheld) return;
            var rail = fab.gameObject.AddComponent<CheckoutFabRail>(); rail.order = order; rail.seq = created++; rail.rect = fab;
            fab.anchorMin = fab.anchorMax = fab.pivot = new Vector2(0, 1);
        }

        void OnEnable() { if (!all.Contains(this)) all.Add(this); }
        void OnDestroy() => all.Remove(this);

        void LateUpdate()
        {
            // Slot: how many visible rail buttons come before this one on the same canvas size.
            int slot = 0;
            foreach (var other in all)
                if (other && other != this && other.isActiveAndEnabled && (other.order < order || (other.order == order && other.seq < seq))) slot++;
            var parent = rect.parent as RectTransform;
            float height = parent ? parent.rect.height : 650f, w = rect.sizeDelta.x * Scale, h = rect.sizeDelta.y * Scale;
            int perColumn = Mathf.Max(1, Mathf.FloorToInt((height - Top - Bottom + Gap) / (h + Gap)));
            rect.anchoredPosition = new Vector2(Left + (slot / perColumn) * (w + Gap), -Top - (slot % perColumn) * (h + Gap));
            // Some buttons pulse by setting their scale every frame: keep their pulse, at the rail's size.
            var s = rect.localScale;
            if (s != applied) { applied = s * Scale; rect.localScale = applied; }
        }
    }
}
