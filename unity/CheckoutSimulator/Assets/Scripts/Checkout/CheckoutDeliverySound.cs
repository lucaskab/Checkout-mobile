using System;
using UnityEngine;

namespace Checkout {
 // Procedural sounds of the Delivery app and packing game: soft, low-mid, never shrill. Every clip is made once
 // and cached. Properties return the clip for a sound; Play() plays it on one shared AudioSource (±3% pitch).
 public static class CheckoutDeliverySound {
  const int Rate=22050;
  static AudioSource source;
  static bool built;
  static AudioClip chime,accept,decline,beep,fold,sticker,printer,bikeArrive,horn,bikeLeave,coin,wrong;
  static AudioClip[] rustleLight,rustleHeavy,rustleGlass,stars;

  public static AudioClip Chime{get{Build();return chime;}}
  public static AudioClip Accept{get{Build();return accept;}}
  public static AudioClip Decline{get{Build();return decline;}}
  public static AudioClip Beep{get{Build();return beep;}}
  public static AudioClip Fold{get{Build();return fold;}}
  public static AudioClip Sticker{get{Build();return sticker;}}
  public static AudioClip Printer{get{Build();return printer;}}
  public static AudioClip BikeArrive{get{Build();return bikeArrive;}}
  public static AudioClip Horn{get{Build();return horn;}}
  public static AudioClip BikeLeave{get{Build();return bikeLeave;}}
  public static AudioClip Coin{get{Build();return coin;}}
  public static AudioClip Wrong{get{Build();return wrong;}}
  // weight: 0 light paper, 1 heavy thud with paper, 2 glass clink.
  public static AudioClip Rustle(int weight){
   Build();
   var list=weight==1?rustleHeavy:weight==2?rustleGlass:rustleLight;
   return list[UnityEngine.Random.Range(0,list.Length)];
  }
  // Rising ding for each star (index 0 = first star).
  public static AudioClip Star(int index){Build();return stars[Mathf.Clamp(index,0,stars.Length-1)];}

  public static void Play(AudioClip clip,float volume=.5f){
   if(!clip)return;
   try{
    if(!source){
     var go=new GameObject("CheckoutDeliverySound");go.hideFlags=HideFlags.HideAndDontSave;
     source=go.AddComponent<AudioSource>();source.playOnAwake=false;
    }
    source.pitch=UnityEngine.Random.Range(.97f,1.03f);source.PlayOneShot(clip,volume);
   }catch(Exception){}
  }

  // ------------------------------------------------------------------ synthesis
  static void Build(){
   if(built)return;built=true;
   // Chime: two marimba-like notes, E5 then B5, quick decay.
   chime=Make("delivery_chime",Mix(.42f,0.7f,
    Marimba(659,0,.5f,.5f),Marimba(988,.15f,.7f,.42f)));
   accept=Make("delivery_accept",Mix(.3f,.6f,Pluck(520,0,.12f,1f),Pluck(780,.06f,.14f,.8f)));
   decline=Make("delivery_decline",Mix(.3f,.6f,Pluck(440,0,.13f,.8f),Pluck(310,.07f,.16f,.7f)));
   beep=Make("delivery_beep",Mix(.2f,.5f,Pluck(988,0,.07f,.45f)));
   fold=Make("delivery_fold",Noise(.22f,11,.22f,2400,1600,.2f));
   sticker=Make("delivery_sticker",Mix(.4f,.6f,Thump(180,120,.09f,.8f),Noise(.05f,3,.1f,3000,800,.4f)));
   printer=Make("delivery_printer",Buzz(.5f,38,.12f));
   // A 125 cc single-cylinder motoboy bike: keys are time, firing rate (Hz), loudness, throttle.
   // Arriving: cruising past, throttle off, engine braking down to idle.
   bikeArrive=Make("delivery_bike_arrive",Mix(.55f,0,Moto(2.3f,7,0,52,.55f,.8f, .9f,58,1,.9f, 1.25f,34,.55f,.1f, 1.9f,18,.45f,.15f, 2.3f,16,.35f,.1f)));
   // Leaving: idle, first gear rev, shift, second gear, fading into the distance.
   bikeLeave=Make("delivery_bike_leave",Mix(.55f,0,Moto(2.4f,9,0,16,.45f,.2f, .15f,18,.6f,.7f, .8f,56,1,1, .9f,38,.8f,.5f, 1.75f,64,.75f,1, 2.4f,58,.2f,.8f)));
   horn=Make("delivery_horn",HornWave());
   coin=Make("delivery_coin",Mix(.4f,.6f,Marimba(1318,0,.35f,.5f),Marimba(1760,.09f,.42f,.42f)));
   wrong=Make("delivery_wrong",Mix(.35f,.5f,Thump(110,82,.3f,.9f)));
   // Soft plastic bag rustle: a short band of noise, no hiss (light items).
   rustleLight=new[]{
    Make("delivery_rustle_l0",Noise(.2f,21,.09f,3600,1400,.35f)),
    Make("delivery_rustle_l1",Noise(.18f,22,.08f,3200,1200,.3f)),
    Make("delivery_rustle_l2",Noise(.22f,23,.085f,3000,1100,.4f))};
   // Cardboard knock: a low, soft tap with a little paper behind it (heavy items).
   rustleHeavy=new[]{
    Make("delivery_rustle_h0",Mix(.34f,.6f,Thump(120,80,.13f,.5f),Noise(.14f,31,.06f,1200,450,.3f))),
    Make("delivery_rustle_h1",Mix(.34f,.6f,Thump(132,88,.12f,.45f),Noise(.12f,32,.05f,1300,500,.3f)))};
   // Fragile (eggs, bread): a muffled soft pluck instead of a glass clink.
   rustleGlass=new[]{
    Make("delivery_glass0",Mix(.22f,.5f,Pluck(523,0,.12f,.5f))),
    Make("delivery_glass1",Mix(.22f,.5f,Pluck(587,0,.11f,.5f)))};
   stars=new AudioClip[5];
   for(int i=0;i<stars.Length;i++){
    float hz=784*Mathf.Pow(2,i/6f);
    stars[i]=Make("delivery_star"+i,Mix(.3f,.6f,Pluck(hz,0,.26f,1f),Pluck(hz*1.5f,.04f,.2f,.25f)));
   }
  }

