// "Estilo do mercado": the staff uniform in the player's colours (CheckoutMarketStyle.cs).
// A mask baked offline per character texture (Resources/CheckoutStyle/Uniform/<texture>_UniformMask.png: R = the main
// garment, G = the details) says which texels are the uniform; each takes the hue and chroma of the chosen colour and
// keeps its lightness relative to the garment's own colour (_UniformMainRef / _UniformDetailRef: the garment's median
// OKLab, measured with the mask), so folds, seams and baked shading survive. A white chef's jacket has no hue of its
// own: it simply takes the new colour's chroma. Going darker than the garment compresses the shading so a white jacket
// painted navy does not turn black in its folds.
#ifndef CHECKOUT_UNIFORM_PAINT_INCLUDED
#define CHECKOUT_UNIFORM_PAINT_INCLUDED
#include "Assets/Resources/CheckoutPaint/MarketPaint.cginc"

// Globals (Shader.SetGlobalVector): OKLab of the two uniform colours.
float4 _UniformMain, _UniformDetail;
// Per material.
float4 _UniformMainRef, _UniformDetailRef;
sampler2D _UniformMask;

float3 UM_Map(float3 lab, float3 ref, float3 target)
{
    float refC = length(ref.yz), c = length(lab.yz);
    float ratio = refC > 0.03 ? clamp(c / refC, 0, 1.5) : 1;
    float tC = length(target.yz);
    float2 hue = target.yz / max(tC, 1e-5);
    float k = clamp(target.x / max(ref.x, 1e-3), 0.35, 1);
    float L = clamp(target.x + (lab.x - ref.x) * k, 0.03, 0.985);
    return MP_FromOklab(float3(L, hue * tC * ratio));
}

float3 UniformPaint(float3 albedo, float2 uv)
{
    float2 w = tex2D(_UniformMask, uv).rg;
    if (w.x + w.y < 0.004) return albedo;
    float3 lab = MP_ToOklab(albedo);
    float3 painted = albedo;
    if (w.x > 0.004) painted = lerp(painted, UM_Map(lab, _UniformMainRef.xyz, _UniformMain.xyz), w.x);
    if (w.y > 0.004) painted = lerp(painted, UM_Map(lab, _UniformDetailRef.xyz, _UniformDetail.xyz), w.y);
    return painted;
}
#endif
