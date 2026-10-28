"""Pool all predicted gene/disease edges by database ID; retain every edge."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed.io import read_json, write_csv, write_json
from biomed.report import safe_json
from biomed.results import load_results

INK, MUTED = "#183543", "#647983"
TEAL, PURPLE, AMBER = "#16879A", "#83729F", "#BB9156"


def pool(output):
    nodes, edges = {}, {}
    sources = load_results(output)
    if not sources:
        raise ValueError("No completed current-run results to plot")
    for data in sources:
        paper = data["article"]["paper_id"]
        local = {e["entity_id"]: e for e in data["entities"]}
        for pair in data["pairs"]:
            if pair["status"] != "predicted":
                continue
            keys = []
            for role in ("gene_id", "disease_id"):
                entity = local[pair[role]]
                # An unresolved surface form is not a cross-paper identity.
                identity = entity["external_id"] if entity["normalization_status"] == "resolved" else paper + ":" + entity["entity_id"]
                key = entity["entity_type"] + ":" + identity
                node = nodes.setdefault(key, {"id": key, "entity_type": entity["entity_type"],
                                              "external_id": entity["external_id"], "names": Counter(),
                                              "aliases": set(), "papers": set()})
                node["names"][entity["canonical_name"]] += 1
                node["aliases"].update(entity["aliases"])
                node["papers"].add(paper)
                keys.append(key)
            edge = edges.setdefault(tuple(keys), {"gene_id": keys[0], "disease_id": keys[1],
                                                   "papers": set(), "relation_types": set(),
                                                   "source_pairs": [], "status": "predicted"})
            edge["papers"].add(paper)
            edge["relation_types"].update(p["relation_type"] for p in pair["predictions"])
            edge["source_pairs"].append({"paper_id": paper, "pair_id": pair["pair_id"],
                                          "context_blocks": pair["coverage"]["retrieved_blocks"],
                                          "report": "../papers/" + paper + "/report.html"})
    for i, (key, node) in enumerate(sorted(nodes.items())):
        node["label"] = node.pop("names").most_common(1)[0][0]
        if node["label"].isdigit():
            node["label"] = node["external_id"]
        node["aliases"] = sorted(node["aliases"])
        node["papers"] = sorted(node["papers"])
        node["gid"] = f"n{i:03d}"
    for i, (key, edge) in enumerate(sorted(edges.items())):
        edge["id"] = f"e{i:03d}"
        edge["papers"] = sorted(edge["papers"])
        edge["paper_count"] = len(edge["papers"])
        edge["relation_types"] = sorted(edge["relation_types"])
    adjacency = {key: set() for key in nodes}
    for g, d in edges:
        adjacency[g].add(d)
        adjacency[d].add(g)
    remaining, components = set(nodes), []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        stack, component = [seed], []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(adjacency[current] & remaining):
                remaining.remove(neighbor)
                stack.append(neighbor)
        components.append(component)
    components.sort(key=lambda c: (-len(c), min(nodes[k]["label"] for k in c)))
    for i, component in enumerate(components):
        for key in component:
            nodes[key]["component"] = i + 1
            nodes[key]["degree"] = len(adjacency[key])
    manifest = read_json(Path(output) / "run_manifest.json")
    if len(sources) != manifest["requested_papers"] or manifest["failed_this_run"]:
        raise ValueError("The inference run is incomplete; audit and resolve failures before plotting")
    summary = {"run_id": manifest["run_id"], "input_papers": len(sources),
               "source_papers_with_predictions": len({p for e in edges.values() for p in e["papers"]}),
               "gene_nodes": sum(n["entity_type"] == "gene" for n in nodes.values()),
               "disease_nodes": sum(n["entity_type"] == "disease" for n in nodes.values()),
               "unique_predicted_pairs": len(edges), "components": len(components),
               "semantic_verification": "not_run",
               "scope": "All predicted edges in the recorded current run. Only incident nodes are drawn; isolates are not drawn.",
               "identity_rule": "Same entity type + same standard ID; unresolved entities stay paper-specific. Distinct species IDs are not merged."}
    return nodes, edges, adjacency, components, summary


def order_component(component, nodes, adjacency):
    genes = sorted((k for k in component if nodes[k]["entity_type"] == "gene"), key=lambda k: nodes[k]["label"])
    diseases = sorted((k for k in component if nodes[k]["entity_type"] == "disease"), key=lambda k: nodes[k]["label"])
    for _ in range(8):
        ranks = {key: i for i, key in enumerate(diseases)}
        genes.sort(key=lambda k: (sum(ranks[n] for n in adjacency[k]) / len(adjacency[k]), nodes[k]["label"]))
        ranks = {key: i for i, key in enumerate(genes)}
        diseases.sort(key=lambda k: (sum(ranks[n] for n in adjacency[k]) / len(adjacency[k]), nodes[k]["label"]))
    return genes, diseases


def draw(nodes, edges, adjacency, components, summary, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import PathPatch, Rectangle
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "font.size": 10.5, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(30, 22), facecolor="white")
    fig.text(.028, .975, "INTEGRATED GENE–DISEASE NETWORK", fontsize=29, color=INK, weight="bold", va="top")
    fig.text(.028, .945,
             f"{summary['gene_nodes']} genes  /  {summary['disease_nodes']} diseases  /  {summary['unique_predicted_pairs']} predicted pairs  /  "
             f"{summary['source_papers_with_predictions']} source papers (of {summary['input_papers']} processed)",
             fontsize=18, color=INK, va="top")
    fig.text(.028, .922, f"Merged by database ID. Teal = gene; purple = disease; dashed lines = model predictions. All {summary['unique_predicted_pairs']} predicted pairs are shown.",
             fontsize=13, color=MUTED, va="top")
    fig.text(.028, .902, "Full-text semantic verification has not run. Labels and identifier mappings remain unreviewed.",
             fontsize=13, color="#A66F2E", va="top")
    columns, loads = [[], [], []], [0., 0., 0.]
    for component in components:
        gene, disease = order_component(component, nodes, adjacency)
        weight = max(len(gene), len(disease)) + 1.5
        col = min(range(3), key=lambda i: loads[i])
        columns[col].append((component, gene, disease, weight))
        loads[col] += weight
    max_load = max(loads)
    for col, items in enumerate(columns):
        ax = fig.add_axes([.02 + col * .325, .055, .315, .805])
        ax.set(xlim=(0, 1), ylim=(0, max_load + 1))
        ax.axis("off")
        ax.text(.205, max_load + .7, "GENES", ha="right", fontsize=13, weight="bold", color=TEAL)
        ax.text(.465, max_load + .7, "DISEASES", ha="left", fontsize=13, weight="bold", color=PURPLE)
        cursor = max_load
        for index, (component, genes, diseases, weight) in enumerate(items):
            height = weight - 1.5
            bottom = cursor - height
            if index % 2 == 0:
                ax.add_patch(Rectangle((.005, bottom - .45), .985, height + .9,
                                       facecolor="#F4F7F8", edgecolor="none", zorder=0))
            positions = {}
            for group, x in ((genes, .22), (diseases, .45)):
                for i, key in enumerate(group):
                    y = bottom + height * (1 - (i + .5) / len(group))
                    positions[key] = x, y
            for (g, d), edge in edges.items():
                if g not in positions:
                    continue
                x1, y1 = positions[g]
                x2, y2 = positions[d]
                curve = MplPath([(x1, y1), (.31, y1), (.36, y2), (x2, y2)],
                                [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
                artist = PathPatch(curve, facecolor="none", edgecolor=AMBER, alpha=.66,
                                   linewidth=.75 + .25 * edge["paper_count"], linestyle=(0, (3, 2)), zorder=1)
                artist.set_gid("edge_" + edge["id"])
                ax.add_patch(artist)
            for key, (x, y) in positions.items():
                node = nodes[key]
                gene = node["entity_type"] == "gene"
                marker = ax.scatter([x], [y], s=23, c=TEAL if gene else PURPLE, zorder=3)
                marker.set_gid("node_" + node["gid"])
                label = ax.text(x - .013 if gene else x + .013, y, node["label"],
                                ha="right" if gene else "left", va="center", fontsize=10.5, color=INK,
                                zorder=4, clip_on=False)
                label.set_gid("label_" + node["gid"])
            cursor -= weight
    fig.text(.028, .027, "Disconnected components are grouped for readability; layout does not encode biological proximity. Only nodes incident to predictions are shown.",
             fontsize=12, color=MUTED)
    fig.text(.028, .013, "Distinct NCBI Gene IDs are retained, including different species. Source: cached PubTator3 predictions aligned to the supplied XML articles.",
             fontsize=12, color=MUTED)
    stem = destination / "gene_disease_network"
    fig.savefig(stem.with_suffix(".svg"), facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white")
    fig.savefig(stem.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)


def write_tables(nodes, edges, summary, destination):
    data = {"summary": summary, "nodes": list(nodes.values()), "edges": list(edges.values())}
    write_json(destination / "network_data.json", data)
    for filename, records, fields in (
        ("nodes.csv", list(nodes.values()), ["id", "label", "entity_type", "external_id", "degree", "component", "aliases", "papers"]),
        ("edges.csv", [dict(e, gene=nodes[e["gene_id"]]["label"], disease=nodes[e["disease_id"]]["label"]) for e in edges.values()],
         ["id", "gene", "disease", "gene_id", "disease_id", "status", "paper_count", "papers", "relation_types", "source_pairs"])):
        write_csv(destination / filename, records, fields)
    return data


def write_html(data, destination):
    svg = (destination / "gene_disease_network.svg").read_text(encoding="utf-8")
    svg = svg[svg.index("<svg"):]
    safe_data = safe_json(data)
    document = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Integrated gene–disease network</title><style>
*{box-sizing:border-box}body{margin:0;font:14px/1.5 'Segoe UI',Arial,sans-serif;color:#183543;background:#f0f5f6}
header{background:#fff;padding:18px 25px;border-bottom:1px solid #dce5e9}h1{margin:0;font-size:24px}.muted{color:#647983}
.tools{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:12px}input,select,button{font:inherit;padding:8px 10px;border:1px solid #bccdd5;border-radius:5px;background:white}
input{min-width:230px}select{max-width:370px}button{cursor:pointer}a{color:#08758e}main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px;padding:14px}
#viewport{overflow:auto;height:calc(100vh - 205px);background:white;border:1px solid #dce5e9;border-radius:8px}#world{width:100%;min-width:900px}#world>svg{width:100%;height:auto;display:block}
aside{background:white;border:1px solid #dce5e9;border-radius:8px;padding:18px;max-height:calc(100vh - 205px);overflow:auto}h2{font-size:18px;margin:0 0 12px}h3{font-size:16px}.notice{background:#fff2df;padding:10px 13px;border-left:3px solid #bc8745;margin-top:10px}
li{margin-bottom:6px}.count{font-weight:600}#world [id^=node_],#world [id^=label_],#world [id^=edge_]{cursor:pointer}
@media(max-width:900px){main{grid-template-columns:1fr}aside{max-height:350px}#viewport{height:70vh}}
</style></head><body><header><h1>Integrated gene–disease network</h1>
<div class="muted">__COUNTS__</div>
<div class="tools"><input id="search" placeholder="Search name, alias or database ID"><select id="select"><option value="">Choose a node to highlight</option></select>
<button id="plus">Zoom +</button><button id="minus">Zoom −</button><button id="reset">Reset</button><span id="zoomlabel">100%</span>
<a href="gene_disease_network.png">High-resolution PNG</a><a href="gene_disease_network.svg">Editable SVG</a><a href="nodes.csv">Nodes CSV</a><a href="edges.csv">Edges CSV</a></div>
<div class="notice">Model predictions only. Full-text semantic verification has not run. Standard names and species assignments remain unreviewed.</div></header>
<main><div id="viewport"><div id="world">__SVG__</div></div><aside><h2>Explore connections</h2><div id="details">Click a gene or disease to highlight its neighbors. Click a dashed edge to inspect its source papers.</div><hr><p class="muted">Nodes are merged only when their entity type and standard ID match. Distinct species IDs stay separate. Disconnected groups are arranged in three columns for readability.</p></aside></main>
<script>const DATA=__DATA__;
const $=id=>document.getElementById(id),N=new Map(DATA.nodes.map(n=>[n.id,n]));let zoom=1;
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
function resetHighlight(){DATA.nodes.forEach(n=>{['node_','label_'].forEach(p=>{const a=$(p+n.gid);if(a)a.style.opacity=1;});});DATA.edges.forEach(e=>{const a=$('edge_'+e.id);if(a)a.style.opacity=1;});}
function highlight(id){resetHighlight();const node=N.get(id);if(!node)return;const edges=DATA.edges.filter(e=>e.gene_id===id||e.disease_id===id),keep=new Set([id,...edges.flatMap(e=>[e.gene_id,e.disease_id])]);
DATA.nodes.forEach(n=>['node_','label_'].forEach(p=>{const a=$(p+n.gid);if(a)a.style.opacity=keep.has(n.id)?1:.12;}));DATA.edges.forEach(e=>{const a=$('edge_'+e.id);if(a)a.style.opacity=e.gene_id===id||e.disease_id===id?1:.06;});
const d=$('details');d.replaceChildren(el('h3',node.label),el('p',node.entity_type+' · '+node.external_id),el('p',edges.length+' predicted connections'));const list=el('ul');edges.forEach(e=>{const other=N.get(e.gene_id===id?e.disease_id:e.gene_id),li=el('li'),b=el('button',other.label);b.addEventListener('click',()=>edgeDetail(e));li.append(b);list.append(li);});d.append(list);}
function edgeDetail(e){highlight(e.gene_id);const d=$('details');d.replaceChildren(el('h3',N.get(e.gene_id).label+' ↔ '+N.get(e.disease_id).label),el('p','Status: predicted; semantic verification not run.'),el('p','Predicted type: '+e.relation_types.join(', ')));e.source_pairs.forEach(s=>{const p=el('p'),a=el('a',s.paper_id+' — open source report');a.href=s.report;a.target='_blank';p.append(a,el('br'),el('span','XML context blocks: '+(s.context_blocks.join(', ')||'cross-block retrieval required')));d.append(p);});}
function options(){const q=$('search').value.toLowerCase(),s=$('select');s.replaceChildren(el('option','Choose a node to highlight'));s.firstChild.value='';const hits=DATA.nodes.filter(n=>(n.label+' '+n.external_id+' '+n.aliases.join(' ')).toLowerCase().includes(q));hits.sort((a,b)=>a.label.localeCompare(b.label)).forEach(n=>{const o=el('option',n.entity_type+': '+n.label+' ['+n.external_id+']');o.value=n.id;s.append(o);});if(q&&hits.length===1){s.value=hits[0].id;highlight(hits[0].id);}}
function scale(){ $('world').style.width=(100*zoom)+'%';$('zoomlabel').textContent=Math.round(zoom*100)+'%';}
$('search').addEventListener('input',options);$('select').addEventListener('change',e=>highlight(e.target.value));$('plus').addEventListener('click',()=>{zoom=Math.min(5,zoom*1.3);scale();});$('minus').addEventListener('click',()=>{zoom=Math.max(.5,zoom/1.3);scale();});$('reset').addEventListener('click',()=>{zoom=1;scale();resetHighlight();$('search').value='';options();$('details').replaceChildren(el('p','Click a node or edge to inspect its connections.'));});
DATA.nodes.forEach(n=>['node_','label_'].forEach(p=>{const a=$(p+n.gid);if(a){a.addEventListener('click',()=>highlight(n.id));const t=document.createElementNS('http://www.w3.org/2000/svg','title');t.textContent=n.label+' | '+n.external_id;a.append(t);}}));DATA.edges.forEach(e=>{const a=$('edge_'+e.id);if(a)a.addEventListener('click',()=>edgeDetail(e));});options();
</script></body></html>"""
    s = data["summary"]
    counts = (f"{s['gene_nodes']} genes · {s['disease_nodes']} diseases · {s['unique_predicted_pairs']} predicted pairs · "
              f"{s['source_papers_with_predictions']} source papers from {s['input_papers']} processed articles")
    (destination / "network.html").write_text(document.replace("__COUNTS__", counts).replace("__SVG__", svg).replace("__DATA__", safe_data), encoding="utf-8")