  static AudioClip Make(string name,float[] data){
   var clip=AudioClip.Create(name,data.Length,1,Rate,false);clip.SetData(data,0);return clip;
  }
  // Sums sample arrays into one buffer and scales the peak to `peak`.
  static float[] Mix(float peak,float _,params float[][] parts){
   int n=0;foreach(var p in parts)n=Mathf.Max(n,p.Length);
   var d=new float[n];
   foreach(var p in parts)for(int i=0;i<p.Length;i++)d[i]+=p[i];
   float max=0;foreach(var v in d)max=Mathf.Max(max,Mathf.Abs(v));
   if(max>0)for(int i=0;i<n;i++)d[i]*=peak/max;
   return d;
  }
  // Sine with a faint octave, fast attack, exponential decay (soft pluck). volume 0..1 scales the note.
  static float[] Pluck(float hz,float start,float len,float volume){
   return Note(hz,start,len,volume,3f,.25f);
  }
  // Marimba: fundamental plus a weak 4th partial, very fast decay.
  static float[] Marimba(float hz,float start,float len,float volume){
   return Note(hz,start,len,volume,9f,.12f);
  }
  // decay: exp(-t*decay/len), so the note is silent near its end whatever its length.
  static float[] Note(float hz,float start,float len,float volume,float decay,float partial){
   int from=Mathf.RoundToInt(start*Rate);int count=Mathf.RoundToInt((start+len+.03f)*Rate);
   var d=new float[count];
   for(int i=from;i<count;i++){
    float t=(i-from)/(float)Rate;
    float env=(1-Mathf.Exp(-t*600f))*Mathf.Exp(-t*decay/Mathf.Max(.05f,len));
    d[i]=volume*env*(Mathf.Sin(2*Mathf.PI*hz*t)+partial*Mathf.Sin(4*Mathf.PI*hz*t));
   }
   return d;
  }
  static float[] Thump(float hzFrom,float hzTo,float len,float volume){
   int count=Mathf.RoundToInt(len*Rate);var d=new float[count];float phase=0;
   for(int i=0;i<count;i++){
    float u=i/(float)count;float hz=Mathf.Lerp(hzFrom,hzTo,u);phase+=hz/Rate;
    d[i]=volume*Mathf.Sin(2*Mathf.PI*phase)*(1-u)*(1-u);
   }
   return d;
  }
  // Band-limited noise with a crumple envelope (paper, fabric).
  static float[] Noise(float len,int seed,float volume,float cutHigh,float cutLow,float tremble){
   var rng=new System.Random(seed);int count=Mathf.RoundToInt(len*Rate);var d=new float[count];
   float lp=0,hp=0,prev=0;float aHigh=1-Mathf.Exp(-2*Mathf.PI*cutHigh/Rate);float aLow=1-Mathf.Exp(-2*Mathf.PI*cutLow/Rate);
   for(int i=0;i<count;i++){
    float t=i/(float)count;float x=(float)(rng.NextDouble()*2-1);
    lp+=aHigh*(x-lp);hp+=aLow*(lp-hp);float y=lp-hp;
    float crumple=1-tremble*.5f+tremble*.5f*Mathf.Sin(t*Mathf.PI*14f);
    float env=Mathf.Sin(Mathf.Clamp01(t*4)*Mathf.PI*.5f)*(1-t)*crumple;
    d[i]=volume*y*env;prev=y;
   }
   return d;
  }
  // Receipt printer: noise gated at ~38 Hz with a low-passed square feel.
  static float[] Buzz(float len,float gateHz,float volume){
   int count=Mathf.RoundToInt(len*Rate);var d=new float[count];var rng=new System.Random(5);float lp=0;
   for(int i=0;i<count;i++){
    float t=i/(float)Rate;float x=(float)(rng.NextDouble()*2-1);lp+=.25f*(x-lp);
    float gate=Mathf.Sin(2*Mathf.PI*gateHz*t)>0?1f:.25f;
    d[i]=volume*lp*gate*(1-t/len);
   }
   return d;
  }
  // Motorbike: each firing of the cylinder is an exhaust pulse that rings the pipe (resonators at 170, 620 and
  // 1500 Hz) plus a short rasp of noise; the firing rate follows the keys (rpm), with a little jitter per stroke so it
  // sounds mechanical, and the whole is softly saturated. keys: t, firing Hz, loudness 0..1, throttle 0..1, repeated.
  static float[] Moto(float len,int seed,params float[] keys){
   var rng=new System.Random(seed);int count=Mathf.RoundToInt(len*Rate);var d=new float[count];
   Res(170,110,out var a0,out var a1c,out var ag);Res(620,260,out var b0,out var b1c,out var bg);
   Res(1500,500,out var c0,out var c1c,out var cg);Res(3200,1800,out var n0,out var n1c,out var ng);
   float ya1=0,ya2=0,yb1=0,yb2=0,yc1=0,yc2=0,yn1=0,yn2=0,phase=0,kick=0,since=1,jit=1,max=0;
   for(int i=0;i<count;i++){
    float t=i/(float)Rate;Key(keys,t,out var hz,out var amp,out var thr);
    phase+=hz/Rate*jit;float x=0;
    if(phase>=1){phase-=1;kick=amp*(.8f+.4f*(float)rng.NextDouble());since=0;jit=1+.07f*((float)rng.NextDouble()-.5f);x=kick;}
    since+=1f/Rate;
    float nz=((float)rng.NextDouble()*2-1)*kick*Mathf.Exp(-since/.005f);
    float ya=x*ag+a0*ya1+a1c*ya2;ya2=ya1;ya1=ya;
    float yb=x*bg+b0*yb1+b1c*yb2;yb2=yb1;yb1=yb;
    float yc=x*cg+c0*yc1+c1c*yc2;yc2=yc1;yc1=yc;
    float yn=nz*ng+n0*yn1+n1c*yn2;yn2=yn1;yn1=yn;
    d[i]=ya+yb*(.5f+.6f*thr)+yc*(.12f+.25f*thr)+yn*(.06f+.12f*thr);
    max=Mathf.Max(max,Mathf.Abs(d[i]));
   }
   const float drive=2.2f;float norm=1f/(float)Math.Tanh(drive);
   for(int i=0;i<count;i++){
    float t=i/(float)Rate;float env=Mathf.Min(1,t/.08f)*Mathf.Min(1,(len-t)/.12f);
    d[i]=(float)Math.Tanh(drive*d[i]/Mathf.Max(1e-6f,max))*norm*Mathf.Max(0,env);
   }
   return d;
  }
  // Two-pole resonator at hz with the given bandwidth: y = g*x + c1*y1 + c2*y2.
  static void Res(float hz,float bw,out float c1,out float c2,out float g){
   float r=Mathf.Exp(-Mathf.PI*bw/Rate);c1=2*r*Mathf.Cos(2*Mathf.PI*hz/Rate);c2=-r*r;g=1-r;
  }
  // Smoothstep between key frames (groups of four: t, hz, amp, throttle).
  static void Key(float[] k,float t,out float hz,out float amp,out float thr){
   int n=k.Length/4;
   if(t<=k[0]){hz=k[1];amp=k[2];thr=k[3];return;}
   for(int g=1;g<n;g++){
    int a=(g-1)*4,b=g*4;
    if(t<=k[b]){
     float u=Mathf.Clamp01((t-k[a])/Mathf.Max(1e-4f,k[b]-k[a]));u=u*u*(3-2*u);
     hz=Mathf.Lerp(k[a+1],k[b+1],u);amp=Mathf.Lerp(k[a+2],k[b+2],u);thr=Mathf.Lerp(k[a+3],k[b+3],u);return;
    }
   }
   int l=(n-1)*4;hz=k[l+1];amp=k[l+2];thr=k[l+3];
  }
  // Two short soft square-ish beeps, low-passed.
  static float[] HornWave(){
   int count=Mathf.RoundToInt(.5f*Rate);var d=new float[count];float lp=0;float a=1-Mathf.Exp(-2*Mathf.PI*1800f/Rate);
   for(int i=0;i<count;i++){
    float t=i/(float)Rate;float v=0;
    for(int b=0;b<2;b++){
     float s=b*.2f;float bt=t-s;
     if(bt<0||bt>.14f)continue;
     float env=Mathf.Min(1,bt*200)*Mathf.Min(1,(.14f-bt)*150);
     float ph=bt*440;float sq=Mathf.Sign(Mathf.Sin(2*Mathf.PI*ph))*.6f+Mathf.Sin(2*Mathf.PI*ph)*.4f;
     v+=env*sq;
    }
    lp+=a*(v*.2f-lp);d[i]=lp;
   }
   return d;
  }
 }
}
