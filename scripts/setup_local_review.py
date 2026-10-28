"""Download pinned official inference assets into the project's private cache."""
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed.io import read_json, write_json

DEST = ROOT / ".Resource" / "local_llm"
RELEASE = "b11934"
MODEL_REVISION = "7c41481f57cb95916b40956ab2f0b139b296d974"
MODEL_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
MODEL_FILE = "Qwen3-8B-Q4_K_M.gguf"


def download(url, path, size, checksum):
    if path.is_file() and path.stat().st_size == size:
        actual = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
        if actual == checksum:
            print("Verified cached " + path.name, flush=True)
            return
        raise ValueError("Cached file checksum mismatch: " + path.name)
    partial = path.with_suffix(path.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "NJITLab-local-review/0.1"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        append = offset > 0 and response.status == 206
        total = offset if append else 0
        checkpoint = total
        with partial.open("ab" if append else "wb") as stream:
            while chunk := response.read(4 * 1024 * 1024):
                stream.write(chunk)
                total += len(chunk)
                if total - checkpoint >= 256 * 1024 * 1024:
                    print(f"{path.name}: {total / 1e9:.2f}/{size / 1e9:.2f} GB", flush=True)
                    checkpoint = total
    if partial.stat().st_size != size:
        raise ValueError("Downloaded size mismatch: " + path.name)
    with partial.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != checksum:
            raise ValueError("Downloaded checksum mismatch: " + path.name)
    partial.replace(path)
    print("Downloaded and verified " + path.name, flush=True)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    url = f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{RELEASE}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "NJITLab-local-review"}), timeout=30) as response:
        release = json.load(response)
    names = [f"llama-{RELEASE}-bin-win-cuda-12.4-x64.zip", "cudart-llama-bin-win-cuda-12.4-x64.zip"]
    runtime = (DEST / "runtime").resolve()
    runtime.mkdir(exist_ok=True)
    assets = []
    for name in names:
        asset = next(a for a in release["assets"] if a["name"] == name)
        checksum = asset["digest"].removeprefix("sha256:")
        path = DEST / name
        download(asset["browser_download_url"], path, asset["size"], checksum)
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                target = (runtime / item.filename).resolve()
                if not target.is_relative_to(runtime):
                    raise ValueError("Unsafe runtime archive entry")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(item))
        assets.append({"name": name, "sha256": checksum, "url": asset["browser_download_url"]})
    model_url = f"https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/{MODEL_REVISION}/{MODEL_FILE}"
    download(model_url, DEST / MODEL_FILE, 5027783488, MODEL_SHA256)
    write_json(DEST / "assets.json", {"model": "Qwen/Qwen3-8B-GGUF", "revision": MODEL_REVISION,
                                      "model_sha256": MODEL_SHA256, "quantization": "Q4_K_M",
                                      "runtime_release": RELEASE, "runtime_assets": assets})
    print("Local review assets ready.", flush=True)


if __name__ == "__main__":
    main()
