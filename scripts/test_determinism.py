import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build.py"


def artifact_hashes() -> dict[str, str]:
    files = sorted((ROOT / "dist" / "files").glob("*"))
    files.extend(sorted((ROOT / "documentation").glob("moriatz-labs-display.*")))
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
        if path.is_file()
    }


def build() -> None:
    subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=ROOT, check=True, capture_output=True)


def main() -> None:
    build()
    first = artifact_hashes()
    build()
    second = artifact_hashes()
    assert first == second, {
        path: (first.get(path), second.get(path))
        for path in sorted(first.keys() | second.keys())
        if first.get(path) != second.get(path)
    }
    print("Strawn builds are deterministic.")


if __name__ == "__main__":
    main()
