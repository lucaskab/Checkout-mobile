using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEngine;

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
  int tierShelves = -1; string tierCheckout, tierCold; InteriorItem[] tierLayout; DecorOwned[] tierOwned; DecorTier[] tierDecor; bool tierPatching;
  static readonly string[] TierKinds = { "produce", "drinks", "bakery", "dairy", "snacks", "coffee", "pizza", "home", "icecream" };
  static readonly Dictionary<string, string> TierKindOf = new Dictionary<string, string> {
   { "produce", "produce" }, { "drinks", "drinks" }, { "bakery", "bakery" }, { "dairy", "dairy" }, { "snacks", "shelf" }, { "coffee", "shelf" }, { "home", "shelf" }, { "pizza", "freezer" }, { "icecream", "icecream" } };

  void PatchTiers(Snapshot s) {
   if (!tierPatching || s == null) return;
   if (tierShelves > 0 && s.shelves != null)
    foreach (var x in s.shelves) if (TierKindOf.TryGetValue(x.id, out var k)) { x.tier = tierShelves; x.tierTemplate = k + "_T" + Mathf.Min(4, tierShelves); x.premium = tierShelves >= 5; }
   if (s.fixtureTiers == null) s.fixtureTiers = new FixtureTiers();
   if (tierCheckout != null) s.fixtureTiers.checkoutTemplate = tierCheckout;
   if (tierCold != null) { s.fixtureTiers.coldRoomTemplate = tierCold; s.fixtureTiers.coldRoomBuilding = ""; }
   if (tierLayout != null) s.interior = new InteriorState { items = tierLayout, owned = tierOwned ?? System.Array.Empty<DecorOwned>(), tiers = tierDecor ?? System.Array.Empty<DecorTier>() };
  }

  IEnumerator Tiers(string request) {
   var parts = request.Split('-'); var which = parts.Length > 1 ? parts[1].Split('.') : new[] { "flow", "shelves", "checkout", "coldroom", "carts", "decor" };
   foreach (var f in Directory.GetFiles("Logs", "ft_*.jpg")) File.Delete(f);
   CheckoutBridge.TestPatch = s => { Patch(s); PatchTiers(s); };
   foreach (var part in which) {
    Note("TIERS == " + part);
    switch (part) {
     case "flow": yield return TierFlow(); break;
     case "shelves": yield return TierShelves(); break;
     case "checkout": yield return TierCheckout(); break;
     case "coldroom": yield return TierCold(); break;
     case "carts": yield return TierCarts(); break;
     case "decor": yield return TierDecor(); break;
     default: Note("unknown part " + part); break;
    }
    TierReset();
   }
   CheckoutBridge.TestPatch = Patch;
  }

  void TierReset() { tierPatching = false; tierShelves = -1; tierCheckout = tierCold = null; tierLayout = null; tierOwned = null; tierDecor = null; roomEra = -1; var inside = CheckoutInterior.Active; if (inside) inside.editing = false; }

  void Hud(string action, string args) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-tiers-" + action + "-" + Time.frameCount + "\",\"action\":\"" + action + "\",\"args\":" + args + "}");
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

  // Lays out the fixtures of the shop (as a tidy player would: rows from the back wall, aisles between) at tier `t`.
  IEnumerator ShowTier(string stage, int era, int t, System.Action<List<InteriorItem>, Rect> extra) {
   tierPatching = true; roomEra = era; roomExtras = false; roomKeepInterior = false; tierShelves = t; tierLayout = null;
   yield return GoToStage(stage);
   var inside = CheckoutInterior.Active; if (!inside) { Note("no interior"); yield break; }
   var floor = inside.FloorRect; var zone = inside.CheckoutZone; var layout = inside.LayoutState;
   float right = CheckoutStall.Small && !CheckoutStall.PlacedCounter ? floor.xMax - .2f : zone.xMin - .25f;
   var items = new List<InteriorItem>();
   float rowTop = floor.yMax - .05f, x = floor.xMin + .1f, rowDepth = 0;
   float front = floor.yMin + (CheckoutStall.ShopInside ? 1.8f : 2.4f);
   foreach (var id in TierKinds.Where(k => ShelfEra[k] <= era)) {
    var template = TierKindOf[id] + "_T" + Mathf.Min(4, t); var piece = inside.TemplateObject(template)?.GetComponent<CheckoutInteriorPiece>();
    if (!piece) { Note("TIERS missing model " + template); continue; }
    float w = piece.max.x - piece.min.x, d = piece.max.y - piece.min.y;
    if (x + w > right) { x = floor.xMin + .1f; rowTop -= rowDepth + 1.35f; rowDepth = 0; }
    if (rowTop - d < front) break;
    // rot 0: customers on -Z (facing the front of the shop)
    var world = new Vector3(x - piece.min.x, 0, rowTop - piece.max.y);
    var b = CheckoutMarketLayout.Unproject(world, layout);
    items.Add(new InteriorItem { id = "shelf:" + id, type = "shelf", x = b.x, z = b.z, rot = 0 });
    x += w + .3f; rowDepth = Mathf.Max(rowDepth, d);
   }
   extra?.Invoke(items, floor);
   tierLayout = items.ToArray();
   yield return Wait(3);
  }

  void ShootFloor(string name) {
   var inside = CheckoutInterior.Active; var floor = inside.FloorRect;
   float size = Mathf.Max(floor.width, floor.height) * (CheckoutStall.Small ? 1.25f : 1.05f) + 1;
   CaptureSized(name, 2048, 1152, new Vector3(floor.center.x, CheckoutInterior.FloorHere, floor.center.y), size);
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
   var stages = new[] { ("mesinha", 1), ("conteiner", 1), ("spati", 1), ("quitanda", 1), ("minimercado", 2), ("mercadinho", 2), ("supermercado", 3), ("hipermercado", 4), ("rede", 4) };
   var bad = new List<string>();
   foreach (var (stage, t) in stages) {
    tierPatching = true; tierCold = "coldroom_T" + t;
    yield return GoToStage(stage);
    yield return Wait(1);
    var root = CheckoutColdRoom.Root;
    Note($"TIERS cold {stage} T{t}: {(root ? root.name + " at " + root.position.ToString("0.0") + " yaw " + root.eulerAngles.y.ToString("0") : "not shown")} · {CheckoutColdRoom.Side}");
    if (t >= 2 && !root) bad.Add(stage);
    CaptureSized($"ft_cold_{stage}_map", 2048, 1152, null, 0);
    if (root) { var b = CheckoutColdRoom.Bounds; CaptureSized($"ft_cold_{stage}_close", 2048, 1152, new Vector3(b.center.x, .5f, b.center.z), Mathf.Max(b.size.x, b.size.z) * 3.2f + 6); }
   }
   Note($"RESULT tiers coldroom: {(bad.Count == 0 ? "PASS" : "FAIL")} placed in every expansion from the minimercado" + (bad.Count > 0 ? "; no room at " + string.Join(", ", bad) : ""));
  }

  // ------------------------------------------------------------------ the three cart stations, customers using them
  IEnumerator TierCarts() {
   tierOwned = new[] { new DecorOwned { type = "basket-station", count = 1 }, new DecorOwned { type = "cart-corral", count = 1 }, new DecorOwned { type = "big-cart-corral", count = 1 } };
   yield return ShowTier("supermercado", 8, 3, (items, floor) => {
    // the stations by the entrance, along the front wall
    var inside = CheckoutInterior.Active; var layout = inside.LayoutState; float x = floor.xMin + .4f;
    foreach (var (id, type) in new[] { ("decor-901", "basket-station"), ("decor-902", "cart-corral"), ("decor-903", "big-cart-corral") }) {
     var piece = inside.TemplateObject(inside.DecorTemplate(type))?.GetComponent<CheckoutInteriorPiece>(); if (!piece) { Note("TIERS missing station " + type); continue; }
     var w = new Vector3(x - piece.min.x, 0, floor.yMin + .05f - piece.min.y);
     var b = CheckoutMarketLayout.Unproject(w, layout); items.Add(new InteriorItem { id = id, type = type, x = b.x, z = b.z, rot = 0 });
     x += piece.max.x - piece.min.x + .35f;
    }
   });
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
   yield return Wait(10);
   var shown = walkers.Where(w => w && w.gameObject.activeInHierarchy).Select(w => { var rig = w.GetComponent<CheckoutShopperRig>(); return rig ? (rig.carrier + (rig.cart ? "/cart" : "/basket-or-hands")) : "-"; }).ToList();
   Note("TIERS shoppers: " + string.Join(", ", shown));
   ShootFloor("ft_carts_shoppers");
   yield return Wait(6);
   ShootFloor("ft_carts_shoppers2");
   bool ok = stations.Count == 3 && stations.All(s => s.template.StartsWith("carts_T"));
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
     foreach (var (type, _) in sets) {
      var piece = inside.TemplateObject(inside.DecorTemplate(type))?.GetComponent<CheckoutInteriorPiece>(); if (!piece) continue;
      var w = new Vector3(x - piece.min.x, 0, floor.yMin + .3f - piece.min.y);
      var b = CheckoutMarketLayout.Unproject(w, layout); items.Add(new InteriorItem { id = "decor-95" + (n++), type = type, x = b.x, z = b.z, rot = 0 });
      x += piece.max.x - piece.min.x + .5f;
     }
    });
    var shown = CheckoutInterior.Active.items.Values.Where(i => i.root && sets.Any(s => s.Item1 == i.type)).Select(i => i.type + "=" + i.template).ToList();
    found += shown.Count;
    Note($"TIERS decor round {r}: " + string.Join(", ", shown));
    ShootFloor($"ft_decor_T{r}");
   }
   Note($"RESULT tiers decor: {(found >= 9 ? "PASS" : "FAIL")} {found}/9 pieces shown over three rounds");
  }
 }
}
