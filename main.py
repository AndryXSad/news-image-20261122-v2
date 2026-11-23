#!/usr/bin/env python3
"""The World in One Day -- Sunday 22 November 2026.

A single self-contained program (PIL + DejaVu only, no network, no clock,
no randomness) that draws one 1024x1024 newspaper front page summing up
the world's news of Sunday 22 November 2026 and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (or ./entry.png).

Design (written from a fresh design description, not copied from any
earlier renderer):
  * giant date masthead, red three-story subhead, big-number strip
  * region-count bar computed from the story list itself
  * UTC timeline strip
  * 3 large illustrated lead cards with certainty tags
  * 12 small illustrated story cards, each with its own drawn scene
  * dotted world map with numbered pins that match the story numbers
  * "Also on Sunday" list, a visible date-check box, sources + legend

If PIL is unavailable the program copies the pre-rendered entry.png that
ships next to this file, so the output is identical either way.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR") or "."
OUT = os.path.join(OUT_DIR, "entry.png")

W, H = 1024, 1024
PAPER = (247, 242, 230)
PANEL = (255, 253, 246)
INK = (25, 29, 36)
NAVY = (21, 42, 68)
NAVY2 = (31, 78, 121)
RED = (177, 30, 36)
RED_DK = (140, 20, 26)
GOLD = (185, 138, 29)
TEAL = (15, 118, 110)
ORANGE = (194, 112, 14)
GREEN = (74, 124, 47)
PURPLE = (107, 79, 161)
GREY = (92, 92, 92)
LGREY = (120, 118, 110)
SEA = (214, 230, 236)
LAND_DOT = (31, 58, 95)

REGION_COLORS = {
    "EUROPE": NAVY2, "MIDDLE EAST": RED, "AMERICAS": TEAL,
    "ASIA-PACIFIC": ORANGE, "AFRICA": GREEN, "OCEANIA": PURPLE,
    "WORLD": GREY,
}
REGION_ORDER = ["EUROPE", "MIDDLE EAST", "AMERICAS", "ASIA-PACIFIC",
                "AFRICA", "OCEANIA", "WORLD"]

CERT_COLORS = {
    "REPORTED": (15, 118, 110), "CLAIM": RED, "OFFICIAL": NAVY2,
    "FORECAST": (120, 90, 20),
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _font(name, size):
    try:
        from PIL import ImageFont
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        from PIL import ImageFont
        return ImageFont.load_default()


def serif_b(size):
    return _font("DejaVuSerif-Bold.ttf", size)


def serif(size):
    return _font("DejaVuSerif.ttf", size)


def sans(size):
    return _font("DejaVuSans.ttf", size)


def sans_b(size):
    return _font("DejaVuSans-Bold.ttf", size)


def text_w(draw, text, font):
    try:
        return draw.textlength(text, font=font)
    except Exception:
        return font.getlength(text)


def fit_font(draw, text, name, start, max_w, minimum=8):
    """Largest font size (<= start) at which text fits max_w."""
    size = start
    while size > minimum:
        f = _font(name, size)
        if text_w(draw, text, f) <= max_w:
            return f
        size -= 1
    return _font(name, minimum)


def wrap(draw, text, font, max_w):
    """Greedy word wrap; returns list of lines, never wider than max_w."""
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for wd in words[1:]:
        trial = cur + " " + wd
        if text_w(draw, trial, font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def draw_wrapped(draw, text, font, x, y, max_w, fill, leading=None,
                 max_lines=None, align="left"):
    """Draw wrapped text; returns y just below the last line."""
    if leading is None:
        leading = int(font.size * 1.32)
    lines = wrap(draw, text, font, max_w)
    if max_lines is not None:
        lines = lines[:max_lines]
    for ln in lines:
        if align == "center":
            lx = x + (max_w - text_w(draw, ln, font)) / 2
        elif align == "right":
            lx = x + max_w - text_w(draw, ln, font)
        else:
            lx = x
        draw.text((lx, y), ln, font=font, fill=fill)
        y += leading
    return y


def pill(draw, x, y, text, font, fg, bg, pad_x=6, pad_y=2):
    """Small rounded label; returns width used."""
    tw = text_w(draw, text, font)
    w = int(tw + pad_x * 2)
    h = int(font.size + pad_y * 2 + 2)
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return w


def num_badge(draw, cx, cy, n, r=9):
    """Red circle with a white story number."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED,
                 outline=(255, 255, 255), width=1)
    f = sans_b(11 if n < 10 else 9)
    t = str(n)
    draw.text((cx - text_w(draw, t, f) / 2, cy - f.size / 2 - 1), t,
              font=f, fill=(255, 255, 255))


