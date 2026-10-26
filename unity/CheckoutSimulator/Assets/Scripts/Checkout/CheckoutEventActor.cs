using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // A person in an event scene (a copy of a market character, CheckoutEventAssets.Actor): walks along paths with the
 // character's own Walking clip, stands with its Idle, and plays event moves (CheckoutEventMoves) over them.
 // Appears and leaves with a short scale fade (getting off a bus, going into the market).
 // The characters' front is their holder's -Z (the city's walkers turn away from their velocity).
 public sealed class CheckoutEventActor : MonoBehaviour {
  Animation anim; GameObject skeleton; Vector3 size = Vector3.one;
  public string Move { get; private set; }
  public bool Visible => transform.localScale.sqrMagnitude > .01f;

  public static CheckoutEventActor Of(Transform holder) {
   if (!holder) return null;
   var a = holder.GetComponent<CheckoutEventActor>();
   if (!a) { a = holder.gameObject.AddComponent<CheckoutEventActor>(); a.size = holder.localScale; }
   a.anim = holder.GetComponentInChildren<Animation>(true); a.skeleton = a.anim ? a.anim.gameObject : null;
   return a;
  }

  // the walk (CheckoutStride): the way, and the eased turn of the body; WalkCycle: metres per Walking clip, as the market
  // characters' own (MarketCharacterAnimator.walkCycleDistance)
  readonly CheckoutVehiclePath route = new CheckoutVehiclePath(); readonly List<Vector3> way = new List<Vector3>();
  readonly CheckoutStride stride = new CheckoutStride();
  const float Bend = .8f, WalkCycle = .733f;
  void Follow(Transform follower, Vector3 offset, Quaternion turn) { if (follower) { follower.rotation = transform.rotation * turn; follower.position = transform.position + transform.rotation * offset; } }
  public static float YawFacing(Vector3 direction) => Mathf.Atan2(-direction.x, -direction.z) * Mathf.Rad2Deg;
  public void Face(Vector3 direction) { direction.y = 0; if (direction.sqrMagnitude > 1e-6f) transform.rotation = Quaternion.Euler(0, YawFacing(direction), 0); }
  public void FaceTowards(Vector3 point) => Face(point - transform.position);

  void Clip(string name) {
   if (!anim) return;
   var s = anim[name] ?? anim["Idle"]; if (!s) return;
   if (anim.IsPlaying(s.name)) return;
   s.wrapMode = WrapMode.Loop; anim.CrossFade(s.name, .2f);
  }

  /// <summary>Plays an event move (null = just the character's own Idle).</summary>
  public void Do(string move, float offset = 0) {
   Move = move;
   if (string.IsNullOrEmpty(move)) { var m = skeleton ? skeleton.GetComponent<CheckoutEventMoves>() : null; if (m) m.Stop(); Clip("Idle"); return; }
   Clip("Idle");
   if (skeleton) CheckoutEventMoves.Play(skeleton, move, 1, offset);
  }
  public CheckoutEventMoves Moves => skeleton ? skeleton.GetComponent<CheckoutEventMoves>() : null;

  public void Show(bool show) { transform.localScale = show ? size : Vector3.zero; }
  public IEnumerator Fade(bool show, float seconds = .35f) {
   var from = transform.localScale; var to = show ? size : Vector3.zero;
   for (float t = 0; t < seconds; t += Time.deltaTime) { transform.localScale = Vector3.Lerp(from, to, Mathf.SmoothStep(0, 1, t / seconds)); yield return null; }
   transform.localScale = to;
  }

  /// <summary>Walks along the points (the first may be where it already stands). `carry` = an arms-only move
  /// (HoldHandle, CarryBox) kept while walking. `follower` is moved along keeping its offset (a pallet jack).
  /// Lucas 26/10: the way's corners are rounded (about a metre), the body eases round to where it walks (turning on the
  /// spot first when it sets off the other way), a little slower round a tight corner, and the walk cycle runs at the
  /// pace really walked, so the feet do not slide.</summary>
  public IEnumerator Walk(IList<Vector3> points, float speed = 1.25f, string carry = null, Transform follower = null) {
   if (points == null || points.Count == 0) yield break;
   points = CheckoutLampClearance.Detour(points, transform.position);   // round the street lamps, not through them
   Clip("Walking");
   if (!string.IsNullOrEmpty(carry)) { if (skeleton) CheckoutEventMoves.Play(skeleton, carry); Move = carry; }
   else { var m = Moves; if (m) m.Stop(); Move = null; }
   Vector3 followOffset = follower ? Quaternion.Inverse(transform.rotation) * (follower.position - transform.position) : Vector3.zero;
   Quaternion followTurn = follower ? Quaternion.Inverse(transform.rotation) * follower.rotation : Quaternion.identity;
   way.Clear(); way.Add(transform.position); foreach (var p in points) way.Add(p);
   route.Build(way, Bend, null, false, null, true);
   if (route.Ready) {
    // set off the other way: turn on the spot first (eased), then walk
    route.Sample(0, out var first);
    for (float t = 0; t < 1.5f && Vector3.Angle(-transform.forward, first) > 12f; t += Time.deltaTime) { stride.Face(transform, first, Time.deltaTime, false); Follow(follower, followOffset, followTurn); yield return null; }
    var walking = anim ? anim["Walking"] : null; float baseSpeed = walking ? walking.speed : 1;
    float s = 0, v = 0;
    while (s < route.Length - .01f) {
     float dt = Time.deltaTime;
     float top = Mathf.Min(speed, route.Allowed(s, speed, 1.5f, 1f));   // a little slower round a tight corner
     v = Mathf.MoveTowards(v, top, 2.5f * dt);
     s = Mathf.Min(route.Length, s + v * dt);
     var pos = route.Sample(s, out _);
     route.Sample(Mathf.Min(route.Length, s + v * CheckoutStride.WalkTurnTime), out var ahead);   // (leads the eased turn)
     transform.position = pos; stride.Face(transform, ahead, dt, true);
     if (walking) walking.speed = v * walking.length / WalkCycle;   // the feet move as fast as the body
     Follow(follower, followOffset, followTurn);
     yield return null;
    }
    if (walking) walking.speed = baseSpeed;
   }
   Clip("Idle");
   if (string.IsNullOrEmpty(carry)) Do(null);
  }
 }
}
