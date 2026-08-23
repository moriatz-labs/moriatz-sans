from __future__ import annotations

import base64
import math
import shutil
from pathlib import Path

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib import build as build_variable
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DIST = ROOT / "dist"
FILES = DIST / "files"
DOCS = ROOT / "documentation"

UPM = 1000
ASCENT = 820
DESCENT = -220
CAP_HEIGHT = 720
X_HEIGHT = 520
DEFAULT_ADVANCE = 620
VERSION = "0.3.0"

Point = tuple[float, float]
PathStroke = list[Point]
GlyphShape = tuple[int, list[PathStroke], list[Point]]


def shape(
    paths: list[PathStroke] | None = None,
    *,
    advance: int = DEFAULT_ADVANCE,
    dots: list[Point] | None = None,
) -> GlyphShape:
    return advance, paths or [], dots or []


L, C, R = 90, 300, 510
B, M, T = 0, 360, 720

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
    "Q": shape([[(195, T), (405, T), (R, 610), (R, 110), (405, B), (195, B), (L, 110), (L, 610), (195, T)], [(355, 155), (540, -55)]]),
    "R": shape([[(L, B), (L, T), (390, T), (R, 610), (R, 470), (390, M), (L, M)], [(340, M), (R, B)]]),
    "S": shape([[(R, T), (L, T), (L, M), (R, M), (R, B), (L, B)]]),
    "T": shape([[(L, T), (R, T)], [(C, T), (C, B)]]),
    "U": shape([[(L, T), (L, 110), (195, B), (405, B), (R, 110), (R, T)]]),
    "V": shape([[(L, T), (C, B), (R, T)]]),
    "W": shape([[(55, T), (165, B), (300, M), (435, B), (565, T)]], advance=680),
    "X": shape([[(L, T), (R, B)], [(R, T), (L, B)]]),
    "Y": shape([[(L, T), (C, M), (R, T)], [(C, M), (C, B)]]),
    "Z": shape([[(L, T), (R, T), (L, B), (R, B)]]),
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
    "$": shape(UPPER["S"][1] + [[(C, 790), (C, -70)]]),
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
    "@": shape(UPPER["O"][1] + [[(410, 190), (410, 500), (250, 500), (180, 430), (180, 260), (250, 190), (500, 190)]]),
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


def lower_shape(letter: str) -> GlyphShape:
    advance, paths, dots = UPPER[letter.upper()]
    scale = X_HEIGHT / CAP_HEIGHT
    transformed_paths = [
        [((x - L) * scale + 78, y * scale) for x, y in path]
        for path in paths
    ]
    transformed_dots = [((x - L) * scale + 78, y * scale) for x, y in dots]
    return int((advance - 70) * scale + 110), transformed_paths, transformed_dots


def all_shapes() -> dict[str, GlyphShape]:
    result = {**UPPER, **DIGITS, **PUNCT}
    result.update({letter.lower(): lower_shape(letter) for letter in UPPER})
    result[" "] = shape(advance=320)
    return result


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
    taper = min(length * 0.24, max(width * 1.65, 22))
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
    _, paths, dots = shape_data
    pen = TTGlyphPen(None)
    for path in paths:
        for start, end in zip(path, path[1:]):
            add_tapered_stroke(pen, start, end, stroke_width)
    for dot in dots:
        add_diamond(pen, dot, stroke_width)
    return pen.glyph()


def align_glyph(glyph, advance: int, vertical_bounds: tuple[int, int] | None = None):
    """Center sidebearings and normalize declared vertical alignment zones."""
    if not glyph.coordinates:
        return glyph

    coordinates = list(glyph.coordinates)
    x_min = min(point[0] for point in coordinates)
    x_max = max(point[0] for point in coordinates)
    x_offset = (advance - (x_max - x_min)) / 2 - x_min

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


def glyph_name(character: str) -> str:
    return f"uni{ord(character):04X}"


def build_notdef(stroke_width: float):
    pen = TTGlyphPen(None)
    for start, end in zip([(80, -80), (520, -80), (520, 760), (80, 760), (80, -80)], [(520, -80), (520, 760), (80, 760), (80, -80), (520, 760)]):
        add_tapered_stroke(pen, start, end, stroke_width)
    return pen.glyph()


