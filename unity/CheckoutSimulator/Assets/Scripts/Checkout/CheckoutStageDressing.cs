using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Swaps the market's facade, signage and decor per expansion stage (corner shop -> hypermarket).
    public class CheckoutStageDressing : MonoBehaviour
    {
        public string[] stageTitles = { "MERCADINHO", "MERCADO DO BAIRRO", "SUPERMERCADO", "SUPERMERCADO", "HIPERMERCADO" };
        // Scenery elsewhere in the world that makes way for the bigger market at later stages.
        public CheckoutStageItem[] external = new CheckoutStageItem[0];
        CheckoutStageItem[] items;
        readonly HashSet<CheckoutStageItem> hidden = new HashSet<CheckoutStageItem>();
        public int Stage { get; private set; } = -1;

        CheckoutStageItem[] Items
        {
            get
            {
                if (items == null || items.Length == 0)
                {
                    var list = new List<CheckoutStageItem>(GetComponentsInChildren<CheckoutStageItem>(true));
                    foreach (var item in external) if (item) list.Add(item);
                    items = list.ToArray();
                }
                return items;
            }
        }

        // Where a piece stands for a layout (null = the unprojected base map).
        public const float AwningLift = .85f;

        public static Vector3 Place(CheckoutStageItem item, MarketLayout layout)
        {
            if (layout == null) return item.basePosition;
            var p = CheckoutMarketLayout.Project(item.basePosition, layout);
            if (item.attachEast) p.x = CheckoutMarketLayout.Project(new Vector3(9.4f, 0, 0), layout).x + (item.basePosition.x - 9.4f);
            return p;
        }

        public string Title(int stage) => stageTitles[Mathf.Clamp(stage, 0, stageTitles.Length - 1)];

        // Places every item on the projected market and shows the ones of this stage. With `hold`, the
        // newly visible pieces stay hidden until Reveal() (used by the construction timelapse).
        public List<CheckoutStageItem> Apply(CheckoutMarketLayout layout, int stage, bool hold)
        {
            var appeared = new List<CheckoutStageItem>();
            // The welcome text painted on the entrance mat read as clutter under the portal sign: plain mat.
            foreach (var t in GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("Text BEM") && t.gameObject.activeSelf) t.gameObject.SetActive(false);
            foreach (var item in Items)
            {
                if (!item) continue;
                if (!item.captured) item.Capture();
                var t = item.transform;
                var fit = item.Fits(layout ? layout.State : null);
                if (item.fixedPosition) { item.gameObject.SetActive(item.Visible(stage) && fit); continue; }
                t.position = Place(item, layout ? layout.State : null);
                // The entrance awning was modelled for shorter people: lift it so customers (about 2.1 m with
                // their heads) walk under it instead of through the canvas.
                if (item.name.IndexOf("door awning", System.StringComparison.OrdinalIgnoreCase) >= 0) t.position += Vector3.up * AwningLift;
                var scale = item.baseScale;
                var state = layout ? layout.State : null;
                if (state != null)
                {
                    // Stretch along the world axis the piece lies on, whatever its local axes are.
                    var axes = new Vector3(item.stretchX ? state.widthScale : 1, 1, item.stretchZ ? state.depthScale : 1);
                    if (item.stretchX || item.stretchZ)
                        scale = Vector3.Scale(scale, new Vector3(
                            Vector3.Scale(t.right, axes).magnitude,
                            Vector3.Scale(t.up, axes).magnitude,
                            Vector3.Scale(t.forward, axes).magnitude));
                }
                t.localScale = scale;
                bool visible = item.Visible(stage) && fit;
                bool wasVisible = Stage >= 0 && item.Visible(Stage);
                if (visible && !wasVisible && hold) { appeared.Add(item); hidden.Add(item); item.gameObject.SetActive(false); continue; }
                item.gameObject.SetActive(visible && !hidden.Contains(item));
            }
            Stage = stage;
            return appeared;
        }

        // Pops the held pieces in one after another with a little bounce.
        public IEnumerator Reveal(float spacing = .06f)
        {
            var list = new List<CheckoutStageItem>(hidden);
            list.Sort((a, b) => a.transform.position.y.CompareTo(b.transform.position.y));
            hidden.Clear();
            foreach (var item in list)
            {
                if (!item || !item.Visible(Stage)) continue;
                item.gameObject.SetActive(true);
                StartCoroutine(Pop(item.transform, item.transform.localScale));
                yield return new WaitForSeconds(spacing);
            }
        }

        // While the works for `targetStage` run, the street scenery on that ground is already cleared away
        // (the next Apply restores whatever the real stage shows).
        public void ClearForWorks(int targetStage)
        {
            foreach (var item in external)
                if (item && item.gameObject.activeSelf && !item.Visible(targetStage)) item.gameObject.SetActive(false);
        }

        public void RevealNow()
        {
            foreach (var item in hidden) if (item) item.gameObject.SetActive(item.Visible(Stage));
            hidden.Clear();
        }

        static IEnumerator Pop(Transform t, Vector3 target)
        {
            for (float time = 0; time < .45f; time += Time.deltaTime)
            {
                if (!t) yield break;
                float k = time / .45f;
                // Overshoot and settle (easeOutBack).
                float s = 1 + 2.2f * Mathf.Pow(k - 1, 3) + 1.2f * Mathf.Pow(k - 1, 2);
                t.localScale = target * Mathf.Max(.01f, s);
                yield return null;
            }
            if (t) t.localScale = target;
        }
    }
}
