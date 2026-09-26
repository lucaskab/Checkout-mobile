#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using MarketDay;
using UnityEngine;

namespace Checkout {
 // Editor/dev-only event preview. In Play mode:  ] / PageDown next event, [ / PageUp previous, 0 clears,
 // F focuses the camera on/off, F9 captures every event to ArtSource/EventProps/Captures.
 // It only drives CheckoutEventVisuals; gameplay state still comes from the React Native snapshot.
 public sealed class CheckoutEventPreview:MonoBehaviour {
  public static CheckoutEventPreview Instance {get;private set;}
  static string[] Ids=>CheckoutEventVisuals.EventIds;
  int index=-1;bool follow=true,capturing;string note="";
  public bool Capturing=>capturing;
  public string Current=>index>=0?Ids[index]:"";
  public static string CaptureFolder=>Path.GetFullPath(Path.Combine(Application.dataPath,"..","ArtSource","EventProps","Captures"));

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){if(Instance||!FindAnyObjectByType<CheckoutBridge>())return;Instance=new GameObject("Checkout Event Preview").AddComponent<CheckoutEventPreview>();}

  CheckoutEventVisuals Effects=>FindAnyObjectByType<CheckoutEventVisuals>();
  public void Show(int i){var fx=Effects;if(!fx)return;index=((i%Ids.Length)+Ids.Length)%Ids.Length;fx.Preview(Ids[index]);if(follow)StartCoroutine(FocusSoon());}
  public void Show(string id){int i=Array.IndexOf(Ids,id);if(i>=0)Show(i);}
  public void Next()=>Show(index+1);
  public void Previous()=>Show(index<0?Ids.Length-1:index-1);
  public void Clear(){var fx=Effects;if(fx)fx.Preview("");index=-1;Home();}
  public void CaptureAll(){if(!capturing)StartCoroutine(Capture());}

