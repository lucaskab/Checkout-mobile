using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using TMPro;
using MarketDay;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using U = Checkout.CheckoutUiKit;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // "Modo edição": the designer builds the map of every shop stage by hand and saves it for the game.
    //  - Móveis: the shop furniture (game pieces + extra design pieces) on the snapping grid.
    //  - Objetos: any object of the map (trees, benches, lamps, buildings...) moved, turned, resized,
    //    hidden, duplicated, or added from a catalogue.
    //  - Pintar: roads, bike lanes, sidewalks, grass... and road markings on a 1 m grid.
    // Runs on a sandbox save with infinite money and everything bought; the stage buttons preview each shop
    // size. "Salvar" writes Assets/Resources/CheckoutMapDesign.json, which the game then follows.
    public partial class CheckoutMapEditor : MonoBehaviour
    {
        public static bool Open { get; private set; }
        public static int Stage { get; private set; }
        public static bool Warehouse { get; private set; }
        public static bool Dragging { get; private set; }

        enum Tool { Furniture, Objects, Paint }
        Tool tool = Tool.Furniture;

        CheckoutDesktopHost host; CheckoutBridge bridge; CheckoutMap map; MarketSimulation sim;
        CheckoutInterior Interior => map ? map.Interior : null;
        CheckoutDesignWorld World => map ? map.Design : null;

        // ui
        RectTransform root, hud, panelRows, rowA, rowB, paletteFace, paletteList, hiddenFace, hiddenList, backButton;
        GameObject paletteDim, hiddenDim;
        TextMeshProUGUI status, selectedName, unsavedLabel, paletteTitle;
        TMP_InputField search;
        readonly List<CheckoutDesktopButton> stageButtons = new List<CheckoutDesktopButton>();
        CheckoutDesktopButton warehouseButton, furnitureTool, objectsTool, paintTool, gridButton, infiniteButton, openButton;
        readonly List<CheckoutDesktopButton> gridSizes = new List<CheckoutDesktopButton>();
        float messageUntil; bool infiniteMoney = true, gameHud;

        // selection & dragging
        CheckoutInterior.Item piece;
        bool dragging, dragChanged; Vector3 dragOffset, dragStart; float dragStartRot; Vector2 downAt; Plane dragPlane;
        bool panning; Vector2 panLast;
        Material okMaterial, badMaterial, pickMaterial; Transform footprint;

        // paint
        int brushGround = 1, brushMark = 0, brushSize = 2; bool markTurned, painting;
        Transform brushPreview; Material previewMaterial;
        readonly List<CheckoutDesktopButton> groundButtons = new List<CheckoutDesktopButton>(), markButtons = new List<CheckoutDesktopButton>(), sizeButtons = new List<CheckoutDesktopButton>();
        CheckoutDesktopButton turnButton;
        static readonly string[] MarkLabels = { "", "Tracejado", "Faixa de pedestre", "Linha amarela", "Linha branca", "Seta ciclovia" };

        // history
        readonly List<string> undo = new List<string>();
        bool stageDirty; readonly HashSet<int> unsaved = new HashSet<int>();
        string confirm; float confirmUntil;
        readonly CultureInfo br = new CultureInfo("pt-BR");

        // ------------------------------------------------------------------ start
        public void Initialize(CheckoutDesktopHost owner)
        {
            host = owner; bridge = GetComponent<CheckoutBridge>(); sim = FindAnyObjectByType<MarketSimulation>();
            StartCoroutine(Boot());
        }

        IEnumerator Boot()
        {
            // Waits for the game (Node host) and the furnished map.
            float waited = 0;
            while ((bridge.State == null || !(map = GetComponent<CheckoutMap>()) || !map.Interior || !map.Interior.Ready || !map.Design) && waited < 60) { waited += Time.unscaledDeltaTime; yield return null; }
            if (bridge.State == null || !map || !map.Interior || !map.Interior.Ready) { Debug.LogError("CHECKOUT_EDITOR the game did not start: map editor unavailable."); yield break; }
            PrepareSandbox();
            // Let the host apply the unlocks before the first stage is built.
            float until = Time.unscaledTime + 1.5f;
            while (Time.unscaledTime < until) yield return null;
            BuildUi();
            Enter();
        }

        void Silent(string action, string args) { var id = host.Action(action, args, ""); if (host.Hud) host.Hud.Silent.Add(id); }

        // Everything bought and unlocked on the sandbox save, and money that never runs out.
        void PrepareSandbox()
        {
            var s = bridge.State;
            if (s.coins < 500_000_000) Silent("devAdjustCoins", "[1000000000]");
            if (s.diamonds < 500_000) Silent("devAdjustDiamonds", "[1000000]");
            if (s.level < 60) Silent("setMarketLevel", "[60]");
            foreach (var id in new[] { "fresh-wing", "service-wing", "stock-annex", "premium-hall", "grand-warehouse" })
                if (s.expansions == null || Array.IndexOf(s.expansions, id) < 0) { Silent("unlockMarketExpansion", "[\"" + id + "\",\"coins\"]"); Silent("devFinishMarketExpansion", "[]"); }
            for (int i = 0; i < 20; i++) Silent("unlockNextShelf", "[]");
            foreach (var id in new[] { CheckoutLanes.ExtraItem, CheckoutLanes.SelfItem })
                if (s.ownedItems == null || Array.IndexOf(s.ownedItems, id) < 0) Silent("purchaseShopItem", "[\"" + id + "\",\"coins\"]");
        }

        void Enter()
        {
            Open = true; Stage = 0; Warehouse = false;
            Interior.designMode = true; Interior.editing = true;
            GameCanvas(false);
            okMaterial = Flat(new Color(.36f, .78f, .35f, .38f)); badMaterial = Flat(new Color(.9f, .28f, .22f, .42f)); pickMaterial = Flat(new Color(1f, .78f, .2f, .35f));
            previewMaterial = Flat(new Color(1, 1, 1, .45f));
            footprint = Quad("Editor footprint", okMaterial).transform; footprint.gameObject.SetActive(false);
            brushPreview = Quad("Editor brush", previewMaterial).transform; brushPreview.gameObject.SetActive(false);
            SwitchStage(0, true);
            SetTool(Tool.Furniture);
            Say("Bem-vindo ao modo edição! Escolha a loja no topo e edite. Salve para o jogo usar este mapa.");
        }

        void OnDestroy()
        {
            if (Open) { Open = false; Dragging = false; }
            CheckoutGridOverlay.Hide();
        }

        // ------------------------------------------------------------------ stages
        DesignStage Capture() => new DesignStage { stage = Stage, interior = Interior.CaptureDesign(), objects = World.CaptureObjects(), paint = World.Paint.Save() };

        void SwitchStage(int stage, bool first = false)
        {
            if (!first && stageDirty) CheckoutMapDesign.Set(Stage, Capture());
            Select(null, null); undo.Clear(); stageDirty = false;
            World.RevertAll();
            Stage = Mathf.Clamp(stage, 0, CheckoutMapDesign.Stages - 1);
            map.Reapply();
            // Items are worked out on the untouched map of this stage, before the design moves anything.
            BuildIndex();
            var d = CheckoutMapDesign.For(Stage);
            World.ApplyStage(d, Stage);
            RefreshCloneItems();
            Interior.ResetTo(d);
            map.FurnitureChanged();
            FocusShop();
            RefreshTop();
            int source = CheckoutMapDesign.SourceStage(Stage);
            if (!first) Say(source == Stage ? CheckoutMapDesign.StageName(Stage) + ": mapa próprio desta loja." : source >= 0 ? CheckoutMapDesign.StageName(Stage) + ": usando o mapa da " + CheckoutMapDesign.StageName(source) + " (edite para criar um próprio)." : CheckoutMapDesign.StageName(Stage) + ": mapa original do jogo.");
        }

        void ToggleWarehouse()
        {
            if (stageDirty) CheckoutMapDesign.Set(Stage, Capture());
            Warehouse = !Warehouse; stageDirty = false;
            SwitchStage(Stage, true);
            Say(Warehouse ? "Com o armazém central (e a adega)." : "Sem o armazém central.");
        }

        void FocusShop()
        {
            var f = Interior.FloorRect;
            sim.Focus(new Vector3(f.center.x, 0, f.center.y), Mathf.Max(f.width, f.height) * .7f);
        }

        // Called before every change: remembers the state for "Desfazer".
        void BeginChange()
        {
            undo.Add(JsonUtility.ToJson(Capture()));
            if (undo.Count > 80) undo.RemoveAt(0);
            stageDirty = true; unsaved.Add(Stage); RefreshTop();
        }

        void Undo()
        {
            if (undo.Count == 0) { Say("Nada para desfazer.", true); return; }
            var d = JsonUtility.FromJson<DesignStage>(undo[undo.Count - 1]); undo.RemoveAt(undo.Count - 1);
            Select(null, null);
            World.ApplyStage(d, Stage); RefreshCloneItems(); Interior.ResetTo(d); map.FurnitureChanged(); CheckoutBlockPaths.Invalidate();
            stageDirty = true; unsaved.Add(Stage); RefreshTop();
            Say("Desfeito.");
        }

        void Save()
        {
            if (stageDirty) CheckoutMapDesign.Set(Stage, Capture());
            if (!CheckoutMapDesign.Save(out var error)) { Say("Não foi possível salvar: " + error, true); return; }
            stageDirty = false; unsaved.Clear(); RefreshTop();
            if (!Interior.Reachable(out var blocked)) Say("Salvo! Atenção: " + Name(blocked) + " ficou sem passagem para os clientes nesta loja.", true);
            else Say("Salvo! O jogo já usa este mapa (" + CheckoutMapDesign.SavePath.Replace('\\', '/').Split('/').Last() + ").");
        }

        void CopyForward()
        {
            if (Stage >= CheckoutMapDesign.Stages - 1) { Say("Esta já é a maior loja.", true); return; }
            if (!Confirm("copy", "Copiar este mapa para as lojas " + (Stage + 2) + " a 5? Clique de novo para confirmar.")) return;
            var d = Capture();
            for (int s = Stage + 1; s < CheckoutMapDesign.Stages; s++) { CheckoutMapDesign.Set(s, d); unsaved.Add(s); }
            CheckoutMapDesign.Set(Stage, d); unsaved.Add(Stage); stageDirty = false;
            RefreshTop();
            Say("Copiado para as lojas seguintes. Lembre de salvar.");
        }

        void ResetStage()
        {
            if (!Confirm("reset", "Voltar esta loja ao mapa original do jogo? Clique de novo para confirmar.")) return;
            BeginChange();
            World.ApplyStage(null); RefreshCloneItems(); Interior.ResetTo(null); map.FurnitureChanged(); CheckoutBlockPaths.Invalidate(); Select(null, null);
            Say("Loja voltou ao mapa original. Salve para confirmar (Desfazer volta atrás).");
        }

        bool Confirm(string key, string question)
        {
            if (confirm == key && Time.unscaledTime < confirmUntil) { confirm = null; return true; }
            confirm = key; confirmUntil = Time.unscaledTime + 4; Say(question, true); return false;
        }

        void Exit()
        {
            if (unsaved.Count > 0 || stageDirty) { if (!Confirm("exit", "Há mudanças não salvas. Clique em Sair de novo para sair sem salvar.")) return; }
            Open = false; sim.cameraLocked = false;
            CheckoutStartMenu.ReturnToMenu();
        }

        // ------------------------------------------------------------------ UI
        static Material Flat(Color c) { var m = new Material(Shader.Find("Sprites/Default")); m.color = c; m.renderQueue = 3100; return m; }
        static GameObject Quad(string name, Material m)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad); q.name = name; Destroy(q.GetComponent<Collider>());
            var r = q.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return q;
        }
        static DesktopButton Data(string label, string variant, bool enabled = true, string icon = "", bool active = false) =>
            new DesktopButton { label = label, variant = variant, enabled = enabled, active = active, icon = icon, action = "", args = "[]", route = "", after = "", ok = "", fail = "" };
        static RectTransform Node(Transform parent, string name) { var t = (RectTransform)new GameObject(name, typeof(RectTransform)).transform; t.SetParent(parent, false); return t; }
        static RectTransform Row(Transform parent, float spacing)
        {
            var t = Node(parent, "Row");
            var h = t.gameObject.AddComponent<HorizontalLayoutGroup>(); h.spacing = spacing; h.childAlignment = TextAnchor.MiddleCenter;
            h.childControlHeight = h.childControlWidth = true; h.childForceExpandHeight = false; h.childForceExpandWidth = false;
            return t;
        }
        static RectTransform Column(Transform parent, float spacing)
        {
            var t = Node(parent, "Column");
            var v = t.gameObject.AddComponent<VerticalLayoutGroup>(); v.spacing = spacing; v.childAlignment = TextAnchor.UpperCenter;
            v.childControlHeight = v.childControlWidth = true; v.childForceExpandHeight = false; v.childForceExpandWidth = true;
            return t;
        }
        CheckoutDesktopButton Btn(Transform parent, string label, string variant, Action onClick, float width, float height = 48, float font = 17, string icon = "")
        {
            var b = U.Button(parent, label, variant, onClick, height, font); if (width > 0) b.SetWidth(width);
            b.Apply(Data(label, variant, true, icon)); return b;
        }
        static TextMeshProUGUI Caption(Transform parent, string text, float width, string color = "BFD0E8", float size = 15)
        {
            var l = U.Label(parent, "Caption", K.Label, size, color); l.text = text;
            var le = l.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = width; le.preferredHeight = 26;
            return l;
        }

        void BuildUi()
        {
            root = U.Canvas(transform, "CheckoutMapEditor", 70);
            hud = Node(root, "Editor HUD"); U.Stretch(hud, Vector2.zero, Vector2.one);

            // Top bar: title, stages, save/exit.
            var top = U.Box(hud, "Top bar", "1D2B4F", 0, new Vector2(0, 1), new Vector2(1, 1)); top.rectTransform.offsetMin = new Vector2(0, -78); top.rectTransform.offsetMax = Vector2.zero; top.color = new Color(.11f, .17f, .31f, .97f);
            var gold = U.Box(top.transform, "Gold", "E0B040", 0, new Vector2(0, 0), new Vector2(1, 0)); gold.rectTransform.offsetMin = new Vector2(0, -4); gold.rectTransform.offsetMax = Vector2.zero;
            var title = U.Label(top.transform, "Title", K.Headline, 30, "E0B040", TextAlignmentOptions.Left); U.Stretch(title.rectTransform, new Vector2(0, 0), new Vector2(0, 1), new Vector2(24, 0), new Vector2(260, 0)); title.text = "MODO EDIÇÃO";
            unsavedLabel = U.Label(top.transform, "Unsaved", K.Label, 15, "FFB199", TextAlignmentOptions.Left); U.Stretch(unsavedLabel.rectTransform, new Vector2(0, 0), new Vector2(0, .4f), new Vector2(26, 2), new Vector2(300, 0));
            var stages = Row(top.transform, 8); U.At(stages, new Vector2(.5f, .5f), new Vector2(760, 56), new Vector2(-40, 0));
            for (int i = 0; i < CheckoutMapDesign.Stages; i++) { int s = i; stageButtons.Add(Btn(stages, CheckoutMapDesign.StageName(i), "secondary", () => { if (s != Stage) SwitchStage(s); }, 118, 50, 18)); }
            warehouseButton = Btn(stages, "Armazém", "secondary", ToggleWarehouse, 130, 50, 17, "Icons/warehouse");
            var actions = Row(top.transform, 8); U.At(actions, new Vector2(1, .5f), new Vector2(420, 56), new Vector2(-222, 0));
            Btn(actions, "Desfazer", "secondary", Undo, 120, 50, 17);
            Btn(actions, "Salvar", "success", Save, 130, 50, 19, "Icons/success");
            Btn(actions, "Sair", "danger", Exit, 110, 50, 18);

            // Status line under the top bar.
            var statusBox = U.Shape(hud, "Status", "FFF7EC", 18, new Vector2(.5f, 1), new Vector2(1060, 40), new Vector2(0, -104));
            status = U.Label(statusBox.transform, "Text", K.Body, 17, "4A3624"); U.Stretch(status.rectTransform, Vector2.zero, Vector2.one, new Vector2(14, 0), new Vector2(-14, 0));

            // Left column: tools, grid, sandbox.
            var leftBack = U.Shape(hud, "Tools", "1D2B4F", 22, new Vector2(0, 1), new Vector2(210, 780), new Vector2(121, -500)); leftBack.color = new Color(.11f, .17f, .31f, .93f);
            var left = Column(leftBack.transform, 8); U.Stretch(left, Vector2.zero, Vector2.one, new Vector2(12, 12), new Vector2(-12, -12));
            Caption(left, "FERRAMENTA", 180, "E0B040");
            furnitureTool = Btn(left, "Móveis", "secondary", () => SetTool(Tool.Furniture), 0, 52, 19, "Icons/shelf");
            objectsTool = Btn(left, "Objetos", "secondary", () => SetTool(Tool.Objects), 0, 52, 19, "Icons/garden");
            paintTool = Btn(left, "Pintar", "secondary", () => SetTool(Tool.Paint), 0, 52, 19, "Icons/construction");
            Caption(left, "GRADE", 180, "E0B040");
            gridButton = Btn(left, "Grade: ligada", "secondary", ToggleGrid, 0, 44, 16);
            var sizes = Row(left, 6); sizes.gameObject.AddComponent<LayoutElement>().preferredHeight = 44;
            foreach (var g in new[] { .25f, .5f, 1f }) { float v = g; gridSizes.Add(Btn(sizes, GridLabel(g), "secondary", () => { CheckoutInterior.GridSize = v; RefreshLeft(); Say("Quadrados de " + GridLabel(v) + "."); }, 0, 40, 12)); }
            Caption(left, "LOJA", 180, "E0B040");
            Btn(left, "Copiar p/ próximas", "secondary", CopyForward, 0, 44, 15);
            Btn(left, "Mapa original", "secondary", ResetStage, 0, 44, 15);
            Caption(left, "DINHEIRO E JOGO", 180, "E0B040");
            infiniteButton = Btn(left, "Dinheiro infinito", "secondary", () => { infiniteMoney = !infiniteMoney; RefreshLeft(); }, 0, 44, 15, "Icons/coin");
            var money = Row(left, 6); money.gameObject.AddComponent<LayoutElement>().preferredHeight = 44;
            Btn(money, "+1 mi", "success", () => Silent("devAdjustCoins", "[1000000]"), 0, 40, 15);
            Btn(money, "-1 mi", "danger", () => Silent("devAdjustCoins", "[-1000000]"), 0, 40, 15);
            openButton = Btn(left, "Loja aberta", "secondary", ToggleOpen, 0, 44, 15, "Icons/market");
            Btn(left, "Telas do jogo", "secondary", () => ShowGameHud(true), 0, 44, 15, "Icons/toolbox");

            // Bottom panel: what the tool can do with the selection.
            var bottom = U.Shape(hud, "Actions", "1D2B4F", 24, new Vector2(.5f, 0), new Vector2(1340, 178), new Vector2(112, 100)); bottom.color = new Color(.11f, .17f, .31f, .93f);
            panelRows = Column(bottom.transform, 8); U.Stretch(panelRows, Vector2.zero, Vector2.one, new Vector2(14, 10), new Vector2(-14, -8));
            selectedName = U.Label(panelRows, "Selected", K.Label, 18, "FFFFFF", TextAlignmentOptions.Left); selectedName.gameObject.AddComponent<LayoutElement>().preferredHeight = 32;
            rowA = Row(panelRows, 5); rowA.gameObject.AddComponent<LayoutElement>().preferredHeight = 48;
            rowB = Row(panelRows, 5); rowB.gameObject.AddComponent<LayoutElement>().preferredHeight = 48;

            BuildPalette();
            BuildHiddenList();

            // Shown while the game's own screens are open.
            var back = Btn(root, "Voltar à edição", "coin", () => ShowGameHud(false), 260, 60, 20, "Icons/hammer");
            backButton = (RectTransform)back.transform; U.At(backButton, new Vector2(0, 0), new Vector2(260, 60), new Vector2(150, 240)); backButton.gameObject.SetActive(false);
        }

        void ClearRows() { foreach (Transform t in rowA) Destroy(t.gameObject); foreach (Transform t in rowB) Destroy(t.gameObject); groundButtons.Clear(); markButtons.Clear(); sizeButtons.Clear(); }

        void BuildToolRows()
        {
            ClearRows();
            if (tool == Tool.Furniture)
            {
                Btn(rowA, "Adicionar móvel", "coin", () => OpenPalette(true), 200, 46, 17, "Icons/cart");
                Btn(rowA, "Girar -90°", "primary", () => TurnPiece(-90), 120); Btn(rowA, "-15°", "primary", () => TurnPiece(-15), 70);
                Btn(rowA, "+15°", "primary", () => TurnPiece(15), 70); Btn(rowA, "Girar +90°", "primary", () => TurnPiece(90), 120);
                Btn(rowA, "Menor", "secondary", () => ScalePiece(-.1f), 100); Btn(rowA, "Maior", "secondary", () => ScalePiece(.1f), 100);
                Btn(rowB, "Duplicar", "success", DuplicatePiece, 140); Btn(rowB, "Remover", "danger", RemovePiece, 130);
                Btn(rowB, "Tamanho normal", "secondary", () => ScalePiece(0, true), 170);
                Caption(rowB, "Arraste para mover • Q/E gira • +/- tamanho • Ctrl+D duplica • Del remove • G grade", 620, "BFD0E8", 14);
            }
            else if (tool == Tool.Objects)
            {
                Btn(rowA, "Adicionar objeto", "coin", () => OpenPalette(false), 200, 46, 17, "Icons/cart");
                partButton = Btn(rowA, partMode ? "Só a parte" : "Item inteiro", "secondary", TogglePartMode, 150); partButton.Apply(Data(partMode ? "Só a parte" : "Item inteiro", "secondary", true, "", partMode));
                Btn(rowA, "Girar -15°", "primary", () => TurnObject(-15), 120); Btn(rowA, "+15°", "primary", () => TurnObject(15), 70);
                Btn(rowA, "90°", "primary", () => TurnObject(90), 70);
                Btn(rowA, "Menor", "secondary", () => ScaleObject(1 / 1.1f), 90); Btn(rowA, "Maior", "secondary", () => ScaleObject(1.1f), 90);
                Btn(rowA, "Subir", "secondary", () => LiftObject(.05f), 86); Btn(rowA, "Descer", "secondary", () => LiftObject(-.05f), 90);
                Btn(rowB, "Duplicar", "success", DuplicateObject, 130); Btn(rowB, "Ocultar / remover", "danger", RemoveObject, 200);
                Btn(rowB, "Voltar ao original", "secondary", ResetObject, 200); Btn(rowB, "Ocultos", "secondary", () => OpenHidden(true), 120);
                Caption(rowB, "Shift+clique junta itens • Shift+arrastar seleciona vários • Q/E gira • PgUp/PgDn altura", 560, "BFD0E8", 14);
            }
            else
            {
                for (int g = 1; g < CheckoutPaintLayer.GroundNames.Length; g++) { int k = g; groundButtons.Add(Btn(rowA, CheckoutPaintLayer.GroundNames[g], "secondary", () => { brushGround = k; brushMark = 0; RefreshPaint(); }, 104, 46, 15)); }
                groundButtons.Add(Btn(rowA, "Apagar chão", "danger", () => { brushGround = 0; brushMark = 0; RefreshPaint(); }, 124, 46, 15));
                foreach (var n in new[] { 1, 2, 3, 5, 8 }) { int k = n; sizeButtons.Add(Btn(rowA, n + "x" + n, "secondary", () => { brushSize = k; RefreshPaint(); }, 52, 46, 14)); }
                for (int m = 1; m < MarkLabels.Length; m++) { int k = m; markButtons.Add(Btn(rowB, MarkLabels[m], "secondary", () => { brushMark = k; brushGround = -1; RefreshPaint(); }, m == 2 ? 176 : 136, 46, 15)); }
                markButtons.Add(Btn(rowB, "Apagar marcas", "danger", () => { brushMark = -2; brushGround = -1; RefreshPaint(); }, 146, 46, 15));
                turnButton = Btn(rowB, "Girar marca (R)", "primary", () => { markTurned = !markTurned; RefreshPaint(); }, 166, 46, 15);
                RefreshPaint();
            }
        }

        void RefreshPaint()
        {
            for (int i = 0; i < groundButtons.Count; i++)
            {
                int kind = i + 1 < CheckoutPaintLayer.GroundNames.Length ? i + 1 : 0;
                bool on = brushMark == 0 && brushGround == kind;
                groundButtons[i].Apply(Data(i + 1 < CheckoutPaintLayer.GroundNames.Length ? CheckoutPaintLayer.GroundNames[i + 1] : "Apagar chão", kind == 0 ? "danger" : "secondary", true, "", on));
            }
            for (int i = 0; i < markButtons.Count; i++)
            {
                int kind = i + 1 < MarkLabels.Length ? i + 1 : -2;
                markButtons[i].Apply(Data(kind > 0 ? MarkLabels[kind] : "Apagar marcas", kind > 0 ? "secondary" : "danger", true, "", brushMark == kind));
            }
            if (turnButton) turnButton.Apply(Data(markTurned ? "Marca girada (R)" : "Girar marca (R)", "primary", true, "", markTurned));
            int[] sizes = { 1, 2, 3, 5, 8 };
            for (int i = 0; i < sizeButtons.Count; i++) sizeButtons[i].Apply(Data(sizes[i] + "x" + sizes[i], "secondary", true, "", brushSize == sizes[i]));
            selectedName.text = "Pincel: " + BrushName() + "  •  " + brushSize + "x" + brushSize + " m";
        }

        string BrushName()
        {
            if (brushMark > 0) return MarkLabels[brushMark] + (markTurned && brushMark < 5 ? " (girada)" : "");
            if (brushMark == -2) return "apagar marcas";
            return brushGround > 0 ? CheckoutPaintLayer.GroundNames[brushGround] : "apagar chão e marcas";
        }

        // The layer kind painted for the chosen brush (markings come in two orientations).
        int MarkKind() => brushMark <= 0 ? brushMark : brushMark == 5 ? 9 : (brushMark - 1) * 2 + 1 + (markTurned ? 1 : 0);

        void SetTool(Tool next)
        {
            EndDrag(); Select(null, null); tool = next;
            furnitureTool.Apply(Data("Móveis", "secondary", true, "Icons/shelf", tool == Tool.Furniture));
            objectsTool.Apply(Data("Objetos", "secondary", true, "Icons/garden", tool == Tool.Objects));
            paintTool.Apply(Data("Pintar", "secondary", true, "Icons/construction", tool == Tool.Paint));
            BuildToolRows();
            if (tool == Tool.Objects) UpdateObjectLabel();
            sim.cameraLocked = tool == Tool.Paint;
            if (tool == Tool.Furniture) { FocusShop(); Say("Móveis: clique numa peça da loja e arraste. Elas encaixam nos quadrados, nas paredes e umas nas outras."); }
            else if (tool == Tool.Objects) Say("Objetos: clique em qualquer coisa do mapa (árvores, bancos, postes, prédios...) e arraste.");
            else Say("Pintar: clique e arraste no chão. Botão direito (ou do meio) arrasta a câmera; roda do mouse dá zoom.");
            brushPreview.gameObject.SetActive(false);
            RefreshLeft();
        }

        void RefreshTop()
        {
            if (!root) return;
            for (int i = 0; i < stageButtons.Count; i++)
            {
                bool own = CheckoutMapDesign.Explicit(i) || (i == Stage && stageDirty);
                stageButtons[i].Apply(Data(CheckoutMapDesign.StageName(i) + (unsaved.Contains(i) ? " *" : ""), own ? "primary" : "secondary", true, "", i == Stage));
            }
            warehouseButton.Apply(Data("Armazém", "secondary", true, "Icons/warehouse", Warehouse));
            unsavedLabel.text = unsaved.Count > 0 ? "não salvo" : "";
        }

        void RefreshLeft()
        {
            gridButton.Apply(Data(CheckoutInterior.GridOn ? "Grade: ligada" : "Grade: desligada", "secondary", true, "", CheckoutInterior.GridOn));
            float[] sizes = { .25f, .5f, 1f };
            for (int i = 0; i < gridSizes.Count; i++) gridSizes[i].Apply(Data(GridLabel(sizes[i]), "secondary", CheckoutInterior.GridOn, "", Mathf.Approximately(CheckoutInterior.GridSize, sizes[i])));
            infiniteButton.Apply(Data("Dinheiro infinito", "secondary", true, "Icons/coin", infiniteMoney));
            bool open = bridge.State != null && bridge.State.isOpen;
            openButton.Apply(Data(open ? "Loja aberta" : "Loja fechada", "secondary", true, "Icons/market", open));
        }

        static string GridLabel(float g) => g >= 1 ? "1m" : Mathf.RoundToInt(g * 100) + "cm";

        void ToggleGrid() { CheckoutInterior.GridOn = !CheckoutInterior.GridOn; RefreshLeft(); Say(CheckoutInterior.GridOn ? "Grade ligada: tudo encaixa nos quadrados." : "Grade desligada: movimento livre (móveis ainda encostam nas paredes e uns nos outros)."); }
        void ToggleOpen() { bool open = bridge.State != null && bridge.State.isOpen; Silent("setMarketOpen", open ? "[false]" : "[true]"); Say(open ? "Loja fechada." : "Loja aberta: clientes entram (param enquanto você edita)."); }

        // The game's own HUD (pages, DEV cheats) over the map, with a button back to the editor.
        void ShowGameHud(bool show)
        {
            gameHud = show; EndDrag(); sim.cameraLocked = !show && tool == Tool.Paint;
            hud.gameObject.SetActive(!show); backButton.gameObject.SetActive(show);
            GameCanvas(show);
            if (show) { Select(null, null); host.Route("!dev"); } else host.Route("");
        }

        void GameCanvas(bool show)
        {
            var own = host && host.Hud ? host.Hud.transform.Find("CheckoutDesktopHUD") : null;
            var canvas = own ? own.GetComponent<Canvas>() : null;
            if (canvas) canvas.enabled = show;
        }

        void Say(string text, bool warn = false)
        {
            if (!status) return;
            status.text = text; status.color = K.C(warn ? "C0401F" : "4A3624"); messageUntil = Time.unscaledTime + (warn ? 5f : 7f);
        }

        string Help => tool == Tool.Furniture ? "Móveis • arraste para mover • Q/E gira • +/- tamanho • Ctrl+Z desfaz • Ctrl+S salva"
            : tool == Tool.Objects ? "Objetos • clique e arraste qualquer coisa do mapa • botão direito move a câmera • Ctrl+Z desfaz"
            : "Pintar • clique e arraste no chão • R gira a marcação • botão direito move a câmera • Ctrl+Z desfaz";

        // ------------------------------------------------------------------ palette (add furniture / objects)
        void BuildPalette()
        {
            paletteFace = U.Window(root, out paletteDim);
            paletteTitle = U.Label(paletteFace, "Title", K.Headline, 34, "4A3624", TextAlignmentOptions.Left);
            U.Stretch(paletteTitle.rectTransform, new Vector2(0, 1), new Vector2(.6f, 1), new Vector2(34, -76), new Vector2(0, -14));
            var close = U.Button(paletteFace, "Fechar", "secondary", () => paletteDim.SetActive(false), 54, 20);
            U.At((RectTransform)close.transform, new Vector2(1, 1), new Vector2(150, 54), new Vector2(-104, -46));
            search = MakeInput(paletteFace, "Buscar…"); U.At((RectTransform)search.transform, new Vector2(.5f, 1), new Vector2(520, 50), new Vector2(120, -46));
            search.onValueChanged.AddListener(_ => FillPalette());
            var view = Node(paletteFace, "Viewport"); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(24, 18), new Vector2(-24, -96));
            view.gameObject.AddComponent<RectMask2D>(); var hit = view.gameObject.AddComponent<Image>(); hit.color = new Color(1, 1, 1, 0);
            paletteList = Node(view, "Grid"); paletteList.anchorMin = new Vector2(0, 1); paletteList.anchorMax = new Vector2(1, 1); paletteList.pivot = new Vector2(.5f, 1); paletteList.offsetMin = paletteList.offsetMax = Vector2.zero;
            var g = paletteList.gameObject.AddComponent<GridLayoutGroup>(); g.cellSize = new Vector2(262, 64); g.spacing = new Vector2(10, 10); g.childAlignment = TextAnchor.UpperCenter; g.padding = new RectOffset(4, 4, 6, 12);
            paletteList.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = paletteList; scroll.horizontal = false; scroll.viewport = view; scroll.scrollSensitivity = 40; scroll.movementType = ScrollRect.MovementType.Clamped;
            paletteDim.SetActive(false);
        }

        static TMP_InputField MakeInput(RectTransform parent, string placeholder)
        {
            var box = U.Box(parent, "Search", "FFFFFF", 14, Vector2.zero, Vector2.one);
            var area = Node(box.transform, "Text Area"); area.gameObject.AddComponent<RectMask2D>(); U.Stretch(area, Vector2.zero, Vector2.one, new Vector2(14, 4), new Vector2(-14, -4));
            var ph = U.Label(area, "Placeholder", K.Body, 20, "A89880", TextAlignmentOptions.Left); U.Stretch(ph.rectTransform, Vector2.zero, Vector2.one); ph.text = placeholder;
            var text = U.Label(area, "Text", K.Body, 20, "4A3624", TextAlignmentOptions.Left); U.Stretch(text.rectTransform, Vector2.zero, Vector2.one); text.overflowMode = TextOverflowModes.Overflow;
            var input = box.gameObject.AddComponent<TMP_InputField>();
            input.textViewport = area; input.textComponent = text; input.placeholder = ph; input.fontAsset = K.Body; input.pointSize = 20;
            return input;
        }

        bool paletteFurniture;

        void OpenPalette(bool furniture)
        {
            paletteFurniture = furniture;
            paletteTitle.text = furniture ? "Adicionar móvel na loja" : "Adicionar objeto no mapa";
            search.SetTextWithoutNotify("");
            paletteDim.SetActive(true); FillPalette();
        }

        void FillPalette()
        {
            foreach (Transform t in paletteList) Destroy(t.gameObject);
            string q = (search.text ?? "").Trim().ToLowerInvariant();
            IEnumerable<(string label, string source, string icon)> entries = paletteFurniture
                ? Interior.Templates.OrderBy(n => n).Select(n => (Pretty(n), "kit:" + n, "Decor/" + n))
                : Catalogue();
            foreach (var e in entries)
            {
                if (q.Length > 0 && !e.label.ToLowerInvariant().Contains(q) && !e.source.ToLowerInvariant().Contains(q)) continue;
                var entry = e;
                var b = U.Button(paletteList, e.label, "secondary", () => AddFromPalette(entry.source), 60, 16);
                b.Apply(Data(e.label, "secondary", true, K.Icon(e.icon) ? e.icon : ""));
            }
        }

        static string Pretty(string name)
        {
            var n = Regex.Replace(name, @"[_\-]+", " ");
            n = Regex.Replace(n, @"\s*\(\d+\)$", "");
            n = Regex.Replace(n, @"\s*\[[^\]]*\]", "").Trim();
            return n.Length > 0 ? char.ToUpperInvariant(n[0]) + n.Substring(1) : name;
        }

        static string BaseName(string name) => Regex.Replace(name, @"(\s*\(\d+\)|[\s_\-]*\d+)$", "").Trim();

        // Kit templates plus one of each item found on the map (benches, trees, lamps, gardens...), whole.
        IEnumerable<(string label, string source, string icon)> Catalogue()
        {
            var list = Interior.Templates.OrderBy(n => n).Select(n => (Pretty(n), "kit:" + n, "Decor/" + n)).ToList();
            list.AddRange(ItemCatalogue());
            return list;
        }

        Vector3 ScreenCenterOn(float y)
        {
            var ray = sim.view.ScreenPointToRay(new Vector3(Screen.width * .5f, Screen.height * .5f));
            var plane = new Plane(Vector3.up, new Vector3(0, y, 0));
            return plane.Raycast(ray, out var d) ? ray.GetPoint(d) : new Vector3(0, y, 0);
        }

        void AddFromPalette(string source)
        {
            paletteDim.SetActive(false);
            if (paletteFurniture)
            {
                var r = Interior.FloorRect; var at = ScreenCenterOn(CheckoutInterior.Floor);
                at.x = Mathf.Clamp(at.x, r.xMin + 1, r.xMax - 1); at.z = Mathf.Clamp(at.z, r.yMin + 1.5f, r.yMax - 1);
                BeginChange();
                var it = Interior.AddDesign(source.Substring(4), at);
                if (it == null) { undo.RemoveAt(undo.Count - 1); Say("Não há espaço livre para esse móvel agora.", true); return; }
                map.FurnitureChanged(); Select(it, null); Say(Pretty(source.Substring(4)) + " adicionado. Arraste para ajustar.");
                return;
            }
            if (source.StartsWith("item:")) { AddItemFromCatalogue(int.Parse(source.Substring(5))); return; }
            var src = World.Source(source);
            if (!src) { Say("Objeto não encontrado.", true); return; }
            var ground = ScreenCenterOn(CheckoutInterior.Ground);
            var b = BoundsOf(src); float lift = src.position.y - b.min.y;
            BeginChange();
            var o = new DesignObject { source = source, position = new Vector3(Snap1(ground.x), CheckoutInterior.Ground + Mathf.Max(0, lift), Snap1(ground.z)), euler = new Vector3(src.eulerAngles.x, src.eulerAngles.y, src.eulerAngles.z), scale = src.lossyScale };
            o.group = "g" + Guid.NewGuid().ToString("N").Substring(0, 8);
            var t = World.AddClone(o);
            if (!t) { Say("Não foi possível copiar esse objeto.", true); return; }
            RefreshCloneItems(); Select(null, t); MarkNavigation(); Say("Objeto adicionado no centro da tela. Arraste para o lugar.");
        }

        // ------------------------------------------------------------------ hidden objects
        void BuildHiddenList()
        {
            hiddenFace = U.Window(root, out hiddenDim);
            var head = U.Label(hiddenFace, "Title", K.Headline, 34, "4A3624", TextAlignmentOptions.Left);
            U.Stretch(head.rectTransform, new Vector2(0, 1), new Vector2(.7f, 1), new Vector2(34, -76), new Vector2(0, -14)); head.text = "Objetos ocultos nesta loja";
            var close = U.Button(hiddenFace, "Fechar", "secondary", () => hiddenDim.SetActive(false), 54, 20);
            U.At((RectTransform)close.transform, new Vector2(1, 1), new Vector2(150, 54), new Vector2(-104, -46));
            var view = Node(hiddenFace, "Viewport"); U.Stretch(view, Vector2.zero, Vector2.one, new Vector2(24, 18), new Vector2(-24, -96));
            view.gameObject.AddComponent<RectMask2D>(); view.gameObject.AddComponent<Image>().color = new Color(1, 1, 1, 0);
            hiddenList = Column(view, 8); hiddenList.anchorMin = new Vector2(0, 1); hiddenList.anchorMax = new Vector2(1, 1); hiddenList.pivot = new Vector2(.5f, 1); hiddenList.offsetMin = hiddenList.offsetMax = Vector2.zero;
            hiddenList.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var scroll = view.gameObject.AddComponent<ScrollRect>(); scroll.content = hiddenList; scroll.horizontal = false; scroll.viewport = view; scroll.scrollSensitivity = 40; scroll.movementType = ScrollRect.MovementType.Clamped;
            hiddenDim.SetActive(false);
        }

        void OpenHidden(bool open)
        {
            hiddenDim.SetActive(open); if (!open) return;
            foreach (Transform t in hiddenList) Destroy(t.gameObject);
            var hidden = World.Overrides.Where(o => o.hidden).OrderBy(o => o.path).ToList();
            if (hidden.Count == 0) { var l = Caption(hiddenList, "Nenhum objeto oculto nesta loja.", 600, "8A7560", 20); return; }
            foreach (var o in hidden)
            {
                var path = o.path;
                var row = Row(hiddenList, 10); row.gameObject.AddComponent<LayoutElement>().preferredHeight = 54;
                var label = U.Label(row, "Name", K.Body, 18, "4A3624", TextAlignmentOptions.Left); label.text = path.Split('/').Last() + "   <size=14><color=#8A7560>" + path + "</color></size>";
                var le = label.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = 1000; le.preferredHeight = 50;
                Btn(row, "Mostrar", "success", () => { BeginChange(); var data = World.OverrideOf(path); if (data != null) { var t = CheckoutMapDesign.Find(path); World.RemoveOverride(path); if (t) { var keep = new DesignObject { path = path, position = data.position, euler = data.euler, scale = data.scale }; if (Moved(t, keep)) World.SetOverride(keep); } } OpenHidden(true); Say("Objeto visível de novo."); }, 150, 48, 17);
            }
        }

        bool Moved(Transform t, DesignObject o)
        {
            World.Original(t, out var p, out var r, out var s);
            return (p - o.position).sqrMagnitude > 1e-6f || Quaternion.Angle(r, Quaternion.Euler(o.euler)) > .05f || (s - o.scale).sqrMagnitude > 1e-6f;
        }

        // ------------------------------------------------------------------ selection
        string Name(CheckoutInterior.Item it)
        {
            if (it == null) return "";
            if (it.design) return Pretty(it.template) + " (do mapa)";
            if (it.type == "checkout") return it.id == "checkout:main" ? "Caixa" : "Caixa 2";
            if (it.type == "kiosk") return "Autoatendimento";
            if (it.type == "sector") { var s = bridge.State?.sectors?.FirstOrDefault(x => "sector:" + x.id == it.id); return s != null ? s.name : "Setor"; }
            if (it.type == "shelf") { var s = bridge.State?.shelves?.FirstOrDefault(x => "shelf:" + x.id == it.id); return s != null ? s.name : "Prateleira"; }
            return Pretty(it.type);
        }

        // Furniture piece, or (with `o`) the map item that object belongs to.
        void Select(CheckoutInterior.Item it, Transform o, Transform leaf = null)
        {
            piece = it; selection.Clear();
            if (o) selection.Add(ItemOf(o, false));
            if (!selectedName) return;
            if (tool == Tool.Paint) { RefreshPaint(); return; }
            if (tool == Tool.Objects) { UpdateObjectLabel(); ShowSelection(); return; }
            if (piece != null) selectedName.text = Name(piece) + "   <size=15><color=#BFD0E8>" + (piece.design ? "peça extra do mapa" : "peça do jogo") + " • tamanho " + (piece.scale * 100).ToString("0") + "%</color></size>";
            else selectedName.text = "Nenhum móvel selecionado";
            ShowSelection();
        }

        static Bounds BoundsOf(Transform t)
        {
            var rs = t.GetComponentsInChildren<Renderer>(true).Where(r => !(r is ParticleSystemRenderer)).ToArray();
            if (rs.Length == 0) return new Bounds(t.position, Vector3.one * .5f);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return b;
        }

        void ShowSelection()
        {
            if (!footprint) return;
            if (piece != null && piece.root)
            {
                float y = piece.outside ? CheckoutInterior.Ground : CheckoutInterior.Floor;
                var position = piece.root.position; position.y = y;
                bool ok = Interior.Fits(piece, position, piece.rot, out _);
                var f = Interior.FootprintAt(piece, position, piece.rot);
                footprint.gameObject.SetActive(true); footprint.GetComponent<Renderer>().sharedMaterial = ok ? okMaterial : badMaterial;
                footprint.SetPositionAndRotation(new Vector3(f.c.x, y + .05f, f.c.y), Quaternion.Euler(90, piece.rot, 0));
                footprint.localScale = new Vector3(f.hx * 2 + .1f, f.hz * 2 + .1f, 1);
            }
            else footprint.gameObject.SetActive(false);
            if (selection.Count > 0) ShowObjectSelection(); else HideObjectSelection();
        }

        // ------------------------------------------------------------------ furniture actions
        void TurnPiece(float delta)
        {
            if (piece == null) { Say("Selecione um móvel primeiro.", true); return; }
            float next = Mathf.Repeat(piece.rot + delta, 360);
            var from = piece.root.position; var to = Interior.Snap(piece, from, next, from);
            if (!Interior.Fits(piece, to, next, out var why)) { Say(why + ": não dá para girar aqui.", true); return; }
            BeginChange(); piece.rot = next; Interior.MoveTo(piece, to); map.FurnitureChanged(); Select(piece, null);
        }

        void ScalePiece(float delta, bool reset = false)
        {
            if (piece == null) { Say("Selecione um móvel primeiro.", true); return; }
            float before = piece.scale, next = reset ? 1 : Mathf.Clamp(Mathf.Round((piece.scale + delta) * 100) / 100, .4f, 2.5f);
            if (Mathf.Approximately(before, next)) return;
            var from = piece.root.position;
            piece.scale = next;
            var to = Interior.Snap(piece, from, piece.rot, from);
            if (!Interior.Fits(piece, to, piece.rot, out var why)) { piece.scale = before; Interior.Place(piece); Say(why + ": não cabe nesse tamanho aqui.", true); return; }
            piece.scale = before; BeginChange(); piece.scale = next; Interior.MoveTo(piece, to); map.FurnitureChanged(); Select(piece, null);
        }

        void DuplicatePiece()
        {
            if (piece == null) { Say("Selecione um móvel primeiro.", true); return; }
            var right = piece.root.right * (Interior.FootprintOf(piece).hx * 2 + .05f);
            BeginChange();
            var copy = Interior.AddDesign(piece.template, piece.root.position + right, piece.outside, piece.rot, piece.scale);
            if (copy == null) { undo.RemoveAt(undo.Count - 1); Say("Sem espaço livre para a cópia.", true); return; }
            map.FurnitureChanged(); Select(copy, null);
            Say(piece != null && !piece.design ? "Cópia criada como decoração do mapa (não é uma prateleira do jogo)." : "Cópia criada.");
        }

        void RemovePiece()
        {
            if (piece == null) { Say("Selecione um móvel primeiro.", true); return; }
            if (!piece.design) { Say("Este móvel faz parte do jogo: dá para mover e girar, mas não remover.", true); return; }
            BeginChange(); Interior.RemoveDecor(piece); Select(null, null); map.FurnitureChanged(); Say("Removido.");
        }

        // ------------------------------------------------------------------ object actions
        void Record(Transform t)
        {
            if (!t) return;
            if (World.IsClone(t, out _)) { World.UpdateClone(t); return; }
            var path = CheckoutMapDesign.PathOf(t);
            var before = World.OverrideOf(path);
            var o = new DesignObject { path = path, position = t.position, euler = t.eulerAngles, scale = t.localScale, hidden = before != null && before.hidden };
            if (!o.hidden && !Moved(t, o)) { World.RemoveOverride(path); return; }
            World.SetOverride(o);
        }

        // ------------------------------------------------------------------ picking objects
        static readonly string[] SkipRoots = { "Market Interior", "CheckoutBridge", "Market Staff", "Market Interface", "Map Design Paint", "Map Grid", "Build footprint", "Build spot", "Editor footprint", "Editor brush", "Market Terrain Grid", "Map Design Staging", "Isometric Camera" };
        static readonly string[] SkipNames = { "Staff Kit", "Interior Kit", "Plaza life" };
        static readonly string[] SkipPrefixes = { "Customer_", "Worker_", "Employee_", "Anim_", "Status ", "Open ", "StockWorker_" };
        readonly Dictionary<Mesh, (Vector3[] v, int[] t)> meshCache = new Dictionary<Mesh, (Vector3[], int[])>();

        static bool Skipped(Transform t)
        {
            for (var p = t; p; p = p.parent)
            {
                if (!p.parent && Array.IndexOf(SkipRoots, p.name) >= 0) return true;
                if (Array.IndexOf(SkipNames, p.name) >= 0) return true;
                foreach (var prefix in SkipPrefixes) if (p.name.StartsWith(prefix)) return true;
            }
            return false;
        }

        // Vertices and triangles of any mesh: readable meshes directly, the others through the read-only mesh
        // data (import settings keep most scene models non-readable to save memory).
        static (Vector3[] v, int[] t) ReadMesh(Mesh mesh)
        {
            try
            {
                if (mesh.isReadable) return (mesh.vertices, mesh.triangles);
                using (var all = Mesh.AcquireReadOnlyMeshData(mesh))
                {
                    var d = all[0];
                    var verts = new Unity.Collections.NativeArray<Vector3>(d.vertexCount, Unity.Collections.Allocator.Temp);
                    d.GetVertices(verts); var v = verts.ToArray(); verts.Dispose();
                    var tris = new List<int>();
                    for (int s = 0; s < d.subMeshCount; s++)
                    {
                        var sub = d.GetSubMesh(s);
                        if (sub.topology != MeshTopology.Triangles) continue;
                        var idx = new Unity.Collections.NativeArray<int>(sub.indexCount, Unity.Collections.Allocator.Temp);
                        d.GetIndices(idx, s); tris.AddRange(idx); idx.Dispose();
                    }
                    return (v, tris.ToArray());
                }
            }
            catch { return (null, null); }
        }

        float MeshHit(MeshRenderer r, Ray ray)
        {
            var filter = r.GetComponent<MeshFilter>(); var mesh = filter ? filter.sharedMesh : null;
            r.bounds.IntersectRay(ray, out var boxHit);
            if (!mesh || r.isPartOfStaticBatch) return boxHit;
            if (!meshCache.TryGetValue(mesh, out var data))
            {
                data = ReadMesh(mesh);
                meshCache[mesh] = data;
            }
            if (data.v == null || data.v.Length == 0) return boxHit;
            var m = r.transform.worldToLocalMatrix;
            Vector3 o = m.MultiplyPoint3x4(ray.origin), d = m.MultiplyVector(ray.direction);
            float bestT = float.MaxValue; var v = data.v; var tri = data.t;
            for (int i = 0; i + 2 < tri.Length; i += 3)
            {
                Vector3 a = v[tri[i]], e1 = v[tri[i + 1]] - a, e2 = v[tri[i + 2]] - a;
                var p = Vector3.Cross(d, e2); float det = Vector3.Dot(e1, p);
                if (det > -1e-9f && det < 1e-9f) continue;
                float inv = 1 / det; var s = o - a; float u = Vector3.Dot(s, p) * inv; if (u < 0 || u > 1) continue;
                var q = Vector3.Cross(s, e1); float w = Vector3.Dot(d, q) * inv; if (w < 0 || u + w > 1) continue;
                float t = Vector3.Dot(e2, q) * inv; if (t > 0 && t < bestT) bestT = t;
            }
            if (bestT == float.MaxValue) return float.MaxValue;
            var world = r.transform.localToWorldMatrix.MultiplyPoint3x4(o + d * bestT);
            return (world - ray.origin).magnitude;
        }

        // ------------------------------------------------------------------ frame
        bool Typing => EventSystem.current && EventSystem.current.currentSelectedGameObject && EventSystem.current.currentSelectedGameObject.GetComponent<TMP_InputField>();
        bool OverUi => EventSystem.current && EventSystem.current.IsPointerOverGameObject();
        bool Windows => (paletteDim && paletteDim.activeSelf) || (hiddenDim && hiddenDim.activeSelf);
        float moneyCheck;

        void Update()
        {
            if (!Open || !root) return;
            moneyCheck -= Time.unscaledDeltaTime;
            if (moneyCheck <= 0)
            {
                moneyCheck = 3;
                var s = bridge.State;
                if (infiniteMoney && s != null) { if (s.coins < 100_000_000) Silent("devAdjustCoins", "[1000000000]"); if (s.diamonds < 100_000) Silent("devAdjustDiamonds", "[1000000]"); }
                RefreshLeft();
            }
            if (Time.unscaledTime > messageUntil) { status.text = Help; status.color = K.C("8A7560"); messageUntil = float.MaxValue; }
            if (gameHud) { if (Input.GetKeyDown(KeyCode.F1)) ShowGameHud(false); return; }
            if (Windows) { if (Input.GetKeyDown(KeyCode.Escape)) { paletteDim.SetActive(false); hiddenDim.SetActive(false); } return; }
            if (!Typing) Keys();
            CameraKeys();
            Grid();
            NavigationFrame();
            if (tool == Tool.Paint) PaintFrame(); else if (tool == Tool.Objects) ObjectsFrame(); else PointerFrame();
        }

        void Keys()
        {
            bool ctrl = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl) || Input.GetKey(KeyCode.LeftCommand);
            bool shift = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
            if (ctrl && Input.GetKeyDown(KeyCode.S)) { Save(); return; }
            if (ctrl && Input.GetKeyDown(KeyCode.Z)) { Undo(); return; }
            if (ctrl && Input.GetKeyDown(KeyCode.D)) { if (tool == Tool.Furniture) DuplicatePiece(); else if (tool == Tool.Objects) DuplicateObject(); return; }
            if (Input.GetKeyDown(KeyCode.G)) ToggleGrid();
            if (Input.GetKeyDown(KeyCode.Alpha1)) SetTool(Tool.Furniture);
            if (Input.GetKeyDown(KeyCode.Alpha2)) SetTool(Tool.Objects);
            if (Input.GetKeyDown(KeyCode.Alpha3)) SetTool(Tool.Paint);
            if (Input.GetKeyDown(KeyCode.Escape)) { EndDrag(); Select(null, null); }
            if (tool == Tool.Paint) { if (Input.GetKeyDown(KeyCode.R)) { markTurned = !markTurned; RefreshPaint(); } return; }
            if (ctrl) return;
            float turn = shift ? 90 : 15;
            bool up = Input.GetKeyDown(KeyCode.Equals) || Input.GetKeyDown(KeyCode.KeypadPlus) || Input.GetKeyDown(KeyCode.Plus);
            bool down = Input.GetKeyDown(KeyCode.Minus) || Input.GetKeyDown(KeyCode.KeypadMinus);
            if (tool == Tool.Furniture)
            {
                if (Input.GetKeyDown(KeyCode.Q)) TurnPiece(-turn);
                if (Input.GetKeyDown(KeyCode.E)) TurnPiece(turn);
                if (up) ScalePiece(.1f); if (down) ScalePiece(-.1f);
                if (Input.GetKeyDown(KeyCode.Delete) || Input.GetKeyDown(KeyCode.Backspace)) RemovePiece();
            }
            else
            {
                if (Input.GetKeyDown(KeyCode.Q)) TurnObject(-turn);
                if (Input.GetKeyDown(KeyCode.E)) TurnObject(turn);
                if (up) ScaleObject(1.1f); if (down) ScaleObject(1 / 1.1f);
                if (Input.GetKeyDown(KeyCode.PageUp)) LiftObject(.05f);
                if (Input.GetKeyDown(KeyCode.PageDown)) LiftObject(-.05f);
                if (Input.GetKeyDown(KeyCode.Delete) || Input.GetKeyDown(KeyCode.Backspace)) RemoveObject();
            }
        }

        // Right/middle mouse drag and WASD/arrows move the camera; the wheel zooms (MarketSimulation).
        void CameraKeys()
        {
            var state = sim.CameraState; var focus = state.focus; bool move = false;
            var right = sim.view.transform.right; right.y = 0; right.Normalize();
            var forward = Vector3.Cross(right, Vector3.up);
            if (!Typing && !(Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl)))
            {
                float speed = state.zoom * 1.1f * Time.unscaledDeltaTime;
                if (Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow)) { focus += forward * speed; move = true; }
                if (Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow)) { focus -= forward * speed; move = true; }
                if (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow)) { focus -= right * speed; move = true; }
                if (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow)) { focus += right * speed; move = true; }
            }
            if ((Input.GetMouseButtonDown(1) || Input.GetMouseButtonDown(2)) && !OverUi) { panning = true; panLast = Input.mousePosition; }
            if (panning && (Input.GetMouseButton(1) || Input.GetMouseButton(2)))
            {
                Vector2 now = Input.mousePosition; var delta = now - panLast; panLast = now;
                focus -= (right * delta.x + forward * delta.y) * state.zoom * 2 / Screen.height; move = true;
            }
            else panning = false;
            if (move) sim.Focus(new Vector3(Mathf.Clamp(focus.x, -80, 80), 0, Mathf.Clamp(focus.z, -80, 90)), state.zoom);
        }

        void Grid()
        {
            if (tool == Tool.Paint)
            {
                var f = sim.CameraState.focus; float half = Mathf.Ceil(sim.CameraState.zoom * 2.2f);
                CheckoutGridOverlay.Show(Rect.MinMaxRect(Mathf.Floor(f.x - half), Mathf.Floor(f.z - half), Mathf.Ceil(f.x + half), Mathf.Ceil(f.z + half)), CheckoutPaintLayer.MarkY + .004f, CheckoutPaintLayer.Cell, new Color(1, 1, 1, .16f));
                return;
            }
            if (!CheckoutInterior.GridOn) { CheckoutGridOverlay.Hide(); return; }
            if (tool == Tool.Furniture) CheckoutGridOverlay.Show(Interior.FloorRect, CheckoutInterior.Floor + .012f, CheckoutInterior.GridSize, new Color(1, 1, 1, .42f));
            else
            {
                var f = sim.CameraState.focus; float g = Mathf.Max(.25f, CheckoutInterior.GridSize), half = Mathf.Ceil(sim.CameraState.zoom * 2.2f / g) * g;
                float x0 = Mathf.Floor((f.x - half) / g) * g, z0 = Mathf.Floor((f.z - half) / g) * g;
                CheckoutGridOverlay.Show(new Rect(x0, z0, half * 2, half * 2), CheckoutInterior.Ground + .03f, g, new Color(1, 1, 1, .14f));
            }
        }

        float Snap1(float v) { if (!CheckoutInterior.GridOn) return v; float g = Mathf.Max(.05f, CheckoutInterior.GridSize); return Mathf.Round(v / g) * g; }

        void PointerFrame()
        {
            var ray = sim.view.ScreenPointToRay(Input.mousePosition);
            if (Input.GetMouseButtonDown(0) && !OverUi)
            {
                downAt = Input.mousePosition;
                if (tool == Tool.Furniture)
                {
                    var hit = Interior.Pick(ray, true);
                    if (hit != null && !hit.outside)
                    {
                        Select(hit, null);
                        dragPlane = new Plane(Vector3.up, new Vector3(0, CheckoutInterior.Floor, 0));
                        if (dragPlane.Raycast(ray, out var d)) { dragging = true; dragChanged = false; dragOffset = hit.root.position - ray.GetPoint(d); dragStart = hit.root.position; dragStartRot = hit.rot; sim.cameraLocked = true; }
                    }
                }
            }
            if (dragging && Input.GetMouseButton(0))
            {
                if (!dragChanged && ((Vector2)Input.mousePosition - downAt).magnitude > 6)
                {
                    dragChanged = true; Dragging = true; BeginChange();
                }
                if (dragChanged && dragPlane.Raycast(ray, out var d))
                {
                    var p = ray.GetPoint(d) + dragOffset;
                    if (piece != null)
                    {
                        var here = piece.root.position; here.y = p.y;
                        p = Interior.Snap(piece, p, piece.rot, here);
                        Interior.MoveTo(piece, p); piece.root.position += Vector3.up * .06f;
                        map.FurnitureChanged(false);
                    }
                    ShowSelection();
                }
            }
            if (Input.GetMouseButtonUp(0))
            {
                if (dragging) Drop();
                else if (!OverUi && ((Vector2)Input.mousePosition - downAt).magnitude < 6) Select(null, null);
            }
        }

        void Drop()
        {
            dragging = false; Dragging = false; sim.cameraLocked = tool == Tool.Paint;
            if (!dragChanged) return;
            if (piece != null)
            {
                Interior.Place(piece);
                if (!Interior.Fits(piece, piece.root.position, piece.rot, out var why)) { Interior.MoveTo(piece, dragStart); Say(why + ". Voltou para o lugar anterior.", true); }
                else if (!Interior.Reachable(out var blocked)) Say("Atenção: assim " + Name(blocked) + " fica sem passagem para os clientes.", true);
                map.FurnitureChanged(); Select(piece, null);
            }
        }

        void EndDrag()
        {
            if (dragging) Drop();
            if (objDrag) EndObjectDrag();
            if (marquee) { marquee = false; if (marqueeBox) marqueeBox.gameObject.SetActive(false); }
            dragging = false; Dragging = false; painting = false;
        }

        // ------------------------------------------------------------------ painting
        void PaintFrame()
        {
            var ray = sim.view.ScreenPointToRay(Input.mousePosition);
            var plane = new Plane(Vector3.up, new Vector3(0, CheckoutInterior.Ground, 0));
            bool over = OverUi;
            if (!plane.Raycast(ray, out var dist) || over) { brushPreview.gameObject.SetActive(false); if (Input.GetMouseButtonUp(0)) painting = false; return; }
            var at = ray.GetPoint(dist);
            var c = CheckoutPaintLayer.CellAt(at);
            int lo = -(brushSize - 1) / 2, hi = brushSize / 2;
            // Preview of the brush square.
            brushPreview.gameObject.SetActive(true);
            float cx = (c.x + (lo + hi) * .5f + .5f) * CheckoutPaintLayer.Cell, cz = (c.y + (lo + hi) * .5f + .5f) * CheckoutPaintLayer.Cell;
            brushPreview.SetPositionAndRotation(new Vector3(cx, CheckoutPaintLayer.MarkY + .01f, cz), Quaternion.Euler(90, 0, 0));
            brushPreview.localScale = new Vector3(brushSize * CheckoutPaintLayer.Cell, brushSize * CheckoutPaintLayer.Cell, 1);
            var tint = brushMark > 0 ? new Color(1, 1, 1, .5f) : brushGround > 0 ? CheckoutPaintLayer.C(CheckoutPaintLayer.GroundColors[brushGround]) : new Color(.9f, .3f, .2f, .5f);
            tint.a = .55f; previewMaterial.color = tint;
            if (Input.GetMouseButtonDown(0)) { painting = true; BeginChange(); }
            if (painting && Input.GetMouseButton(0))
            {
                int ground = brushMark != 0 ? -1 : brushGround, mark = brushMark > 0 ? MarkKind() : brushMark == -2 || brushGround == 0 ? 0 : -1;
                for (int dz = lo; dz <= hi; dz++)
                    for (int dx = lo; dx <= hi; dx++)
                        World.Paint.Set(new Vector2Int(c.x + dx, c.y + dz), ground, mark);
            }
            if (Input.GetMouseButtonUp(0)) painting = false;
        }
    }
}