def main():
    config = read_json(ROOT / "config.json")
    output = ROOT / config["output_dir"]
    destination = output / "integrated"
    destination.mkdir(parents=True, exist_ok=True)
    nodes, edges, adjacency, components, summary = pool(output)
    data = write_tables(nodes, edges, summary, destination)
    draw(nodes, edges, adjacency, components, summary, destination)
    write_html(data, destination)
    qa = {"run_id": summary["run_id"], "conclusion": f"{summary['unique_predicted_pairs']} model-predicted pairs connect {summary['gene_nodes']} gene nodes and {summary['disease_nodes']} disease nodes across {summary['source_papers_with_predictions']} papers.",
          "archetype": "schematic-led composite: exhaustive bipartite network",
          "backend": "python", "dimensions": "30 x 22 inches", "source_papers": summary["input_papers"],
          "aggregation": summary["identity_rule"], "scope": summary["scope"],
          "statistics": "Descriptive network counts. No inference, calibration, or accuracy claims.",
          "exclusions": "No predicted edge excluded. Isolated entities do not express gene-disease correspondences and are not drawn; their per-paper records remain unchanged.",
          "accepted_preflight_warnings": ["Large-format network rather than journal-column width", "300 dpi PNG plus editable vector exports; TIFF not required"],
          "semantic_verification": "not_run"}
    write_json(destination / "network_qa.json", qa)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
