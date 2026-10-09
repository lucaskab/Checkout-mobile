#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Networking;

namespace TripoForUnity
{
    // Enums (ModelVersion, TextureQuality) are defined once in the Runtime
    // assembly (TripoForUnity namespace) and shared via the asmdef reference to
    // tripoforunity.Runtime. Do not redeclare them here.

    public class Tripo_main_window : EditorWindow
    {
        private const string PreferencesPrefix = "TripoForUnity.Editor.";
        private const string ApiKeyPrefsKey = "ApiKeyPrefsKey";
        private const string UserBalancePrefsKey = "UserBalancePrefsKey";
        private const string FrozenCreditsPrefsKey = PreferencesPrefix + "FrozenCredits";
        private const string SelectedModelPrefsKey = PreferencesPrefix + "SelectedModel";
        private const string V3TriangleFaceLimitPrefsKey = PreferencesPrefix + "V3TriangleFaceLimit";
        private const string V3QuadFaceLimitPrefsKey = PreferencesPrefix + "V3QuadFaceLimit";
        private const string V25FaceLimitPrefsKey = PreferencesPrefix + "V25FaceLimit";
        private const string P1FaceLimitPrefsKey = PreferencesPrefix + "P1FaceLimit";
        private const string TexturePrefsKey = PreferencesPrefix + "Texture";
        private const string PbrPrefsKey = PreferencesPrefix + "Pbr";
        private const string TextureQualityPrefsKey = PreferencesPrefix + "TextureQuality";
        private const string AutoSizePrefsKey = PreferencesPrefix + "AutoSize";
        private const string QuadPrefsKey = PreferencesPrefix + "Quad";
        private const string ActiveTabPrefsKey = PreferencesPrefix + "ActiveTab";
        private const string AdvancedFoldoutPrefsKey = PreferencesPrefix + "AdvancedFoldout";

        private string apiKey = "";
        private string userBalance = "";
        private int frozenCredits;
        private string textPrompt = "";
        private string imagePath = "";
        private Texture2D uploadedImage = null;
        private bool advancedSettingsFoldout = false;
        private bool apiKeyConfirmed = false;
        private int activeGenerationTab = 0;
        private static string saveDirectory = "Assets/TripoModels/";

        private int faceLimit = TripoGenerationLimits.DefaultFaceLimit;
        private bool textureOptional = true;
        private bool pbrOptional = true;
        private TextureQuality textureQualityOptional = TextureQuality.Standard;
        private bool autoSizeOptional;
        private bool quadOptional;
        private int v3TriangleFaceLimit = TripoGenerationLimits.MaxTriangleFaceLimit;
        private int v3QuadFaceLimit = TripoGenerationLimits.MaxQuadFaceLimit;
        private int v25FaceLimit = TripoGenerationLimits.MaxV25FaceLimit;
        private int p1FaceLimit = TripoGenerationLimits.MaxP1FaceLimit;


        private int selectedModelIndex = 0;
        private readonly string[] textureQualityOptions = { "standard", "detailed" };
        private readonly string[] topologyOptions = { "Triangles", "Quads" };
        private readonly string[] modelOptions =
        {
            "v3.1-20260211",
            "v3.0-20250812",
            "v2.5-20250123",
            "P1-20260311"
        };
        private const int RequestTimeoutSeconds = 60;
        private const int DownloadTimeoutSeconds = 300;
        private const double TaskTimeoutSeconds = 300d;
        private const double PollIntervalSeconds = 1d;
        private const double SchedulerStallThresholdSeconds = 5d;
        private const double RequestWatchdogGraceSeconds = 15d;
        private const double ProgressStallNoticeSeconds = 30d;
        private const double BalanceRefreshDelaySeconds = 1d;
        private const double ActiveBalanceRefreshIntervalSeconds = 5d;
        private const double TransientRetryDelaySeconds = 2d;
        private const int PollRequestMaxAttempts = 3;
        private const int BalanceRefreshMaxAttempts = 3;
        private const int MaxQueuedJobs = 10;
        private static readonly List<EditorCoroutineState> coroutines = new List<EditorCoroutineState>();
        private static readonly List<GenerationJob> generationJobs = new List<GenerationJob>();
        private static int nextGenerationJobNumber = 1;
        private static int nextBalanceRefreshVersion = 1;
        private static double lastSchedulerUpdateTime;
        private static double lastQueueRepaintTime;

        private enum GenerationJobStage
        {
            Uploading,
            Submitting,
            Generating,
            Converting,
            Downloading,
            Importing,
            Completed,
            Failed
        }

        private sealed class GenerationJob
        {
            public int Number;
            public bool IsTextToModel;
            public string InputSummary;
            public string Prompt;
            public string ImagePath;
            public string ApiKey;
            public string ModelId;
            public int FaceLimit;
            public bool Texture;
            public bool Pbr;
            public string TextureQuality;
            public bool AutoSize;
            public bool Quad;
            public bool GenerationOutputIsFbx;
            public string ImageToken;
            public string GenerationTaskId;
            public string ConversionTaskId;
            public string OutputAssetPath;
            public GenerationJobStage Stage;
            public float GenerationProgress;
            public float ConversionProgress;
            public string ErrorMessage;
            public string LastServerStatus;
            public double StageDeadline;
            public double LastPollTime;
            public double LastProgressChangeTime;
            public double LastActivityTime;

            public bool IsTerminal
            {
                get
                {
                    return Stage == GenerationJobStage.Completed ||
                        Stage == GenerationJobStage.Failed;
                }
            }

            public string CurrentTaskId
            {
                get
                {
                    return !string.IsNullOrEmpty(ConversionTaskId)
                        ? ConversionTaskId
                        : GenerationTaskId;
                }
            }

            public float Progress
            {
                get
                {
                    switch (Stage)
                    {
                        case GenerationJobStage.Uploading:
                            return 0.03f;
                        case GenerationJobStage.Submitting:
                            return 0.08f;
                        case GenerationJobStage.Generating:
                            return Mathf.Lerp(0.1f, Quad ? 0.88f : 0.5f, GenerationProgress);
                        case GenerationJobStage.Converting:
                            return Mathf.Lerp(0.5f, 0.88f, ConversionProgress);
                        case GenerationJobStage.Downloading:
                            return 0.92f;
                        case GenerationJobStage.Importing:
                            return 0.97f;
                        case GenerationJobStage.Completed:
                            return 1f;
                        default:
                            return Quad
                                ? Mathf.Lerp(0.1f, 0.88f, GenerationProgress)
                                : Mathf.Lerp(
                                    0.1f,
                                    0.88f,
                                    (GenerationProgress + ConversionProgress) * 0.5f);
                    }
                }
            }
        }

        private sealed class EditorCoroutineState
        {
            public readonly GenerationJob Job;
            public readonly IEnumerator Routine;
            public object WaitingFor;
            public double WaitDeadline;

            public EditorCoroutineState(IEnumerator routine, GenerationJob job)
            {
                Routine = routine;
                Job = job;
            }
        }

        private sealed class EditorDelay
        {
            public readonly double ResumeAt;

            public EditorDelay(double seconds)
            {
                ResumeAt = EditorApplication.timeSinceStartup + seconds;
            }
        }

        private sealed class BalanceRefreshResult
        {
            public bool Success;
        }

        [MenuItem("Tools/Tripo API Unity")]
        public static void ShowWindow()
        {
            var window = GetWindow<Tripo_main_window>("Tripo API Unity");
            window.minSize = new Vector2(420, 560);
            window.maxSize = new Vector2(4000, 4000);
            Rect p = window.position;
            window.position = new Rect(p.x, p.y, 460, 760);
            window.Show();
        }

        private static readonly Color WindowColor = new Color32(56, 56, 56, 255);
        private static readonly Color SurfaceColor = new Color32(42, 42, 42, 255);
        private static readonly Color SurfaceHoverColor = new Color32(48, 48, 48, 255);
        private static readonly Color BorderColor = new Color32(34, 34, 34, 255);
        private static readonly Color BorderHoverColor = new Color32(82, 82, 82, 255);
        private static readonly Color PrimaryColor = new Color32(250, 204, 21, 255);
        private static readonly Color PrimaryHoverColor = new Color32(234, 179, 8, 255);
        private static readonly Color TextPrimaryColor = new Color32(224, 224, 224, 255);
        private static readonly Color TextSecondaryColor = new Color32(153, 153, 153, 255);
        private static readonly Color TextMutedColor = new Color32(112, 112, 112, 255);
        private static readonly Color CreditsIconColor = new Color32(184, 184, 184, 255);
        private static readonly Color GenerateColor = new Color32(78, 78, 78, 255);
        private static readonly Color GenerateHoverColor = new Color32(92, 92, 92, 255);
        private static readonly Color GenerateActiveColor = new Color32(66, 66, 66, 255);
        private static readonly Color ConfirmedColor = new Color32(52, 211, 153, 255);

        private Texture2D iconKey;
        private Texture2D iconEnter;
        private Texture2D iconCheck;
        private Texture2D iconText;
        private Texture2D iconImage;
        private Texture2D iconImagePlus;
        private Texture2D iconPreview;
        private Texture2D iconBox;
        private Texture2D iconCredits;

        private Texture2D surfaceTexture;
        private Texture2D surfaceHoverTexture;
        private Texture2D confirmedSurfaceTexture;
        private Texture2D generateTexture;
        private Texture2D generateHoverTexture;
        private Texture2D generateActiveTexture;

        private GUIStyle surfaceStyle;
        private GUIStyle confirmedSurfaceStyle;
        private GUIStyle apiKeyTextStyle;
        private GUIStyle apiKeyPlaceholderStyle;
        private GUIStyle promptTextAreaStyle;
        private GUIStyle iconButtonStyle;
        private GUIStyle generateButtonStyle;
        private GUIStyle tabLabelStyle;
        private GUIStyle tabLabelInactiveStyle;
        private GUIStyle sectionTitleStyle;
        private GUIStyle mutedLabelStyle;
        private GUIStyle settingsLabelStyle;
        private GUIStyle balanceLabelStyle;
        private GUIStyle completedLabelStyle;
        private GUIStyle placeholderStyle;
        private GUIStyle transparentBackground;
        private GUIStyle popupStyle;
        private GUIStyle foldoutStyle;

        private readonly List<Texture2D> generatedUiTextures = new List<Texture2D>();

        private static GameObject gameObject;
        private GameObject selectedObject;
        private Editor gameObjectEditor;

        private Vector2 scrollPosition;
        private int latestBalanceRefreshVersion;

        private void OnEnable()
        {
            titleContent = new GUIContent("Tripo API Unity");
            minSize = new Vector2(420, 560);
            maxSize = new Vector2(4000, 4000);

            AssemblyReloadEvents.beforeAssemblyReload -= DestroyPreviewEditor;
            AssemblyReloadEvents.beforeAssemblyReload += DestroyPreviewEditor;

            iconKey = LoadUiTexture("tripo-icon-key.png");
            iconEnter = LoadUiTexture("tripo-icon-enter.png");
            iconCheck = LoadUiTexture("tripo-icon-check.png");
            iconText = LoadUiTexture("tripo-icon-text.png");
            iconImage = LoadUiTexture("tripo-icon-image.png");
            iconImagePlus = LoadUiTexture("tripo-icon-image-plus.png");
            iconPreview = LoadUiTexture("tripo-icon-preview.png");
            iconBox = LoadUiTexture("tripo-icon-box.png");
            iconCredits = LoadUiTexture("coin.png");

            InitializeUiStyles();
            LoadEditorPreferences();
            selectedObject = gameObject;
            if (gameObject != null)
            {
                gameObjectEditor = Editor.CreateEditor(gameObject);
            }
            if (EditorPrefs.HasKey(UserBalancePrefsKey))
            {
                userBalance = EditorPrefs.GetString(UserBalancePrefsKey);
                frozenCredits = Mathf.Max(0, EditorPrefs.GetInt(FrozenCreditsPrefsKey, 0));
            }

            if (EditorPrefs.HasKey(ApiKeyPrefsKey))
            {
                apiKey = EditorPrefs.GetString(ApiKeyPrefsKey);

                if (!apiKey.StartsWith("tsk_"))
                {
                    EditorPrefs.SetString(ApiKeyPrefsKey, "");
                }
                else
                {
                    apiKey = EditorPrefs.GetString(ApiKeyPrefsKey);
                    apiKeyConfirmed = true;
                }
            }

            if (apiKeyConfirmed)
            {
                ScheduleBalanceRefresh(apiKey, false, 0d);
            }
        }

