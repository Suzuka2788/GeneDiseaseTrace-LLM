import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path


STYLE = """
:root{--ink:#142c3b;--muted:#647785;--line:#dae4e9;--blue:#137f96;--amber:#a65c0b;--paper:#fff;--bg:#f0f5f6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 'Segoe UI',Arial,sans-serif}
main{max-width:1500px;margin:auto;padding:30px 34px 60px}a{color:#08758e;text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:31px;line-height:1.2;letter-spacing:-.6px;margin:10px 0 16px}h2{font-size:19px;margin:0 0 12px}h3{font-size:16px}
.eyebrow{color:var(--blue);font-weight:700;letter-spacing:1.8px;text-transform:uppercase;font-size:12px}.sub,.muted{color:var(--muted)}
.notice{border-left:4px solid #dd9b38;background:#fff6e8;padding:13px 18px;border-radius:4px;margin:20px 0}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:23px 0}.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:20px}
.card strong{font-size:29px;display:block;line-height:1.2}.card span{color:var(--muted);font-size:12px}.layout{display:grid;grid-template-columns:minmax(450px,1.15fr) minmax(360px,1fr);gap:18px;align-items:start}
.panel{margin-bottom:18px}input,select,button{border:1px solid #c5d4dc;border-radius:6px;padding:9px 11px;background:#fff;color:var(--ink);font:inherit}
button{cursor:pointer}button:hover{background:#e8f3f5}.tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}.tools input[type=search]{min-width:250px;flex:1}
table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:var(--muted);font-weight:600;background:#f7fafb;position:sticky;top:0}th,td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr.pick{cursor:pointer}tr.pick:hover,tr.selected{background:#eaf5f8}.badge{display:inline-block;padding:3px 8px;border-radius:20px;font-size:11px;white-space:nowrap;background:#eef3f5;color:#456}
.badge.predicted{background:#fff0d9;color:#8b520b}.badge.supported{background:#dff4e9;color:#196c42}.scroll{overflow:auto;max-height:640px}.graphbox{max-height:600px;overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fbfdfd}
blockquote{border-left:3px solid #27a1b6;margin:12px 0;padding:10px 14px;background:#f2f8fa;white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}
.meta{font-size:12px;color:var(--muted)}.count{font-variant-numeric:tabular-nums}.empty{color:var(--muted);padding:20px}.legend{font-size:12px;color:var(--muted);margin:10px 0}
.pill{background:#eef5f6;border-radius:5px;padding:3px 7px;margin:3px;display:inline-block;font-size:12px}.break{overflow-wrap:anywhere}
#detail{max-height:600px;overflow:auto}
details{border-top:1px solid var(--line);padding-top:12px;margin-top:16px}summary{cursor:pointer;font-weight:600}footer{font-size:12px;color:var(--muted);margin-top:24px}
@media(max-width:950px){.layout{grid-template-columns:1fr}.cards{grid-template-columns:repeat(3,1fr)}main{padding:20px}.graphbox{max-height:450px}}
"""


def shell(title, body, script=""):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{STYLE}</style></head>"
            f"<body><main>{body}</main>{script}</body></html>")


def safe_json(data):
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def graph_positions(entities):
    genes = [e for e in entities if e["entity_type"] == "gene"]
    diseases = [e for e in entities if e["entity_type"] == "disease"]
    height = max(220, 55 + max(len(genes), len(diseases)) * 32)
    positions = {}
    for items, x in ((genes, 230), (diseases, 430)):
        for i, entity in enumerate(items):
            positions[entity["entity_id"]] = (x, 55 + (i + 0.5) * (height - 75) / max(len(items), 1))
    return positions, height


