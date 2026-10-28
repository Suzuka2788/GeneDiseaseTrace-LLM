"""A/B comparison of two variants on the frozen benchmark.

Usage: python experiments/single_shot/compare.py v1_card_lean_medium v3_card_lean_low

Entity IDs differ between runs, so entities are matched by shared written forms (original_names); pairs are then
compared through that mapping. Reports, per paper and in total: cost, time, calls, entity counts, how many
entities match, supported-edge overlap (Jaccard) and status agreement on pairs both variants generated.
Agreement between variants is not accuracy; accuracy needs the human-adjudicated reference set.
Writes runs/ab/compare_<A>_vs_<B>.csv.
"""
import csv
import json
import sys

from common import HERE, RUNS


def read(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def load_run(variant, paper_id):
    run = RUNS / "ab" / variant / paper_id
    out = run / "outputs"
    if not (out / "validation.json").exists():
        return None
    meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
    entities = read(out / "entities.csv")
    for e in entities:
        e["names"] = set(json.loads(e["original_names"] or "[]"))
    pairs = {(p["gene_id"], p["disease_id"]): p["status"] for p in read(out / "pairs.csv")}
    calls = meta["calls"]
    # v1 ran before two parser fixes, so some of its repair calls would not happen today; the first call alone is
    # the like-for-like cost across variants.
    return {"entities": entities, "pairs": pairs, "calls": len(calls),
            "seconds": sum(c["seconds"] for c in calls), "cost": sum(c.get("cost_usd") or 0 for c in calls),
            "first_cost": calls[0].get("cost_usd") or 0, "first_seconds": calls[0]["seconds"]}


def match_entities(a, b):
    """Map B's entity IDs to A's by shared written forms; one-to-one, largest overlap first."""
    candidates = sorted(((len(ea["names"] & eb["names"]), ea["entity_id"], eb["entity_id"])
                         for ea in a for eb in b if ea["entity_type"] == eb["entity_type"] or
                         {ea["entity_type"], eb["entity_type"]} <= {"disease", "clinical_event", "ambiguous"}),
                        reverse=True)
    used_a, mapping = set(), {}
    for overlap, ida, idb in candidates:
        if overlap and ida not in used_a and idb not in mapping:
            used_a.add(ida)
            mapping[idb] = ida
    return mapping


def main(variant_a, variant_b):
    papers = [p["paper_id"] for p in json.loads((HERE / "benchmark_12.json").read_text(encoding="utf-8"))["papers"]]
    rows = []
    for paper_id in papers:
        a, b = load_run(variant_a, paper_id), load_run(variant_b, paper_id)
        if not a or not b:
            rows.append({"paper_id": paper_id, "note": "missing run in A or B"})
            continue
        mapping = match_entities(a["entities"], b["entities"])
        b_pairs = {(mapping.get(g), mapping.get(t)): s for (g, t), s in b["pairs"].items()}
        common = [k for k in a["pairs"] if k in b_pairs]
        agree = sum(a["pairs"][k] == b_pairs[k] for k in common)
        sup_a = {k for k, s in a["pairs"].items() if s == "supported"}
        sup_b = {k for k, s in b_pairs.items() if s == "supported"}
        union = sup_a | sup_b
        rows.append({
            "paper_id": paper_id,
            "cost_a": round(a["cost"], 3), "cost_b": round(b["cost"], 3),
            "first_call_cost_a": round(a["first_cost"], 3), "first_call_cost_b": round(b["first_cost"], 3),
            "first_call_seconds_a": round(a["first_seconds"]), "first_call_seconds_b": round(b["first_seconds"]),
            "seconds_a": round(a["seconds"]), "seconds_b": round(b["seconds"]),
            "calls_a": a["calls"], "calls_b": b["calls"],
            "entities_a": len(a["entities"]), "entities_b": len(b["entities"]), "entities_matched": len(mapping),
            "supported_a": len(sup_a), "supported_b": len(sup_b), "supported_both": len(sup_a & sup_b),
            "supported_jaccard": round(len(sup_a & sup_b) / len(union), 2) if union else 1.0,
            "pairs_compared": len(common), "status_agreement": round(agree / len(common), 3) if common else "",
        })
    out = RUNS / "ab" / f"compare_{variant_a}_vs_{variant_b}.csv"
    fields = list(max(rows, key=len))
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    done = [r for r in rows if "cost_a" in r]
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items()))
    if done:
        total = lambda k: sum(r[k] for r in done)
        print(f"\nA={variant_a}  B={variant_b}  ({len(done)} papers)")
        print(f"cost A {total('cost_a'):.2f} vs B {total('cost_b'):.2f} USD; time A {total('seconds_a')} vs B {total('seconds_b')} s")
        print(f"first call only: cost A {total('first_call_cost_a'):.2f} vs B {total('first_call_cost_b'):.2f} USD; "
              f"time A {total('first_call_seconds_a')} vs B {total('first_call_seconds_b')} s")
        print(f"supported edges A {total('supported_a')}, B {total('supported_b')}, in both {total('supported_both')}; "
              f"status agreement on {total('pairs_compared')} shared pairs: "
              f"{sum(r['status_agreement'] * r['pairs_compared'] for r in done if r['pairs_compared']) / max(1, total('pairs_compared')):.3f}")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
