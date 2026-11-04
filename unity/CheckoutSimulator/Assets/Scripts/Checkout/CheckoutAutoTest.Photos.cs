using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace Checkout {
 // Friends' Google photos in the Editor ("eventsphotos-phone"; "events…" runs on the QA copy of the save), against the host's fake server
 // (desktop/social-mock.ts, control "photos"). The Editor cannot count on reaching Google, so the QA puts two local
 // pictures in the photo cache as if Google had sent them (mine and Ana's); Gabi's address is never cached (the real
 // download is tried and fails: her avatar stays); Bruno turned his photo off, Carla is on Apple, Duda (a stranger's
 // request) never gets a photo from the server. Checks: Amigos list + my strip, my profile with the switch (off → my
 // avatar), the Amigos ranking (podium, rows, rival), Mundo without photos, the visit bar, and the fallback with the
 // cache emptied and offline. Every face round (no square corners). Shots Logs/at_ps_*.png at the iPhone's size.
 public sealed partial class CheckoutAutoTest {
  // The mock's addresses (desktop/social-mock.ts › MOCK_PHOTOS).
  const string PhotoMe="https://lh3.googleusercontent.com/a/qa-photo-me=s96-c";
  const string PhotoAna="https://lh3.googleusercontent.com/a/qa-photo-ana=s96-c";
  const string PhotoGabi="https://lh3.googleusercontent.com/a/qa-photo-unreachable=s96-c";

  IEnumerator Photos(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-photos-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Mock(string cmd,string arg="")=>Act("socialMock",arg==""?"[\""+cmd+"\"]":"[\""+cmd+"\",\""+arg+"\"]");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT photos {name}: {(ok?"PASS":"FAIL")} {detail}");
   const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   IEnumerator Tips(){for(int i=0;i<3&&hud&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}}
   IEnumerator Quiet(){for(float t=0;t<25&&hud&&hud.SocialToastShowing;t+=.5f)yield return new WaitForSecondsRealtime(.5f);yield return new WaitForSecondsRealtime(.4f);}
   // Faces on screen drawn from a photo, and faces (tiles) drawn without their round clip (must stay 0).
   int PhotoFaces()=>hud?hud.GetComponentsInChildren<UnityEngine.UI.Image>(false).Count(i=>i.enabled&&i.sprite&&i.sprite.texture&&i.sprite.texture.name=="Friend photo"):0;
   int SquareFaces(){
    int bad=0;var tiles=typeof(CheckoutDesktopHUD).GetField("boardTiles",F)?.GetValue(hud) as System.Collections.IEnumerable;
    if(tiles!=null)foreach(var o in tiles){if(o is not Component c||!c.gameObject.activeInHierarchy)continue;
     var face=(bool)(c.GetType().GetField("isFace",F)?.GetValue(c)??false);var clip=c.GetType().GetField("clip",F)?.GetValue(c) as UnityEngine.UI.Image;
     if(face&&(!clip||!clip.enabled))bad++;}
    return bad;
   }
   IEnumerator Shot2(string name){yield return Shot(name);Note($"photos: {name}: photo faces {PhotoFaces()}, square faces {SquareFaces()}, fold {Fold()}");}

   Note("photos: "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld);
   for(float t=0;t<15&&!CheckoutSocial.Active;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(4f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
   yield return Tips();

   // 0. The two local pictures, as if Google had sent them (written to the disk cache, read back like real ones).
   CheckoutPhotos.QaForgetMemory();CheckoutPhotos.Offline=false;
   CheckoutPhotos.QaSeed(PhotoMe,QaPortrait(new Color(.98f,.78f,.45f),new Color(.86f,.62f,.47f),new Color(.12f,.42f,.55f)));
   CheckoutPhotos.QaSeed(PhotoAna,QaPortrait(new Color(.55f,.78f,.93f),new Color(.62f,.44f,.33f),new Color(.82f,.25f,.32f)));
   Result("sized address asks Google for a 128 px square",CheckoutPhotos.Sized(PhotoAna).EndsWith("=s128-c")&&CheckoutPhotos.Sized("https://lh5.googleusercontent.com/-x/AAA/s96-c/photo.jpg").Contains("/s128-c/"),CheckoutPhotos.Sized(PhotoAna));
   Result("only Google's image hosts over https",CheckoutPhotos.IsAllowed(PhotoAna)&&!CheckoutPhotos.IsAllowed("http://lh3.googleusercontent.com/a/x")&&!CheckoutPhotos.IsAllowed("https://lh3.googleusercontent.com.evil.example/a")&&!CheckoutPhotos.IsAllowed("file:///etc/passwd"),"");

   // 1. Amigos: a name first if this copy has none, then the friends' photos.
   Route("!amigos");yield return new WaitForSecondsRealtime(2.5f);yield return Tips();
   Act("socialSaveProfile","[\"Mercadinho do Lucas\",\"shopper-4\"]");yield return new WaitForSecondsRealtime(1.5f);
   Mock("photos");Act("socialRefresh","[]");yield return new WaitForSecondsRealtime(1.5f);
   Route("~amigos");yield return new WaitForSecondsRealtime(1.5f);
   // the first view asks for the photos: they arrive a moment later (the avatars meanwhile, never a blocked UI)
   int early=PhotoFaces();
   for(float t=0;t<12&&!(CheckoutPhotos.QaReady(PhotoAna)&&CheckoutPhotos.QaReady(PhotoMe));t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(1.6f);yield return Quiet();
   yield return Shot2("ps_amigos");
   int faces=PhotoFaces();
   Result("Amigos shows my photo and Ana's from the cache, the others their avatars",faces>=2&&SquareFaces()==0,$"photo faces {early} at first, then {faces}; disk reads {CheckoutPhotos.FromDisk}");
   // Gabi's address: the real download is tried (no Google picture there): her avatar stays.
   for(float t=0;t<14&&CheckoutPhotos.Failed==0;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   Result("an address that cannot be downloaded keeps the avatar",!CheckoutPhotos.QaReady(PhotoGabi)&&CheckoutPhotos.Failed>=1,$"failed {CheckoutPhotos.Failed}, downloaded {CheckoutPhotos.Downloaded}");

   // 2. My profile: my photo on the card, the switch; off → my avatar for friends.
   Route("~amigos:perfil");yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();
   yield return Shot2("ps_profile");
   Act("socialShowPhoto","[false]");yield return new WaitForSecondsRealtime(1.6f);yield return Quiet();
   yield return Shot2("ps_profile_off");
   Result("switch off: my card shows my avatar",PhotoFaces()==0,$"photo faces {PhotoFaces()}");
   Act("socialShowPhoto","[true]");yield return new WaitForSecondsRealtime(1.4f);yield return Quiet();

   // 3. The Amigos ranking: podium, rows and the rival card with photos; Mundo without any.
   Route("~ranking:amigos");yield return new WaitForSecondsRealtime(2.5f);yield return Quiet();
   yield return Shot2("ps_rank_amigos");
   var rival=typeof(CheckoutDesktopHUD).GetField("rivalMeFace",F)?.GetValue(hud) as UnityEngine.UI.Image;
   Result("friends board: photos on the board and my face on the rival card",PhotoFaces()>=2&&rival&&rival.sprite&&rival.sprite.texture&&rival.sprite.texture.name=="Friend photo"&&SquareFaces()==0,$"photo faces {PhotoFaces()}, rival {(rival&&rival.sprite?rival.sprite.texture.name:"none")}");
   Route("~ranking:mundo");yield return new WaitForSecondsRealtime(2.5f);yield return Quiet();
   yield return Shot2("ps_rank_mundo");
   Result("Mundo keeps the avatars (no photos)",PhotoFaces()==0,$"photo faces {PhotoFaces()}");
   Route("~ranking:liga");yield return new WaitForSecondsRealtime(2.5f);yield return Quiet();
   Result("Liga keeps the avatars (no photos)",PhotoFaces()==0,$"photo faces {PhotoFaces()}");
   Route("");yield return new WaitForSecondsRealtime(1f);

   // 4. The visit bar: Ana's photo.
   Act("socialVisit","[\"u-ana\"]");
   for(float t=0;t<15&&!(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(4f);yield return Quiet();
   var visitAvatar=typeof(CheckoutDesktopHUD).GetField("visitAvatar",F)?.GetValue(hud) as UnityEngine.UI.Image;
   yield return Shot("ps_visit");
   Result("visit bar shows the friend's photo",visitAvatar&&visitAvatar.sprite&&visitAvatar.sprite.texture&&visitAvatar.sprite.texture.name=="Friend photo",visitAvatar&&visitAvatar.sprite?visitAvatar.sprite.texture.name:"none");
   Act("socialLeave","[]");
   for(float t=0;t<10&&(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(3f);

   // 5. Fallback: nothing cached and offline → every face is an avatar, the page works as before.
   CheckoutPhotos.QaDelete(PhotoMe,PhotoAna);CheckoutPhotos.QaForgetMemory();CheckoutPhotos.Offline=true;
   Route("!amigos");yield return new WaitForSecondsRealtime(3f);yield return Quiet();
   yield return Shot2("ps_amigos_fallback");
   Result("no photo reachable: avatars everywhere, round",PhotoFaces()==0&&SquareFaces()==0&&CheckoutDesktopHUD.BoardOpen,$"photo faces {PhotoFaces()}, failed {CheckoutPhotos.Failed}");

   // English: the switch's words translated.
   CheckoutI18n.SetLanguage("en");CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"en\"}");yield return new WaitForSecondsRealtime(1.2f);
   Route("~amigos:perfil");yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();yield return Shot2("ps_profile_en");
   CheckoutI18n.SetLanguage("pt");CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"pt\"}");yield return new WaitForSecondsRealtime(.8f);
   CheckoutPhotos.Offline=false;CheckoutPhotos.QaForgetMemory();
   Route("");yield return new WaitForSecondsRealtime(1f);
  }

  /// <summary>A stand-in "photo" (head and shoulders on a soft background, a little grain): only for the QA cache.</summary>
  static Texture2D QaPortrait(Color back,Color skin,Color shirt){
   const int n=128;var t=new Texture2D(n,n,TextureFormat.RGBA32,false);var px=new Color32[n*n];var rng=new System.Random(n+(int)(back.r*1000));
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float u=x/(float)n,v=y/(float)n;Color c=Color.Lerp(back*.75f,back,v);c.a=1;
    float hx=u-.5f,hy=v-.6f;if(hx*hx/.028f+hy*hy/.04f<1)c=Color.Lerp(skin,skin*.85f,Mathf.Clamp01(hx*3+.5f));
    float hairY=v-.72f;if(hx*hx/.034f+hairY*hairY/.012f<1&&v>.66f)c=new Color(.22f,.15f,.1f);
    float sx=u-.5f,sy=v+.05f;if(sx*sx/.12f+sy*sy/.1f<1&&v<.38f)c=Color.Lerp(shirt,shirt*.8f,u);
    float g=(float)(rng.NextDouble()-.5)*.05f;px[y*n+x]=new Color(Mathf.Clamp01(c.r+g),Mathf.Clamp01(c.g+g),Mathf.Clamp01(c.b+g),1);
   }
   t.SetPixels32(px);t.Apply();return t;
  }
 }
}