def graph_svg(entities, pairs):
    edges = [p for p in pairs if p["status"] in ("predicted", "supported")]
    positions, height = graph_positions(entities)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<text x="25" y="24" font-family="Arial" font-size="13" fill="#885313">MODEL PREDICTIONS - semantic verification not run</text>']
    for pair in edges:
        x1, y1 = positions[pair["gene_id"]]
        x2, y2 = positions[pair["disease_id"]]
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#c28b46" stroke-opacity=".5" stroke-dasharray="5 4"/>')
    for entity in entities:
        x, y = positions[entity["entity_id"]]
        gene = entity["entity_type"] == "gene"
        name = entity["canonical_name"]
        short = name if len(name) <= 35 else name[:32] + "..."
        anchor, tx = ("end", x - 12) if gene else ("start", x + 12)
        parts.append(f'<g><title>{html.escape(name)}</title><circle cx="{x}" cy="{y}" r="5" fill="{"#168598" if gene else "#7956a0"}"/>'
                     f'<text x="{tx}" y="{y + 4}" text-anchor="{anchor}" font-family="Arial" font-size="11">{html.escape(short)}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def graphml(result, path):
    ns = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}graphml")
    for key, target in (("label", "node"), ("entity_type", "node"), ("external_id", "node"),
                        ("status", "edge"), ("relation_type", "edge"), ("evidence_blocks", "edge")):
        ET.SubElement(root, f"{{{ns}}}key", {"id": key, "for": target, "attr.name": key, "attr.type": "string"})
    graph = ET.SubElement(root, f"{{{ns}}}graph", {"id": result["article"]["paper_id"], "edgedefault": "undirected"})
    for entity in result["entities"]:
        node = ET.SubElement(graph, f"{{{ns}}}node", {"id": entity["entity_id"]})
        for key, value in (("label", entity["canonical_name"]), ("entity_type", entity["entity_type"]),
                           ("external_id", entity["external_id"])):
            ET.SubElement(node, f"{{{ns}}}data", {"key": key}).text = value
    for pair in result["pairs"]:
        if pair["status"] not in ("predicted", "supported"):
            continue
        edge = ET.SubElement(graph, f"{{{ns}}}edge", {"id": pair["pair_id"], "source": pair["gene_id"], "target": pair["disease_id"]})
        data = {"status": pair["status"], "relation_type": ",".join(p["relation_type"] for p in pair["predictions"]),
                "evidence_blocks": ",".join(e["block_id"] for e in pair["evidence"])}
        for key, value in data.items():
            ET.SubElement(edge, f"{{{ns}}}data", {"key": key}).text = value
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def render_paper(result, directory):
    directory = Path(directory)
    article, stats = result["article"], result["summary"]
    (directory / "graph.svg").write_text(graph_svg(result["entities"], result["pairs"]), encoding="utf-8")
    graphml(result, directory / "graph.graphml")
    cards = "".join(f"<div class='card'><strong>{stats[key]:,}</strong><span>{label}</span></div>" for key, label in
                    [("genes", "Genes"), ("diseases", "Diseases"), ("pairs", "Candidate pairs"),
                     ("predicted_edges", "Predicted edges"), ("supported_edges", "Semantically verified edges")])
    body = f"""
<a href='../../index.html'>&larr; All papers</a><div class='eyebrow' style='margin-top:22px'>Evidence Explorer / {html.escape(article['paper_id'])}</div>
<h1>{html.escape(article['title'])}</h1><div class='sub'>XML full text · {html.escape(article.get('article_type','unknown'))} · PMID {html.escape(article['pmid'])} · Source: supplied JATS XML + PubTator3</div>
<div class='notice'><b>Baseline predictions, not confirmed relationships.</b> Dashed edges come from PubTator3. Retrieved paragraphs are exact source context, but their support for the relationship has not been semantically verified. An absent edge does not mean no relationship exists.</div>
<div class='cards'>{cards}</div><div class='tools'><a href='entities.csv'>Entities CSV</a><a href='relations.csv'>Predictions CSV</a><a href='pair_decisions.jsonl'>All pair decisions</a><a href='graph.graphml'>GraphML</a><a href='graph.svg'>SVG</a><a href='result.json'>Full JSON</a></div>
<div class='layout'><section class='panel'><h2>Gene–disease bipartite graph</h2><div class='tools'><label><input id='connected' type='checkbox' checked> Connected nodes only</label><span id='graphcount' class='meta'></span></div>
<div id='graph' class='graphbox'></div><div class='legend'>Teal: gene · Purple: disease · Dashed amber: model prediction. Click an edge to inspect its source context. All nodes, including isolates, are retained in GraphML and SVG.</div></section>
<section class='panel'><h2>Source context</h2><div id='detail' class='empty'>Select a graph edge, candidate pair, or entity below.</div></section></div>
<section class='panel'><h2>Candidate pair ledger</h2><div class='tools'><input id='search' type='search' placeholder='Search gene or disease'><select id='filter'><option value='predicted'>Model predictions</option><option value='context'>Pairs with shared source blocks</option><option value='all'>All candidate pairs</option></select><span class='meta' id='rowcount'></span></div><div class='scroll'><table><thead><tr><th>Gene</th><th>Disease</th><th>Status</th><th>Shared blocks</th></tr></thead><tbody id='rows'></tbody></table></div></section>
    <section class='panel'><h2>Entity inventory</h2><div class='tools'><input id='entitysearch' type='search' placeholder='Search name, alias or external ID'></div><div class='scroll'><table><thead><tr><th>Type</th><th>Canonical name</th><th>External ID / mapping status</th><th>Aliases</th><th>Aligned mentions</th></tr></thead><tbody id='entities'></tbody></table></div></section>
<section class='panel'><h2>Coverage and limitations</h2><ul>{''.join('<li>'+html.escape(w)+'</li>' for w in article['warnings']+result['limitations'])}</ul><div class='meta'>Reference list included: {str(article['include_references']).lower()} · Integrity checks passed: {str(result['checks']['passed']).lower()} · {stats['unaligned_annotation_events']} annotation events could not be aligned to included XML content (this also includes excluded sections).</div></section>
<footer>Run: {result['run_id']} · Document locations use stable XML block IDs, not fabricated PDF page numbers. Source SHA-256: {article['source_sha256']}</footer>
"""
    compact = {"entities": result["entities"], "pairs": result["pairs"], "blocks": article["blocks"]}
    script = "<script>const DATA=" + safe_json(compact) + ";\n" + PAPER_JS + "</script>"
    (directory / "report.html").write_text(shell(article["paper_id"] + " | Evidence Explorer", body, script), encoding="utf-8")


