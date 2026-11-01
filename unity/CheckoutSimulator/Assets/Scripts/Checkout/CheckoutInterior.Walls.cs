using System.Linq;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Sector walls (Lucas 01/11): a special sector stands right against the market's walls, with no gap, and there its own
    // back panel ("Back Wall", the white tiles) hides so the market wall is its wall; standing free (or with less than
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
        readonly Dictionary<MeshFilter, Mesh> fullMesh = new Dictionary<MeshFilter, Mesh>();
        static readonly Dictionary<Mesh, Mesh> openBack = new Dictionary<Mesh, Mesh>();
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
            foreach (var gone in fullMesh.Keys.Where(k => !k).ToList()) fullMesh.Remove(gone); // (models swapped or removed)
            foreach (var it in items.Values)
            {
                if (it.type != "sector" || !it.root) continue;
                bool against = BackAgainstWall(it, out var why);
                WallState[it.id] = (against ? "against " : "free ") + why + "; " + ShowBackWall(it, !against);
            }
        }

        string ShowBackWall(Item it, bool show)
        {
            var panel = it.root.Find("Back Wall");
            if (panel) { if (panel.gameObject.activeSelf != show) panel.gameObject.SetActive(show); return show ? "Back Wall shown" : "Back Wall hidden"; }
            // TEMPORARY until the sectors with a separate "Back Wall" land (sector-walls-art): the merged meshes without
            // the back panel's triangles: everything behind the screens' plane (the tiles' face sits just behind it)
            // that rises above the floor plate, except the boards of the screens and of the name.
            var toRoot = it.root.worldToLocalMatrix;
            float cut = it.piece.max.y - .2f;
            var keep = new List<Bounds>();
            var screens = it.root.GetComponentInChildren<CheckoutSectorScreens>(true);
            if (screens)
            {
                var m = toRoot * screens.transform.localToWorldMatrix; float plane = float.MinValue;
                foreach (var q in screens.prices.Concat(screens.tickets))
                {
                    var c = m.MultiplyPoint3x4(q.center); plane = Mathf.Max(plane, c.z);
                    keep.Add(new Bounds(c + new Vector3(0, 0, .04f), new Vector3(q.size.x + .14f, q.size.y + .14f, .16f)));
                }
                if (plane > float.MinValue) cut = plane - .03f;
                foreach (var q in screens.names) { var c = m.MultiplyPoint3x4(q.center); keep.Add(new Bounds(c + new Vector3(0, 0, .04f), new Vector3(q.size.x + .2f, q.size.y + .2f, .16f))); }
            }
            int cutTris = 0, meshes = 0, unreadable = 0;
            foreach (var mf in it.root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!mf.sharedMesh || mf.transform.name.StartsWith("Anim Fill") || mf.GetComponent<TMPro.TMP_Text>()) continue; // (the screens' texts stay)
                if (!fullMesh.TryGetValue(mf, out var full)) { full = mf.sharedMesh; fullMesh[mf] = full; }
                meshes++;
                if (show) { if (mf.sharedMesh != full) mf.sharedMesh = full; continue; }
                var open = OpenBack(full, toRoot * mf.transform.localToWorldMatrix, cut, keep, out int n);
                if (!open) { unreadable++; continue; }
                cutTris += n;
                if (open && mf.sharedMesh != open) mf.sharedMesh = open;
            }
            return show ? $"panel shown ({meshes} meshes)" : $"panel cut: {cutTris} triangles behind z {cut:0.00} of {meshes} meshes ({unreadable} unreadable)";
        }

        public static string LastFaces = "";
        static readonly Dictionary<Mesh, int> openBackCut = new Dictionary<Mesh, int>();
        static Mesh OpenBack(Mesh full, Matrix4x4 toRoot, float cut, List<Bounds> keep, out int cutTris)
        {
            if (openBack.TryGetValue(full, out var cached)) { openBackCut.TryGetValue(full, out cutTris); return cached; }
            cutTris = 0;
            var open = ReadableCopy(full); if (!open) { openBack[full] = null; return null; }
            open.name = full.name + " (open back)";
            var v = open.vertices;
            // (QA: the big faces looking at the customers, by depth: where the panel's face is)
            var faces = new Dictionary<int, float>();
            for (int s = 0; s < open.subMeshCount; s++)
            {
                var t3 = open.GetTriangles(s);
                for (int i = 0; i < t3.Length; i += 3)
                {
                    Vector3 a = toRoot.MultiplyPoint3x4(v[t3[i]]), b = toRoot.MultiplyPoint3x4(v[t3[i + 1]]), c = toRoot.MultiplyPoint3x4(v[t3[i + 2]]);
                    var n = Vector3.Cross(b - a, c - a); float area = n.magnitude * .5f; if (area < 1e-5f) continue;
                    if (Mathf.Abs(n.normalized.z) < .7f || Mathf.Min(a.y, Mathf.Min(b.y, c.y)) < .25f) continue;
                    int key = Mathf.RoundToInt((a.z + b.z + c.z) / 3 * 100) * (n.z < 0 ? 1 : -1);
                    faces.TryGetValue(key, out var sum); faces[key] = sum + area;
                }
            }
            if (faces.Values.Sum() > 1f) LastFaces = $"{full.name}: " + string.Join(", ", faces.OrderByDescending(f => f.Value).Take(8).Select(f => $"z {Mathf.Abs(f.Key) / 100f:0.00} {(f.Key >= 0 ? "front" : "back")}-facing {f.Value:0.00} m2"));
            for (int s = 0; s < open.subMeshCount; s++)
            {
                var tris = open.GetTriangles(s); var kept = new List<int>(tris.Length);
                for (int i = 0; i < tris.Length; i += 3)
                {
                    bool back = true, board = true; float top = float.MinValue;
                    for (int k = 0; k < 3; k++)
                    {
                        var p = toRoot.MultiplyPoint3x4(v[tris[i + k]]);
                        if (p.z < cut) back = false;
                        top = Mathf.Max(top, p.y);
                        bool inBoard = false; foreach (var b in keep) if (b.Contains(p)) { inBoard = true; break; }
                        if (!inBoard) board = false;
                    }
                    if (back && top >= .25f && !board) { cutTris++; continue; } // (the floor plate stays)
                    kept.Add(tris[i]); kept.Add(tris[i + 1]); kept.Add(tris[i + 2]);
                }
                open.SetTriangles(kept, s);
            }
            openBack[full] = open; openBackCut[full] = cutTris;
            return open;
        }

        // The sector bodies are not readable (no CPU copy on the phone). The prototype reads them through the editor's
        // snapshot; in a build it leaves the panel up (the real models hide their own "Back Wall" child).
        static Mesh ReadableCopy(Mesh full)
        {
            if (full.isReadable) return Object.Instantiate(full);
#if UNITY_EDITOR
            var all = UnityEditor.MeshUtility.AcquireReadOnlyMeshData(full);
            try
            {
                var d = all[0]; int n = d.vertexCount;
                var m = new Mesh { indexFormat = n > 65535 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16 };
                using (var a = new Unity.Collections.NativeArray<Vector3>(n, Unity.Collections.Allocator.Temp)) { d.GetVertices(a); m.SetVertices(a); }
                if (d.HasVertexAttribute(UnityEngine.Rendering.VertexAttribute.Normal)) using (var a = new Unity.Collections.NativeArray<Vector3>(n, Unity.Collections.Allocator.Temp)) { d.GetNormals(a); m.SetNormals(a); }
                if (d.HasVertexAttribute(UnityEngine.Rendering.VertexAttribute.Tangent)) using (var a = new Unity.Collections.NativeArray<Vector4>(n, Unity.Collections.Allocator.Temp)) { d.GetTangents(a); m.SetTangents(a); }
                if (d.HasVertexAttribute(UnityEngine.Rendering.VertexAttribute.Color)) using (var a = new Unity.Collections.NativeArray<Color>(n, Unity.Collections.Allocator.Temp)) { d.GetColors(a); m.SetColors(a); }
                for (int ch = 0; ch < 4; ch++)
                    if (d.HasVertexAttribute(UnityEngine.Rendering.VertexAttribute.TexCoord0 + ch)) using (var a = new Unity.Collections.NativeArray<Vector2>(n, Unity.Collections.Allocator.Temp)) { d.GetUVs(ch, a); m.SetUVs(ch, a); }
                m.subMeshCount = d.subMeshCount;
                for (int s = 0; s < d.subMeshCount; s++)
                {
                    var sm = d.GetSubMesh(s);
                    using (var a = new Unity.Collections.NativeArray<int>(sm.indexCount, Unity.Collections.Allocator.Temp)) { d.GetIndices(a, s, true); m.SetIndices(a, sm.topology, s, false); }
                }
                m.bounds = full.bounds;
                return m;
            }
            finally { all.Dispose(); }
#else
            return null;
#endif
        }
    }
}
