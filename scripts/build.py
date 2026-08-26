from __future__ import annotations

import base64
import json
import math
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.designspaceLib import InstanceDescriptor
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Transform
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib import newTable
from fontTools.ttLib.tables.O_S_2f_2 import Panose
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates, flagOverlapSimple
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.varLib import build as build_variable
from fontTools.varLib.instancer import OverlapMode, instantiateVariableFont
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DIST = ROOT / "dist"
FILES = DIST / "files"
DOCS = ROOT / "documentation"

UPM = 1000
# Typographic metrics include room for Latin accents. The visible lowercase and
# capital construction zones remain 520 and 720 units respectively.
ASCENT = 900
DESCENT = -260
CAP_HEIGHT = 720
X_HEIGHT = 520
ASCENDER_HEIGHT = CAP_HEIGHT
DESCENDER_HEIGHT = -220
DEFAULT_ADVANCE = 620
VERSION = "0.7.0"
FAMILY_NAME = "Strawn"
PACKAGE_NAME = "@moriatz-labs/strawn"
FIXED_FONT_TIMESTAMP = 3_953_865_600

Point = tuple[float, float]
PathStroke = list[Point]


@dataclass(frozen=True)
class GlyphShape:
    advance: int
    paths: list[PathStroke]
    dots: list[Point]


def shape(
    paths: list[PathStroke] | None = None,
    *,
    advance: int = DEFAULT_ADVANCE,
    dots: list[Point] | None = None,
) -> GlyphShape:
    return GlyphShape(advance, paths or [], dots or [])


L, C, R = 90, 300, 510
B, M, T = 0, 360, 720
LOWER_BOWL_HEIGHT = 430

UPPER: dict[str, GlyphShape] = {
    "A": shape([[(L, B), (C, T), (R, B)], [(165, 250), (435, 250)]]),
    "B": shape([[(L, B), (L, T), (385, T), (R, 610), (R, 435), (385, M), (L, M)], [(385, M), (R, 285), (R, 110), (385, B), (L, B)]]),
    "C": shape([[(R, T), (L, T), (L, B), (R, B)]]),
    "D": shape([[(L, B), (L, T), (380, T), (R, 585), (R, 135), (380, B), (L, B)]]),
    "E": shape([[(R, T), (L, T), (L, B), (R, B)], [(L, M), (430, M)]]),
    "F": shape([[(R, T), (L, T), (L, B)], [(L, M), (430, M)]]),
    "G": shape([[(R, T), (L, T), (L, B), (R, B), (R, M), (330, M)]]),
    "H": shape([[(L, B), (L, T)], [(R, B), (R, T)], [(L, M), (R, M)]]),
    "I": shape([[(L, T), (R, T)], [(C, T), (C, B)], [(L, B), (R, B)]], advance=600),
    "J": shape([[(L, T), (R, T), (R, 110), (405, B), (180, B), (L, 110)]]),
    "K": shape([[(L, B), (L, T)], [(R, T), (L, M), (R, B)]]),
    "L": shape([[(L, T), (L, B), (R, B)]]),
    "M": shape([[(L, B), (L, T), (C, M), (R, T), (R, B)]], advance=660),
    "N": shape([[(L, B), (L, T), (R, B), (R, T)]]),
    "O": shape([[(195, T), (405, T), (R, 610), (R, 110), (405, B), (195, B), (L, 110), (L, 610), (195, T)]]),
    "P": shape([[(L, B), (L, T), (390, T), (R, 610), (R, 470), (390, M), (L, M)]]),
    "Q": shape([[(195, T), (405, T), (R, 610), (R, 110), (405, B), (195, B), (L, 110), (L, 610), (195, T)], [(350, 170), (565, DESCENDER_HEIGHT)]]),
    "R": shape([[(L, B), (L, T), (390, T), (R, 610), (R, 470), (390, M), (L, M)], [(340, M), (R, B)]]),
    "S": shape([[(R, T), (L, T), (L, M), (R, M), (R, B), (L, B)]]),
    "T": shape([[(L, T), (R, T)], [(C, T), (C, B)]], advance=500),
    "U": shape([[(L, T), (L, 110), (195, B), (405, B), (R, 110), (R, T)]]),
    "V": shape([[(L, T), (C, B), (R, T)]]),
    "W": shape([[(55, T), (165, B), (300, M), (435, B), (565, T)]], advance=680),
    "X": shape([[(L, T), (R, B)], [(R, T), (L, B)]]),
    "Y": shape([[(L, T), (C, M), (R, T)], [(C, M), (C, B)]]),
    "Z": shape([[(L, T), (R, T), (L, B), (R, B)]]),
}


