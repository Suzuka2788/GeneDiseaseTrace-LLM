"""Download the task's public Box archive and extract it inside .Input only."""
import hashlib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://app.box.com/index.php?rm=box_download_shared_file"
       "&shared_name=cf1gqx7eeug8rd5hajno2svt3q94snvv&file_id=f_2400748732646")
EXPECTED_SHA1 = "493c9f112d2ddf6e733f474c1db99a3e6ed08c07"


def main():
    destination = (ROOT / ".Input").resolve()
    destination.mkdir(exist_ok=True)
    archive = destination / "100papers.zip"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(50_000_001)
        if len(data) > 50_000_000:
            raise ValueError("Unexpected archive size")
        if hashlib.sha1(data).hexdigest() != EXPECTED_SHA1:
            raise ValueError("Archive differs from the shared file inspected during setup")
        archive.write_bytes(data)
    if hashlib.sha1(archive.read_bytes()).hexdigest() != EXPECTED_SHA1:
        raise ValueError("Cached archive checksum mismatch")
    with zipfile.ZipFile(archive) as source:
        if sum(item.file_size for item in source.infolist()) > 100_000_000:
            raise ValueError("Archive expands beyond the expected limit")
        for item in source.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Unsafe archive entry")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(item))
    print(f"Ready: {len(list((destination / '100papers').glob('*.xml')))} XML papers")


if __name__ == "__main__":
    main()
