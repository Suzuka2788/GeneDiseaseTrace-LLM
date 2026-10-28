"""Graph and preview rendering for toolkit.build."""
import html
import json

SCOPE_COLOUR = {"两者兼有": "#1f6f8b", "背景引用": "#b8860b", "本研究结果": "#2e7d32", "不确定": "#777777"}


def graph_svg(genes, targets, pairs):
    row, top = 28, 70
    span = max(len(genes), len(targets), 2) - 1
    gy = {g["entity_id"]: top + row * span * i / max(1, len(genes) - 1) for i, g in enumerate(genes)}
    ty = {t["entity_id"]: top + row * span * i / max(1, len(targets) - 1) for i, t in enumerate(targets)}
    height = top + row * span + 70
    edges = [p for p in pairs if p["status"] == "supported"]
    linked = {p["gene_id"] for p in edges} | {p["disease_id"] for p in edges}
    unit_note = len({e["unit_id"] for e in genes + targets}) > 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height:.0f}" font-family="Segoe UI, Arial, sans-serif" font-size="12">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="320" y="34" text-anchor="end" font-weight="bold">Genes</text>',
           '<text x="680" y="34" font-weight="bold">Targets (primary matrix)</text>']
    for p in edges:
        dash = ' stroke-dasharray="6 4"' if p["evidence_species"] != "human" else ""
        tip = html.escape(f"{p['gene_name']} — {p['disease_name']} | {p['relation_type']} | {p['source_scope']} | "
                          f"{p['unit_id']} | {', '.join(p['evidence_ids'])}")
        out.append(f'<line x1="340" y1="{gy[p["gene_id"]]:.1f}" x2="660" y2="{ty[p["disease_id"]]:.1f}" '
                   f'stroke="{SCOPE_COLOUR.get(p["source_scope"], "#777777")}" stroke-width="2"{dash}><title>{tip}</title></line>')
    for g in genes:
        label = g["entity_id"] + "  " + g["canonical_name"] + (f" [{g['unit_id']}]" if unit_note else "")
        fill = "#1f6f8b" if g["entity_id"] in linked else "#c9d6de"
        out.append(f'<circle cx="340" cy="{gy[g["entity_id"]]:.1f}" r="6" fill="{fill}"/>'
                   f'<text x="328" y="{gy[g["entity_id"]] + 4:.1f}" text-anchor="end">{html.escape(label)}</text>')
    for t in targets:
        label = t["entity_id"] + "  " + t["canonical_name"] + (" [ambiguous]" if t["entity_type"] == "ambiguous" else "") \
            + (f" [{t['unit_id']}]" if unit_note else "")
        fill = "#8b3a62" if t["entity_id"] in linked else "#e3cfd9"
        out.append(f'<rect x="654" y="{ty[t["entity_id"]] - 6:.1f}" width="12" height="12" fill="{fill}"/>'
                   f'<text x="674" y="{ty[t["entity_id"]] + 4:.1f}">{html.escape(label)}</text>')
    out.append(f'<text x="20" y="{height - 20:.0f}" fill="#555">Edges: supported only. Amber = 背景引用, green = 本研究结果, '
               'blue = 两者兼有; dashed = non-human or mixed evidence. Pale nodes have no supported edge.</text></svg>')
    return "\n".join(out)


