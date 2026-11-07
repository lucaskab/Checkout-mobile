using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
using Firebase;
using Firebase.Analytics;
using Firebase.Crashlytics;
using Firebase.Extensions;
using Firebase.Messaging;
#endif
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR && CHECKOUT_ADMOB
using GoogleMobileAds.Ump.Api;
#endif

namespace Checkout
{
    // Firebase (Lucas 06/11, launch audit: analytics and crash reports, free; push notifications), project
    // "Checkout Game" (checkout-game, the same Google Cloud project as the Google sign-in). Config files:
    // Assets/Firebase/google-services.json and GoogleService-Info.plist; packages 13.17.1 in GooglePackages/.
    //  - Crashlytics: crashes and uncaught exceptions on phones.
    //  - Analytics: Firebase's own events (first_open, session_start, in_app_purchase...) plus the game's: level_up,
    //    stage_reached, expansion_unlocked, tutorial steps, diamonds earned/spent, rewarded videos. They come from the
    //    snapshots (CheckoutBridge.Received): the game logic stays the only authority.
    //  - Messaging: started only after the notification permission was asked (CheckoutNotifications), because on the
    //    iPhone starting it asks for the permission at once. The device token is kept for the server (Token).
    // Only on phones; the Editor and the PC build log the events (CHECKOUT_ANALYTICS) and do nothing else.
    // Consent (07/11, privacy policy review): Analytics starts with analytics storage DENIED (Firebase consent mode:
    // no analytics identifiers kept). It is granted only once Google's consent check (UMP, the same one the ads use)
    // says this player is outside the regions that need consent (EEA, UK, Switzerland). Ads storage, ad user data and
    // ad personalization stay denied everywhere: the game never uses Analytics for advertising. Crashlytics is not
    // gated (crash reports only, needed to keep the game working).
    public sealed class CheckoutFirebase : MonoBehaviour
    {
        public static bool Ready { get; private set; }
        /// <summary>The push token of this device (empty until Firebase Messaging gives one).</summary>
        public static string Token => PlayerPrefs.GetString("fcm.token", "");
        public static event Action<string> TokenChanged;

        static CheckoutFirebase current;
        bool messaging, consentSet;
        float nextLook;

        // What the last snapshot said (the events are the differences).
        bool seen; int level, eraIndex = -1; double diamonds; readonly HashSet<string> expansions = new HashSet<string>();
        string coach = ""; bool coachStarted; CheckoutDesktopHUD hud;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (current) return;
            current = new GameObject("CheckoutFirebase").AddComponent<CheckoutFirebase>();
            DontDestroyOnLoad(current.gameObject);
        }

        void Start()
        {
            CheckoutBridge.Received += OnSnapshot;
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            FirebaseApp.CheckAndFixDependenciesAsync().ContinueWithOnMainThread(task =>
            {
                if (task.Result != DependencyStatus.Available) { Debug.LogWarning("CHECKOUT_FIREBASE not available: " + task.Result); return; }
                _ = FirebaseApp.DefaultInstance;
                Crashlytics.ReportUncaughtExceptionsAsFatal = true;
                SetConsent(false);
                FirebaseAnalytics.SetAnalyticsCollectionEnabled(true);
                Ready = true;
                Debug.Log("CHECKOUT_FIREBASE ready");
            });
#endif
        }

        void OnDestroy() { CheckoutBridge.Received -= OnSnapshot; }

