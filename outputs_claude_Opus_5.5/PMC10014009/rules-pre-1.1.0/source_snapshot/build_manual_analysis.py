"""Build tables, graph and preview from a hand-curated paper annotation in manual/.

Usage: python scripts/build_manual_analysis.py PMC10014009
Fails if any quote is not verbatim in its cited block or in the source XML.
"""
import html
import importlib
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed.io import digest, read_json, write_csv, write_json

STATUSES = ("supported", "explicit_negative", "uncertain", "not_found")
RELATION_TYPES = ("association", "correlation", "causal", "none")
SCOPES = ("background", "this_study", "both", "uncertain")


def normalise(text):
    return re.sub(r"\s+", " ", text.replace("\u2010", "-").replace("\u2011", "-")).strip()


def find_mentions(spec, blocks):
    candidates = []
    for entity in spec.ENTITIES:
        for pattern in entity["patterns"]:
            for block in blocks:
                for match in re.finditer(pattern, block["text"]):
                    candidates.append((block, match.start(), match.end(), entity["id"]))
    # Longest match wins, so nested names are attributed to the most specific entity.
    candidates.sort(key=lambda item: item[1] - item[2])
    taken, mentions = {}, []
    for block, start, end, entity_id in candidates:
        spans = taken.setdefault(block["block_id"], [])
        if any(start < other_end and other_start < end for other_start, other_end in spans):
            continue
        spans.append((start, end))
        text = block["text"]
        role = "name"
        if entity_id.startswith("D") and re.match(spec.MODIFIER_FOLLOWERS, text[end:]):
            role = "modifier"
        mentions.append({
            "entity_id": entity_id, "surface": text[start:end], "block_id": block["block_id"],
            "xml_id": block.get("xml_id") or "", "section": block["section"], "content_type": block["content_type"],
            "start": start, "end": end, "role": role,
            "context": text[max(0, start - 90):end + 90],
        })
    mentions.sort(key=lambda m: (m["block_id"], m["start"]))
    return mentions


def location(block, quote):
    start = block["text"].index(quote)
    return f"{block['block_id']} ({block['section']}; chars {start}-{start + len(quote)})"


def default_reason(spec, gene_id, disease_id):
    parts = []
    if (gene_id, disease_id) in spec.CASES:
        parts.append(f"Only individual co-occurrence in Table 2 ({spec.CASES[gene_id, disease_id]}); "
                     "the paper neither tests nor claims a relation.")
    if gene_id in ("G01", "G02", "G03") and disease_id in spec.TABLE1_ROWS:
        parts.append(f"Table 1 row {spec.TABLE1_ROWS[disease_id]} gives descriptive frequencies by gene group without "
                     "per-gene testing; the pooled Mutation detected vs not-detected comparison of clinical "
                     "characteristics was not significant (b0066) and is not attributed to individual genes.")
    if disease_id in ("D10", "D11", "D12", "D13", "D14"):
        parts.append("Condition appears only as an exclusion criterion or as absent from the cohort (b0026).")
    if gene_id in ("G06", "G07", "G08"):
        parts.append("Animal-model gene is mentioned only in b0099, about CCM lesions in the model.")
    if disease_id in ("D08", "D04"):
        parts.append("Family-level term; relations stated for CCM subtypes are not propagated upward.")
    if not parts:
        parts.append("No statement or analysis in the checked text links this gene to this disease; "
                     "co-occurrence in the same paper is not treated as evidence.")
    return " ".join(parts)


