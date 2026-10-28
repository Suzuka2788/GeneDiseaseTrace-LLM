"""Render one self-contained HTML page summarising the A/B test of the variants on the frozen benchmark.

Usage: python experiments/single_shot/render_ab_summary.py v1_card_lean_medium v2_full_lean_medium v3_card_lean_low
The first variant is the baseline the others are compared with. Reads the files written by batch.py, compare.py
and compare_pubtator.py; writes runs/ab/ab_summary.html.
"""
import csv
import json
import sys

from common import HERE, RUNS
from render_vs_pubtator import key_numbers

LABELS = {
    "v1_card_lean_medium": ("v1", "Decision card · effort medium"),
    "v2_full_lean_medium": ("v2", "Full rule text · effort medium"),
    "v3_card_lean_low": ("v3", "Decision card · effort low"),
}


def read(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def variant_data(name, papers):
    base = RUNS / "ab" / name
    per_paper = []
    for paper_id in papers:
        run = json.loads((base / paper_id / "run.json").read_text(encoding="utf-8"))
        first = run["calls"][0]
        pairs = read(base / paper_id / "outputs" / "pairs.csv")
        entities = read(base / paper_id / "outputs" / "entities.csv")
        per_paper.append({"paper_id": paper_id, "calls": len(run["calls"]),
                          "first_cost": first.get("cost_usd") or 0, "first_seconds": first["seconds"],
                          "cost": sum(c.get("cost_usd") or 0 for c in run["calls"]),
                          "seconds": sum(c["seconds"] for c in run["calls"]),
                          "genes": sum(e["entity_type"] == "gene" for e in entities),
                          "targets": sum(e["entity_type"] != "gene" for e in entities),
                          **{s: sum(p["status"] == s for p in pairs) for s in ("supported", "uncertain", "explicit_negative")}})
    summary = read(base / "vs_pubtator_summary.csv")
    vs = {k: sum(int(s[k]) for s in summary) for k in summary[0] if k not in ("paper_id", "note")}
    vs_papers = [{"paper_id": s["paper_id"], **{k: int(v) for k, v in s.items() if k not in ("paper_id", "note")},
                  "cost": next(p["cost"] for p in per_paper if p["paper_id"] == s["paper_id"]),
                  "seconds": next(p["seconds"] for p in per_paper if p["paper_id"] == s["paper_id"])} for s in summary]
    key = key_numbers(base, read(base / "vs_pubtator_relations.csv"), vs_papers)
    return {"name": name, "short": LABELS.get(name, (name, name))[0], "description": LABELS.get(name, (name, name))[1],
            "per_paper": per_paper, "vs_pubtator": vs, "key": key}


def main(variants):
    benchmark = json.loads((HERE / "benchmark_12.json").read_text(encoding="utf-8"))
    papers = [p["paper_id"] for p in benchmark["papers"]]
    data = {"papers": [{k: p[k] for k in ("paper_id", "article_type", "chars", "stratum", "title")} for p in benchmark["papers"]],
            "seed": benchmark["seed"], "excluded": benchmark["excluded"],
            "variants": [variant_data(v, papers) for v in variants], "agreement": []}
    for other in variants[1:]:
        rows = [r for r in read(RUNS / "ab" / f"compare_{variants[0]}_vs_{other}.csv") if "supported_a" in r and r["supported_a"] != ""]
        both = sum(int(r["supported_both"]) for r in rows)
        a = sum(int(r["supported_a"]) for r in rows)
        b = sum(int(r["supported_b"]) for r in rows)
        shared = sum(int(r["pairs_compared"]) for r in rows)
        agree = sum(float(r["status_agreement"]) * int(r["pairs_compared"]) for r in rows if r["pairs_compared"] not in ("", "0"))
        data["agreement"].append({"variant": other, "supported_both": both, "supported_base": a, "supported_other": b,
                                  "jaccard": both / max(1, a + b - both), "shared_pairs": shared,
                                  "status_agreement": agree / max(1, shared)})
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = RUNS / "ab" / "ab_summary.html"
    out.write_text(page, encoding="utf-8")
    print(out)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A/B test summary</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--grid:#e1e0d9;--ring:rgba(11,11,11,.10);
--c0:#2a78d6;--c1:#eb6834;--c2:#1baf7a;--on:#ffffff}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--c0:#3987e5;--c1:#d95926;--c2:#199e70}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--c0:#3987e5;--c1:#d95926;--c2:#199e70}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
h1{font-size:24px;margin:0 0 6px}h2{font-size:18px;margin:36px 0 6px}h3{font-size:15px;margin:0 0 8px}
.sub{color:var(--ink2);margin:0 0 4px;max-width:900px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:16px}
.tile{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:14px 16px}
.tile .k{color:var(--ink2);font-size:13px}.tile .v{font-size:26px;font-weight:600}.tile .s{color:var(--ink2);font-size:12px}
.variants{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.vcard{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:12px 14px;border-top:4px solid}
.vcard .name{font-weight:700}.vcard .d{color:var(--ink2);font-size:13px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.panel{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:14px 16px;overflow-x:auto}
.row{display:grid;grid-template-columns:110px 1fr 90px;align-items:center;gap:10px;margin:7px 0}
.row .lab{text-align:right;color:var(--ink2);font-size:13px}
.track{position:relative;height:22px}
.bar{height:100%;border-radius:0 4px 4px 0}
.val{font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink)}
.note{color:var(--ink2);font-size:13px;margin:6px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--grid);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--ink2);font-weight:600}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.pgroup{display:grid;grid-template-columns:260px 1fr;gap:14px;padding:8px 0;border-bottom:1px solid var(--grid)}
.pgroup:last-child{border-bottom:0}
.plab .id{font-weight:600}.plab .t{color:var(--ink2);font-size:12px;line-height:1.3}
.mini{display:grid;grid-template-columns:24px 1fr 28px;align-items:center;gap:8px;margin:2px 0}
.mini .tag{font-size:11px;color:var(--ink2)}.mini .b{height:10px;border-radius:0 3px 3px 0;min-width:2px}
.mini .n{font-size:12px;font-variant-numeric:tabular-nums}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--ink2);font-size:13px;margin:8px 0}
.sw{display:inline-flex;align-items:center;gap:6px}.dot{width:12px;height:12px;border-radius:3px;display:inline-block}
.callout{margin:12px 0 0;padding:12px 16px;border-left:4px solid var(--c0);background:var(--panel);border-radius:0 8px 8px 0}
a{color:var(--c0)}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px;padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.18);display:none;z-index:10}
</style></head><body><main>
<h1>A/B test: how to run the extractor</h1>
<p class="sub">Three variants of the same single-request pipeline (Claude Opus 5.5) on the same frozen benchmark of 12 unseen papers (7 research articles, 2 case reports incl. one in Spanish, 2 reviews, 1 brief report; 463k characters). Each variant's rules and settings are frozen before the run.</p>
<p class="sub">There is no expert gold standard: the page compares cost, coverage and agreement. Agreement between variants is consistency, not accuracy.</p>
<div class="variants" id="variants"></div>

