using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Event moves (Assets/Resources/EventRigs/EventMoves.fbx, built by ArtSource/event_rigs/characters.py): clips keyed on
 // the skeleton every customer and worker shares (Torso, Head, Thigh/Shin/Foot, UpperArm/Forearm/Hand). A hidden copy of
 // that skeleton samples the clip; the pose is copied onto the character bone by bone in the model's own space, so a
 // different bone axis or import scale on the character does not matter. Arms-only clips (pushing the pallet jack,
 // carrying a box) leave the legs to the character's own walk.
 public sealed class CheckoutEventMoves : MonoBehaviour {
  static readonly string[] Bones = { "Torso", "Head", "Thigh_L", "Shin_L", "Foot_L", "Thigh_R", "Shin_R", "Foot_R",
   "UpperArm_L", "Forearm_L", "Hand_L", "UpperArm_R", "Forearm_R", "Hand_R" };
  static readonly HashSet<string> ArmsOnly = new HashSet<string> { "HoldHandle", "CarryBox" };

  // the shared source skeleton
  static GameObject source; static Animation sourceAnim; static Transform sourceRoot;
  static Transform[] sourceBones; static Quaternion[] sourceRest; static Vector3 sourceTorso; static Vector3 sourceUp, sourceSide; static float sourceHeight;

  Transform root; Transform[] bones; Quaternion[] rest; Vector3 restTorso; Quaternion map; float scale = 1;
  AnimationClip clip; float time, speed = 1; bool armsOnly;
  public string Clip { get; private set; }

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
  static void Reset() { source = null; }

  static bool LoadSource() {
   if (source) return true;
   var prefab = Resources.Load<GameObject>("EventRigs/EventMoves");
   if (!prefab) { Debug.LogWarning("CHECKOUT_EVENT_MOVES_MISSING"); return false; }
   source = Instantiate(prefab); source.name = "Event moves skeleton"; source.hideFlags = HideFlags.HideAndDontSave;
   source.transform.position = new Vector3(0, -500, 0);
   sourceAnim = source.GetComponentInChildren<Animation>(true); sourceRoot = source.transform;
   if (sourceAnim) sourceAnim.enabled = false;               // sampled by hand
   sourceBones = Find(sourceRoot);
   var restClip = Find(sourceAnim, "Rest");
   if (restClip) restClip.SampleAnimation(sourceAnim.gameObject, 0);
   sourceRest = Rotations(sourceRoot, sourceBones);
   sourceTorso = sourceRoot.InverseTransformPoint(sourceBones[0].position);
   Frame(sourceRoot, sourceBones, out sourceUp, out sourceSide);
   sourceHeight = sourceRoot.InverseTransformVector(sourceBones[1].position - sourceBones[0].position).magnitude;
   return true;
  }

  static Transform[] Find(Transform root) {
   var all = new Dictionary<string, Transform>();
   foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (!all.ContainsKey(t.name)) all[t.name] = t;
   var found = new Transform[Bones.Length];
   for (int i = 0; i < Bones.Length; i++) all.TryGetValue(Bones[i], out found[i]);
   return found;
  }

  public static AnimationClip Find(Animation animation, string name) {
   if (!animation) return null;
   foreach (AnimationState state in animation)
    if (state.name == name || state.name.EndsWith("|" + name)) return state.clip;
   return null;
  }

  static Quaternion[] Rotations(Transform root, Transform[] bones) {
   var r = new Quaternion[bones.Length];
   for (int i = 0; i < bones.Length; i++) r[i] = bones[i] ? Quaternion.Inverse(root.rotation) * bones[i].rotation : Quaternion.identity;
   return r;
  }

  // Up (hips to head) and side (left to right shoulder) of a skeleton, in its root space.
  static void Frame(Transform root, Transform[] b, out Vector3 up, out Vector3 side) {
   up = root.InverseTransformDirection(b[1].position - b[0].position).normalized;
   side = root.InverseTransformDirection(b[11].position - b[8].position).normalized;
  }

  static Quaternion Basis(Vector3 up, Vector3 side) => Quaternion.LookRotation(Vector3.Cross(side, up).normalized, up);

  /// <summary>Plays an event move on a character (the object holding its legacy Animation and skeleton).</summary>
  public static CheckoutEventMoves Play(GameObject character, string clipName, float speed = 1, float offset = 0) {
   if (!character || !LoadSource()) return null;
   var clip = Find(sourceAnim, clipName);
   if (!clip) { Debug.LogWarning("CHECKOUT_EVENT_MOVE_MISSING " + clipName); return null; }
   var moves = character.GetComponent<CheckoutEventMoves>() ?? character.AddComponent<CheckoutEventMoves>();
   moves.Bind(clip, clipName, speed, offset);
   return moves;
  }

  void Bind(AnimationClip value, string name, float playSpeed, float offset) {
   root = transform; bones = Find(root);
   if (bones[0] == null || bones[1] == null || bones[8] == null || bones[11] == null) { Debug.LogWarning("CHECKOUT_EVENT_MOVES_NO_SKELETON " + name); enabled = false; return; }
   // reference pose: the skin's bind pose (the rig's rest pose, like the source's "Rest" clip); without a skin,
   // the character's own Idle at its first frame
   if (!BindPose(out rest, out restTorso, out var up, out var side, out var height)) {
    var own = GetComponent<Animation>();
    var idle = Find(own, "Idle");
    if (idle) idle.SampleAnimation(gameObject, 0);
    rest = Rotations(root, bones);
    restTorso = root.InverseTransformPoint(bones[0].position);
    Frame(root, bones, out up, out side);
    height = root.InverseTransformVector(bones[1].position - bones[0].position).magnitude;
   }
   map = Basis(up, side) * Quaternion.Inverse(Basis(sourceUp, sourceSide));
   scale = height / Mathf.Max(1e-4f, sourceHeight);
   clip = value; Clip = name; speed = playSpeed; time = offset * clip.length; armsOnly = ArmsOnly.Contains(name);
   enabled = true;
  }

  // Bone poses of the skin's bind pose, in the character's root space.
  bool BindPose(out Quaternion[] rotations, out Vector3 torso, out Vector3 up, out Vector3 side, out float height) {
   rotations = null; torso = up = side = Vector3.zero; height = 0;
   var points = new Vector3[Bones.Length];
   rotations = new Quaternion[Bones.Length];
   var found = new bool[Bones.Length];
   foreach (var skin in GetComponentsInChildren<SkinnedMeshRenderer>(true)) {
    if (!skin.sharedMesh) continue;
    var poses = skin.sharedMesh.bindposes; var skinBones = skin.bones;
    for (int b = 0; b < skinBones.Length && b < poses.Length; b++) {
     int i = System.Array.IndexOf(bones, skinBones[b]);
     if (i < 0 || found[i]) continue;
     var world = skin.transform.localToWorldMatrix * poses[b].inverse;
     rotations[i] = Quaternion.Inverse(root.rotation) * world.rotation;
     points[i] = root.InverseTransformPoint(world.GetColumn(3));
     found[i] = true;
    }
   }
   for (int i = 0; i < Bones.Length; i++) if (bones[i] && !found[i]) return false;
   torso = points[0];
   up = (points[1] - points[0]).normalized; side = (points[11] - points[8]).normalized;
   height = (points[1] - points[0]).magnitude;
   return true;
  }

  // The world position of a bone when the move is at `seconds` (applies that pose now; the next frame continues).
  public Vector3 PoseAt(float seconds, string bone) {
   if (!clip) return transform.position;
   time = seconds; Apply(seconds);
   int i = System.Array.IndexOf(Bones, bone);
   return i >= 0 && bones[i] ? bones[i].position : transform.position;
  }

  public void Stop() { enabled = false; clip = null; Clip = null; }
  /// <summary>Length in seconds of an event move (0 when it is missing).</summary>
  public static float Length(string clipName) { if (!LoadSource()) return 0; var c = Find(sourceAnim, clipName); return c ? c.length : 0; }

  void LateUpdate() {
   if (!clip || bones == null) return;
   time += Time.deltaTime * speed;
   Apply(time);
  }

  void Apply(float at) {
   clip.SampleAnimation(sourceAnim.gameObject, Mathf.Repeat(at, clip.length));
   var inverseMap = Quaternion.Inverse(map);
   for (int i = 0; i < Bones.Length; i++) {
    if (!bones[i] || !sourceBones[i]) continue;
    if (armsOnly && i < 8) continue;
    var now = Quaternion.Inverse(sourceRoot.rotation) * sourceBones[i].rotation;
    var pose = map * now * Quaternion.Inverse(sourceRest[i]) * inverseMap * rest[i];
    bones[i].rotation = root.rotation * pose;
   }
   if (!armsOnly) {
    var lift = sourceRoot.InverseTransformPoint(sourceBones[0].position) - sourceTorso;
    bones[0].position = root.TransformPoint(restTorso + map * lift * scale);
   }
  }
 }
}
