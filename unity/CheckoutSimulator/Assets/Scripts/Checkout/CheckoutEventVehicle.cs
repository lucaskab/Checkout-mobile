using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // An event vehicle rig (EventRigs/Rig_<Vehicle>: Body + Wheel_* bones, buses also Door_*): drives along a path at
 // road speed, slows down and stops for whatever is ahead (city cars, pedestrians on a crossing, other event
 // vehicles), rolls its wheels by the distance driven, pitches its body when braking or pulling away and leans it a
 // little out of the bends (Lucas 26/10: the turns follow a smooth path, CheckoutVehiclePath). While it
 // exists it is an obstacle the city's cars queue behind (CheckoutEventTraffic).
 // The rigs face +X at yaw 0 (the front wheels are Wheel_F_*).
 public sealed class CheckoutEventVehicle : MonoBehaviour {
  struct Wheel { public Transform bone; public Quaternion rest; public float radius; }
  readonly List<Wheel> wheels = new List<Wheel>();
  Transform body; Quaternion bodyRest; Animation anim; Bounds box;
  float roll, pitch, lean, lastSpeed, lastYaw;
  readonly CheckoutVehiclePath route = new CheckoutVehiclePath();
  public float Speed { get; private set; }
  public float HalfLength => box.extents.x;
  /// <summary>Distance from the rig's origin to its front / back / side (its own axes).</summary>
  public float FrontOffset => box.max.x;
  public float BackOffset => -box.min.x;
  public float HalfWidth => box.extents.z;
  /// <summary>The vehicle waits (engine running) while true — e.g. its driver went shopping.</summary>
  public bool Hold { get; set; }
  /// <summary>Extra check for what else stops this vehicle (a lane's leader…), on top of the city and the obstacles.</summary>
  public System.Func<Vector3, Vector3, bool> ExtraBlock;
  /// <summary>Obstacles this vehicle never waits for (e.g. the cars of the other jam lanes off the roundabout).</summary>
  public System.Func<Transform, bool> Ignore;
  public bool YieldToCity = true;

  public static CheckoutEventVehicle Attach(Transform holder) {
   var v = holder.GetComponent<CheckoutEventVehicle>() ?? holder.gameObject.AddComponent<CheckoutEventVehicle>();
   v.Bind(); return v;
  }

  void Bind() {
   wheels.Clear();
   anim = CheckoutEventAssets.RigAnimation(transform);
   foreach (var t in GetComponentsInChildren<Transform>(true)) {
    if (t.name == "Body") { body = t; bodyRest = t.localRotation; }
    else if (t.name.StartsWith("Wheel_")) {
     float r = .4f;
     foreach (var mr in t.GetComponentsInChildren<Renderer>(true)) { r = mr.bounds.extents.y; break; }
     wheels.Add(new Wheel { bone = t, rest = t.localRotation, radius = Mathf.Max(.15f, r) });
    }
   }
   // footprint in the holder's space
   var rs = GetComponentsInChildren<Renderer>(true);
   box = new Bounds(Vector3.zero, Vector3.one);
   bool first = true;
   foreach (var r in rs) {
    var b = r.bounds;
    for (int i = 0; i < 8; i++) {
     var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
     var l = transform.InverseTransformPoint(c);
     if (first) { box = new Bounds(l, Vector3.zero); first = false; } else box.Encapsulate(l);
    }
   }
   CheckoutEventTraffic.Register(transform, box);
  }

  void OnEnable() { if (wheels.Count > 0 || body) CheckoutEventTraffic.Register(transform, box); }
  void OnDisable() { CheckoutEventTraffic.Unregister(transform); Speed = 0; }
  void OnDestroy() { CheckoutEventTraffic.Unregister(transform); }

  public Vector3 Forward => transform.right;
  public Vector3 Front => transform.position + transform.right * box.max.x * transform.lossyScale.x;
  public static float YawFor(Vector3 direction) => Mathf.Atan2(-direction.z, direction.x) * Mathf.Rad2Deg;
  public void Face(Vector3 direction) { direction.y = 0; if (direction.sqrMagnitude > 1e-6f) transform.rotation = Quaternion.Euler(0, YawFor(direction), 0); }

  // ---------------------------------------------------------------- driving
  bool Blocked(Vector3 direction, float reach) {
   if (Hold) return true;
   var front = Front;
   if (YieldToCity && CheckoutEventTraffic.CityAhead(front, direction, reach)) return true;
   if (CheckoutEventTraffic.Blocks(front - direction * .3f, direction, reach, 1.0f, transform, Ignore)) return true;
   return ExtraBlock != null && ExtraBlock(front, direction);
  }

  /// <summary>Drives along `path` (world points, the first is where it starts; its corners rounded, round the roundabout's
  /// island) and stops at the last point. It always faces the way it moves, slows down before the bends.</summary>
  public IEnumerator Drive(IList<Vector3> path, float cruise = 6f, bool stop = true, float accel = 2.2f, float brake = 2.6f) {
   if (path == null || path.Count < 2) yield break;
   route.Build(path);
   float y = path[0].y, s = 0, speed = Speed;
   var p = route.Sample(0, out var direction); p.y = y; transform.position = p; Face(direction);
   while (s < route.Length - .01f) {
    float top = Mathf.Min(cruise, route.Allowed(s, cruise, brake));
    if (stop) top = Mathf.Min(top, Mathf.Max(.3f, route.StopSpeed(s, brake)));
    float look = 1.2f + speed * speed / (2 * brake);
    if (Blocked(direction, look)) top = 0;
    speed = speed < top ? Mathf.Min(top, speed + accel * Time.deltaTime) : Mathf.Max(top, speed - brake * 1.6f * Time.deltaTime);
    s = Mathf.Min(route.Length, s + speed * Time.deltaTime);
    p = route.Sample(s, out direction); p.y = y; transform.position = p; Face(direction);
    Speed = speed;
    yield return null;
   }
   Speed = 0;
  }

  /// <summary>Plays a clip of the rig (bus doors) and waits for it.</summary>
  public IEnumerator Clip(string clip) {
   if (!anim) yield break;
   var state = CheckoutEventAssets.PlayClip(anim, clip, WrapMode.ClampForever);
   if (state == null) yield break;
   yield return new WaitForSeconds(state.length);
  }
  public void Idle(string clip = "Idle") { if (anim && CheckoutEventAssets.ClipState(anim, clip) != null) CheckoutEventAssets.PlayClip(anim, clip, WrapMode.Loop); }

  /// <summary>Moves the vehicle by hand (the jam's car following): sets its speed for the wheels and the pitch.</summary>
  public void Moved(float distance, float dt) { Speed = dt > 0 ? distance / dt : 0; }

  void LateUpdate() {
   float dt = Mathf.Max(1e-4f, Time.deltaTime);
   float accel = (Speed - lastSpeed) / dt; lastSpeed = Speed;
   roll += Speed * dt;
   var heading = transform.right; heading.y = 0;
   var axis = Vector3.Cross(Vector3.up, heading.normalized);
   foreach (var w in wheels) {
    if (!w.bone) continue;
    w.bone.localRotation = w.rest;
    w.bone.rotation = Quaternion.AngleAxis(roll / w.radius * Mathf.Rad2Deg, axis) * w.bone.rotation;
   }
   // nose dips when braking, lifts when pulling away (a few degrees, smoothed)
   pitch = Mathf.Lerp(pitch, Mathf.Clamp(-accel * .9f, -2.5f, 2.5f), 1 - Mathf.Exp(-dt * 5));
   // leans out of a bend by its sideways acceleration (speed x yaw rate; a right turn tips it to the left)
   float yaw = transform.eulerAngles.y, rate = Mathf.DeltaAngle(lastYaw, yaw) * Mathf.Deg2Rad / dt; lastYaw = yaw;
   if (Mathf.Abs(rate) > 3f) rate = 0;   // placed somewhere else (a new lap, a reset), not a bend
   lean = Mathf.Lerp(lean, Mathf.Clamp(Speed * rate * .7f, -2.5f, 2.5f), 1 - Mathf.Exp(-dt * 4));
   bool animated = anim && anim.isPlaying;
   if (body && !animated) {
    body.localRotation = bodyRest;
    body.rotation = Quaternion.AngleAxis(lean, heading.normalized) * Quaternion.AngleAxis(pitch, axis) * body.rotation;   // +angle about up x heading dips the nose
   }
  }
 }
}