<h2>The 12 benchmark papers</h2>
<p class="note" id="benchNote"></p>
<div class="panel"><table id="bench"></table></div>

<h2>Result</h2>
<div class="tiles" id="tiles"></div>
<div class="callout" id="callout"></div>

<h2>Cost and time per run of 12 papers</h2>
<p class="note">Bars show totals including repairs; the detailed table also reports first-request costs. V1 ran before two parser fixes and needed extra repairs, so totals include that implementation difference.</p>
<div class="grid2"><div class="panel"><h3>Total cost including repairs (USD)</h3><div id="cost"></div></div><div class="panel"><h3>Total model time including repairs (minutes)</h3><div id="time"></div></div></div>

<h2>What each variant finds</h2>
<div class="grid2">
 <div class="panel"><h3>Supported gene–disease relations</h3><div id="supported"></div></div>
 <div class="panel"><h3>Genes / diseases also found by PubTator3</h3><div id="shared"></div></div>
 <div class="panel"><h3>Pairs marked uncertain</h3><div id="uncertain"></div></div>
 <div class="panel"><h3>Pairs marked explicit_negative</h3><div id="negative"></div></div>
</div>

<h2>Agreement with the baseline</h2>
<div class="panel"><table id="agree"></table></div>

<h2>Supported relations per paper</h2>
<div class="legend" id="legend"></div>
<div class="panel" id="perpaper"></div>
<p class="note">For each paper, one bar per variant: the number of gene–disease relations that variant judged <i>supported</i>. All bars share one scale. Hover a bar for its uncertain and explicit-negative counts too.</p>

<h2>Full table</h2>
<div class="panel"><table id="full"></table></div>

<h2>Per-variant comparison with PubTator3</h2>
<p class="note" id="links"></p>
</main><div id="tip"></div>
<script>
const D = __DATA__;
const V = D.variants, base = V[0];
const color = i => `var(--c${i})`;
const total = (v, k) => v.per_paper.reduce((a, p) => a + p[k], 0);
function el(tag, attrs={}, text){const n=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n}
const tip=document.getElementById("tip");
function hover(n,t){n.addEventListener("mouseenter",e=>{tip.textContent=t;tip.style.display="block";mv(e)});n.addEventListener("mousemove",mv);n.addEventListener("mouseleave",()=>tip.style.display="none")}
function mv(e){let x=e.clientX+14,y=e.clientY+14;if(x+tip.offsetWidth>innerWidth-8)x=e.clientX-tip.offsetWidth-14;tip.style.left=x+"px";tip.style.top=y+"px"}