# Lowercase letters have their own construction. Earlier releases scaled the
# capitals down to the x-height, which made mixed-case words read as a large
# initial followed by miniature capitals. These outlines preserve the same
# tapered geometry while adding recognisable bowls, shoulders, ascenders, and
# descenders so capitals and lowercase can share a line naturally.
LOWER: dict[str, GlyphShape] = {
    "a": shape([
        [(L, 420), (180, X_HEIGHT), (390, X_HEIGHT), (R, 420), (R, 0)],
        [(R, 260), (L, 260), (L, 100), (180, 0), (R, 0)],
    ], advance=560),
    "b": shape([
        [(L, 0), (L, ASCENDER_HEIGHT)],
        [(L, LOWER_BOWL_HEIGHT), (385, LOWER_BOWL_HEIGHT), (R, 340), (R, 100), (385, 0), (L, 0)],
    ], advance=560),
    "c": shape([[(R, X_HEIGHT), (180, X_HEIGHT), (L, 420), (L, 100), (180, 0), (R, 0)]], advance=550),
    "d": shape([
        [(R, 0), (R, ASCENDER_HEIGHT)],
        [(R, LOWER_BOWL_HEIGHT), (215, LOWER_BOWL_HEIGHT), (L, 340), (L, 100), (215, 0), (R, 0)],
    ], advance=560),
    "e": shape([
        [(R, 260), (L, 260), (L, 420), (180, X_HEIGHT), (405, X_HEIGHT), (R, 420), (R, 260)],
        [(L, 260), (L, 100), (180, 0), (R, 0)],
    ], advance=550),
    "f": shape([
        [(240, 0), (240, ASCENDER_HEIGHT), (R, ASCENDER_HEIGHT)],
        [(L, 430), (430, 430)],
    ], advance=500),
    "g": shape([
        [(180, X_HEIGHT), (390, X_HEIGHT), (R, 420), (R, 0), (180, 0), (L, 100), (L, 420), (180, X_HEIGHT)],
        [(R, X_HEIGHT), (R, -120), (420, DESCENDER_HEIGHT), (210, DESCENDER_HEIGHT), (L, -120)],
    ], advance=560),
    "h": shape([
        [(L, 0), (L, ASCENDER_HEIGHT)],
        [(L, LOWER_BOWL_HEIGHT), (360, LOWER_BOWL_HEIGHT), (R, 340), (R, 0)],
    ], advance=560),
    "i": shape([[(C, 0), (C, 370)]], advance=340, dots=[(C, 500)]),
    "j": shape([[(C, 370), (C, -80), (220, DESCENDER_HEIGHT), (L, DESCENDER_HEIGHT)]], advance=380, dots=[(C, 500)]),
    "k": shape([
        [(L, 0), (L, ASCENDER_HEIGHT)],
        [(R, X_HEIGHT), (L, 260), (R, 0)],
    ], advance=550),
    "l": shape([[(C, ASCENDER_HEIGHT), (C, 90), (380, 0), (R, 0)]], advance=420),
    "m": shape([
        [(L, 0), (L, X_HEIGHT)],
        [(L, X_HEIGHT), (275, X_HEIGHT), (350, 410), (350, 0)],
        [(350, X_HEIGHT), (535, X_HEIGHT), (610, 410), (610, 0)],
    ], advance=700),
    "n": shape([
        [(L, 0), (L, X_HEIGHT)],
        [(L, X_HEIGHT), (360, X_HEIGHT), (R, 400), (R, 0)],
    ], advance=560),
    "o": shape([[(180, X_HEIGHT), (390, X_HEIGHT), (R, 420), (R, 100), (390, 0), (180, 0), (L, 100), (L, 420), (180, X_HEIGHT)]], advance=560),
    "p": shape([
        [(L, DESCENDER_HEIGHT), (L, X_HEIGHT)],
        [(L, LOWER_BOWL_HEIGHT), (385, LOWER_BOWL_HEIGHT), (R, 340), (R, 100), (385, 0), (L, 0)],
    ], advance=560),
    "q": shape([
        [(R, DESCENDER_HEIGHT), (R, X_HEIGHT)],
        [(R, LOWER_BOWL_HEIGHT), (215, LOWER_BOWL_HEIGHT), (L, 340), (L, 100), (215, 0), (R, 0)],
    ], advance=560),
    "r": shape([
        [(L, 0), (L, X_HEIGHT)],
        [(L, X_HEIGHT), (330, X_HEIGHT), (R, 390)],
    ], advance=538),
    "s": shape([[(R, X_HEIGHT), (L, X_HEIGHT), (L, 260), (R, 260), (R, 0), (L, 0)]], advance=540),
    "t": shape([
        [(C, 610), (C, 100), (390, 0), (R, 0)],
        [(L, 410), (R, 410)],
    ], advance=500),
    "u": shape([[(L, X_HEIGHT), (L, 100), (180, 0), (390, 0), (R, 100), (R, X_HEIGHT)]], advance=560),
    "v": shape([[(L, X_HEIGHT), (C, 0), (R, X_HEIGHT)]], advance=560),
    "w": shape([[(55, X_HEIGHT), (165, 0), (300, 260), (435, 0), (565, X_HEIGHT)]], advance=640),
    "x": shape([[(L, X_HEIGHT), (R, 0)], [(R, X_HEIGHT), (L, 0)]], advance=550),
    "y": shape([
        [(L, X_HEIGHT), (C, 40), (R, X_HEIGHT)],
        [(C, 40), (250, DESCENDER_HEIGHT), (L, DESCENDER_HEIGHT)],
    ], advance=560),
    "z": shape([[(L, X_HEIGHT), (R, X_HEIGHT), (L, 0), (R, 0)]], advance=540),
}

DIGITS: dict[str, GlyphShape] = {
    "0": UPPER["O"],
    "1": shape([[(190, 600), (300, T), (300, B)], [(170, B), (430, B)]], advance=560),
    "2": shape([[(L, 610), (195, T), (405, T), (R, 610), (R, M), (L, B), (R, B)]]),
    "3": shape([[(L, T), (R, T), (R, B), (L, B)], [(255, M), (R, M)]]),
    "4": shape([[(L, T), (L, M), (R, M)], [(R, T), (R, B)]]),
    "5": shape([[(R, T), (L, T), (L, M), (R, M), (R, B), (L, B)]]),
    "6": shape([[(R, T), (L, M), (L, B), (R, B), (R, M), (L, M)]]),
    "7": shape([[(L, T), (R, T), (215, B)]]),
    "8": shape([[(L, M), (L, T), (R, T), (R, M), (L, M), (L, B), (R, B), (R, M)]]),
    "9": shape([[(R, M), (L, M), (L, T), (R, T), (R, B), (L, B)]]),
}

PUNCT: dict[str, GlyphShape] = {
    "!": shape([[(C, 215), (C, T)]], advance=360, dots=[(C, 45)]),
    '"': shape([[(210, T), (210, 545)], [(390, T), (390, 545)]], advance=500),
    "#": shape([[(210, T), (150, B)], [(450, T), (390, B)], [(L, 500), (R, 500)], [(L, 220), (R, 220)]]),
    "$": shape(UPPER["S"].paths + [[(C, 790), (C, -70)]]),
    "%": shape([[(L, B), (R, T)], [(120, 610), (220, 710), (320, 610), (220, 510), (120, 610)], [(280, 110), (380, 210), (480, 110), (380, 10), (280, 110)]]),
    "&": shape([[(R, 90), (400, B), (190, B), (L, 120), (L, 300), (410, T), (R, 610), (R, 500), (L, 190)], [(350, 300), (R, 90)]]),
    "'": shape([[(C, T), (C, 540)]], advance=320),
    "(": shape([[(400, T), (220, 540), (170, M), (220, 180), (400, B)]], advance=480),
    ")": shape([[(200, T), (380, 540), (430, M), (380, 180), (200, B)]], advance=480),
    "*": shape([[(C, 630), (C, 250)], [(135, 535), (465, 345)], [(465, 535), (135, 345)]], advance=600),
    "+": shape([[(C, 590), (C, 130)], [(L, M), (R, M)]]),
    ",": shape([[(330, 70), (260, -110)]], advance=340),
    "-": shape([[(L, M), (R, M)]]),
    ".": shape(advance=340, dots=[(C, 45)]),
    "/": shape([[(L, -50), (R, 770)]]),
    ":": shape(advance=340, dots=[(C, 500), (C, 120)]),
    ";": shape([[(330, 150), (260, -70)]], advance=340, dots=[(C, 500)]),
    "<": shape([[(R, 620), (L, M), (R, 100)]]),
    "=": shape([[(L, 470), (R, 470)], [(L, 250), (R, 250)]]),
    ">": shape([[(L, 620), (R, M), (L, 100)]]),
    "?": shape([[(L, 610), (190, T), (410, T), (R, 610), (R, 470), (C, 300), (C, 215)]], dots=[(C, 45)]),
    "@": shape(UPPER["O"].paths + [[(410, 190), (410, 500), (250, 500), (180, 430), (180, 260), (250, 190), (500, 190)]]),
    "[": shape([[(400, T), (L, T), (L, B), (400, B)]], advance=460),
    "\\": shape([[(L, 770), (R, -50)]]),
    "]": shape([[(200, T), (R, T), (R, B), (200, B)]], advance=460),
    "^": shape([[(L, 430), (C, T), (R, 430)]]),
    "_": shape([[(L, -70), (R, -70)]]),
    "`": shape([[(240, T), (340, 590)]], advance=400),
    "{": shape([[(410, T), (270, T), (250, 430), (L, M), (250, 290), (270, B), (410, B)]], advance=500),
    "|": shape([[(C, 780), (C, -60)]], advance=360),
    "}": shape([[(190, T), (330, T), (350, 430), (R, M), (350, 290), (330, B), (190, B)]], advance=500),
    "~": shape([[(L, 300), (200, 420), (400, 300), (R, 420)]]),
    "·": shape(advance=340, dots=[(C, M)]),
    "–": shape([[(L, M), (R, M)]], advance=620),
    "—": shape([[(40, M), (960, M)]], advance=1000),
}


