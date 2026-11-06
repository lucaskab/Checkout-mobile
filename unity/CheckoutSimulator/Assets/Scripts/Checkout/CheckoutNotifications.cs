using System;
using System.Collections.Generic;
using UnityEngine;
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
using Unity.Notifications;
#endif

namespace Checkout
{
    // Phone notifications (Lucas 06/11, launch audit: "Notificações locais... quando uma construção terminou... Um menu
    // nas settings para o usuário conseguir controlar quais notificações ele quer").
    //  - Local: when the game goes to the background, the timers of the last snapshot become notifications (a build,
    //    an evolution, the expansion works, production, a delivery, a fleet truck back home, tomorrow's gift, the market
    //    that stopped selling at the 12 h offline cap). Back in the game, every pending one is cancelled: the game
    //    shows the rest itself.
    //  - Push (Firebase Cloud Messaging, CheckoutFirebase): friends/league and events, sent by the server; the
    //    categories here are the player's choice, sent along with the device token.
    //  - Opções › Avisos (CheckoutSettings) turns each category on or off (PlayerPrefs "notif.<id>", on by default).
    // The system permission is asked once, the first time a timer worth a notification is running (iOS / Android 13+),
    // not on the first launch. In the Editor the schedule is only written to the log (CHECKOUT_NOTIF) for QA.
    public sealed class CheckoutNotifications : MonoBehaviour
    {
        public sealed class Category { public string id, label, icon; public bool push; }

        /// <summary>The categories of Opções › Avisos, in order.</summary>
        public static readonly Category[] Categories =
        {
            new Category { id = "obras", label = "Obras e produção", icon = "Icons/construction" },
            new Category { id = "entregas", label = "Entregas e caminhões", icon = "Icons/delivery-truck" },
            new Category { id = "presente", label = "Presente diário", icon = "Icons/gift" },
            new Category { id = "mercado", label = "Mercado parado", icon = "Icons/market" },
            new Category { id = "amigos", label = "Amigos e liga", icon = "Icons/friends", push = true },
            new Category { id = "eventos", label = "Eventos e novidades", icon = "Icons/festival", push = true },
        };

        public static event Action Changed;

        public static bool IsOn(string id) => PlayerPrefs.GetInt("notif." + id, 1) == 1;
        public static void Set(string id, bool on) { PlayerPrefs.SetInt("notif." + id, on ? 1 : 0); PlayerPrefs.Save(); Changed?.Invoke(); }

        /// <summary>"granted", "denied", "pending" or "unknown" (not asked yet / Editor).</summary>
        public static string Permission
        {
            get
            {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
                if (!started) return "unknown";
                switch (NotificationCenter.PermissionStatus)
                {
                    case NotificationsPermissionStatus.Granted: return "granted";
                    case NotificationsPermissionStatus.Denied: return "denied";
                    case NotificationsPermissionStatus.RequestPending: return "pending";
                    default: return "unknown";
                }
#else
                return "unknown";
#endif
            }
        }

        // The game's offline cap (src/data/economy.ts OFFLINE_CAP_MS): an open market sells while away up to this.
        const double OfflineCapMs = 12 * 3600_000d;
        // Timers that end sooner than this are not worth a notification (the player is likely still around).
        const double MinLeadMs = 90_000;
        // Ends closer than this are one notification ("3 obras ficaram prontas").
        const double MergeMs = 120_000;
        const int MaxScheduled = 24;
        const string AskedKey = "notif.asked";

        static CheckoutNotifications current;
        static bool started;
        CheckoutBridge bridge;
        float nextLook;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (current) return;
            current = new GameObject("CheckoutNotifications").AddComponent<CheckoutNotifications>();
            DontDestroyOnLoad(current.gameObject);
        }

