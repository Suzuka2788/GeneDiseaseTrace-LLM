"""Turn the model's compact line output into data-contract files, then validate them.

Usage: python experiments/single_shot/expand.py RUN_DIR      (RUN_DIR holds response.txt and run.json)
Returns problems instead of writing anything when the response breaks the format or the rules it can check.
"""
import csv
import html
import json
import re
import sys
from pathlib import Path

from common import PROJECT, load, paper_path, sha256

SCOPE = {"bg": "背景引用", "ts": "本研究结果", "both": "两者兼有", "unk": "不确定"}
KIND = {"res": "reported_result", "bgr": "background_relation_statement", "hyp": "hypothesis", "aim": "aim",
        "int": "interpretation", "neg": "negative_result", "co": "descriptive_cooccurrence"}
ASSERTED = {"aff": "affirmed", "neg": "negated", "hyp": "hypothetical", "q": "questioned", "na": "not_asserted",
            "pre": "presupposed"}
BASIS = {"ebr": "explicit_background_report", "rr": "reported_result", "eda": "explicit_disease_attribution",
         "cs": "co_segregation", "cmp": "comparative_result", "mi": "model_intervention", "do": "descriptive_only",
         "ho": "hypothesis_only", "unc": "unclear", "none": "none"}
STATUS = {"sup": "supported", "neg": "explicit_negative", "unc": "uncertain", "nf": "not_found"}
RTYPE = {"c": "causal", "r": "correlation", "a": "association", "-": "none"}
IDENTITY = {"r": "resolved", "p": "provisional", "u": "unresolved"}
ENTITY_TYPES = {"gene", "disease", "clinical_event", "symptom", "phenotype", "ambiguous"}
ISSUES = {"undefined_abbreviation", "suspected_typo", "species_unresolved", "ambiguous_mapping", "other"}
UNRESOLVED = {"identity", "coreference", "hedged_claim", "support_basis_unresolved", "presupposed_only", "scope",
              "conflict", "missing_material", "other"}
FINDING = {"association", "correlation", "group_comparison", "descriptive", "mechanism", "hypothesis", "other"}
SIG = {"significant", "not_significant", "mixed", "unknown", "not_applicable"}
DIRECTION = {"positive", "negative", "mixed", "null", "unknown", "not_applicable"}
AVAIL = {"available", "partial", "unread", "not_reported", "not_applicable"}
PRIORITY = {"causal": 3, "correlation": 2, "association": 1}
WIDTH = {"META": 3, "SCOPE": 2, "UNIT": 4, "E": 10, "X": 4, "EV": 7, "P": 10, "F": 10, "C": 7, "U": 4, "R": 5}


def split_list(value, sep=","):
    return [v.strip() for v in value.split(sep) if v.strip()]


def sentence_list(value):
    """Accept 'b0014.s6+b0014.s7', 'b0014.s6+s7' and ',' or ';' separators; a bare 'sN' reuses the last block."""
    ids, block = [], None
    for part in re.split(r"[+,;\s]+", value):
        if not part:
            continue
        if re.fullmatch(r"s\d+", part) and block:
            part = f"{block}.{part}"
        block = part.split(".")[0]
        ids.append(part)
    return ids


def id_list(value):
    return [v for v in re.split(r"[+,;\s]+", value) if v]


def boundary(surface):
    body = re.escape(surface)
    if surface[:1].isalnum():
        body = r"(?<![A-Za-z0-9])" + body
    if surface[-1:].isalnum():
        body += r"(?![A-Za-z0-9])"
    return re.compile(body)


def parse(text, problems):
    records = {k: [] for k in WIDTH}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        fields = [f.strip() for f in line.split("|")]
        kind = fields[0]
        if kind not in WIDTH:
            problems.append(f"line {n}: unknown record type {kind!r}")
            continue
        # Miscounted empty optional fields: drop surplus empties, first at the end, then from the middle,
        # never touching the record type, the first two fields or the last two (which carry IDs and the reason).
        while len(fields) > WIDTH[kind] and fields[-1] == "":
            fields.pop()
        while len(fields) > WIDTH[kind]:
            middle = [i for i in range(len(fields) - 3, 2, -1) if fields[i] == ""]
            if not middle:
                break
            del fields[middle[0]]
        fields += [""] * (WIDTH[kind] - len(fields))
        if len(fields) != WIDTH[kind]:
            problems.append(f"line {n}: {kind} needs {WIDTH[kind]} fields, got {len(fields)}")
            continue
        records[kind].append(fields[1:])
    return records


