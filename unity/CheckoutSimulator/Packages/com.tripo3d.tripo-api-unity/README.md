# Tripo API Unity

Tripo API Unity integrates Tripo3D's text-to-model and image-to-model features directly into the Unity development environment for 3D content creation and game development.

## Features

- 🎨 **Text to 3D Model Generation**: Create 3D models from text descriptions
- 📸 **Image to 3D Model Generation**: Convert images into 3D models
- ⚡ **Multiple Model Versions**: Choose among v3.1, v3.0, v2.5, and P1
- 🔌 **Runtime Integration**: Full support for runtime model generation
- 🛠️ **Easy-to-use Editor Interface**: User-friendly Unity editor window
- 🔑 **API Integration**: Simple API key management

## Prerequisites

- Unity 2021.3 or higher
- Valid Tripo3D API key (starts with `tsk_`)
- Stable internet connection

## Install

Follow these steps to install **Tripo API Unity** into your Unity project.


---

### Install the Plugin Package
1. Download the Tripo Plugin package from the release page and extract the archive.

2. Open your Unity project, then go to **`Window > Package Manager`**.

3. Click the **`+`** button in the upper-left corner and select
   **`Install package from disk...`** (called **`Add package from disk...`** in
   some Unity versions).

4. In the file picker, open the extracted **`Tripo API Unity`** folder, select its
   **`package.json`** file, and click **Open**.

5. Wait for Unity Package Manager to finish installing the package.

> Do not rename the extracted folder or manually copy it into your project's
> `Packages` directory. Unity registers the local package when you select its
> `package.json` file.

> **Upgrading from v1.0.12 or earlier:** Remove the old
> `com.unity.vast.tripoforunity` package before installing this version. The UPM
> package ID is now `com.tripo3d.tripo-api-unity`.

---

### Open the Plugin
After installation, verify that **Tripo API Unity** appears in
**`Window > Package Manager`**, then open the plugin window from:

**`Tools > Tripo API Unity`**

---
## Usage Guide - Editor

###  Set Up Your API Key
1. Navigate to **`Tools > Tripo API Unity`**.
2. In the popup text inputfield, input your API key (start with `tsk_`) and click  (**✔**) to confirm.
3. Once your API key is validated, all Tripo3D features will become available.

> **Credential storage:** The Editor window stores the API key in Unity `EditorPrefs`,
> which is plain local preference storage and is not encrypted. Use a scoped key when
> available, and click the confirmed key icon before sharing the machine or project to
> remove the stored value.

### Generate a 3D Model Using Text
1. In **Text to Model** module, Enter a description of the model in the text inputfield.
2. Click the **Generate** button to create the model.

### Generate a 3D Model Using Image
1. In **Image to Model** module, Click the box to upload and preview an image from your computer.
2. Click the **Generate** button to create the model.

### Track Multiple Generation Tasks
- You can submit another Text to Model or Image to Model task while earlier tasks are still running.
- The local queue follows the platform limit of 10 concurrent tasks. Generate is disabled while all 10 slots are active.
- The **Task Queue** keeps each task's input (for example, `cat` or `dog`), server task ID, stage, and progress visible independently.
- Each completed task continues through FBX conversion when required, download, Unity import, and Result Preview.
- Completed tasks turn green and remain in the queue until you click **Clear Finished**. Completed history does not consume the 10 active-task slots.
- Failed tasks leave immediately and log their model, task ID, and error in the Unity Console.
- The queue is session-only and starts empty after Unity is closed and restarted.
- Available and frozen credits refresh while tasks are active and when a task reaches a terminal state.

### Adjust Model Versions
1. At the bottom of the window, you'll find a **dropdown menu** for selecting the Tripo model version.
2. Click the dropdown menu to choose the desired version:

- **v3.1-20260211**: The default model. The plugin exposes an adaptive face-limit
  slider, texture, PBR, texture quality, auto-size, and triangle/quad topology.
- **v3.0-20250812**: Supports the same settings currently exposed for v3.1.
- **v2.5-20250123**: Supports face limit, texture, and PBR settings.
- **P1-20260311**: Supports a 500-20,000 face-limit range, texture, and PBR.

All models use a minimum face limit of 500. Each model/topology starts at its
maximum: v3 triangles 2,000,000, v3 quads 150,000, v2.5 500,000, and P1 20,000.


