using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Desktop HUD drawn from the host's view messages: top bar, toolbar, page drawer and toasts.
 // It holds no game rules; every button sends a route or a store action back to the host.
 public partial class CheckoutDesktopHUD:MonoBehaviour {
  CheckoutDesktopHost host;RectTransform root;DesktopView view;
  readonly Dictionary<string,DesktopButton> pending=new Dictionary<string,DesktopButton>();
  public readonly HashSet<string> Silent=new HashSet<string>();

  public void Initialize(CheckoutDesktopHost owner){
   host=owner;
   if(!FindAnyObjectByType<UnityEngine.EventSystems.EventSystem>()){var events=new GameObject("EventSystem");events.AddComponent<UnityEngine.EventSystems.EventSystem>();events.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();}
   var canvasGo=new GameObject("CheckoutDesktopHUD",typeof(RectTransform));canvasGo.transform.SetParent(transform,false);
   var canvas=canvasGo.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=50;
   var scaler=canvasGo.AddComponent<UnityEngine.UI.CanvasScaler>();scaler.uiScaleMode=UnityEngine.UI.CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1600,1000);scaler.matchWidthOrHeight=.5f;
   canvasGo.AddComponent<UnityEngine.UI.GraphicRaycaster>();
   root=(RectTransform)canvasGo.transform;
   BuildTop();BuildToolbar();BuildDrawer();BuildShop();BuildOverlay();
   Offline("Carregando o jogo…");
  }

  // Raised cream panel (edge + face). Returns the face so callers can lay out content in it.
  static RectTransform Panel(Transform parent,string name,float width,float height,out UnityEngine.UI.Image edge,out UnityEngine.UI.Image face,int radius=16){
   var node=N.Node(name,parent);edge=node.gameObject.AddComponent<UnityEngine.UI.Image>();edge.sprite=K.Rounded(radius);edge.type=UnityEngine.UI.Image.Type.Sliced;edge.color=K.Border;
   var layout=node.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();if(width>0)layout.preferredWidth=width;else layout.flexibleWidth=1;layout.preferredHeight=height;
   face=N.Image(node,"Face",K.Cream,radius-2);var rect=face.rectTransform;rect.anchorMin=Vector2.zero;rect.anchorMax=Vector2.one;rect.offsetMin=new Vector2(2,5);rect.offsetMax=new Vector2(-2,-2);
   return rect;
  }
  static RectTransform Bar(Transform parent,float height,Color color,out RectTransform fill){
   var track=N.Image(parent,"Bar",K.C("EADBC4"),6);track.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().preferredHeight=height;
   var f=N.Image(track.transform,"Fill",color,6);fill=f.rectTransform;fill.anchorMin=Vector2.zero;fill.anchorMax=new Vector2(0,1);fill.offsetMin=fill.offsetMax=Vector2.zero;
   return track.rectTransform;
  }
  void Clickable(GameObject target,System.Action action){var b=target.AddComponent<UnityEngine.UI.Button>();b.transition=UnityEngine.UI.Selectable.Transition.None;b.onClick.AddListener(()=>action());}

  public void Apply(string json){
   DesktopView next;try {next=JsonUtility.FromJson<DesktopView>(json);}catch(System.Exception ex){Debug.LogError("CHECKOUT_DESKTOP bad view: "+ex.Message);return;}
   if(next==null||next.kind!="view")return;
   view=next;ApplyTop(next);ApplyToolbar(next);ApplyDrawer(next);ApplyShop(next);ApplyOverlay(next);
  }
  public void Result(string json){
   var result=JsonUtility.FromJson<DesktopResult>(json);if(result==null)return;
   // Actions sent by the map editor for its sandbox (unlocks, money top-ups) finish without toasts.
   if(Silent.Remove(result.id??""))return;
   pending.TryGetValue(result.id??"",out var source);pending.Remove(result.id??"");
   if(result.ok)Toast(string.IsNullOrEmpty(source?.ok)?"Feito!":source.ok,true);
   else Toast(!string.IsNullOrEmpty(source?.fail)?source.fail:result.reason=="game-rule-rejected"?"Não foi possível agora.":result.reason,false);
  }
  // Every HUD button lands here: store actions go to the host, routes navigate.
  void Press(CheckoutDesktopButton button){
   var data=button.Data;if(data==null)return;
   if(!data.enabled){if(!string.IsNullOrEmpty(data.fail))Toast(data.fail,false);return;}
   if(!string.IsNullOrEmpty(data.action)){pending[host.Action(data.action,data.args,data.after)]=data;return;}
   // "@build" opens the build mode (bought furniture waits there to be placed).
   if(data.route=="@build"){host.Route("");CheckoutBuildMode.OpenFromHud();return;}
   // "@lots" shows the lots of the block from above (CheckoutLotView).
   if(data.route=="@lots"){host.Route("");CheckoutLotView.Show();return;}
   // Buttons with neither an action nor a route are labels only.
   if(!string.IsNullOrEmpty(data.route))host.Route(data.route);
  }
  void Update(){
   if(Input.GetKeyDown(KeyCode.Escape)&&view!=null&&view.hasPage)host.Route(view.canBack?"back":"");
   UpdateToast();
  }
 }
}
