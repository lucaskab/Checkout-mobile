using System.Collections;
using TMPro;
using UnityEngine;

namespace Checkout {
 // The coin machines as melhorias (Lucas 18/10): when a customer plays the gumball or the claw machine the game
 // adds the coins (src/stores/game-store.ts processNextCustomer) and lists the play in the snapshot (decorPlays).
 // Here each new play floats "+coins" over the placed machine and gives it a little bounce.
 public sealed class CheckoutDecorPlays : MonoBehaviour {
  CheckoutBridge bridge; double seen = -1;

  public static void Ensure() {
   if (FindAnyObjectByType<CheckoutDecorPlays>()) return;
   new GameObject("Decor plays").AddComponent<CheckoutDecorPlays>();
  }

  void Update() {
   if (!bridge) bridge = FindAnyObjectByType<CheckoutBridge>();
   var plays = bridge ? bridge.State?.decorPlays : null;
   if (plays == null) return;
   double newest = seen;
   foreach (var p in plays) if (p != null && p.at > newest) newest = p.at;
   // the first snapshot only sets the mark: older plays are not replayed
   if (seen < 0) { seen = newest < 0 ? 0 : newest; return; }
   foreach (var p in plays) {
    if (p == null || p.at <= seen) continue;
    var interior = CheckoutInterior.Active; var item = interior ? interior.Get(p.itemId) : null;
    if (item != null && item.root) StartCoroutine(Pop(item.root, p.coins));
   }
   seen = newest;
  }

  IEnumerator Pop(Transform machine, int coins) {
   var top = machine.position + Vector3.up * (TopOf(machine) + .25f);
   var go = new GameObject("Machine coins"); go.transform.position = top;
   var tmp = go.AddComponent<TextMeshPro>();
   tmp.font = CheckoutDesktopKit.Label; tmp.fontSize = 6; tmp.alignment = TextAlignmentOptions.Center;
   tmp.textWrappingMode = TextWrappingModes.NoWrap; tmp.color = new Color32(0xF2, 0xB0, 0x3D, 0xFF);
   tmp.outlineWidth = .25f; tmp.outlineColor = new Color32(0x4A, 0x36, 0x24, 0xFF);
   CheckoutCoinText.Use(tmp); tmp.text = "+" + CheckoutCoinText.Of(coins);
   var baseScale = machine.localScale; var cam = Camera.main;
   for (float t = 0; t < 1.5f; t += Time.deltaTime) {
    if (!go) yield break;
    go.transform.position = top + Vector3.up * (t * .9f);
    if (cam) go.transform.rotation = Quaternion.LookRotation(go.transform.position - cam.transform.position);
    var c = tmp.color; c.a = t < 1.1f ? 1 : 1 - (t - 1.1f) / .4f; tmp.color = c;
    if (machine) { float b = t < .3f ? Mathf.Sin(t / .3f * Mathf.PI) * .06f : 0; machine.localScale = new Vector3(baseScale.x * (1 + b * .5f), baseScale.y * (1 - b), baseScale.z * (1 + b * .5f)); }
    yield return null;
   }
   if (machine) machine.localScale = baseScale;
   Destroy(go);
  }

  static float TopOf(Transform t) {
   float top = 1.4f; bool any = false;
   foreach (var r in t.GetComponentsInChildren<Renderer>()) { var h = r.bounds.max.y - t.position.y; if (!any || h > top) { top = h; any = true; } }
   return top;
  }
 }
}
