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
  public string route,title,subtitle,icon,layout;public DesktopButton[] tabs,chips;public DesktopCard[] cards;public DesktopShelf shelf;
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
  public DesktopButton[] tools;public DesktopCard offline;public DesktopPage page;
 }
 [Serializable] public class DesktopResult {public string kind,id,action,reason;public bool ok;}
}
