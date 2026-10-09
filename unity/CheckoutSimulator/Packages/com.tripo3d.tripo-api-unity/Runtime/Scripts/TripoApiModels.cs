using System;

namespace TripoForUnity
{
    /// <summary>
    /// Centralised Tripo API endpoints. Shared by the Runtime (TripoRuntimeCore)
    /// and the Editor window (Tripo_main_window) so both agree on host + paths.
    ///
    /// Migrated to API v3 (per official migration-v2-to-v3 guide + v3.0 changelog):
    ///   host: api.tripo3d.ai  ->  openapi.tripo3d.ai
    ///   base: /v2/openapi     ->  /v3   (dropped the redundant /openapi segment)
    ///   upload: /upload       ->  /files (multipart)
    ///   the single "/task + type" endpoint splits into per-capability endpoints.
    /// Account balance and generation now use the same v3 API host.
    /// </summary>
    public static class TripoEndpoints
    {
        // v3 base (host + version both changed from v2).
        public const string BaseUrl = "https://openapi.tripo3d.ai/v3";

        // File upload: POST /v2/openapi/upload -> POST /v3/files (multipart).
        public const string Upload = BaseUrl + "/files";

        // Generation: v2 "POST /task + type" -> per-capability v3 endpoints.
        public const string TextToModel = BaseUrl + "/generation/text-to-model";
        public const string ImageToModel = BaseUrl + "/generation/image-to-model";

        // Model processing (Editor GLB->FBX): type=convert_model -> /v3/models/convert.
        public const string ModelConvert = BaseUrl + "/models/convert";

        // Account balance includes available and frozen credits.
        public const string Balance = BaseUrl + "/account/balance";

        // Task query: GET /v2/openapi/task/{id} -> GET /v3/tasks/{id}.
        public static string TaskById(string taskId)
        {
            return BaseUrl + "/tasks/" + taskId;
        }
    }

