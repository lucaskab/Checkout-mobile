using UnityEngine;

namespace Checkout
{
    /// <summary>
    /// The construction crew (Lucas 12/10): every character working on a building site — expansion works, lot clearing,
    /// interior works and the street events with someone working — is one of the two construction workers,
    /// Worker_ConstructionM (man) and Worker_ConstructionF (woman), alternating by variant.
    /// The models live in Resources/CheckoutCrew (built by ArtSource/NPCs/build_npcs.py on the market worker's skeleton,
    /// so every clip and bone the old crew used is there), with their own Hammer and Sledge clips for the tool work.
    /// The crew is still cloned from the market's delivery worker (its scale and placement); only its Visual is swapped.
    /// </summary>
    public static class CheckoutCrew
    {
        static readonly string[] Looks = { "Worker_ConstructionM", "Worker_ConstructionF" };
        static GameObject[] models;
        static Material[] materials;
        static Transform templates;

        static bool Load()
        {
            if (models == null)
            {
                models = new GameObject[Looks.Length]; materials = new Material[Looks.Length];
                for (int i = 0; i < Looks.Length; i++)
                {
                    models[i] = Resources.Load<GameObject>("CheckoutCrew/" + Looks[i]);
                    materials[i] = Resources.Load<Material>("CheckoutCrew/" + Looks[i]);
                }
            }
            return models[0] && models[1];
        }

        /// <summary>Replaces the Visual of a worker clone by a construction worker (variant alternates man / woman).
        /// Returns false (and leaves the clone as it was) if the crew models are not in the build.</summary>
        public static bool Dress(GameObject clone, int variant)
        {
            if (!clone || !Load()) return false;
            int look = Mathf.Abs(variant) % Looks.Length;
            Transform old = null;
            foreach (var t in clone.GetComponentsInChildren<Transform>(true)) if (t.name == "Visual") { old = t; break; }
            var parent = old ? old.parent : clone.transform;
            var visual = Object.Instantiate(models[look], parent, false);
            visual.name = "Visual";
            if (old)
            {
                visual.transform.localPosition = old.localPosition;
                visual.transform.localRotation = old.localRotation;
                visual.transform.localScale = old.localScale;
                visual.layer = old.gameObject.layer;
                Object.DestroyImmediate(old.gameObject);
            }
            else visual.transform.localRotation = Quaternion.Euler(0, 180, 0);
            foreach (var r in visual.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (materials[look]) r.sharedMaterial = materials[look];
                r.updateWhenOffscreen = true; r.enabled = true;
            }
            foreach (var t in visual.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = visual.layer;
            var anim = visual.GetComponent<Animation>();
            if (anim) { anim.playAutomatically = false; anim.cullingType = AnimationCullingType.AlwaysAnimate; anim.enabled = true; }
            return true;
        }

        /// <summary>A hidden construction worker to copy from (CheckoutEventAssets.Actor takes a template character):
        /// the market's delivery worker dressed as one of the crew. Null if the crew or the delivery worker is missing.</summary>
        public static Transform Template(int variant)
        {
            if (!Load()) return null;
            if (!templates)
            {
                templates = new GameObject("Crew templates").transform;
                templates.gameObject.SetActive(false);
                Object.DontDestroyOnLoad(templates.gameObject);
            }
            string name = "Crew " + (Mathf.Abs(variant) % Looks.Length);
            var have = templates.Find(name);
            if (have) return have;
            var source = Object.FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
            if (!source) return null;
            var clone = Object.Instantiate(source.gameObject, templates, false);
            clone.name = name;
            foreach (var b in clone.GetComponentsInChildren<MonoBehaviour>(true)) Object.DestroyImmediate(b);
            foreach (var n in clone.GetComponentsInChildren<UnityEngine.AI.NavMeshAgent>(true)) Object.DestroyImmediate(n);
            foreach (var c in clone.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
            var children = new System.Collections.Generic.List<Transform>();
            foreach (Transform child in clone.transform) children.Add(child);
            foreach (var child in children) if (child.name != "Visual") Object.DestroyImmediate(child.gameObject);
            clone.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            clone.transform.localScale = source.transform.lossyScale;
            Dress(clone, variant);
            clone.SetActive(true);        // active inside the inactive holder: copies come out active
            return clone.transform;
        }

        /// <summary>The character's right hand (the tool hand) and the other one: the rig's L/R names are mirrored,
        /// so the side is taken from where the hands are.</summary>
        public static void Hands(Transform body, Transform a, Transform b, out Transform right, out Transform left)
        {
            if (!a || !b) { right = a ? a : b; left = b ? b : a; return; }
            bool aRight = Vector3.Dot(a.position - body.position, body.right) > Vector3.Dot(b.position - body.position, body.right);
            right = aRight ? a : b; left = aRight ? b : a;
        }
    }
}