def expand(run_dir):
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    paper_id = meta["paper_id"]
    article, kept, dropped, sentences = load(paper_id)
    blocks = {b["block_id"]: b for b in article["blocks"]}
    problems = []
    rec = parse((run_dir / "response.txt").read_text(encoding="utf-8"), problems)

    units = {u[0]: {"unit_id": u[0], "title": u[1], "blocks": u[2]} for u in rec["UNIT"]} or {"u1": {"unit_id": "u1", "title": "whole paper", "blocks": "all"}}
    block_ids = [b["block_id"] for b in kept]

    def unit_blocks(unit_id):
        spec = units[unit_id]["blocks"]
        if spec == "all":
            return block_ids
        start, _, end = spec.partition("-")
        if start not in block_ids or (end or start) not in block_ids:
            problems.append(f"unit {unit_id}: bad block range {spec}")
            return []
        return block_ids[block_ids.index(start):block_ids.index(end or start) + 1]

    # Entities and mentions
    entities = {}
    for eid, etype, name, surfaces, ident, issues, species, parent, unit in rec["E"]:
        unit = unit or next(iter(units))
        ident = ident or "r"
        etype, _, side = etype.partition("_") if etype.startswith("ambiguous") else (etype, "", "")
        if eid in entities or etype not in ENTITY_TYPES or ident not in IDENTITY or unit not in units:
            problems.append(f"E {eid}: duplicate id, bad type/identity or unknown unit")
            continue
        if set(split_list(issues)) - ISSUES or (etype == "ambiguous" and side not in ("gene", "disease")):
            problems.append(f"E {eid}: bad identity issue or missing candidate side")
        entities[eid] = {"paper_id": paper_id, "unit_id": unit, "entity_id": eid, "entity_type": etype,
                         "candidate_side": side, "canonical_name": name, "surfaces": split_list(surfaces, ";"),
                         "identity_status": IDENTITY[ident], "identity_issues": split_list(issues),
                         "gene_species": species or None, "parent_id": parent or None,
                         "in_primary_matrix": etype not in ("symptom", "phenotype")}
    candidates = []
    for e in entities.values():
        for surface in e["surfaces"]:
            pattern = boundary(surface)
            for block_id in unit_blocks(e["unit_id"]):
                for m in pattern.finditer(blocks[block_id]["text"]):
                    candidates.append((block_id, m.start(), m.end(), e["entity_id"]))
    candidates.sort(key=lambda c: c[1] - c[2])
    taken, mentions = {}, []
    for block_id, s, t, eid in candidates:
        spans = taken.setdefault(block_id, [])
        # A longer overlapping name wins, but the very same span may belong to several entities
        # (e.g. "L- and D-2-hydroxyglutaric aciduria" naming two diseases, or one name used for a human and an animal gene).
        if any(s < b and a < t and (a, b) != (s, t) for a, b in spans):
            continue
        spans.append((s, t))
        mentions.append({"mention_id": "", "paper_id": paper_id, "unit_id": entities[eid]["unit_id"], "entity_id": eid,
                         "surface": blocks[block_id]["text"][s:t], "entity_type": entities[eid]["entity_type"],
                         "block_id": block_id, "start": s, "end": t,
                         "location": json.dumps({"block_id": block_id, "start": s, "end": t})})
    mentions.sort(key=lambda m: (m["block_id"], m["start"]))
    for n, m in enumerate(mentions, 1):
        m["mention_id"] = f"M{n:05d}"
    for e in entities.values():
        names = sorted({m["surface"] for m in mentions if m["entity_id"] == e["entity_id"]})
        if not names:
            problems.append(f"E {e['entity_id']}: none of {e['surfaces']} found verbatim in its unit")
        e["original_names"] = names
        e["location"] = sorted({m["block_id"] for m in mentions if m["entity_id"] == e["entity_id"]})

    # Evidence from sentence IDs. An item citing several blocks is split into one item per block
    # (V5 -> V5.1, V5.2); every reference to V5 then points at all its parts.
    evidence, groups = {}, {}
    for vid, sids, scope, kind, asserted, basis in rec["EV"]:
        ids = sentence_list(sids)
        spans = [sentences.get(s) for s in ids]
        if not ids or None in spans:
            problems.append(f"EV {vid}: unknown sentence IDs in {sids}")
            continue
        if scope not in SCOPE or kind not in KIND or asserted not in ASSERTED or set(split_list(basis)) - set(BASIS):
            problems.append(f"EV {vid}: bad code (scope/kind/asserted/basis)")
            continue
        by_block = {}
        for sid, span in zip(ids, spans):
            by_block.setdefault(span[0], []).append((sid, span))
        parts = [vid] if len(by_block) == 1 else [f"{vid}.{n}" for n in range(1, len(by_block) + 1)]
        groups[vid] = parts
        for part, (block_id, items) in zip(parts, by_block.items()):
            start, end = min(s for _, (_, s, _) in items), max(e for _, (_, _, e) in items)
            evidence[part] = {"evidence_id": part, "paper_id": paper_id, "block_id": block_id, "start": start, "end": end,
                              "location": json.dumps({"block_id": block_id, "start": start, "end": end}),
                              "sentence_ids": [sid for sid, _ in items], "quote": blocks[block_id]["text"][start:end],
                              "source_scope": SCOPE[scope], "assertion_kind": KIND[kind],
                              "relation_asserted": ASSERTED[asserted], "support_basis": [BASIS[b] for b in split_list(basis)]}

    def resolve(value):
        """Evidence IDs, or bare sentence IDs cited directly; the latter become implicit evidence items."""
        out = []
        for v in id_list(value):
            if v in groups:
                out += groups[v]
            elif v in sentences and v not in evidence:
                block_id, start, end = sentences[v]
                evidence[v] = {"evidence_id": v, "paper_id": paper_id, "block_id": block_id, "start": start, "end": end,
                               "location": json.dumps({"block_id": block_id, "start": start, "end": end}),
                               "sentence_ids": [v], "quote": blocks[block_id]["text"][start:end], "source_scope": "不确定",
                               "assertion_kind": "descriptive_cooccurrence", "relation_asserted": "not_asserted",
                               "support_basis": ["unclear"], "implicit": True}
                out.append(v)
            else:
                out.append(v)
        return out

    # Pairs
    def side(e):
        return "gene" if e["entity_type"] == "gene" or (e["entity_type"] == "ambiguous" and e["candidate_side"] == "gene") else "target"

    primary = [e for e in entities.values() if e["in_primary_matrix"]]
    genes = [e for e in primary if side(e) == "gene"]
    targets = [e for e in primary if side(e) == "target"]
    listed = {}
    for gid, tid, status, rtype, scope, claims, unresolved, context, reason in rec["P"]:
        where = f"P {gid}-{tid}"
        g, t = entities.get(gid), entities.get(tid)
        if not g or not t or g not in genes or t not in targets or g["unit_id"] != t["unit_id"]:
            problems.append(f"{where}: endpoints must be a primary gene and a primary target in the same unit")
            continue
        if status not in STATUS or rtype not in RTYPE or (scope and scope not in SCOPE):
            problems.append(f"{where}: bad status/type/scope code")
            continue
        parsed_claims = []
        for n, claim in enumerate(split_list(claims, ";"), 1):
            parts = claim.split(":")
            if len(parts) != 4 or parts[0] not in STATUS or parts[1] not in RTYPE or parts[2] not in SCOPE:
                problems.append(f"{where}: bad claim {claim!r}")
                continue
            ev_ids = resolve(parts[3])
            problems += [f"{where}: unknown evidence {v}" for v in ev_ids if v not in evidence]
            parsed_claims.append({"claim_id": f"{gid}-{tid}-c{n}", "status": STATUS[parts[0]], "relation_type": RTYPE[parts[1]],
                                  "source_scope": SCOPE[parts[2]], "evidence_ids": ev_ids})
        status_full, rtype_full = STATUS[status], RTYPE[rtype]
        supported = [c for c in parsed_claims if c["status"] == "supported" and c["evidence_ids"]]
        if status_full == "supported":
            if not supported:
                problems.append(f"{where}: supported needs a supported claim with evidence")
            else:
                top = max(supported, key=lambda c: PRIORITY.get(c["relation_type"], 0))["relation_type"]
                scopes = {c["source_scope"] for c in supported if c["relation_type"] == top}
                expected = "两者兼有" if {"背景引用", "本研究结果"} <= scopes or "两者兼有" in scopes else next(iter(scopes))
                if rtype_full != top or SCOPE.get(scope) != expected:
                    problems.append(f"{where}: main type/scope should be {top}/{expected} (R3)")
        elif rtype_full != "none":
            problems.append(f"{where}: relation type must be '-' unless sup")
        if status_full == "explicit_negative" and not any(c["status"] == "explicit_negative" and c["evidence_ids"] for c in parsed_claims):
            problems.append(f"{where}: neg needs a neg claim with evidence")
        reasons = split_list(unresolved)
        if set(reasons) - UNRESOLVED or (status_full == "uncertain" and not reasons):
            problems.append(f"{where}: uncertain needs valid unresolved reasons")
        context_ids = resolve(context)
        problems += [f"{where}: unknown context evidence {v}" for v in context_ids if v not in evidence]
        listed[(gid, tid)] = {"status": status_full, "relation_type": rtype_full, "source_scope": SCOPE.get(scope, "不确定"),
                              "claims": parsed_claims, "unresolved_reason": reasons, "context_checked": context_ids, "reason": reason}
    pairs = []
    for g in genes:
        for t in targets:
            if g["unit_id"] != t["unit_id"]:
                continue
            p = listed.get((g["entity_id"], t["entity_id"]), {"status": "not_found", "relation_type": "none", "source_scope": "不确定",
                                                             "claims": [], "unresolved_reason": [], "context_checked": [],
                                                             "reason": "No relation evidence in the paper (unlisted pair)."})
            species = "human" if (g["gene_species"] or "") == "human" else "non-human" if g["gene_species"] else "unknown"
            pairs.append({"paper_id": paper_id, "unit_id": g["unit_id"], "pair_id": f"{g['entity_id']}-{t['entity_id']}",
                          "gene_id": g["entity_id"], "gene_name": g["canonical_name"], "disease_id": t["entity_id"],
                          "disease_name": t["canonical_name"], **p,
                          "evidence_ids": list(dict.fromkeys(v for c in p["claims"] for v in c["evidence_ids"])),
                          "evidence_species": species})

    findings = []
    for fid, ftype, variables, group, sig, direction, avail, ev_ids, limits in rec["F"]:
        if ftype not in FINDING or sig not in SIG or direction not in DIRECTION or avail not in AVAIL:
            problems.append(f"F {fid}: bad code")
        problems += [f"F {fid}: unknown evidence {v}" for v in resolve(ev_ids) if v not in evidence]
        findings.append({"finding_id": fid, "finding_type": ftype, "variables": variables, "population_or_group": group,
                         "reported_significance": sig, "effect_direction": direction, "statistics_availability": avail,
                         "evidence_ids": resolve(ev_ids), "limits": limits})
    conflicts = []
    for cid, subject, sids, impact, resolution, note in rec["C"]:
        if impact not in ("noncritical", "status_critical", "undetermined") or resolution not in ("resolved", "unresolved"):
            problems.append(f"C {cid}: bad impact/resolution")
        problems += [f"C {cid}: unknown sentence {s}" for s in sentence_list(sids) if s not in sentences]
        conflicts.append({"conflict_id": cid, "subject": subject, "sentence_ids": sentence_list(sids), "impact": impact,
                          "resolution": resolution, "reason": note})

    if problems:
        return problems
    write_outputs(run_dir, meta, article, dropped, units, entities, mentions, evidence, pairs, findings, conflicts, rec)
    return []


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def write_outputs(run_dir, meta, article, dropped, units, entities, mentions, evidence, pairs, findings, conflicts, rec):
    out = run_dir / "outputs"
    out.mkdir(exist_ok=True)
    entity_fields = ["paper_id", "unit_id", "entity_id", "entity_type", "candidate_side", "canonical_name", "original_names",
                     "identity_status", "identity_issues", "gene_species", "parent_id", "in_primary_matrix", "location"]
    primary = [e for e in entities.values() if e["in_primary_matrix"]]
    write_csv(out / "entities.csv", primary, entity_fields)
    write_csv(out / "auxiliary_entities.csv", [e for e in entities.values() if not e["in_primary_matrix"]], entity_fields)
    write_csv(out / "mentions.csv", mentions, ["mention_id", "paper_id", "unit_id", "entity_id", "surface", "entity_type",
                                               "block_id", "start", "end", "location"])
    write_csv(out / "evidence.csv", list(evidence.values()), ["evidence_id", "paper_id", "block_id", "start", "end", "location",
                                                             "sentence_ids", "quote", "source_scope", "assertion_kind",
                                                             "relation_asserted", "support_basis"])
    pair_fields = ["paper_id", "unit_id", "pair_id", "gene_id", "gene_name", "disease_id", "disease_name", "status",
                   "relation_type", "source_scope", "claims", "evidence_ids", "unresolved_reason", "context_checked",
                   "reason", "evidence_species"]
    write_csv(out / "pairs.csv", pairs, pair_fields)
    write_csv(out / "edges.csv", [p for p in pairs if p["status"] == "supported"], pair_fields)
    write_csv(out / "study_findings.csv", findings, list(findings[0]) if findings else ["finding_id"])
    write_csv(out / "data_conflicts.csv", conflicts, list(conflicts[0]) if conflicts else ["conflict_id"])
    write_csv(out / "excluded_candidates.csv", [dict(zip(("surface", "block_id", "reason"), x)) for x in rec["X"]],
              ["surface", "block_id", "reason"])
    (out / "rule_feedback.md").write_text("\n".join(f"- {r[0]} @ {r[1]}: {r[2]} -> {r[3]}" for r in rec["R"]) or "none",
                                          encoding="utf-8")
    nodes = primary
    gml = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
           '  <key id="name" for="node" attr.name="name" attr.type="string"/>',
           '  <key id="relation_type" for="edge" attr.name="relation_type" attr.type="string"/>',
           '  <key id="source_scope" for="edge" attr.name="source_scope" attr.type="string"/>',
           '  <graph id="G" edgedefault="undirected">']
    gml += [f'    <node id="{html.escape(e["entity_id"])}"><data key="name">{html.escape(e["canonical_name"])}</data></node>' for e in nodes]
    gml += [f'    <edge source="{p["gene_id"]}" target="{p["disease_id"]}"><data key="relation_type">{p["relation_type"]}</data>'
            f'<data key="source_scope">{html.escape(p["source_scope"])}</data></edge>' for p in pairs if p["status"] == "supported"]
    gml += ["  </graph>", "</graphml>"]
    (out / "graph.graphml").write_text("\n".join(gml), encoding="utf-8")
    card = Path(__file__).resolve().parent / "card.md"
    status_counts = {s: sum(p["status"] == s for p in pairs) for s in ("supported", "explicit_negative", "uncertain", "not_found")}
    manifest = {"run_id": run_dir.name, "rule_version": "1.3.0-card-experiment", "rule_hashes": {"card.md": sha256(card)},
                "paper_id": article["paper_id"], "article_type": article["article_type"],
                "source_sha256": sha256(paper_path(article["paper_id"])), "model_identifier": rec["META"][0][0] if rec["META"] else "",
                "exposure": rec["META"][0][1] if rec["META"] else "", "input_scope": rec["SCOPE"][0][0] if rec["SCOPE"] else "",
                "dropped_boilerplate_blocks": dropped, "units": list(units.values()),
                "unread_attachments": [dict(zip(("name", "location", "reason"), u)) for u in rec["U"]],
                "status_counts": status_counts, "run": meta}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_run(run_dir):
    """Validate an expanded run's outputs and write validation.json; the rule-hash check does not apply here."""
    sys.path.insert(0, str(PROJECT))
    from toolkit.validate import validate
    meta = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    report = validate(Path(run_dir) / "outputs", paper_path(meta["paper_id"]))
    (Path(run_dir) / "outputs" / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, [c for c in report["checks"] if not c["passed"] and c["check"] != "manifest_rule_hashes"]


def main(run_dir):
    problems = expand(run_dir)
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    report, failed = validate_run(run_dir)
    print(f"expanded: {report['pairs']} pairs {report['status_counts']}; validation "
          f"{'PASSED' if not failed else 'FAILED'} (rule-hash check skipped: card experiment)")
    for c in failed:
        print(f"  FAIL {c['check']}: {c['detail'][:200]}")


if __name__ == "__main__":
    main(sys.argv[1])
