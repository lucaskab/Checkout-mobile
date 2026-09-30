using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Little motions on the furniture: balloons bob, leaves sway, the claw machine blinks, screens scroll,
    // fans and signs spin. Driven by node names from the Interior Kit ("Anim Bob", "Anim Sway"...).
    public class CheckoutInteriorLife : MonoBehaviour
    {
        struct Node { public Transform t; public Vector3 pos; public Quaternion rot; public Vector3 scale; public int kind; public float seed; public Renderer r; }
        readonly List<Node> nodes = new List<Node>();
        int seen = -1; float rescan;
        MaterialPropertyBlock block;

        void Update()
        {
            rescan -= Time.deltaTime;
            if (rescan <= 0 || transform.childCount != seen) { rescan = 2; seen = transform.childCount; Scan(); }
            float t = Time.time;
            for (int i = 0; i < nodes.Count; i++)
            {
                var n = nodes[i]; if (!n.t) continue;
                switch (n.kind)
                {
                    case 0: n.t.localPosition = n.pos + Vector3.up * Mathf.Sin(t * 1.6f + n.seed) * .05f; n.t.localRotation = n.rot * Quaternion.Euler(0, 0, Mathf.Sin(t * 1.1f + n.seed) * 4); break;
                    case 1: n.t.localRotation = n.rot * Quaternion.Euler(Mathf.Sin(t * 1.3f + n.seed) * 2.5f, 0, Mathf.Cos(t * 1.1f + n.seed) * 2.5f); break;
                    case 2: n.t.localScale = n.scale * ((Mathf.Repeat(t * 2.2f + n.seed, 1) < .5f) ? 1 : .001f); break;
                    case 3:
                        if (n.r) { block ??= new MaterialPropertyBlock(); n.r.GetPropertyBlock(block); block.SetVector("_MainTex_ST", new Vector4(1, 1f / 3, 0, Mathf.Floor(t / 2.5f + n.seed) / 3f)); n.r.SetPropertyBlock(block); }
                        break;
                    case 4: n.t.localRotation = n.rot * Quaternion.Euler(0, t * 60 + n.seed * 50, 0); break;
                }
            }
        }

        readonly HashSet<Transform> known = new HashSet<Transform>();
        // Adds new nodes only: their rest pose is read once, before any animation touched them.
        void Scan()
        {
            nodes.RemoveAll(n => !n.t);
            known.RemoveWhere(t => !t);
            foreach (var t in GetComponentsInChildren<Transform>())
            {
                if (known.Contains(t)) continue;
                string n = t.name; // Blender numbers repeated names: "Anim Bob.003".
                int kind = n.StartsWith("Anim Bob") ? 0 : n.StartsWith("Anim Sway") ? 1 : n.StartsWith("Anim Blink") ? 2 : n.StartsWith("Anim Scroll") ? 3 : n.StartsWith("Anim Spin") ? 4 : -1;
                if (kind < 0) continue;
                known.Add(t);
                nodes.Add(new Node { t = t, pos = t.localPosition, rot = t.localRotation, scale = t.localScale, kind = kind, seed = (nodes.Count * 1.618f) % 7f, r = t.GetComponentInChildren<Renderer>() });
            }
        }
    }
}
