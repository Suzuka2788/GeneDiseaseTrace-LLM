"""Render the head-to-head comparison with PubTator3 as one self-contained HTML page (no external scripts).

Usage: python experiments/single_shot/render_vs_pubtator.py v1_card_lean_medium
Reads the files written by compare_pubtator.py and batch.py; writes runs/ab/<variant>/vs_pubtator.html.
"""
import csv
import html
import json
import sys

from common import HERE, PROJECT, RUNS


THIS_STUDY = {"本研究结果", "两者兼有"}
# Hand-picked illustrations, shown under a heading that says they were selected: (paper, gene, disease) as named
# in vs_pubtator_relations.csv (our names for 'ours_only'/'both', PubTator names for 'pubtator_only').
EXAMPLES = [
    ("PMC4068974", "LAMB2", "Pierson syndrome"),
    ("PMC3776720", "PTPN11", "juvenile myelomonocytic leukemia"),
    ("PMC3399778", "MPZ", "neuropathic pain"),
    ("PMC10096224", "D2HGDH", "Seizures"),
]


def read(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def key_numbers(base, relations, papers):
    """Headline figures computed from the run, so the page never states a number the data does not hold."""
    supported = by_source = evidence_body_only = 0
    sources = {}
    for paper in papers:
        out = base / paper["paper_id"] / "outputs"
        parsed = json.loads((PROJECT / "outputs" / "papers" / paper["paper_id"] / "result.json").read_text(encoding="utf-8"))
        sections = {b["block_id"]: b["section"] for b in parsed["article"]["blocks"]}
        evidence = {e["evidence_id"]: e for e in read(out / "evidence.csv")}
        for pair in read(out / "pairs.csv"):
            if pair["status"] != "supported":
                continue
            supported += 1
            sources[pair["source_scope"]] = sources.get(pair["source_scope"], 0) + 1
            places = {sections[evidence[i]["block_id"]].split(" / ")[0] for i in json.loads(pair["evidence_ids"]) if i in evidence}
            evidence_body_only += not places & {"Abstract", "Title"}
    this_study = sum(n for s, n in sources.items() if s in THIS_STUDY)
    this_study_shared = len({(r["paper_id"], m.split("|")[0]) for r in relations for m in r["matched_supported_pairs"].split(";")
                             if m and m.split("|")[1] in THIS_STUDY})
    pubtator_total = sum(1 for r in relations if r["category"] in ("both", "pubtator_only"))
    ours_only = [r for r in relations if r["category"] == "ours_only"]
    pt_only = [r for r in relations if r["category"] == "pubtator_only"]
    spanish = next((p for p in papers if p["paper_id"] == "PMC8626062"), None)
    ours_matched = len({(r["paper_id"], m.split("|")[0]) for r in relations for m in r["matched_supported_pairs"].split(";") if m})
    return {"our_supported": supported, "pubtator_relations": pubtator_total, "evidence_body_only": evidence_body_only,
            "ours_matched": ours_matched, "pt_matched": pubtator_total - len(pt_only),
            "ours_only_missing_entity": sum(not r["detail"].startswith("PubTator has both") for r in ours_only),
            "pt_only_judged": sum(r["detail"].startswith("our pair") for r in pt_only),
            "pt_only_missing_entity": sum(r["detail"].startswith("we did not record") for r in pt_only),
            "genes_ours": sum(p["genes_both"] + p["genes_ours_only"] for p in papers),
            "genes_pt": sum(p["genes_both"] + p["genes_pubtator_only"] for p in papers),
            "diseases_pt_only": sum(p["diseases_pubtator_only"] for p in papers),
            "background": sources.get("背景引用", 0), "this_study": this_study, "this_study_shared": this_study_shared,
            "ours_only": len(ours_only), "ours_only_background": sum(r["our_source"] == "背景引用" for r in ours_only),
            "ours_only_pt_has_entities": sum(r["detail"].startswith("PubTator has both") for r in ours_only),
            "pt_only": len(pt_only), "pt_only_symptom": sum(r["detail"].startswith("we record this") for r in pt_only),
            "spanish_genes": spanish["genes_ours_only"] if spanish else 0,
            "spanish_relations": spanish["relations_ours_only"] if spanish else 0,
            "uncertain": sum(p["our_uncertain"] for p in papers), "negative": sum(p["our_explicit_negative"] for p in papers),
            "cost_per_paper": sum(p["cost"] for p in papers) / len(papers),
            "seconds_per_paper": sum(p["seconds"] for p in papers) / len(papers)}


def examples(relations):
    picked = []
    for paper, gene, disease in EXAMPLES:
        for r in relations:
            if r["paper_id"] == paper and gene in (r["our_gene"], r["gene"]) and disease in (r["our_disease"], r["disease"]):
                picked.append(r)
                break
    return picked


def main(variant, run_set="ab"):
    base = RUNS / run_set / variant
    with (PROJECT / "outputs" / "inventory.csv").open(encoding="utf-8-sig") as stream:
        benchmark = {r["paper_id"]: {"article_type": r["article_type"], "chars": int(r["characters"]), "title": r["title"]}
                     for r in csv.DictReader(stream)}
    summary = read(base / "vs_pubtator_summary.csv")
    relations = read(base / "vs_pubtator_relations.csv")
    entities = json.loads((base / "vs_pubtator_entities.json").read_text(encoding="utf-8"))
    runs = {r["paper_id"]: r for r in read(base / "summary.csv")}
    papers = [{"paper_id": s["paper_id"], "type": benchmark[s["paper_id"]]["article_type"],
               "chars": benchmark[s["paper_id"]]["chars"], "title": benchmark[s["paper_id"]]["title"], "note": s["note"],
               **{k: int(v) for k, v in s.items() if k not in ("paper_id", "note")},
               "seconds": float(runs[s["paper_id"]]["seconds"]), "cost": float(runs[s["paper_id"]]["cost_usd"])}
              for s in summary]
    data = {"variant": variant, "papers": papers, "relations": relations, "entities": entities,
            "key": key_numbers(base, relations, papers), "examples": examples(relations)}
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__VARIANT__", html.escape(variant)).replace(
        "__SCOPE__", "12 benchmark papers" if run_set == "ab" else f"{len(papers)} papers")
    out = base / "vs_pubtator.html"
    out.write_text(page, encoding="utf-8")
    print(out)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gene–disease extraction vs PubTator3</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--grid:#e1e0d9;--ring:rgba(11,11,11,.10);
