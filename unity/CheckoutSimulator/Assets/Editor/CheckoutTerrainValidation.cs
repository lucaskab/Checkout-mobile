using System;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

public static class CheckoutTerrainValidation
{
    [MenuItem("Supermarket/Validate terrain RuleTiles")]
    public static void Validate()
    {
        var names = new[] { "Grass", "Road", "Water", "Courtyard", "Path", "Bridge" };
        var tiles = names.Select(name => AssetDatabase.LoadAssetAtPath<MarketTerrainTile>(
            CheckoutTerrainBuilder.AssetRoot + name + "Tile.asset")).ToArray();
        int checks = 0;
        void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
            checks++;
        }
        foreach (var tile in tiles)
        {
            Require(tile && tile.sprite && tile.m_DefaultSprite, "Terrain sprite is missing.");
            int count = tile.kind == MarketTerrainKind.River || tile.kind == MarketTerrainKind.Grass ||
                tile.kind == MarketTerrainKind.Courtyard ? 47 : 16;
            Require(tile.m_TilingRules.Count == count, "Incomplete rules for " + tile.kind);
            Require(tile.m_TilingRules.Select(rule => rule.m_Id).Distinct().Count() == count,
                "Duplicate rule ids for " + tile.kind);
            Require(tile.m_TilingRules.All(rule => rule.m_ColliderType == Tile.ColliderType.None),
                "Terrain must preserve the existing gameplay navigation.");
        }

        var temporary = new GameObject("Terrain rule validation", typeof(Grid)) { hideFlags = HideFlags.HideAndDontSave };
        var child = new GameObject("Validation tiles", typeof(Tilemap)) { hideFlags = HideFlags.HideAndDontSave };
        child.transform.SetParent(temporary.transform);
        var map = child.GetComponent<Tilemap>();
        try
        {
            // Exercise Unity's actual tile refresh/data pipeline for every neighborhood,
            // including concave banks, wide rivers, endpoints and intersections.
            foreach (var tile in new[] { tiles[1], tiles[2], tiles[3], tiles[4] })
                for (int mask = 0; mask < 256; mask++)
                {
                    map.ClearAllTiles();
                    map.SetTile(Vector3Int.zero, tile);
                    for (int i = 0; i < 8; i++)
                        if ((mask & (1 << i)) != 0) map.SetTile(MarketTerrainTile.Neighbors[i], tile);
                    var color = map.GetColor(Vector3Int.zero);
                    Require(Mathf.RoundToInt(color.g * 15) == (mask & 15), tile.kind + " cardinal connection mismatch: " + mask);
                    Require(map.GetSprite(Vector3Int.zero) == tile.sprite, "Missing matched sprite for " + tile.kind);
                    if (tile.kind == MarketTerrainKind.River || tile.kind == MarketTerrainKind.Courtyard)
                        for (int corner = 0; corner < 4; corner++)
                        {
                            bool expected = (mask & (16 << corner)) != 0 &&
                                (mask & (1 << corner)) != 0 && (mask & (1 << ((corner + 1) % 4))) != 0;
                            bool actual = (Mathf.RoundToInt(color.b * 15) & (1 << corner)) != 0;
                            Require(actual == expected, tile.kind + " diagonal bank mismatch: " + mask);
                        }
                }

            map.ClearAllTiles();
            map.SetTile(Vector3Int.zero,tiles[4]);
            map.SetTile(Vector3Int.up,tiles[4]);
            map.SetTile(Vector3Int.down,tiles[4]);
            map.SetTile(Vector3Int.left,tiles[3]);
            Require(Mathf.RoundToInt(map.GetColor(Vector3Int.zero).g*15)==5, "Parallel footway sprouts a driveway junction.");
            map.SetTile(Vector3Int.down,tiles[1]);
            Require(Mathf.RoundToInt(map.GetColor(Vector3Int.zero).g*15)==5, "Path endpoint does not reach the road.");
            map.SetTile(Vector3Int.up,tiles[0]);
            Require(Mathf.RoundToInt(map.GetColor(Vector3Int.zero).g*15)==0, "Erasing a path does not refresh its neighbors.");

            map.ClearAllTiles();
            map.SetTile(Vector3Int.zero,tiles[2]);
            map.SetTile(Vector3Int.right,tiles[5]);
            Require(Mathf.RoundToInt(map.GetColor(Vector3Int.zero).g*15)==2, "River stops at the bridge.");
            map.SetTile(Vector3Int.up,tiles[1]);
            Require(tiles[1].ConnectsTo(tiles[5]) && tiles[5].ConnectsTo(tiles[1]), "Bridge does not connect to the road.");
        }
        finally { UnityEngine.Object.DestroyImmediate(temporary); }

        var sceneMap = UnityEngine.Object.FindObjectsByType<Tilemap>().FirstOrDefault(t => t.name == CheckoutTerrainBuilder.TerrainName);
        Require(sceneMap, "Supermarket terrain is missing.");
        var used = sceneMap.GetTilesBlock(sceneMap.cellBounds).OfType<MarketTerrainTile>().ToArray();
        foreach (var kind in Enum.GetValues(typeof(MarketTerrainKind)).Cast<MarketTerrainKind>())
            Require(used.Any(tile => tile.kind == kind), "Level is missing " + kind);
        var material = sceneMap.GetComponent<TilemapRenderer>().sharedMaterial;
        for (int pass = 0; pass < material.passCount; pass++) ShaderUtil.CompilePass(material,pass,true);
        Require(!ShaderUtil.GetShaderMessages(material.shader).Any(message =>
            message.severity == UnityEditor.Rendering.ShaderCompilerMessageSeverity.Error), "Terrain shader has compilation errors.");

        var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var yard = world.Find("Loading Yard Details/YardPaint").GetComponent<MeshFilter>().sharedMesh;
        var crossing = world.Find("Riverbank Details/YardPaint").GetComponent<MeshFilter>().sharedMesh;
        Require(yard != crossing && yard.bounds.center.z > 15 && crossing.bounds.center.z < -10,
            "Riverbank geometry overwrites loading yard markings.");
        var cells = sceneMap.GetTilesBlock(sceneMap.cellBounds);
        var transforms = world.GetComponentsInChildren<Transform>().Select(t => t.localToWorldMatrix).ToArray();
        CheckoutTerrainLevelBuilder.Apply(world,sceneMap,tiles);
        Require(cells.SequenceEqual(sceneMap.GetTilesBlock(sceneMap.cellBounds)), "Reapplying terrain overwrites painted cells.");
        Require(transforms.SequenceEqual(world.GetComponentsInChildren<Transform>().Select(t => t.localToWorldMatrix)),
            "Reapplying terrain moves existing objects.");

        Debug.Log("CHECKOUT_RULE_TERRAIN_VALIDATION_OK checks=" + checks + " neighborhoods=1024 cells=" + used.Length);
    }
}
