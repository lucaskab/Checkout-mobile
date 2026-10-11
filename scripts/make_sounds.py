"""Synthesised sound effects for the mini-games (register and store mishaps).

Softer, richer replacements for the raw sine/noise blips: bell partials, filtered noise with real envelopes,
a touch of room reverb. Writes 44.1 kHz mono WAVs to Resources/CheckoutDesktop/Sounds.
Run: python scripts/make_sounds.py <out dir>
"""
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
rng = np.random.default_rng(7)


def t_(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, attack=.005, decay=None, sustain=1.0, release=.05):
    n = int(n)
    """Attack / exponential decay envelope over n samples."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    if decay:
        a = a * np.exp(-np.maximum(t - attack, 0) / decay)
    r = np.clip((n / SR - t) / max(release, 1e-4), 0, 1)
    return a * r * sustain


def band(x, lo, hi, order=3):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), .99)], btype='band')
    return signal.lfilter(b, a, x)


def lowpass(x, hi, order=3):
    b, a = signal.butter(order, hi / (SR / 2), btype='low')
    return signal.lfilter(b, a, x)


def noise(sec):
    return rng.uniform(-1, 1, int(SR * sec))


def bell(freq, sec, decay=.35, partials=((1, 1), (2.76, .45), (5.4, .25), (8.93, .12))):
    t = t_(sec); out = np.zeros_like(t)
    for ratio, amp in partials:
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / (decay / ratio ** .5))
    return out * env(len(t), .002, None, 1, .02)


def tone(freq, sec, shape='sine', f2=None):
    t = t_(sec)
    f = np.linspace(freq, f2 or freq, len(t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == 'square':
        return lowpass(np.sign(np.sin(ph)) * .6, 5000)
    if shape == 'tri':
        return 2 / np.pi * np.arcsin(np.sin(ph))
    return np.sin(ph)


def reverb(x, room=.18, mix=.18):
    n = int(SR * room)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (SR * room / 5))
    ir = lowpass(ir, 6000)
    wet = signal.fftconvolve(x, ir)[:len(x) + n]
    dry = np.concatenate([x, np.zeros(n)])[:len(wet)]
    wet = wet / (np.max(np.abs(wet)) + 1e-9) * np.max(np.abs(x))
    return dry * (1 - mix) + wet * mix


def cat(*parts, gap=0.0):
    out = []
    for p in parts:
        out.append(p)
        if gap:
            out.append(np.zeros(int(SR * gap)))
    return np.concatenate(out)


def mixat(base, x, at):
    i = int(SR * at)
    need = i + len(x)
    if need > len(base):
        base = np.concatenate([base, np.zeros(need - len(base))])
    base[i:i + len(x)] += x
    return base


def fade_tail(x, sec=.01):
    n = min(len(x), int(SR * sec))
    x[-n:] *= np.linspace(1, 0, n)
    return x


def write(path, x, peak=.8):
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)
    m = np.max(np.abs(x)) or 1
    x = fade_tail(x / m * peak)
    data = (x * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())


# ---------------------------------------------------------------- register
# Cozy register (Lucas, 11/10: "sons mais agradáveis"): warm wooden/marimba tones in the 400-2000 Hz range instead of
# the piercing 2.7 kHz square beep and 4 kHz coin bells, soft attacks, paper and coins lowpassed, a little room.
def marimba(freq, sec, decay=.22, bright=.25):
    """Struck wooden bar: fundamental plus the marimba's 4x and 10x partials, which die away fast (warm, round)."""
    t = t_(sec)
    x = np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)
    x += bright * np.sin(2 * np.pi * freq * 3.93 * t) * np.exp(-t / (decay * .25))
    x += bright * .3 * np.sin(2 * np.pi * freq * 9.7 * t) * np.exp(-t / (decay * .08))
    return x * env(len(t), .003, None, 1, .02)


def scan_beep():
    # A soft two-note "bip-bop" chime (B5 then E6), like a friendly scanner, not a smoke alarm.
    x = mixat(marimba(987.8, .16, .07, .18) * .9, marimba(1318.5, .2, .08, .15), .055)
    return reverb(lowpass(x, 4500), .12, .12)