--both:#2a78d6;--pt:#eb6834;--ours:#1baf7a;--on:#ffffff;--ours-ink:#0f7a52;--mid:#b4b2a8;--light:#e1dfd7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--both:#3987e5;--pt:#d95926;--ours:#199e70;--ours-ink:#4cc89a;--mid:#6b6a63;--light:#3d3c38}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--both:#3987e5;--pt:#d95926;--ours:#199e70;--ours-ink:#4cc89a;--mid:#6b6a63;--light:#3d3c38}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
h1{font-size:24px;margin:0 0 6px}h2{font-size:18px;margin:36px 0 6px}
.sub{color:var(--ink2);margin:0 0 4px;max-width:880px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:18px}
.tile{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:14px 16px}
.tile .k{color:var(--ink2);font-size:13px}.tile .v{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums}
.tile .s{color:var(--ink2);font-size:12px}
.legend{display:flex;gap:18px;flex-wrap:wrap;color:var(--ink2);font-size:13px;margin:10px 0}
.sw{display:inline-flex;align-items:center;gap:6px}.dot{width:12px;height:12px;border-radius:3px;display:inline-block}
.panel{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:14px 16px;overflow-x:auto}
.row{display:grid;grid-template-columns:150px 1fr 70px;align-items:center;gap:10px;margin:6px 0}
.row .lab{text-align:right;color:var(--ink2);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{display:flex;height:24px;gap:2px}
.seg{height:100%;border-radius:4px;display:flex;align-items:center;justify-content:center;color:var(--on);font-size:12px;font-weight:600;min-width:2px;cursor:default}
.tot{color:var(--ink2);font-size:12px;font-variant-numeric:tabular-nums}
.note{color:var(--ink2);font-size:13px;margin:6px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--grid);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--ink2);font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;color:var(--on);font-size:12px;font-weight:600;white-space:nowrap}
.controls{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0;color:var(--ink2);font-size:13px}
select{font:inherit;padding:3px 6px;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px}
details{margin:4px 0}summary{cursor:pointer;color:var(--ink2)}
.quote{color:var(--ink2);font-size:12px;max-width:520px}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px;padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.18);display:none;z-index:10;max-width:320px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
ul{margin:4px 0 0;padding-left:18px}li{margin:2px 0}
.tile .v.big{font-size:34px}
.takeaway{margin:16px 0 0;padding:12px 16px;border-left:4px solid var(--ours);background:var(--panel);border-radius:0 8px 8px 0;max-width:900px}
.ex{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:12px 14px}
.ex h3{margin:6px 0 4px;font-size:15px}.ex .meta{color:var(--ink2);font-size:12px;margin-bottom:6px}
.ex blockquote{margin:6px 0 0;padding-left:10px;border-left:3px solid var(--grid);color:var(--ink2);font-size:13px}
.yes{font-weight:600}.no{color:var(--ink2)}
.lead{font-size:19px;line-height:1.45;margin:10px 0 10px;max-width:900px}
.lead b{color:var(--ours-ink)}
.sc{display:grid;grid-template-columns:minmax(150px,280px) 1fr;gap:4px 14px;align-items:center;padding:8px 0;border-bottom:1px solid var(--grid)}
.sc:last-child{border-bottom:0}
.sc .lab{font-size:13px}.sc .lab small{display:block;color:var(--ink2);font-size:12px}
.pair{display:grid;grid-template-columns:1fr;gap:3px}
.hb{display:flex;align-items:center;gap:8px;height:20px}
.hb .fill{height:100%;border-radius:3px;min-width:3px}
.hb .val{font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}
.hb .val.zero{color:var(--ink2)}
.cov{margin:4px 0 18px}.cov:last-child{margin-bottom:4px}
.cov .head{font-size:14px;margin-bottom:6px}.cov .head b{font-variant-numeric:tabular-nums}
.cov .bar{height:28px}
.cov .seg{color:var(--ink)}
.cov .seg.shared{color:var(--on)}
.keys{display:flex;flex-wrap:wrap;gap:4px 18px;margin-top:6px;font-size:12px;color:var(--ink2)}
.keys .dot{margin-right:5px;vertical-align:-1px}
.check{color:var(--ours-ink);font-weight:700;margin-right:6px}.cross{color:var(--ink2);margin-right:6px}
.fair{margin:12px 0 0;padding:10px 14px;border:1px dashed var(--ring);border-radius:8px;color:var(--ink2);font-size:13px;max-width:900px}
@media (max-width:640px){.sc{grid-template-columns:1fr}.lead{font-size:17px}}
</style></head><body><main>
<h1>Gene–disease extraction: our method vs PubTator3</h1>
<p class="lead" id="lead"></p>
<p class="sub">Same __SCOPE__. Our method reads the parsed full text with the decision card (variant <b>__VARIANT__</b>), using one initial request and at most one repair. PubTator3 results are precomputed annotations fetched by PMID and aligned locally; its relations are primarily abstract-derived. Neither system is used as the answer key. Output counts and disagreements do not establish relative accuracy or recall.</p>
<div class="tiles" id="tiles"></div>

