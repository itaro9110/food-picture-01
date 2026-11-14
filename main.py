# food-picture-01: "The Golden Stack"
# Golden pancakes with maple syrup, melting butter, berries, on a white plate.
# Procedural PNG, Python 3.13 stdlib only. Deterministic: fixed seed, no network.
import math, os, random, struct, zlib
from binascii import crc32

W = H = 1024

def _chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", crc32(typ + data) & 0xFFFFFFFF)

def write_png(path, buf):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

def lerp(a, b, t):
    return a + (b - a) * t

def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))

class Canvas:
    def __init__(self):
        self.buf = bytearray(W * H * 3)
        self.rng = random.Random(20261114)

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def blend(self, x, y, c, a):
        if 0 <= x < W and 0 <= y < H and a > 0:
            if a >= 1:
                self.px(x, y, c)
                return
            i = (y * W + x) * 3
            b = self.buf
            b[i] = int(b[i] * (1 - a) + c[0] * a)
            b[i + 1] = int(b[i + 1] * (1 - a) + c[1] * a)
            b[i + 2] = int(b[i + 2] * (1 - a) + c[2] * a)

    def row(self, y, x0, x1, c):
        if y < 0 or y >= H:
            return
        x0 = max(0, x0)
        x1 = min(W - 1, x1)
        if x1 < x0:
            return
        i0 = (y * W + x0) * 3
        self.buf[i0:(y * W + x1 + 1) * 3] = bytes(c) * (x1 - x0 + 1)

    def vgrad(self, y0, y1, c_top, c_bot):
        for y in range(max(0, y0), min(H, y1)):
            t = (y - y0) / max(1, y1 - y0)
            self.row(y, 0, W - 1, mix(c_top, c_bot, t))

    def ellipse(self, cx, cy, rx, ry, c_top, c_bot=None):
        # Filled ellipse, vertical gradient from c_top (top) to c_bot (bottom).
        if c_bot is None:
            c_bot = c_top
        for y in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            hw = rx * math.sqrt(max(0.0, 1 - dy * dy))
            t = (y - (cy - ry)) / max(1.0, 2 * ry)
            self.row(y, int(cx - hw), int(cx + hw), mix(c_top, c_bot, t))

    def soft_ellipse(self, cx, cy, rx, ry, c, a_max, steps=7):
        # Layered ellipses: soft glow / shadow with alpha falloff.
        for s in range(steps, 0, -1):
            f = s / steps
            a = a_max * (1 - f * f) * 0.35
            rxs, rys = rx * (0.55 + 0.45 * f), ry * (0.55 + 0.45 * f)
            for y in range(max(0, int(cy - rys)), min(H, int(cy + rys) + 1)):
                dy = (y - cy) / rys
                if abs(dy) > 1:
                    continue
                hw = rxs * math.sqrt(max(0.0, 1 - dy * dy))
                for x in range(int(cx - hw), int(cx + hw) + 1):
                    self.blend(x, y, c, a)

    def disc(self, cx, cy, r, c_top, c_bot=None):
        self.ellipse(cx, cy, r, r, c_top, c_bot)

    def thick_line(self, x0, y0, x1, y1, w, c, a=1.0):
        dx, dy = x1 - x0, y1 - y0
        n = int(max(abs(dx), abs(dy)) * 2) + 2
        rr = w / 2
        for i in range(n + 1):
            t = i / n
            x = x0 + dx * t
            y = y0 + dy * t
            for yy in range(int(y - rr), int(y + rr) + 1):
                for xx in range(int(x - rr), int(x + rr) + 1):
                    if (xx - x) ** 2 + (yy - y) ** 2 <= rr * rr:
                        self.blend(xx, yy, c, a)

# ---- palette (warm, appetising) ----
CREAM_TOP = (250, 238, 205)
CREAM_BOT = (238, 205, 150)
TABLE_TOP = (196, 138, 82)
TABLE_BOT = (150, 98, 52)
PLATE = (253, 248, 238)
PLATE_RIM = (232, 220, 196)
GOLD_L = (247, 203, 105)
GOLD = (233, 168, 62)
GOLD_D = (186, 118, 34)
BROWN = (146, 84, 22)
SYRUP = (176, 88, 8)
SYRUP_L = (232, 132, 20)
SYRUP_HI = (255, 205, 110)
BUTTER = (255, 233, 138)
BUTTER_D = (240, 200, 80)
BLUEB = (46, 58, 140)
STRAW = (210, 31, 43)
LEAF = (62, 142, 74)

def speckle(cv, cx, cy, rx, ry, n, colors, a=0.5):
    # Tiny dots inside an ellipse: toasted / powdered texture.
    for _ in range(n):
        ang = cv.rng.uniform(0, 6.2832)
        rr = math.sqrt(cv.rng.random())
        x = int(cx + math.cos(ang) * rx * rr)
        y = int(cy + math.sin(ang) * ry * rr)
        cv.blend(x, y, cv.rng.choice(colors), a * cv.rng.uniform(0.4, 1.0))