def cash_register():
    # Wooden "clack" of the keys, then a warm two-bell "ka-ching" an octave lower than before.
    clack = lowpass(band(noise(.04), 600, 3000), 2500) * env(int(SR * .04), .001, .01) * .6
    ring = bell(1046.5, .9, .45, ((1, 1), (2.0, .35), (3.0, .12))) * .8 + bell(1318.5, .9, .4, ((1, 1), (2.0, .3), (3.0, .1))) * .55
    x = mixat(np.zeros(1), clack, 0)
    x = mixat(x, clack * .7, .05)
    x = mixat(x, lowpass(ring, 5000), .1)
    return reverb(x, .28, .22)


def drawer_open():
    # The drawer rolls out on soft rails and stops with a gentle wooden knock.
    n = int(SR * .3)
    roll = lowpass(band(noise(.3), 120, 900), 800) * np.linspace(.25, .8, n) * env(n, .02, None, 1, .04)
    thunk = tone(140, .12, 'sine', 90) * env(int(SR * .12), .002, .04) * 1.2
    knock = marimba(523.25, .25, .06, .1) * .35
    x = mixat(roll, thunk, .28)
    x = mixat(x, knock, .29)
    return reverb(x, .22, .16)


def coin(seed=0):
    # Coins dropped on a felt tray: two or three small, rounded clinks, nothing above ~4 kHz.
    r = np.random.default_rng(seed)
    x = np.zeros(1)
    for k, at in enumerate((0, .05 + r.uniform(0, .02), .1 + r.uniform(0, .03))):
        f = r.uniform(1800, 2500)
        hit = bell(f, .25, .06, ((1, 1), (1.51, .35), (2.43, .15))) * (1 - k * .35)
        x = mixat(x, hit, at)
    return reverb(lowpass(x, 4200), .14, .14)


def note_rustle(seed=0):
    # A banknote laid down: a short, soft paper swish (no hiss).
    r = np.random.default_rng(seed)
    n = int(SR * .18)
    flutter = 1 + .35 * np.sin(2 * np.pi * r.uniform(18, 26) * t_(.18))
    x = lowpass(band(noise(.18), 500, 3200), 2600) * flutter * env(n, .02, .06)
    return x * .8


def card_slide():
    n = int(SR * .18)
    x = lowpass(band(noise(.18), 500, 2400), 2000) * env(n, .015, None, 1, .04) * np.linspace(1, .5, n)
    x = mixat(x, marimba(660, .08, .02, .05) * .25, .16)
    return x


def approved():
    # Card approved: a happy marimba third (C6 - E6).
    a = marimba(1046.5, .45, .18, .2) * .8; b = marimba(1318.5, .6, .22, .2)
    return reverb(mixat(a, b, .1), .25, .2)


def declined():
    # Card declined: two soft low notes going down, not a buzzer.
    a = marimba(392, .3, .12, .12); b = marimba(329.6, .45, .16, .12)
    return reverb(cat(a, b, gap=.02), .18, .14) * .8


def printer():
    n = int(SR * .45)
    gate = (np.sin(2 * np.pi * 26 * t_(.45)) > .2).astype(float)
    x = band(noise(.45), 1200, 4500) * gate * env(n, .005, None, 1, .04) * .7
    x += tone(95, .45) * .15 * env(n, .02, None, 1, .05)
    return x


# ---------------------------------------------------------------- UI
def pop():
    x = tone(420, .08, 'sine', 980) * env(int(SR * .08), .002, .03)
    return reverb(x, .1, .12)


def tap():
    # Soft wooden tick (was a bright 6 kHz click).
    return mixat(lowpass(band(noise(.025), 800, 3000), 2500) * env(int(SR * .025), .001, .005) * .8, marimba(880, .05, .015, .05) * .35, 0)


def whoosh():
    n = int(SR * .26)
    b, a = signal.butter(2, [500 / (SR / 2), 3500 / (SR / 2)], btype='band')
    x = signal.lfilter(b, a, noise(.26)) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return x


