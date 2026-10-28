"""Head-to-head comparison of one variant of our method with PubTator3 on the frozen benchmark.

Usage: python experiments/single_shot/compare_pubtator.py v1_card_lean_medium

Neither side is treated as the answer key. Both outputs sit on the same parsed blocks, so entities are aligned by
mention span overlap (same block, overlapping characters) and relations through those aligned entities.
For genes, diseases and gene-disease relations it reports what both systems found, what only PubTator found and
what only our method found. Every relation disagreement is listed with our status, our evidence sentences and
PubTator's prediction, so it can be shown or adjudicated later.

PubTator side: cached PubTator3 annotations aligned to the blocks (outputs/papers/<id>/result.json); its relations are
the pairs with a PubTator3 prediction. Our side: runs/ab/<variant>/<paper>/outputs/.
Writes runs/ab/<variant>/vs_pubtator_summary.csv, vs_pubtator_relations.csv and vs_pubtator_entities.json.
"""
import csv
import json
import re
import sys

from common import HERE, PROJECT, RUNS

TARGET_TYPES = {"disease", "clinical_event", "ambiguous"}
AUX_TYPES = {"symptom", "phenotype"}
RUN_SET = "ab"  # runs/<run set>/<variant>/; "ab" is the 12-paper benchmark
NOTES = {"PMC8626062": "Spanish full text: PubTator found no genes and could not align 55 of its annotations"}


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def spans_of(mentions):
    return [(m["block_id"], int(m["start"]), int(m["end"])) for m in mentions]


def touch(a, b):
    return any(x[0] == y[0] and x[1] < y[2] and y[1] < x[2] for x in a for y in b)


def compare_paper(variant, paper_id):
    out = RUNS / RUN_SET / variant / paper_id / "outputs"
    if not (out / "validation.json").exists():
        return None
    pt = json.loads((PROJECT / "outputs" / "papers" / paper_id / "result.json").read_text(encoding="utf-8"))
    ours = {e["entity_id"]: e for e in read(out / "entities.csv") + read(out / "auxiliary_entities.csv")}
    our_spans = {}
    for m in read(out / "mentions.csv"):
        our_spans.setdefault(m["entity_id"], []).append((m["block_id"], int(m["start"]), int(m["end"])))
    # The lean format lists one written form per symptom/phenotype, so its other occurrences (plural, capitalised)
    # are found here case-insensitively; otherwise PubTator 'diseases' that we keep as symptoms look unmatched.
    blocks = [(b["block_id"], b["text"]) for b in pt["article"]["blocks"]]
    for oid, e in ours.items():
        if e["entity_type"] in AUX_TYPES:
            for name in {e["canonical_name"], *json.loads(e["original_names"] or "[]")}:
                pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"s?(?![A-Za-z0-9])", re.I)
                our_spans.setdefault(oid, []).extend((bid, m.start(), m.end()) for bid, text in blocks for m in pattern.finditer(text))
    pt_spans = {e["entity_id"]: spans_of(e["mentions"]) for e in pt["entities"]}
    pt_type = {e["entity_id"]: ("gene" if e["entity_type"] == "gene" else "disease") for e in pt["entities"]}
    pt_name = {e["entity_id"]: e["canonical_name"] for e in pt["entities"]}

    # Entity alignment: which of our entities each PubTator entity touches, by side.
    link = {pid: {oid for oid, sp in our_spans.items() if touch(pt_spans[pid], sp)} for pid in pt_spans}

    def kind(oid):
        t = ours.get(oid, {}).get("entity_type", "")
        return "gene" if t == "gene" else "target" if t in TARGET_TYPES else "aux" if t in AUX_TYPES else "other"

    entities = {"genes_both": [], "genes_pubtator_only": [], "genes_ours_only": [],
                "diseases_both": [], "diseases_pubtator_only": [], "diseases_ours_only": [],
                "pubtator_disease_is_our_symptom_or_phenotype": []}
    for pid, hits in link.items():
        label = f"{pt_name[pid]} [{'; '.join(sorted({m['text'] for m in next(e for e in pt['entities'] if e['entity_id'] == pid)['mentions']}))}]"
        if pt_type[pid] == "gene":
            entities["genes_both" if any(kind(o) == "gene" for o in hits) else "genes_pubtator_only"].append(label)
        elif any(kind(o) == "target" for o in hits):
            entities["diseases_both"].append(label)
        elif any(kind(o) == "aux" for o in hits):
            entities["pubtator_disease_is_our_symptom_or_phenotype"].append(label)
        else:
            entities["diseases_pubtator_only"].append(label)
    for oid, e in ours.items():
        side = kind(oid)
        if side not in ("gene", "target"):
            continue
        matched = any(oid in link[pid] and pt_type[pid] == ("gene" if side == "gene" else "disease") for pid in link)
        if not matched:
            entities["genes_ours_only" if side == "gene" else "diseases_ours_only"].append(e["canonical_name"])

    # Relations
    our_pairs = {(p["gene_id"], p["disease_id"]): p for p in read(out / "pairs.csv")}
    evidence = {e["evidence_id"]: e for e in read(out / "evidence.csv")}

    def our_evidence(pair):
        ids = json.loads(pair.get("evidence_ids") or "[]")
        return " || ".join(f"{evidence[i]['block_id']}: {evidence[i]['quote'][:300]}" for i in ids if i in evidence)

    rows, pt_keys = [], set()
    for p in pt["pairs"]:
        if not p.get("predictions"):
            continue
        genes = {o for o in link.get(p["gene_id"], ()) if kind(o) == "gene"}
        targets = {o for o in link.get(p["disease_id"], ()) if kind(o) == "target"}
        matches = [our_pairs[(g, t)] for g in genes for t in targets if (g, t) in our_pairs]
        pt_keys |= {(m["gene_id"], m["disease_id"]) for m in matches}
        best = next((m for m in matches if m["status"] == "supported"), matches[0] if matches else None)
        pt_type_label = ", ".join(sorted({x["relation_type"] for x in p["predictions"]}))
        if best and best["status"] == "supported":
            category = "both"
        else:
            category = "pubtator_only"
        as_symptom = any(kind(o) == "aux" for o in link.get(p["disease_id"], ()))
        if best:
            why = "our pair: " + best["status"]
        elif not genes:
            why = "we did not record this gene"
        elif not targets:
            why = ("we record this 'disease' as a symptom/phenotype, not a disease" if as_symptom
                   else "we did not record this disease")
        else:
            why = "no pair"
        rows.append({"paper_id": paper_id, "category": category,
                     "gene": p["gene"], "disease": p["disease"],
                     "our_gene": "; ".join(ours[g]["canonical_name"] for g in genes),
                     "our_disease": "; ".join(ours[t]["canonical_name"] for t in targets),
                     "pubtator_relation": pt_type_label, "pubtator_score": max(float(x.get("source_score") or 0) for x in p["predictions"]),
                     "our_status": best["status"] if best else "", "our_relation": best["relation_type"] if best else "",
                     "our_source": best["source_scope"] if best else "", "detail": why if category != "both" else "",
                     "our_reason": best["reason"] if best else "", "our_evidence": our_evidence(best) if best else "",
                     "matched_supported_pairs": ";".join(sorted(f"{m['pair_id']}|{m['source_scope']}" for m in matches
                                                                if m["status"] == "supported"))})
    for key, pair in our_pairs.items():
        if pair["status"] != "supported" or key in pt_keys:
            continue
        g, t = key
        pt_has = [pid for pid in link if g in link[pid] and pt_type[pid] == "gene"], \
                 [pid for pid in link if t in link[pid] and pt_type[pid] == "disease"]
        detail = ("PubTator has both entities but no relation" if all(pt_has)
                  else "PubTator lacks the gene" if not pt_has[0] and pt_has[1]
                  else "PubTator lacks the disease" if pt_has[0] else "PubTator lacks both entities")
        rows.append({"paper_id": paper_id, "category": "ours_only", "gene": "", "disease": "",
                     "our_gene": ours[g]["canonical_name"], "our_disease": ours[t]["canonical_name"],
                     "pubtator_relation": "", "pubtator_score": "", "our_status": "supported",
                     "our_relation": pair["relation_type"], "our_source": pair["source_scope"], "detail": detail,
                     "our_reason": pair["reason"], "our_evidence": our_evidence(pair), "matched_supported_pairs": ""})
    count = lambda c: sum(r["category"] == c for r in rows)
    summary = {"paper_id": paper_id, "note": NOTES.get(paper_id, ""),
               **{k: len(v) for k, v in entities.items()},
               "relations_both": count("both"), "relations_pubtator_only": count("pubtator_only"),
               "relations_ours_only": count("ours_only"),
               "our_uncertain": sum(p["status"] == "uncertain" for p in our_pairs.values()),
               "our_explicit_negative": sum(p["status"] == "explicit_negative" for p in our_pairs.values())}
    return summary, rows, {"paper_id": paper_id, **entities}


