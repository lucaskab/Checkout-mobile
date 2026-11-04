using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;

namespace Checkout {
 /// <summary>
 /// Friends' Google profile photos (docs/social-api.md › Photos). The host sends a face as
 /// <c>"avatar:shopper-3|https://lh3.googleusercontent.com/…"</c>; <see cref="CheckoutSocial.Avatar"/> asks here for the
 /// photo and draws the shopper's portrait until it is ready (or when it fails). Only https addresses on Google's image
 /// hosts (lh3…lh6.googleusercontent.com) are fetched, asking Google for a small square (<c>=s128-c</c>). Downloads run
 /// two at a time in the background (UnityWebRequestTexture, 10 s timeout, ≤ 512 KB); pictures are kept in memory (the
 /// last 48) and on disk in the OS cache folder (≤ 4 MB / 160 files, oldest out first). A failed address is not tried
 /// again for 10 minutes. Nothing here ever blocks the UI: the caller always gets a sprite or null right away.
 /// </summary>
 public class CheckoutPhotos:MonoBehaviour {
  public const int Size=128;
  const int MemoryCap=48,DiskCapFiles=160,Parallel=2,TimeoutSeconds=10,MaxBytes=512*1024;
  const long DiskCapBytes=4L*1024*1024;
  const float RetryAfter=600f;
  static readonly Regex Host=new Regex(@"^lh[3-6]\.googleusercontent\.com$",RegexOptions.CultureInvariant);
  static readonly Regex SizeSuffix=new Regex(@"=[A-Za-z0-9-]+$",RegexOptions.CultureInvariant);
  static readonly Regex SizePath=new Regex(@"/s\d+(-c)?/",RegexOptions.CultureInvariant);

  static readonly Dictionary<string,Sprite> memory=new Dictionary<string,Sprite>();
  static readonly LinkedList<string> recent=new LinkedList<string>();
  static readonly Dictionary<string,float> failedAt=new Dictionary<string,float>();
  static readonly Queue<string> queue=new Queue<string>();
  static readonly HashSet<string> pending=new HashSet<string>();
  static CheckoutPhotos runner;static int running;

  /// <summary>QA: pictures fetched from the network and from disk since start, and addresses that failed.</summary>
  public static int Downloaded {get;private set;}
  public static int FromDisk {get;private set;}
  public static int Failed {get;private set;}
  /// <summary>QA (Editor): stop real downloads, so an address that is not cached fails at once (the avatar stays).</summary>
  public static bool Offline;

  // A new play session (the Editor may keep statics between them): downloads cut short by the last one are forgotten.
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
  static void ResetStatics(){memory.Clear();recent.Clear();failedAt.Clear();queue.Clear();pending.Clear();running=0;runner=null;Offline=false;Downloaded=FromDisk=Failed=0;}

  /// <summary>An address the game may fetch: https, lh3…lh6.googleusercontent.com, no user/port, ≤ 1024 characters.</summary>
  public static bool IsAllowed(string url){
   if(string.IsNullOrEmpty(url)||url.Length>1024||url.IndexOf('|')>=0)return false;
   if(!Uri.TryCreate(url,UriKind.Absolute,out var uri))return false;
   return uri.Scheme==Uri.UriSchemeHttps&&string.IsNullOrEmpty(uri.UserInfo)&&uri.IsDefaultPort&&Host.IsMatch(uri.Host);
  }

  /// <summary>The same picture as a 128 px square (Google's image-sizing parameters: "=s128-c" replaces the token's
  /// "=s96-c"; old "/s96-c/" paths get "/s128-c/"; anything else gets "=s128-c" appended).</summary>
  public static string Sized(string url){
   if(string.IsNullOrEmpty(url))return url;
   int slash=url.LastIndexOf('/');string last=slash>=0?url.Substring(slash+1):url;
   if(SizeSuffix.IsMatch(last))return url.Substring(0,slash+1)+SizeSuffix.Replace(last,"=s"+Size+"-c");
   if(SizePath.IsMatch(url))return SizePath.Replace(url,"/s"+Size+"-c/",1);
   return url+"=s"+Size+"-c";
  }

  /// <summary>The photo's sprite when it is ready, else null (the download or the disk read starts in the background).</summary>
  public static Sprite Get(string url){
   if(!IsAllowed(url))return null;
   string key=Sized(url);
   if(memory.TryGetValue(key,out var sprite)&&sprite){Touch(key);return sprite;}
   if(pending.Contains(key))return null;
   if(failedAt.TryGetValue(key,out var at)&&Time.realtimeSinceStartup-at<RetryAfter)return null;
   pending.Add(key);queue.Enqueue(key);Pump();
   return null;
  }

  static void Pump(){
   if(queue.Count==0||running>=Parallel)return;
   if(!runner){
    var go=new GameObject("Checkout Photos"){hideFlags=HideFlags.HideInHierarchy};
    if(Application.isPlaying)DontDestroyOnLoad(go);
    runner=go.AddComponent<CheckoutPhotos>();
   }
   while(queue.Count>0&&running<Parallel){running++;runner.StartCoroutine(runner.Load(queue.Dequeue()));}
  }