def bonk():
    x = tone(220, .16, 'sine', 140) * env(int(SR * .16), .002, .05)
    x = mixat(x, band(noise(.03), 300, 1500) * env(int(SR * .03), .001, .01) * .5, 0)
    return reverb(x, .1, .1)


def success():
    x = np.zeros(1)
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        x = mixat(x, bell(f, 1.0, .5) * (.8 + k * .08), k * .09)
    return reverb(x, .35, .25)


def pad(freq, sec, attack=.03, decay=.9):
    """Warm sustained note (sine with soft 2nd/3rd harmonics), no vibrato: steady and bright."""
    t = t_(sec)
    x = np.sin(2 * np.pi * freq * t) + .35 * np.sin(4 * np.pi * freq * t) + .12 * np.sin(6 * np.pi * freq * t)
    return x * env(len(t), attack, decay, 1, .25)


def levelup():
    """Level up: the bright C-E-G-C bell run (as 'success'), then a held C major chord and rising sparkles.
    Every interval is major and nothing wobbles, so it reads as a reward."""
    x = np.zeros(1)
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        x = mixat(x, bell(f, .9, .45) * (.75 + k * .08), k * .085)
    chord_at = .36
    for f, amp in ((261.63, .35), (523.25, .55), (659.25, .45), (783.99, .45), (1046.5, .4)):
        x = mixat(x, pad(f, 1.5, .02, .7) * amp, chord_at)
        x = mixat(x, bell(f * 2, 1.2, .6) * amp * .35, chord_at)
    for k, f in enumerate((1567.98, 2093.0, 2637.0, 3135.96, 4186.0)):
        x = mixat(x, bell(f, .5, .18) * (.22 - k * .02), chord_at + .1 + k * .07)
    return reverb(x, .45, .28)


def conquest():
    """Conquest (a lot, an expansion, a sector ready): a quick rising shimmer, a G major chord and sparkles.
    Shorter and lighter than the level-up fanfare, every interval major, nothing wobbles."""
    x = np.zeros(1)
    for k, f in enumerate((783.99, 987.77, 1174.66, 1567.98)):
        x = mixat(x, bell(f, .7, .3) * (.55 + k * .1), k * .05)
    at = .24
    for f, amp in ((196.0, .3), (392.0, .5), (493.88, .42), (587.33, .42), (783.99, .38)):
        x = mixat(x, pad(f, 1.2, .015, .55) * amp, at)
        x = mixat(x, bell(f * 2, .9, .45) * amp * .3, at)
    for k, f in enumerate((2349.32, 3135.96, 3951.07)):
        x = mixat(x, bell(f, .4, .15) * (.2 - k * .03), at + .08 + k * .08)
    return reverb(x, .4, .25)


def bubble(seed=0):
    r = np.random.default_rng(seed)
    f0 = r.uniform(900, 1400)
    x = tone(f0, .05, 'sine', f0 * .55) * env(int(SR * .05), .001, .015)
    return x


# ---------------------------------------------------------------- cleaning
def scrub(seed=0):
    r = np.random.default_rng(seed)
    n = int(SR * .22)
    wet = band(noise(.22), 350, 2200) * (1 + .5 * np.sin(2 * np.pi * r.uniform(9, 14) * t_(.22)))
    squeak = np.sin(2 * np.pi * np.cumsum(r.uniform(1100, 1500) + 90 * np.sin(2 * np.pi * 7 * t_(.22))) / SR) * .12
    return (wet + squeak) * np.sin(np.linspace(0, np.pi, n)) ** 1.5


def glass(seed=0):
    r = np.random.default_rng(seed + 10)
    x = np.zeros(1)
    for k in range(r.integers(2, 4)):
        f = r.uniform(4200, 7800)
        hit = bell(f, .25, .05, ((1, 1), (1.63, .5), (2.71, .3))) * r.uniform(.5, 1)
        x = mixat(x, hit, k * r.uniform(.025, .06))
    return reverb(x, .18, .18)


def glass_dump():
    x = np.zeros(1)
    for k in range(10):
        x = mixat(x, glass(k) * (1 - k * .06), k * .028)
    return x


