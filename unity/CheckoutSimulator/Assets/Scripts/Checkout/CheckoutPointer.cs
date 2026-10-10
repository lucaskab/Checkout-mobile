using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout
{
    // Whether a click or tap belongs to the UI. EventSystem.IsPointerOverGameObject() with no argument only knows the
    // mouse: on the iPhone a finger over a panel or a button reads as "not over UI" and the tap fell through to the
    // world (lots, the stall, the courier...). World click handlers ask this instead. The answer for a press is taken
    // when the finger or button goes down (before anything moves) and kept until the next press, so handlers that act
    // on release (GetMouseButtonUp) see where the press started.
    [DefaultExecutionOrder(-1000)]
    public sealed class CheckoutPointer : MonoBehaviour
    {
        static bool pressOverUi;
        static int pressFrame = -1;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            var go = new GameObject("CheckoutPointer") { hideFlags = HideFlags.HideInHierarchy };
            DontDestroyOnLoad(go);
            go.AddComponent<CheckoutPointer>();
        }

        void Update()
        {
            if (Input.GetMouseButtonDown(0) || AnyTouchBegan()) { pressOverUi = OverUiNow(); pressFrame = Time.frameCount; }
        }

        static bool AnyTouchBegan()
        {
            for (int i = 0; i < Input.touchCount; i++) if (Input.GetTouch(i).phase == TouchPhase.Began) return true;
            return false;
        }

        /// <summary>The pointer (mouse, or any finger on the screen) is over a UI element right now.</summary>
        public static bool OverUiNow()
        {
            var es = EventSystem.current;
            if (!es) return false;
            if (Input.touchCount > 0)
            {
                for (int i = 0; i < Input.touchCount; i++) if (es.IsPointerOverGameObject(Input.GetTouch(i).fingerId)) return true;
                return false;
            }
            return es.IsPointerOverGameObject();
        }

        /// <summary>The current (or last) press started over UI, or the pointer is over UI now: the world must ignore it.</summary>
        public static bool OverUi
        {
            get
            {
                // A handler that runs before this component on the press frame still gets the right answer.
                if (pressFrame != Time.frameCount && (Input.GetMouseButtonDown(0) || AnyTouchBegan())) { pressOverUi = OverUiNow(); pressFrame = Time.frameCount; }
                return pressOverUi || OverUiNow();
            }
        }
    }
}