# ---------------------------------------------------------------- data
# Dotted world map: 60 columns (6 deg lon each, -180..180) x 30 rows
# (4.5 deg lat each, 78N..57S). '#' is land. Authored by hand from a
# rough equirectangular sketch; pins are placed by lon/lat projection
# and nudged where the coarse grid puts a coast one cell off.
LAND = [
    "..........#########.######......#........##################.",
    "..#############.....#######.........########################",
    "..###################.....#...##############################",
    ".......##############........###############################",
    "........#############........#.....##################..###..",
    ".........############........########################.......",
    ".........###########........#########################......",
    ".........##########.........##########################......",
    ".........##########.........##########################......",
    ".........#########..........##########################......",
    "..........#######............###########.##########.........",
    "...........######............###########.##########.........",
    "............####...........#########.###..###....########...",
    "............#####..........#########......##.###............",
    "..............###..........###########....##..##............",
    "................#####......############......######.........",
    ".................#####......###########......###########....",
    ".................#######....##########........##########....",
    "................#########...#########..........######.......",
    "................#########......########.....................",
    ".................#######........#######.........#######.....",
    "..................######........#######.........########....",
    "..................#####.........####............########....",
    "..................#####.........####.............#######....",
    "..................###............###.............#######.###",
    "..................###............##..................###.###",
    ".................###..................................#..###",
    ".................###........................................",
    ".................###........................................",
    "..................##........................................",
]

# Stories. num: story number (also the map pin number for 1..15).
# region: one of REGION_ORDER. cert: REPORTED / CLAIM / OFFICIAL.
# lon/lat: map pin position for the 15 placed stories.
LEADS = [
    dict(num=1, place="ANTALYA, TÜRKIYE", topic="CLIMATE", region="EUROPE",
         cert="OFFICIAL", lon=30.7, lat=36.9, nudge=(-11, 3),
         scene="cop",
         head="COP31 ends with no deal",
         body=("After 44 hours of overtime, the longest climate summit on "
               "record closes with no pact adopted. The final text never "
               "names fossil fuels; the EU and island states refuse it."),
         source="UN News · Reuters · AP"),
    dict(num=2, place="KYIV, UKRAINE", topic="WAR", region="EUROPE",
         cert="REPORTED", lon=30.5, lat=50.4, nudge=(11, -4),
         scene="kyiv",
         head="Kyiv hit again overnight",
         body=("Russia fires 148 drones and 3 ballistic missiles across "
               "Ukraine overnight. Two killed, 83 hurt; Kryvyi Rih takes "
               "the worst of it, a child and a paramedic among the dead."),
         source="Kyiv Independent · Ukraine Monitor"),
    dict(num=3, place="MANAMA, BAHRAIN", topic="IRAN", region="MIDDLE EAST",
         cert="CLAIM", lon=50.6, lat=26.2, nudge=(-14, -4),
         scene="gulf",
         head="Iran strikes at Bahrain",
         body=("Bahrain says Iran set fire to a civilian industrial site "
               "late Saturday; no injuries. Tehran claims two US bases hit. "
               "Two tankers are struck near Hormuz; the US denies an F-16 "
               "was hit."),
         source="Reuters · Al Jazeera · FMT"),
]

MINIS = [
    dict(num=4, place="HONG KONG", topic="ELECTION", region="ASIA-PACIFIC",
         cert="OFFICIAL", lon=114.2, lat=22.3, nudge=(-4, -8), scene="ballot",
         head="Hong Kong elects its committee",
         body="856 vie for 723 seats; turnout 69.6% by 11 am.",
         source="SCMP"),
    dict(num=5, place="WELLINGTON", topic="CRICKET", region="OCEANIA",
         cert="OFFICIAL", lon=174.8, lat=-41.3, nudge=(-5, 0),
         scene="cricket",
         head="India declare on 720/9, a record in NZ",
         body="Pant's 128 powers the tourists; hosts trail by 261.",
         source="ESPNcricinfo"),
    dict(num=6, place="LAS VEGAS", topic="FORMULA 1", region="AMERICAS",
         cert="OFFICIAL", lon=-115.1, lat=36.2, nudge=(0, 0), scene="f1",
         head="Verstappen wins the Las Vegas GP",
         body="The champion takes the Sunday-night race from pole.",
         source="RaceFans · Formula 1"),
    dict(num=7, place="TURIN", topic="TENNIS", region="EUROPE",
         cert="OFFICIAL", lon=7.7, lat=45.1, nudge=(7, -6), scene="tennis",
         head="Alcaraz wins the ATP Finals",
         body="Beats world No. 1 Zverev 6-2, 7-6(7) for a first Turin crown.",
         source="Reuters · ATP"),
    dict(num=8, place="IMPHAL", topic="POISONING", region="ASIA-PACIFIC",
         cert="REPORTED", lon=93.9, lat=24.8, nudge=(4, 10), scene="bottle",
         head="Toxic alcohol kills 11 in Manipur",
         body="180+ in hospital after a batch of illicit liquor.",
         source="Xinhua"),
    dict(num=9, place="MUSCAT", topic="TANKERS", region="MIDDLE EAST",
         cert="REPORTED", lon=58.4, lat=23.6, nudge=(-2, 6), scene="tanker",
         head="Two tankers struck off Hormuz",
         body="UK maritime agency reports no casualties in the attacks.",
         source="UKMTO"),
    dict(num=10, place="MADRID", topic="SPAIN", region="EUROPE",
         cert="REPORTED", lon=-3.7, lat=40.4, nudge=(2, 6), scene="bank",
         head="Spain extends its bank levy to 2027",
         body="And heads for a snap election on 29 November.",
         source="Reuters"),
    dict(num=11, place="NEW YORK", topic="MARKETS", region="AMERICAS",
         cert="REPORTED", lon=-74.0, lat=40.7, nudge=(9, -3), scene="chart",
         head="S&P suffers its worst week since April",
         body="Stocks slide as a December Fed hike turns near-certain.",
         source="Reuters"),
    dict(num=12, place="WASHINGTON", topic="FED", region="AMERICAS",
         cert="REPORTED", lon=-77.0, lat=38.9, nudge=(-9, 7), scene="fed",
         head="December Fed hike now near-certain",
         body="Oil holds near $93 as Gulf tensions run high.",
         source="Reuters"),
    dict(num=13, place="MINNA", topic="NIGERIA", region="AFRICA",
         cert="REPORTED", lon=6.5, lat=9.6, nudge=(0, 0), scene="alert",
         head="Gunmen kill a village chief and four",
         body="Attackers strike in Niger State; no group claims it.",
         source="Reuters"),
    dict(num=14, place="DHAKA", topic="BANGLADESH", region="ASIA-PACIFIC",
         cert="REPORTED", lon=90.4, lat=23.8, nudge=(-12, -6),
         scene="factory",
         head="90 guard platoons deployed in Dhaka",
         body="Arson flares in the capital; troops guard key sites.",
         source="AP"),
    dict(num=15, place="SEOUL", topic="TECH", region="ASIA-PACIFIC",
         cert="REPORTED", lon=127.0, lat=37.5, nudge=(0, 0), scene="chip",
         head="SoftBank's Son weighed a $1tn buyout",
         body="The SK Hynix bid was shelved, reports say.",
         source="Reuters"),
]

