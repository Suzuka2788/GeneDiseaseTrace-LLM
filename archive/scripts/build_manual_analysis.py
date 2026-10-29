"""Build the deliverables for a hand-curated paper annotation in manual/ (skill rules 1.1.0).

Usage: python archive/scripts/build_manual_analysis.py PMC10014009
Writes outputs_<model>/<paper_id>/rules-<version>/ and refuses to overwrite an existing run.
Every quote, mention offset, matrix and graph is checked; any failure stops the build.
"""
import csv
import html
import importlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from biomed.io import digest, read_json, write_csv, write_json

STATUSES = ("supported", "explicit_negative", "uncertain", "not_found")
RELATION_RANK = {"association": 1, "correlation": 2, "causal": 3}
SCOPES = ("background", "this_study", "both", "uncertain")
AUXILIARY_TYPES = ("symptom", "phenotype")
DISEASE_SET_FOLLOWERS = r"\s+(?:genes?\b|gene panel|complex(?:es)?\b|genotypes?\b|mutation genotypes|animal model)"
LESION_FOLLOWERS = r"\s+(?:lesions?|lesion counts|diagnosis|population)\b"
CARRIER_FOLLOWERS = r"\s+(?:variant\s+)?(?:groups?|variant patients|patients)\b"


def normalise(text):
    return re.sub(r"\s+", " ", text.replace("‐", "-").replace("‑", "-").replace("−", "-")).strip()


def mention_role(entity, text, start, end):
    surface, after = text[start:end], text[end:]
    if entity["type"] == "gene":
        if surface in entity.get("protein_forms", ()) or re.match(r"\s+protein\b", after):
            return "protein_product"
        if re.match(CARRIER_FOLLOWERS, after):
            return "carrier_group"
        return "gene"
    if re.match(DISEASE_SET_FOLLOWERS, after):
        return "gene_set_modifier"
    if re.match(LESION_FOLLOWERS, after):
        return "lesion_or_count_modifier"
    return "disease_name"


def find_mentions(spec, blocks):
    entity_by_id = {e["id"]: e for e in spec.ENTITIES}
    candidates = []
    for entity in spec.ENTITIES:
        for pattern in entity["patterns"]:
            for block in blocks:
                candidates.extend((block, m.start(), m.end(), entity["id"]) for m in re.finditer(pattern, block["text"]))
    candidates.sort(key=lambda item: item[1] - item[2])  # longest first
    taken, mentions = {}, []
    for block, start, end, entity_id in candidates:
        spans = taken.setdefault(block["block_id"], [])
        if any(start < other_end and other_start < end for other_start, other_end in spans):
            continue
        spans.append((start, end))
        text = block["text"]
        mentions.append({
            "paper_id": spec.PAPER_ID, "entity_id": entity_id, "surface": text[start:end],
            "entity_type": entity_by_id[entity_id]["type"],
            "mention_role": mention_role(entity_by_id[entity_id], text, start, end),
            "block_id": block["block_id"], "xml_id": block.get("xml_id") or "", "section": block["section"],
            "content_type": block["content_type"], "start": start, "end": end,
            "context": text[max(0, start - 90):end + 90],
        })
    mentions.sort(key=lambda m: (m["block_id"], m["start"]))
    for number, mention in enumerate(mentions, 1):
        mention["mention_id"] = f"M{number:04d}"
    return mentions


def build_evidence(spec, blocks_by_id):
    evidence = {}
    for evidence_id, (block_id, quote, scope, kind, conditions) in spec.EVIDENCE.items():
        block = blocks_by_id[block_id]
        quote = block["text"] if quote is None else quote
        if quote not in block["text"]:
            raise ValueError(f"{evidence_id}: quote not in {block_id}: {quote[:60]}")
        start = block["text"].index(quote)
        if scope not in SCOPES:
            raise ValueError(f"{evidence_id}: bad source_scope {scope}")
        evidence[evidence_id] = {
            "evidence_id": evidence_id, "quote": quote, "block_id": block_id, "xml_id": block.get("xml_id") or "",
            "section": block["section"], "start": start, "end": start + len(quote),
            "location": f"{block_id} ({block['section']}; chars {start}-{start + len(quote)})",
            "source_scope": scope, "assertion_kind": kind, "conditions": conditions,
        }
    return evidence


