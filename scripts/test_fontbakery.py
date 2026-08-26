import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FONTBAKERY = Path(sys.executable).with_name("fontbakery.exe" if sys.platform == "win32" else "fontbakery")
FONTS = [
    ROOT / "dist" / "files" / filename
    for filename in (
        "Strawn-Variable.ttf",
        "Strawn-Fine.ttf",
        "Strawn-Signature.ttf",
        "Strawn-Dense.ttf",
        "Strawn-Structural.ttf",
    )
]
ALLOWED_WARNING_CODES = {
    "None",  # FontBakery emits this alongside its informational alt-caron warning.
    "contour-count",  # Static overlap removal changes intersections across weights.
    "decomposed-outline",  # Static instances intentionally decompose accent components.
    "overlapping-path-segments",  # Compatible variable masters retain flagged overlaps.
}


def main() -> None:
    for font in FONTS:
        result = subprocess.run(
            [
                str(FONTBAKERY),
                "check-universal",
                "--skip-network",
                "--succinct",
                "--loglevel",
                "WARN",
                "--error-code-on",
                "FAIL",
                "--jobs",
                "2",
                str(font),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        warning_codes = {
            code.strip()
            for match in re.findall(r"WARN \[([^\]]+)\]", output)
            for code in match.split(",")
        }
        unexpected = warning_codes - ALLOWED_WARNING_CODES
        assert not unexpected, f"Unexpected FontBakery warnings for {font.name}: {unexpected}\n{output}"
    print("FontBakery universal profile passed with only documented warnings.")


if __name__ == "__main__":
    main()
