using System;
namespace Checkout {
 // Mirrors desktop/view.ts and desktop/view-kit.ts. JsonUtility reads these as-is.
 [Serializable] public class DesktopButton {
  public string label,icon,variant,action,args,route,after,ok,fail,badge;public bool enabled,active;
 }
 [Serializable] public class DesktopCard {
  public string title,eyebrow,subtitle,icon,badge,tone;public string[] lines;public float progress=-1;public DesktopButton[] buttons;
 }
 [Serializable] public class DesktopPage {
  public string route,title,subtitle,icon,layout;public DesktopButton[] tabs,chips;public DesktopCard[] cards;public DesktopShelf shelf;public DesktopBoard board;public DesktopKitchen kitchen;
 }
 // Game windows built from tiles (layout "board"): mirrors BoardView / BoardTile / BoardMeter / BoardStat of desktop/view-kit.ts.
 [Serializable] public class DesktopStat {public string icon,value,label,tone;}
 [Serializable] public class DesktopMark {public float at;public string icon,label,state;public DesktopButton action;}
 [Serializable] public class DesktopMeter {public string title,icon,text,tone;public float value,max;public DesktopMark[] marks;}
 [Serializable] public class DesktopTile {
  public string id,group,icon,title,subtitle,sticker,tone,badge,fillText,state,detail,origin,originLabel,vehicle,lane;
  public int stars,maxStars;public float fill=-1;public double timerEnd,timerTotal;
  public DesktopButton action;public DesktopStat[] facts;public string[] lines;public DesktopButton[] actions;
 }
 [Serializable] public class DesktopBoard {
  public string tint,backdrop,tip,style,empty,focus;public int columns;public double now;
  public DesktopStat[] stats;public DesktopMeter meter;public DesktopTile[] tiles;public DesktopButton[] footer;
 }
 // The hand-made production game (layout "kitchen"): mirrors KitchenView / KitchenStep / KitchenItem of desktop/view-kit.ts.
 [Serializable] public class DesktopKitchenItem {public string icon,label;}
 [Serializable] public class DesktopKitchenStep {
  public string kind,title,hint,art,back,unit,gauge,tool,done;public string[] states;public float[] at,lines,spots,zone,scale;
  public float size,seconds,dir,slow;public int count;public DesktopKitchenItem[] items;
 }
 [Serializable] public class DesktopKitchen {
  public string recipeId,sectorId,title,icon,tint,bench,back,reason;public int output,demo=-1;public bool canCook;public DesktopKitchenStep[] steps;
 }
 // The shelf window (layout "shelf"): mirrors ShelfView / ShelfSlotView / ShelfPickView of desktop/view-kit.ts.
 [Serializable] public class DesktopShelfSlot {
  public string slotId,state,row,name,icon,mood,moodTone,incoming;
  public int index,productId,stock,capacity,reserve,price,minPrice,maxPrice,suggested,cost,level,maxLevel,upgradeCost,restockAmount,unlockCost,unlockLevel;
 }
 [Serializable] public class DesktopShelfPick {public string name,icon,category;public int productId,reserve,price,profit;}
 [Serializable] public class DesktopShelf {
  public string id,kind,art,tint,name,accepts,careTitle,careVerb,careHint,careSpot,rowTop,rowBottom,stallNote;
  public int condition,slotCount,expandCost,expandLevel,capacity,capacityNext,capacityCost,capacityLevel;
  public DesktopShelfSlot[] slots;public DesktopShelfPick[] picks;
 }
 [Serializable] public class DesktopView {
  public string kind;public int revision,level,xp,xpGoal,claimableMissions;
  public string progressLabel,progressRoute,coins,diamonds,daily,eventName,eventTimer,eventEffect,eventIcon;
  public bool isOpen,dailyClaimable,hasEvent,eventNegative,hasOffline,hasPage,canBack;public float dailyProgress;
  public string dayPhase,dayTitle,dayDetail,requestLabel,goalText,goalIcon;public bool goalDone;public float dayProgress;public int requestCount;public bool requestUrgent;
  public DesktopBoost[] boosts;
  public DesktopButton[] tools;public DesktopCard offline;public DesktopPage page;public DesktopLevelUp levelUp;public DesktopCelebration celebration;
  public DesktopCoach coach;public DesktopGoal goal;
 }
 // Dona Neide's tutorial / tip card (src/services/onboarding.ts CoachView); key "" = nothing on screen.
 [Serializable] public class DesktopCoach {
  public string key,mode,speaker,art,title,text,gameText,target,button,buttonAction,rewardKey,rewardText;
  public bool canSkip,isTip;public int step,total;public string[] path;
 }
 // The next big objective under the top bar (src/services/onboarding.ts GoalView); text "" = none.
 [Serializable] public class DesktopGoal {public string text,detail,icon,route;public float progress=-1;}
 // Level-up celebration (desktop/level-up.ts); JsonUtility fills a null with an empty object: an empty key means none.
 [Serializable] public class DesktopLevelUpItem {public string icon,title,detail,tag;}
 [Serializable] public class DesktopLevelUpGroup {public string title,hint,icon,tint,button,route;public DesktopLevelUpItem[] items;}
 [Serializable] public class DesktopCelebrationChip {public string icon,text;}
 [Serializable] public class DesktopCelebration {public string key,id,kind,headline,title,subtitle,icon,tint,button,route,lotId;public DesktopCelebrationChip[] chips;}
 [Serializable] public class DesktopLevelUp {public string key,headline,subtitle,empty,next;public int from,to,total,xp,xpGoal;public DesktopLevelUpGroup[] groups;}
 // A booster running now (desktop/view.ts BoostView): seconds left, full length and the colour of its aura.
 [Serializable] public class DesktopBoost {public string id,name,icon,effect,tint;public int seconds,total;}
 [Serializable] public class DesktopResult {public string kind,id,action,reason;public bool ok;}
}