V.forEach((v,i)=>{const c=el("div",{class:"vcard"});c.style.borderTopColor=color(i);c.append(el("div",{class:"name"},`${v.short}${i===0?" (baseline)":""}`),el("div",{class:"d"},v.description));document.getElementById("variants").append(c)});

document.getElementById("benchNote").textContent =
 `Drawn by seeded random sampling (seed ${D.seed}) within strata of article type and length, then frozen. ` +
 `Excluded beforehand: ${Object.keys(D.excluded).join(", ")} (papers used to build or debug the rules, and the multi-study conference collection). Rules are never tuned on these 12 papers' outputs.`;
const bt=document.getElementById("bench");
const bh=el("tr");["#","Paper","Type","Stratum","Length (k chars)","Title"].forEach((h,i)=>bh.append(el("th",{class:i===4?"num":""},h)));bt.append(bh);
D.papers.forEach((p,i)=>{const tr=el("tr");const link=el("a",{href:`https://pmc.ncbi.nlm.nih.gov/articles/${p.paper_id}/`,target:"_blank",rel:"noopener"},p.paper_id);
  const pc=el("td");pc.append(link);
  tr.append(el("td",{},String(i+1)),pc,el("td",{},p.article_type.replace("-article","")),el("td",{},p.stratum),el("td",{class:"num"},(p.chars/1000).toFixed(1)),el("td",{},p.title));bt.append(tr)});

const fmt = (x, d=0) => x.toFixed(d);
const pctChange = (a, b) => `${b >= a ? "+" : "−"}${Math.abs(Math.round(100 * (b - a) / a))}%`;
const bySub = s => V.find(v => v.short === s);
const v2 = bySub("v2"), v3 = bySub("v3");
const tiles = [];
if (v2) tiles.push(["Condensed card vs full rules", `${total(base,"supported")} vs ${total(v2,"supported")} relations`,
  `first-request cost ${pctChange(total(v2,"first_cost"), total(base,"first_cost"))}; total cost including repairs ${pctChange(total(v2,"cost"), total(base,"cost"))} vs full rules`]);
if (v3) tiles.push(["Effort medium vs low", `${pctChange(total(base,"seconds"), total(v3,"seconds"))} total time`,
  `including repairs: ${pctChange(total(base,"cost"), total(v3,"cost"))} cost, ${pctChange(total(base,"supported"), total(v3,"supported"))} supported labels and ${pctChange(total(base,"uncertain"), total(v3,"uncertain"))} uncertain labels`]);
tiles.push(["Working setting", base.short, `${base.description}: $${fmt(total(base,"cost")/12,2)} and ${Math.round(total(base,"seconds")/12)} s per paper, including repairs`]);
tiles.forEach(([k,v,s])=>{const t=el("div",{class:"tile"});t.append(el("div",{class:"k"},k),el("div",{class:"v"},v),el("div",{class:"s"},s));document.getElementById("tiles").append(t)});
document.getElementById("callout").textContent =
 `The baseline (${base.short}) was selected as the working configuration. More supported labels and high status agreement do not establish greater accuracy or equivalent quality. ` +
 (v2 ? `The largest label difference is in explicit negatives (${total(v2,"explicit_negative")} with full rules vs ${total(base,"explicit_negative")} with the card), mostly from one paper's CFTR variant comparisons. Those disagreements require independent adjudication. ` : "") +
 (v3 ? `Low effort used less time and cost, but labeled fewer pairs supported or uncertain. Completeness requires a gold standard.` : "");

function bars(id, key, unit, decimals=0, divisor=1){
  const box=document.getElementById(id);const vals=V.map(v=>(typeof key==="function"?key(v):total(v,key))/divisor);const max=Math.max(...vals,1e-9);
  V.forEach((v,i)=>{const row=el("div",{class:"row"});row.append(el("div",{class:"lab"},v.short));const tr=el("div",{class:"track"});const b=el("div",{class:"bar"});
    b.style.width=(100*vals[i]/max)+"%";b.style.background=color(i);hover(b,`${v.short}: ${unit}${fmt(vals[i],decimals)}`);tr.append(b);
    row.append(tr,el("div",{class:"val"},unit+fmt(vals[i],decimals)));box.append(row)})}