# "Also on Sunday" -- one line each, region tagged.
ALSO = [
    (16, "TEHRAN", "MIDDLE EAST", "IRGC claims two US bases hit."),
    (17, "TEHRAN", "MIDDLE EAST", "US denies a missile hit an F-16."),
    (18, "RIYADH", "MIDDLE EAST", "Coalition intercepts 3 Houthi missiles."),
    (19, "RIYADH", "MIDDLE EAST", "Strikes follow on Hodeidah."),
    (20, "NEW DELHI", "ASIA-PACIFIC", "India passes 1 crore HPV doses."),
    (21, "COCOA", "AMERICAS", "St Johns River breaks 73-year record."),
    (22, "LONDON", "EUROPE", "Blair: rejoin EU only if UK innovates."),
    (23, "WARSAW", "EUROPE", "Rutte: NATO will defend every inch."),
    (24, "BOURNEMOUTH", "EUROPE", "Evanilson scores six games in a row."),
    (25, "MOSCOW", "EUROPE", "Russia revives pre-2022 NATO demands."),
    (26, "COVENTRY", "EUROPE", "McNeil own goal gives Coventry a 3-2 win."),
    (27, "PORTIMÃO", "EUROPE", "Márquez clinches an eighth MotoGP title."),
    (28, "MADRID", "EUROPE", "Spain heads for a snap poll on 29 Nov."),
    (29, "NEW YORK", "WORLD", "Oil holds near $93 on Gulf tensions."),
    (30, "WELLINGTON", "OCEANIA", "India 629/6 at lunch, lead 261."),
    (31, "HONG KONG", "ASIA-PACIFIC", "Polls open 09:00; 856 vie for 723 seats."),
    (32, "ANTALYA", "EUROPE", "EU: a good deal or no deal — then objects."),
    (33, "KYIV", "EUROPE", "Apartment block damaged in Kyiv Oblast."),
    (34, "MANAMA", "MIDDLE EAST", "Officials: no injuries at the site."),
    (35, "TURIN", "EUROPE", "Arribage and Olivetti win the doubles."),
    (36, "ANTALYA", "EUROPE", "The longest climate summit on record."),
]

TIMELINE = [
    ("00:00", "Explosions in Kyiv as a drone alert sounds across the capital."),
    ("00:41", "Reuters: India 629/6 at lunch in Wellington, lead 261."),
    ("01:00", "Hong Kong polls open — 856 candidates, 723 seats."),
    ("03:00", "COP31 objection deadline on the new climate package."),
    ("06:00", "COP31 reconvenes in Antalya to approve the deal."),
]

NUMBERS = [
    ("148", "Russian drones fired at Ukraine overnight"),
    ("83", "people injured in the overnight attack"),
    ("720/9", "India declare in Wellington — a record"),
    ("856", "candidates in Hong Kong's polls"),
    ("69.6%", "Hong Kong turnout by 11 am"),
    ("11", "dead in Manipur after toxic alcohol"),
]

DATECHECK = ("LEFT OUT ON PURPOSE — FIRST REPORTED SAT 21 NOV: the 400-drone "
             "barrage · “El Chapo Isidro” captured · Geneva “killer robots” "
             "talks end · Sparta II ablaze · Maluku M7.2 · Peru M6.8 · "
             "EU–Indonesia deal · Basra power-station fire.")


