"""Freeze a 50-abstract sample from the BioRED test set and write each abstract as a minimal JATS file.

Usage: python experiments/biored/prepare.py          (frozen 50-abstract test sample)
       python experiments/biored/prepare.py --all    (every abstract with a gene-disease relation, all splits)

Input: data/BioRED/Test.BioC.JSON from BIORED.zip (NCBI FTP, pub/lu/BioRED; public domain, Luo et al. 2022).
Eligible: test abstracts with at least one gold gene-disease relation (GeneOrGeneProduct x DiseaseOrPhenotypicFeature).
Sample: 50 of them, random.Random(SEED), drawn from the sorted PMID list; written once to sample_50.json and never
redrawn (rerunning checks that the frozen sample still matches).

--all: every Train/Dev/Test abstract with at least one gold gene-disease relation (419), no sampling; the list with each
abstract's split is frozen in sample_all.json and the gold in gold_all.json. Our method never trained or tuned on any split.

The JATS files (papers/PMID<pmid>.xml: title + one abstract paragraph, article-type research-article) let the frozen
single-shot pipeline run unchanged: biomed.jats parses them into the same blocks, sentence IDs and validator checks as
the PMC papers. The gold annotations stay out of the files and out of the prompt.
"""
import hashlib
import json
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT))
from biomed.jats import parse_article  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DATA = HERE / "data"
SOURCE = DATA / "BioRED" / "Test.BioC.JSON"
PAPERS = HERE / "papers"
SAMPLE = HERE / "sample_50.json"
SEED = 20261028
SIZE = 50
GENE, DISEASE = "GeneOrGeneProduct", "DiseaseOrPhenotypicFeature"


def gold(doc):
    """Title, abstract, mentions and gene-disease relations of one BioC document (offsets are document-global)."""
    title, abstract = (p["text"] for p in doc["passages"][:2])
    types, mentions = {}, []
    for passage in doc["passages"]:
        for a in passage["annotations"]:
            for identifier in a["infons"]["identifier"].split(","):
                types.setdefault(identifier, a["infons"]["type"])
            loc = a["locations"][0]
            mentions.append({"identifier": a["infons"]["identifier"], "type": a["infons"]["type"], "text": a["text"],
                             "offset": loc["offset"], "length": loc["length"]})
    relations = []
    for r in doc["relations"]:
        e1, e2 = r["infons"]["entity1"], r["infons"]["entity2"]
        kinds = {types.get(e1), types.get(e2)}
        if kinds == {GENE, DISEASE}:
            gene, disease = (e1, e2) if types.get(e1) == GENE else (e2, e1)
            relations.append({"gene": gene, "disease": disease, "type": r["infons"]["type"], "novel": r["infons"]["novel"]})
    return title, abstract, mentions, relations


def write_jats(pmid, title, abstract):
    PAPERS.mkdir(exist_ok=True)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<article article-type="research-article"><front><article-meta>'
           f'<article-id pub-id-type="pmid">{pmid}</article-id>'
           f'<title-group><article-title>{escape(title)}</article-title></title-group>'
           f'<abstract><p>{escape(abstract)}</p></abstract></article-meta></front><body/></article>\n')
    path = PAPERS / f"PMID{pmid}.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def offset_map(original, parsed):
    """Position in the parsed block for every position in the original text; parsing only collapses whitespace."""
    mapping, j = [], 0
    for ch in original:
        mapping.append(j)
        if j < len(parsed) and ch == parsed[j]:
            j += 1
        elif not ch.isspace():
            raise ValueError(f"parsing changed more than whitespace near {original[max(0, len(mapping) - 20):len(mapping) + 20]!r}")
    mapping.append(j)
    return mapping


def main():
    docs = {d["id"]: d for d in json.loads(SOURCE.read_text(encoding="utf-8"))["documents"]}
    parsed = {pmid: gold(doc) for pmid, doc in docs.items()}
    eligible = sorted(pmid for pmid, g in parsed.items() if g[3])
    picked = sorted(random.Random(SEED).sample(eligible, SIZE), key=int)
    record = {"source": "BIORED.zip (https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/), Test.BioC.JSON",
              "zip_sha256": hashlib.sha256((DATA / "BIORED.zip").read_bytes()).hexdigest(),
              "test_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "criteria": "test abstracts with >= 1 gold gene-disease relation", "seed": SEED,
              "test_abstracts": len(docs), "eligible": len(eligible),
              "papers": [{"paper_id": f"PMID{p}", "pmid": p, "gold_gene_disease": len(parsed[p][3]),
                          "gold_novel": sum(r["novel"] == "Novel" for r in parsed[p][3])} for p in picked]}
    if SAMPLE.exists():
        frozen = json.loads(SAMPLE.read_text(encoding="utf-8"))
        if [p["pmid"] for p in frozen["papers"]] != picked or frozen["test_sha256"] != record["test_sha256"]:
            raise SystemExit("sample_50.json no longer matches the data and seed; refusing to redraw")
    else:
        SAMPLE.write_text(json.dumps(record, indent=2), encoding="utf-8")

    gold_out, mismatches = build_gold(parsed, picked)
    (HERE / "gold_50.json").write_text(json.dumps(gold_out, ensure_ascii=False, indent=1), encoding="utf-8")
    report(f"BioRED test: {len(docs)} abstracts, {len(eligible)} with gene-disease relations; sample {len(picked)} (seed {SEED})",
           gold_out, mismatches, "gold_50.json")


