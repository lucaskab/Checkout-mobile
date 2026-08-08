using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public sealed class StoreHud : MonoBehaviour
{
    private static readonly Color PanelColor = new Color(0.03f, 0.12f, 0.16f, 0.94f);
    private static readonly Color PanelLight = new Color(0.06f, 0.2f, 0.22f, 0.94f);
    private static readonly Color Gold = new Color(1f, 0.74f, 0.24f);
    private static readonly Color Mint = new Color(0.28f, 0.92f, 0.7f);
    private static readonly Color Coral = new Color(1f, 0.37f, 0.2f);

    private StoreGameRuntime runtime;
    private Text levelText;
    private Text coinsText;
    private Text satisfactionText;
    private Text marketText;
    private Text selectedText;
    private Text inventoryText;
    private Text productionText;
    private Text noticeText;
    private Text missionText;
    private Button marketButton;
    private Button buildButton;
    private GameObject buildHint;
    private StoreSnapshot lastState;
    private string lastShelfId;

    public void Initialize(StoreGameRuntime owner)
    {
        runtime = owner;
        CreateEventSystem();
        var canvasObject = new GameObject("HUDCanvas");
        canvasObject.transform.SetParent(transform);
        var canvas = canvasObject.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 20;
        var scaler = canvasObject.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
        scaler.matchWidthOrHeight = 0.5f;
        canvasObject.AddComponent<GraphicRaycaster>();

        CreateTopBar(canvasObject.transform);
        CreateActionPanel(canvasObject.transform);
        CreateNotice(canvasObject.transform);
        CreateBuildHint(canvasObject.transform);
    }

    public void Refresh(StoreSnapshot state, string selectedShelfId, bool isBuildMode)
    {
        lastState = state;
        lastShelfId = selectedShelfId;
        if (state == null)
        {
            return;
        }

        var selectedShelf = FindShelf(selectedShelfId);
        levelText.text = $"NÍVEL {state.level}  •  XP {state.experience}/{state.experienceToNextLevel}";
        coinsText.text = $"🪙 {state.coins:N0}";
        satisfactionText.text = $"☺ {state.customerSatisfaction}%";
        marketText.text = state.marketOpen ? "FECHAR MERCADO" : "ABRIR MERCADO";
        selectedText.text = selectedShelf == null ? "Selecione uma gôndola" : $"{selectedShelf.displayName}  •  {selectedShelf.productName}";
        inventoryText.text = selectedShelf == null ? "" : $"GÔNDOLA {selectedShelf.stock}/{selectedShelf.capacity}    ESTOQUE {runtime.GetSelectedInventoryQuantity()}";
        missionText.text = $"MISSÃO  Venda 10 produtos   {Mathf.Min(10, state.unitsSold)}/10";
        productionText.text = state.production.running ? $"PADARIA  •  {state.production.recipeName}  {Mathf.CeilToInt(state.production.remainingSeconds)}s" : "PADARIA  •  pronta para produzir";
        buildHint.SetActive(isBuildMode);
    }

    public void RefreshProduction(StoreProductionState production)
    {
        if (production != null && production.running)
        {
            productionText.text = $"PADARIA  •  {production.recipeName}  {Mathf.CeilToInt(production.remainingSeconds)}s";
        }
    }

    public void ShowNotice(string message)
    {
        noticeText.text = message;
        noticeText.color = Color.white;
    }

    private void CreateTopBar(Transform parent)
    {
        var topBar = Panel("TopBar", parent, new Vector2(0.02f, 0.88f), new Vector2(0.98f, 0.98f), PanelColor);
        MakeText("Title", topBar.transform, "CHECKOUT MARKET", new Vector2(0.02f, 0.1f), new Vector2(0.22f, 0.85f), 28, Gold, TextAnchor.MiddleLeft);
        levelText = MakeText("Level", topBar.transform, "NÍVEL 1  •  XP 0/120", new Vector2(0.25f, 0.1f), new Vector2(0.48f, 0.85f), 22, Color.white, TextAnchor.MiddleLeft);
        coinsText = MakeText("Coins", topBar.transform, "🪙 1.248", new Vector2(0.67f, 0.1f), new Vector2(0.79f, 0.85f), 24, Gold, TextAnchor.MiddleCenter);
        satisfactionText = MakeText("Satisfaction", topBar.transform, "☺ 55%", new Vector2(0.79f, 0.1f), new Vector2(0.89f, 0.85f), 23, Mint, TextAnchor.MiddleCenter);
        marketButton = MakeButton("MarketButton", topBar.transform, "ABRIR MERCADO", new Vector2(0.9f, 0.12f), new Vector2(0.995f, 0.88f), Coral, runtime.ToggleMarket);
        marketText = marketButton.GetComponentInChildren<Text>();
    }

    private void CreateActionPanel(Transform parent)
    {
        var panel = Panel("ActionPanel", parent, new Vector2(0.02f, 0.04f), new Vector2(0.37f, 0.2f), PanelColor);
        selectedText = MakeText("Selected", panel.transform, "Selecione uma gôndola", new Vector2(0.04f, 0.62f), new Vector2(0.57f, 0.94f), 21, Color.white, TextAnchor.MiddleLeft);
        inventoryText = MakeText("Inventory", panel.transform, "", new Vector2(0.04f, 0.34f), new Vector2(0.57f, 0.62f), 17, Mint, TextAnchor.MiddleLeft);
        var restockButton = MakeButton("Restock", panel.transform, "REABASTECER", new Vector2(0.6f, 0.52f), new Vector2(0.98f, 0.92f), Mint, runtime.RestockSelectedShelf);
        restockButton.GetComponentInChildren<Text>().fontSize = 17;
        var orderButton = MakeButton("Order", panel.transform, "PEDIR CARGA", new Vector2(0.6f, 0.08f), new Vector2(0.98f, 0.47f), Gold, runtime.OrderSelectedDelivery);
        orderButton.GetComponentInChildren<Text>().fontSize = 17;

        missionText = MakeText("Mission", parent, "MISSÃO  Venda 10 produtos   0/10", new Vector2(0.4f, 0.05f), new Vector2(0.61f, 0.1f), 18, Color.white, TextAnchor.MiddleCenter);
        productionText = MakeText("Production", parent, "PADARIA  • pronta para produzir", new Vector2(0.4f, 0.1f), new Vector2(0.61f, 0.15f), 18, Color.white, TextAnchor.MiddleCenter);
        var produceButton = MakeButton("Produce", parent, "PRODUZIR", new Vector2(0.64f, 0.04f), new Vector2(0.76f, 0.15f), new Color(0.75f, 0.37f, 0.2f), runtime.StartProduction);
        produceButton.GetComponentInChildren<Text>().fontSize = 17;
        buildButton = MakeButton("Build", parent, "CONSTRUIR", new Vector2(0.78f, 0.04f), new Vector2(0.9f, 0.15f), TealButtonColor(), runtime.ToggleBuildMode);
        buildButton.GetComponentInChildren<Text>().fontSize = 17;
        var saveButton = MakeButton("Save", parent, "SALVAR", new Vector2(0.92f, 0.04f), new Vector2(0.98f, 0.15f), PanelLight, runtime.SaveStandaloneSnapshot);
        saveButton.GetComponentInChildren<Text>().fontSize = 15;
    }

    private void CreateNotice(Transform parent)
    {
        noticeText = MakeText("Notice", parent, "Toque numa gôndola para começar", new Vector2(0.25f, 0.79f), new Vector2(0.75f, 0.85f), 22, Color.white, TextAnchor.MiddleCenter);
    }

    private void CreateBuildHint(Transform parent)
    {
        buildHint = Panel("BuildHint", parent, new Vector2(0.42f, 0.2f), new Vector2(0.78f, 0.29f), new Color(0.03f, 0.29f, 0.28f, 0.93f));
        MakeText("BuildHintText", buildHint.transform, "MODO CONSTRUIR\nToque no terreno + para comprar uma ilha promocional", new Vector2(0.04f, 0.12f), new Vector2(0.96f, 0.88f), 21, Color.white, TextAnchor.MiddleCenter);
        buildHint.SetActive(false);
    }

    private GameObject Panel(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax, Color color)
    {
        var panel = new GameObject(name);
        panel.transform.SetParent(parent, false);
        var image = panel.AddComponent<Image>();
        image.color = color;
        SetRect(panel.GetComponent<RectTransform>(), anchorMin, anchorMax, Vector2.zero, Vector2.zero);
        return panel;
    }

    private Text MakeText(string name, Transform parent, string text, Vector2 anchorMin, Vector2 anchorMax, int fontSize, Color color, TextAnchor alignment)
    {
        var textObject = new GameObject(name);
        textObject.transform.SetParent(parent, false);
        var textComponent = textObject.AddComponent<Text>();
        textComponent.text = text;
        textComponent.color = color;
        textComponent.fontSize = fontSize;
        textComponent.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        textComponent.alignment = alignment;
        textComponent.horizontalOverflow = HorizontalWrapMode.Wrap;
        textComponent.verticalOverflow = VerticalWrapMode.Truncate;
        SetRect(textObject.GetComponent<RectTransform>(), anchorMin, anchorMax, Vector2.zero, Vector2.zero);
        return textComponent;
    }

    private Button MakeButton(string name, Transform parent, string label, Vector2 anchorMin, Vector2 anchorMax, Color color, UnityEngine.Events.UnityAction action)
    {
        var buttonObject = new GameObject(name);
        buttonObject.transform.SetParent(parent, false);
        var image = buttonObject.AddComponent<Image>();
        image.color = color;
        var button = buttonObject.AddComponent<Button>();
        button.targetGraphic = image;
        button.onClick.AddListener(action);
        var colors = button.colors;
        colors.highlightedColor = Color.Lerp(color, Color.white, 0.2f);
        colors.pressedColor = Color.Lerp(color, Color.black, 0.18f);
        button.colors = colors;
        var text = MakeText("Label", buttonObject.transform, label, new Vector2(0.04f, 0.03f), new Vector2(0.96f, 0.97f), 19, Color.white, TextAnchor.MiddleCenter);
        text.fontStyle = FontStyle.Bold;
        SetRect(buttonObject.GetComponent<RectTransform>(), anchorMin, anchorMax, Vector2.zero, Vector2.zero);
        return button;
    }

    private void CreateEventSystem()
    {
        if (FindAnyObjectByType<EventSystem>() != null)
        {
            return;
        }

        var eventSystemObject = new GameObject("EventSystem");
        eventSystemObject.AddComponent<EventSystem>();
        eventSystemObject.AddComponent<StandaloneInputModule>();
    }

    private StoreShelfState FindShelf(string id)
    {
        if (lastState?.shelves == null)
        {
            return null;
        }
        foreach (var shelf in lastState.shelves)
        {
            if (shelf.id == id)
            {
                return shelf;
            }
        }
        return null;
    }

    private static Color TealButtonColor()
    {
        return new Color(0.04f, 0.5f, 0.49f);
    }

    private static void SetRect(RectTransform rect, Vector2 anchorMin, Vector2 anchorMax, Vector2 offsetMin, Vector2 offsetMax)
    {
        rect.anchorMin = anchorMin;
        rect.anchorMax = anchorMax;
        rect.offsetMin = offsetMin;
        rect.offsetMax = offsetMax;
        rect.pivot = new Vector2(0.5f, 0.5f);
    }
}
