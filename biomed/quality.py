"""Automatic review routing. Flags measure processing needs, not accuracy."""
from collections import Counter


def review_queue(result):
    paper_id = result["article"]["paper_id"]
    queue = []

    def add(category, item, detail):
        queue.append({"paper_id": paper_id, "category": category, "item_id": item, "detail": detail})

    for entity in result["entities"]:
        if entity.get("normalization_status") != "resolved":
            add("unresolved_entity_normalization", entity["entity_id"],
                f"{entity['canonical_name']} | {entity['external_id']} | {'; '.join(entity['aliases'])}")
    for pair in result["pairs"]:
        if pair["status"] == "predicted" and not pair["evidence"]:
            add("prediction_without_shared_block", pair["pair_id"],
                "Cross-block retrieval and semantic evidence verification required")
    for kind in ("gene", "disease"):
        if not any(e["entity_type"] == kind for e in result["entities"]):
            add("zero_entity_type", kind, "May be legitimate; extraction completeness has not been assessed")
    for warning in result["article"]["warnings"]:
        add("source_coverage", "article", warning)
    for error in result["checks"]["errors"]:
        add("integrity_error", "article", error)
    return queue


def collection_quality(results):
    queue = [entry for result in results for entry in review_queue(result)]
    return {"papers": len(results), "categories": dict(Counter(q["category"] for q in queue)),
            "article_types": dict(Counter(r["article"].get("article_type", "unknown") for r in results)),
            "papers_with_no_predicted_edges": sum(r["summary"]["predicted_edges"] == 0 for r in results),
            "papers_with_zero_gene_nodes": sum(r["summary"]["genes"] == 0 for r in results),
            "papers_with_zero_disease_nodes": sum(r["summary"]["diseases"] == 0 for r in results),
            "all_structural_checks_passed": all(r["checks"]["passed"] for r in results),
            "semantic_verification": "not_run", "accuracy_evaluation": "not_run",
            "note": "These are workflow diagnostics; none is an estimate of accuracy or recall."}, queue
