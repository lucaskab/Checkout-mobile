using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 // "Evoluções dos móveis" (docs-drafts/evolucoes-moveis.md), on the QA copy of the save ("eventstiers[-part.part]"):
 //  - flow:     the real store actions — capacity steps per shop (T1..cap, blocked above it), the checkout's steps, the cold
 //              room bought and built, the ATM evolved, a cart station bought — checked against the next snapshots.
 //  - shelves:  every product fixture at every tier its shop allows, laid out in the real shop (Conveniência → Supermercado):
 //              Logs/ft_shelves_<stage>_T<n>.jpg, and how many pieces had to stay smaller for lack of room.
 //  - checkout: the checkout's tiers in the shops that place it: Logs/ft_checkout_<stage>_T<n>.jpg.
 //  - coldroom: the cold room's tier in every expansion (Mesinha → Rede), where it stands and why:
 //              Logs/ft_cold_<stage>_{close,map}.jpg.
 //  - carts:    the three stations in the supermarket and QA customers with hands, basket, cart and big cart:
 //              Logs/ft_carts_{close,shoppers}.jpg.
 //  - decor:    ATM T1–T3, gumball T1–T2, claw T1–T3 placed in the supermarket: Logs/ft_decor.jpg.
 // One "RESULT tiers <part>: PASS|FAIL ..." line per part.
 public sealed partial class CheckoutAutoTest {
  int tierShelves = -1, tierSector = -1; bool tierOpen; string tierCheckout, tierCold; InteriorItem[] tierLayout; DecorOwned[] tierOwned; DecorTier[] tierDecor; bool tierPatching;
  static readonly string[] TierKinds = { "produce", "drinks", "bakery", "dairy", "snacks", "coffee", "pizza", "home", "icecream" };
  static readonly Dictionary<string, string> TierKindOf = new Dictionary<string, string> {
   { "produce", "produce" }, { "drinks", "drinks" }, { "bakery", "bakery" }, { "dairy", "dairy" }, { "snacks", "shelf" }, { "coffee", "shelf" }, { "home", "shelf" }, { "pizza", "freezer" }, { "icecream", "icecream" } };

  void PatchTiers(Snapshot s) {
   if (!tierPatching || s == null) return;
   if (tierShelves > 0 && s.shelves != null)
    foreach (var x in s.shelves) if (TierKindOf.TryGetValue(x.id, out var k)) { x.tier = tierShelves; x.tierTemplate = k + "_T" + Mathf.Min(4, tierShelves); x.premium = tierShelves >= 5; }
   if (s.fixtureTiers == null) s.fixtureTiers = new FixtureTiers();
   if (tierCheckout != null) s.fixtureTiers.checkoutTemplate = tierCheckout;
   if (tierSector > 0 && s.sectors != null)
    foreach (var x in s.sectors) if (x != null) { x.unlocked = true; x.building = false; x.tier = tierSector; x.tierTemplate = "sector-" + x.id + "_T" + tierSector; }
   if (tierOpen) s.isOpen = true; // (the carts' shoppers: the QA save may be between days)
   if (tierCold != null) { s.fixtureTiers.coldRoomTemplate = tierCold; s.fixtureTiers.coldRoomBuilding = ""; }
   if (tierLayout != null) s.interior = new InteriorState { items = tierLayout, owned = tierOwned ?? System.Array.Empty<DecorOwned>(), tiers = tierDecor ?? System.Array.Empty<DecorTier>() };
  }

  IEnumerator Tiers(string request) {
   var parts = request.Split('-'); var which = parts.Length > 1 ? parts[1].Split('.') : new[] { "flow", "shelves", "checkout", "coldroom", "carts", "decor" };
   foreach (var f in Directory.GetFiles("Logs", "ft_*.jpg")) File.Delete(f);
   CheckoutBridge.TestPatch = s => { Patch(s); PatchTiers(s); };
   // the QA copy only: pictures in pt-BR and without the guide's coach card
   Hud("skipOnboarding", "[]"); TierLang("pt"); yield return Wait(1.5f);
   foreach (var part in which) {
    Note("TIERS == " + part);
    switch (part) {
     case "flow": yield return TierFlow(); break;
     case "shelves": yield return TierShelves(); break;
     case "checkout": yield return TierCheckout(); break;
     case "coldroom": yield return TierCold(); break;
     case "carts": yield return TierCarts(); break;
     case "decor": yield return TierDecor(); break;
     case "depot": yield return TierDepotProbe(); break;
     case "sectors": yield return TierSectors(); break;
     case "upgrade": yield return TierSectorUpgrade(); break;
     case "ui": yield return TierUi(); break;
     case "floorprobe": yield return TierFloorProbe(); break;
     case "navprobe": yield return TierNavProbe(); break;
     case "markers": yield return TierMarkerShots(); break;
     case "flush": yield return TierFlushAudit(); break;
     case "staff": yield return TierStaffProbe(); break;
     case "perf": yield return TierSectorPerf(); break;
     case "lineup": yield return TierLineup(); break;
     case "paint": yield return TierSectorPaint(); break;
     case "migrate": yield return TierMigrate(); break;
     case "migrateflush": yield return TierMigrateFlush(); break;
     case "wallshots": yield return TierWallShots(); break;
     // evolutions with rewards (CheckoutAutoTest.Evolution)
     case "rewards": yield return EvoRewards(); break;
     case "queue": yield return EvoQueue(); break;
     case "skip": yield return EvoSkip(); break;
     case "oldsave": yield return EvoOldSave(); break;
     case "reveal": yield return EvoReveal(); break;
     case "restock8": yield return EvoRestock8(); break;
     default: Note("unknown part " + part); break;
    }
    TierReset();
   }
   CheckoutBridge.TestPatch = Patch;
  }

  void TierReset() { tierPatching = false; tierOpen = false; tierSector = -1; tierShelves = -1; tierCheckout = tierCold = null; tierLayout = null; tierOwned = null; tierDecor = null; roomEra = -1; var inside = CheckoutInterior.Active; if (inside) inside.editing = false; }

  static int hudSeq;
  void Hud(string action, string args) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-tiers-" + action + "-" + Time.frameCount + "-" + (++hudSeq) + "\",\"action\":\"" + action + "\",\"args\":" + args + "}");
  IEnumerator Wait(float s) { yield return new WaitForSecondsRealtime(s); }

  // ------------------------------------------------------------------ flow (real store actions)
  IEnumerator TierFlow() {
   var fails = new List<string>();
   void Check(bool ok, string what) { Note((ok ? "ok   " : "FAIL ") + what); if (!ok) fails.Add(what); }
   Shelf Sh(string id) => bridge.State.shelves.FirstOrDefault(x => x.id == id);
   Hud("setMarketLevel", "[60]");
   Hud("grantCurrencyPurchase", "[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-tiers-" + System.DateTime.Now.Ticks + "\"}]");
   yield return GoToStage("spati");
   int before = Sh("produce").tier;
   Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Check(Sh("produce").tier == Mathf.Min(2, before + 1) && Sh("produce").tierTemplate.StartsWith("produce_T"), $"spati: produce T{before} → T{Sh("produce").tier} ({Sh("produce").tierTemplate})");
   Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Check(Sh("produce").tier <= 2, $"spati: capped at T2 (shows T{Sh("produce").tier}, capacity {Sh("produce").capacity})");
   Hud("purchaseShopItem", "[\"checkout-register\",\"diamonds\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Check(bridge.State.fixtureTiers != null && bridge.State.fixtureTiers.checkout == 2, $"spati: checkout register → step {bridge.State.fixtureTiers?.checkout}");
   yield return GoToStage("minimercado");
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Check(Sh("produce").tier == 3, $"minimercado: produce T{Sh("produce").tier} ({Sh("produce").tierTemplate}), capacity {Sh("produce").capacity}");
   Hud("purchaseShopItem", "[\"cold-room-2\",\"coins\"]"); yield return Wait(2);
   Check(!string.IsNullOrEmpty(bridge.State.fixtureTiers.coldRoomBuilding), $"minimercado: cold room T2 works '{bridge.State.fixtureTiers.coldRoomBuilding}' until {bridge.State.fixtureTiers.coldRoomEndsAt}");
   yield return Wait(1);
   Note("TIERS cold room while building: " + CheckoutColdRoom.Side);
   Hud("devFinishInteriorConstructions", "[]"); yield return Wait(2);
   Check(bridge.State.fixtureTiers.coldRoom == 2, $"minimercado: cold room tier {bridge.State.fixtureTiers.coldRoom} at {CheckoutColdRoom.Side}");
   yield return GoToStage("supermercado");
   Check(Sh("produce").tier == 3, $"supermercado: produce keeps T{Sh("produce").tier} (bought 3)");
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   Check(Sh("produce").tier == 5 && Sh("produce").premium, $"supermercado: produce ★ (tier {Sh("produce").tier}, premium {Sh("produce").premium})");
   Hud("purchaseDecor", "[\"atm\",\"coins\"]"); yield return Wait(1.5f);
   Hud("upgradeDecorTier", "[\"atm\",\"coins\"]"); yield return Wait(1.5f); Hud("devFinishEvolutions", "[]"); yield return Wait(1.5f);
   var atm = bridge.State.interior?.tiers?.FirstOrDefault(t => t.type == "atm");
   Check(atm != null && atm.tier == 2 && atm.template == "atm_T2", $"ATM → {atm?.tier} {atm?.template}");
   Hud("purchaseDecor", "[\"big-cart-corral\",\"coins\"]"); yield return Wait(2);
   var owned = bridge.State.interior?.owned?.FirstOrDefault(o => o.type == "big-cart-corral");
   Check(owned != null && owned.count > 0, "supermercado: big cart station bought (to place)");
   var customers = bridge.State.customers ?? System.Array.Empty<Customer>();
   Note("TIERS customers' carriers now: " + string.Join(",", customers.Select(c => c.carrier ?? "-")));
   Note($"RESULT tiers flow: {(fails.Count == 0 ? "PASS" : "FAIL")} {fails.Count} failed" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // ------------------------------------------------------------------ every fixture at every tier, inside a real shop
  IEnumerator TierShelves() {
   var stages = new[] { ("spati", 2), ("quitanda", 2), ("minimercado", 3), ("mercadinho", 4), ("supermercado", 5) };
   int shots = 0, shrunk = 0, missing = 0;
   foreach (var (stage, cap) in stages) {
    int era = System.Array.IndexOf(EraIds, stage);
    for (int t = 1; t <= cap; t++) {
     if (cap == 5 && t < 4) continue; // the supermarket: T4 and the premium finish (T1–T3 were shot in the smaller shops)
     yield return ShowTier(stage, era, t, null);
     var inside = CheckoutInterior.Active;
     var pieces = inside.items.Values.Where(i => i.root && i.type == "shelf").ToList();
     int small = pieces.Count(i => i.wantsGrow); shrunk += small; missing += TierKinds.Count(k => ShelfEra[k] <= era) - pieces.Count;
     Note($"TIERS shelves {stage} T{t}: {pieces.Count} placed [{string.Join(", ", pieces.Select(i => i.id.Substring(6) + "=" + i.template + (i.wantsGrow ? "(wants " + i.desired + ")" : "")))}]");
     ShootFloor($"ft_shelves_{stage}_T{t}"); shots++;
    }
   }
   Note($"RESULT tiers shelves: {(missing == 0 ? "PASS" : "FAIL")} {shots} shots, {shrunk} pieces kept a smaller tier for lack of room, {missing} missing");
  }

  // Lays out the fixtures of the shop (as a tidy player would: rows from the back wall, aisles between) at tier `t`,
  // around what else stands on the floor (the sectors, the checkout). In the small shops with a placed counter the
  // checkout is part of the layout too (unplaced, it would wait in the build-mode inventory there).
  IEnumerator ShowTier(string stage, int era, int t, System.Action<List<InteriorItem>, Rect> extra) {
   tierPatching = true; roomEra = era; roomExtras = false; roomKeepInterior = false; tierShelves = t; tierLayout = null;
   yield return GoToStage(stage);
   var inside = CheckoutInterior.Active; if (!inside) { Note("no interior"); yield break; }
   var floor = inside.FloorRect; var zone = inside.CheckoutZone; var layout = inside.LayoutState;
   var fixedItems = new List<InteriorItem>();
   if (CheckoutStall.Small && CheckoutStall.PlacedCounter) {
    var c = CheckoutMarketLayout.Unproject(new Vector3(zone.center.x, 0, floor.yMin + floor.height * .4f), layout);
    fixedItems.Add(new InteriorItem { id = "checkout:main", type = "checkout", x = c.x, z = c.z, rot = 90 });
   }
   extra?.Invoke(fixedItems, floor);
   // First the rest alone, to see where it stands.
   tierLayout = fixedItems.ToArray();
   yield return Reapply();
   // (what stands there, at the size it wants: a piece shown smaller for lack of room still gets its room)
   var blockers = inside.items.Values.Where(i => i.root && i.type != "shelf").Select(i => {
    var rs = i.root.GetComponentsInChildren<Renderer>(); if (rs.Length == 0) return Rect.zero;
    var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds);
    var want = inside.TemplateObject(i.desired ?? i.template)?.GetComponent<CheckoutInteriorPiece>();
    if (want) foreach (var c in new[] { new Vector3(want.min.x, 0, want.min.y), new Vector3(want.max.x, 0, want.min.y), new Vector3(want.min.x, 0, want.max.y), new Vector3(want.max.x, 0, want.max.y) }) bb.Encapsulate(i.root.TransformPoint(c));
    return Rect.MinMaxRect(bb.min.x - .35f, bb.min.z - .35f, bb.max.x + .35f, bb.max.z + .35f);
   }).Where(r => r.width > 0).ToList();
   float right = CheckoutStall.Small && !CheckoutStall.PlacedCounter ? floor.xMax - .2f : zone.xMin - .25f;
   var items = new List<InteriorItem>(fixedItems);
   float rowTop = floor.yMax - .05f, x = floor.xMin + .1f, rowDepth = 0;
   float front = floor.yMin + (CheckoutStall.ShopInside ? 1.8f : 2.4f);
   // a walkway from the front to every row (rows wall to wall would shut the back rows off: customers then route
   // round the outside of the shop to reach them)
   float mid = (floor.xMin + right) * .5f; blockers.Add(Rect.MinMaxRect(mid - .8f, floor.yMin, mid + .8f, floor.yMax));
   foreach (var id in TierKinds.Where(k => ShelfEra[k] <= era)) {
    var template = TierKindOf[id] + "_T" + Mathf.Min(4, t); var piece = inside.TemplateObject(template)?.GetComponent<CheckoutInteriorPiece>();
    if (!piece) { Note("TIERS missing model " + template); continue; }
    float w = piece.max.x - piece.min.x, d = piece.max.y - piece.min.y;
    bool placed = false;
    for (int guard = 0; guard < 40 && !placed; guard++) {
     if (x + w > right) { x = floor.xMin + .1f; rowTop -= rowDepth + 1.35f; rowDepth = 0; }
     if (rowTop - d < front) break;
     var spot = Rect.MinMaxRect(x, rowTop - d, x + w, rowTop);
     var hit = blockers.FirstOrDefault(r => r.Overlaps(spot));
     if (hit.width > 0) { x = hit.xMax + .05f; continue; }
     // rot 0: customers on -Z (facing the front of the shop)
     var b = CheckoutMarketLayout.Unproject(new Vector3(x - piece.min.x, 0, rowTop - piece.max.y), layout);
     items.Add(new InteriorItem { id = "shelf:" + id, type = "shelf", x = b.x, z = b.z, rot = 0 });
     x += w + .3f; rowDepth = Mathf.Max(rowDepth, d); placed = true;
    }
    if (!placed) Note("TIERS no room for " + template + " in the test layout");
   }
   tierLayout = items.ToArray();
   yield return Reapply();
  }

  // The host only sends a snapshot when something changes: apply the patched one now.
  IEnumerator Reapply() {
   var map = FindAnyObjectByType<CheckoutMap>();
   for (int i = 0; i < 2; i++) { var st = bridge.State; if (st != null && map) { Patch(st); PatchTiers(st); map.Apply(st); } yield return Wait(1.5f); }
  }

  // The shell's ceiling dressing (bunting and pendant lamps, "Market Stage Dressing") hangs over the floor and reads as
  // clutter from above: hidden while a tier shot is taken (screenshots only, the game keeps it).
  void TierShot(string name, int w, int h, Vector3? target, float size) {
   var dressing = GameObject.Find("Supermarket World/Market Stage Dressing");
   var hidden = new List<GameObject>();
   if (dressing) foreach (Transform c in dressing.transform) if (c.gameObject.activeSelf && (c.name.StartsWith("Bunting") || c.name.StartsWith("Pendant"))) { c.gameObject.SetActive(false); hidden.Add(c.gameObject); }
   try { CaptureSized(name, w, h, target, size); } finally { foreach (var g in hidden) if (g) g.SetActive(true); }
  }

  void ShootFloor(string name) {
   var inside = CheckoutInterior.Active; var floor = inside.FloorRect;
   float size = Mathf.Max(floor.width, floor.height) * (CheckoutStall.Small ? 1.25f : 1.05f) + 1;
   TierShot(name, 2048, 1152, new Vector3(floor.center.x, CheckoutInterior.FloorHere, floor.center.y), size);
  }

  // ------------------------------------------------------------------ checkout tiers
  IEnumerator TierCheckout() {
   int shots = 0; var fails = new List<string>();
   foreach (var (stage, tiers) in new[] { ("spati", new[] { 1, 2 }), ("minimercado", new[] { 2, 3 }), ("mercadinho", new[] { 3 }), ("supermercado", new[] { 4 }) }) {
    foreach (var t in tiers) {
     tierCheckout = "checkout_T" + t;
     yield return ShowTier(stage, System.Array.IndexOf(EraIds, stage), 2, null);
     var inside = CheckoutInterior.Active; var c = inside.Get("checkout:main");
     string shown = c != null ? c.template : CheckoutStall.ShopInside && !CheckoutStall.PlacedCounter ? "(fixed counter)" : "none";
     Note($"TIERS checkout {stage} T{t}: shows {shown}" + (c != null && c.wantsGrow ? " (wants " + c.desired + ")" : ""));
     if (c == null && CheckoutStall.PlacedCounter) fails.Add(stage + " T" + t + " no checkout");
     ShootFloor($"ft_checkout_{stage}_T{t}"); shots++;
    }
   }
   Note($"RESULT tiers checkout: {(fails.Count == 0 ? "PASS" : "FAIL")} {shots} shots" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // ------------------------------------------------------------------ cold room per expansion
  IEnumerator TierCold() {
   var stages = new[] { ("mesinha", 1), ("conteiner", 1), ("spati", 1), ("quitanda", 1), ("minimercado", 2), ("mercadinho", 2), ("supermercado", 2), ("supermercado", 3), ("hipermercado", 4), ("rede", 4) };
   var bad = new List<string>();
   foreach (var (stage, t) in stages) {
    tierPatching = true; tierCold = "coldroom_T" + t;
    yield return GoToStage(stage);
    yield return Wait(1);
    var root = CheckoutColdRoom.Root;
    Note($"TIERS cold {stage} T{t}: {(root ? root.name + " at " + root.position.ToString("0.0") + " yaw " + root.eulerAngles.y.ToString("0") : "not shown")} · {CheckoutColdRoom.Side}");
    if (t >= 2 && !root && stage != "mercadinho") bad.Add(stage); // the mercadinho has no depot and no free owned side: in the stockroom by design
    TierShot($"ft_cold_{stage}_T{t}_map", 2048, 1152, null, 0);
    if (root) { var b = CheckoutColdRoom.Bounds; TierShot($"ft_cold_{stage}_T{t}_close", 2048, 1152, new Vector3(b.center.x, .5f, b.center.z), Mathf.Max(b.size.x, b.size.z) * 3.2f + 6); }
   }
   Note($"RESULT tiers coldroom: {(bad.Count == 0 ? "PASS" : "FAIL")} placed in every expansion from the minimercado" + (bad.Count > 0 ? "; no room at " + string.Join(", ", bad) : ""));
  }

  // ------------------------------------------------------------------ room for a cold-room wing (depot / mercadinho)
  // Logs the depot's pose, its mesh pivot and local bounds, the free strips around it inside lot C2 (FixedFree sampled
  // on a 0.25 m grid, the truck bay, the clerks' corridor and the storage door as blockers), and for the mercadinho what
  // stands behind the shop. Shots Logs/ft_depot_top.jpg, ft_mercadinho_back.jpg.
  IEnumerator TierDepotProbe() {
   yield return GoToStage("supermercado"); yield return Wait(2);
   var world = GameObject.Find("Supermarket World")?.transform; var layout = FindAnyObjectByType<CheckoutMarketLayout>();
   var depot = world ? world.Find("Warehouse") : null;
   if (!depot || !layout) { Note("DEPOT none"); yield break; }
   Note($"DEPOT root pos {depot.position:F3} euler {depot.eulerAngles:F1} scale {depot.lossyScale:F3} beside={CheckoutMarketLayout.StorageBeside}");
   Bounds wb = new Bounds(depot.position, Vector3.zero); bool any = false;
   foreach (var mf in depot.GetComponentsInChildren<MeshFilter>(false)) {
    var r = mf.GetComponent<MeshRenderer>(); if (!mf.sharedMesh || !r || !r.enabled || r.forceRenderingOff) continue;
    if (!any) { wb = r.bounds; any = true; } else wb.Encapsulate(r.bounds);
    if (mf.sharedMesh.name.Contains("Depot") || mf.sharedMesh.vertexCount > 3000)
     Note($"DEPOT mesh '{mf.sharedMesh.name}' on '{mf.name}' pivot {mf.transform.position:F3} euler {mf.transform.eulerAngles:F1} scale {mf.transform.lossyScale:F3} local bounds {mf.sharedMesh.bounds.min:F3}..{mf.sharedMesh.bounds.max:F3} world {r.bounds.min:F3}..{r.bounds.max:F3}");
   }
   Note($"DEPOT world bounds {wb.min:F3}..{wb.max:F3} (height {wb.size.y:F2})");
   Note($"DEPOT storage door {layout.StorageDoor:F2} facing {layout.StorageFacing:F2}; truck bay x {CheckoutDeliveryTrucks.DepotRearX - .3f:F2}..{CheckoutDeliveryTrucks.DepotRearX + 6.2f:F2} z {CheckoutDeliveryTrucks.DepotTruckZ - 1.45f:F2}..{CheckoutDeliveryTrucks.DepotTruckZ + 1.45f:F2}, drive z {CheckoutDeliveryTrucks.DepotDriveZ0:F2}..{CheckoutDeliveryTrucks.DepotDriveZ1:F2}; block {CheckoutInterior.BlockRect}");
   foreach (var lot in bridge.State.era?.lotRects ?? System.Array.Empty<LotRect>()) Note($"DEPOT lot {lot.id} {lot.status} occ={lot.occupied} x {lot.x0}..{lot.x1} z {lot.z0}..{lot.z1}");
   // Free cells (0.25 m) of lot C2 around the depot: '#' built, 'D' depot, '.' free.
   var c2 = Rect.MinMaxRect(5.75f, 4.75f, 17.25f, 18f); var lines = new List<string>();
   for (float z = c2.yMax - .125f; z > c2.yMin; z -= .25f) {
    var sb = new System.Text.StringBuilder();
    for (float x = c2.xMin + .125f; x < c2.xMax; x += .25f) {
     bool inDepot = x > wb.min.x && x < wb.max.x && z > wb.min.z && z < wb.max.z;
     sb.Append(inDepot ? 'D' : CheckoutBlockPaths.FixedFree(new Vector3(x, 0, z)) ? '.' : '#');
    }
    lines.Add($"{z,6:F2} {sb}");
   }
   File.WriteAllLines("Logs/ft_depot_grid.txt", lines);
   // Free strip widths from each depot wall to the first obstacle / lot edge, sampled every 0.5 m along the wall.
   float Run(Vector3 from, Vector3 dir) { float d = 0; for (; d < 8f; d += .1f) { var p = from + dir * (d + .05f); if (!c2.Contains(new Vector2(p.x, p.z)) || !CheckoutBlockPaths.FixedFree(p)) break; } return d; }
   foreach (var (side, dir) in new[] { ("north", Vector3.forward), ("east", Vector3.right), ("south", Vector3.back), ("west", Vector3.left) }) {
    var spans = new List<string>();
    bool ns = side == "north" || side == "south";
    for (float t = ns ? wb.min.x + .25f : wb.min.z + .25f; t < (ns ? wb.max.x : wb.max.z); t += .5f) {
     var start = side == "north" ? new Vector3(t, 0, wb.max.z + .9f) : side == "south" ? new Vector3(t, 0, wb.min.z - .9f) : side == "east" ? new Vector3(wb.max.x + .9f, 0, t) : new Vector3(wb.min.x - .9f, 0, t);
     spans.Add($"{t:F2}:{Run(start, dir) + .9f:F1}");
    }
    Note($"DEPOT free from the {side} wall (m, first 0.9 m is the paths margin): " + string.Join(" ", spans));
   }
   TierShot("ft_depot_top", 2048, 1152, new Vector3(wb.center.x, 1, wb.center.z), 24);
   // The mercadinho: what stands behind the shop (shell, stockroom, anything on its lots).
   yield return GoToStage("mercadinho"); yield return Wait(2);
   var shell = FindAnyObjectByType<CheckoutMarketShell>();
   Note($"MERCADINHO shell footprint {(shell ? shell.Footprint.ToString("F2") : "-")} clear rect {CheckoutMarketShell.ClearRect(layout.State)}");
   foreach (var lot in bridge.State.era?.lotRects ?? System.Array.Empty<LotRect>()) if (lot.status == "seu" || lot.occupied) Note($"MERCADINHO own lot {lot.id} x {lot.x0}..{lot.x1} z {lot.z0}..{lot.z1}");
   foreach (Transform t in world) {
    if (!t.gameObject.activeInHierarchy) continue;
    var rs = t.GetComponentsInChildren<Renderer>(false); if (rs.Length == 0) continue;
    var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
    if (b.max.z > 3f && b.min.z < 12f && b.max.x > -17.5f && b.min.x < 6f && b.size.y > .5f) Note($"MERCADINHO behind: '{t.name}' {b.min:F1}..{b.max:F1}");
   }
   var lo = CheckoutMarketLayout.Project(new Vector3(-9.4f, 0, 7.4f), layout.State);
   TierShot("ft_mercadinho_back", 2048, 1152, new Vector3(lo.x + 10, 1, lo.z), 26);
   Note("RESULT tiers depot: PASS probe written (Logs/ft_depot_grid.txt)");
  }

  // ------------------------------------------------------------------ the three cart stations, customers using them
  IEnumerator TierCarts() {
   tierOwned = new[] { new DecorOwned { type = "basket-station", count = 1 }, new DecorOwned { type = "cart-corral", count = 1 }, new DecorOwned { type = "big-cart-corral", count = 1 } };
   yield return ShowTier("supermercado", 8, 3, (items, floor) => {
    // the stations along the front wall, past the entrance (never in the way in)
    var inside = CheckoutInterior.Active; var layout = inside.LayoutState;
    var door = FindAnyObjectByType<CheckoutMap>()?.Entrance ?? new Vector3(floor.xMin, 0, floor.yMin);
    float x = Mathf.Max(floor.xMin + .4f, door.x + 2.6f);
    foreach (var (id, type) in new[] { ("decor-901", "basket-station"), ("decor-902", "cart-corral"), ("decor-903", "big-cart-corral") }) {
     var piece = inside.TemplateObject(inside.DecorTemplate(type))?.GetComponent<CheckoutInteriorPiece>(); if (!piece) { Note("TIERS missing station " + type); continue; }
     var w = new Vector3(x - piece.min.x, 0, floor.yMin + .9f - piece.min.y);
     var b = CheckoutMarketLayout.Unproject(w, layout); items.Add(new InteriorItem { id = id, type = type, x = b.x, z = b.z, rot = 0 });
     x += piece.max.x - piece.min.x + .35f;
    }
   });
   // Open for customers (as eventscrowd): at the end of a day they would turn back at the door.
   if (!bridge.State.isOpen) {
    Hud("claimDayResult", "[]"); yield return Wait(1);
    Hud("startDay", "[\"livre\"]"); for (float t = 0; t < 4 && !bridge.State.isOpen; t += .5f) yield return Wait(.5f);
    if (!bridge.State.isOpen) { Hud("setMarketOpen", "[true]"); for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return Wait(.5f); }
    Note("TIERS carts: market open " + bridge.State.isOpen);
   }
   tierOpen = true; yield return Reapply();
   var inside2 = CheckoutInterior.Active;
   var stations = inside2.items.Values.Where(i => i.root && (i.type == "basket-station" || i.type == "cart-corral" || i.type == "big-cart-corral")).ToList();
   Note("TIERS stations: " + string.Join(", ", stations.Select(i => i.type + "=" + i.template)));
   ShootFloor("ft_carts_close");
   // QA customers: one of each carrier, twice.
   var shelfIds = (bridge.State.shelves ?? System.Array.Empty<Shelf>()).Where(s => s.unlocked).Select(s => s.id).ToList();
   var carriers = new[] { "hands", "basket", "cart", "bigCart", "basket", "cart", "bigCart", "hands" };
   var walkers = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).Where(w => w && !w.gameObject.activeSelf && !w.Reserved).Take(carriers.Length).ToList();
   for (int i = 0; i < walkers.Count; i++) {
    var buy = shelfIds.Take(2 + i % 3).Select(id => new Purchase { shelfId = id, productId = 1, quantity = 1 }).ToArray();
    walkers[i].Begin(new Customer { id = "qa-cart-" + i, name = "QA", spent = 20, carrier = carriers[i], purchases = buy });
    yield return Wait(1.2f);
   }
   // They walk in from the street: shoot while they shop.
   var seen = new HashSet<string>();
   // (walk-ins appear 25-45 m away, CheckoutWalker.ArrivalSpot: half a minute before they are in)
   for (int k = 0; k < 5; k++) {
    yield return Wait(k == 0 ? 30 : 8);
    foreach (var wk in walkers.Where(x => x && x.gameObject.activeInHierarchy)) {
     var rig = wk.GetComponent<CheckoutShopperRig>(); if (!rig) continue;
     var inFloor = CheckoutInterior.Active.FloorRect.Contains(new Vector2(wk.transform.position.x, wk.transform.position.z));
     seen.Add(rig.carrier + (rig.cart ? "/cart" : rig.carrier == "hands" ? "/hands" : "/basket") + (inFloor ? " (inside)" : ""));
    }
    if (k == 2) {
     var live = walkers.Where(x => x && x.gameObject.activeInHierarchy).ToList();
     if (live.Count > 0) { var c = live.Aggregate(Vector3.zero, (a, x) => a + x.transform.position) / live.Count; TierShot("ft_carts_shoppers_close", 2048, 1152, c + Vector3.up * .8f, 11); }
    }
    if (k == 2) Note("TIERS QA shoppers: " + string.Join(", ", walkers.Where(x => x).Select(x => (x.gameObject.activeInHierarchy ? "phase " + x.VisitPhase : "gone") + " @" + x.transform.position.ToString("0.0"))));
    ShootFloor("ft_carts_shoppers" + (k + 1));
   }
   Note("TIERS shoppers seen: " + string.Join(", ", seen));
   bool ok = stations.Count == 3 && stations.All(s => s.template.StartsWith("carts_T")) && seen.Any(x => x.StartsWith("bigCart/cart"));
   Note($"RESULT tiers carts: {(ok ? "PASS" : "FAIL")} {stations.Count}/3 stations with the new models, {walkers.Count} QA shoppers ({string.Join(",", carriers.Take(walkers.Count))})");
  }

  // ------------------------------------------------------------------ ATM, gumball, claw machine tiers
  IEnumerator TierDecor() {
   var sets = new[] { ("atm", 3), ("gumball", 2), ("claw-machine", 3) };
   tierOwned = sets.Select(s => new DecorOwned { type = s.Item1, count = 3 }).ToArray();
   int found = 0;
   for (int round = 1; round <= 3; round++) {
    tierDecor = sets.Select(s => new DecorTier { type = s.Item1, tier = Mathf.Min(round, s.Item2), template = (s.Item1 == "claw-machine" ? "claw" : s.Item1) + "_T" + Mathf.Min(round, s.Item2) }).ToArray();
    int r = round;
    yield return ShowTier("supermercado", 8, 2, (items, floor) => {
     var inside = CheckoutInterior.Active; var layout = inside.LayoutState; float x = floor.xMin + .5f; int n = 0;
     foreach (var (type, top) in sets) {
      var model = (type == "claw-machine" ? "claw" : type) + "_T" + Mathf.Min(r, top); // this round's model (the snapshot may not carry it yet)
      var piece = inside.TemplateObject(model)?.GetComponent<CheckoutInteriorPiece>(); if (!piece) continue;
      var w = new Vector3(x - piece.min.x, 0, floor.yMin + 1.2f - piece.min.y);
      var b = CheckoutMarketLayout.Unproject(w, layout); items.Add(new InteriorItem { id = "decor-95" + (n++), type = type, x = b.x, z = b.z, rot = 0 });
      x += piece.max.x - piece.min.x + .8f;
     }
    });
    var shown = CheckoutInterior.Active.items.Values.Where(i => i.root && sets.Any(s => s.Item1 == i.type)).Select(i => i.type + "=" + i.template + (i.wantsGrow ? "(wants " + i.desired + ")" : "")).ToList();
    found += shown.Count;
    Note($"TIERS decor round {r}: " + string.Join(", ", shown));
    ShootFloor($"ft_decor_T{r}");
   }
   Note($"RESULT tiers decor: {(found >= 9 ? "PASS" : "FAIL")} {found}/9 pieces shown over three rounds");
  }

  // ------------------------------------------------------------------ the special sectors (T1..T3) and their screens
  void TierLang(string l) { CheckoutI18n.SetLanguage(l); CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"" + l + "\"}"); }

  void RefreshScreens() { foreach (var sc in FindObjectsByType<CheckoutSectorScreens>(FindObjectsSortMode.None)) sc.RefreshNow(); }

  IEnumerator TierSectors() {
   int shots = 0, shrunk = 0; var fails = new List<string>();
   var before = CheckoutI18n.Language;
   for (int t = 1; t <= 3; t++) {
    tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, "hipermercado"); roomExtras = false; roomKeepInterior = true;
    yield return GoToStage("hipermercado");
    yield return Reapply();
    var inside = CheckoutInterior.Active;
    var sectors = inside.items.Values.Where(i => i.root && i.type == "sector").OrderBy(i => i.id).ToList();
    shrunk += sectors.Count(i => i.wantsGrow);
    Note($"TIERS sectors T{t}: {sectors.Count} [{string.Join(", ", sectors.Select(i => i.id.Substring(7) + "=" + i.template + (i.wantsGrow ? "(wants " + i.desired + ")" : "")))}]");
    if (sectors.Count < 7) fails.Add($"T{t}: {sectors.Count}/7 sectors");
    RefreshScreens(); yield return null;
    ShootFloor($"ft_sectors_T{t}"); shots++;
    foreach (var it in sectors) {
     var sc = it.root.GetComponent<CheckoutSectorScreens>();
     if (!sc) fails.Add(it.template + " has no screens");
     TierShot($"ft_sector_{it.id.Substring(7)}_T{t}", 1600, 1000, it.root.position + Vector3.up * 1.4f, 6.5f); shots++;
    }
    if (t != 2) continue;
    // The price boards in pt-BR and another language (numbers and the name board follow it): the bakery at T2.
    var any = sectors.FirstOrDefault(i => i.id == "sector:padaria") ?? sectors.FirstOrDefault();
    foreach (var lang in new[] { "pt", "en", "de" }) {
     TierLang(lang); yield return Wait(1.5f); RefreshScreens(); yield return null;
     if (any != null) { TierShot("ft_sector_board_" + lang, 1600, 1000, any.root.position + Vector3.up * 2.1f, 3.4f); shots++; }
    }
    TierLang(before); yield return Wait(1f);
   }
   Note($"RESULT tiers sectors: {(fails.Count == 0 ? "PASS" : "FAIL")} {shots} shots, {shrunk} kept a smaller tier for lack of room" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // The real store: a built bakery evolves from T1 to T2 (coins), the model follows.
  IEnumerator TierSectorUpgrade() {
   var fails = new List<string>();
   Sector Bakery() => bridge.State.sectors?.FirstOrDefault(x => x.id == "padaria");
   Hud("setMarketLevel", "[60]");
   Hud("grantCurrencyPurchase", "[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-sector-" + System.DateTime.Now.Ticks + "\"}]");
   yield return GoToStage("supermercado");
   if (Bakery() != null && !Bakery().unlocked) {
    // as a player: buy it, place it (it waits in the build-mode inventory), save the layout, the works run
    Hud("buildSector", "[\"padaria\",\"coins\"]"); yield return Wait(2.5f);
    var inside = CheckoutInterior.Active; var floor = inside.FloorRect;
    // (a layout saved earlier in the run may already stand it where it goes: then nothing to place)
    CheckoutInterior.Item placed = inside.waiting.ContainsKey("sector:padaria") ? null : inside.Get("sector:padaria");
    for (float pz = floor.center.y; placed == null && pz > floor.yMin + 1.5f; pz -= 1.5f)
     for (float px = floor.xMin + 2.5f; placed == null && px < floor.xMax - 2.5f; px += 2f)
      placed = inside.PlaceWaiting("sector:padaria", new Vector3(px, 0, pz));
    Note("TIERS bakery placed: " + (placed != null ? placed.template + " at " + placed.root.position.ToString("0.0") : "no") + $" (waiting {inside.waiting.ContainsKey("sector:padaria")}, standing {inside.Get("sector:padaria") != null}, building {Bakery()?.building}, coins {bridge.State.coins})");
    if (placed != null) { inside.MarkPending(); FindAnyObjectByType<CheckoutMap>().SaveInterior(); yield return Wait(2.5f); }
    Hud("devFinishInteriorConstructions", "[]"); yield return Wait(3f);
   }
   var b = Bakery(); Note($"TIERS bakery: unlocked {b?.unlocked} tier {b?.tier} {b?.tierTemplate} board {b?.board?.Length}");
   if (b == null || !b.unlocked) { fails.Add("the bakery is not built"); }
   else {
    int from = b.tier;
    var it = CheckoutInterior.Active.Get("sector:padaria");
    if (it != null) { RefreshScreens(); TierShot($"ft_sector_upgrade_before_T{from}", 1600, 1000, it.root.position + Vector3.up * 1.4f, 6.5f); }
    Hud("upgradeSectorTier", "[\"padaria\",\"coins\"]"); yield return Wait(1.5f);
    // (the evolution crew takes 30 min / 2 h: finished here, then its reveal and card seen)
    Hud("devFinishEvolutions", "[]"); yield return Wait(2f); yield return ClearReveals();
    b = Bakery(); it = CheckoutInterior.Active.Get("sector:padaria");
    Note($"TIERS bakery after: tier {b?.tier} {b?.tierTemplate}; Unity shows {it?.template}");
    if (b == null || b.tier != Mathf.Min(3, from + 1)) fails.Add($"tier {b?.tier} after evolving from {from}");
    if (it == null || (it.template != b.tierTemplate && !it.wantsGrow)) fails.Add("Unity shows " + it?.template);
    if (it != null) { RefreshScreens(); TierShot($"ft_sector_upgrade_after_T{b.tier}", 1600, 1000, it.root.position + Vector3.up * 1.4f, 6.5f); }
   }
   Note($"RESULT tiers upgrade: {(fails.Count == 0 ? "PASS" : "FAIL")}" + (fails.Count > 0 ? ": " + string.Join(" | ", fails) : ""));
  }

  // The shop and the panels with the evolutions (full screen, HUD included): Logs/ft_ui_*.jpg.
  IEnumerator TierUi() {
   var host = CheckoutDesktopHost.Active; if (!host) { Note("no desktop host"); yield break; }
   // in the Supermercado, with the bakery built (the "Evoluir" of a sector), no popup over the pages
   yield return GoToStage("supermercado");
   if (bridge.State.level < 40) {
    Hud("setMarketLevel", "[45]");
    Hud("grantCurrencyPurchase", "[{\"coins\":2000000,\"diamonds\":500,\"transactionId\":\"qa-ui-" + System.DateTime.Now.Ticks + "\"}]");
    yield return Wait(1.5f);
   }
   // the day's results reviewed (the "Fim do dia" tip goes), no popup over the pages
   Hud("claimDayResult", "[]"); yield return Wait(1f);
   Hud("dismissLevelUp", "[]"); yield return Wait(1f);
   for (int i = 0; i < 3; i++) { Hud("dismissOnboardingTip", "[]"); yield return Wait(.7f); }
   foreach (var route in new[] { "loja:moveis:caixas", "loja:moveis:camara", "loja:moveis:prateleiras", "loja:decoracao:dentro", "shelf:produce", "shelf:dairy", "sector:padaria" }) {
    var hudUi = FindAnyObjectByType<CheckoutDesktopHUD>();
    for (int i = 0; i < 4 && hudUi && (hudUi.LevelUpOpen || hudUi.ConquestOpen); i++) { hudUi.QaCloseCelebrations(); yield return Wait(.8f); }
    // (no delivery-app offer toast over the page in Lucas's pictures: the QA copy turns the offers down)
    foreach (var order in bridge.State.delivery?.orders ?? System.Array.Empty<DeliveryOrder>()) if (order != null && order.status == "oferta") Hud("declineDeliveryOrder", "[\"" + order.id + "\"]");
    host.Route("!" + route); yield return Wait(2);
    for (int i = 0; i < 4 && hudUi && (hudUi.LevelUpOpen || hudUi.ConquestOpen); i++) { hudUi.QaCloseCelebrations(); yield return Wait(.8f); }
    yield return new WaitForEndOfFrame();
    var tex = ScreenCapture.CaptureScreenshotAsTexture();
    int w = tex.width, h = tex.height; float k = Mathf.Min(1, 2048f / Mathf.Max(w, h));
    var rt = RenderTexture.GetTemporary((int)(w * k), (int)(h * k)); Graphics.Blit(tex, rt);
    var prev = RenderTexture.active; RenderTexture.active = rt;
    var small = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false); small.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); small.Apply();
    RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
    File.WriteAllBytes("Logs/ft_ui_" + route.Replace(':', '_') + ".jpg", small.EncodeToJPG(85)); Destroy(small); Destroy(tex);
    Note("TIERS ui shot " + route);
   }
   host.Route("");
   Note("RESULT tiers ui: PASS shots");
  }

  // What stands over the shop floor that is not a placed piece (to tell decorations from markers): renderers whose
  // bounds lie over the floor, grouped by their path. Logs/ft_floor_probe.txt.
  IEnumerator TierFloorProbe() {
   yield return GoToStage("supermercado");
   var inside = CheckoutInterior.Active; var floor = inside.FloorRect;
   var pieces = new HashSet<Transform>(inside.items.Values.Where(i => i.root).Select(i => i.root));
   string PathOf(Transform t) { var p = t.name; for (var q = t.parent; q && p.Length < 160; q = q.parent) p = q.name + "/" + p; return p; }
   bool InPiece(Transform t) { for (; t; t = t.parent) if (pieces.Contains(t)) return true; return false; }
   var groups = new Dictionary<string, int>();
   foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)) {
    if (!r.enabled || !r.gameObject.activeInHierarchy || InPiece(r.transform)) continue;
    var b = r.bounds; if (b.size.x > 6 || b.size.z > 6) continue; // walls, floor, the shell
    if (!floor.Contains(new Vector2(b.center.x, b.center.z)) || b.center.y > 5) continue;
    var path = PathOf(r.transform); var key = System.Text.RegularExpressions.Regex.Replace(path, @"\d+", "#") + " [" + r.GetType().Name + ", " + (r.sharedMaterial ? r.sharedMaterial.name : "-") + ", y " + b.center.y.ToString("0.0") + "]";
    groups.TryGetValue(key, out var n); groups[key] = n + 1;
   }
   File.WriteAllLines("Logs/ft_floor_probe.txt", groups.OrderByDescending(g => g.Value).Select(g => g.Value + " x " + g.Key));
   Note($"RESULT tiers floorprobe: PASS {groups.Count} groups (Logs/ft_floor_probe.txt)");
  }

  // Can shoppers get into the market building? NavMesh paths from the sidewalk to the entrance and on to every shelf's
  // approach, and the solid boxes the navigation is built with near the way in. Logs/ft_nav_probe.txt.
  // The same views of the Mercadinho and the Supermercado (Logs/ft_markers_<stage>_floor|close.jpg), to compare what floats
  // over the furniture before and after a change; counts the "Status …" objects the map shows (the old stock pills).
  IEnumerator TierMarkerShots() {
   foreach (var stage in new[] { "mercadinho", "supermercado" }) {
    yield return ShowTier(stage, System.Array.IndexOf(EraIds, stage), 2, null); yield return Wait(2);
    var map = FindAnyObjectByType<CheckoutMap>(); int shown = 0;
    if (map) foreach (Transform t in map.transform) if (t.name.StartsWith("Status ") && t.gameObject.activeInHierarchy) shown++;
    var inside = CheckoutInterior.Active;
    Note($"TIERS markers {stage}: {shown} status pills shown");
    ShootFloor($"ft_markers_{stage}_floor");
    var shelf = inside ? inside.items.Values.Where(i => i.root && i.type == "shelf").OrderBy(i => i.id).FirstOrDefault() : null;
    if (shelf != null) TierShot($"ft_markers_{stage}_close", 2048, 1152, shelf.root.position + Vector3.up * 1.2f, 6.5f);
    TierReset();
   }
   Note("RESULT tiers markers: PASS shots");
  }

  // ------------------------------------------------------------------ sector walls: flush against the shop's walls
  // Every sector at T1–T3 in each shop with sectors, pushed against each wall in each of the four turns the build mode
  // allows, the way a drag lands it (CheckoutInterior.Snap): how far its wall-side face stays from the wall. Logs one
  // FLUSH line per try and Logs/ft_flush_audit.txt. (Everything else stands aside meanwhile: only the walls count.)
  IEnumerator TierFlushAudit() {
   var lines = new List<string>(); int tries = 0, flushBack = 0, backTries = 0, overlaps = 0; float worstBack = 0;
   foreach (var stage in new[] { "mercadinho", "supermercado", "hipermercado" }) {
    int era = System.Array.IndexOf(EraIds, stage);
    for (int t = 1; t <= 3; t++) {
     tierPatching = true; tierSector = t; roomEra = era; roomExtras = false; roomKeepInterior = true;
     yield return GoToStage(stage); yield return Reapply();
     var inside = CheckoutInterior.Active; if (!inside) continue;
     var floor = inside.FloorRect; var zone = inside.CheckoutZone;
     var sectors = inside.items.Values.Where(i => i.root && i.type == "sector").OrderBy(i => i.id).ToList();
     lines.Add($"== {stage} T{t}: floor {floor} checkout area from x {zone.xMin:0.00}; {sectors.Count} sectors");
     inside.editing = true;
     var others = inside.items.Values.Where(i => i.root && !i.ghost).ToList();
     foreach (var it in sectors) {
      var keepPos = it.root.position; float keepRot = it.rot;
      foreach (var o in others) if (o != it) o.ghost = true;
      var p0 = it.piece;
      lines.Add($"  {it.id} {it.template}{(it.wantsGrow ? " (wants " + it.desired + ")" : "")}: piece x {p0.min.x:0.000}..{p0.max.x:0.000} z {p0.min.y:0.000}..{p0.max.y:0.000}");
      foreach (var wall in new[] { "W", "R", "F", "E" }) {
       foreach (var rot in new[] { 0f, 90f, 180f, 270f }) foreach (var off in new[] { .1f, .24f }) {
        var f = inside.FootprintAt(it, keepPos, rot);
        float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
        var offset = new Vector2(keepPos.x, keepPos.z) - f.c;
        float midX = floor.xMin + (zone.xMin - floor.xMin) * .3f;
        Vector2 c = wall == "W" ? new Vector2(floor.xMin + ex + off, floor.center.y) : wall == "E" ? new Vector2(floor.xMax - ex - off, floor.center.y)
         : wall == "R" ? new Vector2(midX, floor.yMax - ez - off) : new Vector2(midX, floor.yMin + ez + off);
        var desired = new Vector3(c.x + offset.x, keepPos.y, c.y + offset.y);
        var p = inside.Snap(it, desired, rot, desired);
        it.rot = rot; inside.MoveTo(it, p);
        bool fits = inside.Fits(it, it.root.position, rot, out var why);
        var fp = inside.FootprintOf(it);
        float fex = fp.hx * Mathf.Abs(fp.ax.x) + fp.hz * Mathf.Abs(fp.az.x), fez = fp.hx * Mathf.Abs(fp.ax.y) + fp.hz * Mathf.Abs(fp.az.y);
        var rs = it.root.GetComponentsInChildren<Renderer>(); var mb = rs[0].bounds; foreach (var r in rs) mb.Encapsulate(r.bounds);
        float edge, meshEdge, floorEdge; // along the wall's normal, into the room positive
        if (wall == "W") { edge = fp.c.x - fex; meshEdge = mb.min.x; floorEdge = floor.xMin; }
        else if (wall == "E") { edge = -(fp.c.x + fex); meshEdge = -mb.max.x; floorEdge = -floor.xMax; }
        else if (wall == "R") { edge = -(fp.c.y + fez); meshEdge = -mb.max.z; floorEdge = -floor.yMax; }
        else { edge = fp.c.y - fez; meshEdge = mb.min.z; floorEdge = floor.yMin; }
        // which side of the sector faces that wall (its back is local +Z)
        var toWall = wall == "W" ? Vector3.left : wall == "E" ? Vector3.right : wall == "R" ? Vector3.forward : Vector3.back;
        var back = Quaternion.Euler(0, rot, 0) * Vector3.forward;
        string faces = Vector3.Dot(back, toWall) > .9f ? "back" : Vector3.Dot(back, toWall) < -.9f ? "front" : "side";
        float floorGap = edge - floorEdge, meshInset = meshEdge - edge, toPlaster = floorGap + meshInset + CheckoutMarketShellRail;
        // (overlap into the wall: the mesh past the rail's face)
        if (faces == "back" && fits && meshEdge < floorEdge - .005f) overlaps++;
        tries++;
        if (faces == "back") { backTries++; if (fits && floorGap < .005f) flushBack++; if (fits) worstBack = Mathf.Max(worstBack, floorGap + meshInset); }
        // (the back panel's rule, CheckoutInterior.BackAgainstWall, when the build has it)
        string panel = "";
        var against = typeof(CheckoutInterior).GetMethod("BackAgainstWall");
        if (against != null) { var args = new object[] { it, null }; bool hide = (bool)against.Invoke(inside, args); panel = $"; back panel {(hide ? "hidden" : "shown")} ({args[1]})"; }
        lines.Add($"FLUSH {stage} T{t} {it.id.Substring(7)} wall {wall} rot {rot:0} from {off * 100:0} cm ({faces}): fits={fits}{(fits ? "" : " (" + why + ")")} footprint-to-floor-edge {floorGap * 100:0.0} cm, mesh inset {meshInset * 100:0.0} cm, to the plaster {toPlaster * 100:0.0} cm{panel}");
       }
      }
      foreach (var o in others) o.ghost = false;
      it.rot = keepRot; inside.MoveTo(it, keepPos);
     }
     inside.editing = false; TierReset();
    }
   }
   File.WriteAllLines("Logs/ft_flush_audit.txt", lines);
   foreach (var l in lines.Where(x => x.StartsWith("FLUSH"))) Note(l);
   Note($"RESULT tiers flush: {flushBack}/{backTries} back-to-wall tries flush with the floor edge ({tries} tries in all); worst back gap to the rail face (floor edge) {worstBack * 100:0.0} cm; {overlaps} placed back-to-wall tries with mesh past the rail face (Logs/ft_flush_audit.txt)");
  }
  const float CheckoutMarketShellRail = .05f; // CheckoutMarketShell.Rail: the clear floor stops 5 cm inside the plaster

  // A sector dragged against the west wall (flush, panel hidden), standing free mid-floor (panel shown), in the
  // west/rear corner, and against the Mercadinho's rear wall before and after the shop grows into the Supermercado
  // (that wall goes away: the panel comes back). Logs/ft_walls_*.jpg and a WALLS line each.
  IEnumerator TierWallShots() {
   var fails = new List<string>();
   IEnumerator Put(string stage, int t, string id, string where, string shot) {
    var inside = CheckoutInterior.Active; var it = inside?.Get("sector:" + id); if (it == null) { fails.Add($"{stage}: no {id}"); yield break; }
    var floor = inside.FloorRect; var zone = inside.CheckoutZone;
    inside.editing = true;
    foreach (var o in inside.items.Values) if (o != it && o.root && o.type == "sector") o.ghost = false;
    float rot = where == "west" || where == "corner" ? 270 : where == "rear" ? 0 : 0;
    var f = inside.FootprintAt(it, it.root.position, rot);
    float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
    var offset = new Vector2(it.root.position.x, it.root.position.z) - f.c;
    float midX = floor.xMin + (zone.xMin - floor.xMin) * .35f;
    Vector2 c = where == "west" ? new Vector2(floor.xMin + ex + .1f, floor.center.y) : where == "corner" ? new Vector2(floor.xMin + ex + .1f, floor.yMax - ez - .1f)
     : where == "rear" ? new Vector2(midX, floor.yMax - ez - .1f) : new Vector2(midX, floor.center.y);
    // the others step aside from the spot (as a player would make room)
    var spot = Rect.MinMaxRect(c.x - ex - 1, c.y - ez - 1, c.x + ex + 1, c.y + ez + 1);
    foreach (var o in inside.items.Values) if (o != it && o.root) { var of = inside.FootprintOf(o); float oex = of.hx * Mathf.Abs(of.ax.x) + of.hz * Mathf.Abs(of.az.x), oez = of.hx * Mathf.Abs(of.ax.y) + of.hz * Mathf.Abs(of.az.y); if (Rect.MinMaxRect(of.c.x - oex, of.c.y - oez, of.c.x + oex, of.c.y + oez).Overlaps(spot)) o.ghost = true; }
    var desired = new Vector3(c.x + offset.x, it.root.position.y, c.y + offset.y);
    var p = inside.Snap(it, desired, rot, desired); it.rot = rot; inside.MoveTo(it, p);
    foreach (var o in inside.items.Values) if (o.ghost && o.root) o.root.gameObject.SetActive(false);
    yield return Wait(.6f); // (the panel check runs a few times a second)
    var against = typeof(CheckoutInterior).GetMethod("BackAgainstWall"); string state = "";
    if (against != null) { var args = new object[] { it, null }; state = ((bool)against.Invoke(inside, args) ? "panel hidden: " : "panel shown: ") + args[1]; }
    bool fits = inside.Fits(it, it.root.position, it.rot, out var why);
    inside.WallState.TryGetValue(it.id, out var shown);
    Note($"WALLS {stage} T{t} {id} {where}: {it.template} fits={fits}{(fits ? "" : " (" + why + ")")}; {state}; runtime: {shown}");
    RefreshScreens(); yield return null;
    TierShot(shot, 2048, 1152, it.root.position + Vector3.up * 1.3f, 7.5f);
    foreach (var o in inside.items.Values) if (o.ghost && o.root) { o.root.gameObject.SetActive(true); o.ghost = false; }
   }
   foreach (var (stage, t) in new[] { ("supermercado", 2), ("hipermercado", 3) }) {
    tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, stage); roomExtras = false; roomKeepInterior = true;
    yield return GoToStage(stage); yield return Reapply();
    foreach (var where in new[] { "west", "free", "corner", "rear" }) yield return Put(stage, t, "padaria", where, $"ft_walls_{stage}_T{t}_{where}");
    // a flush sector evolving in place: its back stays on the wall (CheckoutInterior.TierSpot)
    if (stage == "supermercado") {
     var inside2 = CheckoutInterior.Active; var bakery2 = inside2?.Get("sector:padaria");
     if (bakery2 != null) {
      string before = bakery2.template; inside2.editing = true;
      var aside = inside2.items.Values.Where(o => o != bakery2 && o.root && !o.ghost).ToList(); foreach (var o in aside) { o.ghost = true; o.root.gameObject.SetActive(false); }
      bakery2.desired = "sector-padaria_T3"; bool grew = inside2.TryGrow(bakery2); yield return Wait(.6f);
      var against2 = typeof(CheckoutInterior).GetMethod("BackAgainstWall"); string st2 = "";
      if (against2 != null) { var args = new object[] { bakery2, null }; st2 = ((bool)against2.Invoke(inside2, args) ? "panel hidden: " : "panel shown: ") + args[1]; }
      Note($"WALLS supermercado evolve at the rear wall: {before} -> {bakery2.template} (grew {grew}); {st2}");
      if (!grew) fails.Add("flush padaria did not grow in place");
      TierShot("ft_walls_supermercado_evolved_rear", 2048, 1152, bakery2.root.position + Vector3.up * 1.3f, 7.5f);
      foreach (var o in aside) { o.ghost = false; if (o.root) o.root.gameObject.SetActive(true); }
     }
    }
    var inside = CheckoutInterior.Active; if (inside) inside.editing = false; TierReset();
   }
   // the Mercadinho's rear wall, then the shop grows and that wall is gone
   tierPatching = true; tierSector = 1; roomEra = System.Array.IndexOf(EraIds, "mercadinho"); roomExtras = false; roomKeepInterior = true;
   yield return GoToStage("mercadinho"); yield return Reapply();
   yield return Put("mercadinho", 1, "padaria", "rear", "ft_walls_grow_1_mercadinho_rear");
   var keep = CheckoutInterior.Active; var bakery = keep?.Get("sector:padaria");
   if (keep != null && bakery != null) {
    keep.MarkPending(); FindAnyObjectByType<CheckoutMap>()?.SaveInterior(); keep.editing = false; yield return Wait(2);
    roomEra = System.Array.IndexOf(EraIds, "supermercado"); roomKeepInterior = true;
    yield return GoToStage("supermercado"); yield return Wait(2);
    var after = CheckoutInterior.Active?.Get("sector:padaria");
    var against = typeof(CheckoutInterior).GetMethod("BackAgainstWall"); string state = "";
    if (after != null && against != null) { var args = new object[] { after, null }; state = ((bool)against.Invoke(CheckoutInterior.Active, args) ? "panel hidden: " : "panel shown: ") + args[1]; }
    string shown2 = ""; CheckoutInterior.Active?.WallState.TryGetValue("sector:padaria", out shown2);
    Note($"WALLS grown to supermercado: padaria at {(after != null ? after.root.position.ToString("0.00") : "-")}; {state}; runtime: {shown2}");
    if (after != null) TierShot("ft_walls_grow_2_supermercado", 2048, 1152, after.root.position + Vector3.up * 1.3f, 7.5f);
   }
   TierReset();
   Note($"RESULT tiers wallshots: {(fails.Count == 0 ? "PASS" : "FAIL " + string.Join(" | ", fails))}");
  }

  // ------------------------------------------------------------------ all seven sectors flush against the market wall
  // Mercadinho, Supermercado and Hiper at T1–T3: the other furniture set aside, the sectors dragged one after the other
  // with their backs on the rear wall (west to east, up to the checkout area), then on the west wall (rear to front).
  // A floor shot each, a close-up of every sector at the Hiper. pt-BR. LINEUP lines: where each landed, its panel.
  IEnumerator TierLineup() {
   var fails = new List<string>(); int shots = 0;
   var before = CheckoutI18n.Language; TierLang("pt"); yield return Wait(1);
   foreach (var stage in new[] { "mercadinho", "supermercado", "hipermercado" })
    for (int t = 1; t <= 3; t++) {
     tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, stage); roomExtras = false; roomKeepInterior = true;
     yield return GoToStage(stage); yield return Reapply(); yield return Wait(1);
     var inside = CheckoutInterior.Active; if (!inside) continue;
     var floor = inside.FloorRect; var zone = inside.CheckoutZone;
     inside.editing = true;
     var aside = inside.items.Values.Where(i => i.root && !i.outside && !i.design && i.type != "sector" && i.type != "checkout" && i.type != "kiosk").ToList();
     foreach (var o in aside) { o.ghost = true; o.root.gameObject.SetActive(false); }
     var sectors = inside.items.Values.Where(i => i.root && i.type == "sector").OrderBy(i => i.id).ToList();
     foreach (var it in sectors) it.ghost = true; // (placed one by one below)
     float x = floor.xMin, z = floor.yMax; int placed = 0;
     foreach (var it in sectors) {
      bool done = false;
      for (int side = 0; side < 2 && !done; side++) {
       float rot = side == 0 ? 0 : 270;
       var f = inside.FootprintAt(it, it.root.position, rot);
       float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
       var offset = new Vector2(it.root.position.x, it.root.position.z) - f.c;
       Vector2 c = side == 0 ? new Vector2(x + ex + .05f, floor.yMax - ez - .1f) : new Vector2(floor.xMin + ex + .1f, z - ez - .05f);
       if (side == 0 && c.x + ex > zone.xMin - .05f) continue;
       if (side == 1 && c.y - ez < floor.yMin + 2.5f) continue;
       var desired = new Vector3(c.x + offset.x, it.root.position.y, c.y + offset.y);
       it.ghost = false;
       var p = inside.Snap(it, desired, rot, desired); it.rot = rot; inside.MoveTo(it, p);
       if (!inside.Fits(it, it.root.position, rot, out _)) { it.ghost = true; continue; }
       var fp = inside.FootprintOf(it);
       float fex = fp.hx * Mathf.Abs(fp.ax.x) + fp.hz * Mathf.Abs(fp.az.x), fez = fp.hx * Mathf.Abs(fp.ax.y) + fp.hz * Mathf.Abs(fp.az.y);
       if (side == 0) x = fp.c.x + fex; else z = fp.c.y - fez;
       if (side == 0) z = Mathf.Min(z, fp.c.y - fez); // the west run starts under the rear ones
       done = true; placed++;
      }
      // no room left on the tall walls: it stands free on the floor (still in the shot)
      if (!done) { it.ghost = false; it.rot = 0; inside.MoveTo(it, new Vector3(floor.center.x - 2, it.root.position.y, floor.center.y)); if (!inside.Settle(it)) it.root.gameObject.SetActive(false); }
     }
     yield return Wait(.6f); RefreshScreens(); yield return null;
     var states = sectors.Where(i => i.root && i.root.gameObject.activeSelf && !i.ghost).Select(i => { inside.WallState.TryGetValue(i.id, out var w); return $"{i.id.Substring(7)} {i.template} {w}"; }).ToList();
     Note($"LINEUP {stage} T{t}: {placed}/{sectors.Count} flush; " + string.Join(" | ", states));
     ShootFloor($"ft_lineup_{stage}_T{t}"); shots++;
     if (stage == "hipermercado")
      foreach (var it in sectors.Where(i => i.root && i.root.gameObject.activeSelf && !i.ghost)) { TierShot($"ft_lineup_hiper_{it.id.Substring(7)}_T{t}", 1600, 1000, it.root.position + Vector3.up * 1.3f, 6f); shots++; }
     if (stage == "hipermercado" && sectors.Count(i => i.root && i.root.gameObject.activeSelf) < 7) fails.Add($"hiper T{t}: not all 7 shown");
     foreach (var it in sectors) { it.ghost = false; if (it.root) it.root.gameObject.SetActive(true); }
     foreach (var o in aside) { o.ghost = false; if (o.root) o.root.gameObject.SetActive(true); }
     inside.editing = false; TierReset();
    }
   TierLang(before);
   Note($"RESULT tiers lineup: {(fails.Count == 0 ? "PASS" : "FAIL " + string.Join(" | ", fails))} {shots} shots");
  }

  // "Cores do mercado" on the sectors: the bakery standing free (its panel shown) next to the market wall, in each palette
  // (the panel's navy wainscot and gold rail/cap follow the wall; the cream body and the bakery's accents do not).
  IEnumerator TierSectorPaint() {
   var paint = CheckoutMarketPaint.Active; if (!paint) { Note("RESULT tiers paint: FAIL no CheckoutMarketPaint"); yield break; }
   tierPatching = true; tierSector = 2; roomEra = System.Array.IndexOf(EraIds, "supermercado"); roomExtras = false; roomKeepInterior = true;
   yield return GoToStage("supermercado"); yield return Reapply(); yield return Wait(1);
   var inside = CheckoutInterior.Active; var it = inside?.Get("sector:padaria"); if (it == null) { Note("RESULT tiers paint: FAIL no padaria"); yield break; }
   var floor = inside.FloorRect; inside.editing = true;
   // free, a little off the rear wall: the panel shows against the market wall behind it
   var f = inside.FootprintAt(it, it.root.position, 0); var offset = new Vector2(it.root.position.x, it.root.position.z) - f.c;
   var c = new Vector2(floor.xMin + f.hx + 1.5f, floor.yMax - f.hz - 1.25f);
   foreach (var o in inside.items.Values) if (o != it && o.root && !o.outside) { var of = inside.FootprintOf(o); if (Vector2.Distance(of.c, c) < 5) { o.ghost = true; o.root.gameObject.SetActive(false); } }
   var desired = new Vector3(c.x + offset.x, it.root.position.y, c.y + offset.y);
   it.rot = 0; inside.MoveTo(it, inside.Snap(it, desired, 0, desired)); yield return Wait(.6f);
   inside.WallState.TryGetValue(it.id, out var wall);
   RefreshScreens();
   int shots = 0;
   foreach (var (id, p, a) in ComparePalettes) {
    paint.Preview(p, a); yield return new WaitForSecondsRealtime(.6f);
    TierShot($"ft_paint_padaria_{id}", 1600, 1000, it.root.position + Vector3.up * 1.3f, 6f); shots++;
    if (id != "classico") Note($"PAINT {id}: {paint.PaintedRenderers} renderers, {paint.PaintedMaterials} painted materials");
   }
   paint.EndPreview(); yield return Wait(.5f);
   foreach (var o in inside.items.Values) if (o.ghost && o.root) { o.ghost = false; o.root.gameObject.SetActive(true); }
   inside.editing = false; TierReset();
   Note($"RESULT tiers paint: PASS {shots} shots ({wall})");
  }

  // ------------------------------------------------------------------ the seven sectors at T3: frame time (CheckoutPerfProbe)
  // The Hiper with all seven sectors at T3 in the game camera's view, the probe's 20 s capture at the iPhone quality;
  // the sectors' own triangles and renderers counted too. Run on main and on the branch to compare.
  IEnumerator TierSectorPerf() {
   tierPatching = true; tierSector = 3; roomEra = System.Array.IndexOf(EraIds, "hipermercado"); roomExtras = false; roomKeepInterior = true;
   yield return GoToStage("hipermercado"); yield return Reapply(); yield return Wait(3);
   var inside = CheckoutInterior.Active;
   var sectors = inside.items.Values.Where(i => i.root && i.type == "sector").ToList();
   int tris = 0, renderers = 0;
   foreach (var it in sectors) foreach (var mf in it.root.GetComponentsInChildren<MeshFilter>()) if (mf.sharedMesh && mf.gameObject.activeInHierarchy && !mf.GetComponent<TMPro.TMP_Text>()) { tris += (int)Enumerable.Range(0, mf.sharedMesh.subMeshCount).Sum(k => (long)mf.sharedMesh.GetIndexCount(k)) / 3; renderers++; }
   Note($"PERF sectors: {sectors.Count} ({string.Join(", ", sectors.Select(i => i.template))}), {tris} triangles in {renderers} renderers");
   var probe = FindAnyObjectByType<CheckoutPerfProbe>();
   var capture = typeof(CheckoutPerfProbe).GetMethod("Capture", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
   if (!probe || capture == null) { Note("RESULT tiers perf: FAIL no perf probe"); yield break; }
   var started = System.DateTime.Now;
   probe.StartCoroutine((IEnumerator)capture.Invoke(probe, null));
   yield return new WaitForSecondsRealtime(24);
   var file = Directory.GetFiles("Logs", "perf_*.txt").Where(f => File.GetLastWriteTime(f) >= started.AddSeconds(-1)).OrderBy(f => File.GetLastWriteTime(f)).LastOrDefault();
   if (file == null) { Note("RESULT tiers perf: FAIL no capture written"); yield break; }
   foreach (var l in File.ReadAllLines(file).Where(l => l.StartsWith("Frame time") || l.StartsWith("Main thread") || l.StartsWith("Batches") || l.StartsWith("SetPass") || l.StartsWith("Triangles") || l.StartsWith("Shadow casters") || l.StartsWith("Camera.Render") || l.StartsWith("Shadows"))) Note("PERF " + l);
   File.Copy(file, "Logs/ft_sector_perf.txt", true);
   Note($"RESULT tiers perf: PASS ({file})");
  }

  // ------------------------------------------------------------------ layouts saved with the old (shallower) sectors
  // The QA save's own layouts (Mercadinho, Supermercado, Hiper) at T1–T3, as the game loads them with the round-5
  // sectors: per sector what happened (fits as saved / grew toward the free side / kept the old footprint / smaller).
  IEnumerator TierMigrate() {
   var lines = new List<string>(); CheckoutInterior.MigrationCount.Clear(); int layouts = 0, smaller = 0, asSaved = 0, outside = 0;
   foreach (var stage in new[] { "mercadinho", "supermercado", "hipermercado" })
    for (int t = 1; t <= 3; t++) {
     tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, stage); roomExtras = false; roomKeepInterior = true;
     yield return GoToStage(stage); yield return Reapply(); yield return Wait(1);
     var inside = CheckoutInterior.Active; if (!inside) continue; layouts++;
     var floor = inside.FloorRect;
     foreach (var it in inside.items.Values.Where(i => i.root && i.type == "sector").OrderBy(i => i.id)) {
      bool fits = inside.Fits(it, it.root.position, it.rot, out var why);
      var f = inside.FootprintOf(it); bool inFloor = true;
      foreach (var c in new[] { new Vector2(-1, -1), new Vector2(1, -1), new Vector2(-1, 1), new Vector2(1, 1) }) { var p = f.c + f.ax * (f.hx * c.x) + f.az * (f.hz * c.y); if (!floor.Contains(p)) inFloor = false; }
      if (!inFloor) outside++;
      if (it.wantsGrow) smaller++;
      if (string.IsNullOrEmpty(it.migrated) && !it.wantsGrow) asSaved++;
      inside.WallState.TryGetValue(it.id, out var wall);
      lines.Add($"MIGRATE {stage} T{t} {it.id.Substring(7)}: {it.template}{(it.wantsGrow ? " (wants " + it.desired + ")" : "")}; {(string.IsNullOrEmpty(it.migrated) ? "as saved" : it.migrated)}; fits={fits}{(fits ? "" : " (" + why + ")")}; inside the floor {inFloor}; {wall}");
     }
     TierReset();
    }
   File.WriteAllLines("Logs/ft_migrate.txt", lines);
   foreach (var l in lines) Note(l);
   Note($"RESULT tiers migrate: {layouts} layouts; sectors as saved {asSaved}; {string.Join(", ", CheckoutInterior.MigrationCount.Select(p => p.Key + " " + p.Value))}; shown at a smaller tier {smaller}; outside the floor {outside} (Logs/ft_migrate.txt)");
  }

  // Old saves with a sector flush against a wall: every sector of the QA layouts (3 shops × T1–T3) put where the OLD
  // model stood with its back on the rear wall (turned 0) and on the west wall (turned 270), at its own x / z, the
  // rest of the layout as saved; only spots where the old footprint fitted count. Then the load rule (FitTiers) runs.
  IEnumerator TierMigrateFlush() {
   var lines = new List<string>(); var count = new Dictionary<string, int>(); int tries = 0, invalid = 0, flushAfter = 0;
   var fit = typeof(CheckoutInterior).GetMethod("FitTiers", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
   var old = new Dictionary<int, Vector2> { { 1, new Vector2(2.5f, 2f) }, { 2, new Vector2(3.25f, 2.5f) }, { 3, new Vector2(4f, 3.25f) } };
   foreach (var stage in new[] { "mercadinho", "supermercado", "hipermercado" })
    for (int t = 1; t <= 3; t++) {
     tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, stage); roomExtras = false; roomKeepInterior = true;
     yield return GoToStage(stage); yield return Reapply(); yield return Wait(1);
     var inside = CheckoutInterior.Active; if (!inside) continue;
     var floor = inside.FloorRect; inside.editing = true;
     foreach (var it in inside.items.Values.Where(i => i.root && i.type == "sector").OrderBy(i => i.id).ToList())
      foreach (var wall in new[] { "rear", "west" }) {
       string keepTemplate = it.template; var keepPos = it.root.position; float keepRot = it.rot;
       int tier = it.template[it.template.Length - 1] - '0'; var o = old[tier];
       float rot = wall == "rear" ? 0 : 270;
       var at = wall == "rear" ? new Vector3(keepPos.x, keepPos.y, floor.yMax - o.y * .5f) : new Vector3(floor.xMin + o.y * .5f, keepPos.y, keepPos.z);
       it.rot = rot; inside.MoveTo(it, at);
       // a valid old layout: the old footprint fitted there
       it.legacySize = o; it.legacyAt = it.root.position; it.legacyRot = rot; it.legacyPiece = it.piece; it.migrated = null;
       bool valid = inside.Fits(it, it.root.position, rot, out var whyOld);
       it.legacySize = Vector2.zero; it.legacyPiece = null;
       if (!valid) { invalid++; it.rot = keepRot; inside.MoveTo(it, keepPos); continue; }
       tries++;
       fit.Invoke(inside, null);
       var now = inside.items[it.id];
       string what = now.legacySize != Vector2.zero ? "kept the old footprint" : !string.IsNullOrEmpty(now.migrated) ? (now.migrated.Contains("forward") ? "grew toward the free side" : "slid back") : now.template != keepTemplate ? "smaller tier" : "fits as saved";
       count.TryGetValue(what, out var n); count[what] = n + 1;
       bool against = inside.BackAgainstWall(now, out var why);
       if (against) flushAfter++;
       lines.Add($"MIGRATEFLUSH {stage} T{t} {it.id.Substring(7)} {wall}: {keepTemplate} -> {now.template}; {what}{(string.IsNullOrEmpty(now.migrated) ? "" : " (" + now.migrated + ")")}; fits={inside.Fits(now, now.root.position, now.rot, out _)}; {why}");
       // back as it was
       now.legacySize = Vector2.zero; now.legacyPiece = null; now.migrated = null; now.rot = keepRot; inside.MoveTo(now, keepPos);
       if (now.template != keepTemplate) inside.TryGrow(now);
      }
     inside.editing = false; TierReset();
    }
   File.WriteAllLines("Logs/ft_migrate_flush.txt", lines);
   foreach (var l in lines) Note(l);
   Note($"RESULT tiers migrateflush: {tries} old flush placements ({invalid} spots where the old model did not fit either, skipped); {string.Join(", ", count.Select(p => p.Key + " " + p.Value))}; back still on the wall afterwards {flushAfter} (Logs/ft_migrate_flush.txt)");
  }

  // ------------------------------------------------------------------ sector staff: how wide, and do they clip
  // The workers of the staffed sectors (baker, butcher, fishmonger, cheesemaker): their mesh bounds standing and while
  // they work, their capsule / agent radius, and at each tier how much room they have at their spot behind the counter
  // (the largest upright capsule that fits there without touching the sector's mesh).
  IEnumerator TierStaffProbe() {
   var lines = new List<string>();
   var world = GameObject.Find("Supermarket World")?.transform;
   for (int t = 1; t <= 3; t++) {
    tierPatching = true; tierSector = t; roomEra = System.Array.IndexOf(EraIds, "hipermercado"); roomExtras = false; roomKeepInterior = true;
    yield return GoToStage("hipermercado"); yield return Reapply(); yield return Wait(1);
    var inside = CheckoutInterior.Active; if (!inside || !world) { lines.Add("no interior"); break; }
    // temporary colliders on the sectors' meshes (removed below)
    var added = new List<Component>();
    foreach (var it in inside.items.Values.Where(i => i.root && i.type == "sector"))
     foreach (var mf in it.root.GetComponentsInChildren<MeshFilter>()) if (mf.sharedMesh && !mf.GetComponent<Collider>()) { var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; added.Add(mc); }
    Physics.SyncTransforms();
    foreach (var (id, actorName) in new[] { ("padaria", "Worker_Baker"), ("acougue", "Worker_Butcher"), ("peixaria", "Worker_Fishmonger"), ("queijaria", "Worker_Cheesemaker") }) {
     var it = inside.Get("sector:" + id); var actor = world.Find(actorName);
     if (it == null || !actor) { lines.Add($"T{t} {id}: {(it == null ? "no sector" : "no " + actorName)}"); continue; }
     var spot = inside.StaffPoint(it);
     bool wasActive = actor.gameObject.activeSelf; if (!wasActive) actor.gameObject.SetActive(true);
     var walker = actor.GetComponent<CheckoutSectorWorker>(); bool walkerOn = walker && walker.enabled; if (walker) walker.enabled = false;
     actor.SetPositionAndRotation(spot, it.root.rotation); yield return null;
     var rot = it.root.rotation; Vector3 R = rot * Vector3.right, F = rot * Vector3.forward;
     // The body's real size: its meshes baked in the pose they have now, measured along the counter's axes.
     var bake = new Mesh(); var renderersSeen = new List<string>();
     (Vector3 min, Vector3 max) Body() {
      var mn = Vector3.one * 1e9f; var mx = -mn;
      void Add(Vector3 w) { var d = w - actor.position; var l = new Vector3(Vector3.Dot(d, R), d.y, Vector3.Dot(d, F)); mn = Vector3.Min(mn, l); mx = Vector3.Max(mx, l); }
      foreach (var r in actor.GetComponentsInChildren<Renderer>()) {
       if (!r.enabled || !r.gameObject.activeInHierarchy || r.name.StartsWith("Handled")) continue; // (not the bag they hand over)
       if (renderersSeen.Count < 12 && !renderersSeen.Any(x => x.StartsWith(r.name + " "))) renderersSeen.Add($"{r.name} {r.GetType().Name} {r.bounds.size.x:0.00}x{r.bounds.size.z:0.00}x{r.bounds.size.y:0.00}");
       if (r is SkinnedMeshRenderer sk) {
        // (the rigs' units differ: bake both ways and keep the one a person's height tall)
        Matrix4x4 best = sk.transform.localToWorldMatrix; Vector3[] bestV = null; float bestErr = 1e9f;
        foreach (var useScale in new[] { false, true }) {
         sk.BakeMesh(bake, useScale); var vs = bake.vertices;
         foreach (var m in new[] { sk.transform.localToWorldMatrix, Matrix4x4.TRS(sk.transform.position, sk.transform.rotation, Vector3.one) }) {
          float lo = 1e9f, hi = -1e9f; foreach (var v in vs) { float y = m.MultiplyPoint3x4(v).y; lo = Mathf.Min(lo, y); hi = Mathf.Max(hi, y); }
          float err = Mathf.Abs((hi - lo) - 1.75f); if (err < bestErr) { bestErr = err; best = m; bestV = vs; }
         }
        }
        if (bestV != null) foreach (var v in bestV) Add(best.MultiplyPoint3x4(v));
       }
       else if (r is MeshRenderer && r.GetComponent<MeshFilter>() is MeshFilter mf && mf.sharedMesh && mf.sharedMesh.isReadable) { var m = mf.transform.localToWorldMatrix; foreach (var v in mf.sharedMesh.vertices) Add(m.MultiplyPoint3x4(v)); }
      }
      return (mn, mx);
     }
     var stand = Body(); var work = stand;
     var anim = actor.GetComponent<MarketDay.MarketCharacterAnimator>();
     if (anim) { anim.Perform("BuyAtSpecialSector", false); for (float w = 0; w < 2.2f; w += .1f) { yield return Wait(.1f); var b = Body(); work.min = Vector3.Min(work.min, b.min); work.max = Vector3.Max(work.max, b.max); } }
     Destroy(bake);
     // The lane at the spot: the free distance to the counter (customer side, -Z) and to the back (+Z), at hip and chest height.
     bool backfaces = Physics.queriesHitBackfaces; Physics.queriesHitBackfaces = true;
     string Lane(Vector3 at) {
      var parts = new List<string>();
      foreach (var hy in new[] { .5f, .95f, 1.3f }) {
       var o = at + Vector3.up * hy;
       float Dist(Vector3 dir) { float best = 9; foreach (var h in Physics.RaycastAll(o, dir, 3f)) if (added.Contains(h.collider)) best = Mathf.Min(best, h.distance); return best; }
       float front = Dist(-F), back = Dist(F), left = Dist(-R), right = Dist(R);
       parts.Add($"{hy:0.00} m: front {(front < 9 ? front.ToString("0.00") : "-")} back {(back < 9 ? back.ToString("0.00") : "-")} sides {(left < 9 ? left.ToString("0.00") : "-")}/{(right < 9 ? right.ToString("0.00") : "-")}");
      }
      return string.Join("; ", parts);
     }
     // The body (as a box in the counter's axes) against the sector's mesh, standing still and at both ends of its pacing.
     float span = walker ? walker.span : .8f;
     int Clips(Vector3 at, (Vector3 min, Vector3 max) b, float shrink) {
      var c = (b.min + b.max) * .5f; var e = (b.max - b.min) * .5f * shrink;
      return Physics.OverlapBox(at + R * c.x + Vector3.up * c.y + F * c.z, e, rot).Count(col => added.Contains(col));
     }
     var clips = new List<string>();
     foreach (var off in new[] { -span, 0f, span }) {
      var at = spot + R * off;
      clips.Add($"x {off:+0.00;-0.00;0.00}: standing {Clips(at, stand, .9f)} working {Clips(at, work, .9f)} hits; lane {Lane(at)}");
     }
     Physics.queriesHitBackfaces = backfaces;
     if (t == 1 || t == 3) TierShot($"ft_staff_{id}_T{t}", 1600, 1000, spot + Vector3.up * 1.1f, 3.2f);
     if (walker) walker.enabled = walkerOn;
     if (!wasActive) actor.gameObject.SetActive(false);
     var q = Quaternion.Inverse(it.root.rotation);
     float toBack = it.piece.max.y - (q * (spot - it.root.position)).z;
     var sz = stand.max - stand.min; var wz = work.max - work.min;
     lines.Add($"STAFF T{t} {id} {it.template} {actorName}: body standing {sz.x:0.00} w x {sz.z:0.00} d x {sz.y:0.00} h m (x {stand.min.x:0.00}..{stand.max.x:0.00}, z {stand.min.z:0.00}..{stand.max.z:0.00}), working {wz.x:0.00} w x {wz.z:0.00} d (z {work.min.z:0.00}..{work.max.z:0.00}); spot {toBack:0.00} m from the back, piece depth {it.piece.max.y - it.piece.min.y:0.00} m; paces +-{span:0.00} m");
     foreach (var c in clips) lines.Add("   " + c);
     if (t == 1 && id == "padaria") lines.Add("   renderers: " + string.Join(", ", renderersSeen));
     yield return null;
    }
    foreach (var col in added) if (col) Destroy(col);
    TierReset();
   }
   File.WriteAllLines("Logs/ft_staff_probe.txt", lines);
   foreach (var l in lines) Note(l);
   Note("RESULT tiers staff: PASS (Logs/ft_staff_probe.txt)");
  }

  IEnumerator TierNavProbe() {
   var lines = new List<string>();
   foreach (var stage in new[] { "mercadinho", "supermercado" }) {
    yield return GoToStage(stage); yield return Wait(2);
    lines.AddRange(NavReport(stage));
   }
   File.WriteAllLines("Logs/ft_nav_probe.txt", lines);
   Note("RESULT tiers navprobe: PASS (Logs/ft_nav_probe.txt)");
  }

  // The way in, measured on the NavMesh: sidewalk → entrance → inside → every shelf's approach, and what stands by the door.
  List<string> NavReport(string tag) {
   var lines = new List<string>();
   var inside = CheckoutInterior.Active; var map = FindAnyObjectByType<CheckoutMap>(); if (!inside || !map) { lines.Add("no interior"); return lines; }
   var floor = inside.FloorRect; var door = map.Entrance;
   lines.Add($"== {tag}: floor {floor} entrance {door.ToString("0.00")} stall door {CheckoutStall.Door.ToString("0.00")} half {CheckoutStall.DoorHalf:0.00} entrance point {inside.EntrancePoint.ToString("0.00")}");
   string Path(Vector3 a, Vector3 b) {
    if (!NavMesh.SamplePosition(a, out var ha, 2f, NavMesh.AllAreas)) return "start off the mesh";
    if (!NavMesh.SamplePosition(b, out var hb, 2f, NavMesh.AllAreas)) return "end off the mesh";
    var path = new NavMeshPath(); NavMesh.CalculatePath(ha.position, hb.position, NavMesh.AllAreas, path);
    var end = path.corners.Length > 0 ? path.corners[path.corners.Length - 1] : Vector3.zero;
    return $"{path.status} corners {path.corners.Length} ends {end.ToString("0.0")} (wanted {hb.position.ToString("0.0")})";
   }
   lines.Add("sidewalk -> entrance: " + Path(door + new Vector3(0, 0, -4), door));
   lines.Add("entrance -> floor centre: " + Path(door, new Vector3(floor.center.x, CheckoutInterior.Floor, floor.center.y)));
   lines.Add("entrance -> just inside: " + Path(door, new Vector3(door.x, CheckoutInterior.Floor, floor.yMin + 1.2f)));
   foreach (var it in inside.items.Values.Where(i => i.root && i.type == "shelf").OrderBy(i => i.id))
    lines.Add($"entrance -> {it.id} approach {inside.Approach(it).ToString("0.0")}: " + Path(door, inside.Approach(it)));
   var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
   var field = typeof(MarketDay.MarketSimulation).GetField("furniture", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
   var nearDoor = Rect.MinMaxRect(door.x - 4, door.z - 3, door.x + 4, floor.yMin + 3);
   if (sim && field != null && field.GetValue(sim) is List<(Vector3 center, Vector3 size, float yaw)> boxes) {
    lines.Add($"navigation boxes: {boxes.Count}; near the way in:");
    foreach (var b in boxes) { var r = Rect.MinMaxRect(b.center.x - b.size.x * .5f, b.center.z - b.size.z * .5f, b.center.x + b.size.x * .5f, b.center.z + b.size.z * .5f); if (r.Overlaps(nearDoor)) lines.Add($"  box {b.center.ToString("0.00")} size {b.size.ToString("0.00")} yaw {b.yaw:0}"); }
   } else lines.Add("navigation boxes: not readable");
   foreach (var it in inside.items.Values.Where(i => i.root)) { var f = inside.FootprintOf(it); if (nearDoor.Contains(f.c)) lines.Add($"  piece near door {it.id} ({it.type}) {it.template} at {f.c.ToString("0.00")} half {f.hx:0.00}x{f.hz:0.00} outside={it.outside} design={it.design}"); }
   // The same walk with no furniture at all on the NavMesh: blocked still = the floor / ramp / walls, not the pieces.
   var layoutField = typeof(MarketDay.MarketSimulation).GetField("marketLayout", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
   if (sim && layoutField != null && layoutField.GetValue(sim) is MarketLayout navLayout) {
    var keep = sim.Furniture;
    sim.Furniture = () => System.Array.Empty<(Vector3 center, Vector3 size, float yaw)>();
    sim.RebuildLayoutNavigation(navLayout);
    lines.Add("no furniture: entrance -> just inside: " + Path(door, new Vector3(door.x, CheckoutInterior.Floor, floor.yMin + 1.2f)) + "; -> floor centre: " + Path(door, new Vector3(floor.center.x, CheckoutInterior.Floor, floor.center.y)));
    sim.Furniture = keep; sim.RebuildLayoutNavigation(navLayout);
    lines.Add("furniture back: entrance -> just inside: " + Path(door, new Vector3(door.x, CheckoutInterior.Floor, floor.yMin + 1.2f)));
   }
   // Where the walkable surface stops on the way in, and what could stand there.
   var from = new Vector3(door.x, .6f, door.z - .5f); var to = new Vector3(door.x, CheckoutInterior.Floor, floor.yMin + 1.5f);
   if (NavMesh.SamplePosition(from, out var hf, 1f, NavMesh.AllAreas)) {
    bool hit = NavMesh.Raycast(hf.position, to, out var rh, NavMesh.AllAreas);
    lines.Add($"raycast in from {hf.position.ToString("0.00")}: {(hit ? "stops at " + rh.position.ToString("0.00") + " normal " + rh.normal.ToString("0.00") : "clear")}");
    if (NavMesh.FindClosestEdge(rh.position, out var edge, NavMesh.AllAreas)) lines.Add($"closest edge {edge.position.ToString("0.00")} normal {edge.normal.ToString("0.00")}");
   }
   var probeBox = Rect.MinMaxRect(door.x - 3, door.z - 1, door.x + 3, floor.yMin + 1.5f);
   var obstacleField = typeof(MarketDay.MarketSimulation).GetField("obstacles", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
   if (sim && obstacleField != null && obstacleField.GetValue(sim) is List<Rect> rects) foreach (var r in rects) if (r.Overlaps(probeBox)) lines.Add($"  sim obstacle {r}");
   foreach (var b in CheckoutLotSites.Obstacles) if (Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z).Overlaps(probeBox)) lines.Add($"  lot ruin obstacle {b.center.ToString("0.00")} size {b.size.ToString("0.00")}");
   foreach (var o in FindObjectsByType<NavMeshObstacle>(FindObjectsSortMode.None)) if (o.isActiveAndEnabled && probeBox.Contains(new Vector2(o.transform.position.x, o.transform.position.z))) lines.Add($"  NavMeshObstacle {o.name} at {o.transform.position.ToString("0.00")} carve={o.carving} size {o.size.ToString("0.00")}");
   // Height of the walkable surface along the way in (the ramp up to the floor), every 0.5 m.
   var heights = new List<string>();
   for (float z = door.z - 3; z <= floor.yMin + 2; z += .5f) heights.Add(NavMesh.SamplePosition(new Vector3(door.x, CheckoutInterior.Floor, z), out var hz, .6f, NavMesh.AllAreas) ? $"{z:0.0}:{hz.position.y:0.00}" : $"{z:0.0}:-");
   lines.Add("walkable along the door axis (z:y): " + string.Join(" ", heights));
   return lines;
  }
 }
}