// "Cores do mercado": the player's two colours on the market (CheckoutMarketPaint.cs).
// The market was painted in two brand colours, navy #1D2B4F (and its support blue #2E4A7D) and gold #D3A53D.
// A painted material swaps them for the player's choice in OKLab: the texel keeps its lightness relative to the
// brand colour (shading, wood grain, baked AO and the two-tone navy survive) and its relative chroma, and takes
// the hue and chroma of the new colour. Which texels change is decided per material (CheckoutMarketPaint.Classify):
//   _PaintWhole 1 / 2   the whole material is navy / gold (flat colours, the navy panel and gold textures);
//   _PaintUseMask 1     a mask baked offline from the texture (R = navy, G = gold): the era atlases;
//   otherwise           a tight colour key (navy hue, dark; gold hue, saturated, light) on the texel.
// Only the market's own renderers get painted materials, and only while a palette other than Clássico is on, so the
// city, the people, the products and the HUD never go through this.
#ifndef CHECKOUT_MARKET_PAINT_INCLUDED
#define CHECKOUT_MARKET_PAINT_INCLUDED

// Globals (Shader.SetGlobalVector): the OKLab L, a, b of the two chosen colours.
float4 _MarketPaintPrimary, _MarketPaintAccent;
// Per material.
float _PaintWhole, _PaintUseMask;
sampler2D _PaintMask;

// OKLab of the brand colours (linear sRGB in, Björn Ottosson's matrices).
static const float3 MP_NAVY = float3(0.29683, -0.00439, -0.06811);
static const float3 MP_GOLD = float3(0.74593, 0.01306, 0.12926);

float3 MP_ToOklab(float3 c)
{
    float3 lms = mul(float3x3(0.4122214708, 0.5363325363, 0.0514459929,
                              0.2119034982, 0.6806995451, 0.1073969566,
                              0.0883024619, 0.2817188376, 0.6299787005), max(c, 0));
    lms = pow(max(lms, 1e-7), 1.0 / 3.0);
    return mul(float3x3(0.2104542553, 0.7936177850, -0.0040720468,
                        1.9779984951, -2.4285922050, 0.4505937099,
                        0.0259040371, 0.7827717662, -0.8086757660), lms);
}

float3 MP_FromOklab(float3 lab)
{
    float3 lms = mul(float3x3(1.0, 0.3963377922, 0.2158037581,
                              1.0, -0.1055613423, -0.0638541748,
                              1.0, -0.0894841821, -1.2914855379), lab);
    lms = lms * lms * lms;
    return max(mul(float3x3(4.0767416613, -3.3077115904, 0.2309699287,
                            -1.2684380041, 2.6097574007, -0.3413193963,
                            -0.0041960865, -0.7034186145, 1.7076147009), lms), 0);
}

// The texel as a shade of `brand`, moved onto `target`.
float3 MP_Map(float3 lab, float3 brand, float3 target)
{
    float chroma = length(lab.yz) / length(brand.yz);
    float L = clamp(target.x + (lab.x - brand.x), 0.03, 0.985);
    return MP_FromOklab(float3(L, target.yz * clamp(chroma, 0, 1.5)));
}

// Albedo (linear) → painted albedo. uv: the material's main uv (for the mask).
float3 MarketPaint(float3 albedo, float2 uv)
{
    float3 lab = MP_ToOklab(albedo);
    float2 w;
    if (_PaintWhole > 1.5) w = float2(0, 1);
    else if (_PaintWhole > 0.5) w = float2(1, 0);
    else if (_PaintUseMask > 0.5) w = tex2D(_PaintMask, uv).rg;
    else
    {
        float c = length(lab.yz);
        float2 hue = lab.yz / max(c, 1e-5);
        float toNavy = dot(hue, float2(-0.06427, -0.99793)); // cos of the hue angle to navy
        float toGold = dot(hue, float2(0.10051, 0.99494));   // … and to gold
        w.x = smoothstep(0.9397, 0.9781, toNavy) * smoothstep(0.025, 0.045, c) * smoothstep(0.08, 0.12, lab.x) * (1 - smoothstep(0.50, 0.56, lab.x));
        w.y = smoothstep(0.9903, 0.9969, toGold) * smoothstep(0.100, 0.118, c) * smoothstep(0.64, 0.68, lab.x) * (1 - smoothstep(0.90, 0.95, lab.x));
    }
    if (w.x + w.y < 0.004) return albedo;
    float3 painted = albedo;
    if (w.x > 0.004) painted = lerp(painted, MP_Map(lab, MP_NAVY, _MarketPaintPrimary.xyz), w.x);
    if (w.y > 0.004) painted = lerp(painted, MP_Map(lab, MP_GOLD, _MarketPaintAccent.xyz), w.y);
    return painted;
}

#endif
