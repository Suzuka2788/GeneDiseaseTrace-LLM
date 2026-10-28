"""Turn the model's judgments.json into every deliverable file, then validate them.

Usage:
  python -m toolkit.build judgments.json --check   # report problems only, write nothing
  python -m toolkit.build judgments.json           # write outputs/<paper>/rules-<version>/<run_id>/

The model decides entities, evidence and judgments; this script locates mentions, computes offsets,
fills every pair the model did not list as not_found, enforces the data contract and renders the files.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from biomed.io import write_csv, write_json

from . import VERSION
from .common import (ASSERTION_KINDS, AUXILIARY_TYPES, DIRECTION, DISPLAY_PRIORITY, ENTITY_TYPES, EVIDENCE_SPECIES,
                     FINDING_TYPES, IDENTITY_ISSUES, IDENTITY_STATUS, IMPACT, RELATION_ASSERTED, RELATION_TYPES,
                     RESOLUTION, SIGNIFICANCE, SOURCE_SCOPES, STAT_AVAILABILITY, STATUSES, SUPPORT_BASIS,
                     UNRESOLVED_REASONS, block_range, load_article, rule_info, sha256)
from .render import graph_svg, graphml, preview
from .validate import validate

DEFAULT_NOT_FOUND = ("No statement, result or analysis in the checked text links this gene to this target; "
                     "co-occurrence in the same paper is not evidence.")


class Problems(list):
    def add(self, where, message):
        self.append(f"{where}: {message}")


def as_list(value):
    if value in (None, ""):
        return []
    return value if isinstance(value, list) else [value]


def check_enum(problems, where, name, value, allowed, required=True):
    if value in (None, "") and not required:
        return
    if value not in allowed:
        problems.add(where, f"{name}={value!r} not in {sorted(allowed)}")


def boundary_pattern(surface, ignore_case):
    body = re.escape(surface)
    if surface[:1].isalnum():
        body = r"(?<![A-Za-z0-9])" + body
    if surface[-1:].isalnum():
        body += r"(?![A-Za-z0-9])"
    return re.compile(body, re.I if ignore_case else 0)


def locate_mentions(entities, unit_blocks, blocks, problems):
    """Find every surface form of every entity inside its unit; longest match wins where forms overlap."""
    candidates = []
    for e in entities:
        for form in e["surface_forms"]:
            spec = form if isinstance(form, dict) else {"surface": form}
            surface = spec.get("surface", "")
            if not surface:
                problems.add(e["entity_id"], "empty surface form")
                continue
            pattern = boundary_pattern(surface, spec.get("ignore_case", False))
            for block_id in unit_blocks[e["unit_id"]]:
                for m in pattern.finditer(blocks[block_id]["text"]):
                    candidates.append((block_id, m.start(), m.end(), e, spec.get("role")))
    candidates.sort(key=lambda c: c[1] - c[2])
    taken, mentions = {}, []
    for block_id, start, end, e, role in candidates:
        spans = taken.setdefault(block_id, [])
        if any(start < s_end and s_start < end for s_start, s_end in spans):
            continue
        spans.append((start, end))
        mentions.append(mention_row(e, block_id, start, end, blocks, role or e.get("default_mention_role") or e["entity_type"]))
    for e in entities:
        for extra in as_list(e.get("extra_mentions")):
            text = blocks.get(extra.get("block_id"), {}).get("text", "")
            surface, nth = extra.get("surface", ""), int(extra.get("occurrence", 1))
            starts = [m.start() for m in re.finditer(re.escape(surface), text)] if surface else []
            if len(starts) < nth:
                problems.add(e["entity_id"], f"extra mention {surface!r} occurrence {nth} not found in {extra.get('block_id')}")
                continue
            row = mention_row(e, extra["block_id"], starts[nth - 1], starts[nth - 1] + len(surface), blocks,
                              extra.get("mention_role", "local_coreference"))
            row["contextual_referent"] = extra.get("contextual_referent", "")
            row["coreference_path"] = extra.get("coreference_path", "")
            mentions.append(row)
    mentions.sort(key=lambda m: (m["block_id"], m["start"]))
    for number, m in enumerate(mentions, 1):
        m["mention_id"] = f"M{number:05d}"
    return mentions


def mention_row(e, block_id, start, end, blocks, role):
    text = blocks[block_id]["text"]
    return {"mention_id": "", "paper_id": e["paper_id"], "unit_id": e["unit_id"], "entity_id": e["entity_id"],
            "surface": text[start:end], "entity_type": e["entity_type"], "mention_role": role, "block_id": block_id,
            "section": blocks[block_id]["section"], "start": start, "end": end,
            "location": json.dumps({"block_id": block_id, "start": start, "end": end}),
            "context": text[max(0, start - 80):end + 80], "contextual_referent": "", "coreference_path": ""}


def build(judgments_path, check_only):
    problems = Problems()
    j = json.loads(Path(judgments_path).read_text(encoding="utf-8"))
    xml_path, article, blocks = load_article()
    block_ids = [b["block_id"] for b in article["blocks"]]
    paper_id = article["paper_id"]
    if j.get("paper_id") != paper_id:
        problems.add("judgments", f"paper_id {j.get('paper_id')!r} does not match input {paper_id!r}")
    rule_version, rule_hashes = rule_info()

    units = j.get("units") or [{"unit_id": "u1", "title": "whole paper", "blocks": "all"}]
    unit_blocks = {}
    for u in units:
        try:
            unit_blocks[u["unit_id"]] = block_range(u.get("blocks", "all"), block_ids)
        except ValueError as error:
            problems.add(f"unit {u.get('unit_id')}", str(error))
    default_unit = units[0]["unit_id"] if len(units) == 1 else None

    # Entities
    entities, seen = [], set()
    for raw in j.get("entities", []):
        e = dict(raw)
        eid = e.get("entity_id", "")
        where = f"entity {eid}"
        if not eid or eid in seen:
            problems.add(where, "missing or duplicate entity_id")
        seen.add(eid)
        e["paper_id"] = paper_id
        e["unit_id"] = e.get("unit_id") or default_unit
        if e["unit_id"] not in unit_blocks:
            problems.add(where, f"unit_id {e['unit_id']!r} is not a declared unit")
            continue
        check_enum(problems, where, "entity_type", e.get("entity_type"), ENTITY_TYPES)
        check_enum(problems, where, "identity_status", e.get("identity_status"), IDENTITY_STATUS)
        for issue in as_list(e.get("identity_issues")):
            check_enum(problems, where, "identity_issues", issue, IDENTITY_ISSUES)
        if e.get("entity_type") == "ambiguous" and e.get("candidate_side") not in ("gene", "disease"):
            problems.add(where, "ambiguous entity needs candidate_side gene or disease")
        if "in_primary_matrix" not in e:
            e["in_primary_matrix"] = e.get("entity_type") not in AUXILIARY_TYPES
        if not as_list(e.get("surface_forms")):
            problems.add(where, "needs at least one surface form found in the text")
        e["surface_forms"] = as_list(e.get("surface_forms"))
        entities.append(e)
    by_id = {e["entity_id"]: e for e in entities}
    for e in entities:
        for parent in as_list(e.get("parent_id")):
            if parent not in by_id:
                problems.add(f"entity {e['entity_id']}", f"parent_id {parent} unknown")

    mentions = locate_mentions(entities, unit_blocks, blocks, problems)
    mention_count = Counter(m["entity_id"] for m in mentions)
    for e in entities:
        if not mention_count[e["entity_id"]]:
            problems.add(f"entity {e['entity_id']}", f"no surface form found in its unit's text: {e['surface_forms']}")
        e["original_names"] = sorted({m["surface"] for m in mentions if m["entity_id"] == e["entity_id"]})
        e["location"] = sorted({m["block_id"] for m in mentions if m["entity_id"] == e["entity_id"]})

    def side(e):
        if e["entity_type"] == "gene" or (e["entity_type"] == "ambiguous" and e.get("candidate_side") == "gene"):
            return "gene"
        return "target"

    primary = [e for e in entities if e["in_primary_matrix"]]
    genes = [e for e in primary if side(e) == "gene"]
    targets = [e for e in primary if side(e) == "target"]
    auxiliary = [e for e in entities if not e["in_primary_matrix"]]

    # Evidence
    evidence = {}
    for raw in j.get("evidence", []):
        ev = dict(raw)
        eid = ev.get("evidence_id", "")
        where = f"evidence {eid}"
        if not eid or eid in evidence:
            problems.add(where, "missing or duplicate evidence_id")
            continue
        block = blocks.get(ev.get("block_id"))
        if block is None:
            problems.add(where, f"unknown block_id {ev.get('block_id')!r}")
            continue
        quote = ev.get("quote") or block["text"]
        if quote not in block["text"]:
            problems.add(where, f"quote not found verbatim in {ev['block_id']}: {quote[:80]!r} (check with python -m toolkit.find)")
            continue
        start = block["text"].index(quote)
        ev.update(quote=quote, start=start, end=start + len(quote), section=block["section"],
                  location=json.dumps({"block_id": ev["block_id"], "start": start, "end": start + len(quote)}),
                  paper_id=paper_id, unit_id=ev.get("unit_id") or next((u for u, b in unit_blocks.items() if ev["block_id"] in b), ""))
        check_enum(problems, where, "source_scope", ev.get("source_scope"), SOURCE_SCOPES)
        check_enum(problems, where, "assertion_kind", ev.get("assertion_kind"), ASSERTION_KINDS)
        check_enum(problems, where, "relation_asserted", ev.get("relation_asserted"), RELATION_ASSERTED, required=False)
        for basis in as_list(ev.get("support_basis")):
            check_enum(problems, where, "support_basis", basis, SUPPORT_BASIS)
        evidence[eid] = ev

    conflict_ids = {c.get("conflict_id") for c in j.get("data_conflicts", [])}

    def known_evidence(where, ids):
        for i in as_list(ids):
            if i not in evidence:
                problems.add(where, f"unknown evidence_id {i}")

    # Pairs: the model lists every pair it judged; the rest become not_found.
    listed = {}
    for raw in j.get("pairs", []):
        p = dict(raw)
        key = (p.get("gene_id"), p.get("disease_id"))
        where = f"pair {key[0]}-{key[1]}"
        g, t = by_id.get(key[0]), by_id.get(key[1])
        if not g or not t or g not in genes or t not in targets:
            problems.add(where, "endpoints must be a primary gene and a primary target")
            continue
        if g["unit_id"] != t["unit_id"]:
            problems.add(where, f"cross-unit pair ({g['unit_id']} vs {t['unit_id']}) is out of scope")
            continue
        if key in listed:
            problems.add(where, "listed twice")
        listed[key] = p
    pairs = []
    for g in genes:
        for t in targets:
            if g["unit_id"] != t["unit_id"]:
                continue
            p = listed.get((g["entity_id"], t["entity_id"])) or {"status": "not_found", "reason": j.get("default_not_found_reason") or DEFAULT_NOT_FOUND}
            pairs.append(normalise_pair(p, g, t, paper_id, problems, known_evidence, conflict_ids))
    cross_unit = sum(1 for g in genes for t in targets if g["unit_id"] != t["unit_id"])

    # Study findings and conflicts
    findings = []
    for raw in j.get("study_findings", []):
        f = dict(raw)
        where = f"finding {f.get('finding_id')}"
        check_enum(problems, where, "finding_type", f.get("finding_type"), FINDING_TYPES)
        check_enum(problems, where, "reported_significance", f.get("reported_significance"), SIGNIFICANCE)
        check_enum(problems, where, "effect_direction", f.get("effect_direction"), DIRECTION)
        check_enum(problems, where, "statistics_availability", f.get("statistics_availability"), STAT_AVAILABILITY)
        check_enum(problems, where, "source_scope", f.get("source_scope"), SOURCE_SCOPES)
        known_evidence(where, f.get("evidence_ids"))
        f.setdefault("unit_id", default_unit or "")
        f["paper_id"] = paper_id
        findings.append(f)
    conflicts = []
    for raw in j.get("data_conflicts", []):
        c = dict(raw)
        where = f"conflict {c.get('conflict_id')}"
        check_enum(problems, where, "impact", c.get("impact"), IMPACT)
        check_enum(problems, where, "resolution", c.get("resolution"), RESOLUTION)
        conflicts.append(c)

    completion = j.get("completion", "complete")
    if completion not in ("complete", "partial"):
        problems.add("judgments", "completion must be complete or partial")

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        return 1
    status_counts = {s: sum(p["status"] == s for p in pairs) for s in STATUSES}
    print(f"OK: {len(units)} unit(s), {len(genes)} genes, {len(targets)} targets, {len(pairs)} pairs {status_counts}; "
          f"{len(auxiliary)} auxiliary, {len(mentions)} mentions, {len(evidence)} evidence")
    if check_only:
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    judgments_hash = sha256(judgments_path)
    run_id = f"{stamp}-{judgments_hash[:8]}"
    out = Path("outputs") / paper_id / f"rules-{rule_version}" / run_id
    out.mkdir(parents=True, exist_ok=False)
    toolkit_dir = Path(__file__).resolve().parent
    manifest = {
        "run_id": run_id, "rule_version": rule_version, "rule_hashes": rule_hashes, "paper_id": paper_id,
        "title": article["title"], "article_type": article["article_type"], "language": j.get("language", ""),
        "input_path": xml_path.as_posix(), "source_sha256": sha256(xml_path), "annotation_hash": judgments_hash,
        "model_identifier": j.get("model_identifier", "unknown_model"), "exposure": j.get("exposure"),
        "completion": completion, "unread_attachments": j.get("unread_attachments", []),
        "scope_overrides": j.get("scope_overrides", []),
        "scope_exclusions": j.get("scope_exclusions", []) + ([f"{cross_unit} cross-unit gene x target combinations not generated (R9)"] if cross_unit else []),
        "text_normalization": "biomed.jats.normalize: NFKC; hyphen/dash/minus/apostrophe variants unified; whitespace collapsed",
        "parser": {"entrypoint": "biomed.jats.parse_article", "sha256": sha256(Path("biomed/jats.py"))},
        "toolkit_version": VERSION,
        "toolkit_hashes": {p.name: sha256(p) for p in sorted(toolkit_dir.glob("*.py"))},
        "counts": {"units": len(units), "genes": len(genes), "targets": len(targets), "auxiliary_entities": len(auxiliary),
                   "excluded_candidates": len(j.get("excluded_candidates", [])), "mentions": len(mentions),
                   "pairs": len(pairs), "edges": status_counts["supported"], "evidence": len(evidence),
                   "study_findings": len(findings), "data_conflicts": len(conflicts)},
        "status_counts": status_counts,
        "check_limits": "Toolkit checks structure, quotes, offsets, matrix and graph consistency only; not semantic correctness.",
    }

    entity_fields = ["paper_id", "unit_id", "entity_id", "entity_type", "candidate_side", "canonical_name", "original_names",
                     "identity_status", "identity_issues", "gene_species", "host_species", "species_scope", "location",
                     "ambiguity", "merge_basis", "parent_id", "hierarchy_basis", "qualifiers", "in_primary_matrix",
                     "database_id", "reference_sequences_from_text"]
    pair_fields = ["paper_id", "unit_id", "pair_id", "gene_id", "gene_name", "disease_id", "disease_name", "status",
                   "relation_type", "tested_relation_type", "source_scope", "claims", "evidence_ids", "location", "reason",
                   "conditions", "unresolved_reason", "context_checked", "observational_context", "data_conflict_ids",
                   "evidence_species", "gene_species", "host_species", "gene_alteration", "model_type"]
    write_csv(out / "entities.csv", primary, entity_fields)
    write_csv(out / "auxiliary_entities.csv", auxiliary, entity_fields)
    write_csv(out / "mentions.csv", mentions, ["mention_id", "paper_id", "unit_id", "entity_id", "surface", "entity_type",
                                               "mention_role", "block_id", "section", "start", "end", "location", "context",
                                               "contextual_referent", "coreference_path"])
    write_csv(out / "excluded_candidates.csv", j.get("excluded_candidates", []),
              ["candidate_id", "surface", "block_id", "context", "candidate_type", "excluded_reason", "reason"])
    write_csv(out / "gene_sets.csv", j.get("gene_sets", []), ["set_id", "surface", "member_ids", "membership_basis", "scope"])
    write_csv(out / "evidence.csv", list(evidence.values()),
              ["evidence_id", "paper_id", "unit_id", "block_id", "section", "start", "end", "location", "quote", "translation",
               "source_scope", "assertion_kind", "relation_asserted", "support_basis", "supports", "conditions",
               "evidence_link_path", "distribution_basis"])
    write_csv(out / "pairs.csv", pairs, pair_fields)
    write_csv(out / "edges.csv", [p for p in pairs if p["status"] == "supported"], pair_fields)
    write_csv(out / "study_findings.csv", findings,
              ["finding_id", "paper_id", "unit_id", "finding_type", "variables", "population_or_group", "source_scope",
               "evidence_ids", "reported_significance", "effect_direction", "statistics_availability", "statistics",
               "conditions", "limits", "depends_on_unread", "dependency_detail", "possible_attachment_reference"])
    write_csv(out / "data_conflicts.csv", conflicts,
              ["conflict_id", "subject", "statements", "same_question_assessment", "impact", "affected_claim_ids",
               "affected_pair_ids", "resolution", "action", "reason"])
    write_csv(out / "unresolved.csv", j.get("unresolved", []), ["item", "kind", "status", "reason", "material_needed"])
    write_json(out / "source_blocks.json", article)
    write_json(out / "result.json", {"manifest": manifest, "units": units, "entities": primary, "auxiliary_entities": auxiliary,
                                     "excluded_candidates": j.get("excluded_candidates", []), "gene_sets": j.get("gene_sets", []),
                                     "mentions": mentions, "evidence": list(evidence.values()), "pairs": pairs,
                                     "study_findings": findings, "data_conflicts": conflicts,
                                     "unresolved": j.get("unresolved", []), "input_scope": j.get("input_scope", "")})
    svg = graph_svg(genes, targets, pairs)
    (out / "graph.svg").write_text(svg, encoding="utf-8")
    (out / "graph.graphml").write_text(graphml(genes, targets, pairs), encoding="utf-8")
    write_rule_feedback(out / "rule_feedback.md", j.get("rule_feedback", []), manifest)
    (out / "judgments.json").write_text(Path(judgments_path).read_text(encoding="utf-8"), encoding="utf-8")
    write_json(out / "manifest.json", manifest)
    (out / "index.html").write_text(preview(manifest, primary, auxiliary, pairs, findings, list(evidence.values()), svg), encoding="utf-8")

    report = validate(out, xml_path)
    write_json(out / "validation.json", report)
    manifest["output_files"] = sorted(p.name for p in out.iterdir())
    write_json(out / "manifest.json", manifest)
    failed = [c for c in report["checks"] if not c["passed"]]
    print(f"Wrote {out.as_posix()} - validation {'PASSED' if not failed else 'FAILED'}")
    for c in failed:
        print(f"  FAIL {c['check']}: {c['detail'][:300]}")
    return 0 if not failed else 1


def normalise_pair(p, g, t, paper_id, problems, known_evidence, conflict_ids):
    where = f"pair {g['entity_id']}-{t['entity_id']}"
    status = p.get("status")
    check_enum(problems, where, "status", status, set(STATUSES))
    relation = p.get("relation_type") or "none"
    check_enum(problems, where, "relation_type", relation, RELATION_TYPES)
    scope = p.get("source_scope") or "不确定"
    check_enum(problems, where, "source_scope", scope, SOURCE_SCOPES)
    claims = as_list(p.get("claims"))
    for c in claims:
        cw = f"{where} claim {c.get('claim_id')}"
        check_enum(problems, cw, "status", c.get("status"), set(STATUSES))
        check_enum(problems, cw, "source_scope", c.get("source_scope"), SOURCE_SCOPES)
        known_evidence(cw, c.get("evidence_ids"))
    supported = [c for c in claims if c.get("status") == "supported"]
    if status == "supported":
        if not supported:
            problems.add(where, "supported needs at least one supported claim with evidence_ids")
        elif any(not as_list(c.get("evidence_ids")) for c in supported):
            problems.add(where, "every supported claim needs evidence_ids")
        else:
            top = max(DISPLAY_PRIORITY.get(c.get("relation_type"), 0) for c in supported)
            top_type = next(k for k, v in DISPLAY_PRIORITY.items() if v == top)
            scopes = {c["source_scope"] for c in supported if c.get("relation_type") == top_type}
            expected_scope = "两者兼有" if {"背景引用", "本研究结果"} <= scopes or "两者兼有" in scopes else scopes.pop()
            if relation != top_type:
                problems.add(where, f"relation_type should be {top_type} (display priority of supported claims, R3)")
            if scope != expected_scope:
                problems.add(where, f"source_scope should be {expected_scope} (source of the selected claim, R3)")
    else:
        if relation != "none":
            problems.add(where, "relation_type must be none unless supported (put tested type in tested_relation_type)")
        if supported and status == "not_found":
            problems.add(where, "not_found cannot carry a supported claim")
    if status == "explicit_negative" and not any(c.get("status") == "explicit_negative" and as_list(c.get("evidence_ids")) for c in claims):
        problems.add(where, "explicit_negative needs an explicit_negative claim with evidence_ids")
    reasons = as_list(p.get("unresolved_reason"))
    for r in reasons:
        check_enum(problems, where, "unresolved_reason", r, UNRESOLVED_REASONS)
    if status == "uncertain" and not reasons:
        problems.add(where, "uncertain needs unresolved_reason")
    if not p.get("reason"):
        problems.add(where, "reason is required")
    for field in ("context_checked", "observational_context"):
        known_evidence(f"{where} {field}", p.get(field))
    for cid in as_list(p.get("data_conflict_ids")):
        if cid not in conflict_ids:
            problems.add(where, f"unknown data_conflict_id {cid}")
    conditions = p.get("conditions") or {}
    species = conditions.get("evidence_species") or ("human" if (g.get("gene_species") or "").lower() in ("human", "homo sapiens")
                                                     else "unknown" if not g.get("gene_species") else "non-human")
    check_enum(problems, where, "evidence_species", species, EVIDENCE_SPECIES)
    evidence_ids = list(dict.fromkeys(i for c in claims for i in as_list(c.get("evidence_ids"))))
    return {"paper_id": paper_id, "unit_id": g["unit_id"], "pair_id": f"{g['entity_id']}-{t['entity_id']}",
            "gene_id": g["entity_id"], "gene_name": g["canonical_name"], "disease_id": t["entity_id"],
            "disease_name": t["canonical_name"], "status": status, "relation_type": relation,
            "tested_relation_type": p.get("tested_relation_type", ""), "source_scope": scope, "claims": claims,
            "evidence_ids": evidence_ids, "location": [], "reason": p.get("reason", ""), "conditions": conditions,
            "unresolved_reason": reasons, "context_checked": as_list(p.get("context_checked")),
            "observational_context": as_list(p.get("observational_context")),
            "data_conflict_ids": as_list(p.get("data_conflict_ids")), "evidence_species": species,
            "gene_species": g.get("gene_species"), "host_species": conditions.get("host_species") or g.get("host_species"),
            "gene_alteration": conditions.get("gene_alteration", ""), "model_type": conditions.get("model_type", "")}


def write_rule_feedback(path, items, manifest):
    lines = [f"# Rule feedback — {manifest['paper_id']}, rules {manifest['rule_version']}, run {manifest['run_id']}", ""]
    if not items:
        lines.append("No rule ambiguities recorded.")
    for n, item in enumerate(items, 1):
        lines += [f"## {n}. {item.get('rule', '')}", f"- Where: {item.get('location', '')}",
                  f"- Problem: {item.get('problem', '')}", f"- Handling: {item.get('handling', '')}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("judgments", type=Path)
    parser.add_argument("--check", action="store_true", help="report problems without writing outputs")
    args = parser.parse_args()
    sys.exit(build(args.judgments, args.check))


if __name__ == "__main__":
    main()
