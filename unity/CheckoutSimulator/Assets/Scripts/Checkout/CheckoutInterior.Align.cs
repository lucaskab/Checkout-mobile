using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // Right angles only (tester 03/11: "Essa gôndola fica tooortaaaaa"; Lucas: the furniture "não fica alinhada de jeito
    // nenhum"). The shop is a box of straight walls and a square grid, so furniture inside it stands at 0/90/180/270 only:
    // the build-mode arrows turn it a quarter, the two-finger twist (Ctrl + mouse on a computer) lands on the nearest
    // quarter. Decorations on the city block outside may also stand diagonally (45° steps), on purpose.
    //
    // Layouts saved before (the twist used to stop every 5°, the arrows turned 45°): when the shop loads, every indoor piece
    // standing askew turns to its nearest right angle where it stands, lines up with the grid, and when it no longer fits
    // there slides to the nearest free spot (Settle). No piece is ever stored away or dropped: a piece with no free spot at
    // a right angle keeps its old spot and turn (it fitted there), and the next load tries again.
    public partial class CheckoutInterior
    {
        /// <summary>The turn step of a piece: a quarter indoors, an eighth on the city block.</summary>
        public static float TurnStep(bool outside) => outside ? 45f : 90f;

        /// <summary>The nearest allowed turn (0..360) for a piece inside the shop or outside on the block.</summary>
        public static float SnapTurn(float rot, bool outside)
        {
            float step = TurnStep(outside);
            return Mathf.Repeat(Mathf.Round(Mathf.Repeat(rot, 360) / step) * step, 360);
        }

        /// <summary>Is the turn one of the allowed steps (within a hundredth of a degree)?</summary>
        public static bool OnStep(float rot, bool outside) => Mathf.Abs(Mathf.DeltaAngle(rot, SnapTurn(rot, outside))) < .01f;

        /// <summary>QA ("eventsalign"): leave askew pieces as saved, to show a layout from before the fix.</summary>
        public static bool QaKeepAskew;
        /// <summary>QA: what squaring up did to each piece on the last load (id → story).</summary>
        public static readonly Dictionary<string, string> SquaredLog = new Dictionary<string, string>();
        // Pieces that found no spot at a right angle, at the spot and turn they kept: not searched again every snapshot.
        readonly HashSet<string> squareGaveUp = new HashSet<string>();

        // Turns every askew piece to its nearest allowed step, on the grid, and settles the ones that no longer fit.
        // True when something moved (the caller saves the layout so it sticks).
        bool SquareUp()
        {
            if (QaKeepAskew) return false;
            var askew = items.Values
                .Where(i => i.root && !i.design && !i.ghost && !OnStep(i.rot, i.outside) && !squareGaveUp.Contains(GaveUpKey(i)))
                // Shelves first leave the checkout strip, so the checkouts find it free (as the other load migrations).
                .OrderBy(i => IsCounter(i) ? 1 : 0).ThenBy(i => i.id).ToList();
            if (askew.Count == 0) return false;
            var before = askew.ToDictionary(i => i.id, i => (x: i.x, z: i.z, rot: i.rot));
            // 1. all of them turn where they stand first, so each one is measured against its neighbours' new footprints.
            foreach (var it in askew) { it.rot = SnapTurn(it.rot, it.outside); it.legacySize = Vector2.zero; Place(it); }
            foreach (var it in askew)
            {
                var b = before[it.id]; string story = $"rot {b.rot:0.#} -> {it.rot:0}";
                var here = it.root.position;
                // 2. on the grid, flush with the walls and the neighbours (the same snapping a drag uses).
                var grid = Snap(it, here, it.rot, here);
                if (Fits(it, grid, it.rot, out _)) { MoveTo(it, grid); story += " in place"; }
                // 3. no room turned this way here: the nearest free spot (Settle slides first, then tries the other quarters).
                else if (!Fits(it, here, it.rot, out _))
                {
                    if (Settle(it)) story += $" settled to ({it.x:0.00},{it.z:0.00}) rot {it.rot:0}";
                    else
                    {
                        // 4. nowhere at a right angle: back where it stood, as it was (it fitted there). Never stored away.
                        it.x = b.x; it.z = b.z; it.rot = b.rot; Place(it);
                        squareGaveUp.Add(GaveUpKey(it));
                        story += " NO ROOM at a right angle: kept as saved";
                        Debug.LogWarning("CHECKOUT_INTERIOR no right-angle spot for " + it.id + ": kept as saved");
                    }
                }
                else story += " in place (off grid)";
                SquaredLog[it.id] = story;
            }
            return true;
        }

        static string GaveUpKey(Item it) => it.id + "@" + it.x.ToString("0.00") + "," + it.z.ToString("0.00") + "," + it.rot.ToString("0.0");
    }
}
