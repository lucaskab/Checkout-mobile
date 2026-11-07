using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Launch trailer footage (Lucas 07/11: "um trailer do jogo... começa na mesinha... chega na rede com o mapa todo
 // evoluído, o supermercado cheio de clientes"), on the QA copy of the save (the player's own save is never touched):
 // "eventstrailer-<pt|en>[-scene.scene...]". The Game view goes to 1920x1080 and the game to that language; every shot
 // is recorded to Logs/tr_<lang>_<scene>_<k>.mjpg (30 fps JPEG frames back to back, ffmpeg reads them) with the HUD
 // hidden for the cinematic shots and shown for the mini-games. The trailer itself is cut outside Unity.
 // Scenes, in story order: mesa (the little table), caixa (the register), cresce (tenda → mercadinho, one shot each),
 // repor (the restock game), hiper (the hypermarket full of customers, its checkouts and sectors), padaria (the
 // sector puzzles), evento (live events), rede (the chain: facade, distribution centre, the whole map from above).
 public sealed partial class CheckoutAutoTest {
  int recW = 1280, recQ = 74;
  readonly List<Canvas> trHidden = new List<Canvas>();
  int trSeq; string trLang = "pt"; string trScene = ""; int trShotK;
  /// <summary>The chain's name when eventscrowd names it (".brand").</summary>
  string crowdChainName = "Bom Preço";

  void TrHud(string action, string args) => CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-tr-" + (++trSeq) + "\",\"action\":\"" + action + "\",\"args\":" + args + "}");
  MarketDay.MarketSimulation TrSim => FindAnyObjectByType<MarketDay.MarketSimulation>();

  /// <summary>Hides (or shows back) every screen-space canvas: the HUD, windows, balloons. World labels stay.</summary>
  void TrHideHud(bool hide) {
   if (hide) {
    foreach (var c in FindObjectsByType<Canvas>(FindObjectsSortMode.None))
     if (c && c.enabled && c.isRootCanvas && c.renderMode == RenderMode.ScreenSpaceOverlay) { c.enabled = false; trHidden.Add(c); }
   } else { foreach (var c in trHidden) if (c) c.enabled = true; trHidden.Clear(); }
  }

  readonly List<Renderer> trWorldHidden = new List<Renderer>();
  /// <summary>Padlocks over the lots, markers, price plates and rings in the world: hidden in the cinematic shots
  /// (as the friend's postcard does, CheckoutSocial.PostcardHide). Request bubbles stay: they show a living shop.</summary>
  void TrHideWorld(bool hide) {
   if (!hide) { foreach (var r in trWorldHidden) if (r) r.enabled = true; trWorldHidden.Clear(); return; }
   string[] words = { "Padlock", "Marker", "Speed up", "Plate", "Ring" };
   foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)) {
    if (!r.enabled) continue; var t = r.transform; bool hit = false;
    for (int depth = 0; depth < 3 && t && !hit; depth++, t = t.parent) foreach (var w in words) if (t.name.Contains(w)) { hit = true; break; }
    if (hit) { r.enabled = false; trWorldHidden.Add(r); }
   }
  }

  /// <summary>Shoppers sent to the shop one after another (as eventscrowd does), each buying two or three things
  /// from the shop's shelves, until `count` were sent or the coroutine is stopped.</summary>
  IEnumerator TrSpawn(int count, float gap) {
   var rnd = new System.Random(7);
   var all = FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include, FindObjectsSortMode.None).ToList();
   for (int sent = 0; sent < count;) {
    var shelfIds = (bridge.State.shelves ?? new Shelf[0]).Where(x => x != null && x.unlocked && !x.building).Select(x => x.id).ToList();
    var idle = all.FirstOrDefault(w => w && !w.gameObject.activeSelf && !w.Reserved);
    if (idle && shelfIds.Count > 0 && !CheckoutWalker.ShopCrowded) {
     var buy = new List<Purchase>(); int k = 2 + rnd.Next(2);
     for (int j = 0; j < k; j++) buy.Add(new Purchase { shelfId = shelfIds[rnd.Next(shelfIds.Count)], productId = 1, quantity = 1 + rnd.Next(2) });
     idle.Begin(new Customer { id = "qa-trailer-" + sent, name = "QA", spent = 12, purchases = buy.ToArray() });
     sent++; yield return new WaitForSecondsRealtime(gap);
    } else yield return new WaitForSecondsRealtime(.5f);
   }
  }

  /// <summary>A cinematic shot (no HUD): the camera glides from (a, za) to (b, zb).</summary>
  IEnumerator TrGlideShot(Vector3 a, float za, Vector3 b, float zb, float seconds) => TrShot(false, TrGlide(a, za, b, zb, seconds), a, za);

  /// <summary>The camera from (a, za) to (b, zb) in `seconds` of video, eased; one step per recorded frame.</summary>
  IEnumerator TrGlide(Vector3 a, float za, Vector3 b, float zb, float seconds) {
   var sim = TrSim; int n = Mathf.Max(1, Mathf.RoundToInt(seconds * 30));
   for (int i = 0; i <= n; i++) {
    float t = i / (float)n; t = t * t * (3 - 2 * t);
    if (sim) sim.FocusCinematic(Vector3.Lerp(a, b, t), Mathf.Lerp(za, zb, t));
    if (i < n) yield return null;
   }
  }

  /// <summary>One recorded shot: Logs/tr_<lang>_<scene>_<k>.mjpg while `body` runs.</summary>
  IEnumerator TrShot(bool hud, IEnumerator body, Vector3? startAt = null, float startZoom = 0) {
   yield return CloseCardsSettled();
   var sim = TrSim; var was = MarketDay.MarketSimulation.Cinematic; MarketDay.MarketSimulation.Cinematic = true;
   if (startAt.HasValue && sim) { sim.FocusCinematic(startAt.Value, startZoom); yield return new WaitForSecondsRealtime(.5f); }
   TrHideHud(!hud); if (!hud) TrHideWorld(true);
   var path = $"Logs/tr_{trLang}_{trScene}_{++trShotK}.mjpg";
   RecStart(path);
   try { yield return body; }
   finally { RecStop(); TrHideHud(false); TrHideWorld(false); MarketDay.MarketSimulation.Cinematic = was; Note($"TRAILER shot {path}"); }
  }

  /// <summary>Waits for a log line containing `text` written after the call (at most `timeout` seconds).</summary>
  IEnumerator TrWaitLog(string text, float timeout) {
   int from = log.Count;
   for (float t = 0; t < timeout; t += .5f) {
    for (int i = from; i < log.Count; i++) if (log[i].Contains(text)) yield break;
    yield return new WaitForSecondsRealtime(.5f);
   }
   Note("trailer: no '" + text + "' in " + timeout + " s");
  }

  IEnumerator TrOpen() {
   if (bridge.State.isOpen) yield break;
   TrHud("claimDayResult", "[]"); yield return new WaitForSecondsRealtime(1);
   TrHud("startDay", "[\"livre\"]"); for (float t = 0; t < 4 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f);
   if (!bridge.State.isOpen) { TrHud("setMarketOpen", "[true]"); for (float t = 0; t < 6 && !bridge.State.isOpen; t += .5f) yield return new WaitForSecondsRealtime(.5f); }
  }

  /// <summary>Where the shop is: the market building's floor, or the stall / small shop.</summary>
  (Vector3 center, float size) TrShop() {
   var inside = CheckoutInterior.Active;
   if (inside && !CheckoutStall.Small) { var f = inside.FloorRect; return (new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height)); }
   var fp = CheckoutStall.Footprint; return (new Vector3(fp.center.x, 0, fp.center.z), Mathf.Max(fp.size.x, fp.size.z));
  }

  Coroutine trCrowd;
  /// <summary>A stage furnished and full of shoppers (eventscrowd: every piece of the expansion placed, shelves stocked,
  /// the register served at once); returns once its shoppers are on their way. The crowd keeps running until the next.</summary>
  IEnumerator TrCrowd(string stage, int shoppers, string extra = "") {
   if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
   int from = log.Count;
   trCrowd = StartCoroutine(Crowd($"eventscrowd-{stage}.240.{shoppers}.stock{extra}"));
   yield return TrWaitLog("CROWD day ", 150);
   Note($"trailer: {stage} ready (era {bridge.State?.era?.id}, open {bridge.State?.isOpen})");
  }

  /// <summary>The shop's shelves and sector counters laid out like a tidy player's shop: evenly along the back wall,
  /// then an island row in the middle (eventscrowd stands them all near one corner). Checkouts stay where they are.</summary>
  void TrArrange() {
   var inside = CheckoutInterior.Active; var map = FindAnyObjectByType<CheckoutMap>(); if (!inside || !map) return;
   var fl = inside.FloorRect;
   var pieces = inside.items.Values.Where(i => i.root && i.functional && !i.outside && !i.building && (i.type == "shelf" || i.type == "sector"))
    .OrderBy(i => i.type == "sector" ? 0 : 1).ThenBy(i => i.id).Select(i => i.id).ToList();
   if (pieces.Count == 0) return;
   inside.editing = true;
   foreach (var id in pieces) inside.Unplace(inside.Get(id));
   int nBack = Mathf.Max(1, Mathf.FloorToInt((fl.width - 2f) / 1.8f));
   int back = Mathf.Min(nBack, pieces.Count <= 6 ? pieces.Count : Mathf.CeilToInt(pieces.Count * .6f)), mid = pieces.Count - back;
   var spots = new List<Vector3>();
   for (int i = 0; i < back; i++) spots.Add(new Vector3(fl.xMin + 1f + (fl.width - 2f) * (i + .5f) / back, CheckoutInterior.Floor, fl.yMax - .8f));
   for (int i = 0; i < mid; i++) spots.Add(new Vector3(fl.xMin + 2.2f + (fl.width - 4.4f) * (i + .5f) / mid, CheckoutInterior.Floor, fl.center.y + .2f));
   int put = 0;
   for (int k = 0; k < pieces.Count; k++) {
    var it = inside.PlaceWaiting(pieces[k], spots[k]);
    if (it != null && !inside.Reachable(out _)) { inside.Unplace(it); it = null; }
    if (it == null) it = inside.PlaceWaiting(pieces[k], new Vector3(fl.center.x, CheckoutInterior.Floor, fl.yMax - 1.5f));
    if (it != null) put++;
   }
   map.FurnitureChanged(false); map.SaveInterior(); inside.MarkPending(); inside.editing = false;
   Note($"trailer: arranged {put}/{pieces.Count} pieces ({back} along the back wall)");
  }

  /// <summary>The shop's fixtures at the tier a player who evolved them would have (bigger gondolas, premium finish),
  /// through the same snapshot patch as eventstiers; sectors only where all of them belong (hipermercado, rede).</summary>
  void TrTiers(int shelves, int sectors) {
   tierPatching = shelves > 0 || sectors > 0; tierShelves = shelves; tierSector = sectors;
   CheckoutBridge.TestPatch = tierPatching ? s => { Patch(s); PatchTiers(s); } : (System.Action<Snapshot>)Patch;
  }

  /// <summary>Decorations in the shop (not saved, not bought: only the picture), spread over the open floor in front
  /// of the shelves, and a few outside by the door.</summary>
  void TrDecorate(string[] inside, string[] outside) {
   var room = CheckoutInterior.Active; if (!room) return;
   var fl = room.FloorRect; int put = 0;
   for (int i = 0; i < inside.Length; i++) {
    float u = (i + .5f) / inside.Length;
    var p = new Vector3(fl.xMin + 2f + (fl.width - 4f) * u, CheckoutInterior.Floor, fl.yMin + fl.height * (i % 2 == 0 ? .34f : .58f));
    if (room.AddDecor(inside[i], p) != null) put++;
   }
   var door = room.EntrancePoint;
   for (int i = 0; i < outside.Length; i++) {
    var p = door + new Vector3((i - (outside.Length - 1) * .5f) * 2.6f + (i >= outside.Length / 2 ? 2f : -2f), 0, -2.2f);
    if (room.AddDecor(outside[i], p, true) != null) put++;
   }
   Note($"trailer: {put} decorations");
  }

  static IEnumerator TrThen(IEnumerator work, System.Action done) { yield return work; done(); }

  IEnumerator Trailer(string request) {
   var parts = request.Split('-');
   trLang = parts.Length > 1 && parts[1] == "en" ? "en" : "pt";
   var scenes = parts.Length > 2 ? parts[2].Split('.') : new[] { "mesa", "caixa", "cresce", "repor", "hiper", "padaria", "evento", "rede" };
   if (!CheckoutStartMenu.QaMode) { Note("trailer: not on the QA copy, stopping"); yield break; }
   Note("trailer: " + CheckoutQaGameView.Set(1920, 1080));
   void Lang(string l) { CheckoutI18n.SetLanguage(l); CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"" + l + "\"}"); }
   var langBefore = CheckoutI18n.Language; Lang(trLang);
   crowdChainName = trLang == "en" ? "Fresh Market" : "Bom Preço";
   recW = 1920; recQ = 90;
   yield return new WaitForSecondsRealtime(2f);
   try {
    foreach (var scene in scenes) {
     trScene = scene; trShotK = 0;
     foreach (var f in Directory.GetFiles("Logs", $"tr_{trLang}_{scene}_*.mjpg")) File.Delete(f);
     Note("TRAILER scene " + scene);
     IEnumerator run = scene == "mesa" ? TrMesa() : scene == "caixa" ? TrCaixa() : scene == "cresce" ? TrCresce() : scene == "repor" ? TrRepor()
      : scene == "hiper" ? TrHiper() : scene == "padaria" ? TrPadaria() : scene == "evento" ? TrEvento() : scene == "rede" ? TrRede() : null;
     if (run == null) { Note("trailer: unknown scene " + scene); continue; }
     yield return run;
    }
   } finally {
    if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
    roomEra = -1; roomKeepInterior = false; roomLanes = false; crowdLayout = null; lowShelves = false; TrTiers(-1, -1);
    recW = 1280; recQ = 74; TrHideHud(false); MarketDay.MarketSimulation.Cinematic = false; crowdChainName = "Bom Preço";
    Lang(langBefore); Note("trailer: language back to " + CheckoutI18n.Language);
   }
  }

  // ── scenes ──────────────────────────────────────────────────────────────────────────────────────────────────────

  IEnumerator TrMesa() {
   TrHud("resetGame", "[]"); yield return new WaitForSecondsRealtime(5f);
   TrHud("skipOnboarding", "[]"); yield return new WaitForSecondsRealtime(1.5f);
   yield return TrOpen();
   var spawn = StartCoroutine(TrSpawn(8, 2.5f));
   yield return new WaitForSecondsRealtime(14f);   // the first customers walk up to the table
   var (c, _) = TrShop();
   yield return TrGlideShot(c + new Vector3(.6f, 0, .3f), 3.6f, c, 5f, 4.5f);
   yield return TrGlideShot(c, 6f, c + new Vector3(-1.5f, 0, 1f), 9.5f, 4f);
   StopCoroutine(spawn);
  }

  IEnumerator TrCaixa() {
   var game = CheckoutCounterGame.Instance; if (!game) { Note("trailer: no register"); yield break; }
   bool en = trLang == "en";
   var lines = (bridge.State.shelves ?? new Shelf[0]).Where(s => s != null && s.productId > 0 && !string.IsNullOrEmpty(s.productName) && s.price > 0)
    .GroupBy(s => s.productId).Select(g => g.First()).Take(3)
    .Select((s, i) => new CheckoutLine { productId = s.productId, quantity = i == 0 ? 2 : 1, name = s.productName, unitPrice = System.Math.Max(1, System.Math.Round(s.price)) }).ToList();
   if (lines.Count < 2) lines = new List<CheckoutLine> {
    new CheckoutLine { productId = 1, quantity = 2, name = en ? "Tomato" : "Tomate", unitPrice = 6 },
    new CheckoutLine { productId = 14, quantity = 1, name = en ? "Soda" : "Refrigerante", unitPrice = 9 },
   };
   double total = lines.Sum(l => l.unitPrice * l.quantity);
   double given = total <= 20 ? 20 : total <= 50 ? 50 : 100;
   var fake = new CheckoutEntry { id = "qa-trailer", customerId = "", customerName = "Dona Neide", mood = "", method = "dinheiro", total = total, cashGiven = given, readyAt = 0, expiresAt = double.MaxValue, items = lines.ToArray() };
   game.OpenPreview(fake);
   yield return TrShot(true, TrCounterPlay(game));
   game.Close(); yield return new WaitForSecondsRealtime(1f);
  }
  IEnumerator TrCounterPlay(CheckoutCounterGame game) {
   yield return Frames(1.0f);
   yield return game.QaScanAll();
   yield return Frames(.7f);
   game.QaPayAll(); yield return Frames(1.3f);
   for (int i = 0; i < 12 && game.QaChanging; i++) { game.QaGive(game.QaNextChange); yield return Frames(.4f); }
   yield return Frames(1.6f);
  }

  IEnumerator TrCresce() {
   // a player well on the way: the shelves have their products (they come with the levels)
   TrHud("setMarketLevel", "[45]"); TrHud("devAdjustCoins", "[9000000]"); yield return new WaitForSecondsRealtime(2f);
   TrHud("dismissLevelUp", "[]"); yield return CloseCardsSettled();
   foreach (var stage in new[] { "tenda", "banca", "conteiner", "spati", "quitanda", "minimercado", "mercadinho" }) {
    if (System.Array.IndexOf(EraIds, stage) >= 4) {
     TrTiers(stage == "minimercado" ? 3 : stage == "mercadinho" ? 4 : 2, -1);
     yield return TrCrowd(stage, 16); TrArrange(); yield return new WaitForSecondsRealtime(10f);
    }
    else {
     if (trCrowd != null) { StopCoroutine(trCrowd); trCrowd = null; }
     roomEra = -1; roomKeepInterior = false; crowdLayout = null;
     TrHud("devSetMarketEra", "[\"" + stage + "\"]"); yield return new WaitForSecondsRealtime(10f);
     yield return TrOpen(); yield return new WaitForSecondsRealtime(9f);
    }
    var (c, size) = TrShop();
    float z = Mathf.Clamp(size * .55f + 3.2f, 5f, 15f);
    yield return TrGlideShot(c + new Vector3(.9f, 0, .5f), z * 1.1f, c, z, 2.6f);
   }
  }

  IEnumerator TrRepor() {
   if (bridge.State?.era?.id != "mercadinho") { yield return TrCrowd("mercadinho", 14); TrArrange(); yield return new WaitForSecondsRealtime(4f); }
   var game = CheckoutRestockGame.Instance; if (!game) { Note("trailer: no restock game"); yield break; }
   lowShelves = true; yield return new WaitForSecondsRealtime(1.5f);
   CheckoutRestockGame.Show(); yield return new WaitForSecondsRealtime(1.5f);
   if (!game.IsOpen) { var id = bridge.State.restockSlots?.FirstOrDefault()?.shelfId; if (id != null) { CheckoutRestockGame.ShowFixture(id); yield return new WaitForSecondsRealtime(1.5f); } }
   if (!game.IsOpen) { Note("trailer: the restock game did not open"); lowShelves = false; yield break; }
   yield return TrShot(true, TrRestockPlay(game));
   lowShelves = false; CloseRestock(); yield return new WaitForSecondsRealtime(1f);
  }
  IEnumerator TrRestockPlay(CheckoutRestockGame game) {
   yield return Frames(.8f);
   // one fixture after another: the game opens the next one by itself after each round
   int budget = 30 * 11;
   while (budget > 0 && game.IsOpen) {
    bool done = false; var run = StartCoroutine(TrThen(game.QaPlayAll(), () => done = true));
    while (!done && budget > 0 && game.IsOpen) { budget--; yield return null; }
    if (!done) { StopCoroutine(run); break; }
    for (int i = 0; i < 75 && budget > 0; i++) { budget--; yield return null; }
   }
  }

  IEnumerator TrHiper() {
   TrTiers(5, 3);
   yield return TrCrowd("hipermercado", 44, ".lanes"); TrArrange();
   TrDecorate(new[] { "fruit-pyramid", "promo-stand", "can-pyramid", "plant-palm", "tasting-table", "watermelon-pile", "balloons", "monstera" },
    new[] { "flower-bed", "ice-cream-cart", "bench", "popcorn-cart" });
   yield return new WaitForSecondsRealtime(16f);   // the shoppers walk in
   var (c, size) = TrShop();
   var inside = CheckoutInterior.Active;
   // the building and the street from outside, then across the aisles, the checkouts, a sector counter
   yield return TrGlideShot(c + new Vector3(-6, 0, -8), 20f, c + new Vector3(0, 0, -2), 15f, 4.5f);
   yield return TrGlideShot(c + new Vector3(-size * .3f, 0, 0), 7.5f, c + new Vector3(size * .3f, 0, 1), 7f, 5f);
   if (inside) {
    var z = inside.CheckoutZone; var lanes = new Vector3(z.center.x, 0, z.center.y);
    yield return TrGlideShot(lanes + new Vector3(-1.5f, 0, 0), 5.2f, lanes + new Vector3(1.5f, 0, .5f), 4.6f, 4f);
    var sector = inside.items.Values.FirstOrDefault(i => i.root && i.id == "sector:acougue") ?? inside.items.Values.FirstOrDefault(i => i.root && i.type == "sector");
    if (sector != null) { var p = sector.root.position; p.y = 0; yield return TrGlideShot(p + new Vector3(.8f, 0, -.6f), 4.2f, p, 3.4f, 4f); }
   }
  }

  IEnumerator TrPadaria() {
   var hud = FindAnyObjectByType<CheckoutDesktopHUD>();
   void Route(string r) => CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"" + r + "\"}");
   // the bakery tray puzzle, played the way the deal solves it
   Route("kitchen:croissant-premium:0"); yield return new WaitForSecondsRealtime(3f);
   yield return TrShot(true, TrTrayPlay(hud));
   Route(""); yield return new WaitForSecondsRealtime(1f);
   // the other sectors' puzzles, a moment each
   foreach (var recipe in new[] { "sushi-especial", "sundae-chocolate", "vinho-da-casa" }) {
    Route("kitchen:" + recipe + ":0"); yield return new WaitForSecondsRealtime(3f);
    yield return TrShot(true, Hold(2.4f));
    Route(""); yield return new WaitForSecondsRealtime(1f);
   }
  }
  IEnumerator TrTrayPlay(CheckoutDesktopHUD hud) {
   yield return Frames(.8f);
   for (int i = 0; i < 14 && hud && hud.QaTrayPlace(); i++) yield return Frames(.45f);
   yield return Frames(1.8f);
  }
  static IEnumerator Hold(float seconds) { yield return Frames(seconds); }

  IEnumerator TrEvento() {
   var fx = FindAnyObjectByType<CheckoutEventVisuals>(); if (!fx) { Note("trailer: no event visuals"); yield break; }
   if (bridge.State?.era?.id != "hipermercado" && bridge.State?.era?.id != "rede") { yield return TrCrowd("hipermercado", 30); yield return new WaitForSecondsRealtime(10f); }
   foreach (var (id, zoom) in new[] { ("carro-de-som", 8f), ("feira-de-rua", 10f), ("nevasca", 14f) }) {
    fx.Preview(id); yield return new WaitForSecondsRealtime(id == "carro-de-som" ? 7f : 3f);
    var f = fx.FocusOf(id); f.y = 0;
    yield return TrGlideShot(f + new Vector3(.8f, 0, .4f), zoom * 1.08f, f, zoom, 3.6f);
    fx.Preview(""); yield return new WaitForSecondsRealtime(1.5f);
   }
  }

  IEnumerator TrRede() {
   TrTiers(5, 3);
   yield return TrCrowd("rede", 44, ".lanes.brand"); TrArrange();
   TrDecorate(new[] { "fruit-pyramid", "promo-stand", "can-pyramid", "plant-palm", "tasting-table", "wine-barrel", "balloons", "aquarium" },
    new[] { "flower-bed", "hotdog-cart", "bench", "fountain" });
   TrHud("orderFromDistributionCenter", "[[{\"productId\":172,\"boxes\":2},{\"productId\":175,\"boxes\":1}]]");
   yield return new WaitForSecondsRealtime(14f);
   var (c, _) = TrShop();
   var letters = GameObject.Find("S4 name");
   if (letters) { var l = letters.transform.position; l.y = 0; yield return TrGlideShot(l + new Vector3(0, 0, -6.5f), 8.5f, l + new Vector3(0, 0, -5.5f), 12f, 4f); }
   yield return TrGlideShot(new Vector3(11, 0, 40), 17f, new Vector3(11, 0, 45), 23f, 4.5f);
   // the whole map from above: the shop first, then everything
   yield return TrGlideShot(c, 13f, new Vector3(4, 0, 17), 30f, 6.5f);
  }
 }
}
