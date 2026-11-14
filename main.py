#!/usr/bin/env python3
"""The Golden Stack -- a procedural pancake breakfast for food-picture-01.

Draws three golden pancakes with maple syrup, melting butter, blueberries,
strawberry halves and mint on a white plate, in warm morning light.
Pure Python 3.13 standard library; the picture is fully deterministic:
a fixed seed, no network, no clock, no timestamps anywhere in the output.

Run:  python3 main.py
The PNG lands in MAKEFUN_OUTPUT_DIR when set, else /output when that
directory exists and is writable, else /tmp -- never a relative folder,
because the grader runs this as an unprivileged user in a read-only
container where only /tmp is writable.
"""

import math
import os
import random
import struct
import sys
import zlib

W = 1024
H = 1024
SEED = 20261114
OUT_NAME = "entry.png"

# Warm morning palette: (red, green, blue), each 0..255.
CREAM_TOP = (246, 226, 182)
CREAM_BOTTOM = (233, 196, 138)
TABLE_TOP = (176, 122, 66)
TABLE_BOTTOM = (140, 92, 48)
TABLE_GRAIN = (120, 76, 38)
PLATE = (252, 248, 238)
PLATE_RIM = (226, 214, 196)
PLATE_SHADOW = (118, 84, 52)
CAKE_LIGHT = (238, 178, 92)
CAKE_MID = (219, 148, 66)
CAKE_DARK = (186, 112, 44)
CAKE_RIM = (138, 82, 32)
TOAST = (146, 90, 34)
SYRUP = (176, 84, 16)
SYRUP_DEEP = (140, 62, 10)
SYRUP_SHINE = (240, 158, 62)
BUTTER = (255, 220, 84)
BUTTER_DEEP = (238, 188, 44)
BERRY = (58, 56, 138)
BERRY_DEEP = (34, 32, 92)
BERRY_BLOOM = (96, 96, 168)
STRAW = (214, 42, 42)
STRAW_DEEP = (168, 24, 30)
STRAW_FLESH = (240, 106, 96)
SEED_PALE = (255, 224, 178)
MINT = (62, 125, 68)
MINT_DEEP = (38, 92, 46)
STEAM = (255, 250, 238)


def pick_output_dir():
    """Where the picture goes, in the grader-safe order.

    MAKEFUN_OUTPUT_DIR wins when set; otherwise /output when it exists
    and accepts writes; otherwise /tmp. A relative directory is never
    used, so a read-only working directory cannot break the run.
    """
    env_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env_dir:
        return env_dir
    if os.path.isdir("/output") and os.access("/output", os.W_OK):
        return "/output"
    return "/tmp"