def build_gold(parsed, pmids):
    gold_out, mismatches = {}, []
    for pmid in pmids:
        title, abstract, mentions, relations = parsed[pmid]
        article = parse_article(write_jats(pmid, title, abstract))
        blocks = article["blocks"]
        # Gold offsets are global (title, one space, abstract); map them onto our blocks, whose whitespace parsing
        # may have collapsed, and check that every mention still reads the same.
        starts = {"b0001": 0, "b0002": len(title) + 1}
        texts = {"b0001": title, "b0002": abstract}
        maps = {b["block_id"]: offset_map(texts[b["block_id"]], b["text"]) for b in blocks}
        block_text = {b["block_id"]: b["text"] for b in blocks}
        for m in mentions:
            block_id = "b0001" if m["offset"] < len(title) else "b0002"
            local = m["offset"] - starts[block_id]
            m.update(block_id=block_id, start=maps[block_id][local], end=maps[block_id][local + m["length"]])
            if " ".join(block_text[block_id][m["start"]:m["end"]].split()) != " ".join(m["text"].split()):
                mismatches.append(f"PMID{pmid} mention {m['text']!r} not at its offset")
        gold_out[f"PMID{pmid}"] = {"blocks": [b["block_id"] for b in blocks], "mentions": mentions, "relations": relations}
    return gold_out, mismatches


def report(head, gold_out, mismatches, gold_name):
    rel = [r for g in gold_out.values() for r in g["relations"]]
    print(head)
    print(f"gold gene-disease relations in sample: {len(rel)} "
          f"({', '.join(f'{t} {sum(r['type'] == t for r in rel)}' for t in sorted({r['type'] for r in rel}))}); "
          f"novel {sum(r['novel'] == 'Novel' for r in rel)}")
    print(f"JATS files: {PAPERS}; gold: {HERE / gold_name}; offset/text mismatches: {len(mismatches)}")
    for line in mismatches[:20]:
        print("  " + line)


def main_all():
    parsed, split_of, hashes = {}, {}, {}
    for split in ("Train", "Dev", "Test"):
        path = DATA / "BioRED" / f"{split}.BioC.JSON"
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
        for doc in json.loads(path.read_text(encoding="utf-8"))["documents"]:
            if doc["id"] in parsed:
                raise SystemExit(f"PMID {doc['id']} appears in two splits")
            parsed[doc["id"]], split_of[doc["id"]] = gold(doc), split
    picked = sorted((p for p, g in parsed.items() if g[3]), key=int)
    frozen_50 = {p["pmid"] for p in json.loads(SAMPLE.read_text(encoding="utf-8"))["papers"]}
    record = {"source": "BIORED.zip (https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/), Train/Dev/Test.BioC.JSON",
              "zip_sha256": hashlib.sha256((DATA / "BIORED.zip").read_bytes()).hexdigest(), "split_sha256": hashes,
              "criteria": "every abstract in any split with >= 1 gold gene-disease relation; no sampling",
              "abstracts": len(parsed), "eligible": len(picked),
              "papers": [{"paper_id": f"PMID{p}", "pmid": p, "split": split_of[p], "in_sample_50": p in frozen_50,
                          "gold_gene_disease": len(parsed[p][3]),
                          "gold_novel": sum(r["novel"] == "Novel" for r in parsed[p][3])} for p in picked]}
    path = HERE / "sample_all.json"
    if path.exists():
        frozen = json.loads(path.read_text(encoding="utf-8"))
        if [p["pmid"] for p in frozen["papers"]] != picked or frozen["split_sha256"] != hashes:
            raise SystemExit("sample_all.json no longer matches the data; refusing to rewrite")
    else:
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    gold_out, mismatches = build_gold(parsed, picked)
    (HERE / "gold_all.json").write_text(json.dumps(gold_out, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {s: sum(split_of[p] == s for p in picked) for s in ("Train", "Dev", "Test")}
    report(f"BioRED all splits: {len(parsed)} abstracts, {len(picked)} with gene-disease relations {counts}; "
           f"{len(frozen_50 & set(picked))} already in sample_50", gold_out, mismatches, "gold_all.json")


if __name__ == "__main__":
    main_all() if "--all" in sys.argv[1:] else main()