def transform_paths(
    source: GlyphShape,
    *,
    scale_x: float = 1,
    scale_y: float = 1,
    move_x: float = 0,
    move_y: float = 0,
) -> list[PathStroke]:
    return [
        [(x * scale_x + move_x, y * scale_y + move_y) for x, y in path]
        for path in source.paths
    ]


SPECIAL: dict[str, GlyphShape] = {
    "Æ": shape(
        transform_paths(UPPER["A"], scale_x=0.72, move_x=-10)
        + transform_paths(UPPER["E"], scale_x=0.72, move_x=300),
        advance=800,
    ),
    "æ": shape(
        transform_paths(LOWER["a"], scale_x=0.72, move_x=-5)
        + transform_paths(LOWER["e"], scale_x=0.72, move_x=280),
        advance=760,
    ),
    "Ð": shape(UPPER["D"].paths + [[(25, M), (355, M)]]),
    "ð": shape(LOWER["d"].paths + [[(245, 610), (455, 710)]]),
    "Ø": shape(UPPER["O"].paths + [[(55, -35), (545, 755)]]),
    "ø": shape(LOWER["o"].paths + [[(55, -35), (510, 555)]]),
    "Þ": shape([
        [(L, B), (L, T)],
        [(L, 560), (390, 560), (R, 470), (R, 300), (390, 210), (L, 210)],
    ]),
    "þ": shape([
        [(L, DESCENDER_HEIGHT), (L, ASCENDER_HEIGHT)],
        [(L, LOWER_BOWL_HEIGHT), (385, LOWER_BOWL_HEIGHT), (R, 340), (R, 100), (385, 0), (L, 0)],
    ], advance=560),
    "ß": shape([
        [(L, 0), (L, 590), (180, ASCENDER_HEIGHT), (385, ASCENDER_HEIGHT), (R, 610), (390, 420), (L, 300)],
        [(300, 300), (R, 180), (R, 80), (390, 0), (220, 0)],
    ], advance=570),
    "ẞ": shape([
        [(L, 0), (L, 590), (180, T), (385, T), (R, 610), (390, 420), (L, 300)],
        [(300, 300), (R, 180), (R, 80), (390, 0), (220, 0)],
    ]),
    "Đ": shape(UPPER["D"].paths + [[(25, M), (355, M)]]),
    "đ": shape(LOWER["d"].paths + [[(250, 590), (555, 590)]], advance=560),
    "ď": shape(LOWER["d"].paths + [[(545, 700), (500, 585)]], advance=590),
    "Ħ": shape(UPPER["H"].paths + [[(30, 525), (570, 525)]]),
    "ħ": shape(LOWER["h"].paths + [[(40, 570), (340, 570)]], advance=560),
    "ı": shape([[(C, 0), (C, 370)]], advance=340),
    "ȷ": shape([[(C, 370), (C, -80), (220, DESCENDER_HEIGHT), (L, DESCENDER_HEIGHT)]], advance=380),
    "Ł": shape(UPPER["L"].paths + [[(35, 210), (415, 500)]]),
    "ł": shape(LOWER["l"].paths + [[(110, 230), (455, 485)]], advance=420),
    "Ľ": shape(UPPER["L"].paths + [[(555, 700), (510, 585)]]),
    "ľ": shape(LOWER["l"].paths + [[(505, 700), (460, 585)]], advance=500),
    "Œ": shape(
        transform_paths(UPPER["O"], scale_x=0.72, move_x=-5)
        + transform_paths(UPPER["E"], scale_x=0.72, move_x=300),
        advance=810,
    ),
    "œ": shape(
        transform_paths(LOWER["o"], scale_x=0.72, move_x=-5)
        + transform_paths(LOWER["e"], scale_x=0.72, move_x=285),
        advance=770,
    ),
    "ť": shape(LOWER["t"].paths + [[(525, 700), (480, 585)]], advance=550),
}

# Combining marks are drawn around the origin. Composite glyphs translate them
# onto explicit top or bottom anchors, and GPOS uses the same anchor model for
# decomposed text.
COMBINING_MARKS: dict[str, GlyphShape] = {
    "̀": shape([[(-55, 95), (45, 0)]], advance=0),
    "́": shape([[(-45, 0), (55, 95)]], advance=0),
    "̂": shape([[(-80, 0), (0, 90), (80, 0)]], advance=0),
    "̃": shape([[(-90, 25), (-35, 75), (25, 25), (90, 75)]], advance=0),
    "̄": shape([[(-90, 45), (90, 45)]], advance=0),
    "̆": shape([[(-85, 85), (-45, 20), (45, 20), (85, 85)]], advance=0),
    "̇": shape(advance=0, dots=[(0, 45)]),
    "̈": shape(advance=0, dots=[(-62, 45), (62, 45)]),
    "̊": shape([[(-45, 45), (0, 90), (45, 45), (0, 0), (-45, 45)]], advance=0),
    "̋": shape([[(-85, 0), (-25, 95)], [(15, 0), (75, 95)]], advance=0),
    "̌": shape([[(-80, 90), (0, 0), (80, 90)]], advance=0),
    "̦": shape([[(0, -5), (-25, -105)]], advance=0),
    "̧": shape([[(0, -5), (-35, -80), (25, -140)]], advance=0),
    "̨": shape([[(0, -5), (-5, -90), (65, -140)]], advance=0),
}

LATIN_CORE_CODEPOINTS = tuple(
    int(value, 16)
    for value in """
0020 0021 0022 0023 0024 0025 0026 0027 0028 0029 002A 002B 002C 002D 002E 002F
0030 0031 0032 0033 0034 0035 0036 0037 0038 0039 003A 003B 003C 003D 003E 003F
0040 0041 0042 0043 0044 0045 0046 0047 0048 0049 004A 004B 004C 004D 004E 004F
0050 0051 0052 0053 0054 0055 0056 0057 0058 0059 005A 005B 005C 005D 005E 005F
0060 0061 0062 0063 0064 0065 0066 0067 0068 0069 006A 006B 006C 006D 006E 006F
0070 0071 0072 0073 0074 0075 0076 0077 0078 0079 007A 007B 007C 007D 007E 00A0
00A1 00A2 00A3 00A5 00A7 00A8 00A9 00AA 00AB 00AE 00AF 00B0 00B4 00B6 00B7
00B8 00BA 00BB 00BF 00C0 00C1 00C2 00C3 00C4 00C5 00C6 00C7 00C8 00C9 00CA
00CB 00CC 00CD 00CE 00CF 00D0 00D1 00D2 00D3 00D4 00D5 00D6 00D7 00D8 00D9
00DA 00DB 00DC 00DD 00DE 00DF 00E0 00E1 00E2 00E3 00E4 00E5 00E6 00E7 00E8
00E9 00EA 00EB 00EC 00ED 00EE 00EF 00F0 00F1 00F2 00F3 00F4 00F5 00F6 00F7
00F8 00F9 00FA 00FB 00FC 00FD 00FE 00FF 0100 0101 0102 0103 0104 0105 0106
0107 010A 010B 010C 010D 010E 010F 0110 0111 0112 0113 0116 0117 0118 0119
011A 011B 011E 011F 0120 0121 0122 0123 0126 0127 012A 012B 012E 012F 0130
0131 0136 0137 0139 013A 013B 013C 013D 013E 0141 0142 0143 0144 0145 0146
0147 0148 0150 0151 0152 0153 0154 0155 0158 0159 015A 015B 015E 015F 0160
0161 0164 0165 016A 016B 016E 016F 0170 0171 0172 0173 0174 0175 0176 0177
0178 0179 017A 017B 017C 017D 017E 0218 0219 021A 021B 0237 02C6 02C7 02D8
02D9 02DA 02DB 02DC 02DD 0300 0301 0302 0303 0304 0306 0307 0308 030A 030B
030C 0326 0327 0328 1E80 1E81 1E82 1E83 1E84 1E85 1E9E 1EF2 1EF3 2013
2014 2018 2019 201A 201C 201D 201E 2022 2026 2039 203A 20AC 2122 2212
""".split()
)


