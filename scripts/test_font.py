import json
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import flagOverlapSimple
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
FILES = ROOT / "dist" / "files"
VARIABLE = FILES / "Strawn-Variable.ttf"
WOFF2 = FILES / "Strawn-Variable.woff2"
STATICS = {
    100: FILES / "Strawn-Fine.ttf",
    300: FILES / "Strawn-Signature.ttf",
    500: FILES / "Strawn-Dense.ttf",
    700: FILES / "Strawn-Structural.ttf",
}
DISPLAY = ROOT / "documentation" / "moriatz-labs-display.png"
HERO_STROKES = FILES / "Strawn-Hero-Strokes.json"
METRICS = FILES / "Strawn-Metrics.json"
CHARSET = FILES / "Strawn-Character-Set.json"
VERSION = "0.7.0"


def feature_tags(font: TTFont, table: str) -> set[str]:
    return {record.FeatureTag for record in font[table].table.FeatureList.FeatureRecord}


def shaped_advance(text: str, *, kern: bool) -> int:
    face = hb.Face(VARIABLE.read_bytes())
    font = hb.Font(face)
    font.scale = (1000, 1000)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer, {"kern": kern})
    assert all(info.codepoint != 0 for info in buffer.glyph_infos), text
    return sum(position.x_advance for position in buffer.glyph_positions)


def assert_bounds_cover_all_instances(font: TTFont) -> None:
    declared = (font["head"].xMin, font["head"].yMin, font["head"].xMax, font["head"].yMax)
    for weight in (100, 300, 500, 700):
        instance = instantiateVariableFont(TTFont(VARIABLE), {"wght": weight}, inplace=True)
        glyph_set = instance.getGlyphSet()
        for name in instance.getGlyphOrder():
            pen = BoundsPen(glyph_set)
            glyph_set[name].draw(pen)
            if not pen.bounds:
                continue
            x_min, y_min, x_max, y_max = pen.bounds
            assert x_min >= declared[0], (weight, name, pen.bounds, declared)
            assert y_min >= declared[1], (weight, name, pen.bounds, declared)
            assert x_max <= declared[2], (weight, name, pen.bounds, declared)
            assert y_max <= declared[3], (weight, name, pen.bounds, declared)


