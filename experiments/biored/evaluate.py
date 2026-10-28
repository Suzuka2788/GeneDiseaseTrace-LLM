"""Score a single-shot run on BioRED against the BioRED gold gene-disease relations.

Usage: python experiments/biored/evaluate.py [variant] [run_set]
  variant  default v1_card_lean_medium (or pubtator3)
  run_set  biored50 (default: frozen 50-abstract test sample, gold_50.json)
           biored_all (all 419 abstracts with a gene-disease relation, gold_all.json; also scored per split)

Unit: one (gene concept, disease concept) pair per abstract. Our entities are matched to gold concepts by mention
overlap (same block, overlapping characters), with types checked: our gene <-> GeneOrGeneProduct, our disease-side
targets (disease / clinical_event / ambiguous) <-> DiseaseOrPhenotypicFeature.
- A gold relation is found when one of our supported pairs joins an entity matching its gene with one matching its
  disease. Recall is over gold relations.
- One of our supported pairs is correct when it matches at least one gold relation that way. Precision is over our pairs.
- Strict: every gold relation counts. Scope-adjusted: gold relations whose disease our rules record only as a
  symptom/phenotype (auxiliary table, outside the gene x disease matrix) are set aside and listed.
- Only 'supported' is a positive prediction; uncertain / explicit_negative pairs are reported separately, and a
  second operating point also counts 'uncertain' as positive.
Bootstrap 95% intervals resample abstracts (2,000 draws, fixed seed).
Writes runs/<run_set>/<variant>/biored_eval.json and biored_eval_rows.csv.
"""
import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "single_shot" / "runs"
GOLD = {"biored50": "gold_50.json", "biored_all": "gold_all.json"}
TARGET_TYPES = {"disease", "clinical_event", "ambiguous"}
AUX_TYPES = {"symptom", "phenotype"}
NOVEL = {"this study": "Novel", "both": "Novel", "background": "No"}  # our source scope -> BioRED novelty
SOURCE_EN = {"本研究结果": "this study", "两者兼有": "both", "背景引用": "background", "不确定": "unclear"}

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def overlap(a, b):
    return any(x[0] == y[0] and x[1] < y[2] and y[1] < x[2] for x in a for y in b)


