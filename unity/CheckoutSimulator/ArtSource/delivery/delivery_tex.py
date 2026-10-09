"""delivery_tex.py -- Checkout - Supermercado Simulator (Oct 2026)
Generates the printed / label / UI image textures used by delivery_art.py (ArtSource/delivery/tex/*.png).
Run with any Python that has Pillow (Blender's bundled Python does not ship it):  python delivery_tex.py [out_dir] [font_dir]
Fonts: Inter (OFL) -- pass the folder that holds Inter-*.otf (default /usr/share/fonts/opentype/inter).
"""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
FD = sys.argv[2] if len(sys.argv) > 2 else "/usr/share/fonts/opentype/inter"
os.makedirs(OUT, exist_ok=True)
SS = 2  # supersampling

BLUE = (46, 140, 174); BLUE_D = (31, 111, 143); BLUE_L = (69, 183, 208); ORANGE = (240, 160, 48); CREAM = (245, 230, 190)
INK = (34, 38, 44); GREY = (120, 126, 134); WHITE = (250, 250, 246); RED = (205, 45, 35); GREEN = (70, 160, 70)

def F(w, px):
    return ImageFont.truetype(os.path.join(FD, f"Inter-{w}.otf"), int(px * SS))

class Canvas:
    def __init__(s, w, h, bg=(0, 0, 0, 0)):
        s.w, s.h = w, h; s.im = Image.new("RGBA", (w * SS, h * SS), bg); s.d = ImageDraw.Draw(s.im)
    def S(s, *v): return [x * SS for x in v]
    def rect(s, x0, y0, x1, y1, fill, r=0, outline=None, width=1):
        s.d.rounded_rectangle(s.S(x0, y0, x1, y1), radius=r * SS, fill=fill, outline=outline, width=int(width * SS))
    def ell(s, cx, cy, r, fill=None, outline=None, width=1):
        s.d.ellipse(s.S(cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=int(width * SS))
    def arc(s, cx, cy, r, a0, a1, fill, width):
        s.d.arc(s.S(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=fill, width=int(width * SS))
    def line(s, pts, fill, width=1):
        s.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=int(width * SS), joint="curve")
    def poly(s, pts, fill):
        s.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
    def text(s, x, y, t, font, fill, anchor="la"):
        s.d.text((x * SS, y * SS), t, font=font, fill=fill, anchor=anchor)
    def tw(s, t, font): return s.d.textlength(t, font=font) / SS
    def save(s, name, blur=0):
        im = s.im.resize((s.w, s.h), Image.LANCZOS)
        if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
        im.save(os.path.join(OUT, name)); return im

def logo(c, cx, cy, size, col, handle=None, hole=None):
    """Checkout bag logo: rounded bag body + handle arc (+ optional cut-out check mark)."""
    w = size; h = size * .82
    c.rect(cx - w / 2, cy - h / 2 + size * .12, cx + w / 2, cy + h / 2 + size * .12, col, r=size * .12)
    c.arc(cx, cy - h / 2 + size * .12, size * .26, 180, 360, handle or col, size * .075)
    if hole:
        c.line([(cx - size * .2, cy + size * .14), (cx - size * .05, cy + size * .28), (cx + size * .22, cy - size * .02)], hole, size * .08)

def paper_noise(im, amt=10, seed=1):
    rnd = random.Random(seed); px = im.load(); w, h = im.size
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if len(p) == 4 and p[3] == 0: continue
            n = rnd.randint(-amt, amt); px[x, y] = tuple(max(0, min(255, v + n)) for v in p[:3]) + ((p[3],) if len(p) == 4 else ())
    return im

def worn_ink(im, seed=3, holes=900):
    """Stamped-print look on an alpha print: speckled drop-outs."""
    rnd = random.Random(seed); w, h = im.size; a = im.split()[3]; d = ImageDraw.Draw(a)
    for _ in range(holes):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(.5, 2.2)
        d.ellipse((x - r, y - r, x + r, y + r), fill=0)
    im.putalpha(a.point(lambda v: int(v * .92))); return im

# ---------------------------------------------------------------- 1. tablet app UI
def app_ui():
    W, H = 1280, 800; c = Canvas(W, H, (243, 245, 247, 255))
    c.rect(0, 0, W, 34, (25, 30, 36)); c.text(24, 17, "14:32", F("SemiBold", 18), WHITE, "lm")
    for k in range(4): c.rect(W - 120 + k * 9, 24 - 4 - k * 3, W - 114 + k * 9, 26, WHITE, r=1)
    c.rect(W - 70, 10, W - 30, 26, None, r=4, outline=WHITE, width=2); c.rect(W - 67, 13, W - 42, 23, (120, 220, 120), r=2); c.rect(W - 29, 15, W - 25, 21, WHITE)
    c.rect(0, 34, W, 130, BLUE)
    logo(c, 62, 80, 46, WHITE, ORANGE)
    c.text(104, 82, "Delivery", F("Bold", 44), WHITE, "lm")
    c.text(320, 86, "Checkout  •  Supermercado", F("Medium", 20), (210, 236, 245), "lm")
    c.rect(W - 300, 58, W - 120, 104, (255, 255, 255, 50), r=23); c.ell(W - 270, 81, 9, (120, 230, 120)); c.text(W - 252, 81, "Loja aberta", F("SemiBold", 20), WHITE, "lm")
    c.ell(W - 62, 81, 26, ORANGE); c.text(W - 62, 81, "3", F("Bold", 28), WHITE, "mm")
    # filter chips
    for k, (t, on) in enumerate((("Novos  3", True), ("Em preparo  1", False), ("Saiu p/ entrega  2", False), ("Concluídos", False))):
        x = 24 + sum(c.tw(tt, F("SemiBold", 20)) + 60 for tt, _ in (("Novos  3", 1), ("Em preparo  1", 1), ("Saiu p/ entrega  2", 1), ("Concluídos", 1))[:k])
        tw = c.tw(t, F("SemiBold", 20)) + 40
        c.rect(x, 148, x + tw, 192, BLUE_D if on else WHITE, r=22, outline=None if on else (205, 212, 220), width=2)
        c.text(x + tw / 2, 170, t, F("SemiBold", 20), WHITE if on else INK, "mm")
    orders = [("#128", "Ana Souza", "R. das Flores, 12  •  1.2 km", "6 itens  •  leite, pão, ovos…", "R$ 48,90", "NOVO", ORANGE, "Aceitar"),
              ("#129", "Bruno Lima", "Av. Brasil, 870  •  2.1 km", "9 itens  •  arroz, banana, café…", "R$ 112,40", "NOVO", ORANGE, "Aceitar"),
              ("#127", "Carla Dias", "R. do Sol, 45  •  0.8 km", "4 itens  •  sorvete, peixe…", "R$ 63,15", "EM PREPARO", BLUE, "Embalar")]
    y = 214
    for k, (num, name, addr, items, price, st, stc, btn) in enumerate(orders):
        c.rect(24 + 3, y + 5, 800 + 3, y + 178 + 5, (215, 220, 226), r=18)
        c.rect(24, y, 800, y + 178, WHITE, r=18)
        c.rect(24, y, 34, y + 178, stc, r=5)
        c.ell(96, y + 60, 34, (225, 238, 244)); c.text(96, y + 60, name[0] + name.split()[1][0], F("Bold", 26), BLUE_D, "mm")
        c.text(148, y + 40, f"Pedido {num}", F("Bold", 28), INK, "lm"); c.text(148, y + 76, name, F("Medium", 22), GREY, "lm")
        tw = c.tw(st, F("Bold", 16)) + 28; c.rect(780 - tw, y + 22, 780, y + 54, stc, r=16); c.text(780 - tw / 2, y + 38, st, F("Bold", 16), WHITE, "mm")
        c.text(148, y + 112, addr, F("Regular", 20), INK, "lm"); c.text(148, y + 144, items, F("Regular", 19), GREY, "lm")
        c.text(780, y + 92, price, F("Bold", 28), INK, "rm")
        c.rect(620, y + 120, 780, y + 164, stc, r=22); c.text(700, y + 142, btn, F("Bold", 20), WHITE, "mm")
        c.text(40 + 520, y + 92, "12 min" if k == 0 else ("3 min" if k == 1 else "18 min"), F("Medium", 18), GREY, "lm")
        y += 196
    # right column: map + route
    c.rect(824, 214, W - 24, 560, (214, 232, 204), r=18)
    for k in range(6): c.line([(824 + 40 + k * 75, 214), (824 + 10 + k * 75, 560)], (250, 250, 240), 10)
    for k in range(4): c.line([(824, 250 + k * 90), (W - 24, 270 + k * 85)], (250, 250, 240), 12)
    for k in range(10): c.rect(840 + (k % 5) * 80, 230 + (k // 5) * 190, 880 + (k % 5) * 80, 262 + (k // 5) * 190, (196, 206, 196), r=4)
    c.line([(870, 520), (880, 430), (1010, 420), (1030, 330), (1180, 300)], ORANGE, 8)
    c.ell(870, 520, 14, BLUE); c.ell(870, 520, 6, WHITE)
    c.ell(1180, 290, 18, ORANGE); c.poly([(1166, 298), (1194, 298), (1180, 322)], ORANGE); c.ell(1180, 290, 7, WHITE)
    c.rect(840, 500, 1060, 548, WHITE, r=12); c.text(856, 524, "Rota  •  14 min", F("SemiBold", 20), INK, "lm")
    c.rect(824, 576, W - 24, 778, WHITE, r=18)
    c.text(848, 606, "Hoje", F("Bold", 24), INK, "lm")
    for k, (v, t) in enumerate((("23", "pedidos"), ("R$ 1.284", "vendas"), ("4.8 ★", "avaliação"))):
        x = 848 + k * 140; c.text(x, 660, v, F("Bold", 26), BLUE_D if k != 2 else ORANGE, "lm"); c.text(x, 694, t, F("Regular", 17), GREY, "lm")
    for k in range(12):
        hh = [30, 45, 38, 60, 72, 50, 84, 66, 40, 58, 76, 62][k]; c.rect(848 + k * 34, 768 - hh, 870 + k * 34, 762, BLUE_L if k != 6 else ORANGE, r=4)
    c.save("app_ui.png")

# ---------------------------------------------------------------- 2. order slips (cork board)
def slips():
    data = [("#125", "Marcos R.", ["2x Arroz 5kg", "1x Feijão 1kg", "3x Leite 1L", "1x Café 500g"], "R$ 87,30", (255, 248, 200)),
            ("#126", "Júlia P.", ["1x Sorvete 2L", "2x Pão forma", "6x Ovos"], "R$ 41,80", (250, 250, 246)),
            ("#127", "Carla D.", ["1x Peixe 800g", "2x Limão", "1x Azeite", "1x Sal"], "R$ 63,15", (220, 238, 250)),
            ("#124", "Seu Zé", ["10x Banana", "1x Mamão", "2x Refri 2L"], "R$ 32,40", (255, 230, 200))]
    rnd = random.Random(7)
    for k, (num, nm, items, tot, bg) in enumerate(data):
        W, H = 400, 560; c = Canvas(W, H, bg + (255,))
        c.rect(0, 0, W, 70, BLUE if k % 2 == 0 else BLUE_D); logo(c, 40, 34, 34, WHITE, ORANGE)
        c.text(76, 36, "PEDIDO " + num, F("Bold", 30), WHITE, "lm")
        c.text(24, 100, nm, F("SemiBold", 26), INK, "lm"); c.text(W - 24, 100, "14:0" + str(k), F("Medium", 20), GREY, "rm")
        c.line([(24, 128), (W - 24, 128)], (160, 160, 160), 2)
        y = 160
        for it in items:
            c.rect(24, y - 11, 46, y + 11, None, r=3, outline=INK, width=2)
            if rnd.random() < .7: c.line([(26, y), (34, y + 9), (50, y - 14)], (40, 90, 200), 4)   # pen tick
            c.text(60, y, it, F("Regular", 22), INK, "lm"); c.line([(60 + c.tw(it, F("Regular", 22)) + 8, y + 6), (W - 90, y + 6)], (200, 200, 200), 1)
            c.text(W - 24, y, f"{rnd.randint(3, 29)},{rnd.randint(10, 99)}", F("Medium", 20), GREY, "rm"); y += 44
        c.line([(24, y), (W - 24, y)], INK, 2); c.text(24, y + 30, "TOTAL", F("Bold", 22), INK, "lm"); c.text(W - 24, y + 30, tot, F("Bold", 24), INK, "rm")
        for i in range(48): c.rect(40 + i * 6.8, H - 92, 40 + i * 6.8 + (2 if i % 3 else 4), H - 40, INK)
        c.text(W / 2, H - 22, "7 891234 5678" + str(k), F("Regular", 16), INK, "mm")
        # handwritten note
        c.arc(W - 80, y + 30, 70, 0, 340, (210, 50, 40), 3); c.text(W - 140, y + 76, "ok!", F("BoldItalic", 26), (210, 50, 40), "mm")
        im = c.save(f"slip_{k}.png"); paper_noise(im, 6, k).save(os.path.join(OUT, f"slip_{k}.png"))

# ---------------------------------------------------------------- 3. posters
def posters():
    W, H = 560, 760
    c = Canvas(W, H, (246, 238, 220, 255))
    c.rect(0, 0, W, 300, BLUE)
    for k in range(9): c.ell(60 + k * 60, 300, 26, BLUE)    # scalloped edge
    logo(c, W / 2, 140, 150, WHITE, ORANGE, BLUE)
    c.text(W / 2, 390, "PEÇA PELO", F("Black", 64), BLUE_D, "mm"); c.text(W / 2, 462, "APP", F("Black", 96), ORANGE, "mm")
    c.text(W / 2, 540, "entrega rápida na sua porta", F("Medium", 26), INK, "mm")
    c.rect(150, 580, W - 150, 640, BLUE_D, r=30); c.text(W / 2, 610, "BAIXE JÁ", F("Bold", 28), WHITE, "mm")
    c.text(W / 2, 700, "checkout.app  •  frete grátis acima de R$ 99", F("Regular", 18), GREY, "mm")
    im = c.save("poster_app.png"); paper_noise(im, 5, 11).save(os.path.join(OUT, "poster_app.png"))
    c = Canvas(W, H, (250, 236, 200, 255))
    c.rect(0, 0, W, H, ORANGE)
    c.rect(30, 30, W - 30, H - 30, None, r=24, outline=WHITE, width=6)
    c.text(W / 2, 150, "SEM", F("Black", 120), WHITE, "mm"); c.text(W / 2, 280, "FILA", F("Black", 140), BLUE_D, "mm")
    # phone illustration
    c.rect(200, 360, 360, 620, INK, r=26); c.rect(212, 380, 348, 600, WHITE, r=10)
    c.rect(212, 380, 348, 420, BLUE, r=10); logo(c, 236, 400, 22, WHITE)
    for k in range(3): c.rect(222, 432 + k * 54, 338, 476 + k * 54, (232, 240, 244), r=8); c.ell(240, 454 + k * 54, 10, ORANGE if k == 0 else BLUE)
    c.text(W / 2, 670, "receba em casa", F("Bold", 40), WHITE, "mm")
    im = c.save("poster_fila.png"); paper_noise(im, 5, 12).save(os.path.join(OUT, "poster_fila.png"))

# ---------------------------------------------------------------- 4. clock face
def clock():
    S = 1024; c = Canvas(S, S, (250, 249, 244, 255)); cx = cy = S / 2
    for k in range(60):
        a = math.radians(k * 6 - 90); r0 = 470 if k % 5 else 440
        c.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + 492 * math.cos(a), cy + 492 * math.sin(a))], INK, 12 if k % 5 == 0 else 5)
    for k in range(1, 13):
        a = math.radians(k * 30 - 90); c.text(cx + 370 * math.cos(a), cy + 370 * math.sin(a), str(k), F("Bold", 96), INK, "mm")
    logo(c, cx, cy - 200, 70, BLUE, ORANGE); c.text(cx, cy - 120, "CHECKOUT", F("Bold", 40), BLUE_D, "mm")
    c.text(cx, cy + 190, "quartz", F("Regular", 30), GREY, "mm")
    c.save("clock_face.png")