def main(variant, run_set="ab"):
    global RUN_SET
    RUN_SET = run_set
    if run_set == "ab":
        papers = [p["paper_id"] for p in json.loads((HERE / "benchmark_12.json").read_text(encoding="utf-8"))["papers"]]
    else:
        papers = sorted(d.name for d in (RUNS / run_set / variant).glob("PMC*") if (d / "outputs" / "validation.json").exists())
    summaries, relations, entity_lists = [], [], []
    for paper_id in papers:
        result = compare_paper(variant, paper_id)
        if result:
            summaries.append(result[0])
            relations += result[1]
            entity_lists.append(result[2])
    out = RUNS / RUN_SET / variant
    for name, rows in (("vs_pubtator_summary.csv", summaries), ("vs_pubtator_relations.csv", relations)):
        with (out / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (out / "vs_pubtator_entities.json").write_text(json.dumps(entity_lists, ensure_ascii=False, indent=2), encoding="utf-8")
    keys = [k for k in summaries[0] if k not in ("paper_id", "note")]
    for s in summaries:
        print(f"  {s['paper_id']:12} " + " ".join(f"{k.replace('relations_', 'rel_').replace('_pubtator_only', '_PT').replace('_ours_only', '_ours')}={s[k]}"
                                               for k in keys) + (f"  ({s['note']})" if s["note"] else ""))
    total = {k: sum(s[k] for s in summaries) for k in keys}
    print(f"\nOur method ({variant}) vs PubTator3, {len(summaries)} papers:")
    print(f"  genes:    both {total['genes_both']}, PubTator only {total['genes_pubtator_only']}, ours only {total['genes_ours_only']}")
    print(f"  diseases: both {total['diseases_both']}, PubTator only {total['diseases_pubtator_only']}, ours only {total['diseases_ours_only']}; "
          f"PubTator 'diseases' we keep as symptom/phenotype: {total['pubtator_disease_is_our_symptom_or_phenotype']}")
    print(f"  relations: both {total['relations_both']}, PubTator only {total['relations_pubtator_only']}, ours only {total['relations_ours_only']}; "
          f"we also mark {total['our_uncertain']} pairs uncertain and {total['our_explicit_negative']} explicit_negative (PubTator has no such states)")
    print(f"\n{out / 'vs_pubtator_relations.csv'}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
