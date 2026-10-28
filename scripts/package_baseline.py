"""Create an offline, reproducible snapshot without temporary web/session data."""
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed import __version__


def main():
    target = ROOT / f"NJITLab_baseline_v{__version__}.zip"
    files = [ROOT / name for name in ("README.md", "config.json", "run.ps1", ".gitignore", "requirements-figures.txt")]
    for folder in ("biomed", "scripts", "tests", ".Input", "cache", "outputs"):
        files.extend(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Archive CRC failed: {bad}")
    print(f"{target.name}: {target.stat().st_size / 1e6:.1f} MB, {len(files)} files; CRC verified")


if __name__ == "__main__":
    main()