        private void LoadEditorPreferences()
        {
            string savedModel = EditorPrefs.GetString(SelectedModelPrefsKey, modelOptions[0]);
            int savedModelIndex = Array.IndexOf(modelOptions, savedModel);
            selectedModelIndex = savedModelIndex >= 0 ? savedModelIndex : 0;
            quadOptional = EditorPrefs.GetBool(QuadPrefsKey, quadOptional) &&
                TripoModelCapabilities.SupportsQuadMesh(modelOptions[selectedModelIndex]);
            v3TriangleFaceLimit = EditorPrefs.GetInt(
                V3TriangleFaceLimitPrefsKey,
                TripoGenerationLimits.MaxTriangleFaceLimit);
            v3QuadFaceLimit = EditorPrefs.GetInt(
                V3QuadFaceLimitPrefsKey,
                TripoGenerationLimits.MaxQuadFaceLimit);
            v25FaceLimit = EditorPrefs.GetInt(V25FaceLimitPrefsKey, v25FaceLimit);
            p1FaceLimit = EditorPrefs.GetInt(P1FaceLimitPrefsKey, p1FaceLimit);
            v3TriangleFaceLimit = Mathf.Clamp(
                v3TriangleFaceLimit,
                TripoGenerationLimits.MinFaceLimit,
                TripoGenerationLimits.MaxTriangleFaceLimit);
            v3QuadFaceLimit = Mathf.Clamp(
                v3QuadFaceLimit,
                TripoGenerationLimits.MinFaceLimit,
                TripoGenerationLimits.MaxQuadFaceLimit);
            v25FaceLimit = Mathf.Clamp(
                v25FaceLimit,
                TripoGenerationLimits.MinFaceLimit,
                TripoGenerationLimits.MaxV25FaceLimit);
            p1FaceLimit = Mathf.Clamp(
                p1FaceLimit,
                TripoGenerationLimits.MinFaceLimit,
                TripoGenerationLimits.MaxP1FaceLimit);
            faceLimit = GetPreferredFaceLimit(modelOptions[selectedModelIndex], quadOptional);

            textureOptional = EditorPrefs.GetBool(TexturePrefsKey, textureOptional);
            pbrOptional = EditorPrefs.GetBool(PbrPrefsKey, pbrOptional);
            textureQualityOptional = (TextureQuality)Mathf.Clamp(
                EditorPrefs.GetInt(TextureQualityPrefsKey, (int)textureQualityOptional),
                (int)TextureQuality.Standard,
                (int)TextureQuality.Detailed);
            autoSizeOptional = EditorPrefs.GetBool(AutoSizePrefsKey, autoSizeOptional);
            activeGenerationTab = Mathf.Clamp(EditorPrefs.GetInt(ActiveTabPrefsKey, activeGenerationTab), 0, 1);
            advancedSettingsFoldout = EditorPrefs.GetBool(
                AdvancedFoldoutPrefsKey,
                advancedSettingsFoldout);
        }

        private void SaveEditorPreferences()
        {
            EditorPrefs.SetString(SelectedModelPrefsKey, modelOptions[selectedModelIndex]);
            EditorPrefs.SetInt(V3TriangleFaceLimitPrefsKey, v3TriangleFaceLimit);
            EditorPrefs.SetInt(V3QuadFaceLimitPrefsKey, v3QuadFaceLimit);
            EditorPrefs.SetInt(V25FaceLimitPrefsKey, v25FaceLimit);
            EditorPrefs.SetInt(P1FaceLimitPrefsKey, p1FaceLimit);
            EditorPrefs.SetBool(TexturePrefsKey, textureOptional);
            EditorPrefs.SetBool(PbrPrefsKey, pbrOptional);
            EditorPrefs.SetInt(TextureQualityPrefsKey, (int)textureQualityOptional);
            EditorPrefs.SetBool(AutoSizePrefsKey, autoSizeOptional);
            EditorPrefs.SetBool(QuadPrefsKey, quadOptional);
            EditorPrefs.SetInt(ActiveTabPrefsKey, activeGenerationTab);
            EditorPrefs.SetBool(AdvancedFoldoutPrefsKey, advancedSettingsFoldout);
        }

        private int GetPreferredFaceLimit(string modelId, bool quad)
        {
            int value;
            if (string.Equals(modelId, "v2.5-20250123", StringComparison.Ordinal))
            {
                value = v25FaceLimit;
            }
            else if (string.Equals(modelId, "P1-20260311", StringComparison.Ordinal))
            {
                value = p1FaceLimit;
            }
            else
            {
                value = quad ? v3QuadFaceLimit : v3TriangleFaceLimit;
            }

            return TripoGenerationLimits.ClampFaceLimit(modelId, quad, value);
        }

        private void SetPreferredFaceLimit(string modelId, bool quad, int value)
        {
            value = TripoGenerationLimits.ClampFaceLimit(modelId, quad, value);
            if (string.Equals(modelId, "v2.5-20250123", StringComparison.Ordinal))
            {
                v25FaceLimit = value;
            }
            else if (string.Equals(modelId, "P1-20260311", StringComparison.Ordinal))
            {
                p1FaceLimit = value;
            }
            else if (quad)
            {
                v3QuadFaceLimit = value;
            }
            else
            {
                v3TriangleFaceLimit = value;
            }
        }

        private static Texture2D LoadUiTexture(string fileName)
        {
            return EditorGUIUtility.Load(
                "Packages/com.tripo3d.tripo-api-unity/Editor/EditorTextures/" + fileName) as Texture2D;
        }

        private void InitializeUiStyles()
        {
            DestroyGeneratedUiTextures();
            surfaceTexture = CreateRoundedUiTexture(SurfaceColor, BorderColor);
            surfaceHoverTexture = CreateRoundedUiTexture(SurfaceHoverColor, BorderHoverColor);
            confirmedSurfaceTexture = CreateRoundedUiTexture(new Color32(39, 55, 48, 255), new Color32(42, 111, 81, 255));
            generateTexture = CreateRoundedUiTexture(GenerateColor, BorderHoverColor, 5);
            generateHoverTexture = CreateRoundedUiTexture(GenerateHoverColor, TextMutedColor, 5);
            generateActiveTexture = CreateRoundedUiTexture(GenerateActiveColor, BorderColor, 5);

            surfaceStyle = new GUIStyle
            {
                border = new RectOffset(10, 10, 10, 10),
                normal = { background = surfaceTexture }
            };
            confirmedSurfaceStyle = new GUIStyle(surfaceStyle);
            confirmedSurfaceStyle.normal.background = confirmedSurfaceTexture;

            apiKeyTextStyle = new GUIStyle
            {
                alignment = TextAnchor.MiddleLeft,
                clipping = TextClipping.Clip,
                fontSize = 12,
                padding = new RectOffset(0, 8, 2, 0),
                normal = { textColor = TextSecondaryColor },
                focused = { textColor = TextPrimaryColor }
            };
            apiKeyPlaceholderStyle = new GUIStyle(apiKeyTextStyle);
            apiKeyPlaceholderStyle.normal.textColor = TextSecondaryColor;

            promptTextAreaStyle = new GUIStyle
            {
                border = new RectOffset(10, 10, 10, 10),
                padding = new RectOffset(14, 14, 12, 12),
                alignment = TextAnchor.UpperLeft,
                wordWrap = true,
                fontSize = 14,
                normal = { background = surfaceTexture, textColor = TextPrimaryColor },
                focused = { background = surfaceHoverTexture, textColor = TextPrimaryColor }
            };

            iconButtonStyle = new GUIStyle
            {
                border = new RectOffset(10, 10, 10, 10),
                alignment = TextAnchor.MiddleCenter,
                normal = { background = surfaceTexture },
                hover = { background = surfaceHoverTexture },
                active = { background = surfaceHoverTexture }
            };

            generateButtonStyle = new GUIStyle
            {
                border = new RectOffset(8, 8, 8, 8),
                alignment = TextAnchor.MiddleCenter,
                fontStyle = FontStyle.Bold,
                fontSize = 14,
                normal = { background = generateTexture, textColor = Color.white },
                hover = { background = generateHoverTexture, textColor = Color.white },
                active = { background = generateActiveTexture, textColor = Color.white },
                focused = { background = generateTexture, textColor = Color.white }
            };

            tabLabelStyle = CreateLabelStyle(TextPrimaryColor, 12, FontStyle.Bold, TextAnchor.MiddleLeft);
            tabLabelInactiveStyle = CreateLabelStyle(TextSecondaryColor, 12, FontStyle.Bold, TextAnchor.MiddleLeft);
            sectionTitleStyle = CreateLabelStyle(TextPrimaryColor, 12, FontStyle.Bold, TextAnchor.MiddleLeft);
            mutedLabelStyle = CreateLabelStyle(TextSecondaryColor, 11, FontStyle.Normal, TextAnchor.MiddleLeft);
            settingsLabelStyle = CreateLabelStyle(TextSecondaryColor, 10, FontStyle.Bold, TextAnchor.MiddleLeft);
            balanceLabelStyle = CreateLabelStyle(PrimaryColor, 12, FontStyle.Bold, TextAnchor.MiddleLeft);
            completedLabelStyle = CreateLabelStyle(ConfirmedColor, 12, FontStyle.Bold, TextAnchor.MiddleLeft);
            placeholderStyle = CreateLabelStyle(TextMutedColor, 14, FontStyle.Normal, TextAnchor.UpperLeft);
            placeholderStyle.padding = new RectOffset(14, 14, 12, 12);

            transparentBackground = new GUIStyle(surfaceStyle);
        }

        private static GUIStyle CreateLabelStyle(Color color, int fontSize, FontStyle fontStyle, TextAnchor alignment)
        {
            return new GUIStyle
            {
                fontSize = fontSize,
                fontStyle = fontStyle,
                alignment = alignment,
                clipping = TextClipping.Clip,
                normal = { textColor = color }
            };
        }