def build_pairs(spec, genes, diseases, evidence):
    pairs = []
    for gene in genes:
        for disease in diseases:
            judgment = spec.JUDGMENTS.get((gene["id"], disease["id"]))
            if judgment is None:
                judgment = {"status": "not_found", "relation_type": "none", "source_scope": "uncertain", "claims": [],
                            "context_checked": [], "conditions": {}, "unresolved_reason": "",
                            "reason": "No statement or analysis in the checked text links this gene to this disease; "
                                      "appearing in the same paper is not evidence."}
            check_judgment(gene["id"], disease["id"], judgment, evidence)
            support_ids = list(dict.fromkeys(i for claim in judgment["claims"] for i in claim["evidence_ids"]))
            evidence_items = [{**evidence[i], "supports": "; ".join(c["statement"] for c in judgment["claims"] if i in c["evidence_ids"])}
                              for i in support_ids]
            context_items = [{**evidence[i], "supports": "context only (not counted as support)"} for i in judgment["context_checked"]]
            pairs.append({
                "paper_id": spec.PAPER_ID, "pair_id": f"{gene['id']}-{disease['id']}",
                "gene_id": gene["id"], "gene": gene["name"], "disease_id": disease["id"], "disease": disease["name"],
                "status": judgment["status"], "relation_type": judgment["relation_type"],
                "source_scope": judgment["source_scope"],
                "evidence_species": judgment["conditions"].get("evidence_species", "human"),
                "evidence_ids": support_ids, "evidence": evidence_items,
                "location": [item["location"] for item in evidence_items],
                "context_checked": context_items, "claims": judgment["claims"],
                "conditions": judgment["conditions"], "unresolved_reason": judgment["unresolved_reason"],
                "reason": judgment["reason"],
            })
    return pairs


def check_judgment(gene_id, disease_id, judgment, evidence):
    name = f"{gene_id}-{disease_id}"
    status, relation = judgment["status"], judgment["relation_type"]
    if status not in STATUSES or judgment["source_scope"] not in SCOPES:
        raise ValueError(f"{name}: bad status or scope")
    for evidence_id in [i for c in judgment["claims"] for i in c["evidence_ids"]] + judgment["context_checked"]:
        if evidence_id not in evidence:
            raise ValueError(f"{name}: unknown evidence {evidence_id}")
    if status in ("supported", "explicit_negative") and not judgment["claims"]:
        raise ValueError(f"{name}: {status} needs claims with evidence")
    if status == "supported":
        top = max(judgment["claims"], key=lambda c: RELATION_RANK[c["relation_type"]])
        if relation != top["relation_type"]:
            raise ValueError(f"{name}: relation_type must be the highest-level claim (R3)")
        top_scopes = {c["source_scope"] for c in judgment["claims"] if c["relation_type"] == relation}
        expected = "both" if top_scopes >= {"background", "this_study"} else top_scopes.pop()
        if judgment["source_scope"] != expected:
            raise ValueError(f"{name}: source_scope must describe the highest-level claim (R3)")
    elif relation != "none":
        raise ValueError(f"{name}: relation_type must be none unless supported")
    if status == "uncertain" and not judgment["unresolved_reason"]:
        raise ValueError(f"{name}: uncertain needs unresolved_reason")
    if status == "not_found" and judgment["claims"]:
        raise ValueError(f"{name}: not_found cannot carry support claims")


def verify_xml(xml_path, evidence, blocks_by_id):
    body = normalise("".join(ET.parse(xml_path).getroot().itertext()))

    def present(item):
        # The parser joins table cells with " | ", which is not in the XML, so table rows are checked cell by cell.
        if blocks_by_id[item["block_id"]]["content_type"] == "table_row":
            return all(normalise(cell) in body for cell in item["quote"].split(" | ") if cell.strip())
        return normalise(item["quote"]) in body

    missing = [e for e in evidence.values() if not present(e)]
    if missing:
        raise ValueError(f"{len(missing)} quotes not in source XML, e.g. {missing[0]['evidence_id']}")


