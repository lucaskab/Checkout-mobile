using UnityEditor;

// Checkout > QA > Capture phone UI: in Play mode (Device Simulator on an iPhone), opens every page and game window,
// saves screenshots and the UI measurements to Logs/ui_qa (see CheckoutUiQa).
public static class CheckoutUiQaMenu
{
    [MenuItem("Checkout/QA/Capture phone UI (Play mode)")]
    static void Capture() => Checkout.CheckoutUiQa.Begin();

    [MenuItem("Checkout/QA/Capture checkout phases (Play mode)")]
    static void CaptureCounter() => Checkout.CheckoutUiQa.Begin(true);

    [MenuItem("Checkout/QA/Capture checkout phases (Play mode)", true)]
    static bool CanCaptureCounter() => EditorApplication.isPlaying && !Checkout.CheckoutUiQa.Running;

    [MenuItem("Checkout/QA/Capture phone UI (Play mode)", true)]
    static bool CanCapture() => EditorApplication.isPlaying && !Checkout.CheckoutUiQa.Running;
}
