from pathlib import Path

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
VARIABLE = ROOT / "dist" / "files" / "MoriatzSans-Variable.ttf"
WOFF2 = ROOT / "dist" / "files" / "MoriatzSans-Variable.woff2"
REGULAR = ROOT / "dist" / "files" / "MoriatzSans-Regular.ttf"
DISPLAY = ROOT / "documentation" / "moriatz-labs-display.png"


def main() -> None:
    for artifact in (VARIABLE, WOFF2, REGULAR, DISPLAY):
        assert artifact.exists(), f"Missing artifact: {artifact}"
        assert artifact.stat().st_size > 1000, f"Artifact is unexpectedly small: {artifact}"

    font = TTFont(VARIABLE)
    required_tables = {"cmap", "fvar", "gvar", "glyf", "head", "hhea", "hmtx", "name", "OS/2", "post"}
    assert required_tables.issubset(font.keys()), required_tables - set(font.keys())

    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    weight = axes["wght"]
    assert (weight.minValue, weight.defaultValue, weight.maxValue) == (100, 300, 700)

    cmap = font.getBestCmap()
    for character in "Moriatz LabsABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?@#%&·–—":
        assert ord(character) in cmap, f"Missing character: {character!r}"

    family_names = {
        record.toUnicode()
        for record in font["name"].names
        if record.nameID == 1
    }
    assert "Moriatz Sans Variable" in family_names
    print("Moriatz Sans quality checks passed.")


if __name__ == "__main__":
    main()
