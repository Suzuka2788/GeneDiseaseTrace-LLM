"""Mechanical integrity checks; these are not semantic or accuracy scores."""


def validate(article, entities, pairs):
    blocks = {b["block_id"]: b for b in article["blocks"]}
    by_id = {e["entity_id"]: e for e in entities}
    errors = []
    if len(by_id) != len(entities):
        errors.append("duplicate_entity_ids")
    mention_count = 0
    for entity in entities:
        for mention in entity["mentions"]:
            mention_count += 1
            block = blocks.get(mention["block_id"])
            if block is None or block["text"][mention["start"]:mention["end"]] != mention["text"]:
                errors.append(f"invalid_mention:{entity['entity_id']}:{mention['block_id']}")
    pair_ids = set()
    endpoints = set()
    for pair in pairs:
        if pair["pair_id"] in pair_ids:
            errors.append("duplicate_pair:" + pair["pair_id"])
        pair_ids.add(pair["pair_id"])
        endpoint = (pair["gene_id"], pair["disease_id"])
        if endpoint in endpoints:
            errors.append("duplicate_pair_endpoints:" + pair["pair_id"])
        endpoints.add(endpoint)
        gene, disease = by_id.get(pair["gene_id"]), by_id.get(pair["disease_id"])
        if not gene or not disease or gene["entity_type"] != "gene" or disease["entity_type"] != "disease":
            errors.append("invalid_pair_endpoints:" + pair["pair_id"])
        for evidence in pair["evidence"]:
            block = blocks.get(evidence["block_id"])
            if block is None or evidence["quote"] not in block["text"]:
                errors.append("invalid_quote:" + pair["pair_id"])
        if pair["status"] == "supported" and (not pair["evidence"] or pair["semantic_verification"] != "passed"):
            errors.append("unsupported_accepted_edge:" + pair["pair_id"])
    ng = sum(e["entity_type"] == "gene" for e in entities)
    nd = sum(e["entity_type"] == "disease" for e in entities)
    if len(pairs) != ng * nd:
        errors.append(f"pair_coverage_mismatch:{len(pairs)}!={ng * nd}")
    genes = [e["entity_id"] for e in entities if e["entity_type"] == "gene"]
    diseases = [e["entity_id"] for e in entities if e["entity_type"] == "disease"]
    expected = {(g, d) for g in genes for d in diseases}
    if endpoints != expected:
        errors.append(f"pair_set_mismatch:missing={len(expected - endpoints)},unexpected={len(endpoints - expected)}")
    return {"passed": not errors, "errors": errors, "checked_mentions": mention_count,
            "checked_pairs": len(pairs), "expected_pairs": ng * nd,
            "meaning": "Structural checks only; not entity/relationship accuracy."}
