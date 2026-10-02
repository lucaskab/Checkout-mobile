using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    // What a customer carries while shopping, and how they hold it. The old props were skinned into the character
    // FBX (a cart gliding along on its own, a basket stuck to the body); now they are real models
    // (scripts/blender/build_shopping_props.py, Resources/CheckoutProps) placed every frame after the animation:
    //  - cart: pushed ahead with both hands on the handle (two-bone arm IK onto the grips); it never pokes into
    //    furniture or walls (NavMesh raycast shortens it) and the customer slows down instead of ramming people;
    //    while they pick something from a shelf it is parked beside them and their hands let go;
    //  - basket: hangs from the left hand, arm down along the body, swinging a little with the steps;
    //  - groceries appear inside one by one as they shop.
    [DefaultExecutionOrder(500)]
    public sealed class CheckoutShopperRig : MonoBehaviour
    {
        public bool cart;
        public bool Blocked { get; private set; }
        public float SpeedFactor => Blocked ? .15f : 1f;

        MarketCharacterAnimator anim;
        Transform visual, upperL, foreL, handL, upperR, foreR, handR, head, thighL;
        Transform prop, gripL, gripR, grip, front;
        readonly List<GameObject> goods = new List<GameObject>();
        bool visible, ready, placed;
        float size = 1, still, attach, swing, swingVelocity;
        int picksAtStart;
        Vector3 lastPosition, cartPosition, lastFacing = Vector3.forward;
        Quaternion cartRotation = Quaternion.identity;
        static readonly Dictionary<string, Material> painted = new Dictionary<string, Material>();
        static readonly List<CheckoutShopperRig> all = new List<CheckoutShopperRig>();

        /// <summary>Some customers push a cart in the market building; at the stalls and small shops everybody carries a hand basket.</summary>
        public static bool WantsCart(string actor) =>
            (actor == "Customer_02" || actor == "Customer_05" || actor == "Customer_07") && !CheckoutStall.Small;

        public static CheckoutShopperRig For(Transform actor)
        {
            var rig = actor.GetComponent<CheckoutShopperRig>();
            if (!rig) rig = actor.gameObject.AddComponent<CheckoutShopperRig>();
            return rig;
        }

        void OnEnable() { if (!all.Contains(this)) all.Add(this); lastPosition = transform.position; placed = false; }
        void OnDisable() { all.Remove(this); if (prop) prop.gameObject.SetActive(false); }

        public void SetVisible(bool show)
        {
            // The expansion changed since this customer last shopped (stall ↔ market): swap cart and basket.
            if (ready && show && !visible && cart != WantsCart(name))
            {
                if (prop) Destroy(prop.gameObject);
                prop = gripL = gripR = grip = front = null;
                goods.Clear();
                ready = false;
            }
            Setup();
            if (show && !visible) { picksAtStart = anim ? anim.Picks : 0; placed = false; attach = 0; }
            visible = show;
            if (prop) prop.gameObject.SetActive(show);
        }

        void Setup()
        {
            if (ready) return;
            ready = true;
            anim = GetComponent<MarketCharacterAnimator>();
            visual = anim && anim.animationPlayer ? anim.animationPlayer.transform : transform;
            cart = WantsCart(name);
            Transform Bone(string n) => visual.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == n);
            upperL = Bone("UpperArm_L"); foreL = Bone("Forearm_L"); handL = Bone("Hand_L");
            upperR = Bone("UpperArm_R"); foreR = Bone("Forearm_R"); handR = Bone("Hand_R"); head = Bone("Head"); thighL = Bone("Thigh_L");
            // The skinned props of the original rig stay hidden for good.
            foreach (var r in GetComponentsInChildren<Renderer>(true)) if (r.name.EndsWith("_Prop")) r.forceRenderingOff = true;
            var template = Resources.Load<GameObject>(cart ? "CheckoutProps/ShoppingCart" : "CheckoutProps/ShoppingBasket");
            if (!template) { Debug.LogWarning("CHECKOUT_SHOPPER missing shopping prop"); return; }
            prop = Instantiate(template).transform; prop.name = (cart ? "Cart · " : "Basket · ") + name;
            foreach (var r in prop.GetComponentsInChildren<Renderer>(true)) r.sharedMaterials = r.sharedMaterials.Select(Paint).ToArray();
            foreach (var t in prop.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "GripL") gripL = t; else if (t.name == "GripR") gripR = t; else if (t.name == "Grip") grip = t; else if (t.name == "Front") front = t;
                else if (t.name.StartsWith("Item_")) goods.Add(t.gameObject);
            }
            goods.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
            // Props follow the character's size (children are smaller than adults).
            float headHeight = head ? head.position.y - transform.position.y : 1.8f;
            size = Mathf.Clamp(headHeight / 1.85f, .72f, 1.12f);
            prop.localScale = Vector3.one * size * (cart ? 1.05f : 1f);
            if (cart && upperL && gripL && gripR)
            {
                // The characters are tall with short arms: the handle goes up to about 0.3 m below the shoulders.
                float shoulder = upperL.position.y - transform.position.y;
                float handle = (gripL.localPosition.y + gripR.localPosition.y) * .5f;
                prop.localScale = Vector3.one * Mathf.Clamp((shoulder - .3f * size) / Mathf.Max(.1f, handle), .8f, 1.35f);
            }
            prop.gameObject.SetActive(false);
        }

        // Blender materials are named C_RRGGBB: paint them like the rest of the game.
        static Material Paint(Material source)
        {
            string n = source ? source.name : "C_FFFFFF";
            int cut = n.IndexOf(' '); if (cut > 0) n = n.Substring(0, cut);
            if (painted.TryGetValue(n, out var m)) return m;
            var shader = Shader.Find("MarketDay/Soft Painted");
            if (!shader || !n.StartsWith("C_") || n.Length < 8) { painted[n] = source; return source; }
            m = new Material(shader) { name = "Shopper " + n, color = MarketSimulation.C(n.Substring(2, 6)) };
            if (m.HasProperty("_Outline")) m.SetFloat("_Outline", .45f);
            if (m.HasProperty("_OutlineColor")) m.SetColor("_OutlineColor", new Color(.22f, .115f, .055f, 1));
            painted[n] = m;
            return m;
        }

        void LateUpdate()
        {
            Setup();
            if (!prop || !visible || !gameObject.activeInHierarchy) { Blocked = false; if (prop && prop.gameObject.activeSelf && !visible) prop.gameObject.SetActive(false); return; }
            float dt = Mathf.Max(Time.deltaTime, 1e-4f);
            var delta = transform.position - lastPosition; delta.y = 0; lastPosition = transform.position;
            float speed = delta.magnitude / dt;
            var facing = -transform.forward; facing.y = 0; if (facing.sqrMagnitude < .01f) facing = lastFacing; facing.Normalize(); lastFacing = facing;
            bool moving = speed > .08f && delta.magnitude < 1f;
            still = moving ? 0 : still + dt;
            // Groceries: one (basket) or two (cart) per product picked.
            int picks = anim ? anim.Picks - picksAtStart : 0;
            int show = Mathf.Clamp(picks * (cart ? 2 : 1), 0, goods.Count);
            for (int i = 0; i < goods.Count; i++) if (goods[i].activeSelf != (i < show)) goods[i].SetActive(i < show);
            if (cart) Cart(facing, moving, dt); else Basket(facing, speed, dt);
        }

        // ------------------------------------------------------------------ cart
        Vector3 LocalGripMid => (gripL.localPosition + gripR.localPosition) * .5f;

        // Pushing: the handle out in front of the belly, at a height the (short) arms reach with the elbows a
        // little bent and pointing down and out; each hand takes the grip on its own side (the rig's "_L" bones
        // are on the character's right, so sides come from positions, not names).
        // Parking: once they stop (picking a product, queueing) the cart is left beside them, parallel to the
        // way they were walking and clear of the body, and stays put until they walk on.
        bool parked; Vector3 parkPosition; Quaternion parkRotation;

        float ArmLength(Transform upper, Transform fore, Transform hand) =>
            upper && fore && hand ? Vector3.Distance(upper.position, fore.position) + Vector3.Distance(fore.position, hand.position) : .5f * size;

        void Cart(Vector3 facing, bool moving, float dt)
        {
            bool busy = anim && anim.Busy;
            bool park = busy || still > .45f;
            var right = Vector3.Cross(Vector3.up, facing).normalized;
            var floor = transform.position;
            float scale = prop.localScale.x;
            float length = (front ? Mathf.Abs(front.localPosition.z) : 1) * scale;
            var pushRotation = Quaternion.LookRotation(-facing);
            // Where the hands can comfortably reach: 88% of the arm length from the shoulders.
            float arm = Mathf.Min(ArmLength(upperL, foreL, handL), ArmLength(upperR, foreR, handR));
            float shoulderY = upperL && upperR ? (upperL.position.y + upperR.position.y) * .5f - floor.y : 1.45f * size;
            var grips = LocalGripMid * scale;
            float drop = Mathf.Max(.05f, shoulderY - grips.y);
            float halfGap = gripL && gripR ? Mathf.Abs(gripL.localPosition.x - gripR.localPosition.x) * .5f * scale : .2f;
            float shoulderHalf = upperL && upperR ? Vector3.Distance(upperL.position, upperR.position) * .5f : .27f * size;
            float lateral = Mathf.Abs(shoulderHalf - halfGap);
            float reach = Mathf.Sqrt(Mathf.Max(.04f, arm * arm * .88f * .88f - drop * drop - lateral * lateral));
            reach = Mathf.Max(reach, .34f * size); // never inside the belly
            var pushPosition = floor + facing * reach - pushRotation * new Vector3(grips.x, 0, grips.z);
            // Never into furniture or walls: pull the cart back along the way it points.
            if (front && NavMesh.SamplePosition(floor, out var here, .6f, NavMesh.AllAreas))
            {
                var nose = pushPosition + pushRotation * (front.localPosition * scale); nose.y = here.position.y;
                if (NavMesh.Raycast(here.position, nose, out var hit, NavMesh.AllAreas))
                {
                    float over = Vector3.Distance(hit.position, nose) + .05f;
                    pushPosition -= facing * Mathf.Min(over, reach * .5f);
                }
            }
            Vector3 targetPosition; Quaternion targetRotation;
            if (park)
            {
                if (!parked)
                {
                    // Beside them, the cart's middle level with the body, pointing the way they came.
                    parked = true;
                    var dir = placed ? cartRotation * Vector3.back : facing; dir.y = 0; dir = dir.sqrMagnitude > .01f ? dir.normalized : facing;
                    var side = Vector3.Cross(Vector3.up, dir).normalized;
                    float clear = .34f * size + .3f * scale + .12f;
                    parkRotation = Quaternion.LookRotation(-dir);
                    Vector3 Spot(float s) => floor + side * s * clear - dir * (length * .5f - .1f);
                    // All four corners of the cart must be on open floor (no shelf, wall or building).
                    bool Fits(Vector3 origin)
                    {
                        float w = .3f * scale;
                        foreach (var c in new[] { new Vector3(w, 0, 0), new Vector3(-w, 0, 0), new Vector3(w, 0, -length), new Vector3(-w, 0, -length), new Vector3(0, 0, -length * .5f) })
                            if (!Free(floor, origin + parkRotation * c, true)) return false;
                        return true;
                    }
                    parkPosition = Spot(1);
                    if (!Fits(parkPosition)) parkPosition = Spot(-1);
                    if (!Fits(parkPosition))
                    {
                        // No room beside them: leave it right behind, in line with the way they came.
                        parkPosition = floor - dir * (.34f * size + .25f);
                        parkRotation = Quaternion.LookRotation(dir);
                        if (!Fits(parkPosition)) { parkPosition = placed ? cartPosition : pushPosition; parkRotation = placed ? cartRotation : pushRotation; }
                    }
                }
                float k = placed ? 1 - Mathf.Exp(-dt * 6) : 1;
                targetPosition = Vector3.Lerp(cartPosition, parkPosition, k);
                targetRotation = Quaternion.Slerp(cartRotation, parkRotation, k);
                attach = Mathf.MoveTowards(attach, 0, dt * 5);
            }
            else
            {
                parked = false;
                // Take it again: hands first (attach), the cart swings back in front quickly.
                float k = placed ? 1 - Mathf.Exp(-dt * (attach > .9f ? 18 : 9)) : 1;
                targetPosition = Vector3.Lerp(cartPosition, pushPosition, k);
                targetRotation = Quaternion.Slerp(cartRotation, pushRotation, k);
                attach = Mathf.MoveTowards(attach, (targetPosition - pushPosition).sqrMagnitude < .05f ? 1 : .5f, dt * 4);
            }
            targetPosition.y = floor.y;
            cartPosition = targetPosition; cartRotation = targetRotation; placed = true;
            prop.SetPositionAndRotation(cartPosition, cartRotation);
            // Wheels bounce a hair on the tiles.
            if (moving) prop.position += Vector3.up * Mathf.Abs(Mathf.Sin(Time.time * 17)) * .004f;
            // Hands on the grips of their own side, elbows down and out.
            if (attach > .01f && gripL && gripR)
            {
                void Hand(Transform upper, Transform fore, Transform hand)
                {
                    if (!upper || !fore || !hand) return;
                    float sideSign = Mathf.Sign(Vector3.Dot(upper.position - floor, right)); if (sideSign == 0) sideSign = 1;
                    var grip = Vector3.Dot(gripL.position - floor, right) * sideSign > Vector3.Dot(gripR.position - floor, right) * sideSign ? gripL : gripR;
                    var pole = upper.position + right * sideSign * .45f - Vector3.up * .5f - facing * .05f;
                    ArmIK(upper, fore, hand, grip.position + Vector3.up * .02f, pole, attach);
                }
                Hand(upperL, foreL, handL);
                Hand(upperR, foreR, handR);
            }
            // People (and parked carts) in front of the cart: slow down instead of running them over.
            Blocked = false;
            if (!park)
            {
                var inverse = Quaternion.Inverse(cartRotation);
                float half = .38f * size;
                foreach (var walker in CheckoutWalkersNearby())
                {
                    var local = inverse * (walker - cartPosition);
                    if (Mathf.Abs(local.x) < half + .25f && local.z < .15f && local.z > -length - .35f) { Blocked = true; break; }
                }
            }
        }

        IEnumerable<Vector3> CheckoutWalkersNearby()
        {
            foreach (var other in all)
            {
                if (!other || other == this || !other.isActiveAndEnabled) continue;
                var p = other.transform.position;
                if ((p - transform.position).sqrMagnitude < 9) yield return p;
                if (other.cart && other.prop && other.prop.gameObject.activeSelf && (other.cartPosition - transform.position).sqrMagnitude < 9) yield return other.cartPosition + other.cartRotation * Vector3.back * .45f * other.size;
            }
        }

        static bool Free(Vector3 from, Vector3 to, bool strict = false)
        {
            if (!NavMesh.SamplePosition(from, out var a, .6f, NavMesh.AllAreas)) return !strict;
            if (NavMesh.Raycast(a.position, new Vector3(to.x, a.position.y, to.z), out _, NavMesh.AllAreas)) return false;
            // The point itself must be on the walkable floor, not just reachable in a straight line.
            return !strict || NavMesh.SamplePosition(new Vector3(to.x, a.position.y, to.z), out var b, .15f, NavMesh.AllAreas);
        }

        // ------------------------------------------------------------------ basket
        // Hanging from the hand at the side, arm almost straight and a little away from the body so the
        // basket clears the hip and the leg; it swings forward and back with the steps and the arm follows.
        void Basket(Vector3 facing, float speed, float dt)
        {
            if (!upperL || !foreL || !handL) return;
            var root = transform.position;
            var right = Vector3.Cross(Vector3.up, facing).normalized;
            float sign = Mathf.Sign(Vector3.Dot(upperL.position - root, right)); if (sign == 0) sign = 1;
            var outward = right * sign;
            float upper = Vector3.Distance(upperL.position, foreL.position), lower = Vector3.Distance(foreL.position, handL.position);
            float reach = (upper + lower) * .96f;
            float shoulderOut = Vector3.Dot(upperL.position - root, outward);
            float legOut = (thighL ? Vector3.Dot(thighL.position - root, outward) : .15f * size) + .16f * size;
            float basketHalf = .17f * prop.localScale.x;
            float lateral = Mathf.Clamp(legOut + basketHalf + .02f - shoulderOut, .05f, reach * .6f);
            // Pendulum: pushed by the walk, damped.
            float push = Mathf.Sin(Time.time * 7.5f) * Mathf.Clamp01(speed) * 9;
            swingVelocity += (push - swing * 40 - swingVelocity * 5) * dt; swing += swingVelocity * dt * 8;
            swing = Mathf.Clamp(swing, -14, 14);
            float forward = .03f * size + Mathf.Sin(swing * Mathf.Deg2Rad) * reach * .35f;
            float drop = Mathf.Sqrt(Mathf.Max(.01f, reach * reach - lateral * lateral - forward * forward));
            var target = upperL.position + outward * lateral + facing * forward + Vector3.down * drop;
            // Elbow slightly back and out, never into the body.
            ArmIK(upperL, foreL, handL, target, upperL.position - facing * .35f + outward * .35f - Vector3.up * .3f, 1);
            // Long side along the walk, handle bar in the hand.
            var rotation = Quaternion.LookRotation(facing) * Quaternion.Euler(0, -90, 0) * Quaternion.Euler(0, 0, swing);
            var gripOffset = grip ? grip.localPosition * prop.localScale.x : Vector3.zero;
            prop.SetPositionAndRotation(handL.position - rotation * gripOffset - Vector3.up * .03f, rotation);
        }

        // Two-bone IK: turns the upper arm and forearm so the hand reaches `target`, elbow toward `pole`.
        static void ArmIK(Transform upper, Transform fore, Transform hand, Vector3 target, Vector3 pole, float weight)
        {
            if (!upper || !fore || !hand || weight <= 0) return;
            Vector3 a = upper.position, b = fore.position, c = hand.position;
            float la = (b - a).magnitude, lb = (c - b).magnitude;
            if (la < 1e-4f || lb < 1e-4f) return;
            var goal = Vector3.Lerp(c, target, weight);
            var dir = goal - a; float d = Mathf.Clamp(dir.magnitude, .02f, la + lb - .001f); dir.Normalize();
            float along = (la * la - lb * lb + d * d) / (2 * d), h = Mathf.Sqrt(Mathf.Max(0, la * la - along * along));
            var bend = Vector3.ProjectOnPlane(pole - a, dir); if (bend.sqrMagnitude < 1e-6f) bend = Vector3.down; bend.Normalize();
            var elbow = a + dir * along + bend * h;
            upper.rotation = Quaternion.FromToRotation(b - a, elbow - a) * upper.rotation;
            fore.rotation = Quaternion.FromToRotation(hand.position - fore.position, (a + dir * d) - fore.position) * fore.rotation;
        }
    }
}
