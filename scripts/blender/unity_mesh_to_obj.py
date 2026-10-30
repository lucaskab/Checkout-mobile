"""Unity text Mesh .asset (m_IndexBuffer / m_VertexData hex) -> OBJ with one group per submesh."""
import re, struct, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
idx_fmt = int(re.search(r"m_IndexFormat: (\d+)", s).group(1))
ib = bytes.fromhex(re.search(r"m_IndexBuffer: ([0-9a-f]+)", s).group(1))
subs = [(int(a), int(b), int(c)) for a, b, c in re.findall(r"firstByte: (\d+)\n\s+indexCount: (\d+)\n\s+topology: \d+\n\s+baseVertex: (\d+)", s)]
vc = int(re.search(r"m_VertexCount: (\d+)", s).group(1))
chan_block = s[s.index("m_Channels:"):s.index("m_DataSize")]
chans = [tuple(map(int, m)) for m in re.findall(r"stream: (\d+)\n\s+offset: (\d+)\n\s+format: (\d+)\n\s+dimension: (\d+)", chan_block)]
size = {0: 4, 1: 2, 2: 1, 3: 1, 4: 2, 5: 2, 6: 1, 7: 1, 8: 2, 9: 2, 10: 4, 11: 4}
stride = 0
for st, off, fm, dim in chans:
    if dim and st == 0:
        stride = max(stride, off + size[fm] * (dim & 15))
vd = bytes.fromhex(re.search(r"_typelessdata: ([0-9a-f]+)", s).group(1))
pos = [struct.unpack_from("<3f", vd, i * stride) for i in range(vc)]
uvc = [c for c in chans if c[0] == 0 and c[2] == 0 and (c[3] & 15) == 2]
uvs = [struct.unpack_from("<2f", vd, i * stride + uvc[0][1]) for i in range(vc)] if uvc else None
w = 4 if idx_fmt == 1 else 2
with open(dst, "w") as f:
    for x, y, z in pos:
        f.write("v %f %f %f\n" % (-x, -z, y))   # Unity (x, y, z) -> Blender (-x, -z, y), as the FBX import does
    if uvs:
        for u, v in uvs:
            f.write("vt %f %f\n" % (u, v))
    for k, (fb, n, base) in enumerate(subs):
        f.write("g sub%d\nusemtl sub%d\n" % (k, k))
        for t in range(0, n, 3):
            a, b, c = (struct.unpack_from("<I" if w == 4 else "<H", ib, fb + (t + j) * w)[0] + base + 1 for j in range(3))
            f.write("f %d/%d %d/%d %d/%d\n" % (a, a, c, c, b, b) if uvs else "f %d %d %d\n" % (a, c, b))
print(vc, len(subs), stride, chans[:4])
