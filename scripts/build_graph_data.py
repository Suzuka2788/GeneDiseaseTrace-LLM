"""Per-paper gene–disease bipartite graphs for the public site (called by build_site.py).

Writes site/graphs/full100.json and site/graphs/biored.json; site/graphs/index.html renders them.
- full100: every gene and disease-side entity in each paper's primary matrix, and every pair our method did not mark
  not_found (supported, uncertain, explicit_negative), with its source label and first evidence sentence.
- biored: our graph for each of the 419 abstracts overlaid on the BioRED gold relations: our supported pairs that are
  in the gold set, our supported pairs that are not, and gold relations we did not report (with the reason, from
  evaluate.py's rows). Gold-only entities get their own nodes, named as BioRED tagged them.
- merged100: all supported links of the 100 papers in one graph (site/graphs/merged.html), entities merged by
  normalized name; each link and entity lists the papers behind it.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
RUNS = PROJECT / "experiments" / "single_shot" / "runs"
BIORED = PROJECT / "experiments" / "biored"
TARGET_TYPES = {"disease", "clinical_event", "ambiguous"}
SOURCE = {"本研究结果": "this study", "两者兼有": "both", "背景引用": "background", "不确定": "unclear"}
QUOTE_CHARS = 280


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def paper_graph(out):
    """Nodes and non-empty pairs of one run folder's outputs."""
    entities = read(out / "entities.csv")
    nodes = [{"id": e["entity_id"], "side": "g" if e["entity_type"] == "gene" else "d", "name": e["canonical_name"]}
             for e in entities if e["entity_type"] == "gene" or e["entity_type"] in TARGET_TYPES]
    evidence = {e["evidence_id"]: e["quote"] for e in read(out / "evidence.csv")}
    edges = []
    for p in read(out / "pairs.csv"):
        if p["status"] == "not_found":
            continue
        ids = json.loads(p["evidence_ids"] or "[]")
        quote = next((evidence[i] for i in ids if i in evidence), "")
        edges.append({"pair": p["pair_id"], "g": p["gene_id"], "d": p["disease_id"], "status": p["status"],
                      "rel": p["relation_type"], "src": SOURCE.get(p["source_scope"], p["source_scope"]),
                      "why": p["reason"], "quote": quote[:QUOTE_CHARS] + ("…" if len(quote) > QUOTE_CHARS else "")})
    return nodes, edges


def full100():
    with (PROJECT / "outputs" / "inventory.csv").open(encoding="utf-8-sig") as stream:
        inventory = {r["paper_id"]: r for r in csv.DictReader(stream)}
    papers = []
    for folder in sorted((RUNS / "full100" / "v1_card_lean_medium").glob("PMC*")):
        nodes, edges = paper_graph(folder / "outputs")
        info = inventory[folder.name]
        papers.append({"id": folder.name, "title": info["title"], "type": info["article_type"], "nodes": nodes, "edges": edges})
    return {"dataset": "full100", "papers": papers}


