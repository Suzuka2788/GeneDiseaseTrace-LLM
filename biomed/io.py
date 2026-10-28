import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in row.items() if key in fields})


def request_json(url, *, timeout=45, retries=2):
    request_headers = {"User-Agent": "NJITLab-literature-pilot/0.1", "Accept": "application/json"}
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            # Do not persist response bodies: providers can include credentials in errors.
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == retries:
                raise RuntimeError(f"HTTP {error.code} from {urllib.parse.urlsplit(url).hostname}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == retries:
                raise RuntimeError(f"Network request failed: {type(error).__name__}") from None
        time.sleep(min(2 ** attempt, 8))
