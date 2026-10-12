using System;
using System.Collections.Generic;
using Checkout;
using UnityEditor;
using UnityEngine;

// Checks of the diamond speed-up price and of the purchase flow on the Unity side, without a store (Lucas 12/10:
// "implement tests so this always works"). The game-logic side is tested with `bun test` (src/data/diamond-skip.test.mjs,
// src/services/diamond-economy.test.mjs, desktop/iap.test.mjs).
//
// Run: menu Checkout › QA › Test purchases and speed-ups, or in batch mode
//   Unity -batchmode -quit -projectPath unity/CheckoutSimulator -executeMethod CheckoutIapTests.RunBatch
// (exit code 1 when a check fails). Results: Console / Logs/iap_tests.txt.
public static class CheckoutIapTests
{
    [MenuItem("Checkout/QA/Test purchases and speed-ups")]
    public static void RunMenu()
    {
        var failures = Run(out var report);
        if (failures == 0) Debug.Log("CHECKOUT_IAP_TESTS_OK\n" + report);
        else Debug.LogError("CHECKOUT_IAP_TESTS_FAILED " + failures + "\n" + report);
    }

    public static void RunBatch()
    {
        var failures = Run(out _);
        EditorApplication.Exit(failures == 0 ? 0 : 1);
    }

    public static int Run(out string report)
    {
        var log = new List<string>();
        int failures = 0;
        void Check(bool ok, string what) { log.Add((ok ? "ok   " : "FAIL ") + what); if (!ok) failures++; }
        const double Min = 60_000, Hour = 60 * Min, Day = 24 * Hour;

        // ---------------------------------------------------------------- speed-up price (same as src/data/diamond-skip.ts)
        Check(CheckoutSkipPrice.Cost(0) == 0 && CheckoutSkipPrice.Cost(-5) == 0, "nothing left costs nothing");
        Check(CheckoutSkipPrice.Cost(1) == 1 && CheckoutSkipPrice.Cost(Min) == 1, "the last minute costs 1");
        Check(CheckoutSkipPrice.Cost(Hour) == 10, "1 hour costs 10");
        Check(CheckoutSkipPrice.Cost(2 * Hour) == 17, "2 hours cost 17 (the service wing)");
        Check(CheckoutSkipPrice.Cost(Day) == 150, "1 day costs 150");
        Check(CheckoutSkipPrice.Cost(7 * Day) == 700, "1 week costs 700");
        bool falls = true; int last = int.MaxValue;
        for (double left = 36 * Hour; left > 0; left -= 7 * Min) { int c = CheckoutSkipPrice.Cost(left); if (c > last) falls = false; last = c; }
        Check(falls, "the price never rises while the timer runs down");
        Check(CheckoutSkipPrice.Cost(2 * Hour) < 2 * CheckoutSkipPrice.Cost(Hour) && CheckoutSkipPrice.Cost(Day) < 24 * CheckoutSkipPrice.Cost(Hour), "long waits are cheaper per hour");

        // ---------------------------------------------------------------- purchase flow
        var sent = new List<string>(); var raw = new List<string>(); int flushes = 0;
        var answers = new Queue<Action<bool, string>>();
        var flow = new CheckoutIapFlow((action, args, answered) => { sent.Add(action + " " + args); answers.Enqueue(answered); }, raw.Add, () => flushes++);

        Check(flow.ReadCatalog("{\"kind\":\"iap-catalog\",\"products\":[{\"productId\":\"com.checkout.currency.diamonds.pouch\",\"packId\":\"diamonds-pouch\"}]}") && flow.Catalog.Count == 1, "reads the catalog from the game");
        Check(!flow.ReadCatalog("{\"kind\":\"iap-catalog\",\"products\":[{\"productId\":\"com.checkout.currency.diamonds.pouch\",\"packId\":\"diamonds-pouch\"}]}"), "the same catalog again changes nothing");

        int confirms = 0;
        flow.Pending("com.checkout.currency.diamonds.pouch", "tx-1", () => confirms++);
        Check(sent.Count == 1 && sent[0] == "grantCurrencyPack [\"com.checkout.currency.diamonds.pouch\",\"tx-1\"]", "a paid order asks the game to credit the pack");
        Check(confirms == 0, "not confirmed to the store before the game answered");
        flow.Pending("com.checkout.currency.diamonds.pouch", "tx-1", () => confirms++);
        Check(sent.Count == 1, "the same order delivered twice is credited once");
        answers.Dequeue()(true, "");
        Check(flushes == 1 && confirms == 2, "after the answer the save is written and both deliveries are confirmed");
        flow.Pending("com.checkout.currency.diamonds.pouch", "tx-1", () => confirms++);
        Check(sent.Count == 1 && confirms == 3, "an order re-delivered later is only confirmed again");

        flow.Pending("com.checkout.currency.coins.sack", "tx-2", () => confirms++);
        answers.Dequeue()(false, "already credited");
        Check(confirms == 4, "an order the game refuses (already credited) is still confirmed, so the store stops re-delivering it");

        int before = sent.Count;
        flow.Pending("com.checkout.currency.coins.sack", "tx-3", () => confirms++);
        Check(sent.Count == before + 1 && confirms == 4, "no answer from the game = no confirmation (the store re-delivers it next launch)");

        flow.ReportStatus(true, new[] { "com.checkout.currency.diamonds.pouch" }, new[] { "R$ 24,90" });
        Check(raw.Count == 1 && raw[0].Contains("\"status\":\"ready\"") && raw[0].Contains("R$ 24,90") && raw[0].StartsWith("{\"kind\":\"iap\""), "reports the store's local prices to the game");
        flow.ReportEvent("cancelled", "com.checkout.currency.diamonds.pouch");
        Check(raw[1].Contains("\"event\":\"cancelled\""), "reports a cancelled purchase");

        report = string.Join("\n", log);
        try { System.IO.Directory.CreateDirectory("Logs"); System.IO.File.WriteAllText("Logs/iap_tests.txt", (failures == 0 ? "OK" : "FAILED " + failures) + "\n" + report); } catch { }
        return failures;
    }
}
