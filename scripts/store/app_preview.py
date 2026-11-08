"""App Store preview (<=30 s, 1920x886 landscape, Lucas 08/11: "coloque o video de trailer tanto na app store quanto na google store"): the trailer's story in 29.5 s, rendered as the trailer at 1920x1080 and cropped to the middle 886 rows.
Cuts the launch trailer from the Unity clips (Logs/tr_<lang>_<scene>_<k>.mp4).

usage: python3 assemble.py <lang pt|en> <clips dir> <out dir>
One encoded file per segment (same size, fps and encoder settings), joined with the concat demuxer, then the music
and the game's own sound effects mixed in.

v3 (Lucas 08/11: "coloque mais efeito no vídeo... mais coisa chamativa... uau, olha que legal quando o mercado fica
super grande"): every cut lands with a white flash and a zoom punch, the titles pop in with a bounce (the numbers
count up), the growth montage speeds up into a riser, and the hypermarket and the chain arrive with an impact, a camera
shake, a big caption and confetti. A light grade (saturation, contrast, vignette) over the game shots.
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titles, fx

LANG, CLIPS, OUT = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
A = titles.A
os.makedirs(OUT, exist_ok=True)
FX = os.path.join(OUT, "fx"); os.makedirs(FX, exist_ok=True)
FPS, W, H = 30, 1920, 1080
ENC = ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", "30", "-an"]
PT = LANG == "pt"

T = {
    "mesa": ("COMECE PEQUENO", "Uma mesinha na calçada") if PT else ("START SMALL", "A little table on the sidewalk"),
    "caixa": ("ATENDA NO CAIXA", "Passe as compras e dê o troco") if PT else ("RUN THE REGISTER", "Scan, bag and give the change"),
    "repor": ("REPONHA", "Prateleiras sempre cheias") if PT else ("RESTOCK", "Keep every shelf full"),
    "cresce": ("CRESÇA", "11 expansões para conquistar") if PT else ("GROW", "11 stages to conquer"),
    "hiper": ("139 PRODUTOS", "Um supermercado lotado") if PT else ("139 PRODUCTS", "A store packed with customers"),
    "setores": ("7 SETORES ESPECIAIS", "Um minigame em cada um") if PT else ("7 SPECIAL SECTORS", "A mini-game in each one"),
    "evento": ("EVENTOS", "Surpresas que mudam o seu dia") if PT else ("LIVE EVENTS", "Surprises that change your day"),
    "rede": ("O GRANDE FINAL", "Centro de distribuição e frota própria") if PT else ("THE BIG FINISH", "Your own distribution centre and fleet"),
}
COUNT = {"hiper": (139, "{n} PRODUTOS" if PT else "{n} PRODUCTS"), "setores": (7, "{n} SETORES ESPECIAIS" if PT else "{n} SPECIAL SECTORS")}
BIG = {"hiper": ["DE MESINHA", "A HIPERMERCADO!"] if PT else ["FROM A LITTLE TABLE", "TO A HYPERMARKET!"],
       "rede": ["SUA REDE DE", "SUPERMERCADOS!"] if PT else ["YOUR OWN", "SUPERMARKET CHAIN!"]}
STAGES = ["Tenda", "Banca de feira", "Mini-contêiner", "Späti", "Quitanda", "Minimercado", "Mercadinho"] if PT else \
    ["Tent", "Market stall", "Mini container", "Späti", "Greengrocer", "Mini market", "Corner store"]

def clip(scene, k): return os.path.join(CLIPS, f"tr_{LANG}_{scene}_{k}.mp4")
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit("ffmpeg failed:\n" + " ".join(cmd) + "\n" + r.stderr[-3000:])

# ── overlays ──────────────────────────────────────────────────────────────────────────────────────────────────────
fx.band(os.path.join(FX, "band.png"))
NT = {}
for key, (k, h) in T.items(): NT[key] = fx.title_anim(os.path.join(FX, f"t_{key}"), k, h, COUNT.get(key))
NB = {key: fx.big_caption(os.path.join(FX, f"b_{key}"), lines) for key, lines in BIG.items()}
NC = fx.confetti(os.path.join(FX, "cf"))
for i, s in enumerate(STAGES):
    titles.chip(s, os.path.join(OUT, f"chip_{i}.png"))
    _c = Image.open(os.path.join(OUT, f"chip_{i}.png")); _m = Image.new("RGBA", _c.size, (0, 0, 0, 0)); _m.paste(_c, (0, 97)); _m.save(os.path.join(OUT, f"chip_{i}.png"))
RISER, IMPACT = fx.sounds(OUT)

def f3(x): return f"{x:.3f}"

def segment(name, parts, title=None, title_in=.35, title_out=None, chips=None, ui=False, big=None, confetti=None):
    """parts: [(clip, in, duration, opts)] cut back to back; opts: speed, punch (zoom punch at the cut, default on),
    flash (white flash at the cut, default on), shake (seconds of camera shake from the cut).
    title pops in at title_in and fades before the end; big = (key, at, seconds) centre caption; confetti = time."""
    out = os.path.join(OUT, f"seg_{name}.mp4"); tmp = out[:-4] + ".tmp.mp4"
    args, f = [], []
    total = 0.0
    for i, p in enumerate(parts):
        path, start, dur = p[:3]; o = p[3] if len(p) > 3 else {}
        sp = o.get("speed", 1.0); total += dur
        args += ["-ss", f3(start), "-t", f3(dur * sp + .1), "-i", path]
        chain = f"[{i}:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS},scale={W}:{H}"
        if o.get("punch", True) or o.get("shake"):
            pz = .10 if o.get("punch", True) else 0.0; sh = o.get("shake", 0.0)
            shx = f"+34*sin(on*2.7)*max(0,1-on/{sh * FPS:.1f})" if sh else ""
            shy = f"+22*cos(on*3.4)*max(0,1-on/{sh * FPS:.1f})" if sh else ""
            zoom = f"1+{pz}*pow(max(0,1-on/10.5),2)" + (f"+0.03*max(0,1-on/{sh * FPS:.1f})" if sh else "")
            chain += f",scale={W * 2}:{H * 2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2){shx}':y='ih/2-(ih/zoom/2){shy}':d=1:s={W}x{H}:fps={FPS}"
        if o.get("flash", True): chain += ",fade=t=in:st=0:d=0.14:color=white"
        chain += f",trim=duration={f3(dur)},setpts=PTS-STARTPTS,format=yuv420p[p{i}]"
        f.append(chain)
    n = len(parts)
    f.append("".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[c0]")
    f.append("[c0]eq=saturation=1.12:contrast=1.05" + ("" if ui else ",vignette=angle=PI/6") + "[base]")
    last = "base"
    def seq_overlay(prefix, frames, at, tag):
        nonlocal last, n
        args.extend(["-framerate", str(FPS), "-start_number", "0", "-i", prefix + "_%03d.png"])
        f.append(f"[{n}:v]format=rgba,setpts=PTS-STARTPTS+{f3(at)}/TB[{tag}s]")
        f.append(f"[{last}][{tag}s]overlay=0:0:eof_action=pass:enable='between(t,{f3(at)},{f3(at + frames / FPS)})'[{tag}o]")
        last = f"{tag}o"; n += 1
    def still_overlay(path, a, b, tag, fade_in=0.0):
        nonlocal last, n
        args.extend(["-loop", "1", "-t", f3(total), "-i", path])
        fi = f",fade=t=in:st={f3(a)}:d={f3(fade_in)}:alpha=1" if fade_in else ""
        f.append(f"[{n}:v]format=rgba{fi},fade=t=out:st={f3(b - .25)}:d=0.25:alpha=1[{tag}s]")
        f.append(f"[{last}][{tag}s]overlay=0:0:enable='between(t,{f3(a)},{f3(b)})'[{tag}o]")
        last = f"{tag}o"; n += 1
    if title:
        te = title_out if title_out is not None else total - .3
        still_overlay(os.path.join(FX, "band.png"), title_in, te, "band", fade_in=.25)
        nt = NT[title]
        seq_overlay(os.path.join(FX, f"t_{title}"), nt, title_in, "tseq")
        still_overlay(os.path.join(FX, f"t_{title}_static.png"), title_in + nt / FPS, te, "tst")
    if big:
        key, at, secs = big; nb = NB[key]
        seq_overlay(os.path.join(FX, f"b_{key}"), nb, at, "bseq")
        still_overlay(os.path.join(FX, f"b_{key}_static.png"), at + nb / FPS, at + secs, "bst")
    if confetti is not None:
        seq_overlay(os.path.join(FX, "cf"), NC, confetti, "cf")
    if chips:
        for j, (ci, a, b) in enumerate(chips):
            args += ["-loop", "1", "-t", f3(total), "-i", os.path.join(OUT, f"chip_{ci}.png")]
            f.append(f"[{last}][{n}:v]overlay=0:0:enable='between(t,{f3(a)},{f3(b)})'[c{j}]"); last = f"c{j}"; n += 1
    run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", ";".join(f), "-map", f"[{last}]", "-t", f3(total), *ENC, tmp])
    os.replace(tmp, out)
    return out, total

def end_card(seconds=5.6):
    """The game's icon, name and where to get it, over the last aerial shot (blurred, darker), with confetti."""
    out = os.path.join(OUT, "seg_end.mp4"); tmp = out[:-4] + ".tmp.mp4"
    bg = os.path.join(OUT, "end_bg.png"); fg = os.path.join(OUT, "end_fg.png")
    run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.2", "-i", clip("rede", 3), "-frames:v", "1", os.path.join(OUT, "end_src.png")])
    im = Image.open(os.path.join(OUT, "end_src.png")).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14))
    dark = Image.new("RGB", (W, H), (16, 24, 52)); im = Image.blend(im, dark, .55); im.save(bg)
    fg_im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(fg_im)
    icon = Image.open(os.path.join(A, "icon.png")).convert("RGBA").resize((330, 330), Image.LANCZOS)
    mask = Image.new("L", icon.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, 329, 329], radius=74, fill=255)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([W // 2 - 165 + 6, 150 + 14, W // 2 + 165 + 6, 480 + 14], radius=74, fill=(0, 0, 0, 140))
    fg_im = Image.alpha_composite(fg_im, sh.filter(ImageFilter.GaussianBlur(12)))
    fg_im.paste(icon, (W // 2 - 165, 150), mask); d = ImageDraw.Draw(fg_im)
    fh = titles.font("Fredoka_700Bold.ttf", 104); fs = titles.font("Fredoka_700Bold.ttf", 54); fst = titles.font("Fredoka_600SemiBold.ttf", 44)
    titles.stroked(d, (W // 2, 640), "Checkout: Supermarket Sim", fh, titles.WHITE, titles.NAVY, 10)
    sub = "Jogue grátis agora" if PT else "Play free now"
    tw = d.textlength(sub, font=fs); box = [W // 2 - tw / 2 - 40, 700, W // 2 + tw / 2 + 40, 790]
    d.rounded_rectangle([box[0], box[1] + 7, box[2], box[3] + 7], radius=45, fill=(150, 100, 20, 255))
    d.rounded_rectangle(box, radius=45, fill=titles.GOLD + (255,), outline=titles.NAVY + (255,), width=5)
    d.text((W // 2, 765), sub, font=fs, fill=titles.NAVY, anchor="ms")
    d.text((W // 2, 880), "App Store  ·  Google Play", font=fst, fill=titles.CREAM, anchor="ms")
    fg_im.save(fg)
    # the card pops in (a bounce, as the titles)
    nfg = 14
    for i in range(nfg):
        s = .6 + .4 * fx.ease_out_back(min(1, i / 11)); fx.scaled(fg_im, s, min(1, i / 4), (W // 2, H // 2)).save(os.path.join(FX, f"end_{i:03d}.png"))
    f = [f"[0:v]scale={W * 2}:{H * 2},zoompan=z='1.0+0.05*on/{int(seconds * FPS)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(seconds * FPS)}:s={W}x{H}:fps={FPS},format=yuv420p[bg]",
         f"[2:v]format=rgba,setpts=PTS-STARTPTS+0.2/TB[pop]",
         f"[bg][pop]overlay=0:0:eof_action=pass:enable='between(t,0.2,{f3(.2 + nfg / FPS)})'[b1]",
         f"[1:v]format=rgba[fg]",
         f"[b1][fg]overlay=0:0:enable='gte(t,{f3(.2 + nfg / FPS)})'[b2]",
         f"[3:v]format=rgba,setpts=PTS-STARTPTS+0.3/TB[cf]",
         f"[b2][cf]overlay=0:0:eof_action=pass[b3]",
         f"[b3]fade=t=in:st=0:d=0.35:color=white,fade=t=out:st={seconds - .6}:d=0.6[v]"]
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{seconds}", "-i", bg, "-loop", "1", "-t", f"{seconds}", "-i", fg,
         "-framerate", str(FPS), "-start_number", "0", "-i", os.path.join(FX, "end_%03d.png"),
         "-framerate", str(FPS), "-start_number", "0", "-i", os.path.join(FX, "cf_%03d.png"),
         "-filter_complex", ";".join(f), "-map", "[v]", "-t", f"{seconds}", *ENC, tmp])
    os.replace(tmp, out)
    return out, seconds

# ── the cut ─────────────────────────────────────────────────────────────────────────────────────────────────────
segs, sfx, t = [], [], 0.0
def add(seg, cues=()):
    global t
    path, dur = seg; segs.append(path)
    for (name, at, vol) in cues: sfx.append((name, t + at, vol))
    t += dur

add(segment("mesa", [(clip("mesa", 1), 0.0, 2.8, {"flash": False})], "mesa"), [("pop", .35, .5)])
add(segment("caixa", [(clip("caixa", 1), 0.2, 4.6)], "caixa", ui=True),
    [("whoosh", -.12, .3), ("pop", .35, .5), ("scan_beep", 1.15, .55), ("scan_beep", 1.45, .55), ("scan_beep", 1.75, .55), ("drawer_open", 2.6, .6),
     ("coin_0", 3.3, .6), ("coin_1", 3.6, .6), ("coin_0", 3.9, .6), ("cash_register", 4.25, .8)])
durs = [1.35, 1.15, 1.0, .9, .8, .72, .7]; speeds = [1.0, 1.0, 1.15, 1.25, 1.3, 1.4, 1.4]
grow, chips, at = [], [], 0.0
for k in range(7):
    grow.append((clip("cresce", k + 1), .6, durs[k], {"speed": speeds[k]})); chips.append((k, at, at + durs[k])); at += durs[k]
gseg = segment("cresce", grow, "cresce", title_in=.2, chips=chips)
add(gseg, [("whoosh", -.12, .35), ("pop", .2, .5)] + [("whoosh", sum(durs[:k]) - .1, .35) for k in range(1, 7)] + [("riser", gseg[1] - 1.6, .55)])
add(segment("hiper", [(clip("hiper", 1), .3, 3.3, {"shake": .7}), (clip("hiper", 2), .8, 2.6), (clip("hiper", 3), .5, 2.2)], "hiper",
            title_in=3.45, big=("hiper", .05, 2.95), confetti=0.0),
    [("impact", 0, .9), ("conquest", .1, .5), ("whoosh", 3.2, .3), ("pop", 3.45, .5), ("whoosh", 5.8, .3)])
add(segment("rede", [(clip("rede", 2), .5, 1.6), (clip("rede", 3), 0.0, 5.8, {"shake": .6})], None, big=("rede", 1.7, 3.6), confetti=1.6),
    [("whoosh", -.12, .3), ("riser", 0.0, .45), ("impact", 1.6, .85), ("conquest", 1.7, .55)])

lst = os.path.join(OUT, "segments.txt")
with open(lst, "w") as fh:
    for p in segs: fh.write(f"file '{p}'\n")
silent = os.path.join(OUT, "video_silent.mp4")
# the middle 886 rows (1920x886, the iPhone 6.5"/6.9" landscape preview size), a short fade out at the end
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"crop=1920:886:0:97,fade=t=out:st={t - .45:.3f}:d=0.45,format=yuv420p",
     "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-crf", "16", "-preset", "slow", "-r", "30", "-g", "30", "-an", silent])

MUSIC_AT = 46.3
inputs = ["-i", silent, "-ss", f"{MUSIC_AT}", "-t", f"{t:.3f}", "-i", os.path.join(A, "music.ogg")]
f = [f"[1:a]afade=t=in:st=0:d=0.6,afade=t=out:st={t - 1.5:.3f}:d=1.5,volume=0.9[m]"]
mix = ["[m]"]
for i, (name, at, vol) in enumerate(sfx):
    path = RISER if name == "riser" else IMPACT if name == "impact" else os.path.join(A, f"{name}.wav")
    inputs += ["-i", path]
    ms = max(0, int(at * 1000))
    f.append(f"[{i + 2}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume={vol},adelay={ms}|{ms}[s{i}]")
    mix.append(f"[s{i}]")
f.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
final = os.path.join(OUT, f"app_preview_{LANG}.mp4"); tmp = final[:-4] + ".tmp.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(f), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-t", f"{t:.3f}", tmp])
os.replace(tmp, final)
print(final, round(t, 2), "s")
