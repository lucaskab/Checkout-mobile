using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 /// <summary>
 /// Caramelo, the store dog (src/services/store-pet.ts → Snapshot.pet). Lives inside the market once adopted: wanders
 /// between the shelves, sniffs, sits near the shoppers, naps by the checkout (on its bed when bought), wakes up for
 /// a pat (tap → "petDog": hearts + the happy clip) and barks at a shoplifter (Snapshot.security.thief.dogBarked).
 /// Before the adoption it sits outside the entrance with a heart balloon; a tap adopts it ("adoptPet").
 /// Art: Resources/CheckoutPets (ArtSource/pets, Legacy clips Dog_*).
 /// </summary>
 public class CheckoutPets : MonoBehaviour {
  CheckoutBridge bridge; CheckoutMap map;
  Transform root, model, holder, bubble, bed, bowls; Animation anim; string clip; float phase; Vector3 lastPos;
  readonly List<Vector3> path = new List<Vector3>(); int pathIndex; float speed;
  enum Mode { None, Offer, Walk, Idle, Sniff, Sit, Sleep, Happy, Bark, Stretch, Arriving, Chase, ChaseOff, Hero, HopIn }
  Mode mode = Mode.None; float modeUntil, nextNap, repathAt, nextWoof; Transform chased; string pendingAfterWalk; Vector3 faceTarget;
  string collarId = "", bandanaId = ""; bool hasBed, hasBowls;
  const float Scale = 1.08f;
  static readonly Dictionary<string, string> CollarColors = new Dictionary<string, string> {
   { "collar_navy", "1E2D5C" }, { "collar_red", "C8372D" }, { "collar_green", "2F8F5B" }, { "collar_gold", "E0B04A" } };
  public static CheckoutPets Instance { get; private set; }
  NavMeshPath navPath;

  public void Initialize(CheckoutBridge b, CheckoutMap m) { bridge = b; map = m; Instance = this; CheckoutBridge.Received += Apply; }
  void OnDestroy() { CheckoutBridge.Received -= Apply; if (holder) Destroy(holder.gameObject); }

  PetState Pet => bridge?.State?.pet;
  bool Adopted => Pet != null && Pet.adopted;

  // ------------------------------------------------------------------ snapshot
  void Apply(Snapshot s) {
   var pet = s.pet;
   bool show = pet != null && (pet.adopted || pet.offer) && !CheckoutSocial.Visiting;
   if (!show) { if (root) root.gameObject.SetActive(false); mode = Mode.None; return; }
   if (!root && !Build()) return;
   if (!root.gameObject.activeSelf) { root.gameObject.SetActive(true); Place(pet.adopted ? HomeSpot() : OfferSpot()); mode = Mode.None; }
   if (pet.adopted && mode == Mode.Offer) { HideBubble(); Arrive(); }
   if (!pet.adopted && mode != Mode.Offer) { mode = Mode.Offer; Place(OfferSpot()); ShowBubble(); }
   if (pet.collar != collarId || pet.bandana != bandanaId) Dress(pet.collar, pet.bandana);
   if (pet.hasBed != hasBed || pet.hasBowls != hasBowls || (bed && bed.gameObject.activeSelf && (bed.position - BedSpot()).sqrMagnitude > .04f)) Furniture(pet.hasBed, pet.hasBowls);
   // a shoplifter just grabbed something and the dog saw it: run and bark at him
   var thief = s.security?.thief;
   if (pet.adopted && thief != null && !string.IsNullOrEmpty(thief.id) && thief.dogBarked && thief.phase == "fleeing" && mode != Mode.Bark && barkedAt != thief.id) {
    barkedAt = thief.id; StartBark();
   }
  }
  string barkedAt;

  bool Build() {
   var prefab = Resources.Load<GameObject>("CheckoutPets/Caramelo");
   if (!prefab) { Debug.LogWarning("CHECKOUT_PET_MISSING Resources/CheckoutPets/Caramelo"); return false; }
   holder = new GameObject("Store dog").transform; holder.SetParent(transform, false);
   root = new GameObject("Caramelo").transform; root.SetParent(holder, false);
   model = Instantiate(prefab, root, false).transform; model.name = "Caramelo model"; model.localScale = Vector3.one * Scale;
   // the dog's FBX faces +Z (the market's convention is -Z): turned so he looks where he walks
   model.localRotation = Quaternion.Euler(0, 180, 0);
   var albedo = Resources.Load<Texture2D>("CheckoutPets/Caramelo_albedo");
   var coat = new Material(Shader.Find("Standard")) { name = "Caramelo coat", mainTexture = albedo, color = Color.white };
   coat.SetFloat("_Glossiness", .14f); coat.SetFloat("_Metallic", 0);
   foreach (var r in model.GetComponentsInChildren<Renderer>(true)) {
    if (r is SkinnedMeshRenderer sk) sk.updateWhenOffscreen = true;
    if (!r.name.Contains("Collar") && !r.name.Contains("Tag") && !r.name.Contains("Bandana")) r.sharedMaterial = coat;
   }
   anim = model.GetComponentInChildren<Animation>(true);
   if (anim) { anim.playAutomatically = false; anim.cullingType = AnimationCullingType.AlwaysAnimate; foreach (AnimationState st in anim) st.wrapMode = Loops(st.name) ? WrapMode.Loop : WrapMode.ClampForever; }
   var box = root.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, .42f, 0); box.size = new Vector3(.75f, .9f, 1.2f);
   root.gameObject.AddComponent<CheckoutTarget>().panel = "pet";
   Dress("collar_navy", "");
   FeetOnFloor();
   return true;
  }
  /// <summary>QA: lowest point of the dog vs where he stands.</summary>
  public string Heights() {
   if (!root || !model) return "dog=off";
   float min = float.MaxValue; var tmp = new Mesh();
   foreach (var sk in model.GetComponentsInChildren<SkinnedMeshRenderer>(true)) { if (!sk.gameObject.activeInHierarchy) continue; sk.BakeMesh(tmp, true); foreach (var v in tmp.vertices) { var w = sk.transform.position + sk.transform.rotation * v; if (w.y < min) min = w.y; } }
   Destroy(tmp);
   var nav = NavMesh.SamplePosition(root.position, out var h, 2f, NavMesh.AllAreas) ? h.position.y : float.NaN;
   return $"dog: root {root.position.y:0.000} feet {min:0.000} nav {nav:0.000} walkerY {WalkerY(root.position):0.000}";
  }
  // Paws on the floor: the standing pose is sampled once and the model lifted so its lowest point sits on the ground
  // (the coat sank into the floor by half a leg).
  void FeetOnFloor() {
   if (!anim || !anim["Dog_Idle"]) return;
   var st = anim["Dog_Idle"]; anim.Play("Dog_Idle"); st.time = 0; st.enabled = true; st.weight = 1; anim.Sample();
   float min = float.MaxValue; var tmp = new Mesh();
   foreach (var sk in model.GetComponentsInChildren<SkinnedMeshRenderer>(true)) {
    if (sk.name.Contains("Bandana") || sk.name.Contains("Collar") || sk.name.Contains("Tag")) continue;
    sk.BakeMesh(tmp, true);
    foreach (var v in tmp.vertices) { var w = sk.transform.position + sk.transform.rotation * v; if (w.y < min) min = w.y; }
   }
   Destroy(tmp);
   if (min == float.MaxValue) return;
   var lift = root.position.y - min;
   if (Mathf.Abs(lift) > .005f && Mathf.Abs(lift) < .6f) model.localPosition += Vector3.up * lift;
   Debug.Log($"CHECKOUT_PET feet lift {lift:0.000}");
  }
  static bool Loops(string n) => n.EndsWith("Idle") || n.EndsWith("Walk") || n.EndsWith("Trot") || n.EndsWith("Sleep") || n.EndsWith("Happy") || n.EndsWith("Sniff") || n.EndsWith("SitIdle");

  void Dress(string collar, string bandana) {
   collarId = collar ?? ""; bandanaId = bandana ?? "";
   if (!model) return;
   var c = MarketDay.MarketSimulation.C(CollarColors.TryGetValue(collarId, out var hex) ? hex : CollarColors["collar_navy"]);
   foreach (var r in model.GetComponentsInChildren<Renderer>(true)) {
    var n = r.name;
    if (n.Contains("Collar")) { r.material.color = c; r.gameObject.SetActive(true); }
    else if (n.Contains("Tag")) r.gameObject.SetActive(true);
    else if (n.Contains("Bandana")) {
     bool on = !string.IsNullOrEmpty(bandanaId) && n.ToLowerInvariant().Contains(bandanaId.Replace("bandana_", ""));
     r.gameObject.SetActive(on);
     if (on && !r.sharedMaterial.mainTexture) {
      var tex = Resources.Load<Texture2D>("CheckoutPets/" + bandanaId);
      if (tex) { var m = new Material(Shader.Find("Standard")) { mainTexture = tex }; m.SetFloat("_Glossiness", .1f); r.sharedMaterial = m; }
     }
    }
   }
  }

  void Furniture(bool wantBed, bool wantBowls) {
   hasBed = wantBed; hasBowls = wantBowls;
   bed = Prop(bed, "PetBed", wantBed && BedItem() == null, BedSpot(), 0);   // (a bed bought in the build mode replaces it)
   bowls = Prop(bowls, "PetBowls", wantBowls, BedSpot() + SideOf(BedSpot()) * .85f, 0);
  }
  Transform Prop(Transform current, string name, bool want, Vector3 at, float yaw) {
   if (!want) { if (current) current.gameObject.SetActive(false); return current; }
   if (!current) {
    var prefab = Resources.Load<GameObject>("CheckoutPets/" + name); if (!prefab) return null;
    current = Instantiate(prefab, holder, false).transform; current.name = name;
    var tex = Resources.Load<Texture2D>("CheckoutPets/" + name + "_albedo");
    if (tex) { var m = new Material(Shader.Find("Standard")) { mainTexture = tex }; m.SetFloat("_Glossiness", .12f); foreach (var r in current.GetComponentsInChildren<Renderer>(true)) r.sharedMaterial = m; }
   }
   current.gameObject.SetActive(true); current.position = Ground(at);
   var toCenter = map.Register - at; toCenter.y = 0; if (toCenter.sqrMagnitude > .01f) current.rotation = Quaternion.LookRotation(-toCenter.normalized);
   return current;
  }

  // ------------------------------------------------------------------ places
  Vector3 Ground(Vector3 p) { var q = NavMesh.SamplePosition(p, out var hit, 2f, NavMesh.AllAreas) ? hit.position : p; q.y = WalkerY(q); return q; }
  // The floor the market's own walkers stand on (CheckoutWalker.Sync): the small shops' raised floor inside, the
  // big market's ramped floor, the sidewalk outside. The NavMesh is only used for x/z (its height is the slab under).
  float WalkerY(Vector3 p) {
   if (CheckoutEntranceFloor.TryHeight(p, out var steps)) return steps;     // the steps and the threshold at the door
   var u = CheckoutMarketLayout.Unproject(p, bridge?.State?.layout ?? new MarketLayout());
   if (CheckoutStall.ShopInside && CheckoutStall.InteriorFloor.Contains(new Vector2(p.x, p.z))) return CheckoutStall.FloorY;
   return CheckoutStall.Small || u.x < -9.4f || u.x > 9.4f || u.z < -10.6f ? .15f : MarketDay.MarketSimulation.Ground(u.z);
  }

  // The NavMesh lies a little under the shop's floor tiles (the dog sank by half a leg): the visible floor is found
  // with a ray straight down near the NavMesh height (never a counter or a shelf: only within 25 cm of it).
  static float FloorAt(Vector3 p, float navY, Transform ignore) {
   var hits = Physics.RaycastAll(new Vector3(p.x, navY + .25f, p.z), Vector3.down, .5f, ~0, QueryTriggerInteraction.Ignore);
   float best = navY; bool found = false;
   foreach (var h in hits) { if (ignore && h.transform.IsChildOf(ignore)) continue; if (!found || h.point.y > best) { best = h.point.y; found = true; } }
   return found ? best : navY;
  }

  Vector3 SideOf(Vector3 p) { var d = p - map.Register; d.y = 0; var side = Vector3.Cross(Vector3.up, d.sqrMagnitude > .01f ? d.normalized : Vector3.forward); return side.normalized; }
  // Beside the main checkout, a step towards the inside of the shop: the dog's nap spot (and its bed).
  Vector3 BedSpot() { var reg = map.Register; var toIn = map.Entrance - reg; toIn.y = 0; var side = Vector3.Cross(Vector3.up, toIn.sqrMagnitude > .01f ? toIn.normalized : Vector3.forward); return Ground(reg + side * 1.4f - toIn.normalized * .4f); }
  Vector3 HomeSpot() => BedSpot();
  // Outside, by the door: where the stray waits to be adopted.
  Vector3 OfferSpot() { var door = map.Entrance; var outward = door - map.Register; outward.y = 0; return Ground(door + outward.normalized * 1.6f + SideOf(door) * .9f); }
  Vector3 RandomSpot() {
   var spots = new List<Vector3>();
   var st = bridge.State;
   if (st?.shelves != null) foreach (var s in st.shelves) if (s.unlocked) spots.Add(map.Approach(s.id));
   spots.Add(map.Register + SideOf(map.Register) * 1.2f);
   spots.Add(map.Entrance - (map.Entrance - map.Register).normalized * 1.2f);
   var p = spots[Random.Range(0, spots.Count)] + new Vector3(Random.Range(-.5f, .5f), 0, Random.Range(-.5f, .5f));
   // now and then a stroll out on the sidewalk in front of the shop (Lucas 08/11: "ou lá fora, na rua também")
   if (Random.value < .3f) { var away = map.Entrance - map.Register; away.y = 0; away = away.sqrMagnitude > .01f ? away.normalized : Vector3.back; p = map.Entrance + away * Random.Range(1.5f, 3f) + Vector3.Cross(Vector3.up, away) * Random.Range(-3.5f, 3.5f); }
   return Ground(p);
  }

  // ------------------------------------------------------------------ his bed (a decoration placed in the build mode)
  // Where he lies on each bed (the model's own metres: x, z of the spot, height of the cushion top, yaw added). The
  // beds face -Z in the game (their front, where he steps in and looks out).
  // (x, z, lift, yaw) on each bed. He sleeps curled up (Dog_CurlSleep, a ~0.65 m donut): on the oval / wide beds he
  // turns 90° so the donut's long side runs along the bed (Lucas 09/11: he went through the beds lying stretched out).
  // The house's mat is too small for the donut: there he lies stretched out in the doorway, rump inside and chin on the
  // mat (Dog_Sleep, facing out of the house).
  static readonly HashSet<string> StretchBeds = new HashSet<string> { "pet-bed-house" };
  static readonly Dictionary<string, Vector4> BedSeats = new Dictionary<string, Vector4> {
   { "pet-bed-round", new Vector4(0, 0, .09f, 0) }, { "pet-bed-basket", new Vector4(0, 0, .12f, 90) }, { "pet-bed-house", new Vector4(0, .04f, .09f, 0) },
   { "pet-bed-sofa", new Vector4(0, -.05f, .3f, 90) }, { "pet-bed-royal", new Vector4(0, 0, .3f, 90) } };
  CheckoutInterior.Item sleepingOn; Vector3 sleptAt;
  /// <summary>The bed he uses: the placed one nearest to him (inside or outside the shop); null = none placed.</summary>
  CheckoutInterior.Item BedItem() {
   var inside = CheckoutInterior.Active; if (!inside || !root) return null;
   CheckoutInterior.Item best = null; float bd = float.MaxValue;
   foreach (var it in inside.items.Values) {
    if (it == null || it.type == null || !it.type.StartsWith("pet-bed") || it.ghost || it.building || !it.root || !it.root.gameObject.activeInHierarchy) continue;
    float d = (it.root.position - root.position).sqrMagnitude; if (d < bd) { bd = d; best = it; }
   }
   return best;
  }
  void BedSeat(CheckoutInterior.Item b, out Vector3 seat, out Quaternion facing, out float lift) {
   var s = BedSeats.TryGetValue(b.type, out var v) ? v : new Vector4(0, 0, .08f, 0);
   seat = b.root.TransformPoint(new Vector3(s.x, 0, s.y)); seat.y = b.root.position.y;
   facing = Quaternion.Euler(0, b.root.eulerAngles.y + s.w, 0); lift = s.z * b.root.lossyScale.y;
  }
  /// <summary>Where he walks to before hopping onto the bed (in front of it, on the NavMesh); no bed: the old spot.</summary>
  Vector3 BedApproach() {
   var b = BedItem(); if (b == null) return HomeSpot();
   BedSeat(b, out var seat, out _, out _);
   var out_ = Quaternion.Euler(0, b.root.eulerAngles.y, 0) * Vector3.back;        // the bed's front (models: -Z)
   var front = seat + out_ * .75f;
   foreach (var tryAt in new[] { front, seat - out_ * .75f, seat })
    if (NavMesh.SamplePosition(tryAt, out var hit, .7f, NavMesh.AllAreas)) return Ground(hit.position);
   return Ground(front);
  }
  // A little hop onto the cushion, a turn, and he curls up (Dog_CurlDown → Dog_CurlSleep).
  IEnumerator HopIn(CheckoutInterior.Item b) {
   mode = Mode.HopIn;
   BedSeat(b, out var seat, out var facing, out var lift);
   var from = root.position; var to = new Vector3(seat.x, WalkerY(seat) + lift, seat.z);
   var d = to - from; d.y = 0; if (d.sqrMagnitude > .01f) root.rotation = Quaternion.LookRotation(-d.normalized);
   float t = 0, dur = Mathf.Clamp(d.magnitude / 1.4f, .25f, .7f);
   while (t < dur && root) {
    t += Time.deltaTime; float k = Mathf.Clamp01(t / dur);
    root.position = Vector3.Lerp(from, to, k) + Vector3.up * Mathf.Sin(k * Mathf.PI) * .18f;
    PlayScrubbed("Dog_Trot", Mathf.Repeat(k * 1.5f, 1));
    yield return null;
   }
   if (!root || mode != Mode.HopIn) yield break;
   root.position = to;
   // he lies down facing out of the bed (the model's front), turning in place like dogs do
   var want = facing;                                                               // (the models' front is +Z here)
   for (float r = 0; r < .35f && root; r += Time.deltaTime) { root.rotation = Quaternion.RotateTowards(root.rotation, want, 520 * Time.deltaTime); yield return null; }
   if (!root || mode != Mode.HopIn) yield break;
   root.rotation = want; lastPos = root.position;
   sleepingOn = b; sleptAt = b.root.position;
   Play(StretchBeds.Contains(b.type) ? "Dog_LieDown" : "Dog_CurlDown"); mode = Mode.Sleep;
   modeUntil = bridge.State.isOpen ? Time.time + Random.Range(28f, 45f) : 0;          // closed: until the shop opens
  }
  void Place(Vector3 p) { root.position = Ground(p); lastPos = root.position; path.Clear(); }

  bool PathTo(Vector3 target) {
   path.Clear(); pathIndex = 0;
   if (navPath == null) navPath = new NavMeshPath();
   if (NavMesh.SamplePosition(root.position, out var a, 1.5f, NavMesh.AllAreas) && NavMesh.SamplePosition(target, out var b, 1.5f, NavMesh.AllAreas)
       && NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, navPath) && navPath.status != NavMeshPathStatus.PathInvalid)
    path.AddRange(navPath.corners);
   else path.Add(target);
   return path.Count > 0;
  }

  // ------------------------------------------------------------------ behaviour
  void Update() {
   if (!root || !root.gameObject.activeSelf || bridge?.State == null) return;
   bool open = bridge.State.isOpen;
   if (bubble) { bubble.position = root.position + Vector3.up * 1.25f + Vector3.up * Mathf.Sin(Time.time * 3) * .05f; if (Camera.main) bubble.rotation = Camera.main.transform.rotation; }
   switch (mode) {
    case Mode.Offer: Play("Dog_SitIdle"); Face(map.Entrance); return;
    case Mode.Walk: case Mode.Arriving: Walking(); break;
    case Mode.Chase: Chasing(); break;
    case Mode.ChaseOff: ChasingOff(); break;
    case Mode.Hero:                                                                 // proud of himself, then back inside
     if (Time.time > modeUntil) { pendingAfterWalk = "sit"; Go(RandomSpot(), true); }
     else Play("Dog_Happy");
     break;
    case Mode.Bark:
     if (Time.time > modeUntil) Next();
     else {
      var t = Thief();
      if (t) {
       Face(t.position);
       var gap = t.position - root.position; gap.y = 0;
       if (gap.magnitude > 2.2f) { mode = Mode.Chase; repathAt = 0; break; }      // he got away: after him again
      }
      if (Done()) { Play("Dog_Bark", 1, true); Woof(); }                           // bark again when a bark ends
     }
     break;
    case Mode.Happy: if (Time.time > modeUntil) Next(); else Play("Dog_Happy"); break;
    case Mode.Sleep:
     // the bed he sleeps on was moved or put away (build mode): he gets up and finds it again
     if (sleepingOn != null && (BedItem() != sleepingOn || (sleepingOn.root && (sleepingOn.root.position - sleptAt).sqrMagnitude > .04f))) { sleepingOn = null; modeUntil = 0; if (!open) { Next(); break; } }
     if (open && Time.time > modeUntil) { Play(clip != null && clip.StartsWith("Dog_Curl") ? "Dog_CurlUp" : "Dog_WakeUp"); mode = Mode.Stretch; modeUntil = Time.time + 1.4f; nextNap = Time.time + Random.Range(55f, 90f); sleepingOn = null; }
     else if (clip == "Dog_LieDown" && Done()) Play("Dog_Sleep");
     else if (clip == "Dog_CurlDown" && Done()) Play("Dog_CurlSleep");
     break;
    case Mode.HopIn: break;                                                          // (HopIn coroutine)
    case Mode.Sit:
     if (Time.time > modeUntil) { if (clip != "Dog_StandUp") { Play("Dog_StandUp"); modeUntil = Time.time + .9f; } else Next(); }
     else if (clip == "Dog_SitDown" && Done()) Play("Dog_SitIdle");
     break;
    case Mode.Stretch: if (Time.time > modeUntil) Next(); break;
    case Mode.Idle: case Mode.Sniff: if (Time.time > modeUntil) Next(); break;
    default: Next(); break;
   }
   lastPos = root.position;
   StyleBeds();
  }

  // ------------------------------------------------------------------ the beds' fabric (pet.bedStyle, bought on the Caramelo page)
  // Every bed model is baked once per fabric with the same UVs (ArtSource/decor_v4 pet-bed-*): the default atlas is the
  // Interior Kit's own (Assets/Art/Interior/Textures/IK_D4_<Bed>_albedo), the others are in Resources/CheckoutPets/
  // BedStyles/IK_D4_<Bed>_albedo_<style>. Only the texture changes.
  float bedStyleAt; readonly Dictionary<string, Texture> bedDefaults = new Dictionary<string, Texture>();
  readonly Dictionary<string, Material> bedMaterials = new Dictionary<string, Material>();
  void StyleBeds() {
   if (Time.time < bedStyleAt) return; bedStyleAt = Time.time + .5f;
   var inside = CheckoutInterior.Active; if (!inside) return;
   var style = Pet?.bedStyle ?? "";
   foreach (var it in inside.items.Values) {
    if (it?.type == null || !it.type.StartsWith("pet-bed") || !it.root) continue;
    foreach (var r in it.root.GetComponentsInChildren<Renderer>(true)) {
     var mats = r.sharedMaterials; bool changed = false;
     for (int i = 0; i < mats.Length; i++) {
      var m = mats[i]; if (!m || !m.mainTexture) continue;
      var tex = m.mainTexture.name; if (!tex.StartsWith("IK_D4_PetBed")) continue;
      int cut = tex.IndexOf("_albedo", System.StringComparison.Ordinal); if (cut < 0) continue;
      var baseName = tex.Substring(0, cut + 7);
      if (tex == baseName && !bedDefaults.ContainsKey(baseName)) bedDefaults[baseName] = m.mainTexture;
      var want = style == "" ? baseName : baseName + "_" + style;
      if (tex == want) continue;
      var key = m.shader.name + "|" + want;
      if (!bedMaterials.TryGetValue(key, out var styled) || !styled) {
       Texture t = style == "" ? (bedDefaults.TryGetValue(baseName, out var d) ? d : null) : Resources.Load<Texture2D>("CheckoutPets/BedStyles/" + want);
       if (!t) continue;
       styled = new Material(m) { name = m.name.Replace(" (Instance)", "") + " " + (style == "" ? "navy" : style), mainTexture = t };
       bedMaterials[key] = styled;
      }
      mats[i] = styled; changed = true;
     }
     if (changed) r.sharedMaterials = mats;
    }
   }
  }

  // What the dog does next: nap when it is due (always when the market is closed), otherwise wander and potter.
  void Next() {
   if (!Adopted) { mode = Mode.Offer; return; }
   // closed: off to his bed for the night (wherever it stands, inside or outside); open: a nap now and then
   if (!bridge.State.isOpen || Time.time > nextNap) { pendingAfterWalk = "sleep"; Go(BedApproach(), !bridge.State.isOpen); return; }   // (closing: a brisk trot home)
   float r = Random.value;
   pendingAfterWalk = r < .35f ? "sniff" : r < .65f ? "sit" : r < .78f ? "stretch" : "idle";
   Go(RandomSpot(), false);
  }

  void Go(Vector3 target, bool hurry) { if (!PathTo(target)) { Arrived(); return; } speed = hurry ? 1.9f : .85f; mode = Mode.Walk; }

  void Walking() { if (!Step()) Arrived(); }

  // One frame along the path; false once the path is done. The dog stays on the NavMesh (never through the glass
  // rails by the door), at the floor height the shoppers walk on.
  float stuckFor;
  bool Step() {
   if (pathIndex >= path.Count) return false;
   var target = path[pathIndex]; var d = target - root.position; d.y = 0;
   if (d.magnitude < .08f) { pathIndex++; return pathIndex < path.Count; }
   var step = d.normalized * Mathf.Min(d.magnitude, speed * Time.deltaTime);
   var before = root.position;
   root.position = Ground(root.position + step);
   root.rotation = Quaternion.RotateTowards(root.rotation, Quaternion.LookRotation(-d.normalized), 360 * Time.deltaTime);
   // no headway for a moment (a wall corner the NavMesh snap keeps him against): that corner is skipped, and at the
   // last one he is as close as he gets (Lucas 08/11: he must never stand stuck against a wall)
   var gained = root.position - before; gained.y = 0;
   stuckFor = gained.magnitude < speed * Time.deltaTime * .25f ? stuckFor + Time.deltaTime : 0;
   if (stuckFor > .7f) { stuckFor = 0; pathIndex++; if (pathIndex >= path.Count) return false; }
   // the gait follows the ground covered (no sliding): stride per cycle measured in Blender
   string gait = speed > 1.2f ? "Dog_Trot" : "Dog_Walk"; float stride = (gait == "Dog_Trot" ? .55f : .42f) * Scale;
   var moved = root.position - lastPos; moved.y = 0;
   phase = Mathf.Repeat(phase + moved.magnitude / stride, 1);
   PlayScrubbed(gait, phase);
   return true;
  }

  void Arrived() {
   path.Clear();
   switch (pendingAfterWalk) {
    case "sleep":
     if (BedItem() is CheckoutInterior.Item b) { StartCoroutine(HopIn(b)); break; }
     Face(map.Register); Play("Dog_LieDown"); mode = Mode.Sleep; modeUntil = Time.time + Random.Range(28f, 45f); break;
    case "sniff": Play("Dog_Sniff"); mode = Mode.Sniff; modeUntil = Time.time + Random.Range(2.5f, 4.5f); break;
    case "sit": FaceNearestShopper(); Play("Dog_SitDown"); mode = Mode.Sit; modeUntil = Time.time + Random.Range(5f, 9f); break;
    case "stretch": Play("Dog_Stretch"); mode = Mode.Stretch; modeUntil = Time.time + 2.1f; break;
    case "bark": StartBark(); break;
    default: Play("Dog_Idle"); mode = Mode.Idle; modeUntil = Time.time + Random.Range(2.5f, 5f); break;
   }
   pendingAfterWalk = null;
  }

  void Arrive() { mode = Mode.Arriving; pendingAfterWalk = "stretch"; PathTo(HomeSpot()); speed = 1.6f; nextNap = Time.time + 40; Hearts(3); }

  // The dog saw the theft: he trots after the thief (the path is renewed as the thief moves) and barks once he is
  // right at his heels. CheckoutSecurity waits for that moment before the thief gives up (Lucas 08/11: the thief
  // stopped long before the dog got to him).
  void StartBark() {
   if (!Thief()) return;
   mode = Mode.Chase; modeUntil = Time.time + 12f; repathAt = 0; pendingAfterWalk = null;
  }
  void Chasing() {
   var t = Thief();
   if (!t || Time.time > modeUntil) { Next(); return; }
   var d = t.position - root.position; d.y = 0;
   if (d.magnitude < 1.05f) { Face(t.position); mode = Mode.Bark; modeUntil = Time.time + 3.4f; Play("Dog_Bark", 1, true); Woof(); return; }
   if (Time.time > repathAt || pathIndex >= path.Count) {
    repathAt = Time.time + .3f;
    // a spot at his heels that is on the NavMesh (never a point behind a rail or a counter)
    var goal = t.position - d.normalized * .85f;
    if (NavMesh.SamplePosition(goal, out var gh, .45f, NavMesh.AllAreas)) goal = gh.position;
    else if (NavMesh.SamplePosition(t.position, out var th, 1.2f, NavMesh.AllAreas)) goal = th.position;
    PathTo(goal); pathIndex = path.Count > 1 ? 1 : 0;
   }
   speed = 3.3f;
   // as close as the floor lets him get: bark from there
   if (!Step() && d.magnitude < 1.9f) { Face(t.position); mode = Mode.Bark; modeUntil = Time.time + 3.4f; Play("Dog_Bark", 1, true); Woof(); }
  }
  /// <summary>The thief gave the goods back and runs off scared (CheckoutSecurity): the dog chases him out of the shop,
  /// barking, and comes back happy for having saved the market (Lucas 08/11).</summary>
  public void ChaseOff(Transform thief) {
   if (!root || !thief) return;
   chased = thief; mode = Mode.ChaseOff; modeUntil = Time.time + 6f; repathAt = 0; nextWoof = Time.time + .25f; pendingAfterWalk = null;
  }
  void ChasingOff() {
   bool gone = !chased || !chased.gameObject.activeInHierarchy;
   if (gone || Time.time > modeUntil) {
    // the market is safe: a happy dance with hearts where he stopped, then he trots back in
    mode = Mode.Hero; modeUntil = Time.time + 2.4f; path.Clear(); Play("Dog_Happy", 1, true); Hearts(5);
    if (Camera.main) Face(Camera.main.transform.position);
    return;
   }
   var d = chased.position - root.position; d.y = 0;
   if (Time.time > repathAt || pathIndex >= path.Count) {
    repathAt = Time.time + .3f;
    var goal = chased.position - d.normalized * 1.1f;
    if (NavMesh.SamplePosition(goal, out var gh, .6f, NavMesh.AllAreas)) goal = gh.position;
    PathTo(goal); pathIndex = path.Count > 1 ? 1 : 0;
   }
   speed = d.magnitude > 1.6f ? 3.6f : 2.6f;                                       // right at his heels, never past him
   if (!Step()) { Face(chased.position); PlayScrubbed("Dog_Trot", phase = Mathf.Repeat(phase + Time.deltaTime * 2.5f, 1)); }
   if (Time.time > nextWoof) { nextWoof = Time.time + Random.Range(.45f, .7f); Woof(); }
  }

  // ------------------------------------------------------------------ the bark: a pop-up "AU!" and a short woof
  void Woof() {
   if (!root) return;
   StartCoroutine(WoofText());
   var clip = Bark; if (clip) CheckoutDeliverySound.Play(clip, .6f);              // (the effects volume is the listener's)
  }
  IEnumerator WoofText() {
   var go = new GameObject("Woof"); go.transform.SetParent(holder, false);
   var tmp = go.AddComponent<TextMeshPro>(); tmp.font = CheckoutDesktopKit.Label; tmp.fontSize = 5.5f; tmp.alignment = TextAlignmentOptions.Center;
   tmp.textWrappingMode = TextWrappingModes.NoWrap; tmp.text = Random.value < .5f ? "AU!" : "AU AU!";
   tmp.color = new Color32(0xFF, 0xF4, 0xDC, 0xFF); tmp.outlineColor = new Color32(0x8A, 0x4B, 0x12, 0xFF); tmp.outlineWidth = .28f;
   float side = Random.Range(-.25f, .25f), tilt = Random.Range(-14f, 14f), t = 0;
   while (t < .9f && go && root) {
    t += Time.deltaTime; float k = t / .9f;
    go.transform.position = root.position + Vector3.up * (1.0f + k * .55f) + (Camera.main ? Camera.main.transform.right * side : Vector3.zero);
    if (Camera.main) go.transform.rotation = Camera.main.transform.rotation * Quaternion.Euler(0, 0, tilt);
    float pop = k < .18f ? Mathf.Lerp(.2f, 1.25f, k / .18f) : Mathf.Lerp(1.25f, 1f, Mathf.Min(1, (k - .18f) / .2f));
    go.transform.localScale = Vector3.one * pop;
    tmp.alpha = k > .65f ? 1 - (k - .65f) / .35f : 1;
    yield return null;
   }
   if (go) Destroy(go);
  }
  // A real recorded bark (Lucas 08/11: the synthesized one sounded awful): Resources/CheckoutPets/Dog_Bark*.wav, one
  // single bark per file, picked at random. No file, no sound (the "AU!" still shows).
  static AudioClip[] barks;
  static AudioClip Bark {
   get {
    if (barks == null) barks = Resources.LoadAll<AudioClip>("CheckoutPets").Where(c => c.name.StartsWith("Dog_Bark")).ToArray();
    return barks.Length > 0 ? barks[Random.Range(0, barks.Length)] : null;
   }
  }

  /// <summary>The dog is running after the thief and not at his heels yet.</summary>
  public bool ChasingThief => root && root.gameObject.activeInHierarchy && mode == Mode.Chase;
  /// <summary>The dog is barking at the thief right next to him.</summary>
  public bool BarkingAtThief => root && root.gameObject.activeInHierarchy && mode == Mode.Bark;
  Transform Thief() => CheckoutSecurity.Instance ? CheckoutSecurity.Instance.ThiefTransform : null;

  void FaceNearestShopper() {
   Transform best = null; float bd = 4;
   foreach (var w in FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None)) { if (!w.gameObject.activeSelf) continue; var dd = Vector3.Distance(w.transform.position, root.position); if (dd < bd) { bd = dd; best = w.transform; } }
   if (best) Face(best.position);
  }
  void Face(Vector3 p) { var d = p - root.position; d.y = 0; if (d.sqrMagnitude > .01f) root.rotation = Quaternion.RotateTowards(root.rotation, Quaternion.LookRotation(-d.normalized), 240 * Time.deltaTime); }

  // ------------------------------------------------------------------ taps
  /// <summary>A tap on the dog (CheckoutBridge.WorldTap, panel "pet").</summary>
  public static void Tapped() { if (Instance) Instance.OnTap(); }
  void OnTap() {
   var pet = Pet; if (pet == null) return;
   if (!pet.adopted) { if (pet.offer) bridge.Command("adoptPet", "[]"); Hearts(4); return; }
   bool reward = pet.cooldownLeftMs <= 0;
   if (reward) bridge.Command("petDog", "[]");
   if (mode == Mode.Sleep) { Play("Dog_WakeUp"); }
   var cam = Camera.main; if (cam) Face(cam.transform.position);
   mode = Mode.Happy; modeUntil = Time.time + (reward ? 3.2f : 1.8f); Play("Dog_Happy"); Hearts(reward ? 5 : 2);
  }

  // ------------------------------------------------------------------ fx
  // A happy dog shows happy faces (Lucas 08/11: hearts read as "in love"): Game/emote_happy, the emotes' glossy style
  // (ArtSource/pets/emote_happy.py). One or two pop up, not a stream.
  void Hearts(int n) { n = Mathf.Clamp((n + 1) / 2, 1, 2); for (int i = 0; i < n; i++) StartCoroutine(Heart(i * .35f)); }
  IEnumerator Heart(float delay) {
   yield return new WaitForSeconds(delay);
   if (!root) yield break;
   var go = new GameObject("Happy"); go.transform.SetParent(holder, false);
   var sr = go.AddComponent<SpriteRenderer>(); sr.sprite = CheckoutDesktopKit.Icon("Game/emote_happy") ?? CheckoutDesktopKit.Icon("Icons/like"); sr.sortingOrder = 50;
   float size = sr.sprite ? Mathf.Max(sr.sprite.bounds.size.x, sr.sprite.bounds.size.y) : 1;
   var start = root.position + Vector3.up * .95f + new Vector3(Random.Range(-.25f, .25f), 0, Random.Range(-.25f, .25f));
   float t = 0, dur = 1.3f, wob = Random.Range(0f, 6f);
   while (t < dur && go) {
    t += Time.deltaTime; float k = t / dur;
    go.transform.position = start + Vector3.up * (k * .9f) + Vector3.right * Mathf.Sin(wob + k * 7) * .08f;
    if (Camera.main) go.transform.rotation = Camera.main.transform.rotation;
    go.transform.localScale = Vector3.one * (.62f / size) * (k < .15f ? k / .15f * 1.15f : k < .3f ? Mathf.Lerp(1.15f, 1f, (k - .15f) / .15f) : 1);
    sr.color = new Color(1, 1, 1, k > .7f ? 1 - (k - .7f) / .3f : 1);
    yield return null;
   }
   if (go) Destroy(go);
  }

  void ShowBubble() {
   if (bubble) return;
   bubble = new GameObject("Adopt balloon").transform; bubble.SetParent(holder, false);
   var bg = new GameObject("Back"); bg.transform.SetParent(bubble, false);
   var srb = bg.AddComponent<SpriteRenderer>(); srb.sprite = CheckoutRankArt.Shape("spot"); srb.color = new Color32(0xFF, 0xF1, 0xCF, 0xFF); srb.sortingOrder = 49;
   if (srb.sprite) bg.transform.localScale = Vector3.one * (.62f / Mathf.Max(srb.sprite.bounds.size.x, srb.sprite.bounds.size.y));
   var ic = new GameObject("Heart"); ic.transform.SetParent(bubble, false); ic.transform.localPosition = new Vector3(0, 0, -.02f);
   var sr = ic.AddComponent<SpriteRenderer>(); sr.sprite = CheckoutDesktopKit.Icon("Icons/like"); sr.sortingOrder = 50;
   if (sr.sprite) ic.transform.localScale = Vector3.one * (.38f / Mathf.Max(sr.sprite.bounds.size.x, sr.sprite.bounds.size.y));
   var hit = bubble.gameObject.AddComponent<BoxCollider>(); hit.size = new Vector3(.8f, .8f, .3f);
   bubble.gameObject.AddComponent<CheckoutTarget>().panel = "pet";
  }
  void HideBubble() { if (bubble) Destroy(bubble.gameObject); bubble = null; }

  // ------------------------------------------------------------------ clips
  void Play(string name, float speed = 1, bool restart = false) {
   if (!anim || clip == name && !restart) return;
   var st = anim[name]; if (!st) return;
   st.speed = speed; if (restart) st.time = 0;
   anim.CrossFade(name, .22f); clip = name;
  }
  void PlayScrubbed(string name, float t) {
   if (!anim) return; var st = anim[name]; if (!st) return;
   if (clip != name) { anim.CrossFade(name, .2f); clip = name; }
   st.speed = 0; st.normalizedTime = t;
  }
  bool Done() { if (!anim || string.IsNullOrEmpty(clip)) return true; var st = anim[clip]; return !st || st.time >= st.length - .02f; }

  /// <summary>QA (CheckoutAutoTest): put the dog in a pose right now.</summary>
  public void QaAct(string what) {
   if (!root) return;
   switch (what) {
    case "pet": OnTap(); break;
    case "sleep": pendingAfterWalk = "sleep"; Place(BedApproach()); Arrived(); break;
    case "walk": Next(); break;
    case "bark": StartBark(); break;
   }
  }
  public Transform Root => root;
 }
}
