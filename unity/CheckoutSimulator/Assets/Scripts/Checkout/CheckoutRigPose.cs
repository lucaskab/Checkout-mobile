using System.Collections.Generic;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    // A city character rig driven by hand: Blender clips are sampled manually and bones can then be
    // re-aimed (sitting, pedalling). Bones point down their local -Y; the figure faces root -Z.
    public class CheckoutRigPose
    {
        public Transform root, visual;
        public Animation clips;
        public Transform torso, head;
        public Transform[] thigh = new Transform[2], shin = new Transform[2], foot = new Transform[2];
        public Transform[] upperArm = new Transform[2], forearm = new Transform[2], hand = new Transform[2];
        public float walkCycle = .733f, walkPhase;

        static MarketCharacterAnimator[] templates;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetTemplates() { templates = null; }

        public static CheckoutRigPose Spawn(Transform parent, string name)
        {
            if (templates == null)
            {
                var source = Object.FindAnyObjectByType<CheckoutCityAppearance>(FindObjectsInactive.Include);
                templates = source ? source.templates : new MarketCharacterAnimator[0];
            }
            if (templates.Length == 0) return null;
            var template = templates[Random.Range(0, templates.Length)];
            var player = template.animationPlayer;
            var pose = new CheckoutRigPose { root = new GameObject(name).transform, walkCycle = template.walkCycleDistance };
            pose.root.SetParent(parent, false);
            var visual = Object.Instantiate(player.gameObject, pose.root);
            visual.transform.localPosition = template.transform.InverseTransformPoint(player.transform.position);
            visual.transform.localRotation = Quaternion.Inverse(template.transform.rotation) * player.transform.rotation;
            visual.SetActive(true);
            foreach (var r in visual.GetComponentsInChildren<Renderer>(true)) r.enabled = !r.name.EndsWith("_Prop");
            pose.visual = visual.transform;
            pose.clips = visual.GetComponent<Animation>();
            pose.clips.enabled = false; // sampled by hand
            var bones = new Dictionary<string, Transform>();
            foreach (var t in visual.GetComponentsInChildren<Transform>(true)) bones[t.name] = t;
            Transform B(string n) => bones.TryGetValue(n, out var t) ? t : null;
            pose.torso = B("Torso"); pose.head = B("Head");
            for (int i = 0; i < 2; i++)
            {
                string s = i == 0 ? "_L" : "_R";
                pose.thigh[i] = B("Thigh" + s); pose.shin[i] = B("Shin" + s); pose.foot[i] = B("Foot" + s);
                pose.upperArm[i] = B("UpperArm" + s); pose.forearm[i] = B("Forearm" + s); pose.hand[i] = B("Hand" + s);
            }
            return pose.torso && pose.thigh[1] && pose.hand[1] ? pose : Discard(pose);
        }

        static CheckoutRigPose Discard(CheckoutRigPose pose) { Object.Destroy(pose.root.gameObject); return null; }

        public void Sample(string clip, float normalizedTime)
        {
            var state = clips[clip];
            if (state) state.clip.SampleAnimation(clips.gameObject, Mathf.Repeat(normalizedTime, 1) * state.length);
        }

        // Walking clip keyed by distance travelled, like MarketCharacterAnimator.
        public void Walk(float distance)
        {
            walkPhase = Mathf.Repeat(walkPhase + distance / Mathf.Max(.1f, walkCycle), 1);
            Sample("Walking", walkPhase);
        }

        public static void Aim(Transform bone, Vector3 direction)
        {
            var down = bone.rotation * Vector3.down;
            bone.rotation = Quaternion.FromToRotation(down, direction.normalized) * bone.rotation;
        }

        // Two-bone IK: bends upper/lower so the end joint reaches target, the middle joint towards pole.
        public static void Reach(Transform upper, Transform lower, Transform end, Vector3 target, Vector3 pole)
        {
            Vector3 a = upper.position;
            float l1 = Vector3.Distance(a, lower.position), l2 = Vector3.Distance(lower.position, end.position);
            Vector3 toTarget = target - a;
            float d = Mathf.Clamp(toTarget.magnitude, .01f, (l1 + l2) * .999f);
            Vector3 axis = toTarget.normalized;
            Vector3 bend = Vector3.ProjectOnPlane(pole, axis).normalized;
            if (bend.sqrMagnitude < .5f) bend = Vector3.ProjectOnPlane(Vector3.forward, axis).normalized;
            float along = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
            float up = Mathf.Sqrt(Mathf.Max(0, l1 * l1 - along * along));
            Vector3 middle = a + axis * along + bend * up;
            Aim(upper, middle - a);
            Aim(lower, a + axis * d - lower.position);
        }

        public Vector3 Forward => -root.forward;
        public Vector3 Right => -root.right;
    }
}
