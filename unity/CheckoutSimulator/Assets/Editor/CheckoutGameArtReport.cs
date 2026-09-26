using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

// Writes Logs/game_art_report.txt with the import state of the mini-game art and force-reimports
// any texture that did not load (after an editor crash corrupted some .meta files).
[InitializeOnLoad]
public static class CheckoutGameArtReport {
 static CheckoutGameArtReport(){EditorApplication.delayCall+=Run;}
 [MenuItem("Checkout/Diagnose game art")]
 public static void Run(){
  const string dir="Assets/Resources/CheckoutDesktop/Game";
  if(!Directory.Exists(dir))return;
  var sb=new StringBuilder();int broken=0;
  foreach(var file in Directory.GetFiles(dir,"*.png")){
   var path=file.Replace('\\','/');var importer=AssetImporter.GetAtPath(path);
   var tex=AssetDatabase.LoadAssetAtPath<Texture2D>(path);
   var name=Path.GetFileNameWithoutExtension(path);var res=Resources.Load<Texture2D>("CheckoutDesktop/Game/"+name);
   sb.AppendLine($"{name}\timporter={(importer?importer.GetType().Name:"null")}\ttex={(tex?tex.width+"x"+tex.height:"null")}\tres={(res?"ok":"null")}\tbytes={new FileInfo(path).Length}");
   if(!tex){broken++;AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate|ImportAssetOptions.ForceSynchronousImport);}
  }
  sb.AppendLine("broken="+broken);
  Directory.CreateDirectory("Logs");File.WriteAllText("Logs/game_art_report.txt",sb.ToString());
 }
}
