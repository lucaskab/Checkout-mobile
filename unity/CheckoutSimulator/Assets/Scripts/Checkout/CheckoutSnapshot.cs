using System;
namespace Checkout {
 [Serializable] public class Snapshot { public MarketLayout layout; public string kind,session;public int protocol,revision,level,served,experience,experienceToNextLevel,claimableMissions;public double sentAt,coins,diamonds,dailyRevenue,dailyGoal;public bool isOpen,dailyClaimable;public float satisfaction;public Shelf[] shelves;public Sector[] sectors;public Employee[] employees;public Order[] orders;public Job[] jobs;public Customer[] customers;public string[] expansions,ownedItems;public Expansion[] expansionStates;public MarketEvent @event;public DayState day;public CheckoutEntry[] checkouts;public IncidentEntry[] incidents;public DockEntry[] dock;public RestockSlot[] restockSlots;public CheckoutResult[] checkoutResults; }
 [Serializable] public class Shelf { public string id,name,productName,category;public int productId,stock,reserve,capacity,requiredLevel;public double price,expiresAt;public bool unlocked; }
 [Serializable] public class Sector {public string id,name;public bool unlocked;public int requiredLevel,jobs;}
 [Serializable] public class Expansion {public string id,name;public int requiredLevel;public bool unlocked;}
 [Serializable] public class Employee {public string id,name,role;public bool isWorking;public int level;public float efficiency;}
 [Serializable] public class Order {public string id,status,productCategory;public int productId,quantity;public double createdAt,deliveryDurationMs;}
 [Serializable] public class Job {public string id,sectorId;public double startedAt,endsAt;}
 [Serializable] public class Customer {public string id,name,status,mood;public double spent;public Purchase[] purchases;}
 [Serializable] public class Purchase {public string shelfId;public int productId,quantity;}
 // Market day (turn) from src/services/simulator-snapshot.ts; requests carry the waiting customer's id.
 [Serializable] public class DayState {public string phase,contractTitle,contractLabel,grade;public int dayNumber,loyalty;public double startedAt,endsAt;public float contractProgress;public bool contractCompleted;public DayRequest[] requests;}
 [Serializable] public class DayRequest {public string id,customerId,customerName,kind,message,productName,status;public int productId;public double createdAt,expiresAt;}
 // Register line (src/services/checkout-counter.ts): baskets waiting to be rung up and the latest outcomes.
 [Serializable] public class CheckoutEntry {public string id,customerId,customerName,mood,method;public double total,cashGiven,readyAt,expiresAt;public CheckoutLine[] items;}
 [Serializable] public class CheckoutLine {public int productId,quantity;public string name;public double unitPrice;}
 [Serializable] public class CheckoutResult {public string id,customerId,status,mistake;public double charged,tip;}
 // Trucks at the dock and the shelf slots the stockroom can refill (src/services/receiving.ts).
 [Serializable] public class DockEntry {public string id,productName,category,zone;public int productId,quantity,unloaded,boxUnits,room;public double arrivedAt;}
 [Serializable] public class RestockSlot {public string slotId,shelfId,shelfName,productName,zone;public int productId,stock,capacity,reserve;}
 // Store mishaps (src/services/store-incidents.ts).
 [Serializable] public class IncidentEntry {public string id,kind,shelfId,shelfName,productName;public int productId;public double createdAt,fixCost,tagPrice,price;}
 [Serializable] public class MarketEvent {public string id,name,description,effectLabel,kind;public double endsAt;public float arrivalMultiplier,productionMultiplier;}
}