def spacing_mark(mark: str, *, advance: int = 360) -> GlyphShape:
    source = COMBINING_MARKS[mark]
    return shape(
        transform_paths(source, move_x=advance / 2, move_y=390),
        advance=advance,
        dots=[(x + advance / 2, y + 390) for x, y in source.dots],
    )


EXTRA_SYMBOLS: dict[str, GlyphShape] = {
    "\u00a0": shape(advance=320),
    "¡": shape([[(C, 505), (C, 0)]], advance=360, dots=[(C, 675)]),
    "¢": shape(LOWER["c"].paths + [[(C, 620), (C, -90)]], advance=560),
    "£": shape([[(470, 610), (390, T), (210, T), (150, 610), (210, M), (150, 0), (R, 0)], [(L, M), (410, M)]]),
    "¥": shape(UPPER["Y"].paths + [[(145, 300), (455, 300)], [(170, 190), (430, 190)]]),
    "§": shape(UPPER["S"].paths + [[(R, 570), (L, 150)]]),
    "¨": spacing_mark("̈"),
    "©": shape(UPPER["O"].paths + transform_paths(UPPER["C"], scale_x=.45, scale_y=.45, move_x=165, move_y=200)),
    "ª": shape(transform_paths(LOWER["a"], scale_x=.55, scale_y=.55, move_x=125, move_y=380), advance=420),
    "«": shape([[ (280, 560), (L, M), (280, 160)], [(R, 560), (330, M), (R, 160)]], advance=620),
    "®": shape(UPPER["O"].paths + transform_paths(UPPER["R"], scale_x=.42, scale_y=.42, move_x=175, move_y=210)),
    "¯": spacing_mark("̄"),
    "°": shape([[ (255, 640), (C, 700), (345, 640), (C, 580), (255, 640)]], advance=440),
    "´": spacing_mark("́"),
    "¶": shape([[(R, T), (215, T), (L, 610), (L, 450), (215, M), (R, M)], [(330, T), (330, 0)], [(R, T), (R, 0)]]),
    "¸": spacing_mark("̧"),
    "º": shape(transform_paths(LOWER["o"], scale_x=.55, scale_y=.55, move_x=125, move_y=380), advance=420),
    "»": shape([[ (L, 560), (280, M), (L, 160)], [(330, 560), (R, M), (330, 160)]], advance=620),
    "¿": shape([[(C, 505), (C, 420), (L, 250), (L, 110), (190, 0), (410, 0), (R, 110)]], dots=[(C, 675)]),
    "×": shape([[(L, 560), (R, 160)], [(R, 560), (L, 160)]]),
    "÷": shape([[(L, M), (R, M)]], dots=[(C, 560), (C, 160)]),
    "ˆ": spacing_mark("̂"),
    "ˇ": spacing_mark("̌"),
    "˘": spacing_mark("̆"),
    "˙": spacing_mark("̇"),
    "˚": spacing_mark("̊"),
    "˛": spacing_mark("̨"),
    "˜": spacing_mark("̃"),
    "˝": spacing_mark("̋"),
    "‘": shape([[ (C, 540), (260, T)]], advance=320),
    "’": shape([[ (C, T), (260, 540)]], advance=320),
    "‚": shape([[ (C, 90), (260, -90)]], advance=320),
    "“": shape([[ (220, 540), (180, T)], [(390, 540), (350, T)]], advance=500),
    "”": shape([[ (220, T), (180, 540)], [(390, T), (350, 540)]], advance=500),
    "„": shape([[ (220, 90), (180, -90)], [(390, 90), (350, -90)]], advance=500),
    "•": shape(advance=420, dots=[(C, M)]),
    "…": shape(advance=860, dots=[(170, 45), (430, 45), (690, 45)]),
    "‹": shape([[(380, 560), (L, M), (380, 160)]], advance=480),
    "›": shape([[(220, 560), (R, M), (220, 160)]], advance=480),
    "€": shape(UPPER["C"].paths + [[(90, 445), (420, 445)], [(90, 275), (420, 275)]]),
    "™": shape(
        transform_paths(UPPER["T"], scale_x=.42, scale_y=.42, move_x=25, move_y=415)
        + transform_paths(UPPER["M"], scale_x=.42, scale_y=.42, move_x=290, move_y=415),
        advance=650,
    ),
    "−": shape([[(L, M), (R, M)]]),
}


# Every source glyph has an explicit optical left edge and fixed advance. Right
# space is allowed to change with stroke weight; the advance never does.
LEFT_SIDEBEARINGS: dict[str, int] = {
    **{character: 62 for character in "BCDEFGHJKLNOPQRSU"},
    **{character: 52 for character in "MT"},
    **{character: 44 for character in "AVWXYZ"},
    "I": 72,
    **{character: 48 for character in "abcdefghkmnopqu"},
    **{character: 42 for character in "csvwxyz"},
    "i": 74,
    "j": 56,
    "l": 60,
    "r": 42,
    "t": 44,
    **{character: 54 for character in "0123456789"},
}


def decomposition_for(character: str) -> tuple[str, tuple[str, ...]] | None:
    decomposition = unicodedata.normalize("NFD", character)
    if len(decomposition) < 2:
        return None
    base, marks = decomposition[0], tuple(decomposition[1:])
    if base in "ij" and marks:
        base = "ı" if base == "i" else "ȷ"
    if base in {**UPPER, **LOWER, **SPECIAL} and all(mark in COMBINING_MARKS for mark in marks):
        return base, marks
    return None


def all_shapes() -> dict[str, GlyphShape]:
    result = {**UPPER, **LOWER, **DIGITS, **PUNCT, **SPECIAL, **EXTRA_SYMBOLS, **COMBINING_MARKS}
    result[" "] = shape(advance=320)
    return result


