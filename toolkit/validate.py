"""Check a run's output folder against the biomed-gene-disease-evidence data contract.

Usage (from a run folder):   python -m toolkit.validate OUTPUT_DIR input/PAPER.xml
Usage (from the project):    python -m toolkit.validate OUTPUT_DIR XML [--label NAME] [--report PATH]

The same checks run on every model's output, independent of any checks the model wrote itself.
Only structure and quotes are checked; passing says nothing about whether a judgment is right.
Column names differ between models' own formats, so each field is read through a few accepted aliases.
"""
import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from biomed.jats import parse_article

STATUSES = {"supported", "explicit_negative", "uncertain", "not_found"}
RELATION_TYPES = {"association", "correlation", "causal", "none"}
SOURCE_SCOPES = {"背景引用", "本研究结果", "两者兼有", "不确定"}
RULE_HASHES = {
    "1.2.0": {
        "SKILL.md": "8286c118fd11a24c69e6009493cb616b75d5630bf9b019755396b4bfc6803b9f",
        "decision-rules.md": "0204643864c423ec066b9720a583c83443aff88dd87ceab8cb07fbe13f80d506",
        "data-contract.md": "22c98879ce145de87ebe8e6dde6d2c38e2ac434541e2f2c0c3fcb5a9ca262455",
    },
    "1.3.0": {
        "SKILL.md": "8469cd2e3cfd2c9672155957181a43b2463ff448cb0d517655d5c333f924062e",
        "decision-rules.md": "00b8e4fd7b995248d2ac833f4027d992495dc0c7038940ef79a8656d31ae2958",
        "data-contract.md": "f74cffa0fee82711ba58e759066dcc18cceb3430f8bc6641cc31e08a74ed2d4e",
    },
}
GRAPHML = "{http://graphml.graphdrawing.org/xmlns}"


