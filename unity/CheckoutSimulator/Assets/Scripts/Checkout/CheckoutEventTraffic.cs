using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // What the market events do to the city's traffic (CheckoutNeighborhoodTraffic, CheckoutCityTraffic):
 // - a curb block: something stands in the westbound curbside lane (road works, a parked truck, the street market);
 //   cars swerve into the inner lane around it, and the drop-off at the market moves past it;
 // - obstacles: every event vehicle (a bus at its stop, the sound car, the jam's cars) is a box the other cars queue
 //   behind instead of driving through;
 // - a jam: the avenue's own traffic steps aside and the event's queues are the traffic.
 // Avenue (CheckoutStreetLayout): north curb z -12.5, westbound lanes z -14 (curb) and -17, eastbound -20 and -23.
 public static class CheckoutEventTraffic {
  public const float CurbLane = -14f, InnerWest = -17f, InnerEast = -20f, CurbEast = -23f, CurbNorth = -12.5f;

  // Two things can stand in the curb lane: an event's scene and a supplier truck unloading at the curb (the small
  // markets have no yard). Cars swerve round the whole stretch both cover.
  static bool eventBlock, deliveryBlock;
  static Vector2 eventSpan, deliverySpan;
  public static bool HasCurbBlock => eventBlock || deliveryBlock;
  public static float BlockFrom => eventBlock && deliveryBlock ? Mathf.Min(eventSpan.x, deliverySpan.x) : eventBlock ? eventSpan.x : deliverySpan.x;
  public static float BlockTo => eventBlock && deliveryBlock ? Mathf.Max(eventSpan.y, deliverySpan.y) : eventBlock ? eventSpan.y : deliverySpan.y;
  /// <summary>The stretch an event's scene takes (null when no event blocks the curb).</summary>
  public static Vector2? EventBlock => eventBlock ? eventSpan : (Vector2?)null;
  public static bool AvenueJammed { get; set; }

  public static void SetCurbBlock(float from, float to) { eventBlock = true; eventSpan = new Vector2(from, to); }
  public static void ClearCurbBlock() { eventBlock = false; }
  public static void SetDeliveryBlock(float from, float to) { deliveryBlock = true; deliverySpan = new Vector2(from, to); }
  public static void ClearDeliveryBlock() { deliveryBlock = false; }

  sealed class Obstacle { public Transform root; public Bounds box; }
  static readonly List<Obstacle> obstacles = new List<Obstacle>();

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
  static void Reset() { obstacles.Clear(); eventBlock = deliveryBlock = false; AvenueJammed = false; pedestrians = null; }

  /// <summary>A vehicle (or any solid thing) the cars must not drive through; `box` is in the root's space.</summary>
  public static void Register(Transform root, Bounds box) {
   Unregister(root);
   obstacles.Add(new Obstacle { root = root, box = box });
  }
  public static void Unregister(Transform root) { obstacles.RemoveAll(o => !o.root || o.root == root); }

  static bool Inside(Obstacle o, Vector3 world, float pad) {
   var p = o.root.InverseTransformPoint(world);
   var s = o.root.lossyScale; float px = pad / Mathf.Max(.01f, Mathf.Abs(s.x)), pz = pad / Mathf.Max(.01f, Mathf.Abs(s.z));
   var b = o.box;
   return p.x > b.min.x - px && p.x < b.max.x + px && p.z > b.min.z - pz && p.z < b.max.z + pz;
  }

  /// <summary>True when an event obstacle (other than `self`) is on the stretch `reach` metres ahead of `from`.</summary>
  public static bool Blocks(Vector3 from, Vector3 direction, float reach, float halfWidth = .9f, Transform self = null, System.Func<Transform, bool> ignore = null) {
   direction.y = 0; if (direction.sqrMagnitude < 1e-6f) return false; direction.Normalize();
   for (int i = obstacles.Count - 1; i >= 0; i--) {
    var o = obstacles[i];
    if (!o.root) { obstacles.RemoveAt(i); continue; }
    if (o.root == self || !o.root.gameObject.activeInHierarchy) continue;
    if (ignore != null && ignore(o.root)) continue;
    for (float s = .4f; s <= reach; s += .5f)
     if (Inside(o, from + direction * s, halfWidth)) return true;
   }
   return false;
  }

  /// <summary>Whether a point is covered by any event obstacle (spawning, drop-offs).</summary>
  public static bool Covered(Vector3 point, float pad = .3f, Transform self = null) {
   foreach (var o in obstacles) if (o.root && o.root != self && o.root.gameObject.activeInHierarchy && Inside(o, point, pad)) return true;
   return false;
  }

  // ---------------------------------------------------------------- what event vehicles yield to
  static CheckoutCityPedestrian[] pedestrians; static float pedestriansAt;
  static CheckoutNeighborhoodTraffic neighborhood; static CheckoutCityTraffic market;

  /// <summary>For event vehicles: a city car, a market visitor's car or a pedestrian in the way.</summary>
  public static bool CityAhead(Vector3 front, Vector3 direction, float reach, float halfWidth = 1.15f) {
   direction.y = 0; if (direction.sqrMagnitude < 1e-6f) return false; direction.Normalize();
   if (!neighborhood) neighborhood = Object.FindAnyObjectByType<CheckoutNeighborhoodTraffic>();
   if (!market) market = Object.FindAnyObjectByType<CheckoutCityTraffic>();
   if (pedestrians == null || Time.time - pedestriansAt > 3) { pedestrians = Object.FindObjectsByType<CheckoutCityPedestrian>(FindObjectsSortMode.None); pedestriansAt = Time.time; }
   if (neighborhood && neighborhood.cars != null && !AvenueJammed)
    foreach (var c in neighborhood.cars) if (c != null && c.vehicle && c.vehicle.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(front, direction, c.vehicle.position, reach + 1.8f, halfWidth)) return true;
   if (market && market.vehicles != null)
    foreach (var v in market.vehicles) if (v && v.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(front, direction, v.position, reach + 1.8f, halfWidth)) return true;
   foreach (var p in pedestrians) if (p && p.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(front, direction, p.transform.position, reach, .9f)) return true;
   return false;
  }
 }
}
