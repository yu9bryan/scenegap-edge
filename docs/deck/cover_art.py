"""Cover art for the SceneGap deck: a film strip of real Commons frames checked against a shot list.

  python cover_art.py <frames_dir> <out.png>

frames_dir holds a.png … f.png (single frames from the Commons clips credited in the appendix).
The panel covers the right side of the title slide (5.6 × 7.5 in at 300 dpi).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC, OUT = sys.argv[1], sys.argv[2]
W, H = 1680, 2250
INK, INK2, VIOLET, VIOLET2, CYAN, AMBER, WHITE = (11, 11, 18), (21, 21, 31), (108, 76, 245), (139, 120, 255), (34, 211, 238), (245, 165, 36), (255, 255, 255)
FR, FB = "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"
MONO = "C:/Windows/Fonts/consola.ttf"


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (FB if bold else FR), size)


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


img = Image.new("RGB", (W, H), INK)
# soft violet glow, matching the violet title background on the left
glow = Image.new("RGB", (W, H), INK)
gd = ImageDraw.Draw(glow)
gd.ellipse((-700, 1300, 1100, 3100), fill=(60, 40, 150))
gd.ellipse((900, -600, 2300, 700), fill=(10, 70, 90))
img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(260)), 0.55)
d = ImageDraw.Draw(img, "RGBA")

# film strip: vertical, bleeding off top and bottom
SX0, SX1 = 300, 1500
d.rectangle((SX0, 0, SX1, H), fill=(6, 6, 10, 255))
FW, FH, GAP = SX1 - SX0 - 180, round((SX1 - SX0 - 180) * 9 / 16), 46
fx = SX0 + 90
frames = ["d", "b", "c", "a", "f"]
y0 = -330
tcs = ["00:02.0", "00:14.0", "00:38.0", "00:55.0", "00:06.0"]
boxes = []
for i, n in enumerate(frames):
    y = y0 + i * (FH + GAP)
    fr = cover(Image.open(os.path.join(SRC, n + ".png")).convert("RGB"), FW, FH)
    img.paste(fr, (fx, y))
    boxes.append((fx, y, fx + FW, y + FH))
    if i != 1:                                       # the checked frame carries the brackets instead
        d.text((fx + 18, y + FH - 52), tcs[i], font=font(30, mono=True), fill=(255, 255, 255, 230))
# sprocket holes
for y in range(-20, H, 74):
    for x in (SX0 + 28, SX1 - 62):
        d.rounded_rectangle((x, y, x + 34, y + 44), 7, fill=(40, 40, 52, 255))

# the frame being checked (latte pour): dim the others, bracket and scan line on this one
for i, b in enumerate(boxes):
    if i != 1:
        d.rectangle(b, fill=(11, 11, 18, 120))
x0, y0_, x1, y1 = boxes[1]
pad, L = 26, 90
for (cx, cy, dx, dy) in ((x0 + pad, y0_ + pad, 1, 1), (x1 - pad, y0_ + pad, -1, 1), (x0 + pad, y1 - pad, 1, -1), (x1 - pad, y1 - pad, -1, -1)):
    d.line((cx, cy, cx + dx * L, cy), fill=CYAN + (255,), width=10)
    d.line((cx, cy, cx, cy + dy * L), fill=CYAN + (255,), width=10)
sy = y0_ + int(FH * 0.62)
scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(scan)
sd.rectangle((x0, sy - 16, x1, sy + 16), fill=CYAN + (90,))
scan = scan.filter(ImageFilter.GaussianBlur(14))
img.paste(scan, (0, 0), scan)
d = ImageDraw.Draw(img, "RGBA")
d.line((x0, sy, x1, sy), fill=CYAN + (255,), width=4)
# label on the checked frame
lab = "SH-05 · candidate"
f = font(40, True)
tw = d.textlength(lab, font=f)
d.rounded_rectangle((x0 + pad, y0_ + pad + 110, x0 + pad + tw + 110, y0_ + pad + 186), 38, fill=INK + (225,), outline=CYAN + (255,), width=4)
d.ellipse((x0 + pad + 24, y0_ + pad + 130, x0 + pad + 60, y0_ + pad + 166), fill=CYAN)
d.line((x0 + pad + 33, y0_ + pad + 149, x0 + pad + 40, y0_ + pad + 157, x0 + pad + 52, y0_ + pad + 139), fill=INK, width=6)
d.text((x0 + pad + 76, y0_ + pad + 126), lab, font=f, fill=WHITE)

# shot list card, overlapping the strip
CX0, CY0, CX1 = 150, 1250, 1210
rows = [("SH-01", "Storefront, 3 s", "ok"), ("SH-05", "Pour into a cup, 3 s", "ok"), ("SH-08", "Two people, same frame", "ok"),
        ("SH-04", "Grinder, 2 s", "re"), ("SH-07", "Someone drinking, 2 s", "re")]
RH = 118
CY1 = CY0 + 150 + len(rows) * RH + 30
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle((CX0 + 10, CY0 + 30, CX1 + 10, CY1 + 40), 40, fill=(0, 0, 0, 200))
sh = sh.filter(ImageFilter.GaussianBlur(30))
img.paste(sh, (0, 0), sh)
d = ImageDraw.Draw(img, "RGBA")
d.rounded_rectangle((CX0, CY0, CX1, CY1), 40, fill=INK2 + (245,), outline=(60, 60, 80, 255), width=3)
d.text((CX0 + 56, CY0 + 50), "SHOT LIST", font=font(36, True), fill=VIOLET2)
d.text((CX1 - 56 - d.textlength("5 of 11", font=font(34)), CY0 + 52), "5 of 11", font=font(34), fill=(156, 163, 175))
for i, (sid, txt, st) in enumerate(rows):
    y = CY0 + 150 + i * RH
    d.line((CX0 + 56, y - 14, CX1 - 56, y - 14), fill=(45, 45, 60, 255), width=2)
    d.text((CX0 + 56, y + 18), sid, font=font(34, mono=True), fill=(156, 163, 175))
    d.text((CX0 + 230, y + 14), txt, font=font(40), fill=WHITE)
    if st == "ok":
        cx, cy = CX1 - 96, y + 38
        d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=CYAN)
        d.line((cx - 15, cy + 1, cx - 4, cy + 13, cx + 16, cy - 12), fill=INK, width=8)
    else:
        lab = "Reshoot"
        f = font(30, True)
        tw = d.textlength(lab, font=f)
        d.rounded_rectangle((CX1 - 56 - tw - 44, y + 10, CX1 - 56, y + 66), 28, outline=AMBER + (255,), width=4)
        d.text((CX1 - 56 - tw - 22, y + 21), lab, font=f, fill=AMBER)

# fade the left edge into the violet title background
fade = Image.new("L", (W, H), 255)
fd = ImageDraw.Draw(fade)
for x in range(0, 120):
    fd.line((x, 0, x, H), fill=int(255 * (x / 120) ** 1.6))
out = Image.new("RGBA", (W, H))
out.paste(img, (0, 0))
out.putalpha(fade)
out.save(OUT)
print(OUT, out.size)
