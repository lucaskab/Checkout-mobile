using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

public static class CheckoutTerrainRules
{
    public static void Configure(MarketTerrainTile tile)
    {
        tile.m_DefaultSprite = tile.sprite;
        tile.m_DefaultColliderType = Tile.ColliderType.None;
        tile.m_TilingRules.Clear();
        bool area = tile.kind == MarketTerrainKind.River || tile.kind == MarketTerrainKind.Grass || tile.kind == MarketTerrainKind.Courtyard;
        for (int mask = 0; mask < (area ? 256 : 16); mask++)
        {
            // A diagonal joins only when both adjacent cardinal cells also join.
            // This reduces the 256 combinations to the standard 47 terrain patterns.
            bool valid = true;
            for (int corner = 0; corner < 4; corner++)
                if ((mask & (16 << corner)) != 0 &&
                    ((mask & (1 << corner)) == 0 || (mask & (1 << ((corner + 1) % 4))) == 0))
                    valid = false;
            if (!valid) continue;
            var rule = new RuleTile.TilingRule
            {
                m_Id = mask,
                m_Sprites = new[] { tile.sprite },
                m_Output = RuleTile.TilingRuleOutput.OutputSprite.Single,
                m_ColliderType = Tile.ColliderType.None,
                m_RuleTransform = RuleTile.TilingRuleOutput.Transform.Fixed
            };
            rule.m_NeighborPositions.Clear();
            for (int i = 0; i < MarketTerrainTile.Neighbors.Length; i++)
                if ((mask & (1 << i)) != 0)
                {
                    rule.m_NeighborPositions.Add(MarketTerrainTile.Neighbors[i]);
                    rule.m_Neighbors.Add(RuleTile.TilingRuleOutput.Neighbor.This);
                }
            tile.m_TilingRules.Add(rule);
        }
        // Missing positions are Don't Care: more specific rules must win first.
        tile.m_TilingRules = tile.m_TilingRules.OrderByDescending(rule => rule.m_Neighbors.Count).ToList();
        tile.UpdateNeighborPositions();
        EditorUtility.SetDirty(tile);
    }
}