        void Start()
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            NotificationCenter.Initialize(new NotificationCenterArgs
            {
                AndroidChannelId = "checkout",
                AndroidChannelName = "Checkout",
                AndroidChannelDescription = CheckoutI18n.T("Avisos do seu mercado"),
                PresentationOptions = NotificationPresentation.Alert | NotificationPresentation.Badge | NotificationPresentation.Sound,
            });
            started = true;
#endif
            ClearPending();
        }

        void Update()
        {
            // Ask for the permission the first time a long timer runs (a build, the expansion works...), once.
            if (Time.unscaledTime < nextLook) return;
            nextLook = Time.unscaledTime + 2f;
            if (PlayerPrefs.GetInt(AskedKey, 0) == 1) return;
            if (!bridge) bridge = FindAnyObjectByType<CheckoutBridge>();
            var state = bridge ? bridge.State : null;
            if (state == null || !HasLongTimer(state)) return;
            AskPermission();
        }

        /// <summary>Asks the system for the permission (once; later calls do nothing).</summary>
        public static void AskPermission()
        {
            PlayerPrefs.SetInt(AskedKey, 1); PlayerPrefs.Save();
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            if (!started || current == null) return;
            current.StartCoroutine(current.Ask());
#else
            Debug.Log("CHECKOUT_NOTIF permission asked (Editor: nothing to ask)");
#endif
        }

#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
        System.Collections.IEnumerator Ask()
        {
            var request = NotificationCenter.RequestPermission();
            while (request.Status == NotificationsPermissionStatus.RequestPending) yield return null;
            Debug.Log("CHECKOUT_NOTIF permission " + request.Status);
            Changed?.Invoke();
        }
#endif

        /// <summary>Opens the phone's settings page of the app (to turn the notifications back on).</summary>
        public static void OpenSystemSettings()
        {
#if UNITY_IOS && !UNITY_EDITOR
            Application.OpenURL("app-settings:");
#elif UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using var player = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var activity = player.GetStatic<AndroidJavaObject>("currentActivity");
                using var intent = new AndroidJavaObject("android.content.Intent", "android.settings.APP_NOTIFICATION_SETTINGS");
                intent.Call<AndroidJavaObject>("putExtra", "android.provider.extra.APP_PACKAGE", Application.identifier);
                intent.Call<AndroidJavaObject>("addFlags", 0x10000000);
                activity.Call("startActivity", intent);
            }
            catch (Exception e) { Debug.LogWarning("CHECKOUT_NOTIF settings: " + e.Message); }
#else
            Debug.Log("CHECKOUT_NOTIF open system settings (Editor)");
#endif
        }

        void OnApplicationPause(bool paused) { if (paused) ScheduleFromState(); else ClearPending(); }
        void OnApplicationFocus(bool focused) { if (focused) ClearPending(); }
        void OnApplicationQuit() => ScheduleFromState();

        // ── Scheduling ───────────────────────────────────────────────────────────────────────────────────────

        public struct Planned { public double inMs; public string category, title, text; }

        void ScheduleFromState()
        {
            if (!bridge) bridge = FindAnyObjectByType<CheckoutBridge>();
            var state = bridge ? bridge.State : null;
            ClearPending();
            if (state == null) return;
            var plan = Plan(state, DateTime.Now);
            foreach (var p in plan) Schedule(p);
            Debug.Log("CHECKOUT_NOTIF scheduled " + plan.Count + (plan.Count > 0 ? ": " + string.Join(" | ", plan.ConvertAll(p => $"{p.category} +{p.inMs / 60000d:0.#} min {p.title} / {p.text}")) : ""));
        }

        static void Schedule(Planned p)
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            if (!started || Permission == "denied") return;
            NotificationCenter.ScheduleNotification(new Notification { Title = p.title, Text = p.text, Data = p.category },
                new NotificationDateTimeSchedule(DateTime.Now.AddMilliseconds(p.inMs)));
