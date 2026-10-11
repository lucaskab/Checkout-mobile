using UnityEngine;
using UnityEngine.UI;

namespace Checkout
{
    // Screen fit for phones. The game's UI is laid out in a 1600 x 1000 reference (desktop). On a phone in landscape
    // that came out tiny (a 20-unit text about 10 pt), so on handheld devices every canvas uses a shorter logical
    // screen: HandheldHeight units tall, matched on the height, which draws everything about 1.3x bigger. Everything a
    // canvas shows also goes inside a SafeArea child, kept clear of the Dynamic Island / notch and the rounded corners.
    // In the Editor, Checkout > iPhone > Preview phone UI makes Play mode behave like the phone (set the Game view to a
    // phone resolution, e.g. 2796x1290).
    public static class CheckoutScreen
    {
        public const float HandheldHeight = 680f;
#if UNITY_EDITOR
        public const string PreviewKey = "Checkout.PreviewPhoneUi";
        // The Device Simulator reports the simulated phone through UnityEngine.Device: it shows the phone layout too.
        public static bool Handheld => Application.isMobilePlatform || UnityEngine.Device.Application.isMobilePlatform || UnityEditor.EditorPrefs.GetBool(PreviewKey, false);
#else
        public static bool Handheld => Application.isMobilePlatform || SystemInfo.deviceType == DeviceType.Handheld;
#endif

        /// <summary>Desktop: the 1600x1000 reference with the given match. Phone: a short logical screen matched on the
        /// height (fixedLayout keeps the desktop reference, for full-screen moments designed for 1000 units of height).</summary>
        public static void Fit(CanvasScaler scaler, float desktopMatch = .5f, bool fixedLayout = false)
        {
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            if (Handheld && !fixedLayout) { scaler.referenceResolution = new Vector2(1600, HandheldHeight); scaler.matchWidthOrHeight = 1; }
            else { scaler.referenceResolution = new Vector2(1600, 1000); scaler.matchWidthOrHeight = desktopMatch; }
        }

        /// <summary>The part of the screen the UI uses: the safe area, adjusted for phones in landscape
        /// (see CheckoutSafeArea.Landscape).</summary>
        public static Rect Usable(Rect safe) => Handheld && Screen.width > Screen.height ? CheckoutSafeArea.Landscape(safe) : safe;

        /// <summary>A full-screen child of the canvas that follows Screen.safeArea; build the UI inside it.</summary>
        public static RectTransform SafeArea(Transform canvas)
        {
            var go = new GameObject("SafeArea", typeof(RectTransform));
            go.transform.SetParent(canvas, false);
            var rect = (RectTransform)go.transform;
            rect.anchorMin = Vector2.zero; rect.anchorMax = Vector2.one; rect.offsetMin = rect.offsetMax = Vector2.zero;
            go.AddComponent<CheckoutSafeArea>();
            return rect;
        }
    }

    // Keeps its RectTransform on Screen.safeArea (re-applied when the phone turns or the screen size changes).
    public sealed class CheckoutSafeArea : MonoBehaviour
    {
        Rect applied; Vector2Int size; ScreenOrientation turned;
        void OnEnable() => Apply();
        void Update() { if (Screen.safeArea != applied || size.x != Screen.width || size.y != Screen.height || Screen.orientation != turned) Apply(); } // turning the phone over moves the island
        void Apply()
        {
            applied = Screen.safeArea; size = new Vector2Int(Screen.width, Screen.height); turned = Screen.orientation;
            if (Screen.width <= 0 || Screen.height <= 0) return;
            var r = (RectTransform)transform;
            var safe = applied;
#if UNITY_EDITOR
            // Previewing the phone in the Editor: the Game view has no island, so pretend the iPhone's (about 6% on each side).
            if (CheckoutScreen.Handheld && safe.width >= Screen.width - 1)
                safe = new Rect(Screen.width * .06f, Screen.height * .045f, Screen.width * .88f, Screen.height * .955f);
#endif
            safe = CheckoutScreen.Usable(safe);
            r.anchorMin = new Vector2(safe.xMin / Screen.width, safe.yMin / Screen.height);
            r.anchorMax = new Vector2(safe.xMax / Screen.width, safe.yMax / Screen.height);
            r.offsetMin = r.offsetMax = Vector2.zero;
        }

        // iPhone in landscape reports the island's inset on BOTH sides and the home bar's at the bottom only, so the
        // UI sat lower-heavy with an empty strip on the side without the island. Keep the full inset only on the island's
        // side; the other side and the top and bottom get a small equal margin (still clear of the rounded corners), so
        // the content is centred vertically and uses the free side.
        public static Rect Landscape(Rect safe)
        {
            float w = Screen.width, h = Screen.height;
            float left = safe.xMin, right = w - safe.xMax;
            float side = Mathf.Round(h * .05f), edge = Mathf.Round(h * .03f); // iPhone 13 Pro: 59 and 35 px
            // Home button / bar on the right (LandscapeLeft) means the island is on the left, and the other way round.
            bool islandLeft = Screen.orientation != ScreenOrientation.LandscapeRight;
            if (islandLeft) right = Mathf.Min(right, side); else left = Mathf.Min(left, side);
            return new Rect(left, edge, w - left - right, h - 2 * edge);
        }
    }
}
