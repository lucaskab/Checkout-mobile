using System;
using UnityEngine;

namespace MarketDay
{
    [Serializable] public class DepartmentState
    {
        public string id;
        public int stock = 12;
        public int reserve = 24;
        public int level = 1;
        public float deliveryRemaining;
        public int incoming;
        public int Capacity => 20 + (level - 1) * 10;
        public int Price => 8 + level * 2;
        public int UpgradeCost => 120 * level;
    }

    [Serializable] public class MarketEconomy
    {
        public int version = 1;
        public int coins = 850;
        public int xp;
        public int served;
        public int workers = 1;
        public int delivered;
        public int restocked;
        public bool opened;
        public bool[] claimed = new bool[3];
        public DepartmentState[] departments;
        public int Level => 1 + xp / 50;
        public int WarehouseUsed { get { int n=0;foreach(var d in departments)n+=d.reserve+d.incoming;return n; } }
        public int WarehouseCapacity => 250;
        public static readonly string[] Ids = { "bakery", "groceries", "fishery", "butcher", "produce" };

        public static MarketEconomy Fresh()
        {
            var m=new MarketEconomy();m.departments=new DepartmentState[Ids.Length];
            for(int i=0;i<Ids.Length;i++)m.departments[i]=new DepartmentState{id=Ids[i]};
            return m;
        }
        public bool Order(int i,out string message)
        {
            var d=departments[i];const int quantity=20,cost=60;
            if(d.incoming>0){message="This delivery is already on its way.";return false;}
            if(coins<cost){message="You need 60 coins for this delivery.";return false;}
            if(WarehouseUsed+quantity>WarehouseCapacity){message="The warehouse is full. Restock your displays first.";return false;}
            coins-=cost;d.incoming=quantity;d.deliveryRemaining=12;
            message="Supplier dispatched! 20 units arrive in 12 seconds.";return true;
        }
        public bool Upgrade(int i,out string message)
        {
            var d=departments[i];
            if(d.level>=5){message="This department is fully upgraded.";return false;}
            if(coins<d.UpgradeCost){message="More coins are needed for this upgrade.";return false;}
            coins-=d.UpgradeCost;d.level++;xp+=10;message="Department upgraded! More shelf space and better prices.";return true;
        }
        public bool Hire(out string message)
        {
            if(workers>=3){message="Your three-person stock team is complete.";return false;}
            int cost=250*workers;
            if(coins<cost){message="You need "+cost+" coins to hire a worker.";return false;}
            coins-=cost;workers++;message="A new stock worker joined your team.";return true;
        }
        public int Refill(int i)
        {
            var d=departments[i];int quantity=Math.Min(d.Capacity-d.stock,Math.Min(d.reserve,10));
            if(quantity<=0)return 0;d.reserve-=quantity;d.stock+=quantity;restocked+=quantity;xp+=2;return quantity;
        }
        public bool TakeFromShelf(int i)
        {
            if(departments[i].stock<=0)return false;
            departments[i].stock--;return true;
        }
        public void Checkout(int receipt)
        {
            if(receipt<=0)return;coins+=receipt;served++;xp+=4;
        }
        public int GoalProgress(int i)=>i==0?served:i==1?restocked:delivered;
        public int GoalTarget(int i)=>i==0?5:i==1?10:20;
        public bool Claim(int i)
        {
            if(claimed[i]||GoalProgress(i)<GoalTarget(i))return false;
            claimed[i]=true;coins+=100;xp+=15;return true;
        }
        public bool Tick(float dt)
        {
            bool arrived=false;
            foreach(var d in departments)
            {
                if(d.incoming<=0)continue;
                d.deliveryRemaining=Mathf.Max(0,d.deliveryRemaining-dt);
                if(d.deliveryRemaining<=0){d.reserve+=d.incoming;delivered+=d.incoming;d.incoming=0;arrived=true;}
            }
            return arrived;
        }
        public bool Valid()
        {
            if(version!=1||departments==null||departments.Length!=5||coins<0||workers<1||workers>3||claimed==null||claimed.Length!=3)return false;
            for(int i=0;i<5;i++)
            {
                var d=departments[i];
                if(d==null||d.id!=Ids[i]||d.level<1||d.level>5||d.stock<0||d.stock>d.Capacity||d.reserve<0||d.incoming<0||d.deliveryRemaining<0)return false;
            }
            return WarehouseUsed<=WarehouseCapacity;
        }
    }
}
