using TMPro;
using UnityEngine;
using UnityEngine.TextCore;

namespace Checkout {
 // The game's money is its own coin, not any country's currency (Lucas 17/10: "o dinheiro do jogo também não pode ser
 // em reais"): amounts on the register, the card machine and the receipts read "<coin> 27" with the coin icon the HUD
 // uses (CheckoutDesktop/Icons/coin) drawn inline by TextMeshPro. The sprite asset is built once at run time; its
 // material lives in Resources (CoinTextSprite.mat) so the TextMeshPro/Sprite shader ships in the builds.
 public static class CheckoutCoinText {
  static TMP_SpriteAsset asset; static bool tried;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)] static void Reset() { asset = null; tried = false; }
  public const string Tag = "<sprite name=\"coin\">";

  /// <summary>"(coin) 27" (any TextMeshPro text draws the coin: it becomes the default sprite asset); plain "27" when
  /// the icon is missing.</summary>
  public static string Of(double value) => (Asset ? Tag + " " : "") + value.ToString("0");

  /// <summary>Lets a label draw the coin (call once on every label that shows Of()).</summary>
  public static T Use<T>(T label) where T : TMP_Text { if (label && Asset) label.spriteAsset = Asset; return label; }

  public static TMP_SpriteAsset Asset {
   get {
    if (asset || tried) return asset;
    tried = true;
    var tex = Resources.Load<Texture2D>("CheckoutDesktop/Icons/coin");
    var mat = Resources.Load<Material>("CheckoutDesktop/CoinTextSprite");
    if (!tex || !mat) { Debug.LogWarning("CHECKOUT_COIN_TEXT missing coin icon or material"); return null; }
    var a = ScriptableObject.CreateInstance<TMP_SpriteAsset>();
    a.name = "Coin sprite"; a.spriteSheet = tex; a.material = new Material(mat) { mainTexture = tex };
    // a 1.1.0 asset: without it TextMeshPro "upgrades" it from the old sprite list and empties the tables
    var version = typeof(TMP_SpriteAsset).GetField("m_Version", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    if (version != null) version.SetValue(a, "1.1.0");
    float w = tex.width, h = tex.height;
    // the asset's point size is the icon's height, so the coin is drawn as tall as the text's point size (scaled to
    // about a capital letter below), sitting a little under the baseline like a round letter
    var faceField = typeof(TMP_SpriteAsset).GetField("m_FaceInfo", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
    if (faceField != null) { var face = new FaceInfo { pointSize = (int)h, scale = 1f, ascentLine = h * .8f, lineHeight = h, baseline = 0, descentLine = -h * .2f }; faceField.SetValue(a, face); }
    var glyph = new TMP_SpriteGlyph(0, new GlyphMetrics(w, h, 0, h * .78f, w * 1.04f), new GlyphRect(0, 0, (int)w, (int)h), .8f, 0);
    a.spriteGlyphTable.Add(glyph);
    var character = new TMP_SpriteCharacter(0xE000, glyph) { name = "coin", scale = 1f };
    a.spriteCharacterTable.Add(character);
    a.UpdateLookupTables();
    asset = a;
    // every text can draw it: the default sprite asset of TextMeshPro (or a fallback of the one set there)
    var settings = TMP_Settings.instance;
    if (settings) {
     var current = TMP_Settings.defaultSpriteAsset;
     var field = typeof(TMP_Settings).GetField("m_defaultSpriteAsset", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
     if (current && current != a) {
      if (current.fallbackSpriteAssets == null) current.fallbackSpriteAssets = new System.Collections.Generic.List<TMP_SpriteAsset>();
      if (!current.fallbackSpriteAssets.Contains(a)) current.fallbackSpriteAssets.Add(a);
      Application.quitting += () => { if (current) current.fallbackSpriteAssets.Remove(a); };   // the editor keeps assets between plays
     } else if (field != null) {
      field.SetValue(settings, a);
      Application.quitting += () => { if (settings) field.SetValue(settings, current); };
     }
    }
    return asset;
   }
  }
 }
}
