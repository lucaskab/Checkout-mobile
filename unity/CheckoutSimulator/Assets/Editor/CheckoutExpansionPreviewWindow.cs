using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.UIElements;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UIElements;

public sealed class CheckoutExpansionPreviewWindow : EditorWindow
{
    static readonly string[] ExpansionNames =
    {
        "Mapa base",
        "Ala de produtos frescos",
        "Ala de atendimento",
        "Anexo de estoque",
        "Galeria premium"
    };

    static readonly string[] StageButtonNames = { "Base", "Frescos", "Atend.", "Estoque", "Premium" };

    static readonly float[,] Scales =
    {
        { .78f, .68f },
        { .86f, .78f },
        { .93f, .88f },
        { 1f, 1f },
        { 1.12f, 1.12f }
    };

    readonly List<Button> stageButtons = new List<Button>();
    Label stageLabel;
    Label statusLabel;
    Button previousButton;
    Button nextButton;
    Button previewButton;
    Button stopButton;
    int stage;
    int appliedStage;
    bool previewing;
    bool savingPreview;
    Transform world;
    Scene previewScene;
    GameObject sessionObject;
    CheckoutMarketLayout layout;

    [MenuItem("Supermarket/Expansion Preview")]
    static void OpenWindow()
    {
        var window = GetWindow<CheckoutExpansionPreviewWindow>("Expansion Preview");
        window.minSize = new Vector2(460, 330);
        window.Show();
    }

    public void CreateGUI()
    {
        var root = rootVisualElement;
        root.Clear();
        root.style.paddingLeft = 8;
        root.style.paddingRight = 8;
        root.style.paddingTop = 8;
        root.style.paddingBottom = 8;
        root.Add(new HelpBox(
            "Alterne as expansões e edite o mapa na Scene View. As mudanças feitas nos objetos projetados são convertidas para o mapa base e permanecem ao trocar de etapa. O progresso salvo do jogo não é alterado.",
            HelpBoxMessageType.Info));

        stageLabel = new Label();
        root.Add(stageLabel);

        var stages = new VisualElement();
        stages.style.flexDirection = FlexDirection.Row;
        stages.style.marginTop = 8;
        stages.style.marginBottom = 4;
        root.Add(stages);
        stageButtons.Clear();
        for (var index = 0; index < ExpansionNames.Length; index++)
        {
            var selectedStage = index;
            var button = new Button(() => SelectStage(selectedStage)) { text = StageButtonNames[index] };
            button.style.flexGrow = 1;
            button.style.flexShrink = 1;
            button.style.minWidth = 0;
            button.style.fontSize = 12;
            button.tooltip = ExpansionNames[index];
            stageButtons.Add(button);
            stages.Add(button);
        }

        var controls = new VisualElement();
        controls.style.flexDirection = FlexDirection.Row;
        controls.style.marginBottom = 8;
        previousButton = new Button(() => SelectStage(Mathf.Max(0, stage - 1))) { text = "◀ Anterior" };
        nextButton = new Button(() => SelectStage(Mathf.Min(4, stage + 1))) { text = "Próxima ▶" };
        previousButton.style.flexGrow = 1;
        nextButton.style.flexGrow = 1;
        controls.Add(previousButton);
        controls.Add(nextButton);
        root.Add(controls);

        previewButton = new Button(StartPreview) { text = "Iniciar prévia" };
        stopButton = new Button(StopPreview) { text = "Parar prévia e voltar ao mapa base" };
        root.Add(previewButton);
        root.Add(stopButton);
        root.Add(new Button(FrameMap) { text = "Enquadrar mapa na Scene View" });
        root.Add(new Button(SaveScene) { text = "Salvar alterações do mapa" });
        statusLabel = new Label();
        statusLabel.style.whiteSpace = WhiteSpace.Normal;
        root.Add(statusLabel);
        RefreshUI();
    }

    void OnEnable()
    {
        minSize = new Vector2(460, 330);
        EditorApplication.update += CaptureSceneEdits;
        EditorSceneManager.sceneSaving += BeforeSceneSave;
        EditorSceneManager.sceneSaved += AfterSceneSave;
    }

    void OnDisable()
    {
        EditorApplication.update -= CaptureSceneEdits;
        EditorSceneManager.sceneSaving -= BeforeSceneSave;
        EditorSceneManager.sceneSaved -= AfterSceneSave;
        EndPreview();
    }

    void SelectStage(int value)
    {
        stage = Mathf.Clamp(value, 0, 4);
        if (previewing) ApplyStage(stage);
        RefreshUI();
    }

    void StartPreview()
    {
        if (EditorApplication.isPlaying)
        {
            SetStatus("Pare o Play Mode para editar a cena.");
            return;
        }

        var simulation = FindAnyObjectByType<MarketSimulation>();
        if (!simulation || !simulation.world)
        {
            SetStatus("Abra a cena Supermarket para iniciar a prévia.");
            return;
        }

        world = simulation.world;
        previewScene = world.gameObject.scene;
        sessionObject = new GameObject("Expansion Preview Session") { hideFlags = HideFlags.HideAndDontSave };
        layout = sessionObject.AddComponent<CheckoutMarketLayout>();
        layout.hideFlags = HideFlags.HideAndDontSave;
        layout.Initialize(world);
        previewing = true;
        ApplyStage(stage);
        SetStatus("Prévia ativa. Mova, gire ou escale objetos na Scene View; Ctrl+S salva as alterações no mapa base.");
        RefreshUI();
    }