# ---------------------------------------------------------------- 5. kraft bag print (alpha) + shelf bag print
def kraft_print():
    W, H = 900, 1060; c = Canvas(W, H)
    logo(c, W / 2, 330, 300, BLUE_D + (255,), ORANGE + (255,), None)
    c.ell(W / 2, 352, 70, None, (0, 0, 0, 0), 1)
    c.text(W / 2, 600, "CHECKOUT", F("Black", 128), BLUE_D + (255,), "mm")
    c.text(W / 2, 700, "mercado  •  delivery", F("SemiBold", 50), BLUE_D + (255,), "mm")
    c.rect(W / 2 - 200, 760, W / 2 + 200, 772, ORANGE + (255,), r=6)
    c.text(W / 2, 850, "♻  papel 100% reciclável", F("Medium", 34), BLUE_D + (255,), "mm")
    c.text(W / 2, 980, "obrigado pela preferência!", F("Italic", 36), BLUE_D + (255,), "mm")
    im = c.save("kraft_print.png"); worn_ink(im, 3, 2500).save(os.path.join(OUT, "kraft_print.png"))

# ---------------------------------------------------------------- 6. grocery labels
def labels():
    # milk carton front
    W, H = 512, 800; c = Canvas(W, H, (250, 250, 248, 255))
    c.rect(0, 0, W, 300, (40, 110, 200));
    for k in range(5): c.ell(80 + k * 90, 300 + (k % 2) * 16, 70, (40, 110, 200))
    c.text(W / 2, 110, "Leite", F("Black", 130), WHITE, "mm"); c.text(W / 2, 220, "INTEGRAL", F("Bold", 54), (255, 220, 80), "mm")
    c.ell(W / 2, 520, 120, (230, 240, 250))
    c.rect(W / 2 - 60, 470, W / 2 + 60, 570, (40, 110, 200), r=30); c.text(W / 2, 520, "1L", F("Black", 64), WHITE, "mm")
    c.text(W / 2, 690, "Fazenda Boa Vista", F("SemiBold", 32), (40, 110, 200), "mm"); c.text(W / 2, 740, "UHT  •  rico em cálcio", F("Regular", 26), GREY, "mm")
    c.save("milk_front.png")
    W, H = 512, 800; c = Canvas(W, H, (250, 250, 248, 255)); c.rect(0, 0, W, 120, (40, 110, 200))
    c.text(W / 2, 60, "INFORMAÇÃO NUTRICIONAL", F("Bold", 30), WHITE, "mm")
    for k in range(12):
        y = 160 + k * 46; c.text(30, y, ["Valor energético", "Carboidratos", "Proteínas", "Gorduras totais", "Gord. saturadas", "Sódio", "Cálcio", "Vitamina A", "Vitamina D", "", "", ""][k], F("Regular", 26), INK, "lm")
        if k < 9: c.text(W - 30, y, f"{(k * 37) % 120 + 3} g", F("Medium", 26), INK, "rm"); c.line([(30, y + 22), (W - 30, y + 22)], (190, 190, 190), 2)
    for i in range(40): c.rect(120 + i * 6.8, 640, 120 + i * 6.8 + (2 if i % 3 else 4), 740, INK)
    c.save("milk_side.png")
    # rice bag
    W, H = 640, 900; c = Canvas(W, H, (250, 246, 236, 255))
    c.rect(0, 0, W, 210, (210, 50, 40)); c.text(W / 2, 105, "Grão Bom", F("Black", 104), WHITE, "mm")
    c.text(W / 2, 330, "ARROZ", F("Black", 150), (210, 50, 40), "mm"); c.text(W / 2, 440, "BRANCO  •  TIPO 1", F("Bold", 48), INK, "mm")
    for k in range(40):
        rnd = random.Random(k); x, y = rnd.uniform(60, W - 60), rnd.uniform(500, 700)
        c.d.ellipse([x * 2 - 18, y * 2 - 8, x * 2 + 18, y * 2 + 8], fill=(240, 235, 220), outline=(200, 190, 170), width=2)
    c.rect(W - 240, 730, W - 40, 860, (255, 200, 40), r=20); c.text(W - 140, 795, "5 kg", F("Black", 72), (210, 50, 40), "mm")
    c.text(40, 795, "qualidade\nselecionada", F("SemiBold", 30), INK, "lm")
    c.save("rice_label.png")
    # soda can wrap (u = around)
    W, H = 1024, 400; c = Canvas(W, H, (200, 30, 30, 255))
    for k in range(3): c.line([(x, 250 + 60 * math.sin(x / 120 + k)) for x in range(0, W + 10, 10)], WHITE, 16 - k * 4)
    c.text(256, 150, "Cola", F("Black", 150), WHITE, "mm"); c.text(768, 150, "Cola", F("Black", 150), WHITE, "mm")
    c.text(256, 340, "350 ml  •  gelada", F("SemiBold", 34), (255, 230, 220), "mm"); c.text(768, 340, "sabor original", F("SemiBold", 34), (255, 230, 220), "mm")
    c.save("soda_wrap.png")
    # egg carton lid label
    W, H = 640, 360; c = Canvas(W, H, (238, 226, 200, 255))
    c.rect(20, 20, W - 20, H - 20, (255, 250, 236), r=30); c.ell(120, H / 2, 90, (255, 200, 60)); c.ell(120, H / 2, 54, (250, 160, 30))
    c.text(400, 120, "OVOS", F("Black", 110), (150, 80, 30), "mm"); c.text(400, 230, "caipira  •  6 un.", F("SemiBold", 40), INK, "mm")
    c.text(400, 290, "Granja Sol", F("Italic", 30), GREY, "mm")
    c.save("eggs_label.png")
    # gloves box
    W, H = 800, 400; c = Canvas(W, H, (250, 250, 250, 255))
    c.rect(0, 0, W, 80, BLUE); c.text(W / 2, 40, "LUVAS DESCARTÁVEIS", F("Black", 46), WHITE, "mm")
    c.rect(0, H - 60, W, H, BLUE_L); c.text(W / 2, H - 30, "nitrílica  •  sem pó  •  100 unidades  •  tam. M", F("SemiBold", 26), WHITE, "mm")
    c.ell(600, 220, 90, (225, 240, 248)); c.text(600, 220, "M", F("Black", 110), BLUE, "mm")
    c.text(60, 160, "proteção", F("Bold", 50), INK, "lm"); c.text(60, 220, "para manusear", F("Regular", 34), GREY, "lm"); c.text(60, 262, "alimentos", F("Regular", 34), GREY, "lm")
    c.save("gloves_box.png")
    # spray bottle label
    W, H = 600, 400; c = Canvas(W, H, (60, 180, 120, 255))
    c.rect(20, 20, W - 20, H - 20, (240, 255, 245), r=30); c.text(W / 2, 120, "Limpa", F("Black", 100), (30, 130, 80), "mm")
    c.text(W / 2, 220, "TUDO", F("Black", 80), (60, 180, 120), "mm"); c.text(W / 2, 320, "multiuso  •  500 ml", F("SemiBold", 34), INK, "mm")
    c.save("spray_label.png")

