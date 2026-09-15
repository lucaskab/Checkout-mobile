using UnityEngine;
using System.Linq;

namespace Checkout {
 // Expansion previews stay visible while locked so simulator players can see what progression adds.
 public sealed class CheckoutExpansionPlot {
  readonly GameObject content,construction;readonly CheckoutStatusMarker marker;bool unlocked;
  public Transform Root {get;private set;}
  public CheckoutExpansionPlot(CheckoutEventAssets art,Transform parent,string id,Vector3 position,Transform source){
   Root=art.Group(parent,"Expansion "+id,position);
   art.Part(Root,"Expansion foundation",Vector3.zero,new Vector3(3.2f,.12f,2.5f),"C8B181");
   construction=art.Group(Root,"Construction preview",Vector3.up*.08f).gameObject;
   art.Bar(construction.transform,new Vector3(-1.3f,.1f,-.95f),new Vector3(1.3f,.1f,-.95f),.08f,"D29B55");
   art.Bar(construction.transform,new Vector3(-1.3f,.1f,.95f),new Vector3(1.3f,.1f,.95f),.08f,"D29B55");
   art.Cone(construction.transform,new Vector3(-1.2f,.05f,-.8f));art.Cone(construction.transform,new Vector3(1.2f,.05f,.8f));
   content=art.Group(Root,"Unlocked feature",Vector3.up*.08f).gameObject;BuildFeature(content.transform,id,source);
   marker=art.Group(Root,"Unlock status",new Vector3(0,2.15f,-.25f)).gameObject.AddComponent<CheckoutStatusMarker>();marker.Initialize(art);marker.transform.localScale=Vector3.one*1.6f;
  }
  public void Apply(bool next,int requiredLevel){
   if(next&&!unlocked){content.transform.localScale=Vector3.one*.75f;}
   unlocked=next;construction.SetActive(!unlocked);content.SetActive(true);marker.Apply(unlocked,1,1,false,requiredLevel);
  }
  public void Update(){if(!unlocked||content.transform.localScale==Vector3.one)return;content.transform.localScale=Vector3.MoveTowards(content.transform.localScale,Vector3.one,Time.deltaTime*1.8f);}
  static void BuildFeature(Transform root,string id,Transform source){
   if(!source)return;var preview=Object.Instantiate(source.gameObject,root);preview.name=id+" model preview";preview.SetActive(true);preview.transform.localPosition=Vector3.zero;preview.transform.rotation=source.rotation;preview.transform.localScale=Vector3.one;
   foreach(var collider in preview.GetComponentsInChildren<Collider>(true))Object.Destroy(collider);
   foreach(var behaviour in preview.GetComponentsInChildren<Behaviour>(true))behaviour.enabled=false;
   foreach(var child in preview.GetComponentsInChildren<Transform>(true))child.gameObject.SetActive(true);
   var renderers=preview.GetComponentsInChildren<Renderer>(true).ToArray();foreach(var renderer in renderers)renderer.enabled=true;if(renderers.Length==0)return;
   var bounds=renderers[0].bounds;foreach(var renderer in renderers)bounds.Encapsulate(renderer.bounds);var maximum=new Vector3(2.6f,1.75f,2f);preview.transform.localScale*=Mathf.Min(maximum.x/bounds.size.x,maximum.y/bounds.size.y,maximum.z/bounds.size.z);
   bounds=renderers[0].bounds;foreach(var renderer in renderers)bounds.Encapsulate(renderer.bounds);var target=root.position+Vector3.up*.08f;preview.transform.position+=new Vector3(target.x-bounds.center.x,target.y-bounds.min.y,target.z-bounds.center.z);
  }
 }
}
