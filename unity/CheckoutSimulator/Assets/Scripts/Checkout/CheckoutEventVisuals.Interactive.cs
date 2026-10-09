using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;
using UnityEngine.AI;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout {
 // What the player does during two events (Oct 2026; rules in src/services/event-interactions.ts, read from the
 // snapshot's event: interaction, stops, seal, windowRequests):
 // - Vigilância sanitária: the inspector (EventRigs/Inspector, a white lab coat over a market character, clipboard and
 //   pen in her hands) gets out of the car, walks into the market to each of her three stops and waits next to the
 //   mishap the app created there (a floating magnifier marks it; clicking the mishap's own bubble opens its
 //   mini-game). Fixed: she stamps and nods; missed: she shakes her head and writes. At the end she hangs the green
 //   seal on the shop front (3/3) or leaves the yellow warning / red fine notice on the door.
 // - Engarrafamento, venda pela janela: a jammed car with a driver (EventRigs/Rig_JamCar) honks, winds its window
 //   down and its driver waves a hand out; a bubble over the roof shows the drink he wants (grey when the market has
 //   none). A click sells it (serveWindowSale) and the stock clerk walks out with the cooler (EventRigs/Rig_Cooler on
 //   his hip), opens it, hands the bottle through the window and takes the coins; the window goes up and the car
 //   moves on.
 // Both live outside the event's scene (so the inspector can finish her round after the visit's clock ends).
 public sealed partial class CheckoutEventVisuals {
  CheckoutBridge bridgeRef; Transform playRoot;
  CheckoutBridge Bridge => bridgeRef ? bridgeRef : (bridgeRef = GetComponent<CheckoutBridge>() ?? FindAnyObjectByType<CheckoutBridge>());
  Transform PlayRoot {
   get {
    if (!playRoot) { var go = new GameObject("Event interactions"); go.transform.SetParent(transform, false); WorldAligned(go.transform); playRoot = go.transform; }
    return playRoot;
   }
  }
  CheckoutMap Map => GetComponent<CheckoutMap>() ?? FindAnyObjectByType<CheckoutMap>();
  Vector3 DoorPoint { get { var m = Map; return m ? m.Entrance : new Vector3(-1.75f, .2f, -8.7f); } }

  void Interactive() {
   var ev = previewing ? null : Bridge?.State?.@event;
   bool live = ev != null && !string.IsNullOrEmpty(active) && ev.id == active && ev.endsAt > DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
   try {
    InspectionTick(live && ev.interaction == "inspection" ? ev : null);
    SealTick(ev != null && ev.seal);
    WindowTick(live && ev.interaction == "window-sales" ? ev : null);
   } catch (Exception e) { if (!interactiveErrorLogged) { interactiveErrorLogged = true; Debug.LogException(e); } }
  }
  bool interactiveErrorLogged;

  void ClearInteractive() { if (playRoot) Destroy(playRoot.gameObject); inspector = null; vendor = null; windowCars.Clear(); serveQueue.Clear(); }

  // ---------------------------------------------------------------- shared helpers
  static Transform MarketCharacter(string name) {
   var sim = FindAnyObjectByType<MarketSimulation>();
   return sim && sim.world ? sim.world.Find(name) : null;
  }
  static Vector3 Flat(Vector3 v) { v.y = 0; return v; }
  /// <summary>A walking route over the NavMesh (the shop floor goes round the shelves); straight when there is none.</summary>
  static List<Vector3> Route(Vector3 from, Vector3 to) {
   var path = new NavMeshPath();
   if (NavMesh.SamplePosition(from, out var a, 1.5f, NavMesh.AllAreas) && NavMesh.SamplePosition(to, out var b, 1.5f, NavMesh.AllAreas)
     && NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, path) && path.status != NavMeshPathStatus.PathInvalid && path.corners.Length > 0)
    return path.corners.ToList();
   return new List<Vector3> { from, to };
  }
  // A prop held in a bone: keeps its size in metres whatever the character's import scale.
  Transform Hold(Transform bone, string model, Vector3 offset, Vector3 euler, float size = 1) {
   var t = art.Prop2(PlayRoot, model, Vector3.zero, 0, 1);
   if (!bone) return t;
   t.SetParent(bone, false);
   var s = bone.lossyScale; t.localScale = new Vector3(size / Mathf.Max(1e-4f, s.x), size / Mathf.Max(1e-4f, s.y), size / Mathf.Max(1e-4f, s.z));
   t.localPosition = new Vector3(offset.x / Mathf.Max(1e-4f, s.x), offset.y / Mathf.Max(1e-4f, s.y), offset.z / Mathf.Max(1e-4f, s.z));
   t.rotation = Quaternion.Euler(euler);
   return t;
  }
  static void Reparent(Transform t, Transform bone) {
   if (!t || !bone) return;
   var size = t.lossyScale; t.SetParent(bone, true);
   var s = bone.lossyScale; t.localScale = new Vector3(size.x / Mathf.Max(1e-4f, s.x), size.y / Mathf.Max(1e-4f, s.y), size.z / Mathf.Max(1e-4f, s.z));
   t.localPosition = Vector3.zero;
  }
  static IEnumerator Pop(Transform t, bool show, float seconds = .25f) {
   if (!t) yield break;
   var home = t.localScale.sqrMagnitude > 1e-6f ? t.localScale : Vector3.one;
   for (float k = 0; k < seconds; k += Time.deltaTime) { if (!t) yield break; float u = k / seconds; t.localScale = home * (show ? Mathf.Sin(u * Mathf.PI * .6f) / Mathf.Sin(Mathf.PI * .6f) : 1 - u); yield return null; }
   if (t) t.localScale = show ? home : Vector3.zero;
  }

  // A clip of a rig on its own layer, only on some of its bones (the rig clips key every bone): the window, the
  // driver and the body play at the same time without fighting.
  static AnimationState Layer(Animation anim, Transform rig, string clip, string part, int layer, string bone, bool recursive) {
   if (!anim) return null;
   var name = clip + "@" + part; var s = anim[name];
   if (!s) {
    var source = CheckoutEventAssets.ClipState(anim, clip); if (source == null) { Debug.LogWarning("CHECKOUT_EVENT_CLIP_MISSING " + clip); return null; }
    anim.AddClip(source.clip, name); s = anim[name]; s.layer = layer;
    var b = CheckoutEventAssets.Bone(rig, bone); if (b) s.AddMixingTransform(b, recursive);
   }
   return s;
  }
  static float PlayLayer(Animation anim, Transform rig, string clip, string part, int layer, string bone, bool recursive, WrapMode wrap) {
   var s = Layer(anim, rig, clip, part, layer, bone, recursive); if (!s) return 0;
   s.wrapMode = wrap; s.speed = 1; s.time = 0; s.weight = 1;
   anim.Play(s.name, PlayMode.StopSameLayer);
   return s.length;
  }

  // ================================================================ vigilância sanitária
  sealed class InspectorRig {
   public Transform holder, template; public Animation anim; public CheckoutEventActor actor; public CheckoutClipRetarget body;
   public readonly Dictionary<string, Renderer[]> held = new Dictionary<string, Renderer[]>();
   public Transform marker; public string key; public bool done; public Coroutine run;
  }
  InspectorRig inspector; MarketEvent inspection; InspectionStop[] lastStops;
  // over the mishap's own bubble (CheckoutIncidents puts it 2.7 m over the floor)
  const float MarkerHeight = 4.25f;
  Transform sealProp, noticeProp; float sealHungUntil = -1, noticeUntil;

  void InspectionTick(MarketEvent ev) {
   inspection = ev;
   if (ev?.stops != null && ev.stops.Length > 0) lastStops = ev.stops;
   if (ev != null) {
    var key = ev.id + "|" + (ev.stops != null && ev.stops.Length > 0 ? ev.stops[0].at.ToString("0") : "");
    if (inspector == null || (inspector.key != key && inspector.done)) {
     if (inspector != null && inspector.holder) Destroy(inspector.holder.gameObject);
     inspector = SpawnInspector(key);
    }
   }
   if (inspector != null && inspector.marker) {
    var m = inspector.marker; m.localPosition = new Vector3(m.localPosition.x, MarkerHeight + Mathf.Sin(Time.time * 2.2f) * .08f, m.localPosition.z);
    m.localRotation = Quaternion.Euler(0, Time.time * 50f, 0);
   }
   if (noticeProp) { bool on = Time.time < noticeUntil; if (noticeProp.gameObject.activeSelf != on) noticeProp.gameObject.SetActive(on); }
  }

  InspectorRig SpawnInspector(string key) {
   var template = MarketCharacter("Customer_07") ?? MarketCharacter("Customer_01");
   var start = inspectionCurb.sqrMagnitude > 1 ? inspectionCurb : DoorPoint + new Vector3(-3f, 0, -3.5f);
   var holder = art.Rig(PlayRoot, "Inspector", start, 0, 1);
   holder.gameObject.name = "Inspector";
   // the Inspector rig faces its holder's +Z; the walkers expect the market characters' -Z (or he walks backwards)
   var model = holder.Find("Inspector model"); if (model) model.localRotation = Quaternion.Euler(0, 180, 0) * model.localRotation;
   var anim = CheckoutEventAssets.RigAnimation(holder);
   var rig = new InspectorRig { holder = holder, template = template, anim = anim, key = key };
   foreach (var r in holder.GetComponentsInChildren<Renderer>(true)) {
    int cut = r.name.IndexOf("__Held", StringComparison.Ordinal); if (cut < 0) continue;
    var prop = r.name.Substring(0, cut);
    rig.held[prop] = rig.held.TryGetValue(prop, out var list) ? list.Append(r).ToArray() : new[] { r };
   }
   if (anim) {
    rig.body = CheckoutClipRetarget.Play(anim.gameObject, template, "Idle", 1, .01f);
    if (rig.body) holder.localScale = Vector3.one * rig.body.SizeRatio;   // as tall as the city's people
   }
   rig.actor = CheckoutEventActor.Of(holder);
   rig.actor.Face(Vector3.forward); rig.actor.Show(false);
   Held(rig, null);
   rig.run = StartCoroutine(InspectorRound(rig));
   return rig;
  }

  // What is in her hands for each move: the clipboard always; the pen while writing and walking, the stamp to
  // stamp, the seal to hang it.
  static void Held(InspectorRig i, string clip) {
   bool stamp = clip == "Inspect_Stamp", seal = clip == "Inspect_HangSeal", free = stamp || seal || clip == "Inspect_Approve";
   void Set(string prop, bool on) { if (i.held.TryGetValue(prop, out var rs)) foreach (var r in rs) if (r) r.enabled = on; }
   Set("Inspect_Clipboard", true); Set("Inspect_Pen", !free); Set("Inspect_Stamp", stamp); Set("Inspect_Seal", seal);
  }

  IEnumerator Act(InspectorRig i, string clip, float hold = 0) {
   if (!i.anim) yield break;
   Held(i, clip);
   if (i.body) i.body.FadeOut(.25f);
   var s = CheckoutEventAssets.PlayClip(i.anim, clip, WrapMode.ClampForever);
   if (s == null) yield break;
   yield return new WaitForSeconds(s.length + hold);
  }
  void Body(InspectorRig i, string clip) {
   Held(i, null);
   if (!i.anim) return;
   var r = CheckoutClipRetarget.Play(i.anim.gameObject, i.template, clip, 1, .25f);
   if (r) i.body = r;
  }
  IEnumerator WalkTo(InspectorRig i, Vector3 to, float speed = 1.15f) {
   if (!i.holder) yield break;
   Body(i, "Walking");
   yield return new WaitForSeconds(.1f);
   if (i.anim) i.anim.Stop();
   yield return i.actor.Walk(Route(i.holder.position, to), speed);
   Body(i, "Idle");
  }

  InspectionStop StopById(string id) => (inspection?.stops ?? lastStops ?? Array.Empty<InspectionStop>()).FirstOrDefault(s => s.id == id);

  IEnumerator InspectorRound(InspectorRig i) {
   var door = DoorPoint;
   var inside = door + Vector3.forward * 1.4f;
   yield return i.actor.Fade(true);
   yield return WalkTo(i, door);
   yield return WalkTo(i, inside);
   while (true) {
    var stops = inspection?.stops ?? lastStops;
    if (inspection == null || stops == null) break;
    var open = stops.FirstOrDefault(s => s.status == "open" && !string.IsNullOrEmpty(s.shelfId));
    if (open != null) { yield return Visit(i, open.id, open.shelfId); continue; }
    if (stops.Length > 0 && stops.All(s => s.status == "fixed" || s.status == "failed")) break;
    yield return Act(i, "Inspect_LookAround");
    Body(i, "Idle"); yield return new WaitForSeconds(.6f);
   }
   // the verdict, at the door
   var final = inspection?.stops ?? lastStops ?? Array.Empty<InspectionStop>();
   if (final.Length == 0) { yield return i.actor.Fade(false); i.done = true; yield break; }
   int fixedCount = final.Count(s => s.status == "fixed"), total = Mathf.Max(1, final.Length);
   string grade = fixedCount >= total ? "approved" : fixedCount == total - 1 ? "warning" : "fined";
   yield return WalkTo(i, door + Vector3.back * .9f);
   i.actor.Face(Vector3.forward);
   if (grade == "approved") {
    yield return Act(i, "Inspect_HangSeal");
    sealHungUntil = Time.time + 30f;   // until the app's own flag (set when the visit ends) takes over
    i.actor.Face(Vector3.back);
    yield return Act(i, "Inspect_Approve");
   } else {
    yield return Act(i, "Inspect_Write");
    ShowNotice(grade == "fined" ? "Inspect_FineNotice" : "Inspect_WarningNotice");
    i.actor.Face(Vector3.back);
    yield return Act(i, "Inspect_HeadShake");
   }
   // back to the car
   var curb = inspectionCurb.sqrMagnitude > 1 ? inspectionCurb : door + new Vector3(-3f, 0, -3.5f);
   Body(i, "Walking"); yield return new WaitForSeconds(.1f); if (i.anim) i.anim.Stop();
   yield return i.actor.Walk(new[] { door + Vector3.back * 1.6f, new Vector3(curb.x, door.y, door.z - 2.2f), curb }, 1.2f);
   yield return i.actor.Fade(false);
   i.done = true;
  }

  IEnumerator Visit(InspectorRig i, string stopId, string shelfId) {
   var map = Map; if (!map) yield break;
   var spot = map.Approach(shelfId);
   // she stands a step beside the mishap (between it and where she comes from) so its bubble stays clickable
   var from = Flat(i.holder.position - spot); if (from.sqrMagnitude < .01f) from = Vector3.back;
   var stand = spot + from.normalized * 1.15f;
   if (NavMesh.SamplePosition(stand, out var hit, 1f, NavMesh.AllAreas)) stand = hit.position;
   if (!i.marker) { i.marker = art.Prop2(PlayRoot, "Inspect_Marker", spot, 0, 1.6f); }
   i.marker.position = new Vector3(spot.x, MarkerHeight, spot.z); i.marker.gameObject.SetActive(true);
   StartCoroutine(Pop(i.marker, true));
   yield return WalkTo(i, stand);
   i.actor.FaceTowards(spot);
   yield return Act(i, "Inspect_Point");
   bool write = true;
   while (StopById(stopId)?.status == "open" && inspection != null) {
    yield return Act(i, write ? "Inspect_Write" : "Inspect_LookAround");
    write = !write;
   }
   var status = StopById(stopId)?.status;
   yield return Pop(i.marker, false);
   if (i.marker) { i.marker.gameObject.SetActive(false); i.marker.localScale = Vector3.one * 1.6f; }
   i.actor.FaceTowards(spot);
   if (status == "fixed") { yield return Act(i, "Inspect_Stamp"); yield return Act(i, "Inspect_Approve"); }
   else { yield return Act(i, "Inspect_HeadShake"); yield return Act(i, "Inspect_Write"); }
   Body(i, "Idle");
  }

  // The green seal on the shop front, next to the door, for the rest of the turn.
  Vector3 FrontSpot(float side) {
   var door = DoorPoint; float z = Mathf.Max(-8.6f, door.z - .25f);
   return new Vector3(door.x + side, door.y + 1.45f, z - .07f);
  }
  void SealTick(bool fromApp) {
   bool on = fromApp || Time.time < sealHungUntil;
   if (on && !sealProp) { sealProp = art.Prop2(PlayRoot, "Inspect_Seal", FrontSpot(1.25f), 0, 1.6f); StartCoroutine(Pop(sealProp, true, .35f)); }
   if (sealProp) { sealProp.position = FrontSpot(1.25f); if (sealProp.gameObject.activeSelf != on) sealProp.gameObject.SetActive(on); }
  }
  void ShowNotice(string model) {
   if (noticeProp) Destroy(noticeProp.gameObject);
   noticeProp = art.Prop2(PlayRoot, model, FrontSpot(-1.25f), 0, 1.6f);
   noticeUntil = Time.time + 75f;
   StartCoroutine(Pop(noticeProp, true, .35f));
  }

  // ================================================================ engarrafamento: venda pela janela
  sealed class WindowCar {
   public string id, status; public JamCar jam; public Transform rig; public Animation anim;
   public Transform bubble, horn, icon; public SpriteRenderer iconSprite; public Renderer[] face; public BoxCollider hit; public CheckoutTarget target;
   public bool serving, released; public int productId; public string productName; public Transform drink;
  }
  readonly Dictionary<string, WindowCar> windowCars = new Dictionary<string, WindowCar>();
  readonly Queue<WindowCar> serveQueue = new Queue<WindowCar>();
  CheckoutEventActor vendor; Transform cooler; Animation coolerAnim; bool vendorRunning;

  void WindowTick(MarketEvent ev) {
   var requests = ev?.windowRequests ?? Array.Empty<WindowRequest>();
   foreach (var r in requests) {
    if (!windowCars.TryGetValue(r.id, out var wc)) {
     if (r.status != "waiting") continue;
     var car = PickCar(r); if (car == null) continue;
     wc = new WindowCar { id = r.id, jam = car, rig = car.car.transform, anim = CheckoutEventAssets.RigAnimation(car.car.transform), productId = r.productId, productName = r.productName };
     windowCars[r.id] = wc; car.car.Hold = true;
     StartCoroutine(CarAsks(wc));
    }
    wc.status = r.status;
    if (wc.bubble) Paint(wc, r.inStock);
    if (r.status == "missed" && !wc.serving && !wc.released) StartCoroutine(Release(wc));
   }
   foreach (var wc in windowCars.Values.ToList()) {
    bool listed = requests.Any(r => r.id == wc.id);
    if ((!listed || ev == null) && !wc.serving && !wc.released) StartCoroutine(Release(wc));
    if (wc.released && wc.bubble == null) windowCars.Remove(wc.id);
    if (wc.bubble) {
     var top = wc.rig ? wc.rig.position : wc.bubble.position;
     wc.bubble.position = top + Vector3.up * (2.45f + Mathf.Sin(Time.time * 3f + wc.id.Length) * .07f);
     if (Camera.main) wc.bubble.rotation = Camera.main.transform.rotation;
     if (wc.horn) { float beat = Mathf.Repeat(Time.time * 1.6f, 1); wc.horn.localScale = Vector3.one * (wc.serving ? 0 : 1f * (1 + .3f * Mathf.Exp(-beat * 6))); }
    }
   }
   if (ev == null && vendor && !vendorRunning) { Destroy(vendor.gameObject); vendor = null; cooler = null; }
  }

  // The car of a request: one of the jam's cars with a driver at the wheel in the request's lane, in front of the
  // market (the slot spreads the requests along the block).
  JamCar PickCar(WindowRequest r) {
   if (jamCars == null) return null;
   var door = DoorPoint; float want = door.x + (r.slot - 1.5f) * 5.5f;
   var taken = new HashSet<JamCar>(windowCars.Values.Where(w => !w.released).Select(w => w.jam));
   return jamCars.Where(j => j.window && j.car && j.car.isActiveAndEnabled && !taken.Contains(j) && !OnRing(j.car.transform.position)
      && j.car.transform.position.x > door.x - 9f && j.car.transform.position.x < door.x + 11f)
    // the curb lane first: the clerk reaches its drivers without crossing the avenue
    .OrderBy(j => (j.lane == 0 ? 0 : j.lane == r.lane ? 40 : 80) + Mathf.Abs(j.car.transform.position.x - want)).FirstOrDefault();
  }

  IEnumerator CarAsks(WindowCar wc) {
   yield return new WaitForSeconds(.5f);   // the car stops
   if (!wc.rig) yield break;
   // honk: the car bounces, the driver leans on the wheel
   PlayLayer(wc.anim, wc.rig, "Car_HonkBounce", "body", 1, "Body", false, WrapMode.ClampForever);
   PlayLayer(wc.anim, wc.rig, "Driver_Honk", "driver", 2, "Driver_Root", true, WrapMode.ClampForever);
   Bubble(wc);
   yield return new WaitForSeconds(.55f);
   if (wc.released) yield break;
   PlayLayer(wc.anim, wc.rig, "Car_WindowDown", "window", 3, "Window_Driver", false, WrapMode.ClampForever);
   yield return new WaitForSeconds(.5f);
   if (wc.released || wc.serving) yield break;
   PlayLayer(wc.anim, wc.rig, "Driver_WaveOut", "driver", 2, "Driver_Root", true, WrapMode.Loop);
  }

  void Bubble(WindowCar wc) {
   var b = art.Group(PlayRoot, "Window request " + wc.id, wc.rig.position + Vector3.up * 2.45f);
   var edge = art.Part(b, "Edge", new Vector3(0, 0, .012f), new Vector3(.74f, .64f, .03f), "4A3624");
   var face = art.Part(b, "Face", Vector3.zero, new Vector3(.68f, .58f, .04f), "FFF1CF");
   art.Part(b, "Tail", new Vector3(0, -.36f, .0f), new Vector3(.16f, .16f, .04f), "FFF1CF").localRotation = Quaternion.Euler(0, 0, 45);
   wc.face = new[] { face.GetComponent<Renderer>() };
   var iconGo = new GameObject("Icon"); iconGo.transform.SetParent(b, false); iconGo.transform.localPosition = new Vector3(0, .02f, -.05f);
   var sr = iconGo.AddComponent<SpriteRenderer>(); sr.sprite = K.Icon($"Products/product-{wc.productId:000}");
   if (sr.sprite) { var size = Mathf.Max(sr.sprite.bounds.size.x, sr.sprite.bounds.size.y); iconGo.transform.localScale = Vector3.one * (.46f / Mathf.Max(.001f, size)); }
   wc.icon = iconGo.transform; wc.iconSprite = sr;
   wc.horn = art.Prop2(b, "Horn_Icon", new Vector3(.52f, .32f, -.04f), 180, 1f);
   // the bubble and the car itself take the click
   var hitGo = new GameObject("Click"); hitGo.transform.SetParent(b, false); hitGo.layer = 0;
   wc.hit = hitGo.AddComponent<BoxCollider>(); wc.hit.size = new Vector3(1f, .9f, .4f);
   wc.target = hitGo.AddComponent<CheckoutTarget>(); wc.target.panel = "windowSale"; wc.target.requestId = wc.id;
   var carHit = wc.rig.Find("Window sale click");
   if (!carHit) { carHit = new GameObject("Window sale click").transform; carHit.SetParent(wc.rig, false); carHit.gameObject.layer = 0; var box = carHit.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, .8f, 0); box.size = new Vector3(4.1f, 1.6f, 1.9f); carHit.gameObject.AddComponent<CheckoutTarget>().panel = "windowSale"; }
   carHit.gameObject.SetActive(true); carHit.GetComponent<CheckoutTarget>().requestId = wc.id;
   wc.bubble = b; b.localScale = Vector3.zero; StartCoroutine(Pop(b, true, .3f));
  }
  void Paint(WindowCar wc, bool inStock) {
   if (wc.iconSprite) wc.iconSprite.color = inStock ? Color.white : new Color(.55f, .55f, .55f, .75f);
   if (wc.face != null) foreach (var r in wc.face) if (r) r.sharedMaterial = art.Material(inStock ? "FFF1CF" : "D9D3C7");
  }

  /// <summary>A click on a honking car (or its bubble): sells the drink and sends the clerk out with the cooler.</summary>
  public void ServeWindow(string id) {
   var req = Bridge?.State?.@event?.windowRequests?.FirstOrDefault(r => r.id == id);
   if (req == null || req.status != "waiting" || !windowCars.TryGetValue(id, out var wc) || wc.serving || wc.released) return;
   if (!req.inStock) { StartCoroutine(Shake(wc.bubble)); return; }
   wc.serving = true;
   Bridge.Command("serveWindowSale", "[\"" + id + "\"]");
   if (wc.hit) wc.hit.enabled = false;
   var carHit = wc.rig ? wc.rig.Find("Window sale click") : null; if (carHit) carHit.gameObject.SetActive(false);
   if (wc.anim) PlayLayer(wc.anim, wc.rig, "Driver_WaveOut", "driver", 2, "Driver_Root", true, WrapMode.Loop);
   serveQueue.Enqueue(wc);
   if (!vendorRunning) StartCoroutine(VendorRun());
  }
  /// <summary>QA: where the parts of a request's car are (CheckoutAutoTest "interactive").</summary>
  public string QaWindowCar(string id) {
   if (!windowCars.TryGetValue(id, out var wc) || !wc.rig) return "no car";
   var sb = new System.Text.StringBuilder($"car {wc.rig.position:F2} yaw {wc.rig.eulerAngles.y:0}");
   foreach (var n in new[] { "Window_Driver", "Driver_Root", "Driver_Head", "Driver_Hand_L" }) { var b = CheckoutEventAssets.Bone(wc.rig, n); sb.Append($" | {n} {(b ? wc.rig.InverseTransformPoint(b.position).ToString("F2") : "-")}"); }
   foreach (var r in wc.rig.GetComponentsInChildren<Renderer>(true)) if (r.name.StartsWith("JamCar_Driver")) sb.Append($" | {r.name} on={r.enabled}/{r.gameObject.activeInHierarchy} bounds={wc.rig.InverseTransformPoint(r.bounds.center):F2} size={r.bounds.size:F2} mat={(r.sharedMaterial ? r.sharedMaterial.name : "-")}");
   if (wc.anim) foreach (AnimationState st in wc.anim) if (wc.anim.IsPlaying(st.name)) sb.Append($" | playing {st.name} t={st.time:0.00} layer={st.layer}");
   return sb.ToString();
  }
  static IEnumerator Shake(Transform t) {
   if (!t) yield break;
   var home = t.localScale;
   for (float k = 0; k < .4f; k += Time.deltaTime) { if (!t) yield break; t.localScale = home * (1 + Mathf.Sin(k * 50) * .12f * (1 - k / .4f)); yield return null; }
   if (t) t.localScale = home;
  }

  IEnumerator Release(WindowCar wc) {
   wc.released = true;
   if (wc.bubble) { yield return Pop(wc.bubble, false, .25f); if (wc.bubble) Destroy(wc.bubble.gameObject); wc.bubble = null; }
   var carHit = wc.rig ? wc.rig.Find("Window sale click") : null; if (carHit) carHit.gameObject.SetActive(false);
   if (wc.anim) {
    wc.anim.Stop("Driver_WaveOut@driver");
    PlayLayer(wc.anim, wc.rig, "Driver_Honk", "driver", 2, "Driver_Root", true, WrapMode.ClampForever);   // hands back on the wheel
    float up = PlayLayer(wc.anim, wc.rig, "Car_WindowUp", "window", 3, "Window_Driver", false, WrapMode.ClampForever);
    yield return new WaitForSeconds(up + .2f);
    if (wc.drink) { Destroy(wc.drink.gameObject); wc.drink = null; }
    if (wc.anim) wc.anim.Stop();
   }
   if (wc.jam != null && wc.jam.car) wc.jam.car.Hold = false;
  }

  // ---------------------------------------------------------------- the clerk with the cooler
  CheckoutEventActor Vendor() {
   if (vendor) return vendor;
   var who = WorkerOr("Worker_Stocker", "Customer_09");
   var h = art.Actor(PlayRoot, who, DoorPoint, 0, "Idle", 1);
   vendor = CheckoutEventActor.Of(h);
   // the cooler hangs on the hip of the hand that takes the bottles (Hand_R), its strap over the other shoulder
   var torso = CheckoutEventAssets.Bone(h, "Torso"); var armR = CheckoutEventAssets.Bone(h, "UpperArm_R"); var armL = CheckoutEventAssets.Bone(h, "UpperArm_L");
   cooler = art.Rig(PlayRoot, "Rig_Cooler", h.position, 0, 1);
   coolerAnim = CheckoutEventAssets.RigAnimation(cooler);
   // the lid shut (the rig's rest pose has it open)
   var shut = coolerAnim ? CheckoutEventAssets.PlayClip(coolerAnim, "Cooler_Close", WrapMode.ClampForever) : null;
   if (shut != null) shut.time = shut.length;
   if (torso && armR && armL) {
    var side = armR.position - armL.position; float unit = side.magnitude / .64f; side = Flat(side).normalized;
    var front = -h.forward;
    cooler.position = torso.position + side * .46f * unit + front * .02f * unit + Vector3.down * .18f * unit;
    cooler.rotation = Quaternion.LookRotation(side, Vector3.up) * Quaternion.Euler(0, CoolerYaw, 0);
    cooler.localScale = Vector3.one * (unit / .72f);   // built for a character at the game's 0.72 scale
    cooler.SetParent(torso, true);
   }
   vendor.Show(false);
   return vendor;
  }
  const float CoolerYaw = 0;

  IEnumerator VendorRun() {
   vendorRunning = true;
   var v = Vendor(); var door = DoorPoint;
   v.transform.position = door; v.Face(Vector3.back);
   yield return v.Fade(true);
   while (serveQueue.Count > 0) {
    var wc = serveQueue.Dequeue();
    if (!wc.rig || wc.released) continue;
    var window = CheckoutEventAssets.Bone(wc.rig, "Window_Driver");
    var w = window ? window.position : wc.rig.position;
    var lateral = Flat(w - wc.rig.position); var fwd = Flat(wc.rig.right).normalized;
    lateral -= Vector3.Project(lateral, fwd); if (lateral.sqrMagnitude < .01f) lateral = Vector3.back;
    var stand = Flat(w) + lateral.normalized * .62f + Vector3.up * .15f + fwd * .1f;
    // round the front of the car (the one ahead drives on, the ones behind queue up to its bumper), never through it
    var vehicle = wc.jam != null ? wc.jam.car : null;
    float gapX = (Flat(wc.rig.position) + fwd * ((vehicle ? vehicle.FrontOffset : 2.1f) + .7f)).x;
    var here = v.transform.position;
    var route = new List<Vector3> { here };
    if (here.z > -12.4f) { route.Add(On(here.x, FootMid)); route.Add(On(gapX, FootMid)); route.Add(On(gapX, CycleLane)); }
    route.Add(Road(gapX, CurbEdge - .3f)); route.Add(Road(gapX, stand.z)); route.Add(stand);
    var body = new Bounds(Vector3.up, new Vector3(.8f, 2f, .8f));
    CheckoutEventTraffic.Register(v.transform, body);
    yield return v.Walk(route, 1.35f, "Vendor_WalkCarry");
    v.FaceTowards(w);
    yield return HandOver(v, wc);
    if (!wc.released) StartCoroutine(Release(wc));
    yield return new WaitForSeconds(.4f);
    // back to the footway (and the next car, if any)
    var p = v.transform.position;
    yield return v.Walk(new[] { p, Road(gapX, p.z), Road(gapX, CurbEdge - .3f) }, 1.35f, "Vendor_WalkCarry");
    if (serveQueue.Count == 0) yield return v.Walk(new[] { On(gapX, CycleLane), On(gapX, FootMid), On(door.x, FootMid), door }, 1.35f, "Vendor_WalkCarry");
    CheckoutEventTraffic.Unregister(v.transform);
   }
   yield return v.Fade(false);
   v.Do(null);
   vendorRunning = false;
  }

  IEnumerator HandOver(CheckoutEventActor v, WindowCar wc) {
   float L(string clip) => Mathf.Max(.5f, CheckoutEventMoves.Length(clip));
   var handR = CheckoutEventAssets.Bone(v.transform, "Hand_R");
   var driverHand = CheckoutEventAssets.Bone(wc.rig, "Driver_Hand_L");
   bool water = IsWater(wc.productName);
   // open the cooler
   v.Do("Vendor_OpenCooler", 0);
   if (coolerAnim) CheckoutEventAssets.PlayClip(coolerAnim, "Cooler_Open", WrapMode.ClampForever);
   yield return new WaitForSeconds(L("Vendor_OpenCooler") * .95f);
   // a bottle (or a can) out of the ice
   v.Do("Vendor_TakeBottle", 0);
   float take = L("Vendor_TakeBottle");
   yield return new WaitForSeconds(take * .5f);
   var drink = Hold(handR, water ? "Vendor_Bottle" : "Vendor_Can", Vector3.zero, Vector3.zero);
   yield return new WaitForSeconds(take * .45f);
   // through the window
   v.Do("Vendor_HandOver", 0);
   float give = L("Vendor_HandOver");
   PlayLayer(wc.anim, wc.rig, "Driver_TakeBottle", "driver", 2, "Driver_Root", true, WrapMode.ClampForever);
   yield return new WaitForSeconds(give * .42f);
   if (drink && driverHand) { Reparent(drink, driverHand); wc.drink = drink; }
   yield return new WaitForSeconds(give * .55f);
   // the coins
   v.Do("Vendor_ReceiveCoin", 0);
   float pay = Mathf.Max(L("Vendor_ReceiveCoin"), PlayLayer(wc.anim, wc.rig, "Driver_Pay", "driver", 2, "Driver_Root", true, WrapMode.ClampForever));
   var coins = Hold(driverHand, "Vendor_Coins", Vector3.zero, Vector3.zero, .8f);
   yield return new WaitForSeconds(pay * .4f);
   if (coins && handR) Reparent(coins, handR);
   yield return new WaitForSeconds(pay * .35f);
   if (coins) { var at = coins.position; Destroy(coins.gameObject); StartCoroutine(CoinPop(at)); }
   if (coolerAnim) CheckoutEventAssets.PlayClip(coolerAnim, "Cooler_Close", WrapMode.ClampForever);
   yield return new WaitForSeconds(pay * .25f);
   v.Do(null);
  }
  static bool IsWater(string name) {
   var n = (name ?? "").ToLowerInvariant();
   return n.Contains("água") || n.Contains("agua") || n.Contains("water") || n.Contains("eau") || n.Contains("wasser");
  }
  IEnumerator CoinPop(Vector3 at) {
   var t = art.Prop2(PlayRoot, "Vendor_Coins", at, 0, 1.4f);
   for (float k = 0; k < 1.1f; k += Time.deltaTime) { if (!t) yield break; t.position = at + Vector3.up * (k * 1.2f); t.rotation = Quaternion.Euler(0, k * 540, 0); t.localScale = Vector3.one * 1.4f * (1 - Mathf.Max(0, k - .7f) / .4f); yield return null; }
   if (t) Destroy(t.gameObject);
  }
 }
}
