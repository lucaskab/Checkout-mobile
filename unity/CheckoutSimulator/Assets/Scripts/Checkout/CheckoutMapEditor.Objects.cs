using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;

namespace Checkout
{
    // "Objetos" in the map editor: everything on the map is an item, like something bought in a shop and put
    // down. A bench is its wooden seat and its concrete feet, a lamp is its pole, globe and cap, a garden is
    // its border, soil and bushes. The scene was not built that way (parts often live in different groups),
    // so the items are worked out from the map itself:
    //  1. a part climbs to its parent while the parent's pieces touch each other (one compound object);
    //  2. separate parts are glued when one stands inside the other's base (soil in its border, a trunk in
    //     its crown) or rests on top of it (seat on its feet, globe on its pole).
    // Items are found on the original map of each stage, so moving one never glues it to another. Shift+click
    // adds items to the selection, Shift+drag draws a box, Alt+click takes a single part.
    public partial class CheckoutMapEditor
    {
        public class MapItem { public readonly List<Transform> parts = new List<Transform>(); public string name; public bool clone; public string group; }

        class PieceInfo { public Transform t; public Bounds all, foot; public bool solo, structure; public int root; }

        readonly Dictionary<Transform, MapItem> itemOfPiece = new Dictionary<Transform, MapItem>();
        readonly List<MapItem> selection = new List<MapItem>();
        readonly Dictionary<Transform, bool> compound = new Dictionary<Transform, bool>();
        readonly List<Transform> selectionQuads = new List<Transform>();
        bool partMode, objDrag, marquee, objMoved;
        Vector3 objOffset, objPivotStart; Vector2 marqueeStart;
        Image marqueeBox; CheckoutDesktopButton partButton;
        float navDirtyAt;