def build_pairs(spec, entities, blocks_by_id):
    genes = [e for e in entities if e["type"] == "gene"]
    diseases = [e for e in entities if e["type"] != "gene"]
    resolved = {}
    for key, value in spec.JUDGMENTS.items():
        if isinstance(value, str):
            source = tuple(value.split(":", 1)[1].split("-"))
            value = spec.JUDGMENTS[source]
        resolved[key] = value
    pairs = []
    for gene in genes:
        for disease in diseases:
            judgment = resolved.get((gene["id"], disease["id"]))
            if judgment is None:
                judgment = {"status": "not_found", "relation_type": "none", "source_scope": "uncertain",
                            "evidence": [], "reason": default_reason(spec, gene["id"], disease["id"])}
            if judgment["status"] not in STATUSES or judgment["relation_type"] not in RELATION_TYPES \
                    or judgment["source_scope"] not in SCOPES:
                raise ValueError(f"Bad labels for {gene['id']}-{disease['id']}")
            if judgment["status"] in ("supported", "explicit_negative") and not judgment["evidence"]:
                raise ValueError(f"{gene['id']}-{disease['id']} needs evidence")
            if judgment["status"] == "supported" and judgment["relation_type"] == "none":
                raise ValueError(f"{gene['id']}-{disease['id']} supported without relation type")
            evidence, locations = [], []
            for block_id, quote in judgment["evidence"]:
                block = blocks_by_id[block_id]
                if quote not in block["text"]:
                    raise ValueError(f"Quote not in {block_id}: {quote[:60]}")
                evidence.append(quote)
                locations.append(location(block, quote))
            pairs.append({
                "paper_id": spec.PAPER_ID, "gene_id": gene["id"], "gene": gene["name"],
                "disease_id": disease["id"], "disease": disease["name"],
                "status": judgment["status"], "relation_type": judgment["relation_type"],
                "source_scope": judgment["source_scope"],
                "species_scope": "animal model" if gene["id"] in ("G06", "G07", "G08") else "human",
                "evidence": evidence, "location": locations, "reason": judgment["reason"],
            })
    return pairs


def verify_against_xml(xml_path, pairs):
    root = ET.parse(xml_path).getroot()
    body = normalise("".join(root.itertext()))
    missing = [q for p in pairs for q in p["evidence"] if normalise(q) not in body]
    if missing:
        raise ValueError(f"{len(missing)} quotes not found in source XML, e.g. {missing[0][:60]}")


def unlisted_symbol_candidates(spec, blocks):
    """Gene-like tokens (letters followed by digits) not covered by an entity or exclusion."""
    covered = {re.sub(r"\\b|\(\?i\)", "", p) for e in spec.ENTITIES for p in e["patterns"]}
    tokens = Counter()
    for block in blocks:
        tokens.update(re.findall(r"\b[A-Z][A-Za-z]{1,6}\d{1,3}[A-Za-z]?\b", block["text"]))
    return sorted(t for t in tokens if t not in covered)


def graph_svg(entities, pairs):
    genes = [e for e in entities if e["type"] == "gene"]
    diseases = [e for e in entities if e["type"] != "gene"]
    row, top = 22, 60
    height = top + row * max(len(genes), len(diseases)) + 40
    gene_y = {g["id"]: top + row * i * (len(diseases) - 1) / max(1, len(genes) - 1) for i, g in enumerate(genes)}
    disease_y = {d["id"]: top + row * i for i, d in enumerate(diseases)}
    linked = {p["gene_id"] for p in pairs if p["status"] == "supported"} | \
             {p["disease_id"] for p in pairs if p["status"] == "supported"}
    colour = {"both": "#1f6f8b", "background": "#b8860b", "this_study": "#2e7d32"}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height:.0f}" font-family="Segoe UI, Arial, sans-serif" font-size="12">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="250" y="30" text-anchor="end" font-weight="bold">Genes</text>',
           '<text x="700" y="30" font-weight="bold">Diseases / phenotypes</text>',
           '<text x="500" y="30" text-anchor="middle" fill="#555">edges: supported only</text>']
    for p in pairs:
        if p["status"] != "supported":
            continue
        dash = ' stroke-dasharray="6 4"' if p["species_scope"] == "animal model" else ""
        tip = html.escape(f"{p['gene']} — {p['disease']} | {p['relation_type']} | {p['source_scope']} | "
                          + " / ".join(p["location"]))
        out.append(f'<line x1="270" y1="{gene_y[p["gene_id"]]:.1f}" x2="680" y2="{disease_y[p["disease_id"]]:.1f}" '
                   f'stroke="{colour[p["source_scope"]]}" stroke-width="2"{dash}><title>{tip}</title></line>')
    for g in genes:
        fill = "#1f6f8b" if g["id"] in linked else "#c9d6de"
        out.append(f'<circle cx="270" cy="{gene_y[g["id"]]:.1f}" r="6" fill="{fill}"/>'
                   f'<text x="258" y="{gene_y[g["id"]] + 4:.1f}" text-anchor="end">{html.escape(g["id"] + "  " + g["name"])}</text>')
    for d in diseases:
        fill = "#8b3a62" if d["id"] in linked else "#e3cfd9"
        out.append(f'<rect x="674" y="{disease_y[d["id"]] - 6:.1f}" width="12" height="12" fill="{fill}"/>'
                   f'<text x="694" y="{disease_y[d["id"]] + 4:.1f}">{html.escape(d["id"] + "  " + d["name"])}</text>')
    legend_y = height - 18
    out.append(f'<text x="20" y="{legend_y}" fill="#555">Line colour: blue = background + this study, amber = background only; '
               'dashed = animal-model gene. Pale nodes have no supported edge.</text></svg>')
    return "\n".join(out)


