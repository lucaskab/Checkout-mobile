using System;
namespace Checkout {
 [Serializable] public class Snapshot { public MarketLayout layout; public string kind,session;public int protocol,revision,level,served,experience,experienceToNextLevel,claimableMissions;public double sentAt,coins,diamonds,dailyRevenue,dailyGoal;public bool isOpen,dailyClaimable;public float satisfaction;public Shelf[] shelves;public Sector[] sectors;public Employee[] employees;public Order[] orders;public Job[] jobs;public Customer[] customers;public string[] expansions,ownedItems;public Expansion[] expansionStates;public MarketEvent @event; }
 [Serializable] public class Shelf { public string id,name,productName,category;public int productId,stock,reserve,capacity,requiredLevel;public double price,expiresAt;public bool unlocked; }
 [Serializable] public class Sector {public string id,name;public bool unlocked;public int requiredLevel,jobs;}
 [Serializable] public class Expansion {public string id,name;public int requiredLevel;public bool unlocked;}
 [Serializable] public class Employee {public string id,name,role;public bool isWorking;public int level;public float efficiency;}
 [Serializable] public class Order {public string id,status,productCategory;public int productId,quantity;public double createdAt,deliveryDurationMs;}
 [Serializable] public class Job {public string id,sectorId;public double startedAt,endsAt;}
 [Serializable] public class Customer {public string id,name,status,mood;public double spent;public Purchase[] purchases;}
 [Serializable] public class Purchase {public string shelfId;public int productId,quantity;}
 [Serializable] public class MarketEvent {public string id,name,description,effectLabel,kind;public double endsAt;public float arrivalMultiplier,productionMultiplier;}
}