<h2>Head to head</h2>
<div class="legend"><span class="sw"><span class="dot" style="background:var(--ours)"></span>Our method</span><span class="sw"><span class="dot" style="background:var(--pt)"></span>PubTator3</span></div>
<div class="panel" id="scorecard"></div>
<p class="note">Each row is scaled to its own larger value.</p>

<h2>Relation overlap</h2>
<div class="panel" id="coverage"></div>
<p class="note">Relations matched through aligned entities. Every segment is a disjoint count; the two bars use different totals.</p>
<div class="takeaway" id="takeaway"></div>

<h2>Output fields and cost</h2>
<div class="panel"><table id="capabilities"></table></div>
<div class="fair"><b>PubTator3.</b> <span id="fair"></span></div>

<h2>Selected examples</h2>
<p class="note">These examples were selected by hand to show different disagreements. They are not a random sample.</p>
<div class="cols" id="examples"></div>

<h2>Overlap by level</h2>
<div class="legend" id="legend"></div>
<div class="panel" id="overlap"></div>
<p class="note">Each bar is one level, scaled to 100% of the items either system found; labels show counts. PubTator also tags symptoms and general terms as Disease; <span id="scopeNote"></span></p>

<h2>Gene–disease relations per paper</h2>
<div class="panel" id="perpaper"></div>
<p class="note">Bars share one scale. Our method also marks pairs as <i>uncertain</i> or <i>explicit_negative</i>; PubTator has no such states (counts in the table below).</p>