def background(cv):
    # Warm wall above, wooden table below, soft glow behind the hero.
    cv.vgrad(0, 660, CREAM_TOP, CREAM_BOT)
    cv.vgrad(660, H, TABLE_TOP, TABLE_BOT)
    # Table edge line, soft.
    for x in range(W):
        cv.blend(x, 660, (120, 76, 40), 0.25)
        cv.blend(x, 661, (255, 225, 170), 0.18)
    # No radial glow: layered ellipses ring visibly against the smooth gradient.
    # The vertical gradient alone carries the warmth.
    # Faint table grain.
    for _ in range(26):
        y = cv.rng.randint(680, 1010)
        x0 = cv.rng.randint(0, 500)
        ln = cv.rng.randint(120, 420)
        cv.thick_line(x0, y, x0 + ln, y + cv.rng.randint(-2, 2), 1,
                      (120, 76, 40), 0.10)

def plate(cv):
    # Soft contact shadow, then the white plate with a rim.
    cv.soft_ellipse(512, 762, 400, 52, (60, 35, 12), 0.34, steps=8)
    cv.soft_ellipse(500, 748, 360, 44, (60, 35, 12), 0.20, steps=6)
    cv.ellipse(512, 700, 392, 148, PLATE, (240, 228, 204))
    cv.ellipse(512, 696, 392, 148, PLATE, PLATE)
    # Rim ring: darker outer band then bright inner well.
    cv.ellipse(512, 698, 330, 118, PLATE_RIM, (246, 236, 214))
    cv.ellipse(512, 698, 312, 108, (252, 246, 232), (244, 232, 208))
    # Top-left light kiss on the rim.
    cv.soft_ellipse(330, 620, 150, 34, (255, 255, 255), 0.35, steps=4)

def wavy_ellipse(cv, cx, cy, rx, ry, c_top, c_bot, ph):
    # Ellipse whose edge wobbles like a real pancake.
    for y in range(max(0, int(cy - ry)), min(H, int(cy + ry) + 1)):
        dy = (y - cy) / ry
        if abs(dy) > 1:
            continue
        hw = rx * math.sqrt(max(0.0, 1 - dy * dy))
        wob = 1 + 0.022 * math.sin(y * 0.085 + ph) + 0.013 * math.sin(y * 0.21 + ph * 2)
        hw *= wob
        t = (y - (cy - ry)) / max(1.0, 2 * ry)
        cv.row(y, int(cx - hw), int(cx + hw), mix(c_top, c_bot, t))

def pancake(cv, cx, cy, rx, ph):
    # Side wall (darker, toasted) then golden top.
    wavy_ellipse(cv, cx, cy + 16, rx, 66, GOLD_D, BROWN, ph)
    wavy_ellipse(cv, cx, cy, rx, 68, GOLD_L, GOLD, ph)
    # Toasted centre: warm radial glow + brown speckles.
    cv.soft_ellipse(cx - 30, cy - 8, rx * 0.62, 34, (255, 224, 150), 0.30, steps=4)
    speckle(cv, cx, cy, rx * 0.9, 52, 520,
            [(190, 120, 40), (160, 95, 25), (220, 155, 60), (140, 82, 20)], 0.65)
    # Toasted rim: darker speckles concentrated near the edge.
    for _ in range(240):
        ang = cv.rng.uniform(0, 6.2832)
        rr = cv.rng.uniform(0.78, 0.98)
        x = int(cx + math.cos(ang) * rx * rr)
        y = int(cy + math.sin(ang) * 52 * rr)
        cv.blend(x, y, cv.rng.choice([(170, 100, 30), (140, 80, 22),
                                      (200, 135, 50)]), 0.6)
    # Light kiss top-left.
    cv.soft_ellipse(cx - 130, cy - 26, 120, 22, (255, 240, 190), 0.35, steps=4)

def stack(cv):
    pancake(cv, 512, 648, 302, 0.0)
    pancake(cv, 506, 566, 292, 1.7)
    pancake(cv, 518, 486, 282, 3.4)

