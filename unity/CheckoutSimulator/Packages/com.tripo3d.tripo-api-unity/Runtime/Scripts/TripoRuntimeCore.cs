using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Events;
namespace TripoForUnity
{
    

public enum ModelVersion
{
    Legacy_v2_5_20250123 = 0,
    Legacy_v2_0_20240919 = 1,
    Legacy_v1_4_20240625 = 2,
    Legacy_v1_3_20240522 = 3,
    v3_1_20260211 = 10,
    v3_0_20250812 = 11,
    v2_5_20250123 = 12,
    P1_20260311 = 13
}

public enum TextureQuality
{
    Standard = 0, 
    Detailed = 1
}

public class TripoRuntimeCore: MonoBehaviour
{
    private const int CurrentModelSelectionSchema = 1;
    private const int RequestTimeoutSeconds = 60;
    private const float TaskTimeoutSeconds = 300f;
    private const float PollIntervalSeconds = 1f;
    private string apiKey = "";
    // Default to the documented latest model, matching the Editor window.
    public ModelVersion selectedModel = ModelVersion.v3_1_20260211;
    [SerializeField, HideInInspector] private int modelSelectionSchemaVersion;

    public int face_limit = TripoGenerationLimits.DefaultFaceLimit;
    public bool texture_optional = true;
    public bool pbr_optional = true;
    public TextureQuality texture_quality_optional = TextureQuality.Standard;
    public bool autosize_optional = false;

    public string textPrompt = "";
    public float textToModelProgress = 0f;
    public float textToModelGenerateProgress = 0f;
    
    public string imagePath = "";
    public Texture2D uploadedImage = null;
    public float imageToModelProgress = 0f;
    public float imageToModelGenerateProgress = 0f;

    public GameObject simpleModel;

    
    private readonly string[] textureQualityOptions = { "standard", "detailed" };
    private string imageToken = "";


    public UnityEvent<string> OnDownloadComplete = new UnityEvent<string>();
    public void set_api_key(string apiKey)
    {
        this.apiKey = apiKey;
    }

    private void Awake()
    {
        MigrateModelSelection();
        ClampGenerationSettings();
    }

    private void OnValidate()
    {
        MigrateModelSelection();
        ClampGenerationSettings();
    }

    private void ClampGenerationSettings()
    {
        string selectedModelId = GetSelectedModelId();
        face_limit = TripoGenerationLimits.ClampFaceLimit(
            selectedModelId,
            false,
            face_limit);
    }

    private void MigrateModelSelection()
    {
        if (modelSelectionSchemaVersion < CurrentModelSelectionSchema)
        {
            switch (selectedModel)
            {
                case ModelVersion.Legacy_v2_5_20250123:
                    selectedModel = ModelVersion.v2_5_20250123;
                    break;
                case ModelVersion.Legacy_v2_0_20240919:
                case ModelVersion.Legacy_v1_4_20240625:
                case ModelVersion.Legacy_v1_3_20240522:
                    selectedModel = ModelVersion.v3_1_20260211;
                    break;
            }
        }

        modelSelectionSchemaVersion = CurrentModelSelectionSchema;
    }

    private string GetSelectedModelId()
    {
        MigrateModelSelection();
        switch (selectedModel)
        {
            case ModelVersion.v3_0_20250812:
                return "v3.0-20250812";
            case ModelVersion.v2_5_20250123:
                return "v2.5-20250123";
            case ModelVersion.P1_20260311:
                return "P1-20260311";
            default:
                return "v3.1-20260211";
        }
    }
    
    public void Text_to_Model_func()
    {
        if (apiKey == "")
        {
            Debug.LogError("Please enter a valid API Key");
            return;
        }
        string selectedModelId = GetSelectedModelId();
        Debug.Log($"Running Text_to_Model_func with input: {textPrompt} and model: {selectedModelId}");
        StartCoroutine(TextPromptsToModel());
    }

