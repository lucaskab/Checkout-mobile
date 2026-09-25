using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 public partial class CheckoutDesktopHUD {
  GameObject modal,status;CheckoutDesktopCard offlineCard;TextMeshProUGUI statusText;
  RectTransform toast;UnityEngine.UI.Image toastEdge,toastFace;TextMeshProUGUI toastText;float toastUntil;

  static RectTransform Fill(Transform parent,string name,Color color,bool blocks){
   var image=N.Image(parent,name,color,0);image.raycastTarget=blocks;var rect=image.rectTransform;
   rect.anchorMin=Vector2.zero;rect.anchorMax=Vector2.one;rect.offsetMin=rect.offsetMax=Vector2.zero;return rect;
  }
  static RectTransform Centered(Transform parent,string name,float width){
   var rect=N.Node(name,parent);rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(.5f,.5f);rect.sizeDelta=new Vector2(width,0);
   var fitter=rect.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();fitter.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
   N.Column(rect.gameObject,0);return rect;
  }

  void BuildOverlay(){
   // Offline earnings, shown over everything until collected (same as the app's modal).
   var dim=Fill(root,"OfflineModal",new Color(.18f,.12f,.07f,.55f),true);modal=dim.gameObject;
   offlineCard=N.Create(Centered(dim,"Box",460));offlineCard.Clicked=Press;modal.SetActive(false);

   // Loading / host stopped screen.
   var back=Fill(root,"Status",new Color(.18f,.12f,.07f,.7f),true);status=back.gameObject;
   var box=Centered(back,"Box",520);var face=Panel(box,"Panel",0,120,out _,out _,20);
   statusText=N.Text(face,"Text",K.Headline,24,K.Ink);statusText.alignment=TextAlignmentOptions.Center;
   var tr=statusText.rectTransform;tr.anchorMin=Vector2.zero;tr.anchorMax=Vector2.one;tr.offsetMin=new Vector2(20,10);tr.offsetMax=new Vector2(-20,-10);

   // Toast just above the toolbar.
   toast=N.Node("Toast",root);toast.anchorMin=toast.anchorMax=toast.pivot=new Vector2(.5f,0);toast.anchoredPosition=new Vector2(0,132);
   var fitter=toast.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();fitter.horizontalFit=fitter.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
   toastEdge=toast.gameObject.AddComponent<UnityEngine.UI.Image>();toastEdge.sprite=K.Rounded(18);toastEdge.type=UnityEngine.UI.Image.Type.Sliced;toastEdge.raycastTarget=false;
   N.Column(toast.gameObject,0,new RectOffset(2,2,2,5));
   toastFace=N.Image(toast,"Face",Color.white,16);N.Row(toastFace.gameObject,0,new RectOffset(22,22,10,10));
   toastText=N.Text(toastFace.transform,"Text",K.Label,18,Color.white);toastText.textWrappingMode=TextWrappingModes.NoWrap;
   toast.gameObject.SetActive(false);
  }

  void ApplyOverlay(DesktopView v){
   status.SetActive(false);
   modal.SetActive(v.hasOffline&&v.offline!=null);if(modal.activeSelf)offlineCard.Apply(v.offline);
  }
  public void Offline(string message){status.SetActive(true);statusText.text=message;}

  void Toast(string message,bool ok){
   if(string.IsNullOrEmpty(message))return;
   var style=K.Variant(ok?"success":"danger",true,false);toastEdge.color=style.edge;toastFace.color=style.face;toastText.color=style.text;
   toastText.text=message;toast.gameObject.SetActive(true);toast.SetAsLastSibling();toastUntil=Time.unscaledTime+2.4f;
  }
  void UpdateToast(){if(toast.gameObject.activeSelf&&Time.unscaledTime>toastUntil)toast.gameObject.SetActive(false);}
 }
}
