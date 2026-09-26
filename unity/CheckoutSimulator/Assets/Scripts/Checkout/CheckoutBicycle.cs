using UnityEngine;

namespace Checkout
{
    // Low-poly city bike built from primitives (faces +Z). Rider anchors are in bike space.
    public class CheckoutBicycle
    {
        public const float WheelRadius = .34f, CrankRadius = .17f;
        public static readonly Vector3 Saddle = new Vector3(0, .9f, -.22f), Crank = new Vector3(0, .32f, 0), Grip = new Vector3(.26f, 1.05f, .32f);
        public Transform root;
        Transform[] wheels = new Transform[2];
        Transform crank;
        static readonly Color[] paints = { new Color(.16f, .55f, .62f), new Color(.86f, .36f, .24f), new Color(.95f, .76f, .26f), new Color(.30f, .42f, .70f) };
        static Material dark, metal;

        public static CheckoutBicycle Build(Transform parent)
        {
            if (!dark) { dark = Flat(new Color(.13f, .13f, .14f), .2f); metal = Flat(new Color(.72f, .74f, .75f), .5f); }
            var paint = Flat(paints[Random.Range(0, paints.Length)], .35f);
            var bike = new CheckoutBicycle { root = new GameObject("Bicycle").transform };
            bike.root.SetParent(parent, false);
            for (int i = 0; i < 2; i++)
            {
                var wheel = new GameObject(i == 0 ? "Rear wheel" : "Front wheel").transform;
                wheel.SetParent(bike.root, false); wheel.localPosition = new Vector3(0, WheelRadius, i == 0 ? -.52f : .52f);
                Part(wheel, PrimitiveType.Cylinder, Vector3.zero, new Vector3(WheelRadius * 2, .025f, WheelRadius * 2), Quaternion.Euler(0, 0, 90), dark);
                Part(wheel, PrimitiveType.Cylinder, Vector3.zero, new Vector3(WheelRadius * 1.6f, .03f, WheelRadius * 1.6f), Quaternion.Euler(0, 0, 90), metal);
                Part(wheel, PrimitiveType.Cube, Vector3.zero, new Vector3(.03f, WheelRadius * 1.7f, .03f), Quaternion.identity, dark); // spoke bar shows the spin
                bike.wheels[i] = wheel;
            }
            Vector3 rear = new Vector3(0, WheelRadius, -.52f), front = new Vector3(0, WheelRadius, .52f), seat = new Vector3(0, .82f, -.2f), head = new Vector3(0, .9f, .3f);
            Tube(bike.root, rear, Crank, .045f, paint); Tube(bike.root, Crank, seat, .05f, paint); Tube(bike.root, seat, head, .05f, paint);
            Tube(bike.root, Crank, head, .055f, paint); Tube(bike.root, rear, seat, .035f, paint); Tube(bike.root, head, front, .04f, metal);
            Tube(bike.root, head, new Vector3(0, Grip.y, Grip.z), .035f, metal);
            Tube(bike.root, new Vector3(-Grip.x, Grip.y, Grip.z), new Vector3(Grip.x, Grip.y, Grip.z), .035f, dark);
            Tube(bike.root, seat, Saddle - new Vector3(0, .04f, 0), .03f, metal);
            Part(bike.root, PrimitiveType.Cube, Saddle, new Vector3(.14f, .05f, .26f), Quaternion.identity, dark);
            Part(bike.root, PrimitiveType.Cube, new Vector3(0, WheelRadius + .38f, -.62f), new Vector3(.14f, .03f, .38f), Quaternion.identity, paint); // rear rack
            bike.crank = new GameObject("Crank").transform; bike.crank.SetParent(bike.root, false); bike.crank.localPosition = Crank;
            Part(bike.crank, PrimitiveType.Cylinder, Vector3.zero, new Vector3(.16f, .02f, .16f), Quaternion.Euler(0, 0, 90), metal);
            return bike;
        }

        // Rolls the wheels and turns the cranks; returns the crank angle (radians).
        public float Roll(float distance, ref float angle)
        {
            angle += distance / WheelRadius;
            foreach (var w in wheels) w.localRotation = Quaternion.Euler(angle * Mathf.Rad2Deg, 0, 0);
            crank.localRotation = Quaternion.Euler(angle * .55f * Mathf.Rad2Deg, 0, 0);
            return angle * .55f;
        }

        // World position of a pedal (side -1 left, +1 right) for a crank angle.
        public Vector3 Pedal(int side, float crankAngle)
        {
            float a = crankAngle + (side > 0 ? Mathf.PI : 0);
            return root.TransformPoint(Crank + new Vector3(side * .13f, -Mathf.Cos(a) * CrankRadius, Mathf.Sin(a) * CrankRadius));
        }

        static Material Flat(Color color, float gloss)
        {
            var material = new Material(Shader.Find("Standard")) { color = color };
            material.SetFloat("_Glossiness", gloss);
            return material;
        }

        static void Part(Transform parent, PrimitiveType type, Vector3 p, Vector3 scale, Quaternion rotation, Material material)
        {
            var part = GameObject.CreatePrimitive(type);
            Object.Destroy(part.GetComponent<Collider>());
            part.transform.SetParent(parent, false);
            part.transform.localPosition = p; part.transform.localRotation = rotation; part.transform.localScale = scale;
            part.GetComponent<Renderer>().sharedMaterial = material;
        }

        static void Tube(Transform parent, Vector3 a, Vector3 b, float thickness, Material material) =>
            Part(parent, PrimitiveType.Cube, (a + b) / 2, new Vector3(thickness, thickness, Vector3.Distance(a, b)), Quaternion.LookRotation(b - a), material);
    }
}
