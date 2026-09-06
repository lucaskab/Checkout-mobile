using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;

namespace MarketDay
{
    public class MarketHUD : MonoBehaviour
    {
        MarketSimulation sim;Canvas canvas;RectTransform safe;RectTransform modal;RectTransform toast;
        Text coinText,levelText,xpText,statusText,dayText,toastText;Image xpFill;
        Font regular,bold;Sprite round,circle;Color ink=MarketSimulation.C("65442E"),cream=MarketSimulation.C("FFF1CF"),teal=MarketSimulation.C("238E80"),gold=MarketSimulation.C("F2BD50");
        float toastUntil;int panelKind=-1;Text panelStock,panelReserve,panelPrice,deliveryText;readonly List<GameObject> floats=new List<GameObject>();
        readonly List<Text> shelfLabels=new List<Text>();
        float width=1600,height=1000;
        public void Build(MarketSimulation game)
        {
            sim=game;
            regular=Resources.Load<Font>("MarketRegular")??Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            bold=Resources.Load<Font>("MarketBold")??regular;
            round=RoundedSprite(64,14);circle=RoundedSprite(64,32);
            canvas=gameObject.GetComponent<Canvas>();if(!canvas)canvas=gameObject.AddComponent<Canvas>();
            canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=sim.view;canvas.planeDistance=1;canvas.sortingOrder=10;
            var scaler=gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1600,1000);scaler.matchWidthOrHeight=.5f;
            gameObject.AddComponent<GraphicRaycaster>();
            safe=Rect(transform,"Safe area",0,0,1600,1000);safe.anchorMin=Vector2.zero;safe.anchorMax=Vector2.one;safe.offsetMin=Vector2.zero;safe.offsetMax=Vector2.zero;
            ApplySafeArea();
            BuildChrome();
            if(!sim.Economy.opened)Welcome();
        }
        void ApplySafeArea()
        {
            if(Screen.width==0||Screen.height==0)return;
            var a=Screen.safeArea;safe.anchorMin=a.position/new Vector2(Screen.width,Screen.height);safe.anchorMax=(a.position+a.size)/new Vector2(Screen.width,Screen.height);
            Canvas.ForceUpdateCanvases();width=safe.rect.width;height=safe.rect.height;
            if(width<100)width=1600;if(height<100)height=1000;
        }
        void BuildChrome()
        {
            var header=Card(safe,"Player card",22,20,332,94);
            var badge=Image(header,"Player badge",12,11,70,70,teal,circle);
            Label(badge.transform,"M",0,1,70,66,37,cream,TextAnchor.MiddleCenter,true);
            Label(header,"SUPERMARKET",98,11,224,25,24,ink,TextAnchor.MiddleLeft,true);
            levelText=Label(header,"Level 1",98,40,100,23,17,ink);
            xpText=Label(header,"0 / 50 XP",204,41,102,20,14,ink,TextAnchor.MiddleRight);
            Image(header,"XP track",99,70,211,9,MarketSimulation.C("DEC7A1"),round);
            xpFill=Image(header,"XP progress",99,70,10,9,MarketSimulation.C("51BACE"),round);
            var coins=Card(safe,"Coins",width/2-124,22,245,65);
            var icon=Image(coins,"Coin",13,10,44,44,gold,circle);Image(icon.transform,"Coin center",7,7,30,30,MarketSimulation.C("F8D678"),circle);Label(icon.transform,"$",0,0,44,44,24,ink,TextAnchor.MiddleCenter,true);
            coinText=Label(coins,"850",70,4,145,57,30,ink,TextAnchor.MiddleLeft,true);
            var goals=Card(safe,"Goal peek",width-286,20,264,94);
            Label(goals,"TODAY'S GOALS",17,10,226,24,20,ink,TextAnchor.MiddleLeft,true);
            statusText=Label(goals,"Serve 5 happy customers",17,40,229,23,16,ink);
            Button(goals,"View goals",143,66,105,21,teal,()=>GoalsPanel(),12);
            var ribbon=Card(safe,"Store status",width/2-126,94,252,33);
            dayText=Label(ribbon,"DAY 1  /  READY TO OPEN",4,2,244,29,14,teal,TextAnchor.MiddleCenter,true);
            // Bottom dock is intentionally spacious for thumbs.
            float bw=112,gap=12,total=5*bw+4*gap,left=(width-total)/2;
            string[] labels={"STORE","STORAGE","WORKERS","UPGRADE","GOALS"};
            string[] icons={"shop","crate","people","hammer","list"};
            Action[] acts={StorePanel,StoragePanel,WorkersPanel,UpgradesPanel,GoalsPanel};
            for(int i=0;i<5;i++)
            {
                int ii=i;var dock=Card(safe,labels[i],left+i*(bw+gap),height-123,bw,100);
                var b=dock.gameObject.AddComponent<Button>();b.onClick.AddListener(()=>acts[ii]());b.targetGraphic=dock.GetComponent<Image>();
                DrawIcon(dock,icons[i],36,11,41,teal);
                Label(dock,labels[i],0,65,bw,27,15,ink,TextAnchor.MiddleCenter,true);
            }
            Button(safe,"-",width-66,height-260,44,44,cream,()=>sim.Zoom(1.4f),27,ink);
            Button(safe,"+",width-66,height-311,44,44,cream,()=>sim.Zoom(-1.4f),27,ink);
            Button(safe,"HOME",width-99,height-203,77,35,cream,()=>sim.HomeCamera(),13,ink);
            Button(safe,"1x / 2x",24,height-64,107,40,cream,()=>{sim.speed=sim.speed==1?2:sim.speed==2?0:1;Toast(sim.speed==0?"Simulation paused":"Simulation speed: "+sim.speed+"x",teal);},15,ink);
            Label(safe,"Drag to explore  /  Pinch to zoom",24,height-94,320,22,14,MarketSimulation.C("FFF8DE"));
            toast=Card(safe,"Notification",width/2-270,143,540,49);toastText=Label(toast,"",15,5,510,40,18,ink,TextAnchor.MiddleCenter,true);toast.gameObject.SetActive(false);
        }
        public void Refresh()
        {
            if(sim==null||coinText==null)return;
            if(safe!=null&&(Mathf.Abs(safe.rect.width-width)>1||Mathf.Abs(safe.rect.height-height)>1))Relayout();
            var e=sim.Economy;coinText.text=e.coins.ToString("N0");levelText.text="Level "+e.Level;xpText.text=(e.xp%50)+" / 50 XP";
            xpFill.rectTransform.sizeDelta=new Vector2(Mathf.Max(9,211*(e.xp%50)/50f),9);
            statusText.text=e.served<5?"Serve customers  "+e.served+" / 5":"Goals ready to collect";
            dayText.text=sim.speed==0?"PAUSED":e.opened?"DAY 1  /  OPEN FOR BUSINESS":"DAY 1  /  READY TO OPEN";
            if(toast!=null&&Time.unscaledTime>toastUntil)toast.gameObject.SetActive(false);
            if(panelKind>=0&&panelKind<5&&modal!=null)
            {
                var d=e.departments[panelKind];panelStock.text=d.stock+" / "+d.Capacity;panelReserve.text=d.reserve+" units";panelPrice.text=d.Price+" coins";
                deliveryText.text=d.incoming>0?"Delivery arrives in "+Mathf.CeilToInt(d.deliveryRemaining)+"s":"Supplier ready  /  20 units for 60 coins";
            }
        }
        public void Relayout()
        {
            if(!safe)return;
            int previous=panelKind;
            foreach(Transform child in safe){child.gameObject.SetActive(false);Destroy(child.gameObject);}
            modal=null;panelKind=-1;ApplySafeArea();BuildChrome();
            if(previous>=0&&previous<5)DepartmentPanel(previous);
            else if(previous==6)StorePanel();else if(previous==7)StoragePanel();else if(previous==8)WorkersPanel();else if(previous==9)UpgradesPanel();else if(previous==10)GoalsPanel();
        }
        RectTransform StartPanel(string title,string subtitle,int h=540)
        {
            ClosePanel();
            var shade=Image(safe,"Modal shade",0,0,width,height,new Color(.14f,.21f,.17f,.22f));
            modal=shade.rectTransform;modal.SetAsLastSibling();
            var back=shade.gameObject.AddComponent<Button>();back.onClick.AddListener(ClosePanel);
            var card=Card(modal,"Details",width/2-280,height/2-h/2,560,h);
            // Consume taps on the card without dismissing it.
            card.gameObject.AddComponent<Button>();
            Image(card,"Top accent",0,0,560,9,teal,round);
            Label(card,title,30,23,455,43,30,ink,TextAnchor.MiddleLeft,true);
            Label(card,subtitle,30,70,490,45,16,ink);
            Button(card,"X",503,21,34,34,MarketSimulation.C("E8D1A7"),ClosePanel,18,ink);
            return card;
        }
        public void ClosePanel(){if(modal!=null)Destroy(modal.gameObject);modal=null;panelKind=-1;}
        public void Welcome()
        {
            var p=StartPanel("A little store. A busy day.","Your neighborhood supermarket is ready for its first customers.",466);
            DrawIcon(p,"shop",236,121,80,teal);
            Label(p,"Stock the shelves. Welcome your neighbors.",40,229,480,28,21,ink,TextAnchor.MiddleCenter,true);
            Label(p,"Tap a department to manage its stock. Order supplies from storage,\nthen let your team keep the displays full. Earn coins as shoppers pay.",42,271,478,65,17,ink,TextAnchor.MiddleCenter);
            Button(p,"OPEN THE SUPERMARKET",80,366,400,58,teal,sim.OpenStore,20);
        }
        public void DepartmentPanel(int i)
        {
            var d=sim.Economy.departments[i];var p=StartPanel(sim.names[i],sim.descriptions[i],540);panelKind=i;
            Image(p,"Department tint",26,123,508,93,MarketSimulation.C("F1E1BF"),round);
            Label(p,"ON DISPLAY",44,137,140,23,13,ink,TextAnchor.MiddleCenter,true);
            panelStock=Label(p,"",44,168,140,32,28,teal,TextAnchor.MiddleCenter,true);
            Label(p,"IN STORAGE",209,137,140,23,13,ink,TextAnchor.MiddleCenter,true);
            panelReserve=Label(p,"",209,168,140,32,26,ink,TextAnchor.MiddleCenter,true);
            Label(p,"SALE PRICE",374,137,140,23,13,ink,TextAnchor.MiddleCenter,true);
            panelPrice=Label(p,"",374,168,140,32,26,ink,TextAnchor.MiddleCenter,true);
            Button(p,"RESTOCK DISPLAY",30,238,241,55,teal,()=>sim.QueueRefill(i),17);
            Button(p,"ORDER SUPPLIES  /  60",285,238,245,55,sim.accents[i],()=>sim.Order(i),16);
            deliveryText=Label(p,"",32,304,496,28,16,ink,TextAnchor.MiddleCenter);
            Label(p,"DEPARTMENT LEVEL "+d.level,32,362,340,29,17,ink,TextAnchor.MiddleLeft,true);
            Label(p,"More shelf space. Better prices.",32,399,340,29,17,ink);
            Button(p,d.level<5?"UPGRADE  /  "+d.UpgradeCost:"MAX LEVEL",30,456,500,55,gold,()=>sim.Upgrade(i),19,ink);
            Refresh();
        }
        public void StorePanel()
        {
            var p=StartPanel("Your supermarket","Choose a department to manage its displays and supplies.",581);panelKind=6;
            for(int i=0;i<5;i++)
            {
                int k=i;var d=sim.Economy.departments[i];
                var row=Card(p,"Department row",27,123+i*72,506,61,MarketSimulation.C("F3E2BF"));
                Image(row,"Department dot",14,16,28,28,sim.accents[i],circle);
                Label(row,sim.names[i],57,6,265,28,20,ink,TextAnchor.MiddleLeft,true);
                Label(row,d.stock+" on display  /  Level "+d.level,57,33,320,23,14,ink);
                Button(row,"VIEW",408,12,83,36,teal,()=>DepartmentPanel(k),14);
            }
            if(!sim.Economy.opened)Button(p,"OPEN STORE",29,500,502,54,teal,sim.OpenStore,18);
            else Label(p,sim.Economy.served+" customers served  /  "+sim.Economy.workers+" stock workers",30,505,500,33,18,teal,TextAnchor.MiddleCenter,true);
        }
        public void StoragePanel()
        {
            var p=StartPanel("Central storage","Deliveries go to storage. Your workers refill the shop displays.",615);panelKind=7;
            Label(p,"WAREHOUSE  "+sim.Economy.WarehouseUsed+" / 250 UNITS",30,122,500,29,19,teal,TextAnchor.MiddleLeft,true);
            Image(p,"Storage bar",30,161,500,10,MarketSimulation.C("DEC7A1"),round);
            Image(p,"Storage fill",30,161,Mathf.Max(10,500*sim.Economy.WarehouseUsed/250f),10,teal,round);
            for(int i=0;i<5;i++)
            {
                int k=i;var d=sim.Economy.departments[i];var r=Card(p,"Stock row",27,194+i*73,506,62,MarketSimulation.C("F3E2BF"));
                Label(r,sim.names[i],16,6,260,28,20,ink,TextAnchor.MiddleLeft,true);
                Label(r,d.reserve+" stored"+(d.incoming>0?"  /  delivery on its way":"  /  supplier ready"),16,33,310,23,14,ink);
                Button(r,d.incoming>0?"IN TRANSIT":"ORDER / 60",358,12,133,38,d.incoming>0?MarketSimulation.C("AFA885"):teal,()=>{sim.Order(k);StoragePanel();},13);
            }
        }
        public void WorkersPanel()
        {
            var p=StartPanel("Meet your team","Your specialists serve each counter. Stock workers refill displays.",470);panelKind=8;
            DrawIcon(p,"people",238,120,82,teal);
            Label(p,sim.Economy.workers+" / 3 STOCK WORKERS",30,227,500,33,23,ink,TextAnchor.MiddleCenter,true);
            Label(p,"Stock workers automatically respond when displays run low.\nYou can also assign a refill from any department.",34,278,490,61,17,ink,TextAnchor.MiddleCenter);
            Button(p,sim.Economy.workers<3?"HIRE A WORKER  /  "+250*sim.Economy.workers:"TEAM COMPLETE",30,375,500,58,gold,sim.Hire,20,ink);
        }
        public void UpgradesPanel()
        {
            var p=StartPanel("Room to grow","Improve a department to raise its capacity and selling price.",573);panelKind=9;
            for(int i=0;i<5;i++)
            {
                int k=i;var d=sim.Economy.departments[i];var r=Card(p,"Upgrade row",27,123+i*78,506,67,MarketSimulation.C("F3E2BF"));
                Label(r,sim.names[i]+"  /  Lv. "+d.level,15,7,300,28,19,ink,TextAnchor.MiddleLeft,true);
                Label(r,d.Capacity+" shelf capacity  /  "+d.Price+" coins per sale",15,36,340,23,13,ink);
                Button(r,d.level<5?"+  "+d.UpgradeCost:"MAX",384,15,107,37,gold,()=>{sim.Upgrade(k);UpgradesPanel();},16,ink);
            }
        }
        public void GoalsPanel()
        {
            var p=StartPanel("A great first day","Complete each goal and collect a little thank-you for your work.",474);panelKind=10;
            string[] title={"Serve 5 happy customers","Refill 10 products","Receive 20 supplies"};
            for(int i=0;i<3;i++)
            {
                int k=i;int n=sim.Economy.GoalProgress(i),target=sim.Economy.GoalTarget(i);bool done=sim.Economy.claimed[i];
                var r=Card(p,"Goal row",27,129+i*103,506,89,MarketSimulation.C("F3E2BF"));
                Label(r,title[i],16,9,330,27,20,ink,TextAnchor.MiddleLeft,true);
                Label(r,done?"Collected  /  thank you!":Mathf.Min(n,target)+" / "+target+"  /  reward: 100 coins",16,46,323,26,15,ink);
                Button(r,done?"DONE":n>=target?"CLAIM":"+100",383,23,108,41,done?MarketSimulation.C("A3BA83"):n>=target?gold:MarketSimulation.C("D6C6A5"),()=>sim.Claim(k),16,ink);
            }
        }
        public void Toast(string message,Color color)
        {
            if(toast==null)return;toastText.text=message;toastText.color=color;toast.gameObject.SetActive(true);toast.SetAsLastSibling();toastUntil=Time.unscaledTime+4;
        }
        public void FloatLabel(Vector3 worldPosition,string words,Color color)
        {
            var screen=sim.view.WorldToScreenPoint(worldPosition);if(screen.z<0)return;
            var go=new GameObject("Sale notification",typeof(RectTransform));go.transform.SetParent(safe,false);
            var t=go.AddComponent<Text>();t.font=bold;t.text=words;t.fontSize=25;t.alignment=TextAnchor.MiddleCenter;t.color=color;t.raycastTarget=false;
            var shadow=go.AddComponent<Shadow>();shadow.effectColor=cream;shadow.effectDistance=new Vector2(1,-2);
            var rt=(RectTransform)go.transform;rt.anchorMin=rt.anchorMax=Vector2.zero;rt.pivot=new Vector2(.5f,0);rt.sizeDelta=new Vector2(150,36);
            rt.anchoredPosition=new Vector2(screen.x/Screen.width*width,screen.y/Screen.height*height);
            var motion=go.AddComponent<FloatingLabel>();motion.text=t;
        }
        RectTransform Rect(Transform parent,string name,float x,float y,float w,float h)
        {
            var go=new GameObject(name,typeof(RectTransform));var r=(RectTransform)go.transform;r.SetParent(parent,false);r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);return r;
        }
        Image Image(Transform parent,string name,float x,float y,float w,float h,Color col,Sprite sprite=null)
        {
            var r=Rect(parent,name,x,y,w,h);var image=r.gameObject.AddComponent<Image>();image.color=col;image.sprite=sprite;if(sprite){image.type=UnityEngine.UI.Image.Type.Sliced;}return image;
        }
        RectTransform Card(Transform parent,string name,float x,float y,float w,float h,Color? fill=null)
        {
            var image=Image(parent,name,x,y,w,h,fill??cream,round);var sh=image.gameObject.AddComponent<Shadow>();sh.effectColor=new Color(.28f,.19f,.10f,.31f);sh.effectDistance=new Vector2(0,-4);return image.rectTransform;
        }
        Text Label(Transform parent,string value,float x,float y,float w,float h,int size,Color col,TextAnchor align=TextAnchor.MiddleLeft,bool strong=false)
        {
            var r=Rect(parent,"Label",x,y,w,h);var t=r.gameObject.AddComponent<Text>();t.font=strong?bold:regular;t.text=value;t.fontSize=size;t.color=col;t.alignment=align;t.raycastTarget=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Overflow;return t;
        }
        Button Button(Transform parent,string title,float x,float y,float w,float h,Color bg,Action act,int size=18,Color? fg=null)
        {
            var r=Card(parent,title,x,y,w,h,bg);var b=r.gameObject.AddComponent<Button>();b.targetGraphic=r.GetComponent<Image>();
            var colors=b.colors;colors.highlightedColor=new Color(1.04f,1.04f,1.04f);colors.pressedColor=new Color(.9f,.9f,.9f);b.colors=colors;b.onClick.AddListener(()=>{ClickSound();act();});
            Label(r,title,5,0,w-10,h,size,fg??cream,TextAnchor.MiddleCenter,true);return b;
        }
        void DrawIcon(Transform p,string kind,float x,float y,float s,Color color)
        {
            var r=Rect(p,"Icon",x,y,s,s);
            Action<float,float,float,float> box=(a,b,w,h)=>{var im=Image(r,"Icon shape",a*s,b*s,w*s,h*s,color);im.raycastTarget=false;};
            Action<float,float,float> dot=(a,b,d)=>{var im=Image(r,"Icon shape",a*s,b*s,d*s,d*s,color,circle);im.raycastTarget=false;};
            if(kind=="shop") {box(.09f,.38f,.82f,.57f);box(.0f,.20f,1,.21f);box(.18f,.05f,.64f,.13f);Image(r,"Door",s*.42f,s*.57f,s*.21f,s*.4f,cream,round).raycastTarget=false;}
            if(kind=="crate") {box(.04f,.12f,.92f,.82f);for(int i=1;i<3;i++)Image(r,"Slat gap",s*.1f,s*(.15f+i*.22f),s*.8f,s*.04f,cream).raycastTarget=false;Image(r,"Crate label",s*.38f,s*.25f,s*.24f,s*.12f,cream,round).raycastTarget=false;}
            if(kind=="people") {dot(.05f,.12f,.34f);dot(.59f,.12f,.34f);dot(.32f,0,.37f);box(.0f,.50f,.4f,.42f);box(.58f,.50f,.4f,.42f);box(.27f,.40f,.47f,.6f);}
            if(kind=="hammer") {var handle=Image(r,"Handle",s*.40f,s*.28f,s*.19f,s*.73f,color,round);handle.rectTransform.localRotation=Quaternion.Euler(0,0,-30);handle.raycastTarget=false;box(.10f,.08f,.75f,.28f);box(.68f,.04f,.20f,.36f);}
            if(kind=="list") {box(.13f,.09f,.75f,.89f);Image(r,"Paper",s*.23f,s*.21f,s*.55f,s*.68f,cream,round).raycastTarget=false;for(int i=0;i<3;i++){box(.33f,.29f+i*.19f,.34f,.05f);}box(.35f,0,.31f,.23f);}
        }
        Sprite RoundedSprite(int size,int radius)
        {
            var tex=new Texture2D(size,size,TextureFormat.RGBA32,false);tex.name="Original rounded interface shape";tex.filterMode=FilterMode.Bilinear;
            var pixels=new Color[size*size];for(int y=0;y<size;y++)for(int x=0;x<size;x++)
            {float dx=Mathf.Max(radius-x,x-(size-1-radius));float dy=Mathf.Max(radius-y,y-(size-1-radius));float d=Mathf.Sqrt(Mathf.Max(dx,0)*Mathf.Max(dx,0)+Mathf.Max(dy,0)*Mathf.Max(dy,0));pixels[y*size+x]=new Color(1,1,1,Mathf.Clamp01(radius-d+.5f));}
            tex.SetPixels(pixels);tex.Apply();return Sprite.Create(tex,new Rect(0,0,size,size),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect,new Vector4(radius,radius,radius,radius));
        }
        AudioSource sound;AudioClip click;
        void ClickSound()
        {
            if(!Application.isPlaying)return;
            if(sound==null){sound=gameObject.AddComponent<AudioSource>();sound.volume=.11f;int n=2205;var data=new float[n];for(int i=0;i<n;i++)data[i]=Mathf.Sin(i*2*Mathf.PI*840/44100)*Mathf.Exp(-i/400f);click=AudioClip.Create("Original soft UI chime",n,1,44100,false);click.SetData(data,0);}
            sound.PlayOneShot(click);
        }
    }
    public class FloatingLabel:MonoBehaviour
    {
        public Text text;float t;
        void Update(){t+=Time.unscaledDeltaTime;transform.localPosition+=Vector3.up*Time.unscaledDeltaTime*24;if(text)text.color=new Color(text.color.r,text.color.g,text.color.b,Mathf.Clamp01(2-t));if(t>2)Destroy(gameObject);}
    }
}
