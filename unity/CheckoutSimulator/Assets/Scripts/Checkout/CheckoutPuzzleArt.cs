using UnityEngine;
namespace Checkout {
 // Measurements of the sector puzzle art (scripts/blender/puzzle_sectors.py, manifest.json of 24/10): pixel rects are
 // (left, bottom, right, top) from the bottom-left corner of each sprite. Re-run the generator after re-rendering.
 static class CheckoutPuzzleArt {
  public struct Meat {public string id;public Vector2 size;public float x0,x1,y0;public float[] profile;}
  public static readonly Meat[] Meats={
   new Meat{id="contrafile",size=new Vector2(1400,300),x0=98,x1=1297,y0=33,profile=new[]{0.3703f,0.4257f,0.4530f,0.4693f,0.4823f,0.4937f,0.5033f,0.5127f,0.5207f,0.5270f,0.5327f,0.5383f,0.5427f,0.5477f,0.5503f,0.5533f,0.5550f,0.5567f,0.5567f,0.5577f,0.5600f,0.5600f,0.5600f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5633f,0.5617f,0.5600f,0.5600f,0.5600f,0.5600f,0.5600f,0.5600f,0.5573f,0.5567f,0.5557f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5533f,0.5527f,0.5517f,0.5500f,0.5500f,0.5500f,0.5500f,0.5493f,0.5500f,0.5500f,0.5483f,0.5467f,0.5467f,0.5457f,0.5433f,0.5433f,0.5433f,0.5433f,0.5433f,0.5433f,0.5433f,0.5433f,0.5420f,0.5400f,0.5400f,0.5397f,0.5367f,0.5367f,0.5353f,0.5333f,0.5333f,0.5320f,0.5300f,0.5300f,0.5283f,0.5267f,0.5260f,0.5233f,0.5233f,0.5213f,0.5200f,0.5200f,0.5170f,0.5170f,0.5173f,0.5190f,0.5183f,0.5173f,0.5140f,0.5147f,0.5153f,0.5120f,0.5100f,0.5077f,0.5027f,0.4960f,0.4870f,0.4757f,0.4613f,0.4363f,0.3980f}},
   new Meat{id="picanha",size=new Vector2(1400,300),x0=142,x1=1263,y0=33,profile=new[]{0.1785f,0.2219f,0.2397f,0.2552f,0.2693f,0.2830f,0.2963f,0.3085f,0.3213f,0.3333f,0.3448f,0.3563f,0.3681f,0.3793f,0.3913f,0.4041f,0.4152f,0.4273f,0.4389f,0.4493f,0.4604f,0.4700f,0.4807f,0.4900f,0.5000f,0.5093f,0.5200f,0.5289f,0.5387f,0.5481f,0.5567f,0.5663f,0.5748f,0.5830f,0.5910f,0.6000f,0.6078f,0.6160f,0.6237f,0.6303f,0.6374f,0.6437f,0.6503f,0.6567f,0.6619f,0.6683f,0.6737f,0.6785f,0.6823f,0.6859f,0.6881f,0.6900f,0.6904f,0.6933f,0.6967f,0.6996f,0.7022f,0.7033f,0.7056f,0.7067f,0.7067f,0.7067f,0.7067f,0.7033f,0.7019f,0.6990f,0.6956f,0.6919f,0.6880f,0.6837f,0.6793f,0.6747f,0.6696f,0.6644f,0.6583f,0.6519f,0.6459f,0.6397f,0.6326f,0.6257f,0.6181f,0.6119f,0.6043f,0.5970f,0.5896f,0.5810f,0.5726f,0.5633f,0.5540f,0.5433f,0.5330f,0.5217f,0.5100f,0.4993f,0.4883f,0.4767f,0.4667f,0.4560f,0.4456f,0.4350f,0.4244f,0.4133f,0.4020f,0.3907f,0.3793f,0.3677f,0.3552f,0.3444f,0.3327f,0.3211f,0.3100f,0.2983f,0.2870f,0.2752f,0.2610f,0.2467f,0.2348f,0.2200f,0.2015f,0.1533f}},
   new Meat{id="fraldinha",size=new Vector2(1400,300),x0=77,x1=1320,y0=34,profile=new[]{0.2037f,0.2460f,0.2588f,0.2683f,0.2787f,0.2858f,0.2917f,0.2957f,0.2991f,0.3010f,0.3033f,0.3033f,0.3063f,0.3067f,0.3067f,0.3040f,0.3033f,0.3033f,0.3027f,0.3000f,0.2990f,0.2967f,0.2940f,0.2920f,0.2891f,0.2863f,0.2833f,0.2797f,0.2760f,0.2721f,0.2687f,0.2653f,0.2621f,0.2597f,0.2567f,0.2542f,0.2517f,0.2493f,0.2467f,0.2433f,0.2412f,0.2387f,0.2367f,0.2333f,0.2310f,0.2293f,0.2267f,0.2253f,0.2233f,0.2227f,0.2200f,0.2200f,0.2170f,0.2167f,0.2155f,0.2133f,0.2133f,0.2112f,0.2100f,0.2100f,0.2100f,0.2077f,0.2067f,0.2067f,0.2067f,0.2067f,0.2063f,0.2033f,0.2033f,0.2033f,0.2033f,0.2033f,0.2017f,0.2000f,0.2000f,0.2000f,0.1979f,0.1967f,0.1967f,0.1952f,0.1933f,0.1933f,0.1903f,0.1900f,0.1876f,0.1867f,0.1833f,0.1821f,0.1800f,0.1779f,0.1767f,0.1733f,0.1715f,0.1693f,0.1667f,0.1633f,0.1607f,0.1580f,0.1552f,0.1527f,0.1500f,0.1470f,0.1457f,0.1433f,0.1410f,0.1400f,0.1370f,0.1353f,0.1333f,0.1303f,0.1277f,0.1248f,0.1217f,0.1187f,0.1155f,0.1123f,0.1090f,0.1021f,0.0940f,0.0721f}},
  };
  // Glass vessels: the sprite size, the liquid band (bottom = empty, top = full: for the cellar vessels the shoulder, where the glass starts to narrow) and the inside (mask) bounds.
  public struct Vessel {public string id;public Vector2 size;public Rect inner,inside;}
  public static readonly Vessel Jug=new Vessel{id="pz_jug_glass",size=new Vector2(240,560),inner=new Rect(37,93,107,312),inside=new Rect(23,83,135,353)};
  public static readonly Vessel[] Vessels={
   new Vessel{id="pz_vessel_big",size=new Vector2(360,560),inner=new Rect(56,45,248,286),inside=new Rect(48,45,264,417)},
   new Vessel{id="pz_vessel_mid",size=new Vector2(280,440),inner=new Rect(53,36,174,220),inside=new Rect(46,36,188,369)},
   new Vessel{id="pz_vessel_small",size=new Vector2(220,320),inner=new Rect(33,68,112,164),inside=new Rect(23,68,132,189)},
  };
  // The gelato freezer of pz_bench_sorvetes (1600×900): six tub slots (row-major from the top-left) and the cone stand.
  public static readonly Vector2 BenchSize=new Vector2(1600,900);
  public static readonly Rect[] TubSlots={new Rect(70,480,280,224),new Rect(376,480,280,224),new Rect(682,480,280,224),new Rect(70,230,280,224),new Rect(376,230,280,224),new Rect(682,230,280,224)};
  public static readonly Vector2 ConeStand=new Vector2(1290,340);
  // pz_scale (560×340): the weighing plate and the display window.
  public static readonly Vector2 ScaleSize=new Vector2(560,340);
  public static readonly Rect ScalePlate=new Rect(48,112,470,160),ScaleDisplay=new Rect(95,48,305,37);
 }
}
