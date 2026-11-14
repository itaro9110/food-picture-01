#!/usr/bin/env python3
"""Smash burger with a molten cheese pull -- procedural food picture.

Pure Python 3 stdlib. Deterministic: one fixed seed, no time/os input,
no network. Writes a 1024x1024 PNG to <out>/entry.png, where <out> is
MAKEFUN_OUTPUT_DIR, else /output if it exists and is writable, else /tmp.
"""
import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
RNG = random.Random(20261114)
PX = [bytearray(W * 3) for _ in range(H)]


def mix(c0, c1, t):
    return (int(c0[0] + (c1[0] - c0[0]) * t + 0.5),
            int(c0[1] + (c1[1] - c0[1]) * t + 0.5),
            int(c0[2] + (c1[2] - c0[2]) * t + 0.5))


def hline(y, x0, x1, c):
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x1 < x0:
        return
    PX[y][x0 * 3:(x1 + 1) * 3] = bytes(c) * (x1 - x0 + 1)


def fill_rect(x0, y0, x1, y1, c):
    for y in range(max(0, int(y0)), min(H, int(y1) + 1)):
        hline(y, x0, x1, c)


def vgrad(y0, y1, c0, c1):
    for y in range(max(0, y0), min(H, y1 + 1)):
        t = (y - y0) / max(y1 - y0, 1)
        fill_rect(0, y, W - 1, y, mix(c0, c1, t))


def ellipse(cx, cy, rx, ry, c):
    rx = float(rx)
    ry = float(ry)
    for y in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
        dy = (y - cy) / ry
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        dx = rx * math.sqrt(d)
        hline(y, cx - dx, cx + dx, c)


def disc(cx, cy, r, c):
    ellipse(cx, cy, r, r, c)


def ellipse_outline(cx, cy, rx, ry, t, c):
    for y in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
        dy = (y - cy) / ry
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        dxo = rx * math.sqrt(d)
        di = 1.0 - ((y - cy) / max(ry - t, 1.0)) ** 2
        if di <= 0:
            hline(y, cx - dxo, cx + dxo, c)
        else:
            dxi = max(rx - t, 1.0) * math.sqrt(di)
            hline(y, cx - dxo, cx - dxi, c)
            hline(y, cx + dxi, cx + dxo, c)


def poly(pts, c):
    ys = [p[1] for p in pts]
    n = len(pts)
    for y in range(max(0, int(min(ys))), min(H, int(max(ys)) + 1)):
        xs = []
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            hline(y, xs[i], xs[i + 1], c)


def glow(cx, cy, rmax, c_in, c_out, steps=22, squash=0.82):
    for i in range(steps, 0, -1):
        t = i / steps
        ellipse(cx, cy, rmax * t, rmax * t * squash,
                mix(c_in, c_out, t))


def blend_ellipse(cx, cy, rx, ry, c, alpha):
    for y in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
        dy = (y - cy) / ry
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        dx = int(rx * math.sqrt(d))
        row = PX[y]
        for x in range(max(0, int(cx - dx)), min(W, int(cx + dx) + 1)):
            o = x * 3
            row[o] = int(row[o] + (c[0] - row[o]) * alpha + 0.5)
            row[o + 1] = int(row[o + 1] + (c[1] - row[o + 1]) * alpha + 0.5)
            row[o + 2] = int(row[o + 2] + (c[2] - row[o + 2]) * alpha + 0.5)


def bez(p0, p1, p2, steps=26):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        pts.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return pts


def strand(pts, r0, r1, c, hi):
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / max(n - 1, 1)
        r = r0 + (r1 - r0) * t
        disc(x, y, r, c)
        disc(x - r * 0.35, y, r * 0.3, hi)


