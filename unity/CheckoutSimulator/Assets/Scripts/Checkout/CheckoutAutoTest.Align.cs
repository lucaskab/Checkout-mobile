using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Straight furniture ("eventsangle-here.quitanda-phone", QA copy of the save). Tester 03/11: "Essa gôndola fica
 // tooortaaaaa"; Lucas: pieces turned only with the ±45° arrows still look off against the walls.
 //  1. the saved layout of the QA copy: every piece's saved turn, its root's yaw on screen and how straight its outline
 //     measures where it stands (Logs/furnangle_layout.txt);
 //  2. every kit and tier model stood against the back wall at 0° and 90° (the other pieces hidden): root yaw, the most
 //     turned child, and the angle of the outline of everything it draws (seen from above) against the walls
 //     (Logs/furnangle.txt / furnangle.csv), top-down shots of the shop furniture (Logs/fa_top_*.jpg) and game-camera shots
 //     of the navy glass-top counter (dairy_T1) at 0°, 45° and 90° (Logs/fa_cam_*.jpg).
 public sealed partial class CheckoutAutoTest {
  IEnumerator FurnitureAngles(string request){
   var parts = request.Split('-');
   var stages = parts.Length > 1 && parts[1] != "phone" && parts[1] != "desk" ? parts[1].Split('.') : new[] { "here", "quitanda" };
   var table = new List<string> { "stage,template,rot,rootYaw,worstChild,worstChildYaw,outlineAngle,outlineSaving,vertices,drawnW,drawnD,footW,footD" };
   var report = new List<string>();
   void Line(string s) { report.Add(s); Note(s); File.WriteAllLines("Logs/furnangle.txt", report); File.WriteAllLines("Logs/furnangle.csv", table); }
   // ---------------------------------------------------------------- 1. the QA copy's own layout
   {
    var inside = CheckoutInterior.Active; var lines = new List<string>();
    var saved = bridge.State?.interior?.items ?? new InteriorItem[0];
    lines.Add($"stage {bridge.State?.era?.id} saved pieces {saved.Length}");
    foreach (var e in saved.Where(e => e != null)) {
     var it = inside ? inside.Get(e.id) : null; string seen = "";
     if (it != null) { var m = inside.QaMeasure(it); seen = $" shown: it.rot {it.rot:0.##} root yaw {it.root.eulerAngles.y:0.##} outline {m.outlineAngle:0.0} (saving {m.outlineSaving:0.000}) template {it.template}"; }
     lines.Add($"{e.id} {e.type} saved rot {e.rot:0.##}{(e.stored ? " stored" : "")}{(e.outside ? " outside" : "")} {(e.stored ? "" : Mathf.Abs(e.rot % 45) > .01f ? "NOT A 45 STEP" : Mathf.Abs(e.rot % 90) > .01f ? "diagonal" : "right angle")}{seen}");
    }
    File.WriteAllLines("Logs/furnangle_layout.txt", lines); Note("layout: " + lines.Count + " lines");
   }
   foreach (var stage in stages) {
    if (stage != "here") {
     int era = System.Array.IndexOf(EraIds, stage); if (era < 0) { Line("unknown stage " + stage); continue; }
     var was = CheckoutInterior.Active; if (was) was.editing = false;
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-angle-" + stage + "\",\"action\":\"devSetMarketEra\",\"args\":[\"" + stage + "\"]}");
     yield return new WaitForSecondsRealtime(18);
    }
    var inside = CheckoutInterior.Active; if (!inside) { Line("no interior at " + stage); continue; }
    inside.editing = true; yield return new WaitForSecondsRealtime(.5f);
    var floor = inside.FloorRect; float y = CheckoutInterior.FloorHere;
    Line($"== {stage} ({bridge.State?.era?.id}): floor {floor} small={CheckoutStall.Small}");
    // Everything else steps aside (hidden) so the shots show one piece against the wall.
    var hidden = inside.items.Values.Where(i => i.root && i.root.gameObject.activeSelf).Select(i => i.root.gameObject).ToList();
    foreach (var go in hidden) go.SetActive(false);
    var templates = inside.Templates.Concat(Resources.LoadAll<GameObject>("CheckoutFixtureTiers").Select(g => g.name)).Distinct().OrderBy(n => n).ToList();
    bool Furniture(string n) => n.StartsWith("shelf") || n.StartsWith("sector") || n.StartsWith("checkout") || n == "kiosk" || n == "bread-basket"
      || n.StartsWith("dairy") || n.StartsWith("drinks") || n.StartsWith("produce") || n.StartsWith("bakery") || n.StartsWith("freezer") || n.StartsWith("icecream");
    foreach (var name in templates) {
     foreach (var rot in new[] { 0f, 90f }) {
      var it = inside.QaSpawn(name, new Vector3(floor.center.x, y, floor.center.y), rot);
      if (it == null) { Line($"{name}: could not build"); break; }
      // back against the back wall, centred
      var f = inside.FootprintAt(it, it.root.position, rot);
      float ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
      var pos = it.root.position + new Vector3(floor.center.x - f.c.x, 0, floor.yMax - ez - f.c.y);
      inside.MoveTo(it, pos);
      yield return null; yield return new WaitForSecondsRealtime(.25f);   // the "life" motions have run
      var m = inside.QaMeasure(it);
      table.Add($"{stage},{name},{rot:0},{m.rootYaw:0.00},{m.worstChild},{m.worstChildYaw:0.00},{m.outlineAngle:0.00},{m.outlineSaving:0.000},{m.vertices},{m.drawn.width:0.000},{m.drawn.height:0.000},{m.footprint.width:0.000},{m.footprint.height:0.000}");
      bool odd = Mathf.Abs(CheckoutInterior.AxisOffset(m.rootYaw - rot)) > .05f || Mathf.Abs(m.worstChildYaw) > .5f || (Mathf.Abs(m.outlineAngle) > 1f && m.outlineSaving > .02f);
      Line($"{(odd ? "CHECK " : "ok    ")}{name} rot {rot:0}: root {m.rootYaw:0.00}, worst child {m.worstChild} {m.worstChildYaw:0.00}, outline {m.outlineAngle:0.00} deg (min-rect saves {m.outlineSaving * 100:0.0}%), drawn {m.drawn.width:0.00}x{m.drawn.height:0.00} vs footprint {m.footprint.width:0.00}x{m.footprint.height:0.00}");
      if (Furniture(name) && (stage == stages[0] || name.StartsWith("dairy") || odd)) {
       var c = it.root.position; float size = Mathf.Max(m.footprint.width, m.footprint.height) + 2.4f;
       TopDown(new Vector3(c.x, 0, c.z + .4f), size, $"fa_top_{stage}_{name}_{rot:0}");
      }
      if (name == "dairy_T1" && rot == 0) {
       foreach (var r in new[] { 0f, 45f, 90f }) {
        it.rot = r; inside.Place(it); yield return null;
        CaptureAt(it.root.position + Vector3.up * .8f, 5, $"fa_cam_{stage}_{name}_{r:0}");
       }
      }
      inside.QaDespawn(it);
     }
    }
    foreach (var go in hidden) if (go) go.SetActive(true);
    inside.editing = false;
    yield return new WaitForSecondsRealtime(1);
   }
   Line("FURNANGLE_DONE");
  }
 }
}