  void Update(){
   if(capturing)return;
   if(Input.GetKeyDown(KeyCode.RightBracket)||Input.GetKeyDown(KeyCode.PageDown))Next();
   if(Input.GetKeyDown(KeyCode.LeftBracket)||Input.GetKeyDown(KeyCode.PageUp))Previous();
   if(Input.GetKeyDown(KeyCode.Alpha0)||Input.GetKeyDown(KeyCode.Keypad0))Clear();
   if(Input.GetKeyDown(KeyCode.F)){follow=!follow;if(follow)Focus();else Home();}
   if(Input.GetKeyDown(KeyCode.F9))CaptureAll();
   if(Input.GetKeyDown(KeyCode.F10))StartCoroutine(CaptureMap());
  }
  // F10: straight-down tiles of the whole city (road markings, crossings) plus close-ups of the entrance,
  // written to ArtSource/EventProps/Captures/Map. File names carry the world centre of each tile.
  IEnumerator CaptureMap(){capturing=true;var folder=Path.Combine(CaptureFolder,"Map");Directory.CreateDirectory(folder);note="· capturando mapa";yield return null;
   var map=FindAnyObjectByType<CheckoutMap>();var door=map?map.Entrance:new Vector3(-1.75f,.74f,-8.7f);
   Shoot(Path.Combine(folder,"entrance-iso.png"),new Bounds(door+new Vector3(0,1.2f,-1.2f),new Vector3(7,3,6)),1280,800);
   ShootTop(Path.Combine(folder,"entrance-top.png"),door+new Vector3(0,0,-2),5,1280,800);
   foreach(var x in new[]{-30,-10,10,30})foreach(var z in new[]{-30,-12,6,24,42})ShootTop(Path.Combine(folder,$"top_{x}_{z}.png"),new Vector3(x,0,z),10,1280,800);
   note="· mapa em ArtSource/EventProps/Captures/Map";capturing=false;Debug.Log("CHECKOUT_MAP_CAPTURES_OK "+folder);}
  static void ShootTop(string path,Vector3 center,float half,int width,int height){var main=Camera.main;if(!main)return;var go=new GameObject("Map capture camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);
   cam.orthographic=true;cam.orthographicSize=half;cam.transform.position=new Vector3(center.x,60,center.z);cam.transform.rotation=Quaternion.Euler(90,0,0);cam.nearClipPlane=.3f;cam.farClipPlane=200;
   var rt=new RenderTexture(width,height,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(width,height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());RenderTexture.active=active;cam.targetTexture=null;Destroy(image);rt.Release();Destroy(rt);Destroy(go);}
  // Only drawn while previewing an event, at the bottom-left so it never covers the game HUD.
  void OnGUI(){
   if(index<0&&!capturing)return;
   var style=new GUIStyle(GUI.skin.box){fontSize=15,alignment=TextAnchor.MiddleLeft,richText=true,padding=new RectOffset(10,10,6,6)};
   string label=index>=0?$"<b>Evento {index+1}/{Ids.Length}:</b> {Ids[index]}":"<b>Sem evento</b>";
   GUI.Box(new Rect(10,Screen.height-150,560,54),label+"\n<size=12>[ ] trocar evento · 0 limpar · F câmera "+(follow?"no evento":"livre")+" · F9 capturar todos "+note+"</size>",style);
  }

  // Camera focus reuses MarketSimulation's own orbit so dragging still works afterwards.
  static readonly FieldInfo FocusField=typeof(MarketSimulation).GetField("focus",BindingFlags.NonPublic|BindingFlags.Instance);
  static readonly FieldInfo ZoomField=typeof(MarketSimulation).GetField("zoom",BindingFlags.NonPublic|BindingFlags.Instance);
  static readonly MethodInfo UpdateCam=typeof(MarketSimulation).GetMethod("UpdateCamera",BindingFlags.NonPublic|BindingFlags.Instance);
  IEnumerator FocusSoon(){yield return null;yield return null;Focus();}
  public Bounds EventBounds(){var fx=Effects;var scene=fx&&index>=0?fx.transform.Find("Event · "+Ids[index]):null;var renderers=scene?scene.GetComponentsInChildren<Renderer>().Where(r=>r.enabled&&r is MeshRenderer).ToArray():new Renderer[0];
   if(renderers.Length==0)return new Bounds(new Vector3(0,.5f,-2),new Vector3(20,2,20));var b=renderers[0].bounds;foreach(var r in renderers.Skip(1))b.Encapsulate(r.bounds);
   if(Ids[index]=="chuva-forte")b=new Bounds(new Vector3(0,.5f,-6),new Vector3(26,2,18));return b;}
  void Focus(){var sim=FindAnyObjectByType<MarketSimulation>();if(!sim||FocusField==null)return;var b=EventBounds();FocusField.SetValue(sim,new Vector3(b.center.x,.1f,b.center.z));ZoomField?.SetValue(sim,Mathf.Clamp(Mathf.Max(b.size.x,b.size.z)*.55f+2.5f,6,20.5f));UpdateCam?.Invoke(sim,null);}
  void Home(){var sim=FindAnyObjectByType<MarketSimulation>();if(sim)sim.HomeCamera();}

  IEnumerator Capture(){capturing=true;Directory.CreateDirectory(CaptureFolder);bool wasFollow=follow;follow=false;
   Clear();yield return new WaitForSeconds(.8f);Shoot(Path.Combine(CaptureFolder,"00-overview.png"),null,1280,800);
   for(int i=0;i<Ids.Length;i++){note=$"· capturando {i+1}/{Ids.Length}";Show(i);yield return new WaitForSeconds(1.6f);var b=EventBounds();
    Shoot(Path.Combine(CaptureFolder,$"{i+1:00}-{Ids[i]}.png"),b,1280,800);}
   Clear();follow=wasFollow;note="· capturas em ArtSource/EventProps/Captures";capturing=false;Debug.Log("CHECKOUT_EVENT_CAPTURES_OK "+CaptureFolder);}

  static void Shoot(string path,Bounds? focus,int width,int height){var main=Camera.main;if(!main)return;var go=new GameObject("Event capture camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);
   if(focus.HasValue){var b=focus.Value;var center=new Vector3(b.center.x,Mathf.Min(b.center.y,1.2f),b.center.z);cam.transform.position=center+new Vector3(28,33,-38);cam.transform.LookAt(center);
    // Fit the bounds' eight corners in the orthographic frustum.
    float half=1;foreach(var c in new[]{-1,1})foreach(var d in new[]{-1,1})foreach(var e in new[]{-1,1}){var corner=b.center+Vector3.Scale(b.extents,new Vector3(c,d,e));var local=cam.transform.InverseTransformPoint(corner);half=Mathf.Max(half,Mathf.Abs(local.y),Mathf.Abs(local.x)*height/width);}
    cam.orthographicSize=half*1.18f+.4f;}
   var rt=new RenderTexture(width,height,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(width,height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());RenderTexture.active=active;cam.targetTexture=null;Destroy(image);rt.Release();Destroy(rt);Destroy(go);}
 }
}
#endif
