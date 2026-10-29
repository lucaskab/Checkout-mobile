using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 // "walkturns[.seconds[.era[.event[.label]]]]" (Lucas 26/10: "the people walking in the street and the people on bicycles also turn all
 // at once, it isn't smooth"): like trafficturns, for everyone on foot outside the shop (passers-by, customers walking
 // to and from the shop, passengers dropped off, event people, the delivery worker) and every cyclist. Per kind:
 //  - slip: the angle between where the body faces and where it really moves (walking sideways), max and 95th percentile;
 //  - yaw rate (deg/s) max and 99th percentile, also standing (turning on the spot), and heading snaps: more than 20
 //    degrees in a single frame;
 //  - turn reversals (Lucas 26/10 21:01: "they start to turn, go back to the angle they had, walk a bit and then turn"):
 //    walking, a turn one way (over 25 deg/s) followed within half a second by a turn the other way;
 //  - the frame times.
 // Customers are sent walking to the shop now and then (on the QA copy of the save: put a word with "events" in the
 // request, e.g. "play walkturns.80,noevents"). Pictures (Logs/walk_*): frame sequences of a person turning a corner and
 // of a cyclist (walk_person_*.jpg, walk_bike_*.jpg) and top-down trail maps coloured by slip (walk_trails_*.jpg).
 public sealed partial class CheckoutAutoTest {
  IEnumerator WalkTurns(string request) {
   var args = request.Split('.');
   float seconds = args.Length > 1 && float.TryParse(args[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var s) && s > 0 ? s : 75;
   string era = args.Length > 2 && args[2] != "-" ? args[2] : null, preview = args.Length > 3 && args[3] != "-" ? args[3] : null;
   var fx = FindAnyObjectByType<CheckoutEventVisuals>();
   string tag = args.Length > 4 ? args[4] : preview ?? "street";   // pictures of each run apart: Logs/walk_<event or street>_*.jpg
   foreach (var f in Directory.GetFiles("Logs", "walk_" + tag + "_*.jpg")) File.Delete(f);

   void Hud(string action, string json) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-" + action + "\",\"action\":\"" + action + "\",\"args\":" + json + "}");
   if (era != null) { Hud("devSetMarketEra", "[\"" + era + "\"]"); yield return new WaitForSecondsRealtime(6); }
   if (bridge.State != null && !bridge.State.isOpen) { Hud("setMarketOpen", "[true]"); yield return new WaitForSecondsRealtime(2); }
   if (preview != null && fx) { fx.Preview(preview); yield return new WaitForSeconds(2f); }
   var cyclists = FindAnyObjectByType<CheckoutPlazaCyclists>();
   Note($"walks: event={preview ?? "-"} era={bridge.State?.era?.id} open={bridge.State?.isOpen} cyclists={(cyclists ? "yes" : "no")} timeScale={Time.timeScale}");

   // who is who, and which way each faces (the city's characters face their holder's -Z, the bikes and the delivery worker +Z)
   var kinds = new Dictionary<Transform, string>(); var back = new HashSet<Transform>();
   string Kind(Transform t) {
    if (t.GetComponent<CheckoutCityPedestrian>()) return "pedestrian";
    if (t.GetComponent<CheckoutWalker>()) return "customer";
    if (t.GetComponent<CheckoutEventActor>()) return "event person";
    if (t.GetComponent<MarketDay.MarketDeliveryWorker>()) return "delivery worker";
    if (t.GetComponent<NavMeshAgent>()) return "passenger";
    return "bike";
   }
   var tracks = new Dictionary<Transform, TurnTrack>(); var stats = new Dictionary<string, TurnStats>();
   var trail = new List<TrailDot>(); var turning = new Dictionary<Transform, Vector2>(); var frameTimes = new List<float>(); var people = new List<Transform>(); var bikes = new List<Transform>();
   float listedAt = -10, nextVisit = 0; int visits = 0, skipUntil = -1, reversed = 0, offs = 0;
   Transform personCar = null, bikeCar = null; int personFrame = 0, bikeFrame = 0; float nextPerson = 0, nextBike = 0;
   var corners = new Vector3[64];
   for (float t0 = Time.time; Time.time - t0 < seconds;) {
    yield return null;
    float dt = Time.deltaTime; if (dt <= 0) continue;
    frameTimes.Add(dt);
    // a customer walking in now and then (they come from a corner of the city, shop and walk away)
    if (Time.time >= nextVisit) {
     nextVisit = Time.time + 6f;
     var idle = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include).FirstOrDefault(w => !w.gameObject.activeSelf && !w.Reserved);
     if (idle && visits < 8) { idle.Begin(new Customer { id = "qa-walk-" + visits, name = "QA", purchases = new Purchase[0] }); visits++; }
    }
    if (Time.time - listedAt > .5f) {
     listedAt = Time.time; people.Clear(); bikes.Clear();
     foreach (var a in FindObjectsByType<NavMeshAgent>(FindObjectsInactive.Exclude)) if (a.isActiveAndEnabled) people.Add(a.transform);
     foreach (var a in FindObjectsByType<CheckoutEventActor>(FindObjectsInactive.Exclude)) if (a.Visible) people.Add(a.transform);
     foreach (var a in FindObjectsByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Exclude)) people.Add(a.transform);
     if (cyclists) cyclists.QaBikes(bikes);
    }
    bool skip = Time.frameCount <= skipUntil;
    for (int list = 0; list < 2; list++)
     foreach (var who in list == 0 ? people : bikes) {
      if (!who || !who.gameObject.activeInHierarchy) continue;
      if (!kinds.TryGetValue(who, out var kind)) { kinds[who] = kind = list == 1 ? "bike" : Kind(who); if (kind == "bike" || kind == "delivery worker") back.Add(who); }
      // inside a building (a passer-by visiting one, invisible) or the customer's shopping, queue and till: not counted
      var at = who.position;
      if ((kind == "customer" && !who.GetComponent<CheckoutWalker>().OutdoorWalk) || (kind == "pedestrian" && who.GetComponent<CheckoutCityPedestrian>().IsSheltered)) { tracks.Remove(who); continue; }
      var f = back.Contains(who) ? who.forward : -who.forward; f.y = 0; if (f.sqrMagnitude < 1e-6f) continue; f.Normalize();
      var p = at; p.y = 0; float yaw = Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg;
      if (!tracks.TryGetValue(who, out var tr)) tracks[who] = tr = new TurnTrack { frame = -5 };
      bool fresh = tr.frame != Time.frameCount - 1 || skip;
      var d = p - tr.p; float dist = d.magnitude, dyaw = Mathf.DeltaAngle(tr.yaw, yaw);
      tr.p = p; tr.yaw = yaw; tr.frame = Time.frameCount;
      if (fresh || dist > 2f) continue;   // just appeared / warped, or a picture was taken
      if (!stats.TryGetValue(kind, out var st)) stats[kind] = st = new TurnStats();
      st.seen.Add(who); st.frames++;
      float rate = Mathf.Abs(dyaw) / dt; st.yaw.Add(rate);
      if (rate > st.yawMax) { st.yawMax = rate; st.worstYaw = $"{who.name}@({p.x:0.0},{p.z:0.0}) {dyaw:0.0}deg in {dt * 1000:0}ms at {dist / dt:0.00}m/s"; }
      // a turn one way, then (within half a second) the other way
      float signed = dyaw / dt;
      if (Mathf.Abs(signed) > 25f && dist / dt > .3f) {
       if (turning.TryGetValue(who, out var before) && Time.time - before.y < .5f && Mathf.Sign(before.x) != Mathf.Sign(signed)) { st.reversals++; if (st.reversals <= 6) Note($"WALK_QA reversal {kind} {who.name}@({p.x:0.0},{p.z:0.0}) {before.x:0}deg/s then {signed:0}deg/s"); }
       turning[who] = new Vector2(signed, Time.time);
      }
      if (Mathf.Abs(dyaw) > 20f) { st.snaps++; if (st.snaps <= 6) Note($"WALK_QA snap {kind} {who.name}@({p.x:0.0},{p.z:0.0}) {dyaw:0.0}deg in {dt * 1000:0}ms speed {dist / dt:0.00}"); }
      if (dist / dt < .3f) continue;   // standing, shuffling: no direction of travel to compare with
      float slip = Vector3.Angle(f, d / dist);
      st.slip.Add(slip);
      if (slip > 10f && slip < 40f && kind == "customer" && offs++ < 12) { var ag = who.GetComponent<NavMeshAgent>(); Note($"WALK_QA off {kind} {who.name} phase {who.GetComponent<CheckoutWalker>().VisitPhase} @({p.x:0.00},{p.z:0.00}) moved {(d / dt):F2} faces {f:F2} desired {ag.desiredVelocity:F2} velocity {ag.velocity:F2} next {ag.nextPosition:F2} dt {dt * 1000:0}ms frame {Time.frameCount}"); }
      if (slip > 150f && reversed++ < 4) { var ag = who.GetComponent<NavMeshAgent>(); Note($"WALK_QA backwards {kind} {who.name}@({p.x:0.0},{p.z:0.0}) moved {(d / dt):F2} faces {f:F2}" + (ag ? $" desired {ag.desiredVelocity:F2} velocity {ag.velocity:F2} stopped {ag.isStopped} steering {ag.steeringTarget:F1}" : "")); }
      if (slip > st.worstSlip) { st.worstSlip = slip; st.worst = $"{who.name}@({p.x:0.0},{p.z:0.0}) {slip:0.0}deg at {dist / dt:0.00}m/s"; }
      if (trail.Count < 150000 && (Time.frameCount & 1) == 0) trail.Add(new TrailDot { p = p, slip = slip });
     }
    if (skip) continue;
    // a person coming up to a corner of their way (the next corner of the path turns by more than 45 degrees)
    if (personCar == null && personFrame == 0)
     foreach (var who in people) {
      if (!who || !kinds.TryGetValue(who, out var k) || (k != "pedestrian" && k != "customer" && k != "passenger")) continue;
      var agent = who.GetComponent<NavMeshAgent>(); if (!agent || !agent.hasPath || agent.isStopped || agent.velocity.sqrMagnitude < .3f) continue;
      int n = agent.path.GetCornersNonAlloc(corners); if (n < 3) continue;
      var a = corners[1] - corners[0]; var b = corners[2] - corners[1]; a.y = b.y = 0;
      if (a.magnitude < 1.2f || a.magnitude > 3f || b.magnitude < 1.5f || Vector3.Angle(a, b) < 45f) continue;
      personCar = who; nextPerson = Time.time; Note($"walks: person sequence follows {who.name} ({k}), corner at {corners[1]}"); break;
     }
    if (personCar && personFrame < 10 && Time.time >= nextPerson) {
     CaptureAt(personCar.position + Vector3.up * .9f, 6f, $"walk_{tag}_person_{personFrame++}"); nextPerson = Time.time + .3f; skipUntil = Time.frameCount + 1;
     if (!personCar.gameObject.activeInHierarchy) personFrame = 10;
    }
    if (bikeCar == null && bikeFrame == 0) foreach (var b in bikes) if (b && b.gameObject.activeInHierarchy) { bikeCar = b; nextBike = Time.time; Note($"walks: bike sequence follows {b.name}"); break; }
    if (bikeCar && bikeFrame < 10 && Time.time >= nextBike) {
     CaptureAt(bikeCar.position + Vector3.up * .8f, 9f, $"walk_{tag}_bike_{bikeFrame++}"); nextBike = Time.time + .4f; skipUntil = Time.frameCount + 1;
     if (!bikeCar.gameObject.activeInHierarchy) bikeFrame = 10;
    }
   }
   if (preview != null && fx) fx.Preview("");
   float P(List<float> l, float q) { if (l.Count == 0) return 0; var a = l.ToArray(); System.Array.Sort(a); return a[Mathf.Min(a.Length - 1, (int)(a.Length * q))]; }
   float Max(List<float> l) => l.Count == 0 ? 0 : l.Max();
   int Over(List<float> l, float x) => l.Count(v => v > x);
   foreach (var pair in stats.OrderBy(q => q.Key)) {
    var st = pair.Value;
    Note($"WALK_QA {pair.Key}: count={st.seen.Count} frames={st.frames} moving={st.slip.Count} slipMax={Max(st.slip):0.0} slipP95={P(st.slip, .95f):0.0} slipOver10={Over(st.slip, 10)} yawRateMax={st.yawMax:0} yawRateP99={P(st.yaw, .99f):0} snaps>20deg={st.snaps} turnReversals={st.reversals}");
    if (st.worst != "") Note($"WALK_QA {pair.Key} worst slip: {st.worst}; fastest yaw: {st.worstYaw}");
   }
   Note($"WALK_QA {seconds:0}s frame ms p95={P(frameTimes, .95f) * 1000:0} max={Max(frameTimes) * 1000:0} customers sent={visits}");
   TrailMap(trail, $"walk_{tag}_trails_avenue", new Vector3(0, 0, -12), 64);
   TrailMap(trail, $"walk_{tag}_trails_front", new Vector3(0, 0, -9), 24);
   TrailMap(trail, $"walk_{tag}_trails_park", new Vector3(0, 0, -32), 40);
   TrailMap(trail, $"walk_{tag}_trails_roundabout", new Vector3(-23.5f, 0, -18.5f), 28);
  }

  // A top-down picture of the trails, each dot coloured by its slip (green < 3, yellow < 10, red above, cyan reversing).
  void TrailMap(List<TrailDot> trail, string name, Vector3 center, float size) {
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
 }
}
