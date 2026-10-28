"""Build the public static showcase site (GitHub Pages) from the task presentation and the result pages.

Usage: python scripts/build_site.py
Writes site/ (its own git repository, published as the public repo GeneDiseaseTrace-LLM-site):
  index.html                                   presentation content (from site_index.html, English/Chinese), figures from the run records
  results/ab/ab_summary.html                   A/B test page (links to the three vs_pubtator pages beside it)
  results/ab/<variant>/vs_pubtator.html        12-paper comparison with PubTator3, per variant
  results/full100/vs_pubtator.html             100-paper comparison with PubTator3
  results/biored/biored_results.html           BioRED accuracy page
  graphs/index.html + graphs/*.json            per-paper gene-disease bipartite graphs (build_graph_data.py)
Nothing private goes in: no input papers, no download links, no local paths.
"""
import re
import shutil
from pathlib import Path

import build_graph_data

PROJECT = Path(__file__).resolve().parents[1]
RUNS = PROJECT / "experiments" / "single_shot" / "runs"
SITE = PROJECT / "site"
PAGES = {
    "results/ab/ab_summary.html": RUNS / "ab" / "ab_summary.html",
    "results/ab/v1_card_lean_medium/vs_pubtator.html": RUNS / "ab" / "v1_card_lean_medium" / "vs_pubtator.html",
    "results/ab/v2_full_lean_medium/vs_pubtator.html": RUNS / "ab" / "v2_full_lean_medium" / "vs_pubtator.html",
    "results/ab/v3_card_lean_low/vs_pubtator.html": RUNS / "ab" / "v3_card_lean_low" / "vs_pubtator.html",
    "results/full100/vs_pubtator.html": RUNS / "full100" / "v1_card_lean_medium" / "vs_pubtator.html",
    "results/biored/biored_results.html": RUNS / "biored_all" / "v1_card_lean_medium" / "biored_results.html",
}


def main():
    SITE.mkdir(exist_ok=True)
    for target, source in PAGES.items():
        out = SITE / target
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out)
    (SITE / "index.html").write_text(INDEX, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are
    build_graph_data.build(SITE)
    print(f"{SITE}: index.html + {len(PAGES)} result pages + graphs/")


def bilingual(template):
    """Expand [[English||中文]] into two spans; the page's language switch shows one of them."""
    def pair(m):
        en, zh = m.group(1), m.group(2)
        return f'<span data-l="en">{en}</span><span data-l="zh">{zh}</span>'
    out = re.sub(r"\[\[(.*?)\|\|(.*?)\]\]", pair, template, flags=re.S)
    if "[[" in out or "||" in out.split("<script>")[0]:
        raise SystemExit("unmatched [[...||...]] in site_index.html")
    return out


INDEX = bilingual((Path(__file__).with_name("site_index.html")).read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