## Usage Guide - Runtime
### Add TripoRuntimeCore to Your Scene
1. create a new empty GameObject.
3. Locate the script at **`Assets/Runtime/SimpleImplementScripts/TripoRuntimeCore`**
2. Attach the **`TripoRuntimeCore`** script to the empty GameObject.
### Core Functionalities
With the **`TripoRuntimeCore`** script attached, you can directly call Tripo's features from your scripts. Additionally, you can adjust various **public variables** of the **`TripoRuntimeCore`** component to customize the generation process.

Below are examples of how to use some of the core functionalities in Runtime Mode. These methods can be directly implemented or found in the **`TripoSimpleUI_Manager`** script for easy integration.

### Setup API Key
```csharp
 GetComponent<TripoRuntimeCore>().set_api_key("Your API Key");
```
### Generate 3D Model from Text
```csharp
GetComponent<TripoRuntimeCore>().textPrompt = "Your Text Prompts";
GetComponent<TripoRuntimeCore>().Text_to_Model_func();
```
### Generate 3D Model from Image
```csharp
GetComponent<TripoRuntimeCore>().imagePath = "Your Image's Path";
GetComponent<TripoRuntimeCore>().Image_to_Model_func();
```
### Handle Model Download Completion
```csharp
void Start()
{
    GetComponent<TripoRuntimeCore>().OnDownloadComplete.AddListener(OnFbxDownloadComplete);
}

void OnFbxDownloadComplete(string path)
{
    Debug.Log($"File downloaded at: {path}");
}
```


Create and manage 3D models with Tripo API Unity.

## Configuration

### API Key Setup
To use Tripo's services, you'll need an API key:
1. [Create a Tripo Developers account](https://developers.tripo3d.ai/en/auth/register) (if you haven't already)
2. Generate an API key from the [API Keys page](https://developers.tripo3d.ai/en/keys)
3. Follow the "Set Up Your API Key" instructions in the Usage Guide below


## Support and Community

- 🛠️ [Tripo Developers](https://developers.tripo3d.ai/)
- 📚 [API Documentation](https://developers.tripo3d.ai/en/docs/introduction)
- 📖 [Tripo DCC Bridge Guide Hub](https://www.tripo3d.ai/blog/tripo-dcc-bridge-guide-hub)
- 📧 Email Support: support@tripo3d.ai
- 🌐 [Official Website](https://www.tripo3d.ai)

## Contributing

We welcome contributions to improve Tripo API Unity! Please feel free to:
- Report bugs
- Suggest new features
- Submit pull requests

## Version History

- v1.0.13 (Current)
  - Renamed the user-facing product and release archive to **Tripo API Unity**
  - Changed the UPM package ID to `com.tripo3d.tripo-api-unity`
  - Raised the minimum supported Unity version to 2021.3
  - Aligned the author and documentation metadata with Tripo Bridge
  - Declared the required `com.unity.ugui` dependency for clean installations
  - Moved S3 distribution to `plugins/unity-api`, using `Tripo_API_Unity` for S3 object filenames only

- v1.0.12
  - Restored the **Clear Finished** queue action
  - Kept successful jobs green with their original input visible until manually cleared
  - Counted only active jobs toward the 10-task platform limit
  - Kept queue history session-only so a Unity restart begins with an empty queue

- v1.0.11
  - Migrated text-to-model, image-to-model, task polling, model conversion, and
    account balance requests to Tripo API v3
  - Added v3.1, v3.0, v2.5, and P1 model selection with model-specific options,
    adaptive face limits, and triangle/quad topology support where available
  - Added an Editor task queue for up to 10 concurrent generation jobs, including
    independent progress, model information, downloads, imports, and previews
  - Refreshed the Editor interface, interactive Result Preview, API key and credit
    display, advanced settings layout, and Package Manager installation guide
  - Improved FBX download/import handling and automatic Unity normal-map detection

- v1.0.1
  - Updated Tripo developer links and prepared the initial API v3 package candidate

- v1.0.0
  - Initial public release
  - Text-to-model and image-to-model support
  - Runtime integration
  
- v0.8.0 (Beta)
  - Beta testing phase
  - Core functionality implementation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Special thanks to our beta testers and community members
- Unity Technologies for their excellent development platform