<h2>Why the relation sets differ</h2>
<div class="cols">
 <div class="panel"><b>Only our method</b><table id="whyOurs"></table></div>
 <div class="panel"><b>Only PubTator</b><table id="whyPT"></table></div>
</div>

<h2>Every relation disagreement</h2>
<div class="controls"><label>Show <select id="fcat"><option value="">all</option><option value="ours_only">only our method</option><option value="pubtator_only">only PubTator</option><option value="both">both</option></select></label>
<label>Paper <select id="fpaper"><option value="">all</option></select></label></div>
<div class="panel"><table id="rels"></table></div>

<h2>Per-paper table</h2>
<div class="panel"><table id="papers"></table></div>

<h2>Entity differences</h2>
<p class="note">Names as PubTator normalised them, with the text it tagged in brackets. Several PubTator-only "diseases" are abbreviation mis-normalisations (e.g. ECM, EMC, PC) or general words; others are phenotypes our method did not list.</p>
<div class="panel" id="entities"></div>
</main><div id="tip"></div>
<script>
const D = __DATA__;
const CAT = {both:{label:"Both", var:"--both"}, pubtator_only:{label:"Only PubTator", var:"--pt"}, ours_only:{label:"Only our method", var:"--ours"}};
const col = c => `var(${CAT[c].var})`;
const SOURCE = {"背景引用": "background", "本研究结果": "this study", "两者兼有": "background + this study", "不确定": "source unclear"};
const sum = k => D.papers.reduce((a, p) => a + p[k], 0);
const tip = document.getElementById("tip");
function hover(el, text){el.addEventListener("mouseenter",e=>{tip.textContent=text;tip.style.display="block";move(e)});el.addEventListener("mousemove",move);el.addEventListener("mouseleave",()=>tip.style.display="none")}
function move(e){let x=e.clientX+14,y=e.clientY+14;if(x+tip.offsetWidth>innerWidth-8)x=e.clientX-tip.offsetWidth-14;if(y+tip.offsetHeight>innerHeight-8)y=e.clientY-tip.offsetHeight-14;tip.style.left=x+"px";tip.style.top=y+"px"}
function el(tag, attrs={}, text){const n=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n}