    public void Image_to_Model_func()
    {
        if (apiKey == "")
        {
            Debug.LogError("Please enter a valid API Key");
            return;
        }
        string selectedModelId = GetSelectedModelId();
        Debug.Log($"Running Image_to_Model_func with image: {imagePath} and model: {selectedModelId}");
        StartCoroutine(ImageToModelCoroutine());
    }
    private IEnumerator ImageToModelCoroutine()
    {
        imageToModelGenerateProgress = 0f;
        imageToModelProgress = 0f;
        if (string.IsNullOrEmpty(imagePath))
        {
            Debug.LogError("No image selected for upload.");
            yield break;
        }

        string url = TripoEndpoints.Upload;

        byte[] imageData = File.ReadAllBytes(imagePath);

        // Creating a WWWForm
        WWWForm form = new WWWForm();
        form.AddBinaryData("file", imageData, Path.GetFileName(imagePath), TripoFileTypes.GetImageMimeType(imagePath));

        // Creating the UnityWebRequest
        using (UnityWebRequest uwr = UnityWebRequest.Post(url, form))
        {
            // Set the authorization header
            uwr.SetRequestHeader("Authorization", $"Bearer {apiKey}");
            uwr.downloadHandler = new DownloadHandlerBuffer();
            uwr.timeout = RequestTimeoutSeconds;
            yield return uwr.SendWebRequest();

            if (uwr.result == UnityWebRequest.Result.ConnectionError ||
                uwr.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"Image upload failed: {uwr.error}, {uwr.result}");
            }
            else if (uwr.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    string responseText = uwr.downloadHandler.text;

                    ImageResponseData jsonResponse = JsonUtility.FromJson<ImageResponseData>(responseText);

                    if (jsonResponse != null && jsonResponse.code == 0 &&
                        jsonResponse.data != null && !string.IsNullOrEmpty(jsonResponse.data.file_token))
                    {
                        imageToken = jsonResponse.data.file_token;
                        Debug.Log($"Image Token: {imageToken}");
                        StartCoroutine(PostImageToModel());
                    }
                    else
                    {
                        Debug.LogError($"Image upload returned no usable file_token. code={jsonResponse?.code}");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError("Error parsing response: " + e.Message);
                }
            }
        }
    }
    private IEnumerator TextPromptsToModel()
    {
        string url = TripoEndpoints.TextToModel;
        textToModelProgress = 0f;
        textToModelGenerateProgress = 0f;
        string jsonData;
        // Build the request body according to each v3 model's supported fields.
        string selectedModelId = GetSelectedModelId();
        int requestedFaceLimit = TripoGenerationLimits.ClampFaceLimit(
            selectedModelId,
            false,
            face_limit);
        face_limit = requestedFaceLimit;
        if (selectedModel == ModelVersion.v3_1_20260211 || selectedModel == ModelVersion.v3_0_20250812)
        {
            TextPromptsRequestData requestData = new TextPromptsRequestData
            {
                model = selectedModelId,
                prompt = textPrompt,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional,
                texture_quality = textureQualityOptions[(int)texture_quality_optional],
                auto_size = autosize_optional,
                quad = false
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else if (selectedModel == ModelVersion.v2_5_20250123)
        {
            TextPromptsRequestData_v25 requestData = new TextPromptsRequestData_v25()
            {
                model = selectedModelId,
                prompt = textPrompt,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else if (selectedModel == ModelVersion.P1_20260311)
        {
            TextPromptsRequestData_p requestData = new TextPromptsRequestData_p
            {
                model = selectedModelId,
                prompt = textPrompt,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else
        {
            // Defensive fallback for future enum values; current legacy values migrate before this point.
            TextPromptsRequestData_lowVersion requestData = new TextPromptsRequestData_lowVersion()
            {
                model = selectedModelId,
                prompt = textPrompt,
            };
            jsonData = JsonUtility.ToJson(requestData);
        }

        Debug.Log(jsonData);
        byte[] postData = System.Text.Encoding.UTF8.GetBytes(jsonData);

        using (UnityWebRequest uwr = new UnityWebRequest(url, "POST"))
        {
            uwr.uploadHandler = new UploadHandlerRaw(postData);

            uwr.downloadHandler = new DownloadHandlerBuffer();
            uwr.SetRequestHeader("Content-Type", "application/json");
            uwr.SetRequestHeader("Authorization", $"Bearer {apiKey}");
            uwr.timeout = RequestTimeoutSeconds;

            yield return uwr.SendWebRequest();
            // Check the results appropriately
            if (uwr.result == UnityWebRequest.Result.ConnectionError ||
                uwr.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"Error: {uwr.error}, {uwr.result}\nResponse body: {uwr.downloadHandler?.text}");
            }
            else if (uwr.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    if (uwr.downloadHandler != null)
                    {
                        string jsonResponse = uwr.downloadHandler.text;

                        // Deserialize and process the response
                        TextTaskResponse response = JsonUtility.FromJson<TextTaskResponse>(jsonResponse);

                        if (response != null && response.code == 0 && response.data != null &&
                            !string.IsNullOrEmpty(response.data.task_id))
                        {
                            
                            StartCoroutine(GetTaskProgressAndOutput(response.data.task_id, true));
                            
                        }
                        else
                        {
                            Debug.LogError("Error in response data.");
                        }
                    }
                    else
                    {
                        Debug.LogError("DownloadHandler is null, failed to retrieve the response.");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError("Error parsing response: " + e.Message);
                }
            }
        }
    }

    private IEnumerator PostImageToModel()
    {
        string url = TripoEndpoints.ImageToModel;
        string jsonData;
        // Build the request body according to each v3 model's supported fields.
        string selectedModelId = GetSelectedModelId();
        int requestedFaceLimit = TripoGenerationLimits.ClampFaceLimit(
            selectedModelId,
            false,
            face_limit);
        face_limit = requestedFaceLimit;
        if (selectedModel == ModelVersion.v3_1_20260211 || selectedModel == ModelVersion.v3_0_20250812)
        {
            ImagePromptsRequestData requestData = new ImagePromptsRequestData
            {
                model = selectedModelId,
                input = imageToken,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional,
                texture_quality = textureQualityOptions[(int)texture_quality_optional],
                auto_size = autosize_optional,
                quad = false
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else if (selectedModel == ModelVersion.v2_5_20250123)
        {
            ImagePromptsRequestData_v25 requestData = new ImagePromptsRequestData_v25()
            {
                model = selectedModelId,
                input = imageToken,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else if (selectedModel == ModelVersion.P1_20260311)
        {
            ImagePromptsRequestData_p requestData = new ImagePromptsRequestData_p
            {
                model = selectedModelId,
                input = imageToken,
                face_limit = requestedFaceLimit,
                texture = texture_optional,
                pbr = pbr_optional
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        else
        {
            // Defensive fallback for future enum values; current legacy values migrate before this point.
            ImagePromptsRequestData_lowVersion requestData = new ImagePromptsRequestData_lowVersion()
            {
                model = selectedModelId,
                input = imageToken,
            };
            jsonData = JsonUtility.ToJson(requestData);
        }
        Debug.Log(jsonData);
        // Adding form fields
        
        byte[] postData = System.Text.Encoding.UTF8.GetBytes(jsonData);
        using (UnityWebRequest uwr = new UnityWebRequest(url, "POST"))
        {
            // Set headers correctly
            uwr.uploadHandler = new UploadHandlerRaw(postData);
            uwr.downloadHandler = new DownloadHandlerBuffer();
            uwr.SetRequestHeader("Content-Type", "application/json");
            uwr.SetRequestHeader("Authorization", $"Bearer {apiKey}");
            uwr.timeout = RequestTimeoutSeconds;

            yield return uwr.SendWebRequest();
            // Check the results appropriately
            if (uwr.result == UnityWebRequest.Result.ConnectionError ||
                uwr.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError($"Error: {uwr.error}, {uwr.result}\nResponse body: {uwr.downloadHandler?.text}");
            }
            else if (uwr.result == UnityWebRequest.Result.Success)
            {
                try
                {
                    string jsonResponse = uwr.downloadHandler.text;
                    ImageTaskResponse response = JsonUtility.FromJson<ImageTaskResponse>(jsonResponse);

                    if (response != null && response.code == 0 && response.data != null &&
                        !string.IsNullOrEmpty(response.data.task_id))
                    {
                        
                        StartCoroutine(GetTaskProgressAndOutput(response.data.task_id, false));
                        
                    }
                    else
                    {
                        Debug.LogError("Error in response: " + jsonResponse);
                    }
                }
                catch (System.Exception e)
                {
                    Debug.LogError("Error parsing response: " + e.Message);
                }
            }
        }
    }

    public IEnumerator GetTaskProgressAndOutput(string taskId, bool isTextToModel)
    {
        string url = TripoEndpoints.TaskById(taskId);
        float startedAt = Time.realtimeSinceStartup;
        while (true)
        {
            if (Time.realtimeSinceStartup - startedAt >= TaskTimeoutSeconds)
            {
                Debug.LogError($"Task polling timed out after {TaskTimeoutSeconds} seconds. task_id={taskId}");
                ResetProgress(isTextToModel);
                yield break;
            }

            using (UnityWebRequest uwr = UnityWebRequest.Get(url))
            {
                uwr.downloadHandler = new DownloadHandlerBuffer();
                uwr.SetRequestHeader("Authorization", $"Bearer {apiKey}");
                uwr.timeout = RequestTimeoutSeconds;

                yield return uwr.SendWebRequest();
                // Handle the response
                if (uwr.result == UnityWebRequest.Result.ConnectionError || uwr.result == UnityWebRequest.Result.ProtocolError)
                {
                    Debug.LogError($"Task polling failed: {uwr.error}. task_id={taskId}");
                    ResetProgress(isTextToModel);
                    yield break;
                }
                else if (uwr.result == UnityWebRequest.Result.Success)
                {
                    try
                    {
                        // v3 unifies task output across every model, so all
                        // versions share one TaskSearchResponse shape.
                        string jsonResponse = uwr.downloadHandler.text;

                        TaskSearchResponse response = JsonUtility.FromJson<TaskSearchResponse>(jsonResponse);

                        if (response != null && response.code == 0 && response.data != null)
                        {
                            string status = response.data.status;
                            if (TripoTaskStatus.IsFailure(status))
                            {
                                Debug.LogError($"Task terminated with status '{status}'. task_id={taskId}");
                                ResetProgress(isTextToModel);
                                yield break;
                            }

                            if (!TripoTaskStatus.IsActive(status) && !TripoTaskStatus.IsSuccess(status))
                            {
                                Debug.LogError($"Task returned unknown status '{status}'. task_id={taskId}");
                                ResetProgress(isTextToModel);
                                yield break;
                            }

                            float progress = Mathf.Clamp01(response.data.progress / 100f);

                            if (isTextToModel)
                            {
                                textToModelGenerateProgress = progress;
                                textToModelProgress = textToModelGenerateProgress;
                            }
                            else
                            {
                                imageToModelGenerateProgress = progress;
                                imageToModelProgress = imageToModelGenerateProgress;
                            }

                            if (TripoTaskStatus.IsSuccess(status))
                            {
                                if (isTextToModel)
                                {
                                    textToModelGenerateProgress = 1f;
                                    textToModelProgress = textToModelGenerateProgress;
                                }
                                else
                                {
                                    imageToModelGenerateProgress = 1f;
                                    imageToModelProgress = imageToModelGenerateProgress;
                                }

                                TaskSearchOutputData output = response.data.output;
                                // v3 exposes the download link as output.model_url
                                // (v2's model / pbr_model fields no longer exist).
                                if (output != null && !string.IsNullOrEmpty(output.model_url))
                                {
                                    Debug.Log($"model_url: {output.model_url}");
                                    OnDownloadComplete.Invoke(output.model_url);
                                    ResetProgress(isTextToModel);
                                }
                                else
                                {
                                    Debug.LogError($"Successful task returned no model_url. task_id={taskId}");
                                    ResetProgress(isTextToModel);
                                }
                                yield break;
                            }
                        }
                        else
                        {
                            Debug.LogError($"Invalid task response. code={response?.code}, task_id={taskId}");
                            ResetProgress(isTextToModel);
                            yield break;
                        }
                    }
                    catch (Exception e)
                    {
                        Debug.LogError("Error parsing response: " + e.Message);
                        ResetProgress(isTextToModel);
                        yield break;
                    }
                }
                else
                {
                    Debug.LogError($"Unexpected task polling result: {uwr.result}. task_id={taskId}");
                    ResetProgress(isTextToModel);
                    yield break;
                }
            }
            yield return new WaitForSeconds(PollIntervalSeconds);
        }
    }

    private void ResetProgress(bool isTextToModel)
    {
        if (isTextToModel)
        {
            textToModelGenerateProgress = 0f;
            textToModelProgress = 0f;
        }
        else
        {
            imageToModelGenerateProgress = 0f;
            imageToModelProgress = 0f;
        }
    }

    // Request/response DTOs and endpoint constants live in the shared
    // TripoApiModels.cs (same TripoForUnity namespace, Runtime assembly),
    // reused by the Editor window. Do not redeclare them here.
}
}