def graphml(entities, pairs):
    keys = [("node", "name"), ("node", "entity_type"), ("node", "category"), ("node", "species"),
            ("edge", "status"), ("edge", "relation_type"), ("edge", "source_scope"),
            ("edge", "species_scope"), ("edge", "evidence"), ("edge", "location"), ("edge", "reason")]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    out += [f'  <key id="{name}" for="{scope}" attr.name="{name}" attr.type="string"/>' for scope, name in keys]
    out.append('  <graph id="G" edgedefault="undirected">')
    for e in entities:
        side = "gene" if e["type"] == "gene" else "disease"
        out.append(f'    <node id="{e["id"]}"><data key="name">{html.escape(e["name"])}</data>'
                   f'<data key="entity_type">{side}</data><data key="category">{e["category"]}</data>'
                   f'<data key="species">{html.escape(e["species"])}</data></node>')
    for p in pairs:
        if p["status"] != "supported":
            continue
        values = {k: p[k] for k in ("status", "relation_type", "source_scope", "species_scope", "reason")}
        values["evidence"] = " || ".join(p["evidence"])
        values["location"] = " || ".join(p["location"])
        data = "".join(f'<data key="{k}">{html.escape(v)}</data>' for k, v in values.items())
        out.append(f'    <edge source="{p["gene_id"]}" target="{p["disease_id"]}">{data}</edge>')
    out += ["  </graph>", "</graphml>"]
    return "\n".join(out)


