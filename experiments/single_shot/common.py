"""Shared pieces of the single-shot experiment: paper loading, sentence numbering, paths."""
import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT))
from biomed.jats import parse_article  # noqa: E402

for _stream in (sys.stdout, sys.stderr):  # Chinese messages on a legacy Windows code page
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

RUNS = HERE / "runs"
# Sections that never carry genes or diseases; dropped from the prompt (recorded in the manifest).
BOILERPLATE = re.compile(r"conflicts? of interest|competing interest|author contributions?|funding|acknowledg|"
                         r"ethical publication|data availability|consent for publication", re.I)
ABBREVIATIONS = ("e.g.", "i.e.", "et al.", "Fig.", "Figs.", "vs.", "No.", "approx.", "ca.", "cf.", "Dr.", "St.", "Ref.")
UNSPLIT_TYPES = {"table_row", "title", "section_heading", "table_note"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def paper_path(paper_id):
    if paper_id.startswith("PMID"):  # BioRED abstracts written as JATS by experiments/biored/prepare.py
        return PROJECT / "experiments" / "biored" / "papers" / f"{paper_id}.xml"
    return PROJECT / ".Input" / "100papers" / f"{paper_id}.xml"


def split_sentences(text):
    """Return (start, end) spans; conservative so a quote never straddles a wrong boundary."""
    spans, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z(\[¿¡0-9])", text):
        head = text[start:m.start()]
        if head.endswith(ABBREVIATIONS) or re.search(r"(?:^|\s)[A-Z]\.$", head):
            continue
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def load(paper_id):
    """Parsed article plus sentence index {sentence_id: (block_id, start, end)} for the kept blocks."""
    article = parse_article(paper_path(paper_id))
    kept, dropped, sentences = [], [], {}
    for block in article["blocks"]:
        if BOILERPLATE.search(block["section"]):
            dropped.append(block["block_id"])
            continue
        kept.append(block)
        spans = [(0, len(block["text"]))] if block["content_type"] in UNSPLIT_TYPES else split_sentences(block["text"])
        for n, (s, e) in enumerate(spans, 1):
            sentences[f"{block['block_id']}.s{n}"] = (block["block_id"], s, e)
    return article, kept, dropped, sentences
