using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // The words written on the map with TextMesh (the shop's welcome sign, the street name signs):
 //  - in the player's language (CheckoutI18n.T on the Portuguese they were built with, again on a language change);
 //  - street names fit inside their green blade (Lucas 17/10: "COLUMBUS CIRCLE" ran past the board) and are drawn
 //    with a depth-tested material, so one blade's name no longer shows through the other blade or a person.
 // Texts made by other systems (construction titles, floating numbers) come and go: the map is looked at again every
 // couple of seconds and only texts seen for the first time are touched.
 public sealed class CheckoutSignText : MonoBehaviour {
  sealed class Sign { public TextMesh text; public string source; public float size; public bool street; public Transform blade; }
  // the blades of CheckoutCentralParkBuilder.StreetSign (their meshes were merged into the city later, so the
  // label usually has no blade object to measure)
  static readonly Vector2 Blade = new Vector2(1.9f, .3f);
  readonly Dictionary<TextMesh, Sign> signs = new Dictionary<TextMesh, Sign>();
  float nextScan; bool dirty = true;
  static Material depthText; static Font depthFont;
  /// <summary>QA: what the last fits measured.</summary>
  public static readonly List<string> Report = new List<string>();

  public static void Ensure() {
   if (FindAnyObjectByType<CheckoutSignText>()) return;
   new GameObject("Sign text").AddComponent<CheckoutSignText>();
  }

  void OnEnable() => CheckoutI18n.Changed += Retranslate;
  void OnDisable() => CheckoutI18n.Changed -= Retranslate;
  void Retranslate() { dirty = true; nextScan = 0; }

  void LateUpdate() {
   if (Time.unscaledTime < nextScan) return;
   nextScan = Time.unscaledTime + 2f;
   foreach (var t in FindObjectsByType<TextMesh>(FindObjectsInactive.Exclude)) {
    if (signs.ContainsKey(t)) continue;
    var parent = t.transform.parent;
    bool street = parent && parent.name == "Street name sign";
    bool shop = t.name == "Portal label";
    if (!street && !shop) continue;
    var s = new Sign { text = t, source = t.text, size = t.characterSize, street = street };
    if (street) {
     s.blade = parent.Find("Blade " + t.name);
     // the names were laid 3 cm off their blade, inside the 5 cm post that runs through the blades' middle: the
     // post (a 13 cm lamp post on some corners) covered the middle letters; 12 cm off the blade clears it.
     var lp = t.transform.localPosition;
     if (Mathf.Abs(lp.z) > .005f && Mathf.Abs(lp.z) < .06f) lp.z = Mathf.Sign(lp.z) * .12f;
     if (Mathf.Abs(lp.x) > .005f && Mathf.Abs(lp.x) < .06f) lp.x = Mathf.Sign(lp.x) * .12f;
     t.transform.localPosition = lp;
    }
    signs[t] = s; Apply(s);
   }
   if (dirty) { dirty = false; foreach (var s in signs.Values) if (s.text) Apply(s); }
  }

  void Apply(Sign s) {
   var t = s.text;
   var wanted = CheckoutI18n.T(s.source);
   if (t.text != wanted) t.text = wanted;
   if (!s.street) return;
   var r = t.GetComponent<MeshRenderer>();
   if (r && t.font) {
    if (!depthText || depthFont != t.font) {
     var shader = Resources.Load<Shader>("CheckoutProps/Text3D");
     if (shader) { depthText = new Material(shader) { name = "Street sign text", mainTexture = t.font.material.mainTexture }; depthFont = t.font; }
    }
    if (depthText) r.sharedMaterial = depthText;
   }
   StartCoroutine(Fit(s));
  }

  // The text's own size is only known once it has been drawn: wait a frame, then shrink it to the blade.
  System.Collections.IEnumerator Fit(Sign s) {
   // measured at the size it has now (a text resized this frame still has last frame's box), scaled from there
   yield return null;
   if (!s.text) yield break;
   var r = s.text.GetComponent<MeshRenderer>(); if (!r) yield break;
   var mf = s.blade ? s.blade.GetComponent<MeshFilter>() : null;
   // the label stands upright facing along a street (yaw 0/90/180/270): its world box gives width and height
   var wb = r.bounds.size; var textSize = new Vector3(Mathf.Max(wb.x, wb.z), wb.y, 0);
   Vector3 bladeSize = mf && mf.sharedMesh ? Vector3.Scale(mf.sharedMesh.bounds.size, s.blade.lossyScale) : new Vector3(Blade.x, Blade.y, .04f);
   float now = s.text.characterSize;
   float k = textSize.x < 1e-4f || textSize.y < 1e-4f ? now / s.size : Mathf.Min(1f, now / s.size * Mathf.Min(bladeSize.x * .86f / textSize.x, bladeSize.y * .68f / textSize.y));
   if (Report.Count > 40) Report.RemoveAt(0);
   Report.Add($"{s.text.text}: text {textSize.x:0.00}x{textSize.y:0.00} blade {bladeSize.x:0.00}x{bladeSize.y:0.00} k {k:0.00} mat {(r.sharedMaterial ? r.sharedMaterial.name : "-")}");
   s.text.characterSize = s.size * k;
   if (!s.blade) yield break;
   // on the blade's face, a hair in front of it, centred on it
   var face = s.blade.InverseTransformPoint(s.text.transform.position);
   face.x = 0; face.y = 0;
   s.text.transform.position = s.blade.TransformPoint(face);
  }
 }
}
