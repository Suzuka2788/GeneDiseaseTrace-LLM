"""Independent, evidence-grounded pilot; never reads PubTator annotations."""
import argparse
import html
import itertools
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .io import digest, read_json, write_csv, write_json
from .jats import parse_article
from .llm_tasks import SYSTEM, checked_quote, chunks, task
from .report import graph_svg, graphml, shell


def entity_tasks(article):
    instructions = ('Extract all explicit gene and disease mentions. Gene/protein names may be '
        'included when a gene referent is plausible, but set ambiguity accordingly. Exclude generic '
        'symptoms/anatomy unless explicitly named as a disease. Return {"entities":['
        '{"entity_type":"gene|disease","canonical_name":"name","species":"explicit species or unknown",'
        '"ambiguity":"none or explanation","mentions":[{"block_id":"b0001","quote":"exact name"}]}]}.'
        ' Merge aliases only when the supplied text supports their identity; no external IDs.')
    return [task("entities", article, n, instructions, group)
            for n, group in enumerate(chunks(article), 1)]


def merge_entities(article, tasks, responses):
    merged = {}
    for item in tasks:
        for entity in responses[item["task_id"]]["entities"]:
            kind, name, species = entity["entity_type"], entity["canonical_name"], entity["species"]
            if kind not in ("gene", "disease") or not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid entity type or name")
            mentions = [checked_quote(article, item, m) for m in entity["mentions"]]
            if not mentions or not isinstance(species, str):
                raise ValueError("Entity requires grounded mentions and species")
            # Conservative exact-name merging does not assert cross-chunk alias equivalence.
            key = (kind, name, species)
            if key not in merged:
                merged[key] = {"entity_id": f"e{len(merged)+1:04d}", "entity_type": kind,
                    "canonical_name": name, "species": species, "external_id": "",
                    "aliases": [], "mentions": [], "ambiguities": []}
            target = merged[key]
            for mention in mentions:
                if mention not in target["mentions"]:
                    target["mentions"].append(mention)
                if mention["quote"] not in target["aliases"]:
                    target["aliases"].append(mention["quote"])
            if entity["ambiguity"] not in target["ambiguities"]:
                target["ambiguities"].append(entity["ambiguity"])
    return list(merged.values())


def relation_tasks(article, entities):
    # Pilot sends the entire included article per batch, avoiding retrieval-based omissions.
    if sum(len(b["text"]) for b in article["blocks"]) > 65000:
        raise ValueError("Pilot full-text limit exceeded; choose a shorter paper (no silent truncation)")
    genes = [e for e in entities if e["entity_type"] == "gene"]
    diseases = [e for e in entities if e["entity_type"] == "disease"]
    pairs = [{"pair_id": f"p{n:05d}", "gene_id": g["entity_id"], "disease_id": d["entity_id"]}
             for n, (g, d) in enumerate(itertools.product(genes, diseases), 1)]
    instructions = ('Assess every supplied pair independently using the complete supplied article. '
        'Return {"pairs":[{"pair_id":"p00001","decision":"supported|negated|uncertain|not_found",'
        '"relation_type":"association|correlation|causal|none",'
        '"source_scope":"study|background|mixed|unknown","reason":"brief evidence-based explanation",'
        '"evidence":[{"block_id":"b0001","quote":"exact supporting or negating passage"}]}]}. '
        'Supported means explicit positive evidence; co-occurrence, research aims and speculation '
        'are insufficient. A null statistical result is not proof of absence. Background claims '
        'may count but must be labeled. Causal claims need intervention/mechanistic evidence with '
        'species context. Include conflicting evidence and use uncertain if unresolved.')
    tasks = [task("relations", article, n, instructions,
                  {"blocks": article["blocks"], "entities": entities, "pairs": pairs[start:start+8]})
             for n, start in enumerate(range(0, len(pairs), 8), 1)]
    return tasks, pairs


def check_relations(article, tasks, responses):
    result = []
    for item in tasks:
        expected = {p["pair_id"]: p for p in item["context"]["pairs"]}
        rows = responses[item["task_id"]]["pairs"]
        ids = [p["pair_id"] for p in rows]
        if len(set(ids)) != len(ids) or set(ids) != set(expected):
            raise ValueError("Missing, duplicate or unexpected pair decisions")
        for row in rows:
            if row["decision"] not in ("supported", "negated", "uncertain", "not_found"):
                raise ValueError("Invalid relation decision")
            if row["relation_type"] not in ("association", "correlation", "causal", "none"):
                raise ValueError("Invalid relation type")
            if row["source_scope"] not in ("study", "background", "mixed", "unknown") or not row["reason"].strip():
                raise ValueError("Missing relation reasoning or source scope")
            evidence = [checked_quote(article, item, e) for e in row["evidence"]]
            if row["decision"] in ("supported", "negated") and not evidence:
                raise ValueError("Positive/negative assertion without evidence")
            if row["decision"] == "supported" and row["relation_type"] == "none":
                raise ValueError("Supported assertion requires relation type")
            result.append({**expected[row["pair_id"]], **row, "evidence": evidence,
                "status": "predicted" if row["decision"] == "supported" else "unreviewed",
                "predictions": [{"relation_type": row["relation_type"]}],
                "quote_check": "passed", "independent_semantic_review": "not_run"})
    return result


