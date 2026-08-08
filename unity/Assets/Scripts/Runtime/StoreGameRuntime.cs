using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;

public sealed class StoreGameRuntime : MonoBehaviour
{
    public static StoreGameRuntime Instance { get; private set; }

    private const string SaveKey = "checkout.unity.snapshot.v1";
    private readonly Dictionary<string, GameObject> shelfObjects = new Dictionary<string, GameObject>();
    private readonly List<CustomerAgent> customers = new List<CustomerAgent>();
    private readonly List<GameObject> placedExpansions = new List<GameObject>();
    private StoreSnapshot state;
    private Transform worldRoot;
    private Transform customerRoot;
    private StoreHud hud;
    private UnityGameBridge bridge;
    private string selectedShelfId = "produce";
    private float customerTimer = 2f;
    private float deliverySaveTimer;
    private bool buildMode;
    private GameObject expansionMarker;
    private int nextExpansionIndex = 1;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        state = CreateDefaultState();
    }

    private void Start()
    {
        Application.targetFrameRate = 60;
        Screen.orientation = ScreenOrientation.LandscapeLeft;
        CreateWorld();
        LoadStandaloneSave();
        CreateHud();

        bridge = FindAnyObjectByType<UnityGameBridge>();
        if (bridge == null)
        {
            var bridgeObject = new GameObject("UnityGameBridge");
            bridge = bridgeObject.AddComponent<UnityGameBridge>();
        }
        bridge.ConnectRuntime(this);
        hud.Refresh(state, selectedShelfId, buildMode);
    }

    private void Update()
    {
        TickDeliveries();
        TickProduction();
        TickCustomers();
        ProcessPointerInput();

        deliverySaveTimer += Time.deltaTime;
        if (deliverySaveTimer > 5f)
        {
            deliverySaveTimer = 0f;
            SaveStandaloneSnapshot();
        }
    }

    public StoreSnapshot BuildSnapshot()
    {
        return state;
    }

    public void ApplySnapshot(StoreSnapshot snapshot)
    {
        if (snapshot == null)
        {
            return;
        }

        state = snapshot;
        state.shelves ??= Array.Empty<StoreShelfState>();
        state.inventory ??= Array.Empty<StoreInventoryEntry>();
        state.deliveries ??= Array.Empty<StoreDeliveryState>();
        state.production ??= new StoreProductionState();
        state.experienceToNextLevel = Mathf.Max(120, state.experienceToNextLevel);
        RebuildShelfVisuals();
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    public void HandleBridgeAction(StoreActionMessage action)
    {
        switch (action.type)
        {
            case "toggle_market":
                ToggleMarket();
                break;
            case "restock":
                RestockShelf(action.targetId);
                break;
            case "order":
                OrderDelivery(action.targetId, action.amount > 0 ? action.amount : 6);
                break;
            case "produce":
                StartProduction();
                break;
            case "build":
                TryPlaceExpansion(new Vector3(action.x, 0f, action.z));
                break;
        }
    }

    public void ToggleMarket()
    {
        state.marketOpen = !state.marketOpen;
        customerTimer = 0.5f;
        SetNotice(state.marketOpen ? "Mercado aberto! Clientes chegando." : "Mercado fechado.", "market_toggle");
    }

    public void SelectShelf(string shelfId)
    {
        if (FindShelf(shelfId) == null)
        {
            return;
        }

        selectedShelfId = shelfId;
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    public void RestockSelectedShelf()
    {
        RestockShelf(selectedShelfId);
    }

    public void RestockShelf(string shelfId)
    {
        var shelf = FindShelf(shelfId);
        if (shelf == null || !shelf.unlocked)
        {
            SetNotice("Essa gôndola ainda está bloqueada.", "error");
            return;
        }

        var amount = Mathf.Min(shelf.capacity - shelf.stock, InventoryQuantity(shelf.productId));
        if (amount <= 0)
        {
            SetNotice("O estoque não tem unidades suficientes.", "error");
            return;
        }

        ChangeInventory(shelf.productId, -amount, shelf.productName);
        shelf.stock += amount;
        RebuildShelfVisuals();
        SetNotice($"{amount}x {shelf.productName} foi para a gôndola.", "restock");
    }

    public void OrderSelectedDelivery()
    {
        var shelf = FindShelf(selectedShelfId);
        OrderDelivery(shelf?.productId ?? "1", 6);
    }

    public void OrderDelivery(string productId, int quantity)
    {
        var shelf = FindShelfByProduct(productId);
        var productName = shelf?.productName ?? ProductName(productId);
        var price = Mathf.Max(40, quantity * Mathf.Max(8, shelf?.sellingPrice / 2 ?? 8));
        if (state.coins < price)
        {
            SetNotice("Moedas insuficientes para pedir essa carga.", "error");
            return;
        }

        state.coins -= price;
        var deliveries = new List<StoreDeliveryState>(state.deliveries ?? Array.Empty<StoreDeliveryState>())
        {
            new StoreDeliveryState
            {
                productId = productId,
                productName = productName,
                quantity = quantity,
                remainingSeconds = 6f,
            },
        };
        state.deliveries = deliveries.ToArray();
        SetNotice($"Caminhão a caminho com {quantity}x {productName}.", "delivery_started");
    }

    public void StartProduction()
    {
        if (state.production.running)
        {
            SetNotice("A padaria já está produzindo.", "error");
            return;
        }

        if (InventoryQuantity("43") < 2 || InventoryQuantity("5") < 1)
        {
            SetNotice("A receita precisa de 2x farinha e 1x leite.", "error");
            return;
        }

        ChangeInventory("43", -2, "Farinha");
        ChangeInventory("5", -1, "Leite integral");
        state.production = new StoreProductionState
        {
            recipeId = "baguete-rustica",
            recipeName = "Baguete rústica",
            outputQuantity = 4,
            remainingSeconds = 12f,
            running = true,
        };
        SetNotice("A fornada começou. Volte em alguns segundos!", "production_started");
    }

    public void ToggleBuildMode()
    {
        buildMode = !buildMode;
        if (expansionMarker != null)
        {
            expansionMarker.SetActive(buildMode);
        }
        SetNotice(buildMode ? "Modo construir: escolha o terreno marcado." : "Modo construir encerrado.", "build_mode");
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    public void TryPlaceExpansion(Vector3 requestedPosition)
    {
        if (!buildMode)
        {
            return;
        }

        if (state.level < 2)
        {
            SetNotice("Chegue ao nível 2 para expandir o mercado.", "error");
            return;
        }

        const int cost = 300;
        if (state.coins < cost)
        {
            SetNotice("A expansão custa 300 moedas.", "error");
            return;
        }

        state.coins -= cost;
        var position = requestedPosition.sqrMagnitude < 0.1f ? new Vector3(7f, 0f, 7f) : requestedPosition;
        position.x = Mathf.Round(Mathf.Clamp(position.x, -7f, 7f));
        position.z = Mathf.Round(Mathf.Clamp(position.z, 0f, 8f));
        CreatePromotionalIsland(position, nextExpansionIndex++);
        if (expansionMarker != null)
        {
            expansionMarker.SetActive(false);
        }
        buildMode = false;
        SetNotice("Nova ilha promocional construída!", "expansion_built");
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    public void CustomerReachedShelf(CustomerAgent customer, string shelfId)
    {
        var shelf = FindShelf(shelfId);
        if (shelf == null || shelf.stock <= 0)
        {
            return;
        }

        shelf.stock -= 1;
        RebuildShelfVisuals();
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    public void CustomerReachedCheckout(CustomerAgent customer, string shelfId)
    {
        var shelf = FindShelf(shelfId);
        if (shelf == null)
        {
            return;
        }

        state.coins += shelf.sellingPrice;
        state.todayRevenue += shelf.sellingPrice;
        state.customersServed += 1;
        state.unitsSold += 1;
        state.customerSatisfaction = Mathf.Clamp(state.customerSatisfaction + 1, 0, 100);
        AwardExperience(Mathf.Max(4, shelf.sellingPrice / 3));
        SetNotice($"Venda concluída: {shelf.productName} +{shelf.sellingPrice} moedas", "sale", shelfId, shelf.sellingPrice);
    }

    public void CustomerExited(CustomerAgent customer)
    {
        customers.Remove(customer);
    }

    private void TickDeliveries()
    {
        if (state.deliveries == null || state.deliveries.Length == 0)
        {
            return;
        }

        var pending = new List<StoreDeliveryState>();
        foreach (var delivery in state.deliveries)
        {
            delivery.remainingSeconds -= Time.deltaTime;
            if (delivery.remainingSeconds > 0f)
            {
                pending.Add(delivery);
                continue;
            }

            ChangeInventory(delivery.productId, delivery.quantity, delivery.productName);
            SetNotice($"Entrega recebida: {delivery.quantity}x {delivery.productName}.", "delivery_completed");
        }
        state.deliveries = pending.ToArray();
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    private void TickProduction()
    {
        if (!state.production.running)
        {
            return;
        }

        state.production.remainingSeconds -= Time.deltaTime;
        if (state.production.remainingSeconds > 0f)
        {
            hud?.RefreshProduction(state.production);
            return;
        }

        ChangeInventory("101", state.production.outputQuantity, "Baguete rústica");
        state.production = new StoreProductionState();
        AwardExperience(10);
        SetNotice("A fornada ficou pronta e foi para o estoque.", "production_completed");
    }

    private void TickCustomers()
    {
        if (!state.marketOpen || customers.Count >= 4)
        {
            return;
        }

        customerTimer -= Time.deltaTime;
        if (customerTimer > 0f)
        {
            return;
        }

        customerTimer = Mathf.Lerp(5.2f, 2.8f, Mathf.Clamp01(state.level / 12f));
        var shelf = ChooseCustomerShelf();
        if (shelf == null)
        {
            state.customerSatisfaction = Mathf.Max(0, state.customerSatisfaction - 1);
            return;
        }

        var customer = CreateCustomer(shelf);
        customers.Add(customer);
    }

    private void ProcessPointerInput()
    {
        var screenPosition = Vector2.zero;
        var hasInput = false;
        if (Input.touchCount > 0 && Input.GetTouch(0).phase == TouchPhase.Began)
        {
            screenPosition = Input.GetTouch(0).position;
            hasInput = true;
        }
        else if (Input.GetMouseButtonDown(0))
        {
            screenPosition = Input.mousePosition;
            hasInput = true;
        }

        if (!hasInput || Camera.main == null)
        {
            return;
        }

        var pointerId = Input.touchCount > 0 ? Input.GetTouch(0).fingerId : -1;
        if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject(pointerId))
        {
            return;
        }

        var ray = Camera.main.ScreenPointToRay(screenPosition);
        if (Physics.Raycast(ray, out var hit, 100f))
        {
            var clickable = hit.collider.GetComponentInParent<StoreClickable>();
            if (clickable != null)
            {
                HandleTarget(clickable);
                return;
            }

            if (buildMode)
            {
                TryPlaceExpansion(hit.point);
            }
        }
    }

    private void HandleTarget(StoreClickable clickable)
    {
        switch (clickable.actionType)
        {
            case "shelf":
                SelectShelf(clickable.targetId);
                break;
            case "market":
                ToggleMarket();
                break;
            case "stockroom":
                SetNotice("Estoque selecionado. Use REABASTECER ou PEDIR CARGA.", "stockroom");
                break;
            case "truck":
                OrderSelectedDelivery();
                break;
            case "bakery":
                StartProduction();
                break;
            case "expansion":
                ToggleBuildMode();
                break;
        }
    }

    private void CreateWorld()
    {
        worldRoot = new GameObject("SupermarketWorld").transform;
        customerRoot = new GameObject("Customers").transform;
        customerRoot.SetParent(worldRoot);
        SetupCamera();
        CreateSupermarketEnvironment();
        foreach (var shelf in state.shelves)
        {
            CreateShelfVisual(shelf);
        }
        CreateExpansionMarker();
    }

    private void SetupCamera()
    {
        var camera = Camera.main;
        if (camera == null)
        {
            var cameraObject = new GameObject("Main Camera");
            camera = cameraObject.AddComponent<Camera>();
            camera.tag = "MainCamera";
        }

        camera.orthographic = true;
        camera.orthographicSize = 17.2f;
        // The customer-facing facade stays closest to the bottom of the screen.
        camera.transform.position = new Vector3(24f, 28f, 26f);
        camera.transform.LookAt(new Vector3(0f, 0.6f, 0f));
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.15f, 0.19f, 0.21f);
        RenderSettings.ambientLight = new Color(0.34f, 0.39f, 0.38f);

        var lightObject = new GameObject("Sun");
        var light = lightObject.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 0.78f;
        light.color = new Color(1f, 0.91f, 0.79f);
        light.shadowStrength = 0.72f;
        light.shadows = LightShadows.Soft;
        light.transform.rotation = Quaternion.Euler(45f, -30f, 0f);

        var fillLightObject = new GameObject("FillLight");
        var fillLight = fillLightObject.AddComponent<Light>();
        fillLight.type = LightType.Directional;
        fillLight.intensity = 0.16f;
        fillLight.color = new Color(0.55f, 0.72f, 0.82f);
        fillLight.shadows = LightShadows.None;
        fillLightObject.transform.rotation = Quaternion.Euler(30f, 145f, 0f);
    }

    private void CreateSupermarketEnvironment()
    {
        var prefab = Resources.Load<GameObject>("Models/SupermarketCity/supermarket_city");
        if (prefab == null)
        {
            Debug.LogError("SupermarketCity FBX was not found at Resources/Models/SupermarketCity/supermarket_city.");
            return;
        }

        var environment = Instantiate(prefab, Vector3.zero, Quaternion.identity, worldRoot);
        environment.name = "SupermarketCity";
        environment.transform.localPosition = Vector3.zero;
        environment.transform.localRotation = Quaternion.identity;
        environment.transform.localScale = Vector3.one;
        DisableEnvironmentHelpers(environment.transform);
        DisableReplacedMarketShell(environment.transform);

        var diamondMarketPrefab = Resources.Load<GameObject>("Models/DiamondMarket/diamond_market");
        if (diamondMarketPrefab == null)
        {
            Debug.LogError("Diamond market FBX was not found at Resources/Models/DiamondMarket/diamond_market.");
            return;
        }

        var diamondMarket = Instantiate(diamondMarketPrefab, Vector3.zero, Quaternion.identity, worldRoot);
        diamondMarket.name = "DiamondCourtyardMarket";
        diamondMarket.transform.localPosition = Vector3.zero;
        diamondMarket.transform.localRotation = Quaternion.identity;
        diamondMarket.transform.localScale = Vector3.one;
        CreateImportedMarketProps();
    }

    private static void DisableEnvironmentHelpers(Transform node)
    {
        var nodeName = node.name;
        if (nodeName == "Roof" || nodeName.StartsWith("UCX_") || nodeName.Contains("_Proxy_"))
        {
            node.gameObject.SetActive(false);
            return;
        }

        for (var i = 0; i < node.childCount; i++)
        {
            DisableEnvironmentHelpers(node.GetChild(i));
        }
    }

    private static void DisableReplacedMarketShell(Transform node)
    {
        var nodeName = node.name;
        if (nodeName.StartsWith("SM_") ||
            nodeName.StartsWith("PROP_Checkout") ||
            nodeName.StartsWith("PROP_FrontPlanter") ||
            nodeName.StartsWith("PROP_EntryPlanter") ||
            nodeName.StartsWith("PROP_Door_") ||
            nodeName.StartsWith("PROP_Entrance_"))
        {
            node.gameObject.SetActive(false);
            return;
        }

        for (var i = 0; i < node.childCount; i++)
        {
            DisableReplacedMarketShell(node.GetChild(i));
        }
    }

    private void CreateImportedMarketProps()
    {
        var root = new GameObject("ImportedMarketProps").transform;
        root.SetParent(worldRoot);

        var entrance = StoreVisualFactory.SpawnModel(
            "Meshy/entrance/entrance",
            new Vector3(4f, 1.25f, 6.7f),
            Quaternion.identity,
            Vector3.one,
            root);
        entrance.name = "StoreEntrance";

        var checkout = StoreVisualFactory.SpawnModel(
            "Meshy/checkout/checkout",
            new Vector3(5.85f, 1.1f, -2.8f),
            Quaternion.identity,
            Vector3.one,
            root);
        checkout.name = "CheckoutCounter";
        StoreVisualFactory.AddClickTarget(checkout, "register", "market");

        var cashier = StoreVisualFactory.SpawnModel(
            "Meshy/cashier/cashier",
            new Vector3(5.35f, 0.9f, -1.55f),
            Quaternion.Euler(0f, 180f, 0f),
            Vector3.one,
            root);
        cashier.name = "Cashier";
    }

    private void CreateMarketTerrain()
    {
        StoreVisualFactory.Cube("GrassTerrain", new Vector3(0f, -0.35f, 3f), new Vector3(22f, 0.6f, 18f), StoreVisualFactory.Grass, worldRoot);
        var floorTexture = Resources.Load<Texture2D>("Art/market-floor-tile-v1");
        if (floorTexture != null)
        {
            StoreVisualFactory.TexturedCube("MarketFloor", new Vector3(0f, -0.01f, 3f), new Vector3(20.8f, 0.14f, 16.8f), Color.white, floorTexture, new Vector2(2.35f, 2.35f), worldRoot);
        }
        else
        {
            StoreVisualFactory.Cube("MarketFloor", new Vector3(0f, -0.01f, 3f), new Vector3(20.8f, 0.14f, 16.8f), StoreVisualFactory.Floor, worldRoot);
        }

        StoreVisualFactory.Cube("EntranceThreshold", new Vector3(0f, 0.13f, -5.2f), new Vector3(4.8f, 0.08f, 0.8f), StoreVisualFactory.TealLight, worldRoot);

        // Parking lot / road strip in front
        StoreVisualFactory.Cube("RoadStrip", new Vector3(0f, -0.32f, -7.5f), new Vector3(22f, 0.1f, 5f), new Color(0.62f, 0.64f, 0.66f), worldRoot);
        StoreVisualFactory.Cube("RoadLine1", new Vector3(-4f, -0.26f, -7.5f), new Vector3(0.18f, 0.02f, 4.8f), Color.white, worldRoot);
        StoreVisualFactory.Cube("RoadLine2", new Vector3(4f, -0.26f, -7.5f), new Vector3(0.18f, 0.02f, 4.8f), Color.white, worldRoot);
    }

    private void CreateLowPerimeter()
    {
        CreateWallSegment("BackWall", new Vector3(0f, 0f, 11.25f), new Vector3(21f, 2.2f, 0.48f));
        CreateWallSegment("LeftWall", new Vector3(-10.45f, 0f, 3f), new Vector3(0.48f, 2.2f, 16.8f));
        CreateWallSegment("RightWall", new Vector3(10.45f, 0f, 3f), new Vector3(0.48f, 2.2f, 16.8f));
        CreateWallSegment("FrontWallLeft", new Vector3(-7.05f, 0f, -5.25f), new Vector3(6.5f, 2.2f, 0.48f));
        CreateWallSegment("FrontWallRight", new Vector3(7.05f, 0f, -5.25f), new Vector3(6.5f, 2.2f, 0.48f));

        // Entrance arch
        StoreVisualFactory.Cube("EntranceMat", new Vector3(0f, 0.02f, -5.25f), new Vector3(4.4f, 0.06f, 0.7f), StoreVisualFactory.TealLight, worldRoot);
        StoreVisualFactory.Cube("EntrancePostLeft", new Vector3(-2.15f, 1.1f, -5.25f), new Vector3(0.42f, 2.2f, 0.42f), StoreVisualFactory.WallWhite, worldRoot);
        StoreVisualFactory.Cube("EntrancePostRight", new Vector3(2.15f, 1.1f, -5.25f), new Vector3(0.42f, 2.2f, 0.42f), StoreVisualFactory.WallWhite, worldRoot);
        StoreVisualFactory.Cube("EntranceHeader", new Vector3(0f, 2.32f, -5.25f), new Vector3(4.9f, 0.46f, 0.58f), StoreVisualFactory.Teal, worldRoot);
        StoreVisualFactory.Cube("EntranceHeaderAccent", new Vector3(0f, 2.08f, -5.25f), new Vector3(4.9f, 0.12f, 0.6f), StoreVisualFactory.Orange, worldRoot);
        StoreVisualFactory.Cube("EntranceSign", new Vector3(0f, 2.32f, -5.0f), new Vector3(3.2f, 0.28f, 0.06f), new Color(1f, 0.85f, 0.2f), worldRoot);
    }

    private void CreateWallSegment(string name, Vector3 position, Vector3 size)
    {
        var center = new Vector3(position.x, size.y * 0.5f, position.z);
        var wallTexture = Resources.Load<Texture2D>("Art/market-wall-teal-v1");
        // White lower body
        StoreVisualFactory.Cube(name + "Body", center + Vector3.down * (size.y * 0.15f), new Vector3(size.x, size.y * 0.7f, size.z), StoreVisualFactory.WallWhite, worldRoot);
        // Teal upper band
        StoreVisualFactory.Cube(name + "Band", center + Vector3.up * (size.y * 0.28f), new Vector3(size.x + 0.04f, size.y * 0.22f, size.z + 0.04f), StoreVisualFactory.Teal, worldRoot);
        // Cream coping at top
        StoreVisualFactory.Cube(name + "Coping", center + Vector3.up * (size.y * 0.54f), new Vector3(size.x + 0.14f, 0.18f, size.z + 0.14f), StoreVisualFactory.Cream, worldRoot);
        // Orange accent stripe at base
        StoreVisualFactory.Cube(name + "Stripe", new Vector3(position.x, 0.08f, position.z), new Vector3(size.x + 0.06f, 0.14f, size.z + 0.06f), StoreVisualFactory.Orange, worldRoot);
    }

    private void CreateLandscaping()
    {
        var positions = new[]
        {
            new Vector3(-8.8f, 9.25f, 0f),
            new Vector3(8.7f, 9.3f, 1f),
            new Vector3(-9.1f, 1.2f, 2f),
            new Vector3(9.05f, 1.5f, 3f),
            new Vector3(-8.3f, -3.9f, 4f),
            new Vector3(8.2f, -3.85f, 5f),
        };

        for (var i = 0; i < positions.Length; i++)
        {
            CreateTree("Tree_" + i, positions[i]);
        }

        for (var i = 0; i < 8; i++)
        {
            var x = -7.8f + (i % 4) * 5.2f;
            var z = i < 4 ? 10.1f : -4.25f;
            StoreVisualFactory.Cylinder("FlowerBedPot_" + i, new Vector3(x, 0.14f, z), new Vector3(0.52f, 0.18f, 0.52f), StoreVisualFactory.Orange, worldRoot);
            StoreVisualFactory.Sphere("FlowerBed_" + i, new Vector3(x, 0.48f, z), new Vector3(0.72f, 0.34f, 0.72f), i % 2 == 0 ? StoreVisualFactory.Leaf : StoreVisualFactory.Berry, worldRoot);
        }
    }

    private void CreateFarmStyleDecor()
    {
        CreateCropPatch("CabbagePatch", new Vector3(-8.05f, 0f, 4.45f), StoreVisualFactory.Leaf);
        CreateCropPatch("TomatoPatch", new Vector3(8.05f, 0f, 4.45f), StoreVisualFactory.Berry);
        CreateCropPatch("CarrotPatch", new Vector3(-8.05f, 0f, 7.25f), StoreVisualFactory.Orange);
        CreateFenceLine("BakeryFence", new Vector3(4.85f, 0f, 9.5f), 3);
    }

    private void CreateCropPatch(string name, Vector3 position, Color cropColor)
    {
        var root = new GameObject(name).transform;
        root.SetParent(worldRoot);
        root.position = position;

        StoreVisualFactory.Cube("BedWood", position + new Vector3(0f, 0.16f, 0f), new Vector3(2.35f, 0.24f, 1.45f), StoreVisualFactory.Wood, root);
        StoreVisualFactory.Cube("BedSoil", position + new Vector3(0f, 0.3f, 0f), new Vector3(2.08f, 0.12f, 1.2f), StoreVisualFactory.GrassDark, root);

        for (var i = 0; i < 4; i++)
        {
            var x = position.x - 0.7f + i * 0.46f;
            var z = position.z + (i % 2 == 0 ? -0.28f : 0.28f);
            StoreVisualFactory.Cylinder("CropStem_" + i, new Vector3(x, 0.58f, z), new Vector3(0.08f, 0.28f, 0.08f), StoreVisualFactory.GrassDark, root);
            StoreVisualFactory.Sphere("Crop_" + i, new Vector3(x, 0.82f, z), new Vector3(0.3f, 0.28f, 0.3f), cropColor, root);
            StoreVisualFactory.Sphere("CropLeaf_" + i, new Vector3(x + 0.16f, 0.74f, z - 0.08f), new Vector3(0.2f, 0.12f, 0.28f), StoreVisualFactory.GrassLight, root);
        }
    }

    private void CreateFenceLine(string name, Vector3 position, int segmentCount)
    {
        var root = new GameObject(name).transform;
        root.SetParent(worldRoot);
        root.position = position;

        for (var i = 0; i <= segmentCount; i++)
        {
            var x = position.x + i * 0.78f;
            StoreVisualFactory.Cylinder("FencePost_" + i, new Vector3(x, 0.58f, position.z), new Vector3(0.12f, 0.58f, 0.12f), StoreVisualFactory.Wood, root);
            StoreVisualFactory.Cube("FenceCap_" + i, new Vector3(x, 1.2f, position.z), new Vector3(0.24f, 0.1f, 0.24f), StoreVisualFactory.Cream, root);
        }

        for (var i = 0; i < segmentCount; i++)
        {
            var x = position.x + 0.39f + i * 0.78f;
            StoreVisualFactory.Cube("FenceRailUpper_" + i, new Vector3(x, 0.88f, position.z), new Vector3(0.82f, 0.12f, 0.12f), StoreVisualFactory.Wood, root);
            StoreVisualFactory.Cube("FenceRailLower_" + i, new Vector3(x, 0.48f, position.z), new Vector3(0.82f, 0.12f, 0.12f), StoreVisualFactory.Wood, root);
        }
    }

    private void CreateTree(string name, Vector3 position)
    {
        var model = StoreVisualFactory.SpawnModel("tree", position, Quaternion.identity, Vector3.one, worldRoot);
        if (model.name == "tree")
        {
            model.name = name;
            return;
        }
        StoreVisualFactory.Cylinder(name + "Planter", position + Vector3.up * 0.14f, new Vector3(1.0f, 0.22f, 1.0f), StoreVisualFactory.Cream, worldRoot);
        StoreVisualFactory.Cylinder(name + "PlanterRim", position + Vector3.up * 0.22f, new Vector3(1.08f, 0.08f, 1.08f), StoreVisualFactory.Orange, worldRoot);
        StoreVisualFactory.Cylinder(name + "Soil", position + Vector3.up * 0.28f, new Vector3(0.78f, 0.06f, 0.78f), StoreVisualFactory.GrassDark, worldRoot);
        StoreVisualFactory.Cylinder(name + "Trunk", position + Vector3.up * 0.9f, new Vector3(0.22f, 0.9f, 0.22f), StoreVisualFactory.Wood, worldRoot);
        StoreVisualFactory.Sphere(name + "Crown", position + Vector3.up * 1.9f, new Vector3(1.3f, 1.55f, 1.3f), StoreVisualFactory.Leaf, worldRoot);
        StoreVisualFactory.Sphere(name + "CrownHigh", position + new Vector3(0.0f, 2.5f, 0.0f), new Vector3(0.9f, 0.88f, 0.9f), StoreVisualFactory.GrassLight, worldRoot);
        StoreVisualFactory.Sphere(name + "CrownAccent", position + new Vector3(0.46f, 2.1f, -0.2f), new Vector3(0.62f, 0.6f, 0.62f), StoreVisualFactory.GrassLight, worldRoot);
    }

    private void CreateShelfVisual(StoreShelfState shelf)
    {
        var root = new GameObject("Shelf_" + shelf.id).transform;
        root.SetParent(worldRoot);
        root.position = new Vector3(shelf.x, 0f, shelf.z);
        shelfObjects[shelf.id] = root.gameObject;

        if (shelf.id == "bakery")
        {
            var bakeryDisplay = StoreVisualFactory.SpawnModel(
                "Meshy/bakery_display/bakery_display",
                new Vector3(shelf.x, 0.9f, shelf.z),
                Quaternion.identity,
                Vector3.one,
                root);
            bakeryDisplay.name = "BakeryDisplay";
            StoreVisualFactory.AddClickTarget(bakeryDisplay, shelf.id, "shelf");
            StoreVisualFactory.AddProductCard(root, shelf.productId, new Vector3(shelf.x, 2.05f, shelf.z - 0.1f), 0.52f);
            return;
        }

        var shelfModel = StoreVisualFactory.SpawnModel("shelf", new Vector3(shelf.x, 0f, shelf.z), Quaternion.identity, Vector3.one, root);
        var body = shelfModel.name == "shelf" ? shelfModel : null;

        if (body != null)
        {
            StoreVisualFactory.AddClickTarget(body, shelf.id, "shelf");
            PlaceShelfDecor(shelf, root, offsetY: 0.54f, productSize: new Vector3(0.34f, 0.30f, 0.26f), cardOffset: -0.28f);
            return;
        }

        var shelfColor = SectorColor(shelf.id);
        body = StoreVisualFactory.Cube("ShelfBack", new Vector3(shelf.x, 1.05f, shelf.z + 0.27f), new Vector3(2.65f, 1.85f, 0.18f), shelfColor, root);
        StoreVisualFactory.Cube("ShelfBase", new Vector3(shelf.x, 0.18f, shelf.z), new Vector3(2.95f, 0.3f, 0.95f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Cube("ShelfLowerDeck", new Vector3(shelf.x, 0.55f, shelf.z - 0.13f), new Vector3(2.75f, 0.12f, 0.82f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cube("ShelfUpperDeck", new Vector3(shelf.x, 1.22f, shelf.z - 0.13f), new Vector3(2.75f, 0.12f, 0.82f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cube("ShelfTopTrim", new Vector3(shelf.x, 1.9f, shelf.z - 0.02f), new Vector3(2.85f, 0.16f, 0.9f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cylinder("ShelfPostLeft", new Vector3(shelf.x - 1.25f, 1.05f, shelf.z - 0.38f), new Vector3(0.14f, 0.78f, 0.14f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cylinder("ShelfPostRight", new Vector3(shelf.x + 1.25f, 1.05f, shelf.z - 0.38f), new Vector3(0.14f, 0.78f, 0.14f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.AddClickTarget(body, shelf.id, "shelf");
        PlaceShelfDecor(shelf, root, offsetY: 0.7f, productSize: new Vector3(0.38f, 0.34f, 0.3f), cardOffset: -0.32f);
    }

    private void PlaceShelfDecor(StoreShelfState shelf, Transform root, float offsetY, Vector3 productSize, float cardOffset)
    {
        var sectorTexture = Resources.Load<Texture2D>("Sectors/sector-display-atlas-v1");
        if (sectorTexture != null)
            StoreVisualFactory.AddAtlasBillboard(root, sectorTexture, new Vector3(shelf.x, 2.02f, shelf.z - 0.02f), new Vector2(0.95f, 0.95f), SectorIndex(shelf.id));

        var productsRoot = new GameObject("Products").transform;
        productsRoot.SetParent(root);
        var stockToShow = Mathf.Min(shelf.stock, 8);
        for (var i = 0; i < stockToShow; i++)
        {
            var column = i % 4;
            var row = i / 4;
            var productColor = ProductColor(shelf.productId, i);
            var product = StoreVisualFactory.Cube("Product_" + i, new Vector3(shelf.x - 1.05f + column * 0.7f, offsetY + row * 0.54f, shelf.z - 0.44f), productSize, productColor, productsRoot);
            product.transform.rotation = Quaternion.Euler(0f, (i % 2) * 7f, 0f);
            StoreVisualFactory.AddProductCard(productsRoot, shelf.productId, product.transform.position + new Vector3(0f, 0f, cardOffset), productSize.x * 0.88f);
        }
    }

    private void RebuildShelfVisuals()
    {
        foreach (var shelf in state.shelves)
        {
            if (shelfObjects.TryGetValue(shelf.id, out var previous) && previous != null)
            {
                Destroy(previous);
            }
        }
        shelfObjects.Clear();
        foreach (var shelf in state.shelves)
        {
            CreateShelfVisual(shelf);
        }
    }

    private void CreateStockroom()
    {
        var root = new GameObject("Stockroom").transform;
        root.SetParent(worldRoot);
        var body = StoreVisualFactory.Cube("StockroomBody", new Vector3(-6.5f, 1.0f, -2.2f), new Vector3(2.4f, 2.0f, 1.7f), StoreVisualFactory.WallWhite, root);
        StoreVisualFactory.Cube("StockroomBand", new Vector3(-6.5f, 1.88f, -2.2f), new Vector3(2.46f, 0.46f, 1.78f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("StockroomBase", new Vector3(-6.5f, 0.1f, -2.2f), new Vector3(2.6f, 0.18f, 1.9f), StoreVisualFactory.Orange, root);
        // Flat roof with parapet
        StoreVisualFactory.Cube("StockroomRoof", new Vector3(-6.5f, 2.18f, -2.2f), new Vector3(2.6f, 0.22f, 1.9f), StoreVisualFactory.RoofBlue, root);
        StoreVisualFactory.Cube("StockroomParapet", new Vector3(-6.5f, 2.38f, -2.2f), new Vector3(2.7f, 0.28f, 2.0f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("StockroomParapetTop", new Vector3(-6.5f, 2.56f, -2.2f), new Vector3(2.82f, 0.12f, 2.12f), StoreVisualFactory.Cream, root);
        // Door
        StoreVisualFactory.Cube("StockroomDoor", new Vector3(-6.5f, 0.78f, -1.37f), new Vector3(0.88f, 1.32f, 0.1f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("StockroomDoorFrame", new Vector3(-6.5f, 0.78f, -1.34f), new Vector3(1.08f, 1.5f, 0.08f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.AddClickTarget(body, "stockroom", "stockroom");
        // Boxes stacked outside
        for (var i = 0; i < 3; i++)
        {
            var boxColor = i % 2 == 0 ? new Color(0.88f, 0.56f, 0.2f) : new Color(0.78f, 0.46f, 0.16f);
            StoreVisualFactory.Cube("Box_" + i, new Vector3(-7.2f + i * 0.58f, 0.28f, -1.18f), new Vector3(0.48f, 0.48f, 0.48f), boxColor, root);
            StoreVisualFactory.Cube("BoxStripe_" + i, new Vector3(-7.2f + i * 0.58f, 0.28f, -1.16f), new Vector3(0.5f, 0.12f, 0.5f), StoreVisualFactory.Teal, root);
        }
        StoreVisualFactory.Cube("BoxTop1", new Vector3(-7.2f, 0.72f, -1.18f), new Vector3(0.48f, 0.48f, 0.48f), new Color(0.88f, 0.56f, 0.2f), root);
    }

    private void CreateCheckout()
    {
        var root = new GameObject("Checkout").transform;
        root.SetParent(worldRoot);

        var model = StoreVisualFactory.SpawnModel("checkout_counter", new Vector3(6f, 0f, -2.2f), Quaternion.identity, Vector3.one, root);
        if (model.name == "checkout_counter")
        {
            StoreVisualFactory.AddClickTarget(model, "register", "market");
            return;
        }
        // Main counter body — white with teal band
        var body = StoreVisualFactory.Cube("CheckoutBody", new Vector3(6f, 0.72f, -2.2f), new Vector3(3.2f, 1.44f, 1.6f), StoreVisualFactory.WallWhite, root);
        StoreVisualFactory.Cube("CheckoutBand", new Vector3(6f, 1.28f, -2.2f), new Vector3(3.26f, 0.34f, 1.66f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("CheckoutBase", new Vector3(6f, 0.08f, -2.2f), new Vector3(3.4f, 0.16f, 1.8f), StoreVisualFactory.Orange, root);
        // Countertop
        StoreVisualFactory.Cube("CheckoutCounter", new Vector3(6f, 1.52f, -2.2f), new Vector3(3.35f, 0.16f, 1.75f), StoreVisualFactory.Cream, root);
        // Register monitor
        StoreVisualFactory.Cube("RegisterBase", new Vector3(6f, 1.72f, -2.72f), new Vector3(0.5f, 0.14f, 0.32f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("RegisterScreen", new Vector3(6f, 2.08f, -2.78f), new Vector3(0.72f, 0.52f, 0.1f), new Color(0.08f, 0.1f, 0.14f), root);
        StoreVisualFactory.Cube("RegisterScreenGlow", new Vector3(6f, 2.08f, -2.72f), new Vector3(0.6f, 0.4f, 0.06f), new Color(0.28f, 0.72f, 1f), root);
        StoreVisualFactory.Cube("RegisterPole", new Vector3(6f, 1.86f, -2.78f), new Vector3(0.1f, 0.72f, 0.1f), StoreVisualFactory.Teal, root);
        // Conveyor belt
        StoreVisualFactory.Cube("ConveyorBelt", new Vector3(6f, 1.62f, -1.92f), new Vector3(2.8f, 0.08f, 0.58f), new Color(0.24f, 0.24f, 0.26f), root);
        StoreVisualFactory.Cube("ConveyorEnd1", new Vector3(4.68f, 1.62f, -1.92f), new Vector3(0.22f, 0.14f, 0.62f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("ConveyorEnd2", new Vector3(7.32f, 1.62f, -1.92f), new Vector3(0.22f, 0.14f, 0.62f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.AddClickTarget(body, "register", "market");
    }

    private void CreateBakery()
    {
        var root = new GameObject("Bakery").transform;
        root.SetParent(worldRoot);

        var model = StoreVisualFactory.SpawnModel("bakery", new Vector3(2.6f, 0f, 7.2f), Quaternion.identity, Vector3.one, root);
        if (model.name == "bakery")
        {
            StoreVisualFactory.AddClickTarget(model, "bakery", "bakery");
            return;
        }
        // White walls with teal upper band
        var body = StoreVisualFactory.Cube("BakeryBody", new Vector3(2.6f, 1.0f, 7.2f), new Vector3(3.1f, 2.0f, 1.65f), StoreVisualFactory.WallWhite, root);
        StoreVisualFactory.Cube("BakeryBand", new Vector3(2.6f, 1.88f, 7.2f), new Vector3(3.16f, 0.46f, 1.72f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("BakeryBase", new Vector3(2.6f, 0.1f, 7.2f), new Vector3(3.3f, 0.18f, 1.85f), StoreVisualFactory.Orange, root);
        // Window
        StoreVisualFactory.Cube("BakeryWindow", new Vector3(2.6f, 1.0f, 6.41f), new Vector3(1.5f, 0.78f, 0.12f), new Color(0.52f, 0.88f, 0.92f), root);
        StoreVisualFactory.Cube("BakeryWindowFrame", new Vector3(2.6f, 1.0f, 6.38f), new Vector3(1.74f, 0.96f, 0.1f), StoreVisualFactory.WallWhite, root);
        StoreVisualFactory.Cube("BakeryWindowBarV", new Vector3(2.6f, 1.0f, 6.35f), new Vector3(0.1f, 0.8f, 0.06f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cube("BakeryWindowBarH", new Vector3(2.6f, 1.0f, 6.35f), new Vector3(1.55f, 0.1f, 0.06f), StoreVisualFactory.Cream, root);
        // Striped awning
        StoreVisualFactory.Cube("BakeryAwning", new Vector3(2.6f, 1.98f, 6.22f), new Vector3(3.4f, 0.2f, 0.82f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Cube("BakeryAwningStripe1", new Vector3(1.6f, 1.98f, 6.22f), new Vector3(0.28f, 0.22f, 0.84f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cube("BakeryAwningStripe2", new Vector3(2.6f, 1.98f, 6.22f), new Vector3(0.28f, 0.22f, 0.84f), StoreVisualFactory.Cream, root);
        StoreVisualFactory.Cube("BakeryAwningStripe3", new Vector3(3.6f, 1.98f, 6.22f), new Vector3(0.28f, 0.22f, 0.84f), StoreVisualFactory.Cream, root);
        // Gabled roof
        var roofLeft = StoreVisualFactory.Cube("BakeryRoofLeft", new Vector3(1.72f, 2.38f, 7.2f), new Vector3(1.9f, 0.22f, 1.9f), StoreVisualFactory.RoofBlue, root);
        roofLeft.transform.rotation = Quaternion.Euler(0f, 0f, -28f);
        var roofRight = StoreVisualFactory.Cube("BakeryRoofRight", new Vector3(3.48f, 2.38f, 7.2f), new Vector3(1.9f, 0.22f, 1.9f), StoreVisualFactory.RoofBlue, root);
        roofRight.transform.rotation = Quaternion.Euler(0f, 0f, 28f);
        StoreVisualFactory.Cube("BakeryRoofPeak", new Vector3(2.6f, 2.78f, 7.2f), new Vector3(0.28f, 0.22f, 1.96f), StoreVisualFactory.Teal, root);
        // Chimney
        StoreVisualFactory.Cylinder("BakeryChimney", new Vector3(3.4f, 2.88f, 7.35f), new Vector3(0.32f, 0.88f, 0.32f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("BakeryChimneyCap", new Vector3(3.4f, 3.36f, 7.35f), new Vector3(0.48f, 0.12f, 0.48f), StoreVisualFactory.Orange, root);
        // Planters
        StoreVisualFactory.Cylinder("BakeryPlanterLeft", new Vector3(1.08f, 0.12f, 6.38f), new Vector3(0.46f, 0.18f, 0.46f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Sphere("BakeryPlantLeft", new Vector3(1.08f, 0.56f, 6.38f), new Vector3(0.52f, 0.46f, 0.52f), StoreVisualFactory.Leaf, root);
        StoreVisualFactory.Cylinder("BakeryPlanterRight", new Vector3(4.12f, 0.12f, 6.38f), new Vector3(0.46f, 0.18f, 0.46f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Sphere("BakeryPlantRight", new Vector3(4.12f, 0.56f, 6.38f), new Vector3(0.52f, 0.46f, 0.52f), StoreVisualFactory.Leaf, root);
        StoreVisualFactory.AddClickTarget(body, "bakery", "bakery");
    }

    private void CreateDeliveryTruck()
    {
        var root = new GameObject("DeliveryTruck").transform;
        root.SetParent(worldRoot);

        var model = StoreVisualFactory.SpawnModel("truck", new Vector3(-6f, 0f, 7.3f), Quaternion.identity, Vector3.one, root);
        if (model.name == "truck")
        {
            StoreVisualFactory.AddClickTarget(model, "truck", "truck");
            return;
        }
        // Cargo box
        var body = StoreVisualFactory.Cube("TruckBody", new Vector3(-6.1f, 0.82f, 7.3f), new Vector3(3.2f, 1.52f, 1.78f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Cube("TruckBodyBand", new Vector3(-6.1f, 1.42f, 7.3f), new Vector3(3.26f, 0.28f, 1.84f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("TruckBodyStripe", new Vector3(-6.1f, 0.22f, 7.3f), new Vector3(3.26f, 0.2f, 1.84f), StoreVisualFactory.Cream, root);
        // Cab
        StoreVisualFactory.Cube("TruckCab", new Vector3(-4.02f, 0.76f, 7.3f), new Vector3(0.82f, 1.4f, 1.72f), StoreVisualFactory.Teal, root);
        StoreVisualFactory.Cube("TruckCabRoof", new Vector3(-4.02f, 1.52f, 7.3f), new Vector3(0.86f, 0.2f, 1.76f), StoreVisualFactory.RoofBlue, root);
        StoreVisualFactory.Cube("TruckWindow", new Vector3(-3.6f, 0.92f, 7.3f), new Vector3(0.1f, 0.62f, 1.1f), new Color(0.52f, 0.88f, 0.92f), root);
        StoreVisualFactory.Cube("TruckBumper", new Vector3(-3.58f, 0.22f, 7.3f), new Vector3(0.18f, 0.28f, 1.78f), new Color(0.62f, 0.64f, 0.66f), root);
        StoreVisualFactory.Cube("TruckHeadlightL", new Vector3(-3.58f, 0.72f, 6.52f), new Vector3(0.1f, 0.28f, 0.3f), new Color(1f, 0.92f, 0.6f), root);
        StoreVisualFactory.Cube("TruckHeadlightR", new Vector3(-3.58f, 0.72f, 8.08f), new Vector3(0.1f, 0.28f, 0.3f), new Color(1f, 0.92f, 0.6f), root);
        StoreVisualFactory.AddClickTarget(body, "truck", "truck");
        // Wheels
        for (var i = 0; i < 4; i++)
        {
            var wheelObj = StoreVisualFactory.Cylinder("Wheel_" + i, new Vector3(-6.9f + i * 1.25f, 0.2f, i % 2 == 0 ? 6.38f : 8.22f), new Vector3(0.38f, 0.2f, 0.38f), new Color(0.18f, 0.18f, 0.2f), root);
            wheelObj.transform.Rotate(90f, 0f, 0f);
            StoreVisualFactory.Cylinder("WheelHub_" + i, new Vector3(-6.9f + i * 1.25f, 0.2f, i % 2 == 0 ? 6.36f : 8.2f), new Vector3(0.2f, 0.06f, 0.2f), new Color(0.72f, 0.72f, 0.72f), root);
            root.GetChild(root.childCount - 1).Rotate(90f, 0f, 0f);
        }
    }

    private void CreateExpansionMarker()
    {
        expansionMarker = new GameObject("ExpansionMarker");
        expansionMarker.transform.SetParent(worldRoot);
        expansionMarker.transform.position = new Vector3(7f, 0.05f, 7f);
        var tile = StoreVisualFactory.Cube("ExpansionTile", expansionMarker.transform.position, new Vector3(2.2f, 0.08f, 1.8f), new Color(0.25f, 0.8f, 0.68f), expansionMarker.transform);
        StoreVisualFactory.AddClickTarget(tile, "expansion-1", "expansion");
        expansionMarker.SetActive(false);
    }

    private void CreatePromotionalIsland(Vector3 position, int index)
    {
        var root = new GameObject("PromotionalIsland_" + index).transform;
        root.SetParent(worldRoot);
        root.position = position;
        StoreVisualFactory.Cube("IslandBase", position + new Vector3(0f, 0.12f, 0f), new Vector3(2.3f, 0.22f, 1.65f), StoreVisualFactory.Orange, root);
        StoreVisualFactory.Cube("IslandTop", position + new Vector3(0f, 0.35f, 0f), new Vector3(2f, 0.18f, 1.35f), StoreVisualFactory.Cream, root);
        for (var i = 0; i < 4; i++)
        {
            StoreVisualFactory.Cylinder("IslandProduct_" + i, position + new Vector3(-0.65f + i * 0.43f, 0.7f, 0f), new Vector3(0.18f, 0.28f, 0.18f), ProductColor("101", i), root);
        }
    }

    private CustomerAgent CreateCustomer(StoreShelfState shelf)
    {
        var root = new GameObject("Customer");
        root.transform.SetParent(customerRoot);
        root.transform.position = new Vector3(4f + UnityEngine.Random.Range(-0.35f, 0.35f), 0f, 6.7f);
        var customerPrefab = Resources.Load<GameObject>("Models/Customers/customer_3d");
        if (customerPrefab != null)
        {
            var model = Instantiate(customerPrefab, root.transform);
            model.name = "Customer3D";
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = Quaternion.identity;
            model.transform.localScale = Vector3.one;
        }

        var animator = root.AddComponent<CustomerModelAnimator>();
        var agent = root.AddComponent<CustomerAgent>();
        agent.Initialize(
            this,
            shelf.id,
            new Vector3(shelf.x, 0f, shelf.z - 1.1f),
            new Vector3(6f, 0f, -2.8f),
            new Vector3(4f, 0f, 6.7f),
            animator);
        return agent;
    }

    private static int SectorIndex(string shelfId)
    {
        switch (shelfId)
        {
            case "produce":
                return 0;
            case "dairy":
                return 1;
            case "bakery":
                return 2;
            default:
                return 3;
        }
    }

    private static Color SectorColor(string shelfId)
    {
        switch (shelfId)
        {
            case "produce":
                return new Color(0.15f, 0.5f, 0.31f);
            case "dairy":
                return new Color(0.08f, 0.47f, 0.51f);
            case "bakery":
                return new Color(0.76f, 0.31f, 0.18f);
            default:
                return new Color(0.87f, 0.42f, 0.12f);
        }
    }

    private StoreShelfState ChooseCustomerShelf()
    {
        var available = new List<StoreShelfState>();
        foreach (var shelf in state.shelves)
        {
            if (shelf.unlocked && shelf.stock > 0)
            {
                available.Add(shelf);
            }
        }
        return available.Count == 0 ? null : available[UnityEngine.Random.Range(0, available.Count)];
    }

    private void AwardExperience(int amount)
    {
        state.experience += amount;
        state.experience = Mathf.Max(0, state.experience);
        while (state.experience >= state.experienceToNextLevel)
        {
            state.experience -= state.experienceToNextLevel;
            state.level += 1;
            state.experienceToNextLevel = 120 + (state.level - 1) * 80;
            if (state.level == 2 && expansionMarker != null)
            {
                expansionMarker.SetActive(buildMode);
            }
            SetNotice($"Nível {state.level}! Novas possibilidades de construção.", "level_up");
        }
        hud?.Refresh(state, selectedShelfId, buildMode);
    }

    private StoreShelfState FindShelf(string shelfId)
    {
        foreach (var shelf in state.shelves)
        {
            if (shelf.id == shelfId)
            {
                return shelf;
            }
        }
        return null;
    }

    private StoreShelfState FindShelfByProduct(string productId)
    {
        foreach (var shelf in state.shelves)
        {
            if (shelf.productId == productId)
            {
                return shelf;
            }
        }
        return null;
    }

    private int InventoryQuantity(string productId)
    {
        foreach (var entry in state.inventory)
        {
            if (entry.productId == productId)
            {
                return entry.quantity;
            }
        }
        return 0;
    }

    private void ChangeInventory(string productId, int amount, string productName)
    {
        foreach (var entry in state.inventory)
        {
            if (entry.productId == productId)
            {
                entry.quantity = Mathf.Max(0, entry.quantity + amount);
                return;
            }
        }

        if (amount > 0)
        {
            var inventory = new List<StoreInventoryEntry>(state.inventory)
            {
                new StoreInventoryEntry { productId = productId, productName = productName, quantity = amount },
            };
            state.inventory = inventory.ToArray();
        }
    }

    private string ProductName(string productId)
    {
        return productId switch
        {
            "1" => "Tomate",
            "5" => "Leite integral",
            "9" => "Suco de laranja",
            "43" => "Farinha",
            "101" => "Baguete rústica",
            _ => "Produto",
        };
    }

    private Color ProductColor(string productId, int variation)
    {
        return productId switch
        {
            "1" => variation % 2 == 0 ? StoreVisualFactory.Berry : StoreVisualFactory.Leaf,
            "5" => Color.white,
            "101" => new Color(0.83f, 0.48f, 0.18f),
            "9" => new Color(1f, 0.56f, 0.04f),
            _ => new Color(0.2f + variation * 0.08f, 0.5f, 0.75f),
        };
    }

    private void CreateHud()
    {
        var hudObject = new GameObject("StoreHUD");
        hud = hudObject.AddComponent<StoreHud>();
        hud.Initialize(this);
    }

    public void SetNotice(string message, string eventType, string targetId = "", int amount = 0)
    {
        hud?.ShowNotice(message);
        bridge?.EmitAction(new StoreEventMessage
        {
            type = eventType,
            targetId = targetId,
            amount = amount,
            coins = state.coins,
            level = state.level,
            message = message,
        });
    }

    public StoreShelfState GetSelectedShelf()
    {
        return FindShelf(selectedShelfId);
    }

    public int GetSelectedInventoryQuantity()
    {
        var shelf = GetSelectedShelf();
        return shelf == null ? 0 : InventoryQuantity(shelf.productId);
    }

    public void SaveStandaloneSnapshot()
    {
        PlayerPrefs.SetString(SaveKey, JsonUtility.ToJson(state));
        PlayerPrefs.Save();
    }

    private void LoadStandaloneSave()
    {
        var json = PlayerPrefs.GetString(SaveKey, string.Empty);
        if (!string.IsNullOrEmpty(json))
        {
            var saved = JsonUtility.FromJson<StoreSnapshot>(json);
            if (saved != null && saved.shelves != null && saved.shelves.Length > 0)
            {
                state = saved;
                NormalizeShelfLayout();
                RebuildShelfVisuals();
            }
        }
    }

    private void NormalizeShelfLayout()
    {
        foreach (var shelf in state.shelves)
        {
            switch (shelf.id)
            {
                case "produce":
                    shelf.x = -5.35f;
                    shelf.z = 4.05f;
                    break;
                case "dairy":
                    shelf.x = -1.8f;
                    shelf.z = 4.05f;
                    break;
                case "bakery":
                    shelf.x = 1.8f;
                    shelf.z = 4.05f;
                    break;
                case "snacks":
                    shelf.x = 5.35f;
                    shelf.z = 4.05f;
                    break;
            }
        }
    }

    private static StoreSnapshot CreateDefaultState()
    {
        return new StoreSnapshot
        {
            coins = 1248,
            premiumCurrency = 10,
            level = 1,
            experience = 0,
            experienceToNextLevel = 120,
            customersServed = 0,
            unitsSold = 0,
            todayRevenue = 0,
            customerSatisfaction = 55,
            marketOpen = false,
            employeeHired = false,
            shelves = new[]
            {
                new StoreShelfState { id = "produce", displayName = "Hortifruti", productId = "1", productName = "Tomate", stock = 3, capacity = 8, sellingPrice = 18, unlocked = true, x = -5.35f, z = 4.05f },
                new StoreShelfState { id = "dairy", displayName = "Laticínios", productId = "5", productName = "Leite integral", stock = 3, capacity = 8, sellingPrice = 32, unlocked = true, x = -1.8f, z = 4.05f },
                new StoreShelfState { id = "bakery", displayName = "Padaria", productId = "101", productName = "Baguete", stock = 2, capacity = 8, sellingPrice = 48, unlocked = true, x = 1.8f, z = 4.05f },
                new StoreShelfState { id = "snacks", displayName = "Mercearia", productId = "9", productName = "Suco", stock = 3, capacity = 8, sellingPrice = 28, unlocked = true, x = 5.35f, z = 4.05f },
            },
            inventory = new[]
            {
                new StoreInventoryEntry { productId = "1", productName = "Tomate", quantity = 9 },
                new StoreInventoryEntry { productId = "5", productName = "Leite integral", quantity = 4 },
                new StoreInventoryEntry { productId = "9", productName = "Suco de laranja", quantity = 6 },
                new StoreInventoryEntry { productId = "43", productName = "Farinha", quantity = 8 },
            },
            deliveries = Array.Empty<StoreDeliveryState>(),
            production = new StoreProductionState(),
        };
    }
}
