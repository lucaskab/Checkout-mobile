using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // The new ceiling decorations in the real shop (Lucas 05/11: "me mostra no jogo real, no mercado real, com as coisas
 // lá"). On the QA copy of the save ("eventsdeco[-phone]"): the supermarket and the hypermarket laid out with their
 // shelves like a tidy player would (ShowTier), the day open with shoppers, then pictures:
 //  Logs/fd_<stage>_game.jpg  the game's own screen (HUD included) at the home zoom,
 //  Logs/fd_<stage>_wide.jpg  the whole shop from the game's camera, no HUD,
 //  Logs/fd_<stage>_close.jpg a closer look at the middle of the shop.
 // RESULT lines count the garland spans and lamps that replaced the old primitives.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Deco(string request) {
   if (request.EndsWith("-phone")) Note("deco: " + CheckoutQaGameView.Set(2778, 1284));
   if (!CheckoutStartMenu.QaMode) { Note("deco: not on the QA copy, stopping"); yield break; }
   foreach (var f in Directory.GetFiles("Logs", "fd_*.jpg")) File.Delete(f);
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   CheckoutBridge.TestPatch = s => { Patch(s); PatchTiers(s); };
   Hud("skipOnboarding", "[]"); Hud("claimDayResult", "[]"); TierLang("pt"); yield return Wait(1.5f);
   var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
   foreach (var stage in new[] { "supermercado", "hipermercado" }) {
    int era = System.Array.IndexOf(EraIds, stage);
    tierOpen = true;
    yield return ShowTier(stage, era, 4, null);
    Hud("dismissLevelUp", "[]"); if (hud) { hud.QaReleaseCelebrations(); for (int i = 0; i < 4 && hud.CoachQa().isTip; i++) { Hud("dismissOnboardingTip", "[]"); yield return Wait(.4f); } }
    Hud("startDay", "[\"livre\"]");
    yield return Wait(9f);   // shoppers walk in
    var dressing = GameObject.Find("Supermarket World/Market Stage Dressing");
    int spans = 0, lamps = 0, oldOn = 0;
    if (dressing) foreach (Transform item in dressing.transform) {
     if (!item.gameObject.activeInHierarchy) continue;
     if (!item.name.StartsWith("Bunting") && !item.name.StartsWith("Pendant")) continue;
     var holder = item.Find("Ceiling deco");
     if (holder) foreach (Transform c in holder) if (c.gameObject.activeSelf) { if (item.name.StartsWith("Bunting")) spans++; else lamps++; }
     foreach (Transform c in item) if (c.name != "Ceiling deco" && c.gameObject.activeSelf) oldOn++;
    }
    Note($"RESULT deco {stage}: {(spans > 0 && oldOn == 0 ? "PASS" : "FAIL")} {spans} garland spans, {lamps} lamps, {oldOn} old pieces still on");
    var inside = CheckoutInterior.Active; var floor = inside ? inside.FloorRect : new Rect(-9, -8, 18, 15);
    var mid = new Vector3(floor.center.x, CheckoutInterior.FloorHere, floor.center.y);
    if (sim) sim.HomeCamera(); yield return Wait(1.5f);
    if (hud) for (int i = 0; i < 4 && hud.CoachQa().isTip; i++) { Hud("dismissOnboardingTip", "[]"); yield return Wait(.4f); }
    yield return new WaitForEndOfFrame();
    File.WriteAllBytes($"Logs/fd_{stage}_game.jpg", RecJpg(2778, 86));
    CaptureSized($"fd_{stage}_wide", 2400, 1350, mid, Mathf.Max(floor.width, floor.height) * 1.08f + 1);
    CaptureSized($"fd_{stage}_close", 2400, 1350, mid + new Vector3(-floor.width * .12f, 0, floor.height * .05f), 11f);
    Note($"deco shots {stage}");
   }
   tierPatching = false; tierOpen = false; CheckoutBridge.TestPatch = null;
   yield return Wait(1f);
  }
 }
}
