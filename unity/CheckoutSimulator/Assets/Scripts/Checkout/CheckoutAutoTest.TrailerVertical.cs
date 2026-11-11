using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Vertical footage for the Google Ads videos (Lucas 11/11: "pode gravar imagens novas que você realmente ache que vai
 // fazer sucesso"; and from the first cut: the checkouts shown as packed had nobody in line, and the crowd bunched at
 // the crosswalk looked like a bug). Scenes "v..." of eventstrailer, e.g. "eventstrailer-pt-vmesa.vcresce.vhiper.vrede":
 // the Game view at 1080x1440 (3:4, the ad's gameplay window), no HUD, the same files Logs/tr_<lang>_<scene>_<k>.mjpg.
 // The checkout shots wait until the open counters have people in line (shoppers who buy one or two things are sent
 // first); the chain gets fewer shoppers so nobody piles up outside waiting to get in.
 public sealed partial class CheckoutAutoTest {
  public const int TrVW = 1080, TrVH = 1440;
  static bool TrIsVertical(IEnumerable<string> scenes) => scenes.Any(s => s.Length > 1 && s[0] == 'v');

  IEnumerator TrVertical(string scene) =>
   scene == "vmesa" ? TrVMesa() : scene == "vcresce" ? TrVCresce() : scene == "vhiper" ? TrVHiper() : scene == "vrede" ? TrVRede() : null;

  /// <summary>Orthographic half-height that fits a shop `size` m across in the 3:4 frame, a little street around it.</summary>
  static float TrVZoom(float size) => Mathf.Clamp((size * 1.4f + 3.5f) / 1.5f, 3.4f, 24f);

  /// <summary>Shoppers who buy one or two things and go straight to the checkouts (the lines form in seconds).</summary>
  IEnumerator TrVSpawnQuick(int count, float gap) {
   var rnd = new System.Random(11);
   var all = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).ToList();
   for (int sent = 0, guard = 0; sent < count && guard < count * 10; guard++) {
    var shelfIds = (bridge.State.shelves ?? new Shelf[0]).Where(x => x != null && x.unlocked && !x.building).Select(x => x.id).ToList();
    var idle = all.FirstOrDefault(w => w && !w.gameObject.activeSelf && !w.Reserved);
    if (idle && shelfIds.Count > 0 && !CheckoutWalker.ShopCrowded) {
     var buy = new List<Purchase>(); int k = 1 + rnd.Next(2);
     for (int j = 0; j < k; j++) buy.Add(new Purchase { shelfId = shelfIds[rnd.Next(shelfIds.Count)], productId = 1, quantity = 1 + rnd.Next(3) });
     idle.Begin(new Customer { id = "qa-vad-" + sent, name = "QA", spent = 12, purchases = buy.ToArray() });
     sent++; yield return new WaitForSecondsRealtime(gap);
    } else yield return new WaitForSecondsRealtime(.4f);
   }
  }

  string TrVLanes() {
   var map = FindAnyObjectByType<CheckoutMap>(); if (!map || map.Lanes == null) return "no lanes";
   return string.Join(" ", map.Lanes.lanes.Select(l => $"[{l.itemId ?? "main"} {(l.Open ? "open" : "shut")}{(l.staffed ? "" : " no-cashier")}{(l.cashier && l.cashier.gameObject.activeInHierarchy ? " op" : "")} q{l.queue.Count}]"));
  }

  /// <summary>Until all the open counters but one have at least `perLane` people in line (at most `timeout` s).</summary>
  IEnumerator TrVWaitQueues(int perLane, float timeout) {
   var map = FindAnyObjectByType<CheckoutMap>();
   float t = 0;
   for (; map && map.Lanes != null && t < timeout; t += .5f) {
    var open = map.Lanes.lanes.Where(l => l.Open && !l.isKiosk).ToList();
    int busy = open.Count(l => l.queue.Count >= perLane);
    if (open.Count > 0 && busy >= Mathf.Max(1, open.Count - 1)) break;
    yield return new WaitForSecondsRealtime(.5f);
   }
   Note($"vads lanes after {t:0.0}s: {TrVLanes()}");
  }

  /// <summary>The shop open for business (eventscrowd's day ends after 300 s, long before the chain's shots: a closed
  /// shop leaves its shoppers piled up at the door and on the crosswalk, and nobody reaches the checkouts).</summary>
  IEnumerator TrVOpen(float settle) {
   if (bridge.State != null && bridge.State.isOpen) yield break;
   yield return TrOpen();
   Note($"vads: shop opened ({bridge.State?.isOpen}), settling {settle:0} s");
   yield return new WaitForSecondsRealtime(settle);
  }

  IEnumerator TrVMesa() {
   TrHud("resetGame", "[]"); yield return new WaitForSecondsRealtime(5f);
   TrHud("skipOnboarding", "[]"); yield return new WaitForSecondsRealtime(1.5f);
   CheckoutBridge.QaNoVisits = true;
   foreach (var w in FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None)) if (w && w.gameObject.activeSelf) w.CancelVisit();
   yield return TrOpen(); yield return new WaitForSecondsRealtime(2f);
   var (c, _) = TrShop();
   trLastWalker = null; yield return TrSpawn(1, .1f);
   var who = trLastWalker;
   var last = who ? who.transform.position : Vector3.zero; int still = 0;
   for (float t = 0; t < 60 && who && who.gameObject.activeInHierarchy; t += .25f) {
    yield return new WaitForSecondsRealtime(.25f);
    var pos = who.transform.position; var d = pos - c; d.y = 0;
    still = d.magnitude < 2.8f && (pos - last).magnitude < .04f ? still + 1 : 0; last = pos;
    if (still >= 2) break;
   }
   yield return TrGlideShot(c + new Vector3(.35f, 0, .2f), 3.1f, c, 3.9f, 3.5f);
   yield return TrGlideShot(c, 4.3f, c + new Vector3(-.6f, 0, .5f), 6.5f, 3f);
   CheckoutBridge.QaNoVisits = false;
  }

  IEnumerator TrVCresce() {
   TrHud("setMarketLevel", "[45]"); TrHud("devAdjustCoins", "[9000000]"); yield return new WaitForSecondsRealtime(2f);
   TrHud("dismissLevelUp", "[]"); yield return CloseCardsSettled();
   foreach (var stage in new[] { "tenda", "banca", "conteiner", "spati", "quitanda", "minimercado", "mercadinho", "supermercado" }) {
    int era = System.Array.IndexOf(EraIds, stage);
    if (era >= 4) {
     TrTiers(stage == "minimercado" ? 3 : stage == "mercadinho" || stage == "supermercado" ? 4 : 2, -1);
     yield return TrCrowd(stage, 16); yield return TrFill(stage); yield return new WaitForSecondsRealtime(10f);
    } else {
     if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
     roomEra = -1; roomKeepInterior = false; crowdLayout = null; tierLayout = null; tierOwned = null; tierDecor = null;
     TrHud("devSetMarketEra", "[\"" + stage + "\"]"); yield return new WaitForSecondsRealtime(10f);
     yield return TrOpen(); yield return new WaitForSecondsRealtime(9f);
    }
    var (c, size) = TrShop();
    float z = TrVZoom(size);
    Note($"vads cresce {stage}: shop {size:0.0} m, zoom {z:0.0}");
    yield return TrGlideShot(c + new Vector3(.5f, 0, .3f), z * 1.08f, c, z, 2.4f);
   }
  }

  IEnumerator TrVHiper() {
   TrTiers(5, 3);
   yield return TrCrowd("hipermercado", 40, ".lanes");
   TrDecorateOutside(new[] { "flower-bed", "ice-cream-cart", "bench", "popcorn-cart" });
   yield return TrFill("hipermercado");
   yield return new WaitForSecondsRealtime(4f);
   yield return TrVOpen(2f);
   StartCoroutine(TrSpawn(30, .35f));
   yield return new WaitForSecondsRealtime(22f);   // the shoppers walk in
   var (c, size) = TrShop();
   var inside = CheckoutInterior.Active;
   Note($"vads hiper: shop {size:0.0} m; {TrVLanes()}");
   // 1. the aisles full of shoppers, close (the hook)
   yield return TrGlideShot(c + new Vector3(-size * .18f, 0, .5f), 8.5f, c + new Vector3(size * .05f, 0, 1f), 7.6f, 4f);
   // 2. the building and its sign from the street (the reveal)
   yield return TrVOpen(8f);
   yield return TrGlideShot(c + new Vector3(-3, 0, -5), 17f, c + new Vector3(0, 0, -1), 14f, 4f);
   if (inside) {
    // 3. the checkouts, a line at every counter
    yield return TrVOpen(6f);
    StartCoroutine(TrVSpawnQuick(30, .35f));
    yield return TrVWaitQueues(2, 60f);
    var z = inside.CheckoutZone; var lanes = new Vector3(z.center.x, 0, z.center.y);
    yield return TrGlideShot(lanes + new Vector3(-1f, 0, -.3f), 6.2f, lanes + new Vector3(.8f, 0, .3f), 5.4f, 4.5f);
    StartCoroutine(TrVSpawnQuick(12, .5f));
    yield return TrVWaitQueues(2, 20f);
    yield return TrGlideShot(lanes + new Vector3(1.2f, 0, 0), 4.4f, lanes + new Vector3(-.6f, 0, .2f), 3.9f, 4f);
    // 4. a sector counter, close
    var sector = inside.items.Values.FirstOrDefault(i => i.root && i.id == "sector:acougue") ?? inside.items.Values.FirstOrDefault(i => i.root && i.type == "sector");
    if (sector != null) { var p = sector.root.position; p.y = 0; yield return TrGlideShot(p + new Vector3(.6f, 0, -.4f), 3.8f, p, 3.1f, 3.5f); }
   }
  }

  IEnumerator TrVRede() {
   TrTiers(5, 3);
   yield return TrCrowd("rede", 26, ".lanes.brand");
   TrDecorateOutside(new[] { "flower-bed", "hotdog-cart", "bench", "fountain" });
   yield return TrFill("rede");
   TrHud("orderFromDistributionCenter", "[[{\"productId\":172,\"boxes\":2},{\"productId\":175,\"boxes\":1}]]");
   yield return new WaitForSecondsRealtime(4f);
   yield return TrVOpen(2f);
   StartCoroutine(TrSpawn(16, .5f));
   yield return new WaitForSecondsRealtime(16f);
   var (c, size) = TrShop();
   Note($"vads rede: shop {size:0.0} m; {TrVLanes()}");
   var letters = GameObject.Find("S4 name");
   if (letters) { var l = letters.transform.position; l.y = 0; yield return TrGlideShot(l + new Vector3(0, 0, -5.5f), 8.5f, l + new Vector3(0, 0, -4.5f), 11f, 3.5f); }
   yield return TrVOpen(6f);
   // the distribution centre and its trucks
   yield return TrGlideShot(new Vector3(11, 0, 40), 14f, new Vector3(11, 0, 43), 18f, 4f);
   // the shop, then the whole map from above
   yield return TrGlideShot(c, 13f, new Vector3(5, 0, 22), 30f, 5.5f);
   var inside = CheckoutInterior.Active;
   if (inside) {
    yield return TrVOpen(6f);
    StartCoroutine(TrVSpawnQuick(26, .35f));
    yield return TrVWaitQueues(2, 60f);
    var z = inside.CheckoutZone; var lanes = new Vector3(z.center.x, 0, z.center.y);
    yield return TrGlideShot(lanes + new Vector3(-1f, 0, -.3f), 6f, lanes + new Vector3(.8f, 0, .3f), 5.2f, 4.5f);
   }
  }
 }
}
