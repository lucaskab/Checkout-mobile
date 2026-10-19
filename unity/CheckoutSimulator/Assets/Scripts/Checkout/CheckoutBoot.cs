using System;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Checkout
{
    // The build starts on the tiny "Boot" scene so the Android base module stays under Google Play's 200 MB:
    // the big "Supermarket" scene ships in the install-time asset pack and is loaded from here.
    // The game's start-up hooks run once the game scene is loaded (any other scene opened in the
    // editor runs them straight away, as before).
    public static class CheckoutBoot
    {
        public const string BootScene = "Boot";
        public const string GameScene = "Supermarket";
        static bool started;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void Reset() { started = false; SceneManager.sceneLoaded -= Loaded; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void AfterFirstScene()
        {
            if (SceneManager.GetActiveScene().name != BootScene) { StartGame(); return; }
            SceneManager.sceneLoaded += Loaded;
            SceneManager.LoadSceneAsync(GameScene, LoadSceneMode.Single);
        }

        static void Loaded(Scene scene, LoadSceneMode mode)
        {
            if (scene.name != GameScene) return;
            SceneManager.sceneLoaded -= Loaded;
            StartGame();
        }

        static void StartGame()
        {
            if (started) return;
            started = true;
            Run(CheckoutI18nText.Boot);
            Run(CheckoutAudio.Boot); // background music + the volume settings
            Run(CheckoutPointer.Boot);
            Run(CheckoutEntranceDressing.Boot);
            Run(CheckoutPlazaLife.Boot);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            Run(CheckoutEventPreview.Boot);
#endif
#if UNITY_EDITOR || (UNITY_STANDALONE && !UNITY_IOS && !UNITY_ANDROID) || CHECKOUT_EMBEDDED
            Run(CheckoutDesktopHost.Boot);
#endif
            Run(CheckoutPerfProbe.Boot);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            Run(CheckoutUiQa.Auto);
#endif
            Run(CheckoutAutoTest.Boot);
        }

        // One failing hook must not stop the others (each used to be its own Unity start-up call).
        static void Run(Action hook)
        {
            try { hook(); }
            catch (Exception error) { Debug.LogException(error); }
        }
    }
}
