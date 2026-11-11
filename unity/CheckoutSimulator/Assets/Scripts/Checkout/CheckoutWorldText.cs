using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // The 3D TextMesh letters in the world use the font's own material ("GUI/Text Shader"), which draws over everything:
 // the facade's big gold name showed through the totem and other things in front of it (Lucas 06/11). Every TextMesh
 // in the world gets the same font texture on "Checkout/World Text" (Resources/Rede/CheckoutWorldText.shader), depth-
 // tested like the rest of the scene. Looked at again now and then: stage changes rebuild / re-enable the dressing.
 public static class CheckoutWorldText {
  static Shader shader;static bool missing;
  static readonly Dictionary<Material,Material> fixedFor=new Dictionary<Material,Material>();
  static readonly HashSet<Material> made=new HashSet<Material>();
  /// <summary>QA: letters moved onto the depth-tested material so far.</summary>
  public static int Fixed{get;private set;}

  static bool hooked;
  // A dynamic font's atlas can be rebuilt with new glyphs: the copies follow the font's own material.
  static void Rebuilt(Font font){foreach(var pair in fixedFor)if(pair.Key&&pair.Value)pair.Value.mainTexture=pair.Key.mainTexture;}

  public static void Fix(Transform root){
   if(!root||missing)return;
   if(!hooked){hooked=true;Font.textureRebuilt+=Rebuilt;}
   if(!shader){shader=Shader.Find("Checkout/World Text");if(!shader){missing=true;Debug.LogWarning("CHECKOUT_WORLD_TEXT_SHADER_MISSING");return;}}
   foreach(var t in root.GetComponentsInChildren<TextMesh>(true)){
    var r=t.GetComponent<MeshRenderer>();if(!r)continue;
    var m=r.sharedMaterial;if(!m||made.Contains(m))continue;
    if(!fixedFor.TryGetValue(m,out var f)||!f){
     f=new Material(shader){name=m.name+" (depth)"};f.mainTexture=m.mainTexture;
     if(m.HasProperty("_Color"))f.color=m.color;
     fixedFor[m]=f;made.Add(f);
    }
    r.sharedMaterial=f;Fixed++;
   }
  }
 }
}
