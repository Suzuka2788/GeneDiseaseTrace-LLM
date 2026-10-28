import argparse
import json
import platform
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .io import digest, read_json, write_csv, write_json
from .jats import parse_article
from .pubtator import extract_entities, fetch, pair_records, relation_predictions
from .quality import collection_quality
from .validate import validate


def prepare(config):
    directory = Path(config["input_dir"])
    paths = sorted(directory.glob("*.xml"))
    if not paths:
        raise ValueError(f"No XML articles in {directory.resolve()}")
    articles, failures = [], []
    for path in paths:
        try:
            article = parse_article(path, config.get("include_references", False))
            write_json(Path(config["cache_dir"]) / "articles" / f"{article['paper_id']}.json", article)
            articles.append(article)
        except (ValueError, OSError, SyntaxError) as error:
            failures.append({"source": str(path), "stage": "parse", "error": str(error)})
    output = Path(config["output_dir"])
    rows = [{"paper_id": a["paper_id"], "pmid": a["pmid"], "title": a["title"], "article_type": a["article_type"],
             "blocks": len(a["blocks"]), "characters": sum(len(b["text"]) for b in a["blocks"]),
             "table_rows": sum(b["content_type"] == "table_row" for b in a["blocks"]),
             "source_sha256": a["source_sha256"], "warnings": a["warnings"]} for a in articles]
    write_csv(output / "inventory.csv", rows,
              ["paper_id", "pmid", "title", "article_type", "blocks", "characters", "table_rows", "source_sha256", "warnings"])
    write_json(output / "parse_failures.json", failures)
    print(f"Parsed {len(articles)}/{len(paths)} XML articles; {len(failures)} failures", flush=True)
    return articles


