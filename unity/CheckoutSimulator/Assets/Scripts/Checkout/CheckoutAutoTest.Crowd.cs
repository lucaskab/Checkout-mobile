using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 // A crowded little shop ("eventscrowd-<stage>[.seconds[.customers[.keep]]]", QA copy of the save). Lucas 29/10, from a
 // tester's Conveniência full of furniture and customers: "os clientes ficam meio bugados ali na fila... a galera que quer
 // entrar não consegue entrar, ou não consegue andar dentro do espaço". The shop gets every shelf of its expansion placed
 // along the walls (as eventsroom) and the layout is written to Logs/crowd_<stage>_layout.txt; with "keep" the layout of
 // an earlier run is put back at the same saved coordinates instead (a save from before a change) and each piece is
 // checked: still placed, inside the floor, not in a wall, the counter or the way in. Then the market opens and
 // <customers> shoppers with two or three things to buy walk in close together (the host's own customers come too).
 // Measured over <seconds>: people inside (max, mean), the line (longest, seconds with people waiting past the spots
 // inside), customers held up while walking (a stop of more than 3 s / 8 s on the way somewhere), the safety net firing
 // (CheckoutWalker.QaUnsticks / QaForceExits), seconds with someone standing in the doorway, outside waiting to get in,
 // and per QA shopper the time to get in, to pay and the visits that never paid. Logs/crowd_<stage>[_keep].txt, pictures
 // Logs/crowd_<stage>_{home,close,top,jams}.jpg (jams: a plan of where people were held up, red > 3 s).
 public sealed partial class CheckoutAutoTest {
  InteriorItem[] crowdLayout;
  IEnumerator Crowd(string request) {
   var parts = request.Split('-'); var args = parts.Length > 1 ? parts[1].Split('.') : new[] { "spati" };
   string stage = args[0];
   float seconds = args.Length > 1 && float.TryParse(args[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var s) && s > 0 ? s : 150;
   int count = args.Length > 2 && int.TryParse(args[2], out var n) && n > 0 ? n : 16;
   bool keep = args.Contains("keep");
   // ".carts" (Evoluções dos móveis): the three cart stations bought and placed by the entrance, the QA shoppers take
   // basket / cart / big cart / hands in turn; per carrier: who got in and paid, and what the host's own customers took.
   bool carts = args.Contains("carts");
   // ".stock" (implied by ".carts"): every shelf topped up from the storeroom, so the host's own customers find
   // something to buy (the QA save's shelves are nearly empty, and an empty-handed customer never reaches the till).
   bool stock = carts || args.Contains("stock");
   string tag = stage + (keep ? "_keep" : "") + (carts ? "_carts" : stock ? "_stock" : "");
   int era = System.Array.IndexOf(EraIds, stage); if (era < 0) { Note("unknown stage " + stage); yield break; }
   var lines = new List<string>();
   void Line(string t) { lines.Add(t); Note("CROWD " + t); }
   string layoutFile = $"Logs/crowd_{stage}_layout.txt";
   var inside = CheckoutInterior.Active; if (inside) inside.editing = false;
   roomEra = era; roomExtras = false; roomKeepInterior = false; crowdLayout = null;
   List<string[]> before = null;
   if (keep) {
    if (!File.Exists(layoutFile)) { Line("no saved layout " + layoutFile + ": run eventscrowd-" + stage + " first"); roomEra = -1; yield break; }
    before = File.ReadAllLines(layoutFile).Where(l => !l.StartsWith("#") && l.Trim().Length > 0).Select(l => l.Split(';')).ToList();
    crowdLayout = before.Select(b => new InteriorItem { id = b[0], type = b[1], x = F(b[2]), z = F(b[3]), rot = F(b[4]) }).ToArray();
   }
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-crowd-" + stage + "\",\"action\":\"devSetMarketEra\",\"args\":[\"" + stage + "\"]}");
   yield return new WaitForSecondsRealtime(18);
   string[] stationTypes = { "basket-station", "cart-corral", "big-cart-corral" };
   if (carts) {
    Hud("setMarketLevel", "[60]");
    Hud("grantCurrencyPurchase", "[{\"coins\":2000000,\"diamonds\":500,\"transactionId\":\"qa-crowd-carts-" + System.DateTime.Now.Ticks + "\"}]");
    yield return new WaitForSecondsRealtime(1.5f);
    foreach (var st in stationTypes) { Hud("purchaseDecor", "[\"" + st + "\",\"coins\"]"); yield return new WaitForSecondsRealtime(1f); }
    Hud("dismissLevelUp", "[]"); yield return new WaitForSecondsRealtime(1f); var hudUi = FindAnyObjectByType<CheckoutDesktopHUD>(); if (hudUi && (hudUi.LevelUpOpen || hudUi.ConquestOpen)) hudUi.QaCloseCelebrations();
   }
   inside = CheckoutInterior.Active; var map = FindAnyObjectByType<CheckoutMap>();
   if (!inside || !map) { Line("no interior"); roomEra = -1; crowdLayout = null; yield break; }
   var floor = inside.FloorRect;
   Line($"{stage}: era {bridge.State?.era?.id} shop={CheckoutStall.ShopInside} floor {floor.xMin:0.00},{floor.yMin:0.00} .. {floor.xMax:0.00},{floor.yMax:0.00} ({floor.width:0.00} x {floor.height:0.00} m = {floor.width * floor.height:0.0} m2) door x {CheckoutStall.Door.x:0.00} half {CheckoutStall.DoorHalf:0.00} counter {CheckoutStall.CounterArea} placedCounter={CheckoutStall.PlacedCounter}");
   if (!keep) {
    // Furnished the way eventsroom does it: counters first, shelves in buying order, along the walls first.
    inside.editing = true; yield return new WaitForSecondsRealtime(.5f);
    Line("waiting: " + string.Join(", ", inside.waiting.Keys) + "; placed: " + string.Join(", ", inside.items.Values.Where(i => i.root && i.functional).Select(i => i.id)));
    var order = inside.waiting.Keys.OrderBy(k => k.StartsWith("checkout") || k.StartsWith("kiosk") ? 0 : k.StartsWith("shelf") ? 1 : 2)
     .ThenBy(k => k.StartsWith("shelf:") && ShelfEra.TryGetValue(k.Substring(6), out var e) ? e : 0).ThenBy(k => k).ToList();
    var starts = new List<Vector3>();
    for (float z = floor.yMax - 1; z > floor.yMin; z -= .75f) for (float x = floor.xMin + 1; x < floor.xMax; x += .75f) starts.Add(new Vector3(x, CheckoutInterior.Floor, z));
    float Wall(Vector3 p) => Mathf.Min(Mathf.Min(p.x - floor.xMin, floor.xMax - p.x), floor.yMax - p.z);
    starts = starts.OrderBy(p => Mathf.Round(Wall(p) * 2) / 2).ThenBy(p => -p.z).ThenBy(p => p.x).ToList();
    foreach (var id in order) {
     if (!inside.waiting.ContainsKey(id)) continue;
     bool counter = id.StartsWith("checkout") || id.StartsWith("kiosk");
     CheckoutInterior.Item placed = null; int tries = 0;
     var points = counter ? new List<Vector3> { new Vector3(inside.CheckoutZone.center.x, CheckoutInterior.Floor, floor.yMin + 2) }.Concat(starts.Take(12)).ToList() : starts;
     foreach (var p in points) {
      if (++tries > 36) break;
      var it = inside.PlaceWaiting(id, p); if (it == null) break;
      if (inside.Reachable(out _)) { placed = it; break; }
      inside.Unplace(it);
     }
     Line(placed != null ? $"placed {id} at ({placed.root.position.x:0.00},{placed.root.position.z:0.00}) rot {placed.rot:0}" : $"NO ROOM {id}");
    }
    // A shop where the player places the checkout (minimercado) opens only with it placed: in its zone by the east wall.
    if (CheckoutStall.PlacedCounter && inside.Get("checkout:main") == null) {
     if (!inside.waiting.ContainsKey("checkout:main")) inside.waiting["checkout:main"] = ("checkout", "checkout");
     var z = inside.CheckoutZone; var put = inside.PlaceWaiting("checkout:main", new Vector3(z.center.x, CheckoutInterior.Floor, z.center.y));
     Line(put != null ? $"placed checkout:main at ({put.root.position.x:0.00},{put.root.position.z:0.00}) rot {put.rot:0}" : "NO ROOM checkout:main");
    }
    if (carts) {
     // the stations along the front wall, past the way in
     var door0 = map.Entrance; float sx = Mathf.Max(floor.xMin + .5f, door0.x + 2.6f);
     foreach (var st in stationTypes) {
      var it = inside.AddDecor(st, new Vector3(sx, CheckoutInterior.Floor, floor.yMin + .9f));
      Line(it != null ? $"placed {st} ({it.template}) at ({it.root.position.x:0.00},{it.root.position.z:0.00})" : $"NO ROOM {st}");
      sx += 2.8f;
     }
    }
    map.FurnitureChanged(false); map.SaveInterior();
    roomKeepInterior = true; inside.MarkPending(); inside.editing = false;
    var saved = new List<string> { $"# {stage} layout (Item x;z;rot = saved coordinates) from {System.DateTime.Now:yyyy-MM-dd HH:mm}; world position after" };
    foreach (var it in inside.items.Values.Where(i => i.root && i.functional && !i.outside).OrderBy(i => i.id))
     saved.Add(string.Join(";", it.id, it.type, it.x.ToString("0.0000", CultureInfo.InvariantCulture), it.z.ToString("0.0000", CultureInfo.InvariantCulture), it.rot.ToString("0.0", CultureInfo.InvariantCulture), it.root.position.x.ToString("0.000", CultureInfo.InvariantCulture), it.root.position.z.ToString("0.000", CultureInfo.InvariantCulture)));
    File.WriteAllLines(layoutFile, saved);
    yield return new WaitForSecondsRealtime(3);
   } else {
    // The pieces of the old layout, at their saved coordinates, against the shop as it is now.
    yield return new WaitForSecondsRealtime(3);
    int ok = 0;
    foreach (var b in before) {
     var it = inside.Get(b[0]);
     if (it == null || !it.root || !it.root.gameObject.activeInHierarchy) { Line($"LAYOUT {b[0]}: NOT PLACED (waiting={inside.waiting.ContainsKey(b[0])})"); continue; }
     var p = it.root.position; float dx = b.Length > 6 ? p.x - F(b[5]) : 0, dz = b.Length > 6 ? p.z - F(b[6]) : 0;
     var f = inside.FootprintOf(it); bool inFloor = true;
     foreach (var c in new[] { f.c + f.ax * f.hx + f.az * f.hz, f.c - f.ax * f.hx + f.az * f.hz, f.c + f.ax * f.hx - f.az * f.hz, f.c - f.ax * f.hx - f.az * f.hz })
      if (c.x < floor.xMin - .01f || c.x > floor.xMax + .01f || c.y < floor.yMin - .01f || c.y > floor.yMax + .01f) inFloor = false;
     bool fits = inside.Fits(it, p, it.rot, out var why);
     bool same = Mathf.Abs(dx) < .005f && Mathf.Abs(dz) < .005f;
     if (inFloor && fits && same) ok++;
     Line($"LAYOUT {b[0]}: at ({p.x:0.000},{p.z:0.000}) moved ({dx:0.000},{dz:0.000}) inside floor={inFloor} fits={fits}{(fits ? "" : " (" + why + ")")}");
    }
    Line($"LAYOUT {stage}: {ok}/{before.Count} pieces kept their spot, inside the floor and valid");
    // the host keeps the layout too (a shop whose checkout waits in the inventory does not open)
    inside.MarkPending(); map.SaveInterior(); roomKeepInterior = true; crowdLayout = null; yield return new WaitForSecondsRealtime(2);
   }
   var cam = FindAnyObjectByType<MarketDay.MarketSimulation>(); if (cam) cam.HomeCamera();
   // A day that would end during the run (scenarios chained in one play) is closed first, so the run gets a whole day.
   if (bridge.State.isOpen && bridge.State.day != null && bridge.State.day.phase == "open" && bridge.State.day.endsAt - CheckoutBridge.Now < (seconds + 30) * 1000) {
    Line($"day ends in {(bridge.State.day.endsAt - CheckoutBridge.Now) / 1000:0}s: closed for a fresh one");
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-close-" + tag + "\",\"action\":\"closeDay\",\"args\":[]}");
    for (float t = 0; t < 4 && bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f);
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-claim-" + tag + "\",\"action\":\"claimDayResult\",\"args\":[]}"); yield return new WaitForSecondsRealtime(1);
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-dismiss-" + tag + "\",\"action\":\"dismissLevelUp\",\"args\":[]}"); yield return new WaitForSecondsRealtime(.5f);
   }
   // Open for customers (as eventsstalls).
   if (!bridge.State.isOpen) {
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-claim\",\"action\":\"claimDayResult\",\"args\":[]}"); yield return new WaitForSecondsRealtime(1);
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-day\",\"action\":\"startDay\",\"args\":[\"livre\"]}"); for (float t = 0; t < 4 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f);
    if (!bridge.State.isOpen) { CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}"); for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f); }
   }
   Line($"open={bridge.State.isOpen} day {bridge.State.day?.phase} capacity {CheckoutStall.Capacity} line places {CheckoutStall.QueueInside}");
   foreach (var l in NavReport(tag)) Line("NAV " + l);
   void Stock() {
    foreach (var sh in bridge.State.shelves ?? System.Array.Empty<Shelf>())
     if (sh != null && sh.unlocked && !sh.building && sh.productId > 0 && sh.stock < sh.capacity) {
      int add = sh.capacity - sh.stock;
      Hud("devAdjustInventory", $"[{sh.productId},{add}]");
      Hud("restockShelf", "[{\"shelfId\":\"" + sh.id + "\",\"productId\":" + sh.productId + ",\"amount\":" + add + "}]");
     }
   }
   if (stock) { Stock(); yield return new WaitForSecondsRealtime(1.5f); Line("stocked: " + string.Join(", ", (bridge.State.shelves ?? System.Array.Empty<Shelf>()).Where(x => x.unlocked).Select(x => $"{x.id} {x.stock}/{x.capacity}"))); }
   float nextStock = Time.time + 20;
   // The 5-minute day may end during the run (everyone heads home then): logged, and the next day started at once.
   var day0 = bridge.State.day; Line($"day {day0?.phase} ends in {((day0?.endsAt ?? 0) - CheckoutBridge.Now) / 1000:0}s");
   bool wasOpen = bridge.State.isOpen; int closes = 0; float reopenStep = -1, closedSec = 0;
   var shelfIds = inside.items.Values.Where(i => i.root && i.type == "shelf" && !i.building).Select(i => i.id.Substring(6)).ToList();
   if (shelfIds.Count == 0) shelfIds = (bridge.State.shelves ?? System.Array.Empty<Shelf>()).Where(x => x.unlocked).Select(x => x.id).ToList();
   var rnd = new System.Random(29);
   int unstick0 = CheckoutWalker.QaUnsticks, exit0 = CheckoutWalker.QaForceExits;
   var all = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).ToList();
   var visits = new Dictionary<CheckoutWalker, CrowdVisit>(); var done = new List<CrowdVisit>();
   var jam = new Dictionary<CheckoutWalker, float>(); var flagged3 = new HashSet<CheckoutWalker>(); var flagged8 = new HashSet<CheckoutWalker>();
   var doorStand = new Dictionary<CheckoutWalker, float>(); var dots = new List<TrailDot>();
   int sent = 0, stops3 = 0, stops8 = 0, maxInside = 0, maxLine = 0, maxOutside = 0; float insideSum = 0, overflowSec = 0, doorSec = 0, waitOutSec = 0, longestStop = 0, t0 = Time.time, nextSend = 0;
   string longestWho = "";
   float gap = Mathf.Max(1.2f, seconds * .45f / count);   // the shoppers set off within the first half of the run
   bool shotClose = false, shotTop = false; float nextLineNote = 15;
   var door = CheckoutStall.Door; float doorHalf = CheckoutStall.DoorHalf;
   Rect doorZone = Rect.MinMaxRect(door.x - doorHalf - .25f, door.y - 1.1f, door.x + doorHalf + .25f, door.y + .9f);
   // The register is served at once, as by an attentive player or a cashier: the host's customers otherwise wait at
   // the till for the player (up to 150 s) and the line would measure that, not the room.
   var served = new HashSet<string>(); float nextServe = 0;
   var carrierShots = new HashSet<string>(); var carrierInside = new HashSet<string>();
   var hostCarriers = new Dictionary<string, (string carrier, int products, int units)>();
   // Everyone who paid in the run (the host's customers too): the register's real throughput.
   var paidBefore = new Dictionary<CheckoutWalker, bool>(); int paidAll = 0;
   while (Time.time - t0 < seconds) {
    yield return null; float dt = Time.deltaTime; if (dt <= 0) continue;
    if (stock && Time.time >= nextStock) { nextStock = Time.time + 20; Stock(); }
    bool openNow = bridge.State.isOpen;
    if (!openNow) closedSec += dt;
    if (wasOpen && !openNow) { closes++; reopenStep = 0; Line($"market closed at t={Time.time - t0:0} (day {bridge.State.day?.phase})"); }
    wasOpen = openNow;
    if (reopenStep >= 0 && !openNow) {
     reopenStep += dt;
     if (reopenStep > 1 && reopenStep - dt <= 1) { CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-claim-" + closes + "\",\"action\":\"claimDayResult\",\"args\":[]}"); CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-day-" + closes + "\",\"action\":\"startDay\",\"args\":[\"livre\"]}"); }
     if (reopenStep > 4 && reopenStep - dt <= 4) CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open-" + closes + "\",\"action\":\"setMarketOpen\",\"args\":[true]}");
    } else if (openNow) reopenStep = -1;
    if (Time.time >= nextServe) {
     nextServe = Time.time + .5f;
     if (carts) foreach (var c in bridge.State.customers ?? System.Array.Empty<Customer>())
      if (c != null && !string.IsNullOrEmpty(c.id) && !c.id.StartsWith("qa-") && !hostCarriers.ContainsKey(c.id))
       hostCarriers[c.id] = (string.IsNullOrEmpty(c.carrier) ? "-" : c.carrier, (c.purchases ?? System.Array.Empty<Purchase>()).Length, (c.purchases ?? System.Array.Empty<Purchase>()).Sum(x => x.quantity));
     foreach (var e in bridge.State.checkouts ?? System.Array.Empty<CheckoutEntry>())
      if (e != null && e.readyAt <= CheckoutBridge.Now && served.Add(e.id)) bridge.Command("completeCheckout", "[\"" + e.id + "\"," + System.Math.Max(1, System.Math.Round(e.total)).ToString(CultureInfo.InvariantCulture) + "]");
    }
    // (as the game's own spawning: nobody sets off for a shop with two rows already waiting outside)
    if (sent < count && Time.time >= nextSend && CheckoutWalker.ShopCrowded) nextSend = Time.time + .5f;
    if (sent < count && Time.time >= nextSend) {
     var idle = all.FirstOrDefault(w => w && !w.gameObject.activeSelf && !w.Reserved);
     if (idle) {
      int k = 2 + rnd.Next(2); var buy = new List<Purchase>();
      for (int j = 0; j < k && shelfIds.Count > 0; j++) buy.Add(new Purchase { shelfId = shelfIds[rnd.Next(shelfIds.Count)], productId = 1, quantity = 1 + rnd.Next(2) });
      var carrier = carts ? CrowdCarriers[sent % CrowdCarriers.Length] : null;
      idle.Begin(new Customer { id = "qa-crowd-" + sent, name = "QA", spent = 12, purchases = buy.ToArray(), carrier = carrier });
      visits[idle] = new CrowdVisit { id = "qa-crowd-" + sent, began = Time.time, carrier = carrier }; sent++; nextSend = Time.time + gap;
     } else nextSend = Time.time + .5f;
    }
    int inCount = 0, outWait = 0;
    foreach (var w in all) {
     if (!w || !w.gameObject.activeInHierarchy) { if (w && visits.TryGetValue(w, out var gone) && !gone.closed) { gone.closed = true; gone.left = Time.time; done.Add(gone); visits.Remove(w); } continue; }
     paidBefore.TryGetValue(w, out var hadPaid); if (w.HasPaid && !hadPaid) paidAll++; paidBefore[w] = w.HasPaid;
     var p = w.transform.position; var xz = new Vector2(p.x, p.z);
     // (the market building: its floor; the small shops: their interior)
     bool In = CheckoutStall.ShopInside ? CheckoutStall.InteriorFloor.Contains(xz) : !CheckoutStall.Small && floor.Contains(xz);
     if (carts && In) {
      var rig = w.GetComponent<CheckoutShopperRig>();
      if (rig && !string.IsNullOrEmpty(rig.carrier) && w.name.Length > 0 && (w.VisitPhase == 0 || w.VisitPhase == 1)) {
       bool wheeled = rig.carrier == "cart" || rig.carrier == "bigCart";
       // (the picture: taking a product off a shelf well inside, not still at the door behind the shop window)
       if (rig.cart == wheeled && w.VisitPhase == 1 && p.z > floor.yMin + 3f && carrierShots.Add(rig.carrier)) TierShot("ft_carts_inside_" + rig.carrier, 2048, 1152, p + Vector3.up * .8f, 6.5f);
       carrierInside.Add(w.name + "#" + all.IndexOf(w) + ":" + rig.carrier);
      }
     }
     if (In) inCount++;
     if (w.VisitPhase == 18) outWait++;
     var agent = w.GetComponent<NavMeshAgent>(); if (!agent || !agent.isOnNavMesh) continue;
     float speed = new Vector2(agent.velocity.x, agent.velocity.z).magnitude;
     // (only near the shop: people leaving along the city's sidewalks are not part of it)
     var near = CheckoutStall.Footprint; bool atShop = Mathf.Abs(p.x - near.center.x) < near.size.x * .5f + 4 && Mathf.Abs(p.z - near.center.z) < near.size.z * .5f + 4;
     bool walking = atShop && !agent.isStopped && agent.hasPath && Vector3.Distance(agent.nextPosition, w.QaTarget) > .6f;
     if (walking && speed < .08f) {
      jam.TryGetValue(w, out var j); j += dt; jam[w] = j;
      if (j > 3 && flagged3.Add(w)) stops3++;
      if (j > 8 && flagged8.Add(w)) stops8++;
      if (j > longestStop) { longestStop = j; longestWho = $"{w.name} phase {w.VisitPhase} at ({p.x:0.0},{p.z:0.0}) going to ({w.QaTarget.x:0.0},{w.QaTarget.z:0.0})"; }
     } else { jam[w] = 0; flagged3.Remove(w); flagged8.Remove(w); }
     if (doorZone.Contains(xz) && speed < .08f) { doorStand.TryGetValue(w, out var d); doorStand[w] = d + dt; } else doorStand[w] = 0;
     if (visits.TryGetValue(w, out var v)) {
      if (v.entered < 0 && In) v.entered = Time.time;
      if (v.paid < 0 && w.HasPaid) v.paid = Time.time;
     }
     if ((Time.frameCount & 3) == 0 && dots.Count < 120000) { jam.TryGetValue(w, out var jj); dots.Add(new TrailDot { p = p, slip = jj > 3 ? 20 : jj > 1 ? 5 : 0 }); }
    }
    if (doorStand.Values.Any(d => d > 1f)) doorSec += dt;
    int line = bridge.Queue.Count; foreach (var lane in map.Lanes.lanes) line = Mathf.Max(line, lane.queue.Count);
    maxLine = Mathf.Max(maxLine, line); if (line > CheckoutStall.QueueInside) overflowSec += dt;
    maxInside = Mathf.Max(maxInside, inCount); insideSum += inCount * dt; maxOutside = Mathf.Max(maxOutside, outWait); if (outWait > 0) waitOutSec += dt;
    float at = Time.time - t0;
    // Every 15 s: who is in the line and how far from their place (the front: phase and distance to the till).
    if (at >= nextLineNote) {
     nextLineNote += 15;
     var q = map.Lanes.lanes.Count > 0 ? map.Lanes.lanes[0].queue : bridge.Queue; var b = new StringBuilder();
     for (int i = 0; i < q.Count && i < 5; i++) { var w = q[i]; if (!w) continue; var ag = w.GetComponent<NavMeshAgent>(); b.Append($" [{i} {w.name} ph{w.VisitPhase} {Vector3.Distance(w.transform.position, w.QaTarget):0.0}m stuck{(jam.TryGetValue(w, out var jj2) ? jj2 : 0):0}s]"); }
     var phases = all.Where(w => w && w.gameObject.activeInHierarchy).GroupBy(w => w.VisitPhase).OrderBy(g => g.Key).Select(g => $"{g.Key}:{g.Count()}");
     Note($"CROWD t={at:0} line {q.Count}:{b} | phases {string.Join(" ", phases)}");
    }
    if (!shotClose && at > seconds * .5f) { shotClose = true; var fc = CheckoutStall.Footprint; CaptureAt(new Vector3(fc.center.x, .6f, fc.center.z - .4f), Mathf.Max(fc.size.x, fc.size.z) * 1.5f + 1, $"crowd_{tag}_close"); Capture($"crowd_{tag}_home"); }
    if (!shotTop && at > seconds * .55f) { shotTop = true; var c = floor.center; TopDown(new Vector3(c.x, 0, c.y), Mathf.Max(floor.width, floor.height) + 5, $"crowd_{tag}_top"); }
   }
   foreach (var pair in visits) { pair.Value.left = -1; done.Add(pair.Value); }
   float elapsed = Time.time - t0;
   var paid = done.Where(v => v.paid > 0).ToList(); var noPay = done.Where(v => v.paid < 0 && v.closed).ToList(); var still = done.Where(v => !v.closed).ToList();
   float Mean(IEnumerable<float> l) { var a = l.ToList(); return a.Count > 0 ? a.Average() : 0; }
   float Max(IEnumerable<float> l) { var a = l.ToList(); return a.Count > 0 ? a.Max() : 0; }
   Line($"RESULT {tag}: floor {floor.width * floor.height:0.0} m2, {sent} QA shoppers over {elapsed:0}s; inside max {maxInside} mean {insideSum / elapsed:0.0}; line max {maxLine} (spots inside {CheckoutStall.QueueInside}), {overflowSec:0}s past them; " +
        $"held up >3s: {stops3}, >8s: {stops8}, longest {longestStop:0.0}s ({longestWho}); safety net unstick {CheckoutWalker.QaUnsticks - unstick0} force-exit {CheckoutWalker.QaForceExits - exit0}; " +
        $"doorway blocked {doorSec:0}s; waiting outside max {maxOutside} ({waitOutSec:0}s); " +
        $"host checkouts served {served.Count}; paid (everyone) {paidAll}; " +
        $"market closed {closes}x ({closedSec:0}s); " +
        $"QA visits paid {paid.Count}/{sent} (time to get in mean {Mean(paid.Where(v => v.entered > 0).Select(v => v.entered - v.began)):0}s, to pay mean {Mean(paid.Select(v => v.paid - v.began)):0}s max {Max(paid.Select(v => v.paid - v.began)):0}s), left without paying {noPay.Count}, still in the shop {still.Count}");
   if (carts) {
    var qa = CrowdCarriers.Select(c => $"{c}: sent {done.Count(v => v.carrier == c)} in {carrierInside.Count(x => x.EndsWith(":" + c))} paid {paid.Count(v => v.carrier == c)} shot {(carrierShots.Contains(c) ? "yes" : "no")}");
    var host = hostCarriers.Values.GroupBy(v => v.carrier).OrderBy(g => g.Key).Select(g => $"{g.Key} n={g.Count()} products mean {g.Average(v => v.products):0.0} max {g.Max(v => v.products)} units mean {g.Average(v => v.units):0.0}");
    Line($"RESULT {tag} carriers: QA shoppers by carrier (in = walkers of that carrier seen shopping inside, the host's too) [{string.Join("; ", qa)}]; host customers by carrier [{string.Join("; ", host)}]");
   }
   TrailMap(dots, $"crowd_{tag}_jams", new Vector3(floor.center.x, 0, floor.center.y - 1), Mathf.Max(floor.width, floor.height) + 6);
   File.WriteAllLines($"Logs/crowd_{tag}.txt", lines);
   // Everyone sent home, so the next run starts with an empty shop and free walkers.
   foreach (var w in all) if (w && w.gameObject.activeSelf) w.CancelVisit();
   yield return new WaitForSecondsRealtime(1);
   roomEra = -1; roomKeepInterior = false; crowdLayout = null;
  }
  static readonly string[] CrowdCarriers = { "basket", "cart", "bigCart", "hands" };
  sealed class CrowdVisit { public string id, carrier; public float began, entered = -1, paid = -1, left = -1; public bool closed; }
  static float F(string s) => float.Parse(s, NumberStyles.Float, CultureInfo.InvariantCulture);
 }
}
