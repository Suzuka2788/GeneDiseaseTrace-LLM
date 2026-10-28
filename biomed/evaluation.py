"""Source-grounded development checks, not benchmark accuracy estimates."""
import argparse
import html
import re
from collections import Counter, defaultdict
from pathlib import Path

from .io import digest, read_json, write_json
from .report import shell


def assess(result, reference):
    if result["article"]["source_sha256"] != reference["source_sha256"]:
        raise ValueError("Reference/source mismatch")
    lookup = defaultdict(set)
    for item in reference["entities"]:
        for name in [item["key"], *item["aliases"]]:
            lookup[(item["entity_type"], name.casefold())].add(item["key"])
    mapping, identities, conflicts = {}, defaultdict(list), []
    for entity in result["entities"]:
        kind = entity["entity_type"]
        names = [entity["canonical_name"], *entity["aliases"]]
        matches = set().union(*(lookup[(kind, name.casefold())] for name in names))
        primary = lookup[(kind, entity["canonical_name"].casefold())]
        chosen = primary if len(primary) == 1 else matches
        if len(matches) > 1:
            conflicts.append({"entity_id": entity["entity_id"], "reference_identities": sorted(matches)})
        if len(chosen) == 1:
            key = next(iter(chosen))
            mapping[entity["entity_id"]] = key
            identities[key].append(entity["entity_id"])
    positives = {(mapping[p["gene_id"]], mapping[p["disease_id"]]) for p in result["pairs"]
                 if p["status"] in ("predicted", "supported") and p["gene_id"] in mapping and p["disease_id"] in mapping}
    checks = []
    for item in reference["relation_checks"]:
        present = bool(identities[item["gene"]]) and bool(identities[item["disease"]])
        positive = (item["gene"], item["disease"]) in positives
        checks.append({"gene": item["gene"], "disease": item["disease"],
            "expectation": item["expectation"], "entities_present": present,
            "positive_edge": positive, "passed": (positive if item["expectation"] == "positive" else not positive) if present else None})
    numbered = []
    for entity in result["entities"]:
        suffixes = defaultdict(set)
        for alias in entity["aliases"]:
            match = re.fullmatch(r"([A-Za-z][A-Za-z-]*)([0-9]+)", alias)
            if match:
                suffixes[match[1].casefold()].add(match[2])
        if any(len(values) > 1 for values in suffixes.values()):
            numbered.append(entity["entity_id"])
    pmd = next(e for e in reference["entities"] if e["key"] == "PMD_HLD1")
    pmd_grouped = any(set(n.casefold() for n in pmd["aliases"]) <=
                      {n.casefold() for n in e["aliases"]} for e in result["entities"])
    return {"entity_records": len(result["entities"]), "candidate_pairs": len(result["pairs"]),
        "predicted_edges": sum(p["status"] in ("predicted", "supported") for p in result["pairs"]),
        "entity_presence": {e["key"]: bool(identities[e["key"]]) for e in reference["entities"]},
        "multiple_records_per_reference_concept": {k: ids for k, ids in identities.items() if len(ids) > 1},
        "cross_identity_alias_conflicts": conflicts, "conflicting_numbered_aliases": numbered,
        "PMD_HLD1_aliases_grouped": pmd_grouped, "relation_checks": checks,
        "review_disagreements": sum(p.get("review_agreement") is False for p in result["pairs"]),
        "decisions": dict(Counter(p.get("decision", p["status"]) for p in result["pairs"]))}


def compare(reference, paths, output):
    output = Path(output)
    reports = {name: assess(read_json(path), reference) for name, path in paths.items()}
    document = {"paper_id": reference["paper_id"], "reference_kind": reference["reference_kind"],
        "reference_sha256": digest(reference), "evaluation_scope": "development checks on a paper used to revise workflow; not held-out or expert gold",
        "reports": reports, "no_precision_recall_claim": True}
    write_json(output / "comparison.json", document)
    write_json(output / "reference.json", reference)
    labels = list(reports)
    header = "<tr><th>Check</th>" + "".join(f"<th>{html.escape(n)}</th>" for n in labels) + "</tr>"
    rows = ""
    def row(label, values):
        return "<tr><td>" + html.escape(label) + "</td>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in values) + "</tr>"
    for key in ("entity_records", "candidate_pairs", "predicted_edges", "PMD_HLD1_aliases_grouped"):
        rows += row(key, [reports[n][key] for n in labels])
    for entity in reference["entities"]:
        rows += row("Entity present: " + entity["key"], [reports[n]["entity_presence"][entity["key"]] for n in labels])
    rows += row("Cross-identity alias conflicts", [len(reports[n]["cross_identity_alias_conflicts"]) for n in labels])
    rows += row("Conflicting numbered aliases", [len(reports[n]["conflicting_numbered_aliases"]) for n in labels])
    for i, item in enumerate(reference["relation_checks"]):
        rows += row(item["gene"] + " / " + item["disease"] + " (" + item["expectation"] + ")",
            ["not assessable: entity missing" if reports[n]["relation_checks"][i]["passed"] is None else
             ("pass" if reports[n]["relation_checks"][i]["passed"] else "fail") for n in labels])
    body = "<h1>PMC6240673 · Workflow comparison</h1><div class='notice'>Development sample used to revise the workflow. Reference prepared by the assistant from source text; not expert gold or a held-out benchmark. No accuracy/recall claim.</div>"
    body += "<p>Counts are provisional entity records and model-predicted edges, not verified biological facts.</p>"
    body += f"<table>{header}{rows}</table><h2>Reference evidence</h2>"
    for item in reference["relation_checks"]:
        body += f"<h3>{html.escape(item['gene'])} / {html.escape(item['disease'])}</h3><p>{html.escape(item['note'])}</p>"
        body += "".join(f"<p>{e['block_id']}</p><blockquote>{html.escape(e['quote'])}</blockquote>" for e in item["evidence"])
    body += "<p>Multiple records per reference concept may reflect unresolved ortholog scope; inspect species metadata before merging.</p>"
    (output / "index.html").write_text(shell("Workflow comparison", body), encoding="utf-8")
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compare(read_json(args.reference), {"PubTator": args.baseline, "Qwen direct": args.old,
                                     "Qwen reviewed": args.new}, args.output)


if __name__ == "__main__":
    main()
