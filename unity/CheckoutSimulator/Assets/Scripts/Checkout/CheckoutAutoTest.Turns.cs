using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "trafficturns[.seconds[.event[.era]]]" (Lucas 26/10: "the cars' turns, at the roundabout and the corners, are locked and jerky"):
 // follows every moving vehicle frame by frame for N game seconds (default 75) and logs, per kind of vehicle,
 //  - slip: the angle between where the body points and where it really moves (a car never slides sideways), max and
 //    95th percentile, forwards and reversing apart;
 //  - yaw rate (deg/s) max, and heading snaps: more than 8 degrees in a single frame;
 //  - the frame times (a long editor frame makes a fair turn look like a snap).
 // An optional event id (e.g. carro-de-som, hora-do-rush; "-" for none) is previewed meanwhile so its vehicles are
 // measured too. An optional era (e.g. supermercado) is set first, with a supplier truck driving in (and off again half
 // way) and two delivery orders whose couriers come, are handed the bags and ride off: put a word with "events" in the
 // request (e.g. "play trafficturns.80.-.supermercado,noevents") so it runs on the QA copy of the save.
 // Pictures (<tag>: the event id, or "city"): frame sequences of a vehicle through the roundabout and round a corner
 // (Logs/turn_<tag>_round_*.jpg, Logs/turn_<tag>_corner_*.jpg) and top-down maps of every driven trail coloured by slip
 // (Logs/turn_<tag>_trails_*.jpg: green under 3 degrees, yellow under 10, red above, cyan reversing).
 public sealed partial class CheckoutAutoTest {
  sealed class TurnTrack { public Vector3 p; public float yaw; public int frame; }
  sealed class TurnStats { public readonly List<float> slip = new List<float>(), back = new List<float>(); public readonly List<float> yaw = new List<float>(); public float yawMax, worstSlip; public int snaps, frames, reversals, dodges, shoved; public string worst = "", worstYaw = ""; public readonly HashSet<Transform> seen = new HashSet<Transform>(); }
  struct TrailDot { public Vector3 p; public float slip; }

  IEnumerator TrafficTurns(string request) {
   var args = request.Split('.');
   float seconds = args.Length > 1 && float.TryParse(args[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var s) && s > 0 ? s : 75;
   string preview = args.Length > 2 && args[2] != "-" ? args[2] : null, era = args.Length > 3 && args[3] != "-" ? args[3] : null;
   string tag = preview ?? "city";   // pictures of each run apart: Logs/turn_<event or city>_*.jpg
   foreach (var f in Directory.GetFiles("Logs", "turn_" + tag + "_*.jpg")) File.Delete(f);
   var fx = FindAnyObjectByType<CheckoutEventVisuals>();
   void Hud(string action, string json) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-" + action + "\",\"action\":\"" + action + "\",\"args\":" + json + "}");
   if (era != null) { Hud("devSetMarketEra", "[\"" + era + "\"]"); yield return new WaitForSecondsRealtime(6); }
   bool opened = false;
   if (bridge.State != null && !bridge.State.isOpen) {
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}"); opened = true;
    for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f);
   }
   if (!string.IsNullOrEmpty(preview) && fx) { fx.Preview(preview); yield return new WaitForSeconds(2f); }
   var trucks = CheckoutDeliveryTrucks.Current; Transform truck = null; bool truckGone = false; float nextOrders = 0, nextCar = 0, nextStatus = 0; int carVisits = 0;
   if (era != null) {
    if (trucks) { truck = trucks.DriveInForReview(); Note("turns: truck " + (truck ? truck.name : "none") + " drives in, yard " + trucks.Kind); }
    for (int i = 0; i < 2; i++) { Hud("devSpawnDeliveryOffer", "[]"); yield return new WaitForSecondsRealtime(.6f); }
   }
   var circle = CheckoutRoundabout.Current;
   var market = FindAnyObjectByType<CheckoutCityTraffic>(); var hood = FindAnyObjectByType<CheckoutNeighborhoodTraffic>();
   Note($"turns: era={bridge.State?.era?.id} open={bridge.State?.isOpen} lot={CheckoutCityTraffic.Lot} roundabout={(circle ? circle.center.ToString() : "none")} preview={preview ?? "-"} timeScale={Time.timeScale}");

   string Kind(Transform t) {
    if (t.GetComponent<CheckoutEventVehicle>()) return "event";
    if (market && market.vehicles != null && System.Array.IndexOf(market.vehicles, t) >= 0) return "market";
    if (hood && hood.cars != null && hood.cars.Any(c => c != null && c.vehicle == t)) return "city";
    if (CheckoutDeliveryTrucks.Current && CheckoutDeliveryTrucks.Current.All.Contains(t)) return "truck";
    if (t.name.StartsWith("Courier")) return "courier";
    return "other";
   }
   var tracks = new Dictionary<Transform, TurnTrack>(); var stats = new Dictionary<string, TurnStats>(); var kinds = new Dictionary<Transform, string>();
   var trail = new List<TrailDot>(); var frameTimes = new List<float>();
   var vehicles = new List<Transform>(); float listedAt = -10;
   int skipUntil = -1; bool roundShot = false, cornerShot = false; int roundFrame = 0, cornerFrame = 0; float nextRound = 0, nextCorner = 0; Transform roundCar = null, cornerCar = null;
   Vector3 cornerAt = Vector3.zero;
   float Yaw(Transform t, bool evt) { var f = evt ? t.right : t.forward; return Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg; }
   for (float t0 = Time.time; Time.time - t0 < seconds;) {
    yield return null;
    float dt = Time.deltaTime; if (dt <= 0) continue;
    if (era != null && Time.time >= nextOrders) {
     // the couriers: accept the offers, hand the bags over once the bike waits at the door (and keep the shop open:
     // its customers' cars are the ones that use the parking lot)
     nextOrders = Time.time + 2f;
     if (bridge.State != null && !bridge.State.isOpen) { Hud("setMarketOpen", "[true]"); opened = true; }
     // a customer who comes by car now and then (into the parking lot, shopping, backing out of the bay)
     if (market && Time.time >= nextCar && CheckoutCityTraffic.Bays > 0) {
      nextCar = Time.time + 7f;
      var idle = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include).FirstOrDefault(w => !w.gameObject.activeSelf && !w.Reserved);
      bool began = idle && market.TryBegin(new Customer { id = "qa-car-" + carVisits, name = "QA", purchases = new Purchase[0] }, idle);
      if (began) carVisits++;
      // the shop may not open on the QA copy (pieces still to place): the drivers come back without shopping, so the
      // backing out of the bays is driven too
      if (market.ParkedVisits > market.CompletedVisits && Time.time - t0 > 14f) { int sent = market.QaSendBack(); if (sent > 0) Note($"turns: {sent} parked car(s) sent off"); }
      if (Time.time >= nextStatus) { nextStatus = Time.time + 15f; Note($"turns: open={bridge.State?.isOpen} car visits begun={carVisits} parked={market.ParkedVisits} done={market.CompletedVisits} orders={string.Join(",", (bridge.State?.delivery?.orders ?? new DeliveryOrder[0]).Where(o => o != null).Select(o => o.status))}"); }
     }
     var orders = bridge.State?.delivery?.orders;
     if (orders != null) foreach (var o in orders) {
      if (o == null) continue;
      if (o.status == "oferta") bridge.Command("acceptDeliveryOrder", "[\"" + o.id + "\"]");
      else if (o.status == "moto-na-porta") bridge.Command("handOverDelivery", "[\"" + o.id + "\"]");
     }
    }
    if (truck && !truckGone && Time.time - t0 > seconds * .5f) { truckGone = true; trucks.EndReview(); Note("turns: the truck drives off"); }
    frameTimes.Add(dt);
    if (Time.time - listedAt > .5f) {
     listedAt = Time.time; vehicles.Clear(); vehicles.AddRange(CheckoutTrafficJunctions.QaVehicles());
     foreach (var v in FindObjectsByType<CheckoutEventVehicle>(FindObjectsSortMode.None)) if (!vehicles.Contains(v.transform)) vehicles.Add(v.transform);
    }
    bool skip = Time.frameCount <= skipUntil;
    foreach (var car in vehicles) {
     if (!car || !car.gameObject.activeInHierarchy) continue;
     if (!kinds.TryGetValue(car, out var kind)) kinds[car] = kind = Kind(car);
     bool evt = kind == "event";
     var p = car.position; p.y = 0; float yaw = Yaw(car, evt);
     if (!tracks.TryGetValue(car, out var tr)) tracks[car] = tr = new TurnTrack { frame = -5 };
     bool fresh = tr.frame != Time.frameCount - 1 || skip;
     var d = p - tr.p; float dist = d.magnitude; float dyaw = Mathf.DeltaAngle(tr.yaw, yaw);
     tr.p = p; tr.yaw = yaw; tr.frame = Time.frameCount;
     if (fresh || dist > 3f) continue;   // just appeared, came back in at a map edge, or a picture was taken
     if (!stats.TryGetValue(kind, out var st)) stats[kind] = st = new TurnStats();
     st.seen.Add(car); st.frames++;
     float rate = Mathf.Abs(dyaw) / dt; st.yaw.Add(rate);
     if (rate > st.yawMax) { st.yawMax = rate; st.worstYaw = $"{car.name}@({p.x:0.0},{p.z:0.0}) {dyaw:0.0}deg in {dt * 1000:0}ms"; }
     if (Mathf.Abs(dyaw) > 8f) { st.snaps++; if (st.snaps <= 6) Note($"TURNS_QA snap {kind} {car.name}@({p.x:0.0},{p.z:0.0}) {dyaw:0.0}deg in {dt * 1000:0}ms speed {dist / dt:0.0}"); }
     if (dist / dt < .3f) continue;   // standing (or creeping): no direction of travel to compare with
     var f = evt ? car.right : car.forward; f.y = 0; f.Normalize();
     float angle = Vector3.Angle(f, d / dist);
     bool back = angle > 90f; float slip = back ? 180f - angle : angle;
     (back ? st.back : st.slip).Add(slip);
     if (!back && slip > st.worstSlip) { st.worstSlip = slip; st.worst = $"{car.name}@({p.x:0.0},{p.z:0.0}) {slip:0.0}deg at {dist / dt:0.0}m/s"; }
     if (trail.Count < 120000 && (Time.frameCount & 1) == 0) trail.Add(new TrailDot { p = p, slip = back ? -slip - 1 : slip });
    }
    if (skip) continue;
    // the frame sequences: a vehicle coming into the roundabout, one coming up to a corner
    if (!roundShot && circle && roundCar == null)
     foreach (var car in vehicles) {
      if (!car || !car.gameObject.activeInHierarchy) continue;
      var off = car.position - circle.center; off.y = 0; var f = kinds.TryGetValue(car, out var k) && k == "event" ? car.right : car.forward; f.y = 0;
      if (off.magnitude > circle.clipRadius + .5f && off.magnitude < circle.clipRadius + 5f && Vector3.Dot(f.normalized, -off.normalized) > .5f) { roundCar = car; nextRound = Time.time; Note($"turns: roundabout sequence follows {car.name}"); break; }
     }
    if (roundCar != null && !roundShot && Time.time >= nextRound) {
     CaptureAt(circle.center + Vector3.up * .5f, 22f, $"turn_{tag}_round_{roundFrame++}"); nextRound = Time.time + .45f; skipUntil = Time.frameCount + 1;
     if (roundFrame >= 9 || !roundCar || !roundCar.gameObject.activeInHierarchy) roundShot = true;
    }
    if (!cornerShot && cornerCar == null)
     foreach (var car in vehicles) {
      // a customer's car turning into the parking lot, or a city car turning off the east street onto the avenue
      if (!car || !car.gameObject.activeInHierarchy || !kinds.TryGetValue(car, out var k)) continue;
      var c = k == "market" ? new Vector3(CheckoutCityTraffic.FrontAisleX, 0, -17) : new Vector3(22.4f, 0, -14);
      var off = c - car.position; off.y = 0;
      bool coming = k == "market" ? off.magnitude < 7f && off.magnitude > 3f && CheckoutCityTraffic.Lot == CheckoutCityTraffic.ParkingLot.Front
       : k != "event" && Mathf.Abs(off.x) < 1f && off.z < -3f && off.z > -7f && car.forward.z < -.7f;
      if (coming) { cornerCar = car; cornerAt = c; nextCorner = Time.time; Note($"turns: corner sequence follows {car.name} at {c}"); break; }
     }
    if (cornerCar != null && !cornerShot && Time.time >= nextCorner) {
     CaptureAt(cornerAt + Vector3.up * .5f, 15f, $"turn_{tag}_corner_{cornerFrame++}"); nextCorner = Time.time + .4f; skipUntil = Time.frameCount + 1;
     if (cornerFrame >= 8 || !cornerCar || !cornerCar.gameObject.activeInHierarchy) cornerShot = true;
    }
   }
   if (!string.IsNullOrEmpty(preview) && fx) fx.Preview("");
   if (truck && !truckGone) trucks.EndReview();
   if (opened) CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-close\",\"action\":\"setMarketOpen\",\"args\":[false]}");

   float P95(List<float> l) { if (l.Count == 0) return 0; var a = l.ToArray(); System.Array.Sort(a); return a[Mathf.Min(a.Length - 1, (int)(a.Length * .95f))]; }
   float Max(List<float> l) => l.Count == 0 ? 0 : l.Max();
   // (the max yaw rate is noisy: a vehicle moved by a coroutine that ran before this one in one frame and after it in the
   // next shows two frames of turning over one frame time; the 99th percentile is the honest figure)
   float P99(List<float> l) { if (l.Count == 0) return 0; var a = l.ToArray(); System.Array.Sort(a); return a[Mathf.Min(a.Length - 1, (int)(a.Length * .99f))]; }
   int Over(List<float> l, float x) => l.Count(v => v > x);
   var all = new TurnStats();
   foreach (var pair in stats.OrderBy(q => q.Key)) {
    var st = pair.Value; all.slip.AddRange(st.slip); all.yaw.AddRange(st.yaw); all.back.AddRange(st.back); all.snaps += st.snaps; all.yawMax = Mathf.Max(all.yawMax, st.yawMax); all.frames += st.frames;
    Note($"TURNS_QA {pair.Key}: vehicles={st.seen.Count} frames={st.frames} moving={st.slip.Count} slipMax={Max(st.slip):0.0} slipP95={P95(st.slip):0.0} slipOver3={Over(st.slip, 3)} reverseFrames={st.back.Count} reverseSlipMax={Max(st.back):0.0} yawRateMax={st.yawMax:0} yawRateP99={P99(st.yaw):0} snaps>8deg={st.snaps}");
    if (st.worst != "") Note($"TURNS_QA {pair.Key} worst slip: {st.worst}; fastest yaw: {st.worstYaw}");
    foreach (var car in st.seen.Take(1)) Note($"TURNS_QA {pair.Key} body: {CheckoutTrafficJunctions.QaBody(car)} scale {car.lossyScale.x:0.00}");
   }
   Note($"TURNS_QA all {seconds:0}s: moving frames={all.slip.Count} slipMax={Max(all.slip):0.0} slipP95={P95(all.slip):0.0} slipOver3={Over(all.slip, 3)} ({(all.slip.Count > 0 ? 100f * Over(all.slip, 3) / all.slip.Count : 0):0.0}%) reverseSlipMax={Max(all.back):0.0} yawRateMax={all.yawMax:0} yawRateP99={P99(all.yaw):0} snaps>8deg={all.snaps} frame ms p95={P95(frameTimes) * 1000:0} max={Max(frameTimes) * 1000:0}");
   // top-down maps of the trails (where they run against the kerbs and lanes, and how much they slip)
   void Trails(string name, Vector3 center, float size) {
    var go = new GameObject("QA trail camera"); var cam = go.AddComponent<Camera>();
    cam.orthographic = true; cam.orthographicSize = size * .5f; cam.aspect = 1; go.transform.position = center + Vector3.up * 80; go.transform.rotation = Quaternion.Euler(90, 0, 0);
    cam.nearClipPlane = 1; cam.farClipPlane = 200; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(.2f, .2f, .2f);
    const int px = 1024; var rt = new RenderTexture(px, px, 24) { antiAliasing = 4 }; cam.targetTexture = rt; cam.Render();
    var active = RenderTexture.active; RenderTexture.active = rt; var image = new Texture2D(px, px, TextureFormat.RGB24, false); image.ReadPixels(new Rect(0, 0, px, px), 0, 0); RenderTexture.active = active;
    foreach (var dot in trail) {
     var sp = cam.WorldToScreenPoint(dot.p + Vector3.up * .15f); int x = (int)sp.x, y = (int)sp.y; if (x < 1 || y < 1 || x >= px - 1 || y >= px - 1) continue;
     var c = dot.slip < 0 ? Color.cyan : dot.slip < 3 ? Color.green : dot.slip < 10 ? Color.yellow : Color.red;
     for (int a = -1; a <= 1; a++) for (int b = -1; b <= 1; b++) image.SetPixel(x + a, y + b, c);
    }
    image.Apply(); File.WriteAllBytes("Logs/" + name + ".jpg", image.EncodeToJPG(88)); Destroy(image); cam.targetTexture = null; rt.Release(); Destroy(rt); Destroy(go); Note("shot " + name);
   }
   Trails($"turn_{tag}_trails_avenue", new Vector3(0, 0, -12), 64);
   if (circle) Trails($"turn_{tag}_trails_roundabout", circle.center, 24);
   Trails($"turn_{tag}_trails_lot", CheckoutCityTraffic.Lot == CheckoutCityTraffic.ParkingLot.Back ? new Vector3(16, 0, 18) : new Vector3(13, 0, -7), 26);
   Trails($"turn_{tag}_trails_east", new Vector3(23.5f, 0, -12), 22);
  }
 }
}
