using System.Collections.Generic;
using Checkout;
using UnityEditor;
using UnityEngine;

// Checks of the furniture turn steps (tester 03/11: "Essa gôndola fica tooortaaaaa"): inside the shop pieces stand at
// 0/90/180/270 only, on the city block at 45° steps; a two-finger twist lands on the nearest step. The whole save
// migration (a layout saved at 15°/35°/47°/200° loading squared up, every piece still placed) runs in play mode:
// autotest "eventsalign-quitanda.mercadinho-phone" (CheckoutAutoTest.Align.cs, Logs/furnalign.txt).
//
// Run: menu Checkout › QA › Test furniture right angles (results in the Console and Logs/furniture_align_tests.txt).
public static class CheckoutFurnitureAlignTests
{
    [MenuItem("Checkout/QA/Test furniture right angles")]
    public static void RunMenu()
    {
        var failures = Run(out var report);
        System.IO.File.WriteAllText("Logs/furniture_align_tests.txt", report + (failures == 0 ? "\nOK" : "\nFAILED " + failures));
        if (failures == 0) Debug.Log("CHECKOUT_ALIGN_TESTS_OK\n" + report);
        else Debug.LogError("CHECKOUT_ALIGN_TESTS_FAILED " + failures + "\n" + report);
    }

    public static void RunBatch() { var failures = Run(out _); EditorApplication.Exit(failures == 0 ? 0 : 1); }

    public static int Run(out string report)
    {
        var log = new List<string>(); int failures = 0;
        void Check(bool ok, string what) { log.Add((ok ? "ok   " : "FAIL ") + what); if (!ok) failures++; }
        bool Same(float a, float b) => Mathf.Abs(Mathf.DeltaAngle(a, b)) < .001f;

        // ---------------------------------------------------------------- indoors: right angles
        Check(Same(CheckoutInterior.SnapTurn(15, false), 0), "inside 15° -> 0°");
        Check(Same(CheckoutInterior.SnapTurn(35, false), 0), "inside 35° -> 0°");
        Check(Same(CheckoutInterior.SnapTurn(47, false), 90), "inside 47° -> 90°");
        Check(Same(CheckoutInterior.SnapTurn(200, false), 180), "inside 200° -> 180°");
        Check(Same(CheckoutInterior.SnapTurn(-15, false), 0), "inside -15° -> 0°");
        Check(Same(CheckoutInterior.SnapTurn(275, false), 270), "inside 275° -> 270°");
        Check(Same(CheckoutInterior.SnapTurn(355, false), 0) && CheckoutInterior.SnapTurn(355, false) >= 0 && CheckoutInterior.SnapTurn(355, false) < 360, "inside 355° -> 0° (kept in 0..360)");
        for (float a = -720; a <= 720; a += 2.5f)
        {
            float r = CheckoutInterior.SnapTurn(a, false);
            if (!(Mathf.Abs(r % 90) < .001f && r >= 0 && r < 360 && Mathf.Abs(Mathf.DeltaAngle(a, r)) <= 45.001f)) { Check(false, $"inside {a}° -> {r}° is not the nearest right angle"); break; }
        }
        Check(true, "inside: every turn from -720° to 720° lands on the nearest of 0/90/180/270");
        Check(CheckoutInterior.OnStep(90, false) && CheckoutInterior.OnStep(0, false) && CheckoutInterior.OnStep(270.004f, false), "0/90/270 are right angles");
        Check(!CheckoutInterior.OnStep(45, false) && !CheckoutInterior.OnStep(15, false) && !CheckoutInterior.OnStep(200, false), "45/15/200 are not right angles indoors");
        Check(CheckoutInterior.TurnStep(false) == 90, "the arrows turn a quarter indoors");

        // ---------------------------------------------------------------- outdoors (city block): 45° steps
        Check(Same(CheckoutInterior.SnapTurn(15, true), 0), "outside 15° -> 0°");
        Check(Same(CheckoutInterior.SnapTurn(35, true), 45), "outside 35° -> 45°");
        Check(Same(CheckoutInterior.SnapTurn(200, true), 180), "outside 200° -> 180°");
        Check(CheckoutInterior.OnStep(45, true) && CheckoutInterior.OnStep(135, true), "45/135 are fine on the block");
        Check(CheckoutInterior.TurnStep(true) == 45, "the arrows turn an eighth on the block");

        // ---------------------------------------------------------------- the twist lands on the nearest step
        Check(Same(CheckoutBuildMode.TwistTarget(0 + 30, false), 0), "a 30° twist (20° of fingers) keeps the quarter");
        Check(Same(CheckoutBuildMode.TwistTarget(0 + 60, false), 90), "a 60° twist (40° of fingers) clicks to the next quarter");
        Check(Same(CheckoutBuildMode.TwistTarget(90 - 70, false), 0), "twisting back 70° from 90° lands on 0°");
        Check(Same(CheckoutBuildMode.TwistTarget(180 + 140, false), 0), "a 140° twist from 180° (320°) lands on 0°");
        Check(Same(CheckoutBuildMode.TwistTarget(25, true), 45), "outside a 25° twist clicks to 45°");

        report = string.Join("\n", log);
        return failures;
    }
}