def build_master(weight: int, stroke_width: float, path: Path) -> None:
    shapes = all_shapes()
    characters = sorted(shapes, key=ord)
    order = [".notdef"] + [glyph_name(character) for character in characters]
    glyphs = {".notdef": build_notdef(stroke_width)}
    metrics = {".notdef": (600, 40)}
    cmap: dict[int, str] = {}

    for character in characters:
        name = glyph_name(character)
        advance = shapes[character][0]
        vertical_bounds = None
        if character in UPPER:
            vertical_bounds = (-55, CAP_HEIGHT) if character == "Q" else (0, CAP_HEIGHT)
        elif character.islower():
            vertical_bounds = (-40, X_HEIGHT) if character == "q" else (0, X_HEIGHT)
        elif character in DIGITS:
            vertical_bounds = (0, CAP_HEIGHT)

        glyph = align_glyph(build_glyph(shapes[character], stroke_width), advance, vertical_bounds)
        glyphs[name] = glyph
        left_side_bearing = min((point[0] for point in glyph.coordinates), default=0)
        metrics[name] = (advance, left_side_bearing)
        cmap[ord(character)] = name

    style = {100: "Light", 300: "Regular", 700: "Bold"}[weight]
    font = FontBuilder(UPM, isTTF=True)
    font.setupGlyphOrder(order)
    font.setupCharacterMap(cmap)
    font.setupGlyf(glyphs)
    font.setupHorizontalMetrics(metrics)
    font.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=80)
    font.setupNameTable(
        {
            "familyName": "Moriatz Sans",
            "styleName": style,
            "uniqueFontIdentifier": f"Moriatz Sans {style} {VERSION}",
            "fullName": f"Moriatz Sans {style}",
            "psName": f"MoriatzSans-{style}",
            "version": f"Version {VERSION}",
            "manufacturer": "Moriatz Labs",
            "designer": "Moriatz Labs",
            "description": "A darkened, tapered-stroke system typeface for Moriatz Labs.",
            "vendorURL": "https://moriatz.com",
            "licenseDescription": "Licensed under the SIL Open Font License, Version 1.1.",
            "licenseInfoURL": "https://openfontlicense.org",
        }
    )
    font.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        sTypoLineGap=80,
        usWinAscent=ASCENT,
        usWinDescent=abs(DESCENT),
        usWeightClass=weight,
        sxHeight=X_HEIGHT,
        sCapHeight=CAP_HEIGHT,
        fsSelection=0x40 if weight == 300 else 0,
        achVendID="MRTZ",
    )
    font.setupPost(underlinePosition=-120, underlineThickness=max(18, int(stroke_width)))
    font.setupMaxp()
    font.save(path)


def make_designspace(master_paths: dict[int, Path]) -> Path:
    document = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name = "Weight"
    axis.tag = "wght"
    axis.minimum = 100
    axis.default = 300
    axis.maximum = 700
    axis.map = [(100, 100), (300, 300), (700, 700)]
    document.addAxis(axis)

    for weight, path in master_paths.items():
        source = SourceDescriptor()
        source.name = f"Moriatz Sans {weight}"
        source.path = str(path)
        source.location = {"Weight": weight}
        source.familyName = "Moriatz Sans"
        source.styleName = {100: "Light", 300: "Regular", 700: "Bold"}[weight]
        if weight == 300:
            source.copyInfo = True
            source.copyLib = True
            source.copyFeatures = True
        document.addSource(source)

    designspace_path = BUILD / "MoriatzSans.designspace"
    document.write(designspace_path)
    return designspace_path


def set_variable_names(font: TTFont) -> None:
    names = font["name"]
    for name_id, value in {
        1: "Moriatz Sans Variable",
        2: "Regular",
        3: f"Moriatz Sans Variable {VERSION}",
        4: "Moriatz Sans Variable",
        5: f"Version {VERSION}",
        6: "MoriatzSans-Variable",
    }.items():
        names.setName(value, name_id, 3, 1, 0x409)
        names.setName(value, name_id, 1, 0, 0)