def graph_svg(genes, diseases, pairs):
    row, top = 30, 70
    span = max(len(genes), len(diseases)) - 1
    gene_y = {g["id"]: top + row * span * i / max(1, len(genes) - 1) for i, g in enumerate(genes)}
    disease_y = {d["id"]: top + row * span * i / max(1, len(diseases) - 1) for i, d in enumerate(diseases)}
    height = top + row * span + 70
    edges = [p for p in pairs if p["status"] == "supported"]
    linked = {p["gene_id"] for p in edges} | {p["disease_id"] for p in edges}
    colour = {"both": "#1f6f8b", "background": "#b8860b", "this_study": "#2e7d32"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height:.0f}" font-family="Segoe UI, Arial, sans-serif" font-size="12">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="300" y="34" text-anchor="end" font-weight="bold">Genes</text>',
           '<text x="660" y="34" font-weight="bold">Diseases (primary matrix)</text>']
    for p in edges:
        dash = ' stroke-dasharray="6 4"' if p["evidence_species"] == "non-human" else ""
        tip = html.escape(f"{p['gene']} — {p['disease']} | {p['relation_type']} | {p['source_scope']} | "
                          f"{', '.join(p['evidence_ids'])} | " + " / ".join(p["location"]))
        out.append(f'<line x1="320" y1="{gene_y[p["gene_id"]]:.1f}" x2="640" y2="{disease_y[p["disease_id"]]:.1f}" '
                   f'stroke="{colour[p["source_scope"]]}" stroke-width="2"{dash}><title>{tip}</title></line>')
    for g in genes:
        fill = "#1f6f8b" if g["id"] in linked else "#c9d6de"
        out.append(f'<circle cx="320" cy="{gene_y[g["id"]]:.1f}" r="6" fill="{fill}"/>'
                   f'<text x="308" y="{gene_y[g["id"]] + 4:.1f}" text-anchor="end">{html.escape(g["id"] + "  " + g["name"])}</text>')
    for d in diseases:
        fill = "#8b3a62" if d["id"] in linked else "#e3cfd9"
        mark = " [ambiguous]" if d["type"] == "ambiguous" else ""
        out.append(f'<rect x="634" y="{disease_y[d["id"]] - 6:.1f}" width="12" height="12" fill="{fill}"/>'
                   f'<text x="654" y="{disease_y[d["id"]] + 4:.1f}">{html.escape(d["id"] + "  " + d["name"] + mark)}</text>')
    out.append(f'<text x="20" y="{height - 20:.0f}" fill="#555">Edges: supported only. Amber = background evidence, '
               'green = this study, blue = both; dashed = non-human (animal-model) evidence. Pale nodes have no supported edge.</text></svg>')
    return "\n".join(out)


def graphml(genes, diseases, pairs):
    node_keys = ("name", "bipartite", "entity_type", "species", "ambiguity")
    edge_keys = ("edge_id", "status", "relation_type", "source_scope", "evidence_species", "model_type",
                 "evidence_ids", "location", "reason")
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    out += [f'  <key id="n_{k}" for="node" attr.name="{k}" attr.type="string"/>' for k in node_keys]
    out += [f'  <key id="e_{k}" for="edge" attr.name="{k}" attr.type="string"/>' for k in edge_keys]
    out.append('  <graph id="G" edgedefault="undirected">')
    for entity in genes + diseases:
        values = {"name": entity["name"], "bipartite": "gene" if entity["type"] == "gene" else "disease",
                  "entity_type": entity["type"], "species": entity["species"], "ambiguity": entity["ambiguity"]}
        data = "".join(f'<data key="n_{k}">{html.escape(v)}</data>' for k, v in values.items())
        out.append(f'    <node id="{entity["id"]}">{data}</node>')
    for p in pairs:
        if p["status"] != "supported":
            continue
        values = {"edge_id": p["pair_id"], "status": p["status"], "relation_type": p["relation_type"],
                  "source_scope": p["source_scope"], "evidence_species": p["evidence_species"],
                  "model_type": p["conditions"].get("model_type", ""), "evidence_ids": ",".join(p["evidence_ids"]),
                  "location": " || ".join(p["location"]), "reason": p["reason"]}
        data = "".join(f'<data key="e_{k}">{html.escape(v)}</data>' for k, v in values.items())
        out.append(f'    <edge id="{p["pair_id"]}" source="{p["gene_id"]}" target="{p["disease_id"]}">{data}</edge>')
    out += ["  </graph>", "</graphml>"]
    return "\n".join(out)


