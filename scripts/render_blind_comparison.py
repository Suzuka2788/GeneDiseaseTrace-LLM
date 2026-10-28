"""Render a self-contained HTML page comparing several blind runs of one paper.

Usage: python scripts/render_blind_comparison.py outputs_blind_comparison/PMC10014009
Reads entity_alignment.json, aligned_pairs.csv and validation_<run>.json from that folder
(produced by compare_blind_runs.py and validate_contract.py) and writes comparison.html there.
"""
import csv
import html
import json
import sys
from pathlib import Path

STATUS_ORDER = ["supported", "uncertain", "explicit_negative", "not_found", "absent"]


def main(folder):
    folder = Path(folder)
    alignment = json.loads((folder / "entity_alignment.json").read_text(encoding="utf-8"))
    runs = list(alignment["runs"])
    with (folder / "aligned_pairs.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    validations = {}
    for run in runs:
        path = folder / f"validation_{run}.json"
        if path.exists():
            validations[run] = json.loads(path.read_text(encoding="utf-8"))

    summary = []
    for run in runs:
        v = validations.get(run, {})
        summary.append({"run": run, "passed": v.get("passed"), "genes": v.get("genes"), "targets": v.get("targets"),
                        "pairs": v.get("pairs"), **{s: (v.get("status_counts") or {}).get(s, 0) for s in STATUS_ORDER[:4]}})

    data = {
        "paper": alignment["paper_id"], "runs": runs,
        "genes": list(alignment["genes"]), "targets": list(alignment["targets"]),
        "absent": alignment.get("absent", {}), "summary": summary,
        "cells": [{"gene": r["gene"], "target": r["target"], "agreement": r["agreement"],
                   "runs": [{"status": r[run], "relation": r[f"{run}_relation"], "reason": r[f"{run}_reason"]} for run in runs]}
                  for r in rows],
    }
    page = TEMPLATE.replace("__TITLE__", html.escape(f"{alignment['paper_id']} blind run comparison"))
    page = page.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out = folder / "comparison.html"
    out.write_text(page, encoding="utf-8")
    print(out)


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);
--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--none:#ecebe6;--absent-line:#c3c2b7;--edge3:#0ca30c;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--none:#2f2f2c;--absent-line:#4a4a46;--accent:#3987e5}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#222220;--ink:#f0efec;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--none:#2f2f2c;--absent-line:#4a4a46;--accent:#3987e5}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:32px 0 8px}
.sub{color:var(--ink2);margin:0 0 16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.tile{background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:12px 14px}
.tile h3{margin:0 0 6px;font-size:14px}.tile .big{font-size:24px;font-weight:600}
.tile dl{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:8px 0 0;color:var(--ink2);font-size:13px}
.tile dd{margin:0;color:var(--ink);text-align:right;font-variant-numeric:tabular-nums}
.ok{color:var(--good)}.bad{color:var(--crit)}
.legend{display:flex;flex-wrap:wrap;gap:14px;align-items:center;color:var(--ink2);font-size:13px;margin:8px 0}
.sw{display:inline-flex;align-items:center;gap:6px}
.chip{width:16px;height:16px;border-radius:3px;display:inline-grid;place-items:center;font-size:11px;font-weight:700;color:#fff}
.scroll{overflow-x:auto;background:var(--panel);border:1px solid var(--ring);border-radius:8px;padding:8px}
table.m{border-collapse:separate;border-spacing:2px;font-size:12px}
table.m th{font-weight:600;color:var(--ink2);padding:2px 4px;white-space:nowrap}
table.m th.t{text-align:right;max-width:240px;overflow:hidden;text-overflow:ellipsis}
table.m th.g{writing-mode:vertical-rl;transform:rotate(180deg);height:118px;vertical-align:bottom;text-align:left}
.cell{display:flex;gap:2px;padding:2px;border-radius:4px;cursor:default}
.cell.dis{outline:2px solid var(--accent);outline-offset:0}
.st{width:16px;height:18px;border-radius:3px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#fff}
.st.supported{background:var(--good)}.st.uncertain{background:var(--warn);color:#0b0b0b}.st.explicit_negative{background:var(--crit)}
.st.not_found{background:var(--none)}.st.absent{background:transparent;border:1px dashed var(--absent-line)}
.note{color:var(--ink2);font-size:13px;margin:6px 0}
table.list{border-collapse:collapse;width:100%;font-size:13px;background:var(--panel)}
table.list th,table.list td{border-bottom:1px solid var(--grid);padding:6px 8px;text-align:left;vertical-align:top}
table.list th{color:var(--ink2);font-weight:600}
#tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--ink);border:1px solid var(--ring);border-radius:6px;
padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.18);max-width:360px;display:none;z-index:10}
#tip b{display:block;margin-bottom:4px}
svg text{fill:var(--ink);font-size:12px}
.controls{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0;color:var(--ink2);font-size:13px}
</style></head>
<body><main>
<h1 id="title"></h1>
<p class="sub">三个模型按同一规则（skill 1.2.0）独立完成的结果。颜色只表示判断状态，每个色块里还有符号，悬停可看详情。</p>

<h2>概况</h2>
<div class="tiles" id="tiles"></div>

<h2>逐对判断矩阵</h2>
<div class="legend" id="legend"></div>
<p class="note">每格三个小块，从左到右依次是 <span id="order"></span>。蓝框表示模型之间判断不一致。虚线空框表示该模型没有建这个实体。</p>
<div class="controls"><label><input type="checkbox" id="onlyInteresting"> 只看至少一个模型不是 not_found 的行</label></div>
<div class="scroll"><table class="m" id="matrix"></table></div>

<h2>共识二部图</h2>
<p class="note">实线：supported，线越粗表示越多模型判 supported（最粗 = 三个模型都判 supported；悬停可看各模型的判断）。虚线：没有模型判 supported、但至少一个判 uncertain，不是支持关系。</p>
<div class="controls"><label><input type="checkbox" id="showUncertain" checked> 显示 uncertain 虚线</label></div>
<div class="scroll"><svg id="graph" role="img" aria-label="consensus bipartite graph"></svg></div>

<h2>不一致与只在部分模型出现的实体</h2>
<table class="list" id="disagree"></table>
<h2>实体缺失说明</h2>
<table class="list" id="absent"></table>
</main>
<div id="tip"></div>
<script>
const D = __DATA__;
const LABEL = {supported:"supported",uncertain:"uncertain",explicit_negative:"explicit_negative",not_found:"not_found",absent:"未建实体"};
const GLYPH = {supported:"✓",uncertain:"?",explicit_negative:"✕",not_found:"",absent:""};
const SHORT = r => r.replace(/_/g," ");
document.getElementById("title").textContent = D.paper + "：三模型盲测结果对照";
document.getElementById("order").textContent = D.runs.map(SHORT).join(" → ");

const tiles = document.getElementById("tiles");
D.summary.forEach(s => {
  const t = document.createElement("div"); t.className = "tile";
  t.innerHTML = `<h3></h3><div class="big"></div><dl></dl>`;
  t.querySelector("h3").textContent = SHORT(s.run);
  t.querySelector(".big").textContent = `${s.genes} × ${s.targets} = ${s.pairs} 对`;
  const dl = t.querySelector("dl");
  [["公共校验", s.passed ? "✓ 通过" : "✕ 未通过"], ["supported", s.supported], ["uncertain", s.uncertain],
   ["explicit_negative", s.explicit_negative], ["not_found", s.not_found]].forEach(([k, v]) => {
    const dt = document.createElement("dt"); dt.textContent = k; const dd = document.createElement("dd"); dd.textContent = v;
    if (k === "公共校验") dd.className = s.passed ? "ok" : "bad";
    dl.append(dt, dd);
  });
  tiles.append(t);
});

const legend = document.getElementById("legend");
["supported","uncertain","explicit_negative","not_found","absent"].forEach(s => {
  const span = document.createElement("span"); span.className = "sw";
  span.innerHTML = `<span class="st ${s}">${GLYPH[s]}</span>`; span.append(LABEL[s]); legend.append(span);
});

const cellMap = new Map(D.cells.map(c => [c.gene + "|" + c.target, c]));
const tip = document.getElementById("tip");
function showTip(e, c) {
  tip.innerHTML = "";
  const b = document.createElement("b"); b.textContent = `${c.gene} × ${c.target}`; tip.append(b);
  c.runs.forEach((r, i) => {
    const line = document.createElement("div");
    let text = `${SHORT(D.runs[i])}：${LABEL[r.status] || r.status}`;
    if (r.relation && r.relation !== "none") text += ` / ${r.relation}`;
    const reason = (r.reason || "").replace(/[\[\]"]/g, "");
    if (reason) text += `（${reason}）`;
    line.textContent = text; tip.append(line);
  });
  tip.style.display = "block"; moveTip(e);
}
function moveTip(e) {
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = e.clientX + pad, y = e.clientY + pad;
  if (x + w > innerWidth - 8) x = e.clientX - w - pad;
  if (y + h > innerHeight - 8) y = e.clientY - h - pad;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() { tip.style.display = "none"; }

function renderMatrix() {
  const only = document.getElementById("onlyInteresting").checked;
  const table = document.getElementById("matrix"); table.innerHTML = "";
  const head = table.insertRow(); head.insertCell().outerHTML = "<th></th>";
  D.genes.forEach(g => { const th = document.createElement("th"); th.className = "g"; th.textContent = g; head.append(th); });
  D.targets.forEach(t => {
    const cells = D.genes.map(g => cellMap.get(g + "|" + t));
    if (only && cells.every(c => c.runs.every(r => r.status === "not_found" || r.status === "absent"))) return;
    const tr = table.insertRow();
    const th = document.createElement("th"); th.className = "t"; th.textContent = t; th.title = t; tr.append(th);
    cells.forEach(c => {
      const td = tr.insertCell(); const div = document.createElement("div");
      div.className = "cell" + (c.agreement === "disagree" ? " dis" : "");
      div.setAttribute("aria-label", `${c.gene} × ${t}: ` + c.runs.map((r, i) => `${D.runs[i]} ${r.status}`).join(", "));
      c.runs.forEach(r => { const s = document.createElement("span"); s.className = "st " + r.status; s.textContent = GLYPH[r.status] || ""; div.append(s); });
      div.addEventListener("mouseenter", e => showTip(e, c)); div.addEventListener("mousemove", moveTip); div.addEventListener("mouseleave", hideTip);
      td.append(div);
    });
  });
}
document.getElementById("onlyInteresting").addEventListener("change", renderMatrix);
renderMatrix();

function renderGraph() {
  const showU = document.getElementById("showUncertain").checked;
  const svg = document.getElementById("graph"); const NS = "http://www.w3.org/2000/svg";
  const row = 26, top = 30, left = 200, right = 560, width = 960;
  const n = Math.max(D.genes.length, D.targets.length), height = top + row * (n - 1) + 40;
  svg.setAttribute("width", width); svg.setAttribute("height", height); svg.setAttribute("viewBox", `0 0 ${width} ${height}`); svg.innerHTML = "";
  const gy = {}, ty = {};
  D.genes.forEach((g, i) => gy[g] = top + row * (n - 1) * i / Math.max(1, D.genes.length - 1));
  D.targets.forEach((t, i) => ty[t] = top + row * (n - 1) * i / Math.max(1, D.targets.length - 1));
  const linked = new Set();
  D.cells.forEach(c => {
    const sup = c.runs.filter(r => r.status === "supported").length;
    const unc = c.runs.filter(r => r.status === "uncertain").length;
    if (!sup && !(showU && unc)) return;
    const line = document.createElementNS(NS, "line");
    line.setAttribute("x1", left); line.setAttribute("y1", gy[c.gene]); line.setAttribute("x2", right); line.setAttribute("y2", ty[c.target]);
    if (sup) { line.setAttribute("stroke", "var(--good)"); line.setAttribute("stroke-width", 1 + sup); line.setAttribute("stroke-opacity", 0.4 + 0.2 * sup); linked.add(c.gene); linked.add(c.target); }
    else { line.setAttribute("stroke", "var(--warn)"); line.setAttribute("stroke-width", 1.5); line.setAttribute("stroke-dasharray", "4 4"); }
    line.addEventListener("mouseenter", e => showTip(e, c)); line.addEventListener("mousemove", moveTip); line.addEventListener("mouseleave", hideTip);
    const hit = line.cloneNode(); hit.setAttribute("stroke", "transparent"); hit.setAttribute("stroke-width", 10); hit.removeAttribute("stroke-dasharray");
    hit.addEventListener("mouseenter", e => showTip(e, c)); hit.addEventListener("mousemove", moveTip); hit.addEventListener("mouseleave", hideTip);
    svg.append(line, hit);
  });
  D.genes.forEach(g => {
    const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", left); c.setAttribute("cy", gy[g]); c.setAttribute("r", 5);
    c.setAttribute("fill", linked.has(g) ? "var(--ink)" : "var(--axis)");
    const t = document.createElementNS(NS, "text"); t.setAttribute("x", left - 10); t.setAttribute("y", gy[g] + 4); t.setAttribute("text-anchor", "end"); t.textContent = g;
    svg.append(c, t);
  });
  D.targets.forEach(tg => {
    const r = document.createElementNS(NS, "rect"); r.setAttribute("x", right - 5); r.setAttribute("y", ty[tg] - 5); r.setAttribute("width", 10); r.setAttribute("height", 10); r.setAttribute("rx", 2);
    r.setAttribute("fill", linked.has(tg) ? "var(--ink)" : "var(--axis)");
    const t = document.createElementNS(NS, "text"); t.setAttribute("x", right + 12); t.setAttribute("y", ty[tg] + 4); t.textContent = tg;
    svg.append(r, t);
  });
}
document.getElementById("showUncertain").addEventListener("change", renderGraph);
renderGraph();

function listTable(id, headers, rows) {
  const table = document.getElementById(id);
  const head = table.insertRow(); headers.forEach(h => { const th = document.createElement("th"); th.textContent = h; head.append(th); });
  rows.forEach(r => { const tr = table.insertRow(); r.forEach(v => { tr.insertCell().textContent = v; }); });
}
const interesting = D.cells.filter(c => c.agreement !== "all_agree" && c.runs.some(r => !["not_found","absent"].includes(r.status)));
listTable("disagree", ["基因", "目标"].concat(D.runs.map(SHORT)), interesting.map(c => [c.gene, c.target].concat(c.runs.map(r => LABEL[r.status] || r.status))));
const absentRows = [];
Object.entries(D.absent || {}).forEach(([run, items]) => Object.entries(items).forEach(([concept, why]) => absentRows.push([SHORT(run), concept, why])));
listTable("absent", ["模型", "实体", "去向"], absentRows);
</script>
</body></html>
"""

if __name__ == "__main__":
    main(sys.argv[1])
