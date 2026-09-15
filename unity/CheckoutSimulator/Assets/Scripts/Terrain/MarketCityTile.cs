using UnityEngine;
using UnityEngine.Tilemaps;

namespace MarketDay
{
    public enum MarketCityKind { Street, Crosswalk, Sidewalk, Plaza, Asphalt, SidewalkEdge, SidewalkCorner }

    [CreateAssetMenu(menuName = "Supermarket/City RuleTile")]
    public class MarketCityTile : RuleTile
    {
        public MarketCityKind kind;
        public bool IsStreet => kind == MarketCityKind.Street || kind == MarketCityKind.Crosswalk;

        public override bool RuleMatch(int neighbor, TileBase other)
        {
            if (other is RuleOverrideTile replacement) other = replacement.m_InstanceTile;
            bool matches = other is MarketCityTile city && (IsStreet ? city.IsStreet : city.kind == kind);
            if (neighbor == TilingRuleOutput.Neighbor.This) return matches;
            if (neighbor == TilingRuleOutput.Neighbor.NotThis) return !matches;
            return true;
        }

        public override void GetTileData(Vector3Int position, ITilemap tilemap, ref TileData data)
        {
            base.GetTileData(position, tilemap, ref data);
            int mask = 0;
            for (int direction = 0; direction < 4; direction++)
                if (tilemap.GetTile(position + MarketTerrainTile.Neighbors[direction]) is MarketCityTile neighbor && neighbor.IsStreet)
                    mask |= 1 << direction;
            // Open only a road endpoint into a yard; parallel asphalt must not create repeated junctions.
            if (IsStreet && mask != 0 && (mask & (mask - 1)) == 0)
                for (int direction = 0; direction < 4; direction++)
                    if ((mask & (1 << ((direction + 2) % 4))) != 0 &&
                        tilemap.GetTile(position + MarketTerrainTile.Neighbors[direction]) is MarketCityTile apron &&
                        apron.kind == MarketCityKind.Asphalt)
                    { mask |= 1 << direction; break; }
            // Connectivity is independent of sprite rotation; the shader draws continuous world-space streets.
            data.color = new Color((int)kind / 7f, mask / 15f, 0f, 1f);
            data.colliderType = Tile.ColliderType.None;
            data.flags = TileFlags.LockAll;
            // The supplied sheet has uneven tile bounds. Fit each sliced sprite
            // to the existing 4 m grid. A 1 mm overlap on each edge prevents raster cracks.
            if (data.sprite)
                data.transform *= Matrix4x4.Scale(new Vector3(4.002f / data.sprite.bounds.size.x, 4.002f / data.sprite.bounds.size.y, 1f));
        }
    }
}
