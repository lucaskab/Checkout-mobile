using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Event crowds are the market's real customers (Lucas 15/10: "the events have no interaction with the market: the
 // people at the ATM withdraw money, walk somewhere and vanish. They must go into the market and buy something").
 //
 // While an event with a crowd runs, the app tags a share of the customers it sends (src/data/game-events.ts
 // crowdShare → Customer.origin = the event's id). Those are the same real visits (basket, money at the register,
 // XP): only where their walk starts changes. CheckoutBridge hands them here (TakeVisit) and the scene routes them:
 //  - a line (payday's ATM): the customer arrives on foot, queues with the scene's own people, withdraws the money
 //    (the paying move at the machine) and walks in to shop (CheckoutWalker phases 15 → 16 → 14);
 //  - riders (the rush-hour bus, the school bus): the customer waits "on the bus" (hidden, reserved) until the bus
 //    opens its doors, gets off with the scene's crowd and walks in; the scene shows fewer extras for each real one;
 //  - stops (the street fair, the ice-cream cart, the prize wheel, the offers truck's pallets, the big screen, the
 //    influencer, the pharmacy's clearance): the customer arrives on foot, stops there a moment (buys at the stall,
 //    watches the wheel or the match…) and walks in (phases 15 → 17 → 14).
 // Events about the street or the staff (rain, road works, the jam, the power cut, the card machine, the inspector,
 // the tired shift, the coffee break, the rival's sound car) send no crowd: their customers come as usual (in the
 // rain with umbrellas, SetCustomerUmbrellas).
 public sealed partial class CheckoutEventVisuals {
  /// <summary>How a customer the event brought gets into the market: a start spot (null = on foot from the city, like
  /// any walk-in), a stop on the way (stand/look/pause/clip) or the event's line (payday's ATM).</summary>
  public sealed class LeadIn {public Vector3? start,stand;public Vector3 look;public float pause;public string clip;public bool line;}
  sealed class EventLine {public Func<int,Vector3> slot;public Vector3 front;public int capacity;public readonly List<object> members=new List<object>();public readonly HashSet<object> standing=new HashSet<object>();}
  sealed class Rider {public CheckoutWalker walker;public Customer visit;public string origin;public float since;}
  readonly Dictionary<string,List<LeadIn>> stops=new Dictionary<string,List<LeadIn>>();
  readonly HashSet<string> busScenes=new HashSet<string>();
  readonly Dictionary<string,EventLine> lines=new Dictionary<string,EventLine>();
  readonly List<Rider> riders=new List<Rider>();
  const float RiderPatience=45f;   // a bus loop is ~40 s; past this the customer just walks in

  void ForgetCrowd(string id){stops.Remove(id);busScenes.Remove(id);lines.Remove(id);}
  /// <summary>A stop the event's customers make on their way in (scene building helper).</summary>
  void Stop(Vector3 stand,Vector3 look,float pause=3f,string clip=null){if(!stops.TryGetValue(building,out var l))stops[building]=l=new List<LeadIn>();l.Add(new LeadIn{stand=stand,look=look,pause=pause,clip=clip});}
  /// <summary>This scene's customers arrive by bus: the scene releases them when the doors open (TakeRiders).</summary>
  void BusRiders()=>busScenes.Add(building);

  /// <summary>Called by CheckoutBridge for a visit tagged with an event: true when the scene took it.</summary>
  public bool TakeVisit(Customer visit,CheckoutWalker walker){
   if(visit==null||!walker||string.IsNullOrEmpty(active)||visit.origin!=active||!scenes.ContainsKey(active))return false;
   if(busScenes.Contains(active)){walker.Reserve();riders.Add(new Rider{walker=walker,visit=visit,origin=active,since=Time.time});return true;}
   LeadIn lead=null;
   if(lines.TryGetValue(active,out var line)&&line.members.Count<line.capacity)lead=new LeadIn{line=true};
   else if(stops.TryGetValue(active,out var list)&&list.Count>0)lead=list[UnityEngine.Random.Range(0,list.Count)];
   return lead!=null&&walker.BeginFromEvent(visit,lead);
  }

  /// <summary>The customers waiting on this scene's bus (at most max), handed to the scene to get off.</summary>
  List<Rider> TakeRiders(string id,int max){var taken=new List<Rider>();for(int i=0;i<riders.Count&&taken.Count<max;i++){var r=riders[i];if(r.origin!=id||!r.walker||r.walker.gameObject.activeSelf||!r.walker.Reserved)continue;taken.Add(r);riders.RemoveAt(i);i--;}return taken;}
  /// <summary>A rider gets off at `door` and walks in (or, if no walkable spot is there, simply walks in from the city).</summary>
  static void RiderGetsOff(Rider r,Vector3 door){if(!r.walker.BeginFromEvent(r.visit,new LeadIn{start=door}))r.walker.Begin(r.visit);}

  // Riders whose bus never came (the event ended, the scene could not be built) walk in normally; a closed market
  // sends them home.
  void MarketTick(){
   for(int i=riders.Count-1;i>=0;i--){
    var r=riders[i];
    if(!r.walker||r.walker.gameObject.activeSelf||!r.walker.Reserved){riders.RemoveAt(i);continue;}
    if(!(Bridge?.State?.isOpen??false)){riders.RemoveAt(i);r.walker.CancelVisit();continue;}
    if(r.origin!=active||Time.time-r.since>RiderPatience){riders.RemoveAt(i);r.walker.Begin(r.visit);}
   }
  }
  // The event changed: customers still in its line go straight in (riders are handled by MarketTick).
  void ReleaseCrowd(){foreach(var line in lines.Values){line.members.RemoveAll(m=>m is CheckoutWalker);line.standing.RemoveWhere(m=>m is CheckoutWalker);}}

  // ---------------------------------------------------------------- the line (CheckoutWalker phase 16)
  EventLine LineOf(CheckoutWalker w){if(string.IsNullOrEmpty(active)||!lines.TryGetValue(active,out var line))return null;return line;}
  /// <summary>Where a customer walking to the line would stand (its end); null when the line is full or gone.</summary>
  public Vector3? LineTail(CheckoutWalker w){var line=LineOf(w);if(line==null)return null;int i=line.members.IndexOf(w);if(i<0){if(line.members.Count>=line.capacity)return null;i=line.members.Count;}return line.slot(i);}
  public bool JoinLine(CheckoutWalker w){var line=LineOf(w);if(line==null)return false;if(line.members.Contains(w))return true;if(line.members.Count>=line.capacity)return false;line.members.Add(w);return true;}
  /// <summary>The customer's spot in the line; null once the scene let them go (they walk in) or the line is gone.</summary>
  public Vector3? LineSpot(CheckoutWalker w){var line=LineOf(w);if(line==null)return null;int i=line.members.IndexOf(w);return i<0?(Vector3?)null:line.slot(i);}
  public Vector3 LineLook(CheckoutWalker w){var line=LineOf(w);if(line==null)return w.transform.position;int i=line.members.IndexOf(w);return i<=0?line.front:line.slot(i-1);}
  public bool LineFront(CheckoutWalker w){var line=LineOf(w);return line!=null&&line.members.Count>0&&ReferenceEquals(line.members[0],w);}
  public void LineStanding(CheckoutWalker w,bool standing){var line=LineOf(w);if(line==null)return;if(standing&&line.members.Contains(w))line.standing.Add(w);else line.standing.Remove(w);}
  public void LeaveLine(CheckoutWalker w){foreach(var line in lines.Values){line.members.Remove(w);line.standing.Remove(w);}}
 }
}
