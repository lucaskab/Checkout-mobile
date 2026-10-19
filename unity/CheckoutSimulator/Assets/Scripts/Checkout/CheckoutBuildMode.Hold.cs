using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout
{
    // Touch and hold a piece of the shop (or a decoration outside) for a moment to move it, as in Hay Day and Township
    // (Lucas 20/10: the game is mostly played on phones; no Ctrl, no G). A ring fills under the finger; when it closes
    // the build mode opens with that piece lifted, and it follows the same finger until it is let go. Moving the finger
    // (a camera pan), a second finger (a pinch) or a window over the map cancels the hold. The Construir button and the
    // tray stay the way in for everything else.
    public partial class CheckoutBuildMode
    {
        const float HoldSeconds = .55f, HoldShowAfter = .12f, HoldSlop = 14f;
        CheckoutInterior.Item holdItem; float holdStart; Vector2 holdAt; Image holdRing, holdTrack;

        bool CanHold => buildButton && buildButton.activeSelf && Interior && !CheckoutStartMenu.Showing && !CheckoutMapEditor.Open
            && !CheckoutDesktopHUD.ShopOpen && !CheckoutLotView.Open && simulation && simulation.view;

        void HoldToMove()
        {
            if (Open) { if (holdItem != null) { holdItem = null; ShowRing(false); } return; }
            if (Input.GetMouseButtonDown(0) && Input.touchCount < 2 && CanHold && !CheckoutPointer.OverUiNow())
            {
                var hit = Interior.Pick(simulation.view.ScreenPointToRay(Input.mousePosition));
                if (hit != null && hit.root && !hit.building) { holdItem = hit; holdStart = Time.unscaledTime; holdAt = Input.mousePosition; }
            }
            if (holdItem == null) return;
            if (!Input.GetMouseButton(0) || Input.touchCount > 1 || !CanHold || !holdItem.root || ((Vector2)Input.mousePosition - holdAt).magnitude > HoldSlop)
            { holdItem = null; ShowRing(false); return; }
            float t = (Time.unscaledTime - holdStart) / HoldSeconds;
            if (Time.unscaledTime - holdStart > HoldShowAfter) ShowRing(true, Mathf.InverseLerp(HoldShowAfter / HoldSeconds, 1, t));
            if (t < 1) return;
            var it = holdItem; holdItem = null; ShowRing(false);
            Enter(it);
            if (!Open) return;
            // The finger is still down: the piece is already in its hand.
            var ray = simulation.view.ScreenPointToRay(Input.mousePosition);
            if (PlaneOf(it).Raycast(ray, out var d))
            {
                dragging = it; dragOffset = it.root.position - ray.GetPoint(d); dragStartPosition = it.root.position; dragStartRot = it.rot;
                simulation.cameraLocked = true; pointerDown = Input.mousePosition; pointerMoved = false; pressOnItem = true;
            }
            Say(CheckoutScreen.Handheld ? "Arraste para o lugar e solte." : "Arraste para o lugar e solte o botão.");
        }

        void ShowRing(bool on, float fill = 0)
        {
            if (!on) { if (holdTrack) holdTrack.gameObject.SetActive(false); return; }
            if (!holdTrack)
            {
                holdTrack = N.Image(root, "Hold ring", new Color(0, 0, 0, .28f), 0); holdTrack.sprite = CheckoutGlyph.Get("ring");
                var r = holdTrack.rectTransform; r.anchorMin = r.anchorMax = r.pivot = new Vector2(.5f, .5f); r.sizeDelta = new Vector2(96, 96);
                holdRing = N.Image(holdTrack.transform, "Fill", Color.white, 0); holdRing.sprite = CheckoutGlyph.Get("ring");
                holdRing.type = Image.Type.Filled; holdRing.fillMethod = Image.FillMethod.Radial360; holdRing.fillOrigin = (int)Image.Origin360.Top; holdRing.fillClockwise = true;
                var f = holdRing.rectTransform; f.anchorMin = Vector2.zero; f.anchorMax = Vector2.one; f.offsetMin = f.offsetMax = Vector2.zero;
            }
            holdTrack.gameObject.SetActive(true);
            holdRing.fillAmount = Mathf.Clamp01(fill); holdRing.color = Color.Lerp(K.C("FFE3A8"), K.C("5DA637"), fill);
            if (RectTransformUtility.ScreenPointToLocalPointInRectangle(root, holdAt, null, out var local)) holdTrack.rectTransform.anchoredPosition = local + new Vector2(0, 70); // above the fingertip
        }

        void ToggleGrid()
        {
            CheckoutInterior.GridOn = !CheckoutInterior.GridOn;
            Say(CheckoutInterior.GridOn ? "Grade ligada: as peças encaixam nos quadrados." : "Grade desligada: movimento livre (ainda encosta nas paredes e nos móveis).");
            RefreshTray();
        }
    }
}
