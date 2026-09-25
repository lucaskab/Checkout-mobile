using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Opt-in gameplay parity QA captures the actual snapshot-driven world without mutating app storage.
 public sealed class CheckoutParityPlaytest:MonoBehaviour {
  public IEnumerator Run(CheckoutBridge bridge,string folder){
   Directory.CreateDirectory(folder);yield return new WaitForSeconds(2);
   Require(bridge.State!=null,"snapshot missing");Require(bridge.State.experienceToNextLevel>0,"XP projection missing");Require(bridge.State.dailyGoal>0,"daily goal missing");
   Require(bridge.State.sectors.All(sector=>sector.requiredLevel>0),"sector level requirements missing");Require(bridge.State.shelves.All(shelf=>shelf.requiredLevel>0),"shelf level requirements missing");Require(bridge.State.expansionStates!=null&&bridge.State.expansionStates.Length==4,"expansion projection missing");
   foreach(var expansion in bridge.State.expansionStates)Require(!bridge.transform.Find("Expansion "+expansion.id),"removed expansion marker returned: "+expansion.id);
   var camera=Camera.main;var originalPosition=camera.transform.position;var originalRotation=camera.transform.rotation;var originalSize=camera.orthographicSize;
   var shots=new[]{
    new Shot("01-full-market",new Vector3(28,33,-32),new Vector3(0,0,5),20.5f),new Shot("02-storefront",new Vector3(24,25,-31),new Vector3(0,0,0),13.5f),
    new Shot("03-departments",new Vector3(26,23,-16),new Vector3(0,0,2.5f),10.5f),new Shot("04-expansion-row",new Vector3(32,19,-1),new Vector3(13.5f,0,1),9),
    new Shot("05-loading-yard",new Vector3(22,21,34),new Vector3(1,0,13),10),new Shot("06-fresh-wing",new Vector3(28,16,-13),new Vector3(13.5f,0,-5.2f),6.5f),
    new Shot("07-service-wing",new Vector3(30,16,-6),new Vector3(13.5f,0,-1.05f),6.5f),new Shot("08-stock-annex",new Vector3(31,16,2),new Vector3(13.5f,0,3.1f),6.5f),
    new Shot("09-premium-hall",new Vector3(29,17,10),new Vector3(13.5f,0,7.25f),6.5f),new Shot("10-rear-market",new Vector3(-25,25,31),new Vector3(0,0,3),14),
   };
   foreach(var shot in shots){camera.transform.position=shot.position;camera.transform.LookAt(shot.focus);camera.orthographicSize=shot.size;Capture(camera,Path.Combine(folder,shot.name+".png"),1280,800);yield return null;}
   camera.transform.SetPositionAndRotation(originalPosition,originalRotation);camera.orthographicSize=originalSize;
   File.WriteAllText(Path.Combine(folder,"report.json"),"{\"passed\":true,\"captures\":"+shots.Length+",\"level\":"+bridge.State.level+",\"expansions\":"+bridge.State.expansionStates.Length+"}");Debug.Log("CHECKOUT_PARITY_QA_OK "+shots.Length);Application.Quit(0);
  }
  static void Require(bool ok,string message){if(ok)return;Debug.LogError("CHECKOUT_PARITY_QA_FAILED "+message);Application.Quit(1);throw new Exception(message);}
  static void Capture(Camera camera,string path,int width,int height){var old=camera.targetTexture;var active=RenderTexture.active;var rt=new RenderTexture(width,height,24){antiAliasing=4};camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;var image=new Texture2D(width,height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());camera.targetTexture=old;RenderTexture.active=active;Destroy(image);Destroy(rt);}
  readonly struct Shot {public readonly string name;public readonly Vector3 position,focus;public readonly float size;public Shot(string name,Vector3 position,Vector3 focus,float size){this.name=name;this.position=position;this.focus=focus;this.size=size;}}
 }
}
