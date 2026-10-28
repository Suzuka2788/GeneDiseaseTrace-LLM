"""Render the BioRED accuracy results as one self-contained HTML page (no external scripts).

Usage: python experiments/biored/render_results.py [variant]   (default v1_card_lean_medium)
Main view: all 419 abstracts with a gene-disease relation (runs/biored_all, evaluate.py ... biored_all), with scores per
split. Head-to-head section: the frozen 50-abstract test sample, where PubTator3 was scored by the same rules
(runs/biored50/<variant> and runs/biored50/pubtator3); PubTator3 is not compared on Train/Dev, which it was trained on.
Writes runs/biored_all/<variant>/biored_results.html (and the same page to runs/biored50/<variant>/).
"""
import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "single_shot" / "runs"

# Hand-picked illustrations, shown under a heading that says they were selected: (paper, outcome, text in a name).
EXAMPLES = [
    ("PMID15485686", "TP", "SCN5A"),
    ("PMID17003923", "FN", "factor V"),
    ("PMID25277705", "FP", "Il4"),
    ("PMID26937641", "FN", "CCl4"),
    ("PMID15464247", "FP", "sustained virologic response"),
]
# Miss / extra reasons grouped into what they mean for the comparison.
FAMILY = {
    "our pair: not_found": "non-supported decision", "our pair: uncertain": "non-supported decision",
    "our pair: explicit_negative": "non-supported decision",
    "disease not recorded by us": "entity missing or excluded", "disease recorded by us as symptom/phenotype": "entity missing or excluded",
    "gene not recorded by us": "entity missing or excluded",
    "gold has both concepts but no relation": "relation not annotated in gold",
    "disease not a gold disease concept": "our error: endpoint taken as disease",
}


def read(path):
    with path.open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def head_to_head(our_rows):
    """PubTator3 scored by the same evaluate.py on the same abstracts, plus a gold-relation-by-relation comparison."""
    base = RUNS / "biored50" / "pubtator3"
    result = json.loads((base / "biored_eval.json").read_text(encoding="utf-8"))
    pt_rows = read(base / "biored_eval_rows.csv")
    key = lambda r: (r["paper_id"], r["gold_gene"], r["gold_disease"])
    ours = {key(r): r for r in our_rows if r["outcome"] != "FP"}
    pt = {key(r): r for r in pt_rows if r["outcome"] != "FP"}
    if ours.keys() != pt.keys():
        raise SystemExit("gold relations differ between the two evaluations")
    both = lambda a, b: [k for k in ours if ours[k]["outcome"] == a and pt[k]["outcome"] == b]
    pt_only, ours_only = both("FN", "TP"), both("TP", "FN")

    def count(keys, side, field):
        values = [side[k][field] for k in keys]
        return dict(sorted(((v, values.count(v)) for v in set(values)), key=lambda x: -x[1]))

    silent = sorted(p for p, c in result["per_paper"].items() if c["our_supported"] == 0 and c["fn"] > 0)
    return {"result": {k: result[k] for k in ("strict", "counts", "fp_reasons", "fn_reasons")},
            "both": len(both("TP", "TP")), "pt_only": len(pt_only), "ours_only": len(ours_only), "neither": len(both("FN", "FN")),
            "pt_only_our_reason": count(pt_only, ours, "detail"), "ours_only_papers": count(ours_only, ours, "paper_id"),
            "pt_silent_papers": silent, "pt_silent_gold": sum(result["per_paper"][p]["fn"] for p in silent)}