def sweep(seed=0):
    r = np.random.default_rng(seed + 20)
    n = int(SR * .3)
    b, a = signal.butter(2, [r.uniform(1800, 2600) / (SR / 2), 9000 / (SR / 2)], btype='band')
    x = signal.lfilter(b, a, noise(.3)) * np.sin(np.linspace(0, np.pi, n)) ** 1.2
    return x * (1 + .25 * np.sin(2 * np.pi * 40 * t_(.3)))


def trash():
    thud = tone(95, .12, 'sine', 60) * env(int(SR * .12), .001, .04)
    rustle = band(noise(.15), 1500, 6000) * env(int(SR * .15), .003, .05) * .5
    return reverb(mixat(thud, rustle, .005), .15, .15)


def pickup():
    x = tone(600, .06, 'sine', 1100) * env(int(SR * .06), .002, .02) * .6
    return mixat(x, band(noise(.04), 2000, 6000) * env(int(SR * .04), .001, .01) * .3, 0)


# ---------------------------------------------------------------- lamp
def twist(seed=0):
    r = np.random.default_rng(seed + 30)
    x = np.zeros(1)
    for k in range(4):
        tick = band(noise(.012), 2500, 9000) * env(int(SR * .012), .0005, .003)
        x = mixat(x, tick * r.uniform(.5, 1), k * .035)
    sq = np.sin(2 * np.pi * np.cumsum(np.linspace(2300, 2600, int(SR * .13))) / SR) * env(int(SR * .13), .01, .05) * .15
    return mixat(x, sq, .0)


def bulb_on():
    n = int(SR * .7)
    hum = (tone(100, .7) * .5 + tone(200, .7) * .25 + tone(300, .7) * .1) * np.linspace(0, 1, n) * env(n, .05, None, 1, .2)
    ping = bell(1760, .8, .4) * .7
    return reverb(mixat(hum * .6, ping, .45), .25, .2)


def zap():
    n = int(SR * .22)
    crackle = noise(.22) * (rng.uniform(0, 1, n) > .92) * env(n, .001, .08)
    return band(crackle, 1500, 9000) + band(noise(.22), 3000, 9000) * env(n, .001, .03) * .3


SOUNDS = {
    'scan_beep': scan_beep, 'cash_register': cash_register, 'drawer_open': drawer_open,
    'coin_0': lambda: coin(0), 'coin_1': lambda: coin(1), 'coin_2': lambda: coin(2),
    'note_0': lambda: note_rustle(0), 'note_1': lambda: note_rustle(1),
    'card_slide': card_slide, 'card_ok': approved, 'card_no': declined, 'printer': printer,
    'pop': pop, 'tap': tap, 'whoosh': whoosh, 'bonk': bonk, 'success': success, 'levelup': levelup, 'conquest': conquest,
    'bubble_0': lambda: bubble(0), 'bubble_1': lambda: bubble(1), 'bubble_2': lambda: bubble(2),
    'scrub_0': lambda: scrub(0), 'scrub_1': lambda: scrub(1), 'scrub_2': lambda: scrub(2),
    'glass_0': lambda: glass(0), 'glass_1': lambda: glass(1), 'glass_2': lambda: glass(2), 'glass_dump': glass_dump,
    'sweep_0': lambda: sweep(0), 'sweep_1': lambda: sweep(1), 'trash': trash, 'pickup': pickup,
    'twist_0': lambda: twist(0), 'twist_1': lambda: twist(1), 'bulb_on': bulb_on, 'zap': zap,
}

if __name__ == '__main__':
    # python scripts/make_sounds.py <out dir> [name ...]: only the named sounds when names are given.
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'Sounds'); out.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[2:])
    for name, make in SOUNDS.items():
        if only and name not in only:
            continue
        quiet = name in ('tap',) or name.startswith(('coin_', 'note_'))  # heard many times in a row: softer
        write(out / (name + '.wav'), make(), peak=.55 if name in ('success', 'cash_register', 'bulb_on', 'levelup', 'conquest') else .5 if quiet else .7)
        print('SOUND', name)