const K = D.key;
const pct = (a, b) => Math.round(100 * a / Math.max(1, b)) + "%";
const n = x => Number(x).toLocaleString("en-US");
const ratio = (K.our_supported / Math.max(1, K.pubtator_relations)).toFixed(1);
const lead = document.getElementById("lead");
lead.append(`Our method reports ${n(K.our_supported)} gene–disease relations, compared with ${n(K.pubtator_relations)} from PubTator3 (${ratio} times as many). Each includes source sentences; ${pct(K.evidence_body_only, K.our_supported)} cite only body text, tables or captions.`);

const tiles = [
 ["Relations reported", `${ratio}×`, `${n(K.our_supported)} by our method vs ${n(K.pubtator_relations)} by PubTator3`],
 ["Relations with quoted evidence", `${n(K.our_supported)} vs 0`, "each of ours cites the sentence(s) it rests on; PubTator gives a score only"],
 ["Evidence beyond the abstract", pct(K.evidence_body_only, K.our_supported), `${n(K.evidence_body_only)} of our ${n(K.our_supported)} relations rest only on body text, tables or captions`],
 K.this_study_shared < K.this_study
  ? ["Study-finding labels absent from PubTator3", `${n(K.this_study - K.this_study_shared)} of ${n(K.this_study)}`, "relations our method labels as study findings that PubTator3 does not predict"]
  : ["Agreement on the papers' own findings", `${n(K.this_study_shared)} of ${n(K.this_study)}`, "relations our method attributes to the study itself are also predicted by PubTator3"],
];
if (K.spanish_genes) tiles.push(["Non-English paper", `${K.spanish_genes} vs 0 genes`, `Spanish full text: PubTator3 found no genes; we found ${K.spanish_genes} genes and ${K.spanish_relations} relations`]);
tiles.forEach(([k,v,s])=>{const t=el("div",{class:"tile"});t.append(el("div",{class:"k"},k),el("div",{class:"v big"},String(v)),el("div",{class:"s"},s));document.getElementById("tiles").append(t)});

// Head-to-head scorecard: one row per capability, each scaled to its own larger value.
const score = [
 ["Gene–disease relations reported", "", K.our_supported, K.pubtator_relations],
 ["… with a quoted supporting sentence", "traceable to block and character position", K.our_supported, 0],
 ["… labelled as this study's result vs background", "new finding vs restated knowledge", K.our_supported, 0],
 ["Pairs flagged uncertain or explicitly negative", "with a stated reason; PubTator only predicts", K.uncertain + K.negative, 0],
 ["Genes recognised", "aligned by text position", K.genes_ours, K.genes_pt],
];
if (K.spanish_genes) score.push(["Genes in the Spanish full text", "PMC8626062", K.spanish_genes, 0]);
const sc = document.getElementById("scorecard");
score.forEach(([lab, sub, ours, theirs])=>{const row=el("div",{class:"sc"});const l=el("div",{class:"lab"},lab);if(sub)l.append(el("small",{},sub));
  const pair=el("div",{class:"pair"});const max=Math.max(ours,theirs,1);
  [[ours,"--ours","Our method"],[theirs,"--pt","PubTator3"]].forEach(([v,c,who])=>{const hb=el("div",{class:"hb"});const f=el("div",{class:"fill"});
    f.style.width=v?`calc(${(85*v/max).toFixed(2)}%)`:"3px";f.style.background=v?`var(${c})`:"var(--grid)";
    hb.append(f,el("span",{class:"val"+(v?"":" zero")},v?n(v):"0 — not provided"));hover(hb,`${who}: ${n(v)}`);pair.append(hb)});
  row.append(l,pair);sc.append(row)});

