using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Right-angle furniture ("eventsalign-quitanda.mercadinho-phone", QA copy of the save). Tester 03/11: "Essa gôndola fica
 // tooortaaaaa". For each stage:
 //  1. a save from before the fix: every piece of the stage placed in the shop, turned 15°, 35°, 47° and 200° in turn (each
 //     where it fits at that turn, as the old 5° twist allowed), shown as saved (fa_before_<stage>);
 //  2. the shop loads it with the fix: every piece must stand at 0/90/180/270, still placed (none stored, none gone), on a
 //     spot where it fits, and the squared layout must come back from the game's save (fa_after_<stage>);
 //  3. build mode: a twist of 20° only leans the piece (fa_twist_lean_<stage>), 40° clicks it a quarter round
 //     (fa_twist_snap_<stage>), letting go leaves it on a right angle, the arrows turn it a quarter, and the footprint is red
 //     where a turned piece does not fit.
 // Results: Logs/furnalign.txt (PASS / FAIL lines) and Logs/at_fa_*.png.
 public sealed partial class CheckoutAutoTest {
  static readonly float[] AskewTurns = { 15, 35, 47, 200 };

  IEnumerator FurnitureAlign(string request){
   var parts = request.Split('-');
   var stages = parts.Length > 1 && parts[1] != "phone" && parts[1] != "desk" ? parts[1].Split('.') : new[] { "quitanda", "mercadinho" };
   var report = new List<string>(); int failures = 0;
   void Line(string s) { report.Add(s); Note(s); File.WriteAllLines("Logs/furnalign.txt", report); }
   void Check(bool ok, string what) { if (!ok) failures++; Line((ok ? "PASS " : "FAIL ") + what); }
   var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
   foreach (var stage in stages) {
    int era = System.Array.IndexOf(EraIds, stage); if (era < 0) { Line("unknown stage " + stage); continue; }
    var inside = CheckoutInterior.Active; if (inside) inside.editing = false;
    // Every piece of the stage starts in the inventory (as RoomAudit), then goes in at an askew turn.
    roomEra = era; roomExtras = false; roomKeepInterior = false; crowdLayout = null; CheckoutInterior.QaKeepAskew = true;
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-align-" + stage + "\",\"action\":\"devSetMarketEra\",\"args\":[\"" + stage + "\"]}");
    yield return new WaitForSecondsRealtime(18);
    inside = CheckoutInterior.Active; if (!inside) { Line("no interior at " + stage); continue; }
    inside.editing = true; yield return new WaitForSecondsRealtime(.5f);
    var floor = inside.FloorRect;
    Line($"== {stage}: floor {floor} small={CheckoutStall.Small} waiting {string.Join(",", inside.waiting.Keys)}");
    // ---------------------------------------------------------------- 1. the old save (askew turns)
    var order = inside.waiting.Keys.Where(k => !k.StartsWith("checkout") && !k.StartsWith("kiosk")).OrderBy(k => k).ToList();
    var starts = new List<Vector3>();
    for (float z = floor.yMax - 1; z > floor.yMin + .5f; z -= 1.1f) for (float x = floor.xMin + 1; x < floor.xMax - .5f; x += 1.3f) starts.Add(new Vector3(x, CheckoutInterior.FloorHere, z));
    int n = 0;
    foreach (var id in order) {
     CheckoutInterior.Item placed = null;
     foreach (var p in starts.Skip(n * 2).Concat(starts.Take(n * 2))) {
      var it = inside.PlaceWaiting(id, p); if (it == null) break;
      // turned the old way: the askew turn where it fits at that turn (the old twist only kept a fitting spot green)
      it.rot = AskewTurns[n % AskewTurns.Length]; inside.Place(it);
      if (inside.Fits(it, it.root.position, it.rot, out _) || inside.Settle(it)) { if (Mathf.Abs(Mathf.DeltaAngle(it.rot, AskewTurns[n % AskewTurns.Length])) < .5f) { placed = it; break; } }
      inside.Unplace(it);
     }
     if (placed != null) { Line($"askew {id} rot {placed.rot:0} at ({placed.x:0.00},{placed.z:0.00})"); n++; }
     else Line($"(no askew spot for {id}: stays stored)");
    }
    var old = inside.Export();
    var askewIds = old.Where(e => !e.stored && !CheckoutInterior.OnStep(e.rot, e.outside)).Select(e => e.id).ToList();
    var placedBefore = old.Where(e => !e.stored).Select(e => e.id).ToList();
    var turnsUsed = old.Where(e => !e.stored).Select(e => Mathf.RoundToInt(e.rot)).Distinct().OrderBy(r => r).ToList();
    Check(askewIds.Count >= 4 && AskewTurns.All(t => turnsUsed.Contains((int)t)), $"{stage}: old save has askew pieces at 15/35/47/200 ({string.Join(",", turnsUsed)}; {askewIds.Count} askew of {placedBefore.Count} placed)");
    // As a save from before the fix: the snapshot carries this layout, the shop shows it as saved (QaKeepAskew).
    crowdLayout = old.Where(e => !e.stored).ToArray();
    inside.MarkPending(); inside.editing = false;
    yield return new WaitForSecondsRealtime(3);
    var f = inside.FloorRect;
    sim?.Focus(new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height) * .62f);
    yield return new WaitForSecondsRealtime(1.5f);
    yield return Shot("fa_before_" + stage);
    Check(askewIds.All(id => { var it = inside.Get(id); return it != null && !CheckoutInterior.OnStep(it.rot, false); }), $"{stage}: before the fix the shop shows them askew");
    // ---------------------------------------------------------------- 2. load with the fix
    CheckoutInterior.SquaredLog.Clear(); CheckoutInterior.QaKeepAskew = false;
    yield return new WaitForSecondsRealtime(2.5f);   // next snapshot: Apply squares them up and saves (saveInteriorLayout)
    foreach (var kv in CheckoutInterior.SquaredLog) Line($"squared {kv.Key}: {kv.Value}");
    // Stop feeding the old layout: from now on the snapshot is the game's own save.
    crowdLayout = null; roomKeepInterior = true;
    yield return new WaitForSecondsRealtime(9);       // past the pending window (8 s): what the shop shows is what the app saved
    var saved = bridge.State?.interior?.items ?? new InteriorItem[0];
    foreach (var id in placedBefore) {
     var it = inside.Get(id); var e = saved.FirstOrDefault(x => x != null && x.id == id);
     bool ok = it != null && it.root && !inside.waiting.ContainsKey(id) && CheckoutInterior.OnStep(it.rot, false) && inside.Fits(it, it.root.position, it.rot, out _)
               && e != null && !e.stored && CheckoutInterior.OnStep(e.rot, false);
     Check(ok, $"{stage}: {id} placed at a right angle and fits (shown rot {(it != null ? it.rot : -1):0}, saved rot {(e != null ? e.rot : -1):0}{(e != null && e.stored ? " STORED" : "")})");
    }
    Check(inside.items.Values.Where(i => i.root && !i.outside && !i.design).All(i => CheckoutInterior.OnStep(i.rot, false)), $"{stage}: every indoor piece at 0/90/180/270");
    bool reach = inside.Reachable(out var blocked);
    Line($"info {stage}: every piece can be walked to = {reach}{(blocked != null ? " (blocked: " + blocked.id + ")" : "")} (the test layout is not tidied for passages)");
    yield return Shot("fa_after_" + stage);
    // ---------------------------------------------------------------- 3. build mode: twist and arrows
    var target = placedBefore.Select(id => inside.Get(id)).FirstOrDefault(i => i != null && i.type == "shelf") ?? placedBefore.Select(id => inside.Get(id)).FirstOrDefault(i => i != null);
    if (target != null && CheckoutBuildMode.QaSelect(target.id)) {
     yield return new WaitForSecondsRealtime(1);
     float r0 = target.rot;
     for (int i = 0; i < 10; i++) { CheckoutBuildMode.QaTwist(2); yield return null; }   // 20° of fingers (30° with the gain)
     yield return new WaitForSecondsRealtime(.3f);
     float leanYaw = target.root.eulerAngles.y;
     Check(Mathf.Abs(Mathf.DeltaAngle(target.rot, r0)) < .01f && Mathf.Abs(Mathf.DeltaAngle(leanYaw, r0)) > 1f, $"{stage}: 20° twist leans the model ({leanYaw:0.0}) but keeps the turn {target.rot:0}");
     yield return Shot("fa_twist_lean_" + stage);
     for (int i = 0; i < 10; i++) { CheckoutBuildMode.QaTwist(2); yield return null; }   // 40° in all: past half a quarter
     yield return new WaitForSecondsRealtime(.3f);
     Check(Mathf.Abs(Mathf.DeltaAngle(target.rot, r0 + 90)) < .01f, $"{stage}: 40° twist clicks a quarter round ({r0:0} -> {target.rot:0})");
     yield return Shot("fa_twist_snap_" + stage);
     for (int i = 0; i < 4; i++) { CheckoutBuildMode.QaTwist(1.5f); yield return null; }  // a little past it, then let go
     CheckoutBuildMode.QaTwistEnd(); yield return new WaitForSecondsRealtime(.3f);
     Check(CheckoutInterior.OnStep(target.rot, false) && Mathf.Abs(Mathf.DeltaAngle(target.root.eulerAngles.y, target.rot)) < .01f, $"{stage}: let go: straight on {target.rot:0}");
     float r1 = target.rot; CheckoutBuildMode.QaTurn(1); yield return new WaitForSecondsRealtime(.3f);
     Check(Mathf.Abs(Mathf.DeltaAngle(target.rot, r1 + 90)) < .01f, $"{stage}: arrow turns a quarter ({r1:0} -> {target.rot:0})");
     // red where it does not fit: pushed into its neighbour's spot (or out against a wall) and turned
     bool fits = inside.Fits(target, target.root.position, target.rot, out var why);
     Check(CheckoutBuildMode.QaFootprintGreen == (fits && inside.Reachable(out _)), $"{stage}: footprint {(CheckoutBuildMode.QaFootprintGreen ? "green" : "red")} matches fits={fits} ({why})");
     var other = inside.items.Values.FirstOrDefault(i => i != target && i.root && !i.outside && !i.design);
     if (other != null) {
      inside.MoveTo(target, other.root.position); CheckoutBuildMode.QaShowFootprint(); yield return new WaitForSecondsRealtime(.4f);
      Check(!CheckoutBuildMode.QaFootprintGreen, $"{stage}: footprint red over {other.id}");
      yield return Shot("fa_red_" + stage);
     }
     CheckoutBuildMode.QaClose(); yield return new WaitForSecondsRealtime(1);
    } else Line($"{stage}: no piece to twist");
    roomKeepInterior = false;
   }
   roomEra = -1; roomKeepInterior = false; crowdLayout = null; CheckoutInterior.QaKeepAskew = false;
   var last = CheckoutInterior.Active; if (last) last.editing = false;
   Line(failures == 0 ? "FURNALIGN_OK" : "FURNALIGN_FAILED " + failures);
  }
 }
}
