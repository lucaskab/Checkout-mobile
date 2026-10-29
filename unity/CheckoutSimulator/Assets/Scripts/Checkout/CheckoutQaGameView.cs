using System;
using System.Reflection;
using UnityEngine;

namespace Checkout {
 // Editor-only helper for the QA runs (CheckoutAutoTest "onboarding-…"): sets the Game view to a fixed resolution
 // (an iPhone, an iPad, a desktop window) through the editor's internal GameViewSizes, and puts the size the player
 // had back at the end. Does nothing in a build.
 public static class CheckoutQaGameView {
#if UNITY_EDITOR
  const BindingFlags All=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static|BindingFlags.FlattenHierarchy;
  static int restoreIndex=-1;
  static object Get(object o,Type t,string name){var p=t.GetProperty(name,All);if(p!=null)return p.GetValue(p.GetGetMethod(true).IsStatic?null:o);var f=t.GetField(name,All);return f?.GetValue(f.IsStatic?null:o);}
  static Type T(string name)=>typeof(UnityEditor.EditorWindow).Assembly.GetType(name);
  static object Group(){
   var sizes=T("UnityEditor.GameViewSizes");var single=typeof(UnityEditor.ScriptableSingleton<>).MakeGenericType(sizes);
   var inst=single.GetProperty("instance",All).GetValue(null);
   var groupType=Get(inst,sizes,"currentGroupType");
   return sizes.GetMethod("GetGroup",All).Invoke(inst,new[]{groupType});
  }
  static UnityEngine.Object View(){var t=T("UnityEditor.GameView");var views=Resources.FindObjectsOfTypeAll(t);return views.Length>0?views[0]:null;}
  static int Selected(UnityEngine.Object view)=>view?(int)Get(view,view.GetType(),"selectedSizeIndex"):-1;
  static void Select(UnityEngine.Object view,int index){
   var t=view.GetType();var cb=t.GetMethod("SizeSelectionCallback",All);
   if(cb!=null)cb.Invoke(view,new object[]{index,null});else t.GetProperty("selectedSizeIndex",All).SetValue(view,index);
   view.GetType().GetMethod("Repaint",All,null,Type.EmptyTypes,null)?.Invoke(view,null);
  }
#endif
  /// <summary>Game view at w x h (a custom fixed size is added once). Returns a line for the test log.</summary>
  public static string Set(int w,int h){
#if UNITY_EDITOR
   try{
    var group=Group();var g=group.GetType();int count=(int)g.GetMethod("GetTotalCount",All).Invoke(group,null);int index=-1;
    for(int i=0;i<count&&index<0;i++){var s=g.GetMethod("GetGameViewSize",All).Invoke(group,new object[]{i});var st=s.GetType();
     if(Convert.ToInt32(Get(s,st,"width"))==w&&Convert.ToInt32(Get(s,st,"height"))==h&&Convert.ToInt32(Get(s,st,"sizeType"))==1)index=i;}
    if(index<0){
     var sizeT=T("UnityEditor.GameViewSize");var kind=T("UnityEditor.GameViewSizeType");
     var size=sizeT.GetConstructor(new[]{kind,typeof(int),typeof(int),typeof(string)}).Invoke(new object[]{Enum.ToObject(kind,1),w,h,"QA "+w+"x"+h});
     g.GetMethod("AddCustomSize",All).Invoke(group,new[]{size});index=count;
    }
    var view=View();if(!view)return "no Game view";
    if(restoreIndex<0)restoreIndex=Selected(view);
    Select(view,index);return $"game view size #{index} {w}x{h} (was #{restoreIndex})";
   }catch(Exception e){return "game view size failed: "+e.GetType().Name+" "+e.Message;}
#else
   return "not in the editor";
#endif
  }
  /// <summary>Puts back the size the Game view had before the first Set.</summary>
  public static void Restore(){
#if UNITY_EDITOR
   try{var view=View();if(view&&restoreIndex>=0)Select(view,restoreIndex);}catch{}
   restoreIndex=-1;
#endif
  }
 }
}