// Coverage: what share of the other system's relations each one also reports, with the rest split by reason.
function coverage(head, total, parts){const box=el("div",{class:"cov"});const h=el("div",{class:"head"});h.innerHTML=head;box.append(h);
  const bar=el("div",{class:"bar"});const keys=el("div",{class:"keys"});
  parts.forEach(([v,c,label,shared])=>{if(!v)return;const s=el("div",{class:"seg"+(shared?" shared":"")});s.style.background=`var(${c})`;s.style.width=(100*v/total)+"%";
    if(100*v/total>6)s.textContent=n(v);hover(s,`${label}: ${n(v)} (${pct(v,total)})`);bar.append(s);
    const k=el("span");const d=el("span",{class:"dot"});d.style.background=`var(${c})`;k.append(d,`${label} — ${n(v)}`);keys.append(k)});
  box.append(bar,keys);document.getElementById("coverage").append(box)}
coverage(`Our method supports <b>${n(K.pt_matched)} (${pct(K.pt_matched,K.pubtator_relations)})</b> of PubTator3's <b>${n(K.pubtator_relations)}</b> relations`,
  K.pubtator_relations,
  [[K.pt_matched,"--both","also supported by our method",true],
   [K.pt_only_judged,"--mid","we read the pair and judged it not supported (not_found / uncertain / negative)"],
   [K.pt_only_symptom,"--light","its 'disease' is a symptom/phenotype in our rules"],
   [K.pt_only_missing_entity,"--pt","we did not record one of the entities"]]);
coverage(`PubTator3 predicts <b>${n(K.ours_matched)} (${pct(K.ours_matched,K.our_supported)})</b> of our <b>${n(K.our_supported)}</b> relations`,
  K.our_supported,
  [[K.ours_matched,"--both","also predicted by PubTator3",true],
   [K.ours_only_pt_has_entities,"--mid","PubTator3 tagged both entities but predicted no relation"],
   [K.ours_only_missing_entity,"--ours","PubTator3 missed the gene or the disease"]]);

document.getElementById("takeaway").textContent =
 `For ${n(K.ours_only_pt_has_entities)} of the ${n(K.ours_only)} pairs reported only by our method, PubTator3 tagged both entities but predicted no relation. ` +
 (K.ours_only_background === K.ours_only
   ? "Our method labels all of these relations as background knowledge. "
   : `Our method labels ${n(K.ours_only_background)} as background knowledge and ${n(K.ours_only - K.ours_only_background)} as the paper's own results. `) +
 `Of the ${n(K.pt_only)} pairs reported only by PubTator3, ${n(K.pt_only_judged + K.pt_only_symptom)} received non-supported or symptom labels from our method; ${n(K.pt_only_missing_entity)} involve an entity it did not capture. These categories still need manual review. ` +
 `Cost: about $${K.cost_per_paper.toFixed(2)} and ${Math.round(K.seconds_per_paper)} s per paper.`;

const caps = [
 ["Reads", true, "Full text: body, tables, captions", "Full-text entity tags; relations mainly from abstracts"],
 ["Evidence for each relation", true, "Quoted sentence(s) with block and character position", "None (relation prediction with a score)"],
 ["Relation states", true, "supported / uncertain / explicit_negative / not_found", "Predicted only"],
 ["Source of a relation", true, "Background knowledge vs this study's result, kept apart", "Not distinguished"],
 ["Symptoms vs diseases", true, "Kept apart (symptoms in an auxiliary table)", "Both tagged as Disease"],
 ["Non-English full text", true, "Works on the original text", "No usable annotation in the Spanish paper"],
 ["Cost and speed", false, `≈$${K.cost_per_paper.toFixed(2)} and ${Math.round(K.seconds_per_paper)} s per paper`, "Precomputed, free to query"],
];
const ct = document.getElementById("capabilities");
const ch = el("tr");["", "Our method", "PubTator3"].forEach(h=>ch.append(el("th",{},h)));ct.append(ch);
caps.forEach(([a,win,b,c])=>{const tr=el("tr");const ours=el("td",{class:"yes"});const theirs=el("td");
  ours.append(el("span",{class:win?"check":"cross"},win?"✓":"–"),b);theirs.append(el("span",{class:win?"cross":"check"},win?"✗":"✓"),c);
  tr.append(el("td",{class:"no"},a),ours,theirs);ct.append(tr)});