        private Texture2D CreateRoundedUiTexture(Color fill, Color border, int radius = 8)
        {
            const int size = 32;
            const int borderWidth = 1;
            Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp
            };

            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    bool outer = IsInsideRoundedRect(x, y, size, size, radius);
                    bool inner = IsInsideRoundedRect(
                        x - borderWidth,
                        y - borderWidth,
                        size - borderWidth * 2,
                        size - borderWidth * 2,
                        Mathf.Max(0, radius - borderWidth));
                    texture.SetPixel(x, y, !outer ? Color.clear : inner ? fill : border);
                }
            }

            texture.Apply(false, false);
            generatedUiTextures.Add(texture);
            return texture;
        }

        private static bool IsInsideRoundedRect(int x, int y, int width, int height, int radius)
        {
            if (x < 0 || y < 0 || x >= width || y >= height) return false;
            if (radius <= 0) return true;

            float centerX = Mathf.Clamp(x, radius, width - radius - 1);
            float centerY = Mathf.Clamp(y, radius, height - radius - 1);
            float dx = x - centerX;
            float dy = y - centerY;
            return dx * dx + dy * dy <= radius * radius;
        }

        private void DestroyGeneratedUiTextures()
        {
            foreach (Texture2D texture in generatedUiTextures)
            {
                if (texture != null) DestroyImmediate(texture);
            }
            generatedUiTextures.Clear();
        }

        private void OnDisable()
        {
            SaveEditorPreferences();
            AssemblyReloadEvents.beforeAssemblyReload -= DestroyPreviewEditor;
            DestroyPreviewEditor();
            if (uploadedImage != null)
            {
                DestroyImmediate(uploadedImage);
                uploadedImage = null;
            }
            DestroyGeneratedUiTextures();
        }

        private static void OnEditorFocusChanged(bool hasFocus)
        {
            if (!hasFocus) return;
            EnsureCoroutineSchedulerRegistered();
            RepaintQueueWindows();
            EditorApplication.QueuePlayerLoopUpdate();
        }

        // Editor.CreateEditor(gameObject) builds Unity's internal GameObjectInspector, whose OnDisable
        // reads a cached SerializedProperty. If it is destroyed after Unity has disposed that
        // SerializedObject (window teardown / domain reload), Unity throws + logs
        // "SerializedObject of SerializedProperty has been Disposed" from GameObjectInspector.OnDisable.
        // That throw happens inside Unity's native DestroyImmediate callback and is logged by Unity
        // itself, so the try/catch below can't actually suppress it — the real fix is calling this
        // pre-reload (see AssemblyReloadEvents subscription in OnEnable) while the SerializedObject is
        // still alive. The try/catch stays as a cheap extra guard. Single helper keeps all destroy sites consistent.
        private void DestroyPreviewEditor()
        {
            if (gameObjectEditor == null) return;
            try
            {
                DestroyImmediate(gameObjectEditor);
            }
            catch (NullReferenceException)
            {
                // known GameObjectInspector.OnDisable teardown bug — harmless, editor is going away
            }
            gameObjectEditor = null;
        }


        private void ApplyBalance(BalanceResponseData balance)
        {
            // The v3 response already reports available credits; frozen is informational.
            userBalance = Mathf.Max(0, balance.balance).ToString();
            frozenCredits = Mathf.Max(0, balance.frozen);
            EditorPrefs.SetString(ApiKeyPrefsKey, apiKey);
            EditorPrefs.SetString(UserBalancePrefsKey, userBalance);
            EditorPrefs.SetInt(FrozenCreditsPrefsKey, frozenCredits);
            apiKeyConfirmed = true;
            Repaint();
        }

        public void OnGUI()
        {
            EnsureEditorFonts();
            EditorGUI.DrawRect(new Rect(0f, 0f, position.width, position.height), WindowColor);

            float scrollbarWidth = Mathf.Max(GUI.skin.verticalScrollbar.fixedWidth, 16f);
            float contentWidth = Mathf.Min(760f, Mathf.Max(320f, position.width - scrollbarWidth - 40f));

            scrollPosition.x = 0f;
            scrollPosition = GUILayout.BeginScrollView(
                scrollPosition,
                GUIStyle.none,
                GUI.skin.verticalScrollbar,
                GUILayout.Width(position.width),
                GUILayout.Height(position.height));

            GUILayout.BeginHorizontal();
            GUILayout.FlexibleSpace();
            GUILayout.BeginVertical(GUILayout.Width(contentWidth));
            GUILayout.Space(20f);

            DrawApiKeyBar();
            GUILayout.Space(24f);
            DrawSeparator();
            GUILayout.Space(20f);
            DrawGenerationTabs();
            GUILayout.Space(16f);

            if (activeGenerationTab == 0) DrawTextInput();
            else DrawImageInput();

            GUILayout.Space(12f);
            DrawGenerationSettings();
            GUILayout.Space(16f);
            DrawGenerateAction();

            if (generationJobs.Count > 0)
            {
                GUILayout.Space(20f);
                DrawTaskQueue();
            }

            GUILayout.Space(24f);
            DrawSeparator();
            GUILayout.Space(20f);
            DrawResultPreview(contentWidth);
            GUILayout.Space(20f);

            GUILayout.EndVertical();
            GUILayout.FlexibleSpace();
            GUILayout.EndHorizontal();
            GUILayout.EndScrollView();
        }

        private void EnsureEditorFonts()
        {
            Font editorFont = EditorStyles.standardFont != null ? EditorStyles.standardFont : GUI.skin.font;
            GUIStyle[] styles =
            {
                apiKeyTextStyle,
                apiKeyPlaceholderStyle,
                promptTextAreaStyle,
                generateButtonStyle,
                tabLabelStyle,
                tabLabelInactiveStyle,
                sectionTitleStyle,
                mutedLabelStyle,
                settingsLabelStyle,
                balanceLabelStyle,
                completedLabelStyle,
                placeholderStyle
            };

            foreach (GUIStyle style in styles)
            {
                if (style != null && style.font == null) style.font = editorFont;
            }

            if (popupStyle == null)
            {
                popupStyle = new GUIStyle(EditorStyles.popup)
                {
                    fontSize = 11,
                    alignment = TextAnchor.MiddleLeft
                };
            }

            if (foldoutStyle == null)
            {
                foldoutStyle = new GUIStyle(EditorStyles.foldout)
                {
                    fontSize = 10,
                    fontStyle = FontStyle.Bold
                };
                foldoutStyle.normal.textColor = TextSecondaryColor;
                foldoutStyle.onNormal.textColor = TextPrimaryColor;
                foldoutStyle.focused.textColor = TextSecondaryColor;
                foldoutStyle.onFocused.textColor = TextPrimaryColor;
            }
        }

        private void DrawApiKeyBar()
        {
            Rect rowRect = GUILayoutUtility.GetRect(10f, 40f, GUILayout.ExpandWidth(true));

            const float actionWidth = 40f;
            const float balanceWidth = 92f;
            const float componentGap = 8f;
            float trailingWidth = actionWidth + componentGap;
            if (apiKeyConfirmed) trailingWidth += balanceWidth + componentGap;

            Rect barRect = new Rect(
                rowRect.x,
                rowRect.y,
                Mathf.Max(160f, rowRect.width - trailingWidth),
                rowRect.height);
            Rect actionRect = new Rect(
                barRect.xMax + componentGap,
                rowRect.y,
                actionWidth,
                rowRect.height);
            Rect balanceRect = apiKeyConfirmed
                ? new Rect(actionRect.xMax + componentGap, rowRect.y, balanceWidth, rowRect.height)
                : Rect.zero;

            GUI.Box(barRect, GUIContent.none, apiKeyConfirmed ? confirmedSurfaceStyle : surfaceStyle);
            if (apiKeyConfirmed)
            {
                GUI.Box(balanceRect, GUIContent.none, surfaceStyle);
            }

            Rect keyIconRect = new Rect(barRect.x + 12f, barRect.y + 12f, 16f, 16f);
            DrawIcon(keyIconRect, iconKey, apiKeyConfirmed ? ConfirmedColor : TextMutedColor);

            float fieldHeight = EditorGUIUtility.singleLineHeight;
            Rect fieldRect = new Rect(
                keyIconRect.xMax + 10f,
                barRect.center.y - fieldHeight * 0.5f,
                Mathf.Max(20f, barRect.xMax - 10f - (keyIconRect.xMax + 10f)),
                fieldHeight);

            bool confirmByEnter =
                !apiKeyConfirmed
                && Event.current.type == EventType.KeyDown
                && (Event.current.keyCode == KeyCode.Return || Event.current.keyCode == KeyCode.KeypadEnter)
                && GUI.GetNameOfFocusedControl() == "ApiKeyField";

            if (confirmByEnter)
            {
                GUI.FocusControl(null);
                Event.current.Use();
            }

            apiKeyTextStyle.normal.textColor = apiKeyConfirmed ? ConfirmedColor : TextSecondaryColor;
            apiKeyTextStyle.focused.textColor = apiKeyConfirmed ? ConfirmedColor : TextPrimaryColor;
            EditorGUI.BeginDisabledGroup(apiKeyConfirmed);
            GUI.SetNextControlName("ApiKeyField");
            apiKey = GUI.PasswordField(fieldRect, apiKey, '\u2022', apiKeyTextStyle);
            EditorGUI.EndDisabledGroup();

            bool apiKeyFieldFocused = GUI.GetNameOfFocusedControl() == "ApiKeyField";
            if (string.IsNullOrEmpty(apiKey) && !apiKeyFieldFocused)
            {
                GUI.Label(fieldRect, "API key, begins with tsk_...", apiKeyPlaceholderStyle);
            }

            if (apiKeyConfirmed)
            {
                DrawIcon(
                    new Rect(balanceRect.x + 10f, balanceRect.y + 12f, 16f, 16f),
                    iconCredits,
                    CreditsIconColor);
                string balanceText = string.IsNullOrEmpty(userBalance) ? "----" : userBalance;
                DrawAutoSizedLabel(
                    new Rect(balanceRect.x + 34f, balanceRect.y, balanceRect.width - 40f, balanceRect.height),
                    balanceText,
                    balanceLabelStyle,
                    $"Available: {balanceText}\nFrozen by active tasks: {frozenCredits}");
            }

            string actionTooltip = apiKeyConfirmed ? "Edit API key" : "Confirm API key";
            if (GUI.Button(actionRect, new GUIContent(string.Empty, actionTooltip), iconButtonStyle))
            {
                ConfirmApiKey();
            }

            Texture2D actionIcon = apiKeyConfirmed ? iconCheck : iconEnter;
            DrawIcon(
                new Rect(actionRect.x + 12f, actionRect.y + 12f, 16f, 16f),
                actionIcon,
                apiKeyConfirmed ? ConfirmedColor : TextPrimaryColor);

            if (confirmByEnter) ConfirmApiKey();
        }

        private void ConfirmApiKey()
        {
            if (apiKeyConfirmed)
            {
                apiKeyConfirmed = false;
                userBalance = string.Empty;
                frozenCredits = 0;
                latestBalanceRefreshVersion = 0;
                EditorPrefs.SetString(ApiKeyPrefsKey, string.Empty);
                EditorPrefs.SetString(UserBalancePrefsKey, string.Empty);
                EditorPrefs.SetInt(FrozenCreditsPrefsKey, 0);
                Repaint();
                return;
            }

            if (string.IsNullOrWhiteSpace(apiKey))
            {
                EditorUtility.DisplayDialog("API Key Required", "Enter a Tripo API key before confirming.", "OK");
                return;
            }

            ScheduleBalanceRefresh(apiKey, true, 0d);
        }

        private void DrawSeparator()
        {
            Rect separatorRect = GUILayoutUtility.GetRect(10f, 1f, GUILayout.ExpandWidth(true));
            EditorGUI.DrawRect(separatorRect, SurfaceColor);
        }

        private void DrawGenerationTabs()
        {
            Rect tabsRect = GUILayoutUtility.GetRect(10f, 44f, GUILayout.ExpandWidth(true));
            float tabWidth = tabsRect.width * 0.5f;
            Rect textTabRect = new Rect(tabsRect.x, tabsRect.y, tabWidth, tabsRect.height);
            Rect imageTabRect = new Rect(textTabRect.xMax, tabsRect.y, tabWidth, tabsRect.height);

            DrawGenerationTab(textTabRect, 0, iconText, "TEXT TO MODEL");
            DrawGenerationTab(imageTabRect, 1, iconImage, "IMAGE TO MODEL");
            EditorGUI.DrawRect(new Rect(tabsRect.x, tabsRect.yMax - 1f, tabsRect.width, 1f), SurfaceColor);
        }

        private void DrawGenerationTab(Rect rect, int tabIndex, Texture2D icon, string title)
        {
            bool active = activeGenerationTab == tabIndex;
            EditorGUIUtility.AddCursorRect(rect, MouseCursor.Link);
            if (GUI.Button(rect, GUIContent.none, GUIStyle.none))
            {
                activeGenerationTab = tabIndex;
                SaveEditorPreferences();
                GUI.FocusControl(null);
            }

            Color tint = active ? TextPrimaryColor : TextSecondaryColor;
            Rect iconRect = new Rect(rect.x + 16f, rect.y + 12f, 18f, 18f);
            DrawIcon(iconRect, icon, tint);
            Rect labelRect = new Rect(iconRect.xMax + 9f, rect.y, rect.width - 48f, rect.height - 2f);
            GUI.Label(labelRect, title, active ? tabLabelStyle : tabLabelInactiveStyle);

            if (active)
            {
                EditorGUI.DrawRect(new Rect(rect.x, rect.yMax - 3f, rect.width, 3f), PrimaryColor);
            }
        }

        private void DrawTextInput()
        {
            Rect inputRect = GUILayoutUtility.GetRect(10f, 160f, GUILayout.ExpandWidth(true));
            GUI.SetNextControlName("TextPromptField");
            textPrompt = GUI.TextArea(inputRect, textPrompt, promptTextAreaStyle);
            if (string.IsNullOrEmpty(textPrompt))
            {
                GUI.Label(inputRect, "Enter the text prompt here...", placeholderStyle);
            }
        }

        private void DrawImageInput()
        {
            Rect uploadRect = GUILayoutUtility.GetRect(10f, 160f, GUILayout.ExpandWidth(true));
            EditorGUIUtility.AddCursorRect(uploadRect, MouseCursor.Link);

            if (GUI.Button(uploadRect, GUIContent.none, surfaceStyle))
            {
                string path = EditorUtility.OpenFilePanel("Select an Image", "", "jpg,png");
                if (!string.IsNullOrEmpty(path))
                {
                    imagePath = path;
                    if (uploadedImage != null) DestroyImmediate(uploadedImage);
                    uploadedImage = new Texture2D(2, 2)
                    {
                        hideFlags = HideFlags.HideAndDontSave
                    };
                    uploadedImage.LoadImage(File.ReadAllBytes(imagePath));
                }
            }

            DrawDashedBorder(uploadRect, BorderHoverColor);
            if (uploadedImage != null)
            {
                Rect imageRect = new Rect(
                    uploadRect.x + 12f,
                    uploadRect.y + 12f,
                    uploadRect.width - 24f,
                    uploadRect.height - 36f);
                GUI.DrawTexture(imageRect, uploadedImage, ScaleMode.ScaleToFit, true);

                Rect fileRect = new Rect(uploadRect.x + 12f, uploadRect.yMax - 23f, uploadRect.width - 24f, 18f);
                GUI.Label(fileRect, Path.GetFileName(imagePath), mutedLabelStyle);
            }
            else
            {
                const float iconSize = 42f;
                Rect iconRect = new Rect(
                    uploadRect.center.x - iconSize * 0.5f,
                    uploadRect.center.y - iconSize * 0.5f,
                    iconSize,
                    iconSize);
                DrawIcon(iconRect, iconImagePlus, TextMutedColor);
            }
        }

        private void DrawGenerationSettings()
        {
            EditorGUI.BeginChangeCheck();

            Rect modelRow = GUILayoutUtility.GetRect(10f, 34f, GUILayout.ExpandWidth(true));
            GUI.Box(modelRow, GUIContent.none, surfaceStyle);
            GUI.Label(new Rect(modelRow.x + 12f, modelRow.y, 46f, modelRow.height), "MODEL", settingsLabelStyle);

            const float advancedWidth = 92f;
            Rect popupRect = new Rect(
                modelRow.x + 58f,
                modelRow.y + 6f,
                Mathf.Max(90f, modelRow.width - 70f - advancedWidth),
                modelRow.height - 12f);
            int previousModelIndex = selectedModelIndex;
            selectedModelIndex = EditorGUI.Popup(popupRect, selectedModelIndex, modelOptions, popupStyle);
            string selectedModelId = modelOptions[selectedModelIndex];
            bool supportsV30PlusParams =
                TripoModelCapabilities.SupportsAdvancedGeneration(selectedModelId);
            bool supportsQuadMesh = TripoModelCapabilities.SupportsQuadMesh(selectedModelId);
            if (!supportsQuadMesh)
            {
                quadOptional = false;
            }

            if (selectedModelIndex != previousModelIndex)
            {
                faceLimit = GetPreferredFaceLimit(selectedModelId, quadOptional);
            }

            faceLimit = TripoGenerationLimits.ClampFaceLimit(
                selectedModelId,
                quadOptional,
                faceLimit);

            Rect foldoutRect = new Rect(
                modelRow.xMax - advancedWidth,
                modelRow.y + 7f,
                advancedWidth - 8f,
                20f);
            advancedSettingsFoldout = EditorGUI.Foldout(
                foldoutRect,
                advancedSettingsFoldout,
                "ADVANCED",
                true,
                foldoutStyle);

            if (!advancedSettingsFoldout)
            {
                if (EditorGUI.EndChangeCheck()) SaveEditorPreferences();
                return;
            }

            CheckAndCloseBumpMapSettingsFixingWindow();
            GUILayout.Space(8f);
            float settingsHeight = 94f;
            if (supportsV30PlusParams) settingsHeight += 56f;
            if (supportsQuadMesh) settingsHeight += 28f;
            Rect settingsRect = GUILayoutUtility.GetRect(10f, settingsHeight, GUILayout.ExpandWidth(true));
            GUI.Box(settingsRect, GUIContent.none, surfaceStyle);

            float left = settingsRect.x + 12f;
            float right = settingsRect.xMax - 12f;
            float rowY = settingsRect.y + 10f;
            const float labelWidth = 118f;
            float controlLeft = left + labelWidth;
            float controlWidth = Mathf.Clamp(right - controlLeft, 90f, 180f);

            GUI.Label(new Rect(left, rowY, 90f, 20f), "FACE LIMIT", settingsLabelStyle);
            TripoGenerationLimits.GetFaceLimitRange(
                selectedModelId,
                quadOptional,
                out int minimumFaceLimit,
                out int maximumFaceLimit);
            faceLimit = Mathf.Clamp(faceLimit, minimumFaceLimit, maximumFaceLimit);
            Rect sliderRect = new Rect(controlLeft, rowY, Mathf.Max(50f, controlWidth - 72f), 20f);
            EditorGUI.BeginChangeCheck();
            faceLimit = DrawLogarithmicIntSlider(
                sliderRect,
                faceLimit,
                minimumFaceLimit,
                maximumFaceLimit);
            Rect faceLimitValueRect = new Rect(sliderRect.xMax + 6f, rowY, 66f, 20f);
            faceLimit = Mathf.Clamp(
                EditorGUI.IntField(faceLimitValueRect, faceLimit),
                minimumFaceLimit,
                maximumFaceLimit);
            if (EditorGUI.EndChangeCheck())
            {
                SetPreferredFaceLimit(selectedModelId, quadOptional, faceLimit);
            }
            rowY += 28f;

            textureOptional = EditorGUI.ToggleLeft(
                new Rect(left, rowY, right - left, 20f),
                new GUIContent("Texture", "Generate textures"),
                textureOptional);
            rowY += 28f;

            pbrOptional = EditorGUI.ToggleLeft(
                new Rect(left, rowY, right - left, 20f),
                new GUIContent("PBR", "Generate PBR materials"),
                pbrOptional);
            rowY += 28f;

            if (supportsV30PlusParams)
            {
                GUI.Label(
                    new Rect(left, rowY, labelWidth - 8f, 20f),
                    "TEXTURE QUALITY",
                    settingsLabelStyle);
                textureQualityOptional = (TextureQuality)EditorGUI.EnumPopup(
                    new Rect(controlLeft, rowY, controlWidth, 20f),
                    textureQualityOptional);
                rowY += 28f;
                autoSizeOptional = EditorGUI.ToggleLeft(
                    new Rect(left, rowY, right - left, 20f),
                    new GUIContent("Auto Size", "Scale the model to real-world dimensions"),
                    autoSizeOptional);
                rowY += 28f;
            }

            if (supportsQuadMesh)
            {
                GUI.Label(new Rect(left, rowY, labelWidth - 8f, 20f), "TOPOLOGY", settingsLabelStyle);
                bool previousQuad = quadOptional;
                int topologyIndex = previousQuad ? 1 : 0;
                topologyIndex = EditorGUI.Popup(
                    new Rect(controlLeft, rowY, controlWidth, 20f),
                    topologyIndex,
                    topologyOptions,
                    popupStyle);
                quadOptional = topologyIndex == 1;
                if (quadOptional != previousQuad)
                {
                    faceLimit = GetPreferredFaceLimit(selectedModelId, quadOptional);
                }
            }
            if (EditorGUI.EndChangeCheck()) SaveEditorPreferences();
        }

        private void DrawGenerateAction()
        {
            Rect actionRow = GUILayoutUtility.GetRect(10f, 40f, GUILayout.ExpandWidth(true));
            Rect buttonRect = new Rect(
                actionRow.x,
                actionRow.y + 2f,
                actionRow.width,
                36f);

            bool previousEnabled = GUI.enabled;
            bool queueHasCapacity = CanQueueAnotherJob();
            GUI.enabled = apiKeyConfirmed && queueHasCapacity;
            EditorGUIUtility.AddCursorRect(buttonRect, GUI.enabled ? MouseCursor.Link : MouseCursor.Arrow);
            string generateTooltip = queueHasCapacity
                ? "Submit another independent Tripo generation job"
                : $"The task queue is full ({MaxQueuedJobs}/{MaxQueuedJobs}). Wait for a task to finish.";
            if (GUI.Button(
                buttonRect,
                new GUIContent("Generate", generateTooltip),
                generateButtonStyle))
            {
                if (activeGenerationTab == 0) TryStartTextGeneration();
                else TryStartImageGeneration();
            }
            GUI.enabled = previousEnabled;
        }

        private void DrawTaskQueue()
        {
            Rect headerRect = GUILayoutUtility.GetRect(10f, 28f, GUILayout.ExpandWidth(true));
            int activeJobCount = GetActiveJobCount();
            GUI.Label(
                new Rect(headerRect.x + 2f, headerRect.y, Mathf.Max(120f, headerRect.width - 118f), headerRect.height),
                $"TASK QUEUE ({activeJobCount}/{MaxQueuedJobs})",
                sectionTitleStyle);

            bool hasCompletedJobs = generationJobs.Exists(
                job => job.Stage == GenerationJobStage.Completed);
            Rect clearRect = new Rect(headerRect.xMax - 110f, headerRect.y + 2f, 108f, 22f);
            bool previousEnabled = GUI.enabled;
            GUI.enabled = hasCompletedJobs;
            if (GUI.Button(clearRect, "Clear Finished"))
            {
                generationJobs.RemoveAll(job => job.Stage == GenerationJobStage.Completed);
                RepaintQueueWindows();
            }
            GUI.enabled = previousEnabled;

            for (int i = generationJobs.Count - 1; i >= 0; i--)
            {
                DrawTaskQueueItem(generationJobs[i]);
                GUILayout.Space(6f);
            }
        }

        private static bool CanQueueAnotherJob()
        {
            return GetActiveJobCount() < MaxQueuedJobs;
        }

        private static int GetActiveJobCount()
        {
            int count = 0;
            foreach (GenerationJob job in generationJobs)
            {
                if (!job.IsTerminal) count++;
            }

            return count;
        }

        private static bool TryReserveQueueSlot(bool showDialog)
        {
            if (GetActiveJobCount() >= MaxQueuedJobs)
            {
                const string message =
                    "The platform allows up to 10 concurrent tasks. Wait for a task to finish before generating another model.";
                if (showDialog)
                {
                    EditorUtility.DisplayDialog("Task Queue Full", message, "OK");
                }
                else
                {
                    Debug.LogWarning(message);
                }
                return false;
            }

            return true;
        }

        private void DrawTaskQueueItem(GenerationJob job)
        {
            Rect itemRect = GUILayoutUtility.GetRect(10f, 76f, GUILayout.ExpandWidth(true));
            bool isCompleted = job.Stage == GenerationJobStage.Completed;
            GUI.Box(itemRect, GUIContent.none, isCompleted ? confirmedSurfaceStyle : surfaceStyle);

            const float padding = 12f;
            float textWidth = itemRect.width - padding * 2f;
            float progress = Mathf.Clamp01(job.Progress);
            string typeLabel = job.IsTextToModel ? "TEXT" : "IMAGE";
            string modelLabel = GetModelDisplayLabel(job.ModelId);
            GUI.Label(
                new Rect(itemRect.x + padding, itemRect.y + 8f, 132f, 18f),
                new GUIContent($"#{job.Number}  {typeLabel}  {modelLabel}", job.ModelId),
                settingsLabelStyle);
            GUI.Label(
                new Rect(itemRect.x + 144f, itemRect.y + 8f, Mathf.Max(80f, itemRect.width - 156f), 18f),
                GetJobStatusText(job, EditorApplication.timeSinceStartup, progress),
                isCompleted ? completedLabelStyle : mutedLabelStyle);
            GUI.Label(
                new Rect(itemRect.x + padding, itemRect.y + 29f, textWidth, 18f),
                new GUIContent(job.InputSummary, job.InputSummary),
                mutedLabelStyle);

            string taskId = job.CurrentTaskId;
            string detail = !string.IsNullOrEmpty(job.ErrorMessage)
                ? job.ErrorMessage
                : !string.IsNullOrEmpty(job.OutputAssetPath)
                    ? job.OutputAssetPath
                    : string.IsNullOrEmpty(taskId)
                        ? job.ModelId
                        : "Task: " + taskId;
            GUI.Label(
                new Rect(itemRect.x + padding, itemRect.y + 49f, textWidth, 17f),
                new GUIContent(detail, detail),
                settingsLabelStyle);

            Rect trackRect = new Rect(itemRect.x + 1f, itemRect.yMax - 4f, itemRect.width - 2f, 3f);
            EditorGUI.DrawRect(trackRect, BorderColor);
            if (progress > 0f)
            {
                Color progressColor = isCompleted ? ConfirmedColor : PrimaryColor;
                EditorGUI.DrawRect(
                    new Rect(trackRect.x, trackRect.y, trackRect.width * progress, trackRect.height),
                    progressColor);
            }
        }

        private static string GetModelDisplayLabel(string modelId)
        {
            if (string.IsNullOrEmpty(modelId))
            {
                return "Unknown";
            }

            int versionSeparator = modelId.IndexOf('-');
            return versionSeparator > 0 ? modelId.Substring(0, versionSeparator) : modelId;
        }

        private static string GetJobStatusText(
            GenerationJob job,
            double now,
            float overallProgress)
        {
            string statusText;
            switch (job.Stage)
            {
                case GenerationJobStage.Uploading:
                    statusText = "Uploading image...";
                    break;
                case GenerationJobStage.Submitting:
                    statusText = "Submitting...";
                    break;
                case GenerationJobStage.Generating:
                    statusText = $"Generating {overallProgress * 100f:0}%";
                    break;
                case GenerationJobStage.Converting:
                    statusText = $"Converting {overallProgress * 100f:0}%";
                    break;
                case GenerationJobStage.Downloading:
                    statusText = "Downloading...";
                    break;
                case GenerationJobStage.Importing:
                    statusText = "Importing...";
                    break;
                case GenerationJobStage.Completed:
                    return "Completed";
                case GenerationJobStage.Failed:
                    return "Failed";
                default:
                    return job.Stage.ToString();
            }

            if ((job.Stage == GenerationJobStage.Generating ||
                 job.Stage == GenerationJobStage.Converting) &&
                job.LastProgressChangeTime > 0d &&
                now - job.LastProgressChangeTime >= ProgressStallNoticeSeconds)
            {
                statusText += " (waiting for server)";
            }

            return statusText;
        }

        private void TryStartTextGeneration()
        {
            if (string.IsNullOrWhiteSpace(textPrompt))
            {
                EditorUtility.DisplayDialog("Empty Prompt", "Please enter a text prompt before generating.", "OK");
                return;
            }

            GUI.FocusControl(null);
            GenerationJob job = CreateGenerationJob(true);
            if (job == null) return;
            StartEditorCoroutine(TextPromptsToModel(job), job);
        }

        private void TryStartImageGeneration()
        {
            if (string.IsNullOrEmpty(imagePath))
            {
                EditorUtility.DisplayDialog("Image Required", "Select a JPG or PNG image before generating.", "OK");
                return;
            }
            GenerationJob job = CreateGenerationJob(false);
            if (job == null) return;
            StartEditorCoroutine(ImageToModelCoroutine(job), job);
        }

        private GenerationJob CreateGenerationJob(bool isTextToModel)
        {
            if (!TryReserveQueueSlot(true)) return null;

            string selectedModelId = modelOptions[selectedModelIndex];
            bool requestQuad = TripoModelCapabilities.SupportsQuadMesh(selectedModelId) && quadOptional;
            int requestedFaceLimit = TripoGenerationLimits.ClampFaceLimit(
                selectedModelId,
                requestQuad,
                faceLimit);
            faceLimit = requestedFaceLimit;

            GenerationJob job = new GenerationJob
            {
                Number = nextGenerationJobNumber++,
                IsTextToModel = isTextToModel,
                InputSummary = isTextToModel
                    ? textPrompt.Trim()
                    : Path.GetFileName(imagePath),
                Prompt = isTextToModel ? textPrompt : string.Empty,
                ImagePath = isTextToModel ? string.Empty : imagePath,
                ApiKey = apiKey,
                ModelId = selectedModelId,
                FaceLimit = requestedFaceLimit,
                Texture = textureOptional,
                Pbr = pbrOptional,
                TextureQuality = textureQualityOptions[(int)textureQualityOptional],
                AutoSize = autoSizeOptional,
                Quad = requestQuad,
                GenerationOutputIsFbx = requestQuad,
                LastActivityTime = EditorApplication.timeSinceStartup,
                LastProgressChangeTime = EditorApplication.timeSinceStartup,
                Stage = isTextToModel
                    ? GenerationJobStage.Submitting
                    : GenerationJobStage.Uploading
            };
            generationJobs.Add(job);
            Repaint();
            return job;
        }

        private static int DrawLogarithmicIntSlider(
            Rect rect,
            int value,
            int minimum,
            int maximum)
        {
            if (maximum <= minimum) return minimum;
            float logMinimum = Mathf.Log10(Mathf.Max(1, minimum));
            float logMaximum = Mathf.Log10(Mathf.Max(1, maximum));
            float logValue = Mathf.Log10(Mathf.Clamp(value, minimum, maximum));
            float normalized = Mathf.InverseLerp(logMinimum, logMaximum, logValue);
            normalized = GUI.HorizontalSlider(rect, normalized, 0f, 1f);
            return Mathf.Clamp(
                Mathf.RoundToInt(Mathf.Pow(10f, Mathf.Lerp(logMinimum, logMaximum, normalized))),
                minimum,
                maximum);
        }

        private void DrawResultPreview(float contentWidth)
        {
            Rect headerRect = GUILayoutUtility.GetRect(10f, 30f, GUILayout.ExpandWidth(true));
            Rect iconRect = new Rect(headerRect.x + 2f, headerRect.y + 7f, 16f, 16f);
            DrawIcon(iconRect, iconPreview, TextSecondaryColor);

            Rect titleRect = new Rect(iconRect.xMax + 8f, headerRect.y, 132f, headerRect.height);
            GUI.Label(titleRect, "RESULT PREVIEW", sectionTitleStyle);

            Rect objectRect = new Rect(
                titleRect.xMax + 8f,
                headerRect.y + 2f,
                Mathf.Max(120f, headerRect.xMax - (titleRect.xMax + 8f)),
                26f);
            selectedObject = (GameObject)EditorGUI.ObjectField(objectRect, gameObject, typeof(GameObject), false);

            if (selectedObject != gameObject)
            {
                gameObject = selectedObject;
                DestroyPreviewEditor();
                if (gameObject != null) gameObjectEditor = Editor.CreateEditor(gameObject);
            }

            GUILayout.Space(10f);
            float previewHeight = Mathf.Clamp(contentWidth * 0.58f, 224f, 420f);
            Rect previewRect = GUILayoutUtility.GetRect(10f, previewHeight, GUILayout.ExpandWidth(true));
            GUI.Box(previewRect, GUIContent.none, surfaceStyle);

            if (gameObjectEditor != null)
            {
                Rect interactiveRect = new Rect(
                    previewRect.x + 1f,
                    previewRect.y + 1f,
                    previewRect.width - 2f,
                    previewRect.height - 2f);
                gameObjectEditor.OnInteractivePreviewGUI(interactiveRect, transparentBackground);
            }
            else
            {
                const float iconSize = 64f;
                Rect emptyIconRect = new Rect(
                    previewRect.center.x - iconSize * 0.5f,
                    previewRect.center.y - iconSize * 0.5f,
                    iconSize,
                    iconSize);
                DrawIcon(emptyIconRect, iconBox, new Color32(68, 68, 68, 255));
            }
        }

        private static void DrawIcon(Rect rect, Texture2D texture, Color tint)
        {
            if (texture == null) return;
            Color previousColor = GUI.color;
            GUI.color = tint;
            GUI.DrawTexture(rect, texture, ScaleMode.ScaleToFit, true);
            GUI.color = previousColor;
        }

        private static void DrawAutoSizedLabel(
            Rect rect,
            string text,
            GUIStyle style,
            string tooltip)
        {
            int originalFontSize = style.fontSize;
            GUIContent content = new GUIContent(text, tooltip);

            while (style.fontSize > 1 && style.CalcSize(content).x > rect.width)
            {
                style.fontSize--;
            }

            GUI.Label(rect, content, style);
            style.fontSize = originalFontSize;
        }

        private static void DrawDashedBorder(Rect rect, Color color)
        {
            const float thickness = 1f;
            const float dashLength = 6f;
            const float gap = 5f;

            for (float x = rect.x + 8f; x < rect.xMax - 8f; x += dashLength + gap)
            {
                float width = Mathf.Min(dashLength, rect.xMax - 8f - x);
                EditorGUI.DrawRect(new Rect(x, rect.y, width, thickness), color);
                EditorGUI.DrawRect(new Rect(x, rect.yMax - thickness, width, thickness), color);
            }

            for (float y = rect.y + 8f; y < rect.yMax - 8f; y += dashLength + gap)
            {
                float height = Mathf.Min(dashLength, rect.yMax - 8f - y);
                EditorGUI.DrawRect(new Rect(rect.x, y, thickness, height), color);
                EditorGUI.DrawRect(new Rect(rect.xMax - thickness, y, thickness, height), color);
            }
        }

        private static void StartEditorCoroutine(IEnumerator coroutine, GenerationJob job = null)
        {
            EnsureCoroutineSchedulerRegistered();
            coroutines.Add(new EditorCoroutineState(coroutine, job));
        }

        private static void EnsureCoroutineSchedulerRegistered()
        {
            EditorApplication.update -= UpdateCoroutines;
            EditorApplication.update += UpdateCoroutines;
            EditorApplication.focusChanged -= OnEditorFocusChanged;
            EditorApplication.focusChanged += OnEditorFocusChanged;
            if (lastSchedulerUpdateTime <= 0d)
            {
                lastSchedulerUpdateTime = EditorApplication.timeSinceStartup;
            }
        }

        private static void UpdateCoroutines()
        {
            double now = EditorApplication.timeSinceStartup;
            double schedulerGap = lastSchedulerUpdateTime > 0d
                ? now - lastSchedulerUpdateTime
                : 0d;
            lastSchedulerUpdateTime = now;
            if (schedulerGap >= SchedulerStallThresholdSeconds)
            {
                Debug.Log(
                    $"Tripo task scheduler resumed after {schedulerGap:0.0}s without Editor updates. " +
                    "Polling deadlines were extended by the paused interval.");
                foreach (GenerationJob job in generationJobs)
                {
                    if (job.IsTerminal) continue;
                    if (job.StageDeadline > 0d) job.StageDeadline += schedulerGap;
                    if (job.LastProgressChangeTime > 0d) job.LastProgressChangeTime += schedulerGap;
                    if (job.LastActivityTime > 0d) job.LastActivityTime += schedulerGap;
                    if (job.LastPollTime > 0d) job.LastPollTime += schedulerGap;
                }

                foreach (EditorCoroutineState state in coroutines)
                {
                    if (state.WaitDeadline > 0d) state.WaitDeadline += schedulerGap;
                }
            }

            for (int i = coroutines.Count - 1; i >= 0; i--)
            {
                EditorCoroutineState state = coroutines[i];
                if (state.WaitingFor is AsyncOperation operation && !operation.isDone)
                {
                    if (state.WaitDeadline > 0d && now >= state.WaitDeadline)
                    {
                        FailJob(state.Job, "A network request stopped responding.");
                        DisposeCoroutine(state);
                        coroutines.RemoveAt(i);
                    }
                    continue;
                }
                if (state.WaitingFor is EditorDelay delay && now < delay.ResumeAt) continue;

                state.WaitingFor = null;
                state.WaitDeadline = 0d;
                bool hasNext;
                try
                {
                    hasNext = state.Routine.MoveNext();
                }
                catch (Exception exception)
                {
                    Debug.LogException(exception);
                    if (state.Job != null)
                    {
                        FailJob(state.Job, exception.Message);
                    }
                    hasNext = false;
                }

                if (!hasNext)
                {
                    DisposeCoroutine(state);
                    coroutines.RemoveAt(i);
                    continue;
                }

                state.WaitingFor = state.Routine.Current;
                if (state.WaitingFor is UnityWebRequestAsyncOperation requestOperation)
                {
                    int requestTimeout = requestOperation.webRequest != null
                        ? requestOperation.webRequest.timeout
                        : 0;
                    state.WaitDeadline = now +
                        Math.Max(requestTimeout, RequestTimeoutSeconds) +
                        RequestWatchdogGraceSeconds;
                }
            }

            if (coroutines.Count == 0)
            {
                EditorApplication.update -= UpdateCoroutines;
                EditorApplication.focusChanged -= OnEditorFocusChanged;
                lastSchedulerUpdateTime = 0d;
            }
            else
            {
                if (now - lastQueueRepaintTime >= 1d)
                {
                    lastQueueRepaintTime = now;
                    RepaintQueueWindows();
                }
            }
        }

        private static void DisposeCoroutine(EditorCoroutineState state)
        {
            if (state.Routine is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }


        private static void FailJob(GenerationJob job, string errorMessage)
        {
            if (job == null || job.IsTerminal) return;
            GenerationJobStage failedStage = job.Stage;
            job.Stage = GenerationJobStage.Failed;
            job.ErrorMessage = string.IsNullOrWhiteSpace(errorMessage)
                ? "Unknown error"
                : errorMessage;
            string failedApiKey = job.ApiKey;
            job.ApiKey = string.Empty;
            job.StageDeadline = 0d;
            job.LastActivityTime = EditorApplication.timeSinceStartup;
            generationJobs.Remove(job);
            Debug.LogError(
                $"Tripo job #{job.Number} failed. " +
                $"stage={failedStage}, model={job.ModelId}, " +
                $"task_id={job.CurrentTaskId}, error={job.ErrorMessage}");
            ScheduleBalanceRefresh(failedApiKey);
            RepaintQueueWindows();
        }

        private static void RepaintQueueWindows()
        {
            foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
            {
                window.Repaint();
            }
        }

        private static IEnumerator DownloadFBXModel(
            GenerationJob job,
            string fileUrl,
            string uniquePath,
            int attempt = 0)
        {
            const int maxAttempts = 3;

            // A null/empty URL is NOT transient — retrying spins forever and (because
            // DownloadHandlerFile creates a folder per attempt) spawns endless folders.
            // The v3 task result exposes the model link as output.model_url; an empty
            // value here means upstream task/output parsing is wrong, so stop cleanly.
            if (string.IsNullOrEmpty(fileUrl))
            {
                Debug.LogError("Download aborted: empty model URL (expected output.model_url from the v3 task result).");
                FailJob(job, "The completed task returned no model URL.");
                yield break;
            }

            string directory = Path.GetDirectoryName(uniquePath);
            if (!Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            using (UnityWebRequest uwr = UnityWebRequest.Get(fileUrl))
            {
                uwr.downloadHandler = new DownloadHandlerFile(uniquePath);
                uwr.timeout = DownloadTimeoutSeconds;
                yield return uwr.SendWebRequest();

                if (uwr.result == UnityWebRequest.Result.ConnectionError ||
                    uwr.result == UnityWebRequest.Result.ProtocolError)
                {
                    if (attempt + 1 < maxAttempts)
                    {
                        Debug.LogWarning($"Error downloading file (attempt {attempt + 1}/{maxAttempts}): {uwr.error}. Retrying...");
                        StartEditorCoroutine(
                            DownloadFBXModel(job, fileUrl, uniquePath, attempt + 1),
                            job);
                    }
                    else
                    {
                        Debug.LogError($"Error downloading file, giving up after {maxAttempts} attempts: {uwr.error}");
                        FailJob(job, uwr.error);
                    }
                    yield break;
                }

                if (uwr.result == UnityWebRequest.Result.Success)
                {
                    SetJobStage(job, GenerationJobStage.Importing);
                    AssetDatabase.Refresh();
                    ModelPostProcessing(uniquePath);
                    AssetDatabase.Refresh();
                    ShowPreviewModel(uniquePath);
                    job.OutputAssetPath = uniquePath;
                    SetJobStage(job, GenerationJobStage.Completed);
                    job.ErrorMessage = string.Empty;
                    string completedApiKey = job.ApiKey;
                    job.ApiKey = string.Empty;
                    ScheduleBalanceRefresh(completedApiKey);
                    RepaintQueueWindows();
                }
                else
                {
                    Debug.LogError($"Unexpected result: {uwr.result}");
                    FailJob(job, "Unexpected download result: " + uwr.result);
                }
            }
        }

        private static string GetUniqueFilePath(string originalPath)
        {
            // Give each downloaded model its own folder UNDER the save directory, e.g.
            // Assets/TripoModels/TripoModel_1/TripoModel_1.fbx. The path MUST stay under
            // Assets/ or Unity cannot import the mesh.
            //
            // The previous version built the first candidate without the directory prefix
            // ("TripoModel_1/TripoModel_1.fbx"), so the file landed at the project root
            // outside Assets/ (import silently failed), and its File.Exists loop reused a
            // stale count and kept minting brand-new folders on every retry.
            string directory = Path.GetDirectoryName(originalPath);
            string nameWithoutExtension = Path.GetFileNameWithoutExtension(originalPath);
            string extension = Path.GetExtension(originalPath);

            int count = 1;
            string folderPath;
            do
            {
                folderPath = Path.Combine(directory, $"{nameWithoutExtension}_{count}");
                count++;
            } while (Directory.Exists(folderPath));

            string fileName = Path.GetFileName(folderPath) + extension;
            return Path.Combine(folderPath, fileName).Replace("\\", "/");
        }

        private static void ModelPostProcessing(string assetPath)
        {
            ModelImporter modelImporter = AssetImporter.GetAtPath(assetPath) as ModelImporter;
            if (modelImporter == null)
            {
                Debug.LogError("Failed to post-process model at path: " + assetPath);
                return;
            }

            string directoryPath = Path.GetDirectoryName(assetPath)?.Replace("\\", "/");
            if (string.IsNullOrEmpty(directoryPath))
            {
                Debug.LogError("Failed to determine the model directory for: " + assetPath);
                return;
            }

            modelImporter.ExtractTextures(directoryPath);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            HashSet<string> normalTexturePaths = FindMaterialNormalTexturePaths(assetPath);
            foreach (string textureGuid in AssetDatabase.FindAssets("t:Texture2D", new[] { directoryPath }))
            {
                string texturePath = AssetDatabase.GUIDToAssetPath(textureGuid);
                if (IsNormalTextureFileName(texturePath))
                {
                    normalTexturePaths.Add(texturePath);
                }
            }

            int normalTextureCount = 0;
            foreach (string texturePath in normalTexturePaths)
            {
                TextureImporter textureImporter = AssetImporter.GetAtPath(texturePath) as TextureImporter;
                if (textureImporter == null)
                {
                    continue;
                }

                if (textureImporter.textureType != TextureImporterType.NormalMap || textureImporter.sRGBTexture)
                {
                    textureImporter.textureType = TextureImporterType.NormalMap;
                    textureImporter.sRGBTexture = false;
                    textureImporter.SaveAndReimport();
                }

                normalTextureCount++;
            }

            if (normalTextureCount > 0)
            {
                AssetDatabase.ImportAsset(
                    assetPath,
                    ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            }
        }

        private static HashSet<string> FindMaterialNormalTexturePaths(string assetPath)
        {
            HashSet<string> texturePaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (UnityEngine.Object asset in AssetDatabase.LoadAllAssetsAtPath(assetPath))
            {
                Material material = asset as Material;
                if (material == null)
                {
                    continue;
                }

                foreach (string propertyName in material.GetTexturePropertyNames())
                {
                    if (!IsNormalTextureProperty(propertyName))
                    {
                        continue;
                    }

                    Texture texture = material.GetTexture(propertyName);
                    string texturePath = texture != null ? AssetDatabase.GetAssetPath(texture) : string.Empty;
                    if (!string.IsNullOrEmpty(texturePath))
                    {
                        texturePaths.Add(texturePath);
                    }
                }
            }

            return texturePaths;
        }

        private static bool IsNormalTextureProperty(string propertyName)
        {
            return !string.IsNullOrEmpty(propertyName) &&
                (propertyName.IndexOf("normal", StringComparison.OrdinalIgnoreCase) >= 0 ||
                 propertyName.IndexOf("bump", StringComparison.OrdinalIgnoreCase) >= 0);
        }

        private static bool IsNormalTextureFileName(string assetPath)
        {
            string fileName = Path.GetFileNameWithoutExtension(assetPath);
            if (string.IsNullOrEmpty(fileName))
            {
                return false;
            }

            string[] tokens = fileName.Split(
                new[] { '_', '-', ' ', '.' },
                StringSplitOptions.RemoveEmptyEntries);
            foreach (string token in tokens)
            {
                switch (token.ToLowerInvariant())
                {
                    case "normal":
                    case "normals":
                    case "normalmap":
                    case "normalgl":
                    case "normaldx":
                    case "nrm":
                    case "bump":
                    case "bumpmap":
                        return true;
                }
            }

            return false;
        }

        private static void CheckAndCloseBumpMapSettingsFixingWindow()
        {
            var type = typeof(Editor).Assembly.GetType("UnityEditor.BumpMapSettingsFixingWindow");
            if (type != null && HasOpenInstances(type))
            {
                var windows = Resources.FindObjectsOfTypeAll(type);
                foreach (var window in windows)
                {
                    if (window is EditorWindow editorWindow)
                    {
                        editorWindow.Close();
                    }
                }
            }
        }

        public static bool HasOpenInstances(Type t)
        {
            UnityEngine.Object[] objectsOfTypeAll = Resources.FindObjectsOfTypeAll(t);
            return objectsOfTypeAll != null && objectsOfTypeAll.Length != 0;
        }

        private static void ShowPreviewModel(string assetPath)
        {
            GameObject loadedModel = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (loadedModel != null)
            {
                // Preview uses the FBX's own imported orientation — no hardcoded
                // axis rotation. (Previously forced Quaternion.Euler(-90,0,0).)
                // Concurrent jobs intentionally use last-completed-wins for Result Preview.
                loadedModel.GetComponent<Transform>().localScale = Vector3.one;
                gameObject = loadedModel;
                foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
                {
                    window.selectedObject = loadedModel;
                    window.DestroyPreviewEditor();
                    window.gameObjectEditor = Editor.CreateEditor(loadedModel);
                }
            }
            else
            {
                Debug.LogError("Failed to load model at path: " + assetPath);
            }

            RepaintQueueWindows();
        }

        private static IEnumerator ImageToModelCoroutine(GenerationJob job)
        {
            byte[] imageData;
            try
            {
                imageData = File.ReadAllBytes(job.ImagePath);
            }
            catch (Exception exception)
            {
                FailJob(job, "Unable to read the selected image: " + exception.Message);
                yield break;
            }

            WWWForm form = new WWWForm();
            form.AddBinaryData(
                "file",
                imageData,
                Path.GetFileName(job.ImagePath),
                TripoFileTypes.GetImageMimeType(job.ImagePath));

            using (UnityWebRequest request = UnityWebRequest.Post(TripoEndpoints.Upload, form))
            {
                request.SetRequestHeader("Authorization", $"Bearer {job.ApiKey}");
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = RequestTimeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    FailJob(job, GetRequestFailureMessage("Image upload failed", request));
                    yield break;
                }

                try
                {
                    ImageResponseData response =
                        JsonUtility.FromJson<ImageResponseData>(request.downloadHandler.text);
                    if (response == null || response.code != 0 || response.data == null ||
                        string.IsNullOrEmpty(response.data.file_token))
                    {
                        FailJob(job, "Image upload returned no usable file token.");
                        yield break;
                    }

                    job.ImageToken = response.data.file_token;
                    SetJobStage(job, GenerationJobStage.Submitting);
                    StartEditorCoroutine(PostImageToModel(job), job);
                }
                catch (Exception exception)
                {
                    FailJob(job, "Unable to parse the image upload response: " + exception.Message);
                }
            }
        }

        private static IEnumerator TextPromptsToModel(GenerationJob job)
        {
            return SubmitGenerationRequest(
                job,
                TripoEndpoints.TextToModel,
                BuildTextRequestJson(job));
        }

        private static IEnumerator PostImageToModel(GenerationJob job)
        {
            return SubmitGenerationRequest(
                job,
                TripoEndpoints.ImageToModel,
                BuildImageRequestJson(job));
        }

        private static IEnumerator SubmitGenerationRequest(GenerationJob job, string url, string jsonData)
        {
            byte[] postData = System.Text.Encoding.UTF8.GetBytes(jsonData);
            using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(postData);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Authorization", $"Bearer {job.ApiKey}");
                request.timeout = RequestTimeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    FailJob(job, GetRequestFailureMessage("Generation submission failed", request));
                    yield break;
                }

                try
                {
                    TextTaskResponse response =
                        JsonUtility.FromJson<TextTaskResponse>(request.downloadHandler.text);
                    if (response == null || response.code != 0 || response.data == null ||
                        string.IsNullOrEmpty(response.data.task_id))
                    {
                        FailJob(job, "Generation submission returned no task ID.");
                        yield break;
                    }

                    job.GenerationTaskId = response.data.task_id;
                    SetJobStage(job, GenerationJobStage.Generating, true);
                    ScheduleBalanceRefresh(job.ApiKey);
                    StartEditorCoroutine(GetTaskProgressAndOutput(job), job);
                }
                catch (Exception exception)
                {
                    FailJob(job, "Unable to parse the generation response: " + exception.Message);
                }
            }
        }

        private static string BuildTextRequestJson(GenerationJob job)
        {
            if (TripoModelCapabilities.SupportsAdvancedGeneration(job.ModelId))
            {
                return JsonUtility.ToJson(new TextPromptsRequestData
                {
                    model = job.ModelId,
                    prompt = job.Prompt,
                    face_limit = job.FaceLimit,
                    texture = job.Texture,
                    pbr = job.Pbr,
                    texture_quality = job.TextureQuality,
                    auto_size = job.AutoSize,
                    quad = job.Quad
                });
            }

            if (job.ModelId == "v2.5-20250123")
            {
                return JsonUtility.ToJson(new TextPromptsRequestData_v25
                {
                    model = job.ModelId,
                    prompt = job.Prompt,
                    face_limit = job.FaceLimit,
                    texture = job.Texture,
                    pbr = job.Pbr
                });
            }

            return JsonUtility.ToJson(new TextPromptsRequestData_p
            {
                model = job.ModelId,
                prompt = job.Prompt,
                face_limit = job.FaceLimit,
                texture = job.Texture,
                pbr = job.Pbr
            });
        }

        private static string BuildImageRequestJson(GenerationJob job)
        {
            if (TripoModelCapabilities.SupportsAdvancedGeneration(job.ModelId))
            {
                return JsonUtility.ToJson(new ImagePromptsRequestData
                {
                    model = job.ModelId,
                    input = job.ImageToken,
                    face_limit = job.FaceLimit,
                    texture = job.Texture,
                    pbr = job.Pbr,
                    texture_quality = job.TextureQuality,
                    auto_size = job.AutoSize,
                    quad = job.Quad
                });
            }

            if (job.ModelId == "v2.5-20250123")
            {
                return JsonUtility.ToJson(new ImagePromptsRequestData_v25
                {
                    model = job.ModelId,
                    input = job.ImageToken,
                    face_limit = job.FaceLimit,
                    texture = job.Texture,
                    pbr = job.Pbr
                });
            }

            return JsonUtility.ToJson(new ImagePromptsRequestData_p
            {
                model = job.ModelId,
                input = job.ImageToken,
                face_limit = job.FaceLimit,
                texture = job.Texture,
                pbr = job.Pbr
            });
        }

        private static string GetRequestFailureMessage(string operation, UnityWebRequest request)
        {
            string detail = request != null ? request.error : string.Empty;
            if (request != null && request.responseCode > 0)
            {
                detail += $" (http_status={request.responseCode})";
            }
            string responseText = request?.downloadHandler?.text;
            if (!string.IsNullOrWhiteSpace(responseText))
            {
                try
                {
                    ApiErrorResponse response = JsonUtility.FromJson<ApiErrorResponse>(responseText);
                    if (response != null)
                    {
                        if (!string.IsNullOrWhiteSpace(response.message)) detail = response.message;
                        if (response.code != 0) detail += $" (code={response.code})";
                        if (!string.IsNullOrWhiteSpace(response.suggestion))
                        {
                            detail += " Suggestion: " + response.suggestion;
                        }
                        if (!string.IsNullOrWhiteSpace(response.request_id))
                        {
                            detail += " request_id=" + response.request_id;
                        }
                    }
                }
                catch (ArgumentException)
                {
                    // Keep UnityWebRequest.error when the server body is not valid JSON.
                }
            }

            return string.IsNullOrWhiteSpace(detail) ? operation : operation + ": " + detail;
        }

        private static string GetTaskFailureMessage(
            string operation,
            TaskSearchResponse response,
            string status)
        {
            TaskSearchData data = response?.data;
            string detail = FirstNonEmpty(
                data?.error,
                data?.message,
                data?.reason,
                response?.message);
            int errorCode = data != null && data.error_code != 0
                ? data.error_code
                : response?.code ?? 0;
            string suggestion = FirstNonEmpty(data?.suggestion, response?.suggestion);
            string requestId = FirstNonEmpty(data?.request_id, response?.request_id);

            string message = operation + " ended with status: " + status;
            if (!string.IsNullOrWhiteSpace(detail)) message += ". " + detail;
            else message += ". The server returned no failure details; contact Tripo support with the task ID.";
            if (errorCode != 0) message += $" (code={errorCode})";
            if (!string.IsNullOrWhiteSpace(suggestion)) message += " Suggestion: " + suggestion;
            if (!string.IsNullOrWhiteSpace(requestId)) message += " request_id=" + requestId;
            return message;
        }

        private static string FirstNonEmpty(params string[] values)
        {
            foreach (string value in values)
            {
                if (!string.IsNullOrWhiteSpace(value)) return value;
            }

            return string.Empty;
        }

        private static void ScheduleBalanceRefresh(
            string requestApiKey,
            bool showErrors = false,
            double delaySeconds = BalanceRefreshDelaySeconds)
        {
            if (string.IsNullOrEmpty(requestApiKey)) return;

            int refreshVersion = nextBalanceRefreshVersion++;
            bool hasMatchingWindow = false;
            foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
            {
                if (requestApiKey != window.apiKey ||
                    (!window.apiKeyConfirmed && !showErrors))
                {
                    continue;
                }
                window.latestBalanceRefreshVersion = refreshVersion;
                hasMatchingWindow = true;
            }

            if (!hasMatchingWindow) return;
            StartEditorCoroutine(RefreshBalanceAfterDelay(
                requestApiKey,
                showErrors,
                refreshVersion,
                delaySeconds));
        }

        private static IEnumerator RefreshBalanceAfterDelay(
            string requestApiKey,
            bool showErrors,
            int refreshVersion,
            double delaySeconds)
        {
            if (delaySeconds > 0d)
            {
                yield return new EditorDelay(delaySeconds);
            }

            if (!IsBalanceRefreshCurrent(requestApiKey, refreshVersion)) yield break;

            for (int attempt = 1; attempt <= BalanceRefreshMaxAttempts; attempt++)
            {
                BalanceRefreshResult result = new BalanceRefreshResult();
                IEnumerator routine = GetUserBalance(
                    requestApiKey,
                    showErrors && attempt == BalanceRefreshMaxAttempts,
                    refreshVersion,
                    result);
                try
                {
                    while (routine.MoveNext()) yield return routine.Current;
                }
                finally
                {
                    if (routine is IDisposable disposable) disposable.Dispose();
                }

                if (result.Success ||
                    !IsBalanceRefreshCurrent(requestApiKey, refreshVersion))
                {
                    break;
                }

                if (attempt < BalanceRefreshMaxAttempts)
                {
                    yield return new EditorDelay(TransientRetryDelaySeconds);
                }
            }

            if (IsBalanceRefreshCurrent(requestApiKey, refreshVersion) &&
                HasActiveJobForApiKey(requestApiKey))
            {
                ScheduleBalanceRefresh(
                    requestApiKey,
                    false,
                    ActiveBalanceRefreshIntervalSeconds);
            }
        }

        private static bool IsBalanceRefreshCurrent(string requestApiKey, int refreshVersion)
        {
            foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
            {
                if (requestApiKey == window.apiKey &&
                    refreshVersion == window.latestBalanceRefreshVersion)
                {
                    return true;
                }
            }

            return false;
        }

        private static bool HasActiveJobForApiKey(string requestApiKey)
        {
            return generationJobs.Exists(job =>
                !job.IsTerminal && requestApiKey == job.ApiKey);
        }

        private static IEnumerator GetUserBalance(
            string requestApiKey,
            bool showErrors,
            int refreshVersion,
            BalanceRefreshResult result)
        {
            using (UnityWebRequest request = UnityWebRequest.Get(TripoEndpoints.Balance))
            {
                request.SetRequestHeader("Authorization", $"Bearer {requestApiKey}");
                request.timeout = RequestTimeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    if (showErrors &&
                        IsBalanceRefreshCurrent(requestApiKey, refreshVersion) &&
                        HasWindowWithApiKey(requestApiKey))
                    {
                        string title = requestApiKey.StartsWith("tsk_")
                            ? "Connection failed"
                            : "Invalid API Key";
                        string message = requestApiKey.StartsWith("tsk_")
                            ? "We are unable to locate your account balance; please check your internet connection."
                            : "The API Key format is incorrect. Please ensure it starts with 'tsk_'.";
                        EditorUtility.DisplayDialog(title, message, "OK");
                    }
                    yield break;
                }

                try
                {
                    BalanceResponseDataWrapper response =
                        JsonUtility.FromJson<BalanceResponseDataWrapper>(request.downloadHandler.text);
                    if (response != null && response.code == 0 && response.data != null)
                    {
                        foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
                        {
                            if (requestApiKey == window.apiKey &&
                                refreshVersion == window.latestBalanceRefreshVersion)
                            {
                                window.ApplyBalance(response.data);
                            }
                        }
                        result.Success = true;
                        yield break;
                    }

                    if (showErrors &&
                        IsBalanceRefreshCurrent(requestApiKey, refreshVersion) &&
                        HasWindowWithApiKey(requestApiKey))
                    {
                        EditorUtility.DisplayDialog(
                            "Balance unavailable",
                            "The API did not return a valid account balance. Verify the API key and try again.",
                            "OK");
                    }
                }
                catch (Exception exception)
                {
                    Debug.LogError($"Error parsing balance response: {exception.Message}");
                }
            }
        }

        private static bool HasWindowWithApiKey(string requestApiKey)
        {
            foreach (Tripo_main_window window in Resources.FindObjectsOfTypeAll<Tripo_main_window>())
            {
                if (requestApiKey == window.apiKey) return true;
            }

            return false;
        }

        public IEnumerator GetTaskProgressAndOutput(
            string taskId,
            bool isTextToModel)
        {
            // Source-compatible entry point retained for existing Editor extensions.
            return ResumeGenerationTask(taskId, isTextToModel, false);
        }

        public IEnumerator GetTaskProgressAndOutput(
            string taskId,
            bool isTextToModel,
            bool outputIsFbx)
        {
            // Extended entry point for tasks whose generation output is already FBX.
            return ResumeGenerationTask(taskId, isTextToModel, outputIsFbx);
        }

        public IEnumerator GetConversionTaskProgressAndOutput(
            string taskId,
            bool isTextToModel)
        {
            // Retained for compatibility with Editor extensions that resume a conversion task.
            return ResumeConversionTask(taskId, isTextToModel);
        }

        private IEnumerator ResumeGenerationTask(
            string taskId,
            bool isTextToModel,
            bool outputIsFbx)
        {
            GenerationJob job = CreateRecoveredJob(
                taskId,
                isTextToModel,
                outputIsFbx,
                false);
            if (job == null) yield break;
            IEnumerator routine = GetTaskProgressAndOutput(job);
            try
            {
                while (routine.MoveNext()) yield return routine.Current;
            }
            finally
            {
                if (routine is IDisposable disposable) disposable.Dispose();
            }
        }

        private IEnumerator ResumeConversionTask(string taskId, bool isTextToModel)
        {
            GenerationJob job = CreateRecoveredJob(
                taskId,
                isTextToModel,
                false,
                true);
            if (job == null) yield break;
            IEnumerator routine = GetConversionTaskProgressAndOutput(job);
            try
            {
                while (routine.MoveNext()) yield return routine.Current;
            }
            finally
            {
                if (routine is IDisposable disposable) disposable.Dispose();
            }
        }

        private GenerationJob CreateRecoveredJob(
            string taskId,
            bool isTextToModel,
            bool outputIsFbx,
            bool isConversion)
        {
            if (!TryReserveQueueSlot(false)) return null;

            double now = EditorApplication.timeSinceStartup;
            GenerationJob job = new GenerationJob
            {
                Number = nextGenerationJobNumber++,
                IsTextToModel = isTextToModel,
                InputSummary = "External task",
                ApiKey = apiKey,
                ModelId = "External",
                GenerationOutputIsFbx = outputIsFbx,
                GenerationTaskId = isConversion ? string.Empty : taskId,
                ConversionTaskId = isConversion ? taskId : string.Empty,
                GenerationProgress = isConversion ? 1f : 0f,
                LastActivityTime = now,
                LastProgressChangeTime = now,
                Stage = isConversion
                    ? GenerationJobStage.Converting
                    : GenerationJobStage.Generating
            };
            generationJobs.Add(job);
            RepaintQueueWindows();
            return job;
        }

        private static IEnumerator GetTaskProgressAndOutput(GenerationJob job)
        {
            string taskId = job.GenerationTaskId;
            string url = TripoEndpoints.TaskById(taskId);
            int consecutiveRequestFailures = 0;
            EnsureStageDeadline(job);
            while (EditorApplication.timeSinceStartup < job.StageDeadline)
            {
                job.LastPollTime = EditorApplication.timeSinceStartup;
                job.LastActivityTime = job.LastPollTime;
                using (UnityWebRequest request = UnityWebRequest.Get(url))
                {
                    request.downloadHandler = new DownloadHandlerBuffer();
                    request.SetRequestHeader("Authorization", $"Bearer {job.ApiKey}");
                    request.timeout = RequestTimeoutSeconds;
                    yield return request.SendWebRequest();

                    if (request.result != UnityWebRequest.Result.Success)
                    {
                        consecutiveRequestFailures++;
                        if (consecutiveRequestFailures >= PollRequestMaxAttempts)
                        {
                            FailJob(job, GetRequestFailureMessage("Generation polling failed", request));
                            yield break;
                        }

                        Debug.LogWarning(
                            $"Generation polling failed for job #{job.Number} " +
                            $"(attempt {consecutiveRequestFailures}/{PollRequestMaxAttempts}). " +
                            $"The existing task will be queried again. task_id={taskId}");
                        yield return new EditorDelay(TransientRetryDelaySeconds);
                        continue;
                    }
                    consecutiveRequestFailures = 0;

                    TaskSearchResponse response;
                    try
                    {
                        response = JsonUtility.FromJson<TaskSearchResponse>(request.downloadHandler.text);
                    }
                    catch (Exception exception)
                    {
                        FailJob(job, "Unable to parse the generation task: " + exception.Message);
                        yield break;
                    }

                    if (response == null || response.code != 0 || response.data == null)
                    {
                        FailJob(job, "Generation polling returned an invalid response.");
                        yield break;
                    }

                    string status = response.data.status;
                    if (TripoTaskStatus.IsFailure(status))
                    {
                        FailJob(job, GetTaskFailureMessage("Generation", response, status));
                        yield break;
                    }

                    if (!TripoTaskStatus.IsActive(status) && !TripoTaskStatus.IsSuccess(status))
                    {
                        FailJob(job, "Generation returned an unknown status: " + status);
                        yield break;
                    }

                    float progress = Mathf.Clamp01(response.data.progress / 100f);
                    UpdateJobProgress(job, progress, false, status);
                    RepaintQueueWindows();
                    if (TripoTaskStatus.IsSuccess(status))
                    {
                        job.GenerationProgress = 1f;
                        ScheduleBalanceRefresh(job.ApiKey);
                        if (job.GenerationOutputIsFbx)
                        {
                            TaskSearchOutputData output = response.data.output;
                            if (output == null || string.IsNullOrEmpty(output.model_url))
                            {
                                FailJob(job, "The completed quad task returned no model URL.");
                                yield break;
                            }

                            StartJobDownload(job, output.model_url);
                        }
                        else
                        {
                            StartEditorCoroutine(RequestFbxConversion(job), job);
                        }
                        yield break;
                    }
                }

                yield return new EditorDelay(PollIntervalSeconds);
            }

            FailJob(job, $"Generation made no progress for {TaskTimeoutSeconds:0} seconds.");
        }

        private static IEnumerator RequestFbxConversion(GenerationJob job)
        {
            SetJobStage(job, GenerationJobStage.Converting, true);
            string jsonData = JsonUtility.ToJson(new FBXConversionRequestData
            {
                format = "FBX",
                input = job.GenerationTaskId
            });
            byte[] postData = System.Text.Encoding.UTF8.GetBytes(jsonData);

            using (UnityWebRequest request = new UnityWebRequest(TripoEndpoints.ModelConvert, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(postData);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("Authorization", $"Bearer {job.ApiKey}");
                request.timeout = RequestTimeoutSeconds;
                yield return request.SendWebRequest();

                if (request.result != UnityWebRequest.Result.Success)
                {
                    FailJob(job, GetRequestFailureMessage("FBX conversion submission failed", request));
                    yield break;
                }

                try
                {
                    TextTaskResponse response =
                        JsonUtility.FromJson<TextTaskResponse>(request.downloadHandler.text);
                    if (response == null || response.code != 0 || response.data == null ||
                        string.IsNullOrEmpty(response.data.task_id))
                    {
                        FailJob(job, "FBX conversion returned no task ID.");
                        yield break;
                    }

                    job.ConversionTaskId = response.data.task_id;
                    ScheduleBalanceRefresh(job.ApiKey);
                    StartEditorCoroutine(GetConversionTaskProgressAndOutput(job), job);
                }
                catch (Exception exception)
                {
                    FailJob(job, "Unable to parse the conversion response: " + exception.Message);
                }
            }
        }

        private static IEnumerator GetConversionTaskProgressAndOutput(GenerationJob job)
        {
            string taskId = job.ConversionTaskId;
            string url = TripoEndpoints.TaskById(taskId);
            int consecutiveRequestFailures = 0;
            EnsureStageDeadline(job);
            while (EditorApplication.timeSinceStartup < job.StageDeadline)
            {
                job.LastPollTime = EditorApplication.timeSinceStartup;
                job.LastActivityTime = job.LastPollTime;
                using (UnityWebRequest request = UnityWebRequest.Get(url))
                {
                    request.downloadHandler = new DownloadHandlerBuffer();
                    request.SetRequestHeader("Authorization", $"Bearer {job.ApiKey}");
                    request.timeout = RequestTimeoutSeconds;
                    yield return request.SendWebRequest();

                    if (request.result != UnityWebRequest.Result.Success)
                    {
                        consecutiveRequestFailures++;
                        if (consecutiveRequestFailures >= PollRequestMaxAttempts)
                        {
                            FailJob(job, GetRequestFailureMessage("Conversion polling failed", request));
                            yield break;
                        }

                        Debug.LogWarning(
                            $"Conversion polling failed for job #{job.Number} " +
                            $"(attempt {consecutiveRequestFailures}/{PollRequestMaxAttempts}). " +
                            $"The existing task will be queried again. task_id={taskId}");
                        yield return new EditorDelay(TransientRetryDelaySeconds);
                        continue;
                    }
                    consecutiveRequestFailures = 0;

                    TaskSearchResponse response;
                    try
                    {
                        response = JsonUtility.FromJson<TaskSearchResponse>(request.downloadHandler.text);
                    }
                    catch (Exception exception)
                    {
                        FailJob(job, "Unable to parse the conversion task: " + exception.Message);
                        yield break;
                    }

                    if (response == null || response.code != 0 || response.data == null)
                    {
                        FailJob(job, "Conversion polling returned an invalid response.");
                        yield break;
                    }

                    string status = response.data.status;
                    if (TripoTaskStatus.IsFailure(status))
                    {
                        FailJob(job, GetTaskFailureMessage("Conversion", response, status));
                        yield break;
                    }

                    if (!TripoTaskStatus.IsActive(status) && !TripoTaskStatus.IsSuccess(status))
                    {
                        FailJob(job, "Conversion returned an unknown status: " + status);
                        yield break;
                    }

                    float progress = Mathf.Clamp01(response.data.progress / 100f);
                    UpdateJobProgress(job, progress, true, status);
                    RepaintQueueWindows();
                    if (TripoTaskStatus.IsSuccess(status))
                    {
                        ScheduleBalanceRefresh(job.ApiKey);
                        TaskSearchOutputData output = response.data.output;
                        if (output == null || string.IsNullOrEmpty(output.model_url))
                        {
                            FailJob(job, "The completed conversion returned no model URL.");
                            yield break;
                        }

                        job.ConversionProgress = 1f;
                        StartJobDownload(job, output.model_url);
                        yield break;
                    }
                }

                yield return new EditorDelay(PollIntervalSeconds);
            }

            FailJob(job, $"Conversion made no progress for {TaskTimeoutSeconds:0} seconds.");
        }

        private static void StartJobDownload(GenerationJob job, string modelUrl)
        {
            SetJobStage(job, GenerationJobStage.Downloading);
            string savePath = Path.Combine(saveDirectory, "TripoModel.fbx");
            string uniquePath = GetUniqueFilePath(savePath);
            string directory = Path.GetDirectoryName(uniquePath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            StartEditorCoroutine(DownloadFBXModel(job, modelUrl, uniquePath), job);
        }

        private static void SetJobStage(
            GenerationJob job,
            GenerationJobStage stage,
            bool hasTaskDeadline = false)
        {
            double now = EditorApplication.timeSinceStartup;
            job.Stage = stage;
            job.StageDeadline = hasTaskDeadline ? now + TaskTimeoutSeconds : 0d;
            job.LastActivityTime = now;
            job.LastProgressChangeTime = now;
            RepaintQueueWindows();
        }

        private static void EnsureStageDeadline(GenerationJob job)
        {
            if (job.StageDeadline <= 0d)
            {
                job.StageDeadline = EditorApplication.timeSinceStartup + TaskTimeoutSeconds;
            }
        }

        private static void UpdateJobProgress(
            GenerationJob job,
            float progress,
            bool isConversion,
            string serverStatus)
        {
            double now = EditorApplication.timeSinceStartup;
            float previousProgress = isConversion
                ? job.ConversionProgress
                : job.GenerationProgress;
            if (progress > previousProgress + 0.0001f ||
                !string.Equals(job.LastServerStatus, serverStatus, StringComparison.OrdinalIgnoreCase))
            {
                job.LastProgressChangeTime = now;
                job.StageDeadline = now + TaskTimeoutSeconds;
            }

            if (isConversion) job.ConversionProgress = Mathf.Max(previousProgress, progress);
            else job.GenerationProgress = Mathf.Max(previousProgress, progress);
            job.LastServerStatus = serverStatus;
            job.LastActivityTime = now;
        }

        // Request/response DTOs are defined once in the shared TripoApiModels.cs
        // (Runtime assembly, TripoForUnity namespace) and reused here via the
        // asmdef reference to tripoforunity.Runtime. Do not redeclare them here.
    }
}
#endif
