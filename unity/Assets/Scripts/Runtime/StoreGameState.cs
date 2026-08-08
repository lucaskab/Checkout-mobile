using System;

[Serializable]
public sealed class StoreShelfState
{
    public string id;
    public string displayName;
    public string productId;
    public string productName;
    public int stock;
    public int capacity;
    public int sellingPrice;
    public bool unlocked;
    public float x;
    public float z;
}

[Serializable]
public sealed class StoreInventoryEntry
{
    public string productId;
    public string productName;
    public int quantity;
}

[Serializable]
public sealed class StoreDeliveryState
{
    public string productId;
    public string productName;
    public int quantity;
    public float remainingSeconds;
}

[Serializable]
public sealed class StoreProductionState
{
    public string recipeId;
    public string recipeName;
    public int outputQuantity;
    public float remainingSeconds;
    public bool running;
}

[Serializable]
public sealed class StoreSnapshot
{
    public int coins;
    public int premiumCurrency;
    public int level;
    public int experience;
    public int experienceToNextLevel;
    public int customersServed;
    public int unitsSold;
    public int todayRevenue;
    public int customerSatisfaction;
    public bool marketOpen;
    public bool employeeHired;
    public StoreShelfState[] shelves;
    public StoreInventoryEntry[] inventory;
    public StoreDeliveryState[] deliveries;
    public StoreProductionState production;
}

[Serializable]
public sealed class StoreActionMessage
{
    public string type;
    public string targetId;
    public int amount;
    public float x;
    public float z;
}

[Serializable]
public sealed class StoreEventMessage
{
    public string type;
    public string targetId;
    public int amount;
    public int coins;
    public int level;
    public string message;
}