def main() -> None:
    artifacts = (VARIABLE, WOFF2, *STATICS.values(), DISPLAY, HERO_STROKES, METRICS, CHARSET)
    for artifact in artifacts:
        assert artifact.exists(), f"Missing artifact: {artifact}"
        assert artifact.stat().st_size > 500, f"Artifact is unexpectedly small: {artifact}"

    hero = json.loads(HERO_STROKES.read_text(encoding="utf-8"))
    assert hero["fontVersion"] == VERSION
    assert hero["lines"] == ["STRAWN"]
    assert hero["totalInkLength"] > 0
    assert {stroke["kind"] for stroke in hero["strokes"]} == {"ink", "travel"}
    assert all(stroke["length"] > 0 for stroke in hero["strokes"])

    metrics_manifest = json.loads(METRICS.read_text(encoding="utf-8"))
    charset_manifest = json.loads(CHARSET.read_text(encoding="utf-8"))
    assert metrics_manifest["version"] == VERSION
    assert metrics_manifest["descenderHeight"] == -220
    assert charset_manifest["repertoire"] == "GF_Latin_Core"
    assert charset_manifest["count"] == 319

    font = TTFont(VARIABLE)
    required_tables = {
        "GDEF", "GPOS", "GSUB", "HVAR", "MVAR", "OS/2", "STAT", "cmap",
        "avar", "fvar", "gasp", "glyf", "gvar", "head", "hhea", "hmtx", "name", "post", "prep",
    }
    assert required_tables.issubset(font.keys()), required_tables - set(font.keys())
    assert feature_tags(font, "GPOS") == {"kern", "mark", "mkmk"}
    assert feature_tags(font, "GSUB") == {"ccmp"}

    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    weight = axes["wght"]
    assert (weight.minValue, weight.defaultValue, weight.maxValue) == (100, 500, 700)
    instance_names = [font["name"].getDebugName(instance.subfamilyNameID) for instance in font["fvar"].instances]
    assert instance_names == ["Fine", "Signature", "Regular", "Dense", "Bold", "Structural"], instance_names
    stat_names = [
        font["name"].getDebugName(value.ValueNameID)
        for value in font["STAT"].table.AxisValueArray.AxisValue
    ]
    assert stat_names == ["Fine", "Signature", "Regular", "Dense", "Bold", "Structural"], stat_names

    os2 = font["OS/2"]
    assert os2.version >= 4
    assert os2.fsType == 0
    assert (os2.sxHeight, os2.sCapHeight) == (520, 720)
    assert (os2.sTypoAscender, os2.sTypoDescender) == (900, -260)
    assert any(vars(os2.panose).values())
    assert font["gasp"].gaspRange == {65535: 0x000F}
    assert bytes(font["prep"].program.getBytecode()) == bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D])
    assert abs(font["head"].fontRevision - 0.7) < 0.001

    family_names = {record.toUnicode() for record in font["name"].names if record.nameID in {1, 16}}
    assert family_names == {"Strawn"}
    assert not any("Moriatz Sans" in record.toUnicode() for record in font["name"].names)
    assert f"Version {VERSION}" in {record.toUnicode() for record in font["name"].names if record.nameID == 5}

    cmap = font.getBestCmap()
    expected_codepoints = {
        int(item["codepoint"].removeprefix("U+"), 16)
        for item in charset_manifest["characters"]
    }
    assert set(cmap) == expected_codepoints
    assert len(cmap) == 319

    dense = TTFont(STATICS[500])
    dense_cmap = dense.getBestCmap()
    glyf = dense["glyf"]
    for character in "ABDEHIKLMNPRTUVWXZ":
        glyph = glyf[dense_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (0, 720), (character, glyph.yMin, glyph.yMax)
    for character in "CGOØ":
        glyph = glyf[dense_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (-12, 732), (character, glyph.yMin, glyph.yMax)
    for character in "aceosø":
        glyph = glyf[dense_cmap[ord(character)]]
        assert (glyph.yMin, glyph.yMax) == (-10, 530), (character, glyph.yMin, glyph.yMax)
    for character in "bdhpq":
        glyph = glyf[dense_cmap[ord(character)]]
        expected_top = 720 if character in "bdh" else 520
        expected_bottom = -220 if character in "pq" else 0
        assert (glyph.yMin, glyph.yMax) == (expected_bottom, expected_top), (character, glyph.yMin, glyph.yMax)

    advances_by_weight = {}
    for axis_weight in (100, 300, 500, 700):
        instance = instantiateVariableFont(TTFont(VARIABLE), {"wght": axis_weight}, inplace=True)
        instance_cmap = instance.getBestCmap()
        advances_by_weight[axis_weight] = {
            codepoint: instance["hmtx"].metrics[name][0]
            for codepoint, name in instance_cmap.items()
        }
    assert len({tuple(sorted(advances.items())) for advances in advances_by_weight.values()}) == 1

    expected_kerned_pairs = [
        "AV", "AW", "AT", "FA", "LT", "PA", "TA", "To", "Te", "Ty",
        "Tr", "Va", "Wa", "Yo", "rt", "ry",
    ]
    for pair in expected_kerned_pairs:
        assert shaped_advance(pair, kern=True) < shaped_advance(pair, kern=False), pair

    for sample in (
        "Árvíztűrő tükörfúrógép",
        "Pchnąć w tę łódź jeża lub ośm skrzyń fig",
        "Strawn — 100 € ™ ©",
        "A\u0301 E\u0328 o\u0308",
    ):
        shaped_advance(sample, kern=True)

    for name in font.getGlyphOrder():
        glyph = font["glyf"][name]
        if glyph.numberOfContours > 0:
            assert glyph.flags[0] & flagOverlapSimple, name

    assert_bounds_cover_all_instances(font)
    print("Strawn v0.7 quality checks passed.")


if __name__ == "__main__":
    main()