def endpoint(base_url):
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password:
        raise ValueError("Pilot endpoint must be local HTTP without embedded credentials")
    return base_url.rstrip("/")


def infer(item, base_url, model, api_key=""):
    url = endpoint(base_url) + "/chat/completions"
    payload = {"model": model, "temperature": 0, "max_tokens": 4096,
        "stream": False, "response_format": {"type": "json_object"},
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "system", "content": item["system"]},
                     {"role": "user", "content": json.dumps({"instructions": item["instructions"],
                                                               "context": item["context"]}, ensure_ascii=False)}]}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Local model returned HTTP {error.code}; response body withheld") from None
    choice = raw["choices"][0]
    if choice["finish_reason"] != "stop":
        raise ValueError("Incomplete model response; not accepted")
    return {"task_sha256": item["sha256"], "model": raw["model"],
        "requested_model": model, "seconds": round(time.monotonic() - started, 3),
        "usage": raw.get("usage", {}), "content": choice["message"]["content"]}


def execute(tasks, directory, base_url, model, key):
    responses = {}
    for item in tasks:
        path = directory / "responses" / f"{item['task_id']}.json"
        write_json(directory / "tasks" / f"{item['task_id']}.json", item)
        if path.exists():
            response = read_json(path)
            if response["task_sha256"] != item["sha256"] or response["requested_model"] != model:
                raise ValueError("Cached task/model mismatch; use a separate output directory")
        else:
            print(f"Running {item['task_id']}", flush=True)
            response = infer(item, base_url, model, key)
            write_json(path, response)
        # Persist the raw content before decoding so malformed JSON remains inspectable.
        payload = response["payload"] if "payload" in response else json.loads(response["content"])
        responses[item["task_id"]] = payload
    return responses


