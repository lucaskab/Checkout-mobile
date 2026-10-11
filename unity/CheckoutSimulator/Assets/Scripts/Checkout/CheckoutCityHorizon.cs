using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Tilemaps;

namespace Checkout
{
    // The map carries on past its edge, so it no longer floats on a void: the map simply made bigger.
    //  - the ground: a ring of tiles around the city tilemap, each a copy of the nearest edge tile (same sprite,
    //    same tile data, same "MarketDay/City Tiles" material and settings), so the streets, cycle lanes,
    //    sidewalks, paving and the park run on exactly as they are drawn on the map;
    //  - the blocks out there are built up with copies of the map's own houses (their own materials);
    //  - a dark fog (CheckoutEdgeFog, on the camera) closes in right at the edge of the map; the camera clears to
    //    the fog colour.
    // Scenery only: no colliders, no scripts, no navigation. The camera's pan limits stay as they are.
    public sealed class CheckoutCityHorizon : MonoBehaviour
    {
        public static readonly Color DayHaze = new Color(.05f, .05f, .06f);
        // The fog starts a little inside the map's edge and is solid this far out (metres).
        public const float FogStart = -1f, FogEnd = 20f;
        const int RingCells = 5;          // tiles added round the map on every side
        const float Houses = 22f;         // how far out the park trees go (the fog is solid past it)
        // Only a few houses, in a loose row hugging the map's edge: the city "goes on" into the fog. It used to pack
        // every block out to 22 m (~180 copies of 150-175k-triangle Tripo houses, ~28M triangles a frame), which
        // was what made the iPhone lag.
        const float HouseRow = 8f;        // how far past the edge a house may stand
        const float HouseGap = 5f;        // free space kept around each one
        const int HousesPerBlock = 3;     // five blocks round the map: ~15 houses in all
        const int ParkTrees = 12;

        Transform world, root; Rect playable; Camera view;
        TilemapRenderer tilesRenderer; MeshRenderer ring; MaterialPropertyBlock block; Texture atlas; float refresh;
        readonly List<Rect> placed = new List<Rect>();
        System.Random random;
        List<Template> houses, trees;
        public int Buildings { get; private set; }
        public Rect Playable => playable;

        sealed class Template
        {
            public readonly List<(Mesh mesh, Material[] materials, Matrix4x4 local)> parts = new List<(Mesh, Material[], Matrix4x4)>();
            public Bounds box;            // in the template's own (unscaled) frame
            public Vector3 front;         // its street side, in that frame
        }

        public void Initialize(Transform worldRoot)
        {
            world = worldRoot;
            view = Camera.main;
            foreach (var r in FindObjectsByType<TilemapRenderer>(FindObjectsSortMode.None))
                if (r.sharedMaterial && r.sharedMaterial.shader.name == "MarketDay/City Tiles") { tilesRenderer = r; break; }
            if (tilesRenderer) { var b = tilesRenderer.bounds; playable = Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z); }
            else playable = Rect.MinMaxRect(-41.5f, -45.5f, 41.5f, 49.5f);
            // The sky behind the city: the camera clears to the fog (the events tint it for rain and night).
            if (view)
            {
                view.backgroundColor = DayHaze; view.clearFlags = CameraClearFlags.SolidColor; view.farClipPlane = Mathf.Max(view.farClipPlane, 700f);
                var fog = view.GetComponent<CheckoutEdgeFog>() ?? view.gameObject.AddComponent<CheckoutEdgeFog>();
                fog.Configure(playable, FogStart, FogEnd);
            }
            random = new System.Random(5119);
            // The world root is turned round (yaw 180): the horizon keeps world axes.
            root = new GameObject("City Horizon").transform; root.SetParent(world, false);
            root.SetPositionAndRotation(Vector3.zero, Quaternion.identity); root.localScale = Vector3.one;
            BuildGround();
            BuildCity();
        }

