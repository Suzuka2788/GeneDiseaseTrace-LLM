"""Expand the compact single-response JSON (format in toolkit/pack.py) into the judgments.json that toolkit.build reads.

Usage: python -m toolkit.expand work/compact.json judgments.json [--model NAME]
"""
import argparse
import json
from pathlib import Path


def expand(compact, paper_id, model):
    units = [{"unit_id": u["id"], "title": u.get("title", ""), "blocks": u.get("blocks", "all")} for u in compact.get("units", [])]
    entities = []
    for e in compact.get("entities", []):
        row = {"entity_id": e.get("id"), "entity_type": e.get("type"), "canonical_name": e.get("name"),
               "surface_forms": e.get("forms", []), "identity_status": e.get("status", "resolved"),
               "identity_issues": e.get("issues", []), "gene_species": e.get("species"), "host_species": e.get("host"),
               "parent_id": e.get("parent"), "ambiguity": e.get("note", ""), "merge_basis": e.get("note", "")}
        for source, target in (("side", "candidate_side"), ("unit", "unit_id"), ("primary", "in_primary_matrix"),
                               ("species_scope", "species_scope"), ("qualifiers", "qualifiers")):
            if source in e:
                row[target] = e[source]
        entities.append(row)
    evidence = [{"evidence_id": ev.get("id"), "block_id": ev.get("block"), "quote": ev.get("quote"),
                 "translation": ev.get("translation", ""), "source_scope": ev.get("scope"), "assertion_kind": ev.get("kind"),
                 "relation_asserted": ev.get("asserted"), "support_basis": ev.get("basis", []),
                 "supports": ev.get("supports", ""), "conditions": ev.get("cond", {})} for ev in compact.get("evidence", [])]
    pairs = []
    for p in compact.get("pairs", []):
        status, kind = p.get("status"), p.get("type")
        pair_id = f"{p.get('gene')}-{p.get('target')}"
        claims = [{"claim_id": f"{pair_id}-C{n}", "status": c.get("status"),
                   ("relation_type" if c.get("status") == "supported" else "tested_relation_type"): c.get("type"),
                   "source_scope": c.get("scope"), "evidence_ids": c.get("ev", []), "reason": c.get("reason", "")}
                  for n, c in enumerate(p.get("claims", []), 2)]
        if status in ("supported", "explicit_negative") and p.get("ev"):
            claims.insert(0, {"claim_id": f"{pair_id}-C1", "status": status,
                              ("relation_type" if status == "supported" else "tested_relation_type"): kind,
                              "source_scope": p.get("scope"), "evidence_ids": p.get("ev"), "reason": p.get("reason", "")})
        pairs.append({"gene_id": p.get("gene"), "disease_id": p.get("target"), "status": status,
                      "relation_type": kind if status == "supported" else "none",
                      "tested_relation_type": kind if status == "explicit_negative" else "",
                      "source_scope": p.get("scope") or "不确定", "claims": claims, "reason": p.get("reason", ""),
                      "conditions": p.get("cond", {}), "unresolved_reason": p.get("unresolved", []),
                      "context_checked": p.get("context", []), "observational_context": p.get("obs", []),
                      "data_conflict_ids": p.get("conflicts", [])})
    findings = [{"finding_id": f.get("id"), "finding_type": f.get("type"), "variables": f.get("variables", ""),
                 "population_or_group": f.get("group", ""), "source_scope": f.get("scope"), "evidence_ids": f.get("ev", []),
                 "reported_significance": f.get("significance"), "effect_direction": f.get("direction"),
                 "statistics_availability": f.get("stats_available"), "statistics": f.get("stats"),
                 "depends_on_unread": f.get("unread", ""), "limits": f.get("limits", "")} for f in compact.get("findings", [])]
    conflicts = [{"conflict_id": c.get("id"), "subject": c.get("subject", ""), "statements": c.get("statements", []),
                  "impact": c.get("impact"), "resolution": c.get("resolution"), "reason": c.get("reason", "")}
                 for c in compact.get("conflicts", [])]
    judgments = {
        "paper_id": paper_id, "model_identifier": model, "exposure": {"statement": compact.get("exposure", "")},
        "language": compact.get("language", ""), "completion": compact.get("completion", "complete"),
        "input_scope": compact.get("input_scope", ""), "entities": entities, "evidence": evidence, "pairs": pairs,
        "excluded_candidates": [{"candidate_id": f"X{n:02d}", "surface": x.get("surface"), "block_id": x.get("block"),
                                 "reason": x.get("reason", ""), "excluded_reason": x.get("label", "")}
                                for n, x in enumerate(compact.get("excluded", []), 1)],
        "study_findings": findings, "data_conflicts": conflicts,
        "unread_attachments": compact.get("unread", []), "unresolved": compact.get("unresolved", []),
        "rule_feedback": [{"rule": f.get("rule", ""), "location": f.get("where", ""), "problem": f.get("problem", ""),
                           "handling": f.get("handling", "")} for f in compact.get("feedback", [])],
    }
    if units:
        judgments["units"] = units
    return judgments


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("compact", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="unknown_model")
    args = parser.parse_args()
    from .common import load_article
    paper_id = load_article()[1]["paper_id"]
    judgments = expand(json.loads(args.compact.read_text(encoding="utf-8")), paper_id, args.model)
    args.output.write_text(json.dumps(judgments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.output}: {len(judgments['entities'])} entities, {len(judgments['pairs'])} listed pairs")


if __name__ == "__main__":
    main()
