import json
from pathlib import Path

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
VARIABLE = ROOT / "dist" / "files" / "MoriatzSans-Variable.ttf"
WOFF2 = ROOT / "dist" / "files" / "MoriatzSans-Variable.woff2"
REGULAR = ROOT / "dist" / "files" / "MoriatzSans-Regular.ttf"
DISPLAY = ROOT / "documentation" / "moriatz-labs-display.png"
HERO_STROKES = ROOT / "dist" / "files" / "MoriatzSans-Hero-Strokes.json"


def main() -> None:
    for artifact in (VARIABLE, WOFF2, REGULAR, DISPLAY, HERO_STROKES):
        assert artifact.exists(), f"Missing artifact: {artifact}"
        assert artifact.stat().st_size > 500, f"Artifact is unexpectedly small: {artifact}"

    hero = json.loads(HERO_STROKES.read_text(encoding="utf-8"))
    assert hero["fontVersion"] == "0.6.1"
    assert hero["lines"] == ["MORIATZ", "SANS"]
    assert hero["totalInkLength"] > 0
    assert {stroke["kind"] for stroke in hero["strokes"]} == {"ink", "travel"}
    assert all(stroke["length"] > 0 for stroke in hero["strokes"])

    font = TTFont(VARIABLE)
    required_tables = {"cmap", "fvar", "gvar", "glyf", "head", "hhea", "hmtx", "name", "OS/2", "post"}
    assert required_tables.issubset(font.keys()), required_tables - set(font.keys())

    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    weight = axes["wght"]
    assert (weight.minValue, weight.defaultValue, weight.maxValue) == (100, 500, 700)

    cmap = font.getBestCmap()
    for character in "Moriatz LabsABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?@#%&·–—":
        assert ord(character) in cmap, f"Missing character: {character!r}"

    family_names = {
        record.toUnicode()
        for record in font["name"].names
        if record.nameID == 1
    }
    assert "Moriatz Sans Variable" in family_names
    version_names = {record.toUnicode() for record in font["name"].names if record.nameID == 5}
    assert "Version 0.6.1" in version_names

    regular = TTFont(REGULAR)
    regular_cmap = regular.getBestCmap()
    glyf = regular["glyf"]
    for character in "ABCDEFGHIJKLMNOPRSTUVWXYZ":
        glyph = glyf[regular_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (0, 720), (character, glyph.yMin, glyph.yMax)
    assert (glyf[regular_cmap[ord("Q")]].yMin, glyf[regular_cmap[ord("Q")]].yMax) == (-220, 720)
    for character in "acemnorsuvwxz":
        glyph = glyf[regular_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (0, 520), (character, glyph.yMin, glyph.yMax)
    for character in "bdfhkl":
        glyph = glyf[regular_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (0, 720), (character, glyph.yMin, glyph.yMax)
    for character in "gpqy":
        glyph = glyf[regular_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (-220, 520), (character, glyph.yMin, glyph.yMax)
    assert (glyf[regular_cmap[ord("i")]].yMin, glyf[regular_cmap[ord("i")]].yMax) == (0, 620)
    assert (glyf[regular_cmap[ord("j")]].yMin, glyf[regular_cmap[ord("j")]].yMax) == (-220, 620)
    assert (glyf[regular_cmap[ord("t")]].yMin, glyf[regular_cmap[ord("t")]].yMax) == (0, 610)
    h_glyph = glyf[regular_cmap[ord("h")]]
    n_glyph = glyf[regular_cmap[ord("n")]]
    assert h_glyph.yMax - n_glyph.yMax >= 200, (h_glyph.yMax, n_glyph.yMax)
    k_glyph = glyf[regular_cmap[ord("k")]]
    assert max(y for x, y in k_glyph.coordinates if x > 250) < 600
    for character in "bhp":
        glyph = glyf[regular_cmap[ord(character)]]
        assert max(y for x, y in glyph.coordinates if x > 250) < 500, character
    for character in "dq":
        glyph = glyf[regular_cmap[ord(character)]]
        assert max(y for x, y in glyph.coordinates if x < 350) < 500, character
    for character in "0123456789":
        glyph = glyf[regular_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (0, 720), (character, glyph.yMin, glyph.yMax)

    horizontal_metrics = regular["hmtx"].metrics
    for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
        glyph_name = regular_cmap[ord(character)]
        glyph = glyf[glyph_name]
        advance, left_side_bearing = horizontal_metrics[glyph_name]
        right_side_bearing = advance - glyph.xMax
        assert abs(left_side_bearing - right_side_bearing) <= 1, (
            character,
            left_side_bearing,
            right_side_bearing,
        )
    print("Moriatz Sans quality checks passed.")


if __name__ == "__main__":
    main()