def polyline_length(points: PathStroke) -> float:
    return sum(math.dist(start, end) for start, end in zip(points, points[1:]))


def svg_polyline(points: PathStroke) -> str:
    commands = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    commands.extend(f"L {point[0]:.2f} {point[1]:.2f}" for point in points[1:])
    return " ".join(commands)


def write_hero_wordmark() -> None:
    shapes = all_shapes()
    width, height = 5000, 1740
    tracking = 80
    line_specs = [("STRAWN", 1200)]
    strokes: list[dict[str, object]] = []
    previous_end: Point | None = None

    for word, baseline in line_specs:
        word_width = sum(shapes[character].advance for character in word) + tracking * (len(word) - 1)
        cursor = (width - word_width) / 2
        for character in word:
            glyph_shape = shapes[character]
            advance, paths = glyph_shape.advance, glyph_shape.paths
            for source_path in paths:
                points = [(cursor + x, baseline - y) for x, y in source_path]
                if previous_end is not None:
                    travel_peak = min(previous_end[1], points[0][1]) - 110
                    travel_path = (
                        f"M {previous_end[0]:.2f} {previous_end[1]:.2f} "
                        f"Q {(previous_end[0] + points[0][0]) / 2:.2f} {travel_peak:.2f} "
                        f"{points[0][0]:.2f} {points[0][1]:.2f}"
                    )
                    direct = math.dist(previous_end, points[0])
                    strokes.append({"kind": "travel", "path": travel_path, "length": round(direct * 1.12, 2), "glyph": character})
                strokes.append({"kind": "ink", "path": svg_polyline(points), "length": round(polyline_length(points), 2), "glyph": character})
                previous_end = points[-1]
            cursor += advance + tracking

    data = {
        "fontVersion": VERSION,
        "viewBox": [0, 0, width, height],
        "lines": [word for word, _ in line_specs],
        "lineLayouts": [
            {"text": word, "x": width / 2, "baseline": baseline, "tracking": tracking}
            for word, baseline in line_specs
        ],
        "strokes": strokes,
        "totalInkLength": round(sum(float(stroke["length"]) for stroke in strokes if stroke["kind"] == "ink"), 2),
    }
    (FILES / "Strawn-Hero-Strokes.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def add_tapered_stroke(pen: TTGlyphPen, start: Point, end: Point, width: float) -> None:
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    half = width / 2
    # Weight changes the body, not the character of the terminal. A linear
    # taper keeps the toothpick point stable across the complete axis.
    taper = min(length * 0.32, max(width * 1.55, 24))
    points = [
        (x1, y1),
        (x1 + ux * taper + nx * half, y1 + uy * taper + ny * half),
        (x2 - ux * taper + nx * half, y2 - uy * taper + ny * half),
        (x2, y2),
        (x2 - ux * taper - nx * half, y2 - uy * taper - ny * half),
        (x1 + ux * taper - nx * half, y1 + uy * taper - ny * half),
    ]
    pen.moveTo(points[0])
    for point in points[1:]:
        pen.lineTo(point)
    pen.closePath()


def add_diamond(pen: TTGlyphPen, center: Point, width: float) -> None:
    x, y = center
    radius = max(width * 0.9, 24)
    pen.moveTo((x, y + radius))
    pen.lineTo((x + radius, y))
    pen.lineTo((x, y - radius))
    pen.lineTo((x - radius, y))
    pen.closePath()


def build_glyph(shape_data: GlyphShape, stroke_width: float):
    paths, dots = shape_data.paths, shape_data.dots
    pen = TTGlyphPen(None)
    for path in paths:
        for start, end in zip(path, path[1:]):
            add_tapered_stroke(pen, start, end, stroke_width)
    for dot in dots:
        add_diamond(pen, dot, stroke_width)
    return pen.glyph()


def align_glyph(glyph, left_sidebearing: int, vertical_bounds: tuple[int, int] | None = None):
    """Apply an explicit optical left edge and normalize alignment zones."""
    if not glyph.coordinates:
        return glyph

    coordinates = list(glyph.coordinates)
    x_min = min(point[0] for point in coordinates)
    x_offset = left_sidebearing - x_min

    if vertical_bounds is None:
        transformed = [(round(x + x_offset), round(y)) for x, y in coordinates]
    else:
        target_min, target_max = vertical_bounds
        y_min = min(point[1] for point in coordinates)
        y_max = max(point[1] for point in coordinates)
        y_scale = (target_max - target_min) / (y_max - y_min)
        transformed = [
            (round(x + x_offset), round(target_min + (y - y_min) * y_scale))
            for x, y in coordinates
        ]

    glyph.coordinates = GlyphCoordinates(transformed)
    return glyph


def left_sidebearing_for(character: str) -> int:
    if character in COMBINING_MARKS:
        return 0
    decomposition = decomposition_for(character)
    if decomposition:
        return left_sidebearing_for(decomposition[0])
    if character in LEFT_SIDEBEARINGS:
        return LEFT_SIDEBEARINGS[character]
    if character in ".,:;!'‘’‚“”„":
        return 110
    if character in "()[]{}<>‹›«»":
        return 54
    if character.isspace():
        return 0
    return 58


def vertical_bounds_for(character: str) -> tuple[int, int] | None:
    if character in "CGOØ":
        return (-12, 732)
    if character == "Q":
        return (DESCENDER_HEIGHT, 732)
    if character in UPPER or character in "ÆÐÞĐĦŒẞ":
        return (0, CAP_HEIGHT)
    if character in "aceosøœ":
        return (-10, 530)
    if character == "g":
        return (DESCENDER_HEIGHT, 530)
    if character in "mnrsvwxz":
        return (0, X_HEIGHT)
    if character in "bdfhklþðđħ":
        return (0, ASCENDER_HEIGHT)
    if character in "pqy":
        return (DESCENDER_HEIGHT, X_HEIGHT)
    if character in "ı":
        return (0, 370)
    if character == "i":
        return (0, 620)
    if character in "jȷ":
        return (DESCENDER_HEIGHT, 620 if character == "j" else 370)
    if character == "t":
        return (0, 610)
    if character in DIGITS:
        return (-8, 728) if character in "0689" else (0, CAP_HEIGHT)
    return None


def glyph_name(character: str) -> str:
    return f"uni{ord(character):04X}"


def build_notdef(stroke_width: float):
    pen = TTGlyphPen(None)
    for start, end in zip([(80, -80), (520, -80), (520, 760), (80, 760), (80, -80)], [(520, -80), (520, 760), (80, 760), (80, -80), (520, 760)]):
        add_tapered_stroke(pen, start, end, stroke_width)
    return pen.glyph()


def composite_glyph(
    glyphs: dict[str, object],
    base: str,
    marks: tuple[str, ...],
) -> object:
    pen = TTGlyphPen(glyphs)
    pen.addComponent(glyph_name(base), Transform())
    top_y = 740 if base.isupper() else 540
    if base in "iıjȷ":
        top_y = 635
    top_offset = 0
    bottom_offset = 0
    advance = all_shapes()[base].advance
    for mark in marks:
        if mark in "̧̨̦":
            transform = Transform(dx=advance / 2, dy=bottom_offset)
            bottom_offset -= 95
        else:
            transform = Transform(dx=advance / 2, dy=top_y + top_offset)
            top_offset += 110
        pen.addComponent(glyph_name(mark), transform)
    return pen.glyph()


def feature_source(characters: list[str]) -> str:
    present = set(characters)

    def names(text: str) -> str:
        return " ".join(glyph_name(character) for character in text if character in present)

    top_marks = "̀́̂̃̄̆̇̈̊̋̌"
    bottom_marks = "̧̨̦"
    lines = [
        f"@LeftDiagonal = [{names('AVWY')}];",
        f"@RightDiagonal = [{names('AVWY')}];",
        f"@LeftTop = [{names('TFLP')}];",
        f"@RightRoundUpper = [{names('ACGJOQSU')}];",
        f"@RightRoundLower = [{names('acdegoqsu')}];",
        f"@RightNarrow = [{names('irt')}];",
        "feature kern {",
        "  lookup OpticalOverrides {",
        f"    pos {glyph_name('V')} {glyph_name('a')} -42;",
        f"    pos {glyph_name('W')} {glyph_name('a')} -42;",
        f"    pos {glyph_name('Y')} {glyph_name('o')} -58;",
        "  } OpticalOverrides;",
        "  pos @LeftDiagonal @RightDiagonal -72;",
        "  pos @LeftTop @RightRoundUpper -54;",
        "  pos @LeftTop @RightRoundLower -66;",
        "  pos @LeftDiagonal @RightRoundLower -42;",
        "  pos @LeftDiagonal @RightNarrow -30;",
        f"  pos {glyph_name('L')} @RightDiagonal -58;",
        f"  pos {glyph_name('A')} {glyph_name('T')} -44;",
        f"  pos {glyph_name('L')} {glyph_name('T')} -38;",
        f"  pos {glyph_name('Y')} [{names('aoeuy')}] -58;",
        f"  pos {glyph_name('r')} [{names('oy')}] -22;",
        f"  pos {glyph_name('r')} {glyph_name('t')} -18;",
        f"  pos {glyph_name('T')} {glyph_name('r')} -34;",
        f"  pos {glyph_name('T')} {glyph_name('y')} -48;",
        "} kern;",
    ]
    for mark in top_marks:
        if mark in present:
            lines.append(f"markClass {glyph_name(mark)} <anchor 0 0> @MC_top;")
    for mark in bottom_marks:
        if mark in present:
            lines.append(f"markClass {glyph_name(mark)} <anchor 0 0> @MC_bottom;")
    lines.append("feature mark {")
    for character in sorted(present, key=ord):
        if character in COMBINING_MARKS or not character.isalpha():
            continue
        advance = all_shapes().get(character, all_shapes().get(decomposition_for(character)[0] if decomposition_for(character) else " ")).advance
        top_y = 740 if character.isupper() else 540
        if character in "ijıȷ":
            top_y = 635
        lines.append(f"  pos base {glyph_name(character)} <anchor {advance // 2} {top_y}> mark @MC_top;")
        lines.append(f"  pos base {glyph_name(character)} <anchor {advance // 2} 0> mark @MC_bottom;")
    lines.append("} mark;")
    lines.append("feature mkmk {")
    lines.append(f"  pos mark [{names(top_marks)}] <anchor 0 110> mark @MC_top;")
    lines.append("} mkmk;")
    lines.append("feature ccmp {")
    for character in sorted(present, key=ord):
        decomposition = decomposition_for(character)
        if not decomposition:
            continue
        base, marks = decomposition
        if len(marks) == 1:
            lines.append(f"  sub {glyph_name(base)} {glyph_name(marks[0])} by {glyph_name(character)};")
    lines.append("} ccmp;")
    return "\n".join(lines)


def build_master(weight: int, stroke_width: float, path: Path) -> None:
    shapes = all_shapes()
    target_characters = [chr(codepoint) for codepoint in LATIN_CORE_CODEPOINTS]
    decomposed = {
        character: decomposition_for(character)
        for character in target_characters
        if character not in shapes
    }
    missing = [character for character, value in decomposed.items() if value is None]
    if missing:
        raise ValueError(f"Unconstructable Latin Core characters: {missing!r}")
    direct_characters = sorted(
        set(shapes).intersection(target_characters)
        | {base for base, _ in decomposed.values()}
        | {mark for _, marks in decomposed.values() for mark in marks},
        key=ord,
    )
    composite_characters = sorted(decomposed, key=ord)
    characters = direct_characters + composite_characters
    order = [".notdef"] + [glyph_name(character) for character in characters]
    glyphs = {".notdef": build_notdef(stroke_width)}
    metrics = {".notdef": (600, 40)}
    cmap: dict[int, str] = {}

    for character in direct_characters:
        name = glyph_name(character)
        glyph_shape = shapes[character]
        advance = glyph_shape.advance
        glyph = build_glyph(shapes[character], stroke_width)
        if character not in COMBINING_MARKS:
            glyph = align_glyph(glyph, left_sidebearing_for(character), vertical_bounds_for(character))
        glyphs[name] = glyph
        left_side_bearing = min((point[0] for point in glyph.coordinates), default=0)
        metrics[name] = (advance, left_side_bearing)
        cmap[ord(character)] = name

    for character in composite_characters:
        base, marks = decomposed[character]
        name = glyph_name(character)
        glyphs[name] = composite_glyph(glyphs, base, marks)
        advance = shapes[base].advance
        metrics[name] = (advance, left_sidebearing_for(base))
        cmap[ord(character)] = name

    for character in target_characters:
        cmap[ord(character)] = glyph_name(character)

    style = {100: "Fine", 300: "Signature", 500: "Dense", 700: "Structural"}[weight]
    font = FontBuilder(UPM, isTTF=True)
    font.setupGlyphOrder(order)
    font.setupCharacterMap(cmap)
    font.setupGlyf(glyphs)
    font.setupHorizontalMetrics(metrics)
    font.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    font.setupNameTable(
        {
            "familyName": FAMILY_NAME,
            "styleName": style,
            "uniqueFontIdentifier": f"Strawn {style} {VERSION}",
            "fullName": f"Strawn {style}",
            "psName": f"Strawn-{style}",
            "version": f"Version {VERSION}",
            "manufacturer": "Moriatz Labs",
            "designer": "Moriatz Labs",
            "description": "Moriatz Labs' original tapered toothpick variable typeface.",
            "vendorURL": "https://moriatz.com",
            "licenseDescription": "Licensed under the SIL Open Font License, Version 1.1.",
            "licenseInfoURL": "https://openfontlicense.org",
        }
    )
    font.setupOS2(
        version=4,
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        sTypoLineGap=0,
        usWinAscent=ASCENT,
        usWinDescent=abs(DESCENT),
        usWeightClass=weight,
        sxHeight=X_HEIGHT,
        sCapHeight=CAP_HEIGHT,
        fsSelection=0xC0 if weight == 500 else 0x80,
        fsType=0,
        achVendID="MRTZ",
    )
    ttfont = font.font
    os2 = ttfont["OS/2"]
    os2.panose = Panose(
        bFamilyType=2,
        bSerifStyle=11,
        bWeight={100: 2, 300: 3, 500: 6, 700: 8}[weight],
        bProportion=3,
        bContrast=8,
        bStrokeVariation=2,
        bArmStyle=8,
        bLetterForm=2,
        bMidline=2,
        bXHeight=4,
    )
    os2.ulCodePageRange1 = 1
    os2.ulCodePageRange2 = 0
    os2.ySubscriptXSize = 650
    os2.ySubscriptYSize = 600
    os2.ySubscriptXOffset = 0
    os2.ySubscriptYOffset = 75
    os2.ySuperscriptXSize = 650
    os2.ySuperscriptYSize = 600
    os2.ySuperscriptXOffset = 0
    os2.ySuperscriptYOffset = 350
    os2.yStrikeoutSize = max(32, int(stroke_width * .65))
    os2.yStrikeoutPosition = 300
    font.setupPost(underlinePosition=-150, underlineThickness=50)
    font.setupMaxp()
    ttfont["head"].created = FIXED_FONT_TIMESTAMP
    ttfont["head"].modified = FIXED_FONT_TIMESTAMP
    ttfont["head"].fontRevision = 0.7
    ttfont.recalcTimestamp = False
    gasp = newTable("gasp")
    gasp.gaspRange = {65535: 0x000F}
    ttfont["gasp"] = gasp
    prep = newTable("prep")
    prep.program = Program()
    prep.program.fromBytecode([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D])
    ttfont["prep"] = prep
    for glyph in glyphs.values():
        if getattr(glyph, "numberOfContours", 0) > 0 and getattr(glyph, "flags", None):
            glyph.flags[0] |= flagOverlapSimple
    addOpenTypeFeaturesFromString(ttfont, feature_source(target_characters), filename="Strawn-v0.7.fea")
    ttfont["name"].names = [record for record in ttfont["name"].names if record.platformID != 1]
    font.save(path)


def make_designspace(master_paths: dict[int, Path]) -> Path:
    document = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name = "Weight"
    axis.tag = "wght"
    axis.minimum = 100
    axis.default = 500
    axis.maximum = 700
    axis.map = [(100, 100), (300, 300), (500, 500), (700, 700)]
    document.addAxis(axis)

    for weight, path in master_paths.items():
        source = SourceDescriptor()
        source.name = f"Strawn {weight}"
        source.path = str(path)
        source.location = {"Weight": weight}
        source.familyName = FAMILY_NAME
        source.styleName = {100: "Fine", 300: "Signature", 500: "Dense", 700: "Structural"}[weight]
        if weight == 500:
            source.copyInfo = True
            source.copyLib = True
            source.copyFeatures = True
        document.addSource(source)

    for weight, style_name in {
        100: "Fine",
        300: "Signature",
        400: "Regular",
        500: "Dense",
        700: "Bold",
    }.items():
        instance = InstanceDescriptor()
        instance.name = f"{FAMILY_NAME} {style_name}"
        instance.familyName = FAMILY_NAME
        instance.styleName = style_name
        instance.postScriptFontName = f"{FAMILY_NAME}-{style_name}"
        instance.location = {"Weight": weight}
        document.addInstance(instance)
    structural = InstanceDescriptor()
    structural.name = f"{FAMILY_NAME} Structural"
    structural.familyName = FAMILY_NAME
    structural.styleName = "Structural"
    structural.postScriptFontName = f"{FAMILY_NAME}-Structural"
    structural.location = {"Weight": 700}
    document.addInstance(structural)

    designspace_path = BUILD / "Strawn.designspace"
    document.write(designspace_path)
    return designspace_path


def set_variable_names(font: TTFont) -> None:
    names = font["name"]
    for name_id, value in {
        1: FAMILY_NAME,
        2: "Regular",
        3: f"{FAMILY_NAME} Variable {VERSION}",
        4: FAMILY_NAME,
        5: f"Version {VERSION}",
        6: f"{FAMILY_NAME}-Variable",
        16: FAMILY_NAME,
        17: "Dense",
        25: FAMILY_NAME,
    }.items():
        names.setName(value, name_id, 3, 1, 0x409)


def add_variable_metadata(font: TTFont) -> None:
    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "ordering": 0,
                "values": [
                    {"value": 100, "name": "Fine"},
                    {"value": 300, "name": "Signature"},
                    {"value": 400, "name": "Regular"},
                    {"value": 500, "name": "Dense", "flags": 0x2},
                    {"value": 700, "name": "Bold"},
                    {"value": 700, "name": "Structural"},
                ],
            }
        ],
        elidedFallbackName="Dense",
    )
    name_ids = {
        record.toUnicode(): record.nameID
        for record in font["name"].names
        if record.platformID == 3 and record.langID == 0x409
    }
    for instance in font["fvar"].instances:
        coordinate = round(instance.coordinates["wght"])
        current_label = font["name"].getDebugName(instance.subfamilyNameID)
        label = "Dense" if coordinate == 500 else current_label
        instance.subfamilyNameID = name_ids[label]
        if coordinate == 500:
            instance.postscriptNameID = 6
    avar = newTable("avar")
    avar.segments = {"wght": {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}}
    font["avar"] = avar
    font["head"].created = FIXED_FONT_TIMESTAMP
    font["head"].modified = FIXED_FONT_TIMESTAMP
    font["head"].fontRevision = 0.7
    font.recalcTimestamp = False
    font["name"].names = [record for record in font["name"].names if record.platformID != 1]


