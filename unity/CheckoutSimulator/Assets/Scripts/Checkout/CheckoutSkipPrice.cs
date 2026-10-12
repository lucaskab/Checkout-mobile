namespace Checkout {
 /// <summary>
 /// Diamonds to finish a timer right now ("Acelerar"): the game's one speed-up price, from the time still left, so it
 /// drops as the wait runs down (Lucas 12/10). Copy of src/data/diamond-skip.ts for the boards that count down in
 /// the world (works signs, lot balloons) between two snapshots. src/data/diamond-skip.test.mjs checks that the
 /// points below are the same as the TypeScript ones.
 /// </summary>
 public static class CheckoutSkipPrice {
  const double Minute=60000,Hour=60*Minute,Day=24*Hour;
  // [time left in ms, diamonds]: ≤ 1 min → 1 · 1 h → 10 · 1 day → 150 · 1 week → 700 (straight lines between).
  public static readonly double[,] Points={{Minute,1},{Hour,10},{Day,150},{7*Day,700}};

  public static int Cost(double remainingMs){
   if(double.IsNaN(remainingMs)||double.IsInfinity(remainingMs)||remainingMs<=0)return 0;
   int n=Points.GetLength(0);
   if(remainingMs<=Points[0,0])return (int)Points[0,1];
   for(int i=1;i<n;i++){
    if(remainingMs<=Points[i,0])return Ceil(Points[i-1,1]+(Points[i,1]-Points[i-1,1])*(remainingMs-Points[i-1,0])/(Points[i,0]-Points[i-1,0]));
   }
   return Ceil(Points[n-1,1]+(Points[n-1,1]-Points[n-2,1])*(remainingMs-Points[n-1,0])/(Points[n-1,0]-Points[n-2,0]));
  }
  // Same rounding as Math.ceil in the game logic.
  static int Ceil(double value)=>(int)System.Math.Ceiling(value);
 }
}
