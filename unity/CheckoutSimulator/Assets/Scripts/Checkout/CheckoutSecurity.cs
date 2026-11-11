using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 /// <summary>
 /// Shoplifter and security guard (src/services/store-security.ts → Snapshot.security, employees with role "security").
 /// The thief walks in sneaking, waits by the shelf looking around, stashes the goods in his bag (the rules take them at
 /// grabAt) and runs for the door (he escapes at fleeDeadline). While he runs a magnifier marker floats over him and a
 /// tap catches him ("catchThief"): hands up, he gives the goods back and leaves ashamed. A hired guard waits by the
 /// door, patrols now and then and, when the rules say so (guardCatchAt), sprints to the thief and stops him.
 /// Art: Resources/CheckoutSecurity/Thief and Guard (the customers' skeleton; clips Thief_* / Guard_*).
 /// </summary>
 public class CheckoutSecurity : MonoBehaviour {
  public static CheckoutSecurity Instance { get; private set; }
  CheckoutBridge bridge; CheckoutMap map; Transform holder; readonly CheckoutEventAssets art = new CheckoutEventAssets();
  const float CharScale = .72f;

  sealed class Actor {
   public Transform root, model; public Animation anim; public string clip; public float phase; public Vector3 last; public GameObject cuffs;
   public float size = 1, stuck;    // size: model scale over CharScale (the thief is matched to the shoppers' height)
   public readonly List<Vector3> path = new List<Vector3>(); public int index; public float speed;
  }
  Actor thief, guard; string thiefId = ""; string thiefPhase = ""; Transform marker; Transform loot, bag;
  // The thief robs the till (src/data/security.ts THIEF_TILL_ID; Lucas 08/11: "lá que fica o dinheiro").
  const string TillId = "checkout:main";
  Coroutine scene; bool guardBusy; float guardNextPatrol, guardRepath; bool guardPatrolling;
  NavMeshPath navPath;

  public Transform ThiefTransform => thief != null && thief.root && thief.root.gameObject.activeSelf ? thief.root : null;

  public void Initialize(CheckoutBridge b, CheckoutMap m) {
   bridge = b; map = m; Instance = this;
   holder = new GameObject("Security").transform; holder.SetParent(transform, false);
   CheckoutBridge.Received += Apply;
  }
  void OnDestroy() { CheckoutBridge.Received -= Apply; if (holder) Destroy(holder.gameObject); }

  // ------------------------------------------------------------------ snapshot
  void Apply(Snapshot s) {
   if (CheckoutSocial.Visiting) { Clear(); return; }
   // the guard
   bool hired = s.employees != null && s.employees.Any(e => e.role == "security" && e.isWorking);
   if (hired && s.isOpen) { if (guard == null) guard = Spawn("Guard", GuardPost()); if (guard != null && !guard.root.gameObject.activeSelf) { guard.root.gameObject.SetActive(true); Place(guard, GuardPost()); } }
   else if (guard != null && guard.root.gameObject.activeSelf && !guardBusy) guard.root.gameObject.SetActive(false);
   // the thief
   var t = s.security?.thief;
   bool has = t != null && !string.IsNullOrEmpty(t.id);
   if (!has) { if (thief != null && thief.root.gameObject.activeSelf && scene == null) thief.root.gameObject.SetActive(false); thiefId = ""; thiefPhase = ""; HideMarker(); return; }
   if (t.id != thiefId) { thiefId = t.id; thiefPhase = ""; if (scene != null) StopCoroutine(scene); scene = StartCoroutine(Story(t.id)); }
  }
  void Clear() { if (thief != null) thief.root.gameObject.SetActive(false); if (guard != null) guard.root.gameObject.SetActive(false); HideMarker(); thiefId = ""; }

  ThiefState Current(string id) { var t = bridge?.State?.security?.thief; return t != null && t.id == id ? t : null; }
  static float Until(double at) => (float)((at - CheckoutBridge.Now) / 1000.0);

  // ------------------------------------------------------------------ the thief's story
  IEnumerator Story(string id) {
   var t = Current(id); if (t == null) { scene = null; yield break; }
   if (thief == null) thief = Spawn("Thief", Outside());
   if (thief == null) { scene = null; yield break; }
   thief.root.gameObject.SetActive(true);
   MatchShoppers(thief);
   bool till = t.shelfId == TillId;
   Vector3 shelfSpot, shelfFace;
   if (till) shelfSpot = TillSpot(out shelfFace);
   else {
    shelfSpot = Ground(string.IsNullOrEmpty(t.shelfId) ? RandomShelfSpot() : map.Approach(t.shelfId));
    shelfFace = string.IsNullOrEmpty(t.shelfId) ? shelfSpot : map.Fixture(t.shelfId);
   }
   string walkedTo = t.shelfId ?? "";
   if (t.phase == "entering") {
    // in from the sidewalk, sneaking; he reaches the shelf about two seconds before he grabs
    Place(thief, Outside());
    PathTo(thief, shelfSpot);
    float time = Mathf.Max(2f, Until(t.grabAt) - 2.2f);
    thief.speed = Mathf.Clamp(Length(thief) / time, .5f, 1.6f);
    while (!Arrived(thief)) { if (Current(id)?.phase != "entering") break; Walk(thief, "Thief_Sneak", 1.34f); yield return null; }
    while (Current(id)?.phase == "entering") { Face(thief, shelfFace); Play(thief, "Thief_LookAround"); yield return null; }
   } else Place(thief, shelfSpot);
   t = Current(id); if (t == null) { thief.root.gameObject.SetActive(false); scene = null; yield break; }
   if (t.phase == "fleeing") {
    // What he took is decided when he grabs (src/services/store-security.ts grab): when the product he came for sold
    // out meanwhile, it is the best one left, maybe on another shelf. He goes there first, so what shows in his hand
    // is always from the shelf he takes it from (Lucas 08/11: a tomato out of the drinks cooler).
    if (!till && !string.IsNullOrEmpty(t.shelfId) && t.shelfId != walkedTo) {
     var spot = Ground(map.Approach(t.shelfId)); shelfFace = map.Fixture(t.shelfId);
     PathTo(thief, spot); thief.speed = 1.9f; float w0 = Time.time;
     while (!Arrived(thief) && Time.time - w0 < 4f && Current(id)?.phase == "fleeing") { Walk(thief, "Thief_Sneak", 1.34f); yield return null; }
    }
    // he stashes the goods (the product shows in his hand), then runs for the door
    Face(thief, shelfFace, true);
    Play(thief, "Thief_Stash", true);
    if (till) { ShowBag(); if (t.value >= 1) StartCoroutine(Coins(shelfFace + Vector3.up * 1.2f, -(int)System.Math.Round(t.value))); }  // the cash out of the till
    else ShowLoot(t.productId);
    float stash = 1.5f, s0 = Time.time;
    while (Time.time - s0 < stash && Current(id)?.phase == "fleeing") { yield return null; }
    HideLoot();                                                    // (the money bag stays in his hand while he runs)
    ShowMarker(id);
    PathTo(thief, map.Entrance); var outPath = Outside(); thief.path.Add(outPath);
    while (Current(id)?.phase == "fleeing") {
     var left = Mathf.Max(.6f, Until(Current(id).fleeDeadline));
     thief.speed = Mathf.Clamp(Length(thief) / left, 1.2f, 4.5f);
     if (!Arrived(thief)) Walk(thief, "Thief_Run", .95f); else Play(thief, "Thief_LookAround");
     yield return null;
    }
   }
   HideMarker();
   t = Current(id);
   string end = t?.phase ?? "gone";
   if (end == "caught") yield return Caught(id, t.caughtBy == "guard", t.productId, t.coins);
   else if (end == "escaped") {
    // gone with the goods: out of the door and away down the sidewalk
    var away = Outside() + Away() * 6f; PathTo(thief, away); thief.speed = 4f;
    float t0 = Time.time; while (!Arrived(thief) && Time.time - t0 < 4) { Walk(thief, "Thief_Run", .95f); yield return null; }
   }
   thief.root.gameObject.SetActive(false); HideBag();
   scene = null;
  }

  IEnumerator Caught(string id, bool byGuard, int productId, int coins) {
   bool withGuard = byGuard && guard != null && guard.root.gameObject.activeSelf;
   if (withGuard) {
    guardBusy = true;
    // the guard sprints to him; the thief freezes when the guard arrives
    PathTo(guard, thief.root.position + (guard.root.position - thief.root.position).normalized * .75f); guard.speed = 3.6f;
    float t0 = Time.time;
    while (!Arrived(guard) && Time.time - t0 < 3f) { Walk(guard, "Guard_Run", .95f); Play(thief, "Thief_Run"); yield return null; }
    // face to face
    Face(guard, thief.root.position, true); Face(thief, guard.root.position, true);
    Play(guard, "Guard_Stop", true);
   } else {
    // the store dog is after him: he keeps running (out of breath) until the dog is at his heels, and only then the
    // fright (Lucas 08/11: he stopped long before the dog got to him)
    var dog = CheckoutPets.Instance;
    if (dog && dog.ChasingThief) {
     if (Arrived(thief)) { PathTo(thief, Outside()); thief.path.Add(Outside() + Away() * 4f); }
     thief.speed = 1.5f; float d0 = Time.time;
     while (dog && dog.ChasingThief && Time.time - d0 < 5f) { if (!Arrived(thief)) Walk(thief, "Thief_Run", .62f); else Play(thief, "Thief_LookAround"); yield return null; }
    }
    if (dog && dog.Root && dog.Root.gameObject.activeInHierarchy && Flat(dog.Root.position - thief.root.position) < 3f) Face(thief, dog.Root.position, true);
    else if (Camera.main) Face(thief, Camera.main.transform.position, true);
   }
   Play(thief, "Thief_Caught", true); yield return new WaitForSeconds(.8f);
   Play(thief, "Thief_HandsUp", true); if (withGuard) Play(guard, "Guard_Catch", true); yield return new WaitForSeconds(1.1f);
   bool cash = bag && bag.gameObject.activeSelf;
   Play(thief, "Thief_GiveBack", true); if (!cash) ShowLoot(productId); yield return new WaitForSeconds(1.0f);
   HideLoot(); HideBag(); if (coins > 0) StartCoroutine(Coins(thief.root.position + Vector3.up * 1.9f, coins));
   if (!withGuard) {
    var pet = CheckoutPets.Instance;
    if (pet && pet.Root && pet.Root.gameObject.activeInHierarchy && Flat(pet.Root.position - thief.root.position) < 3.5f) {
     // the dog caught him: scared of the dog, he runs off and the dog chases him out barking (Lucas 08/11); the dog
     // comes back happy once he is gone (CheckoutPets.ChaseOff)
     yield return new WaitForSeconds(.3f);
     var exit = Outside(); Face(thief, exit, true);
     PathTo(thief, exit); thief.path.Add(Outside() + Away() * 7f); thief.speed = 3.3f;
     pet.ChaseOff(thief.root);
     float r0 = Time.time;
     while (!Arrived(thief) && Time.time - r0 < 6f) { Walk(thief, "Thief_Run", .95f); yield return null; }
     yield break;
    }
    yield return new WaitForSeconds(.6f);
    // caught by the player (no guard on duty): he gives the goods back and leaves, head down
    PathTo(thief, Outside()); thief.path.Add(Outside() + Away() * 5f); thief.speed = .85f;
    float w0 = Time.time;
    while (!Arrived(thief) && Time.time - w0 < 9) { Walk(thief, "Thief_WalkAshamed", 1.06f); yield return null; }
    yield break;
   }
   // the guard cuffs him: he turns to the door with the hands behind his back, the guard steps behind him
   var door = Outside(); Face(thief, door, true);
   if (thief.cuffs) thief.cuffs.SetActive(true);
   Play(thief, "Thief_Cuffed", true);
   var behind = OnFloor(thief.root.position + thief.root.forward * .55f);
   PathTo(guard, behind); guard.speed = 1.4f;
   float c0 = Time.time;
   while (!Arrived(guard) && Time.time - c0 < 2f) { Walk(guard, "Guard_Walking", .5f); yield return null; }
   guard.root.rotation = thief.root.rotation; Play(guard, "Guard_Escort", true); Freeze(guard, "Guard_Escort");
   yield return new WaitForSeconds(.5f);
   // ...and walks him out of the market, a hand on his shoulder
   PathTo(thief, Outside()); thief.path.Add(Outside() + Away() * 4.5f); thief.speed = .9f;
   float e0 = Time.time;
   while (!Arrived(thief) && Time.time - e0 < 12) {
    Walk(thief, "Thief_CuffedWalk", 1.06f);
    var want = thief.root.position + thief.root.forward * .55f;
    var step = want - guard.root.position; step.y = 0;
    guard.root.position = OnFloor(guard.root.position + Vector3.ClampMagnitude(step, thief.speed * 1.6f * Time.deltaTime + .002f));
    guard.root.rotation = Quaternion.RotateTowards(guard.root.rotation, thief.root.rotation, 300 * Time.deltaTime);
    Scrub(guard, "Guard_Escort", .46f);
    yield return null;
   }
   // outside: the thief is taken away, the guard comes back, thumbs up
   thief.root.gameObject.SetActive(false); if (thief.cuffs) thief.cuffs.SetActive(false);
   Face(guard, map.Entrance, true); Play(guard, "Guard_ThumbsUp", true); yield return new WaitForSeconds(1.1f);
   guardBusy = false; BackToPost();
  }

  // the clip follows the ground the actor covered (for actors moved by hand, not by Walk)
  void Scrub(Actor a, string clip, float stride) {
   var moved = a.root.position - a.last; moved.y = 0;
   a.phase = Mathf.Repeat(a.phase + moved.magnitude / Mathf.Max(.1f, stride * CharScale * a.size * 1.4f), 1);
   a.last = a.root.position;
   if (!a.anim) return; var st = a.anim[clip]; if (!st) return;
   if (a.clip != clip) { a.anim.CrossFade(clip, .2f); a.clip = clip; }
   st.speed = 0; st.normalizedTime = a.phase;
  }
  void Freeze(Actor a, string clip) { if (a?.anim == null) return; var st = a.anim[clip]; if (st) { st.speed = 0; st.normalizedTime = a.phase; } }

  // ------------------------------------------------------------------ the guard
  void Update() {
   if (thief != null && thief.root && thief.root.gameObject.activeSelf) thief.last = thief.root.position;
   if (marker && thief != null && thief.root) { marker.position = thief.root.position + Vector3.up * (2.15f + Mathf.Sin(Time.time * 4) * .06f); if (Camera.main) marker.rotation = Quaternion.LookRotation(marker.position - Camera.main.transform.position); }
   if (bag && bag.gameObject.activeSelf && thief != null && thief.root) { var hand = Bone(thief, "Hand_R"); if (hand) { bag.position = hand.position + Vector3.down * .16f; bag.rotation = Quaternion.LookRotation(-thief.root.forward); } }
   if (loot && thief != null && thief.root) { var hand = Bone(thief, "Hand_R"); if (hand) loot.position = hand.position + Vector3.down * .05f; if (Camera.main) loot.rotation = Camera.main.transform.rotation; }
   if (guard == null || !guard.root.gameObject.activeSelf || guardBusy) return;
   // the rules scheduled a guard catch: start the sprint so he gets there in time
   var t = bridge?.State?.security?.thief;
   if (t != null && t.phase == "fleeing" && t.guardCatchAt > 0 && thief != null) {
    // the way to him is worked out again only now and then (every frame, near the door, the NavMesh answered with
    // the way round one side and then the other: he ran on the spot against the glass)
    var target = thief.root.position;
    if (Time.time > guardRepath || Arrived(guard)) { guardRepath = Time.time + .5f; PathTo(guard, target); }
    guard.speed = Mathf.Clamp(Length(guard) / Mathf.Max(.4f, Until(t.guardCatchAt)), 2f, 4.5f);
    Walk(guard, "Guard_Run", .95f); guard.last = guard.root.position; return;
   }
   if (guardPatrolling) {
    if (Arrived(guard)) { guardPatrolling = false; BackToPost(); }
    else Walk(guard, "Guard_Walking", .5f);
   } else if (guard.path.Count > 0 && !Arrived(guard)) Walk(guard, "Guard_Walking", .5f);
   else {
    Face(guard, map.Entrance + (map.Entrance - map.Register) * 2f); Play(guard, Time.time % 30 < 4 ? "Guard_Radio" : "Guard_Idle");
    if (Time.time > guardNextPatrol) { guardNextPatrol = Time.time + Random.Range(18f, 30f); PathTo(guard, RandomShelfSpot()); guard.speed = .9f; guardPatrolling = true; }
   }
   guard.last = guard.root.position;
  }
  void BackToPost() { if (guard == null) return; PathTo(guard, GuardPost()); guard.speed = 1f; guardPatrolling = false; }

  // ------------------------------------------------------------------ actors
  Actor Spawn(string who, Vector3 at) {
   var prefab = Resources.Load<GameObject>("CheckoutSecurity/" + who);
   if (!prefab) { Debug.LogWarning("CHECKOUT_SECURITY_MISSING Resources/CheckoutSecurity/" + who); return null; }
   var a = new Actor();
   a.root = new GameObject(who).transform; a.root.SetParent(holder, false);
   a.model = Instantiate(prefab, a.root, false).transform; a.model.name = who + " model"; a.model.localScale = Vector3.one * CharScale;
   foreach (var r in a.model.GetComponentsInChildren<Renderer>(true)) {
    if (r is SkinnedMeshRenderer sk) sk.updateWhenOffscreen = true;
    var mats = r.sharedMaterials;
    for (int i = 0; i < mats.Length; i++) {
     var src = mats[i]; var texName = src ? src.name.Replace(" (Instance)", "") : "";
     var tex = Resources.Load<Texture2D>("CheckoutSecurity/Textures/" + texName.Replace("_Mat", ""));
     var m = new Material(Shader.Find("Standard")) { name = texName };
     if (tex) m.mainTexture = tex; else if (src) m.color = src.color;
     m.SetFloat("_Glossiness", texName.Contains("Lens") ? .8f : .12f); m.SetFloat("_Metallic", texName.Contains("Gold") || texName.Contains("Metal") ? .6f : 0);
     mats[i] = m;
    }
    r.sharedMaterials = mats;
   }
   // both FBX face +Z (the market's walkers face -Z): turned so they look where they walk
   a.model.localRotation = Quaternion.Euler(0, 180, 0);
   foreach (var r in a.model.GetComponentsInChildren<Renderer>(true)) if (r.name.Contains("Cuffs")) { a.cuffs = r.gameObject; a.cuffs.SetActive(false); }
   a.anim = a.model.GetComponentInChildren<Animation>(true);
   if (a.anim) { a.anim.playAutomatically = false; a.anim.cullingType = AnimationCullingType.AlwaysAnimate; foreach (AnimationState st in a.anim) st.wrapMode = Loop(st.name) ? WrapMode.Loop : WrapMode.ClampForever; }
   if (who == "Thief") {
    var box = a.root.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, 1.0f, 0); box.size = new Vector3(.9f, 2.0f, .9f);
    var target = a.root.gameObject.AddComponent<CheckoutTarget>(); target.panel = "thief";
   } else {
    var box = a.root.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, 1.0f, 0); box.size = new Vector3(.8f, 2.0f, .8f);
    a.root.gameObject.AddComponent<CheckoutTarget>().panel = "team";
   }
   Place(a, at);
   return a;
  }
  static bool Loop(string n) => n.EndsWith("Cuffed") || n.EndsWith("CuffedWalk") || n.EndsWith("Escort") || n.EndsWith("Sneak") || n.EndsWith("LookAround") || n.EndsWith("Run") || n.EndsWith("HandsUp") || n.EndsWith("WalkAshamed") || n.EndsWith("Idle") || n.EndsWith("Radio") || n.EndsWith("Walking") || n.EndsWith("Idle0");

  void Place(Actor a, Vector3 p) { a.root.position = Ground(p); a.last = a.root.position; a.path.Clear(); a.index = 0; }
  bool PathTo(Actor a, Vector3 target) {
   a.path.Clear(); a.index = 0; if (navPath == null) navPath = new NavMeshPath();
   // the start on the NavMesh right under him when there is one (a wide search from the doorway could start the
   // way on the other side of the shop window)
   if ((NavMesh.SamplePosition(a.root.position, out var h0, .5f, NavMesh.AllAreas) || NavMesh.SamplePosition(a.root.position, out h0, 2f, NavMesh.AllAreas))
       && NavMesh.SamplePosition(target, out var h1, 2f, NavMesh.AllAreas)
       && NavMesh.CalculatePath(h0.position, h1.position, NavMesh.AllAreas, navPath) && navPath.status != NavMeshPathStatus.PathInvalid)
    a.path.AddRange(navPath.corners.Skip(1));
   if (a.path.Count == 0 || (a.path[a.path.Count - 1] - target).sqrMagnitude > .25f) a.path.Add(target);
   return true;
  }
  static float Length(Actor a) { float d = 0; var p = a.root.position; for (int i = a.index; i < a.path.Count; i++) { d += Vector3.Distance(p, a.path[i]); p = a.path[i]; } return d; }
  static bool Arrived(Actor a) => a.index >= a.path.Count;
  void Walk(Actor a, string clip, float stride) {
   if (Arrived(a)) return;
   var target = a.path[a.index]; var d = target - a.root.position; d.y = 0;
   if (d.magnitude < .1f) { a.index++; a.stuck = 0; return; }
   // the NavMesh gave the path; the step only takes the floor height (snapping x/z back onto the NavMesh every
   // frame pinned the guard at the door: the corner past the door frame was never reached)
   var before = a.root.position;
   a.root.position = OnFloor(a.root.position + d.normalized * Mathf.Min(d.magnitude, a.speed * Time.deltaTime));
   a.root.rotation = Quaternion.RotateTowards(a.root.rotation, Quaternion.LookRotation(-d.normalized), 540 * Time.deltaTime);
   // no headway for half a second (something in the way): that corner is skipped
   a.stuck = Flat(a.root.position - before) < a.speed * Time.deltaTime * .3f ? a.stuck + Time.deltaTime : 0;
   if (a.stuck > .5f) { a.index++; a.stuck = 0; }
   // the cycle follows the ground covered: stride = metres per cycle of the clip at the game's scale
   var moved = a.root.position - a.last; moved.y = 0;
   a.phase = Mathf.Repeat(a.phase + moved.magnitude / Mathf.Max(.1f, stride * CharScale * a.size * 1.4f), 1);
   if (!a.anim) return; var st = a.anim[clip] ?? a.anim["Walking"]; if (!st) return;
   if (a.clip != st.name) { a.anim.CrossFade(st.name, .2f); a.clip = st.name; }
   st.speed = 0; st.normalizedTime = a.phase;
   a.last = a.root.position;
  }
  void Play(Actor a, string clip, bool restart = false) {
   if (a == null || !a.anim) return; var st = a.anim[clip]; if (!st) return;
   if (a.clip == clip && !restart && st.speed > 0) return;
   st.speed = 1; if (restart) st.time = 0;
   a.anim.CrossFade(clip, .18f); a.clip = clip;
  }
  void Face(Actor a, Vector3 p, bool snap = false) { var d = p - a.root.position; d.y = 0; if (d.sqrMagnitude < .01f) return; var want = Quaternion.LookRotation(-d.normalized); a.root.rotation = snap ? want : Quaternion.RotateTowards(a.root.rotation, want, 360 * Time.deltaTime); }
  static Transform Bone(Actor a, string name) { foreach (var t in a.model.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t; return null; }

  /// <summary>QA: how high the feet are above the ground the actor stands on (lowest point of the skinned meshes).</summary>
  public string Heights() {
   string One(string n, Actor a) {
    if (a == null || !a.root || !a.root.gameObject.activeInHierarchy) return n + "=off";
    float min = float.MaxValue; var tmp = new Mesh();
    foreach (var sk in a.model.GetComponentsInChildren<SkinnedMeshRenderer>(true)) { if (!sk.gameObject.activeInHierarchy) continue; sk.BakeMesh(tmp, true); foreach (var v in tmp.vertices) { var w = sk.transform.position + sk.transform.rotation * v; if (w.y < min) min = w.y; } }
    Destroy(tmp);
    var nav = NavMesh.SamplePosition(a.root.position, out var h, 2f, NavMesh.AllAreas) ? h.position.y : float.NaN;
    return $"{n}: root {a.root.position.y:0.000} feet {min:0.000} nav {nav:0.000} walkerY {WalkerY(a.root.position):0.000}";
   }
   return One("thief", thief) + " | " + One("guard", guard);
  }

  // ------------------------------------------------------------------ places
  Vector3 Ground(Vector3 p) { var q = NavMesh.SamplePosition(p, out var hit, 2.5f, NavMesh.AllAreas) ? hit.position : p; q.y = WalkerY(q); return q; }
  Vector3 OnFloor(Vector3 p) { p.y = WalkerY(p); return p; }
  static float Flat(Vector3 v) { v.y = 0; return v.magnitude; }

  // The thief's sculpt came out a head shorter and much slimmer than the shoppers (Lucas 08/11: "muito magrinho,
  // pequeno"): 12% taller and a sturdier build (checked side by side with the shoppers in sec_2/sec_3).
  const float ThiefTall = 1.12f, ThiefWide = 1.16f;
  void MatchShoppers(Actor a) {
   a.size = ThiefTall;
   a.model.localScale = new Vector3(CharScale * ThiefTall * ThiefWide, CharScale * ThiefTall, CharScale * ThiefTall * ThiefWide);
  }
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

  Vector3 Away() { var d = map.Entrance - map.Register; d.y = 0; return d.sqrMagnitude > .01f ? d.normalized : Vector3.back; }
  Vector3 Outside() => Ground(map.Entrance + Away() * 2.2f);
  Vector3 GuardPost() { var side = Vector3.Cross(Vector3.up, Away()); return Ground(map.Entrance - Away() * 1.3f + side * 1.1f); }
  Vector3 RandomShelfSpot() {
   var shelves = bridge.State?.shelves?.Where(s => s.unlocked).ToList();
   if (shelves == null || shelves.Count == 0) return Ground(map.Register);
   return Ground(map.Approach(shelves[Random.Range(0, shelves.Count)].id));
  }

  // ------------------------------------------------------------------ marker, loot, coins
  void ShowMarker(string id) {
   if (!marker) {
    marker = art.Prop2(holder, "Inspect_Marker", Vector3.zero, 0, 1.4f);
    var hit = new GameObject("Click"); hit.transform.SetParent(marker, false);
    var box = hit.AddComponent<BoxCollider>(); box.size = new Vector3(1.1f, 1.1f, .6f);
    hit.AddComponent<CheckoutTarget>().panel = "thief";
   }
   marker.gameObject.SetActive(true);
   foreach (var tg in marker.GetComponentsInChildren<CheckoutTarget>(true)) tg.requestId = id;
   if (thief != null) thief.root.GetComponent<CheckoutTarget>().requestId = id;
   StartCoroutine(Pulse(marker));
  }
  void HideMarker() { if (marker) marker.gameObject.SetActive(false); }
  IEnumerator Pulse(Transform t) { float k = 0; var s = t.localScale; while (k < 1 && t) { k += Time.deltaTime * 4; t.localScale = s * (k < .6f ? Mathf.Lerp(0, 1.15f, k / .6f) : Mathf.Lerp(1.15f, 1, (k - .6f) / .4f)); yield return null; } if (t) t.localScale = s; }

  void ShowLoot(int productId) {
   if (!loot) { var go = new GameObject("Loot"); go.transform.SetParent(holder, false); var sr = go.AddComponent<SpriteRenderer>(); sr.sortingOrder = 40; loot = go.transform; }
   var r = loot.GetComponent<SpriteRenderer>(); r.sprite = CheckoutDesktopKit.Icon($"Products/product-{productId:000}");
   if (r.sprite) loot.localScale = Vector3.one * (.32f / Mathf.Max(r.sprite.bounds.size.x, r.sprite.bounds.size.y));
   loot.gameObject.SetActive(true);
  }
  void HideLoot() { if (loot) loot.gameObject.SetActive(false); }

  // The money bag he fills at the till and runs off with (EventProps/MoneyBag, about 30 cm tall in his hand).
  void ShowBag() {
   if (!bag) {
    bag = art.Model(holder, "MoneyBag", Vector3.zero, 0, 1f);
    var rs = bag.GetComponentsInChildren<Renderer>(true);
    if (rs.Length > 0) { var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); bag.localScale *= .3f / Mathf.Max(.01f, b.size.y); }
   }
   bag.gameObject.SetActive(true);
  }
  void HideBag() { if (bag) bag.gameObject.SetActive(false); }

  // Where he robs the till: beside the place where the customers pay at the main checkout, facing its register.
  Vector3 TillSpot(out Vector3 face) {
   var lane = map.Lanes != null && map.Lanes.lanes.Count > 0 ? map.Lanes.lanes[0] : null;
   var pay = map.QueueSpot(lane, 0); face = map.LaneRegister(lane);
   var dir = face - pay; dir.y = 0;
   var side = dir.sqrMagnitude > .01f ? Vector3.Cross(Vector3.up, dir.normalized) * .45f : Vector3.zero;
   return Ground(pay + side);
  }

  IEnumerator Coins(Vector3 at, int coins) {
   var go = new GameObject("Thief reward"); go.transform.SetParent(holder, false); go.transform.position = at;
   var tmp = go.AddComponent<TextMeshPro>(); tmp.font = CheckoutDesktopKit.Label; tmp.fontSize = 6; tmp.alignment = TextAlignmentOptions.Center;
   tmp.textWrappingMode = TextWrappingModes.NoWrap; tmp.color = new Color32(0xF2, 0xB0, 0x3D, 0xFF);
   CheckoutCoinText.Use(tmp); tmp.text = (coins < 0 ? "-" : "+") + CheckoutCoinText.Of(Mathf.Abs(coins));
   if (coins < 0) tmp.color = new Color32(0xE0, 0x4A, 0x3A, 0xFF);                // cash taken: red
   float t = 0; while (t < 1.4f && go) { t += Time.deltaTime; go.transform.position = at + Vector3.up * t * .8f; if (Camera.main) go.transform.rotation = Camera.main.transform.rotation; tmp.alpha = t > 1 ? 1 - (t - 1) / .4f : 1; yield return null; }
   if (go) Destroy(go);
  }

  // ------------------------------------------------------------------ taps
  /// <summary>A tap on the running thief or his marker (CheckoutBridge.WorldTap, panel "thief").</summary>
  public static void Tapped(string id) {
   if (!Instance) return;
   var t = Instance.bridge?.State?.security?.thief;
   if (t == null || string.IsNullOrEmpty(t.id)) return;
   if (t.phase != "fleeing") { Instance.StartCoroutine(Instance.Shrug()); return; }    // he has not taken anything yet
   Instance.bridge.Command("catchThief", "[\"" + t.id + "\"]");
   Instance.HideMarker();
  }
  IEnumerator Shrug() { if (thief == null) yield break; var s = thief.model.localScale; float k = 0; while (k < 1) { k += Time.deltaTime * 5; thief.model.localScale = s * (1 + .05f * Mathf.Sin(k * Mathf.PI)); yield return null; } thief.model.localScale = s; }
 }
}