def biored():
    sample = json.loads((BIORED / "sample_all.json").read_text(encoding="utf-8"))
    docs = {d["id"]: d for split in ("Train", "Dev", "Test")
            for d in json.loads((BIORED / "data" / "BioRED" / f"{split}.BioC.JSON").read_text(encoding="utf-8"))["documents"]}
    base = RUNS / "biored_all" / "v1_card_lean_medium"
    rows = {}
    for r in read(base / "biored_eval_rows.csv"):
        rows.setdefault(r["paper_id"], []).append(r)
    strip = lambda name: re.sub(r"\s*\([^()]*\)$", "", name)  # "SCN5A (6331)" -> "SCN5A"
    papers = []
    for p in sample["papers"]:
        nodes, edges = paper_graph(base / p["paper_id"] / "outputs")
        # The scorer lists every supported pair that matches no gold relation as an FP row; a TP row names only one
        # of possibly several matching pairs, so 'confirmed' is every supported pair not listed as FP.
        not_in_gold = {r["our_pair"] for r in rows.get(p["paper_id"], []) if r["outcome"] == "FP"}
        kept = []
        for e in edges:
            if e["status"] == "supported":
                e["status"] = "fp" if e["pair"] in not_in_gold else "tp"
                kept.append(e)
        by_name = {(n["side"], n["name"].lower()): n["id"] for n in nodes}
        pair_ends = {e["pair"]: (e["g"], e["d"]) for e in edges}
        for r in rows.get(p["paper_id"], []):
            if r["outcome"] != "FN":
                continue
            if r["our_pair"] in pair_ends:  # we judged this pair uncertain / explicit_negative: draw it on our nodes
                g, d = pair_ends[r["our_pair"]]
                kept.append({"pair": r["our_pair"], "g": g, "d": d, "status": "fn", "rel": r["gold_type"],
                             "src": "novel" if r["gold_novel"] == "Novel" else "not novel", "why": r["detail"], "quote": ""})
                continue
            ends = []
            for side, name in (("g", strip(r["gold_gene"])), ("d", strip(r["gold_disease"]))):
                key = (side, name.lower())
                if key not in by_name:
                    by_name[key] = f"X{len(by_name)}"
                    nodes.append({"id": by_name[key], "side": side, "name": name, "gold_only": True})
                ends.append(by_name[key])
            kept.append({"pair": "", "g": ends[0], "d": ends[1], "status": "fn", "rel": r["gold_type"],
                         "src": "novel" if r["gold_novel"] == "Novel" else "not novel", "why": r["detail"], "quote": ""})
        papers.append({"id": p["paper_id"], "title": docs[p["pmid"]]["passages"][0]["text"], "type": p["split"],
                       "nodes": nodes, "edges": kept})
    return {"dataset": "biored", "papers": papers}


def merge_key(name):
    """Entities are merged across papers by normalized name only (no database IDs): case, dashes, apostrophes, spaces."""
    name = unicodedata.normalize("NFKC", name).lower().strip()
    name = re.sub(r"[‐-―−]", "-", name)
    name = re.sub(r"[‘’`']", "'", name)
    return re.sub(r"\s+", " ", name)


def merged(per_paper):
    """One graph over all papers: supported links merged by entity name; weight = number of papers."""
    nodes, edges = {}, {}
    for p in per_paper["papers"]:
        name = {n["id"]: (n["side"], n["name"]) for n in p["nodes"]}
        for e in p["edges"]:
            if e["status"] != "supported":
                continue
            ends = []
            for node_id in (e["g"], e["d"]):
                side, label = name[node_id]
                key = f"{side}:{merge_key(label)}"
                node = nodes.setdefault(key, {"id": key, "side": side, "spellings": {}, "papers": set()})
                node["spellings"][label] = node["spellings"].get(label, 0) + 1
                node["papers"].add(p["id"])
                ends.append(key)
            edge = edges.setdefault(tuple(ends), {"g": ends[0], "d": ends[1], "papers": {}})
            edge["papers"].setdefault(p["id"], {"paper": p["id"], "src": e["src"], "rel": e["rel"], "quote": e["quote"]})
    titles = {p["id"]: p["title"] for p in per_paper["papers"]}
    out_nodes = [{"id": n["id"], "side": n["side"], "name": max(n["spellings"], key=lambda s: (n["spellings"][s], s)),
                  "aka": sorted(n["spellings"]), "papers": sorted(n["papers"])} for n in nodes.values()]
    out_edges = [{"g": e["g"], "d": e["d"], "papers": list(e["papers"].values())} for e in edges.values()]
    return {"dataset": "merged100", "titles": titles, "nodes": out_nodes, "edges": out_edges}


def build(site):
    folder = site / "graphs"
    folder.mkdir(parents=True, exist_ok=True)
    papers = full100()
    for name, data in (("full100", papers), ("biored", biored()), ("merged100", merged(papers))):
        (folder / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for page, template in (("index.html", "graph_viewer.html"), ("merged.html", "merged_viewer.html")):
        (folder / page).write_text((Path(__file__).with_name(template)).read_text(encoding="utf-8"), encoding="utf-8")