#endif
        }

        static void ClearPending()
        {
#if (UNITY_ANDROID || UNITY_IOS) && !UNITY_EDITOR
            if (!started) return;
            NotificationCenter.CancelAllScheduledNotifications();
            NotificationCenter.CancelAllDeliveredNotifications();
#endif
        }

        static bool HasLongTimer(Snapshot s)
        {
            double now = s.sentAt;
            bool Long(double endsAt) => endsAt - now > 5 * 60_000;
            if (s.builds != null) foreach (var b in s.builds) if (!b.pending && !b.queued && Long(b.endsAt)) return true;
            if (s.evolutions != null) foreach (var e in s.evolutions) if (!e.queued && Long(e.endsAt)) return true;
            if (s.construction != null && !string.IsNullOrEmpty(s.construction.expansionId) && Long(s.construction.endsAt)) return true;
            if (s.era?.construction != null && !string.IsNullOrEmpty(s.era.construction.eraId) && Long(s.era.construction.endsAt)) return true;
            return false;
        }

        static string L(string text) => CheckoutI18n.T(text);
        static string F(string pattern, params object[] args) => string.Format(L(pattern), args);

        /// <summary>The notifications for a snapshot, soonest first (pure: also used by the QA).</summary>
        public static List<Planned> Plan(Snapshot s, DateTime localNow)
        {
            var list = new List<Planned>();
            double now = s.sentAt;
            void Add(string category, double endsAt, string title, string text)
            {
                double inMs = endsAt - now;
                if (!IsOn(category) || inMs < MinLeadMs || double.IsNaN(inMs)) return;
                list.Add(new Planned { inMs = inMs, category = category, title = title, text = text });
            }

            // Obras: builds and evolutions (merged when they end together), the expansion works, production.
            var works = new List<(double at, string name)>();
            if (s.builds != null) foreach (var b in s.builds) if (!b.pending && !b.queued) works.Add((b.endsAt, b.name));
            if (s.evolutions != null) foreach (var e in s.evolutions) if (!e.queued) works.Add((e.endsAt, null));
            works.Sort((a, b) => a.at.CompareTo(b.at));
            for (int i = 0; i < works.Count;)
            {
                int j = i; while (j + 1 < works.Count && works[j + 1].at - works[i].at < MergeMs) j++;
                int n = j - i + 1; var last = works[j];
                if (n > 1) Add("obras", last.at, L("Obras prontas!"), F("{0} obras do seu mercado ficaram prontas. Venha ver!", n));
                else if (!string.IsNullOrEmpty(last.name)) Add("obras", last.at, L("Obra pronta!"), F("Terminou: {0}. Venha ver!", L(last.name)));
                else Add("obras", last.at, L("Evolução pronta!"), L("A evolução do seu móvel terminou. Venha ver como ficou!"));
                i = j + 1;
            }
            if (s.construction != null && !string.IsNullOrEmpty(s.construction.expansionId))
                Add("obras", s.construction.endsAt, L("Ampliação pronta!"), L("A obra do seu mercado terminou. Venha abrir a parte nova!"));
            if (s.era?.construction != null && !string.IsNullOrEmpty(s.era.construction.eraId))
                Add("obras", s.era.construction.endsAt, L("Nova fase pronta!"), F("Terminou a obra: {0}. Venha inaugurar!", L(s.era.construction.name)));
            if (s.jobs != null && s.jobs.Length > 0)
            {
                double last = 0; foreach (var j in s.jobs) last = Math.Max(last, j.endsAt);
                Add("obras", last, L("Produção pronta!"), L("A produção do seu mercado terminou. Venha repor as prateleiras!"));
            }

            // Entregas: supplier orders (one notification: the last one to arrive) and the fleet trucks back home.
            if (s.orders != null)
            {
                double last = 0; int n = 0;
                foreach (var o in s.orders) if (o.status != "entregue") { last = Math.Max(last, o.createdAt + o.deliveryDurationMs); n++; }
                if (n > 0) Add("entregas", last, L("Entrega chegou!"), n > 1 ? F("{0} entregas chegaram no depósito. Venha descarregar!", n) : L("A sua entrega chegou no depósito. Venha descarregar!"));
            }
            if (s.chain?.trucks != null)
            {
                double last = 0;
                foreach (var t in s.chain.trucks) if (!string.IsNullOrEmpty(t.job) && t.returnAt > now) last = Math.Max(last, t.returnAt);
                if (last > 0) Add("entregas", last, L("Caminhões de volta!"), L("Os caminhões da sua rede voltaram para o pátio. Mande eles de novo!"));
            }

            // Presente diário: tomorrow at noon (or today at 19:00 when today's is still waiting).
            {
                var at = s.dailyClaimable && localNow.Hour < 18 ? localNow.Date.AddHours(19) : localNow.Date.AddDays(1).AddHours(12);
                Add("presente", now + (at - localNow).TotalMilliseconds, L("Presente do dia"), L("O seu presente diário está esperando. Não perca a sequência!"));
            }

            // Mercado parado: an open market sells while away up to the cap; then it waits for the player.
            if (s.isOpen) Add("mercado", now + OfflineCapMs, L("O mercado parou de vender"), L("Os clientes estão esperando! Volte para o mercado continuar vendendo."));

            list.Sort((a, b) => a.inMs.CompareTo(b.inMs));
            if (list.Count > MaxScheduled) list.RemoveRange(MaxScheduled, list.Count - MaxScheduled);
            return list;
        }
    }
}
