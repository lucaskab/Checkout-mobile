using UnityEngine;

namespace Checkout {
 // Moves a bone by a fixed offset on top of whatever its animation sets (the driver of EventRigs/Rig_JamCar sits a
 // little behind the window he talks through: this brings him forward). The offset is in `space`'s axes.
 public sealed class CheckoutBoneNudge : MonoBehaviour {
  public Transform space; public Vector3 offset;
  Vector3 animated, written; bool started;

  public static CheckoutBoneNudge Add(Transform bone, Transform space, Vector3 offset) {
   if (!bone) return null;
   var n = bone.GetComponent<CheckoutBoneNudge>() ?? bone.gameObject.AddComponent<CheckoutBoneNudge>();
   n.space = space; n.offset = offset; return n;
  }

  void LateUpdate() {
   var p = transform.localPosition;
   // a fresh value means the animation wrote this frame; otherwise the bone still holds our own
   if (!started || (p - written).sqrMagnitude > 1e-10f) { animated = p; started = true; }
   var parent = transform.parent;
   var local = parent && space ? parent.InverseTransformVector(space.TransformVector(offset)) : offset;
   transform.localPosition = written = animated + local;
  }
 }
}