bars("cost","cost","$",2);
bars("time","seconds","",1,60);
bars("supported","supported","");
bars("uncertain","uncertain","");
bars("negative","explicit_negative","");
const sh=document.getElementById("shared");
V.forEach((v,i)=>{const row=el("div",{class:"row"});row.append(el("div",{class:"lab"},v.short));const tr=el("div",{class:"track"});
  const g=v.vs_pubtator.genes_both,d=v.vs_pubtator.diseases_both,max=Math.max(...V.map(x=>x.vs_pubtator.genes_both+x.vs_pubtator.diseases_both));
  const b=el("div",{class:"bar"});b.style.width=(100*(g+d)/max)+"%";b.style.background=color(i);hover(b,`${v.short}: ${g} genes, ${d} diseases shared with PubTator3`);tr.append(b);
  row.append(tr,el("div",{class:"val"},`${g} / ${d}`));sh.append(row)});

const at=document.getElementById("agree");
const ah=el("tr");["Compared with "+base.short,"Supported in both","Only baseline","Only this variant","Overlap (Jaccard)","Status agreement on shared pairs"].forEach((h,i)=>ah.append(el("th",{class:i?"num":""},h)));at.append(ah);
D.agreement.forEach(a=>{const tr=el("tr");[bySub(V.find(v=>v.name===a.variant).short).short,a.supported_both,a.supported_base-a.supported_both,a.supported_other-a.supported_both,fmt(a.jaccard,2),(100*a.status_agreement).toFixed(1)+"% of "+a.shared_pairs]
  .forEach((x,i)=>tr.append(el("td",{class:i?"num":""},String(x))));at.append(tr)});

V.forEach((v,i)=>{const s=el("span",{class:"sw"});const d=el("span",{class:"dot"});d.style.background=color(i);s.append(d,`${v.short} · ${v.description}`);document.getElementById("legend").append(s)});
const pp=document.getElementById("perpaper");const maxS=Math.max(...V.flatMap(v=>v.per_paper.map(p=>p.supported)),1);
D.papers.forEach(p=>{const g=el("div",{class:"pgroup"});const lab=el("div",{class:"plab"});
  lab.append(el("div",{class:"id"},`${p.paper_id} · ${p.article_type.replace("-article","")}`),el("div",{class:"t"},p.title.length>80?p.title.slice(0,78)+"…":p.title));
  const bars=el("div");
  V.forEach((v,i)=>{const r=v.per_paper.find(x=>x.paper_id===p.paper_id);const m=el("div",{class:"mini"});const tr=el("div");const b=el("div",{class:"b"});
    b.style.width=(100*r.supported/maxS)+"%";b.style.background=color(i);tr.append(b);
    hover(m,`${p.paper_id} · ${v.short}: ${r.supported} supported, ${r.uncertain} uncertain, ${r.explicit_negative} explicit_negative`);
    m.append(el("div",{class:"tag"},v.short),tr,el("div",{class:"n"},String(r.supported)));bars.append(m)});
  g.append(lab,bars);pp.append(g)});

const ft=document.getElementById("full");
const metrics=[["First-request cost (USD)",v=>"$"+fmt(total(v,"first_cost"),2)],["First-request time (min)",v=>fmt(total(v,"first_seconds")/60,1)],
 ["All requests cost (USD)",v=>"$"+fmt(total(v,"cost"),2)],["Papers passing on first request",v=>v.per_paper.filter(p=>p.calls===1).length+" / 12"],
 ["Genes",v=>total(v,"genes")],["Disease targets",v=>total(v,"targets")],["Supported relations",v=>total(v,"supported")],
 ["Uncertain pairs",v=>total(v,"uncertain")],["Explicit-negative pairs",v=>total(v,"explicit_negative")],
 ["Relations also predicted by PubTator3",v=>v.vs_pubtator.relations_both],["Relations only this variant",v=>v.vs_pubtator.relations_ours_only],
 ["PubTator3 relations not supported",v=>v.vs_pubtator.relations_pubtator_only],["Relations with evidence outside the abstract",v=>`${v.key.evidence_body_only} / ${v.key.our_supported}`]];
const fh=el("tr");fh.append(el("th",{},"Metric"));V.forEach(v=>fh.append(el("th",{class:"num"},v.short)));ft.append(fh);
metrics.forEach(([lab,f])=>{const tr=el("tr");tr.append(el("td",{},lab));V.forEach(v=>tr.append(el("td",{class:"num"},String(f(v)))));ft.append(tr)});

const links=document.getElementById("links");links.append("Detailed head-to-head pages: ");
V.forEach((v,i)=>{const a=el("a",{href:`${v.name}/vs_pubtator.html`},`${v.short} vs PubTator3`);links.append(a);if(i<V.length-1)links.append(" · ")});
</script></body></html>
"""

if __name__ == "__main__":
    main(sys.argv[1:])