document.getElementById("fair").textContent =
 `The annotations are precomputed and free to query. PubTator3 reports ${n(K.diseases_pt_only)} disease entities absent from our output, including symptoms, general terms, apparent abbreviation errors and conditions our method did not capture. ` +
 `The disagreement table includes all ${n(K.pt_only)} relations reported only by PubTator3.`;

const exBox = document.getElementById("examples");
D.examples.forEach(r=>{const card=el("div",{class:"ex"});const tag=el("span",{class:"tag"},CAT[r.category].label);tag.style.background=col(r.category);
  card.append(tag,el("h3",{},`${r.our_gene||r.gene} → ${r.our_disease||r.disease}`),
    el("div",{class:"meta"},`${r.paper_id} · PubTator: ${r.pubtator_relation?r.pubtator_relation+" (score "+(+r.pubtator_score).toFixed(2)+")":"no relation"} · ours: ${r.our_status?[r.our_status,r.our_relation!=="none"?r.our_relation:"",SOURCE[r.our_source]||r.our_source].filter(Boolean).join(", "):"no pair"}`),
    el("div",{},r.detail||r.our_reason||""));
  if(r.our_evidence)card.append(el("blockquote",{},r.our_evidence.split(" || ")[0].replace(/^b\d+: /,"")));
  exBox.append(card)});

Object.keys(CAT).forEach(c=>{const s=el("span",{class:"sw"});const d=el("span",{class:"dot"});d.style.background=col(c);s.append(d,CAT[c].label);document.getElementById("legend").append(s)});

function stacked(container, label, parts, total, scale, tipPrefix){
  const row=el("div",{class:"row"});row.append(el("div",{class:"lab",title:label},label));
  const bar=el("div",{class:"bar"});
  parts.forEach(([c,n])=>{if(!n)return;const s=el("div",{class:"seg"});s.style.background=col(c);s.style.width=(100*n/scale)+"%";
    if(100*n/scale>4)s.textContent=n;hover(s,`${tipPrefix}${CAT[c].label}: ${n}`);bar.append(s)});
  row.append(bar,el("div",{class:"tot"},String(total)));container.append(row)}
const ov=document.getElementById("overlap");
[["Genes","genes"],["Diseases","diseases"],["Relations","relations"]].forEach(([lab,k])=>{
  const parts=[["both",sum(k+"_both")],["pubtator_only",sum(k+"_pubtator_only")],["ours_only",sum(k+"_ours_only")]];
  const total=parts.reduce((a,[,n])=>a+n,0);stacked(ov,lab,parts,total,total,lab+" · ")});
document.getElementById("scopeNote").textContent=`${sum("pubtator_disease_is_our_symptom_or_phenotype")} PubTator "diseases" are kept by our rules as symptoms/phenotypes and are not counted above.`;

const pp=document.getElementById("perpaper");
const maxRel=Math.max(...D.papers.map(p=>p.relations_both+p.relations_pubtator_only+p.relations_ours_only),1);
D.papers.forEach(p=>{const parts=[["both",p.relations_both],["pubtator_only",p.relations_pubtator_only],["ours_only",p.relations_ours_only]];
  stacked(pp,`${p.paper_id} · ${p.type.replace("-article","")}`,parts,parts.reduce((a,[,n])=>a+n,0),maxRel,`${p.paper_id} · `)});

function reasonTable(id, cat){const t=document.getElementById(id);const counts={};
  D.relations.filter(r=>r.category===cat).forEach(r=>{const k=r.detail||"—";counts[k]=(counts[k]||0)+1});
  t.append(Object.assign(el("tr"),{innerHTML:"<th>Reason</th><th>Relations</th>"}));
  Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([k,n])=>{const tr=el("tr");tr.append(el("td",{},k),el("td",{class:"num"},String(n)));t.append(tr)})}