def graphml(genes, targets, pairs):
    node_keys = ("name", "bipartite", "entity_type", "unit_id", "identity_status", "gene_species", "ambiguity")
    edge_keys = ("edge_id", "unit_id", "status", "relation_type", "source_scope", "evidence_species", "gene_species",
                 "host_species", "gene_alteration", "model_type", "evidence_ids", "conditions", "reason")
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    out += [f'  <key id="n_{k}" for="node" attr.name="{k}" attr.type="string"/>' for k in node_keys]
    out += [f'  <key id="e_{k}" for="edge" attr.name="{k}" attr.type="string"/>' for k in edge_keys]
    out.append('  <graph id="G" edgedefault="undirected">')
    for e in genes + targets:
        values = {"name": e["canonical_name"], "bipartite": "gene" if e in genes else "target", "entity_type": e["entity_type"],
                  "unit_id": e["unit_id"], "identity_status": e["identity_status"], "gene_species": e.get("gene_species") or "",
                  "ambiguity": e.get("ambiguity") or ""}
        out.append(f'    <node id="{html.escape(e["entity_id"])}">'
                   + "".join(f'<data key="n_{k}">{html.escape(str(v))}</data>' for k, v in values.items()) + "</node>")
    for p in pairs:
        if p["status"] != "supported":
            continue
        values = {"edge_id": p["pair_id"], "unit_id": p["unit_id"], "status": p["status"], "relation_type": p["relation_type"],
                  "source_scope": p["source_scope"], "evidence_species": p["evidence_species"],
                  "gene_species": p["gene_species"] or "", "host_species": p["host_species"] or "",
                  "gene_alteration": p["gene_alteration"] or "", "model_type": p["model_type"] or "",
                  "evidence_ids": ",".join(p["evidence_ids"]), "conditions": json.dumps(p["conditions"], ensure_ascii=False),
                  "reason": p["reason"]}
        out.append(f'    <edge id="{html.escape(p["pair_id"])}" source="{html.escape(p["gene_id"])}" target="{html.escape(p["disease_id"])}">'
                   + "".join(f'<data key="e_{k}">{html.escape(str(v))}</data>' for k, v in values.items()) + "</edge>")
    out += ["  </graph>", "</graphml>"]
    return "\n".join(out)


def preview(manifest, entities, auxiliary, pairs, findings, evidence, svg):
    def cell(value):
        if isinstance(value, (list, dict)):
            return html.escape(json.dumps(value, ensure_ascii=False))
        return html.escape(str(value if value is not None else ""))

    def table(rows, fields, status=False):
        head = "".join(f"<th>{html.escape(f)}</th>" for f in fields)
        body = "".join(f'<tr data-status="{html.escape(r.get("status", "")) if status else ""}">'
                       + "".join(f"<td>{cell(r.get(f))}</td>" for f in fields) + "</tr>" for r in rows)
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"

    order = ("supported", "explicit_negative", "uncertain", "not_found")
    ordered = sorted(pairs, key=lambda p: order.index(p["status"]))
    counts = ", ".join(f"{k}: {v}" for k, v in manifest["status_counts"].items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(manifest['paper_id'])} evidence</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222;background:#fff}}
table{{border-collapse:collapse;font-size:12px;margin-bottom:24px}}td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left;max-width:520px}}
th{{background:#f2f2f2}}.svg{{overflow-x:auto;border:1px solid #ddd}}</style></head><body>
<h1>{html.escape(manifest['paper_id'])}: {html.escape(manifest['title'])}</h1>
<p>{html.escape(manifest['article_type'])} · rules {html.escape(manifest['rule_version'])} · toolkit {html.escape(manifest['toolkit_version'])} ·
model {html.escape(str(manifest['model_identifier']))} · run {html.escape(manifest['run_id'])} · completion {html.escape(manifest['completion'])}</p>
<p>{manifest['counts']['units']} unit(s); {manifest['counts']['pairs']} pairs ({html.escape(counts)}). Program checks only; not an independent validation.</p>
<h2>D. Graph</h2><div class="svg">{svg}</div>
<h2>B. Primary entities</h2>{table(entities, ["entity_id", "unit_id", "entity_type", "canonical_name", "original_names", "identity_status", "identity_issues", "gene_species", "parent_id", "merge_basis", "ambiguity"])}
<h2>B. Auxiliary entities</h2>{table(auxiliary, ["entity_id", "unit_id", "entity_type", "canonical_name", "original_names", "ambiguity"])}
<h2>C. Pairs</h2><p><select id="f"><option value="">all</option>{''.join(f'<option>{s}</option>' for s in order)}</select></p>
<div id="pairs">{table(ordered, ["pair_id", "unit_id", "gene_name", "disease_name", "status", "relation_type", "source_scope", "evidence_ids", "unresolved_reason", "context_checked", "reason"], True)}</div>
<h2>Study findings</h2>{table(findings, ["finding_id", "finding_type", "variables", "population_or_group", "reported_significance", "effect_direction", "statistics_availability", "statistics", "evidence_ids", "limits"])}
<h2>Evidence</h2>{table(evidence, ["evidence_id", "block_id", "assertion_kind", "relation_asserted", "source_scope", "quote", "translation"])}
<script>document.getElementById('f').addEventListener('change',function(e){{var v=e.target.value;
document.querySelectorAll('#pairs tbody tr').forEach(function(r){{r.style.display=!v||r.dataset.status===v?'':'none';}});}});</script>
</body></html>"""