def score_paper(paper_id, gold, out, positive=("supported",)):
    ours = {e["entity_id"]: e for e in read(out / "entities.csv") + read(out / "auxiliary_entities.csv")}
    spans = {}
    for m in read(out / "mentions.csv"):
        spans.setdefault(m["entity_id"], []).append((m["block_id"], int(m["start"]), int(m["end"])))
    gold_spans, gold_type, gold_name = {}, {}, {}
    for m in gold["mentions"]:
        for concept in m["identifier"].split(","):
            gold_spans.setdefault(concept, []).append((m["block_id"], m["start"], m["end"]))
            gold_type[concept] = m["type"]
            gold_name.setdefault(concept, m["text"])

    def kind(oid):
        t = ours[oid]["entity_type"]
        return "gene" if t == "gene" else "target" if t in TARGET_TYPES else "aux" if t in AUX_TYPES else "other"

    # concept -> our entities of the matching kind (and, for diseases, auxiliary entities separately)
    match = {c: {o for o in spans if o in ours and overlap(gold_spans[c], spans[o])} for c in gold_spans}
    genes_of = {c: {o for o in match[c] if kind(o) == "gene"} for c in match}
    targets_of = {c: {o for o in match[c] if kind(o) == "target"} for c in match}
    aux_of = {c: {o for o in match[c] if kind(o) == "aux"} for c in match}

    pairs = read(out / "pairs.csv")
    supported = {(p["gene_id"], p["disease_id"]): p for p in pairs if p["status"] in positive}
    other = {(p["gene_id"], p["disease_id"]): p for p in pairs if p["status"] in {"supported", "uncertain", "explicit_negative"} - set(positive)}
    rows, gold_hit_pairs = [], set()
    for r in gold["relations"]:
        g, d = r["gene"], r["disease"]
        candidates = sorted((a, b) for a in genes_of.get(g, ()) for b in targets_of.get(d, ()))  # sorted: deterministic pick
        hit = [k for k in candidates if k in supported]
        held = [k for k in candidates if k in other]
        gold_hit_pairs |= set(hit)
        if hit:
            outcome, why = "TP", ""
        elif held:
            outcome, why = "FN", "our pair: " + other[held[0]]["status"]
        elif not genes_of.get(g):
            outcome, why = "FN", "gene not recorded by us"
        elif not targets_of.get(d):
            outcome, why = ("FN", "disease recorded by us as symptom/phenotype") if aux_of.get(d) else ("FN", "disease not recorded by us")
        else:
            outcome, why = "FN", "our pair: not_found"
        best = supported[hit[0]] if hit else other[held[0]] if held else None
        rows.append({"paper_id": paper_id, "outcome": outcome, "detail": why,
                     "gold_gene": f"{gold_name.get(g, g)} ({g})", "gold_disease": f"{gold_name.get(d, d)} ({d})",
                     "gold_type": r["type"], "gold_novel": r["novel"],
                     "our_pair": best["pair_id"] if best else "", "our_status": best["status"] if best else "",
                     "our_relation": best["relation_type"] if best else "",
                     "our_source": SOURCE_EN.get(best["source_scope"], best["source_scope"]) if best else "",
                     "our_reason": best["reason"] if best else ""})
    for key, p in supported.items():
        if key in gold_hit_pairs:
            continue
        gene_concepts = [c for c in genes_of if key[0] in genes_of[c] and gold_type[c] == "GeneOrGeneProduct"]
        disease_concepts = [c for c in targets_of if key[1] in targets_of[c] and gold_type[c] == "DiseaseOrPhenotypicFeature"]
        why = ("gold has both concepts but no relation" if gene_concepts and disease_concepts
               else "gene not a gold gene concept" if not gene_concepts and disease_concepts
               else "disease not a gold disease concept" if gene_concepts else "neither entity is a gold concept")
        rows.append({"paper_id": paper_id, "outcome": "FP", "detail": why, "gold_gene": "", "gold_disease": "",
                     "gold_type": "", "gold_novel": "", "our_pair": p["pair_id"],
                     "our_gene": p["gene_name"], "our_disease": p["disease_name"], "our_status": p["status"],
                     "our_relation": p["relation_type"], "our_source": SOURCE_EN.get(p["source_scope"], p["source_scope"]),
                     "our_reason": p["reason"]})
    for row in rows:
        if row["outcome"] != "FP" and row["our_pair"]:
            p = next(x for x in pairs if x["pair_id"] == row["our_pair"])
            row.update(our_gene=p["gene_name"], our_disease=p["disease_name"])
    counts = {"tp_gold": sum(r["outcome"] == "TP" for r in rows),
              "fn": sum(r["outcome"] == "FN" for r in rows),
              "fn_symptom": sum(r["detail"] == "disease recorded by us as symptom/phenotype" for r in rows),
              "our_supported": len(supported),
              "tp_ours": len(gold_hit_pairs),
              "uncertain_or_negative": len(other),
              "uncertain_or_negative_in_gold": sum(r["detail"].startswith("our pair: uncertain") or r["detail"].startswith("our pair: explicit") for r in rows)}
    return counts, rows


def prf(c, scope_adjusted=False):
    gold_total = c["tp_gold"] + c["fn"] - (c["fn_symptom"] if scope_adjusted else 0)
    p = c["tp_ours"] / c["our_supported"] if c["our_supported"] else 0.0
    r = c["tp_gold"] / gold_total if gold_total else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def total(counts):
    return {k: sum(c[k] for c in counts) for k in counts[0]}


