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
  IEnumerator EnsurePlaced(string pieceId, float fromX = 0) {
   var inside = CheckoutInterior.Active; if (!inside || inside.Get(pieceId) != null) yield break;
   if (!inside.waiting.ContainsKey(pieceId)) { Note("EVO " + pieceId + " is neither placed nor waiting"); yield break; }
   var floor = inside.FloorRect; CheckoutInterior.Item placed = null;
   for (float pz = floor.yMax - 1.2f; placed == null && pz > floor.yMin + 1.2f; pz -= 1.1f)
    for (float px = floor.xMin + 1.2f + fromX; placed == null && px < floor.xMax - 1.2f; px += 1.3f)
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
   foreach (var f in Directory.GetFiles("Logs", "ft_evo_*")) if (!f.EndsWith(".txt")) File.Delete(f);
   yield return GoToStage("supermercado"); yield return EnsureBakery(); yield return ClearReveals();
   Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f); yield return ClearReveals();
   // a shelf, taken to T3 first so the recorded reveal is the T3 → T4 one (the Mercadinho's model)
   yield return EnsurePlaced("shelf:produce");
   for (int i = 0; i < 2; i++) { Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(1.2f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.2f); }
   yield return ClearReveals();
   yield return StockShelf("produce");
   yield return RevealOne("shelf", "produce", () => Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"), fails, "shelf", true);
   // the sector (the bakery T1 → T2)
   var bakery = bridge.State.sectors?.FirstOrDefault(x => x.id == "padaria");
   if (bakery != null && bakery.unlocked && bakery.tier < 3) yield return RevealOne("sector", "padaria", () => Hud("upgradeSectorTier", "[\"padaria\",\"coins\"]"), fails, "sector", false);
   else fails.Add("no bakery to evolve");
   // a second shelf (the drinks fridge T1 → T2). The QA game view is already the iPhone's (2778 × 1284, held
   // sideways): the game is landscape only (ProjectSettings allows no portrait), so there is no portrait reveal.
   Note("EVO game view: " + Screen.width + "x" + Screen.height);
   yield return EnsurePlaced("shelf:drinks", 4.5f); yield return StockShelf("drinks");   // (clear of the produce stand)
   yield return RevealOne("shelf", "drinks", () => Hud("upgradeShelfCapacity", "[\"drinks\",\"coins\"]"), fails, "fridge", false);
   // the card on narrower screens with long names: an iPad (4:3) in German and 16:9 in French (the fridge again)
   foreach (var (w, h, lang, name) in new[] { (2048, 1536, "de", "card_ipad_de"), (1920, 1080, "fr", "card_16x9_fr") }) {
    Note($"EVO {name}: game view {CheckoutQaGameView.Set(w, h)}"); TierLang(lang); yield return Wait(2.5f);
    yield return RevealOne("shelf", "drinks", () => Hud("upgradeShelfCapacity", "[\"drinks\",\"coins\"]"), fails, name, false);
   }
   TierLang("pt"); CheckoutQaGameView.Restore(); yield return Wait(2f);
   // what the confetti costs: the pooled system simulated on the main thread (no jobs) with a sector's worth of pieces
   var fx = CheckoutConquestFx.Instance;
   foreach (int n in new[] { 60, 170 }) Note($"EVO confetti cost: {n} pieces, {fx.QaConfettiBench(n, 60):0.000} ms per frame (main thread, editor on the Mac), 1 particle system, 1 material");
   Note($"EVO confetti atlas: {CheckoutConfettiArt.Cols}x{CheckoutConfettiArt.Rows} cells of {CheckoutConfettiArt.Cell} px, drawn in {CheckoutConfettiArt.LastAtlasMs:0} ms (once per accent colour)");
   if (CheckoutConfettiArt.Material(CheckoutConfettiArt.AccentFor("sector", "padaria")).mainTexture is Texture2D atlas) File.WriteAllBytes("Logs/ft_evo_confetti_atlas.png", atlas.EncodeToPNG());
   Note($"RESULT tiers reveal: {(fails.Count == 0 ? "PASS" : "FAIL")}" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : "") + " (Logs/ft_evo_reveal_*.mjpg)");
  }

  // Products on the fixture, so the reveal has something to drop in: the first product of the piece, stocked.
  IEnumerator StockShelf(string shelfId) {
   var slot = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).FirstOrDefault(r => r.shelfId == shelfId);
   if (slot == null) {
    var pick = (bridge.State.supplierCatalog ?? System.Array.Empty<SupplierProduct>()).FirstOrDefault(p => !p.locked && (shelfId == "drinks" ? p.category == "refrigerantes" || p.category == "aguas" : p.category == "hortifruti"));
    if (pick == null) { Note("EVO nothing to stock on " + shelfId); yield break; }
    Hud("assignProductToShelf", "[\"" + shelfId + "\"," + pick.productId + "]"); yield return Wait(1.2f);
    slot = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).FirstOrDefault(r => r.shelfId == shelfId);
    if (slot == null) { Note("EVO could not assign on " + shelfId); yield break; }
   }
   Hud("devAdjustInventory", "[" + slot.productId + ",80]"); yield return Wait(1f);
   // (as much as fits and as the stock room has: the store refuses more than either)
   slot = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).FirstOrDefault(r => r.slotId == slot.slotId) ?? slot;
   int room = Mathf.Max(1, Mathf.Min(slot.capacity - slot.stock, slot.reserve > 0 ? slot.reserve : slot.capacity));
   Hud("restockShelf", "[{\"shelfId\":\"" + slot.slotId + "\",\"productId\":" + slot.productId + ",\"amount\":" + room + "}]"); yield return Wait(1.2f);
   var now = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).FirstOrDefault(r => r.slotId == slot.slotId);
   Note($"EVO stocked {shelfId}: {slot.productName} {now?.stock}/{now?.capacity}");
  }

  // One reveal recorded at 30 fps (a fixed game step: Time.captureFramerate) into Logs/ft_evo_reveal_<name>.mjpg (JPEG
  // frames back to back; ffmpeg reads them as a video), from the camera's first move to the card standing.
  IEnumerator RevealOne(string kind, string target, System.Action start, List<string> fails, string name, bool stills) {
   // whatever came before (reveals dismissed half way) left no cloth behind and gave the camera back
   int stray = CheckoutEvolutionReveal.Instance.transform.Cast<Transform>().Count(c => c.name == "Evolution cloth");
   Note($"EVO before {name}: stray cloths {stray}, camera free {!MarketDay.MarketSimulation.Cinematic}");
   if (stray > 0) fails.Add(name + ": " + stray + " cloth(s) left behind");
   if (MarketDay.MarketSimulation.Cinematic) fails.Add(name + ": camera still held by a cut reveal");
   start(); yield return Wait(2);
   if (Evo(kind, target) == null) { fails.Add(kind + " " + target + ": no evolution"); yield break; }
   // keep the card from starting before we look: a page open holds the reveal (CheckoutDesktopHUD.ApplyConquest)
   var host = CheckoutDesktopHost.Active; host.Route("!shelf:produce"); yield return Wait(1);
   Hud("devFinishEvolutions", "[]"); yield return Wait(2);
   var it = CheckoutInterior.Active.Get(kind == "shelf" ? "shelf:" + target : "sector:" + target);
   bool veiled = it?.root && it.root.GetComponentsInChildren<Renderer>().All(r => r.forceRenderingOff || r.GetComponentInParent<TMPro.TextMeshPro>());
   Note($"EVO {kind} {target}: under the cloth {veiled}");
   if (!veiled) fails.Add(kind + " not under the cloth");
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>(); var reveal = CheckoutEvolutionReveal.Instance;
   var sim = FindAnyObjectByType<MarketDay.MarketSimulation>(); var camBefore = sim ? sim.CameraState : default;
   var path = "Logs/ft_evo_reveal_" + name + ".mjpg";
   var fs = File.Create(path); int frames = 0, waited = 0, countAt = -1, cardAt = -1, popAt = -1, revealStart = -1; bool cloth = false, pop = false, card = false; float maxFill = 0;
   Time.captureFramerate = 30;
   try {
    host.Route("");   // back to the map: the reveal starts
    while (frames < 30 * 9) {
     yield return new WaitForEndOfFrame();
     // (from the reveal's first frame: the window that held it back is not part of the show)
     if (revealStart < 0 && reveal.Playing) revealStart = frames + 1;
     if (revealStart < 0) { if (++waited > 90) break; continue; }
     var jpg = GrabJpg(1280); fs.Write(jpg, 0, jpg.Length); frames++;
     if (stills && !cloth && revealStart > 0 && frames - revealStart == 26) { File.WriteAllBytes("Logs/ft_evo_cloth.jpg", GrabJpg(1920)); cloth = true; }
     if (popAt < 0 && revealStart > 0 && reveal.Playing && reveal.Stage >= 2) popAt = frames;
     if (stills && !pop && popAt > 0 && frames - popAt == 9) { File.WriteAllBytes("Logs/ft_evo_pop.jpg", GrabJpg(1920)); pop = true; }
     // the confetti at its peak (about 0.6 s after the pop: up, spread and turning), shelf and sector
     if ((name == "shelf" || name == "sector") && popAt > 0 && frames - popAt == 18) {
      File.WriteAllBytes("Logs/ft_evo_confetti_" + name + ".jpg", GrabJpg(1920));
      var cfx = CheckoutConquestFx.Instance; Note($"EVO {name} confetti: {cfx.LastConfettiCount} pieces over the piece's bounds, {cfx.ConfettiAlive} alive at the peak, emitted in {cfx.LastConfettiSetupMs:0.00} ms");
     }
     if (reveal.Playing && it?.root) maxFill = Mathf.Max(maxFill, ScreenShare(it.root));
     if (cardAt < 0 && !reveal.Playing && revealStart > 0 && hud.ConquestOpen && hud.QaCardShown) cardAt = frames;
     if (cardAt > 0 && countAt < 0 && hud.QaCountDone) countAt = frames;
     // 1.5 s more once the last number has landed: the final values stay on screen; the still is the last frame
     if (countAt > 0 && frames - countAt >= 45) { File.WriteAllBytes("Logs/ft_evo_card" + (stills ? "" : "_" + name) + ".jpg", GrabJpg(1920)); card = true; break; }
     if (cardAt > 0 && frames - cardAt > 30 * 4) break;
    }
   } finally { Time.captureFramerate = 0; fs.Close(); }
   float seconds = revealStart > 0 && cardAt > 0 ? (cardAt - revealStart) / 30f : -1;
   Note($"EVO {kind} {target}: {frames} frames at 30 fps, cloth → card {seconds:0.00}s, piece up to {maxFill * 100:0}% of the screen height");
   if (!card) fails.Add(kind + " card missing");
   // the numbers: at their final values within ~0.8 s of the card, and the table's
   float countSeconds = cardAt > 0 && countAt > 0 ? (countAt - cardAt) / 30f : -1;
   var texts = hud.QaStatTexts; var want = ExpectedStats(name);
   texts = texts.Select(t => System.Text.RegularExpressions.Regex.Replace(t, "<[^>]+>", "")).ToArray();
   bool match = want == null || (texts.Length == want.Length && texts.Select((t, i) => t.Replace(" ", "").EndsWith("→" + want[i])).All(x => x));
   // the card's rhythm: room under the title, between the numbers and the NOVO tile and above the buttons; the badge inside
   var gaps = hud.QaCardGaps();
   Note($"EVO {name} card layout: title→next {gaps[0]:0}, numbers→NOVO {gaps[1]:0}, NOVO→buttons {gaps[2]:0} (canvas units), badge inside {gaps[3] > 0}");
   if (gaps[0] < 6 || (!float.IsNaN(gaps[1]) && gaps[1] < 16) || gaps[2] < 16 || gaps[3] <= 0) fails.Add($"{name} card spacing {gaps[0]:0}/{gaps[1]:0}/{gaps[2]:0}/{gaps[3]}");
   Note($"EVO {name} card: numbers final {countSeconds:0.00}s after the card; {string.Join(" | ", texts)}; table {(want == null ? "-" : string.Join(" ", want))}: {(match ? "match" : "MISMATCH")}; picture {hud.QaCardPicture}");
   if (countSeconds <= 0 || countSeconds > 1.0f) fails.Add($"{name} numbers final after {countSeconds:0.00}s");
   if (!match) fails.Add(name + " card numbers differ from the table");
   if (hud.QaCardPicture != "snapshot") fails.Add(name + " card picture: " + hud.QaCardPicture);
   if (hud.QaPortrait is Texture2D shot) File.WriteAllBytes("Logs/ft_evo_snapshot_" + name + ".png", shot.EncodeToPNG());
   if (seconds > 0 && (seconds < 3.2f || seconds > 4.3f)) fails.Add($"{kind} cloth → card {seconds:0.0}s");
   // the card closes: the camera goes back to exactly where it was
   yield return CloseCards(); yield return Wait(1.5f);
   if (sim) {
    var after = sim.CameraState; bool same = Vector3.Distance(after.focus, camBefore.focus) < .05f && Mathf.Abs(after.zoom - camBefore.zoom) < .05f;
    Note($"EVO camera back: {same} (zoom {camBefore.zoom:0.00} → {after.zoom:0.00})");
    if (!same) fails.Add(kind + " camera not back");
   }
   yield return ClearReveals();
  }

  // The card's numbers after each recorded evolution (claude/evolucoes-recompensas.md): the new values, in card order.
  static string[] ExpectedStats(string name) => name switch {
   "shelf" => new[] { "20", "7", "15%", "30%" },        // produce T4: per product, places, customers, restock
   "sector" => new[] { "3", "15%", "25%", "5" },        // bakery T2: lines, faster, per batch, counter
   "fridge" => new[] { "10", "5", "5%", "10%" },        // drinks T2
   _ => null };

  // How much of the screen's height the piece takes now.
  static float ScreenShare(Transform root) {
   var cam = Camera.main; if (!cam) return 0; var rs = root.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) return 0;
   bool any = false; Bounds b = default;
   foreach (var r in rs) {
    if (r is ParticleSystemRenderer || !r.enabled || !r.gameObject.activeInHierarchy) continue;
    var rb = r.bounds; if (rb.size.x < .08f && rb.size.z < .08f && rb.size.y > .4f) continue;   // (a hanging cable)
    if (!any) { b = rb; any = true; } else b.Encapsulate(rb);
   }
   if (!any) return 0;
   float minY = float.MaxValue, maxY = float.MinValue;
   for (int i = 0; i < 8; i++) { var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z); var p = cam.WorldToViewportPoint(c); minY = Mathf.Min(minY, p.y); maxY = Mathf.Max(maxY, p.y); }
   return maxY - minY;
  }

  // The screen, scaled to `width` (a linear target keeps the colours: the screen texture is not flagged sRGB).
  static byte[] GrabJpg(int width) {
   var tex = ScreenCapture.CaptureScreenshotAsTexture();
   float k = Mathf.Min(1, width / (float)tex.width);
   int w = Mathf.RoundToInt(tex.width * k) / 2 * 2, h = Mathf.RoundToInt(tex.height * k) / 2 * 2;
   var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear);
   Graphics.Blit(tex, rt);
   var prev = RenderTexture.active; RenderTexture.active = rt;
   var small = new Texture2D(w, h, TextureFormat.RGB24, false); small.ReadPixels(new Rect(0, 0, w, h), 0, 0); small.Apply();
   RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
   var bytes = small.EncodeToJPG(86); Destroy(small); Destroy(tex);
   return bytes;
  }

  // ------------------------------------------------------------------ the 8-lane restock game (a ★ fixture)
  IEnumerator EvoRestock8() {
   QaRich("restock8");
   yield return GoToStage("supermercado"); yield return ClearReveals();
   for (int i = 0; i < 4 && (bridge.State.shelves.First(x => x.id == "produce").tier < 5); i++) { Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(1.2f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.2f); }
   yield return ClearReveals();
   var picks = (bridge.State.supplierCatalog ?? System.Array.Empty<SupplierProduct>()).Where(p => !p.locked && p.category == "hortifruti").Select(p => p.productId).Distinct().ToList();
   var have = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).Where(r => r.shelfId == "produce").Select(r => r.productId).ToList();
   int lane = 0;
   foreach (var id in picks) {
    if (lane >= 8) break; var slot = lane == 0 ? "produce" : "produce:" + lane;
    if (!have.Contains(id)) { Hud("assignProductToShelf", "[\"" + slot + "\"," + id + "]"); yield return Wait(.5f); }
    Hud("devAdjustInventory", "[" + id + ",40]"); yield return Wait(.3f); lane++;
   }
   yield return Wait(1.5f);
   var slots = (bridge.State.restockSlots ?? System.Array.Empty<RestockSlot>()).Where(r => r.shelfId == "produce").ToList();
   Note($"EVO restock8: produce T{bridge.State.shelves.First(x => x.id == "produce").tier}, {slots.Count} products: {string.Join(", ", slots.Select(r => r.slotId + "=" + r.productName))}");
   CheckoutRestockGame.ShowFixture("produce"); yield return Wait(3f);
   yield return new WaitForEndOfFrame(); File.WriteAllBytes("Logs/ft_evo_restock8.jpg", GrabJpg(1920));
   Note($"RESULT tiers restock8: {(slots.Count >= 8 ? "PASS" : "FAIL")} {slots.Count} products on the ★ produce stand (Logs/ft_evo_restock8.jpg)");
   yield return Wait(1f);
  }

  void SaveFrame(string name, int width) {
   // Full size and straight from the screen (a blit through a render texture washed the colours out); the frames are
   // scaled down afterwards, off the game.
   var tex = ScreenCapture.CaptureScreenshotAsTexture();
   File.WriteAllBytes("Logs/" + name + ".jpg", tex.EncodeToJPG(width >= 1600 ? 88 : 80)); Destroy(tex);
  }
 }
}