        // ---------------------------------------------------------------- building the item list
        void BuildIndex()
        {
            itemOfPiece.Clear(); selection.Clear(); compound.Clear();
            var found = new HashSet<Transform>();
            foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy || Skipped(r.transform)) continue;
                if (r.transform.IsChildOf(World.CloneRoot)) continue;
                found.Add(PieceOf(r.transform));
            }
            // A piece inside another piece belongs to it.
            var pieces = found.Where(p => { for (var a = p.parent; a; a = a.parent) if (found.Contains(a)) return false; return true; }).ToList();
            var info = new List<PieceInfo>();
            foreach (var p in pieces)
            {
                var rs = p.GetComponentsInChildren<MeshRenderer>().Where(r => r.enabled).ToArray();
                if (rs.Length == 0) continue;
                var all = rs[0].bounds; foreach (var r in rs) all.Encapsulate(r.bounds);
                var foot = FootOf(rs, all.min.y + .3f, all);
                bool big = Mathf.Max(all.size.x, all.size.z) > 8f, flatBig = all.size.y < .3f && all.size.x * all.size.z > 9f;
                info.Add(new PieceInfo { t = p, all = all, foot = foot, solo = big || flatBig, structure = UnderStructure(p), root = info.Count });
            }
            // Glue parts that make one object (union-find).
            int Find(int i) { while (info[i].root != i) { info[i].root = info[info[i].root].root; i = info[i].root; } return i; }
            var order = Enumerable.Range(0, info.Count).Where(i => !info[i].solo).OrderBy(i => info[i].all.min.x).ToList();
            for (int a = 0; a < order.Count; a++)
            {
                var A = info[order[a]];
                for (int b = a + 1; b < order.Count; b++)
                {
                    var B = info[order[b]];
                    if (B.all.min.x > A.all.max.x + .05f) break;
                    if (B.all.min.z > A.all.max.z + .05f || B.all.max.z < A.all.min.z - .05f) continue;
                    if (SameObject(A, B)) { int ra = Find(order[a]), rb = Find(order[b]); if (ra != rb) info[rb].root = ra; }
                }
            }
            var groups = new Dictionary<int, MapItem>();
            for (int i = 0; i < info.Count; i++)
            {
                int r = Find(i);
                if (!groups.TryGetValue(r, out var item)) groups[r] = item = new MapItem();
                item.parts.Add(info[i].t); itemOfPiece[info[i].t] = item;
            }
            foreach (var item in groups.Values) item.name = NameOf(item);
            RefreshCloneItems();
        }

        // Where the piece touches the ground: the outline of its lowest 30 cm (vertices, not boxes), so a tree
        // stands on its trunk and not on the whole crown.
        Bounds FootOf(MeshRenderer[] rs, float below, Bounds fallback)
        {
            var foot = new Bounds(); bool any = false;
            void Add(Vector3 p) { if (!any) { foot = new Bounds(p, Vector3.zero); any = true; } else foot.Encapsulate(p); }
            foreach (var r in rs)
            {
                if (r.bounds.min.y >= below) continue;
                var filter = r.GetComponent<MeshFilter>(); var mesh = filter ? filter.sharedMesh : null;
                Vector3[] v = null;
                if (mesh && !r.isPartOfStaticBatch)
                {
                    if (!meshCache.TryGetValue(mesh, out var data))
                    {
                        data = ReadMesh(mesh);
                        meshCache[mesh] = data;
                    }
                    v = data.v;
                }
                if (v == null || v.Length == 0)
                {
                    // Mesh data not readable here: a tall model (tree, lamp) stands on a narrow middle, others on their box.
                    var b = r.bounds;
                    if (b.size.y > 2f) { var e = new Vector3(b.extents.x * .18f, 0, b.extents.z * .18f); Add(new Vector3(b.center.x, b.min.y, b.center.z) - e); Add(new Vector3(b.center.x, b.min.y, b.center.z) + e); }
                    else { Add(b.min); Add(new Vector3(b.max.x, Mathf.Min(b.max.y, below), b.max.z)); }
                    continue;
                }
                var m = r.transform.localToWorldMatrix; int step = Mathf.Max(1, v.Length / 4000);
                for (int i = 0; i < v.Length; i += step) { var w = m.MultiplyPoint3x4(v[i]); if (w.y < below) Add(w); }
            }
            return any ? foot : fallback;
        }

        static float Area(Bounds b) => Mathf.Max(.0025f, b.size.x * b.size.z);
        static float Overlap(Bounds a, Bounds b)
        {
            float x = Mathf.Min(a.max.x, b.max.x) - Mathf.Max(a.min.x, b.min.x), z = Mathf.Min(a.max.z, b.max.z) - Mathf.Max(a.min.z, b.min.z);
            return x <= 0 || z <= 0 ? 0 : x * z;
        }

        static bool SameObject(PieceInfo a, PieceInfo b)
        {
            // Two tall things (trees, lamps, signals) are always separate items.
            if (a.all.size.y > 2.5f && b.all.size.y > 2.5f) return false;
            if (Area(b.foot) > Area(a.foot)) { var t = a; a = b; b = t; }
            bool verticalTouch = b.all.min.y <= a.all.max.y + .15f && a.all.min.y <= b.all.max.y + .15f;
            // Stands inside the other's base: soil in its border, trunk in its planter, bushes in the bed.
            // The centre must be well inside (80 %) so a bench next to a round planter stays a bench.
            var c = b.foot.center; var f = a.foot;
            bool inside = Mathf.Abs(c.x - f.center.x) <= f.extents.x * .8f && Mathf.Abs(c.z - f.center.z) <= f.extents.z * .8f;
            // Trees, lamps and signals are never swallowed by the ground piece they stand on (rocks, beds).
            bool tall = a.all.size.y > 2.5f || b.all.size.y > 2.5f;
            // On the shop building only small fixtures glue (soil in a planter, not everything on the steps).
            bool structure = a.structure || b.structure;
            if (!tall && verticalTouch && inside && (!structure || (Area(a.foot) <= 3f && b.all.size.y < .3f)) && Overlap(b.foot, a.foot) >= .6f * Area(b.foot)) return true;
            // Rests on top of the other: seat on its feet, globe on its pole, cap on its globe.
            PieceInfo lower = null, upper = null;
            if (Mathf.Abs(b.all.min.y - a.all.max.y) <= .12f) { lower = a; upper = b; }
            else if (Mathf.Abs(a.all.min.y - b.all.max.y) <= .12f) { lower = b; upper = a; }
            if (lower == null) return false;
            // Things standing on a step, deck or slab are their own items (a planter on the entrance steps).
            if (lower.all.size.y < .35f && Area(lower.all) > 1.5f && Area(upper.all) < .5f * Area(lower.all)) return false;
            if (structure && Area(lower.all) > 1f) return false; // a lamp on a planter wall stays a lamp
            return Overlap(a.all, b.all) >= .4f * Mathf.Min(Area(a.all), Area(b.all));
        }

        // Climbs from a mesh to the object it is part of: the parent counts while its pieces touch each other.
        Transform PieceOf(Transform leaf)
        {
            var t = leaf;
            while (true)
            {
                var p = t.parent;
                if (!p || !p.parent || p == World.CloneRoot) break;
                if (t.GetComponent<CheckoutStageItem>()) break;
                if (!Compound(p)) break;
                t = p;
            }
            return t;
        }

        bool Compound(Transform p)
        {
            if (compound.TryGetValue(p, out var known)) return known;
            var boxes = new List<Bounds>();
            var own = p.GetComponent<MeshRenderer>();
            if (own && own.enabled) boxes.Add(own.bounds);
            foreach (Transform c in p)
            {
                if (!c.gameObject.activeInHierarchy) continue;
                var rs = c.GetComponentsInChildren<MeshRenderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                if (b.size.y < .3f && b.size.x * b.size.z > 9f) continue; // a floor under the group's pieces
                boxes.Add(b);
                if (boxes.Count > 80) break;
            }
            bool result;
            if (boxes.Count > 80) result = false;
            else
            {
                var all = boxes.Count > 0 ? boxes[0] : new Bounds();
                foreach (var b in boxes) all.Encapsulate(b);
                // Inside the shop building only small fixtures count as one object (lamps, signs), never whole walls.
                float cap = UnderStructure(p) ? 3f : 25f;
                if (boxes.Count > 0 && Mathf.Max(all.size.x, all.size.z) > cap) result = false;
                else
                {
                    // Connected when every piece touches the rest (breadth first over touching boxes).
                    var seen = new bool[boxes.Count]; var queue = new Queue<int>(); int reached = 0;
                    if (boxes.Count > 0) { seen[0] = true; queue.Enqueue(0); }
                    while (queue.Count > 0)
                    {
                        int i = queue.Dequeue(); reached++;
                        var a = boxes[i]; a.Expand(.08f);
                        for (int j = 0; j < boxes.Count; j++) if (!seen[j] && a.Intersects(boxes[j])) { seen[j] = true; queue.Enqueue(j); }
                    }
                    result = reached == boxes.Count;
                }
            }
            compound[p] = result;
            return result;
        }

        static bool UnderStructure(Transform t)
        {
            for (var a = t; a; a = a.parent) if (a.name == "Market Shell") return true;
            return false;
        }

        string NameOf(MapItem item)
        {
            var main = item.parts.OrderByDescending(p => { var b = BoundsOf(p); return b.size.x * b.size.z * Mathf.Max(.1f, b.size.y); }).First();
            var n = BaseName(main.name);
            if (n.Length < 3 || n.StartsWith("Mesh") || n.StartsWith("tripo") || n.StartsWith("node") || n.StartsWith("Object")) n = main.parent ? BaseName(main.parent.name) : n;
            if (item.clone) { var data = CloneData(main); if (data != null && data.source != null && data.source.StartsWith("kit:")) n = data.source.Substring(4); }
            return Pretty(n);
        }

        DesignObject CloneData(Transform t) => World.IsClone(t, out var data) ? data : null;

        // Copies placed in the editor: one item per copy group.
        void RefreshCloneItems()
        {
            foreach (var key in itemOfPiece.Where(p => p.Value.clone || !p.Key).Select(p => p.Key).ToList()) itemOfPiece.Remove(key);
            var byGroup = new Dictionary<string, MapItem>();
            foreach (var c in World.Clones)
            {
                if (!c.root) continue;
                string g = string.IsNullOrEmpty(c.data.group) ? c.data.id : c.data.group;
                if (!byGroup.TryGetValue(g, out var item)) byGroup[g] = item = new MapItem { clone = true, group = g };
                item.parts.Add(c.root); itemOfPiece[c.root] = item;
            }
            foreach (var item in byGroup.Values) item.name = NameOf(item);
            selection.RemoveAll(i => i.parts.Any(p => !p));
        }

        MapItem ItemOf(Transform leaf, bool part)
        {
            for (var t = leaf; t; t = t.parent)
                if (itemOfPiece.TryGetValue(t, out var item))
                {
                    if (!part || item.parts.Count == 1) return item;
                    var single = new MapItem { name = Pretty(BaseName(t.name)), clone = item.clone, group = item.group };
                    single.parts.Add(t); return single;
                }
            // Something that appeared after the list was made (e.g. a later stage's dressing).
            var p = PieceOf(leaf);
            var fresh = new MapItem { name = Pretty(BaseName(p.name)) }; fresh.parts.Add(p); itemOfPiece[p] = fresh;
            return fresh;
        }

        // ---------------------------------------------------------------- selection
        IEnumerable<Transform> SelectedParts()
        {
            var set = new HashSet<Transform>(selection.SelectMany(i => i.parts).Where(p => p));
            return set.Where(p => { for (var a = p.parent; a; a = a.parent) if (set.Contains(a)) return false; return true; }).ToList();
        }

        Bounds SelectionBounds()
        {
            var parts = SelectedParts().ToList();
            var b = BoundsOf(parts[0]); foreach (var p in parts.Skip(1)) b.Encapsulate(BoundsOf(p));
            return b;
        }

        Vector3 Pivot() { var b = SelectionBounds(); return new Vector3(b.center.x, b.min.y, b.center.z); }

        void SelectItems(IEnumerable<MapItem> items, bool add = false)
        {
            if (!add) selection.Clear();
            foreach (var i in items) if (i != null && !selection.Contains(i)) selection.Add(i);
            piece = null;
            UpdateObjectLabel(); ShowSelection();
        }

        void ToggleItem(MapItem item)
        {
            var same = selection.FirstOrDefault(s => s.parts.SequenceEqual(item.parts));
            if (same != null) selection.Remove(same); else selection.Add(item);
            UpdateObjectLabel(); ShowSelection();
        }

        void UpdateObjectLabel()
        {
            if (!selectedName || tool != Tool.Objects) return;
            if (selection.Count == 0) { selectedName.text = "Nenhum objeto selecionado   <size=15><color=#BFD0E8>Shift+clique junta itens • Shift+arrastar faz uma caixa de seleção • Alt+clique pega só uma parte</color></size>"; return; }
            if (selection.Count == 1)
            {
                var i = selection[0];
                selectedName.text = i.name + "   <size=15><color=#BFD0E8>" + (i.clone ? "item adicionado" : "item do mapa") + (i.parts.Count > 1 ? " • " + i.parts.Count + " partes juntas" : "") + "</color></size>";
            }
            else selectedName.text = selection.Count + " itens selecionados   <size=15><color=#BFD0E8>movem, giram e mudam de tamanho juntos</color></size>";
        }

        void ShowObjectSelection()
        {
            int n = 0;
            foreach (var item in selection)
            {
                var parts = item.parts.Where(p => p).ToList(); if (parts.Count == 0) continue;
                var b = BoundsOf(parts[0]); foreach (var p in parts.Skip(1)) b.Encapsulate(BoundsOf(p));
                if (selectionQuads.Count <= n) selectionQuads.Add(Quad("Editor select", pickMaterial).transform);
                var q = selectionQuads[n++]; q.gameObject.SetActive(true);
                q.SetPositionAndRotation(new Vector3(b.center.x, Mathf.Max(b.min.y, 0) + .04f, b.center.z), Quaternion.Euler(90, 0, 0));
                q.localScale = new Vector3(b.size.x + .2f, b.size.z + .2f, 1);
            }
            for (int i = n; i < selectionQuads.Count; i++) selectionQuads[i].gameObject.SetActive(false);
        }

        void HideObjectSelection() { foreach (var q in selectionQuads) if (q) q.gameObject.SetActive(false); }

        void TogglePartMode()
        {
            partMode = !partMode;
            if (partButton) partButton.Apply(Data(partMode ? "Só a parte" : "Item inteiro", "secondary", true, "", partMode));
            Say(partMode ? "Selecionando uma parte de cada vez (ex.: só o assento do banco)." : "Selecionando o item inteiro (banco completo, poste completo...).");
        }

        // ---------------------------------------------------------------- changing the selection
        bool NeedObject() { if (selection.Count > 0) return true; Say("Selecione um objeto primeiro.", true); return false; }

        void ChangeParts(System.Action<List<Transform>, Vector3> change)
        {
            var parts = SelectedParts().ToList(); var pivot = Pivot();
            foreach (var p in parts) if (!World.IsClone(p, out _)) World.Touch(p);
            change(parts, pivot);
            foreach (var p in parts) Record(p);
            ShowSelection(); MarkNavigation();
        }

        void TurnObject(float delta)
        {
            if (!NeedObject()) return; BeginChange();
            var q = Quaternion.Euler(0, delta, 0);
            ChangeParts((parts, pivot) => { foreach (var p in parts) { p.position = pivot + q * (p.position - pivot); p.rotation = q * p.rotation; } });
        }

        void ScaleObject(float factor)
        {
            if (!NeedObject()) return; BeginChange();
            ChangeParts((parts, pivot) => { foreach (var p in parts) { p.position = pivot + (p.position - pivot) * factor; p.localScale *= factor; } });
            UpdateObjectLabel();
        }

        void LiftObject(float dy)
        {
            if (!NeedObject()) return; BeginChange();
            ChangeParts((parts, pivot) => { foreach (var p in parts) p.position += Vector3.up * dy; });
        }

        void MoveSelection(Vector3 delta)
        {
            foreach (var p in SelectedParts()) p.position += delta;
            ShowObjectSelection();
        }

        void DuplicateObject()
        {
            if (!NeedObject()) return;
            var b = SelectionBounds(); var step = new Vector3(Mathf.Max(1, Mathf.Ceil(b.size.x + .3f)), 0, 0);
            BeginChange();
            var copies = new List<MapItem>();
            foreach (var item in selection.ToList())
            {
                var copy = CopyItem(item.parts.Where(p => p).ToList(), step, item.name);
                if (copy != null) copies.Add(copy);
            }
            if (copies.Count == 0) { Say("Não foi possível duplicar.", true); return; }
            SelectItems(copies); MarkNavigation();
            Say(copies.Count == 1 ? "Duplicado ao lado. Arraste para ajustar." : copies.Count + " itens duplicados ao lado.");
        }

        // A new copy of these parts, offset by `delta`, kept together as one item.
        MapItem CopyItem(List<Transform> parts, Vector3 delta, string name)
        {
            string group = "g" + System.Guid.NewGuid().ToString("N").Substring(0, 8);
            var item = new MapItem { clone = true, group = group, name = name };
            foreach (var p in parts)
            {
                string source = World.IsClone(p, out var data) ? data.source : "path:" + CheckoutMapDesign.PathOf(p);
                var t = World.AddClone(new DesignObject { source = source, group = group, position = p.position + delta, euler = p.eulerAngles, scale = p.lossyScale });
                if (t) { item.parts.Add(t); itemOfPiece[t] = item; }
            }
            return item.parts.Count > 0 ? item : null;
        }

        void RemoveObject()
        {
            if (!NeedObject()) return;
            BeginChange();
            int removed = 0, hidden = 0;
            foreach (var p in SelectedParts())
            {
                if (World.IsClone(p, out var data)) { itemOfPiece.Remove(p); World.RemoveClone(data.id); removed++; continue; }
                World.Touch(p);
                World.SetOverride(new DesignObject { path = CheckoutMapDesign.PathOf(p), position = p.position, euler = p.eulerAngles, scale = p.localScale, hidden = true });
                hidden++;
            }
            selection.Clear(); ShowSelection(); UpdateObjectLabel(); MarkNavigation();
            Say(hidden > 0 ? "Oculto nesta loja. Em \"Ocultos\" dá para mostrar de novo." : "Removido.");
        }

        void ResetObject()
        {
            if (!NeedObject()) return;
            BeginChange(); int n = 0;
            foreach (var p in SelectedParts()) if (!World.IsClone(p, out _)) { World.RemoveOverride(CheckoutMapDesign.PathOf(p)); n++; }
            ShowSelection(); MarkNavigation();
            Say(n > 0 ? "Voltou ao lugar original." : "Itens adicionados por você não têm lugar original: use Remover.", n == 0);
        }

        // ---------------------------------------------------------------- pointer (Objetos)
        void ObjectsFrame()
        {
            var ray = sim.view.ScreenPointToRay(Input.mousePosition);
            bool shift = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
            bool alt = Input.GetKey(KeyCode.LeftAlt) || Input.GetKey(KeyCode.RightAlt) || partMode;
            if (Input.GetMouseButtonDown(0) && !OverUi)
            {
                downAt = Input.mousePosition; objMoved = false;
                var leaf = PickLeaf(ray);
                if (leaf)
                {
                    var item = ItemOf(leaf, alt);
                    if (shift) { ToggleItem(item); return; }
                    if (!selection.Any(s => s.parts.SequenceEqual(item.parts))) SelectItems(new[] { item });
                    var pivot = Pivot();
                    dragPlane = new Plane(Vector3.up, pivot);
                    if (dragPlane.Raycast(ray, out var d)) { objDrag = true; objOffset = pivot - ray.GetPoint(d); objPivotStart = pivot; sim.cameraLocked = true; }
                }
                else if (shift) { marquee = true; marqueeStart = Input.mousePosition; sim.cameraLocked = true; }
            }
            if (objDrag && Input.GetMouseButton(0))
            {
                if (!objMoved && ((Vector2)Input.mousePosition - downAt).magnitude > 6)
                {
                    objMoved = true; Dragging = true; BeginChange();
                    foreach (var p in SelectedParts()) if (!World.IsClone(p, out _)) World.Touch(p);
                }
                if (objMoved && dragPlane.Raycast(ray, out var d))
                {
                    var target = ray.GetPoint(d) + objOffset;
                    target.x = Snap1(target.x); target.z = Snap1(target.z); target.y = objPivotStart.y;
                    var now = Pivot(); now.y = objPivotStart.y;
                    MoveSelection(target - now);
                }
            }
            if (marquee) DrawMarquee(Input.mousePosition);
            if (Input.GetMouseButtonUp(0))
            {
                if (objDrag) EndObjectDrag();
                else if (marquee) FinishMarquee(Input.mousePosition, shift);
                else if (!OverUi && !shift && ((Vector2)Input.mousePosition - downAt).magnitude < 6) { selection.Clear(); UpdateObjectLabel(); ShowSelection(); }
            }
        }

        void EndObjectDrag()
        {
            objDrag = false; Dragging = false; sim.cameraLocked = false;
            if (!objMoved) return;
            objMoved = false;
            foreach (var p in SelectedParts()) Record(p);
            ShowSelection(); MarkNavigation();
        }

        Transform PickLeaf(Ray ray)
        {
            Transform leaf = null; float best = float.MaxValue;
            foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || r.forceRenderingOff || !r.gameObject.activeInHierarchy) continue;
                var b = r.bounds;
                if (b.size.x > 40 || b.size.z > 40) continue; // streets, terrain and other huge ground pieces
                if (!b.IntersectRay(ray, out var near) || near > best) continue;
                if (Skipped(r.transform)) continue;
                float hit = MeshHit(r, ray);
                if (hit < best) { best = hit; leaf = r.transform; }
            }
            return leaf;
        }

        void DrawMarquee(Vector2 now)
        {
            if (!marqueeBox)
            {
                marqueeBox = U.Box(root, "Marquee", "E0B040", 4, Vector2.zero, Vector2.zero); marqueeBox.color = new Color(1f, .8f, .25f, .22f); marqueeBox.raycastTarget = false;
                marqueeBox.rectTransform.pivot = Vector2.zero;
            }
            var canvas = root.GetComponent<Canvas>(); float k = canvas ? canvas.scaleFactor : 1;
            var min = Vector2.Min(marqueeStart, now) / k; var size = (Vector2.Max(marqueeStart, now) - Vector2.Min(marqueeStart, now)) / k;
            var rt = marqueeBox.rectTransform; rt.anchorMin = rt.anchorMax = Vector2.zero; rt.anchoredPosition = min; rt.sizeDelta = size;
            marqueeBox.gameObject.SetActive(true);
        }

        void FinishMarquee(Vector2 end, bool add)
        {
            marquee = false; sim.cameraLocked = false;
            if (marqueeBox) marqueeBox.gameObject.SetActive(false);
            var rect = Rect.MinMaxRect(Mathf.Min(marqueeStart.x, end.x), Mathf.Min(marqueeStart.y, end.y), Mathf.Max(marqueeStart.x, end.x), Mathf.Max(marqueeStart.y, end.y));
            if (rect.width < 6 || rect.height < 6) return;
            var picked = new List<MapItem>();
            foreach (var item in itemOfPiece.Values.Distinct())
            {
                var parts = item.parts.Where(p => p && p.gameObject.activeInHierarchy).ToList(); if (parts.Count == 0) continue;
                if (parts.All(p => p.GetComponentsInChildren<Renderer>().All(r => r.forceRenderingOff))) continue;
                var b = BoundsOf(parts[0]); foreach (var p in parts.Skip(1)) b.Encapsulate(BoundsOf(p));
                if (Mathf.Max(b.size.x, b.size.z) > 30) continue;
                var s = sim.view.WorldToScreenPoint(b.center);
                if (s.z > 0 && rect.Contains(new Vector2(s.x, s.y))) picked.Add(item);
            }
            SelectItems(picked, add);
            Say(picked.Count == 0 ? "Nenhum item dentro da caixa." : picked.Count + " itens selecionados.");
        }

        // People and the navigation follow the new map a moment after a change.
        void MarkNavigation() { navDirtyAt = Time.unscaledTime + .8f; }

        void NavigationFrame()
        {
            if (navDirtyAt <= 0 || Time.unscaledTime < navDirtyAt || Dragging) return;
            navDirtyAt = 0;
            CheckoutBlockPaths.Invalidate();
            map.FurnitureChanged();
        }

        // ---------------------------------------------------------------- catalogue of map items
        readonly List<MapItem> catalogueItems = new List<MapItem>();

        IEnumerable<(string label, string source, string icon)> ItemCatalogue()
        {
            catalogueItems.Clear();
            var seen = new HashSet<string>();
            foreach (var item in itemOfPiece.Values.Distinct().Where(i => !i.clone).OrderBy(i => i.name))
            {
                var parts = item.parts.Where(p => p).ToList(); if (parts.Count == 0) continue;
                var b = BoundsOf(parts[0]); foreach (var p in parts.Skip(1)) b.Encapsulate(BoundsOf(p));
                if (Mathf.Max(b.size.x, b.size.z) > 16 || b.size.y < .05f) continue;
                if (!seen.Add(item.name.ToLowerInvariant())) continue;
                catalogueItems.Add(item);
                yield return (item.name + (parts.Count > 1 ? " (" + parts.Count + " partes)" : ""), "item:" + (catalogueItems.Count - 1), "");
            }
        }

        void AddItemFromCatalogue(int index)
        {
            if (index < 0 || index >= catalogueItems.Count) return;
            var template = catalogueItems[index]; var parts = template.parts.Where(p => p).ToList(); if (parts.Count == 0) return;
            var b = BoundsOf(parts[0]); foreach (var p in parts.Skip(1)) b.Encapsulate(BoundsOf(p));
            var ground = ScreenCenterOn(CheckoutInterior.Ground);
            var delta = new Vector3(Snap1(ground.x) - b.center.x, CheckoutInterior.Ground - b.min.y, Snap1(ground.z) - b.center.z);
            BeginChange();
            var copy = CopyItem(parts, delta, template.name);
            if (copy == null) { Say("Não foi possível copiar esse item.", true); return; }
            SelectItems(new[] { copy }); MarkNavigation();
            Say(template.name + " adicionado no centro da tela. Arraste para o lugar.");
        }
    }
}