reasonTable("whyOurs","ours_only");reasonTable("whyPT","pubtator_only");

const fpaper=document.getElementById("fpaper");D.papers.forEach(p=>fpaper.append(el("option",{value:p.paper_id},p.paper_id)));
function renderRels(){const t=document.getElementById("rels");t.innerHTML="";
  const head=el("tr");["Paper","Found by","Gene","Disease","PubTator prediction","Our judgment","Why they differ / our reason","Our evidence"].forEach(h=>head.append(el("th",{},h)));t.append(head);
  const fc=document.getElementById("fcat").value,fp=fpaper.value;
  D.relations.filter(r=>(!fc||r.category===fc)&&(!fp||r.paper_id===fp)).forEach(r=>{const tr=el("tr");
    const tag=el("span",{class:"tag"},CAT[r.category].label);tag.style.background=col(r.category);
    const ev=el("td",{class:"quote"});if(r.our_evidence){const d=el("details");d.append(el("summary",{},"show"),el("div",{},r.our_evidence));ev.append(d)}
    const td=el("td");td.append(tag);
    tr.append(el("td",{},r.paper_id),td,el("td",{},r.our_gene||r.gene),el("td",{},r.our_disease||r.disease),
      el("td",{},r.pubtator_relation?`${r.pubtator_relation} (score ${(+r.pubtator_score).toFixed(2)})`:"none"),
      el("td",{},r.our_status?[r.our_status,r.our_relation!=="none"?r.our_relation:"",SOURCE[r.our_source]||r.our_source].filter(Boolean).join(" · "):"no pair"),
      el("td",{},[r.detail,r.our_reason].filter(Boolean).join(" — ")),ev);t.append(tr)})}
document.getElementById("fcat").addEventListener("change",renderRels);fpaper.addEventListener("change",renderRels);renderRels();

const pt=document.getElementById("papers");
const ph=el("tr");["Paper","Type","Chars","Genes both / PT / ours","Diseases both / PT / ours","Relations both / PT / ours","Our uncertain","Our negative","Our time (s)","Our cost ($)","Note"].forEach(h=>ph.append(el("th",{},h)));pt.append(ph);
D.papers.forEach(p=>{const tr=el("tr");[p.paper_id,p.type,p.chars,`${p.genes_both} / ${p.genes_pubtator_only} / ${p.genes_ours_only}`,
  `${p.diseases_both} / ${p.diseases_pubtator_only} / ${p.diseases_ours_only}`,`${p.relations_both} / ${p.relations_pubtator_only} / ${p.relations_ours_only}`,
  p.our_uncertain,p.our_explicit_negative,Math.round(p.seconds),p.cost.toFixed(2),p.note].forEach((v,i)=>tr.append(el("td",{class:i>=2&&i<=9?"num":""},String(v))));pt.append(tr)});

const ent=document.getElementById("entities");
D.entities.forEach(e=>{const d=el("details");d.append(el("summary",{},`${e.paper_id}: genes only PubTator ${e.genes_pubtator_only.length}, only ours ${e.genes_ours_only.length}; diseases only PubTator ${e.diseases_pubtator_only.length}, only ours ${e.diseases_ours_only.length}`));
  const grid=el("div",{class:"cols"});
  [["Genes only PubTator",e.genes_pubtator_only],["Genes only our method",e.genes_ours_only],["Diseases only PubTator",e.diseases_pubtator_only],["Diseases only our method",e.diseases_ours_only],["PubTator 'diseases' we keep as symptoms",e.pubtator_disease_is_our_symptom_or_phenotype]].forEach(([h,list])=>{
    const box=el("div");box.append(el("b",{},`${h} (${list.length})`));const ul=el("ul");list.forEach(x=>ul.append(el("li",{},x)));box.append(ul);grid.append(box)});
  d.append(grid);ent.append(d)});
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:3])
