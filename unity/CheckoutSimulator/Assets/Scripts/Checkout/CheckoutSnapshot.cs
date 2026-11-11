using System;
namespace Checkout {
 [Serializable] public class Snapshot { public MarketLayout layout; public string kind,session;public int protocol,revision,level,served,experience,experienceToNextLevel,claimableMissions;public double sentAt,coins,diamonds,dailyRevenue,dailyGoal;public bool isOpen,dailyClaimable;public float satisfaction;public Shelf[] shelves;public Sector[] sectors;public Employee[] employees;public Order[] orders;public Job[] jobs;public Customer[] customers;public string[] expansions,ownedItems,boosts;public float[] boostSeconds;public BuildEntry[] builds;public Expansion[] expansionStates;public Construction construction;public InteriorState interior;public DecorEntry[] decorCatalog;public DecorPlay[] decorPlays;public MarketEvent @event;public DayState day;public CheckoutEntry[] checkouts;public IncidentEntry[] incidents;public DockEntry[] dock;public StockroomEntry[] stockroom;public RestockSlot[] restockSlots;public CheckoutResult[] checkoutResults;public StaffTask[] staffTasks;public EraState era; public SupplierProduct[] supplierCatalog; public SupplierInfo supplierInfo; public DeliveryState delivery; public PaintState paint; public StyleState style; public ChainState chain; public FixtureTiers fixtureTiers; public Evolution[] evolutions; public RevealEntry[] reveals; public SecurityState security; public PetState pet; }
 [Serializable] public class Shelf { public string id,name,productName,category,tierTemplate;public int productId,stock,reserve,capacity,requiredLevel,tier;public double price,expiresAt;public bool unlocked,building,premium; }
 // "Evoluções dos móveis" (src/services/simulator-snapshot.ts fixtureTiers): the checkouts' step and the cold room.
 [Serializable] public class FixtureTiers { public int checkout,coldRoom;public string checkoutTemplate,coldRoomTemplate,coldRoomBuilding;public bool scanner;public double coldRoomEndsAt; }
 // A shelf, sector or fixture paid for and still being built inside the market (src/services/interior-construction.ts).
 // The evolution crew's queue (src/data/fixture-evolution.ts): builder and navy ring on the piece (CheckoutEvolutionSite).
[Serializable] public class Evolution {public string id,kind,targetId;public int toTier,skipCost;public double startedAt,endsAt,durationMs;public bool queued;public float progress;}
// An evolution that ended and waits for its reveal: the piece stays under the cloth (CheckoutEvolutionReveal).
[Serializable] public class RevealEntry {public string id,kind,targetId;public int tier;}
[Serializable] public class BuildEntry {public string id,kind,targetId,name;public double startedAt,endsAt,durationMs;public int skipCost;public bool pending,queued;}
 // tier / tierTemplate / board: "Evoluções dos móveis", the sector's model and its price boards (CheckoutSectorScreens).
 [Serializable] public class Sector {public string id,name,tierTemplate;public bool unlocked,building;public int requiredLevel,jobs,tier;public BoardRow[] board; [Serializable] public class BoardRow {public int productId;public double price;} }
 [Serializable] public class Expansion {public string id,name;public int requiredLevel;public bool unlocked,building;}
 // Paid expansion still being built (it takes real time; diamonds finish it early). Empty id = no works.
 [Serializable] public class Construction {public string expansionId;public double startedAt,endsAt;public int skipCost;public MarketLayout targetLayout;}
 [Serializable] public class Employee {public string id,name,role;public bool isWorking;public int level;public float efficiency;}
 [Serializable] public class Order {public string id,status,productCategory,fleetTruckId;public int productId,quantity,boxes;public double createdAt,deliveryDurationMs;public OrderLine[] lines;}
 [Serializable] public class OrderLine {public int productId,boxes;public string productName;}
 [Serializable] public class Job {public string id,sectorId;public double startedAt,endsAt;}
 // origin: the event that brought the customer ("quinto-dia-util"…): their walk starts in the event's scene (the ATM
 // queue, the bus stop…) before they shop (CheckoutEventVisuals.Market.cs). Empty = a normal walk-in or car customer.
 // sex: "f" / "m" (src/data/customer-names.ts), the name matches it; CheckoutBridge walks the customer in with a body of that sex. "" = any body.
 [Serializable] public class Customer {public string id,name,status,mood,origin,carrier,sex;public double spent;public Purchase[] purchases;}
 [Serializable] public class Purchase {public string shelfId;public int productId,quantity;}
 // Market day (turn) from src/services/simulator-snapshot.ts.
 [Serializable] public class DayState {public string phase,contractTitle,contractLabel,grade,shift;public int dayNumber;public double startedAt,endsAt;public float contractProgress;public bool contractCompleted;}
 // Register line (src/services/checkout-counter.ts): baskets waiting to be rung up and the latest outcomes.
 [Serializable] public class CheckoutEntry {public string id,customerId,customerName,mood,method;public double total,cashGiven,readyAt,expiresAt;public CheckoutLine[] items;}
 [Serializable] public class CheckoutLine {public int productId,quantity;public string name;public double unitPrice;}
 [Serializable] public class CheckoutResult {public string id,customerId,status,mistake;public double charged,tip;}
 // Trucks at the dock and the shelf slots the stockroom can refill (src/services/receiving.ts).
 [Serializable] public class DockEntry {public string id,productName,category,zone,orderId;public int productId,quantity,unloaded,boxUnits,boxes,room;public double arrivedAt;}
[Serializable] public class StockroomEntry {public string productName,category,zone;public int productId,units,caseSize,boxes,capacityBoxes;}
 [Serializable] public class RestockSlot {public string slotId,shelfId,shelfName,productName,zone;public int productId,stock,capacity,reserve,caseSize;public float restockBonus;}
 // Store mishaps (src/services/store-incidents.ts).
 [Serializable] public class IncidentEntry {public string id,kind,shelfId,shelfName,productName;public int productId;public double createdAt,fixCost,tagPrice,price;}
 // What the hired stock clerks and cleaners are doing (src/services/staff-work.ts); CheckoutStaff plays it.
 [Serializable] public class StaffTask {public string id,employeeId,role,kind,shelfId,slotId,productName,box,incidentId,incidentKind;public int productId,units;public double startedAt,endsAt;}
 [Serializable] public class MarketEvent {public string id,name,description,effectLabel,kind;public double endsAt;public float arrivalMultiplier,productionMultiplier;
  // What the player does during the event (src/services/event-interactions.ts): "inspection" (the inspector's three
  // stops), "window-sales" (drinks sold through the jammed cars' windows) or "".
  public string interaction;public InspectionStop[] stops;public bool seal;public WindowRequest[] windowRequests;public int windowServed,windowGoal;}
 // A stop of the inspector: waiting | open | fixed | failed; open ones point at a real store mishap.
 [Serializable] public class InspectionStop {public string id,status,shelfId,incidentId,kind;public double at,deadline;}
 // A driver of the jam asking for a drink: lane 0 = next to the sidewalk; waiting | served | missed.
 [Serializable] public class WindowRequest {public string id,productName,status;public int lane,slot,productId;public double expiresAt;public bool inStock;}
 // Stage of the market (src/services/market-era.ts) and the lots of the block (src/data/market-lots.ts).
 [Serializable] public class EraState {public string id,name,nextName;public int index;public bool building;public LotGrid grid;public LotRect[] lotRects;public string[] lots,nextLots,plazaLots;public EraConstruction construction;}
 [Serializable] public class LotRect {public string id,label,ruin,ruinName,status;public float x0,z0,x1,z1;public double price,clearCost,clearDurationMs,clearStartedAt,clearEndsAt;public int skipCost;public bool occupied;public string neededBy;}
 [Serializable] public class LotGrid {public float x0,z0,width,depth;public int columns,rows;}
 [Serializable] public class EraConstruction {public string eraId,name;public int index,skipCost;public double startedAt,endsAt;}
 [Serializable] public class SupplierProduct {public string name,category,categoryLabel;public int productId,caseSize,stockUnits,shelfUnits,capacityBoxes,freeBoxes,incomingBoxes,unlockLevel;public float boxPrice,unitCost,salePrice,deliverySeconds;public bool low,locked;}
 // The saved supplier cart (Lucas 11/11): "Pedir caixas" anywhere adds to it; the shop window follows cartRevision.
 [Serializable] public class SupplierInfo {public int slots,active,maxBoxes,freightCoupons,cartRevision;public float extraProductShare,extraProductCap;public CartEntry[] cart;}
 [Serializable] public class CartEntry {public int productId,boxes;}
 // Delivery app (src/services/delivery.ts). Times are epoch ms; 0 = not set.
 // "Cores do mercado" (src/data/market-paint.ts): the player's two colours, the curated palettes, the last ones applied
 // and the prices at the current expansion (CheckoutMarketPaint paints the market, CheckoutMarketPaintPanel picks).
 // Rede de supermercados (src/services/chain.ts createChainSnapshot): the chain's brand and where each fleet truck is.
 [Serializable] public class ChainState {public bool unlocked,named;public string brand,emblem;public FleetTruckState[] trucks;public BranchState[] branches;}
 [Serializable] public class FleetTruckState {public string id,kind,job,phase;public double departAt,arriveAt,returnAt;}
 [Serializable] public class BranchState {public string id;public int level;public bool building;}
 [Serializable] public class PaintState {public string primary,accent,palette;public int coinPrice,diamondPrice;public PaintPalette[] palettes,recent,owned;}
 [Serializable] public class PaintPalette {public string id,name,primary,accent;}
 // "Estilo do mercado" (src/data/market-style.ts → CheckoutMarketStyle / CheckoutMarketStylePanel).
 [Serializable] public class StyleState {public string floor,floorColor,wall,wallColor,uniform,uniformMain,uniformDetail;public StyleSign sign;public string[] owned,swatches;public bool insideUnlocked,signUnlocked;public int coinBase;public StyleItem[] items;public StylePalette[] palettes;}
 [Serializable] public class StyleSign {public string font,look,effect,main,second,palette;public int speed;}
 [Serializable] public class StyleItem {public string id,kind,name,color,main,detail,note;public bool free,tintable;public float coinFactor;public int diamondPrice,coinPrice;}
 [Serializable] public class StylePalette {public string id,name;public string[] colors;}
 // "Ladrão e segurança" (src/services/store-security.ts createSecuritySnapshot → CheckoutSecurity). Times are epoch ms;
 // no thief = an empty id (JsonUtility never leaves the object null). phase: entering | fleeing | caught | escaped.
 [Serializable] public class SecurityState {public ThiefState thief;public bool guardHired;public int caughtToday,escapedToday;public SecurityOutcome lastOutcome;}
 [Serializable] public class ThiefState {public string id,phase,productName,slotId,shelfId,caughtBy;public int productId,quantity,coins;public double value,spawnedAt,grabAt,fleeDeadline,guardCatchAt,removeAt,grabInMs,fleeLeftMs,guardInMs;public bool dogBarked;}
 [Serializable] public class SecurityOutcome {public string kind,productName;public int coins,quantity;public double ageMs;}
 // "Mascote caramelo" (src/services/store-pet.ts createPetSnapshot → CheckoutPets): adopted or waiting at the door, mood and cosmetics.
 [Serializable] public class PetState {public bool adopted,offer,hasBed,hasBowls;public double happyLeftMs,cooldownLeftMs;public string collar,bandana,bedStyle;public string[] owned;}
 [Serializable] public class DeliveryState {public bool unlocked;public string unlockEraName;public int slots,active,streak,bestStreak,delivered;public float rating;public DeliveryOrder[] orders;}
 [Serializable] public class DeliveryOrder {public string id,status,customerName,neighborhood,note;public int avatar;public DeliveryItem[] items;public float distanceKm,fee,itemsValue,fillRatio,quality,stars,tip,bonus,paid;public DeliveryCourier courier;public double createdAt,expiresAt,acceptedAt,packBy,packedAt,arriveAt,doorSince,deliverAt;}
 [Serializable] public class DeliveryItem {public int productId,quantity,packed;public string productName,category;}
 [Serializable] public class DeliveryCourier {public string id,name,color;public DeliveryPhrases phrases;}
 [Serializable] public class DeliveryPhrases {public string[] arrive,leave,delivered;}
}
