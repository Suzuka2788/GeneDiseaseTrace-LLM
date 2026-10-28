"""Read only results committed by one recorded inference run."""
from pathlib import Path

from .io import read_json


def load_results(output):
    output = Path(output)
    manifest = read_json(output / "run_manifest.json")
    expected = {item["paper_id"]: item for item in manifest["expected_articles"]}
    if len(expected) != len(manifest["expected_articles"]):
        raise ValueError("Duplicate expected paper IDs")
    if len(set(manifest["successful_paper_ids"])) != len(manifest["successful_paper_ids"]):
        raise ValueError("Duplicate successful paper IDs")
    results = []
    for paper_id in manifest["successful_paper_ids"]:
        if paper_id not in expected:
            raise ValueError(f"Unexpected successful paper: {paper_id}")
        result = read_json(output / "papers" / paper_id / "result.json")
        if result["run_id"] != manifest["run_id"] or result["config_sha256"] != manifest["started_config_hash"]:
            raise ValueError(f"Stale run/configuration for {paper_id}")
        if result["article"]["paper_id"] != paper_id:
            raise ValueError(f"Paper identity mismatch for {paper_id}")
        if result["article"]["source_sha256"] != expected[paper_id]["source_sha256"]:
            raise ValueError(f"Input hash mismatch for {paper_id}")
        if result["article"]["include_references"] != manifest["references_included"]:
            raise ValueError(f"Extraction scope mismatch for {paper_id}")
        results.append(result)
    return results