    public static class TripoTaskStatus
    {
        public static bool IsActive(string status)
        {
            return string.Equals(status, "queued", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(status, "running", StringComparison.OrdinalIgnoreCase);
        }

        public static bool IsSuccess(string status)
        {
            return string.Equals(status, "success", StringComparison.OrdinalIgnoreCase);
        }

        public static bool IsFailure(string status)
        {
            return string.Equals(status, "failed", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(status, "banned", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(status, "expired", StringComparison.OrdinalIgnoreCase)
                   || string.Equals(status, "cancelled", StringComparison.OrdinalIgnoreCase);
        }
    }

    public static class TripoFileTypes
    {
        public static string GetImageMimeType(string path)
        {
            return path != null && path.EndsWith(".png", StringComparison.OrdinalIgnoreCase)
                ? "image/png"
                : "image/jpeg";
        }
    }

    public static class TripoGenerationLimits
    {
        public const int MinFaceLimit = 500;
        public const int MaxTriangleFaceLimit = 2000000;
        public const int MaxQuadFaceLimit = 150000;
        public const int MaxV25FaceLimit = 500000;
        public const int MaxP1FaceLimit = 20000;
        public const int DefaultFaceLimit = MaxTriangleFaceLimit;

        public static void GetFaceLimitRange(string model, bool quad, out int minimum, out int maximum)
        {
            if (string.Equals(model, "P1-20260311", StringComparison.Ordinal))
            {
                minimum = MinFaceLimit;
                maximum = MaxP1FaceLimit;
                return;
            }

            minimum = MinFaceLimit;
            if (quad && TripoModelCapabilities.SupportsQuadMesh(model))
            {
                maximum = MaxQuadFaceLimit;
            }
            else if (string.Equals(model, "v2.5-20250123", StringComparison.Ordinal))
            {
                maximum = MaxV25FaceLimit;
            }
            else
            {
                maximum = MaxTriangleFaceLimit;
            }
        }

        public static int ClampFaceLimit(string model, bool quad, int value)
        {
            GetFaceLimitRange(model, quad, out int minimum, out int maximum);
            return Math.Min(maximum, Math.Max(minimum, value));
        }
    }

    public static class TripoModelCapabilities
    {
        public static bool SupportsAdvancedGeneration(string model)
        {
            return string.Equals(model, "v3.1-20260211", StringComparison.Ordinal) ||
                   string.Equals(model, "v3.0-20250812", StringComparison.Ordinal);
        }

        public static bool SupportsQuadMesh(string model)
        {
            // The current API enables both capabilities at v3.0+, but keeping
            // separate predicates prevents UI code from coupling their contracts.
            return string.Equals(model, "v3.1-20260211", StringComparison.Ordinal) ||
                   string.Equals(model, "v3.0-20250812", StringComparison.Ordinal);
        }
    }

    // ---------------------------------------------------------------------
    // Request bodies
    //
    // v3 migration: the "type" field is gone (the endpoint path now implies the
    // capability), and every input-source field (file / file_token / url /
    // object) collapses into a single "input" string that the server infers.
    //
    // The model-version field is named "model" in v3 (per the per-endpoint
    // reference docs). Allowed values are the v3 set only:
    // v3.1-20260211 / v3.0-20250812 / v2.5-20250123 / P1-20260311. The old v2
    // strings (v2.0-*, v1.4-*, v1.3-*) are rejected with code 1004.
    //
    // Advanced params texture_quality / auto_size / quad require model >=
    // v3.0-20250812. The *_v25 and *_p bodies keep unsupported fields out of
    // requests while preserving each model family's documented face limits.
    // ---------------------------------------------------------------------

    [Serializable]
    public class FBXConversionRequestData
    {
        // convert_model: original_model_task_id -> input (the source task id).
        public string format;
        public string input;
    }

    [Serializable]
    public class TextPromptsRequestData_lowVersion
    {
        public string model;
        public string prompt;
    }

    [Serializable]
    public class TextPromptsRequestData_v25
    {
        public string model;
        public string prompt;
        public int face_limit;
        public bool texture;
        public bool pbr;
    }

    [Serializable]
    public class TextPromptsRequestData_p
    {
        public string model;
        public string prompt;
        public int face_limit;
        public bool texture;
        public bool pbr;
    }

    [Serializable]
    public class TextPromptsRequestData
    {
        public string model;
        public string prompt;
        public int face_limit;
        public bool texture;
        public bool pbr;
        public string texture_quality;
        public bool auto_size;
        public bool quad;
    }

    [Serializable]
    public class ImagePromptsRequestData_lowVersion
    {
        public string model;
        // v3: the uploaded file's token goes straight into "input" (was a nested
        // { type, file_token } object under "file" in v2).
        public string input;
    }

    [Serializable]
    public class ImagePromptsRequestData_v25
    {
        public string model;
        public string input;
        public int face_limit;
        public bool texture;
        public bool pbr;
    }

    [Serializable]
    public class ImagePromptsRequestData_p
    {
        public string model;
        public string input;
        public int face_limit;
        public bool texture;
        public bool pbr;
    }

    [Serializable]
    public class ImagePromptsRequestData
    {
        public string model;
        public string input;
        public int face_limit;
        public bool texture;
        public bool pbr;
        public string texture_quality;
        public bool auto_size;
        public bool quad;
    }

    // ---------------------------------------------------------------------
    // Responses: task creation
    // ---------------------------------------------------------------------

    [Serializable]
    public class TextTaskResponse
    {
        public int code;
        public TaskData data;
    }

    [Serializable]
    public class TaskData
    {
        public string task_id;
    }

    [Serializable]
    public class ImageTaskResponse
    {
        public int code;
        public ImageTaskData data;
    }

    [Serializable]
    public class ImageTaskData
    {
        public string task_id;
    }

    // ---------------------------------------------------------------------
    // Responses: image upload
    // ---------------------------------------------------------------------

    [Serializable]
    public class ImageResponseData
    {
        public int code;
        public ImageData data;
    }

    [Serializable]
    public class ImageData
    {
        // Confirmed by a live v3 upload integration test.
        public string file_token;
    }

    [Serializable]
    public class ApiErrorResponse
    {
        public int code;
        public string message;
        public string suggestion;
        public string request_id;
    }

    // ---------------------------------------------------------------------
    // Responses: task query (progress + output)
    // ---------------------------------------------------------------------

    [Serializable]
    public class TaskSearchResponse
    {
        public int code;
        public string message;
        public string suggestion;
        public string request_id;
        public TaskSearchData data;
    }

    [Serializable]
    public class TaskSearchData
    {
        public string task_id;
        public string type;
        public string status;
        public TaskSearchInput input;
        public TaskSearchOutputData output;
        public int progress;
        public int error_code;
        public string error;
        public string message;
        public string reason;
        public string suggestion;
        public string request_id;
        public string created_at; // v3: ISO 8601 string (e.g. "2026-04-28T12:00:00Z"), was unix long in v2
    }

    [Serializable]
    public class TaskSearchInput
    {
        public string prompt;
    }

    // v3 task result output. Per the generation endpoint task-result example, the
    // output object contains exactly these two URLs — v2's model / base_model /
    // pbr_model / rendered_image fields no longer exist in v3:
    //   "output": { "model_url": "...glb", "rendered_image_url": "...png" }
    [Serializable]
    public class TaskSearchOutputData
    {
        public string model_url;
        public string rendered_image_url;
    }

    // ---------------------------------------------------------------------
    // Responses: user balance (Editor only today, shared for future use)
    // ---------------------------------------------------------------------

    [Serializable]
    public class BalanceResponseDataWrapper
    {
        public int code;
        public BalanceResponseData data;
    }

    [Serializable]
    public class BalanceResponseData
    {
        public int balance;
        public int frozen;
    }
}