def apply_global_master_bounds(font: TTFont, master_paths: dict[int, Path]) -> None:
    masters = [TTFont(path) for path in master_paths.values()]
    head = font["head"]
    head.xMin = min(master["head"].xMin for master in masters)
    head.yMin = min(master["head"].yMin for master in masters)
    head.xMax = max(master["head"].xMax for master in masters)
    head.yMax = max(master["head"].yMax for master in masters)
    hhea = font["hhea"]
    hhea.minLeftSideBearing = min(master["hhea"].minLeftSideBearing for master in masters)
    hhea.minRightSideBearing = min(master["hhea"].minRightSideBearing for master in masters)
    hhea.xMaxExtent = max(master["hhea"].xMaxExtent for master in masters)
    font.recalcBBoxes = False


def write_manifests() -> None:
    metrics = {
        "family": FAMILY_NAME,
        "version": VERSION,
        "unitsPerEm": UPM,
        "capHeight": CAP_HEIGHT,
        "xHeight": X_HEIGHT,
        "ascenderHeight": ASCENDER_HEIGHT,
        "descenderHeight": DESCENDER_HEIGHT,
        "typographicAscent": ASCENT,
        "typographicDescent": DESCENT,
        "weightAxis": {"minimum": 100, "default": 500, "maximum": 700},
        "instances": [
            {"weight": 100, "name": "Fine"},
            {"weight": 300, "name": "Signature"},
            {"weight": 500, "name": "Dense"},
            {"weight": 700, "name": "Structural"},
        ],
        "opticalZones": {
            "capRound": [-12, 732],
            "lowercaseRound": [-10, 530],
        },
    }
    charset = {
        "family": FAMILY_NAME,
        "version": VERSION,
        "repertoire": "GF_Latin_Core",
        "count": len(LATIN_CORE_CODEPOINTS),
        "characters": [
            {
                "character": chr(codepoint),
                "codepoint": f"U+{codepoint:04X}",
                "name": unicodedata.name(chr(codepoint), "UNNAMED"),
            }
            for codepoint in LATIN_CORE_CODEPOINTS
        ],
    }
    (FILES / "Strawn-Metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (FILES / "Strawn-Character-Set.json").write_text(json.dumps(charset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def set_static_names(font: TTFont, style_name: str) -> None:
    legacy_family = FAMILY_NAME if style_name == "Dense" else f"{FAMILY_NAME} {style_name}"
    values = {
        1: legacy_family,
        2: "Regular",
        3: f"{FAMILY_NAME} {style_name} {VERSION}",
        4: f"{FAMILY_NAME} {style_name}",
        5: f"Version {VERSION}",
        6: f"{FAMILY_NAME}-{style_name}",
        16: FAMILY_NAME,
        17: style_name,
    }
    names = font["name"]
    for name_id, value in values.items():
        names.setName(value, name_id, 3, 1, 0x409)
    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "values": [{"value": round(font["OS/2"].usWeightClass), "name": style_name, "flags": 0x2}],
            }
        ],
        elidedFallbackName=style_name,
    )
    names.names = [record for record in names.names if record.platformID != 1]


