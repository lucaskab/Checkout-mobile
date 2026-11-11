using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace Checkout
{
    // "Estilo do mercado" (Lucas 08/11: "Piso e parede da loja e uniforme da equipe... várias opções para os jogadores
    // mudarem e estilizarem... o letreiro na parede traseira... mudar a fonte, os estilos, as cores... neon, piscando de
    // formas diferentes"). The rules, the catalogue and the prices are the game's (src/data/market-style.ts); this draws
    // what the player wears (the snapshot's "style") or tries in the picker (CheckoutMarketStylePanel → Preview):
    //  - Floor and walls: the market building's tiled floor ("Market Shell/Base/Floor") and the cream plaster of every
    //    wall ("… Inner") take a material on "MarketDay/Style Surface" (world-space triplanar like the originals, so the
    //    build grid lines up; tintable textures carry a mask for the player's colour). The navy wainscot and its gold rail
    //    stay: they are the market's paint (CheckoutMarketPaint). The Späti, quitanda and minimercado are single models,
    //    so a floor quad and three wall quads are laid over their inside (CheckoutStall.InteriorFloor).
    //  - Uniform: the staff's materials ("Worker_*", the stock clerks and cleaners) get copies with UNIFORM_PAINT on
    //    (Resources/CheckoutStyle/UniformPaint.cginc + a mask per character texture); the colours are two globals, so
    //    trying colours costs nothing.
    //  - The big sign on the back wall (stage dressing "S0 name board", "S1 rear sign", "S2 name", "S4 name"): its 3D
    //    TextMesh letters hide and TextMeshPro layers take their place and size, in the chosen font, look (painted, box
    //    letters, outline, gradient, one colour per letter, neon, neon on a dark plate, theatre bulbs) and effect (pulse,
    //    blink, failing neon, letter by letter, wave, alternate colours, rainbow, shine), animated per letter.
    // Everything classic puts the original materials and letters back: a player who never styles draws exactly what was
    // drawn before.
    public class CheckoutMarketStyle : MonoBehaviour
    {
        public const string Classic = "classico", Static = "fixo";
        public static CheckoutMarketStyle Active { get; private set; }
        public StyleState State { get; private set; }
        public StyleChoice Saved { get; private set; } = new StyleChoice();
        public StyleChoice Shown { get; private set; } = new StyleChoice();
        public bool Previewing { get; private set; }
        Transform world;
        bool dirty = true; float nextCheck;

        public void Initialize(Transform root) { world = root; Active = this; }
        void OnDestroy() { if (Active == this) Active = null; }

        // ------------------------------------------------------------------ state
        public void Apply(StyleState state)
        {
            State = state;
            var saved = StyleChoice.From(state);
            if (!saved.Same(Saved)) { Saved = saved; if (!Previewing) Show(Saved); }
        }
        public void Preview(StyleChoice choice) { Previewing = true; Show(choice); }
        public void EndPreview() { Previewing = false; Show(Saved); }
        /// <summary>The purchase landed: this is the player's style now (the snapshot confirms it a moment later).</summary>
        public void Adopt(StyleChoice choice) { Saved = choice.Clone(); EndPreview(); }

        void Show(StyleChoice choice)
        {
            Shown = choice.Clone(); dirty = true;
            Shader.SetGlobalVector("_UniformMain", CheckoutMarketPaint.Oklab(Hex(Shown.uniformMain, "1D2B4F")));
            Shader.SetGlobalVector("_UniformDetail", CheckoutMarketPaint.Oklab(Hex(Shown.uniformDetail, "D3A53D")));
            Refresh();
        }

        void Update()
        {
            if (dirty || Time.unscaledTime >= nextCheck) Refresh();
            AnimateSigns(Time.unscaledTime);
        }

        // Pieces come and go (the shell is rebuilt, staff are hired, the stage dressing changes, the shop grows): the
        // style is checked twice a second, and at once when it changes.
        void Refresh()
        {
            dirty = false; nextCheck = Time.unscaledTime + .5f;
            if (!world) return;
            FloorAndWalls();
            Uniforms();
            Signs();
        }

        public static string Hex(string value, string fallback)
        {
            var h = CheckoutMarketPaint.Norm(value);
            return h == "" ? fallback : h;
        }
        static Color C(string hex) { ColorUtility.TryParseHtmlString("#" + hex, out var c); return c; }

        // ------------------------------------------------------------------ floor and walls
        // Metres per texture tile and smoothness of each texture (Resources/CheckoutStyle/Textures, ArtSource gen_textures.py).
        static readonly Dictionary<string, (float tiling, float gloss)> Surfaces = new Dictionary<string, (float, float)>
        {
            ["Floor_madeira-clara"] = (1.6f, .55f), ["Floor_taco"] = (1.2f, .6f), ["Floor_porcelanato"] = (1.2f, .7f),
            ["Floor_xadrez"] = (1.2f, .65f), ["Floor_cimento"] = (3f, .45f), ["Floor_ladrilho"] = (.8f, .5f),
            ["Floor_granilite"] = (2f, .6f), ["Floor_terracota"] = (1.4f, .35f), ["Floor_vinil"] = (1.2f, .55f),
            ["Floor_marmore-escuro"] = (2.4f, .8f),
            ["Wall_tinta"] = (2f, .3f), ["Wall_metro"] = (.6f, .75f), ["Wall_tijolinho"] = (1f, .2f), ["Wall_ripado"] = (1f, .35f),
            ["Wall_pastilha"] = (.4f, .8f), ["Wall_listrado"] = (.9f, .25f), ["Wall_floral"] = (1.2f, .25f), ["Wall_concreto"] = (2.4f, .2f),
            ["Wall_lousa"] = (2f, .15f), ["Wall_pedra"] = (1.2f, .15f),
        };
        readonly Dictionary<string, Material> surfaceMaterials = new Dictionary<string, Material>();
        readonly Dictionary<Renderer, Material> originalSurface = new Dictionary<Renderer, Material>();
        static Shader styleSurface;
        Transform overlay; MeshRenderer overlayFloor, overlayBack, overlayLeft, overlayRight;
        /// <summary>QA: renderers wearing a style surface now.</summary>
        public int StyledSurfaces { get; private set; }

        Material Surface(string kind, string id, string colour)
        {
            if (string.IsNullOrEmpty(id) || id == Classic) return null;
            string key = kind + "_" + id;
            if (!surfaceMaterials.TryGetValue(key, out var m))
            {
                var albedo = Resources.Load<Texture2D>("CheckoutStyle/Textures/" + key + "_albedo");
                if (!albedo) { surfaceMaterials[key] = null; return null; }
                if (!styleSurface) styleSurface = Shader.Find("MarketDay/Style Surface");
                if (!styleSurface) return null;
                m = new Material(styleSurface) { name = "Style " + key };
                m.SetTexture("_MainTex", albedo);
                var normal = Resources.Load<Texture2D>("CheckoutStyle/Textures/" + key + "_normal");
                if (normal) m.SetTexture("_BumpMap", normal);
                var mask = Resources.Load<Texture2D>("CheckoutStyle/Textures/" + key + "_mask");
                if (mask) m.SetTexture("_TintMask", mask);
                var s = Surfaces.TryGetValue(key, out var v) ? v : (tiling: 1.5f, gloss: .4f);
                m.SetFloat("_Tiling", s.tiling); m.SetFloat("_Glossiness", s.gloss);
                surfaceMaterials[key] = m;
            }
            if (m) m.SetColor("_TintColor", C(Hex(colour, "FFFFFF")));
            return m;
        }

        void Wear(Renderer r, Material m)
        {
            if (!r) return;
            if (m)
            {
                if (!originalSurface.ContainsKey(r)) originalSurface[r] = r.sharedMaterial;
                if (r.sharedMaterial != m) r.sharedMaterial = m;
                StyledSurfaces++;
            }
            else if (originalSurface.TryGetValue(r, out var original)) { r.sharedMaterial = original; originalSurface.Remove(r); }
        }

        void FloorAndWalls()
        {
            StyledSurfaces = 0;
            bool unlocked = State == null || State.insideUnlocked;
            var floor = unlocked ? Surface("Floor", Shown.floor, Shown.floorColor) : null;
            var wall = unlocked ? Surface("Wall", Shown.wall, Shown.wallColor) : null;
            // The market building.
            var shell = world.GetComponentInChildren<CheckoutMarketShell>(true);
            if (shell)
            {
                var f = shell.transform.Find("Base/Floor");
                if (f) Wear(f.GetComponent<Renderer>(), floor);
                foreach (Transform t in shell.Walls)
                    if (t.name.EndsWith(" Inner")) Wear(t.GetComponent<Renderer>(), wall);
            }
            // The shops with an inside: quads over the model's floor and walls.
            ShopOverlay(floor, wall);
        }

        // The shops' inner wall faces in model metres (the same frame as CheckoutStall's ShopPlan: x right, z back), the
        // floor's top and the walls' tops as the game cuts them (the CUT_ parts are hidden), measured on the models
        // (ArtSource/market_style: Blender, faces facing into the shop). The minimercado's back wall goes up to 3.56 m;
        // its name board and pilasters stand in front of it and stay as they are.
        struct ShopFaces { public float xMin, xMax, back, floor, sideTop, backTop; }
        static readonly Dictionary<string, ShopFaces> ShopWalls = new Dictionary<string, ShopFaces>
        {
            ["Era4_Spati"] = new ShopFaces { xMin = -3.25f, xMax = 3.85f, back = 2.95f, floor = .06f, sideTop = 1.1f, backTop = 1.1f },
            ["Era5_Quitanda"] = new ShopFaces { xMin = -4.0f, xMax = 4.0f, back = 4.0f, floor = .07f, sideTop = 1.19f, backTop = 1.19f },
            ["Era6_Minimercado"] = new ShopFaces { xMin = -5.95f, xMax = 5.45f, back = 4.75f, floor = .17f, sideTop = 1.29f, backTop = 3.56f },
        };

        void ShopOverlay(Material floor, Material wall)
        {
            Transform model = null; ShopFaces plan = default;
            if (CheckoutStall.ShopInside && (floor || wall))
                foreach (Transform child in world)
                {
                    if (!child.gameObject.activeInHierarchy) continue;
                    foreach (var pair in ShopWalls) if (child.name.StartsWith(pair.Key)) { model = child; plan = pair.Value; break; }
                    if (model) break;
                }
            if (!model) { if (overlay) overlay.gameObject.SetActive(false); return; }
            if (!overlay)
            {
                overlay = new GameObject("Market Style Overlay").transform; overlay.SetParent(world, false);
                overlayFloor = Quad("Floor"); overlayBack = Quad("Back wall"); overlayLeft = Quad("Left wall"); overlayRight = Quad("Right wall");
            }
            overlay.gameObject.SetActive(true);
            var o = model.position; float k = model.lossyScale.x;
            float x0 = o.x + plan.xMin * k, x1 = o.x + plan.xMax * k, z1 = o.z + plan.back * k, z0 = CheckoutStall.InteriorFloor.yMin;
            float y0 = o.y + plan.floor * k, sideTop = o.y + plan.sideTop * k, backTop = o.y + plan.backTop * k;
            const float inset = .012f;
            overlayFloor.gameObject.SetActive(floor);
            if (floor)
            {
                var t = overlayFloor.transform;
                t.position = new Vector3((x0 + x1) * .5f, y0 + .004f, (z0 + z1) * .5f); t.rotation = Quaternion.Euler(90, 0, 0);
                t.localScale = new Vector3(x1 - x0, z1 - z0, 1); overlayFloor.sharedMaterial = floor; StyledSurfaces++;
            }
            foreach (var q in new[] { overlayBack, overlayLeft, overlayRight }) { q.gameObject.SetActive(wall); if (wall) { q.sharedMaterial = wall; StyledSurfaces++; } }
            if (!wall) return;
            Place(overlayBack.transform, new Vector3((x0 + x1) * .5f, (y0 + backTop) * .5f, z1 - inset), Quaternion.identity, new Vector3(x1 - x0, backTop - y0, 1));
            Place(overlayLeft.transform, new Vector3(x0 + inset, (y0 + sideTop) * .5f, (z0 + z1) * .5f), Quaternion.Euler(0, -90, 0), new Vector3(z1 - z0, sideTop - y0, 1));
            Place(overlayRight.transform, new Vector3(x1 - inset, (y0 + sideTop) * .5f, (z0 + z1) * .5f), Quaternion.Euler(0, 90, 0), new Vector3(z1 - z0, sideTop - y0, 1));
        }
        static void Place(Transform t, Vector3 p, Quaternion q, Vector3 s) { t.position = p; t.rotation = q; t.localScale = s; }
        MeshRenderer Quad(string name)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad); go.name = name;
            var col = go.GetComponent<Collider>(); if (col) Destroy(col);
            go.transform.SetParent(overlay, false);
            var mr = go.GetComponent<MeshRenderer>(); mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return mr;
        }

        // ------------------------------------------------------------------ uniform
        // Each character texture's garment colours (OKLab medians under its mask, ArtSource gen_uniform_masks.py).
        static readonly Dictionary<string, (Vector3 main, Vector3 detail)> UniformRefs = new Dictionary<string, (Vector3, Vector3)>
        {
            ["Staff_Clerk"] = (new Vector3(.2929f, -.0045f, -.0685f), new Vector3(.5266f, .1788f, .0896f)),
            ["Staff_Cleaner"] = (new Vector3(.469f, -.0965f, .0643f), new Vector3(.8281f, .003f, .1561f)),
            ["CheckoutWoman_BaseColor"] = (new Vector3(.5036f, -.0811f, -.0154f), new Vector3(.9137f, .0075f, .0465f)),
            ["Worker_Baker"] = (new Vector3(.994f, 0, 0), new Vector3(.548f, .056f, .0808f)),
            ["Worker_Butcher"] = (new Vector3(.7731f, -.0184f, -.0408f), new Vector3(.9747f, .0052f, .0142f)),
            ["Worker_Fishmonger"] = (new Vector3(.4859f, -.0384f, -.0909f), new Vector3(.9943f, 0, 0)),
        };
        readonly Dictionary<Material, Material> uniformCopy = new Dictionary<Material, Material>();   // original → copy (null: not a uniform)
        readonly Dictionary<Material, Material> uniformOriginal = new Dictionary<Material, Material>(); // copy → original
        readonly HashSet<Renderer> uniformTracked = new HashSet<Renderer>();
        readonly List<Transform> staff = new List<Transform>();
        readonly List<Material> mats = new List<Material>();
        readonly List<Renderer> scratch = new List<Renderer>();
        Transform staffRoot; static Shader uniformStandard;
        /// <summary>QA: staff renderers in the player's uniform now.</summary>
        public int UniformRenderers => uniformTracked.Count;

        void Uniforms()
        {
            bool on = !string.IsNullOrEmpty(Shown.uniform) && Shown.uniform != Classic;
            if (!on) { if (uniformTracked.Count > 0) RestoreUniforms(); return; }
            staff.Clear();
            foreach (Transform w in world) if (w.name.StartsWith("Worker_") && !w.name.StartsWith("Worker_Delivery")) staff.Add(w);
            if (!staffRoot) { var go = GameObject.Find("Market Staff"); staffRoot = go ? go.transform : null; }
            if (staffRoot) foreach (Transform w in staffRoot) if (w.GetComponent<MarketDay.MarketCharacterAnimator>()) staff.Add(w);
            foreach (var w in staff)
            {
                w.GetComponentsInChildren(true, scratch);
                foreach (var r in scratch)
                {
                    if (!(r is SkinnedMeshRenderer) && !(r is MeshRenderer)) continue;
                    r.GetSharedMaterials(mats);
                    bool changed = false;
                    for (int i = 0; i < mats.Count; i++)
                    {
                        var m = mats[i]; if (!m || uniformOriginal.ContainsKey(m)) continue;
                        var copy = UniformCopy(m); if (!copy) continue;
                        mats[i] = copy; changed = true;
                    }
                    if (changed) { r.sharedMaterials = mats.ToArray(); uniformTracked.Add(r); }
                    mats.Clear();
                }
                scratch.Clear();
            }
        }

        void RestoreUniforms()
        {
            foreach (var r in uniformTracked)
            {
                if (!r) continue;
                r.GetSharedMaterials(mats);
                bool changed = false;
                for (int i = 0; i < mats.Count; i++) if (mats[i] && uniformOriginal.TryGetValue(mats[i], out var o)) { mats[i] = o; changed = true; }
                if (changed) r.sharedMaterials = mats.ToArray();
                mats.Clear();
            }
            uniformTracked.Clear();
        }

        Material UniformCopy(Material m)
        {
            if (uniformCopy.TryGetValue(m, out var cached)) return cached;
            Material copy = null;
            var tex = m.HasProperty("_MainTex") ? m.mainTexture : null;
            if (tex && UniformRefs.TryGetValue(tex.name, out var refs))
            {
                var mask = Resources.Load<Texture2D>("CheckoutStyle/Uniform/" + tex.name + "_UniformMask");
                if (mask)
                {
                    if (m.shader && m.shader.name == "MarketDay/Soft Painted") { copy = new Material(m); copy.EnableKeyword("UNIFORM_PAINT"); }
                    else
                    {
                        if (!uniformStandard) uniformStandard = Shader.Find("MarketDay/Uniform Standard");
                        if (uniformStandard)
                        {
                            copy = new Material(uniformStandard);
                            copy.SetColor("_Color", m.HasProperty("_Color") ? m.color : Color.white);
                            copy.mainTexture = tex; copy.mainTextureScale = m.mainTextureScale; copy.mainTextureOffset = m.mainTextureOffset;
                            if (m.HasProperty("_Glossiness")) copy.SetFloat("_Glossiness", m.GetFloat("_Glossiness"));
                            if (m.HasProperty("_Metallic")) copy.SetFloat("_Metallic", m.GetFloat("_Metallic"));
                        }
                    }
                    if (copy)
                    {
                        copy.name = m.name + " (uniform)";
                        copy.SetTexture("_UniformMask", mask);
                        copy.SetVector("_UniformMainRef", refs.main); copy.SetVector("_UniformDetailRef", refs.detail);
                        uniformOriginal[copy] = m;
                    }
                }
            }
            uniformCopy[m] = copy;
            return copy;
        }

        // ------------------------------------------------------------------ the sign
        static readonly string[] SignRoots = { "S0 name board", "S1 rear sign", "S2 name", "S4 name" };
        static readonly Dictionary<string, string> FontFiles = new Dictionary<string, string>
        {
            ["redonda"] = "CheckoutDesktop/Fonts/Fredoka_700Bold", ["esportiva"] = "CheckoutStyle/Fonts/Nunito-BlackItalic",
            ["elegante"] = "CheckoutStyle/Fonts/Caladea-Bold", ["moderna"] = "CheckoutStyle/Fonts/Inter-SemiBold",
            ["digital"] = "CheckoutDesktop/Fonts/JetBrainsMono_700Bold", ["pesada"] = "CheckoutStyle/Fonts/Inter-Black",
            ["fina"] = "CheckoutStyle/Fonts/Inter-Light",
        };
        static readonly Dictionary<string, TMP_FontAsset> fontAssets = new Dictionary<string, TMP_FontAsset>();
        static Texture2D dot; static Material bulbMaterial;
        static readonly Color Gold = new Color(1f, .82f, .38f), GoldSide = new Color(.55f, .36f, .1f);

        sealed class Layer { public TextMeshPro text; public string role; public float alpha = 1; public Vector3[] rest; public bool lifted; }
        sealed class Sign
        {
            public Transform root, holder, plate; public readonly List<MeshRenderer> originals = new List<MeshRenderer>();
            public TextMesh front; public readonly List<Layer> layers = new List<Layer>(); public readonly List<MeshRenderer> bulbs = new List<MeshRenderer>();
            public string key = "", text = ""; public Vector2 size; public int letters; public float letterHeight;
        }
        readonly Dictionary<Transform, Sign> signs = new Dictionary<Transform, Sign>();
        /// <summary>QA: signs drawn by the style now.</summary>
        public int StyledSigns { get; private set; }
        public static string SignReport { get; private set; } = "";

        bool SignStyled => (State == null || State.signUnlocked) && Shown.sign != null &&
            (Shown.sign.look != Classic || Shown.sign.font != Classic || Shown.sign.effect != Static);

        void Signs()
        {
            var dressing = world.Find("Market Stage Dressing");
            StyledSigns = 0;
            if (!dressing) return;
            bool on = SignStyled;
            foreach (var name in SignRoots)
            {
                var root = dressing.Find(name); if (!root) continue;
                if (!signs.TryGetValue(root, out var s)) { s = Collect(root); signs[root] = s; }
                if (!s.front) continue;
                if (!on || !root.gameObject.activeInHierarchy) { Restore(s); continue; }
                Dress(s);
                StyledSigns++;
            }
        }

        static Sign Collect(Transform root)
        {
            var s = new Sign { root = root };
            float frontZ = float.MaxValue;
            foreach (Transform c in root)
            {
                var tm = c.GetComponent<TextMesh>(); if (!tm) continue;
                var mr = c.GetComponent<MeshRenderer>(); if (mr) s.originals.Add(mr);
                if (c.localPosition.z < frontZ) { frontZ = c.localPosition.z; s.front = tm; }
            }
            return s;
        }

        static void Restore(Sign s)
        {
            foreach (var r in s.originals) if (r) r.enabled = true;
            if (s.holder) s.holder.gameObject.SetActive(false);
        }

        void Dress(Sign s)
        {
            var sign = Shown.sign;
            string text = s.front.text ?? "";
            string key = sign.font + "|" + sign.look + "|" + text;
            // Measure the original letters (before hiding them; a renamed chain changes their width).
            if (key != s.key || s.size == Vector2.zero)
            {
                foreach (var r in s.originals) if (r) r.enabled = true;
                var b = s.front.GetComponent<MeshRenderer>().bounds;
                float scale = Mathf.Max(1e-4f, s.root.lossyScale.x);
                var right = s.root.right;
                var size = new Vector2(Mathf.Abs(right.x) >= Mathf.Abs(right.z) ? b.size.x : b.size.z, b.size.y);
                if (size.x > .05f && size.y > .02f) s.size = size / scale;
            }
            foreach (var r in s.originals) if (r) r.enabled = false;
            // (active before building: TextMeshPro makes no mesh under an inactive object)
            if (s.holder) s.holder.gameObject.SetActive(true);
            if (key != s.key) { Build(s, sign, text); s.key = key; }
            Colourise(s, 0, true);
        }

        /// <summary>The TextMeshPro font of a sign font id (the picker shows each in its own font too).</summary>
        public static TMP_FontAsset SignFont(string id)
        {
            if (string.IsNullOrEmpty(id)) id = Classic;
            if (fontAssets.TryGetValue(id, out var cached) && cached) return cached;
            // Clássica: the stage dressing's own letters (CheckoutMarketStagesBuilder: Resources/MarketBold).
            Font font = id == Classic ? Resources.Load<Font>("MarketBold") : (FontFiles.TryGetValue(id, out var path) ? Resources.Load<Font>(path) : null);
            TMP_FontAsset asset = null;
            if (font)
            {
                try { asset = TMP_FontAsset.CreateFontAsset(font, 72, 14, GlyphRenderMode.SDFAA, 1024, 1024, AtlasPopulationMode.Dynamic, true); }
                catch (Exception e) { Debug.LogWarning("Market style font " + id + ": " + e.Message); }
            }
            if (!asset) asset = TMP_Settings.defaultFontAsset;
            fontAssets[id] = asset;
            return asset;
        }

        // The layers of a look, front first: "face" (the letters), "side" (the depth behind, like the original gold letters),
        // "halo" (the neon's glow).
        void Build(Sign s, StyleSign sign, string text)
        {
            if (!s.holder)
            {
                s.holder = new GameObject("Style sign").transform; s.holder.SetParent(s.root, false);
            }
            foreach (Transform c in s.holder) Destroy(c.gameObject);
            s.layers.Clear(); s.bulbs.Clear(); s.plate = null;
            s.holder.localPosition = s.front.transform.localPosition; s.holder.localRotation = s.front.transform.localRotation; s.holder.localScale = Vector3.one;
            var font = SignFont(sign.font);
            float h = Mathf.Max(.1f, s.size.y);           // letter height (root units)
            float depth = Mathf.Clamp(h * .035f, .01f, .05f);
            string look = sign.look;
            bool neon = look == "neon" || look == "neon-placa";
            int sides = look == "liso" ? 0 : look == "caixa" ? 6 : look == "contorno" ? 2 : look == "degrade" ? 3 : look == "colorido" ? 4 : look == "lampadas" ? 3 : neon ? 0 : 4;
            if (neon)
            {
                AddLayer(s, font, text, "halo", depth * 2.2f, .65f, 1);
                AddLayer(s, font, text, "halo", depth * 1.4f, .9f, 2);
            }
            for (int i = sides; i >= 1; i--) AddLayer(s, font, text, "side", depth * i, 0, 0);
            AddLayer(s, font, text, "face", -.002f, 0, 0);
            var face = s.layers[s.layers.Count - 1].text;
            face.ForceMeshUpdate();
            s.letters = 0; for (int i = 0; i < face.textInfo.characterCount; i++) if (face.textInfo.characterInfo[i].isVisible) s.letters++;
            s.letterHeight = h;
            if (look == "contorno") { face.outlineWidth = .28f; }
            if (neon) { face.outlineWidth = .16f; face.fontMaterial.SetFloat(ShaderUtilities.ID_FaceDilate, -.05f); }
            // the text's real extent for the plate and the bulbs
            var bounds = face.textBounds;
            if (look == "neon-placa")
            {
                var plate = GameObject.CreatePrimitive(PrimitiveType.Cube); plate.name = "Neon plate";
                var col = plate.GetComponent<Collider>(); if (col) Destroy(col);
                plate.transform.SetParent(s.holder, false);
                plate.transform.localPosition = new Vector3(bounds.center.x, bounds.center.y, depth * 3.4f);
                plate.transform.localScale = new Vector3(bounds.size.x + h * .7f, bounds.size.y + h * .55f, depth * 1.5f);
                var mr = plate.GetComponent<MeshRenderer>();
                mr.sharedMaterial = PlateMaterial(); mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                s.plate = plate.transform;
            }
            if (look == "lampadas")
            {
                float w = bounds.size.x + h * .7f, hh = bounds.size.y + h * .42f, step = h * .4f;
                int nx = Mathf.Max(4, Mathf.RoundToInt(w / step)), ny = Mathf.Max(2, Mathf.RoundToInt(hh / step));
                var cx = bounds.center.x; var cy = bounds.center.y;
                for (int i = 0; i <= nx; i++) { float x = cx - w * .5f + w * i / nx; Bulb(s, new Vector3(x, cy + hh * .5f, -.004f), h); Bulb(s, new Vector3(x, cy - hh * .5f, -.004f), h); }
                for (int j = 1; j < ny; j++) { float y = cy - hh * .5f + hh * j / ny; Bulb(s, new Vector3(cx - w * .5f, y, -.004f), h); Bulb(s, new Vector3(cx + w * .5f, y, -.004f), h); }
            }
            foreach (var l in s.layers)
            {
                l.text.ForceMeshUpdate();
                var info = l.text.textInfo;
                l.rest = info != null && info.meshInfo != null && info.meshInfo.Length > 0 && info.meshInfo[0].vertices != null ? (Vector3[])info.meshInfo[0].vertices.Clone() : null;
            }
            SignReport = $"{s.root.name}: '{text}' font={sign.font} look={look} layers={s.layers.Count} letters={s.letters} size={s.size}";
        }

        void AddLayer(Sign s, TMP_FontAsset font, string text, string role, float z, float alpha, int haloStep)
        {
            var go = new GameObject(role + " " + s.layers.Count, typeof(RectTransform));
            go.transform.SetParent(s.holder, false);
            go.transform.localPosition = new Vector3(0, 0, z);
            var t = go.AddComponent<TextMeshPro>();
            t.font = font; t.text = text; t.alignment = TextAlignmentOptions.Center; t.textWrappingMode = TextWrappingModes.NoWrap;
            t.enableAutoSizing = true; t.fontSizeMin = .05f; t.fontSizeMax = 400; t.overflowMode = TextOverflowModes.Overflow;
            t.rectTransform.sizeDelta = new Vector2(s.size.x * 1.04f, s.size.y * 1.55f);
            t.characterSpacing = Shown.sign.font == "digital" ? 4 : 0;
            t.color = Color.white; t.richText = false;
            var mr = t.GetComponent<MeshRenderer>(); if (mr) { mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false; }
            if (role == "halo")
            {
                var m = t.fontMaterial;
                m.SetFloat(ShaderUtilities.ID_FaceDilate, haloStep == 1 ? .7f : .35f);
                m.SetFloat(ShaderUtilities.ID_OutlineSoftness, haloStep == 1 ? 1f : .6f);
                t.outlineWidth = haloStep == 1 ? .35f : .2f;
            }
            s.layers.Add(new Layer { text = t, role = role, alpha = role == "halo" ? alpha : 1 });
        }

        void Bulb(Sign s, Vector3 at, float h)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad); go.name = "Bulb";
            var col = go.GetComponent<Collider>(); if (col) Destroy(col);
            go.transform.SetParent(s.holder, false); go.transform.localPosition = at; go.transform.localScale = Vector3.one * h * .34f;
            var mr = go.GetComponent<MeshRenderer>(); mr.sharedMaterial = BulbMaterial(); mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
            s.bulbs.Add(mr);
        }

        static Material BulbMaterial()
        {
            if (bulbMaterial) return bulbMaterial;
            if (!dot)
            {
                const int n = 64; dot = new Texture2D(n, n, TextureFormat.RGBA32, false) { name = "Style bulb", wrapMode = TextureWrapMode.Clamp };
                var px = new Color[n * n];
                for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
                    {
                        float d = Vector2.Distance(new Vector2(x + .5f, y + .5f), new Vector2(n / 2f, n / 2f)) / (n / 2f);
                        float core = Mathf.Clamp01((.42f - d) / .06f), glow = Mathf.Clamp01(1 - d) * .55f;
                        px[y * n + x] = new Color(1, 1, 1, Mathf.Clamp01(core + glow * glow));
                    }
                dot.SetPixels(px); dot.Apply();
            }
            bulbMaterial = new Material(Shader.Find("Sprites/Default")) { name = "Style bulb", mainTexture = dot };
            return bulbMaterial;
        }
        static Material plateMaterial;
        static Material PlateMaterial()
        {
            if (plateMaterial) return plateMaterial;
            plateMaterial = new Material(Shader.Find("Standard")) { name = "Style neon plate", color = new Color(.07f, .08f, .11f) };
            plateMaterial.SetFloat("_Glossiness", .55f);
            return plateMaterial;
        }

        // ------------------------------------------------------------------ colours and effects
        static readonly float[] Speeds = { .55f, 1f, 1.8f };
        static float Hash(float a, float b) => Mathf.Repeat(Mathf.Sin(a * 12.9898f + b * 78.233f) * 43758.5453f, 1f);
        MaterialPropertyBlock block;

        void AnimateSigns(float now)
        {
            if (signs.Count == 0 || !SignStyled) return;
            foreach (var s in signs.Values)
                if (s.holder && s.holder.gameObject.activeInHierarchy) Colourise(s, now, false);
        }

        // Per letter: the look's colour × the effect's light (0 off … 1 on), the wave's lift, written into the layers' vertices.
        void Colourise(Sign s, float now, bool force)
        {
            var sign = Shown.sign; if (sign == null || s.layers.Count == 0) return;
            string effect = sign.effect ?? Static, look = sign.look ?? Classic;
            float t = now * Speeds[Mathf.Clamp(sign.speed, 0, 2)];
            Color main = C(Hex(sign.main, "FFD54F")), second = C(Hex(sign.second, "E53935"));
            var palette = PaletteColours(sign.palette);
            bool neon = look == "neon" || look == "neon-placa";
            int n = Mathf.Max(1, s.letters);
            foreach (var layer in s.layers)
            {
                var tmp = layer.text; if (!tmp) continue; var info = tmp.textInfo; if (info == null || info.meshInfo == null || info.meshInfo.Length == 0) continue;
                bool moved = false; int letter = 0;
                for (int ci = 0; ci < info.characterCount; ci++)
                {
                    var ch = info.characterInfo[ci]; if (!ch.isVisible) continue;
                    int mi = ch.materialReferenceIndex; if (mi < 0 || mi >= info.meshInfo.Length) continue;
                    var colours = info.meshInfo[mi].colors32; var verts = info.meshInfo[mi].vertices;
                    int vi = ch.vertexIndex; if (colours == null || vi + 3 >= colours.Length) continue;
                    float light = Light(effect, letter, n, t);
                    Color top, bottom;
                    LetterColours(look, effect, layer.role, letter, n, t, main, second, palette, out top, out bottom);
                    if (effect == "brilho") { float pos = Mathf.Repeat(t * .9f, 1.6f) * (n + 4) - 2; float boost = Mathf.Exp(-(letter - pos) * (letter - pos) / 1.5f); top = Color.Lerp(top, Color.white, boost * .7f); bottom = Color.Lerp(bottom, Color.white, boost * .7f); }
                    float dim = neon ? .16f : .35f;
                    top = Color.Lerp(top * dim, top, light); bottom = Color.Lerp(bottom * dim, bottom, light);
                    float a = layer.role == "halo" ? layer.alpha * light : 1;
                    if (neon && layer.role == "face") { top = Color.Lerp(top, Color.white, .45f * light); bottom = Color.Lerp(bottom, Color.white, .45f * light); }
                    top.a = bottom.a = a;
                    colours[vi] = bottom; colours[vi + 1] = top; colours[vi + 2] = top; colours[vi + 3] = bottom;
                    if (effect == "onda" && mi == 0 && layer.rest != null && vi + 3 < layer.rest.Length)
                    {
                        float lift = Mathf.Sin(t * 4f - letter * .6f) * s.letterHeight * .1f;
                        for (int k = 0; k < 4; k++) verts[vi + k] = layer.rest[vi + k] + new Vector3(0, lift, 0);
                        moved = true;
                    }
                    else if (layer.lifted && mi == 0 && layer.rest != null && vi + 3 < layer.rest.Length)
                    {
                        for (int k = 0; k < 4; k++) verts[vi + k] = layer.rest[vi + k];
                        moved = true;
                    }
                    letter++;
                }
                layer.lifted = effect == "onda";
                // the neon tube's edge follows the letters' colour
                if (neon && layer.role == "face" && force) tmp.outlineColor = main;
                if (neon && layer.role == "halo" && force) tmp.outlineColor = new Color(main.r, main.g, main.b, .5f);
                if (look == "contorno" && layer.role == "face" && force) tmp.outlineColor = second;
                tmp.UpdateVertexData(moved ? TMP_VertexDataUpdateFlags.Colors32 | TMP_VertexDataUpdateFlags.Vertices : TMP_VertexDataUpdateFlags.Colors32);
            }
            // theatre bulbs chase round the frame
            for (int i = 0; i < s.bulbs.Count; i++)
            {
                var b = s.bulbs[i]; if (!b) continue;
                float on = effect == Static ? 1 : effect == "piscar" ? Light(effect, 0, 1, t) : (Mathf.Repeat(i - t * 6f, 3f) < 1.4f ? 1f : .25f);
                var c = Color.Lerp(new Color(1f, .93f, .7f) * .35f, new Color(1f, .93f, .7f), on); c.a = 1;
                if (block == null) block = new MaterialPropertyBlock();
                block.SetColor("_Color", c); b.SetPropertyBlock(block);
            }
        }

        static Color Darker(Color c, float k) => new Color(c.r * k, c.g * k, c.b * k, c.a);

        void LetterColours(string look, string effect, string role, int letter, int n, float t, Color main, Color second, Color[] palette, out Color top, out Color bottom)
        {
            Color face;
            if (look == Classic) face = Gold;
            else if (look == "colorido") face = palette[letter % palette.Length];
            else face = main;
            Color low = look == "degrade" ? second : face;
            if (effect == "alternar") { bool flip = ((Mathf.FloorToInt(t * 1.25f) + letter) & 1) == 1; face = flip ? second : (look == "colorido" ? face : main); low = face; }
            if (effect == "arco-iris") { face = Color.HSVToRGB(Mathf.Repeat(t * .15f + letter / (n * 1.3f), 1f), .75f, 1f); low = look == "degrade" ? Color.HSVToRGB(Mathf.Repeat(t * .15f + letter / (n * 1.3f) + .15f, 1f), .75f, 1f) : face; }
            if (role == "side")
            {
                Color side = look == Classic ? Color.Lerp(GoldSide, Gold, .25f)
                    : look == "caixa" || look == "contorno" || look == "lampadas" ? Darker(effect == "arco-iris" || effect == "alternar" ? face : second, .7f)
                    : Darker(face, .55f);
                top = bottom = side; return;
            }
            top = face; bottom = low;
        }

        static float Light(string effect, int letter, int n, float t)
        {
            switch (effect)
            {
                case "pulsar": return .35f + .65f * (.5f + .5f * Mathf.Sin(t * 2.4f));
                case "piscar": return Mathf.Repeat(t * .8f, 1f) < .62f ? 1 : 0;
                case "falhando":
                    {
                        float slot = Mathf.Floor(t * 1.3f); int bad = Mathf.FloorToInt(Hash(slot, 3) * n);
                        if (letter != bad || Mathf.Repeat(t * 1.3f, 1f) > .55f) return 1;
                        return Hash(Mathf.Floor(t * 14f), letter) > .45f ? 1 : .08f;
                    }
                case "letra":
                    {
                        float step = .22f, run = n * step, cycle = run + 1.6f, p = Mathf.Repeat(t, cycle);
                        if (p < run) return letter < p / step ? 1 : .1f;
                        return Mathf.Repeat(p - run, .4f) < .25f ? 1 : .2f;
                    }
                case "onda": return .85f + .15f * Mathf.Sin(t * 4f - letter * .6f);
                default: return 1;
            }
        }

        Color[] PaletteColours(string id)
        {
            var list = State?.palettes;
            if (list != null) foreach (var p in list) if (p.id == id && p.colors != null && p.colors.Length > 0) { var r = new Color[p.colors.Length]; for (int i = 0; i < r.Length; i++) r[i] = C(Hex(p.colors[i], "FFFFFF")); return r; }
            return new[] { C("E53935"), C("FB8C00"), C("FDD835"), C("43A047"), C("1E88E5"), C("8E24AA") };
        }

        // ------------------------------------------------------------------ QA
        public string QaReport() => $"style floor={Shown.floor} wall={Shown.wall} uniform={Shown.uniform} sign={Shown.sign?.font}/{Shown.sign?.look}/{Shown.sign?.effect} surfaces={StyledSurfaces} uniformRenderers={UniformRenderers} signs={StyledSigns} {SignReport}";
    }

    /// <summary>What the market wears (the snapshot's style without the catalogue), and the JSON applyMarketStyle takes.</summary>
    [Serializable]
    public class StyleChoice
    {
        public string floor = CheckoutMarketStyle.Classic, floorColor = "", wall = CheckoutMarketStyle.Classic, wallColor = "";
        public string uniform = CheckoutMarketStyle.Classic, uniformMain = "", uniformDetail = "";
        public StyleSign sign = new StyleSign { font = CheckoutMarketStyle.Classic, look = CheckoutMarketStyle.Classic, effect = CheckoutMarketStyle.Static, main = "", second = "", palette = "arco-iris", speed = 1 };

        public static StyleChoice From(StyleState s)
        {
            var c = new StyleChoice();
            if (s == null) return c;
            c.floor = s.floor ?? c.floor; c.floorColor = s.floorColor ?? ""; c.wall = s.wall ?? c.wall; c.wallColor = s.wallColor ?? "";
            c.uniform = s.uniform ?? c.uniform; c.uniformMain = s.uniformMain ?? ""; c.uniformDetail = s.uniformDetail ?? "";
            if (s.sign != null) c.sign = new StyleSign { font = s.sign.font ?? CheckoutMarketStyle.Classic, look = s.sign.look ?? CheckoutMarketStyle.Classic, effect = s.sign.effect ?? CheckoutMarketStyle.Static, main = s.sign.main ?? "", second = s.sign.second ?? "", palette = s.sign.palette ?? "arco-iris", speed = s.sign.speed };
            return c;
        }
        public StyleChoice Clone() => JsonUtility.FromJson<StyleChoice>(JsonUtility.ToJson(this));
        public string Json() => JsonUtility.ToJson(this);
        public bool Same(StyleChoice o) => o != null && Json() == o.Json();
    }
}