def main(variant="v1_card_lean_medium"):
    base = RUNS / "biored_all" / variant
    result = json.loads((base / "biored_eval.json").read_text(encoding="utf-8"))
    rows = read(base / "biored_eval_rows.csv")
    runs = {r["paper_id"]: r for r in read(base / "summary.csv")}
    sample = json.loads((HERE / "sample_all.json").read_text(encoding="utf-8"))
    docs = {d["id"]: d for split in ("Train", "Dev", "Test")
            for d in json.loads((HERE / "data" / "BioRED" / f"{split}.BioC.JSON").read_text(encoding="utf-8"))["documents"]}
    base50 = RUNS / "biored50" / variant
    result50 = json.loads((base50 / "biored_eval.json").read_text(encoding="utf-8"))
    papers = [{"paper_id": p["paper_id"], "split": p["split"], "in50": p["in_sample_50"],
               "title": docs[p["pmid"]]["passages"][0]["text"], "gold": p["gold_gene_disease"],
               **result["per_paper"][p["paper_id"]],
               "cost": float(runs[p["paper_id"]]["cost_usd"]), "seconds": float(runs[p["paper_id"]]["seconds"]),
               "calls": int(runs[p["paper_id"]]["calls"])} for p in sample["papers"]]
    examples = []
    for paper, outcome, text in EXAMPLES:
        examples += [r for r in rows if r["paper_id"] == paper and r["outcome"] == outcome
                     and any(text in r[k] for k in ("gold_gene", "gold_disease", "our_gene", "our_disease"))][:1]
    # Rows go in column form (field names once) to keep the page small; the script rebuilds the objects.
    fields = list(rows[0])
    packed = {"fields": fields, "values": [[r.get(f, "") for f in fields] for r in rows]}
    data = {"variant": variant, "result": {k: v for k, v in result.items() if k != "per_paper"}, "rows": packed, "papers": papers, "examples": examples, "family": FAMILY,
            "sample": {k: sample[k] for k in ("abstracts", "eligible", "criteria")},
            "ours50": {k: result50[k] for k in ("strict", "supported_or_uncertain", "counts", "novelty")},
            "pubtator": head_to_head(read(base50 / "biored_eval_rows.csv"))}
    page = TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__VARIANT__", html.escape(variant))
    for out in (base / "biored_results.html", base50 / "biored_results.html"):
        out.write_text(page, encoding="utf-8")
        print(out)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BioRED Accuracy Results</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--grid:#e1e0d9;--ring:rgba(11,11,11,.10);
--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--on:#ffffff;--good:#0f7a52;--mid:#b4b2a8;--light:#e1dfd7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--c1:#3987e5;--c2:#d95926;--c3:#199e70;--good:#4cc89a;--mid:#6b6a63;--light:#3d3c38}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--ring:rgba(255,255,255,.10);--c1:#3987e5;--c2:#d95926;--c3:#199e70;--good:#4cc89a;--mid:#6b6a63;--light:#3d3c38}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 56px}
h1{font-size:24px;margin:0 0 6px}h2{font-size:18px;margin:36px 0 6px}h3{font-size:15px;margin:0 0 6px}
.lead{font-size:19px;line-height:1.45;margin:10px 0;max-width:900px}.lead b{color:var(--good)}
.sub{color:var(--ink2);margin:0 0 4px;max-width:900px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:18px}
.tile,.panel,.ex{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:14px 16px}
.panel{overflow-x:auto}
.tile .k{color:var(--ink2);font-size:13px}.tile .v{font-size:26px;white-space:nowrap;font-weight:600;font-variant-numeric:tabular-nums}
.tile .s{color:var(--ink2);font-size:12px}
.note{color:var(--ink2);font-size:13px;margin:6px 0}
.legend{display:flex;gap:18px;flex-wrap:wrap;color:var(--ink2);font-size:13px;margin:8px 0}
.sw{display:inline-flex;align-items:center;gap:6px}.dot{width:12px;height:12px;border-radius:3px;display:inline-block}
.metric{display:grid;grid-template-columns:90px 1fr;gap:6px 12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--grid)}
.metric:last-child{border-bottom:0}.metric .name{font-weight:600}
.track{position:relative;height:20px;margin:3px 0}
.track .fill{position:absolute;left:0;top:3px;height:14px;border-radius:3px}
.track .ci{position:absolute;top:9px;height:2px;background:var(--ink)}
.track .ci::before,.track .ci::after{content:"";position:absolute;top:-4px;width:2px;height:10px;background:var(--ink)}
.track .ci::before{left:0}.track .ci::after{right:0}
.track .lab{position:absolute;top:0;font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}
.axis{position:relative;height:16px;margin-left:102px;color:var(--ink2);font-size:11px}
.axis span{position:absolute;transform:translateX(-50%)}
.bar{display:flex;height:28px;gap:2px;margin:4px 0}
.seg{height:100%;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:var(--on);min-width:2px}
.seg.dark{color:var(--ink)}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.reason{display:grid;grid-template-columns:minmax(150px,240px) 1fr 40px;gap:8px;align-items:center;margin:5px 0;font-size:13px}
.reason .b{height:16px;border-radius:3px}.reason .n{text-align:right;font-variant-numeric:tabular-nums;color:var(--ink2)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--grid);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--ink2);font-weight:600}th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
td.hit{font-weight:700;color:var(--good)}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap;color:var(--on)}
.takeaway{margin:14px 0 0;padding:12px 16px;border-left:4px solid var(--c3);background:var(--panel);border-radius:0 8px 8px 0;max-width:900px}
.ex .meta{color:var(--ink2);font-size:12px;margin:4px 0}
.controls{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0;color:var(--ink2);font-size:13px}
select{font:inherit;padding:3px 6px;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px;padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.18);display:none;z-index:10;max-width:320px}
@media (max-width:640px){.lead{font-size:17px}.reason{grid-template-columns:1fr 40px}.reason .b{grid-column:1/-1}}
</style></head><body><main>
<h1>Accuracy on BioRED: gene–disease relations</h1>
<p class="lead" id="lead"></p>
<p class="sub" id="setup"></p>
<div class="tiles" id="tiles"></div>

