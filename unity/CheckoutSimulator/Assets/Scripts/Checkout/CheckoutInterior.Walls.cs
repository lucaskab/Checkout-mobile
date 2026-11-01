using System.Linq;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Sector walls (Lucas 01/11): a special sector stands right against the market's walls, with no gap, and there its own
    // freestanding panel (the "Back Wall" child of the round-5 models) hides so the market wall is its wall; standing free (or with less than
    // 80% of its back against a wall) it keeps the panel. The boards, the name and the ticket display stay either way.
    //
    // Flush (art agent, sector-walls-art): the back face (local +Z, max Z) sits on the face of the wainscot's gold rail,
    // which is the clear floor's edge (CheckoutMarketShell: 5 cm inside the plaster). Placement already lands there:
    // snapping sticks to the floor edge within 30 cm (SnapCore / Inside), more than half a grid square, with no overlap
    // into the wall. Only tall walls count; the low front and east walls (0.75 m) leave the panel up, or the boards float.
    public partial class CheckoutInterior
    {
        /// <summary>The side of the shop a piece's back (local +Z) faces at this turn: 0 west, 1 east, 2 front (south), 3 rear (north), -1 none.</summary>
        static int BackSide(float rot)
        {
            var back = Quaternion.Euler(0, rot, 0) * Vector3.forward;
            if (back.x < -.9f) return 0; if (back.x > .9f) return 1; if (back.z < -.9f) return 2; if (back.z > .9f) return 3;
            return -1;
        }

        // ------------------------------------------------------------------ tiers grow away from the wall
        // The tier models are centred on their pivot, so a bigger tier at the same pivot pushed its back into the wall and
        // never fitted there (a flush sector could not evolve in place). A sector whose back is on a wall edge of the
        // floor changes tier with its back staying on that wall: it grows (or shrinks) toward its customers.

        /// <summary>The gap from the piece's back face (local +Z) to the floor edge it faces, or +inf when it is turned askew.</summary>
        float BackGap(Item it, Footprint f)
        {
            var floor = FloorRect;
            float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
            switch (BackSide(it.rot))
            {
                case 0: return (f.c.x - ex) - floor.xMin;
                case 1: return floor.xMax - (f.c.x + ex);
                case 2: return (f.c.y - ez) - floor.yMin;
                case 3: return floor.yMax - (f.c.y + ez);
            }
            return float.PositiveInfinity;
        }

        /// <summary>Where `it` stands with the model `to`: its pivot, or (a sector with its back on a wall) moved along
        /// its depth so the back face stays where it is.</summary>
        Vector3 TierSpot(Item it, CheckoutInteriorPiece to)
        {
            var pos = it.root.position;
            if (!to || !it.piece || it.type != "sector" || it.outside || it.design || CheckoutStall.Small) return pos;
            float gap = BackGap(it, FootprintOf(it));
            if (gap > BackNear || gap < -.02f) return pos;
            float s = it.scale > 0 ? it.scale : 1;
            return pos + Quaternion.Euler(0, it.rot, 0) * new Vector3(0, 0, (Square(it.piece.max.y) - Square(to.max.y)) * s);
        }

        // ------------------------------------------------------------------ the back panel against a wall
        public const float BackCover = .8f;      // this much of the back's width against a wall hides the panel
        const float BackNear = .07f;             // back face this close to the rail's face counts as against it
        float wallsNext; string wallsSignature;
        /// <summary>QA: sector id → its back is against a wall (the panel hidden), and what was measured.</summary>
        public readonly Dictionary<string, string> WallState = new Dictionary<string, string>();

        /// <summary>Is this sector's back against a tall wall of the market (≥ 80% of its width, within 7 cm of the rail's face)?</summary>
        public bool BackAgainstWall(Item it, out string why)
        {
            why = "";
            if (it == null || !it.root || it.outside || it.type != "sector") { why = "not a sector"; return false; }
            if (CheckoutStall.Small) { why = "small shop"; return false; }
            var f = FootprintOf(it); var floor = FloorRect;
            float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
            int side = BackSide(it.rot);
            // The tall walls are the west and the rear ones; the front and east walls are low (the camera looks in over
            // them): against those the panel stays, or the sector would stand open to the street.
            if (side != 0 && side != 3) { why = side < 0 ? "turned" : "low wall"; return false; }
            float gap = BackGap(it, f);
            float a0 = side == 0 ? f.c.y - ez : f.c.x - ex, a1 = side == 0 ? f.c.y + ez : f.c.x + ex;
            float w0 = side == 0 ? floor.yMin : floor.xMin, w1 = side == 0 ? floor.yMax : floor.xMax;
            float covered = Mathf.Max(0, Mathf.Min(a1, w1) - Mathf.Max(a0, w0));
            // the rear wall's service door is an opening, not wall
            if (side == 3) { var d = ServiceDoor; float d0 = d.c.x - d.hx, d1 = d.c.x + d.hx; covered -= Mathf.Max(0, Mathf.Min(a1, d1) - Mathf.Max(a0, d0)); }
            float share = covered / Mathf.Max(.01f, a1 - a0);
            why = $"{(side == 0 ? "west" : "rear")} wall, back {gap * 100:0.0} cm from the rail, {share * 100:0}% of it against the wall";
            return gap <= BackNear && gap >= -.02f && share >= BackCover;
        }

        // Re-checked a few times a second (placed, moved, turned, the walls moved with an expansion): cheap, seven sectors.
        void UpdateSectorWalls()
        {
            if (Time.unscaledTime < wallsNext) return;
            wallsNext = Time.unscaledTime + .2f;
            var sb = new System.Text.StringBuilder(); sb.Append(FloorRect.ToString("F2"));
            foreach (var it in items.Values) if (it.type == "sector" && it.root) sb.Append('|').Append(it.id).Append(it.root.position.ToString("F2")).Append(it.rot.ToString("F0")).Append(it.template).Append(it.root.GetHashCode());
            var signature = sb.ToString();
            if (signature == wallsSignature) return;
            wallsSignature = signature;
            WallState.Clear();
            foreach (var it in items.Values)
            {
                if (it.type != "sector" || !it.root) continue;
                bool against = BackAgainstWall(it, out var why);
                ShowBackWall(it, !against);
                WallState[it.id] = (against ? "against " : "free ") + why + (it.root.Find("Back Wall") ? "" : " (no Back Wall child)");
            }
        }

        void ShowBackWall(Item it, bool show)
        {
            var panel = it.root.Find("Back Wall");
            if (panel && panel.gameObject.activeSelf != show) panel.gameObject.SetActive(show);
        }

        // ------------------------------------------------------------------ layouts saved with the old sectors
        // Round 5 made the sectors deeper (T1 2.0 → 3.25 m, T2 2.5 → 3.5, T3 3.25 → 3.5; widths the same) for the staff
        // lane. A sector saved where the old model fitted keeps its spot:
        //  1. it grows toward the free side: slid along its own depth by the least that fits, preferring forward
        //     (toward its customers), so a sector against a wall keeps its back on the wall;
        //  2. otherwise it keeps the old footprint at that spot (for room and collisions) until the player moves it.
        static readonly Dictionary<int, Vector2> OldSectorSize = new Dictionary<int, Vector2> { { 1, new Vector2(2.5f, 2f) }, { 2, new Vector2(3.25f, 2.5f) }, { 3, new Vector2(4f, 3.25f) } };
        bool slidSome;
        /// <summary>QA: what happened to each sector under a layout saved with the old models.</summary>
        public static readonly Dictionary<string, int> MigrationCount = new Dictionary<string, int>();

        bool LegacyHere(Item it, Vector3 position, float rot) =>
            it.legacySize != Vector2.zero && it.piece == it.legacyPiece && (new Vector2(position.x - it.legacyAt.x, position.z - it.legacyAt.z)).sqrMagnitude < 1e-4f && Mathf.Abs(Mathf.DeltaAngle(rot, it.legacyRot)) < .5f;

        bool MigrateDeeper(Item it)
        {
            if (it.type != "sector" || it.outside || it.design || !it.root || !it.piece || string.IsNullOrEmpty(it.template)) return false;
            int tier = it.template[it.template.Length - 1] - '0';
            if (!OldSectorSize.TryGetValue(tier, out var old)) return false;
            float s = it.scale > 0 ? it.scale : 1;
            float grown = (Square(it.piece.max.y) - Square(it.piece.min.y)) - old.y * s; if (grown <= .01f) return false;
            var pos = it.root.position; var fwd = Quaternion.Euler(0, it.rot, 0) * Vector3.forward;
            // 1. slide: forward first (the back stays), up to the whole growth, in quarter-grid steps
            for (float d = .125f; d <= grown + .001f; d += .125f)
                foreach (var dir in new[] { -1f, 1f })
                {
                    var p = pos + fwd * (dir * d);
                    if (!Fits(it, p, it.rot, out _)) continue;
                    MoveTo(it, p); slidSome = true;
                    it.migrated = $"slid {d:0.00} m {(dir < 0 ? "forward" : "back")}"; Count(dir < 0 ? "grew toward the free side" : "slid back");
                    return true;
                }
            // 2. the old footprint at the saved spot (only where the old model really fitted)
            it.legacySize = old * s; it.legacyAt = pos; it.legacyRot = it.rot; it.legacyPiece = it.piece;
            if (Fits(it, pos, it.rot, out _)) { it.migrated = "old footprint kept until moved"; Count("kept the old footprint"); return true; }
            it.legacySize = Vector2.zero;
            return false;
        }

        static void Count(string what) { MigrationCount.TryGetValue(what, out var n); MigrationCount[what] = n + 1; }
    }
}
