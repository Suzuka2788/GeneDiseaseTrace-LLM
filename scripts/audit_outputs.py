"""Audit the expected inputs and exact exports of the current inference run."""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from biomed.io import digest, read_json, write_json
from biomed.results import load_results
from biomed.validate import validate


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.targets.extend(value for key, value in attrs if key == "href" and value)


def audit_outputs(output):
    output = Path(output)
    errors = []
    counts = {"papers": 0, "expected_papers": 0, "graphs": 0, "candidate_pairs": 0,
              "predicted_edges": 0, "supported_edges": 0, "mentions": 0, "checked_local_links": 0}
    run_id = None
    try:
        manifest = read_json(output / "run_manifest.json")
        run_id = manifest["run_id"]
        expected = {a["paper_id"] for a in manifest["expected_articles"]}
        successful = set(manifest["successful_paper_ids"])
        counts["expected_papers"] = len(expected)
        if not expected:
            errors.append("No expected input papers recorded")
        if len(expected) != len(manifest["expected_articles"]):
            errors.append("Duplicate expected paper IDs")
        if successful != expected or len(successful) != len(manifest["successful_paper_ids"]):
            errors.append("Successful-paper set does not match expected input set")
        with (output / "inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
            inventory = {row["paper_id"]: row for row in csv.DictReader(stream)}
        if set(manifest["input_paper_ids"]) != set(inventory):
            errors.append("Input inventory does not match the recorded input collection")
        if not expected <= set(inventory):
            errors.append("Expected paper missing from input inventory")
        for item in manifest["expected_articles"]:
            if item["paper_id"] in inventory and inventory[item["paper_id"]]["source_sha256"] != item["source_sha256"]:
                errors.append("Inventory input hash mismatch: " + item["paper_id"])
        if read_json(output / "parse_failures.json") or read_json(output / "run_failures.json"):
            errors.append("Parse or processing failures recorded")
        results = load_results(output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"Run records invalid: {type(error).__name__}: {error}")
        results = []

    counts["papers"] = len(results)
    reports = [output / "index.html"]
    for result in results:
        article = result["article"]
        paper = article["paper_id"]
        directory = output / "papers" / paper
        reports.append(directory / "report.html")
        try:
            checks = validate(article, result["entities"], result["pairs"])
            errors.extend(f"{paper}: {e}" for e in checks["errors"])
            if digest(Path(article["source_file"]).read_bytes()) != article["source_sha256"]:
                errors.append(f"{paper}: source file changed")
            graph = ET.parse(directory / "graph.graphml").getroot()
            graph_nodes = [n.get("id") for n in graph.findall(".//{*}node")]
            if set(graph_nodes) != {e["entity_id"] for e in result["entities"]} or len(graph_nodes) != len(result["entities"]):
                errors.append(f"{paper}: graph node set mismatch")
            edges = [p for p in result["pairs"] if p["status"] in ("predicted", "supported")]
            graph_edges = graph.findall(".//{*}edge")
            actual_edges = {(e.get("source"), e.get("target")) for e in graph_edges}
            expected_edges = {(p["gene_id"], p["disease_id"]) for p in edges}
            if actual_edges != expected_edges or len(graph_edges) != len(edges):
                errors.append(f"{paper}: graph edge endpoint set mismatch")
            with (directory / "pair_decisions.jsonl").open(encoding="utf-8") as stream:
                ledger = [json.loads(line) for line in stream if line.strip()]
            if ledger != result["pairs"]:
                errors.append(f"{paper}: pair ledger differs from JSON result")
            with (directory / "entities.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != len(result["entities"]) or {r["entity_id"] for r in rows} != set(graph_nodes):
                errors.append(f"{paper}: entity CSV ID set mismatch")
            ET.parse(directory / "graph.svg")
            counts["graphs"] += 1
            counts["candidate_pairs"] += len(ledger)
            counts["predicted_edges"] += sum(p["status"] == "predicted" for p in ledger)
            counts["supported_edges"] += sum(p["status"] == "supported" for p in ledger)
            counts["mentions"] += checks["checked_mentions"]
        except (OSError, ValueError, KeyError, ET.ParseError) as error:
            errors.append(f"{paper}: incomplete/invalid exports: {error}")
    try:
        with (output / "summary.csv").open(encoding="utf-8-sig", newline="") as stream:
            summaries = list(csv.DictReader(stream))
        if [r["paper_id"] for r in summaries] != [r["article"]["paper_id"] for r in results]:
            errors.append("Summary paper set/order differs from current results")
        for summary, result in zip(summaries, results):
            for key in ("genes", "diseases", "pairs", "predicted_edges", "supported_edges"):
                if int(summary[key]) != result["summary"][key]:
                    errors.append("Summary value mismatch: " + summary["paper_id"] + ":" + key)
    except (OSError, ValueError, KeyError) as error:
        errors.append(f"Summary invalid: {error}")
    for path in reports:
        try:
            parser = Links()
            parser.feed(path.read_text(encoding="utf-8"))
            for target in parser.targets:
                parts = urlsplit(target)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                counts["checked_local_links"] += 1
                if not (path.parent / unquote(parts.path)).resolve().is_file():
                    errors.append(f"Broken local link: {path.relative_to(output)} -> {target}")
        except OSError as error:
            errors.append(f"Report missing: {path.name}: {error}")
    return {"passed": not errors, "run_id": run_id, "counts": counts, "errors": errors,
            "scope": "Expected inputs, current-run per-paper exports, summary and report links. Derived overview/network figures are separate exports.",
            "note": "Delivery integrity only. Not a semantic correctness or recall evaluation."}


def main():
    config = read_json(ROOT / "config.json")
    output = ROOT / config["output_dir"]
    report = audit_outputs(output)
    write_json(output / "delivery_audit.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