def validate(out, genes, diseases, auxiliary, pairs, mentions, blocks_by_id):
    """Data-contract checks 1-5, re-reading the written files."""
    checks = []
    for m in mentions:
        if blocks_by_id[m["block_id"]]["text"][m["start"]:m["end"]] != m["surface"]:
            raise ValueError(f"Mention offset mismatch {m['mention_id']}")
    checks.append(f"1. {len(mentions)} mention offsets slice to their surface; all evidence quotes found in their block and in the source XML.")
    expected = {(g["id"], d["id"]) for g in genes for d in diseases}
    actual = [(p["gene_id"], p["disease_id"]) for p in pairs]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("Pair matrix is not the exact gene x primary-disease product")
    checks.append(f"2. Pair set equals the {len(genes)} x {len(diseases)} product exactly once ({len(actual)} pairs).")
    checks.append("3. supported/explicit_negative carry claims with evidence; uncertain carries unresolved_reason; "
                  "relation_type/source_scope follow the highest-level claim (R3).")
    graph = ET.parse(out / "graph.graphml").getroot()
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    nodes = {n.get("id") for n in graph.iterfind(".//g:node", ns)}
    edges = {(e.get("source"), e.get("target")) for e in graph.iterfind(".//g:edge", ns)}
    supported = {(p["gene_id"], p["disease_id"]) for p in pairs if p["status"] == "supported"}
    if nodes != {e["id"] for e in genes + diseases} or edges != supported:
        raise ValueError("GraphML nodes/edges differ from primary entities/supported pairs")
    if any(e["id"] in nodes for e in auxiliary):
        raise ValueError("Auxiliary entity leaked into the graph")
    checks.append(f"4. GraphML nodes = {len(nodes)} primary entities (isolated kept, auxiliary excluded); edges = {len(edges)} supported pairs.")
    with (out / "pairs.csv").open(encoding="utf-8-sig") as stream:
        csv_pairs = list(csv.DictReader(stream))
    with (out / "edges.csv").open(encoding="utf-8-sig") as stream:
        csv_edges = list(csv.DictReader(stream))
    result = read_json(out / "result.json")
    if not (len(csv_pairs) == len(result["pairs"]) == len(pairs) and len(csv_edges) == len(edges)):
        raise ValueError("CSV / JSON / GraphML counts disagree")
    checks.append("5. pairs.csv, edges.csv, result.json and graph.graphml counts agree.")
    return {"passed": True, "checks": checks,
            "not_checked": ["Biological correctness of any judgment", "Entities only present in unread supplements or figure pixels",
                            "Recall of entity names beyond the pattern list and manual reading"]}


def preview(spec, article, manifest, genes, diseases, auxiliary, pairs, findings, evidence, svg):
    def cell(value):
        if isinstance(value, list):
            return "<br>".join(cell(v) for v in value)
        if isinstance(value, dict):
            if "evidence_id" in value:
                return f"<b>{html.escape(value['evidence_id'])}</b> [{html.escape(value['assertion_kind'])}, {html.escape(value['source_scope'])}] " \
                       f"“{html.escape(value['quote'][:400])}” — {html.escape(value['location'])}"
            return html.escape(json.dumps(value, ensure_ascii=False))
        return html.escape(str(value))

    def table(rows, fields, row_attr=None):
        head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
        body = "".join(f'<tr data-status="{html.escape(r.get(row_attr, "")) if row_attr else ""}">'
                       + "".join(f"<td>{cell(r.get(f, ''))}</td>" for f in fields) + "</tr>" for r in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    entity_fields = ["id", "type", "name", "original_names", "species", "parent_ids", "qualifiers", "mention_count", "locations", "merge_basis", "ambiguity"]
    counts = ", ".join(f"{k}: {v}" for k, v in manifest["status_counts"].items())
    ordered = sorted(pairs, key=lambda p: STATUSES.index(p["status"]))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(spec.PAPER_ID)} gene–disease evidence</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222;background:#fff;max-width:1400px}}
