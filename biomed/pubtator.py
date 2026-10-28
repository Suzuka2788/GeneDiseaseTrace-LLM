"""Public, precomputed PubTator3 predictions aligned to the supplied XML.

The service's document-level relation predictions are NOT evidence validation.
Only locally aligned entity mentions enter the output graph.
"""
import re
import time
import urllib.parse
from pathlib import Path

from .io import read_json, request_json, write_json
from .jats import normalize

API = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson"


def fetch(pmid, cache_dir, timeout=45, retries=2, interval=0.55, offline=False):
    cache = Path(cache_dir) / "pubtator" / f"{pmid}.json"
    if cache.exists():
        data = read_json(cache)
    elif offline:
        raise FileNotFoundError(f"PubTator cache missing for PMID {pmid}")
    else:
        url = API + "?" + urllib.parse.urlencode({"pmids": pmid, "full": "true"})
        try:
            data = request_json(url, timeout=timeout, retries=retries)
        finally:
            time.sleep(interval)
        # Cache the public response, including a legitimate empty result.
        write_json(cache, data)
    documents = data.get("PubTator3", data.get("documents", [])) if isinstance(data, dict) else data
    if not isinstance(documents, list):
        raise ValueError("Unexpected PubTator response shape")
    for document in documents:
        if str(document.get("pmid", "")) == str(pmid) or str(document.get("id")) == str(pmid):
            return document
        for passage in document.get("passages", []):
            if str(passage.get("infons", {}).get("article-id_pmid", "")) == str(pmid):
                return document
    raise ValueError(f"No matching PubTator document for PMID {pmid}")


def occurrences(text, surface):
    if not surface:
        return []
    # Preserve case: CAT, MET and other short gene symbols are ambiguous words.
    pattern = re.compile(r"(?<!\w)" + re.escape(normalize(surface)) + r"(?!\w)")
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


def extract_entities(article, document):
    groups = {}
    rejected = []
    for passage in document.get("passages", []):
        for annotation in passage.get("annotations", []):
            info = annotation.get("infons", {})
            kind = info.get("type", "").lower()
            if kind not in ("gene", "disease"):
                continue
            surface = normalize(annotation.get("text", ""))
            if not surface:
                continue
            identifier = str(info.get("identifier", "")).strip()
            # Do not collapse unresolved mentions into one shared empty-ID entity.
            key = (kind, identifier if identifier not in ("", "-", "-1") else "surface:" + surface)
            entity = groups.setdefault(key, {"entity_type": kind, "external_id": identifier,
                                             "canonical_name": info.get("name") or surface,
                                             "aliases": set(), "mentions": [], "source": "PubTator3",
                                             "accession": info.get("accession", ""),
                                             "normalization_status": "resolved" if (
                                                 info.get("valid") is True and
                                                 (identifier.isdigit() if kind == "gene" else identifier.startswith(("MESH:", "OMIM:"))))
                                             else "unresolved",
                                             "biological_type_review": "not_run",
                                             "species_review": "not_run"})
            # Annotation offsets refer to PubTator text, not the supplied XML.
            # Anchor to the source passage first to avoid spreading ambiguous aliases
            # into unrelated paragraphs (e.g. CAT as an ordinary word).
            source = normalize(passage.get("text", ""))
            source_matches = []
            for block in article["blocks"]:
                target = block["text"]
                context_match = target == source or (
                    len(source) >= 60 and len(target) >= 60 and (source in target or target in source))
                if source and context_match and occurrences(target, surface):
                    source_matches.append(block)
            aligned = source_matches
            if not aligned:
                # Distinctive longer context may align after differences in xrefs.
                for block in article["blocks"]:
                    if not occurrences(block["text"], surface):
                        continue
                    source_words = set(re.findall(r"\w+", source.lower()))
                    target_words = set(re.findall(r"\w+", block["text"].lower()))
                    overlap = len(source_words & target_words) / max(1, min(len(source_words), len(target_words)))
                    if overlap >= 0.8 and min(len(source_words), len(target_words)) >= 6:
                        aligned.append(block)
            matched = False
            for block in aligned:
                for start, end in occurrences(block["text"], surface):
                    mention = {"block_id": block["block_id"], "text": block["text"][start:end],
                               "start": start, "end": end, "alignment": "source_context"}
                    if mention not in entity["mentions"]:
                        entity["mentions"].append(mention)
                    matched = True
            if matched:
                entity["aliases"].add(surface)
            else:
                rejected.append({"type": kind, "text": surface, "external_id": identifier,
                                 "reason": "annotation_not_aligned_to_included_XML_content"})
    entities = []
    for key in sorted(groups):
        entity = groups[key]
        if not entity["mentions"]:
            continue
        entity["entity_id"] = ("G" if key[0] == "gene" else "D") + f"{len(entities) + 1:04d}"
        entity["aliases"] = sorted(entity["aliases"])
        entity["mentions"].sort(key=lambda m: (m["block_id"], m["start"]))
        entities.append(entity)
    return entities, rejected


def relation_predictions(document, entities):
    index = {(e["entity_type"], e["external_id"]): e["entity_id"] for e in entities}
    result = {}
    for relation in document.get("relations", []):
        info = relation.get("infons", {})
        roles = [info.get("role1", {}), info.get("role2", {})]
        kinds = [role.get("type", "").lower() for role in roles]
        if set(kinds) != {"gene", "disease"}:
            continue
        mapped = {kind: index.get((kind, str(role.get("identifier", "")))) for kind, role in zip(kinds, roles)}
        if not all(mapped.values()):
            continue
        pair = (mapped["gene"], mapped["disease"])
        prediction = {"source_relation_id": relation.get("id"), "relation_type": info.get("type", ""),
                      "source_score": info.get("score"), "source": "PubTator3"}
        result.setdefault(pair, []).append(prediction)
    return result


def pair_records(article, entities, predictions):
    blocks = {b["block_id"]: b for b in article["blocks"]}
    genes = [e for e in entities if e["entity_type"] == "gene"]
    diseases = [e for e in entities if e["entity_type"] == "disease"]
    records = []
    for gene in genes:
        gb = {m["block_id"] for m in gene["mentions"]}
        for disease in diseases:
            db = {m["block_id"] for m in disease["mentions"]}
            common = sorted(gb & db)
            evidence = [{"block_id": bid, "quote": blocks[bid]["text"],
                         "evidence_role": "retrieved_context_not_semantically_verified"} for bid in common[:6]]
            preds = predictions.get((gene["entity_id"], disease["entity_id"]), [])
            # A missing precomputed relation is neither a negative nor a completed review.
            records.append({"pair_id": f"{gene['entity_id']}__{disease['entity_id']}",
                            "gene_id": gene["entity_id"], "disease_id": disease["entity_id"],
                            "gene": gene["canonical_name"], "disease": disease["canonical_name"],
                            "status": "predicted" if preds else "unreviewed",
                            "predictions": preds, "evidence": evidence,
                            "same_block_count": len(common), "semantic_verification": "not_run",
                            "coverage": {"mode": "precomputed_full_text_annotations_and_local_alignment",
                                         "retrieved_blocks": common, "all_pairs_semantically_reviewed": False}})
    return records
