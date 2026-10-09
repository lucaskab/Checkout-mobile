using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Plays one of a market character's own clips (Walking, Idle…) on another rig that shares its skeleton (the
 // inspector of the health inspection, EventRigs/Inspector, has only its Inspect_* clips). A hidden copy of the
 // character samples the clip; the pose is copied bone by bone in the model's own space from the bind poses of both
 // skins, the same way CheckoutEventMoves does, so a different bone axis or import scale does not matter.
 // `Weight` blends with whatever the rig's own Animation set this frame: fading it hands the body over smoothly.
 public sealed class CheckoutClipRetarget : MonoBehaviour {
  static readonly string[] Bones = { "Torso", "Head", "Thigh_L", "Shin_L", "Foot_L", "Thigh_R", "Shin_R", "Foot_R",
   "UpperArm_L", "Forearm_L", "Hand_L", "UpperArm_R", "Forearm_R", "Hand_R" };

  sealed class Pose { public Transform root; public Transform[] bones; public Quaternion[] rest; public Vector3 torso, up, side; public float height; }
  sealed class Source { public GameObject copy; public Animation anim; public Pose pose; }
  static readonly Dictionary<Transform, Source> sources = new Dictionary<Transform, Source>();

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
  static void Reset() { sources.Clear(); }

  Source source; Pose pose; Quaternion map; float scale = 1;
  AnimationClip clip; float time, speed = 1, fade = 4, target;
  public string Clip { get; private set; }
  public float Weight { get; private set; }
  /// <summary>Head-to-hips length of the source character over this rig's (scale the rig by it to match the city's people).</summary>
  public float SizeRatio { get; private set; } = 1;

  /// <summary>Starts (or keeps) `clip` of the character `template` on `rig` (the object holding the rig's skeleton).</summary>
  public static CheckoutClipRetarget Play(GameObject rig, Transform template, string clipName, float speed = 1, float fadeIn = .25f) {
   if (!rig || !template) return null;
   var r = rig.GetComponent<CheckoutClipRetarget>() ?? rig.AddComponent<CheckoutClipRetarget>();
   if (!r.Bind(template)) return null;
   r.Use(clipName, speed, fadeIn);
   return r;
  }

  /// <summary>Hands the body back to the rig's own Animation over `seconds`.</summary>
  public void FadeOut(float seconds = .25f) { target = 0; fade = 1 / Mathf.Max(.01f, seconds); }

  bool Bind(Transform template) {
   if (source != null && source.copy) return true;
   if (!sources.TryGetValue(template, out source) || !source.copy) {
    source = MakeSource(template); if (source == null) return false;
    sources[template] = source;
   }
   pose = Capture(transform);
   if (pose == null) { Debug.LogWarning("CHECKOUT_RETARGET_NO_SKELETON " + name); source = null; return false; }
   map = Basis(pose.up, pose.side) * Quaternion.Inverse(Basis(source.pose.up, source.pose.side));
   scale = pose.height / Mathf.Max(1e-4f, source.pose.height);
   SizeRatio = source.pose.height * source.pose.root.lossyScale.y / Mathf.Max(1e-4f, pose.height * transform.lossyScale.y);
   return true;
  }

  static Source MakeSource(Transform template) {
   var player = template.GetComponentInChildren<Animation>(true);
   if (!player) { Debug.LogWarning("CHECKOUT_RETARGET_NO_ANIMATION " + template.name); return null; }
   var copy = Instantiate(player.gameObject);
   copy.name = "Retarget source " + template.name; copy.hideFlags = HideFlags.HideAndDontSave;
   foreach (var b in copy.GetComponentsInChildren<MonoBehaviour>(true)) Destroy(b);
   foreach (var c in copy.GetComponentsInChildren<Collider>(true)) Destroy(c);
   foreach (var r in copy.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
   copy.transform.SetPositionAndRotation(new Vector3(0, -520, 0), Quaternion.identity);
   copy.transform.localScale = player.transform.lossyScale;
   copy.SetActive(true);
   var anim = copy.GetComponent<Animation>(); anim.enabled = false;   // sampled by hand
   var p = Capture(copy.transform);
   if (p == null) { Destroy(copy); Debug.LogWarning("CHECKOUT_RETARGET_NO_SKELETON " + template.name); return null; }
   return new Source { copy = copy, anim = anim, pose = p };
  }

  // Bone poses of the skins' bind pose (the rig's rest pose), in the root's space.
  static Pose Capture(Transform root) {
   var all = new Dictionary<string, Transform>();
   foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (!all.ContainsKey(t.name)) all[t.name] = t;
   var bones = new Transform[Bones.Length];
   for (int i = 0; i < Bones.Length; i++) { all.TryGetValue(Bones[i], out bones[i]); if (!bones[i]) return null; }
   var rest = new Quaternion[Bones.Length]; var points = new Vector3[Bones.Length]; var found = new bool[Bones.Length];
   foreach (var skin in root.GetComponentsInChildren<SkinnedMeshRenderer>(true)) {
    if (!skin.sharedMesh) continue;
    var poses = skin.sharedMesh.bindposes; var skinBones = skin.bones;
    for (int b = 0; b < skinBones.Length && b < poses.Length; b++) {
     int i = System.Array.IndexOf(bones, skinBones[b]);
     if (i < 0 || found[i]) continue;
     var world = skin.transform.localToWorldMatrix * poses[b].inverse;
     rest[i] = Quaternion.Inverse(root.rotation) * world.rotation;
     points[i] = root.InverseTransformPoint(world.GetColumn(3));
     found[i] = true;
    }
   }
   for (int i = 0; i < Bones.Length; i++) if (!found[i]) return null;
   return new Pose { root = root, bones = bones, rest = rest, torso = points[0], up = (points[1] - points[0]).normalized,
    side = (points[11] - points[8]).normalized, height = (points[1] - points[0]).magnitude };
  }

  static Quaternion Basis(Vector3 up, Vector3 side) => Quaternion.LookRotation(Vector3.Cross(side, up).normalized, up);

  void Use(string clipName, float playSpeed, float fadeIn) {
   var state = source.anim[clipName];
   if (!state) { Debug.LogWarning("CHECKOUT_RETARGET_CLIP_MISSING " + clipName); return; }
   if (Clip != clipName) { time = Random.value * state.clip.length; Clip = clipName; }
   clip = state.clip; speed = playSpeed; target = 1; fade = 1 / Mathf.Max(.01f, fadeIn); enabled = true;
  }

  void LateUpdate() {
   if (!clip || source == null || !source.copy) return;
   Weight = Mathf.MoveTowards(Weight, target, Time.deltaTime * fade);
   if (Weight <= 0 && target <= 0) { Clip = null; enabled = false; return; }
   time += Time.deltaTime * speed;
   clip.SampleAnimation(source.copy, Mathf.Repeat(time, clip.length));
   var s = source.pose; var inverseMap = Quaternion.Inverse(map); var root = pose.root;
   for (int i = 0; i < Bones.Length; i++) {
    var now = Quaternion.Inverse(s.root.rotation) * s.bones[i].rotation;
    var want = root.rotation * (map * now * Quaternion.Inverse(s.rest[i]) * inverseMap * pose.rest[i]);
    pose.bones[i].rotation = Weight >= 1 ? want : Quaternion.Slerp(pose.bones[i].rotation, want, Weight);
   }
   var lift = s.root.InverseTransformPoint(s.bones[0].position) - s.torso;
   var at = root.TransformPoint(pose.torso + map * lift * scale);
   pose.bones[0].position = Weight >= 1 ? at : Vector3.Lerp(pose.bones[0].position, at, Weight);
  }
 }
}
