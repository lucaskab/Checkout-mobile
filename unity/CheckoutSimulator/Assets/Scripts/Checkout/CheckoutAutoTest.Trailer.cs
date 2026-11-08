using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Launch trailer footage (Lucas 07/11: "um trailer do jogo... começa na mesinha... chega na rede com o mapa todo
 // evoluído, o supermercado cheio de clientes"), on the QA copy of the save (the player's own save is never touched):
 // "eventstrailer-<pt|en>[-scene.scene...]". The Game view goes to 1920x1080 and the game to that language; every shot
 // is recorded to Logs/tr_<lang>_<scene>_<k>.mjpg (30 fps JPEG frames back to back, ffmpeg reads them) with the HUD
 // hidden for the cinematic shots and shown for the mini-games. The trailer itself is cut outside Unity.
 // Scenes, in story order: mesa (the little table), caixa (the register), cresce (tenda → mercadinho, one shot each),
 // repor (the restock game), hiper (the hypermarket full of customers, its checkouts and sectors), padaria (the
 // sector puzzles), evento (live events), rede (the chain: facade, distribution centre, the whole map from above).
 public sealed partial class CheckoutAutoTest {
  int recW = 1280, recQ = 74;
  bool trFull;
  readonly List<Canvas> trHidden = new List<Canvas>();
  int trSeq; string trLang = "pt"; string trScene = ""; int trShotK;
  /// <summary>The chain's name when eventscrowd names it (".brand").</summary>
  string crowdChainName = "Bom Preço";

  void TrHud(string action, string args) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-tr-" + (++trSeq) + "\",\"action\":\"" + action + "\",\"args\":" + args + "}");
  MarketDay.MarketSimulation TrSim => FindAnyObjectByType<MarketDay.MarketSimulation>();

  /// <summary>Hides (or shows back) every screen-space canvas: the HUD, windows, balloons. World labels stay.</summary>
  void TrHideHud(bool hide) {
   if (hide) {
    foreach (var c in FindObjectsByType<Canvas>(FindObjectsSortMode.None))
     if (c && c.enabled && c.isRootCanvas && c.renderMode == RenderMode.ScreenSpaceOverlay) { c.enabled = false; trHidden.Add(c); }
   } else { foreach (var c in trHidden) if (c) c.enabled = true; trHidden.Clear(); }
  }

  readonly List<Renderer> trWorldHidden = new List<Renderer>();
  /// <summary>Padlocks over the lots, markers, price plates and rings in the world: hidden in the cinematic shots
  /// (as the friend's postcard does, CheckoutSocial.PostcardHide). Request bubbles stay: they show a living shop.</summary>
  void TrHideWorld(bool hide) {
   if (!hide) { foreach (var r in trWorldHidden) if (r) r.enabled = true; trWorldHidden.Clear(); return; }
   string[] words = { "Padlock", "Marker", "Speed up", "Plate", "Ring" };
   foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)) {
    if (!r.enabled) continue; var t = r.transform; bool hit = false;
    for (int depth = 0; depth < 3 && t && !hit; depth++, t = t.parent) foreach (var w in words) if (t.name.Contains(w)) { hit = true; break; }
    if (hit) { r.enabled = false; trWorldHidden.Add(r); }
   }
  }

  /// <summary>Shoppers sent to the shop one after another (as eventscrowd does), each buying two or three things
  /// from the shop's shelves, until `count` were sent or the coroutine is stopped.</summary>
  CheckoutWalker trLastWalker;
  IEnumerator TrSpawn(int count, float gap) {
   var rnd = new System.Random(7);
   var all = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).ToList();
   for (int sent = 0; sent < count;) {
    var shelfIds = (bridge.State.shelves ?? new Shelf[0]).Where(x => x != null && x.unlocked && !x.building).Select(x => x.id).ToList();
    var idle = all.FirstOrDefault(w => w && !w.gameObject.activeSelf && !w.Reserved);
    if (idle && shelfIds.Count > 0 && !CheckoutWalker.ShopCrowded) {
     var buy = new List<Purchase>(); int k = 2 + rnd.Next(2);
     for (int j = 0; j < k; j++) buy.Add(new Purchase { shelfId = shelfIds[rnd.Next(shelfIds.Count)], productId = 1, quantity = 1 + rnd.Next(2) });
     idle.Begin(new Customer { id = "qa-trailer-" + sent, name = "QA", spent = 12, purchases = buy.ToArray() }); trLastWalker = idle;
     sent++; yield return new WaitForSecondsRealtime(gap);
    } else yield return new WaitForSecondsRealtime(.5f);
   }
  }

  /// <summary>A cinematic shot (no HUD): the camera glides from (a, za) to (b, zb).</summary>
  IEnumerator TrGlideShot(Vector3 a, float za, Vector3 b, float zb, float seconds) => TrShot(false, TrGlide(a, za, b, zb, seconds), a, za);

  /// <summary>The camera from (a, za) to (b, zb) in `seconds` of video, eased; one step per recorded frame.</summary>
  IEnumerator TrGlide(Vector3 a, float za, Vector3 b, float zb, float seconds) {
   var sim = TrSim; int n = Mathf.Max(1, Mathf.RoundToInt(seconds * 30));
   for (int i = 0; i <= n; i++) {
    float t = i / (float)n; t = t * t * (3 - 2 * t);
    if (sim) sim.FocusCinematic(Vector3.Lerp(a, b, t), Mathf.Lerp(za, zb, t));
    if (i % 15 == 7) TrHideWorld(true);   // (padlocks and markers that came up mid-shot)
    if (i < n) yield return null;
   }
  }

  /// <summary>One recorded shot: Logs/tr_<lang>_<scene>_<k>.mjpg while `body` runs.</summary>
  IEnumerator TrShot(bool hud, IEnumerator body, Vector3? startAt = null, float startZoom = 0) {
   yield return CloseCardsSettled();
   var sim = TrSim; var was = MarketDay.MarketSimulation.Cinematic; MarketDay.MarketSimulation.Cinematic = true;
   if (startAt.HasValue && sim) { sim.FocusCinematic(startAt.Value, startZoom); yield return new WaitForSecondsRealtime(.5f); }
   TrHideHud(!hud); if (!hud) TrHideWorld(true);
   var path = $"Logs/tr_{trLang}_{trScene}_{++trShotK}.mjpg";
   RecStart(path);
   try { yield return body; }
   finally { RecStop(); TrHideHud(false); TrHideWorld(false); MarketDay.MarketSimulation.Cinematic = was; Note($"TRAILER shot {path}"); }
  }

  /// <summary>Waits for a log line containing `text` written after the call (at most `timeout` seconds).</summary>
  IEnumerator TrWaitLog(string text, float timeout) {
   int from = log.Count;
   for (float t = 0; t < timeout; t += .5f) {
    for (int i = from; i < log.Count; i++) if (log[i].Contains(text)) yield break;
    yield return new WaitForSecondsRealtime(.5f);
   }
   Note("trailer: no '" + text + "' in " + timeout + " s");
  }

  IEnumerator TrOpen() {
   if (bridge.State.isOpen) yield break;
   TrHud("claimDayResult", "[]"); yield return new WaitForSecondsRealtime(1);
   TrHud("startDay", "[\"livre\"]"); for (float t = 0; t < 4 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f);
   if (!bridge.State.isOpen) { TrHud("setMarketOpen", "[true]"); for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f); }
  }

  /// <summary>Where the shop is: the market building's floor, or the stall / small shop.</summary>
  (Vector3 center, float size) TrShop() {
   var inside = CheckoutInterior.Active;
   if (inside && !CheckoutStall.Small) { var f = inside.FloorRect; return (new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height)); }
   var fp = CheckoutStall.Footprint; return (new Vector3(fp.center.x, 0, fp.center.z), Mathf.Max(fp.size.x, fp.size.z));
  }

  Coroutine trCrowd;
  /// <summary>A stage furnished and full of shoppers (eventscrowd: every piece of the expansion placed, shelves stocked,
  /// the register served at once); returns once its shoppers are on their way. The crowd keeps running until the next.</summary>
  IEnumerator TrCrowd(string stage, int shoppers, string extra = "") {
   if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
   tierLayout = null; tierOwned = null; tierDecor = null;   // (the last stage's layout must not land in this one)
   int from = log.Count;
   trCrowd = StartCoroutine(Crowd($"eventscrowd-{stage}.240.{shoppers}.stock{extra}"));
   yield return TrWaitLog("CROWD day ", 150);
   Note($"trailer: {stage} ready (era {bridge.State?.era?.id}, open {bridge.State?.isOpen})");
  }

  sealed class TrP { public string id, type; public CheckoutInteriorPiece p; public bool decor; }

  /// <summary>The shop floor laid out the way supermarkets are (Lucas 08/11: "procurar na internet como geralmente os
  /// mercados posicionam as coisas... ficar mais organizado", and less of it than the first try): the fresh sectors
  /// along the back wall (the perimeter), a wide main aisle, the cold row (drinks, dairy, freezers), then the dry
  /// gondolas in straight parallel rows with cross aisles and a promotional endcap at each end of a run, the produce
  /// right by the way in, and an open decompression strip inside the door. In the big shops (from 150 m²) extra
  /// gondolas and coolers stand in where a real store has them: decorations whose model is a fixture's
  /// (DecorTier: the picture only, nothing is bought). Checkouts, kiosks and their queues stay where they are. The
  /// layout goes in through the snapshot patch (tierLayout, as eventstiers does), so every later snapshot keeps it.</summary>
  IEnumerator TrFill(string stage) {
   var inside = CheckoutInterior.Active; var map = FindAnyObjectByType<CheckoutMap>(); if (!inside || !map) yield break;
   inside.editing = false;
   var layout = inside.LayoutState; var floor = inside.FloorRect;
   bool IsMain(string type) => type == "shelf" || type == "sector";
   bool big = floor.width * floor.height > 150f, deep = floor.height >= 11f;
   float mainAisle = deep ? 2f : 1.5f, aisle = deep ? 1.8f : 1.4f;
   var live = inside.items.Values.Where(i => i.root && i.placed && !i.ghost && !i.design).ToList();
   // what stays: checkouts, kiosks, stations, the decorations outside
   var items = new List<InteriorItem>();
   foreach (var i in live.Where(l => !IsMain(l.type) && (l.functional || l.outside)))
    items.Add(new InteriorItem { id = i.id, type = i.type, x = i.x, z = i.z, rot = i.rot, outside = i.outside });
   foreach (var w in inside.waiting.Where(w => !IsMain(w.Value.type))) items.Add(new InteriorItem { id = w.Key, type = w.Value.type, stored = true });
   // where nothing goes: what stays inside (with room around it), the checkouts and their queues, a walkway in from the door
   // (what stands on the floor: lamps and bunting hanging from the ceiling are not in the way)
   float reach = CheckoutInterior.FloorHere + 1.6f;
   Rect BoxOf(CheckoutInterior.Item i, float pad) {
    var rs = i.root.GetComponentsInChildren<Renderer>().Where(r => r.enabled && r.bounds.min.y < reach).ToArray(); if (rs.Length == 0) return Rect.zero;
    var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
    return Rect.MinMaxRect(bb.min.x - pad, bb.min.z - pad, bb.max.x + pad, bb.max.z + pad);
   }
   var blockers = new List<Rect>();
   float queueTop = floor.yMin;
   foreach (var i in inside.items.Values.Where(l => l.root && l.root.gameObject.activeInHierarchy && (!IsMain(l.type) && !l.outside && l.functional || l.design))) {
    bool counter = i.type == "checkout" || i.type == "kiosk";
    var b = BoxOf(i, counter ? 1f : .4f); if (b.width <= 0) continue;
    blockers.Add(b); if (b.width * b.height > 6f) Note($"trailer fill {stage}: big blocker {i.id} ({i.type}{(i.design ? ", design" : "")}) {b.xMin:0.0},{b.yMin:0.0}..{b.xMax:0.0},{b.yMax:0.0}");
    // the queue: towards the middle of the shop (a line of checkouts along a side wall queues across the floor, a
    // counter at the front queues back into the shop)
    if (counter) {
     float cx = b.center.x - floor.center.x;
     blockers.Add(cx > floor.width * .2f ? Rect.MinMaxRect(b.xMin - 2.6f, b.yMin, b.xMax, b.yMax) : cx < -floor.width * .2f ? Rect.MinMaxRect(b.xMin, b.yMin, b.xMax + 2.6f, b.yMax)
      : Rect.MinMaxRect(b.xMin, b.yMin, b.xMax, b.yMax + 3f));
    }
   }
   var zone = inside.CheckoutZone;
   if (zone.width > .1f) blockers.Add(Rect.MinMaxRect(zone.xMin - .4f, floor.yMin, floor.xMax, floor.yMin + 3f));
   float front = floor.yMin + (big ? (deep ? 3.4f : 2.4f) : CheckoutStall.ShopInside ? 1.6f : 1.9f);
   float right = CheckoutStall.Small && !CheckoutStall.PlacedCounter ? floor.xMax - .2f : floor.xMax - .1f;
   float walk = Mathf.Clamp(map.Entrance.x, floor.xMin + 2.5f, right - 2.5f);
   CheckoutInteriorPiece PieceOf(string template) => inside.TemplateObject(template)?.GetComponent<CheckoutInteriorPiece>();
   float W(CheckoutInteriorPiece p) => p.max.x - p.min.x; float D(CheckoutInteriorPiece p) => p.max.y - p.min.y;
   // the real fixtures, by where a supermarket keeps them
   var sectors = new List<TrP>(); var cold = new List<TrP>(); var dry = new List<TrP>(); var produce = new List<TrP>();
   string KindOf(string id) => id.StartsWith("shelf:") && TierKindOf.TryGetValue(id.Substring(6), out var k) ? k : "shelf";
   void Sort(string id, string type, CheckoutInteriorPiece pc) {
    var x = new TrP { id = id, type = type, p = pc };
    if (type == "sector") { sectors.Add(x); return; }
    var k = KindOf(id);
    (k == "produce" ? produce : k == "drinks" || k == "dairy" || k == "freezer" || k == "icecream" ? cold : dry).Add(x);
   }
   foreach (var i in live.Where(l => IsMain(l.type)).OrderBy(l => l.id)) { var pc = PieceOf(i.desired ?? i.template) ?? i.piece; if (pc) Sort(i.id, i.type, pc); else Note("trailer fill: no model for " + i.id); }
   foreach (var w in inside.waiting.Where(w => IsMain(w.Value.type))) { var pc = PieceOf(w.Value.template); if (pc) Sort(w.Key, w.Value.type, pc); }
   int mainsTotal = sectors.Count + cold.Count + dry.Count + produce.Count;
   // the stand-ins (big shops): decorations shown with a fixture's model
   int tier = Mathf.Clamp(tierShelves > 0 ? tierShelves : 1, 1, 4);
   var standIns = new Dictionary<string, (string type, CheckoutInteriorPiece p)>();
   var decorTiers = new List<DecorTier>();
   foreach (var (kind, type) in new[] { ("shelf", "umbrella-stand"), ("dairy", "neon-cart"), ("drinks", "giant-teddy"), ("freezer", "party-tree"), ("produce", "floor-lamp") }) {
    var t = kind + "_T" + tier; var pc = PieceOf(t); if (!pc) continue;
    standIns[kind] = (type, pc); decorTiers.Add(new DecorTier { type = type, tier = 1, template = t });
   }
   var owned = new Dictionary<string, int>();
   int decorN = 0, placedMain = 0, standInCount = 0, displayCount = 0;
   TrP Decor(string type, CheckoutInteriorPiece pc) => pc ? new TrP { id = null, type = type, p = pc, decor = true } : null;
   TrP Display(string type) => Decor(type, PieceOf(inside.DecorTemplate(type)));
   TrP StandIn(string kind) => big && standIns.TryGetValue(kind, out var s) ? Decor(s.type, s.p) : null;
   int endcapK = 0; string[] endcapTypes = { "promo-stand", "can-pyramid" };
   TrP Endcap() { for (int k = 0; k < endcapTypes.Length; k++) { var e = Display(endcapTypes[(endcapK + k) % endcapTypes.Length]); if (e != null) { endcapK += k + 1; return e; } } return null; }
   void Put(TrP pc, float x, float top) {
    var b = CheckoutMarketLayout.Unproject(new Vector3(x - pc.p.min.x, 0, top - pc.p.max.y), layout);
    string id = pc.id;
    if (pc.decor) { id = "decor-" + (800 + decorN++); owned[pc.type] = (owned.TryGetValue(pc.type, out var c) ? c : 0) + 1; }
    else placedMain++;
    items.Add(new InteriorItem { id = id, type = pc.type, x = b.x, z = b.z, rot = 0 });
    blockers.Add(Rect.MinMaxRect(x - .06f, top - D(pc.p) - .06f, x + W(pc.p) + .06f, top + .06f));
   }
   const float gap = .12f;
   // One row, left to right (the way in is on the left): the real pieces first, then what `extra` gives; runs of at
   // most `runMax` metres with a cross aisle between them and, if `endcaps`, a promotional display at each end.
   List<TrP> Row(float top, float depth, List<TrP> reals, System.Func<TrP> extra, float runMax, bool endcaps) {
    var deferred = new List<TrP>(); float x = floor.xMin + .1f, run = 0; string why = "end of the row";
    for (int guard = 0; guard < 240 && x < right - .3f; guard++) {
     bool isEnd = endcaps && run == 0;
     var pc = isEnd ? Endcap() : reals.Count > 0 ? reals[0] : extra?.Invoke();
     if (pc == null) { if (isEnd) { run = .01f; continue; } why = "nothing more to place"; break; }
     float w = W(pc.p), d = D(pc.p);
     bool fromReals = !isEnd && reals.Count > 0 && reals[0] == pc;
     if (d > depth + .05f) { if (fromReals) { if (!pc.decor) deferred.Add(pc); reals.RemoveAt(0); continue; } if (isEnd) { run = .01f; continue; } why = "too deep " + pc.type; break; }
     if (x + w > right) { why = "no width for " + pc.type; break; }
     var spot = Rect.MinMaxRect(x, top - d, x + w, top);
     var hit = blockers.Where(b => b.Overlaps(spot)).Select(b => b.xMax).DefaultIfEmpty(-999).Max();
     if (hit > -999) {
      // a run ends at the blocker: its endcap first if it fits
      if (endcaps && run > 1f) { var e = Endcap(); if (e != null && x + W(e.p) <= hit && !blockers.Any(b => b.Overlaps(Rect.MinMaxRect(x, top - D(e.p), x + W(e.p), top)))) Put(e, x, top); }
      x = hit + .05f; run = 0; continue;
     }
     if (spot.yMin < front) { why = "past the front for " + pc.type; break; }
     Put(pc, x, top); if (fromReals) reals.RemoveAt(0);
     if (pc.decor && !isEnd) { if (standIns.Values.Any(v => v.type == pc.type)) standInCount++; else displayCount++; }
     x += w + gap; run += w + gap;
     if (run > runMax) {
      if (endcaps) { var e = Endcap(); if (e != null && x + W(e.p) <= right && !blockers.Any(b => b.Overlaps(Rect.MinMaxRect(x, top - D(e.p), x + W(e.p), top)))) { Put(e, x, top); x += W(e.p); } }
      x += big ? 1.8f : 1.4f; run = 0;
     }
    }
    Note($"trailer fill {stage}: row top {top - floor.yMin:0.0} m depth {depth:0.0}: {why} at x {x - floor.xMin:0.0}/{right - floor.xMin:0.0}; {reals.Count} fixtures left");
    deferred.AddRange(reals); reals.Clear();
    return deferred;
   }
   float MaxD(IEnumerable<TrP> l, float fallback) => l.Where(x => x != null).Select(x => D(x.p)).DefaultIfEmpty(fallback).Max();
   int ci = 0; string[] coldCycle = { "drinks", "dairy", "freezer", "dairy" };
   TrP ColdExtra() { for (int k = 0; k < coldCycle.Length; k++) { var e = StandIn(coldCycle[ci++ % coldCycle.Length]); if (e != null) return e; } return null; }
   TrP DryExtra() => StandIn("shelf");
   float rowTop = floor.yMax - .05f;
   // 1. the perimeter: sectors along the back wall, and in a shallow shop (or one without sectors) the coolers too
   var backReals = sectors.Concat(!deep || sectors.Count == 0 ? cold : new List<TrP>()).ToList();
   if (!deep || sectors.Count == 0) cold = new List<TrP>();
   float dA = MaxD(backReals, 1f);
   // the walkway in from the door, up to the main aisle (the back wall stays whole)
   if (floor.width > 6f) blockers.Add(Rect.MinMaxRect(walk - (big ? 1f : .8f), floor.yMin, walk + (big ? 1f : .8f), floor.yMax - dA - .3f));
   var left = Row(rowTop, dA, backReals, big ? ColdExtra : (System.Func<TrP>)null, 99f, false);
   rowTop -= dA + mainAisle;
   // a sector the back wall had no room for (the checkout lines reach far back in the big shops) stands on its own
   // by the way in (a bakery by the door, as stores do), not in the cold row
   var sectorOverflow = left.Where(x => x.type == "sector").ToList(); left = left.Where(x => x.type != "sector").ToList();
   // 2. the cold row (drinks, dairy, freezers) in a deep shop
   if (deep && (cold.Count > 0 || big)) {
    var coldReals = cold.Concat(left).ToList(); left.Clear();
    float dB = MaxD(coldReals.Concat(new[] { StandIn("drinks"), StandIn("dairy") }), 1f);
    if (rowTop - dB >= front) { left = Row(rowTop, dB, coldReals, big ? ColdExtra : (System.Func<TrP>)null, big ? 9f : 99f, big); rowTop -= dB + aisle; }
    else left = coldReals;
   }
   // 3. the dry gondolas in parallel rows; the front-most row starts with the produce by the way in
   var dryReals = dry.Concat(left).ToList();
   float dC = MaxD(dryReals.Concat(produce).Concat(new[] { StandIn("shelf") }), 1f);
   int rows = 0; for (float t = rowTop; t - dC >= front; t -= dC + aisle) rows++;
   for (int r = 0; r < rows; r++) {
    bool last = r == rows - 1;
    var reals = last ? produce.Concat(new[] { Display("fruit-pyramid"), Display("watermelon-pile") }.Where(x => x != null)).Concat(dryReals).ToList() : dryReals;
    if (last) dryReals = new List<TrP>();
    var rest = Row(rowTop, Mathf.Max(dC, MaxD(reals, dC)), reals, DryExtra, big ? 8f : 99f, big);
    dryReals = rest.Where(x => !x.decor).Concat(dryReals).ToList();
    rowTop -= dC + aisle;
   }
   if (rows == 0) dryReals = produce.Concat(dryReals).ToList();
   // a fixture the rows had no room for (a small shop): anywhere it fits, from the back, before the inventory
   front = floor.yMin + .9f;
   dryReals = sectorOverflow.Concat(dryReals).ToList();
   foreach (var x in dryReals.Where(x => !x.decor).ToList()) {
    bool done = false; float w = W(x.p), d = D(x.p);
    for (float top = floor.yMax - .05f; top - d >= front && !done; top -= .25f)
     for (float px = floor.xMin + .1f; px + w <= right && !done; px += .25f) {
      // (with room in front of it for the customers, and the aisle behind it left free)
      var r = Rect.MinMaxRect(px, top - d - 1.2f, px + w, top + (top < floor.yMax - .2f ? 1.3f : 0f));
      if (blockers.Any(b => b.Overlaps(r))) continue;
      Put(x, px, top); dryReals.Remove(x); done = true;
     }
   }
   // what still found no room waits in the inventory (stored) rather than vanish
   foreach (var x in dryReals.Where(x => !x.decor)) items.Add(new InteriorItem { id = x.id, type = x.type, stored = true });
   foreach (var i in items.Where(x => x.outside)) { var lv = live.FirstOrDefault(l => l.id == i.id); if (lv != null && !lv.functional) owned[i.type] = (owned.TryGetValue(i.type, out var c) ? c : 0) + 1; }
   tierPatching = true; tierLayout = items.ToArray(); tierDecor = decorTiers.ToArray();
   tierOwned = owned.Select(o => new DecorOwned { type = o.Key, count = o.Value }).ToArray();
   CheckoutBridge.TestPatch = s => { Patch(s); PatchTiers(s); };
   yield return Reapply();
   inside = CheckoutInterior.Active;
   int shown = inside.items.Values.Count(i => i.root && i.root.gameObject.activeInHierarchy && !i.outside);
   bool ok = inside.Reachable(out var blocked);
   Note($"trailer fill {stage}: {placedMain}/{mainsTotal} fixtures, {standInCount} stand-in fixtures, {displayCount} displays, {decorN - standInCount - displayCount} endcaps, {shown} pieces shown inside, waiting {inside.waiting.Count}, reachable {ok}{(ok ? "" : " (blocked: " + blocked?.id + ")")}");
   ShootFloor("tr_fill_" + trLang + "_" + stage);
  }

  /// <summary>The fixtures at the tier a player who evolved them would have (bigger gondolas, premium finish),
  /// through the same snapshot patch as eventstiers; sectors only where all of them belong (hipermercado, rede).</summary>
  void TrTiers(int shelves, int sectors) {
   tierPatching = shelves > 0 || sectors > 0; tierShelves = shelves; tierSector = sectors;
   CheckoutBridge.TestPatch = tierPatching ? s => { Patch(s); PatchTiers(s); } : (System.Action<Snapshot>)Patch;
  }

  /// <summary>Decorations outside by the door (not saved, not bought: only the picture; TrFill keeps them).</summary>
  void TrDecorateOutside(string[] outside) {
   var room = CheckoutInterior.Active; if (!room) return;
   int put = 0; var door = room.EntrancePoint;
   for (int i = 0; i < outside.Length; i++) {
    var p = door + new Vector3((i - (outside.Length - 1) * .5f) * 2.6f + (i >= outside.Length / 2 ? 2f : -2f), 0, -2.2f);
    if (room.AddDecor(outside[i], p, true) != null) put++;
   }
   Note($"trailer: {put} decorations outside");
  }

  static IEnumerator TrThen(IEnumerator work, System.Action done) { yield return work; done(); }

  IEnumerator Trailer(string request) {
   var parts = request.Split('-');
   trLang = parts.Length > 1 && parts[1] == "en" ? "en" : "pt";
   var scenes = parts.Length > 2 ? parts[2].Split('.') : new[] { "mesa", "caixa", "cresce", "repor", "hiper", "padaria", "evento", "rede" };
   if (!CheckoutStartMenu.QaMode) { Note("trailer: not on the QA copy, stopping"); yield break; }
   Note("trailer: " + CheckoutQaGameView.Set(1920, 1080));
   void Lang(string l) { CheckoutI18n.SetLanguage(l); CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"" + l + "\"}"); }
   var langBefore = CheckoutI18n.Language; Lang(trLang);
   crowdChainName = trLang == "en" ? "Fresh Market" : "Bom Preço";
   recW = 1920; recQ = 90;
   // The footage at the best quality (Lucas 08/11: "quando a câmera move, tem alguns assets que ele fica meio
   // piscando"): the editor runs the phone's level (no anti-aliasing, hard shadows that end 20 m from the camera,
   // early LOD switches), so edges crawled and shadows popped in and out as the camera moved. Ultra, a long shadow
   // reach, and each frame rendered at twice the size and averaged down.
   int qualityBefore = QualitySettings.GetQualityLevel();
   QualitySettings.SetQualityLevel(QualitySettings.names.Length - 1, true);
   QualitySettings.shadowDistance = 160; QualitySettings.antiAliasing = 8;
   recSuper = 4; trFull = true;
   // (and no shadow acne: thin trims such as the chain's totem showed a dark seam that came and went with the camera)
   var lightsBefore = new List<(Light l, float bias, float normal)>();
   foreach (var l in FindObjectsByType<Light>(FindObjectsSortMode.None))
    if (l && l.type == LightType.Directional && l.shadows != LightShadows.None) { lightsBefore.Add((l, l.shadowBias, l.shadowNormalBias)); l.shadowBias = Mathf.Max(l.shadowBias, .12f); l.shadowNormalBias = Mathf.Max(l.shadowNormalBias, .6f); }
   Note($"trailer: quality {QualitySettings.names[QualitySettings.GetQualityLevel()]} (was {QualitySettings.names[qualityBefore]}), AA {QualitySettings.antiAliasing}, shadows {QualitySettings.shadowDistance} m, frames x{recSuper}");
   yield return new WaitForSecondsRealtime(2f);
   try {
    foreach (var scene in scenes) {
     trScene = scene; trShotK = 0;
     foreach (var f in Directory.GetFiles("Logs", $"tr_{trLang}_{scene}_*.mjpg")) File.Delete(f);
     Note("TRAILER scene " + scene);
     IEnumerator run = scene == "fill" ? TrFillOnly() : scene == "mesa" ? TrMesa() : scene == "caixa" ? TrCaixa() : scene == "cresce" ? TrCresce() : scene == "repor" ? TrRepor()
      : scene == "hiper" ? TrHiper() : scene == "padaria" ? TrPadaria() : scene == "evento" ? TrEvento() : scene == "rede" ? TrRede() : null;
     if (run == null) { Note("trailer: unknown scene " + scene); continue; }
     yield return run;
    }
   } finally {
    if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
    roomEra = -1; roomKeepInterior = false; roomLanes = false; crowdLayout = null; lowShelves = false; TrTiers(-1, -1);
    tierLayout = null; tierOwned = null; tierDecor = null; CheckoutBridge.QaNoVisits = false; trFull = false;
    foreach (var (l, bias, normal) in lightsBefore) if (l) { l.shadowBias = bias; l.shadowNormalBias = normal; }
    recSuper = 1; QualitySettings.SetQualityLevel(qualityBefore, true);   // (the level brings its own shadows and AA back)
    recW = 1280; recQ = 74; TrHideHud(false); MarketDay.MarketSimulation.Cinematic = false; crowdChainName = "Bom Preço";
    Lang(langBefore); Note("trailer: language back to " + CheckoutI18n.Language);
   }
  }

  /// <summary>Layout check only (no recording): the furnished mercadinho, hypermarket and chain, a still of each floor.</summary>
  IEnumerator TrFillOnly() {
   TrHud("setMarketLevel", "[45]"); TrHud("devAdjustCoins", "[9000000]"); yield return new WaitForSecondsRealtime(2f);
   TrHud("dismissLevelUp", "[]"); yield return CloseCardsSettled();
   foreach (var (stage, t, sec, extra) in new[] { ("spati", 2, -1, ""), ("mercadinho", 4, -1, ""), ("hipermercado", 5, 3, ".lanes"), ("rede", 5, 3, ".lanes.brand") }) {
    TrTiers(t, sec); yield return TrCrowd(stage, 6, extra); yield return TrFill(stage); yield return new WaitForSecondsRealtime(2f);
   }
  }

  // ── scenes ──────────────────────────────────────────────────────────────────────────────────────────────────────

  IEnumerator TrMesa() {
   TrHud("resetGame", "[]"); yield return new WaitForSecondsRealtime(5f);
   TrHud("skipOnboarding", "[]"); yield return new WaitForSecondsRealtime(1.5f);
   // One customer at the little table (Lucas 08/11: "só coloca um cliente sendo atendido"): the day's own visitors
   // stay away (CheckoutBridge.QaNoVisits), one QA shopper walks up and buys.
   CheckoutBridge.QaNoVisits = true;
   foreach (var w in FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None)) if (w && w.gameObject.activeSelf) w.CancelVisit();
   yield return TrOpen(); yield return new WaitForSecondsRealtime(2f);
   var (c, _) = TrShop();
   trLastWalker = null; yield return TrSpawn(1, .1f);
   var who = trLastWalker;
   // (at the table and standing still: buying, not walking past it)
   var last = who ? who.transform.position : Vector3.zero; int still = 0;
   for (float t = 0; t < 60 && who && who.gameObject.activeInHierarchy; t += .25f) {
    yield return new WaitForSecondsRealtime(.25f);
    var pos = who.transform.position; var d = pos - c; d.y = 0;
    still = d.magnitude < 2.8f && (pos - last).magnitude < .04f ? still + 1 : 0; last = pos;
    if (still >= 2) break;
   }
   Note($"trailer: the customer at the table ({(who ? (who.transform.position - c).magnitude.ToString("0.0") + " m, phase " + who.VisitPhase : "none")})");
   yield return TrGlideShot(c + new Vector3(.6f, 0, .3f), 3.6f, c, 5f, 4.5f);
   yield return TrGlideShot(c, 6f, c + new Vector3(-1.5f, 0, 1f), 9.5f, 4f);
   CheckoutBridge.QaNoVisits = false;
  }

  IEnumerator TrCaixa() {
   var game = CheckoutCounterGame.Instance; if (!game) { Note("trailer: no register"); yield break; }
   bool en = trLang == "en";
   var lines = (bridge.State.shelves ?? new Shelf[0]).Where(s => s != null && s.productId > 0 && !string.IsNullOrEmpty(s.productName) && s.price > 0)
    .GroupBy(s => s.productId).Select(g => g.First()).Take(3)
    .Select((s, i) => new CheckoutLine { productId = s.productId, quantity = i == 0 ? 2 : 1, name = s.productName, unitPrice = System.Math.Max(1, System.Math.Round(s.price)) }).ToList();
   if (lines.Count < 2) lines = new List<CheckoutLine> {
    new CheckoutLine { productId = 1, quantity = 2, name = en ? "Tomato" : "Tomate", unitPrice = 6 },
    new CheckoutLine { productId = 14, quantity = 1, name = en ? "Soda" : "Refrigerante", unitPrice = 9 },
   };
   double total = lines.Sum(l => l.unitPrice * l.quantity);
   double given = total <= 20 ? 20 : total <= 50 ? 50 : 100;
   var fake = new CheckoutEntry { id = "qa-trailer", customerId = "", customerName = "Dona Neide", mood = "", method = "dinheiro", total = total, cashGiven = given, readyAt = 0, expiresAt = double.MaxValue, items = lines.ToArray() };
   game.OpenPreview(fake);
   yield return TrShot(true, TrCounterPlay(game));
   game.Close(); yield return new WaitForSecondsRealtime(1f);
  }
  IEnumerator TrCounterPlay(CheckoutCounterGame game) {
   yield return Frames(1.0f);
   yield return game.QaScanAll();
   yield return Frames(.7f);
   game.QaPayAll(); yield return Frames(1.3f);
   for (int i = 0; i < 12 && game.QaChanging; i++) { game.QaGive(game.QaNextChange); yield return Frames(.4f); }
   yield return Frames(1.6f);
  }

  IEnumerator TrCresce() {
   // a player well on the way: the shelves have their products (they come with the levels)
   TrHud("setMarketLevel", "[45]"); TrHud("devAdjustCoins", "[9000000]"); yield return new WaitForSecondsRealtime(2f);
   TrHud("dismissLevelUp", "[]"); yield return CloseCardsSettled();
   foreach (var stage in new[] { "tenda", "banca", "conteiner", "spati", "quitanda", "minimercado", "mercadinho" }) {
    if (System.Array.IndexOf(EraIds, stage) >= 4) {
     TrTiers(stage == "minimercado" ? 3 : stage == "mercadinho" ? 4 : 2, -1);
     yield return TrCrowd(stage, 16); yield return TrFill(stage); yield return new WaitForSecondsRealtime(10f);
    }
    else {
     if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
     roomEra = -1; roomKeepInterior = false; crowdLayout = null; tierLayout = null; tierOwned = null; tierDecor = null;
     TrHud("devSetMarketEra", "[\"" + stage + "\"]"); yield return new WaitForSecondsRealtime(10f);
     yield return TrOpen(); yield return new WaitForSecondsRealtime(9f);
    }
    var (c, size) = TrShop();
    float z = Mathf.Clamp(size * .55f + 3.2f, 5f, 15f);
    yield return TrGlideShot(c + new Vector3(.9f, 0, .5f), z * 1.1f, c, z, 2.6f);
   }
  }

  IEnumerator TrRepor() {
   if (bridge.State?.era?.id != "mercadinho") { yield return TrCrowd("mercadinho", 14); yield return TrFill("mercadinho"); yield return new WaitForSecondsRealtime(4f); }
   var game = CheckoutRestockGame.Instance; if (!game) { Note("trailer: no restock game"); yield break; }
   lowShelves = true; yield return new WaitForSecondsRealtime(1.5f);
   CheckoutRestockGame.Show(); yield return new WaitForSecondsRealtime(1.5f);
   if (!game.IsOpen) { var id = bridge.State.restockSlots?.FirstOrDefault()?.shelfId; if (id != null) { CheckoutRestockGame.ShowFixture(id); yield return new WaitForSecondsRealtime(1.5f); } }
   if (!game.IsOpen) { Note("trailer: the restock game did not open"); lowShelves = false; yield break; }
   yield return TrShot(true, TrRestockPlay(game));
   lowShelves = false; CloseRestock(); yield return new WaitForSecondsRealtime(1f);
  }
  IEnumerator TrRestockPlay(CheckoutRestockGame game) {
   yield return Frames(.8f);
   // one fixture after another: the game opens the next one by itself after each round
   int budget = 30 * 11;
   while (budget > 0 && game.IsOpen) {
    bool done = false; var run = StartCoroutine(TrThen(game.QaPlayAll(), () => done = true));
    while (!done && budget > 0 && game.IsOpen) { budget--; yield return null; }
    if (!done) { StopCoroutine(run); break; }
    for (int i = 0; i < 75 && budget > 0; i++) { budget--; yield return null; }
   }
  }

  IEnumerator TrHiper() {
   TrTiers(5, 3);
   yield return TrCrowd("hipermercado", 44, ".lanes");
   TrDecorateOutside(new[] { "flower-bed", "ice-cream-cart", "bench", "popcorn-cart" });
   yield return TrFill("hipermercado");
   yield return new WaitForSecondsRealtime(16f);   // the shoppers walk in
   var (c, size) = TrShop();
   var inside = CheckoutInterior.Active;
   // the building and the street from outside, then across the aisles, the checkouts, a sector counter
   yield return TrGlideShot(c + new Vector3(-6, 0, -8), 20f, c + new Vector3(0, 0, -2), 15f, 4.5f);
   yield return TrGlideShot(c + new Vector3(-size * .3f, 0, 0), 7.5f, c + new Vector3(size * .3f, 0, 1), 7f, 5f);
   if (inside) {
    var z = inside.CheckoutZone; var lanes = new Vector3(z.center.x, 0, z.center.y);
    yield return TrGlideShot(lanes + new Vector3(-1.5f, 0, 0), 5.2f, lanes + new Vector3(1.5f, 0, .5f), 4.6f, 4f);
    var sector = inside.items.Values.FirstOrDefault(i => i.root && i.id == "sector:acougue") ?? inside.items.Values.FirstOrDefault(i => i.root && i.type == "sector");
    if (sector != null) { var p = sector.root.position; p.y = 0; yield return TrGlideShot(p + new Vector3(.8f, 0, -.6f), 4.2f, p, 3.4f, 4f); }
   }
  }

  IEnumerator TrPadaria() {
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   void Route(string r) => CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"" + r + "\"}");
   // the bakery tray puzzle, played the way the deal solves it
   Route("kitchen:croissant-premium:0"); yield return new WaitForSecondsRealtime(3f);
   yield return TrShot(true, TrTrayPlay(hud));
   Route(""); yield return new WaitForSecondsRealtime(1f);
   // the other sectors' puzzles, a moment each
   foreach (var recipe in new[] { "sushi-especial", "sundae-chocolate", "vinho-da-casa" }) {
    Route("kitchen:" + recipe + ":0"); yield return new WaitForSecondsRealtime(3f);
    yield return TrShot(true, Hold(2.4f));
    Route(""); yield return new WaitForSecondsRealtime(1f);
   }
  }
  IEnumerator TrTrayPlay(CheckoutDesktopHUD hud) {
   yield return Frames(.8f);
   for (int i = 0; i < 14 && hud && hud.QaTrayPlace(); i++) yield return Frames(.45f);
   yield return Frames(1.8f);
  }
  static IEnumerator Hold(float seconds) { yield return Frames(seconds); }

  IEnumerator TrEvento() {
   var fx = FindAnyObjectByType<CheckoutEventVisuals>(); if (!fx) { Note("trailer: no event visuals"); yield break; }
   if (bridge.State?.era?.id != "hipermercado" && bridge.State?.era?.id != "rede") { yield return TrCrowd("hipermercado", 30); yield return new WaitForSecondsRealtime(10f); }
   foreach (var (id, zoom) in new[] { ("carro-de-som", 8f), ("feira-de-rua", 10f), ("nevasca", 14f) }) {
    fx.Preview(id); yield return new WaitForSecondsRealtime(id == "carro-de-som" ? 7f : 3f);
    var f = fx.FocusOf(id); f.y = 0;
    yield return TrGlideShot(f + new Vector3(.8f, 0, .4f), zoom * 1.08f, f, zoom, 3.6f);
    fx.Preview(""); yield return new WaitForSecondsRealtime(1.5f);
   }
  }

  IEnumerator TrRede() {
   TrTiers(5, 3);
   yield return TrCrowd("rede", 44, ".lanes.brand");
   TrDecorateOutside(new[] { "flower-bed", "hotdog-cart", "bench", "fountain" });
   yield return TrFill("rede");
   TrHud("orderFromDistributionCenter", "[[{\"productId\":172,\"boxes\":2},{\"productId\":175,\"boxes\":1}]]");
   yield return new WaitForSecondsRealtime(14f);
   var (c, _) = TrShop();
   var letters = GameObject.Find("S4 name");
   if (letters) { var l = letters.transform.position; l.y = 0; yield return TrGlideShot(l + new Vector3(0, 0, -6.5f), 8.5f, l + new Vector3(0, 0, -5.5f), 12f, 4f); }
   yield return TrGlideShot(new Vector3(11, 0, 40), 17f, new Vector3(11, 0, 45), 23f, 4.5f);
   // the whole map from above: the shop first, then everything
   yield return TrGlideShot(c, 13f, new Vector3(4, 0, 17), 30f, 6.5f);
  }
 }
}
