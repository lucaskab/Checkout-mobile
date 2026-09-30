using System;
using UnityEngine;

namespace Checkout
{
    // Small moving details that keep the stock room and the central warehouse alive: roller doors that
    // roll up when a truck backs onto their bay (or now and then on their own), rooftop fans and turbine
    // vents, a chasing bulb border on the name board, dock lights, a beacon and a forklift shuttling pallets.
    public class CheckoutStorageLife : MonoBehaviour
    {
        [Serializable]
        public class Door
        {
            public Transform pivot;          // top of the opening; its Y scale rolls the curtain up
            public Transform watch;          // truck that uses this door (optional)
            public Vector3 watchHome;        // where that truck stands when docked
            public Renderer signal;          // dock light: green while a truck is docked
            public float period = 18f, offset;
            [NonSerialized] public float open;
        }

        public Door[] doors = new Door[0];
        public Transform[] fans = new Transform[0];
        public Transform[] vents = new Transform[0];
        public Renderer[] bulbs = new Renderer[0];
        public Material bulbOn, bulbOff, signalGreen, signalRed;
        public Transform beacon;

        [Header("Forklift")]
        public Transform forklift, forks, forkLoad;
        public Transform[] wheels = new Transform[0];
        public Vector3[] route = new Vector3[0];     // 0 = pick-up at the racks ... last = inside the door
        public int forkliftDoor = -1;               // index into doors opened for the forklift
        public float forkliftSpeed = 1.6f;

        int leg = 0; bool loaded, pausing; float pause, forkHeight;
        Vector3 forksHome;

        void Start()
        {
            if (forks) forksHome = forks.localPosition;
            if (forklift && route.Length > 0) { forklift.position = route[0]; loaded = false; }
            if (forkLoad) forkLoad.gameObject.SetActive(false);
        }

        void Update()
        {
            float dt = Time.deltaTime, t = Time.time;
            foreach (var f in fans) if (f) f.Rotate(0, 420 * dt, 0, Space.Self);
            for (int i = 0; i < vents.Length; i++) if (vents[i]) vents[i].Rotate(0, (140 + i * 23) * dt, 0, Space.Self);
            if (beacon) beacon.gameObject.SetActive(Mathf.Repeat(t, 1.4f) < .5f);
            if (bulbs.Length > 0 && bulbOn && bulbOff)
            {
                int lit = Mathf.FloorToInt(t * 6);
                for (int i = 0; i < bulbs.Length; i++) if (bulbs[i]) bulbs[i].sharedMaterial = (i + lit) % 4 == 0 ? bulbOff : bulbOn;
            }
            bool forkliftAtDoor = forklift && route.Length > 1 && Vector3.Distance(forklift.position, route[route.Length - 1]) < 3.2f;
            for (int i = 0; i < doors.Length; i++)
            {
                var d = doors[i]; if (!d.pivot) continue;
                // Horizontal distance: the saved dock marks sit higher than the trucks' pivots.
                var gap = d.watch ? d.watch.position - d.watchHome : Vector3.zero; gap.y = 0;
                bool docked = d.watch && d.watch.gameObject.activeInHierarchy && gap.magnitude < 1.2f;
                bool want = docked || (i == forkliftDoor && forkliftAtDoor) || (!d.watch && Mathf.Repeat(t + d.offset, d.period) < d.period * .35f);
                d.open = Mathf.MoveTowards(d.open, want ? 1 : 0, dt * .45f);
                float k = Mathf.SmoothStep(0, 1, d.open);
                d.pivot.localScale = new Vector3(1, Mathf.Lerp(1, .06f, k), 1);
                if (d.signal && signalGreen && signalRed) d.signal.sharedMaterial = docked ? signalGreen : signalRed;
            }
            Forklift(dt);
        }

        void Forklift(float dt)
        {
            if (!forklift || route.Length < 2) return;
            if (pausing)
            {
                pause -= dt;
                // Forks rise with the pallet at the racks and drop it inside.
                forkHeight = Mathf.MoveTowards(forkHeight, loaded ? .55f : 0, dt * .5f);
                if (forks) forks.localPosition = forksHome + Vector3.up * forkHeight;
                if (pause <= 0) pausing = false;
                return;
            }
            var target = route[leg];
            var delta = target - forklift.position;
            if (delta.magnitude < .05f)
            {
                forklift.position = target;
                if (leg == 0) { loaded = true; if (forkLoad) forkLoad.gameObject.SetActive(true); pausing = true; pause = 1.6f; }
                else if (leg == route.Length - 1)
                {
                    // Drops the pallet inside, then reverses out for the next one.
                    pausing = true; pause = 1.6f; loaded = false;
                    if (forkLoad) forkLoad.gameObject.SetActive(false);
                }
                bool outbound = loaded;
                leg = outbound ? leg + 1 : leg - 1;
                if (leg >= route.Length) leg = route.Length - 2;
                if (leg < 0) leg = 1;
                return;
            }
            // Route point 1 is the turning spot. Between the racks (0) and it the forklift backs out loaded
            // and drives in empty, forks first; from it to the door it drives loaded and backs out empty.
            bool nearRacks = leg == 0 || (leg == 1 && loaded);
            bool forward = nearRacks ? !loaded : loaded;
            var heading = forward ? delta : -delta;
            forklift.rotation = Quaternion.RotateTowards(forklift.rotation, Quaternion.LookRotation(heading.normalized), 150 * dt);
            var flat = heading; flat.y = 0;
            var facing = forklift.forward; facing.y = 0;
            if (Vector3.Angle(facing, flat) > 20) return;
            float step = Mathf.Min(delta.magnitude, forkliftSpeed * dt);
            forklift.position += delta.normalized * step;
            foreach (var w in wheels) if (w) w.Rotate(step / .2f * Mathf.Rad2Deg * (forward ? 1 : -1), 0, 0, Space.Self);
            forkHeight = Mathf.MoveTowards(forkHeight, loaded ? .25f : .05f, dt * .5f);
            if (forks) forks.localPosition = forksHome + Vector3.up * forkHeight;
        }
    }
}