PAPER_JS = r"""
const $=id=>document.getElementById(id), blockMap=new Map(DATA.blocks.map(b=>[b.block_id,b]));
const E=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const svgNS='http://www.w3.org/2000/svg';
const S=(tag,attrs)=>{const e=document.createElementNS(svgNS,tag);Object.entries(attrs||{}).forEach(([k,v])=>e.setAttribute(k,v));return e;};
function showPair(p){
 const d=$('detail');d.replaceChildren();d.append(E('h3',p.gene+' ↔ '+p.disease),E('span',p.status,'badge '+p.status));
 d.append(E('p','Semantic verification: '+p.semantic_verification+'. Source scores are uncalibrated model scores, not accuracy.','meta'));
 p.predictions.forEach(v=>d.append(E('div',v.source+' · '+v.relation_type+' · score '+(v.source_score??'unavailable'),'pill')));
 if(!p.evidence.length)d.append(E('p','No shared XML block retrieved. This prediction requires cross-block evidence retrieval and semantic review.','notice'));
 p.evidence.forEach(ev=>{const b=blockMap.get(ev.block_id);d.append(E('div',ev.block_id+' · '+(b?.section||'')+' · '+(b?.content_type||''),'meta'),E('blockquote',ev.quote));});
 d.append(E('p','Displayed text is retrieved context, not an assertion that the context supports this pair.','meta'));
}
function showEntity(e){
 const d=$('detail');d.replaceChildren();d.append(E('h3',e.canonical_name),E('span',e.entity_type,'badge'),E('p','External ID: '+e.external_id+' · Mapping: '+(e.normalization_status||'unchecked'),'meta'));
 d.append(E('p','Observed aliases: '+e.aliases.join('; ')),E('p','Species and gene/protein or disease/phenotype disambiguation have not run.','meta'));
 const bids=[...new Set(e.mentions.map(m=>m.block_id))];bids.slice(0,12).forEach(id=>{const b=blockMap.get(id);d.append(E('div',id+' · '+b.section+' · '+b.content_type,'meta'),E('blockquote',b.text));});
 if(bids.length>12)d.append(E('p','Showing 12 of '+bids.length+' source blocks. Full mention locations are in the entity export.','meta'));
}
function graph(){
 const edges=DATA.pairs.filter(p=>p.status==='predicted'||p.status==='supported');
 const connected=new Set(edges.flatMap(p=>[p.gene_id,p.disease_id]));
 const nodes=DATA.entities.filter(e=>!$('connected').checked||connected.has(e.entity_id));
 const groups=[nodes.filter(e=>e.entity_type==='gene'),nodes.filter(e=>e.entity_type==='disease')];
 const h=Math.max(240,80+Math.max(...groups.map(g=>g.length))*38), positions=new Map();
 const svg=S('svg',{viewBox:'0 0 720 '+h,width:'100%',height:h,role:'img','aria-label':'Predicted gene disease bipartite graph'});
 groups.forEach((g,col)=>g.forEach((e,i)=>positions.set(e.entity_id,[col?445:245,60+(i+.5)*(h-85)/Math.max(1,g.length)])));
 edges.forEach(p=>{if(!positions.has(p.gene_id)||!positions.has(p.disease_id))return;const [x1,y1]=positions.get(p.gene_id),[x2,y2]=positions.get(p.disease_id);const line=S('line',{x1,y1,x2,y2,stroke:'#bc8745','stroke-opacity':'.55','stroke-width':2,'stroke-dasharray':'5 4',tabindex:0});line.style.cursor='pointer';line.addEventListener('click',()=>showPair(p));line.addEventListener('keydown',e=>{if(e.key==='Enter')showPair(p)});const title=S('title');title.textContent=p.gene+' / '+p.disease;line.append(title);svg.append(line);});
 nodes.forEach(e=>{const [x,y]=positions.get(e.entity_id),gene=e.entity_type==='gene';const g=S('g'),circle=S('circle',{cx:x,cy:y,r:6,fill:gene?'#168598':'#7956a0'}),text=S('text',{x:gene?x-12:x+12,y:y+4,'text-anchor':gene?'end':'start','font-size':12,'font-family':'Segoe UI, Arial'});const name=e.canonical_name;text.textContent=name.length>32?name.slice(0,29)+'…':name;const title=S('title');title.textContent=name+' | '+e.external_id;g.append(title,circle,text);svg.append(g);});
 $('graph').replaceChildren(svg);$('graphcount').textContent=nodes.length+' / '+DATA.entities.length+' nodes';
 if(!nodes.length)$('graph').append(E('p','No predicted connected nodes. Uncheck the filter to view isolates.','empty'));
}
function rows(){const q=$('search').value.toLowerCase(),f=$('filter').value;const rows=DATA.pairs.filter(p=>(f==='all'||f==='predicted'&&p.status==='predicted'||f==='context'&&p.same_block_count>0)&&(p.gene+' '+p.disease).toLowerCase().includes(q));const frag=document.createDocumentFragment();rows.slice(0,1000).forEach(p=>{const tr=E('tr');tr.className='pick';tr.append(E('td',p.gene),E('td',p.disease));const status=E('td');status.append(E('span',p.status,'badge '+p.status));tr.append(status,E('td',p.same_block_count));tr.addEventListener('click',()=>showPair(p));frag.append(tr);});$('rows').replaceChildren(frag);$('rowcount').textContent=rows.length.toLocaleString()+' pairs'+(rows.length>1000?' (first 1,000 shown; export contains all)':'');}
function entities(){const q=$('entitysearch').value.toLowerCase(),frag=document.createDocumentFragment();DATA.entities.filter(e=>(e.canonical_name+' '+e.aliases.join(' ')+' '+e.external_id).toLowerCase().includes(q)).forEach(e=>{const tr=E('tr');tr.className='pick';[e.entity_type,e.canonical_name,e.external_id+' / '+(e.normalization_status||'unchecked'),e.aliases.join('; '),e.mentions.length].forEach(v=>tr.append(E('td',v)));tr.addEventListener('click',()=>showEntity(e));frag.append(tr);});$('entities').replaceChildren(frag);}
$('connected').addEventListener('change',graph);$('search').addEventListener('input',rows);$('filter').addEventListener('change',rows);$('entitysearch').addEventListener('input',entities);graph();rows();entities();
const first=DATA.pairs.find(p=>p.status==='predicted');if(first)showPair(first);
"""


