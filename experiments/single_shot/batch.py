"""Run one frozen variant over the frozen benchmark, in parallel, resumable, with a per-paper summary.

Usage:
  python experiments/single_shot/batch.py --variant v1_card_lean_medium [--parallel 4] [--papers PMC1 PMC2]
  python experiments/single_shot/batch.py --variant v1_card_lean_medium --summary-only

A variant is a folder under variants/ holding card.md, format.md and variant.json (effort, description); its files
are copied there once and never edited, so later card changes cannot silently alter a finished variant.
Results: runs/ab/<variant>/<paper>/ (response, run.json, outputs/) and runs/ab/<variant>/summary.csv.
A paper with outputs/validation.json is skipped on rerun; a failed paper is retried.
"""
import argparse
import csv
import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from common import HERE, PROJECT, RUNS, sha256
from expand import expand, validate_run
from pack import paper_part
from run import MODELS, call

MODEL = "Claude_Opus_5.5"
OUT_ROOT = RUNS / "ab"  # set by --run-set
LIMIT_HIT = threading.Event()  # set once the CLI reports the subscription limit; later papers are not started


def variant_files(name):
    folder = HERE / "variants" / name
    config = json.loads((folder / "variant.json").read_text(encoding="utf-8"))
    fixed = (folder / "card.md").read_text(encoding="utf-8") + "\n\n" + (folder / "format.md").read_text(encoding="utf-8")
    hashes = {f: sha256(folder / f) for f in ("card.md", "format.md")}
    return config, fixed, hashes


def run_paper(variant, paper_id):
    config, fixed, hashes = variant_files(variant)
    run_dir = OUT_ROOT / variant / paper_id
    if (run_dir / "outputs" / "validation.json").exists():
        return paper_id, "skipped (done)"
    shutil.rmtree(run_dir, ignore_errors=True)
    workdir = run_dir / "empty_workdir"
    workdir.mkdir(parents=True)
    prompt, _ = paper_part(paper_id)
    meta = {"paper_id": paper_id, "variant": variant, "model": MODEL, "cli_model": MODELS[MODEL][1],
            "effort": config["effort"], "variant_hashes": hashes, "fixed_characters": len(fixed),
            "paper_characters": len(prompt), "calls": []}
    if LIMIT_HIT.is_set():
        shutil.rmtree(run_dir, ignore_errors=True)
        return paper_id, "not started (usage limit reached)"
    text, usage = call(MODEL, config["effort"], prompt, workdir, fixed)
    if "hit your session limit" in text or "usage limit" in text.lower():
        # The CLI answers instantly with a limit notice; nothing was judged, so leave the paper for the next run.
        LIMIT_HIT.set()
        shutil.rmtree(run_dir, ignore_errors=True)
        return paper_id, f"not started ({text.strip()[:90]})"
    meta["calls"].append(usage)
    (run_dir / "response.txt").write_text(text, encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    problems = expand(run_dir)
    if problems:
        repair = (prompt + "\n\n# Your previous output\n" + text + "\n\n# Problems found by the checker\n" +
                  "\n".join(problems) + "\n\nFix these problems and output the complete result again "
                  "(all lines, not only the changed ones).")
        text, usage = call(MODEL, config["effort"], repair, workdir, fixed)
        meta["calls"].append(usage)
        (run_dir / "response_first.txt").write_text((run_dir / "response.txt").read_text(encoding="utf-8"), encoding="utf-8")
        (run_dir / "response.txt").write_text(text, encoding="utf-8")
        meta["first_response_problems"] = problems
    (run_dir / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if problems:
        problems = expand(run_dir)
    if problems:
        (run_dir / "problems.txt").write_text("\n".join(problems), encoding="utf-8")
        return paper_id, f"failed after {len(meta['calls'])} call(s): {problems[0]}"
    _, failed = validate_run(run_dir)
    result = "ok" if not failed else "validation failed: " + ", ".join(c["check"] for c in failed)
    return paper_id, f"{result}, {len(meta['calls'])} call(s)"


def count(path, field=None, value=None):
    if not path.exists():
        return ""
    with path.open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    return sum(1 for r in rows if field is None or r.get(field) == value)


def summarise(variant, papers):
    rows = []
    for paper_id in papers:
        run_dir = OUT_ROOT / variant / paper_id
        if not (run_dir / "run.json").exists():
            rows.append({"paper_id": paper_id, "result": "not run"})
            continue
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        calls = meta["calls"]
        usage = [c.get("usage") or {} for c in calls]
        out = run_dir / "outputs"
        validation = json.loads((out / "validation.json").read_text(encoding="utf-8")) if (out / "validation.json").exists() else None
        failed_checks = [c["check"] for c in (validation or {}).get("checks", []) if not c["passed"] and c["check"] != "manifest_rule_hashes"]
        rows.append({
            "paper_id": paper_id, "result": "ok" if validation and not failed_checks else "failed",
            "calls": len(calls), "seconds": round(sum(c["seconds"] for c in calls), 1),
            "cost_usd": round(sum(c.get("cost_usd") or 0 for c in calls), 4),
            "input_tokens": sum(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0) for u in usage),
            "cache_read_tokens": sum(u.get("cache_read_input_tokens", 0) for u in usage),
            "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
            "thinking_tokens": sum(sum(m.get("thinkingTokens", 0) for m in (c.get("model_usage") or {}).values()) for c in calls),
            "genes": count(out / "entities.csv", "entity_type", "gene"),
            "targets": (count(out / "entities.csv") or 0) - (count(out / "entities.csv", "entity_type", "gene") or 0) if out.exists() else "",
            "auxiliary": count(out / "auxiliary_entities.csv"),
            "pairs": count(out / "pairs.csv"), "supported": count(out / "pairs.csv", "status", "supported"),
            "uncertain": count(out / "pairs.csv", "status", "uncertain"),
            "explicit_negative": count(out / "pairs.csv", "status", "explicit_negative"),
            "failed_checks": ";".join(failed_checks),
        })
    path = OUT_ROOT / variant / "summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(max(rows, key=len))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    done = [r for r in rows if r["result"] == "ok"]
    print(f"\n{variant}: {len(done)}/{len(rows)} ok; first-try {sum(r['calls'] == 1 for r in done)}/{len(done)}; "
          f"total {sum(r['seconds'] for r in done):.0f} s, {sum(r['cost_usd'] for r in done):.2f} USD; summary: {path}")
    for r in rows:
        print("  " + "  ".join(f"{k}={r[k]}" for k in ("paper_id", "result", "calls", "seconds", "cost_usd", "genes", "targets", "supported", "uncertain") if k in r))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", required=True)
    parser.add_argument("--papers", nargs="+")
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--run-set", default="ab", help="results go to runs/<run-set>/<variant>/ (default ab = the benchmark A/B)")
    parser.add_argument("--all", action="store_true", help="every paper in the input inventory instead of the benchmark")
    args = parser.parse_args()
    benchmark = json.loads((HERE / "benchmark_12.json").read_text(encoding="utf-8"))
    global OUT_ROOT
    OUT_ROOT = RUNS / args.run_set
    if args.all:
        with (PROJECT / "outputs" / "inventory.csv").open(encoding="utf-8-sig") as stream:
            papers = [r["paper_id"] for r in csv.DictReader(stream)]
    else:
        papers = args.papers or [p["paper_id"] for p in benchmark["papers"]]
    if not args.summary_only:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            for future in as_completed(pool.submit(run_paper, args.variant, p) for p in papers):
                paper_id, result = future.result()
                print(f"{paper_id}: {result}", flush=True)
    summarise(args.variant, papers)


if __name__ == "__main__":
    main()