        // The tilemap's own settings (streets, park, market block) follow it: copy them now and then.
        void Update()
        {
            if (!ring || !tilesRenderer || (refresh -= Time.unscaledDeltaTime) > 0) return;
            refresh = .5f; CopySettings();
        }

        void CopySettings()
        {
            block ??= new MaterialPropertyBlock();
            tilesRenderer.GetPropertyBlock(block);
            if (atlas) block.SetTexture("_MainTex", atlas);
            ring.sharedMaterial = tilesRenderer.sharedMaterial;
            ring.SetPropertyBlock(block);
        }

        // ------------------------------------------------------------------ ground
        // A ring of cells round the tilemap, in its own frame: every new cell repeats the nearest cell on the map's
        // edge (sprite and tile data), so whatever reaches the edge goes on.
        void BuildGround()
        {
            if (!tilesRenderer) return;
            var map = tilesRenderer.GetComponent<Tilemap>(); if (!map) return;
            var cells = map.cellBounds; var frame = map.transform;
            var vertices = new List<Vector3>(); var uvs = new List<Vector2>(); var colors = new List<Color>(); var triangles = new List<int>();
            for (int x = cells.xMin - RingCells; x < cells.xMax + RingCells; x++)
                for (int y = cells.yMin - RingCells; y < cells.yMax + RingCells; y++)
                {
                    if (x >= cells.xMin && x < cells.xMax && y >= cells.yMin && y < cells.yMax) continue;   // the map itself
                    var source = new Vector3Int(Mathf.Clamp(x, cells.xMin, cells.xMax - 1), Mathf.Clamp(y, cells.yMin, cells.yMax - 1), cells.zMin);
                    Sprite sprite = null;
                    for (int z = cells.zMin; z < cells.zMax && !sprite; z++) { source.z = z; sprite = map.GetSprite(source); }
                    if (!sprite) continue;
                    atlas ??= sprite.texture;
                    // The tile's data colour as the tilemap hands it to the shader (linear in a linear project: the
                    // shader turns it back to gamma to read the kind and the street mask).
                    var color = map.GetColor(source);
                    if (QualitySettings.activeColorSpace == ColorSpace.Linear) color = color.linear;
                    var su = sprite.uv;
                    float u0 = su.Min(q => q.x), u1 = su.Max(q => q.x), v0 = su.Min(q => q.y), v1 = su.Max(q => q.y);
                    // The tile's own turn/flip, so its picture lies the same way as on the map.
                    var turn = map.GetTransformMatrix(source).inverse;
                    Vector2 UV(float cx, float cy)
                    {
                        var s = turn.MultiplyVector(new Vector3(cx - .5f, cy - .5f, 0));
                        float sx = Mathf.Clamp01(s.x / Mathf.Max(.0001f, Mathf.Abs(turn.MultiplyVector(Vector3.right).magnitude)) + .5f);
                        float sy = Mathf.Clamp01(s.y / Mathf.Max(.0001f, Mathf.Abs(turn.MultiplyVector(Vector3.up).magnitude)) + .5f);
                        return new Vector2(Mathf.Lerp(u0, u1, sx), Mathf.Lerp(v0, v1, sy));
                    }
                    Vector3 Corner(int cx, int cy) => frame.InverseTransformPoint(map.CellToWorld(new Vector3Int(cx, cy, source.z)));
                    int i = vertices.Count;
                    vertices.Add(Corner(x, y)); vertices.Add(Corner(x, y + 1)); vertices.Add(Corner(x + 1, y + 1)); vertices.Add(Corner(x + 1, y));
                    uvs.Add(UV(0, 0)); uvs.Add(UV(0, 1)); uvs.Add(UV(1, 1)); uvs.Add(UV(1, 0));
                    for (int k = 0; k < 4; k++) colors.Add(color);
                    triangles.AddRange(new[] { i, i + 1, i + 2, i, i + 2, i + 3 });
                }
            if (vertices.Count == 0) return;
            var mesh = new Mesh { name = "City tiles ring", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.SetVertices(vertices); mesh.SetUVs(0, uvs); mesh.SetColors(colors); mesh.SetTriangles(triangles, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            var go = new GameObject("Ground (city tiles)"); go.transform.SetParent(root, true);
            var t = map.transform;
            go.transform.SetPositionAndRotation(t.position, t.rotation); go.transform.localScale = t.lossyScale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            ring = go.AddComponent<MeshRenderer>();
            ring.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; ring.receiveShadows = tilesRenderer.receiveShadows;
            CopySettings();
        }

        // ------------------------------------------------------------------ buildings
        // The map's blocks run on past its edge: between the local streets (x ±23.5) and either side of the
        // avenue (z -18.5), sidewalks included (CheckoutStreetLayout).
        void BuildCity()
        {
            houses = Templates(world.Find("City Establishments"), t => true, true);
            trees = Templates(world, t => t.name.StartsWith("City Tree"), false, 3);
            const float E = 400f;
            var columns = new[] { (-E, -29.75f), (-17.25f, 17.25f), (29.75f, E) };
            var rows = new[] { (-E, -28.5f), (-8.5f, E) };
            foreach (var c in columns)
                foreach (var r in rows)
                {
                    var b = Rect.MinMaxRect(c.Item1, r.Item1, c.Item2, r.Item2);
                    bool park = Mathf.Abs(b.center.x) < 1 && r.Item2 < 0;   // Central Park, south of the avenue
                    if (park) Park(b); else Block(b);
                }
        }

        float Distance(Vector2 p)
        {
            float dx = Mathf.Max(0, Mathf.Max(playable.xMin - p.x, p.x - playable.xMax));
            float dz = Mathf.Max(0, Mathf.Max(playable.yMin - p.y, p.y - playable.yMax));
            return Mathf.Sqrt(dx * dx + dz * dz);
        }
        bool OnMap(Rect footprint) => footprint.Overlaps(Rect.MinMaxRect(playable.xMin - .3f, playable.yMin - .3f, playable.xMax + .3f, playable.yMax + .3f));

        // Houses packed over the part of a block just outside the map, each facing the nearest street side.
        void Block(Rect block)
        {
            if (houses.Count == 0) return;
            placed.Clear();
            float x0 = Mathf.Max(block.xMin, playable.xMin - Houses), x1 = Mathf.Min(block.xMax, playable.xMax + Houses);
            float z0 = Mathf.Max(block.yMin, playable.yMin - Houses), z1 = Mathf.Min(block.yMax, playable.yMax + Houses);
            // Spots along the edge, tried in a shuffled (seeded, so always the same) order: the few houses spread out
            // along the block instead of piling up in its first corner.
            var spots = new List<Vector2>();
            for (float z = z0 + .3f; z < z1; z += 1f)
                for (float x = x0 + .3f; x < x1; x += 1f)
                    if (Distance(new Vector2(x, z)) <= HouseRow) spots.Add(new Vector2(x, z));
            for (int i = spots.Count - 1; i > 0; i--) { int j = random.Next(i + 1); (spots[i], spots[j]) = (spots[j], spots[i]); }
            foreach (var p in spots)
                {
                    if (placed.Count >= HousesPerBlock) return;
                    if (Distance(p) > HouseRow || OnMap(new Rect(p, Vector2.one * .1f)) || placed.Any(q => q.Contains(p))) continue;
                    // Rows like the map's own in the same block: the side blocks face the local street (east block
                    // west, west block east), the block behind the market faces the avenue side (south).
                    var facing = block.center.x > 20 ? Vector3.left : block.center.x < -20 ? Vector3.right : Vector3.back;
                    var t = houses[random.Next(houses.Count)]; Footprint(t, out var w, out var d);
                    var size = Mathf.Abs(facing.z) > .5f ? new Vector2(w, d) : new Vector2(d, w);
                    var rect = new Rect(p, size);
                    if (rect.xMax > block.xMax - .2f || rect.yMax > block.yMax - .2f || OnMap(rect) || placed.Any(q => q.Overlaps(Shrink(rect, -HouseGap)))) continue;
                    Place(t, rect.center, facing); placed.Add(rect); Buildings++;
                }
        }

        // More of the park: trees scattered over the lawn (the tiles draw the lawn and paths).
        void Park(Rect block)
        {
            if (trees.Count == 0) return;
            for (int k = 0; k < ParkTrees; k++)
            {
                var p = new Vector2(Mathf.Lerp(block.xMin + 1.5f, block.xMax - 1.5f, (float)random.NextDouble()), Mathf.Lerp(playable.yMin - Houses, playable.yMin, (float)random.NextDouble()));
                if (OnMap(new Rect(p - Vector2.one * 1.5f, Vector2.one * 3))) continue;
                Place(trees[random.Next(trees.Count)], p, Vector3.forward, Mathf.Lerp(.8f, 1.25f, (float)random.NextDouble()), (float)random.NextDouble() * 360f);
            }
        }

        static Rect Shrink(Rect r, float by) => Rect.MinMaxRect(r.xMin + by, r.yMin + by, r.xMax - by, r.yMax - by);

        void Footprint(Template t, out float width, out float depth)
        {
            bool frontX = Mathf.Abs(t.front.x) > .5f;
            width = frontX ? t.box.size.z : t.box.size.x; depth = frontX ? t.box.size.x : t.box.size.z;
        }

        // A copy of a template with its front to `facing`, its footprint centred on `centre`.
        void Place(Template t, Vector2 centre, Vector3 facing, float scale = 1, float extraYaw = 0)
        {
            var rotation = Quaternion.Euler(0, Vector3.SignedAngle(t.front, facing, Vector3.up) + extraYaw, 0);
            var offset = rotation * Vector3.Scale(new Vector3(t.box.center.x, 0, t.box.center.z), Vector3.one * scale);
            var frame = Matrix4x4.TRS(new Vector3(centre.x, 0, centre.y) - offset, rotation, Vector3.one * scale);
            var holder = new GameObject("Horizon " + (t.parts.Count > 0 ? t.parts[0].mesh.name : "piece")).transform; holder.SetParent(root, false);
            foreach (var part in t.parts)
            {
                var m = frame * part.local;
                var go = new GameObject(part.mesh.name); go.transform.SetParent(holder, false);
                go.transform.SetPositionAndRotation(m.GetColumn(3), m.rotation); go.transform.localScale = m.lossyScale;
                go.AddComponent<MeshFilter>().sharedMesh = part.mesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = part.materials;   // lit and shaded like the map's own
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;               // out in the fog: no shadow pass
            }
        }

        // The city's own models to copy: their meshes in their own frame and the side that faces the street.
        List<Template> Templates(Transform group, System.Func<Transform, bool> pick, bool buildings, int limit = 40)
        {
            var list = new List<Template>(); if (!group) return list;
            var seen = new HashSet<string>();
            IEnumerable<Transform> candidates = buildings ? group.Cast<Transform>() : group.GetComponentsInChildren<Transform>(true).Where(pick);
            foreach (var t in candidates)
            {
                if (list.Count >= limit) break;
                if (!pick(t) || t.name.Contains("vehicle")) continue;
                string key = System.Text.RegularExpressions.Regex.Replace(t.name, @"[\s(]*\d+\)?$", "");
                if (!buildings && !seen.Add(key)) continue;
                // The template's own frame keeps only its heading: the model's tilt (FBX roots lie at -90 on X)
                // stays inside the parts, so the copies stand up.
                var heading = Quaternion.Euler(0, t.eulerAngles.y, 0);
                var frame = Matrix4x4.TRS(t.position, heading, Vector3.one).inverse;
                var template = new Template(); bool first = true;
                foreach (var mf in t.GetComponentsInChildren<MeshFilter>(true))
                {
                    var mr = mf.GetComponent<MeshRenderer>();
                    if (!mf.sharedMesh || !mr || !mr.enabled || mr.forceRenderingOff) continue;
                    var local = frame * mf.transform.localToWorldMatrix;
                    template.parts.Add((mf.sharedMesh, mr.sharedMaterials, local));
                    var b = mf.sharedMesh.bounds;
                    for (int i = 0; i < 8; i++)
                    {
                        var c = local.MultiplyPoint3x4(new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z));
                        if (first) { template.box = new Bounds(c, Vector3.zero); first = false; } else template.box.Encapsulate(c);
                    }
                }
                if (template.parts.Count == 0) continue;
                if (buildings)
                {
                    // Only the houses along the side streets: their front is towards the street (x ±23.5).
                    var centre = Matrix4x4.TRS(t.position, heading, Vector3.one).MultiplyPoint3x4(template.box.center);
                    if (Mathf.Abs(centre.x) < CheckoutStreetLayout.LocalCurbOuter || template.box.size.y < 3 || template.box.size.x > 22 || template.box.size.z > 22) continue;
                    var front = new Vector3(-Mathf.Sign(centre.x), 0, 0);
                    var local = Quaternion.Inverse(heading) * front; local.y = 0;
                    template.front = Mathf.Abs(local.x) > Mathf.Abs(local.z) ? new Vector3(Mathf.Sign(local.x), 0, 0) : new Vector3(0, 0, Mathf.Sign(local.z));
                }
                else template.front = Vector3.forward;
                list.Add(template);
            }
            return list;
        }

        public string TileReport()
        {
            if (!tilesRenderer) return "no tiles";
            var map = tilesRenderer.GetComponent<Tilemap>(); var cb = map.cellBounds; var lines = new List<string>();
            lines.Add($"cells {cb} size {map.layoutGrid.cellSize} anchor {map.tileAnchor} orientation {map.orientation} pos {map.transform.position} rot {map.transform.eulerAngles} scale {map.transform.lossyScale} tilemap color {map.color}");
            lines.Add($"cell {cb.xMin},{cb.yMin} world {map.CellToWorld(new Vector3Int(cb.xMin, cb.yMin, 0))} next {map.CellToWorld(new Vector3Int(cb.xMin + 1, cb.yMin + 1, 0))}");
            int my = (cb.yMin + cb.yMax) / 2, mx = (cb.xMin + cb.xMax) / 2;
            for (int x = cb.xMin; x < cb.xMin + 4; x++) { var c = new Vector3Int(x, my, 0); var s = map.GetSprite(c); lines.Add($"west row {x},{my}: sprite {(s ? s.name : "-")} colour {map.GetColor(c)} flags {map.GetTileFlags(c)} centre {map.GetCellCenterWorld(c)}"); }
            for (int x = cb.xMax - 4; x < cb.xMax; x++) { var c = new Vector3Int(x, my, 0); var s = map.GetSprite(c); lines.Add($"east row {x},{my}: sprite {(s ? s.name : "-")} colour {map.GetColor(c)} centre {map.GetCellCenterWorld(c)}"); }
            for (int y = cb.yMax - 4; y < cb.yMax; y++) { var c = new Vector3Int(mx, y, 0); var s = map.GetSprite(c); lines.Add($"north col {mx},{y}: sprite {(s ? s.name : "-")} colour {map.GetColor(c)} centre {map.GetCellCenterWorld(c)}"); }
            var mf = tilesRenderer.GetComponent<MeshFilter>();
            return string.Join("\n", lines);
        }

        public string Describe() => TileReport() + "\n" + $"horizon: playable {playable} ring {(ring ? ring.GetComponent<MeshFilter>().sharedMesh.vertexCount / 4 : 0)} tiles, atlas {(atlas ? atlas.name : "none")}, houses {houses?.Count ?? 0} trees {trees?.Count ?? 0} copies {Buildings} renderers {root.GetComponentsInChildren<Renderer>().Length}";
    }
}