<h2>Results by BioRED's original splits</h2>
<p class="sub">The pipeline was not trained or prompt-tuned on BioRED. Results are reported separately for its original Train / Dev / Test splits. Overlapping confidence intervals do not establish equivalence, and foundation-model pretraining exposure was not assessed.</p>
<div class="panel" id="splits"></div>
<p class="note">Strict setting; whiskers are bootstrap 95% intervals. Dev and Test have about 70 abstracts each, so their intervals are wider.</p>

<h2>Head to head with PubTator3 (50-abstract test sample)</h2>
<p class="sub">PubTator3's public abstract annotations for the frozen 50-abstract relation-positive test sample, aligned to the same text and scored by the same script and rules. PubTator3 uses BioRED in training; the exact training split of the deployed models was not verified. Both systems' numbers in this section are for these same 50 abstracts.</p>
<div class="legend"><span class="sw"><span class="dot" style="background:var(--c3)"></span>Our method</span><span class="sw"><span class="dot" style="background:var(--c2)"></span>PubTator3</span></div>
<div class="panel" id="h2h"></div>
<p class="note">Metric rows share a 0–1 scale; count rows are scaled to their larger value. For our method, recall and F1 are shown strict and with pairs we flagged uncertain counted as predictions.</p>
<div class="cols" style="margin-top:16px">
 <div class="panel"><h3 id="vennHead"></h3><div class="bar" id="vennBar"></div><div class="legend" id="vennKeys"></div><p class="note" id="vennNote"></p></div>
 <div class="panel"><h3 id="ptOnlyHead"></h3><div id="ptOnly"></div><p class="note">Most of the gap is pairs our method read and deliberately left at <i>uncertain</i> or <i>not_found</i>, plus symptoms and broad terms ("tumor", "infection") that BioRED and PubTator3 count as diseases and our rules do not.</p></div>
</div>
<div class="takeaway" id="h2hTake"></div>

<h2>Precision, recall and F1</h2>
<div class="legend" id="opLegend"></div>
<div class="panel"><div id="metrics"></div><div class="axis" id="axis"></div></div>
<p class="note">Whiskers: bootstrap 95% intervals (2,000 resamples of abstracts). <b>Strict</b>: every gold relation counts, only <i>supported</i> pairs are predictions. <b>Scope-adjusted</b>: gold relations whose "disease" our rules record as a symptom/phenotype are set aside. <b>Supported + uncertain</b>: pairs we flagged uncertain also count as predictions.</p>
<div class="takeaway" id="takeaway"></div>

<h2>What happened to every relation</h2>
<div class="cols">
 <div class="panel"><h3 id="goldHead"></h3><div class="bar" id="goldBar"></div><div class="legend" id="goldKeys"></div></div>
 <div class="panel"><h3 id="oursHead"></h3><div class="bar" id="oursBar"></div><div class="legend" id="oursKeys"></div></div>
</div>

<h2>Why gold relations were missed, and why we reported extra ones</h2>
<div class="legend" id="famLegend"></div>
<div class="cols">
 <div class="panel"><h3 id="fnHead"></h3><div id="fn"></div></div>
 <div class="panel"><h3 id="fpHead"></h3><div id="fp"></div></div>
</div>

<h2>This study vs background: agreement with BioRED's novelty label</h2>
<div class="cols">
 <div class="panel"><table id="novelty"></table></div>
 <div class="panel"><b>Relation type on matched pairs</b><table id="types"></table><p class="note">BioRED labels most gene–disease relations <i>Association</i>; our rules use association / correlation / causal. Not scored as a metric.</p></div>
</div>

<h2>Selected examples</h2>
<p class="note">Hand-picked to illustrate each kind of outcome; every row is in the full table below.</p>
<div class="cols" id="examples"></div>

<h2>How to read these numbers</h2>
<div class="panel"><table id="context"></table></div>

<h2>Per abstract</h2>
<div class="panel"><table id="papers"></table></div>