def run(source, output, base_url, model, key="", *, workflow="direct"):
    if workflow not in ("direct", "reviewed"):
        raise ValueError("Unknown workflow")
    output = Path(output)
    if (output / "result.json").exists():
        raise ValueError("Completed result exists; use a fresh output directory")
    article = parse_article(source)
    identity = {"source_sha256": article["source_sha256"], "model": model, "workflow": workflow,
                "endpoint": endpoint(base_url), "code_sha256": digest({p.name: digest(p.read_bytes())
                    for p in (Path(__file__), Path(__file__).with_name("identity.py"), Path(__file__).with_name("llm_tasks.py"))})}
    manifest_path = output / "manifest.json"
    if manifest_path.exists() and read_json(manifest_path)["identity"] != identity:
        raise ValueError("Run configuration changed; use a fresh output directory")
    if not manifest_path.exists():
        write_json(manifest_path, {"identity": identity, "created_at": datetime.now(timezone.utc).isoformat(),
                                  "pubtator_used": False})
    write_json(output / "article.json", article)
    write_json(output / "run_state.json", {"status": "running", "model": model,
        "source_sha256": article["source_sha256"], "method": "independent_llm", "pubtator_used": False})
    if workflow == "reviewed":
        from .identity import (collect_mentions, identity_task, mention_tasks, reconcile_reviews,
                               resolve_identities, review_tasks)
        if sum(len(b["text"]) for b in article["blocks"]) > 65000:
            raise ValueError("Reviewed pilot full-text limit exceeded")
        tasks = mention_tasks(article)
        mentions = collect_mentions(article, tasks, execute(tasks, output, base_url, model, key))
        write_json(output / "mentions.json", mentions)
        item = identity_task(article, mentions)
        identity_response = execute([item], output, base_url, model, key)[item["task_id"]]
        entities = resolve_identities(article, item, identity_response, mentions)
        write_json(output / "identity_decisions.json", identity_response)
    else:
        tasks = entity_tasks(article)
        entities = merge_entities(article, tasks, execute(tasks, output, base_url, model, key))
    write_json(output / "entities.json", entities)
    tasks, candidates = relation_tasks(article, entities)
    pairs = check_relations(article, tasks, execute(tasks, output, base_url, model, key))
    if workflow == "reviewed":
        write_json(output / "initial_pairs.json", pairs)
        tasks = review_tasks(article, entities, candidates)
        reviewed = check_relations(article, tasks, execute(tasks, output, base_url, model, key))
        write_json(output / "review_pairs.json", reviewed)
        pairs = reconcile_reviews(pairs, reviewed)
    if len(pairs) != len(candidates):
        raise ValueError("Incomplete Cartesian pair coverage")
    result = {"article": article, "entities": entities, "pairs": pairs,
        "method": "independent_llm", "workflow": workflow, "model": model, "pubtator_used": False,
        "quote_integrity": "passed", "independent_semantic_review": "not_run",
        "limitations": ["Exact quotes do not prove correct reasoning.",
            "Document-level identities are provisional, not database-resolved." if workflow == "reviewed" else
            "Cross-chunk aliases are merged only by identical canonical name and species.",
            "Same-model agreement is not independent expert verification.",
            "No independent recall evaluation; protein/gene ambiguity retained."]}
    write_csv(output / "entities.csv", entities, ["entity_id", "entity_type", "canonical_name", "species", "aliases", "mentions", "ambiguities"])
    write_csv(output / "pairs.csv", pairs, ["pair_id", "gene_id", "disease_id", "decision", "relation_type", "source_scope", "reason", "evidence", "quote_check"])
    graphml(result, output / "graph.graphml")
    svg = graph_svg(entities, pairs).replace("MODEL PREDICTIONS - semantic verification not run", "LLM PREDICTIONS - exact quotes checked; independent semantic review pending")
    (output / "graph.svg").write_text(svg, encoding="utf-8")
    names = {e["entity_id"]: e["canonical_name"] for e in entities}
    rows = ""
    for pair in pairs:
        values = [names[pair["gene_id"]], names[pair["disease_id"]], pair["decision"],
                  pair["relation_type"], pair["source_scope"], pair["reason"]]
        evidence_html = "".join(f"<a href='#{e['block_id']}'>{e['block_id']}</a><blockquote>"
                                f"{html.escape(e['quote'])}</blockquote>" for e in pair["evidence"])
        rows += "<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in values) + f"<td>{evidence_html}</td></tr>"
    body = f"<h1>{html.escape(article['title'])}</h1><p>Independent LLM pilot: {html.escape(model)}</p>"
    body += "<div class='notice'>Quotes checked against source. Model decisions have not been independently reviewed. Missing edges do not establish absence.</div>"
    body += f"<p>{len(entities)} entities; {len(pairs)} candidate pairs.</p><div class='graphbox'>{svg}</div>"
    body += f"<table><tr><th>Gene</th><th>Disease</th><th>Decision</th><th>Type</th><th>Scope</th><th>Reason</th><th>Evidence</th></tr>{rows}</table>"
    body += "<h2>Entities</h2><table><tr><th>ID</th><th>Type</th><th>Name</th><th>Species</th><th>Ambiguity</th></tr>"
    body += "".join("<tr>" + "".join(f"<td>{html.escape(str(e[k]))}</td>" for k in
        ("entity_id", "entity_type", "canonical_name", "species", "ambiguities")) + "</tr>" for e in entities) + "</table>"
    body += "<h2>Source text</h2>" + "".join(f"<section id='{b['block_id']}'><h3>{b['block_id']} · "
        f"{html.escape(b['section'])}</h3><p>{html.escape(b['text'])}</p></section>" for b in article["blocks"])
    (output / "index.html").write_text(shell("LLM pilot", body), encoding="utf-8")
    write_json(output / "result.json", result)
    (output / "failure.json").unlink(missing_ok=True)
    write_json(output / "run_state.json", {"status": "completed", "model": model,
        "source_sha256": article["source_sha256"], "entities": len(entities), "pairs": len(pairs),
        "predicted_edges": sum(p["status"] == "predicted" for p in pairs), "independent_semantic_review": "not_run"})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--key-file", type=Path, help="Local runtime key file; never copied to output")
    parser.add_argument("--prepare-only", action="store_true", help="Export entity tasks without inference")
    parser.add_argument("--workflow", choices=("direct", "reviewed"), default="direct")
    args = parser.parse_args()
    key = args.key_file.read_text(encoding="utf-8").strip() if args.key_file else os.environ.get("BIOMED_LOCAL_API_KEY", "")
    if args.prepare_only:
        article = parse_article(args.source)
        write_json(args.output / "article.json", article)
        from .identity import mention_tasks
        for item in (mention_tasks(article) if args.workflow == "reviewed" else entity_tasks(article)):
            write_json(args.output / "tasks" / f"{item['task_id']}.json", item)
        return
    try:
        run(args.source, args.output, args.base_url, args.model, key, workflow=args.workflow)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        # Network bodies and credentials must never appear in persisted errors.
        if not (args.output / "result.json").exists():
            failure = {"status": "failed", "error_type": type(error).__name__,
                       "message": "Pilot stopped; inspect task and response files. No completed result published."}
            write_json(args.output / "failure.json", failure)
            write_json(args.output / "run_state.json", failure)
        raise SystemExit(f"Pilot stopped ({type(error).__name__}); see {args.output / 'failure.json'}") from None


if __name__ == "__main__":
    main()
