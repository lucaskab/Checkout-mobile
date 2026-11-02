"""Social v1 UI icons (friends pages), exec'd into the namespace of scripts/blender/build_ui_sprites.py so they share its
materials (glossy coat, procedural paper / wood / plastic surfaces), helpers and studio light. No text or letters.
Each builder fills the scene and calls studio(); social_run.run_icons() renders them at 512 px, transparent."""
import math

S_NAVY, S_NAVY_L, S_GOLD, S_CREAM = '1D2B4F', '33497E', 'D3A53D', 'F6EBD6'
S_CORAL, S_TEAL, S_RED, S_SKIN = 'EC7A5C', '1F9A8E', 'E8435A', 'F2C29B'


def _heart_pts(s, n=40):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * s / 17.0, y * s / 17.0))
    return pts


def _upright(o, loc):
    """_poly_mesh builds in the XY plane extruded along +Z: stand it up facing the camera (-Y)."""
    o.rotation_euler = (R(90), 0, 0)
    o.location = loc
    return o


def _pawn(x, y, s, body_hex, head_hex):
    """A chunky person glyph: rounded body (lathe-like cone with a bevel) and a round head."""
    body = tex('plastic', body_hex, body_hex, rough=.3, scale=1, bump=.02, coat=.6)
    cyl(.42 * s, .7 * s, (x, y, .35 * s), body, v=48, bev=.2 * s, r2=.3 * s)
    sphere(.27 * s, (x, y, .98 * s), tex('plastic', head_hex, head_hex, rough=.3, scale=1, bump=.02, coat=.6))


def icon_friends():
    _pawn(.42, .28, 1.0, S_CORAL, 'F5A68F')
    _pawn(-.32, -.12, 1.08, S_NAVY_L, '6E86C2')
    o = _poly_mesh('Heart', _heart_pts(.2), .08, mat(S_GOLD, .25, .3, coat=1), bev=.03)
    _upright(o, (.05, -.45, 1.42))
    studio(elev=18, yaw=-14)


def icon_gift():
    paper = tex('paper', '24396B', S_NAVY, rough=.45, scale=1, bump=.12, coat=.5)
    gold = mat(S_GOLD, .28, .45, coat=.8)
    box((1.2, 1.2, .9), (0, 0, .45), paper, .04)
    box((1.32, 1.32, .26), (0, 0, 1.02), paper, .05)
    for rot in ((0, 0, 0), (0, 0, 90)):
        box((.22, 1.34, 1.18), (0, 0, .59), gold, .02, rot=rot)
    box((.24, .24, .06), (0, 0, 1.17), gold, .03)
    for s in (-1, 1):
        o = torus(.2, .07, (s * .2, 0, 1.3), gold, rot=(90, s * 35, 0))
        o.scale = (1, 1, .7)
        cyl(.06, .4, (s * .16, -.12, 1.0), gold, rot=(20, s * 25, 0), bev=.02)
    sphere(.1, (0, 0, 1.24), gold)
    studio(elev=24, yaw=-22)


def icon_help():
    skin = tex('plastic', S_SKIN, 'E6AF85', rough=.35, scale=1, bump=.03, coat=.4)
    box((.9, .7, .28), (0, 0, .3), skin, .13)                                   # palm, facing up
    for i in range(4):
        x = -.33 + i * .22
        cyl(.1, .5 - abs(i - 1.5) * .06, (x, -.55, .38), skin, rot=(70, 0, 0), bev=.05)
        sphere(.1, (x, -.78 + abs(i - 1.5) * .03, .46), skin)
    cyl(.11, .45, (.55, -.12, .4), skin, rot=(60, 0, -60), bev=.05)            # thumb
    sphere(.11, (.72, -.28, .5), skin)
    cyl(.4, .35, (0, .55, .3), tex('fabric', S_NAVY, '2A3D6E', rough=.6, scale=1, bump=.1, coat=.1), rot=(90, 0, 0), bev=.06)
    cyl(.42, .08, (0, .37, .3), mat(S_GOLD, .3, .4, coat=.8), rot=(90, 0, 0), bev=.02)
    _upright(_star('Star', .34, .15, mat(S_GOLD, .25, .4, coat=1), (0, 0, 0), depth=.1), (.22, -.6, .98))
    for x, z, r in ((-.55, .95, .06), (.5, 1.2, .05)):
        sphere(r, (x, -.1, z), mat('FFE9A0', .2, emit=.6))
    studio(elev=30, yaw=-20)


def icon_like():
    m = mat(S_RED, .16, coat=1)
    for x in (-.36, .36):
        sphere(.5, (x, 0, .25), m, (1, .8, 1))
    o = box((.78, .62, .78), (0, 0, -.18), m, .3, rot=(0, 45, 0))
    o.scale = (1, 1, 1)
    sub = o.modifiers.new('Sub', 'SUBSURF'); sub.levels = sub.render_levels = 2
    sphere(.11, (-.42, -.38, .52), mat('FFFFFF', .1, coat=1, alpha=.5), (1.3, .5, .8))
    _upright(_star('Spark', .17, .065, mat(S_GOLD, .25, .4, coat=1), (0, 0, 0), depth=.05), (.78, -.15, .85))
    studio(elev=8, yaw=-10)


