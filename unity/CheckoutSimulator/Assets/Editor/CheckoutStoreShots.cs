using System.IO;
using UnityEditor;

// App Store screenshots (23/10): plays a showcase market on the QA copy of the save (the player's own save is never
// touched): no tutorial card, no Dev tab, the chosen stage built, then the phone UI capture (CheckoutUiQa) saves every
// HUD page and game window at the Game view resolution to Logs/ui_qa/*.jpg. Set the Game view to the store size first
// (iPhone 6.5": 2778x1284; iPad 13": 2732x2048). The flag file Logs/store_shots.txt holds the stage and is removed at
// the end.
public static class CheckoutStoreShots
{
    static void Run(string stage)
    {
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/store_shots.txt", stage);
        if (!EditorApplication.isPlaying) EditorApplication.isPlaying = true;
    }

    [MenuItem("Checkout/iPhone/Store screenshots - Supermarket")]
    static void Supermarket() => Run("supermercado");

    [MenuItem("Checkout/iPhone/Store screenshots - Mini market")]
    static void MiniMarket() => Run("quitanda");

    [MenuItem("Checkout/iPhone/Store screenshots - Supermarket", true)]
    [MenuItem("Checkout/iPhone/Store screenshots - Mini market", true)]
    static bool CanRun() => !EditorApplication.isPlaying;
}