def drip(x, y0, depth, w, c, hi):
    fill_rect(x - w // 2, y0, x + w // 2, y0 + depth, c)
    disc(x, y0 + depth, w // 2, c)
    disc(x, y0, w // 2, c)
    hline(y0 + depth // 2, x - w // 2 + 3, x - w // 2 + 8, hi)


def _chunk(typ, data):
    ch = struct.pack(">I", len(data)) + typ + data
    return ch + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def write_png(path):
    raw = bytearray()
    for row in PX:
        raw.append(0)
        raw.extend(row)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def out_dir():
    d = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if d:
        return d
    if os.path.isdir("/output") and os.access("/output", os.W_OK):
        return "/output"
    return "/tmp"


def draw():
    # Backdrop: warm dark gradient, amber glow from upper left.
    vgrad(0, H - 1, (48, 27, 16), (20, 11, 6))
    glow(390, 290, 700, (128, 76, 34), (30, 17, 9), steps=48)
    glow(370, 250, 380, (158, 96, 42), (60, 32, 14), steps=48)
    # Wooden table.
    fill_rect(0, 690, W - 1, H - 1, (56, 35, 19))
    for yy in (762, 852, 942):
        fill_rect(0, yy, W - 1, yy + 3, (36, 21, 11))
    for _ in range(46):
        gx = RNG.uniform(0, W)
        gy = RNG.uniform(700, 1010)
        ellipse(gx, gy, RNG.uniform(90, 320), RNG.uniform(1.5, 3.5),
                (46, 28, 15) if RNG.random() < 0.6 else (76, 49, 27))
    blend_ellipse(512, 880, 430, 130, (130, 76, 32), 0.22)
    # Dark ceramic plate.
    ellipse(512, 818, 398, 116, (56, 50, 46))
    ellipse(512, 815, 378, 106, (40, 36, 33))
    ellipse_outline(512, 815, 378, 106, 5, (96, 88, 78))
    ellipse(430, 726, 120, 11, (124, 114, 102))
    blend_ellipse(512, 895, 310, 34, (0, 0, 0), 0.28)

    # Top bun: tall golden brioche dome, smooth vertical gradient.
    for yy in range(350, 607):
        t = (yy - 350) / 256.0
        dy = (yy - 478) / 128.0
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        dx = 295 * math.sqrt(d)
        hline(yy, 512 - dx, 512 + dx, mix((234, 170, 86), (166, 98, 34), t))
    ellipse(430, 402, 95, 14, (255, 232, 172))
    for ry in range(430, 530, 8):
        ex = 512 + 295 * math.sqrt(max(0.0, 1 - ((ry - 478) / 128.0) ** 2))
        disc(ex - 9, ry, 6, (232, 152, 72))
    # Lettuce ruffle peeking under the bun: flat overlapping leaves.
    ellipse(512, 622, 296, 22, (64, 112, 30))
    for i in range(34):
        lx = 222 + i * 17.5 + RNG.uniform(-5, 5)
        ellipse(lx, 628 + RNG.uniform(-3, 7), RNG.uniform(20, 30),
                RNG.uniform(8, 12),
                RNG.choice([(96, 160, 48), (78, 134, 38), (122, 182, 62)]))

    # Tomato slice.
    ellipse(512, 672, 282, 52, (196, 48, 30))
    ellipse(512, 672, 258, 42, (218, 70, 44))
    ellipse(410, 656, 110, 9, (248, 124, 78))
    # Bottom bun (before the patty so the patty overlaps its top).
    for yy in range(808, 925):
        t = (yy - 808) / 116.0
        dy = (yy - 866) / 58.0
        d = 1.0 - dy * dy
        if d <= 0:
            continue
        dx = 288 * math.sqrt(d)
        hline(yy, 512 - dx, 512 + dx, mix((208, 144, 64), (158, 98, 36), t))
    ellipse(400, 838, 140, 10, (226, 164, 84))
    ellipse_outline(512, 866, 288, 58, 4, (140, 88, 30))
    # Thick charred smash patty with glistening speckles.
    ellipse(512, 772, 306, 84, (74, 38, 18))
    ellipse(370, 730, 130, 13, (150, 86, 36))
    for _ in range(260):
        sx = RNG.uniform(222, 802)
        sy = RNG.uniform(697, 847)
        if ((sx - 512) / 290) ** 2 + ((sy - 772) / 75) ** 2 > 1:
            continue
        r = RNG.random()
        col = (46, 24, 10) if r < 0.6 else ((96, 52, 22)
              if r < 0.85 else (190, 110, 46))
        disc(sx, sy, RNG.uniform(1.5, 4), col)

    # Molten cheese draped over the patty, with glossy drips.
    ellipse(512, 700, 302, 48, (246, 158, 24))
    ellipse(512, 688, 295, 30, (255, 184, 64))
    for x, depth, w in ((300, 62, 36), (420, 84, 42), (560, 56, 34),
                        (690, 76, 40)):
        drip(x, 716, depth, w, (246, 158, 24), (255, 200, 90))
    # Cheese pull strands running down the front of the stack.
    strand(bez((398, 600), (372, 648), (402, 704)), 21, 11,
           (255, 168, 32), (255, 208, 96))
    strand(bez((644, 600), (672, 648), (646, 704)), 23, 12,
           (255, 168, 32), (255, 208, 96))
    strand(bez((520, 602), (510, 650), (526, 700)), 12, 7,
           (255, 168, 32), (255, 208, 96))

    # Sesame seeds scattered on the dome.
    for gx in range(6):
        for gy in range(4):
            sx = 290 + gx * 74 + RNG.uniform(-14, 14)
            sy = 388 + gy * 30 + RNG.uniform(-10, 10)
            if ((sx - 512) / 255) ** 2 + ((sy - 478) / 105) ** 2 > 1:
                continue
        rx = RNG.uniform(6, 9)
        ellipse(sx, sy, rx, rx * 0.55, (214, 178, 120))
        ellipse(sx - 1, sy - 1, rx * 0.9, rx * 0.5, (250, 230, 180))
    # Thin steam wisps rising off the hot bun.
    for wx in (380, 520, 650):
        for i in range(36):
            t = i / 35.0
            y = 332 - t * 188
            x = wx + math.sin(t * 5.2 + wx) * 14 - t * 10
            disc(x, y, 8 - t * 4, (198, 182, 152))
    # A few crumbs on the plate rim.
    for cx, cy in ((180, 850), (860, 860), (150, 900), (880, 900)):
        disc(cx, cy, 4, (120, 84, 44))
        disc(cx + 8, cy + 5, 3, (90, 60, 30))


def main():
    draw()
    d = out_dir()
    os.makedirs(d, exist_ok=True)
    write_png(os.path.join(d, "entry.png"))


if __name__ == "__main__":
    main()