def read_csv(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def field(row, *names):
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return ""


def as_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [part for part in re.split(r"[;,|]\s*", value) if part]
    return parsed if isinstance(parsed, list) else [parsed]


def location(row):
    """Return (block_id, start, end) from a block_id column, a JSON location, or a bare 'b0001'."""
    block, start, end = field(row, "block_id"), field(row, "start"), field(row, "end")
    raw = field(row, "location")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        if isinstance(parsed, dict):
            block = block or parsed.get("block_id", "")
            start = start if start != "" else parsed.get("start", "")
            end = end if end != "" else parsed.get("end", "")
        elif not block:
            found = re.search(r"b\d{4}", str(parsed))
            block = found.group(0) if found else ""
    to_int = lambda v: int(v) if str(v).strip().lstrip("-").isdigit() else None
    return block, to_int(start), to_int(end)


def is_true(value):
    return str(value).strip().lower() in ("true", "1", "yes")


def check(results, name, passed, detail=""):
    results.append({"check": name, "passed": bool(passed), "detail": detail})


def validate(run, xml_path):
    results = []
    blocks = {b["block_id"]: b["text"] for b in parse_article(xml_path)["blocks"]}
    xml_sha = hashlib.sha256(Path(xml_path).read_bytes()).hexdigest()

    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    check(results, "manifest_source_sha256", manifest.get("source_sha256") == xml_sha,
          f"manifest={manifest.get('source_sha256')}")
    rule_hashes = {Path(k).name: v for k, v in (manifest.get("rule_hashes") or {}).items()}
    version = str(manifest.get("rule_version", ""))
    check(results, "manifest_rule_hashes", rule_hashes == RULE_HASHES.get(version),
          f"rule_version={version}; {json.dumps(rule_hashes)}")

    entities = read_csv(run / "entities.csv")
    entity_ids = [field(e, "entity_id", "id") for e in entities]
    check(results, "entity_ids_unique", len(entity_ids) == len(set(entity_ids)))
    primary = [e for e in entities if is_true(field(e, "in_primary_matrix") or "true")]
    genes = {field(e, "entity_id", "id") for e in primary
             if field(e, "entity_type") == "gene" or field(e, "candidate_side") == "gene"}
    targets = {field(e, "entity_id", "id") for e in primary} - genes
    # Multi-study files (R9) pair only within a study unit; a single-unit paper has one unit.
    units = {}
    for e in primary:
        side = "genes" if field(e, "entity_id", "id") in genes else "targets"
        units.setdefault(field(e, "unit_id"), {"genes": set(), "targets": set()})[side].add(field(e, "entity_id", "id"))

    auxiliary_path = run / "auxiliary_entities.csv"
    auxiliary_ids = {field(e, "entity_id", "id") for e in read_csv(auxiliary_path)} if auxiliary_path.exists() else set()
    check(results, "auxiliary_not_in_primary", not (auxiliary_ids & set(entity_ids)),
          ", ".join(sorted(auxiliary_ids & set(entity_ids))))

    mentions = read_csv(run / "mentions.csv")
    bad_mentions = []
    for m in mentions:
        block, start, end = location(m)
        text = blocks.get(block)
        if text is None or start is None or end is None or text[start:end] != field(m, "surface"):
            bad_mentions.append(field(m, "mention_id") or field(m, "surface"))
    check(results, "mention_offsets", not bad_mentions, f"{len(mentions)} mentions; failures={bad_mentions[:10]}"
          + (f" (+{len(bad_mentions) - 10})" if len(bad_mentions) > 10 else ""))

    evidence = read_csv(run / "evidence.csv")
    evidence_ids = {field(e, "evidence_id") for e in evidence}
    missing_quote, bad_offset = [], []
    for e in evidence:
        block, start, end = location(e)
        text, quote = blocks.get(block), field(e, "quote")
        if text is None or quote not in text:
            missing_quote.append(field(e, "evidence_id"))
        elif start is not None and end is not None and text[start:end] != quote:
            bad_offset.append(field(e, "evidence_id"))
    check(results, "evidence_quotes_in_cited_block", not missing_quote, f"{len(evidence)} quotes; missing={missing_quote}")
    check(results, "evidence_offsets", not bad_offset, f"offset mismatches={bad_offset}")
    check(results, "evidence_ids_unique", len(evidence_ids) == len(evidence))

    pairs = read_csv(run / "pairs.csv")
    keys = [(field(p, "gene_id"), field(p, "disease_id", "target_id")) for p in pairs]
    expected = {(g, t) for unit in units.values() for g in unit["genes"] for t in unit["targets"]}
    check(results, "matrix_is_full_product", set(keys) == expected and len(keys) == len(expected),
          f"{len(units)} unit(s); {len(genes)} genes, {len(targets)} targets; expected pairs={len(expected)}; rows={len(keys)}; "
          f"missing={len(expected - set(keys))}; extra={len(set(keys) - expected)}; duplicates={len(keys) - len(set(keys))}")

    enum_errors, rule_errors, dangling = [], [], []
    for p in pairs:
        pid = field(p, "pair_id") or "-".join((field(p, "gene_id"), field(p, "disease_id", "target_id")))
        status, relation, scope = field(p, "status"), field(p, "relation_type"), field(p, "source_scope")
        ids = as_list(field(p, "evidence_ids"))
        if status not in STATUSES or relation not in RELATION_TYPES or (scope and scope not in SOURCE_SCOPES):
            enum_errors.append(pid)
        if status == "supported" and (relation == "none" or not ids):
            rule_errors.append(f"{pid}: supported needs relation type and evidence")
        if status == "explicit_negative" and not ids:
            rule_errors.append(f"{pid}: explicit_negative needs evidence")
        if status == "uncertain" and not as_list(field(p, "unresolved_reason")):
            rule_errors.append(f"{pid}: uncertain needs unresolved_reason")
        if status != "supported" and relation != "none":
            rule_errors.append(f"{pid}: relation_type must be none unless supported")
        dangling += [f"{pid}:{i}" for i in ids if i not in evidence_ids]
    check(results, "pair_enumerations", not enum_errors, f"bad rows={enum_errors}")
    check(results, "pair_status_requirements", not rule_errors, "; ".join(rule_errors))
    check(results, "pair_evidence_ids_exist", not dangling, f"dangling={dangling[:10]}")

    supported = {k for k, p in zip(keys, pairs) if field(p, "status") == "supported"}
    edges = read_csv(run / "edges.csv")
    edge_keys = {(field(e, "gene_id", "source"), field(e, "disease_id", "target")) for e in edges}
    check(results, "edges_csv_equals_supported", edge_keys == supported and len(edges) == len(supported),
          f"edges={len(edges)} supported={len(supported)}")

    graph = ET.parse(run / "graph.graphml").getroot()
    nodes = {n.get("id") for n in graph.iter(f"{GRAPHML}node")}
    graph_edges = {frozenset((e.get("source"), e.get("target"))) for e in graph.iter(f"{GRAPHML}edge")}
    check(results, "graph_nodes_equal_primary_entities", nodes == genes | targets,
          f"nodes={len(nodes)} primary={len(genes | targets)}; extra={sorted(nodes - genes - targets)}; "
          f"missing={sorted((genes | targets) - nodes)}")
    check(results, "graph_edges_equal_supported", graph_edges == {frozenset(k) for k in supported},
          f"graph_edges={len(graph_edges)} supported={len(supported)}")

    statuses = {s: sum(field(p, "status") == s for p in pairs) for s in STATUSES}
    reported = manifest.get("status_counts")
    for key in ("statistics", "counts"):
        block = manifest.get(key) or {}
        reported = block.get("status_counts") or block.get("statuses") or reported
    check(results, "manifest_status_counts", reported is None or all(reported.get(s, 0) == statuses[s] for s in STATUSES),
          f"manifest={reported} actual={statuses}")

    return {"run_dir": str(run), "passed": all(r["passed"] for r in results),
            "genes": len(genes), "targets": len(targets), "pairs": len(pairs), "status_counts": statuses,
            "checks": results,
            "not_checked": ["whether any judgment is biologically or textually correct",
                            "entities missed by the model", "content of result.json beyond what the CSVs and GraphML carry"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("xml", type=Path)
    parser.add_argument("--label", default="")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"label": args.label, **validate(args.run_dir, args.xml)}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.label or args.run_dir}: {'PASSED' if report['passed'] else 'FAILED'} "
          f"({report['genes']} genes x {report['targets']} targets, {report['pairs']} pairs, {report['status_counts']})")
    for r in report["checks"]:
        if not r["passed"]:
            print(f"  FAIL {r['check']}: {r['detail'][:300]}")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
