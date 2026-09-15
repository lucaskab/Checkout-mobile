using UnityEngine;
using UnityEngine.Tilemaps;

namespace MarketDay
{
    public enum MarketTerrainKind { Grass, Road, River, Courtyard, Path, Bridge }

    [CreateAssetMenu(menuName = "Supermarket/Terrain tile")]
    public class MarketTerrainTile : RuleTile
    {
        public MarketTerrainKind kind;
        public Sprite sprite;
        public static readonly Vector3Int[] Neighbors =
        {
            Vector3Int.up, Vector3Int.right, Vector3Int.down, Vector3Int.left,
            new Vector3Int(1,1,0), new Vector3Int(1,-1,0), new Vector3Int(-1,-1,0), new Vector3Int(-1,1,0)
        };

        public bool ConnectsTo(MarketTerrainTile other)
        {
            if (!other) return false;
            if (other.kind == kind) return true;
            switch (kind)
            {
                case MarketTerrainKind.Road:
                    return other.kind == MarketTerrainKind.Courtyard || other.kind == MarketTerrainKind.Bridge;
                case MarketTerrainKind.Path:
                    return other.kind == MarketTerrainKind.Courtyard || other.kind == MarketTerrainKind.Road;
                case MarketTerrainKind.Bridge:
                    return other.kind == MarketTerrainKind.Road;
                case MarketTerrainKind.River:
                    return other.kind == MarketTerrainKind.Bridge;
                case MarketTerrainKind.Courtyard:
                    return other.kind == MarketTerrainKind.Road || other.kind == MarketTerrainKind.Path;
                default:
                    return false;
            }
        }

        public override bool RuleMatch(int neighbor, TileBase other)
        {
            if (other is RuleOverrideTile replacement) other = replacement.m_InstanceTile;
            bool connects = ConnectsTo(other as MarketTerrainTile);
            if (neighbor == TilingRuleOutput.Neighbor.This) return connects;
            if (neighbor == TilingRuleOutput.Neighbor.NotThis) return !connects;
            return true;
        }

        public override void RefreshTile(Vector3Int position, ITilemap tilemap)
        {
            tilemap.RefreshTile(position);
            foreach (var offset in Neighbors) tilemap.RefreshTile(position + offset);
        }

        public override bool RuleMatches(TilingRule rule, Vector3Int position, ITilemap tilemap, ref Matrix4x4 transform)
        {
            if (kind != MarketTerrainKind.Path) return base.RuleMatches(rule, position, tilemap, ref transform);
            int paths = 0;
            for (int i = 0; i < 4; i++)
                if (tilemap.GetTile<MarketTerrainTile>(position + Neighbors[i])?.kind == MarketTerrainKind.Path) paths++;
            for (int i = 0; i < rule.m_Neighbors.Count; i++)
            {
                var offset = rule.m_NeighborPositions[i];
                var other = tilemap.GetTile<MarketTerrainTile>(position + offset);
                bool connects = ConnectsTo(other);
                // Extend an endpoint into pavement. A footway running beside a
                // driveway must not sprout a junction at every adjacent cell.
                if (other && other.kind != MarketTerrainKind.Path)
                    connects &= paths != 2 && tilemap.GetTile<MarketTerrainTile>(position - offset)?.kind == MarketTerrainKind.Path;
                if (rule.m_Neighbors[i] == TilingRuleOutput.Neighbor.This && !connects) return false;
                if (rule.m_Neighbors[i] == TilingRuleOutput.Neighbor.NotThis && connects) return false;
            }
            transform = Matrix4x4.identity;
            return true;
        }

        public override void GetTileData(Vector3Int position, ITilemap tilemap, ref TileData data)
        {
            // Rule ids contain the matched neighbor mask. The shared terrain shader
            // draws its edges from that mask, preserving the existing painted textures.
            int mask = 0;
            data.sprite = m_DefaultSprite ? m_DefaultSprite : sprite;
            var transform = Matrix4x4.identity;
            foreach (var rule in m_TilingRules)
                if (RuleMatches(rule, position, tilemap, ref transform))
                {
                    mask = rule.m_Id;
                    data.sprite = rule.m_Sprites[0];
                    break;
                }
            int courtyards = 0, river = 0;
            for (int i = 0; i < 4; i++)
            {
                var neighbor = tilemap.GetTile<MarketTerrainTile>(position + Neighbors[i]);
                if (neighbor && (neighbor.kind == MarketTerrainKind.Courtyard ||
                    (kind == MarketTerrainKind.Road && neighbor.kind == MarketTerrainKind.Path))) courtyards |= 1 << i;
                if (neighbor && (neighbor.kind == MarketTerrainKind.River || neighbor.kind == MarketTerrainKind.Bridge)) river |= 1 << i;
            }
            data.color = new Color(((int)kind + 1) / 8f, (mask & 15) / 15f,
                (kind == MarketTerrainKind.Bridge ? river : mask >> 4) / 15f, 1f - courtyards / 32f);
            data.transform = Matrix4x4.identity;
            data.flags = TileFlags.LockAll;
            data.colliderType = Tile.ColliderType.None;
        }
    }
}
