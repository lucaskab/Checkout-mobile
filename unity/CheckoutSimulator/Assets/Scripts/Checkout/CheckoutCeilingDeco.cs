using System.Collections.Generic;
using MarketDay;
using UnityEngine;
using UnityEngine.Rendering;

namespace Checkout {
 // The market's ceiling decorations (Lucas 05/11: "umas luminárias e umas fitinhas que correm o mercado inteiro… minha
 // irmã não entendeu o que era"). The stage dressing's "Bunting A/B/C" lines and "Pendant x,z" lamps were primitive
 // quads and spheres that read as stray marks from the game's camera. Their visuals are swapped for the Blender models
 // of scripts/blender/rede_dc.py (Resources/CheckoutRede):
 //  - MarketBunting: a 4 m span of fabric pennants (the market's two colours + cream) with string-light bulbs between
 //    them, on a sagging cord with ceiling hooks. A line is tiled with whole spans (never stretched: the stage item
 //    itself is stretched along the grown market, so the spans live in a counter-scaled holder);
 //  - MarketPendant: a dome lamp with gold bands and a lit diffuser, hanging from a ceiling rose.
 // The stage items keep deciding where and when they show (minStage/maxStage, the market's projection); the old
 // children are only switched off. Navy and gold are flat colours, so "Cores do mercado" repaints them like the rest.
 public static class CheckoutCeilingDeco {
  const float Span = 4f;               // the garland model's length (m)
  const float PendantLift = .55f;      // the lamp's ceiling point over the old item (its shade bottom ends ~2.5 m up)
  const string Holder = "Ceiling deco";
  static GameObject bunting, pendant;
  static bool loaded;
  static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
  static Shader painted, unlit;

  public static void Dress(Transform dressing) {
   if (!dressing) return;
   if (!loaded) { loaded = true; bunting = Resources.Load<GameObject>("CheckoutRede/MarketBunting"); pendant = Resources.Load<GameObject>("CheckoutRede/MarketPendant"); }
   foreach (Transform item in dressing) {
    if (item.name.StartsWith("Bunting")) { if (bunting) DressBunting(item); }
    else if (item.name.StartsWith("Pendant")) { if (pendant) DressPendant(item); }
   }
  }

  static Transform HolderOf(Transform item) {
   var h = item.Find(Holder);
   if (!h) { h = new GameObject(Holder).transform; h.SetParent(item, false); }
   // the old primitive children go dark (kept, so nothing else that looks them up breaks)
   foreach (Transform c in item) if (c != h && c.gameObject.activeSelf) c.gameObject.SetActive(false);
   return h;
  }

  static void DressBunting(Transform item) {
   var h = HolderOf(item);
   // the line's length: the old cord was 17.8 m on the unstretched market, the item is stretched with the shop
   var s = item.localScale;
   float span = 17.8f * Mathf.Abs(s.x);
   h.localScale = new Vector3(1f / Mathf.Max(.01f, s.x), 1f / Mathf.Max(.01f, s.y), 1f / Mathf.Max(.01f, s.z));
   h.localPosition = Vector3.zero; h.localRotation = Quaternion.identity;
   int n = Mathf.Max(1, Mathf.RoundToInt(span / Span));
   float each = span / n;
   while (h.childCount < n) Spawn(bunting, h, "Span");
   for (int i = 0; i < h.childCount; i++) {
    var c = h.GetChild(i); bool on = i < n; c.gameObject.SetActive(on); if (!on) continue;
    c.localPosition = new Vector3(-span / 2 + each * (i + .5f), 0, 0);
    c.localRotation = Quaternion.identity;
    c.localScale = new Vector3(each / Span, 1, 1);
   }
  }

  static void DressPendant(Transform item) {
   var h = HolderOf(item);
   var s = item.localScale;
   h.localScale = new Vector3(1f / Mathf.Max(.01f, s.x), 1f / Mathf.Max(.01f, s.y), 1f / Mathf.Max(.01f, s.z));
   h.localPosition = new Vector3(0, PendantLift / Mathf.Max(.01f, s.y), 0); h.localRotation = Quaternion.identity;
   if (h.childCount == 0) Spawn(pendant, h, "Lamp");
  }

  static void Spawn(GameObject prefab, Transform parent, string name) {
   var go = Object.Instantiate(prefab, parent, false); go.name = name;
   foreach (var col in go.GetComponentsInChildren<Collider>(true)) Object.Destroy(col);
   foreach (var r in go.GetComponentsInChildren<Renderer>(true)) {
    var list = r.sharedMaterials;
    for (int i = 0; i < list.Length; i++) list[i] = Remap(list[i]);
    r.sharedMaterials = list;
    r.shadowCastingMode = ShadowCastingMode.Off;   // thin hanging pieces: their shadows only speckled the floor
    r.receiveShadows = false;
   }
  }

  // Blender material names: C_RRGGBB = a painted colour (the game's toon shader, thin contour), E_RRGGBB = a lamp
  // (unlit, always bright).
  static Material Remap(Material source) {
   var name = source ? source.name.Replace(" (Instance)", "") : "C_FFFFFF";
   int dot = name.IndexOf('.'); if (dot > 0) name = name.Substring(0, dot);
   if (materials.TryGetValue(name, out var m) && m) return m;
   bool lamp = name.StartsWith("E_");
   string hex = name.Length >= 8 && (lamp || name.StartsWith("C_")) ? name.Substring(2, 6) : "FFFFFF";
   if (lamp) {
    if (!unlit) unlit = Shader.Find("Unlit/Color");
    m = new Material(unlit) { name = "Ceiling " + name, color = MarketSimulation.C(hex) };
   } else {
    if (!painted) painted = Shader.Find("MarketDay/Soft Painted");
    m = new Material(painted) { name = "Ceiling " + name, color = MarketSimulation.C(hex) };
    m.SetFloat("_Outline", .45f);
    m.SetColor("_OutlineColor", new Color(.22f, .115f, .055f, 1));
   }
   materials[name] = m;
   return m;
  }
 }
}
