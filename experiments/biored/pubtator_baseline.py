"""PubTator3 on the BioRED 50 sample, written in our output layout so evaluate.py scores it by the same rules.

Usage: python experiments/biored/pubtator_baseline.py
Then:  python experiments/biored/evaluate.py pubtator3

For each sampled PMID the public PubTator3 abstract export (biocjson without full=true, cached under
data/pubtator_abstract/; title and abstract only, the same text BioRED annotates and our method reads) is aligned to the same JATS
blocks our method reads (biomed.pubtator: gene/disease mentions by surface form in the source passage). A gene-disease
pair is a positive prediction when PubTator3 lists a relation for it; everything else is no prediction.
PubTator3 has no evidence, source (novel/background) or uncertain state, so those fields stay empty.
Writes runs/biored50/pubtator3/<paper>/outputs/{entities,mentions,pairs}.csv and source.json.
"""
import csv
import json
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT))
from biomed.jats import parse_article  # noqa: E402
from biomed.io import request_json  # noqa: E402
from biomed.pubtator import API, extract_entities, relation_predictions  # noqa: E402

OUT = HERE.parent / "single_shot" / "runs" / "biored50" / "pubtator3"


def fetch_abstract(pmid):
    cache = HERE / "data" / "pubtator_abstract" / f"{pmid}.json"
    if not cache.exists():
        data = request_json(API + "?" + urllib.parse.urlencode({"pmids": pmid}))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(0.55)
    data = json.loads(cache.read_text(encoding="utf-8"))
    documents = data.get("PubTator3", data.get("documents", [])) if isinstance(data, dict) else data
    return next(d for d in documents if str(d.get("pmid", d.get("id"))) == str(pmid))


def write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    sample = json.loads((HERE / "sample_50.json").read_text(encoding="utf-8"))
    for paper in sample["papers"]:
        article = parse_article(HERE / "papers" / f"{paper['paper_id']}.xml")
        document = fetch_abstract(paper["pmid"])
        entities, rejected = extract_entities(article, document)
        predictions = relation_predictions(document, entities)
        out = OUT / paper["paper_id"] / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        write(out / "entities.csv", [{"entity_id": e["entity_id"], "entity_type": e["entity_type"],
                                      "canonical_name": e["canonical_name"], "external_id": e["external_id"]} for e in entities],
              ["entity_id", "entity_type", "canonical_name", "external_id"])
        write(out / "mentions.csv", [{"entity_id": e["entity_id"], "block_id": m["block_id"], "start": m["start"], "end": m["end"],
                                      "surface": m["text"]} for e in entities for m in e["mentions"]],
              ["entity_id", "block_id", "start", "end", "surface"])
        names = {e["entity_id"]: e["canonical_name"] for e in entities}
        write(out / "pairs.csv", [{"pair_id": f"{g}-{d}", "gene_id": g, "disease_id": d, "gene_name": names[g],
                                   "disease_name": names[d], "status": "supported",
                                   "relation_type": ", ".join(sorted({p["relation_type"] for p in preds})),
                                   "source_scope": "", "reason": f"PubTator3 prediction (score {max(float(p['source_score'] or 0) for p in preds):.2f})"}
                                  for (g, d), preds in sorted(predictions.items())],
              ["pair_id", "gene_id", "disease_id", "gene_name", "disease_name", "status", "relation_type", "source_scope", "reason"])
        (out / "source.json").write_text(json.dumps({"source": API, "pmid": paper["pmid"], "written": datetime.now(timezone.utc).isoformat(),
                                                     "unaligned_annotations": len(rejected)}, indent=2), encoding="utf-8")
        print(f"{paper['paper_id']}: {sum(e['entity_type'] == 'gene' for e in entities)} genes, "
              f"{sum(e['entity_type'] == 'disease' for e in entities)} diseases, {len(predictions)} relations, "
              f"{len(rejected)} unaligned")


if __name__ == "__main__":
    main()
