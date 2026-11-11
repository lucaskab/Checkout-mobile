using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "securityvideo[-<stage>]": the store dog and the shoplifter (Lucas 08/11), recorded in a furnished shop:
 //   Logs/sec_1_caramelo.mjpg  the stray at the door → adopted → walks in → potters around → a pat → nap
 //   Logs/sec_2_ladrao.mjpg    a thief sneaks in, stashes the goods, runs; the dog barks; the player taps him
 //   Logs/sec_3_seguranca.mjpg the same with a security guard on duty: the guard sprints and stops him
 // "securityshots": close stills of the three characters (Logs/sec_*.jpg) to check the assets in the game's light.
 public sealed partial class CheckoutAutoTest {
  IEnumerator SecurityVideo(string request) {
   var parts = request.Split('-'); var stage = parts.Length > 1 && parts[1] != "" ? parts[1] : "minimercado";
   bool shotsOnly = request.StartsWith("securityshots");
   foreach (var f in Directory.GetFiles("Logs", "sec_*.*")) File.Delete(f);
   int seq = 0; void Act(string action, string args) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-sec-" + (++seq) + "\",\"action\":\"" + action + "\",\"args\":" + args + "}");
   // a furnished shop of the stage, open, with customers (as in eventsvideo-<stage>-furnished)
   Act("resetGame", "[]"); yield return new WaitForSecondsRealtime(4f);
   Act("skipOnboarding", "[]"); Act("claimDayResult", "[]"); yield return new WaitForSecondsRealtime(1.5f);
   Act("setMarketLevel", "[40]");
   Act("grantCurrencyPurchase", "[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-sec-" + DateTime.Now.Ticks + "\"}]");
   yield return new WaitForSecondsRealtime(2f); Act("dismissLevelUp", "[]");
   Act("devSetMarketEra", "[\"" + stage + "\"]"); yield return new WaitForSecondsRealtime(6);
   var inside0 = CheckoutInterior.Active;
   for (float t = 0; t < 8 && (inside0 == null || bridge.State?.era?.id != stage); t += .5f) { yield return new WaitForSecondsRealtime(.5f); inside0 = CheckoutInterior.Active; }
   yield return new WaitForSecondsRealtime(3.5f);
   for (int k = 0; k < 9; k++) { Act("unlockNextShelf", "[]"); yield return new WaitForSecondsRealtime(.7f); }
   var inside = CheckoutInterior.Active;
   if (inside != null) {
    var fl = inside.FloorRect; int put = 0;
    foreach (var key in new System.Collections.Generic.List<string>(inside.waiting.Keys)) {
     if (key.StartsWith("sector:")) continue;
     CheckoutInterior.Item it = null;
     for (float pz = fl.yMin + 1.2f; it == null && pz < fl.yMax - .6f; pz += .8f)
      for (float px = fl.xMin + .8f; it == null && px < fl.xMax - .6f; px += .8f)
       it = inside.PlaceWaiting(key, new Vector3(px, 0, pz));
     if (it != null && inside.Reachable(out _)) put++; else if (it != null) { inside.waiting[key] = (it.type, it.template); Destroy(it.root.gameObject); inside.items.Remove(key); }
    }
    inside.MarkPending(); FindAnyObjectByType<CheckoutMap>().SaveInterior(); yield return new WaitForSecondsRealtime(2.5f);
    Act("devFinishInteriorConstructions", "[]"); yield return new WaitForSecondsRealtime(3f);
    Note($"security: {put} pieces placed");
   }
   Act("hireEmployee", "[\"cashier\"]"); Act("hireEmployee", "[\"stock_clerk\"]"); yield return new WaitForSecondsRealtime(1.5f);
   if (!bridge.State.isOpen) { Act("setMarketOpen", "[true]"); for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f); }
   yield return new WaitForSecondsRealtime(15f);   // customers come in
   yield return CloseCardsSettled();
   var home = FindAnyObjectByType<MarketDay.MarketSimulation>(); var map = FindAnyObjectByType<CheckoutMap>();
   var pets = CheckoutPets.Instance; var sec = CheckoutSecurity.Instance;
   Note($"security: era={bridge.State?.era?.id} open={bridge.State.isOpen} pet offer={bridge.State.pet?.offer} adopted={bridge.State.pet?.adopted}");

   if (request.StartsWith("securitybeds")) { yield return PetBeds(home, map, pets, Act); if (home) home.HomeCamera(); yield break; }

   // ---- 1: Caramelo
   var door = map.Entrance;
   if (home) home.FocusCinematic(new Vector3(door.x, 0, door.z - 1.0f), 3.4f);
   yield return new WaitForSecondsRealtime(1.5f);
   if (!shotsOnly) RecStart("Logs/sec_1_caramelo.mjpg");
   yield return Frames(3f);
   CheckoutPets.Tapped(); Note("tap: adopt");                                   // the stray at the door
   for (float t = 0; t < 4 && !(bridge.State.pet?.adopted ?? false); t += .1f) yield return Frames(.1f);
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 9f;) { if (pets && pets.Root && home) home.FocusCinematic(pets.Root.position + Vector3.back * .4f, 3.0f); yield return null; }
   Note("heights " + (pets ? pets.Heights() : "") + " | customers " + CustomerFeet());
   pets?.QaAct("walk");
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 7f;) { if (pets && pets.Root && home) home.FocusCinematic(pets.Root.position + Vector3.back * .4f, 3.0f); yield return null; }
   CheckoutPets.Tapped(); Note("tap: pat");                                      // a pat: hearts and the happy dance
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 4f;) { if (pets && pets.Root && home) home.FocusCinematic(pets.Root.position + Vector3.back * .3f, 2.6f); yield return null; }
   pets?.QaAct("sleep");
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 6f;) { if (pets && pets.Root && home) home.FocusCinematic(pets.Root.position + Vector3.back * .3f, 2.6f); yield return null; }
   if (shotsOnly) { if (pets && pets.Root) { CaptureAt(pets.Root.position + Vector3.up * .4f, 2.2f, "sec_dog_sleep"); pets.QaAct("pet"); yield return new WaitForSecondsRealtime(.6f); CaptureAt(pets.Root.position + Vector3.up * .4f, 2.2f, "sec_dog_happy"); } }
   else RecStop();
   Note($"pet: adopted={bridge.State.pet?.adopted} happy={bridge.State.pet?.happyLeftMs} cooldown={bridge.State.pet?.cooldownLeftMs}");

   // ---- 2: the shoplifter, caught by the player
   yield return Thief("sec_2_ladrao", tapIt: true, home, shotsOnly);
   // ---- 3: with a security guard on duty
   Act("hireEmployee", "[\"security\"]"); yield return new WaitForSecondsRealtime(4f);
   Note($"guard hired: {bridge.State.security?.guardHired} employees={string.Join(",", (bridge.State.employees ?? Array.Empty<Employee>()).Select(e => e.role))}");
   yield return Thief("sec_3_seguranca", tapIt: false, home, shotsOnly);
   if (home) home.HomeCamera();
  }

  // "securitybeds": Caramelo's beds (Lucas 08/11). The dog is adopted, a wooden house goes on the sidewalk and a round bed
  // inside; the market closes and he walks to the nearest bed and sleeps (Logs/sec_beds_night.mjpg), it opens and he
  // wakes up (same video); then stills of him on every bed and of the fabrics (Logs/sec_bed_*.jpg).
  IEnumerator PetBeds(MarketDay.MarketSimulation home, CheckoutMap map, CheckoutPets pets, Action<string, string> act) {
   CheckoutPets.Tapped(); Note("tap: adopt");
   for (float t = 0; t < 5 && !(bridge.State.pet?.adopted ?? false); t += .2f) yield return new WaitForSecondsRealtime(.2f);
   yield return new WaitForSecondsRealtime(3f);
   string[] beds = { "pet-bed-round", "pet-bed-basket", "pet-bed-house", "pet-bed-sofa", "pet-bed-royal" };
   foreach (var id in beds) act("purchaseDecor", "[\"" + id + "\",\"" + (id == "pet-bed-royal" ? "diamonds" : "coins") + "\"]");
   yield return new WaitForSecondsRealtime(1.5f);
   var inside = CheckoutInterior.Active;
   if (!inside || !pets || !pets.Root) { Note("beds: no interior or dog"); yield break; }
   var away = map.Entrance - map.Register; away.y = 0; away = away.sqrMagnitude > .01f ? away.normalized : Vector3.back;
   var side = Vector3.Cross(Vector3.up, away);
   // the house on the sidewalk beside the door: the first spot the build mode accepts where it was asked (not pushed away)
   CheckoutInterior.Item house = null;
   // (the shops' fronts face -Z: the sidewalk runs along X in front of the door)
   foreach (var dx in new[] { 3.2f, -3.2f, 4.6f, -4.6f, 6f, -6f })
    foreach (var dz in new[] { 1.4f, 2f, .9f }) {
     if (house != null) break;
     var want = map.Entrance + Vector3.back * dz + Vector3.right * dx;
     if (dx == 3.2f && dz == 1.4f) want = new Vector3(6.4f, 0, -8.1f);    // (minimercado: the shop's front walk is kept free; the east sidewalk takes decorations)
     var it = inside.AddDecor("pet-bed-house", want, true);
     Note($"beds: house try {want:F1} -> {(it != null ? it.root.position.ToString("F1") : "null")}");
     if (it == null) continue;
     var gap = it.root.position - want; gap.y = 0;
     if (gap.magnitude < 1.5f) house = it; else { Destroy(it.root.gameObject); inside.items.Remove(it.id); }
    }
   Note($"beds: entrance {map.Entrance:F2} register {map.Register:F2}");
   inside.MarkPending(); map.SaveInterior();
   Note($"beds: owned={string.Join(",", beds)} house={(house != null ? house.root.position.ToString("F2") + " rot " + house.rot : "none")}");
   yield return new WaitForSecondsRealtime(1.5f);
   // night 1: only the house outside
   if (home) home.FocusCinematic(pets.Root.position + Vector3.back * .4f, 3.4f);
   RecStart("Logs/sec_beds_night.mjpg");
   act("setMarketOpen", "[false]"); Note("market closed");
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 24f;) { if (home && pets.Root) home.FocusCinematic(pets.Root.position + Vector3.back * .4f, 3.2f); yield return null; }
   Note("beds: dog at " + pets.Root.position.ToString("F2") + " " + pets.Heights());
   act("claimDayResult", "[]"); yield return new WaitForSecondsRealtime(1f);
   act("setMarketOpen", "[true]"); act("startDay", "[]"); Note("market open");
   for (float t0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - t0 < 9f;) { if (home && pets.Root) home.FocusCinematic(pets.Root.position + Vector3.back * .4f, 3.2f); yield return null; }
   RecStop();
   // every bed, inside the shop, and the dog asleep on each (stills)
   var fl = inside.FloorRect; var placed = new System.Collections.Generic.List<CheckoutInterior.Item>();
   float x = fl.xMin + 1.4f;
   foreach (var id in beds) {
    if (id == "pet-bed-house") continue;
    var it = inside.AddDecor(id, new Vector3(x, 0, fl.yMax - 1.3f));
    if (it != null) placed.Add(it); x += 2.2f;
    Note($"beds: {id} {(it != null ? it.root.position.ToString("F2") : "no room")}");
   }
   inside.MarkPending(); map.SaveInterior(); yield return new WaitForSecondsRealtime(1f);
   foreach (var it in placed) {
    pets.Root.position = it.root.position + Vector3.back * 1.2f;
    pets.QaAct("sleep");
    yield return new WaitForSecondsRealtime(3.6f);                       // hop, turn and curl up (Dog_CurlDown 1.7 s)
    CaptureAt(it.root.position + Vector3.up * .3f, 2.2f, "sec_bed_" + it.type.Replace("pet-bed-", ""));
    Note("beds: " + it.type + " dog " + pets.Root.position.ToString("F2") + " " + pets.Heights());
   }
   if (house != null) { pets.Root.position = house.root.position + Vector3.back * 1.2f; pets.QaAct("sleep"); yield return new WaitForSecondsRealtime(3.6f); CaptureAt(house.root.position + Vector3.up * .3f, 2.4f, "sec_bed_house"); }
   // the fabrics
   foreach (var style in new[] { "teal", "orange", "rose" }) {
    act("buyPetCosmetic", "[\"bedstyle_" + style + "\"]"); yield return new WaitForSecondsRealtime(1.2f);
    var royal = placed.Find(p => p.type == "pet-bed-royal") ?? (placed.Count > 0 ? placed[0] : null);
    if (royal != null) CaptureAt(royal.root.position + Vector3.up * .3f, 3.2f, "sec_bed_style_" + style);
   }
   Note("beds: done, style=" + bridge.State.pet?.bedStyle);
  }

  // the market's own walkers: root height vs their lowest point (the reference for "feet on the floor")
  static string CustomerFeet() {
   var sb = new System.Text.StringBuilder(); int n = 0;
   foreach (var r in FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None)) {
    var root = r.transform.root; if (n >= 3 || !r.gameObject.activeInHierarchy) continue;
    Transform walker = r.transform; while (walker.parent && !walker.name.StartsWith("Customer_")) walker = walker.parent;
    if (!walker.name.StartsWith("Customer_")) continue;
    var tmp = new Mesh(); r.BakeMesh(tmp, true); float min = float.MaxValue; foreach (var v in tmp.vertices) { var w = r.transform.position + r.transform.rotation * v; if (w.y < min) min = w.y; } Destroy(tmp);
    sb.Append($"{walker.name} root {walker.position.y:0.000} feet {min:0.000}; "); n++;
   }
   return sb.ToString();
  }

  IEnumerator Thief(string name, bool tapIt, MarketDay.MarketSimulation home, bool shotsOnly) {
   var map = FindAnyObjectByType<CheckoutMap>(); var sec = CheckoutSecurity.Instance;
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-" + name + "\",\"action\":\"devSpawnThief\",\"args\":[]}");
   for (float t = 0; t < 4 && string.IsNullOrEmpty(bridge.State.security?.thief?.id); t += .2f) yield return new WaitForSecondsRealtime(.2f);
   var th = bridge.State.security?.thief; Note($"{name}: thief={th?.id} phase={th?.phase} product={th?.productName} shelf={th?.shelfId}");
   if (string.IsNullOrEmpty(th?.id)) { Note("no thief spawned"); yield break; }
   var door = map.Entrance; if (home) home.FocusCinematic(new Vector3(door.x, 0, door.z - 1f), 3.6f);
   yield return new WaitForSecondsRealtime(.4f);
   if (!shotsOnly) RecStart("Logs/" + name + ".mjpg");
   bool tapped = false; float fleeingAt = -1; int shots = 0; string lastPhase = ""; float t0 = Time.realtimeSinceStartup, goneAt = -1;
   while (Time.realtimeSinceStartup - t0 < 40f) {
    float t = Time.realtimeSinceStartup - t0;
    var cur = bridge.State.security?.thief; var tr = sec ? sec.ThiefTransform : null;
    var phase = string.IsNullOrEmpty(cur?.id) ? "none" : cur.phase;
    if (phase != lastPhase && sec) Note($"{name}: heights {sec.Heights()}");
    if (phase != lastPhase) { Note($"{name}: {t:0.0}s phase {phase} (guard in {cur?.guardInMs:0} ms, flee left {cur?.fleeLeftMs:0} ms, by {cur?.caughtBy})"); lastPhase = phase; }
    if (tr && home) home.FocusCinematic(tr.position + Vector3.back * .5f, 3.4f);
    if (phase == "fleeing") {
     if (fleeingAt < 0) fleeingAt = t;
     if (tapIt && !tapped && t - fleeingAt > 2.4f) { tapped = true; CheckoutSecurity.Tapped(cur.id); Note($"{name}: tap at {t:0.0}s"); }
    }
    if (shotsOnly && tr && shots < 4 && t > shots * 4f) { CaptureAt(tr.position + Vector3.up * 1f, 3.2f, $"{name}_{shots++}"); }
    if (phase == "none" && !tr) { if (goneAt < 0) goneAt = t; if (t - goneAt > 1.5f) break; } else goneAt = -1;
    yield return null;
   }
   // the dog chased him off: keep filming the dog coming back happy
   var dog = CheckoutPets.Instance;
   if (tapIt && dog && dog.Root && dog.Root.gameObject.activeInHierarchy)
    for (float d0 = Time.realtimeSinceStartup; Time.realtimeSinceStartup - d0 < 5f;) { if (home) home.FocusCinematic(dog.Root.position + Vector3.back * .4f, 3.2f); yield return null; }
   if (!shotsOnly) RecStop();
   var o = bridge.State.security?.lastOutcome; Note($"{name}: outcome={o?.kind} coins={o?.coins} caught={bridge.State.security?.caughtToday} escaped={bridge.State.security?.escapedToday}");
  }
 }
}