def preview(spec, article, entities, pairs, svg, counts):
    def table(rows, fields):
        head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
        body = []
        for r in rows:
            cells = []
            for f in fields:
                v = r.get(f, "")
                v = "<br>".join(html.escape(x) for x in v) if isinstance(v, list) else html.escape(str(v))
                cells.append(f"<td>{v}</td>")
            body.append(f'<tr data-status="{html.escape(r.get("status", ""))}">' + "".join(cells) + "</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    entity_rows = [{**e, "surface_forms": e["surface_forms"], "locations": e["locations"]} for e in entities]
    judged = sorted(pairs, key=lambda p: STATUSES.index(p["status"]))
    summary = ", ".join(f"{k}: {counts.get(k, 0)}" for k in STATUSES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(spec.PAPER_ID)} gene–disease graph</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222;background:#fff}}
table{{border-collapse:collapse;font-size:12px;margin-bottom:24px}}td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left}}
th{{background:#f2f2f2;position:sticky;top:0}}.svg{{overflow-x:auto;border:1px solid #ddd}}</style></head><body>
<h1>{html.escape(spec.PAPER_ID)}: {html.escape(article['title'])}</h1>
<p>PMID {html.escape(article['pmid'])} · {html.escape(article['article_type'])} · {len(entities)} entities ·
{len(pairs)} candidate pairs ({html.escape(summary)}). Edges are drawn only for <b>supported</b>; hover an edge for its evidence location.
This is a hand-curated self-checked analysis, not an independent expert validation.</p>
<div class="svg">{svg}</div>
<h2>Entities</h2>{table(entity_rows, ["id", "type", "category", "name", "surface_forms", "species", "mention_count", "locations", "merge_basis", "ambiguity"])}
<h2>All candidate pairs</h2>
<p><label>Status filter <select id="f"><option value="">all</option>{''.join(f'<option>{s}</option>' for s in STATUSES)}</select></label></p>
<div id="pairs">{table(judged, ["gene_id", "gene", "disease_id", "disease", "status", "relation_type", "source_scope", "species_scope", "evidence", "location", "reason"])}</div>
<script>document.getElementById('f').addEventListener('change',function(e){{var v=e.target.value;
document.querySelectorAll('#pairs tbody tr').forEach(function(r){{r.style.display=!v||r.dataset.status===v?'':'none';}});}});</script>
</body></html>"""


def main(paper_id):
    spec = importlib.import_module(f"manual.{paper_id.lower()}")
    article = read_json(ROOT / "cache" / "articles" / f"{paper_id}.json")
    blocks = article["blocks"]
    blocks_by_id = {b["block_id"]: b for b in blocks}
    mentions = find_mentions(spec, blocks)
    entities = []
    for entity in spec.ENTITIES:
        own = [m for m in mentions if m["entity_id"] == entity["id"]]
        if not own:
            raise ValueError(f"No mention located for {entity['id']} {entity['name']}")
        entities.append({
            "paper_id": paper_id, "id": entity["id"], "type": entity["type"], "category": entity["category"],
            "name": entity["name"], "surface_forms": sorted({m["surface"] for m in own}),
            "species": entity["species"], "db_ref_from_text": entity.get("db_ref_from_text", ""),
            "mention_count": len(own), "modifier_mentions": sum(m["role"] == "modifier" for m in own),
            "locations": sorted({m["block_id"] for m in own}),
            "merge_basis": entity["merge_basis"], "ambiguity": entity["ambiguity"],
        })
    pairs = build_pairs(spec, entities, blocks_by_id)
    verify_against_xml(ROOT / ".Input" / "100papers" / f"{paper_id}.xml", pairs)
    counts = Counter(p["status"] for p in pairs)

    out = ROOT / "outputs_claude_Opus_5.5" / paper_id
    entity_fields = ["paper_id", "id", "type", "category", "name", "surface_forms", "species", "db_ref_from_text",
                     "mention_count", "modifier_mentions", "locations", "merge_basis", "ambiguity"]
    pair_fields = ["paper_id", "gene_id", "gene", "disease_id", "disease", "status", "relation_type",
                   "source_scope", "species_scope", "evidence", "location", "reason"]
    write_csv(out / "entities.csv", entities, entity_fields)
    write_csv(out / "mentions.csv", mentions, ["entity_id", "surface", "role", "block_id", "xml_id", "section",
                                               "content_type", "start", "end", "context"])
    write_csv(out / "excluded_names.csv", [dict(zip(("name", "kind", "reason"), row)) for row in spec.EXCLUDED],
              ["name", "kind", "reason"])
    write_csv(out / "pairs.csv", pairs, pair_fields)
    supported = [p for p in pairs if p["status"] == "supported"]
    write_csv(out / "edges.csv", supported, pair_fields)
    write_json(out / "result.json", {"paper_id": paper_id, "entities": entities, "pairs": pairs,
                                     "excluded_names": spec.EXCLUDED})
    svg = graph_svg(entities, pairs)
    (out / "graph.svg").write_text(svg, encoding="utf-8")
    (out / "graph.graphml").write_text(graphml(entities, pairs), encoding="utf-8")
    (out / "index.html").write_text(preview(spec, article, entities, pairs, svg, counts), encoding="utf-8")
    write_json(out / "manifest.json", {
        "paper_id": paper_id, "source_sha256": article["source_sha256"],
        "annotation_sha256": digest((ROOT / "manual" / f"{paper_id.lower()}.py").read_bytes()),
        "genes": sum(e["type"] == "gene" for e in entities), "diseases": sum(e["type"] != "gene" for e in entities),
        "pairs": len(pairs), "status_counts": dict(counts),
        "unlisted_symbol_candidates": unlisted_symbol_candidates(spec, blocks),
    })
    print(f"{paper_id}: {len(entities)} entities, {len(mentions)} mentions, {len(pairs)} pairs, {dict(counts)}")
    print("Unlisted symbol-like tokens:", unlisted_symbol_candidates(spec, blocks))


if __name__ == "__main__":
    main(sys.argv[1])
