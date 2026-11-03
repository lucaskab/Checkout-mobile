using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // Rankings v1 in the Editor ("rankings-phone"): on the QA copy of the save, against the host's fake server
 // (desktop/rankings-mock.ts behind desktop/social-mock.ts). The Ranking window opened from the HUD's corner menu, every
 // tab (Mundo, País, Amigos, Liga), the podium and my pinned row, round faces only, joining the league by earning points,
 // a league_reward applied once across a lost ack (diamonds up exactly once) with the end-of-week card, the save
 // untouched by just looking, opted out, signed out, English and the iPad. Shots Logs/at_rank_*.png; RESULT lines in
 // Logs/autotest_log.txt.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Rankings(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-rank-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Tick()=>CheckoutBridge.Emit("{\"kind\":\"social-tick\",\"reason\":\"qa\"}");
   void Mock(string cmd,string arg="")=>Act("socialMock",arg==""?"[\""+cmd+"\"]":"[\""+cmd+"\",\""+arg+"\"]");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT rankings {name}: {(ok?"PASS":"FAIL")} {detail}");
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   string savePath=Path.Combine(Application.persistentDataPath,"checkout-qa-save.json");
   string SaveText(){try{return File.ReadAllText(savePath);}catch{return "";}}
   const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   T Field<T>(string name) where T:class=>typeof(CheckoutDesktopHUD).GetField(name,F)?.GetValue(hud) as T;
   IEnumerator Quiet(){for(float t=0;t<25&&hud&&hud.SocialToastShowing;t+=.5f)yield return new WaitForSecondsRealtime(.5f);yield return new WaitForSecondsRealtime(.4f);}
   IEnumerator Shot2(string name){yield return Shot(name);Note($"rankings: fold {name}: {Fold()} {RankState()}");}
   IEnumerator Tips(){for(int i=0;i<3&&hud&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}}
   IEnumerator Tab(string tab,float wait=2f){Route("~ranking:"+tab);yield return new WaitForSecondsRealtime(wait);}
   // The open board's ranking pieces: podium shown, pinned row title, faces drawn without their round clip (must be 0).
   string RankState(){
    var podium=Field<RectTransform>("rankPodium");var pinned=Field<Component>("rankPinned");
    string pinnedTitle="";if(pinned&&pinned.gameObject.activeSelf){var tmp=pinned.GetComponentsInChildren<TMPro.TextMeshProUGUI>(false).FirstOrDefault(x=>x.name=="Title");pinnedTitle=tmp?tmp.text:"";}
    return $"podium {(podium&&podium.gameObject.activeInHierarchy?"on":"off")}, pinned '{pinnedTitle}', square faces {SquareFaces()}";
   }
   int SquareFaces(){
    int bad=0;var tiles=Field<System.Collections.IEnumerable>("boardTiles");
    if(tiles!=null)foreach(var o in tiles){if(o is not Component c||!c.gameObject.activeInHierarchy)continue;
     var face=(bool)(c.GetType().GetField("isFace",F)?.GetValue(c)??false);var clip=c.GetType().GetField("clip",F)?.GetValue(c) as UnityEngine.UI.Image;
     if(face&&(!clip||!clip.enabled))bad++;}
    return bad;
   }
   bool PodiumOn(){var p=Field<RectTransform>("rankPodium");return p&&p.gameObject.activeInHierarchy;}
   string PinnedTitle(){var pinned=Field<Component>("rankPinned");if(!pinned||!pinned.gameObject.activeInHierarchy)return "";var t=pinned.GetComponentsInChildren<TMPro.TextMeshProUGUI>(false).FirstOrDefault(x=>x.name=="Title");return t?t.text:"";}
   int Rows(){var tiles=Field<System.Collections.IEnumerable>("boardTiles");int n=0;if(tiles!=null)foreach(var o in tiles)if(o is Component c&&c.gameObject.activeInHierarchy)n++;return n;}
   string Route0()=>typeof(CheckoutDesktopHUD).GetField("boardRouteShown",F)?.GetValue(hud) as string??"";

   Note("rankings: "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld);
   for(float t=0;t<15&&!CheckoutSocial.Active;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(4f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
   yield return Tips();
   var langBefore=CheckoutI18n.Language;

   // 1. From the HUD: the corner menu has "Ranking" next to "Amigos"; a tap opens the full-screen window.
   var setQuick=typeof(CheckoutDesktopHUD).GetMethod("SetQuickOpen",F);
   setQuick?.Invoke(hud,new object[]{true});yield return new WaitForSecondsRealtime(.8f);
   yield return Shot("rank_hud_menu");
   var rankButton=hud.GetComponentsInChildren<CheckoutDesktopButton>(false).FirstOrDefault(b=>b.Data!=null&&b.Data.label=="Ranking");
   Note("rankings: HUD button "+(rankButton?"found ("+rankButton.Data.route+")":"missing"));
   if(rankButton){var at=ScreenOf(rankButton.transform);ExecuteEvents.Execute(rankButton.gameObject,new PointerEventData(EventSystem.current){position=at,pressPosition=at,button=PointerEventData.InputButton.Left},ExecuteEvents.pointerClickHandler);}
   yield return new WaitForSecondsRealtime(2.5f);
   Result("Ranking opens from the HUD",rankButton&&CheckoutDesktopHUD.BoardOpen&&Route0().StartsWith("ranking"),$"button {(rankButton?"yes":"no")} board {CheckoutDesktopHUD.BoardOpen} route {Route0()}");
   setQuick?.Invoke(hud,new object[]{false});

   // 2. Just looking never writes the save (the market is closed: nothing else runs into it).
   var saveBefore=SaveText();
   foreach(var tab in new[]{"mundo","pais","amigos","liga","mundo"})yield return Tab(tab,1.6f);
   yield return new WaitForSecondsRealtime(2f);
   var saveAfter=SaveText();
   Result("viewing leaves the save unchanged",saveBefore.Length>0&&saveBefore==saveAfter,$"{saveBefore.Length} -> {saveAfter.Length} chars, rankings slice same {Slice(saveBefore,"rankings")==Slice(saveAfter,"rankings")}");

   // 3. Every tab renders: Mundo / País with the podium and my pinned row, Amigos with its columns, Liga before joining.
   yield return Tab("mundo");yield return Quiet();
   Result("Mundo: podium, rows and my pinned row",PodiumOn()&&Rows()>=90&&PinnedTitle().StartsWith("Você"),$"rows {Rows()} pinned '{PinnedTitle()}'");
   Result("round faces only (Mundo)",SquareFaces()==0,$"square {SquareFaces()}");
   yield return Shot2("rank_mundo_pt");
   // "Ver minha posição" when I am in my country's top 100
   yield return Tab("pais");yield return Quiet();
   Result("País: podium and pinned row",PodiumOn()&&Rows()>0&&PinnedTitle().StartsWith("Você"),$"rows {Rows()} pinned '{PinnedTitle()}'");
   yield return Shot2("rank_pais_pt");
   var pinnedTile=Field<Component>("rankPinned");
   var see=pinnedTile?pinnedTile.GetComponentsInChildren<CheckoutDesktopButton>(false).FirstOrDefault(b=>b.Data!=null&&!string.IsNullOrEmpty(b.Data.action)):null;
   if(see){see.Clicked?.Invoke(see);yield return new WaitForSecondsRealtime(1.6f);yield return Shot2("rank_pais_me_pt");}
   Note("rankings: Ver minha posição "+(see?"pressed":"not offered (outside the top 100)"));
   yield return Tab("amigos");yield return Quiet();
   Result("Amigos: friends board with the invite row",Rows()>=2,$"rows {Rows()}");
   yield return Shot2("rank_amigos_pt");
   Act("rankingColumn","[\"curtidas\"]");yield return new WaitForSecondsRealtime(1.2f);yield return Shot2("rank_amigos_curtidas_pt");
   Act("rankingColumn","[\"nivel\"]");
   yield return Tab("liga");yield return Quiet();
   Result("Liga before joining: how to earn points",Rows()>=5,$"rows {Rows()}");
   yield return Shot2("rank_liga_before_pt");

   // 4. Earning points joins the league: a help on a friend's build (+5), sent at once (as on pause / day end).
   Act("socialHelp","[\"u-ana\",\"evolution:evolucao-shelf-produce-2-ana\"]");yield return new WaitForSecondsRealtime(1.5f);
   CheckoutBridge.Emit("{\"kind\":\"rankings-pause\",\"reason\":\"qa\"}");yield return new WaitForSecondsRealtime(2f);
   Act("rankingRefresh","[]");yield return new WaitForSecondsRealtime(2f);
   yield return Tab("liga");yield return Quiet();
   Result("joined the league by earning points",Rows()>=29&&PinnedTitle().StartsWith("Você · #"),$"rows {Rows()} pinned '{PinnedTitle()}'");
   Result("round faces only (Liga)",SquareFaces()==0,$"square {SquareFaces()}");
   yield return Shot2("rank_liga_pt");

   // 5. The end of the week: a league_reward whose ack is lost (the app "died") pays once; the card shows.
   double gems=bridge.State.diamonds;
   Mock("league-reward");Mock("fail","/v1/social/inbox/ack");yield return new WaitForSecondsRealtime(.5f);
   Tick();yield return new WaitForSecondsRealtime(1.2f);
   Note("rankings: card "+(hud.LeagueCardOpen?"open":"closed"));
   yield return new WaitForSecondsRealtime(.4f);yield return Shot("rank_reward_anim_pt");
   yield return new WaitForSecondsRealtime(3.4f);yield return Shot("rank_reward_card_pt");
   Tick();yield return new WaitForSecondsRealtime(3f);
   double gems1=bridge.State.diamonds;
   Result("league reward applied once across a lost ack",gems1==gems+15,$"diamonds {gems} -> {gems1}");
   Result("end-of-week card shown",hud.LeagueCardOpen,hud.LeagueCardQa);
   var cont=Field<CheckoutDesktopButton>("leagueButton");if(cont)cont.Clicked?.Invoke(cont);
   yield return new WaitForSecondsRealtime(2f);
   Result("card closes and stays closed",!hud.LeagueCardOpen&&bridge.State.diamonds==gems1,$"open {hud.LeagueCardOpen} diamonds {bridge.State.diamonds}");

   // 6. "Aparecer no ranking": off and back on.
   yield return Tab("mundo");
   Act("rankingOptOut","[true]");yield return new WaitForSecondsRealtime(2.5f);yield return Quiet();
   Result("opt-out hides my place",PinnedTitle()=="Você",$"pinned '{PinnedTitle()}'");
   yield return Shot2("rank_mundo_optout_pt");
   Act("rankingOptOut","[false]");yield return new WaitForSecondsRealtime(2.5f);yield return Quiet();

   // 7. Signed out: Mundo stays readable with the sign-in card.
   Mock("signed-out");Act("rankingRefresh","[]");yield return new WaitForSecondsRealtime(2f);yield return Tab("mundo");yield return Quiet();
   Result("signed out: boards read-only with the sign-in card",PodiumOn()&&PinnedTitle()=="",$"podium {PodiumOn()} pinned '{PinnedTitle()}'");
   yield return Shot2("rank_signedout_pt");
   yield return Tab("liga");yield return Shot2("rank_signedout_liga_pt");
   Mock("signed-out","off");Act("rankingRefresh","[]");yield return new WaitForSecondsRealtime(1.5f);

   // 8. English (Lucas plays in English: no Portuguese may leak), and the card in English.
   Lang("en");yield return new WaitForSecondsRealtime(1.5f);
   foreach(var tab in new[]{"mundo","pais","amigos","liga"}){yield return Tab(tab);yield return Quiet();yield return Shot2("rank_"+tab+"_en");}
   Mock("league-reward","2026-W40");Tick();yield return new WaitForSecondsRealtime(5f);yield return Shot("rank_reward_card_en");
   cont=Field<CheckoutDesktopButton>("leagueButton");if(cont&&hud.LeagueCardOpen)cont.Clicked?.Invoke(cont);yield return new WaitForSecondsRealtime(1.5f);
   Lang(langBefore);yield return new WaitForSecondsRealtime(1f);

   // 9. iPad (4:3): Mundo, Liga and the card lay out.
   Note("rankings: "+CheckoutQaGameView.Set(2048,1536));yield return new WaitForSecondsRealtime(2.5f);
   foreach(var tab in new[]{"mundo","liga"}){yield return Tab(tab,2.5f);yield return Quiet();yield return Shot2("rank_"+tab+"_ipad");}
   Mock("league-reward","2026-W39");Tick();yield return new WaitForSecondsRealtime(5f);yield return Shot("rank_reward_card_ipad");
   cont=Field<CheckoutDesktopButton>("leagueButton");if(cont&&hud.LeagueCardOpen)cont.Clicked?.Invoke(cont);yield return new WaitForSecondsRealtime(1.5f);
   Note("rankings: "+CheckoutQaGameView.Set(2778,1284));yield return new WaitForSecondsRealtime(2f);
   Route("");yield return new WaitForSecondsRealtime(1f);
  }

  /// <summary>The JSON object stored under "key" in a save text (brace matched; "" when absent).</summary>
  static string Slice(string json,string key){
   int at=json.IndexOf("\""+key+"\":",System.StringComparison.Ordinal);if(at<0)return "";
   int start=json.IndexOf('{',at);if(start<0)return "";
   int depth=0;bool str=false;
   for(int i=start;i<json.Length;i++){char c=json[i];
    if(str){if(c=='\\')i++;else if(c=='"')str=false;continue;}
    if(c=='"')str=true;else if(c=='{')depth++;else if(c=='}'&&--depth==0)return json.Substring(start,i-start+1);}
   return "";
  }
 }
}
