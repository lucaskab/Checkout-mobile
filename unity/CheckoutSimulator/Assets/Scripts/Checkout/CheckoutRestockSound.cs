using UnityEngine;

namespace Checkout {
 // Sounds of the REPOR mini-game: short, soft recordings (Kenney "Interface Sounds", CC0) filtered below
 // 5 kHz and kept quiet, in Resources/CheckoutDesktop/Restock/Sounds. Like Unpacking, each action has a few
 // variants picked at random and played with a small pitch change, so repeating it never sounds the same.
 public static class CheckoutRestockSound {
  const string Dir="CheckoutDesktop/Restock/Sounds/restock_";
  static AudioClip Load(string name)=>Resources.Load<AudioClip>(Dir+name);
  static AudioClip[] Many(params string[] names){var a=new AudioClip[names.Length];for(int i=0;i<a.Length;i++)a[i]=Load(names[i]);return a;}
  static AudioClip Any(AudioClip[] a)=>a==null||a.Length==0?null:a[Random.Range(0,a.Length)];
  static AudioClip[] place,glass,grab,back;static AudioClip wrong,doorOpen,doorClose,tape,flatten,done,next;
  static bool loaded;
  static void Init(){
   if(loaded)return;loaded=true;
   place=Many("place_1","place_2","place_3");glass=Many("glass_1","glass_2","glass_3");
   grab=Many("grab_1","grab_2");back=Many("back_1","back_2");
   wrong=Load("wrong");doorOpen=Load("door_open");doorClose=Load("door_close");tape=Load("tape");
   flatten=Load("flatten");done=Load("done");next=Load("next");
  }
  public static AudioClip Place(bool glassy){Init();return Any(glassy?glass:place);}
  public static AudioClip Grab{get{Init();return Any(grab);}}
  public static AudioClip Back{get{Init();return Any(back);}}
  public static AudioClip Wrong{get{Init();return wrong;}}
  public static AudioClip DoorOpen{get{Init();return doorOpen;}}
  public static AudioClip DoorClose{get{Init();return doorClose;}}
  public static AudioClip Tape{get{Init();return tape;}}
  public static AudioClip Flatten{get{Init();return flatten;}}
  public static AudioClip Done{get{Init();return done;}}
  public static AudioClip Next{get{Init();return next;}}
  // A small random pitch change around `pitch` (±3%).
  public static float Vary(float pitch=1)=>pitch*Random.Range(.97f,1.03f);
 }
}
