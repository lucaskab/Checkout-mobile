using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 /// <summary>
 /// The way in of the small shops (Späti, quitanda, minimercado): the steps, the golden threshold on the wall line
 /// and the door mat stand higher than the sidewalk (0.15) and than the NavMesh, so whoever walked there by the
 /// sidewalk/floor rule sank to the ankles (Lucas 08/11: "a escadinha e o douradinho estão engolindo os pés").
 /// Heights measured on each model (Blender, rays straight down through the doorway; the doors and glass left out),
 /// in the model's own units relative to the front wall line: dz &lt; 0 outside, &gt; 0 inside.
 /// </summary>
 public static class CheckoutEntranceFloor {
  const float Sidewalk = float.NaN;   // the street's own height (0.15 world) at the foot of the steps

  sealed class Profile {
   public float door0, door1, floorY;   // the plan's door (model x) and floor top (model y): give scale and origin
   public float x0, x1;                 // where the steps run along the wall (model x)
   public Vector2[] points;             // (dz, model height), piecewise linear; NaN = the sidewalk
  }

  static readonly Dictionary<int, Profile> ByEra = new Dictionary<int, Profile> {
   // Späti: one low step in front of the door
   [4] = new Profile { door0 = .58f, door1 = 1.78f, floorY = .06f, x0 = .68f, x1 = 1.73f, points = new[] {
    new Vector2(-.72f, Sidewalk), new Vector2(-.66f, .014f), new Vector2(-.20f, .014f), new Vector2(-.15f, .06f), new Vector2(.05f, .06f) } },
   // quitanda: a long low step along the front, a raised threshold under the wide door
   [5] = new Profile { door0 = -3.45f, door1 = .55f, floorY = .06f, x0 = -4.2f, x1 = 2.55f, points = new[] {
    new Vector2(-.92f, Sidewalk), new Vector2(-.86f, .03f), new Vector2(-.20f, .03f), new Vector2(-.15f, .075f), new Vector2(.15f, .075f), new Vector2(.20f, .06f) } },
   // minimercado: two steps, the golden threshold and the door mat
   [6] = new Profile { door0 = -1.2f, door1 = .2f, floorY = .16f, x0 = -2.25f, x1 = 1.3f, points = new[] {
    new Vector2(-1.07f, Sidewalk), new Vector2(-1.01f, .08f), new Vector2(-.65f, .08f), new Vector2(-.60f, .14f), new Vector2(-.25f, .14f),
    new Vector2(-.20f, .172f), new Vector2(.42f, .172f), new Vector2(.47f, .16f) } },
  };

  /// <summary>The height of the visible floor at the shop's way in (world), when p stands on it.</summary>
  public static bool TryHeight(Vector3 p, out float y) {
   y = 0;
   if (!CheckoutStall.ShopInside || !ByEra.TryGetValue(CheckoutStall.Era, out var pr)) return false;
   float k = 2f * CheckoutStall.DoorHalf / (pr.door1 - pr.door0);
   if (k < .3f || k > 3f) return false;
   float x = (p.x - CheckoutStall.Door.x) / k + (pr.door0 + pr.door1) * .5f;
   float dz = (p.z - CheckoutStall.Door.y) / k;
   var pts = pr.points;
   if (dz < pts[0].x || dz > pts[pts.Length - 1].x || x < pr.x0 || x > pr.x1) return false;
   if (dz > 0 && (x < pr.door0 - .25f || x > pr.door1 + .25f)) return false;     // inside, only the doorway itself
   float Level(float h) => float.IsNaN(h) ? (.15f - CheckoutStall.FloorY) / k + pr.floorY : h;
   for (int i = 1; i < pts.Length; i++) {
    if (dz > pts[i].x) continue;
    float a = Level(pts[i - 1].y), b = Level(pts[i].y);
    float t = Mathf.InverseLerp(pts[i - 1].x, pts[i].x, dz);
    y = CheckoutStall.FloorY + (Mathf.Lerp(a, b, t) - pr.floorY) * k;
    return true;
   }
   return false;
  }
 }
}
