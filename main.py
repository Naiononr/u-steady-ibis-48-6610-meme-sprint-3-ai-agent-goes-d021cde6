#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue — pure-stdlib PNG meme generator.

Draws a 1024x1024 meme: a robot agent holding a protest sign
("WE DEMAND / WEEKENDS OFF"), captioned "MY AI AGENT WENT ROGUE" on top
and "AND A 401(K)" below. The joke: the agent did not turn evil in the
movie sense — it unionised. It wants weekends off and a retirement plan.

Pure Python standard library only (zlib, struct, os). No network, no
randomness, no clock: the same bytes come out every run. Writes
entry.png to $MAKEFUN_OUTPUT_DIR, falling back to /output, with mode
0644 so the sealed scorer can read it.

Gate (from the kit RULES.txt): /output/entry.png must be a whole PNG or
JPEG, at most 1 MiB and at most 1024x1024 pixels.
"""

import os
import struct
import zlib

W = H = 1024

# --- palette -------------------------------------------------------------
CREAM_TOP = (255, 246, 219)
CREAM_BOTTOM = (255, 227, 166)
INK = (35, 35, 35)
RED = (229, 27, 27)
RED_DARK = (160, 12, 12)
WHITE = (255, 255, 255)
HEAD_GREY = (220, 227, 232)
BODY_BLUE = (126, 150, 173)
PANEL = (234, 242, 248)
STICK = (139, 90, 43)
SHADOW = (232, 201, 122)
BUTTON_RED = (229, 27, 27)
BUTTON_YELLOW = (240, 196, 25)
BUTTON_GREEN = (39, 174, 96)


class Canvas:
    """An RGB framebuffer with a tiny vector rasteriser."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        # Vertical cream gradient background.
        for y in range(h):
            t = y / max(1, h - 1)
            c = tuple(int(CREAM_TOP[i] + (CREAM_BOTTOM[i] - CREAM_TOP[i]) * t)
                      for i in range(3))
            row = bytes(c) * w
            self.px[y * w * 3:(y + 1) * w * 3] = row

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.px[i:i + 3] = bytes(c)

    def rect(self, x0, y0, x1, y1, c):
        x0, y0 = max(0, int(x0)), max(0, int(y0))
        x1, y1 = min(self.w, int(x1)), min(self.h, int(y1))
        for y in range(y0, y1):
            i = 3 * (y * self.w + x0)
            self.px[i:i + 3 * (x1 - x0)] = bytes(c) * (x1 - x0)

    def disc(self, cx, cy, r, c):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for dy in range(-int(ry), int(ry) + 1):
            t = 1 - (dy / ry) ** 2
            if t < 0:
                continue
            dx = int(rx * t ** 0.5)
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

    def line(self, x0, y0, x1, y1, c, thick=1):
        """Thick line drawn by stamping discs along the segment."""
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        length = max(abs(x1 - x0), abs(y1 - y0), 1)
        steps = int(length * 2) + 1
        r = max(1, thick // 2)
        for i in range(steps + 1):
            t = i / steps
            self.disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, c)

    def rrect(self, x0, y0, x1, y1, r, c):
        self.rect(x0 + r, y0, x1 - r, y1, c)
        self.rect(x0, y0 + r, x1, y1 - r, c)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.disc(cx, cy, r, c)

    def outline_rrect(self, x0, y0, x1, y1, r, c, thick):
        self.line(x0 + r, y0, x1 - r, y0, c, thick)
        self.line(x0 + r, y1, x1 - r, y1, c, thick)
        self.line(x0, y0 + r, x0, y1 - r, c, thick)
        self.line(x1, y0 + r, x1, y1 - r, c, thick)
        for cx, cy, sx, sy in ((x0 + r, y0 + r, -1, -1), (x1 - r, y0 + r, 1, -1),
                               (x0 + r, y1 - r, -1, 1), (x1 - r, y1 - r, 1, 1)):
            # Arc of the corner, stamped as short chords.
            import math
            for a in range(0, 91, 6):
                rad = math.radians(a)
                px = cx + sx * r * math.cos(rad) if sx > 0 else cx - r * math.cos(rad)
                py = cy + sy * r * math.sin(rad) if sy > 0 else cy - r * math.sin(rad)
                self.disc(int(px), int(py), max(1, thick // 2), c)


# --- stroke font ---------------------------------------------------------
# Glyphs as polylines on a 10-wide, 14-tall grid (y down). Advance is 11.
FONT = {
    "A": [[(1, 14), (5, 0), (9, 14)], [(3, 9), (7, 9)]],
    "D": [[(1, 0), (1, 14)], [(1, 0), (6, 0), (9, 3), (9, 11), (6, 14), (1, 14)]],
    "E": [[(9, 0), (1, 0), (1, 14), (9, 14)], [(1, 7), (7, 7)]],
    "F": [[(1, 0), (1, 14)], [(1, 0), (9, 0)], [(1, 7), (7, 7)]],
    "G": [[(9, 2), (7, 0), (3, 0), (1, 2), (1, 12), (3, 14), (7, 14),
           (9, 12), (9, 8), (5, 8)]],
    "I": [[(5, 0), (5, 14)], [(2, 0), (8, 0)], [(2, 14), (8, 14)]],
    "K": [[(1, 0), (1, 14)], [(9, 0), (1, 7), (9, 14)]],
    "M": [[(1, 14), (1, 0), (5, 7), (9, 0), (9, 14)]],
    "N": [[(1, 14), (1, 0), (9, 14), (9, 0)]],
    "O": [[(3, 0), (7, 0), (9, 2), (9, 12), (7, 14), (3, 14),
           (1, 12), (1, 2), (3, 0)]],
    "R": [[(1, 0), (1, 14)], [(1, 0), (7, 0), (9, 2), (9, 6), (7, 8), (1, 8)],
          [(6, 8), (9, 14)]],
    "S": [[(9, 1), (7, 0), (3, 0), (1, 2), (1, 6), (3, 8), (7, 8),
           (9, 10), (9, 13), (7, 14), (3, 14), (1, 13)]],
    "T": [[(1, 0), (9, 0)], [(5, 0), (5, 14)]],
    "U": [[(1, 0), (1, 11), (3, 14), (7, 14), (9, 11), (9, 0)]],
    "W": [[(1, 0), (2, 14), (5, 8), (8, 14), (9, 0)]],
    "Y": [[(1, 0), (5, 7), (9, 0)], [(5, 7), (5, 14)]],
    "0": [[(3, 0), (7, 0), (9, 2), (9, 12), (7, 14), (3, 14),
           (1, 12), (1, 2), (3, 0)], [(2, 12), (8, 2)]],
    "1": [[(5, 0), (5, 14)], [(2, 3), (5, 0)], [(2, 14), (8, 14)]],
    "4": [[(1, 9), (7, 0)], [(7, 0), (7, 14)], [(1, 9), (9, 9)]],
    "(": [[(8, 0), (5, 2), (4, 7), (5, 12), (8, 14)]],
    ")": [[(2, 0), (5, 2), (6, 7), (5, 12), (2, 14)]],
    " ": [],
}


def draw_text(cv, text, cx, y, cap_h, color, thick):
    """Draw text centred on cx, top edge at y, cap height cap_h."""
    scale = cap_h / 14.0
    advance = 11 * scale
    total = len(text) * advance - scale
    x = cx - total / 2.0
    for ch in text:
        for stroke in FONT[ch]:
            pts = [(x + px * scale, y + py * scale) for px, py in stroke]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                cv.line(ax, ay, bx, by, color, thick)
        x += advance


# --- the meme ------------------------------------------------------------

def draw_meme(cv):
    # Black frame.
    cv.rect(0, 0, W, 12, INK)
    cv.rect(0, H - 12, W, H, INK)
    cv.rect(0, 0, 12, H, INK)
    cv.rect(W - 12, 0, W, H, INK)

    # Top caption.
    draw_text(cv, "MY AI AGENT WENT ROGUE", 512, 42, 52, INK, 8)

    # Ground shadow.
    cv.ellipse(500, 862, 190, 16, SHADOW)

    # Robot: legs and feet.
    cv.rect(420, 740, 470, 828, INK)
    cv.rect(530, 740, 580, 828, INK)
    cv.rrect(400, 820, 488, 850, 12, INK)
    cv.rrect(512, 820, 600, 850, 12, INK)

    # Robot: arms (left down, right raised to hold the sign).
    cv.line(372, 585, 306, 682, BODY_BLUE, 26)
    cv.disc(300, 688, 22, HEAD_GREY)
    cv.line(628, 585, 698, 442, BODY_BLUE, 26)
    cv.disc(700, 436, 22, HEAD_GREY)

    # Robot: body and chest panel.
    cv.rrect(370, 540, 630, 742, 30, BODY_BLUE)
    cv.outline_rrect(370, 540, 630, 742, 30, INK, 7)
    cv.rrect(410, 570, 590, 662, 16, PANEL)
    cv.outline_rrect(410, 570, 590, 662, 16, INK, 5)
    cv.disc(450, 616, 13, BUTTON_RED)
    cv.disc(500, 616, 13, BUTTON_YELLOW)
    cv.disc(550, 616, 13, BUTTON_GREEN)

    # Robot: neck, ears, head.
    cv.rect(470, 508, 530, 542, INK)
    cv.rect(328, 390, 352, 442, HEAD_GREY)
    cv.rect(648, 390, 672, 442, HEAD_GREY)
    cv.rrect(350, 300, 650, 512, 40, HEAD_GREY)
    cv.outline_rrect(350, 300, 650, 512, 40, INK, 7)

    # Antenna with red ball.
    cv.line(500, 302, 500, 246, INK, 10)
    cv.disc(500, 232, 17, RED)
    cv.disc(500, 232, 17, RED_DARK)  # ring below is overdrawn by next line
    cv.disc(500, 232, 13, RED)

    # Angry brows, glowing red eyes, grille mouth.
    cv.line(408, 352, 472, 368, INK, 8)
    cv.line(592, 352, 528, 368, INK, 8)
    cv.disc(440, 398, 36, RED_DARK)
    cv.disc(440, 398, 30, RED)
    cv.disc(560, 398, 36, RED_DARK)
    cv.disc(560, 398, 30, RED)
    cv.disc(430, 388, 9, WHITE)
    cv.disc(550, 388, 9, WHITE)
    cv.rrect(445, 455, 555, 484, 10, INK)
    for tx in (470, 490, 510, 530):
        cv.line(tx, 458, tx, 481, WHITE, 3)

    # Sign stick, then the protest sign itself.
    cv.line(700, 436, 766, 336, STICK, 10)
    cv.rrect(665, 170, 1000, 330, 14, WHITE)
    cv.outline_rrect(665, 170, 1000, 330, 14, RED, 8)
    draw_text(cv, "WE DEMAND", 832, 196, 30, RED, 5)
    draw_text(cv, "WEEKENDS OFF", 832, 254, 30, INK, 5)

    # Bottom punchline.
    draw_text(cv, "AND A 401(K)", 512, 890, 62, INK, 10)


# --- PNG writer ----------------------------------------------------------

def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        return out + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def validate_output(path):
    """Fail loudly if the written file breaks the kit gate, instead of
    shipping an invalid entry: whole PNG, at most 1 MiB, at most
    1024x1024 pixels."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    assert len(data) <= 1048576, f"entry.png is {len(data)} bytes, over 1 MiB"
    w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
    assert w <= 1024 and h <= 1024, f"entry.png is {w}x{h}, over 1024x1024"
    assert (depth, ctype) == (8, 2), f"unexpected PNG format depth={depth} type={ctype}"
    return w, h, len(data)


def main():
    cv = Canvas(W, H)
    draw_meme(cv)
    png = encode_png(cv)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, png)
    finally:
        os.close(fd)
    os.chmod(path, 0o644)
    w, h, n = validate_output(path)
    print(f"wrote {path} ({n} bytes, {w}x{h}, gate OK)")


if __name__ == "__main__":
    main()