def icon_request():
    wood = tex('wood', 'C98B4E', '8E5A2E', rough=.55, scale=2.2, bump=.3, coat=.15)
    dark = tex('wood', 'A86E3A', '6E4424', rough=.6, scale=2.2, bump=.3, coat=.1)
    box((1.4, 1.0, .1), (0, 0, .05), dark, .02)
    for z in (.22, .5):
        for y in (-.48, .48):
            box((1.42, .07, .2), (0, y, z), wood, .03)
        for x in (-.68, .68):
            box((.07, 1.0, .2), (x, 0, z), wood, .03)
    for x in (-.68, .68):
        for y in (-.48, .48):
            box((.12, .12, .66), (x, y, .33), dark, .03)
    # supplies peeking out: a red apple, a loaf, a bottle, a can
    sphere(.24, (-.32, -.05, .7), tex('plastic', 'D9362B', 'B32920', rough=.25, scale=1, bump=.02, coat=.8), (1, 1, .92))
    cyl(.025, .14, (-.32, -.05, .95), mat('5A3A22', .6), bev=0)
    o = sphere(.2, (.22, .15, .68), tex('noise', 'D99A4E', 'B8742F', rough=.5, scale=3, bump=.2, coat=.3), (1.7, .9, .75))
    cyl(.12, .6, (.42, -.15, .7), mat('3E8F55', .1, coat=1, trans=.25), bev=.05)
    cyl(.05, .14, (.42, -.15, 1.06), mat(S_CREAM, .3), bev=.02)
    # the request flag
    cyl(.025, 1.0, (-.6, -.38, .95), mat('5A3A22', .5), bev=.01)
    o = _poly_mesh('Flag', [(0, 0), (.55, -.12), (0, -.3)], .03, mat(S_RED, .4, coat=.4), bev=.008)
    _upright(o, (-.6, -.37, 1.42))
    sphere(.04, (-.6, -.38, 1.46), mat(S_GOLD, .25, .5))
    studio(elev=26, yaw=-22)


def icon_share():
    node = tex('plastic', S_TEAL, '157A70', rough=.25, scale=1, bump=.02, coat=.9)
    gold = mat(S_GOLD, .3, .45, coat=.8)
    a, b, c = (-.55, 0, .8), (.5, 0, 1.4), (.5, 0, .2)
    bar(a, b, .09, gold)
    bar(a, c, .09, gold)
    for p, r in ((a, .32), (b, .3), (c, .3)):
        sphere(r, p, node)
    studio(elev=8, yaw=-8)


def icon_invite():
    paper = tex('paper', 'FBF3E2', 'E8DCC2', rough=.6, scale=1, bump=.1, coat=.2)
    box((1.6, .14, 1.05), (0, 0, .52), paper, .04)
    # the card peeking out of the top
    box((1.3, .06, .5), (0, .02, 1.0), tex('paper', 'FFFFFF', 'F1EDE4', rough=.6, scale=1, bump=.06, coat=.1), .03)
    # flap (navy) folded down over the front, and the lower side folds
    o = _poly_mesh('Flap', [(-.8, 0), (.8, 0), (0, -.62)], .03, tex('paper', S_NAVY, '17223F', rough=.5, scale=1, bump=.1, coat=.3), bev=.012)
    _upright(o, (0, -.075, 1.05))
    # gold star seal at the tip of the flap
    cyl(.17, .06, (0, -.11, .43), mat(S_GOLD, .3, .45, coat=.8), rot=(90, 0, 0), bev=.02)
    _upright(_star('Seal', .14, .06, mat('FFE59A', .25, .5, coat=1), (0, 0, 0), depth=.04), (0, -.14, .43))
    studio(elev=12, yaw=-14)


def icon_visit():
    wall = tex('paper', S_CREAM, 'E2D2B2', rough=.6, scale=1.5, bump=.12, coat=.1)
    roof = tex('ribs', S_NAVY, '2A3D6E', rough=.45, scale=6, bump=.25, coat=.4)
    wood = tex('wood', 'B9743F', '7A4A26', rough=.5, scale=2.5, bump=.25, coat=.2)
    box((1.4, 1.1, 1.0), (0, 0, .5), wall, .04)
    for s in (-1, 1):
        box((1.6, .85, .1), (0, s * .32, 1.24), roof, .03, rot=(s * -40, 0, 0))
    box((1.62, .12, .12), (0, 0, 1.52), mat(S_GOLD, .3, .45, coat=.8), .04)
    box((.2, .22, .4), (.45, .25, 1.45), tex('tiles', 'B85B3E', 'E8DECB', rough=.6, scale=6, bump=.2, c3='A44E33'), .02)
    # the door, ajar, warm light inside, gold knob, step and mat
    box((.46, .02, .72), (-.18, -.556, .4), mat('FFD27A', .5, emit=2.2), 0)
    door = box((.46, .06, .72), (-.36, -.72, .4), wood, .02, rot=(0, 0, -62))
    sphere(.035, (-.27, -.92, .4), mat(S_GOLD, .25, .6))
    box((.6, .3, .06), (-.18, -.75, .03), tex('fabric', 'C0392B', '8E2A20', rough=.8, scale=1, bump=.1, coat=0), .02)
    # window with warm light and a navy frame
    box((.34, .03, .3), (.35, -.556, .62), mat('FFE3A3', .4, emit=1.2), 0)
    fr = mat(S_NAVY, .4)
    for z in (.455, .785, .62):
        box((.4, .05, .04), (.35, -.565, z), fr, .01)
    for x in (.17, .53, .35):
        box((.04, .05, .36), (x, -.565, .62), fr, .01)
    studio(elev=20, yaw=-24)


SOCIAL_ICONS = {
    'friends': icon_friends, 'gift': icon_gift, 'help': icon_help, 'like': icon_like,
    'request': icon_request, 'share': icon_share, 'invite': icon_invite, 'visit': icon_visit,
}