def write_css() -> None:
    css = """@font-face {
  font-family: \"Moriatz Sans Variable\";
  src: url(\"./files/MoriatzSans-Variable.woff2\") format(\"woff2-variations\");
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

    def tracked_text(text: str, y: int, font_object, tracking: int) -> None:
        advances = [draw.textlength(character, font=font_object) for character in text]
        total = sum(advances) + tracking * (len(text) - 1)
        x = (width - total) / 2
        for character, advance in zip(text, advances):
            draw.text((x, y), character, font=font_object, fill="#f6f6f2")
            x += advance + tracking

    tracked_text("MORIATZ", 210, font, 30)
    tracked_text("LABS", 430, font, 52)
    tracked_text("VARIABLE SYSTEM TYPEFACE · 100—700", 770, label_font, 10)
    image.save(DOCS / "moriatz-labs-display.png", optimize=True)

    encoded = base64.b64encode(variable_woff2.read_bytes()).decode("ascii")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <style>
    @font-face {{ font-family: "Moriatz Sans Variable"; src: url(data:font/woff2;base64,{encoded}) format("woff2"); font-weight: 100 700; }}
    .brand {{ font: 300 230px "Moriatz Sans Variable"; letter-spacing: 30px; fill: #f6f6f2; text-anchor: middle; }}
    .labs {{ font: 300 230px "Moriatz Sans Variable"; letter-spacing: 52px; fill: #f6f6f2; text-anchor: middle; }}
    .meta {{ font: 300 42px "Moriatz Sans Variable"; letter-spacing: 10px; fill: #a3a3a3; text-anchor: middle; }}
  </style>
  <rect width="1600" height="900" fill="#050505"/>
  <text class="brand" x="800" y="390">MORIATZ</text>
  <text class="labs" x="800" y="610">LABS</text>
  <text class="meta" x="800" y="820">VARIABLE SYSTEM TYPEFACE · 100—700</text>
</svg>'''
    (DOCS / "moriatz-labs-display.svg").write_text(svg, encoding="utf-8")


def write_specimen_html() -> None:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Moriatz Sans specimen</title>
  <link rel="stylesheet" href="../dist/index.css">
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; background: #050505; color: #f5f5f0; }
    * { box-sizing: border-box; }
    body { margin: 0; }
    main { width: min(100% - 2rem, 90rem); margin: auto; padding: 7rem 0; }
    .display { font-family: "Moriatz Sans Variable", sans-serif; font-weight: 400; letter-spacing: .08em; }
    h1 { max-width: 8ch; margin: 0; font-size: clamp(5rem, 17vw, 15rem); line-height: .82; }
    .deck { max-width: 24ch; margin: 5rem 0; font-size: clamp(2.5rem, 7vw, 7rem); line-height: .95; }
    .axis { display: grid; gap: 2rem; padding-top: 4rem; border-top: 1px solid #333; }
    .axis p { margin: 0; font-size: clamp(2rem, 5vw, 5rem); line-height: 1; }
    .hairline { font-weight: 100; } .regular { font-weight: 300; } .bold { font-weight: 700; }
    small { color: #999; letter-spacing: .12em; text-transform: uppercase; }
  </style>
</head>
<body>
  <main>
    <small>Original variable system typeface · Moriatz Labs</small>
    <h1 class="display">Moriatz Labs</h1>
    <p class="display deck">Thin ideas. Sharp systems. Useful software.</p>
    <section class="display axis" aria-label="Weight specimens">
      <p class="hairline">100 — Fine</p>
      <p class="regular">300 — Signature</p>
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

    # Dark enough to survive common UI sizes while preserving the tapered,
    # skeletal construction. Regular is 2.8x the original 20-unit master.
    master_specs = {100: 32.0, 300: 56.0, 700: 96.0}
    master_paths: dict[int, Path] = {}
    for weight, stroke_width in master_specs.items():
        path = BUILD / f"MoriatzSans-{weight}.ttf"
        build_master(weight, stroke_width, path)
        master_paths[weight] = path

    designspace = make_designspace(master_paths)
    variable_font, _, _ = build_variable(designspace)
    set_variable_names(variable_font)
    variable_ttf = FILES / "MoriatzSans-Variable.ttf"
    variable_font.save(variable_ttf)

    variable_woff2 = FILES / "MoriatzSans-Variable.woff2"
    webfont = TTFont(variable_ttf)
    webfont.flavor = "woff2"
    webfont.save(variable_woff2)

    static_regular = FILES / "MoriatzSans-Regular.ttf"
    shutil.copy2(master_paths[300], static_regular)

    write_css()
    write_specimen_html()
    render_specimen(static_regular, variable_woff2)
    print(f"Built {variable_ttf.relative_to(ROOT)}")
    print(f"Built {variable_woff2.relative_to(ROOT)}")
    print(f"Rendered {(DOCS / 'moriatz-labs-display.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