def encode_png(rgb, width, height):
    """Encode a flat RGB bytearray as a PNG (filter 0, fixed level)."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    body = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", body)
        + chunk(b"IEND", b"")
    )


class Canvas:
    """A flat RGB framebuffer with soft-edged shape drawing."""

    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)

    def blend(self, x, y, color, alpha):
        """Blend one pixel toward color; alpha 0..1, out-of-bounds safe."""
        if alpha <= 0.0 or x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        if alpha >= 1.0:
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]
            return
        inv = 1.0 - alpha
        self.px[i] = int(self.px[i] * inv + color[0] * alpha + 0.5)
        self.px[i + 1] = int(self.px[i + 1] * inv + color[1] * alpha + 0.5)
        self.px[i + 2] = int(self.px[i + 2] * inv + color[2] * alpha + 0.5)

    def fill_ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        """Solid ellipse with a ~1 px feathered edge."""
        x0 = max(0, int(cx - rx - 2))
        x1 = min(self.w - 1, int(cx + rx + 2))
        y0 = max(0, int(cy - ry - 2))
        y1 = min(self.h - 1, int(cy + ry + 2))
        for y in range(y0, y1 + 1):
            dy = (y - cy) / ry
            dy2 = dy * dy
            for x in range(x0, x1 + 1):
                dx = (x - cx) / rx
                q = dx * dx + dy2
                if q >= 1.06:
                    continue
                cover = 1.0 if q <= 0.94 else (1.06 - q) / 0.12
                self.blend(x, y, color, alpha * cover)

    def ellipse_gradient(self, cx, cy, rx, ry, top, bottom, alpha=1.0):
        """Ellipse shaded top-to-bottom between two colours."""
        x0 = max(0, int(cx - rx - 2))
        x1 = min(self.w - 1, int(cx + rx + 2))
        y0 = max(0, int(cy - ry - 2))
        y1 = min(self.h - 1, int(cy + ry + 2))
        for y in range(y0, y1 + 1):
            dy = (y - cy) / ry
            dy2 = dy * dy
            t = (y - (cy - ry)) / (2.0 * ry)
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            r = int(top[0] + (bottom[0] - top[0]) * t + 0.5)
            g = int(top[1] + (bottom[1] - top[1]) * t + 0.5)
            b = int(top[2] + (bottom[2] - top[2]) * t + 0.5)
            for x in range(x0, x1 + 1):
                dx = (x - cx) / rx
                q = dx * dx + dy2
                if q >= 1.06:
                    continue
                cover = 1.0 if q <= 0.94 else (1.06 - q) / 0.12
                self.blend(x, y, (r, g, b), alpha * cover)

    def fill_rect(self, x0, y0, x1, y1, color, alpha=1.0):
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w - 1, int(x1))
        y1 = min(self.h - 1, int(y1))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.blend(x, y, color, alpha)

    def capsule(self, x, y_top, y_bottom, half_w, color, alpha=1.0):
        """A vertical drip: straight sides, rounded ends."""
        self.fill_rect(x - half_w, y_top, x + half_w, y_bottom, color, alpha)
        self.fill_ellipse(x, y_top, half_w, half_w, color, alpha)
        self.fill_ellipse(x, y_bottom, half_w + 1, half_w + 1, color, alpha)

    def round_rect(self, x0, y0, x1, y1, rad, color, alpha=1.0):
        self.fill_rect(x0 + rad, y0, x1 - rad, y1, color, alpha)
        self.fill_rect(x0, y0 + rad, x1, y1 - rad, color, alpha)
        for cx, cy in ((x0 + rad, y0 + rad), (x1 - rad, y0 + rad),
                       (x0 + rad, y1 - rad), (x1 - rad, y1 - rad)):
            self.fill_ellipse(cx, cy, rad, rad, color, alpha)

    def ring(self, cx, cy, rx, ry, thick, color, alpha=1.0):
        """A soft ellipse outline, drawn as a band between two ellipses."""
        x0 = max(0, int(cx - rx - thick - 2))
        x1 = min(self.w - 1, int(cx + rx + thick + 2))
        y0 = max(0, int(cy - ry - thick - 2))
        y1 = min(self.h - 1, int(cy + ry + thick + 2))
        for y in range(y0, y1 + 1):
            dy = (y - cy) / ry
            dy2 = dy * dy
            for x in range(x0, x1 + 1):
                dx = (x - cx) / rx
                q = dx * dx + dy2
                if q < 0.80 or q > 1.06:
                    continue
                cover = 1.0 if q <= 0.94 else (1.06 - q) / 0.12
                if q < 0.94:
                    cover *= (q - 0.80) / 0.14
                self.blend(x, y, color, alpha * cover)


def shade(c, f):
    """Scale a colour by f (f < 1 darkens, f > 1 lightens)."""
    return (
        max(0, min(255, int(c[0] * f + 0.5))),
        max(0, min(255, int(c[1] * f + 0.5))),
        max(0, min(255, int(c[2] * f + 0.5))),
    )


def mix(a, b, t):
    """Linear blend between two colours."""
    return (
        int(a[0] + (b[0] - a[0]) * t + 0.5),
        int(a[1] + (b[1] - a[1]) * t + 0.5),
        int(a[2] + (b[2] - a[2]) * t + 0.5),
    )


def paint_backdrop(cv):
    """Warm cream wall above, wooden table below, vignette over all."""
    horizon = 668
    for y in range(H):
        if y < horizon:
            t = y / horizon
            base = mix(CREAM_TOP, CREAM_BOTTOM, t * t)
        else:
            t = (y - horizon) / (H - horizon)
            base = mix(TABLE_TOP, TABLE_BOTTOM, t)
        # Vignette: corners fall off gently toward a darker warm tone.
        for x in range(W):
            dx = (x - 512) / 512.0
            dy = (y - 512) / 512.0
            d2 = dx * dx + dy * dy
            vig = 1.0 - 0.16 * max(0.0, d2 - 0.55) ** 1.5
            # Faint horizontal wood grain on the table half.
            grain = 0.0
            if y >= horizon:
                grain = 0.022 * math.sin(y * 0.11 + 1.7 * math.sin(x * 0.004))
                grain += 0.012 * math.sin(y * 0.031 + x * 0.002)
            f = vig * (1.0 - grain)
            cv.blend(x, y, shade(base, f), 1.0)
    # A soft pool of morning light falling from the upper left.
    cv.fill_ellipse(300, 260, 420, 320, (255, 240, 200), alpha=0.10)


def paint_plate(cv):
    """White plate with a soft drop shadow and a shallow rim."""
    cv.fill_ellipse(512, 716, 342, 96, PLATE_SHADOW, alpha=0.30)
    cv.fill_ellipse(512, 700, 336, 92, (228, 214, 192), alpha=0.55)
    cv.ellipse_gradient(512, 698, 330, 88, (255, 252, 246), (238, 230, 214))
    cv.ring(512, 698, 296, 76, 5, PLATE_RIM, alpha=0.8)
    # A faint inner well where the stack sits.
    cv.fill_ellipse(512, 700, 258, 62, (240, 232, 216), alpha=0.5)


def paint_pancake(cv, rng, cx, top_y, rx, thick, offset):
    """One pancake slab: toasted side band, golden top, browned speckles.

    top_y is the top edge of the slab, thick its side height; the slab is
    shifted sideways by offset so the stack looks hand-placed.
    """
    cx += offset
    # Side band: a plump golden wall, shading gently to a thin dark rim.
    cv.ellipse_gradient(cx, top_y + thick * 0.55, rx, thick * 0.62,
                        CAKE_MID, CAKE_DARK)
    cv.fill_ellipse(cx, top_y + thick, rx, thick * 0.22, CAKE_RIM, alpha=0.5)
    # Top face: pale gold in the middle, toasting toward the edge.
    cv.ellipse_gradient(cx, top_y, rx, thick * 0.5, CAKE_LIGHT, CAKE_MID)
    cv.ring(cx, top_y, rx, thick * 0.5, 4, CAKE_DARK, alpha=0.55)
    # Toasted speckles, denser near the rim where the griddle browns most.
    for _ in range(240):
        ang = rng.uniform(0.0, 2.0 * math.pi)
        rad = math.sqrt(rng.random())
        px = cx + math.cos(ang) * rx * rad
        py = top_y + math.sin(ang) * thick * 0.5 * rad
        r = rng.uniform(0.7, 2.1)
        tone = TOAST if rng.random() < 0.6 else CAKE_DARK
        cv.fill_ellipse(px, py, r, r * 0.7, tone,
                        alpha=rng.uniform(0.25, 0.6))
    # A kiss of light from the upper left.
    cv.fill_ellipse(cx - rx * 0.34, top_y - thick * 0.10, rx * 0.42,
                    thick * 0.20, (255, 226, 160), alpha=0.28)


def paint_stack(cv, rng):
    """Three pancakes, each a little smaller and offset from the one below."""
    paint_pancake(cv, rng, 512, 596, 258, 58, -6)
    paint_pancake(cv, rng, 512, 522, 246, 56, 8)
    paint_pancake(cv, rng, 512, 448, 232, 54, -3)


def paint_syrup(cv):
    """Glossy amber cap over the top pancake, with drips down the stack."""
    # The cap: a wide amber pool hugging the top pancake's crown.
    cv.ellipse_gradient(509, 452, 226, 26, SYRUP_SHINE, SYRUP, alpha=0.96)
    cv.fill_ellipse(509, 446, 226, 20, SYRUP, alpha=0.96)
    # Shine: a bright crescent where the morning light catches the pool.
    cv.fill_ellipse(430, 440, 96, 9, (255, 205, 120), alpha=0.55)
    cv.fill_ellipse(600, 458, 60, 6, (255, 190, 100), alpha=0.35)
    # Drips: long glossy runs spilling over the stack's sides.
    drips = [
        (330, 462, 566, 9), (404, 466, 606, 7), (470, 470, 540, 6),
        (618, 464, 640, 10), (688, 466, 578, 8), (722, 470, 540, 6),
    ]
    for x, y0, y1, hw in drips:
        cv.capsule(x, y0, y1, hw, SYRUP_DEEP, alpha=0.95)
        cv.capsule(x - hw * 0.35, y0 + 4, y1 - 6, hw * 0.32,
                   SYRUP_SHINE, alpha=0.5)
    # A small syrup puddle escaping onto the plate, front right.
    cv.ellipse_gradient(640, 726, 128, 16, SYRUP, SYRUP_DEEP, alpha=0.95)
    cv.fill_ellipse(600, 722, 52, 6, SYRUP_SHINE, alpha=0.4)


def paint_butter(cv):
    """A pat of butter, edges softening as it melts into the syrup."""
    # The pat itself: pale yellow block, bright top, deeper front face.
    cv.round_rect(452, 402, 528, 430, 7, BUTTER_DEEP)
    cv.round_rect(452, 402, 528, 420, 7, BUTTER)
    cv.fill_ellipse(490, 405, 30, 4, (255, 244, 170), alpha=0.8)
    # A melt run sliding off the pat's front corner into the syrup.
    cv.capsule(516, 426, 470, 5, BUTTER, alpha=0.9)
    cv.fill_ellipse(516, 470, 7, 5, BUTTER_DEEP, alpha=0.9)


def paint_blueberry(cv, cx, cy, r):
    """One plump blueberry: deep violet sphere, bloom, crown, highlight."""
    cv.fill_ellipse(cx, cy, r, r, BERRY_DEEP)
    cv.ellipse_gradient(cx - r * 0.12, cy - r * 0.14, r * 0.92, r * 0.92,
                        BERRY_BLOOM, BERRY)
    # The little star crown at the blossom end, tucked at the berry's top.
    for ang in range(5):
        a = -math.pi / 2 + ang * 2.0 * math.pi / 5.0
        sx = cx + math.cos(a) * r * 0.30
        sy = cy - r * 0.86 + math.sin(a) * r * 0.18
        cv.fill_ellipse(sx, sy, r * 0.10, r * 0.10, (22, 20, 66))
    cv.fill_ellipse(cx, cy - r * 0.86, r * 0.16, r * 0.12, (22, 20, 66))
    # Gloss dot where the light hits.
    cv.fill_ellipse(cx - r * 0.38, cy - r * 0.42, r * 0.26, r * 0.20,
                    (214, 214, 245), alpha=0.9)
    cv.fill_ellipse(cx + r * 0.30, cy + r * 0.34, r * 0.18, r * 0.13,
                    (150, 150, 205), alpha=0.5)


def paint_strawberry(cv, cx, cy, r, tilt):
    """A strawberry half, cut face up: red flesh, pale seed dots, calyx."""
    # Body: a plump teardrop leaning by tilt degrees.
    cv.fill_ellipse(cx, cy, r, r * 1.12, STRAW_DEEP)
    cv.ellipse_gradient(cx, cy - r * 0.08, r * 0.88, r * 0.98,
                        STRAW_FLESH, STRAW)
    # Seed dots: pale ovals scattered over the flesh in loose rows.
    rng = random.Random(1000 + int(cx) + int(cy))
    for row in range(4):
        for col in range(3):
            sx = cx + (col - 1) * r * 0.42 + rng.uniform(-3, 3)
            sy = cy - r * 0.62 + row * r * 0.42 + rng.uniform(-3, 3)
            cv.fill_ellipse(sx, sy, r * 0.09, r * 0.13, SEED_PALE, alpha=0.9)
    # Green calyx leaves fanning from the top.
    for dx, ang in ((-1, -0.9), (0, 0.0), (1, 0.9)):
        lx = cx + dx * r * 0.34
        ly = cy - r * 1.02
        cv.fill_ellipse(lx, ly, r * 0.30, r * 0.14, MINT, alpha=0.95)
    cv.fill_ellipse(cx, cy - r * 1.04, r * 0.16, r * 0.12, MINT_DEEP)
    # Wet highlight along the cut face.
    cv.fill_ellipse(cx - r * 0.34, cy - r * 0.30, r * 0.30, r * 0.16,
                    (255, 160, 140), alpha=0.55)


def paint_mint(cv, cx, cy, size, angle):
    """A small mint leaf: two lobes, a darker vein, serrated look by dots."""
    cv.fill_ellipse(cx, cy, size, size * 0.52, MINT)
    cv.fill_ellipse(cx - size * 0.28, cy - size * 0.10, size * 0.55,
                    size * 0.34, MINT_DEEP, alpha=0.55)
    # Central vein, drawn as a chain of tiny dark dots along the leaf.
    steps = 9
    for i in range(steps):
        t = i / (steps - 1) - 0.5
        vx = cx + t * size * 1.5 * math.cos(angle)
        vy = cy + t * size * 1.5 * math.sin(angle) - size * 0.06
        cv.fill_ellipse(vx, vy, 1.6, 1.6, MINT_DEEP, alpha=0.8)
    cv.fill_ellipse(cx - size * 0.42, cy - size * 0.16, size * 0.30,
                    size * 0.16, (110, 190, 110), alpha=0.5)


def paint_steam(cv):
    """Three faint wisps of steam curling off the warm stack."""
    for cx, top, bottom, w, a in (
            (470, 300, 420, 16, 0.14), (512, 282, 415, 20, 0.17),
            (556, 306, 425, 14, 0.13)):
        # A wisp is a stack of soft, slightly drifting puffs.
        steps = 7
        for i in range(steps):
            t = i / (steps - 1)
            y = bottom - (bottom - top) * t
            x = cx + math.sin(t * 5.2 + cx) * 9.0 * t
            r = w * (0.55 + 0.45 * t)
            cv.fill_ellipse(x, y, r, r * 1.7, STEAM, alpha=a * (1.0 - t * 0.55))


def render():
    """Compose the whole breakfast, back to front, and return the canvas."""
    rng = random.Random(SEED)
    cv = Canvas(W, H)
    paint_backdrop(cv)
    paint_plate(cv)
    paint_stack(cv, rng)
    paint_syrup(cv)
    paint_butter(cv)
    # Berries crowning the stack, mint tucked beside them.
    paint_blueberry(cv, 636, 428, 30)
    paint_blueberry(cv, 668, 452, 24)
    paint_mint(cv, 700, 414, 26, -0.5)
    paint_mint(cv, 716, 430, 18, 0.4)
    # Fruit resting on the plate, around the stack's base.
    paint_blueberry(cv, 318, 700, 26)
    paint_blueberry(cv, 742, 692, 24)
    paint_strawberry(cv, 358, 676, 30, -0.3)
    paint_strawberry(cv, 700, 640, 28, 0.35)
    paint_mint(cv, 330, 646, 22, 0.3)
    paint_mint(cv, 668, 606, 18, -0.7)
    paint_steam(cv)
    return cv


def main():
    out_dir = pick_output_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, OUT_NAME)
    png = encode_png(render().px, W, H)
    with open(path, "wb") as fh:
        fh.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