def run(config, articles, *, limit=None, offline=False, fetch_only=False, paper=None):
    from .report import render_dashboard, render_paper
    output = Path(config["output_dir"])
    input_paper_ids = [article["paper_id"] for article in articles]
    if len(set(input_paper_ids)) != len(input_paper_ids):
        raise ValueError("Duplicate input paper IDs")
    if paper:
        articles = [a for a in articles if a["paper_id"] == paper]
        if not articles:
            raise ValueError(f"Unknown article {paper}")
    if limit is not None:
        articles = articles[:limit]
    run_id = uuid.uuid4().hex
    config_hash = digest(config)
    source_code_hash = digest({p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))})
    failures, results, cached = [], [], []
    for number, article in enumerate(articles, 1):
        pid = article["paper_id"]
        try:
            document = fetch(article["pmid"], config["cache_dir"], timeout=config.get("http_timeout", 45),
                             retries=config.get("max_retries", 2), interval=config.get("pubtator_request_interval", 0.55),
                             offline=offline)
            if fetch_only:
                cached.append(pid)
                print(f"[{number}/{len(articles)}] cached {pid}", flush=True)
                continue
            entities, unaligned = extract_entities(article, document)
            predictions = relation_predictions(document, entities)
            pairs = pair_records(article, entities, predictions)
            checks = validate(article, entities, pairs)
            if not checks["passed"]:
                raise ValueError("Integrity validation failed: " + "; ".join(checks["errors"]))
            counts = Counter(e["entity_type"] for e in entities)
            summary = {"paper_id": pid, "pmid": article["pmid"], "title": article["title"],
                       "genes": counts["gene"], "diseases": counts["disease"], "pairs": len(pairs),
                       "article_type": article["article_type"],
                       "predicted_edges": sum(p["status"] == "predicted" for p in pairs),
                       "supported_edges": sum(p["status"] == "supported" for p in pairs),
                       "aligned_mentions": checks["checked_mentions"],
                       "unaligned_annotation_events": len(unaligned),
                       "integrity_passed": checks["passed"], "semantic_verification": "not_run"}
            result = {"schema_version": 2, "run_id": run_id, "config_sha256": config_hash,
                      "summary": summary, "article": article, "entities": entities,
                      "pairs": pairs, "checks": checks, "unaligned_annotations": unaligned,
                      "annotation_document_id": document.get("_id", document.get("id")),
                      "annotation_passages": len(document.get("passages", [])),
                      "annotation_scope": "full_text" if str(document.get("pmcid", "")) else "check_source_metadata",
                      "relation_scope": "provider_predictions_not_a_full_text_relation_scan",
                      "limitations": ["Precomputed annotations may differ from the supplied XML version.",
                                      "Graph edges are model predictions, not verified supported relations.",
                                      "Full-text entity annotations do not imply full-text relation extraction coverage.",
                                      "No entity or relation recall estimate without independent annotations.",
                                      "Image pixels and external supplements are not processed.",
                                      "No candidate-pair semantic review has been executed."]}
            directory = output / "papers" / pid
            write_json(directory / "entities.json", entities)
            write_csv(directory / "entities.csv", entities,
                      ["entity_id", "entity_type", "canonical_name", "external_id", "normalization_status", "aliases", "mentions", "source"])
            with (directory / "pair_decisions.jsonl").open("w", encoding="utf-8") as stream:
                for pair in pairs:
                    stream.write(json.dumps(pair, ensure_ascii=False) + "\n")
            write_csv(directory / "relations.csv", [p for p in pairs if p["predictions"]],
                      ["pair_id", "gene", "disease", "status", "semantic_verification", "predictions", "evidence"])
            render_paper(result, directory)
            # Only fully exported results enter this run's collection.
            write_json(directory / "result.json", result)
            results.append(result)
            print(f"[{number}/{len(articles)}] {pid}: {counts['gene']} genes, {counts['disease']} diseases, "
                  f"{summary['predicted_edges']} predicted edges; integrity={checks['passed']}", flush=True)
        except (RuntimeError, ValueError, OSError, KeyError, TypeError) as error:
            failure = {"paper_id": pid, "stage": "baseline", "error_type": type(error).__name__, "error": str(error)}
            failures.append(failure)
            print(f"[{number}/{len(articles)}] FAILED {pid}: {error}", flush=True)
    if fetch_only:
        write_json(output / "fetch_manifest.json", {"cached_paper_ids": cached, "failures": failures,
                                                   "requested_paper_ids": [a["paper_id"] for a in articles]})
        return failures
    write_json(output / "run_failures.json", failures)
    summaries = [r["summary"] for r in results]
    quality, queue = collection_quality(results)
    quality["run_id"] = run_id
    write_json(output / "quality_report.json", quality)
    write_csv(output / "review_queue.csv", queue, ["paper_id", "category", "item_id", "detail"])
    fields = ["paper_id", "pmid", "title", "article_type", "genes", "diseases", "pairs", "predicted_edges", "supported_edges",
              "aligned_mentions", "unaligned_annotation_events", "integrity_passed", "semantic_verification"]
    write_csv(output / "summary.csv", summaries, fields)
    render_dashboard(summaries, failures, output)
    manifest = {"schema_version": 2, "run_id": run_id, "started_config_hash": config_hash,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "software_version": __version__, "python": platform.python_version(), "mode": "pubtator_baseline",
                "source_code_sha256": source_code_hash,
                "requested_papers": len(articles), "processed_this_run": len(results),
                "available_results": len(summaries), "failed_this_run": len(failures),
                "input_paper_ids": input_paper_ids,
                "expected_articles": [{"paper_id": a["paper_id"], "source_sha256": a["source_sha256"]} for a in articles],
                "successful_paper_ids": [r["article"]["paper_id"] for r in results],
                "selection": {"paper": paper, "limit": limit},
                "references_included": config.get("include_references", False),
                "background_relations_included_as_predictions": True,
                "semantic_verification": "not_run", "gold_standard_evaluation": "not_run",
                "sources": ["https://www.ncbi.nlm.nih.gov/research/pubtator3/",
                            "https://app.box.com/s/cf1gqx7eeug8rd5hajno2svt3q94snvv"]}
    write_json(output / "run_manifest.json", manifest)
    return failures


def main():
    parser = argparse.ArgumentParser(description="Evidence-linked XML literature mining baseline")
    parser.add_argument("command", choices=["prepare", "run", "fetch"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--paper")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    config = read_json(args.config)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    articles = prepare(config)
    if args.command == "prepare":
        return 1 if read_json(Path(config["output_dir"]) / "parse_failures.json") else 0
    failures = run(config, articles, limit=args.limit, paper=args.paper, offline=args.offline,
                   fetch_only=args.command == "fetch")
    parse_failures = read_json(Path(config["output_dir"]) / "parse_failures.json")
    return 1 if failures or parse_failures else 0


if __name__ == "__main__":
    sys.exit(main())
