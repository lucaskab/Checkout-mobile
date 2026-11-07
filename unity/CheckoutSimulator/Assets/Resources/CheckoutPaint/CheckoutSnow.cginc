// Snow cover of the city for the "nevasca" event (CheckoutSnowCover sets the globals; Lucas 06/11).
// Every outdoor surface shader turns the faces that look up white by _CheckoutSnow (0 = none, 1 = all white),
// patchy while it settles (a broad noise decides where it lands first); the shop floor and its walls stay clear
// (_CheckoutSnowCut = x min, z min, x max, z max in world space: the market has a roof).
#ifndef CHECKOUT_SNOW_INCLUDED
#define CHECKOUT_SNOW_INCLUDED
float _CheckoutSnow;
float4 _CheckoutSnowCut;
float CheckoutSnowHash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
float CheckoutSnowNoise(float2 p)
{
    float2 i = floor(p), f = frac(p); f = f * f * (3 - 2 * f);
    return lerp(lerp(CheckoutSnowHash(i), CheckoutSnowHash(i + float2(1, 0)), f.x), lerp(CheckoutSnowHash(i + float2(0, 1)), CheckoutSnowHash(i + 1), f.x), f.y);
}
/// How much a face looks up (0 on walls, 1 on floors and roofs).
float CheckoutSnowUp(float3 worldNormal) { return smoothstep(.35, .8, normalize(worldNormal).y); }
/// The albedo under the snow. `keep` < 1 where it melts (the traffic on the road, water).
float3 CheckoutSnow(float3 albedo, float3 worldPos, float up, float keep)
{
    if (_CheckoutSnow < .001) return albedo;
    float2 p = worldPos.xz;
    float inside = step(_CheckoutSnowCut.x, p.x) * step(p.x, _CheckoutSnowCut.z) * step(_CheckoutSnowCut.y, p.y) * step(p.y, _CheckoutSnowCut.w);
    float n = CheckoutSnowNoise(p * 1.3) * .6 + CheckoutSnowNoise(p * 5.1) * .4;
    float cover = saturate((_CheckoutSnow * 1.35 - (1 - n) * .6) * 2.5) * up * keep * (1 - inside);
    float3 snow = lerp(float3(.80, .85, .93), float3(.97, .98, 1), n);
    return lerp(albedo, snow, cover);
}
#endif