def write_css() -> None:
    css = """@font-face {
  font-family: \"Strawn\";
  src: url(\"./files/Strawn-Variable.woff2\") format(\"woff2-variations\");
  font-display: swap;
  font-style: normal;
  font-weight: 100 700;
}
"""
    (DIST / "index.css").write_text(css, encoding="utf-8")


def render_specimen(static_font: Path, variable_woff2: Path) -> None:
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "#050505")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(static_font), 230)
    label_font = ImageFont.truetype(str(static_font), 42)

    def centered_text(text: str, y: int, font_object) -> None:
        bounds = draw.textbbox((0, 0), text, font=font_object)
        x = (width - (bounds[2] - bounds[0])) / 2
        draw.text((x, y), text, font=font_object, fill="#f6f6f2")

    centered_text("MORIATZ", 210, font)
    centered_text("LABS", 430, font)
    centered_text("VARIABLE TYPEFACE · LATIN CORE · 100—700", 770, label_font)
    image.save(DOCS / "moriatz-labs-display.png", optimize=True)

    encoded = base64.b64encode(variable_woff2.read_bytes()).decode("ascii")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <style>
    @font-face {{ font-family: "Strawn"; src: url(data:font/woff2;base64,{encoded}) format("woff2"); font-weight: 100 700; }}
    .brand {{ font: 500 230px "Strawn"; fill: #f6f6f2; text-anchor: middle; }}
    .labs {{ font: 500 230px "Strawn"; fill: #f6f6f2; text-anchor: middle; }}
    .meta {{ font: 500 42px "Strawn"; fill: #a3a3a3; text-anchor: middle; }}
  </style>
  <rect width="1600" height="900" fill="#050505"/>
  <text class="brand" x="800" y="390">MORIATZ</text>
  <text class="labs" x="800" y="610">LABS</text>
  <text class="meta" x="800" y="820">VARIABLE TYPEFACE · LATIN CORE · 100—700</text>
</svg>'''
    (DOCS / "moriatz-labs-display.svg").write_text(svg, encoding="utf-8")


def write_specimen_html() -> None:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Strawn specimen</title>
  <link rel="stylesheet" href="../dist/index.css">
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; background: #050505; color: #f5f5f0; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    main { width: min(100% - 2rem, 90rem); margin: auto; padding: 7rem 0; }
    .display { font-family: "Strawn", sans-serif; font-weight: 500; }
    h1 { max-width: 8ch; margin: 0; font-size: clamp(5rem, 17vw, 15rem); line-height: .82; }
    .deck { max-width: 24ch; margin: 5rem 0; font-size: clamp(2.5rem, 7vw, 7rem); line-height: .95; }
    .axis { display: grid; gap: 2rem; padding-top: 4rem; border-top: 1px solid #333; }
    .axis p { margin: 0; font-size: clamp(2rem, 5vw, 5rem); line-height: 1; }
    .hairline { font-weight: 100; } .signature { font-weight: 300; } .dense { font-weight: 500; } .bold { font-weight: 700; }
    small { color: #999; text-transform: uppercase; }
  </style>
</head>
<body>
  <main>
    <small>Original variable system typeface · Moriatz Labs</small>
    <h1 class="display">Moriatz Labs</h1>
    <p class="display deck">Thin ideas. Sharp systems. Useful software.</p>
    <section class="display axis" aria-label="Weight specimens">
      <p class="hairline">100 — Fine</p>
      <p class="signature">300 — Signature</p>
      <p class="dense">500 — Dense</p>
      <p class="bold">700 — Structural</p>
    </section>
  </main>
</body>
</html>
"""
    (DOCS / "specimen.html").write_text(html, encoding="utf-8")


def main() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(DIST, ignore_errors=True)
    BUILD.mkdir(parents=True)
    FILES.mkdir(parents=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    # Dense is the default interface master while the lighter Signature master
    # remains available on the continuous axis.
    master_specs = {100: 32.0, 300: 56.0, 500: 76.0, 700: 96.0}
    master_paths: dict[int, Path] = {}
    for weight, stroke_width in master_specs.items():
        path = BUILD / f"Strawn-{weight}.ttf"
        build_master(weight, stroke_width, path)
        master_paths[weight] = path

    designspace = make_designspace(master_paths)
    variable_font, _, _ = build_variable(designspace)
    set_variable_names(variable_font)
    add_variable_metadata(variable_font)
    apply_global_master_bounds(variable_font, master_paths)
    variable_ttf = FILES / "Strawn-Variable.ttf"
    variable_font.save(variable_ttf)

    variable_woff2 = FILES / "Strawn-Variable.woff2"
    webfont = TTFont(variable_ttf)
    webfont.recalcBBoxes = False
    webfont.recalcTimestamp = False
    webfont.flavor = "woff2"
    webfont.save(variable_woff2)

    static_paths: dict[int, Path] = {}
    for weight, style_name in {
        100: "Fine",
        300: "Signature",
        500: "Dense",
        700: "Structural",
    }.items():
        static_font = instantiateVariableFont(
            TTFont(variable_ttf),
            {"wght": weight},
            inplace=False,
            overlap=OverlapMode.REMOVE,
            updateFontNames=True,
        )
        static_font["head"].created = FIXED_FONT_TIMESTAMP
        static_font["head"].modified = FIXED_FONT_TIMESTAMP
        static_font["head"].fontRevision = 0.7
        static_font.recalcTimestamp = False
        set_static_names(static_font, style_name)
        static_path = FILES / f"Strawn-{style_name}.ttf"
        static_font.save(static_path)
        static_paths[weight] = static_path

    write_css()
    write_hero_wordmark()
    write_manifests()
    write_specimen_html()
    render_specimen(static_paths[500], variable_woff2)
    print(f"Built {variable_ttf.relative_to(ROOT)}")
    print(f"Built {variable_woff2.relative_to(ROOT)}")
    print(f"Rendered {(DOCS / 'moriatz-labs-display.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
