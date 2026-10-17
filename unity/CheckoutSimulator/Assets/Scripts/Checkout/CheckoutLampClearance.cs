using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout {
 // Street lamps and the people on the footway (Lucas 17/10: posts went through pedestrians, lamp heads sat on their
 // hair). Every lamp on the map is found once (its head, the same way CheckoutStreetLightPools finds them, and the
 // pole under it); its footprint is the strip from the pole to the point under the head. Then:
 //  - the city's walkers (NavMesh agents) get a carved NavMeshObstacle over that strip, so they path round it;
 //  - the event scenes move a person standing on it aside (Clear) and bend a walk that crosses it (Detour).
 public static class CheckoutLampClearance {
  static readonly string[] EmitterNames = { "luminous lens", "lamp globe", "lamp light", "lamp head glow", "streetlight lens" };
  static readonly string[] EmitterMaterials = { "citylamp", "lampglobe", "modernlampglow", "yardlamp", "streetlampglow" };
  struct Strip { public Vector2 a, b; }
  static List<Strip> strips;
  // what the game camera sees standing "in" a lamp: the ground behind the post and behind its head, as far back as
  // the 3.9 m lamp reaches in the picture (only for people placed to stand still)
  static List<Strip> views;
  const float Body = .62f;   // a person's half width plus the pole, and room for the lamp head over their hair

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
  static void Reset() { strips = null; views = null; }

  public static int Count { get { Ensure(); return strips.Count; } }
  /// <summary>QA: how many lamps, how many with their pole found.</summary>
  public static string Describe { get { Ensure(); int poles = 0; foreach (var s in strips) if ((s.b - s.a).sqrMagnitude > .01f) poles++; return $"{strips.Count} lamps, {poles} with a pole"; } }

  /// <summary>Finds the lamps and carves them out of the walkers' NavMesh (once per scene).</summary>
  public static void Ensure() {
   if (strips != null) return;
   strips = new List<Strip>(); views = new List<Strip>();
   var cam = Camera.main; Vector2 back = Vector2.zero; float reach = 0;
   if (cam) { var f = cam.transform.forward; var flat = new Vector2(f.x, f.z); if (flat.sqrMagnitude > 1e-4f) { back = flat.normalized; float pitch = Mathf.Asin(Mathf.Clamp(-f.y, -1, 1)); reach = Mathf.Clamp(3.9f / Mathf.Max(.3f, Mathf.Tan(pitch)), 0, 6f); } }
   var all = Object.FindObjectsByType<Renderer>(FindObjectsInactive.Exclude);
   var heads = new List<Vector3>();
   foreach (var r in all) {
    if (r is ParticleSystemRenderer) continue;
    var n = r.name.ToLowerInvariant();
    bool match = EmitterNames.Contains(n) || r.sharedMaterials.Any(m => m && EmitterMaterials.Any(e => m.name.ToLowerInvariant().StartsWith(e)));
    if (!match) continue;
    var c = r.bounds.center; if (c.y < 2.2f || c.y > 9) continue;
    if (heads.Any(h => Flat(h - c).sqrMagnitude < 1.4f * 1.4f)) continue;
    heads.Add(c);
   }
   // the pole: a tall thin renderer reaching up near the head
   var poles = all.Where(r => { var b = r.bounds; return b.size.y > 1.8f && b.size.x < .4f && b.size.z < .4f && b.min.y < .8f; }).Select(r => r.bounds).ToList();
   var holder = new GameObject("Lamp clearance").transform;
   foreach (var h in heads) {
    var head = new Vector2(h.x, h.z); var foot = head; float best = 1.6f;
    foreach (var b in poles) {
     if (b.max.y < h.y - 1.2f || b.max.y > h.y + 1.6f) continue;
     var p = new Vector2(b.center.x, b.center.z); float d = (p - head).magnitude;
     if (d < best) { best = d; foot = p; }
    }
    strips.Add(new Strip { a = foot, b = head });
    if (reach > 0) { views.Add(new Strip { a = foot, b = foot + back * reach }); views.Add(new Strip { a = head, b = head + back * reach }); }
    // carve the strip for the NavMesh walkers
    var mid = (foot + head) * .5f; var along = head - foot;
    var go = new GameObject("Lamp footprint"); go.transform.SetParent(holder, false);
    go.transform.position = new Vector3(mid.x, .13f, mid.y);
    if (along.sqrMagnitude > 1e-4f) go.transform.rotation = Quaternion.LookRotation(new Vector3(along.x, 0, along.y));
    var o = go.AddComponent<NavMeshObstacle>();
    o.shape = NavMeshObstacleShape.Box; o.carving = true; o.carveOnlyStationary = true;
    // wide enough for the rain umbrellas the walkers carry (0.57 m radius, at the lamp head's height)
    o.size = new Vector3(1.5f, 2f, along.magnitude + 1.6f); o.center = Vector3.up;
   }
  }

  static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);

  static Vector2 Closest(Strip s, Vector2 p) {
   var ab = s.b - s.a; float t = ab.sqrMagnitude < 1e-6f ? 0 : Mathf.Clamp01(Vector2.Dot(p - s.a, ab) / ab.sqrMagnitude);
   return s.a + ab * t;
  }

  /// <summary>Distance from a point to the nearest lamp footprint (infinity when there are none).</summary>
  public static float Distance(Vector3 p) {
   Ensure(); float best = float.PositiveInfinity; var q = new Vector2(p.x, p.z);
   foreach (var s in strips) best = Mathf.Min(best, (q - Closest(s, q)).magnitude);
   return best;
  }

  /// <summary>The spot itself, or the nearest spot `room` metres clear of every lamp.</summary>
  public static Vector3 Clear(Vector3 p, float room = Body) => Clear(p, room, false);
  /// <summary>Clear, and also out of the lamp's picture (not right behind the post as the camera sees it): for people
  /// placed to stand somewhere.</summary>
  public static Vector3 ClearInView(Vector3 p, float room = Body) => Clear(p, room, true);

  static Vector3 Clear(Vector3 p, float room, bool view) {
   Ensure();
   for (int pass = 0; pass < 4; pass++) {
    bool moved = false; var q = new Vector2(p.x, p.z);
    foreach (var s in view ? strips.Concat(views) : strips) {
     var c = Closest(s, q); var away = q - c; float d = away.magnitude;
     if (d >= room) continue;
     // the nearest free spot: straight away from the lamp (or across its strip when standing right on it)
     var side = d > 1e-3f ? away / d : new Vector2(-(s.b - s.a).y, (s.b - s.a).x);
     if (side.sqrMagnitude < 1e-6f) side = Vector2.right;
     side.Normalize();
     q = c + side * room; moved = true;
    }
    p.x = q.x; p.z = q.y;
    if (!moved) break;
   }
   return p;
  }

  /// <summary>The walk with a bend round every lamp it would pass through (people walk round the post).</summary>
  public static List<Vector3> Detour(IList<Vector3> points, Vector3 start, float room = Body) {
   Ensure();
   var result = new List<Vector3>();
   var from = start;
   foreach (var target in points) {
    var to = Clear(target, room, true);   // a corner of the walk on (or right behind) a lamp moves off it too
    if (strips.Count > 0) {
     var a = new Vector2(from.x, from.z); var b = new Vector2(to.x, to.z); var ab = b - a; float len = ab.magnitude;
     if (len > .2f) {
      // the closest pass of this leg to each lamp, in order along the leg
      var bends = new List<(float t, Vector3 p)>();
      foreach (var s in strips) {
       float bestT = 0, bestD = float.PositiveInfinity;
       for (float t = 0; t <= 1.0001f; t += .2f / len) {
        var q = a + ab * Mathf.Min(1, t); float d = (q - Closest(s, q)).magnitude;
        if (d < bestD) { bestD = d; bestT = Mathf.Min(1, t); }
       }
       if (bestD >= room || bestT <= .02f || bestT >= .98f) continue;
       // step aside, square to the walk, on the side of the lamp's far end from the path
       var at = Vector3.Lerp(from, to, bestT); var dir = ab / len; var n = new Vector2(-dir.y, dir.x);
       var q0 = new Vector2(at.x, at.z); var mid = (s.a + s.b) * .5f; float sideSign = Vector2.Dot(q0 - mid, n) >= 0 ? 1 : -1;
       Vector3 bend = at;
       for (float k = .1f; k <= 2.4f; k += .1f) {
        bool found = false;
        foreach (float sg in new[] { sideSign, -sideSign }) {
         var c = at + new Vector3(n.x, 0, n.y) * (k * sg);
         if (Distance(c) >= room + .05f) { bend = c; found = true; break; }
        }
        if (found) break;
       }
       bends.Add((bestT, bend));
      }
      foreach (var bend in bends.OrderBy(x => x.t)) result.Add(bend.p);
     }
    }
    result.Add(to); from = to;
   }
   return result;
  }
 }
}
