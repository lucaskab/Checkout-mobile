using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;

namespace Checkout
{
    // Room for what the player could buy next (Lucas 24/10: "comprou um freezer e não conseguiu utilizar"). The shop
    // only sells a piece of furniture while there is a spot for it on the real floor: with the pieces standing where the
    // player put them and the ones still in the inventory put in first, each next piece (the next shelf, every sector
    // not built yet, the second checkout, the self-checkout kiosks) is tried along the walls and in the middle, and must
    // stand free and leave every counter reachable (the same rules as the build mode). The ones that do not fit go to
    // the game logic ({ kind: "room", blocked: [...] }, src/services/interior-room.ts): their buy buttons say
    // "Sem espaço na loja" until the player makes room or the market grows. Measured again whenever the floor changes;
    // the probes are put up and taken down in the same frame, never drawn.
    public partial class CheckoutInterior
    {
        CheckoutBridge roomBridge;
        string roomSignature, roomSent;
        float roomNext;
        /// <summary>The last list of pieces with no room sent to the game logic (JSON array), for the QA checks.</summary>
        public string RoomSent => roomSent;

        void Update()
        {
            if (!kit || editing || designMode || Time.unscaledTime < roomNext) return;
            roomNext = Time.unscaledTime + 1.5f;
            if (!roomBridge) roomBridge = FindAnyObjectByType<CheckoutBridge>();
            var s = roomBridge ? roomBridge.State : null;
            if (s?.shelves == null || s.era == null) return;
            var candidates = RoomCandidates(s);
            var signature = Signature(s, candidates);
            if (signature == roomSignature) return;
            roomSignature = signature;
            var blocked = MeasureRoom(candidates);
            var json = "[" + string.Join(",", blocked.Select(id => "\"" + id + "\"")) + "]";
            if (json == roomSent) return;
            roomSent = json;
            Debug.Log("CHECKOUT_ROOM " + json);
            CheckoutBridge.Emit("{\"kind\":\"room\",\"blocked\":" + json + "}");
        }

        // What can still be bought and stands on the floor: (piece id, type, template).
        List<(string id, string type, string template)> RoomCandidates(Snapshot s)
        {
            var list = new List<(string, string, string)>();
            bool Known(string id) => items.ContainsKey(id) || waiting.ContainsKey(id);
            // Shelves open one by one, in the order of the snapshot (src/data/shelf-types.ts).
            var next = s.shelves.FirstOrDefault(x => x != null && !x.unlocked && !x.building);
            if (next != null && !Known("shelf:" + next.id) && !CheckoutStall.BuiltIn("shelf:" + next.id))
                list.Add(("shelf:" + next.id, "shelf", ShelfTemplate(next)));
            foreach (var sector in s.sectors ?? System.Array.Empty<Sector>())
                if (sector != null && !sector.unlocked && !sector.building && layout.HasSector(sector.id) && kit.Find("sector-" + sector.id) && !Known("sector:" + sector.id))
                    list.Add(("sector:" + sector.id, "sector", "sector-" + sector.id));
            // Counters only where the player places them (not in the stalls and shops with a counter of their own).
            if (!CheckoutStall.Small || CheckoutStall.PlacedCounter)
            {
                var owned = s.ownedItems ?? System.Array.Empty<string>();
                if (!owned.Contains(CheckoutLanes.ExtraItem) && !Known("checkout:extra")) list.Add(("checkout:extra", "checkout", "checkout"));
                if (!owned.Contains(CheckoutLanes.SelfItem) && !Known("kiosk:1")) { list.Add(("kiosk:1", "kiosk", "kiosk")); list.Add(("kiosk:2", "kiosk", "kiosk")); }
            }
            return list;
        }

        string Signature(Snapshot s, List<(string id, string type, string template)> candidates)
        {
            var b = new StringBuilder();
            b.Append(s.era.id).Append('|').Append(layout.State.stage).Append(':').Append(layout.State.widthScale).Append(':').Append(layout.State.depthScale).Append('|');
            foreach (var it in items.Values.Where(i => i.root && !i.outside).OrderBy(i => i.id))
                b.Append(it.id).Append('@').Append(it.x.ToString("0.0")).Append(',').Append(it.z.ToString("0.0")).Append(',').Append(((int)it.rot)).Append(';');
            b.Append('|').Append(string.Join(",", waiting.Keys.OrderBy(k => k)));
            b.Append('|').Append(string.Join(",", candidates.Select(c => c.id)));
            return b.ToString();
        }

        // Pieces with no spot now. The inventory goes in first (it is already the player's), then each candidate alone,
        // except the two kiosks, which come together.
        List<string> MeasureRoom(List<(string id, string type, string template)> candidates)
        {
            var blocked = new List<string>();
            if (candidates.Count == 0) return blocked;
            var temps = new List<Item>();
            try
            {
                bool full = false;
                foreach (var w in waiting.OrderBy(w => w.Value.type == "checkout" || w.Value.type == "kiosk" ? 0 : 1).ThenBy(w => w.Key).ToList())
                {
                    if ((w.Value.type == "checkout" || w.Value.type == "kiosk") && CheckoutStall.Small && !CheckoutStall.PlacedCounter) continue;
                    var it = Probe(w.Key, w.Value.type, w.Value.template);
                    if (it == null) { full = true; break; }
                    temps.Add(it);
                }
                Item kiosk = null;
                foreach (var c in candidates)
                {
                    if (full) { blocked.Add(c.id); continue; }
                    if (c.id == "kiosk:2" && kiosk == null) { blocked.Add(c.id); continue; }
                    var it = Probe(c.id, c.type, c.template);
                    if (it == null) { blocked.Add(c.id); if (c.id == "kiosk:2") blocked.Add("kiosk:1"); continue; }
                    if (c.id == "kiosk:1") { kiosk = it; temps.Add(it); continue; }
                    Drop(it);
                }
            }
            finally { foreach (var it in temps) Drop(it); }
            return blocked.Distinct().ToList();
        }

        // Stands a throwaway copy of the piece at the nearest free, reachable spot (null: none).
        Item Probe(string id, string type, string template)
        {
            if (!kit.Find(template) || items.ContainsKey(id)) return null;
            var it = new Item { id = id, type = type, template = template, functional = true, placed = true };
            var d = DefaultFor(id, out _); it.rot = IsCounter(it) ? 90 : d.y;
            Build(it); if (!it.root) return null;
            it.root.gameObject.SetActive(false);   // never drawn, never picked
            items[id] = it;
            var floor = FloorRect; float y = it.root.position.y;
            var starts = new List<Vector3> { new Vector3(floor.center.x, y, floor.center.y) };
            for (int i = 0; i < 4; i++)
            {
                float fx = i % 2 == 0 ? .25f : .75f, fz = i < 2 ? .75f : .25f;
                starts.Add(new Vector3(Mathf.Lerp(floor.xMin, floor.xMax, fx), y, Mathf.Lerp(floor.yMin, floor.yMax, fz)));
            }
            foreach (var at in starts)
            {
                MoveTo(it, at);
                if (Settle(it) && Reachable(out _)) return it;
            }
            Drop(it);
            return null;
        }

        void Drop(Item it)
        {
            if (it == null) return;
            if (it.root) Destroy(it.root.gameObject);
            it.root = null;
            if (items.TryGetValue(it.id, out var same) && same == it) items.Remove(it.id);
        }
    }
}