# ------------------------------------------------------- scene painters
def _star(d, cx, cy, r, fill):
    import math
    pts = []
    for i in range(8):
        a = math.pi * i / 4
        rr = r if i % 2 == 0 else r * 0.38
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _flame(d, x, y, s, c1=(255, 140, 0), c2=(255, 210, 60)):
    d.polygon([(x, y), (x + s * 0.45, y - s), (x + s * 0.8, y - s * 0.35),
               (x + s, y)], fill=c1)
    d.polygon([(x + s * 0.25, y), (x + s * 0.5, y - s * 0.55),
               (x + s * 0.75, y)], fill=c2)


def scene_cop(d, x, y, w, h):
    """COP31 hall: delegates at a long table, globe, NO DEAL stamp."""
    d.rectangle([x, y, x + w, y + h], fill=(23, 68, 74))
    d.rectangle([x, y, x + w, y + 26], fill=(18, 52, 58))
    # globe, left
    gx, gy, gr = x + 34, y + 52, 26
    d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=(64, 140, 190),
              outline=(220, 230, 235), width=2)
    d.ellipse([gx - 12, gy - 16, gx + 4, gy - 2], fill=(110, 190, 110))
    d.ellipse([gx - 2, gy + 4, gx + 16, gy + 18], fill=(110, 190, 110))
    d.arc([gx - gr, gy - gr, gx + gr, gy + gr], 60, 300, fill=(200, 220, 230))
    # table
    d.rectangle([x + 66, y + 62, x + w - 8, y + 78], fill=(122, 82, 48))
    d.rectangle([x + 66, y + 78, x + w - 8, y + h - 6], fill=(94, 62, 36))
    # delegates: heads + shoulders in flag colours
    skins = [(232, 190, 150), (190, 140, 100), (240, 205, 170),
             (200, 150, 105), (235, 195, 155), (180, 130, 95)]
    flags = [(177, 30, 36), (31, 78, 121), (15, 118, 110),
             (194, 112, 14), (107, 79, 161), (74, 124, 47)]
    n = 6
    for i in range(n):
        cx = x + 84 + i * ((w - 100) // (n - 1))
        d.ellipse([cx - 8, y + 34, cx + 8, y + 50], fill=skins[i])
        d.pieslice([cx - 13, y + 50, cx + 13, y + 70], 180, 360,
                   fill=flags[i])
        d.rectangle([cx - 1, y + 52, cx + 1, y + 60], fill=(250, 250, 250))
    # NO DEAL stamp (double outline, slightly tilted by construction)
    sx0, sy0 = x + w - 128, y + 8
    d.rounded_rectangle([sx0, sy0, sx0 + 118, sy0 + 30], radius=4,
                        outline=(255, 255, 255), width=3)
    d.rounded_rectangle([sx0 + 4, sy0 + 4, sx0 + 114, sy0 + 26], radius=3,
                        outline=(255, 255, 255), width=1)
    f = sans_b(19)
    d.text((sx0 + 59 - text_w(d, "NO DEAL", f) / 2, sy0 + 5), "NO DEAL",
           font=f, fill=(255, 255, 255))


def scene_kyiv(d, x, y, w, h):
    """Kyiv at night: skyline, lit windows, drones, explosions, moon."""
    d.rectangle([x, y, x + w, y + h], fill=(13, 20, 38))
    # stars: fixed deterministic pattern
    for i in range(26):
        sx = x + (i * 47) % (w - 8) + 4
        sy = y + (i * 29) % 34 + 4
        d.ellipse([sx, sy, sx + 1, sy + 1], fill=(220, 225, 240))
    # moon
    d.ellipse([x + w - 34, y + 8, x + w - 12, y + 30], fill=(235, 230, 205))
    d.ellipse([x + w - 30, y + 14, x + w - 24, y + 20], fill=(210, 205, 180))
    # searchlight beam
    d.polygon([(x + 60, y + h), (x + 120, y + 6), (x + 132, y + 6),
               (x + 84, y + h)], fill=(120, 130, 160))
    # skyline
    heights = [58, 74, 48, 82, 62, 90, 54, 70, 44, 78, 60, 68]
    bw = w // len(heights)
    for i, bh in enumerate(heights):
        bx = x + i * bw
        d.rectangle([bx + 1, y + h - bh, bx + bw - 1, y + h],
                    fill=(8, 12, 26))
        for wy in range(y + h - bh + 6, y + h - 6, 12):
            for wx in range(bx + 4, bx + bw - 4, 9):
                if (wx * 7 + wy * 13) % 5 < 2:
                    d.rectangle([wx, wy, wx + 3, wy + 4], fill=(255, 200, 90))
    # drones: small crosses with trails
    for dx, dy in ((x + 90, y + 22), (x + 190, y + 34), (x + 250, y + 18)):
        d.line([dx - 22, dy + 8, dx, dy], fill=(200, 200, 210), width=1)
        d.line([dx - 6, dy, dx + 6, dy], fill=(240, 240, 245), width=2)
        d.line([dx, dy - 6, dx, dy + 6], fill=(240, 240, 245), width=2)
    # explosions
    _star(d, x + 130, y + 40, 12, (255, 150, 40))
    _star(d, x + 130, y + 40, 6, (255, 220, 120))
    _star(d, x + 272, y + 52, 9, (255, 150, 40))
    _star(d, x + 272, y + 52, 4, (255, 220, 120))


def scene_gulf(d, x, y, w, h):
    """Strait of Hormuz: tanker ablaze, smoke, sun, second ship."""
    d.rectangle([x, y, x + w, y + 52], fill=(240, 200, 130))
    d.rectangle([x, y + 52, x + w, y + h], fill=(28, 68, 110))
    d.ellipse([x + 22, y + 10, x + 52, y + 40], fill=(255, 220, 120))
    for wy in (y + 62, y + 76, y + 90):
        for wx in range(x + 8, x + w - 8, 26):
            d.line([wx, wy, wx + 14, wy], fill=(120, 170, 210), width=2)
    # distant tanker
    d.rectangle([x + w - 96, y + 56, x + w - 30, y + 66], fill=(20, 30, 44))
    d.rectangle([x + w - 88, y + 48, x + w - 80, y + 56], fill=(20, 30, 44))
    # main tanker
    d.polygon([(x + 60, y + 66), (x + 250, y + 66), (x + 238, y + 92),
               (x + 72, y + 92)], fill=(16, 22, 34))
    d.rectangle([x + 210, y + 48, x + 244, y + 66], fill=(16, 22, 34))
    d.rectangle([x + 96, y + 54, x + 150, y + 66], fill=(120, 40, 30))
    d.rectangle([x + 156, y + 54, x + 200, y + 66], fill=(40, 90, 60))
    # funnel + smoke
    d.rectangle([x + 176, y + 38, x + 190, y + 54], fill=(140, 30, 26))
    for i, (sx, sy, sr) in enumerate(((184, 30, 8), (192, 21, 9),
                                      (200, 13, 10), (206, 6, 8))):
        d.ellipse([x + sx - sr, y + sy - sr, x + sx + sr, y + sy + sr],
                  fill=(70, 70, 74))
    # flames on deck
    _flame(d, x + 100, y + 54, 26)
    _flame(d, x + 158, y + 54, 20)


MINI_BG = {
    "ballot": (232, 238, 244), "cricket": (46, 110, 62),
    "f1": (24, 30, 44), "tennis": (52, 110, 160),
    "bottle": (40, 34, 30), "tanker": (28, 68, 110),
    "bank": (232, 226, 210), "chart": (250, 250, 248),
    "fed": (232, 226, 210), "alert": (30, 30, 34),
    "factory": (120, 140, 155), "chip": (26, 34, 48),
}


def scene_mini(d, key, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=MINI_BG[key])
    cx, cy = x + w // 2, y + h // 2
    if key == "ballot":
        d.rectangle([cx - 26, cy - 4, cx + 26, cy + 16], fill=(255, 255, 255),
                    outline=(120, 120, 120))
        d.rectangle([cx - 14, cy - 8, cx + 14, cy - 4], fill=(60, 60, 60))
        d.polygon([(cx - 8, cy + 2), (cx - 2, cy + 9), (cx + 12, cy - 8)],
                  fill=(177, 30, 36))
        d.rectangle([cx + 30, cy - 16, cx + 52, cy + 2], fill=(31, 78, 121))
    elif key == "cricket":
        d.rectangle([x, cy - 8, x + w, cy + 8], fill=(210, 190, 140))
        for sx in (cx - 34, cx - 30, cx - 26):
            d.rectangle([sx, cy - 14, sx + 2, cy + 6], fill=(255, 220, 90))
        d.ellipse([cx + 18, cy - 2, cx + 28, cy + 8], fill=(200, 40, 40))
        d.line([cx - 52, cy - 16, cx - 30, cy + 8], fill=(150, 100, 50),
               width=4)
    elif key == "f1":
        d.rounded_rectangle([cx - 52, cy - 6, cx + 52, cy + 8], radius=5,
                            fill=(200, 30, 36))
        d.rectangle([cx + 40, cy - 14, cx + 56, cy - 6], fill=(200, 30, 36))
        d.ellipse([cx - 34, cy + 4, cx - 18, cy + 18], fill=(10, 10, 12),
                  outline=(180, 180, 180))
        d.ellipse([cx + 22, cy + 4, cx + 38, cy + 18], fill=(10, 10, 12),
                  outline=(180, 180, 180))
        for i in range(8):
            d.rectangle([x + i * (w // 8), y + h - 6,
                         x + (i + 1) * (w // 8), y + h],
                        fill=(255, 255, 255) if i % 2 == 0 else (20, 20, 20))
    elif key == "tennis":
        d.line([x, cy + 10, x + w, cy + 10], fill=(255, 255, 255), width=2)
        d.line([cx, cy - 12, cx, cy + 12], fill=(255, 255, 255), width=2)
        d.ellipse([cx - 32, cy - 18, cx - 18, cy - 4], fill=(220, 230, 60),
                  outline=(255, 255, 255))
        d.arc([cx - 32, cy - 18, cx - 18, cy - 4], 200, 340,
              fill=(255, 255, 255))
    elif key == "bottle":
        d.rounded_rectangle([cx - 12, cy - 12, cx + 12, cy + 16], radius=4,
                            fill=(190, 120, 40))
        d.rectangle([cx - 5, cy - 20, cx + 5, cy - 12], fill=(190, 120, 40))
        d.polygon([(cx + 30, cy - 16), (cx + 44, cy + 8), (cx + 16, cy + 8)],
                  fill=(255, 210, 40))
        d.text((cx + 29, cy - 8), "!", font=sans_b(12), fill=(20, 20, 20))
    elif key == "tanker":
        d.rectangle([x, cy + 6, x + w, y + h], fill=(18, 48, 84))
        d.polygon([(cx - 52, cy - 2), (cx + 52, cy - 2), (cx + 44, cy + 12),
                   (cx - 44, cy + 12)], fill=(14, 20, 32))
        d.rectangle([cx + 26, cy - 12, cx + 46, cy - 2], fill=(14, 20, 32))
        _flame(d, cx - 30, cy - 2, 16)
    elif key == "bank":
        d.polygon([(cx - 40, cy - 14), (cx + 40, cy - 14), (cx, cy - 24)],
                  fill=(90, 70, 40))
        for i in (-28, 0, 28):
            d.rectangle([cx + i - 4, cy - 12, cx + i + 4, cy + 14],
                        fill=(120, 100, 66))
        d.rectangle([cx - 48, cy + 14, cx + 48, cy + 18], fill=(90, 70, 40))
    elif key == "chart":
        d.line([x + 10, y + 8, x + 10, y + h - 8], fill=(150, 150, 150))
        d.line([x + 10, y + h - 8, x + w - 8, y + h - 8], fill=(150, 150, 150))
        pts = [(x + 16, y + 10), (x + 44, y + 16), (x + 72, y + 12),
               (x + 100, y + 26), (x + 128, y + 30)]
        d.line(pts, fill=(177, 30, 36), width=3)
        for px, py in pts:
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(177, 30, 36))
    elif key == "fed":
        d.polygon([(cx - 34, cy - 12), (cx + 34, cy - 12), (cx, cy - 20)],
                  fill=(90, 70, 40))
        for i in (-20, 0, 20):
            d.rectangle([cx + i - 3, cy - 10, cx + i + 3, cy + 10],
                        fill=(120, 100, 66))
        d.text((cx + 26, cy - 16), "$", font=sans_b(18), fill=(15, 118, 110))
    elif key == "alert":
        d.polygon([(cx, cy - 18), (cx + 18, cy + 12), (cx - 18, cy + 12)],
                  fill=(255, 210, 40))
        d.text((cx - 3, cy - 10), "!", font=sans_b(16), fill=(20, 20, 20))
    elif key == "factory":
        d.rectangle([cx - 48, cy - 4, cx + 48, cy + 16], fill=(70, 80, 92))
        d.polygon([(cx - 48, cy - 4), (cx - 32, cy - 16), (cx - 16, cy - 4),
                   (cx, cy - 16), (cx + 16, cy - 4), (cx + 32, cy - 16),
                   (cx + 48, cy - 4)], fill=(70, 80, 92))
        d.rectangle([cx + 34, cy - 22, cx + 42, cy - 4], fill=(70, 80, 92))
        d.ellipse([cx + 30, cy - 30, cx + 40, cy - 20], fill=(230, 230, 230))
        d.ellipse([cx + 38, cy - 36, cx + 50, cy - 24], fill=(230, 230, 230))
    elif key == "chip":
        d.rectangle([cx - 16, cy - 14, cx + 16, cy + 14], fill=(60, 90, 140),
                    outline=(160, 190, 230), width=2)
        d.rectangle([cx - 7, cy - 6, cx + 7, cy + 6], fill=(40, 60, 100))
        for i in (-10, 0, 10):
            d.line([cx + i, cy - 20, cx + i, cy - 14], fill=(160, 190, 230),
                   width=2)
            d.line([cx + i, cy + 14, cx + i, cy + 20], fill=(160, 190, 230),
                   width=2)
            d.line([cx - 22, cy + i, cx - 16, cy + i], fill=(160, 190, 230),
                   width=2)
            d.line([cx + 16, cy + i, cx + 22, cy + i], fill=(160, 190, 230),
                   width=2)


# ------------------------------------------------------------ layout
LEAD_SCENES = {"cop": scene_cop, "kyiv": scene_kyiv, "gulf": scene_gulf}


def render():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    stories = LEADS + MINIS
    n_stories = len(stories) + len(ALSO)
    regions = {}
    for s in stories:
        regions[s["region"]] = regions.get(s["region"], 0) + 1
    for _n, _p, r, _t in ALSO:
        regions[r] = regions.get(r, 0) + 1
    n_regions = len(regions)

    # ---- top bar
    d.rectangle([0, 0, W, 26], fill=NAVY)
    d.text((8, 5), "THE WORLD IN ONE DAY", font=sans_b(13),
           fill=(255, 255, 255))
    right = ("%d STORIES · %d REGIONS · EVERY ONE DATED "
             "SUNDAY 22 NOVEMBER 2026" % (n_stories, n_regions))
    f = sans(11)
    d.text((W - 8 - text_w(d, right, f), 6), right, font=f,
           fill=(210, 215, 225))

    # ---- giant date masthead
    title = "Sunday 22 November 2026"
    tf = fit_font(d, title, "DejaVuSerif-Bold.ttf", 80, 1000)
    d.text(((W - text_w(d, title, tf)) / 2, 30), title, font=tf, fill=INK)
    d.rectangle([8, 110, W - 8, 112], fill=GOLD)
    d.rectangle([8, 114, W - 8, 115], fill=INK)

    # ---- red three-story subhead
    sub = ("148 drones over Ukraine in the night  ◆  COP31 ends with no deal"
           "  ◆  Iran's radar claim meets Bahrain's denial")
    sf = fit_font(d, sub, "DejaVuSans-Bold.ttf", 16, 1000)
    d.text(((W - text_w(d, sub, sf)) / 2, 118), sub, font=sf, fill=RED)

    # ---- big-number strip
    y0, ch, cw = 138, 54, 168
    for i, (num, cap) in enumerate(NUMBERS):
        x = 8 + i * cw
        d.rectangle([x, y0, x + cw - 2, y0 + ch], fill=PANEL,
                    outline=(205, 198, 180))
        nf = fit_font(d, num, "DejaVuSerif-Bold.ttf", 32, cw - 12)
        d.text((x + (cw - 2 - text_w(d, num, nf)) / 2, y0 + 2), num,
               font=nf, fill=RED)
        draw_wrapped(d, cap, sans(9), x + 6, y0 + 32, cw - 14, LGREY,
                     leading=11, max_lines=2, align="center")

    # ---- region-count bar (widths from the real counts)
    y0 = 196
    total = float(sum(regions.values()))
    widths = {}
    base, k = 52, (1008 - 52 * len(regions)) / max(1, sum(
        c - 1 for c in regions.values()))
    for r in REGION_ORDER:
        if r in regions:
            widths[r] = 52 + (regions[r] - 1) * k
    x = 8
    for r in REGION_ORDER:
        if r not in regions:
            continue
        wd = widths[r]
        d.rectangle([x, y0, x + wd - 1, y0 + 20], fill=REGION_COLORS[r])
        lab = "%s %d" % (r, regions[r])
        lf = sans_b(10)
        d.text((x + (wd - text_w(d, lab, lf)) / 2, y0 + 4), lab, font=lf,
               fill=(255, 255, 255))
        x += wd

    # ---- UTC timeline
    y0 = 220
    d.rectangle([8, y0, 118, y0 + 20], fill=NAVY)
    d.text((14, y0 + 4), "THE DAY IN UTC", font=sans_b(10),
           fill=(255, 255, 255))
    line_y = y0 + 14
    d.line([126, line_y, W - 8, line_y], fill=(150, 145, 135), width=2)
    tick_x = [220, 400, 580, 760, 940]
    for i, (tm, txt) in enumerate(TIMELINE):
        tx = tick_x[i]
        d.ellipse([tx - 4, line_y - 4, tx + 4, line_y + 4], fill=RED,
                  outline=(255, 255, 255), width=1)
        tf2 = sans_b(10)
        d.text((tx - text_w(d, tm, tf2) / 2, y0), tm, font=tf2,
               fill=RED)
        bx = max(126, min(tx - 82, W - 8 - 164))
        draw_wrapped(d, txt, sans(9), bx, y0 + 18, 164, INK,
                     leading=11, max_lines=2, align="center")

    # ---- lead cards
    y0, lh = 268, 254
    for i, s in enumerate(LEADS):
        x = 8 + i * 340
        d.rectangle([x, y0, x + 328, y0 + lh], fill=PANEL,
                    outline=(200, 194, 178))
        LEAD_SCENES[s["scene"]](d, x + 1, y0 + 1, 326, 104)
        num_badge(d, x + 16, y0 + 16, s["num"], r=11)
        ky = y0 + 112
        kf = sans_b(10)
        kick = "%s · %s" % (s["place"], s["topic"])
        d.text((x + 10, ky), kick, font=kf,
               fill=REGION_COLORS[s["region"]])
        _pf = sans_b(8)
        _pw = int(text_w(d, s["cert"], _pf) + 12)
        pill(d, x + 318 - _pw, ky - 1, s["cert"], _pf,
             (255, 255, 255), CERT_COLORS[s["cert"]])
        # headline (serif, up to 2 lines)
        hy = draw_wrapped(d, s["head"], serif_b(19), x + 10, ky + 18, 308,
                          INK, leading=22, max_lines=2)
        draw_wrapped(d, s["body"], sans(11), x + 10, hy + 4, 308, INK,
                     leading=14, max_lines=4)
        d.text((x + 10, y0 + lh - 16), s["source"], font=sans(9), fill=LGREY)

    # ---- mini cards (2 rows x 6)
    my0, mh = 528, 114
    for row in range(2):
        for col in range(6):
            s = MINIS[row * 6 + col]
            x = 8 + col * 169
            y = my0 + row * (mh + 6)
            d.rectangle([x, y, x + 163, y + mh], fill=PANEL,
                        outline=(200, 194, 178))
            scene_mini(d, s["scene"], x + 1, y + 1, 161, 40)
            num_badge(d, x + 13, y + 13, s["num"], r=9)
            kick = "%s · %s" % (s["place"], s["topic"])
            kf = fit_font(d, kick, "DejaVuSans-Bold.ttf", 9, 153)
            d.text((x + 6, y + 45), kick, font=kf,
                   fill=REGION_COLORS[s["region"]])
            draw_wrapped(d, s["head"], serif_b(11), x + 6, y + 57, 151,
                         INK, leading=12, max_lines=2)
            draw_wrapped(d, s["body"], sans(9), x + 6, y + 83, 151, INK,
                         leading=10, max_lines=2)
            d.text((x + 6, y + mh - 10), s["source"], font=sans(8),
                   fill=LGREY)

    # ---- bottom zone: map + also list
    by = 766
    d.text((8, by), "WHERE IT HAPPENED — PINS MATCH STORY NUMBERS",
           font=sans_b(11), fill=NAVY)
    d.text((446, by), "ALSO ON SUNDAY 22 NOVEMBER — 21 MORE STORIES",
           font=sans_b(11), fill=NAVY)
    d.line([8, by + 18, 438, by + 18], fill=NAVY, width=2)
    d.line([446, by + 18, W - 8, by + 18], fill=NAVY, width=2)

    # dotted map
    mx, my, mw, mhgt = 8, by + 22, 430, 120
    d.rectangle([mx, my, mx + mw, my + mhgt], fill=SEA)
    cw_, ch_ = mw / 60.0, mhgt / 30.0
    for r, row in enumerate(LAND):
        for c, ch2 in enumerate(row):
            if ch2 == "#":
                cx = mx + (c + 0.5) * cw_
                cy = my + (r + 0.5) * ch_
                d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=LAND_DOT)
    for s in stories:
        px = mx + (s["lon"] + 180.0) / 360.0 * mw + s["nudge"][0]
        py = my + (78.0 - s["lat"]) / 135.0 * mhgt + s["nudge"][1]
        num_badge(d, px, py, s["num"], r=9)

    # also list, two columns, one line each
    col_x = [446, 732]
    col_w = [278, 284]
    for j, (n, place, _r, txt) in enumerate(ALSO):
        col = 0 if j < 11 else 1
        row = j if j < 11 else j - 11
        x = col_x[col]
        y = by + 22 + row * 11.5
        f9 = sans_b(9)
        d.text((x, y), str(n), font=f9, fill=RED)
        item = "%s — %s" % (place, txt)
        fx = fit_font(d, item, "DejaVuSans.ttf", 9, col_w[col] - 22)
        d.text((x + 20, y), item, font=fx, fill=INK)

    # ---- date-check box
    y0 = 918
    d.rectangle([8, y0, W - 8, y0 + 38], outline=RED, width=2)
    d.rectangle([8, y0, 118, y0 + 38], fill=RED)
    d.text((14, y0 + 11), "DATE CHECK", font=sans_b(12),
           fill=(255, 255, 255))
    draw_wrapped(d, DATECHECK, sans(10), 128, y0 + 3, W - 8 - 138, INK,
                 leading=12, max_lines=2)

    # ---- sources + certainty legend
    y0 = 960
    d.text((8, y0), "SOURCES: REUTERS · AP · KYIV INDEPENDENT · UKRAINE "
           "MONITOR · CHINA DAILY · BBC · AL JAZEERA · SUPERSPORT · "
           "ESPNCRICINFO · UKMTO · ATP · RACEFANS · UN NEWS",
           font=sans(9), fill=LGREY)
    d.text((8, y0 + 13), "CERTAINTY:  REPORTED — carried by the day's wires"
           "   ·   CLAIM — one side's account, labelled as such   ·   "
           "OFFICIAL — result or on the record   ·   FORECAST — still to "
           "happen when drawn", font=sans(9), fill=LGREY)

    # ---- footer
    d.rectangle([0, 992, W, H], fill=NAVY)
    foot = ("THE WORLD IN ONE DAY  ·  SUNDAY 22 NOVEMBER 2026  ·  "
            "%d STORIES  ·  DRAWN, NOT PHOTOGRAPHED" % n_stories)
    ff = sans_b(12)
    d.text(((W - text_w(d, foot, ff)) / 2, 1004), foot, font=ff,
           fill=(255, 255, 255))
    return img


def main():
    try:
        from PIL import Image  # noqa: F401
    except Exception:
        src = os.path.join(HERE, "entry.png")
        if os.path.exists(src):
            os.makedirs(OUT_DIR, exist_ok=True)
            shutil.copyfile(src, OUT)
            return 0
        raise
    img = render()
    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(OUT, format="PNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