        /// <summary>Grants analytics storage once UMP knows consent is not required here (see the note above).</summary>
        void LookAtConsent()
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR && CHECKOUT_ADMOB
            var status = ConsentInformation.ConsentStatus;
            if (status == ConsentStatus.Unknown) return;       // CheckoutAds has not refreshed the consent info yet
            consentSet = true;
            if (status == ConsentStatus.NotRequired) SetConsent(true);
#elif (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            consentSet = true;                                  // no consent SDK in this build: stay denied
#else
            consentSet = true;
#endif
        }

        static void SetConsent(bool analytics)
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            FirebaseAnalytics.SetConsent(new Dictionary<ConsentType, Firebase.Analytics.ConsentStatus>
            {
                { ConsentType.AnalyticsStorage, analytics ? Firebase.Analytics.ConsentStatus.Granted : Firebase.Analytics.ConsentStatus.Denied },
                { ConsentType.AdStorage, Firebase.Analytics.ConsentStatus.Denied },
                { ConsentType.AdUserData, Firebase.Analytics.ConsentStatus.Denied },
                { ConsentType.AdPersonalization, Firebase.Analytics.ConsentStatus.Denied },
            });
            Debug.Log("CHECKOUT_FIREBASE consent analytics=" + analytics);
#endif
        }

        void Update()
        {
            if (Time.unscaledTime < nextLook) return;
            nextLook = Time.unscaledTime + 1f;
            if (Ready && !consentSet) LookAtConsent();
            // Messaging once the notification permission has been asked (never before: it would ask on its own).
            if (Ready && !messaging && PlayerPrefs.GetInt("notif.asked", 0) == 1) StartMessaging();
            // Push: the server learns this phone's token, language and the push kinds left on (Opções › Avisos).
            if (!registering) { var sig = PushSignature(); if (sig != null && sig != PlayerPrefs.GetString("push.sent", "")) StartCoroutine(Register(sig)); }
            // Tutorial: the coach card's key.
            if (!hud) hud = FindAnyObjectByType<CheckoutDesktopHUD>();
            var key = hud ? hud.CoachKey : "";
            if (key != coach)
            {
                if (!string.IsNullOrEmpty(key))
                {
                    if (!coachStarted && PlayerPrefs.GetInt("analytics.tutorial", 0) == 0) { coachStarted = true; Log("tutorial_begin"); }
                    Log("tutorial_step", ("step", key));
                }
                else if (!string.IsNullOrEmpty(coach) && coach == "objetivo" && PlayerPrefs.GetInt("analytics.tutorial", 0) == 0)
                {
                    PlayerPrefs.SetInt("analytics.tutorial", 1); Log("tutorial_complete");
                }
                coach = key;
            }
        }

        void StartMessaging()
        {
            messaging = true;
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            FirebaseMessaging.TokenReceived += (_, e) => SetToken(e.Token);
            FirebaseMessaging.MessageReceived += (_, e) => Debug.Log("CHECKOUT_FIREBASE message " + e.Message?.MessageId);
            FirebaseMessaging.GetTokenAsync().ContinueWithOnMainThread(t => { if (t.IsCompletedSuccessfully) SetToken(t.Result); });
#endif
        }

        // ── Push registration (worker/src/push.ts: PUT /v1/push) ─────────────────────────────────────────────────────
        bool registering; float retryAt;
        [Serializable] class Device { public string token, platform, lang; public string[] categories; }

        /// <summary>What the server should know now (null = nothing to send: no token, not signed in, Editor/PC).</summary>
        static string PushSignature()
        {
            var cloud = CheckoutCloud.Active;
            if (string.IsNullOrEmpty(Token) || !cloud || !cloud.HasSession) return null;
            if (Application.platform != RuntimePlatform.Android && Application.platform != RuntimePlatform.IPhonePlayer) return null;
            var cats = new List<string>();
            foreach (var c in CheckoutNotifications.Categories) if (c.push && CheckoutNotifications.IsOn(c.id)) cats.Add(c.id);
            return Token + "|" + CheckoutI18n.Language + "|" + string.Join(",", cats) + "|" + cloud.SessionToken.GetHashCode();
        }

        System.Collections.IEnumerator Register(string sig)
        {
            if (Time.unscaledTime < retryAt) yield break;
            registering = true;
            var cats = new List<string>();
            foreach (var c in CheckoutNotifications.Categories) if (c.push && CheckoutNotifications.IsOn(c.id)) cats.Add(c.id);
            var body = JsonUtility.ToJson(new Device { token = Token, platform = Application.platform == RuntimePlatform.IPhonePlayer ? "ios" : "android", lang = CheckoutI18n.Language, categories = cats.ToArray() });
            using (var request = new UnityWebRequest(CheckoutCloud.ServerUrl + "/v1/push", "PUT"))
            {
                request.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(body));
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Authorization", "Bearer " + CheckoutCloud.Active.SessionToken);
                request.timeout = 40;
                yield return request.SendWebRequest();
                if (request.responseCode == 200) { PlayerPrefs.SetString("push.sent", sig); PlayerPrefs.Save(); }
                else { retryAt = Time.unscaledTime + 120f; Debug.Log("CHECKOUT_FIREBASE push registration -> " + request.responseCode); }
            }
            registering = false;
        }

        static void SetToken(string token)
        {
            if (string.IsNullOrEmpty(token) || token == Token) return;
            PlayerPrefs.SetString("fcm.token", token); PlayerPrefs.Save();
            TokenChanged?.Invoke(token);
        }

        void OnSnapshot(Snapshot s)
        {
            if (s == null) return;
            if (!seen)
            {
                seen = true; level = s.level; eraIndex = s.era != null ? s.era.index : -1; diamonds = s.diamonds;
                expansions.Clear(); if (s.expansions != null) foreach (var e in s.expansions) expansions.Add(e);
                Property("level", level.ToString()); if (s.era != null) Property("stage", s.era.id);
                return;
            }
            if (s.level > level)
            {
                for (int l = level + 1; l <= s.level; l++) Log("level_up", ("level", l));
                Property("level", s.level.ToString());
            }
            level = s.level;
            if (s.era != null && eraIndex >= 0 && s.era.index > eraIndex) { Log("stage_reached", ("stage", s.era.id), ("index", s.era.index)); Property("stage", s.era.id); }
            if (s.era != null) eraIndex = s.era.index;
            if (s.expansions != null) foreach (var e in s.expansions) if (expansions.Add(e)) Log("expansion_unlocked", ("expansion", e));
            double delta = s.diamonds - diamonds;
            if (Math.Abs(delta) >= 1)
            {
                if (delta > 0) Log("earn_virtual_currency", ("virtual_currency_name", "diamonds"), ("value", (long)Math.Round(delta)));
                else Log("spend_virtual_currency", ("virtual_currency_name", "diamonds"), ("value", (long)Math.Round(-delta)), ("item_name", "speed_up"));
            }
            diamonds = s.diamonds;
        }

        /// <summary>A rewarded video watched to the end (CheckoutAds).</summary>
        public static void AdWatched(string unit) => Log("ad_reward", ("unit", unit ?? ""));

        public static void Log(string name, params (string key, object value)[] args)
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            if (!Ready) return;
            var ps = new Parameter[args.Length];
            for (int i = 0; i < args.Length; i++)
            {
                var (k, v) = args[i];
                ps[i] = v is int n ? new Parameter(k, n) : v is long l ? new Parameter(k, l) : v is double d ? new Parameter(k, d) : new Parameter(k, v?.ToString() ?? "");
            }
            FirebaseAnalytics.LogEvent(name, ps);
#else
            if (CheckoutAutoTestActive) Debug.Log("CHECKOUT_ANALYTICS " + name + (args.Length > 0 ? " " + string.Join(", ", Array.ConvertAll(args, a => a.key + "=" + a.value)) : ""));
#endif
        }

        static void Property(string name, string value)
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            if (Ready) FirebaseAnalytics.SetUserProperty(name, value);
#endif
        }

#if !((UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR)
        // The Editor logs the events only in the QA runs (the day-to-day play stays quiet).
        static bool CheckoutAutoTestActive => Application.isEditor;
#endif
    }
}
