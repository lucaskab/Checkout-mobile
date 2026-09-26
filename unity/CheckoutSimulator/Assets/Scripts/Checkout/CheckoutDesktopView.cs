using System;
namespace Checkout {
 // Mirrors desktop/view.ts and desktop/view-kit.ts. JsonUtility reads these as-is.
 [Serializable] public class DesktopButton {
  public string label,icon,variant,action,args,route,after,ok,fail;public bool enabled,active;
 }
 [Serializable] public class DesktopCard {
  public string title,eyebrow,subtitle,icon,badge,tone;public string[] lines;public float progress=-1;public DesktopButton[] buttons;
 }
 [Serializable] public class DesktopPage {
  public string route,title,subtitle,icon;public DesktopButton[] chips;public DesktopCard[] cards;
 }
 [Serializable] public class DesktopView {
  public string kind;public int revision,level,xp,xpGoal,claimableMissions;
  public string progressLabel,progressRoute,coins,diamonds,daily,eventName,eventTimer,eventEffect,eventIcon;
  public bool isOpen,dailyClaimable,hasEvent,eventNegative,hasOffline,hasPage,canBack;public float dailyProgress;
  public string dayPhase,dayTitle,dayDetail,requestLabel;public float dayProgress;public int requestCount;public bool requestUrgent;
  public DesktopButton[] tools;public DesktopCard offline;public DesktopPage page;
 }
 [Serializable] public class DesktopResult {public string kind,id,action,reason;public bool ok;}
}
