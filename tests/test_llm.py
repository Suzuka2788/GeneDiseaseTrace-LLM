import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from biomed.io import read_json
from biomed.jats import parse_article
from biomed.llm import (check_relations, chunks, endpoint, entity_tasks, infer,
                        execute, merge_entities, relation_tasks, run)


XML = '''<article><front><article-meta><article-id pub-id-type="pmcid">PMC1</article-id>
<title-group><article-title>Study</article-title></title-group></article-meta></front>
<body><sec><title>Results</title><p>GeneA is associated with DiseaseB.</p></sec></body></article>'''


class LLMTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "article.xml"
        self.path.write_text(XML, encoding="utf-8")
        self.article = parse_article(self.path)
        self.block = next(b for b in self.article["blocks"] if "GeneA" in b["text"])
        self.tasks = entity_tasks(self.article)
        self.response = {self.tasks[0]["task_id"]: {"entities": [
            {"entity_type": k, "canonical_name": n, "species": "unknown", "ambiguity": "none",
             "mentions": [{"block_id": self.block["block_id"], "quote": n}]}
            for k, n in (("gene", "GeneA"), ("disease", "DiseaseB"))]}}

    def relation_response(self, tasks):
        return {tasks[0]["task_id"]: {"pairs": [{"pair_id": "p00001", "decision": "supported",
            "relation_type": "association", "source_scope": "study", "reason": "Explicit statement",
            "evidence": [{"block_id": self.block["block_id"], "quote": self.block["text"]}]}]}}

    def test_chunk_reassembly_no_loss(self):
        groups = chunks(self.article, 8)
        for block in self.article["blocks"]:
            pieces = [s["text"] for g in groups for s in g if s["block_id"] == block["block_id"]]
            self.assertEqual("".join(pieces), block["text"])

    def test_hallucinated_entity_rejected(self):
        self.response[self.tasks[0]["task_id"]]["entities"][0]["mentions"][0]["quote"] = "BRCA1"
        with self.assertRaisesRegex(ValueError, "task context"):
            merge_entities(self.article, self.tasks, self.response)

    def test_species_not_merged(self):
        row = self.response[self.tasks[0]["task_id"]]["entities"][0]
        self.response[self.tasks[0]["task_id"]]["entities"].append({**row, "species": "mouse"})
        self.assertEqual(len(merge_entities(self.article, self.tasks, self.response)), 3)

    def test_all_pairs_required_and_quotes_checked(self):
        entities = merge_entities(self.article, self.tasks, self.response)
        tasks, pairs = relation_tasks(self.article, entities)
        response = self.relation_response(tasks)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(check_relations(self.article, tasks, response)[0]["status"], "predicted")
        row = response[tasks[0]["task_id"]]["pairs"][0]
        row["evidence"][0]["quote"] = "GeneA causes DiseaseB"
        with self.assertRaises(ValueError):
            check_relations(self.article, tasks, response)
        response[tasks[0]["task_id"]]["pairs"] = []
        with self.assertRaisesRegex(ValueError, "Missing"):
            check_relations(self.article, tasks, response)

    def test_pipeline_exports_no_pubtator(self):
        def model(item, *_):
            payload = self.response[item["task_id"]] if item["stage"] == "entities" else self.relation_response([item])[item["task_id"]]
            return {"task_sha256": item["sha256"], "requested_model": "test", "model": "test", "payload": payload}
        output = Path(self.tmp.name) / "out"
        with patch("biomed.llm.infer", side_effect=model):
            result = run(self.path, output, "http://127.0.0.1:1/v1", "test")
        self.assertFalse(result["pubtator_used"])
        self.assertEqual(read_json(output / "run_state.json")["status"], "completed")
        self.assertIn("GeneA", (output / "graph.svg").read_text())
        self.assertTrue((output / "graph.graphml").exists())
        with self.assertRaisesRegex(ValueError, "Completed"):
            run(self.path, output, "http://127.0.0.1:1/v1", "test")

    def test_reviewed_pipeline_disagreement_withholds_edge(self):
        seen = []
        def model(item, *_):
            seen.append(item)
            if item["stage"] == "mentions":
                payload = {"mentions": [{"surface": name, "entity_type": kind, "ambiguity": "none",
                    "block_id": self.block["block_id"]} for kind, name in (("gene", "GeneA"), ("disease", "DiseaseB"))]}
            elif item["stage"] == "identity":
                payload = {"entities": [{"entity_type": kind, "canonical_name": name, "species": "unknown",
                    "species_context": "not specified", "ambiguity": "none", "aliases": [name],
                    "identity_evidence": [{"block_id": self.block["block_id"], "quote": self.block["text"]}]}
                    for kind, name in (("gene", "GeneA"), ("disease", "DiseaseB"))], "excluded": []}
            else:
                payload = self.relation_response([item])[item["task_id"]]
                if item["stage"] == "review":
                    payload["pairs"][0].update(decision="uncertain", relation_type="none")
            return {"task_sha256": item["sha256"], "requested_model": "test", "payload": payload}
        output = Path(self.tmp.name) / "reviewed"
        with patch("biomed.llm.infer", side_effect=model):
            result = run(self.path, output, "http://127.0.0.1:1/v1", "test", workflow="reviewed")
        self.assertEqual([t["stage"] for t in seen], ["mentions", "identity", "relations", "review"])
        self.assertNotIn("reference", str(seen))
        self.assertEqual(result["pairs"][0]["status"], "unreviewed")
        self.assertTrue((output / "review_pairs.json").exists())

    def test_remote_endpoint_rejected(self):
        for url in ("https://example.com/v1", "http://user:key@localhost/v1"):
            with self.assertRaises(ValueError):
                endpoint(url)

    def test_malformed_json_preserved_for_diagnosis(self):
        output = Path(self.tmp.name) / "invalid"
        item = self.tasks[0]
        response = {"task_sha256": item["sha256"], "requested_model": "test", "content": "{broken"}
        with patch("biomed.llm.infer", return_value=response):
            with self.assertRaises(json.JSONDecodeError):
                execute([item], output, "http://127.0.0.1:1/v1", "test", "")
        self.assertEqual(read_json(output / "responses" / f"{item['task_id']}.json")["content"], "{broken")

    def test_resume_rejects_different_model(self):
        output = Path(self.tmp.name) / "cached"
        item = self.tasks[0]
        response = {"task_sha256": item["sha256"], "requested_model": "first", "payload": {"entities": []}}
        with patch("biomed.llm.infer", return_value=response):
            execute([item], output, "http://127.0.0.1:1/v1", "first", "")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            execute([item], output, "http://127.0.0.1:1/v1", "second", "")

    def test_foreign_quote_and_duplicate_pair_rejected(self):
        entities = merge_entities(self.article, self.tasks, self.response)
        tasks, _ = relation_tasks(self.article, entities)
        response = self.relation_response(tasks)
        rows = response[tasks[0]["task_id"]]["pairs"]
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            check_relations(self.article, tasks, response)
        rows.pop()
        rows[0]["evidence"][0]["block_id"] = "foreign"
        with self.assertRaisesRegex(ValueError, "unknown block"):
            check_relations(self.article, tasks, response)

    def test_real_http_adapter_contract_and_truncation(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            finish_reason = "stop"
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"model": "fixture", "choices": [{"finish_reason": self.finish_reason,
                    "message": {"content": '{"entities":[]}'}}]}).encode())
            def log_message(self, *_):
                pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/v1"
            self.assertEqual(json.loads(infer(self.tasks[0], url, "fixture")["content"]), {"entities": []})
            self.assertNotIn("PubTator", str(received))
            Handler.finish_reason = "length"
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                infer(self.tasks[0], url, "fixture")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
