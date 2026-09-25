using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Opt-in visual QA uses a supplied isolated snapshot; it never writes gameplay state.
 public sealed class CheckoutEventPlaytest:MonoBehaviour {
  public IEnumerator Run(CheckoutBridge bridge,string folder){Directory.CreateDirectory(folder);yield return new WaitForSeconds(1);var effects=bridge.GetComponent<CheckoutEventVisuals>();var state=JsonUtility.FromJson<Snapshot>(JsonUtility.ToJson(bridge.State));var baseline=JsonUtility.ToJson(state.shelves);var sun=FindObjectsByType<Light>().First(l=>l.type==LightType.Directional);effects.Apply(new MarketEvent());var light=sun.color;var intensity=sun.intensity;
   Capture(Path.Combine(folder,"00-clean-market.png"),1280,800);
   int checks=0;
   foreach(var id in CheckoutEventVisuals.EventIds){state.revision++;state.@event=new MarketEvent{id=id,endsAt=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()+60000};bridge.Receive(JsonUtility.ToJson(state));yield return new WaitForSeconds(1.3f);
    Require(effects.ActiveId==id,"Wrong active event: "+id);var scene=effects.transform.Find("Event · "+id);Require(scene&&scene.gameObject.activeSelf,"Missing scene: "+id);Require(scene.GetComponentsInChildren<Renderer>().Length>0,"Missing assets: "+id);Require(scene.GetComponentsInChildren<Renderer>().All(r=>r.sharedMaterial&&r.sharedMaterial.shader.isSupported),"Unsupported event material: "+id);Require(scene.GetComponentsInChildren<TextMesh>().Length==0,"Floating text remains");Require(JsonUtility.ToJson(bridge.State.shelves)==baseline,"Visual event changed inventory");
    if(id=="chuva-forte"){
     Require(scene.GetComponentsInChildren<ParticleSystem>().Sum(p=>p.particleCount)>100,"Rain is not emitting");
     var outside=FindObjectsByType<MarketDay.MarketCharacterAnimator>(FindObjectsInactive.Exclude).Where(c=>c.GetComponent<CheckoutCityPedestrian>()||c.GetComponent<CheckoutCityAppearance>()).Where(c=>{var pedestrian=c.GetComponent<CheckoutCityPedestrian>();return !pedestrian||!pedestrian.IsSheltered;}).ToArray();
     Require(outside.Length>0,"No exposed city characters are available for umbrella validation");
     Require(outside.All(c=>{var rig=c.GetComponent<MarketDay.MarketRainUmbrellaRig>();return rig&&rig.HasVisibleUmbrella&&rig.HasRightHandRig&&rig.ForearmIsUpright&&rig.IsShelteringHead;}),"An exposed city character needs a colored umbrella over the head, held in the raised right hand with an upright forearm");
     var lamps=FindObjectsByType<Light>(FindObjectsInactive.Exclude).Where(l=>l.type==LightType.Spot&&l.name.ToLowerInvariant().Contains("spotlight")).ToArray();
     Require(lamps.Length>=28,"Streetlight fixtures are missing: "+lamps.Length);
     Require(lamps.All(l=>l.enabled&&l.intensity>=5&&l.range>=11),"One or more streetlights did not brighten for the rain event");
    }
    int count=scene.childCount;effects.Apply(state.@event);Require(scene.childCount==count,"Duplicate assets on snapshot");
    Capture(Path.Combine(folder,id+".png"),1280,800);if(id=="chuva-forte")Capture(Path.Combine(folder,"portrait-rain.png"),390,844);
    effects.Apply(new MarketEvent());yield return null;Require(!scene.gameObject.activeSelf,"Event not cleaned up");Require(scene.GetComponentsInChildren<ParticleSystem>(true).All(p=>p.particleCount==0),"Particles not cleared");Require(sun.color==light&&Mathf.Approximately(sun.intensity,intensity),"Lighting not restored");checks++;
   }
   effects.Apply(new MarketEvent{id="chuva-forte",endsAt=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()+100});yield return new WaitForSeconds(.3f);Require(effects.ActiveId=="","Expired event still visible without a new snapshot");
   File.WriteAllText(Path.Combine(folder,"report.json"),"{\"passed\":true,\"events\":"+checks+",\"expiryAndCleanup\":true,\"inventoryUnchanged\":true}");Debug.Log("CHECKOUT_EVENT_QA_OK "+checks);Application.Quit(0);
  }
  static void Require(bool ok,string message){if(ok)return;Debug.LogError("CHECKOUT_EVENT_QA_FAILED "+message);Application.Quit(1);throw new Exception(message);}
  static void Capture(string path,int width,int height){var camera=Camera.main;var old=camera.targetTexture;var active=RenderTexture.active;var rt=new RenderTexture(width,height,24){antiAliasing=4};camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;var image=new Texture2D(width,height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());camera.targetTexture=old;RenderTexture.active=active;Destroy(image);Destroy(rt);}
 }
}
