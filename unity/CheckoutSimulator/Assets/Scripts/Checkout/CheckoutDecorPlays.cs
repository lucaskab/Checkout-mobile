using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;

namespace Checkout {
 // The coin machines as melhorias (Lucas 18/10): when a customer plays the gumball or the claw machine the game
 // adds the coins (src/stores/game-store.ts processNextCustomer) and lists the play in the snapshot (decorPlays).
 // Here each new play floats "+coins" over the placed machine and gives it a little bounce.
 public sealed class CheckoutDecorPlays : MonoBehaviour {
  CheckoutBridge bridge; double seen = -1;
  // Photo booths (Lucas 19/10): the curtain ("Anim Curtain", pivot on the rail side, local X = how far it is drawn)
  // stays open; when a customer takes photos it closes, the flash goes off inside, and it opens again.
  const float CurtainOpen = .25f;
  readonly Dictionary<Transform, Vector3> curtains = new Dictionary<Transform, Vector3>();
  readonly HashSet<Transform> busy = new HashSet<Transform>();
  float nextScan;

  public static void Ensure() {
   if (FindAnyObjectByType<CheckoutDecorPlays>()) return;
   new GameObject("Decor plays").AddComponent<CheckoutDecorPlays>();
  }

  void Update() {
   if (Time.unscaledTime >= nextScan) { nextScan = Time.unscaledTime + 1f; ScanCurtains(); }
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
    if (item != null && item.root) {
     StartCoroutine(Pop(item.root, p.coins));
     var curtain = CurtainOf(item.root);
     if (curtain && !busy.Contains(curtain)) StartCoroutine(TakePhotos(curtain));
    }
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

  // Plays the booth's photo animation on any booth (the "decorshow" autotest uses it on a plain clone).
  public static void Photos(Transform booth) {
   Ensure(); var self = FindAnyObjectByType<CheckoutDecorPlays>(); var c = booth ? CurtainOf(booth) : null;
   if (!self || !c || self.busy.Contains(c)) return;
   if (!self.curtains.ContainsKey(c)) { self.curtains[c] = c.localScale; c.localScale = self.Drawn(c, CurtainOpen); }
   self.StartCoroutine(self.TakePhotos(c));
  }

  static Transform CurtainOf(Transform root) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("Anim Curtain"));

  // Every placed booth starts with its curtain drawn open (the model is built closed).
  void ScanCurtains() {
   var interior = CheckoutInterior.Active; if (!interior) return;
   foreach (var it in interior.items.Values) {
    if (it == null || !it.root || it.type != "photo-booth") continue;
    var c = CurtainOf(it.root); if (!c || curtains.ContainsKey(c)) continue;
    curtains[c] = c.localScale;
    if (!busy.Contains(c)) c.localScale = Drawn(c, CurtainOpen);
   }
   foreach (var dead in curtains.Keys.Where(k => !k).ToList()) curtains.Remove(dead);
  }

  Vector3 Drawn(Transform c, float amount) { var b = curtains.TryGetValue(c, out var s) ? s : c.localScale; return new Vector3(b.x * amount, b.y, b.z); }

  IEnumerator TakePhotos(Transform curtain) {
   if (!curtains.ContainsKey(curtain)) curtains[curtain] = curtain.localScale;
   busy.Add(curtain);
   yield return Draw(curtain, CurtainOpen, 1f, .35f);
   // the flash: a quick white light inside the booth, twice
   var flash = new GameObject("Booth flash").AddComponent<Light>();
   flash.type = LightType.Point; flash.color = Color.white; flash.range = 2.2f; flash.intensity = 0;
   flash.transform.position = curtain.parent ? curtain.parent.position + Vector3.up * 1.4f : curtain.position;
   for (int shot = 0; shot < 2; shot++) {
    yield return new WaitForSeconds(.35f);
    for (float t = 0; t < .18f; t += Time.deltaTime) { if (flash) flash.intensity = 6f * (1 - t / .18f); yield return null; }
    if (flash) flash.intensity = 0;
   }
   if (flash) Destroy(flash.gameObject);
   yield return new WaitForSeconds(.4f);
   if (curtain) yield return Draw(curtain, 1f, CurtainOpen, .45f);
   busy.Remove(curtain);
  }

  IEnumerator Draw(Transform c, float from, float to, float seconds) {
   for (float t = 0; t < seconds; t += Time.deltaTime) {
    if (!c) yield break;
    float k = Mathf.SmoothStep(0, 1, t / seconds);
    c.localScale = Drawn(c, Mathf.Lerp(from, to, k));
    yield return null;
   }
   if (c) c.localScale = Drawn(c, to);
  }

  static float TopOf(Transform t) {
   float top = 1.4f; bool any = false;
   foreach (var r in t.GetComponentsInChildren<Renderer>()) { var h = r.bounds.max.y - t.position.y; if (!any || h > top) { top = h; any = true; } }
   return top;
  }
 }
}
