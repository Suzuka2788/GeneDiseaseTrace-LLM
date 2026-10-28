"""Mention collection and document-level identity checks, before relation inference."""
import re

from .pubtator import occurrences
from .llm_tasks import checked_quote, chunks, task


def mention_tasks(article):
    instructions = ('Collect explicit gene/protein and disease NAME SURFACES, without merging aliases, '
        'assigning canonical names or inferring species. Include text in captions and marker proteins. '
        'Exclude anatomy, generic phenotypes, fluorescent tags and database labels. Return '
        '{"mentions":[{"surface":"exact name as printed","entity_type":"gene|disease",'
        '"ambiguity":"none or gene/protein uncertainty","block_id":"b0001"}]}. '
        'One example location per surface is enough; software will enumerate exact occurrences. '
        'Different disease subtype numbers are different surfaces. Do not infer unprinted gene names.')
    return [task("mentions", article, n, instructions, group)
            for n, group in enumerate(chunks(article, 9000), 1)]


def collect_mentions(article, tasks, responses):
    surfaces = {}
    for item in tasks:
        for row in responses[item["task_id"]]["mentions"]:
            if row["entity_type"] not in ("gene", "disease"):
                raise ValueError("Invalid mention type")
            checked_quote(article, item, {"block_id": row["block_id"], "quote": row["surface"]})
            key = (row["entity_type"], row["surface"])
            surfaces[key] = row["ambiguity"]
    result = []
    for (kind, surface), ambiguity in surfaces.items():
        locations = [{"block_id": b["block_id"], "quote": surface, "start": start, "end": end}
                     for b in article["blocks"] for start, end in occurrences(b["text"], surface)]
        if not locations:
            raise ValueError("Surface has no whole-token occurrence")
        result.append({"surface": surface, "entity_type": kind, "ambiguity": ambiguity, "mentions": locations})
    return result


def identity_task(article, mentions):
    return task("identity", article, 1,
        'Reconcile entity identities across the WHOLE article. Audit supplied surfaces against every '
        'paragraph and caption; add any omitted names with exact evidence. Merge only when the '
        'article establishes identity, not resemblance, family membership, shared roots or nearby numbers. '
        'Do not treat unknown species as evidence of a separate entity. Resolve species from explicit '
        'construct descriptions; preserve genuine ortholog/species ambiguity in ambiguity and species_context. '
        'A marker protein may remain a gene-type candidate with explicit protein ambiguity. '
        'Return {"entities":[{"entity_type":"gene|disease","canonical_name":"name",'
        '"species":"species or unknown","species_context":"explain relevant species/ortholog scope",'
        '"ambiguity":"none or explanation","aliases":["exact surface"],'
        '"identity_evidence":[{"block_id":"b0001","quote":"exact passage establishing identity"}]}],'
        '"excluded":[{"entity_type":"gene|disease","surface":"input surface","reason":"why excluded"}]}. '
        'Every supplied type/surface must appear in exactly one entity or the excluded ledger. '
        'Every alias must occur as a whole token in identity_evidence; quote enough context to justify '
        'equivalence. For a single surface an occurrence is sufficient. No external IDs. '
        'Do not merge distinct numbered subtypes. Species fields are provisional, not database taxon IDs.',
        {"blocks": article["blocks"], "mentions": mentions})


