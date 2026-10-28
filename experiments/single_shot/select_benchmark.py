"""Pick the fixed 12-paper benchmark by seeded random sampling within strata, and freeze it to benchmark_12.json.

Usage: python experiments/single_shot/select_benchmark.py        (refuses to overwrite an existing benchmark)

Papers already used to build or tune the rules are excluded, so the benchmark measures unseen papers.
The conference collection is excluded too; it needs unit splitting and is tested separately.
"""
import csv
import json
import random

from common import HERE, PROJECT

SEED = 20261028
EXCLUDED = {
    "PMC10014009": "used to build the rules and the card (development paper)",
    "PMC10487392": "used repeatedly while building the single-shot pipeline (development paper)",
    "PMC6240673": "development reference of the earlier LLM workflow",
    "PMC10994491": "multi-study conference collection; tested separately",
}
SPANISH = "PMC8626062"  # the only non-English paper; included on purpose as the language-robustness case
STRATA = [  # (name, filter, count)
    ("research, short (<31k chars)", lambda r: r["article_type"] == "research-article" and r["chars"] < 31354, 2),
    ("research, medium (31k-52k)", lambda r: r["article_type"] == "research-article" and 31354 <= r["chars"] < 51933, 3),
    ("research, long (>=52k)", lambda r: r["article_type"] == "research-article" and r["chars"] >= 51933, 2),
    ("case report (English)", lambda r: r["article_type"] == "case-report" and r["paper_id"] != SPANISH, 1),
    ("review", lambda r: r["article_type"] in ("review-article", "systematic-review"), 2),
    ("short other (letter, editorial, discussion, brief report)",
     lambda r: r["article_type"] in ("letter", "editorial", "discussion", "brief-report"), 1),
]


def main():
    out = HERE / "benchmark_12.json"
    if out.exists():
        raise SystemExit(f"{out} already exists; the benchmark is frozen.")
    with (PROJECT / "outputs" / "inventory.csv").open(encoding="utf-8-sig") as stream:
        papers = [{"paper_id": r["paper_id"], "article_type": r["article_type"], "chars": int(r["characters"]),
                   "title": r["title"]} for r in csv.DictReader(stream) if r["paper_id"] not in EXCLUDED]
    rng = random.Random(SEED)
    chosen = [{**next(p for p in papers if p["paper_id"] == SPANISH), "stratum": "case report (Spanish, fixed)"}]
    for name, keep, count in STRATA:
        pool = sorted((p for p in papers if keep(p) and p["paper_id"] != SPANISH), key=lambda p: p["paper_id"])
        for p in rng.sample(pool, count):
            chosen.append({**p, "stratum": name})
    benchmark = {"seed": SEED, "excluded": EXCLUDED, "strata": [[n, c] for n, _, c in STRATA],
                 "note": "Frozen benchmark for A/B tests. Do not tune rules on these papers' outputs.",
                 "papers": chosen}
    out.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in chosen:
        print(f"{p['paper_id']:12} {p['article_type']:17} {p['chars']:7}  {p['stratum']:40} {p['title'][:60]}")
    print(f"{len(chosen)} papers, {sum(p['chars'] for p in chosen)} characters -> {out}")


if __name__ == "__main__":
    main()
