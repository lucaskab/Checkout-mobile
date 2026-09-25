using System.Linq;
using UnityEngine;

namespace MarketDay
{
    [DefaultExecutionOrder(200)]
    public sealed class MarketRainUmbrellaRig : MonoBehaviour
    {
        Animation animationPlayer;
        GameObject umbrellaPrefab;
        GameObject umbrella;
        Transform upperArm;
        Transform forearm;
        Transform hand;
        Transform head;
        Renderer[] bodyRenderers;
        float upperArmLength;
        float forearmLength;
        float headTop = .55f;
        float shelterWeight;
        bool sheltering;
        public bool HasVisibleUmbrella => umbrella && umbrella.activeInHierarchy;
        public bool HasRightHandRig => upperArm && forearm && hand && IsRightSide(hand.name);
        public bool ForearmIsUpright => forearm && hand && Vector3.Dot((hand.position - forearm.position).normalized, Vector3.up) > .5f;
        public bool IsShelteringHead
        {
            get
            {
                if (!umbrella) return false;
                var renderer = umbrella.GetComponentInChildren<Renderer>();
                if (!renderer) return false;
                var bounds = renderer.bounds;
                Vector3 headPosition = head ? head.position : BoundsHeadPosition();
                return bounds.center.y >= headPosition.y - .05f
                    && Mathf.Abs(bounds.center.x - headPosition.x) <= bounds.extents.x
                    && Mathf.Abs(bounds.center.z - headPosition.z) <= bounds.extents.z;
            }
        }

        public void Initialize(Animation player, GameObject prefab)
        {
            if (animationPlayer == player && umbrellaPrefab == prefab && (umbrella || !prefab)) return;
            animationPlayer = player;
            umbrellaPrefab = prefab;
            if (!animationPlayer || !umbrellaPrefab) return;

            upperArm = FindRightArmBone(animationPlayer.transform, true);
            forearm = FindRightArmBone(animationPlayer.transform, false);
            hand = FindRightHand(animationPlayer.transform);
            head = FindHead(animationPlayer.transform);
            if (upperArm && forearm && hand)
            {
                upperArmLength = Vector3.Distance(upperArm.position, forearm.position);
                forearmLength = Vector3.Distance(forearm.position, hand.position);
            }
            bodyRenderers = animationPlayer.GetComponentsInChildren<Renderer>(true);
            if (head) headTop = MeasureHeadTop();

            if (!umbrella)
            {
                umbrella = Instantiate(umbrellaPrefab, transform);
                umbrella.name = "Rain umbrella";
                                ApplyColorfulMaterial(umbrella);
                umbrella.SetActive(false);
            }
        }

        public void SetRainShelter(bool value)
        {
            sheltering = value;
            if (value && umbrella) umbrella.SetActive(true);
        }

        void LateUpdate()
        {
            shelterWeight = Mathf.MoveTowards(shelterWeight, sheltering ? 1 : 0, Time.deltaTime * 2.5f);
            if (!umbrella || !animationPlayer || shelterWeight <= .001f)
            {
                if (!sheltering && shelterWeight <= .001f && umbrella) umbrella.SetActive(false);
                return;
            }

            // The rigs look along -forward. The grip sits at chin height, in front of the shoulder and a bit inwards,
            // with the elbow down and out, like someone walking with an umbrella.
            Vector3 headPosition = head ? head.position : BoundsHeadPosition();
            Vector3 face = -transform.forward;
            Vector3 grip = headPosition - Vector3.up * .2f + face * .3f;
            if (upperArm && forearm && hand)
            {
                Vector3 side = transform.right * Mathf.Sign(transform.InverseTransformPoint(upperArm.position).x);
                Vector3 shoulder = upperArm.position;
                grip = shoulder + Vector3.up * .08f + face * .3f - side * .08f;
                Vector3 toGrip = grip - shoulder;
                float reach = Mathf.Clamp(toGrip.magnitude, Mathf.Abs(upperArmLength - forearmLength) + .01f, upperArmLength + forearmLength - .01f);
                Vector3 direction = toGrip.normalized;
                Vector3 pole = Vector3.ProjectOnPlane(side * .5f - Vector3.up, direction).normalized;
                float cos = Mathf.Clamp((upperArmLength * upperArmLength + reach * reach - forearmLength * forearmLength) / (2 * upperArmLength * reach), -1, 1);
                Vector3 elbow = shoulder + direction * upperArmLength * cos + pole * upperArmLength * Mathf.Sqrt(1 - cos * cos);
                Aim(upperArm, forearm, elbow - shoulder);
                Aim(forearm, hand, grip - forearm.position);
                grip = hand.position;
            }

            // The shaft leans a little towards the head so the canopy stays centred over it.
            Vector3 lean = Vector3.ProjectOnPlane(headPosition - grip, Vector3.up) * .35f;
            Quaternion rotation = Quaternion.FromToRotation(Vector3.up, (Vector3.up + lean).normalized) * Quaternion.LookRotation(face, Vector3.up);
            // The hand slides up the long shaft when the canopy rim would touch the hair (the big heads vary a lot).
            Vector3 axis = rotation * Vector3.up;
            Vector3 rim = grip + axis * RimHeight * umbrella.transform.lossyScale.y;
            Vector3 top = headPosition + Vector3.up * (headTop + .06f);
            float rimAtHead = rim.y - (axis.x * (top.x - rim.x) + axis.z * (top.z - rim.z)) / axis.y;
            umbrella.transform.position = grip - axis * Mathf.Clamp((rimAtHead - top.y) * axis.y, -.35f, 0);
            umbrella.transform.rotation = rotation;
            if (!umbrella.activeSelf) umbrella.SetActive(true);
        }

