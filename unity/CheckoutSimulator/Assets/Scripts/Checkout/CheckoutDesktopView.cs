using System;
namespace Checkout {
 // Mirrors desktop/view.ts and desktop/view-kit.ts. JsonUtility reads these as-is.
 [Serializable] public class DesktopButton {
  public string label,icon,variant,action,args,route,after,ok,fail,badge;public bool enabled,active;
 }
 [Serializable] public class DesktopCard {
  public string title,eyebrow,subtitle,icon,badge,tone;public string[] lines;public float progress=-1;public DesktopButton[] buttons;
  // Social v1 (desktop/view-kit.ts CardInput, desktop/qr.ts): a text field (id "" = none) and a QR code ("" = none).
  public DesktopInput input;public string qr;
  // Board windows: the cards stand in a row over the tiles; "hero" = the title in large type (a friend code).
  public bool hero;
 }
 /// <summary>A text field on a card: buttons send what was typed with "$input:&lt;id&gt;" in their args.</summary>
 [Serializable] public class DesktopInput {public string id,placeholder,value,kind;public int max;}
 /// <summary>Visiting a friend's market (desktop/social.ts VisitView): the bar on top and an "Ajudar" per build.</summary>
 [Serializable] public class DesktopVisit {
  public bool active;public string friendId,friendName,avatar,subtitle,note;public DesktopButton[] buttons;public DesktopVisitBuild[] builds;
 }
 [Serializable] public class DesktopVisitBuild {public string buildId,kind,targetId,label;public bool helped;public DesktopButton button;}
 [Serializable] public class DesktopPage {
  public string route,title,subtitle,icon,layout;public DesktopButton[] tabs,chips,sections;public DesktopCard[] cards;public DesktopShelf shelf;public DesktopBoard board;public DesktopKitchen kitchen;
 }
 // Game windows built from tiles (layout "board"): mirrors BoardView / BoardTile / BoardMeter / BoardStat of desktop/view-kit.ts.
 [Serializable] public class DesktopStat {public string icon,value,label,tone;}
 [Serializable] public class DesktopMark {public float at;public string icon,label,state;public DesktopButton action;}
 [Serializable] public class DesktopMeter {
  public string title,icon,text,tone;public float value,max;public DesktopMark[] marks;
  // Social v1: the bar as a player strip: buttons at its end, drawn in blocks, a face for the icon that opens a route.
  public DesktopButton[] buttons;public int segments;public string frame,route;
 }
 [Serializable] public class DesktopTile {
  public string id,group,icon,title,subtitle,sticker,tone,badge,fillText,state,detail,origin,originLabel,vehicle,lane;
  public int stars,maxStars;public float fill=-1;public double timerEnd,timerTotal;
  public DesktopButton action;public DesktopStat[] facts;public string[] lines;public DesktopButton[] actions;
  // Social v1: chips under the title (likes, builds to help, a request), a framed portrait, a corner badge (stage)
  // and a second big button (Presente next to Visitar).
  public DesktopStat[] chips;public string frame,corner;public DesktopButton alt;
  // Rankings v1 (frame "rank"): the place, the player's flag ("Flags/br") and the number at the row's end with its label.
  public string rank,flag,value,valueLabel;
  // (03/11) the value's icon ("shape:star" too), places gained/lost since the board was last opened, "invite" look.
  public string valueIcon,look;public int trend;
 }
 // The Amigos rivalry card (desktop/view-kit.ts RivalView): me VS the friend just above me (or below when I lead).
 [Serializable] public class DesktopRival {
  public string meIcon,meName,meValue,otherIcon,otherName,otherValue,text,icon;public bool lead;public DesktopButton button;
 }
 [Serializable] public class DesktopBoard {
  public string tint,backdrop,tip,style,empty,focus;public int columns;public double now;
  public DesktopStat[] stats;public DesktopMeter meter;public DesktopTile[] tiles;public DesktopButton[] footer;
  // Rankings v1 (style "rank"): the top three on a podium, my row pinned under the rows (id "" = none), a strip of chips
  // over the rows (the league's prizes) and a tile to scroll to ("<id>#<count>").
  public DesktopTile[] podium;public DesktopTile pinned;public DesktopStat[] strip;public string scroll;
  public DesktopRival rival;
 }
 // The hand-made production game (layout "kitchen"): mirrors KitchenView / KitchenStep / KitchenItem of desktop/view-kit.ts.
 [Serializable] public class DesktopKitchenItem {public string icon,label;}
 [Serializable] public class DesktopKitchenStep {
  public string kind,title,hint,art,back,unit,gauge,tool,done;public string[] states;public float[] at,lines,spots,zone,scale;
  public float size,seconds,dir,slow;public int count;public DesktopKitchenItem[] items;
  // Puzzle steps (kind "tray"): board [columns, rows], the pieces that may be dealt, most 1×1 pieces.
  public float[] grid;public string[] pieces;public int singles;
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
  // "Evoluções dos móveis" (desktop/pages/shelf-view.ts): the next capacity step may bring the next model.
  public int capacityDiamonds,tier,nextTier;public string tierName,nextTierName,nextTemplate,blockedNote;public bool evolve,grows;public float nextWidth,nextDepth;
  // Evolutions with rewards: what the next one gives and how long it takes; the crew at work and its diamond skip.
  public string[] rewards;public string evolveTime,evolutionId,evolvingLine;public bool evolving;public double evolvingEndsAt,evolvingTotal;public int skipCost;
  public DesktopShelfSlot[] slots;public DesktopShelfPick[] picks;
 }
 [Serializable] public class DesktopView {
  public string kind;public int revision,level,xp,xpGoal,claimableMissions;
  public string progressLabel,progressRoute,coins,diamonds,daily,eventName,eventTimer,eventEffect,eventIcon;
  public bool isOpen,dailyClaimable,hasEvent,eventNegative,hasOffline,hasPage,canBack;public float dailyProgress;
  public string dayPhase,dayTitle,dayDetail,goalText,goalIcon;public bool goalDone;public float dayProgress;
  public DesktopBoost[] boosts;
  public DesktopButton[] quick;
  // The corner "Bônus" button that opens the quick buttons as a menu (CheckoutDesktopHUD.Quick.cs).
  public DesktopButton quickMain;
  public DesktopButton[] tools;public DesktopCard offline;public DesktopPage page;public DesktopLevelUp levelUp;public DesktopCelebration celebration;
  public DesktopCoach coach;public DesktopGoal goal;
  // null (an empty object in JsonUtility) = at home; active = the player is visiting a friend.
  public DesktopVisit visit;
  // Rankings v1: the end-of-week card waiting to be seen (desktop/pages/ranking.ts leagueCardView); key "" = none.
  public DesktopLeagueCard leagueCard;
 }
 [Serializable] public class DesktopLeagueCard {
  public string key,headline,title,subtitle,division,movedTo,moved,movedText,badgeFrom,badgeTo,avatar,button,tint;
  public int place,diamonds,coins;public string[] podiumNames,podiumAvatars,podiumPoints;
  public string stamp,meName,meTag;public DesktopStat[] stats;
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
 [Serializable] public class DesktopCelebrationStat {public string icon,label,suffix;public float from,to;}
 [Serializable] public class DesktopCelebrationProduct {public int productId;public string name,icon;}
 [Serializable] public class DesktopCelebrationReveal {public string kind,targetId,template;public int tier,maxTier;public string[] chips,chipIcons;}
 [Serializable] public class DesktopCelebration {public string key,id,kind,headline,title,subtitle,icon,tint,button,route,lotId;public DesktopCelebrationChip[] chips;
  // Evolutions (desktop/celebration.ts tierView): numbers counting up, the products opened (NOVO), the reveal first.
  public DesktopCelebrationStat[] stats;public DesktopCelebrationProduct[] products;public DesktopCelebrationReveal reveal;}
 [Serializable] public class DesktopLevelUp {public string key,headline,subtitle,empty,next;public int from,to,total,xp,xpGoal;public DesktopLevelUpGroup[] groups;}
 // A booster running now (desktop/view.ts BoostView): seconds left, full length and the colour of its aura.
 [Serializable] public class DesktopBoost {public string id,name,icon,effect,tint;public int seconds,total;}
 [Serializable] public class DesktopResult {public string kind,id,action,reason;public bool ok;}
}
