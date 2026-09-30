using UnityEngine;

namespace Checkout
{
    // Small signs of life on the empty lot behind the fence: pigeons pecking and hopping about, a loose
    // tarp lifting in the wind, grass swaying and a broken lamp that flickers.
    public class CheckoutLotLife : MonoBehaviour
    {
        public Transform[] pigeons = new Transform[0];
        public Transform[] grass = new Transform[0];
        public Transform tarp, cat;
        public Renderer lamp;
        public Material lampOn, lampOff;
        public Vector3 area = new Vector3(6, 0, 6);

        Vector3[] homes, targets; float[] timers; float flicker;

        void Start()
        {
            homes = new Vector3[pigeons.Length]; targets = new Vector3[pigeons.Length]; timers = new float[pigeons.Length];
            for (int i = 0; i < pigeons.Length; i++) if (pigeons[i]) { homes[i] = targets[i] = pigeons[i].position; timers[i] = Random.Range(0, 3f); }
        }

        void Update()
        {
            float dt = Time.deltaTime, t = Time.time;
            for (int i = 0; i < pigeons.Length; i++)
            {
                var p = pigeons[i]; if (!p) continue;
                timers[i] -= dt;
                var delta = targets[i] - p.position; delta.y = 0;
                if (delta.magnitude > .03f)
                {
                    // Short hops towards the next crumb.
                    float step = Mathf.Min(delta.magnitude, dt * 1.1f);
                    p.position += delta.normalized * step;
                    var pos = p.position; pos.y = homes[i].y + Mathf.Abs(Mathf.Sin(t * 14 + i)) * .06f; p.position = pos;
                    p.rotation = Quaternion.RotateTowards(p.rotation, Quaternion.LookRotation(delta), dt * 400);
                }
                else
                {
                    // Pecking: the whole bird tips forward in quick nods.
                    float peck = Mathf.Max(0, Mathf.Sin(t * 9 + i * 1.7f)) * 28;
                    var e = p.eulerAngles; p.rotation = Quaternion.Euler(peck, e.y, 0);
                    var pos = p.position; pos.y = homes[i].y; p.position = pos;
                    if (timers[i] <= 0)
                    {
                        timers[i] = Random.Range(1.5f, 4.5f);
                        var r = Random.insideUnitCircle * 1.4f;
                        var next = homes[i] + new Vector3(r.x, 0, r.y);
                        targets[i] = next;
                    }
                }
            }
            for (int i = 0; i < grass.Length; i++)
                if (grass[i]) grass[i].localRotation = Quaternion.Euler(Mathf.Sin(t * 1.3f + i * .7f) * 4, grass[i].localEulerAngles.y, Mathf.Cos(t * 1.1f + i) * 3);
            if (tarp) tarp.localRotation = Quaternion.Euler(Mathf.Sin(t * 2.2f) * 7 + Mathf.Sin(t * 5.1f) * 2, 0, 0);
            if (cat) cat.localRotation = Quaternion.Euler(0, Mathf.Sin(t * .8f) * 25, 0);
            if (lamp && lampOn && lampOff)
            {
                flicker -= dt;
                if (flicker <= 0)
                {
                    bool on = lamp.sharedMaterial != lampOn;
                    lamp.sharedMaterial = on ? lampOn : lampOff;
                    flicker = on ? Random.Range(.05f, 1.6f) : Random.Range(.04f, .25f);
                }
            }
        }
    }
}