    void StopPreview()
    {
        if (!previewing) return;
        CaptureSceneEdits();
        EndPreview();
        stage = 0;
        SetStatus("Prévia encerrada. As alterações ficam no mapa base; salve a cena para mantê-las.");
        RefreshUI();
        SceneView.RepaintAll();
    }

    void EndPreview()
    {
        if (!previewing) return;
        try
        {
            CaptureSceneEdits();
            RestoreBase();
        }
        catch (Exception exception)
        {
            Debug.LogWarning("Expansion preview cleanup: " + exception.Message);
        }

        previewing = false;
        layout = null;
        world = null;
        if (sessionObject) DestroyImmediate(sessionObject);
        sessionObject = null;
        SceneView.RepaintAll();
        RefreshUI();
    }

    void ApplyStage(int value)
    {
        if (!previewing || !layout) return;
        var next = CreateLayout(value);
        layout.Apply(next);
        ApplySectorVisibility(next);
        appliedStage = value;
        SceneView.RepaintAll();
        RefreshUI();
    }

    // The saved scene is the unprojected map (scale 1, every area bought) that runtime projects
    // per stage. Stage 0 is itself a projection, so saving or stopping on it shrinks the map again.
    void RestoreBase()
    {
        if (!previewing || !layout) return;
        layout.Apply(new MarketLayout
        {
            stage = 4,
            storage = true,
            parking = true,
            loadingYard = true,
            premium = true,
            sectorIds = new[] { "padaria", "queijaria", "acougue", "bebidas", "peixaria", "sorvetes" }
        });
        appliedStage = -1;
        SceneView.RepaintAll();
    }

    static MarketLayout CreateLayout(int value)
    {
        value = Mathf.Clamp(value, 0, 4);
        bool fresh = value >= 1;
        bool service = value >= 2;
        bool stock = value >= 3;
        bool premium = value >= 4;
        var sectors = new List<string> { "padaria" };
        if (fresh) sectors.Add("queijaria");
        if (service) { sectors.Add("acougue"); sectors.Add("bebidas"); }
        if (stock) sectors.Add("peixaria");
        if (premium) sectors.Add("sorvetes");
        return new MarketLayout
        {
            stage = value,
            widthScale = Scales[value, 0],
            depthScale = Scales[value, 1],
            storage = fresh,
            parking = service,
            loadingYard = stock,
            premium = premium,
            sectorIds = sectors.ToArray()
        };
    }

    void ApplySectorVisibility(MarketLayout next)
    {
        var sectorIds = new[] { "padaria", "queijaria", "acougue", "bebidas", "peixaria", "sorvetes" };
        foreach (var id in sectorIds)
        {
            bool present = next.sectorIds.Contains(id);
            var root = world.Find("Sector_" + id);
            var progress = world.Find("Sector Construction/" + id)?.GetComponent<CheckoutSectorProgress>();
            if (progress)
            {
                progress.gameObject.SetActive(present);
                progress.Apply(present, false);
            }
            else if (root) root.gameObject.SetActive(present);
        }
    }

    void CaptureSceneEdits()
    {
        if (!previewing || !layout || EditorApplication.isPlayingOrWillChangePlaymode) return;
        if (!layout.CaptureEditorEdits()) return;
        if (previewScene.IsValid()) EditorSceneManager.MarkSceneDirty(previewScene);
        SetStatus("Alterações capturadas para todas as etapas. Ctrl+S salva o mapa base.");
        SceneView.RepaintAll();
    }

    void BeforeSceneSave(Scene scene, string path)
    {
        if (!previewing || scene != previewScene || savingPreview) return;
        CaptureSceneEdits();
        savingPreview = true;
        RestoreBase();
    }

    void AfterSceneSave(Scene scene)
    {
        if (!previewing || scene != previewScene || !savingPreview) return;
        savingPreview = false;
        ApplyStage(stage);
        SetStatus("Cena salva com os objetos no mapa base. Prévia da " + ExpansionNames[stage] + " continua ativa.");
    }

    void SaveScene()
    {
        if (previewing) CaptureSceneEdits();
        var scene = previewing ? previewScene : SceneManager.GetActiveScene();
        if (!scene.IsValid() || string.IsNullOrEmpty(scene.path))
        {
            SetStatus("A cena ainda não tem um caminho para salvar.");
            return;
        }
        EditorSceneManager.SaveScene(scene);
    }

    void FrameMap()
    {
        if (!world) world = FindAnyObjectByType<MarketSimulation>()?.world;
        if (!world) return;
        var renderers = world.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0) return;
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
        var view = SceneView.lastActiveSceneView;
        if (view) view.Frame(bounds, false);
    }

    void RefreshUI()
    {
        if (stageLabel == null) return;
        stageLabel.text = "Etapa " + stage + " de 4: " + ExpansionNames[stage];
        for (var index = 0; index < stageButtons.Count; index++)
            stageButtons[index].SetEnabled(!previewing || index != appliedStage);
        previousButton?.SetEnabled(stage > 0);
        nextButton?.SetEnabled(stage < 4);
        previewButton?.SetEnabled(!previewing);
        stopButton?.SetEnabled(previewing);
        if (!previewing && statusLabel != null && string.IsNullOrEmpty(statusLabel.text))
            statusLabel.text = "Escolha uma etapa e inicie a prévia para editar o mapa.";
    }

    void SetStatus(string message)
    {
        if (statusLabel != null) statusLabel.text = message;
    }
}