def with_ci(counts, papers, adjusted, rng):
    point = prf(total([counts[p] for p in papers]), adjusted)
    draws = [prf(total([counts[rng.choice(papers)] for _ in papers]), adjusted) for _ in range(2000)]
    ci = {}
    for i, name in enumerate(("precision", "recall", "f1")):
        values = sorted(d[i] for d in draws)
        ci[name] = [round(values[49], 3), round(values[1949], 3)]
    return {"precision": round(point[0], 3), "recall": round(point[1], 3), "f1": round(point[2], 3), "ci95": ci}


def main(variant="v1_card_lean_medium", run_set="biored50"):
    gold = json.loads((HERE / GOLD[run_set]).read_text(encoding="utf-8"))
    base = RUNS / run_set / variant
    per_paper, rows, missing = {}, [], []
    for paper_id, g in gold.items():
        out = base / paper_id / "outputs"
        if not (out / "validation.json").exists() and not (out / "source.json").exists():  # source.json: PubTator3 baseline
            missing.append(paper_id)
            continue
        per_paper[paper_id], paper_rows = score_paper(paper_id, g, out)
        rows += paper_rows
    papers = sorted(per_paper)
    rng = random.Random(20261028)
    result = {"variant": variant, "run_set": run_set, "papers_scored": len(papers), "papers_missing": missing}
    # Second operating point: count 'uncertain' as a positive too (no rerun; same outputs).
    per_paper_loose = {p: score_paper(p, gold[p], base / p / "outputs", ("supported", "uncertain"))[0] for p in papers}
    for label, counts, adjusted in (("strict", per_paper, False), ("scope_adjusted", per_paper, True),
                                    ("supported_or_uncertain", per_paper_loose, False)):
        result[label] = with_ci(counts, papers, adjusted, rng)
    if run_set == "biored_all":
        # Same scores per BioRED split; our method never trained on any of them, so they should agree.
        split = {p["paper_id"]: p["split"] for p in json.loads((HERE / "sample_all.json").read_text(encoding="utf-8"))["papers"]}
        result["by_split"] = {}
        for name in ("Train", "Dev", "Test"):
            subset = [p for p in papers if split[p] == name]
            if subset:
                result["by_split"][name] = {"papers": len(subset), "gold": sum(per_paper[p]["tp_gold"] + per_paper[p]["fn"] for p in subset),
                                            "strict": with_ci(per_paper, subset, False, rng),
                                            "supported_or_uncertain": with_ci(per_paper_loose, subset, False, rng)}
    t = total([per_paper[p] for p in papers])
    result["per_paper"] = per_paper
    tp_rows = [r for r in rows if r["outcome"] == "TP" and r["our_source"] in NOVEL]
    novelty_agree = sum(NOVEL[r["our_source"]] == r["gold_novel"] for r in tp_rows)
    result["counts"] = t
    result["novelty"] = {"compared": len(tp_rows), "agree": novelty_agree}
    result["fn_reasons"] = {}
    result["fp_reasons"] = {}
    for r in rows:
        if r["outcome"] in ("FN", "FP"):
            bucket = result["fn_reasons" if r["outcome"] == "FN" else "fp_reasons"]
            bucket[r["detail"]] = bucket.get(r["detail"], 0) + 1
    result["relation_types_on_tp"] = {}
    for r in rows:
        if r["outcome"] == "TP":
            k = f"{r['gold_type']} -> {r['our_relation']}"
            result["relation_types_on_tp"][k] = result["relation_types_on_tp"].get(k, 0) + 1
    (base / "biored_eval.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["paper_id", "outcome", "detail", "gold_gene", "gold_disease", "gold_type", "gold_novel",
              "our_pair", "our_gene", "our_disease", "our_status", "our_relation", "our_source", "our_reason"]
    with (base / "biored_eval_rows.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r.get(k, "") for k in fields} for r in rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:3])
