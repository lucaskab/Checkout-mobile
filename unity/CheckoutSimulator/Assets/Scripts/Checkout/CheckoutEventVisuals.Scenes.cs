using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 // The event scenes (Oct 2026, rigs and moves): every scene is built in world space on the real avenue in front of the
 // market and checked against what stands there at the current stage (the stall or the shop front, lamps, the
 // crossing, the parking entrance, the roundabout's corner).
 //
 // The avenue (CheckoutStreetLayout): north curb z -12.5, a cycle lane along it (z -12.3..-11.1), the footway
 // behind it up to z -8.5, the shop fronts from there (the stall stages stand on the footway itself). Westbound
 // lanes z -14 (curb) and -17, eastbound -20 and -23 (right-hand traffic). The market's crossing is at x -1.75
 // (2.5 m), the roundabout's crossing on the avenue at x ~-11.2, the lamps on the north footway at x -16.3, -6.5,
 // 9.6, the parking entrance (big stages) from x 9.2. A vehicle that stops at the curb uses the westbound curb lane
 // west of the crossing (x -9.6..-3.5) or east of it (from x 0.2); the city's cars swerve round it.
 //
 // Rigs face +X at yaw 0 (vehicles drive forward along +X; props show their front to the street, -Z). The curbside
 // vehicles were mirrored for right-hand traffic, so westbound (yaw 180) they open their doors onto the curb and
 // show their lettering to the street. Characters face their holder's -Z (CheckoutEventActor).
 public sealed partial class CheckoutEventVisuals {
  const float FootFront = -11.0f, FootBack = -8.6f, FootMid = -9.8f, CycleLane = -11.7f, CurbEdge = -12.6f;
  const float LaneW = -14f, LaneW2 = -17f, LaneE2 = -20f;
  const float CrossFrom = -3.3f, CrossTo = -.2f;
  const float WestZoneFrom = -9.6f, WestZoneTo = -3.5f, EastZoneFrom = .2f;
  const float West = 180, East = 0;
  static readonly string[] Shoppers = { "Customer_07", "Customer_03", "Customer_06", "Customer_02", "Customer_09", "Customer_04", "Customer_08", "Customer_01", "Customer_05" };

  readonly Dictionary<string, Vector2> curbBlocks = new Dictionary<string, Vector2>();
  readonly Dictionary<string, Vector3> focus = new Dictionary<string, Vector3>();
  /// <summary>Where an event's scene happens (QA shots frame it).</summary>
  public Vector3 FocusOf(string id) => focus.TryGetValue(id, out var f) ? f : doorW;
  void Focus(Vector3 p) => focus[building] = p;
  readonly HashSet<string> jams = new HashSet<string>();

  void ApplyTraffic(string id) {
   if (!string.IsNullOrEmpty(id) && curbBlocks.TryGetValue(id, out var b)) CheckoutEventTraffic.SetCurbBlock(b.x, b.y); else CheckoutEventTraffic.ClearCurbBlock();
   CheckoutEventTraffic.AvenueJammed = !string.IsNullOrEmpty(id) && jams.Contains(id);
  }

  // A scene's root sits at the world origin, unrotated and unscaled: everything in it is placed in world space.
  void WorldAligned(Transform t) {
   t.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
   var s = transform.lossyScale; t.localScale = new Vector3(1 / Mathf.Max(1e-4f, s.x), 1 / Mathf.Max(1e-4f, s.y), 1 / Mathf.Max(1e-4f, s.z));
  }

  // ---------------------------------------------------------------- the street as it is now
  Vector3 doorW; bool small; float facadeZ; List<Rect> blockers, taken; List<string> blockerNames; CheckoutEventDirector director; Transform root;

  void Survey() {
   var map = GetComponent<CheckoutMap>() ?? FindAnyObjectByType<CheckoutMap>();
   doorW = map ? map.Entrance : new Vector3(-1.75f, .74f, -8.7f);
   small = CheckoutStall.Small;
   facadeZ = small ? FootBack : Mathf.Max(FootBack, doorW.z - .25f);
   taken = new List<Rect>(); blockers = new List<Rect>(); blockerNames = new List<string>();
   foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)) {
    if (!r.enabled || r.forceRenderingOff || !r.gameObject.activeInHierarchy || r is ParticleSystemRenderer || r is SkinnedMeshRenderer) continue;
    if (r.transform.IsChildOf(transform)) continue;
    var b = r.bounds;
    if (b.max.z < -13.2f || b.min.z > -5f || b.max.x < -18f || b.min.x > 22f) continue;
    if (b.size.y < .3f || b.max.y < .45f || b.size.x > 12f || b.size.z > 12f) continue;
    if (Mover(r.transform)) continue;
    Block(Rect.MinMaxRect(b.min.x - .1f, b.min.z - .1f, b.max.x + .1f, b.max.z + .1f), (r.transform.parent ? r.transform.parent.name + "/" : "") + r.name);
   }
   Block(Rect.MinMaxRect(CrossFrom, -13f, CrossTo, -8.4f), "market crossing");        // the crossing and its landing
   Block(Rect.MinMaxRect(-40f, -13f, -12.7f, -4f), RoundaboutCorner);       // the roundabout's corner and its crossing
   Block(Rect.MinMaxRect(-12.7f, -13f, -9.5f, -10.1f), "roundabout crossing landing"); // where that crossing lands on the footway
   if (map && map.HasParking) Block(Rect.MinMaxRect(9.2f, -13f, 18.6f, -4f), "parking entrance"); // the parking entrance
   // The stall stages (mesinha … contêiner): the strip in front of the tables where shoppers pick and the register
   // line that runs from the cooler end towards the sidewalk are the stall's own shop floor: no event prop there.
   if (CheckoutStall.Yard) {
    var front = CheckoutStall.StallFront; Block(Rect.MinMaxRect(front.xMin - .1f, front.yMin - .1f, front.xMax + .1f, front.yMax + .1f), "stall's tables strip");
    var q = CheckoutStall.QueueSpot(0); Block(Rect.MinMaxRect(q.x - .5f, q.z - 2.2f, q.x + 2.6f, q.z + .2f), "stall's register line");
    // the way from the entrance spot on the sidewalk up to the tables
    Block(Rect.MinMaxRect(doorW.x - .7f, Mathf.Min(doorW.z, front.yMin) - .2f, doorW.x + .7f, Mathf.Max(doorW.z, front.yMin) + .1f), "stall's entry path");
    // the whole face of the stall down to the middle of the sidewalk: shoppers walk up to any of its tables, so
    // nothing stands in front of it (props go beside the stall instead)
    var stallArea = CheckoutStall.StallArea; Block(Rect.MinMaxRect(stallArea.xMin - .3f, -10.1f, stallArea.xMax + .3f, stallArea.yMin + .05f), "in front of the stall");
   }
   float half = small ? (CheckoutStall.ShopInside ? 2.1f : 1.1f) : 2.5f;     // the stall's front / the small shop's steps / the shop's entrance steps
   wayIn = Rect.MinMaxRect(doorW.x - half, -11.2f, doorW.x + half, Mathf.Max(doorW.z, -8.4f));
   Block(wayIn, "way in"); // way in
  }
  const string RoundaboutCorner = "roundabout corner";
  Rect wayIn;
  void Block(Rect r, string why) { blockers.Add(r); blockerNames.Add(why); }
  /// <summary>What covers the rect (a blocker's name, "another prop"), or null when it is free. `inLot`: the rect is on
  /// the market's own lot, behind the sidewalk, where the roundabout corner's wide guard does not apply.</summary>
  string Blocker(Rect r, bool inLot = false) {
   for (int i = 0; i < blockers.Count; i++) if (blockers[i].Overlaps(r) && !(inLot && blockerNames[i] == RoundaboutCorner)) return blockerNames[i];
   foreach (var t in taken) if (t.Overlaps(r)) return "another prop";
   return null;
  }
  static bool Mover(Transform t) {
   for (var p = t; p; p = p.parent) {
    if (p.GetComponent<NavMeshAgent>() || p.GetComponent<MarketCharacterAnimator>() || p.GetComponent<CheckoutWalker>() || p.GetComponent<CheckoutCityPedestrian>()) return true;
    var n = p.name; if (n.Contains("Neighborhood car") || n.Contains("Vehicle") || n.Contains("Truck") || n.StartsWith("Car") || n.Contains("Bicycle") || n.Contains("Bike") || n.Contains("Cyclist")) return true;
   }
   return false;
  }
  bool Free(Rect r) => !blockers.Any(b => b.Overlaps(r)) && !taken.Any(b => b.Overlaps(r));
  /// <summary>The free spot nearest to x for a footprint [x-left, x+right] x [zFrom, zTo]; false when there is none.</summary>
  bool Place(ref float x, float left, float right, float zFrom, float zTo, float reach = 9f, int prefer = 1) {
   int steps = Mathf.CeilToInt(reach / .125f) * 2;
   for (int i = 0; i <= steps; i++) {
    float d = ((i + 1) / 2) * .125f * (i % 2 == 1 ? prefer : -prefer);
    var r = Rect.MinMaxRect(x + d - left, zFrom, x + d + right, zTo);
    if (Free(r)) { x += d; taken.Add(r); return true; }
   }
   return false;
  }
  void Claim(float x0, float z0, float x1, float z1) => taken.Add(Rect.MinMaxRect(Mathf.Min(x0, x1), Mathf.Min(z0, z1), Mathf.Max(x0, x1), Mathf.Max(z0, z1)));

  /// <summary>A point on the sidewalk at its walking height (the NavMesh), or the road surface.</summary>
  static Vector3 On(float x, float z) {
   if (z > -12.45f && NavMesh.SamplePosition(new Vector3(x, .6f, z), out var hit, .8f, NavMesh.AllAreas) && Mathf.Abs(hit.position.x - x) < .5f && Mathf.Abs(hit.position.z - z) < .5f)
    return new Vector3(x, hit.position.y, z);
   return new Vector3(x, z > -12.45f ? .2f : .15f, z);
  }
  static Vector3 Road(float x, float z) => new Vector3(x, .15f, z);

  /// <summary>Walking route from a point on the street to the market's door: onto the footway, along it, in.</summary>
  Vector3[] ToDoor(Vector3 from, float walkZ = FootMid) {
   var pts = new List<Vector3> { from };
   if (from.z < -12.4f) pts.Add(On(from.x, CycleLane));
   pts.Add(On(from.x, walkZ));
   pts.Add(On(doorW.x + (from.x > doorW.x ? .5f : -.5f), walkZ));
   if (doorW.z > walkZ + .6f) pts.Add(On(doorW.x, Mathf.Min(doorW.z - .6f, FootBack)));
   pts.Add(doorW);
   return pts.ToArray();
  }
  static Vector3[] Reverse(Vector3[] p) { var r = (Vector3[])p.Clone(); Array.Reverse(r); return r; }

  // ---------------------------------------------------------------- building blocks
  Transform Prop(string model, Vector3 p, float yaw = 0, float scale = 1) => art.Prop2(root, model, p, yaw, scale);
  Transform Rig(string rig, Vector3 p, float yaw = 0, string clip = null, float scale = 1) => art.Rig(root, rig, p, yaw, scale, clip);
  CheckoutEventActor Person(string who, Vector3 p, Vector3 face, string move = null, float scale = 1, bool shown = true, float offset = -1) {
   // "@crew0" / "@crew1": one of the construction crew (CheckoutCrew), for everyone working on a site or a pole.
   var crew = who.StartsWith("@crew") ? CheckoutCrew.Template(int.Parse(who.Substring(5))) : null;
   if (who.StartsWith("@crew") && !crew) who = "Worker_Delivery";
   var h = crew ? art.Actor(root, crew, p, 0, "Idle", 1, move, offset)
    : who.StartsWith("#") && cast != null && cast.Count > 0 ? art.Actor(root, cast[int.Parse(who.Substring(1)) % cast.Count], p, 0, "Idle", 1, move, offset) : art.Actor(root, who, p, 0, "Idle", 1, move, offset);
   h.localScale = Vector3.one * scale;
   var a = CheckoutEventActor.Of(h); a.Face(face); if (!shown) a.Show(false);
   return a;
  }
  CheckoutEventVehicle Vehicle(string rig, Vector3 p, float yaw) { var t = Rig(rig, p, yaw); return CheckoutEventVehicle.Attach(t); }
  void Story(Func<IEnumerator> s) => director.Add(s);
  void Fx2(Transform parent, string model, Vector3 local, string kind, float yaw = 0, float scale = 1) {
   var t = art.Prop2(parent, model, local, yaw, scale);
   motions[building].Add(new Motion { root = t, home = t.localPosition, rot = t.localRotation, scale = t.localScale, kind = kind, phase = motions[building].Count * .7f });
  }
  void Ride(Transform t, Transform target, Vector3 offset) => motions[building].Add(new Motion { root = t, target = target, offset = offset, home = t.localPosition, rot = t.localRotation, scale = t.localScale, kind = "ride" });
  void Follow(Transform t, Transform target, Vector3 offset) => motions[building].Add(new Motion { root = t, target = target, offset = offset, home = t.localPosition, rot = t.localRotation, scale = t.localScale, kind = "follow" });
  static Vector3 Dir(float x, float z) => new Vector3(x, 0, z);
  static readonly Vector3 North = Vector3.forward, South = Vector3.back, EastDir = Vector3.right, WestDir = Vector3.left;
  string WorkerOr(string worker, string fallback) { var sim = FindAnyObjectByType<MarketSimulation>(); return sim && sim.world && (sim.world.Find(worker) || (worker == "Worker_Stocker" && sim.world.Find("StockWorker_0"))) ? worker : fallback; }
  static IEnumerator Wait(float s) { yield return new WaitForSeconds(s); }
  // The people of the neighbourhood: the city's appearance templates (each looks different); "#n" picks one of them.
  List<Transform> cast;
  int pick; string Next() => cast != null && cast.Count > 0 ? "#" + ((pick++) % cast.Count) : Shoppers[(pick++) % Shoppers.Length];
  void CastPeople() {
   cast = new List<Transform>(); var seen = new HashSet<string>();
   foreach (var app in FindObjectsByType<CheckoutCityAppearance>(FindObjectsInactive.Include, FindObjectsSortMode.None))
    if (app.templates != null) foreach (var t in app.templates) if (t && seen.Add(t.name)) cast.Add(t.transform);
   foreach (var n in Shoppers) if (seen.Add(n)) { var sim = FindAnyObjectByType<MarketSimulation>(); var t = sim && sim.world ? sim.world.Find(n) : null; if (t && !t.GetComponent<CheckoutCityAppearance>()) cast.Add(t); }
  }

  /// <summary>Blocks the westbound curb lane for this event (the city's cars swerve round it).</summary>
  void BlockCurb(float from, float to) => curbBlocks[building] = new Vector2(from, to);

  void Build(string id, Transform sceneRoot) {
   root = sceneRoot; Survey(); if (cast == null || cast.Count == 0) CastPeople();
   director = root.gameObject.AddComponent<CheckoutEventDirector>();
   curbBlocks.Remove(id); jams.Remove(id); ForgetCrowd(id); pick = id.Length;
   switch (id) {
    case "hora-do-rush": Rush(); break;
    case "quinto-dia-util": Payday(); break;
    case "feira-de-rua": StreetMarket(); break;
    case "onda-de-calor": HeatWave(); break;
    case "sorteio-na-porta": PrizeWheel(); break;
    case "caminhao-de-ofertas": OffersTruck(); break;
    case "dia-de-jogo": MatchDay(); break;
    case "cafe-com-a-equipe": CoffeeBreak(); break;
    case "viralizou": Influencer(); break;
    case "chuva-forte": BuildRain(root); break;
    case "rua-em-obras": RoadWorksScene(); break;
    case "engarrafamento": Jam(); break;
    case "fim-do-mes": MonthEnd(); break;
    case "maquininha-fora-do-ar": CardsDown(); break;
    case "excursao-da-escola": SchoolTrip(); break;
    case "queda-de-energia": PowerCut(); break;
    case "turno-puxado": TiredShift(); break;
    case "vigilancia-sanitaria": Inspection(); break;
    case "carro-de-som": SoundCar(); break;
   }
  }

  // The middle of each door of a westbound bus stopped with its origin at stopX (leaves Door_<n>L/R).
  static List<float> DoorCentres(CheckoutEventVehicle bus, float stopX) {
   var byDoor = new Dictionary<string, List<float>>();
   foreach (var t in bus.GetComponentsInChildren<Transform>(true))
    if (t.name.StartsWith("Door_") && t.GetComponent<Renderer>() == null) {
     var key = t.name.Substring(0, t.name.Length - 1);
     if (!byDoor.TryGetValue(key, out var l)) byDoor[key] = l = new List<float>();
     l.Add(bus.transform.InverseTransformPoint(t.position).x);
    }
   return byDoor.Values.Select(l => stopX - l.Average()).OrderBy(x => x).ToList();
  }

  // A bus or truck path from the east end of the avenue to a curbside stop (front at frontX) in the westbound lane.
  static Vector3[] ArriveWest(float stopX) => new[] { Road(37f, LaneW), Road(stopX, LaneW) };
  // From a westbound curbside stop out through the roundabout and up the west street.
  static Vector3[] LeaveWest(float fromX) => CheckoutRoundabout.Route(new[] { Road(fromX, LaneW), Road(-22.4f, LaneW), Road(-22.4f, 37f) });

  // ================================================================ hora do rush
  // A city bus pulls up at the stop, opens its doors onto the curb, a crowd of workers gets off and walks to the
  // market's door; someone waiting at the shelter gets on; the bus leaves through the roundabout. Every ~40 s.
  // The customers the rush brought (Customer.origin) ride this bus: they get off first and really go in and shop
  // (CheckoutEventVisuals.Market.cs); the scene's own extras only fill the crowd up.
  void Rush() {
   var director = this.director;   // the stories run later: they keep this scene's director
   var id = building; BusRiders();
   var bus = Vehicle("Rig_CityBus", Road(37, LaneW), West);
   float frontX = EastZoneFrom + .1f;
   float stopX = frontX + bus.FrontOffset;          // rig origin when its front is at frontX (westbound: front = origin - offset)
   float sideZ = LaneW + bus.HalfWidth + .22f;      // just outside its doors, on the curb
   var doors = DoorCentres(bus, stopX);
   if (doors.Count == 0) doors.Add(stopX - 2f);
   // the shelter on the footway next to the stop
   float sx = (doors.Min() + doors.Max()) * .5f;
   bool shelter = Place(ref sx, 2.95f, 2.25f, -10.95f, -9.05f, 4f);
   if (shelter) Prop("Rush_BusShelter", On(sx, -10.0f), 0);
   Focus(On(doors.Count > 0 ? doors[0] + 2f : sx, -11.6f));
   var waiting = new List<CheckoutEventActor>();
   if (shelter) { waiting.Add(Person(Next(), On(sx - .9f, -10.35f), South, "LookPhone")); waiting.Add(Person(Next(), On(sx + .7f, -10.4f), South)); }
   var crowd = new List<CheckoutEventActor>();
   for (int i = 0; i < 6; i++) crowd.Add(Person(Next(), Road(frontX, CurbEdge), North, null, 1, false));
   director.OnReset(() => { bus.transform.position = Road(37, LaneW); bus.Face(WestDir); foreach (var c in crowd) c.Show(false); });
   Story(() => BusRun());
   IEnumerator BusRun() {
    yield return Wait(.5f);
    while (true) {
     bus.gameObject.SetActive(true);
     yield return bus.Drive(ArriveWest(stopX), 7f);
     yield return Wait(.4f);
     yield return bus.Clip("DoorsOpen");
     var real = TakeRiders(id, crowd.Count);
     for (int i = 0; i < real.Count; i++) { RiderGetsOff(real[i], On(doors[i % doors.Count], sideZ)); yield return Wait(.55f); }
     for (int i = 0; i < Mathf.Max(real.Count > 0 ? 1 : crowd.Count, crowd.Count - real.Count); i++) {
      var c = crowd[i]; float dx = doors[(i + real.Count) % doors.Count];
      c.transform.position = On(dx, sideZ); c.Face(North);
      director.StartCoroutine(GetOff(c));
      yield return Wait(.55f);
     }
     if (waiting.Count > 0) { var w = waiting[0]; director.StartCoroutine(Board(w, doors[doors.Count - 1])); }
     yield return Wait(2.6f);
     yield return bus.Clip("DoorsClose");
     yield return Wait(.6f);
     yield return bus.Drive(LeaveWest(stopX), 7f, false);
     bus.gameObject.SetActive(false);
     bus.transform.position = Road(37, LaneW); bus.Face(WestDir);
     yield return Wait(12f);
    }
   }
   IEnumerator GetOff(CheckoutEventActor c) {
    yield return c.Fade(true, .3f);
    var path = new List<Vector3> { c.transform.position, On(c.transform.position.x, CycleLane) };
    // round the shelter on its street side, then along the footway to the door
    if (shelter) { float wx = sx - 3.3f; path.Add(On(wx, CycleLane)); }
    path.AddRange(ToDoor(path[path.Count - 1]).Skip(1));
    yield return c.Walk(path, UnityEngine.Random.Range(1.15f, 1.45f));
    yield return c.Fade(false, .3f);
   }
   IEnumerator Board(CheckoutEventActor w, float doorX) {
    var home = w.transform.position;
    yield return w.Walk(new[] { On(home.x, CycleLane), On(doorX, sideZ) }, 1.2f);
    yield return w.Fade(false, .3f);
    yield return Wait(14f);
    w.transform.position = On(home.x + 7f, FootMid); w.Face(WestDir);
    yield return w.Fade(true, .3f);
    yield return w.Walk(new[] { home }, 1.1f); w.Face(South); w.Do("LookPhone");
   }
  }

  // ================================================================ quinto dia útil
  // A 24h ATM against the market's front (or the stall's back line), facing the street, a few steps from the door; the
  // queue runs along the front, away from the entrance, so the outer footway stays free for passers-by (no rope
  // barriers: people just stand in line). Whoever is done walks into the market with the money. The payday customers
  // (Customer.origin) are real: they arrive on foot, join this same line, withdraw (the paying move at the machine)
  // and go in to shop; the scene's own people keep the line from looking empty and also walk in when done.
  void Payday() {
   var director = this.director;   // the stories run later: they keep this scene's director
   var id = building;
   int capacity; float step;
   if (!AtmSpot(out var ap, out var face, out var lineDir, out capacity, out step)) return;   // no room for the ATM and its line near the door
   bool straight = Vector3.Dot(face, lineDir) > .9f;          // the line runs straight out from the machine (else beside it)
   // Each one stands ≥ .6 m clear of the machine's body, on its screen side.
   Vector3 Slot(int i) { var p = ap + face * AtmClear + (i == 0 ? Vector3.zero : lineDir * ((straight ? 0 : .2f) + i * step)); return On(p.x, p.z); }
   Vector3 along = straight ? -face : -lineDir;               // how the ones waiting face (towards the machine)
   Vector3 atFront = -face;
   Focus(Slot(1));
   var atm = Prop("Pagamento_ATM", On(ap.x, ap.z), CheckoutEventActor.YawFacing(face));
   // nobody walks through the machine: it carves its body out of the walkable area
   var block = atm.gameObject.AddComponent<NavMeshObstacle>(); block.shape = NavMeshObstacleShape.Box; block.size = new Vector3(.8f, 1.8f, .7f); block.center = new Vector3(0, .9f, 0); block.carving = true; block.carveOnlyStationary = true;
   var line = new EventLine { slot = Slot, front = On(ap.x, ap.z), capacity = capacity };
   // the scene's extras come from beyond the end of the line and leave straight for the way in
   Vector3 joinFrom = Slot(capacity - 1) + lineDir * 1.6f;
   var pool = new List<CheckoutEventActor>();
   for (int i = 0; i < 4; i++) pool.Add(Person(Next(), Slot(i), i == 0 ? atFront : along, null, 1, false));
   var free = new List<CheckoutEventActor>();
   int extras = Mathf.Min(3, capacity - 2);   // the scene's own people in line: room is always left for real customers
   director.OnReset(() => {
    line.members.RemoveAll(m => m is CheckoutEventActor); line.standing.RemoveWhere(m => m is CheckoutEventActor); free.Clear();
    for (int i = 0; i < pool.Count; i++) {
     var a = pool[i];
     if (i < extras) { a.transform.position = Slot(i); a.Face(i == 0 ? atFront : along); a.Show(true); a.Do(i == 0 ? "TypeATM" : (i % 2 == 1 ? "LookPhone" : null)); line.members.Insert(Mathf.Min(i, line.members.Count), a); line.joined[a] = Time.time; }
     else { a.Show(false); free.Add(a); }
    }
   });
   Story(() => Atm()); Story(() => Fill());
   IEnumerator Atm() {
    foreach (var m in line.members.ToArray()) if (m is CheckoutEventActor a) director.StartCoroutine(InLine(a));
    while (true) {
     yield return null;
     if (line.members.Count == 0) continue;
     var first = line.members[0];
     // whoever is first has to reach the machine (a customer may still be walking up)
     for (float waited = 0; waited < 20f && line.members.Count > 0 && line.members[0] == first && !line.standing.Contains(first); waited += Time.deltaTime) yield return null;
     if (line.members.Count == 0 || line.members[0] != first) continue;
     yield return Wait(UnityEngine.Random.Range(4.5f, 6.5f));
     if (line.members.Count == 0 || line.members[0] != first) continue;   // a customer left the line (the market closed)
     line.Drop(first);
     // a customer (CheckoutWalker) sees it is out of the line and walks in with the money; an extra walks to the door
     if (first is CheckoutEventActor done) { done.Do(null); director.StartCoroutine(Leave(done)); }
    }
   }
   // keep two or three people in line while no payday customer is in it (the real customers never wait behind extras
   // that join after them)
   IEnumerator Fill() {
    while (true) {
     yield return Wait(UnityEngine.Random.Range(2.5f, 4f));
     if (line.members.Count < extras && free.Count > 0 && !line.members.Any(m => m is CheckoutWalker)) { var a = free[0]; free.RemoveAt(0); director.StartCoroutine(Join(a)); }
    }
   }
   IEnumerator Join(CheckoutEventActor a) { a.transform.position = joinFrom; a.Face(along); line.Join(a); yield return a.Fade(true); yield return InLine(a); }
   // follows its place in the line: steps up when the one in front is done, types at the machine when first
   IEnumerator InLine(CheckoutEventActor a) {
    int at = -1;
    while (line.members.Contains(a)) {
     int i = line.members.IndexOf(a);
     if (i != at) {
      line.standing.Remove(a); a.Do(null);
      yield return a.Walk(new[] { Slot(i) }, 1.0f);
      at = i;
      if (line.members.IndexOf(a) != i) continue;
      a.Face(i == 0 ? atFront : along); a.Do(i == 0 ? "TypeATM" : (UnityEngine.Random.value < .6f ? "LookPhone" : null)); line.standing.Add(a);
     }
     yield return null;
    }
   }
   IEnumerator Leave(CheckoutEventActor a) { yield return a.Walk(small ? new[] { a.transform.position + lineDir * .7f, doorW } : ToDoor(a.transform.position, Slot(0).z - .3f), 1.3f); yield return a.Fade(false); free.Add(a); }
   lines[id] = line;   // last: customers are routed here only once the scene is complete
  }

  /// <summary>Where payday's ATM stands, the side its screen faces (where people stand) and the way its line grows.
  /// Shop stages: against the shop front on the footway, screen to the street, a few steps from the door, the line
  /// along the front away from it. Stall stages (CheckoutStall.Yard): the best spot 1.8–6 m from the entrance, on
  /// the stall's own lot (plaza beside / in front of the stall, or the sidewalk by it), never on the tables' strip,
  /// the register line, the entry path or the way in; the screen to the street or turned to the side, the line straight
  /// out from it or beside it, every place on the walkable area. Never more than ~6 m from the door: no spot = no ATM
  /// (payday customers then simply walk in). Why the candidates were turned down: AtmReport (QA).</summary>
  const float AtmClear = .95f;   // machine centre → where the user stands (body half-depth .35 + .6 clear)
  string atmReport = "";
  public string AtmReport => atmReport;
  bool AtmSpot(out Vector3 ap, out Vector3 face, out Vector3 lineDir, out int capacity, out float step) {
   ap = face = lineDir = Vector3.zero;
   if (!CheckoutStall.Yard) {
    capacity = 5; step = .8f;
    float zBack = small ? FootBack - .05f : Mathf.Min(facadeZ, -7.6f), atmZ = zBack - .35f, reachOut = .6f + capacity * step;
    // east of the door with the line growing east, else west of it with the line growing west (within ~6 m)
    float x = doorW.x + 3.2f; bool ok = Place(ref x, .7f, reachOut, atmZ - AtmClear - .4f, zBack, 2.8f); lineDir = Vector3.right;
    if (!ok) { x = doorW.x - 3.2f; ok = Place(ref x, reachOut, .7f, atmZ - AtmClear - .4f, zBack, 2.8f, -1); lineDir = Vector3.left; }
    ap = new Vector3(x, 0, atmZ); face = Vector3.back;
    atmReport = ok ? $"ATM on the shop front at x {x:0.0} ({Mathf.Abs(x - doorW.x):0.0} m from the door)" : "no free spot on the shop front within 6 m of the door";
    return ok;
   }
   capacity = 4; step = .75f;
   const float LotMinX = -17.25f, LotMaxX = -5.75f;           // lot A1: the stall's own lot (CheckoutStall)
   var why = new Dictionary<string, int>(); void No(string k) { why.TryGetValue(k, out var n); why[k] = n + 1; }
   var stall = CheckoutStall.StallArea; var door = new Vector2(doorW.x, doorW.z);
   Vector3[] faces = { Vector3.back, Vector3.right, Vector3.left };
   float best = float.MaxValue; bool found = false; Vector3 bestP = default, bestF = default, bestL = default;
   for (float x = door.x - 6f; x <= door.x + 6f; x += .25f)
    for (float z = -10.9f; z <= stall.center.y; z += .25f) {
     var p2 = new Vector2(x, z); float d = Vector2.Distance(p2, door);
     if (d < 1.8f || d > 6f) { No("too near / too far from the door"); continue; }
     if (x - .45f < LotMinX || x + .45f > LotMaxX) { No("another lot"); continue; }
     bool inLot = z > -8.5f;
     var body = Rect.MinMaxRect(x - .45f, z - .45f, x + .45f, z + .45f);
     if (stall.Overlaps(body)) { No("on the stall"); continue; }
     var hit = Blocker(body, inLot); if (hit != null) { No("ATM spot: " + hit); continue; }
     var p = new Vector3(x, 0, z);
     foreach (var f in faces) {
      var side = new Vector3(f.z, 0, -f.x); if (Vector3.Dot(side, p - doorW) < 0) side = -side;   // beside it: away from the door
      foreach (var l in new[] { f, side }) {
       bool straight = l == f; string bad = null;
       for (int i = 0; i < capacity && bad == null; i++) {
        var s = p + f * AtmClear + (i == 0 ? Vector3.zero : l * ((straight ? 0 : .2f) + i * step));
        var spot = Rect.MinMaxRect(s.x - .25f, s.z - .25f, s.x + .25f, s.z + .25f);
        if (stall.Overlaps(spot)) bad = "line on the stall";
        else if (s.x < LotMinX || s.x > LotMaxX) bad = "line on another lot";
        else if ((hit = Blocker(spot, s.z > -8.5f)) != null) bad = "line: " + hit;
        else if (!NavMesh.SamplePosition(new Vector3(s.x, .3f, s.z), out var nav, .45f, NavMesh.AllAreas) || Mathf.Abs(nav.position.x - s.x) > .3f || Mathf.Abs(nav.position.z - s.z) > .3f) bad = "line off the walkable area";
       }
       if (bad != null) { No(bad); continue; }
       // a few steps from the door, on the plaza rather than the sidewalk, screen to the street, the line straight out
       float score = Mathf.Abs(d - 3.2f) + (z < -8.5f ? 1f : 0) + (f == Vector3.back ? 0 : .3f) + (straight ? 0 : .2f);
       if (score < best) { best = score; found = true; bestP = p; bestF = f; bestL = l; }
      }
     }
    }
   var reasons = string.Join(", ", why.OrderByDescending(k => k.Value).Take(6).Select(k => k.Key + " ×" + k.Value));
   if (!found) { atmReport = "stall stage: no ATM spot within 6 m of the door (" + reasons + ")"; return false; }
   ap = bestP; face = bestF; lineDir = bestL;
   for (int i = 0; i < capacity; i++) { var s = ap + face * AtmClear + (i == 0 ? Vector3.zero : lineDir * ((Vector3.Dot(face, lineDir) > .9f ? 0 : .2f) + i * step)); Claim(s.x - .25f, s.z - .25f, s.x + .25f, s.z + .25f); }
   Claim(ap.x - .45f, ap.z - .45f, ap.x + .45f, ap.z + .45f);
   atmReport = $"stall stage: ATM at ({ap.x:0.0}, {ap.z:0.0}) {Vector2.Distance(new Vector2(ap.x, ap.z), door):0.0} m from the door, screen {face}, line {(Vector3.Dot(face, lineDir) > .9f ? "straight out" : "beside")} {lineDir}; rejected: {reasons}";
   return true;
  }

  // ================================================================ feira de rua
  // The street market takes the curb lane east of the crossing: two stalls facing the footway, the FEIRA LIVRE banner
  // and cones closing the lane at its start; vendors call out from behind, shoppers buy from the curb, families
  // carry their bags into the market.
  void StreetMarket() {
   var director = this.director;   // the stories run later: they keep this scene's director
   float a = EastZoneFrom;
   var red = Prop("Feira_StallRed", Road(a + 1.85f, LaneW + .1f), 180);
   var blue = Prop("Feira_StallBlue", Road(a + 5.45f, LaneW + .1f), 180);
   Rig("Rig_FeiraBanner", Road(a + 7.9f, LaneW), -90, "Wind", .72f);
   for (int i = 0; i < 4; i++) art.Cone(root, Road(a + 8.8f + i * .7f, LaneW - 1.4f + i * .8f));   // taper from the curb into the inner lane
   BlockCurb(a - .2f, a + 11.2f);
   Focus(Road(a + 4f, -13.2f));
   Person(Next(), Road(a + 1.4f, LaneW - 1.35f), North, "Wave");
   Person(Next(), Road(a + 5.9f, LaneW - 1.35f), North);
   Person(Next(), On(a + 1.0f, CurbEdge + .25f), South, "LookPhone");
   Person(Next(), On(a + 2.6f, CurbEdge + .3f), South);
   Person(Next(), On(a + 5.2f, CurbEdge + .25f), South, "Clipboard");
   // the fair's customers buy at a stall and then walk into the market (Market.cs)
   Stop(On(a + 1.8f, CurbEdge + .3f), Road(a + 1.85f, LaneW + .1f), 2.5f, "BuyAtSpecialSector");
   Stop(On(a + 4.3f, CurbEdge + .3f), Road(a + 5.45f, LaneW + .1f), 2.5f, "BuyAtSpecialSector");
   Stop(On(a + 6.3f, CurbEdge + .3f), Road(a + 5.45f, LaneW + .1f), 2.5f, "BuyAtSpecialSector");
   // a family takes the shopping into the market and comes back for more
   var parent = Person(Next(), On(a + 4f, CycleLane), WestDir, "CarryBox", 1, false);
   var kid = Person(Next(), On(a + 4.6f, CycleLane), WestDir, null, .58f, false);
   Story(() => Family());
   IEnumerator Family() {
    while (true) {
     parent.transform.position = On(a + 3.5f, CycleLane); kid.transform.position = On(a + 4.2f, CycleLane);
     director.StartCoroutine(parent.Fade(true)); yield return kid.Fade(true);
     var route = ToDoor(parent.transform.position);
     director.StartCoroutine(kid.Walk(route.Select(p => p + new Vector3(.6f, 0, .45f)).ToArray(), 1.15f));
     yield return parent.Walk(route, 1.15f, "CarryBox");
     director.StartCoroutine(kid.Fade(false)); yield return parent.Fade(false);
     yield return Wait(9f);
    }
   }
  }

  // ================================================================ onda de calor
  // 38 °C on the street thermometer; an ice-cream cart on the footway with a queue fanning themselves, someone in
  // the shade of the parasol bench with a cold drink.
  void HeatWave() {
   float tx = doorW.x - 3.2f;
   if (Place(ref tx, .8f, .8f, -11.05f, -10.6f, 8f, -1)) Prop("Calor_StreetThermometer", On(tx, -10.85f), 0);
   float cx = doorW.x + 3.4f;
   if (Place(ref cx, 1.6f, 1.2f, -11.0f, -8.7f, 26f)) {
    Prop("Calor_IceCreamCart", On(cx, -9.55f), 0); Focus(On(cx + 1.5f, -9.9f));
    Person(Next(), On(cx - 1.45f, -9.55f), EastDir, "Wave");
    Person(Next(), On(cx - .3f, -10.6f), North, "Fan");
    Person(Next(), On(cx + .55f, -10.75f), Dir(-.3f, 1), "Sip");
    // the heat's customers stop at the cart on their way in for cold drinks (Market.cs)
    Stop(On(cx + 1.45f, -9.85f), On(cx, -9.55f), 2.5f, "BuyAtSpecialSector"); Stop(On(cx + 1.25f, -10.85f), On(cx, -9.55f), 2f);
   }
   float bx = doorW.x + 7.4f;
   if (Place(ref bx, 1.25f, 1.25f, -10.7f, -8.65f, 14f)) {
    Rig("Rig_SunUmbrella", On(bx, -9.35f), 0, "Wind");
    Person(Next(), On(bx - .35f, -9.45f), South, "SitSip");
    Person(Next(), On(bx + .95f, -10.35f), Dir(-.5f, -1), "Fan");
   }
  }

  // ================================================================ sorteio na porta
  // The prize wheel by the door: the promoter pulls it, it spins and slows down with the flapper ticking, the
  // customers in front clap when it stops on a prize; a balloon arch over the door.
  void PrizeWheel() {
   var director = this.director;   // the stories run later: they keep this scene's director
   float x = doorW.x + 2.6f;
   float back = small ? FootBack : Mathf.Min(facadeZ, -7.7f);
   if (!Place(ref x, 1.3f, 1.2f, back - 2.9f, back, 26f)) return;
   // the promoter first: her hand at the top of the pull decides where the wheel stands
   var promoter = Person(WorkerOr("Worker_Cashier", "Customer_07"), On(x - .6f, back - .9f), South, "PullWheel", 1, true, 0);
   // wheel origin (its stand's foot): the disc's hub is 1.75 m above it and its face .32 m in front of it
   var moves = promoter.Moves; float ox = x + .45f, oz = back - .4f, ground = On(ox, oz).y;
   if (moves) {
    var h = moves.PoseAt(8f / 24f, "Hand_R"); var hl = moves.PoseAt(8f / 24f, "Hand_L");
    if (hl.y > h.y) h = hl;
    moves.PoseAt(0, "Hand_R");
    float dy = h.y - (ground + 1.75f); float dx = Mathf.Sqrt(Mathf.Max(0, .78f * .78f - dy * dy));
    float side = Mathf.Sign(h.x - promoter.transform.position.x); if (side == 0) side = 1;
    ox = h.x + side * dx; oz = h.z + .37f;
   }
   var wheel = Rig("Rig_PrizeWheel", new Vector3(ox, ground, oz), 0, "Spin");
   var wheelAnim = CheckoutEventAssets.RigAnimation(wheel);
   var spin = CheckoutEventAssets.ClipState(wheelAnim, "Spin");
   Vector3 hub = new Vector3(ox, ground + 1.75f, oz - .18f); Focus(new Vector3(ox, ground, oz - 1f));
   Prop("Sorteio_GiftBoxes", On(ox + 1.15f, oz + .2f), -20);
   if (!small) Prop("Sorteio_BalloonArch", On(doorW.x, doorW.z - .55f), 0);
   var fans = new[] { Person(Next(), On(hub.x - .3f, hub.z - 1.35f), North), Person(Next(), On(hub.x + .6f, hub.z - 1.55f), Dir(-.2f, 1)) };
   // the raffle's customers watch a spin with the others, then go in (Market.cs)
   Stop(On(hub.x - 1.1f, hub.z - 1.45f), hub, 4f); Stop(On(hub.x + 1.5f, hub.z - 1.35f), hub, 4f);
   director.OnReset(() => { CheckoutEventAssets.PlayClip(wheelAnim, "Spin"); var m = promoter.Moves; if (m) m.PoseAt(0, "Hand_R"); });
   Story(() => Cheer());
   IEnumerator Cheer() {
    // the wheel and the pull share their 10 s clock; everyone claps when it stops (frame 170)
    while (true) {
     float t = spin != null ? Mathf.Repeat(spin.time, spin.length) : Mathf.Repeat(Time.time, 10f);
     bool clap = t > 7.2f && t < 9.4f;
     foreach (var f in fans) if ((f.Move == "Clap") != clap) f.Do(clap ? "Clap" : null);
     yield return null;
    }
   }
  }

  // ================================================================ caminhão de ofertas
  // The supplier's truck parks at the curb (lettering to the street, doors to the curb); a porter pushes pallets of
  // offers with the pallet jack from its back to the display by the market, customers browse and carry boxes in.
  void OffersTruck() {
   var director = this.director;   // the stories run later: they keep this scene's director
   var truck = Vehicle("Rig_BoxTruck", Road(0, LaneW), West);
   float front = EastZoneFrom + .1f, stopX = front + truck.FrontOffset;
   truck.transform.position = Road(stopX, LaneW);
   float rear = stopX + truck.BackOffset;
   BlockCurb(front - .3f, rear + .3f);
   float dx = doorW.x + 3.6f;
   if (!Place(ref dx, 1.8f, 1.6f, -10.6f, -8.65f, 26f)) dx = (front + rear) * .5f;   // no room by the market: sell from beside the truck
   Focus(On((dx + rear) * .5f, -11f));
   Prop("Ofertas_PalletStack", On(dx - 1.0f, -9.3f), 8); Prop("Ofertas_PalletStack", On(dx + .3f, -9.25f), -6);
   Person(Next(), On(dx - .9f, -10.35f), North, "LookPhone"); Person(Next(), On(dx + .4f, -10.45f), Dir(-.2f, 1));
   // customers look through the pallets of offers on their way in (Market.cs)
   Stop(On(dx - 1.7f, -10.15f), On(dx - 1.0f, -9.3f), 2.5f, "GetFromShelf"); Stop(On(dx - .25f, -10.95f), On(dx + .3f, -9.25f), 2.5f, "GetFromShelf");
   var porter = Person(WorkerOr("Worker_Stocker", "Customer_09"), Road(rear + .7f, CurbEdge), North, "HoldHandle", 1, false);
   var jack = Prop("Ofertas_PalletJack", Vector3.zero, 0); var load = art.Prop2(jack, "Ofertas_PalletStack", new Vector3(.58f, .13f, 0), 0, .95f);
   jack.localScale = Vector3.zero;
   var buyer = Person(Next(), On(dx, -10.4f), WestDir, "CarryBox", 1, false);
   void Hitch(Vector3 facing) {   // the jack in front of the porter, forks first, handle at his hands
    porter.Face(facing); var d = facing.normalized;
    jack.position = porter.transform.position + d * .78f; jack.rotation = Quaternion.Euler(0, CheckoutEventVehicle.YawFor(d), 0);
   }
   director.OnReset(() => { porter.Show(false); jack.localScale = Vector3.zero; load.gameObject.SetActive(true); buyer.Show(false); });
   Story(() => Haul()); Story(() => Buy());
   IEnumerator Haul() {
    while (true) {
     porter.transform.position = Road(rear + .5f, LaneW + 1.1f); load.gameObject.SetActive(true);
     Hitch(North); director.StartCoroutine(Grow(jack, true)); yield return porter.Fade(true);
     var go = new[] { On(rear + .5f, CycleLane), On(dx + 2.4f, -10.0f), On(dx + 1.6f, -10.0f) };
     yield return porter.Walk(go, 1.0f, "HoldHandle", jack);
     yield return Wait(1.5f); load.gameObject.SetActive(false);   // the pallet goes onto the display
     Hitch(EastDir);
     yield return porter.Walk(Reverse(go).Skip(1).Concat(new[] { Road(rear + .5f, LaneW + 1.1f) }).ToArray(), 1.1f, "HoldHandle", jack);
     director.StartCoroutine(Grow(jack, false)); yield return porter.Fade(false);
     yield return Wait(4f);
    }
   }
   IEnumerator Buy() {
    while (true) {
     yield return Wait(6f);
     buyer.transform.position = On(dx + .2f, -10.3f); yield return buyer.Fade(true);
     yield return buyer.Walk(ToDoor(buyer.transform.position, -10.3f), 1.1f, "CarryBox"); yield return buyer.Fade(false);
    }
   }
  }
  static IEnumerator Grow(Transform t, bool show) { var to = show ? Vector3.one : Vector3.zero; var from = t.localScale; for (float k = 0; k < .3f; k += Time.deltaTime) { t.localScale = Vector3.Lerp(from, to, k / .3f); yield return null; } t.localScale = to; }

  // ================================================================ dia de jogo
  // Brazil plays on a big screen on the footway; the neighbourhood watches from the street side under the bunting
  // between two flags; every goal everyone jumps (confetti), otherwise they clap or wait.
  void MatchDay() {
   var director = this.director;   // the stories run later: they keep this scene's director
   float x = doorW.x - 5f;
   float back = small ? FootBack : Mathf.Min(facadeZ, -7.8f);
   if (!Place(ref x, 3.4f, 3.4f, back - .75f, back, 26f, -1)) return;
   // the flags and the fans in front of the screen fill the footway there: never in front of the door
   if (wayIn.Overlaps(Rect.MinMaxRect(x - 3.8f, -11.2f, x + 3.8f, -10.3f))) {
    taken.RemoveAt(taken.Count - 1);
    x = x < doorW.x ? wayIn.xMin - 3.9f : wayIn.xMax + 3.9f;
    if (!Place(ref x, 3.4f, 3.4f, back - .75f, back, 8f, x < doorW.x ? -1 : 1) || wayIn.Overlaps(Rect.MinMaxRect(x - 3.8f, -11.2f, x + 3.8f, -10.3f))) return;
   }
   Focus(On(x, -10.2f));
   Prop("Jogo_BigScreen", On(x, back - .4f), 0);
   float f1 = x - 3.2f, f2 = x + 3.2f;
   float Clear(float f) { int away = f < doorW.x ? -1 : 1; for (float d = 0; d <= 2.5f; d += .25f) { var r = Rect.MinMaxRect(f + away * d - .3f, -11.1f, f + away * d + .3f, -10.6f); if (!blockers.Any(b => b.Overlaps(r))) return f + away * d; } return float.NaN; }
   f1 = Clear(f1); f2 = Clear(f2);
   if (float.IsNaN(f1) || float.IsNaN(f2)) { Claim(x - 3.4f, back - .75f, x + 3.4f, back); return; }
   Rig("Rig_FlagPole", On(f1, -10.85f), 0, "Wind"); Rig("Rig_FlagPole", On(f2, -10.85f), 0, "Wind");
   var bunting = Rig("Rig_Bunting", On(f1, -10.85f) + Vector3.up * 3.85f, 0, "Wind"); bunting.localScale = new Vector3((f2 - f1) / 12f, 1, 1);
   Claim(f1 - .3f, -11.1f, f2 + .3f, -10.6f);
   var fans = new List<CheckoutEventActor>();
   for (int i = 0; i < 5; i++) fans.Add(Person(Next(), On(x - 2.2f + i * 1.1f, -10.95f - (i % 2) * .4f), North, null));
   // the match's customers watch a moment at the screen, then go in for beer and meat (Market.cs)
   Stop(On(x - 2.7f, -10.5f), On(x, back - .4f), 4f); Stop(On(x + 2.6f, -10.5f), On(x, back - .4f), 4f);
   Confetti(root, On(x, -10.4f) + Vector3.up * 2.4f);
   var burst = root.GetComponentsInChildren<ParticleSystem>(true).LastOrDefault(); if (burst) { var e = burst.emission; e.enabled = false; }
   Story(() => Game());
   IEnumerator Game() {
    while (true) {
     foreach (var f in fans) f.Do(UnityEngine.Random.value < .35f ? "Clap" : null, UnityEngine.Random.value);
     yield return Wait(UnityEngine.Random.Range(9f, 14f));
     foreach (var f in fans) f.Do("Cheer", UnityEngine.Random.value * .3f);       // goal!
     if (burst) burst.Emit(60);
     yield return Wait(3.2f);
    }
   }
  }

  // ================================================================ café com a equipe
  // The staff take their coffee break at a folding table on the footway beside the market (the chalkboard says
  // CAFÉ): two sit with their cups, one stands and sips.
  void CoffeeBreak() {
   float x = doorW.x - 3.8f;
   if (!Place(ref x, 1.6f, 1.6f, -10.9f, -8.65f, 26f, -1)) return;
   var t = On(x, -9.6f); Focus(t);
   Prop("Cafe_BreakTable", t, 0);
   Prop("Cafe_FoldingChair", t + new Vector3(-1.15f, 0, 0), -90); Prop("Cafe_FoldingChair", t + new Vector3(1.15f, 0, 0), 90);
   Prop("Cafe_CoffeeBoard", On(x + 1.9f, -9.2f), 15);
   Person(WorkerOr("Worker_Cashier", "Customer_07"), t + new Vector3(-1.1f, 0, 0), EastDir, "SitSip");
   Person(WorkerOr("Worker_Stocker", "Customer_09"), t + new Vector3(1.1f, 0, 0), WestDir, "SitSip");
   Person(WorkerOr("Worker_Baker", "Customer_06"), t + new Vector3(.1f, 0, -.95f), North, "Sip");
  }

  // ================================================================ viralizou
  // An influencer films herself with the market behind her (ring light and softbox in front of her), onlookers
  // film her, hearts float up.
  void Influencer() {
   float x = doorW.x + 3.2f;
   if (!Place(ref x, 1.8f, 1.8f, -11.0f, -8.7f, 26f)) return;
   var her = Person(Next(), On(x, -9.35f), South, "FilmPhone"); Focus(On(x, -10f));
   Prop("Viral_RingLightTripod", On(x + .1f, -10.55f), 180);
   Prop("Viral_Softbox", On(x + 1.35f, -9.9f), 135);
   Person(Next(), On(x - 1.5f, -10.75f), Dir(.6f, 1), "LookPhone");
   Person(Next(), On(x + 2.0f, -10.85f), Dir(-.6f, 1), "LookPhone");
   Person(Next(), On(x - .9f, -11.5f), Dir(.3f, 1));
   // her followers watch the filming, then go in for the product of the video (Market.cs)
   Stop(On(x - 2.3f, -10.4f), her.transform.position, 3f); Stop(On(x + 2.7f, -10.3f), her.transform.position, 3f);
   for (int i = 0; i < 4; i++) Fx2(root, "Viral_HeartPop", her.transform.position + new Vector3(-.4f + i * .3f, 2.1f + i * .15f, 0), "rise", 0, 1.1f);
  }

  // ================================================================ rua em obras
  // Road works in the curb lane east of the crossing: the trench behind barriers, the backhoe digging it and
  // dumping the earth on the pile, a detour sign and cones; the city's cars swerve into the inner lane.
  void RoadWorksScene() {
   float pit = EastZoneFrom + 2.35f;
   Prop("Obras_Pit", Road(pit, LaneW - .3f), 0);
   var hoe = Rig("Rig_Backhoe", Road(pit + 6.1f, LaneW), 0, "Dig");
   for (int i = 0; i < 7; i++) Prop("Obras_Barrier", Road(EastZoneFrom + .9f + i * 1.75f, LaneW - 1.45f), 0);
   for (int i = 0; i < 4; i++) art.Cone(root, Road(pit + 10.6f + i * .8f, LaneW - 1.3f + i * .5f));
   BlockCurb(EastZoneFrom - .2f, pit + 12.6f); Focus(Road(pit + 3f, -13.4f));
   float sx = pit + 12.2f;
   if (Place(ref sx, .5f, .5f, -11.0f, -10.4f, 4f)) Prop("Obras_DetourSign", On(sx, -10.75f), 0);
   Person("@crew1", Road(pit - 1.6f, CurbEdge - .25f), Dir(1, -.4f), "Clipboard");
   Person("@crew0", Road(pit + 1.9f, LaneW - 1.05f), Dir(-1, .3f));
  }

  // ================================================================ engarrafamento
  // The avenue is jammed: queues of cars creep stop-and-go in both westbound lanes and the inner eastbound lane
  // (the city's own cars step aside while it lasts); now and then a driver stuck in front of the market gets out,
  // buys water and walks back to the car, the queue behind waiting. Some of the cars are Rig_JamCar (a driver at the
  // wheel, a window that winds down): those are the ones that honk for a drink (CheckoutEventVisuals.Interactive.cs).
  void Jam() {
   var director = this.director;   // the stories run later: they keep this scene's director
   jams.Add(building); Focus(Road(doorW.x + 3f, -14.5f));
   string[] cars = { "Rig_JamCar", "Rig_CarBlue", "Rig_CarWhite", "Rig_JamCar", "Rig_CarYellow", "Rig_CarTeal", "Rig_CarGreen" };
   var lanes = new List<Vector3[]> {
    CheckoutRoundabout.Route(new[] { Road(37, LaneW), Road(-22.4f, LaneW), Road(-22.4f, 37) }),
    CheckoutRoundabout.Route(new[] { Road(37, LaneW2), Road(-37, LaneW2) }),
    CheckoutRoundabout.Route(new[] { Road(-37, LaneE2), Road(37, LaneE2) }),
   };
   var all = new List<JamCar>();
   int k = 0;
   for (int l = 0; l < lanes.Count; l++) {
    var path = lanes[l]; float length = PathLength(path);
    int n = Mathf.FloorToInt(length / 7.2f);
    for (int i = 0; i < n; i++) {
     var rig = cars[(k++) % cars.Length];
     var v = Vehicle(rig, path[0], 0);
     // the driver forward to the window he talks through (and a touch higher in his seat)
     if (rig == "Rig_JamCar") CheckoutBoneNudge.Add(CheckoutEventAssets.Bone(v.transform, "Driver_Root"), v.transform, new Vector3(.3f, .05f, 0));
     var jc = new JamCar { car = v, lane = l, path = path, length = length, s = i * length / n + UnityEngine.Random.Range(-.6f, .6f), phase = UnityEngine.Random.value * 7f, window = rig == "Rig_JamCar" };
     v.YieldToCity = false; all.Add(jc);
    }
   }
   jamCars = all;
   var laneOf = all.ToDictionary(j => j.car.transform, j => j.lane);
   foreach (var jc in all) { var j = jc; j.car.Ignore = other => laneOf.TryGetValue(other, out var l) && l != j.lane && !OnRing(other.position); }
   var lamp = 0f; float bx = doorW.x + 6f;
   if (Place(ref bx, 1.2f, 2.0f, -11.0f, -9.6f, 20f)) Prop("Transito_MessageBoard", On(bx, -10.3f), 0);
   var driver = Person(Next(), Road(0, CurbEdge), North, null, 1, false);
   director.OnReset(() => { foreach (var j in all) j.car.Hold = false; driver.Show(false); });
   Story(() => Creep(all)); Story(() => Water());
   IEnumerator Water() {
    while (true) {
     yield return Wait(12f + lamp);
     // the car in the curb lane nearest the market's door stops; its driver gets out on the curb side
     JamCar pickCar = null; float best = 6f;
     foreach (var j in all) if (j.lane == 0 && !j.window) { var p = j.car.transform.position; float d = Mathf.Abs(p.x - (doorW.x + 2f)); if (Mathf.Abs(p.z - LaneW) < .3f && d < best) { best = d; pickCar = j; } }
     if (pickCar == null) continue;
     pickCar.car.Hold = true; yield return Wait(.8f);
     var at = pickCar.car.transform.position; driver.transform.position = Road(at.x, CurbEdge - .15f); driver.Face(North);
     yield return driver.Fade(true);
     var route = ToDoor(driver.transform.position, -10.6f);
     yield return driver.Walk(route, 1.3f); yield return driver.Fade(false);
     yield return Wait(5f);
     yield return driver.Fade(true);
     yield return driver.Walk(Reverse(route).Skip(1).ToArray(), 1.3f, "CarryBox");
     yield return driver.Fade(false); driver.Do(null);
     pickCar.car.Hold = false;
     lamp = UnityEngine.Random.Range(4f, 12f);
    }
   }
  }
  sealed class JamCar { public CheckoutEventVehicle car; public int lane; public Vector3[] path; public float length, s, speed, phase, waited; public bool window; }
  List<JamCar> jamCars;
  static bool HeldAhead(List<JamCar> all, JamCar j) {
   var at = j.car.transform.position; var heading = j.car.Forward;
   foreach (var o in all) {
    if (o == j || !o.car.Hold) continue;
    var d = o.car.transform.position - at; d.y = 0;
    float along = Vector3.Dot(d, heading);
    if (along > 0 && along < 9f && (d - heading * along).magnitude < 1.4f) return true;
   }
   return false;
  }
  static float PathLength(Vector3[] p) { float l = 0; for (int i = 1; i < p.Length; i++) l += Vector3.Distance(p[i - 1], p[i]); return l; }
  static Vector3 AlongPath(Vector3[] p, float s, out Vector3 dir) {
   for (int i = 1; i < p.Length; i++) { float l = Vector3.Distance(p[i - 1], p[i]); if (s <= l || i == p.Length - 1) { dir = (p[i] - p[i - 1]).normalized; return Vector3.Lerp(p[i - 1], p[i], l > 0 ? Mathf.Clamp01(s / l) : 0); } s -= l; }
   dir = Vector3.right; return p[p.Length - 1];
  }
  static bool OnRing(Vector3 p) { var c = CheckoutRoundabout.Current; return c && Vector2.Distance(new Vector2(p.x, p.z), new Vector2(c.center.x, c.center.z)) < c.clipRadius + .4f; }
  IEnumerator Creep(List<JamCar> all) {
   // stop-and-go: every lane breathes on a slow wave; each car keeps its gap to whatever is ahead
   foreach (var j in all) { var p = AlongPath(j.path, Mathf.Repeat(j.s, j.length), out var d); j.car.transform.position = p; j.car.Face(d); }
   while (true) {
    float dt = Time.deltaTime, now = Time.time;
    foreach (var j in all) {
     float wave = 1.1f * (1 - Mathf.Cos(2 * Mathf.PI * (now + j.phase * .15f - j.s * .02f) / 7f));
     var front = j.car.Front; var heading = j.car.Forward;
     bool blocked = j.car.Hold || CheckoutEventTraffic.Blocks(front - heading * .3f, heading, 1.6f + j.speed * .8f, .9f, j.car.transform, j.car.Ignore)
      || CheckoutEventTraffic.CityAhead(front, heading, 1.4f, .9f);
     // never a gridlock on the roundabout: after a long wait a car edges on anyway
     // (but never into a car that waits on purpose: a driver buying through the window, one that went shopping)
     j.waited = blocked && !j.car.Hold && !HeldAhead(all, j) ? j.waited + dt : 0;
     if (j.waited > 7f) blocked = j.waited > 8.5f ? (j.waited = 0) > 1 : false;
     float target = blocked ? 0 : wave;
     j.speed = Mathf.MoveTowards(j.speed, target, (target < j.speed ? 4f : 1.4f) * dt);
     float step = j.speed * dt; j.s += step;
     bool wrapped = j.s > j.length; if (wrapped) j.s -= j.length;   // off the map's edge, back in at the other end
     var p = AlongPath(j.path, j.s, out var d);
     j.car.transform.position = p;
     var want = Quaternion.Euler(0, CheckoutEventVehicle.YawFor(d), 0);
     j.car.transform.rotation = wrapped ? want : Quaternion.RotateTowards(j.car.transform.rotation, want, dt * 120f);
     j.car.Moved(step, dt);
    }
    yield return null;
   }
  }

  // ================================================================ fim do mês
  // The pharmacy across the side street holds a clearance sale (LIQUIDA TUDO banner on its avenue wall, A-frames on
  // its sidewalk), two shoppers in front of it and an A-frame by the market door.
  void MonthEnd() {
   var sim = FindAnyObjectByType<MarketSimulation>();
   var shop = sim && sim.world ? sim.world.Find("City Establishments/Pharmacy") : null;
   if (shop) {
    var rs = shop.GetComponentsInChildren<Renderer>().Where(r => r.enabled).ToArray();
    if (rs.Length > 0) {
     var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
     float cx = b.center.x, wall = b.min.z; Focus(On(cx, wall - 1.5f));
     Rig("Rig_SaleBanner", new Vector3(cx, On(cx, wall - .3f).y, wall - .06f), 0, "Wind");
     Prop("FimMes_PriceTags", new Vector3(cx, On(cx, wall - .3f).y, wall - .08f), 0);
     Prop("FimMes_AFrame", On(cx - 1.6f, wall - 1.3f), 10); Prop("FimMes_AFrame", On(cx + 1.8f, wall - 1.4f), -12);
     Person(Next(), On(cx - .5f, wall - 1.6f), North, "LookPhone"); Person(Next(), On(cx + .7f, wall - 2.0f), Dir(-.3f, 1));
     // bargain hunters compare the clearance's prices, then come to the market for the cheap products (Market.cs)
     Stop(On(cx - .1f, wall - 1.0f), On(cx, wall), 3f); Stop(On(cx + 2.6f, wall - 1.9f), On(cx, wall), 3f);
    }
   }
   float ax = doorW.x + 2.6f;
   if (Place(ref ax, .4f, .4f, -10.95f, -10.35f, 6f)) Prop("FimMes_AFrame", On(ax, -10.65f), 20);
  }

  // ================================================================ maquininha fora do ar
  // The operator's van parks at the curb west of the crossing; on the telecom pole a technician up the ladder works
  // on the box (its LED blinking), the other checks the list at the van; SÓ DINHEIRO at the market.
  void CardsDown() {
   var van = Vehicle("Rig_TelecomVan", Road(0, LaneW), West);
   float front = WestZoneFrom + .1f, vx = front + van.FrontOffset;
   van.transform.position = Road(vx, LaneW);
   BlockCurb(WestZoneFrom - .2f, vx + van.BackOffset + .3f);
   float px = vx;
   // the pole, its ladder and the cable reel beside it: on free footway, never in the way in (looks further along
   // the street when the van's spot is in front of the door)
   if (!Place(ref px, .5f, 1.9f, -11.2f, -9.3f, 6f) && !Place(ref px, .5f, 1.9f, -11.2f, -9.3f, 26f)) px = float.NaN;
   if (float.IsNaN(px)) { Person(Next(), On(vx + van.BackOffset - .4f, CurbEdge + .25f), Dir(-.4f, 1), "Clipboard"); CashOnly(); return; }
   var pole = Prop("Maquininha_TelecomPole", On(px, -9.55f), 0); Focus(On(px, -10.8f));
   Fx2(pole, "Maquininha_CtoLed", new Vector3(.11f, 4.52f, -.5f), "blink");
   Prop("Maquininha_Ladder", On(px, -11.0f), 0);
   // standing on the ladder ~2.1 m up, leaning in to the box
   var tech = Person("@crew0", new Vector3(px, On(px, -11f).y + 2.1f, -10.55f), North, "WorkOverhead");
   Prop("Maquininha_CableReel", On(px + 1.3f, -10.7f), 0);
   Person(Next(), On(vx + van.BackOffset - .4f, CurbEdge + .25f), Dir(-.4f, 1), "Clipboard");
   CashOnly();
  }
  // SÓ DINHEIRO beside the way in (on the door glass at the shop), and a customer reading it off to the side
  void CashOnly() {
   var sign = doorW + (small ? new Vector3(CheckoutStall.ShopInside ? 2.3f : 1.45f, 1.35f, -.1f) : new Vector3(.3f, 1.95f, -.12f));
   Prop("Maquininha_CashOnlySign", sign, 0);
   float side = small ? (CheckoutStall.ShopInside ? 2.9f : 2.1f) : 3.0f;
   Person(Next(), On(doorW.x + side, Mathf.Min(doorW.z - .5f, FootBack - .3f)), Dir(-.6f, 1), "LookPhone");
  }

  // ================================================================ excursão da escola
  // The school bus parks at the curb; the class gets off in a line behind the teacher, walks into the market
  // (a second teacher counts them at the door) and later comes back out and boards; the bus leaves, another comes.
  // The trip's customers (Customer.origin: the parents and teachers along) ride this bus, get off after the class and
  // really shop (Market.cs).
  void SchoolTrip() {
   var director = this.director;   // the stories run later: they keep this scene's director
   var id = building; BusRiders();
   var bus = Vehicle("Rig_SchoolBus", Road(37, LaneW), West);
   float front = EastZoneFrom + .1f, stopX = front + bus.FrontOffset, sideZ = LaneW + bus.HalfWidth + .22f;
   var doorList = DoorCentres(bus, stopX); float doorX = doorList.Count > 0 ? doorList[0] : stopX - 2.2f;
   Focus(On((doorX + doorW.x) * .5f, -11f));
   var kids = new List<CheckoutEventActor>();
   for (int i = 0; i < 8; i++) kids.Add(Person(Next(), On(doorX, sideZ), North, null, .58f, false));
   var teacher = Person(Next(), On(doorX, sideZ), North, null, 1, false);
   float countAt = small ? (CheckoutStall.ShopInside ? 2.6f : 1.8f) : 2.9f;   // beside the way in, not in it
   var counter = Person(Next(), On(doorW.x + countAt, Mathf.Min(doorW.z - .6f, FootBack - .4f)), Dir(-.7f, -1), "Clipboard");
   director.OnReset(() => { bus.transform.position = Road(37, LaneW); bus.Face(WestDir); foreach (var c in kids) c.Show(false); teacher.Show(false); });
   Story(() => Trip());
   IEnumerator Trip() {
    while (true) {
     bus.gameObject.SetActive(true);
     yield return bus.Drive(ArriveWest(stopX), 6f);
     yield return bus.Clip("DoorsOpen");
     bus.gameObject.SetActive(true);
     teacher.transform.position = On(doorX, sideZ); yield return teacher.Fade(true);
     yield return teacher.Walk(new[] { On(doorX - .9f, CycleLane + .2f) }, 1.2f); teacher.Face(Dir(.4f, -1)); teacher.Do("Wave");
     var route = ToDoor(On(doorX, sideZ));
     for (int i = 0; i < kids.Count; i++) { var kid = kids[i]; kid.transform.position = route[0]; director.StartCoroutine(Walk(kid, route, 1.0f + .1f * (i % 3))); yield return Wait(.7f); }
     foreach (var r in TakeRiders(id, 4)) { RiderGetsOff(r, On(doorX, sideZ)); yield return Wait(.8f); }
     yield return Wait(3f); teacher.Do(null);
     yield return teacher.Walk(route.Skip(1).ToArray(), 1.15f); yield return teacher.Fade(false);
     yield return Wait(14f);                                      // shopping inside
     var back = Reverse(route);
     teacher.transform.position = back[0]; yield return teacher.Fade(true);
     director.StartCoroutine(teacher.Walk(back.Skip(1).ToArray(), 1.2f));
     for (int i = 0; i < kids.Count; i++) { var kid = kids[i]; kid.transform.position = back[0]; director.StartCoroutine(Walk(kid, back, 1.05f + .1f * (i % 3))); yield return Wait(.7f); }
     yield return Wait(route.Length > 0 ? PathLength(route) / 1.0f + 1f : 6f);
     yield return teacher.Fade(false);
     yield return bus.Clip("DoorsClose"); yield return Wait(.5f);
     yield return bus.Drive(LeaveWest(stopX), 6f, false);
     bus.gameObject.SetActive(false);
     bus.transform.position = Road(37, LaneW); bus.Face(WestDir);
     yield return Wait(10f);
    }
   }
   IEnumerator Walk(CheckoutEventActor kid, Vector3[] path, float speed) { yield return kid.Fade(true, .25f); yield return kid.Walk(path, speed); yield return kid.Fade(false, .25f); }
  }

  // ================================================================ queda de energia
  // The transformer on the pole blew (sparks, smoke); the power company's truck parks at the curb with its boom
  // swung over the footway and the lineman works on the transformer from the basket; a colleague watches below.
  void PowerCut() {
   var truck = Vehicle("Rig_BucketTruck", Road(0, LaneW), West);
   truck.Idle("Work");
   float front = EastZoneFrom + .1f, tx = front + truck.FrontOffset;
   truck.transform.position = Road(tx, LaneW);
   var seat = CheckoutEventAssets.Bone(truck.transform, "Seat");
   var work = CheckoutEventAssets.ClipState(CheckoutEventAssets.RigAnimation(truck.transform), "Work");
   if (work != null) work.clip.SampleAnimation(CheckoutEventAssets.RigAnimation(truck.transform).gameObject, 2.4f);   // the boom where it holds
   BlockCurb(front - .3f, tx + truck.BackOffset + .4f);
   var s = seat ? seat.position : new Vector3(tx + 3.7f, 3.75f, -10.3f);
   // the transformer hangs on the street side of the pole, an arm's length in front of the lineman
   float px = s.x, pz = s.z + .45f + .62f;
   if (!Place(ref px, .3f, .3f, pz - .4f, pz + .4f, 1.5f)) px = s.x;
   var pole = Prop("Energia_UtilityPole", On(px, pz), 0); Focus(On(px - 1f, -11f));
   Fx2(pole, "Energia_Spark", new Vector3(.1f, 6.0f, -.95f), "flicker");
   Fx2(pole, "Energia_Smoke", new Vector3(-.2f, 6.5f, -.7f), "rise");
   var lineman = Person("@crew0", s, North, "WorkOverhead");
   if (seat) Ride(lineman.transform, seat, Vector3.zero);
   Person(Next(), On(px - 1.2f, FootMid - .6f), Dir(.5f, .4f), "Clipboard");
   for (int i = 0; i < 3; i++) art.Cone(root, Road(tx + truck.BackOffset + .9f + i * .7f, LaneW - 1.3f + i * .7f));
  }

  // ================================================================ turno puxado
  // Exhausted staff: sleepy bubbles follow every worker around, empty coffee cups by the till, a yawning clock on
  // the shop front.
  void TiredShift() {
   var sim = FindAnyObjectByType<MarketSimulation>();
   if (sim && sim.world)
    foreach (var a in sim.world.GetComponentsInChildren<MarketCharacterAnimator>(true))
     if (a.name.StartsWith("Worker_") || a.name.StartsWith("StockWorker") || a.name.StartsWith("Staff")) {
      var b = art.Prop2(root, "Turno_SleepyBubble", a.transform.position + Vector3.up * 2.7f, 0, .9f);
      Follow(b, a.transform, Vector3.up * 2.7f);
     }
   var cashier = sim && sim.world ? sim.world.Find("Worker_Cashier") : null;
   var till = cashier && cashier.gameObject.activeInHierarchy ? cashier.position : CheckoutStall.Register;
   if (small || !cashier || !cashier.gameObject.activeInHierarchy) {
    // the stall's clerk, worn out behind the counter
    var clerk = Person(WorkerOr("Worker_Cashier", "Customer_07"), new Vector3(till.x, On(till.x, till.z + .7f).y, till.z + .7f), South, "Tired");
    var b = art.Prop2(root, "Turno_SleepyBubble", clerk.transform.position + Vector3.up * 2.7f, 0, .9f); Follow(b, clerk.transform, Vector3.up * 2.7f);
    Prop("Turno_CoffeeCups", new Vector3(till.x - .35f, till.y + .05f, till.z), 0);
   } else Prop("Turno_CoffeeCups", till + new Vector3(.55f, .95f, -.45f), 0);
   Focus(till);
   if (!small) Prop("Turno_YawnClock", new Vector3(doorW.x - 1.9f, doorW.y + 2.3f, doorW.z - .08f), 0, 1.8f);
  }

  // ================================================================ vigilância sanitária
  // The health inspection's car parks at the curb west of the crossing. The
  // inspector gets out of the car and walks the shop floor to each of her stops (CheckoutEventVisuals.Interactive.cs).
  void Inspection() {
   var car = Vehicle("Rig_InspectionCar", Road(0, LaneW), West);
   float front = WestZoneFrom + .2f, cx = front + car.FrontOffset;
   car.transform.position = Road(cx, LaneW);
   BlockCurb(WestZoneFrom - .2f, cx + car.BackOffset + .3f); Focus(On((cx + doorW.x) * .5f, -10.5f));
   inspectionCurb = Road(cx + .5f, CurbEdge - .1f);
  }
  Vector3 inspectionCurb;

  // ================================================================ carro de som
  // The rival's sound car drives slowly along the eastbound lane (round the roundabout), the city's cars behind it
  // held up.
  void SoundCar() {
   var director = this.director;   // the stories run later: they keep this scene's director
   var van = Vehicle("Rig_SoundVan", Road(-37, LaneE2), East);
   var path = CheckoutRoundabout.Route(new[] { Road(-37, LaneE2), Road(37, LaneE2) }); Focus(Road(doorW.x, -17f));
   director.OnReset(() => { van.transform.position = path[0]; van.Face(EastDir); });
   Story(() => Tour());
   IEnumerator Tour() {
    while (true) {
     yield return van.Drive(path, 3.2f, false, 1.2f);
     yield return Wait(5f);
    }
   }
  }
 }
}