<h2>Every scored relation</h2>
<div class="controls"><label>Show <select id="fout"><option value="">all</option><option value="TP">found (TP)</option><option value="FN">missed (FN)</option><option value="FP">extra (FP)</option></select></label>
<label>Abstract <select id="fpaper"><option value="">all</option></select></label></div>
<div class="panel"><table id="rows"></table></div>
</main><div id="tip"></div>
<script>
const D = __DATA__, R = D.result, C = R.counts;
D.rows = D.rows.values.map(v => Object.fromEntries(D.rows.fields.map((f, i) => [f, v[i]])));
const tip = document.getElementById("tip");
function hover(el, text){el.addEventListener("mouseenter",e=>{tip.textContent=text;tip.style.display="block";move(e)});el.addEventListener("mousemove",move);el.addEventListener("mouseleave",()=>tip.style.display="none")}
function move(e){let x=e.clientX+14,y=e.clientY+14;if(x+tip.offsetWidth>innerWidth-8)x=e.clientX-tip.offsetWidth-14;if(y+tip.offsetHeight>innerHeight-8)y=e.clientY-tip.offsetHeight-14;tip.style.left=x+"px";tip.style.top=y+"px"}
function el(tag, attrs={}, text){const n=document.createElement(tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n}
const f2 = x => x.toFixed(2), pct = (a,b) => Math.round(100*a/Math.max(1,b)) + "%";
const sum = k => D.papers.reduce((a,p)=>a+p[k],0);
const SCALE = 0.9; // bars use 90% of the track so value labels fit
const cost = sum("cost"), secs = sum("seconds");
const nov = R.novelty;

const P = D.pubtator, PR = P.result.strict, PC = P.result.counts;
const O = D.ours50, R50 = O, C50 = O.counts, nov50 = O.novelty;
const SPL = R.by_split, splitF1 = Object.values(SPL).map(v=>v.strict.f1);
document.getElementById("lead").append(`On the ${D.papers.length} relation-positive BioRED abstracts, `, el("b",{},`pair-detection precision is ${f2(R.strict.precision)} and recall is ${f2(R.strict.recall)}`),
  ` (precision 95% CI ${R.strict.ci95.precision.map(f2).join("–")}). On the separate 50-abstract comparison, precision estimates are ${f2(R50.strict.precision)} vs ${f2(PR.precision)} (ours vs PubTator3); similar estimates do not establish equivalence.`);
document.getElementById("setup").textContent = `BioRED (Luo et al. 2022): ${D.sample.abstracts} expert-annotated PubMed abstracts; every one with at least one gene–disease relation is included — ${D.papers.length} abstracts (` +
  Object.entries(SPL).map(([k,v])=>`${k} ${v.papers}`).join(", ") + `), ${C.tp_gold + C.fn} gold relations, no sampling. ` +
  `Our method: Claude Opus 5.5, one initial request with validation-triggered repair, frozen variant ${D.variant}, the same decision card as the 100-paper run without BioRED-specific prompt tuning. Entities are matched by overlapping mention spans; relation-type agreement is not required. The other ${D.sample.abstracts-D.papers.length} abstracts were not evaluated, so these are subset pair-detection scores, not official full-task BioRED scores. Quote/offset validation checks provenance, not semantic entailment.`;

[["Precision", f2(R.strict.precision), `${C.tp_ours} of our ${C.our_supported} supported pairs are in the gold set · 95% CI ${R.strict.ci95.precision.map(f2).join("–")}`],
 ["Scores by original split", `F1 ${f2(Math.min(...splitF1))}–${f2(Math.max(...splitF1))}`, Object.entries(SPL).map(([k,v])=>`${k} ${f2(v.strict.f1)}`).join(" · ") + " (strict)"],
 ["Recall", `${f2(R.strict.recall)} → ${f2(R.supported_or_uncertain.recall)}`, `strict, then counting our uncertain pairs as predictions (precision ${f2(R.strict.precision)} → ${f2(R.supported_or_uncertain.precision)})`],
 ["F1", `${f2(R.strict.f1)} – ${f2(R.supported_or_uncertain.f1)}`, "strict to supported + uncertain"],
 ["Novelty agreement", pct(nov.agree, nov.compared), `${nov.agree} of ${nov.compared} matched relations: this study vs background agrees with BioRED`],
 ["Cost", `$${(cost/D.papers.length).toFixed(3)}`, `per abstract, ${Math.round(secs/D.papers.length)} s; $${cost.toFixed(2)} for all ${D.papers.length}`],
].forEach(([k,v,s])=>{const t=el("div",{class:"tile"});t.append(el("div",{class:"k"},k),el("div",{class:"v"},v),el("div",{class:"s"},s));document.getElementById("tiles").append(t)});

// Per split: one group per split, P / R / F1 tracks with CI whiskers.
const sp=document.getElementById("splits");
Object.entries(SPL).forEach(([name,v])=>{const row=el("div",{class:"metric",style:"grid-template-columns:150px 1fr"});
  const l=el("div");l.append(el("div",{class:"name"},name),el("div",{class:"note",style:"margin:0"},`${v.papers} abstracts · ${v.gold} relations`));
  const box=el("div");[["precision","P"],["recall","R"],["f1","F1"]].forEach(([m,short])=>{const val=v.strict[m],ci=v.strict.ci95[m];
    const line=el("div",{style:"display:grid;grid-template-columns:28px 1fr;align-items:center"});line.append(el("span",{class:"note",style:"margin:0"},short));
    const tr=el("div",{class:"track"});const fl=el("div",{class:"fill"});fl.style.width=(100*SCALE*val)+"%";fl.style.background=`var(${m==="precision"?"--c3":m==="recall"?"--c1":"--c2"})`;
    const w=el("div",{class:"ci"});w.style.left=(100*SCALE*ci[0])+"%";w.style.width=(100*SCALE*(ci[1]-ci[0]))+"%";
    const lb=el("div",{class:"lab"},f2(val));lb.style.left=`calc(${100*SCALE*ci[1]}% + 8px)`;tr.append(fl,w,lb);hover(tr,`${name} · ${m}: ${f2(val)} (95% CI ${ci.map(f2).join("–")})`);
    line.append(tr);box.append(line)});
  row.append(l,box);sp.append(row)});

// Head to head with PubTator3 (50-abstract test sample): paired bars per row.
const H = [
 ["Precision", "share of reported relations in the gold set", R50.strict.precision, PR.precision, true],
 ["Recall", "strict → uncertain counted", R50.strict.recall, PR.recall, true, R50.supported_or_uncertain.recall],
 ["F1", "strict → uncertain counted", R50.strict.f1, PR.f1, true, R50.supported_or_uncertain.f1],
 ["This study vs background correct", `share of matched relations, all ${D.papers.length} abstracts`, nov.agree / Math.max(1, nov.compared), null, true],
 ["Relations with a quoted supporting sentence", "", C50.our_supported, 0, false],
 ["Pairs flagged uncertain or explicitly negative", "each with a stated reason", C50.uncertain_or_negative, 0, false],
];
const hb = document.getElementById("h2h");
H.forEach(([lab, sub, ours, theirs, ratio, alt])=>{const row=el("div",{class:"metric",style:"grid-template-columns:minmax(150px,260px) 1fr"});const l=el("div");l.append(el("div",{class:"name"},lab));if(sub)l.append(el("div",{class:"note",style:"margin:0"},sub));
  const box=el("div");const max=ratio?1:Math.max(ours,theirs||0,1);
  [[ours,"--c3","Our method",alt],[theirs,"--c2","PubTator3"]].forEach(([v,c,who,a])=>{const tr=el("div",{class:"track"});
    if(!v){tr.append(el("div",{class:"lab",style:"left:0;color:var(--ink2)"},v===null?"not provided":"0 — not provided"));box.append(tr);return}
    const w=100*SCALE*Math.max(v,a||0)/max;
    if(a){const ghost=el("div",{class:"fill"});ghost.style.width=w+"%";ghost.style.background=`var(${c})`;ghost.style.opacity=".35";tr.append(ghost)}
    const fl=el("div",{class:"fill"});fl.style.width=(100*SCALE*v/max)+"%";fl.style.background=`var(${c})`;
    const txt=ratio?(a?`${f2(v)} → ${f2(a)}`:f2(v)):String(v);
    const lb=el("div",{class:"lab"},txt);lb.style.left=`calc(${w}% + 8px)`;tr.append(fl,lb);hover(tr,`${who} · ${lab}: ${txt}`);box.append(tr)});
  row.append(l,box);hb.append(row)});

// Metrics chart: one group per metric, one bar per operating point, CI whiskers, 0-1 scale.
const OPS = [["strict","Strict","--c1"],["scope_adjusted","Scope-adjusted","--c2"],["supported_or_uncertain","Supported + uncertain","--c3"]];
OPS.forEach(([,lab,c])=>{const s=el("span",{class:"sw"});const d=el("span",{class:"dot"});d.style.background=`var(${c})`;s.append(d,lab);document.getElementById("opLegend").append(s)});
["precision","recall","f1"].forEach(m=>{const row=el("div",{class:"metric"});row.append(el("div",{class:"name"},m==="f1"?"F1":m[0].toUpperCase()+m.slice(1)));
  const box=el("div");OPS.forEach(([k,lab,c])=>{const v=R[k][m],ci=R[k].ci95[m];const tr=el("div",{class:"track"});
    const fl=el("div",{class:"fill"});fl.style.width=(100*SCALE*v)+"%";fl.style.background=`var(${c})`;
    const w=el("div",{class:"ci"});w.style.left=(100*SCALE*ci[0])+"%";w.style.width=(100*SCALE*(ci[1]-ci[0]))+"%";
    const lb=el("div",{class:"lab"},f2(v));lb.style.left=`calc(${100*SCALE*ci[1]}% + 8px)`;
    tr.append(fl,w,lb);hover(tr,`${lab} · ${m}: ${f2(v)} (95% CI ${ci.map(f2).join("–")})`);box.append(tr)});
  row.append(box);document.getElementById("metrics").append(row)});
const axis=document.getElementById("axis");[0,.25,.5,.75,1].forEach(t=>{const s=el("span",{},t.toFixed(2));s.style.left=(100*SCALE*t)+"%";axis.append(s)});

document.getElementById("takeaway").textContent =
 `Of ${C.fn} missed gold relations, ${Object.entries(R.fn_reasons).filter(([k])=>D.family[k]==="non-supported decision").reduce((a,[,n])=>a+n,0)} have both entities captured but a non-supported label, including not_found, uncertain and explicit_negative. This categorizes outputs, not the correctness of the rejection. ` +
 `Counting uncertain as positive moves recall from ${f2(R.strict.recall)} to ${f2(R.supported_or_uncertain.recall)} and precision from ${f2(R.strict.precision)} to ${f2(R.supported_or_uncertain.precision)}. Independent adjudication is needed to separate policy differences from extraction errors.`;

// Outcome bars
function bar(id, keysId, parts){const b=document.getElementById(id),k=document.getElementById(keysId);const tot=parts.reduce((a,p)=>a+p[1],0);
  parts.forEach(([lab,n,c,dark])=>{if(!n)return;const s=el("div",{class:"seg"+(dark?" dark":"")});s.style.background=`var(${c})`;s.style.width=(100*n/tot)+"%";if(100*n/tot>7)s.textContent=n;hover(s,`${lab}: ${n} (${pct(n,tot)})`);b.append(s);
    const kk=el("span",{class:"sw"});const d=el("span",{class:"dot"});d.style.background=`var(${c})`;kk.append(d,`${lab} — ${n}`);k.append(kk)})}
document.getElementById("goldHead").textContent=`BioRED's ${C.tp_gold + C.fn} gold relations`;
const fam = R.fn_reasons, by = f => Object.entries(fam).filter(([k])=>D.family[k]===f).reduce((a,[,n])=>a+n,0);
bar("goldBar","goldKeys",[["found by our method",C.tp_gold,"--c3"],["both entities captured, non-supported label",by("non-supported decision"),"--mid",true],["entity missing or excluded",by("entity missing or excluded"),"--light",true]]);
document.getElementById("oursHead").textContent=`Our ${C.our_supported} supported pairs`;
bar("oursBar","oursKeys",[["in the gold set",C.tp_ours,"--c3"],["gold has both entities, no relation annotated",R.fp_reasons["gold has both concepts but no relation"]||0,"--mid",true],["our error",C.our_supported-C.tp_ours-(R.fp_reasons["gold has both concepts but no relation"]||0),"--c2"]]);

// Who found which gold relation
document.getElementById("vennHead").textContent=`The test sample's ${C50.tp_gold + C50.fn} gold relations: who found which`;
bar("vennBar","vennKeys",[["both systems",P.both,"--c1"],["only PubTator3",P.pt_only,"--c2"],["only our method",P.ours_only,"--c3"],["neither",P.neither,"--light",true]]);
const recovered = P.pt_silent_papers.reduce((a,p)=>a+(P.ours_only_papers[p]||0),0);
document.getElementById("vennNote").textContent=`Together the two systems find ${P.both+P.pt_only+P.ours_only} of ${C50.tp_gold + C50.fn} (${pct(P.both+P.pt_only+P.ours_only, C50.tp_gold + C50.fn)}). `+
  (P.pt_silent_papers.length?`In ${P.pt_silent_papers.join(", ")} PubTator3 predicted no relation at all (${P.pt_silent_gold} gold relations); our method recovered ${recovered} of them.`:"");
document.getElementById("ptOnlyHead").textContent=`The ${P.pt_only} relations only PubTator3 found: what our method did`;
(()=>{const box=document.getElementById("ptOnly");const max=Math.max(...Object.values(P.pt_only_our_reason));
  Object.entries(P.pt_only_our_reason).forEach(([k,n])=>{const r=el("div",{class:"reason"});const b=el("div",{class:"b"});b.style.width=(100*n/max)+"%";
    b.style.background=`var(${k.startsWith("our pair")?"--c1":"--mid"})`;const w=el("div");w.append(b);
    r.append(el("div",{},k.replace("our pair: ","read the pair, judged ")),w,el("div",{class:"n"},String(n)));box.append(r)})})();
const deliberate = Object.entries(P.pt_only_our_reason).filter(([k])=>k.startsWith("our pair")).reduce((a,[,n])=>a+n,0);
document.getElementById("h2hTake").textContent =
 `On this 50-abstract sample, precision estimates are ${f2(R50.strict.precision)} vs ${f2(PR.precision)}; PubTator3 has higher recall (${f2(PR.recall)} vs ${f2(R50.strict.recall)}) and F1 (${f2(PR.f1)} vs ${f2(R50.strict.f1)}). These results do not establish equal precision. ` +
 `${deliberate} of the ${P.pt_only} relations found only by PubTator3 received non-supported judgments from our pipeline. Their correctness requires separate review. ` +
 `Additional outputs include source labels (${pct(nov.agree, nov.compared)} agreement conditional on matched relations across ${D.papers.length} abstracts), quoted source sentences and uncertain states. Our method found ${P.ours_only} gold relations absent from the PubTator3 predictions.`;

// Reasons
const FAMC = {"non-supported decision":"--c1","entity missing or excluded":"--mid","relation not annotated in gold":"--light","our error: endpoint taken as disease":"--c2"};
Object.entries(FAMC).forEach(([f,c])=>{const s=el("span",{class:"sw"});const d=el("span",{class:"dot"});d.style.background=`var(${c})`;s.append(d,f);document.getElementById("famLegend").append(s)});
function reasons(id, obj){const box=document.getElementById(id);const max=Math.max(...Object.values(obj));
  Object.entries(obj).sort((a,b)=>b[1]-a[1]).forEach(([k,n])=>{const r=el("div",{class:"reason"});const b=el("div",{class:"b"});b.style.width=(100*n/max)+"%";b.style.background=`var(${FAMC[D.family[k]]||"--mid"})`;
    const wrap=el("div");wrap.append(b);r.append(el("div",{},k),wrap,el("div",{class:"n"},String(n)));hover(r,`${k}: ${n} · ${D.family[k]||""}`);box.append(r)})}
document.getElementById("fnHead").textContent=`Missed gold relations (${C.fn})`;reasons("fn",R.fn_reasons);
document.getElementById("fpHead").textContent=`Our supported pairs not in gold (${C.our_supported - C.tp_ours})`;reasons("fp",R.fp_reasons);

// Novelty matrix
const tpRows = D.rows.filter(r=>r.outcome==="TP");
const M = {}; tpRows.forEach(r=>{const k=r.our_source+"|"+r.gold_novel;M[k]=(M[k]||0)+1});
const nt=document.getElementById("novelty");
nt.innerHTML=`<tr><th>Our source label</th><th class="num">BioRED: Novel</th><th class="num">BioRED: not novel</th></tr>`;
[["this study","Novel"],["both","Novel"],["background","No"],["unclear",""]].forEach(([s,expect])=>{const tr=el("tr");tr.append(el("td",{},s==="both"?"background + this study":s));
  ["Novel","No"].forEach(g=>{const n=M[s+"|"+g]||0;tr.append(el("td",{class:"num"+(expect===g&&n?" hit":"")},String(n)))});nt.append(tr)});
const cap=el("tr");const td=el("td",{colspan:"3",class:"note"},`Agreement on ${nov.compared} matched relations: ${nov.agree} (${pct(nov.agree,nov.compared)}). "This study" and "both" count as Novel, "background" as not novel; bold cells agree.`);cap.append(td);nt.append(cap);
const tt=document.getElementById("types");tt.innerHTML=`<tr><th>BioRED type</th><th>Our type</th><th class="num">Pairs</th></tr>`;
Object.entries(R.relation_types_on_tp).sort((a,b)=>b[1]-a[1]).forEach(([k,n])=>{const [g,o]=k.split(" -> ");const tr=el("tr");tr.append(el("td",{},g),el("td",{},o),el("td",{class:"num"},String(n)));tt.append(tr)});

// Examples
const OUT = {TP:["Found","--c3"],FN:["Missed","--c1"],FP:["Extra","--c2"]};
D.examples.forEach(r=>{const card=el("div",{class:"ex"});const tag=el("span",{class:"tag"},OUT[r.outcome][0]);tag.style.background=`var(${OUT[r.outcome][1]})`;
  const gene=r.our_gene||r.gold_gene, dis=r.our_disease||r.gold_disease;
  card.append(tag,el("h3",{style:"margin-top:6px"},`${gene} → ${dis}`),
    el("div",{class:"meta"},`${r.paper_id} · BioRED: ${r.gold_type?r.gold_type+" ("+(r.gold_novel==="Novel"?"novel":"not novel")+")":"no relation"} · ours: ${r.our_status?[r.our_status,r.our_relation,r.our_source].filter(Boolean).join(", "):"no pair"}`),
    el("div",{},[r.detail,r.our_reason].filter(Boolean).join(" — ")));document.getElementById("examples").append(card)});

// Context
const ct=document.getElementById("context");
ct.innerHTML="<tr><th>System</th><th>Setting</th><th class='num'>F1</th><th>Comparable to ours?</th></tr>";
[["Our method, all splits (this page)",`Zero-shot, one request per abstract, ${D.papers.length} abstracts; ⟨gene, disease⟩ pairs only; entities from raw text; relation type not required`,`${f2(R.strict.f1)}–${f2(R.supported_or_uncertain.f1)}`,"—"],
 ["Our method, 50-abstract test sample","Same, on the head-to-head sample",`${f2(R50.strict.f1)}–${f2(R50.supported_or_uncertain.f1)}`,"—"],
 ["PubTator3, 50-abstract test sample","NCBI production system, models trained on BioRED annotations; same abstracts, alignment and scoring as ours",f2(PR.f1),"Yes — same data and scoring, but trained on this annotation scheme"],
 ["PubMedBERT (Luo et al. 2022)","Supervised on BioRED training set; ⟨gene, disease⟩ entity-pair extraction","0.67","No — trained on BioRED, task setup differs"],
 ["GPT-4 / o1 (Brokman et al. 2025)","Zero-shot end-to-end; all BioRED relation types; relation type must match","0.10 / 0.23","No — harder setting (all types, exact type)"],
].forEach(r=>{const tr=el("tr");r.forEach((v,i)=>tr.append(el("td",{class:i===2?"num":""},v)));ct.append(tr)});
const cn=el("tr");cn.append(el("td",{colspan:"4",class:"note"},"The published numbers are background only: each uses a different task definition. The PubTator3 comparison uses 50 test abstracts, so its intervals are wide (see the head-to-head section)."));ct.append(cn);

// Per abstract
const pt=document.getElementById("papers");
pt.innerHTML="<tr><th>Abstract</th><th>Split</th><th>Title</th><th class='num'>Gold</th><th class='num'>Found</th><th class='num'>Missed</th><th class='num'>Our pairs</th><th class='num'>In gold</th><th class='num'>Calls</th><th class='num'>Cost ($)</th></tr>";
D.papers.forEach(p=>{const tr=el("tr");const a=el("a",{href:`https://pubmed.ncbi.nlm.nih.gov/${p.paper_id.slice(4)}/`,target:"_blank",rel:"noopener"},p.paper_id);const t0=el("td");t0.append(a);tr.append(t0,el("td",{},p.split+(p.in50?" · sample 50":"")),el("td",{},p.title));
  [p.gold,p.tp_gold,p.fn,p.our_supported,p.tp_ours,p.calls,p.cost.toFixed(3)].forEach(v=>tr.append(el("td",{class:"num"},String(v))));pt.append(tr)});

// All rows
const fp=document.getElementById("fpaper");D.papers.forEach(p=>fp.append(el("option",{value:p.paper_id},p.paper_id)));
function renderRows(){const t=document.getElementById("rows");t.innerHTML="<tr><th>Abstract</th><th>Outcome</th><th>Gene</th><th>Disease</th><th>BioRED</th><th>Ours</th><th>Why / our reason</th></tr>";
  const fo=document.getElementById("fout").value,fa=fp.value;
  D.rows.filter(r=>(!fo||r.outcome===fo)&&(!fa||r.paper_id===fa)).forEach(r=>{const tr=el("tr");const tag=el("span",{class:"tag"},OUT[r.outcome][0]);tag.style.background=`var(${OUT[r.outcome][1]})`;const t1=el("td");t1.append(tag);
    tr.append(el("td",{},r.paper_id),t1,el("td",{},r.our_gene||r.gold_gene),el("td",{},r.our_disease||r.gold_disease),
      el("td",{},r.gold_type?`${r.gold_type} · ${r.gold_novel==="Novel"?"novel":"not novel"}`:"—"),
      el("td",{},r.our_status?[r.our_status,r.our_relation,r.our_source].filter(Boolean).join(" · "):"no pair"),
      el("td",{},[r.detail,r.our_reason].filter(Boolean).join(" — ")));t.append(tr)})}
document.getElementById("fout").addEventListener("change",renderRows);fp.addEventListener("change",renderRows);renderRows();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:2])