def render_dashboard(summaries, failures, output):
    output = Path(output)
    totals = {key: sum(s.get(key, 0) for s in summaries) for key in ("genes", "diseases", "pairs", "predicted_edges", "supported_edges")}
    cards = f"<div class='card'><strong>{len(summaries)}</strong><span>Papers processed</span></div>" + "".join(
        f"<div class='card'><strong>{totals[key]:,}</strong><span>{label}</span></div>" for key, label in
        [("genes", "Gene nodes across papers"), ("diseases", "Disease nodes across papers"),
         ("predicted_edges", "Predicted edges"), ("supported_edges", "Semantically verified edges")])
    rows = "".join(f"<tr class='paper'><td><a href='papers/{html.escape(s['paper_id'])}/report.html'>{html.escape(s['paper_id'])}</a></td>"
                   f"<td>{html.escape(s['title'])}</td><td>{s['genes']}</td><td>{s['diseases']}</td><td>{s['pairs']:,}</td><td>{s['predicted_edges']}</td>"
                   f"<td><span class='badge predicted'>Predicted</span></td></tr>" for s in summaries)
    body = f"""
<div class='eyebrow'>NJITLab / Biomedical Literature Mining</div><h1>From papers to evidence-linked graphs</h1>
<div class='sub'>{len(summaries)} papers in the current run · Automated, key-free PubTator3 baseline · Supplied XML source alignment</div>
<div class='notice'><b>Prototype baseline.</b> Entity mentions are aligned to supplied XML. Dashed graph edges are public model predictions; semantic evidence verification and independent accuracy evaluation have not run. Zero verified edges means verification is pending, not that no relationships exist. Retrieving full-text entity annotations does not establish full-text relation coverage.</div>
<div class='cards'>{cards}</div><div class='tools'><a href='inventory.csv'>Input inventory</a><a href='summary.csv'>Summary CSV</a><a href='review_queue.csv'>Automatic review queue</a><a href='quality_report.json'>Quality diagnostics</a><a href='run_manifest.json'>Run manifest</a><a href='run_failures.json'>Failures ({len(failures)})</a></div>
<section class='panel'><h2>Paper collection</h2><div class='tools'><input id='search' type='search' placeholder='Search paper ID or title'><span class='meta'>{totals['pairs']:,} candidate pairs tracked · Counts sum per-paper nodes, not unique entities across the collection.</span></div>
<div class='scroll' style='max-height:900px'><table><thead><tr><th>Paper</th><th>Title</th><th>Genes</th><th>Diseases</th><th>Pairs</th><th>Predicted edges</th><th>Stage</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class='panel'><h2>How to read these results</h2><p>Open a paper to explore its graph, inspect exact XML context and download structured outputs. The pair ledger keeps every gene × disease combination. Missing predictions remain unreviewed; co-occurrence never creates an accepted edge.</p><p class='meta'>Current scope: title, abstract, body, tables, captions and non-reference back matter. Reference lists are excluded by default. External supplements and image contents are not analyzed. Baseline gene labels may include gene/protein mentions; these have not undergone species or biological-type disambiguation.</p><p><a href='https://www.ncbi.nlm.nih.gov/research/pubtator3/'>PubTator3 source</a> · <a href='https://pmc.ncbi.nlm.nih.gov/articles/PMC11223843/'>Method paper</a></p></section>
<footer>All content and interactions are local. No API key, external JavaScript, telemetry, or CDN is required to view the reports.</footer>
"""
    script = "<script>document.getElementById('search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('tr.paper').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script>"
    (output / "index.html").write_text(shell("NJITLab | Evidence Explorer", body, script), encoding="utf-8")
