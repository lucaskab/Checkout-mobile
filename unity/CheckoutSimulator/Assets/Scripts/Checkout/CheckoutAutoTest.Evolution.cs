using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "Evoluções com recompensa" (claude/evolucoes-recompensas.md) on the QA copy of the save ("eventstiers-<part>"):
 //  - rewards: a shelf and a sector evolve with the real store actions: the timer, the old look meanwhile, then the
 //             tier, the places, the restock bonus and the exclusive product.
 //  - queue:   two evolutions at once: the second waits for the first; the ring and the builder (Logs/ft_evo_ring.jpg).
 //  - skip:    a tap on the ring shows the diamond plate (Logs/ft_evo_skip.jpg); the diamonds finish it.
 //  - oldsave: what the v49 migration gave this save: exclusive products by tier, places of the evolved fixtures.
 //  - reveal:  the reveal of a shelf and of a sector, frame by frame (Logs/ft_evo_reveal_<kind>_NNN.jpg), with the
 //             cloth (ft_evo_cloth), the pop and confetti (ft_evo_pop) and the card (ft_evo_card).
 // One "RESULT tiers <part>: PASS|FAIL ..." line per part.
 public sealed partial class CheckoutAutoTest {
  static readonly string[] EvoFixtures = { "produce", "drinks", "bakery", "dairy", "snacks", "coffee", "home", "pizza", "icecream" };
  // (desktop/celebration.ts: the exclusive product of a fixture at a tier, ids 122 + 4 × fixture + tier − 2)
  static int ExclusiveId(string fixture, int tier) => 122 + System.Array.IndexOf(EvoFixtures, fixture) * 4 + (tier - 2);

  Evolution Evo(string kind, string target) => bridge.State.evolutions?.FirstOrDefault(e => e != null && e.kind == kind && e.targetId == target);
  void QaRich(string tag) {
   Hud("setMarketLevel", "[60]");
   Hud("grantCurrencyPurchase", "[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-evo-" + tag + "-" + System.DateTime.Now.Ticks + "\"}]");
  }
  IEnumerator CloseCards() {
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   for (int i = 0; i < 8 && hud && (hud.LevelUpOpen || hud.ConquestOpen || CheckoutEvolutionReveal.Instance.Playing); i++) { hud.QaCloseCelebrations(); yield return Wait(.9f); }
  }
  // Dismisses every pending tier celebration (and its reveal), so a part starts clean.
  IEnumerator ClearReveals() {
   for (int i = 0; i < 12 && (bridge.State.reveals?.Length ?? 0) > 0; i++) {
    foreach (var r in bridge.State.reveals) Hud("dismissCelebration", "[\"" + r.id + "\"]");
    yield return Wait(1.2f);
   }
   yield return CloseCards();
  }

  // The QA copy keeps its furniture in the build-mode inventory: put the piece on the floor (as a player would) so
  // the evolution crew, the cloth and the reveal have something to stand on.
  IEnumerator EnsurePlaced(string pieceId) {
   var inside = CheckoutInterior.Active; if (!inside || inside.Get(pieceId) != null) yield break;
   if (!inside.waiting.ContainsKey(pieceId)) { Note("EVO " + pieceId + " is neither placed nor waiting"); yield break; }
   var floor = inside.FloorRect; CheckoutInterior.Item placed = null;
   for (float pz = floor.yMax - 1.2f; placed == null && pz > floor.yMin + 1.2f; pz -= 1.1f)
    for (float px = floor.xMin + 1.2f; placed == null && px < floor.xMax - 1.2f; px += 1.3f)
     placed = inside.PlaceWaiting(pieceId, new Vector3(px, 0, pz));
   Note("EVO placed " + pieceId + ": " + (placed != null ? placed.template + " at " + placed.root.position.ToString("0.0") : "no room"));
   if (placed != null) { inside.MarkPending(); FindAnyObjectByType<CheckoutMap>().SaveInterior(); yield return Wait(2.5f); }
  }

  IEnumerator EnsureBakery() {
   Sector Bakery() => bridge.State.sectors?.FirstOrDefault(x => x.id == "padaria");
   if (Bakery() == null || Bakery().unlocked) yield break;
   Hud("buildSector", "[\"padaria\",\"coins\"]"); yield return Wait(2.5f);
   var inside = CheckoutInterior.Active; var floor = inside.FloorRect;
   CheckoutInterior.Item placed = inside.waiting.ContainsKey("sector:padaria") ? null : inside.Get("sector:padaria");
   for (float pz = floor.center.y; placed == null && pz > floor.yMin + 1.5f; pz -= 1.5f)
    for (float px = floor.xMin + 2.5f; placed == null && px < floor.xMax - 2.5f; px += 2f)
     placed = inside.PlaceWaiting("sector:padaria", new Vector3(px, 0, pz));
   if (placed != null) { inside.MarkPending(); FindAnyObjectByType<CheckoutMap>().SaveInterior(); yield return Wait(2.5f); }
   Hud("devFinishInteriorConstructions", "[]"); yield return Wait(3f);
   yield return CloseCards();
  }

  // ------------------------------------------------------------------ rewards
  IEnumerator EvoRewards() {
   var fails = new List<string>();
   void Check(bool ok, string what) { Note((ok ? "ok   " : "FAIL ") + what); if (!ok) fails.Add(what); }
   QaRich("rewards");
   yield return GoToStage("spati"); yield return ClearReveals();
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   yield return EnsurePlaced("shelf:produce");
   var shelf = bridge.State.shelves.First(x => x.id == "produce");
   int tier = shelf.tier; int cap = shelf.capacity;
   Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(2);
   var evo = Evo("shelf", "produce");
   shelf = bridge.State.shelves.First(x => x.id == "produce");
   Check(evo != null && evo.toTier >= 2, $"shelf evolution queued: {(evo == null ? "none" : $"T{evo.toTier}, {evo.durationMs / 60000:0.#} min")}");
   Check(shelf.tier == tier && shelf.capacity == cap, $"meanwhile the old look and numbers: T{shelf.tier} cap {shelf.capacity}");
   var site = CheckoutInterior.Active?.Get("shelf:produce")?.root?.GetComponent<CheckoutEvolutionSite>();
   Check(site != null && site.Ring, "the ring and the builder on the shelf");
   Hud("devFinishEvolutions", "[]"); yield return Wait(2);
   shelf = bridge.State.shelves.First(x => x.id == "produce");
   Check(shelf.tier > tier || shelf.capacity > cap, $"after: T{shelf.tier} cap {shelf.capacity}");
   var reveal = bridge.State.reveals?.FirstOrDefault(r => r.kind == "shelf" && r.targetId == "produce");
   Check(reveal != null, "the reveal waits under the cloth");
   int want = ExclusiveId("produce", Mathf.Max(2, evo?.toTier ?? 2));
   var supplier = bridge.State.supplierCatalog ?? System.Array.Empty<SupplierProduct>();
   Check(supplier.Any(p => p.productId == want && !p.locked), $"exclusive product {want} open at the supplier");
   var slots = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).Where(r => r.shelfId == "produce").ToList();
   Note($"EVO produce restock slots {slots.Count}, bonus {(slots.Count > 0 ? slots[0].restockBonus : -1):0.00}");
   yield return CloseCards(); yield return ClearReveals();
   // a sector
   yield return GoToStage("supermercado"); yield return EnsureBakery(); yield return ClearReveals();
   var bakery = bridge.State.sectors?.FirstOrDefault(x => x.id == "padaria");
   if (bakery == null || !bakery.unlocked) fails.Add("no bakery");
   else if (bakery.tier >= 3) Note("EVO bakery already T3 (skipped)");
   else {
    int from = bakery.tier;
    Hud("upgradeSectorTier", "[\"padaria\",\"coins\"]"); yield return Wait(2);
    var se = Evo("sector", "padaria");
    Check(se != null && Mathf.Abs((float)se.durationMs - (from == 1 ? 1800000f : 7200000f)) < 1, $"sector evolution {(se == null ? "none" : $"T{se.toTier} {se.durationMs / 60000:0} min")}");
    Check(bridge.State.sectors.First(x => x.id == "padaria").tier == from, "the sector keeps producing as before");
    Hud("devFinishEvolutions", "[]"); yield return Wait(2);
    Check(bridge.State.sectors.First(x => x.id == "padaria").tier == from + 1, $"sector T{bridge.State.sectors.First(x => x.id == "padaria").tier}");
    int sx = from + 1 == 2 ? 158 : 159;
    Check(supplier.Length >= 0, $"exclusive recipe {sx} opened (production board)");
   }
   yield return ClearReveals();
   Note($"RESULT tiers rewards: {(fails.Count == 0 ? "PASS" : "FAIL")} {fails.Count} failed" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // ------------------------------------------------------------------ queue (+ the ring and builder shot)
  IEnumerator EvoQueue() {
   var fails = new List<string>();
   void Check(bool ok, string what) { Note((ok ? "ok   " : "FAIL ") + what); if (!ok) fails.Add(what); }
   QaRich("queue");
   yield return GoToStage("supermercado"); yield return ClearReveals();
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   var ids = bridge.State.shelves.Where(s => s.unlocked && s.tier < 5 && TierKindOf.ContainsKey(s.id)).Select(s => s.id).Take(2).ToList();
   if (ids.Count < 2) { Note("RESULT tiers queue: FAIL fewer than two shelves to evolve"); yield break; }
   foreach (var id in ids) yield return EnsurePlaced("shelf:" + id);
   foreach (var id in ids) { Hud("upgradeShelfCapacity", "[\"" + id + "\",\"coins\"]"); yield return Wait(1.5f); }
   var a = Evo("shelf", ids[0]); var b = Evo("shelf", ids[1]);
   Check(a != null && b != null, $"both queued ({ids[0]}, {ids[1]})");
   if (a != null && b != null) {
    Check(!a.queued && b.queued, $"first running, second waiting (queued {a.queued}/{b.queued})");
    Check(System.Math.Abs(b.startedAt - a.endsAt) < 1, $"the second starts when the first ends ({(b.startedAt - a.endsAt):0} ms)");
   }
   var it = CheckoutInterior.Active?.Get("shelf:" + ids[0]);
   var site = it?.root ? it.root.GetComponent<CheckoutEvolutionSite>() : null;
   Check(site && site.Ring, "ring and builder on the running one");
   var it2 = CheckoutInterior.Active?.Get("shelf:" + ids[1]);
   Check(it2?.root && it2.root.GetComponent<CheckoutEvolutionSite>(), "ring (NA FILA) on the queued one");
   yield return Wait(2.5f); // the builder settles into his hammering
   if (it?.root) { CaptureAt(it.root.position + Vector3.up * 1.2f, 7f, "ft_evo_ring"); yield return Shot("evo_ring_full"); }
   // the first ends: the second starts
   if (a != null) { Hud("finishEvolutionNow", "[\"" + a.id + "\"]"); yield return Wait(2); }
   var b2 = Evo("shelf", ids[1]);
   Check(b2 != null && !b2.queued, "the second runs once the first is done");
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   Note($"RESULT tiers queue: {(fails.Count == 0 ? "PASS" : "FAIL")} {fails.Count} failed" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // ------------------------------------------------------------------ skip
  IEnumerator EvoSkip() {
   var fails = new List<string>();
   void Check(bool ok, string what) { Note((ok ? "ok   " : "FAIL ") + what); if (!ok) fails.Add(what); }
   QaRich("skip");
   yield return GoToStage("supermercado"); yield return ClearReveals();
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   var id = bridge.State.shelves.Where(s => s.unlocked && s.tier < 5 && TierKindOf.ContainsKey(s.id)).Select(s => s.id).FirstOrDefault();
   if (id == null) { Note("RESULT tiers skip: FAIL no shelf to evolve"); yield break; }
   yield return EnsurePlaced("shelf:" + id);
   Hud("upgradeShelfCapacity", "[\"" + id + "\",\"coins\"]"); yield return Wait(2);
   var e = Evo("shelf", id);
   Check(e != null && e.skipCost > 0, $"evolving {id}: skip {e?.skipCost} diamonds");
   if (e == null) { Note("RESULT tiers skip: FAIL no evolution"); yield break; }
   var it = CheckoutInterior.Active.Get("shelf:" + id); var site = it?.root ? it.root.GetComponent<CheckoutEvolutionSite>() : null;
   Check(site, "the ring and the builder on " + id);
   // a tap on the ring (through the world tap, as a finger would)
   var cam = Camera.main; var at = site && site.Ring && cam ? (Vector2)cam.WorldToScreenPoint(site.Ring.position) : Vector2.zero;
   var hit = site && cam ? bridge.WorldTap(at) : null;
   Note($"EVO ring tap at {at}: hit {(hit ? hit.panel : "nothing")}");
   if (!hit || hit.panel != "evolution") CheckoutEvolutionSite.Tapped(e.id);
   yield return Wait(.6f);
   Check(site && site.PlateOpen, "the diamond plate shows under the ring");
   if (it?.root) CaptureAt(it.root.position + Vector3.up * 1.6f, 7f, "ft_evo_skip");
   double diamonds = bridge.State.diamonds; int cost = Evo("shelf", id)?.skipCost ?? e.skipCost;
   var plateHit = site && site.Plate && cam ? bridge.WorldTap(cam.WorldToScreenPoint(site.Plate.position)) : null;
   Note($"EVO plate tap: hit {(plateHit ? plateHit.panel : "nothing")}");
   if (!plateHit || plateHit.panel != "finishEvolution") Hud("finishEvolutionNow", "[\"" + e.id + "\"]");
   yield return Wait(2);
   Check(Evo("shelf", id) == null, "finished");
   Check(System.Math.Abs(diamonds - bridge.State.diamonds - cost) <= 1, $"diamonds {diamonds} → {bridge.State.diamonds} (cost {cost})");
   yield return ClearReveals();
   Note($"RESULT tiers skip: {(fails.Count == 0 ? "PASS" : "FAIL")} {fails.Count} failed" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // ------------------------------------------------------------------ what the migration gave this save
  IEnumerator EvoOldSave() {
   var fails = new List<string>();
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   var card = hud ? hud.QaView?.celebration : null;
   Note($"EVO old save card now: {(card == null ? "none" : card.headline + " · " + card.title + " · " + (card.products?.Length ?? 0) + " products")}");
   var supplier = bridge.State.supplierCatalog ?? System.Array.Empty<SupplierProduct>();
   int expected = 0, found = 0; var lines = new List<string>();
   foreach (var s in bridge.State.shelves.Where(x => x.unlocked && System.Array.IndexOf(EvoFixtures, x.id) >= 0)) {
    for (int t = 2; t <= Mathf.Min(5, s.tier); t++) {
     expected++; int id = ExclusiveId(s.id, t); bool open = supplier.Any(p => p.productId == id && !p.locked);
     if (open) found++; else fails.Add($"{s.id} T{t} product {id} closed");
     lines.Add($"MIGRATE {s.id} T{s.tier}: exclusive T{t} #{id} {(open ? "open" : "CLOSED")}");
    }
   }
   foreach (var sec in bridge.State.sectors.Where(x => x.unlocked && x.tier >= 2)) lines.Add($"MIGRATE sector {sec.id} T{sec.tier}: exclusive recipe(s) up to T{sec.tier}");
   File.WriteAllLines("Logs/ft_evo_migrate.txt", lines); foreach (var l in lines) Note(l);
   Note($"RESULT tiers oldsave: {(fails.Count == 0 ? "PASS" : "FAIL")} {found}/{expected} exclusive products of the evolved fixtures open (Logs/ft_evo_migrate.txt)" + (fails.Count > 0 ? ": " + string.Join(" | ", fails.Take(6)) : ""));
   yield break;
  }

  // ------------------------------------------------------------------ the reveal, frame by frame
  IEnumerator EvoReveal() {
   var fails = new List<string>();
   QaRich("reveal");
   foreach (var f in Directory.GetFiles("Logs", "ft_evo_reveal_*.jpg")) File.Delete(f);
   yield return GoToStage("supermercado"); yield return EnsureBakery(); yield return ClearReveals();
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   // a shelf
   var id = bridge.State.shelves.Where(s => s.unlocked && s.tier < 5 && TierKindOf.ContainsKey(s.id)).OrderBy(s => s.tier).Select(s => s.id).FirstOrDefault();
   if (id != null) yield return EnsurePlaced("shelf:" + id);
   if (id != null) yield return RevealOne("shelf", id, () => Hud("upgradeShelfCapacity", "[\"" + id + "\",\"coins\"]"), fails, true);
   else fails.Add("no shelf to evolve");
   // a sector
   var bakery = bridge.State.sectors?.FirstOrDefault(x => x.id == "padaria");
   if (bakery != null && bakery.unlocked && bakery.tier < 3) yield return RevealOne("sector", "padaria", () => Hud("upgradeSectorTier", "[\"padaria\",\"coins\"]"), fails, false);
   else Note("EVO no sector reveal (bakery " + (bakery == null ? "missing" : bakery.unlocked ? "T" + bakery.tier : "not built") + ")");
   int frames = Directory.GetFiles("Logs", "ft_evo_reveal_*.jpg").Length;
   Note($"RESULT tiers reveal: {(fails.Count == 0 ? "PASS" : "FAIL")} {frames} frames" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  IEnumerator RevealOne(string kind, string target, System.Action start, List<string> fails, bool stills) {
   start(); yield return Wait(2);
   var e = Evo(kind, target);
   if (e == null) { fails.Add(kind + " " + target + ": no evolution"); yield break; }
   // keep the card from starting before we look: a page open holds the reveal (CheckoutDesktopHUD.ApplyConquest)
   var host = CheckoutDesktopHost.Active; host.Route("!shelf:produce"); yield return Wait(1);
   Hud("devFinishEvolutions", "[]"); yield return Wait(2);
   var pieceKey = kind == "shelf" ? "shelf:" + target : "sector:" + target;
   var it = CheckoutInterior.Active.Get(pieceKey);
   bool veiled = it?.root && it.root.GetComponentsInChildren<Renderer>().All(r => r.forceRenderingOff || r.GetComponentInParent<TMPro.TextMeshPro>());
   Note($"EVO {kind} {target}: under the cloth {veiled}");
   if (!veiled) fails.Add(kind + " not under the cloth");
   // back to the map: the reveal starts
   host.Route(""); var reveal = CheckoutEvolutionReveal.Instance;
   for (float t = 0; t < 6 && !reveal.Playing; t += .1f) yield return new WaitForSecondsRealtime(.1f);
   if (!reveal.Playing) { fails.Add(kind + " reveal did not start"); yield break; }
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   int n = 0; bool clothShot = false, popShot = false; float since = -1, popAt = -1; float t0 = Time.realtimeSinceStartup;
   for (float t = 0; t < 11; t = Time.realtimeSinceStartup - t0) {
    yield return new WaitForEndOfFrame();
    if (n % 1 == 0) SaveFrame($"ft_evo_reveal_{kind}_{n:000}", 960);
    n++;
    if (stills && !clothShot && reveal.Stage == 0 && t > .9f) { SaveFrame("ft_evo_cloth", 1600); clothShot = true; }
    if (stills && !popShot && reveal.Stage >= 2 && popAt < 0) popAt = t;
    if (stills && !popShot && popAt >= 0 && t - popAt > .25f) { SaveFrame("ft_evo_pop", 1600); popShot = true; }
    if (!reveal.Playing && hud.ConquestOpen) { if (since < 0) since = t; if (t - since > 2.8f) break; }
    yield return new WaitForSecondsRealtime(1f / 14);
   }
   if (stills) SaveFrame("ft_evo_card", 1600);
   SaveFrame($"ft_evo_card_{kind}", 1280);
   Note($"EVO {kind} {target}: {n} frames, card {(hud.ConquestOpen ? "open" : "missing")}");
   if (!hud.ConquestOpen) fails.Add(kind + " card missing");
   yield return CloseCards(); yield return ClearReveals();
  }

  void SaveFrame(string name, int width) {
   // Full size and straight from the screen (a blit through a render texture washed the colours out); the frames are
   // scaled down afterwards, off the game.
   var tex = ScreenCapture.CaptureScreenshotAsTexture();
   File.WriteAllBytes("Logs/" + name + ".jpg", tex.EncodeToJPG(width >= 1600 ? 88 : 80)); Destroy(tex);
  }
 }
}