  IEnumerator Load(string key){
   Texture2D texture=null;
   try{
    // 1) the disk cache (a frame later: the UI that asked is drawn first)
    yield return null;
    var file=FileFor(key);
    if(file!=null&&File.Exists(file)){
     try{
      var bytes=File.ReadAllBytes(file);
      if(bytes.Length>0&&bytes.Length<=MaxBytes){
       texture=new Texture2D(2,2,TextureFormat.RGBA32,false);
       if(!texture.LoadImage(bytes,true)||texture.width<8||texture.width>1024||texture.height>1024){Destroy(texture);texture=null;}
       else{FromDisk++;try{File.SetLastWriteTimeUtc(file,DateTime.UtcNow);}catch{}}
      }
     }catch(Exception ex){Debug.LogWarning("CHECKOUT_PHOTOS disk: "+ex.Message);texture=null;}
    }
    // 2) Google
    if(!texture&&!Offline){
     using var request=UnityWebRequestTexture.GetTexture(key,true);
     // (no redirects: only the host the address was checked against answers)
     request.timeout=TimeoutSeconds;request.redirectLimit=0;
     yield return request.SendWebRequest();
     bool ok=request.result==UnityWebRequest.Result.Success;
     var bytes=ok?request.downloadHandler.data:null;
     if(ok&&bytes!=null&&bytes.Length>0&&bytes.Length<=MaxBytes){
      texture=DownloadHandlerTexture.GetContent(request);
      if(texture&&(texture.width<8||texture.width>1024||texture.height>1024)){Destroy(texture);texture=null;}
      if(texture){Downloaded++;Save(key,bytes);}
     }else if(!ok)Debug.Log("CHECKOUT_PHOTOS "+(int)request.responseCode+" "+request.result);
    }
    if(texture){
     texture.wrapMode=TextureWrapMode.Clamp;texture.filterMode=FilterMode.Bilinear;texture.name="Friend photo";
     // A centred square (=s128-c already is one): round portraits only, the gold ring masks the edge.
     int side=Mathf.Min(texture.width,texture.height);
     var rect=new Rect((texture.width-side)/2f,(texture.height-side)/2f,side,side);
     Remember(key,Sprite.Create(texture,rect,new Vector2(.5f,.5f),100));
     failedAt.Remove(key);
    }else{failedAt[key]=Time.realtimeSinceStartup;Failed++;}
   }finally{
    pending.Remove(key);running--;Pump();
   }
  }

  static void Remember(string key,Sprite sprite){
   memory[key]=sprite;Touch(key);
   while(recent.Count>MemoryCap){
    var old=recent.Last.Value;recent.RemoveLast();
    if(memory.TryGetValue(old,out var gone)){memory.Remove(old);if(gone){var t=gone.texture;Destroy(gone);if(t)Destroy(t);}}
   }
  }
  static void Touch(string key){recent.Remove(key);recent.AddFirst(key);}

  // ---- disk cache: <OS cache>/friend-photos/<sha1 of the sized address>.img ----
  static string folder;
  static string Folder(){
   if(folder!=null)return folder;
   try{folder=Path.Combine(Application.temporaryCachePath,"friend-photos");Directory.CreateDirectory(folder);}catch{folder="";}
   return folder;
  }
  static string FileFor(string key){
   var dir=Folder();if(string.IsNullOrEmpty(dir))return null;
   using var sha=SHA1.Create();var hash=sha.ComputeHash(Encoding.UTF8.GetBytes(key));
   var name=new StringBuilder(44);foreach(var b in hash)name.Append(b.ToString("x2"));
   return Path.Combine(dir,name+".img");
  }
  static void Save(string key,byte[] bytes){
   try{
    var file=FileFor(key);if(file==null)return;
    File.WriteAllBytes(file,bytes);Trim();
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_PHOTOS save: "+ex.Message);}
  }
  /// <summary>Keeps the folder under the cap (files and bytes): the least recently used go first.</summary>
  static void Trim(){
   var dir=Folder();if(string.IsNullOrEmpty(dir))return;
   var files=new List<FileInfo>(new DirectoryInfo(dir).GetFiles("*.img"));
   long total=0;foreach(var f in files)total+=f.Length;
   if(files.Count<=DiskCapFiles&&total<=DiskCapBytes)return;
   files.Sort((a,b)=>a.LastWriteTimeUtc.CompareTo(b.LastWriteTimeUtc));
   for(int i=0;i<files.Count&&(files.Count-i>DiskCapFiles||total>DiskCapBytes);i++){total-=files[i].Length;try{files[i].Delete();}catch{}}
  }

  // ---- QA ----
  /// <summary>QA: a picture for an address as if Google had sent it (written to the disk cache: the next Get reads it
  /// like a real cached photo).</summary>
  public static void QaSeed(string url,Texture2D picture){
   if(!IsAllowed(url)||!picture)return;
   string key=Sized(url);
   Save(key,picture.EncodeToPNG());
   if(memory.TryGetValue(key,out var old)){memory.Remove(key);recent.Remove(key);if(old)Destroy(old);}
   failedAt.Remove(key);
  }
  /// <summary>QA: forget the photos in memory (the disk cache stays) and the failures, so the next views load again.</summary>
  public static void QaForgetMemory(){
   foreach(var s in memory.Values)if(s){var t=s.texture;Destroy(s);if(t)Destroy(t);}
   memory.Clear();recent.Clear();failedAt.Clear();Downloaded=FromDisk=Failed=0;
  }
  /// <summary>QA: is that address's photo in memory now.</summary>
  public static bool QaReady(string url)=>IsAllowed(url)&&memory.TryGetValue(Sized(url),out var s)&&s;
  /// <summary>QA: remove the cached files of these addresses (the QA run leaves the folder as it found it).</summary>
  public static void QaDelete(params string[] urls){
   foreach(var url in urls){if(!IsAllowed(url))continue;var file=FileFor(Sized(url));try{if(file!=null&&File.Exists(file))File.Delete(file);}catch{}}
  }
 }
}
