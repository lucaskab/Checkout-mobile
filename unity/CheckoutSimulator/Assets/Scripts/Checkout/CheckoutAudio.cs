using System;
using UnityEngine;

namespace Checkout
{
    // Background music and the player's volume settings (Lucas 18/10: "o jogo tem que ter uma musiquinha"; the
    // Opções window, CheckoutSettings, changes them).
    // - Music: Resources/CheckoutDesktop/Music/music_main, looped on its own source that ignores the listener volume.
    //   It starts with the game (behind the start screen too) and survives the scene reload of "Voltar ao menu".
    // - Effects: every other AudioSource in the game (register, restock, level-up, delivery app, ...) plays through
    //   the AudioListener, so the effects volume is AudioListener.volume. New sounds follow it with no extra code.
    // Sliders are 0..1; the loudness follows the square of the slider, which feels even to the ear.
    // Saved in PlayerPrefs (per device, like the language).
    [DefaultExecutionOrder(-700)]
    public sealed class CheckoutAudio : MonoBehaviour
    {
        const string MusicKey = "checkout.audio.music", MusicOffKey = "checkout.audio.musicOff";
        const string EffectsKey = "checkout.audio.effects", EffectsOffKey = "checkout.audio.effectsOff";
        public const float DefaultMusic = .6f, DefaultEffects = 1f;
        const string MusicClip = "CheckoutDesktop/Music/music_main";

        static CheckoutAudio instance;
        static bool held; // a rewarded video is playing (CheckoutAds): the music waits
        AudioSource music;
        float start; // fades the music in on launch

        /// <summary>Any setting changed (the Opções window refreshes itself).</summary>
        public static event Action Changed;

        public static float MusicVolume
        {
            get => Mathf.Clamp01(PlayerPrefs.GetFloat(MusicKey, DefaultMusic));
            set { PlayerPrefs.SetFloat(MusicKey, Mathf.Clamp01(value)); Saved(); }
        }
        public static bool MusicOn
        {
            get => PlayerPrefs.GetInt(MusicOffKey, 0) == 0;
            set { PlayerPrefs.SetInt(MusicOffKey, value ? 0 : 1); Saved(); }
        }
        public static float EffectsVolume
        {
            get => Mathf.Clamp01(PlayerPrefs.GetFloat(EffectsKey, DefaultEffects));
            set { PlayerPrefs.SetFloat(EffectsKey, Mathf.Clamp01(value)); Saved(); }
        }
        public static bool EffectsOn
        {
            get => PlayerPrefs.GetInt(EffectsOffKey, 0) == 0;
            set { PlayerPrefs.SetInt(EffectsOffKey, value ? 0 : 1); Saved(); }
        }

        static float Loudness(float slider) => slider * slider;
        static float MusicTarget => MusicOn && !held ? Loudness(MusicVolume) : 0f;

        // Started by CheckoutBoot with the game scene (the Boot scene comes first on Android).
        internal static void Boot() => Ensure();

        static void Ensure()
        {
            if (instance) return;
            var go = new GameObject("CheckoutAudio");
            DontDestroyOnLoad(go);
            instance = go.AddComponent<CheckoutAudio>();
        }

        /// <summary>CheckoutAds: the music pauses while a rewarded video plays and comes back after it.</summary>
        public static void HoldMusic(bool hold) { held = hold; }

        static void Saved()
        {
            PlayerPrefs.Save();
            ApplyEffects();
            Changed?.Invoke();
        }

        static void ApplyEffects() => AudioListener.volume = EffectsOn ? Loudness(EffectsVolume) : 0f;

        void Awake()
        {
            music = gameObject.AddComponent<AudioSource>();
            music.playOnAwake = false; music.loop = true; music.spatialBlend = 0; music.priority = 0;
            music.ignoreListenerVolume = true; // the effects slider never touches the music
            music.bypassEffects = music.bypassListenerEffects = music.bypassReverbZones = true;
            music.clip = Resources.Load<AudioClip>(MusicClip);
            if (!music.clip) Debug.LogWarning("CHECKOUT_AUDIO music missing: Resources/" + MusicClip);
            music.volume = 0; start = Time.unscaledTime;
            ApplyEffects();
        }

        void Update()
        {
            if (!music.clip) return;
            // 2.5 s fade-in on launch; mute / unmute and the slider glide in about a quarter of a second.
            float target = MusicTarget * Mathf.Clamp01((Time.unscaledTime - start) / 2.5f);
            music.volume = Mathf.MoveTowards(music.volume, target, Time.unscaledDeltaTime * 2.5f);
            // Muted: the track pauses (no decoding) and resumes where it stopped.
            if (target > 0 && !music.isPlaying) { if (music.time > 0) music.UnPause(); else music.Play(); }
            else if (target <= 0 && music.volume <= .0001f && music.isPlaying) music.Pause();
        }

        void OnDestroy() { if (instance == this) instance = null; }
    }
}