table{{border-collapse:collapse;font-size:12px;margin-bottom:24px}}td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left}}
th{{background:#f2f2f2}}.svg{{overflow-x:auto;border:1px solid #ddd}}code{{background:#f4f4f4;padding:1px 4px}}</style></head><body>
<h1>{html.escape(spec.PAPER_ID)}: {html.escape(article['title'])}</h1>
<p>PMID {html.escape(article['pmid'])} · {html.escape(article['article_type'])} · rules {html.escape(spec.RULE_VERSION)} · model {html.escape(spec.MODEL)} ·
run <code>{html.escape(manifest['run_id'])}</code></p>
<p>{len(genes)} genes × {len(diseases)} primary diseases = {len(pairs)} pairs ({html.escape(counts)}); {len(auxiliary)} auxiliary symptom/phenotype entities;
{len(findings)} study findings. Program checks passed; this is a self-check, not independent expert validation.</p>
<h2>D. Bipartite graph</h2><div class="svg">{svg}</div>
<h2>B. Primary entities</h2>{table(genes + diseases, entity_fields)}
<h2>B. Auxiliary entities (symptoms / phenotypes, R1)</h2>{table(auxiliary, entity_fields)}
<h2>C. All candidate pairs</h2>
<p><label>Status filter <select id="f"><option value="">all</option>{''.join(f'<option>{s}</option>' for s in STATUSES)}</select></label></p>
<div id="pairs">{table(ordered, ["pair_id", "gene", "disease", "status", "relation_type", "source_scope", "evidence", "context_checked", "conditions", "unresolved_reason", "reason"], "status")}</div>
<h2>Study findings (not gene–disease edges, R5)</h2>{table(findings, ["finding_id", "variables", "population_or_group", "status", "source_scope", "evidence", "conditions", "limits"])}
<h2>Evidence ledger</h2>{table(list(evidence.values()), ["evidence_id", "assertion_kind", "source_scope", "quote", "location", "conditions"])}
<script>document.getElementById('f').addEventListener('change',function(e){{var v=e.target.value;
document.querySelectorAll('#pairs tbody tr').forEach(function(r){{r.style.display=!v||r.dataset.status===v?'':'none';}});}});</script>
</body></html>"""


def main(paper_id):
    spec = importlib.import_module(f"archive.manual.{paper_id.lower()}")
    out = ROOT / spec.OUTPUT_ROOT / paper_id / f"rules-{spec.RULE_VERSION}"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} already exists; rule outputs are not overwritten. Bump RULE_VERSION or move it.")
    article = read_json(ROOT / "cache" / "articles" / f"{paper_id}.json")
    blocks = article["blocks"]
    blocks_by_id = {b["block_id"]: b for b in blocks}
    mentions = find_mentions(spec, blocks)
    evidence = build_evidence(spec, blocks_by_id)
    verify_xml(ROOT / ".Input" / "100papers" / f"{paper_id}.xml", evidence, blocks_by_id)

    entities = []
    for entity in spec.ENTITIES:
        own = [m for m in mentions if m["entity_id"] == entity["id"]]
        if not own:
            raise ValueError(f"No mention located for {entity['id']}")
        entities.append({
            "paper_id": paper_id, "id": entity["id"], "type": entity["type"], "name": entity["name"],
            "original_names": sorted({m["surface"] for m in own}), "species": entity["species"],
            "in_primary_matrix": entity["type"] not in AUXILIARY_TYPES,
            "parent_ids": entity.get("parents", []), "parent_basis": entity.get("parent_basis", ""),
            "qualifiers": entity.get("qualifiers", ""), "database_id": "",
            "reference_sequences_from_text": entity.get("reference_sequences_from_text", ""),
            "mention_count": len(own), "mention_roles": dict(Counter(m["mention_role"] for m in own)),
            "locations": sorted({m["block_id"] for m in own}),
            "merge_basis": entity["merge_basis"], "ambiguity": entity["ambiguity"],
        })
    genes = [e for e in entities if e["type"] == "gene"]
    diseases = [e for e in entities if e["type"] != "gene" and e["in_primary_matrix"]]
    auxiliary = [e for e in entities if not e["in_primary_matrix"]]
    pairs = build_pairs(spec, genes, diseases, evidence)
    findings = [{**f, "evidence": [evidence[i] for i in f["evidence"]]} for f in spec.STUDY_FINDINGS]
    excluded = [dict(zip(("name", "kind", "reason"), row)) for row in spec.EXCLUDED]
    counts = Counter(p["status"] for p in pairs)
    annotation = ROOT / "manual" / f"{paper_id.lower()}.py"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "run_id": f"{stamp}-{digest(annotation.read_bytes())[:8]}", "rule_version": spec.RULE_VERSION,
        "skill": "biomed-gene-disease-evidence", "model": spec.MODEL, "paper_id": paper_id, "pmid": article["pmid"],
        "title": article["title"], "article_type": article["article_type"], "order_basis": spec.ORDER_BASIS,
        "source_file": f".Input/100papers/{paper_id}.xml", "source_sha256": article["source_sha256"],
        "parsed_blocks": f"cache/articles/{paper_id}.json ({len(blocks)} blocks; references excluded)",
        "annotation_file": annotation.relative_to(ROOT).as_posix(), "annotation_hash": digest(annotation.read_bytes()),
        "text_normalisation": "U+2010/U+2011 hyphens and U+2212 minus -> '-', thin/no-break spaces and whitespace collapsed; spelling, numbers and negations unchanged",
        "unread_attachments": spec.UNREAD_ATTACHMENTS, "scope_overrides": [],
        "genes": len(genes), "primary_diseases": len(diseases), "auxiliary_entities": len(auxiliary),
        "pairs": len(pairs), "status_counts": {s: counts.get(s, 0) for s in STATUSES},
        "study_findings": len(findings), "evidence_items": len(evidence),
        "ambiguous_entities": sum(e["type"] == "ambiguous" for e in entities),
    }

    out.mkdir(parents=True, exist_ok=True)
    entity_fields = ["paper_id", "id", "type", "name", "original_names", "species", "in_primary_matrix", "parent_ids",
                     "parent_basis", "qualifiers", "database_id", "reference_sequences_from_text", "mention_count",
                     "mention_roles", "locations", "merge_basis", "ambiguity"]
    write_csv(out / "entities.csv", genes + diseases, entity_fields)
    write_csv(out / "auxiliary_entities.csv", auxiliary, entity_fields)
    write_csv(out / "mentions.csv", mentions, ["mention_id", "paper_id", "entity_id", "surface", "entity_type", "mention_role",
                                               "block_id", "xml_id", "section", "content_type", "start", "end", "context"])
    write_csv(out / "excluded_candidates.csv", excluded, ["name", "kind", "reason"])
    write_csv(out / "evidence.csv", list(evidence.values()), ["evidence_id", "quote", "block_id", "xml_id", "section", "start",
                                                              "end", "source_scope", "assertion_kind", "conditions"])
    pair_rows = [{**p, "evidence": p["evidence_ids"], "context_checked": [c["evidence_id"] for c in p["context_checked"]]} for p in pairs]
    pair_fields = ["paper_id", "pair_id", "gene_id", "gene", "disease_id", "disease", "status", "relation_type", "source_scope",
                   "evidence_species", "evidence", "location", "reason", "conditions", "unresolved_reason", "claims", "context_checked"]
    write_csv(out / "pairs.csv", pair_rows, pair_fields)
    write_csv(out / "edges.csv", [r for r in pair_rows if r["status"] == "supported"], pair_fields)
    write_csv(out / "study_findings.csv", [{**f, "evidence": [e["evidence_id"] for e in f["evidence"]]} for f in findings],
              ["finding_id", "variables", "population_or_group", "status", "source_scope", "evidence", "conditions", "limits"])
    write_json(out / "result.json", {"manifest": manifest, "entities": genes + diseases, "auxiliary_entities": auxiliary,
                                     "mentions": mentions, "excluded_candidates": excluded, "evidence": list(evidence.values()),
                                     "pairs": pairs, "study_findings": findings})
    svg = graph_svg(genes, diseases, pairs)
    (out / "graph.svg").write_text(svg, encoding="utf-8")
    (out / "graph.graphml").write_text(graphml(genes, diseases, pairs), encoding="utf-8")
    validation = validate(out, genes, diseases, auxiliary, pairs, mentions, blocks_by_id)
    write_json(out / "validation.json", validation)
    manifest["output_files"] = sorted(p.name for p in out.iterdir()) + ["manifest.json", "index.html"]
    write_json(out / "manifest.json", manifest)
    (out / "index.html").write_text(preview(spec, article, manifest, genes, diseases, auxiliary, pairs, findings, evidence, svg), encoding="utf-8")
    print(f"{out.relative_to(ROOT).as_posix()}: {len(genes)} genes x {len(diseases)} diseases = {len(pairs)} pairs {dict(counts)}; "
          f"{len(auxiliary)} auxiliary; {len(findings)} findings; validation passed")


if __name__ == "__main__":
    main(sys.argv[1])
