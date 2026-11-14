#!/usr/bin/env python3
"""The Steam Bowl -- food-picture-01 entry.

A big bowl of tonkotsu ramen, close and slightly from above: chopsticks
lifting a swirl of glossy noodles, a halved soft egg with a runny yolk,
spring onions, nori, steam curling up, rich warm broth on a dark wooden
table. Pure procedural drawing, Python stdlib only. No text anywhere.
Deterministic: fixed seed, same bytes every run.
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
RNG = random.Random(20261114)


def out_dir():
    d = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if d:
        return d
    if os.path.isdir("/output") and os.access("/output", os.W_OK):
        return "/output"
    return "/tmp"


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def fill(self, r, g, b):
        self.px[:] = bytes((r, g, b)) * (self.w * self.h)

    def _row(self, y, x0, x1, r, g, b):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        self.px[i:i + (x1 - x0 + 1) * 3] = bytes((r, g, b)) * (x1 - x0 + 1)

    def blend_row(self, y, x0, x1, r, g, b, a):
        if y < 0 or y >= self.h or a <= 0:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        px = self.px
        inv = 255 - a
        for x in range(x0, x1 + 1):
            i = (y * self.w + x) * 3
            px[i] = (r * a + px[i] * inv) // 255
            px[i + 1] = (g * a + px[i + 1] * inv) // 255
            px[i + 2] = (b * a + px[i + 2] * inv) // 255

    def ellipse(self, cx, cy, rx, ry, r, g, b, a=255):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(1 - dy * dy)
            if a >= 255:
                self._row(y, cx - dx, cx + dx, r, g, b)
            else:
                self.blend_row(y, cx - dx, cx + dx, r, g, b, a)

    def circle(self, cx, cy, rad, r, g, b, a=255):
        self.ellipse(cx, cy, rad, rad, r, g, b, a)

    def poly(self, pts, r, g, b, a=255):
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                if a >= 255:
                    self._row(y, xs[k], xs[k + 1], r, g, b)
                else:
                    self.blend_row(y, xs[k], xs[k + 1], r, g, b, a)


def cubic(p0, p1, p2, p3, t):
    u = 1 - t
    return (u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0]
            + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1]
            + t * t * t * p3[1])


def strand(cv, p0, p1, p2, p3, rad, col, n=40, hi=None, clip=None):
    pts = [cubic(p0, p1, p2, p3, i / (n - 1)) for i in range(n)]
    for (x, y) in pts:
        if clip and not clip(x, y):
            continue
        cv.circle(x, y, rad, *col)
    if hi:
        for (x, y) in pts:
            if clip and not clip(x, y):
                continue
            cv.circle(x - 1, y - 1, max(1, rad // 2), *hi)


def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def grade(cv):
    """Vignette the edges, warm the light from the upper left."""
    px = cv.px
    w = cv.w
    h = cv.h
    for y in range(h):
        ny = (y - h / 2) / (h / 2)
        base = y * w * 3
        for x in range(w):
            nx = (x - w / 2) / (w / 2)
            d = math.sqrt(nx * nx + ny * ny)
            v = 1.0
            if d > 0.55:
                v = 1.0 - 0.30 * min(1.0, (d - 0.55) / 0.5)
            lx = (x - 190) / 720.0
            ly = (y - 150) / 720.0
            l2 = lx * lx + ly * ly
            warm = 0.10 * max(0.0, 1.0 - l2)
            i = base + x * 3
            px[i] = min(255, int(px[i] * v + 255 * warm * 0.9))
            px[i + 1] = min(255, int(px[i + 1] * v + 255 * warm * 0.55))
            px[i + 2] = max(0, min(255, int(px[i + 2] * v - 255 * warm * 0.15)))


def draw_table(cv):
    cv.fill(59, 36, 22)
    # wood grain: wavy horizontal streaks, two tones
    for gi in range(26):
        y0 = 30 + gi * 38 + RNG.randint(-6, 6)
        ph = RNG.uniform(0, 6.28)
        tone = (42, 24, 12) if gi % 3 else (78, 47, 26)
        for x in range(0, W, 26):
            y = y0 + int(4 * math.sin(x / 180.0 + ph))
            cv._row(y, x, x + 26, *tone)
            cv._row(y + 1, x, x + 26, *tone)
    # plank seams
    for sx in (330, 690):
        for y in range(H):
            cv.blend_row(y, sx, sx + 2, 20, 11, 6, 90)


def draw_bowl(cv):
    # soft shadow under the bowl
    cv.ellipse(512, 902, 412, 58, 12, 7, 4, 70)
    cv.ellipse(512, 894, 392, 48, 12, 7, 4, 60)
    # outer bowl, inner wall, broth
    cv.ellipse(512, 575, 405, 315, 29, 40, 49)
    cv.ellipse(512, 570, 388, 300, 43, 60, 71)
    cv.ellipse(512, 565, 362, 278, 168, 90, 22)
    cv.ellipse(512, 550, 300, 225, 192, 122, 36)
    cv.ellipse(470, 520, 200, 140, 217, 143, 46, 120)
    # rim highlight, upper-left arc
    for k in range(70):
        t = math.pi * (1.05 + 0.55 * k / 69)
        x = 512 + 396 * math.cos(t)
        y = 572 + 306 * math.sin(t)
        cv.circle(x, y, 4, 150, 175, 190, 150)


def broth_bits(cv):
    # oil droplets with a gloss dot each
    for _ in range(24):
        a = RNG.uniform(0, 6.28)
        rr = math.sqrt(RNG.uniform(0.1, 0.9))
        x = 512 + 330 * rr * math.cos(a)
        y = 565 + 250 * rr * math.sin(a)
        r = RNG.randint(5, 12)
        cv.circle(x, y, r, 232, 168, 60, 200)
        cv.circle(x - r // 3, y - r // 3, 2, 255, 240, 200, 170)
    # sesame seeds
    for _ in range(34):
        a = RNG.uniform(0, 6.28)
        rr = math.sqrt(RNG.uniform(0.05, 0.95))
        x = 512 + 340 * rr * math.cos(a)
        y = 565 + 258 * rr * math.sin(a)
        cv.circle(x, y, 2, 242, 227, 192, 220)


def draw_nori(cv):
    cv.poly([(428, 332), (582, 316), (602, 432), (448, 448)], 22, 36, 26)
    cv.poly([(440, 344), (578, 330), (586, 352), (446, 364)], 42, 68, 38)


def draw_chashu(cv):
    for (cx, cy, r) in ((715, 620, 80), (778, 522, 66)):
        cv.circle(cx, cy, r, 150, 96, 62)
        cv.circle(cx, cy, int(r * 0.78), 217, 154, 110)
        cv.circle(cx - r // 4, cy - r // 4, int(r * 0.3), 232, 178, 134)
        for _ in range(12):
            a = RNG.uniform(0, 6.28)
            rr = RNG.uniform(0.2, 0.85) * r
            cv.circle(cx + rr * math.cos(a), cy + rr * math.sin(a),
                      RNG.randint(2, 5), 138, 75, 46, 200)


def draw_egg(cv):
    cv.ellipse(336, 700, 96, 67, 217, 201, 168, 120)
    cv.ellipse(330, 690, 100, 72, 243, 234, 214)
    cv.circle(330, 690, 44, 224, 138, 12)
    cv.circle(330, 690, 30, 242, 165, 31)
    cv.circle(318, 678, 7, 255, 240, 200, 180)
    cv.circle(330, 690, 12, 250, 190, 80, 120)


def in_broth(x, y):
    return ((x - 512) / 362.0) ** 2 + ((y - 565) / 278.0) ** 2 <= 1.0


def draw_onions(cv):
    for _ in range(46):
        a = RNG.uniform(0, 6.28)
        rr = math.sqrt(RNG.uniform(0.05, 0.95))
        x = 512 + 340 * rr * math.cos(a)
        y = 565 + 258 * rr * math.sin(a)
        if RNG.random() < 0.7:
            cv.circle(x, y, RNG.randint(4, 6), 78, 155, 62)
            cv.circle(x, y, 2, 140, 203, 102)
        else:
            cv.circle(x, y, RNG.randint(3, 5), 232, 232, 216)


NOODLE = (227, 185, 92)
NOODLE_DARK = (192, 138, 53)
NOODLE_HI = (242, 206, 126)


def draw_bowl_noodles(cv):
    # central swirl: three concentric arcs
    for (rx, ry, col) in ((150, 105, NOODLE), (115, 80, NOODLE_DARK),
                          (80, 55, NOODLE_HI)):
        for k in range(90):
            t = 6.28 * k / 89
            x = 520 + rx * math.cos(t)
            y = 560 + ry * math.sin(t)
            if in_broth(x, y):
                cv.circle(x, y, 6, *col)
    # loose strands across the broth
    for _ in range(52):
        sx = RNG.uniform(220, 800)
        sy = RNG.uniform(360, 790)
        if not in_broth(sx, sy):
            continue
        ex = sx + RNG.uniform(-160, 160)
        ey = sy + RNG.uniform(-70, 70)
        if not in_broth(ex, ey):
            continue
        col = RNG.choice([NOODLE, NOODLE, NOODLE_DARK, NOODLE_HI])
        hi = (250, 220, 150) if col != NOODLE_HI else None
        strand(cv, (sx, sy),
               (sx + RNG.uniform(-90, 90), sy + RNG.uniform(-60, 60)),
               (ex + RNG.uniform(-90, 90), ey + RNG.uniform(-60, 60)),
               (ex, ey), RNG.randint(5, 6), col, hi=hi, clip=in_broth)


def draw_chopsticks(cv):
    cv.poly([(880, 92), (652, 298), (641, 311), (870, 106)], 122, 68, 35)
    cv.poly([(884, 100), (654, 300), (648, 307), (878, 108)], 154, 92, 51)
    cv.poly([(908, 138), (674, 316), (665, 329), (900, 151)], 107, 58, 30)
    cv.poly([(911, 145), (675, 318), (670, 325), (904, 153)], 138, 82, 46)


def draw_lifted_noodles(cv):
    # a glossy bundle rising from the broth to the chopstick tips
    for i in range(22):
        spread = (i - 11) / 11.0
        sx = 585 + spread * 70 + RNG.uniform(-12, 12)
        sy = 452 + abs(spread) * 26 + RNG.uniform(-8, 8)
        tx = 648 + spread * 26 + RNG.uniform(-8, 8)
        ty = 302 + abs(spread) * 14 + RNG.uniform(-6, 6)
        bow = 470 + spread * 150
        col = RNG.choice([NOODLE, NOODLE, NOODLE_HI, NOODLE_DARK])
        hi = (250, 220, 150) if col != NOODLE_HI else None
        strand(cv, (sx, sy), (bow, 400), (bow + 60, 330), (tx, ty),
               RNG.randint(5, 6), col, n=36, hi=hi)
    # a few strands draped over the chopsticks themselves
    for i in range(5):
        x0 = 640 + i * 9
        strand(cv, (x0, 296), (x0 + 14, 318), (x0 + 4, 336), (x0 - 8, 348),
               5, NOODLE_HI, n=18, hi=(250, 220, 150))
    # dangling strands falling back into the broth
    for i in range(4):
        x0 = 560 + i * 26
        strand(cv, (x0, 470), (x0 - 18, 520), (x0 + 10, 560), (x0 - 4, 600),
               5, NOODLE, n=22)


def draw_steam(cv):
    for wx in (430, 490, 550, 610, 662):
        ph = RNG.uniform(0, 6.28)
        for k in range(15):
            t = k / 14.0
            y = 390 - t * 270
            x = wx + 22 * math.sin(t * 5.0 + ph) * (0.4 + t)
            r = 9 + 14 * math.sin(t * 3.14)
            cv.circle(x, y, r, 255, 250, 242, RNG.randint(12, 22))


def draw():
    cv = Canvas(W, H)
    draw_table(cv)
    draw_bowl(cv)
    broth_bits(cv)
    draw_nori(cv)
    draw_chashu(cv)
    draw_egg(cv)
    draw_onions(cv)
    draw_bowl_noodles(cv)
    draw_chopsticks(cv)
    draw_lifted_noodles(cv)
    draw_steam(cv)
    grade(cv)
    return cv


def main():
    cv = draw()
    out = os.path.join(out_dir(), "entry.png")
    with open(out, "wb") as f:
        f.write(png_bytes(cv))
    print(out)


if __name__ == "__main__":
    main()