        // Height of the canopy rim above the grip, in the umbrella model (scripts/blender/build_props.py).
        const float RimHeight = .93f;

        // Highest point of the skinned body (hair included) above the head bone, from one baked pose.
        float MeasureHeadTop()
        {
            float top = float.MinValue;
            var baked = new Mesh();
            foreach (var skinned in animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                if (!skinned.enabled || skinned.name.EndsWith("_Prop")) continue;
                skinned.BakeMesh(baked, true);
                foreach (var vertex in baked.vertices) top = Mathf.Max(top, skinned.transform.TransformPoint(vertex).y);
            }
            Destroy(baked);
            return top > float.MinValue ? Mathf.Clamp(top - head.position.y, .2f, .9f) : .55f;
        }

        static Transform FindRightArmBone(Transform root, bool upper)
        {
            foreach (var bone in root.GetComponentsInChildren<Transform>(true))
            {
                string key = Normalize(bone.name);
                if (!IsRightSide(bone.name)) continue;
                bool isUpper = key.Contains("upperarm") || key.EndsWith("rightarm") || key.EndsWith("armr");
                bool isForearm = key.Contains("forearm") || key.Contains("lowerarm");
                if (upper ? isUpper : isForearm) return bone;
            }
            return null;
        }

        static Transform FindRightHand(Transform root)
        {
            foreach (var bone in root.GetComponentsInChildren<Transform>(true))
            {
                string key = Normalize(bone.name);
                if (IsRightSide(bone.name) && key.Contains("hand") && (key.EndsWith("hand") || key.EndsWith("handr"))) return bone;
            }
            return null;
        }

        static Transform FindHead(Transform root)
        {
            foreach (var bone in root.GetComponentsInChildren<Transform>(true))
                if (Normalize(bone.name) == "head" || Normalize(bone.name).EndsWith("head")) return bone;
            return null;
        }

        static string Normalize(string value) => string.Concat(value.ToLowerInvariant().Where(char.IsLetterOrDigit));
        static bool IsRightSide(string name)
        {
            string key = Normalize(name);
            return key.Contains("right") || key.EndsWith("r");
        }

        static void ApplyColorfulMaterial(GameObject target)
        {
            var source = target.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).FirstOrDefault(m => m && m.mainTexture);
            if (!source) return;
            foreach (var renderer in target.GetComponentsInChildren<Renderer>(true))
            {
                var materials = renderer.materials;
                for (int i = 0; i < materials.Length; i++)
                {
                    var material = materials[i];
                    if (!material || !material.mainTexture) materials[i] = material = new Material(source);
                    if (material.HasProperty("_Color")) material.SetColor("_Color", Color.white);
                    if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", Color.white);
                }
                renderer.materials = materials;
            }
        }

        Vector3 BoundsHeadPosition()
        {
            Bounds bounds = new Bounds(animationPlayer.transform.position, Vector3.zero);
            bool hasBounds = false;
            foreach (var renderer in bodyRenderers)
            {
                if (!renderer || !renderer.enabled || renderer.name.EndsWith("_Prop")) continue;
                if (!hasBounds) { bounds = renderer.bounds; hasBounds = true; }
                else bounds.Encapsulate(renderer.bounds);
            }
            if (!hasBounds) return animationPlayer.transform.position + Vector3.up * 1.35f;
            return new Vector3(bounds.center.x, bounds.max.y - .16f, bounds.center.z);
        }

        void Aim(Transform bone, Transform child, Vector3 desiredDirection)
        {
            Vector3 current = child.position - bone.position;
            if (current.sqrMagnitude < .0001f || desiredDirection.sqrMagnitude < .0001f) return;
            Quaternion aimed = Quaternion.FromToRotation(current, desiredDirection) * bone.rotation;
            bone.rotation = Quaternion.Slerp(bone.rotation, aimed, shelterWeight);
        }
    }
}
