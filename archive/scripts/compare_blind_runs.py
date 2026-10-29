"""Line up several runs' pair judgments through a hand-made entity crosswalk.

Usage: python archive/scripts/compare_blind_runs.py archive/outputs_blind_comparison/PMC10014009/entity_alignment.json
Writes aligned_pairs.csv next to the crosswalk: one row per aligned gene x target, one status column per run,
plus whether the runs agree. A run without an entity for that concept shows 'absent'.
"""
import csv
import json
import sys
from pathlib import Path


def load_pairs(run_dir):
    with (Path(run_dir) / "pairs.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    return {(r["gene_id"], r.get("disease_id") or r.get("target_id")): r for r in rows}


def main(alignment_path):
    alignment_path = Path(alignment_path)
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    runs = list(alignment["runs"])
    pairs = [load_pairs(path) for path in alignment["runs"].values()]
    rows = []
    for gene, gene_ids in alignment["genes"].items():
        for target, target_ids in alignment["targets"].items():
            row = {"gene": gene, "target": target}
            present = []
            for run, run_pairs, gene_id, target_id in zip(runs, pairs, gene_ids, target_ids):
                record = run_pairs.get((gene_id, target_id)) if target_id else None
                status = record["status"] if record else "absent"
                row[run] = status
                row[f"{run}_relation"] = record["relation_type"] if record else ""
                row[f"{run}_reason"] = (record.get("unresolved_reason") or "") if record else ""
                if record:
                    present.append(status)
            row["agreement"] = ("all_agree" if len(set(present)) == 1 and len(present) == len(runs)
                                else "agree_where_present" if len(set(present)) == 1
                                else "disagree")
            rows.append(row)
    out = alignment_path.parent / "aligned_pairs.csv"
    fields = ["gene", "target"] + [f for run in runs for f in (run, f"{run}_relation", f"{run}_reason")] + ["agreement"]
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for row in rows:
        counts[row["agreement"]] = counts.get(row["agreement"], 0) + 1
    print(f"{out}: {len(rows)} aligned pairs {counts}")
    for row in rows:
        if row["agreement"] != "all_agree" and any(row[r] not in ("not_found", "absent") for r in runs):
            print(f"  {row['gene']:16} | {row['target']:36} | " + " | ".join(f"{r}={row[r]}" for r in runs))


if __name__ == "__main__":
    main(sys.argv[1])