# ---------------------------------------------------------------- 7. sticker tile (repeats along the roll) + receipt
def sticker_tile():
    S = 256; c = Canvas(S, S, (250, 248, 240, 255)); cx = cy = S / 2
    c.ell(cx, cy, 112, BLUE); c.ell(cx, cy, 92, WHITE); logo(c, cx, cy - 16, 66, BLUE, ORANGE)
    c.text(cx, cy + 50, "ENTREGUE!", F("Black", 20), BLUE_D, "mm")
    c.save("sticker_tile.png")

def receipt():
    W, H = 320, 1000; c = Canvas(W, H, (250, 250, 246, 255)); f = F("Medium", 20); fb = F("Bold", 24)
    logo(c, W / 2, 60, 60, INK); c.text(W / 2, 120, "CHECKOUT", F("Black", 34), INK, "mm"); c.text(W / 2, 152, "mercado • delivery", F("Regular", 18), INK, "mm")
    c.text(W / 2, 200, "PEDIDO #128", F("Black", 40), INK, "mm"); c.text(W / 2, 240, "Ana Souza  •  1.2 km", f, INK, "mm")
    c.text(W / 2, 268, "R. das Flores, 12", f, INK, "mm")
    y = 300; c.line([(16, y), (W - 16, y)], INK, 2)
    for k, (it, p) in enumerate((("Leite integral 1L", "5,49"), ("Pão de forma", "8,90"), ("Ovos caipira 6un", "12,90"), ("Alface", "3,99"), ("Cola 350ml x2", "9,98"), ("Taxa entrega", "4,00"))):
        y += 40; c.text(16, y, it, f, INK, "lm"); c.text(W - 16, y, p, f, INK, "rm")
    y += 30; c.line([(16, y), (W - 16, y)], INK, 2); y += 40; c.text(16, y, "TOTAL", fb, INK, "lm"); c.text(W - 16, y, "R$ 48,90", fb, INK, "rm")
    y += 40; c.text(16, y, "Pago no app  •  PIX", f, INK, "lm")
    y += 30
    rnd = random.Random(5)
    for i in range(21):
        for j in range(21):
            if (i < 7 and j < 7) or (i < 7 and j > 13) or (i > 13 and j < 7):
                on = (min(i % 14, 6) in (0, 6) or min(j % 14, 6) in (0, 6)) or (2 <= i % 14 <= 4 and 2 <= j % 14 <= 4)
            else: on = rnd.random() < .5
            if on: c.rect(76 + i * 8, y + j * 8, 84 + i * 8, y + 8 + j * 8, INK)
    y += 190; c.text(W / 2, y, "obrigado! volte sempre", f, INK, "mm")
    for i in range(52): c.rect(20 + i * 5.5, y + 30, 20 + i * 5.5 + (1.5 if i % 3 else 3), y + 90, INK)
    im = c.save("receipt.png"); paper_noise(im, 5, 9).save(os.path.join(OUT, "receipt.png"))

