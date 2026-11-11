using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "feetslip[.seconds]" (Lucas 06/11: the legs walk strangely): with the shop open, every character playing a walking clip
 // is followed frame by frame: the foot that is on the ground (the lower one, at its lowest) should stay put while the
 // body moves. Per model and clip: how fast that foot slides, as a share of the body's speed (median / 90th percentile;
 // 0 = no sliding), and the walk cycle CheckoutWalkCycle measured. Pictures: Logs/feet_<n>_<frame>.jpg, a few frames of
 // a walking shopper close up.
 public sealed partial class CheckoutAutoTest {
  IEnumerator FeetSlip(string request) {
   var args = request.Split('.');
   float seconds = args.Length > 1 && float.TryParse(args[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var s) && s > 0 ? s : 45;
   void Hud(string action, string json) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-" + action + "\",\"action\":\"" + action + "\",\"args\":" + json + "}");
   if (bridge.State != null && !bridge.State.isOpen) { Hud("setMarketOpen", "[true]"); yield return new WaitForSecondsRealtime(3); }
   var feet = new Dictionary<Animation, (Transform l, Transform r, string model)>();
   var last = new Dictionary<Animation, (Vector3 body, Vector3 foot, bool left, float low)>();
   var ratios = new Dictionary<string, List<float>>(); var cycles = new Dictionary<string, float>();
   float end = Time.realtimeSinceStartup + seconds, nextShot = Time.realtimeSinceStartup + 6; int shots = 0;
   while (Time.realtimeSinceStartup < end) {
    yield return new WaitForEndOfFrame();
    float dt = Time.deltaTime; if (dt <= 0) continue;
    foreach (var anim in FindObjectsByType<Animation>(FindObjectsSortMode.None)) {
     if (!anim.isActiveAndEnabled) continue;
     if (!feet.TryGetValue(anim, out var f)) {
      Transform l = null, r = null;
      foreach (var t in anim.GetComponentsInChildren<Transform>()) { if (t.name == "Foot_L") l = t; else if (t.name == "Foot_R") r = t; }
      var body = anim.GetComponentsInChildren<SkinnedMeshRenderer>().FirstOrDefault(m => !m.name.EndsWith("_Prop") && m.sharedMesh);
      feet[anim] = f = (l, r, body ? body.sharedMesh.name : anim.name);
     }
     if (!f.l || !f.r) continue;
     string clip = null;
     foreach (AnimationState st in anim) if (st.enabled && st.weight > .9f && st.name.EndsWith("Walking") || st.enabled && st.weight > .9f && st.name == "WalkingWithBasket") clip = st.name;
     if (clip == null) { last.Remove(anim); continue; }
     float scale = Mathf.Abs(anim.transform.lossyScale.y);
     bool left = f.l.position.y <= f.r.position.y;
     var foot = left ? f.l.position : f.r.position; var pos = anim.transform.position;
     float h = foot.y - pos.y, low = h;
     if (last.TryGetValue(anim, out var p)) {
      low = Mathf.Min(p.low + .02f * dt * scale, h);
      var moved = pos - p.body; moved.y = 0; float bodyV = moved.magnitude / dt;
      if (p.left == left && bodyV > .35f && h < low + .012f * scale) {
       var slid = foot - p.foot; slid.y = 0;
       string key = f.model + " / " + clip;
       if (!ratios.TryGetValue(key, out var list)) ratios[key] = list = new List<float>();
       list.Add(slid.magnitude / dt / bodyV);
       cycles[key] = CheckoutWalkCycle.World(anim, clip, 0);
      }
     }
     last[anim] = (pos, foot, left, low);
    }
    if (Time.realtimeSinceStartup > nextShot && shots < 3) {
     var walker = last.Keys.FirstOrDefault(a => a && feet[a].model.StartsWith("Customer") && a.transform.position.sqrMagnitude < 900);
     if (walker) {
      shots++;
      for (int k = 0; k < 6; k++) { CaptureAt(walker.transform.position + Vector3.up * .9f, 3.2f, $"feet_{shots}_{k}"); yield return new WaitForSeconds(.12f); }
     }
     nextShot = Time.realtimeSinceStartup + 9;
    }
   }
   foreach (var kv in ratios.OrderBy(k => k.Key)) {
    var v = kv.Value; v.Sort();
    Note($"FEET {kv.Key}: n={v.Count} slip median={v[v.Count / 2]:0.00} p90={v[(int)(v.Count * .9f)]:0.00} cycle={cycles[kv.Key]:0.00}m");
   }
   Note("feetslip done");
  }

  // "umbrellaprobe": who holds the umbrella how (bones the rig bound vs the live skeleton), a few frames apart.
  IEnumerator UmbrellaProbe(string request) {
   if (!bridge.State.isOpen) CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");
   var fx = FindAnyObjectByType<CheckoutEventVisuals>(); if (!fx) yield break;
   fx.Preview("chuva-forte"); yield return new WaitForSecondsRealtime(6);
   var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
   string Path(Transform t) { var p = t ? t.name : "null"; for (var x = t ? t.parent : null; x && x.GetComponent<MarketDay.MarketRainUmbrellaRig>() == null; x = x.parent) p = x.name + "/" + p; return p; }
   foreach (var rig in FindObjectsByType<MarketDay.MarketRainUmbrellaRig>(FindObjectsSortMode.None).Where(r => r.HasVisibleUmbrella).Take(4)) {
    var t = typeof(MarketDay.MarketRainUmbrellaRig);
    var anim = (Animation)t.GetField("animationPlayer", flags).GetValue(rig);
    var hand = (Transform)t.GetField("hand", flags).GetValue(rig); var upper = (Transform)t.GetField("upperArm", flags).GetValue(rig);
    float w = (float)t.GetField("shelterWeight", flags).GetValue(rig);
    float slide = (float)t.GetField("slide", flags).GetValue(rig); var pts = (Vector3[])t.GetField("headPoints", flags).GetValue(rig);
    var headB = (Transform)t.GetField("head", flags).GetValue(rig); var um = rig.Umbrella;
    float hairTop = float.MinValue; if (pts != null && headB) foreach (var q in pts) hairTop = Mathf.Max(hairTop, headB.TransformPoint(q).y);
    Note($"UPROBE2 {rig.name}: slide {slide:0.00} headPoints {(pts == null ? -1 : pts.Length)} hairTop {hairTop:0.00} grip y {(um ? um.transform.position.y : 0):0.00} hand y {(hand ? hand.position.y : 0):0.00} scale {(um ? um.transform.lossyScale.y : 0):0.00} head {(headB ? headB.name + " " + headB.position.y.ToString("0.00") + " s" + headB.lossyScale.y.ToString("0.0") : "null")}");
    var mca = rig.GetComponent<MarketDay.MarketCharacterAnimator>();
    yield return new WaitForEndOfFrame();
    Note($"UPROBE {rig.name}: weight {w:0.00} anim {Path(anim ? anim.transform : null)} (mca {(mca && mca.animationPlayer == anim ? "same" : "OTHER " + Path(mca && mca.animationPlayer ? mca.animationPlayer.transform : null))}) hand {Path(hand)} active {(hand ? hand.gameObject.activeInHierarchy : false)} hand-shoulder y {(hand && upper ? hand.position.y - upper.position.y : 0):0.00} upright {rig.ForearmIsUpright} rigs on body {rig.GetComponents<MarketDay.MarketRainUmbrellaRig>().Length} shopperRig {(rig.GetComponent<CheckoutShopperRig>() ? "yes" : "no")} anim enabled {(anim ? anim.enabled : false)}");
   }
  }
 }
}