def resolve_identities(article, item, payload, mentions):
    entities, assigned = [], set()
    for row in payload["entities"]:
        kind, name, aliases = row["entity_type"], row["canonical_name"], row["aliases"]
        if kind not in ("gene", "disease") or not name.strip() or not aliases or len(set(aliases)) != len(aliases):
            raise ValueError("Invalid normalized entity")
        evidence = [checked_quote(article, item, q) for q in row["identity_evidence"]]
        numbers = {}
        locations = []
        for surface in aliases:
            key = (kind, surface)
            if key in assigned:
                raise ValueError("Surface assigned to multiple identities")
            if not any(occurrences(e["quote"], surface) for e in evidence):
                raise ValueError("Alias lacks whole-token identity evidence")
            match = re.fullmatch(r"([A-Za-z][A-Za-z-]*)([0-9]+)", surface)
            if match:
                prefix, suffix = match.groups()
                numbers.setdefault(prefix.casefold(), set()).add(suffix)
            assigned.add(key)
            locations.extend({"block_id": b["block_id"], "quote": surface, "start": start, "end": end}
                             for b in article["blocks"] for start, end in occurrences(b["text"], surface))
        if any(len(values) > 1 for values in numbers.values()):
            raise ValueError("Conflicting numbered aliases require explicit manual review")
        entities.append({"entity_id": f"e{len(entities)+1:04d}", "entity_type": kind,
            "canonical_name": name, "aliases": aliases, "species": row["species"],
            "species_context": row["species_context"], "external_id": "", "mentions": locations,
            "identity_evidence": evidence, "ambiguities": [row["ambiguity"]],
            "normalization_status": "document_model_reviewed_not_database_resolved"})
    excluded = set()
    for row in payload["excluded"]:
        key = (row["entity_type"], row["surface"])
        if not row["reason"].strip() or key in assigned or key in excluded:
            raise ValueError("Invalid or conflicting excluded surface")
        excluded.add(key)
    supplied = {(m["entity_type"], m["surface"]) for m in mentions}
    if not supplied <= assigned | excluded or not excluded <= supplied:
        raise ValueError("Incomplete input surface accounting")
    return entities


def review_tasks(article, entities, candidates):
    instructions = ('Independently assess each pair from the article without seeing prior verdicts. '
        'Act as an evidence auditor: do not trust the normalized aliases blindly. Check exact '
        'disease subtype, gene identity, species, negation and source scope. Inspect ALL captions '
        'as well as body paragraphs. A comparison with a different disease is not a negative result. '
        'Family/subtype links are not aliases. Do not infer causation from mutant cell phenotypes '
        'alone. Prefer direct disease-specific evidence; use uncertain if the identity is unresolved. '
        'Return {"pairs":[{"pair_id":"p00001","decision":"supported|negated|uncertain|not_found",'
        '"relation_type":"association|correlation|causal|none",'
        '"source_scope":"study|background|mixed|unknown","reason":"short justification",'
        '"evidence":[{"block_id":"b0001","quote":"exact passage"}]}]}. '
        'Every pair needs one verdict. Positive or negative assertions require exact evidence.')
    return [task("review", article, n, instructions,
                 {"blocks": article["blocks"], "entities": entities, "pairs": candidates[start:start+8]})
            for n, start in enumerate(range(0, len(candidates), 8), 1)]


def reconcile_reviews(initial, reviewed):
    by_id = {p["pair_id"]: p for p in reviewed}
    if len(by_id) != len(reviewed) or set(by_id) != {p["pair_id"] for p in initial}:
        raise ValueError("Review pair set mismatch")
    final = []
    for first in initial:
        second = by_id[first["pair_id"]]
        if (first["gene_id"], first["disease_id"]) != (second["gene_id"], second["disease_id"]):
            raise ValueError("Review endpoint mismatch")
        agrees = first["decision"] == second["decision"] and first["relation_type"] == second["relation_type"]
        evidence = list(first["evidence"])
        for quote in second["evidence"]:
            if quote not in evidence:
                evidence.append(quote)
        final.append({**first, "decision": first["decision"] if agrees else "uncertain",
            "status": "predicted" if agrees and first["decision"] == "supported" else "unreviewed",
            "relation_type": first["relation_type"] if agrees else "none",
            "source_scope": first["source_scope"] if first["source_scope"] == second["source_scope"] else "unknown",
            "reason": f"Initial: {first['reason']} Review: {second['reason']}", "evidence": evidence,
            "review_agreement": agrees, "initial_decision": first["decision"],
            "review_decision": second["decision"], "review_method": "same_model_fresh_context_blinded_to_initial",
            "independent_semantic_review": "not_run", "predictions": [{"relation_type": first["relation_type"] if agrees else "none"}]})
    return final
