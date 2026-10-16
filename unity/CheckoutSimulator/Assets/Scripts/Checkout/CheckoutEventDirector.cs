using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Runs the little stories of an event scene (the bus arrives, people get off and walk into the market, the bus
 // leaves…). Each story is a coroutine factory; they all start over whenever the scene is shown again.
 public sealed class CheckoutEventDirector : MonoBehaviour {
  readonly List<Func<IEnumerator>> stories = new List<Func<IEnumerator>>();
  readonly List<Action> resets = new List<Action>();
  public void Add(Func<IEnumerator> story) { stories.Add(story); if (isActiveAndEnabled) StartCoroutine(Guard(story)); }
  /// <summary>Puts things back where a story expects them when the scene is shown again.</summary>
  public void OnReset(Action reset) => resets.Add(reset);
  // A reset that throws is logged and skipped: it must never keep the scene's stories from starting.
  void OnEnable() { foreach (var r in resets) { try { r(); } catch (Exception e) { Debug.LogException(e); } } foreach (var s in stories) StartCoroutine(Guard(s)); }
  void OnDisable() { StopAllCoroutines(); }
  IEnumerator Guard(Func<IEnumerator> story) {
   // a story that throws would silently stop the scene: log it once and keep the others going
   var run = story();
   while (true) {
    object current;
    try { if (!run.MoveNext()) yield break; current = run.Current; }
    catch (Exception e) { Debug.LogException(e); yield break; }
    yield return current;
   }
  }
  // Nested coroutines are run by the Guard as plain IEnumerators.
 }
}
