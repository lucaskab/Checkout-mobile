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
            if (umbrella && umbrellaPrefab != prefab) { Destroy(umbrella); umbrella = null; }   // another model (QA preview)
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
            rimHeight = umbrellaPrefab.name.Contains("V2") ? .85f : .93f;
            // the chunky rigs are ~2.5 m tall with big heads: their umbrella is sized up to match (1.55 m across)
            if (umbrellaPrefab.name.Contains("V2")) UmbrellaScale = 1.35f;
            // the wrist as the model was bound (its bind pose): straight, the fist closed around the shaft
            if (forearm && hand) handRestLocal = BindLocal(forearm, hand) ?? Quaternion.Inverse(forearm.rotation) * hand.rotation;
            if (head) headTop = MeasureHeadTop();

            if (!umbrella)
            {
                // a holder at the grip with the shaft along its up axis; the model keeps its own import rotation inside
                // (Blender FBX files come in turned -90° about X)
                umbrella = new GameObject("Rain umbrella");
                umbrella.transform.SetParent(transform, false);
                umbrella.transform.localScale = Vector3.one * UmbrellaScale;
                Instantiate(umbrellaPrefab, umbrella.transform, false).name = umbrellaPrefab.name;
                if (umbrellaPrefab.name.Contains("V2")) Tint(umbrella, TintFor(GetEntityId().GetHashCode()));
                else ApplyColorfulMaterial(umbrella);
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

            // The rigs look along -forward. The hand holds the shaft beside the face on its own side, forearm upright
            // and elbow down and out; the shaft leans towards the head so the canopy is centred over it, and the hand
            // rises as far as needed for the canopy rim to clear the hair (the chunky rigs have big heads).
            Vector3 headPosition = head ? head.position : BoundsHeadPosition();
            Vector3 face = -transform.forward; face.y = 0; face = face.sqrMagnitude > .001f ? face.normalized : Vector3.forward;
            float scale = umbrella.transform.lossyScale.y;
            float hairTop = headPosition.y + headTop;
            Vector3 grip = headPosition - Vector3.up * .3f + face * .3f;
            Vector3 axis = Vector3.up;
            if (upperArm && forearm && hand)
            {
                Vector3 side = transform.right * Mathf.Sign(transform.InverseTransformPoint(upperArm.position).x);
                Vector3 shoulder = upperArm.position;
                // A natural hold: elbow down, out and a little forward, forearm upright, the fist at about shoulder
                // height. The upper arm only lifts (towards level) as far as the canopy needs to clear the hair, and
                // swings out until the shaft stands clear of the big heads.
                Vector3 elbow = shoulder, wanted = grip;
                for (int step = 0; step <= 8; step++)
                {
                    float lift = step / 8f;
                    Vector3 elbowDir = (-Vector3.up * Mathf.Lerp(.75f, .15f, lift) + side * Mathf.Lerp(.42f, .62f, lift) + face * .5f).normalized;
                    elbow = shoulder + elbowDir * upperArmLength;
                    wanted = elbow + (Vector3.up * .95f + face * .12f).normalized * forearmLength;
                    float clear = Vector3.Dot(Vector3.ProjectOnPlane(wanted - headPosition, Vector3.up), side);
                    if (clear < ShaftOffset) { wanted += side * (ShaftOffset - clear); }
                    if (wanted.y + rimHeight * scale >= hairTop + .08f) break;
                }
                axis = ShaftAxis(wanted, headPosition);
                Quaternion handBefore = hand.rotation;
                Aim(upperArm, forearm, elbow - shoulder);
                Aim(forearm, hand, wanted - forearm.position);
                // the wrist stays straight (bind pose), without the bend the walk gives it
                Vector3 forearmAxis = (hand.position - forearm.position).normalized;
                hand.rotation = Quaternion.Slerp(handBefore, Quaternion.AngleAxis(HandTwist, forearmAxis) * forearm.rotation * handRestLocal, shelterWeight);
                // the shaft passes through the middle of the palm, and the fingers close around it
                grip = PalmCentre();
                CloseFist(grip, axis);
            }
            else axis = ShaftAxis(grip, headPosition);

            Quaternion rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(face, axis), axis);
            umbrella.transform.position = grip;
            umbrella.transform.rotation = rotation;
            if (!umbrella.activeSelf) umbrella.SetActive(true);
        }

        // Middle of the palm: a little way from the wrist towards the knuckles (the first joint of the longest finger).
        Vector3 PalmCentre()
        {
            if (fingers == null) fingers = FindFingers();
            Vector3 knuckles = Vector3.zero; int count = 0;
            foreach (var chain in fingers) if (!chain.thumb && chain.bones.Length > 0) { knuckles += chain.bones[0].position; count++; }
            return count > 0 ? Vector3.Lerp(hand.position, knuckles / count, .55f) : hand.position;
        }

        // Each finger joint turns towards the shaft so the hand wraps it (the walk animation leaves them open).
        void CloseFist(Vector3 grip, Vector3 axis)
        {
            if (fingers == null) return;
            foreach (var chain in fingers)
            {
                float[] curl = chain.thumb ? new[] { 25f, 30f, 20f } : new[] { 55f, 70f, 50f };
                for (int i = 0; i < chain.bones.Length; i++)
                {
                    var bone = chain.bones[i];
                    var tip = i + 1 < chain.bones.Length ? chain.bones[i + 1] : (bone.childCount > 0 ? bone.GetChild(0) : null);
                    if (!tip) continue;
                    Vector3 along = tip.position - bone.position;
                    // the point of the shaft level with this joint
                    Vector3 onShaft = grip + axis * Vector3.Dot(bone.position - grip, axis);
                    Vector3 hinge = Vector3.Cross(along, onShaft - bone.position);
                    if (hinge.sqrMagnitude < 1e-8f) continue;
                    float angle = curl[Mathf.Min(i, curl.Length - 1)] * shelterWeight;
                    bone.rotation = Quaternion.AngleAxis(angle, hinge.normalized) * bone.rotation;
                }
            }
        }

        sealed class Finger { public Transform[] bones; public bool thumb; }
        Finger[] fingers;
        Finger[] FindFingers()
        {
            var found = new System.Collections.Generic.List<Finger>();
            foreach (Transform child in hand)
            {
                var chain = new System.Collections.Generic.List<Transform>();
                for (var bone = child; bone && chain.Count < 3; bone = bone.childCount > 0 ? bone.GetChild(0) : null) chain.Add(bone);
                if (chain.Count == 0 || child.GetComponent<Renderer>()) continue;
                found.Add(new Finger { bones = chain.ToArray(), thumb = Normalize(child.name).Contains("thumb") });
            }
            return found.ToArray();
        }

        // The shaft stands nearly upright, leaning a few degrees towards the head so the canopy reaches over it.
        const float ShaftOffset = .4f;
        /// <summary>Turn of the hand about the forearm (the rigs have no finger bones: the open hand faces the shaft).</summary>
        public static float HandTwist = 180f;
        float UmbrellaScale = 1f;
        Vector3 ShaftAxis(Vector3 grip, Vector3 headPosition)
        {
            Vector3 toHead = Vector3.ProjectOnPlane(headPosition - grip, Vector3.up);
            return toHead.sqrMagnitude < .0001f ? Vector3.up : Vector3.RotateTowards(Vector3.up, toHead.normalized, 7f * Mathf.Deg2Rad, 0);
        }

        // Height of the canopy rim above the grip: .85 m in RainUmbrellaV2 (scripts/blender/build_umbrella_v2.py),
        // .93 m in the first umbrella (scripts/blender/build_props.py).
        float rimHeight = .93f;
        Quaternion handRestLocal = Quaternion.identity;

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

        // One solid colour per person (RainUmbrellaV2's canopy is near-white with shaded seams, made to be tinted).
        // hand rotation relative to the forearm in the skin's bind pose
        Quaternion? BindLocal(Transform parent, Transform child)
        {
            foreach (var skinned in animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var bones = skinned.bones; var poses = skinned.sharedMesh ? skinned.sharedMesh.bindposes : null;
                if (bones == null || poses == null) continue;
                int a = System.Array.IndexOf(bones, parent), b = System.Array.IndexOf(bones, child);
                if (a < 0 || b < 0 || a >= poses.Length || b >= poses.Length) continue;
                Quaternion parentWorld = poses[a].inverse.rotation, childWorld = poses[b].inverse.rotation;
                return Quaternion.Inverse(parentWorld) * childWorld;
            }
            return null;
        }

        static readonly Color[] Tints = { C(0xE04B3A), C(0x2E4A7D), C(0xF2C230), C(0x4FA36B), C(0x2FA3A3), C(0xE97AA2), C(0x8A5BB8), C(0x2B2B2E) };
        static Color C(int rgb) => new Color(((rgb >> 16) & 255) / 255f, ((rgb >> 8) & 255) / 255f, (rgb & 255) / 255f);
        static Color TintFor(int seed) => Tints[Mathf.Abs(seed) % Tints.Length];
        static void Tint(GameObject target, Color color)
        {
            foreach (var renderer in target.GetComponentsInChildren<Renderer>(true))
            {
                var materials = renderer.materials;
                for (int i = 0; i < materials.Length; i++)
                    if (materials[i] && materials[i].name.StartsWith("Canopy"))
                    {
                        var shader = Shader.Find("Checkout/TintedVertexColor");
                        if (shader) { materials[i] = new Material(shader) { name = "Canopy (tinted)" }; materials[i].SetFloat("_Glossiness", .3f); }
                        if (materials[i].HasProperty("_Color")) materials[i].SetColor("_Color", color);
                        if (materials[i].HasProperty("_BaseColor")) materials[i].SetColor("_BaseColor", color);
                    }
                renderer.materials = materials;
            }
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