# ---------------------------------------------------------------- 8. thermal-bag print (white, alpha) + quilt stitch tile
def thermal_print():
    W, H = 1000, 500; c = Canvas(W, H)
    logo(c, 180, 230, 220, WHITE + (255,), ORANGE + (255,), None)
    c.text(330, 210, "DELIVERY", F("Black", 120), WHITE + (255,), "lm")
    c.text(334, 300, "checkout  •  supermercado", F("SemiBold", 40), WHITE + (255,), "lm")
    c.rect(334, 345, 760, 355, ORANGE + (255,), r=5)
    c.save("thermal_print.png")

def quilt_stitch():
    """Unit tile: dashed diagonal seams (both diagonals) -- matches the diamond quilting height in delivery_art.py."""
    S = 512; c = Canvas(S, S)
    for (a, b) in (((0, 0), (S, S)), ((0, S), (S, 0))):
        n = 22
        for k in range(n):
            t0, t1 = k / n, (k + .55) / n
            c.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0), (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], (235, 235, 230, 255), 5)
    c.save("quilt_stitch.png")

def chalk_menu():
    W, H = 1180, 580; c = Canvas(W, H, (28, 40, 34, 255))
    rnd = random.Random(2)
    for _ in range(300):   # chalk smudges
        x, y = rnd.uniform(0, W), rnd.uniform(0, H); c.ell(x, y, rnd.uniform(10, 60), (40 + rnd.randint(0, 12), 54 + rnd.randint(0, 12), 46 + rnd.randint(0, 12), 255))
    ch = (240, 240, 228); ch2 = (250, 200, 110)
    c.text(W / 2, 70, "PEÇA PELO APP", F("Black", 70), ch, "mm"); c.line([(W / 2 - 300, 120), (W / 2 + 300, 116)], ch2, 6)
    for k, (a, b) in enumerate((("taxa de entrega", "R$ 4 + R$ 2/km"), ("tempo médio", "40 min"), ("pedido mínimo", "R$ 20"), ("frete grátis", "acima de R$ 99"))):
        y = 180 + k * 72; c.text(80, y, a, F("Medium", 40), ch, "lm"); c.text(W - 80, y, b, F("Bold", 40), ch2 if k == 3 else ch, "rm")
        c.line([(80 + c.tw(a, F("Medium", 40)) + 20, y + 10), (W - 100 - c.tw(b, F("Bold", 40)), y + 10)], (120, 130, 120), 2)
    c.text(W / 2, 500, "★ ★ ★ ★ ★   4.8   no app", F("Bold", 44), ch2, "mm")
    im = c.save("chalk_menu.png", blur=.6); paper_noise(im, 10, 4).save(os.path.join(OUT, "chalk_menu.png"))

def plate():
    W, H = 400, 130; c = Canvas(W, H, (245, 245, 245, 255)); c.rect(0, 0, W, 30, (30, 60, 160)); c.text(W / 2, 15, "BRASIL", F("Bold", 20), WHITE, "mm")
    c.text(W / 2, 82, "CKT2O26", F("Bold", 70), INK, "mm"); c.rect(2, 2, W - 2, H - 2, None, r=8, outline=INK, width=4); c.save("plate.png")

if __name__ == "__main__":
    for fn in (app_ui, slips, posters, clock, kraft_print, labels, sticker_tile, receipt, thermal_print, quilt_stitch, chalk_menu, plate): fn()
    print("ok", sorted(os.listdir(OUT)))