def drip(cv, x, y0, y1, w):
    # Viscous drip: tapers slightly, bulbous tip, bright left edge.
    n = 26
    for i in range(n + 1):
        t = i / n
        y = y0 + (y1 - y0) * t
        r = w / 2 * (1 - 0.22 * t) + (3.5 if t > 0.92 else 0)
        cv.disc(int(x), int(y), max(2, int(r)), SYRUP, (150, 70, 5))
    cv.thick_line(x - w // 3, y0 + 6, x - w // 3, y1 - 8, 4, SYRUP_HI, 0.65)

def syrup(cv):
    # Glossy cap poured over the top pancake.
    cv.ellipse(518, 472, 252, 52, SYRUP_L, SYRUP)
    cv.ellipse(518, 463, 236, 44, (240, 150, 40), SYRUP)
    cv.soft_ellipse(432, 442, 112, 14, SYRUP_HI, 0.55, steps=4)
    cv.soft_ellipse(600, 478, 80, 10, SYRUP_HI, 0.35, steps=3)
    # Drips running down the stack.
    for (x, y0, y1, w) in [(298, 498, 612, 26), (702, 494, 588, 22),
                           (622, 504, 662, 30), (418, 508, 642, 20),
                           (760, 500, 560, 18)]:
        drip(cv, x, y0, y1, w)
    # Pool on the plate at the base of the stack.
    cv.ellipse(566, 746, 182, 26, SYRUP_L, (170, 95, 15))
    cv.soft_ellipse(522, 737, 92, 10, SYRUP_HI, 0.45, steps=3)

def butter(cv):
    # A pat of butter, slightly tilted, melting on the warm syrup.
    cv.soft_ellipse(470, 442, 62, 14, (120, 60, 10), 0.25, steps=3)
    for y in range(404, 452):
        t = (y - 404) / 48
        inset = 0
        if y < 412:
            inset = (412 - y) * 2
        elif y > 444:
            inset = (y - 444) * 2
        x0 = int(428 + (y - 404) * 0.30) + inset
        x1 = int(516 + (y - 404) * 0.30) - inset
        cv.row(y, x0, x1, mix((255, 238, 155), (244, 196, 70), t))
    # Glossy top face + bright edge.
    for y in range(406, 420):
        x0 = int(430 + (y - 404) * 0.30)
        x1 = int(514 + (y - 404) * 0.30)
        cv.row(y, x0, x1, (255, 248, 205))
    cv.thick_line(438, 411, 504, 411, 3, (255, 252, 225), 0.85)
    # Melt drips running down the front.
    cv.thick_line(498, 448, 506, 494, 16, (250, 222, 110), 0.95)
    cv.thick_line(502, 452, 508, 490, 4, (255, 244, 170), 0.8)
    cv.disc(506, 496, 10, (250, 222, 110), (235, 195, 75))

def blueberry(cv, cx, cy, r):
    cv.disc(cx, cy, r, (92, 104, 190), (24, 30, 80))
    cv.soft_ellipse(cx - r // 3, cy - r // 3, r // 2, r // 3,
                    (190, 200, 250), 0.5, steps=3)
    cv.disc(cx, cy - r + 2, max(2, r // 5), (20, 24, 60), (20, 24, 60))

def strawberry(cv, cx, cy, r):
    # Plump berry: red body, pale seed dots, green cap.
    cv.disc(cx, cy, r, (235, 70, 70), (150, 12, 24))
    cv.soft_ellipse(cx - r // 3, cy - r // 3, r // 2, r // 3,
                    (255, 150, 140), 0.5, steps=3)
    speckle(cv, cx, cy, r * 0.8, r * 0.8, 26,
            [(255, 220, 190), (255, 200, 170)], 0.8)
    cv.ellipse(cx, cy - r + 4, r // 2, r // 4, (46, 120, 60), (30, 90, 45))

def mint(cv, cx, cy):
    cv.ellipse(cx, cy, 34, 14, LEAF, (30, 96, 44))
    cv.thick_line(cx - 30, cy, cx + 30, cy, 2, (24, 80, 38), 0.7)

def garnish(cv):
    blueberry(cv, 612, 442, 30)
    blueberry(cv, 652, 466, 24)
    blueberry(cv, 296, 724, 26)
    blueberry(cv, 742, 726, 24)
    strawberry(cv, 706, 636, 34)
    strawberry(cv, 330, 700, 26)
    mint(cv, 660, 420)
    mint(cv, 356, 668)
    # Powdered sugar dust on the top pancake.
    speckle(cv, 518, 470, 240, 40, 220, [(255, 255, 255)], 0.55)

def steam(cv):
    # Thin wavy columns rising from the hot stack.
    for (x0, amp, ph, top) in [(470, 16, 0.0, 250), (560, 20, 2.1, 210),
                               (520, 12, 4.0, 280)]:
        y = 420
        while y > top:
            t = (420 - y) / (420 - top)
            x = x0 + math.sin(y * 0.03 + ph) * amp * (0.4 + t)
            r = 14 + t * 18
            cv.soft_ellipse(int(x), y, r, r * 1.6, (255, 255, 255),
                            0.16 * (1 - t * 0.55), steps=4)
            y -= 26

def vignette(cv):
    for (cx, cy) in [(-40, -40), (1064, -40), (-40, 1064), (1064, 1064)]:
        cv.soft_ellipse(cx, cy, 420, 420, (90, 55, 20), 0.05, steps=10)

def output_dir():
    # The grader runs as an unprivileged user in a read-only container
    # where only /tmp is guaranteed writable: never default to a
    # relative directory (os.makedirs('out') would crash there).
    d = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if d:
        return d
    if os.path.isdir("/output") and os.access("/output", os.W_OK):
        return "/output"
    return "/tmp"

def main():
    cv = Canvas()
    background(cv)
    plate(cv)
    stack(cv)
    syrup(cv)
    butter(cv)
    garnish(cv)
    steam(cv)
    vignette(cv)
    out = output_dir()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    n = write_png(path, cv.buf)
    print("wrote %s (%d bytes, %dx%d)" % (path, n, W, H))

if __name__ == "__main__":
    main()

