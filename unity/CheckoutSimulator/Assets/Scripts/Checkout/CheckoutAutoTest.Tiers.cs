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
   Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(2);
   Check(Sh("produce").tier == Mathf.Min(2, before + 1) && Sh("produce").tierTemplate.StartsWith("produce_T"), $"spati: produce T{before} → T{Sh("produce").tier} ({Sh("produce").tierTemplate})");
   Hud("upgradeShelfCapacity", "[\"produce\",\"coins\"]"); yield return Wait(2);
   Check(Sh("produce").tier <= 2, $"spati: capped at T2 (shows T{Sh("produce").tier}, capacity {Sh("produce").capacity})");
   Hud("purchaseShopItem", "[\"checkout-register\",\"diamonds\"]"); yield return Wait(2);
   Check(bridge.State.fixtureTiers != null && bridge.State.fixtureTiers.checkout == 2, $"spati: checkout register → step {bridge.State.fixtureTiers?.checkout}");
   yield return GoToStage("minimercado");
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(2);
   Check(Sh("produce").tier == 3, $"minimercado: produce T{Sh("produce").tier} ({Sh("produce").tierTemplate}), capacity {Sh("produce").capacity}");
   Hud("purchaseShopItem", "[\"cold-room-2\",\"coins\"]"); yield return Wait(2);
   Check(!string.IsNullOrEmpty(bridge.State.fixtureTiers.coldRoomBuilding), $"minimercado: cold room T2 works '{bridge.State.fixtureTiers.coldRoomBuilding}' until {bridge.State.fixtureTiers.coldRoomEndsAt}");
   yield return Wait(1);
   Note("TIERS cold room while building: " + CheckoutColdRoom.Side);
   Hud("devFinishInteriorConstructions", "[]"); yield return Wait(2);
   Check(bridge.State.fixtureTiers.coldRoom == 2, $"minimercado: cold room tier {bridge.State.fixtureTiers.coldRoom} at {CheckoutColdRoom.Side}");
   yield return GoToStage("supermercado");
   Check(Sh("produce").tier == 3, $"supermercado: produce keeps T{Sh("produce").tier} (bought 3)");
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(1.5f);
   Hud("upgradeShelfCapacity", "[\"produce\",\"diamonds\"]"); yield return Wait(2);
   Check(Sh("produce").tier == 5 && Sh("produce").premium, $"supermercado: produce ★ (tier {Sh("produce").tier}, premium {Sh("produce").premium})");
   Hud("purchaseDecor", "[\"atm\",\"coins\"]"); yield return Wait(1.5f);
   Hud("upgradeDecorTier", "[\"atm\",\"coins\"]"); yield return Wait(2);
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
    Hud("upgradeSectorTier", "[\"padaria\",\"coins\"]"); yield return Wait(2.5f);
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